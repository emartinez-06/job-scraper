"""Entry point: check every configured company for new roles, notify on
newly-posted ones, and persist state for the next run.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import job_watch.companies  # noqa: F401 - import discovers and registers every company module
from job_watch.config import CompanyConfig, load_config
from job_watch.notify import create_issue
from job_watch.registry import get_fetcher
from job_watch.roles import Role, matches_keywords
from job_watch.state import load_state, newly_seen, save_state

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = REPO_ROOT / "config" / "config.yaml"
DEFAULT_STATE_PATH = REPO_ROOT / "state" / "seen_roles.json"


def run(config_path: Path, state_path: Path, dry_run: bool) -> None:
    config = load_config(config_path)
    state = load_state(state_path)

    for company in config.companies:
        fetcher = get_fetcher(company.id)
        if fetcher is None:
            print(f"warning: no fetcher registered for company '{company.id}', skipping", file=sys.stderr)
            continue

        try:
            all_roles = fetcher(company.locations)
        except Exception as exc:  # noqa: BLE001 - keep other companies running
            print(f"warning: fetching {company.name} failed: {exc}", file=sys.stderr)
            continue

        matching = [role for role in all_roles if matches_keywords(role, company.keywords)]
        current_ids = [role.id for role in matching]
        by_id = {role.id: role for role in matching}

        previous_ids = state.get(company.id, [])
        new_ids = newly_seen(previous_ids, current_ids)

        if new_ids:
            _notify_new_roles(company, [by_id[role_id] for role_id in new_ids], dry_run)
        else:
            print(f"{company.name}: no new matching roles ({len(matching)} open)")

        state[company.id] = current_ids

    if not dry_run:
        save_state(state_path, state)


def _notify_new_roles(company: CompanyConfig, roles: list[Role], dry_run: bool) -> None:
    for role in roles:
        title = f"[{company.name}] {role.title}"
        body = (
            f"**Division:** {role.division}\n\n"
            f"**Location:** {role.location}\n\n"
            f"[View posting]({role.url})"
        )
        print(title)
        if not dry_run:
            url = create_issue(title, body, labels=[company.id])
            print(f"  -> {url}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Watch configured companies for new job postings.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE_PATH)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't create issues or write state; just print what would happen.",
    )
    args = parser.parse_args()
    run(args.config, args.state, args.dry_run)


if __name__ == "__main__":
    main()
