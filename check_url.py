import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import re

# Source URL containing shop hosts
SOURCE_URL = "https://opennx.github.io"

# Timezone for last updated field
TIMEZONE = "America/Sao_Paulo"

# Ghostland shops with their `/up` status endpoints
GHOSTLAND_UP_ENDPOINTS = {
    "https://nx.ghostland.at": "https://nx.ghostland.at/up",
    "https://nx-retro.ghostland.at": "https://nx.ghostland.at/up",
    "https://nx-saves.ghostland.at": "https://nx.ghostland.at/up"
}

# -------------------------------------------------------
# Fetch hosts list
# -------------------------------------------------------
def fetch_hosts():
    try:
        response = requests.get(SOURCE_URL, timeout=15)
        response.raise_for_status()
        hosts = re.findall(r"host:\s*(.+)", response.text)
        return [h.strip() for h in hosts]
    except Exception as e:
        print(f"Error fetching hosts list: {e}")
        return []

# -------------------------------------------------------
# Ghostland status check using `/up` endpoint
# -------------------------------------------------------
def check_ghostland_up(url):
    try:
        status_url = GHOSTLAND_UP_ENDPOINTS[url]
        response = requests.get(status_url, timeout=10)
        if response.status_code == 200 and "ok" in response.text.lower():
            return "\u2705 ONLINE"
        return "\u274C OFFLINE"
    except Exception:
        return "\u274C OFFLINE"

# -------------------------------------------------------
# Generic shop status check
# -------------------------------------------------------
def check_url_status(url):
    # First handle Ghostland shops
    if url in GHOSTLAND_UP_ENDPOINTS:
        return check_ghostland_up(url)

    # Try HTTPS first, fallback to HTTP
    try:
        response = requests.get(f"https://{url}", timeout=10)
    except Exception:
        try:
            response = requests.get(f"http://{url}", timeout=10)
        except Exception:
            return "\u274C OFFLINE"

    # Non-200 means offline
    if response.status_code != 200:
        return "\u274C OFFLINE"

    # If it forces a download → bad config
    if "content-disposition" in response.headers and "attachment" in response.headers["content-disposition"].lower():
        return "\u274C OFFLINE"

    # If not HTML/text → invalid
    if "content-type" in response.headers and not response.headers["content-type"].startswith(("text/html", "application/xhtml")):
        return "\u274C OFFLINE"

    # Parse content
    content = response.text.lower()
    soup = BeautifulSoup(content, "html.parser")

    # Maintenance detection
    if soup.title and "maintenance" in soup.title.text.lower():
        return "\u274C OFFLINE"
    if soup.find(["h1", "h2"], string=lambda t: t and "maintenance" in t.lower()):
        return "\u274C OFFLINE"

    # Common server error markers
    error_phrases = [
        "502 bad gateway",
        "default web page",
        "site not found",
        "temporarily unavailable",
        "error",
    ]
    if any(p in content for p in error_phrases):
        return "\u274C OFFLINE"

    # Very small page → suspicious
    if len(content) < 300:
        return "\u274C OFFLINE"

    # Positive signals
    keywords = [".nsp", ".xci", "tinfoil", "switch", "game"]
    if any(k in content for k in keywords):
        return "\u2705 ONLINE"

    # Fallback → assume offline
    return "\u274C OFFLINE"

# -------------------------------------------------------
# Generate README.md with results
# -------------------------------------------------------
def generate_readme(results):
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)

    with open("README.md", "w", encoding="utf-8") as f:
        f.write("# Nintendo Switch Tinfoil Shops Status\n\n")
        f.write("This page shows the real-time status of various Tinfoil shops.\n\n")
        f.write(f"Last updated: **{now.strftime('%Y-%m-%d %H:%M:%S %Z')}**\n\n")

        f.write("Legend: ✅ = Online | ❌ = Offline\n\n")
        f.write("| Shop | Status |\n")
        f.write("|------|--------|\n")

        for host, status in results:
            f.write(f"| {host} | {status} |\n")

# -------------------------------------------------------
# Main
# -------------------------------------------------------
def main():
    hosts = fetch_hosts()
    results = []

    for host in hosts:
        status = check_url_status(host)
        print(f"{host}: {status}")
        results.append((host, status))

    generate_readme(results)

if __name__ == "__main__":
    main()
