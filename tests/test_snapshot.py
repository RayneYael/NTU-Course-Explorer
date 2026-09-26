import os

import pytest

from ntu_courses import snapshot
from ntu_courses.snapshot import Archive


def sem_data(key="2026;1", title="DIGITAL LOGIC", errors=(), fetched="2026-09-26T00:00:00+00:00"):
    return {
        "format": 2, "semester": {"key": key}, "fetched_at": fetched,
        "programmes": [{"value": "CSC;;1;F", "courses": [{"code": "SC1005"}]}],
        "courses": {"SC1005": {"code": "SC1005", "title": title, "indexes": [{"index": "10081"}]}},
        "errors": list(errors),
    }


@pytest.fixture
def archive(tmp_path, monkeypatch):
    # give each write a distinct timestamp
    ticks = iter(range(10))

    class FakeDT(snapshot.datetime):
        @classmethod
        def now(cls, tz=None):
            return snapshot.datetime(2026, 9, 26, 0, 0, next(ticks), tzinfo=tz)

    monkeypatch.setattr(snapshot, "datetime", FakeDT)
    return Archive(tmp_path)


def test_write_and_load(archive):
    name = archive.write([sem_data()])
    assert archive.latest() == name
    assert archive.load_semester(name, "2026;1")["courses"]["SC1005"]["title"] == "DIGITAL LOGIC"


def test_unchanged_semester_is_not_stored_twice(archive):
    first = archive.write([sem_data()])
    second = archive.write([sem_data(fetched="2026-09-27T00:00:00+00:00")])  # only timestamp differs
    assert archive.manifest(second)["semesters"]["2026;1"]["stored_in"] == first
    assert not (archive.snapshots / second / "2026_1.json.gz").exists()
    assert archive.load_semester(second, "2026;1") == archive.load_semester(first, "2026;1")


def test_changed_semester_stored_and_old_kept(archive):
    first = archive.write([sem_data()])
    second = archive.write([sem_data(title="DIGITAL LOGIC II")])
    assert archive.manifest(second)["semesters"]["2026;1"]["previous"] == first
    assert archive.load_semester(first, "2026;1")["courses"]["SC1005"]["title"] == "DIGITAL LOGIC"
    assert archive.load_semester(second, "2026;1")["courses"]["SC1005"]["title"] == "DIGITAL LOGIC II"
    assert archive.list() == [first, second]


def test_incomplete_snapshot_does_not_move_latest(archive):
    first = archive.write([sem_data()])
    bad = archive.write([sem_data(title="X", errors=[{"programme": "CSC;;1;F", "error": "timeout"}])])
    assert archive.manifest(bad)["complete"] is False
    assert archive.latest() == first
    assert not any(n.endswith(".tmp") for n in os.listdir(archive.snapshots))
