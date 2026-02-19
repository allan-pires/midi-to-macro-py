"""Inspect sequence 151186 binary structure."""
import base64
import re
import struct
import urllib.request

url = "https://onlinesequencer.net/151186"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req, timeout=15) as r:
    html = r.read().decode("utf-8", errors="replace")

m = re.search(r"var data = '([^']*)'", html)
if not m:
    m = re.search(r'var data = "([^"]*)"', html)
raw = m.group(1).strip()
binary = base64.b64decode(raw)
print("Total decoded length:", len(binary))

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

# Walk top-level and count field 1 vs field 2
pos = 0
field1_blocks = []
field2_blocks = []
while pos < len(binary):
    if pos >= len(binary):
        break
    tag = binary[pos]
    pos += 1
    field = tag >> 3
    wire = tag & 7
    if wire == 2:
        L, pos = read_varint(binary, pos)
        if field == 1:
            field1_blocks.append((pos, L))
        elif field == 2:
            field2_blocks.append((pos, L))
        pos += L
    elif wire == 0:
        v, pos = read_varint(binary, pos)
    elif wire == 5:
        pos += 4
    elif wire == 1:
        pos += 8
    else:
        break

print("Field 1 blocks (notes blob):", len(field1_blocks))
print("Field 2 blocks:", len(field2_blocks))
if field2_blocks:
    lengths = set(L for _, L in field2_blocks)
    print("Field 2 lengths:", lengths)
    # Dump first three field-2 payloads (19 bytes?)
    for i, (start, L) in enumerate(field2_blocks[:5]):
        payload = binary[start : start + L]
        print("  Field2 block %d len %d hex: %s" % (i, L, payload.hex()))
        # Try parse as: 08 xx (varint), 15 xx xx xx xx (float), 1d xx xx xx xx (float)?
        if L >= 13:
            p = 0
            while p < min(L, 15):
                if p >= len(payload):
                    break
                t = payload[p]
                f, w = t >> 3, t & 7
                p += 1
                if w == 0:
                    v, p = read_varint(payload, p)
                    print("    field %d varint %d" % (f, v))
                elif w == 5 and p + 4 <= L:
                    fl = struct.unpack("<f", payload[p:p+4])[0]
                    print("    field %d float %s" % (f, fl))
                    p += 4
                elif w == 2:
                    n, p = read_varint(payload, p)
                    p += n
                else:
                    break
            print("    --")
    # Total notes if each field2 is one note
    print("If each field2 is 1 note: total notes =", len(field1_blocks) * 34, "+", len(field2_blocks), "=?")
    # Actually field1 has 34 notes per block, and we have 1 block. So 34 + len(field2_blocks)
    print("Estimated total notes: 34 +", len(field2_blocks), "=", 34 + len(field2_blocks))
