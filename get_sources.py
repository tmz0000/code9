import asyncio
from playwright.async_api import async_playwright
import logging
import os
import requests
import urllib3
import random
import re
import json

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logging.basicConfig(level=logging.INFO)

# More realistic user agents with recent versions
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0'
]

async def fetch_new_stream_url(channel_page_url, retries=3):
    for attempt in range(retries):
        try:
            async with async_playwright() as p:
                # FIXED: Use launch_persistent_context instead of launch + user-data-dir arg
                browser_args = [
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
                    '--disable-popup-blocking',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor',
                    '--enable-features=NetworkService,NetworkServiceLogging',
                    '--disable-default-apps',
                    '--no-default-browser-check',
                    '--disable-component-extensions-with-background-pages'
                ]
                
                # Use persistent context with user data directory
                user_data_dir = f"/tmp/chrome-user-data-{random.randint(1000, 9999)}"
                
                context = await p.chromium.launch_persistent_context(
                    user_data_dir=user_data_dir,
                    headless=False,  # Keep visible for debugging
                    args=browser_args,
                    user_agent=random.choice(USER_AGENTS),
                    viewport={'width': 1920, 'height': 1080},
                    ignore_https_errors=True,
                    java_script_enabled=True,
                    permissions=['camera', 'microphone', 'geolocation'],
                    geolocation={'latitude': 40.7128, 'longitude': -74.0060},
                    locale='en-US',
                    timezone_id='America/New_York',
                    extra_http_headers={
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                        'Accept-Language': 'en-US,en;q=0.9',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'DNT': '1',
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1',
                        'Sec-Fetch-Dest': 'document',
                        'Sec-Fetch-Mode': 'navigate',
                        'Sec-Fetch-Site': 'none',
                        'Sec-Fetch-User': '?1',
                        'Cache-Control': 'max-age=0',
                        'Referer': 'https://www.google.com/'
                    }
                )
                
                page = await context.new_page()
                
                # Advanced anti-detection measures
                await setup_anti_detection(page)
                
                playlist_urls = []

                # Enhanced request monitoring
                async def handle_request(request):
                    url = request.url
                    
                    # Capture ANY URL containing m3u8
                    if '.m3u8' in url.lower():
                        playlist_urls.append(url)
                        logging.info(f"🎯 FOUND M3U8 REQUEST: {url}")

                async def handle_response(response):
                    url = response.url
                    
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

                try:
                    # Navigate with realistic behavior
                    logging.info(f"🌐 Navigating to: {channel_page_url}")
                    
                    # First, visit a referrer page to look more natural
                    await page.goto('https://www.google.com/', wait_until='domcontentloaded', timeout=30000)
                    await asyncio.sleep(random.uniform(2, 4))
                    
                    # Now navigate to the target page
                    await page.goto(
                        channel_page_url, 
                        wait_until='domcontentloaded',
                        timeout=60000  # Reduced timeout
                    )
                    
                    # Simulate human-like behavior immediately after page load
                    await simulate_human_behavior(page)
                    
                    # Wait and handle popups
                    await asyncio.sleep(random.uniform(3, 5))
                    await handle_popups(page)
                    
                    # More realistic interaction pattern
                    await realistic_page_interaction(page)
                    
                    # Wait for streams to load with random intervals
                    logging.info("⏳ Waiting for streams to load...")
                    await asyncio.sleep(random.uniform(10, 15))  # Reduced wait time
                    
                    # Search page source thoroughly
                    await search_page_source(page, playlist_urls)
                    
                    # Execute JavaScript to search for hidden m3u8 URLs
                    await execute_advanced_js_search(page, playlist_urls)
                    
                    # Try to trigger video player initialization
                    await trigger_video_player(page)
                    
                    # Final wait with random timing
                    await asyncio.sleep(random.uniform(3, 6))  # Reduced wait time

                except Exception as e:
                    logging.error(f"❌ Error loading page {channel_page_url} on attempt {attempt + 1}: {e}")
                    await context.close()
                    continue

                await context.close()

                # Remove duplicates and validate
                playlist_urls = list(dict.fromkeys(playlist_urls))
                
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
            wait_time = random.uniform(5, 10) * (attempt + 1)  # Reduced retry delay
            logging.warning(f"🔄 Retrying {channel_page_url} ({attempt + 1}/{retries}) after {wait_time:.1f}s...")
            await asyncio.sleep(wait_time)

    logging.error(f"❌ Failed to fetch stream URL for {channel_page_url} after {retries} attempts")
    return None

async def setup_anti_detection(page):
    """Setup advanced anti-detection measures"""
    
    # Override navigator properties to look more human
    await page.add_init_script("""
        // Override the navigator.webdriver property
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined,
        });
        
        // Override the navigator.plugins property to look more realistic
        Object.defineProperty(navigator, 'plugins', {
            get: () => ({
                length: 5,
                0: { name: "Chrome PDF Plugin" },
                1: { name: "Chrome PDF Viewer" },
                2: { name: "Native Client" },
                3: { name: "Chromium PDF Plugin" },
                4: { name: "Microsoft Edge PDF Plugin" }
            })
        });
        
        // Override the navigator.languages property
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en']
        });
        
        // Override WebGL vendor and renderer
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {
            if (parameter === 37445) return 'Intel Inc.';
            if (parameter === 37446) return 'Intel Iris OpenGL Engine';
            return getParameter.call(this, parameter);
        };
        
        // Override screen properties to look more realistic
        Object.defineProperty(screen, 'colorDepth', {
            get: () => 24
        });
        
        Object.defineProperty(screen, 'pixelDepth', {
            get: () => 24
        });
        
        // Add some randomness to make it look more human
        const originalRandom = Math.random;
        Math.random = function() {
            return originalRandom() * 0.99 + 0.005;
        };
        
        // Override permission API
        if (navigator.permissions && navigator.permissions.query) {
            const originalQuery = navigator.permissions.query;
            navigator.permissions.query = function(parameters) {
                if (parameters.name === 'notifications') {
                    return Promise.resolve({ state: 'default' });
                }
                return originalQuery.call(this, parameters);
            };
        }
        
        // Hide automation indicators
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
    """)

async def simulate_human_behavior(page):
    """Simulate realistic human behavior patterns"""
    
    # Random mouse movements
    for _ in range(random.randint(1, 3)):  # Reduced iterations
        x = random.randint(100, 1800)
        y = random.randint(100, 1000)
        await page.mouse.move(x, y)
        await asyncio.sleep(random.uniform(0.2, 0.8))  # Faster movements
    
    # Random scrolling pattern
    for _ in range(random.randint(2, 4)):  # Reduced iterations
        scroll_amount = random.randint(200, 600)
        await page.evaluate(f"window.scrollBy(0, {scroll_amount})")
        await asyncio.sleep(random.uniform(0.5, 1.5))  # Faster scrolling
    
    # Scroll back to top
    await page.evaluate("window.scrollTo(0, 0)")
    await asyncio.sleep(random.uniform(0.5, 1))

async def handle_popups(page):
    """Enhanced popup handling with more selectors"""
    popup_selectors = [
        '[class*="close"]', '[class*="dismiss"]', '[class*="modal-close"]',
        '[id*="close"]', '[aria-label="Close"]', '.popup-close',
        'button[title="Close"]', '[data-dismiss="modal"]',
        '.close', '#close', '.modal-close', '.overlay-close',
        '[onclick*="close"]', '[onclick*="hide"]', '.btn-close',
        '[class*="overlay"]', '[class*="popup"]', '[class*="modal"]',
        'button:has-text("Accept")', 'button:has-text("OK")',
        'button:has-text("Continue")', '[class*="cookie"]',
        '[id*="cookie"]', '[class*="gdpr"]', '[class*="consent"]'
    ]
    
    await asyncio.sleep(1)  # Reduced wait time
    
    for selector in popup_selectors:
        try:
            elements = await page.query_selector_all(selector)
            for element in elements[:2]:  # Limit to first 2 elements
                try:
                    if await element.is_visible():
                        await element.click(timeout=2000)  # Reduced timeout
                        await asyncio.sleep(random.uniform(0.2, 0.8))
                        logging.info(f"🚫 Closed popup: {selector}")
                        break  # Exit after first successful click
                except:
                    continue
        except:
            continue

async def realistic_page_interaction(page):
    """More realistic and comprehensive page interaction"""
    
    # Wait a bit before starting interactions
    await asyncio.sleep(random.uniform(1, 2))
    
    # Try clicking play buttons and video elements
    await click_elements_realistic(page, [
        'button[class*="play"]', '.play-button', '[aria-label*="play" i]',
        'video', '.video-player', '[class*="player"]', '.player',
        '[id*="play"]', '.play', '#play', 'button[title*="play" i]',
        '.video-js', '.vjs-big-play-button', '[class*="video"]',
        '.stream', '[class*="stream"]', '.live', '[class*="live"]'
    ])

async def click_elements_realistic(page, selectors):
    """Realistic clicking with human-like delays"""
    for selector in selectors[:5]:  # Limit to first 5 selectors
        try:
            element = await page.query_selector(selector)
            if element and await element.is_visible():
                try:
                    await element.scroll_into_view_if_needed()
                    await asyncio.sleep(random.uniform(0.2, 0.5))
                    await element.hover()
                    await asyncio.sleep(random.uniform(0.1, 0.3))
                    await element.click(timeout=3000)
                    await asyncio.sleep(random.uniform(0.5, 1.5))
                    logging.info(f"🖱️ Clicked: {selector}")
                    return True
                except Exception as e:
                    logging.debug(f"Click failed for {selector}: {e}")
        except:
            continue
    return False

async def trigger_video_player(page):
    """Try to trigger video player initialization with various methods"""
    
    js_triggers = [
        # Dispatch events on video elements
        """
        document.querySelectorAll('video, [class*="player"], [class*="video"]').forEach(el => {
            ['click', 'play', 'loadstart'].forEach(eventType => {
                try {
                    el.dispatchEvent(new Event(eventType, {bubbles: true}));
                } catch(e) {}
            });
        });
        """,
        
        # Try common player methods
        """
        ['player', 'videoPlayer', 'jwplayer'].forEach(objName => {
            if (window[objName] && typeof window[objName].play === 'function') {
                try { window[objName].play(); } catch(e) {}
            }
        });
        """,
        
        # Trigger resize and scroll events
        """
        window.dispatchEvent(new Event('resize'));
        window.dispatchEvent(new Event('scroll'));
        """
    ]
    
    for js_code in js_triggers:
        try:
            await page.evaluate(js_code)
            await asyncio.sleep(random.uniform(1, 2))
        except Exception as e:
            logging.debug(f"JS trigger failed: {e}")

async def search_page_source(page, playlist_urls):
    """Enhanced page source search with better regex patterns"""
    try:
        content = await page.content()
        
        # Comprehensive regex patterns for m3u8 URLs
        patterns = [
            r'https?://[^\s<>"\'`]+\.m3u8[^\s<>"\'`]*',
            r'["\']([^"\']*\.m3u8[^"\']*)["\']',
            r'url[:\s]*["\']?([^"\']*\.m3u8[^"\']*)["\']?',
            r'src[:\s]*["\']?([^"\']*\.m3u8[^"\']*)["\']?'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                url = match if match.startswith('http') else match
                if url and url not in playlist_urls and '.m3u8' in url:
                    playlist_urls.append(url)
                    logging.info(f"🎯 PAGE SOURCE M3U8: {url}")
                    
    except Exception as e:
        logging.error(f"Error searching page source: {e}")

async def execute_advanced_js_search(page, playlist_urls):
    """Advanced JavaScript search for m3u8 URLs"""
    try:
        js_code = """
        () => {
            const urls = new Set();
            
            // Search all script tags
            document.querySelectorAll('script').forEach(script => {
                const text = script.textContent || script.innerText || '';
                const patterns = [
                    /https?:\/\/[^\s<>"'`]+\.m3u8[^\s<>"'`]*/gi,
                    /"([^"]*\.m3u8[^"]*)"/gi,
                    /'([^']*\.m3u8[^']*)'/gi
                ];
                
                patterns.forEach(pattern => {
                    let match;
                    while ((match = pattern.exec(text)) !== null) {
                        const url = match[1] || match[0];
                        if (url && url.includes('.m3u8')) {
                            urls.add(url);
                        }
                    }
                });
            });
            
            // Search data attributes
            ['data-src', 'data-url', 'data-stream', 'src', 'href'].forEach(attr => {
                document.querySelectorAll(`[${attr}]`).forEach(el => {
                    const val = el.getAttribute(attr);
                    if (val && val.includes('.m3u8')) {
                        urls.add(val);
                    }
                });
            });
            
            return Array.from(urls);
        }
        """
        
        js_urls = await page.evaluate(js_code)
        for url in js_urls:
            if url and url not in playlist_urls:
                playlist_urls.append(url)
                logging.info(f"🎯 JAVASCRIPT M3U8: {url}")
                
    except Exception as e:
        logging.error(f"Error executing JavaScript search: {e}")

async def validate_m3u8_url(url):
    """Enhanced m3u8 URL validation"""
    try:
        if '.m3u8' not in url.lower():
            return False
        
        session = requests.Session()
        session.headers.update({
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'application/vnd.apple.mpegurl, application/x-mpegurl, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Connection': 'keep-alive'
        })
        
        # Try HEAD request first
        try:
            response = session.head(url, timeout=10, verify=False, allow_redirects=True)
            if response.status_code in [200, 302, 301]:
                return True
        except:
            pass
            
        # If HEAD fails, try GET with limited content
        try:
            response = session.get(url, timeout=10, verify=False, stream=True)
            if response.status_code in [200, 302, 301]:
                return True
        except:
            pass
        
        return False
        
    except Exception as e:
        logging.debug(f"Validation error for {url}: {e}")
        return False

async def update_m3u_file(m3u_path, channel_updates):
    """Update M3U file with new stream URLs"""
    if not os.path.exists(m3u_path):
        logging.error(f"File not found: {m3u_path}")
        return

    try:
        with open(m3u_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()

        tasks = []
        for i, line in enumerate(lines):
            if line.startswith('#EXTINF:') and 'group-title="NEW-XXX"' in line:
                if i + 1 < len(lines):
                    try:
                        tvg_id = line.split('tvg-id="')[1].split('"')[0]
                        if tvg_id in channel_updates:
                            channel_name = line.split(',')[1].strip() if ',' in line else f'Channel {tvg_id}'
                            tasks.append((i + 1, channel_name, channel_updates[tvg_id]))
                    except IndexError:
                        continue

        # Process channels with better error handling
        successful_updates = 0
        
        for idx, (line_idx, channel_name, url) in enumerate(tasks):
            logging.info(f"🎬 Processing {channel_name} ({idx+1}/{len(tasks)})")
            
            try:
                result = await fetch_new_stream_url(url)
                if result:
                    lines[line_idx] = result + "\n"
                    successful_updates += 1
                    logging.info(f"✅ {channel_name}: Updated successfully")
                else:
                    logging.error(f"❌ {channel_name}: No stream found")
            except Exception as e:
                logging.error(f"❌ {channel_name}: Error - {e}")
            
            # Delay between channels
            if idx < len(tasks) - 1:
                delay = random.uniform(3, 8)
                logging.info(f"⏳ Waiting {delay:.1f}s before next channel...")
                await asyncio.sleep(delay)

        # Write updated M3U file
        with open(m3u_path, 'w', encoding='utf-8') as file:
            file.writelines(lines)

        logging.info(f"📁 M3U file updated: {m3u_path}")
        logging.info(f"📊 Summary: {successful_updates}/{len(tasks)} channels updated successfully")
        
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
