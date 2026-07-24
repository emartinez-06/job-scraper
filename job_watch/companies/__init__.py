"""One module per company, each self-registering a fetcher via
`@job_watch.registry.register("company_id")`. Importing this package (done
once, in job_watch/main.py) discovers and imports all of them, which is all
that's needed for a new company to plug in - see README "Adding a company".
"""

from job_watch.registry import discover

discover(__name__, __path__)
