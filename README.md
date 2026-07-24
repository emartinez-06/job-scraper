# Job Scraper

A cron-driven watcher for company job/internship postings.
It polls each configured company's own career-site API on a schedule and opens a GitHub Issue - which GitHub emails to you - the moment a posting matching your keywords appears.

## How it works

Rather than scraping rendered HTML (fragile, and often blocked by bot protection), each company module talks to the same backend API the career site's own search page calls.
For Goldman Sachs, that's a public, unauthenticated GraphQL endpoint (`api-higher.gs.com/gateway/api/v1/graphql`) that returns structured role data directly - no cookies, no headless browser, no session required.

`job_watch/main.py` (run on a schedule by GitHub Actions):

1. Loads `config/config.yaml` - which companies to watch, which countries to restrict to, and which keywords a posting's title/division must contain.
2. Fetches every open campus/entry-level role for each company.
3. Filters to roles matching the configured keywords.
4. Diffs against `state/seen_roles.json` from the previous run.
5. Opens a GitHub Issue for anything newly seen.
6. Commits the updated state file back to the repo.

No server or always-on machine is required.

## Setup

1. Edit `config/config.yaml` - add or adjust companies, their `locations` filter, and the `keywords` a posting must match.
2. Push to `main`. The workflow in `.github/workflows/watch.yml` starts running on its schedule automatically once it's on the default branch.
   - If this repo was forked, GitHub disables Actions on forks by default - enable it from the **Actions** tab first.
   - GitHub auto-disables scheduled workflows after 60 days with no repository activity; a push (like a state-file commit) resets that clock.
3. Watch the repo's **Issues** tab, or just your email - GitHub notifies repository owners by email when a new issue opens, with no extra configuration.

No secrets or credentials are required.
The workflow uses the repository's built-in `GITHUB_TOKEN` to open issues and push state files.

## Adding a company

1. Create `job_watch/companies/<name>.py` with a `fetch_roles(countries: list[str]) -> list[Role]` function.
   Check the site's own network requests first (its search page almost always calls a JSON API under the hood) before resorting to HTML scraping or browser automation.
2. Register it in `_FETCHERS` in `job_watch/main.py`.
3. Add an entry under `companies:` in `config/config.yaml`.

## Local development

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest
```

Run the watcher locally without opening issues or writing state:

```sh
.venv/bin/python -m job_watch.main --dry-run
```

## Project structure

```
config/config.yaml           Companies to watch, location filters, keyword filters
job_watch/
  main.py                    Orchestrates a single watch run across all configured companies
  roles.py                   Shared Role type and keyword matching
  state.py                   Tracks previously-seen role ids per company
  notify.py                  Opens a GitHub Issue
  config.py                  Loads config.yaml
  companies/
    goldman_sachs.py          Goldman Sachs campus roles via their GraphQL API
state/seen_roles.json        Watcher's memory of what's already been notified, per company
tests/                       pytest suite, with captured-structure JSON fixtures
.github/workflows/watch.yml  Scheduled run, every 30 minutes
```

## Limitations / ideas not yet built

- Only Goldman Sachs is wired up so far. Add more companies as above.
- "Watch community internship-tracker channels" (e.g. the popular GitHub internship-list repos) was floated as a stretch goal but isn't implemented - it would be its own `job_watch/companies/`-style module that diffs a tracked repo's README instead of calling a company API.
- Keyword matching is a simple case-insensitive substring match against title + division; it's intentionally not a real search index in the interest of keeping this maintainable.

## License

MIT
