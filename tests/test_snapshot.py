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


def labelled(key, label, **kw):
    d = sem_data(key=key, **kw)
    d["semester"]["label"] = label
    return d


def test_available_semesters_keeps_older_terms(archive):
    archive.write([labelled("2025;2", "Acad Yr 2025 Semester 2"), labelled("2025;S", "Acad Yr 2025 Special Term")])
    archive.write([labelled("2026;1", "Acad Yr 2026 Semester 1")])        # later crawl: latest term only
    archive.write([labelled("2026;1", "Acad Yr 2026 Semester 1", title="NEW",
                            errors=[{"programme": "X", "error": "timeout"}])])  # failed crawl ignored
    sems = archive.available_semesters()
    assert [s["label"] for s in sems] == \
        ["Acad Yr 2026 Semester 1", "Acad Yr 2025 Special Term", "Acad Yr 2025 Semester 2"]
    assert archive.load_current("2026;1")["courses"]["SC1005"]["title"] == "DIGITAL LOGIC"
    with pytest.raises(KeyError):
        archive.load_current("2024;1")


def test_export_web(archive, tmp_path):
    import json
    from ntu_courses.export import export_web
    archive.write([labelled("2026;1", "Acad Yr 2026 Semester 1")])
    out = tmp_path / "web"
    (out).mkdir()
    (out / "2019_1.json").write_text("{}")                                  # stale file is removed
    index = export_web(archive, out)
    assert [s["file"] for s in index] == ["2026_1.json"]
    assert sorted(p.name for p in out.iterdir()) == ["2026_1.json", "semesters.json"]
    data = json.loads((out / "2026_1.json").read_text())
    assert data["semester"]["key"] == "2026_1" and "SC1005" in data["courses"]
