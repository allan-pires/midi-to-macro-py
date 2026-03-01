"""Generate where-songs-meet.ico from 🎶 emoji using Segoe UI Emoji (Windows). Run from project root."""

import os
import sys

def main():
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("Pillow required: pip install Pillow")
        sys.exit(1)

    windir = os.environ.get("WINDIR", "C:\\Windows")
    font_path = os.path.join(windir, "Fonts", "seguiemj.ttf")
    if not os.path.isfile(font_path):
        print("Segoe UI Emoji not found at", font_path)
        sys.exit(1)

    size = 256
    font_size = max(8, int(size * 72 / 96))
    font = ImageFont.truetype(font_path, font_size)
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.text((size / 2, size / 2), "🎶", font=font, anchor="mm", embedded_color=True)

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_path = os.path.join(root, "where-songs-meet.ico")
    img.save(out_path, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (256, 256)])
    print("Wrote", out_path)

if __name__ == "__main__":
    main()
