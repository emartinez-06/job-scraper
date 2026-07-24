import json
from pathlib import Path

from job_watch.companies import goldman_sachs
from job_watch.config import LocationFilter

FIXTURE = Path(__file__).parent / "fixtures" / "goldman_campus_roles_page0.json"


class _FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code
        self.text = json.dumps(payload)

    def json(self) -> dict:
        return self._payload


def test_fetch_roles_parses_items_and_stops_after_one_page(monkeypatch):
    payload = json.loads(FIXTURE.read_text())
    calls = []

    def fake_post(url, json, headers, timeout):
        calls.append(json)
        return _FakeResponse(payload)

    monkeypatch.setattr(goldman_sachs.requests, "post", fake_post)

    roles = goldman_sachs.fetch_roles([LocationFilter(country="United States", state="TX", city="Dallas")])

    assert len(calls) == 1  # totalCount (3) fits in one page, so no second request
    assert [r.id for r in roles] == ["158147_GS_CAMPUS", "160001_GS_CAMPUS", "160002_GS_CAMPUS"]
    assert roles[1].title == "2027 | Americas | New York | Engineering | Summer Analyst"
    assert roles[1].location == "New York, United States"
    assert roles[1].url == "https://higher.gs.com/roles/160001"

    sent_filters = calls[0]["variables"]["searchQueryInput"]["filters"]
    assert sent_filters == [
        {
            "filterCategoryType": "LOCATION",
            "filters": [
                {"filter": "United States", "subFilters": [{"filter": "TX", "subFilters": [{"filter": "Dallas", "subFilters": []}]}]}
            ],
        }
    ]


def test_location_filters_country_only_leaves_state_unrestricted(monkeypatch):
    payload = json.loads(FIXTURE.read_text())
    calls = []

    def fake_post(url, json, headers, timeout):
        calls.append(json)
        return _FakeResponse(payload)

    monkeypatch.setattr(goldman_sachs.requests, "post", fake_post)

    goldman_sachs.fetch_roles([LocationFilter(country="United States")])

    sent_filters = calls[0]["variables"]["searchQueryInput"]["filters"]
    assert sent_filters == [
        {"filterCategoryType": "LOCATION", "filters": [{"filter": "United States", "subFilters": []}]}
    ]


def test_fetch_roles_raises_on_non_200(monkeypatch):
    def fake_post(url, json, headers, timeout):
        return _FakeResponse({}, status_code=500)

    monkeypatch.setattr(goldman_sachs.requests, "post", fake_post)

    try:
        goldman_sachs.fetch_roles([])
        assert False, "expected FetchError"
    except goldman_sachs.FetchError:
        pass
