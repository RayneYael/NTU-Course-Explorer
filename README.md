# NTU Course Explorer

English | [中文](README_zh.md)

Browse NTU undergraduate courses by semester and programme: class schedules, course descriptions and a weekly timetable for every index.

**Live site: https://rayneyael.github.io/NTU-Course-Explorer/**

## Features

- Every programme, year, minor and elective group, for every available semester
- Search by course code, title or description
- Course details: AU, prerequisites, restrictions and description
- All class indexes, with a weekly timetable
- BDE / UE / GE tags for the selected programme

Data comes from NTU's public [Class Schedule](https://wish.wis.ntu.edu.sg/webexe/owa/AUS_SCHEDULE.main) and [Content of Courses](https://wish.wis.ntu.edu.sg/webexe/owa/aus_subj_cont.main) pages.

## Quick start

Requires Python 3.10+, Node 20+ and pnpm.

```bash
pip install -r requirements.txt
python -m ntu_courses crawl          # scrape the latest semester (about 15 min)
python -m ntu_courses export-web     # prepare the data for the web app

cd web && pnpm install && pnpm dev   # open the local URL it prints
```

## Scraper commands

| Command | What it does |
|---|---|
| `python -m ntu_courses crawl` | Scrape the latest semester |
| `python -m ntu_courses crawl --sem 2025_2` | Scrape a specific semester |
| `python -m ntu_courses crawl --all` | Scrape every semester |
| `python -m ntu_courses export-web` | Export data for the web app |

`--sem` takes a key such as `2026_1` or the site's name, e.g. `"Acad Yr 2026 Semester 1"`.

## Project structure

```
ntu_courses/   Python scraper and CLI
web/           React web app
scripts/       maintenance scripts
```
