# Outstanding work

Written 2026-07-28 during the first live-show test. Ordered by the sequence
agreed with Ian. Anything marked **[ruling]** is a decision I made without him
so work could continue; he wants to review these, not be blocked by them.

## Context a new session needs

- The tool is `possumlogic.py`. Site publishes to <https://possumlogic.com>
  from `gh-pages`; `./publish.sh` publishes by hand, `.github/workflows/`
  has `possumlogic.yml` (thorough, ~hourly) and `watch.yml` (resident poller
  during a show, 5-minute passes, restarted half-hourly).
- Every run's output goes through `log()` and is timestamped. Config is read
  from `PL_*` env vars falling back to unprefixed names; `check_env()` warns
  about near-miss names.
- Verify claims before acting on them. Two independent reviews were run and
  both contained confident assertions that were wrong on inspection (e.g.
  `.ax-*` called dead CSS when it is live on the index). Measure first.
- Never claim something is done without rendering it. Counting elements in
  HTML proves markup exists, not that it is styled or visible.

## 1. Song page enrichment — preceded by / followed by

Every song page row already prints what the performance came out of and went
into (`prev`/`next`/`in`/`out` in `site/data/songs/<slug>.json`). Nothing
aggregates it. Tweezer alone has 418 pairings.

Add to the song page: the songs that most often precede and follow this one,
with counts. Audience asks this constantly.

## 2. "Due" page

`site/data/current.json` already ships `since` (shows since last played) for
every song, and each song page carries `data-high` (85th percentile) and
`data-bustout`. A ranked "what is overdue going into tonight" page is the most
shareable thing the site could publish.

**Dormant songs must be excluded.** A song with no recent norm that has been
gone 250 shows is not *due* — nobody expects it. Only songs with a real
percentile (>= 8 plays in the ten-year window) that are past it count as due.

## 3. Index hero and a loud in-progress banner

- Hero cards: more, and make the dead ones links. `VENUES 153` advertises a
  spine that does not exist; `LONGEST GAP` should link to the show holding it.
  `SONG PERFORMANCES` is already a link and shows the `→` affordance — copy it.
- A show in progress should be loud on the index, not just a `so far` tag.
- **Encore detection** to shorten the "in progress" lie. Once a set marked
  `e` (or `e2`/`e3`) has landed *and* the count has been still ~30 min, stop
  claiming in progress and say "just ended". Set labels are in each song's
  `set` field. Ian accepts a ~30-minute lie window for now; tightening it
  further needs an external signal and is explicitly out of scope.

## 4. Navigation

- **URL state for search** (`?q=&era=&sort=`), pushState on input, read on
  load. Highest-leverage item on the list: the index search already matches 81
  MSG shows, 33 shows in 2015, 171 Tweezer shows — none of it linkable.
- Venue and tour on a show page are plain text; make them searches.
- Bustout leaderboard (biggest gaps per performance, archive-wide).
- On this day. Random show. `sitemap.xml`, `robots.txt`, a feed — all 404.
- Song pages have no next/prev performance stepper; show pages do.
- **[ruling]** Do *not* build `/venue/` and `/year/` page trees. URL-addressable
  search gets the same result with no new build output and nothing to fall out
  of sync. Build real venue pages only for per-venue *statistics*.

## 5. DOM growth before the 1983 backfill

Measured at 690 shows: 664 KB HTML, 9,866 nodes. Straight-line to ~2,100
shows: ~1.9 MB, ~30,000 nodes. Matching is not the problem (0.65 ms per pass);
layout is — a filter pass with forced reflow is 22 ms at 690 and ~68 ms at
2,100, per keystroke.

In order: debounce input ~80 ms; filter by toggling a class on the container
rather than setting `hidden` on thousands of elements; only then consider
windowing. **Do not reach for a virtual list first** — it costs the printable,
Ctrl-F-able, no-JS-degradable property the list has now.

Also: the index has no era or year headings, while song pages already group by
era with counts and spans. Port that pattern; it gives scroll landmarks and
free anchors.

## 6. Remaining visual work

- `col.c-bar` 16% → 22%, taking it from `c-last`. The bar is 80px wide with a
  32px band; rows the numbers separate clearly sit 2px apart in the bar.
- Bustout rows draw a `track bare` ghost at ~1.3:1 contrast with no tooltip,
  so the most interesting rows have the emptiest graphic and hovering explains
  nothing. Draw nothing at all, and add a `data-tip` saying why.
- Dark-mode band is 5.29:1 against paper where light is 3.09:1 — same graphic,
  different weight per palette. Drop `.bar .band` opacity to ~.55 in dark.
- **Do not remove the 2px paper halo on `.at`.** Marker-against-band is
  1.25–1.87:1 in every combination; the halo is the only reason it reads.
- Cards have no grain and use a plain rule where pages use `.rule2`. The card
  and the page it opens do not feel like the same object.
- Card mark (the arc) at `opacity:.12` is invisible at thumbnail size.
- Header DOM order is `h1 → .where → .show` but the grid flips `.show` above
  `.where` at >= 700px, so reading order differs between narrow, wide and print.

## 7. Mobile and the method page

- Nav targets measure 37×17 at 375px against a 24×24 minimum (WCAG 2.5.8), and
  the two nav rows are 4.8px apart so the spacing exception does not apply.
  Fix with padding, not a hamburger — the small-caps text row is the right
  pattern for a reference archive with three destinations.
- Below 620px a tap in `td.last` goes to the previous show and a tap elsewhere
  goes to the song page, with only a 2px border to say so. Signal it.
- `td.n` carries an `aria-label` that *replaces* the cell contents for screen
  readers, dropping the figure, the median and the verdict. Use a
  visually-hidden span inside the cell instead.
- Method page: ordering is scattered (the bar is discussed mid-gap-calculation)
  and it needs a table of contents.

## 8. Known and deliberately not fixed

- GitHub Pages serves `cache-control: max-age=600` and cannot be configured,
  so the 2-minute meta refresh is served from cache four times in five. The
  real fix is to stop relying on the refresh and poll a small per-show JSON,
  patching rows in — the same pattern `current.json` already uses on song
  pages. **[ruling]** Worth doing, sequenced after the items above.
- The "in progress" state lies for up to ~30 minutes after the encore even
  with encore detection. Ian accepts this; tightening needs external signals.
- phish.net's gap is not reproducible from the show calendar — two songs
  spanning the same pair of shows can carry different gaps. The site computes
  its own "shows since" and says so. Do not try to match their number.
