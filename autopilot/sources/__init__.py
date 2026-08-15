"""Job discovery sources.

Only sources with a public API and a free apply path live here.

**RemoteOK is deliberately excluded.** Its listings are readable for free, but
applying is gated behind a $29.95/year subscription, so every match it
produced was a dead end.

LinkedIn, Naukri, Internshala and Wellfound are also absent: they forbid
automated scraping and will restrict the account. Those are handled by the
browser-assisted flow described in AGENTS.md, where Kevin is already signed
in and approves each submission.

Greenhouse and Lever are the important ones for Indian roles — you apply on
the company's own careers page, which is free and is where applications
actually get read.
"""

from .base import Source
from .free_boards import Arbeitnow, Himalayas, Jobicy
from .greenhouse import Greenhouse, Lever
from .remotive import Remotive

ALL_SOURCES: list[Source] = [
    Greenhouse(),   # Indian product companies, free apply
    Lever(),        # Indian product companies, free apply
    Arbeitnow(),
    Jobicy(),
    Himalayas(),
    Remotive(),
]

__all__ = [
    "Source", "Arbeitnow", "Jobicy", "Himalayas",
    "Greenhouse", "Lever", "Remotive", "ALL_SOURCES",
]
