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

`--sem` takes the form `2026;1`, `2025;2` or `2025;S` (Special Term). If omitted, the latest semester is used.

```bash
# Semesters offered on the site
python -m ntu_courses semesters

# Programme/year options for a semester; -f filters by keyword
python -m ntu_courses programmes --sem 2026;1 -f computer

# Live view of a programme/year; -c shows one course, --no-desc hides descriptions
python -m ntu_courses show -p 'CSC;;1;F' --sem 2026;1 -c SC1005

# Search the class schedule by course code or keyword
python -m ntu_courses search SC100 --sem 2026;1

# Crawl and archive (writes a new snapshot)
python -m ntu_courses crawl                           # latest semester
python -m ntu_courses crawl --sem 2025;2 --sem 2025;1 # specific semesters (repeatable)
python -m ntu_courses crawl --all                     # every semester in the dropdown
python -m ntu_courses crawl --limit 5 --data /tmp/t   # trial run: first 5 programmes, temp directory

# List saved snapshots (* marks LATEST)
python -m ntu_courses snapshots
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
  __main__.py   command line
```
