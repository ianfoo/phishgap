# Build inputs, not reader data

Nothing here is published. The workflows copy `site/.` to `gh-pages`, so this
directory is tracked in git and available to CI without shipping to readers.

## `setlist-order.json`

The running order of every **settled** show the archive has a performance for:
one entry per date, each a list of `{set, position, slug, song, trans_mark}`
sorted by `SET_ORDER` then position, Phish only. 2,008 dates.

It exists because the running order is the one thing the song-history endpoint
does not give you. `/setlists/slug/<song>` says every night a song was played;
only `/setlists/showdate/<date>` says what stood next to it. That is one call
per show, and this file is what stops us paying for them again.

**It is a derived extract, not a cache of API responses.** Only the five fields
above are kept. Everything else the endpoint returns — reviews, ids, permalinks,
tour metadata, ratings, footnotes — is dropped, either because the archive
already stores it or because it has no use here. `CACHE_TTL` in
`possumlogic.py` still expires actual API responses after six hours; that is
unchanged and should stay.

**Settled only, and this is the important part.** The first harvest ran during a
show and wrote that night down at the 12 songs it had at the time. An extract is
a cache with no expiry, so reading that back would have frozen the running order
of the one show whose order was still moving. `--seed-setlists` therefore always
re-fetches a show whose report is `provisional`, and never writes one here: a
partial record stops being skipped and starts being believed the day the show
settles.

`--seed-setlists` maintains this file. It walks what is here, buys only the
dates that are not, and writes those back — so a rule change costs nothing for
everything already recorded. The full re-walk on 2026-07-30 cost 44 calls
against 2,009 shows. `--force` re-walks everything; no API key is needed if this
file covers the dates.

Nothing in CI writes it: it is one 3.4 MB document, and a nightly append would
put a fresh 3.4 MB blob in git history every day. So it lags by however many
nights since someone ran the seed by hand. That costs nothing until the rules
change again, and then one call per un-archived night. **Shard it by year before
letting CI maintain it.**

Written 2026-07-30, after a session in which the record of which setlists had
been walked was destroyed and 1,966 of them had to be fetched a second time —
see `docs/TODO.md` §0 and the `nb` notes in `CLAUDE.md`. Keeping the running
order means the neighbour rules can change again without re-fetching anything,
which they did, the next day.
