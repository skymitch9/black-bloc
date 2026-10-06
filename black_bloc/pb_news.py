"""Which fetched personal bests are news, given what is already stored. No I/O."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from .speedrun import VERIFIED, PersonalBest

BASELINE = "baseline"
SAME_RUN = "same_run"
NOT_FASTER = "not_faster"
UNDATED = "undated"
BEFORE_BASELINE = "before_baseline"
TOO_OLD = "too_old"
OVER_THE_CAP = "over_the_cap"


@dataclass(frozen=True)
class Quiet:
    best: PersonalBest
    why: str


@dataclass(frozen=True)
class Verdict:
    news: tuple[PersonalBest, ...] = ()
    quiet: tuple[Quiet, ...] = ()
    held: tuple[PersonalBest, ...] = ()
    unverified: int = 0
    counts: dict[str, int] = field(default_factory=dict)


def verified(fetched: Any) -> list[PersonalBest]:
    return [best for best in fetched or () if best.status == VERIFIED]


def stored_seconds(row: Any) -> float | None:
    try:
        return float(row["seconds"])
    except (KeyError, TypeError, ValueError):
        return None


def why_quiet(
    best: PersonalBest,
    baseline: dict[str, Any],
    seen_runs: set[str],
    since: datetime,
    now: datetime,
    max_age: timedelta,
) -> str | None:
    """The reason a verified run is not news, or None when it is."""
    if best.run_id in seen_runs:
        return SAME_RUN
    held = baseline.get(best.slot)
    before = stored_seconds(held) if held is not None else None
    if before is not None and best.seconds >= before:
        return NOT_FASTER
    if best.verified_at is None:
        return UNDATED
    if best.verified_at < since:
        return BEFORE_BASELINE
    if now - best.verified_at > max_age:
        return TOO_OLD
    return None


def news(
    baseline: dict[str, Any],
    fetched: Any,
    *,
    since: datetime | None,
    now: datetime,
    max_age_days: int,
    max_posts: int,
) -> Verdict:
    """`since` is when the baseline was taken; None means this is the first sight, all quiet."""
    looked = verified(fetched)
    unverified = len(list(fetched or ())) - len(looked)
    if since is None:
        return Verdict(
            quiet=tuple(Quiet(best, BASELINE) for best in looked),
            unverified=unverified,
            counts={BASELINE: len(looked)},
        )
    seen_runs = {str(row["run_id"]) for row in baseline.values()}
    max_age = timedelta(days=max(1, int(max_age_days)))
    found: list[PersonalBest] = []
    quiet: list[Quiet] = []
    counts: dict[str, int] = {}
    for best in looked:
        why = why_quiet(best, baseline, seen_runs, since, now, max_age)
        if why is None:
            found.append(best)
            continue
        quiet.append(Quiet(best, why))
        counts[why] = counts.get(why, 0) + 1
    found.sort(key=lambda best: best.verified_at or now)
    cap = max(1, int(max_posts))
    held = tuple(found[cap:])
    if held:
        counts[OVER_THE_CAP] = len(held)
    return Verdict(tuple(found[:cap]), tuple(quiet), held, unverified, counts)


__all__ = [
    "BASELINE",
    "BEFORE_BASELINE",
    "NOT_FASTER",
    "OVER_THE_CAP",
    "SAME_RUN",
    "TOO_OLD",
    "UNDATED",
    "Quiet",
    "Verdict",
    "news",
    "verified",
    "why_quiet",
]
