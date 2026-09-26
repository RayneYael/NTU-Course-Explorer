"""Live smoke tests against the real NTU site. Run with: pytest -m live"""
import pytest

from ntu_courses import NTUClient

pytestmark = pytest.mark.live


@pytest.fixture(scope="module")
def client():
    return NTUClient(delay=0.5)


@pytest.fixture(scope="module")
def sem(client):
    return client.semesters()[0]


def test_programmes(client, sem):
    progs = {p.value for p in client.programmes(sem)}
    assert "CSC;;1;F" in progs and any(v.startswith("MLOAD;") for v in progs)


@pytest.mark.parametrize("programme", ["CSC;;1;F", "MLOAD;AI;X;F", "GERP;STS;X;F"])
def test_courses_complete(client, sem, programme):
    prog = next(p for p in client.programmes(sem) if p.value == programme)
    courses = client.courses(sem, prog)
    assert courses
    assert any(c.indexes for c in courses)
    assert all(c.description for c in courses), [c.code for c in courses if not c.description]
