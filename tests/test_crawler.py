from ntu_courses.crawler import build_semester


def course(code, indexes, bde=False, remark=None, dept=None, desc="d"):
    attrs = {}
    if remark:
        attrs["Remark"] = remark
    if dept:
        attrs["Department"] = dept
    return {"code": code, "title": "T", "au": 3.0, "description": desc, "attributes": attrs,
            "is_ue": False, "is_bde": bde, "is_self_paced": False, "is_ge_pe": False,
            "indexes": [{"index": i, "sessions": [{"day": "MON"}]} for i in indexes]}


def page(value, *courses):
    return {"programme": {"value": value, "label": value}, "content_value": value, "courses": list(courses)}


def test_build_semester_folds_programme_views():
    data = build_semester({"key": "2026;1"}, "t", [
        page("A", course("CC0001", ["2", "1"], remark="only A")),
        page("B", course("CC0001", ["3"], bde=True, dept="NTC")),
        page("C", course("CC0001", ["1", "2", "3"])),
    ], [])
    c = data["courses"]["CC0001"]
    assert [i["index"] for i in c["indexes"]] == ["1", "2", "3"]      # union, sorted
    assert c["attributes"] == {"Department": "NTC"}                  # Remark is per programme
    a, b, cc = (p["courses"][0] for p in data["programmes"])
    assert a["indexes"] == ["2", "1"] and a["remark"] == "only A" and not a["is_bde"]
    assert b["indexes"] == ["3"] and b["is_bde"] and "remark" not in b
    assert "indexes" not in cc                                       # sees all indexes


def test_empty_programme_kept():
    data = build_semester({"key": "2026;1"}, "t", [page("A", course("X1001", ["1"])), page("EMPTY")], [])
    assert [(p["value"], p["status"], p["courses"]) for p in data["programmes"]][1] == ("EMPTY", "empty", [])
    assert data["programmes"][0]["status"] == "ok"


def test_failed_programme_still_listed():
    from ntu_courses.crawler import crawl_semester
    from ntu_courses.models import Course, Programme, Semester

    class FakeClient:
        def programmes(self, sem):
            return [Programme("OK;;1;F", "Ok Year 1"), Programme("BAD;;1;F", "Bad Year 1"),
                    Programme("NONE;;1;F", "None Year 1")]

        def courses(self, sem, p):
            if p.value == "BAD;;1;F":
                raise TimeoutError("boom")
            return [Course("OK1001", "T")] if p.value == "OK;;1;F" else []

        def content_programme_for(self, sem, p):
            return p.value

    data = crawl_semester(FakeClient(), Semester(2026, "1"))
    assert [(p["value"], p["status"]) for p in data["programmes"]] == \
        [("OK;;1;F", "ok"), ("BAD;;1;F", "error"), ("NONE;;1;F", "empty")]
    assert data["errors"][0]["programme"] == "BAD;;1;F"


def test_normalize_adds_status_to_old_data():
    from ntu_courses.crawler import normalize
    data = build_semester({"key": "k"}, "t", [page("A", course("X1001", ["1"])), page("B")], [])
    for p in data["programmes"]:
        del p["status"]
    assert [p["status"] for p in normalize(data)["programmes"]] == ["ok", "empty"]
