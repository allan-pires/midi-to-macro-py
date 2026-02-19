"""Extract and decode the 'data' var from a sequence page."""
import re
import base64
import urllib.request

req = urllib.request.Request(
    "https://onlinesequencer.net/5210091",
    headers={"User-Agent": "Mozilla/5.0"},
)
with urllib.request.urlopen(req, timeout=12) as r:
    html = r.read().decode("utf-8", errors="replace")

# var data = '...'  (the string can be very long, single quoted)
m = re.search(r"var data = '([^']*)'", html)
if not m:
    m = re.search(r'var data = "([^"]*)"', html)
if not m:
    # Data might be split across lines with concatenation
    m = re.search(r"var data = '([A-Za-z0-9+/=]+)'", html, re.DOTALL)
if m:
    raw = m.group(1).strip()
    print("Data length:", len(raw))
    try:
        decoded = base64.b64decode(raw)
        print("Decoded len:", len(decoded))
        print("First 32 bytes hex:", decoded[:32].hex())
        print("First 32 ascii:", decoded[:32])
        if decoded[:4] == b"MThd":
            print("-> MIDI file header!")
        # Save for inspection
        with open("sample/seq_raw.bin", "wb") as f:
            f.write(decoded)
        print("Saved to sample/seq_raw.bin")
    except Exception as e:
        print("B64 decode error:", e)
else:
    print("No data var found")
    # Find where data is assigned
    idx = html.find("var data =")
    if idx >= 0:
        print("Found at idx", idx, "snippet:", html[idx : idx + 100])
