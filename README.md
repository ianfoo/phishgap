# possumlogic

A browsable archive of Phish performances, published at
**[possumlogic.com](https://possumlogic.com/)**.

Every show since the 2009 Hampton reunion has a page: what was played, what each
song went into, how long since the band last played it, and how that compares to
how often they usually play it. Every song has a page too — every performance of
it, oldest to newest, with its debut, its longest absence, and where the best
recorded version is.

The **gap** is the spine of it: how many shows passed between one performance of
a song and the one before. A gap of 4 is a regular in rotation; 1,468 is Cold as
Ice returning in 2026 after last being played in 1992. Gaps come from the
[Phish.net API v5](https://docs.phish.net/) already computed, so there is no
scraping and no arithmetic — but which shows *count* toward one is a judgement,
and the site follows phish.net's own `exclude_from_stats` flag rather than
inventing a rule. Soundchecks and television sessions are on file and say so.

Ratings and best-version links come from
[fouldomain](https://fouldomain.com/); listening links point at
[phish.in](https://phish.in/). A show still being played publishes while it is
being played, and says so.

Everything is static. There is no server, no database and no build pipeline —
one Python script writes the whole site from a JSON archive it also maintains,
and GitHub Pages serves it.

## Usage

Get a key at [phish.net/api](https://phish.net/api), then put it anywhere the
script looks — `PL_PHISHNET_API_KEY` (or plain `PHISHNET_API_KEY`), `--apikey`,
or `~/.config/possumlogic/keys.json`,
which holds one key per service so each says which API it belongs to:
`{"phish.net": "..."}`. The older `~/.config/phishgap/apikey` is still read.

A single show, as text on stdout:

```sh
./possumlogic.py 2026-07-24
```

Add `--previous` for each song's prior performance — date, venue, city. It costs
one API call per song, which is why it is opt-in.

### A growing site

```sh
./possumlogic.py 2026-07-22 2026-07-24 --previous --site site
```

Each show lands in `site/show/<date>.html`, its data is archived in
`site/data/shows/<date>.json`, and `site/index.html` is regenerated from that archive
with search, per-year filters, and sorting. Dates the site already has are
skipped unless `--force`, so runs are additive.

### Song pages

Every song in a report links to its own page at `site/song/<slug>.html`: every
Phish performance of it newest first, with search, sorting, and the song's gap
history drawn against its own longest. The archive for those lives in
`site/data/songs/<slug>.json`, and it is nearly free — `--previous` already
fetches each song's complete history to find its previous performance, then
threw the rest away.

Three passes fill in what a single show's fetch cannot know. Each is skippable,
resumable, and only asks for what it does not already hold:

```sh
./possumlogic.py --site site --seed-songs      # a history per song the archive names
./possumlogic.py --site site --seed-scores     # fouldomain's top-rated versions
./possumlogic.py --site site --seed-setlists   # what each performance followed
```

`--seed-songs` costs one call per song. `--seed-scores` fetches [fouldomain's](https://fouldomain.com/)
ratings, which also carry phish.net's own show rating — phish.net's API does not
expose it. `--seed-setlists` fills in what each performance followed and led
into: a song's history says where it was played but not what stood next to it,
which needs the whole setlist of every show in the archive.

It used to be the expensive one. Now it walks `archive/setlist-order.json` — the
running order of every show already fetched — and buys only the dates that file
is missing, so re-walking all 2,008 shows after a rule change costs nothing and
needs no API key. Each show is marked on its own rows as it is walked, so an
interrupted run picks up where it stopped, and `--catch-up` records a new show's
neighbours as it fetches it. `--force` re-walks everything.

Ratings and jam charts arrive late — a version is scored from audio analysis, so
it has none until a recording circulates, and jam chart entries are curated
months afterwards. Both are treated as optional everywhere they appear.

Rather than naming dates, let it find them:

```sh
./possumlogic.py --site site --previous --catch-up      # shows played in the last 21 days
./possumlogic.py --site site --previous --catch-up 400  # or a whole year of them
```

A show is held back until its setlist stops growing. Nothing in the API says
whether a setlist is finished — there is no show time to reason from, the show
record's `updated_at` lags by days, and the format is not promised: a
rained-out show can stop mid-second-set with no encore, so counting sets proves
nothing. So stability stands in for completeness. A song count that has not
moved for `QUIET_HOURS` is taken for the whole show; until then the report is
archived as `provisional` and kept off the site, because a half-entered setlist
would publish wrong totals. The window is sized to clear the longest gap
between two songs being entered — a 45-minute jam, or a setbreak, plus the lag
of whoever is typing. If stability never settles, a backstop publishes anyway
once no show that night could still be running anywhere in North America.

`--catch-up` re-fetches provisional shows every run, however often you run it.
Corrections to shows that already settled arrive with `--recheck`:

```sh
./possumlogic.py --site site --previous --catch-up --recheck
```

Because the archive holds every report, re-rendering after a style change costs
nothing and touches no API:

```sh
./possumlogic.py --site site --rebuild
```

Two checks answer questions about the built site that are otherwise settled by
reading it, which has been wrong both ways — a working link reported broken, and
a broken one reported fine:

```sh
python3 tools/check_links.py
```

Walks all 1,310 built pages and fails on a link to a missing file, a fragment no
element carries, or an id repeated within a page.

```sh
python3 tools/check_few_plays.py
```

Fails if the words on the out-of-rotation page stop tracking `FEW_PLAYS`, the
constant that decides how few performances counts as never having got going.

### Single files

```sh
./possumlogic.py 2026-07-24 --previous --html report.html --pdf report.pdf
```

`--pdf` wants [WeasyPrint](https://weasyprint.org/) (`pip install weasyprint`)
and falls back to the `weasyprint` CLI, then to headless Chrome. `--single-page`
emits one continuous page instead of paginating for letter paper.

The file is one document — CSS, scripts, the favicon and the three source
badges are inlined. It is not self-contained: three references to Google's font
hosts fetch IBM Plex Mono and Literata. Since `body` is Plex Mono site-wide,
essentially every word depends on the network; offline the page falls back to
the system monospace and Georgia. The display face is inlined as a 13 KB
`data:font/otf` only for a show still being played, which is the one page here
with a rule that asks for it — a settled show is 17 KB lighter for it. There is
no paper grain either: the grain lives in `fonts.css`, and this path emits the
inline face instead of the sheet.

## Publishing

GitHub Pages serves the `gh-pages` branch root. `main` tracks the script and the
JSON archive; the generated pages live only on `gh-pages`.

```sh
./possumlogic.py --site site --previous --catch-up   # build
./publish.sh                                      # push site/ to gh-pages
```

`.github/workflows/gap-reports.yml` does the same thing on a schedule: hourly
through the window a show can be settling in, plus a once-a-day pass that also
re-checks recent shows for corrections. On a day with no show it finds nothing
and publishes nothing. It needs one repository secret, `PHISHNET_API_KEY`, which it passes to the
script as `PL_PHISHNET_API_KEY`. Everything this program reads from the
environment is prefixed `PL_`; set `PL_GOATCOUNTER` as a repository variable
to turn on analytics. Each falls back to its unprefixed name, and every run
logs which variable it actually read — so a mistyped prefix cannot quietly
fall through to a stale unprefixed value without saying so.
Pushing a change to `possumlogic.py` also triggers it, so a template edit
republishes every page.

Song pages are the bulk of the built site — one per song rather than one per
show — so a template edit rewrites all of them at once. Worth knowing before
changing something every page shares.

## Notes

API responses are cached under `~/.cache/possumlogic` for six hours (the old `~/.cache/phishgap` is
still used if it is the one that exists), because
phish.net asks that clients cache rather than re-request; `--refresh` bypasses
it. Live requests are spaced out and back off on HTTP 429, which a tour-length
run with `--previous` will otherwise earn.
