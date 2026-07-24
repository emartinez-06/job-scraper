"""Loads and validates the watcher's YAML configuration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class LocationFilter:
    country: str
    state: str | None = None
    city: str | None = None


@dataclass(frozen=True)
class CompanyConfig:
    id: str
    name: str
    locations: list[LocationFilter]
    keywords: list[str]


@dataclass(frozen=True)
class Config:
    companies: list[CompanyConfig]


def load_config(path: Path) -> Config:
    with path.open() as f:
        raw = yaml.safe_load(f)

    companies = [
        CompanyConfig(
            id=c["id"],
            name=c["name"],
            locations=[
                LocationFilter(country=loc["country"], state=loc.get("state"), city=loc.get("city"))
                for loc in c.get("locations", [])
            ],
            keywords=list(c.get("keywords", [])),
        )
        for c in raw.get("companies", [])
    ]
    return Config(companies=companies)
