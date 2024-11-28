import pyppeteer
import asyncio
import logging

logging.basicConfig(level=logging.INFO)

async def fetch_new_stream_url(channel_page_url):
    try:
        # Launch browser in headless mode
        browser = await pyppeteer.launch(headless=True)
        page = await browser.newPage()

        # Enable request interception
        await page.setRequestInterception(True)

        # Intercept requests and capture the playlist URL
        playlist_url = None

        async def handle_request(request):
            nonlocal playlist_url
            if ".m3u8?" in request.url:
                playlist_url = request.url
            await request.continue_()  # Continue the request

        page.on('request', lambda req: asyncio.create_task(handle_request(req)))

        # Navigate to the channel page
        await page.goto(channel_page_url, {'waitUntil': 'networkidle2'})

        # Wait for some time to capture requests
        await asyncio.sleep(5)

        # Close the browser
        await browser.close()

        if playlist_url:
            logging.info(f"Found playlist URL: {playlist_url}")
        else:
            logging.warning(f"No playlist URL found for {channel_page_url}")

        return playlist_url

    except Exception as e:
        logging.error(f"Failed to fetch stream URL: {e}")
        return None


async def update_m3u_file(m3u_path, channel_updates):
    try:
        with open(m3u_path, 'r') as file:
            lines = file.readlines()

        with open(m3u_path, 'w') as file:
            i = 0
            while i < len(lines):
                try:
                    line = lines[i]
                    if line.startswith('#EXTINF:') and 'group-title="NEW-XXX"' in line:
                        channel_info = line.strip()
                        channel_url = lines[i + 1].strip()
                        tvg_id = channel_info.split('tvg-id="')[1].split('"')[0]
                        if tvg_id in channel_updates:
                            try:
                                new_url = await fetch_new_stream_url(channel_updates[tvg_id])
                            except Exception as e:
                                logging.error(f"Failed to fetch new URL for tvg-id={tvg_id}: {e}")
                                new_url = None
                            if new_url:
                                channel_url = new_url
                                print(f"Updating tvg-id={tvg_id} with new URL: {new_url}")
                                logging.info(f"Updated tvg-id={tvg_id} with new URL: {new_url}")
                            file.write(f"{channel_info}\n{channel_url}\n")
                            i += 2
                        else:
                            file.write(f"{channel_info}\n{channel_url}\n")
                            i += 2
                    else:
                        file.write(line)
                        i += 1
                except Exception as e:
                    logging.error(f"Exception occurred at line {i}: {e}")
                    i += 1  # Increment to avoid infinite loop
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
