#!/usr/bin/env python3
"""Generate a terminal-style profile banner as a self-contained SVG.

The portrait is converted to a 1-bit stipple using Floyd-Steinberg error
diffusion with serpentine scan order, then emitted as a single SVG path of
round dots. No external requests, no fonts to load, no scripts -- GitHub
renders the committed file directly.

Usage:
    python generate.py --photo me.png --config profile.json --out ../assets

    # tuning
    python generate.py --photo me.png --points 20000 --gamma 1.3 --invert

Best results come from a PNG with the background already removed: the alpha
channel is used as a mask, so only the subject gets stippled.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from xml.sax.saxutils import escape

import numpy as np
from PIL import Image, ImageFilter, ImageOps

# --- layout ---------------------------------------------------------------
W, H = 1100, 560          # viewBox
PAD = 8
BAR_H = 44                # title bar height
IMG_W, IMG_H = 300, 340   # stipple grid, in dots

LEFT_X, LEFT_W = 28, 340
RIGHT_X, RIGHT_W = 392, 680
BODY_Y, BODY_H = 68, 452

ROW_SIZE = 13.5           # info row font size
ROW_GAP = 25.5
CW = 0.6                  # monospace advance width ratio (width = size * CW)

MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,'DejaVu Sans Mono',monospace"

THEMES = {
    "dark": dict(bg="#0D1117", panel="#10161F", border="#1F2A37", chrome="#161B22",
                 label="#7D8590", value="#C9D1D9", accent="#4EA8DE",
                 dim="#30363D", dot="#4EA8DE"),
    "light": dict(bg="#FFFFFF", panel="#F6F8FA", border="#D0D7DE", chrome="#EAEEF2",
                  label="#57606A", value="#1F2328", accent="#0969DA",
                  dim="#AFB8C1", dot="#0B4F8A"),
}


# --- stipple --------------------------------------------------------------
def load_mask(path: Path, invert: bool, gamma: float, brightness: float) -> np.ndarray:
    """Return an (IMG_H, IMG_W) float array in [0,1]: the ink density we want."""
    img = Image.open(path)

    alpha = None
    if img.mode in ("RGBA", "LA") or "transparency" in img.info:
        alpha = img.convert("RGBA").split()[-1]

    gray = ImageOps.exif_transpose(img).convert("L")
    gray = ImageOps.contain(gray, (IMG_W, IMG_H), Image.LANCZOS)

    # centre it on the grid rather than stretching the aspect ratio
    canvas = Image.new("L", (IMG_W, IMG_H), 0)
    ox, oy = (IMG_W - gray.width) // 2, (IMG_H - gray.height) // 2
    canvas.paste(gray, (ox, oy))
    a = np.asarray(canvas, dtype=np.float64) / 255.0

    if alpha is not None:
        am = ImageOps.contain(alpha, (IMG_W, IMG_H), Image.LANCZOS)
        acan = Image.new("L", (IMG_W, IMG_H), 0)
        acan.paste(am, (ox, oy))
        a *= np.asarray(acan, dtype=np.float64) / 255.0

    if invert:
        a = 1.0 - a
        if alpha is not None:  # keep cut-out background empty after inverting
            acan_arr = np.asarray(acan, dtype=np.float64) / 255.0
            a *= acan_arr

    a = np.clip(a * brightness, 0.0, 1.0) ** gamma
    return a


def fit_density(a: np.ndarray, target: int) -> np.ndarray:
    """Scale so the array sums to `target`, compensating for clipping."""
    total = a.sum()
    if total <= 0:
        raise SystemExit("Image is uniformly empty -- try --invert or a lighter photo.")
    k = target / total
    for _ in range(40):
        scaled = np.clip(a * k, 0.0, 1.0)
        s = scaled.sum()
        if abs(s - target) < max(1.0, target * 0.002):
            break
        k *= target / max(s, 1e-9)
    return np.clip(a * k, 0.0, 1.0)


def dither(a: np.ndarray) -> np.ndarray:
    """Floyd-Steinberg error diffusion, serpentine scan. Returns a bool array."""
    work = a.copy()
    h, w = work.shape
    out = np.zeros((h, w), dtype=bool)

    for y in range(h):
        rng = range(w) if y % 2 == 0 else range(w - 1, -1, -1)
        step = 1 if y % 2 == 0 else -1
        for x in rng:
            old = work[y, x]
            new = 1.0 if old > 0.5 else 0.0
            out[y, x] = new > 0.5
            err = old - new
            nx = x + step
            if 0 <= nx < w:
                work[y, nx] += err * 7 / 16
            if y + 1 < h:
                if 0 <= x - step < w:
                    work[y + 1, x - step] += err * 3 / 16
                work[y + 1, x] += err * 5 / 16
                if 0 <= nx < w:
                    work[y + 1, nx] += err * 1 / 16
    return out


def dots_paths(mask, x0, y0, scale, groups=3):
    """Split the dots across N paths so each can shimmer out of phase."""
    ys, xs = np.nonzero(mask)
    rng = np.random.default_rng(7)
    bucket = rng.integers(0, groups, size=len(xs))
    out = []
    for g in range(groups):
        sel = bucket == g
        out.append("".join(
            f"M{x0 + px * scale:.0f} {y0 + py * scale:.0f}h.01"
            for px, py in zip(xs[sel], ys[sel])
        ))
    return out


# --- svg ------------------------------------------------------------------
def text(x, y, s, fill, size=ROW_SIZE, anchor="start", weight="400", extra=""):
    return (f'<text x="{x:.1f}" y="{y:.1f}" fill="{fill}" font-size="{size}" '
            f'font-family="{MONO}" font-weight="{weight}" '
            f'text-anchor="{anchor}"{extra}>{escape(s)}</text>')


PER_FRAME = 9.0       # seconds each frame holds
REVEAL = 2.2          # seconds for one frame to wipe over the last


BANDS = 26            # horizontal slices used to fake a wipe without clip-path


def cyclic_pulse(on: float, off: float, e: float = 0.006):
    """Opacity keyframes for something switched on over [on, off) in cyclic time.

    Built from plain opacity animation rather than an animated <clipPath>.
    clip-path on an <img>-embedded SVG is the one thing that did not survive
    GitHub's profile page, so the wipe is done with banded opacity instead.
    """
    on %= 1.0
    off %= 1.0
    if on < off:
        pts = [(0.0, 0), (on, 0), (on + e, 1), (off, 1), (off + e, 0), (1.0, 0)]
    else:
        pts = [(0.0, 1), (off, 1), (off + e, 0), (on, 0), (on + e, 1), (1.0, 1)]

    times, vals, last = [], [], -1.0
    for t, v in pts:
        t = min(max(t, 0.0), 1.0)
        if t <= last:
            t = min(last + 1e-4, 1.0)
        if times and t <= times[-1]:
            continue
        times.append(t)
        vals.append(v)
        last = t
    if times[0] > 0:
        times.insert(0, 0.0)
        vals.insert(0, pts[0][1])
    if times[-1] < 1.0:
        times.append(1.0)
        vals.append(vals[-1])
    return ";".join(str(v) for v in vals), kt(times)


def band_paths(mask, ix, iy, bands: int):
    """Split the stipple into horizontal bands, top to bottom."""
    ys, xs = np.nonzero(mask)
    h = mask.shape[0]
    out = []
    for b in range(bands):
        lo, hi = b * h // bands, (b + 1) * h // bands
        sel = (ys >= lo) & (ys < hi)
        out.append("".join(f"M{ix + px:.0f} {iy + py:.0f}h.01"
                           for px, py in zip(xs[sel], ys[sel])))
    return out


def frame_clip(i: int, n: int, iy: float):
    """A frame is revealed by a top-down wipe and removed by the same wipe
    running under the next frame, so the panel is never empty."""
    cycle = PER_FRAME * n
    exit_t = ((i + 1) * PER_FRAME) / cycle          # when the next frame lands
    exit_s = exit_t - REVEAL / cycle                # when its wipe starts
    enter_s = (i * PER_FRAME - REVEAL) / cycle
    enter_t = (i * PER_FRAME) / cycle

    if i == 0:
        # frame 0 is already whole at t=0 and re-wipes in at the very end,
        # which makes the loop seamless
        hv = f"{IMG_H};{IMG_H};0;0;{IMG_H}"
        hk = kt([0, exit_s, exit_t, 1 - REVEAL / cycle, 1])
    else:
        hv = f"0;0;{IMG_H};{IMG_H};0;0"
        hk = kt([0, enter_s, enter_t, exit_s, exit_t, 1])

    yv = f"{iy};{iy};{iy+IMG_H};{iy};{iy}"
    yk = kt([0, exit_s, exit_t, min(exit_t + 0.002, 1), 1])
    return cycle, hv, hk, yv, yk, enter_s, enter_t, exit_s, exit_t


def kt(vals) -> str:
    return ";".join(f"{v:g}" for v in vals)


def build(cfg: dict, frames, theme: str) -> str:
    """frames: list of (mask, dot_count, label) -- each a full-resolution stipple."""
    c = THEMES[theme]
    n = len(frames)
    cycle = PER_FRAME * n
    ix, iy = LEFT_X + 20, BODY_Y + 46
    o = []

    o.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
             f'width="{W}" height="{H}" role="img" '
             f'aria-label="{escape(cfg.get("alt", "profile banner"))}">')

    o.append("<defs>")
    o.append(f'<linearGradient id="scan" x1="0" y1="0" x2="0" y2="1">'
             f'<stop offset="0" stop-color="{c["accent"]}" stop-opacity="0"/>'
             f'<stop offset="0.5" stop-color="{c["accent"]}" stop-opacity="0.75"/>'
             f'<stop offset="1" stop-color="{c["accent"]}" stop-opacity="0"/>'
             f'</linearGradient>')
    o.append("</defs>")

    o.append(f'<rect x="{PAD}" y="{PAD}" width="{W-2*PAD}" height="{H-2*PAD}" rx="10" '
             f'fill="{c["bg"]}" stroke="{c["border"]}"/>')
    o.append(f'<path d="M{PAD} {PAD+18}a10 10 0 0 1 10-10h{W-2*PAD-20}a10 10 0 0 1 10 10'
             f'v{BAR_H-18}H{PAD}z" fill="{c["chrome"]}"/>')
    o.append(f'<line x1="{PAD}" y1="{PAD+BAR_H}" x2="{W-PAD}" y2="{PAD+BAR_H}" '
             f'stroke="{c["border"]}"/>')
    for i, col in enumerate(("#FF5F56", "#FFBD2E", "#27C93F")):
        o.append(f'<circle cx="{32+i*20}" cy="{PAD+BAR_H/2}" r="6" fill="{col}"/>')
    title = cfg.get("title", "profile.sh --live")
    o.append(text(W/2, PAD + BAR_H/2 + 4.5, title, c["label"], 13, "middle"))
    cxp = W/2 + len(title) * 13 * CW / 2 + 5
    o.append(f'<rect x="{cxp:.1f}" y="{PAD+BAR_H/2-8:.1f}" width="7" height="13" '
             f'fill="{c["accent"]}"><animate attributeName="opacity" '
             f'values="1;1;0;0" keyTimes="0;0.5;0.5;1" dur="1.1s" '
             f'repeatCount="indefinite"/></rect>')

    o.append(f'<rect x="{LEFT_X}" y="{BODY_Y}" width="{LEFT_W}" height="{BODY_H}" rx="6" '
             f'fill="{c["panel"]}" stroke="{c["border"]}"/>')
    o.append(f'<line x1="{LEFT_X}" y1="{BODY_Y+30}" x2="{LEFT_X+LEFT_W}" y2="{BODY_Y+30}" '
             f'stroke="{c["border"]}"/>')
    o.append(text(LEFT_X + 14, BODY_Y + 20, cfg.get("visual_label", "VISUAL.MAP"),
                  c["accent"], 11.5, weight="700"))
    o.append(text(LEFT_X + LEFT_W - 14, BODY_Y + 20, f"{IMG_W}\u00d7{IMG_H} / 1-BIT",
                  c["dim"], 10, "end"))

    for dx, dy, sx, sy in ((0, 0, 1, 1), (IMG_W, 0, -1, 1),
                           (0, IMG_H, 1, -1), (IMG_W, IMG_H, -1, -1)):
        o.append(f'<path d="M{ix+dx} {iy+dy+sy*14}v{-sy*14}h{sx*14}" fill="none" '
                 f'stroke="{c["dim"]}" stroke-width="1.5"/>')

    # one full-resolution stipple per frame, each scanned in then dissolved
    rev = REVEAL / cycle
    for i, (mask, _count, _lab) in enumerate(frames):
        enter = (i * PER_FRAME) / cycle
        leave = ((i + 1) * PER_FRAME) / cycle
        for b, d in enumerate(band_paths(mask, ix, iy, BANDS)):
            if not d:
                continue
            delay = (b / BANDS) * rev
            ov, ok = cyclic_pulse(enter + delay, leave + delay)
            # static fallback: if SMIL never runs, frame 0 still shows
            base = 1 if i == 0 else 0
            o.append(f'<path d="{d}" stroke="{c["dot"]}" stroke-width="1.15" '
                     f'stroke-linecap="round" fill="none" opacity="{base}">'
                     f'<animate attributeName="opacity" values="{ov}" '
                     f'keyTimes="{ok}" dur="{cycle}s" '
                     f'repeatCount="indefinite"/></path>')

    # the glow band rides each reveal edge in turn
    for i in range(n):
        _, _hv, _hk, _yv, _yk, _es, _et, exit_s, exit_t = frame_clip(i, n, iy)
        o.append(f'<rect x="{ix-2}" y="{iy-26}" width="{IMG_W+4}" height="26" '
                 f'fill="url(#scan)" opacity="0">'
                 f'<animate attributeName="y" '
                 f'values="{iy-26};{iy-26};{iy+IMG_H};{iy-26}" '
                 f'keyTimes="{kt([0, exit_s, exit_t, 1])}" '
                 f'dur="{cycle}s" repeatCount="indefinite"/>'
                 f'<animate attributeName="opacity" values="0;0;1;0;0" '
                 f'keyTimes="{kt([0, max(exit_s-0.002, 0), exit_s, exit_t, 1])}" '
                 f'dur="{cycle}s" repeatCount="indefinite"/></rect>')

    # footer label swaps with the active frame
    for i, (_m, count, lab) in enumerate(frames):
        _c, _hv, _hk, _yv, _yk, _es, enter_t, _xs, exit_t = frame_clip(i, n, iy)
        t0 = 0.0 if i == 0 else enter_t
        tf = exit_t
        te = exit_t
        txt = f"PTS {count} / {lab}"
        o.append(f'<g opacity="{1 if i == 0 else 0}">'
                 f'<animate attributeName="opacity" '
                 f'values="{"1;1;0;0" if i == 0 else "0;0;1;1;0;0"}" '
                 f'keyTimes="{kt([0, tf, te, 1]) if i == 0 else kt([0, max(t0-1e-4,0), t0, tf, min(te,1), 1])}" '
                 f'dur="{cycle}s" repeatCount="indefinite"/>'
                 + text(LEFT_X + 14, BODY_Y + BODY_H - 12, txt, c["dim"], 9.5)
                 + "</g>")

    o.append(f'<rect x="{RIGHT_X}" y="{BODY_Y}" width="{RIGHT_W}" height="{BODY_H}" rx="6" '
             f'fill="{c["panel"]}" stroke="{c["border"]}"/>')
    o.append(f'<line x1="{RIGHT_X}" y1="{BODY_Y+30}" x2="{RIGHT_X+RIGHT_W}" y2="{BODY_Y+30}" '
             f'stroke="{c["border"]}"/>')
    o.append(text(RIGHT_X + 16, BODY_Y + 20, cfg.get("info_label", "SYSTEM.INFO"),
                  c["accent"], 11.5, weight="700"))

    handle = cfg.get("handle", "")
    bw = len(handle) * 11 * CW + 22
    bx = RIGHT_X + RIGHT_W - 16 - bw
    o.append(f'<rect x="{bx:.1f}" y="{BODY_Y+5}" width="{bw:.1f}" height="20" rx="10" '
             f'fill="{c["accent"]}" opacity="0.16"/>')
    o.append(text(bx + bw/2, BODY_Y + 19, handle, c["accent"], 11, "middle", "600"))
    o.append(f'<circle cx="{bx-52:.1f}" cy="{BODY_Y+15}" r="3.5" fill="#27C93F">'
             f'<animate attributeName="opacity" values="1;0.2;1" dur="2.2s" '
             f'repeatCount="indefinite"/></circle>')
    o.append(text(bx - 42, BODY_Y + 19, "LIVE", c["label"], 10, weight="600"))

    lx, rx = RIGHT_X + 18, RIGHT_X + RIGHT_W - 18
    y = BODY_Y + 58
    for i, (lab, value) in enumerate(cfg.get("rows", [])):
        beg = 0.35 + i * 0.11
        o.append(f'<g opacity="0">'
                 f'<animate attributeName="opacity" from="0" to="1" dur="0.55s" '
                 f'begin="{beg:.2f}s" fill="freeze"/>'
                 f'<animateTransform attributeName="transform" type="translate" '
                 f'from="14 0" to="0 0" dur="0.55s" begin="{beg:.2f}s" fill="freeze"/>')
        o.append(text(lx, y, lab, c["label"]))
        o.append(text(rx, y, value, c["value"], anchor="end", weight="500"))
        a = lx + len(lab) * ROW_SIZE * CW + 8
        b = rx - len(value) * ROW_SIZE * CW - 8
        if b > a + 6:
            o.append(f'<line x1="{a:.1f}" y1="{y-4:.1f}" x2="{b:.1f}" y2="{y-4:.1f}" '
                     f'stroke="{c["dim"]}" stroke-width="1" stroke-dasharray="1 4" '
                     f'stroke-linecap="round"/>')
        o.append("</g>")
        y += ROW_GAP

    fy = BODY_Y + BODY_H - 12
    o.append(f'<circle cx="{RIGHT_X+22}" cy="{fy-4}" r="3" fill="#27C93F">'
             f'<animate attributeName="opacity" values="1;0.3;1" dur="2.2s" '
             f'begin="0.7s" repeatCount="indefinite"/></circle>')
    o.append(text(RIGHT_X + 32, fy, cfg.get("status_left", "ALL SYSTEMS NOMINAL"),
                  "#27C93F", 9.5))
    o.append(text(rx, fy, cfg.get("status_right", ""), c["dim"], 9.5, "end"))

    o.append("</svg>")
    return "".join(o)


def frame_mask(spec, invert: bool, edges: bool, floor: float,
               gamma: float, points: int):
    """Dither one image to a full-resolution 1-bit stipple for the panel."""
    img = Image.open(spec)
    alpha = img.convert("RGBA").split()[-1] if img.mode in ("RGBA", "LA") else None
    gray = ImageOps.contain(img.convert("L"), (IMG_W, IMG_H), Image.LANCZOS)
    canvas = Image.new("L", (IMG_W, IMG_H), 0)
    ox, oy = (IMG_W - gray.width) // 2, (IMG_H - gray.height) // 2
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
        am = ImageOps.contain(alpha, (IMG_W, IMG_H), Image.LANCZOS)
        ac = Image.new("L", (IMG_W, IMG_H), 0)
        ac.paste(am, (ox, oy))
        a *= np.asarray(ac, dtype=np.float64) / 255.0

    a = np.clip(np.where(a < floor, 0.0, a - floor), 0, 1) ** gamma
    mask = dither(fit_density(a, points))
    return mask, int(mask.sum())


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--photo", required=True, type=Path)
    p.add_argument("--config", default=Path("profile.json"), type=Path)
    p.add_argument("--out", default=Path("../assets"), type=Path)
    p.add_argument("--points", type=int, default=18000,
                   help="roughly how many dots to draw (default 18000)")
    p.add_argument("--gamma", type=float, default=1.0,
                   help=">1 thins the mid-tones, <1 fills them in")
    p.add_argument("--brightness", type=float, default=1.0)
    p.add_argument("--invert", action="store_true",
                   help="use for dark subjects on light backgrounds")
    p.add_argument("--frames", nargs="*", default=[],
                   help="extra images the VISUAL.MAP panel cycles through, "
                        "each rendered at full stipple resolution")
    p.add_argument("--frame-floors", nargs="*", type=float, default=[])
    p.add_argument("--frame-invert", nargs="*", type=int, default=[])
    p.add_argument("--frame-edges", nargs="*", type=int, default=[])
    p.add_argument("--frame-labels", nargs="*", default=[])
    a = p.parse_args()

    if not a.photo.exists():
        raise SystemExit(f"No such photo: {a.photo}")
    cfg = json.loads(a.config.read_text(encoding="utf-8"))

    dens = fit_density(load_mask(a.photo, a.invert, a.gamma, a.brightness), a.points)
    mask = dither(dens)
    n = int(mask.sum())
    frames = [(mask, n, "FS/SERPENTINE")]
    print(f"  {a.photo.name}: {n} dots")

    for i, spec in enumerate(a.frames):
        fl = a.frame_floors[i] if i < len(a.frame_floors) else 0.0
        lab = (a.frame_labels[i] if i < len(a.frame_labels) else Path(spec).stem).upper()
        m, cnt = frame_mask(spec, i in a.frame_invert, i in a.frame_edges,
                            fl, a.gamma, a.points)
        frames.append((m, cnt, lab))
        print(f"  {Path(spec).name}: {cnt} dots"
              f"{' (edges)' if i in a.frame_edges else ''}"
              f"{' (inverted)' if i in a.frame_invert else ''}")

    a.out.mkdir(parents=True, exist_ok=True)
    for theme in ("dark", "light"):
        path = a.out / f"banner-{theme}.svg"
        path.write_text(build(cfg, frames, theme), encoding="utf-8")
        print(f"  {path}  ({path.stat().st_size/1024:.0f} KB)")
    print(f"\n{len(frames)} frames, {PER_FRAME*len(frames):.0f}s loop.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
