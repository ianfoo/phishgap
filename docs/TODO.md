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

### Newest first: the 2026-07-30 session — "a one-off is not dormant"

**§2j is the whole of it, and it supersedes parts of §2f.** Ian read the
dormant page and objected that 126 of its 281 rows had been played exactly
once, which is not what "dormant" means. Measured against the archive's own
774 long silences, he is right and the effect is large: a song that fell quiet
after one play came back 28% of the time, after 8+ plays 84%. The page is now
three sections — **54 dormant, 53 rarities, 174 once or twice** — titled
*Out of rotation*, at the same URL.

Two things a fresh session should know:

- **`ROTATION_PLAYS = 8` is a separate constant from `MIN_HISTORY = 8`** on
  purpose. Same number, different meaning: one counts recent gaps and gates a
  verdict, the other counts plays ever and picks a noun. Tuning one must not
  move the other.
- **The sticky-header bug fixed in §2j was on `due.html` too**, and had been
  since §2. If another page grows a second `.lhead`, wrap each in its own
  parent or the first one pins for the rest of the document.

He then read the split and moved the bottom line himself: one and two plays are
one group (`FEW_PLAYS = 2`). The archive backs him — see §2j, second round.
Nothing is left open.

### The 2026-07-28 session, second sitting — everything here is pushed

Nothing is in flight. Working tree clean, `main` and `origin/gh-pages` agree,
and every item below was verified against the *published* tree rather than the
local build.

Ian drove this sitting almost entirely from the live site, in rounds. **The
pattern worth carrying forward: every time he said a figure looked wrong, it
was wrong** — four times, four real bugs. Measure before defending anything he
questions.

| § | what | state |
|---|---|---|
| 2b | The ten-year window travelled with each song, so the dormancy filter could never fire | done — 148 of 588 song pages changed |
| 2c | `site/data` reorganised; 711 reports under `data/shows/` | done, with a one-shot migration |
| 2d | "Due" reworked twice: a bustout ceiling, then measured against the **median** rather than the 85th percentile, plus a cadence floor | done — due 9 / slipping 26 / shelf 5 / dormant 283 |
| 2g | His due-page review: the "overdue" overload, the false bustout claim, `tabular-nums` missing from two sheets | done bar three items |
| 3e | FAQ index, back-links, the eras arithmetic; song front matter decluttered | done |
| 3f | Sticky column headers, and four list pages given headers at all | done |

### The 2026-07-28 session, third sitting — everything here is pushed

Run overnight while Ian slept, on his instruction to make provisional calls
where they are cheap to walk back and to skip anything that genuinely needs
him. **Working tree clean, eight commits on `main`, nothing in flight.**

| § | what | state |
|---|---|---|
| 8e.1 | Six named blocks now hold every rule all three sheets carried three copies of | done — sheets byte-identical after |
| 2i | The whole type scale a step up, from the root: body 14→15.75px, labels 10→11.25px, headings held | done — his largest open item |
| 2h | The three show-page details he spotted | done — all three |
| 2f | `dormant.html`, 284 songs by the year each was last heard | done — the last dead card on the site is a link |
| 7 | Method page: contents block from one list, and the bar moved next to the verdict it draws | done |
| 3d | The keyboard layer: `[`/`]`/`←`/`→`, a `?` overlay that reads its list off the page, a `Keys` button | done |
| 4 | Venue and tour on a show page are searches; `sitemap.xml` and `robots.txt` exist | done |

**The theme of the night: eight bugs, and six of them were already shipping.**
Every one was invisible until something moved into it. Full detail in the
sections, but the shape is worth carrying:

| what | how long it had been wrong |
|---|---|
| Every show page scrolled sideways above 620px — a `visibility:hidden` tooltip still lays out | since the phone-only fix for the same bug |
| That tooltip was 648px of unbreakable text, its end off the side of the page | since it was written |
| `.dek a` styled in one sheet of three — the due page's two standfirst links in browser blue | since the due page shipped |
| `.backtop` out-specified by `.prose p`, so every "All questions" link was set as prose | since the FAQ shipped |
| `since` measured from a date no page displays — **Midnight Rider read 90 shows where the honest figure is 1,234** | since `write_current` was written |
| `custom` is not a song: nine different pieces of music under one slug, every gap zero | since the archive had it |
| The index scrolled sideways at 375px on one 45-character song title | it was six pixels away before tonight |
| Venue and tour links came out in browser blue | caught before shipping, by measuring |

### The 2026-07-29 session — a live outage, found by Ian mid-show

Ian opened with "there is a show going on RIGHT NOW and there is nothing
happening on possumlogic". He was right, and the cause was a hole in the fix
for an earlier outage rather than anything new.

The watcher was healthy the whole time — gate `true`, resident job alive,
passes every five minutes. It was fetching a setlist from a six-hour cache
that had been poisoned by its own first pass. `--catch-up` bypassed the cache
only for shows in `recheck` (archived but still provisional); a show with no
report yet was never in it, which is every show on the night it is played. The
window opens at 23:00 UTC, the first song is posted around 23:30, so the first
pass reliably cached an empty setlist and every pass after it re-read that
emptiness. No report meant never provisional, meant never rechecked, meant
never refreshed.

| § | what | state |
|---|---|---|
| 0 | Setlist refreshed for a show with no report yet, not just one in `recheck` — the condition widened rather than replaced, so `--recheck` keeps working | done — `1cb640f59`, verified live |
| 0 | The counting-before-setlist hazard below | **open** |

Verified against the published tree, not the local build: the show archived
with its songs, `show/2026-07-29.html` live with "This show is being played
right now", an "ON STAGE NOW" banner on the index, and the invariant that
*exactly* the songs played that night read `since == 0` — six played, six
zeroed, nothing else zeroed.

**The open item, and it is a data-integrity one.** `--calendar` builds the
counting calendar from phish.net's show list, so it counts tonight's show as
soon as the API lists it. `--catch-up` fetches the setlist separately and can
fail. When it does, `current.json` advances anyway: on 2026-07-29 it went to
`as_of: 2026-07-29`, `shows: 2108`, and all 588 songs moved up one, with none
of the six actually played reset to zero. The root cause is fixed so the window
is now one pass instead of a whole show, but the two steps remain independent.
Options, cheapest first: hold `write_current` at the last calendar date that
has an archived report; or make `--calendar` add a date only once its setlist
is archived (but note the calendar entry is what puts the show at the top of the
index, so this would trade a wrong figure for a mis-sorted index). **Needs
Ian's call on which reading is more honest**, since holding the count means the
site says "counted through 2026-07-27" on a night a show is playing.

Two smaller things noticed and not acted on: the display name "Possum Logic" is
hardcoded in 24 template spots with no `SITE_NAME` constant, which is what a
rename would cost (the domain is already one constant with a `PL_DOMAIN`
override); and `recent_shows` filters on the UTC date, so a show is "already
played" from 00:00 UTC — fine today because the watch window gates it, but it
would mislead anything that called it without that gate.

### Same session, second round — two bugs off one screenshot

Ian sent a crop of the Fly Famous Mockingbird page and asked two things: why
the note text runs into the Before / after column, and why no before/after
songs are listed. They turned out to be unrelated, and the first one was not
what it looked like.

| § | what | state |
|---|---|---|
| 0 | `.stuck .in` was `max-width:960px` where `.wrap` is `60rem` | done — the note never overflowed; the *header* was 60px off its own columns |
| 0 | `nb=1` recorded "asked" for songs the fetched setlist never mentioned, so blank was permanent | done — extractor now reports every song it saw, empty entry included |
| 0 | 758 poisoned flags cleared and re-seeded | done — see the note below on what the re-seed exposed |

**The note never left its column.** Measured at nine widths from 830 to
1920px: the note fills the venue cell exactly and stops 20px short of `.nb`,
which is the column gap. What was wrong is that `.wrap` was converted from
`960px` to `60rem` so the measure would travel with the type scale — and
`.stuck .in`, which carries the sticky column labels, was left at the literal
`960px`. Content grew to 1080px, the bar held at 960, and every label landed
60px off the column it names. A long note then appeared to cross the
"Before / after" label while never touching that column. **The lesson is the
diagnosis, not the fix: the complaint was about the note and the bug was in the
header.** Measure the header against the row before believing a cell overflows.

**The re-seed exposed something bigger than the 758, and it is not what it
first looked like.** `--seed-setlists` builds its work list from every
performance lacking `nb`, and that came to **1966 dates** rather than the 601 I
had poisoned. I read that as "seeding was never finished" and said so; that was
wrong, and Ian caught it by asking the obvious question — how did we ever have
*any* neighbours if the setlists were not being fetched. Measured against the
pre-repair archive:

| performances | count |
|---|---|
| carry `prev`/`next` | 28,264 |
| carry the `nb` flag | 18,292 |
| **have the data but no flag** | **10,730** — 10,718 of them on dates the old index recorded as walked |
| have neither, on a walked date | 8,058 — genuinely "walked, no neighbour", flag lost |
| on a date never walked | ~78 |

So the setlists *had* been fetched, for 1,975 of about 2,100 dates. What was
lost was the record of it, and the loss has a precise cause. `nb` replaced an
older central index, `site/data/neighbours.json`, which listed walked dates and
was deleted by `acd87fb91` on 2026-07-26 when the migration ran. That migration
(possumlogic.py, the `if os.path.isfile(index)` block) sets `nb` **in memory**,
calls `os.remove(index)` immediately, and then writes files only through
`flush()` — which writes only the slugs the fetch loop put in `pending`. Every
song that run did not happen to re-fetch never had its migrated flag written to
disk, and the index was already gone. Had `todo` come out empty it would have
returned before writing anything at all. **It deleted the source of truth before
durably writing the replacement** — the same family as the rest, but the worst
instance, because the record was destroyed rather than merely stale. The
migration guard also skips any song with no neighbours anywhere, which is 395
songs, so none of those were ever flagged either.

The consequence is only wasted work, not wrong data: the re-seed re-asks ~1,966
dates that were mostly already answered and writes back the same values. After
it lands, `nb` is a true record of all 37,146 performances for the first time.
The migration block is now unreachable (no `neighbours.json` exists to trigger
it) but is still present and still carries the landmine — **worth deleting
outright, or at minimum writing every song before removing the index.**

**The new `absent` counter earned itself on its first run, with exactly one
hit.** Of 37,146 performances, one is not in the setlist phish.net returns for
its own date: `the-curtain` on 2026-07-27. That date's showdate response lists
only `the-curtain-with` ("The Curtain With") — but phish.net's *song-history*
endpoint for `the-curtain` returns that night too, so the archive has the same
performance filed under both slugs, and `the-curtain` carries a 2026-07-27 row
with a gap of 185 that is arguably not its own. Two phish.net endpoints
disagreeing about one performance. **Left alone deliberately** — deciding which
of their endpoints to believe is the same call as the `custom` slug in §0, and
it is Ian's. It stays unmarked, so every run re-asks and the counter keeps
reporting it, which is the behaviour I want from it.

Separately: `--seed-setlists` is a manual command and the daily workflow does
not pass it, so a newly archived show gets neighbours only when someone runs it
by hand — tonight's 2026-07-29 rows had none until this run. **Worth fixing** —
either add it to the daily run, or have `--catch-up` record neighbours for the
show it just fetched, since `build()` already holds that show's full setlist and
needs no extra call.

### Same session, third round — the agreed neighbour work, and the poller

Everything here is pushed. Working tree clean.

| § | what | state |
|---|---|---|
| 0 | The migration landmine deleted outright | done |
| next.1 | Set / show opener–closer labels | done — 3,821 terminals named |
| next.2 | Cross-boundary neighbours | done — 6,927 cross-set adjacencies shown |
| 0 | `--seed-setlists` walks `archive/setlist-order.json` first, buys only what it misses | done — the full re-walk cost 44 calls, not 2,009 |
| 0 | `--catch-up` records a new show's neighbours as it fetches it | done — no more blank column on the night |
| 0 | The live page polls instead of hoping; "last checked" reworded | done — all four paths driven in a browser |

**The archive paid for itself on its first use.** Re-walking all 2,009 shows
under new rules cost 44 API calls — the 43 dates the extract was missing, plus
tonight's. That is what `archive/README.md` promised and it held.

**But an extract is a cache with no expiry, and it had already gone stale in
the one place that matters.** The harvest ran mid-show, so it holds 2026-07-29
at the 12 songs it had at 19:53. Walking that back would have frozen the
running order of the one show whose running order was still moving — the same
shape as the six-hour cache that cost the first hour of that night, minus even
the six hours. A show whose report is still provisional is now always
re-fetched, and never written into the extract: its order is partial by
definition, and the day it settles a partial record stops being skipped and
starts being believed.

**The invariant, proved rather than sampled.** Of 37,148 walked performances,
every one carries exactly one before-state (`prev` / `xprev` / `first`) and
exactly one after-state (`next` / `xnext` / `last`) — 37,148 and 37,148, zero
violations. A blank cell now means one thing only: we have not walked that
setlist. That was the whole point of items 1 and 2.

**A seventh instance of the family, caught before it shipped.**
`save_song_history` carries neighbour fields forward across an API rewrite
through a hardcoded list of four key names. Adding four new fields elsewhere
would have left every one of them dropped on the next `--previous` run, in a
function nobody would think to open. The list is now one named constant,
`NB_CARRY`, next to the walk that produces it.

### "N new since you last looked" could not know that, and now can

Ian, on a screenshot: *"how can it know when I last looked? I went and
scrolled to the bottom and then back to the top and it still said this, so
right there, it's not true."* He was right, and the mechanism was dumber than
the words. `seen` is a row count in `localStorage`, it was written **at page
load**, and the tag was built once from it and never touched again. So the
sentence meant "since this browser last loaded a document for this show", and
the tag was a snapshot frozen at load — scrolling re-evaluated nothing.

**Making the reloads real is what exposed it.** Before the poller the meta
refresh never fired, the page almost never reloaded, and `seen > 0 &&
rows > seen` therefore almost never came true. The claim had been false all
along and nobody had been shown it often enough to notice.

One rule fixes it: **the stored count only ever advances to rows that have
actually been in view.** An IntersectionObserver on the last new row, with a
one-second dwell so a flick past the table does not count as looking, retires
the tag and banks the count at the same moment. Nothing is written at load
when there is something new to show.

**The first attempt was wrong in both directions and the first test caught
it.** It also banked on `visibilitychange` and `pagehide`, to stop an unread
page accumulating a claim. But a reload *fires* `pagehide`, so the count was
banked from the document being torn down, and rows in the next document that
the reader had still never seen were recorded as seen — two songs landing
without a scroll between them would report "1 new", not 2. Accumulation was
never the bug: if you never look at the new songs they are still new, and
saying so is the entire point of the tag.

Verified in a browser, all four paths: baseline 18 against 20 rows → tag
"2 new", two rows marked, **stored still 18**; the last new row scrolled into
view and held → tag gone, stored 20; back to the top → still gone, which is
exactly what he did and did not get; reload with nothing new → no tag, no
marks. Note for the next session: **the browser pane reports
`document.visibilityState: "hidden"` unless the tab is fronted**, and an
IntersectionObserver does not fire in a hidden document — the first run of
this test looked like a broken observer and was a broken harness. Front the
tab, then measure.

**And his second thought: the count should be the way there.** The tag is now
a link to the first new row. Every song row already carries its slug as an id
— `#character-zero` — so this is a real `href` to a real fragment rather than
a scripted scroll, which is the §2h ruling again: a fragment jump is
reversible with the Back button and a scroll is not. It points at the *first*
new row so the reader lands at the start of what they missed. `tabindex="-1"`
on the target, and `[tabindex="-1"]:focus{outline:none}` in `BASE_CSS`
already handles it correctly — a landing spot is a place, not a control. The
rows already carry `scroll-margin-top:46.8px`, so it clears the sticky header
without anything new.

`text-decoration:none` had to be said out loud. The chip's own `color` beats
the UA link colour so it was never going to come out browser blue, but it
would have come out underlined — the same family as the four links that have
shipped here wearing a default the author sheet never overrode.

**A harness limit worth recording**: a synthetic click in the browser pane
does **not** perform fragment navigation. Clicking the new link changed
nothing, and so did clicking the *pre-existing* `#suspicious-minds` link —
which is how it was shown to be the pane rather than the change. Verified
instead by resolving the fragment directly: scroll 0 → 2273, target at
`top:47` and in view, `document.activeElement` the row itself, no ring on it,
and the target confirmed to be the first `tr.fresh`.

### `footer{}` hoisted into `FOOTER_BOX_CSS`

Measured while checking whether hiding the Keys button would strand a footer
separator: the three `footer{…}` layout copies had become identical, though
`CLAUDE.md` had been telling sessions for a long time that they "differ by
real amounts". They now live in one named block beside `FOOTER_LINK_CSS`,
which they precede at all three call sites.

Proved a no-op rather than assumed. The built stylesheet of all nine page
types is identical to the pre-hoist build once whitespace is normalised, and
the raw diff of the whole site is **three continuation lines re-indented from
seven spaces to three**, in the two sheets that used seven — `song/*.html` is
byte-for-byte unchanged because its sheet already used three. No card was
redrawn and `cards.json` never moved.

That leaves `.crumb` (four occurrences, four genuinely different) and `.hero`
(flex against grid) as the real near-misses, plus the 32–46 rules that still
repeat pairwise. §8e.

### Three things Ian raised after the tag shipped

**A song slug is not necessarily a unique id.** He is right in principle, and
the show page already defends it: `render_html` numbers repeats, so a second
Character Zero in a night is `#character-zero-2` (possumlogic.py, the
`row_ids` / `seen_slugs` loop, with a comment saying exactly what he said).
The jump link uses `target.id` verbatim, so it inherits that. Measured across
all 712 show pages: **zero duplicate ids of any kind**, and no song slug
collides with the one static id a show page carries (`main`). It is currently
dormant — `build()` still drops repeats — which means **item 3 (reprises) is
what will first exercise it.** Check it lands correctly when that work starts.

**The Keys button showed on touch devices.** It is a discovery aid for keys a
phone does not have, offering "[ and ] to step between shows" to a reader who
cannot press either. Hidden under `@media (hover:none) and (pointer:coarse)`,
in `BASE_CSS` so it is said once for all eight page types. The `?` handler
stays bound, so an iPad with a keyboard attached still reaches the list.
**Not verified on a real touch device**: the browser pane reports
`pointer: fine` however narrow the viewport, so width is not the signal and
resizing proves nothing. What was verified is that the query parses (it
normalises rather than collapsing to `not all`), that the selector and
declaration do hide the button, and that the footer — a flex row with `gap`
and no separator characters — closes up with a 0px trailing gap. The iOS
simulator was the way to close this and Xcode is not selected on this machine.

**The jump could not be demonstrated end to end, and that is the harness.**
See the note in the tag section: a synthetic click does not perform fragment
navigation in the pane, and neither does a real `Enter` on the focused link,
and neither does clicking the *pre-existing* `#suspicious-minds` link. Real
Chrome was the other route and the extension is not connected. So what stands
proven is the target (`href` equals the first `tr.fresh` id, confirmed
identical), the resolution (setting the hash scrolls 0 → 2273, lands the row
at `top:47` clear of the sticky header, focuses it, no ring), and the link's
own semantics from the accessibility tree. The activation step itself is
unexercised. **The next live show is the real test.**

### Ian's idea: a `/live` endpoint, not a rebuilt page

Raised in the same message and explicitly parked by him — *"I know we'd have
to do something other than Github Actions for that."* The shape: the watcher
serves a live endpoint and the `.html` page redirects to it while an event is
on, so the reader is not waiting on a static publish at all. It would remove
the whole publish-latency floor (60–90s of Pages deploy on top of the polling
interval) that §0 records as "not a bug to chase". Worth keeping written down
as the answer to that floor if the hosting ever moves.

**And the push exposed one in the workflow — twice over, the same shape.**
The hourly job's "Commit the data archive" step ran a bare `git push` under
`bash -e`, so losing a race to the watcher killed the step, and with it the
*publish* step below — the site sat a build behind over a commit that had
already landed on `main`, and nothing in the failure said "publish did not
run". `watch.yml` has had the fix for a while: replay onto `origin/main`,
abort on conflict rather than publishing a tree with conflict markers inside
`site/data/shows/<date>.json`, and never treat a rejected push as fatal.
`possumlogic.yml` now has the same. **Twice tonight the rule lived in one of
two callers**: `--catch-up` knew to withhold `nb` mid-show and the seed did
not; the watcher knew to replay a rejected push and the hourly job did not.

**The rebase exposed a hole in the fix.** The watcher pushed mid-session and
`character-zero.json` conflicted — reading the conflict showed `seed_setlists`
still stamped `nb=1` and `last` unconditionally. `--catch-up` had the guard;
the seed did not, so a hand-run of `--seed-setlists` during a show would have
written "closed the show" onto whatever song was last at that moment and
marked the date answered — the one state no later run revisits. Both callers
now go through `apply_neighbours`, which owns the rule. **Two callers of the
same walk, and only one of them had been taught the rule.**

**Ian's note on the live banner, mid-session.** "This page refreshes itself"
is a separate idea from the counts and was running in after a middot, so it
wrapped after "this" — consistently, because that is simply where the measure
ran out. It has its own line now; `.live span:not(.since-you)` already makes
every span there a block, so it cost no CSS. One line each on desktop, two and
one at 375px. The remaining break is "this page was / built 1 minute ago",
which is mid-phrase but strands no separator — **his call whether that wants
its own line too.**

**Two typographic things, both found by looking rather than reasoning.** A
terminal line dropped the arrow slot and so hung two characters left of its
own sibling — visible on 3,821 rows; the arrow is now hidden rather than
removed. And the cross-boundary lines truncated mid-preposition at every
desktop width ("Opened set 3, af…" on 40 of Tweezer's 50), because the column
is 162px wide however wide the window is. Those lines now wrap, which cost 14
of that page's 418 rows a line and the page 0.7% of its height. Titles still
truncate: half a title is readable, half a preposition is not. Measured at
1280px across eight song pages — 610 edge labels, none truncated.

**What is still manual.** The extract only grows when `--seed-setlists` runs,
which the workflows do not call, so it falls behind by however many nights
since the last hand run. That is deliberate: it is a 3.4 MB single file, and
committing it nightly in CI would put a fresh 3.4 MB blob in git history every
day. `--catch-up` keeps the *reader-visible* data current on its own, so the
lag costs nothing until the neighbour rules change again — and then it costs
one call per un-archived night. If it is ever worth having CI maintain it,
shard it by year first (~160 KB a year) and add `archive` to the `git add` in
both workflows.

### Picked up next session — two left of the four agreed with Ian

Items 1 and 2 are done — see the round above. 3 and 4 are not started, and 3
still needs his call before anything is written.

1. ~~**Set / show opener–closer labels.**~~ **DONE.** Rendered as "Opened the
   show" / "Closed the show" for the two true terminals, which carry no song
   because there is none, and "Opened set 2" / "Closed the encore" for the
   rest, which do.
2. ~~**Cross-boundary neighbours.**~~ **DONE.** "Opened set 2, after Harry
   Hood" — label primary, in ink against the dim song, and no mark ever, so
   the page cannot imply a segue across a setbreak.
3. **Reprises.** 683 of 1,966 shows repeat a song; **972 performances are
   currently dropped**, because only the first occurrence per show is kept. Their
   neighbours differ from the first pass, so neighbour accuracy needs them.
   **Bring the cardinality question back to Ian before acting**: our 131 for Fly
   Famous Mockingbird matches phish.net's own "played 131 time(s)" headline while
   their table lists 143 rows, so adding rows diverges from their count and
   touches gap and "shows since". Treat *neighbour accuracy* as separable from
   *what counts as a performance*.
4. **Scarcity, as distinct from recency.** Ian's observation: Colonel Forbin's
   Ascent and Fly Famous Mockingbird are each **5 plays in ten years** yet
   correctly not bustouts, because both were played at the Sphere in April. 252
   of 588 songs have 1–8 plays in the last ten years and **40 of those were
   played in the last 90 days**. Bustout measures recency; this is scarcity, and
   the site has no vocabulary for it. §2d and the "under 8 plays in ten years"
   note already half-know this.

**No fetching required for 3.** `archive/setlist-order.json` holds the running
order of all 2,008 settled dates — set, position, slug, song, trans_mark — which
is everything reprises need. See `archive/README.md`.

### ~~Also open: the live page does not auto-refresh~~ DONE 2026-07-30

Two separate faults, found together on 2026-07-29, both fixed.

**The label was misattributed, not wrong.** `checked = _utcnow()` is stamped at
*render* time and `AGO_JS` recounts it client-side every 20s, so a stale document
faithfully reports **its own age** — it was the only honest thing on Ian's stale
page. But "last checked" read as a claim about the server. It now says "this
page was built <em>4 minutes ago</em> · it updates as songs land", which is what
the stamp measures and what the page now does.

**The refresh did not fire.** `<meta http-equiv="refresh" content="120">` was
present, well-formed and correctly placed. It failed twice over: Pages sends
`cache-control: max-age=600`, so a reload inside ten minutes can be satisfied
from cache; and browsers throttle or defer meta refresh in background tabs,
unboundedly. Ian hit refresh by hand and the setlist **jumped five songs** —
about 25 minutes of drift, past the cache window, so it was not firing at all.

Replaced by `LIVE_JS`, which fetches `data/shows/<date>.json` with a changing
query string — its own CDN cache key, which is what defeats both caches —
and reloads **only** when the song count moves or the show settles. It does not
poll while the tab is hidden; `visibilitychange` brings it up to date the moment
the reader looks back, which is sooner than any interval. All four paths were
driven in a browser against the real report file: no change → one fetch, no
reload; a song added → one reload, `sessionStorage` marked; dispatched again
against a document now genuinely stale → **no second reload**, which is the
guard against a reload storm on a reader's phone; `provisional` flipped false →
reload. Note the shape: the same "**anything long-running must re-read its
inputs each pass**" lesson as the outages in `CLAUDE.md`, now on the client. The
page was a long-running thing that reloaded on a timer and hoped.

### Same session, fourth round — the band is measured on a log scale now

Ian, from the 2026-07-29 show page: "This median range is WILD… it gives a song
a really wide berth to being considered *expected*. Perhaps we should use some
sort of scaling math to shrink the range as the rarity of a song goes up." He
also guessed standard deviation was involved somewhere. Both instincts pointed
at something real; neither was the mechanism.

**The test that settled it, and the one to reuse.** Replay every rateable
performance in the archive, build the band from that song's *earlier* gaps only,
then check it against the gap that actually followed. A band that says "usually"
should contain the next gap about 70% of the time; where it holds more than
that it is too generous, and where it holds less it is claiming more than it can.
32,605 performances, no API calls.

**Scaling by rarity would have been backwards.** Coverage *fell* as songs got
rarer — 76% for staples down to 44% for the rarest — so the rare bands were
already too narrow, and the wide bands he was looking at belong to songs whose
spread is large relative to their own median, which is nearly independent of
rarity. Ordinary mean ± SD is worse than the percentiles: 78% coverage against a
nominal 68%, and a low end at or below zero on 38% of rows.

**What shipped**: the band is the spread of *log* gaps, exponentiated — a ratio
around the song's typical gap rather than a fixed number of shows either side.
`gap_band()` is now the single definition, replacing four independent
`_quantile(recent, BAND[…])` call sites (report row, song page figure, that
page's `data-high`, due page gate); `_quantile` is gone with them. `BAND` still
means "the middle 70%" and `BAND_K` is the matching z-score, so the phrase stays
literally what is computed.

| | staples → rarest | premature / expected / overdue |
|---|---|---|
| percentiles | 76% → 44% | 6.5 / 72.2 / 21.4 |
| log scale | 70% → 49% | 9.3 / 69.1 / 21.7 |

Overdue barely moved, which is what keeps §2d's tuning note intact.

**Second half, for clarity rather than data**: some songs do two things, and one
range describes neither. `layoff_break()` finds a clean break above the median
and the row says the second thing in words — Esther reads "usually 8 to 58, but
3 of its last 12 gaps ran 68 or longer". Fires on 10.8% of performances, 9 of
214 songs today, carried on the row as `gap_away` because the renderer sees the
row and not the history. Not added to song pages: they draw the band and never
state it in words, so it would have meant a new paragraph on all 588 pages to
reach nine.

**Verified**: 712 show pages replayed against their data with 0 tooltip
mismatches; all 11,938 archived bands and 370 clauses recomputed from song
histories with 0 disagreements; real hover in light and dark; no horizontal
overflow at 375 or 1280. Due page moved 43 → 39 rows (11 → 10 due, 27 → 24
slipping), and all six moves were checked by hand.

**Stale wording elsewhere in this file.** §2, §2b and §2d describe the gate as
"the 85th percentile", which was true when they were written and is not now —
the figure is the same gate, computed differently. Left as history rather than
rewritten, but do not design against the phrase; CLAUDE.md's warning about a
stale constraint being more expensive than a missing one applies to this file.

**Also, and unrelated to the change**: `.claude/launch.json` hardcoded port 8769
with no `autoPort`, so a second worktree could not serve the site at all — and
the server already running on 8769 belonged to another worktree and served the
*old* build. Verifying against it would have shown this change as missing.
Now `autoPort: true` with the port taken from `$PORT`.

### The three biggest open things, in the order I would take them

1. **§2e/§2f graphs.** Ian wants them and named the best one himself (a song's
   trajectory, §2e item 1). Both it and the catalogue-wide charts need the same
   missing capability — evaluating the §2d classification **as of a past
   date** — so build that first and the charts fall out of it. **This is now
   the largest thing he has asked for that has not been started.**
2. **§8e.2 — link one `site.css` instead of inlining a sheet into 1,307
   pages.** Measured at 45.6 MB, 39% of all HTML on the site; a show page would
   go 62 KB → ~29 KB. §8e.1 is done, nothing is in the way, and the note there
   says so.
3. **§3b, the older agreed work**, still none of it started — and note that the
   rename of "reports" is in it. That one is **skipped rather than deferred**:
   see the open questions below.

Then: §6 card visuals, §5 benchmark, and §4's leaderboard / on-this-day /
random show / feed.

### Two habits this file has now paid for many times

- **A rule written into one stylesheet of three is invisible until something
  leans on it.** §8e.1 has now named the rules all three shared, so that class
  is closed for those — but **32–46 rules still repeat pairwise**, and tonight
  added two more instances of the bug (`.dek a`, and the masthead links, the
  second caught before shipping). Six now.
- **A rule that is typed is not a rule that is drawn.** `.backtop` was in the
  sheet, reasoned about in a comment, and had never once applied. Read the
  computed style, not the stylesheet.
- **Programmatic focus is not focus.** Reading a skip link's colour after
  `element.focus()` reported browser blue on all eight page types tonight. A
  real Tab press showed it was correct all along.

### In flight when the *first* sitting ended (historical)

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

### The older queue, after the three above

1. **§6 remaining visual work** — cards have no grain and use a plain rule
   where pages use `.rule2`; the card mark is invisible at thumbnail size.
   **Left alone deliberately tonight**: changing card markup means redrawing
   588 PNGs, and §8g's trap is that drawing them locally writes "already drawn"
   into a file that ships and CI then draws nothing. Do this where the drawing
   can be checked.
2. **§5 `content-visibility` benchmark** — method written down, needs doing
   properly rather than in one live page.
3. **§3b** — the older agreed work. Still none of it started, and one item in
   it is now explicitly **skipped for want of his input** (see below).
4. **§4** — bustout leaderboard, on this day, random show, a feed.

§3c, §3d, §3e, §3f and §7 are done — see those sections.

### What the 2026-07-27 session added

§3c, all four items, plus the nav regression it exposed (§8c) and the same
segue hole on the method page. New page: `faq.html`, reached from a
**Questions** nav item on all eight page types. Verified in a browser rather
than from markup — Literata measured by advance width, nav hit areas re-checked
across every page type at 375px, pairing alignment across eight viewport
widths, and every link and anchor resolved. Ian's mid-session queue is §8d.

### Skipped tonight because it genuinely needs him

- **§3b, renaming "reports".** He raised it and it is not cosmetic to him, but
  §3b's own instruction is "pick the replacement once and change it in one
  pass — a half-renamed vocabulary is worse than the old one", and the word
  reaches `SHOW_DIR`, `saved_reports()`, `REPORT_NAME`, `report_card()`,
  `render_html`'s docstrings, the index hero label and subtitle, `--catch-up`'s
  output, `publish.sh`'s tally and the pager's aria-labels. A rename across a
  dozen identifiers and two shell scripts is **not cheap to walk back**, which
  is the test he set for making a call without him. **The only thing missing is
  the word.** Say it and the pass is an hour.

### Open questions waiting on Ian, none of them blocking

- **§2d, The Howling.** He named it as due at 36 shows; it lands in *slipping*
  at 5.1× a typical gap of 7. He hedged on it in the same breath. `DUE_MULTIPLE`
  (3.5) is the one number that moves it — 5.5 would bring it in along with
  Winterqueen, The Line and I Always Wanted It This Way.
- **§2g, the name "Slipping".** Mine, not his. It exists because "overdue" was
  already taken by the per-performance verdict; any word that is not "overdue"
  will do.
- **§2g, the masthead's three faces.** Ruled to keep Bagnard / mono caps /
  Literata, with the reasoning written down. He asked for a call and may
  disagree with it.
- A **festival/event name** for the 35 shows phish.net files as "Not Part of a
  Tour" (§6). Needs a curated table; his call.
- Whether the `MOST SONGS` fact wants a **"show length" or "highest rated"
  view** beyond the sort options (§8b.7).

### The calls made overnight on 2026-07-28, for the same batch

Each is one line, one string or one threshold, and each is in its own section
with the reasoning. Listed here so the batch is in one place.

| call | where | to reverse |
|---|---|---|
| The type scale went **up one step from the root** (112.5%), and the `h1` clamps were pulled back so headings hold their size | §2i | one declaration; the clamps are exact reciprocals |
| `.dek` got **its own step** on top of that, so a standfirst is larger than the body it introduces | §2i | one value in `DEK_CSS` |
| The stray `→` on a show row is **`↗`**, not deleted — it was signalling something real | §2h | one character |
| A show row's landing spot is **marked** rather than given a link back: a fragment jump is reversible by the browser, a scroll is not | §2h | delete two rules |
| `dormant.html` is **not in the nav** — its doors are the due page and the FAQ | §2f | one nav item |
| Dormant figures are set **in ink, not the accent** | §2f | one rule |
| ~~Dormant is ordered **by year last heard**, then by all-time plays~~ — superseded 2026-07-30: it is now split into three kinds first, and ordered by year *inside* each. See §2j | §2j | — |
| The dormant/rarity line is **8 plays**, its own constant rather than `MIN_HISTORY` | §2j | one constant |
| The page is titled **Out of rotation**; the URL stays `dormant.html` | §2j | one string |
| `.backtop` now renders as the **mono control it was always written to be** — this changes the look of a page he has reviewed | §7 | revert one selector |
| A tour whose name is inside another tour's name is **left unlinked** rather than linking to the wrong shows | §4 | delete `ambiguous_tours` |
| The sitemap carries **no `<lastmod>`** | §4 | add one field |


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

**The fourth row is out of date and is left as written.** It is a record of
what the page said on 2026-07-28. As of 2026-07-30 that 283 is 281 and is no
longer one category: 54 dormant, 53 rarities, 174 once-or-twice, and the due page's
hero cell counts only the 54. See §2j.

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

## 2g. Ian's due-page review, 2026-07-28 — mostly DONE, three open

Fixed in the same pass:

- **"Overdue" was overloaded.** He caught it: show pages already stamp a
  *performance* overdue when its gap passed the 85th percentile, and the due
  page had taken the word for a *category*. They are not the same claim, and
  every song on the due page — both lists — would be stamped overdue if it
  turned up tonight, so the word cannot also name one of the lists. The
  section is **Slipping** now. **[ruling] the name is mine and is cheap to
  change**; what matters is that it is not "overdue".
- **"usually every 5.5" beside "93 shows"** was two numbers arguing in one
  row. Reads `usual gap 5.5` now — a noun, not a claim about the present —
  and the Slipping section says outright that for a song this far past it,
  that figure is the schedule it *was* on.
- **The bustout claim was false and the method page stated it flatly.** "A gap
  of 100 or more is a bustout regardless of everything above" — it is not.
  Bustout is the `elif` branch in `_classify`: it fires only where a song has
  *no* recent record. Measured: of **335** performances with a gap ≥ 100,
  **293** are bustouts and **42** are not — Crowd Control came back after 122
  shows and Nellie Kane after 146, both marked overdue, both still in
  rotation. Method page, FAQ and the shelf blurb all corrected.
- **Decimals overhanging the row edge on iPhone**, and the cause was not the
  decimal. `white-space:nowrap` plus a 17-character caption in a 7rem column
  overflowed; the shorter label fits. But the real find underneath:
  **`font-variant-numeric:tabular-nums` was in `CSS` only**, so the index,
  songs, due, venues and *every song page* had been setting their figures in
  proportional digits. Fourth instance of the §8c one-sheet-of-three bug. All
  40 rows now share a single right edge, measured.
- **Back to top from every section.** He has asked for this three times now
  (FAQ answers, and here), so it is a house idiom in `.backtop` rather than a
  page's trick. **The general problem is worth stating: this site jumps a
  reader somewhere and maroons them.** Any new anchor target should ship with
  its way back.
- **Section headings were barely larger than the rows they headed** (1.5rem
  over 1rem). Now 2.125rem.
- **A nod to themed nights.** His point: "MSG in 5" is playing nothing newer
  than the 1990s, and the 2021 Halloween runs and the Sphere elements nights
  did the same thing. The figures cannot know, and the page now says so.

### Still open from that review

- ~~**Type size, site-wide.**~~ **DONE 2026-07-28.** See §2i below — it grew
  large enough to want its own section, and it found five bugs on the way.
- **[ruling] The masthead's three faces stay as they are.** He asked for a
  design call: `h1` in Bagnard, subtitle in large mono caps, prose in
  Literata, and "a designer might have a fit". The call is to keep it, and the
  reasoning is that the subtitle is **not prose** — it is a derived figure
  ("9 songs you might reasonably expect tonight"), the same kind of thing as
  the column headers and the hero labels, and mono caps is the voice this site
  gives every one of those. Bagnard is deliberately confined to three slots
  (the wordmark, a show's date, a song's name); a fourth dilutes the one face
  that is the site's identity. Literata would put the subtitle in the same
  voice as the paragraph directly beneath it, which is the one place it must
  not be. **He is right about the cause, though** — the reason it feels
  arbitrary is that mono is the *default* rather than a choice, which is
  exactly §8d's open question. Settle that and this stops being a question.
- **Dormant needs somewhere to go.** Its hero cell states 283 and links
  nowhere. See §2f.

## 2i. The type scale, site-wide — Ian's largest ask. DONE 2026-07-28

Ian: "the prose text feels small even by these standards… I feel this way on
iPhone and on desktop… I think an accessibility review of the entire site is in
order soon."

**Stated once rather than as 300 edited declarations.** Everything on this site
was already sized in `rem`, so the whole scale moves from the root:
`html{font-size:112.5%}` in `BASE_CSS`. Nothing can drift out of proportion
with anything else, and it is relative rather than absolute — a reader whose
browser is set to 20px gets 22.5, not 18.

| | before | after | |
|---|---|---|---|
| root | 16px | **18px** | |
| `body` — every row, cell and paragraph | 14px | **15.75px** | |
| `.lbl` / `.crumb` / `.lhead` — the labels | 10px | **11.25px** | 101 declarations, the most-used size on the site |
| footer, captions | 12px | **13.5px** | |
| `.dek` — the standfirst | 13px | **16.875px** | its own step; see below |
| `.num` — hero figures | 36px | 40.5px | |
| `h1` | 64px | **64px** | held deliberately |
| `.wrap` | 960px | 1080px (`60rem`) | |

- **The top of the scale is held, not lifted.** The three `h1` clamps have their
  rem endpoints divided by exactly 1.125, so every heading renders at the pixel
  size it did before at every viewport width — measured, 64px → 64.0008px. A
  wordmark at 64px was never the complaint. A scale should compress at the
  display end and open at the reading end.
- **`.dek` is the one size that does not simply ride the lift.** A standfirst
  introduces the body text under it, and this one was set *smaller* than that
  text — 13px over 14 — so it apologised for the thing it announced. It is a
  step above body now, with `opsz` moved 12 → 16 to follow the point size.
- **The measure is in rem too.** `max-width:960px` would have held still while
  the type went up a step, which is the same page with less room in it.

### It found five bugs, and three of them were already shipping

Every one was invisible until the type grew into it. **The pattern is worth
carrying: a layout tuned to fit is a layout six pixels from not fitting**, and
nothing tells you which until something moves.

1. **Every show page has been scrollable sideways on desktop.** `[data-tip]`'s
   tooltip is `position:absolute` and `white-space:nowrap`, hidden with
   `visibility:hidden` — which still takes part in layout. This was found once
   before and fixed *only for phones*, by dropping the tooltip below 620px; so
   above 620px it kept doing exactly what the comment says it used to do.
   Measured on the live build at 1280px: **1,627px of scroll width, a page that
   slid 347px into nothing.** Fixed with `html,body{overflow-x:clip}` — `clip`
   rather than `hidden` because `hidden` would make the body a scroll container
   and break every `position:sticky` header on the site.
   - **On `html` as well as `body`, and that is not belt and braces.** An
     overflow set on `body` alone is *propagated* to the viewport and `body` is
     then treated as `visible`, so the first attempt shipped the rule and
     changed nothing. The check caught it because it re-measured rather than
     re-reading the CSS.
2. **The tooltip was 648px of unbreakable text.** The sentence a song with no
   range bar carries could not fit any viewport under about 1,600px, so its end
   was off the side of the page. It wraps now (`width:max-content` up to
   `min(24rem,100vw - 3rem)`), and both right-hand columns hang their tips the
   other way. Checked at 700/820/1100/1400px: every tooltip on the page is fully
   on screen, where before the clip they were unreachable and after it they
   would have been cut.
3. **The index scrolled sideways at 375px.** `.r-top` keeps `white-space:nowrap`
   in the narrow layout, where it is an inline run rather than a column with an
   ellipsis. "She Caught the Katy and Left Me a Mule to Ride" is 45 characters —
   344px of mono at the old size, 389px at the new. The page was **six pixels**
   from scrolling before this change and 33 past it after.
4. **The venues rows could not fit their own labels.** The narrow layout gives
   the figures a fixed `5.5rem`, cut to fit "longest 1,468" at the old scale:
   99px of column for 106px of label. It is `max-content` now, and below 400px
   the row stacks — the left column has a hard 217px floor (a date range that
   must not break) and 320px does not have 217 + 106 to give.
5. **`.dek a` was styled in one sheet of three** — the fifth instance. The due
   page's standfirst has the only two links of their kind on the site
   ("slipping", "on the shelf"), and both rendered in **the browser's default
   link blue with a browser underline**. Folded into `DEK_CSS`, so there is now
   one place to say it. Checked afterwards across all eight page types: of
   2,103 links, none resolves to a browser default colour.

### What was re-checked afterwards, and held

- **No page scrolls sideways** at 320, 375, 414, 620, 820 or 1400px — six root
  pages, three shows and three songs, twelve pages × six widths.
- **Sticky headers still hand off.** `overflow-x:clip` does not create a scroll
  container, and the proof is behavioural: on a show page exactly one table's
  header row is stuck at a time, and it changes over as you scroll.
- **The skip link still lands clear of the sticky header** — first row top 47px,
  header bottom 47px, on the due page at the new scale.
- **Nav hit areas** on all eight page types at 375px: every one still 24×24 or
  better, none overlapping.
- One measurement of my own was wrong first time and is worth recording, since
  the file already warns about it: reading the skip link's colour with
  `element.focus()` reported browser blue on all eight page types. A real Tab
  press showed it correctly — `--ink` on `--paper`, 163×43, with the hot ring.
  **Programmatic focus is not focus.**

## 2h. Three things Ian noticed elsewhere, 2026-07-28. DONE

- ~~**A stray `&rarr;` on the phone layout of a show page**~~, after the "Last
  performed" label. Ian: the arrow means something specific in a setlist —
  songs running together — so a decorative one next to data is actively
  misleading. He is right, and the mark was borrowed from the hero cards, where
  it is fine because no hero card sits above a setlist.
  - **[ruling] it is `&nearr;` (↗) now, not nothing.** The arrow was solving a
    real problem — §7's "a tap in `td.last` goes to the previous show and a tap
    elsewhere goes to the song page, with only a 2px border to say so" — so
    deleting it would trade a misleading mark for no mark. A north-east arrow
    is not setlist notation, and it says "leaves this row" rather than "runs
    into the next one". One character if he wants it gone.
- ~~**The gap column has no label on the phone layout.**~~ It carries a `Gap`
  cap now, hidden above 620px exactly the way `.last`'s own cap is, because
  above 620px the `<th>` does the naming. The largest figure in the row was the
  only thing on it that never said what it was.
- ~~**The `LONGEST GAP` hero should link to the row it is about.**~~ Done, and
  **the note above was wrong to assume the anchor existed** — it says to check,
  and checking was the whole job: song rows had no `id` at all, so nothing on a
  show page could be linked to.
  - Every song row carries one now. **The slug alone is not enough**: a song can
    appear twice in a night, and two elements with one id is a document where
    half the links go somewhere else. Repeats are numbered. Asserted across all
    711 show pages: **0 with a duplicate row id, 0 hero links pointing at an id
    that is not there.**
  - The card is an `<a>` with a **down** arrow rather than the index's right
    one, because it leads down this page rather than out to another — and
    because a right arrow on a show page is the mark discussed above.
  - **[ruling] the landing is marked rather than given a link back.** The row
    you arrive at is tinted and carries a hot inset bar, so it is obvious you
    got there. It does not get the `.backtop` treatment the FAQ answers have:
    this is a fragment navigation, which the browser's back button genuinely
    reverses, where a scroll is not. Verified by following the link: the row
    lands at 46px with the sticky header's bottom at 34px, clear of it.

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

1. **A song's trajectory — Ian's own idea, 2026-07-28**, and the best on this
   list: "the song's trajectory over the years, in terms of play frequency.
   You can see where a song slipped into being shelved and then into
   dormancy." One chart per song page: plays per year, with the §2d bands
   drawn behind it, so the moment a song stopped being in rotation is visible
   rather than inferred. It is the picture of the classification this session
   spent its time getting right, and it needs the same thing §2f needs — the
   ability to evaluate that classification **as of a past date** — so build
   that once and both this and the catalogue-wide charts fall out of it.
   Related, simpler, and worth doing first as a warm-up: a **heartbeat strip**,
   one tick per performance across the song's whole life, era-banded behind.
   McGrupp reads 101 / 1 / 13 / 9 by era in prose today; a strip shows it
   instantly.
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

## 2f. The dormant songs should be explorable — Ian, 2026-07-28. PAGE DONE

**`dormant.html` shipped 2026-07-28**, and the hero cell on `due.html` that
stated a figure and led nowhere now leads here. The three *charts* in this
section are still open and still want the "classify as of a past date"
capability described at the end.

**Read §2j before this section.** On 2026-07-30 the page was split three ways
and retitled, which makes several statements below stale: the year strip is
gone, "284 songs grouped by year" is now 281 songs in three parts each grouped
by year, and the count on the due page's hero cell is 54 rather than the whole
list. The paragraphs are left as the record of what shipped that night.

### What landed

- **284 songs, grouped by the year each was last heard, newest first.** Within
  a year they are ordered by how often the band ever played it, so a year opens
  on the staple that stopped and ends on the cover played once. That order is
  not a preference — a dormant song has **no percentile to rank by**, which is
  the definition of dormant, so the only figures available are when and how
  often.
- **The headline figure per row is all-time plays**, not shows-since. 126 of
  the 284 were played exactly once, mostly one-off covers from the 2016
  Halloween Bowie set and the 2017 LP-replay run; without that figure a reader
  takes 284 for 284 songs that used to be in rotation, which is not what this
  page is. The caption carries shows-since and the song's span (`1990–2017`).
- **It reuses the due page's row grid wholesale** — `.d-song`, `.d-last`,
  `.d-n`, `.typ`, and how they stack on a phone — so the new CSS is only what
  the due page has no use for: the year headings and the strip of years at the
  top. Asserted in the browser: the column header's computed
  `grid-template-columns` is identical to a row's.
- The year strip and the year headings come from **one grouping**, the way the
  FAQ's contents block does, so the strip cannot offer a year the page has not
  got. Every heading carries **↑ Top**, which is the house idiom by now.
- **[ruling] it is not in the nav.** Seven items is a lot for a row that
  already broke once at six (§8c), and Ian's own framing was that this is the
  fourth list on the due page. Its doors are the due page's hero cell, two
  links in that page's prose, and the FAQ's "what does due mean" answer. If it
  feels buried, the fix is one nav item.
- **[ruling] the figures are set in ink, not the accent.** The due page sets
  its figure hot because it is sounding an alarm and because it is the order
  the list is in. Neither is true here, and 284 rows shouting in the accent
  colour spends it on everything.

### Building it found two wrong figures, both shipping

`due_rows` returned only a *count* for dormant, so the first job was making it
return which songs. What came back was not entirely songs.

- **`custom` is not a song, and it was about to headline the page.** It sorted
  first on LONGEST GONE — the loudest figure on a new page. phish.net files
  one-off and unlisted titles under it: nine performances, nine different
  pieces of music in the notes (Me and Bobby McGee, Magilla, Mountain Dew,
  Goodbye Jam, What's The Use?, Dog Log, and a Devil With a Blue Dress On jam),
  every gap zero. **Structurally the same entry as `jam`**, which `NOT_A_SONG`
  has excluded all along; this one had simply never been ranked first by
  anything. Now excluded, with the same caveat on its own page.
- **`since` was measured from a date no page displays.** `write_current()`
  computed shows-since from each song's raw last performance, while everything
  that prints a last-played date filters to the counting calendar first — a
  soundcheck is not a night the band played. Five songs of 588 diverged, and
  not by a little:

  | song | was | is | its newest row |
  |---|---|---|---|
  | Midnight Rider | 90 | **1,234** | 2024-08-14 soundcheck |
  | Stairway to Heaven | 90 | **598** | 2024-08-14 soundcheck |
  | Windora Bug | 251 | **769** | 2020-02-19 soundcheck |
  | Jam | 28 | **457** | 2026-01-27 Moon Palace |
  | custom | 661 | **1,004** | 2009-10-29 |

  Midnight Rider's own page has always said "Last played 1994-06-22"; the live
  figure beside it said 90 shows, off by **1,144**. Exactly the shape the
  archive's own rule is for — a wrong figure is worse than a missing one — and
  it was found only because a new page happened to sort on it.
- The correction moves two songs into dormancy (they were under the 100-show
  line on the old figure) and `custom` out of it: **283 → 284**. The due page's
  hero cell and the length of this page are one `due_rows()` call apart, so
  they cannot disagree.

### Verified

No sideways scroll at 320/375/414/620/820/1100/1400. Header grid identical to
row grid. `.lhead` sticky, and a year anchor lands at 47px with its bottom at
34px — clear of it. Every internal link on all seven root pages resolves to a
file that exists.

### Ian's original words, and what is still open

His words: "We should allow the users to explore dormant songs. There's some
nostalgia and discovery in there." He floated "its own page because of the
length? or maybe a collapsible section, which is a language we don't have on
this site (yet)." A page, and no new interaction idiom for one use.

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

## 2j. A one-off is not dormant — Ian, 2026-07-30. DONE

His words, reading the page shipped in §2f: "A bunch of the songs on this list
have been played once. I don't think it's fair to call a one-off 'dormant.'
Dormancy implies that it was once not dormant, but many songs that get played
once will never be played again." And on the MSG bustouts: "a lot of the 1,000+
performance gaps we saw closed this week will open up new indefinite gaps
again, and we'll never see those songs performed again."

He was right, and 45% of the page was the problem: **126 of 281 rows had been
played exactly once, ever**, and 42 of those 126 were played on a Halloween
night as part of a costume set — performed once by design, with no rotation to
fall out of.

### The archive picks the line, not taste

Every silence of `BUSTOUT_GAP` or more in the archive — **774** of them —
grouped by plays-at-the-time and scored on whether it was ever ended:

| plays when it fell quiet | silences | ever came back |
|---|---:|---:|
| 1 | 176 | **28%** |
| 2 | 72 | 33% |
| 3 | 40 | 62% |
| 4 | 37 | 68% |
| 5–7 | 76 | 66% |
| 8–15 | 104 | 70% |
| 16–40 | 120 | 85% |
| 41+ | 149 | **93%** |

Conditioned on silences that already reached 300 shows — where this page lives,
its median row gone 490 — the three groups read **75% / 43% / 20%**. A one-off
is the only kind that is likelier to stay gone than to return.

**Eleven rules were measured against the same outcome.** Raw play count won at
49 points of separation; `3+ in any 50 shows` and `3+ in any 200 shows` tied at
48 and cost a concept; **`span >= 100 shows` was worst at 34**. Whether a song
was ever in rotation is answered by how many times they played it, not by how
long they had it lying around. `ROTATION_PLAYS = 8` carries this.

### His MSG worry is a different population — worth telling him

22 songs returned 2026-07-20..29 from a 100+ show silence, and **21 of them had
8 or more plays first**: Sweet Adeline 176, The Curtain 124, Glide 117,
Makisupa 109, Big Ball Jam 103, Love You 94, La Grange 83, Highway to Hell 78,
Harpua 67, Drowned 49, Cold as Ice 48. Only Back in the U.S.S.R. (4) is a
rarity. When these re-open their gaps they will be **correctly** called dormant.
The one-off problem and the callback problem barely overlap.

### The callback is an event, not a fourth category — [ruling]

He asked how to handle a song called back for one night. It gets no new name:
the play count already carries it, and a second performance still is not a
rotation. It is also not a coin toss. Of returns from a 300+ show silence that
have since had 300+ shows of chance, the ones played **once** before went quiet
again for good **43%** of the time; 2–7 before, **27%**; 8+ before, **7%**.
Baby Lemonade, Bohemian Rhapsody, Jungle Boogie and Theme from New York, New
York are all 2-play New Year's callbacks still silent, and all now sit under
Rarities rather than Dormant.

### What landed

- **`rotation_split()` beside `due_rows()`**, for the reason `due_rows` itself
  is shared: the page and the due page's hero cell come from one call, so they
  cannot disagree about how many songs are dormant.
- **Three sections on one page** (his choice, offered against separate pages
  and a filter), each with its own year grouping and anchored year ids —
  `#dormant-2019` rather than `#y2019`, because a year appears in all three.
- **Retitled *Out of rotation*; URL stays `dormant.html`** so nothing that
  links here breaks.
- **The due page's Dormant cell now counts 54, not 281,** and links to
  `#dormant` rather than the page top, so the figure and what it lands on are
  the same set. Its tail sentence names all three.
- **A `rotation` section on the method page** carrying the table above, and the
  FAQ's fourth definition renamed and extended.
- **Song pages stamp `one-off` / `played twice` / `rarity` / `dormant`** from
  the same constants,
  via new `data-plays` and `data-rotation`. The box outlives any one list, so
  fixing only the page would have left the word loose on 126 song pages.
- **The section strip was built and then removed.** Eighteen years needed a
  jump strip; three sections do not, and the hero directly under it already
  named, counted and linked all three — two rows saying the same three numbers
  a line apart.

### It found a live layout bug on a page Ian has reviewed

`.lhead` is `position:sticky; top:0`, and a sticky element is held by its
**parent**. All three column headers shared `#main`, so each stayed pinned for
the whole rest of the page: scrolling into Rarities showed the Dormant header
ruled straight across the word "Rarities". **`due.html` had this first** — its
three headers all shared `.wrap` — and it has been shipping since §2 with 43
rows to hide it. Both fixed by giving each section its own wrapper.

### Verified

- 54 + 101 + 126 = 281, and **every row's printed play count satisfies its own
  section's rule** — dormant min 8, rarities 3–7, once-or-twice 1 or 2, zero
  violations. Not three examples: all 281.
- **All 281 song pages agree with the section their song is in**, and all 589
  carry `data-plays`. `sanity` → dormant, `the-connection` → rarity,
  `baby-lemonade` → played twice, `and-flew-away` → one-off, read out of the
  live DOM after the fetch.
- No duplicate ids on the page. Sticky headers release at their section end
  (measured: tops −11555, −58, 256 rather than 0, 0, 0).
- Rendered and screenshotted in **both themes**, desktop and 390px. No sideways
  scroll on mobile (`scrollWidth` 390 = `innerWidth`).

### Second round, same day — Ian moved the bottom line, and was right

He kept 8 for the rotation line ("the line for having a rotation at 8 does seem
to make sense") and rejected the bottom one: *"We can't call two a 'one shot' …
but for most intents and purposes, they should probably be grouped with the one
shots."*

**Measured, and merging is the better cut.** Splitting 1 / 2–7 / 8+ the three
groups ever came back **28% / 55% / 84%**; splitting 1–2 / 3–7 / 8+ they come
back **30% / 65% / 84%**. The gap at the bottom boundary widens from 27 points
to 35 and nothing at the top moves. `FEW_PLAYS = 2` carries it. Sections are now
**54 / 53 / 174**.

**He also asked about the *spacing* of a rare song's plays** — "two plays 1,000
shows apart was a one-shot that was revived… two plays a handful of shows apart
paints a different story" — and said he wasn't sure how to model it. Three
findings, and the effect is not where either of us expected:

| group | clustered (≤200 shows/play) | scattered (>200/play) |
|---|---:|---:|
| 1–2 plays | 36% (n=50) | 27% (n=22) |
| 3–7 plays | **70%** (n=132) | **38%** (n=21) |

- Among the **1–2** group spacing barely moves the answer — which is a second,
  independent argument for merging them rather than splitting them further.
- Among the **3–7 rarities** it is a 32-point spread. That is the real finding
  and it belongs to that section, whose blurb now states it.
- **There is no natural line to draw.** Shows-per-play across everything that
  fell quiet at 2–7 plays is one hump with a long right tail; the 48 two-play
  songs run 8 / 12 / 8 / 8 / 12 across the spacing buckets. Any threshold below
  the one above would be invented, so none was.
- **The page was already printing his distinction.** The span at the right of
  every row reads `2009` for a song played twice three shows apart and
  `1992–2021` for one played twice 1,308 apart; 13 of the 48 print a single
  year. Nothing pointed a reader at that column. Both blurbs now do — described
  rather than modelled, which is the honest treatment of a continuum.

**Two more layout defects found while verifying this round**, both measured
rather than eyeballed: the second paragraph of a section blurb had
`margin-bottom: 0` against 19.8px for the first, because `.shelf-h+.dek` reaches
only the first standfirst — the trailing paragraph sat flush against the column
header. Fixed with `.rot .dek`, a no-op on the due page. And `<br>` between the
two paragraphs gave a line break where a paragraph break was wanted.

### Third round — the words come from the constant, or the build stops

**The heading is "Once or twice", not "One or two nights".** Ian, on the first
attempt: *"I'm not sure where you picked up the 'nights' lexicon. While it's
true that most shows are at night, this seems over-specific."* He is right, and
it was vocabulary this site does not otherwise use about its own subject — the
unit is a **show**, counted as one everywhere from `BUSTOUT_GAP` to
`shows_since`, and a matinee or a festival afternoon is no less one. The right
register was already on the page: the column these rows are counted in is
headed **Times played**. So the heading says how many times and nothing about
when, the anchor is `#once-or-twice`, and the hero cell now carries the heading
verbatim rather than an abbreviation of it — "ONCE OR TWICE" fits on one line
where "ONE OR TWO NIGHTS" wrapped. `tools/check_few_plays.py` asserts the word
"night" cannot come back into any derived string.


Ian, on the trap above: *"Let's build a dictionary that maps the number of plays
to the badge text, and a constant that names the section title, clustered near
the numeric constant. That way it should be noticed if ever it gets changed.
It's not a guarantee, but it's stronger."*

It is now a guarantee for every value the table covers, and a build failure for
the one it does not.

- **`FEW_NAMES`** sits directly under `FEW_PLAYS` and holds, per play count,
  `(times, badge)` as a **namedtuple** — `1: ("once", "one-off")`,
  `2: ("twice", "played twice")`, and 3 and 4 for headroom. Named and not
  positional because the first cut was a three-tuple, and dropping the unused
  cardinal left `FEW_NAMES[plays][2]` reading off the end of a two-tuple; the
  build caught it, but `.badge` cannot rot that way at all.
- **`FEW_TITLE` and `FEW_TIMES` are built from it**, not written out:
  `"Once or twice"` and `"once or twice"`, which differ only by a capital. The
  section heading, its hero cell, the due page's tail, the method page and the
  FAQ all interpolate them, so none can drift from the constant. The tally under
  the heading — "126 played once and 48 played twice" — is generated the same
  way, one clause per play count.
- **A module-level guard raises** if `FEW_PLAYS` exceeds what `FEW_NAMES`
  spells, naming the three places that would otherwise go quietly wrong.
- **The numeric bounds are interpolated too** — the method page and FAQ now
  print `8 or more` and `3 to 7` from `ROTATION_PLAYS` and `FEW_PLAYS`, so the
  other tunable constant is covered by the same discipline.

Proved by moving the constant rather than by reading the code, and the proof is
checked in: **`tools/check_few_plays.py`**. It writes possumlogic to a fresh
temp directory per value with a unique module name and bytecode off, and asserts
rather than prints — 1 through 4 must carry every derived string, 5 and 9 must
refuse to import, and no derived string may contain the word "night".

```
python3 tools/check_few_plays.py
```

**The check was verified to fail**, which is the only thing that makes a passing
run mean anything. Hardcoding `FEW_TITLE` makes it report three wrong titles;
deleting the guard makes `FEW_PLAYS = 5` die on a bare `KeyError` deep inside
`rotation_word` instead of at import — which is exactly the value the guard
adds, and is now demonstrated rather than asserted.

An earlier throwaway version of this probe was worthless and looked fine: it
reused one module name across four runs, so Python served the first run's
`__pycache__` back three times and it printed identical output for four
different constants. That is why this one gets a directory per run.

**Two structural wins came with it.** `rotation_group()` is now the only place
the thresholds meet a play count — `rotation_split()` groups with it and
`rotation_word()` names from it, so a song cannot be filed under one heading and
stamped with another word. And `SONG_JS` **stopped knowing the vocabulary**: the
page ships `data-quiet` with the word already chosen and the browser only
decides whether the gap makes it apply, which removed a second copy of both
thresholds and all four words written in another language.

**It found a live crash on the first build.** `rotation_word(0)` raised
`KeyError: 0`. Nine of the 589 songs — Day Tripper, My Sharona, Watcher of the
Skies and six more — exist in this archive *only as soundchecks*, and a
soundcheck is not a night the band played, so their counted play count is zero.
They now render an empty `data-quiet` and the box says nothing, which is this
file's standing answer where the data will not support a claim.

**Four of the nine were shipping a false word before this.** The old ternary

read `plays<=1?'one-off':…` off a `data-plays` of `0`, so a zero-play song came
out as a one-off — but only where the verdict branch fires at all, which needs
`since >= BUSTOUT_GAP`. Liquid Time, No Reply at All, Sunshine Superman and
Watcher of the Skies cleared it and were each labelled **one-off** on a song the
band has never played at a show. The other five sit at 91 shows and showed
nothing either way. Measured, not assumed: the first draft of this entry said
all nine, which was wrong by five.

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

## 3d. Keyboard: hotkeys, not just tab order — DONE 2026-07-28

§7b did the accessibility floor (focus ring, skip link, everything reachable).
This is the jumping layer, and it is deliberately three keys rather than a
keyboard interface — Ian was explicit that the point is not being *forced* to
reach for a pointer.

- **`[` / `←` and `]` / `→` step through the collection.** Bound to whatever
  the page marks `rel="prev"` and `rel="next"`, so a show page steps through
  shows and any page that grows a pager gets the keys for free. **Verified with
  a real key press, not a synthetic one**: `←` on 2026-07-22 landed on
  2026-07-21.
- **`?` opens an overlay listing the keys** — and *the list is read off the
  page rather than written down*, which is the FAQ contents-block discipline
  applied to a help panel. A page with no search box does not claim `/` focuses
  one; a show page with no later show shows only **Previous show**. Measured:
  index and song pages offer 3 rows, a show page 2, and the FAQ 1 plus a line
  saying where the others apply.
- **A `Keys ?` button in every footer**, because a shortcut nobody can find is
  a shortcut nobody has. 65×26, above the 24×24 floor, on every page type at
  320/375/1400px.
- **`<dialog>`, not a div.** It brings the modal semantics, Escape, the focus
  move on open and the focus restore on close from the browser rather than from
  a focus trap here that would be wrong on some platform nobody tested.
  Verified: opening puts focus inside, closing returns it to the button that
  opened it, and the keys form one column (`display:contents` on the rows, or
  each `<div>` is a single grid item and they never line up).
- **Nothing fires while you are typing.** Checked by focusing a field and
  dispatching `[` and `?`: no navigation, no overlay.
- The styling lives in `BASE_CSS`, the block every sheet shares — which is what
  §8e.1 was for. Three copies is how four rules on this site came to disagree.

### Two things this did not do

- **`/` still only works where there is a search box** — index, songs and song
  pages. Due, venues, dormant, method and FAQ have no search input for it to
  focus, so the overlay does not offer it there rather than binding a key that
  would do nothing. The older note in this section read as though those pages
  were missing a binding; they are missing a search box, which is a different
  and larger question.
- **Song pages still have no prev/next.** The keys are ready for one — they
  bind to `rel` — but the stepper itself is §4's item and wants a decision:
  baking neighbours into each page goes stale the moment a new song debuts
  unless every neighbour is re-rendered, which is the "record that outlives the
  work it records" shape this file already has four instances of. The safe
  shape is a client-side lookup from a small JSON, like `current.json`.

### One measurement of mine that was wrong, kept as a warning

A first sweep reported the footer button hanging off the right edge of every
page at every width. It was measuring before `DOMContentLoaded` had run the
script that creates it. Re-measured with a settle: the button is inside the
footer on every page at every width. **`overflow-x:clip` now hides exactly this
class of mistake from the eye**, which is an argument for measuring positions
rather than looking for a scrollbar.


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
- ~~Venue and tour on a show page are plain text; make them searches.~~ **DONE
  2026-07-28.** Both link to `index.html?q="<name>"`, through one
  `search_href()` so the quoting rule — which is the whole correctness of these
  links — is stated once rather than in every caller.
  - **Replayed rather than assumed**, the same check the venues page got:
    every link every show page emits, run against the built index's own
    haystack. **691 venue links and 669 tour links return exactly their own
    shows, 0 do not.**
  - **And the failure §8b.4 predicted has now actually happened.** That note
    said quoted phrases are "correct-in-practice rather than
    correct-by-construction, and a future venue name that is a phrase-prefix of
    another would break it". It was not a venue: **`2011 NYE` is inside
    `2010/2011 NYE Run`**, so its link returned nine shows for a four-show run.
    One of sixty-two tours.
    - Fixed by checking rather than trusting: `ambiguous_tours()` finds any
      name that is a substring of another, and those stay plain text. The run
      logs which names it dropped, so this cannot go quiet. Today that is
      exactly one name and four shows.
    - The correct-by-construction fix is still a `?tour=` parameter matched
      against a `data-tour` attribute. It needs a visible affordance to explain
      why the list is filtered — `?q=` explains itself by filling the search
      box, and a filter with no control is a mystery — so it is his call, not
      a cheap swap.
  - **Both links came out in the browser's default blue on the first build**,
    because `CSS` had no rule for a link in a masthead. Fifth instance tonight.
    Caught by measuring the computed colour before shipping rather than by a
    reader. They keep their own colour and weight — demoting the venue to
    `--dim` would demote the venue — and take the hairline every other link on
    the site wears.
- Bustout leaderboard (biggest gaps per performance, archive-wide).
- On this day. Random show. A feed — still 404.
- ~~`sitemap.xml`, `robots.txt`~~ **DONE 2026-07-28.** 1,306 URLs, walked off
  the *built directory* rather than assembled from what the build thinks it
  wrote — those are different claims and only one of them is checkable.
  Asserted: every URL resolves to a file that exists, no duplicates, and the
  only built pages left out are the two forwarding stubs, which are not pages.
  - **No `<lastmod>`, and that is the interesting decision.** The honest value
    is when a page's content last changed, and nothing knows it: CI checks out
    fresh, so every mtime is the build time, and stamping 1,306 pages "changed
    just now" every run is exactly the confidently-wrong figure this archive
    exists not to publish. The show's own date would be wrong differently — a
    2009 page changes whenever the archive behind it does. `<changefreq>` and
    `<priority>` are out because Google has said for years it ignores them.
  - Both files are **gitignored**. Tracking output generated from the built
    tree is how `cards.json` came to describe images it no longer matched
    (§8g); these travel with the build or not at all.
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
- ~~Method page: ordering is scattered (the bar is discussed
  mid-gap-calculation) and it needs a table of contents.~~ **DONE 2026-07-28.**
  - **One list drives both**, the way `FAQ` does: `METHOD` is ten
    `(anchor, heading, body)` tuples, and the contents block and the sections
    are the same tuple rendered twice. The page cannot advertise a section it
    does not have. The prose was carried across by parsing it out of the old
    string rather than retyped.
  - **The reorder was one swap.** It ran gap → median → verdict → *segue
    notation* → the bar, so the paragraph that draws the verdict was separated
    from the three that define it by a section about something else. The bar
    closes that argument now and the notation follows it. Anchors are
    unchanged, which matters: the FAQ deep-links `#which-show-this-was` and
    `#when-a-report-appears`, and both still resolve.
  - Every section ends with **↑ All sections**, and clicking one puts focus on
    the index — checked by reading `document.activeElement`, which is
    `sections.toc`.
  - **The `.toc` and `.backtop` rules moved from `FAQ_CSS` into `METHOD_CSS`**,
    which `FAQ_CSS` is built on, so both prose pages get them from one
    statement rather than two. Asserted: `FAQ_CSS` comes out with exactly the
    same set of rules it had, only in a different order.

  **And it found a rule that had never once been drawn.** `.backtop` sets mono
  at 10px, uppercase — "it is a control, not a sentence, and it must not read
  as another paragraph of the answer", says the comment. Inside `.prose` these
  are `<p>` elements, and `.prose p` is one class plus one type against a bare
  `.backtop`'s one class, so it out-specifies it and **order cannot help**.
  Every "All questions" link on the FAQ has been set in Literata at body size
  since the page was built. Confirmed against the *published* sheet on
  `origin/gh-pages`, not just the local one. The selector is
  `.backtop,.prose .backtop` now, and all three pages measure mono 11.25px.
  **[ruling]** this changes the look of a page Ian has already reviewed — but
  it is the treatment that was written down and reasoned about, and it had
  simply never applied.

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

## 8e. The three stylesheets — Ian's question, measured. §1 DONE 2026-07-28

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

1. ~~**Source duplication**~~ **DONE 2026-07-28.** Six named blocks now hold
   every rule that was byte-identical in all three sheets, and each sheet
   splices them in where its own copy sat, so the cascade is unchanged:
   `BASE_CSS` (skip link, focus ring, box model, tabular figures),
   `BODY_BOX_CSS`, `NAV_HIT_CSS`, `RULE2_CSS`, `FIGURE_CSS`,
   `FOOTER_LINK_CSS`. 5,983 bytes of triplicated source gone.
   - **Verified by string equality, not by eye**: all six composed sheets
     (`CSS`, `INDEX_CSS`, `SONG_CSS`, `SONGS_CSS`, `METHOD_CSS`, `FAQ_CSS`)
     come out byte-identical to what they were, with one deliberate exception —
     the show sheet's tabular-numerals comment now carries the same wording as
     the other two, which is the §8c bug written down where it can be read.
     A change that cannot alter a byte of any stylesheet cannot alter a page.
   - **One trap found on the way, and it is the kind that ships quietly.**
     `SONG_CSS` ended `""".replace("__PNET__", ICON_PNET)…` — three base64
     icons substituted into the closing literal. Splitting the literal to
     splice a block left that `.replace` seeing only the last segment, so the
     three placeholders survived into the published sheet and every external
     link icon would have rendered as a broken image. The substitution now
     runs over the composed string. Caught because the check compared the
     built sheet against the old one instead of asking whether the file
     compiled.
   - Not done, and worth knowing: this covers only what was identical in
     **all three**. Pairwise, 32–46 rules still repeat, and the near-misses
     (`footer{…}`, `.crumb{…}`, `.hero{…}`) differ by real amounts, so they
     want a decision per rule rather than another mechanical pass.
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

## 8h. Sparse song pages, and a Debuted hero — Ian, 2026-07-30. DONE

He opened on <https://possumlogic.com/song/lit-o-bit.html>: a one-performance
history does not need a search/sort/filter, "basically none of the heroes even
make sense", and such a page "can almost have an entirely different layout
because it's such a different story". Then, separately: a `debuted on` hero is
worth having on a song with lots of plays — "just a quick sort reversal away,
but it's useful data about the song" — and there is probably a weaker hero it
could replace.

### What the measurement said

- **134 of 589 songs are played exactly once**, 193 twice or fewer. On a
  one-play page three of the four static cards read `n/a` and the fourth
  restated the subtitle; at 375px the hero and tools bar were **367px of
  chrome in front of a single 257px row**.
- **n/a rate per hero**, over all 589: Times played 2%, *Debut 2%*, median
  10-year 33%, median all-time 24%, longest gap 24%. The debut is the most
  widely available figure the hero was not showing.
- **The two medians earn their two cards.** They differ as printed on **275 of
  the 392** songs that have both — the standing defence in `render_song` holds,
  so neither is the one to drop. Longest gap equals the all-time median on only
  52 of 446.
- **Times played was the weak one, and not because it is uninteresting.** The
  same integer was already printed three more times on the page: the subtitle a
  dozen pixels above the card, the `n of n shows` counter, and the sticky bar.
  It moved nowhere — it is still in the subtitle.

### What shipped

`SPARSE_HISTORY = 1`. At or below it a song page drops the tools bar whole
(search, clear, era chips, sort, counter), drops the era heading over its one
row, and takes a two-card hero: the date, and the current gap with its verdict.
Above it, every page gains a **Debuted** card in the slot Times played held,
linking to the debut's own row — the sort reversal, as one click — and the
subtitle drops its `Debut` clause so the date is stated once.

**The figure is the year, and that is measurement not taste.** Five cards
across leave 117–160px inside each between 900 and 1280px; `1986-02-03` wants
243px at `.num` size and still 162px shrunk to 1.5rem, and it wrapped at 900,
1024 and 375. Widening the card starves the other four below 1024. The full
date goes where there is room: the sparse page's two-card hero, and the row the
card links to. Swept 5 pages × 15 widths from 300 to 1440: **0 wrapped figures,
0 sideways scroll.**

### Two bugs found on the way

1. **The sticky bar counted rows the rest of the page does not.** It used
   `len(perfs)` where the hero, subtitle and counter all use `len(countable)`,
   so on **136 of 589 pages** the condensed header contradicted the page it
   condenses — You Enjoy Myself read `629 shows` stuck above a page whose every
   other figure said 627. It also told a one-play song it had "1 shows". Both
   fixed; an invariant now asserts sticky == counter == countable on all 589.
2. **`id="main"` was very nearly duplicated.** The first cut moved the skip
   target onto the `<ol>`, which already had `id="list"` — two `id` attributes
   on one element, only the first honoured, and `#main` silently resolving to
   nothing. Invisible unless you tab into the page. The skip link is now
   re-pointed at `#list` instead, and the sweep asserts every page's skip href
   resolves to exactly one element.

### Both open items closed the same day, on Ian's call

`SPARSE_HISTORY` is **2**, and the preview card follows the page. See §8i.

## 8i. The preview cards were worse than anyone thought — 2026-07-30. DONE

Ian bumped `SPARSE_HISTORY` to 2, asked for the preview card to follow the new
page design, and mentioned in passing that he had **shared a card the night
before that still carried the "Gap Report" wordmark**. The last of those turned
out to be the thread worth pulling.

### On the wordmark he saw

**No published card carries it.** "Gap Report" was the `kind` line on show cards
and the title on the index and songs cards until `5d59cbdbf` (2026-07-27
03:25). Every one of the 1,304 published PNGs was grouped by its wordmark strip
— four distinct groups, all four checked by eye, all four reading POSSUMLOGIC.
So the most likely explanation is a **platform-cached unfurl**: Slack, Discord,
iMessage and the rest cache OG images for weeks and will re-serve a copy
fetched before the rename. Worth re-sharing the link to a channel that has
never seen it before concluding anything about the site.

That said, he was right that something was wrong with the cards. Three things
were, and none of them would ever have fixed themselves.

### 1. Fourteen published cards had `{sheet}` printed across the top

`CARDS_SHELL` is a `.format()`-style template that nothing calls `.format()`
on — `shoot_cards` uses `.replace("__CARDS__", …)`, deliberately, because
CARD_CSS is full of braces. So `{fonts}` and `{sheet}` stood as literal text.
`{fonts}` sat inside an `href` and merely 404ed. `{sheet}` was inside one too
until `b8244026b` (2026-07-27 23:40) unwrapped it, and **bare text in `<head>`
is relocated into `<body>` by the parser** — painted at the top of the page,
and captured in the first card of every 24-card batch.

Measured over all 1,304 published PNGs by sampling the top-left strip: **14
defaced**, among them `index.png` and `due.png` — the two a shared link is most
likely to unfurl.

### 2. Every card has been drawn in fallback faces

Same root cause: neither font link resolved, so the renderer never loaded
Bagnard, IBM Plex Mono or Literata. The cards looked plausible because Chrome
fell through to Georgia and whatever mono was to hand. Side by side, the
published `index.png` sets "Possum Logic" in Georgia; the redrawn one sets it in
Bagnard. The sheet is now addressed absolutely (`file://…/site/fonts.css`),
because the card markup is written to a temp directory and a relative path
resolves beside *that*.

### 3. And CI would have fixed neither, ever

This is the part worth remembering. `card_print` hashed **markup + CARD_CSS**.
The shell was not in it. So a change to the way a card is drawn — the fonts,
the shell, the shooter's flags — produced identical hashes, the index went on
saying every card was current, and CI redrew nothing. Checked directly:
**all 1,301 recorded hashes matched the then-current code** while 14 of the
images were visibly broken.

`CARD_INDEX` is a cache keyed on a hash of *some* of its inputs, which is the
same shape as §8g one level deeper — and the docstring on `card_print` already
tells the story of CARD_CSS being added for exactly this reason. It stopped one
input short. Fixed twice over: `CARDS_SHELL` is now hashed, and `CARD_REVISION`
is a hand-bumped integer for the changes no hash of the inputs can see, because
"same input, different output" has no other expression.

**A cache key must cover the whole pipeline, not the part that is convenient to
hash. When you fix a renderer, ask what invalidates the render.**

### 4. A three-line title collided with the wordmark

`.card` centres its content in a fixed 630px box and the wordmark is positioned
absolutely, so a title that took three lines pushed the figures onto it — "The
Inner Reaches of Outer" printed POSSUMLOGIC hard against TIMES PLAYED, 1 card of
1,304. The box now stops short of the wordmark's strip, which cannot collide at
any title length; stepping `_card_size` down again would only move the length at
which it happens.

### What the cards say now

Sparse songs get the sparse page's story: `DEBUTED 2010-06-22` over
`COMCAST CENTER, MANSFIELD, MA` where the card used to read `1 / N/A / N/A`
across three slots, and a two-performance song adds its one real interval
(`1,312 SHOWS BETWEEN`). The one-year span was replaced by the venue on
one-play cards because "2010 — 2010" is the same year printed twice.

### The one thing to watch on the next CI run

**`site/data/cards.json` is deliberately committed stale.** All 1,304 entries
now disagree with the current code, so the next build redraws every card. That
is the point — it is the only way the 14 defaced ones and the fallback faces
reach the published tree. Drawing them locally and committing the fresh index
would have been §8g exactly: CI restores the *published* PNGs, reads an index
claiming they are current, and draws nothing.

Cost: the full redraw took **4m25s locally** (1,304 cards, 24 per browser
launch). Expect the next scheduled run to be several minutes longer than usual,
once. After that the index is current again and the incremental behaviour is
unchanged.

## 8j. Hovering the Jam chart stamp made it vanish — Ian, 2026-07-30. DONE

He sent a screenshot of a setlist row where the chip beside "Mercury >" was a
solid red block, said this was the same thing as the "new since you last
looked" tag the night before, and asked for the whole class to be swept rather
than found one at a time. It was the right instinct: there was a second live
one, on a banner he could not have stumbled into.

### What was wrong

**1. The chip — 1.00:1, both palettes.** `a.jc-chip:hover` sets
`background:var(--hot);color:var(--paper)` at 0-2-1. `td.song a:hover{color:
var(--hot)}`, 190 lines further down the same sheet, is 0-2-2 and took the
`color` — so the chip painted `--hot` on `--hot`. What made it look handled was
the other half of its own selector, `td.song a:hover .jc-chip`, which had
**never matched anything**: the chip is a *sibling* of the title link, not a
descendant. Fixed at the far end — `td.song a:not(.jc-chip):hover` — rather
than by escalating the chip, which only moves the race one round on. That is
the fifth modifier-class-loses-to-descendant-selector bug, after the
sticky-header hide, `.backtop` and `.live span`.

**2. "On stage now" — 1.12:1 light, 1.08:1 dark.** `.onstage:hover` reverses
the whole banner onto a solid fill and then repaints exactly three children:
`.k`, `.n b`, `.p`. It missed `.n` itself, whose own text is the words "songs
so far", so they stayed `var(--dim)` on the fill. Identical numbers to the
`.live span` bug in §"N new since you last looked". **This banner only exists
while a show is being played**, so no page in the archive carries it and
nothing that reads built HTML could have found it.

**3. The stamps had drifted from the palette's own rule.** `--hot-text` exists
because "the accent reads at 4.44:1 on paper — fine for a 36px figure, under
the bar for the 10px chips and verdicts it is also used on." Three of the four
reversed stamps were still filling with `--hot`: the chip's hover,
`.verdict.bustout`, and `.prose .bust` on the method page. `.prose .overdue`
was `--hot` where the show pages' `.verdict.overdue` was already `--hot-text` —
the same stamp, two sheets, one of them fixed. All now `--hot-text`: 5.78:1
light, 6.63:1 dark, and a no-op in the dark palette where the two are one
colour.

### The `*` trap, which cost a round

The first fix for `.onstage` was `.onstage:hover *{color:inherit}` — a list of
children is a list a fourth child is not on, so name none of them. It fixed
`.k`, `.p` and `.n` and **not** `.n b`, which stayed at 2.68:1 / 2.25:1. `*`
contributes *nothing* to specificity, so that selector is 0-2-0: it beat the
0-2-0 rules on source order alone and lost to `.onstage .n b` at 0-2-1. It is
`.onstage:hover.onstage *` now — 0-3-0, which no descendant rule in the block
can reach and which does not depend on where it sits in the sheet.

The audit below is what caught that. It is worth saying plainly: the tool
caught the *fix* being wrong, not just the bug.

### `tools/contrast_audit.html`

None of this is visible in the source, in a resting screenshot, or to anything
that reads the CSS. The cascade has to be resolved *in the state*, which means
a browser. The tool rewrites `:hover`, `:focus-visible`, `:target` and
`:active` to classes of **identical specificity** (a pseudo-class and a class
are both 0-1-0), in place in the same `<style>` element, so cascade order and
specificity are exactly what a real pointer produces; then it walks every
element and pseudo-element, composites the translucent backgrounds down to
what is actually painted, and compares against the AA floor for that element's
own type size. Both palettes, 1280 and 390. The two live-show states are
reconstructed, since no built page carries them.

Served from the repo root by the `audit` entry in `.claude/launch.json`, so it
cannot end up published. Run it after touching a palette token, a `:hover` or
`:focus` rule, or any selector that could out-specify one.

Three things it got wrong first, all now guarded in the file:

- **Reading `.sheet.cssRules` right after rewriting `textContent`** returns the
  rule list from *before* the rewrite, or an empty one. It reported a clean
  pass on a page with a known 1.00:1 bug. Selectors are parsed out of the text.
- **`python -m http.server` sends no `Cache-Control`,** so a run straight after
  a `--rebuild` measured the *previous* build and reported the bug just fixed
  as still present. Every load now carries its own query string.
- **A 404 fires `onload` like any other page,** giving a document with no
  stylesheet, no findings, and a green report. It now throws if the loaded
  document has under 1000 bytes of CSS.

### Still open: the `--hot`/`--hot-text` line outside the stamps

The sweep leaves **one band standing, all of it in the light palette** (dark is
unaffected: `--hot` and `--hot-text` are the same colour there). It is not a
bug, it is the same palette rule not being applied outside the stamps, and it
is Ian's call because it changes the site's hover red everywhere:

- **4.12:1** — `--hot` text on the `--hover` row tint. Every row hover on the
  site: `td.song a`, `.d-song`, `.vn-venue`, `.r-venue`, `.r-date a`,
  `.gap.big`, `details.jam summary::after`, the `.ext` links.
- **4.44:1** — `--hot` on plain paper, at 11–22px: `.keyhint`, `.crumb a`,
  `.crumb.pager`, `.ax-date`, `.best .score`, `.era-chip b`, `.totop`,
  `.yr .up`, `.notes p a`.
- **3.68:1 and 4.13:1** — the method page's `.toc`, worst in the set, because
  that panel has its own `--rule-soft` background under the text. Its resting
  number (`.toc a::before`, `--dim`) is 4.13 light and 4.49 dark.

Swapping `--hot` → `--hot-text` in text position fixes all of it (5.30:1 on the
row tint, 4.80:1 in the `.toc` panel) at roughly 20 rule sites, and darkens the
light-mode hover red a shade. Not done: it is a look-of-the-site decision, not
a defect.

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
