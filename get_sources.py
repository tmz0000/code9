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
                    headless=False,  # Changed to visible for debugging
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
                
                # REMOVED resource blocking - this was likely preventing m3u8 detection
                # The original script blocked too many resources
                
                playlist_urls = []
                all_network_requests = []

                # Enhanced request monitoring
                async def handle_request(request):
                    url = request.url
                    all_network_requests.append(url)
                    
                    # Log ALL requests for debugging
                    logging.debug(f"REQUEST: {request.resource_type} - {url}")
                    
                    # Capture ANY URL containing m3u8
                    if '.m3u8' in url.lower():
                        playlist_urls.append(url)
                        logging.info(f"🎯 FOUND M3U8 REQUEST: {url}")

                async def handle_response(response):
                    url = response.url
                    
                    # Log response details
                    logging.debug(f"RESPONSE: {response.status} - {response.request.resource_type} - {url}")
                    
                    # Check for m3u8 in URL
                    if '.m3u8' in url.lower() and url not in playlist_urls:
                        playlist_urls.append(url)
                        logging.info(f"🎯 FOUND M3U8 RESPONSE: {url}")
                    
                    # Check content-type headers
                    try:
                        content_type = response.headers.get('content-type', '').lower()
                        if any(ct in content_type for ct in ['mpegurl', 'x-mpegurl', 'vnd.apple.mpegurl']):
                            if url not in playlist_urls:
                                playlist_urls.append(url)
                                logging.info(f"🎯 FOUND M3U8 BY CONTENT-TYPE: {url}")
                    except:
                        pass

                # Listen to all network activity
                page.on("request", handle_request)
                page.on("response", handle_response)

                # Enhanced CDP session for lower-level network monitoring
                client = await context.new_cdp_session(page)
                await client.send('Network.enable')
                
                async def handle_cdp_request(params):
                    url = params.get('request', {}).get('url', '')
                    if '.m3u8' in url.lower() and url not in playlist_urls:
                        playlist_urls.append(url)
                        logging.info(f"🎯 CDP FOUND M3U8: {url}")
                
                client.on('Network.requestWillBeSent', handle_cdp_request)

                try:
                    # Navigate to page with much longer timeout
                    logging.info(f"🌐 Navigating to: {channel_page_url}")
                    await page.goto(
                        channel_page_url, 
                        wait_until='domcontentloaded',  # Changed from networkidle
                        timeout=120000  # 2 minutes
                    )
                    
                    # Wait for initial load
                    await asyncio.sleep(3)
                    
                    # Handle popups and overlays
                    await handle_popups(page)
                    
                    # Much more aggressive interaction strategy
                    await interact_with_page(page)
                    
                    # Wait longer for lazy-loaded content
                    logging.info("⏳ Waiting for streams to load...")
                    await asyncio.sleep(15)  # Increased wait time
                    
                    # Try to find and interact with iframes
                    await handle_iframes(page, playlist_urls)
                    
                    # Additional wait after iframe interactions
                    await asyncio.sleep(10)
                    
                    # Search page source more thoroughly
                    await search_page_source(page, playlist_urls)
                    
                    # Execute JavaScript to search for hidden m3u8 URLs
                    await execute_js_search(page, playlist_urls)
                    
                    # Final wait for any delayed requests
                    await asyncio.sleep(5)

                except Exception as e:
                    logging.error(f"❌ Error loading page {channel_page_url} on attempt {attempt + 1}: {e}")
                    await browser.close()
                    continue

                await client.detach()
                await browser.close()

                # Remove duplicates and log findings
                playlist_urls = list(dict.fromkeys(playlist_urls))  # Remove duplicates while preserving order
                
                logging.info(f"📊 Total unique m3u8 URLs found: {len(playlist_urls)}")
                for i, url in enumerate(playlist_urls, 1):
                    logging.info(f"  {i}. {url}")

                # Validate m3u8 URLs
                for url in playlist_urls:
                    if await validate_m3u8_url(url):
                        logging.info(f"✅ Valid playlist URL: {url}")
                        return url

        except Exception as e:
            logging.error(f"❌ Attempt {attempt + 1} failed for {channel_page_url}: {e}")

        if attempt < retries - 1:
            wait_time = (attempt + 1) * 10
            logging.warning(f"🔄 Retrying {channel_page_url} ({attempt + 1}/{retries}) after {wait_time}s...")
            await asyncio.sleep(wait_time)

    logging.error(f"❌ Failed to fetch stream URL for {channel_page_url} after {retries} attempts")
    return None

async def handle_popups(page):
    """Enhanced popup handling"""
    popup_selectors = [
        '[class*="close"]', '[class*="dismiss"]', '[class*="modal-close"]',
        '[id*="close"]', '[aria-label="Close"]', '.popup-close',
        'button[title="Close"]', '[data-dismiss="modal"]',
        '.close', '#close', '.modal-close', '.overlay-close',
        '[onclick*="close"]', '[onclick*="hide"]', '.btn-close',
        '[class*="overlay"]', '[class*="popup"]', '[class*="modal"]'
    ]
    
    for selector in popup_selectors:
        try:
            elements = await page.query_selector_all(selector)
            for element in elements:
                try:
                    if await element.is_visible():
                        await element.click(timeout=2000)
                        await asyncio.sleep(1)
                        logging.info(f"🚫 Closed popup: {selector}")
                except:
                    continue
        except:
            continue

async def interact_with_page(page):
    """Enhanced page interaction"""
    interactions = [
        # Scroll to trigger lazy loading
        lambda: page.evaluate("window.scrollTo(0, document.body.scrollHeight)"),
        lambda: asyncio.sleep(2),
        lambda: page.evaluate("window.scrollTo(0, 0)"),
        lambda: asyncio.sleep(2),
        
        # Try clicking play buttons and video elements
        lambda: click_elements(page, [
            'button[class*="play"]', '.play-button', '[aria-label*="play" i]',
            'video', '.video-player', '[class*="player"]', '.player',
            '[id*="play"]', '.play', '#play', 'button[title*="play" i]',
            '.video-js', '.vjs-big-play-button', '[class*="video"]',
            '.stream', '[class*="stream"]', '.live', '[class*="live"]'
        ]),
        
        # Hover over video areas
        lambda: hover_elements(page, ['video', '.video-player', '[class*="player"]']),
        
        # Try pressing space and enter keys
        lambda: page.keyboard.press('Space'),
        lambda: asyncio.sleep(1),
        lambda: page.keyboard.press('Enter'),
        lambda: asyncio.sleep(2),
    ]
    
    for action in interactions:
        try:
            await action()
        except Exception as e:
            logging.debug(f"Interaction failed: {e}")

async def handle_iframes(page, playlist_urls):
    """Handle iframe content"""
    try:
        iframes = await page.query_selector_all('iframe')
        logging.info(f"🖼️ Found {len(iframes)} iframes")
        
        for i, iframe in enumerate(iframes):
            try:
                # Get iframe src
                src = await iframe.get_attribute('src')
                if src:
                    logging.info(f"  Iframe {i+1}: {src}")
                    
                    # Try to access iframe content
                    frame = await iframe.content_frame()
                    if frame:
                        # Wait for frame to load
                        await asyncio.sleep(3)
                        
                        # Listen for network requests in iframe
                        async def iframe_request_handler(request):
                            url = request.url
                            if '.m3u8' in url.lower() and url not in playlist_urls:
                                playlist_urls.append(url)
                                logging.info(f"🎯 IFRAME M3U8: {url}")
                        
                        frame.on("request", iframe_request_handler)
                        
                        # Try interacting with iframe content
                        try:
                            await frame.click('video', timeout=3000)
                        except:
                            pass
                        
                        await asyncio.sleep(3)
                        
            except Exception as e:
                logging.debug(f"Iframe {i+1} error: {e}")
                
    except Exception as e:
        logging.error(f"Error handling iframes: {e}")

async def search_page_source(page, playlist_urls):
    """Search page source for m3u8 URLs"""
    try:
        content = await page.content()
        
        # Multiple regex patterns for m3u8 URLs
        patterns = [
            r'https?://[^\s<>"\']+\.m3u8[^\s<>"\']*',
            r'["\']([^"\']*\.m3u8[^"\']*)["\']',
            r'url[:\s]*["\']?([^"\']*\.m3u8[^"\']*)["\']?',
            r'src[:\s]*["\']?([^"\']*\.m3u8[^"\']*)["\']?'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                url = match if match.startswith('http') else match
                if url and url not in playlist_urls:
                    playlist_urls.append(url)
                    logging.info(f"🎯 PAGE SOURCE M3U8: {url}")
                    
    except Exception as e:
        logging.error(f"Error searching page source: {e}")

async def execute_js_search(page, playlist_urls):
    """Execute JavaScript to search for m3u8 URLs"""
    try:
        js_code = """
        () => {
            const urls = [];
            
            // Search all script tags
            document.querySelectorAll('script').forEach(script => {
                const text = script.textContent || script.innerText || '';
                const matches = text.match(/https?:\/\/[^\s<>"']+\.m3u8[^\s<>"']*/gi);
                if (matches) {
                    urls.push(...matches);
                }
            });
            
            // Search all elements with data attributes
            document.querySelectorAll('[data-src], [data-url], [data-stream]').forEach(el => {
                ['data-src', 'data-url', 'data-stream'].forEach(attr => {
                    const val = el.getAttribute(attr);
                    if (val && val.includes('.m3u8')) {
                        urls.push(val);
                    }
                });
            });
            
            // Search window object for common video player properties
            const searchProps = ['videoUrl', 'streamUrl', 'playlistUrl', 'hlsUrl', 'source'];
            searchProps.forEach(prop => {
                if (window[prop] && typeof window[prop] === 'string' && window[prop].includes('.m3u8')) {
                    urls.push(window[prop]);
                }
            });
            
            return [...new Set(urls)];
        }
        """
        
        js_urls = await page.evaluate(js_code)
        for url in js_urls:
            if url not in playlist_urls:
                playlist_urls.append(url)
                logging.info(f"🎯 JAVASCRIPT M3U8: {url}")
                
    except Exception as e:
        logging.error(f"Error executing JavaScript search: {e}")

async def click_elements(page, selectors):
    """Helper function to click elements with various selectors"""
    for selector in selectors:
        try:
            elements = await page.query_selector_all(selector)
            for element in elements:
                try:
                    if await element.is_visible():
                        await element.click(timeout=3000)
                        await asyncio.sleep(1)
                        logging.info(f"🖱️ Clicked: {selector}")
                        return True
                except:
                    continue
        except:
            continue
    return False

async def hover_elements(page, selectors):
    """Helper function to hover over elements"""
    for selector in selectors:
        try:
            elements = await page.query_selector_all(selector)
            for element in elements:
                try:
                    if await element.is_visible():
                        await element.hover(timeout=3000)
                        await asyncio.sleep(1)
                        logging.info(f"👆 Hovered: {selector}")
                        return True
                except:
                    continue
        except:
            continue
    return False

async def validate_m3u8_url(url):
    """Validate m3u8 URL with comprehensive checking"""
    try:
        # Skip obvious non-playlist URLs
        if any(skip in url.lower() for skip in ['ad', 'analytics', 'tracking']):
            return False
            
        # Must contain m3u8
        if '.m3u8' not in url.lower():
            return False
        
        # Try HEAD request first
        response = requests.head(url, timeout=15, verify=False, allow_redirects=True, 
                               headers={'User-Agent': random.choice(USER_AGENTS)})
        
        if response.status_code in [200, 302, 301]:
            return True
            
        # If HEAD fails, try GET
        response = requests.get(url, timeout=15, verify=False, stream=True,
                              headers={'User-Agent': random.choice(USER_AGENTS)})
        
        if response.status_code in [200, 302, 301]:
            # Verify it's actually a playlist
            try:
                chunk = next(response.iter_content(chunk_size=1024), b'')
                if b'#EXTM3U' in chunk or b'#EXT-X-' in chunk:
                    return True
                    
                # Sometimes m3u8 files don't start with standard headers
                if b'.ts' in chunk or b'.m4s' in chunk:
                    return True
                    
            except:
                pass
            return True
        
        return False
        
    except Exception as e:
        logging.debug(f"Validation error for {url}: {e}")
        return False

# Update M3U file (same as original but with better logging)
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
                            tasks.append((i + 1, channel_info, channel_updates[tvg_id]))
                    except IndexError:
                        logging.warning(f"Could not extract tvg-id from: {channel_info}")

        # Process channels one by one for better debugging
        fetch_results = []
        
        for idx, (line_idx, channel_info, url) in enumerate(tasks):
            channel_name = channel_info.split(',')[1] if ',' in channel_info else f'Channel {idx+1}'
            logging.info(f"🎬 Processing {channel_name} ({idx+1}/{len(tasks)})")
            
            result = await fetch_new_stream_url(url)
            fetch_results.append(result)
            
            if result:
                logging.info(f"✅ {channel_name}: {result}")
            else:
                logging.error(f"❌ {channel_name}: No stream found")
            
            # Delay between channels
            if idx < len(tasks) - 1:
                await asyncio.sleep(3)

        # Update URLs in the lines
        for idx, result in enumerate(fetch_results):
            if result:
                lines[tasks[idx][0]] = result + "\n"

        # Write updated M3U file
        with open(m3u_path, 'w', encoding='utf-8') as file:
            file.writelines(lines)

        logging.info(f"📁 Successfully updated M3U file: {m3u_path}")
        
        # Print summary
        successful = sum(1 for result in fetch_results if result)
        total = len(fetch_results)
        logging.info(f"📊 Summary: {successful}/{total} channels updated successfully ({successful/total*100:.1f}%)")
        
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
