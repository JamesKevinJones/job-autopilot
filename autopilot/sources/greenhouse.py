"""Greenhouse and Lever company boards.

These are the only genuinely free route to Indian roles. Both expose public
JSON per company with no key, no rate limit worth worrying about, and no
paywall between you and the apply button — you apply on the company's own
site, which is also where an application actually gets read.

Slugs are verified working; unverified guesses were removed rather than left
to 404 on every run.
"""

from __future__ import annotations

from typing import Any

from ..models import Job
from .base import get_json, repair_mojibake, strip_html

GREENHOUSE_API = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
LEVER_API = "https://api.lever.co/v0/postings/{slug}"

# Verified 2026-08-12. Commented counts are jobs / of which in India.
GREENHOUSE_BOARDS = (
    "hackerrank",                       # 28 / 17
    "druva",                            # 29 / 11
    "postman",                          # 107 / 9
    "groww",                            # 8 / 8
    "phonepe",                          # 79 / 1
    "razorpaysoftwareprivatelimited",   # 21
    "glance",                           # 44
)

LEVER_BOARDS = (
    "meesho",   # 53
    "zeta",     # 24
    "cred",     # 5
)


class Greenhouse:
    name = "greenhouse"

    def fetch(self, profile: dict[str, Any]) -> list[Job]:
        jobs: list[Job] = []
        for slug in GREENHOUSE_BOARDS:
            try:
                payload = get_json(GREENHOUSE_API.format(slug=slug), params={"content": "true"})
            except Exception:
                continue  # a dead board must not kill the source

            for item in payload.get("jobs", []):
                location = (item.get("location") or {}).get("name", "")
                jobs.append(
                    Job(
                        source=f"{self.name}:{slug}",
                        title=repair_mojibake(item.get("title", "")),
                        company=slug.replace("softwareprivatelimited", "").title(),
                        url=item.get("absolute_url", ""),
                        location=repair_mojibake(location),
                        description=strip_html(item.get("content", "")),
                        posted_at=item.get("updated_at", ""),
                        remote="remote" in location.lower(),
                    )
                )
        return jobs


def _lever_text(item: dict[str, Any]) -> str:
    """Lever splits a posting across several fields.

    The requirements — which is where the tech stack and the years-of-
    experience line actually live — sit in ``lists[].content`` as HTML, not in
    ``descriptionPlain``. Reading only the description meant every Lever job
    looked like it had no stack and no experience requirement.
    """
    parts = [item.get("descriptionPlain", "") or ""]
    for section in item.get("lists") or []:
        parts.append(section.get("text", "") or "")
        parts.append(strip_html(section.get("content", "") or ""))
    return " ".join(parts)[:6000]


class Lever:
    name = "lever"

    def fetch(self, profile: dict[str, Any]) -> list[Job]:
        jobs: list[Job] = []
        for slug in LEVER_BOARDS:
            try:
                payload = get_json(LEVER_API.format(slug=slug), params={"mode": "json"})
            except Exception:
                continue

            for item in payload:
                categories = item.get("categories") or {}
                location = categories.get("location", "") or ""
                jobs.append(
                    Job(
                        source=f"{self.name}:{slug}",
                        title=repair_mojibake(item.get("text", "")),
                        company=slug.title(),
                        url=item.get("hostedUrl", ""),
                        location=repair_mojibake(location),
                        description=_lever_text(item),
                        posted_at=str(item.get("createdAt", "")),
                        remote="remote" in location.lower(),
                    )
                )
        return jobs
