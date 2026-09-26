"""HTML parsers for the NTU WISH pages. Pure functions: HTML string in, models out."""
from __future__ import annotations

import re

from bs4 import BeautifulSoup, Tag

from .models import ClassIndex, ClassSession, Course, Programme, Semester

_TITLE_MARKERS = "*~^#"


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


def _text(node: Tag | None) -> str:
    if node is None:
        return ""
    return node.get_text(" ", strip=True).replace("\xa0", " ").strip()


# --------------------------------------------------------------------------- forms

def parse_semesters(html: str) -> list[Semester]:
    """Semester options from either the schedule ('2026;1') or content ('2026_1') main page."""
    sel = _soup(html).find("select", attrs={"name": "acadsem"})
    out = []
    for opt in sel.find_all("option") if sel else []:
        m = re.fullmatch(r"(\d{4})[;_](\w)", opt.get("value", "").strip())
        if m:
            out.append(Semester(int(m.group(1)), m.group(2), _text(opt)))
    return out


def parse_selected_semester(html: str) -> Semester | None:
    soup = _soup(html)
    hidden = soup.find("input", attrs={"type": "hidden", "name": "acadsem"})
    val = hidden.get("value", "") if hidden else ""
    m = re.fullmatch(r"(\d{4})[;_](\w)", val.strip())
    return Semester(int(m.group(1)), m.group(2)) if m else None


def parse_programmes(html: str) -> list[Programme]:
    sel = _soup(html).find("select", attrs={"name": "r_course_yr"})
    out = []
    for opt in sel.find_all("option") if sel else []:
        val = opt.get("value", "").strip()
        if val:  # skip separators / headers such as '---Double Degree---'
            out.append(Programme(val, _text(opt)))
    return out


# --------------------------------------------------------------------------- course header

def _split_title(raw: str) -> tuple[str, set[str]]:
    markers = set()
    while raw and raw[-1] in _TITLE_MARKERS:
        markers.add(raw[-1])
        raw = raw[:-1]
    return raw.strip(), markers


_CODE_RE = re.compile(r"[A-Z0-9]{2,}\d{2,}[A-Z0-9]*")
_BLUE = re.compile(r"#0000FF", re.I)


def _course_from_code_row(tds: list[Tag]) -> Course | None:
    """A code row looks like: CODE | TITLE[markers] | '3.0 AU' [| DEPT (search page only)]."""
    if len(tds) < 2 or not tds[0].find("font", color=_BLUE):
        return None
    code = _text(tds[0])
    if not _CODE_RE.fullmatch(code):
        return None
    title, markers = _split_title(_text(tds[1]))
    au = None
    if len(tds) > 2:
        m = re.search(r"\d+(?:\.\d+)?", _text(tds[2]))
        au = float(m.group()) if m else None
    course = Course(
        code=code, title=title, au=au,
        is_ue="*" in markers, is_bde="~" in markers,
        is_self_paced="^" in markers, is_ge_pe="#" in markers,
    )
    if len(tds) > 3 and _text(tds[3]):
        course.attributes["Department"] = _text(tds[3])
    return course


def _parse_header_rows(table: Tag) -> list[Course]:
    """Parse the non-bordered table(s) holding course code / title / AU and the rows below it.

    Handles all three layouts:
      - schedule page: one course per table, labelled rows (Prerequisite, Remark ...)
      - content page:  same, plus a long description row (single td, colspan=3)
      - content search: a column header row, then possibly several courses in one table
    Labels spanning several rows (e.g. 'Prerequisite: A OR' / ' B') are joined.
    """
    courses: list[Course] = []
    attrs: dict[str, list[str]] = {}
    last_label = None

    def flush():
        if courses:
            for k, v in attrs.items():
                if v:
                    courses[-1].attributes[k] = " ".join(v)

    for tr in table.find_all("tr"):
        tds = tr.find_all("td")
        if not tds:
            continue
        course = _course_from_code_row(tds)
        if course:
            flush()
            courses.append(course)
            attrs, last_label = {}, None
            continue
        if not courses:
            continue  # column header row on the search page
        if len(tds) == 1:
            td = tds[0]
            if not _text(td):
                continue               # '&nbsp;' spacer between courses
            if td.find("b") is None:  # description row
                desc = td.get_text("\n").replace("\xa0", " ")
                courses[-1].description = "\n".join(l.strip() for l in desc.splitlines() if l.strip())
            else:                      # stand-alone note e.g. 'Not offered as Unrestricted Elective'
                attrs.setdefault("Notes", []).append(_text(td))
            continue
        label = _text(tds[0]).rstrip(":").strip()
        value = _text(tds[1])
        if label:
            last_label = label
            attrs.setdefault(label, [])
        if value and last_label:
            attrs[last_label].append(value)
    flush()
    return courses


# --------------------------------------------------------------------------- schedule page

def parse_page_title(html: str) -> str:
    """E.g. 'Class Schedule 2026 Semester 1 Computer Science Year 1'."""
    font = _soup(html).find("font", color=re.compile("black", re.I))
    return re.sub(r"\s+", " ", _text(font)) if font else ""


def _parse_schedule_table(table: Tag) -> list[ClassIndex]:
    indexes: list[ClassIndex] = []
    for tr in table.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 7:
            continue  # header row uses <th>
        idx, typ, grp, day, time, venue, remark = (_text(td) for td in tds[:7])
        session = ClassSession(typ, grp, day, time, venue, remark)
        if idx or not indexes:  # a blank index continues the previous one
            indexes.append(ClassIndex(idx))
        indexes[-1].sessions.append(session)
    return indexes


def _is_schedule_table(table: Tag) -> bool:
    return table.has_attr("border") and any(_text(th) == "INDEX" for th in table.find_all("th"))


def parse_schedule(html: str) -> list[Course]:
    """Parse an AUS_SCHEDULE.main_display1 result page into courses with class indexes."""
    courses: list[Course] = []
    for table in _soup(html).find_all("table"):
        if _is_schedule_table(table):
            if courses and not courses[-1].indexes:
                courses[-1].indexes = _parse_schedule_table(table)
            continue
        courses.extend(_parse_header_rows(table))
    return courses


# --------------------------------------------------------------------------- content page

def parse_content(html: str) -> list[Course]:
    """Parse an AUS_SUBJ_CONT.main_display1 result page (descriptions, prereqs, etc.)."""
    courses = []
    for table in _soup(html).find_all("table"):
        courses.extend(_parse_header_rows(table))
    return courses
