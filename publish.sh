#!/bin/sh
# Copy the built site/ onto the gh-pages branch and push it. Same steps the
# scheduled workflow runs, for when you want to publish by hand.
set -eu

cd "$(dirname "$0")"

if [ ! -f site/index.html ]; then
    echo "no site/index.html -- build the site first:" >&2
    echo "  ./phishgap.py --site site --previous --catch-up" >&2
    exit 1
fi

# Publish onto whatever is on the remote, not onto whatever this clone last
# saw. `git fetch origin gh-pages` moves origin/gh-pages and FETCH_HEAD but
# leaves the local gh-pages branch where it was, so checking that branch out
# built the new commit on a stale base: every publish the scheduled workflow
# made in between was an ancestor this one did not have, and the push came back
# rejected as non-fast-forward. Nothing here is ever edited by hand -- the tree
# is replaced wholesale below -- so the remote tip is always the right base.
git fetch origin gh-pages
work=$(mktemp -d)
trap 'git worktree remove --force "$work" 2>/dev/null || true' EXIT
git worktree add --detach "$work" origin/gh-pages >/dev/null

# Replace the published tree wholesale so deleted reports actually disappear.
find "$work" -mindepth 1 -maxdepth 1 -not -name .git -exec rm -rf {} +
cp -R site/. "$work"/

cd "$work"
git add -A
if git diff --cached --quiet; then
    echo "site unchanged, nothing to publish"
else
    git commit -q -m "Publish $(date -u +%F)"
    # Detached HEAD, so name both ends. A rejection here means the workflow
    # published while this ran; re-running picks up its commit and replays.
    git push origin HEAD:gh-pages
    echo "published $(ls show/*.html 2>/dev/null | wc -l | tr -d ' ') reports, $(ls song/*.html 2>/dev/null | wc -l | tr -d ' ') song pages, $(ls *.html | wc -l | tr -d ' ') top-level"
fi
