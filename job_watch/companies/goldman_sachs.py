"""Goldman Sachs campus roles, via the same GraphQL API higher.gs.com's own
search page calls (api-higher.gs.com/gateway/api/v1/graphql, operation
GetCampusRoles).

This is a plain, unauthenticated POST endpoint - no session, no API key, no
browser required. It returns structured role data directly instead of
requiring HTML scraping, so it needs no cookies, headless browser, or bot
mitigation.
"""

from __future__ import annotations

import requests

from job_watch.config import LocationFilter
from job_watch.roles import Role

_API_URL = "https://api-higher.gs.com/gateway/api/v1/graphql"
_PAGE_SIZE = 100
_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)

_QUERY = """
query GetCampusRoles($searchQueryInput: RoleSearchQueryInput!) {
  roleSearch(searchQueryInput: $searchQueryInput) {
    totalCount
    items {
      roleId
      jobTitle
      division
      status
      locations {
        primary
        state
        country
        city
        __typename
      }
      __typename
    }
    __typename
  }
}
"""


class FetchError(RuntimeError):
    pass


def _location_filters(locations: list[LocationFilter]) -> list[dict]:
    """Builds the nested country/state/city filter GS's API expects.

    An empty `subFilters` list at any level means "no further restriction
    within this country/state" - so a country-only entry (no state) matches
    every state and city in that country.
    """
    if not locations:
        return []

    tree: dict[str, dict[str, dict[str, None]]] = {}
    for loc in locations:
        states = tree.setdefault(loc.country, {})
        if loc.state is None:
            continue
        cities = states.setdefault(loc.state, {})
        if loc.city is not None:
            cities[loc.city] = None

    country_filters = []
    for country, states in tree.items():
        state_filters = [
            {"filter": state, "subFilters": [{"filter": city, "subFilters": []} for city in cities]}
            for state, cities in states.items()
        ]
        country_filters.append({"filter": country, "subFilters": state_filters})

    return [{"filterCategoryType": "LOCATION", "filters": country_filters}]


def _role_url(role_id: str) -> str:
    # roleId looks like "158147_GS_CAMPUS" - the numeric prefix is the id
    # higher.gs.com uses in its own role detail page URLs.
    numeric_id = role_id.split("_")[0]
    return f"https://higher.gs.com/roles/{numeric_id}"


def _location_label(locations: list[dict]) -> str:
    primary = next((loc for loc in locations if loc.get("primary")), None) or (
        locations[0] if locations else None
    )
    if primary is None:
        return "Unknown location"
    parts = [p for p in (primary.get("city"), primary.get("country")) if p]
    return ", ".join(parts) or "Unknown location"


def fetch_roles(locations: list[LocationFilter]) -> list[Role]:
    """Fetches every open campus role, optionally restricted to given locations.

    An empty `locations` list means worldwide.
    """
    roles: list[Role] = []
    page_number = 0
    while True:
        payload = {
            "operationName": "GetCampusRoles",
            "variables": {
                "searchQueryInput": {
                    "page": {"pageSize": _PAGE_SIZE, "pageNumber": page_number},
                    "sort": {"sortStrategy": "RELEVANCE", "sortOrder": "DESC"},
                    "filters": _location_filters(locations),
                    "experiences": ["CAMPUS"],
                    "searchTerm": "",
                }
            },
            "query": _QUERY,
        }
        response = requests.post(
            _API_URL,
            json=payload,
            headers={"Content-Type": "application/json", "User-Agent": _USER_AGENT},
            timeout=20,
        )
        if response.status_code != 200:
            raise FetchError(f"Goldman Sachs role search failed: {response.status_code} {response.text}")

        result = response.json()["data"]["roleSearch"]
        items = result["items"]
        for item in items:
            roles.append(
                Role(
                    id=item["roleId"],
                    title=item["jobTitle"],
                    division=item["division"] or "",
                    location=_location_label(item["locations"]),
                    url=_role_url(item["roleId"]),
                )
            )

        fetched_so_far = (page_number + 1) * _PAGE_SIZE
        if fetched_so_far >= result["totalCount"] or not items:
            break
        page_number += 1

    return roles
