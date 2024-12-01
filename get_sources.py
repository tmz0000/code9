import asyncio
from playwright.async_api import async_playwright
import logging
import os
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logging.basicConfig(level=logging.INFO)

# Function to fetch and validate m3u8 URL
async def fetch_new_stream_url(channel_page_url):
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)  # Headless for speed
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
                # Load the page quickly without waiting for unnecessary resources
                await page.goto(channel_page_url, wait_until='networkidle', timeout=20000)
            except Exception as e:
                logging.error(f"Error loading page {channel_page_url}: {e}")
                await browser.close()
                return None

            await browser.close()

            # Validate m3u8 URLs
            valid_url = None
            for url in playlist_urls:
                try:
                    response = requests.head(url, timeout=5, verify=False)
                    if response.status_code == 200:
                        logging.info(f"Valid playlist URL: {url}")
                        valid_url = url
                        break
                    else:
                        logging.warning(f"Invalid playlist URL: {url}")
                except requests.exceptions.RequestException as e:
                    logging.error(f"Error validating URL {url}: {e}")

            return valid_url
    except Exception as e:
        logging.error(f"Failed to fetch stream URL: {e}")
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


if __name__ == "__main__":
    asyncio.run(main())
