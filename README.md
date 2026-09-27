# NTU Undergraduate Course Scraper

English | [中文](README_zh.md)

Scrapes complete course information for every NTU undergraduate programme, year and semester, and archives it as snapshots.

| Source | Provides |
|---|---|
| [Class Schedule](https://wish.wis.ntu.edu.sg/webexe/owa/AUS_SCHEDULE.main) (`AUS_SCHEDULE`) | index, type, group, day, time, venue, teaching weeks, AU, UE/BDE/GE flags |
| [Content of Courses](https://wish.wis.ntu.edu.sg/webexe/owa/aus_subj_cont.main) (`AUS_SUBJ_CONT`) | description, prerequisites, mutually exclusive courses, grade type, programme restrictions |

The two are merged by course code.

## Installation

Requires Python 3.10+.

```bash
pip install -r requirements.txt
```

## Commands

`--sem` accepts either the semester key or the label shown on the NTU site (case-insensitive). If omitted, the first semester in the site's dropdown (the latest) is used.

| Key | Label |
|---|---|
| `2026_1` | `"Acad Yr 2026 Semester 1"` |
| `2025_2` | `"Acad Yr 2025 Semester 2"` |
| `2025_S` | `"Acad Yr 2025 Special Term"` |

Keys may also be written `2026-1` or `2026;1`. In a shell, `;` separates commands, so the `;` form must be quoted (`'2026;1'`). Run `python -m ntu_courses semesters` for the full list.

```bash
# Semesters offered on the site (key and label)
python -m ntu_courses semesters

# Programme/year options for a semester; -f filters by keyword
python -m ntu_courses programmes --sem 2026_1 -f computer

# Live view of a programme/year; -c shows one course, --no-desc hides descriptions
python -m ntu_courses show -p 'CSC;;1;F' --sem "Acad Yr 2026 Semester 1" -c SC1005

# Search the class schedule by course code or keyword
python -m ntu_courses search SC100 --sem 2026_1

# Crawl and archive (writes a new snapshot)
python -m ntu_courses crawl                           # latest semester
python -m ntu_courses crawl --sem 2025_2 --sem 2025_S # specific semesters (repeatable)
python -m ntu_courses crawl --all                     # every semester in the dropdown
python -m ntu_courses crawl --limit 5 --data /tmp/t   # trial run: first 5 programmes, temp directory

# List saved snapshots (* marks LATEST)
python -m ntu_courses snapshots

# Export the newest data of every crawled semester for the web UI (offline)
python -m ntu_courses export-web
```

The global option `--delay` (default 0.5 s) sets the minimum interval between requests. It goes before the subcommand, e.g. `python -m ntu_courses --delay 1 crawl`. A semester has about 680 programme/year options, so a full crawl takes roughly 15–20 minutes. Redirecting output to a log file is recommended:

```bash
mkdir -p logs && python -m ntu_courses crawl > logs/crawl_$(date +%F).log 2>&1
```

## Snapshot archive

```
data/
  LATEST                         name of the newest complete snapshot
  snapshots/
    2026-09-26T053215Z/          one directory per crawl (UTC time); never modified or overwritten
      manifest.json              crawl time, per-semester hash, programme/course/index counts, errors
      2026_1.json.gz             one file per semester
```

- **Append-only**: every `crawl` creates a new snapshot; existing snapshots are left untouched.
- **Per-semester dedup**: if a semester is identical to the previous crawl, the manifest records `stored_in` pointing at the existing file instead of storing it again.
- **Only complete snapshots become LATEST**: if any programme still fails after one retry, the snapshot is saved with `complete=false` and `LATEST` is not moved.
- **No half-written snapshots**: data is written to a `.tmp` directory and renamed only when finished.

## Data format

Each semester file (gzipped JSON) looks like this:

```jsonc
{
  "format": 2,
  "semester": {"key": "2026;1", "year": 2026, "sem": "1", "label": "Acad Yr 2026 Semester 1"},
  "fetched_at": "2026-09-26T05:14:49+00:00",
  "errors": [],                       // programmes that failed to fetch
  "courses": {                        // each course stored once
    "SC1005": {
      "code": "SC1005", "title": "DIGITAL LOGIC", "au": 3.0,
      "description": "This course aims to ...",
      "attributes": {"Mutually exclusive with": "CE1005, ...", "Prerequisite": "..."},
      "indexes": [                    // union of indexes seen on all programme pages
        {"index": "10081", "sessions": [
          {"type": "LEC/STUDIO", "group": "LE1", "day": "MON", "time": "0830-0920",
           "venue": "LT1A", "remark": ""}
        ]}
      ]
    }
  },
  "programmes": [                     // every programme/year in the site's dropdown is listed
    {"value": "CSC;;1;F", "label": "Computer Science Year 1", "content_value": "CSC;;1;F",
     "status": "ok",                  // ok | empty (no courses on the site this term) | error (fetch failed)
     "courses": [
       {"code": "SC1005", "is_ue": false, "is_bde": true, "is_self_paced": false, "is_ge_pe": false,
        "remark": "...",              // optional: Remark shown on this programme's page
        "indexes": ["10081", "..."]}  // optional: indexes shown to this programme; absent = all
     ]},
    {"value": "ACBS;RMI;2;F", "label": "Accountancy And Business (RMI) Year 2",
     "content_value": "ACBS;RMI;2;F", "status": "empty", "courses": []}
  ]
}
```

Notes:

- **Programmes are never dropped.** Programmes with no courses, or that failed to fetch, are kept with an empty `courses` list; `status` tells you why. List them in the UI like any other programme.
- **Programme-specific fields live on the programme.** UE/BDE/GE flags, Remark and visible indexes depend on the student's programme, so they are stored under `programmes[].courses[]`. `courses` only holds programme-independent information.
- **Courses with no class schedule.** A course with an empty `indexes` list appears only on the course content page and has no classes this semester.
- **Programme value format.** `value` is `programme;specialisation;year;F/P` (F = full time, P = part time). Minors are `MLOAD;…`, BDE/UE are `GLOAD;…`, and General Education is `GERP;…`.

### Reading from Python

```python
from ntu_courses.snapshot import Archive

archive = Archive("data")
data = archive.load_semester(archive.latest(), "2026;1")   # older snapshot formats are converted on load

prog = next(p for p in data["programmes"] if p["value"] == "CSC;;1;F")
for entry in prog["courses"]:
    course = data["courses"][entry["code"]]
    print(course["code"], course["title"], len(course["indexes"]))
```

Or query the site directly, bypassing snapshots:

```python
from ntu_courses import NTUClient, Semester

client = NTUClient()
courses = client.courses(Semester(2026, "1"), "CSC;;1;F")   # list[Course]
```

## Web UI

`web/` is a React + TypeScript + Tailwind + shadcn/ui app (scaffolded with the `web-artifacts-builder` skill). Pick a semester (every crawled semester appears, by its NTU label) and a programme (all programmes, including those with no classes), search by course code, title or description, and open a course to see its details, all its indexes and a weekly timetable for the selected index.

It reads static JSON, so there is no backend. Export the newest data of every crawled semester first:

```bash
python -m ntu_courses export-web      # writes web/public/data/semesters.json and <key>.json
```

Then, with Node 20+ and pnpm:

```bash
cd web
pnpm install
pnpm dev            # development server with hot reload
pnpm run bundle     # single-file build: bundle.html (+ dist/artifact.html for claude.ai)
```

`bundle.html` contains the whole app but not the data. To host it, put it next to a `data/` folder holding the exported JSON and serve the folder with any static file server, e.g.:

```bash
mkdir -p site && cp web/bundle.html site/index.html && cp -r web/public/data site/
python -m http.server -d site 8000
```

After every crawl, run `export-web` again; a semester you crawled earlier stays in the dropdown.

### Deploy to GitHub Pages

```bash
scripts/deploy_pages.sh            # export data, build, commit to gh-pages and push
scripts/deploy_pages.sh --dry-run  # same, but only commit locally
```

The script runs `export-web` and the single-file build, then commits `index.html` and `data/` to the `gh-pages` branch in a temporary git worktree. The `main` branch and your working tree are not touched, and data still isn't committed to `main`. Each deploy is a normal commit, so earlier versions of the site stay in the branch history. Pages serves the branch at `https://<owner>.github.io/<repo>/` (enable it once under **Settings → Pages → Deploy from a branch → gh-pages / root**).

Typical update: `python -m ntu_courses crawl`, then `scripts/deploy_pages.sh`.

## Tests

```bash
pytest              # offline tests against saved pages in tests/fixtures
pytest -m live      # live tests against the real site
```

If the offline tests pass but the live tests fail, the site's page layout has probably changed. Replace the samples in `tests/fixtures` with fresh pages and update `ntu_courses/parsers.py`.

## Code layout

```
ntu_courses/
  models.py     data classes: semester, programme, course, index, class session
  parsers.py    HTML parsing (pure functions)
  client.py     HTTP (retries, rate limiting), programme mapping between the two sites, description fill-in by course code
  crawler.py    whole-semester crawl, de-duplication, conversion of older data formats
  snapshot.py   snapshot archive read/write
  export.py     static JSON export for the web UI
  __main__.py   command line
web/
  src/lib/data.ts        data loading, programme grouping, search, time helpers
  src/components/        programme picker, course list, course detail, weekly timetable
  scripts/bundle.sh      single-file build
```
