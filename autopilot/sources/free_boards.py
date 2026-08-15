"""Arbeitnow, Jobicy and Himalayas — free remote boards with open APIs.

All three let you apply without a subscription, unlike RemoteOK, which gates
the apply button behind $29.95/year.
"""

from __future__ import annotations

from typing import Any

from ..models import Job
from .base import get_json, repair_mojibake, strip_html


def _as_list(value: Any) -> list[str]:
    """Sources are inconsistent about tag shapes — dicts, strings, or lists."""
    if isinstance(value, list):
        return [str(v) for v in value]
    if isinstance(value, dict):
        return [str(v) for v in value.values()]
    if isinstance(value, str):
        return [value]
    return []


class Arbeitnow:
    name = "arbeitnow"
    API = "https://www.arbeitnow.com/api/job-board-api"

    def fetch(self, profile: dict[str, Any]) -> list[Job]:
        payload = get_json(self.API)
        jobs: list[Job] = []
        for item in payload.get("data", []):
            jobs.append(
                Job(
                    source=self.name,
                    title=repair_mojibake(item.get("title", "")),
                    company=repair_mojibake(item.get("company_name", "")),
                    url=item.get("url", ""),
                    location=repair_mojibake(item.get("location", "")),
                    description=strip_html(item.get("description", "")),
                    tags=_as_list(item.get("tags")) + _as_list(item.get("job_types")),
                    posted_at=str(item.get("created_at", "")),
                    remote=bool(item.get("remote")),
                )
            )
        return jobs


class Jobicy:
    name = "jobicy"
    API = "https://jobicy.com/api/v2/remote-jobs"

    def fetch(self, profile: dict[str, Any]) -> list[Job]:
        jobs: list[Job] = []
        seen: set[str] = set()

        # Jobicy filters by industry; these are the two that carry dev roles.
        for industry in ("engineering", "dev"):
            try:
                payload = get_json(self.API, params={"count": 50, "industry": industry})
            except Exception:
                continue

            for item in payload.get("jobs", []):
                job_id = str(item.get("id"))
                if job_id in seen:
                    continue
                seen.add(job_id)
                jobs.append(
                    Job(
                        source=self.name,
                        title=repair_mojibake(item.get("jobTitle", "")),
                        company=repair_mojibake(item.get("companyName", "")),
                        url=item.get("url", ""),
                        location=repair_mojibake(item.get("jobGeo", "") or "Remote"),
                        description=strip_html(item.get("jobExcerpt", "")),
                        tags=item.get("jobIndustry", []) or [],
                        posted_at=item.get("pubDate", ""),
                        remote=True,
                    )
                )
        return jobs


class Himalayas:
    name = "himalayas"
    API = "https://himalayas.app/jobs/api"

    def fetch(self, profile: dict[str, Any]) -> list[Job]:
        payload = get_json(self.API, params={"limit": 100})
        jobs: list[Job] = []
        for item in payload.get("jobs", []):
            locations = item.get("locationRestrictions") or []
            jobs.append(
                Job(
                    source=self.name,
                    title=repair_mojibake(item.get("title", "")),
                    company=repair_mojibake(item.get("companyName", "")),
                    url=item.get("applicationLink") or item.get("guid", ""),
                    location=", ".join(locations) if locations else "Remote",
                    description=strip_html(item.get("description", "")),
                    tags=item.get("categories", []) or [],
                    posted_at=str(item.get("pubDate", "")),
                    remote=True,
                )
            )
        return jobs
