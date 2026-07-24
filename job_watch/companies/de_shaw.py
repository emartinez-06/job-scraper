"""D. E. Shaw open roles (full-time and internship).

D. E. Shaw's careers pages are server-rendered Next.js, and - conveniently
- embed the complete jobs list as JSON right in the page's __NEXT_DATA__
script tag. No separate API call, no pagination, and no Next.js buildId to
track: fetch the plain HTML, parse out that one script tag.

Full-time roles and internships are split across two pages/keys
("regularJobs" on /careers/choose-your-path, "internships" on
/careers/internships) - both are fetched and merged. A third key,
"internalJobs", is deliberately skipped: those are internal-transfer
postings only current employees can apply to.

Only US/UK roles show up here; D. E. Shaw India runs an entirely separate
careers site (deshawindia.com) this module doesn't cover.
"""

from __future__ import annotations

import json
import re

import requests

from job_watch.config import LocationFilter
from job_watch.registry import register
from job_watch.roles import Role

_PAGES = {
    "regularJobs": "https://www.deshaw.com/careers/choose-your-path",
    "internships": "https://www.deshaw.com/careers/internships",
}
_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
_NEXT_DATA = re.compile(
    r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', re.S
)

# D. E. Shaw's job data has no country field, only a city - it only ever
# posts to these three, so this is a complete, stable mapping in practice.
_CITY_COUNTRIES = {
    "New York": "United States",
    "Denver": "United States",
    "London": "United Kingdom",
}


class FetchError(RuntimeError):
    pass


def _location_matches(city: str, locations: list[LocationFilter]) -> bool:
    if not locations:
        return True
    country = _CITY_COUNTRIES.get(city)
    for loc in locations:
        if loc.city is not None:
            if loc.city.lower() == city.lower():
                return True
        elif loc.country == country:
            return True
    return False


def _fetch_jobs(url: str, jobs_key: str) -> list[dict]:
    response = requests.get(url, headers={"User-Agent": _USER_AGENT}, timeout=20)
    if response.status_code != 200:
        raise FetchError(f"D. E. Shaw role listing failed: {response.status_code}")

    match = _NEXT_DATA.search(response.text)
    if match is None:
        raise FetchError("D. E. Shaw page layout changed: __NEXT_DATA__ not found")

    return json.loads(match.group(1))["props"]["pageProps"][jobs_key]


def _to_role(job: dict) -> Role | None:
    data = job["data"]
    job_locations = data.get("jobMetadata", {}).get("jobLocations") or []
    city = job_locations[0]["name"] if job_locations else None
    if city is None:
        return None

    department = (data.get("department") or {}).get("name", "")
    headers = ", ".join(data.get("jobHeaders") or [])
    division = f"{headers} - {department}" if department else headers

    return Role(
        id=str(data["id"]),
        title=data["displayName"],
        division=division,
        location=city,
        url=f"https://www.deshaw.com/careers/{data['jobUrl'].lower()}",
    )


@register("de_shaw")
def fetch_roles(locations: list[LocationFilter]) -> list[Role]:
    """Fetches every open role (full-time and internship), optionally
    restricted to given locations.
    """
    roles = []
    for jobs_key, url in _PAGES.items():
        for job in _fetch_jobs(url, jobs_key):
            role = _to_role(job)
            if role is not None and _location_matches(role.location, locations):
                roles.append(role)
    return roles
