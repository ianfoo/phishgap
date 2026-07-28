#!/usr/bin/env python3
"""
possumlogic.py -- an archive of Phish performances, via the Phish.net API v5.

One call to /v5/setlists/showdate/<date>.json returns every song in the show
with its `gap` already computed, so there is no HTML parsing and no arithmetic.

    export PL_PHISHNET_API_KEY=...         # or ~/.config/possumlogic/keys.json
                                           # {"phish.net": "..."}
                                           # every PL_ var belongs to this program
    python3 possumlogic.py 2026-07-24 --html report.html --pdf report.pdf

Or keep a growing site of them, one page per show plus a searchable index:

    python3 possumlogic.py 2026-07-22 2026-07-24 --previous --site site
    python3 possumlogic.py --site site --rebuild    # re-render after a CSS edit

Each show lands in site/<date>.html, its data is archived in site/data, and
site/index.html is regenerated from that archive every run. Dates already in
the site are skipped unless --force, so runs are additive and cheap.

Requires: stdlib only for JSON/text output. `pip install weasyprint` for --pdf.
Responses are cached on disk; phish.net asks that clients cache rather than
re-request. Use --refresh to bypass.
"""

import argparse
import base64
import bisect
import contextlib
import collections
import datetime
import glob
import hashlib
import html
import json
import math
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
import zoneinfo

API_ROOT = "https://api.phish.net/v5"
CACHE_TTL = 6 * 3600
# The new home, with the old one still read. A cache is disposable, but
# throwing one away silently means the next run re-fetches thousands of
# responses it already had, so the move is made without that cost.
_CACHE_NEW = os.path.expanduser("~/.cache/possumlogic")
_CACHE_OLD = os.path.expanduser("~/.cache/phishgap")
DEFAULT_CACHE = (_CACHE_OLD if os.path.isdir(_CACHE_OLD)
                 and not os.path.isdir(_CACHE_NEW) else _CACHE_NEW)

# Minimum spacing between live requests. Building a whole tour with --previous
# is a couple of hundred calls, and phish.net is a volunteer operation; the
# cache absorbs everything after the first pass, so the cost is once-only.
# 0.25s was enough to earn a 429, so pace it at well under two per second and
# back off when asked to.
MIN_INTERVAL = 0.6
MAX_TRIES = 5
_last_fetch = [0.0]

# How long a song count has to hold still before it is taken for the finished
# show. This is NOT the run interval: runs can be hourly and the quiet period
# still two. What it has to clear is the longest gap between two consecutive
# songs being entered -- a 45-minute jam, or a setbreak, plus the lag of
# whoever is typing. Call that 90 minutes and round up.
QUIET_HOURS = 2
# After an encore the band has said it is over, so the wait to call the
# show finished drops from two hours to this. Long enough for a second
# encore, which is the only thing that follows the first.
ENCORE_QUIET = datetime.timedelta(minutes=30)

# Backstop for when stability never settles, e.g. a setlist entered set by set
# and then abandoned overnight. Doors are never later than about 20:30 local and
# even a three-set night is done inside five hours, so 09:00 UTC the next day is
# past the latest plausible end for a Pacific show -- and for anywhere else on
# the continent by more. No venue time zone required, just the worst case.
LAST_END_UTC = datetime.time(9, 0)

# --catch-up re-fetches shows this recent even when they are already archived.
# There is no hour that is safely after both an east coast and a west coast
# show, so any schedule can catch a setlist mid-entry; without a recheck window
# that partial fill would be archived and then skipped for good. This also
# picks up phish.net corrections made in the days after a show.
RECHECK_DAYS = 3

# phish.net encodes sets as 1..4 then e / e2 / e3
SET_ORDER = {"1": 0, "2": 1, "3": 2, "4": 3, "e": 4, "e2": 5, "e3": 6}
SET_LABEL = {"1": "SET 1", "2": "SET 2", "3": "SET 3", "4": "SET 4",
             "e": "ENCORE", "e2": "ENCORE 2", "e3": "ENCORE 3"}


# -------------------------------------------------------------------- api ---

class ApiError(RuntimeError):
    pass


# One file, one key per service, because a file called `apikey` holding a bare
# string does not say whose key it is -- and it stopped being true the moment a
# second service was worth asking. Keyed by the host the key authenticates
# against, so the name of the setting is checkable against the URL it is sent
# to rather than being a label we chose.
CONFIG_DIR = os.path.join(
    os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config"),
    "possumlogic")
CONFIG_FILE = os.path.join(CONFIG_DIR, "keys.json")
LEGACY_KEY_FILE = os.path.expanduser("~/.config/phishgap/apikey")

# The environment variable for each service names the service too. PHISHNET_API_KEY
# keeps its name: it is phish.net's key, not this program's, and rebranding
# someone else's credential would be the same mistake in the other direction.
# Everything this program reads from the environment is prefixed PL_, so it
# cannot collide with a variable some other tool owns and so a shell that has
# several of these in it says which belongs to what. The names are derived from
# the service key rather than listed, which is what keeps a third service from
# needing a decision: phish.net becomes PL_PHISH_NET_API_KEY on its own.
ENV_PREFIX = "PL_"

SERVICES = {
    "phish.net": {"signup": "https://phish.net/api"},
    "setlist.fm": {"signup": "https://www.setlist.fm/settings/api"},
}


# Every setting this program takes from the environment, prefixed or not, so a
# variable that is nearly right can be told from one that is simply unknown.
ENV_SETTINGS = ("GOATCOUNTER", "DOMAIN")


def env_all_names():
    """Every environment variable this program will read, prefixed and plain."""
    names = []
    for service in SERVICES:
        names.extend(env_names(service))
    for extra in ENV_SETTINGS:
        names.extend((ENV_PREFIX + extra, extra))
    return tuple(names)


# Reported once each, however many times a value is asked for.
_ENV_SAID = set()


def env_value(stem, quiet=False):
    """Read ENV_PREFIX+stem, falling back to stem, saying which one it used.

    Saying so is the point. A prefix typed slightly wrong -- PL_PHISNET_API_KEY
    -- sets a variable nothing reads, and the fallback then quietly serves
    whatever the unprefixed name happens to hold, which may be a key from a
    year ago. Silence there costs an afternoon. So a fallback announces itself,
    and a PL_ variable nobody recognises is called out by name.
    """
    for name in (ENV_PREFIX + stem, stem):
        raw = os.environ.get(name)
        if raw and raw.strip():
            if not quiet and name not in _ENV_SAID:
                _ENV_SAID.add(name)
                if not name.startswith(ENV_PREFIX):
                    log("using %s (%s%s is not set)", name, ENV_PREFIX, stem)
                else:
                    log("using %s", name)
            return raw.strip()
    return None


def check_env():
    """Say what the environment is giving this run, and what it is not.

    Two things worth saying out loud. Which variable a value actually came
    from, because an unprefixed one is a value this program did not ask for by
    its own name and may be older than whoever set the prefixed one intended.
    And any PL_ variable nothing reads, because a prefixed name that is not one
    of ours is almost always a typo -- nothing else has a reason to use the
    prefix, and the fallback will hide the mistake by quietly working.
    """
    known = set(env_all_names())
    # One line naming where the configuration came from, not an inventory of
    # what is set. The only per-variable thing worth saying is when a value
    # arrived under a name this program did not ask for by, because that value
    # may be older than whoever set the prefixed one intended.
    plain = [n for n in env_all_names()
             if not n.startswith(ENV_PREFIX)
             and (os.environ.get(n) or "").strip()
             and not (os.environ.get(ENV_PREFIX + n) or "").strip()]
    sources = []
    if any((os.environ.get(n) or "").strip() for n in known):
        sources.append("environment")
    if _config_keys():
        sources.append(os.path.basename(CONFIG_FILE))
    if not sources and os.path.isfile(LEGACY_KEY_FILE):
        sources.append(LEGACY_KEY_FILE)
    if sources:
        log("config from %s", " and ".join(sources))
    for name in plain:
        log("config: %s came from the unprefixed %s -- %s%s is not set",
            name.split("_")[0].lower(), name, ENV_PREFIX, name)
    # Two kinds of near-miss. A wrong name under the right prefix -- and a
    # right name under the wrong prefix, which is the one that hides: PH_ for
    # PL_ sets a variable that starts with neither of our forms, so a check
    # that only looks at PL_ never sees it and the setting silently does
    # nothing. Anything ending in one of our stems is suspicious whatever it
    # begins with.
    stems = tuple(n for n in known if not n.startswith(ENV_PREFIX))
    stray = sorted(n for n in os.environ
                   if n not in known
                   and (n.startswith(ENV_PREFIX)
                        or any(n.endswith("_" + s) for s in stems)))
    for n in stray:
        near = [x for x in known
                if x.startswith(ENV_PREFIX) and n.endswith(x[len(ENV_PREFIX):])]
        log("env: warning -- %s is set but nothing reads it. %s",
            n, ("Did you mean %s?" % near[0]) if near else
            "This program reads %s"
            % ", ".join(sorted(x for x in known if x.startswith(ENV_PREFIX))))
    return stray


def env_names(service):
    """Environment variables to try for `service`, in order of precedence.

    The namespaced name, then the same name without the prefix. Separators in
    the service key are dropped rather than becoming underscores, which makes
    the unprefixed form come out as PHISHNET_API_KEY -- the name already in
    every existing shell and in the repository secret a scheduled job depends
    on tonight. So the fallback is not a compatibility shim bolted on; it is
    simply what these have always been called.
    """
    stem = re.sub(r"[^A-Z0-9]+", "", service.upper()) + "_API_KEY"
    return (ENV_PREFIX + stem, stem)


def _config_keys():
    """{service: key} from the config file, or {} if there is not one."""
    if not os.path.isfile(CONFIG_FILE):
        return {}
    try:
        with open(CONFIG_FILE, encoding="utf-8") as fh:
            data = json.load(fh)
    except ValueError as exc:
        raise ApiError("%s is not valid JSON: %s" % (CONFIG_FILE, exc))
    if not isinstance(data, dict):
        raise ApiError("%s should hold an object of service -> key" % CONFIG_FILE)
    return {k: v for k, v in data.items() if isinstance(v, str) and v.strip()}


def load_key(explicit=None, service="phish.net", required=True):
    """The key for one service: explicit, then environment, then config file.

    Returns None rather than raising when `required` is false, which is how an
    optional service -- one whose absence costs a feature rather than the run --
    asks whether it is configured.
    """
    if explicit:
        return explicit
    meta = SERVICES.get(service) or {}
    stem = env_names(service)[1]                 # the unprefixed form
    found = env_value(stem)
    if found:
        return found
    found = _config_keys().get(service)
    if found:
        return found
    # The old single-key file, which could only ever have been phish.net's.
    if service == "phish.net" and os.path.isfile(LEGACY_KEY_FILE):
        with open(LEGACY_KEY_FILE) as fh:
            legacy = fh.read().strip()
        if legacy:
            return legacy
    if not required:
        return None
    raise ApiError(
        "No %s API key. Set %s, or add it to %s as\n"
        '  {"%s": "..."}\n'
        "Request a key at %s"
        % (service, env_names(service)[0], CONFIG_FILE,
           service, meta.get("signup", "the service")))


def _http_json(url, label, cache_dir=DEFAULT_CACHE, refresh=False,
               ttl=CACHE_TTL, secret=None):
    """Fetch and parse one JSON URL, cached on disk, paced and backed off.

    `label` is what appears in errors, since a URL with a key in it must never
    be printed. `secret`, when given, is masked out of the cache key for the
    same reason. Shared by both APIs this reads, which is also why the pacing
    is global: politeness to one host should not be spent on the other.
    """
    blob = None
    if cache_dir:
        os.makedirs(cache_dir, exist_ok=True)
        # key on the URL minus the apikey so the key never lands on disk
        stable = url.replace(urllib.parse.quote(secret), "KEY") if secret else url
        cache_file = os.path.join(
            cache_dir, hashlib.sha256(stable.encode()).hexdigest()[:20] + ".json")
        if not refresh and os.path.isfile(cache_file):
            if time.time() - os.path.getmtime(cache_file) < ttl:
                with open(cache_file, encoding="utf-8") as fh:
                    blob = fh.read()

    if blob is None:
        req = urllib.request.Request(
            url, headers={"User-Agent": "possumlogic/1.0 (+personal use)",
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
                    raise ApiError("HTTP %s from %s" % (exc.code, label)) from None
                # Honour Retry-After when the server sends one, else back off.
                try:
                    pause = float(exc.headers.get("Retry-After") or 0)
                except ValueError:
                    pause = 0.0
                pause = pause or min(30.0, 2.0 ** attempt)
                log("HTTP %s from %s, retrying in %.0fs (%d/%d)",
                    exc.code, label, pause, attempt, MAX_TRIES)
                time.sleep(pause)
            except urllib.error.URLError as exc:
                # Wifi dropping out mid-run used to abandon a tour-length fetch
                # and leave half the histories unfilled, so this retries too.
                if attempt == MAX_TRIES:
                    raise ApiError("Could not reach %s: %s"
                                   % (urllib.parse.urlsplit(url).netloc,
                                      exc.reason)) from None
                pause = min(30.0, 2.0 ** attempt)
                log("%s, retrying in %.0fs (%d/%d)",
                    exc.reason, pause, attempt, MAX_TRIES)
                time.sleep(pause)
        if cache_dir:
            with open(cache_file, "w", encoding="utf-8") as fh:
                fh.write(blob)

    try:
        return json.loads(blob)
    except ValueError:
        raise ApiError("Non-JSON response from %s" % label) from None


def get(path, apikey, cache_dir=DEFAULT_CACHE, refresh=False, **params):
    """GET <API_ROOT>/<path>.json, cached on disk. -> list of row dicts."""
    params["apikey"] = apikey
    url = "%s/%s.json?%s" % (API_ROOT, path.strip("/"),
                             urllib.parse.urlencode(params))
    payload = _http_json(url, path, cache_dir=cache_dir, refresh=refresh,
                         secret=apikey)
    if payload.get("error"):
        raise ApiError(payload.get("error_message") or "API reported an error")
    return payload.get("data") or []


# fouldomain scores every circulating performance out of 100 and carries
# phish.net's own show rating besides, which phish.net's API does not expose --
# its /reviews rows have a `score`, but that is votes on the review, running
# 0-42 where the rating is out of 5. Recalculated nightly at their end, so a
# day's cache is as fresh as the data ever gets.
FOUL_ROOT = "https://fouldomain.com/api/public"
FOUL_TTL = 24 * 3600
BEST_LIMIT = 25

# "Top 25 versions" is only a distinction when a song has more than 25 to rank.
# Sparks has been played 15 times, so its whole history comes back as its own
# best, and a score of 35 would have been captioned "highly rated". The score
# is absolute across every Phish performance, so the caption goes by the score
# rather than by the rank: Tweezer's 25th is 86 and earns it, Sparks' second is
# 47 and does not, while both still carry the score and a way to hear them.
RATED_HIGH = 80

# Notes longer than this fold, so that one entry cannot take half the screen.
# Two lines at the width they are set to is about this many characters, and the
# median note is 178: roughly half of them fold, and the short ones are spared
# an affordance they do not need.
JAM_CLAMP = 200

# Grouping a song's history by year gives a heading every 7.9 rows across the
# archive -- but 16% of them head a single row, and on Weigh it is 76%. A year
# heading is the only thing on the page repeating what every row it heads
# already says, which is why it reads as furniture when it covers one row and
# as rhythm when it covers eighteen.
#
# Eras carry something no row does, and there are always three or four of them.
# Bounded by date rather than year because the hiatuses fall mid-year: the last
# show before the first was 2000-10-07, and 2.0 ended at Coventry.
ERAS = (
    ("1.0", "", "2000-10-07"),
    ("2.0", "2002-12-31", "2004-08-15"),
    ("3.0", "2009-03-06", "2020-02-23"),
    ("4.0", "2021-07-28", "9999"),
)


def era(iso):
    for label, start, end in ERAS:
        if start <= iso <= end:
            return label
    # A date in a hiatus belongs to whichever era it sits between; nothing in
    # the archive lands here, but a gap year should not go unlabelled.
    return next((l for l, s, _ in reversed(ERAS) if iso >= s), ERAS[0][0])


def foul(path, cache_dir=DEFAULT_CACHE, refresh=False, **params):
    """GET one fouldomain endpoint. -> parsed payload."""
    url = "%s/%s?%s" % (FOUL_ROOT, path.strip("/"),
                        urllib.parse.urlencode(params))
    return _http_json(url, "fouldomain/%s" % path, cache_dir=cache_dir,
                      refresh=refresh, ttl=FOUL_TTL)


# ---------------------------------------------------------------- fonts ---

# Bagnard, Sebastien Sanfilippo, SIL Open Font License 1.1. Self-hosted rather
# than served from Google: the point of changing face at all was to stop
# wearing the same two the whole internet wears, and the licence ships beside
# it in font/OFL.txt as the OFL requires.
#
# One stylesheet for the site rather than the face inlined into every page --
# 13 KB inlined across 640 pages is 8 MB re-downloaded page to page, where one
# linked file is fetched once and cached for the whole visit. The single-file
# --html output keeps its own inlined fonts, since that one is still meant to
# survive being handed to somebody.
FONT_DIR = "font"
DISPLAY_FACE = "Bagnard"
FONT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "site", FONT_DIR, "Bagnard.otf")


def inline_font_css():
    """The face as a data URI, for output that has no stylesheet beside it.

    The hosted pages link one shared sheet, which is the whole reason for
    having a sheet. A file handed to somebody in a chat has no beside, so that
    one carries the face itself -- 13 KB of it -- or falls back to Georgia if
    the font is not where it should be.
    """
    try:
        with open(FONT_FILE, "rb") as fh:
            blob = base64.b64encode(fh.read()).decode()
    except OSError:
        return ""
    return ("<style>@font-face{font-family:'%s';font-weight:400;"
            "font-display:swap;src:url(data:font/otf;base64,%s) "
            "format('opentype')}</style>" % (DISPLAY_FACE, blob))
FONTS_CSS = """/* %(face)s -- Sebastien Sanfilippo, SIL Open Font License 1.1.
   Licence text: ./%(dir)s/OFL.txt */
@font-face{font-family:'%(face)s';src:url('./%(dir)s/Bagnard.otf') format('opentype');
  font-weight:400;font-style:normal;font-display:swap}
/* The paper's texture. It lives here rather than inline in every page for two
   reasons. It was an SVG feTurbulence data URI, which the browser has to run a
   filter over before it can paint -- about a quarter of a second, during which
   the page showed flat colour and then visibly changed under the reader. A PNG
   decodes immediately. And as one cached file it costs 640 pages nothing,
   where a data URI large enough to look good would have been carried by each
   of them.

   url() in an external sheet resolves against the sheet, not the page, so this
   one line works from ./, ./show/ and ./song/ alike.

   The blend mode is the variable that has existed unused since the palettes
   were written: multiply on cream darkens the grain into the paper, screen on
   near-black lifts it, and neither shifts the paper colour the way painting
   opaque noise over it did. */
body{background-image:url(grain.png);background-blend-mode:var(--grain-blend)}
""" % {"face": DISPLAY_FACE, "dir": FONT_DIR}

# Plex Mono is the only thing still coming from Google: it is doing real work
# at 10-14px and swapping it would cost legibility for no identity gain.
WEB_FONTS = ("https://fonts.googleapis.com/css2"
             "?family=IBM+Plex+Mono:wght@400;500;600"
             "&family=Literata:opsz,wght@7..72,400..500&display=swap")


# ------------------------------------------------------------------ share ---

# A donut with a bite out of it: near enough to Phish's own iconography to be
# recognised on a tab strip, far enough to be our own shape, and the bite is
# the thing the site is about. One path, so it survives being drawn at 16px.
FAVICON = (
    "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'>"
    "<circle cx='16' cy='16' r='10.5' fill='none' stroke='#c8371b'"
    " stroke-width='8' stroke-dasharray='44 22' transform='rotate(-42 16 16)'/>"
    "</svg>")
# Fully percent-encoded, so the URI needs no HTML escaping on the way into an
# attribute -- escaping it turned every angle bracket into an entity.
FAVICON_HREF = "data:image/svg+xml,%s" % urllib.parse.quote(FAVICON, safe="/:=")

# Where the site lives, for the absolute URLs link previews require: og:image
# and og:url are fetched by a server that has no idea what page they came from,
# so a relative path is no path at all.
# The domain. In the source rather than only in the environment, because it is
# not a secret and because the alternative bites: GitHub Pages keeps serving a
# custom domain only while CNAME is on the branch, publishing replaces that
# branch wholesale, and a build that does not know the domain writes no CNAME.
# So with this in a repository variable alone, every publish from a laptop --
# where the variable does not exist -- would silently take the domain down
# until the next scheduled run put it back. PL_DOMAIN still overrides, which is
# what a move or a second deployment would use.
DOMAIN = env_value("DOMAIN", quiet=True) or "possumlogic.com"
SITE_URL = ("https://%s" % DOMAIN) if DOMAIN else "https://ianfoo.github.io/phishgap"

# GoatCounter: no cookies, no personal data, nothing stored about a visitor, so
# there is nothing for a consent banner to ask about. Set to the account code
# to switch it on; empty means the pages ask nothing of anyone, which is what
# they do until someone deliberately changes this line.
# Read quietly at import; check_env reports it with everything else, so a run
# gets one block about its environment rather than a line from wherever each
# value happened to be needed.
GOATCOUNTER = (env_value("GOATCOUNTER", quiet=True) or "")
ANALYTICS = ('<script data-goatcounter="https://%s.goatcounter.com/count" '
             'async src="//gc.zgo.at/count.js"></script>' % GOATCOUNTER
             if GOATCOUNTER else "")
OG_IMAGE = "og.png"


def share_meta(title, description, path="", image=OG_IMAGE, card=None):
    """The tags iMessage, Signal, Discord and the rest read off a link.

    All of them fall back to Open Graph, so that carries the weight; the
    twitter:card line is what makes the ones that look for it render a large
    image rather than a thumbnail. Without og:image the card is a line of grey
    text, which is a poor advertisement for a page of graphs.
    """
    url = "%s/%s" % (SITE_URL, path.lstrip("./")) if path else SITE_URL + "/"
    # A page's own card when one is being made for it, the house card when not
    # -- a preview naming the wrong show is worse than a generic one.
    if card:
        image = "%s/%s.png" % (CARD_DIR, card)
    return "".join((
        '<link rel="icon" href="%s">' % FAVICON_HREF,
        '<meta name="theme-color" content="#c8371b">',
        '<meta name="description" content="%s">' % description,
        '<meta property="og:site_name" content="Possum Logic">',
        '<meta property="og:title" content="%s">' % title,
        '<meta property="og:description" content="%s">' % description,
        '<meta property="og:url" content="%s">' % html.escape(url, quote=True),
        '<meta property="og:image" content="%s/%s">' % (SITE_URL, image),
        '<meta property="og:image:width" content="1200">',
        '<meta property="og:image:height" content="630">',
        '<meta property="og:image:alt" content="%s">' % description,
        '<meta name="twitter:card" content="summary_large_image">',
    ))


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


def log(msg, *args):
    """One timestamped line to stderr.

    These are read in a GitHub Actions log days later, usually to answer "what
    did the run at 01:35 actually see" -- so every line carries the UTC time
    and says what was decided rather than what was written. A run that does
    nothing should say why in one line; a run during a show should be legible
    as a sequence of events without opening the archive.
    """
    stamp = _utcnow().strftime("%H:%M:%S")
    print("[%s] %s" % (stamp, msg % args if args else msg), file=sys.stderr)


def _utcnow():
    return datetime.datetime.now(datetime.timezone.utc)


def recent_shows(apikey, days, artist="Phish", **kw):
    """Dates of shows already played within the last `days`, oldest first.

    One call per calendar year touched by the window, which is how --catch-up
    stays cheap enough to run on a schedule: most days it finds nothing new.
    """
    today = _utcnow().date()
    start = today - datetime.timedelta(days=days)
    dates = set()
    # Every year the window touches, not just its two ends. A 21-day window
    # spans at most two calendar years and the set of both read correctly; a
    # backfill does not. Asking for 2020 and 2026 and calling it six years
    # returned 60 shows, all of them from 2020, and silently skipped four
    # years in the middle.
    for year in range(start.year, today.year + 1):
        for row in get("shows/showyear/%d" % year, apikey, **kw):
            if artist and row.get("artist_name") != artist:
                continue
            showdate = row.get("showdate") or ""
            if start.isoformat() <= showdate <= today.isoformat():
                dates.add(showdate)
    return sorted(dates)


def own_history(rows, artist):
    """One band's own performances of a song, oldest first.

    A song's history spans every band that has played it: /slug/ghost returns
    242 Phish rows, 81 Trey Anastasio and one Page McConnell. Unfiltered, the
    last performance of a Phish song came back as a Trey solo show at the
    Capitol Theatre. The same filter keeps the same-date lookup in
    add_previous from landing on another band's row, makes a debut mean the
    first time *this* band played it, and keeps song pages from listing TAB
    shows. Across the archive it drops 4,361 rows of 32,880.
    """
    rows = [r for r in rows if r.get("showdate")
            and (not artist or r.get("artist_name") == artist)]
    rows.sort(key=lambda r: (r["showdate"], int(r.get("position") or 0)))
    return rows


def remeasure(site_dir, artist="Phish"):
    """Recompute every archived report's derived fields from stored histories.

    Gaps, verdicts and previous performances are written into a report when it
    is fetched, so a change to how any of them is decided leaves every report
    already on disk stating the old answer. Re-fetching to correct that would
    be thousands of calls for data the archive already holds; this reads the
    song histories instead and costs nothing.

    Only songs whose stored history covers the show are touched. Anything else
    is left exactly as it was rather than guessed at.
    """
    changed = skipped = 0
    counting = set(load_calendar(site_dir))
    for path in sorted(glob.glob(os.path.join(site_dir, "data", "[12]*.json"))):
        with open(path, encoding="utf-8") as fh:
            report = json.load(fh)
        before = json.dumps(report, sort_keys=True)
        counts = report["date"] in counting
        for s in report.get("songs") or []:
            hist = archived_history(site_dir, s.get("slug") or "", report["date"])
            if hist is None:
                # No stored history to recompute from, but a verdict on an
                # event that is not a show is wrong whatever the history says,
                # so that much can still be withdrawn.
                if not counts:
                    for k in ("verdict", "gap_median", "gap_low", "gap_high"):
                        s.pop(k, None)
                    s["verdict"] = None
                skipped += 1
                continue
            # The verdict fields are rewritten wholesale, so a song that should
            # no longer carry one loses it rather than keeping a stale value.
            for k in ("gap", "verdict", "debut", "prev_date", "prev_venue",
                      "prev_place", "gap_median", "gap_mean", "gap_low",
                      "gap_high", "plays", "recent_plays", "out"):
                s.pop(k, None)
            _finish_song(s, hist, report["date"], counting)
        after = json.dumps(report, sort_keys=True)
        if after != before:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(report, fh, indent=2)
            changed += 1
    log("remeasured: %d report%s rewritten, %d song rows had no stored history",
        changed, "" if changed == 1 else "s", skipped)
    return changed


def _finish_song(s, hist, date, counting=None):
    """Fill one song's gap, verdict and previous performance from its history.

    Split out so the archived path and the fetched path cannot drift: they
    differ in where the rows came from and in nothing else.

    `counting` is the set of show dates that count toward a gap. Performances
    at the others -- soundchecks, the Tonight Show, Tiny Desk -- are dropped
    before anything is decided, because they are not shows and must not stand
    as the performance before this one. Left in, Gone read as a bustout of
    1,468 whose previous performance was two months earlier: its first outing
    was the Festival 8 soundcheck, so its real debut did not look like one.
    Evolve pointed "last performed" at a Tiny Desk session four shows back that
    was not four shows back, or a show at all.

    The show being described always survives the filter, even when it is itself
    a soundcheck -- those reports still exist and still have to render.
    """
    if counting:
        hist = [h for h in hist
                if h["showdate"] in counting or h["showdate"] == date]
    idx = next((i for i, h in enumerate(hist) if h["showdate"] == date), None)
    if idx is not None:
        # by_show has already found the night's real gap, wherever among the
        # repeats phish.net happened to file it.
        g = _gap(hist[idx])
        if g is not None:
            s["gap"] = g
    # What the song went into. phish.net files the mark on the earlier of the
    # two songs it joins, which is what makes it belong on this row: with a
    # band that segues as much as this one, "Tweezer ->" and "Tweezer" are
    # different facts about the night, and the report was printing them the
    # same. Absent for a set closer, which genuinely went into nothing.
    if idx is not None:
        s["out"] = hist[idx].get("out") or ""
    if idx == 0:
        s["debut"] = True              # this show IS the first performance
        # ...and a debut has no gap. A gap is the shows between a performance
        # and the one before it, so with nothing before it there is no gap to
        # state. phish.net files a number here anyway, and that number is the
        # count of every show the band had played up to that night: the
        # fourteen covers debuted on 2009-10-31 all carry 1,451, the nine on
        # 2016-10-31 all carry 1,747. Kept, it made 244 debuts read as bustouts
        # -- a song cannot come back from an absence it was never in -- and put
        # a debut at the top of the index as the longest gap on the site.
        s["gap"] = None
    # The history is already in hand for the previous-performance lookup, so
    # the song's own gap distribution costs nothing more. Shows before this one
    # only, and never the debut, which has no gap to speak of.
    # No verdict where the comparison would be meaningless. A soundcheck is not
    # a show, so calling something a bustout there says the band brought a song
    # back at an event that does not count as an occasion. And "Jam" is not a
    # composition -- it cannot be overdue or bust out, because there is no
    # particular thing to have been waiting for.
    judgeable = (not counting or date in counting) \
        and (s.get("slug") or "") not in NOT_A_SONG
    if judgeable:
        s.update(_classify(s["gap"], hist[1:idx if idx else 0], date,
                           plays=None if idx is None else idx + 1))
    else:
        for k in ("verdict", "gap_median", "gap_mean", "gap_low", "gap_high",
                  "plays", "recent_plays"):
            s.pop(k, None)
        s["verdict"] = None
    prior = hist[idx - 1] if idx else (hist[-1] if idx is None and hist else None)
    # Always assigned, never conditionally. The renderers read these by
    # subscript because the report shape has always guaranteed them, so a debut
    # that simply omitted them turned into a KeyError three screens away.
    s["prev_date"] = prior.get("showdate") if prior else None
    s["prev_venue"] = (prior.get("venue") or "") if prior else ""
    s["prev_place"] = ", ".join(
        p for p in (prior.get("city"), prior.get("state")) if p) if prior else ""


def add_previous(report, apikey, site_dir=None, **kw):
    """Optional second pass: date/venue of each song's prior performance.

    Costs one call per song, so it is opt-in behind --previous.

    The response is the song's whole performance history, so with a site to
    write into, that history is archived on the way past. The refresh
    invariant falls out for free: a song's history only changes when the band
    plays it, and when they do, that show's fetch comes back through here.
    """
    missed = []
    artist = report.get("artist")
    counting = set(load_calendar(site_dir)) if site_dir else None
    for s in report["songs"]:
        # Free when the archive already covers this show, which during a
        # backfill is nearly always.
        hist = archived_history(site_dir, s["slug"], report["date"])
        if hist is not None:
            _finish_song(s, hist, report["date"], counting)
            continue
        try:
            hist = get("setlists/slug/%s" % s["slug"], apikey, **kw)
        except ApiError as exc:
            # Worth saying out loud: a rate limit here would otherwise just
            # render as a show whose songs quietly have no history.
            missed.append("%s (%s)" % (s["song"], exc))
            continue
        # One row per show from here down. The response has one row per setlist
        # slot, and a song can come round more than once a night -- five
        # Tweezers at Merriweather in 2014 -- which would otherwise count as
        # five plays, and file four gaps of 0 into the distribution that
        # decides whether tonight's gap is unusual.
        hist = by_show(own_history(hist, artist))
        if site_dir:
            save_song_history(site_dir, s["slug"], s["song"], hist, artist)
        _finish_song(s, hist, report["date"], counting)
    if missed:
        log("warning: no history for %d of %d songs in %s: %s",
            len(missed), len(report["songs"]), report["date"], "; ".join(missed))
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


LIGHT = {
    "paper": "#f2ece0", "ink": "#17150f", "ink-soft": "#413c31",
    "rule": "#c9bfa9", "rule-soft": "rgba(201,191,169,.45)",
    "hot": "#c8371b", "cool": "#4f6046", "dim": "#6b6456",
    # The accent reads at 4.44:1 on paper -- fine for a 36px figure, under the
    # bar for the 10px chips and verdicts it is also used on. Display keeps the
    # brighter one; anything small takes the darker.
    "hot-text": "#a92e14",
    "track": "rgba(23,21,15,.085)", "band": "#7d7360",
    "hover": "rgba(200,55,27,.055)", "edge": "#8d8676",
    "grain-blend": "multiply", "grain-opacity": ".45",
}
DARK = {
    "paper": "#131210", "ink": "#ece5d5", "ink-soft": "#c4bcaa",
    "rule": "#413a30", "rule-soft": "rgba(236,229,213,.13)",
    "hot": "#ff6b45", "cool": "#93b184", "dim": "#9b9384",
    "hot-text": "#ff6b45",
    "track": "rgba(236,229,213,.1)", "band": "#a89c85",
    "hover": "rgba(255,107,69,.07)", "edge": "#6b5f4f",
    "grain-blend": "screen", "grain-opacity": ".2",
}


def _vars(palette):
    return "".join("--%s:%s;" % kv for kv in palette.items())


def _dark_under(root):
    """The dark rules, written against whichever :root selector applies.

    An explicit choice has to beat the system preference in both directions,
    which normally means two copies of the palette drifting apart. Emitting
    both from one dict instead: once for a dark system that has not been
    overridden, once for an explicit dark. Both stay inside `screen`, so print
    and PDF are never anything but paper stock.
    """
    return ("%(r)s{%(v)s}\n"
            # Favicons drawn as solid black on transparency vanish here.
            "%(r)s .badge img.flip{filter:invert(1)}\n"
            # Same icon, same problem, worn as a background by the song pages.
            "%(r)s .ext.i-pin::after{filter:invert(1)}\n"
            % {"r": root, "v": _vars(DARK)})


# Shared by the report pages and the index, so one palette edit moves both.
PALETTE_CSS = (
    ":root{color-scheme:light dark;%s}\n" % _vars(LIGHT)
    + ':root[data-theme="light"]{color-scheme:only light}\n'
    + ':root[data-theme="dark"]{color-scheme:only dark}\n'
    + "@media screen and (prefers-color-scheme:dark){\n%s}\n"
      % _dark_under(':root:not([data-theme="light"])')
    + "@media screen{\n%s}\n" % _dark_under(':root[data-theme="dark"]')
)

# Footer control. The buttons ship disabled and JavaScript enables them, so a
# page with scripting off offers nothing it cannot deliver.
THEME_CSS = """
.theme{display:inline-flex;gap:.3rem;align-items:center}
.theme button{font:inherit;font-size:.625rem;letter-spacing:.14em;
   text-transform:uppercase;padding:.28rem .45rem;border:1px solid var(--edge);
   background:transparent;color:var(--dim);cursor:pointer;border-radius:0}
.theme button:hover:not(:disabled):not(.on){color:var(--ink);
   border-color:var(--ink)}
.theme button.on{background:var(--ink);color:var(--paper);
   border-color:var(--ink)}
/* The selected one is already ink-on-paper reversed, so hovering it must not
   set the text to the colour it is sitting on. It brightens its edge instead. */
.theme button.on:hover:not(:disabled){color:var(--paper);
   box-shadow:0 0 0 2px var(--hot)}
.theme button:disabled{opacity:.45;cursor:default}
.theme button:focus-visible{outline:2px solid var(--hot);outline-offset:1px}
@media print{.theme{display:none}}
"""

NEW_ROWS_JS = """<script>
/* Which rows are new since this reader last looked. A reload of a growing
   setlist otherwise gives a longer table and no clue what changed, so finding
   the new part means re-reading the whole thing -- which is why the tab gets
   closed. The count last seen is kept in this browser only; nothing is sent
   anywhere and nothing is stored server-side. */
(function(){
  var live=document.querySelector('.live');
  if(!live||!window.localStorage) return;
  var rows=[].slice.call(document.querySelectorAll('tbody tr'));
  if(!rows.length) return;
  var key='pl-seen-'+document.title.replace(/[^0-9-]/g,'').slice(0,10);
  var seen=parseInt(localStorage.getItem(key)||'0',10);
  if(seen>0&&rows.length>seen){
    rows.slice(seen).forEach(function(r){ r.classList.add('fresh'); });
    var n=rows.length-seen;
    var tag=document.createElement('span');
    tag.className='since-you';
    tag.textContent=n+' new since you last looked';
    live.appendChild(tag);
  }
  try{ localStorage.setItem(key,String(rows.length)); }catch(e){}
})();
</script>"""


AGO_JS = """<script>
/* "4 minutes ago" rather than "01:47 UTC". A clock time on a page about dates
   reads like a server log, and the fact a reader wants is elapsed -- has this
   stalled? -- not the hour it happened. The stamp ships in datetime= so it is
   correct without JavaScript and correct after the tab has been open an hour;
   this only renders it. */
(function(){
  var els=[].slice.call(document.querySelectorAll('time.ago'));
  if(!els.length) return;
  function say(sec){
    if(sec<45) return 'just now';
    var m=Math.round(sec/60);
    if(m<60) return m+' minute'+(m===1?'':'s')+' ago';
    var h=Math.round(m/60);
    return h+' hour'+(h===1?'':'s')+' ago';
  }
  function tick(){
    var now=Date.now();
    els.forEach(function(e){
      var t=Date.parse(e.getAttribute('datetime'));
      if(!isNaN(t)) e.textContent=say((now-t)/1000);
    });
  }
  tick();
  setInterval(tick,20000);
})();
</script>"""


ROW_JS = """<script>
(function(){
  // On a phone the song title is a very small target for a link that is the
  // only one in its row, so the row follows it. Delegated rather than wrapped,
  // because an overlay covering the row would swallow the hover the gap
  // figure's tooltip needs. With scripting off the title still works.
  var t=document.querySelector('table');
  if(!t) return;
  document.addEventListener('click', function(e){
    if(e.target.closest('a')) return;
    var tr=e.target.closest('tr');
    if(!tr) return;
    // Two questions live in one row: "where does tonight's version sit in this
    // song's history" and "what else happened the last time they played it".
    // The whole row used to answer only the first, which swallowed the second
    // -- reaching for the previous show landed you on the current one.
    var last=e.target.closest('td.last');
    var a=(last && last.querySelector('a')) || tr.querySelector('td.song a');
    if(!a) return;
    var sel=window.getSelection();
    if(sel && !sel.isCollapsed) return;   // let people copy a venue name
    a.click();
  });
})();
</script>"""

THEME_UI = ("<span class='theme' role='group' aria-label='Colour theme'>"
            + "".join("<button type='button' data-theme='%s' disabled>%s</button>"
                      % (v, v.title()) for v in ("auto", "light", "dark"))
            + "</span>")

# Runs in <head> so the stored choice is on the root element before first
# paint, otherwise a dark-mode reader gets a flash of paper. localStorage
# throws on a file:// page in some browsers, which is exactly how these get
# shared, hence the try blocks.
THEME_JS = """<script>
(function(){
  // Deliberately not renamed: this is a private key in a reader's own
  // browser, and changing it would silently reset the light/dark choice
  // of everyone who has ever set one, to rename a string nobody sees.
  var KEY='phishgap-theme', root=document.documentElement;
  function apply(v){
    if(v==='light'||v==='dark') root.setAttribute('data-theme',v);
    else root.removeAttribute('data-theme');
  }
  try{ apply(localStorage.getItem(KEY)); }catch(e){}
  document.addEventListener('DOMContentLoaded', function(){
    var box=document.querySelector('.theme');
    if(!box) return;
    var btns=[].slice.call(box.querySelectorAll('button'));
    function mark(){
      var cur=root.getAttribute('data-theme')||'auto';
      btns.forEach(function(b){
        var on=b.getAttribute('data-theme')===cur;
        b.classList.toggle('on',on);
        b.setAttribute('aria-pressed',on?'true':'false');
      });
    }
    btns.forEach(function(b){
      b.disabled=false;
      b.addEventListener('click',function(){
        var v=b.getAttribute('data-theme');
        apply(v);
        try{ v==='auto'?localStorage.removeItem(KEY):localStorage.setItem(KEY,v); }
        catch(e){}
        mark();
      });
    });
    mark();
  });
})();
</script>"""

CSS = PALETTE_CSS + THEME_CSS + """
*{box-sizing:border-box}
/* Every figure on this site sits in a column beside another figure. Tabular
   numerals are what makes that work; the alternative is a hand-measured
   min-width per field, re-measured the first time a four-digit gap turns up. */
body{font-variant-numeric:tabular-nums}
h1,h2,.title{text-wrap:balance}
body{margin:0;padding:clamp(1.4rem,4vw,3.5rem) clamp(1rem,5vw,3rem);
     background:var(--paper);color:var(--ink);
     font-family:'IBM Plex Mono',ui-monospace,SFMono-Regular,monospace;
     font-size:.875rem;line-height:1.55}
.wrap{max-width:960px;margin:0 auto}
/* The header is a grid so the tour, which lives in the show line where there
   is room for it, can be lifted out to ride the breadcrumb row where there is
   not -- see the max-width block. One element either way. */
header{padding-bottom:.9rem}
/* Three fixed columns rather than space-between, so the index link stays put
   when a show is missing one of its neighbours. */
.crumb{font-size:.625rem;letter-spacing:.14em;text-transform:uppercase;
   margin:0 0 .5rem}
.crumb.sections{display:flex;flex-wrap:wrap;align-items:baseline;
   gap:.3rem .9rem}
/* The site's name, not a link. It used to go where "Shows" goes, so the strip
   offered the same destination twice under two labels. As a label it also stops
   inheriting the link underline that made it sit differently from its
   neighbours on the song pages. */
.crumb .mark{color:var(--ink);border-bottom:0;cursor:default}
/* Two cells, not three. The middle one held an "All reports" link that the
   section row above already provides, and once that came out it was an empty
   grid cell on every page in the archive. */
.crumb.pager{display:grid;grid-template-columns:1fr 1fr;align-items:baseline;
       gap:.5rem;margin:0 0 1rem;font-size:.625rem;letter-spacing:.14em;
       text-transform:uppercase}
.crumb a{color:var(--dim);text-decoration:none;white-space:nowrap;
         border-bottom:1px solid var(--rule)}
.crumb a:hover{color:var(--hot);border-bottom-color:var(--hot)}
.crumb .prev{grid-column:1;justify-self:start}
.crumb .next{grid-column:2;justify-self:end}
/* The date, not the wordmark. A report is one night, and the night's name is
   its date -- but the page led with the site's own name at 4rem while the date sat
   small beside a tour and an ordinal, so the one thing that identified the
   page was the least prominent thing on it. The wordmark is already in the nav
   above as a small mark, which is where a wordmark belongs on a page that is
   not the front door.
   Tabular figures because a date is eight digits: without them the 1s pull the
   whole string crooked at this size. */
/* Plex Mono, not the display face. A show's masthead is a date -- eight
   digits and two hyphens -- and the display face has no GSUB table at all, so
   font-variant-numeric here did nothing and its digits run 254 to 1151 units.
   Because the h1 sits in the grid's auto column, that spread moved the venue
   column by up to 45px depending on which digits the date happened to contain.
   The mono is already loaded, already tabular, and already sets every other
   date on the site. The display face keeps the wordmark, the song titles and
   the method page's headings -- words, which is what it is for. */
h1{font-family:'IBM Plex Mono',ui-monospace,monospace;font-weight:600;
   font-size:clamp(1.7rem,5vw,2.75rem);line-height:1.1;margin:0 0 .25rem;
   letter-spacing:-.02em;font-variant-numeric:tabular-nums}
/* The day of the week, which the index has always shown and this page never
   did. Set against the date rather than under it: the masthead is already
   two blocks at width, and a third line would make it three. */
h1 .dow{font-family:'IBM Plex Mono',ui-monospace,monospace;font-weight:400;
   font-size:.75rem;letter-spacing:.14em;text-transform:uppercase;
   color:var(--dim);margin-left:.7rem;vertical-align:.35em;
   white-space:nowrap}
/* Date and tour pair up: both short, so this line cannot wrap and the one
   separator on the page can be neither orphaned nor widowed. The venue is the
   variable-length part, so it gets a line to wrap inside, with no separator to
   strand at the break. */
.show{margin:0;display:flex;flex-wrap:wrap;align-items:baseline}
.show .date{font-family:'IBM Plex Mono',ui-monospace,monospace;font-weight:600;font-size:1.5rem;
   line-height:1;color:var(--ink)}
.show .tour{font-size:1rem;font-weight:600;letter-spacing:0;
   text-transform:uppercase;color:var(--dim)}
/* Sits with the tour, not with the date: it is context for the night rather
   than part of naming it. Absent for 1.0, where it cannot be said honestly,
   and for anything phish.net does not count as a show. */
.show .nth{font-size:.75rem;font-weight:400;letter-spacing:0;color:var(--dim);
   text-transform:none;white-space:nowrap}
/* A dim middot, not a second hot bullet. The bullet separates the two things
   that name the night -- its date and its tour -- and repeating it would make
   this a third of equal rank. It is an aside about the night, so it attaches
   with the quieter mark. Its own, because a show with no tour still needs
   something between the date and this. */
.show .nth::before{content:"\\00B7";color:var(--dim);margin:0 .45rem}
/* No leading bullet: the tour used to follow the date on this line and the
   bullet joined them. It leads now, and a separator with nothing before it is
   just a dot. The ordinal brings its own, which is the only join left. */
.where{margin:0 0 .45rem;font-size:1.125rem;font-weight:600;letter-spacing:0;
   text-transform:uppercase;color:var(--ink)}
/* Two elements, so there is no separator to strand. The locality steps back
   rather than being joined by punctuation that has nowhere safe to break. */
.where .v-name{display:block}
.where .v-place{display:block;font-size:.875rem;color:var(--ink-soft)}
/* Below the stats rather than in the masthead: the header stays a tight block
   of identity, and the links get their own air on the first screen. */
.links{margin:1.1rem 0 0;display:flex;flex-wrap:wrap;gap:.4rem}
.badge{display:inline-flex;align-items:center;gap:.35rem;line-height:1;
   padding:.32rem .52rem;border:1px solid var(--rule);color:var(--dim);
   font-size:.625rem;letter-spacing:.14em;text-transform:uppercase;
   text-decoration:none;white-space:nowrap}
.badge img{display:block;width:13px;height:13px}
.badge:hover{color:var(--ink);border-color:var(--ink-soft);
   background:var(--hover)}

/* Letterpress: a thick rule with a hairline under it. Three to a page at most
   -- a double rule that turns up six times is wallpaper. */
.rule2{height:5px;margin:0 0 1rem;background:linear-gradient(to bottom,
   var(--ink) 0 3px,transparent 3px 4px,var(--ink) 4px 5px)}
/* The tear line between one set and the next. Never between rows. */
.perf{height:1px;margin:1.5rem 0 .6rem;background:repeating-linear-gradient(
   to right,var(--edge) 0 5px,transparent 5px 10px)}
.hero{display:flex;flex-wrap:wrap;margin:.7rem 0 .3rem;
      border-bottom:1px solid var(--ink)}
.card{flex:1 1 0;padding:.85rem 1.1rem;border-left:1px solid var(--rule);
   display:flex;flex-direction:column}
.card:first-child{border-left:0;padding-left:0}
.num{font-family:'IBM Plex Mono',ui-monospace,monospace;font-weight:600;font-size:2.25rem;line-height:1;
     letter-spacing:0;margin-top:auto;color:var(--ink)}
.num.hot{color:var(--hot)}
.lbl{font-size:.625rem;text-transform:uppercase;letter-spacing:.14em;
   color:var(--dim);margin-bottom:.35rem}
/* A tab struck in reverse, hung on a rule that runs out to the margin. Lighter
   on the page than slab caps, and it leaves the display face one job. */
h2{display:flex;align-items:center;gap:.6rem;margin:1.5rem 0 .3rem;padding:0;
   border:0;font-family:'IBM Plex Mono',ui-monospace,monospace;font-weight:600;
   font-size:.625rem;letter-spacing:.14em;text-transform:uppercase}
h2 .tab{background:var(--ink);color:var(--paper);padding:.25rem .55rem;
   print-color-adjust:exact;-webkit-print-color-adjust:exact}
h2::after{content:"";flex:1;border-bottom:1px solid var(--ink)}
table{width:100%;border-collapse:collapse;table-layout:fixed}
/* The gap column carries the number plus the song's typical figures under it,
   so it is wider than the number alone would need. */
/* Song, then where it last turned up, then the bar and the figure. The row
   leads with what it is about; the gap is an attribute of it. */
col.c-song{width:26%}
col.c-last{width:38%}
col.c-bar{width:16%}
col.c-gap{width:20%}
table.no-last col.c-song{width:36%}
table.no-last col.c-bar{width:44%}
th{font-size:.625rem;text-transform:uppercase;letter-spacing:.14em;
   color:var(--dim);font-weight:500;text-align:left;padding:.45rem .6rem;
   border-bottom:1px solid var(--rule)}
th.n,td.n{text-align:right;padding-right:1.1rem;white-space:nowrap}
.gap,.song,.last .date{line-height:1.35rem}
td{padding:.5rem .6rem;border-bottom:1px solid var(--rule-soft);
   vertical-align:middle;line-height:1.35rem}
.song{font-weight:600;font-size:1rem}
/* Outlined, not filled: a bustout is the headline of a night and gets the
   solid stamp, while this is an invitation to read something elsewhere. Inside
   the link, so the whole title-and-chip is one target and lights up together. */
/* The segue mark, which is a fact about the night rather than about the song:
   "Tweezer ->" and "Tweezer" are different entries in a setlist, and the report
   was printing them identically. Quiet, because it qualifies the title rather
   than competing with it. */
/* Only the two-glyph mark is tightened, and only slightly. At full monospace
   advance -> reads as a hyphen standing beside an angle bracket rather than as
   one mark; -.06em closes that without breaking the fixed advance the rest of
   the column depends on. A lone > has nothing to close up, so it is left on
   the grid. */
.seg.tight{letter-spacing:-.06em}
.seg{margin-left:.3rem;font-family:'IBM Plex Mono',ui-monospace,monospace;
   font-weight:600;color:var(--dim);white-space:nowrap}
.jc-chip{display:inline-block;margin-left:.5rem;padding:.1rem .32rem;
   border:1px solid var(--hot);color:var(--hot-text);font-size:.625rem;
   font-weight:600;letter-spacing:.14em;text-transform:uppercase;
   line-height:1.15;vertical-align:.12em;white-space:nowrap}
a.jc-chip{text-decoration:none}
td.song a:hover .jc-chip,a.jc-chip:hover{background:var(--hot);color:var(--paper);
   print-color-adjust:exact;-webkit-print-color-adjust:exact}
.gap{font-family:'IBM Plex Mono',ui-monospace,monospace;font-weight:600;font-size:1.5rem;line-height:1;
     white-space:nowrap}
.gap.big{color:var(--hot)}
.gap.small{color:var(--cool)}
/* The number carries the gap; these carry how the song usually behaves. Sized
   into the same family as the venue text under a date, which is the smallest
   thing on the page that is comfortably readable. */
.typ{display:block;margin-top:.25rem;font-size:.75rem;color:var(--dim);
   white-space:nowrap}
.typ .abbr{display:none}
.verdict{display:inline-block;margin-left:.5rem;vertical-align:.05em;font-size:.625rem;letter-spacing:.14em;
   text-transform:uppercase;white-space:nowrap}
.verdict.overdue{color:var(--hot-text)}
/* One of the pair shows at a time. Wide: under the figure, where the median
   it is judged against already is. Narrow: beside the title, because the
   gap column there is 3.7rem and the word is wider than that. */
.verdict.at-gap{display:block;margin:.1rem 0 0}
.verdict.premature{color:var(--cool)}
/* A bustout is the headline of a show, not a footnote to it: stamped rather
   than merely coloured. print-color-adjust keeps the fill when a browser prints
   it; WeasyPrint keeps backgrounds anyway. */
/* A filled edge reads tighter than text does at the same distance, so the chip
   needs more room above it than the plain tags to sit on the same rhythm. */
/* Struck twice -- fill, a hairline of paper, then the outline again -- and set
   two degrees off true. The right margin buys the rotation its clearance. This
   is the only rotated thing on the site; the moment there are two, it reads as
   a theme rather than a stamp. */
.verdict.bustout{display:inline-block;margin:0 .6rem .1rem .5rem;
   background:var(--hot);color:var(--paper);padding:.16rem .4rem;
   font-size:.625rem;font-weight:600;letter-spacing:.14em;line-height:1.15;
   box-shadow:0 0 0 1.5px var(--paper),0 0 0 3px var(--hot);
   transform:rotate(-2deg);transform-origin:left center;
   print-color-adjust:exact;-webkit-print-color-adjust:exact}
/* Our own tooltip, because the browser's waits about a second before showing
   and this one exists to answer "what is that bar?" while the pointer is still
   on it. No delay, no JavaScript; hidden from print, where nothing hovers. */
@media screen{
  td[data-tip]{position:relative}
  td[data-tip]::after{content:attr(data-tip);position:absolute;left:.25rem;
    bottom:calc(100% - .35rem);z-index:5;white-space:nowrap;
    padding:.3rem .5rem;background:var(--ink);color:var(--paper);
    font-size:.75rem;letter-spacing:0;line-height:1;
    opacity:0;visibility:hidden;transition:opacity .09s ease-out}
  td[data-tip]:hover::after,td[data-tip]:focus-visible::after{
    opacity:1;visibility:visible}
  /* The last column's tip would run off the right edge, so it hangs the other
     way. */
  td.bar[data-tip]::after{left:auto;right:1.2rem}
}
.bar{padding-right:1.2rem}
/* A position, not a length. The track is the whole range a gap can sit in for
   this song; the shaded middle is where it usually sits, the hairline is its
   median, and the mark is tonight. Nothing here is scaled to the show, so a
   bustout somewhere else on the bill cannot flatten this row. */
.bar .track{display:block;position:relative;width:100%;height:14px}
/* The line the mark sits on. Faint, but a real line -- without it a mark near
   the middle had nothing to be near. */
.bar .track::before{content:"";position:absolute;left:0;right:0;top:6px;
   height:2px;background:var(--rule)}
.bar .track.bare::before{opacity:.55}
/* Where this song usually lands, as a block rather than a tint. The previous
   version used --track, which is a 10% alpha meant for the inside of a
   progress bar, and against paper it was not there at all. */
.bar .band{position:absolute;left:30%;right:30%;top:3px;bottom:3px;
   background:var(--band);opacity:.85;border-radius:1px}
.bar .mid{position:absolute;left:50%;top:1px;bottom:1px;width:2px;
   background:var(--paper);opacity:.85}
/* Tonight. Full height and full-strength ink, with a paper halo so it reads
   wherever it lands -- including on top of the median line. This is the one
   thing in the row the eye is meant to find. */
.bar .at{position:absolute;left:50%;top:0;bottom:0;width:5px;
   transform:translateX(-50%);background:var(--ink);border-radius:1px;
   box-shadow:0 0 0 2px var(--paper)}
.bar .at.late{background:var(--hot)}
.bar .at.early{background:var(--cool)}
/* Inside its own band is the ordinary case and gets no colour at all -- ink,
   like the figures. Two thirds of rows land here, and colouring them would
   spend the palette on "nothing to report". */
.bar .at.usual{background:var(--ink)}
.last{font-size:.875rem;overflow-wrap:anywhere;vertical-align:top}
.last .date{white-space:nowrap}
/* Named only where the column header is not doing it -- on a wide screen the
   thead says "Last performed" and a second label would be saying it twice. */
.last .cap{display:none}
/* The date links when we hold that show. Underlined rather than coloured, so
   a column of them does not turn the right-hand side of the table orange. */
.last .date a{color:inherit;text-decoration:none;
   border-bottom:1px solid var(--rule)}
.last .date a:hover{color:var(--hot-text);border-bottom-color:var(--hot-text)}
/* Stacked on wide layouts, run together on narrow ones -- see the
   max-width block, which puts these back inline with separators. */
.last .date,.last .venue,.last .place{display:block}
.venue{color:var(--dim);font-size:.75rem;line-height:1.2rem}
.rating{margin:.45rem 0 0;font-size:.625rem;letter-spacing:.14em;
   text-transform:uppercase;color:var(--dim)}
.rating b{font-family:'IBM Plex Mono',ui-monospace,monospace;font-weight:600;
   font-size:1rem;color:var(--ink);letter-spacing:0;margin-left:.15rem}
.rating span{opacity:.75}
/* A show that is still happening. Marked, not decorated: the same field
   language as the rest of the masthead, with the state in the bold half and
   the detail in the quiet one. */
.live{margin:.7rem 0 0;display:flex;flex-wrap:wrap;align-items:baseline;
   gap:.2rem .6rem;font-size:.75rem}
/* A state, not a label. It used to be 10px tracked caps in the hot ink --
   character for character the same specification as every field label, every
   table head and every badge on the page -- so the one thing worth
   interrupting for was delivered in the site's most generic voice. */
.live{margin:.8rem 0 0;padding:.6rem 0 .6rem .9rem;
   border-left:4px solid var(--hot);display:block;max-width:62ch}
.live b{display:block;font-family:'Bagnard',Georgia,serif;font-weight:400;
   font-size:1.25rem;line-height:1.2;letter-spacing:0;text-transform:none;
   color:var(--ink)}
.live span{display:block;margin-top:.15rem;font-size:.8125rem;color:var(--dim)}
.live span b.n{display:inline;font-family:'IBM Plex Mono',ui-monospace,monospace;
   font-weight:600;font-size:.9375rem;color:var(--ink)}
/* Added since this reader last looked. */
.since-you{display:inline-block;margin-top:.35rem;font-size:.625rem;
   letter-spacing:.14em;text-transform:uppercase;color:var(--paper);
   background:var(--hot);padding:.15rem .4rem}
tr.fresh td{background:var(--hover)}
tr.fresh td.song{box-shadow:inset 3px 0 0 var(--hot)}
/* Same shape as the still-coming-in notice: state in the bold half, detail in
   the quiet one, set in the reading face because it is a sentence. */
.aside-note{margin:.7rem 0 0;padding-left:.8rem;border-left:2px solid var(--rule);
   max-width:62ch}
.aside-note b{display:block;font-size:.625rem;letter-spacing:.14em;
   text-transform:uppercase;color:var(--dim);font-weight:400}
.aside-note span{font-family:'Literata',Georgia,serif;font-size:.9375rem;
   line-height:1.5;font-variation-settings:'opsz' 14;color:var(--ink-soft)}
/* The title carries the link to the song's own page; underlining every one of
   them would stripe the table, so it colours on hover instead. */
td.n,td.song{vertical-align:baseline}
td.song a{color:inherit;text-decoration:none}
td.song a:hover{color:var(--hot)}
.place{color:var(--dim);font-size:.75rem;line-height:1.2rem;white-space:nowrap}
.none{color:var(--dim);font-style:italic}
/* The show's own notes: the other block of real prose on the site, and set in
   the reading face for the same reason the song pages' are. */
.notes{margin:2.2rem 0 0;padding:1rem 1.1rem;border-left:3px solid var(--rule);
       font-family:'Literata',Georgia,serif;font-size:.9375rem;line-height:1.5;
       font-variation-settings:'opsz' 14;color:var(--ink-soft);max-width:68ch}
.notes a{color:var(--hot)}
footer{margin-top:2.4rem;padding-top:.9rem;border-top:1px solid var(--rule);
       font-size:.75rem;letter-spacing:.14em;text-transform:uppercase;
       color:var(--dim);display:flex;justify-content:space-between;
       flex-wrap:wrap;align-items:center;gap:.4rem .9rem}
@media screen{
  .bar .fill{animation:grow .7s cubic-bezier(.2,.8,.3,1) both}
  @keyframes grow{from{transform:scaleX(0);transform-origin:left}}
  tr:hover td{background:var(--hover)}
  /* The whole row leads to the song page on a phone, so it should look like
     it does. Desktop keeps the title as the target -- there the pointer is
     precise and a row-wide cursor over a table of figures reads as noise. */
  @media (max-width:620px){
    tbody tr:has(td.song a){cursor:pointer}
    /* The last-performed block is its own destination once the row stacks, so
       it gets its own edge rather than reading as more of the row above it. */
    td.last:has(a){padding-left:.55rem;border-left:2px solid var(--rule)}
  }
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
  .typ .full{display:none}
  .typ .abbr{display:inline}
  /* minmax(0,1fr) rather than 1fr, because a 1fr track still takes
     min-width:auto and a long unbreakable run would widen it. Not the cause of
     anything observed -- the tracks measure 267 + 59 against a 338 row -- but
     the row has no business being able to grow. */
  /* 4.6rem, not 3.7. The verdict lives in this cell at every width -- one
     element rather than a visible copy and a hidden one, which is what let an
     aria-hidden end up on the copy the phone actually shows. "premature" is
     the widest word it can hold, 63px at this size, so the track is sized for
     it: 73.6px. The song column gives up 0.9rem, which it can afford; the
     alternative costs a screen reader the verdict entirely. */
  tr{display:grid;grid-template-columns:minmax(0,1fr) 4.6rem;column-gap:.7rem;
     grid-template-areas:"song gap" "meta gap";
     padding:.5rem 0;border-bottom:1px solid var(--rule-soft)}
  /* And nothing inside may refuse to break, or the track has no smaller size
     to fall back to. */
  td.song,td.last{min-width:0;overflow-wrap:anywhere}
  td{border:0;padding:0}
  td.n{grid-area:gap;padding-right:0;align-self:start;padding-top:.1rem;
       text-align:right}
  td.song{grid-area:song}
  td.last{grid-area:meta}
  td.bar{display:none}
  /* The hover tooltip, gone. It is position:absolute and white-space:nowrap,
     and it was hidden with visibility:hidden -- which still takes part in
     layout. Every report page was therefore as wide as its longest tooltip:
     497px inside a 375px viewport, so every report scrolled sideways on a
     phone, with nothing visible out there to explain why. Measured: disabling
     this one rule takes the page from 497 to exactly 375.
     No loss here, because there is no hover on a touch screen to show it. */
  td[data-tip]::after{content:none}
  /* No bar here to carry the tick, so the words do all the work. */
  .typ{font-size:.75rem;margin-top:.2rem}
  .verdict{font-size:.625rem}
  .verdict.bustout{font-size:.625rem}
  .gap{font-size:1.25rem}
  .song{font-size:1rem;line-height:1.25rem}
  .last{font-size:.75rem;line-height:1.15rem}
  .last .cap{display:block;font-size:.625rem;letter-spacing:.14em;
     text-transform:uppercase;color:var(--dim);margin-bottom:.15rem}
  .last .date,.last .venue,.last .place{display:inline}
  .last .place{white-space:normal}
  /* --dim rather than --rule. A hairline colour is for hairlines: at #413a30
     on #131210 this separator was invisible on the dark palette. */
  .last .venue::before,.last .place::before{content:" · ";color:var(--dim);
    opacity:.7}
  /* Same two lines, scaled down: date and tour still pair on the first one
     even at 320px, and the masthead closes up so it reads as one block rather
     than a stack of separate announcements. */
  header{padding-bottom:.55rem}
  /* Two full dates and the index link have to share one line here, and at
     320px they only just do, so the pager gives up some tracking rather than
     risk pushing the page sideways. */
  .crumb{margin-bottom:.7rem;gap:.35rem;font-size:.625rem;letter-spacing:.14em}
  h1{margin-bottom:.45rem}
  /* At this width the whole thing fits on one line, so it reads better joined
     -- and a middot cannot be orphaned the way a comma was, because it only
     exists when the two parts are already side by side. */
  .where .v-name,.where .v-place{display:inline}
  /* Margin rather than spaces inside content: a leading or trailing space in
     a generated string collapses, which left "GARDEN ·NEW YORK". */
  .where .v-place::before{content:"\\00B7";color:var(--dim);
     margin:0 .45rem 0 .55rem}
  .show .date{font-size:1.25rem}
  .show .tour{font-size:.625rem;font-weight:400;letter-spacing:.14em}
  .show .tour::before{font-size:1rem;margin:0 .5rem}
  .where{margin-top:.2rem;font-size:.75rem;letter-spacing:0}
  /* The buttons stand twice as tall as a line of footer text, so sharing a row
     with it inflated that row and opened a gap between the two text lines.
     They get their own row down here instead. */
  .theme{order:1;flex-basis:100%}
  /* All three badges have to hold one line down to a 320px phone. */
  .links{margin-top:.95rem;gap:.3rem}
  .badge{font-size:.625rem;letter-spacing:0;padding:.3rem .45rem;gap:.3rem}
  .badge img{width:12px;height:12px}
  .card{flex:1 1 45%;padding:.65rem .55rem}
  .card:nth-child(odd){border-left:0;padding-left:0}
  .card:nth-child(n+3){border-top:1px solid var(--rule)}
  .num{font-size:1.5rem}
  .lbl{font-size:.625rem;letter-spacing:.14em}
}
/* Wide layouts have a big empty corner to the right of the wordmark, and the
   show identity is about as tall as the wordmark is, so the two balance as
   columns. The masthead keeps the strongest position, top left; the show block
   gets the hard right edge of the page rather than being tucked into a corner,
   and the hero rule under both ties them together.

   Scoped to `screen`: a printed report wants its masthead stacked, and the
   page box measures 538pt, which would fall the wrong side of this threshold
   by unit accident rather than by intent. */
@media screen and (min-width:700px){
  header{display:grid;grid-template-columns:auto 1fr;column-gap:2.5rem;
         align-items:start;
         grid-template-areas:"sections sections" "pager pager"
                             "title show" "title where"}
  .crumb.sections{grid-area:sections}
  .crumb.pager{grid-area:pager}
  h1{grid-area:title;margin-bottom:0}
  .show{grid-area:show;justify-content:flex-end;text-align:right}
  .where{grid-area:where;text-align:right;margin-top:.35rem}
}
@media (prefers-reduced-motion:reduce){.bar .fill{animation:none}}
@page{size:letter;margin:14mm 13mm 12mm}
@media print{
  body{padding:0;font-size:10.5pt;background:#fff}
  .crumb,.links{display:none}
  /* rem still resolves against the 16px root here while the body drops to
     10.5pt, so these do not shrink with the column and the widest of them ran
     into the song title. Sized in points to match the page. */
  .typ{font-size:7.5pt}
  .verdict{font-size:6.5pt}
  .verdict.bustout{font-size:7pt;padding:1pt 2.5pt}
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
<title>{titlestate}{date} &mdash; Possum Logic</title>{refresh}
<meta property="og:type" content="article">{share}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="{fonts}" rel="stylesheet">
{sheet}
<style>{css}</style>{theme_js}{ago_js}{new_rows_js}</head><body><div class="wrap">
<div class="rule2"></div>
<header>{crumb}<h1>{date}<span class="dow">{dow}</span></h1>
<p class="where">{venue}</p>
<p class="show">{tour}</p>{rating}{aside}{live}</header>
<section class="hero">{hero}</section>
<div class="rule2"></div>
<p class="links">{links}</p>
{sections}{notes}
<footer><span><a href="../method.html">How this is worked out</a></span>{theme_ui}
<span>{stamp}</span></footer>
{analytics}
</div>{row_js}</body></html>
"""


# Site favicons, fetched once and inlined as 32px PNGs. Embedded rather than
# hotlinked for the same reason the fonts hurt: a page saved out of a chat has
# no network, and a badge with a broken image looks worse than no badge.
ICON_PNET = "iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAJM0lEQVR42pWXe1BU1x3HP3ef7C4Lyy6wwAYUARVQAopR4yPWRC3SpJE4SZ2k0UmtSSeTadNJJo8/OomtZhIzJm1m0hgz0zhO6jimRuMQdEtsxuIDDI8QKhUBkYcLbFgey7LL7rK//gEB8d3fzJ07c+65v+/nnvO953eOIiLC/xk+n4+Ghgbq67/nyJEjGAxR1NTVsqAlwK+YhRoFADUKjYqXsgUG/nJoPz2ubqqqzvPlsS+pr/+O4WEfyt0AjI2N4fV66e3txel0cv78eXp6eli+fAUPrl7NkWNHOfTeHl4eTScLMxHGU2pQOKH08sVsIT//XiqrqujvcKEKR7BrjDjCOjR3Eu/v76eyspKqqira2tpwuVykpqby8ccfo9PrCQaD1NfVsyhoJoPoSXEAP2M0yiCXmlwEL7YzCyM/IYN0olGPKTQxdOcROHfuHJ999hmrVq0iKyuLoSEvu955m5jYGHRBP0OePqprv+OxPjurlQQ0okwihBFO0I2fMRZjxYEBDSrCRChX3FTda74zwOjoKD6fj6ioKOrr69m5cyelJ+uIRCK8kB7kpXQD34Z97G4KsOCKg4cj9sl3FRTCRFChoEJBEAKM8RXdjJQU8vIf/3DnKdDr9ej1er44coSD+/ZTW1MLiQ+BLpmDA19QovNQYrERws2brna0AYUoFDoYpVsfIj6o8HNJwYaeMEKZ0oOnaB5/emcHWRmZdwYAqKmr5R97/8a2hNk0xnjoVGZCVDK9ygY+uHSUaLuHVrcKc0aQi0lNxNus9PYL/zrjITMUy3pJwk+Y04qHr5NDvL3tGbIyMieMepPw+/14vV60Wi0Go5Hjh4/yG3MG2ZoYfKEoiE4ACYMqlrLuaDqHG1mxwc5HvywgLS2EzWajrGyQitMDJEai+Jwe2vHRpfERHoW3du7gq9LjPP74Yzd6wOPxsGPHDo4ePUpSUhJZWVn0dV5l56xlhMeC/PSf/8atz0eGW5hla6SkWGHTJgvzcqxotdrJPBcueHjvjcv8t6WPKFuElNQ0MmaqSb3Hx4ULag4fvkpv73UmjESEXbt2sX37m4yMjEwmMxiNzE9JIxKJUNPpQoWK5Us1/PZ30axbl47BoAfUgExc4yGDEa784CYmDqzWhIk+ABHOnm1m79726QB1dXWUlJRw+fLlO/oiOlqDw2Hg/vtDLF2WTE5eLAW5FoxGwzQIUE2KTg8hEAhNB3jxxRd5//330ev1iAjBYPCul+eUmbBovoVVSw2seSSF9PRYjEbttK8WEfz+EDqdFo1GRXPLFZCJaG1tlcLCQlEURUwmk+h0OgFFUlI0sn69RaxWs1wzxre8tGrEbtfIxo162bs3Xaqq8sXjKRCRdeL3Pyivvx4tBw9miMg6OXk4RyYBysvLxWaziVqtFq1WI4DMmGGWsrICGRxcLps3JwoodwUBiEaDGI3IjBnImjVqeemlGXLggF2WLFFk2TKzePofEBksmgJwOp0SFxc3mcBkQj74IFFE1opIkZSW5ktcnPauxDMyVPLuu3bZv98uOTkqASQ3F8nORkwmrcTGKnLqVKqIXAPQ2dkpa9asmUyyerUivb0LRGS9iKyXpqZ7paDgzuKJiRo5cGB8iEXWyUcfZUpCgiLHjlnk7Nn58sILZlEU5JVXZolIkfxoURwOB7t372bhwkKio7U880wWCQnxE+4VUlMNpKZG3daIigJPP53CE09kAgqgZsUKM+npQn+/gSVLUnn11TkUF0dx6VI/o6Mjk/8IAOXlX+NyXWXTJiMbN6Zd8wsJUVFx2O3JtwWw29U89VQCijKV1uEYw2qF6upoQEhJSWDbNgvunn6aLvZNB6ioOINOd5Xnn78HvV57g0Bm5iiaW1aPcfHcXOs164BgMBhRq/VcvTq1sM2ZY+GHbg1tTcoUwNmzZzl3rpKly2zk5SXcVGLpUjVm883li1fE8/utuWg06mntOp0Ng8HK8LCbwKgHAJstFa0pgarv2qcAWltbcfd1MDffgKJcv5qNf83ChRls3hyPxTI1DHPnwnPP2fnzJ4kkz9Fd6wh6e/u5dKmTwUE/oSGF0ODEXlEtmM0BGhoGp6qhSqWCSIQUy9gt59hoNPDGG/MoKhqmry+MSiXk5MC83DgU1Y/QCqDwn9peXnutnjZXkOZmWLvcQJR+/FkgEKKjI8xA8LpyrFJBdPTtbCbExhpYu9YwITTV/qN4MOinpdXNXz9ppqLSjFqjwT/iptPjp6W7m7mxOpzOJtxuL+0d1wEEAlBdo+eJX0QYt4fcFGL6fbKW0tJyhQ8/dFFePkRHJywsXElaWiptbW1cuFDDr7deISnpB6qq/KjVMTzy8KobNyT7/t5NfLKOLZvisSfF3kLs+lBx8WIfzz7bTnu7HbM5k4xZahyOFGJiYpg/fz5Wq5WamnpOn76MSJiSkofYs2fPVDXs6Ohg69atOJ1O9HoNhYVaiotjWbvWQmamA4Mhgk6nu6buRxgdDeHzqamp6WTXrkEqKoZ59NGfkZiYiIhw7V5HRBgZGaGnp4fGxkbC4TCFhYXTy7HL5WLLli04nc4Jt4LNpmP2bB0FBUFyclKwWm1otVrc7h6+/babM2fMBAJuZs4UGhoUZsxYzOLFi1CpVJMAiqLQ09NDbW0tGRkZxMfH4/V6uXz58o1bso6ODsrKyti+fTtdXV3k5Wl48skxBgZ0NFyA3kEzowMxiHjIzPSxaFEs993nID8fPv20i7fe8uFwzCEvLw+LxYKijJvV6/Vy5swZOjs7MZvN2O129Hr9rc8FTqeTQ4c+5+TJUh54wE1xcTqJiQqO1GgsMTYUJYJeH8FoVANaQMHlcrFhw0UqK31YLBays7PJysqaBAmFQjQ3N1NdXU1fXx8FBQW3P5iMjY1x/PgJSku/oqamApFWrHEhkpLjyc0dJTtbGBpS8HgidHVF0dIS5PvvzRQVPYparWbfvn1EIhHi4+NJS0sjMTERk8nEwMAA33zzDXl5eXd3OA0Gg3i9Xqqr6zh+/AQulwu9Pkwk4mNgYJjY2DhMJhuzZ89j1arl5OXlAXDq1ClKS0upqKigq6sLn8+HyWTCaDQiIqxcufLuAG4VIyN+hoaGSEhIQK1W3bJfS0sLzc3N9PX1EQgEAEhOTmbJkiX8Dy6oalTSw0WAAAAAAElFTkSuQmCC"
# phish.in's mark ships around half-transparent -- a mean alpha of 130 where
# phish.net's is fully opaque -- which reads as a grey smudge on cream and as
# nothing at all on near-black, whichever way it is inverted. Alpha is the one
# thing a CSS filter cannot raise, so the shape is made opaque here instead.
ICON_PIN = "iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAACAUlEQVR42s2Xz2djURTHP0kqPMIwlBKGUoZQwlRWIausQukopaWmsuowZgyl/SO67X8xs+i2225a7bYMQyndtJTwCCFeN9/HdZv77n3pq9cvR17uPe/8vOfc86BkVIznGtAAFg1qAJH2psAYGAGPwD3wpLVC8BHoAkkgfQM+A/XXKu4AmzkU27QNLCtSIajbRicF0KGM8KEBNEVRkQakKXFFoQmsW/zrSmGwggOgDwwzeNry0kQEbDj4f+MQMpix3jWE9hwCh/LW9HzL49gLJasZ3qVY9kQhxYYvslUrXGOF2cYP1XyKGPjqyHck6gB/fafSNqAHHM/gO1PzMUupkSF3BbgI7QMhB9BGK4N3oAMbIrdFYHnZGHiqJUR5Ry3ey9i18tsqqG/sqwOz72E0O1y7wMaVAEkNuAIeFNZZ+C+v+8Cft7iSV4r2Kg9V0zyUOZAkZRpQLXskK9uAI15Zx90iDuE82AFOA/h++RgWHOt7uv2awImxvgucA7fGtZyF63kNuNbtVwfW1LNjYyQPze94XgNupRDgLuP9OGNv5Nl3VsH3kBeFR6XFZcCT5OUy4CbHYRxl5PlejlzmGUi2raHSh/Rz7osxBxxo5F7S/gdHuQ6BfgX4qVD+U75HwGSO0qynA4Yw0fekaWhkzJ4xMK0An8Qc63fyRl2vZv2f8h7wDEQBdexwLq8GAAAAAElFTkSuQmCC"
ICON_FOUL = "iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAC7UlEQVR42u2Xz2tcVRTHP+e+Nz+a2MTa4Ewy0zSpq7ZiFwWhCEIRoxWULhztdBItRbKwW3fdduHfUBDFYIM/diq6cS2KoNAWwSyqTjLMpLVEW9PJzLv36yIabcvUZGZUhJztvfe8zz3nnvM9D7Zt27q0y6WD6dqLo/t79eO6Pbgrvv6qi6n0ChB3c+jq6ZGdfs3tBQ3+VHlgaLU10E7HraHc/HLjHwMQWKOcO+qJcoH4CwhDIN8meyyV1jWv1BHg3FYBbLMbGy+MHQ8Rz4I1cfKGG4TggYvIhkETmXT6tV1vfb/Stwg0KuOPBZIpF5Kvvdkxk9apxcAf6IYdwEkK0FxrTwHv9QXgyqmJrK21SxjDuMxuk0+tZ+LO1ChCLoIgRyj2rQqySfu5gHZuxZlwe+ozucG7IlkuHKmVi9ObArj2UrFQr4yedcGPb/U2QmlH/Iz+8rbqM7lJmZ1wCo83pguH7gmg2cOpJPEvI5sMcpNdFbbXU8snR6c2fPr4aUkxDieFE9VScUdHgKutH3dj0UO9NJYgLDj3qMA0eziFNPHnavRgKq0nOgIkSfp0X/p00D5KxezSzfpBYOSO1UMdAeIQdvRNLLJt5wjRXe/ElHQEaGfsvBS+6/Xbhi0w11hNx1EdY+224MC3HQEKb9aqKHwUgvmeFE66YaCRtxeXTNrojGb6OTL/2T3LcHS+ftlMK13dXCTAApH7ZCPkkRYAFGhK9lV+rvHr33dCs0+Rnse4CQxtnsBCfn7p9dty7t2HjjCcRO6D4juLi5sWo5WZvZPNVhhUlJxxFvsgP4AQWNNMGczZ72IEuAgFefi8cKH2Rl9a8f1zP1zJv1u95MwuAjhjtcPWWxJVgNh0ve9yrBJR1e3ZT5ZbUcvPOuw+M9pgERYyJt1wRtXLHs5fqL3S94HE3sdD9RLA8snCvBfTgo9BRw3yMvuyZXwD/pd/bRhdV7jxJ+uVsfONcvGR/2QqVomoUR47vv1/sG3/e/sNrEkrwQ1sbIcAAAAASUVORK5CYII="

# Last field flags an icon that is solid black on transparency, which needs
# inverting to survive the dark palette.
SHOW_LINKS = (
    ("phish.net", "https://phish.net/setlist/?d=%s", ICON_PNET, False),
    ("phish.in", "https://phish.in/%s", ICON_PIN, True),
    ("fouldomain", "https://fouldomain.com/shows/%s", ICON_FOUL, False),
)


def _show_links(date, on_phishin=None):
    """Badge links out to the sites that hold the rest of the story.

    phish.in only appears once they actually have the show. They post audio a
    while after the night, so the page most likely to be shared -- tonight's,
    while it is being played -- was the one guaranteed to link to a 404. When
    the catalogue has not been fetched the link is shown as before, because a
    missing local file is not evidence of a missing recording.
    """
    return "".join(
        "<a class='badge' href='%s' target='_blank' rel='noopener noreferrer'>"
        "<img class='%s' src='data:image/png;base64,%s' alt='' "
        "width='13' height='13'><span>%s</span></a>"
        % (url % date, "flip" if flip else "", icon, label)
        for label, url, icon, flip in SHOW_LINKS
        if label != "phish.in" or on_phishin is None or date in on_phishin)


# Below this many prior performances a song has no meaningful "typical", so it
# gets numbers but no verdict. A song played four times cannot be overdue.
MIN_HISTORY = 8

# The "typical" gap is measured over this many years before the show, never
# over all of history. Forty years of a working band is several different bands:
# the 1990s dominate any all-time figure, when they played far more shows a year
# out of a smaller catalog, so all-time gaps are much shorter and 59% of this
# archive came out overdue -- a word that means nothing if it fits three songs
# in five.
#
# Counting performances instead of years does not fix it, because a window of
# 20 performances is two years for a staple and twenty-four for a rarity: Kung's
# last 20 reach back to 1995, and every one of Big Ball Jam's is inside 1994.
# Their medians are true statements about a band that no longer exists. Bounding
# by time means a song has to have been in rotation lately to be judged at all.
RECENT_YEARS = 10

# Gaps outside the middle 70% of that window get a verdict. Over the 2026 tour
# quartiles called 37% of songs overdue, too many to carry weight; this yields
# 13% premature, 67% expected, 20% overdue, with 9% of songs unrated for want of
# recent performances -- which is the honest answer for a bustout.
BAND = (.15, .85)

# A song out of rotation and gone this long is a bustout rather than an
# unrateable blank. It also has to have been played MIN_HISTORY times at some
# point: Sightless Escape at four plays ever, or Cream at one, are rare new
# songs, and calling their return a bustout would be nonsense. 100 sits where
# phish.net's own setlist notes use the word -- they called Kung at 258 and
# Sparks at 357 bustouts on 2026-07-24, and did not use it for Weigh at 88.
BUSTOUT_GAP = 100


def _quantile(vals, q):
    """Linear-interpolated quantile of an unsorted list."""
    if not vals:
        return None
    ordered = sorted(vals)
    if len(ordered) == 1:
        return float(ordered[0])
    pos = (len(ordered) - 1) * q
    low = int(pos)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (pos - low)


def _years_before(iso, years):
    d = datetime.date.fromisoformat(iso)
    try:
        return d.replace(year=d.year - years).isoformat()
    except ValueError:                      # 29 February
        return d.replace(year=d.year - years, day=28).isoformat()


def _classify(gap, prior, on_date, plays=None):
    """Where this gap sits against how the song has behaved lately.

    `prior` is the song's performances before this one, each a row with a
    showdate and a gap. Only those within RECENT_YEARS of the show count, so
    the answer describes the rotation the band was in at the time rather than
    the one they were in decades earlier -- see the note on that constant.

    Percentiles rather than mean and standard deviation, because gap
    distributions are savagely right-skewed: a rotation staple with a median of
    6 carries a handful of 200s, and a standard deviation over that would call
    almost anything expected.

    A song without enough recent performances to judge gets no verdict, because
    there is no current norm to be early or late against. If it has also been
    gone a long time, that is a bustout, which is the more useful thing to say
    about it anyway.
    """
    cutoff = _years_before(on_date, RECENT_YEARS)
    recent = [int(h["gap"]) for h in prior
              if h.get("showdate", "") >= cutoff
              and str(h.get("gap")).lstrip("-").isdigit()]
    stats = {"plays": plays, "recent_plays": len(recent), "gap_median": None,
             "gap_mean": None, "gap_low": None, "gap_high": None,
             "verdict": None}
    if len(recent) >= MIN_HISTORY:
        stats["gap_median"] = _median(recent)
        stats["gap_mean"] = sum(recent) / len(recent)
        stats["gap_low"] = _quantile(recent, BAND[0])
        stats["gap_high"] = _quantile(recent, BAND[1])
        if gap is not None:
            stats["verdict"] = (
                "premature" if gap < stats["gap_low"] else
                "overdue" if gap > stats["gap_high"] else "expected")
    elif gap is not None and gap >= BUSTOUT_GAP:
        # The gap alone decides it. This used also to require more than
        # MIN_HISTORY performances, meaning to screen out a new song whose
        # return is not a bustout because it never went anywhere -- but a gap
        # counts shows, so a gap of 485 already proves the song has been in the
        # catalogue for 485 shows. Nothing new can reach the threshold: Cream's
        # largest gap ever is 17. All the test actually screened out was songs
        # that are *rare*, which is the whole population the word is for --
        # Back in the U.S.S.R., four plays between 1994 and 2026, returning
        # after 485 shows, was being called nothing at all.
        stats["verdict"] = "bustout"
    return stats


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


def _band_pos(gap, low, high):
    """Where this gap sits against the song's own band, as 0-100 across a track.

    The old bar drew each gap as a fraction of the longest gap in the show,
    which works until a bustout is in the room -- and on 168 of 690 shows the
    longest gap is at least twenty times the median, so about 95% of that
    night's bars collapse into one flat nub a couple of pixels long. A scale
    that one row can destroy for every other row is not a scale.

    So the bar stops measuring magnitude, which the printed number already
    gives exactly, and measures the only thing the number cannot: whether this
    was early or late *for this song*. Every row gets its own scale, which is
    the point -- Tweezer's 9 and Cold as Ice's 1,468 are both ordinary against
    their own histories, and both should read that way.

    The band [low, high] occupies the middle 40% of the track, so a gap inside
    it lands in the middle and one outside it visibly leaves. Beyond the band
    the mapping saturates rather than running off: at three times the high mark
    it reaches the end and stays there, because past a point "very late" is the
    whole of the message and a longer bar does not add to it.
    """
    if high is None or low is None or high <= 0:
        return None
    if gap <= low:
        return 30.0 * (gap / low) if low > 0 else 0.0
    if gap <= high:
        return 30.0 + 40.0 * (gap - low) / (high - low) if high > low else 50.0
    over = (gap - high) / (high * 2.0)
    return 70.0 + 30.0 * min(1.0, over)


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


def era_ordinal(dates, date):
    """"nth show of 3.0", or None where that cannot be said honestly.

    An absolute ordinal cannot: phish.net offers three defensible totals for
    how many shows Phish has played -- 2,239 rows, 2,114 that count toward
    statistics, 2,106 distinct dates -- and 1983-10-30, the show everyone calls
    their first, is flagged exclude_from_stats, so a stats-based count declares
    the second show to be number one. Any figure we printed would be
    confidently wrong against the one the reader already has.

    Inside an era it can, for three of the four. Six dates carry more than one
    counting show and all six are in 1.0, the earliest being 1985-02-25 -- so
    the drift is not confined to six shows, it is inherited by every show after
    them, roughly 1,350 of 1,361. 2.0, 3.0 and 4.0 are one show per date
    throughout, so the count is exact rather than approximately right.
    """
    label = era(date)
    if label == ERAS[0][0]:
        return None
    start = next((s for l, s, _ in ERAS if l == label), None)
    if not start:
        return None
    n = sum(1 for d in dates if start <= d <= date)
    return (n, label) if n else None


def _ordinal(n):
    """1 -> 1st. 11, 12 and 13 are the ones that break the naive rule."""
    suffix = "th" if 11 <= n % 100 <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return "{:,}{}".format(n, suffix)


def render_html(report, bar_scale="linear", index_href=None,
                prev_date=None, next_date=None, songs=(), card=None,
                archived_show=(), sheet="../fonts.css", calendar=(),
                on_phishin=None):
    # Whether this is a show at all. A soundcheck's songs are real and its
    # gaps are phish.net's, but nothing here feeds the rest of the site, and a
    # count of bustouts is a verdict wearing a number's clothes.
    counts = not calendar or report["date"] in set(calendar)
    allg = [s["gap"] for s in report["songs"] if s["gap"] is not None]
    biggest = max(allg) if allg else 0
    avg = _stat(sum(allg) / len(allg)) if allg else "n/a"
    med = _stat(_median(allg))
    longest = _stat(biggest) if allg else "n/a"
    show_last = any(s["prev_date"] for s in report["songs"])

    hero = "".join(
        "<div class='card'><div class='lbl'>%s</div>"
        "<div class='num%s'>%s</div></div>" % (lbl, cls, val)
        for val, lbl, cls in (
            (len(report["songs"]), "Songs Played", ""),
            (longest, "Longest Gap", " hot"),
            (med, "Median Gap", ""),
            # Not the mean. A gap distribution with one 1,947 in it has a mean
            # that describes no song in the setlist -- across this archive it
            # runs to twice the median on 48% of shows and 253x on one of them.
            # The count of bustouts is the thing the mean was standing near.
            (sum(1 for s in report["songs"]
                 if (s["gap"] or 0) >= BUSTOUT_GAP), "Bustouts", ""),
        ) if counts or lbl != "Bustouts")

    sections, rows, current = [], [], None

    def flush():
        if current is None:
            return
        # In the same order as the header below, which it was not: the last
        # column was emitted as c-last, so the widths came to 26 + 42 + 12 + 42
        # and the table was 122% of its container -- which is why a report
        # scrolled sideways on a phone. Without the Last Performed column it
        # was worse than wrong, it was misaligned: three cols against three
        # headers, but c-last landed on the bar and c-bar on the gap.
        cols = ("<colgroup><col class='c-song'>"
                + ("<col class='c-last'>" if show_last else "")
                + "<col class='c-bar'><col class='c-gap'></colgroup>")
        head = ("<th>Song</th>"
                + ("<th>Last Performed</th>" if show_last else "")
                + "<th></th><th class='n'>Gap</th>")
        sections.append("%s<h2><span class='tab'>%s</span></h2>\n"
                        "<table%s>%s<thead><tr>%s</tr></thead>"
                        "<tbody>\n%s\n</tbody></table>"
                        % ("<div class='perf'></div>" if sections else "",
                           html.escape(current),
                           "" if show_last else " class='no-last'",
                           cols, head, "\n".join(rows)))

    for s in report["songs"]:
        if s["set"] != current:
            flush()
            current, rows = s["set"], []
        g = s["gap"]
        klass = "big" if (g or 0) >= 50 else "small"
        # How this song usually behaves: printed small under the number, and
        # marked on the bar so an overshoot is visible rather than arithmetic.
        # Free for anyone who hovers, no clutter for anyone who does not.
        # data-tip rather than title. The browser's own tooltip waits about a
        # second before it appears, which is far too long for a mark whose
        # whole job is answering "what is this?" -- by then the pointer has
        # moved on. aria-label carries the same words to a screen reader,
        # which title was doing incidentally.
        explain = ""
        if s.get("gap_low") is not None and g is not None:
            tip = ("%s show%s; usually %s to %s"
                   % (_stat(g), "" if g == 1 else "s",
                      _stat(round(s["gap_low"])), _stat(round(s["gap_high"]))))
            explain = " data-tip='%s' aria-label='%s'" % (tip, tip)

        typical = ""
        if s.get("gap_median") is not None:
            # The median alone. The mean sits within 20% of it for two thirds
            # of songs, so it earned its space rarely, and the percentile band
            # that actually decides the verdict read as jargon on the page --
            # its ends are interpolated values that appear nowhere in the
            # song's real gaps. Both are still archived in the JSON.
            typical = "<span class='typ'>med %s</span>" % _stat(s["gap_median"])
        elif s.get("recent_plays") is not None:
            # No norm to compare against, so say why: this is how thin its
            # recent record is.
            # Spelt out where there is room, abbreviated where there is not:
            # at 390px "3 in 10 yr" is 72px against a 56px four-digit gap, so
            # the rarest thing in the column was setting its width.
            typical = ("<span class='typ'><span class='full'>%d in %d yr</span>"
                       "<span class='abbr'>%d/%dy</span></span>"
                       % (s["recent_plays"], RECENT_YEARS,
                          s["recent_plays"], RECENT_YEARS))
        # Where a verdict goes depends on what kind of thing it is. A bustout
        # is remarkable about the song -- it belongs against the title, next to
        # the jam chart chip, which is likewise about the song and not its
        # timing. Premature and overdue are judgements about the number, so
        # they belong against the number, under the median they are measured
        # from.
        #
        # At 390px "premature" is 63px against a 39px figure in a 3.7rem
        # column, so at that width the row's grid moves it out of the figure's
        # cell rather than letting it set the column's width -- see the narrow
        # rules, where it becomes its own line in the song area.
        tag = verdict = ""
        v = s.get("verdict")
        if v == "bustout":
            verdict = "<span class='verdict bustout'>bustout</span>"
        elif v in ("premature", "overdue"):
            # One span, not two. Shipping a copy in each cell and hiding one
            # with CSS meant the aria-hidden was baked into whichever copy the
            # markup called the spare -- so on a phone, where the layout shows
            # that one, the visible verdict was hidden from assistive
            # technology and the exposed one was display:none. No verdict was
            # announced at all on the width where it is the only one shown.
            # It lives in the gap cell and the narrow layout moves it.
            tag = "<span class='verdict %s at-gap'>%s</span>" % (v, v)
        if g is None:
            gap_cell = "<span class='gap none'>&mdash;</span>" + typical + tag
            bar = "<td class='bar'></td>"
        else:
            gap_cell = ("<span class='gap %s'>%s</span>%s%s"
                        % (klass, "{:,}".format(g), typical, tag))
            # Against the song's own band, not the show's longest gap. See
            # _band_pos: a bustout used to set a scale that flattened every
            # other row on the night into an identical nub.
            pos = _band_pos(g, s.get("gap_low"), s.get("gap_high"))
            if pos is None:
                # Too little history to have a norm, so there is nothing to be
                # early or late against and the bar says nothing rather than
                # implying a comparison that was never made.
                bar = "<td class='bar'%s><span class='track bare'></span></td>" % explain
            else:
                # The mark is coloured by where it landed, not by how large
                # the number is. Those are different questions and they
                # disagree: a gap of 10 against a median of 5 sits right of the
                # band and is called overdue, but 10 is under the absolute
                # threshold, so the mark was drawn cool while its position and
                # the verdict beside it both said late. Position is what this
                # graphic encodes, so position is what it may colour.
                where = ("early" if pos < 30 else
                         "late" if pos > 70 else "usual")
                bar = ("<td class='bar'%s><span class='track'>"
                       "<span class='band'></span><span class='mid'></span>"
                       "<span class='at %s' style='left:%.2f%%'></span>"
                       "</span></td>" % (explain, where, pos))
        # Both statistics cells carry the explanation, so the hover target is
        # the whole of them rather than a range bar that can be five pixels wide.
        # The title is the way in to the song's own history, but only once that
        # page exists: a report archived before song pages did has songs the
        # band has not played since, and those get a page when they next come
        # round rather than a link to nowhere now.
        title = html.escape(typographic(s["song"]))
        href = ""
        if s["slug"] in songs:
            # Anchored at this very performance, so the link answers "where
            # does tonight's version sit against all the others" rather than
            # dropping you at the top of a six-hundred-row page to go looking.
            href = "../song/%s.html#%s" % (
                html.escape(s["slug"], quote=True),
                html.escape(report["date"], quote=True))
            title = "<a href='%s'>%s</a>" % (href, title)
        # phish.net wrote something about this one. The prose itself lives on
        # the song page, so this says so and points there rather than repeating
        # it here: a report is one night's gaps, and a paragraph per song would
        # bury them. A dot used to mark these, which told nobody anything.
        # Its own link rather than part of the title's, so the segue mark can
        # sit between them -- see below.
        chip = ""
        if s["jamchart"]:
            chip = ("<a class='jc-chip' href='%s'>Jam chart</a>" % href if href
                    else "<span class='jc-chip'>Jam chart</span>")
        # Outside the link, so the mark is not underlined with the title and
        # cannot be mistaken for part of the song's name.
        seg = ("<span class='seg%s'>%s</span>"
               % (" tight" if s["out"] == "->" else "", html.escape(s["out"]))
               if s.get("out") else "")
        # Song, then how it left, then everything said about it. The mark is
        # setlist notation and belongs against the title the way it is written
        # -- "Ether Edge >" -- not stranded past a chip, where it read as
        # punctuation belonging to the chip.
        cells = "<td class='song'>%s%s%s%s</td>" % (title, seg, chip, verdict)
        if show_last:
            if s["prev_date"]:
                # No <br>: the spans are blocks on wide layouts and inline on
                # narrow ones, so CSS alone decides how they stack. Empty ones
                # are dropped rather than left to grow a stray separator.
                # We very likely hold that show too -- 23 of 26 on a typical
                # report -- and "what else happened the last time they played
                # it" is the most natural click on the page. It was dead text.
                stamp = s["prev_date"]
                if stamp in archived_show:
                    stamp = ("<a href='./%s.html'>%s</a>"
                             % (html.escape(stamp, quote=True), stamp))
                bits = ["<span class='cap'>Last performed</span>",
                        "<span class='date'>%s</span>" % stamp]
                for cls, text in (("venue", s["prev_venue"]),
                                  ("place", s.get("prev_place"))):
                    if text:
                        bits.append("<span class='%s'>%s</span>"
                                    % (cls, html.escape(text)))
                cells += "<td class='last'>%s</td>" % "".join(bits)
            elif s.get("debut"):
                cells += ("<td class='last'><span class='cap'>Last performed"
                          "</span><span class='none'>debut</span></td>")
            else:
                cells += "<td class='last'></td>"
        # The bar and the figure close the row, which is where the song page
        # puts them too.
        cells += "%s<td class='n'%s>%s</td>" % (bar, explain, gap_cell)
        rows.append("<tr>%s</tr>" % cells)
    flush()

    notes = ""
    if report.get("notes"):
        notes = "<div class='notes'>%s</div>" % report["notes"]

    # Walking a tour without going back to the index. The first and last shows
    # the site knows about simply have one fewer link; the grid holds the
    # index link in the middle either way.
    crumb = ""
    if index_href:
        step = ("<a class='%s' rel='%s' href='./%s.html' "
                "aria-label='%s show, %s'>%s</a>")
        # Two rows, deliberately: the section links read the same as every
        # other page type, and the pager sits under them. Appending them to a
        # three-column pager grid left them wrapping into cells meant for
        # something else.
        crumb = ("<nav class='crumb sections'>"
                 "<span class='mark'>Possum Logic</span>"
                 "<a href='../index.html'>Shows</a>"
                 "<a href='../songs.html'>Songs</a>"
                 "<a href='../due.html'>Due</a>"
                 "<a href='../method.html'>How this is worked out</a></nav>"
                 # No "All reports" in the middle: the row above already has
                 # Shows, pointing at the same page under the name the rest of
                 # the site uses for it. The pager is for the two neighbours.
                 "<nav class='crumb pager'>%s%s"
                 "</nav>") % (
            step % ("prev", "prev", prev_date, "Previous", prev_date,
                    "&larr; " + prev_date) if prev_date else "",
            step % ("next", "next", next_date, "Next", next_date,
                    next_date + " &rarr;") if next_date else "")

    # What a chat client shows when someone drops the link in a thread. Plain
    # text, entities and all, because html.escape has the last word on it.
    # The share text must agree with the share image. The card for a show in
    # progress deliberately carries no figures, so a description asserting a
    # song count and a longest gap contradicts the picture above it -- and both
    # are frozen into somebody else's timeline the moment they paste the link.
    if report.get("provisional"):
        blurb = "%s \u00b7 being played now, setlist still coming in" % report["venue"]
        allg = []
    else:
        blurb = "%s \u00b7 %d songs" % (report["venue"], len(report["songs"]))
    if allg:
        blurb += " · longest gap %s (%s)" % (
            longest, next((s["song"] for s in report["songs"]
                           if s["gap"] == biggest), ""))

    # phish.net files one-offs under "Not Part of a Tour", which is not worth
    # saying out loud.
    tour = report.get("tour") or ""
    tour = ("<span class='tour'>%s</span>" % html.escape(tour)
            if tour and "not part of a tour" not in tour.lower() else "")

    # Era-scoped, because an absolute one cannot be said honestly -- see
    # era_ordinal. Silent for 1.0 and for anything not on the calendar, which
    # is where the soundchecks and sessions land.
    place = era_ordinal(calendar, report["date"])
    if place:
        tour += ("<span class='nth'>%s show of %s</span>"
                 % (_ordinal(place[0]), place[1]))

    # phish.net's own rating for the night, which their API does not expose --
    # fouldomain does, so it is theirs by way of someone else and says so.
    # Absent for a show played last night, which simply has no line.
    # Still coming in. Said plainly, with the two facts that make it useful:
    # how much is here, and when it last moved. The reload keeps a page open on
    # a phone in a parking lot current without anybody touching it.
    # Not a show. Its pages exist and its songs are real, but nothing on it
    # feeds a gap, a median or a verdict, and a reader who arrived from the
    # "Also on file" list should not have to infer that.
    aside = ""
    if not counts:
        aside = ("<p class='aside-note'><b>Not counted</b>"
                 "<span>phish.net does not count this toward a gap, so neither "
                 "do we. Nothing here feeds any figure on the rest of the "
                 "site.</span></p>")

    live = refresh = ""
    if report.get("provisional"):
        # Two clocks, and the second is the one that matters. When the last
        # song arrived says how the show is going; when we last looked says
        # whether this page is still being fed. Without the second, a reader
        # cannot tell a gap between sets from a build that has stopped -- and
        # both look like a page that has not changed for forty minutes.
        since = report.get("count_since") or ""
        checked = _utcnow().isoformat(timespec="seconds")
        n = len(report["songs"])
        # One clock, and it is the one that says whether this page is still
        # being fed. When the last song arrived is on the row it arrived in;
        # repeating it up here as a second wall-clock time said nothing the
        # reader wanted and read like a server log.
        live = ("<p class='live' role='status' aria-live='polite'>"
                "<b>This show is being played right now</b>"
                "<span><b class='n'>%d</b> song%s so far &middot; "
                "last checked <time class='ago' datetime='%s'>%s</time>"
                " &middot; this page refreshes itself</span></p>"
                % (n, "" if n == 1 else "s",
                   html.escape(checked, quote=True), _clock(checked)))
        refresh = '\n<meta http-equiv="refresh" content="120">'

    rating = ""
    if report.get("pnet_rating") is not None:
        rating = ("<p class='rating'>Phish.net rating <b>%.2f</b>"
                  "<span> via fouldomain</span></p>" % report["pnet_rating"])

    return SHELL.format(
        ago_js=AGO_JS,
        new_rows_js=NEW_ROWS_JS,
        analytics=ANALYTICS,
        css=CSS, theme_js=THEME_JS, theme_ui=THEME_UI, fonts=WEB_FONTS,
        date=html.escape(report["date"]), crumb=crumb, tour=tour,
        dow=_full_weekday(report["date"]),
        # A tab left open all night should say what it is holding. Without
        # this the live show's tab is indistinguishable from any archived one.
        titlestate=("(%d) " % len(report["songs"])
                    if report.get("provisional") else ""),
        live=live, refresh=refresh, aside=aside,
        venue=_venue_lines(report), hero=hero, rating=rating,
        links=_show_links(report["date"], on_phishin), blurb=html.escape(blurb, quote=True),
        sections="\n".join(sections), notes=notes,
        sheet=('<link href="%s" rel="stylesheet">' % sheet if sheet
               else inline_font_css()),
        row_js=ROW_JS,
        share=share_meta("%s%s &mdash; Possum Logic"
                         % ("Live: " if report.get("provisional") else "",
                            html.escape(report["date"])),
                         html.escape(blurb, quote=True),
                         "%s/%s.html" % (SHOW_DIR, report["date"]), card=card),
        # Dated by the report's own data, not by the clock. A build stamp made
        # every page differ from yesterday's copy of itself, so a nightly run
        # republished all of them to say nothing had happened. count_since is
        # when this setlist last actually moved; a report rendered outside a
        # site has none and falls back to the night it describes.
        stamp="Updated %s" % (report.get("count_since")
                              or report["date"])[:10])


# ------------------------------------------------------------------ index ---

INDEX_CSS = PALETTE_CSS + THEME_CSS + """
*{box-sizing:border-box}
body{margin:0;padding:clamp(1.4rem,4vw,3.5rem) clamp(1rem,5vw,3rem);
     background:var(--paper);color:var(--ink);
     font-family:'IBM Plex Mono',ui-monospace,SFMono-Regular,monospace;
     font-size:.875rem;line-height:1.55}
.wrap{max-width:960px;margin:0 auto}
/* Which of the two lists you are looking at, and the way to the other one.
   Above the wordmark because that is where a reader looks for it, and because
   the footer link that used to be the only route was found by nobody. */
.crumb{display:flex;align-items:baseline;gap:.9rem;margin-bottom:1.1rem;
   font-size:.625rem;
   letter-spacing:.14em;text-transform:uppercase}
.crumb a{color:var(--dim);text-decoration:none;padding-bottom:.15rem;
   border-bottom:1px solid var(--rule)}
.crumb a:hover{color:var(--hot);border-bottom-color:var(--hot)}
.crumb a.here{color:var(--ink);border-bottom-color:var(--ink);cursor:default}
h1{font-family:'Bagnard',Georgia,serif;font-weight:400;
   font-size:clamp(2rem,7vw,4rem);line-height:1.06;margin:0 0 .7rem;
   letter-spacing:-.01em}
h1 em{font-style:normal;color:var(--hot)}
/* The wordmark goes home, as a wordmark does, without looking like a link. */
h1 a{color:inherit;text-decoration:none}
h1 a:hover em{color:var(--ink)}
/* A hero card that is also a way in. Only some of them are. */
a.card{text-decoration:none;color:inherit}
a.card:hover{background:var(--hover)}
/* Only one of the four cards is a link, so it needs to say so -- but a rule
   under a letterspaced label reads as a stray underline rather than an
   affordance, and it was the one line in the hero not doing structural work.
   An arrow after the label carries the same message and disappears into the
   type. */
a.card .lbl::after{content:" →";color:var(--dim);white-space:nowrap}
a.card:hover .lbl,a.card:hover .lbl::after{color:var(--hot-text)}
header{padding-bottom:.9rem}
.show{margin:0;font-size:1rem;font-weight:600;letter-spacing:0;
      text-transform:uppercase;color:var(--ink-soft)}

/* Letterpress: a thick rule with a hairline under it. Three to a page at most
   -- a double rule that turns up six times is wallpaper. */
.rule2{height:5px;margin:0 0 1rem;background:linear-gradient(to bottom,
   var(--ink) 0 3px,transparent 3px 4px,var(--ink) 4px 5px)}
/* The tear line between one set and the next. Never between rows. */
.perf{height:1px;margin:1.5rem 0 .6rem;background:repeating-linear-gradient(
   to right,var(--edge) 0 5px,transparent 5px 10px)}
.hero{display:flex;flex-wrap:wrap;margin:.7rem 0 .3rem;
      border-bottom:1px solid var(--ink)}
.card{flex:1 1 0;padding:.85rem 1.1rem;border-left:1px solid var(--rule);
   display:flex;flex-direction:column}
.card:first-child{border-left:0;padding-left:0}
.num{font-family:'IBM Plex Mono',ui-monospace,monospace;font-weight:600;font-size:2.25rem;line-height:1;
     letter-spacing:0;margin-top:auto}
.num.hot{color:var(--hot)}
.lbl{font-size:.625rem;text-transform:uppercase;letter-spacing:.14em;
   color:var(--dim);margin-bottom:.35rem}
.tools{margin:1.9rem 0 .9rem}
/* Two rows rather than one wrapping run. The things you operate -- the search
   box and the sort -- sit together on the first; the filter chips are a
   different kind of control and get their own line instead of pushing sort to
   wherever the chips happen to stop. */
.tools-main{display:flex;flex-wrap:wrap;align-items:center;gap:.55rem .8rem}
.tools .chips{margin-top:.6rem}
.search{flex:1 1 15rem;min-width:0;font:inherit;font-size:.875rem;
        padding:.5rem .7rem;border:1px solid var(--edge);border-radius:0;
        background:transparent;color:var(--ink)}
.search::placeholder{color:var(--dim)}
.search:focus-visible,.chip:focus-visible,.sort:focus-visible{
  outline:2px solid var(--hot);outline-offset:1px}
/* Shown only once there is something to clear. The song page has carried this
   button for a while; the index only ever had the line of script that hides
   it, which is why that line referred to an element that was never here. */
.clear{font:inherit;font-size:.625rem;letter-spacing:.14em;text-transform:uppercase;
   padding:.45rem .6rem;border:1px solid var(--edge);background:transparent;
   color:var(--dim);cursor:pointer}
.clear:hover{color:var(--hot);border-color:var(--hot)}
.clear:focus-visible{outline:2px solid var(--hot);outline-offset:1px}
.chips{display:flex;flex-wrap:wrap;gap:.3rem}
.chip{font:inherit;font-size:.625rem;letter-spacing:.14em;text-transform:uppercase;
      padding:.42rem .6rem;border:1px solid var(--edge);background:transparent;
      color:var(--dim);cursor:pointer}
.chip:hover{color:var(--ink)}
.chip.on{background:var(--ink);color:var(--paper);border-color:var(--ink)}
/* How many shows the era holds, so four chips carry the information the
   forty years did without the forty buttons. */
.chip-n{font-family:'IBM Plex Mono',ui-monospace,monospace;font-weight:600;
   letter-spacing:0;color:var(--dim);margin-left:.3rem}
.chip.on .chip-n{color:var(--paper)}
.sort{font:inherit;font-size:.75rem;padding:.4rem .3rem;background:transparent;
      color:var(--ink);border:1px solid var(--edge);border-radius:0}
.count{font-size:.625rem;letter-spacing:.14em;text-transform:uppercase;
       color:var(--dim);margin-left:auto}
.count b{font-family:'IBM Plex Mono',ui-monospace,monospace;font-weight:600;
         font-size:1rem;color:var(--ink)}
.reports{list-style:none;margin:0;padding:0;border-top:1px solid var(--rule)}
.row{display:grid;grid-template-columns:7.2rem 1fr 20.4rem;column-gap:1.1rem;
     align-items:baseline;padding:.7rem .25rem;text-decoration:none;
     color:inherit;border-bottom:1px solid var(--rule-soft)}
.row:hover{background:var(--hover)}
/* Same rule, same reason: this is the one place the site still spoke two
   languages, since the song pages had already moved. */
/* Data in a column, so the mono: tabular by construction, which is what makes
   710 dates present one edge to the venue beside them rather than a soft
   ragged one. The display face keeps the mastheads, where a date is the name
   of the page rather than a value in a list. */
.r-date{font-family:'IBM Plex Mono',ui-monospace,monospace;font-weight:600;
        font-size:1rem;line-height:1.3rem;white-space:nowrap}
.r-venue{font-size:.875rem;font-weight:500;letter-spacing:0;
         line-height:1.3rem}
.r-place{display:block;color:var(--dim);font-size:.75rem;line-height:1.15rem}
/* Deliberately not a report row. These are on file, not on the bill: smaller,
   dimmer, no figures, and below the empty-search message so a search matching
   nothing cannot look as though it matched these. */
/* The due list. Same row grammar as the show index -- identity, context,
   figure -- so the two pages read as the same object seen from two sides. */
.onstage{display:flex;flex-wrap:wrap;align-items:baseline;gap:.3rem 1.1rem;
   margin:1.1rem 0 0;padding:.7rem .9rem;color:inherit;text-decoration:none;
   border-left:4px solid var(--hot);background:var(--hover)}
.onstage:hover{background:var(--hot);color:var(--paper)}
.onstage .k{font-size:.625rem;letter-spacing:.14em;text-transform:uppercase;
   color:var(--hot-text);font-weight:600}
.onstage:hover .k,.onstage:hover .n b,.onstage:hover .p{color:var(--paper)}
.onstage .w{font-size:1rem;font-weight:600;letter-spacing:0;text-transform:uppercase}
.onstage .p{display:block;font-size:.75rem;font-weight:400;color:var(--dim);
   text-transform:none;letter-spacing:0}
.onstage .n{margin-left:auto;font-size:.625rem;letter-spacing:.14em;
   text-transform:uppercase;color:var(--dim)}
.onstage .n b{font-family:'IBM Plex Mono',ui-monospace,monospace;font-weight:600;
   font-size:1.125rem;letter-spacing:0;color:var(--ink)}
.due{list-style:none;margin:0;padding:0;border-top:1px solid var(--rule)}
.due li{border-bottom:1px solid var(--rule-soft)}
.due .row{display:grid;grid-template-columns:1fr 12rem 7rem;column-gap:1.1rem;
   align-items:baseline;padding:.6rem .25rem;color:inherit;text-decoration:none}
.due .row:hover{background:var(--hover)}
.d-song{font-size:1rem;font-weight:500}
.due .row:hover .d-song{color:var(--hot)}
.d-date{font-family:'IBM Plex Mono',ui-monospace,monospace;font-weight:600;
   font-size:.875rem;white-space:nowrap}
.d-where{display:block;color:var(--dim);font-size:.75rem}
.d-n{text-align:right}
.d-n b{font-family:'IBM Plex Mono',ui-monospace,monospace;font-weight:600;
   font-size:1.5rem;line-height:1;color:var(--hot)}
.d-n .typ{display:block;font-size:.75rem;color:var(--dim);margin-top:.15rem}
.dek.foot{margin-top:1.4rem;max-width:64ch}
@media screen and (max-width:620px){
  .due .row{grid-template-columns:1fr 5.5rem;grid-template-areas:"song n" "last n";
     row-gap:.15rem}
  .d-song{grid-area:song}
  .d-last{grid-area:last}
  .d-n{grid-area:n}
  .d-n b{font-size:1.25rem}
}
.aside{margin:2.2rem 0 0;padding-top:.9rem;border-top:1px solid var(--rule)}
.aside h2{font-size:.625rem;letter-spacing:.14em;text-transform:uppercase;
   color:var(--dim);margin:0 0 .3rem;font-weight:400}
.aside>p{margin:0 0 .7rem;font-size:.75rem;color:var(--dim);max-width:68ch}
.aside ol{list-style:none;margin:0;padding:0}
.aside li{display:flex;flex-wrap:wrap;align-items:baseline;gap:.5rem;
   padding:.3rem 0;border-bottom:1px solid var(--rule-soft);font-size:.75rem}
.ax-row{display:contents;color:inherit;text-decoration:none}
.ax-date{font-family:'Bagnard',Georgia,serif;font-size:.875rem;
   border-bottom:1px solid var(--rule)}
a.ax-row:hover .ax-date{color:var(--hot);border-bottom-color:var(--hot)}
.ax-kind{font-size:.625rem;letter-spacing:.14em;text-transform:uppercase;
   color:var(--hot-text)}
.ax-venue{color:var(--dim)}
.aside .for{color:var(--dim)}
.aside .for a{color:inherit}
/* A grid, not a right-aligned sentence. Right-alignment pins only the right
   edge; every figure to the left of it still moved row to row with the width
   of the numbers beside it. */
.r-stats{font-size:.75rem;color:var(--dim);line-height:1.3rem;
         display:grid;grid-template-columns:5.4rem 6.4rem 7.4rem;
         justify-items:end;column-gap:.6rem}
.r-stats .st{white-space:nowrap}
/* Tabular numerals do the aligning; the widths these used to be given by hand
   were a workaround for not having asked the face for them. */
.r-stats .st b{display:inline-block;text-align:right}
.r-stats b{font-family:'IBM Plex Mono',ui-monospace,monospace;font-weight:600;
           font-size:1rem;color:var(--ink)}
.r-stats b.hot{color:var(--hot-text)}
/* A show still being played, said in the one place on the row where the
   number it qualifies already is: 24 songs means something different
   tonight than it will tomorrow. */
.live-tag{font-size:.625rem;letter-spacing:.14em;text-transform:uppercase;
   color:var(--hot-text)}
/* The song that held the longest gap, under the figures it belongs to. Named
   for what it is: ".r-song" also means "the song this row is about" on the
   song index, which inherits this stylesheet, and one grid-column rule meant
   for this was enough to wreck that. */
.r-top{grid-column:1/-1;font-size:.75rem;color:var(--dim);text-align:right;
   white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.empty{margin:2rem 0;font-size:.875rem;color:var(--dim);font-style:italic}
footer{margin-top:2.4rem;padding-top:.9rem;border-top:1px solid var(--rule);
       font-size:.75rem;letter-spacing:.14em;text-transform:uppercase;
       color:var(--dim);display:flex;justify-content:space-between;
       flex-wrap:wrap;align-items:center;gap:.4rem .9rem}
@media screen{
}
/* Same lesson as the report tables: stack instead of squeezing columns, so
   the rules still run the full width and nothing has to be hidden. */
@media screen and (max-width:620px){
  .row{grid-template-columns:1fr;column-gap:0;row-gap:.15rem;padding:.6rem 0}
  .r-stats{display:block;text-align:left;white-space:normal}
  .r-stats .st{display:inline;white-space:normal}
  /* Before each but the first, never after: the last .st is not the last
     child -- the song name follows it -- so a trailing separator was left
     stranded at the end of the line with the name wrapped beneath it. */
  .r-stats .st:empty{display:none}
  /* --dim, not --rule: rule is a hairline colour and a glyph drawn in it is
     invisible on the dark paper, the way the separators were. */
  .r-stats .st:not(:empty) ~ .st:not(:empty)::before{content:"\\00b7";
    color:var(--dim);opacity:.7;margin:0 .4rem 0 .35rem}
  .r-stats .st b{min-width:0!important;text-align:left}
  .r-top{text-align:left;display:inline}
  .r-top::before{content:" ("}
  .r-top::after{content:")"}
  .card{flex:1 1 45%;padding:.65rem .55rem}
  .card:nth-child(odd){border-left:0;padding-left:0}
  .card:nth-child(n+3){border-top:1px solid var(--rule)}
  .num{font-size:1.5rem}
  .lbl{font-size:.625rem;letter-spacing:.14em}
  .show{font-size:.75rem;letter-spacing:0}
  .count{margin-left:0}
  .theme{order:1;flex-basis:100%}
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
      clear=document.getElementById('clear'),
      chips=Array.prototype.slice.call(document.querySelectorAll('.chip')),
      era='';
  // Only the eras and the sorts the page actually offers. A hand-typed
  // ?era=90s matching no chip would otherwise hide every row at once, with
  // nothing on screen saying why and no lit chip to click back off.
  var eraOK={}, sortOK={};
  chips.forEach(function(c){ eraOK[c.getAttribute('data-era')]=1; });
  Array.prototype.forEach.call(sort.options, function(o){ sortOK[o.value]=1; });
  // A bare number means that number: searching 8 should find the 8th, not the
  // 18th. Anything else is a plain substring, which is what makes partial
  // venue and song typing work.
  function matcher(t){
    if(!/^\\d+$/.test(t)) return function(hay){ return hay.indexOf(t)>-1; };
    var re=new RegExp('(^|[^0-9])'+t+'([^0-9]|$)');
    return function(hay){ return re.test(hay); };
  }
  function apply(){
    var terms=q.value.toLowerCase().split(/\\s+/).filter(Boolean).map(matcher),
        n=0;
    rows.forEach(function(r){
      var hay=r.getAttribute('data-search'), ok=terms.every(function(t){
        return t(hay);
      });
      if(ok&&era) ok=r.getAttribute('data-era')===era;
      r.hidden=!ok;
      if(ok) n++;
    });
    shown.textContent=n;
    empty.hidden=n>0;
    // The way out of a filter appears only once there is one to leave. This
    // line referred to an undeclared `clear` for as long as it has existed --
    // copied from the song page without the element or the declaration that
    // make it work there. Every keystroke threw a ReferenceError; nothing
    // showed because apply() had already done all its visible work by this
    // point, and there was nothing after it to lose.
    if(clear) clear.hidden=!q.value;
  }
  // The order the rows are actually in, so a page load in the order the server
  // already rendered does not re-append all 691 of them to prove it.
  var ordered='newest';
  function order(){
    var k=sort.value;
    if(k===ordered) return;
    rows.slice().sort(function(a,b){
      if(k==='gap') return b.getAttribute('data-longest')-a.getAttribute('data-longest');
      var x=a.getAttribute('data-date'), y=b.getAttribute('data-date');
      return k==='oldest' ? x.localeCompare(y) : y.localeCompare(x);
    }).forEach(function(r){ list.appendChild(r); });
    ordered=k;
  }

  /* The search is how this archive is read, and none of it was addressable:
     81 shows at MSG, 171 with a Tweezer, 33 in 2015 -- every one a state you
     can reach and cannot send to anybody. q, era and sort now ride in the
     query string.

     Typing replaces rather than pushes. One history entry per character would
     bury the back button -- eight presses to leave a search you typed once.
     A chip and the sort are each a single deliberate act, so those push, and
     back undoes them one at a time. */
  var HIST=!!(window.history&&window.history.replaceState);
  function write(push){
    if(!HIST) return;
    var p=[];
    if(q.value) p.push('q='+encodeURIComponent(q.value));
    if(era) p.push('era='+encodeURIComponent(era));
    if(sort.value!=='newest') p.push('sort='+encodeURIComponent(sort.value));
    // A bare path when nothing is filtered, so the front door keeps a clean
    // URL rather than growing ?q=&era=&sort= just from being looked at.
    var url=location.pathname+(p.length?'?'+p.join('&'):'')+location.hash;
    try{ window.history[push?'pushState':'replaceState'](null,'',url); }
    catch(e){}          // opaque origins (file://) refuse; the page still works
  }
  function read(){
    var out={};
    location.search.replace(/^\\?/,'').split('&').forEach(function(kv){
      if(!kv) return;
      var i=kv.indexOf('='), k=i<0?kv:kv.slice(0,i), v=i<0?'':kv.slice(i+1);
      try{ out[decodeURIComponent(k)]=decodeURIComponent(v.replace(/\\+/g,' ')); }
      catch(e){}        // a stray % is a bad query string, not a broken page
    });
    return out;
  }
  // The page follows the URL, rather than only ever writing to it -- which is
  // what makes both a pasted link and the back button land in the same state.
  function restore(){
    var st=read();
    q.value=st.q||'';
    era=st.era&&eraOK[st.era]?st.era:'';
    sort.value=st.sort&&sortOK[st.sort]?st.sort:'newest';
    chips.forEach(function(c){
      c.classList.toggle('on', c.getAttribute('data-era')===era);
    });
    order();
    apply();
  }

  function setQuery(v){ q.value=v; apply(); write(false); }
  q.addEventListener('input', function(){ apply(); write(false); });
  sort.addEventListener('change', function(){ order(); write(true); });
  chips.forEach(function(c){
    c.addEventListener('click', function(){
      era = c.classList.contains('on') ? '' : c.getAttribute('data-era');
      chips.forEach(function(o){ o.classList.toggle('on', o.getAttribute('data-era')===era); });
      apply();
      write(true);
    });
  });
  if(clear) clear.addEventListener('click', function(){ setQuery(''); q.focus(); });
  document.addEventListener('keydown', function(e){
    if(e.key==='/' && document.activeElement!==q){ e.preventDefault(); q.focus(); }
    if(e.key==='Escape' && document.activeElement===q){ setQuery(''); q.blur(); }
  });
  window.addEventListener('popstate', restore);
  q.disabled=false; sort.disabled=false;
  chips.forEach(function(c){ c.disabled=false; });
  // Whatever the link asked for, before the first paint the reader sees.
  restore();
})();
"""

INDEX_SHELL = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Possum Logic</title>
<meta property="og:type" content="website">{share}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="{fonts}" rel="stylesheet">
<link href="{sheet}" rel="stylesheet">
<style>{css}</style>{theme_js}{ago_js}{new_rows_js}</head><body><div class="wrap">
<nav class="crumb"><a class="here">Shows</a><a href="./songs.html">Songs</a>
<a href="./due.html">Due</a><a href="./method.html">How this is worked out</a></nav>
<div class="rule2"></div>
<header><h1>Possum <em>Logic</em></h1>
<p class="show">{subtitle}</p></header>
{onstage}
<section class="hero">{hero}</section>
<div class="rule2"></div>
<div class="tools">
<div class="tools-main">
<input id="q" class="search" type="search" autocomplete="off" disabled
       placeholder="Search date, venue, city, song, year&hellip;" aria-label="Search reports">
<button id="clear" class="clear" type="button" hidden>Clear</button>
<label class="count" for="sort">Sort
<select id="sort" class="sort" disabled>
<option value="newest">Newest</option><option value="oldest">Oldest</option>
<option value="gap">Longest gap</option></select></label>
<span class="count"><b id="shown">{count}</b> of {count} shows</span>
</div>
<div class="chips">{years}</div>
</div>
<ol class="reports" id="list">
{rows}
</ol>
<p class="empty" id="empty" hidden>No shows match that search.</p>
{aside}
<footer><span><a href="./method.html">How this is worked out</a></span>{theme_ui}
<span>{stamp}</span></footer>
{analytics}
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
        "live": bool(report.get("provisional")),
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


def _date_aliases(iso):
    """The other ways somebody might type a date into the search box.

    The archive only ever spells dates YYYY-MM-DD, so searching 7/24 or
    "july 24" would otherwise come up empty. Cheaper to widen the haystack
    than to teach the query parser about date formats.
    """
    try:
        d = datetime.date.fromisoformat(iso)
    except ValueError:
        return ""
    return " ".join((
        "%02d/%02d/%d" % (d.month, d.day, d.year),
        "%d/%d/%d" % (d.month, d.day, d.year),
        "%d/%d/%02d" % (d.month, d.day, d.year % 100),
        "%02d/%02d" % (d.month, d.day),
        "%d/%d" % (d.month, d.day),
        "%d-%d" % (d.month, d.day),
        # Both day spellings: "jul" still matches "july", and the unpadded one
        # is what lets a whole-number search for 8 find the 8th.
        d.strftime("%B %d %Y"),
        "%s %d" % (d.strftime("%B"), d.day),
        # The weekday is on the song pages anyway, and putting it in the
        # haystack makes "never miss a Sunday show" a search rather than a
        # saying. "sun" is a prefix of "sunday", so one spelling covers both.
        d.strftime("%A"),
    ))


def typographic(text):
    """A straight apostrophe becomes the right single quote.

    The display face has 149 codepoints and U+0027 is not among them, while
    U+2019 is -- so "Mike\u2019s Song" set in Bagnard drops the apostrophe or
    falls back to another face mid-word, visibly, on 35 of 587 song titles.
    U+2019 is the correct mark for an English apostrophe regardless of which
    face is in use, so this is worth doing even if the face changes.
    """
    return (text or "").replace("'", "\u2019")


def neighbours(perfs, counting=None, top=3):
    """What this song most often came out of and went into.

    Every row on a song page already names both, and nothing has ever added
    them up -- which is the question this audience asks most: what does Tweezer
    come out of? Counted over performances that count toward a gap, so a
    soundcheck pairing does not enter a statistic the rest of the site would
    not recognise.

    -> ([(song, n), ...] before, [(song, n), ...] after)
    """
    before, after = collections.Counter(), collections.Counter()
    for p in perfs:
        if counting and p.get("date") not in counting:
            continue
        if p.get("prev"):
            before[p["prev"]] += 1
        if p.get("next"):
            after[p["next"]] += 1
    # A pairing seen once says nothing; it is a coincidence with a name.
    keep = lambda c: [(s, n) for s, n in c.most_common(top) if n > 1]
    return keep(before), keep(after)


def _clock(iso):
    """A bare HH:MM fallback for a stamp that JavaScript will make relative."""
    return html.escape(iso[11:16]) if iso else ""


def _venue_lines(report):
    """The venue and its locality as two elements, with no comma between them.

    One flat string could not be made to wrap well. The masthead puts the date
    in an auto-sized grid column, so the venue's column is whatever is left --
    258px at 1280 and 187px at 1000, never more however wide the window. Long
    venues therefore always wrap, and the comma joining venue to city was
    stranded at the end of a line every time: "MADISON SQUARE GARDEN," above
    "NEW YORK, NY", and at 1000px a second orphan a line further up.

    No CSS can detect a wrap, so the separator has to stop existing. The index
    rows already solved this -- venue and place as two elements, no comma --
    and this is that pattern. Wide: two lines, the locality quieter. Narrow:
    one line joined by a middot, where the whole string fits anyway.
    """
    venue = report.get("venue_name") or ""
    place = ", ".join(p for p in (report.get("city"), report.get("state")) if p)
    if not venue:
        # Reports saved before venue/city/state were stored separately.
        parts = [p.strip() for p in (report.get("venue") or "").split(",")]
        venue, place = (parts[0] if parts else ""), ", ".join(parts[1:])
    return ("<span class='v-name'>%s</span><span class='v-place'>%s</span>"
            % (html.escape(venue), html.escape(place)))


def _full_weekday(iso):
    """Saturday, Sunday... spelt out.

    The index abbreviates because it repeats the word 710 times down a column
    and the abbreviation is unambiguous there. A masthead says it once, so it
    can say it properly.
    """
    try:
        return datetime.date.fromisoformat(iso).strftime("%A")
    except ValueError:
        return ""


def weekday(iso):
    """Sun, Mon, Tue... for a date the archive spells YYYY-MM-DD."""
    try:
        return datetime.date.fromisoformat(iso).strftime("%a")
    except ValueError:
        return ""


def render_index(reports, page_href="./show/%s.html", card=None, aside=()):
    """A single self-contained index page over every saved report."""
    entries = sorted((summarize(r) for r in reports),
                     key=lambda e: e["date"], reverse=True)

    rows = []
    for e in entries:
        # Everything worth searching, flattened into one lowercase haystack.
        hay = " ".join([e["date"], _date_aliases(e["date"]),
                        e["venue"], e["place"], e["tour"]]
                       + e["titles"]).lower()
        # Each figure in its own cell rather than one right-aligned run of
        # text. Right-aligning the whole string only pins its right edge: with
        # 16 songs against 26, and a longest of 45 against 1,468, every other
        # number in the line sat at a different place on every row.
        stats = "<span class='st'><b>%d</b> songs%s</span>" % (
            e["songs"], " <span class='live-tag'>so far</span>" if e["live"] else "")
        if e["longest"] is not None:
            stats += ("<span class='st'>median <b>%s</b></span>"
                      "<span class='st'>longest <b class='hot'>%s</b></span>"
                      "<span class='r-top'>%s</span>"
                      % (_stat(e["median"]), _stat(e["longest"]),
                         html.escape(e["longest_song"])))
        rows.append(
            "<li data-date='%s' data-year='%s' data-era='%s' "
            "data-longest='%d' data-search=\"%s\">"
            "<a class='row' href='%s'>"
            "<span class='r-date'>%s</span>"
            "<span class='r-where'><span class='r-venue'>%s</span>"
            "<span class='r-place'>%s</span></span>"
            "<span class='r-stats'>%s</span></a></li>"
            % (e["date"], e["date"][:4], era(e["date"]), e["longest"] or 0,
               html.escape(hay, quote=True),
               html.escape(page_href % e["date"], quote=True),
               e["date"], html.escape(e["venue"]), html.escape(e["place"]),
               stats))

    # Eras rather than years. A year chip per year was fine at six and is not
    # at eighteen; the full archive would put more than forty buttons above the
    # list, which is a wall rather than a filter. The eras are four, they are
    # the divisions the band's own audience uses, and the site already teaches
    # them on song pages. A year is still reachable -- typing it in the search
    # box filters to it, because the date is in the haystack.
    order = [label for label, _, _ in ERAS]
    present = sorted({era(e["date"]) for e in entries}, key=order.index)
    counts = collections.Counter(era(e["date"]) for e in entries)
    chips = "" if len(present) < 2 else "".join(
        "<button class='chip' type='button' disabled data-era='%s'>"
        "%s <span class='chip-n'>%d</span></button>" % (x, x, counts[x])
        for x in present)

    # A figure in the hero that cannot be followed is an advertisement for a
    # page that does not exist. The show holding the longest gap is a page the
    # site already builds, so the number points at it rather than just sitting
    # there being large.
    peak = max((e for e in entries if e["longest"]),
               key=lambda e: e["longest"], default=None)
    # The fullest single night is a different question from the longest gap,
    # and one the index had no way of asking. Labelled by song count rather
    # than "longest" so it does not read as a second gap figure.
    most = max(entries, key=lambda e: e["songs"], default=None)
    # The songs card doubles as the way to the song index, since a reader who
    # has just noticed how many songs are logged is the reader who wants it.
    hero = "".join(
        ("<a class='card' href='%s'>" % html.escape(href, quote=True)
         if href else "<div class='card'>")
        + "<div class='lbl'>%s</div><div class='num%s'>%s</div>" % (lbl, cls, val)
        + ("</a>" if href else "</div>")
        for val, lbl, cls, href in (
            (len(entries), "Reports", "", ""),
            (_stat(peak["longest"]) if peak else "n/a", "Longest Gap", " hot",
             page_href % peak["date"] if peak else ""),
            # Performances, not songs: this sums every song slot across every
            # report. Labelled "Songs Logged" it read 4,593 and linked to a
            # page saying 379, which is the same word counting two things.
            ("{:,}".format(sum(e["songs"] for e in entries)),
             "Song Performances", "", "./songs.html"),
            (most["songs"] if most else "n/a", "Most Songs", "",
             page_href % most["date"] if most else ""),
            (len({e["venue"] for e in entries if e["venue"]}), "Venues", "", ""),
        ))

    # Not concerts, and kept off the list above rather than out of the site:
    # the pages exist, the gap figures on them do not describe a show, and a
    # soundcheck's whole reason for existing is the concert it precedes.
    aside_html = ""
    if aside:
        items = []
        for a in sorted(aside, key=lambda a: a["report"]["date"], reverse=True):
            r, kind = a["report"], a["kind"]
            link = ""
            if kind == "soundcheck" and a["before"]:
                link = ("<span class='for'>for <a href='%s'>%s</a></span>"
                        % (page_href % a["before"], a["before"]))
            items.append(
                "<li><a class='ax-row' href='%s'><span class='ax-date'>%s</span>"
                "<span class='ax-kind'>%s</span>"
                "<span class='ax-venue'>%s</span></a>%s</li>"
                % (page_href % r["date"], r["date"], kind,
                   html.escape(r.get("venue") or ""), link))
        aside_html = (
            "<section class='aside'><h2>Also on file</h2>"
            "<p>Soundchecks, and television and radio sessions. phish.net lists"
            " these but does not count them toward a gap, so neither do we"
            " &mdash; the figures on their pages describe the entry, not a"
            " show the band played.</p><ol>%s</ol></section>" % "".join(items))

    # A show being played is the reason to be here tonight, and a "so far"
    # tag on one row among 690 is not a way of saying so. The whole block is
    # the link, because the front door failing to reach the live page is the
    # failure this exists to fix.
    onstage = ""
    live_now = [e for e in entries if e.get("live")]
    if live_now:
        e = live_now[0]
        onstage = ("<a class='onstage' href='%s'>"
                   "<span class='k'>On stage now</span>"
                   "<span class='w'>%s<span class='p'>%s</span></span>"
                   "<span class='n'><b>%d</b> song%s so far</span></a>"
                   % (html.escape(page_href % e["date"], quote=True),
                      html.escape(e["venue"]), html.escape(e["place"]),
                      e["songs"], "" if e["songs"] == 1 else "s"))

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
        ago_js=AGO_JS,
        new_rows_js=NEW_ROWS_JS,
        analytics=ANALYTICS,
        css=INDEX_CSS, js=INDEX_JS, theme_js=THEME_JS, theme_ui=THEME_UI,
        fonts=WEB_FONTS, sheet="./fonts.css",
        hero=hero, years=chips,
        count=len(entries), rows="\n".join(rows) or "",
        aside=aside_html, subtitle=subtitle, onstage=onstage,
        share=share_meta("Possum Logic", html.escape(blurb, quote=True),
                         card=card),
        # The newest show it lists, for the same reason.
        stamp="Updated %s" % (entries[0]["date"] if entries else "&mdash;"))


# ------------------------------------------------------------------- song ---

# Alfa Slab One has one weight and it is a poster weight: right for a wordmark
# and for a bare number, too heavy for a date string, which has twice the
# characters and three pieces of punctuation. Aleo carries the dates and the
# song title; the gap figures and the hero numbers stay in the slab.
SONG_FONTS = WEB_FONTS

SONG_CSS = (PALETTE_CSS + THEME_CSS + """
*{box-sizing:border-box}
body{margin:0;padding:clamp(1.4rem,4vw,3.5rem) clamp(1rem,5vw,3rem);
     background:var(--paper);color:var(--ink);
     font-family:'IBM Plex Mono',ui-monospace,SFMono-Regular,monospace;
     font-size:.875rem;line-height:1.55}
.wrap{max-width:960px;margin:0 auto}
.crumb{display:flex;flex-wrap:wrap;align-items:baseline;gap:.3rem .9rem;
   margin-bottom:1.1rem;
   font-size:.625rem;letter-spacing:.14em;text-transform:uppercase}
.crumb a{color:var(--dim);text-decoration:none;
   border-bottom:1px solid var(--rule)}
.crumb a:hover{color:var(--hot);border-bottom-color:var(--hot)}
/* One of the three slots the display face is allowed: the wordmark, a show's
   date, and a song's name. Nowhere else. */
h1{font-family:'Bagnard',Georgia,serif;font-weight:400;
   font-size:clamp(2rem,6.5vw,3.4rem);line-height:1.14;margin:0 0 .5rem;
   letter-spacing:-.01em}
.show{margin:0;font-size:.75rem;font-weight:600;letter-spacing:0;
   text-transform:uppercase;color:var(--ink-soft)}

/* Letterpress: a thick rule with a hairline under it. Three to a page at most
   -- a double rule that turns up six times is wallpaper. */
.rule2{height:5px;margin:0 0 1rem;background:linear-gradient(to bottom,
   var(--ink) 0 3px,transparent 3px 4px,var(--ink) 4px 5px)}
/* The tear line between one set and the next. Never between rows. */
.perf{height:1px;margin:1.5rem 0 .6rem;background:repeating-linear-gradient(
   to right,var(--edge) 0 5px,transparent 5px 10px)}
.hero{display:flex;flex-wrap:wrap;margin:.7rem 0 .3rem;
   border-bottom:1px solid var(--ink)}
.card{flex:1 1 0;padding:.85rem 1.1rem;border-left:1px solid var(--rule);
   display:flex;flex-direction:column}
.card:first-child{border-left:0;padding-left:0}
.num{font-family:'IBM Plex Mono',ui-monospace,monospace;font-weight:600;font-size:2.25rem;line-height:1;
   letter-spacing:0;margin-top:auto}
.num.hot{color:var(--hot)}
.lbl{font-size:.625rem;text-transform:uppercase;letter-spacing:.14em;
   color:var(--dim);margin-bottom:.35rem}
.lbl .abbr{display:none}
/* The best version gets a line rather than a fifth card: it is a date, a
   place, a score and two links, none of which fit a card built for one
   number. */
/* A stub, not a callout. The tinted panel with a coloured left border was the
   one object on the site that looked like a framework component; it reads in
   the same field language as the row above it now -- label, value, no fill. */
.best{display:flex;flex-wrap:wrap;align-items:baseline;gap:.35rem 1.1rem;
   margin:.7rem 0 0;padding:0 0 .7rem;border-bottom:1px solid var(--rule);
   font-size:.875rem}
.best .cap{font-size:.625rem;letter-spacing:.14em;text-transform:uppercase;
   color:var(--dim)}
.best .field{display:flex;flex-direction:column;gap:.3rem}
.best .when{font-family:'IBM Plex Mono',ui-monospace,monospace;font-weight:600;font-size:1rem}
.best .score{font-family:'IBM Plex Mono',ui-monospace,monospace;font-weight:600;color:var(--hot);
   font-size:1.25rem;line-height:1}
.best .where{color:var(--dim)}
.best a{color:var(--ink);text-decoration:none;border-bottom:1px solid var(--rule)}
.best a:hover{color:var(--hot);border-bottom-color:var(--hot)}
.links{margin:1.1rem 0 0;display:flex;flex-wrap:wrap;gap:.4rem}
.badge{display:inline-flex;align-items:center;gap:.35rem;line-height:1;
   padding:.35rem .5rem;border:1px solid var(--edge);color:var(--dim);
   text-decoration:none;font-size:.625rem;letter-spacing:.14em;
   text-transform:uppercase}
.badge img{display:block;width:13px;height:13px}
.badge:hover{color:var(--ink);border-color:var(--ink-soft)}
.tools{display:flex;flex-wrap:wrap;align-items:center;gap:.55rem .8rem;
   margin:1.9rem 0 .9rem}
.search{flex:1 1 15rem;min-width:0;font:inherit;font-size:.875rem;
   padding:.5rem .7rem;border:1px solid var(--edge);border-radius:0;
   background:transparent;color:var(--ink)}
.search::placeholder{color:var(--dim)}
.search:focus-visible,.sort:focus-visible{outline:2px solid var(--hot);
   outline-offset:1px}
.sort{font:inherit;font-size:.75rem;padding:.4rem .3rem;background:transparent;
   color:var(--ink);border:1px solid var(--edge);border-radius:0}
.count{font-size:.625rem;letter-spacing:.14em;text-transform:uppercase;
   color:var(--dim);margin-left:auto}
/* Jump to an era, with how many shows are in it. Anchors, so they work with
   scripting off and survive a reload. */
.eras{display:flex;flex-wrap:wrap;align-items:center;gap:.3rem}
/* Captioned, because "4.0 42" beside a sort control reads as a filter with an
   unexplained number, and nobody outside the fandom knows 4.0 is an era. */
.eras-cap{font-size:.625rem;letter-spacing:.14em;text-transform:uppercase;
   color:var(--dim);margin-right:.15rem}
.era-chip{display:inline-flex;align-items:baseline;gap:.3rem;
   font-size:.625rem;letter-spacing:.14em;text-transform:uppercase;
   padding:.42rem .55rem;border:1px solid var(--edge);color:var(--dim);
   text-decoration:none}
.era-chip b{font-family:'IBM Plex Mono',ui-monospace,monospace;font-weight:600;
   font-size:.875rem;letter-spacing:0;color:var(--ink-soft)}
.era-chip:hover{color:var(--ink);border-color:var(--ink-soft)}
.era-chip:hover b{color:var(--hot)}
/* Shown only once there is something to clear. */
.clear{font:inherit;font-size:.625rem;letter-spacing:.14em;text-transform:uppercase;
   padding:.45rem .6rem;border:1px solid var(--edge);background:transparent;
   color:var(--dim);cursor:pointer}
.clear:hover{color:var(--hot);border-color:var(--hot)}
.clear:focus-visible{outline:2px solid var(--hot);outline-offset:1px}
/* A venue is a filter waiting to happen: click it to see every other night
   the song was played there. */
.r-venue{cursor:pointer}
.r-venue:hover{color:var(--hot)}
.count b{font-family:'IBM Plex Mono',ui-monospace,monospace;font-weight:600;
   font-size:1rem;color:var(--ink)}
.perfs{list-style:none;margin:0;padding:0;border-top:1px solid var(--rule)}
/* Anything a link can land on stops clear of the condensed header, which is
   fixed and 42px tall -- without this the browser puts the target's top edge
   at the top of the viewport, which is exactly where the header is, and the
   row you tapped to look at arrives half hidden underneath it. */
/* Clear of the sticky bar, which is not one height. Below 820px it carries the
   song and its counts and measures 42px; above, it also carries the column
   labels and measures 73px -- against the 57.6px this used to be, which put a
   jumped-to performance 16px underneath the bar meant to orient it. Measured
   at both widths rather than estimated, with room left over so the row has air
   above it rather than being flush to the edge. */
.perfs>li,.perfs>li.yr{scroll-margin-top:3.6rem}
@media screen and (min-width:821px){
  .perfs>li,.perfs>li.yr{scroll-margin-top:5.4rem}
}
.perfs>li{border-bottom:1px solid var(--rule-soft)}
.perfs>li.yr{border-bottom:0}
/* The same tab the set headings take, so a section boundary looks the same
   wherever it falls. */
.yr h2{display:flex;flex-wrap:wrap;align-items:center;gap:.2rem .7rem;
   font-family:'IBM Plex Mono',ui-monospace,monospace;font-weight:600;
   font-size:.625rem;letter-spacing:.14em;text-transform:uppercase;
   margin:1.6rem 0 .3rem;padding:0;border:0;color:var(--ink)}
.yr h2 .tab{background:var(--ink);color:var(--paper);padding:.25rem .55rem;
   letter-spacing:.14em;print-color-adjust:exact;-webkit-print-color-adjust:exact}
.yr h2::after{content:"";flex:1;border-bottom:1px solid var(--ink)}
.yr h2 span{font-family:'IBM Plex Mono',monospace;font-size:.625rem;
   letter-spacing:.14em;text-transform:uppercase;color:var(--dim)}
.yr:first-child h2{margin-top:.4rem}
/* Column labels. The date and the venue say what they are; the bar and the
   number on the far right did not, and were left to be guessed at. */
.head{padding-bottom:.35rem;border-bottom:1px solid var(--rule);
   font-size:.625rem;letter-spacing:.14em;text-transform:uppercase;
   color:var(--dim)}
.head .nhead{color:var(--dim)}
.head .ghead{grid-column:4/-1;text-align:right}
/* Every row is its own grid, so an `auto` last column sizes to its own content
   and the gap figures stop lining up: "set 1" is 36px, "encore" 43, "set 2 -
   2x" 71, which put the numbers at three different left edges down the page.
   Fixed width, sized for the longest of them. */
.row{display:grid;grid-template-columns:8.4rem 1fr 9rem 5rem 6.4rem;
   column-gap:1.1rem;align-items:baseline;padding:.6rem .25rem}
.row:hover{background:var(--hover)}
/* The row's identifier, in the display face, same as the show index. It is
   the one thing in the row that is not the song. */
.r-date{font-family:'IBM Plex Mono',ui-monospace,monospace;font-weight:600;
   font-size:1rem;line-height:1.3rem;white-space:nowrap}
.r-date a{color:inherit;text-decoration:none;
   border-bottom:1px solid var(--rule)}
.r-date a:hover{color:var(--hot);border-bottom-color:var(--hot)}
/* One copy of each favicon for the whole page, worn by class.
   No blanket opacity: these icons do not agree about their own. phish.net's is
   fully opaque, phish.in's averages an alpha of 130 and fouldomain's 137, so a
   single .65 on top of all three dimmed the translucent ones to about a third.
   Black at a third reads fine on cream and disappears on near-black, which is
   why phish.in's went missing in the dark and only in the dark. Each is dimmed
   to taste against what it actually ships, and 12px rather than 10 because
   they are detailed marks being drawn very small. */
.ext::after{content:"";display:inline-block;width:12px;height:12px;
   margin-left:.3rem;vertical-align:-1px;
   background-position:center;background-repeat:no-repeat;
   background-size:contain}
.i-pnet::after{opacity:.6}
.i-pin::after,.i-foul::after{opacity:.95}
.ext:hover::after{opacity:1}
.i-pnet::after{background-image:url("data:image/png;base64,__PNET__")}
.i-pin::after{background-image:url("data:image/png;base64,__PIN__")}
.i-foul::after{background-image:url("data:image/png;base64,__FOUL__")}
.dek{margin:.55rem 0 0;font-size:.75rem;line-height:1.5;color:var(--dim);
   max-width:56ch}
/* The notation legend. The arrows read as decoration unless something says
   they are load-bearing: an arrow means the songs merely followed one another,
   and phish.net's mark in its place means they did not stop. Worth one line,
   because the alternative is a reader inventing a meaning for it. */
.dek.key .k{font-family:'IBM Plex Mono',ui-monospace,monospace;font-weight:600;
   color:var(--ink-soft);padding:0 .1rem}
/* Said where the page explains itself, in the same voice as the gap note above
   it, but marked -- it is a correction to what the numbers appear to mean, not
   more description of them. */
/* What the song sits between, counted over its whole history. Two short rows
   rather than a table: this is context for the list below, not a finding of
   its own, and it earns its place only because the answer is usually
   surprising -- Harry Hood comes out of Hold Your Head Up 31 times. */
.pairs{margin:.7rem 0 0;display:flex;flex-wrap:wrap;gap:.15rem 2rem}
.pair{display:flex;flex-wrap:wrap;align-items:baseline;gap:.15rem .7rem}
.pair .cap{font-size:.625rem;letter-spacing:.14em;text-transform:uppercase;
   color:var(--dim)}
.pair .p{font-size:.8125rem;color:var(--ink-soft);white-space:nowrap}
.pair .p b{font-family:'IBM Plex Mono',ui-monospace,monospace;font-weight:600;
   font-size:.75rem;color:var(--dim);margin-left:.3rem}
.caveat{margin:.6rem 0 0;padding-left:.8rem;border-left:2px solid var(--hot);
   font-family:'Literata',Georgia,serif;font-size:.9375rem;line-height:1.5;
   font-variation-settings:'opsz' 14;color:var(--ink-soft);max-width:58ch}

.dow{display:block;font-family:'IBM Plex Mono',monospace;font-weight:400;
   font-size:.625rem;letter-spacing:.14em;text-transform:uppercase;
   color:var(--dim);line-height:1.1rem}
/* Heavier than the show index's venue, deliberately. There the venue is the
   row's identity repeated 259 times and the weight accumulates into a wall.
   Here every row is the same song, so the venue is the only thing telling one
   performance from the next -- the weight is carrying the distinction rather
   than shouting. The date being in the display face is what keeps the two from
   competing at the same volume. */
.r-venue{font-size:.875rem;font-weight:600;letter-spacing:0;
   text-transform:uppercase;line-height:1.3rem}
.r-place{display:block;color:var(--dim);font-size:.75rem;line-height:1.15rem}
.r-gap{text-align:right;line-height:1.3rem}
/* The column header names this column, so the per-row label would be a second
   answer to a question already answered -- but the header is the first thing
   the narrow layout drops, and there the number was left to be guessed at.
   Shown exactly where the header is not. */
.glabel{display:none;font-size:.625rem;letter-spacing:.14em;text-transform:uppercase;
   color:var(--dim);margin-right:.4rem}
.gap{font-family:'IBM Plex Mono',ui-monospace,monospace;font-weight:600;font-size:1rem}
/* The one card whose number arrives after the page does. Same shape as its
   four neighbours so its appearance is a card filling in, not the row
   reflowing around a new one. */
.card.since.over .num{color:var(--hot)}
/* The verdict rides in the label, which the hero can now afford to let wrap:
   the figures hang off a shared bottom edge, so a second line here moves this
   label and nothing else on the row. */
.card.since .v{display:block;text-transform:none;letter-spacing:0}
.card.since .v:not(:empty){margin-top:.1rem}
.card.since .v.quiet,.card.since .v.dim{color:var(--dim)}
.card.since.over .v{color:var(--hot-text);text-transform:uppercase;
   letter-spacing:.14em}
.card.since.dormant .num{color:var(--ink-soft)}
.gap.big{color:var(--hot)}
.gap.none{color:var(--dim)}
/* A soundcheck or a television session. It happened and it is listed,
   but phish.net does not count it toward a gap and neither do we, so
   the column says why it is empty rather than leaving a dash to be read
   as missing data. */
.gap.none{font-size:.75rem;letter-spacing:.14em;text-transform:uppercase}
.set{display:block;font-size:.625rem;letter-spacing:.14em;color:var(--dim);
   text-transform:uppercase}
/* What it followed and what it led into, stacked. Sized in ch so the column
   holds a couple of words of song title and truncates the rest rather than
   pushing the gap figures around. */
.nb{font-size:.75rem;line-height:1.25rem;color:var(--dim);min-width:0}
/* Named only where the column header is not doing it. */
.nb .cap{display:none}
/* Direct children only. These are the two lines -- what came before, what
   came after -- and each is its own line. The transition mark now lives in
   a span inside one of them, and a blanket rule here made that mark a
   block too, so a row read "->" and "Golden Age" on separate lines. */
.nb>span{display:block;overflow:hidden;text-overflow:ellipsis;
   white-space:nowrap}
/* Doubled backslashes: this is a Python string, and "\2190" is read as the
   octal escape \21 followed by "90", which reaches the browser as a control
   character and renders as a box. */
.nb-in::before{content:"\\2190\\00a0";opacity:.55}
.nb-out::before{content:"\\2192\\00a0";opacity:.55}
/* Where a transition mark is shown it points on its own; the plain arrow is
   only for rows that have none, so no line ever reads "-> ->". */
.nb .seg::before{content:none}
/* Same -.06em as the report pages: enough to make -> one mark, not so
   much that it stops matching the > on the row above it. */
.nb .mk.tight{letter-spacing:-.06em}
.bar{align-self:center}
/* The same band the report pages use. This CSS is the half of that change I
   left out the first time: the markup emitted .band, .mid and .at while this
   sheet still described the old fill, so a song page drew an empty track with
   three unstyled spans inside it and looked like nothing at all. */
.bar .track{display:block;position:relative;width:100%;height:14px}
.bar .track::before{content:"";position:absolute;left:0;right:0;top:6px;
   height:2px;background:var(--rule)}
.bar .track.bare::before{opacity:.55}
.bar .band{position:absolute;left:30%;right:30%;top:3px;bottom:3px;
   background:var(--band);opacity:.85;border-radius:1px}
.bar .mid{position:absolute;left:50%;top:1px;bottom:1px;width:2px;
   background:var(--paper);opacity:.85}
.bar .at{position:absolute;left:50%;top:0;bottom:0;width:5px;
   transform:translateX(-50%);background:var(--ink);border-radius:1px;
   box-shadow:0 0 0 2px var(--paper)}
.bar .at.late{background:var(--hot)}
.bar .at.early{background:var(--cool)}
.bar .at.usual{background:var(--ink)}
/* Only the rated versions carry these, which is 25 rows out of however many
   hundred -- and only they are known to have audio, since a version cannot be
   scored until a recording of it circulates. */
.mark{display:block;margin-top:.3rem;font-size:.625rem;letter-spacing:.14em;
   text-transform:uppercase;color:var(--dim)}
.mark b{font-family:'IBM Plex Mono',ui-monospace,monospace;font-weight:600;
   font-size:.875rem;color:var(--dim);letter-spacing:0}
.mark.high b{color:var(--hot-text)}
.mark a{color:var(--ink-soft);text-decoration:none;
   border-bottom:1px solid var(--rule)}
.mark a:hover{color:var(--hot);border-bottom-color:var(--hot)}
/* phish.net's note on the version, set under the venue rather than across the
   row: spanning every column put it against the page's left edge, where it
   read as something stuck on afterwards rather than as part of the entry.
   Roman, not italic -- these run to 950 characters at the long end, and a
   paragraph of italic prose is tiring well before that. */
/* The only real prose on the site, and the one job neither other face can do.
   The mono set it evenly and never argued with the figures, but 950 characters
   of monospace gives the eye nothing to return on, and the display face at
   text size is a display face at text size. Literata is drawn for reading and
   has the optical axis to be drawn differently here than at a headline, which
   is the whole argument for a third family rather than stretching a second.
   15px rather than 12: a proportional face sets far more into the same measure,
   and the old size was compensating for the mono's width. */
.jam,.note{margin:.45rem 0 0;font-family:'Literata',Georgia,serif;
   font-size:.9375rem;line-height:1.5;font-variation-settings:'opsz' 14;
   color:var(--ink-soft);max-width:62ch}
.jam a,.note a{color:inherit;text-decoration:none;
   border-bottom:1px solid var(--edge);word-break:break-word}
.jam a:hover,.note a:hover{color:var(--hot-text);border-bottom-color:var(--hot-text)}
.tag{display:inline-block;margin-right:.45rem;font-size:.625rem;
   letter-spacing:.14em;text-transform:uppercase;color:var(--dim)}
details.jam,details.note{cursor:pointer}
details.jam summary,details.note summary{display:block;list-style:none}
details.jam summary::-webkit-details-marker,
details.note summary::-webkit-details-marker{display:none}
.clip{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;
   overflow:hidden}
details[open] .clip{-webkit-line-clamp:none;display:block}
/* The affordance sits outside the clamped box, or it would be clipped away by
   the very rule that makes it necessary. */
details.jam summary::after,
details.note summary::after{content:"More";display:inline-block;margin-top:.2rem;
   font-size:.625rem;letter-spacing:.14em;text-transform:uppercase;
   color:var(--dim);border-bottom:1px solid var(--rule)}
details.jam[open] summary::after,
details.note[open] summary::after{content:"Less"}
details.jam summary:hover::after,
details.note summary:hover::after{color:var(--hot);border-bottom-color:var(--hot)}
details.jam summary:focus-visible,
details.note summary:focus-visible{outline:2px solid var(--hot);outline-offset:2px}
.empty{margin:2rem 0;font-size:.875rem;color:var(--dim);font-style:italic}
/* The header a reader keeps once the real one has scrolled away. Landing on a
   row from a report's link otherwise drops you into an unlabelled list of
   dates with no way to tell what page you are on. It carries the song and the
   figure the page exists for, and nothing else. */
.stuck{position:fixed;top:0;left:0;right:0;z-index:20;
  background:var(--paper);border-bottom:1px solid var(--rule);
  transform:translateY(-101%);transition:transform .22s ease;
  padding:.5rem clamp(1rem,5vw,3rem)}
.stuck.on{transform:none}
.stuck .in{max-width:960px;margin:0 auto;display:flex;align-items:baseline;
  gap:.7rem}
.stuck .name{font-family:'IBM Plex Mono',ui-monospace,monospace;font-weight:600;font-size:1rem;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.stuck .n{font-size:.625rem;letter-spacing:.14em;text-transform:uppercase;
  color:var(--dim);margin-left:auto;white-space:nowrap}
.stuck .n b{font-family:'IBM Plex Mono',ui-monospace,monospace;font-weight:600;
  font-size:.875rem;color:var(--ink);letter-spacing:0}
/* The column labels come along. A reader arriving from a report page lands
   mid-list, having never seen the header row, and the last column is a bare
   number: knowing it is a gap requires knowing the site already. Same markup
   and same grid as the real header, so the labels sit over their columns
   rather than near them. Dropped below 820px, where the row stops being
   columns at all and each field carries its own label instead. */
.stuck .cols{display:block;margin-top:.4rem}
.stuck .cols .head{border-bottom:0;padding-bottom:0}
@media screen and (max-width:820px){.stuck .cols{display:none}}
@media (prefers-reduced-motion:reduce){.stuck{transition:none}}
/* Where a link dropped you. Bright for a moment, then gone -- it answers
   "which row?" and then stops being ink on the page. */
@keyframes landed{from{background:var(--hover);box-shadow:inset 3px 0 0 var(--hot)}
  to{background:transparent;box-shadow:inset 3px 0 0 transparent}}
.perfs>li.landed{animation:landed 3.4s ease-out both}
@media (prefers-reduced-motion:reduce){
  .perfs>li.landed{animation:none;box-shadow:inset 3px 0 0 var(--hot)}}
.totop{position:fixed;right:clamp(.8rem,3vw,2rem);bottom:clamp(.8rem,3vw,2rem);
  z-index:19;width:2.6rem;height:2.6rem;display:flex;align-items:center;
  justify-content:center;background:var(--paper);border:1px solid var(--edge);
  color:var(--ink-soft);text-decoration:none;font-size:1rem}
.totop:hover{color:var(--hot);border-color:var(--hot)}
footer{margin-top:2.4rem;padding-top:.9rem;border-top:1px solid var(--rule);
   font-size:.75rem;letter-spacing:.14em;text-transform:uppercase;
   color:var(--dim);display:flex;justify-content:space-between;
   flex-wrap:wrap;align-items:center;gap:.4rem .9rem}
footer a{color:var(--dim)}
@media screen{
}
/* Same lesson as the reports and the index: below this width the columns stop
   being columns, so nothing has to be squeezed or hidden. Higher than the 620
   the other pages use, because this row carries five columns to their three --
   at 760px the fixed four left the venue about 14rem and "Bethel Woods Center
   for the Arts" came out over four lines. */
@media screen and (max-width:820px){
  .head{display:none}
  .row{grid-template-columns:1fr;column-gap:0;row-gap:.15rem;padding:.55rem 0}
  .nb{margin-top:.35rem}
  .nb>span{white-space:normal;overflow:visible}
  .nb .cap{display:block;font-size:.625rem;letter-spacing:.14em;
     text-transform:uppercase;color:var(--dim);margin-bottom:.1rem}
  .r-date{display:flex;align-items:baseline;gap:.5rem}
  .dow{display:inline}
  .r-gap{text-align:left}
  .glabel{display:inline}
  .gap{font-size:1rem}
  .set{display:inline;margin-left:.5rem}
  .set::before{content:"\\00b7";margin-right:.5rem;color:var(--dim);opacity:.7}
  .bar{margin:.25rem 0}
  .card{flex:1 1 45%;padding:.65rem .55rem}
  .card:nth-child(odd){border-left:0;padding-left:0}
  .card:nth-child(n+3){border-top:1px solid var(--rule)}
  .num{font-size:1.5rem}
  .lbl{font-size:.625rem;letter-spacing:.14em}
  /* "Median gap, last 10 years" is the clear label and the default one; the
     column is simply not wide enough for it here. */
  .lbl .full{display:none}
  .lbl .abbr{display:inline}
  .show{font-size:.75rem;letter-spacing:0}
  .count{margin-left:0}
  .theme{order:1;flex-basis:100%}
}
""".replace("__PNET__", ICON_PNET)
   .replace("__PIN__", ICON_PIN)
   .replace("__FOUL__", ICON_FOUL))

SONG_JS = """
/* How long this song has been waiting, read from one small file rather than
   rendered into the page. It is the only figure here that moves when some
   *other* song is played, so baking it in would rewrite every song page after
   every show -- 48 MB pushed to publish one number that fits in 7 KB. The card
   ships hidden and stays hidden if the fetch fails, so nothing on the page is
   ever a placeholder waiting for a network that is not coming. */
(function(){
  var box=document.querySelector('.card.since');
  if(!box||!window.fetch) return;
  var slug=box.getAttribute('data-slug');
  fetch('../data/current.json').then(function(r){
    if(!r.ok) throw 0;
    return r.json();
  }).then(function(d){
    var n=d.since&&d.since[slug];
    if(typeof n!=='number') return;
    box.querySelector('.num').textContent=n.toLocaleString();
    /* The same two thresholds the report pages apply, in the same order: the
       85th percentile of recent gaps where the song has enough history to have
       one, and the bustout line where it does not. Ours against ours -- this
       is not a claim about phish.net's gap, which is not reproducible from a
       show calendar. */
    var high=parseFloat(box.getAttribute('data-high')),
        bust=parseFloat(box.getAttribute('data-bustout')),
        v=box.querySelector('.v');
    if(high>0){
      if(n>high){ box.classList.add('over'); if(v) v.textContent='overdue'; }
      else if(v){ v.textContent='line '+Math.round(high); v.className='v quiet'; }
    }else if(n>=bust){
      box.classList.add('dormant');
      if(v){ v.textContent='dormant'; v.className='v dim'; }
    }
    box.title='Counted through '+d.as_of+', over '+d.shows.toLocaleString()+
            ' shows that count toward a gap';
    box.hidden=false;
  }).catch(function(){});
})();
(function(){
  var list=document.getElementById('list');
  if(!list) return;
  var kids=Array.prototype.slice.call(list.children),
      rows=kids.filter(function(n){ return !n.classList.contains('yr'); }),
      heads=kids.filter(function(n){ return n.classList.contains('yr'); }),
      q=document.getElementById('q'), sort=document.getElementById('sort'),
      shown=document.getElementById('shown'), empty=document.getElementById('empty');
  function matcher(t){
    if(!/^\\d+$/.test(t)) return function(hay){ return hay.indexOf(t)>-1; };
    var re=new RegExp('(^|[^0-9])'+t+'([^0-9]|$)');
    return function(hay){ return re.test(hay); };
  }
  function apply(){
    var terms=q.value.toLowerCase().split(/\\s+/).filter(Boolean).map(matcher),
        n=0, live={};
    rows.forEach(function(r){
      var hay=r.getAttribute('data-search'), ok=terms.every(function(t){
        return t(hay);
      });
      r.hidden=!ok;
      // A soundcheck row is shown but is not a show, so it is not counted.
      if(ok){ if(r.getAttribute('data-counted')!=='0') n++;
              live[r.getAttribute('data-era')]=1; }
    });
    // A year heading with nothing left under it is worse than no heading, so
    // it goes when its rows do -- and stays gone whenever the order is not
    // chronological, because then it is not describing what follows it.
    var byDate=sort.value==='newest'||sort.value==='oldest';
    heads.forEach(function(h){
      h.hidden=!byDate||!live[h.getAttribute('data-era')];
    });
    shown.textContent=n;
    empty.hidden=n>0;
    // The way out of a filter appears only once there is one to leave.
    if(clear) clear.hidden=!q.value;
  }
  var headFor={};
  heads.forEach(function(h){ headFor[h.getAttribute('data-era')]=h; });
  function order(){
    var k=sort.value;
    var sorted=rows.slice().sort(function(a,b){
      if(k==='rating') return (b.getAttribute('data-score')||-1)-(a.getAttribute('data-score')||-1);
      if(k==='gap') return (b.getAttribute('data-gap')||-1)-(a.getAttribute('data-gap')||-1);
      var x=a.getAttribute('data-date'), y=b.getAttribute('data-date');
      return k==='oldest' ? x.localeCompare(y) : y.localeCompare(x);
    });
    sorted.forEach(function(r){ list.appendChild(r); });
    if(k==='newest'||k==='oldest'){
      // Walk the list as it now runs and put each heading before the first row
      // of its era. Reading the era order off the original array instead put
      // every heading at the foot of its group when sorted oldest, because the
      // array is newest-first and never gets re-sorted itself.
      var placed={};
      sorted.forEach(function(r){
        var e=r.getAttribute('data-era');
        if(placed[e]) return;
        placed[e]=1;
        if(headFor[e]) list.insertBefore(headFor[e], r);
      });
    } else {
      // Hidden either way, but parked at the end rather than left stranded
      // between rows they no longer describe.
      heads.forEach(function(h){ list.appendChild(h); });
    }
    apply();
  }
  var clear=document.getElementById('clear');
  function setQuery(v){ q.value=v; apply(); }
  q.addEventListener('input', apply);
  sort.addEventListener('change', order);
  // Clicking a venue asks the question you were about to type.
  list.addEventListener('click', function(e){
    var v=e.target.closest && e.target.closest('.r-venue');
    if(!v) return;
    setQuery(v.textContent.trim());
    q.scrollIntoView({block:'nearest'});
  });
  if(clear) clear.addEventListener('click', function(){ setQuery(''); q.focus(); });
  document.addEventListener('keydown', function(e){
    if(e.key==='/' && document.activeElement!==q){ e.preventDefault(); q.focus(); }
    if(e.key==='Escape' && q.value){ setQuery(''); q.blur(); }
  });
  q.disabled=false; sort.disabled=false;
  apply();

  // The condensed header appears once the real one is off screen, and the
  // real one is the thing to watch rather than a scroll offset -- no
  // magic number, and it stays right when the header wraps to more lines.
  var stuck=document.getElementById('stuck'), head=document.querySelector('header'),
      totop=document.getElementById('totop');
  function perch(on){
    if(stuck) stuck.classList.toggle('on', on);
    if(totop) totop.hidden=!on;
  }
  if(head && 'IntersectionObserver' in window){
    new IntersectionObserver(function(e){ perch(!e[0].isIntersecting); },
      {rootMargin:'-8px 0px 0px 0px'}).observe(head);
  }

  // A link from a report lands on one row; say which, then stop saying it.
  function land(){
    var id=location.hash.slice(1);
    if(!id) return;
    var li=document.getElementById(id);
    if(!li || li.classList.contains('yr')) return;
    li.classList.remove('landed');
    void li.offsetWidth;            // restart the animation on a repeat visit
    li.classList.add('landed');
  }
  window.addEventListener('hashchange', land);
  land();
})();
"""

SONG_SHELL = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{song} &mdash; Possum Logic</title>
<meta property="og:type" content="article">{share}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="{fonts}" rel="stylesheet">
<link href="{sheet}" rel="stylesheet">
<style>{css}</style>{theme_js}{ago_js}{new_rows_js}</head><body id="top"><div class="wrap">
<nav class="crumb sections"><span class="mark">Possum Logic</span><a href="../index.html">Shows</a><a href="../songs.html">Songs</a><a href="../due.html">Due</a><a href="../method.html">How this is worked out</a></nav>
<div class="stuck" id="stuck" aria-hidden="true"><div class="in">
<span class="name">{song}</span>
<span class="n">{stuckstat}</span></div>
<div class="in cols">{cols}</div></div>
<div class="rule2"></div>
<header><h1>{song}</h1>
<p class="show">{subtitle}</p>
<p class="dek">Gap &mdash; the number of shows the band played between one
performance of this song and the one before it.</p>{pairs}
<p class="dek key"><span class="k">&#8592;&#8201;&#8594;</span> the songs either
side, played as separate songs. <span class="k">&gt;</span> and
<span class="k">&#8211;&gt;</span> are phish.net&rsquo;s own marks, and mean the
band ran them together rather than stopping between them.</p>{caveat}</header>
<section class="hero">{hero}</section>
<div class="rule2"></div>
{best}
<p class="links">{links}</p>
<div class="tools">
<input id="q" class="search" type="search" autocomplete="off" disabled
       placeholder="Search venue, city, year, Sunday&hellip;" aria-label="Search performances">
<button id="clear" class="clear" type="button" hidden>Clear</button>
<span class="eras"><span class="eras-cap">Eras</span>{eras}</span>
<label class="count" for="sort">Sort
<select id="sort" class="sort" disabled>
<option value="newest">Newest</option><option value="oldest">Oldest</option>
<option value="rating">Highest rated</option><option value="gap">Longest gap</option>
</select></label>
<span class="count"><b id="shown">{count}</b> of {count} shows</span>
</div>
{head}
<ol class="perfs" id="list">
{rows}
</ol>
<p class="empty" id="empty" hidden>No performances match that search.</p>
<a class="totop" id="totop" href="#top" hidden aria-label="Back to the top">&uarr;</a>
<footer><span><a href="../method.html">How this is worked out</a></span>{theme_ui}
<span>{stamp}</span></footer>
{analytics}
</div><script>{js}</script></body></html>
"""

SONG_LINKS = (
    ("phish.net", "https://phish.net/song/%s", ICON_PNET, False),
    ("phish.in", "https://phish.in/songs/%s", ICON_PIN, True),
)


def _ext(url, label, cls):
    """An outbound link, wearing the favicon of wherever it lands.

    The icon arrives by class rather than as an inlined <img>. It is the same
    2.5 KB of base64 either way, but on a page with a link on every one of You
    Enjoy Myself's 628 rows the difference is 2.6 MB against 240 KB.
    """
    return ("<a class='ext %s' href='%s' target='_blank'"
            " rel='noopener noreferrer'>%s</a>"
            % (cls, html.escape(url, quote=True), label))


# phish.net's prose occasionally carries a bare URL -- one in the archive so
# far, pointing at a YouTube clip of the version being described. It was being
# escaped and printed as text, which is the one place a reader would obviously
# want to click.
URL_IN_PROSE = re.compile(r"https?://[^\s<]+")


def linkify(escaped):
    """Turn bare URLs in already-escaped prose into links.

    Runs on escaped text, so an ampersand in a query string is already
    &amp; -- which is what an href wants anyway. Trailing punctuation belongs
    to the sentence rather than the address: the one live example ends
    ").", and a closing bracket only counts if the URL opened one.
    """
    def wrap(m):
        url = m.group(0)
        tail = ""
        while url and url[-1] in ".,;:!?":
            url, tail = url[:-1], url[-1] + tail
        while url.endswith(")") and url.count("(") < url.count(")"):
            url, tail = url[:-1], ")" + tail
        if not url:
            return m.group(0)
        return ("<a href='%s' target='_blank' rel='noopener noreferrer'>%s</a>%s"
                % (url, url, tail))
    return URL_IN_PROSE.sub(wrap, escaped)


def render_song(doc, archived=(), stamp=None, card=None, counting=None):
    """One song's whole performance history, newest first.

    The archive stores phish.net verbatim, so the corrections happen here.
    `counting` is the set of dates that count toward a gap; performances at the
    others are soundchecks and television sessions, and they are shown -- they
    happened -- but they are not the song's debut, they carry no gap, and they
    are kept out of every figure. Left in, Gone's debut was the Festival 8
    soundcheck, which made its real first performance render a gap of 1,468.
    """
    perfs = list(reversed(doc["performances"]))
    song = doc["song"]
    best = doc.get("best") or []
    rated = {v["date"]: v for v in best}
    # Newest first, so the last countable row is the earliest one.
    countable = [p for p in perfs
                 if not counting or p["date"] in counting]
    debut_date = countable[-1]["date"] if countable else None
    gaps = [p["gap"] for p in countable
            if p["gap"] is not None and p["date"] != debut_date]
    biggest = max(gaps) if gaps else 0

    # The all-time and recent medians sit side by side because they disagree so
    # often: You Enjoy Myself is 1 against 6, Llama 2 against 11. Showing only
    # the all-time figure would describe a band that stopped existing in 1999.
    cutoff = _years_before(perfs[0]["date"], RECENT_YEARS) if perfs else ""
    recent = [p["gap"] for p in countable
              if p["gap"] is not None and p["date"] >= cutoff
              and p["date"] != debut_date]
    lbl10 = ("Median Gap, <span class='full'>Last %d Years</span>"
             "<span class='abbr'>%d Yr</span>" % (RECENT_YEARS, RECENT_YEARS))
    hero = "".join(
        "<div class='card'><div class='lbl'>%s</div>"
        "<div class='num%s'>%s</div></div>" % (lbl, cls, val)
        for val, lbl, cls in (
            (len(countable), "Times Played", ""),
            (_stat(_median(recent)) if recent else "n/a", lbl10, ""),
            (_stat(_median(gaps)) if gaps else "n/a", "Median Gap, All-Time", ""),
            (_stat(biggest) if gaps else "n/a", "Longest Gap", " hot"),
        ))
    # Filled in the browser from data/current.json; see SONG_JS. It carries the
    # thresholds rather than the verdict, because the count it has to be judged
    # against is the thing that is not known until the page is open. They are
    # the same two the report pages use -- the 85th percentile of recent gaps
    # where there is enough history for one, the bustout line where there is
    # not -- so a song called overdue here is overdue by the site's one rule.
    hero += ("<div class='card since' hidden data-slug='%s' data-high='%s' "
             "data-bustout='%d'>"
             "<div class='lbl'>Current Gap<span class='v'></span></div>"
             "<div class='num'></div></div>"
             % (html.escape(doc.get("slug") or ""),
                _quantile(recent, BAND[1]) if len(recent) >= MIN_HISTORY else "",
                BUSTOUT_GAP))

    top = best[0] if best else ""
    if top:
        where = ", ".join(x for x in (top["venue"], top["city"]) if x)
        # The date is a link to its own row. Without it the only way to read
        # that version's notes was to remember the date, tap an era chip and
        # scroll for it.
        top = ("<p class='best'>"
               "<span class='field'><span class='cap'>Best version</span>"
               "<a class='when' href='#%s'>%s</a></span>"
               "<span class='field'><span class='cap'>Venue</span>"
               "<span class='where'>%s</span></span>"
               "<span class='field'><span class='cap'>Score</span>"
               "<span class='score'>%s</span></span>"
               "<span class='field'><span class='cap'>Hear it</span>"
               "<span class='cap'>%s &middot; %s</span></span></p>"
               % (top["date"], top["date"], html.escape(where), top["score"],
                  _ext("https://phish.in/%s" % top["date"], "Listen", "i-pin"),
                  _ext(top["link"] or "https://fouldomain.com/", "Details", "i-foul")))

    # Each era heading counts its own shows, which is the thing a year heading
    # never told you: McGrupp reads 101 / 1 / 13 / 9 and you can watch the song
    # nearly die and come back.
    # Counted over what counts, so an era chip agrees with the rows under it
    # and with Times Played above it.
    tally = collections.Counter(era(p["date"]) for p in countable)
    span = {}
    for p in perfs:
        e = era(p["date"])
        lo, hi = span.get(e, (p["date"], p["date"]))
        span[e] = (min(lo, p["date"]), max(hi, p["date"]))

    # One band for the whole page: this is a single song, so "usually" is a
    # single answer rather than a per-row one.
    low = _quantile(recent, BAND[0]) if len(recent) >= MIN_HISTORY else None
    high = _quantile(recent, BAND[1]) if len(recent) >= MIN_HISTORY else None
    rows, seen_era = [], None
    for i, p in enumerate(perfs):
        date, g = p["date"], p["gap"]
        # The oldest row is the debut, and what phish.net files as its gap is
        # shows since the band's own first show -- Blaze On's 1,682 counts the
        # thirty years before it existed. A different measurement wearing the
        # same name: it does not belong in the column, in the song's longest
        # gap, or on a bar scaled to gaps that mean the other thing.
        # The earliest performance that counts, not the earliest row: a
        # soundcheck standing in front of it made the real debut look ordinary
        # and gave it phish.net's since-the-beginning figure as a gap.
        counted = not counting or date in counting
        debut = date == debut_date
        if not counted:
            g = None
        this = era(date)
        if this != seen_era:
            seen_era = this
            lo, hi = span[this]
            rows.append(
                # The dot goes out of the id: "era-4.0" is a perfectly good
                # fragment but not a valid selector, where the dot reads as a
                # class -- querySelector throws on it and :target could never
                # match without escaping.
                "<li class='yr' id='era-%s' data-era='%s'>"
                "<h2><span class='tab'>%s</span>"
                "<span>%d show%s</span><span>%s&ndash;%s</span></h2></li>"
                % (this.replace(".", "-"), this, this, tally[this],
                   "" if tally[this] == 1 else "s", lo[:4], hi[:4]))
        note = p.get("note") or ""
        hay = " ".join([date, _date_aliases(date), p["venue"], p["city"],
                        p["state"], p.get("jam") or "",
                        p.get("note") or ""]).lower()
        # A performance we have a report for links to it; everything else goes
        # to phish.net, wearing their favicon so the trip off-site is visible
        # before it is taken rather than after.
        if date in archived:
            link = "<a href='../show/%s.html'>%s</a>" % (date, date)
        else:
            link = _ext("https://phish.net/setlist/?d=%s" % date, date, "i-pnet")
        place = ", ".join(x for x in (p["city"], p["state"]) if x)
        big = (g or 0) >= 50 and not debut
        # The same band the report pages use, and for the same reason: scaled
        # to the song's own longest gap, one bustout flattened every other row
        # on the page -- Back in the U.S.S.R. drew 485 and 689 at full width
        # and its 23 at three percent of one. The band is the same for every
        # row here, since every row is this song, so the marks line up down the
        # page and the shape of them is the song's history.
        bar = "<span class='bar'><span class='track bare'></span></span>"
        pos = _band_pos(g, low, high) if (g is not None and not debut) else None
        if pos is not None:
            # Coloured by where it landed rather than by the size of the
            # number, so it cannot disagree with its own position.
            where = "early" if pos < 30 else "late" if pos > 70 else "usual"
            bar = ("<span class='bar'><span class='track'>"
                   "<span class='band'></span><span class='mid'></span>"
                   "<span class='at %s' style='left:%.2f%%'></span>"
                   "</span></span>" % (where, pos))
        mark = ""
        if date in rated:
            v = rated[date]
            mark = ("<span class='mark%s'>%s <b>%s</b> &middot; %s</span>"
                    % (" high" if v["score"] >= RATED_HIGH else "",
                       "Highly rated" if v["score"] >= RATED_HIGH else "Rated",
                       v["score"],
                       _ext("https://phish.in/%s" % date, "Listen", "i-pin")))
        # What it came out of and went into, reading the way a setlist reads:
        # the mark sits between the two songs it joins. Absent for a set opener
        # or closer, which genuinely has nothing on that side.
        # Always emitted, even empty: every row places the same number of grid
        # children, or a set opener with nothing before it shifts its own bar
        # and gap one column left of everybody else's.
        # One symbol per line. Where phish.net recorded a transition it stands
        # in setlist position and does the pointing itself -- "Everything's
        # Right ->" above, "-> Golden Age" below; a plain arrow only where
        # there was no mark to show. Both at once read as "-> ->".
        def _mk(mark):
            """The transition mark, wrapped so it can be set on its own."""
            return ("<span class='mk%s'>%s</span>"
                    % (" tight" if mark == "->" else "", html.escape(mark)))

        bits = []
        if p.get("prev"):
            bits.append("<span class='nb-in%s'>%s%s</span>"
                        % (" seg" if p.get("in") else "",
                           html.escape(p["prev"]),
                           " %s" % _mk(p["in"]) if p.get("in") else ""))
        if p.get("next"):
            bits.append("<span class='nb-out%s'>%s%s</span>"
                        % (" seg" if p.get("out") else "",
                           "%s " % _mk(p["out"]) if p.get("out") else "",
                           html.escape(p["next"])))
        nb = ("<span class='nb'>%s%s</span>"
              % ("<span class='cap'>Before / after</span>" if bits else "",
                 "".join(bits)))
        times = ("<span class='set'>%s &middot; %d&times;</span>"
                 % (SET_LABEL.get(p["set"], "Set %s" % p["set"]), p["times"])
                 if p.get("times") else
                 "<span class='set'>%s</span>"
                 % SET_LABEL.get(p["set"], "Set %s" % p["set"]))
        # Folded only when long enough to be worth folding. <details> does the
        # work, so a note is still fully readable with scripting off -- and the
        # text is stored once, clamped by CSS rather than truncated in the
        # markup, so searching still reaches the hidden half.
        # phish.net's footnote first -- it is terse and about the performance --
        # then the jamchart prose, which is longer and about the playing. Each
        # labelled, because unlabelled they read as one run-on paragraph.
        jam = ""
        for cls, tag, text in (("note", "Note", p.get("note")),
                               ("jam", "Jam chart", p.get("jam"))):
            if not text:
                continue
            body = ("<span class='tag'>%s</span>%s"
                    % (tag, linkify(html.escape(html.unescape(text)))))
            jam += ("<details class='%s'><summary><span class='clip'>%s</span>"
                    "</summary></details>" % (cls, body)
                    if len(text) > JAM_CLAMP
                    else "<p class='%s'>%s</p>" % (cls, body))
        rows.append(
            "<li id='%s' data-date='%s' data-era='%s' data-gap='%s'"
            " data-score='%s'%s data-search=\"%s\"><div class='row'>"
            "<span class='r-date'>%s<span class='dow'>%s</span></span>"
            "<span><span class='r-venue'>%s</span>"
            "<span class='r-place'>%s</span>%s%s</span>%s%s"
            "<span class='r-gap'><span class='glabel'>Gap</span>"
            "<span class='gap%s'>%s</span>%s</span>"
            "</div></li>"
            % (date, date, this, -1 if (g is None or debut) else g,
               rated[date]["score"] if date in rated else "",
               "" if counted else " data-counted='0'",
               html.escape(hay, quote=True), link, weekday(date),
               html.escape(p["venue"]), html.escape(place), mark, jam, nb, bar,
               " none" if (g is None or debut) else (" big" if big else ""),
               "Debut" if debut else
               ("Not a show" if not counted else
                "{:,}".format(g) if g is not None else "&mdash;"), times))

    # Every bar on this page is the same song against the same scale, so the
    # median sits at one position for all of them -- drawn as a gridline in the
    # track rather than as a tick repeated on six hundred rows, which is the
    # year-heading mistake in another costume. The report pages mark it per row
    # because there each row is a different song with a different norm.
    med = _median(gaps) if gaps else None
    medmark = ""
    if med and biggest and _bar_pct(med, biggest) >= 2:
        medmark = ("<style>.perfs{--med:%.2f%%}</style>"
                   % _bar_pct(med, biggest))

    # One chip per era the song actually has, in page order. Anchors rather
    # than filters: "jump to 1.0" should land you there with the rest still
    # beneath you, which is what makes the spine worth having.
    seen_order, chips = [], ""
    for p in perfs:
        e = era(p["date"])
        if e not in seen_order:
            seen_order.append(e)
    chips = "".join(
        "<a class='era-chip' href='#era-%s'>%s<b>%d</b></a>"
        % (e.replace(".", "-"), e, tally[e])
        for e in seen_order)

    # The labels alone, so the sticky bar can carry a second copy without
    # dragging the median's <style> block into a div with it.
    cols = ("<div class='row head'><span>Date</span><span>Venue</span>"
            "<span class='nhead'>Before / after</span>"
            "<span class='ghead'>Gap%s</span></div>"
            % (" &middot; mark at median %s" % _stat(med) if medmark else ""))
    head = medmark + cols

    # Over the performances that count, so the debut named here is the one the
    # rows call the debut and the total matches Times Played.
    first = debut_date or ""
    last = countable[0]["date"] if countable else ""
    n = len(countable)
    # What it usually sits between. Counted from the same rows the page
    # already prints, so nothing new is fetched or stored.
    before, after = neighbours(perfs, counting)
    pairs = ""
    if before or after:
        def _side(label, items):
            if not items:
                return ""
            return ("<div class='pair'><span class='cap'>%s</span>%s</div>"
                    % (label, " ".join(
                        "<span class='p'>%s<b>%d</b></span>"
                        % (html.escape(typographic(s)), n) for s, n in items)))
        pairs = ("<div class='pairs'>%s%s</div>"
                 % (_side("Usually out of", before), _side("Usually into", after)))

    caveat = NOT_A_SONG.get(doc.get("slug") or "")
    caveat = "<p class='caveat'>%s</p>" % html.escape(caveat) if caveat else ""
    subtitle = " &middot; ".join(x for x in (
        "Debut %s" % first if first else "",
        "Last played %s" % last if last and last != first else "",
        "%d performance%s" % (n, "" if n == 1 else "s"),
    ) if x)
    blurb = "Every Phish performance of %s: %d show%s" % (
        song, n, "" if n == 1 else "s")
    if first:
        blurb += ", %s to %s" % (first, last)
    if best:
        blurb += ". Best version %s (%s)" % (best[0]["date"], best[0]["score"])

    links = "".join(
        "<a class='badge' href='%s' target='_blank' rel='noopener noreferrer'>"
        "<img class='%s' src='data:image/png;base64,%s' alt='' width='13'"
        " height='13'><span>%s</span></a>"
        % (url % doc["slug"], "flip" if flip else "", icon, label)
        for label, url, icon, flip in SONG_LINKS)

    return SONG_SHELL.format(
        ago_js=AGO_JS,
        new_rows_js=NEW_ROWS_JS,
        analytics=ANALYTICS,
        css=SONG_CSS, js=SONG_JS, fonts=WEB_FONTS, sheet="../fonts.css",
        cols=cols, caveat=caveat, pairs=pairs, theme_js=THEME_JS,
        theme_ui=THEME_UI, song=html.escape(typographic(song)), subtitle=subtitle,
        hero=hero, best=top, links=links, count=len(countable), eras=chips,
        share=share_meta(html.escape(typographic(song)),
                         html.escape(blurb, quote=True),
                         "song/%s.html" % doc["slug"], card=card),
        stuckstat="<b>%d</b> shows &middot; median gap <b>%s</b>"
                  % (len(perfs), _stat(_median(gaps)) if gaps else "&mdash;"),
        head=head,          # already carries medmark; see where it is built
        rows="\n".join(rows), blurb=html.escape(blurb, quote=True),
        # Dated by the data rather than by the clock. A build stamp changed
        # every page on every run, which is exactly the churn that made
        # rebuilds expensive -- and it was answering "when did this run?"
        # when the useful question is "how current is this?"
        stamp=stamp or ("Current through %s" % last if last else "No performances"))


# ------------------------------------------------------------- song index ---

# The show index's vocabulary, with the first column widened for titles and set
# in the same face the song pages use for theirs. One stylesheet's worth of
# rules rather than a second one drifting away from the first.
SONGS_CSS = INDEX_CSS + """
/* Fixed, not auto. Every row is its own grid, so a column sized to its own
   contents put "485 shows - median 2 - longest 31 - best 90" and "325 shows -
   median 3 - longest 202 - best 79" at different widths, and the last-played
   column shifted row to row down the page. */
.row{grid-template-columns:1fr 8.5rem 23.5rem}
.r-stats{grid-template-columns:5.4rem 6.4rem 7.4rem 4.3rem}
.r-song{display:block;font-family:'IBM Plex Mono',ui-monospace,monospace;font-weight:600;
   font-size:1rem;line-height:1.3rem;color:inherit}
.r-when{font-size:.75rem;color:var(--dim);line-height:1.3rem;white-space:nowrap}
.r-when b{font-family:'IBM Plex Mono',monospace;font-weight:400;color:var(--ink-soft)}
.r-stats .score{color:var(--hot-text)}
/* The song the top score belongs to, under its label. */
.lbl .of{display:block;margin-top:.2rem;letter-spacing:.14em;color:var(--ink-soft);
   text-transform:none;font-size:.75rem}
@media screen and (max-width:620px){
  .row{grid-template-columns:1fr}
  .r-when{white-space:normal}
}
"""

SONGS_SHELL = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Songs &mdash; Possum Logic</title>
<meta property="og:type" content="website">{share}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="{fonts}" rel="stylesheet">
<link href="{sheet}" rel="stylesheet">
<style>{css}</style>{theme_js}{ago_js}{new_rows_js}</head><body><div class="wrap">
<nav class="crumb"><a href="./index.html">Shows</a><a class="here">Songs</a>
<a href="./due.html">Due</a><a href="./method.html">How this is worked out</a></nav>
<div class="rule2"></div>
<header><h1><a href="./index.html">Possum <em>Logic</em></a></h1>
<p class="show">{subtitle}</p></header>
<section class="hero">{hero}</section>
<div class="rule2"></div>
<div class="tools">
<label class="count" for="sort">Sort
<select id="sort" class="sort" disabled>
<option value="played">Most played</option><option value="az">A&ndash;Z</option>
<option value="recent">Recently played</option><option value="gap">Longest gap</option>
<option value="rated">Highest rated</option></select></label>
<input id="q" class="search" type="search" autocomplete="off" disabled
       placeholder="Search songs&hellip;" aria-label="Search songs">
<span class="count"><b id="shown">{count}</b> of {count} songs</span>
</div>
<ol class="reports" id="list">
{rows}
</ol>
<p class="empty" id="empty" hidden>No songs match that search.</p>
<footer><span><a href="./method.html">How this is worked out</a></span>{theme_ui}
<span>{stamp}</span></footer>
{analytics}
</div><script>{js}</script></body></html>
"""

SONGS_JS = """
(function(){
  var list=document.getElementById('list');
  if(!list) return;
  var rows=Array.prototype.slice.call(list.children),
      q=document.getElementById('q'), sort=document.getElementById('sort'),
      shown=document.getElementById('shown'), empty=document.getElementById('empty');
  function matcher(t){
    if(!/^\\d+$/.test(t)) return function(hay){ return hay.indexOf(t)>-1; };
    var re=new RegExp('(^|[^0-9])'+t+'([^0-9]|$)');
    return function(hay){ return re.test(hay); };
  }
  function apply(){
    var terms=q.value.toLowerCase().split(/\\s+/).filter(Boolean).map(matcher), n=0;
    rows.forEach(function(r){
      var ok=terms.every(function(t){ return t(r.getAttribute('data-search')); });
      r.hidden=!ok; if(ok) n++;
    });
    shown.textContent=n; empty.hidden=n>0;
  }
  function num(r,k){ var v=r.getAttribute(k); return v===''?-1:+v; }
  function order(){
    var k=sort.value;
    rows.slice().sort(function(a,b){
      if(k==='az') return a.getAttribute('data-song').localeCompare(b.getAttribute('data-song'));
      if(k==='recent') return b.getAttribute('data-last').localeCompare(a.getAttribute('data-last'));
      if(k==='gap') return num(b,'data-longest')-num(a,'data-longest');
      if(k==='rated') return num(b,'data-score')-num(a,'data-score');
      return num(b,'data-played')-num(a,'data-played');
    }).forEach(function(r){ list.appendChild(r); });
  }
  q.addEventListener('input', apply);
  sort.addEventListener('change', order);
  document.addEventListener('keydown', function(e){
    if(e.key==='/' && document.activeElement!==q){ e.preventDefault(); q.focus(); }
    if(e.key==='Escape' && document.activeElement===q){ q.value=''; apply(); q.blur(); }
  });
  q.disabled=false; sort.disabled=false;
  apply();
})();
"""


DUE_SHELL = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>What&rsquo;s due &mdash; Possum Logic</title>
<meta property="og:type" content="website">{share}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="{fonts}" rel="stylesheet">
<link href="{sheet}" rel="stylesheet">
<style>{css}</style>{theme_js}{ago_js}{new_rows_js}</head><body><div class="wrap">
<nav class="crumb sections"><span class="mark">Possum Logic</span>
<a href="./index.html">Shows</a><a href="./songs.html">Songs</a>
<a class="here">Due</a>
<a href="./method.html">How this is worked out</a></nav>
<div class="rule2"></div>
<header><h1>What&rsquo;s due</h1>
<p class="show">{subtitle}</p>
<p class="dek">Songs the band plays often enough to have a habit, which are now
past it. Measured against each song&rsquo;s own recent gaps, not against a
single number &mdash; a staple is late at eight shows and a rarity is not late
at eighty.</p></header>
<div class="rule2"></div>
<ol class="due">
{rows}
</ol>
<p class="dek foot">{dormant}</p>
<footer><span><a href="./method.html">How this is worked out</a></span>{theme_ui}
<span>{stamp}</span></footer>
{analytics}
</div></body></html>
"""


def render_due(docs, counting, since, card=None):
    """Songs past their own norm, longest overdue first.

    Deliberately not every song that has been gone a while. A song with no
    recent habit that has not been played in 274 shows is not *due* -- nobody
    is expecting it, and calling it due would bury the fifty-five songs someone
    might actually shout for tonight under three hundred that nobody would.
    Dormant is a different fact and the song's own page says it.
    """
    rows, dormant = [], 0
    for doc in docs:
        slug = doc["slug"]
        n = since.get(slug)
        perfs = doc.get("performances") or []
        if n is None or not perfs or slug in NOT_A_SONG:
            continue
        played = [p for p in perfs if not counting or p["date"] in counting]
        if not played:
            continue
        cutoff = _years_before(played[-1]["date"], RECENT_YEARS)
        recent = [p["gap"] for p in played[1:]
                  if p.get("gap") is not None and p["date"] >= cutoff]
        if len(recent) < MIN_HISTORY:
            if n >= BUSTOUT_GAP:
                dormant += 1
            continue
        high = _quantile(recent, BAND[1])
        if high <= 0 or n <= high:
            continue
        last = played[-1]
        rows.append((n / high, n, high, doc, last))
    rows.sort(key=lambda r: -r[0])

    out = []
    for over, n, high, doc, last in rows:
        place = ", ".join(x for x in (last.get("city"), last.get("state")) if x)
        out.append(
            "<li><a class='row' href='./song/%s.html'>"
            "<span class='d-song'>%s</span>"
            "<span class='d-last'><span class='d-date'>%s</span>"
            "<span class='d-where'>%s</span></span>"
            "<span class='d-n'><b>%s</b><span class='typ'>usually by %s</span>"
            "</span></a></li>"
            % (html.escape(doc["slug"], quote=True),
               html.escape(typographic(doc["song"])),
               last["date"], html.escape(place),
               "{:,}".format(n), _stat(high)))

    n_due = len(rows)
    subtitle = ("%d song%s past %s own usual gap"
                % (n_due, "" if n_due == 1 else "s",
                   "its" if n_due == 1 else "their"))
    tail = ("A further %d have been gone long enough to be bustouts but have no "
            "recent habit to be late against. They are dormant rather than due."
            % dormant) if dormant else ""
    blurb = "Phish songs that are overdue, measured against their own habits."
    return DUE_SHELL.format(
        analytics=ANALYTICS, ago_js=AGO_JS,
        css=INDEX_CSS, fonts=WEB_FONTS, sheet="./fonts.css",
        theme_js=THEME_JS, theme_ui=THEME_UI,
        subtitle=subtitle, rows="\n".join(out), dormant=tail,
        share=share_meta("What's due &mdash; Possum Logic",
                         html.escape(blurb, quote=True), "due.html", card=card),
        stamp="Updated %s" % _utcnow().date().isoformat())


DUE_SHELL_END = None


def due_card(docs, counting, since):
    """The due page's preview: how many, and the one that has waited longest."""
    best, n_due = None, 0
    for doc in docs:
        n = since.get(doc["slug"])
        perfs = [p for p in (doc.get("performances") or [])
                 if not counting or p["date"] in counting]
        if n is None or not perfs or doc["slug"] in NOT_A_SONG:
            continue
        cutoff = _years_before(perfs[-1]["date"], RECENT_YEARS)
        recent = [p["gap"] for p in perfs[1:]
                  if p.get("gap") is not None and p["date"] >= cutoff]
        if len(recent) < MIN_HISTORY:
            continue
        high = _quantile(recent, BAND[1])
        if high > 0 and n > high:
            n_due += 1
            if best is None or n / high > best[0]:
                best = (n / high, n, doc["song"])
    return card_markup(
        "Phish", "What&rsquo;s <em>due</em>", "Songs past their own usual gap",
        (("%d" % n_due, "Songs due", ""),
         ("{:,}".format(best[1]) if best else "&mdash;",
          html.escape(typographic(best[2][:22])) if best else "Longest wait",
          "hot")),
        size=104)


def render_songs(docs, stamp=None, card=None):
    """One page listing every song the archive holds a history for."""
    rows, entries = [], []
    for doc in docs:
        perfs = doc.get("performances") or []
        if not perfs:
            continue
        gaps = [p["gap"] for p in perfs[1:] if p["gap"] is not None]
        best = (doc.get("best") or [None])[0]
        entries.append({
            "song": doc["song"], "slug": doc["slug"], "played": len(perfs),
            "last": perfs[-1]["date"], "first": perfs[0]["date"],
            "median": _median(gaps) if gaps else None,
            "longest": max(gaps) if gaps else None,
            "score": best["score"] if best else None,
            "best_date": best["date"] if best else "",
        })
    entries.sort(key=lambda e: -e["played"])

    for e in entries:
        # One cell per figure, so the columns line up down the page rather than
        # drifting with the width of each row's numbers.
        stats = ("<span class='st'><b>%d</b> show%s</span>"
                 % (e["played"], "" if e["played"] == 1 else "s"))
        stats += ("<span class='st'>median <b>%s</b></span>" % _stat(e["median"])
                  if e["median"] is not None else "<span class='st'></span>")
        stats += ("<span class='st'>longest <b class='hot'>%s</b></span>"
                  % _stat(e["longest"]) if e["longest"] is not None
                  else "<span class='st'></span>")
        stats += ("<span class='st'>best <b class='score'>%s</b></span>" % e["score"]
                  if e["score"] is not None else "<span class='st'></span>")
        rows.append(
            "<li data-song=\"%s\" data-played='%d' data-last='%s'"
            " data-longest='%s' data-score='%s' data-search=\"%s\">"
            "<a class='row' href='./song/%s.html'>"
            "<span class='r-song'>%s</span>"
            "<span class='r-when'>last <b>%s</b></span>"
            "<span class='r-stats'>%s</span></a></li>"
            % (html.escape(e["song"], quote=True), e["played"], e["last"],
               e["longest"] if e["longest"] is not None else "",
               e["score"] if e["score"] is not None else "",
               html.escape(e["song"].lower(), quote=True),
               html.escape(e["slug"], quote=True), html.escape(e["song"]),
               e["last"], stats))

    total = sum(e["played"] for e in entries)
    top = max(entries, key=lambda e: e["score"] or -1) if entries else None
    # "Performances" on a page listing songs can be read as the band's, and
    # 27,966 of those would be some tour. The count is of songs played, so it
    # says so -- and the best version is some particular song's, so it names it
    # rather than leaving a bare 97 to be a superlative about nothing.
    hero = "".join(
        "<div class='card'><div class='lbl'>%s</div>"
        "<div class='num%s'>%s</div></div>" % (lbl, cls, val)
        for val, lbl, cls in (
            (len(entries), "Songs", ""),
            ("{:,}".format(total), "Song Performances", ""),
            (_stat(max((e["longest"] or 0) for e in entries)) if entries else "n/a",
             "Longest Gap", " hot"),
            (top["score"] if top and top["score"] else "n/a",
             "Best Rated Version%s" % ("<span class='of'>%s</span>"
                                       % html.escape(top["song"])
                                       if top and top["score"] else ""), ""),
        ))
    subtitle = ("%d song%s, played %s time%s"
                % (len(entries), "" if len(entries) == 1 else "s",
                   "{:,}".format(total), "" if total == 1 else "s"))
    blurb = ("Every song in the archive: %d of them, played %s times."
             % (len(entries), "{:,}".format(total)))
    return SONGS_SHELL.format(
        ago_js=AGO_JS,
        new_rows_js=NEW_ROWS_JS,
        analytics=ANALYTICS,
        css=SONGS_CSS, js=SONGS_JS, fonts=WEB_FONTS, sheet="./fonts.css", theme_js=THEME_JS,
        theme_ui=THEME_UI, hero=hero, count=len(entries),
        rows="\n".join(rows), subtitle=subtitle,
        share=share_meta("Songs &mdash; Possum Logic",
                         html.escape(blurb, quote=True), "songs.html", card=card),
        stamp=stamp or "Updated %s" % max((e["last"] for e in entries), default=""))


# ----------------------------------------------------------------- method ---

METHOD_CSS = INDEX_CSS + """
.prose{max-width:66ch;margin:0 0 2.4rem}
.prose h2{font-family:'Bagnard',Georgia,serif;font-weight:400;
   font-size:1.25rem;margin:2.2rem 0 .5rem;letter-spacing:0}
/* The page is almost nothing but prose -- 3.4 KB of it, eleven paragraphs --
   and it was the one place where setting everything in the mono was hardest to
   defend: this is the page that has to be read start to finish rather than
   scanned for a number. The reading face, at the measure it was already given.
   Figures inside a sentence stay mono, so a threshold quoted in the text looks
   like the same object it does on a report. */
.prose p{margin:0 0 1rem;font-family:'Literata',Georgia,serif;
   font-size:1rem;line-height:1.6;font-variation-settings:'opsz' 16;
   color:var(--ink-soft)}
.prose li{font-family:'Literata',Georgia,serif;font-size:1rem;line-height:1.6;
   font-variation-settings:'opsz' 16;color:var(--ink-soft)}
.prose b{color:var(--ink)}
.prose .verdict{display:inline-block;margin:0 .15rem;font-size:.625rem;
   letter-spacing:.14em;text-transform:uppercase}
.prose .overdue{color:var(--hot)}
.prose .premature{color:var(--cool)}
.prose .bust{background:var(--hot);color:var(--paper);padding:.1rem .3rem;
   font-weight:600;print-color-adjust:exact;-webkit-print-color-adjust:exact}
.prose .num{font-family:'IBM Plex Mono',ui-monospace,monospace;font-weight:600;font-size:1rem;
   color:var(--ink)}
"""

METHOD_SHELL = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>How this is worked out &mdash; Possum Logic</title>
<meta property="og:type" content="article">{share}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="{fonts}" rel="stylesheet">
<link href="{sheet}" rel="stylesheet">
<style>{css}</style>{theme_js}{ago_js}{new_rows_js}</head><body><div class="wrap">
<nav class="crumb"><a href="./index.html">Shows</a><a href="./songs.html">Songs</a>
<a href="./due.html">Due</a><a class="here">How this is worked out</a></nav>
<div class="rule2"></div>
<header><h1><a href="./index.html">Possum <em>Logic</em></a></h1>
<p class="show">How this is worked out</p></header>
<div class="rule2"></div>
<div class="prose">{body}</div>
<footer><span><a href="./index.html">All reports</a></span>{theme_ui}
<span>Data: Phish.net &middot; ratings fouldomain &middot; not affiliated with Phish</span></footer>
{analytics}
</div></body></html>
"""


def render_method():
    """The page the footers point at when a number wants explaining."""
    body = """
<h2 id="what-a-gap-is">What a gap is</h2>
<p>The number beside a song is how many shows the band played between this
performance and the one before it. A gap of <b class="num">0</b> means they
played it again the very next night; <b class="num">485</b> means four hundred
and eighty-five shows went by. The figure comes from Phish.net, which computes
it; nothing here is counted a second time.</p>

<h2 id="the-median-and-why-ten-years">The median, and why ten years</h2>
<p>Under each gap is that song's usual one &mdash; the median of its gaps over
the <b>ten years</b> before the show, not over all of history. Forty years of a
working band is several different bands. The 1990s dominate any all-time
figure, when they played far more shows a year out of a smaller catalogue, so
all-time gaps run much shorter and better than half of everything came out
overdue &mdash; a word that means nothing if it fits three songs in five.</p>
<p>Counting a fixed number of past performances instead does not fix it: twenty
performances is two years for a staple and twenty-four for a rarity. Kung's
last twenty reach back to 1995. Bounding by time instead means a song has to
have been in rotation lately to be judged at all.</p>
<p>The median rather than the average, because gap distributions are savagely
right-skewed: a staple with a median of 6 carries a handful of 200s, and an
average over that would call almost anything ordinary.</p>

<h2 id="the-verdicts">The verdicts</h2>
<p>A gap outside the middle 70% of that ten-year window gets called. Below it,
<span class="verdict premature">premature</span>; above it,
<span class="verdict overdue">overdue</span>; inside, nothing is said, which is
most songs. The band's ends are interpolated values that appear nowhere in the
song's actual gaps, which is why they are not printed as numbers.</p>
<p>The band is wide enough that a verdict stays worth reading: roughly
<span class="num">13%</span> of performances come out premature,
<span class="num">67%</span> expected and <span class="num">20%</span>
overdue.</p>

<h2 id="before-and-after">What came before and after</h2>
<p>A song page shows what each performance sat between. A plain
<span class="num">&#8592;</span> or <span class="num">&#8594;</span> means only
that: the song before it, the song after it, played as separate songs with a
stop between them.</p>
<p>Where phish.net recorded that the band ran two songs together, its own mark
appears in place of the arrow &mdash; <span class="num">&gt;</span> or
<span class="num">&#8211;&gt;</span> &mdash; and it sits between the two songs
it joins, the way it does in a written setlist. So an arrow is the absence of a
segue rather than the presence of anything, which is worth saying because the
two look equally deliberate on the page.</p>

<h2 id="the-bar">The bar</h2>
<p>The bar is a <b>position, not a length</b>. Its shaded middle is the band
above &mdash; where this song usually lands &mdash; the hairline through it is
the median, and the mark is the performance being reported. Left of the shading
is sooner than usual for that song, right of it is later. Past three times the
upper edge the mark stops at the end and stays there, because beyond a point
&ldquo;very late&rdquo; is the whole of the message.</p>
<p>Every row is drawn against its own song rather than against the night, so
one bustout cannot flatten the rest of the bill &mdash; on
<span class="num">168</span> of <span class="num">690</span> shows the longest
gap is at least twenty times the median. It shows position rather than
magnitude because the number beside it already gives the magnitude exactly;
what the number cannot say is whether this was early or late
<em>for this song</em>.</p>
<p>A song with fewer than <b>eight</b> performances in the ten-year window has
no band to be measured against, so its track is drawn empty rather than
implying a comparison that was never made.</p>

<h2 id="which-show-this-was">Which show this was</h2>
<p>A report says where the night sits inside its era &mdash; the
<span class="num">312th</span> show of 3.0 &mdash; and never where it sits
overall. There is no honest overall number to give. phish.net offers three
defensible totals for how many shows the band has played: <span
class="num">2,239</span> entries listed, <span class="num">2,114</span> that
count toward statistics, and <span class="num">2,106</span> distinct dates
among those. They differ by soundchecks, television and radio sessions,
cancelled dates, and nights when two separate shows were played.</p>
<p>The disagreement reaches the beginning. <b>1983-10-30</b>, the show
generally called Phish's first, is one phish.net excludes from statistics, so a
count built on that flag declares the <em>second</em> show to be number one and
every figure after it inherits the error.</p>
<p>Inside an era the count is exact for three of the four. Six dates carry more
than one counting show, and all six fall in 1.0 &mdash; the earliest being
<b>1985-02-25</b>, close enough to the start that the drift is not confined to
six shows but is inherited by every show after them, roughly <span
class="num">1,350</span> of <span class="num">1,361</span>. 2.0, 3.0 and 4.0
run one show to a date throughout, so their ordinals are counted rather than
estimated. <b>1.0 shows carry no ordinal</b>, which is a decision and not an
oversight: the number could be produced, and it would be wrong by somewhere
between one and eight with no way to tell which from the date alone.</p>

<h2 id="songs-with-no-verdict">Songs with no verdict</h2>
<p>A song needs <b>eight</b> performances inside that ten-year window before
any of this is said about it. Below that there is no current norm to be early
or late against, so it gets its numbers and no adjective. Roughly one song in
eleven falls here, which is the honest answer for something the band has nearly
stopped playing.</p>

<h2 id="bustouts">Bustouts</h2>
<p>A gap of <b class="num">100</b> or more is a
<span class="verdict bust">bustout</span> regardless of everything above. A
hundred sits where Phish.net's own setlist notes use the word. The gap alone
decides it: a gap counts shows, so a large one already proves the song has been
in the catalogue a long while &mdash; nothing newly written can reach the
threshold.</p>

<h2 id="ratings-and-jam-charts">Ratings and jam charts</h2>
<p>Version scores and the Phish.net show rating both come by way of
<b>fouldomain</b>, which is the only place the latter is exposed
programmatically. Scores are computed from a mix of community signal and audio
analysis, so a version has none until a recording of it circulates &mdash;
days or weeks after the show, sometimes never. Jam chart entries are Phish.net's
own, written months after the fact. Both are treated as optional everywhere
they appear, which is why a report published the morning after a show carries
neither.</p>

<h2 id="when-a-report-appears">When a report appears</h2>
<p>A report is published while the show is still being played. Songs appear on
it as phish.net records them, the page says <b>setlist still coming in</b> with
how much is there and when it last moved, and it reloads itself every couple of
minutes. The index says <b>so far</b> next to the song count, because
<span class="num">24</span> songs means something different tonight than it
will tomorrow.</p>
<p>Knowing when it is <em>finished</em> is the harder half, and nothing in the
data says so. There is no show time to reason from, and the format is not
promised &mdash; a rained-out show can stop mid-second-set with no encore, so
counting sets proves nothing. Stability stands in for completeness instead:
once a song count has not moved for <b>two hours</b>, the show is taken to be
over and the report stops calling itself provisional.</p>
<p>Until that happens the figures are real but partial. A median gap over nine
songs is the median of those nine, not of the night, and the preview image
shared from that page deliberately carries no figures at all &mdash; only the
date, the venue, and that the setlist is still coming in &mdash; so a link
shared mid-show does not freeze a half-finished number into somebody else's
timeline.</p>
"""
    blurb = ("How the gaps, the medians and the verdicts on this site are "
             "worked out.")
    return METHOD_SHELL.format(
        ago_js=AGO_JS,
        new_rows_js=NEW_ROWS_JS,
        analytics=ANALYTICS,
        css=METHOD_CSS, fonts=WEB_FONTS, sheet="./fonts.css", theme_js=THEME_JS, theme_ui=THEME_UI,
        body=body.strip(),
        share=share_meta("How this is worked out", html.escape(blurb, quote=True),
                         "method.html"))


# ------------------------------------------------------------------ cards ---

CARD_W, CARD_H = 1200, 630
CARD_DIR = "card"
# How many cards go into one browser launch. Each launch costs about 2.7s of
# startup and a font fetch, so doing them one at a time put eight minutes on a
# full rebuild; stacked and sliced, the same 185 take about twenty seconds.
# Chrome will not screenshot past roughly 16,000px, which is 26 of these.
CARDS_PER_SHOT = 24
# What each card was drawn from, so a card is redrawn when its own contents
# change and not merely when the page around it does. A stylesheet edit
# rewrites every page and no card: the two have nothing in common but a name.
CARD_INDEX = "cards.json"


def card_prints(site_dir):
    path = os.path.join(site_dir, "data", CARD_INDEX)
    if not os.path.isfile(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        try:
            return json.load(fh)
        except ValueError:
            return {}


def save_card_prints(site_dir, prints):
    path = os.path.join(site_dir, "data", CARD_INDEX)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(prints, fh, indent=1, sort_keys=True)


def card_print(markup):
    """What a card would look like, as a hash.

    The stylesheet is part of it. It was not, on the reasoning that a page
    carries a stylesheet and a card does not -- but CARD_CSS *is* the card's
    stylesheet, so changing the display face would have redrawn none of the
    711 cards and left every one of them set in the old type with no way to
    notice. A card is markup plus the rules that draw it.
    """
    return hashlib.sha256(
        (markup + CARD_CSS).encode("utf-8")).hexdigest()[:16]


def chrome_exe():
    """The Chrome-family browser to shoot cards with, or None."""
    exe = next((c for c in CHROME_CANDIDATES
                if os.path.isfile(c) or shutil.which(c)), None)
    return exe if not exe or os.path.isfile(exe) else shutil.which(exe)


CARD_CSS = """
*{box-sizing:border-box;margin:0}
body{background:#e9e3d6;font-family:'IBM Plex Mono',ui-monospace,monospace}
.card{width:%(w)dpx;height:%(h)dpx;background:#f2ece0;color:#17150f;
  display:flex;flex-direction:column;justify-content:center;
  padding:0 84px;position:relative;overflow:hidden}
.kind{font-size:25px;letter-spacing:.14em;text-transform:uppercase;color:#877e6e}
/* Kept clear of the mark, which starts around x=870: without a ceiling a
   middling title like "You Enjoy Myself" ran under it and the last word went
   muddy. Wrapping is better than colliding. */
h1{font-family:'Bagnard',Georgia,serif;font-weight:400;line-height:.94;
   letter-spacing:-.01em;margin-top:16px;word-break:break-word;max-width:770px}
/* Same rule as the pages: a card whose headline is a date or a song title
   sets it in Aleo, so a link and the page behind it speak the same way. */
h1.data{font-family:'IBM Plex Mono',ui-monospace,monospace;font-weight:600;letter-spacing:-.01em}
h1 em{font-style:normal;color:#c8371b}
.sub{font-size:30px;letter-spacing:.14em;text-transform:uppercase;color:#413c31;
  margin-top:20px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.rule{height:7px;background:#17150f;margin-top:38px}
.stats{display:flex;gap:58px;margin-top:30px;font-size:23px;letter-spacing:.14em;
  text-transform:uppercase;color:#877e6e}
.stats b{font-family:'IBM Plex Mono',ui-monospace,monospace;font-weight:600;font-size:52px;
  letter-spacing:0;color:#17150f;display:block;margin-bottom:4px;white-space:nowrap}
.stats .hot{color:#c8371b}
.mark{position:absolute;right:-64px;top:-72px;width:392px;height:392px;opacity:.12}
.brand{position:absolute;left:84px;bottom:40px;font-size:21px;letter-spacing:.14em;
  text-transform:uppercase;color:#877e6e}
""" % {"w": CARD_W, "h": CARD_H}

CARDS_SHELL = """<!DOCTYPE html><html><head><meta charset="utf-8">
<link href="{fonts}" rel="stylesheet">
<link href="{sheet}" rel="stylesheet">
<style>%s</style></head><body>__CARDS__</body></html>""" % CARD_CSS


def card_markup(kind, title, subtitle, stats, size=96, data=False):
    """One 1200x630 card: what it is, what it is called, and three figures."""
    figures = "".join(
        "<span><b class='%s'>%s</b>%s</span>" % (cls, val, lbl)
        for val, lbl, cls in stats)
    return ("<div class='card'>%s"
            "<div class='kind'>%s</div>"
            "<h1 class='%s' style='font-size:%dpx'>%s</h1>"
            "<div class='sub'>%s</div><div class='rule'></div>"
            "<div class='stats'>%s</div>"
            "<div class='brand'>possumlogic</div></div>"
            % (FAVICON.replace("<svg", "<svg class='mark'", 1), kind,
               "data" if data else "", size, title, subtitle, figures))


def shoot_cards(exe, jobs, site_dir):
    """Render a batch of cards in one browser launch, then slice them apart.

    -> the number written. Any failure is reported and returns 0, because a
    missing card costs a page its preview image and nothing else.
    """
    try:
        from PIL import Image
    except ImportError:
        log("cards: Pillow not installed, skipping previews")
        return 0
    out_dir = os.path.join(site_dir, CARD_DIR)
    os.makedirs(out_dir, exist_ok=True)
    written = 0
    for start in range(0, len(jobs), CARDS_PER_SHOT):
        batch = jobs[start:start + CARDS_PER_SHOT]
        # replace, not format: the stylesheet above is full of braces
        page = CARDS_SHELL.replace("__CARDS__", "".join(m for _, m in batch))
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, "cards.html")
            shot = os.path.join(tmp, "cards.png")
            with open(src, "w", encoding="utf-8") as fh:
                fh.write(page)
            cmd = [exe, "--headless", "--disable-gpu", "--hide-scrollbars",
                   "--force-device-scale-factor=1",
                   "--window-size=%d,%d" % (CARD_W, CARD_H * len(batch)),
                   "--screenshot=" + shot,
                   # Generous, because the whole batch waits on the webfonts
                   # and display=swap will happily paint a fallback first --
                   # at 6s the third family was still in flight and cards came
                   # out in whatever the system offered.
                   "--virtual-time-budget=15000",
                   "file://" + urllib.parse.quote(src)]
            try:
                with _muted_stderr():
                    subprocess.run(cmd, check=True, timeout=180,
                                   stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL)
                sheet = Image.open(shot)
            except (subprocess.SubprocessError, OSError) as exc:
                log("cards: %s", exc)
                return written
            for i, (name, _) in enumerate(batch):
                top = i * CARD_H
                if top + CARD_H > sheet.height:
                    break
                sheet.crop((0, top, CARD_W, top + CARD_H)).save(
                    os.path.join(out_dir, "%s.png" % name), optimize=True)
                written += 1
    return written


def report_card(report):
    """A show: what it was, where, and the night's headline gap.

    A show still being played gets a different card, and deliberately a fixed
    one. Withholding it entirely was the wrong call: a show in progress is
    exactly when a link gets shared, and a shared link with no preview is the
    one that looks broken. But drawing the real card would redraw it every five
    minutes all night, so the in-progress card says only what will not change
    -- the date, the venue, and that the setlist is still coming in. Its
    content hash is therefore stable, so it is drawn once at first sighting and
    then left alone until the show settles and the real one replaces it.
    """
    if report.get("provisional"):
        return card_markup(
            "Possum Logic", html.escape(report["date"]),
            html.escape((report.get("venue") or "").upper()),
            ((" ", "Setlist still coming in", "hot"),),
            size=104)
    gaps = [s["gap"] for s in report["songs"] if s["gap"] is not None]
    biggest = max(gaps) if gaps else None
    song = next((s["song"] for s in report["songs"] if s["gap"] == biggest), "")
    where = report.get("venue") or ""
    return card_markup(
        "Possum Logic", html.escape(report["date"]), html.escape(where.upper()),
        (("%d" % len(report["songs"]), "Songs", ""),
         (_stat(_median(gaps)) if gaps else "&mdash;", "Median gap", ""),
         (_stat(biggest) if gaps else "&mdash;",
          html.escape(song[:22]) or "Longest gap", "hot")),
        # No `data`: the card is a small copy of the masthead, and the masthead
        # sets its date in the display face. A shared link should look like the
        # page it opens.
        size=104)


def _card_size(title):
    """Three steps rather than a cliff, so titles do not lurch between sizes."""
    n = len(title)
    return 104 if n <= 15 else 84 if n <= 26 else 68


def song_card(doc):
    """A song: how often, how long between, and its best version."""
    perfs = doc["performances"]
    gaps = [p["gap"] for p in perfs[1:] if p["gap"] is not None]
    best = (doc.get("best") or [None])[0]
    span = ("%s &ndash; %s" % (perfs[0]["date"][:4], perfs[-1]["date"][:4])
            if perfs else "")
    title = html.escape(typographic(doc["song"]))
    return card_markup(
        "Every performance", title, span,
        (("%d" % len(perfs), "Times played", ""),
         (_stat(_median(gaps)) if gaps else "&mdash;", "Median gap", ""),
         (("%s" % best["score"]) if best else "&mdash;",
          "Best version" if best else "Longest gap", "hot")),
        size=_card_size(doc["song"]), data=True)


def index_card(reports):
    entries = [summarize(r) for r in reports]
    longest = max((e["longest"] or 0) for e in entries) if entries else 0
    return card_markup(
        # "How long since they last played it" described a gap calculator. The
        # site stopped being one a while ago; the gap is the spine of an
        # archive rather than the whole of it, and the card was the last place
        # still saying otherwise.
        "Phish", "Possum <em>Logic</em>", "An archive of every performance",
        (("%d" % len(entries), "Shows", ""),
         ("{:,}".format(sum(e["songs"] for e in entries)), "Songs logged", ""),
         (_stat(longest) if longest else "&mdash;", "Longest gap", "hot")))


def songs_card(docs):
    total = sum(len(d["performances"]) for d in docs)
    best = max((v["score"] for d in docs for v in (d.get("best") or [])),
               default=None)
    return card_markup(
        "Every song", "Possum <em>Logic</em>", "One page per song, all the way back",
        (("%d" % len(docs), "Songs", ""),
         ("{:,}".format(total), "Song performances", ""),
         (("%s" % best) if best else "&mdash;", "Best rated version", "hot")))


# ------------------------------------------------------------------- site ---

SHOW_DIR = "show"


def site_paths(site_dir, date):
    # Reports live in their own directory rather than the site root. At
    # fourteen of them the root was tidy enough; at 259 it was the whole site,
    # and any future top-level page would have had to pick a name no show could
    # ever be called.
    return (os.path.join(site_dir, SHOW_DIR, "%s.html" % date),
            os.path.join(site_dir, "data", "%s.json" % date))


# A report is named for its date and nothing else is. data/ also holds indexes
# now -- neighbours.json among them -- and globbing every .json in there read
# one as a show whose date key was missing, which is a KeyError at build time
# rather than anything as polite as a skip.
REPORT_NAME = re.compile(r"^\d{4}-\d{2}-\d{2}\.json$")


# The only two report URLs that were ever shared before reports moved into
# show/. Everything else on the site is linked, not remembered, so it follows
# the move for free; these two are out in a chat somewhere and cannot.
MOVED = ("2026-07-24", "2026-07-25")

REDIRECT = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta http-equiv="refresh" content="0; url=./show/{date}.html">
<link rel="canonical" href="{site}/show/{date}.html">
<title>{date} &mdash; Possum Logic</title>
<style>body{{font-family:ui-monospace,monospace;margin:4rem auto;max-width:32rem;
padding:0 1rem;line-height:1.6}}a{{color:#c8371b}}</style></head>
<body><p>This report has moved to
<a href="./show/{date}.html">show/{date}.html</a>.</p></body></html>
"""


def write_grain(site_dir, size=140):
    """The paper texture, as a tile beside fonts.css. Skipped without Pillow.

    Monochrome and deliberately faint. The old SVG painted full-range noise --
    single pixels from 19 to 232 on a 0-255 scale -- straight over the paper at
    28% opacity, which lifted the dark palette's #131210 to a measured #2d2c2a
    and muddied the light one. Texture should be felt rather than seen; this is
    a narrow band around mid-grey, and the blend mode in fonts.css decides which
    way it pushes.

    Deterministic, so a rebuild does not produce a new file and republish it.
    """
    path = os.path.join(site_dir, "grain.png")
    try:
        from PIL import Image
    except ImportError:
        return None
    rnd = random.Random(20260727)          # fixed: the tile must not change
    img = Image.new("L", (size, size))
    img.putdata([rnd.randint(108, 148) for _ in range(size * size)])
    img = img.convert("RGBA")
    img.putalpha(46)
    scratch = path + ".tmp"
    img.save(scratch, "PNG", optimize=True)
    with open(scratch, "rb") as fh:
        blob = fh.read()
    os.remove(scratch)
    if os.path.isfile(path):
        with open(path, "rb") as fh:
            if fh.read() == blob:
                return path
    with open(path, "wb") as fh:
        fh.write(blob)
    log("wrote %s (%d bytes)", path, len(blob))
    return path


def write_redirects(site_dir):
    """Leave a forwarding note where the two shared links used to point."""
    for date in MOVED:
        if not os.path.isfile(site_paths(site_dir, date)[1]):
            continue
        write_if_changed(os.path.join(site_dir, "%s.html" % date),
                         REDIRECT.format(date=date, site=SITE_URL))


def archived_dates(site_dir):
    data_dir = os.path.join(site_dir, "data")
    if not os.path.isdir(data_dir):
        return set()
    return {n[:-5] for n in os.listdir(data_dir) if REPORT_NAME.match(n)}


_UNREADABLE = []


def saved_reports(site_dir):
    """Every report JSON already in the site, oldest first."""
    data_dir = os.path.join(site_dir, "data")
    out = []
    for name in sorted(os.listdir(data_dir) if os.path.isdir(data_dir) else []):
        if not REPORT_NAME.match(name):
            continue
        with open(os.path.join(data_dir, name), encoding="utf-8") as fh:
            try:
                out.append(json.load(fh))
            except ValueError:
                # Loud, and counted, because an unreadable report is a show
                # missing from the site and the build will otherwise publish
                # cheerfully without it.
                log("warning: skipping unreadable %s", name)
                _UNREADABLE.append(name)
    return out


def archived(site_dir, date):
    """The report already on disk for `date`, or None."""
    _, blob = site_paths(site_dir, date)
    if not os.path.isfile(blob):
        return None
    with open(blob, encoding="utf-8") as fh:
        try:
            return json.load(fh)
        except ValueError:
            return None


# What a song page needs off each performance row. The full payload carries
# setlist notes, jamchart prose, tour ids and permalinks besides, several times
# the weight, and all of it either reconstructible or already in the show's own
# report. Trimmed, the archive's 165 songs come to 3.4 MB; untrimmed they would
# not be worth the disk.
def _gap(row):
    gap = row.get("gap")
    return int(gap) if str(gap).lstrip("-").isdigit() else None


def by_show(rows):
    """One row per show, out of a history that has one row per setlist slot.

    A song can come round more than once in a night -- Hold Your Head Up
    bookends the Fishman song, Tweezer came back twice at SNHU Arena in 2025 --
    and phish.net records each appearance. That is 717 of the archive's 28,519
    rows, across 79 of its 165 songs, and a page listing performances rather
    than setlist slots wants them collapsed: three rows reading 2025-06-22,
    2025-06-22, 2025-06-22 look like a bug even when they are the truth.

    The night's gap is the largest of them. Only the standalone performance has
    a gap to speak of -- the repeats sit at 0, having missed no shows since the
    one an hour earlier -- and taking the maximum finds it wherever it sits.
    phish.net is not consistent about that: on 2025-06-22 Tweezer's 5 is on the
    third of the three rows, and on 2025-09-19 it is on the first.

    Everything else comes off the first appearance, which is the one the set
    and position describe. `times` records how many there were, and is left off
    the ordinary single-performance night.

    Copies rather than the rows themselves: add_previous goes on to measure the
    song's gap distribution off the same list, and a collapse it did not ask
    for should not reach it from here.
    """
    out, seen = [], {}
    for row in rows:
        date = row.get("showdate")
        first = seen.get(date)
        if first is None:
            first = seen[date] = dict(row)
            out.append(first)
            continue
        first["_times"] = first.get("_times", 1) + 1
        if (_gap(row) or 0) > (_gap(first) or 0):
            first["gap"] = row.get("gap")
        # The annotated version of the night is not always the first one out of
        # the gate, so the flag and the note come off whichever appearance
        # earned them rather than off whichever came first.
        if str(row.get("isjamchart")) == "1":
            first["isjamchart"] = "1"
        for field in ("jamchart_description", "footnote"):
            if not (first.get(field) or "").strip():
                first[field] = row.get(field)
    return out


def _performance(row):
    out = {
        "date": row.get("showdate"),
        "venue": row.get("venue") or "",
        "city": row.get("city") or "",
        "state": row.get("state") or "",
        "gap": _gap(row),
        "set": str(row.get("set") or ""),
    }
    if row.get("_times"):
        out["times"] = row["_times"]
    # phish.net's own note on why this version is worth hearing, which is the
    # closest thing the API has to a rating: there is no per-performance score
    # anywhere in v5 -- reviews attach to shows, not to songs within them.
    # 15.7% of performances are jamcharted and every one of them carries prose,
    # median 178 characters. Kept verbatim, entities and all; the renderer
    # unescapes and re-escapes rather than trusting it as markup.
    if str(row.get("isjamchart")) == "1":
        out["jamchart"] = True
    jam = (row.get("jamchart_description") or "").strip()
    if jam:
        out["jam"] = jam
    # phish.net's footnote on the performance itself -- "Unfinished.", "Lyrics
    # altered to reference a hot tub." Terser and more factual than the jamchart
    # prose, on 8.6% of performances, and riding along in the same response.
    note = (row.get("footnote") or "").strip()
    if note:
        out["note"] = note
    # How the song left: 9,373 performances go out on a ">" and 1,513 on a true
    # "->". Stored now because it costs nothing; what it segued *into* needs the
    # whole setlist and does not.
    mark = (row.get("trans_mark") or "").strip()
    if mark and mark != ",":
        out["out"] = mark
    return out


def best_versions(song, **kw):
    """fouldomain's top-rated versions of one song, best first.

    Matched on the song's title, not its slug: `song=you-enjoy-myself` comes
    back empty where `song=You Enjoy Myself` returns ten. How many come back
    varies by song -- 25 for Tweezer, 10 for You Enjoy Myself -- so this takes
    what it is given rather than promising a count.

    A version only has a score once a recording of it circulates, because
    nearly half the weighting is audio analysis. That makes this a poor thing
    to block a report on, so every caller treats failure as "no scores yet".
    """
    # Ten come back unasked; the endpoint caps at 25 however much more you ask
    # for, and 25 marks on a 654-row page is still only the notable 4%.
    tracks = (foul("best-versions", song=song, limit=BEST_LIMIT,
                   **kw) or {}).get("tracks") or []
    out, seen = [], set()
    for t in tracks:
        date = t.get("date")
        # The same night can appear twice when the song was played twice; the
        # page has one row per show to hang these on, so the better score wins.
        if not date or t.get("score") is None:
            continue
        if date in seen:
            continue
        seen.add(date)
        out.append({"date": date, "score": t.get("score"),
                    "venue": t.get("venue") or "", "city": t.get("city") or "",
                    "state": t.get("state") or "", "link": t.get("link") or ""})
    out.sort(key=lambda v: (-v["score"], v["date"]))
    return out


def add_ratings(report, **kw):
    """Attach the show's ratings, or leave the report exactly as it was.

    One call, and a failed or empty one costs nothing: a show played last night
    has no rating yet either way, so the page simply does not carry the line.
    """
    try:
        report.update(show_ratings(report["date"], **kw))
    except ApiError as exc:
        log("warning: no ratings for %s: %s", report["date"], exc)
    return report


def show_ratings(date, **kw):
    """phish.net's rating for a show, and fouldomain's own score for it.

    phish.net's rating is theirs; we are taking it second-hand because their
    API does not offer it. Attributed as such wherever it is shown.
    """
    data = foul("show", date=date, **kw) or {}
    out = {}
    if data.get("pnetRating") is not None:
        out["pnet_rating"] = data["pnetRating"]
    if data.get("showScore") is not None:
        out["foul_score"] = data["showScore"]
    return out


PHISHIN = ("data", "phishin.json")


def phishin_dates(site_dir):
    """Show dates phish.in holds audio for, from disk. Empty if never fetched."""
    path = os.path.join(site_dir, *PHISHIN)
    if not os.path.isfile(path):
        return set()
    try:
        with open(path, encoding="utf-8") as fh:
            return set(json.load(fh).get("dates") or [])
    except ValueError:
        log("warning: unreadable %s", path)
        return set()


def fetch_phishin(site_dir, **kw):
    """Refresh the list of shows phish.in has. -> the set of dates.

    Three calls at a thousand a page for the whole catalogue, which is cheaper
    than asking about one show and far cheaper than being wrong: a link to
    phish.in for a show they do not have is a 404, and the show most likely to
    be missing is the one being played tonight, which is exactly the page most
    likely to be shared.
    """
    dates, page = set(), 1
    while True:
        got = foulless_json(
            "https://phish.in/api/v2/shows?per_page=1000&page=%d" % page, **kw)
        if not got:
            break
        dates |= {s["date"] for s in got.get("shows") or [] if s.get("date")}
        if page >= (got.get("total_pages") or 1):
            break
        page += 1
    if not dates:
        return phishin_dates(site_dir)
    path = os.path.join(site_dir, *PHISHIN)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    write_if_changed(path, json.dumps({"dates": sorted(dates)},
                                      separators=(",", ":")) + "\n")
    log("phish.in has audio for %d shows", len(dates))
    return dates


def foulless_json(url, cache_dir=DEFAULT_CACHE, refresh=False, **_):
    """One JSON GET with no API key, uncached. -> parsed body, or None."""
    req = urllib.request.Request(
        url, headers={"User-Agent": "possumlogic/1.0 (+personal use)",
                      "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:                                   # noqa: BLE001
        log("phish.in: %s", exc)
        return None


def write_if_changed(path, text):
    """Write only when the bytes differ. -> True if it wrote.

    There are one of these pages per song rather than per show, and a rebuild
    renders all of them. Writing every time meant a template edit -- or a run
    that changed nothing at all -- pushed the whole set to gh-pages again as
    new blobs. Nothing downstream can tell an unchanged rewrite from a real
    one, so the cheapest place to notice is here.
    """
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as fh:
            if fh.read() == text:
                return False
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return True


def song_path(site_dir, slug):
    return os.path.join(site_dir, "data", "songs", "%s.json" % slug)


def archived_songs(site_dir):
    """Slugs whose history the site already holds."""
    songs_dir = os.path.join(site_dir, "data", "songs")
    if not os.path.isdir(songs_dir):
        return set()
    return {n[:-5] for n in os.listdir(songs_dir) if n.endswith(".json")}


def save_song_history(site_dir, slug, song, rows, artist=None, best=None):
    """Archive one song's complete performance history, oldest first.

    Oldest first because that is the order the gaps were earned in, and
    because a show being added then appends at the end of the file instead of
    shifting every line in it -- this archive lives in git and is rewritten
    once per song per show.

    One performance per line for the same reason. json.dump(indent=2) spends
    107 KB on You Enjoy Myself's 654 performances where this spends 78 KB, and
    turns a one-show diff into six changed lines rather than one.
    """
    path = song_path(site_dir, slug)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    # No fetched-at stamp: it would rewrite every file on every run whether or
    # not the history moved, and the last row already says when it last moved.
    # Scores are fetched separately and can fail on their own, so a history
    # rewritten while fouldomain is down keeps the ones it already had rather
    # than dropping them and waiting for the next seed.
    held = song_history(site_dir, slug) or {}
    if best is None:
        best = held.get("best") or []
    # Neighbours cost a call per show to work out and are not in this response,
    # so a history rewritten from the API carries forward the ones it had
    # rather than making the twenty-minute backfill run again.
    keep = {p["date"]: {k: p[k] for k in ("prev", "in", "next", "nb") if k in p}
            for p in held.get("performances") or []}
    perfs = [_performance(r) for r in by_show(rows)]
    for p in perfs:
        p.update(keep.get(p["date"]) or {})
    return write_song_file(site_dir, slug,
                           {"song": song, "slug": slug, "artist": artist or ""},
                           perfs, best)


def write_song_file(site_dir, slug, head, perfs, best):
    """The archive file itself, given rows already in their stored shape."""
    path = song_path(site_dir, slug)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    lines = lambda rows: ",\n".join(
        "  " + json.dumps(r, separators=(", ", ": ")) for r in rows)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("{\n%s,\n \"best\": [\n%s\n ],\n \"performances\": [\n%s\n ]\n}\n"
                 % (",\n".join(" %s: %s" % (json.dumps(k), json.dumps(v))
                               for k, v in head.items()),
                    lines(best), lines(perfs)))
    return path


def song_history(site_dir, slug):
    """The archived history for `slug`, or None."""
    path = song_path(site_dir, slug)
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as fh:
        try:
            return json.load(fh)
        except ValueError:
            log("warning: skipping unreadable %s", path)
            return None


# --------------------------------------------------------------- schedule ---

# phish.net lists announced dates alongside played ones, so the schedule comes
# from a call the calendar already makes. What it does not carry is a start
# time -- there is no time field of any kind -- so knowing *when* to look still
# needs a local clock, and a local clock needs the venue's zone.
#
# Not derived from coordinates. Zone boundaries follow county lines rather than
# meridians, so deriving them means either a geo API with a quota or a shapefile
# dependency, to answer a question with 157 distinct venues and three countries
# in it. A checked table is smaller than the code that would avoid it, costs no
# network, and is wrong only where a diff can show it.
TZ_BY_STATE = {
    # Eastern
    "CT": "America/New_York", "DC": "America/New_York", "DE": "America/New_York",
    "GA": "America/New_York", "MA": "America/New_York", "MD": "America/New_York",
    "ME": "America/New_York", "NC": "America/New_York", "NH": "America/New_York",
    "NJ": "America/New_York", "NY": "America/New_York", "OH": "America/New_York",
    "PA": "America/New_York", "RI": "America/New_York", "SC": "America/New_York",
    "VA": "America/New_York", "VT": "America/New_York", "WV": "America/New_York",
    # Central
    "AL": "America/Chicago", "AR": "America/Chicago", "IA": "America/Chicago",
    "IL": "America/Chicago", "LA": "America/Chicago", "MN": "America/Chicago",
    "MO": "America/Chicago", "MS": "America/Chicago", "OK": "America/Chicago",
    "WI": "America/Chicago",
    # Mountain and Pacific
    "CO": "America/Denver", "MT": "America/Denver", "NM": "America/Denver",
    "UT": "America/Denver", "WY": "America/Denver",
    "CA": "America/Los_Angeles", "NV": "America/Los_Angeles",
    "WA": "America/Los_Angeles",
    # Outside the US, by province rather than state
    "Quintana Roo": "America/Cancun", "Ontario": "America/Toronto",
}

# The eight states Phish plays that span two zones. Every venue in them
# resolves by city, and Tennessee is the only one where it genuinely decides
# anything -- Knoxville is Eastern, Nashville and Manchester are Central.
TZ_BY_CITY = {
    ("AZ", "Phoenix"): "America/Phoenix",          # no DST, so not Denver
    ("FL", "Jacksonville"): "America/New_York",
    ("FL", "Miami"): "America/New_York",
    ("IN", "Noblesville"): "America/Indiana/Indianapolis",
    ("KY", "Louisville"): "America/New_York",
    ("MI", "Clarkston"): "America/Detroit",
    ("MI", "Detroit"): "America/Detroit",
    ("MI", "Grand Rapids"): "America/Detroit",
    ("OR", "Bend"): "America/Los_Angeles",
    ("OR", "Eugene"): "America/Los_Angeles",
    ("OR", "Portland"): "America/Los_Angeles",
    ("TN", "Knoxville"): "America/New_York",
    ("TN", "Manchester"): "America/Chicago",
    ("TN", "Nashville"): "America/Chicago",
    ("TX", "Austin"): "America/Chicago",
    ("TX", "Del Valle"): "America/Chicago",
    ("TX", "Grand Prairie"): "America/Chicago",
}


def venue_zone(row):
    """IANA zone for a show row, or None when we cannot say.

    None is a real answer and the caller must treat it as one: a venue we have
    no zone for gets no watch window and falls back to the ordinary sweep,
    which is late but never wrong. Guessing a zone would schedule a burst of
    polling at the wrong hour and quietly miss the show.
    """
    state = (row.get("state") or "").strip()
    city = (row.get("city") or "").strip()
    return TZ_BY_CITY.get((state, city)) or TZ_BY_STATE.get(state)


# When to be watching, in the venue's own local time. Deliberately generous at
# both ends, because the two ways of being wrong do not cost the same: polling
# a few extra times on a public repo costs nothing, and being twenty minutes
# late to open costs the first set. So exceptions widen the window; none of
# them narrows it.
#
# The default opens before the earliest plausible downbeat -- setlist.fm has
# tonight's Garden show scheduled for 19:30, and shows run 19:25 to 20:10 -- and
# closes after a four-hour show plus the quiet period a setlist needs to settle.
WATCH_DEFAULT = ((19, 0), (2, 30))

# Mexico is the standing exception and the reason the window is a table rather
# than a constant. The run does not keep one start time: the first night runs
# late for people still arriving, the middle nights are ordinary but early, and
# the last night is early again for people flying out. Rather than encode which
# night is which -- and be wrong the year they reorder it -- the window spans
# all of them.
WATCH_RULES = (
    (lambda s: s.get("tz") == "America/Cancun", ((17, 0), (3, 30))),
)

SCHEDULE = ("data", "schedule.json")

# phish.net logs unnamed improvisation under the title "Jam", which makes it
# the 125th most played "song" in the catalogue with 93 performances. It is not
# a composition, so every figure on its page answers a different question than
# the same figure does anywhere else: its median gap is how often the band
# improvises without naming what came out, not how often they play a song.
# Left unsaid, the page reads as a straightforwardly popular tune.
#
# Only entries that are genuinely not songs. Big Ball Jam is a song, Woodlands
# Jam is a named one-off, and neither belongs here.
NOT_A_SONG = {
    "jam": "phish.net files unnamed improvisation under this title, so this is "
           "not one composition but every jam the band never named. The figures "
           "below are real counts, but they describe how often that happens "
           "rather than how often a particular song is played.",
}


def watch_window(show):
    """(open, close) in UTC for one scheduled show, or None without a zone.

    The close is on the following day whenever it falls after midnight, which
    for a show starting at seven in the evening it always does.
    """
    if not show.get("tz"):
        return None
    try:
        zone = zoneinfo.ZoneInfo(show["tz"])
    except Exception:                                          # noqa: BLE001
        return None
    (oh, om), (ch, cm) = WATCH_DEFAULT
    for matches, window in WATCH_RULES:
        if matches(show):
            (oh, om), (ch, cm) = window
            break
    try:
        day = datetime.date.fromisoformat(show["date"])
    except ValueError:
        return None
    start = datetime.datetime.combine(
        day, datetime.time(oh, om), tzinfo=zone)
    end = datetime.datetime.combine(
        day + datetime.timedelta(days=1), datetime.time(ch, cm), tzinfo=zone)
    return start.astimezone(datetime.timezone.utc), \
        end.astimezone(datetime.timezone.utc)


def next_show(site_dir, now=None):
    """The soonest scheduled show still ahead of `now`, or None.

    Only for the log: a run that did nothing is much easier to trust when it
    says what it is waiting for.
    """
    now = (now or _utcnow()).date().isoformat()
    path = os.path.join(site_dir, *SCHEDULE)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            shows = json.load(fh).get("shows") or []
    except ValueError:
        return None
    return next((s for s in shows if s.get("date", "") >= now), None)


def watching(site_dir, now=None):
    """Scheduled shows whose watch window contains `now`. Usually empty.

    This is the whole gate: a run that finds nothing here has done no API call
    and can stop. Reading a file the repo already holds is the cheapest
    possible answer to "is anything happening", and on most days it is no.
    """
    now = now or _utcnow()
    path = os.path.join(site_dir, *SCHEDULE)
    if not os.path.isfile(path):
        return []
    try:
        with open(path, encoding="utf-8") as fh:
            shows = json.load(fh).get("shows") or []
    except ValueError:
        log("warning: unreadable %s", path)
        return []
    live = []
    for s in shows:
        w = watch_window(s)
        if w and w[0] <= now <= w[1]:
            live.append(s)
    return live


def fetch_schedule(site_dir, apikey, artist="Phish", **kw):
    """Announced shows that have not happened yet. -> the list, soonest first.

    Rewritten whole every run rather than merged, which is what makes it
    self-correcting: the 2021 New Year's run was announced for December, then
    withdrawn, then re-announced for the following April. A merge would have
    kept believing in the December dates forever.
    """
    today = _utcnow().date()
    out = []
    # Always past the cache: an announced date that has been withdrawn is
    # exactly the thing this file exists to notice, and a cached answer cannot.
    fresh = dict(kw, refresh=True)
    for year in (today.year, today.year + 1):
        for row in get("shows/showyear/%d" % year, apikey, **fresh):
            if artist and row.get("artist_name") != artist:
                continue
            # Yesterday counts. A show is dated by its local evening, but its
            # watch window runs past midnight UTC -- a Garden show on the 27th
            # is watched until 06:30 UTC on the 28th. Dropping anything before
            # today therefore deleted the show that was on stage at the moment
            # UTC rolled over, which is the middle of every east-coast set, and
            # the watcher then could not see a show it had been following. The
            # window decides when to stop looking; this only decides what to
            # remember.
            date = row.get("showdate") or ""
            if date < (today - datetime.timedelta(days=1)).isoformat():
                continue
            out.append({"date": date,
                        "venue": row.get("venue") or "",
                        "city": row.get("city") or "",
                        "state": row.get("state") or "",
                        "country": row.get("country") or "",
                        "tz": venue_zone(row) or ""})
    out.sort(key=lambda s: (s["date"], s["venue"]))
    path = os.path.join(site_dir, *SCHEDULE)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    write_if_changed(path, json.dumps(
        {"fetched": today.isoformat(), "shows": out}, indent=1) + "\n")
    unknown = [s for s in out if not s["tz"]]
    if unknown:
        log("warning: no time zone for %d scheduled venue(s): %s",
            len(unknown), "; ".join("%s %s" % (s["date"], s["venue"]) for s in unknown[:4]))
    return out


# --------------------------------------------------------------- calendar ---

# A gap is a count of shows, so it needs the list of shows -- and that list is
# not the archive. The archive holds the reports we have written, which is a
# subset of what the band played, so counting its rows undercounts every gap
# that spans a show we never fetched.
#
# phish.net flags the shows that do not count toward statistics. Of the 289
# Phish shows it lists for 2020-2026, 39 carry exclude_from_stats: 27 are the
# cancelled 2020 Summer Tour dates that became the Dinner and a Movie webcasts,
# which are replays of shows already in the record and would otherwise inflate
# every gap spanning that summer. The flag is phish.net's own judgment about
# what counts, which is a better thing to defer to than a rule of our own.
CALENDAR = ("data", "calendar.json")


def calendar_path(site_dir):
    return os.path.join(site_dir, *CALENDAR)


def load_calendar(site_dir):
    """Every show date that counts toward a gap, oldest first."""
    path = calendar_path(site_dir)
    if not os.path.isfile(path):
        return []
    with open(path, encoding="utf-8") as fh:
        try:
            return json.load(fh).get("shows") or []
        except ValueError:
            log("warning: skipping unreadable %s", path)
            return []


def fetch_calendar(site_dir, apikey, years, artist="Phish", **kw):
    """Refresh `years` of the show calendar. -> every counting date, sorted.

    One call per year. Only the current year needs re-asking on a normal run,
    which is why this is cheap enough to sit in the scheduled job; a full
    backfill is one call per year of the band's career and happens once.
    """
    have = set(load_calendar(site_dir))
    # showyear lists a tour that has been announced as readily as one that has
    # been played -- asking in July 2026 returns dates into September -- and a
    # show nobody has played yet cannot be a show a song has gone without.
    #
    # Strictly before today in UTC, not up to and including it. The band plays
    # in the evening in North America, which is already tomorrow in UTC, so a
    # date equal to the UTC date is a show that has either not started or not
    # finished. Cutting below it costs nothing -- a show that ended at 04:00
    # UTC is counted the moment that day ends -- and never counts a concert
    # that has not happened.
    today = _utcnow().date().isoformat()
    for year in years:
        prefix = "%d-" % year
        fresh = set()
        for row in get("shows/showyear/%d" % year, apikey, **kw):
            if artist and row.get("artist_name") != artist:
                continue
            if str(row.get("exclude_from_stats")) in ("1", "True"):
                continue
            date = row.get("showdate") or ""
            # Two shows on one date is still one date: .net's own gap figures
            # count 2021-12-31 once, and a date is what a performance carries.
            if date and date < today:
                fresh.add(date)
        # Replace the year wholesale, so a show phish.net has since withdrawn
        # or newly flagged actually leaves the calendar.
        have = {d for d in have if not d.startswith(prefix)} | fresh
    dates = sorted(have)
    path = calendar_path(site_dir)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    write_if_changed(path, "{\n \"shows\": [\n%s\n ]\n}\n"
                     % ",\n".join('  "%s"' % d for d in dates))
    return dates


def shows_since(dates, date):
    """How many counting shows the band has played since `date`."""
    return len(dates) - bisect.bisect_right(dates, date)


def write_current(site_dir, dates=None):
    """The one file that changes when a show is played.

    Every song's count moves at once -- play one song and all the others go up
    by one -- so this cannot be rendered into the pages without rewriting all
    of them every time. At 379 songs that is 48 MB pushed per show, and the
    catalog is nowhere near its full size. Here it is a single file of a few
    kilobytes that the pages read at load, so a show changes exactly one blob.

    Deliberately not called a gap. phish.net's gap is not reproducible from
    the show calendar -- two songs spanning the same pair of shows can carry
    different gaps, so there is a per-song term in it we cannot see -- and
    publishing a number that disagrees with theirs under their name would be
    worse than publishing our own under ours. This counts shows since the last
    performance, which is exact because we define it.
    """
    if dates is None:
        dates = load_calendar(site_dir)
    if not dates:
        return None
    since = {}
    for slug in sorted(archived_songs(site_dir)):
        doc = song_history(site_dir, slug)
        perfs = (doc or {}).get("performances") or []
        if perfs:
            since[slug] = shows_since(dates, perfs[-1]["date"])
    path = os.path.join(site_dir, "data", "current.json")
    write_if_changed(path, json.dumps(
        {"as_of": dates[-1], "shows": len(dates), "since": since},
        separators=(",", ":"), sort_keys=True) + "\n")
    return path


def show_kind(report, calendar=None):
    """Whether an archived report is a show, a soundcheck or a session.

    Nine of the archive's entries are not concerts. phish.net lists them and
    flags them exclude_from_stats, which is why they are absent from the
    calendar, and their notes say which kind they are: five Moon Palace
    soundchecks, the Mondegreen soundcheck, two Tonight Show appearances and an
    NPR Tiny Desk. A gap counted over them would be counting a soundcheck as a
    show the band played, and 2020-02-19 -- a soundcheck -- is the oldest entry
    in the archive, so it opened the index.

    phish.net is not consistent about this across its whole history: of twenty
    studio, TV and radio sessions in the song histories, eight count and twelve
    do not, split roughly at 1999. We defer to the flag rather than invent a
    rule, so where they disagree with themselves we disagree with ourselves in
    exactly the same places, which is at least auditable.
    """
    if calendar is None:
        calendar = ()
    if report["date"] in set(calendar):
        return "show"
    notes = re.sub(r"<[^>]+>", " ", html.unescape(str(report.get("notes") or "")))
    # "was the soundcheck for X", but also "there were two soundchecks for X"
    # and "the tech rehearsal for X" -- all the same thing, a non-show that
    # exists because of a show that follows it. A television or radio session
    # exists on its own account and matches none of them.
    return ("soundcheck"
            if re.search(r"\b(?:soundchecks?|rehearsal)\b[^.]{0,60}\bfor\b",
                         notes, re.I)
            else "session")


def split_archive(reports, calendar):
    """(concerts, everything else), the second oldest-first and annotated.

    A soundcheck belongs to the show it precedes -- that is what it is for --
    so each one carries the date of the next concert on the calendar.
    """
    dates = sorted(calendar)
    shows, aside = [], []
    for r in sorted(reports, key=lambda r: r["date"]):
        kind = show_kind(r, dates)
        if kind == "show":
            shows.append(r)
            continue
        i = bisect.bisect_right(dates, r["date"])
        aside.append({"report": r, "kind": kind,
                      "before": dates[i] if i < len(dates) else None})
    return shows, aside


def archived_history(site_dir, slug, date):
    """A song's history from disk, in the shape add_previous wants, or None.

    setlists/slug returns a song's *whole* history, so archiving one show's
    songs archives their 1980s performances too. Backfilling therefore asks
    phish.net for history it already has: at 21 songs a show, a 440-show
    backfill of 3.0 is some 9,000 calls to re-read files on this disk.

    Returned only when the stored history already contains the show being
    built. That is the exact condition under which it is known to be complete
    for this purpose -- a history missing tonight is a history that predates
    tonight, and its gaps stop short. Anything else falls through to the API.
    """
    if not site_dir:
        return None
    doc = song_history(site_dir, slug)
    perfs = (doc or {}).get("performances") or []
    if not any(p.get("date") == date for p in perfs):
        return None
    # Stored oldest-first and already one row per show, which is what by_show
    # and own_history would have produced on the way in.
    return [{"showdate": p["date"], "venue": p.get("venue") or "",
             "city": p.get("city") or "", "state": p.get("state") or "",
             "gap": p.get("gap"), "out": p.get("out") or ""} for p in perfs]


def setlist_neighbours(rows, artist=None):
    """What each song followed and led into, per slug, for one show.

    Scoped to the set: a set opener has nothing before it, and saying it
    followed the last song of the previous set would be a lie about a gap of
    twenty minutes. A song played more than once in a night keeps the first
    appearance, which is the row the archive keeps too.

    The mark between two songs belongs to the earlier of them -- phish.net
    stores it as the trailing punctuation -- so the way *into* a song is the
    previous row's mark, not its own.
    """
    rows = [r for r in rows
            if r.get("song") and (not artist or r.get("artist_name") == artist)]
    rows.sort(key=lambda r: (SET_ORDER.get(str(r.get("set")), 9),
                             int(r.get("position") or 0)))
    out = {}
    for i, r in enumerate(rows):
        slug = r.get("slug") or r.get("song")
        if slug in out:
            continue
        same = lambda j: (0 <= j < len(rows)
                          and str(rows[j].get("set")) == str(r.get("set")))
        nb = {}
        if same(i - 1):
            nb["prev"] = rows[i - 1].get("song") or ""
            mark = (rows[i - 1].get("trans_mark") or "").strip()
            if mark and mark != ",":
                nb["in"] = mark
        if same(i + 1):
            nb["next"] = rows[i + 1].get("song") or ""
        if nb:
            out[slug] = nb
    return out


NEIGHBOUR_INDEX = "neighbours.json"
NEIGHBOUR_FLUSH = 150


def seed_setlists(site_dir, apikey, artist="Phish", force=False, **kw):
    """Backfill what came before and after each archived performance.

    One setlist call per distinct show. Every row a call covers is marked
    asked, on the row itself rather than in an index of dates: a date index
    cannot tell "asked, and this song opened the set" from "never asked", so
    adding songs later left them with no neighbours on dates the index already
    called done -- 88 songs added in one backfill came out at 0.3% covered.

    Flushed in batches, because twenty minutes of fetching should not have to
    start over because a laptop lid closed.
    """
    songs = {}
    for slug in sorted(archived_songs(site_dir)):
        doc = song_history(site_dir, slug)
        if doc:
            songs[slug] = doc

    # One-time migration off the old date index: a song that already carries
    # neighbours somewhere was walked while that index was being built, so its
    # rows on those dates were genuinely asked about.
    index = os.path.join(site_dir, "data", NEIGHBOUR_INDEX)
    if os.path.isfile(index):
        with open(index, encoding="utf-8") as fh:
            try:
                seen = set(json.load(fh).get("dates") or [])
            except ValueError:
                seen = set()
        for doc in songs.values():
            if not any(p.get("prev") or p.get("next") for p in doc["performances"]):
                continue
            for p in doc["performances"]:
                if p["date"] in seen:
                    p["nb"] = 1
        os.remove(index)

    todo = sorted({p["date"] for d in songs.values() for p in d["performances"]
                   if force or not p.get("nb")})
    if not todo:
        log("neighbours: nothing to fetch")
        return 0

    log("neighbours: %d show%s to fetch",
        len(todo), "" if len(todo) == 1 else "s")
    pending, fetched, missed = {}, 0, []

    def flush():
        for slug in sorted(pending):
            doc = songs[slug]
            write_song_file(site_dir, slug,
                            {k: doc.get(k, "") for k in ("song", "slug", "artist")},
                            doc["performances"], doc.get("best") or [])
        pending.clear()

    for i, date in enumerate(todo, 1):
        try:
            rows = get("setlists/showdate/%s" % date, apikey, **kw)
        except ApiError as exc:
            missed.append("%s (%s)" % (date, exc))
            continue
        nb = setlist_neighbours(rows, artist)
        for slug, doc in songs.items():
            for p in doc["performances"]:
                if p["date"] != date:
                    continue
                # Marked whether or not there was anything to say, so a set
                # opener is not asked about again on every future run.
                p["nb"] = 1
                p.update(nb.get(slug) or {})
                pending[slug] = True
        fetched += 1
        if i % NEIGHBOUR_FLUSH == 0:
            flush()
            log("  %d/%d shows", i, len(todo))
    flush()
    if missed:
        log("warning: no setlist for %d show%s: %s",
            len(missed), "" if len(missed) == 1 else "s", "; ".join(missed[:5]))
    log("neighbours: %d show%s fetched", fetched, "" if fetched == 1 else "s")
    return fetched


# How far back to keep asking about a show that still has no rating. Measured
# on this archive: every show four days old or more had one, the two newer than
# that had none, so the answer arrives somewhere in between. --recheck's three
# days would have missed a rating landing on the fourth, and re-fetching whole
# shows to find out is a poor trade when the rating is one call on its own.
RATING_CHASE_DAYS = 21


def sweep_ratings(site_dir, days=RATING_CHASE_DAYS, **kw):
    """Re-ask about archived shows that still have no rating.

    Ratings show up days after a show, long after its setlist has settled and
    the report stopped being re-fetched. This asks only about the shows still
    missing one, only for as long as one might plausibly arrive, and only of
    fouldomain -- phish.net is not touched.
    """
    cutoff = (_utcnow().date() - datetime.timedelta(days=days)).isoformat()
    todo = [r for r in saved_reports(site_dir)
            if r["date"] >= cutoff and r.get("pnet_rating") is None]
    if not todo:
        return []
    log("ratings: %d recent show%s still without one",
        len(todo), "" if len(todo) == 1 else "s")
    found = []
    for report in todo:
        got = {}
        try:
            got = show_ratings(report["date"], **kw)
        except ApiError as exc:
            log("  %s: %s", report["date"], exc)
        if not got:
            continue
        # fouldomain answers with whatever it has, and it has its own score for
        # a show well before phish.net has a rating for it -- so a non-empty
        # reply is not the same as the reply we came for. Keeping the score is
        # still worth the write; announcing a rating that is not there is a
        # KeyError that kills the whole run, which is what it did.
        report.update(got)
        _, blob = site_paths(site_dir, report["date"])
        with open(blob, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2)
        rating = got.get("pnet_rating")
        if rating is None:
            log("  %s: fouldomain has a score but phish.net has no rating yet",
                report["date"])
            continue
        found.append(report["date"])
        log("  %s rated %.2f", report["date"], rating)
    return found


def seed_scores(site_dir, songs=None, **kw):
    """Fill in fouldomain's top-rated versions for archived songs.

    One call per song. Songs that already have scores are skipped unless named
    explicitly, because the top of a forty-year song's ranking does not move
    when the band plays it once more -- a new performance essentially never
    enters its own all-time best list on the night.
    """
    have = archived_songs(site_dir)
    todo = sorted(songs if songs is not None
                  else (s for s in have
                        if not (song_history(site_dir, s) or {}).get("best")))
    if not todo:
        return 0
    log("scores: %d song%s to ask fouldomain about",
        len(todo), "" if len(todo) == 1 else "s")
    written, missed = 0, []
    for i, slug in enumerate(todo, 1):
        doc = song_history(site_dir, slug)
        if not doc:
            continue
        try:
            best = best_versions(doc["song"], **kw)
        except ApiError as exc:
            missed.append("%s (%s)" % (doc["song"], exc))
            continue
        write_song_file(site_dir, slug,
                        {k: doc.get(k, "") for k in ("song", "slug", "artist")},
                        doc["performances"], best)
        written += 1
        top = best[0] if best else None
        log(" [%d/%d] %-34s %2d rated%s",
            i, len(todo), doc["song"], len(best), " best %s (%s)" % (top["date"], top["score"]) if top else "")
    if missed:
        log("warning: no scores for %d song%s: %s",
            len(missed), "" if len(missed) == 1 else "s", "; ".join(missed[:5]))
    return written


def seed_songs(site_dir, apikey, artist="Phish", force=False, **kw):
    """Backfill histories for every song the saved reports already name.

    Ordinarily a song's history arrives with the show that played it, which
    means the corpus fills in over tours rather than all at once. This pays
    the calls up front instead, so every song in the archive has a page today.
    Songs already held are skipped unless --force, which makes a second run
    cost nothing.
    """
    wanted = {}
    for report in saved_reports(site_dir):
        for s in report["songs"]:
            wanted.setdefault(s["slug"], s["song"])
    have = set() if force else archived_songs(site_dir)
    todo = sorted(slug for slug in wanted if slug not in have)
    log("seeding: %d song%s named by the archive, %d already held, %d to fetch",
        len(wanted), "" if len(wanted) == 1 else "s", len(wanted) - len(todo), len(todo))

    missed, written = [], 0
    for i, slug in enumerate(todo, 1):
        try:
            rows = get("setlists/slug/%s" % slug, apikey, **kw)
        except ApiError as exc:
            missed.append("%s (%s)" % (wanted[slug], exc))
            continue
        rows = own_history(rows, artist)
        if not rows:
            # Every song here came out of a report for this artist, so an empty
            # history means the slug moved rather than that the song is new.
            missed.append("%s (no %s performances)" % (wanted[slug], artist))
            continue
        save_song_history(site_dir, slug, wanted[slug], rows, artist)
        written += 1
        shows = len(by_show(rows))
        log(" [%d/%d] %-34s %4d show%s%s",
            i, len(todo), wanted[slug], shows, " " if shows == 1 else "s", "" if shows == len(rows) else " (+%d same-night repeat%s)" % (len(rows) - shows, "" if len(rows) - shows == 1 else "s"))
    if missed:
        log("warning: no history for %d song%s: %s",
            len(missed), "" if len(missed) == 1 else "s", "; ".join(missed))
    log("seeded %d song histor%s into %s",
        written, "y" if written == 1 else "ies", os.path.join(site_dir, "data", "songs"))
    return written


def _coverage(report):
    """Songs, and how many of them know when they were last played.

    Song count alone is too coarse a measure of a better report: a re-fetch
    interrupted by a network drop returns the whole setlist with some of the
    per-song history missing, and would pass a count-only comparison.
    """
    songs = report.get("songs") or []
    return len(songs), sum(1 for s in songs if s.get("prev_date") or s.get("debut"))


def is_fuller(report, prior):
    """Whether a re-fetched show is worth replacing the archived one with.

    A re-check exists to complete a setlist that was archived mid-entry, so it
    must never do the reverse and trade a fuller report for a thinner one.
    """
    if not prior:
        return True
    was, now = _coverage(prior), _coverage(report)
    if now >= was:
        return True
    log("keeping archived %s: %d songs/%d with history beats the %d/%d just " "fetched",
        report["date"], was[0], was[1], now[0], now[1])
    return False


def _ts(value):
    """Parse an archived timestamp, or None if it is missing or unreadable.

    Naive values are read as UTC. A stamp we cannot trust restarts the quiet
    period, which delays a show rather than publishing a partial one.
    """
    try:
        t = datetime.datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    return t if t.tzinfo else t.replace(tzinfo=datetime.timezone.utc)


def _certainly_over(showdate, now):
    """True once no show on `showdate` could still be running anywhere in NA."""
    bound = datetime.datetime.combine(
        datetime.date.fromisoformat(showdate) + datetime.timedelta(days=1),
        LAST_END_UTC, tzinfo=datetime.timezone.utc)
    return now >= bound


def settle(report, prior, now):
    """Mark a freshly fetched show provisional until its song count holds still.

    Completeness cannot be read off the data. There is no showtime to reason
    from, the show record's updated_at lags by days, and the format is not
    promised -- a rained-out show can stop mid-second-set with no encore, so
    counting sets proves nothing. Stability stands in for completeness instead:
    a count that has not moved for QUIET_HOURS is taken for the whole show.
    Nothing about geography or set lengths is assumed, so a weather-shortened
    night converges exactly like a normal one; it just stops growing sooner.
    """
    count = len(report["songs"])
    same = prior and len(prior.get("songs") or []) == count
    since = _ts((prior or {}).get("count_since")) if same else None
    since = since if since and since <= now else now
    report["count_since"] = since.isoformat(timespec="seconds")
    held = now - since
    # An encore is the band saying the show is over, so the quiet period after
    # one can be much shorter than the one after an ordinary song. Two hours is
    # sized for the worst case -- a rained-out show that stops mid-second-set
    # with no encore and no other signal that it has ended. Once an encore has
    # been recorded, that worst case is not the case we are in, and holding the
    # page at "still coming in" for another two hours is simply wrong for most
    # of that time. Thirty minutes still covers a second encore, which is the
    # only thing that realistically follows the first.
    encored = any(str(s.get("set") or "").lower().startswith("e")
                  for s in report["songs"])
    wait = ENCORE_QUIET if encored else datetime.timedelta(hours=QUIET_HOURS)
    report["encored"] = encored
    report["provisional"] = not (held >= wait
                                or _certainly_over(report["date"], now))
    if report["provisional"]:
        log("%s still coming in: %d song%s, unchanged for %d of the %d min "
            "needed to call it finished%s",
            report["date"], count, "" if count == 1 else "s",
            held.total_seconds() // 60, wait.total_seconds() // 60,
            " (encore played)" if encored else "")
    elif prior is not None and (prior or {}).get("provisional"):
        log("%s settled: %d song%s, publishing as complete",
            report["date"], count, "" if count == 1 else "s")
    return report


def write_site(site_dir, reports, bar_scale="linear", rebuild=False):
    """Add reports to the site and rebuild the index around them.

    The JSON sidecar in data/ is the archive: it is what lets --rebuild
    re-render every page after a template change without touching the API.
    """
    os.makedirs(os.path.join(site_dir, "data"), exist_ok=True)
    # Archive everything first, provisional included, so the neighbour map that
    # the prev/next links need is built from the whole published site at once.
    for report in reports:
        _, blob = site_paths(site_dir, report["date"])
        with open(blob, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2)

    # Everything publishes, unfinished included. A show is worth reading while
    # it is happening, and the page says plainly that it is still coming in --
    # which is more honest than a site that pretends nothing is going on for
    # the four hours a show takes plus the two it takes to settle.
    known = list(saved_reports(site_dir))
    order = sorted(r["date"] for r in known)
    around = {d: (order[i - 1] if i else None,
                  order[i + 1] if i + 1 < len(order) else None)
              for i, d in enumerate(order)}

    # A new show gives its neighbour a next link it did not have, so that page
    # is stale too. --rebuild rewrites the lot regardless.
    fresh = {r["date"] for r in reports}
    stale = set(fresh)
    for date in fresh:
        stale |= {d for d in around.get(date, ()) if d}

    # A page and its preview card are made together, so a link shared the
    # moment a show lands already has a picture on it. No browser to draw them
    # with means no cards, and every page falls back to the house one rather
    # than pointing at a file that will never exist.
    # Drawing them needs a browser; naming them does not. A build without one
    # leaves the cards to the next build that has one, and the pages stay
    # byte-identical either way.
    exe = chrome_exe()
    jobs, prints = [], card_prints(site_dir)

    def want_card(name, markup):
        """A card is due when what it says has changed, or it is not there.

        Not when its page changed: a page carries a stylesheet and a card does
        not, so an edit to one rewrites all 169 pages and should redraw none of
        the cards. The second half keeps the pair self-healing -- a run that
        died before drawing, or a directory deleted by hand, is put right on the
        next build rather than leaving pages pointing at previews that do not
        exist.
        """
        if not exe:
            return False
        if card_print(markup) == prints.get(name) and os.path.isfile(
                os.path.join(site_dir, CARD_DIR, "%s.png" % name)):
            return False
        jobs.append((name, markup))
        return True

    songs = archived_songs(site_dir)
    have_dates = {r["date"] for r in known}
    calendar = load_calendar(site_dir)
    counting = set(calendar)
    on_phishin = phishin_dates(site_dir) or None
    rebuilt = 0
    live_now = [r["date"] for r in known if r.get("provisional")]
    if live_now:
        log("%d show(s) still coming in: %s", len(live_now), ", ".join(live_now))
    for report in known:
        date = report["date"]
        if not (rebuild or date in stale):
            continue
        page, _ = site_paths(site_dir, date)
        prev, nxt = around.get(date, (None, None))
        if write_if_changed(page, render_html(
                report, bar_scale=bar_scale, index_href="../index.html",
                prev_date=prev, next_date=nxt, songs=songs,
                card=date, archived_show=have_dates,
                sheet="../fonts.css", calendar=calendar,
                on_phishin=on_phishin)):
            if date in fresh:
                log("wrote %s", page)
            else:
                rebuilt += 1
        # Provisional shows included -- see report_card, where the in-progress
        # card is built from only the facts that will not move, so its hash
        # holds still and it is drawn once rather than every five minutes.
        want_card(date, report_card(report))

    # Song pages last, so they can link to whichever reports now exist. They
    # are cheap to write and the archive is the only input, so a rebuild does
    # the lot; otherwise only the songs this run touched.
    have = archived_dates(site_dir)
    played = {s["slug"] for r in reports for s in r["songs"]}
    wrote, considered, docs = 0, 0, []
    for slug in sorted(archived_songs(site_dir)):
        doc = song_history(site_dir, slug)
        if not doc or not doc.get("performances"):
            continue
        docs.append(doc)
        if not (rebuild or slug in played):
            continue
        considered += 1
        page = os.path.join(site_dir, "song", "%s.html" % slug)
        name = "song-%s" % slug
        moved = write_if_changed(page, render_song(doc, archived=have,
                                                   card=name, counting=counting))
        wrote += 1 if moved else 0
        want_card(name, song_card(doc))
    if considered:
        log("song pages: %d rendered, %d changed",
            considered, wrote)

    if docs:
        songs_page = os.path.join(site_dir, "songs.html")
        moved = write_if_changed(songs_page, render_songs(docs, card="songs"))
        if moved:
            log("wrote %s (%d songs)", songs_page, len(docs))
        want_card("songs", songs_card(docs))

    if rebuilt:
        log("re-rendered %d unchanged-content page(s) after a template change",
            rebuilt)
    write_redirects(site_dir)
    write_if_changed(os.path.join(site_dir, "fonts.css"), FONTS_CSS)
    write_grain(site_dir)
    # Regenerated every publish, because every publish would otherwise remove
    # it. Never deleted when DOMAIN is empty: an unset variable in one
    # environment is not an instruction to unpublish the domain in all of them,
    # which is exactly the mistake this file exists to survive.
    if DOMAIN:
        write_if_changed(os.path.join(site_dir, "CNAME"), DOMAIN + "\n")
    # Rewritten every run, but it is one small file and write_if_changed means
    # a run that moved nothing publishes nothing.
    write_current(site_dir)
    if _UNREADABLE:
        log("warning: %d archived report(s) could not be read and are missing "
            "from this build: %s", len(_UNREADABLE),
            ", ".join(sorted(set(_UNREADABLE))[:5]))

    # After write_current, because it reads what that just wrote.
    since = {}
    cur_path = os.path.join(site_dir, "data", "current.json")
    if os.path.isfile(cur_path):
        try:
            with open(cur_path, encoding="utf-8") as fh:
                since = json.load(fh).get("since") or {}
        except ValueError:
            pass
    if docs and since:
        due_page = os.path.join(site_dir, "due.html")
        if write_if_changed(due_page, render_due(docs, counting, since,
                                                 card="due")):
            log("wrote %s", due_page)
        want_card("due", due_card(docs, counting, since))

    method = os.path.join(site_dir, "method.html")
    if write_if_changed(method, render_method()):
        log("wrote %s", method)

    index = os.path.join(site_dir, "index.html")
    # Nine of the archive's entries are soundchecks or TV and radio sessions,
    # which phish.net does not count toward a gap. Keeping them in the list
    # meant the index counted 259 shows the band had not played 259 of, and
    # opened on a 2020 Moon Palace soundcheck.
    shows, aside = split_archive(known, load_calendar(site_dir))
    changed = write_if_changed(
        index, render_index(shows, card="index", aside=aside))
    want_card("index", index_card(shows))
    if jobs:
        made = shoot_cards(exe, jobs, site_dir)
        log("preview cards: %d of %d drawn", made, len(jobs))
        # Only what was actually drawn, so a batch that died partway is
        # retried next run rather than recorded as done.
        for name, markup in jobs[:made]:
            prints[name] = card_print(markup)
        save_card_prints(site_dir, prints)
    # Serve the directory verbatim on GitHub Pages, Jekyll out of the way.
    open(os.path.join(site_dir, ".nojekyll"), "a").close()
    log("%s %s (%d report%s)",
        "wrote" if changed else "unchanged", index, len(known), "" if len(known) == 1 else "s")
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
    ap.add_argument("--apikey", help="overrides PL_PHISHNET_API_KEY")
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
    ap.add_argument("--seed-songs", action="store_true",
                    help="with --site, fetch a performance history for every "
                         "song the archive already names (one call per song, "
                         "skipping songs already held)")
    ap.add_argument("--sweep-ratings", nargs="?", type=int,
                    const=RATING_CHASE_DAYS, metavar="DAYS",
                    help="with --site, re-ask fouldomain about archived shows "
                         "from the last DAYS (default %d) that still have no "
                         "rating; one call per show and none to phish.net"
                         % RATING_CHASE_DAYS)
    ap.add_argument("--seed-setlists", action="store_true",
                    help="with --site, fetch the full setlist of every show in "
                         "the archive to record what each performance followed "
                         "and led into (one call per show, resumable)")
    ap.add_argument("--seed-scores", action="store_true",
                    help="with --site, fetch fouldomain's top-rated versions "
                         "for archived songs that have none yet; --force "
                         "re-asks for every song")
    ap.add_argument("--remeasure", action="store_true",
                    help="with --site, recompute gaps, verdicts and previous "
                         "performances for every archived report from the "
                         "stored song histories (no API calls)")
    ap.add_argument("--watching", action="store_true",
                    help="with --site, print watching=true when a scheduled "
                         "show is inside its watch window and watching=false "
                         "otherwise, then exit (no API calls)")
    ap.add_argument("--phishin", action="store_true",
                    help="with --site, refresh the list of shows phish.in has "
                         "audio for, so links to them are only shown when they "
                         "will resolve (three calls, no key)")
    ap.add_argument("--schedule", action="store_true",
                    help="with --site, refresh the list of announced shows "
                         "that have not happened yet, with each venue's time "
                         "zone (two API calls)")
    ap.add_argument("--calendar", nargs="?", type=int, const=0, metavar="FROM",
                    help="with --site, refresh the show calendar that gap "
                         "counts are measured against, from year FROM to now "
                         "(default: the current year only; one call per year)")
    ap.add_argument("--catch-up", nargs="?", type=int, const=21, metavar="DAYS",
                    help="with --site, add every show played in the last DAYS "
                         "(default 21) that the site does not have yet, and "
                         "re-fetch any it is still holding as provisional")
    ap.add_argument("--recheck", nargs="?", type=int, const=RECHECK_DAYS,
                    metavar="DAYS",
                    help="with --catch-up, also re-fetch settled shows from "
                         "the last DAYS (default %d) to pick up corrections"
                         % RECHECK_DAYS)
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
    if (args.rebuild or args.force or args.catch_up or args.seed_songs
            or args.seed_scores or args.seed_setlists or args.sweep_ratings
            or args.calendar is not None or args.schedule
            or args.remeasure or args.phishin) and not args.site:
        sys.exit("error: --rebuild, --force, --catch-up, --seed-songs, "
                 "--seed-scores, --seed-setlists, --sweep-ratings and "
                 "--calendar need --site DIR")
    if args.site:
        jobs = [n for n, on in (
            ("catch-up %s days" % args.catch_up, args.catch_up),
            ("recheck", args.recheck), ("previous", args.previous),
            ("rebuild", args.rebuild), ("sweep-ratings", args.sweep_ratings),
            ("calendar", args.calendar is not None), ("schedule", args.schedule),
            ("remeasure", args.remeasure), ("seed-songs", args.seed_songs),
            ("seed-scores", args.seed_scores),
            ("seed-setlists", args.seed_setlists)) if on]
        if jobs and not args.watching:
            log("run starting: %s", ", ".join(jobs))
            check_env()

    if args.watching:
        if not args.site:
            sys.exit("error: --watching needs --site DIR")
        live = watching(args.site)
        for s in live:
            w = watch_window(s)
            log("show in progress: %s %s (%s) -- window %s to %s UTC",
                s["date"], s["venue"], s["tz"],
                w[0].strftime("%H:%M"), w[1].strftime("%H:%M"))
        if not live:
            nxt = next_show(args.site)
            log("nothing playing%s", " -- next is %s %s" % (nxt["date"], nxt["venue"])
                if nxt else "")
        # stdout stays machine-readable: a workflow reads this one line. Named
        # for what it actually reports -- whether a scheduled show is inside
        # its watch window right now -- and not for what a caller might do
        # about it, which is the caller's question and has other answers.
        print("watching=%s" % ("true" if live else "false"))
        return
    if args.recheck and not args.catch_up:
        sys.exit("error: --recheck only means something with --catch-up")
    if not (args.showdate or args.from_json or args.rebuild or args.catch_up
            or args.seed_songs or args.seed_scores or args.seed_setlists
            or args.sweep_ratings or args.calendar is not None
            or args.schedule or args.remeasure or args.phishin):
        sys.exit("error: give at least one show date (YYYY-MM-DD)")
    if args.html and args.pdf and \
            os.path.abspath(args.html) == os.path.abspath(args.pdf):
        sys.exit("error: --html and --pdf point at the same file")

    reports, key, dates, recheck = [], None, list(args.showdate), set()
    kw = {"cache_dir": args.cache_dir, "refresh": args.refresh}
    try:
        if args.catch_up:
            key = load_key(args.apikey)
            played = recent_shows(key, args.catch_up, artist=args.artist, **kw)
            have = {} if args.force else {r["date"]: r
                                          for r in saved_reports(args.site)}
            # Anything still unsettled is re-fetched every run, however often
            # that is; settled shows only when --recheck asks for corrections.
            recheck = {d for d in played if (have.get(d) or {}).get("provisional")}
            if args.recheck:
                cutoff = (_utcnow().date()
                          - datetime.timedelta(days=args.recheck)).isoformat()
                recheck |= {d for d in played if d >= cutoff and d in have}
            fresh = [d for d in played
                     if (d not in have or d in recheck) and d not in dates]
            log("catch-up: %d show%s played in the last %d days, " "%d new, %d re-fetched",
                len(played), "" if len(played) == 1 else "s", args.catch_up, len(fresh) - len(recheck), len(recheck))
            dates += fresh

        if args.from_json:
            with open(args.from_json, encoding="utf-8") as fh:
                reports.append(json.load(fh))
        for date in dates:
            if args.site and not args.force and date not in recheck:
                _, blob = site_paths(args.site, date)
                if os.path.exists(blob):
                    log("%s is already in the site (--force to re-fetch)", date)
                    continue
            key = key or load_key(args.apikey)   # not needed for --rebuild
            # A show being re-fetched is one that is still changing, so its
            # setlist must not come from the cache. The cache holds a response
            # for six hours and a watch job runs for five, so without this the
            # first pass froze the setlist and every pass after it republished
            # that same copy -- the watcher reporting 13 songs while phish.net
            # had 16, unable to ever see another. Only this call bypasses it;
            # song histories and the calendar stay cached, which is most of the
            # traffic and none of the volatility.
            live = dict(kw, refresh=True) if date in recheck else kw
            try:
                report = build(date, key, artist=args.artist, **live)
            except ApiError as exc:
                # A tour-length run should not die on tonight's show having no
                # setlist posted yet.
                if not args.site:
                    raise
                log("skipping %s: %s", date, exc)
                continue
            if args.previous:
                add_previous(report, key, site_dir=args.site, **kw)
            if args.site or args.html or args.pdf:
                add_ratings(report, **kw)
            # After add_previous, not before: the comparison counts how many
            # songs know their history, which is only true once it has run.
            prior = archived(args.site, date) if args.site else None
            if not is_fuller(report, prior):
                continue
            if args.site:
                settle(report, prior, _utcnow())
            reports.append(report)

        if args.seed_songs:
            # After the fetch loop, so anything new tonight is already archived
            # by add_previous and does not get asked for twice.
            key = key or load_key(args.apikey)
            seed_songs(args.site, key, artist=args.artist, force=args.force,
                       **kw)
        if args.sweep_ratings:
            sweep_ratings(args.site, days=args.sweep_ratings, **kw)
        if args.seed_setlists:
            key = key or load_key(args.apikey)
            seed_setlists(args.site, key, artist=args.artist,
                          force=args.force, **kw)
        if args.seed_songs or args.seed_scores:
            seed_scores(args.site,
                        songs=sorted(archived_songs(args.site))
                        if args.force and args.seed_scores else None, **kw)
        if args.remeasure:
            remeasure(args.site, artist=args.artist)
        if args.phishin:
            fetch_phishin(args.site, **kw)
        if args.schedule:
            key = key or load_key(args.apikey)
            fetch_schedule(args.site, key, artist=args.artist, **kw)
        if args.calendar is not None:
            # The current year alone on a scheduled run: earlier years cannot
            # gain shows, and a year that gains a correction is rare enough to
            # ask for by hand.
            key = key or load_key(args.apikey)
            first = args.calendar or _utcnow().date().year
            fetch_calendar(args.site, key, range(first, _utcnow().date().year + 1),
                           artist=args.artist, **kw)
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
        # No stylesheet beside a single file, so it carries the face itself.
        markup = render_html(report, bar_scale=args.bar_scale, sheet=None)
        if args.html:
            with open(args.html, "w", encoding="utf-8") as fh:
                fh.write(markup)
            log("wrote %s", args.html)
        if args.pdf:
            try:
                used = write_pdf(markup, args.pdf, prefer=args.pdf_backend,
                                 single_page=args.single_page)
            except ApiError as exc:
                sys.exit("error: %s" % exc)
            log("wrote %s (via %s)", args.pdf, used)
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2)
        log("wrote %s", args.json)


if __name__ == "__main__":
    main()