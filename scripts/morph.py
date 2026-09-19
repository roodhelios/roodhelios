#!/usr/bin/env python3
"""Morph a fixed set of particles between several shapes.

Each shape is sampled to exactly N points and sorted the same way -- by angle
around the centroid -- so particle i lands somewhere sensible in the next
shape and the transition reads as a flow rather than a reshuffle. One
<animateTransform> per particle, so cost is linear in N regardless of how
many shapes there are.

Shapes are either image files or built-in symbols named with a leading colon:
:shield  :terminal  :lock  :radar

    python scripts/morph.py hood.png :shield :terminal \
        --labels ANONYMITY "ZERO TRUST" AUTOMATION --out assets

What works at 900 particles is THIN structure -- outlines, edges, highlights.
A solid filled silhouette becomes noise, because sparse points cannot render
a filled mass. If an image reads as a blob, try --edges, or use a symbol.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

SIZE = 340
PAD = 24
VIEW = SIZE + PAD * 2
MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,'DejaVu Sans Mono',monospace"

THEMES = {
    "dark": dict(dot="#4EA8DE", label="#8291A8", frame="#1F2A37"),
    "light": dict(dot="#0B4F8A", label="#57606A", frame="#D0D7DE"),
}


# --- built-in symbols, drawn as strokes so they survive sparse sampling ----
def sym_shield() -> Image.Image:
    im = Image.new("L", (SIZE, SIZE), 0)
    d = ImageDraw.Draw(im)
    pts = [(170, 32), (280, 72), (280, 170), (170, 308), (60, 170), (60, 72)]
    d.line(pts + [pts[0]], fill=255, width=7, joint="curve")
    d.line([(170, 110), (170, 210)], fill=255, width=7)
    d.line([(128, 160), (212, 160)], fill=255, width=7)
    return im


def sym_terminal() -> Image.Image:
    im = Image.new("L", (SIZE, SIZE), 0)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([44, 80, 296, 262], radius=14, outline=255, width=7)
    d.line([(44, 122), (296, 122)], fill=255, width=6)
    for cx in (70, 96, 122):
        d.ellipse([cx - 7, 94, cx + 7, 108], outline=255, width=5)
    d.line([(80, 168), (112, 192), (80, 216)], fill=255, width=7, joint="curve")
    d.line([(128, 220), (200, 220)], fill=255, width=7)
    return im


def sym_lock() -> Image.Image:
    im = Image.new("L", (SIZE, SIZE), 0)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([78, 152, 262, 292], radius=16, outline=255, width=7)
    d.arc([110, 58, 230, 186], start=180, end=360, fill=255, width=7)
    d.line([(110, 122), (110, 152)], fill=255, width=7)
    d.line([(230, 122), (230, 152)], fill=255, width=7)
    d.ellipse([155, 196, 185, 226], outline=255, width=7)
    d.line([(170, 226), (170, 258)], fill=255, width=7)
    return im


def sym_radar() -> Image.Image:
    im = Image.new("L", (SIZE, SIZE), 0)
    d = ImageDraw.Draw(im)
    for r in (46, 90, 134):
        d.ellipse([170 - r, 170 - r, 170 + r, 170 + r], outline=255, width=6)
    d.line([(170, 170), (170, 36)], fill=255, width=6)
    d.line([(170, 170), (285, 232)], fill=255, width=6)
    for px, py in ((214, 118), (122, 216), (238, 196)):
        d.ellipse([px - 9, py - 9, px + 9, py + 9], fill=255)
    return im


SYMBOLS = {"shield": sym_shield, "terminal": sym_terminal,
           "lock": sym_lock, "radar": sym_radar}


# --- shape loading --------------------------------------------------------
def load(spec: str, invert: bool, edges: bool, floor: float, gamma: float) -> np.ndarray:
    if spec.startswith(":"):
        key = spec[1:]
        if key not in SYMBOLS:
            raise SystemExit(f"Unknown symbol {spec}. Try: "
                             + ", ".join(f":{k}" for k in SYMBOLS))
        return np.clip(np.asarray(SYMBOLS[key](), dtype=np.float64) / 255.0, 0, 1)

    img = Image.open(spec)
    alpha = img.convert("RGBA").split()[-1] if img.mode in ("RGBA", "LA") else None
    gray = ImageOps.contain(img.convert("L"), (SIZE, SIZE), Image.LANCZOS)
    canvas = Image.new("L", (SIZE, SIZE), 0)
    ox, oy = (SIZE - gray.width) // 2, (SIZE - gray.height) // 2
    canvas.paste(gray, (ox, oy))
    a = np.asarray(canvas, dtype=np.float64) / 255.0
    inside = np.zeros_like(a)
    inside[oy:oy + gray.height, ox:ox + gray.width] = 1.0

    if edges:
        gy, gx = np.gradient(a)
        a = np.hypot(gx, gy)
        a = a / max(a.max(), 1e-9)
        a = np.asarray(Image.fromarray((a * 255).astype(np.uint8))
                       .filter(ImageFilter.GaussianBlur(0.6)), dtype=np.float64) / 255.0
    elif invert:
        a = 1.0 - a

    a *= inside
    if alpha is not None:
        am = ImageOps.contain(alpha, (SIZE, SIZE), Image.LANCZOS)
        ac = Image.new("L", (SIZE, SIZE), 0)
        ac.paste(am, (ox, oy))
        a *= np.asarray(ac, dtype=np.float64) / 255.0

    return np.clip(np.where(a < floor, 0.0, a - floor), 0, 1) ** gamma


def sample(a: np.ndarray, n: int, seed: int) -> np.ndarray:
    flat = a.ravel()
    if flat.sum() <= 0:
        raise SystemExit("Shape sampled to nothing -- lower --floor, or try --invert.")
    rng = np.random.default_rng(seed)
    idx = rng.choice(flat.size, size=n, replace=True, p=flat / flat.sum())
    ys, xs = np.divmod(idx, a.shape[1])
    return np.stack([xs + rng.uniform(-.45, .45, n), ys + rng.uniform(-.45, .45, n)], 1)


def order(pts: np.ndarray) -> np.ndarray:
    c = pts.mean(axis=0)
    d = pts - c
    return pts[np.lexsort((np.hypot(d[:, 0], d[:, 1]), np.arctan2(d[:, 1], d[:, 0])))]


def timeline(n: int, hold: float = 0.72):
    seg, kt, idx, t = 1.0 / n, [], [], 0.0
    for i in range(n):
        kt += [t, t + seg * hold]
        idx += [i, i]
        t += seg
    return [min(1.0, round(k, 4)) for k in kt] + [1.0], idx + [0]


def build(shapes, labels, theme: str, dur: float, seed: int = 5,
          spline: bool = False) -> str:
    c = THEMES[theme]
    n = len(shapes[0])
    kt, idx = timeline(len(shapes))
    kt_s = ";".join(f"{k:g}" for k in kt)
    ease = (f' calcMode="spline" keySplines="'
            + ";".join(["0.45 0 0.2 1"] * (len(kt) - 1)) + '"') if spline else ""
    radii = np.random.default_rng(seed).choice([1.1, 1.4, 1.8], n, p=[.5, .37, .13])

    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {VIEW} {VIEW}" '
         f'width="{VIEW}" height="{VIEW}" role="img" '
         f'aria-label="morphing particle field">']
    for dx, dy, sx, sy in ((0, 0, 1, 1), (SIZE, 0, -1, 1),
                           (0, SIZE, 1, -1), (SIZE, SIZE, -1, -1)):
        o.append(f'<path d="M{PAD+dx} {PAD+dy+sy*16}v{-sy*16}h{sx*16}" fill="none" '
                 f'stroke="{c["frame"]}" stroke-width="1.5"/>')

    o.append(f'<g fill="{c["dot"]}">')
    for i in range(n):
        vals = ";".join(f"{shapes[s][i][0]+PAD:.0f},{shapes[s][i][1]+PAD:.0f}"
                        for s in idx)
        o.append(f'<circle r="{radii[i]}">'
                 f'<animateTransform attributeName="transform" type="translate" '
                 f'values="{vals}" keyTimes="{kt_s}" dur="{dur}s" '
                 f'repeatCount="indefinite"{ease}/></circle>')
    o.append("</g>")

    seg = 1.0 / len(shapes)
    for s, lab in enumerate(labels[:len(shapes)]):
        o.append(f'<text x="{VIEW/2}" y="{VIEW-8}" fill="{c["label"]}" font-size="10" '
                 f'font-family="{MONO}" text-anchor="middle" letter-spacing="2.5" '
                 f'opacity="0">{lab.upper()}'
                 f'<animate attributeName="opacity" values="0;1;1;0" '
                 f'keyTimes="0;0.04;{seg*0.76:g};{seg*0.94:g}" dur="{dur}s" '
                 f'begin="{s*seg*dur:.2f}s" repeatCount="indefinite"/></text>')

    o.append("</svg>")
    return "".join(o)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("shapes", nargs="+", help="image paths and/or :symbol names")
    p.add_argument("--out", type=Path, default=Path("assets"))
    p.add_argument("--name", default="morph")
    p.add_argument("--points", type=int, default=900)
    p.add_argument("--dur", type=float, default=18.0)
    p.add_argument("--labels", nargs="*", default=[])
    p.add_argument("--floor", type=float, default=0.30,
                   help="zero out anything dimmer than this; kills background noise")
    p.add_argument("--floors", nargs="*", type=float, default=[],
                   help="per-shape floor overrides, one per shape")
    p.add_argument("--spline", action="store_true",
                   help="ease the transitions; adds ~90 bytes per particle")
    p.add_argument("--invert", nargs="*", type=int, default=[],
                   help="indices that are dark-on-light")
    p.add_argument("--edges", nargs="*", type=int, default=[],
                   help="indices to trace as edges rather than fill")
    p.add_argument("--gamma", type=float, default=1.0)
    a = p.parse_args()

    if len(a.shapes) < 2:
        raise SystemExit("Need at least two shapes.")

    built = []
    for i, spec in enumerate(a.shapes):
        fl = a.floors[i] if i < len(a.floors) else a.floor
        d = load(spec, i in a.invert, i in a.edges, fl, a.gamma)
        built.append(order(sample(d, a.points, seed=11 + i)))
        flags = "".join(f" {f}" for f, on in
                        (("inverted", i in a.invert), ("edges", i in a.edges)) if on)
        print(f"  {spec}: {a.points} particles{flags}")

    labels = a.labels or [s.lstrip(":") for s in a.shapes]
    a.out.mkdir(parents=True, exist_ok=True)
    for theme in ("dark", "light"):
        path = a.out / f"{a.name}-{theme}.svg"
        path.write_text(build(built, labels, theme, a.dur, spline=a.spline),
                        encoding="utf-8")
        print(f"  {path}  ({path.stat().st_size/1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
