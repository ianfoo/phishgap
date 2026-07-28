# Working on possumlogic

`possumlogic.py` is one file that builds a static site from the phish.net API
and publishes it to <https://possumlogic.com>. The README covers what the tool
does. This file covers how to work on it without repeating the mistakes it has
already made.

## Commands

```bash
./possumlogic.py --site site --rebuild      # re-render everything from the local archive, no API calls, ~2s
python3 -m py_compile possumlogic.py        # syntax check before you claim anything works
./publish.sh                                # publish by hand (the workflows normally do this)
./possumlogic.py --site site --watching     # is a show in its watch window right now?
```

The rebuild is two seconds. There is never a reason to reason about what the
output *would* look like — build it and look.

Serve the built site with the `site` entry in `.claude/launch.json`
(`python3 -m http.server 8769 --directory site`). Verifying over `file://` is
misleading: `history.pushState` and other same-origin APIs behave differently.

## The one rule this project keeps learning

**Verify the artifact the reader actually gets.** Not the source, not the
markup count, not your intent. This has failed in every session so far:

- Counting elements in HTML proves markup exists, not that it is styled or
  visible. Render it.
- `grep`ping the source proves you typed it. It does not prove it shipped.
- **Verify the *published* thing, not the local build.** The live site and a
  local build disagreed for over an hour and every local check passed.
- **Check `origin/gh-pages` with git, not the live URL with `curl`.** Pages
  serves `max-age=600`, so a `curl` can be ten minutes stale and look exactly
  like a failed publish. `git fetch origin gh-pages && git show
  origin/gh-pages:index.html | grep -c ...` is the ground truth.
- Programmatic `.focus()` does not reliably match `:focus-visible`. Testing
  focus styles that way reported "no focus ring at all", which was wrong.
  Drive the real key.

## Measure before you act on a claim

Assertions in this repo's own docs, in review output, and in `docs/TODO.md`
have been confidently wrong. Two examples from one session: the backlog said
the empty range bar was a bustout problem (it is any song under 8 plays in ten
years), and it prescribed a fix for search cost aimed at the wrong thing —
measured, attribute writes are constant at 691 while the pass ranges 0.3–36 ms
depending on how many rows *change* visibility.

When a measurement contradicts the backlog, fix the backlog too.

## Decline rather than guess

This is a reference archive; a wrong figure is worse than a missing one.

- phish.net files 35 shows as "Not Part of a Tour" (festivals, TV sessions,
  the Mexico runs). The festival name exists only in freeform notes prose. A
  regex over it found 3 of 35 and spelled two of them differently. Three
  inconsistent labels are worse than 35 blanks — so the site says nothing.
- The site computes its own "shows since" and says so, because phish.net's gap
  is not reproducible from a show calendar. Do not try to match their number.

## Long-lived jobs publish from something they read once

Three separate outages have had this exact shape. Assume the fourth exists.

1. A conflicted rebase was swallowed, so the watcher published a site *without
   the show it was watching* — every five minutes, over correct publishes.
2. The setlist was served from a six-hour cache, so a five-hour watch re-read
   the same response forever.
3. The watcher checked the repo out once and republished the whole site from
   that frozen commit every five minutes, reverting every change pushed during
   a show.

Anything that runs for hours must re-read its inputs — the API, the repo, the
remote — at the top of each pass, not once at startup.

## Code style

Read the surrounding code before writing any. The house style is unusual and
deliberate:

- **Comments explain *why*, at length, and often record what was tried and
  failed.** They are the project's memory. Match that register — a comment
  saying what the line does adds nothing here.
- Commit messages are prose in the same voice: what was wrong, what a reader
  saw, what changed. Imperative subject, no ticket refs.
- The JS is deliberately ES5-flavoured (`var`, `Array.prototype.slice.call`)
  and inline in the page. `fetch`/`IntersectionObserver`/`:has()` are already
  used, so that tier is fine; keep to it.

### Editing the stylesheets

There are three base stylesheets — `CSS` (show pages), `INDEX_CSS`,
`SONG_CSS` — and `SONGS_CSS` and `METHOD_CSS` extend `INDEX_CSS`. **Rule text
is frequently identical across them**, so a naive string replace hits two or
three places. Anchor on a neighbouring line that differs, assert the match
count in a script, and know which sheet you meant.

`body` is `IBM Plex Mono` site-wide; Literata is loaded and used deliberately
for running prose (`.jam`, `.note`, `.prose`). Mono prose elsewhere is usually
an artifact of that default, not a decision.

### Typography is load-bearing here

Ian notices, and is right to. Recurring traps:

- **Separators that can strand.** A `::before` middot on an element prints
  whenever that element does, including when the thing it was separating from
  is absent. Make the separator its own element emitted only with something on
  both sides — make the artifact impossible, not relocated.
- **Wrapping layouts that indent a row.** A wrapped flex row gives the first
  card of line two a left rule against the page margin. Tie such rules to a
  *column position* (grid), not to wrap order.
- **Restating a rule at two breakpoints.** The wide rule outranks the narrow
  one and something ends up half a space out of line. Let each width state its
  own.
- Do not remove the 2px paper halo on `.at`; it is the only reason the marker
  reads against the band.

## Working with Ian

- He thinks out loud. An idea is not always an instruction — propose and
  measure. When he does decide something mid-message, build it or say plainly
  that it is outstanding.
- He would rather you keep working than stop to ask. Make a **provisional
  decision** when it is cheap to reverse, record it in `docs/TODO.md` §8b for
  batched review, and continue. Defer only decisions too expensive to unwind.
- On a permissions or scope failure, give him the command to run rather than
  working around it.
- Check rendered output in **both light and dark**; alpha and contrast differ
  per palette and reasoning from the CSS gets it wrong.
- **Do not commit or push unless asked.** The site is public and the workflows
  publish on push.

## docs/TODO.md is the handoff

It opens with a §0 "where the session left off" block: in-flight state, the
ordered queue, and the verification commands to re-run. Read it first and keep
it current — carry the *whole* backlog forward, not just the part of it the
current conversation is about. Work has been silently dropped that way before,
which is why §3b exists.
