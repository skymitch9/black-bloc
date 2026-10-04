"""Each reminder a marathon run or a host block got: where it stands and what it says, so a
move edits it in place."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from . import marathon as mt

COLUMN = "reminder_posts"
HOST_FIELD = "reminders"
STAFF = "staff"
PUBLIC = "public"
COPIES = (PUBLIC, STAFF)
POSTED = "posted"
EDIT = "edit"
REPOST = "repost"
MODES = (EDIT, REPOST)

GONE_CHANNEL = "channel_gone"
GONE_MESSAGE = "message_gone"
GONE_PERMISSION = "no_permission"


def _copy(one: Any) -> dict[str, Any] | None:
    if not isinstance(one, dict) or not one.get("message_id") or not one.get("channel_id"):
        return None
    return {
        "channel_id": int(one["channel_id"]),
        "message_id": int(one["message_id"]),
        "text": str(one.get("text") or ""),
        "head": str(one.get("head") or ""),
        "at": one.get("at"),
    }


def _entry(one: Any) -> dict[str, Any]:
    one = one if isinstance(one, dict) else {}
    kept: dict[str, Any] = {POSTED: bool(one.get(POSTED))}
    for name in COPIES:
        copy = _copy(one.get(name))
        if copy is not None:
            kept[name] = copy
    return kept


def posts_of(raw: Any) -> dict[int, dict[str, Any]]:
    """mark → what was posted for it, from a run's column or a host record's field."""
    if isinstance(raw, str):
        try:
            raw = json.loads(raw or "{}")
        except (TypeError, ValueError):
            return {}
    if not isinstance(raw, dict):
        return {}
    found: dict[int, dict[str, Any]] = {}
    for mark, one in raw.items():
        try:
            found[int(mark)] = _entry(one)
        except (TypeError, ValueError):
            continue
    return found


def of_run(row: Any) -> dict[int, dict[str, Any]]:
    return posts_of(mt._cell(row, COLUMN))


def dump(found: dict[int, dict[str, Any]]) -> str:
    return json.dumps({str(mark): found[mark] for mark in sorted(found)}, sort_keys=True)


def copy_of(message: Any, channel_id: Any, text: str, at: Any) -> dict[str, Any] | None:
    """What one sent message is remembered as; `head` is whatever stood before the words (a
    role mention, a rehearsal note), kept so an edit leaves it as it was."""
    if message is None or not channel_id or not getattr(message, "id", None):
        return None
    body = str(getattr(message, "content", None) or "")
    head = body[: len(body) - len(text)] if text and body.endswith(text) else ""
    return {
        "channel_id": int(channel_id),
        "message_id": int(message.id),
        "text": text,
        "head": head,
        "at": at,
    }


def entry_of(**copies: Any) -> dict[str, Any]:
    kept = {name: copy for name, copy in copies.items() if name in COPIES and copy}
    return {POSTED: bool(kept)} | kept


def with_skipped(found: dict[int, dict[str, Any]], marks: Any) -> dict[int, dict[str, Any]]:
    return dict(found) | {int(mark): {POSTED: False} for mark in marks or ()}


def held(found: dict[int, dict[str, Any]], sent: Any) -> set[int]:
    """The sent marks a move never fires again: the ones that posted, and the ones sent before
    posts were remembered (no entry at all), which cannot be told from posted."""
    return {
        int(mark)
        for mark in sent or ()
        if int(mark) not in found or found[int(mark)].get(POSTED)
    }


def rearmed(
    sent: Any, found: dict[int, dict[str, Any]], new_start: Any, now: datetime, mode: str
) -> tuple[list[int], dict[int, dict[str, Any]]]:
    """`repost` forgets every mark whose moment is ahead again; `edit` keeps the ones that
    posted, so only a skipped or failed mark fires at its new moment."""
    was = sorted({int(one) for one in sent or ()})
    kept = set(mt.rearmed(was, new_start, now))
    if mode != REPOST:
        kept |= held(found, was)
    return (sorted(kept), {mark: one for mark, one in found.items() if mark in kept})


def run_fields(row: Any, new_start: Any, now: datetime, mode: str) -> dict[str, str]:
    marks, found = rearmed(mt.marks_of(row), of_run(row), new_start, now, mode)
    return {"reminders_sent": json.dumps(marks), COLUMN: dump(found)}


def standing(found: dict[int, dict[str, Any]]) -> list[tuple[int, str, dict[str, Any]]]:
    """Every copy that can still be edited: the nearest mark first, the public copy first."""
    return [
        (mark, name, found[mark][name])
        for mark in sorted(found)
        for name in COPIES
        if name in found[mark]
    ]


def body(copy: dict[str, Any], text: str) -> str:
    return f"{copy.get('head') or ''}{text}"[: mt.MESSAGE_LIMIT]


def shown(found: dict[int, dict[str, Any]], mark: int, name: str, text: str, at: Any) -> None:
    found[mark][name] = found[mark][name] | {"text": text, "at": at}


def forget(found: dict[int, dict[str, Any]], mark: int, name: str) -> None:
    """The message is gone: the id is dropped, the mark stays posted and is never sent again."""
    found[mark].pop(name, None)
    found[mark][POSTED] = True


class Budget:
    """How many edits one pass may still make."""

    def __init__(self, limit: Any) -> None:
        self.left = max(0, int(limit))
        self.waiting = 0

    def take(self) -> bool:
        if self.left <= 0:
            self.waiting += 1
            return False
        self.left -= 1
        return True


__all__ = [
    "COLUMN",
    "COPIES",
    "EDIT",
    "GONE_CHANNEL",
    "GONE_MESSAGE",
    "GONE_PERMISSION",
    "HOST_FIELD",
    "MODES",
    "POSTED",
    "PUBLIC",
    "REPOST",
    "STAFF",
    "Budget",
    "body",
    "copy_of",
    "dump",
    "entry_of",
    "forget",
    "held",
    "of_run",
    "posts_of",
    "rearmed",
    "run_fields",
    "shown",
    "standing",
    "with_skipped",
]
