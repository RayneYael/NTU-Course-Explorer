"""Command line entry: python -m ntu_courses <command> ...

  semesters                              list available terms (key and label)
  programmes [--sem 2026_1] [-f text]    list programme/year options for a term
  show -p 'CSC;;1;F' [--sem 2026_1] [-c SC1005] [--no-desc]
                                         print courses of a programme (schedule + content)
  search KEYWORD [--sem 2026_1]          search schedule by course code / keyword
  crawl [--sem 2026_1 ...] [--all]       crawl whole semester(s) into a new snapshot (default: latest)
  snapshots                              list saved snapshots
  export-web [--out web/public/data]     write the newest data of every crawled semester for the web UI

--sem accepts a key (2026_1, 2026;1, 2025_S) or the site's label ("Acad Yr 2026 Semester 1").
"""
from __future__ import annotations

import argparse
import logging
import sys
import textwrap

from . import parsers
from .client import NTUClient
from .crawler import crawl_semester
from .export import export_web
from .snapshot import Archive
from .models import Course, Semester, find_semester


def _sem(client: NTUClient, value: str | None) -> Semester:
    sems = client.semesters()
    if not value:
        return sems[0]
    sem = find_semester(value, sems)
    if sem is None:
        offered = "\n".join(f"  {s.content_key:8} {s.label}" for s in sems)
        sys.exit(f"unknown semester {value!r}. Use a key or a label, e.g. 2026_1 or "
                 f"'Acad Yr 2026 Semester 1'. Offered:\n{offered}")
    return sem


def _print_course(c: Course, desc: bool) -> None:
    flags = "".join(f for f, on in (("UE ", c.is_ue), ("BDE ", c.is_bde),
                                    ("SelfPaced ", c.is_self_paced), ("GE-PE ", c.is_ge_pe)) if on)
    print(f"\n{c.code}  {c.title}  [{c.au} AU]  {flags.strip()}")
    for k, v in c.attributes.items():
        print(f"  {k}: {v}")
    if desc and c.description:
        print(textwrap.indent(textwrap.fill(c.description, 100), "  | "))
    for idx in c.indexes:
        for i, s in enumerate(idx.sessions):
            print(f"  {idx.index if i == 0 else '':>6}  {s.type:<11}{s.group:<8}{s.day:<4} {s.time:<10}{s.venue:<16}{s.remark}")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="ntu_courses", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--delay", type=float, default=0.5, help="seconds between requests")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("semesters")
    p = sub.add_parser("programmes")
    p.add_argument("--sem")
    p.add_argument("-f", "--filter", default="")
    p = sub.add_parser("show")
    p.add_argument("--sem")
    p.add_argument("-p", "--programme", required=True, help="dropdown value, e.g. 'CSC;;1;F'")
    p.add_argument("-c", "--code", help="only show this course")
    p.add_argument("--no-desc", action="store_true")
    p = sub.add_parser("search")
    p.add_argument("keyword")
    p.add_argument("--sem")

    p = sub.add_parser("crawl")
    p.add_argument("--sem", action="append", help="repeatable; default = latest semester")
    p.add_argument("--all", action="store_true", help="every semester in the dropdown")
    p.add_argument("--limit", type=int, help="only the first N programmes (for testing)")
    p.add_argument("--data", default="data")
    p = sub.add_parser("snapshots")
    p.add_argument("--data", default="data")
    p = sub.add_parser("export-web")
    p.add_argument("--data", default="data")
    p.add_argument("--out", default="web/public/data")

    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
    if args.cmd == "export-web":  # offline: reads the archive only
        index = export_web(Archive(args.data), args.out)
        if not index:
            sys.exit(f"no successfully crawled semesters in {args.data}/; run `crawl` first")
        for s in index:
            print(f"{args.out}/{s['file']}  {s['label']}  ({s['programmes']} programmes, "
                  f"{s['courses']} courses, fetched {s['fetched_at']})")
        return
    client = NTUClient(delay=args.delay)

    if args.cmd == "semesters":
        for s in client.semesters():
            print(f"{s.content_key:8} {s.label}")
    elif args.cmd == "programmes":
        sem = _sem(client, args.sem)
        for p in client.programmes(sem):
            if args.filter.lower() in (p.value + " " + p.label).lower():
                print(f"{p.value:18} {p.label}")
    elif args.cmd == "show":
        sem = _sem(client, args.sem)
        progs = {p.value: p for p in client.programmes(sem)}
        if args.programme not in progs:
            sys.exit(f"unknown programme {args.programme!r} for {sem}; see `programmes --sem {sem}`")
        courses = client.courses(sem, progs[args.programme])
        if args.code:
            courses = [c for c in courses if c.code == args.code.upper()]
        print(f"{sem.label}  {progs[args.programme].label}: {len(courses)} courses")
        for c in courses:
            _print_course(c, not args.no_desc)
    elif args.cmd == "search":
        sem = _sem(client, args.sem)
        for c in parsers.parse_schedule(client.search_schedule_html(sem, args.keyword)):
            _print_course(c, False)
    elif args.cmd == "crawl":
        sems = client.semesters() if args.all else [_sem(client, v) for v in (args.sem or [None])]
        results = [crawl_semester(client, sem, limit=args.limit) for sem in sems]
        archive = Archive(args.data)
        name = archive.write(results)
        m = archive.manifest(name)
        print(f"snapshot {name} ({'complete' if m['complete'] else 'INCOMPLETE, LATEST not moved'})")
        for key, e in m["semesters"].items():
            note = f"unchanged, stored in {e['stored_in']}" if "stored_in" in e else e["file"]
            print(f"  {e.get('label') or key}: {e['programmes']} programmes, {e['courses']} courses, "
                  f"{e['indexes']} indexes, {len(e['errors'])} errors  [{note}]")
    elif args.cmd == "snapshots":
        archive = Archive(args.data)
        latest = archive.latest()
        for name in archive.list():
            m = archive.manifest(name)
            sems = ", ".join(f"{e.get('label') or k}{' (unchanged)' if 'stored_in' in e else ''}"
                             for k, e in m["semesters"].items())
            print(f"{'*' if name == latest else ' '} {name}  complete={m['complete']}  {sems}")


if __name__ == "__main__":
    main()
