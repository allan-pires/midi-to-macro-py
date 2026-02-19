"""One-off: fetch onlinesequencer.net/sequences and print structure."""
import re
import urllib.request

req = urllib.request.Request(
    "https://onlinesequencer.net/sequences?sort=1",
    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; rv:91.0) Gecko/20100101 Firefox/91.0"},
)
with urllib.request.urlopen(req, timeout=15) as r:
    html = r.read().decode("utf-8", errors="replace")

# <div class="preview" title="..."> ... <a href="/ID"></a>
blocks = re.findall(
    r'<div class="preview" title="([^"]*)"[^>]*>.*?<a href="/(\d+)"',
    html,
    re.DOTALL,
)
# Decode HTML entities in title
import html as html_module
pairs = [(sid, html_module.unescape(t.strip()) or f"Sequence {sid}") for t, sid in blocks]
print("ID-title pairs:", len(pairs))
for sid, title in pairs[:15]:
    print(" ", sid, repr(title[:55]))
