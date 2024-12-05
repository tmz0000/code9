import asyncio
from playwright.async_api import async_playwright
import logging
import os
import requests
import urllib3
import aiohttp
import re

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
    async def test_multiple_accesses(m3u8_url, num_sessions=10):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
        "X-Forwarded-For": "86.62.30.103",  # UK IP address
        "X-GeoIP-Country-Code": "GB",  # UK country code
        "X-GeoIP-Region": "London",    # UK region
        "X-GeoIP-City": "London",      # UK city
        "X-GeoIP-Postal-Code": "EC1A", # UK postal code
        "X-GeoIP-Time-Zone": "Europe/London"  # UK timezone
    }

    async def access_m3u8(session, url, session_id):
        try:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    m3u8_contents = await response.text()
                    stream_details = parse_m3u8(m3u8_contents)
                    logging.info(f"[Session {session_id}] Successfully accessed {url}")
                    return stream_details
                else:
                    logging.warning(f"[Session {session_id}] Failed with status {response.status}")
                    return None
        except Exception as e:
            logging.error(f"[Session {session_id}] Error accessing {url}: {e}")
            return None

    def parse_m3u8(m3u8_contents):
        stream_details = []
        lines = m3u8_contents.splitlines()
        for line in lines:
            if line.startswith("#EXT-X-STREAM-INF"):
                match = re.search(r"BANDWIDTH=(\d+),RESOLUTION=(\d+x\d+)", line)
                if match:
                    bitrate = int(match.group(1)) // 1000  # Convert to kbps
                    resolution = match.group(2)
                    stream_details.append({"bitrate": bitrate, "resolution": resolution})
        return stream_details

    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
        tasks = [access_m3u8(session, m3u8_url, i + 1) for i in range(num_sessions)]
        results = await asyncio.gather(*tasks)

    successful_accesses = sum(1 for result in results if result)
    logging.info(f"Total successful accesses: {successful_accesses}/{num_sessions}")

    # Print stream details
    for i, result in enumerate(results):
        if result:
            logging.info(f"[Session {i+1}] Stream details:")
            for stream in result:
                logging.info(f"  Bitrate: {stream['bitrate']} kbps, Resolution: {stream['resolution']}")

    return successful_accesses


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logging.error(f"Error running main: {e}")

    try:
        test_url = "http://rso.uspeh.sbs/va2VuPVtzdGJfdG9rZW5dIiwidWZ0IjoiMiIsInVmcCI6IjgwMzAiLCJzdHAiOiIxIiwiYWRsIjoiMTQiLCJsIjoiMDc3NjA4NjQiLCJwIjoiMDc3NjA4NjQ4NGVlNDg2NSIsImMiOiI0MjAiLCJ0IjoiMmE4MjhlYjJkNmZmOTUyZDg2OTU3OTQ4OTA5ZDUzNmEiLCJkIjoiMTYzMDg0IiwiciI6IjE2NjM1NiIsIm0iOiJ0diIsImR0IjoiMCJ9eyJ1IjoiaHR0cDovLzE5NS4yMTEuMjcuMTQ5Ojg4NjgvODAzMC9pbmRleC5tM3U4P3R/index.m3u8"
        asyncio.run(test_multiple_accesses(test_url, num_sessions=10))
    except Exception as e:
        logging.error(f"Error running test_multiple_accesses: {e}")
