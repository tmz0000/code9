import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

# Set up ChromeDriver
options = Options()
options.add_argument("--headless")
options.add_argument("--disable-gpu")

capabilities = DesiredCapabilities.CHROME
capabilities['goog:loggingPrefs'] = {'performance': 'ALL'}

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options, desired_capabilities=capabilities)

def fetch_new_stream_url(channel_page_url):
    driver.get(channel_page_url)
    time.sleep(5)  # Wait for page load

    # Get performance logs
    performance_logs = driver.get_log('performance')

    # Find request URL containing "playlist.m3u8?wmsAuthSign="
    for log in performance_logs:
        if log['message'].startswith('{"message":{"method":"Network.requestWillBeSent"'):
            log_message = log['message']
            request_url = log_message.split('"url":"')[1].split('"')[0]
            if request_url.startswith("playlist.m3u8?wmsAuthSign="):
                return request_url

    return None

def update_m3u_file(m3u_path, channel_updates):
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
