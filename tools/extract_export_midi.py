"""Extract exportMidi and related logic from the app JS."""
import urllib.request

url = "https://onlinesequencer.net/resources/c/41ee65af5a9601395bf0c1366e0e04c1.js"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req, timeout=15) as r:
    js = r.read().decode("utf-8", errors="replace")

# Find exportMidi function - get a big chunk after it
idx = js.find("function exportMidi()")
if idx >= 0:
    # Get next 4000 chars to see structure
    chunk = js[idx : idx + 4500]
    with open("sample/export_midi_snippet.txt", "w", encoding="utf-8") as f:
        f.write(chunk)
    print("Wrote sample/export_midi_snippet.txt", len(chunk), "chars")
else:
    print("exportMidi not found")
    idx = js.find("exportMidi")
    if idx >= 0:
        print("Found at", idx, ":", js[idx : idx + 500])
