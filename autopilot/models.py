"""Core data types shared across sources, scoring and storage."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Job:
    """A single job posting, normalised across sources."""

    source: str
    title: str
    company: str
    url: str
    location: str = ""
    description: str = ""
    tags: list[str] = field(default_factory=list)
    posted_at: str = ""
    salary: str = ""
    remote: bool = False

    @property
    def fingerprint(self) -> str:
        """Stable id used to avoid showing the same posting twice.

        Keyed on company + title rather than URL, because the same role is
        often reposted under a new URL every few weeks.
        """
        raw = f"{self.company.strip().lower()}|{self.title.strip().lower()}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    @property
    def haystack(self) -> str:
        """Lowercased blob used for keyword matching."""
        return " ".join(
            [self.title, self.description, " ".join(self.tags), self.location]
        ).lower()


@dataclass
class Verdict:
    """The scorer's decision about a job."""

    score: int
    reasons_for: list[str] = field(default_factory=list)
    reasons_against: list[str] = field(default_factory=list)
    rejected_by: str = ""

    @property
    def passed_gates(self) -> bool:
        return not self.rejected_by


@dataclass
class ScoredJob:
    job: Job
    verdict: Verdict
    seen_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
