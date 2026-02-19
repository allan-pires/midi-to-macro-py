"""Inspect first compact notes of sequence 545492 - raw bytes and field layout."""
import base64
import re
import struct
import urllib.request

url = "https://onlinesequencer.net/545492"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req, timeout=15) as r:
    html = r.read().decode("utf-8", errors="replace")
m = re.search(r"var data = '([^']*)'", html) or re.search(r'var data = "([^"]*)"', html)
binary = base64.b64decode(m.group(1).strip())

def read_varint(data, pos):
    v, shift = 0, 0
    while pos < len(data):
        b = data[pos]
        pos += 1
        v |= (b & 0x7F) << shift
        if not (b & 0x80):
            return v, pos
        shift += 7
    return v, pos

pos = 0
count = 0
while pos < len(binary) and count < 5:
    tag = binary[pos]
    pos += 1
    field, wire = tag >> 3, tag & 7
    if wire == 2:
        L, pos = read_varint(binary, pos)
        payload = binary[pos : pos + L]
        pos += L
        if field == 2 and L in (9, 14, 19):
            count += 1
            print("Compact note %d len %d hex: %s" % (count, L, payload.hex()))
            # Parse: 08 xx = field 1 varint
            p = 0
            while p < len(payload):
                t = payload[p]
                p += 1
                f, w = t >> 3, t & 7
                if w == 0:
                    v, p = read_varint(payload, p)
                    print("  field %d varint %d" % (f, v))
                elif w == 5 and p + 4 <= len(payload):
                    fl = struct.unpack("<f", payload[p:p+4])[0]
                    print("  field %d float %s" % (f, fl))
                    p += 4
                elif w == 2:
                    n, p = read_varint(payload, p)
                    p += n
                else:
                    break
            print()
    elif wire == 0:
        v, pos = read_varint(binary, pos)
    elif wire == 5:
        pos += 4
    elif wire == 1:
        pos += 8
    else:
        break

# Correct first note R = 75 (D#5). So we need to see what value would give 75.
# If field 1 = 75, use as MIDI. If field 1 = 32 (type_index), 107-32=75.
print("Expected: first note R = MIDI 75. So field 1 should be 75 (if MIDI) or 32 (if type_index 107-75).")
