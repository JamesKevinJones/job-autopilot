"""Shared source plumbing."""

from __future__ import annotations

import html
import re
from typing import Any, Protocol

import requests

from ..models import Job

USER_AGENT = "job-autopilot/0.1 (personal job search; contact kj6384647@gmail.com)"
TIMEOUT = 30

_TAG_RE = re.compile(r"<[^>]+>")


class Source(Protocol):
    """Anything that can produce jobs."""

    name: str

    def fetch(self, profile: dict[str, Any]) -> list[Job]:
        ...


def get_json(url: str, params: dict[str, Any] | None = None) -> Any:
    response = requests.get(
        url, params=params, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT
    )
    response.raise_for_status()
    return response.json()


def repair_mojibake(text: str) -> str:
    """Undo double-encoded UTF-8.

    RemoteOK declares UTF-8 correctly but serves text that was already
    decoded as latin-1 and re-encoded, so "الرياض" arrives as "Ø§ÙØ±ÙØ§Ø¶".
    Round-tripping back through latin-1 restores it. Strings that are not
    double-encoded fail the round trip and are returned untouched.
    """
    if not text or text.isascii():
        return text
    try:
        return text.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text


def strip_html(text: str, limit: int = 4000) -> str:
    """Sources return HTML descriptions; the scorer only needs the words.

    Greenhouse returns the body HTML-escaped (``&lt;p&gt;Python&lt;/p&gt;``),
    so unescaping has to happen before tag stripping — otherwise nothing is
    removed, the tags stay in the text as entities, and skill matching sees
    no stack keywords at all.
    """
    return _TAG_RE.sub(" ", html.unescape(text or ""))[:limit]
