import json
from pathlib import Path

from job_watch.companies import hudson_river_trading as hrt
from job_watch.config import LocationFilter

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "hrt_jobs.json").read_text())


class _FakeResponse:
    def __init__(self, payload, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code
        self.text = json.dumps(payload)

    def json(self):
        return self._payload


def test_fetch_roles_parses_cards(monkeypatch):
    def fake_post(url, data, headers, timeout):
        return _FakeResponse(FIXTURE)

    monkeypatch.setattr(hrt.requests, "post", fake_post)

    roles = hrt.fetch_roles([])

    assert len(roles) == 2
    assert roles[0].title == "HPC Network Engineer"
    assert roles[0].division == "Systems and Networking, Experienced"
    assert roles[0].location == "New York, Singapore"
    assert roles[0].id == "397389"

    # title's HTML entity is unescaped
    assert roles[1].title == "Algorithm Developer (Quant Research & Trading) – 2027 Grads"
    assert roles[1].division == "Strategy Development, New Grad"
    assert roles[1].location == "London"


def test_fetch_roles_filters_by_country(monkeypatch):
    def fake_post(url, data, headers, timeout):
        return _FakeResponse(FIXTURE)

    monkeypatch.setattr(hrt.requests, "post", fake_post)

    uk_only = hrt.fetch_roles([LocationFilter(country="United Kingdom")])

    assert [r.title for r in uk_only] == ["Algorithm Developer (Quant Research & Trading) – 2027 Grads"]


def test_fetch_roles_filters_by_city_matches_any_of_multiple_offices(monkeypatch):
    def fake_post(url, data, headers, timeout):
        return _FakeResponse(FIXTURE)

    monkeypatch.setattr(hrt.requests, "post", fake_post)

    singapore_only = hrt.fetch_roles([LocationFilter(country="Singapore", city="Singapore")])

    assert [r.title for r in singapore_only] == ["HPC Network Engineer"]


def test_fetch_roles_raises_on_non_200(monkeypatch):
    def fake_post(url, data, headers, timeout):
        return _FakeResponse([], status_code=500)

    monkeypatch.setattr(hrt.requests, "post", fake_post)

    try:
        hrt.fetch_roles([])
        assert False, "expected FetchError"
    except hrt.FetchError:
        pass
