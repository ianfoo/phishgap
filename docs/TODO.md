# Outstanding work

**Read §3b before deciding what to work on.** It holds the work agreed with Ian
*before* the two design reviews arrived, which a mid-session rewrite of this
file dropped. It is not lower priority than the review findings; it is older.


Written 2026-07-28 during the first live-show test. Ordered by the sequence
agreed with Ian. Anything marked **[ruling]** is a decision I made without him
so work could continue; he wants to review these, not be blocked by them.

## Context a new session needs

- The tool is `possumlogic.py`. Site publishes to <https://possumlogic.com>
  from `gh-pages`; `./publish.sh` publishes by hand, `.github/workflows/`
  has `possumlogic.yml` (thorough, ~hourly) and `watch.yml` (resident poller
  during a show, 5-minute passes, restarted four times an hour at odd
  minutes — see §8.4 for why not on the half hour).
- Every run's output goes through `log()` and is timestamped. Config is read
  from `PL_*` env vars falling back to unprefixed names; `check_env()` warns
  about near-miss names.
- Verify claims before acting on them. Two independent reviews were run and
  both contained confident assertions that were wrong on inspection (e.g.
  `.ax-*` called dead CSS when it is live on the index). Measure first.
- Never claim something is done without rendering it. Counting elements in
  HTML proves markup exists, not that it is styled or visible.
- **Report from observation, not from intent.** The recurring failure in this
  project has not been bad code, it has been saying a thing was done because it
  had been typed. Instances in one night: song pages were twice reported as
  carrying a treatment whose CSS was never added; code was pushed without
  compiling; an item was reported as added to this file and was not. The check
  is always the same and always cheap — look at the artifact the reader gets.
- Verify the *published* thing, not the local one. The live site and a local
  build disagreed for over an hour tonight and every local check passed.
- **Carry the whole backlog forward, not the most recent conversation.** This
  file was written mid-session and captured only what was being discussed at
  that moment; a batch of work Ian had asked for earlier was silently dropped
  and he had to notice it was gone. Anything he has asked for stays here until
  he says otherwise, whether or not it is what is currently being worked on.
  §3b exists because of that failure.
- GitHub Pages adds 60–90 seconds of deployment lag after each publish, on top
  of the polling interval. It is a floor on how live the live show can be and
  is not a bug to chase.

## 1. ~~Song page enrichment — preceded by / followed by~~ DONE 2026-07-28

Every song page row already prints what the performance came out of and went
into (`prev`/`next`/`in`/`out` in `site/data/songs/<slug>.json`). Nothing
aggregates it. Tweezer alone has 418 pairings.

Add to the song page: the songs that most often precede and follow this one,
with counts. Audience asks this constantly.

## 2. ~~"Due" page~~ DONE 2026-07-28 — `due.html`, 55 due, 274 dormant excluded

`site/data/current.json` already ships `since` (shows since last played) for
every song, and each song page carries `data-high` (85th percentile) and
`data-bustout`. A ranked "what is overdue going into tonight" page is the most
shareable thing the site could publish.

**Dormant songs must be excluded.** A song with no recent norm that has been
gone 250 shows is not *due* — nobody expects it. Only songs with a real
percentile (>= 8 plays in the ten-year window) that are past it count as due.

## 3. Index hero and a loud in-progress banner — DONE 2026-07-28

- ~~Hero cards~~ DONE: six of them, 3×2. `LONGEST GAP` links to the show
  holding it (2026-07-22, Cold as Ice, 1,468 — checked against a scan of the
  raw archive, not against the page that renders it). New `MOST SONGS` links
  to the fullest night (45, 2011-07-02). `VENUES` links to the new venues
  page; `SONGS DUE` links to `due.html`. Three of the six now carry the `→`.
- The hero is a grid rather than a wrapping flex row. Six cards wrap, and a
  wrapped flex row gave the first card of row two a left rule separating it
  from the *page margin* and indenting its number out of line with the
  wordmark. Row-starts are now a column position, so that artifact is
  impossible rather than moved. Column count comes from the card count
  (`hero_cols()`), so it cannot disagree with what is in the hero.
- Watch for this: the narrow layout already had its own two-column rules. The
  first attempt restated them at the wide breakpoint too and outranked them,
  which left card 4 of six indented half a space out of line. Each width
  states its own row-starts now and neither undoes the other.
- A show in progress should be loud on the index, not just a `so far` tag.
- ~~**Encore detection**~~ DONE: `ENCORE_QUIET` = 30 min once any set
  starting `e` has landed; 2 hours otherwise. Verified: 40 min with no encore
  stays live, 35 min after one settles.
- ~~On-stage banner on the index~~ DONE: links straight through.
- Original note on encore detection the "in progress" lie. Once a set marked
  `e` (or `e2`/`e3`) has landed *and* the count has been still ~30 min, stop
  claiming in progress and say "just ended". Set labels are in each song's
  `set` field. Ian accepts a ~30-minute lie window for now; tightening it
  further needs an external signal and is explicitly out of scope.

## 3b. Work agreed before the reviews — do not lose this again

These predate the UX and visual reviews and were discussed with Ian directly.
They are not review findings and none of them has been started.

### Rename "reports"

The site stopped being a gap calculator and the vocabulary did not follow.
"Reports" survives in: the index hero card label and subtitle, `--catch-up`'s
output, `publish.sh`'s tally, `SHOW_DIR`, `saved_reports()`, `REPORT_NAME`,
`report_card()`, `render_html`'s docstrings, and the pager's aria-labels. Pick
the replacement once and change it in one pass — a half-renamed vocabulary is
worse than the old one. Ian raised this; it is not cosmetic to him.

### More charts on show and song pages

Ian's words: "some cool stats… like song era distribution and debut years for
songs", explicitly inspired by what phish.net and fouldomain publish, with the
goal of making the archive rewarding to explore rather than merely correct.
Everything needed is already in the archive:

- **Era distribution of a show's setlist** — how much of tonight came from 1.0,
  2.0, 3.0, 4.0. `era()` already exists and every song has a debut date.
- **Debut-year spread** — the oldest and newest song played, and the shape
  between them. A show that opens with a 1988 song and closes with a 2024 one
  is a different night from one drawn entirely from *Sigma Oasis*.
- Ian was clear this is about delight, not completeness. Do not turn it into a
  dashboard.

### Bagnard alternatives specimen — ASKED FOR AND NEVER DELIVERED

Ian asked for a specimen of display-face alternatives: "I'd be game to look at
a specimen for Bagnard alternatives. I want something that has style and
personality." It was promised and never built. The visual review has since
narrowed the brief usefully — the masthead date has moved to Plex Mono, so a
replacement only has to set the wordmark, song titles and method headings,
which are words. Candidates the reviewer named, with the checks to run before
committing to any of them: `'GSUB' in TTFont(f)`, the digit-advance spread from
`hmtx`, and U+0027 in the cmap.

- **Fraunces** (OFL, variable; `SOFT` and `WONK` axes)
- **Instrument Serif** (OFL; more poster, verify the digits)
- **Redaction** (OFL; ships in halftone grades, conceptually close to the
  ephemera direction, riskiest)

Bagnard is not bad — the reviewer measured the method page as the best-typeset
page on the site and Bagnard sets its headings. The open question is only
whether something with more personality would serve the wordmark better.

### Video enrichment — filed, not started

GitHub issues #1 (show pages) and #2 (song pages). Official Phish YouTube and
The Pharchive post a day or two after a show; titles carry date and song name
but not phish.net slugs, so matching is fuzzy and must decline rather than
guess. Needs a YouTube Data API key and its own sweep pass, like ratings. The
config already supports per-service keys.

### Config reporting is still too coarse

Ian: "'config from environment' feels broad… what if two values are env vars,
and one is a command line switch, or API key from a file?" It currently prints
one line naming the sources collectively. It should name each setting and where
that setting came from, so a mixed setup reads correctly.

### Backfill further back

The archive starts at the 2009 Hampton reunion. Ian has said repeatedly he
wants to keep going back; 1.0 alone is ~1,360 shows. **Do the DOM work in §5
first** — the index is already 664 KB at 690 shows. Note that song pages are
already at full scale and do not grow: backfilling converts 271 outbound
phish.net links on Tweezer's page into internal ones and adds no rows.

### Year and tour pages for scale

Ian's stated preference, from before the reviews: **years as the browse spine,
tours as context**. The UX review argues against building page trees and for
URL-addressable search instead (§4). These are not the same answer and Ian's
preference predates the review — his call, not the reviewer's.

### Smaller items from the original backlog

- **Song page breakpoint is 820px**; every other page breaks at 620px. Ian
  asked for this to match.
- **`songs.html` accent thresholding** — roughly 750 orange numerals across
  587 rows, which spends the accent colour on everything and therefore on
  nothing.
- **`method.html` carries INDEX_CSS wholesale**, of which the great majority is
  unused. Strip it.
- **Mexico start times.** phish.net has no start time and setlist.fm exposes it
  only on the page, not the API, so it is not scraped. The Mexico runs are the
  standing exception — night 1 late, middle nights early, last night earliest —
  and the watch window is currently widened to cover all of them rather than
  encoding which night is which. Revisit only if the window proves too wide.
- **The `--html` single-file output must stay self-contained.** The hosted site
  dropped that requirement and uses `fonts.css`; the single file still inlines
  the face, because that one is meant to survive being handed to somebody with
  nothing beside it. Do not "simplify" it into the shared sheet.

## 4. Navigation

- ~~**URL state for search**~~ DONE 2026-07-28. `?q=&era=&sort=` on the index,
  read on load and on `popstate`, written on every change. Verified in a
  browser both ways: a pasted link restores all three, and back steps through
  them. 82 MSG shows and 171 Tweezer shows are now addressable.
  - **Typing replaces, it does not push.** One history entry per keystroke
    would take eight back-presses to leave a search you typed once. The era
    chips and the sort push, because each is one deliberate act. This is a
    deliberate departure from "pushState on input" as written above.
  - Unknown `era`/`sort` values are ignored rather than applied, so a
    hand-edited URL cannot hide all 691 rows with no lit chip to click off.
    The bare index keeps a bare URL.
  - **Quoted phrases**: `"Key Arena"` matches the phrase, unquoted matches
    loose ANDed words. This exists because the venue links needed it — see
    below.
- ~~**[ruling]** Build real venue pages only for per-venue statistics~~ DONE:
  `venues.html`, one page, 153 venues ranked by nights with span and longest
  gap. No page tree — each row links to `index.html?q="<venue>"`.
  - The rows had to be **quoted phrases**. Unquoted, 6 of 153 venues returned
    somebody else's shows: `Key Arena` matched 8 (any arena with a "key"
    anywhere in its setlist), and `The Wharf Amphitheater` and `Amphitheater
    at the Wharf` each answered for the other. Checked by replaying every
    venue's own link against the built haystack: 153 of 153 now return exactly
    their own shows. **Re-run that check if the matcher is ever touched.**
- Venue and tour on a show page are plain text; make them searches. Now cheap:
  link them to `index.html?q="<venue>"` the way `venues.html` does.
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

## 8. The watcher needs a real test before it is trusted again

Three separate bugs in one night, each of which made the live feature quietly
not work while looking like it did:

1. **It never refreshed the calendar.** A show only counts as a concert if the
   counting calendar holds its date, and that calendar comes from phish.net's
   show list — so the show being played was not in it, and landed under "Also
   on file" instead of at the top of the index.
2. **A conflicted `git pull --rebase` was swallowed by `|| true`**, writing
   conflict markers into `site/data/<date>.json`. That file is then unreadable
   JSON, the show drops out of the archive, and the watcher publishes a site
   *without the show it is watching* — every five minutes, over the top of
   correct publishes.
3. **It served the setlist from a six-hour cache.** A watch job runs five
   hours, so after its first pass it re-read the same response forever. The log
   said "1 re-fetched" every pass and meant it; the fetch happened and never
   left the disk. The song count only ever moved when some *other* run — the
   hourly workflow, or a manual dispatch — started on a fresh runner with an
   empty cache.

4. **Its schedule had never once fired.** `watch.yml` went on main at 00:30
   UTC with `cron: "*/30 22-23,0-9 * * *"`, which asks only for `:00` and
   `:30` — the two most contended minutes on the platform and the two GitHub
   is likeliest to drop. Six of those boundaries passed and every one was
   skipped: the workflow had three runs in its life, all `workflow_dispatch`.
   Meanwhile `possumlogic.yml`'s `*/5` got four `schedule` events in the same
   repository over the same hours, so scheduling itself was working fine.
   Fixed by asking for four odd minutes an hour (`3,18,33,48`) instead. The
   header already knew the schedule was throttled; what it missed is that
   *which* minutes you ask for decides whether you are throttled to less or
   throttled to nothing.

   This is why the site fell "several songs behind" during a show even after
   bug 3 was fixed — with no watcher ever started, the only thing updating the
   page was the ordinary hourly workflow, itself throttled to roughly one run
   in forty minutes. The archive was never wrong, only slow. **Confirm a
   `schedule` event actually appears in `gh run list --workflow=watch.yml`
   before believing the watcher is live.**

All four are fixed. The point is that they existed at once, each invisible
from the logs, and tonight is unlikely to have found the last.

### Two more, in the page rather than the job

Both were single-line and both made a live feature render as if it had never
been written:

- **`AGO_JS` and `NEW_ROWS_JS` ship in `<head>`** and ran before the body they
  query existed, so both returned immediately, every time. The "last checked"
  stamp had therefore been showing its no-JavaScript fallback — a bare `03:41`
  UTC clock reading — on every live page since it was written, which is what
  Ian saw. Both are wrapped in a `readyState`/`DOMContentLoaded` guard now.
  Verified in a browser: the stamp reads "just now" and reranks on its timer.
- **`NEW_ROWS_JS` bakes the song count into its `localStorage` key.** The key
  is derived from `document.title`, which begins `(16) 2026-07-27 …`, so
  stripping non-digits yields `162026-07-27` → `pl-seen-162026-07-`. Every new
  song mints a *new* key, `seen` reads 0, and "N new since you last looked"
  can never fire — it also leaves a key per song count behind. **Not fixed
  here**, because it is another session's in-flight feature: the key wants to
  come from the show date alone, not from the title.

**Write an end-to-end test before adding anything else to the watcher.** Drive
`write_site` against a synthetic show whose setlist grows across passes, and
assert the *published* page changes — not that a function was called, not that
markup contains a class. The bugs above all pass any test that stops short of
reading the output.

## 9. Known and deliberately not fixed

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
