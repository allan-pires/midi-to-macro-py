import re
import urllib.request

req = urllib.request.Request(
    "https://onlinesequencer.net/5210091",
    headers={"User-Agent": "Mozilla/5.0"},
)
with urllib.request.urlopen(req, timeout=12) as r:
    html = r.read().decode("utf-8", errors="replace")

# Script src
for m in re.finditer(r'src="([^"]+\.js)"', html):
    print(m.group(1))
