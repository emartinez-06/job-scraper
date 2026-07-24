"""Hudson River Trading (HRT) open roles.

HRT's careers page (a WordPress site) renders its job cards client-side via
a custom "hrt-jobs" plugin, which calls WordPress's generic AJAX endpoint
(wp-admin/admin-ajax.php, action=get_hrt_jobs_handler) to fetch them. That
endpoint turns out to need no auth, session, or nonce - it's a plain POST
that returns every open role as JSON (each with a pre-rendered HTML card
in `content`, which is parsed here for location/category).
"""

from __future__ import annotations

import html
import re

import requests

from job_watch.config import LocationFilter
from job_watch.registry import register
from job_watch.roles import Role

_URL = "https://www.hudsonrivertrading.com/wp-admin/admin-ajax.php"
_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
_PAYLOAD = {
    "action": "get_hrt_jobs_handler",
    "data[search]": "",
    "setting": (
        '{"meta_data":[{"icon":"","term":"locations"},{"icon":"","term":"job-category"},'
        '{"icon":"","term":"job-type"}],"settings":{"hide_job_id":true}}'
    ),
}

_META_BLOCK = re.compile(r'<div class="hrt-card-meta-desktop"[^>]*>(.*?)</div>', re.S)
_INFO_LIST = re.compile(r'<ul class="hrt-card-info-list[^"]*">(.*?)</ul>', re.S)
_SPAN = re.compile(r"<span>([^<]*)</span>")
_TITLE_LINK = re.compile(r'<a class="hrt-card-title" href="([^"]+)"')

# HRT's job cards only give city names, not countries - this is a complete,
# stable mapping of every city they currently post to.
_CITY_COUNTRIES = {
    "Austin": "United States",
    "Boston": "United States",
    "Boulder": "United States",
    "Chicago": "United States",
    "New York": "United States",
    "Dublin": "Ireland",
    "London": "United Kingdom",
    "Hong Kong": "Hong Kong",
    "Seoul": "South Korea",
    "Shanghai Shi": "China",
    "Singapore": "Singapore",
}


class FetchError(RuntimeError):
    pass


def _parse_card(content: str) -> tuple[list[str], list[str], str | None]:
    """Returns (cities, category_parts, url) parsed from a job's HTML card."""
    meta_match = _META_BLOCK.search(content)
    cities: list[str] = []
    category_parts: list[str] = []
    if meta_match is not None:
        lists = _INFO_LIST.findall(meta_match.group(1))
        if len(lists) >= 1:
            cities = [html.unescape(s.strip()) for s in _SPAN.findall(lists[0])]
        if len(lists) >= 2:
            category_parts = [
                html.unescape(s.strip())
                for s in _SPAN.findall(lists[1])
                if s.strip() not in ("•", "|")
            ]

    link_match = _TITLE_LINK.search(content)
    url = link_match.group(1) if link_match else None
    return cities, category_parts, url


def _location_matches(cities: list[str], locations: list[LocationFilter]) -> bool:
    if not locations:
        return True
    for city in cities:
        country = _CITY_COUNTRIES.get(city)
        for loc in locations:
            if loc.city is not None and loc.city.lower() == city.lower():
                return True
            if loc.city is None and loc.country == country:
                return True
    return False


@register("hudson_river_trading")
def fetch_roles(locations: list[LocationFilter]) -> list[Role]:
    """Fetches every open role, optionally restricted to given locations."""
    response = requests.post(
        _URL,
        data=_PAYLOAD,
        headers={"User-Agent": _USER_AGENT},
        timeout=20,
    )
    if response.status_code != 200:
        raise FetchError(f"HRT role listing failed: {response.status_code} {response.text}")

    roles = []
    for job in response.json():
        cities, category_parts, url = _parse_card(job["content"])
        if url is None or not _location_matches(cities, locations):
            continue
        roles.append(
            Role(
                id=str(job["ID"]),
                title=html.unescape(job["title"]),
                division=", ".join(category_parts),
                location=", ".join(cities) if cities else "Unknown location",
                url=url,
            )
        )
    return roles
