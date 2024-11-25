from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time

def fetch_new_stream_url(channel_page_url):
    options = Options()
    options.add_argument("--headless")  # Run in headless mode
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    try:
        driver.get(channel_page_url)
        time.sleep(5)  # Wait for all elements to load completely
        # Look for the playlist.m3u8 in page source or specific elements
        links = driver.find_elements_by_tag_name('a')
        for link in links:
            href = link.get_attribute('href')
            if 'playlist.m3u8' in href:
                print(f"Found URL: {href}")
                return href
    except Exception as e:
        print(f"Error fetching URL from {channel_page_url}: {e}")
    finally:
        driver.quit()
    return None

def update_m3u_file(m3u_path, channel_updates):
    try:
        with open(m3u_path, 'r') as file:
            lines = file.readlines()

        with open(m3u_path, 'w') as file:
            i = 0
            while i < len(lines):
                line = lines[i]
                if line.startswith('#EXTINF:') and 'group-title="NEW-XXX"' in line:
                    channel_info = line.strip()
                    channel_url = lines[i + 1].strip()
                    tvg_id = channel_info.split('tvg-id="')[1].split('"')[0]
                    if tvg_id in channel_updates:
                        new_url = fetch_new_stream_url(channel_updates[tvg_id])
                        if new_url:
                            channel_url = new_url  # Update the URL
                            print(f"Updating tvg-id={tvg_id} with new URL: {new_url}")
                    file.write(f"{channel_info}\n{channel_url}\n")
                    i += 1  # Skip the URL line as it's already updated
                else:
                    file.write(line)
                i += 1
    except Exception as e:
        print(f"Error updating M3U file: {e}")

def main():
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
        "09": "https://adult-tv-channels.com/private-tv-online/"
    }
    update_m3u_file(m3u_path, channel_updates)

if __name__ == "__main__":
    main()
