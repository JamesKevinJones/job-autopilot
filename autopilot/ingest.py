"""Ingest job posts pasted from places that have no API.

WhatsApp Channels, Telegram groups and forwarded email carry a lot of Indian
fresher roles that never reach a job board. None of them can be read
automatically: WhatsApp has no public channel API, and driving WhatsApp Web
breaks its terms and risks the account.

So this is the manual path, and it is deliberately the *only* manual part:
paste the text, and every gate, score and store rule that runs on Greenhouse
or Remotive runs on it identically. A five-year automotive role pasted from a
channel is rejected for the same reason it would be from an API.
"""

from __future__ import annotations

import re
from pathlib import Path

from .config import load_profile
from .models import Job, ScoredJob
from .pipeline import QUEUE_THRESHOLD
from .scorer import score as score_job
from .store import connect, record_run, upsert

# Posts are found by where they *start*, not by blank lines. Splitting on
# blank lines shattered every post into fragments, which detached the apply
# link from the title and left nothing parseable.
POST_START_RE = re.compile(
    r"^(?=.{0,80}?\bis\s+(?:currently\s+)?hiring\b"
    r"|\s*(?:company|position|role|designation|job\s*title)\s*[:\-–])",
    re.IGNORECASE | re.MULTILINE,
)

# Explicit dividers people paste between posts.
DIVIDER_RE = re.compile(r"^\s*[-=_*—]{3,}\s*$", re.MULTILINE)

URL_RE = re.compile(r"https?://[^\s<>\"')]+")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")

# "Capgemini is hiring for Wheels & Tyre Development Engineer at Chennai."
HIRING_RE = re.compile(
    r"(?P<company>[A-Za-z][\w&.\- ]{1,40}?)\s+is\s+(?:currently\s+)?hiring"
    r"(?:\s+for)?\s*(?P<title>[^.\n]*)",
    re.IGNORECASE,
)

FIELD_RES = {
    "title": re.compile(r"^\s*(?:position|role|designation|job\s*title)\s*[:\-–]\s*(.+)$", re.I | re.M),
    "company": re.compile(r"^\s*(?:company|organisation|organization)\s*[:\-–]\s*(.+)$", re.I | re.M),
    "location": re.compile(r"^\s*(?:location|based in|work location)\s*[:\-–]\s*(.+)$", re.I | re.M),
}

# WhatsApp decorates almost every line with an emoji; strip them so the
# scorer sees plain words.
EMOJI_RE = re.compile(
    "[\U0001F000-\U0001FAFF☀-➿️•··]", flags=re.UNICODE
)


def _clean(text: str) -> str:
    return EMOJI_RE.sub(" ", text).replace("​", "").strip()


def _first(pattern: re.Pattern[str], text: str) -> str:
    match = pattern.search(text)
    return _clean(match.group(1)) if match else ""


def split_posts(text: str) -> list[str]:
    """Slice a pasted dump into one string per job post."""
    # Dividers are unambiguous when present, so honour them first.
    chunks = [c for c in DIVIDER_RE.split(text) if c.strip()]

    blocks: list[str] = []
    for chunk in chunks:
        starts = [m.start() for m in POST_START_RE.finditer(chunk)]
        if not starts:
            blocks.append(chunk)
            continue
        # Anything before the first anchor is channel chatter, not a post.
        bounds = starts + [len(chunk)]
        pieces = [chunk[bounds[i]:bounds[i + 1]] for i in range(len(starts))]

        # "Cisco is hiring" on its own line is a headline, not a post: the
        # next anchor ("Position:") immediately follows. Merge short leading
        # fragments forward, or the company name is lost and the post falls
        # back to being credited to the channel.
        merged: list[str] = []
        carry = ""
        for piece in pieces:
            if len(piece.strip()) < 60:
                carry += piece
                continue
            merged.append(carry + piece)
            carry = ""
        if carry.strip():
            merged.append(carry)

        blocks.extend(merged)
    return blocks


def parse_block(block: str, channel: str) -> Job | None:
    """Turn one pasted post into a Job, or None if it is not a job post."""
    text = _clean(block)
    if len(text) < 40:
        return None

    title = _first(FIELD_RES["title"], text)
    company = _first(FIELD_RES["company"], text)
    location = _first(FIELD_RES["location"], text)

    hiring = HIRING_RE.search(text)
    if hiring:
        company = company or _clean(hiring.group("company"))
        if not title:
            headline = _clean(hiring.group("title"))
            # "... Engineer at Chennai" — split the location back off.
            at_split = re.split(r"\s+(?:at|in)\s+", headline, maxsplit=1)
            title = at_split[0].strip()
            if not location and len(at_split) > 1:
                location = at_split[1].strip()

    if not title:
        return None

    urls = URL_RE.findall(text)
    # Skip channel-invite links, which every WhatsApp post ends with.
    apply_urls = [u for u in urls if "whatsapp.com/channel" not in u]
    emails = EMAIL_RE.findall(text)

    url = apply_urls[0] if apply_urls else (f"mailto:{emails[0]}" if emails else "")
    if not url:
        return None

    return Job(
        source=f"pasted:{channel}",
        title=title[:140],
        company=(company or channel)[:80],
        url=url,
        location=location,
        description=text[:4000],
        remote="remote" in text.lower() or "work from home" in text.lower(),
    )


def parse(text: str, channel: str) -> list[Job]:
    jobs = []
    for block in split_posts(text):
        job = parse_block(block, channel)
        if job:
            jobs.append(job)
    return jobs


def ingest(text: str, channel: str = "whatsapp", threshold: int = QUEUE_THRESHOLD) -> dict:
    """Parse, score and store pasted posts. Returns a small summary."""
    profile = load_profile()
    jobs = parse(text, channel)

    summary: dict = {"parsed": len(jobs), "new": 0, "queued": 0, "gated": 0, "detail": []}

    with connect() as conn:
        for job in jobs:
            verdict = score_job(job, profile)
            scored = ScoredJob(job=job, verdict=verdict)

            is_new = upsert(conn, scored, threshold)
            if is_new:
                summary["new"] += 1
                if not verdict.passed_gates:
                    summary["gated"] += 1
                elif verdict.score >= threshold:
                    summary["queued"] += 1

            summary["detail"].append(
                {
                    "title": job.title,
                    "company": job.company,
                    "score": verdict.score,
                    "rejected_by": verdict.rejected_by,
                    "seen_before": not is_new,
                    "url": job.url,
                }
            )

        record_run(conn, fetched=len(jobs), new_jobs=summary["new"],
                   queued=summary["queued"], rejected=summary["gated"])

    return summary


def ingest_path(path: Path, channel: str = "whatsapp", threshold: int = QUEUE_THRESHOLD) -> dict:
    return ingest(path.read_text(encoding="utf-8"), channel=channel, threshold=threshold)
