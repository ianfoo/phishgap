---
name: verify-site
description: Verify a possumlogic site change actually reached the reader — rendering, published output, and measurement discipline. Use before claiming any site change works, when a local build and the live site disagree, or when checking styling, layout, focus, or accessibility.
---

# Verifying a possumlogic change

Every session so far has reported something as done that was not, in one of
the ways below. The check is always cheap.

## Look at the artifact, not the source

`grep`ping `possumlogic.py` proves you typed it. Counting elements in the
built HTML proves markup exists — not that it is styled, visible, or correct.

Rebuild (`--rebuild`, ~2s), serve via the `site` entry in
`.claude/launch.json`, and look at the rendered page.

- **Screenshot anything visual.** Contrast and alpha differ per palette, so
  check light *and* dark; reasoning from the CSS gets this wrong.
- **Drive real input for interaction.** Programmatic `.focus()` does not
  reliably match `:focus-visible` — testing focus styles that way once
  reported "no focus ring at all", which was false. Press the real key.
- The browser pane sometimes reports `innerWidth: 0` and returns blank
  screenshots. Resize it and retake rather than trusting the measurement.
- **Prove the state you are claiming, not its opposite.** A control that hides
  itself needs its *hidden* state measured; the floating back-to-top button was
  permanently visible for two days because `hidden` loses to an author
  `display`, and every screenshot of it showed it working.

## The browser pane cannot test IntersectionObserver

Its top-level document reports `innerWidth`/`innerHeight` of 0, so IO has no
root, and it never fires — not even the mandatory initial callback. This is
silent: no error, the observer just never runs. The site's own sticky header
does not activate there either, which is the quick way to tell the pane apart
from your change. That covers `.stuck`, `.totop`, and anything else keyed to
the header leaving the viewport.

Headless Chrome does fire it. Put the page in an iframe on a harness page under
`site/` (same origin, so you can script it), drive it, and read the result out
with `--dump-dom`:

```bash
"$(python3 -c 'import possumlogic;print(possumlogic.chrome_exe())')" --headless \
  --disable-gpu --hide-scrollbars --window-size=1400,900 \
  --virtual-time-budget=40000 --dump-dom "http://localhost:8769/_probe.html?p=/due.html"
```

Two things that will bite. **Poll to a settled state rather than sleeping** —
an intersection callback lands on the rendering lifecycle, and a fixed wait had
the same page reporting both answers on consecutive runs; loop on
`requestAnimationFrame` until the value is what you are waiting for, with a
frame cap. And **delete the harness and rebuild before committing**, or it
ships and lands in `sitemap.xml`.

## Local build and published site are different questions

The live site and a local build disagreed for over an hour while every local
check passed.

```bash
git fetch origin gh-pages
git show origin/gh-pages:index.html | grep -c 'the-thing-you-shipped'
```

Use that, not `curl`. Pages serves `max-age=600`, so a `curl` can be ten
minutes stale and is indistinguishable from a failed publish. Pages also adds
60–90s of deploy lag after each push.

If the published tree is missing a change that is on `main`, suspect a
long-lived job republishing from an old checkout before suspecting the build.

## Measure before acting on a claim

Assertions in `docs/TODO.md`, in review output, and in prior sessions' notes
have been confidently wrong. Two from one session: the empty range bar was
recorded as a bustout problem when it is any song under 8 plays in ten years;
and a prescribed performance fix targeted attribute writes when writes are
constant and the cost tracks rows that *change* visibility.

Measure first. When a measurement contradicts the backlog, correct the backlog
in the same change.

## Prove the invariant, not the example

One passing case is not the property. When venue links were switched to
quoted phrases, the check was to replay all 153 venue links against the built
haystack and assert each returned exactly its own shows — which is how the 6
broken ones were found, and how the fix was shown to hold.

For workflow changes, exercise the failure paths against a real remote: the
`possumlogic.yml` publish retry was tested for stale base, nothing-to-publish,
rejected-then-replayed, and give-up-cleanly, and that run caught an invalid
`git worktree prune -q` before it ever ran in anger.
