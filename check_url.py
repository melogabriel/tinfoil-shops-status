import requests
import re
import time
from datetime import datetime
import pytz
from bs4 import BeautifulSoup

SOURCE_URL = "https://opennx.github.io"
TIMEZONE = "Europe/Lisbon"

# Using a Switch-like User-Agent to pass through shop filters
HEADERS = {
    "User-Agent": "Tinfoil/17.0 (Nintendo Switch)",
    "Accept": "*/*"
}

GHOSTLAND_UP_ENDPOINTS = {
    "nx.ghostland.at": "https://nx.ghostland.at/up",
    "nx-retro.ghostland.at": "https://nx.ghostland.at/up",
    "nx-saves.ghostland.at": "https://nx.ghostland.at/up"
}

def fetch_hosts():
    try:
        response = requests.get(SOURCE_URL, headers=HEADERS, timeout=15)
        response.raise_for_status()
        hosts = re.findall(r"host:\s*(.+)", response.text, re.IGNORECASE)
        return [h.strip() for h in hosts]
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
    except Exception:
        return "❌ DOWN"

def check_url_status(url):
    if url in GHOSTLAND_UP_ENDPOINTS:
        return check_ghostland_up(url)

    def try_fetch(scheme):
        try:
            full_url = f"{scheme}://{url}"
            # allow_redirects=True is crucial if index.html is behind a redirect
            response = requests.get(full_url, headers=HEADERS, timeout=12, allow_redirects=True)
            return response
        except (requests.exceptions.SSLError, requests.exceptions.RequestException):
            return None

    response = try_fetch("https")
    if response is None:
        response = try_fetch("http")
        if response is None:
            return "❌ DOWN (Connection Failed)"

    if response.status_code != 200:
        return f"❌ DOWN ({response.status_code})"

    content_type = response.headers.get('Content-Type', '').lower()
    content = response.text.lower()

    # --- BROAD DETECTION LOGIC ---
    # This covers JSON, TFL files, and forced HTML downloads
    is_download = any(t in content_type for t in ['application/octet-stream', 'application/json', 'application/x-forcedownload'])
    is_html = 'text/html' in content_type

    # Keywords that indicate a functional shop (regardless of file type)
    working_indicators = [
        ".nsp", ".xci", "/files/", "tinfoil", ".nsz", "eshop", 
        "\"files\":", "\"directories\":", "success", "index.html"
    ]

    # 1. Check if the content (downloaded or rendered) has shop signatures
    if any(good in content for good in working_indicators):
        if is_download:
            return "✅ Operational"
        return "✅ OK"

    # 2. If it is HTML but no indicators, use BeautifulSoup to check for Maintenance
    if is_html:
        soup = BeautifulSoup(content, "html.parser")
        title_text = soup.title.string.strip().lower() if soup.title else ""
        headers_text = " ".join(h.get_text().lower() for h in soup.find_all(["h1", "h2"]))
        
        if "maintenance" in title_text or "maintenance" in headers_text:
            return "⚠️ Under maintenance"

        broken_indicators = ["default web page", "site not found", "502 bad gateway", "error 403"]
        if any(bad in content for bad in broken_indicators):
            return "❌ Error/Placeholder"

    # 3. Size check as a last resort
    if len(content.strip()) < 200:
        return "⚠️ Minimal content"

    return "⚠️ Unknown/Empty"

def generate_readme(results):
    results.sort(key=lambda x: x[1])
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    last_updated = now.strftime('%Y-%m-%d %H:%M:%S %Z')

    with open("README.md", "w", encoding="utf-8") as f:
        f.write("[![Update Shop Status](https://github.com/melogabriel/tinfoil-shops-status/actions/workflows/update.yml/badge.svg)](https://github.com/melogabriel/tinfoil-shops-status/actions/workflows/update.yml) ")
        f.write("![GitHub Repo stars](https://img.shields.io/github/stars/melogabriel/tinfoil-shops-status)\n\n")
        f.write("### Tinfoil Shop Status Monitor\n\n")
        f.write(f"**Last updated:** `{last_updated}` \n\n")
        f.write("### Status Legend\n")
        f.write("- ✅ OK — Shop is online (HTML, JSON, or Index file)\n")
        f.write("- ⚠️ Minimal/Maintenance — Site reachable but content is ambiguous\n")
        f.write("- ❌ DOWN — Shop unreachable\n\n")
        f.write("| Shop | Status |\n|------|--------|\n")
        for host, status in results:
            f.write(f"| `{host}` | {status} |\n")

def main():
    hosts = fetch_hosts()
    results = []
    for host in hosts:
        status = check_url_status(host)
        print(f"{datetime.now().strftime('%H:%M:%S')} - {host} -> {status}")
        results.append((host, status))
    generate_readme(results)

if __name__ == "__main__":
    main()
