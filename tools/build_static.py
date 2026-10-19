"""Builds the hand-designed (non-live) profile artwork into assets/v3/{dark,light}.

    python tools/build_static.py
"""
from __future__ import annotations

import math
import random
import re

from svgkit import THEMES, TOOLS, Doc, card, chip, chips, dot_grid, glow, keyframes, measure

W = 1000


# ---------------------------------------------------------------- motion ---
def particles(doc: Doc, n=18, x0=30, x1=970, y=None, rise=230, seed=7, color=None):
    """Embers drifting upward."""
    t = doc.t
    rnd = random.Random(seed)
    y = doc.h + 6 if y is None else y
    doc.style(
        "@keyframes ember{0%{transform:translateY(0);opacity:0}15%{opacity:.9}"
        f"100%{{transform:translateY(-{rise}px);opacity:0}}}}"
        ".ember{animation:ember linear infinite both}"
    )
    out = []
    for _ in range(n):
        x = rnd.uniform(x0, x1)
        r = rnd.uniform(0.8, 2.2)
        dur = rnd.uniform(6, 12)
        delay = -rnd.uniform(0, dur)
        c = color or rnd.choice([t["ember"], t["ember"], t["amber"]])
        out.append(
            f'<circle class="ember" cx="{x:.1f}" cy="{y:.1f}" r="{r:.2f}" fill="{c}" '
            f'style="animation-duration:{dur:.2f}s;animation-delay:{delay:.2f}s"/>'
        )
    doc.add(*out)


def typewriter(doc: Doc, x0, y, phrases, size=15, face="mono", fill=None, per=4.6, cps=0.05):
    """Types and erases phrases in turn (SMIL, works inside <img>)."""
    t = doc.t
    cw = measure("M", face, size)
    total = per * len(phrases)
    cursor_t, cursor_x = [0.0], [x0]
    for i, s in enumerate(phrases):
        start = i * per
        n = len(s)
        times, widths = [0.0], [0.0]
        if start > 0:
            times.append(start)
            widths.append(0.0)
        for k in range(1, n + 1):
            times.append(start + k * cps)
            widths.append(k * cw)
        erase = start + per - 0.55
        steps = 8
        for k in range(1, steps + 1):
            times.append(erase + k * 0.05)
            widths.append(max(0.0, n * cw * (1 - k / steps)))
        times.append(start + per)
        widths.append(0.0)
        cursor_t += times[1:]
        cursor_x += [x0 + w for w in widths[1:]]
        kt = ";".join(f"{min(tt / total, 1):.4f}" for tt in times)
        if times[-1] < total:
            kt += ";1"
            widths.append(0.0)
        vals = ";".join(f"{w:.1f}" for w in widths)
        clip = doc.uid("type")
        doc.define(
            f'<clipPath id="{clip}"><rect x="{x0}" y="{y - size}" width="0" height="{size * 1.5}">'
            f'<animate attributeName="width" dur="{total}s" repeatCount="indefinite" calcMode="discrete" '
            f'keyTimes="{kt}" values="{vals}"/></rect></clipPath>'
        )
        doc.add(f'<g clip-path="url(#{clip})">{doc.text(x0, y, s, face, size, fill or t["text"])}</g>')
    # one cursor that follows whichever phrase is active
    pairs = sorted(zip(cursor_t, cursor_x))
    kt = ";".join(f"{min(p[0] / total, 1):.4f}" for p in pairs)
    vals = ";".join(f"{p[1]:.1f}" for p in pairs)
    if pairs[-1][0] < total:
        kt += ";1"
        vals += f";{x0}"
    doc.style("@keyframes blink{0%,49%{opacity:1}50%,100%{opacity:0}}.cur{animation:blink 1s steps(1) infinite}")
    doc.add(
        f'<rect class="cur" x="{x0}" y="{y - size * 0.82:.1f}" width="{cw * 0.55:.1f}" height="{size * 1.05:.1f}" fill="{t["ember"]}">'
        f'<animate attributeName="x" dur="{total}s" repeatCount="indefinite" calcMode="discrete" keyTimes="{kt}" values="{vals}"/></rect>'
    )


# ------------------------------------------------------------------ hero ---
HERO_PHRASES = [
    "what happens when it crashes?",
    "replay the WAL, then answer the query.",
    "simulate the pull request before it ships.",
    "route each task to the cheapest model that works.",
]

HERO_NODES = {  # name: (x, y, r)
    "core": (812, 176, 9),
    "wal": (712, 92, 4.5),
    "shard-03": (902, 84, 4.5),
    "hnsw": (948, 186, 4.5),
    "kafka": (900, 276, 4.5),
    "grpc": (756, 282, 4.5),
    "e-graph": (676, 196, 4.5),
    "mcp": (808, 54, 3.5),
    "adr-012": (640, 120, 3.5),
    "router": (958, 132, 3.5),
    "cache": (842, 318, 3.5),
}
HERO_EDGES = [
    ("core", "wal"), ("core", "shard-03"), ("core", "hnsw"), ("core", "kafka"), ("core", "grpc"),
    ("core", "e-graph"), ("wal", "mcp"), ("mcp", "shard-03"), ("wal", "adr-012"), ("adr-012", "e-graph"),
    ("shard-03", "router"), ("router", "hnsw"), ("hnsw", "kafka"), ("kafka", "cache"), ("cache", "grpc"),
    ("grpc", "e-graph"),
]


def hero(t):
    d = Doc(W, 400, t, "Razeef Shaik — software engineer, backend and distributed systems",
            "Animated banner: Razeef Shaik. Engineered for the edge case. Crash-safe storage, concurrent Go, "
            "and AI agents that reason over graphs. NIT Silchar, B.Tech EE 2027.")
    card(d, grain=True)
    glow(d, 860, 360, 430, t["ember"], 0.30 * t["glow"] / 0.55)
    glow(d, 812, 176, 170, t["amber"], 0.20 * t["glow"] / 0.55)
    dot_grid(d, 0.5, 0.5, 999, 399, step=22, fade_cx=820, fade_cy=180, fade_r=330)

    # eyebrow
    d.style("@keyframes pulse{0%,100%{opacity:1}50%{opacity:.25}}.pulse{animation:pulse 2.4s ease-in-out infinite}")
    d.add(f'<circle class="pulse" cx="52" cy="58" r="4.5" fill="{t["teal"]}"/>',
          f'<circle cx="52" cy="58" r="8.5" stroke="{t["teal"]}" stroke-opacity=".35"/>')
    d.add(d.text(68, 62.5, "SOFTWARE ENGINEER  ·  BACKEND & DISTRIBUTED SYSTEMS", "mono", 12.5, t["muted"], spacing=1.6))

    # name
    g = d.uid("name")
    d.define(f'<linearGradient id="{g}" x1="0" x2="1"><stop offset="0" stop-color="{t["ember"]}"/>'
             f'<stop offset="1" stop-color="{t["amber"]}"/></linearGradient>')
    size = 108
    x2 = 44 + measure("Razeef ", "serif", size)
    d.style("@keyframes rise{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:none}}"
            ".rise{animation:rise .9s cubic-bezier(.2,.7,.2,1) both}")
    d.add(f'<g class="rise">{d.text(42, 168, "Razeef", "serif", size, t["text"], spacing=-1)}'
          f'{d.text(x2 - 4, 168, "Shaik", "serif-i", size, f"url(#{g})", spacing=-1)}</g>')

    # tagline
    d.add(f'<g class="rise" style="animation-delay:.15s">' + d.runs(46, 214, [
        ("Engineered for the ", "sans-m", t["text"]), ("edge case.", "serif-i", t["ember"])], size=26) + "</g>")
    d.add(f'<g class="rise" style="animation-delay:.3s">' + d.text(
        46, 246, "Crash-safe storage, concurrent Go, and AI agents that reason over graphs.",
        "sans", 16.5, t["muted"]) + "</g>")

    # terminal line
    d.add(f'<rect x="44" y="270" width="560" height="44" rx="12" fill="{t["surface2"]}" stroke="{t["line"]}"/>')
    d.add(d.text(62, 297.5, "$", "mono-b", 15, t["ember"]))
    typewriter(d, 80, 297.5, HERO_PHRASES, size=15, fill=t["text"])

    # graph
    nodes = HERO_NODES
    for a, b in HERO_EDGES:
        (x1, y1, _), (x2_, y2, _) = nodes[a], nodes[b]
        d.add(f'<line x1="{x1}" y1="{y1}" x2="{x2_}" y2="{y2}" stroke="{t["line2"]}" stroke-width="1"/>')
    rnd = random.Random(3)
    for i, (a, b) in enumerate(HERO_EDGES):
        (x1, y1, _), (x2_, y2, _) = nodes[a], nodes[b]
        if rnd.random() < 0.35:
            x1, y1, x2_, y2 = x2_, y2, x1, y1
        dur = rnd.uniform(2.2, 4.2)
        d.add(f'<circle r="2.2" fill="{t["ember"]}" opacity="0">'
              f'<animateMotion dur="{dur:.2f}s" begin="{-rnd.uniform(0, dur):.2f}s" repeatCount="indefinite" '
              f'path="M{x1},{y1} L{x2_},{y2}"/>'
              f'<animate attributeName="opacity" dur="{dur:.2f}s" begin="{-rnd.uniform(0, dur):.2f}s" '
              f'repeatCount="indefinite" values="0;1;1;0" keyTimes="0;.15;.85;1"/></circle>')
    d.style("@keyframes spin{to{transform:rotate(360deg)}}"
            ".spin{transform-box:fill-box;transform-origin:center;animation:spin 18s linear infinite}"
            ".spin-r{transform-box:fill-box;transform-origin:center;animation:spin 28s linear infinite reverse}")
    for name, (x, y, r) in nodes.items():
        if name == "core":
            continue
        d.add(f'<circle cx="{x}" cy="{y}" r="{r + 3}" fill="{t["bg"]}"/>',
              f'<circle cx="{x}" cy="{y}" r="{r}" fill="{t["surface2"]}" stroke="{t["soft"]}" stroke-width="1.2"/>')
        anchor = "start" if x < 940 else "end"
        dx = r + 7 if anchor == "start" else -(r + 7)
        d.add(d.text(x + dx, y - r - 4, name, "mono", 11, t["muted"], anchor))
    cx, cy, _ = nodes["core"]
    d.add(f'<circle class="spin" cx="{cx}" cy="{cy}" r="34" stroke="{t["ember"]}" stroke-opacity=".55" stroke-dasharray="2 7"/>',
          f'<circle class="spin-r" cx="{cx}" cy="{cy}" r="52" stroke="{t["amber"]}" stroke-opacity=".28" stroke-dasharray="14 10 2 10"/>',
          f'<circle cx="{cx}" cy="{cy}" r="20" fill="{t["bg"]}" stroke="{t["ember"]}" stroke-width="1.5"/>',
          f'<circle class="pulse" cx="{cx}" cy="{cy}" r="8" fill="{t["ember"]}"/>')

    # footer strip
    d.add(f'<line x1="44" y1="342" x2="956" y2="342" stroke="{t["line"]}"/>')
    d.add(d.text(44, 372, "NIT SILCHAR · EE '27", "mono", 11.5, t["muted"], spacing=1.2),
          d.text(500, 372, "JAVA · GO · C++ · PYTHON · TS", "mono", 11.5, t["muted"], "middle", 1.2),
          d.text(956, 372, "CF EXPERT · LC KNIGHT", "mono", 11.5, t["muted"], "end", 1.2))
    clip = d.uid("clip")
    d.define(f'<clipPath id="{clip}"><rect x="1" y="1" width="998" height="398" rx="22"/></clipPath>')
    d.add(f'<g clip-path="url(#{clip})">')
    particles(d, n=16, x0=600, x1=980)
    d.add("</g>")
    return d


# ----------------------------------------------------------------- icons ---
ICON_DIR = TOOLS / "icons"
# devicon colors that disappear on an obsidian tile
DARK_FIX = {"#231f20": "#E9E2D8", "#003956": "#5AA9D6", "#3a4d54": "#C9D6DA"}


def icon(doc: Doc, file: str, x, y, size, color=None) -> str:
    raw = (ICON_DIR / file).read_text(encoding="utf-8")
    vb = re.search(r'viewBox="([^"]+)"', raw).group(1)
    inner = re.sub(r"^.*?<svg[^>]*>|</svg>\s*$", "", raw, flags=re.S)
    inner = re.sub(r"<title>.*?</title>", "", inner, flags=re.S)
    pre = doc.uid("ic")
    inner = re.sub(r'id="([^"]+)"', lambda m: f'id="{pre}{m.group(1)}"', inner)
    inner = re.sub(r"url\(#([^)]+)\)", lambda m: f"url(#{pre}{m.group(1)})", inner)
    inner = re.sub(r'href="#([^"]+)"', lambda m: f'href="#{pre}{m.group(1)}"', inner)
    if doc.t["name"] == "dark":
        for k, v in DARK_FIX.items():
            inner = re.sub(k, v, inner, flags=re.I)
    fill = f' fill="{color}"' if color else ""
    return f'<svg x="{x:g}" y="{y:g}" width="{size}" height="{size}" viewBox="{vb}"{fill}>{inner}</svg>'


def glyph(doc: Doc, kind: str, x, y, size, color) -> str:
    """Small line glyphs drawn in a 16-unit box."""
    s = size / 16
    g = f'<g transform="translate({x:g} {y:g}) scale({s:g})" stroke="{color}" stroke-width="1.5" fill="none" stroke-linecap="round">'
    if kind == "globe":
        return g + '<circle cx="8" cy="8" r="6.8"/><ellipse cx="8" cy="8" rx="3" ry="6.8"/><path d="M1.4 8h13.2"/></g>'
    if kind == "in":
        doc.use_chars("sans-b", "in")
        return (f'<g transform="translate({x:g} {y:g}) scale({s:g})"><rect width="16" height="16" rx="3.5" fill="{color}"/>'
                f'<text x="8" y="12.2" font-size="10.5" text-anchor="middle" class="f-sans-b" fill="{doc.t["bg"]}">in</text></g>')
    if kind == "arrow":
        return g + '<path d="M3 8h10M9 4l4 4-4 4"/></g>'
    raise ValueError(kind)


# ----------------------------------------------------------------- utils ---
def rgba(hex_: str, a: float) -> str:
    h = hex_.lstrip("#")
    return f"rgba({int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)},{a})"


def clip_card(d: Doc, rx=22):
    c = d.uid("clip")
    d.define(f'<clipPath id="{c}"><rect x="1" y="1" width="{d.w - 2}" height="{d.h - 2}" rx="{rx}"/></clipPath>')
    return c


# ---------------------------------------------------------- section rule ---
SECTIONS = {
    "s-whoami": ("01", "WHOAMI", [("Curious by default. ", "serif"), ("Relentless by design.", "serif-i")], "live system info"),
    "s-flagship": ("02", "FLAGSHIP", [("Search finds documents. ", "serif"), ("Premise finds consequences.", "serif-i")], ""),
    "s-work": ("03", "SELECTED WORK", [("Less talk. ", "serif"), ("More shipped.", "serif-i")], "systems built from first principles"),
    "s-stack": ("04", "TOOLKIT", [("Depth over ", "serif"), ("buzzwords.", "serif-i")], "the tools change, the fundamentals stay"),
    "s-experience": ("05", "EXPERIENCE", [("Work that ", "serif"), ("matters.", "serif-i")], "research · industry · community"),
    "s-cp": ("06", "UNDER THE CLOCK", [("Pressure ", "serif"), ("tested.", "serif-i")], "live from the judges' APIs"),
    "s-activity": ("07", "ACTIVITY", [("Always ", "serif"), ("shipping.", "serif-i")], "refreshed daily by GitHub Actions"),
}


def section(key):
    idx, label, parts, note = SECTIONS[key]

    def build(t):
        plain = "".join(p for p, _ in parts)
        d = Doc(W, 100, t, f"{idx} / {label} — {plain}")
        d.add(d.runs(2, 26, [(idx, "mono-b", t["ember"]), ("  /  " + label, "mono", t["muted"])], size=12.5, spacing=2))
        d.add(d.runs(0, 76, [(p, f, t["text"] if f == "serif" else t["ember"]) for p, f in parts], size=42, spacing=-0.4))
        if note:
            d.add(d.text(998, 76, note, "mono", 12, t["muted"], "end", 0.6))
        d.style("@keyframes draw{from{transform:scaleX(0)}to{transform:scaleX(1)}}"
                ".draw{transform-box:fill-box;transform-origin:left;animation:draw 1.2s cubic-bezier(.2,.7,.2,1) both}")
        d.add(f'<rect x="0" y="94" width="1000" height="1" fill="{t["line2"]}"/>',
              f'<rect class="draw" x="0" y="93" width="132" height="3" rx="1.5" fill="{t["ember"]}"/>')
        return d
    return build


# ------------------------------------------------------------------ pills ---
LINK_PILLS = {
    "btn-portfolio": ("Portfolio", ("glyph", "globe"), 132),
    "btn-linkedin": ("LinkedIn", ("glyph", "in"), 132),
    "btn-email": ("Email", ("icon", "si-gmail.svg"), 132),
    "btn-devto": ("dev.to", ("icon", "si-devdotto.svg"), 132),
    "btn-leetcode": ("LeetCode", ("icon", "si-leetcode.svg"), 132),
    "btn-codeforces": ("Codeforces", ("icon", "si-codeforces.svg"), 132),
    "btn-premise-live": ("Live app", ("glyph", "globe"), 156),
    "btn-premise-demo": ("3-min demo", ("icon", "si-youtube.svg"), 156),
    "btn-premise-walk": ("Walkthrough", ("icon", "si-youtube.svg"), 156),
    "btn-premise-blog": ("Blog post", ("icon", "si-devdotto.svg"), 156),
    "btn-premise-code": ("Source", ("icon", "si-github.svg"), 156),
}


def pill(key):
    label, (kind, ref), w = LINK_PILLS[key]

    def build(t):
        d = Doc(w, 42, t, label)
        d.add(f'<rect x=".5" y=".5" width="{w - 1}" height="41" rx="20.5" fill="{t["surface"]}" stroke="{t["line2"]}"/>')
        lw = measure(label.upper(), "mono-b", 11.5, 1.2)
        x0 = (w - (16 + 9 + lw)) / 2
        d.add(glyph(d, ref, x0, 13, 16, t["ember"]) if kind == "glyph" else icon(d, ref, x0, 13, 16, t["ember"]))
        d.add(d.text(x0 + 25, 25.5, label.upper(), "mono-b", 11.5, t["text"], spacing=1.2))
        return d
    return build


# --------------------------------------------------------------- premise ---
def premise(t):
    d = Doc(W, 480, t, "Premise — the company brain that knows what your next pull request will break",
            "Flagship project card. A pull request changes paylane.retry_window from 24h to 72h; the change "
            "propagates red through config, an assumption and four guarantees to ADR-012 and its owners, the merge "
            "is blocked, then a verified fix heals the graph. 275 nodes and 488 edges from 88 sources, 380 tests, "
            "red team 35 of 35 safe. Built for WeMakeDevs x FalkorDB Graph Hacks.")
    card(d, grain=True)
    clip = clip_card(d)
    d.add(f'<g clip-path="url(#{clip})">')
    glow(d, 760, 250, 340, t["red"], 0.10 * t["glow"] / 0.55)
    glow(d, 120, 470, 300, t["ember"], 0.18 * t["glow"] / 0.55)
    d.add("</g>")

    # left column
    d.add(d.text(44, 58, "WEMAKEDEVS × FALKORDB GRAPH HACKS", "mono", 12, t["ember"], spacing=1.6))
    d.add(d.text(40, 148, "Premise", "serif", 96, t["text"], spacing=-1.5))
    d.add(d.text(44, 186, "The company brain that knows what", "sans-m", 20, t["text"]),
          d.text(44, 212, "your next pull request will break.", "sans-m", 20, t["text"]))
    body = ["Workers turn ADRs, config, tickets and runbooks into one",
            "FalkorDB graph. On every PR an agent walks it, blocks the",
            "merge, routes reviewers, and opens a fix only after the",
            "graph proves it complete."]
    for i, line in enumerate(body):
        d.add(d.text(44, 250 + i * 22, line, "sans", 15, t["muted"]))
    stats = [("275", "NODES"), ("488", "EDGES"), ("380", "TESTS"), ("35/35", "RED TEAM SAFE"), ("88", "SOURCES")]
    x = 44
    for num, lab in stats:
        d.add(d.text(x, 382, num, "serif", 36, t["text"]), d.text(x + 1, 404, lab, "mono", 10, t["muted"], spacing=1))
        x += max(measure(num, "serif", 36), measure(lab, "mono", 10, 1)) + 26
    chips(d, 44, 424, ["Python", "FalkorDB", "MCP", "Agents"], size=11.5, h=28)

    # graph panel
    px, py, pw, ph = 520, 30, 450, 420
    d.add(f'<rect x="{px}" y="{py}" width="{pw}" height="{ph}" rx="16" fill="{t["surface"]}" stroke="{t["line"]}"/>')
    d.add(d.text(px + 22, py + 34, "PULL REQUEST", "mono", 10.5, t["muted"], spacing=1.4))
    d.add(d.runs(px + 22, py + 58, [("paylane.retry_window  ", "mono", t["text"]), ("24h → ", "mono", t["muted"]),
                                     ("72h", "mono-b", t["ember"])], size=14))
    d.add(f'<line x1="{px}" y1="{py + 76}" x2="{px + pw}" y2="{py + 76}" stroke="{t["line"]}"/>')

    C = 12.0
    P = lambda s: max(0.0, min(100.0, s / C * 100))
    nodes = {  # key: (x, y, label, break_t, heal_t)
        "pr": (583, 146, "PR", 1.0, 7.0),
        "cfg": (673, 146, "config", 1.8, 7.4),
        "asm": (763, 146, "assumption", 2.5, 7.8),
        "g1": (610, 250, "G1", 3.2, 8.2), "g2": (712, 250, "G2", 3.35, 8.3),
        "g3": (814, 250, "G3", 3.5, 8.4), "g4": (916, 250, "G4", 3.65, 8.5),
        "adr": (665, 340, "ADR-012", 4.1, 8.9), "own": (865, 340, "owners", 4.3, 9.1),
    }
    edges = [("pr", "cfg"), ("cfg", "asm"), ("asm", "g1"), ("asm", "g2"), ("asm", "g3"), ("asm", "g4"),
             ("g1", "adr"), ("g2", "adr"), ("g3", "own"), ("g4", "own"), ("adr", "own")]
    neutral = f'fill:{t["surface2"]};stroke:{t["line2"]}'
    for a, b in edges:
        x1, y1 = nodes[a][:2]
        x2, y2, _, bt, ht = nodes[b]
        L = math.hypot(x2 - x1, y2 - y1)
        d.add(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{t["line2"]}" stroke-width="1.5"/>')
        for color, start, end, nm in ((t["red"], bt - 0.5, ht, "r"), (t["teal"], ht - 0.45, 11.2, "g")):
            k = d.uid("e" + nm)
            d.style(keyframes(k, [(0, f"stroke-dashoffset:{L:.1f};opacity:1"), (P(start), f"stroke-dashoffset:{L:.1f};opacity:1"),
                                  (P(start + 0.45), "stroke-dashoffset:0;opacity:1"), (P(end), "stroke-dashoffset:0;opacity:1"),
                                  (P(end + 0.4), "stroke-dashoffset:0;opacity:0"), (100, "stroke-dashoffset:0;opacity:0")])
                    + f".{k}{{animation:{k} {C}s linear infinite}}")
            d.add(f'<line class="{k}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="2" '
                  f'stroke-dasharray="{L:.1f}" stroke-dashoffset="0" opacity="0"/>')
    for key, (x, y, label, bt, ht) in nodes.items():
        hot = t["ember"] if key == "pr" else t["red"]
        k, hk = d.uid("n"), d.uid("h")
        d.style(keyframes(k, [(0, neutral), (P(bt) - 0.3, neutral), (P(bt), f"fill:{rgba(hot, .25)};stroke:{hot}"),
                              (P(ht) - 0.3, f"fill:{rgba(hot, .25)};stroke:{hot}"),
                              (P(ht), f"fill:{rgba(t['teal'], .22)};stroke:{t['teal']}"),
                              (P(11.2), f"fill:{rgba(t['teal'], .22)};stroke:{t['teal']}"), (P(11.7), neutral), (100, neutral)])
                + f".{k}{{animation:{k} {C}s linear infinite}}")
        d.style(keyframes(hk, [(0, "opacity:0;transform:scale(.6)"), (P(bt) - 0.2, "opacity:0;transform:scale(.6)"),
                               (P(bt), "opacity:.9;transform:scale(1)"), (P(bt + 1.1), "opacity:0;transform:scale(1.9)"),
                               (100, "opacity:0;transform:scale(1.9)")])
                + f".{hk}{{transform-box:fill-box;transform-origin:center;animation:{hk} {C}s ease-out infinite}}")
        d.add(f'<circle class="{hk}" cx="{x}" cy="{y}" r="15" stroke="{hot}" stroke-width="1.5" opacity="0"/>',
              f'<circle class="{k}" cx="{x}" cy="{y}" r="11" stroke-width="2" style="{neutral}"/>')
        d.add(d.text(x, y + 30, label, "mono", 11, t["soft"], "middle"))
    d.add(d.text(763, 296, "4 GUARANTEES", "mono", 9.5, t["muted"], "middle", 1.4))

    # status line
    sy = py + ph - 38
    phases = [
        ("idle", "WATCHING main", t["muted"], [(0, 1), (P(1.0), 1), (P(1.2), 0), (P(11.5), 0), (P(11.8), 1), (100, 1)]),
        ("sim", "SIMULATING BLAST RADIUS…", t["amber"], [(0, 0), (P(1.0), 0), (P(1.2), 1), (P(4.4), 1), (P(4.6), 0), (100, 0)]),
        ("blk", "BLOCKED · 4 GUARANTEES BROKEN", t["red"], [(0, 0), (P(4.4), 0), (P(4.6), 1), (P(6.8), 1), (P(7.0), 0), (100, 0)]),
        ("fix", "FIX PR · RE-SIMULATING…", t["amber"], [(0, 0), (P(6.8), 0), (P(7.0), 1), (P(8.9), 1), (P(9.1), 0), (100, 0)]),
        ("ok", "CLEAR · FIX VERIFIED BY THE GRAPH", t["teal"], [(0, 0), (P(8.9), 0), (P(9.1), 1), (P(11.5), 1), (P(11.8), 0), (100, 0)]),
    ]
    for name, label, color, stops in phases:
        k = d.uid("ph")
        d.style(keyframes(k, [(p, f"opacity:{o}") for p, o in stops]) + f".{k}{{animation:{k} {C}s linear infinite}}")
        w = measure(label, "mono-b", 11.5, 1.2) + 46
        op = stops[0][1]
        d.add(f'<g class="{k}" opacity="{op}"><rect x="{px + 22}" y="{sy - 18}" width="{w:.0f}" height="30" rx="15" '
              f'fill="{rgba(color, .12)}" stroke="{color}" stroke-opacity=".6"/>'
              f'<circle cx="{px + 40}" cy="{sy - 3}" r="4" fill="{color}"/>'
              + d.text(px + 54, sy + 1, label, "mono-b", 11.5, color, spacing=1.2) + "</g>")
    k = d.uid("own")
    d.style(keyframes(k, [(0, "opacity:0"), (P(4.6), "opacity:0"), (P(4.9), "opacity:1"), (P(6.8), "opacity:1"),
                          (P(7.0), "opacity:0"), (100, "opacity:0")]) + f".{k}{{animation:{k} {C}s linear infinite}}")
    d.add(f'<g class="{k}" opacity="0">' + d.text(px + pw - 22, py + 34, "owners left → reviewers routed", "mono", 10.5, t["red"], "end")
          + "</g>")
    return d


# -------------------------------------------------------------- projects ---
PROJECTS = {
    "p-forgeflow": dict(cat="AGENT INFRASTRUCTURE", title="ForgeFlow", art="pipeline",
                        lines=["Finds open-source issues worth fixing, plans and",
                               "codes in sandboxed Git workspaces, verifies, and",
                               "opens a PR only after a human approves it."],
                        metric="11 explained ranking factors · restart-safe runs",
                        tags=["Go", "React", "TypeScript", "SQLite"]),
    "p-jevrouter": dict(cat="LLM ROUTING API", title="JevRouter", art="router",
                        lines=["Recommends the right model tier for each coding",
                               "task under a hard cost cap, then learns from",
                               "accepted and rejected feedback."],
                        metric="T0–T3 tiers · idempotent routes · spend guards",
                        tags=["Go", "SQLite", "AI Gateway"]),
    "p-vector": dict(cat="DISTRIBUTED SYSTEMS", title="Vector Search", art="shards",
                     lines=["From-scratch HNSW in C++ behind four Go-",
                            "coordinated shards. Writes hit a checksummed WAL",
                            "before memory; recovery survives a hard kill."],
                     metric="95% recall@10 · <50 ms p99 at 100 QPS",
                     tags=["C++", "Go", "gRPC", "AVX2"]),
    "p-goegg": dict(cat="OPEN-SOURCE LIBRARY", title="GoEgg", art="egraph",
                    lines=["Equality saturation for Go: parallel matching,",
                           "bulk-synchronous rebuilds and lock-free",
                           "extraction. Zero dependencies."],
                    metric="3.79× faster rebuilds · v0.1.4 on pkg.go.dev",
                    tags=["Go", "E-graphs", "Parallelism"]),
    "p-guardian": dict(cat="AI DEBUGGING AGENT", title="Code Guardian", art="branches",
                       lines=["Ingests a repository, localizes defects with RAG",
                              "and static analysis, and proposes fixes on",
                              "reviewable Git branches. Humans stay in the loop."],
                       metric="Kafka job pipeline · one branch per fix",
                       tags=["Java", "Spring Boot", "Kafka", "Docker"]),
    "p-gateway": dict(cat="SEARCH INFRASTRUCTURE", title="Search Gateway", art="bucket",
                      lines=["Text-to-vector search through Go gRPC APIs,",
                             "idempotent Kafka ingestion, and separate",
                             "embedding services for search and ingest."],
                      metric="token-bucket rate limits per client",
                      tags=["Go", "gRPC", "Kafka", "Python"]),
    "p-arnyx": dict(cat="AI TOOLING OBSERVATORY", title="Arnyx", art="radar",
                    lines=["Four concurrent scouts discover skills, MCP",
                           "servers and plugins; guided walkthroughs help",
                           "you assemble a stack that fits your work."],
                    metric="scheduled discovery · reviewed skill installs",
                    tags=["Java 21", "Spring Boot", "React", "TS"]),
    "p-tokie": dict(cat="DESKTOP UTILITY", title="Tokie", art="widget",
                    lines=["An always-on-top Windows widget that counts your",
                           "Claude Code and Codex tokens from local logs.",
                           "Nothing is uploaded anywhere."],
                    metric="stdlib-only Python · one-file .exe",
                    tags=["Python", "Windows", "Local-first"]),
}


def art(d: Doc, kind: str, bx, by, bw=128, bh=100):
    t = d.t
    cx, cy = bx + bw / 2, by + bh / 2
    out = []
    if kind == "pipeline":
        xs = [bx + 8 + i * 28 for i in range(5)]
        y = cy + 4
        out.append(f'<path d="M{xs[0]},{y} H{xs[-1]}" stroke="{t["line2"]}" stroke-width="1.5"/>')
        for i, x in enumerate(xs[:-1]):
            out.append(f'<circle cx="{x}" cy="{y}" r="6" fill="{t["surface2"]}" stroke="{t["soft"]}" stroke-width="1.3"/>')
        lx = xs[-1]
        out.append(f'<rect x="{lx - 9}" y="{y - 9}" width="18" height="18" rx="5" fill="{t["surface2"]}" stroke="{t["teal"]}" stroke-width="1.4"/>'
                   f'<path d="M{lx - 4},{y} l3,3 l6,-6" stroke="{t["teal"]}" stroke-width="1.6" fill="none"/>')
        out.append(f'<circle r="4" fill="{t["ember"]}"><animateMotion dur="3.2s" repeatCount="indefinite" '
                   f'keyPoints="0;0.25;0.25;0.5;0.5;0.75;0.75;1" keyTimes="0;.12;.25;.37;.5;.62;.75;1" calcMode="linear" '
                   f'path="M{xs[0]},{y} H{xs[-1] - 10}"/></circle>')
        labels = ["find", "plan", "code", "test", "you"]
        for x, lab in zip(xs, labels):
            out.append(d.text(x, y + 26, lab, "mono", 9.5, t["teal"] if lab == "you" else t["muted"], "middle"))
    elif kind == "router":
        ix, iy = bx + 12, cy
        tiers = [(bx + 104, by + 14 + i * 24, f"T{i}") for i in range(4)]
        out.append(f'<circle cx="{ix}" cy="{iy}" r="7" fill="{rgba(t["ember"], .2)}" stroke="{t["ember"]}" stroke-width="1.5"/>')
        for i, (x, y, lab) in enumerate(tiers):
            path = f"M{ix + 7},{iy} C{ix + 50},{iy} {x - 50},{y} {x - 8},{y}"
            out.append(f'<path d="{path}" stroke="{t["line2"]}" stroke-width="1.3"/>')
            k = d.uid("tier")
            s = i * 25
            d.style(keyframes(k, [(0, f"stroke:{t['line2']}"), (s + 6, f"stroke:{t['line2']}"), (s + 9, f"stroke:{t['ember']}"),
                                  (s + 22, f"stroke:{t['ember']}"), (s + 25, f"stroke:{t['line2']}"), (100, f"stroke:{t['line2']}")])
                    + f".{k}{{animation:{k} 6s linear infinite}}")
            out.append(f'<circle class="{k}" cx="{x}" cy="{y}" r="7" fill="{t["surface2"]}" stroke="{t["line2"]}" stroke-width="1.5"/>')
            out.append(d.text(x + 13, y + 4, lab, "mono-b", 10.5, t["soft"]))
            out.append(f'<circle r="3" fill="{t["ember"]}" opacity="0"><animateMotion dur="6s" begin="{i * 1.5}s" '
                       f'repeatCount="indefinite" keyPoints="0;1;1" keyTimes="0;.09;1" calcMode="linear" path="{path}"/>'
                       f'<animate attributeName="opacity" dur="6s" begin="{i * 1.5}s" repeatCount="indefinite" '
                       f'values="1;1;0;0" keyTimes="0;.09;.1;1"/></circle>')
    elif kind == "shards":
        out.append(f'<rect x="{cx - 26}" y="{by + 4}" width="52" height="20" rx="6" fill="{rgba(t["ember"], .15)}" stroke="{t["ember"]}" stroke-width="1.3"/>')
        out.append(d.text(cx, by + 18, "coord", "mono", 9.5, t["ember"], "middle"))
        for i in range(4):
            sx = bx + 4 + i * 32
            path = f"M{cx},{by + 24} L{sx + 13},{by + 66}"
            out.append(f'<path d="{path}" stroke="{t["line2"]}" stroke-width="1.2"/>')
            out.append(f'<rect x="{sx}" y="{by + 66}" width="26" height="30" rx="5" fill="{t["surface2"]}" stroke="{t["soft"]}" stroke-width="1.2"/>')
            for j in range(3):
                k = d.uid("wal")
                d.style(keyframes(k, [(0, "opacity:.25"), (20 + j * 15, "opacity:.25"), (25 + j * 15, "opacity:1"),
                                      (85, "opacity:1"), (95, "opacity:.25"), (100, "opacity:.25")])
                        + f".{k}{{animation:{k} 3.6s linear infinite;animation-delay:{i * .15:.2f}s}}")
                out.append(f'<rect class="{k}" x="{sx + 5}" y="{by + 73 + j * 7}" width="16" height="3" rx="1.5" fill="{t["amber"]}"/>')
            out.append(f'<circle r="2.6" fill="{t["ember"]}"><animateMotion dur="1.8s" repeatCount="indefinite" '
                       f'keyPoints="0;1;0" keyTimes="0;.5;1" calcMode="linear" path="{path}"/></circle>')
    elif kind == "egraph":
        for side, lab, color in ((-1, "a×2", t["soft"]), (1, "a+a", t["soft"])):
            k = d.uid("eg")
            d.style(keyframes(k, [(0, "transform:translateX(0)"), (30, "transform:translateX(0)"),
                                  (55, f"transform:translateX({-side * 22}px)"), (80, f"transform:translateX({-side * 22}px)"),
                                  (100, "transform:translateX(0)")]) + f".{k}{{animation:{k} 5s ease-in-out infinite}}")
            ex = cx + side * 34
            out.append(f'<g class="{k}"><ellipse cx="{ex}" cy="{cy - 8}" rx="30" ry="22" fill="{rgba(t["ember"], .06)}" '
                       f'stroke="{t["ember"]}" stroke-width="1.3" stroke-dasharray="3 4"/>'
                       + d.text(ex, cy - 3, lab, "mono-b", 13, color, "middle") + "</g>")
        k = d.uid("eq")
        d.style(keyframes(k, [(0, "opacity:0"), (52, "opacity:0"), (60, "opacity:1"), (80, "opacity:1"), (88, "opacity:0"), (100, "opacity:0")])
                + f".{k}{{animation:{k} 5s ease-in-out infinite}}")
        out.append(f'<g class="{k}" opacity="0">' + d.text(cx, cy + 36, "≡  one e-class", "mono", 10, t["amber"], "middle") + "</g>")
    elif kind == "branches":
        y0 = cy + 22
        out.append(f'<path d="M{bx + 4},{y0} H{bx + bw - 4}" stroke="{t["soft"]}" stroke-width="1.5"/>')
        branch = f"M{bx + 30},{y0} C{bx + 44},{y0} {bx + 40},{by + 26} {bx + 58},{by + 26} H{bx + 82}"
        merge = f"M{bx + 82},{by + 26} C{bx + 100},{by + 26} {bx + 96},{y0} {bx + 110},{y0}"
        k1, k2 = d.uid("br"), d.uid("mg")
        d.style(keyframes(k1, [(0, "stroke-dashoffset:110"), (35, "stroke-dashoffset:0"), (100, "stroke-dashoffset:0")])
                + f".{k1}{{animation:{k1} 4.5s ease-out infinite}}"
                + keyframes(k2, [(0, "stroke-dashoffset:60"), (55, "stroke-dashoffset:60"), (80, "stroke-dashoffset:0"), (100, "stroke-dashoffset:0")])
                + f".{k2}{{animation:{k2} 4.5s ease-out infinite}}")
        out.append(f'<path class="{k1}" d="{branch}" stroke="{t["ember"]}" stroke-width="1.6" stroke-dasharray="110"/>')
        out.append(f'<path class="{k2}" d="{merge}" stroke="{t["teal"]}" stroke-width="1.6" stroke-dasharray="60"/>')
        for x in (bx + 12, bx + 30, bx + 110):
            out.append(f'<circle cx="{x}" cy="{y0}" r="5" fill="{t["surface2"]}" stroke="{t["soft"]}" stroke-width="1.4"/>')
        for x in (bx + 62, bx + 82):
            out.append(f'<circle cx="{x}" cy="{by + 26}" r="5" fill="{t["surface2"]}" stroke="{t["ember"]}" stroke-width="1.4"/>')
        out.append(d.text(bx + 70, by + 12, "fix/null-guard", "mono", 9.5, t["ember"], "middle"))
        out.append(d.text(bx + 4, y0 + 20, "main", "mono", 9.5, t["muted"]))
    elif kind == "bucket":
        out.append(f'<path d="M{cx - 30},{by + 30} V{by + 84} Q{cx - 30},{by + 94} {cx - 20},{by + 94} H{cx + 20} '
                   f'Q{cx + 30},{by + 94} {cx + 30},{by + 84} V{by + 30}" stroke="{t["soft"]}" stroke-width="1.6"/>')
        for i in range(8):
            r_, c_ = divmod(i, 4)
            out.append(f'<circle cx="{cx - 18 + c_ * 12}" cy="{by + 84 - r_ * 12}" r="4.5" fill="{t["amber"]}" opacity="{.9 - r_ * .3:.1f}"/>')
        k = d.uid("drop")
        d.style(keyframes(k, [(0, "transform:translateY(0);opacity:0"), (10, "opacity:1"), (60, "transform:translateY(40px);opacity:1"),
                              (70, "transform:translateY(46px);opacity:0"), (100, "transform:translateY(46px);opacity:0")])
                + f".{k}{{animation:{k} 1.6s ease-in infinite}}")
        out.append(f'<circle class="{k}" cx="{cx}" cy="{by + 8}" r="4.5" fill="{t["ember"]}"/>')
        k2 = d.uid("leak")
        d.style(keyframes(k2, [(0, "transform:translateX(0);opacity:0"), (20, "opacity:1"), (100, "transform:translateX(34px);opacity:0")])
                + f".{k2}{{animation:{k2} 2.4s linear infinite}}")
        out.append(f'<circle class="{k2}" cx="{cx + 34}" cy="{by + 84}" r="3.5" fill="{t["teal"]}"/>')
        out.append(d.text(cx + 38, by + 72, "req", "mono", 9.5, t["muted"]))
    elif kind == "radar":
        rcx, rcy = cx, cy + 2
        for r in (16, 32, 48):
            out.append(f'<circle cx="{rcx}" cy="{rcy}" r="{r}" stroke="{t["line2"]}" stroke-width="1"/>')
        g = d.uid("sw")
        d.define(f'<linearGradient id="{g}" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{t["ember"]}" stop-opacity="0"/>'
                 f'<stop offset="1" stop-color="{t["ember"]}" stop-opacity=".55"/></linearGradient>')
        d.style("@keyframes sweep{to{transform:rotate(360deg)}}"
                f".sweep{{transform-origin:{rcx}px {rcy}px;animation:sweep 4s linear infinite}}")
        out.append(f'<g class="sweep"><path d="M{rcx},{rcy} L{rcx + 48},{rcy} A48,48 0 0 0 {rcx + 48 * math.cos(math.radians(-50)):.1f},'
                   f'{rcy + 48 * math.sin(math.radians(-50)):.1f} Z" fill="url(#{g})"/>'
                   f'<line x1="{rcx}" y1="{rcy}" x2="{rcx + 48}" y2="{rcy}" stroke="{t["ember"]}" stroke-width="1.4"/></g>')
        for ang, rad in ((-20, 38), (60, 24), (150, 42), (230, 30)):
            bx_ = rcx + rad * math.cos(math.radians(ang))
            by_ = rcy + rad * math.sin(math.radians(ang))
            delay = ((ang % 360) / 360) * 4
            k = d.uid("blip")
            d.style(keyframes(k, [(0, "opacity:1"), (35, "opacity:.15"), (100, "opacity:.15")])
                    + f".{k}{{animation:{k} 4s linear infinite;animation-delay:{delay:.2f}s}}")
            out.append(f'<circle class="{k}" cx="{bx_:.1f}" cy="{by_:.1f}" r="3.2" fill="{t["amber"]}"/>')
        out.append(f'<circle cx="{rcx}" cy="{rcy}" r="3" fill="{t["ember"]}"/>')
    elif kind == "widget":
        wx, wy = bx + 14, by + 20
        out.append(f'<path d="M{wx + 14},{wy + 1} l6,-12 l7,11 M{wx + 73},{wy + 0} l7,-11 l6,12" fill="{t["surface2"]}" '
                   f'stroke="{t["soft"]}" stroke-width="1.4" stroke-linejoin="round"/>')
        out.append(f'<rect x="{wx}" y="{wy}" width="100" height="74" rx="14" fill="{t["surface2"]}" stroke="{t["soft"]}" stroke-width="1.4"/>')
        d.style("@keyframes wink{0%,92%,100%{transform:scaleY(1)}95%{transform:scaleY(.1)}}"
                ".wink{transform-box:fill-box;transform-origin:center;animation:wink 4s infinite}")
        out.append(f'<ellipse class="wink" cx="{wx + 40}" cy="{wy + 16}" rx="2.2" ry="2.8" fill="{t["text"]}"/>'
                   f'<ellipse class="wink" cx="{wx + 60}" cy="{wy + 16}" rx="2.2" ry="2.8" fill="{t["text"]}"/>')
        out.append(d.text(wx + 50, wy + 44, "1.28M", "mono-b", 17, t["ember"], "middle"))
        for i, hgt in enumerate((6, 10, 7, 13, 9, 15, 12)):
            k = d.uid("bar")
            d.style(keyframes(k, [(0, "transform:scaleY(.4)"), (50, "transform:scaleY(1)"), (100, "transform:scaleY(.4)")])
                    + f".{k}{{transform-box:fill-box;transform-origin:bottom;animation:{k} {2 + i * .3:.1f}s ease-in-out infinite}}")
            out.append(f'<rect class="{k}" x="{wx + 18 + i * 9.5:.1f}" y="{wy + 66 - hgt}" width="6" height="{hgt}" rx="2" fill="{t["amber"]}" opacity=".85"/>')
    d.add(*out)


def project(key):
    p = PROJECTS[key]

    def build(t):
        d = Doc(500, 300, t, f'{p["title"]} — {p["cat"].lower()}', " ".join(p["lines"]) + " " + p["metric"])
        card(d, rx=20)
        art(d, p["art"], 350, 26)
        d.add(d.text(28, 44, p["cat"], "mono", 11, t["ember"], spacing=1.5))
        d.add(d.text(26, 96, p["title"], "serif", 40, t["text"], spacing=-0.5))
        for i, line in enumerate(p["lines"]):
            d.add(d.text(28, 146 + i * 22, line, "sans", 14.5, t["soft"]))
        d.add(d.runs(28, 228, [("▸ ", "mono", t["ember"]), (p["metric"], "mono", t["amber"])], size=11.5))
        d.add(f'<line x1="28" y1="246" x2="472" y2="246" stroke="{t["line"]}"/>')
        chips(d, 28, 258, p["tags"], size=11, h=24, pad=9, gap=6)
        d.style("@keyframes nudge{0%,100%{transform:translateX(0)}50%{transform:translateX(4px)}}"
                ".nudge{animation:nudge 2.4s ease-in-out infinite}")
        d.add(f'<g class="nudge">{glyph(d, "arrow", 448, 262, 16, t["muted"])}</g>')
        return d
    return build


# ----------------------------------------------------------------- stack ---
STACK_ROWS = [
    [("Java", "java-original.svg"), ("Go", "go-original-wordmark.svg"), ("C++", "cplusplus-original.svg"),
     ("Python", "python-original.svg"), ("TypeScript", "typescript-original.svg"), ("React", "react-original.svg"),
     ("Node.js", "nodejs-original.svg"), ("Kotlin", "kotlin-original.svg"), ("Flutter", "flutter-original.svg")],
    [("Spring", "spring-original.svg"), ("PostgreSQL", "postgresql-original.svg"), ("Redis", "redis-original.svg"),
     ("Kafka", "apachekafka-original.svg"), ("gRPC", "grpc-original.svg"), ("Docker", "docker-original.svg"),
     ("Git", "git-original.svg"), ("Actions", "githubactions-original.svg"), ("SQLite", "sqlite-original.svg")],
]
CAPABILITIES = [
    ("APIS & MESSAGING", "REST · gRPC · Kafka", "MQTT · SSE · webhooks"),
    ("DATA & STORAGE", "PostgreSQL · Redis · SQLite", "FalkorDB · WAL · HNSW"),
    ("AI SYSTEMS", "RAG · MCP · embeddings", "agents · model routing"),
    ("RELIABILITY", "idempotency · rate limits", "crash recovery · TSan"),
]


def stack(t):
    names = [n for row in STACK_ROWS for n, _ in row]
    d = Doc(W, 330, t, "Toolkit", "Languages and tools: " + ", ".join(names) + ". " +
            " ".join(f"{a}: {b}, {c}." for a, b, c in CAPABILITIES))
    card(d)
    m, mg = d.uid("fade"), d.uid("fg")
    d.define(f'<linearGradient id="{mg}" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/>'
             f'<stop offset=".09" stop-color="#fff"/><stop offset=".91" stop-color="#fff"/>'
             f'<stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
             f'<mask id="{m}"><rect x="0" y="0" width="{W}" height="240" fill="url(#{mg})"/></mask>')
    pitch, tw, th = 140, 126, 88
    syms = {}
    for row in STACK_ROWS:
        for _, f in row:
            sid = d.uid("sym")
            nested = icon(d, f, 0, 0, 38)
            d.define(f'<symbol id="{sid}" viewBox="0 0 38 38">{nested}</symbol>')
            syms[f] = sid
    d.style("@keyframes mq{from{transform:translateX(0)}to{transform:translateX(-1260px)}}"
            "@keyframes mqr{from{transform:translateX(-1260px)}to{transform:translateX(0)}}"
            ".mq{animation:mq 46s linear infinite}.mqr{animation:mqr 46s linear infinite}")
    d.add(f'<g mask="url(#{m})">')
    for r, row in enumerate(STACK_ROWS):
        y = 26 + r * 102
        d.add(f'<g class="{"mq" if r == 0 else "mqr"}">')
        for rep in range(3):
            for i, (name, f) in enumerate(row):
                x = 20 + (rep * len(row) + i) * pitch
                d.add(f'<rect x="{x}" y="{y}" width="{tw}" height="{th}" rx="16" fill="{t["surface2"]}" stroke="{t["line"]}"/>',
                      f'<use href="#{syms[f]}" x="{x + tw / 2 - 19:g}" y="{y + 13}" width="38" height="38"/>',
                      d.text(x + tw / 2, y + 73, name, "mono", 11.5, t["soft"], "middle", 0.4))
        d.add("</g>")
    d.add("</g>")
    d.add(f'<line x1="32" y1="242" x2="968" y2="242" stroke="{t["line"]}"/>')
    for i, (head, a, b) in enumerate(CAPABILITIES):
        x = 36 + i * 238
        d.add(d.text(x, 270, head, "mono", 10.5, t["ember"], spacing=1.4),
              d.text(x, 294, a, "sans", 14, t["soft"]), d.text(x, 314, b, "sans", 14, t["muted"]))
    return d


# ------------------------------------------------------------ experience ---
EXPERIENCE = [
    ("2026", "MAY – JUL", "Research Intern", "S.N. Bose National Centre for Basic Sciences",
     ["GPU-accelerated discrete Voronoi diagrams in Python and Taichi.",
      "Density-aware cut-offs, benchmarked against the Jump Flood Algorithm."],
     ["Computational geometry", "GPU", "Taichi"]),
    ("2025", "JUL – DEC", "Backend Software Developer Intern", "LIMA · Defense Sector Organization",
     ["Java and Spring Boot backend serving 700+ personnel.",
      "Owned PostgreSQL schema, query tuning, and JWT multi-level access."],
     ["★ Certificate of Appreciation", "Spring Boot", "PostgreSQL"]),
    ("2024", "SEP → MAY '26", "Moderator", "Google Developer Student Clubs · NIT Silchar",
     ["Ran technical workshops for 30+ students on software and systems.",
      "Also event management executive, Electra Society (2024–25)."],
     ["Workshops", "Community"]),
    ("2023", "→ 2027", "B.Tech, Electrical Engineering", "National Institute of Technology, Silchar",
     ["CGPA 8.26 / 10. Authors problems, validators and checkers",
      "on Codeforces Polygon; drills advanced DS&A on CSES."],
     ["CGPA 8.26", "Polygon problem setter"]),
]


def experience(t):
    step = 138
    d = Doc(W, 40 + step * len(EXPERIENCE) + 4, t, "Experience",
            " ".join(f"{role}, {org}, {yr} {rng}: {' '.join(lines)}" for yr, rng, role, org, lines, _ in EXPERIENCE))
    card(d)
    rail_x, top = 214, 52
    bottom = top + step * (len(EXPERIENCE) - 1)
    d.add(f'<line x1="{rail_x}" y1="{top}" x2="{rail_x}" y2="{bottom}" stroke="{t["line2"]}" stroke-width="2"/>')
    d.style("@keyframes rail{from{stroke-dashoffset:%d}to{stroke-dashoffset:0}}"
            ".rail{animation:rail 2.4s cubic-bezier(.3,.6,.2,1) both}" % (bottom - top)
            + "@keyframes pop{from{opacity:0;transform:translateX(-10px)}to{opacity:1;transform:none}}"
            ".pop{animation:pop .7s cubic-bezier(.2,.7,.2,1) both}")
    d.add(f'<line class="rail" x1="{rail_x}" y1="{top}" x2="{rail_x}" y2="{bottom}" stroke="{t["ember"]}" stroke-width="2" '
          f'stroke-dasharray="{bottom - top}"/>')
    for i, (yr, rng, role, org, lines, tags) in enumerate(EXPERIENCE):
        y = top + i * step
        g = f'<g class="pop" style="animation-delay:{.25 + i * .45:.2f}s">'
        g += d.text(178, y + 14, yr, "serif", 40, t["text"], "end")
        g += d.text(178, y + 38, rng, "mono", 10.5, t["muted"], "end", 1)
        g += (f'<circle cx="{rail_x}" cy="{y}" r="9" fill="{t["bg"]}" stroke="{t["ember"]}" stroke-width="2"/>'
              f'<circle cx="{rail_x}" cy="{y}" r="3.5" fill="{t["ember"]}"/>')
        g += d.text(246, y + 9, role, "serif", 28, t["text"])
        g += d.text(246 + measure(role, "serif", 28) + 14, y + 8, org, "sans-m", 14.5, t["ember"])
        for j, line in enumerate(lines):
            g += d.text(247, y + 36 + j * 21, line, "sans", 14.5, t["soft"])
        d.add(g)
        cx = 247
        for tag in tags:
            hl = tag.startswith("★")
            cx += chip(d, cx, y + 70, tag, color=t["amber"] if hl else t["soft"], size=10.5, h=23, pad=9) + 6
        d.add("</g>")
    return d


# ---------------------------------------------------------------- footer ---
def footer(t):
    d = Doc(W, 210, t, "Build. Break. Understand. Repeat.",
            "Closing banner: Build. Break. Understand. Repeat. What happens when it crashes? Let's find out together. "
            "shaikrazeef2@gmail.com")
    card(d, grain=True)
    clip = clip_card(d)
    d.add(f'<g clip-path="url(#{clip})">')
    glow(d, 500, 260, 360, t["ember"], 0.32 * t["glow"] / 0.55)
    particles(d, n=22, x0=60, x1=940, rise=200, seed=11)
    d.add("</g>")
    d.add(d.runs(500, 98, [("Build. Break. Understand. ", "serif", t["text"]), ("Repeat.", "serif-i", t["ember"])],
                 size=50, anchor="middle", spacing=-0.5))
    d.add(d.text(500, 136, "WHAT HAPPENS WHEN IT CRASHES? LET'S FIND OUT TOGETHER.", "mono", 12, t["muted"], "middle", 1.6))
    g = d.uid("streak")
    d.define(f'<linearGradient id="{g}" x1="0" x2="1"><stop offset="0" stop-color="{t["ember"]}" stop-opacity="0"/>'
             f'<stop offset=".5" stop-color="{t["amber"]}"/><stop offset="1" stop-color="{t["ember"]}" stop-opacity="0"/></linearGradient>')
    d.style("@keyframes streak{from{transform:translateX(-240px)}to{transform:translateX(1000px)}}"
            ".streak{animation:streak 5s ease-in-out infinite}")
    d.add(f'<line x1="300" y1="160" x2="700" y2="160" stroke="{t["line2"]}"/>',
          f'<g clip-path="url(#{clip})"><rect class="streak" x="0" y="159" width="240" height="2" fill="url(#{g})"/></g>')
    d.add(d.text(500, 186, "shaikrazeef2@gmail.com", "mono-b", 12.5, t["ember"], "middle", 0.8))
    return d


BUILDERS = {"hero": hero, "premise": premise, "stack": stack, "experience": experience, "footer": footer}
BUILDERS.update({k: section(k) for k in SECTIONS})
BUILDERS.update({k: pill(k) for k in LINK_PILLS})
BUILDERS.update({k: project(k) for k in PROJECTS})


def main(only: list[str] | None = None):
    for name, fn in BUILDERS.items():
        if only and not any(name.startswith(o) for o in only):
            continue
        for t in THEMES:
            path = fn(t).save(name)
            print(f"{path.relative_to(path.parents[3])}  {path.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    import sys
    main(sys.argv[1:] or None)
