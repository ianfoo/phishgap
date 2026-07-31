#!/usr/bin/env python3
"""The built site, served the way GitHub Pages serves it.

    python3 tools/serve.py [port] [site_dir]

`python3 -m http.server` 404s on every extensionless link, so with the site
linking `/song/tweezer` it would disagree with production on every single
navigation -- the exact shape of failure this project keeps hitting, where the
local check is wrong in a way that reads as a real bug. This adds the one thing
Pages does that http.server does not: fall back to `<path>.html`.

The rule itself is in tools/pathmap.py, shared with tools/check_links.py.
"""
import os
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pathmap  # noqa: E402


class Handler(SimpleHTTPRequestHandler):
    def translate_path(self, path):
        fs_path = super().translate_path(path)
        return pathmap.resolve(fs_path) or fs_path

    def list_directory(self, path):
        """404, because that is what Pages does.

        `/song/` has no index.html, and http.server would answer it with a
        generated file listing -- a 200 where production returns 404, and a
        page that exists locally and nowhere else. Measured 2026-07-31:
        /song/, /show/ and /data/ were 200 here and 404 live.
        """
        self.send_error(404, "File not found")
        return None

    def log_message(self, fmt, *args):
        sys.stderr.write("%s %s\n" % (self.address_string(), fmt % args))


def main(port=8769, site_dir="site"):
    if not os.path.isdir(site_dir):
        print("no such directory: %s -- build the site first" % site_dir)
        return 2
    handler = partial(Handler, directory=site_dir)
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    print("serving %s at http://127.0.0.1:%d/ (extensionless, as Pages does)"
          % (site_dir, port))
    server.serve_forever()


if __name__ == "__main__":
    sys.exit(main(int(sys.argv[1]) if len(sys.argv) > 1 else 8769,
                  sys.argv[2] if len(sys.argv) > 2 else "site"))
