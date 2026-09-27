#!/bin/bash
# Publish the web UI and the latest course data to GitHub Pages (branch gh-pages).
#
#   1. export the newest data of every crawled semester (python -m ntu_courses export-web)
#   2. build the single-file web app (web/scripts/bundle.sh)
#   3. commit index.html + data/ to the gh-pages branch and push it
#
# The main branch and your working tree are never touched: gh-pages is updated in a
# temporary git worktree, and each deploy is a normal (non-force) commit on that branch.
#
# Usage: scripts/deploy_pages.sh [--dry-run]     (--dry-run builds and commits locally, no push)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
BRANCH=gh-pages
REMOTE=origin
DRY_RUN=0
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=1

echo "==> Exporting course data"
python3 -m ntu_courses export-web

echo "==> Building web app"
(cd web && pnpm install --frozen-lockfile --silent && pnpm run bundle)

SITE="$(mktemp -d)"
WT="$(mktemp -d)"
rmdir "$WT"  # git worktree add wants to create it
cleanup() {
  git worktree remove --force "$WT" 2>/dev/null || true
  rm -rf "$SITE" "$WT"
}
trap cleanup EXIT

cp web/bundle.html "$SITE/index.html"
cp -r web/public/data "$SITE/data"
touch "$SITE/.nojekyll"  # serve files as-is, no Jekyll processing

echo "==> Preparing $BRANCH"
if git fetch --quiet "$REMOTE" "$BRANCH" 2>/dev/null; then
  if git show-ref --quiet "refs/heads/$BRANCH" && git merge-base --is-ancestor "$REMOTE/$BRANCH" "$BRANCH"; then
    git worktree add --quiet "$WT" "$BRANCH"                     # local is ahead (e.g. after --dry-run)
  else
    git worktree add --quiet -B "$BRANCH" "$WT" "$REMOTE/$BRANCH"
  fi
elif git show-ref --quiet "refs/heads/$BRANCH"; then
  git worktree add --quiet "$WT" "$BRANCH"                       # not pushed yet
else
  git worktree add --quiet --orphan -b "$BRANCH" "$WT"           # first deploy
fi

find "$WT" -mindepth 1 -maxdepth 1 ! -name .git -exec rm -rf {} +
cp -r "$SITE"/. "$WT"/

SOURCE="$(git rev-parse --short HEAD)$(git diff --quiet HEAD -- ntu_courses web || echo '-dirty')"
SEMESTERS="$(python3 -c 'import json,sys; print(", ".join(s["label"] for s in json.load(open(sys.argv[1]))))' "$SITE/data/semesters.json")"

cd "$WT"
git add -A
if git diff --cached --quiet; then
  echo "==> Site unchanged since the last deploy commit"
else
  git commit --quiet -m "Deploy site from $SOURCE" -m "Semesters: $SEMESTERS"
  echo "==> Committed $(git rev-parse --short HEAD) on $BRANCH"
fi

if [[ $DRY_RUN == 1 ]]; then
  echo "Dry run: not pushed. Inspect with: git log $BRANCH"
  exit 0
fi
git push --quiet "$REMOTE" "$BRANCH"  # no-op when already up to date

REPO_URL="$(git -C "$ROOT" remote get-url "$REMOTE")"
OWNER_REPO="$(sed -E 's#(git@github.com:|https://github.com/)##; s#\.git$##' <<<"$REPO_URL")"
echo "==> Pushed. Site: https://$(cut -d/ -f1 <<<"$OWNER_REPO" | tr 'A-Z' 'a-z').github.io/$(cut -d/ -f2 <<<"$OWNER_REPO")/"
