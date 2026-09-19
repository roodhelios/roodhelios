#!/usr/bin/env python3
"""Turn IMG_2556.jpg into a background-free, tone-mapped portrait PNG.

The silhouette is a hand-traced polygon, not an ML segmentation, so the edge
is approximate. remove.bg will beat it if you want it cleaner.
"""

from PIL import Image, ImageDraw, ImageFilter
import numpy as np

SRC = "/mnt/user-data/uploads/IMG_2556.jpg"
CROP = (880, 1345, 1250, 1770)
SIZE = (370, 425)
OUT = "portrait.png"

# traced off a gridded crop, clockwise from the top of the hair
POLY = [
    (140, 34), (165, 36), (190, 42), (212, 56), (228, 76), (236, 100),
    (234, 126), (232, 150), (228, 172), (238, 190), (258, 202),
    (282, 222), (302, 256), (316, 300), (326, 356), (334, 425),
    (26, 425), (32, 366), (40, 310), (52, 262), (66, 222), (78, 196),
    (74, 168), (70, 140), (72, 112), (78, 84), (92, 58), (114, 40),
]

# compress into this range so the dark polo still gets some dots
FLOOR, CEIL = 0.15, 0.86


def build():
    img = Image.open(SRC).crop(CROP).resize(SIZE, Image.LANCZOS).convert("L")

    mask = Image.new("L", SIZE, 0)
    ImageDraw.Draw(mask).polygon(POLY, fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(2.5))

    # fade the last stretch so the bright khaki dissolves into the panel
    mk = np.asarray(mask, dtype=np.float64)
    ramp = np.ones(SIZE[1])
    ramp[-95:] = np.linspace(1.0, 0.0, 95) ** 1.4
    mask = Image.fromarray((mk * ramp[:, None]).astype(np.uint8))

    a = np.asarray(img, dtype=np.float64)
    m = np.asarray(mask, dtype=np.float64) / 255.0
    inside = a[m > 0.5]
    lo, hi = np.percentile(inside, 1), np.percentile(inside, 99)
    a = np.clip((a - lo) / max(hi - lo, 1e-6), 0, 1)

    # mild local contrast so hair and collar keep their edges
    blur = np.asarray(Image.fromarray((a * 255).astype(np.uint8))
                      .filter(ImageFilter.GaussianBlur(12)), dtype=np.float64) / 255.0
    a = np.clip(a + (a - blur) * 0.55, 0, 1)

    a = FLOOR + a * (CEIL - FLOOR)

    out = Image.fromarray((a * 255).astype(np.uint8)).convert("RGBA")
    out.putalpha(mask)
    out.save(OUT)
    print("portrait.png written", out.size)


if __name__ == "__main__":
    build()
