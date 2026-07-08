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

# Using a Switch-like User-Agent to pass through shop firewalls/filters
HEADERS = {
    "User-Agent": "Tinfoil/17.0 (Nintendo Switch)",
    "Accept": "*/*"
}

# Mapping Ghostland shops to their /up endpoints
GHOSTLAND_UP_ENDPOINTS = {
    "nx.ghostland.at": "https://nx.ghostland.at/up",
    "nx-retro.ghostland.at": "https://nx.ghostland.at/up",
    "nx-saves.ghostland.at": "https://nx.ghostland.at/up"
}

# --- YOUR CUSTOM SHOP LINKS ---
CUSTOM_SHOP_LINKS = {
    "magicmonkei.com": "https://dashboard.magicmonkei.com/pt/signup?ref=opennx",
    "pixelgoblin.link": "https://pixelgoblin.link/r/awarelocale28"
}

def fetch_hosts():
    try:
        response = requests.get(SOURCE_URL, headers=HEADERS)
        response.raise_for_status()
        hosts = re.findall(r"host:\s*(.+)", response.text, re.IGNORECASE)
        return list(dict.fromkeys(h.strip() for h in hosts))  # Filters duplicates, preserves order
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
            print(f"SSL error on {scheme}://{url}, trying fallback...")
            return None
        except requests.exceptions.RequestException as e:
            print(f"{scheme.upper()} error for {url}: {e}")
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
        f.write("[![Update Shop Status](https://github.com/melogabriel/tinfoil-shops-status/actions/workflows/update.yml/badge.svg)](https://github.com/melogabriel/tinfoil-shops-status/actions/workflows/update.yml) ")
        f.write("![GitHub Repo stars](https://img.shields.io/github/stars/melogabriel/tinfoil-shops-status) ")
        f.write("![GitHub watchers](https://img.shields.io/github/watchers/melogabriel/tinfoil-shops-status)\n\n")
        f.write("### Check which tinfoil shops are active and working for Nintendo Switch\n\n")
        f.write("This page monitors the availability of Tinfoil shops from [this source list](https://opennx.github.io) and updates automatically every hour.\n\n")
        f.write("If this tool is useful, consider giving it a ⭐ on [GitHub](https://github.com/melogabriel/tinfoil-shops-status)!\n\n")
        f.write("If you have any shops to add, open an [issue](https://github.com/OpenNX/opennx.github.io/issues/new/choose) or make a [pull request](https://github.com/OpenNX/opennx.github.io/pulls).\n\n")
        f.write(f"**Last updated:** `{last_updated}` \n\n")

        f.write("### Status Legend\n")
        f.write("- ✅ OK — Shop is online and serving valid content\n")
        f.write("- ✅ Operational (via Ghostland `/up` endpoint)\n")
        f.write("- ⚠️ Possibly blank — Low-content or unusual page\n")
        f.write("- ⚠️ Under maintenance\n")
        f.write("- ❌ DOWN/Error — Shop not reachable or shows error\n\n")

        f.write("### Current Shop Status\n\n")
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
                
            shop_cell = f"[`{host}`]({link_url})"
            f.write(f"| {shop_cell} | {status} |\n")

        f.write("\n---\n")
        f.write("> This project is not affiliated with Tinfoil. This is for educational and monitoring purposes only.\n")

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

    # --- 1. BUILD MAIN SCOREBOARD POST ---
    main_tb = client_utils.TextBuilder()
    main_tb.text(f"🎮 Tinfoil Shop Status Update ({timestamp})\n\n")
    main_tb.text(f"🟢 Online: {online}/{total}\n")
    main_tb.text(f"🟡 Issues/Maint: {issues}\n")
    main_tb.text(f"🔴 Offline: {offline}\n\n")
    main_tb.text("#NintendoSwitch #Tinfoil")

    try:
        client = Client()
        client.login(BLUESKY_HANDLE, BLUESKY_PASSWORD)
        
        # Send main dashboard overview post
        root_post = client.send_post(main_tb)
        print("Successfully posted main summary to Bluesky!")
        
        parent_reference = {'cid': root_post.cid, 'uri': root_post.uri}
        root_reference = parent_reference.copy()

        # --- 2. CHUNKED REPLIES FOR DIRECTORY ---
        current_reply_tb = client_utils.TextBuilder()
        current_reply_tb.text("📋 Current Shop Directory:\n\n")
        
        # Track characters safely within the 300 constraint limit
        current_length = len(current_reply_tb.build_text())

        for host, status in results:
            icon = "❌"
            if "✅" in status:
                icon = "🟢"
            elif "⚠️" in status:
                icon = "🟡"

            # Compile line content into a temporary validation builder
            line_tb = client_utils.TextBuilder()
            line_tb.text(f"{icon} {host} — ")
            
            link_url = None
            for custom_key, custom_url in CUSTOM_SHOP_LINKS.items():
                if custom_key in host:
                    link_url = custom_url
                    break
            
            if link_url:
                line_tb.link("[Access]", link_url)
            else:
                line_tb.link("[Link]", f"https://{host}")
            line_tb.text("\n")

            line_text_len = len(line_tb.build_text())
            
            # Slice the thread response down if it goes beyond 240 bytes
            if current_length + line_text_len > 240:
                reply_post = client.send_post(
                    current_reply_tb,
                    reply_to={'root': root_reference, 'parent': parent_reference}
                )
                print("Posted directory chunk reply!")
                
                # Chain subsequent replies to the last sent post
                parent_reference = {'cid': reply_post.cid, 'uri': reply_post.uri}
                
                current_reply_tb = client_utils.TextBuilder()
                current_reply_tb.text("📋 Directory Continued:\n\n")
                current_length = len(current_reply_tb.build_text())

            # Append the text to the chunk
            current_reply_tb.text(line_tb.build_text())
            for facet in line_tb.build_facets():
                # Correctly offset facet indices to align with the running text length
                facet.index.byte_start += current_length
                facet.index.byte_end += current_length
                current_reply_tb.facets.append(facet)
                
            current_length += line_text_len

        # Emit any trailing remnants 
        if current_length > len("📋 Directory Continued:\n\n") and current_length > len("📋 Current Shop Directory:\n\n"):
            client.send_post(
                current_reply_tb,
                reply_to={'root': root_reference, 'parent': parent_reference}
            )
            print("Posted final directory chunk reply!")

    except Exception as e:
        print(f"Failed to post to Bluesky: {e}")

def main():
    hosts = fetch_hosts()
    results = []
    for host in hosts:
        status = check_url_status(host)
        print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {host} -> {status}")
        results.append((host, status))
    
    # Run pipelines sequentially
    generate_readme(results)
    post_to_bluesky(results)

if __name__ == "__main__":
    main()
