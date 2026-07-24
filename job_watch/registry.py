"""A tiny self-registration registry so a company module is the only file
that needs to change to add a new company - nothing else in the codebase
has to know it exists.

Each company module decorates its fetch function with `@register("its_id")`.
`job_watch/companies/__init__.py` imports every module in that package
purely so those decorators run; see README "Adding a company".
"""

from __future__ import annotations

import importlib
import pkgutil
from typing import Callable

from job_watch.config import LocationFilter
from job_watch.roles import Role

Fetcher = Callable[[list[LocationFilter]], list[Role]]

_fetchers: dict[str, Fetcher] = {}


def register(company_id: str) -> Callable[[Fetcher], Fetcher]:
    def decorator(fn: Fetcher) -> Fetcher:
        _fetchers[company_id] = fn
        return fn

    return decorator


def get_fetcher(company_id: str) -> Fetcher | None:
    return _fetchers.get(company_id)


def discover(package_name: str, package_path: list[str]) -> None:
    """Imports every module in a package, triggering its @register calls."""
    for _, module_name, _ in pkgutil.iter_modules(package_path):
        importlib.import_module(f"{package_name}.{module_name}")
