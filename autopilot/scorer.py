"""Fit scoring.

Two stages, deliberately separate:

1. Hard gates — disqualifying facts. A job that fails one is never queued,
   regardless of how well it scores otherwise.
2. Weighted score — 0-100, only computed for jobs that clear the gates.

Rejections are stored, not discarded, so the thresholds can be recalibrated
against real data instead of guesswork.
"""

from __future__ import annotations

import re
from typing import Any

from .config import flat_skills
from .models import Job, Verdict

# Titles that mean the role is above entry level.
SENIOR_MARKERS = (
    "senior", "sr.", "staff", "principal", "lead", "architect",
    "manager", "head of", "director", "vp ", "chief",
)

# Junior signals, which actively help. Matched as whole words: plain
# substring matching counted "SDE III" and "SDE IV" as entry level because
# "sde i" is a prefix of both.
JUNIOR_MARKERS_RE = re.compile(
    r"\b(intern|internship|junior|jr\.?|graduate|trainee|entry[- ]level|"
    r"fresher|campus|new\s+grad|sde\s*[-]?\s*(?:i|1)\b|associate)\b",
    re.IGNORECASE,
)

# An explicit fresher declaration anywhere in the post counts as an
# entry-level signal, not just the title. Channel posts are terse: "Position:
# Software Engineer / Experience: Freshers" carries the signal on its own
# line, and title-only matching scored it as if seniority were unstated.
FRESHER_DECLARATION_RE = re.compile(
    r"(?:experience|exp)\s*[:\-–]?\s*"
    r"(?:freshers?|0\s*(?:-|to)?\s*1?\s*(?:years?|yrs?)?|nil|none|no\s+prior)",
    re.IGNORECASE,
)

# Explicitly-levelled senior variants that the seniority gate should catch.
LEVELLED_SENIOR_RE = re.compile(
    r"\b(?:sde|engineer|developer|swe)\s*[-]?\s*(?:ii|iii|iv|v|2|3|4|5)\b",
    re.IGNORECASE,
)

# Postings that ask the candidate for money are scams.
FEE_MARKERS = (
    "registration fee", "training fee", "security deposit",
    "pay to apply", "franchise fee", "course fee",
)

# Only count "N years" when 'experience' appears close by. Without the
# proximity requirement this matched things like "40 hours" and "founded 30
# years ago", producing nonsense gates such as requires-40y-experience.
YEARS_RE = re.compile(
    r"(\d{1,2})\s*\+?\s*(?:-\s*\d{1,2}\s*)?\s*(?:\+\s*)?years?[^.]{0,40}?experience",
    re.IGNORECASE,
)

# The reverse phrasing, which job posts shared on WhatsApp and Telegram use
# constantly: "Experience: 5+ Years", "Exp - 3 to 6 yrs". Without this the
# fresher gate missed them entirely and a 5-year role scored as a match.
YEARS_REVERSED_RE = re.compile(
    r"exp(?:erience)?\s*[:\-–]?\s*(\d{1,2})\s*\+?\s*(?:(?:-|to)\s*\d{1,2}\s*)?\s*(?:years?|yrs?)",
    re.IGNORECASE,
)

# Fresher-only: any posting asking for two or more years is out. One year is
# tolerated because postings often write "0-1 years" or "up to 1 year".
MAX_YEARS_EXPERIENCE = 1

# Mid-level phrasing that is not caught by the senior title list but still
# rules out a fresher.
EXPERIENCED_MARKERS = (
    "mid-level", "mid level", "midlevel", "experienced ", "seasoned",
    "proven track record", "years of professional", "minimum of 2 years",
    "at least 2 years", "at least 3 years", "2+ years", "3+ years",
)

# A title must contain one of these to be a software role at all. Without
# this gate, non-technical remote listings (Handyman, Merchandising Associate,
# Sales Development Representative) leak through on incidental keyword hits.
TECH_ANCHORS = (
    "engineer", "developer", "programmer", "sde", "software", "full stack",
    "fullstack", "full-stack", "backend", "back-end", "frontend", "front-end",
    "web dev", "devops", "data scientist", "machine learning", "blockchain",
    "web3", "qa ", "sre", "technical", "architect", "analyst programmer",
    "development engineer", "computer science",
)

# Skill tags too short or too common to match on their own. Each of these
# produced false positives: "move" inside "remove", "rag" inside "storage",
# "java" inside "javascript".
AMBIGUOUS_SKILLS = {"move", "rag", "java", "css", "html", "sql", "c++", "git", "vite", "bm25"}


def _required_years(text: str) -> int | None:
    """Largest years-of-experience figure mentioned, in either phrasing."""
    matches = [int(m) for m in YEARS_RE.findall(text)]
    matches += [int(m) for m in YEARS_REVERSED_RE.findall(text)]
    return max(matches) if matches else None


def _skill_hits(text: str, skills: set[str]) -> list[str]:
    """Word-boundary skill matching, skipping tags that are too ambiguous.

    Substring matching was scoring a Handyman listing 29/100.
    """
    hits: list[str] = []
    for skill in skills:
        if skill in AMBIGUOUS_SKILLS:
            continue
        pattern = r"(?<![a-z0-9])" + re.escape(skill) + r"(?![a-z0-9])"
        if re.search(pattern, text):
            hits.append(skill)
    return sorted(hits)


# Onsite is acceptable in Chennai (home) and Bangalore (relocation). Remote of
# any origin still qualifies. Bangalore matters because the Greenhouse and
# Lever boards that supply Indian roles hire almost entirely there.
HOME_LOCATIONS = ("chennai", "tamil nadu", "madras")
RELOCATION_LOCATIONS = ("bangalore", "bengaluru", "karnataka")
ONSITE_LOCATIONS = HOME_LOCATIONS + RELOCATION_LOCATIONS


def _location_ok(job: Job, profile: dict[str, Any]) -> bool:
    """True if the job is remote, or onsite within commuting distance."""
    if job.remote:
        return True
    blob = f"{job.location} {job.title}".lower()
    if "remote" in blob or "anywhere" in blob or "work from home" in blob:
        return True
    return any(place in blob for place in ONSITE_LOCATIONS)


def apply_gates(job: Job, profile: dict[str, Any]) -> str:
    """Return the name of the failed gate, or '' if the job passes."""
    title = job.title.lower()
    text = job.haystack

    if not any(anchor in title for anchor in TECH_ANCHORS):
        return "not-a-tech-role"

    if any(marker in title for marker in SENIOR_MARKERS):
        return "senior-title"

    if LEVELLED_SENIOR_RE.search(title):
        return "senior-level-title"

    if any(marker in text for marker in EXPERIENCED_MARKERS):
        return "wants-experienced-hire"

    blacklist = [c.lower() for c in profile["targets"].get("blacklist_companies", [])]
    if job.company.lower() in blacklist:
        return "blacklisted-company"

    if any(marker in text for marker in FEE_MARKERS):
        return "asks-for-money"

    years = _required_years(text)
    if years is not None and years > MAX_YEARS_EXPERIENCE:
        return f"requires-{years}y-experience"

    if not _location_ok(job, profile):
        return "location-mismatch"

    return ""


def score(job: Job, profile: dict[str, Any]) -> Verdict:
    """Score a job 0-100 with human-readable reasoning."""
    rejected_by = apply_gates(job, profile)
    if rejected_by:
        return Verdict(score=0, rejected_by=rejected_by)

    title = job.title.lower()
    text = job.haystack
    reasons_for: list[str] = []
    reasons_against: list[str] = []
    total = 0

    # --- Title match against target roles (max 35) ---
    # Scored on whole target phrases, not individual words: matching loose
    # words let "Business Development Representative" hit on "development".
    targets = [t.lower() for t in profile["targets"]["role_titles"]]
    best_overlap = 0.0
    best_words: set[str] = set()
    for target in targets:
        words = {w for w in re.findall(r"[a-z]+", target) if len(w) > 2}
        if not words:
            continue
        hit = {w for w in words if w in title}
        overlap = len(hit) / len(words)
        # Prefer the target with the most words actually matched; a 50% hit on
        # a two-word target ("web3 developer") is weaker evidence than a 67%
        # hit on a three-word one, and naming it misleads.
        if (len(hit), overlap) > (len(best_words), best_overlap):
            best_overlap, best_words = overlap, hit

    # Half the words of a target title must appear before it counts.
    if best_overlap >= 0.5:
        title_points = int(35 * best_overlap)
        total += title_points
        reasons_for.append(f"title matches target terms: {', '.join(sorted(best_words))}")
    else:
        reasons_against.append("title does not match any target role")

    # --- Stack overlap (max 35) ---
    skills = flat_skills(profile)
    matched = _skill_hits(text, skills)
    stack_points = min(35, len(matched) * 7)
    if stack_points:
        total += stack_points
        reasons_for.append(f"stack overlap: {', '.join(matched[:6])}")
    else:
        reasons_against.append("no overlap with your stack")

    # --- Seniority fit (max 15) ---
    if JUNIOR_MARKERS_RE.search(title):
        total += 15
        reasons_for.append("explicitly entry level")
    elif FRESHER_DECLARATION_RE.search(text):
        total += 15
        reasons_for.append("post states freshers welcome")
    else:
        reasons_against.append("seniority not stated as entry level")

    # --- Location preference (max 15) ---
    if job.remote or "remote" in text:
        total += 15
        reasons_for.append("remote")
    elif any(c in text for c in HOME_LOCATIONS):
        total += 15
        reasons_for.append("Chennai — no relocation needed")
    elif any(c in text for c in RELOCATION_LOCATIONS):
        total += 11
        reasons_for.append("Bangalore — relocation required")

    return Verdict(score=min(100, total), reasons_for=reasons_for, reasons_against=reasons_against)
