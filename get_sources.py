import asyncio
from playwright.async_api import async_playwright
import logging
import os
import requests
import urllib3
import aiohttp

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logging.basicConfig(level=logging.INFO)


# Function to fetch and validate m3u8 URL with retries
async def fetch_new_stream_url(channel_page_url, retries=3):
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
                    # Load the page with slightly extended time for dynamic content
                    await page.goto(channel_page_url, wait_until='networkidle', timeout=30000)
                except Exception as e:
                    logging.error(f"Error loading page {channel_page_url} on attempt {attempt + 1}: {e}")
                    await browser.close()
                    continue

                await asyncio.sleep(5)  # Reduced wait time for page interaction
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

        logging.warning(f"Retrying {channel_page_url} ({attempt + 1}/{retries})...")

    logging.error(f"Failed to fetch stream URL for {channel_page_url} after {retries} attempts")
    return None


# Update M3U file
async def update_m3u_file(m3u_path, channel_updates):
    if not os.path.exists(m3u_path):
        logging.error(f"File not found: {m3u_path}")
        return

    try:
        with open(m3u_path, 'r') as file:
            lines = file.readlines()

        updated_lines = []
        tasks = []

        for i, line in enumerate(lines):
            if line.startswith('#EXTINF:') and 'group-title="NEW-XXX"' in line:
                channel_info = line.strip()
                channel_url = lines[i + 1].strip()
                tvg_id = channel_info.split('tvg-id="')[1].split('"')[0]
                if tvg_id in channel_updates:
                    # Schedule fetching URL concurrently
                    tasks.append((i + 1, channel_info, channel_updates[tvg_id]))

        # Fetch all URLs concurrently
        fetch_results = await asyncio.gather(*[fetch_new_stream_url(task[2]) for task in tasks])

        # Update URLs in the lines
        for idx, result in enumerate(fetch_results):
            if result:
                logging.info(f"Updated tvg-id={tasks[idx][1]} with new URL: {result}")
                lines[tasks[idx][0]] = result + "\n"
            else:
                logging.error(f"Failed to fetch stream URL for {tasks[idx][1]}")

        # Write updated M3U file
        with open(m3u_path, 'w') as file:
            file.writelines(lines)

        logging.info(f"Successfully updated M3U file: {m3u_path}")
    except Exception as e:
        logging.error(f"Failed to update M3U file: {e}")


# Main function
async def main():
    m3u_path = 's18.m3u'
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
        "11": "https://adult-tv-channels.com/evil-angel-tv-online/"
    }
    await update_m3u_file(m3u_path, channel_updates)


# Function to test multiple accesses
async def test_multiple_accesses(m3u8_url, num_sessions=10):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    }

    async def access_m3u8(session, url, session_id):
        try:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    logging.info(f"[Session {session_id}] Successfully accessed {url}")
                    return True
                else:
                    logging.warning(f"[Session {session_id}] Failed with status {response.status}")
                    return False
        except Exception as e:
            logging.error(f"[Session {session_id}] Error accessing {url}: {e}")
            return False

    async with aiohttp.ClientSession(headers=headers) as session:
        tasks = [access_m3u8(session, m3u8_url, i + 1) for i in range(num_sessions)]
        results = await asyncio.gather(*tasks)

    successful_accesses = sum(results)
    logging.info(f"Total successful accesses: {successful_accesses}/{num_sessions}")
    return successful_accesses


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logging.error(f"Error running main: {e}")

    try:
        test_url = "https://ortepe.xyz:47269/tv/dorcel/playlist.m3u8?wmsAuthSign=c2VydmVyX3RpbWU9MTIvNS8yMDI0IDExOjUyOjA4IEFNJmhhc2hfdmFsdWU9UzVyV3J0NEl2MjdGb3AzQUcyYmVvUT09JnZhbGlkbWludXRlcz02MA=="
        asyncio.run(test_multiple_accesses(test_url, num_sessions=10))
    except Exception as e:
        logging.error(f"Error running test_multiple_accesses: {e}")
