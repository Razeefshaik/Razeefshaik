"""Tiny SVG toolkit for the profile artwork.

Every asset is a self-contained SVG: fonts are subset to the glyphs the
image uses and embedded as base64 WOFF, so GitHub renders the exact same
typography for every visitor without any external request.
"""
from __future__ import annotations

import base64
import html
import io
from functools import lru_cache
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
FONTS = TOOLS / "fonts"
OUT = ROOT / "assets" / "v3"

# ---------------------------------------------------------------- themes ---
DARK = dict(
    name="dark",
    bg="#0B0A0D", surface="#121015", surface2="#1A171E", line="#2A2530", line2="#3B3441",
    text="#F1EBE1", soft="#CBC2B6", muted="#988E86", dim="#5F5760",
    ember="#FF6A1F", amber="#FFB547", red="#FF4D4D", teal="#3DDBB5", blue="#6EA8FF",
    glow=0.55, grid=0.5,
)
LIGHT = dict(
    name="light",
    bg="#F7F3ED", surface="#FFFCF7", surface2="#F0E9DF", line="#E4DACB", line2="#D3C7B5",
    text="#17130F", soft="#3E362E", muted="#6F655B", dim="#ABA092",
    ember="#E2550A", amber="#B8700A", red="#CF3434", teal="#0B9A7C", blue="#2F6BD8",
    glow=0.28, grid=0.9,
)
THEMES = (DARK, LIGHT)

# ----------------------------------------------------------------- fonts ---
# face key -> (file, css family, weight, style, variable-axis location)
FACES = {
    "serif": ("InstrumentSerif-Regular.ttf", "RZSerif", 400, "normal", None),
    "serif-i": ("InstrumentSerif-Italic.ttf", "RZSerif", 400, "italic", None),
    "mono": ("JetBrainsMono.ttf", "RZMono", 400, "normal", {"wght": 400}),
    "mono-b": ("JetBrainsMono.ttf", "RZMono", 700, "normal", {"wght": 700}),
    "sans": ("Archivo.ttf", "RZSans", 400, "normal", {"wght": 400, "wdth": 100}),
    "sans-m": ("Archivo.ttf", "RZSans", 600, "normal", {"wght": 600, "wdth": 100}),
    "sans-b": ("Archivo.ttf", "RZSans", 800, "normal", {"wght": 800, "wdth": 100}),
}
FALLBACK = {
    "RZSerif": "Georgia,'Times New Roman',serif",
    "RZMono": "ui-monospace,SFMono-Regular,Consolas,monospace",
    "RZSans": "'Segoe UI',Helvetica,Arial,sans-serif",
}


@lru_cache(maxsize=None)
def _static_font_bytes(face: str) -> bytes:
    file, _, _, _, axes = FACES[face]
    font = TTFont(FONTS / file, recalcTimestamp=False)
    if axes:
        font = instancer.instantiateVariableFont(font, axes)
    buf = io.BytesIO()
    font.save(buf)
    return buf.getvalue()


@lru_cache(maxsize=None)
def _metrics(face: str):
    font = TTFont(io.BytesIO(_static_font_bytes(face)))
    return font.getBestCmap(), font["hmtx"].metrics, font["head"].unitsPerEm


def measure(s: str, face: str, size: float, spacing: float = 0) -> float:
    cmap, hmtx, upm = _metrics(face)
    total = 0
    for ch in s:
        glyph = cmap.get(ord(ch))
        total += hmtx[glyph][0] if glyph else upm * 0.5
    return total * size / upm + spacing * max(len(s) - 1, 0)


def _subset_woff(face: str, chars: set[str]) -> str:
    font = TTFont(io.BytesIO(_static_font_bytes(face)), recalcTimestamp=False)
    opts = subset.Options()
    opts.flavor = "woff"
    opts.layout_features = ["kern"]
    opts.hinting = False
    opts.desubroutinize = True
    opts.name_IDs = [0, 1, 2]
    sub = subset.Subsetter(opts)
    sub.populate(text="".join(sorted(chars)) + " ")
    sub.subset(font)
    buf = io.BytesIO()
    font.flavor = "woff"
    font.save(buf)
    return base64.b64encode(buf.getvalue()).decode()


# ------------------------------------------------------------------- doc ---
def esc(s) -> str:
    return html.escape(str(s), quote=False)


def attr(s) -> str:
    return html.escape(str(s), quote=True)


class Doc:
    def __init__(self, w: int, h: int, theme: dict, title: str, desc: str = ""):
        self.w, self.h, self.t = w, h, theme
        self.title, self.desc = title, desc
        self.defs: list[str] = []
        self.css: list[str] = []
        self.body: list[str] = []
        self.chars: dict[str, set[str]] = {}
        self._ids = 0

    # ids keep gradients/filters unique inside one file
    def uid(self, prefix: str = "i") -> str:
        self._ids += 1
        return f"{prefix}{self._ids}"

    def add(self, *parts: str) -> "Doc":
        self.body.extend(parts)
        return self

    def style(self, css: str) -> "Doc":
        self.css.append(css)
        return self

    def define(self, d: str) -> "Doc":
        self.defs.append(d)
        return self

    def use_chars(self, face: str, s: str) -> None:
        self.chars.setdefault(face, set()).update(s)

    # text ---------------------------------------------------------------
    def text(self, x, y, s, face="sans", size=16, fill=None, anchor=None,
             spacing=None, cls="", extra="", opacity=None) -> str:
        """Return a <text> element (not added) so callers can wrap it."""
        self.use_chars(face, s)
        a = [f'x="{x:g}"' if isinstance(x, (int, float)) else f'x="{x}"', f'y="{y:g}"',
             f'class="f-{face}{(" " + cls) if cls else ""}"', f'font-size="{size:g}"']
        if fill:
            a.append(f'fill="{fill}"')
        if anchor:
            a.append(f'text-anchor="{anchor}"')
        if spacing:
            a.append(f'letter-spacing="{spacing:g}"')
        if opacity is not None:
            a.append(f'opacity="{opacity:g}"')
        if extra:
            a.append(extra)
        return f"<text {' '.join(a)}>{esc(s)}</text>"

    def runs(self, x, y, parts, size=16, anchor=None, spacing=None, cls="", extra="") -> str:
        """Mixed-style line: parts = [(text, face, fill), ...]."""
        spans = []
        for s, face, fill in parts:
            self.use_chars(face, s)
            spans.append(f'<tspan class="f-{face}" fill="{fill}">{esc(s)}</tspan>')
        a = [f'x="{x:g}"', f'y="{y:g}"', f'font-size="{size:g}"']
        if cls:
            a.append(f'class="{cls}"')
        if anchor:
            a.append(f'text-anchor="{anchor}"')
        if spacing:
            a.append(f'letter-spacing="{spacing:g}"')
        if extra:
            a.append(extra)
        return f"<text {' '.join(a)} xml:space=\"preserve\">{''.join(spans)}</text>"

    # render ---------------------------------------------------------------
    def _font_css(self) -> str:
        out = []
        for face, chars in sorted(self.chars.items()):
            _, fam, weight, style, _ = FACES[face]
            b64 = _subset_woff(face, chars)
            out.append(
                f"@font-face{{font-family:{fam};font-weight:{weight};font-style:{style};"
                f"src:url(data:font/woff;base64,{b64}) format('woff')}}"
            )
            out.append(
                f".f-{face}{{font-family:{fam},{FALLBACK[fam]};font-weight:{weight};font-style:{style}}}"
            )
        return "\n".join(out)

    def render(self) -> str:
        motion = "@media (prefers-reduced-motion:reduce){*{animation:none!important}}"
        css = "\n".join([self._font_css(), "text{white-space:pre}", *self.css, motion])
        tid, did = "title", "desc"
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'viewBox="0 0 {self.w} {self.h}" width="{self.w}" height="{self.h}" '
            f'role="img" aria-labelledby="{tid} {did}" fill="none">\n'
            f'<title id="{tid}">{esc(self.title)}</title>\n<desc id="{did}">{esc(self.desc or self.title)}</desc>\n'
            f"<style>\n{css}\n</style>\n"
            f"<defs>{''.join(self.defs)}</defs>\n"
            + "\n".join(self.body)
            + "\n</svg>\n"
        )

    def save(self, name: str) -> Path:
        path = OUT / self.t["name"] / f"{name}.svg"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.render(), encoding="utf-8")
        return path


# --------------------------------------------------------------- helpers ---
def card(doc: Doc, x=0.5, y=0.5, w=None, h=None, rx=22, fill=None, grain=False) -> None:
    """Rounded panel with a hairline border and a soft top highlight."""
    t = doc.t
    w = (doc.w - 1) if w is None else w
    h = (doc.h - 1) if h is None else h
    hi = doc.uid("hi")
    doc.define(
        f'<linearGradient id="{hi}" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{t["text"]}" stop-opacity="{0.05 if t["name"] == "dark" else 0.0}"/>'
        f'<stop offset=".35" stop-color="{t["text"]}" stop-opacity="0"/></linearGradient>'
    )
    doc.add(
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill or t["bg"]}"/>',
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="url(#{hi})"/>',
    )
    if grain:
        g = doc.uid("grain")
        doc.define(
            f'<filter id="{g}" x="0" y="0" width="100%" height="100%">'
            f'<feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="2" stitchTiles="stitch"/>'
            f'<feColorMatrix values="0 0 0 0 .5  0 0 0 0 .5  0 0 0 0 .5  0 0 0 {0.10 if t["name"] == "dark" else 0.07} 0"/></filter>'
        )
        doc.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" filter="url(#{g})"/>')
    doc.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" stroke="{t["line"]}"/>')


def glow(doc: Doc, cx, cy, r, color, opacity) -> None:
    g = doc.uid("glow")
    doc.define(
        f'<radialGradient id="{g}"><stop offset="0" stop-color="{color}" stop-opacity="{opacity}"/>'
        f'<stop offset="1" stop-color="{color}" stop-opacity="0"/></radialGradient>'
    )
    doc.add(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="url(#{g})"/>')


def dot_grid(doc: Doc, x, y, w, h, step=22, r=0.9, fade_cx=None, fade_cy=None, fade_r=None, rx=22) -> None:
    t = doc.t
    p, m, mg = doc.uid("dots"), doc.uid("mask"), doc.uid("mg")
    doc.define(
        f'<pattern id="{p}" width="{step}" height="{step}" patternUnits="userSpaceOnUse">'
        f'<circle cx="{step/2}" cy="{step/2}" r="{r}" fill="{t["dim"]}" opacity="{t["grid"]}"/></pattern>'
    )
    if fade_r:
        doc.define(
            f'<radialGradient id="{mg}" gradientUnits="userSpaceOnUse" cx="{fade_cx}" cy="{fade_cy}" r="{fade_r}">'
            f'<stop offset="0" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>'
            f'<mask id="{m}"><rect x="{x}" y="{y}" width="{w}" height="{h}" fill="url(#{mg})"/></mask>'
        )
        doc.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="url(#{p})" mask="url(#{m})"/>')
    else:
        doc.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="url(#{p})"/>')


def chip(doc: Doc, x, y, label, color=None, face="mono", size=12, pad=10, h=26, fill=None) -> float:
    """Outlined pill; returns its width."""
    t = doc.t
    w = measure(label, face, size, 0.4) + pad * 2
    doc.add(
        f'<rect x="{x}" y="{y}" width="{w:.1f}" height="{h}" rx="{h/2}" fill="{fill or t["surface2"]}" stroke="{t["line2"]}"/>',
        doc.text(x + w / 2, y + h / 2 + size * 0.36, label, face, size, color or t["soft"], "middle", 0.4),
    )
    return w


def chips(doc: Doc, x, y, labels, gap=8, **kw) -> float:
    for label in labels:
        x += chip(doc, x, y, label, **kw) + gap
    return x


def keyframes(name: str, stops: list[tuple[float, str]]) -> str:
    body = "".join(f"{p:.2f}%{{{decl}}}" for p, decl in stops)
    return f"@keyframes {name}{{{body}}}"


def fmt(n: int) -> str:
    return f"{n:,}"
