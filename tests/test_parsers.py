"""Offline parser tests against saved HTML snapshots (tests/fixtures, captured 2026-09-26)."""
from pathlib import Path

import pytest

from ntu_courses import merge_courses, parsers

FIX = Path(__file__).parent / "fixtures"


def load(name: str) -> str:
    return (FIX / name).read_text(encoding="cp1252")


@pytest.fixture(scope="module")
def schedule():
    return {c.code: c for c in parsers.parse_schedule(load("schedule_csc_y1_2026_1.html"))}


@pytest.fixture(scope="module")
def content():
    return {c.code: c for c in parsers.parse_content(load("content_csc_y1_2026_1.html"))}


def test_semesters_and_programmes():
    html = load("schedule_main.html")
    sems = parsers.parse_semesters(html)
    assert sems[0].schedule_key == "2026;1" and sems[0].content_key == "2026_1"
    assert {s.sem for s in sems} == {"1", "2", "S"}
    progs = {p.value: p for p in parsers.parse_programmes(html)}
    assert progs["CSC;;1;F"].label == "Computer Science Year 1"
    assert progs["MLOAD;AI;X;F"].category == "MLOAD"
    assert "" not in progs  # separators dropped


def test_schedule_course_header(schedule):
    assert len(schedule) == 34
    c = schedule["MH1812"]
    assert c.title == "DISCRETE MATHEMATICS"          # markers stripped
    assert c.au == 3.0 and c.is_ue and c.is_bde
    assert not schedule["SC1005"].is_ue and schedule["SC1005"].is_bde


def test_schedule_multiline_prerequisite(schedule):
    assert schedule["SC1008"].attributes["Prerequisite"] == "SC1003 OR SC1303 OR SC1001"
    assert schedule["SP0061"].attributes["Remark"] == "Only for Premier Scholars Programme students."


def test_schedule_indexes(schedule):
    cc1 = schedule["CC0001"]
    first = cc1.indexes[0]
    assert first.index == "82001"
    s = first.sessions[0]
    assert (s.type, s.group, s.day, s.time, s.venue, s.remark) == \
        ("TUT", "T001", "MON", "1030-1220", "LHN-TR+22", "Teaching Wk2-13")
    assert (s.start, s.end) == ("1030", "1220")
    # rows with a blank INDEX belong to the previous index
    last = schedule["SC2302"].indexes[-1]
    assert last.index == "10421" and [x.type for x in last.sessions] == ["LEC/STUDIO", "TUT", "LAB"]


def test_content(content):
    c = content["CC0001"]
    assert c.description.startswith("Researchers agree that writing is a tool for thinking")
    assert "\n" in c.description  # paragraphs kept
    assert c.attributes["Mutually exclusive with"].startswith("AB0601, HW0105")
    assert all(x.description for x in content.values())


def test_content_minor_layout():
    # Minor / GE pages use the search layout: column header row + many courses in one table
    courses = {c.code: c for c in parsers.parse_content(load("content_minor_ai_2026_1.html"))}
    assert len(courses) == 8 and all(c.description for c in courses.values())
    dm = courses["DM2012"]
    assert dm.au == 3.0 and dm.attributes["Department"] == "ADM"
    assert courses["BC3415"].attributes["Notes"] == "Not offered as Unrestricted Elective"


def test_content_search_layout():
    codes = [c.code for c in parsers.parse_content(load("content_search_sc100_2026_1.html"))]
    assert codes == ["SC1001", "SC1003", "SC1004", "SC1005", "SC1006", "SC1007", "SC1008"]


def test_merge(schedule, content):
    merged = {c.code: c for c in merge_courses(list(schedule.values()), list(content.values()))}
    assert set(merged) == set(schedule) | set(content)
    sc1005 = merged["SC1005"]
    assert sc1005.indexes and sc1005.description and sc1005.is_bde


@pytest.mark.parametrize("text", [
    "2026;1", "2026_1", "2026-1", "2026 1", "20261", " 2026 ; 1 ",
    "Acad Yr 2026 Semester 1", "acad yr 2026  semester 1",
])
def test_find_semester_accepts_key_or_label(text):
    from ntu_courses.models import find_semester
    sem = find_semester(text, parsers.parse_semesters(load("schedule_main.html")))
    assert (sem.year, sem.sem, sem.label) == (2026, "1", "Acad Yr 2026 Semester 1")


def test_find_semester_special_term_and_unknown():
    from ntu_courses.models import Semester, find_semester
    sems = parsers.parse_semesters(load("schedule_main.html"))
    assert find_semester("2025_s", sems).label == "Acad Yr 2025 Special Term"
    assert find_semester("Acad Yr 2025 Special Term", sems) == Semester(2025, "S")
    assert find_semester("2019_1", sems) is None
    assert find_semester("Semester 1", sems) is None
