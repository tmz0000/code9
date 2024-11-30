import asyncio
from playwright.async_api import async_playwright
import logging
import os

logging.basicConfig(level=logging.INFO)

async def fetch_new_stream_url(channel_page_url):
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            playlist_urls = []

            async def handle_route(route, request):
                request_url = request.url

                if ".m3u8?" in request_url:
                    playlist_urls.append(request_url)
                    logging.info(f"Found potential playlist URL: {request_url}")

                await route.continue_()

            await page.route("**/*", handle_route)

            try:
                await page.goto(channel_page_url, wait_until='domcontentloaded', timeout=60000)
            except Exception as e:
                logging.error(f"Error loading page {channel_page_url}: {e}")
                await browser.close()
                return None

            await asyncio.sleep(10)  # Wait for 10 seconds to capture the playlist URL
            await browser.close()

            # Return the first valid URL or None if the list is empty
            return playlist_urls[0] if playlist_urls else None

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
        "01": "https://adult-tv-channels.com/redlight-hd-online/",
        "02": "https://adult-tv-channels.com/dorcel-tv-online/",
        "03": "https://adult-tv-channels.com/penthouse-passion-online/",
        "04": "https://adult-tv-channels.com/penthouse-passion-tv-online/",
        "05": "https://adult-tv-channels.com/vivid-tv-online/",
        "06": "https://adult-tv-channels.com/eroxxx-hd-tv-online/",
        "07": "https://adult-tv-channels.com/extasy-tv-online/",
        "08": "https://adult-tv-channels.com/pink-erotic-tv-online/",
        "09": "https://adult-tv-channels.com/private-tv-online/",
        "10": "http://hochu.tv/babes-tv.html",
        "11": "http://sweet-tv.net/babes-tv.html",
        "12": "https://adult-tv-channels.click/vixen/",
        "13": "https://adult-tv-channels.com/ox-ax-tv-online/",
        "14": "https://adult-tv-channels.com/evil-angel-tv-online/"
    }
    await update_m3u_file(m3u_path, channel_updates)


if __name__ == "__main__":
    asyncio.run(main())
