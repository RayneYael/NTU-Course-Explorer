"""Crawl every programme of a semester into one de-duplicated, JSON-ready structure.

Semester data layout (format 2):
{
  "semester": {...}, "fetched_at": "...", "errors": [...],
  "courses": {code: {code, title, au, description, attributes, indexes: [union over all pages]}},
  "programmes": [{value, label, content_value,
                  status,                         # "ok" | "empty" (site lists no courses) | "error" (fetch failed)
                  courses: [{code, is_ue, is_bde, is_self_paced, is_ge_pe,
                             remark?,            # programme-specific 'Remark' from schedule page
                             indexes?}]}]        # index numbers shown to this programme; absent = all
}

Every programme in the site's dropdown is always listed, even when empty or failed, so
the programme list can be shown in full; such entries simply have "courses": [].

Why: the same course is shown on many programme pages. What varies per page is only
(a) the elective flags (UE/BDE/GE depend on the viewer's programme), (b) a schedule
'Remark', and (c) which indexes are listed. Session data of an index never differs.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

from .client import NTUClient
from .models import Programme, Semester

log = logging.getLogger(__name__)

FLAGS = ("is_ue", "is_bde", "is_self_paced", "is_ge_pe")
PER_PROGRAMME_ATTRS = ("Remark",)


def crawl_semester(client: NTUClient, sem: Semester, limit: int | None = None,
                   retry_failed: bool = True) -> dict:
    started = datetime.now(timezone.utc)
    programmes = client.programmes(sem)
    if limit:
        programmes = programmes[:limit]
    log.info("%s: %d programmes", sem, len(programmes))

    pages: dict[str, dict] = {}  # programme value -> {"programme", "content_value", "courses": [dict]}
    failed: list[Programme] = []

    def run(p: Programme) -> None:
        got = client.courses(sem, p)
        pages[p.value] = {"programme": p, "content_value": client.content_programme_for(sem, p),
                          "courses": [c.to_dict() for c in got]}

    t0 = time.monotonic()
    for i, p in enumerate(programmes, 1):
        try:
            run(p)
        except Exception as e:  # keep going; retried below
            log.warning("  FAIL %s: %r", p.value, e)
            failed.append(p)
        if i % 20 == 0 or i == len(programmes):
            codes = {c["code"] for pg in pages.values() for c in pg["courses"]}
            log.info("  %d/%d programmes, %d unique courses, %.0fs", i, len(programmes),
                     len(codes), time.monotonic() - t0)

    errors = []
    for p in failed:
        try:
            if not retry_failed:
                raise RuntimeError("failed")
            run(p)
        except Exception as e:
            errors.append({"programme": p.value, "error": repr(e)})
            pages[p.value] = {"programme": p, "content_value": None, "courses": [], "error": True}

    ordered = [pages[p.value] for p in programmes]
    return build_semester(
        {"key": sem.schedule_key, "year": sem.year, "sem": sem.sem, "label": sem.label},
        started.isoformat(timespec="seconds"), ordered, errors)


def build_semester(semester: dict, fetched_at: str, pages: list[dict], errors: list) -> dict:
    """Fold per-programme course lists into canonical courses + per-programme views.

    `pages` items: {"programme": Programme | {"value","label"}, "content_value", "courses": [course dict],
                    "error"?: bool}
    """
    courses: dict[str, dict] = {}
    index_order: dict[str, dict[str, dict]] = {}  # code -> index no -> index dict (first seen)

    for page in pages:
        for c in page["courses"]:
            base = courses.get(c["code"])
            if base is None:
                base = courses[c["code"]] = {
                    "code": c["code"], "title": c["title"], "au": c["au"],
                    "description": c["description"], "attributes": {},
                }
            base["description"] = base["description"] or c["description"]
            if base["au"] is None:
                base["au"] = c["au"]
            for k, v in c["attributes"].items():
                if k not in PER_PROGRAMME_ATTRS:
                    base["attributes"].setdefault(k, v)
            seen = index_order.setdefault(c["code"], {})
            for idx in c["indexes"]:
                seen.setdefault(idx["index"], idx)

    for code, base in courses.items():
        base["indexes"] = sorted(index_order[code].values(), key=lambda i: i["index"])

    programmes = []
    for page in pages:
        p = page["programme"]
        value, label = (p.value, p.label) if isinstance(p, Programme) else (p["value"], p["label"])
        entries = []
        for c in page["courses"]:
            e = {"code": c["code"], **{f: c[f] for f in FLAGS}}
            for k in PER_PROGRAMME_ATTRS:
                if k in c["attributes"]:
                    e[k.lower()] = c["attributes"][k]
            shown = [i["index"] for i in c["indexes"]]
            if len(shown) != len(courses[c["code"]]["indexes"]):
                e["indexes"] = shown
            entries.append(e)
        status = "error" if page.get("error") else ("ok" if entries else "empty")
        programmes.append({"value": value, "label": label, "content_value": page["content_value"],
                           "status": status, "courses": entries})

    return {
        "format": 2,
        "semester": semester,
        "fetched_at": fetched_at,
        "programmes": programmes,
        "courses": dict(sorted(courses.items())),
        "errors": errors,
    }


def normalize(data: dict) -> dict:
    """Bring semester data from any older snapshot up to the current layout (on load)."""
    data = upgrade_v1(data)
    failed = {e["programme"] for e in data["errors"]}
    for p in data["programmes"]:
        if "status" not in p:
            p["status"] = "error" if p["value"] in failed else ("ok" if p["courses"] else "empty")
    return data


def upgrade_v1(data: dict) -> dict:
    """Convert a format-1 semester (canonical course + full-copy course_overrides) to format 2."""
    if data.get("format") == 2:
        return data
    pages = [{"programme": {"value": p["value"], "label": p["label"]},
              "content_value": p["content_value"],
              "courses": [p["course_overrides"].get(c, data["courses"][c]) for c in p["courses"]]}
             for p in data["programmes"]]
    return build_semester(data["semester"], data["fetched_at"], pages, data["errors"])
