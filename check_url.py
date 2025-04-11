import requests
import re
import time

SOURCE_URL = "https://melogabriel.github.io/tinfoil-shops/"

def check_url_status(url):
    try:
        response = requests.get(f"http://{url}", timeout=10)
        if response.status_code != 200:
            return f"DOWN ({response.status_code})"
        
        content = response.text.lower()

        # Examples of working content (very basic match for file list or title)
        if "nsp" in content or "title" in content or ".nsp" in content:
            return "✅ OK"

        # Looks like a blank page or placeholder
        if len(content.strip()) < 300:
            return "⚠️ Blank or minimal content"

        return "⚠️ Unexpected content"

    except requests.RequestException as e:
        return f"❌ Error: {e}"
