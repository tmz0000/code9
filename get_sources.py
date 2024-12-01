import asyncio
from playwright.async_api import async_playwright
import logging
import os
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logging.basicConfig(level=logging.INFO)

async def fetch_new_stream_url(channel_info):
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            playlist_urls = []

            async def handle_route(route, request):
                request_url = request.url

                if ".m3u8" in request_url:
                    playlist_urls.append(request_url)
                    logging.info(f"Found potential playlist URL: {request_url}")

                await route.continue_()

            await page.route("**/*", handle_route)

            try:
                await page.goto(channel_info["url"], wait_until='domcontentloaded', timeout=2000)
            except Exception as e:
                logging.error(f"Error loading page {channel_info['url']}: {e}")
                await browser.close()
                return None

            await asyncio.sleep(10)  # Wait for 10 seconds to capture the playlist URL

            if channel_info.get("hold_session", False):
                await page.reload()

            await browser.close()

            # Validate potential m3u8 URLs
            valid_url = None
            for url in playlist_urls:
                try:
                    response = requests.head(url, timeout=30, verify=False)
                    if response.status_code == 200:
                        logging.info(f"Valid playlist URL: {url}")
                        valid_url = url
                        break
                    else:
                        logging.warning(f"Invalid playlist URL: {url}")
                except requests.exceptions.RequestException as e:
                    logging.error(f"Error validating URL {url}: {e}")

            if valid_url:
                return valid_url
            else:
                logging.error(f"No valid playlist URL found for {channel_info['url']}")
                return None

    except Exception as e:
        logging.error(f"Failed to fetch stream URL: {e}")
        return None


async def update_m3u_file(m3u_path, channel_updates):
    if not os.path.exists(m3u_path):
        logging.error(f"File not found: {m3u_path}")
        return

    try:
        with open(m3u_path, 'r') as file:
            lines = file.readlines()

        updated_lines = []
        i = 0
        while i < len(lines):
            line = lines[i]
            if line.startswith('#EXTINF:') and 'group-title="NEW-XXX"' in line:
                channel_info = line.strip()
                channel_url = lines[i + 1].strip()
                tvg_id = channel_info.split('tvg-id="')[1].split('"')[0]
                if tvg_id in channel_updates:
                    new_url = await fetch_new_stream_url(channel_updates[tvg_id])
                    if new_url:
                        channel_url = new_url
                        logging.info(f"Updated tvg-id={tvg_id} with new URL: {new_url}")
                    else:
                        logging.error(f"Failed to fetch stream URL for {tvg_id}")
                updated_lines.append(f"{channel_info}\n")
                updated_lines.append(f"{channel_url}\n")
                i += 2
            else:
                updated_lines.append(line)
                i += 1

        with open(m3u_path, 'w') as file:
            file.writelines(updated_lines)

        logging.info(f"Successfully updated M3U file: {m3u_path}")

    except Exception as e:
        logging.error(f"Failed to update M3U file: {e}")


async def main():
    m3u_path = 's18.m3u'
    channel_updates = {
        "01": {
            "url": "https://adult-tv-channels.com/redlight-hd-online/",
            "hold_session": False
        },
        "02": {
            "url": "https://adult-tv-channels.com/dorcel-tv-online/",
            "hold_session": False
        },
        "03": {
            "url": "https://adult-tv-channels.com/penthouse-passion-online/",
            "hold_session": False
        },
        "04": {
            "url": "https://adult-tv-channels.com/penthouse-passion-tv-online/",
            "hold_session": False
        },
        "05": {
            "url": "https://adult-tv-channels.com/vivid-tv-online/",
            "hold_session": False
        },
        "06": {
            "url": "https://adult-tv-channels.com/eroxxx-hd-tv-online/",
            "hold_session": False
        },
        "07": {
            "url": "https://adult-tv-channels.com/extasy-tv-online/",
            "hold_session": False
        },
        "08": {
            "url": "https://adult-tv-channels.com/pink-erotic-tv-online/",
            "hold_session": False
        },
        "09": {
            "url": "https://adult-tv-channels.com/private-tv-online/",
            "hold_session": False
        },
        "10": {
            "url": "http://hochu.tv/babes-tv.html",
            "hold_session": True
        },
        "11": {
            "url": "http://sweet-tv.net/babes-tv.html",
            "hold_session": False
        },
        "12": {
            "url": "https://adult-tv-channels.click/vixen/",
            "hold_session": False
        },
        "13": {
            "url": "https://adult-tv-channels.com/ox-ax-tv-online/",
            "hold_session": False
        },
        "14": {
            "url": "https://adult-tv-channels.com/evil-angel-tv-online/",
            "hold_session": False
        }
    }
    await update_m3u_file(m3u_path, channel_updates)


if __name__ == "__main__":
    asyncio.run(main())
