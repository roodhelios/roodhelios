#!/usr/bin/env python3
"""Check generated SVGs without a rasteriser.

Text widths are estimated from the monospace advance ratio, which is exact
enough to catch anchoring and overflow mistakes. Radar vertices are checked
against the trigonometry they are supposed to satisfy.

Usage:
    python scripts/verify.py
"""

from __future__ import annotations

import json
import math
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

NS = "{http://www.w3.org/2000/svg}"
CW = 0.6
ROOT = Path(__file__).resolve().parent.parent
R = 118

BANNER_PANELS = {"left": (28, 368), "right": (392, 1072)}


def viewbox(root) -> tuple[float, float]:
    _, _, w, h = (float(v) for v in root.get("viewBox").split())
    return w, h


def text_extent(el) -> tuple[float, float]:
    x = float(el.get("x"))
    size = float(el.get("font-size"))
    w = len(el.text or "") * size * CW
    a = el.get("text-anchor", "start")
    if a == "end":
        return x - w, x
    if a == "middle":
        return x - w / 2, x + w / 2
    return x, x + w


def check_text(path: Path, panels=None) -> list[str]:
    root = ET.parse(path).getroot()
    vw, vh = viewbox(root)
    bad = []
    for el in root.iter(NS + "text"):
        lo, hi = text_extent(el)
        y = float(el.get("y"))
        name = (el.text or "")[:32]
        if lo < -1 or hi > vw + 1:
            bad.append(f"{name!r} spans {lo:.0f}-{hi:.0f}, viewBox width {vw:.0f}")
        if not 0 <= y <= vh:
            bad.append(f"{name!r} y={y:.0f} outside height {vh:.0f}")
        for pname, (pl, pr) in (panels or {}).items():
            cx = (lo + hi) / 2
            if pl <= cx <= pr and not (pl - 2 <= lo and hi <= pr + 2):
                bad.append(f"{name!r} overflows {pname} panel ({pl}-{pr})")
    return bad



def check_banner_visibility(path: Path) -> list[str]:
    """Catch clip geometry that makes VISUAL.MAP blank on GitHub."""
    root = ET.parse(path).getroot()
    bad = []
    clips = list(root.iter(NS + "clipPath"))
    if not clips:
        return ["no VISUAL.MAP clip paths found"]
    for clip in clips:
        rect = clip.find(NS + "rect")
        if rect is None:
            bad.append(f"{clip.get('id', 'clipPath')} has no rectangle")
            continue
        if float(rect.get("height", "0")) <= 0:
            bad.append(f"{clip.get('id', 'clipPath')} starts with zero height")
        if rect.find(NS + "animate") is not None:
            bad.append(f"{clip.get('id', 'clipPath')} animates geometry; GitHub may hide it")

    scenes = [g for g in root.iter(NS + "g") if (g.get("clip-path") or "").startswith("url(#rv")]
    if len(scenes) != len(clips):
        bad.append(f"{len(scenes)} scene groups found for {len(clips)} clips")
    initial = [g for g in scenes if float(g.get("opacity", "1")) > 0]
    if len(initial) != 1:
        bad.append(f"{len(initial)} scenes are initially visible; expected exactly one")
    for scene in scenes:
        animations = [a for a in scene.findall(NS + "animate")
                      if a.get("attributeName") == "opacity"]
        if not animations:
            bad.append(f"{scene.get('clip-path')} has no frame opacity animation")

    dot_moves = 0
    for el in root.iter(NS + "path"):
        if el.get("stroke-linecap") == "round":
            dot_moves += (el.get("d") or "").count("M")
    if dot_moves < 2500:
        bad.append(f"only {dot_moves} stipple points found; VISUAL.MAP is likely empty")
    return bad

def check_radar(svg: Path, cfg: Path) -> list[str]:
    axes = json.loads(cfg.read_text())["axes"]
    n = len(axes)
    root = ET.parse(svg).getroot()
    vw, vh = viewbox(root)
    cx, cy = None, None
    for ln in root.iter(NS + "line"):
        cx, cy = float(ln.get("x1")), float(ln.get("y1"))
        break
    target = None
    for pg in root.iter(NS + "polygon"):
        an = pg.find(NS + "animate")
        if an is not None:
            target = an.get("to")
    if target is None:
        return ["no animated value polygon found"]

    pts = [tuple(map(float, p.split(","))) for p in target.split()]
    bad = []
    if len(pts) != n:
        return [f"{len(pts)} vertices, expected {n}"]
    for i, a in enumerate(axes):
        ang = -math.pi / 2 + i * 2 * math.pi / n
        frac = a["value"] / 100
        ex, ey = cx + R * frac * math.cos(ang), cy + R * frac * math.sin(ang)
        if math.hypot(pts[i][0] - ex, pts[i][1] - ey) > 0.05:
            bad.append(f"axis {i} ({a['label']}) at {pts[i]}, expected ({ex:.2f},{ey:.2f})")
    return bad


def main() -> int:
    fails = 0
    jobs = [
        ("assets/banner-dark.v2.svg", BANNER_PANELS, None),
        ("assets/banner-light.v2.svg", BANNER_PANELS, None),
        ("assets/radar-dark.svg", None, "assets/skills.json"),
        ("assets/radar-light.svg", None, "assets/skills.json"),
        ("assets/radar-langs-dark.svg", None, "assets/langmix.json"),
        ("assets/radar-langs-light.svg", None, "assets/langmix.json"),
        ("assets/card-stats-dark.svg", None, None),
        ("assets/card-stats-light.svg", None, None),
    ]
    for rel, panels, cfg in jobs:
        p = ROOT / rel
        if not p.exists():
            print(f"{rel}: skipped (not generated)")
            continue
        errs = check_text(p, panels)
        if "banner-" in rel:
            errs += check_banner_visibility(p)
        if cfg:
            errs += check_radar(p, ROOT / cfg)
        src = p.read_text()
        if "<script" in src.lower():
            errs.append("contains <script>, GitHub will strip it")
        fails += len(errs)
        print(f"{rel}: {'OK' if not errs else f'{len(errs)} PROBLEM(S)'}")
        for e in errs:
            print("    ", e)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
