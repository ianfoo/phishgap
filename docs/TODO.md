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

## 0. Where the 2026-07-28 session left off — read this first

**Everything below marked DONE is committed and pushed to `main`.** The site
rebuilds clean (`./possumlogic.py --site site --rebuild`, ~2 s) and
`python3 -m py_compile possumlogic.py` passes.

### In flight when the session ended

- **A watcher run is live**, dispatched on the fixed code (see §8.5). The
  previous run was cancelled because it was pinned to an old commit and
  republishing the whole site from it every five minutes.
- **Verified once, not yet over a long run.** `origin/gh-pages` at 04:42 UTC
  carries the skip link, the new sort options, five hero cards and the
  no-range dashes, and the watcher has not put an older build back over them
  since. Re-check the same way if anything looks reverted:
  `git fetch origin gh-pages && git show origin/gh-pages:index.html | grep -c 'class="skip"'`
  — expect `1`. A `0` after a watcher pass means the §8.5 fix did not take.
- **Remember the CDN.** GitHub Pages serves `max-age=600`, so `curl` of the
  live site can be ten minutes stale and *looks* like a failed publish. This
  cost real time tonight. Check `origin/gh-pages` with git, not the URL, when
  you want to know what was actually published.

### Queue, in the order I would take it

1. **§3c song page front matter** — Ian's most recent review, four items, all
   well specified. The `.dek` font fix is a one-liner; the FAQ page is the
   biggest piece.
2. **§3d keyboard hotkeys** — the accessibility floor is done; this is the
   jumping layer.
3. **§7 method page** — table of contents and reordering. Untouched.
4. **§6 remaining visual work** — cards have no grain and use a plain rule
   where pages use `.rule2`; the card mark is invisible at thumbnail size.
5. **§5 `content-visibility` benchmark** — method written down, needs doing
   properly rather than in one live page.
6. **§3b** — the older agreed work, still none of it started.

### Two things Ian has asked for that are not yet scheduled anywhere

- A **festival/event name** for the 35 shows phish.net files as "Not Part of a
  Tour" (§6). Needs a curated table; his call.
- Whether the `MOST SONGS` fact wants a **"show length" or "highest rated"
  view** beyond the sort options added tonight (§8b.7).


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

## 3c. Song page front matter — Ian's live review, 2026-07-28. NOT STARTED

Looking at Tweezer Reprise. The block above the statistics has accumulated
four separate things and reads as clutter. Taken in order:

### The prose is mono because nothing ever told it not to

**Answered:** it is an artifact, not a decision. `body` sets
`font-family:'IBM Plex Mono'` for the whole site, so everything inherits mono
unless it opts out. Literata *is* loaded and *is* used deliberately for running
prose — `.jam`, `.note`, `.aside-note`, and the method page's `.prose` — and
the comment beside those rules says why ("Literata is drawn for reading").
`.dek` simply never got the same treatment. Giving `.dek` Literata is a
one-line change and is almost certainly right.

### "Usually out of" / "usually into" overstates its evidence

Tweezer Reprise has 331 performances; the three songs listed under "usually
out of" sum to 58. Calling that *usually* is wrong — it is "most often", and
even that wants a denominator. Two fixes needed:

- **Reword.** "Most often out of" / "most often into", or show the share.
- **Separators.** `Sleeping Monkey 26  Harry Hood 18  Loving Cup 14` runs
  together as one string of alternating words and numbers. It needs real
  separation between pairs, and the count needs to read as a count.

### The gap explanation does not belong on every song page

It is the first prose on the page, it explains the site's *old* headline
statistic, and anybody exploring Phish statistics probably knows what a gap
is. **Ian's proposal: a FAQ page**, with this as one entry.

**Audit the site for the other entries while building it.** Candidates already
visible from this session:
- What a gap is, and that ours is "shows since" and deliberately not
  phish.net's number (§9 has the reasoning).
- What `>` and `->` mean, and **how they differ** — the current legend does
  not say, which is the substantive complaint below.
- Why a song shows no range bar (fewer than 8 plays in ten years — the tooltip
  now says it per row, but the *rule* wants stating once).
- What "due" means and why dormant songs are excluded.
- What the eras (1.0–4.0) are.
- Why some shows say "Not Part of a Tour".

### The notation legend is heavy and also wrong

The arrow legend is wordy for something repeated on every song page, and it is
**inadequate**: it explains that `>` and `->` both mean the band ran songs
together, but not the difference between them. Either explain it properly
(FAQ) or drop the legend to a link.

## 3d. Keyboard: hotkeys, not just tab order — NOT STARTED

§7b did the accessibility floor (focus ring, skip link, everything reachable).
Ian wants the next layer: **jumping**, not advancing.

- `/` to focus the search box. **Already exists** on the index, songs and song
  pages — but not on `due`, `venues` or `method`, and it is undocumented.
- `[` and `]`, or `←` and `→`, to step through the current collection —
  previous/next show on a show page, previous/next song on a song page. Show
  pages already have a prev/next pager in the markup; song pages have none
  (§4 notes that gap).
- Whatever is added needs to be discoverable — a `?` overlay listing the keys
  is the usual answer, and would pair with the FAQ page above.
- Do not let keyboard control define the site: Ian was explicit that this is
  about not being *forced* to reach for a pointer, not about building a modal
  keyboard interface.


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

- ~~**Debounce input**~~ DONE 2026-07-28, at 80 ms for the filter and 400 ms
  for the URL write. Two timers, because they want different delays — and the
  URL write needs one for a second reason: `history.replaceState` is rate
  limited (Safari ~100 calls per 30 s) and the URL-state work added one per
  keystroke. Keystroke dispatch now costs ~0.1 ms.
- **The container-class idea is aimed at the wrong cost.** Measured at 691
  rows: the number of `hidden` writes is 691 in *every* case, while the pass
  costs 0.3 ms when no row changes visibility, ~10 ms when 607 rows hide, and
  ~36 ms when a hidden set comes back. Cost tracks rows whose visibility
  *changed*, not attribute writes, so moving the writes to one container class
  saves nothing. **Do not do this item as written.**
- **`content-visibility:auto` is the promising lever** — it skips layout for
  offscreen rows while the DOM stays whole, which is exactly the printable,
  Ctrl-F-able property this section is protecting. First attempt measured
  *worse* (65 ms vs 10 ms), but that was the first pass after applying it, so
  the browser was establishing intrinsic sizes for all 691 rows at once. Not a
  fair number. **Deferred, and it needs a real benchmark**: separate page
  loads per condition, N passes each, compare medians — not a before/after in
  one live page like the one that produced that 65.

Also: the index has no era or year headings, while song pages already group by
era with counts and spans. Port that pattern; it gives scroll landmarks and
free anchors.

## 6. Remaining visual work

- ~~`col.c-bar` 16% → 22%~~ DONE 2026-07-28, taken from `c-last` (38% → 32%).
- ~~Bustout rows draw a `track bare` ghost~~ DONE 2026-07-28, and **the note
  above had the cause wrong**. It is not a bustout condition. Any song with
  fewer than `MIN_HISTORY` (8) plays inside the ten-year window has no
  percentile band, so nothing can be drawn — Strange Design has six plays, is
  not a bustout, and looked identical to Johnny B. Goode's 927. Ian spotted
  this on the live page. The ghost is gone; the cell now carries a dim em-dash
  where the mark would have been, and the whole statistics area carries a
  `data-tip` saying which of the two reasons applies ("played 6 times in 10
  years…" / "not played in 10 years…"). Six rows on tonight's page use it.
- ~~Dark-mode band weight~~ DONE 2026-07-28. Both figures confirmed exactly.
  Opacity is a palette variable now (`--band-opacity`) rather than one shared
  constant. Solved for the match instead of taking the ~.55 estimate: .58 on
  the dark paper measures 3.10:1 against light's 3.09:1. (.55 would have been
  2.92:1 — fine, but under rather than level.)
- **Do not remove the 2px paper halo on `.at`.** Marker-against-band is
  1.25–1.87:1 in every combination; the halo is the only reason it reads.
- Cards have no grain and use a plain rule where pages use `.rule2`. The card
  and the page it opens do not feel like the same object.
- Card mark (the arc) at `opacity:.12` is invisible at thumbnail size.
- ~~Header DOM order~~ DONE 2026-07-28. The markup moved rather than the
  grid: it now runs `h1 → .show → .where`, which is what the wide layout
  already showed and what puts the venue nearest the setlist it
  introduces. Verified DOM order equals visual order at 375px and 1000px.
- ~~Masthead weight ran the wrong way~~ DONE 2026-07-28 (Ian, live). The
  first line opened on its boldest element and trailed into its lightest,
  while the two lines under it set their heaviest type hard right. The
  ordinal now leads and the tour closes, so weight builds towards the
  right edge the whole block is set against.
- ~~Orphaned separator on the masthead~~ DONE 2026-07-28 (Ian, live). The
  middot was a `::before` on the ordinal, so it printed whenever the
  ordinal did — including on the 35 shows phish.net files as "Not Part of
  a Tour", where there is no tour to separate. Watkins Glen opened with
  "· 119th show of 3.0". It is its own element now, emitted only with
  something on each side.
  - **Naming those shows properly is not doable from the data.** They are
    festivals, TV sessions and the Mexico runs. The festival name is only
    in the freeform `notes` prose, and a regex over it found 3 of 35 —
    spelling them inconsistently ("SuperBall IX" vs "Super Ball IX") and
    missing Festival 8 entirely. Three inconsistent labels is worse than
    35 blanks. A short curated table (the festivals are a finite, famous
    list) is the only reliable route — **Ian's call, deferred.**

## 7. Mobile and the method page

- ~~Nav targets~~ DONE 2026-07-28. Re-measured first and they were worse than
  recorded: 37×19, and "Due" only 22 wide. **Not fixed with padding** — the
  `border-bottom` is the affordance, and padding-bottom pushes that underline
  off the word it underlines. The hit area grows via a pseudo-element instead
  (24px tall, min 24px wide, inside the anchor) so the ink does not move at
  all. Row gap went .3rem → .55rem so two rows of enlarged areas cannot
  overlap. Verified at 375px: all five pass, none overlap.
- Below 620px a tap in `td.last` goes to the previous show and a tap elsewhere
  goes to the song page, with only a 2px border to say so. Signal it.
- ~~`td.n` aria-label~~ DONE 2026-07-28. `data-tip` still draws the hover; the
  words reach a screen reader as a `.sr` span *inside* the cell, so the figure
  and the median are announced alongside them instead of being replaced. The
  bar cell keeps the hover only — it holds nothing to announce and would have
  said the same sentence twice. `.sr` is a new utility; there was none.
- Method page: ordering is scattered (the bar is discussed mid-gap-calculation)
  and it needs a table of contents.

## 7b. Keyboard navigation — DONE 2026-07-28 (Ian)

Basic navigation, searching and sorting now work without a pointer, without
keyboard control taking over the design.

- **A focus ring in the site's own accent, everywhere.** Search, sort and the
  chips already had one; links, rows and hero cards fell through to Chrome's
  1px blue default — off-palette on both papers, and thin on exactly the
  things a keyboard travels between. Now 2px `--hot` on every focusable, tucked
  inside rows and cards rather than floating off a full-width band.
  `:focus-visible`, so a pointer click never draws it.
- **A skip link on all seven page types.** The index puts 691 rows between the
  search box and the footer. The link is off-screen until focused, then a real
  145×39 control in the corner; its target carries `tabindex="-1"` so focus
  actually lands there and the next Tab is the search box rather than the top
  of the page again.
- Verified with real Tab presses, not programmatic focus — `:focus-visible`
  does not reliably match programmatic focus, so the first attempt to measure
  this reported "no focus ring at all", which was wrong.
- Already fine and left alone: rows on every list are real anchors, the era
  chips are buttons, sort is a `<select>`, `/` focuses search and Escape
  clears it, and the theme toggle is three buttons.

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

5. **It republished the whole site from a frozen checkout.** A resident job
   checks the repository out once and then lives for hours, rebuilding and
   publishing *everything* every five minutes -- but it only ran `git pull`
   inside the branch that fires when `site/data` changed. So once a show
   settles and no new songs arrive, it stops tracking main altogether, which
   is precisely when it is still publishing on a five-minute cadence. Tonight
   the live site flip-flopped for forty minutes: each watcher pass put the
   03:55 build back, each push put the new one up again. The published page
   was never wrong for long, which is what made it hard to see. Fixed by
   pulling main at the top of every pass, before the build.

   **This is the third variant of the same failure** -- §8.2 published a site
   with the show missing, §8.3 served a cached setlist, and this republished
   stale code. The shape is always "a long-lived job keeps publishing from
   something it read once".

All five are fixed. The point is that they existed at once, each invisible
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

### The index "live now" banner outliving the show — most likely already fixed

Ian saw the index still showing the on-stage banner while the show page it
linked to no longer claimed to be live. **The current build does not do this.**
Checked directly: `site/data/2026-07-27.json` has `provisional: false`, the
show page contains no "being played right now", and the built index contains
no `<a class='onstage'>` at all — the only "onstage" hits in it are CSS rules.

The most likely explanation is bug 5 above, not a settlement bug. The stale
watcher was republishing the **03:55 build over the top of every newer one**,
and at 03:55 the show *was* still provisional — so the live site kept getting
a banner-carrying index back every five minutes while the freshly-built show
page it linked to came from a later publish. Two publishers, two vintages, one
site.

**Not proven, and worth one check when the next show runs**: if the banner and
the show page ever disagree again *after* the watcher fix, then there is a
real settlement bug and the two are computed from different states —
`summarize()` reads `provisional` for the index, `render_html` reads it for
the page, so they should never disagree within one build.

## 8b. Provisional decisions, for Ian's batched review

Each of these was made without him so work could continue, and each is cheap
to reverse — a label, a threshold or a few lines. None needs a decision to keep
working; all of them are here so the batch can be reviewed in one sitting.

1. **The empty bar draws an em-dash, not nothing.** §6 said "draw nothing at
   all". Nothing is invisible, and invisible is what made the row confusing in
   the first place. A dim `&mdash;` where the mark would have been states the
   absence instead of merely having it. Revert = delete one CSS rule and one
   span.
2. **"Most Songs" is the label for the fullest-night hero card**, not "Longest
   Show" — two cards reading "Longest …" side by side invited the number to be
   read as a second gap figure.
3. **The venue page is not in the hero's `→` vocabulary twice.** `VENUES` and
   `SONGS DUE` both link out, giving three linked cards of six. If that reads
   as too busy, the fix is to drop the arrow from one, not to unlink it.
4. **Venue links are quoted phrases, not an exact-match filter.** A `?venue=`
   parameter matched against a `data-venue` attribute would be exact by
   construction; quoting is a smaller change that also gives the search box a
   general capability. Measured exact for all 153 venues today, but it is
   correct-in-practice rather than correct-by-construction, and a future venue
   name that is a phrase-prefix of another would break it. The check to re-run
   is in §4.
5. **`possumlogic.yml` retries a rejected publish three times, then fails the
   step.** Three is a guess; it only has to outlast the watcher's five-minute
   cadence, and each attempt is a fetch plus a tree copy.
6. **The header's reading order was unified on context-above-venue**, which
   is what the wide layout already showed. The alternative was to flip the
   wide layout to venue-first and leave the markup alone. Reverting is two
   lines in `SHELL`.
7. ~~**`MOST SONGS` stays a hero card**~~ — **reversed by Ian, correctly.**
   It is static content in a slot whose other five figures move with every
   show: once the backfill reaches 1999-12-31 it becomes Big Cypress and never
   changes again. A fine fact, a bad headline. Removed from the hero (back to
   five cards) and made reachable instead by sorting the archive — the index
   sort gained **Most songs** and **Highest rated**, the latter answering the
   same kind of question and not previously askable here at all. 707 of 711
   shows carry a rating; the four without sort last rather than as zero.

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
