"""Shared role representation and keyword matching, used by every company module."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Role:
    id: str
    title: str
    division: str
    location: str
    url: str


def matches_keywords(role: Role, keywords: list[str]) -> bool:
    """True if any keyword appears (case-insensitive) in the role's title or division."""
    if not keywords:
        return True
    haystack = f"{role.title} {role.division}"
    pattern = re.compile("|".join(re.escape(k) for k in keywords), re.IGNORECASE)
    return bool(pattern.search(haystack))
