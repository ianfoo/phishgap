#!/usr/bin/env python3
"""
phishgap5.py -- per-song gap report for a Phish show, via the Phish.net API v5.

One call to /v5/setlists/showdate/<date>.json returns every song in the show
with its `gap` already computed, so there is no HTML parsing and no arithmetic.

    export PHISHNET_API_KEY=...            # request a key at phish.net/api
    python3 phishgap5.py 2026-07-24 --html report.html --pdf report.pdf

Or keep a growing site of them, one page per show plus a searchable index:

    python3 phishgap5.py 2026-07-22 2026-07-24 --previous --site site
    python3 phishgap5.py --site site --rebuild      # re-render after a CSS edit

Each show lands in site/<date>.html, its data is archived in site/data, and
site/index.html is regenerated from that archive every run. Dates already in
the site are skipped unless --force, so runs are additive and cheap.

Requires: stdlib only for JSON/text output. `pip install weasyprint` for --pdf.
Responses are cached on disk; phish.net asks that clients cache rather than
re-request. Use --refresh to bypass.
"""

import argparse
import contextlib
import datetime
import hashlib
import html
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request

API_ROOT = "https://api.phish.net/v5"
CACHE_TTL = 6 * 3600
DEFAULT_CACHE = os.path.expanduser("~/.cache/phishgap")

# Minimum spacing between live requests. Building a whole tour with --previous
# is a couple of hundred calls, and phish.net is a volunteer operation; the
# cache absorbs everything after the first pass, so the cost is once-only.
# 0.25s was enough to earn a 429, so pace it at well under two per second and
# back off when asked to.
MIN_INTERVAL = 0.6
MAX_TRIES = 5
_last_fetch = [0.0]

# phish.net encodes sets as 1..4 then e / e2 / e3
SET_ORDER = {"1": 0, "2": 1, "3": 2, "4": 3, "e": 4, "e2": 5, "e3": 6}
SET_LABEL = {"1": "SET 1", "2": "SET 2", "3": "SET 3", "4": "SET 4",
             "e": "ENCORE", "e2": "ENCORE 2", "e3": "ENCORE 3"}


# -------------------------------------------------------------------- api ---

class ApiError(RuntimeError):
    pass


def load_key(explicit=None):
    if explicit:
        return explicit
    env = os.environ.get("PHISHNET_API_KEY")
    if env:
        return env
    path = os.path.expanduser("~/.config/phishgap/apikey")
    if os.path.isfile(path):
        with open(path) as fh:
            return fh.read().strip()
    raise ApiError(
        "No API key. Set PHISHNET_API_KEY, pass --apikey, or write one to "
        "~/.config/phishgap/apikey. Request a key at https://phish.net/api")


def get(path, apikey, cache_dir=DEFAULT_CACHE, refresh=False, **params):
    """GET <API_ROOT>/<path>.json, cached on disk. -> list of row dicts."""
    params["apikey"] = apikey
    url = "%s/%s.json?%s" % (API_ROOT, path.strip("/"),
                             urllib.parse.urlencode(params))

    blob = None
    if cache_dir:
        os.makedirs(cache_dir, exist_ok=True)
        # key on the URL minus the apikey so the key never lands on disk
        stable = url.replace(urllib.parse.quote(apikey), "KEY")
        cache_file = os.path.join(
            cache_dir, hashlib.sha256(stable.encode()).hexdigest()[:20] + ".json")
        if not refresh and os.path.isfile(cache_file):
            if time.time() - os.path.getmtime(cache_file) < CACHE_TTL:
                with open(cache_file, encoding="utf-8") as fh:
                    blob = fh.read()

    if blob is None:
        req = urllib.request.Request(
            url, headers={"User-Agent": "phishgap/1.0 (+personal use)",
                          "Accept": "application/json"})
        for attempt in range(1, MAX_TRIES + 1):
            wait = MIN_INTERVAL - (time.time() - _last_fetch[0])
            if wait > 0:
                time.sleep(wait)
            _last_fetch[0] = time.time()
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    blob = resp.read().decode("utf-8")
                break
            except urllib.error.HTTPError as exc:
                retryable = exc.code == 429 or 500 <= exc.code < 600
                if not retryable or attempt == MAX_TRIES:
                    raise ApiError("HTTP %s from %s" % (exc.code, path)) from None
                # Honour Retry-After when the server sends one, else back off.
                try:
                    pause = float(exc.headers.get("Retry-After") or 0)
                except ValueError:
                    pause = 0.0
                pause = pause or min(30.0, 2.0 ** attempt)
                print("HTTP %s from %s, retrying in %.0fs (%d/%d)"
                      % (exc.code, path, pause, attempt, MAX_TRIES),
                      file=sys.stderr)
                time.sleep(pause)
            except urllib.error.URLError as exc:
                raise ApiError("Could not reach api.phish.net: %s"
                               % exc.reason) from None
        if cache_dir:
            with open(cache_file, "w", encoding="utf-8") as fh:
                fh.write(blob)

    try:
        payload = json.loads(blob)
    except ValueError:
        raise ApiError("Non-JSON response from %s" % path) from None
    if payload.get("error"):
        raise ApiError(payload.get("error_message") or "API reported an error")
    return payload.get("data") or []


# ------------------------------------------------------------------ model ---

def build(showdate, apikey, artist="Phish", **kw):
    rows = get("setlists/showdate/%s" % showdate, apikey, **kw)
    if not rows:
        raise ApiError("No setlist found for %s" % showdate)

    artists = {r.get("artist_name") for r in rows if r.get("artist_name")}
    if artist and len(artists) > 1:
        rows = [r for r in rows if r.get("artist_name") == artist] or rows

    rows.sort(key=lambda r: (SET_ORDER.get(str(r.get("set")), 9),
                             int(r.get("position") or 0)))

    songs, seen = [], set()
    for r in rows:
        slug = r.get("slug") or r.get("song")
        if slug in seen:
            continue          # song repeated later in the same show
        seen.add(slug)
        gap = r.get("gap")
        songs.append({
            "set": SET_LABEL.get(str(r.get("set")), "SET %s" % r.get("set")),
            "song": r.get("song") or "",
            "slug": slug,
            "gap": int(gap) if str(gap).lstrip("-").isdigit() else None,
            "jamchart": str(r.get("isjamchart")) == "1",
            "prev_date": None,
            "prev_venue": None,
            "prev_place": None,
        })

    head = rows[0]
    report = {
        "date": head.get("showdate") or showdate,
        "venue": ", ".join(p for p in (head.get("venue"), head.get("city"),
                                       head.get("state")) if p),
        # Kept apart as well, because the index lays them out separately.
        "venue_name": head.get("venue") or "",
        "city": head.get("city") or "",
        "state": head.get("state") or "",
        "artist": head.get("artist_name") or artist,
        "tour": head.get("tourname") or "",
        "notes": (head.get("setlistnotes") or "").strip(),
        "permalink": head.get("permalink") or "",
        "songs": songs,
    }
    return report


def recent_shows(apikey, days, artist="Phish", **kw):
    """Dates of shows already played within the last `days`, oldest first.

    One call per calendar year touched by the window, which is how --catch-up
    stays cheap enough to run on a schedule: most days it finds nothing new.
    """
    today = datetime.date.today()
    start = today - datetime.timedelta(days=days)
    dates = set()
    for year in sorted({start.year, today.year}):
        for row in get("shows/showyear/%d" % year, apikey, **kw):
            if artist and row.get("artist_name") != artist:
                continue
            showdate = row.get("showdate") or ""
            if start.isoformat() <= showdate <= today.isoformat():
                dates.add(showdate)
    return sorted(dates)


def add_previous(report, apikey, **kw):
    """Optional second pass: date/venue of each song's prior performance.

    Costs one call per song, so it is opt-in behind --previous.
    """
    missed = []
    for s in report["songs"]:
        try:
            hist = get("setlists/slug/%s" % s["slug"], apikey, **kw)
        except ApiError as exc:
            # Worth saying out loud: a rate limit here would otherwise just
            # render as a show whose songs quietly have no history.
            missed.append("%s (%s)" % (s["song"], exc))
            continue
        hist = [h for h in hist if h.get("showdate")]
        hist.sort(key=lambda h: h["showdate"])
        idx = next((i for i, h in enumerate(hist)
                    if h["showdate"] == report["date"]), None)
        if s["gap"] is None and idx is not None:
            g = hist[idx].get("gap")
            s["gap"] = int(g) if str(g).lstrip("-").isdigit() else None
        if idx == 0:
            s["debut"] = True          # this show IS the first performance
        prior = hist[idx - 1] if idx else (hist[-1] if idx is None and hist else None)
        if prior:
            s["prev_date"] = prior.get("showdate")
            s["prev_venue"] = prior.get("venue") or ""
            s["prev_place"] = ", ".join(
                p for p in (prior.get("city"), prior.get("state")) if p)
    if missed:
        print("warning: no history for %d of %d songs in %s: %s"
              % (len(missed), len(report["songs"]), report["date"],
                 "; ".join(missed)), file=sys.stderr)
    return report


# ----------------------------------------------------------------- render ---

def render_text(report):
    out = ["%s  --  %s" % (report["date"], report["venue"]), ""]
    width = max((len(s["song"]) for s in report["songs"]), default=10)
    current = None
    for s in report["songs"]:
        if s["set"] != current:
            current = s["set"]
            out += ["", current, "-" * (width + 24)]
        gap = "%6s" % ("{:,}".format(s["gap"]) if s["gap"] is not None else "?")
        tail = "  %s" % s["prev_date"] if s["prev_date"] else ""
        out.append("%s  %-*s%s" % (gap, width, s["song"], tail))
    gaps = [s["gap"] for s in report["songs"] if s["gap"] is not None]
    if gaps:
        out += ["", "%d songs | median %s | average %s | longest %s"
                % (len(report["songs"]), _stat(_median(gaps)),
                   _stat(sum(gaps) / len(gaps)), _stat(max(gaps)))]
    return "\n".join(out) + "\n"


# Shared by the report pages and the index, so one palette edit moves both.
PALETTE_CSS = """
:root{color-scheme:light dark;
      --paper:#f2ece0;--ink:#17150f;--ink-soft:#413c31;--rule:#c9bfa9;
      --rule-soft:rgba(201,191,169,.45);--hot:#c8371b;--cool:#4f6046;
      --dim:#877e6e;--track:rgba(23,21,15,.085);--hover:rgba(200,55,27,.055);
      --grain-blend:multiply;--grain-opacity:.45;}
/* Dark palette is scoped to `screen` so print and PDF stay on paper stock. */
@media screen and (prefers-color-scheme:dark){
  :root{--paper:#131210;--ink:#ece5d5;--ink-soft:#c4bcaa;--rule:#413a30;
        --rule-soft:rgba(236,229,213,.13);--hot:#ff6b45;--cool:#93b184;
        --dim:#948b7c;--track:rgba(236,229,213,.1);
        --hover:rgba(255,107,69,.07);
        --grain-blend:screen;--grain-opacity:.2;}
  /* A 3px cream bar blooms on near-black the way 3px of ink never does on
     paper, so the hero rule gets thinner and steps back a tone in the dark. */
  .hero{border-top-width:2px;border-top-color:#6b6353}
  /* Favicons drawn as a solid black glyph on transparency vanish here. */
  .badge img.flip{filter:invert(1)}
}
"""

CSS = PALETTE_CSS + """
*{box-sizing:border-box}
body{margin:0;padding:clamp(1.4rem,4vw,3.5rem) clamp(1rem,5vw,3rem);
     background:var(--paper);color:var(--ink);
     font-family:'IBM Plex Mono',ui-monospace,SFMono-Regular,monospace;
     font-size:15px;line-height:1.5}
.wrap{max-width:960px;margin:0 auto}
/* The header is a grid so the tour, which lives in the show line where there
   is room for it, can be lifted out to ride the breadcrumb row where there is
   not -- see the max-width block. One element either way. */
header{padding-bottom:.9rem}
.crumb{margin:0 0 1rem;font-size:.62rem;letter-spacing:.16em;
       text-transform:uppercase}
.crumb a{color:var(--dim);text-decoration:none;
         border-bottom:1px solid var(--rule)}
.crumb a:hover{color:var(--hot);border-bottom-color:var(--hot)}
h1{font-family:'Alfa Slab One',Georgia,serif;font-weight:400;
   font-size:clamp(2rem,7vw,4rem);line-height:.94;margin:0 0 .7rem;
   letter-spacing:-.02em}
h1 em{font-style:normal;color:var(--hot)}
/* Date and tour pair up: both short, so this line cannot wrap and the one
   separator on the page can be neither orphaned nor widowed. The venue is the
   variable-length part, so it gets a line to wrap inside, with no separator to
   strand at the break. */
.show{margin:0;display:flex;flex-wrap:wrap;align-items:baseline}
.show .date{font-family:'Alfa Slab One',Georgia,serif;font-size:1.5rem;
   line-height:1;color:var(--ink)}
.show .tour{font-size:.95rem;font-weight:600;letter-spacing:.07em;
   text-transform:uppercase;color:var(--dim)}
.show .tour::before{content:"\\2022";color:var(--hot);font-size:1.2rem;
   margin:0 .7rem}
.where{margin:.4rem 0 0;font-size:.95rem;font-weight:600;letter-spacing:.07em;
   text-transform:uppercase;color:var(--ink-soft)}
/* Below the stats rather than in the masthead: the header stays a tight block
   of identity, and the links get their own air on the first screen. */
.links{margin:1.1rem 0 0;display:flex;flex-wrap:wrap;gap:.4rem}
.badge{display:inline-flex;align-items:center;gap:.35rem;line-height:1;
   padding:.32rem .52rem;border:1px solid var(--rule);color:var(--dim);
   font-size:.62rem;letter-spacing:.1em;text-transform:uppercase;
   text-decoration:none;white-space:nowrap}
.badge img{display:block;width:13px;height:13px}
.badge:hover{color:var(--ink);border-color:var(--ink-soft);
   background:var(--hover)}
.hero{display:flex;flex-wrap:wrap;margin:1.1rem 0 .3rem;
      border-top:3px solid var(--ink);border-bottom:1px solid var(--rule)}
.card{flex:1 1 0;padding:.85rem 1.1rem;border-left:1px solid var(--rule)}
.card:first-child{border-left:0;padding-left:0}
.num{font-family:'Alfa Slab One',Georgia,serif;font-size:2.3rem;line-height:1;
     letter-spacing:-.01em;color:var(--ink)}
.num.hot{color:var(--hot)}
.lbl{font-size:.62rem;text-transform:uppercase;letter-spacing:.18em;
     color:var(--dim);margin-top:.4rem}
h2{font-family:'Alfa Slab One',Georgia,serif;font-weight:400;font-size:.9rem;
   letter-spacing:.1em;text-transform:uppercase;margin:2.4rem 0 .3rem;
   padding-bottom:.3rem;border-bottom:1px solid var(--rule)}
table{width:100%;border-collapse:collapse;table-layout:fixed}
col.c-gap{width:13%}
col.c-song{width:24%}
col.c-bar{width:16%}
col.c-last{width:47%}
table.no-last col.c-song{width:35%}
table.no-last col.c-bar{width:52%}
th{font-size:.62rem;text-transform:uppercase;letter-spacing:.15em;
   color:var(--dim);font-weight:500;text-align:left;padding:.45rem .6rem;
   border-bottom:1px solid var(--rule)}
th.n,td.n{text-align:right;padding-right:1.1rem;white-space:nowrap}
.gap,.song,.last .date{line-height:1.35rem}
td{padding:.5rem .6rem;border-bottom:1px solid var(--rule-soft);
   vertical-align:middle;line-height:1.35rem}
.song{font-weight:600;font-size:1rem}
.jc::after{content:"\\2022";color:var(--hot);margin-left:.4em;font-size:1.1em}
.gap{font-family:'Alfa Slab One',Georgia,serif;font-size:1.3rem;line-height:1;
     white-space:nowrap}
.gap.big{color:var(--hot)}
.gap.small{color:var(--cool)}
.bar{padding-right:1.2rem}
.bar .track{display:block;width:100%;height:7px;background:var(--track)}
.bar .fill{display:block;height:7px;background:var(--cool);min-width:2px}
.bar .fill.big{background:var(--hot)}
.last{font-size:.85rem;overflow-wrap:anywhere;vertical-align:top}
.last .date{white-space:nowrap}
/* Stacked on wide layouts, run together on narrow ones -- see the
   max-width block, which puts these back inline with separators. */
.last .date,.last .venue,.last .place{display:block}
.venue{color:var(--dim);font-size:.78rem;line-height:1.2rem}
.place{color:var(--dim);font-size:.78rem;line-height:1.2rem;white-space:nowrap}
.none{color:var(--dim);font-style:italic}
.notes{margin:2.2rem 0 0;padding:1rem 1.1rem;border-left:3px solid var(--rule);
       font-size:.84rem;color:var(--ink-soft)}
.notes a{color:var(--hot)}
footer{margin-top:2.4rem;padding-top:.9rem;border-top:1px solid var(--rule);
       font-size:.68rem;letter-spacing:.1em;text-transform:uppercase;
       color:var(--dim);display:flex;justify-content:space-between;
       flex-wrap:wrap;gap:.5rem}
@media screen{
  body::before{content:"";position:fixed;inset:0;pointer-events:none;z-index:9;
    opacity:var(--grain-opacity);mix-blend-mode:var(--grain-blend);background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='140' height='140'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='3'/></filter><rect width='140' height='140' filter='url(%23n)' opacity='.28'/></svg>")}
  .bar .fill{animation:grow .7s cubic-bezier(.2,.8,.3,1) both}
  @keyframes grow{from{transform:scaleX(0);transform-origin:left}}
  tr:hover td{background:var(--hover)}
}
/* Narrow viewports: the four-column table becomes a list of stacked rows.
   A hidden `bar` cell used to leave the table's last column empty -- the
   cells shifted left into the colgroup widths while the 47% `last` column
   kept its space -- which is why the rules stopped short of the right edge.
   Dropping table layout altogether fixes that and buys room for the venue
   and city, which no longer have to be hidden to make the columns fit. */
@media screen and (max-width:620px){
  table,tbody,tr,td{display:block}
  colgroup,thead{display:none}
  /* Wide enough for a comma'd four-digit gap in the Georgia fallback. */
  tr{display:grid;grid-template-columns:3.8rem 1fr;column-gap:.7rem;
     grid-template-areas:"gap song" "gap meta";
     padding:.5rem 0;border-bottom:1px solid var(--rule-soft)}
  td{border:0;padding:0}
  td.n{grid-area:gap;padding-right:0;align-self:start;padding-top:.1rem}
  td.song{grid-area:song}
  td.last{grid-area:meta}
  td.bar{display:none}
  .gap{font-size:1.2rem}
  .song{font-size:.95rem;line-height:1.25rem}
  .last{font-size:.72rem;line-height:1.15rem}
  .last .date,.last .venue,.last .place{display:inline}
  .last .place{white-space:normal}
  .last .venue::before,.last .place::before{content:" · ";color:var(--rule)}
  /* Same two lines, scaled down: date and tour still pair on the first one
     even at 320px, and the masthead closes up so it reads as one block rather
     than a stack of separate announcements. */
  header{padding-bottom:.55rem}
  .crumb{margin-bottom:.7rem}
  h1{margin-bottom:.45rem}
  .show .date{font-size:1.15rem}
  .show .tour{font-size:.62rem;font-weight:400;letter-spacing:.14em}
  .show .tour::before{font-size:1rem;margin:0 .5rem}
  .where{margin-top:.2rem;font-size:.72rem;letter-spacing:.05em}
  /* All three badges have to hold one line down to a 320px phone. */
  .links{margin-top:.95rem;gap:.3rem}
  .badge{font-size:.58rem;letter-spacing:.07em;padding:.3rem .45rem;gap:.3rem}
  .badge img{width:12px;height:12px}
  .card{flex:1 1 45%;padding:.65rem .55rem}
  .card:nth-child(odd){border-left:0;padding-left:0}
  .card:nth-child(n+3){border-top:1px solid var(--rule)}
  .num{font-size:1.5rem}
  .lbl{font-size:.53rem;letter-spacing:.1em}
}
@media (prefers-reduced-motion:reduce){.bar .fill{animation:none}}
@page{size:letter;margin:14mm 13mm 12mm}
@media print{
  body{padding:0;font-size:10.5pt;background:#fff}
  .crumb,.links{display:none}
  .wrap{max-width:none}
  h1{font-size:34pt}
  h2{margin-top:16pt;break-after:avoid}
  table{break-inside:auto}
  tr{break-inside:avoid}
  thead{display:table-header-group}
  footer{break-before:avoid}
}
"""

SHELL = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Gap Report &mdash; {date}</title>
<meta name="description" content="{blurb}">
<meta property="og:title" content="Gap Report &mdash; {date}">
<meta property="og:description" content="{blurb}">
<meta property="og:type" content="article">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Alfa+Slab+One&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>{css}</style></head><body><div class="wrap">
<header>{crumb}<h1>Gap <em>Report</em></h1>
<p class="show"><span class="date">{date}</span>{tour}</p>
<p class="where">{venue}</p></header>
<section class="hero">{hero}</section>
<p class="links">{links}</p>
{sections}{notes}
<footer><span>Data: Phish.net API v5</span><span>{stamp}</span></footer>
</div></body></html>
"""


# Site favicons, fetched once and inlined as 32px PNGs. Embedded rather than
# hotlinked for the same reason the fonts hurt: a page saved out of a chat has
# no network, and a badge with a broken image looks worse than no badge.
ICON_PNET = "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"
ICON_PIN = "iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAEmElEQVR42sWX225bRRSGP9uTOCS1kzZOTNykhRTaphxaECVCgifgQXgUHodH4AohAQ1QiNqS0pybkHPs2LFjO+bmG2lkodDmplva8njvmbX+9f9rrZkNb/jK9I0DkE/uAOR81wO6QBtoAafAmc8ufYVkPAAUgUlgAhgHCgLJAedAEzgGdoFNYB+o++7SDFwDhoFS4ngMGOljAR2dAVVgB3gJrAuk+YpsZBNbZICvdDxn9D2gARwCJzpMGSoBo8AQsA38BCwKpP4KjA84PgO6QQAjgsgY2T5wpM5R96ZO68A7MjULdGSoeQELbwFXvUd1/hKo5YBv1XoT+BX4EXimsaDTU+A5sASsAHsaLgDv+rsta52+nMgZ3APgC+BL4EYEG4ApoAasAb8ByyKuGGXXyfuJ4xPzYxS4I60zwKoV0kkiLwG3nHfP8Y7+Wln/bAB/qWNPY58DHxpBNTGKObKikba58baR5pN514BPgYcGlNd+NuZTSPStGm1ZlLMaqRv9WWK44/yaBoc0eEXAOdmZBT7Wed0SLhpAE2gGSy4unpCmO5bmjtr+I7VpKcWMDsk4lusVbTzwN6s8HedVZW85MtBTrylpn5WNHXWv9WX1QNI3hnXQcc2g7z7xLrs+a+7EJF4DNrMODjRasR9UpGvdRf3XiNl/S6q7OmnJ5ntJDg1Z3pOCXQIWrLpaAH7QSVbHMybLvpNO+kpqxD7wEfC+c7cNogvc9N1dnS5LeVuWTi3Tq8BwAL7zzyww7biR6H+aACgY3UNgXgbOE6mCzj9Luupx0rJriXTnQC8Af2uoJIC8i6KeUyLPA9fN6nkjLAAvNN607O7JTFZWjnyXd35ZKc6ATjBjJ4Hbdqi46xV9FlwwqjxzslV2V3wqzXnX3zaY2GyOEtkqBnSuvMfBqG9otKRejWSXnHQ86nha0E0j/1Nj40ZeMdIdde+aO8POmdb+ekzCu+p63UkbNo24LUd5BoxyxPcrwB/uhKfAB9oqOndM4LvuEZtKOmFiLwFLAbivkwkTLeo2ZsQ3NEpSbivAz8AjDZeU56ZBdAR5YCKfJEnZFtAK8DQkGVvU8a730H/U/6FJ9wj43v2jLYCKQQzq9IlnhcfanhPgoID2gK1gq4ynn7ptdy3p/RnZaFhOT9y2F6yWigDGtdMGtnT82HHBIKeUZ1B5poIG4jGpJoBnlueSWT6ssy2p25SlEZNz3MTsydIy8LtsjemjbI/pCWQemAka6UrLoYbXZWDNOwjuUOrqSUseEmDcaqtKsO78stEWnXuuVPeB2Xgqbhvhni340L4em0nGxGr37YrxcNlLtumaIOJxLkh5SHbSWCmd+LBl3W7pvJ4cQBoXHDI7MnfgHQzgOOn9TedEUBl/a0ArJNqvqu9R3+nnoqsl3S+siKrUHwjgTEnXtF+wKe05fz8HfG3SLdhYVv8n6v6ra1RZnT03CTeSj5Z4aDkWzCLwC7CYAb7xxWqS3aev8WGTS8psSMprstDS8aiZXxRow/eNjP275aKG1F3mUyvb962ZJmem7wurq8y9jCV0npznL/2d9xofwiTg3uz1L00mm/d4vOqwAAAAAElFTkSuQmCC"
ICON_FOUL = "iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAC7UlEQVR42u2Xz2tcVRTHP+e+Nz+a2MTa4Ewy0zSpq7ZiFwWhCEIRoxWULhztdBItRbKwW3fdduHfUBDFYIM/diq6cS2KoNAWwSyqTjLMpLVEW9PJzLv36yIabcvUZGZUhJztvfe8zz3nnvM9D7Zt27q0y6WD6dqLo/t79eO6Pbgrvv6qi6n0ChB3c+jq6ZGdfs3tBQ3+VHlgaLU10E7HraHc/HLjHwMQWKOcO+qJcoH4CwhDIN8meyyV1jWv1BHg3FYBbLMbGy+MHQ8Rz4I1cfKGG4TggYvIhkETmXT6tV1vfb/Stwg0KuOPBZIpF5Kvvdkxk9apxcAf6IYdwEkK0FxrTwHv9QXgyqmJrK21SxjDuMxuk0+tZ+LO1ChCLoIgRyj2rQqySfu5gHZuxZlwe+ozucG7IlkuHKmVi9ObArj2UrFQr4yedcGPb/U2QmlH/Iz+8rbqM7lJmZ1wCo83pguH7gmg2cOpJPEvI5sMcpNdFbbXU8snR6c2fPr4aUkxDieFE9VScUdHgKutH3dj0UO9NJYgLDj3qMA0eziFNPHnavRgKq0nOgIkSfp0X/p00D5KxezSzfpBYOSO1UMdAeIQdvRNLLJt5wjRXe/ElHQEaGfsvBS+6/Xbhi0w11hNx1EdY+224MC3HQEKb9aqKHwUgvmeFE66YaCRtxeXTNrojGb6OTL/2T3LcHS+ftlMK13dXCTAApH7ZCPkkRYAFGhK9lV+rvHr33dCs0+Rnse4CQxtnsBCfn7p9dty7t2HjjCcRO6D4juLi5sWo5WZvZPNVhhUlJxxFvsgP4AQWNNMGczZ72IEuAgFefi8cKH2Rl9a8f1zP1zJv1u95MwuAjhjtcPWWxJVgNh0ve9yrBJR1e3ZT5ZbUcvPOuw+M9pgERYyJt1wRtXLHs5fqL3S94HE3sdD9RLA8snCvBfTgo9BRw3yMvuyZXwD/pd/bRhdV7jxJ+uVsfONcvGR/2QqVomoUR47vv1/sG3/e/sNrEkrwQ1sbIcAAAAASUVORK5CYII="

# Last field flags an icon that is solid black on transparency, which needs
# inverting to survive the dark palette.
SHOW_LINKS = (
    ("phish.net", "https://phish.net/setlist/?d=%s", ICON_PNET, False),
    ("phish.in", "https://phish.in/%s", ICON_PIN, True),
    ("fouldomain", "https://fouldomain.com/shows/%s", ICON_FOUL, False),
)


def _show_links(date):
    """Badge links out to the sites that hold the rest of the story."""
    return "".join(
        "<a class='badge' href='%s' target='_blank' rel='noopener noreferrer'>"
        "<img class='%s' src='data:image/png;base64,%s' alt='' "
        "width='13' height='13'><span>%s</span></a>"
        % (url % date, "flip" if flip else "", icon, label)
        for label, url, icon, flip in SHOW_LINKS)


def _median(vals):
    ordered = sorted(vals)
    n = len(ordered)
    if not n:
        return None
    mid = n // 2
    return ordered[mid] if n % 2 else (ordered[mid - 1] + ordered[mid]) / 2


def _stat(value):
    """Thousands separators, and no trailing .0 on whole numbers."""
    if value is None:
        return "n/a"
    return ("{:,}".format(int(value)) if float(value).is_integer()
            else "{:,.1f}".format(value))


BAR_SCALES = ("linear", "sqrt", "log")


def _bar_pct(gap, biggest, scale="linear"):
    """Bar length as a percentage of the longest gap in the show.

    Linear by default, because the bar's only job is comparing magnitudes.
    A log scale badly flatters mid-range values: against a 1,170 maximum it
    draws 531 at 89% of full width when the value is 45% of it, which makes
    the bars look arbitrary next to the numbers printed right beside them.
    """
    if not biggest or not gap:
        return 0.0
    if scale == "log":
        return math.log10(gap + 1) / math.log10(biggest + 1) * 100
    if scale == "sqrt":
        return math.sqrt(gap) / math.sqrt(biggest) * 100
    return gap / biggest * 100


def render_html(report, bar_scale="linear", index_href=None):
    allg = [s["gap"] for s in report["songs"] if s["gap"] is not None]
    biggest = max(allg) if allg else 0
    avg = _stat(sum(allg) / len(allg)) if allg else "n/a"
    med = _stat(_median(allg))
    longest = _stat(biggest) if allg else "n/a"
    show_last = any(s["prev_date"] for s in report["songs"])

    hero = "".join(
        "<div class='card'><div class='num%s'>%s</div>"
        "<div class='lbl'>%s</div></div>" % (cls, val, lbl)
        for val, lbl, cls in (
            (len(report["songs"]), "Songs Played", ""),
            (longest, "Longest Gap", " hot"),
            (med, "Median Gap", ""),
            (avg, "Average Gap", ""),
        ))

    sections, rows, current = [], [], None

    def flush():
        if current is None:
            return
        cols = ("<colgroup><col class='c-gap'><col class='c-song'>"
                "<col class='c-bar'>"
                + ("<col class='c-last'>" if show_last else "")
                + "</colgroup>")
        head = ("<th class='n'>Gap</th><th>Song</th><th></th>"
                + ("<th>Last Performed</th>" if show_last else ""))
        sections.append("<h2>%s</h2>\n<table%s>%s<thead><tr>%s</tr></thead>"
                        "<tbody>\n%s\n</tbody></table>"
                        % (html.escape(current),
                           "" if show_last else " class='no-last'",
                           cols, head, "\n".join(rows)))

    for s in report["songs"]:
        if s["set"] != current:
            flush()
            current, rows = s["set"], []
        g = s["gap"]
        klass = "big" if (g or 0) >= 50 else "small"
        if g is None:
            gap_cell = "<span class='gap none'>&mdash;</span>"
            bar = "<td class='bar'></td>"
        else:
            gap_cell = "<span class='gap %s'>%s</span>" % (klass, "{:,}".format(g))
            pct = _bar_pct(g, biggest, bar_scale)
            bar = ("<td class='bar'><span class='track'>"
                   "<span class='fill %s' style='width:%.2f%%'></span>"
                   "</span></td>" % (klass, pct))
        cells = "<td class='n'>%s</td><td class='song%s'>%s</td>%s" % (
            gap_cell, " jc" if s["jamchart"] else "",
            html.escape(s["song"]), bar)
        if show_last:
            if s["prev_date"]:
                # No <br>: the spans are blocks on wide layouts and inline on
                # narrow ones, so CSS alone decides how they stack. Empty ones
                # are dropped rather than left to grow a stray separator.
                bits = ["<span class='date'>%s</span>" % s["prev_date"]]
                for cls, text in (("venue", s["prev_venue"]),
                                  ("place", s.get("prev_place"))):
                    if text:
                        bits.append("<span class='%s'>%s</span>"
                                    % (cls, html.escape(text)))
                cells += "<td class='last'>%s</td>" % "".join(bits)
            elif s.get("debut"):
                cells += "<td class='last'><span class='none'>debut</span></td>"
            else:
                cells += "<td class='last'></td>"
        rows.append("<tr>%s</tr>" % cells)
    flush()

    notes = ""
    if report.get("notes"):
        notes = "<div class='notes'>%s</div>" % report["notes"]

    crumb = ""
    if index_href:
        crumb = ("<nav class='crumb'><a href='%s'>&larr; All reports</a></nav>"
                 % html.escape(index_href, quote=True))

    # What a chat client shows when someone drops the link in a thread. Plain
    # text, entities and all, because html.escape has the last word on it.
    blurb = "%s · %d songs" % (report["venue"], len(report["songs"]))
    if allg:
        blurb += " · longest gap %s (%s)" % (
            longest, next((s["song"] for s in report["songs"]
                           if s["gap"] == biggest), ""))

    # phish.net files one-offs under "Not Part of a Tour", which is not worth
    # saying out loud.
    tour = report.get("tour") or ""
    tour = ("<span class='tour'>%s</span>" % html.escape(tour)
            if tour and "not part of a tour" not in tour.lower() else "")

    return SHELL.format(
        css=CSS, date=html.escape(report["date"]), crumb=crumb, tour=tour,
        venue=html.escape(report["venue"]), hero=hero,
        links=_show_links(report["date"]), blurb=html.escape(blurb, quote=True),
        sections="\n".join(sections), notes=notes,
        stamp=time.strftime("Generated %Y-%m-%d"))


# ------------------------------------------------------------------ index ---

INDEX_CSS = PALETTE_CSS + """
*{box-sizing:border-box}
body{margin:0;padding:clamp(1.4rem,4vw,3.5rem) clamp(1rem,5vw,3rem);
     background:var(--paper);color:var(--ink);
     font-family:'IBM Plex Mono',ui-monospace,SFMono-Regular,monospace;
     font-size:15px;line-height:1.5}
.wrap{max-width:960px;margin:0 auto}
h1{font-family:'Alfa Slab One',Georgia,serif;font-weight:400;
   font-size:clamp(2rem,7vw,4rem);line-height:.94;margin:0 0 .7rem;
   letter-spacing:-.02em}
h1 em{font-style:normal;color:var(--hot)}
header{padding-bottom:.9rem}
.show{margin:0;font-size:.95rem;font-weight:600;letter-spacing:.07em;
      text-transform:uppercase;color:var(--ink-soft)}
.hero{display:flex;flex-wrap:wrap;margin:1.1rem 0 .3rem;
      border-top:3px solid var(--ink);border-bottom:1px solid var(--rule)}
.card{flex:1 1 0;padding:.85rem 1.1rem;border-left:1px solid var(--rule)}
.card:first-child{border-left:0;padding-left:0}
.num{font-family:'Alfa Slab One',Georgia,serif;font-size:2.3rem;line-height:1;
     letter-spacing:-.01em}
.num.hot{color:var(--hot)}
.lbl{font-size:.62rem;text-transform:uppercase;letter-spacing:.18em;
     color:var(--dim);margin-top:.4rem}
.tools{display:flex;flex-wrap:wrap;align-items:center;gap:.55rem .8rem;
       margin:1.9rem 0 .9rem}
.search{flex:1 1 15rem;min-width:0;font:inherit;font-size:.9rem;
        padding:.5rem .7rem;border:1px solid var(--rule);border-radius:0;
        background:transparent;color:var(--ink)}
.search::placeholder{color:var(--dim)}
.search:focus-visible,.chip:focus-visible,.sort:focus-visible{
  outline:2px solid var(--hot);outline-offset:1px}
.chips{display:flex;flex-wrap:wrap;gap:.3rem}
.chip{font:inherit;font-size:.6rem;letter-spacing:.14em;text-transform:uppercase;
      padding:.42rem .6rem;border:1px solid var(--rule);background:transparent;
      color:var(--dim);cursor:pointer}
.chip:hover{color:var(--ink)}
.chip.on{background:var(--ink);color:var(--paper);border-color:var(--ink)}
.sort{font:inherit;font-size:.7rem;padding:.4rem .3rem;background:transparent;
      color:var(--ink);border:1px solid var(--rule);border-radius:0}
.count{font-size:.6rem;letter-spacing:.14em;text-transform:uppercase;
       color:var(--dim);margin-left:auto}
.count b{font-family:'Alfa Slab One',Georgia,serif;font-weight:400;
         font-size:.95rem;color:var(--ink)}
.reports{list-style:none;margin:0;padding:0;border-top:1px solid var(--rule)}
.row{display:grid;grid-template-columns:7.2rem 1fr auto;column-gap:1.1rem;
     align-items:baseline;padding:.7rem .25rem;text-decoration:none;
     color:inherit;border-bottom:1px solid var(--rule-soft)}
.row:hover{background:var(--hover)}
.r-date{font-family:'Alfa Slab One',Georgia,serif;font-size:1.05rem;
        line-height:1.3rem;white-space:nowrap}
.r-venue{font-size:.85rem;font-weight:600;letter-spacing:.04em;
         text-transform:uppercase;line-height:1.3rem}
.r-place{display:block;color:var(--dim);font-size:.75rem;line-height:1.15rem}
.r-stats{font-size:.7rem;color:var(--dim);text-align:right;white-space:nowrap;
         line-height:1.3rem}
.r-stats b{font-family:'Alfa Slab One',Georgia,serif;font-weight:400;
           font-size:.95rem;color:var(--ink)}
.r-stats b.hot{color:var(--hot)}
.r-song{display:block;font-size:.7rem;color:var(--dim)}
.empty{margin:2rem 0;font-size:.85rem;color:var(--dim);font-style:italic}
footer{margin-top:2.4rem;padding-top:.9rem;border-top:1px solid var(--rule);
       font-size:.68rem;letter-spacing:.1em;text-transform:uppercase;
       color:var(--dim);display:flex;justify-content:space-between;
       flex-wrap:wrap;gap:.5rem}
@media screen{
  body::before{content:"";position:fixed;inset:0;pointer-events:none;z-index:9;
    opacity:var(--grain-opacity);mix-blend-mode:var(--grain-blend);background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='140' height='140'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='3'/></filter><rect width='140' height='140' filter='url(%23n)' opacity='.28'/></svg>")}
}
/* Same lesson as the report tables: stack instead of squeezing columns, so
   the rules still run the full width and nothing has to be hidden. */
@media screen and (max-width:620px){
  .row{grid-template-columns:1fr;column-gap:0;row-gap:.15rem;padding:.6rem 0}
  .r-stats{text-align:left;white-space:normal}
  .r-song{display:inline}
  .r-song::before{content:" ("}
  .r-song::after{content:")"}
  .card{flex:1 1 45%;padding:.65rem .55rem}
  .card:nth-child(odd){border-left:0;padding-left:0}
  .card:nth-child(n+3){border-top:1px solid var(--rule)}
  .num{font-size:1.5rem}
  .lbl{font-size:.53rem;letter-spacing:.1em}
  .show{font-size:.72rem;letter-spacing:.05em}
  .count{margin-left:0}
}
"""

# Filtering is progressive enhancement: the rows are in the HTML, so the page
# is a complete list with JavaScript off. The haystack lives in a data
# attribute per row, which keeps the page one file with nothing to fetch.
INDEX_JS = """
(function(){
  var list=document.getElementById('list');
  if(!list) return;
  var rows=Array.prototype.slice.call(list.children);
  var q=document.getElementById('q'), sort=document.getElementById('sort'),
      shown=document.getElementById('shown'), empty=document.getElementById('empty'),
      chips=Array.prototype.slice.call(document.querySelectorAll('.chip')),
      year='';
  function apply(){
    var terms=q.value.toLowerCase().split(/\\s+/).filter(Boolean), n=0;
    rows.forEach(function(r){
      var hay=r.getAttribute('data-search'), ok=terms.every(function(t){
        return hay.indexOf(t)>-1;
      });
      if(ok&&year) ok=r.getAttribute('data-year')===year;
      r.hidden=!ok;
      if(ok) n++;
    });
    shown.textContent=n;
    empty.hidden=n>0;
  }
  function order(){
    var k=sort.value;
    rows.slice().sort(function(a,b){
      if(k==='gap') return b.getAttribute('data-longest')-a.getAttribute('data-longest');
      var x=a.getAttribute('data-date'), y=b.getAttribute('data-date');
      return k==='oldest' ? x.localeCompare(y) : y.localeCompare(x);
    }).forEach(function(r){ list.appendChild(r); });
  }
  q.addEventListener('input', apply);
  sort.addEventListener('change', order);
  chips.forEach(function(c){
    c.addEventListener('click', function(){
      year = c.classList.contains('on') ? '' : c.getAttribute('data-year');
      chips.forEach(function(o){ o.classList.toggle('on', o.getAttribute('data-year')===year); });
      apply();
    });
  });
  document.addEventListener('keydown', function(e){
    if(e.key==='/' && document.activeElement!==q){ e.preventDefault(); q.focus(); }
    if(e.key==='Escape' && document.activeElement===q){ q.value=''; apply(); q.blur(); }
  });
  q.disabled=false; sort.disabled=false;
  chips.forEach(function(c){ c.disabled=false; });
  apply();
})();
"""

INDEX_SHELL = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Phish Gap Reports</title>
<meta name="description" content="{blurb}">
<meta property="og:title" content="Phish Gap Reports">
<meta property="og:description" content="{blurb}">
<meta property="og:type" content="website">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Alfa+Slab+One&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>{css}</style></head><body><div class="wrap">
<header><h1>Gap <em>Reports</em></h1>
<p class="show">{subtitle}</p></header>
<section class="hero">{hero}</section>
<div class="tools">
<input id="q" class="search" type="search" autocomplete="off" disabled
       placeholder="Search date, venue, city, song&hellip;" aria-label="Search reports">
<div class="chips">{years}</div>
<label class="count" for="sort">Sort
<select id="sort" class="sort" disabled>
<option value="newest">Newest</option><option value="oldest">Oldest</option>
<option value="gap">Longest gap</option></select></label>
<span class="count"><b id="shown">{count}</b> of {count} shows</span>
</div>
<ol class="reports" id="list">
{rows}
</ol>
<p class="empty" id="empty" hidden>No shows match that search.</p>
<footer><span>Data: Phish.net API v5</span><span>{stamp}</span></footer>
</div><script>{js}</script></body></html>
"""


def summarize(report):
    """The handful of fields the index needs out of a full report."""
    gaps = [s["gap"] for s in report["songs"] if s["gap"] is not None]
    longest = max(gaps) if gaps else None
    titles = [s["song"] for s in report["songs"]]
    venue, place = report.get("venue_name"), ", ".join(
        p for p in (report.get("city"), report.get("state")) if p)
    if not venue:
        # Reports saved before venue/city/state were split out on their own.
        parts = [p.strip() for p in (report.get("venue") or "").split(",")]
        venue, place = (parts[0] if parts else ""), ", ".join(parts[1:])
    return {
        "date": report["date"],
        "venue": venue,
        "place": place,
        "tour": report.get("tour") or "",
        "songs": len(report["songs"]),
        "median": _median(gaps),
        "longest": longest,
        "longest_song": next((s["song"] for s in report["songs"]
                              if s["gap"] == longest), "") if gaps else "",
        "titles": titles,
    }


def render_index(reports, page_href="./%s.html"):
    """A single self-contained index page over every saved report."""
    entries = sorted((summarize(r) for r in reports),
                     key=lambda e: e["date"], reverse=True)

    rows = []
    for e in entries:
        # Everything worth searching, flattened into one lowercase haystack.
        hay = " ".join([e["date"], e["venue"], e["place"], e["tour"]]
                       + e["titles"]).lower()
        stats = "<b>%d</b> songs" % e["songs"]
        if e["longest"] is not None:
            stats += (" &middot; median <b>%s</b> &middot; longest "
                      "<b class='hot'>%s</b><span class='r-song'>%s</span>"
                      % (_stat(e["median"]), _stat(e["longest"]),
                         html.escape(e["longest_song"])))
        rows.append(
            "<li data-date='%s' data-year='%s' data-longest='%d' data-search=\"%s\">"
            "<a class='row' href='%s'>"
            "<span class='r-date'>%s</span>"
            "<span class='r-where'><span class='r-venue'>%s</span>"
            "<span class='r-place'>%s</span></span>"
            "<span class='r-stats'>%s</span></a></li>"
            % (e["date"], e["date"][:4], e["longest"] or 0,
               html.escape(hay, quote=True),
               html.escape(page_href % e["date"], quote=True),
               e["date"], html.escape(e["venue"]), html.escape(e["place"]),
               stats))

    # A lone year chip filters nothing, and it crowds the search box on a
    # phone, so the chips only appear once there is more than one year.
    years = sorted({e["date"][:4] for e in entries}, reverse=True)
    chips = "" if len(years) < 2 else "".join(
        "<button class='chip' type='button' disabled data-year='%s'>%s</button>"
        % (y, y) for y in years)

    every = [g for e in entries for g in ([e["longest"]] if e["longest"] else [])]
    hero = "".join(
        "<div class='card'><div class='num%s'>%s</div>"
        "<div class='lbl'>%s</div></div>" % (cls, val, lbl)
        for val, lbl, cls in (
            (len(entries), "Reports", ""),
            (_stat(max(every)) if every else "n/a", "Longest Gap", " hot"),
            ("{:,}".format(sum(e["songs"] for e in entries)), "Songs Logged", ""),
            (len({e["venue"] for e in entries if e["venue"]}), "Venues", ""),
        ))

    plural = "" if len(entries) == 1 else "s"
    if entries:
        span = ("%s &rarr; %s" % (entries[-1]["date"], entries[0]["date"])
                if len(entries) > 1 else entries[0]["date"])
        subtitle = "%d report%s &middot; %s" % (len(entries), plural, span)
        blurb = "Per-song gaps for %d Phish show%s, %s to %s." % (
            len(entries), plural, entries[-1]["date"], entries[0]["date"])
    else:
        subtitle, blurb = "No reports yet", "Per-song gaps for Phish shows."

    return INDEX_SHELL.format(
        css=INDEX_CSS, js=INDEX_JS, hero=hero, years=chips,
        count=len(entries), rows="\n".join(rows) or "",
        subtitle=subtitle, blurb=html.escape(blurb, quote=True),
        stamp=time.strftime("Updated %Y-%m-%d"))


# ------------------------------------------------------------------- site ---

def site_paths(site_dir, date):
    return (os.path.join(site_dir, "%s.html" % date),
            os.path.join(site_dir, "data", "%s.json" % date))


def archived_dates(site_dir):
    data_dir = os.path.join(site_dir, "data")
    if not os.path.isdir(data_dir):
        return set()
    return {n[:-5] for n in os.listdir(data_dir) if n.endswith(".json")}


def saved_reports(site_dir):
    """Every report JSON already in the site, oldest first."""
    data_dir = os.path.join(site_dir, "data")
    out = []
    for name in sorted(os.listdir(data_dir) if os.path.isdir(data_dir) else []):
        if not name.endswith(".json"):
            continue
        with open(os.path.join(data_dir, name), encoding="utf-8") as fh:
            try:
                out.append(json.load(fh))
            except ValueError:
                print("warning: skipping unreadable %s" % name, file=sys.stderr)
    return out


def write_site(site_dir, reports, bar_scale="linear", rebuild=False):
    """Add reports to the site and rebuild the index around them.

    The JSON sidecar in data/ is the archive: it is what lets --rebuild
    re-render every page after a template change without touching the API.
    """
    os.makedirs(os.path.join(site_dir, "data"), exist_ok=True)
    for report in reports:
        page, blob = site_paths(site_dir, report["date"])
        with open(blob, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2)
        with open(page, "w", encoding="utf-8") as fh:
            fh.write(render_html(report, bar_scale=bar_scale,
                                 index_href="./index.html"))
        print("wrote %s" % page, file=sys.stderr)

    known = saved_reports(site_dir)
    if rebuild:
        fresh = {r["date"] for r in reports}
        for report in known:
            if report["date"] in fresh:
                continue          # just written above
            page, _ = site_paths(site_dir, report["date"])
            with open(page, "w", encoding="utf-8") as fh:
                fh.write(render_html(report, bar_scale=bar_scale,
                                     index_href="./index.html"))
            print("rebuilt %s" % page, file=sys.stderr)

    index = os.path.join(site_dir, "index.html")
    with open(index, "w", encoding="utf-8") as fh:
        fh.write(render_index(known))
    # Serve the directory verbatim on GitHub Pages, Jekyll out of the way.
    open(os.path.join(site_dir, ".nojekyll"), "a").close()
    print("wrote %s (%d report%s)"
          % (index, len(known), "" if len(known) == 1 else "s"), file=sys.stderr)
    return index


PDF_MAX_IN = 200.0        # PDF user-space ceiling: 14400 units = 200in


def _page_count(data):
    """Page count, or None if it genuinely cannot be determined.

    Never guess here. An earlier version returned 1 on failure, which the
    fitting search read as "it fits" and happily shrank the page to its floor,
    producing dozens of tiny pages. Unknown has to stay unknown.
    """
    try:
        import io
        from pypdf import PdfReader
        return len(PdfReader(io.BytesIO(data)).pages)
    except ImportError:
        pass
    except Exception:                                 # noqa: BLE001
        return None
    if b"/ObjStm" in data:
        return None          # page objects live inside compressed streams
    import re as _re
    return len(_re.findall(rb"/Type\s*/Page(?!\w)", data)) or None


def _page_css(height_in, width_in=8.5, margin="12mm"):
    return "@page{size:%.4gin %.4gin;margin:%s}" % (width_in, height_in, margin)


def _with_page_css(markup, css):
    """Author-level injection.

    WeasyPrint's render(stylesheets=...) are *user* stylesheets, which lose to
    the document's own @page rule, so the override goes into the markup.
    """
    tag = "<style>%s</style>" % css
    return (markup.replace("</head>", tag + "</head>", 1)
            if "</head>" in markup else tag + markup)


MIN_PAGE_IN = 3.0         # no real report legitimately fits under this


def fit_single_page(pages_at, tolerance=0.08):
    """pages_at(height_in) -> page count, or None when it cannot be measured.

    Grows the page until the content lands on one sheet, then binary searches
    downward for the shortest height that still fits. Returns that height, or
    None if one page is unreachable or the count cannot be trusted.
    """
    hi = 22.0
    while True:
        count = pages_at(hi)
        if count is None:
            return None                    # refuse to search blind
        if count == 1:
            break
        if hi >= PDF_MAX_IN:
            return None
        hi = min(hi * 2, PDF_MAX_IN)

    lo = MIN_PAGE_IN
    if pages_at(lo) == 1:
        return lo                          # genuinely tiny document
    while hi - lo > tolerance:
        mid = (lo + hi) / 2
        count = pages_at(mid)
        if count is None:
            return None
        if count == 1:
            hi = mid
        else:
            lo = mid
    return hi


@contextlib.contextmanager
def _muted_stderr():
    """Silence fd 2 for the duration.

    WeasyPrint prints a multi-line installation banner straight to stderr when
    its native libs are missing, before raising. On macOS that import is never
    going to work from a venv, so the banner is noise on every single run.
    Muting the fd catches it whether it comes from Python or the C layer.
    """
    saved = os.dup(2)
    try:
        with open(os.devnull, "w") as null:
            os.dup2(null.fileno(), 2)
        yield
    finally:
        os.dup2(saved, 2)
        os.close(saved)


def _pdf_via_module(markup, path, base_url, single_page=False):
    with _muted_stderr():
        from weasyprint import HTML       # raises OSError on missing dylibs

    def doc(css=""):
        return HTML(string=_with_page_css(markup, css) if css else markup,
                    base_url=base_url)

    if not single_page:
        doc().write_pdf(path)
        return
    # exact count straight from the layout tree, no PDF parsing involved
    height = fit_single_page(lambda h: len(doc(_page_css(h)).render().pages))
    if height is None:
        raise RuntimeError("could not fit one page under %gin" % PDF_MAX_IN)
    doc(_page_css(height)).write_pdf(path)


def _in_current_env(path):
    """True if path lives inside the running venv/interpreter prefix."""
    try:
        real = os.path.realpath(path)
    except OSError:
        return False
    prefixes = {os.path.realpath(p) for p in (sys.prefix, sys.exec_prefix)
                if p}
    return any(real.startswith(p + os.sep) for p in prefixes)


# Packaged installs (brew, macports, apt) link their native libs correctly.
# A weasyprint on PATH may instead be the venv's own copy -- the exact one
# that already failed to import -- so those are skipped.
CLI_CANDIDATES = (
    "/opt/homebrew/bin/weasyprint",     # Homebrew, Apple silicon
    "/usr/local/bin/weasyprint",        # Homebrew, Intel
    "/opt/local/bin/weasyprint",        # MacPorts
    "/usr/bin/weasyprint",              # apt
)


def _weasyprint_clis():
    seen, out = set(), []
    for cand in CLI_CANDIDATES:
        if os.path.isfile(cand) and os.access(cand, os.X_OK):
            seen.add(os.path.realpath(cand))
            out.append(cand)
    found = shutil.which("weasyprint")
    if found and os.path.realpath(found) not in seen \
            and not _in_current_env(found):
        out.append(found)
    return out


def _pdf_via_weasyprint_cli(markup, path, base_url, single_page=False):
    """Packaged weasyprint CLIs run in the environment their packager built.

    That sidesteps the dlopen failure that hits an importable module inside a
    venv -- but only if we skip the venv's own CLI, which shares the fault.
    """
    exes = _weasyprint_clis()
    if not exes:
        raise FileNotFoundError(
            "no weasyprint CLI outside this venv (checked %s)"
            % ", ".join(CLI_CANDIDATES))
    last = None
    for exe in exes:
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, "report.html")
            with open(src, "w", encoding="utf-8") as fh:
                fh.write(markup)
            out = os.path.join(tmp, "out.pdf")

            def run(css="", uncompressed=False, _exe=exe, _src=src, _out=out):
                doc = _with_page_css(markup, css) if css else markup
                with open(_src, "w", encoding="utf-8") as fh2:
                    fh2.write(doc)
                cmd = [_exe, "--base-url", base_url]
                if uncompressed:
                    # keeps page objects out of compressed streams so they
                    # stay countable without pypdf
                    cmd.append("--uncompressed-pdf")
                subprocess.run(cmd + [_src, _out], check=True,
                               capture_output=True, timeout=180)
                with open(_out, "rb") as fh2:
                    return fh2.read()

            try:
                if single_page:
                    height = fit_single_page(
                        lambda h: _page_count(run(_page_css(h), True)))
                    if height is None:
                        raise RuntimeError(
                            "could not fit one page under %gin" % PDF_MAX_IN)
                    data = run(_page_css(height))
                else:
                    data = run()
                with open(path, "wb") as fh:
                    fh.write(data)
                return
            except subprocess.CalledProcessError as exc:
                last = exc
    raise last


# Chrome has no single-page switch, so the document measures itself and sets
# @page before printing. Needs preferCSSPageSize, which --print-to-pdf honours.
MEASURE_JS = """<script>
(function(){
  var d=document.documentElement, b=document.body;
  var h=Math.max(b.scrollHeight,d.scrollHeight,b.offsetHeight,d.offsetHeight);
  var s=document.createElement('style');
  s.textContent='@page{size:8.5in '+((h/96)+0.4).toFixed(3)+'in;margin:12mm}';
  document.head.appendChild(s);
})();
</script>"""

CHROME_CANDIDATES = (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    "google-chrome", "chromium", "chromium-browser", "msedge",
)


def _pdf_via_chrome(markup, path, base_url, single_page=False):
    exe = next((c for c in CHROME_CANDIDATES
                if os.path.isfile(c) or shutil.which(c)), None)
    if not exe:
        raise FileNotFoundError("no Chrome-family browser found")
    exe = exe if os.path.isfile(exe) else shutil.which(exe)
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "report.html")
        if single_page:
            markup = markup.replace("</body>", MEASURE_JS + "</body>")
        with open(src, "w", encoding="utf-8") as fh:
            fh.write(markup)
        proc = subprocess.run(
            [exe, "--headless", "--disable-gpu", "--no-sandbox",
             "--no-pdf-header-footer",
             "--virtual-time-budget=4000",       # let the webfonts arrive
             "--user-data-dir=" + os.path.join(tmp, "profile"),
             "--print-to-pdf=" + os.path.abspath(path),
             "file://" + src],
            capture_output=True, timeout=180)
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or b"").decode("utf-8", "replace")
                           .strip() or "browser exited %d" % proc.returncode)


def _looks_like_pdf(path):
    try:
        if os.path.getsize(path) < 1024:
            return False
        with open(path, "rb") as fh:
            return fh.read(5) == b"%PDF-"
    except OSError:
        return False


PDF_BACKENDS = (
    ("module", _pdf_via_module),
    ("cli", _pdf_via_weasyprint_cli),
    ("browser", _pdf_via_chrome),
)

BACKEND_HELP = {
    "module": "weasyprint python module",
    "cli": "weasyprint command-line binary",
    "browser": "headless chrome/chromium/edge/brave",
}


def write_pdf(markup, path, base_url=None, prefer=None, single_page=False):
    """Try each backend in turn, verifying real PDF bytes before accepting.

    Each backend renders to a scratch file. A backend that exits cleanly but
    writes nothing (or writes non-PDF bytes) counts as a failure, and the
    destination is only replaced once the output is confirmed good.
    """
    base_url = base_url or (os.getcwd() + os.sep)
    backends = PDF_BACKENDS
    if prefer:
        backends = [b for b in PDF_BACKENDS if b[0] == prefer] or PDF_BACKENDS
    problems = []
    scratch_dir = os.path.dirname(os.path.abspath(path)) or "."
    for name, fn in backends:
        fd, scratch = tempfile.mkstemp(suffix=".pdf", dir=scratch_dir)
        os.close(fd)
        os.unlink(scratch)
        try:
            fn(markup, scratch, base_url, single_page)
            if not _looks_like_pdf(scratch):
                raise RuntimeError("produced no usable PDF")
            if single_page:
                with open(scratch, "rb") as fh:
                    n = _page_count(fh.read())
                if n is not None and n != 1:
                    raise RuntimeError("asked for one page, got %d" % n)
            shutil.move(scratch, path)
            return name
        except Exception as exc:                      # noqa: BLE001
            detail = getattr(exc, "stderr", b"") or b""
            if isinstance(detail, bytes):
                detail = detail.decode("utf-8", "replace")
            first = next((ln for ln in detail.strip().splitlines()
                          if ln.strip() and not ln.startswith("-")), "")
            problems.append("  %-8s %-34s %s" % (
                name, BACKEND_HELP[name],
                ("%s: %s" % (type(exc).__name__, first or str(exc)))[:110]))
        finally:
            if os.path.exists(scratch):
                os.unlink(scratch)
    raise ApiError(
        "No working PDF backend. Tried:\n%s\n\n"
        "Options:\n"
        "  brew install weasyprint   the cli backend then needs no venv\n"
        "  --html out.html           then Cmd-P in your browser; the print\n"
        "                            stylesheet is already in the document"
        % "\n".join(problems))


# ------------------------------------------------------------------- main ---

def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("showdate", nargs="*", metavar="SHOWDATE",
                    help="one or more show dates, YYYY-MM-DD")
    ap.add_argument("--apikey", help="overrides PHISHNET_API_KEY")
    ap.add_argument("--artist", default="Phish",
                    help="artist filter when a date has multiple (default Phish)")
    ap.add_argument("--previous", action="store_true",
                    help="also fetch each song's prior performance "
                         "(one extra API call per song)")
    ap.add_argument("--site", metavar="DIR",
                    help="add each show to DIR as DIR/<date>.html, archive the "
                         "data in DIR/data, and regenerate DIR/index.html")
    ap.add_argument("--force", action="store_true",
                    help="with --site, re-fetch dates the site already has")
    ap.add_argument("--rebuild", action="store_true",
                    help="with --site, re-render every archived report "
                         "(use after a template change; no API calls)")
    ap.add_argument("--catch-up", nargs="?", type=int, const=21, metavar="DAYS",
                    help="with --site, add every show played in the last DAYS "
                         "(default 21) that the site does not have yet")
    ap.add_argument("--html", help="write an HTML report here")
    ap.add_argument("--pdf", help="write a PDF report here")
    ap.add_argument("--bar-scale", choices=BAR_SCALES, default="linear",
                    metavar="{linear,sqrt,log}",
                    help="bar length scaling (default linear)")
    ap.add_argument("--single-page", action="store_true",
                    help="one continuous page, no page breaks")
    ap.add_argument("--pdf-backend", choices=("module", "cli", "browser"),
                    metavar="{module,cli,browser}",
                    help="force one PDF backend instead of trying each")
    ap.add_argument("--json", help="write the raw report here")
    ap.add_argument("--cache-dir", default=DEFAULT_CACHE)
    ap.add_argument("--refresh", action="store_true", help="bypass the cache")
    ap.add_argument("--from-json", help="render a saved --json file, no API call")
    args = ap.parse_args()

    one_file = next((f for f in ("html", "pdf", "json")
                     if getattr(args, f)), None)
    if one_file and len(args.showdate) > 1:
        sys.exit("error: --%s names a single file; use --site DIR to render "
                 "several dates at once" % one_file)
    if (args.rebuild or args.force or args.catch_up) and not args.site:
        sys.exit("error: --rebuild, --force and --catch-up need --site DIR")
    if not (args.showdate or args.from_json or args.rebuild or args.catch_up):
        sys.exit("error: give at least one show date (YYYY-MM-DD)")
    if args.html and args.pdf and \
            os.path.abspath(args.html) == os.path.abspath(args.pdf):
        sys.exit("error: --html and --pdf point at the same file")

    reports, key, dates = [], None, list(args.showdate)
    kw = {"cache_dir": args.cache_dir, "refresh": args.refresh}
    try:
        if args.catch_up:
            key = load_key(args.apikey)
            played = recent_shows(key, args.catch_up, artist=args.artist, **kw)
            have = set() if args.force else archived_dates(args.site)
            fresh = [d for d in played if d not in have and d not in dates]
            print("catch-up: %d show%s played in the last %d days, %d to fetch"
                  % (len(played), "" if len(played) == 1 else "s",
                     args.catch_up, len(fresh)), file=sys.stderr)
            dates += fresh

        if args.from_json:
            with open(args.from_json, encoding="utf-8") as fh:
                reports.append(json.load(fh))
        for date in dates:
            if args.site and not args.force:
                _, blob = site_paths(args.site, date)
                if os.path.exists(blob):
                    print("%s is already in the site (--force to re-fetch)"
                          % date, file=sys.stderr)
                    continue
            key = key or load_key(args.apikey)   # not needed for --rebuild
            try:
                report = build(date, key, artist=args.artist, **kw)
            except ApiError as exc:
                # A tour-length run should not die on tonight's show having no
                # setlist posted yet.
                if not args.site:
                    raise
                print("skipping %s: %s" % (date, exc), file=sys.stderr)
                continue
            if args.previous:
                add_previous(report, key, **kw)
            reports.append(report)
    except ApiError as exc:
        sys.exit("error: %s" % exc)

    if args.site:
        write_site(args.site, reports, bar_scale=args.bar_scale,
                   rebuild=args.rebuild)
    elif reports:
        sys.stdout.write(render_text(reports[0]))

    if not (one_file and reports):
        return

    report = reports[0]
    if args.html or args.pdf:
        markup = render_html(report, bar_scale=args.bar_scale)
        if args.html:
            with open(args.html, "w", encoding="utf-8") as fh:
                fh.write(markup)
            print("wrote %s" % args.html, file=sys.stderr)
        if args.pdf:
            try:
                used = write_pdf(markup, args.pdf, prefer=args.pdf_backend,
                                 single_page=args.single_page)
            except ApiError as exc:
                sys.exit("error: %s" % exc)
            print("wrote %s (via %s)" % (args.pdf, used), file=sys.stderr)
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2)
        print("wrote %s" % args.json, file=sys.stderr)


if __name__ == "__main__":
    main()