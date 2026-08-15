"""Discovery run: fetch -> gate -> score -> store."""

from __future__ import annotations

from dataclasses import dataclass

from .config import load_profile
from .models import ScoredJob
from .scorer import score as score_job
from .sources import ALL_SOURCES
from .store import connect, record_run, upsert

# Jobs at or above this score go into the approval queue.
#
# Set from the observed distribution, not picked in advance. With the gates
# doing the disqualifying work, scores for real software roles cluster in the
# 38-52 band and the old threshold of 55 sat above the ceiling, so nothing
# ever queued. 45 admits genuine entry-level-plausible roles while staying
# clear of the levelled-senior postings that cluster at 38.
QUEUE_THRESHOLD = 45


@dataclass
class RunResult:
    fetched: int = 0
    new_jobs: int = 0
    queued: int = 0
    rejected: int = 0
    errors: list[str] = None

    def __post_init__(self) -> None:
        if self.errors is None:
            self.errors = []


def run(threshold: int = QUEUE_THRESHOLD) -> RunResult:
    """One full discovery pass across every source."""
    profile = load_profile()
    result = RunResult()

    with connect() as conn:
        for source in ALL_SOURCES:
            try:
                jobs = source.fetch(profile)
            except Exception as exc:  # a dead source must not kill the run
                result.errors.append(f"{source.name}: {exc}")
                continue

            result.fetched += len(jobs)
            for job in jobs:
                if not job.title or not job.company or not job.url:
                    continue

                verdict = score_job(job, profile)
                scored = ScoredJob(job=job, verdict=verdict)

                if not upsert(conn, scored, threshold):
                    continue  # already seen

                result.new_jobs += 1
                if not verdict.passed_gates:
                    result.rejected += 1
                elif verdict.score >= threshold:
                    result.queued += 1

        record_run(
            conn,
            fetched=result.fetched,
            new_jobs=result.new_jobs,
            queued=result.queued,
            rejected=result.rejected,
            errors="; ".join(result.errors),
        )

    return result
