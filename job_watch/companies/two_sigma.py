"""Two Sigma open roles, scraped from their public careers listing page.

Two Sigma's career site (an Avature-hosted "OpenRoles" page) has no
client-side JSON API to call - the page itself is fully server-rendered
HTML, so a plain HTTP GET already returns the whole job list. This needs no
JS execution, cookies, or session, and (as of writing) sits behind no bot
protection - just a normal HTTP client with a browser-like User-Agent.
"""

from __future__ import annotations

import html
import re

import requests

from job_watch.config import LocationFilter
from job_watch.registry import register
from job_watch.roles import Role

_URL = "https://careers.twosigma.com/careers/OpenRoles/"
_PAGE_SIZE = 10
_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)

_ARTICLE_SPLIT = re.compile(r'<article class="article article--result"')
_TITLE_LINK = re.compile(r'<a class="link" href="([^"]*)">\s*([^<]*?)\s*</a>')
_SPAN = re.compile(r'<span class="paragraph_inner-span">([^<]*)</span>')


class FetchError(RuntimeError):
    pass


def _parse_jobs(page_html: str) -> list[Role]:
    roles = []
    for block in _ARTICLE_SPLIT.split(page_html)[1:]:
        block = block[: block.find("</article>")]
        link = _TITLE_LINK.search(block)
        if link is None:
            continue  # the "No jobs found" placeholder on the last page has no link
        url, title = link.groups()
        spans = _SPAN.findall(block)
        location = spans[0] if spans else "Unknown location"
        division = spans[1] if len(spans) > 1 else ""
        roles.append(
            Role(
                id=url,
                title=html.unescape(title),
                division=html.unescape(division),
                location=html.unescape(location),
                url=url,
            )
        )
    return roles


def _country_matches(role_location: str, locations: list[LocationFilter]) -> bool:
    if not locations:
        return True
    # Location strings look like "United States - NY New York" - only the
    # country prefix is reliably structured, so state/city on a
    # LocationFilter are ignored here (see README "Adding a company").
    country = role_location.split(" - ")[0].strip()
    return any(loc.country == country for loc in locations)


@register("two_sigma")
def fetch_roles(locations: list[LocationFilter]) -> list[Role]:
    """Fetches every open role, optionally restricted to given countries."""
    all_roles: list[Role] = []
    offset = 0
    while True:
        response = requests.get(
            _URL,
            params={"jobRecordsPerPage": _PAGE_SIZE, "jobOffset": offset},
            headers={"User-Agent": _USER_AGENT},
            timeout=20,
        )
        if response.status_code != 200:
            raise FetchError(f"Two Sigma role listing failed: {response.status_code}")

        page_roles = _parse_jobs(response.text)
        if not page_roles:
            break
        all_roles.extend(page_roles)
        offset += _PAGE_SIZE

    return [role for role in all_roles if _country_matches(role.location, locations)]
