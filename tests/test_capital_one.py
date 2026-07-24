import json
from pathlib import Path

from job_watch.companies import capital_one
from job_watch.config import LocationFilter

FIXTURES = Path(__file__).parent / "fixtures"
LOCATIONS_PLANO = json.loads((FIXTURES / "capital_one_locations_plano.json").read_text())
PAGE1 = json.loads((FIXTURES / "capital_one_results_page1.json").read_text())
PAGE1_OF2 = json.loads((FIXTURES / "capital_one_results_page1_of2.json").read_text())
PAGE2_OF2 = json.loads((FIXTURES / "capital_one_results_page2_of2.json").read_text())


class _FakeResponse:
    def __init__(self, payload, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code
        self.text = json.dumps(payload) if not isinstance(payload, str) else payload

    def json(self):
        return self._payload


def test_fetch_roles_geocodes_and_parses_results(monkeypatch):
    calls = {"locations": [], "results": []}

    def fake_get(url, params, headers, timeout):
        if url == capital_one._LOCATIONS_URL:
            calls["locations"].append(params)
            return _FakeResponse(LOCATIONS_PLANO)
        calls["results"].append(params)
        return _FakeResponse(PAGE1)

    monkeypatch.setattr(capital_one.requests, "get", fake_get)

    roles = capital_one.fetch_roles([LocationFilter(country="United States", state="TX", city="Plano")])

    assert calls["locations"][0]["term"] == "Plano, TX"
    assert calls["results"][0]["Latitude"] == 33.01984
    assert calls["results"][0]["LocationPath"] == "6252001-4736286-4682500-4719457"

    assert len(roles) == 2
    # &amp; is unescaped
    assert roles[1].title == "Senior Associate - Cyber Risk & Analysis, Technology Audit"
    assert roles[0].location == "Plano, TX"
    assert roles[0].url == "https://www.capitalonecareers.com/job/plano/director-project-management/1732/98197007024"
    assert roles[0].id == "98197007024"


def test_fetch_roles_empty_locations_means_nationwide_no_geocode(monkeypatch):
    location_calls = []

    def fake_get(url, params, headers, timeout):
        if url == capital_one._LOCATIONS_URL:
            location_calls.append(params)
            return _FakeResponse(LOCATIONS_PLANO)
        assert "Latitude" not in params
        assert "LocationPath" not in params
        return _FakeResponse(PAGE1)

    monkeypatch.setattr(capital_one.requests, "get", fake_get)

    roles = capital_one.fetch_roles([])

    assert location_calls == []  # no geocoding happens for a nationwide search
    assert len(roles) == 2


def test_fetch_roles_paginates_until_total_pages(monkeypatch):
    pages_served = []

    def fake_get(url, params, headers, timeout):
        if url == capital_one._LOCATIONS_URL:
            return _FakeResponse(LOCATIONS_PLANO)
        pages_served.append(params["CurrentPage"])
        return _FakeResponse(PAGE1_OF2 if params["CurrentPage"] == 1 else PAGE2_OF2)

    monkeypatch.setattr(capital_one.requests, "get", fake_get)

    roles = capital_one.fetch_roles([LocationFilter(country="United States", state="TX", city="Plano")])

    assert pages_served == [1, 2]
    assert {r.title for r in roles} == {"Director, Project Management", "Lead Software Engineer, Back End"}


def test_fetch_roles_dedupes_across_multiple_locations(monkeypatch):
    def fake_get(url, params, headers, timeout):
        if url == capital_one._LOCATIONS_URL:
            return _FakeResponse(LOCATIONS_PLANO)
        return _FakeResponse(PAGE1)

    monkeypatch.setattr(capital_one.requests, "get", fake_get)

    dallas = LocationFilter(country="United States", state="TX", city="Dallas")
    plano = LocationFilter(country="United States", state="TX", city="Plano")
    roles = capital_one.fetch_roles([dallas, plano])

    # same 2 jobs returned for both locations in this fixture - dedupe keeps only 2
    assert len(roles) == 2


def test_geocode_returns_none_when_no_candidates(monkeypatch):
    def fake_get(url, params, headers, timeout):
        return _FakeResponse([])

    monkeypatch.setattr(capital_one.requests, "get", fake_get)

    assert capital_one._geocode("Nowhere, XX") is None


def test_fetch_roles_raises_on_non_200(monkeypatch):
    def fake_get(url, params, headers, timeout):
        if url == capital_one._LOCATIONS_URL:
            return _FakeResponse(LOCATIONS_PLANO)
        return _FakeResponse({}, status_code=500)

    monkeypatch.setattr(capital_one.requests, "get", fake_get)

    try:
        capital_one.fetch_roles([LocationFilter(country="United States", state="TX", city="Plano")])
        assert False, "expected FetchError"
    except capital_one.FetchError:
        pass
