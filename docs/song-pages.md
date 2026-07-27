# Brief: song history pages

A page per song, listing every Phish performance of it newest-first, with hero
stats and search. Intended to fix what is annoying about phish.net's own song
history pages: oldest-first ordering, and stats presented as lines of prose.

## The thing worth knowing first

The data is already being fetched and thrown away. `add_previous()` calls
`setlists/slug/<song>` for every song in a show to find its previous
performance, then discards the rest of the response. That response is the
song's complete performance history: one row per performance with showdate,
venue, city, state, gap, set, and more. So the corpus for these pages costs no
additional API calls — only disk.

Filter it by artist. `/setlists/slug/ghost` returns 242 Phish rows, 81 Trey
Anastasio and one Page McConnell; `add_previous` already filters on
`report["artist"]` and these pages must too, or a song page will list TAB shows
as Phish performances.

## Proposed archive layout

    site/data/<date>.json          show reports (exists today)
    site/data/songs/<slug>.json    song histories (new)

The refresh invariant falls out for free: a song's history only changes when
Phish plays it, and when they do, that show's fetch re-fetches that song. So
writing the history whenever `add_previous` touches a song keeps every song
current, with no extra bookkeeping. A song nobody has played since the archive
started keeps a history that is still correct.

Trim the stored rows to what the page needs — showdate, venue, city, state,
gap, set — rather than keeping the whole payload. Tweezer alone is 470 rows,
and a full corpus is several hundred songs.

## Statistics already computed

`_classify()` in possumlogic.py already produces, per song per show, and stores in
the show's JSON: `plays`, `recent_plays`, `gap_median`, `gap_mean`, `gap_low`,
`gap_high` (the p15/p85 bounds), and `verdict`. Hero stats for a song page can
reuse these rather than inventing a second set. Note they are deliberately
era-bounded — measured over `RECENT_YEARS` (10) before the show, because
all-time figures are dominated by the 1990s when the band played far more shows
a year out of a smaller catalog. Llama's all-time median gap is 2 against 10
across its last 20 performances. A song page showing all-time and recent side
by side would be genuinely interesting; showing only all-time would mislead.

## Search

Ian's requirement: search by venue, city, state, and year, like the show index.

Mirror `INDEX_JS` and `render_index()` rather than writing something new. The
index pattern is:

- Rows are server-rendered, so the page is a complete list with JS off. The
  controls ship `disabled` and JavaScript enables them.
- Each row carries a `data-search` attribute holding a lowercased haystack of
  everything searchable. Terms are ANDed.
- A purely numeric term matches as a whole number, so searching 8 finds the 8th
  and not the 18th.
- Dates carry alias spellings (`_date_aliases`) so 7/24, 07/24/2026, 7/24/26
  and "july 24" all resolve. Reuse that function.

## Conventions in this codebase, learned the hard way

- Palette comes from the `LIGHT`/`DARK` dicts; the dark blocks are generated so
  the two never drift. Never hardcode a colour.
- Everything dark-mode is scoped to `@media screen` so print and PDF stay on
  paper stock.
- A table column sized in percent cannot hold text sized in rem. Below some
  viewport width the text outgrows the column, and `text-align` will not save
  it: an overlong nowrap line starts at its box's start edge and spills out the
  end, into the next column. Either let it wrap or gate it on a width.
- Narrow viewports drop table layout entirely for a stacked grid, so rules span
  the full width. See the `max-width:620px` block.
- Verify at 320px and at desktop, in both colour schemes, and check the PDF.
  Measure with Ranges rather than element boxes — a block child fills its cell
  regardless of how wide its text is, so box measurements hide overflow.
- Hover targets: put `title` on a whole cell, never on a small mark.
- Only annotate the notable. Ian does not want every ordinary row tagged.

## Open decisions

1. **URL shape.** `site/song/<slug>.html` with reports at the site root, so a
   report links `./song/<slug>.html` and a song page links back `../<date>.html`.
2. **Which performances link out.** A performance whose show is in our archive
   can link to that report; the rest are text, or link to phish.net.
3. **Hero stats.** Candidates: times played, debut, last played, median gap
   recent and all-time, longest gap, and how many of the corpus's shows it
   appeared in.
4. **Song index.** Whether the show index gains a songs tab, or songs are
   reachable only by tapping a title in a report.
5. **Corpus scope.** Whether to seed histories for every song the archive has
   ever seen, or only fill in as shows are added.

## Working style

Ian designs by conversation. Ideas arrive as "I wonder if" and are exploratory
until he clearly asks for something. Investigate, measure, propose, then wait —
do not build and commit inside the same turn. See the project memory files.
