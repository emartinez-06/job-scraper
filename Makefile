.PHONY: setup test watch

VENV := .venv
PYTHON := $(VENV)/bin/python
PYTEST := $(VENV)/bin/pytest

setup:
	python3 -m venv $(VENV)
	$(VENV)/bin/pip install -q -r requirements-dev.txt

test:
	$(PYTEST) -q

# Fetches real, live postings and prints what would be notified, without
# opening any GitHub issues or writing state. Safe to run anytime.
watch:
	$(PYTHON) -m job_watch.main --dry-run
