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


# Function to extract token from pirilampo.tv URLs with shared browser context
async def fetch_pirilampo_token(page, channel_page_url, retries=3):
    for attempt in range(retries):
        try:
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
                
                # Wait for token URL to be captured instead of fixed sleep
                try:
                    await page.wait_for_response(
                        lambda response: "token=" in response.url and "moonlight.wideiptv.top" in response.url,
                        timeout=15000
                    )
                    logging.info(f"Token response detected for {channel_page_url}")
                except Exception:
                    # Fallback to shorter sleep if specific response not detected
                    await asyncio.sleep(3)
                    logging.warning(f"Token response timeout, using fallback wait for {channel_page_url}")
                
            except Exception as e:
                logging.error(f"Error loading page {channel_page_url} on attempt {attempt + 1}: {e}")
                continue

            # Clear the route to avoid interference with next page
            await page.unroute("**/*")

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


# Function to fetch and validate m3u8 URL with shared browser context
async def fetch_m3u8_stream_url(page, channel_page_url, retries=3):
    for attempt in range(retries):
        try:
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
                await page.goto(channel_page_url, wait_until='domcontentloaded', timeout=30000)
                
                # Wait for m3u8 response instead of fixed sleep
                try:
                    await page.wait_for_response(
                        lambda response: ".m3u8" in response.url,
                        timeout=10000
                    )
                    logging.info(f"M3U8 response detected for {channel_page_url}")
                except Exception:
                    # Fallback to shorter sleep if specific response not detected
                    await asyncio.sleep(2)
                    logging.warning(f"M3U8 response timeout, using fallback wait for {channel_page_url}")
                
            except Exception as e:
                logging.error(f"Error loading page {channel_page_url} on attempt {attempt + 1}: {e}")
                continue

            # Clear the route to avoid interference with next page
            await page.unroute("**/*")

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
        elif tvg_id == "14":  # Leo-tv-hd
            return f"https://moonlight.wideiptv.top/LeoTV/index.fmp4.m3u8?token={fetched_result}"
        else:
            # Default fallback for other pirilampo channels
            return f"https://moonlight.wideiptv.top/VividHD/index.fmp4.m3u8?token={fetched_result}"
    else:
        # For non-pirilampo URLs, return the direct m3u8 URL
        return fetched_result


# Async function to process a single channel with shared browser context
async def process_channel(page, channel_info, channel_url, tvg_id, is_pirilampo=False):
    """Process a single channel and return the result"""
    try:
        if is_pirilampo:
            logging.info(f"Processing pirilampo channel tvg-id={tvg_id}: {channel_url}")
            fetched_result = await fetch_pirilampo_token(page, channel_url)
        else:
            logging.info(f"Processing regular channel tvg-id={tvg_id}: {channel_url}")
            fetched_result = await fetch_m3u8_stream_url(page, channel_url)
        
        if fetched_result:
            final_url = build_final_url(channel_url, fetched_result, tvg_id)
            if final_url:
                logging.info(f"Successfully processed tvg-id={tvg_id}: {final_url}")
                return tvg_id, final_url
        
        logging.error(f"Failed to process tvg-id={tvg_id}")
        return tvg_id, None
        
    except Exception as e:
        logging.error(f"Error processing channel tvg-id={tvg_id}: {e}")
        return tvg_id, None


# Update M3U file with shared browser context and true concurrency
async def update_m3u_file(m3u_path, channel_updates, pirilampo_channels):
    if not os.path.exists(m3u_path):
        logging.error(f"File not found: {m3u_path}")
        return

    try:
        with open(m3u_path, 'r') as file:
            lines = file.readlines()

        # Collect all channels to process
        channels_to_process = []
        line_indices = {}  # Map tvg_id to line index for updates

        for i, line in enumerate(lines):
            if line.startswith('#EXTINF:') and 'group-title="NEW-XXX"' in line:
                channel_info = line.strip()
                channel_url = lines[i + 1].strip()
                tvg_id = channel_info.split('tvg-id="')[1].split('"')[0]
                if tvg_id in channel_updates:
                    is_pirilampo = tvg_id in pirilampo_channels
                    channels_to_process.append((channel_info, channel_updates[tvg_id], tvg_id, is_pirilampo))
                    line_indices[tvg_id] = i + 1

        if not channels_to_process:
            logging.info("No channels to process")
            return

        # Launch browser once and reuse context
        logging.info(f"Starting browser for processing {len(channels_to_process)} channels...")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context()
            
            # Create multiple pages for better concurrency (but limit to avoid overwhelming)
            max_concurrent = min(4, len(channels_to_process))  # Limit concurrent pages
            pages = []
            for _ in range(max_concurrent):
                pages.append(await context.new_page())
            
            # Process channels with limited concurrency
            semaphore = asyncio.Semaphore(max_concurrent)
            
            async def process_with_semaphore(channel_data, page_index):
                async with semaphore:
                    page = pages[page_index % len(pages)]
                    return await process_channel(page, *channel_data)
            
            # Process all channels concurrently
            logging.info(f"Processing {len(channels_to_process)} channels concurrently...")
            tasks = [
                process_with_semaphore(channel_data, i) 
                for i, channel_data in enumerate(channels_to_process)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Close browser
            await browser.close()

        # Update the M3U file with results
        successful_updates = 0
        for result in results:
            if isinstance(result, Exception):
                logging.error(f"Task failed with exception: {result}")
                continue
                
            tvg_id, final_url = result
            if final_url and tvg_id in line_indices:
                lines[line_indices[tvg_id]] = final_url + "\n"
                successful_updates += 1
                logging.info(f"Updated line for tvg-id={tvg_id}")
            else:
                logging.error(f"Failed to get final URL for tvg-id={tvg_id}")

        # Write updated M3U file
        if successful_updates > 0:
            with open(m3u_path, 'w') as file:
                file.writelines(lines)
            logging.info(f"Successfully updated M3U file with {successful_updates} channels: {m3u_path}")
        else:
            logging.warning("No channels were successfully updated")

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
        "13": "https://www.pirilampo.tv/live-tv/vivid-red-hd.html/",
        "14": "https://www.pirilampo.tv/live-tv/leo-tv.html"
    }
    
    # Specify which channels are pirilampo channels (need token extraction)
    pirilampo_channels = {"12", "13", "14"}  # Add more IDs here as needed
    
    await update_m3u_file(m3u_path, channel_updates, pirilampo_channels)


if __name__ == "__main__":
    asyncio.run(main())
