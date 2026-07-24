from pathlib import Path

from job_watch.companies import de_shaw
from job_watch.config import LocationFilter

FIXTURES = Path(__file__).parent / "fixtures"
CHOOSE_YOUR_PATH_HTML = (FIXTURES / "de_shaw_choose_your_path.html").read_text()
INTERNSHIPS_HTML = (FIXTURES / "de_shaw_internships.html").read_text()


class _FakeResponse:
    def __init__(self, text: str, status_code: int = 200):
        self.text = text
        self.status_code = status_code


def test_fetch_roles_merges_regular_jobs_and_internships(monkeypatch):
    def fake_get(url, headers, timeout):
        if "internships" in url:
            return _FakeResponse(INTERNSHIPS_HTML)
        return _FakeResponse(CHOOSE_YOUR_PATH_HTML)

    monkeypatch.setattr(de_shaw.requests, "get", fake_get)

    roles = de_shaw.fetch_roles([])

    assert {r.title for r in roles} == {
        "Associate – Firmwide Technology Management",
        "Quantitative Analyst",
        "Quantitative Analyst Intern (New York) – Summer 2027",
    }
    # internalJobs must never surface, regardless of location filters
    assert "Internal Transfer - Should Be Skipped" not in {r.title for r in roles}

    quant = next(r for r in roles if r.title == "Quantitative Analyst")
    assert quant.division == "QUANTITATIVE RESEARCH & TECHNOLOGY DEVELOPMENT - Quantitative Strategies"
    assert quant.location == "London"
    assert quant.url == "https://www.deshaw.com/careers/quantitative-analyst-5637"
    assert quant.id == "5637"


def test_fetch_roles_filters_by_city(monkeypatch):
    def fake_get(url, headers, timeout):
        if "internships" in url:
            return _FakeResponse(INTERNSHIPS_HTML)
        return _FakeResponse(CHOOSE_YOUR_PATH_HTML)

    monkeypatch.setattr(de_shaw.requests, "get", fake_get)

    ny_only = de_shaw.fetch_roles([LocationFilter(country="United States", city="New York")])

    assert {r.title for r in ny_only} == {
        "Associate – Firmwide Technology Management",
        "Quantitative Analyst Intern (New York) – Summer 2027",
    }


def test_fetch_roles_filters_by_country(monkeypatch):
    def fake_get(url, headers, timeout):
        if "internships" in url:
            return _FakeResponse(INTERNSHIPS_HTML)
        return _FakeResponse(CHOOSE_YOUR_PATH_HTML)

    monkeypatch.setattr(de_shaw.requests, "get", fake_get)

    uk_only = de_shaw.fetch_roles([LocationFilter(country="United Kingdom")])

    assert [r.title for r in uk_only] == ["Quantitative Analyst"]


def test_fetch_roles_raises_when_next_data_missing(monkeypatch):
    def fake_get(url, headers, timeout):
        return _FakeResponse("<html>no next data here</html>")

    monkeypatch.setattr(de_shaw.requests, "get", fake_get)

    try:
        de_shaw.fetch_roles([])
        assert False, "expected FetchError"
    except de_shaw.FetchError:
        pass
