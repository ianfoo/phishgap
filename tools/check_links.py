#!/usr/bin/env python3
"""Every internal link in the built site resolves -- file *and* fragment.

    python3 tools/check_links.py [site_dir]

Exits non-zero and names each bad link. Run it after `--rebuild`, before
believing anything about where a link goes.

This exists because "method.html has no id 'rotation'" was reported, believed
and acted on, and was false: the id was there, in the same published build as
the commit that routed around it. The sentence on the out-of-rotation page
offering to show the measurement was moved off the section that holds the
measurement and onto the one about a different eight -- MIN_HISTORY, which
gates a verdict, rather than ROTATION_PLAYS, which counts plays ever. Those two
constants are deliberately separate and this site has a page explaining each.

A claim about a link is cheap to settle and expensive to get wrong, so it
should be settled by running something. Reading a page and reporting what you
did not see is not a measurement.

Checks, over every .html the build produced:

  * `href` to a file that does not exist
  * `href="#frag"` where this page has no element with that id
  * `href="other#frag"` where that page has no element with that id
  * ids that repeat within one page, which makes a fragment ambiguous
  * an internal `href` that still carries `.html`, which resolves perfectly
    and is wrong anyway -- see below

Query strings are stripped before resolving: the venue links are
`?q=%22...%22`, and an earlier version of this check called all 153 of them
broken.

Links are extensionless -- `href="./method"`, not `href="./method.html"` --
so resolving one to the file that answers it is tools/pathmap.py's job, the
same rule tools/serve.py uses. A link that resolves here resolves in the
browser only if all three of pathmap, the local server and GitHub Pages agree;
that is why the rule is written once.
"""
import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pathmap  # noqa: E402

HREF = re.compile(r"""href=["']([^"']+)["']""")
ID = re.compile(r"""\bid=["']([^"']+)["']""")
EXTERNAL = ("http://", "https://", "mailto:", "tel:", "data:", "//")


def html_files(root):
    for base, _dirs, names in os.walk(root):
        for n in sorted(names):
            if n.endswith(".html"):
                yield os.path.join(base, n)


def main(root="site"):
    if not os.path.isdir(root):
        print("no such directory: %s -- build the site first" % root)
        return 2

    pages = list(html_files(root))
    if not pages:
        print("no .html under %s -- build the site first" % root)
        return 2

    # One pass for ids, so a page linked from a thousand others is read once.
    ids, dupes = {}, []
    for path in pages:
        with open(path, encoding="utf-8") as fh:
            found = ID.findall(fh.read())
        ids[os.path.realpath(path)] = set(found)
        for name, n in Counter(found).items():
            if n > 1:
                dupes.append((path, name, n))

    bad = []
    for path in pages:
        with open(path, encoding="utf-8") as fh:
            body = fh.read()
        here = os.path.realpath(path)
        for href in HREF.findall(body):
            if href.startswith(EXTERNAL) or href == "#":
                continue
            target, _, frag = href.partition("#")
            target = target.split("?")[0]
            # The site links extensionless, and `./faq.html` would *work* --
            # the file is right there, and Pages and pathmap both serve it. So
            # nothing else in this project can notice the convention breaking:
            # no 404, no broken build, just two URL forms in circulation and a
            # canonical tag pointing at whichever one share_meta computed. A
            # rule that cannot fail visibly has to be checked deliberately.
            if target.endswith(".html"):
                bad.append((path, href,
                            "links .html; the site links extensionless"))
            if not target:
                if frag not in ids[here]:
                    bad.append((path, href, "no id %r on this page" % frag))
                continue
            # Resolved the way the host resolves it, so that an extensionless
            # `href="./method"` is checked against method.html -- and, just as
            # importantly, so `dest` is the *file*. Accepting the bare path as
            # "exists" would quietly skip every fragment check below, leaving a
            # check that still passes and no longer checks.
            dest = pathmap.resolve(os.path.realpath(
                os.path.join(os.path.dirname(path), target)))
            if dest is None:
                bad.append((path, href, "no such file"))
                continue
            dest = os.path.realpath(dest)
            if frag and dest in ids and frag not in ids[dest]:
                bad.append((path, href,
                            "%s has no id %r" % (os.path.basename(dest), frag)))

    rel = lambda p: os.path.relpath(p, root)
    for path, name, n in dupes:
        print("DUPLICATE ID  %s  id=%r appears %d times" % (rel(path), name, n))
    for path, href, why in bad:
        print("BROKEN LINK   %s  ->  %s  (%s)" % (rel(path), href, why))

    total = len(bad) + len(dupes)
    print("%d pages checked, %d links, %d problem(s)"
          % (len(pages),
             sum(len(HREF.findall(open(p, encoding="utf-8").read()))
                 for p in pages),
             total))
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "site"))
