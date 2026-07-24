"""Tracks which role ids have already been seen, per company."""

from __future__ import annotations

import json
from pathlib import Path

State = dict[str, list[str]]


def load_state(path: Path) -> State:
    if not path.exists():
        return {}
    with path.open() as f:
        return json.load(f)


def save_state(path: Path, state: State) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        json.dump(state, f, indent=2, sort_keys=True)
        f.write("\n")


def newly_seen(previous_ids: list[str], current_ids: list[str]) -> list[str]:
    previous = set(previous_ids)
    return sorted(role_id for role_id in current_ids if role_id not in previous)
