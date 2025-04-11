import requests
import re
import time

SOURCE_URL = "https://melogabriel.github.io/tinfoil-shops/"

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

        # BLOCKLIST: Signs of broken/misconfigured or placeholder pages
        broken_indicators = [
            "403 forbidden",
            "cloudflare",
            "not found",
            "<title>error",
            "default web page",
            "site not found",
            "502 bad gateway",
            "this site can’t be reached"
        ]
        if any(bad in content for bad in broken_indicators):
            return "❌ Error/Placeholder content"

        # ALLOWLIST: Signs of a working shop
        working_indicators = [
            ".nsp", ".xci", "title", "tinfoil", "game",
            "/files/", "nsz", "eshop", "iso", "region", "release"
        ]
        if any(good in content for good in working_indicators):
            return "✅ OK"

        # Page is very short or looks empty
        if len(content.strip()) < 500:
            return "⚠️ Blank or minimal content"

        return "⚠️ Unexpected content"

    except requests.RequestException as e:
        return f"❌ Error: {e}"

def main():
    hosts = fetch_hosts()
    for host in hosts:
        status = check_url_status(host)
        print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {host} -> {status}")

if __name__ == "__main__":
    main()
