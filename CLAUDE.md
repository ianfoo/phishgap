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

**Three base stylesheets carry identical rule text.** `CSS` (show pages),
`INDEX_CSS` and `SONG_CSS`; `SONGS_CSS`, `METHOD_CSS` and `FAQ_CSS` extend
`INDEX_CSS`. A plain string replace on a CSS rule will hit two or three of
them. Anchor on a neighbouring line that differs and assert the match count.
The reverse costs more: a rule added to one sheet and not the others is
invisible until something leans on it — two bugs in one night that way, a nav
that could not wrap and a footer link left in the browser's default blue.
Measured and costed in `docs/TODO.md` §8e; fix the composition, not the copies.

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
