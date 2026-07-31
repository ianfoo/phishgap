# possumlogic

One Python file (`possumlogic.py`) builds a static site from the phish.net API
and publishes it to <https://possumlogic.com> from the `gh-pages` branch. The
README covers what it does; `docs/TODO.md` opens with a §0 handoff block
holding current state and the work queue.

```bash
./possumlogic.py --site site --rebuild   # re-render everything from the local archive; no API calls, ~2s
./possumlogic.py --site site --watching  # is a show inside its watch window now?
```

Serve the built site with the `site` entry in `.claude/launch.json`, not over
`file://` — `history.pushState` and other same-origin APIs behave differently
there, which makes local verification lie.

## Gotchas

**There are still three base stylesheets, but what they share is now named.**
`CSS` (show pages), `INDEX_CSS` and `SONG_CSS`; `SONGS_CSS`, `METHOD_CSS`,
`FAQ_CSS`, `DORMANT_CSS` and `YEARS_CSS` extend `INDEX_CSS`. The rules that
were identical in all three live in `BASE_CSS`, `BODY_BOX_CSS`, `NAV_CSS`,
`RULE2_CSS`, `FIGURE_CSS`, `FOOTER_BOX_CSS`, `FOOTER_LINK_CSS`, `TOTOP_CSS`
and `CARD_LINK_CSS` — edit those once. (`DEK_CSS` is the same idea across two
of the three, not all three.) `CARD_LINK_CSS` was named on 2026-07-30 the
moment a third sheet wanted a linked hero card, rather than after: it holds
the three rules that do not depend on where the card goes, and deliberately
leaves out the fourth, which carries the arrow — the index points right
because the card leaves the page, the show and song sheets point down because
it lands further down this one. `YEAR_STRIP_CSS` is the year strip; it was
named when a second page wanted it and is back to one caller, because the
dormant page was regrouped into three sections and dropped its strip.
`NAV_CSS` is the whole nav strip and replaced `NAV_HIT_CSS`: the four
near-identical `.crumb{…}` rules are gone, and the show sheet keeps only what
is genuinely its own — the pager row and a margin. **The markup is one
function too**, `nav_strip()`, after ten hand-written copies left every show
and song page — 1,302 of 1,310 — marking no current location at all while the
other eight marked themselves. A nav in ten copies is ten chances to be
inconsistent about the one thing a nav must be right about, and the tenth
arrived on `main` while the ninth was being removed on a branch. **The strip
is four destinations**, and it is four on purpose: Due, Out of rotation and
Not a show are questions asked *about* the archive rather than ways into it,
so each hangs off the parent that owns it as a hero card and marks that
parent as its section. Adding a fifth is a decision about the whole strip's
width rather than a one-line edit — at 390px one line holds 336px and the
four spines use 219px of it. **Taking one out is the riskier edit**: it can
strand a page while every link on the site still resolves, so assert that
anything off the strip still has a door from a page on it.
**Everything else is still copied**: 32–46 rules repeat pairwise, and the
near-miss `.hero{…}` (flex in one sheet, grid in another) differs by a real
amount. `footer{…}` was listed with them and had stopped differing: measured
2026-07-30 its three copies were identical once whitespace was normalised, so
it was hoisted into `FOOTER_BOX_CSS`. **The stale note is the lesson** — it
told several sessions to leave a pure triplicate alone, and a wrong constraint
in a doc gets obeyed.
So a plain string replace on any rule
outside a named block will still hit two or three sheets, or — worse — one.
Anchor on a neighbouring line that differs and assert the match count. Five
bugs have come out of the copies: a nav that could not wrap, a footer link in
the browser's default blue, a sticky-header hide out-specified by a modifier
class, tabular figures on show pages only, and — 2026-07-30, caught by
measurement before it shipped — a `.crumb{gap:.35rem}` in the show sheet's
narrow media query, written when both nav strips wanted the same geometry,
which out-specified the shared row gap the moment the strip got 44px tap
targets and left four overlapping targets on show pages and nowhere else.
**The check that found it is the one to reuse**: walk every page type at every
breakpoint and assert no two tap targets overlap, rather than looking at one
page and calling it done. `docs/TODO.md` §8e.
`TOTOP_CSS` was named when the floating back-to-top control went from one
sheet to all of them. **The markup had the same problem**: five functions
built the hero cards from five copies of the same two lines, three escaping
the href and two not. `hero_html` is the one copy now, and `hero_cols` beside
it is the pattern — the builder *states* what the CSS needs to know (how many
columns, which card carries a name) rather than the CSS inferring it, because
an inference like `:has(.of)` fails silent. **The footer is `footer_html()`**
for the same reason as the nav — it was eleven copies in eleven shells, and
adding one cell to it would have been eleven chances to miss a page. It also
reserves a lane at the page bottom for the floating back-to-top: `.totop` is
fixed to the viewport's bottom right, so the footer's last row is the one
piece of content it is guaranteed to cover, and a fourth cell put a 65×26px
control under it. Reserve the lane rather than move the victim; the sweep
found a second one at 768px.

**`.prose p` beats a bare class, and two rules have lost to it.** `.prose p`
is one class and one type, so any single-class rule styling a `<p>` inside the
prose loses outright — order cannot help, because the two are not equal.
`.backtop` was found this way; `.src` had *never once been drawn* since the
FAQ's segues answer was written, rendering as an ordinary body paragraph. Both
are `X,.prose X` now. **Check any single-class rule that styles a `<p>` inside
`.prose`, and check it by reading the computed style off the built page** —
and reload past the cache first: this was measured as still-broken once,
against a page the browser had kept.

**A debut carries a "gap" that is not a gap, and skipping row 0 does not
always skip it.** phish.net gives a song's first counted performance a gap
equal to every show the band had played before it — 2,022 for What's Going
Through Your Mind. That is the band's history length, not a silence. The site
drops it by ignoring each song's first row, which is right for 473 of the 518
debuts and wrong for the other 45: those songs first appeared at a date
phish.net does not count toward gaps (Festival 8's 2009-10-29, 1997-06-06,
1999-06-24, 1995-05-14 and a dozen more), the archive keeps that appearance as
row 0, and the debut gap lands on row 1 where "skip the first row" cannot
reach it. **Filter to counted performances first, then drop the first** —
`due_rows` and `render_song` have always done it in that order; `render_songs`
and `songs_card` did not, and published 42 wrong longest gaps. Fixed, and the
whole songs index counts shows now: 127 songs had a "shows" figure that
included soundchecks, so the index and the song page one click away disagreed
about 127 songs. **A page that summarises other pages must count the way they
do** — the check that found it was reading both. `docs/TODO.md` §2k.

**And phish.net's gaps themselves are sound — do not go looking for that bug.**
Measured counted-performance to counted-performance, 0 of 36,378 exceed the
shows actually between them. A first pass at the above found "95 impossible
gaps" by comparing each gap with the previous row *in this archive's list*,
which includes the performances phish.net deliberately does not count; every
one of the 95 had an uncounted row before it, and 50 of them were the
measurement being wrong rather than the data.

**A `hidden` attribute loses to any author `display`.** The browser hides
`[hidden]` with a *user-agent* rule, and a user-agent rule loses to an author
declaration outright — specificity does not enter into it. `.totop` declared
`display:flex`, so `hidden` did nothing, and the back-to-top button sat on
every song page permanently, pinned over the header it exists to replace, from
the day it shipped. The script had been setting `.hidden` correctly the whole
time. **Prove the state you are claiming, not its opposite**: every screenshot
of that button showed it working. `docs/TODO.md` §2k.

**Drawing preview cards locally poisons CI.** `site/data/cards.json` records
what each card was drawn from and is tracked; `site/card/*.png` is gitignored.
So a local `--rebuild` draws the images here, writes "already drawn" into a
file that ships, and CI then restores the *published* PNGs, sees an index
claiming everything is current, and draws nothing. The markup updates and the
images do not. **This is the fourth instance of the shape below** — a record
that outlives the work it records. Check the published PNG, not the log line.
If you must draw locally to see a change, `git checkout HEAD -- site/data/cards.json`
before committing: an index that says "stale" is true of the published images
and makes CI redraw, where a fresh one silently freezes them.

**And the card index was keyed on only part of what draws a card.**
`card_print` hashed markup + `CARD_CSS` but not `CARDS_SHELL`, so the three
days when `{sheet}` was printed literally across the top of every batch's first
card — 14 published PNGs, `index.png` and `due.png` among them — never
invalidated anything: all 1,301 recorded hashes matched the code that was
producing the broken images. The same omission had every card drawn in Georgia
and system mono, because the shell is where the font links live. `CARDS_SHELL`
is hashed now, and `CARD_REVISION` is a hand-bumped integer for what no hash of
the inputs can see. **A cache key must cover the whole pipeline; when you fix a
renderer, ask what invalidates the render.** `docs/TODO.md` §8i.

**And the fifth: `nb` on a performance meant "we asked", not "we know".**
`setlist_neighbours` returned an entry only for songs that *had* a neighbour,
and the caller then stamped `nb=1` on every song of that date. So "the setlist
we fetched did not mention this song" was written down identically to "this
song genuinely opened its set" — and `nb` is what keeps a date from being
asked again, so the guess became permanent. It emptied the Before / after
column on 758 performances across 601 dates, concentrated in songs that have
almost never been played without a neighbour: the Sloth 107 of 177, Colonel
Forbin's Ascent 75 of 130, Fly Famous Mockingbird 74 of 131 — a song whose
every performance follows Colonel Forbin's, showing nothing. Fixed by having
the extractor report every song it *saw*, empty entry included. **When a flag
means "handled", check what it does when the answer was unavailable rather
than absent.**

**And the sixth, in the same flag: the migration that created it deleted the
record it replaced before writing its own.** `nb` took over from a central
`site/data/neighbours.json` listing walked dates. The migration block sets `nb`
in memory, calls `os.remove(index)` immediately, then writes files only via
`flush()` — which writes only the slugs the *fetch loop* queued. Every song that
run did not re-fetch lost its record permanently; an empty `todo` would have
returned before writing anything. Measured cost: 28,264 performances carry
neighbour data but only 18,292 carry the flag, and 10,718 of the difference sit
on dates the deleted index had recorded as walked. Only ~78 performances in the
archive were genuinely never asked. **Do not delete the old record until the new
one is on disk** — and the block is still there, unreachable but loaded, so
`docs/TODO.md` §0 argues for removing it.

**And the seventh, caught before it shipped: a carry-forward list in another
function.** `save_song_history` rewrites a song's history from the API, and the
neighbour fields are in no such response, so it copies them across by name —
through a hardcoded tuple of four key names, in a function nobody editing the
neighbour walk would think to open. Adding four new fields to the walk would
have dropped every one of them on the next `--previous` run. The list is now
one constant, `NB_CARRY`, sitting beside the walk that produces it. **When you
add a field, grep for the list that copies fields.**

**`archive/setlist-order.json` makes a re-walk free, and is a cache with no
expiry at all.** It holds the running order of every settled show, so changing
the neighbour rules and re-walking all 2,009 of them cost 44 API calls rather
than 2,009, and needs no API key. But the first harvest ran *during* a show and
wrote down that show at the 12 songs it had at the time. Reading that back
would have frozen the running order of the one show still moving — the six-hour
cache bug again, minus the six hours. So `--seed-setlists` always re-fetches a
show whose report is still `provisional`, and never writes one into the extract:
its order is partial by definition, and the day it settles a partial record
stops being skipped and starts being believed. **An extract of a live source
needs the same staleness rules as the cache it replaced.**

**Measures are in `rem`, and one place was missed for a year.** `.wrap` is
`max-width:60rem` precisely so it travels with the type scale, and the comment
there says so. `.stuck .in` kept the literal `960px`, so when the scale went up
a step the content grew to 1080px and the sticky bar held still — putting every
column label 60px off the column it names. It read as a *content* bug: a long
note in the venue cell appeared to run past the "Before / after" label while
never touching that column. Before believing a cell overflows, measure the
header against the row.

**Every API response is on disk for six hours — count the cache before quoting
a cost.** `DEFAULT_CACHE` is `~/.cache/phishgap`, `CACHE_TTL` is 6h. A job that
looks like a thousand calls is often zero. On 2026-07-29 a re-seed of 1,966
setlists was quoted at "1,298 calls, ~13 minutes" twenty minutes after those
exact responses had been fetched and cached — the real cost was nothing.
The TTL also runs the other way: it is a **deadline on data already paid for**,
so if a pending change will need something a run just fetched, copy it out of
the cache before it expires rather than planning to re-fetch. Knowing the cache
exists is not the same as remembering it while costing work.

**`body` is IBM Plex Mono site-wide.** Literata is loaded and applied
deliberately to running prose (`.jam`, `.note`, `.prose`). Mono prose anywhere
else is usually an artifact of that default rather than a decision.

**Anything long-running must re-read its inputs each pass.** Three separate
outages have had one shape — a job that publishes from something it read once:
a swallowed rebase conflict published a site missing the show it was watching;
a six-hour HTTP cache served one watcher the same setlist for five hours; a
resident watcher republished the whole site from its startup commit every five
minutes, reverting everything pushed during a show; and a card index that said
588 previews were current while the published images were a build behind.
Assume a fifth exists.

**The fifth existed, and the cure had a hole in exactly the shape of the
common case.** The six-hour cache above was fixed by refreshing the setlist of
any show in `recheck` — archived but still provisional. A show with no report
yet is not in `recheck`, and that is every show on the night it is played: the
window opens at 23:00 UTC, the first song is posted around 23:30, so the
watcher's first pass asks for a setlist that does not exist and then serves
that emptiness back for six hours. Nothing archived means never provisional,
means never rechecked, means never refreshed — the one show being watched was
the one show that could never be seen. It cost the whole first hour of
2026-07-29 at MSG, live, and it had been latent every night since the original
fix. When fixing a cache-staleness bug, check the bootstrap case: the first
fetch is the one guaranteed to be too early.

**The sixth was on the client, and it was the page itself.** The live show page
carried `<meta http-equiv="refresh" content="120">` — present, well-formed,
correctly placed, and never once firing: Pages sends `max-age=600`, so a reload
inside ten minutes can be answered from the browser's own cache with the same
document, and browsers throttle meta refresh in background tabs for as long as
they like. A page that reloads on a timer is a long-running job that publishes
from something it read once. It now polls the report JSON with a changing query
string, which puts each request on its own CDN cache key, and reloads only when
the song count actually moves. **Any reload-on-a-timer needs a changing URL, or
it is asking the cache whether the cache has changed.**

**A show can be counted before its setlist is known, and then every figure is
wrong.** `--calendar` builds the counting calendar from phish.net's show list,
so it adds tonight's show the moment the API lists it — while `--catch-up`
fetches the setlist separately and may fail. On 2026-07-29 that combination
advanced `current.json` to `as_of: 2026-07-29`, `shows: 2108`, and moved all
588 songs up by one, with none of the six actually played reset to zero. The
root cause above is fixed, so the window is now one pass rather than a whole
show — but the two steps are still independent, and a wrong figure is worse
than a missing one. `docs/TODO.md` carries this as open.

**Re-check the assumptions written here before designing against one.** The
`--html` output was documented as needing to stay self-contained long after
that stopped being a goal — and it was never self-contained anyway: it links
Google Fonts for the two faces that set nearly all the text, and inlines only
the display face. A stale constraint in a doc is more expensive than a missing
one, because it gets obeyed.

**GitHub Pages serves `cache-control: max-age=600`.** `curl` of the live site
can be ten minutes stale and look exactly like a failed publish. `git fetch
origin gh-pages && git show origin/gh-pages:<path>` is the ground truth for
what was actually published.

**This is a reference archive, so a wrong figure is worse than a missing one.**
Where the data will not support a claim, the site says nothing — phish.net's
gap is not reproducible from a show calendar, so this site computes its own
"shows since" and says so; the 35 shows filed as "Not Part of a Tour" stay
unnamed because their festival names exist only in freeform prose.

## Verifying a change

Claims about this site have been wrong in every session so far, in the same
few ways. Before reporting that a site change works, use the `verify-site`
skill in `.claude/skills/`.
