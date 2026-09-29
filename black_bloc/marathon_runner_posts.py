"""One post per BaF run in a tracked marathon's thread: its words, its order, its pin's end."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from . import marathon as mt
from .golive import parse_ts

POSTABLE = (mt.UPCOMING, mt.LIVE, mt.DONE)
UNPIN_STATES = (mt.DONE, mt.DROPPED)
PIN_CAP_CODE = 30003
PIN_REASON = "Black Bloc: a BaF run on the marathon"
UNPIN_REASON = "Black Bloc: that BaF run is over"
BECAUSE_OVER = "run_over"
BECAUSE_UNLISTED = "unlisted"
BECAUSE_MARATHON_OVER = "over"


def post_id(row: Any) -> int | None:
    found = mt._cell(row, "post_message_id")
    return int(found) if found else None


def post_channel(row: Any) -> int | None:
    found = mt._cell(row, "post_channel_id")
    return int(found) if found else None


def is_pinned(row: Any) -> bool:
    return bool(mt._cell(row, "post_pinned"))


def wanted(rows: Any) -> list[Any]:
    """Runs that get a post, in schedule order: every run already posted, and every BaF run the
    board lists except one that was dropped before it was ever posted."""
    return sorted(
        (
            one
            for one in rows or ()
            if post_id(one) or (mt.is_ours(one) and mt._cell(one, "state") in POSTABLE)
        ),
        key=mt._when,
    )


def names_of(row: Any, people: Any = None) -> str:
    people = mt.ours(mt.people_of(row)) if people is None else list(people)
    if people:
        return ", ".join(str(one.get("name") or "") for one in people)
    return str(mt._cell(row, "runners_text") or "")


def fields_of(
    row: Any, marathon: Any, words: dict[str, str], *, url: str, unlisted: str, people: Any = None
) -> dict[str, Any]:
    base = mt.run_fields(row, marathon, words, url=url, people=people)
    ours = people is not None or mt.is_ours(row)
    return {
        "runner": names_of(row, people),
        "mention": base["member"],
        "game": base["game"],
        "category": base["category"],
        "part": base["part"],
        "when": base["when"],
        "relative": base["relative"],
        "url": url,
        "marathon": base["marathon"],
        "state": base["state"] if ours else unlisted,
    }


def post_text(
    row: Any,
    marathon: Any,
    words: dict[str, str],
    *,
    template: Any,
    default: str,
    url: str,
    unlisted: str,
    people: Any = None,
) -> mt.Rendered:
    found = mt.render(
        template,
        default,
        **fields_of(row, marathon, words, url=url, unlisted=unlisted, people=people),
    )
    return mt.Rendered(found.text[: mt.MESSAGE_LIMIT], found.fell_back)


def over_at(row: Any) -> datetime | None:
    state = mt._cell(row, "state")
    if state == mt.DONE:
        return (
            parse_ts(mt._cell(row, "ends_at"))
            or parse_ts(mt._cell(row, "done_at"))
            or parse_ts(mt._cell(row, "scheduled_at"))
        )
    if state == mt.DROPPED:
        return parse_ts(mt._cell(row, "last_seen_at")) or parse_ts(mt._cell(row, "scheduled_at"))
    return None


def unpin_because(row: Any, now: datetime) -> str | None:
    """The board's rule, per run: the pin comes off a day after the run is over or dropped;
    a run no longer counted as BaF comes off at once."""
    if not is_pinned(row):
        return None
    if not mt.is_ours(row):
        return BECAUSE_UNLISTED
    if mt._cell(row, "state") not in UNPIN_STATES:
        return None
    ended = over_at(row)
    if ended is None or now > ended + mt.AFTER_END:
        return BECAUSE_OVER
    return None


def pins_now(row: Any, now: datetime) -> bool:
    """A post made for a run whose pin would already be due off is not pinned at all."""
    return unpin_because({**dict(row), "post_pinned": 1}, now) is None


def is_pin_cap(exc: BaseException) -> bool:
    return getattr(exc, "code", None) == PIN_CAP_CODE
