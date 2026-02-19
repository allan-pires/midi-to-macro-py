"""Inspect sequence page HTML for embedded data."""
import re
import urllib.request

req = urllib.request.Request(
    "https://onlinesequencer.net/5210091",
    headers={"User-Agent": "Mozilla/5.0"},
)
with urllib.request.urlopen(req, timeout=12) as r:
    html = r.read().decode("utf-8", errors="replace")

# Find script tags that might contain sequence data
for m in re.finditer(r"<script[^>]*>([^<]{100,})</script>", html):
    content = m.group(1)
    if "note" in content.lower() or "song" in content or "sequence" in content.lower():
        if "instrument" in content or "time" in content or "length" in content:
            print("--- script block (first 2000 chars) ---")
            print(content[:2000])
            print()

# Also try to find URLs that load data
urls = re.findall(r'["\']([^"\']*\.(?:json|js|xml)[^"\']*)["\']', html)
print("Potential data URLs:", urls[:15])

# Look for loadSequence or similar
if "loadSequence" in html:
    idx = html.find("loadSequence")
    print("Around loadSequence:", html[idx : idx + 300])
if "songData" in html or "song_data" in html:
    idx = html.find("songData") or html.find("song_data")
    print("Around songData:", html[idx : idx + 400])
