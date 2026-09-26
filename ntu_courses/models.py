"""Data models for NTU course information."""
from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict


@dataclass(frozen=True)
class Semester:
    """An academic term, e.g. year=2026, sem='1' (sem may be '1', '2' or 'S')."""
    year: int
    sem: str
    label: str = field(default="", compare=False)  # display name, e.g. 'Acad Yr 2026 Semester 1'

    @property
    def schedule_key(self) -> str:   # format used by AUS_SCHEDULE
        return f"{self.year};{self.sem}"

    @property
    def content_key(self) -> str:    # format used by AUS_SUBJ_CONT
        return f"{self.year}_{self.sem}"

    def __str__(self) -> str:
        return self.schedule_key


def find_semester(value: str, semesters: list[Semester]) -> Semester | None:
    """Resolve user input to one of `semesters` (those offered by the site).

    Accepts the key in any common form ('2026;1', '2026_1', '2026-1', '2026 1', '2025;s')
    or the site's label, case-insensitive ('Acad Yr 2026 Semester 1').
    """
    text = " ".join(value.split()).lower()
    for s in semesters:
        if s.label and " ".join(s.label.split()).lower() == text:
            return s
    m = re.fullmatch(r"(\d{4})\s*[;_/ -]?\s*(\w)", text)
    if m:
        year, sem = int(m.group(1)), m.group(2).upper()
        for s in semesters:
            if (s.year, s.sem) == (year, sem):
                return s
    return None


@dataclass(frozen=True)
class Programme:
    """An entry in the 'r_course_yr' dropdown, e.g. 'CSC;;1;F' -> Computer Science Year 1."""
    value: str
    label: str

    @property
    def parts(self) -> list[str]:
        return self.value.split(";")

    @property
    def category(self) -> str:
        """Rough grouping: MLOAD=minor, GLOAD=BDE/UE, GERP=GE, else a degree programme code."""
        return self.parts[0]

    @property
    def year(self) -> str:
        return self.parts[2] if len(self.parts) > 2 else ""

    @property
    def mode(self) -> str:
        """'F' full time, 'P' part time."""
        return self.parts[3] if len(self.parts) > 3 else ""


@dataclass
class ClassSession:
    """One row in the schedule table (a single meeting pattern of an index)."""
    type: str      # LEC/STUDIO, TUT, LAB, SEM ...
    group: str
    day: str
    time: str      # e.g. '1030-1220'
    venue: str
    remark: str    # e.g. 'Teaching Wk2-13'

    @property
    def start(self) -> str:
        return self.time.split("-")[0] if "-" in self.time else ""

    @property
    def end(self) -> str:
        return self.time.split("-")[1] if "-" in self.time else ""


@dataclass
class ClassIndex:
    """A registrable index number and all its sessions."""
    index: str
    sessions: list[ClassSession] = field(default_factory=list)


@dataclass
class Course:
    code: str
    title: str
    au: float | None = None
    # Flags derived from the title suffix markers on the schedule page.
    is_ue: bool = False            # *  available as Unrestricted Elective
    is_bde: bool = False           # ~  available as Broadening and Deepening Elective
    is_self_paced: bool = False    # ^
    is_ge_pe: bool = False         # #  General Education Prescribed Elective
    # Labelled attributes (Prerequisite, Remark, Mutually exclusive with, Grade Type, ...).
    attributes: dict[str, str] = field(default_factory=dict)
    description: str = ""
    indexes: list[ClassIndex] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)
