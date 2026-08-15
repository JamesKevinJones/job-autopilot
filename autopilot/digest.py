"""End-of-day summary — written to docs/DAILY/ and optionally emailed."""

from __future__ import annotations

from datetime import date

from .config import DIGEST_DIR
from .store import APPLIED, REJECTED_BY_GATE, QUEUED, connect, runs_today, today_rows


def build(day: str | None = None) -> str:
    """Render the day's activity as markdown."""
    day = day or date.today().isoformat()

    with connect() as conn:
        grouped = today_rows(conn, day)
        runs = runs_today(conn, day)

    fetched = sum(r["fetched"] for r in runs)
    new_jobs = sum(r["new_jobs"] for r in runs)
    errors = [r["errors"] for r in runs if r["errors"]]

    queued = grouped.get(QUEUED, [])
    applied = grouped.get(APPLIED, [])
    gated = grouped.get(REJECTED_BY_GATE, [])

    lines: list[str] = [
        f"# Job Autopilot — {day}",
        "",
        f"- Postings scanned: **{fetched}**",
        f"- New (not seen before): **{new_jobs}**",
        f"- Matches queued for approval: **{len(queued)}**",
        f"- Applications submitted: **{len(applied)}**",
        f"- Filtered out by hard gates: **{len(gated)}**",
        f"- Discovery runs: **{len(runs)}**",
        "",
    ]

    if queued:
        lines += ["## Waiting for your approval", ""]
        for row in queued:
            lines.append(f"### {row['score']}/100 — {row['title']} @ {row['company']}")
            lines.append(f"- {row['location'] or 'location not stated'} · {row['source']}")
            if row["salary"]:
                lines.append(f"- Salary: {row['salary']}")
            if row["reasons_for"]:
                lines.append(f"- **For:** {row['reasons_for']}")
            if row["reasons_against"]:
                lines.append(f"- **Against:** {row['reasons_against']}")
            lines.append(f"- {row['url']}")
            lines.append("")
    else:
        lines += ["## Waiting for your approval", "", "Nothing cleared the threshold today.", ""]

    if applied:
        lines += ["## Submitted today", ""]
        lines += [f"- {r['title']} @ {r['company']} — {r['url']}" for r in applied]
        lines.append("")

    if gated:
        counts: dict[str, int] = {}
        for row in gated:
            counts[row["rejected_by"]] = counts.get(row["rejected_by"], 0) + 1
        lines += ["## Why things were filtered out", ""]
        lines += [f"- {reason}: {n}" for reason, n in sorted(counts.items(), key=lambda kv: -kv[1])]
        lines.append("")

    if errors:
        lines += ["## Problems", ""]
        lines += [f"- {e}" for e in errors]
        lines.append("")

    lines += ["---", "", "Approve with: `python -m autopilot approve <fingerprint>`"]
    return "\n".join(lines)


def write(day: str | None = None, deliver: bool = False) -> str:
    """Write the digest to docs/DAILY/<date>.md and return the path.

    With deliver=True, also fires the Windows toast and emails it if Gmail
    has been authorised.
    """
    day = day or date.today().isoformat()
    DIGEST_DIR.mkdir(parents=True, exist_ok=True)
    path = DIGEST_DIR / f"{day}.md"
    body = build(day)
    path.write_text(body, encoding="utf-8")

    if deliver:
        from .notify import deliver as deliver_digest

        queued = body.count("### ")
        summary = f"{queued} role(s) queued for approval"
        for line in deliver_digest(str(path), summary, body, f"Job Autopilot — {day}"):
            print(f"  {line}")

    return str(path)
