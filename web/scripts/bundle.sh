#!/bin/bash
# Build the app into one self-contained HTML file, following the web-artifacts-builder
# skill: Parcel build, then inline every asset with html-inline.
#
#   bundle.html         standalone page; serve it next to a data/ folder
#   dist/artifact.html  same page for a claude.ai artifact: <title> first, no outer
#                       html/head/body (the artifact host adds its own skeleton)
#
# Course data is NOT inlined; the page fetches ./data/*.json at runtime.
set -euo pipefail
cd "$(dirname "$0")/.."
rm -rf dist bundle.html
pnpm exec parcel build index.html --dist-dir dist --no-source-maps --no-cache
pnpm exec html-inline dist/index.html > bundle.html
node -e '
const fs = require("fs")
let s = fs.readFileSync("bundle.html", "utf8")
const title = s.match(/<title>.*?<\/title>/)[0]
s = s.replace(title, "")
for (const re of [/<!DOCTYPE html>/i, /<html[^>]*>/i, /<\/html>/i, /<head>/i, /<\/head>/i,
                  /<body>/i, /<\/body>/i, /<meta charset=[^>]*>/i, /<meta name=viewport[^>]*>/i])
  s = s.replace(re, "")
fs.writeFileSync("dist/artifact.html", title + "\n" + s)
'
echo "bundle.html ($(du -h bundle.html | cut -f1)), dist/artifact.html"
