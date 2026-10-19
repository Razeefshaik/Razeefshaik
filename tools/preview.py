"""Local preview: renders README.md the way GitHub lays it out and screenshots it.

    python tools/preview.py [dark|light] [out.png] [--asset NAME]

Uses a headless Chrome/Edge with a throwaway profile. Nothing is uploaded.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BROWSERS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "google-chrome", "chromium", "chrome",
]
GH = {
    "dark": dict(bg="#0d1117", fg="#e6edf3", border="#30363d", muted="#8d96a0", link="#4493f8"),
    "light": dict(bg="#ffffff", fg="#1f2328", border="#d0d7de", muted="#59636e", link="#0969da"),
}
RAW = "https://raw.githubusercontent.com/Razeefshaik/Razeefshaik/main/"


def browser() -> str:
    for b in BROWSERS:
        if Path(b).exists() or shutil.which(b):
            return b
    sys.exit("No Chrome/Edge found")


GH_CSS = "https://cdnjs.cloudflare.com/ajax/libs/github-markdown-css/5.8.1/github-markdown-{theme}.min.css"


def page(body: str, theme: str, width: int) -> str:
    c = GH[theme]
    return f"""<!doctype html><html><head><meta charset="utf-8">
<link rel="stylesheet" href="{GH_CSS.format(theme=theme)}"><style>
body{{margin:0;background:{c['bg']};color:{c['fg']};font:16px/1.5 -apple-system,'Segoe UI',Helvetica,Arial,sans-serif}}
.box{{width:{width}px;margin:24px auto;border:1px solid {c['border']};border-radius:6px;padding:24px 32px}}
a{{color:{c['link']};text-decoration:none}} img{{max-width:100%;vertical-align:middle}} .markdown-body{{background:{c['bg']}}}
h2{{border-bottom:1px solid {c['border']};padding-bottom:.3em}} table{{border-collapse:collapse}}
td,th{{border:1px solid {c['border']};padding:6px 13px}} details summary{{cursor:pointer}}
sub{{color:{c['muted']}}}
</style></head><body><div class="box markdown-body">{body}</div></body></html>"""


def github_render(md: str) -> str | None:
    """Render with GitHub's own Markdown API (same sanitizer and GFM as the profile page)."""
    import json
    import urllib.request
    try:
        req = urllib.request.Request(
            "https://api.github.com/markdown",
            data=json.dumps({"text": md, "mode": "gfm", "context": "Razeefshaik/Razeefshaik"}).encode(),
            headers={"Accept": "application/vnd.github+json", "User-Agent": "profile-preview"})
        return urllib.request.urlopen(req, timeout=30).read().decode("utf-8")
    except Exception as e:
        print("GitHub render unavailable, using the built-in converter:", e, file=sys.stderr)
        return None


def readme_html(theme: str) -> str:
    md = (ROOT / "README.md").read_text(encoding="utf-8")
    rendered = github_render(md)
    if rendered:
        md = rendered
    # resolve raw URLs and <picture> sources to local files for the chosen theme
    md = md.replace(RAW, "")
    def pick(m):
        block = m.group(0)
        src = re.search(rf'media="\(prefers-color-scheme: {theme}\)"\s+srcset="([^"]+)"', block)
        img = re.search(r"<img[^>]*>", block).group(0)
        if src:
            img = re.sub(r'src="[^"]+"', f'src="{src.group(1)}"', img)
        return img
    md = re.sub(r"<picture>.*?</picture>", pick, md, flags=re.S)
    if rendered:
        return md
    # minimal markdown: headings, bold, links, paragraphs (the README is mostly HTML)
    md = re.sub(r"^## (.+)$", r"<h2>\1</h2>", md, flags=re.M)
    md = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", md)
    md = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', md)
    return md


def shoot(html: str, out: Path, width: int, height: int):
    tmp = Path(tempfile.mkdtemp(prefix="rzprev-"))
    try:
        f = ROOT / "_preview.html"
        f.write_text(html, encoding="utf-8")
        args = [browser(), "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-prefers-reduced-motion",
                f"--user-data-dir={tmp}", f"--window-size={width},{height}",
                "--virtual-time-budget=8000", f"--screenshot={out}", f.as_uri()]
        subprocess.run(args, check=True, capture_output=True, timeout=120)
        f.unlink(missing_ok=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    argv = sys.argv[1:]
    theme = argv[0] if argv and argv[0] in GH else "dark"
    out = Path(next((a for a in argv if a.endswith(".png")), ROOT / f"_preview-{theme}.png")).resolve()
    if "--asset" in argv:
        name = argv[argv.index("--asset") + 1]
        rel = f"assets/v3/{theme}/{name}.svg"
        html = page(f'<img src="{rel}" width="100%">', theme, 900)
        shoot(html, out, 1000, int(argv[argv.index("--h") + 1]) if "--h" in argv else 560)
    else:
        h = int(argv[argv.index("--h") + 1]) if "--h" in argv else 6000
        shoot(page(readme_html(theme), theme, 896), out, 1000, h)
    print(out)


if __name__ == "__main__":
    main()
