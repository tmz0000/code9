import pyppeteer
import asyncio
import logging
import os
import re

logging.basicConfig(level=logging.INFO)

async def fetch_new_stream_url(channel_page_url):
    try:
        browser = await pyppeteer.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--no-first-run',
                '--no-zygote',
                '--single-process',
                '--disable-gpu',
            ]
        )
        page = await browser.newPage()

        client = await page.target.createCDPSession()
        await client.send("Fetch.enable", {"patterns": [{"urlPattern": "*"}]})

        playlist_url = None

        async def handle_request(event):
            nonlocal playlist_url
            request_id = event.get("requestId")
            request_url = event.get("request", {}).get("url", "")

            block_patterns = ["start_scriptBus", "scriptBus", "disable-devtool", "disable-adblock", "adManager"]
            for pattern in block_patterns:
                if pattern.lower() in request_url.lower():
                    logging.info(f"Blocked script due to pattern '{pattern}': {request_url}")
                    await client.send("Fetch.failRequest", {"requestId": request_id, "errorReason": "BlockedByClient"})
                    return

            if ".m3u8?" in request_url:
                playlist_url = request_url
                logging.info(f"Captured playlist URL: {playlist_url}")

            await client.send("Fetch.continueRequest", {"requestId": request_id})

        client.on("Fetch.requestPaused", lambda event: asyncio.create_task(handle_request(event)))

        try:
            await page.goto(channel_page_url, {'waitUntil': 'networkidle2', 'timeout': 30000})
        except Exception as e:
            logging.error(f"Error loading page {channel_page_url}: {e}")
            await browser.close()
            return None

        # Wait dynamically for the playlist URL
        max_wait_time = 10  # seconds
        waited_time = 0
        while not playlist_url and waited_time < max_wait_time:
            await asyncio.sleep(1)
            waited_time += 1

        await browser.close()

        if playlist_url and ".m3u8?" in playlist_url:
            logging.info(f"Found valid playlist URL: {playlist_url}")
        else:
            logging.warning(f"No valid playlist URL found for {channel_page_url}")
        return playlist_url

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
        "10": "https://fuckflix.click/vixen/",
        "11": "https://freeshot.live/live-tv/vixen/848",
        "12": "https://adult-tv-channels.click/vixen/",
        "13": "https://adult-tv-channels.com/ox-ax-tv-online/",
        "14": "https://adult-tv-channels.com/evil-angel-tv-online/"
    }
    await update_m3u_file(m3u_path, channel_updates)


if __name__ == "__main__":
    asyncio.run(main())
