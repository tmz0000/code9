import asyncio
from playwright.async_api import async_playwright
import logging
import os
import requests
import urllib3
import random

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logging.basicConfig(level=logging.INFO)

# User agents to rotate for better stealth
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
]

# Function to fetch and validate m3u8 URL with retries
async def fetch_new_stream_url(channel_page_url, retries=3):
    for attempt in range(retries):
        try:
            async with async_playwright() as p:
                # Launch browser with stealth settings
                browser = await p.chromium.launch(
                    headless=True,  # Changed to True for better performance
                    args=[
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-accelerated-2d-canvas',
                        '--no-first-run',
                        '--no-zygote',
                        '--disable-gpu',
                        '--disable-extensions',
                        '--disable-background-timer-throttling',
                        '--disable-backgrounding-occluded-windows',
                        '--disable-renderer-backgrounding',
                        '--disable-features=TranslateUI',
                        '--disable-ipc-flooding-protection',
                        '--disable-blink-features=AutomationControlled',
                        '--disable-popup-blocking'  # Important for popup-heavy sites
                    ]
                )
                
                # Create context with realistic browser settings
                context = await browser.new_context(
                    user_agent=random.choice(USER_AGENTS),
                    viewport={'width': 1920, 'height': 1080},
                    ignore_https_errors=True,
                    java_script_enabled=True,
                    permissions=['camera', 'microphone'],  # Some adult sites check for permissions
                    extra_http_headers={
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.5',
                        'Accept-Encoding': 'gzip, deflate',
                        'DNT': '1',
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1',
                    }
                )
                
                page = await context.new_page()
                
                # Block unnecessary resources to speed up loading
                await page.route("**/*", lambda route, request: (
                    route.abort() if request.resource_type in ["image", "stylesheet", "font", "media"] 
                    and ".m3u8" not in request.url
                    else route.continue_()
                ))

                playlist_urls = []

                # Capture all .m3u8 requests
                async def handle_route(route, request):
                    request_url = request.url
                    if ".m3u8" in request_url:
                        playlist_urls.append(request_url)
                        logging.info(f"Found potential playlist URL: {request_url}")
                    await route.continue_()

                await page.route("**/*.m3u8*", handle_route)

                try:
                    # Extended timeout and different wait strategies
                    await page.goto(
                        channel_page_url, 
                        wait_until='domcontentloaded',  # Changed from networkidle for faster loading
                        timeout=60000  # Increased timeout to 60 seconds
                    )
                    
                    # Wait for JavaScript to execute and load content
                    await asyncio.sleep(3)
                    
                    # Try to dismiss any popups/overlays
                    try:
                        # Common popup close selectors
                        popup_selectors = [
                            '[class*="close"]', '[class*="dismiss"]', '[class*="modal-close"]',
                            '[id*="close"]', '[aria-label="Close"]', '.popup-close',
                            'button[title="Close"]', '[data-dismiss="modal"]'
                        ]
                        
                        for selector in popup_selectors:
                            try:
                                await page.click(selector, timeout=2000)
                                await asyncio.sleep(1)
                                logging.info(f"Closed popup with selector: {selector}")
                                break
                            except:
                                continue
                    except Exception as e:
                        logging.debug(f"No popups to close or error closing: {e}")
                    
                    # Scroll down to trigger lazy loading
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await asyncio.sleep(2)
                    
                    # Look for play buttons or video elements and try to interact
                    try:
                        play_selectors = [
                            'button[class*="play"]', '.play-button', '[aria-label*="play"]',
                            'video', '.video-player', '[class*="player"]'
                        ]
                        
                        for selector in play_selectors:
                            try:
                                await page.click(selector, timeout=3000)
                                await asyncio.sleep(2)
                                logging.info(f"Clicked play element: {selector}")
                                break
                            except:
                                continue
                    except Exception as e:
                        logging.debug(f"No play buttons found or error clicking: {e}")
                    
                    # Additional wait for m3u8 URLs to be generated
                    await asyncio.sleep(5)
                    
                    # If no URLs found, try refreshing the page once
                    if not playlist_urls and attempt == 0:
                        logging.info("No m3u8 URLs found, trying page refresh...")
                        await page.reload(wait_until='domcontentloaded', timeout=60000)
                        await asyncio.sleep(5)

                except Exception as e:
                    logging.error(f"Error loading page {channel_page_url} on attempt {attempt + 1}: {e}")
                    await browser.close()
                    continue

                await browser.close()

                # Validate m3u8 URLs with more permissive validation
                for url in playlist_urls:
                    try:
                        # Try HEAD request first, then GET if it fails
                        response = requests.head(url, timeout=15, verify=False, allow_redirects=True)
                        if response.status_code not in [200, 302, 301]:
                            # Some servers don't support HEAD, try GET
                            response = requests.get(url, timeout=15, verify=False, stream=True)
                            # Read only first few bytes to avoid downloading entire file
                            next(response.iter_content(chunk_size=1024), None)
                        
                        if response.status_code in [200, 302, 301]:
                            logging.info(f"Valid playlist URL: {url}")
                            return url  # Return valid URL immediately
                        else:
                            logging.warning(f"Invalid playlist URL (status {response.status_code}): {url}")
                    except requests.exceptions.RequestException as e:
                        logging.error(f"Error validating URL {url}: {e}")

        except Exception as e:
            logging.error(f"Attempt {attempt + 1} failed for {channel_page_url}: {e}")

        if attempt < retries - 1:
            wait_time = (attempt + 1) * 5  # Progressive backoff
            logging.warning(f"Retrying {channel_page_url} ({attempt + 1}/{retries}) after {wait_time}s...")
            await asyncio.sleep(wait_time)

    logging.error(f"Failed to fetch stream URL for {channel_page_url} after {retries} attempts")
    return None


# Update M3U file
async def update_m3u_file(m3u_path, channel_updates):
    if not os.path.exists(m3u_path):
        logging.error(f"File not found: {m3u_path}")
        return

    try:
        with open(m3u_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()

        tasks = []

        for i, line in enumerate(lines):
            if line.startswith('#EXTINF:') and 'group-title="NEW-XXX"' in line:
                channel_info = line.strip()
                if i + 1 < len(lines):
                    channel_url = lines[i + 1].strip()
                    try:
                        tvg_id = channel_info.split('tvg-id="')[1].split('"')[0]
                        if tvg_id in channel_updates:
                            # Schedule fetching URL concurrently
                            tasks.append((i + 1, channel_info, channel_updates[tvg_id]))
                    except IndexError:
                        logging.warning(f"Could not extract tvg-id from: {channel_info}")

        # Process channels with some delay between batches to avoid overwhelming servers
        batch_size = 3
        fetch_results = []
        
        for i in range(0, len(tasks), batch_size):
            batch = tasks[i:i + batch_size]
            batch_results = await asyncio.gather(*[fetch_new_stream_url(task[2]) for task in batch])
            fetch_results.extend(batch_results)
            
            # Small delay between batches
            if i + batch_size < len(tasks):
                await asyncio.sleep(2)

        # Update URLs in the lines
        for idx, result in enumerate(fetch_results):
            if result:
                logging.info(f"Updated {tasks[idx][1].split(',')[1] if ',' in tasks[idx][1] else 'channel'} with new URL: {result}")
                lines[tasks[idx][0]] = result + "\n"
            else:
                logging.error(f"Failed to fetch stream URL for {tasks[idx][1].split(',')[1] if ',' in tasks[idx][1] else 'channel'}")

        # Write updated M3U file
        with open(m3u_path, 'w', encoding='utf-8') as file:
            file.writelines(lines)

        logging.info(f"Successfully updated M3U file: {m3u_path}")
        
        # Print summary
        successful = sum(1 for result in fetch_results if result)
        total = len(fetch_results)
        logging.info(f"Summary: {successful}/{total} channels updated successfully ({successful/total*100:.1f}%)")
        
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
        "11": "https://adult-tv-channels.com/evil-angel-tv-online/",
        "12": "https://www.pirilampo.tv/live-tv/nuart-tv.html/",
        "13": "https://www.pirilampo.tv/live-tv/vivid-red-hd.html/"
    }
    await update_m3u_file(m3u_path, channel_updates)


if __name__ == "__main__":
    asyncio.run(main())
