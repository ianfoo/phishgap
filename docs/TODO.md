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

**Ian's standing instruction, 2026-07-27:** verify, then commit and push —
do not end a turn holding verified work, and do not stop with queue items open
and nothing blocking. He does not want to babysit turns or re-point a fresh
session at this file. He also wants every turn to end with a **table** of what
was done, why, and what came of it.

### The 2026-07-28 session, second sitting

Two bugs Ian found on the live due page, both fixed and both written up in
§2b: dormant songs were ranked as due because the ten-year window travelled
with each song, and the list was sorted by a figure it never printed. The fix
reached the song pages as well — 148 of 588 changed — because the same
travelling window fed their statistics. He also asked for the `site/data`
reorganisation now filed as §2c.

### In flight when the earlier sitting ended

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

1. **§3d keyboard hotkeys** — the accessibility floor is done; this is the
   jumping layer. The `?` overlay it wants now has a natural companion in
   `faq.html`.
2. **§7 method page** — table of contents and reordering. Untouched. The FAQ
   page's contents block is a working pattern to copy: it is generated from
   the same list as the entries, so it cannot name a section that is not there.
3. **§6 remaining visual work** — cards have no grain and use a plain rule
   where pages use `.rule2`; the card mark is invisible at thumbnail size.
4. **§5 `content-visibility` benchmark** — method written down, needs doing
   properly rather than in one live page.
5. **§3b** — the older agreed work, still none of it started.

§3c is done — see that section for what landed and §8b.8–11 for the calls
made along the way.

### What the 2026-07-27 session added

§3c, all four items, plus the nav regression it exposed (§8c) and the same
segue hole on the method page. New page: `faq.html`, reached from a
**Questions** nav item on all eight page types. Verified in a browser rather
than from markup — Literata measured by advance width, nav hit areas re-checked
across every page type at 375px, pairing alignment across eight viewport
widths, and every link and anchor resolved. Ian's mid-session queue is §8d.

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

## 2. ~~"Due" page~~ DONE 2026-07-28 — `due.html`, 40 due, 283 dormant excluded

`site/data/current.json` already ships `since` (shows since last played) for
every song, and each song page carries `data-high` (85th percentile) and
`data-bustout`. A ranked "what is overdue going into tonight" page is the most
shareable thing the site could publish.

**Dormant songs must be excluded.** A song with no recent norm that has been
gone 250 shows is not *due* — nobody expects it. Only songs with a real
percentile (>= 8 plays in the ten-year window) that are past it count as due.

**That exclusion did not work, for nine months.** See §2b.

## 2b. The ten-year window travelled with the song — FIXED 2026-07-28 (Ian)

Ian, on the live page: "The first entry is a song with a gap of over 500
shows. This is not a song that is 'due.' That's clearly dormant."

He was right, and the dormancy guard §2 describes was never able to fire.
`due_rows` measured "the ten-year window" as the ten years before *the song's
own last performance* — and a song's own last performance is always inside a
window ending at its own last performance. So the filter asked "has this song
had a habit lately?" and every song answered yes about whenever it was last
around. **Anything But Me** was last played 2011-08-15, had 11 gaps in
2001–2011 and a norm of 21.5, and so led the page at 564 shows and 26× late.
It has **zero** gaps inside the real ten years.

- Fixed by anchoring to the newest show the archive counts, in one named
  helper (`recent_cutoff`), so every song is judged over the same ten years.
- **15 songs left the list, 1 joined**: 55 → 40 due, 270 → 283 dormant. The
  15 include Anything But Me (gone since 2011), Uncle Pen (2017), The
  Star-Spangled Banner (2016) and Let Me Lie (2016). Three of the 15 are
  honest borderlines rather than dormancy — Waste, Waiting All Night and
  Sanity sit within a gap or two of the MIN_HISTORY line either way.
- **The same window fed the song pages**, which is why the fix could not stop
  at `due.html`: `render_song` computed its "Median Gap, Last 10 Years" card,
  its `data-high`, and the percentile band behind every row from the same
  travelling cutoff. Left alone, a song would have dropped off the due page
  while its own page still called it due. **148 of 588 song pages** now give a
  different figure and **51** read `n/a` where they used to print a median
  drawn from a decade that ended years ago.
- **`_classify` is deliberately not changed.** A verdict printed on a 2011
  show has to be judged by the ten years before 2011, so that one anchors to
  the show's own date and is correct as it stands.
- **A knock-on the fix exposed**: with no band, no row draws a track at all —
  every one is the no-range dash — yet the column header still read "mark at
  median 8". Rare before, 51 pages after. The header is now emitted only where
  there are bars for it to be a gridline on. Asserted across all 588 pages:
  0 promise a mark they do not draw.

### And the order was invisible

Ian, same message: "There is no apparent order in the Due page. It's not by
date, by gap, or by name. If there is a deterministic order, it's a mystery."

It was ordered — by `n / high`, how many times past its own norm — and that
figure appeared nowhere on the page. Worse, the number set large in the same
column was the raw shows-since count, which ran 184, 131, 176, 90 down the
page and denied on sight that the list was sorted at all.

The ratio is the headline figure now and the raw count moved into the caption
under it (`12.8×` over `184 shows, usually 14.3`). Both numbers are still
there; only which one is set large has changed. Asserted on the built page:
the printed figure descends monotonically for all 40 rows. The standfirst and
the FAQ entry both say what the order is, which neither did before.

## 2d. "Due" needed a ceiling, not just a ratio — Ian, 2026-07-28. DONE

Ian, after §2b landed: "I don't see how we can call a song that hasn't been
played in 184 performances 'due' with a straight face. A song like that is on
the shelf… Something like 'The Howling,' however, could be considered 'due.'
36 shows. That's reasonable."

He was right, and the ranking proved it. Sorted purely by multiple, the top of
the list was **Rise/Come Together at 12.8× — gone 184 shows and four years**,
with Wombat (176 shows, 4.0 yr) third; The Howling, gone 36 shows after
twenty-one performances in four years, sat **ninth**. Both figures were
correctly computed. Only one of those songs is due.

**The first fix was a ceiling at `BUSTOUT_GAP`** — a song whose return
phish.net would call a bustout is not merely late — which moved five songs onto
a shelf. That was right and not enough. Ian, on the result:

> I'm looking at the songs that have multipliers in the 1-2 range and median
> gaps of about 10-20. *These* are the songs I would call "due"… The songs we
> *expect* to hear, but that haven't been played in a bit longer than we
> expect… I'm expecting due songs. I'm not expecting overdue songs.

### Two conditions, and measuring showed both are load-bearing

**The scale was wrong.** "How late" was measured against the 85th percentile —
the gate for *is it late at all* — which is skewed by a song's few worst gaps
and is useless as a ruler. Mr. Completely read **1.8×**, looking mildly late,
while gone 98 shows against a typical gap of 15: **6.5×** on the median. The
multiple is computed and printed against the **median** now, and the row says
"usually every 15" rather than "usually back by 55.2".

**Cadence is a filter in its own right.** Without it Fuck Your Face qualifies —
gone 78 shows, only 2.7× its median — but its median *is* 28.5, so even on time
you wait 28 shows for it. Nobody expects that song tonight. `DUE_CADENCE = 20`
is Ian's own "median gaps of about 10-20".

Both thresholds were fitted to the songs he named, not chosen and then
defended. Every one lands between **1.8× and 3.2×** its median — Golden Age
1.8, Hey Stranger 2.0, Kill Devil Falls 2.2, A Life Beyond The Dream 2.2,
Martian Monster 2.4, 46 Days 2.5, Twist 3.2 — and every song he rejected is far
clear: I Never Needed You Like This Before **12.9×**, Death Don't Hurt Very
Long **16.9×**. `DUE_MULTIPLE = 3.5` sits above his examples and well below
those.

| | plays ≤ every 20 | < 3.5× median | gone < 100 | has a habit | count |
|---|---|---|---|---|---|
| **due** | yes | yes | yes | yes | 9 |
| **overdue** | — | — | yes | yes | 26 |
| **on the shelf** | — | — | no | yes | 5 |
| **dormant** | — | — | — | no | 283 |

All four are listed or counted on the page, and each has a hero cell linking to
its section (dormant excepted — see §2f).

**One boundary case to put to Ian.** He named **The Howling** as due at 36
shows; it lands in *overdue* at **5.1×** a typical gap of 7. He hedged on it in
the same breath ("either still in rotation and just not been played, or shelved
and on its way to dormant"), so this is left where the measure puts it.
`DUE_MULTIPLE` is the one number that moves it.

### Show of Life: the figure was right, the word was wrong

Ian: "it hasn't been played in 131 shows, but according to the stats, it's…
usually played every 53.8 shows..? I feel like they definitely played it more
often than that."

Both halves of his instinct check out. In the ten-year window it has **8
plays**, gaps `[25, 50, 8, 56, 17, 54, 17, 34]` — so 53.8 is the correct 85th
percentile. But its **median is 29.5**, and the page was calling the 85th
percentile "usually", which is a claim the song's own history contradicts. It
reads **"usually back by 53.8"** now, which is what an 85th percentile actually
says: back within that, 85% of the time. His memory of it being played more
often is about its 33 all-time plays, most of which predate the window.

### Shows per year — his correction, measured

Ian: "Phish doesn't play anywhere near 70 shows per year anymore… The number
of shows per year probably needs to be considered."

Measured across the whole counting calendar (2,107 shows, 1983–2026):

| era | mean shows/yr | 100 shows = |
|---|---|---|
| 1990–2000 | 94.7 | 1.1 years |
| 2009–2019 (3.0) | 40.0 | 2.5 years |
| 2021–2025 (4.0) | 43.8 | 2.3 years |

He is right that the rate is nothing like the 1990s. **He is not right that it
is still declining** — 3.0 averaged 40.0 and 4.0 averages 43.8, and the last
five complete years run 36, 46, 49, 41, 47. The drop happened at the 2000
hiatus and the band has been steady since the reunion.

**And the calculation already absorbs this, because gaps are counted in shows
rather than in days.** A gap of 36 shows is 36 chances to hear it whether the
band took eight months or two years over them; the percentile band is built
from the last ten years, so it is calibrated to the current rate by
construction. The one place a rate assumption was baked in was a code comment
converting the cap to years — it now names the measured range and the era it
applies to instead of a single number stated as if timeless.

## 2e. Graphs — Ian, 2026-07-28. FILED, NOT STARTED

His words: "This site needs pretty graphs. Lots more graphs… Especially ones
that animate nicely when they show up on screen, or when the user selects
something that alters what the data represented will be." He explicitly did not
specify what to plot and asked for ideas. Deliberately vague; this is a
direction, not a spec.

**Constraints that fall out of the site as it stands**, worth stating before
anybody reaches for a charting library:

- No external JS. Everything here is hand-built and inlined; a library would
  be the largest dependency on the site by an order of magnitude. Inline SVG
  is the natural fit and already matches the `.track` / `.band` / `.at`
  vocabulary the range bars use.
- `prefers-reduced-motion` is already respected for `.bar .fill`. Any entrance
  animation has to honour it, and the reduced case must be the finished chart
  rather than no chart.
- §5's DOM budget is real. 588 song pages × an SVG each is fine; 691 index
  rows × anything is not.

**Ideas, ranked by what the archive can actually support today:**

1. **A song's heartbeat.** One horizontal strip per song page, a tick per
   performance across its whole life, era-banded behind. This is the chart the
   site is already half-drawing in prose — McGrupp reading 101 / 1 / 13 / 9 by
   era is a song nearly dying and coming back, and a strip shows it instantly.
   Draws left to right on entry.
2. **Shows per year, 1983–2026.** The chart this very session had to compute by
   hand to answer a question. It belongs on the method or FAQ page, because it
   is the context that makes "gaps are counted in shows" make sense.
3. **A song's gap distribution**, with its own percentile band overlaid. Would
   make the range bar self-explanatory — the bar's meaning currently needs a
   paragraph, and a histogram with the band drawn on it needs none.
4. **Era distribution of a setlist** (already promised in §3b) and the
   **debut-year spread** of one night — oldest song to newest as a dot plot. A
   show opening on a 1988 song and closing on a 2024 one is a different night
   from one drawn entirely from *Sigma Oasis*.
5. **Version scores over time** for one song, from the fouldomain ratings
   already archived. Answers "is this song getting better?", which nothing on
   the site answers now.

Ian's framing in §3b applies to all of it: this is about delight, not
completeness. **Do not turn it into a dashboard.**

## 2f. The dormant songs should be explorable — Ian, 2026-07-28. NOT STARTED

His words: "We should allow the users to explore dormant songs. There's some
nostalgia and discovery in there."

Ian also asked for the due page's new sections to get hero cells linking to
them, which landed — except dormant, which has a cell stating 283 and no link,
because there is nowhere yet to send it. His own suggestion: "maybe should be
its own page because of the length? or maybe a collapsible section, which is a
language we don't have on this site (yet)." **A page, most likely** — 283 rows
is more than the shelf and overdue lists put together, and `songs.html` already
carries 588 rows without trouble. A collapsible would be a new interaction
idiom for one use.

Right now §2d's fourth category is **a number in a hero cell that goes
nowhere** — 283 songs the site has full histories for and offers no way to
browse as a group. That is the largest single body of content on the site with
no door into it. Everything needed exists: `due_rows` already identifies them,
and each has its own page.

The obvious shape is a third list, but note it cannot be a straight port of the
due list: dormant songs have **no percentile to rank by**, which is the whole
reason they are dormant. So it needs a different order and a different headline
figure — longest gone, or last-played date, or era of last performance. Last
played is probably the nostalgic one: "you have not heard this since 2014."

He also wants it as a **graph**, and this is the most interesting of the ideas
in §2e because it is about the catalogue rather than about one song:

- **Dormant count per year.** How much of the catalogue is out of rotation at
  any moment, plotted over time. Needs the classification recomputed as of each
  past date rather than only as of today — the archive supports it, since every
  performance carries its date, but it is a real piece of work and not a
  by-product of the current code.
- **Rotation churn: into and out of dormancy.** Ian: "what is the nature of
  rotation into and out of dormancy, or shelvedness?" A song crossing back over
  the line is a bustout, and the archive knows every one of them. Two series —
  songs going dormant in a year, songs returning — say something nobody has
  said about this band with numbers.
- **How stable the set is.** The share of a year's performances drawn from the
  songs that were also in rotation the year before. A single number per year,
  and probably the most revealing chart on the list.

**Sequence it after §2e's simpler charts.** All three of these need a
classification that can be evaluated *as of a past date*, which the current
code cannot do — it answers only "what is dormant now". That is the actual
piece of work, and the charts are cheap once it exists.

## 2c. `site/data` layout — Ian, 2026-07-28. DONE

His words: the directory "is cluttered. shows should probably go under a
`shows` directory to keep things organized. As it is they're siblings of
calendar, schedule, cards — and a songs subdirectory (which seems sensible)."

Measured: `site/data/` holds **711 `<date>.json` show reports** flat, beside
five index files (`calendar.json`, `cards.json`, `current.json`,
`phishin.json`, `schedule.json`) and one directory that already does it right,
`songs/` with 588 in it. He is describing an inconsistency the archive created
itself — `songs/` was added later and nobody went back for the shows.

The reads are contained, which is the good news. Everything that touches a
show's JSON path goes through four places: `site_paths()`, `archived_dates()`,
`saved_reports()` and the glob in `remeasure()`, plus one `makedirs`. The
`REPORT_NAME` regex exists precisely because the flat directory made a show
indistinguishable from an index file by name — under `shows/` that guard stops
being load-bearing, though it is worth keeping.

**What makes this bigger than a `git mv`:**

- The 711 files are tracked in `main` *and* published to `gh-pages`. Moving
  them locally without moving the published tree leaves the site serving the
  old paths; moving both in one publish is the whole job.
- `possumlogic.yml` restores parts of the site from `gh-pages` before
  building. Check what it restores before assuming a rename propagates.
- A reader with the old layout checked out must still build. Either read both
  locations for one release, or migrate on first run and say so in the log.
- `watch.yml`'s conflict guard names `site/data/<date>.json` in a comment;
  the comment is documentation and should move with the files.
- Nothing outside the repo links these paths — the site's own JavaScript
  fetches `data/current.json` and `data/songs/<slug>.json` only, both of
  which stay put — so no redirects are needed. Verify that rather than
  believing it: `grep` the built HTML for `data/` before shipping.

**What landed.** 711 files moved, git recorded all 711 as renames and zero as
deletions, and a `--rebuild` afterwards changed **no page and no byte** — which
is the invariant a pure move has to meet and the one worth asserting. The five
index files stay flat in `data/`, beside `shows/` and `songs/`.

- The four readers now go through `show_data_dir()`. `REPORT_NAME` is kept
  even though nothing else lives in `shows/` to be confused with: it is what
  the migration recognises a stray report by.
- **`migrate_show_data()` moves any reports still lying flat**, once, on any
  run with `--site`. Not a nicety: a checkout made before this commit, built
  with code from after it, finds **zero** shows and publishes a complete site
  with the entire archive missing — and this file records three separate
  outages with exactly that shape, every one of them silent. Tested against a
  copy of the real archive: 0 shows before, 711 after, idempotent on a second
  pass, index files untouched.
- Neither publisher needs anything: both replace the published tree wholesale,
  so the old paths leave `gh-pages` on the first publish. CI restores only
  `card/` from `gh-pages`, never `data/`. The workflow push triggers name only
  `possumlogic.py` and the workflow file, so nothing there had to move.
- Two stale references fixed in the same pass: `watch.yml`'s conflict-guard
  comment, and README, which named `site/data/<date>.json` *and* still said
  reports land in `site/<date>.html` — they have been under `show/` for a
  while. That second one is the §3b lesson again: a doc nobody re-read.

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
- ~~**The `--html` single-file output must stay self-contained.**~~ **This is
  not true and has not been for a long time.** Ian, 2026-07-27: the
  self-contained page mattered when he was shipping one styled HTML file over a
  messaging service, and stopped mattering the moment this became a site.
  Measured rather than taken on his word — a real `--html` file carries **three
  references to Google's font hosts** and links
  `fonts.googleapis.com/css2?family=IBM+Plex+Mono…&family=Literata…`. It
  inlines exactly one face, Bagnard, as a 13 KB `data:font/otf`. Since `body`
  is Plex Mono site-wide, essentially every word in that "self-contained" file
  depends on a network fetch; only the wordmark survives offline. It also gets
  no paper grain, because the grain lives in `fonts.css` and this path emits
  the inline face instead of the sheet.

  So there is no self-containment left to protect, and no reason for it to be
  an exception in §8e's stylesheet plan. Keep the single-file mode — it is
  still a convenient way to hand someone one page — but stop treating it as a
  constraint on how the hosted site loads CSS. **The general lesson Ian drew is
  the more useful one: periodically re-check the assumptions written down here.
  This one shaped a design decision hours after it had stopped being true.**

## 3c. Song page front matter — Ian's live review, 2026-07-28. DONE

All four items landed. The block above the statistics is now three things —
subtitle, the pairings, and one line about the marks — where it was four, and
the two that went are the two Ian named. Taken in order:

### ~~The prose is mono because nothing ever told it not to~~ DONE

**Answered:** it is an artifact, not a decision. `body` sets
`font-family:'IBM Plex Mono'` for the whole site, so everything inherits mono
unless it opts out. Literata *is* loaded and *is* used deliberately for running
prose — `.jam`, `.note`, `.aside-note`, and the method page's `.prose` — and
the comment beside those rules says why ("Literata is drawn for reading").
`.dek` simply never got the same treatment.

- **It was two rules, not one, and the note above was wrong about why.**
  `.dek` had a base rule in `SONG_CSS` only. `INDEX_CSS` carried `.dek.foot`
  and nothing else, so the identical class on `due.html` and `venues.html` was
  falling through to a bare `<p>` — 16px, mono, full measure — while a song
  page set it at 12px and dim. One class, two appearances, by accident. Both
  sheets state it now: Literata, .8125rem, `opsz` 12.
- Verified by measuring the rendered advance against the same string forced to
  each face, not by reading the CSS: `.dek` resolves to Literata on the song,
  due, venues and FAQ pages, and `document.fonts.check` confirms it loaded.

### ~~"Usually out of" / "usually into" overstates its evidence~~ DONE

Tweezer Reprise has 331 performances; the three songs listed under "usually
out of" sum to 58. Calling that *usually* is wrong — it is "most often", and
even that wants a denominator.

- **Reworded** to "Most often out of" / "Most often into".
- **The count now terminates its own pairing**: `Sleeping Monkey 26×`, and the
  gap between pairings went .7rem → 1.4rem. A middot *between* items was the
  obvious separator and is the wrong one here — this block wraps at every
  phone width, and a separator that lives between two items can land at the
  head of a wrapped line. A terminator belonging to the item cannot. See §8b.9.
- **The two rows are one grid now**, so both lists start at the same place.
  As two independent flex rows they each began wherever their own caption
  ended, and "out of" is longer than "into" — the lists sat 14.8px out of line.
  The caption column is `max-content`, so neither row states a width and the
  alignment holds at 320, 375, 414, 620, 760, 900, 1100 and 1400px, checked.

### ~~The gap explanation does not belong on every song page~~ DONE

It is the first prose on the page, it explains the site's *old* headline
statistic, and anybody exploring Phish statistics probably knows what a gap
is. **Ian's proposal: a FAQ page**, with this as one entry.

Built as `faq.html`, eight entries, every one from the audit list:

- What a gap is — and that it is not a length of time.
- Why a song page says "shows since" rather than a gap (§9's reasoning).
- What `>` and `–>` mean and how they differ.
- Why a row has no range bar.
- What "due" means and why dormant songs are not on the list.
- What the eras are.
- Why some shows say "Not Part of a Tour".
- Why a show page says "setlist still coming in".

Entries and the contents block at the top come from one list in the source, so
the page cannot advertise a question it does not answer. Where the method page
already holds the long reasoning the entry links to its anchor rather than
restating it — both of those deep links were checked against the ids that page
actually emits. Reached from a new **Questions** item in the nav on all eight
page types.

### ~~The notation legend is heavy and also wrong~~ DONE

The arrow legend was wordy for something repeated on every song page, and it
was **inadequate**: it explained that `>` and `->` both mean the band ran songs
together, but not the difference between them. It is one line now — the marks,
four words each, and a link to `faq.html#segues`.

**The method page had the same hole** and it has been fixed there too; §4 of
that page said the same thing and stopped at the same place.

The difference, from phish.net's own FAQ on segues (they block `WebFetch`;
read in a browser): `->` is an actual segue, one song jamming fluidly and
without interruption into the next. `>` is everything else that runs together —
and is *also* a convention, used between songs always played as a set (Mike's
> Hydrogen > Weekapaug, The Horse > Silent) and around lead-in and exit songs
like HYHU, **even where there was an audible gap in the music**. That last part
is the bit worth having: a `>` is not always a claim about sound.

## 3e. FAQ and song front matter — Ian's second live review, 2026-07-28. DONE

### The contents block read as the first answer

His words: "The list of questions in the FAQ should stand out a little more.
The way it's rendered, it sort of looks like the answer to the first question."

Measured, and he was describing something real: the entries were Literata at
.9375rem in `--ink-soft`, and the `h2` immediately under them was Literata at
1.0625rem in `--ink`. One size and one shade apart, same face, both over
hairline rules — so nothing said "index" rather than "prose". Three things
separate it now: the block is enclosed rather than merely ruled, the entries
are numbered, and the numbers are mono, which is this site's voice for a
figure. A reader can tell an index from an answer before reading either.

- **`display:grid` on the anchor broke the segues entry** and this is worth
  writing down: the number is a `::before` counter in its own column, and a
  grid container makes *every* child a grid item — so the two
  `<span class="num">` marks inside "What do `>` and `–>` mean?" each took a
  cell and that entry rendered as three broken lines. The question is wrapped
  in one span now, whatever markup is inside it. Caught by looking at the
  page; nothing about the markup or the CSS says this on inspection.

### Every answer now has a way back

"I don't want to jump to a question and then have to scroll back to the top of
the page myself to look at another one." Each answer ends with **↑ All
questions**. The target carries `tabindex="-1"`, so focus actually lands on
the index and a keyboard reader's next Tab is the first question — verified
by clicking it and reading `document.activeElement`, not by reading the CSS.

### The eras answer had its arithmetic wrong

"It describes the *four* stretches the band has played in as 'either side of
its two long breaks.' The math doesn't add up." It does not: four eras are
separated by **three** breaks — the 2000 hiatus, the split after Coventry, and
the 2020 shutdown. The answer said two.

He also asked whether "era" is the site's word, since the answer never used
it. It is — the chips on the song pages and the index filter both say Eras,
and `era()` is what computes them. The entry now leads with the term, and the
heading names it too, so the contents list reads "What are the eras" rather
than only "What are 1.0, 2.0, 3.0 and 4.0?". 3.0's boundary is identified as
the Hampton reunion, checked against the archive rather than from memory.

### The notation legend came off the song pages

"I'm wondering whether we really need to call this out on every song page at
all… if a user is wondering, maybe they should just investigate the FAQ page,
where we have conveniently answered this question." Agreed and removed — it
was four lines of prose above the statistics on all 588 pages, explaining a
notation to everybody in order to reach the few who wondered, and wrapping
awkwardly while it did.

The pointer moved rather than vanishing: the **Before / after** column header
now carries `> and –>` as a link to `faq.html#segues`, wearing the two marks
as its own label, so a reader who wonders what `>` means is looking straight
at the answer's door. **One gap to know about**: `.head` is hidden below
820px, so on a phone that pointer is not there and the reader has the nav's
FAQ link like every other page. Given the item was to *reduce* what every page
carries, that is the right side to err on, but it is a deliberate call rather
than an oversight.

Front matter is now three things: the title, the subtitle, and the pairings.

### One provisional decision made in passing

**The song page's Current Gap card said "line 10".** That is the site talking
to itself — the reader has no way to know which line, and the number is the
one the song becomes overdue at. It says **"due at 10"** now. Not something
Ian asked for; one string, and reversible in one line.

## 3f. Sticky column headers on the tabular pages — Ian, 2026-07-28. DONE

His words, after scrolling a setlist longer than the viewport: the column
headings scroll off. The show page repeats them per section (set 1, set 2,
encore) so it is not as bad as it could be, but he wants consistency across
the site — "which implies the other tabular shells as well".

What he is describing is exactly what `position:sticky` does natively when the
header lives inside each section rather than above all of them: the header of
the section being scrolled into view **takes over** from the one above it, and
**peels off** again on the way back up, with no JavaScript and no measurement.
Each set's header sticks only while its own set is on screen.

**The thing to get right is the one he named.** A sticky header covers the top
of the viewport, so anchor targets land underneath it — the song page has had
this problem more than once. Every jump target on an affected page needs
`scroll-margin-top` at least the height of the sticky strip, and that height
has to come from one place both the CSS and the offset read, not from two
numbers that agree today. The song page's `.stuck` bar is the existing
precedent and is worth reading before starting.

Ian's clarification, same session: "I want sticky headers on all the tabular
shell pages. That currently includes venues and due now, as well. I think
that's it."

**Measured before starting, and it changes the shape of the job.** Only two
page types have column headers at all:

| page | header today |
|---|---|
| show | `<thead>` per set section — 3 on a two-set-plus-encore night |
| song | one `.row head` div, plus the existing `.stuck` bar |
| index, songs, due, venues | **none** |

So on four of the six this is not "make the header sticky", it is "give the
page a header, then make it sticky". That is a visible design change rather
than a scrolling one, and on the due page it fixes something already noted
here: the headline figure on each row carries no label at all.

### Why the list pages are not tables — Ian asked, and there is a real reason

"Why is the songs page not using a table? … If there's a good reason for this,
explain it to me."

There is, and it is one line of HTML law: **an `<a>` cannot wrap a `<tr>`.**
Every row on the index, songs, due and venues pages is a *single link* — one
`<a class="row">` around the whole row — so those rows cannot be `<tr>`s
without either losing the whole-row target, faking it with a click handler
(which breaks middle-click, open-in-new-tab and the status bar), or putting a
separate link in every cell (which makes a screen reader announce four links
per row). A show page is a real `<table>` for the opposite reason: its rows
carry **two** destinations — the song, and the night it was last performed —
so its links live in cells and a `<tr>` costs nothing. Verified against the
built markup rather than recalled: one show row contains 2 anchors, one list
row contains 1 wrapping everything.

So the markup differs for a reason. **The missing headers were not a reason,
they were an omission**, and Ian was right about that — all four list pages now
have one, sharing each page's grid template through a paired selector
(`.row,.lhead{…}`) rather than a second copy of the column widths.

### What landed

- **Show pages**: `thead th` is sticky. Each table is its own containing block,
  so the hand-off Ian described comes free — proven by measurement, not by
  eye: at one scroll position set 1's header is stuck at top 0 with its table
  still on screen; 500px later set 1's header has been carried off (top −167,
  its table's bottom −136) and set 2's is stuck at 0. Exactly one header is
  ever stuck.
- **Index, songs, due, venues**: a new `.lhead`. Asserted in the browser that
  the header's computed `grid-template-columns` is byte-identical to its
  rows', including the figures sub-grid — the labels cannot drift off their
  columns. The due page gains something separate from stickiness: its headline
  figure had no label at all, and now reads **How late**.
- **Song pages left alone.** They already carry sticky column labels, in the
  `.stuck` bar, which also carries the song name and its running totals. A
  second mechanism would have competed with it for the same 30px of screen.
- **`scroll-margin-top` on every `[id]`**, stated once per sheet rather than
  per anchor. Tested the exact failure Ian named: activating the skip link on
  the due page lands the list at 41px with the sticky header's bottom at 41px
  and the first row not behind it.

### Two bugs this turned up, both found by measuring rather than reading

- **`.lhead.due-h` and `.lhead.vn-h` out-specify `.lhead`.** The narrow-width
  rule hiding the header was written as `.lhead{display:none}` — one class
  against two — so at 440px the media query was active, the rule was in the
  sheet, and the computed display was still `grid`: a three-column header
  standing over two-column stacked rows. All three selectors are named now.
- **The skip link's target was briefly `display:none` on a phone.** `#main`
  had been moved onto the header, which is hidden below 620px, so on the due
  and venues pages the skip link would have landed nowhere at exactly the
  width where skipping matters most. The id is back on the `<ol>`, which is
  the content anyway.

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
    in the freeform `notes` prose. A short curated table (the festivals are
    a finite, famous list) is the only reliable route — **Ian's call,
    deferred.**
  - **The "3 of 35" figure this used to quote does not reproduce**, and it
    also said Festival 8 was missed entirely, which is wrong — re-measured
    2026-07-27, a name-hunting regex hits 10 of the 35 and *does* find
    Festival 8. The conclusion is unchanged and the reasons are better: the
    hits include ordinary prose ("it" matching IT), two spellings of Festival
    8 and three of Super Ball IX ("SuperBall IX" / "Super Ball IX" /
    "superballix"), and nothing at all for the Dick's runs, the Mexico runs,
    the TV sessions, or Watkins Glen. Wrong and inconsistent labels on ten
    shows is worse than 35 blanks. Do not re-quote the old number.

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
8. ~~**The FAQ is called "Questions" in the nav**~~ — **reversed by Ian, same
   night.** "FAQ is a well understood term on the internet. There's no good
   reason to call it 'questions'." He is right; the argument for "Questions"
   was internal consistency with a page-name family, against a word every
   reader already knows. Nav, page heading, `<title>` and share title all say
   **FAQ** now. The file was always `faq.html`.
   - And the awkwardness I was trying to sit next to was real, but in the
     other item: **"How this is worked out" is now just "Method"** in the nav
     and in every footer. Ian: "really wordy and kind of awkward." The page
     keeps the sentence as its own heading, where it reads as description
     rather than as a target. **Open, his call:** he floated dropping it from
     the nav entirely and making it a FAQ entry that redirects — but also
     said it may deserve to stay first-class "because it explains things that
     might not be 'frequently asked,' exactly." Left first-class.
   - **"Method" then went too far the other way** — Ian: "definitely shorter,
     but maybe also ambiguous." The label is **"How this works"**, his own
     suggestion, in all 8 navs and all 7 footers. He noted it is not strictly
     accurate — the page explains how the numbers are *worked out*, not how the
     site works — and invited better. Alternatives that are shorter than the
     original and more accurate than "Method", if he wants one:
     **"How the numbers work"**, **"How this is counted"**, **"Where these
     numbers come from"**. The page keeps its own fuller heading either way.

## 8b bis. The song preview card printed no longest gap

Ian spotted it on Johnny B. Goode: the card sat under the words LONGEST GAP
showing an em-dash while the song page showed 927.

The third stat on a song card is the best version's score where one exists and
the longest gap where none does. The label already switched correctly; the
**value was an em-dash in both branches**, so the longest-gap case had never
once printed a figure — **340 of 588 songs**, every one of them a share image.

Fixed, and fixed at the cause rather than at the symptom: `song_card` and
`render_song` each did their own arithmetic over the performance list, so they
could differ in more ways than this one. Both now call `countable_gaps(doc,
counting)`, which applies the two exclusions once — the counting calendar, and
the debut's own gap (Johnny B. Goode's debut carries **954**, which counts shows
since the band's first show, not since a previous performance of this song; the
real longest gap is 927). The card also counted *every* performance where the
page counts only countable ones, which would have diverged on any song with a
soundcheck row.

Checked as an invariant rather than on the one song: all 588 cards regenerated
and compared field by field against their own page. **0 disagree**; 197 now
print a real longest gap; the remaining 143 are songs played once, where both
say `n/a` (the card said `&mdash;` — it now uses the page's word).
9. **A pairing's count terminates the pairing (`26×`) rather than a middot
   separating pairings.** Reasoning in §3c. If the `×` reads as noise the
   alternative is not a middot — it is stacking the count under its song.
10. **The denominator for the pairings is left in the subtitle** ("331
    performances"), not repeated per pairing as a share. Ian's note said the
    count "wants a denominator"; printing `26 of 331` three times per side is
    the clutter the whole item is about. One line above, once. If he wants
    shares, `neighbours()` already returns the counts and the total is to hand.
11. **The FAQ links to the method page rather than restating it.** Two entries
    are two sentences and a link. The alternative — a self-contained FAQ — puts
    the same reasoning in two files that will drift.

## 8c. Found while building §3c — a nav that had never been pushed

**Adding a sixth nav item made `due.html` scroll sideways on a phone**, and it
is worth writing down because the cause was not the new item.

`INDEX_CSS`'s `.crumb` had no `flex-wrap`, so the row could not break; at five
sections each *label* wrapped inside itself and the row stayed within the
viewport. At six it stopped fitting and the due page laid out 401px wide inside
a 375px client — the whole page scrolling for one nav link. `SONG_CSS`'s
`.crumb` has wrapped all along. The two sheets disagreed only because nothing
had ever pushed the narrower one.

Fixed by giving `INDEX_CSS` the song sheet's `flex-wrap:wrap` and `.55rem .9rem`
gap, plus `white-space:nowrap` on the anchors so a row breaks *between* labels
rather than inside them. Re-ran §7's check afterwards across all eight page
types at 375px: every hit area still 24×24 or better, no two overlapping,
nothing past the viewport edge, and no page scrolling sideways.

### The footer link had been the browser's default blue on seven of eight

Ian spotted this the same night: the footer link "appears semi-unstyled,
appearing as blue text with an underline, like a default link in a browser
would." Measured, it was worse than that — `footer a{color:var(--dim)}` existed
in `SONG_CSS` **only**, so the footer link rendered in Chrome's default link
colour on the index, songs, due, venues, method, FAQ and every show page. Song
pages were the single exception. Long-standing; nothing in this session caused
it.

All three sheets now carry the rule, and it matches how links are drawn
everywhere else on the site — `--dim`, no `text-decoration`, a `--rule`
border-bottom, `--hot` on hover. Checked on all eight page types: no link
anywhere in a footer still resolves to a default colour.

**This is the argument for §3b's "strip INDEX_CSS out of METHOD_CSS".** Three
sheets carrying near-identical rule text also carry near-identical rules that
have silently diverged, and the divergence only shows up when something new
leans on it. Two independent instances in one session — the nav that could not
wrap, and a footer link styled in one sheet of three. **When touching anything
that lives in more than one sheet, check all three and assert the match
count**; CLAUDE.md says this and it is worth believing.

## 8f. The wordmark flicker — Ian, 2026-07-27. FIXED, and it was not the font

His guess was the inlined Bagnard. It was not: **no hosted page inlines a
face** — `data:font/otf` appears zero times in the published `index.html`. The
inline path exists only for `--html`.

It was a serial fetch. `fonts.css` holds `src:url('./font/Bagnard.otf')`, so
the face could not begin loading until that stylesheet had arrived *and been
parsed*. Measured on localhost, where there is no latency to blame:

| | `fonts.css` starts | `Bagnard.otf` starts | initiated by |
|---|---|---|---|
| before | 9.3 ms | 24.1 ms | the stylesheet |
| after | 10.4 ms | 10.3 ms | the document |

On the live site that 14.8 ms is a whole round trip, and `font-display:swap`
spends it painting Georgia and then swapping — which is the flicker.

Fixed with `<link rel="preload" as="font" crossorigin>` in every shell, at the
right relative depth (`./font/` for root pages, `../font/` for `show/` and
`song/`). `crossorigin` is not optional: fonts are fetched in CORS mode and a
preload without it is discarded and refetched. Verified the face still renders
(advance-width against Georgia, not by reading CSS) and that no page logs a
"preloaded but not used" warning — every page type does use Bagnard, though on
a show page it is not the `h1`, which is the date and deliberately mono.

**Still on the table if it ever flickers again**, in order of value: convert
the 12.9 KB `.otf` to `.woff2` (typically 40–60% smaller); or inline the face
into `fonts.css` as a data URI, which collapses to a single request since that
sheet is already fetched and cached. `font-display:optional` would kill the
swap outright but a first-time visitor might never see the wordmark in Bagnard,
which is too high a price for the one thing that is the site's identity.

## 8g. The card index outlives the cards it describes — GUARD IT

Cost real time tonight and is now a CLAUDE.md gotcha. `site/data/cards.json`
records what each preview card was drawn from and **is tracked in `main`**;
`site/card/*.png` is **gitignored**. So a local `--rebuild` draws the images
here, writes "already drawn" into a file that ships, and CI then restores the
*published* PNGs, reads an index claiming everything is current, and draws
nothing. The longest-gap fix reached the markup and the images kept the
em-dash — spotted only because the published PNG was opened and looked at.

Recovered by deleting the 588 song records and dispatching a run. Note the
second trap on the way out: that commit touched only `site/data/`, which is
**not** one of `possumlogic.yml`'s push trigger paths, so it did not start a
run at all and sat on `main` doing nothing until dispatched by hand.

**Recommended fix: move the index to where the images are.** Write it to
`site/card/cards.json` so it publishes to `gh-pages` alongside the PNGs it
describes, and stop tracking it in `main`. The workflow already restores
`card/` from `gh-pages`, so it would restore the index in the same step, and
the record could no longer disagree with the artifacts because they would
travel together. Until that lands: **after any local rebuild that draws cards,
do not commit `site/data/cards.json`** — take the version CI produced.

## 8e. The three stylesheets — Ian's question, measured. NOT STARTED

Ian, 2026-07-27: "why are there three stylesheets that contain duplicate
definitions? … The fact that you need to call out the triplicate definitions in
the CLAUDE.md file feels like a smell." He is right, and he offered to accept a
build step producing a bespoke sheet per page. **Measured before answering:**

| sheet | size | rules |
|---|---|---|
| `CSS` (show pages) | 34.3 KB | 135 |
| `INDEX_CSS` | 22.3 KB | 130 |
| `SONG_CSS` | 35.8 KB | 176 |
| `SONGS_CSS`/`METHOD_CSS`/`FAQ_CSS` | 23.3/24.0/26.1 KB | extend `INDEX_CSS` |

- **31 rules (4.0 KB) are byte-identical in all three.** Pairwise, 32–46.
- **1,307 pages inline a sheet: 45.6 MB of CSS, 39% of all HTML on the site.**
- A show page is **54% stylesheet** (33.5 KB of 62.2 KB); the FAQ is **65%**.
  The index looks fine at 3% only because 691 rows dwarf everything.
- **The union of every sheet is 43.9 KB / 380 rules** — barely more than
  `SONG_CSS` alone.

**These are two different problems and they want different fixes.**

1. **Source duplication** — the actual smell, and the cause of both bugs in
   §8c. Fix by composing sheets from named blocks (`BASE` + per-page blocks)
   instead of copy-pasted rule text. No output change, no risk, and it is what
   stops an edit landing in one sheet of three. **Do this first.**
2. **Wire duplication** — 45.6 MB. Fix by linking one `site.css` instead of
   inlining. The site already links `fonts.css`. A show page would go 62 KB →
   ~29 KB, the FAQ 39 → ~14 KB, and it is cached after the first page.
   **Nothing is in the way of this.** An earlier draft of this section carved
   out an exception for the `--html` single-file output on self-containment
   grounds; that requirement is dead and the file was never self-contained
   anyway — see §3b, corrected.
3. **Per-page bespoke sheets — recommend against, and the measurement is why.**
   The union of everything is 43.9 KB against `SONG_CSS`'s 35.8 KB, so the most
   a perfect per-page split can save over one shared cached sheet is roughly
   8 KB, on the first request only. Against that: rules are selected by classes
   that JavaScript adds at runtime (`.onstage`, `.since`, `hidden`, the theme
   toggle's states, `.era-chip` selection), so static usage analysis will drop
   a rule that is needed and the failure is invisible until someone is looking
   at a live show. Not worth it. If the shared sheet ever gets big enough to
   matter, the honest lever is deleting the unused rules §3b already names in
   `METHOD_CSS`, not generating 1,307 variants.

**One caveat to state plainly:** inlining costs zero requests, so an external
sheet adds a round trip before first paint on a cold visit. That is the whole
argument for the status quo, and it is outweighed here — a reader of this site
opens many pages, and every page after the first pays nothing.

## 8d. Ian's queue, sent 2026-07-27 during the §3c work — NOT STARTED

Sent while the above was being built, with "do not allow it to interrupt".
Recorded verbatim in substance; none of it is started.

### Is `body` in Plex Mono the right default at all?

Ian: "I am dubious about setting the body font to Plex Mono, because I keep
finding spots where it is misapplied." His example is the **"Also on file"
section on the shows page**, whose leading prose is mono. His question is
whether mono should be the body default, or whether it should be applied to
**data classes, or a data parent class that data elements inherit from**.

**This is the general form of the bug §3c just fixed one instance of.** `.dek`
was mono for no reason anybody chose, and so was `due.html`'s standfirst, and
so is this. Every fix so far has been an opt-out bolted onto a default that is
wrong for prose — the site now has `.jam`, `.note`, `.aside-note`, `.prose`,
`.caveat` and `.dek` each independently saying "not mono, actually". Six
opt-outs is the shape of an inverted default.

Worth measuring before doing: count what is actually mono-by-decision (figures,
dates, setlist marks, labels, counts) against what is mono-by-inheritance. If
the first set is enumerable it wants a `.data`-style parent and a serif body,
which inverts the default and removes the whole class of bug. **Ian asked a
question here, not for the change** — bring him the measurement.

### The "Also on file" section — three things

The name itself is one of them: he wants **a better internal name** for this
category ("also on file" is clumsy to refer to, even if the words are fine on
the page). It is `split_archive()`'s second return value and covers soundchecks,
studio and TV/radio sessions — the entries phish.net does not count.

- **The heading is tiny.** Probably deliberate once; reads wrong to him now.
- **It ignores the search filter.** The section shows in full even when the
  show list is filtered. He half-defends this — it is a different category of
  data — but it feels wrong: "perhaps only data that passes the filter should
  appear", in either table. Note this interacts with §5's filter cost work and
  with the URL-state work in §4.
- **Its columns do not align.** Date, classification, details, flowing left to
  right and *almost* lining up. Two causes, both worth stating because the fix
  differs: the date is in a proportional face where the show table uses mono,
  so digit widths move the classification; and the classification is plain
  text of varying length ("session" against "soundcheck"), so the details
  column starts wherever the word ended. A grid with a `max-content` column
  fixes the second — the same fix §3c just used on the pairings block.

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
