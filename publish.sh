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

git fetch origin gh-pages
work=$(mktemp -d)
trap 'git worktree remove --force "$work" 2>/dev/null || true' EXIT
git worktree add "$work" gh-pages >/dev/null

# Replace the published tree wholesale so deleted reports actually disappear.
find "$work" -mindepth 1 -maxdepth 1 -not -name .git -exec rm -rf {} +
cp -R site/. "$work"/

cd "$work"
git add -A
if git diff --cached --quiet; then
    echo "site unchanged, nothing to publish"
else
    git commit -q -m "Publish $(date -u +%F)"
    git push origin gh-pages
    echo "published $(ls *.html | wc -l | tr -d ' ') pages"
fi
