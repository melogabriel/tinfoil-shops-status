import requests
import re
import time
from datetime import datetime
import pytz  

SOURCE_URL = "https://melogabriel.github.io/tinfoil-shops/"
TIMEZONE = "America/Sao_Paulo"  # Change as needed


def fetch_hosts():
    try:
        response = requests.get(SOURCE_URL)
        response.raise_for_status()
        hosts = re.findall(r"host:\s*(.+)", response.text, re.IGNORECASE)
        return [h.strip() for h in hosts]
    except Exception as e:
        print(f"Failed to fetch host list: {e}")
        return []

from bs4 import BeautifulSoup

def check_url_status(url):
    try:
        response = requests.get(f"https://{url}", timeout=10)
        print(f"Fetching: https://{url} -> {response.status_code}")

        if response.status_code != 200:
            return f"❌ DOWN ({response.status_code})"

        content = response.text.lower()

        # Debug specific domains
        if "ghostland" in url or "oragne" in url:
            print(f"\n--- DEBUG: Content from {url} ---")
            print(content[:1000])
            print("--- END DEBUG ---\n")

        # Parse using BeautifulSoup to analyze structure
        soup = BeautifulSoup(content, "html.parser")
        title_text = soup.title.string.strip().lower() if soup.title else ""

        # Step 1: Maintenance if the title clearly says it
        if "maintenance" in title_text:
            return "⚠️ Under maintenance"

        # Optional: look at headers (h1/h2) if needed
        headers = " ".join(h.get_text().lower() for h in soup.find_all(["h1", "h2"]))
        if "maintenance" in headers:
            return "⚠️ Under maintenance"

        # Step 2: Broken indicators
        broken_indicators = [
            "default web page", "site not found", "502 bad gateway",
            "this site can’t be reached", "<title>error", "error 403"
        ]
        if any(bad in content for bad in broken_indicators):
            return "❌ Error/Placeholder content"

        # Step 3: Possibly blank content
        if len(content.strip()) < 300:
            return "⚠️ Possibly blank or minimal content"

        # Step 4: Working indicators
        working_indicators = [
            ".nsp", ".xci", "/files/", "tinfoil", ".nsz", ".iso",
            "eshop", "switch", "game", "region", "release"
        ]
        if any(good in content for good in working_indicators):
            return "✅ OK"

        return "⚠️ Unknown"

    except requests.RequestException as e:
        return f"❌ Error: {e}"


def generate_readme(results):
    # Sort by status (optional)
    results.sort(key=lambda x: x[1])

    # Timezone-aware last updated
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    last_updated = now.strftime('%Y-%m-%d %H:%M:%S %OZ%Z')

    with open("README.md", "w", encoding="utf-8") as f:
        f.write("#  Tinfoil Shops Status Monitor\n\n")
        f.write("[![Update Shop Status](https://github.com/melogabriel/tinfoil-shops-status/actions/workflows/update.yml/badge.svg)](https://github.com/melogabriel/tinfoil-shops-status/actions/workflows/update.yml)\n\n")
        f.write("This page monitors the availability of Tinfoil shops from [this source list](https://melogabriel.github.io/tinfoil-shops/) and updates automatically every 6 hours.\n\n")
        f.write("If this tool is useful, consider giving it a ⭐ on [GitHub](https://github.com/melogabriel/tinfoil-shops-status)!\n\n")

        f.write(f"**Last updated:** `{last_updated}` \n\n")

        f.write("### Status Legend\n")
        f.write("- ✅ OK — Shop is online and serving valid content\n")
        f.write("- ⚠️ Possibly blank — Low-content or unusual page\n")
        f.write("- ❌ DOWN/Error — Shop not reachable or shows error\n\n")

        f.write("### Current Shop Status\n\n")
        f.write("| Host | Status |\n")
        f.write("|------|--------|\n")
        for host, status in results:
            f.write(f"| `{host}` | {status} |\n")

        f.write("\n---\n")
        f.write("_This project is not affiliated with Tinfoil. This is for educational and monitoring purposes only._\n")

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
