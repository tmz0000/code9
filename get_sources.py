import asyncio
from playwright.async_api import async_playwright
import logging
import os
import requests
import urllib3
import random
import re

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
                    headless=True,
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
                        '--disable-popup-blocking'
                    ]
                )
                
                # Create context with realistic browser settings
                context = await browser.new_context(
                    user_agent=random.choice(USER_AGENTS),
                    viewport={'width': 1920, 'height': 1080},
                    ignore_https_errors=True,
                    java_script_enabled=True,
                    permissions=['camera', 'microphone'],
                    extra_http_headers={
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.5',
                        'Accept-Encoding': 'gzip, deflate',
                        'DNT': '1',
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1',
                        'Referer': 'https://www.google.com/'
                    }
                )
                
                page = await context.new_page()
                
                # More selective resource blocking - allow important resources
                await page.route("**/*", lambda route, request: (
                    route.abort() if request.resource_type in ["image", "font"] 
                    and ".m3u8" not in request.url.lower()
                    and ".mp4" not in request.url.lower()
                    and ".ts" not in request.url.lower()
                    else route.continue_()
                ))

                playlist_urls = []
                all_network_requests = []

                # Capture ALL network requests, not just m3u8 routes
                async def handle_request(request):
                    url = request.url
                    all_network_requests.append(url)
                    
                    # More comprehensive m3u8 detection
                    if any(pattern in url.lower() for pattern in ['.m3u8', 'playlist', 'manifest', 'stream']):
                        if '.m3u8' in url.lower() or 'playlist' in url.lower():
                            playlist_urls.append(url)
                            logging.info(f"Found potential playlist URL: {url}")

                async def handle_response(response):
                    url = response.url
                    # Check response content type for streaming content
                    try:
                        content_type = response.headers.get('content-type', '').lower()
                        if any(ct in content_type for ct in ['application/vnd.apple.mpegurl', 'video/', 'application/x-mpegurl']):
                            if url not in playlist_urls:
                                playlist_urls.append(url)
                                logging.info(f"Found playlist URL via content-type: {url}")
                    except:
                        pass

                # Listen to all network activity
                page.on("request", handle_request)
                page.on("response", handle_response)

                # Also use route interception as backup
                async def handle_route(route, request):
                    request_url = request.url
                    if ".m3u8" in request_url.lower() or "playlist" in request_url.lower():
                        if request_url not in playlist_urls:
                            playlist_urls.append(request_url)
                            logging.info(f"Found potential playlist URL via route: {request_url}")
                    await route.continue_()

                await page.route("**/*", handle_route)

                try:
                    # Navigate to page with longer timeout
                    await page.goto(
                        channel_page_url, 
                        wait_until='networkidle',  # Wait for network activity to settle
                        timeout=90000  # Increased timeout
                    )
                    
                    # Wait for initial page load
                    await asyncio.sleep(5)
                    
                    # More aggressive popup handling
                    popup_selectors = [
                        '[class*="close"]', '[class*="dismiss"]', '[class*="modal-close"]',
                        '[id*="close"]', '[aria-label="Close"]', '.popup-close',
                        'button[title="Close"]', '[data-dismiss="modal"]',
                        '.close', '#close', '.modal-close', '.overlay-close',
                        '[onclick*="close"]', '[onclick*="hide"]'
                    ]
                    
                    for selector in popup_selectors:
                        try:
                            elements = await page.query_selector_all(selector)
                            for element in elements:
                                try:
                                    if await element.is_visible():
                                        await element.click(timeout=2000)
                                        await asyncio.sleep(1)
                                        logging.info(f"Closed popup with selector: {selector}")
                                except:
                                    continue
                        except:
                            continue
                    
                    # Multiple interaction attempts
                    interaction_attempts = [
                        # Scroll to trigger lazy loading
                        lambda: page.evaluate("window.scrollTo(0, document.body.scrollHeight)"),
                        lambda: asyncio.sleep(3),
                        
                        # Try clicking various play elements
                        lambda: click_elements(page, [
                            'button[class*="play"]', '.play-button', '[aria-label*="play" i]',
                            'video', '.video-player', '[class*="player"]', '.player',
                            '[id*="play"]', '.play', '#play', 'button[title*="play" i]',
                            '.video-js', '.vjs-big-play-button'
                        ]),
                        
                        # Wait and scroll again
                        lambda: asyncio.sleep(3),
                        lambda: page.evaluate("window.scrollTo(0, 0)"),
                        lambda: asyncio.sleep(2),
                        
                        # Try clicking anywhere that might trigger video loading
                        lambda: click_elements(page, [
                            'iframe', '.embed', '[class*="embed"]', '[class*="video"]',
                            '.stream', '[class*="stream"]', '.live', '[class*="live"]'
                        ]),
                        
                        # Final wait for any delayed requests
                        lambda: asyncio.sleep(8)
                    ]
                    
                    for action in interaction_attempts:
                        try:
                            await action()
                        except Exception as e:
                            logging.debug(f"Interaction failed: {e}")
                    
                    # Check for m3u8 URLs in page source as last resort
                    try:
                        page_content = await page.content()
                        m3u8_matches = re.findall(r'https?://[^\s<>"\']+\.m3u8[^\s<>"\']*', page_content, re.IGNORECASE)
                        for match in m3u8_matches:
                            if match not in playlist_urls:
                                playlist_urls.append(match)
                                logging.info(f"Found m3u8 URL in page source: {match}")
                    except Exception as e:
                        logging.debug(f"Failed to search page source: {e}")
                    
                    # Also check all collected network requests for any missed m3u8 URLs
                    for req_url in all_network_requests:
                        if '.m3u8' in req_url.lower() and req_url not in playlist_urls:
                            playlist_urls.append(req_url)
                            logging.info(f"Found m3u8 URL from network logs: {req_url}")
                    
                    # If still no URLs found, try refreshing once more
                    if not playlist_urls and attempt == 0:
                        logging.info("No m3u8 URLs found, trying page refresh...")
                        await page.reload(wait_until='networkidle', timeout=90000)
                        await asyncio.sleep(8)

                except Exception as e:
                    logging.error(f"Error loading page {channel_page_url} on attempt {attempt + 1}: {e}")
                    await browser.close()
                    continue

                await browser.close()

                # Validate m3u8 URLs with more comprehensive checking
                for url in playlist_urls:
                    if await validate_m3u8_url(url):
                        logging.info(f"Valid playlist URL: {url}")
                        return url

        except Exception as e:
            logging.error(f"Attempt {attempt + 1} failed for {channel_page_url}: {e}")

        if attempt < retries - 1:
            wait_time = (attempt + 1) * 8  # Longer backoff
            logging.warning(f"Retrying {channel_page_url} ({attempt + 1}/{retries}) after {wait_time}s...")
            await asyncio.sleep(wait_time)

    logging.error(f"Failed to fetch stream URL for {channel_page_url} after {retries} attempts")
    return None

async def click_elements(page, selectors):
    """Helper function to click elements with various selectors"""
    for selector in selectors:
        try:
            elements = await page.query_selector_all(selector)
            for element in elements:
                try:
                    if await element.is_visible():
                        await element.click(timeout=3000)
                        await asyncio.sleep(2)
                        logging.info(f"Clicked element: {selector}")
                        return True
                except:
                    continue
        except:
            continue
    return False

async def validate_m3u8_url(url):
    """Validate m3u8 URL with comprehensive checking"""
    try:
        # First try HEAD request
        response = requests.head(url, timeout=20, verify=False, allow_redirects=True, 
                               headers={'User-Agent': random.choice(USER_AGENTS)})
        
        if response.status_code in [200, 302, 301]:
            return True
            
        # If HEAD fails, try GET with limited content
        response = requests.get(url, timeout=20, verify=False, stream=True,
                              headers={'User-Agent': random.choice(USER_AGENTS)})
        
        if response.status_code in [200, 302, 301]:
            # Try to read a small chunk to verify it's actually a playlist
            try:
                chunk = next(response.iter_content(chunk_size=2048), b'')
                # Check if it looks like an m3u8 playlist
                if b'#EXTM3U' in chunk or b'#EXT-X-' in chunk or b'.ts' in chunk:
                    return True
            except:
                pass
            return True
        
        logging.warning(f"Invalid playlist URL (status {response.status_code}): {url}")
        return False
        
    except requests.exceptions.RequestException as e:
        logging.error(f"Error validating URL {url}: {e}")
        return False

# Update M3U file (same as before but with improved logging)
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

        # Process channels with smaller batches and longer delays for difficult sites
        batch_size = 2  # Reduced batch size
        fetch_results = []
        
        for i in range(0, len(tasks), batch_size):
            batch = tasks[i:i + batch_size]
            logging.info(f"Processing batch {i//batch_size + 1}/{(len(tasks) + batch_size - 1)//batch_size}")
            
            batch_results = await asyncio.gather(*[fetch_new_stream_url(task[2]) for task in batch])
            fetch_results.extend(batch_results)
            
            # Longer delay between batches
            if i + batch_size < len(tasks):
                await asyncio.sleep(5)

        # Update URLs in the lines
        for idx, result in enumerate(fetch_results):
            channel_name = tasks[idx][1].split(',')[1] if ',' in tasks[idx][1] else 'channel'
            if result:
                logging.info(f"Updated {channel_name} with new URL: {result}")
                lines[tasks[idx][0]] = result + "\n"
            else:
                logging.error(f"Failed to fetch stream URL for {channel_name}")

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
