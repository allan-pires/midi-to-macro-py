"""Find where sequence data is decoded into song/notes in the app JS."""
import urllib.request

url = "https://onlinesequencer.net/resources/c/41ee65af5a9601395bf0c1366e0e04c1.js"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req, timeout=15) as r:
    js = r.read().decode("utf-8", errors="replace")

# Search for decodeBinary, decode, data (in load context), song.notes =
for term in ["decodeBinary", "decodeSequence", "loadSequence", "song.notes=", "var data", "data="]:
    idx = 0
    while True:
        idx = js.find(term, idx)
        if idx < 0:
            break
        start = max(0, idx - 60)
        end = min(len(js), idx + 120)
        print("---", term, "at", idx, "---")
        print(repr(js[start:end]))
        print()
        idx += 1
        if term in ["decodeBinary", "loadSequence"] and idx > 0:
            break  # one occurrence enough
