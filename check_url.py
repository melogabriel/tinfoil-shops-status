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

        # Heuristics for functional Tinfoil shops
        if "nsp" in content or ".nsp" in content or "title" in content or "tinfoil" in content:
            return "✅ OK"

        # Page is too empty or generic
        if len(content.strip()) < 300:
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
