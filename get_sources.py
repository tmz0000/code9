import asyncio
from playwright.async_api import async_playwright
import logging
import os
import requests
import urllib3
import re
from urllib.parse import urlparse, parse_qs

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logging.basicConfig(level=logging.INFO)


# Function to extract token from pirilampo.tv URLs
async def fetch_pirilampo_token(channel_page_url, retries=3):
    for attempt in range(retries):
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=False)
                context = await browser.new_context()
                page = await context.new_page()

                token_urls = []

                # Capture requests containing tokens
                async def handle_route(route, request):
                    request_url = request.url
                    if "token=" in request_url and "moonlight.wideiptv.top" in request_url:
                        token_urls.append(request_url)
                        logging.info(f"Found token URL: {request_url}")
                    await route.continue_()

                await page.route("**/*", handle_route)

                try:
                    await page.goto(channel_page_url, wait_until='domcontentloaded', timeout=30000)
                    await asyncio.sleep(8)  # Wait for dynamic content to load
                except Exception as e:
                    logging.error(f"Error loading page {channel_page_url} on attempt {attempt + 1}: {e}")
                    await browser.close()
                    continue

                await browser.close()

                # Extract token from captured URLs
                for url in token_urls:
                    try:
                        parsed_url = urlparse(url)
                        query_params = parse_qs(parsed_url.query)
                        if 'token' in query_params:
                            token = query_params['token'][0]
                            logging.info(f"Extracted token: {token}")
                            return token
                    except Exception as e:
                        logging.error(f"Error extracting token from {url}: {e}")

        except Exception as e:
            logging.error(f"Attempt {attempt + 1} failed for {channel_page_url}: {e}")

        if attempt < retries - 1:
            logging.warning(f"Retrying {channel_page_url} ({attempt + 1}/{retries})...")

    logging.error(f"Failed to fetch token for {channel_page_url} after {retries} attempts")
    return None


# Function to fetch and validate m3u8 URL with retries (for regular channels)
async def fetch_m3u8_stream_url(channel_page_url, retries=3):
    for attempt in range(retries):
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=False)
                context = await browser.new_context()
                page = await context.new_page()

                playlist_urls = []

                # Capture all .m3u8 requests
                async def handle_route(route, request):
                    request_url = request.url
                    if ".m3u8" in request_url:
                        playlist_urls.append(request_url)
                        logging.info(f"Found potential playlist URL: {request_url}")
                    await route.continue_()

                await page.route("**/*", handle_route)

                try:
                    await page.goto(channel_page_url, wait_until='networkidle', timeout=30000)
                except Exception as e:
                    logging.error(f"Error loading page {channel_page_url} on attempt {attempt + 1}: {e}")
                    await browser.close()
                    continue

                await asyncio.sleep(5)
                await browser.close()

                # Validate m3u8 URLs
                for url in playlist_urls:
                    try:
                        response = requests.head(url, timeout=10, verify=False)
                        if response.status_code == 200:
                            logging.info(f"Valid playlist URL: {url}")
                            return url  # Return valid URL immediately
                        else:
                            logging.warning(f"Invalid playlist URL: {url}")
                    except requests.exceptions.RequestException as e:
                        logging.error(f"Error validating URL {url}: {e}")

        except Exception as e:
            logging.error(f"Attempt {attempt + 1} failed for {channel_page_url}: {e}")

        if attempt < retries - 1:
            logging.warning(f"Retrying {channel_page_url} ({attempt + 1}/{retries})...")

    logging.error(f"Failed to fetch stream URL for {channel_page_url} after {retries} attempts")
    return None


# Function to build the final URL based on channel type
def build_final_url(channel_page_url, fetched_result, tvg_id):
    if "pirilampo.tv" in channel_page_url and fetched_result:
        # Build the moonlight URL with the extracted token
        if tvg_id == "12":  # nuart-tv
            return f"https://moonlight.wideiptv.top/NuartTV/index.fmp4.m3u8?token={fetched_result}"
        elif tvg_id == "13":  # vivid-red-hd
            return f"https://moonlight.wideiptv.top/VividHD/index.fmp4.m3u8?token={fetched_result}"
        else:
            # Default fallback for other pirilampo channels
            return f"https://moonlight.wideiptv.top/VividHD/index.fmp4.m3u8?token={fetched_result}"
    else:
        # For non-pirilampo URLs, return the direct m3u8 URL
        return fetched_result


# Update M3U file
async def update_m3u_file(m3u_path, channel_updates, pirilampo_channels):
    if not os.path.exists(m3u_path):
        logging.error(f"File not found: {m3u_path}")
        return

    try:
        with open(m3u_path, 'r') as file:
            lines = file.readlines()

        # Separate regular channels and pirilampo channels
        regular_tasks = []
        pirilampo_tasks = []

        for i, line in enumerate(lines):
            if line.startswith('#EXTINF:') and 'group-title="NEW-XXX"' in line:
                channel_info = line.strip()
                channel_url = lines[i + 1].strip()
                tvg_id = channel_info.split('tvg-id="')[1].split('"')[0]
                if tvg_id in channel_updates:
                    if tvg_id in pirilampo_channels:
                        # Schedule pirilampo token fetching
                        pirilampo_tasks.append((i + 1, channel_info, channel_updates[tvg_id], tvg_id))
                    else:
                        # Schedule regular m3u8 fetching
                        regular_tasks.append((i + 1, channel_info, channel_updates[tvg_id], tvg_id))

        # Fetch regular m3u8 URLs concurrently
        logging.info(f"Fetching {len(regular_tasks)} regular m3u8 URLs...")
        regular_results = []
        if regular_tasks:
            regular_results = await asyncio.gather(*[fetch_m3u8_stream_url(task[2]) for task in regular_tasks])

        # Fetch pirilampo tokens concurrently
        logging.info(f"Fetching {len(pirilampo_tasks)} pirilampo tokens...")
        pirilampo_results = []
        if pirilampo_tasks:
            pirilampo_results = await asyncio.gather(*[fetch_pirilampo_token(task[2]) for task in pirilampo_tasks])

        # Update regular channel URLs
        for idx, result in enumerate(regular_results):
            if result:
                final_url = build_final_url(regular_tasks[idx][2], result, regular_tasks[idx][3])
                if final_url:
                    logging.info(f"Updated tvg-id={regular_tasks[idx][3]} with new URL: {final_url}")
                    lines[regular_tasks[idx][0]] = final_url + "\n"
                else:
                    logging.error(f"Failed to build final URL for tvg-id={regular_tasks[idx][3]}")
            else:
                logging.error(f"Failed to fetch stream URL for tvg-id={regular_tasks[idx][3]}")

        # Update pirilampo channel URLs
        for idx, result in enumerate(pirilampo_results):
            if result:
                final_url = build_final_url(pirilampo_tasks[idx][2], result, pirilampo_tasks[idx][3])
                if final_url:
                    logging.info(f"Updated tvg-id={pirilampo_tasks[idx][3]} with new URL: {final_url}")
                    lines[pirilampo_tasks[idx][0]] = final_url + "\n"
                else:
                    logging.error(f"Failed to build final URL for tvg-id={pirilampo_tasks[idx][3]}")
            else:
                logging.error(f"Failed to fetch token for tvg-id={pirilampo_tasks[idx][3]}")

        # Write updated M3U file
        with open(m3u_path, 'w') as file:
            file.writelines(lines)

        logging.info(f"Successfully updated M3U file: {m3u_path}")
    except Exception as e:
        logging.error(f"Failed to update M3U file: {e}")


# Main function
async def main():
    m3u_path = 's18.m3u'
    
    # All channel updates
    channel_updates = {
        "01": "https://adult-tv-channels.com/redlight-hd-online/",
        "02": "https://adult-tv-channels.com/dorcel-tv-online/",
        "03": "https://adult-tv-channels.com/penthouse-passion-online/",
        "04": "https://adult-tv-channels.com/penthouse-passion-tv-online/",
        "05": "https://adult-tv-channels.com/vivid-tv-online/",
        "06": "https://adult-tv-channels.com/eroxxx-hd-tv-online/",
        "07": "https://adult-tv-channels.com/extasy-tv-online/",
        "08": "https://adult-tv-channels.com/pink-erotic-tv-online/",
        "09": "https://adult-tv-channels.com/private-tv-online/",
        "10": "https://adult-tv-channels.com/ox-ax-tv-online/",
        "11": "https://adult-tv-channels.com/evil-angel-tv-online/",
        "12": "https://www.pirilampo.tv/live-tv/nuart-tv.html/",
        "13": "https://www.pirilampo.tv/live-tv/vivid-red-hd.html/"
    }
    
    # Specify which channels are pirilampo channels (need token extraction)
    pirilampo_channels = {"12", "13"}  # Add more IDs here as needed
    
    await update_m3u_file(m3u_path, channel_updates, pirilampo_channels)


if __name__ == "__main__":
    asyncio.run(main())
