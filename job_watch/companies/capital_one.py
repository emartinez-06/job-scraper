"""Capital One open roles.

Capital One's careers site (Avature-style, "search-jobs") loads its results
via a plain GET to /search-jobs/results, which returns a JSON envelope with
an HTML fragment (no auth, no session). Location filtering isn't a simple
city/state/country match - it geocodes a place name to a lat/lon via
/search-jobs/locations (also plain, public) and then searches within a
radius of that point, so this module does the same two-step lookup.

Note that this is a radius search, not an exact-match filter: it returned
noticeably different results for "Dallas, TX" and "Plano, TX" as search
centers even though the two are ~20 miles apart, so if you want a specific
office covered, geocode that office's own city rather than a nearby one.
"""

from __future__ import annotations

import html
import re

import requests

from job_watch.config import LocationFilter
from job_watch.registry import register
from job_watch.roles import Role

_BASE_URL = "https://www.capitalonecareers.com"
_LOCATIONS_URL = f"{_BASE_URL}/search-jobs/locations"
_RESULTS_URL = f"{_BASE_URL}/search-jobs/results"
_RECORDS_PER_PAGE = 100
_RADIUS_MILES = 50
_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)

_JOB_LINK = re.compile(r'<a href="([^"]+)" data-job-id="(\d+)">(.*?)</a>\s*(?:<button|</li>)', re.S)
_TITLE = re.compile(r"<h2>([^<]*)</h2>")
_LOCATION = re.compile(r'job-location">([^<]*)</span>')
_TOTAL_PAGES = re.compile(r'data-total-pages="(\d+)"')


class FetchError(RuntimeError):
    pass


def _geocode(term: str) -> dict | None:
    response = requests.get(
        _LOCATIONS_URL,
        params={"term": term, "countryCodes": "", "lat": "", "lon": ""},
        headers={"User-Agent": _USER_AGENT},
        timeout=20,
    )
    if response.status_code != 200:
        raise FetchError(f"Capital One location lookup failed: {response.status_code}")

    candidates = response.json()
    if not candidates:
        return None
    exact = next((c for c in candidates if c["value"].lower() == term.lower()), None)
    return exact or candidates[0]


def _search_term(location: LocationFilter) -> str:
    parts = [p for p in (location.city, location.state) if p]
    return ", ".join(parts) if parts else location.country


def _fetch_page(params: dict) -> tuple[list[Role], int]:
    response = requests.get(_RESULTS_URL, params=params, headers={"User-Agent": _USER_AGENT}, timeout=20)
    if response.status_code != 200:
        raise FetchError(f"Capital One role search failed: {response.status_code}")

    results_html = response.json()["results"]
    total_pages_match = _TOTAL_PAGES.search(results_html)
    total_pages = int(total_pages_match.group(1)) if total_pages_match else 1

    roles = []
    for href, job_id, block in _JOB_LINK.findall(results_html):
        title_match = _TITLE.search(block)
        location_match = _LOCATION.search(block)
        title = title_match.group(1) if title_match else "Unknown title"
        location = location_match.group(1) if location_match else "Unknown location"
        roles.append(
            Role(
                id=job_id,
                title=html.unescape(title),
                division="",
                location=html.unescape(location),
                url=f"{_BASE_URL}{href}",
            )
        )
    return roles, total_pages


def _fetch_for_geocode(geocode: dict | None, location_label: str) -> list[Role]:
    # Capital One's results endpoint appears to model-bind strictly - it
    # silently returns an empty result set unless every one of these fields
    # is present, even the ones left blank, so all of them are always sent.
    base_params = {
        "ActiveFacetID": 0,
        "RecordsPerPage": _RECORDS_PER_PAGE,
        "TotalContentResults": "",
        "Distance": _RADIUS_MILES,
        "RadiusUnitType": 0,
        "Keywords": "",
        "ShowRadius": "True",
        "IsPagination": "False",
        "CustomFacetName": "",
        "FacetTerm": "",
        "FacetType": 0,
        "SearchResultsModuleName": "Search Results",
        "SearchFiltersModuleName": "Search Filters",
        "SortCriteria": 0,
        "SortDirection": 0,
        "SearchType": 5,
        "PostalCode": "",
        "ResultsType": 0,
        "fc": "",
        "fl": "",
        "fcf": "",
        "afc": "",
        "afl": "",
        "afcf": "",
        "TotalContentPages": "NaN",
    }
    if geocode is not None:
        base_params.update(
            {
                "Location": location_label,
                "Latitude": geocode["lat"],
                "Longitude": geocode["lon"],
                "LocationType": geocode["type"],
                "LocationPath": geocode["lp"],
            }
        )

    roles: list[Role] = []
    page = 1
    while True:
        page_roles, total_pages = _fetch_page({**base_params, "CurrentPage": page})
        roles.extend(page_roles)
        if page >= total_pages:
            break
        page += 1
    return roles


@register("capital_one")
def fetch_roles(locations: list[LocationFilter]) -> list[Role]:
    """Fetches every open role, optionally restricted to given locations.

    Each location is geocoded and searched within a fixed-radius circle
    (see module docstring); an empty `locations` list means nationwide
    (every open role, unfiltered).
    """
    if not locations:
        return _fetch_for_geocode(None, "")

    by_id: dict[str, Role] = {}
    for location in locations:
        term = _search_term(location)
        geocode = _geocode(term)
        if geocode is None:
            continue
        for role in _fetch_for_geocode(geocode, geocode["value"]):
            by_id[role.id] = role
    return list(by_id.values())
