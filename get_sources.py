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
                # Launch browser with maximum stealth
                browser = await p.chromium.launch(
                    headless=False,  # Keep visible for debugging
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
                        '--disable-popup-blocking',
                        '--disable-web-security',
                        '--disable-features=VizDisplayCompositor',
                        '--user-data-dir=/tmp/chrome-user-data',
                        '--enable-features=NetworkService,NetworkServiceLogging',
                        '--disable-features=VizDisplayCompositor',
                        '--disable-default-apps',
                        '--no-default-browser-check',
                        '--disable-component-extensions-with-background-pages'
                    ]
                )
                
                # Create context with maximum human-like behavior
                context = await browser.new_context(
                    user_agent=random.choice(USER_AGENTS),
                    viewport={'width': 1920, 'height': 1080},
                    ignore_https_errors=True,
                    java_script_enabled=True,
                    permissions=['camera', 'microphone', 'geolocation'],
                    geolocation={'latitude': 40.7128, 'longitude': -74.0060},  # NYC coordinates
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
                    await page.goto('https://www.google.com/', wait_until='domcontentloaded')
                    await asyncio.sleep(random.uniform(2, 4))
                    
                    # Now navigate to the target page
                    await page.goto(
                        channel_page_url, 
                        wait_until='domcontentloaded',
                        timeout=120000
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
                    await asyncio.sleep(random.uniform(15, 25))
                    
                    # Search page source thoroughly
                    await search_page_source(page, playlist_urls)
                    
                    # Execute JavaScript to search for hidden m3u8 URLs
                    await execute_advanced_js_search(page, playlist_urls)
                    
                    # Try to trigger video player initialization
                    await trigger_video_player(page)
                    
                    # Final wait with random timing
                    await asyncio.sleep(random.uniform(5, 10))

                except Exception as e:
                    logging.error(f"❌ Error loading page {channel_page_url} on attempt {attempt + 1}: {e}")
                    await browser.close()
                    continue

                await browser.close()

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
            wait_time = random.uniform(10, 20) * (attempt + 1)
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
        
        // Override the navigator.plugins property
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5]
        });
        
        // Override the navigator.languages property
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en']
        });
        
        // Mock canvas fingerprinting
        const getContext = HTMLCanvasElement.prototype.getContext;
        HTMLCanvasElement.prototype.getContext = function(type) {
            if (type === '2d') {
                const context = getContext.call(this, type);
                const originalFillText = context.fillText;
                context.fillText = function() {
                    return originalFillText.apply(this, arguments);
                };
                return context;
            }
            return getContext.call(this, type);
        };
        
        // Mock screen properties
        Object.defineProperty(screen, 'colorDepth', {
            get: () => 24
        });
        
        // Mock timezone
        Date.prototype.getTimezoneOffset = function() {
            return 300; // EST timezone
        };
        
        // Add some randomness to make it look more human
        const originalRandom = Math.random;
        Math.random = function() {
            return originalRandom() * 0.99 + 0.005; // Avoid exact 0 or 1
        };
        
        // Override permission API
        const originalQuery = navigator.permissions.query;
        navigator.permissions.query = function(parameters) {
            return parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters);
        };
        
        // Mock battery API
        Object.defineProperty(navigator, 'getBattery', {
            get: () => () => Promise.resolve({
                charging: true,
                chargingTime: 0,
                dischargingTime: Infinity,
                level: 1
            })
        });
    """)

async def simulate_human_behavior(page):
    """Simulate realistic human behavior patterns"""
    
    # Random mouse movements
    for _ in range(random.randint(2, 5)):
        x = random.randint(100, 1800)
        y = random.randint(100, 1000)
        await page.mouse.move(x, y)
        await asyncio.sleep(random.uniform(0.5, 1.5))
    
    # Random scrolling pattern
    for _ in range(random.randint(3, 6)):
        scroll_amount = random.randint(200, 800)
        await page.evaluate(f"window.scrollBy(0, {scroll_amount})")
        await asyncio.sleep(random.uniform(1, 3))
    
    # Scroll back to top
    await page.evaluate("window.scrollTo(0, 0)")
    await asyncio.sleep(random.uniform(1, 2))

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
    
    await asyncio.sleep(2)  # Wait for popups to appear
    
    for selector in popup_selectors:
        try:
            elements = await page.query_selector_all(selector)
            for element in elements:
                try:
                    if await element.is_visible():
                        await element.click(timeout=3000)
                        await asyncio.sleep(random.uniform(0.5, 1.5))
                        logging.info(f"🚫 Closed popup: {selector}")
                except:
                    continue
        except:
            continue

async def realistic_page_interaction(page):
    """More realistic and comprehensive page interaction"""
    
    # Wait a bit before starting interactions
    await asyncio.sleep(random.uniform(2, 4))
    
    interactions = [
        # Realistic scrolling behavior
        lambda: page.evaluate("window.scrollTo({top: document.body.scrollHeight/4, behavior: 'smooth'})"),
        lambda: asyncio.sleep(random.uniform(2, 4)),
        lambda: page.evaluate("window.scrollTo({top: document.body.scrollHeight/2, behavior: 'smooth'})"),
        lambda: asyncio.sleep(random.uniform(2, 4)),
        lambda: page.evaluate("window.scrollTo({top: document.body.scrollHeight*3/4, behavior: 'smooth'})"),
        lambda: asyncio.sleep(random.uniform(2, 4)),
        lambda: page.evaluate("window.scrollTo({top: 0, behavior: 'smooth'})"),
        lambda: asyncio.sleep(random.uniform(1, 3)),
        
        # Try clicking various elements that might trigger video loading
        lambda: click_elements_realistic(page, [
            'button[class*="play"]', '.play-button', '[aria-label*="play" i]',
            'video', '.video-player', '[class*="player"]', '.player',
            '[id*="play"]', '.play', '#play', 'button[title*="play" i]',
            '.video-js', '.vjs-big-play-button', '[class*="video"]',
            '.stream', '[class*="stream"]', '.live', '[class*="live"]',
            '[data-play]', '[onclick*="play"]', '.btn-play',
            '.video-container', '.player-container', '[class*="channel"]'
        ]),
        
        # Hover interactions
        lambda: hover_elements_realistic(page, [
            'video', '.video-player', '[class*="player"]', '.stream',
            '[class*="stream"]', '.live', '[class*="live"]'
        ]),
        
        # Keyboard interactions with realistic timing
        lambda: page.keyboard.press('Space'),
        lambda: asyncio.sleep(random.uniform(1, 2)),
        lambda: page.keyboard.press('Enter'),
        lambda: asyncio.sleep(random.uniform(1, 3)),
        
        # Focus on different elements
        lambda: focus_elements(page, ['video', 'input', 'button']),
    ]
    
    for action in interactions:
        try:
            await action()
        except Exception as e:
            logging.debug(f"Interaction failed: {e}")

async def click_elements_realistic(page, selectors):
    """Realistic clicking with human-like delays"""
    for selector in selectors:
        try:
            elements = await page.query_selector_all(selector)
            for element in elements:
                try:
                    if await element.is_visible():
                        # Scroll element into view first
                        await element.scroll_into_view_if_needed()
                        await asyncio.sleep(random.uniform(0.5, 1))
                        
                        # Hover before clicking (human-like)
                        await element.hover()
                        await asyncio.sleep(random.uniform(0.2, 0.5))
                        
                        # Click with realistic timing
                        await element.click(timeout=5000)
                        await asyncio.sleep(random.uniform(1, 3))
                        logging.info(f"🖱️ Clicked: {selector}")
                        return True
                except Exception as e:
                    logging.debug(f"Click failed for {selector}: {e}")
                    continue
        except:
            continue
    return False

async def hover_elements_realistic(page, selectors):
    """Realistic hovering with human-like movement"""
    for selector in selectors:
        try:
            elements = await page.query_selector_all(selector)
            for element in elements:
                try:
                    if await element.is_visible():
                        await element.scroll_into_view_if_needed()
                        await asyncio.sleep(random.uniform(0.3, 0.7))
                        await element.hover()
                        await asyncio.sleep(random.uniform(1, 3))
                        logging.info(f"👆 Hovered: {selector}")
                        return True
                except:
                    continue
        except:
            continue
    return False

async def focus_elements(page, selectors):
    """Focus on elements to trigger events"""
    for selector in selectors:
        try:
            elements = await page.query_selector_all(selector)
            for element in elements:
                try:
                    if await element.is_visible():
                        await element.focus()
                        await asyncio.sleep(random.uniform(0.5, 1))
                        logging.debug(f"🎯 Focused: {selector}")
                        return True
                except:
                    continue
        except:
            continue
    return False

async def trigger_video_player(page):
    """Try to trigger video player initialization with various methods"""
    
    # Execute JavaScript to manually trigger video events
    js_triggers = [
        # Dispatch mouse events on video elements
        """
        document.querySelectorAll('video, [class*="player"], [class*="video"]').forEach(el => {
            ['mouseenter', 'mouseover', 'click', 'focus'].forEach(eventType => {
                try {
                    el.dispatchEvent(new Event(eventType, {bubbles: true}));
                } catch(e) {}
            });
        });
        """,
        
        # Try to call common video player methods
        """
        if (window.player && typeof window.player.play === 'function') {
            try { window.player.play(); } catch(e) {}
        }
        if (window.videoPlayer && typeof window.videoPlayer.play === 'function') {
            try { window.videoPlayer.play(); } catch(e) {}
        }
        if (window.jwplayer) {
            try { 
                const players = jwplayer().getPlaylist();
                if (players && players.length > 0) {
                    jwplayer().play();
                }
            } catch(e) {}
        }
        """,
        
        # Trigger resize and scroll events that might initialize lazy-loaded content
        """
        window.dispatchEvent(new Event('resize'));
        window.dispatchEvent(new Event('scroll'));
        document.dispatchEvent(new Event('DOMContentLoaded'));
        """,
        
        # Look for and trigger common streaming platform initialization
        """
        ['initPlayer', 'loadStream', 'startStream', 'playVideo'].forEach(methodName => {
            if (window[methodName] && typeof window[methodName] === 'function') {
                try { window[methodName](); } catch(e) {}
            }
        });
        """
    ]
    
    for js_code in js_triggers:
        try:
            await page.evaluate(js_code)
            await asyncio.sleep(random.uniform(2, 4))
        except Exception as e:
            logging.debug(f"JS trigger failed: {e}")

async def search_page_source(page, playlist_urls):
    """Enhanced page source search with better regex patterns"""
    try:
        content = await page.content()
        
        # Multiple comprehensive regex patterns for m3u8 URLs
        patterns = [
            r'https?://[^\s<>"\'`]+\.m3u8[^\s<>"\'`]*',
            r'["\']([^"\']*\.m3u8[^"\']*)["\']',
            r'url[:\s]*["\']?([^"\']*\.m3u8[^"\']*)["\']?',
            r'src[:\s]*["\']?([^"\']*\.m3u8[^"\']*)["\']?',
            r'source[:\s]*["\']?([^"\']*\.m3u8[^"\']*)["\']?',
            r'stream[:\s]*["\']?([^"\']*\.m3u8[^"\']*)["\']?',
            r'playlist[:\s]*["\']?([^"\']*\.m3u8[^"\']*)["\']?',
            r'hls[:\s]*["\']?([^"\']*\.m3u8[^"\']*)["\']?',
            r'data-src[=:\s]*["\']?([^"\']*\.m3u8[^"\']*)["\']?',
            r'data-url[=:\s]*["\']?([^"\']*\.m3u8[^"\']*)["\']?',
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
            
            // Search all script tags with improved regex
            document.querySelectorAll('script').forEach(script => {
                const text = script.textContent || script.innerText || '';
                const patterns = [
                    /https?:\/\/[^\s<>"'`]+\.m3u8[^\s<>"'`]*/gi,
                    /"([^"]*\.m3u8[^"]*)"/gi,
                    /'([^']*\.m3u8[^']*)'/gi,
                    /`([^`]*\.m3u8[^`]*)`/gi
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
            
            // Search all elements with various data attributes
            const dataAttrs = ['data-src', 'data-url', 'data-stream', 'data-playlist', 
                              'data-hls', 'data-source', 'src', 'href'];
            
            dataAttrs.forEach(attr => {
                document.querySelectorAll(`[${attr}]`).forEach(el => {
                    const val = el.getAttribute(attr);
                    if (val && val.includes('.m3u8')) {
                        urls.add(val);
                    }
                });
            });
            
            // Deep search in window object
            function searchObject(obj, path = 'window', maxDepth = 3) {
                if (maxDepth <= 0 || !obj || typeof obj !== 'object') return;
                
                try {
                    Object.keys(obj).forEach(key => {
                        try {
                            const value = obj[key];
                            if (typeof value === 'string' && value.includes('.m3u8')) {
                                urls.add(value);
                            } else if (typeof value === 'object' && value !== null) {
                                searchObject(value, `${path}.${key}`, maxDepth - 1);
                            }
                        } catch(e) {}
                    });
                } catch(e) {}
            }
            
            // Search common video player objects
            const videoObjects = ['player', 'videoPlayer', 'jwplayer', 'hlsPlayer', 
                                'streamPlayer', 'videojs', 'flowplayer'];
            
            videoObjects.forEach(objName => {
                if (window[objName]) {
                    searchObject(window[objName], objName, 2);
                }
            });
            
            // Search for URLs in localStorage and sessionStorage
            try {
                for (let i = 0; i < localStorage.length; i++) {
                    const key = localStorage.key(i);
                    const value = localStorage.getItem(key);
                    if (value && value.includes('.m3u8')) {
                        urls.add(value);
                    }
                }
            } catch(e) {}
            
            try {
                for (let i = 0; i < sessionStorage.length; i++) {
                    const key = sessionStorage.key(i);
                    const value = sessionStorage.getItem(key);
                    if (value && value.includes('.m3u8')) {
                        urls.add(value);
                    }
                }
            } catch(e) {}
            
            // Search in CSS content (sometimes URLs are hidden there)
            try {
                Array.from(document.styleSheets).forEach(sheet => {
                    try {
                        Array.from(sheet.cssRules).forEach(rule => {
                            const cssText = rule.cssText || '';
                            const matches = cssText.match(/url\(['"]*([^'"]+\.m3u8[^'"]*)['"]*\)/gi);
                            if (matches) {
                                matches.forEach(match => {
                                    const url = match.replace(/url\(['"]*([^'"]+)['"]*\)/, '$1');
                                    if (url.includes('.m3u8')) {
                                        urls.add(url);
                                    }
                                });
                            }
                        });
                    } catch(e) {}
                });
            } catch(e) {}
            
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
        # Skip obvious non-playlist URLs
        skip_keywords = ['ad', 'analytics', 'tracking', 'pixel', 'beacon', 'metric']
        if any(skip in url.lower() for skip in skip_keywords):
            return False
            
        # Must contain m3u8
        if '.m3u8' not in url.lower():
            return False
        
        # Create session with realistic headers
        session = requests.Session()
        session.headers.update({
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'application/vnd.apple.mpegurl, application/x-mpegurl, application/mpegurl, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Referer': 'https://www.google.com/'
        })
        
        # Try HEAD request first
        try:
            response = session.head(url, timeout=15, verify=False, allow_redirects=True)
            if response.status_code in [200, 302, 301]:
                return True
        except:
            pass
            
        # If HEAD fails, try GET
        try:
            response = session.get(url, timeout=15, verify=False, stream=True)
            
            if response.status_code in [200, 302, 301]:
                # Verify it's actually a playlist
                try:
                    chunk = next(response.iter_content(chunk_size=2048), b'')
                    content = chunk.decode('utf-8', errors='ignore').lower()
                    
                    # Check for HLS playlist markers
                    hls_markers = ['#extm3u', '#ext-x-', '#extinf', '.ts', '.m4s', '.mp4']
                    if any(marker in content for marker in hls_markers):
                        return True
                        
                    # Sometimes valid playlists don't have standard headers
                    if len(chunk) > 100:  # Has substantial content
                        return True
                        
                except:
                    pass
                return True
        except:
            pass
        
        return False
        
    except Exception as e:
        logging.debug(f"Validation error for {url}: {e}")
        return False

# Update M3U file function (unchanged)
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
            
            # Longer delay between channels to avoid rate limiting
            if idx < len(tasks) - 1:
                delay = random.uniform(5, 15)
                logging.info(f"⏳ Waiting {delay:.1f}s before next channel...")
                await asyncio.sleep(delay)

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

# Additional helper function for debugging specific sites
async def debug_specific_site(url, max_wait_time=60):
    """Debug a specific site with extended monitoring"""
    logging.info(f"🔍 DEBUG MODE: Analyzing {url}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,  # Always visible for debugging
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor',
                '--user-data-dir=/tmp/chrome-debug'
            ]
        )
        
        context = await browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            viewport={'width': 1920, 'height': 1080}
        )
        
        page = await context.new_page()
        await setup_anti_detection(page)
        
        # Enhanced logging for debugging
        all_requests = []
        all_responses = []
        
        async def log_request(request):
            all_requests.append({
                'url': request.url,
                'method': request.method,
                'resource_type': request.resource_type,
                'headers': dict(request.headers)
            })
            if '.m3u8' in request.url.lower():
                logging.info(f"🎯 REQUEST M3U8: {request.url}")
        
        async def log_response(response):
            all_responses.append({
                'url': response.url,
                'status': response.status,
                'headers': dict(response.headers)
            })
            if '.m3u8' in response.url.lower():
                logging.info(f"🎯 RESPONSE M3U8: {response.url} (Status: {response.status})")
        
        page.on("request", log_request)
        page.on("response", log_response)
        
        try:
            # Navigate and wait
            await page.goto(url, wait_until='domcontentloaded', timeout=120000)
            await simulate_human_behavior(page)
            await handle_popups(page)
            await realistic_page_interaction(page)
            
            # Extended wait with periodic interactions
            for i in range(max_wait_time // 10):
                await asyncio.sleep(10)
                await page.evaluate("window.scrollTo(0, Math.random() * document.body.scrollHeight)")
                await trigger_video_player(page)
                
                # Check if any m3u8 URLs found
                m3u8_requests = [r for r in all_requests if '.m3u8' in r['url'].lower()]
                m3u8_responses = [r for r in all_responses if '.m3u8' in r['url'].lower()]
                
                if m3u8_requests or m3u8_responses:
                    logging.info(f"✅ Found streams after {(i+1)*10}s of monitoring")
                    break
                    
                logging.info(f"⏳ Still monitoring... {(i+1)*10}s elapsed")
        
        except Exception as e:
            logging.error(f"Debug error: {e}")
        
        finally:
            # Print debug summary
            logging.info(f"📊 DEBUG SUMMARY for {url}:")
            logging.info(f"   Total requests: {len(all_requests)}")
            logging.info(f"   Total responses: {len(all_responses)}")
            
            m3u8_requests = [r for r in all_requests if '.m3u8' in r['url'].lower()]
            m3u8_responses = [r for r in all_responses if '.m3u8' in r['url'].lower()]
            
            logging.info(f"   M3U8 requests: {len(m3u8_requests)}")
            logging.info(f"   M3U8 responses: {len(m3u8_responses)}")
            
            for req in m3u8_requests:
                logging.info(f"   📥 REQ: {req['url']}")
            
            for resp in m3u8_responses:
                logging.info(f"   📤 RESP: {resp['url']} (Status: {resp['status']})")
            
            await browser.close()

# Main function with enhanced error handling
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
    
    # Optional: Debug specific problematic URLs first
    debug_mode = False  # Set to True to debug specific sites
    
    if debug_mode:
        # Debug the problematic ones (01 and 02)
        await debug_specific_site(channel_updates["01"], max_wait_time=120)
        await debug_specific_site(channel_updates["02"], max_wait_time=120)
    else:
        # Run the full update
        await update_m3u_file(m3u_path, channel_updates)

if __name__ == "__main__":
    asyncio.run(main())
