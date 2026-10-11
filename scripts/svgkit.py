"""Design system for the profile images.

Every SVG on the profile is generated from this module so the page reads as one
piece: two themes that follow GitHub's light/dark setting, Space Grotesk and
JetBrains Mono embedded as subset WOFF2 (an SVG shown through <img> cannot load
web fonts), one palette, and shared drawing helpers.
"""
from __future__ import annotations

import base64
import functools
import html
import io
import json
import math
import random
import re
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

HERE = Path(__file__).resolve().parent

# Emerald + blue, matching yamrajkhadka.com.np.
THEMES = {
    "dark": {
        "sky0": "#03060b", "sky1": "#06101a", "sky2": "#0b1923",
        "surface": "#0b131b", "surface2": "#0f1a24", "surface3": "#15222e",
        "line": "#1b2834", "line2": "#2a3b4b",
        "ink1": "#e8f0f3", "ink2": "#a3b4bf", "ink3": "#74878f",
        "brand": "#34d399", "brand_text": "#34d399", "brand_tint": "#0f2b23",
        "accent": "#60a5fa", "accent_text": "#7db5fb", "accent_tint": "#13243a",
        "star": "#dce8f3", "orb": "#f3e6bd", "orb_glow": "#f3e6bd",
        "mtn_far": ("#172839", "#0f1b26"), "mtn_mid": ("#111f2a", "#0a141c"),
        "mtn_near": ("#08140f", "#050c09"),
        "snow": "#d9e7f1", "snow_far": 0.30, "snow_mid": 0.50,
        "grid": "#1b2834", "baseline": "#2c3d4d",
    },
    "light": {
        "sky0": "#e3f2ee", "sky1": "#f0f8f5", "sky2": "#fdf1e3",
        "surface": "#ffffff", "surface2": "#f5f9f8", "surface3": "#eaf2f0",
        "line": "#e0e8e6", "line2": "#c9d6d3",
        "ink1": "#0c1a1e", "ink2": "#44565d", "ink3": "#65777e",
        "brand": "#059669", "brand_text": "#047857", "brand_tint": "#e2f6ee",
        "accent": "#2563eb", "accent_text": "#1d4ed8", "accent_tint": "#e7eefd",
        "star": "#ffffff", "orb": "#fbbf24", "orb_glow": "#fde68a",
        "mtn_far": ("#cfdfe2", "#dfeaeb"), "mtn_mid": ("#a1b7bf", "#bccdd2"),
        "mtn_near": ("#6b9a89", "#578775"),
        "snow": "#ffffff", "snow_far": 0.70, "snow_mid": 0.92,
        "grid": "#e4ebe9", "baseline": "#c3d0cd",
    },
}

# ── Type ──────────────────────────────────────────────────────────────────────

FONT_FILES = {"sans": HERE / "fonts" / "SpaceGrotesk.ttf", "mono": HERE / "fonts" / "JetBrainsMono.ttf"}
FONT_NAMES = {"sans": "YK Sans", "mono": "YK Mono"}
FALLBACKS = {
    "sans": "'Space Grotesk',ui-sans-serif,system-ui,-apple-system,'Segoe UI',Helvetica,Arial,sans-serif",
    "mono": "'JetBrains Mono',ui-monospace,SFMono-Regular,Menlo,Consolas,monospace",
}
# Class name -> (family, weight). Text elements pick their face with one of these.
TYPE = {
    "s4": ("sans", 400), "s5": ("sans", 500), "s6": ("sans", 600), "s7": ("sans", 700),
    "m4": ("mono", 400), "m5": ("mono", 500), "m7": ("mono", 700),
}


@functools.lru_cache(maxsize=None)
def _static_font(family: str, weight: int) -> bytes:
    font = instancer.instantiateVariableFont(TTFont(FONT_FILES[family], recalcTimestamp=False), {"wght": weight})
    font.recalcTimestamp = False  # keep output byte-identical between runs
    buf = io.BytesIO()
    font.save(buf)
    return buf.getvalue()


@functools.lru_cache(maxsize=None)
def _metrics(family: str, weight: int):
    font = TTFont(io.BytesIO(_static_font(family, weight)))
    advances = {name: adv for name, (adv, _) in font["hmtx"].metrics.items()}
    return font.getBestCmap(), advances, font["head"].unitsPerEm


def text_width(s: str, cls: str, size: float, tracking: float = 0.0) -> float:
    """Advance width of `s` in px (kerning ignored, so a hair wide for sans)."""
    cmap, advances, upm = _metrics(*TYPE[cls])
    units = sum(advances.get(cmap.get(ord(ch), ".notdef"), upm // 2) for ch in s)
    return units * size / upm + tracking * len(s)


def wrap(s: str, cls: str, size: float, max_width: float) -> list[str]:
    lines, line = [], ""
    for word in s.split():
        trial = f"{line} {word}".strip()
        if line and text_width(trial, cls, size) > max_width:
            lines.append(line)
            line = word
        else:
            line = trial
    return lines + [line] if line else lines


@functools.lru_cache(maxsize=None)
def _woff2(family: str, weight: int, chars: str) -> bytes:
    font = TTFont(io.BytesIO(_static_font(family, weight)), recalcTimestamp=False)
    options = subset.Options()
    options.flavor = "woff2"
    options.layout_features = ["kern", "liga", "calt", "ccmp", "locl", "mark", "mkmk", "tnum"]
    options.hinting = False
    options.desubroutinize = True
    subsetter = subset.Subsetter(options)
    subsetter.populate(text=chars)
    subsetter.subset(font)
    font.flavor = "woff2"
    buf = io.BytesIO()
    font.save(buf)
    return buf.getvalue()


def _font_css(body: str) -> str:
    used = {c for group in re.findall(r'class="([^"]*)"', body) for c in group.split()} & TYPE.keys()
    chars = "".join(sorted(set(_text_content(body)) | set(" 0123456789")))
    faces, rules = {}, []
    for cls in sorted(used):
        family, weight = TYPE[cls]
        if (family, weight) not in faces:
            data = base64.b64encode(_woff2(family, weight, chars)).decode()
            faces[(family, weight)] = (
                f"@font-face{{font-family:'{FONT_NAMES[family]}';font-weight:{weight};"
                f"src:url(data:font/woff2;base64,{data}) format('woff2')}}"
            )
        rules.append(f".{cls}{{font-family:'{FONT_NAMES[family]}',{FALLBACKS[family]};font-weight:{weight}}}")
    return "".join(faces.values()) + "".join(rules)


def _text_content(body: str) -> str:
    inner = re.findall(r"<text\b[^>]*>(.*?)</text>", body, re.S)
    return html.unescape(re.sub(r"<[^>]+>", "", "".join(inner)))


# ── Markup helpers ────────────────────────────────────────────────────────────

def esc(s) -> str:
    return html.escape(str(s), quote=True)


def fmt(v: float) -> str:
    return f"{v:.2f}".rstrip("0").rstrip(".") if isinstance(v, float) else str(v)


def text(x, y, s, cls, size, fill, *, anchor=None, tracking=None, opacity=None, attrs="") -> str:
    a = f'x="{fmt(x)}" y="{fmt(y)}" class="{cls}" font-size="{fmt(size)}" fill="{fill}"'
    if anchor:
        a += f' text-anchor="{anchor}"'
    if tracking:
        a += f' letter-spacing="{fmt(tracking)}"'
    if opacity is not None:
        a += f' opacity="{fmt(opacity)}"'
    return f"<text {a}{(' ' + attrs) if attrs else ''}>{esc(s)}</text>"


def rect(x, y, w, h, r=0, fill="none", stroke=None, sw=1, attrs="") -> str:
    a = f'x="{fmt(x)}" y="{fmt(y)}" width="{fmt(w)}" height="{fmt(h)}"'
    if r:
        a += f' rx="{fmt(r)}"'
    a += f' fill="{fill}"'
    if stroke:
        a += f' stroke="{stroke}" stroke-width="{fmt(sw)}"'
    return f"<rect {a}{(' ' + attrs) if attrs else ''}/>"


def pill(x, y, label, t, *, cls="m5", size=12.5, h=26, pad=11, fill=None, stroke=None, ink=None):
    """A rounded tag. Returns (markup, width)."""
    w = text_width(label, cls, size) + 2 * pad
    out = rect(x, y, w, h, h / 2, fill or t["surface2"], stroke or t["line2"])
    out += text(x + w / 2, y + h / 2 + size * 0.36, label, cls, size, ink or t["ink2"], anchor="middle")
    return out, w


def document(width, height, body, *, title, desc="", defs="", css="") -> str:
    style = (
        _font_css(body)
        + "text{font-kerning:normal;white-space:pre}"
        + ".fade{animation:fadeUp .9s cubic-bezier(.2,.7,.2,1) both}"
        + "@keyframes fadeUp{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}"
        + css
        + "@media (prefers-reduced-motion:reduce){*{animation:none!important}}"
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" xml:space="preserve" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">'
        f'<title id="title">{esc(title)}</title><desc id="desc">{esc(desc or title)}</desc>'
        f"<style>{style}</style><defs>{defs}</defs>{body}</svg>\n"
    )


def delay(seconds: float) -> str:
    return f'style="animation-delay:{seconds:.2f}s"'


# ── Color ─────────────────────────────────────────────────────────────────────

def _luminance(hex_color: str) -> float:
    r, g, b = (int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5))
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in (r, g, b)]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(a: str, b: str) -> float:
    hi, lo = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


# ── Icons ─────────────────────────────────────────────────────────────────────

@functools.lru_cache(maxsize=None)
def _icons(kind: str) -> dict:
    return json.loads((HERE / "icons" / f"{kind}.json").read_text())


def brand_color(slug: str, t: dict, bg: str) -> str:
    """The brand's own color, or the theme ink when it would vanish on `bg`."""
    hex_color = _icons("brands")[slug]["hex"]
    return hex_color if hex_color and contrast(hex_color, bg) >= 2.4 else t["ink1"]


def brand_icon(slug: str, x, y, size, color) -> str:
    d = _icons("brands")[slug]["path"]
    return f'<path transform="translate({fmt(x)} {fmt(y)}) scale({fmt(size / 24)})" d="{d}" fill="{color}"/>'


def ui_icon(name: str, x, y, size, color, stroke=2.0) -> str:
    return (
        f'<g transform="translate({fmt(x)} {fmt(y)}) scale({fmt(size / 24)})" fill="none" stroke="{color}" '
        f'stroke-width="{fmt(stroke)}" stroke-linecap="round" stroke-linejoin="round">{_icons("ui")[name]}</g>'
    )


def linkedin_icon(x, y, size, color, bg) -> str:
    """Simple Icons dropped LinkedIn, so draw the mark: a rounded square with 'in'."""
    s = size / 24
    return (
        f'<g transform="translate({fmt(x)} {fmt(y)}) scale({fmt(s)})">'
        f'<rect width="24" height="24" rx="4" fill="{color}"/>'
        f'<rect x="5" y="9.5" width="3" height="9.5" fill="{bg}"/><circle cx="6.5" cy="6.4" r="1.75" fill="{bg}"/>'
        f'<path d="M10.5 9.5h2.9v1.4c.5-.9 1.6-1.65 3.2-1.65 2.8 0 3.4 1.8 3.4 4.2V19h-3v-4.9c0-1.2-.1-2.4-1.6-2.4'
        f's-1.9 1.1-1.9 2.3V19h-3z" fill="{bg}"/></g>'
    )


def nepal_flag(x, y, height) -> str:
    """The flag of Nepal: two stacked pennants, crimson with a blue border, moon above sun."""
    s = height / (4 / 3)
    pts = [(0, 0), (1, 0.6262), (0.2929, 0.6262), (1, 4 / 3), (0, 4 / 3)]
    outline = " ".join(f"{fmt(x + px * s)},{fmt(y + py * s)}" for px, py in pts)
    mx, my, mr = x + 0.25 * s, y + 0.40 * s, 0.12 * s
    sun = []
    cx, cy = x + 0.27 * s, y + 1.02 * s
    for i in range(24):
        r = 0.135 * s if i % 2 == 0 else 0.085 * s
        a = i * math.pi / 12
        sun.append(f"{fmt(cx + r * math.cos(a))},{fmt(cy + r * math.sin(a))}")
    return (
        f'<g><polygon points="{outline}" fill="#dc143c" stroke="#003893" '
        f'stroke-width="{fmt(max(height * 0.075, 1.0))}" stroke-linejoin="miter"/>'
        f'<path d="M{fmt(mx - mr)} {fmt(my)} A{fmt(mr)} {fmt(mr)} 0 0 0 {fmt(mx + mr)} {fmt(my)} '
        f'A{fmt(mr)} {fmt(mr * 0.55)} 0 0 1 {fmt(mx - mr)} {fmt(my)}Z" fill="#fff"/>'
        f'<circle cx="{fmt(mx)}" cy="{fmt(my - mr * 0.15)}" r="{fmt(mr * 0.42)}" fill="#fff"/>'
        f'<polygon points="{" ".join(sun)}" fill="#fff"/></g>'
    )


# ── Landscape ─────────────────────────────────────────────────────────────────

def _fractal(n: int, rng: random.Random, roughness: float = 0.55) -> list[float]:
    """Midpoint displacement noise in [-1, 1]; n must be 2**k + 1."""
    vals = [0.0] * n
    vals[0], vals[-1] = rng.uniform(-1, 1), rng.uniform(-1, 1)
    step, scale = n - 1, 1.0
    while step > 1:
        half = step // 2
        for i in range(half, n - 1, step):
            vals[i] = (vals[i - half] + vals[i + half]) / 2 + rng.uniform(-scale, scale)
        step, scale = half, scale * roughness
    peak = max(abs(v) for v in vals) or 1.0
    return [v / peak for v in vals]


def ridge(width, height, peaks, *, base, jag, seed, round_=False, n=257):
    """A mountain range as a closed path. peaks = [(x, top_y, slope)].

    Returns (path_d, highest_y).
    """
    noise = _fractal(n, random.Random(seed))
    pts = []
    for i in range(n):
        x = -16 + (width + 32) * i / (n - 1)
        y = base
        for px, py, slope in peaks:
            dy = slope * (x - px) ** 2 / 160 if round_ else slope * abs(x - px)
            y = min(y, py + dy)
        pts.append((x, min(y + noise[i] * jag, height + 4)))
    d = "M" + " L".join(f"{fmt(px)},{fmt(py)}" for px, py in pts)
    d += f" L{fmt(width + 16)},{fmt(height + 16)} L-16,{fmt(height + 16)}Z"
    return d, min(py for _, py in pts)


def stars(rng: random.Random, count, box, avoid=()):
    """Random stars inside box=(x0, y0, x1, y1), skipping rectangles in `avoid`."""
    out = []
    while len(out) < count:
        x, y = rng.uniform(box[0], box[2]), rng.uniform(box[1], box[3])
        if any(a[0] <= x <= a[2] and a[1] <= y <= a[3] for a in avoid):
            continue
        out.append((x, y, rng.choice((0.6, 0.7, 0.8, 0.9, 1.1, 1.4)), rng.uniform(0.25, 0.85)))
    return out
