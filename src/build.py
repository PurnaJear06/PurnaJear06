"""Builds every SVG in ../assets for the profile README.

Each asset is rendered twice (dark + light) and embeds subsetted copies of
Martian Mono (display) and IBM Plex Mono (body), both SIL OFL, so the type
looks identical on every machine. Requires fontTools + brotli.

    python src/build.py
"""
from __future__ import annotations

import base64
import io
import os
import random
from pathlib import Path
from xml.sax.saxutils import escape

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets"
FONT_DIR = Path(os.environ.get("FONT_DIR", Path.home() / "Library/Fonts"))

THEMES = {
    "dark": dict(
        panel="#0d1218", band="#10161e", line="#222b36", line2="#2c3744",
        text="#e6edf3", muted="#8b96a3", dim="#4a5462", grid="#1c2430",
        mint="#3ddc97", amber="#ffb547", red="#ff6b6b", violet="#a78bfa",
        on_mint="#06140d",
    ),
    "light": dict(
        panel="#ffffff", band="#f6f8fa", line="#d8dee4", line2="#c3ccd5",
        text="#1f2328", muted="#59636e", dim="#a2acb7", grid="#e6eaef",
        mint="#0b8457", amber="#b25e00", red="#cf222e", violet="#6e4ad8",
        on_mint="#ffffff",
    ),
}

GLYPHS = "".join(chr(c) for c in range(32, 127)) + "·→—–…×≤≥─│├└▸•✓"


# ---------------------------------------------------------------- fonts ----

def _woff2(font: TTFont) -> str:
    opts = subset.Options()
    opts.flavor = "woff2"
    opts.layout_features = ["kern", "liga", "calt"]
    opts.name_IDs = []
    sub = subset.Subsetter(opts)
    sub.populate(text=GLYPHS)
    sub.subset(font)
    buf = io.BytesIO()
    font.flavor = "woff2"
    font.save(buf)
    return base64.b64encode(buf.getvalue()).decode()


def _load_fonts():
    martian = TTFont(FONT_DIR / "MartianMono[wdth,wght].ttf")
    martian = instancer.instantiateVariableFont(martian, {"wght": 700, "wdth": 100})
    adv = martian["hmtx"]["a"][0] / martian["head"].unitsPerEm
    plex = TTFont(FONT_DIR / "IBMPlexMono-Medium.ttf")
    return _woff2(martian), _woff2(plex), adv


DISPLAY_B64, BODY_B64, DISPLAY_ADV = _load_fonts()
BODY_ADV = 0.6
FONT_CSS = (
    "@font-face{font-family:PJD;src:url(data:font/woff2;base64,%s) format('woff2')}"
    "@font-face{font-family:PJB;src:url(data:font/woff2;base64,%s) format('woff2')}"
    ".d{font-family:PJD,'Martian Mono',ui-monospace,Menlo,Consolas,monospace;font-weight:700}"
    ".b{font-family:PJB,'IBM Plex Mono',ui-monospace,Menlo,Consolas,monospace;font-weight:500}"
) % (DISPLAY_B64, BODY_B64)


# -------------------------------------------------------------- helpers ----

def svg(w, h, body, title):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img" aria-label="{escape(title)}">'
        f"<title>{escape(title)}</title><style>{FONT_CSS}</style>{body}</svg>"
    )


def width(s, size, display=False):
    return len(s) * size * (DISPLAY_ADV if display else BODY_ADV)


def text(x, y, s, size, fill, display=False, anchor="start", ls=0, op=None, fit=True, extra=""):
    attrs = f'x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" text-anchor="{anchor}"'
    if ls:
        attrs += f' letter-spacing="{ls}"'
    elif fit and s.strip():
        # Pins the run to the embedded font's exact advance, so a fallback
        # font can never overflow or desync a typing clip.
        attrs += f' textLength="{width(s, size, display):.1f}" lengthAdjust="spacingAndGlyphs"'
    if op is not None:
        attrs += f' opacity="{op}"'
    cls = "d" if display else "b"
    return f'<text class="{cls}" {attrs} {extra}>{escape(s)}</text>'


def fade_in(begin, dur=0.35, rise=6):
    """Opacity + small rise, frozen at the end."""
    out = f'<animate attributeName="opacity" from="0" to="1" begin="{begin:.2f}s" dur="{dur}s" fill="freeze"/>'
    if rise:
        out += (
            f'<animateTransform attributeName="transform" type="translate" from="0 {rise}" to="0 0" '
            f'begin="{begin:.2f}s" dur="{dur}s" fill="freeze" calcMode="spline" keySplines=".2 .7 .3 1" keyTimes="0;1"/>'
        )
    return out


def dot_grid(pid, color, step=18, r=1):
    return (
        f'<pattern id="{pid}" width="{step}" height="{step}" patternUnits="userSpaceOnUse">'
        f'<circle cx="{step/2}" cy="{step/2}" r="{r}" fill="{color}"/></pattern>'
    )


def pulse_dot(cx, cy, color, r=4, dur=1.8):
    return (
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{color}"/>'
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{color}" stroke-width="1.5">'
        f'<animate attributeName="r" values="{r};{r*3}" dur="{dur}s" repeatCount="indefinite"/>'
        f'<animate attributeName="opacity" values=".8;0" dur="{dur}s" repeatCount="indefinite"/></circle>'
    )


def packet(path_id, color, dur, begin, r=3):
    return (
        f'<circle r="{r}" fill="{color}" opacity="0">'
        f'<animateMotion dur="{dur}s" begin="{begin}s" repeatCount="indefinite" rotate="auto"><mpath href="#{path_id}"/></animateMotion>'
        f'<animate attributeName="opacity" values="0;1;1;0" keyTimes="0;.1;.85;1" dur="{dur}s" begin="{begin}s" repeatCount="indefinite"/>'
        f"</circle>"
    )


# ----------------------------------------------------------------- hero ----

def hero(t):
    W, H = 1200, 470
    p = []
    p.append(f'<defs>{dot_grid("hg", t["grid"])}'
             f'<clipPath id="win"><rect x="1" y="1" width="{W-2}" height="{H-2}" rx="14"/></clipPath>'
             f'<filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="4"/></filter></defs>')
    p.append(f'<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="14" fill="{t["panel"]}" stroke="{t["line"]}"/>')
    p.append('<g clip-path="url(#win)">')

    # title bar
    p.append(f'<rect x="0" y="0" width="{W}" height="42" fill="{t["band"]}"/>'
             f'<line x1="0" y1="42" x2="{W}" y2="42" stroke="{t["line"]}"/>')
    for i, c in enumerate((t["red"], t["amber"], t["mint"])):
        p.append(f'<circle cx="{26 + i*20}" cy="21" r="5.5" fill="{c}" opacity=".85"/>')
    p.append(text(W/2, 26, "purna@relay: ~/ops  —  shift 3 of 3", 12.5, t["muted"], anchor="middle"))
    p.append(pulse_dot(W-74, 21, t["mint"], r=3.5))
    p.append(text(W-62, 25.5, "LIVE", 11.5, t["mint"], ls=2))

    # right: context graph panel
    gx, gy, gw, gh = 660, 64, 516, 330
    p.append(f'<rect x="{gx}" y="{gy}" width="{gw}" height="{gh}" rx="10" fill="url(#hg)" stroke="{t["line"]}" stroke-dasharray="3 5"/>')
    p.append(text(gx+16, gy+24, "// relay · context graph", 12, t["dim"]))

    sources = ["telemetry", "servicenow", "slack", "bridge calls", "past incidents"]
    sx, sw = gx + 24, 150
    rag = (gx + 300, gy + 178)
    agent = (gx + 430, gy + 178)
    paths, nodes = [], []
    for i, s in enumerate(sources):
        y = gy + 70 + i * 50
        nodes.append(
            f'<g opacity="0">{fade_in(0.25 + i*0.08, rise=0)}'
            f'<rect x="{sx}" y="{y-14}" width="{sw}" height="28" rx="14" fill="{t["panel"]}" stroke="{t["line2"]}"/>'
            f'<circle cx="{sx+16}" cy="{y}" r="3.5" fill="{t["mint"]}"/>'
            + text(sx+30, y+4.5, s, 13, t["text"]) + "</g>")
        x0 = sx + sw
        pid = f"hp{i}"
        paths.append(f'<path id="{pid}" d="M{x0},{y} C{x0+70},{y} {rag[0]-90},{rag[1]} {rag[0]-30},{rag[1]}" '
                     f'fill="none" stroke="{t["line2"]}" stroke-width="1.5"/>')
        paths.append(packet(pid, t["mint"], 2.6, round(0.6 + i*0.45, 2)))
    paths.append(f'<path id="hpa" d="M{rag[0]+30},{rag[1]} L{agent[0]-34},{agent[1]}" stroke="{t["line2"]}" stroke-width="1.5"/>')
    paths.append(packet("hpa", t["amber"], 1.4, 0.9))
    paths.append(packet("hpa", t["amber"], 1.4, 1.6))
    op_y = gy + gh - 40
    paths.append(f'<path id="hpo" d="M{agent[0]},{agent[1]+34} L{agent[0]},{op_y-14}" stroke="{t["line2"]}" stroke-width="1.5"/>')
    paths.append(packet("hpo", t["mint"], 1.2, 1.2))
    p += paths + nodes

    # rag node
    p.append(f'<circle cx="{rag[0]}" cy="{rag[1]}" r="30" fill="{t["mint"]}" opacity=".18" filter="url(#glow)"/>')
    p.append(f'<circle cx="{rag[0]}" cy="{rag[1]}" r="30" fill="{t["panel"]}" stroke="{t["mint"]}" stroke-width="1.5"/>')
    p.append(f'<circle cx="{rag[0]}" cy="{rag[1]}" r="30" fill="none" stroke="{t["mint"]}">'
             '<animate attributeName="r" values="30;48" dur="2.4s" repeatCount="indefinite"/>'
             '<animate attributeName="opacity" values=".6;0" dur="2.4s" repeatCount="indefinite"/></circle>')
    p.append(text(rag[0], rag[1]+5, "RAG", 14, t["mint"], display=True, anchor="middle"))
    p.append(text(rag[0], rag[1]+52, "retrieve", 11.5, t["muted"], anchor="middle"))
    # agent node
    p.append(f'<circle cx="{agent[0]}" cy="{agent[1]}" r="34" fill="{t["amber"]}" opacity=".16" filter="url(#glow)"/>')
    p.append(f'<circle cx="{agent[0]}" cy="{agent[1]}" r="28" fill="{t["panel"]}" stroke="{t["amber"]}" stroke-width="1.5"/>')
    p.append(f'<circle cx="{agent[0]}" cy="{agent[1]}" r="36" fill="none" stroke="{t["amber"]}" stroke-dasharray="4 7" opacity=".8">'
             f'<animateTransform attributeName="transform" type="rotate" from="0 {agent[0]} {agent[1]}" to="360 {agent[0]} {agent[1]}" dur="14s" repeatCount="indefinite"/></circle>')
    p.append(text(agent[0], agent[1]+5, "agent", 13, t["amber"], display=True, anchor="middle"))
    # operator node
    ow = 168
    p.append(f'<rect x="{agent[0]-ow/2}" y="{op_y-14}" width="{ow}" height="28" rx="6" fill="{t["panel"]}" stroke="{t["mint"]}"/>')
    p.append(text(agent[0], op_y+4.5, "→ operator answer", 12.5, t["text"], anchor="middle"))

    # left: terminal
    x0, lh = 40, 32
    y = 92
    cps = 26  # typing speed, chars/sec
    clock = 0.5
    ids = iter(range(100))

    def prompt_cmd(y, cmd, begin):
        i = next(ids)
        pr = "~ $"
        pw = width(pr + " ", 16)
        n = len(cmd)
        cw = 16 * BODY_ADV
        d = n / cps
        vals = ";".join(f"{k*cw:.1f}" for k in range(n + 1))
        keys = ";".join(f"{k/n:.4f}" for k in range(n + 1))
        out = [f'<g opacity="0">{fade_in(begin, .15, 0)}{text(x0, y, pr, 16, t["mint"])}</g>']
        out.append(f'<clipPath id="tc{i}"><rect x="{x0+pw}" y="{y-16}" width="0" height="24">'
                   f'<animate attributeName="width" values="{vals}" keyTimes="{keys}" calcMode="discrete" begin="{begin+.15:.2f}s" dur="{d:.2f}s" fill="freeze"/></rect></clipPath>')
        out.append(f'<g clip-path="url(#tc{i})">{text(x0+pw, y, cmd, 16, t["text"])}</g>')
        out.append(f'<rect x="{x0+pw}" y="{y-14}" width="9" height="18" fill="{t["mint"]}" opacity="0">'
                   f'<set attributeName="opacity" to="1" begin="{begin+.15:.2f}s"/>'
                   f'<animate attributeName="x" values="{";".join(f"{x0+pw+k*cw:.1f}" for k in range(n+1))}" keyTimes="{keys}" calcMode="discrete" begin="{begin+.15:.2f}s" dur="{d:.2f}s" fill="freeze"/>'
                   f'<set attributeName="opacity" to="0" begin="{begin+.15+d+.25:.2f}s"/></rect>')
        return "".join(out), begin + .15 + d + .3

    s, clock = prompt_cmd(y, "whoami", clock)
    p.append(s)
    y += 56
    p.append(f'<g opacity="0">{fade_in(clock)}{text(x0, y, "Purna Jear Swami", 38, t["text"], display=True)}</g>')
    y += 34
    p.append(f'<g opacity="0">{fade_in(clock+.15)}'
             + text(x0, y, "Applied AI Engineer", 16, t["mint"])
             + text(x0 + width("Applied AI Engineer ", 16), y, "· Genpact · Hyderabad, IN", 16, t["muted"])
             + "</g>")
    clock += .7
    y += 48
    s, clock = prompt_cmd(y, "cat principles.txt", clock)
    p.append(s)
    y += lh
    words = [("models interpret.", t["text"]), ("code calculates.", t["text"]), ("humans approve.", t["amber"])]
    xx = x0
    for k, (wd, col) in enumerate(words):
        p.append(f'<g opacity="0">{fade_in(clock + k*.35, rise=4)}{text(xx, y, wd, 16, col)}</g>')
        xx += width(wd + " ", 16)
    clock += 1.4
    y += 48
    s, clock = prompt_cmd(y, "relay --status", clock)
    p.append(s)
    y += lh
    xx = x0
    for k, src in enumerate(["telemetry", "tickets", "slack", "history"]):
        b = clock + k * .22
        p.append(f'<g opacity="0">{fade_in(b, .2, 0)}'
                 + text(xx, y, "[", 16, t["dim"]) + text(xx + width("[", 16), y, "ok", 16, t["mint"])
                 + text(xx + width("[ok", 16), y, "]", 16, t["dim"])
                 + text(xx + width("[ok] ", 16), y, src, 16, t["muted"]) + "</g>")
        xx += width(f"[ok] {src}  ", 16)
    clock += 4 * .22 + .2
    y += lh
    p.append(f'<g opacity="0">{fade_in(clock, .3, 0)}'
             + text(x0, y, "→ context ready · handover drafted for next shift", 16, t["text"]) + "</g>")
    clock += .6
    y += 48
    p.append(f'<g opacity="0">{fade_in(clock, .15, 0)}{text(x0, y, "~ $", 16, t["mint"])}'
             f'<rect x="{x0 + width("~ $ ", 16):.1f}" y="{y-14}" width="9" height="18" fill="{t["mint"]}">'
             '<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;.5;.5;1" dur="1.05s" repeatCount="indefinite"/></rect></g>')

    # tmux-style status bar
    by = H - 34
    p.append(f'<rect x="0" y="{by}" width="{W}" height="34" fill="{t["band"]}"/>'
             f'<line x1="0" y1="{by}" x2="{W}" y2="{by}" stroke="{t["line"]}"/>')
    p.append(f'<rect x="0" y="{by}" width="74" height="34" fill="{t["mint"]}"/>')
    p.append(text(37, by+22, "[ops]", 13, t["on_mint"], anchor="middle"))
    xx = 92
    for k, win in enumerate(["relay*", "tracend", "hireind", "gridwatch", "roster"]):
        s = f"{k}:{win}"
        p.append(text(xx, by+22, s, 13, t["text"] if k == 0 else t["muted"]))
        xx += width(s + "   ", 13)
    right = "claude certified architect  │  IST · 24×7"
    p.append(text(W-20, by+22, right, 13, t["muted"], anchor="end"))
    p.append("</g>")
    return svg(W, H, "".join(p),
               "Purna Jear Swami, Applied AI Engineer at Genpact. Principles: models interpret, code calculates, "
               "humans approve. Animated graph: telemetry, ServiceNow, Slack, bridge calls and past incidents flow "
               "through RAG into an agent that answers the operator.")


# ------------------------------------------------------- section header ----

def section(t, num, label, note):
    W, H = 1200, 64
    p = []
    p.append(text(0, 40, num, 15, t["amber"]))
    p.append(text(width(num + "  ", 15), 40, "/", 15, t["dim"]))
    lx = width(num + "  /  ", 15)
    p.append(text(lx, 41, label, 20, t["text"], display=True))
    end = lx + width(label, 20, True) + 22
    nw = width(note, 13)
    p.append(f'<line x1="{end:.1f}" y1="35" x2="{W-nw-36:.1f}" y2="35" stroke="{t["line2"]}" stroke-dasharray="2 6"/>')
    p.append(text(W-24-nw, 39.5, note, 13, t["muted"]))
    p.append(pulse_dot(W-8, 35, t["mint"], r=3, dur=2.2))
    return svg(W, H, "".join(p), f"{num} {label}: {note}")


# ---------------------------------------------------------------- cards ----

def band_tracend(t):
    pts, x = [], 0
    while x <= 600:
        pts += [(x, 64), (x+40, 64), (x+48, 58), (x+56, 64), (x+66, 64), (x+71, 72), (x+78, 30),
                (x+86, 80), (x+92, 64), (x+110, 64), (x+122, 56), (x+136, 64)]
        x += 150
    d = "M" + " L".join(f"{a},{b}" for a, b in pts if a <= 600)
    return (f'<path id="ecg" d="{d}" fill="none" stroke="{t["mint"]}" stroke-width="1.6" opacity=".9"/>'
            f'<path d="{d}" fill="none" stroke="{t["mint"]}" stroke-width="5" opacity=".18" filter="url(#cg)"/>'
            f'<circle r="4" fill="{t["mint"]}"><animateMotion dur="5s" repeatCount="indefinite"><mpath href="#ecg"/></animateMotion></circle>')


def band_relay(t):
    out, hub, ag = [], (330, 60), (500, 60)
    for i in range(5):
        y = 38 + i * 12
        out.append(f'<path id="rb{i}" d="M40,{y} C170,{y} 220,{hub[1]} {hub[0]-12},{hub[1]}" fill="none" stroke="{t["line2"]}"/>')
        out.append(f'<circle cx="40" cy="{y}" r="3" fill="{t["mint"]}"/>')
        out.append(packet(f"rb{i}", t["mint"], 2.2, round(i*.4, 1), r=2.5))
    out.append(f'<path id="rba" d="M{hub[0]+12},{hub[1]} L{ag[0]-14},{ag[1]}" stroke="{t["line2"]}"/>')
    out.append(packet("rba", t["amber"], 1.3, .3, r=2.5))
    out.append(f'<circle cx="{hub[0]}" cy="{hub[1]}" r="11" fill="{t["band"]}" stroke="{t["mint"]}" stroke-width="1.5"/>')
    out.append(f'<circle cx="{ag[0]}" cy="{ag[1]}" r="13" fill="{t["band"]}" stroke="{t["amber"]}" stroke-width="1.5"/>'
               f'<circle cx="{ag[0]}" cy="{ag[1]}" r="19" fill="none" stroke="{t["amber"]}" stroke-dasharray="3 5">'
               f'<animateTransform attributeName="transform" type="rotate" from="0 {ag[0]} {ag[1]}" to="360 {ag[0]} {ag[1]}" dur="10s" repeatCount="indefinite"/></circle>')
    return "".join(out)


def band_roster(t):
    rnd = random.Random(7)
    out, cols, x0, cw, gap = [], 31, 24, 14.8, 3
    for r in range(3):
        for c in range(cols):
            x, y = x0 + c * (cw + gap), 40 + r * 18
            off = rnd.random() < .18
            col = t["dim"] if off else (t["amber"] if r == 2 else t["mint"])
            op = .25 if off else rnd.choice([.35, .55, .8])
            out.append(f'<rect x="{x:.1f}" y="{y}" width="{cw}" height="13" rx="2.5" fill="{col}" opacity="{op}"/>')
    out.append(f'<rect x="{x0-3}" y="35" width="{cw+6:.1f}" height="60" rx="4" fill="none" stroke="{t["text"]}" stroke-opacity=".55">'
               f'<animate attributeName="x" values="{";".join(f"{x0-3+c*(cw+gap):.1f}" for c in range(cols))}" dur="6.2s" calcMode="discrete" repeatCount="indefinite"/></rect>')
    return "".join(out)


def band_gridwatch(t):
    rnd = random.Random(3)
    pts = []
    for i in range(0, 121):
        x = 20 + i * 4.67
        y = 72 + 6 * __import__("math").sin(i / 5) + rnd.uniform(-3, 3)
        if 84 <= i <= 88:
            y = [62, 44, 30, 50, 68][i - 84]
        pts.append((x, y))
    d = "M" + " L".join(f"{a:.1f},{b:.1f}" for a, b in pts)
    sx, sy = pts[86]
    return (f'<line x1="20" y1="48" x2="580" y2="48" stroke="{t["amber"]}" stroke-dasharray="5 5" opacity=".8"/>'
            f'<path d="{d}" fill="none" stroke="{t["muted"]}" stroke-width="1.5"/>'
            f'<path d="M{pts[83][0]:.1f},{pts[83][1]:.1f} ' + " ".join(f"L{a:.1f},{b:.1f}" for a, b in pts[84:90]) +
            f'" fill="none" stroke="{t["red"]}" stroke-width="2"/>'
            + pulse_dot(round(sx, 1), round(sy, 1), t["red"], r=3.5, dur=1.4))


def band_hireind(t):
    rnd = random.Random(11)
    out = []
    hits = {1, 4, 6}
    for r in range(8):
        y = 38 + (r % 4) * 13
        x = 24 if r < 4 else 312
        w = rnd.randint(130, 250)
        hit = r in hits
        out.append(f'<rect x="{x}" y="{y}" width="{w}" height="6" rx="3" fill="{t["mint"] if hit else t["dim"]}" opacity="{.9 if hit else .45}"/>')
        if hit:
            out.append(f'<circle cx="{x+w+12}" cy="{y+3}" r="3" fill="{t["mint"]}"/>')
    out.append(f'<rect x="20" y="32" width="560" height="2" fill="{t["mint"]}" opacity=".7">'
               '<animate attributeName="y" values="32;88;32" dur="3.6s" repeatCount="indefinite"/></rect>')
    return "".join(out)


def band_classroom(t):
    out = []
    people = [(90, 0), (250, 1), (340, 0), (430, 1), (530, 0)]
    for k, (cx, tracked) in enumerate(people):
        g = [f'<circle cx="{cx}" cy="62" r="8" fill="{t["dim"]}"/>',
             f'<rect x="{cx-14}" y="73" width="28" height="22" rx="8" fill="{t["dim"]}"/>']
        if tracked:
            c = t["mint"] if k == 1 else t["amber"]
            g.append(f'<rect x="{cx-22}" y="49" width="44" height="48" rx="3" fill="none" stroke="{c}" stroke-width="1.5" stroke-dasharray="5 3"/>')
            g.append(f'<rect x="{cx-22}" y="38" width="40" height="12" rx="2" fill="{c}"/>')
            g.append(text(cx-18, 47.5, f"id 0{k+2}", 9.5, t["on_mint"]))
        out.append(f'<g><animateTransform attributeName="transform" type="translate" values="0 0;{3 if k%2 else -3} 0;0 0" dur="{3+k*.4:.1f}s" repeatCount="indefinite"/>{"".join(g)}</g>')
    return "".join(out)


CARDS = [
    dict(key="relay", band=band_relay, status="IN BUILD · GENPACT", sc="amber",
         title="Relay", tag="24×7 AI incident-resolution agent",
         bullets=["correlates telemetry, ServiceNow, Slack + bridge calls",
                  "RAG over past incidents & architecture knowledge",
                  "answers what changed, when, and who handled it"],
         stack="LLM agents · RAG · ServiceNow · New Relic · PagerDuty"),
    dict(key="tracend", band=band_tracend, status="PRIVATE BETA", sc="mint",
         title="Tracend", tag="Evidence-driven AI personal trainer",
         bullets=["Apple HealthKit + 9 Deno edge functions",
                  "5-layer structured memory across coaching sessions",
                  "no plan or meal changes without policy checks + approval"],
         stack="Flutter · Supabase · Deno · Gemini · PostgreSQL"),
    dict(key="hireind", band=band_hireind, status="CLAUDE CODE SKILL", sc="violet",
         title="Hireind", tag="Job-search automation for Indian tech",
         bullets=["scans 30+ Indian portals, scores roles on 5 dimensions",
                  "reframes service-company resumes for product ATS",
                  "INR salary benchmarks + negotiation anchors"],
         stack="Claude Code · Playwright · Node.js"),
    dict(key="gridwatch", band=band_gridwatch, status="REAL-TIME SYSTEM", sc="violet",
         title="GridWatch", tag="Infrastructure anomaly detection",
         bullets=["bulk-ingests up to 1,000 sensor readings per request",
                  "acks ≤200 ms; async threshold + rate-of-change rules",
                  "alert lifecycles + live, zone-isolated operator views"],
         stack="TypeScript · Node.js · PostgreSQL · Redis · React"),
    dict(key="roster", band=band_roster, status="SHIPPED · IN USE", sc="mint",
         title="EOC Roster Optimizer", tag="Constraint-solved rosters for a 24×7 team",
         bullets=["18 people × 3 shifts, solved with OR-Tools CP-SAT",
                  "fair nights/weekends, 2 consecutive offs, ≤6-day streaks",
                  "saves ~4–5 hours of manual scheduling a month"],
         stack="Python · OR-Tools · Excel"),
    dict(key="classroom", band=band_classroom, status="PATENT APP. 202541062540", sc="amber",
         title="Classroom Behavior AI", tag="Real-time classroom computer vision",
         bullets=["detects 14 behaviours with engagement heatmaps",
                  "YOLOv8 + ByteTrack with facial re-identification",
                  "LLM session summaries on an AWS Streamlit dashboard"],
         stack="Python · YOLOv8 · ByteTrack · OpenCV · AWS"),
]


def card(t, c, idx):
    W, H = 600, 330
    p = [f'<defs><clipPath id="cc"><rect x="1" y="1" width="{W-2}" height="{H-2}" rx="12"/></clipPath>'
         f'{dot_grid("cgd", t["grid"], 14, .9)}'
         '<filter id="cg" x="-20%" y="-50%" width="140%" height="200%"><feGaussianBlur stdDeviation="3"/></filter></defs>']
    p.append(f'<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="12" fill="{t["panel"]}" stroke="{t["line"]}"/>')
    p.append('<g clip-path="url(#cc)">')
    p.append(f'<rect x="0" y="0" width="{W}" height="104" fill="{t["band"]}"/><rect x="0" y="0" width="{W}" height="104" fill="url(#cgd)"/>'
             f'<line x1="0" y1="104" x2="{W}" y2="104" stroke="{t["line"]}"/>')
    p.append(c["band"](t))
    sc = t[c["sc"]]
    sw = width(c["status"], 11) + len(c["status"]) * 1.2 + 34
    p.append(f'<rect x="16" y="12" width="{sw:.1f}" height="22" rx="11" fill="{t["panel"]}" stroke="{sc}" stroke-opacity=".7"/>')
    p.append(f'<circle cx="29" cy="23" r="3.5" fill="{sc}"/>')
    p.append(text(40, 27, c["status"], 11, sc, ls=1.2))
    p.append(text(W-20, 28, f"{idx:02d}", 12, t["dim"], anchor="end"))
    p.append("</g>")
    p.append(text(28, 146, c["title"], 24, t["text"], display=True))
    p.append(text(28, 172, c["tag"], 14.5, t["muted"]))
    for k, b in enumerate(c["bullets"]):
        y = 210 + k * 26
        p.append(text(28, y, "→", 14.5, sc) + text(50, y, b, 14.5, t["text"]))
    p.append(f'<line x1="28" y1="285" x2="{W-28}" y2="285" stroke="{t["line"]}" stroke-dasharray="2 5"/>')
    p.append(text(28, 310, c["stack"], 12.5, t["muted"]))
    return svg(W, H, "".join(p), f'{c["title"]}: {c["tag"]}. ' + "; ".join(c["bullets"]) + f'. Stack: {c["stack"]}.')


# ---------------------------------------------------------------- stack ----

STACK = [
    ("applied ai", True, ["LLM integration", "RAG", "agent workflows", "MCP", "LangGraph", "LangChain", "prompt design"]),
    ("languages", False, ["Python", "TypeScript", "SQL", "JavaScript"]),
    ("backend", False, ["Node.js", "Deno edge functions", "PostgreSQL", "Supabase", "REST APIs", "Docker", "CI/CD"]),
    ("cloud & ops", False, ["AWS", "Azure", "ServiceNow", "New Relic", "PagerDuty", "SolarWinds"]),
    ("ml & cv", False, ["Pandas", "NumPy", "scikit-learn", "YOLOv8", "ByteTrack", "OpenCV", "OR-Tools CP-SAT"]),
    ("apps", False, ["Flutter", "Apple HealthKit", "Streamlit", "React"]),
]


def stack(t):
    W = 1200
    rows, y = [], 26
    for label, hot, chips in STACK:
        rows.append(text(0, y + 19, label.upper(), 12, t["amber"] if hot else t["muted"], ls=1.6))
        x = 190
        for ch in chips:
            w = width(ch, 14.5) + 28
            if x + w > W:
                x, y = 190, y + 44
            stroke = t["mint"] if hot else t["line2"]
            fill = t["text"] if hot else t["text"]
            rows.append(f'<rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="30" rx="15" fill="{t["panel"]}" stroke="{stroke}"/>')
            rows.append(text(x + 14, y + 20, ch, 14.5, fill))
            x += w + 10
        rows.append(f'<line x1="0" y1="{y+43}" x2="{W}" y2="{y+43}" stroke="{t["line"]}" stroke-dasharray="2 6"/>')
        y += 56
    H = y - 6
    return svg(W, H, "".join(rows), "Stack. " + ". ".join(f"{l}: {', '.join(c)}" for l, _, c in STACK))


# --------------------------------------------------------------- footer ----

def footer(t):
    W, H = 1200, 96
    p = []
    begin = 0.4
    p.append(text(0, 34, "~ $", 15, t["mint"]) + text(width("~ $ ", 15), 34, "exit", 15, t["text"]))
    msg = "handover saved. thanks for reading — see you next shift."
    p.append(f'<g opacity="0">{fade_in(begin, .5, 4)}{text(0, 66, msg, 15, t["muted"])}</g>')
    p.append(f'<rect x="{width(msg + " ", 15):.1f}" y="52" width="9" height="18" fill="{t["mint"]}" opacity="0">'
             f'<set attributeName="opacity" to="1" begin="{begin+.5}s"/>'
             f'<animate attributeName="fill-opacity" values="1;1;0;0" keyTimes="0;.5;.5;1" dur="1.05s" repeatCount="indefinite"/></rect>')
    return svg(W, H, "".join(p), "exit — handover saved. Thanks for reading, see you next shift.")


# ----------------------------------------------------------------- main ----

SECTIONS = [
    ("now", "01", "NOW", "what i'm working on"),
    ("work", "02", "SELECTED WORK", "things i've shipped & am shipping"),
    ("stack", "03", "STACK", "tools i reach for"),
    ("telemetry", "04", "TELEMETRY", "updated daily by github actions"),
    ("contact", "05", "CONTACT", "say hi"),
]


def main():
    OUT.mkdir(exist_ok=True)
    for name, t in THEMES.items():
        files = {f"hero-{name}.svg": hero(t), f"stack-{name}.svg": stack(t), f"footer-{name}.svg": footer(t)}
        for key, num, label, note in SECTIONS:
            files[f"h-{key}-{name}.svg"] = section(t, num, label, note)
        for i, c in enumerate(CARDS, 1):
            files[f"card-{c['key']}-{name}.svg"] = card(t, c, i)
        for fn, data in files.items():
            (OUT / fn).write_text(data, encoding="utf-8")
    total = sum(f.stat().st_size for f in OUT.glob("*.svg"))
    print(f"wrote {len(list(OUT.glob('*.svg')))} svgs, {total/1024:.0f} KB total")


if __name__ == "__main__":
    main()
