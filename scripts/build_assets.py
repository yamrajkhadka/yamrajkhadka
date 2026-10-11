"""Render the static profile images into assets/ and regenerate README.md.

    pip install -r scripts/requirements.txt
    python scripts/build_assets.py

Each image is written twice, <name>-dark.svg and <name>-light.svg, and the README
serves the right one through <picture> and GitHub's prefers-color-scheme.
Live numbers (contributions, languages, downloads) are not here: they come from
build_stats.py, which a GitHub Action runs daily.
"""
from __future__ import annotations

import math
import random
from pathlib import Path

from svgkit import (THEMES, brand_color, brand_icon, delay, document, esc, fmt, linkedin_icon, nepal_flag,
                    pill, rect, ridge, stars, text, text_width, ui_icon, wrap)

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
USER = "yamrajkhadka"
RAW = f"https://raw.githubusercontent.com/{USER}/{USER}"
GH = f"https://github.com/{USER}"

LINKS = {
    "website": "https://www.yamrajkhadka.com.np",
    "linkedin": "https://linkedin.com/in/yamraj-khadka-7806b833b",
    "huggingface": "https://huggingface.co/yamraj047",
    "app": "https://nepallawai.yamrajkhadka.com.np",
    "model": "https://huggingface.co/yamraj047/nepal-legal-mistral-7b",
    "space": "https://huggingface.co/spaces/yamraj047/GGUF_with-RAG",
    "paper": "https://lnkd.in/g6F8w8nM",
}

# ── Hero ──────────────────────────────────────────────────────────────────────

PHRASES = [
    "fine-tuning LLMs for Nepali law",
    "building hybrid RAG over 5,849 legal provisions",
    "orchestrating multi-agent systems with LangGraph",
    "segmenting satellite imagery with U-Net",
    "shipping models with MLflow and FastAPI",
]

# A small feed-forward net drawn as a constellation: query -> ... -> answer.
NET = [
    [(772, 104), (750, 168), (774, 230)],
    [(872, 70), (892, 128), (866, 186), (888, 240)],
    [(990, 98), (1008, 164), (986, 226)],
    [(1096, 162)],
]


def _keytimes(events, total):
    """Collapse (time, value) events into SMIL keyTimes/values (discrete)."""
    times, values = [], []
    for t, v in events:
        if values and values[-1] == v:
            continue
        times.append(min(t / total, 1.0))
        values.append(v)
    return ";".join(f"{k:.4f}" for k in times), ";".join(fmt(float(v)) for v in values)


def typing(x, y, phrases, t, *, size=19.0, start=1.1, type_s=0.055, hold_s=1.9, del_s=0.024, gap_s=0.45):
    """A looping typewriter: one clipped <text> per phrase, revealed by SMIL."""
    cw = text_width("M", "m4", size)
    events, now = [(0.0, -1, 0)], start
    for i, phrase in enumerate(phrases):
        for n in range(1, len(phrase) + 1):
            events.append((now, i, n))
            now += type_s
        now += hold_s
        for n in range(len(phrase) - 1, -1, -1):
            events.append((now, i, n))
            now += del_s
        now += gap_s
    total = now
    defs, body = [], []
    for i, phrase in enumerate(phrases):
        kt, vals = _keytimes([(et, n * cw if ei == i else 0) for et, ei, n in events], total)
        defs.append(
            f'<clipPath id="type{i}"><rect x="{fmt(x)}" y="{fmt(y - size * 1.05)}" width="0" height="{fmt(size * 1.6)}">'
            f'<animate attributeName="width" dur="{total:.2f}s" repeatCount="indefinite" calcMode="discrete" '
            f'keyTimes="{kt}" values="{vals}"/></rect></clipPath>'
        )
        body.append(f'<g clip-path="url(#type{i})">{text(x, y, phrase, "m4", size, t["ink1"])}</g>')
    kt, vals = _keytimes([(et, x + n * cw) for et, _, n in events], total)
    body.append(
        f'<rect class="caret" x="{fmt(x)}" y="{fmt(y - size * 0.8)}" width="{fmt(size * 0.5)}" '
        f'height="{fmt(size * 1.0)}" rx="1.5" fill="{t["brand"]}">'
        f'<animate attributeName="x" dur="{total:.2f}s" repeatCount="indefinite" calcMode="discrete" '
        f'keyTimes="{kt}" values="{vals}"/></rect>'
    )
    return "".join(defs), "".join(body)


def sky_and_landscape(t, theme, W, H, *, seed, ranges, orb, star_box, avoid, net=False):
    """Shared night/day scene: sky, aurora or sun haze, stars, orb, mountain ranges."""
    rng = random.Random(seed)
    dark = theme == "dark"
    defs = [
        f'<clipPath id="card"><rect width="{W}" height="{H}" rx="20"/></clipPath>',
        f'<linearGradient id="sky" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="0" y2="{H}">'
        f'<stop offset="0" stop-color="{t["sky0"]}"/><stop offset=".6" stop-color="{t["sky1"]}"/>'
        f'<stop offset="1" stop-color="{t["sky2"]}"/></linearGradient>',
        f'<radialGradient id="orbglow"><stop offset="0" stop-color="{t["orb_glow"]}" stop-opacity="{".22" if dark else ".75"}"/>'
        f'<stop offset="1" stop-color="{t["orb_glow"]}" stop-opacity="0"/></radialGradient>',
    ]
    body = ['<g clip-path="url(#card)">', rect(0, 0, W, H, fill="url(#sky)")]
    if dark:
        defs.append('<filter id="soft" x="-30%" y="-80%" width="160%" height="260%"><feGaussianBlur stdDeviation="26"/></filter>')
        defs.append(
            f'<linearGradient id="aurora" x1="0" x2="1"><stop offset="0" stop-color="{t["brand"]}" stop-opacity="0"/>'
            f'<stop offset=".35" stop-color="{t["brand"]}" stop-opacity=".6"/><stop offset=".72" stop-color="{t["accent"]}" '
            f'stop-opacity=".45"/><stop offset="1" stop-color="{t["accent"]}" stop-opacity="0"/></linearGradient>'
        )
        ax = W * 0.32
        body.append(
            f'<g filter="url(#soft)" opacity=".30"><path class="aurora" d="M{fmt(ax)} {fmt(H * .27)} C {fmt(ax + 190)} {fmt(H * .05)}, '
            f'{fmt(ax + 400)} {fmt(H * .42)}, {fmt(ax + 620)} {fmt(H * .16)} S {fmt(W + 60)} {fmt(H * .3)}, {fmt(W + 120)} {fmt(H * .12)}" '
            f'stroke="url(#aurora)" stroke-width="64" fill="none"/>'
            f'<path class="aurora a2" d="M{fmt(ax + 140)} {fmt(H * .45)} C {fmt(ax + 320)} {fmt(H * .3)}, {fmt(ax + 480)} {fmt(H * .55)}, '
            f'{fmt(ax + 700)} {fmt(H * .36)}" stroke="url(#aurora)" stroke-width="36" fill="none" opacity=".7"/></g>'
        )
        for x, y, r, o in stars(rng, int(W * H / 4200), star_box, avoid):
            tw = rng.random() < 0.3
            attrs = f' class="tw" style="animation-duration:{rng.uniform(2.6, 5.5):.1f}s;animation-delay:-{rng.uniform(0, 5):.1f}s"' if tw else ""
            body.append(f'<circle cx="{fmt(x)}" cy="{fmt(y)}" r="{fmt(r)}" fill="{t["star"]}" opacity="{o:.2f}"{attrs}/>')
    ox, oy, orad = orb
    body.append(f'<circle cx="{fmt(ox)}" cy="{fmt(oy)}" r="{fmt(orad * (3.4 if dark else 5))}" fill="url(#orbglow)"/>')
    if dark:  # crescent moon: a lit disc with the sky drawn over its offset
        body.append(f'<circle cx="{fmt(ox)}" cy="{fmt(oy)}" r="{fmt(orad)}" fill="{t["orb"]}" opacity=".92"/>')
        body.append(f'<circle cx="{fmt(ox + orad * .42)}" cy="{fmt(oy - orad * .28)}" r="{fmt(orad * .86)}" fill="url(#sky)"/>')
    else:
        body.append(f'<circle cx="{fmt(ox)}" cy="{fmt(oy)}" r="{fmt(orad)}" fill="{t["orb"]}"/>')

    if net:
        body.append(_network(t, dark))

    # Mountain ranges, far to near, each fading into haze for depth.
    for i, (name, peaks, base, jag, rseed, kind) in enumerate(ranges):
        top_c, bottom_c = t[name]
        d, top = ridge(W, H, peaks, base=base, jag=jag, seed=rseed, round_=(kind == "round"))
        gid = f"m{i}"
        defs.append(
            f'<linearGradient id="{gid}" gradientUnits="userSpaceOnUse" x1="0" y1="{fmt(top)}" x2="0" y2="{H}">'
            f'<stop offset="0" stop-color="{top_c}"/><stop offset="1" stop-color="{bottom_c}"/></linearGradient>'
        )
        defs.append(f'<clipPath id="c{gid}"><path d="{d}"/></clipPath>')
        body.append(f'<path d="{d}" fill="url(#{gid})"/>')
        if kind == "snow":
            alpha = t["snow_far"] if i == 0 else t["snow_mid"]
            depth = 64 if i == 0 else 46
            defs.append(
                f'<linearGradient id="s{gid}" gradientUnits="userSpaceOnUse" x1="0" y1="{fmt(top)}" x2="0" y2="{fmt(top + depth)}">'
                f'<stop offset="0" stop-color="{t["snow"]}" stop-opacity="{alpha}"/>'
                f'<stop offset="1" stop-color="{t["snow"]}" stop-opacity="0"/></linearGradient>'
            )
            body.append(f'<g clip-path="url(#c{gid})">{rect(0, top - 2, W, depth + 2, fill=f"url(#s{gid})")}</g>')
        if i < len(ranges) - 1:
            defs.append(
                f'<linearGradient id="h{gid}" gradientUnits="userSpaceOnUse" x1="0" y1="{fmt(top)}" x2="0" y2="{H}">'
                f'<stop offset="0" stop-color="{t["sky2"]}" stop-opacity="0"/>'
                f'<stop offset="1" stop-color="{t["sky2"]}" stop-opacity="{".5" if dark else ".55"}"/></linearGradient>'
            )
            body.append(f'<path d="{d}" fill="url(#h{gid})"/>')
    body.append("</g>")
    body.append(rect(0.5, 0.5, W - 1, H - 1, 19.5, "none", t["line"]))
    css = (
        ".aurora{animation:drift 17s ease-in-out infinite alternate}.a2{animation-duration:12s}"
        "@keyframes drift{from{transform:translateX(-34px)}to{transform:translateX(34px)}}"
        ".tw{animation:tw 4s ease-in-out infinite}@keyframes tw{50%{opacity:.08}}"
    )
    return "".join(defs), "".join(body), css


def _network(t, dark):
    edge_c, edge_o = (t["ink2"], 0.17) if dark else (t["ink3"], 0.26)
    out = []
    for a, b in zip(NET, NET[1:]):
        for x1, y1 in a:
            for x2, y2 in b:
                out.append(f'<path d="M{x1} {y1} L{x2} {y2}" stroke="{edge_c}" stroke-opacity="{edge_o}" stroke-width="1"/>')
    # One forward pass every 5 s: signals hop layer to layer, then the output flashes.
    rng = random.Random(3)
    for phase, (a, b) in enumerate(zip(NET, NET[1:])):
        pairs = [(p, q) for p in a for q in b]
        for (x1, y1), (x2, y2) in rng.sample(pairs, min(4, len(pairs))):
            out.append(
                f'<path class="pulse ph{phase}" d="M{x1} {y1} L{x2} {y2}" pathLength="100" stroke="{t["brand"]}" stroke-width="2.4"/>'
            )
    for li, layer in enumerate(NET):
        for x, y in layer:
            last = li == len(NET) - 1
            core = t["accent"] if last else t["brand"]
            out.append(f'<circle cx="{x}" cy="{y}" r="{11 if last else 9}" fill="{core}" opacity="{".14" if dark else ".12"}"/>')
            out.append(f'<circle cx="{x}" cy="{y}" r="{4.6 if last else 3.4}" fill="{core}"/>')
            if dark:
                out.append(f'<circle cx="{x}" cy="{y}" r="1.3" fill="#ffffff" opacity=".85"/>')
            if last:
                out.append(f'<circle class="flash" cx="{x}" cy="{y}" r="14" fill="none" stroke="{core}" stroke-width="1.6"/>')
    return "".join(out)


NET_CSS = (
    ".pulse{fill:none;stroke-dasharray:12 120;stroke-dashoffset:12;stroke-linecap:round;opacity:0;"
    "animation-duration:5s;animation-timing-function:linear;animation-iteration-count:infinite}"
    ".ph0{animation-name:ph0}.ph1{animation-name:ph1}.ph2{animation-name:ph2}"
    "@keyframes ph0{0%{stroke-dashoffset:12;opacity:0}1%{opacity:1}19%{stroke-dashoffset:-100;opacity:1}20%,100%{stroke-dashoffset:-100;opacity:0}}"
    "@keyframes ph1{0%,21%{stroke-dashoffset:12;opacity:0}22%{opacity:1}40%{stroke-dashoffset:-100;opacity:1}41%,100%{stroke-dashoffset:-100;opacity:0}}"
    "@keyframes ph2{0%,42%{stroke-dashoffset:12;opacity:0}43%{opacity:1}58%{stroke-dashoffset:-100;opacity:1}59%,100%{stroke-dashoffset:-100;opacity:0}}"
    ".flash{opacity:0;transform-box:fill-box;transform-origin:center;animation:flash 5s ease-out infinite}"
    "@keyframes flash{0%,57%{opacity:0;transform:scale(.5)}63%{opacity:.9;transform:scale(1)}82%,100%{opacity:0;transform:scale(2)}}"
)


def hero(t, theme):
    W, H = 1200, 440
    ranges = [
        ("mtn_far", [(120, 362, .5), (330, 350, .6), (560, 314, .6), (760, 286, .75), (958, 256, 1.05), (1120, 278, .7)],
         424, 9, 11, "snow"),
        ("mtn_mid", [(200, 386, .45), (470, 358, .5), (700, 334, .62), (906, 296, 1.05), (940, 306, 1.25), (1150, 322, .6)],
         432, 7, 23, "snow"),
        ("mtn_near", [(60, 414, .22), (330, 420, .18), (600, 412, .2), (860, 404, .2), (1150, 410, .24)], 446, 4, 5, "round"),
    ]
    defs, body, css = sky_and_landscape(
        t, theme, W, H, seed=7, ranges=ranges, orb=(1132, 70, 21),
        star_box=(0, 0, W, 330), avoid=[(40, 46, 730, 360), (1080, 30, 1180, 110)], net=True,
    )
    x0 = 72
    tdefs, tbody = typing(x0 + 28, 286, PHRASES, t)
    chips, cx = [], x0
    flag = nepal_flag(cx + 14, 323.5, 17)
    label = "KATHMANDU, NEPAL"
    w = 14 + 13 + 10 + text_width(label, "m5", 12, 1.6) + 14
    chips.append(rect(cx, 317, w, 30, 15, t["surface"], t["line2"], attrs='fill-opacity=".72"') + flag
                 + text(cx + 14 + 13 + 10, 336.5, label, "m5", 12, t["ink2"], tracking=1.6))
    cx += w + 10
    label = "OPEN TO AI/ML ROLES & RESEARCH"
    w = 14 + 8 + 10 + text_width(label, "m5", 12, 1.6) + 14
    chips.append(rect(cx, 317, w, 30, 15, t["surface"], t["line2"], attrs='fill-opacity=".72"')
                 + f'<circle class="live" cx="{fmt(cx + 18)}" cy="332" r="7" fill="{t["brand"]}" opacity=".25"/>'
                 + f'<circle cx="{fmt(cx + 18)}" cy="332" r="3.6" fill="{t["brand"]}"/>'
                 + text(cx + 14 + 8 + 10, 336.5, label, "m5", 12, t["ink2"], tracking=1.6))
    name_w = text_width("Yamraj Khadka", "s7", 76, -2.2)
    dot = f'<circle cx="{fmt(x0 - 3 + name_w + 7)}" cy="179" r="6.5" fill="{t["brand"]}"/>'
    content = (
        f'<g class="fade" {delay(.05)}>{rect(x0, 101, 26, 2.5, 1.25, t["brand"])}'
        f'{text(x0 + 38, 108, "NAMASTE, I’M", "m5", 13.5, t["ink2"], tracking=3.4)}</g>'
        f'<g class="fade" {delay(.15)}><text x="{x0 - 3}" y="186" class="s7" font-size="76" letter-spacing="-2.2" fill="{t["ink1"]}">'
        f'Yamraj Khadka</text>{dot}</g>'
        f'<g class="fade" {delay(.3)}>{text(x0, 232, "Computer Engineer · AI/ML Engineer & Researcher", "s5", 24, t["ink2"])}</g>'
        f'<g class="fade" {delay(.45)}>{text(x0, 286, "❯", "m7", 19, t["brand"])}{tbody}</g>'
        f'<g class="fade" {delay(.6)}>{"".join(chips)}</g>'
    )
    css += NET_CSS + (
        ".caret{animation:blink 1.06s steps(1) infinite}@keyframes blink{50%{opacity:0}}"
        ".live{transform-box:fill-box;transform-origin:center;animation:live 2.2s ease-out infinite}"
        "@keyframes live{0%{transform:scale(.6);opacity:.55}100%{transform:scale(2.1);opacity:0}}"
    )
    return document(
        W, H, body + content, defs=defs + tdefs, css=css,
        title="Yamraj Khadka — Computer Engineer · AI/ML Engineer & Researcher",
        desc="Kathmandu, Nepal. Fine-tuning LLMs for Nepali law, hybrid RAG, multi-agent systems, U-Net segmentation and MLOps.",
    )


# ── Section headers ───────────────────────────────────────────────────────────

SECTIONS = {
    "about": ("01", "About", "whoami"),
    "work": ("02", "Featured work", "selected builds"),
    "journey": ("03", "Journey", "dec 2024 → now"),
    "toolkit": ("04", "Toolkit", "daily drivers"),
    "telemetry": ("05", "Telemetry", "live · refreshed daily"),
}


def header(t, theme, key):
    num, title, note = SECTIONS[key]
    W, H = 1200, 64
    nx = text_width(num, "m5", 15, 1) + 16
    tx = nx + text_width(title, "s7", 30, -0.6) + 24
    note_w = text_width(note, "m4", 13, 1.6)
    body = (
        text(2, 42, num, "m5", 15, t["brand_text"], tracking=1)
        + text(nx, 43, title, "s7", 30, t["ink1"], tracking=-0.6)
        + f'<path d="M{fmt(tx)} 36.5 H{fmt(W - note_w - 22)}" stroke="{t["line2"]}" stroke-width="1"/>'
        + rect(tx - 3, 34, 5, 5, 1, t["brand"])
        + text(W - 2, 41, note, "m4", 13, t["ink3"], anchor="end", tracking=1.6)
    )
    return document(W, H, body, title=f"{num} {title}")


# ── About: terminal ───────────────────────────────────────────────────────────

TERMINAL = [
    ("cmd", "whoami"),
    ("out", [("Yamraj Khadka", "ink1", "m7"), ("  ·  Computer Engineer · AI/ML Engineer & Researcher", "ink2", "m4")]),
    ("out", [("IOE Purwanchal Campus  ·  Kathmandu, Nepal", "ink2", "m4")]),
    ("cmd", "cat mission.txt"),
    ("out", [("I build AI systems end to end: from research and fine-tuned LLMs to production pipelines.", "ink1", "m4")]),
    ("cmd", "ls focus/"),
    ("out", [("llms/", "accent_text", "m5"), ("   rag-pipelines/", "accent_text", "m5"), ("   agentic-ai/", "accent_text", "m5"),
             ("   computer-vision/", "accent_text", "m5"), ("   mlops/", "accent_text", "m5")]),
    ("cmd", "cat status.txt"),
    ("out", [("●", "brand", "m4"), (" Open to AI research, data science and ML engineering roles, and research collaborations.",
                                     "ink1", "m4")]),
    ("prompt", None),
]


def about(t, theme):
    W, size, lh, top = 1200, 17.0, 31, 92
    H = top + (len(TERMINAL) - 1) * lh + 34
    x_prompt, x_text = 34, 34 + text_width("❯ ", "m4", size)
    defs, body = [], []
    body.append(rect(0.5, 0.5, W - 1, H - 1, 18, t["surface"], t["line"]))
    body.append(f'<path d="M0.5 46 V18.5 a18 18 0 0 1 18 -18 H{W - 18.5} a18 18 0 0 1 18 18 V46 Z" fill="{t["surface2"]}"/>')
    body.append(f'<path d="M0.5 46 H{W - 0.5}" stroke="{t["line"]}"/>')
    for i, c in enumerate(("#ff5f57", "#febc2e", "#28c840")):
        body.append(f'<circle cx="{28 + i * 22}" cy="23.5" r="6.5" fill="{c}"/>')
    body.append(text(W / 2, 28, "yamraj@kathmandu: ~", "m5", 13, t["ink3"], anchor="middle"))
    now = 0.5
    cw = text_width("M", "m4", size)
    for i, (kind, payload) in enumerate(TERMINAL):
        y = top + i * lh
        if kind == "cmd":
            n = len(payload)
            body.append(f'<g class="show" {delay(now)}>{text(x_prompt, y, "❯", "m7", size, t["brand"])}</g>')
            steps = [(0.0, 0)] + [(now + 0.12 + k * 0.05, k * cw) for k in range(1, n + 1)]
            total = steps[-1][0] + 0.01
            kt = ";".join(f"{s / total:.4f}" for s, _ in steps)
            vals = ";".join(fmt(float(v)) for _, v in steps)
            defs.append(
                f'<clipPath id="cmd{i}"><rect x="{fmt(x_text)}" y="{fmt(y - size)}" width="{fmt(n * cw)}" height="{fmt(size * 1.6)}">'
                f'<animate attributeName="width" dur="{total:.2f}s" fill="freeze" calcMode="discrete" keyTimes="{kt}" values="{vals}"/>'
                f"</rect></clipPath>"
            )
            body.append(f'<g clip-path="url(#cmd{i})">{text(x_text, y, payload, "m5", size, t["ink1"])}</g>')
            now = total + 0.2
        elif kind == "out":
            spans, x = "", x_text
            for s, color, cls in payload:
                spans += text(x, y, s, cls, size, t[color])
                x += text_width(s, cls, size)
            body.append(f'<g class="show" {delay(now)}>{spans}</g>')
            now += 0.16
            if i + 1 < len(TERMINAL) and TERMINAL[i + 1][0] != "out":
                now += 0.35
        else:
            body.append(f'<g class="show" {delay(now)}>{text(x_prompt, y, "❯", "m7", size, t["brand"])}'
                        f'<rect class="caret" x="{fmt(x_text)}" y="{fmt(y - size * 0.8)}" width="{fmt(size * 0.55)}" '
                        f'height="{fmt(size)}" rx="1.5" fill="{t["ink1"]}"/></g>')
    css = (
        ".show{animation:show .35s ease-out both}@keyframes show{from{opacity:0}to{opacity:1}}"
        ".caret{animation:blink 1.06s steps(1) infinite}@keyframes blink{50%{opacity:0}}"
    )
    return document(
        W, H, "".join(body), defs="".join(defs), css=css,
        title="About Yamraj Khadka",
        desc="Computer Engineer and AI/ML engineer & researcher from IOE Purwanchal Campus, based in Kathmandu, Nepal. "
             "Builds AI systems end to end, from research and fine-tuned LLMs to production pipelines. Focus: LLMs, RAG pipelines, "
             "agentic AI, computer vision, MLOps. Open to AI research, data science and ML engineering roles, and research collaborations.",
    )


HIGHLIGHTS = [
    ("7B", "Legal LLM shipped", "Mistral 7B + LoRA on Hugging Face"),
    ("0.674", "U-Net mean IoU", "published in JoEIS, Vol. 5"),
    ("5,849", "Legal provisions indexed", "hybrid RAG over 6 Nepali laws"),
    ("100+", "Students mentored", "45-hour AI/ML bootcamp"),
]


def highlights(t, theme):
    W, H, gap = 1200, 146, 16
    tw = (W - gap * 3) / 4
    body = []
    for i, (value, label, sub) in enumerate(HIGHLIGHTS):
        x = i * (tw + gap)
        body.append(
            f'<g class="fade" {delay(.1 + i * .12)}>'
            + rect(x + .5, .5, tw - 1, H - 1, 16, t["surface"], t["line"])
            + rect(x + 24, 24, 22, 3, 1.5, t["brand"])
            + text(x + 22, 82, value, "s7", 46, t["ink1"], tracking=-1.2)
            + text(x + 24, 110, label, "s6", 15.5, t["ink1"])
            + text(x + 24, 130, sub, "s4", 13.5, t["ink2"])
            + "</g>"
        )
    return document(
        W, H, "".join(body), title="Highlights",
        desc="; ".join(f"{v} {l} ({s})" for v, l, s in HIGHLIGHTS),
    )


# ── Featured work ─────────────────────────────────────────────────────────────

PIPELINE = [
    # (key, title, subtitle, row) — row 0 sits on the main line, -1/+1 split above/below it.
    ("q", "Question", "plain English", 0),
    ("dense", "Dense search", "mpnet + FAISS", -1),
    ("bm25", "Keyword search", "BM25", 1),
    ("rrf", "RRF fusion", "k = 60", 0),
    ("boost", "Section boost", "exact § match", 0),
    ("rerank", "Rerank", "cross-encoder", 0),
    ("llm", "Mistral 7B", "LoRA · GGUF", 0),
    ("ans", "Cited answer", "law · section", 0),
]


def flagship(t, theme):
    W, H = 1200, 476
    dark = theme == "dark"
    defs = [
        f'<radialGradient id="glow" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse" gradientTransform="translate(120 40) scale(620 360)">'
        f'<stop offset="0" stop-color="{t["brand"]}" stop-opacity="{".13" if dark else ".10"}"/>'
        f'<stop offset="1" stop-color="{t["brand"]}" stop-opacity="0"/></radialGradient>',
        f'<clipPath id="card"><rect width="{W}" height="{H}" rx="20"/></clipPath>',
    ]
    body = [rect(0.5, 0.5, W - 1, H - 1, 19.5, t["surface"], t["line"]),
            f'<g clip-path="url(#card)">{rect(0, 0, W, H, fill="url(#glow)")}'
            f'<g opacity=".035">{ui_icon("scale", 1000, -86, 290, t["ink1"], 1.1)}</g></g>']
    # Kicker row
    tag, tag_w = pill(40, 34, "FLAGSHIP", t, cls="m7", size=11.5, h=26, pad=12, fill=t["brand_tint"],
                      stroke=t["brand"], ink=t["brand_text"])
    body.append(tag)
    body.append(text(40 + tag_w + 14, 51.5, "LEGAL AI FOR NEPAL", "m5", 12.5, t["ink3"], tracking=2.2))
    live = "nepallawai.yamrajkhadka.com.np"
    url_end = W - 64
    live_x = url_end - text_width(live, "m5", 13) - 14 - text_width("LIVE", "m7", 12, 1.5)
    body.append(f'<circle class="live" cx="{fmt(live_x - 15)}" cy="47" r="7" fill="{t["brand"]}" opacity=".25"/>'
                f'<circle cx="{fmt(live_x - 15)}" cy="47" r="3.6" fill="{t["brand"]}"/>')
    body.append(text(live_x, 51.5, "LIVE", "m7", 12, t["brand_text"], tracking=1.5))
    body.append(text(url_end, 51.5, live, "m5", 13, t["ink2"], anchor="end"))
    body.append(ui_icon("arrow-up-right", W - 58, 39, 16, t["ink3"], 2.2))
    # Title + description
    body.append(text(38, 116, "Nepal Legal AI", "s7", 44, t["ink1"], tracking=-1.2))
    desc = ("A legal LLM and retrieval stack for Nepali law: Mistral 7B fine-tuned with LoRA on the National Penal "
            "Code 2017, grounded by hybrid retrieval over 5,849 provisions from 6 laws, so answers point back to the "
            "exact law and section.")
    for i, line in enumerate(wrap(desc, "s4", 18, 760)):
        body.append(text(40, 154 + i * 27, line, "s4", 18, t["ink2"]))
    # Fact column
    facts = [("6,400", "fine-tuning examples"), ("< 1 day", "to community GGUF quants"), ("3", "live Hugging Face Spaces")]
    fx = 880
    body.append(f'<path d="M{fx - 28} 96 V214" stroke="{t["line2"]}"/>')
    for i, (v, l) in enumerate(facts):
        y = 120 + i * 40
        body.append(text(fx, y, v, "s7", 25, t["ink1"], tracking=-0.5))
        body.append(text(fx + text_width(v, "s7", 25, -0.5) + 10, y - 1, l, "s4", 14, t["ink2"]))
    # Pipeline
    body.append(text(40, 262, "HOW AN ANSWER IS BUILT", "m5", 11.5, t["ink3"], tracking=2))
    body.append(f'<path d="M{fmt(40 + text_width("HOW AN ANSWER IS BUILT", "m5", 11.5, 2) + 12)} 258 H{W - 40}" stroke="{t["line"]}"/>')
    body.append(_pipeline(t, y_mid=338))
    # Ships as
    body.append(text(40, 444, "SHIPS AS", "m5", 11.5, t["ink3"], tracking=2))
    x = 40 + text_width("SHIPS AS", "m5", 11.5, 2) + 16
    for label in ("Next.js web app · live", "Expo mobile app", "Streamlit app", "FastAPI retriever", "Hugging Face Spaces"):
        p, w = pill(x, 425, label, t, cls="m5", size=12, h=27, pad=12)
        body.append(p)
        x += w + 8
    css = (
        ".flow{stroke-dasharray:1.6 7.4;stroke-linecap:round;animation:flow 1.1s linear infinite}"
        "@keyframes flow{to{stroke-dashoffset:-9}}"
        ".live{transform-box:fill-box;transform-origin:center;animation:live 2.2s ease-out infinite}"
        "@keyframes live{0%{transform:scale(.6);opacity:.55}100%{transform:scale(2.1);opacity:0}}"
    )
    return document(
        W, H, "".join(body), defs="".join(defs), css=css,
        title="Nepal Legal AI — flagship project",
        desc=desc + " Pipeline: question → dense search (mpnet + FAISS) and BM25 keyword search → reciprocal rank fusion → "
                    "section-number boost → cross-encoder rerank → fine-tuned Mistral 7B → cited answer. "
                    "Live at nepallawai.yamrajkhadka.com.np.",
    )


def _pipeline(t, y_mid):
    bh, split = 54, 38
    widths = {}
    for key, title, sub, _ in PIPELINE:
        widths[key] = max(text_width(title, "s6", 15), text_width(sub, "m4", 11.5)) + 34
    order = ["q", "split", "rrf", "boost", "rerank", "llm", "ans"]
    col_w = [widths["q"], max(widths["dense"], widths["bm25"]), widths["rrf"], widths["boost"], widths["rerank"],
             widths["llm"], widths["ans"]]
    gap = (1200 - 80 - sum(col_w)) / (len(col_w) - 1)
    xs, x = [], 40.0
    for w in col_w:
        xs.append(x)
        x += w + gap
    boxes = {}
    for ci, key in enumerate(order):
        if key == "split":
            for k, row in (("dense", -1), ("bm25", 1)):
                boxes[k] = (xs[ci], y_mid + row * split - bh / 2, col_w[ci], bh)
        else:
            boxes[key] = (xs[ci], y_mid - bh / 2, col_w[ci], bh)

    def right(k):
        x, y, w, h = boxes[k]
        return x + w, y + h / 2

    def left(k):
        x, y, w, h = boxes[k]
        return x, y + h / 2

    links = [("q", "dense"), ("q", "bm25"), ("dense", "rrf"), ("bm25", "rrf"), ("rrf", "boost"), ("boost", "rerank"),
             ("rerank", "llm"), ("llm", "ans")]
    out = []
    for a, b in links:
        (x1, y1), (x2, y2) = right(a), left(b)
        mx = (x1 + x2) / 2
        d = f"M{fmt(x1)} {fmt(y1)} C{fmt(mx)} {fmt(y1)} {fmt(mx)} {fmt(y2)} {fmt(x2)} {fmt(y2)}"
        out.append(f'<path d="{d}" fill="none" stroke="{t["line2"]}" stroke-width="1.4"/>')
        out.append(f'<path class="flow" d="{d}" fill="none" stroke="{t["brand"]}" stroke-width="2.2" opacity=".85"/>')
    for key, title, sub, _ in PIPELINE:
        x, y, w, h = boxes[key]
        hot = key == "llm"
        out.append(rect(x, y, w, h, 12, t["brand_tint"] if hot else t["surface2"], t["brand"] if hot else t["line2"],
                        1.4 if hot else 1))
        out.append(text(x + w / 2, y + 23, title, "s6", 15, t["ink1"], anchor="middle"))
        out.append(text(x + w / 2, y + 41, sub, "m4", 11.5, t["brand_text"] if hot else t["ink3"], anchor="middle"))
    return "".join(out)


CARDS = [
    dict(key="legalgpt", icon="scale", kicker="FINAL-YEAR PROJECT · TEAM OF 4", repo="MAJOR-PROJECT",
         title="LegalGPT Nepal", metric=("12B", "parameters"),
         desc="RAG legal advisor for the Constitution and laws of Nepal: a QLoRA-tuned Mistral Nemo 12B, pgvector "
              "retrieval, FastAPI WebSocket streaming and cited answers. I led legal data collection, testing and docs.",
         tags=["Mistral Nemo", "QLoRA", "pgvector", "FastAPI", "React"]),
    dict(key="landcover", icon="satellite", kicker="RESEARCH · PUBLISHED IN JoEIS", repo="project_on_img_seg_using_unet_archi",
         title="Land-cover segmentation", metric=("0.674", "mean IoU"),
         desc="A U-Net designed from scratch with a custom focal-Tversky + weighted cross-entropy loss for 7-class "
              "land-cover maps of DeepGlobe satellite imagery, plus a Streamlit app for inference.",
         tags=["TensorFlow", "U-Net", "Albumentations", "Streamlit"]),
    dict(key="agents", icon="workflow", kicker="AGENTIC AI", repo="Agentic-AI",
         title="Agentic Nexus", metric=("5", "agents"),
         desc="Multi-agent orchestration on LangGraph: a mood-aware router hands each turn to specialised agents for "
              "memory (RAG over FAISS), writing, planning and safety review, with state shared across the conversation.",
         tags=["LangGraph", "LangChain", "FAISS", "Llama 3.3", "Streamlit"]),
    dict(key="mlops", icon="gauge", kicker="MLOPS · DATATALKS ZOOMCAMP", repo="MLOOPS_NYC-taxi-duration-prediction",
         title="NYC taxi trip duration", metric=None,
         desc="Trip-duration prediction on NYC green-taxi data with MLflow experiment tracking and model logging, "
              "Hyperopt search over XGBoost, and versioned preprocessing artifacts.",
         tags=["MLflow", "Hyperopt", "XGBoost", "scikit-learn", "pandas"]),
]


def card(t, theme, c):
    W, H = 600, 330
    body = [rect(0.5, 0.5, W - 1, H - 1, 18, t["surface"], t["line"])]
    body.append(rect(28, 28, 46, 46, 12, t["brand_tint"]))
    body.append(ui_icon(c["icon"], 39, 39, 24, t["brand_text"], 1.9))
    body.append(text(90, 46, c["kicker"], "m5", 11.5, t["ink3"], tracking=1.6))
    body.append(ui_icon("folder-git-2", 90, 56.5, 14, t["ink3"], 2))
    body.append(text(110, 68, c["repo"], "m4", 12.5, t["ink2"]))
    body.append(ui_icon("arrow-up-right", W - 46, 30, 18, t["ink3"], 2.2))
    body.append(text(26, 132, c["title"], "s7", 27, t["ink1"], tracking=-0.6))
    if c["metric"]:
        v, l = c["metric"]
        body.append(text(W - 28, 128, v, "s7", 27, t["ink1"], anchor="end", tracking=-0.6))
        body.append(text(W - 28, 147, l, "m4", 11.5, t["ink3"], anchor="end"))
    for i, line in enumerate(wrap(c["desc"], "s4", 16, W - 56)[:4]):
        body.append(text(28, 172 + i * 24, line, "s4", 16, t["ink2"]))
    x = 28
    for tag in c["tags"]:
        p, w = pill(x, 276, tag, t, cls="m5", size=12, h=26, pad=11)
        body.append(p)
        x += w + 7
    return document(W, H, "".join(body), title=c["title"], desc=f'{c["kicker"].title()}. {c["desc"]}')


# ── Journey ───────────────────────────────────────────────────────────────────

JOURNEY = [
    ("DEC 2024", "First neural net", "MNIST digit recognition", "build"),
    ("FEB 2025", "Deep learning series", "perceptron to CNNs, in public", "build"),
    ("MAY 2025", "ANN Intern · Planto AI", "deep learning for predictive models", "work"),
    ("JUN 2025", "U-Net land cover", "0.674 mIoU, later published", "work"),
    ("AUG 2025", "AI/ML Mentor · Sayapatri", "100+ students, 45-hour bootcamp", "work"),
    ("OCT 2025", "MLOps", "MLflow · Hyperopt · XGBoost", "build"),
    ("JAN 2026", "Nepal Legal Mistral 7B", "LoRA fine-tune, community GGUF", "build"),
    ("MAR 2026", "LegalGPT Nepal", "final-year team project", "build"),
    ("SEP 2026", "Nepal Law AI goes live", "web app on hybrid RAG", "build"),
]


def journey(t, theme):
    W, H, y0 = 1200, 352, 172
    n = len(JOURNEY)
    xs = [84 + i * (W - 168) / (n - 1) for i in range(n)]
    defs = (f'<linearGradient id="prog" gradientUnits="userSpaceOnUse" x1="{fmt(xs[0])}" x2="{fmt(xs[-1])}" y1="0" y2="0">'
            f'<stop offset="0" stop-color="{t["brand"]}"/>'
            f'<stop offset="1" stop-color="{t["accent"]}"/></linearGradient>')
    body = [f'<path d="M40 {y0} H{W - 40}" stroke="{t["line2"]}" stroke-width="1.5"/>',
            f'<path class="draw" d="M{fmt(xs[0])} {y0} H{fmt(xs[-1])}" pathLength="100" stroke="url(#prog)" stroke-width="3" '
            f'stroke-linecap="round" fill="none"/>']
    for i, (date, title, detail, kind) in enumerate(JOURNEY):
        x, up = xs[i], i % 2 == 0
        ty = 64 if up else 252
        stem = f'<path d="M{fmt(x)} {fmt(y0 - 12 if up else y0 + 12)} V{fmt(ty + 54 if up else ty - 22)}" stroke="{t["line2"]}"/>'
        color = t["brand"] if kind == "build" else t["accent"]
        if kind == "build":
            mark = (f'<circle cx="{fmt(x)}" cy="{y0}" r="8" fill="{t["surface"]}" stroke="{color}" stroke-width="2.5"/>'
                    f'<circle cx="{fmt(x)}" cy="{y0}" r="3" fill="{color}"/>')
        else:
            mark = (f'<rect x="{fmt(x - 7)}" y="{y0 - 7}" width="14" height="14" rx="2" transform="rotate(45 {fmt(x)} {y0})" '
                    f'fill="{t["surface"]}" stroke="{color}" stroke-width="2.5"/>'
                    f'<rect x="{fmt(x - 2.6)}" y="{y0 - 2.6}" width="5.2" height="5.2" transform="rotate(45 {fmt(x)} {y0})" fill="{color}"/>')
        if i == n - 1:
            mark = f'<circle class="ring" cx="{fmt(x)}" cy="{y0}" r="13" fill="none" stroke="{color}" stroke-width="1.5"/>' + mark
        half = max(text_width(date, "m5", 12, 1.6), text_width(title, "s6", 16), text_width(detail, "s4", 13.5)) / 2
        lx = min(max(x, half + 4), W - half - 4)
        label = (text(lx, ty, date, "m5", 12, t["ink3"], anchor="middle", tracking=1.6)
                 + text(lx, ty + 25, title, "s6", 16, t["ink1"], anchor="middle")
                 + text(lx, ty + 46, detail, "s4", 13.5, t["ink2"], anchor="middle"))
        body.append(f'<g class="fade" {delay(.25 + i * .2)}>{stem}{label}{mark}</g>')
    lx = 40
    body.append(f'<circle cx="{lx + 6}" cy="{H - 16}" r="5" fill="{t["surface"]}" stroke="{t["brand"]}" stroke-width="2.2"/>')
    body.append(text(lx + 18, H - 11.5, "Build", "s5", 13, t["ink2"]))
    lx += 18 + text_width("Build", "s5", 13) + 22
    body.append(f'<rect x="{lx + 1.5}" y="{H - 20.5}" width="9" height="9" rx="1.5" transform="rotate(45 {lx + 6} {H - 16})" '
                f'fill="{t["surface"]}" stroke="{t["accent"]}" stroke-width="2.2"/>')
    body.append(text(lx + 18, H - 11.5, "Work & research", "s5", 13, t["ink2"]))
    css = (
        ".draw{stroke-dasharray:100;animation:draw 2.6s cubic-bezier(.4,0,.2,1) both}@keyframes draw{from{stroke-dashoffset:100}to{stroke-dashoffset:0}}"
        ".ring{transform-box:fill-box;transform-origin:center;animation:ring 2.4s ease-out infinite}"
        "@keyframes ring{0%{transform:scale(.6);opacity:.9}100%{transform:scale(1.7);opacity:0}}"
    )
    return document(
        W, H, "".join(body), defs=defs, css=css, title="Journey",
        desc="; ".join(f"{d.title()}: {ti} — {de}" for d, ti, de, _ in JOURNEY),
    )


# ── Toolkit ───────────────────────────────────────────────────────────────────

TOOLKIT = [
    ("LLMs & generative AI", [("huggingface", "Hugging Face"), ("ui:sparkles", "LoRA / QLoRA"), ("mistralai", "Mistral"),
                              ("langchain", "LangChain"), ("langgraph", "LangGraph"), ("ollama", "Ollama"),
                              ("ui:search", "FAISS · BM25")]),
    ("Deep learning & vision", [("pytorch", "PyTorch"), ("tensorflow", "TensorFlow"), ("keras", "Keras"),
                                ("opencv", "OpenCV"), ("ultralytics", "YOLO"), ("scikitlearn", "scikit-learn"),
                                ("jupyter", "Jupyter")]),
    ("MLOps & backend", [("mlflow", "MLflow"), ("optuna", "Optuna"), ("docker", "Docker"), ("fastapi", "FastAPI"),
                         ("postgresql", "PostgreSQL · pgvector"), ("streamlit", "Streamlit"), ("cloudflare", "Cloudflare Tunnel")]),
    ("Apps & languages", [("python", "Python"), ("typescript", "TypeScript"), ("react", "React"), ("nextdotjs", "Next.js"),
                          ("expo", "Expo · React Native"), ("supabase", "Supabase"), ("tailwindcss", "Tailwind CSS")]),
]


def toolkit(t, theme):
    W, gap, row = 1200, 16, 38
    cw = (W - gap * 3) / 4
    H = 74 + row * max(len(items) for _, items in TOOLKIT) + 16
    body = []
    for ci, (group, items) in enumerate(TOOLKIT):
        x = ci * (cw + gap)
        body.append(f'<g class="fade" {delay(.1 + ci * .12)}>')
        body.append(rect(x + .5, .5, cw - 1, H - 1, 16, t["surface"], t["line"]))
        body.append(rect(x + 22, 30, 4, 14, 2, t["brand"]))
        body.append(text(x + 34, 42, group.upper(), "m5", 11.5, t["ink2"], tracking=1.5))
        for i, (icon, label) in enumerate(items):
            y = 74 + i * row
            tile = rect(x + 20, y, 28, 28, 8, t["surface2"], t["line"])
            if icon.startswith("ui:"):
                glyph = ui_icon(icon[3:], x + 25, y + 5, 18, t["brand_text"], 2)
            else:
                glyph = brand_icon(icon, x + 25, y + 5, 18, brand_color(icon, t, t["surface2"]))
            body.append(tile + glyph + text(x + 60, y + 19.5, label, "s5", 15, t["ink1"]))
        body.append("</g>")
    return document(
        W, H, "".join(body), title="Toolkit",
        desc=" · ".join(f"{g}: {', '.join(l for _, l in items)}" for g, items in TOOLKIT),
    )


# ── Footer & buttons ──────────────────────────────────────────────────────────

def footer(t, theme):
    W, H = 1200, 260
    ranges = [
        ("mtn_far", [(150, 200, .55), (420, 186, .7), (640, 160, 1.0), (668, 168, 1.2), (900, 190, .6), (1100, 176, .7)],
         240, 7, 41, "snow"),
        ("mtn_mid", [(60, 222, .5), (330, 214, .6), (560, 206, .6), (820, 214, .55), (1080, 206, .6)], 250, 5, 43, "snow"),
        ("mtn_near", [(140, 240, .2), (520, 244, .18), (900, 238, .2), (1180, 242, .22)], 266, 3, 47, "round"),
    ]
    defs, body, css = sky_and_landscape(
        t, theme, W, H, seed=19, ranges=ranges, orb=(1090, 58, 16), star_box=(0, 0, W, 200),
        avoid=[(240, 30, 960, 170), (1050, 20, 1130, 100)],
    )
    content = (
        text(W / 2, 74, "Thanks for stopping by.", "s7", 32, t["ink1"], anchor="middle", tracking=-0.8)
        + text(W / 2, 106, "Open to AI research, data science and ML engineering roles, and research collaborations.",
               "s4", 16.5, t["ink2"], anchor="middle")
    )
    label = "YAMRAJKHADKA.COM.NP  ·  KATHMANDU, NEPAL"
    lw = text_width(label, "m5", 12, 1.8)
    fx = W / 2 - (lw + 22) / 2
    content += nepal_flag(fx, 126, 16) + text(fx + 22, 138.5, label, "m5", 12, t["ink3"], tracking=1.8)
    return document(W, H, body + f'<g class="fade" {delay(.1)}>{content}</g>', defs=defs, css=css,
                    title="Thanks for stopping by",
                    desc="Open to AI research, data science and ML engineering roles, and research collaborations. "
                         "yamrajkhadka.com.np · Kathmandu, Nepal.")


BUTTONS = [
    ("website", "Website", "yamrajkhadka.com.np"),
    ("linkedin", "LinkedIn", "LinkedIn"),
    ("huggingface", "Hugging Face", "Hugging Face"),
    ("app", "Nepal Law AI (live)", "Nepal Law AI"),
]


def button(t, theme, key, label):
    H, pad, icon = 52, 20, 22
    live = key == "app"
    lw = text_width(label, "s6", 16.5)
    W = math.ceil(pad + icon + 11 + lw + 12 + (50 if live else 0) + 14 + pad)
    body = [rect(0.5, 0.5, W - 1, H - 1, 25.5, t["surface"], t["line2"])]
    ix, iy = pad, (H - icon) / 2
    if key == "website":
        body.append(ui_icon("globe", ix, iy, icon, t["brand_text"], 2))
    elif key == "linkedin":
        body.append(linkedin_icon(ix, iy, icon, "#0a66c2" if theme == "light" else "#4d9de0", t["surface"]))
    elif key == "huggingface":
        body.append(brand_icon("huggingface", ix, iy, icon, "#ffd21e" if theme == "dark" else "#e0a800"))
    else:
        body.append(ui_icon("scale", ix, iy, icon, t["brand_text"], 2))
    x = ix + icon + 11
    body.append(text(x, 32, label, "s6", 16.5, t["ink1"]))
    x += lw + 12
    if live:
        body.append(rect(x, 16, 40, 20, 10, t["brand_tint"]))
        body.append(text(x + 20, 30, "LIVE", "m7", 10.5, t["brand_text"], anchor="middle", tracking=1.2))
        x += 48
    body.append(ui_icon("arrow-up-right", W - pad - 14, (H - 14) / 2, 14, t["ink3"], 2.4))
    return document(W, H, "".join(body), title=label)


# ── README ────────────────────────────────────────────────────────────────────

def picture(name, alt, *, width=None, height=None, branch="main", folder="assets/"):
    size = f' width="{width}"' if width else ""
    size += f' height="{height}"' if height else ""
    base = f"{RAW}/{branch}/{folder}{name}"
    return (
        f'<picture><source media="(prefers-color-scheme: dark)" srcset="{base}-dark.svg">'
        f'<source media="(prefers-color-scheme: light)" srcset="{base}-light.svg">'
        f'<img alt="{esc(alt)}" src="{base}-dark.svg"{size}></picture>'
    )


MORE = [
    ("LeNet-5 on MNIST", "MNIST-digit-classifier-using_LNET", "LeNet-5 CNN in TensorFlow/Keras, 99.55% test accuracy"),
    ("RNN · GRU · LSTM · BiRNN from scratch", "implementation_of_rnn-gru-lstm-brnn_from_scratch", "recurrent cells in PyTorch"),
    ("U-Net from scratch", "Implementation_of_unet_architecture_from_scratch", "the encoder–decoder in Keras"),
    ("LexNepal AI", "NEPAL_LAW-RAG", "Streamlit legal assistant with cross-encoder reranking"),
    ("Nepal Law AI web", "nepallaw", "Next.js + Supabase client for the legal assistant"),
    ("Nepal Law mobile", "MOBILE_APP-NEPAL-LAW", "Expo / React Native app with Google sign-in"),
    ("Meta Lead Ads live feed", "Meta-Lead-ADS---React-Native-Live-Feed-APP", "webhooks → Socket.io → React Native"),
    ("Fake news detection", "Fake-News-Detection-", "TF-IDF with logistic regression, decision tree, random forest"),
    ("Fashion-MNIST classifier", "Fashain-Mnist-Classifier", "L2-regularised network in TensorFlow"),
    ("Deep learning journey", "DeepLearning", "day-by-day notes, from the perceptron to CNNs"),
]


def readme() -> str:
    def section(key):
        num, title, _ = SECTIONS[key]
        return picture(f"h-{key}", f"{num} — {title}", width="100%")

    cards = {c["key"]: c for c in CARDS}

    def card_link(key):
        c = cards[key]
        return f'<a href="{GH}/{c["repo"]}">{picture(f"card-{key}", c["title"] + " — " + c["desc"], width="49%")}</a>'

    buttons = "\n  ".join(
        f'<a href="{LINKS[key]}">{picture(f"btn-{key}", alt, height="46")}</a>' for key, alt, _ in BUTTONS
    )
    more = "\n".join(f'| [**{n}**]({GH}/{r}) | {d} |' for n, r, d in MORE)
    return f"""<!-- Generated by scripts/build_assets.py. Edit the script, run it, and commit the result. -->
<div align="center">

{picture("hero", "Yamraj Khadka — Computer Engineer · AI/ML Engineer & Researcher. Kathmandu, Nepal.", width="100%")}

<p>
  {buttons}
</p>

{section("about")}

{picture("about", "whoami: Yamraj Khadka, Computer Engineer and AI/ML Engineer & Researcher from IOE Purwanchal Campus, Kathmandu, Nepal. I build AI systems end to end, from research and fine-tuned LLMs to production pipelines. Focus: LLMs, RAG pipelines, agentic AI, computer vision, MLOps. Open to AI research, data science and ML engineering roles, and research collaborations.", width="100%")}

{picture("highlights", "Highlights: 7B legal LLM shipped · 0.674 U-Net mean IoU (published in JoEIS Vol. 5) · 5,849 legal provisions indexed · 100+ students mentored", width="100%")}

{section("work")}

<a href="{LINKS["app"]}">{picture("flagship", "Nepal Legal AI — Mistral 7B fine-tuned with LoRA on Nepali law, grounded by hybrid retrieval (FAISS + BM25, RRF, cross-encoder rerank) over 5,849 provisions from 6 laws.", width="100%")}</a>

<sub><a href="{LINKS["app"]}"><b>Live app</b></a> &nbsp;·&nbsp; <a href="{LINKS["model"]}">Model on Hugging Face</a> &nbsp;·&nbsp; <a href="{LINKS["space"]}">GGUF + RAG Space</a> &nbsp;·&nbsp; <a href="{GH}/RAG-NEPAL_LAW">Hybrid retriever</a> &nbsp;·&nbsp; <a href="{GH}/nepallaw">Web client</a> &nbsp;·&nbsp; <a href="{GH}/MOBILE_APP-NEPAL-LAW">Mobile app</a></sub>

<br><br>

{card_link("legalgpt")}
{card_link("landcover")}
{card_link("agents")}
{card_link("mlops")}

<sub>📄 <a href="{LINKS["paper"]}"><b>Land Cover Segmentation from Satellite Imagery Using U-Net with Custom Loss</b></a> — Journal of Engineering Issues and Solutions (JoEIS), Vol. 5</sub>

</div>

<details>
<summary><b>More builds</b></summary>
<br>

| Project | What it is |
| :-- | :-- |
{more}

</details>

<div align="center">

{section("journey")}

{picture("journey", "Journey: " + "; ".join(f"{d.title()} — {ti}: {de}" for d, ti, de, _ in JOURNEY), width="100%")}

{section("toolkit")}

{picture("toolkit", "Toolkit — " + " · ".join(f"{g}: {', '.join(l for _, l in items)}" for g, items in TOOLKIT), width="100%")}

{section("telemetry")}

{picture("stats", "GitHub activity: contributions, streaks, weekly activity and languages, refreshed daily by a GitHub Action.", width="100%", branch="output", folder="")}

{picture("snake", "A snake eating the contribution graph", width="100%", branch="output", folder="")}

{picture("footer", "Thanks for stopping by. Open to AI research, data science and ML engineering roles, and research collaborations.", width="100%")}

</div>
"""


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    ASSETS.mkdir(exist_ok=True)
    jobs = {"hero": hero, "about": about, "highlights": highlights, "flagship": flagship, "journey": journey,
            "toolkit": toolkit, "footer": footer}
    for key in SECTIONS:
        jobs[f"h-{key}"] = lambda t, th, key=key: header(t, th, key)
    for c in CARDS:
        jobs[f"card-{c['key']}"] = lambda t, th, c=c: card(t, th, c)
    for key, _, label in BUTTONS:
        jobs[f"btn-{key}"] = lambda t, th, key=key, label=label: button(t, th, key, label)
    for name, render in jobs.items():
        for theme, palette in THEMES.items():
            (ASSETS / f"{name}-{theme}.svg").write_text(render(palette, theme), encoding="utf-8")
    (ROOT / "README.md").write_text(readme(), encoding="utf-8")
    print(f"wrote {len(jobs) * 2} SVGs and README.md")


if __name__ == "__main__":
    main()
