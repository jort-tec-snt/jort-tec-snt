"""svgkit — primitives for the OrtizDev biomechanical SVG set.

Everything here emits plain SVG + SMIL (no scripts, no external resources),
which is what GitHub allows inside an <img>.
"""
import math
import random
import re

TAU = math.pi * 2

BG = "#07090A"
PANEL = "#080C09"
GREEN = "#39FF14"
LIME = "#9DFF3A"
CHROME = "#E5E7EB"
GRAY = "#6B7280"
SLATE = "#9CA3AF"
FLESH = "#121B16"
PUS = "#D8E64A"
ROT = "#7A3E8C"
MONO = ("'Cascadia Code','Cascadia Mono',Consolas,'SF Mono',Menlo,"
        "'DejaVu Sans Mono','Courier New',monospace")


def n(x):
    s = f"{x:.1f}"
    return s[:-2] if s.endswith(".0") else s


def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def svg_doc(w, h, body, defs="", title=""):
    t = esc(title)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="{t}">\n'
        f"<title>{t}</title>\n<defs>\n{COMMON_DEFS}\n{defs}\n</defs>\n{body}\n</svg>\n"
    )


COMMON_DEFS = f"""<filter id="glow" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur stdDeviation="6"/></filter>
<filter id="glow2" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur stdDeviation="2.4"/></filter>
<radialGradient id="pus" cx=".36" cy=".32" r=".8">
<stop offset="0" stop-color="#F6FFA8"/><stop offset=".4" stop-color="#D8E64A"/><stop offset=".78" stop-color="#6E9A10"/><stop offset="1" stop-color="#26400A"/></radialGradient>
<radialGradient id="vesicle" cx=".5" cy=".5" r=".5">
<stop offset=".6" stop-color="#39FF14" stop-opacity="0"/><stop offset=".92" stop-color="#39FF14" stop-opacity=".16"/><stop offset="1" stop-color="#9DFF3A" stop-opacity=".42"/></radialGradient>
<linearGradient id="chrome" x1="0" y1="0" x2="0" y2="1">
<stop offset="0" stop-color="#F9FAFB"/><stop offset=".5" stop-color="#9CA3AF"/><stop offset="1" stop-color="#4B5563"/></linearGradient>"""


# --------------------------------------------------------------------------
# tentacles
# --------------------------------------------------------------------------
def spine(base, length, a0, curl, amp, waves, phase, npts):
    x, y = base
    pts, ths = [(x, y)], [a0]
    step = length / npts
    for i in range(1, npts + 1):
        t = i / npts
        th = a0 + curl * t + amp * math.sin(TAU * waves * t - phase) * (0.25 + 0.75 * t)
        x += step * math.cos(th)
        y += step * math.sin(th)
        pts.append((x, y))
        ths.append(th)
    return pts, ths


def width_at(t, w0):
    return max(0.5, w0 * (1 - t) ** 0.85)


def body_path(pts, ths, w0):
    last = len(pts) - 1
    left, right = [], []
    for i, (p, th) in enumerate(zip(pts, ths)):
        w = width_at(i / last, w0)
        nx, ny = -math.sin(th), math.cos(th)
        left.append(f"{n(p[0] + nx * w)},{n(p[1] + ny * w)}")
        right.append(f"{n(p[0] - nx * w)},{n(p[1] - ny * w)}")
    return "M" + " L".join(left + right[::-1]) + "Z"


def spine_path(pts):
    return "M" + " L".join(f"{n(x)},{n(y)}" for x, y in pts)


def thorn_path(pts, ths, w0, side, every):
    last = len(pts) - 1
    segs = []
    for i in range(every, int(last * 0.86), every):
        t = i / last
        w = width_at(t, w0)
        th = ths[i]
        tx, ty = math.cos(th), math.sin(th)
        nx, ny = -math.sin(th) * side, math.cos(th) * side
        px, py = pts[i]
        ln = 4 + w * 0.5
        b1 = (px - tx * w * 0.4 + nx * w * 0.7, py - ty * w * 0.4 + ny * w * 0.7)
        b2 = (px + tx * w * 0.4 + nx * w * 0.7, py + ty * w * 0.4 + ny * w * 0.7)
        tip = (px + nx * (w + ln) + tx * ln * 1.5, py + ny * (w + ln) + ty * ln * 1.5)
        segs.append(f"M{n(b1[0])},{n(b1[1])} L{n(tip[0])},{n(tip[1])} L{n(b2[0])},{n(b2[1])}Z")
    return " ".join(segs)


class Tent:
    """A tapered, undulating tentacle: animated body, chrome thorns, sucker dots,
    and a bioluminescent pulse that travels base -> tip."""

    def __init__(self, tid, base, length, a0, curl=0.0, amp=0.3, waves=1.6, w0=14,
                 frames=10, dur=11.0, phase0=0.0, thorns=True, thorn_side=1,
                 npts=34, every=3):
        self.id, self.base, self.length = tid, base, length
        self.a0, self.curl, self.amp, self.waves, self.w0 = a0, curl, amp, waves, w0
        self.frames, self.dur, self.phase0 = frames, dur, phase0
        self.thorns, self.side, self.npts, self.every = thorns, thorn_side, npts, every

    def _frames(self):
        if getattr(self, "_cache", None):
            return self._cache
        bodies, spines, thorns, self.tips = [], [], [], []
        for k in range(self.frames + 1):
            ph = self.phase0 + TAU * k / self.frames
            pts, ths = spine(self.base, self.length, self.a0, self.curl,
                             self.amp, self.waves, ph, self.npts)
            bodies.append(body_path(pts, ths, self.w0))
            spines.append(spine_path(pts))
            self.tips.append(pts[-1])
            if self.thorns:
                thorns.append(thorn_path(pts, ths, self.w0, self.side, self.every))
        self._cache = (bodies, spines, thorns)
        return self._cache

    def defs(self):
        bodies, spines, thorns = self._frames()

        def el(suffix, frames):
            vals = ";".join(frames)
            return (f'<path id="{self.id}{suffix}" d="{frames[0]}">'
                    f'<animate attributeName="d" dur="{self.dur}s" repeatCount="indefinite" '
                    f'values="{vals}"/></path>')

        out = [el("b", bodies), el("s", spines)]
        if self.thorns:
            out.append(el("t", thorns))
        return "\n".join(out)

    def draw(self, opacity=1.0, glow=0.22, suckers=True, pulse=True, ridge=True, bulb=False):
        self._frames()
        i = self.id
        u = lambda suf: f'href="#{i}{suf}" xlink:href="#{i}{suf}"'
        o = [f'<g opacity="{opacity}">']
        if glow:
            o.append(f'<use {u("b")} fill="{GREEN}" opacity="{glow}" filter="url(#glow)"/>')
        o.append(f'<use {u("b")} fill="{FLESH}" stroke="{SLATE}" stroke-opacity=".8" stroke-width="1"/>')
        if ridge:
            o.append(f'<use {u("s")} fill="none" stroke="{CHROME}" stroke-opacity=".3" '
                     f'stroke-width="1.6" stroke-linecap="round"/>')
        if self.thorns:
            o.append(f'<use {u("t")} fill="url(#chrome)" opacity=".85"/>')
        if suckers:
            o.append(f'<use {u("s")} fill="none" stroke="{GREEN}" stroke-opacity=".8" '
                     f'stroke-width="{n(max(2.0, self.w0 * 0.18))}" stroke-linecap="round" '
                     f'stroke-dasharray="0.1 {n(max(9, self.w0 * 0.85))}"/>')
        if pulse:
            o.append(f'<use {u("s")} fill="none" stroke="{LIME}" stroke-width="{n(max(2.2, self.w0 * 0.2))}" '
                     f'stroke-linecap="round" stroke-dasharray="16 140" opacity=".95" filter="url(#glow2)">'
                     f'<animate attributeName="stroke-dashoffset" values="156;0" dur="{n(self.dur * 0.55)}s" '
                     f'repeatCount="indefinite"/></use>')
        if bulb:
            r = max(4.0, self.w0 * 0.3)
            xs = ";".join(n(p[0]) for p in self.tips)
            ys = ";".join(n(p[1]) for p in self.tips)
            o.append(f'<circle r="{n(r)}" cx="{n(self.tips[0][0])}" cy="{n(self.tips[0][1])}" fill="url(#pus)" '
                     f'stroke="{GREEN}" stroke-opacity=".6" stroke-width="1">'
                     f'<animate attributeName="cx" dur="{self.dur}s" repeatCount="indefinite" values="{xs}"/>'
                     f'<animate attributeName="cy" dur="{self.dur}s" repeatCount="indefinite" values="{ys}"/>'
                     f'<animate attributeName="r" values="{n(r)};{n(r * 1.3)};{n(r)}" dur="2.6s" repeatCount="indefinite"/></circle>')
        o.append("</g>")
        return "\n".join(o)


# --------------------------------------------------------------------------
# small organic extras
# --------------------------------------------------------------------------
def drip(x, y, length, delay, dur=6.0):
    d = f"{dur}s"
    b = f"{delay}s"
    return (
        f'<g><rect x="{n(x - 0.9)}" y="{n(y)}" width="1.8" height="0" rx=".9" fill="{LIME}">'
        f'<animate attributeName="height" values="0;{n(length)};{n(length)};{n(length)}" '
        f'keyTimes="0;.5;.8;1" dur="{d}" begin="{b}" repeatCount="indefinite"/>'
        f'<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;.5;.8;1" dur="{d}" begin="{b}" '
        f'repeatCount="indefinite"/></rect>'
        f'<circle cx="{n(x)}" cy="{n(y)}" r="1" fill="{LIME}" filter="url(#glow2)">'
        f'<animate attributeName="cy" values="{n(y)};{n(y + length)};{n(y + length + 70)};{n(y + length + 70)}" '
        f'keyTimes="0;.5;.85;1" dur="{d}" begin="{b}" repeatCount="indefinite"/>'
        f'<animate attributeName="r" values="1;3;3;3" keyTimes="0;.5;.85;1" dur="{d}" begin="{b}" '
        f'repeatCount="indefinite"/>'
        f'<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;.5;.85;1" dur="{d}" begin="{b}" '
        f'repeatCount="indefinite"/></circle></g>'
    )


def spores(rng, count, x0, x1, y0, y1, rmax=2.0):
    out = []
    for _ in range(count):
        x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
        r = rng.uniform(0.5, rmax)
        dur = rng.uniform(6, 15)
        rise = rng.uniform(25, 70)
        start = -rng.uniform(0, dur)
        out.append(
            f'<circle cx="{n(x)}" cy="{n(y)}" r="{n(r)}" fill="{LIME}" opacity="0">'
            f'<animate attributeName="cy" values="{n(y)};{n(y - rise)};{n(y)}" dur="{n(dur)}s" '
            f'begin="{n(start)}s" repeatCount="indefinite"/>'
            f'<animate attributeName="opacity" values="0;.85;0" dur="{n(dur)}s" begin="{n(start)}s" '
            f'repeatCount="indefinite"/></circle>'
        )
    return "\n".join(out)


# --------------------------------------------------------------------------
# angular title letters (monoline, 60 x 90 grid) — drawn as paths so they
# render identically on every OS (no font dependency)
# --------------------------------------------------------------------------
LETTERS = {
    "O": "M12,0 L48,0 L60,12 L60,78 L48,90 L12,90 L0,78 L0,12 Z",
    "R": "M0,90 L0,0 L48,0 L60,12 L60,38 L48,50 L0,50 M28,50 L60,90",
    "T": "M0,0 L60,0 M30,0 L30,90",
    "I": "M10,0 L50,0 M30,0 L30,90 M10,90 L50,90",
    "Z": "M0,0 L60,0 L0,90 L60,90",
    "D": "M0,0 L0,90 L40,90 L60,70 L60,20 L40,0 Z",
    "E": "M60,0 L0,0 L0,90 L60,90 M0,45 L46,45",
    "V": "M0,0 L30,90 L60,0",
}
_XY = re.compile(r"(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)")


def letter_path(ch, ox, oy, sc):
    return _XY.sub(lambda m: f"{n(ox + float(m[1]) * sc)},{n(oy + float(m[2]) * sc)}", LETTERS[ch])


# --------------------------------------------------------------------------
# micro-ecosystem: pustules, vesicles, bacteria, cilia
# --------------------------------------------------------------------------
SPLINE = 'calcMode="spline" keySplines=".45 0 .55 1;.45 0 .55 1"'


def pustule(cx, cy, r, dur=5.2, delay=0.0, burst=False, rng=None, halo=True):
    """A swelling pus-filled bulb. Non-burst ones 'breathe'; burst ones swell, pop,
    eject spores and regrow."""
    rng = rng or random.Random(int(cx * 7 + cy))
    hl = (f'<ellipse cx="{n(-r * .32)}" cy="{n(-r * .4)}" rx="{n(r * .3)}" ry="{n(r * .17)}" '
          f'fill="#fff" opacity=".6" transform="rotate(-32 {n(-r * .32)} {n(-r * .4)})"/>')
    sat = ""
    for k in range(3):
        a = rng.uniform(0, TAU)
        sr = r * rng.uniform(.14, .22)
        sat += (f'<circle cx="{n(math.cos(a) * r * .5)}" cy="{n(math.sin(a) * r * .5)}" r="{n(sr)}" '
                f'fill="#F6FFA8" opacity=".35"/>')
    core = (f'<circle r="{n(r * 1.45)}" fill="{GREEN}" opacity=".16" filter="url(#glow2)"/>' if halo else "")
    core += (f'<circle r="{n(r)}" fill="url(#pus)" stroke="{GREEN}" stroke-opacity=".55" stroke-width="1"/>'
             f'<circle r="{n(r)}" fill="none" stroke="{ROT}" stroke-opacity=".35" stroke-width="{n(max(1, r * .12))}"/>'
             + sat + hl)
    if not burst:
        return (f'<g transform="translate({n(cx)},{n(cy)})"><g>'
                f'<animateTransform attributeName="transform" type="scale" values="1;1.1;1" keyTimes="0;.5;1" '
                f'dur="{n(dur)}s" begin="{n(delay)}s" repeatCount="indefinite" {SPLINE}/>{core}</g></g>')
    kt = "0;.5;.55;.8;.84;1"
    sp = ""
    for k in range(8):
        a = TAU * k / 8 + rng.uniform(-.25, .25)
        d = r * rng.uniform(2.2, 3.6)
        sr = rng.uniform(1.2, 2.6)
        dx, dy = math.cos(a) * d, math.sin(a) * d - r * .5
        sp += (f'<circle r="{n(sr)}" fill="{LIME}" opacity="0">'
               f'<animate attributeName="cx" values="0;0;{n(dx)};{n(dx)}" keyTimes="0;.5;.8;1" dur="{n(dur)}s" begin="{n(delay)}s" repeatCount="indefinite"/>'
               f'<animate attributeName="cy" values="0;0;{n(dy)};{n(dy + 8)}" keyTimes="0;.5;.8;1" dur="{n(dur)}s" begin="{n(delay)}s" repeatCount="indefinite"/>'
               f'<animate attributeName="opacity" values="0;0;1;0;0" keyTimes="0;.5;.53;.82;1" dur="{n(dur)}s" begin="{n(delay)}s" repeatCount="indefinite"/></circle>')
    ring = (f'<circle r="{n(r * 1.4)}" fill="none" stroke="{LIME}" stroke-width="2" opacity="0">'
            f'<animate attributeName="r" values="{n(r * 1.4)};{n(r * 1.4)};{n(r * 3.4)};{n(r * 3.4)}" keyTimes="0;.5;.72;1" dur="{n(dur)}s" begin="{n(delay)}s" repeatCount="indefinite"/>'
            f'<animate attributeName="opacity" values="0;0;.8;0;0" keyTimes="0;.5;.53;.74;1" dur="{n(dur)}s" begin="{n(delay)}s" repeatCount="indefinite"/></circle>')
    return (f'<g transform="translate({n(cx)},{n(cy)})">{ring}{sp}<g>'
            f'<animateTransform attributeName="transform" type="scale" values="1;1.4;1.62;.2;.2;1" keyTimes="{kt}" '
            f'dur="{n(dur)}s" begin="{n(delay)}s" repeatCount="indefinite"/>'
            f'<animate attributeName="opacity" values="1;1;0;0;1;1" keyTimes="{kt}" dur="{n(dur)}s" begin="{n(delay)}s" repeatCount="indefinite"/>'
            f'{core}</g></g>')


def vesicle(cx, cy, r, dur=18.0, delay=0.0, drift=22):
    """Large translucent cell-membrane bubble, drifting and breathing."""
    return (f'<circle cx="{n(cx)}" cy="{n(cy)}" r="{n(r)}" fill="url(#vesicle)" stroke="{GREEN}" stroke-opacity=".22">'
            f'<animate attributeName="r" values="{n(r)};{n(r * 1.07)};{n(r)}" dur="{n(dur * .28)}s" begin="{n(delay)}s" repeatCount="indefinite"/>'
            f'<animate attributeName="cy" values="{n(cy)};{n(cy - drift)};{n(cy)}" dur="{n(dur)}s" begin="{n(delay)}s" repeatCount="indefinite"/></circle>')


def phage(sc, rng):
    """Bacteriophage: icosahedral head with coiled DNA, collar, ringed sheath, base plate and
    four flexing tail fibres. Local origin = centre of the head/tail junction, tail points down."""
    f = lambda k, v: f'{k}="{v}"'
    dur = n(rng.uniform(1.6, 2.6))
    def leg(sx, ph):
        a = f"M{sx * 4},24 L{sx * 15},11 L{sx * 21},31"
        b = f"M{sx * 4},24 L{sx * 17},13 L{sx * 20},31"
        v = f"{a};{b};{a}" if ph else f"{b};{a};{b}"
        return (f'<path d="{a}" fill="none" stroke="{GREEN}" stroke-width="1.6" stroke-linejoin="round" stroke-linecap="round">'
                f'<animate attributeName="d" values="{v}" dur="{dur}s" repeatCount="indefinite"/></path>')
    legs = leg(-1, 0) + leg(1, 1) + leg(-1, 1).replace("1.6", "1").replace(f'stroke="{GREEN}"', f'stroke="{GREEN}" stroke-opacity=".6"') \
        + leg(1, 0).replace("1.6", "1").replace(f'stroke="{GREEN}"', f'stroke="{GREEN}" stroke-opacity=".6"')
    rings = "".join(f'<path d="M-3.4,{y} L3.4,{y}" stroke="{GREEN}" stroke-opacity=".7" stroke-width="1"/>' for y in range(0, 22, 3))
    dna = (f'<path d="M-6,-16 q6,-7 12,0 t-12,8 q6,-7 12,0 t-12,8 M-4,-30 q8,-4 8,3 t-8,6" fill="none" stroke="{PUS}" '
           f'stroke-width="1.5" stroke-linecap="round"><animate attributeName="opacity" values=".5;1;.5" dur="5.2s" repeatCount="indefinite"/></path>')
    return (f'<g transform="scale({n(sc)}) translate(0,-6)">'
            f'<polygon points="0,-42 12,-34 12,-14 0,-5 -12,-14 -12,-34" fill="#16240F" stroke="{GREEN}" stroke-width="1.6" stroke-linejoin="round"/>'
            f'<path d="M-12,-34 L0,-24 L12,-34 M0,-24 L0,-5" stroke="{GREEN}" stroke-opacity=".4" stroke-width=".8" fill="none"/>'
            f'{dna}<rect x="-4" y="-5" width="8" height="4" fill="{SLATE}" opacity=".8"/>'
            f'<rect x="-3.4" y="-1" width="6.8" height="23" fill="#0F1A12" stroke="{GREEN}" stroke-opacity=".8"/>{rings}'
            f'<polygon points="-8,22 8,22 5,28 -5,28" fill="{LIME}" opacity=".85" stroke="{GREEN}"/>{legs}</g>')


def bacteria(rng, count, x0, x1, y0, y1, opacity=.85):
    out = []
    for i in range(count):
        x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
        L, Wd = rng.uniform(14, 26), rng.uniform(5, 8)
        dur = rng.uniform(22, 40)
        a0 = rng.uniform(-60, 60)
        pts = [(x, y), (x + rng.uniform(-60, 60), y + rng.uniform(-40, 40)),
               (x + rng.uniform(-60, 60), y + rng.uniform(-40, 40)), (x, y)]
        tv = ";".join(f"{n(px)},{n(py)}" for px, py in pts)
        rv = f"{n(a0)};{n(a0 + rng.uniform(20, 50))};{n(a0 - rng.uniform(10, 40))};{n(a0)}"
        beg = -rng.uniform(0, dur)
        if i % 3 == 0:  # coccus chain
            k = rng.randint(3, 4)
            cr = Wd * .55
            body = "".join(f'<circle cx="{n(j * cr * 1.8 - k * cr * .9)}" cy="0" r="{n(cr)}" fill="#16240F" stroke="{GREEN}" stroke-opacity=".6"/>'
                           f'<circle cx="{n(j * cr * 1.8 - k * cr * .9)}" cy="0" r="{n(cr * .35)}" fill="{PUS}" opacity=".7"/>' for j in range(k))
            tail = ""
        else:           # bacteriophage
            body, tail = phage(rng.uniform(.95, 1.35), rng), ""
        out.append(
            f'<g opacity="{opacity}"><g><animateTransform attributeName="transform" type="translate" values="{tv}" '
            f'dur="{n(dur)}s" begin="{n(beg)}s" repeatCount="indefinite"/>'
            f'<g><animateTransform attributeName="transform" type="rotate" values="{rv}" dur="{n(dur * .6)}s" '
            f'begin="{n(beg)}s" repeatCount="indefinite"/>{tail}{body}</g></g></g>')
    return "\n".join(out)


def cilia(rng, x0, x1, y, direction=-1, count=60, lmin=12, lmax=30, opacity=.5):
    """A fringe of waving hairs along an edge (direction -1 = growing upward)."""
    out = []
    for i in range(count):
        x = x0 + (x1 - x0) * (i + rng.uniform(-.3, .3)) / count
        ln = rng.uniform(lmin, lmax)
        sw = rng.uniform(5, 11)
        dur = rng.uniform(2.2, 4.2)
        beg = -rng.uniform(0, dur)
        y2 = y + direction * ln
        d1 = f"M{n(x)},{n(y)} Q{n(x - sw)},{n(y + direction * ln * .55)} {n(x - sw * .4)},{n(y2)}"
        d2 = f"M{n(x)},{n(y)} Q{n(x + sw)},{n(y + direction * ln * .55)} {n(x + sw * .4)},{n(y2)}"
        out.append(f'<path d="{d1}" fill="none" stroke="{GREEN}" stroke-width="1.7" stroke-linecap="round" opacity="{opacity}">'
                   f'<animate attributeName="d" values="{d1};{d2};{d1}" dur="{n(dur)}s" begin="{n(beg)}s" repeatCount="indefinite" {SPLINE}/></path>')
    return "\n".join(out)
