"""Refreshes the live cards: about (neofetch), cp (ratings) and activity (contributions).

    python tools/update_live.py            # fetch + render
    python tools/update_live.py --offline  # render from tools/data/live.json only

Runs daily in .github/workflows/refresh-profile.yml. Every source is optional:
if one fails, the last good value from tools/data/live.json is kept.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import os
import re
import sys
import urllib.request

from svgkit import THEMES, TOOLS, Doc, card, chip, fmt, keyframes, measure

USER = "Razeefshaik"
CF_HANDLE = "Razeef"
ATCODER = "RazeefShaik"
JOINED = dt.date(2023, 10, 28)
CACHE = TOOLS / "data" / "live.json"

# not available from a public API; edit here when they change
STATIC = {
    "leetcode": {"peak": 2032, "badge": "Knight"},
    "codechef": {"peak": 1723, "stars": 3},
    "problems": "1,500+",
}


# ----------------------------------------------------------------- fetch ---
def get(url: str, *, json_out=True, headers=None):
    h = {"User-Agent": "razeefshaik-profile-refresh", **(headers or {})}
    if "api.github.com" in url and os.environ.get("GITHUB_TOKEN"):
        h["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=25) as r:
        body = r.read().decode("utf-8")
    return json.loads(body) if json_out else body


def fetch_github():
    user = get(f"https://api.github.com/users/{USER}")
    repos = get(f"https://api.github.com/users/{USER}/repos?per_page=100&type=owner")
    commits = get(f"https://api.github.com/search/commits?q=author:{USER}&per_page=1",
                  headers={"Accept": "application/vnd.github+json"})
    return {
        "repos": user["public_repos"],
        "own_repos": sum(1 for r in repos if not r["fork"]),
        "stars": sum(r["stargazers_count"] for r in repos),
        "followers": user["followers"],
        "commits": commits["total_count"],
    }


def fetch_calendar():
    page = get(f"https://github.com/users/{USER}/contributions", json_out=False)
    cells = re.findall(r'<td[^>]*data-date="([\d-]+)"[^>]*id="([^"]+)"[^>]*data-level="(\d)"', page)
    tips = dict(re.findall(r'<tool-tip[^>]*for="([^"]+)"[^>]*>([^<]+)</tool-tip>', page))
    days = []
    for date, cid, level in cells:
        m = re.match(r"(\d+|No) contribution", tips.get(cid, "No"))
        days.append([date, 0 if not m or m.group(1) == "No" else int(m.group(1)), int(level)])
    if len(days) < 300:
        raise ValueError("contribution calendar not found")
    days.sort()
    return days


def fetch_codeforces():
    info = get(f"https://codeforces.com/api/user.info?handles={CF_HANDLE}")["result"][0]
    hist = get(f"https://codeforces.com/api/user.rating?handle={CF_HANDLE}")["result"]
    return {"rating": info.get("rating"), "max": info.get("maxRating"), "rank": info.get("rank"),
            "max_rank": info.get("maxRank"), "history": [h["newRating"] for h in hist]}


def fetch_atcoder():
    hist = [h["NewRating"] for h in get(f"https://atcoder.jp/users/{ATCODER}/history/json") if h["IsRated"]]
    return {"rating": hist[-1], "max": max(hist), "history": hist}


def refresh(offline: bool) -> dict:
    data = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    if not offline:
        for key, fn in (("github", fetch_github), ("calendar", fetch_calendar),
                        ("codeforces", fetch_codeforces), ("atcoder", fetch_atcoder)):
            try:
                data[key] = fn()
                print(f"ok   {key}")
            except Exception as e:  # keep the last good value
                print(f"keep {key}: {e!r}", file=sys.stderr)
        data["updated"] = dt.date.today().isoformat()
    CACHE.parent.mkdir(exist_ok=True)
    CACHE.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
    return data


# --------------------------------------------------------------- helpers ---
def streaks(days):
    counts = [c for _, c, _ in days]
    longest = run = 0
    for c in counts:
        run = run + 1 if c else 0
        longest = max(longest, run)
    current = 0
    i = len(counts) - 1
    if counts and counts[-1] == 0:  # today may not have started yet
        i -= 1
    while i >= 0 and counts[i]:
        current += 1
        i -= 1
    best = max(days, key=lambda d: d[1])
    return current, longest, best


def uptime(today: dt.date) -> str:
    months = (today.year - JOINED.year) * 12 + today.month - JOINED.month
    if today.day < JOINED.day:
        months -= 1
    anchor_m = JOINED.month + months
    anchor = dt.date(JOINED.year + (anchor_m - 1) // 12, (anchor_m - 1) % 12 + 1, JOINED.day)
    days = (today - anchor).days
    y, m = divmod(months, 12)
    plural = lambda n, w: f"{n} {w}{'' if n == 1 else 's'}"
    return f"{plural(y, 'year')}, {plural(m, 'month')}, {plural(days, 'day')}"


def cf_color(t, rating):
    if rating is None:
        return t["muted"]
    for floor, color in ((2100, t["amber"]), (1900, "#B36BFF"), (1600, t["blue"]), (1400, "#2EC4C4"), (1200, t["teal"])):
        if rating >= floor:
            return color
    return t["muted"]


def atcoder_color(t, rating):
    for floor, name, color in ((2000, "Yellow", t["amber"]), (1600, "Blue", t["blue"]), (1200, "Cyan", "#2EC4C4"),
                               (800, "Green", t["teal"]), (400, "Brown", "#B07A4A"), (0, "Gray", t["muted"])):
        if rating >= floor:
            return name, color
    return "Gray", t["muted"]


def atcoder_kyu(rating):
    if rating >= 2000:
        return f"{(rating - 2000) // 200 + 1} Dan"
    return f"{max(1, (2000 - rating - 1) // 200 + 1 - 0)} Kyu" if rating >= 400 else "—"


def spark(d: Doc, values, x, y, w, h, color, label_max=True):
    t = d.t
    if len(values) < 2:
        return
    lo, hi = min(values), max(values)
    span = max(hi - lo, 1)
    pts = [(x + i * w / (len(values) - 1), y + h - (v - lo) / span * h) for i, v in enumerate(values)]
    path = "M" + " L".join(f"{px:.1f},{py:.1f}" for px, py in pts)
    g = d.uid("sg")
    d.define(f'<linearGradient id="{g}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{color}" stop-opacity=".28"/>'
             f'<stop offset="1" stop-color="{color}" stop-opacity="0"/></linearGradient>')
    length = sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))
    k = d.uid("ln")
    d.style(keyframes(k, [(0, f"stroke-dashoffset:{length:.0f}"), (100, "stroke-dashoffset:0")])
            + f".{k}{{animation:{k} 2.2s cubic-bezier(.3,.6,.2,1) both}}")
    d.add(f'<path d="{path} L{pts[-1][0]:.1f},{y + h} L{x},{y + h} Z" fill="url(#{g})"/>',
          f'<path class="{k}" d="{path}" stroke="{color}" stroke-width="2" stroke-linejoin="round" '
          f'stroke-dasharray="{length:.0f}"/>')
    i = values.index(hi)
    d.add(f'<circle cx="{pts[i][0]:.1f}" cy="{pts[i][1]:.1f}" r="3.5" fill="{t["bg"]}" stroke="{color}" stroke-width="2"/>')
    d.add(f'<circle cx="{pts[-1][0]:.1f}" cy="{pts[-1][1]:.1f}" r="2.6" fill="{color}"/>')


# ----------------------------------------------------------------- about ---
def about(t, data):
    today = dt.date.fromisoformat(data.get("updated", dt.date.today().isoformat()))
    gh = data.get("github", {})
    cal = data.get("calendar", [])
    year_total = sum(c for _, c, _ in cal)
    portrait = json.loads((TOOLS / "data" / "portrait.json").read_text(encoding="utf-8"))

    rows = [
        ("OS", "B.Tech EE · NIT Silchar · class of 2027"),
        ("Uptime", uptime(today)),
        ("Kernel", "backend · distributed systems · agent infra"),
        ("Shell", "Java · Go · C++ · Python · TypeScript"),
        ("Packages", f"{gh.get('repos', 36)} repos · GoEgg v0.1.4 on pkg.go.dev"),
        ("CPU", f"{STATIC['problems']} problems · CF Expert · LC Knight"),
        ("Memory", "WAL-backed, fsync'd before every mutation"),
        ("Motto", '"What happens when it crashes?"'),
        None,
        ("Email", "shaikrazeef2@gmail.com"),
        ("LinkedIn", "in/shaik-mahammad-razeef"),
        ("Blog", "dev.to/razeef_shaik"),
        None,
        ("Contributions", f"{fmt(year_total)} this year · {fmt(gh.get('commits', 0))} commits"),
        ("Building", "Premise · ForgeFlow · JevRouter"),
    ]
    desc = "; ".join(f"{k}: {v}" for k, v in (r for r in rows if r))
    d = Doc(1000, 500, t, "razeef@silchar — neofetch", "Terminal-style profile card with a halftone portrait. " + desc)
    card(d)
    # window chrome
    for i, c in enumerate((t["red"], t["amber"], t["teal"])):
        d.add(f'<circle cx="{26 + i * 18}" cy="22" r="5.5" fill="{c}" opacity=".85"/>')
    d.add(d.text(500, 26.5, "razeef@silchar: ~", "mono", 12, t["muted"], "middle"),
          f'<line x1="0" y1="44" x2="1000" y2="44" stroke="{t["line"]}"/>')

    # halftone portrait
    px, py, pw = 30, 62, 360
    ph = pw * portrait["aspect"]
    colors = {"t": t["text"], "e": t["ember"], "a": t["amber"]}
    cell = portrait["cell"] * pw
    bands: dict[int, list[str]] = {}
    for x, y, lum, tone in portrait["dots"]:
        # light mode prints ink like a newspaper halftone; the laptop's glow stays a glow
        v = lum if t["name"] == "dark" or tone == "e" else 1 - lum
        r = cell / 2 * (0.08 + 0.95 * v ** (1.2 if t["name"] == "dark" else 1.3))
        if r < 0.35:
            continue
        bands.setdefault(int(y * 60), []).append(
            f'<circle cx="{px + x * pw:.1f}" cy="{py + y * pw:.1f}" r="{r:.2f}" fill="{colors[tone]}"/>')
    d.style("@keyframes scan{from{opacity:0}to{opacity:1}}.scan{animation:scan .5s ease-out both}")
    for band, circles in sorted(bands.items()):
        d.add(f'<g class="scan" style="animation-delay:{band * 0.025:.2f}s">' + "".join(circles) + "</g>")
    # scanline sweeping the portrait
    g = d.uid("sl")
    d.define(f'<linearGradient id="{g}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{t["ember"]}" stop-opacity="0"/>'
             f'<stop offset="1" stop-color="{t["ember"]}" stop-opacity=".35"/></linearGradient>')
    d.style(f"@keyframes sweepy{{0%{{transform:translateY(0);opacity:0}}10%{{opacity:1}}90%{{opacity:1}}"
            f"100%{{transform:translateY({ph - 30:.0f}px);opacity:0}}}}.sweepy{{animation:sweepy 6s ease-in-out infinite 1.5s both}}")
    d.add(f'<rect class="sweepy" x="{px}" y="{py}" width="{pw}" height="30" fill="url(#{g})" opacity="0"/>')

    # info column
    x0, y = 420, 82
    lines = [d.runs(x0, y, [("razeef@silchar", "mono-b", t["ember"]), (" ~ $ ", "mono", t["muted"]),
                            ("neofetch", "mono", t["text"])], size=13.5)]
    y += 32
    lines.append(d.runs(x0, y, [("razeef", "mono-b", t["ember"]), ("@", "mono-b", t["muted"]),
                                ("silchar", "mono-b", t["ember"])], size=16))
    y += 12
    lines.append(f'<line x1="{x0}" y1="{y}" x2="{x0 + measure("razeef@silchar", "mono-b", 16)}" y2="{y}" '
                 f'stroke="{t["line2"]}" stroke-dasharray="3 3"/>')
    y += 24
    key_w = 15
    for row in rows:
        if row is None:
            y += 8
            continue
        k, v = row
        lines.append(d.runs(x0, y, [(k + " ", "mono-b", t["amber"]),
                                    ("." * (key_w - len(k)) + " ", "mono", t["dim"]),
                                    (v, "mono", t["text"])], size=13.5))
        y += 21.5
    y += 6
    for i, key in enumerate(("bg", "red", "ember", "amber", "teal", "blue", "muted", "text")):
        lines.append(f'<rect x="{x0 + i * 30}" y="{y}" width="26" height="14" rx="3" fill="{t[key]}" '
                     f'stroke="{t["line2"]}"/>')
    d.style("@keyframes boot{from{opacity:0;transform:translateX(-6px)}to{opacity:1;transform:none}}"
            ".boot{animation:boot .35s ease-out both}")
    for i, el in enumerate(lines):
        d.add(f'<g class="boot" style="animation-delay:{0.3 + i * 0.07:.2f}s">{el}</g>')
    d.add(d.text(976, 486, f"refreshed {today.isoformat()}", "mono", 10, t["dim"], "end"))
    return d


# -------------------------------------------------------------------- cp ---
def cp(t, data):
    cf = data.get("codeforces", {})
    at = data.get("atcoder", {})
    lc, cc = STATIC["leetcode"], STATIC["codechef"]
    at_name, at_col = atcoder_color(t, at.get("max", 0))
    d = Doc(1000, 372, t, "Competitive programming",
            f"Codeforces peak {cf.get('max')} ({cf.get('max_rank')}), now {cf.get('rating')}. "
            f"LeetCode peak {lc['peak']} ({lc['badge']}). AtCoder peak {at.get('max')} ({at_name}, {atcoder_kyu(at.get('max', 0))}). "
            f"CodeChef {cc['stars']} star, peak {cc['peak']}. {STATIC['problems']} problems solved across five judges.")
    card(d)
    tiles = [
        ("CODEFORCES", CF_HANDLE, cf.get("max"), (cf.get("max_rank") or "").title(), cf_color(t, cf.get("max")),
         f"now {cf.get('rating')} · {(cf.get('rank') or '').lower()} · {len(cf.get('history', []))} contests", cf.get("history", [])),
        ("LEETCODE", "RAZEEF_SHAIK", lc["peak"], lc["badge"], t["amber"], "peak contest rating", None),
        ("ATCODER", ATCODER, at.get("max"), f"{at_name} · {atcoder_kyu(at.get('max', 0))}", at_col,
         f"now {at.get('rating')} · {len(at.get('history', []))} rated contests", at.get("history", [])),
    ]
    tw, gap, x0, y0, th = 304, 16, 24, 24, 252
    for i, (name, handle, peak, title, color, sub, hist) in enumerate(tiles):
        x = x0 + i * (tw + gap)
        d.add(f'<rect x="{x}" y="{y0}" width="{tw}" height="{th}" rx="16" fill="{t["surface"]}" stroke="{t["line"]}"/>')
        d.add(d.text(x + 20, y0 + 32, name, "mono-b", 11, t["ember"], spacing=1.6),
              d.text(x + tw - 20, y0 + 32, handle, "mono", 11, t["muted"], "end"))
        d.add(d.text(x + 18, y0 + 92, str(peak), "serif", 60, t["text"], spacing=-1))
        nx = x + 26 + measure(str(peak), "serif", 60, -1)
        d.add(d.text(nx, y0 + 70, "PEAK", "mono", 10, t["muted"], spacing=1.4),
              d.text(nx, y0 + 90, title, "sans-m", 15, color))
        d.add(d.text(x + 20, y0 + 120, sub, "mono", 11, t["muted"]))
        if hist:
            spark(d, hist, x + 20, y0 + 146, tw - 40, 84, color)
        else:  # LeetCode: no public history for this handle, draw the badge ribbon instead
            cx, cy = x + tw / 2, y0 + 190
            d.add(f'<path d="M{cx},{cy - 44} l38,22 v44 l-38,22 l-38,-22 v-44 Z" fill="{t["surface2"]}" '
                  f'stroke="{color}" stroke-width="1.6"/>',
                  f'<path d="M{cx},{cy - 30} l26,15 v30 l-26,15 l-26,-15 v-30 Z" stroke="{color}" stroke-opacity=".45"/>')
            d.add(d.text(cx, cy + 7, "K", "serif-i", 30, color, "middle"))
            for s in (-1, 1):
                d.add(f'<path d="M{cx + s * 54},{cy + 30} q{s * 14},-26 {s * 4},-58" stroke="{t["line2"]}" stroke-width="1.4"/>')
    sy = y0 + th + 22
    d.add(f'<line x1="24" y1="{sy}" x2="976" y2="{sy}" stroke="{t["line"]}"/>')
    items = [("CODECHEF", f"{cc['stars']}★ · peak {cc['peak']}"), ("SOLVED", f"{STATIC['problems']} across five judges"),
             ("ALSO", "problem setter on Codeforces Polygon")]
    for i, (k, v) in enumerate(items):
        x = 28 + i * 318
        d.add(d.runs(x, sy + 34, [(k + "  ", "mono-b", t["ember"]), (v, "sans", t["soft"])], size=13.5, spacing=0.3))
    return d


# -------------------------------------------------------------- activity ---
def activity(t, data):
    cal = data.get("calendar", [])
    total = sum(c for _, c, _ in cal)
    cur, longest, best = streaks(cal) if cal else (0, 0, ["", 0, 0])
    best_date = dt.date.fromisoformat(best[0]).strftime("%b %d").replace(" 0", " ") if best[0] else "—"
    d = Doc(1000, 300, t, "Contribution activity",
            f"{total} contributions in the last year. Current streak {cur} days, longest {longest} days, "
            f"best day {best[1]} contributions on {best_date}.")
    card(d)
    d.add(d.text(36, 66, fmt(total), "serif", 52, t["text"], spacing=-1))
    d.add(d.text(44 + measure(fmt(total), "serif", 52, -1), 64, "contributions in the last year", "sans", 16, t["muted"]))
    stats = [("CURRENT STREAK", f"{cur}d"), ("LONGEST", f"{longest}d"), ("BEST DAY", f"{best[1]} · {best_date}")]
    x = 964
    for k, v in reversed(stats):
        w = max(measure(k, "mono", 10, 1.4), measure(v, "mono-b", 16))
        d.add(d.text(x, 44, k, "mono", 10, t["muted"], "end", 1.4), d.text(x, 68, v, "mono-b", 16, t["ember"], "end"))
        x -= w + 34

    if not cal:
        return d
    first = dt.date.fromisoformat(cal[0][0])
    start = first - dt.timedelta(days=(first.weekday() + 1) % 7)  # weeks start on Sunday
    cell, pitch = 13, 16.2
    weeks = (dt.date.fromisoformat(cal[-1][0]) - start).days // 7 + 1
    gx = (1000 - weeks * pitch) / 2 + 10
    gy = 118
    shades = [t["surface2"], f'{t["ember"]}', t["ember"], t["ember"], t["amber"]]
    alphas = [1, .3, .55, .85, 1]
    d.style("@keyframes ignite{from{opacity:.08}to{opacity:1}}.ig{animation:ignite .6s ease-out both}")
    cols: dict[int, list[str]] = {}
    month_seen = set()
    for date, count, level in cal:
        day = dt.date.fromisoformat(date)
        wk = (day - start).days // 7
        dow = (day.weekday() + 1) % 7
        x, y = gx + wk * pitch, gy + dow * pitch
        stroke = f' stroke="{t["line"]}"' if level == 0 else ""
        cols.setdefault(wk, []).append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{cell}" height="{cell}" rx="3" fill="{shades[level]}" '
            f'fill-opacity="{alphas[level]}"{stroke}/>')
        if day.day <= 7 and dow == 0 and (day.year, day.month) not in month_seen:
            month_seen.add((day.year, day.month))
            d.add(d.text(x, gy - 10, day.strftime("%b"), "mono", 10.5, t["muted"]))
    for wk, rects in sorted(cols.items()):
        d.add(f'<g class="ig" style="animation-delay:{wk * 0.028:.2f}s">' + "".join(rects) + "</g>")
    for dow, lab in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        d.add(d.text(gx - 10, gy + dow * pitch + 10.5, lab, "mono", 10, t["muted"], "end"))
    # scanner sweeping the grid
    g = d.uid("scan")
    d.define(f'<linearGradient id="{g}" x1="0" x2="1"><stop offset="0" stop-color="{t["amber"]}" stop-opacity="0"/>'
             f'<stop offset=".8" stop-color="{t["amber"]}" stop-opacity=".22"/><stop offset="1" stop-color="{t["amber"]}" stop-opacity=".6"/></linearGradient>')
    span = weeks * pitch
    d.style(f"@keyframes sweepx{{0%{{transform:translateX(0);opacity:0}}8%{{opacity:1}}85%{{opacity:1}}"
            f"100%{{transform:translateX({span:.0f}px);opacity:0}}}}.sweepx{{animation:sweepx 7s ease-in-out 2.4s infinite both}}")
    d.add(f'<rect class="sweepx" x="{gx - 60:.1f}" y="{gy - 4}" width="60" height="{7 * pitch + 4:.0f}" rx="4" fill="url(#{g})" opacity="0"/>')
    ly = gy + 7 * pitch + 30
    d.add(d.text(gx, ly, f"github.com/{USER} · refreshed {data.get('updated', '')}", "mono", 10.5, t["dim"]))
    lx = gx + weeks * pitch - 5 * pitch - 34
    d.add(d.text(lx - 8, ly, "less", "mono", 10.5, t["muted"], "end"))
    for i in range(5):
        stroke = f' stroke="{t["line"]}"' if i == 0 else ""
        d.add(f'<rect x="{lx + i * pitch:.1f}" y="{ly - 11}" width="{cell}" height="{cell}" rx="3" fill="{shades[i]}" '
              f'fill-opacity="{alphas[i]}"{stroke}/>')
    d.add(d.text(lx + 5 * pitch + 4, ly, "more", "mono", 10.5, t["muted"]))
    return d


def main():
    data = refresh(offline="--offline" in sys.argv)
    for name, fn in (("about", about), ("cp", cp), ("activity", activity)):
        for t in THEMES:
            path = fn(t, data).save(name)
            print(f"{path.relative_to(path.parents[3])}  {path.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
