# phishgap

Per-song **gap** reports for Phish shows: how many shows passed between each
song at a given concert and the last time the band played it. A gap of 4 is a
regular in rotation; a gap of 1,170 is a bustout worth shouting about.

Data comes from the [Phish.net API v5](https://docs.phish.net/), which returns
each song's gap already computed, so there is no scraping and no arithmetic.

Reports are published at
**[ianfoo.github.io/phishgap](https://ianfoo.github.io/phishgap/)**.

## Usage

Get a key at [phish.net/api](https://phish.net/api), then put it anywhere the
script looks — `PHISHNET_API_KEY`, `--apikey`, or `~/.config/phishgap/apikey`.

A single show, as text on stdout:

```sh
./phishgap.py 2026-07-24
```

Add `--previous` for each song's prior performance — date, venue, city. It costs
one API call per song, which is why it is opt-in.

### A growing site

```sh
./phishgap.py 2026-07-22 2026-07-24 --previous --site site
```

Each show lands in `site/<date>.html`, its data is archived in
`site/data/<date>.json`, and `site/index.html` is regenerated from that archive
with search, per-year filters, and sorting. Dates the site already has are
skipped unless `--force`, so runs are additive.

Rather than naming dates, let it find them:

```sh
./phishgap.py --site site --previous --catch-up      # shows played in the last 21 days
./phishgap.py --site site --previous --catch-up 400  # or a whole year of them
```

Because the archive holds every report, re-rendering after a style change costs
nothing and touches no API:

```sh
./phishgap.py --site site --rebuild
```

### Single files

```sh
./phishgap.py 2026-07-24 --previous --html report.html --pdf report.pdf
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
./phishgap.py --site site --previous --catch-up   # build
./publish.sh                                      # push site/ to gh-pages
```

`.github/workflows/gap-reports.yml` does the same thing on a schedule: once a
day it looks for shows the archive is missing, and on a day with no show it
finds nothing and publishes nothing. It needs one repository secret,
`PHISHNET_API_KEY`. Pushing a change to `phishgap.py` also triggers it, so a
template edit republishes every page.

## Notes

API responses are cached under `~/.cache/phishgap` for six hours, because
phish.net asks that clients cache rather than re-request; `--refresh` bypasses
it. Live requests are spaced out and back off on HTTP 429, which a tour-length
run with `--previous` will otherwise earn.
