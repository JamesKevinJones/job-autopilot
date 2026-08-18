"""Command line entry point.

    python -m autopilot run       # discover, score, queue
    python -m autopilot queue     # show what is waiting for approval
    python -m autopilot digest    # write today's summary
    python -m autopilot approve <fingerprint>
    python -m autopilot skip <fingerprint>
    python -m autopilot daily     # run + digest, for the scheduled task
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import digest, ingest as ingest_mod, pipeline
from .store import APPLIED, SKIPPED, connect, queue, set_status


def cmd_run(_: argparse.Namespace) -> int:
    result = pipeline.run()
    print(
        f"fetched={result.fetched} new={result.new_jobs} "
        f"queued={result.queued} gated={result.rejected}"
    )
    for error in result.errors:
        print(f"  error: {error}", file=sys.stderr)
    return 0


def cmd_queue(args: argparse.Namespace) -> int:
    with connect() as conn:
        rows = queue(conn, limit=args.limit)
    if not rows:
        print("Queue is empty.")
        return 0
    for row in rows:
        print(f"[{row['score']:>3}] {row['fingerprint']}  {row['title']} @ {row['company']}")
        print(f"      {row['location']} · {row['source']} · {row['url']}")
        if row["reasons_for"]:
            print(f"      for: {row['reasons_for']}")
    return 0


def cmd_digest(_: argparse.Namespace) -> int:
    print(digest.write())
    return 0


def cmd_status(args: argparse.Namespace, status: str) -> int:
    with connect() as conn:
        set_status(conn, args.fingerprint, status)
    print(f"{args.fingerprint} -> {status}")
    return 0


def cmd_ingest(args: argparse.Namespace) -> int:
    """Score job posts pasted from a channel that has no API."""
    if args.file:
        text = Path(args.file).read_text(encoding="utf-8")
    else:
        print("Paste the posts, then press Ctrl+Z and Enter (Windows):")
        text = sys.stdin.read()

    result = ingest_mod.ingest(text, channel=args.channel)

    print(
        f"parsed={result['parsed']} new={result['new']} "
        f"queued={result['queued']} gated={result['gated']}"
    )
    for row in result["detail"]:
        if row["seen_before"]:
            mark = "seen"
        elif row["rejected_by"]:
            mark = row["rejected_by"]
        else:
            mark = f"{row['score']}/100"
        print(f"  [{mark:>24}] {row['title'][:48]} @ {row['company'][:22]}")
        print(f"  {'':>26} {row['url'][:90]}")
    return 0


def cmd_daily(_: argparse.Namespace) -> int:
    cmd_run(_)
    print(digest.write(deliver=True))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="autopilot", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("run", help="discover and score jobs").set_defaults(func=cmd_run)

    p_queue = sub.add_parser("queue", help="show jobs awaiting approval")
    p_queue.add_argument("--limit", type=int, default=20)
    p_queue.set_defaults(func=cmd_queue)

    p_ingest = sub.add_parser(
        "ingest", help="score job posts pasted from WhatsApp/Telegram/email"
    )
    p_ingest.add_argument("--file", help="read from a file instead of stdin")
    p_ingest.add_argument("--channel", default="whatsapp", help="where it came from")
    p_ingest.set_defaults(func=cmd_ingest)

    sub.add_parser("digest", help="write today's summary").set_defaults(func=cmd_digest)
    sub.add_parser("daily", help="run + digest (for the scheduler)").set_defaults(func=cmd_daily)

    p_approve = sub.add_parser("approve", help="mark a job as applied")
    p_approve.add_argument("fingerprint")
    p_approve.set_defaults(func=lambda a: cmd_status(a, APPLIED))

    p_skip = sub.add_parser("skip", help="dismiss a job")
    p_skip.add_argument("fingerprint")
    p_skip.set_defaults(func=lambda a: cmd_status(a, SKIPPED))

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
