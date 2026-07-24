"""Sends notifications by opening a GitHub Issue.

The workflow runs inside the same repo it watches, so the built-in
GITHUB_TOKEN is enough to create issues - no notification secrets to
configure. As the repo owner, GitHub emails you the moment the issue opens.
"""

from __future__ import annotations

import os

import requests

_API_ROOT = "https://api.github.com"


class NotifyError(RuntimeError):
    pass


def create_issue(title: str, body: str, labels: list[str] | None = None) -> str:
    """Opens a GitHub issue and returns its URL.

    Requires GITHUB_TOKEN and GITHUB_REPOSITORY (both set automatically by
    GitHub Actions) in the environment.
    """
    token = os.environ["GITHUB_TOKEN"]
    repo = os.environ["GITHUB_REPOSITORY"]
    response = requests.post(
        f"{_API_ROOT}/repos/{repo}/issues",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        },
        json={"title": title, "body": body, "labels": labels or []},
        timeout=20,
    )
    if response.status_code != 201:
        raise NotifyError(
            f"GitHub issue creation failed: {response.status_code} {response.text}"
        )
    return response.json()["html_url"]
