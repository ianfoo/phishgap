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
`INDEX_CSS` and `SONG_CSS`; `SONGS_CSS` and `METHOD_CSS` extend `INDEX_CSS`. A
plain string replace on a CSS rule will hit two or three of them. Anchor on a
neighbouring line that differs and assert the match count.

**`body` is IBM Plex Mono site-wide.** Literata is loaded and applied
deliberately to running prose (`.jam`, `.note`, `.prose`). Mono prose anywhere
else is usually an artifact of that default rather than a decision.

**Anything long-running must re-read its inputs each pass.** Three separate
outages have had one shape — a job that publishes from something it read once:
a swallowed rebase conflict published a site missing the show it was watching;
a six-hour HTTP cache served one watcher the same setlist for five hours; a
resident watcher republished the whole site from its startup commit every five
minutes, reverting everything pushed during a show. Assume a fourth exists.

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
