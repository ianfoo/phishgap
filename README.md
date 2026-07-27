# possumlogic

Per-song **gap** reports for Phish shows: how many shows passed between each
song at a given concert and the last time the band played it. A gap of 4 is a
regular in rotation; a gap of 1,170 is a bustout worth shouting about.

Data comes from the [Phish.net API v5](https://docs.phish.net/), which returns
each song's gap already computed, so there is no scraping and no arithmetic.

Reports are published at
**[ianfoo.github.io/phishgap](https://ianfoo.github.io/phishgap/)**.

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

Each show lands in `site/<date>.html`, its data is archived in
`site/data/<date>.json`, and `site/index.html` is regenerated from that archive
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
expose it. `--seed-setlists` is the expensive one: a song's history says where it
was played but not what came before it, so this fetches the full setlist of every
show in the archive, about two thousand calls the first time and none after, since
a new show's setlist is fetched anyway. It writes in batches and records what it
has done in `site/data/neighbours.json`, so an interrupted run picks up where it
stopped.

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

### Single files

```sh
./possumlogic.py 2026-07-24 --previous --html report.html --pdf report.pdf
```

`--pdf` wants [WeasyPrint](https://weasyprint.org/) (`pip install weasyprint`)
and falls back to the `weasyprint` CLI, then to headless Chrome. `--single-page`
emits one continuous page instead of paginating for letter paper.

Pages inline everything they can — CSS, favicons, the lot — so a file handed to
someone in a chat still renders offline. Web fonts are the exception: they need
the network, and fall back to Georgia and the system monospace without it.

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
