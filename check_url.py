import os
import requests
import re
import time
from datetime import datetime
import pytz
from bs4 import BeautifulSoup
from atproto import Client, client_utils

SOURCE_URL = "https://opennx.github.io"
TIMEZONE = "Europe/Lisbon"

# --- READ SECURITY CREDENTIALS FROM ENVIRONMENT ---
BLUESKY_HANDLE = os.environ.get("BLUESKY_HANDLE")
BLUESKY_PASSWORD = os.environ.get("BLUESKY_PASSWORD")

HEADERS = {
    "User-Agent": "Tinfoil/17.0 (Nintendo Switch)",
    "Accept": "*/*"
}

GHOSTLAND_UP_ENDPOINTS = {
    "nx.ghostland.at": "https://nx.ghostland.at/up",
    "nx-retro.ghostland.at": "https://nx.ghostland.at/up",
    "nx-saves.ghostland.at": "https://nx.ghostland.at/up"
}

CUSTOM_SHOP_LINKS = {
    "magicmonkei.com": "https://dashboard.magicmonkei.com/pt/signup?ref=opennx",
    "pixelgoblin.link": "https://pixelgoblin.link/r/awarelocale28"
}

def fetch_hosts():
    try:
        response = requests.get(SOURCE_URL, headers=HEADERS)
        response.raise_for_status()
        hosts = re.findall(r"host:\s*(.+)", response.text, re.IGNORECASE)
        return list(dict.fromkeys(h.strip() for h in hosts))
    except Exception as e:
        print(f"Failed to fetch host list: {e}")
        return []

def check_ghostland_up(url):
    try:
        response = requests.get(GHOSTLAND_UP_ENDPOINTS[url], headers=HEADERS, timeout=10)
        response.raise_for_status()
        if "ok" in response.text.lower():
            return "✅ Operational"
        return "❌ DOWN"
    except Exception as e:
        print(f"Error checking Ghostland /up for {url}: {e}")
        return "❌ DOWN"

def check_url_status(url):
    if url in GHOSTLAND_UP_ENDPOINTS:
        return check_ghostland_up(url)

    def try_fetch(scheme):
        try:
            full_url = f"{scheme}://{url}"
            response = requests.get(full_url, headers=HEADERS, timeout=12, allow_redirects=True)
            print(f"Fetching: {full_url} -> {response.status_code}")
            return response
        except requests.exceptions.SSLError:
            return None
        except requests.exceptions.RequestException:
            return None

    response = try_fetch("https")
    if response is None:
        response = try_fetch("http")
        if response is None:
            return "❌ DOWN (HTTPS and HTTP failed)"

    if response.status_code != 200:
        return f"❌ DOWN ({response.status_code})"

    content_type = response.headers.get('Content-Type', '').lower()
    content = response.text.lower()

    is_html = 'text/html' in content_type
    is_download = any(t in content_type for t in ['application/octet-stream', 'application/json', 'application/x-forcedownload'])

    working_indicators = [
        ".nsp", ".xci", "/files/", "tinfoil", ".nsz", ".iso",
        "eshop", "shop", "switch", "game", "region", "release",
        "\"files\":", "\"directories\":", "index.html", "server"
    ]

    if any(good in content for good in working_indicators):
        return "✅ OK"

    if is_html:
        soup = BeautifulSoup(content, "html.parser")
        title_text = soup.title.string.strip().lower() if soup.title else ""
        headers = " ".join(h.get_text().lower() for h in soup.find_all(["h1", "h2"]))

        if "maintenance" in title_text or "maintenance" in headers:
            return "⚠️ Under maintenance"

        broken_indicators = [
            "default web page", "site not found", "502 bad gateway",
            "this site can’t be reached", "<title>error", "error 403"
        ]
        if any(bad in content for bad in broken_indicators):
            return "❌ Error/Placeholder content"

        if len(content.strip()) < 300:
            return "⚠️ Possibly blank or minimal content"

    if is_download:
        return "⚠️ Unknown download content"

    return "⚠️ Unknown"

def generate_readme(results):
    results.sort(key=lambda x: x[1])
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    last_updated = now.strftime('%Y-%m-%d %H:%M:%S %Z')

    with open("README.md", "w", encoding="utf-8") as f:
        f.write("[![Update Shop Status](https://github.com/melogabriel/tinfoil-shops-status/actions/workflows/update.yml/badge.svg)](https://github.com/melogabriel/tinfoil-shops-status/actions/workflows/update.yml) \n\n")
        f.write("### Check which tinfoil shops are active and working for Nintendo Switch\n\n")
        f.write(f"**Last updated:** `{last_updated}` \n\n")

        f.write("| Shop | Status |\n")
        f.write("|------|--------|\n")
        
        for host, status in results:
            link_url = None
            for custom_key, custom_url in CUSTOM_SHOP_LINKS.items():
                if custom_key in host:
                    link_url = custom_url
                    break
            
            if not link_url:
                link_url = f"https://{host}"
                
            f.write(f"| [`{host}`]({link_url}) | {status} |\n")

def post_to_bluesky(results):
    if not BLUESKY_HANDLE or not BLUESKY_PASSWORD:
        print("Bluesky credentials missing from environment variables. Skipping post.")
        return

    total = len(results)
    online = sum(1 for _, status in results if "✅" in status)
    issues = sum(1 for _, status in results if "⚠️" in status)
    offline = sum(1 for _, status in results if "❌" in status)

    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    timestamp = now.strftime('%H:%M %Z')

    # Using TextBuilder to cleanly map rich clickable links to Bluesky
    tb = client_utils.TextBuilder()
    tb.text(f"🎮 Tinfoil Shop Status Update ({timestamp})\n\n")
    tb.text(f"🟢 Online: {online}/{total}\n")
    tb.text(f"🟡 Issues/Maint: {issues}\n")
    tb.text(f"🔴 Offline: {offline}\n\n")

    # Check and add active referral links dynamically
    has_featured = False
    for host, status in results:
        if "✅" in status:
            for custom_key, custom_url in CUSTOM_SHOP_LINKS.items():
                if custom_key in host:
                    if not has_featured:
                        tb.text("🌟 Featured:\n")
                        has_featured = True
                    tb.text(f"🔗 {custom_key}\n")
                    tb.link("[Register Here]", custom_url)
                    tb.text("\n\n")
                    break

    tb.text("#NintendoSwitch #Tinfoil")

    try:
        client = Client()
        client.login(BLUESKY_HANDLE, BLUESKY_PASSWORD)
        client.send_post(tb)
        print("Successfully posted to Bluesky!")
    except Exception as e:
        print(f"Failed to post to Bluesky: {e}")

def main():
    hosts = fetch_hosts()
    results = []
    for host in hosts:
        status = check_url_status(host)
        results.append((host, status))
    
    generate_readme(results)
    post_to_bluesky(results)

if __name__ == "__main__":
    main()
