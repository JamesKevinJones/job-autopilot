"""Remotive — public remote-jobs API, queried once per search term."""

from __future__ import annotations

from typing import Any

from ..models import Job
from .base import get_json, strip_html

API = "https://remotive.com/api/remote-jobs"

# `search` alone returns unrelated roles (it matches description text, so
# "Sales Jedi" comes back for "engineer"). Pinning the category first is what
# actually restricts results to software engineering.
CATEGORY = "software-dev"

# Weighted towards zero-experience language. Searching "backend" returns a
# pool that is overwhelmingly mid-level and then throws almost all of it away
# at the gate; searching "fresher" and "graduate" asks for the right pool in
# the first place.
SEARCH_TERMS = (
    "junior",
    "intern",
    "graduate",
    "entry level",
    "trainee",
    "associate software engineer",
    "full stack",
    "backend",
    "python",
)


class Remotive:
    name = "remotive"

    def fetch(self, profile: dict[str, Any]) -> list[Job]:
        seen: set[str] = set()
        jobs: list[Job] = []

        for term in SEARCH_TERMS:
            payload = get_json(API, params={"category": CATEGORY, "search": term, "limit": 100})
            for item in payload.get("jobs", []):
                job_id = str(item.get("id"))
                if job_id in seen:
                    continue
                seen.add(job_id)

                jobs.append(
                    Job(
                        source=self.name,
                        title=item.get("title", ""),
                        company=item.get("company_name", ""),
                        url=item.get("url", ""),
                        location=item.get("candidate_required_location") or "Remote",
                        description=strip_html(item.get("description", "")),
                        tags=item.get("tags", []),
                        posted_at=item.get("publication_date", ""),
                        salary=item.get("salary", ""),
                        remote=True,
                    )
                )
        return jobs
