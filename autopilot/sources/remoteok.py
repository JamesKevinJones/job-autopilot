"""RemoteOK — public JSON feed of remote roles."""

from __future__ import annotations

from typing import Any

from ..models import Job
from .base import get_json, repair_mojibake, strip_html

API = "https://remoteok.com/api"

# The bare feed is every remote job on the site — barbers, lifeguards and
# handymen included. Tag-filtered feeds are the only way to get dev roles.
TAGS = ("dev", "python", "javascript", "react", "backend", "junior", "typescript")


class RemoteOK:
    name = "remoteok"

    def fetch(self, profile: dict[str, Any]) -> list[Job]:
        entries: list[dict[str, Any]] = []
        seen_ids: set[str] = set()

        for tag in TAGS:
            payload = get_json(API, params={"tag": tag})
            for item in payload:
                # The first element is RemoteOK's legal notice, not a job.
                if not isinstance(item, dict) or not item.get("position"):
                    continue
                job_id = str(item.get("id") or item.get("slug") or item.get("url"))
                if job_id in seen_ids:
                    continue
                seen_ids.add(job_id)
                entries.append(item)

        jobs: list[Job] = []
        for item in entries:
            jobs.append(
                Job(
                    source=self.name,
                    title=repair_mojibake(item.get("position", "")),
                    company=repair_mojibake(item.get("company", "")),
                    url=item.get("url") or item.get("apply_url", ""),
                    location=repair_mojibake(item.get("location") or "Remote"),
                    description=repair_mojibake(strip_html(item.get("description", ""))),
                    tags=[t for t in item.get("tags", []) if t],
                    posted_at=item.get("date", ""),
                    salary=_salary(item),
                    remote=True,
                )
            )
        return jobs


def _salary(item: dict[str, Any]) -> str:
    low, high = item.get("salary_min"), item.get("salary_max")
    if low and high:
        return f"${low:,} - ${high:,}"
    return ""
