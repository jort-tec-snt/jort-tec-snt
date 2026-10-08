#!/usr/bin/env python3
"""
Builds the living parts of the profile from real GitHub data:

    dist/organism.svg   contribution calendar as a creature that feeds on your commits
    dist/vitals.svg     streaks, language colonies, yearly pulse, weekday rhythm
    dist/feed.svg       latest public pushes ("mutations")

Python standard library only. Reuses the drawing kit in svgkit.py (same folder).

    python scripts/build_profile.py --out dist                # real data (needs GH_TOKEN)
    python scripts/build_profile.py --out dist --fixture      # synthetic data, no network

Environment:
    GH_TOKEN        token used for the API (the workflow passes GITHUB_TOKEN or PROFILE_TOKEN)
    PROFILE_USER    GitHub login (defaults to jort-tec-snt)

Only PUBLIC data is read: public contribution counts, public repos, public push events.
"""
import argparse
import datetime as dt
import json
import math
import os
import random
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from svgkit import (BG, PANEL, GREEN, LIME, PUS, ROT, CHROME, GRAY, SLATE, FLESH, MONO,  # noqa: E402
                    n, esc, svg_doc, pustule, vesicle, bacteria, cilia, phage)

USER = os.environ.get("PROFILE_USER", "jort-tec-snt")
API = "https://api.github.com"

LEVEL_FILL = ["#0F1612", "#17420F", "#27901A", GREEN, "#C6FF4A"]


# ====================================================================== DATA
def http_json(url, token, body=None):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body else None)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "profile-organism")
    if body:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


QUERY = """
query($login:String!){
  user(login:$login){
    followers{ totalCount }
    contributionsCollection{
      contributionCalendar{
        totalContributions
        weeks{ contributionDays{ date contributionCount contributionLevel weekday } }
      }
    }
    repositories(first:100, ownerAffiliations:OWNER, isFork:false, privacy:PUBLIC){
      totalCount
      nodes{ languages(first:8, orderBy:{field:SIZE, direction:DESC}){ edges{ size node{ name } } } }
    }
  }
}"""
LEVELS = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}


def fetch_real(token):
    d = http_json(f"{API}/graphql", token, {"query": QUERY, "variables": {"login": USER}})
    if "errors" in d or not d.get("data", {}).get("user"):
        raise RuntimeError(f"GraphQL error: {d.get('errors')}")
    u = d["data"]["user"]
    cal = u["contributionsCollection"]["contributionCalendar"]
    weeks = [[{"date": x["date"], "count": x["contributionCount"],
               "level": LEVELS.get(x["contributionLevel"], 0), "wd": x["weekday"]}
              for x in w["contributionDays"]] for w in cal["weeks"]]
    langs = {}
    for r in u["repositories"]["nodes"]:
        for e in r["languages"]["edges"]:
            langs[e["node"]["name"]] = langs.get(e["node"]["name"], 0) + e["size"]
    # latest pushes (public events)
    feed = []
    try:
        events = http_json(f"{API}/users/{USER}/events/public?per_page=60", token)
    except Exception as exc:  # feed is optional, never fail the whole build for it
        print("  feed unavailable:", exc)
        events = []
    for ev in events:
        if ev.get("type") != "PushEvent" or len(feed) >= 5:
            continue
        repo = ev["repo"]["name"].split("/")[-1]
        pl = ev.get("payload", {})
        sha = pl.get("head") or ""
        msg = ""
        if pl.get("commits"):
            msg = pl["commits"][-1].get("message", "")
        if not msg and sha:
            try:
                msg = http_json(f"{API}/repos/{ev['repo']['name']}/commits/{sha}", token)["commit"]["message"]
            except Exception:
                msg = "(push)"
        feed.append({"repo": repo, "sha": sha[:7], "msg": msg.strip().split("\n")[0],
                     "date": ev["created_at"][:10]})
    return {"weeks": weeks, "total": cal["totalContributions"], "langs": langs, "feed": feed,
            "followers": u["followers"]["totalCount"], "repos": u["repositories"]["totalCount"]}


def fetch_fixture():
    rng = random.Random(7)
    end = dt.date(2026, 10, 7)
    start = end - dt.timedelta(days=364)
    start -= dt.timedelta(days=(start.weekday() + 1) % 7)  # back to Sunday
    days, d = [], start
    while d <= end:
        wd = (d.weekday() + 1) % 7
        base = 0 if rng.random() < (.55 if wd in (0, 6) else .3) else rng.choice([1, 1, 2, 3, 5, 8, 12])
        if d.month in (8, 9, 10):
            base = base + rng.choice([0, 1, 2, 4]) if base else rng.choice([0, 2, 5])
        if 8 <= (d - start).days % 60 <= 14:
            base = 0
        days.append({"date": d.isoformat(), "count": base, "wd": wd})
        d += dt.timedelta(days=1)
    mx = max(x["count"] for x in days)
    for x in days:
        c = x["count"]
        x["level"] = 0 if c == 0 else min(4, 1 + int(4 * (c - 1) / max(mx, 1)))
    weeks, cur = [], []
    for x in days:
        if x["wd"] == 0 and cur:
            weeks.append(cur)
            cur = []
        cur.append(x)
    weeks.append(cur)
    return {"weeks": weeks, "total": sum(x["count"] for x in days),
            "langs": {"Java": 52000, "JavaScript": 38000, "PHP": 31000, "Python": 22000,
                      "Dart": 14000, "HTML": 9000, "Dockerfile": 3000},
            "feed": [
                {"repo": "plant-guardian", "sha": "a91c3e7", "msg": "feat(api): add sensor ingestion endpoint with validation", "date": "2026-10-06"},
                {"repo": "mediguard", "sha": "5be02d1", "msg": "fix: sanitize patient search input", "date": "2026-10-05"},
                {"repo": "jort-tec-snt", "sha": "03fd8aa", "msg": "feat(profile): biomechanical microecosystem README", "date": "2026-10-05"},
                {"repo": "docker-labs", "sha": "c7710b9", "msg": "chore: multi-stage build, image 412MB -> 87MB", "date": "2026-10-02"},
                {"repo": "aws-lab", "sha": "e4d2f60", "msg": "docs: describe VPC + subnet layout", "date": "2026-09-30"}],
            "followers": 12, "repos": 14}


# =================================================================== HELPERS
def frame(x, y, w, h, c=10, stroke=GRAY, op=.55, fill=PANEL):
    pts = f"{x + c},{y} {x + w},{y} {x + w},{y + h - c} {x + w - c},{y + h} {x},{y + h} {x},{y + c}"
    return (f'<polygon points="{pts}" fill="{fill}" stroke="{stroke}" stroke-opacity="{op}" stroke-width="1.2"/>'
            f'<path d="M{x},{y + c} L{x + c},{y}" stroke="{GREEN}" stroke-width="2" opacity=".9"/>'
            f'<path d="M{x + w},{y + h - c} L{x + w - c},{y + h}" stroke="{GREEN}" stroke-width="2" opacity=".9"/>')


def text(x, y, s, size=12, fill=SLATE, weight="normal", anchor="start", op=1, extra=""):
    return (f'<text x="{n(x)}" y="{n(y)}" font-family="{MONO}" font-size="{size}" font-weight="{weight}" '
            f'fill="{fill}" text-anchor="{anchor}" opacity="{op}" {extra}>{esc(s)}</text>')


def clean(s, limit):
    s = re.sub(r"[\x00-\x1f\x7f]", " ", s)
    return s if len(s) <= limit else s[:limit - 1] + "…"


def streaks(days):
    cnt = [d["count"] for d in days]
    longest = run = 0
    for c in cnt:
        run = run + 1 if c > 0 else 0
        longest = max(longest, run)
    cur, i = 0, len(cnt) - 1
    if i >= 0 and cnt[i] == 0:  # today may not have happened yet
        i -= 1
    while i >= 0 and cnt[i] > 0:
        cur += 1
        i -= 1
    return cur, longest


def vein_bg(W, H, seed):
    rng = random.Random(seed)
    out = ""
    for _ in range(3):
        x = rng.uniform(0, W)
        out += (f'<circle cx="{n(x)}" cy="{n(rng.uniform(0, H))}" r="{n(rng.uniform(60, 120))}" fill="{GREEN}" opacity=".025" filter="url(#glow)"/>')
    return out


# =================================================================== ORGANISM
def render_organism(data):
    weeks = data["weeks"]
    ncols = len(weeks)
    W, H = 1000, 262
    X0, Y0 = 44, 62
    P = min(18.0, (W - X0 - 14) / ncols)
    C = P - 3
    cells = {}
    for ci, w in enumerate(weeks):
        for d in w:
            cells[(ci, d["wd"])] = d

    # serpentine route through existing cells
    route = []
    for ci in range(ncols):
        rows = sorted(r for (c, r) in cells if c == ci)
        route += [(ci, r) for r in (rows if ci % 2 == 0 else rows[::-1])]
    ctr = lambda ci, r: (X0 + ci * P + C / 2, Y0 + r * P + C / 2)
    pts = [ctr(*k) for k in route]
    dist = [0.0]
    for a, b in zip(pts, pts[1:]):
        dist.append(dist[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    L = dist[-1] or 1
    MOVE = max(18.0, len(route) * 0.075)
    HOLD = 4.0
    T = MOVE + HOLD
    tcell = {k: dist[i] / L * MOVE for i, k in enumerate(route)}
    path_d = "M" + " L".join(f"{n(x)},{n(y)}" for x, y in pts)

    # cells
    maxlvl = max([d["level"] for w in weeks for d in w] + [0])
    body = []
    for key in route:
        ci, r = key
        d = cells[key]
        x, y = X0 + ci * P, Y0 + r * P
        lv = d["level"]
        tip = f'<title>{esc(d["date"])}: {d["count"]} contributions</title>'
        if lv == 0:
            body.append(f'<rect x="{n(x)}" y="{n(y)}" width="{n(C)}" height="{n(C)}" rx="3" fill="{LEVEL_FILL[0]}" '
                        f'stroke="#1A271F" stroke-width=".8">{tip}</rect>')
        else:
            p = tcell[key] / T
            kt = f"0;{p:.4f};{p + .006:.4f};.96;1"
            vals = f"{LEVEL_FILL[0]};{LEVEL_FILL[0]};{LEVEL_FILL[lv]};{LEVEL_FILL[lv]};{LEVEL_FILL[0]}"
            body.append(f'<rect x="{n(x)}" y="{n(y)}" width="{n(C)}" height="{n(C)}" rx="3" fill="{LEVEL_FILL[0]}" '
                        f'stroke="#1A271F" stroke-width=".8">{tip}'
                        f'<animate attributeName="fill" values="{vals}" keyTimes="{kt}" dur="{n(T)}s" repeatCount="indefinite"/></rect>')
    cellsvg = (f'<g>{"".join(body)}<animate attributeName="opacity" values=".86;1;.86" dur="5.2s" '
               f'repeatCount="indefinite" calcMode="spline" keyTimes="0;.5;1" keySplines=".45 0 .55 1;.45 0 .55 1"/></g>')

    # spore bombs on the hottest days, spaced along the route
    bombs, last = [], -99
    top = maxlvl if maxlvl >= 3 else 99
    for i, key in enumerate(route):
        if cells[key]["level"] >= top and i - last >= 11 and len(bombs) < 26:
            bombs.append(key)
            last = i
    bsvg = []
    for key in bombs:
        ci, r = key
        cx, cy = ctr(ci, r)
        t = tcell[key]
        p0, p1, p2 = t / T, (t + 1.5) / T, (t + 2.2) / T
        e = .004
        arm = 2 * P + C / 2
        cross = (f'<rect x="{n(-arm)}" y="{n(-C * .28)}" width="{n(2 * arm)}" height="{n(C * .56)}" rx="3" fill="{LIME}"/>'
                 f'<rect x="{n(-C * .28)}" y="{n(-arm)}" width="{n(C * .56)}" height="{n(2 * arm)}" rx="3" fill="{LIME}"/>'
                 f'<circle r="{n(C * .9)}" fill="{PUS}"/>')
        bsvg.append(
            f'<g transform="translate({n(cx)},{n(cy)})">'
            # swelling spore
            f'<g opacity="0"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;{p0:.4f};{p0 + e:.4f};{p1:.4f};{p1 + e:.4f};1" dur="{n(T)}s" repeatCount="indefinite"/>'
            f'<g><animateTransform attributeName="transform" type="scale" values="0.5;0.5;1.35;0.9;1.6;1.6" keyTimes="0;{p0:.4f};{(p0 + p1) / 2:.4f};{(p0 + p1) / 2 + .01:.4f};{p1:.4f};1" dur="{n(T)}s" repeatCount="indefinite"/>'
            f'<circle r="{n(C * .5)}" fill="url(#pus)" stroke="{GREEN}" stroke-width="1"/></g></g>'
            # cross-shaped blast
            f'<g opacity="0"><animate attributeName="opacity" values="0;0;.85;0;0" keyTimes="0;{p1:.4f};{p1 + e:.4f};{p2:.4f};1" dur="{n(T)}s" repeatCount="indefinite"/>'
            f'<g><animateTransform attributeName="transform" type="scale" values="0.15;0.15;1;1" keyTimes="0;{p1:.4f};{p2:.4f};1" dur="{n(T)}s" repeatCount="indefinite"/>{cross}</g></g>'
            f'</g>')

    # the creature
    segs = [(0.0, 7.2, GREEN), (0.30, 6.2, LIME), (0.60, 5.4, LIME), (0.90, 4.6, PUS), (1.20, 3.8, PUS), (1.50, 3.0, PUS)]
    cre = []
    for lag, r, col in reversed(segs):
        a, b = lag / T, (lag + MOVE) / T
        extra = ""
        if lag == 0:
            extra = (f'<circle r="3.1" cx="2.2" cy="-1.6" fill="{BG}"/><circle r="1.2" cx="2.8" cy="-1.9" fill="#fff"/>'
                     f'<circle r="3.1" cx="2.2" cy="2.6" fill="{BG}"/><circle r="1.2" cx="2.8" cy="2.3" fill="#fff"/>')
        cre.append(f'<g><animateMotion dur="{n(T)}s" repeatCount="indefinite" calcMode="linear" '
                   f'keyPoints="0;0;1;1" keyTimes="0;{a:.4f};{b:.4f};1" path="{path_d}"/>'
                   f'<circle r="{n(r * 2.1)}" fill="{GREEN}" opacity=".22" filter="url(#glow2)"/>'
                   f'<circle r="{n(r)}" fill="{col}" stroke="{BG}" stroke-width="1.2"/>{extra}</g>')
    creature = (f'<g>{"".join(cre)}<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;.93;.97;1" '
                f'dur="{n(T)}s" repeatCount="indefinite"/></g>')

    # bacteriophages that land on dormant days and infect them
    rng_p = random.Random(5)
    dormant = [k for k in route if cells[k]["level"] == 0 and k[0] > ncols * .35 and 1 <= k[1] <= 5]
    infect = []
    for j in range(5 if dormant else 0):
        key = rng_p.choice(dormant)
        cx, cy = ctr(*key)
        sc = 1.15
        per = 11.0 + j * 1.3
        beg = j * 2.3
        land = cy - 28 * sc
        infect.append(
            f'<rect x="{n(cx - C / 2)}" y="{n(cy - C / 2)}" width="{n(C)}" height="{n(C)}" rx="3" fill="{ROT}" opacity="0">'
            f'<animate attributeName="opacity" values="0;0;.95;.95;0;0" keyTimes="0;.34;.40;.62;.72;1" dur="{n(per)}s" begin="{n(beg)}s" repeatCount="indefinite"/></rect>'
            f'<g opacity="0"><animate attributeName="opacity" values="0;1;1;1;0;0" keyTimes="0;.08;.5;.7;.85;1" dur="{n(per)}s" begin="{n(beg)}s" repeatCount="indefinite"/>'
            f'<g><animateTransform attributeName="transform" type="translate" '
            f'values="{n(cx + 40)},{n(land - 90)};{n(cx)},{n(land)};{n(cx)},{n(land)};{n(cx)},{n(land)};{n(cx - 30)},{n(land - 80)};{n(cx - 30)},{n(land - 80)}" '
            f'keyTimes="0;.34;.4;.62;.9;1" dur="{n(per)}s" begin="{n(beg)}s" repeatCount="indefinite"/>{phage(sc, rng_p)}</g></g>')
    infection = "".join(infect)

    # month + weekday labels
    labels, lastm, lastx = [], None, -99
    for ci, w in enumerate(weeks):
        m = dt.date.fromisoformat(w[0]["date"]).month
        if m != lastm:
            if ci * P - lastx >= 40 and not (ci == 0 and len(weeks) > 1 and
                                              dt.date.fromisoformat(weeks[1][0]["date"]).month != m):
                labels.append(text(X0 + ci * P, Y0 - 10, dt.date(2000, m, 1).strftime("%b").upper(), 12, GRAY))
                lastx = ci * P
            lastm = m
    for r, nm in ((1, "MON"), (3, "WED"), (5, "FRI")):
        labels.append(text(X0 - 8, Y0 + r * P + C - 3, nm, 11, GRAY, anchor="end"))

    # chrome: header line, legend, ornaments
    legend = text(W - 14 - 5 * 22 - 150, 238, "DORMANT", 12, GRAY)
    lx = W - 14 - 5 * 22 - 76
    for i, c in enumerate(LEVEL_FILL):
        legend += f'<rect x="{lx + i * 22}" y="229" width="14" height="14" rx="3" fill="{c}" stroke="#1A271F"/>'
    legend += text(lx + 5 * 22 + 4, 238, "HYPER", 12, GRAY)
    rng = random.Random(11)
    deco = vein_bg(W, H, 3) + "".join(
        pustule(x, y, r, 5.2, d, False, rng) for x, y, r, d in ((16, 233, 6, 0), (W - 14, 28, 5.5, .8)))
    deco += cilia(rng, 40, 330, H - 3, -1, 40, 4, 10, .35)
    head = (text(X0, 30, f"> organism.scan  //  {data['total']:,} contributions  //  {ncols} weeks", 15, GREEN, "bold") +
            text(W - 40, 30, f"spores armed: {len(bombs)}", 14, LIME, anchor="end", op=.9) +
            text(X0, 240, "> state: feeding  //  every lit cell is a day it ate", 13, SLATE))
    defs = ""
    body = (f'<rect width="{W}" height="{H}" fill="{BG}"/>{deco}{"".join(labels)}{cellsvg}{infection}{"".join(bsvg)}{creature}{head}{legend}')
    return svg_doc(W, H, body, defs, "Contribution organism")


# ===================================================================== VITALS
def render_vitals(data):
    W, H = 1000, 382
    days = [d for w in data["weeks"] for d in w]
    cur, longest = streaks(days)
    best = max(days, key=lambda d: d["count"]) if days else {"count": 0, "date": "-"}
    stats = [("CONTRIBUTIONS", f"{data['total']:,}", "last 12 months"),
             ("CURRENT.STREAK", f"{cur}", "consecutive days"),
             ("LONGEST.STREAK", f"{longest}", "days in a row"),
             ("BEST.DAY", f"{best['count']}", best["date"])]
    out = [f'<rect width="{W}" height="{H}" fill="{BG}"/>', vein_bg(W, H, 5)]
    rng = random.Random(21)
    cw, gap = 232, 24
    for i, (lab, val, cap) in enumerate(stats):
        x = i * (cw + gap)
        out.append(frame(x, 8, cw, 124))
        out.append(text(x + 16, 34, lab, 11, GRAY, "bold", extra='letter-spacing="2"'))
        out.append(text(x + 16, 92, val, 52, GREEN, "bold", op=.5, extra='filter="url(#glow2)"'))
        out.append(text(x + 16, 92, val, 52, GREEN, "bold"))
        out.append(text(x + 16, 118, cap, 11, SLATE))
        out.append(pustule(x + cw - 20, 28, 6, 5.2, i * .5, False, rng))
        if i < 3:  # vein with travelling pulse between cells
            y = 70
            out.append(f'<path d="M{x + cw},{y} L{x + cw + gap},{y}" stroke="{GREEN}" stroke-width="2" opacity=".55"/>')
            out.append(f'<circle r="2.6" fill="{LIME}"><animateMotion dur="2.6s" begin="{i * .7}s" repeatCount="indefinite" path="M{x + cw},{y} L{x + cw + gap},{y}"/></circle>')

    # --- language colonies
    out.append(frame(0, 150, 490, 224))
    out.append(text(16, 176, "LANG.COLONIES", 11, GRAY, "bold", extra='letter-spacing="2"'))
    langs = sorted(data["langs"].items(), key=lambda kv: -kv[1])[:6]
    tot = sum(data["langs"].values()) or 1
    pal = [GREEN, LIME, PUS, ROT, SLATE, CHROME]
    pmax = langs[0][1] if langs else 1
    cx0, cy0 = 128, 276
    placed = []
    for i, (nm, sz) in enumerate(langs):
        r = 12 + 30 * math.sqrt(sz / pmax) if i else 42
        if i == 0:
            x, y = cx0, cy0
        else:
            a = (-.6, 2.7, .9, 4.1, 5.3)[i - 1]
            dd = placed[0][2] + r + 3
            x, y = cx0 + math.cos(a) * dd, cy0 + math.sin(a) * dd
        placed.append((x, y, r))
        col = pal[i]
        dly = i * .7
        out.append(f'<g transform="translate({n(x)},{n(y)})"><g>'
                   f'<animateTransform attributeName="transform" type="scale" values="1;1.07;1" dur="5.2s" begin="{n(dly)}s" repeatCount="indefinite" calcMode="spline" keyTimes="0;.5;1" keySplines=".45 0 .55 1;.45 0 .55 1"/>'
                   f'<circle r="{n(r * 1.35)}" fill="{col}" opacity=".10" filter="url(#glow2)"/>'
                   f'<circle r="{n(r)}" fill="{col}" fill-opacity=".14" stroke="{col}" stroke-opacity=".8" stroke-width="1.4"/>'
                   f'<circle r="{n(r * .55)}" cx="{n(r * .12)}" cy="{n(-r * .1)}" fill="{col}" fill-opacity=".45"/>'
                   f'<circle r="{n(r * .22)}" cx="{n(-r * .35)}" cy="{n(r * .3)}" fill="{col}" fill-opacity=".8"/>'
                   f'<ellipse cx="{n(-r * .38)}" cy="{n(-r * .45)}" rx="{n(r * .22)}" ry="{n(r * .12)}" fill="#fff" opacity=".35" transform="rotate(-32 {n(-r * .38)} {n(-r * .45)})"/>'
                   f'</g></g>')
    # legend list
    for i, (nm, sz) in enumerate(langs):
        y = 204 + i * 27
        pct = sz / tot * 100
        out.append(f'<circle cx="262" cy="{y - 4}" r="4.5" fill="{pal[i]}"/>')
        out.append(text(274, y, clean(nm, 13), 13, CHROME))
        out.append(text(474, y, f"{pct:.0f}%", 13, pal[i], "bold", "end"))
        out.append(f'<rect x="274" y="{y + 5}" width="200" height="2" fill="#1A271F"/>'
                   f'<rect x="274" y="{y + 5}" width="{n(200 * sz / (langs[0][1] or 1))}" height="2" fill="{pal[i]}" opacity=".85">'
                   f'<animate attributeName="opacity" values=".5;.95;.5" dur="5.2s" begin="{n(i * .3)}s" repeatCount="indefinite"/></rect>')

    # --- yearly pulse + weekday rhythm
    out.append(frame(510, 150, 490, 224))
    out.append(text(526, 176, "PULSE.52W", 11, GRAY, "bold", extra='letter-spacing="2"'))
    wk = [sum(d["count"] for d in w) for w in data["weeks"]]
    mx = max(wk + [1])
    px0, px1, py0, py1 = 530, 980, 192, 282
    step = (px1 - px0) / max(len(wk) - 1, 1)
    pts = [(px0 + i * step, py1 - (v / mx) * (py1 - py0)) for i, v in enumerate(wk)]
    pd = "M" + " L".join(f"{n(x)},{n(y)}" for x, y in pts)
    out.append(f'<path d="M{px0},{py1} L{px1},{py1}" stroke="#1A271F" stroke-width="1"/>')
    out.append(f'<path d="{pd} L{px1},{py1} L{px0},{py1} Z" fill="{GREEN}" opacity=".07"/>')
    out.append(f'<path d="{pd}" fill="none" stroke="{GREEN}" stroke-width="5" opacity=".25" filter="url(#glow2)"/>')
    out.append(f'<path d="{pd}" fill="none" stroke="{GREEN}" stroke-width="1.8" stroke-linejoin="round" pathLength="1000" stroke-dasharray="1000" stroke-dashoffset="1000">'
               f'<animate attributeName="stroke-dashoffset" values="1000;0;0;0" keyTimes="0;.55;.95;1" dur="9s" repeatCount="indefinite"/></path>')
    out.append(f'<circle r="4" fill="{LIME}"><animateMotion dur="9s" repeatCount="indefinite" calcMode="linear" keyPoints="0;1;1" keyTimes="0;.55;1" path="{pd}"/>'
               f'<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;.55;.6;1" dur="9s" repeatCount="indefinite"/></circle>')
    # weekday bars
    wd = [0] * 7
    for d in [d for w in data["weeks"] for d in w]:
        wd[d["wd"]] += d["count"]
    wmx = max(wd + [1])
    names = "SMTWTFS"
    bw, bx0 = 36, 540
    for i, v in enumerate(wd):
        h = 6 + (v / wmx) * 40
        x = bx0 + i * 64
        top = i == wd.index(max(wd))
        col = LIME if top else GREEN
        out.append(f'<rect x="{x}" y="{n(358 - h)}" width="{bw}" height="{n(h)}" rx="3" fill="{col}" fill-opacity="{.85 if top else .4}" stroke="{col}" stroke-opacity=".7">'
                   f'<animate attributeName="height" values="{n(h)};{n(h * 1.12)};{n(h)}" dur="5.2s" begin="{n(i * .25)}s" repeatCount="indefinite"/>'
                   f'<animate attributeName="y" values="{n(358 - h)};{n(358 - h * 1.12)};{n(358 - h)}" dur="5.2s" begin="{n(i * .25)}s" repeatCount="indefinite"/></rect>')
        out.append(text(x + bw / 2, 372, names[i], 9, GRAY, anchor="middle"))
    out.append(text(980, 176, "weekly commits  /  rhythm by weekday", 10, GRAY, anchor="end"))
    out.append(cilia(rng, 520, 990, H - 2, -1, 40, 3, 8, .3))
    return svg_doc(W, H, "\n".join(out), "", "Vitals")


# ======================================================================= FEED
def render_feed(data):
    feed = data["feed"] or [{"repo": "—", "sha": "·······", "msg": "no recent public mutations — organism dormant", "date": ""}]
    RH = 56
    W, H = 1000, 18 + RH * len(feed)
    out = [f'<rect width="{W}" height="{H}" fill="{BG}"/>', vein_bg(W, H, 9)]
    vx = 24
    out.append(f'<path d="M{vx},0 L{vx},{H}" stroke="{GREEN}" stroke-width="3" opacity=".35"/>')
    out.append(f'<path d="M{vx},0 L{vx},{H}" stroke="{LIME}" stroke-width="2" stroke-dasharray="3 40" opacity=".9">'
               f'<animate attributeName="stroke-dashoffset" values="86;0" dur="3.2s" repeatCount="indefinite"/></path>')
    rng = random.Random(33)
    for i, e in enumerate(feed):
        y = 10 + i * RH
        c = y + 24
        fade = (f'<animate attributeName="opacity" values="0;1" dur=".7s" begin="{n(.35 * i)}s" fill="freeze"/>')
        out.append(f'<g opacity="0">{fade}'
                   f'<path d="M{vx},{c} L{vx + 26},{c}" stroke="{GREEN}" stroke-width="2" opacity=".6"/>'
                   + pustule(vx, c, 7, 5.2, i * .45, False, rng) +
                   frame(vx + 30, y, W - vx - 34, RH - 8, 8, GRAY, .35) +
                   text(vx + 48, y + 22, e["sha"], 13, GRAY) +
                   text(vx + 48 + 10 * 8.2, y + 22, clean(e["repo"], 34), 15, GREEN, "bold") +
                   text(vx + 48, y + 41, clean(e["msg"], 92), 13, SLATE) +
                   text(W - 20, y + 22, e["date"], 12, GRAY, anchor="end") +
                   '</g>')
    # scanning highlight
    out.append(f'<rect x="{vx + 30}" y="0" width="{W - vx - 34}" height="2" fill="{LIME}" opacity="0">'
               f'<animate attributeName="y" values="0;{H}" dur="6s" repeatCount="indefinite"/>'
               f'<animate attributeName="opacity" values="0;.5;.5;0" keyTimes="0;.1;.9;1" dur="6s" repeatCount="indefinite"/></rect>')
    return svg_doc(W, H, "\n".join(out), "", "Latest mutations")


# ======================================================================= MAIN
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="dist")
    ap.add_argument("--fixture", action="store_true")
    a = ap.parse_args()
    if a.fixture:
        data = fetch_fixture()
    else:
        token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
        if not token:
            sys.exit("GH_TOKEN is not set (use --fixture for synthetic data)")
        data = fetch_real(token)
    os.makedirs(a.out, exist_ok=True)
    for name, fn in (("organism", render_organism), ("vitals", render_vitals), ("feed", render_feed)):
        svg = fn(data)
        ET.fromstring(svg)  # refuse to publish malformed XML
        with open(os.path.join(a.out, f"{name}.svg"), "w", encoding="utf-8") as fh:
            fh.write(svg)
        print(f"  {name}.svg  {len(svg) // 1024} KB")
    print(f"ok: {data['total']} contributions, {len(data['feed'])} feed items")


if __name__ == "__main__":
    main()
