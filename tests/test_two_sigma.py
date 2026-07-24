from pathlib import Path

from job_watch.companies import two_sigma
from job_watch.config import LocationFilter

FIXTURES = Path(__file__).parent / "fixtures"
PAGE_0 = (FIXTURES / "two_sigma_openroles_page0.html").read_text()
EMPTY = (FIXTURES / "two_sigma_openroles_empty.html").read_text()


class _FakeResponse:
    def __init__(self, text: str, status_code: int = 200):
        self.text = text
        self.status_code = status_code


def test_fetch_roles_parses_jobs_and_stops_on_empty_page(monkeypatch):
    calls = []

    def fake_get(url, params, headers, timeout):
        calls.append(params)
        return _FakeResponse(PAGE_0 if params["jobOffset"] == 0 else EMPTY)

    monkeypatch.setattr(two_sigma.requests, "get", fake_get)

    roles = two_sigma.fetch_roles([])

    assert len(calls) == 2  # page 0 has jobs, page 1 (offset 10) is empty, so it stops
    assert [r.title for r in roles] == [
        "AI Research Scientist - Campus Full-Time",
        "Software Engineer, London & Trading Systems",  # &amp; unescaped
    ]
    assert roles[0].division == "Quantitative Research"
    assert roles[0].location == "United States - NY New York"
    assert roles[0].id == roles[0].url


def test_fetch_roles_filters_by_country(monkeypatch):
    def fake_get(url, params, headers, timeout):
        return _FakeResponse(PAGE_0 if params["jobOffset"] == 0 else EMPTY)

    monkeypatch.setattr(two_sigma.requests, "get", fake_get)

    uk_only = two_sigma.fetch_roles([LocationFilter(country="United Kingdom")])

    assert len(uk_only) == 1
    assert uk_only[0].title.startswith("Software Engineer")


def test_fetch_roles_raises_on_non_200(monkeypatch):
    def fake_get(url, params, headers, timeout):
        return _FakeResponse("", status_code=500)

    monkeypatch.setattr(two_sigma.requests, "get", fake_get)

    try:
        two_sigma.fetch_roles([])
        assert False, "expected FetchError"
    except two_sigma.FetchError:
        pass
