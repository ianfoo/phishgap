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

`site/song/tweezer.html` and `site/song/tweezer/` can coexist on disk, and it
is *not* verified what Pages serves for `/song/tweezer` when both are there.
No such collision exists in the site today. The order below prefers the flat
file, on the principle that the page is the file; if sub-views are ever added
under a page's own directory, settle what Pages actually does first rather than
trusting this.
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
