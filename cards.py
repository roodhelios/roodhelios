#!/usr/bin/env python3
"""Render a GitHub statistics card from the GraphQL API.

Deliberately not github-readme-stats or streak-stats: those are shared public
instances that go down and take the section with them. This queries the API
directly and commits a static SVG.

Usage:
    GITHUB_TOKEN=ghp_... python scripts/cards.py --login roodhelios --out assets
    python scripts/cards.py --mock --out assets      # offline, fixture data
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from xml.sax.saxutils import escape

API = "https://api.github.com/graphql"
MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,'DejaVu Sans Mono',monospace"
CW = 0.6

W, H = 480, 236
PAD = 16

THEMES = {
    "dark": dict(panel="#10161F", border="#1F2A37", title="#4EA8DE",
                 label="#8291A8", value="#DDE7F5", rule="#1F2A37", accent="#4EA8DE"),
    "light": dict(panel="#F6F8FA", border="#D0D7DE", title="#0969DA",
                  label="#57606A", value="#1F2328", rule="#D0D7DE", accent="#0969DA"),
}

QUERY = """
query($login: String!, $after: String) {
  user(login: $login) {
    name
    login
    followers { totalCount }
    pullRequests { totalCount }
    issues { totalCount }
    repositories(first: 100, after: $after, ownerAffiliations: OWNER, isFork: false) {
      totalCount
      pageInfo { hasNextPage endCursor }
      nodes { stargazerCount }
    }
    contributionsCollection {
      totalCommitContributions
      restrictedContributionsCount
      totalRepositoriesWithContributedCommits
    }
  }
}
"""

MOCK = {
    "name": "Aryan Singh", "login": "roodhelios",
    "followers": 1, "stars": 3, "repos": 10,
    "commits": 67, "prs": 4, "issues": 2, "contributed": 3,
}


def fetch(login: str, token: str, include_private: bool) -> dict:
    stars = repos = 0
    cursor, user = None, None
    while True:
        body = json.dumps({"query": QUERY,
                           "variables": {"login": login, "after": cursor}}).encode()
        req = urllib.request.Request(API, data=body, headers={
            "Authorization": f"bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "profile-card-generator",
        })
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                payload = json.loads(r.read())
        except urllib.error.HTTPError as e:
            raise SystemExit(f"GitHub API returned {e.code}: {e.read()[:300].decode()}")
        if "errors" in payload:
            raise SystemExit(f"GraphQL error: {payload['errors']}")
        user = payload["data"]["user"]
        if user is None:
            raise SystemExit(f"No such user: {login}")
        page = user["repositories"]
        repos = page["totalCount"]
        stars += sum(n["stargazerCount"] for n in page["nodes"])
        if not page["pageInfo"]["hasNextPage"]:
            break
        cursor = page["pageInfo"]["endCursor"]

    cc = user["contributionsCollection"]
    commits = cc["totalCommitContributions"]
    if include_private:
        commits += cc["restrictedContributionsCount"]
    return {
        "name": user["name"] or user["login"],
        "login": user["login"],
        "followers": user["followers"]["totalCount"],
        "stars": stars,
        "repos": repos,
        "commits": commits,
        "prs": user["pullRequests"]["totalCount"],
        "issues": user["issues"]["totalCount"],
        "contributed": cc["totalRepositoriesWithContributedCommits"],
    }


def build(d: dict, theme: str) -> str:
    c = THEMES[theme]
    cells = [
        ("Repositories", d["repos"]),
        ("Stars earned", d["stars"]),
        ("Commits (past yr)", d["commits"]),
        ("Pull requests", d["prs"]),
        ("Issues opened", d["issues"]),
        ("Contributed to", d["contributed"]),
    ]

    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
         f'width="{W}" height="{H}" role="img" '
         f'aria-label="GitHub statistics for {escape(d["login"])}">']

    o.append(f'<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="8" '
             f'fill="{c["panel"]}" stroke="{c["border"]}"/>')
    o.append(f'<text x="{PAD}" y="30" fill="{c["title"]}" font-size="14" '
             f'font-family="{MONO}" font-weight="700">'
             f'{escape(d["name"])} \u2014 GitHub</text>')
    o.append(f'<text x="{W-PAD}" y="30" fill="{c["label"]}" font-size="10.5" '
             f'font-family="{MONO}" text-anchor="end">@{escape(d["login"])}</text>')
    o.append(f'<line x1="{PAD}" y1="42" x2="{W-PAD}" y2="42" stroke="{c["rule"]}"/>')

    col_w = (W - 2 * PAD) / 2
    for i, (label, value) in enumerate(cells):
        cx = PAD + (i % 2) * col_w
        cy = 76 + (i // 2) * 52
        beg = 0.2 + i * 0.09
        o.append(f'<g opacity="0">'
                 f'<animate attributeName="opacity" from="0" to="1" dur="0.5s" '
                 f'begin="{beg:.2f}s" fill="freeze"/>'
                 f'<animateTransform attributeName="transform" type="translate" '
                 f'from="0 10" to="0 0" dur="0.5s" begin="{beg:.2f}s" fill="freeze"/>')
        o.append(f'<rect x="{cx:.0f}" y="{cy-16:.0f}" width="3" height="26" rx="1.5" '
                 f'fill="{c["accent"]}" opacity="0.55"/>')
        o.append(f'<text x="{cx+12:.0f}" y="{cy-5:.0f}" fill="{c["label"]}" '
                 f'font-size="9.5" font-family="{MONO}" letter-spacing="0.6">'
                 f'{escape(label.upper())}</text>')
        o.append(f'<text x="{cx+12:.0f}" y="{cy+11:.0f}" fill="{c["value"]}" '
                 f'font-size="17" font-family="{MONO}" font-weight="700">'
                 f'{value:,}</text>')
        o.append("</g>")

    o.append(f'<line x1="{PAD}" y1="{H-30}" x2="{W-PAD}" y2="{H-30}" stroke="{c["rule"]}"/>')
    o.append(f'<circle cx="{PAD+5}" cy="{H-15}" r="3" fill="#27C93F">'
             f'<animate attributeName="opacity" values="1;0.3;1" dur="2.2s" '
             f'repeatCount="indefinite"/></circle>')
    o.append(f'<text x="{PAD+15}" y="{H-11}" fill="{c["label"]}" font-size="9" '
             f'font-family="{MONO}">{d["followers"]:,} followers</text>')
    o.append(f'<text x="{W-PAD}" y="{H-11}" fill="{c["label"]}" font-size="9" '
             f'font-family="{MONO}" text-anchor="end">generated from the GitHub API</text>')
    o.append("</svg>")
    return "".join(o)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--login", default="roodhelios")
    p.add_argument("--out", type=Path, default=Path("assets"))
    p.add_argument("--mock", action="store_true", help="use fixture data, no network")
    p.add_argument("--include-private", action="store_true",
                   help="add restricted contribution counts (needs a PAT with repo scope)")
    a = p.parse_args()

    if a.mock:
        data = MOCK
        print("  using mock data")
    else:
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("METRICS_TOKEN")
        if not token:
            raise SystemExit("Set GITHUB_TOKEN (or pass --mock to render fixture data).")
        data = fetch(a.login, token, a.include_private)

    a.out.mkdir(parents=True, exist_ok=True)
    for theme in ("dark", "light"):
        path = a.out / f"card-stats-{theme}.svg"
        path.write_text(build(data, theme), encoding="utf-8")
        print(f"  {path}  ({path.stat().st_size / 1024:.1f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
