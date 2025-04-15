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

def check_url_status(url):
    try:
        response = requests.get(f"http://{url}", timeout=10)
        if response.status_code != 200:
            return f"❌ DOWN ({response.status_code})"

        content = response.text.lower()

        # Step 1: Maintenance or placeholder
        maintenance_indicators = [
            "under maintenance", "site is under maintenance",
            "working on", "will be back", "site is being updated",
            "we are currently", "maintenance mode", "under construction"
        ]
        if any(word in content for word in maintenance_indicators):
            return "⚠️ Under maintenance"

        # Step 2: Broken placeholder
        broken_indicators = [
            "default web page", "site not found", "502 bad gateway",
            "this site can’t be reached", "<title>error", "error 403"
        ]
        if any(bad in content for bad in broken_indicators):
            return "❌ Error/Placeholder content"

        # Step 3: Check for real working indicators
        working_indicators = [
            ".nsp", ".xci", "/files/", "tinfoil", ".nsz", ".iso",
            "eshop", "switch", "game", "region", "release"
        ]
        if any(good in content for good in working_indicators):
            return "✅ OK"

        # Step 4: Very short content
        if len(content.strip()) < 300:
            return "⚠️ Possibly blank or minimal content"

        return "⚠️ Unclear or low-confidence status"

    except requests.RequestException as e:
        return f"❌ Error: {e}"


def generate_readme(results):
    # Sort by status (optional)
    results.sort(key=lambda x: x[1])

    # Timezone-aware last updated
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    last_updated = now.strftime('%Y-%m-%d %H:%M:%S %Z')

    with open("README.md", "w", encoding="utf-8") as f:
        f.write("# 🛒 Tinfoil Shops Status Monitor\n\n")
        f.write("[![Update Shop Status](https://github.com/melogabriel/tinfoil-shops-status/actions/workflows/update.yml/badge.svg)](https://github.com/melogabriel/tinfoil-shops-status/actions/workflows/update.yml)\n\n")
        f.write("This page monitors the availability of Tinfoil shops from [this source list](https://melogabriel.github.io/tinfoil-shops/) and updates automatically every 6 hours.\n\n")
        f.write("If this tool is useful, consider giving it a ⭐ on [GitHub](https://github.com/melogabriel/tinfoil-shops-status)!\n\n")

        f.write(f"**Last updated:** `{last_updated}`\n\n")

        f.write("### 🔍 Status Legend\n")
        f.write("- ✅ OK — Shop is online and serving valid content\n")
        f.write("- ⚠️ Possibly blank — Low-content or unusual page\n")
        f.write("- ❌ DOWN/Error — Shop not reachable or shows error\n\n")

        f.write("### 📋 Current Shop Status\n\n")
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
