"""Render the live "Telemetry" panel (stats-dark.svg / stats-light.svg).

Runs daily in .github/workflows/profile-assets.yml:

    GITHUB_TOKEN=... python scripts/build_stats.py --out dist

Data: public contributions, streaks and languages from the GitHub GraphQL API,
and all-time model downloads from the Hugging Face API. Pass --from-json to
render from a saved snapshot instead (--dump writes one).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from svgkit import THEMES, delay, document, fmt, rect, text, text_width

GRAPHQL = "https://api.github.com/graphql"
CHART = {"dark": "#10a874", "light": "#059669"}  # validated against both chart surfaces
LANG_SHARE = 0.10  # a language "counts" for a repo at >= 10% of its bytes

REPOS_QUERY = """
query($login: String!, $after: String) {
  user(login: $login) {
    createdAt
    repositories(first: 100, after: $after, ownerAffiliations: OWNER, privacy: PUBLIC, isFork: false) {
      pageInfo { hasNextPage endCursor }
      nodes {
        name
        languages(first: 20, orderBy: {field: SIZE, direction: DESC}) { edges { size node { name } } }
      }
    }
  }
}"""

CALENDAR_QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar { weeks { contributionDays { date contributionCount } } }
    }
  }
}"""


# ── Fetching ──────────────────────────────────────────────────────────────────

def _graphql(query: str, variables: dict, token: str) -> dict:
    body = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request(GRAPHQL, data=body, headers={
        "Authorization": f"bearer {token}", "Content-Type": "application/json", "User-Agent": "profile-stats",
    })
    with urllib.request.urlopen(req, timeout=40) as resp:
        payload = json.load(resp)
    if payload.get("errors"):
        raise RuntimeError("GitHub GraphQL: " + "; ".join(e.get("message", "?") for e in payload["errors"]))
    return payload["data"]


def fetch_github(login: str, token: str) -> dict:
    repos, after, created = [], None, None
    while True:
        user = _graphql(REPOS_QUERY, {"login": login, "after": after}, token)["user"]
        created = user["createdAt"]
        page = user["repositories"]
        for node in page["nodes"]:
            repos.append({"name": node["name"],
                          "languages": {e["node"]["name"]: e["size"] for e in node["languages"]["edges"]}})
        if not page["pageInfo"]["hasNextPage"]:
            break
        after = page["pageInfo"]["endCursor"]

    now = datetime.now(timezone.utc)
    calendar = {}
    for year in range(int(created[:4]), now.year + 1):
        start = f"{year}-01-01T00:00:00Z"
        end = now.strftime("%Y-%m-%dT%H:%M:%SZ") if year == now.year else f"{year}-12-31T23:59:59Z"
        data = _graphql(CALENDAR_QUERY, {"login": login, "from": start, "to": end}, token)
        for week in data["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]:
            for day in week["contributionDays"]:
                if day["date"].startswith(str(year)):
                    calendar[day["date"]] = day["contributionCount"]
    return {"login": login, "created_at": created[:10], "repos": repos, "calendar": calendar}


def fetch_hf(author: str) -> dict | None:
    url = (f"https://huggingface.co/api/models?author={urllib.parse.quote(author)}"
           f"&expand%5B%5D=downloadsAllTime&limit=1000")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "profile-stats"})
        with urllib.request.urlopen(req, timeout=40) as resp:
            models = json.load(resp)
        return {"author": author, "models": len(models),
                "downloads": sum(m.get("downloadsAllTime") or 0 for m in models)}
    except Exception as exc:  # a missing tile beats a failed run
        print(f"::warning::Hugging Face stats unavailable: {exc}")
        return None


# ── Metrics ───────────────────────────────────────────────────────────────────

def metrics(data: dict, today: date) -> dict:
    days = {date.fromisoformat(d): c for d, c in data["calendar"].items() if date.fromisoformat(d) <= today}
    ordered = sorted(days)
    longest, run, best_end = 0, 0, None
    prev = None
    for d in ordered:
        if days[d] > 0:
            run = run + 1 if prev is not None and (d - prev).days == 1 and days[prev] > 0 else 1
            if run > longest:
                longest, best_end = run, d
        else:
            run = 0
        prev = d
    current, d = 0, today if days.get(today, 0) > 0 else today - timedelta(days=1)
    while days.get(d, 0) > 0:
        current += 1
        d -= timedelta(days=1)

    week0 = today - timedelta(days=(today.weekday() + 1) % 7)  # Sunday, like GitHub's grid
    weeks = []
    for i in range(51, -1, -1):
        start = week0 - timedelta(weeks=i)
        weeks.append((start, sum(days.get(start + timedelta(days=k), 0) for k in range(7))))

    counts, bytes_ = {}, {}
    for repo in data["repos"]:
        total = sum(repo["languages"].values())
        for lang, size in repo["languages"].items():
            bytes_[lang] = bytes_.get(lang, 0) + size
            if total and size / total >= LANG_SHARE:
                counts[lang] = counts.get(lang, 0) + 1
    langs = sorted(counts.items(), key=lambda kv: (-kv[1], -bytes_[kv[0]]))[:6]

    return {
        "total": sum(days.values()),
        "year": sum(c for d, c in days.items() if d > today - timedelta(days=365)),
        "active": sum(1 for c in days.values() if c > 0),
        "longest": longest,
        "longest_range": (best_end - timedelta(days=longest - 1), best_end) if best_end else None,
        "current": current,
        "weeks": weeks,
        "langs": langs,
        "repos": len(data["repos"]),
        "since": date.fromisoformat(data["created_at"]),
    }


# ── Rendering ─────────────────────────────────────────────────────────────────

def _num(n: int) -> str:
    return f"{n / 1000:.1f}K" if n >= 10_000 else f"{n:,}"


def _day(d: date, year=True) -> str:
    return f"{d:%b} {d.day}, {d.year}" if year else f"{d:%b} {d.day}"


def _column(x, base, w, h, r=4.0):
    """A column with a rounded data end and a square baseline."""
    r = min(r, w / 2, h)
    top = base - h
    return (f'M{fmt(x)} {fmt(base)} V{fmt(top + r)} Q{fmt(x)} {fmt(top)} {fmt(x + r)} {fmt(top)} '
            f'H{fmt(x + w - r)} Q{fmt(x + w)} {fmt(top)} {fmt(x + w)} {fmt(top + r)} V{fmt(base)} Z')


def _hbar(x, y, w, h, r=4.0):
    r = min(r, h / 2, w)
    return (f'M{fmt(x)} {fmt(y)} H{fmt(x + w - r)} Q{fmt(x + w)} {fmt(y)} {fmt(x + w)} {fmt(y + r)} '
            f'V{fmt(y + h - r)} Q{fmt(x + w)} {fmt(y + h)} {fmt(x + w - r)} {fmt(y + h)} H{fmt(x)} Z')


def _step(peak: int) -> int:
    raw = max(peak, 1) / 3
    mag = 10 ** math.floor(math.log10(raw)) if raw >= 1 else 1
    for m in (1, 2, 5, 10):
        if raw <= m * mag:
            return max(1, int(m * mag))
    return int(10 * mag)


def render(m: dict, hf: dict | None, t: dict, theme: str, today: date, login: str) -> str:
    W, H, pad = 1200, 520, 32
    ink_bar = CHART[theme]
    body = [rect(0.5, 0.5, W - 1, H - 1, 18, t["surface"], t["line"])]

    # Header
    body.append(text(pad, 56, "GitHub activity", "s7", 22, t["ink1"], tracking=-0.4))
    body.append(text(pad + text_width("GitHub activity", "s7", 22, -0.4) + 12, 56, f"public contributions · @{login}",
                     "m4", 12.5, t["ink3"]))
    stamp = f"Updated {_day(today)} · refreshes daily"
    sx = W - pad - text_width(stamp, "m4", 12.5)
    body.append(f'<circle class="live" cx="{fmt(sx - 14)}" cy="51.5" r="6.5" fill="{t["brand"]}" opacity=".25"/>'
                f'<circle cx="{fmt(sx - 14)}" cy="51.5" r="3.4" fill="{t["brand"]}"/>')
    body.append(text(W - pad, 56, stamp, "m4", 12.5, t["ink2"], anchor="end"))

    # KPI tiles
    if m["current"] > 0:
        streak_sub = f"current streak: {m['current']} day{'s' if m['current'] != 1 else ''}"
    elif m["longest_range"]:
        a, b = m["longest_range"]
        streak_sub = f"{_day(a, a.year != b.year)} – {_day(b)}"
    else:
        streak_sub = "—"
    tiles = [
        ("Contributions", _num(m["total"]), f"since {m['since']:%b %Y}"),
        ("Past 12 months", _num(m["year"]), f"{today - timedelta(days=364):%b %Y} – {today:%b %Y}"),
        ("Active days", _num(m["active"]), "days with a contribution"),
        ("Longest streak", f"{m['longest']} day{'s' if m['longest'] != 1 else ''}", streak_sub),
    ]
    if hf:
        tiles.append(("Model downloads", _num(hf["downloads"]), f"all-time · {hf['models']} HF models"))
    else:
        tiles.append(("Public repos", _num(m["repos"]), "excluding forks"))
    gap = 14
    tw = (W - 2 * pad - gap * (len(tiles) - 1)) / len(tiles)
    for i, (label, value, sub) in enumerate(tiles):
        x, y = pad + i * (tw + gap), 84
        body.append(f'<g class="fade" {delay(.08 + i * .08)}>'
                    + rect(x + .5, y + .5, tw - 1, 109, 14, t["surface2"], t["line"])
                    + text(x + 20, y + 32, label, "s5", 13.5, t["ink2"])
                    + text(x + 19, y + 74, value, "s7", 34, t["ink1"], tracking=-0.8)
                    + text(x + 20, y + 96, sub, "s4", 12.5, t["ink3"])
                    + "</g>")

    # Weekly contributions (single series: one hue, no legend; the title names it)
    cx0, cx1, top = pad, 736, 232
    weeks = m["weeks"]
    peak_i = max(range(len(weeks)), key=lambda i: (weeks[i][1], i))
    peak_v = weeks[peak_i][1]
    body.append(text(cx0, top + 12, "Weekly contributions", "s6", 16, t["ink1"]))
    sub = (f"Last 52 weeks · peak {peak_v} in the week of {_day(weeks[peak_i][0])}" if peak_v
           else "Last 52 weeks · no public contributions yet")
    body.append(text(cx0, top + 34, sub, "s4", 13, t["ink3"]))
    px0, px1, py0, py1 = cx0 + 34, cx1, top + 74, H - 62
    step = _step(peak_v)
    ymax = max(step, math.ceil(peak_v / step) * step)
    for v in range(0, ymax + 1, step):
        y = py1 - (py1 - py0) * v / ymax
        color = t["baseline"] if v == 0 else t["grid"]
        body.append(f'<path d="M{fmt(px0)} {fmt(y)} H{fmt(px1)}" stroke="{color}" stroke-width="1"/>')
        body.append(text(px0 - 10, y + 4, str(v), "m4", 11.5, t["ink3"], anchor="end"))
    slot = (px1 - px0) / len(weeks)
    bw = min(24, slot * 0.68)
    last_label_x = -99
    for i, (start, v) in enumerate(weeks):
        x = px0 + i * slot + (slot - bw) / 2
        if v:
            h = (py1 - py0) * v / ymax
            body.append(f'<path class="grow" {delay(.2 + i * .012)} d="{_column(x, py1, bw, h)}" fill="{ink_bar}"/>')
        # Label the first week of each month; a partial month at the left edge stays unlabeled.
        prev = weeks[i - 1][0] if i else None
        new_month = start.day <= 7 if prev is None else start.month != prev.month
        if new_month and x - last_label_x > 34:
            label = f"{start:%b} ’{start:%y}" if start.month == 1 else f"{start:%b}"
            body.append(text(x + bw / 2, py1 + 22, label, "m4", 11.5, t["ink3"], anchor="middle"))
            last_label_x = x
    if peak_v:
        x = px0 + peak_i * slot + slot / 2
        y = py1 - (py1 - py0) * peak_v / ymax
        body.append(text(x, y - 8, str(peak_v), "s6", 12.5, t["ink1"], anchor="middle"))

    # Languages by repository count
    lx0, lx1 = 776, W - pad
    body.append(f'<path d="M{lx0 - 24} {top - 4} V{H - pad}" stroke="{t["line"]}"/>')
    body.append(text(lx0, top + 12, "Languages across repositories", "s6", 16, t["ink1"]))
    body.append(text(lx0, top + 34, f"Repos where it is ≥ {int(LANG_SHARE * 100)}% of the code · forks excluded",
                     "s4", 13, t["ink3"]))
    langs = m["langs"]
    if langs:
        label_w = max(text_width(n, "s5", 13.5) for n, _ in langs) + 14
        bar_x0, bar_x1 = lx0 + label_w, lx1 - 30
        most = langs[0][1]
        for i, (name, n) in enumerate(langs):
            y = top + 74 + i * 34
            w = (bar_x1 - bar_x0) * n / most
            body.append(text(bar_x0 - 14, y + 11, name, "s5", 13.5, t["ink2"], anchor="end"))
            body.append(f'<path class="growx" {delay(.3 + i * .07)} d="{_hbar(bar_x0, y, w, 14)}" fill="{ink_bar}"/>')
            body.append(text(bar_x0 + w + 8, y + 11.5, str(n), "s6", 13.5, t["ink1"]))
        body.append(text(lx0, H - pad - 2, f"{m['repos']} public repositories", "s4", 12.5, t["ink3"]))

    css = (
        ".grow{transform-box:fill-box;transform-origin:50% 100%;animation:grow .8s cubic-bezier(.2,.7,.2,1) both}"
        "@keyframes grow{from{transform:scaleY(0)}to{transform:none}}"
        ".growx{transform-box:fill-box;transform-origin:0 50%;animation:growx .8s cubic-bezier(.2,.7,.2,1) both}"
        "@keyframes growx{from{transform:scaleX(0)}to{transform:none}}"
        ".live{transform-box:fill-box;transform-origin:center;animation:live 2.2s ease-out infinite}"
        "@keyframes live{0%{transform:scale(.6);opacity:.55}100%{transform:scale(2.1);opacity:0}}"
    )
    desc = (f"{m['total']:,} public contributions since {m['since']:%B %Y}; {m['year']:,} in the past 12 months; "
            f"{m['active']:,} active days; longest streak {m['longest']} days. "
            f"Busiest week: {peak_v} contributions (week of {_day(weeks[peak_i][0])}). "
            + ("Languages by repository count: " + ", ".join(f"{n} {c}" for n, c in langs) + ". " if langs else "")
            + (f"{hf['downloads']:,} all-time downloads across {hf['models']} Hugging Face models." if hf else ""))
    return document(W, H, "".join(body), css=css, title="GitHub activity", desc=desc)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--user", default=os.environ.get("GITHUB_REPOSITORY_OWNER", "yamrajkhadka"))
    ap.add_argument("--hf-user", default="yamraj047")
    ap.add_argument("--out", default="dist")
    ap.add_argument("--from-json", help="render from a saved snapshot instead of the APIs")
    ap.add_argument("--dump", help="also save the fetched snapshot here")
    ap.add_argument("--today", help="override today's date (YYYY-MM-DD), for previews")
    args = ap.parse_args()

    if args.from_json:
        snapshot = json.loads(Path(args.from_json).read_text())
    else:
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if not token:
            print("::error::GITHUB_TOKEN is not set")
            return 1
        try:
            snapshot = {"github": fetch_github(args.user, token), "hf": fetch_hf(args.hf_user)}
        except Exception as exc:
            print(f"::error::Could not fetch GitHub stats: {exc}")
            return 1
    if args.dump:
        Path(args.dump).write_text(json.dumps(snapshot, indent=1))

    today = date.fromisoformat(args.today) if args.today else datetime.now(timezone.utc).date()
    m = metrics(snapshot["github"], today)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for theme, palette in THEMES.items():
        (out / f"stats-{theme}.svg").write_text(
            render(m, snapshot.get("hf"), palette, theme, today, snapshot["github"]["login"]), encoding="utf-8")
    print(f"stats: {m['total']} contributions, longest streak {m['longest']}, "
          f"{len(m['langs'])} languages, hf={snapshot.get('hf')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
