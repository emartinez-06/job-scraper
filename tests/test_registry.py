import job_watch.companies  # noqa: F401 - triggers self-registration
import job_watch.registry as registry
from job_watch.companies import goldman_sachs
from job_watch.registry import get_fetcher, register


def test_company_modules_self_register_on_import():
    assert get_fetcher("goldman_sachs") is goldman_sachs.fetch_roles


def test_get_fetcher_returns_none_for_unknown_company():
    assert get_fetcher("nonexistent_company") is None


def test_register_is_reusable_for_a_new_company(monkeypatch):
    monkeypatch.setattr(registry, "_fetchers", dict(registry._fetchers))

    @register("acme_corp")
    def fetch_acme_roles(locations):
        return []

    assert get_fetcher("acme_corp") is fetch_acme_roles
