# Build inputs, not reader data

Nothing here is published. The workflows copy `site/.` to `gh-pages`, so this
directory is tracked in git and available to CI without shipping to readers.

## `setlist-order.json`

The running order of every show the archive has a performance for: one entry per
date, each a list of `{set, position, slug, song, trans_mark}` sorted by
`SET_ORDER` then position, Phish only. 1,966 dates, 39,337 rows.

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

Regenerate by re-running `--seed-setlists` and re-extracting, at one call per
date. Written 2026-07-30, after a session in which the record of which setlists
had been walked was destroyed and 1,966 of them had to be fetched a second time
— see `docs/TODO.md` §0 and the `nb` notes in `CLAUDE.md`. Keeping the running
order means the neighbour rules can change again without re-fetching anything.
