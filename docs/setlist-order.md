# `site/data/setlist-order.jsonl`

## Where it lives, and the theory that did not survive

This spent a day in a top-level `archive/`, on the reasoning that `site/` is
what readers see and this is a build input. Measured 2026-07-31, that split is
not the one this repo actually keeps. Of `site/data`'s 19 MB, exactly two things
are ever fetched by a page — `data/shows/<date>.json`, which the live show page
polls, and `data/current.json`. **`data/songs` is 10 MB that no reader has ever
requested**, along with `calendar.json`, `cards.json`, `phishin.json` and
`schedule.json`. `.gitignore` has said the real rule all along: "site/data is
the archive that regenerates them."

So it lives with the rest of the archive. Being published costs 3.5 MB on a
228 MB tree, and it buys the thing that was awkward: both workflows already
commit `site/data`, so CI keeps this file with no special case, and
`order_path(site_dir)` takes the site directory like every other archive path
instead of an absolute one derived from `__file__`.

The running order of every **settled** show the archive has a performance for:
one JSON object per line, `{"date": ..., "rows": [...]}`, sorted by date, each
row `{set, position, slug, song, trans_mark}` sorted by `SET_ORDER` then
position, Phish only. 2,008 dates.

It exists because the running order is the one thing the song-history endpoint
does not give you. Same API as everything else here — `api.phish.net/v5`, one
key — but `/setlists/slug/<song>` says every night a song was played and only
`/setlists/showdate/<date>` says what stood next to it. This site is organized
per song; adjacency is only knowable per show. That is one call per show, and
this file is what stops us paying for them again.

**It is a derived extract, not a cache of API responses.** Only the five fields
above are kept. Everything else the endpoint returns — reviews, ids, permalinks,
tour metadata, ratings, footnotes — is dropped, either because the archive
already stores it or because it has no use here. `CACHE_TTL` in
`possumlogic.py` still expires actual API responses after six hours; that is
unchanged and should stay.

**Settled only, and this is the important part.** The first harvest ran during a
show and wrote that night down at the 12 songs it had at the time. An extract is
a cache with no expiry, so reading that back would have frozen the running order
of the one show whose order was still moving. Both writers therefore skip a show
whose report is still `provisional`, and `--seed-setlists` always re-fetches one:
a partial record stops being skipped and starts being believed the day the show
settles.

## Who writes it

`--catch-up` writes it, as of 2026-07-31. The setlist that builds a report is
already in hand, so the running order costs no additional call — the same
argument that already had `record_neighbors` writing the derived neighbors at
fetch time. Before this, the file only grew when somebody ran `--seed-setlists`
by hand, so it lagged by however many nights since, and every missing night was
a call the next rule change would have to buy.

`--seed-setlists` still maintains it for backfills. It walks what is here, buys
only the dates that are not, and writes those back — so a rule change costs
nothing for everything already recorded. The full re-walk on 2026-07-30 cost 44
calls against 2,009 shows. `--force` re-walks everything; no API key is needed
if this file covers the dates.

## Why one file, and why JSONL

**One file, because git stores the delta, not the document.** Measured
2026-07-31 over thirty nightly appends: 13.0 KiB on the wire and 16 KiB of pack
growth — about 500 bytes per show, not 3.4 MB. An earlier version of this README
said "a nightly append would put a fresh 3.4 MB blob in git history every day"
and gave that as the reason CI must not maintain the file. That was wrong, it
was never measured, and it kept the file un-automated and drifting for a day.
The 3.4 MB figure is the size of the loose object before `git gc`; it collapses
on repack, and a push sends a delta.

Sharding was measured at the same time and is not worth it. By year: 41 files,
13.6 KiB wire, 250 KiB pack — within noise of one file, for an assembly step.
By song, which looks appealing because a new show touches only the songs it
played: **497 KiB pack and 286 KiB wire, fourteen times worse.** Git deltas one
large append-only file near-perfectly; twenty small rewritten files become
twenty new blobs plus a new tree over a 981-entry directory every night, and
small blobs do not delta. Sharding by song also breaks the unit of use — the
consumer, `setlist_neighbors`, takes one show's rows at a time.

**JSONL, because of the diff.** As a single JSON document a backfilled show
landed mid-history as one changed line of 3.3 MB. `git diff --numstat` called
that "1 line" either way, so a pull request summary read as harmless while the
diff itself was 7 MB of unreadable. One date per line makes the same insert a
13.7 KB one-line diff. This matters most during the pre-2009 backfill, which is
all mid-history inserts.

Written 2026-07-30, after a session in which the record of which setlists had
been walked was destroyed and 1,966 of them had to be fetched a second time —
see `docs/TODO.md` §0 and the `nb` notes in `CLAUDE.md`. Keeping the running
order means the neighbor rules can change again without re-fetching anything,
which they did, the next day. Converted to JSONL and wired into `--catch-up` on
2026-07-31.
