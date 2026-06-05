"""Generate the PWA app icons (a simple cauldron on the Claude-dark background).

Build-time only — Pillow is NOT a runtime dependency. Regenerate with:
    .venv/Scripts/python.exe -m pip install pillow
    .venv/Scripts/python.exe scripts/make_icons.py
"""
from PIL import Image, ImageDraw

BG = (38, 38, 36, 255)        # #262624
ACCENT = (217, 119, 87, 255)  # #d97757
RIM = (230, 150, 120, 255)


def make(size: int, path: str):
    img = Image.new("RGBA", (size, size), BG)
    d = ImageDraw.Draw(img)
    s = size
    w = max(2, int(s * 0.03))
    # handles
    d.ellipse([s * 0.13, s * 0.46, s * 0.25, s * 0.62], outline=ACCENT, width=w)
    d.ellipse([s * 0.75, s * 0.46, s * 0.87, s * 0.62], outline=ACCENT, width=w)
    # pot body
    d.ellipse([s * 0.22, s * 0.34, s * 0.78, s * 0.82], fill=ACCENT)
    # rim
    d.ellipse([s * 0.20, s * 0.28, s * 0.80, s * 0.45], fill=RIM)
    # inner (the "soup" hollow)
    d.ellipse([s * 0.27, s * 0.31, s * 0.73, s * 0.42], fill=BG)
    img.save(path)


if __name__ == "__main__":
    make(192, "app/static/icon-192.png")
    make(512, "app/static/icon-512.png")
    print("icons written")
