#!/usr/bin/env python3
"""Render a radar chart from hand-entered scores.

The scores are yours, not scraped. That is the point: a byte-count of your
repos says you write HTML, which is true and useless. This says what you
actually work on.

Usage:
    python scripts/radar.py assets/skills.json   --out assets --name radar
    python scripts/radar.py assets/langmix.json  --out assets --name radar-langs
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from xml.sax.saxutils import escape

R = 118
RINGS = 5
LABEL_GAP = 24
LABEL_SIZE = 10.5
MARGIN = 14
TITLE_Y = 30
MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,'DejaVu Sans Mono',monospace"
CW = 0.6

THEMES = {
    "dark": dict(bg="none", grid="#1F2A37", spoke="#1F2A37", label="#8291A8",
                 title="#4EA8DE", fill="#4EA8DE", stroke="#4EA8DE",
                 dot="#9BD1F5", ring="#2A3644", value="#C9D1D9"),
    "light": dict(bg="none", grid="#D0D7DE", spoke="#D0D7DE", label="#57606A",
                  title="#0969DA", fill="#0969DA", stroke="#0969DA",
                  dot="#0B4F8A", ring="#C2CBD4", value="#1F2328"),
}


def angle(i: int, n: int) -> float:
    return -math.pi / 2 + i * 2 * math.pi / n


def anchor_for(cosa: float) -> str:
    return "middle" if abs(cosa) < 0.25 else ("start" if cosa > 0 else "end")


def layout(axes) -> tuple[float, float, float, float]:
    """Size the canvas so the longest label still fits. Returns W, H, CX, CY."""
    n = len(axes)
    left = right = up = down = R + 6
    for i, a in enumerate(axes):
        ang = angle(i, n)
        cosa, sina = math.cos(ang), math.sin(ang)
        tw = len(str(a["label"])) * LABEL_SIZE * CW
        px, py = (R + LABEL_GAP) * cosa, (R + LABEL_GAP) * sina
        anc = anchor_for(cosa)
        lo = px - tw if anc == "end" else (px - tw / 2 if anc == "middle" else px)
        hi = lo + tw
        left = max(left, -lo)
        right = max(right, hi)
        up = max(up, -(py - LABEL_SIZE))
        down = max(down, py + 12 + LABEL_SIZE)      # label plus the score line
    half = max(left, right) + MARGIN
    w = 2 * half
    cy = up + MARGIN + TITLE_Y
    h = cy + down + MARGIN
    return w, h, half, cy


def vertex(cx: float, cy: float, i: int, n: int, frac: float) -> tuple[float, float]:
    """Point for axis i at `frac` of full radius. Axis 0 points straight up."""
    ang = angle(i, n)
    return cx + R * frac * math.cos(ang), cy + R * frac * math.sin(ang)


def poly(points) -> str:
    return " ".join(f"{x:.2f},{y:.2f}" for x, y in points)


def build(cfg: dict, theme: str) -> str:
    c = THEMES[theme]
    axes = cfg["axes"]
    n = len(axes)
    if n < 3:
        raise SystemExit("A radar needs at least 3 axes.")

    W, H, CX, CY = layout(axes)
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}" '
         f'width="{W:.0f}" height="{H:.0f}" role="img" '
         f'aria-label="{escape(cfg.get("title", "radar"))}">']

    o.append(f'<defs><radialGradient id="rg-{theme}">'
             f'<stop offset="0" stop-color="{c["fill"]}" stop-opacity="0.42"/>'
             f'<stop offset="1" stop-color="{c["fill"]}" stop-opacity="0.14"/>'
             f'</radialGradient></defs>')

    o.append(f'<text x="{CX:.1f}" y="{TITLE_Y}" fill="{c["title"]}" font-size="13" '
             f'font-family="{MONO}" font-weight="700" text-anchor="middle" '
             f'letter-spacing="1.5">{escape(cfg.get("title", "").upper())}</text>')

    # concentric rings
    for ring in range(1, RINGS + 1):
        frac = ring / RINGS
        o.append(f'<polygon points="{poly(vertex(CX, CY, i, n, frac) for i in range(n))}" '
                 f'fill="none" stroke="{c["grid"] if ring < RINGS else c["ring"]}" '
                 f'stroke-width="{1 if ring < RINGS else 1.4}"/>')

    # spokes
    for i in range(n):
        x, y = vertex(CX, CY, i, n, 1.0)
        o.append(f'<line x1="{CX:.1f}" y1="{CY:.1f}" x2="{x:.2f}" y2="{y:.2f}" '
                 f'stroke="{c["spoke"]}" stroke-width="1"/>')

    # scale ticks up the vertical axis
    for ring in range(1, RINGS + 1):
        o.append(f'<text x="{CX + 5:.1f}" y="{CY - R * ring / RINGS + 4:.1f}" '
                 f'fill="{c["grid"]}" font-size="8" font-family="{MONO}">'
                 f'{ring * 100 // RINGS}</text>')

    # the value polygon, grown from the centre on load
    pts = [vertex(CX, CY, i, n, max(0.0, min(100.0, axes[i]["value"])) / 100)
           for i in range(n)]
    zero = [(CX, CY)] * n
    o.append(f'<polygon points="{poly(zero)}" fill="url(#rg-{theme})" '
             f'stroke="{c["stroke"]}" stroke-width="2" stroke-linejoin="round">'
             f'<animate attributeName="points" from="{poly(zero)}" to="{poly(pts)}" '
             f'dur="1.1s" begin="0.15s" fill="freeze" '
             f'calcMode="spline" keySplines="0.2 0.8 0.3 1" keyTimes="0;1"/>'
             f'</polygon>')

    # vertex dots, fading in behind the growing polygon
    for i, (x, y) in enumerate(pts):
        o.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3.2" fill="{c["dot"]}" '
                 f'opacity="0"><animate attributeName="opacity" from="0" to="1" '
                 f'dur="0.4s" begin="{0.85 + i * 0.05:.2f}s" fill="freeze"/></circle>')

    # axis labels, placed outside the outer ring
    for i, a in enumerate(axes):
        ang = angle(i, n)
        cosa = math.cos(ang)
        tx = CX + (R + LABEL_GAP) * cosa
        ty = CY + (R + LABEL_GAP) * math.sin(ang) + 4
        anchor = anchor_for(cosa)
        o.append(f'<text x="{tx:.1f}" y="{ty:.1f}" fill="{c["label"]}" font-size="{LABEL_SIZE}" '
                 f'font-family="{MONO}" text-anchor="{anchor}">'
                 f'{escape(a["label"])}</text>')
        # the score, tucked just inside the vertex
        sx = tx
        sy = ty + 12
        o.append(f'<text x="{sx:.1f}" y="{sy:.1f}" fill="{c["value"]}" font-size="9.5" '
                 f'font-family="{MONO}" font-weight="600" text-anchor="{anchor}" '
                 f'opacity="0.75">{a["value"]}</text>')

    o.append("</svg>")
    return "".join(o)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("config", type=Path)
    p.add_argument("--out", type=Path, default=Path("assets"))
    p.add_argument("--name", default="radar")
    a = p.parse_args()

    cfg = json.loads(a.config.read_text(encoding="utf-8"))
    a.out.mkdir(parents=True, exist_ok=True)
    for theme in ("dark", "light"):
        path = a.out / f"{a.name}-{theme}.svg"
        path.write_text(build(cfg, theme), encoding="utf-8")
        print(f"  {path}  ({path.stat().st_size / 1024:.1f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
