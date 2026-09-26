"""HTTP client for the NTU WISH class schedule / course content pages."""
from __future__ import annotations

import logging
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from . import parsers
from .models import Course, Programme, Semester

log = logging.getLogger(__name__)

BASE_URL = "https://wish.wis.ntu.edu.sg/webexe/owa/"
_PLACEHOLDER = "Enter Keywords or Course Code"
_ENCODING = "cp1252"  # server declares Windows-1252


class NTUClient:
    """Thin wrapper around the two WISH endpoints.

    - AUS_SCHEDULE : class schedule (index, type, group, day, time, venue, remark)
    - AUS_SUBJ_CONT: course content (description, prerequisites, exclusions, grade type)

    Both expose the same "programme / year" dropdown, but it changes per semester, so
    always call `programmes(sem)` rather than reusing an older list.
    """

    def __init__(self, delay: float = 0.5, timeout: float = 60, retries: int = 3):
        self.delay = delay
        self.timeout = timeout
        self._last = 0.0
        self._content_progs: dict[Semester, list[Programme]] = {}
        self._content_cache: dict[Semester, dict[str, Course]] = {}
        self._searched: set[tuple[Semester, str]] = set()
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "Mozilla/5.0 (ntu-course-scraper)"
        retry = Retry(total=retries, backoff_factor=1.5, status_forcelist=(429, 500, 502, 503, 504),
                      allowed_methods=frozenset({"GET", "POST"}))
        self.session.mount("https://", HTTPAdapter(max_retries=retry))

    # ------------------------------------------------------------------ low level
    def _request(self, method: str, path: str, data: dict | None = None) -> str:
        wait = self.delay - (time.monotonic() - self._last)
        if wait > 0:
            time.sleep(wait)
        try:
            resp = self.session.request(method, BASE_URL + path, data=data, timeout=self.timeout)
        finally:
            self._last = time.monotonic()
        resp.raise_for_status()
        return resp.content.decode(_ENCODING, errors="replace")

    # ------------------------------------------------------------------ schedule
    def schedule_main(self, sem: Semester | None = None) -> str:
        """Main schedule form. Without `sem` the server returns its default (latest) term."""
        if sem is None:
            return self._request("GET", "AUS_SCHEDULE.main")
        return self._request("POST", "AUS_SCHEDULE.main_display", {
            "acadsem": sem.schedule_key, "r_course_yr": "", "r_subj_code": _PLACEHOLDER,
            "r_search_type": "F", "boption": "x", "staff_access": "false",
        })

    def semesters(self) -> list[Semester]:
        return parsers.parse_semesters(self.schedule_main())

    def programmes(self, sem: Semester) -> list[Programme]:
        return parsers.parse_programmes(self.schedule_main(sem))

    def schedule_html(self, sem: Semester, programme: str) -> str:
        return self._request("POST", "AUS_SCHEDULE.main_display1", {
            "acadsem": sem.schedule_key, "r_course_yr": programme, "r_subj_code": _PLACEHOLDER,
            "r_search_type": "F", "boption": "CLoad", "staff_access": "false",
        })

    def search_schedule_html(self, sem: Semester, keyword: str) -> str:
        """Search the schedule by course code or keyword (same as the 'Search' button)."""
        return self._request("POST", "AUS_SCHEDULE.main_display1", {
            "acadsem": sem.schedule_key, "r_course_yr": "", "r_subj_code": keyword,
            "r_search_type": "F", "boption": "Search", "staff_access": "false",
        })

    def schedule(self, sem: Semester, programme: str) -> list[Course]:
        return parsers.parse_schedule(self.schedule_html(sem, programme))

    # ------------------------------------------------------------------ content
    def content_main(self, sem: Semester) -> str:
        return self._request("POST", "AUS_SUBJ_CONT.main_display", {
            "acadsem": sem.content_key, "acad": str(sem.year), "semester": sem.sem,
            "r_course_yr": "", "r_subj_code": "", "boption": "",
        })

    def content_programmes(self, sem: Semester) -> list[Programme]:
        """The content page's own dropdown; values differ from the schedule page's
        (e.g. minors are 'MLOAD;AI;' there vs 'MLOAD;AI;X;F' here), labels mostly match."""
        if sem not in self._content_progs:
            self._content_progs[sem] = parsers.parse_programmes(self.content_main(sem))
        return self._content_progs[sem]

    def content_programme_for(self, sem: Semester, programme: Programme | str) -> str | None:
        """Find the content-page dropdown value equivalent to a schedule-page programme."""
        value = programme.value if isinstance(programme, Programme) else programme
        label = programme.label if isinstance(programme, Programme) else None
        progs = self.content_programmes(sem)
        by_value = {p.value: p for p in progs}
        if value in by_value:
            return value
        if label:
            for p in progs:
                if p.label == label:
                    return p.value
        # 'MLOAD;AI;X;F' -> 'MLOAD;AI;' / 'CNY;CNY;X'
        parts = value.split(";")
        for cand in (";".join(parts[:3]), ";".join(parts[:2]) + ";"):
            if cand in by_value:
                return cand
        return None

    def content_html(self, sem: Semester, programme: str) -> str:
        return self._request("POST", "AUS_SUBJ_CONT.main_display1", {
            "acadsem": sem.content_key, "acad": str(sem.year), "semester": sem.sem,
            "r_course_yr": programme, "r_subj_code": _PLACEHOLDER, "boption": "CLoad",
        })

    def search_content_html(self, sem: Semester, keyword: str) -> str:
        return self._request("POST", "AUS_SUBJ_CONT.main_display1", {
            "acadsem": sem.content_key, "acad": str(sem.year), "semester": sem.sem,
            "r_course_yr": "", "r_subj_code": keyword, "boption": "Search",
        })

    def content(self, sem: Semester, programme: str) -> list[Course]:
        courses = parsers.parse_content(self.content_html(sem, programme))
        self._remember(sem, courses)
        return courses

    def search_content(self, sem: Semester, keyword: str) -> list[Course]:
        courses = parsers.parse_content(self.search_content_html(sem, keyword))
        self._remember(sem, courses)
        return courses

    def content_for_code(self, sem: Semester, code: str) -> Course | None:
        """Content of a single course, cached per semester."""
        cache = self._content_cache.setdefault(sem, {})
        key = (sem, code)
        if key not in self._searched and not (cache.get(code) and cache[code].description):
            self._searched.add(key)  # don't retry misses
            self.search_content(sem, code)
        return cache.get(code)

    def _remember(self, sem: Semester, courses: list[Course]) -> None:
        cache = self._content_cache.setdefault(sem, {})
        for c in courses:
            old = cache.get(c.code)
            if old is None or c.description or not old.description:
                cache[c.code] = c

    # ------------------------------------------------------------------ combined
    def courses(self, sem: Semester, programme: Programme | str, fill_missing: bool = True) -> list[Course]:
        """Schedule + content for one programme/year, merged by course code.

        Content comes from the equivalent content-page programme; any scheduled course
        still without a description is looked up individually when `fill_missing`.
        """
        value = programme.value if isinstance(programme, Programme) else programme
        schedule = self.schedule(sem, value)
        content_prog = self.content_programme_for(sem, programme)
        content = self.content(sem, content_prog) if content_prog else []
        merged = merge_courses(schedule, content)
        if fill_missing:
            for c in merged:
                if not c.description:
                    extra = self.content_for_code(sem, c.code)
                    if extra:
                        merge_courses([c], [extra])
        return merged


def merge_courses(schedule: list[Course], content: list[Course]) -> list[Course]:
    """Merge schedule-page and content-page courses by code.

    The schedule page supplies class indexes and the elective markers; the content page
    supplies the description and fuller attribute set. Courses present on only one page
    are kept as-is.
    """
    merged: dict[str, Course] = {c.code: c for c in schedule}
    for c in content:
        base = merged.get(c.code)
        if base is None:
            merged[c.code] = c
            continue
        base.description = c.description or base.description
        base.attributes = {**base.attributes, **c.attributes}
        if base.au is None:
            base.au = c.au
    return sorted(merged.values(), key=lambda c: c.code)
