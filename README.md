# Job Scraper

![Python](https://img.shields.io/badge/python-3.12%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

A cron-driven watcher for company job and internship postings.
It polls each configured company's own career-site API on a schedule and opens a GitHub Issue - which GitHub emails to you - the moment a posting matching your filters appears.

Fork it, add your target companies and keywords to one YAML file, push, and it starts watching.
No server, no database, no secrets to configure.

## How it works

Each company module prefers whatever data source is cleanest: a JSON API when the career site has one, and a plain HTML fetch (no headless browser) when it's server-rendered and doesn't.
Almost every modern careers site is either a single-page app backed by a JSON API, or a server-rendered page with no client-side API at all - open its network tab, search for a role, and you'll usually find one or the other within a couple of minutes.
This is both simpler to write and far more robust than driving a real browser, since a JSON/HTML contract changes far less often than a page's rendered DOM, and it needs no cookies, session, or headless Chrome to run on a schedule.

| Company | Data source | Notes |
|---|---|---|
| Goldman Sachs | Public GraphQL API (`api-higher.gs.com`) | Same endpoint `higher.gs.com`'s own search page calls; no auth |
| Two Sigma | Server-rendered HTML (Avature) | Plain GET returns the full job list already filled in; no bot protection encountered |
| D. E. Shaw | Server-rendered HTML (`__NEXT_DATA__` JSON embedded in the page) | Next.js embeds the whole job list as JSON right in the HTML - no API call, no buildId to track |
| Hudson River Trading | WordPress AJAX endpoint (`admin-ajax.php`) | A custom plugin's action, called with no auth/nonce required |
| Citadel Securities | Not implemented | Their careers site sits behind an active Cloudflare bot challenge (plain requests get a 403); deliberately not attempted - see "Limitations" |

`job_watch/main.py` runs on a schedule via GitHub Actions and, each time:

1. Loads `config/config.yaml` - which companies to watch, which locations to restrict to, and which keywords a posting's title/division must contain.
2. Fetches every open role for each configured company.
3. Filters to roles matching the configured keywords.
4. Diffs the result against `state/seen_roles.json` from the previous run.
5. Opens a GitHub Issue for anything newly seen.
6. Commits the updated state file back to the repo.

## Quickstart

1. Use this repo as a template (or clone/fork it) into your own GitHub account.
2. Edit `config/config.yaml` to list the companies, locations, and keywords you care about.
   Goldman Sachs, Two Sigma, D. E. Shaw, and Hudson River Trading are already wired up as working examples - see below to add more.
3. Push to `main`.
   The workflow in `.github/workflows/watch.yml` starts running on its schedule automatically once it's on your default branch.
   - If you forked instead of using this as a template, GitHub disables Actions on forks by default - enable it from your repo's **Actions** tab first.
   - GitHub also auto-disables scheduled workflows after 60 days with no repository activity; any push (like a state-file commit) resets that clock.
4. Watch your repo's **Issues** tab, or just your email - GitHub notifies repository owners by email when a new issue opens, with no extra configuration.

No secrets or credentials are required.
The workflow uses the repository's built-in `GITHUB_TOKEN` to open issues and push state files.

## Adding a company

This is the part meant to be plug-and-play: a company module is a single file, and it self-registers, so **no other file in the codebase needs to change.**

1. Find the company's underlying data source, in this order of preference:
   - **A JSON API.** Open the careers page in a browser, open DevTools' Network tab, filter to Fetch/XHR, and search for a role.
     Most career sites (Workday, Greenhouse, Lever, custom GraphQL gateways like Goldman's) call one.
     `job_watch/companies/goldman_sachs.py` and `hudson_river_trading.py` are working examples.
   - **Embedded JSON in server-rendered HTML.** If there's no XHR call, view the page source (not the rendered DOM) - React/Next.js sites often embed the full page data as JSON in a `<script>` tag (look for `__NEXT_DATA__`).
     `job_watch/companies/de_shaw.py` is a working example.
   - **Plain HTML scraping**, as a last resort: fetch the page with `requests` (no browser) and check whether the job list is already in the response.
     `job_watch/companies/two_sigma.py` is a working example; it's more fragile than the above since markup changes more often than a JSON contract.
   - If none of these work without solving a CAPTCHA or defeating active bot protection (Cloudflare challenge pages, etc.), stop - don't build a company module that fights that fight.
     Citadel Securities was skipped for exactly this reason; see "Limitations".
2. Create `job_watch/companies/<company_id>.py` following this shape:

   ```python
   from job_watch.config import LocationFilter
   from job_watch.registry import register
   from job_watch.roles import Role


   @register("<company_id>")
   def fetch_roles(locations: list[LocationFilter]) -> list[Role]:
       """Fetches every open role, optionally restricted to given locations."""
       # Call the company's API here and map each result to a Role:
       #   Role(id=..., title=..., division=..., location=..., url=...)
       # `id` just needs to be stable across runs - it's what's diffed
       # against state to detect "new" postings.
       ...
   ```

3. Add an entry for it under `companies:` in `config/config.yaml` (see the reference below).
4. Run `make watch` to sanity-check it against the real, live API before pushing - it only prints what it finds, it doesn't open issues or write state.

`LocationFilter` and the country/state/city shape it implies are just what Goldman's API happens to want; treat it as an example, not a contract.
If your company's API filters by location differently (or not at all), have your module interpret the `locations` list however makes sense, or ignore it entirely.
The one thing every fetcher must return is a list of `Role`, since that's what keyword-matching and state-diffing operate on.

## Configuration reference

```yaml
companies:
  - id: goldman_sachs          # matches the id passed to @register(...)
    name: "Goldman Sachs"      # used in issue titles and log output
    # Location filter. country/state/city map to Goldman's own LOCATION
    # filter hierarchy; other companies interpret this differently (see
    # each module's docstring) - e.g. de_shaw and hudson_river_trading
    # only look at `country` and `city`, ignoring `state`. Omitting
    # `state`/`city` matches every state/city within the level above.
    # Empty `locations` list means worldwide.
    locations:
      - country: "United States"
        state: "TX"
        city: "Dallas"
    # A role notifies if any of these (case-insensitive) appear in its
    # title or division. Empty list means every posting notifies,
    # regardless of keyword, e.g. "Quantitative Strats", "Engineering
    # Division", "Software Engineer".
    keywords: []

  - id: two_sigma
    name: "Two Sigma"
    locations:
      - country: "United States"
    keywords: []

  - id: de_shaw
    name: "D. E. Shaw"
    locations:
      - country: "United States"
    keywords: []

  - id: hudson_river_trading
    name: "Hudson River Trading"
    locations:
      - country: "United States"
    keywords: []
```

Add as many entries under `companies:` as you like; each is independent, and a fetch failure for one company (a schema change, a timeout) is logged as a warning and doesn't stop the others from running.

## Local development

```sh
make setup   # creates .venv and installs dependencies
make test    # runs the pytest suite
make watch   # dry-run against the real, live APIs - prints what it finds, changes nothing
```

Point `job_watch.main` at different files directly if you want to test against an alternate config or throwaway state:

```sh
.venv/bin/python -m job_watch.main --config /path/to/config.yaml --state /path/to/state.json --dry-run
```

## Project structure

```
config/config.yaml           Companies to watch, location filters, keyword filters
job_watch/
  main.py                    Orchestrates a single watch run across all configured companies
  registry.py                Self-registration mechanism company modules plug into
  roles.py                   Shared Role type and keyword matching
  state.py                   Tracks previously-seen role ids per company
  notify.py                  Opens a GitHub Issue
  config.py                  Loads config.yaml
  companies/
    goldman_sachs.py          Goldman Sachs roles via their GraphQL API
    two_sigma.py              Two Sigma roles, scraped from server-rendered HTML
    de_shaw.py                D. E. Shaw roles, parsed from embedded Next.js JSON
    hudson_river_trading.py   HRT roles via their WordPress AJAX endpoint
state/seen_roles.json        Watcher's memory of what's already been notified, per company
tests/                       pytest suite, with captured-structure JSON fixtures
.github/workflows/watch.yml  Scheduled run, every 30 minutes
Makefile                     make setup / make test / make watch
```

## Limitations / ideas not yet built

- Citadel Securities was deliberately skipped: its careers site sits behind an active Cloudflare bot challenge (plain requests get a 403 "Just a moment..." page), and defeating that wasn't attempted on purpose.
  If you have a way to reach their listings that doesn't involve bypassing that protection, `job_watch/companies/` is where a module for it would go.
- Watching community internship-tracker channels (e.g. the popular GitHub internship-list repos that get updated by many contributors) was floated as a stretch goal but isn't implemented.
  It would be its own `job_watch/companies/`-style module that diffs a tracked repo's README instead of calling a company API.
- Keyword matching is a simple case-insensitive substring match against title + division; it's intentionally not a real search index, in the interest of keeping this maintainable.
- The 30-minute schedule in `.github/workflows/watch.yml` is a starting point - tighten or loosen it depending on how many companies you're watching and how time-sensitive you want alerts to be.

## License

MIT
