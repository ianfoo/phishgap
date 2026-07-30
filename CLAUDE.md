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
`CSS` (show pages), `INDEX_CSS` and `SONG_CSS`; `SONGS_CSS`, `METHOD_CSS` and
`FAQ_CSS` extend `INDEX_CSS`. The rules that were identical in all three live
in `BASE_CSS`, `BODY_BOX_CSS`, `NAV_HIT_CSS`, `RULE2_CSS`, `FIGURE_CSS` and
`FOOTER_LINK_CSS` — edit those once. **Everything else is still copied**:
32–46 rules repeat pairwise, and the near-misses (`footer{…}`, `.crumb{…}`,
`.hero{…}`) differ by real amounts. So a plain string replace on any rule
outside a named block will still hit two or three sheets, or — worse — one.
Anchor on a neighbouring line that differs and assert the match count. Four
bugs have come out of the copies: a nav that could not wrap, a footer link in
the browser's default blue, a sticky-header hide out-specified by a modifier
class, and tabular figures on show pages only. `docs/TODO.md` §8e.

**Drawing preview cards locally poisons CI.** `site/data/cards.json` records
what each card was drawn from and is tracked; `site/card/*.png` is gitignored.
So a local `--rebuild` draws the images here, writes "already drawn" into a
file that ships, and CI then restores the *published* PNGs, sees an index
claiming everything is current, and draws nothing. The markup updates and the
images do not. **This is the fourth instance of the shape below** — a record
that outlives the work it records. Check the published PNG, not the log line.

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
