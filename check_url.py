import requests
import re
import time
from datetime import datetime
import pytz
from bs4 import BeautifulSoup

SOURCE_URL = "https://opennx.github.io"
TIMEZONE = "Europe/Lisbon"

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

def fetch_hosts():
    try:
        response = requests.get(SOURCE_URL, headers=HEADERS)
        response.raise_for_status()
        hosts = re.findall(r"host:\s*(.+)", response.text, re.IGNORECASE)
        return [h.strip() for h in hosts]
    except Exception as e:
        print(f"Failed to fetch host list: {e}")
        return []

def check_ghostland_up(url):
    """Check Ghostland shops via their /up endpoint"""
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
    # Handle Ghostland shops via /up endpoints
    if url in GHOSTLAND_UP_ENDPOINTS:
        return check_ghostland_up(url)

    def try_fetch(scheme):
        try:
            full_url = f"{scheme}://{url}"
            # allow_redirects=True handles URLs that point directly to files
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

    # --- UPDATED: Detection for HTML, JSON, and Forced Downloads ---
    is_html = 'text/html' in content_type
    is_download = any(t in content_type for t in ['application/octet-stream', 'application/json', 'application/x-forcedownload'])

    # Keywords for any format (HTML or direct file download)
    working_indicators = [
        ".nsp", ".xci", "/files/", "tinfoil", ".nsz", ".iso",
        "eshop", "shop", "switch", "game", "region", "release",
        "\"files\":", "\"directories\":", "index.html"
    ]

    # If indicators are found in a download OR HTML, mark as OK
    if any(good in content for good in working_indicators):
        return "✅ OK"

    # Fallback to HTML-specific parsing if no obvious indicators found
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

    # Final check: if it was a download but had no indicators
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
            f.write(f"| `{host}` | {status} |\n")

        f.write("\n---\n")
        f.write("> This project is not affiliated with Tinfoil. This is for educational and monitoring purposes only.\n")

def main():
    hosts = fetch_hosts()
    results = []
    for host in hosts:
        status = check_url_status(host)
        print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {host} -> {status}")
        results.append((host, status))
    generate_readme(results)

if __name__ == "__main__":
    main()
