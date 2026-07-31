#!/usr/bin/env python3
"""How a URL path becomes a file, in the one place that decides it.

The site links extensionless -- `/song/tweezer`, not `/song/tweezer.html` --
while the files on disk keep their extensions and stay flat. Something has to
bridge that, and in production it is GitHub Pages, which serves `/song/tweezer`
from `song/tweezer.html` with no redirect (verified 2026-07-31: both forms 200,
byte-identical, same etag). Netlify, Cloudflare Pages, Vercel, Apache
MultiViews and nginx `try_files $uri $uri.html` all do the same thing; Pages is
unusual only in not redirecting one form to the other.

Locally there is no Pages, so `tools/serve.py` and `tools/check_links.py` have
to reproduce the rule -- and if their two copies of it ever drift, the checker
passes while the server 404s, or the reverse. That is the failure this project
keeps having: a local check that lies. So the rule lives here once and both
import it.

The order below is measured, not assumed. A throwaway Pages deploy on
2026-07-31 built every collision deliberately and was asked what it served:

  * `/b`, with both `b.html` and `b/index.html` present -> **`b.html`**, no
    redirect, and the same etag as `/b.html`. The flat file wins.
  * `/b/` -> `b/index.html`. The trailing slash is what asks for the directory.
  * `/c`, with `c.html` beside a `c/` holding only `c/sub.html` -> `c.html`,
    and `/c/sub` -> `c/sub.html`.
  * `/c/`, a directory with no index.html -> 404. Which is why the server in
    tools/serve.py refuses to list directories: http.server would answer that
    with a generated listing, a 200 where production 404s.

So a page can own a directory of sub-views without losing its own URL or
growing a trailing slash: `/song/tweezer` and `/song/tweezer/gaps` coexist,
and `song/tweezer/` needs no index.html. No such collision exists in the site
today, but nothing has to be redesigned the day one does.
"""
import os


def resolve(fs_path):
    """The file that answers `fs_path`, or None if nothing does.

    `fs_path` is already filesystem-side: query string and fragment stripped,
    joined against the document root by the caller.
    """
    if os.path.isfile(fs_path):
        return fs_path
    if os.path.isfile(fs_path + ".html"):
        return fs_path + ".html"
    if os.path.isdir(fs_path):
        index = os.path.join(fs_path, "index.html")
        if os.path.isfile(index):
            return index
    return None
