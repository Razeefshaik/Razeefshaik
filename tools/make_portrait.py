"""Turns the GitHub avatar into halftone dot data (tools/data/portrait.json).

Run once (or when the avatar changes): python tools/make_portrait.py
Needs Pillow; the daily workflow only reads the JSON.
"""
from __future__ import annotations

import colorsys
import io
import json
import urllib.request

from PIL import Image, ImageDraw, ImageFilter, ImageStat

from svgkit import TOOLS

AVATAR = "https://avatars.githubusercontent.com/u/149264441?v=4&s=460"
CROP = (34, 96, 446, 456)          # the bust and the laptop
COLS = 66                          # dots across
LAPTOP = [(338, 256), (414, 254), (402, 410), (196, 418), (196, 352), (330, 352)]  # lid + keyboard
ARM = [(192, 204), (244, 206), (260, 226), (268, 262), (276, 300), (282, 336), (262, 350), (236, 318),
       (234, 270), (214, 252), (192, 248)]  # the lit arm raised to the chin
GAP = [(264, 236), (344, 236), (336, 350), (272, 350)]  # white page between hand and lid


def main():
    raw = urllib.request.urlopen(AVATAR, timeout=30).read()
    im = Image.open(io.BytesIO(raw)).convert("RGB")
    w, h = im.size
    px = im.load()
    # background = everything reachable from the border through white page or orange lettering;
    # the laptop and the lit arm are orange too, so inside them only near-white counts as background
    laptop = Image.new("1", (w, h), 0)
    ImageDraw.Draw(laptop).polygon(LAPTOP, fill=1)
    ImageDraw.Draw(laptop).polygon(ARM, fill=1)
    lp = laptop.load()

    def bg_like(x, y):
        r, g, b = px[x, y]
        hue, light, sat = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
        if lp[x, y]:
            return light > 0.95
        return light > 0.92 or (hue < 0.14 and sat > 0.45 and light > 0.35)
    seen = bytearray(w * h)
    stack = [(x, y) for x in range(w) for y in (0, h - 1)] + [(x, y) for y in range(h) for x in (0, w - 1)]
    while stack:
        x, y = stack.pop()
        i = y * w + x
        if seen[i] or not bg_like(x, y):
            continue
        seen[i] = 1
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < w and 0 <= ny < h and not seen[ny * w + nx]:
                stack.append((nx, ny))
    # enclosed bits of white page (between arm and laptop) are background too
    page = [colorsys.rgb_to_hls(*(c / 255 for c in px[i % w, i // w]))[1] > 0.95 for i in range(w * h)]
    mask = Image.frombytes("L", (w, h), bytes(0 if v or pg else 255 for v, pg in zip(seen, page)))
    ImageDraw.Draw(mask).polygon(GAP, fill=0)
    mask = mask.filter(ImageFilter.MinFilter(5)).filter(ImageFilter.MedianFilter(7))  # eat anti-aliased letter edges
    mask, img = mask.crop(CROP), im.crop(CROP)
    gray = img.convert("L")
    # equalize only inside the bust so the marble keeps its modelling
    vals = sorted(v for v, m in zip(gray.get_flattened_data(), mask.get_flattened_data()) if m > 128)
    lo, hi = vals[len(vals) // 50], vals[-len(vals) // 50]
    cw, ch = img.size
    cell = cw / COLS
    rows = int(ch / (cell * 0.866))
    grid = {}
    for row in range(rows):
        cy = (row + 0.5) * cell * 0.866
        off = cell / 2 if row % 2 else 0
        for col in range(COLS):
            cx = (col + 0.5) * cell + off
            if cx >= cw:
                continue
            box = (int(cx - cell / 2), int(cy - cell / 2), int(cx + cell / 2), int(cy + cell / 2))
            if ImageStat.Stat(mask.crop(box)).mean[0] / 255 < 0.6:
                continue
            region = img.crop(box).resize((1, 1), Image.BOX).getpixel((0, 0))
            g = ImageStat.Stat(gray.crop(box)).mean[0]
            lum = min(1.0, max(0.0, (g - lo) / max(1, hi - lo)))
            hue, light, sat = colorsys.rgb_to_hls(*(c / 255 for c in region))
            tone = "e" if (sat > 0.42 and hue < 0.12 and light > 0.3) else ("a" if sat > 0.28 and hue < 0.14 else "t")
            grid[(row, col)] = [round(cx / cw, 4), round(cy / ch, 4), round(lum, 3), tone]
    # drop specks: a dot needs at least three neighbours
    def neighbours(row, col):
        return sum((row + dr, col + dc) in grid for dr in (-1, 0, 1) for dc in (-1, 0, 1) if dr or dc)
    dots = [v for (r_, c_), v in grid.items() if neighbours(r_, c_) >= 3]
    out = TOOLS / "data" / "portrait.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"aspect": round(ch / cw, 4), "cell": round(cell / cw, 4), "dots": dots}), encoding="utf-8")
    print(out, len(dots), "dots")


if __name__ == "__main__":
    main()
