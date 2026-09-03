from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from .events import clamp
from .golive import parse_ts, ping_prefix
from .timezones import unix

log = logging.getLogger(__name__)

TITLE_LIMIT = 100
DESCRIPTION_LIMIT = 500
SLOT_MINUTES_MIN = 15
SLOT_MINUTES_MAX = 12 * 60
SLOT_COUNT_MIN = 1
SLOT_COUNT_MAX = 24
CHECKIN_EARLY_MINUTES = 15
REMINDER_LATE_MINUTES = 15
TWITCH_URL = "https://twitch.tv/{login}"

OPEN = "open"
LOCKED = "locked"
LIVE = "live"
DONE = "done"
CANCELLED = "cancelled"
STATUSES = (OPEN, LOCKED, LIVE, DONE, CANCELLED)
OPEN_STATUSES = (OPEN, LOCKED, LIVE)

TRANSITIONS: dict[str, tuple[str, ...]] = {
    OPEN: (LOCKED, LIVE, CANCELLED),
    LOCKED: (OPEN, LIVE, CANCELLED),
    LIVE: (DONE,),
    DONE: (),
    CANCELLED: (),
}

TERMINAL_STATUSES = tuple(status for status, moves in TRANSITIONS.items() if not moves)

STATUS_WORDS: dict[str, str] = {
    OPEN: "open for sign-ups",
    LOCKED: "locked — the lineup is set",
    LIVE: "running now",
    DONE: "finished",
    CANCELLED: "cancelled",
}

NOWHERE_TO_MOVE = "**{status}** is the end of the line for a raid train, so nothing was changed."
CANNOT_MOVE = (
    "A raid train that is **{status}** cannot be marked **{to}**, so nothing was changed. From "
    "here it can only become {allowed}."
)
NEEDS_LINK = (
    "Black Bloc needs to know your Twitch channel before you can take a slot, because the "
    "streamer before you raids the name on the lineup. Run `/twitch link <your channel name>` "
    "and claim the slot again — nothing was taken in the meantime."
)
SLOT_TAKEN = (
    "Slot **#{position}** already belongs to someone else, so nothing was changed. "
    "`/raidtrain status` shows which slots are still open."
)
SLOT_UNKNOWN = (
    "This train has no slot **#{position}**, so nothing was changed. It runs from #1 to "
    "#{last} — `/raidtrain status` lists them."
)
TRAIN_FULL = "Every slot on **{title}** is taken, so there was nothing to claim."
CAP_REACHED = (
    "You already hold {held} slot(s) on **{title}**, which is as many as this server allows one "
    "person. Release one with `/raidtrain release` if you would rather take a different hour, or "
    "ask an organizer to assign you another."
)
TRAIN_LOCKED = (
    "**{title}** is locked, so its lineup cannot be changed. An organizer unlocks it with "
    "`/raidtrain unlock`, and a train locks itself when it starts."
)
NOT_YOURS = (
    "Slot **#{position}** is not yours, so nothing was released. `/raidtrain mine` lists the "
    "slots you hold."
)


def _value(row: Any, key: str, fallback: Any = None) -> Any:
    """One reader for a sqlite Row, a dict or an object, so the helpers stay testable."""
    if row is None:
        return fallback
    if isinstance(row, dict):
        return row.get(key, fallback)
    try:
        return row[key]
    except (IndexError, KeyError, TypeError):
        return getattr(row, key, fallback)


def slot_times(
    starts_at: datetime, slot_minutes: int, slot_count: int
) -> list[tuple[datetime, datetime]]:
    """Consecutive slots from the start, so a swap never has to rewrite a time."""
    length = timedelta(minutes=int(slot_minutes))
    return [
        (starts_at + length * index, starts_at + length * (index + 1))
        for index in range(int(slot_count))
    ]


def ends_at(train: Any, slots: Any = None) -> datetime | None:
    """When the last slot finishes; the row's own times win over the arithmetic."""
    latest = None
    for slot in slots or ():
        finish = parse_ts(_value(slot, "ends_at"))
        if finish is not None and (latest is None or finish > latest):
            latest = finish
    if latest is not None:
        return latest
    starts = parse_ts(_value(train, "starts_at"))
    if starts is None:
        return None
    minutes = int(_value(train, "slot_minutes") or 0) * int(_value(train, "slot_count") or 0)
    return starts + timedelta(minutes=minutes)


def may_move(status: Any, to: Any) -> bool:
    return str(to) in TRANSITIONS.get(str(status), ())


def allowed_moves(status: Any) -> str:
    """What a refusal is allowed to say next, in words rather than a status list."""
    moves = TRANSITIONS.get(str(status), ())
    if not moves:
        return "nothing"
    if len(moves) == 1:
        return f"**{moves[0]}**"
    return ", ".join(f"**{one}**" for one in moves[:-1]) + f" or **{moves[-1]}**"


def move_refusal(status: Any, to: Any) -> str:
    if not TRANSITIONS.get(str(status), ()):
        return NOWHERE_TO_MOVE.format(status=status)
    return CANNOT_MOVE.format(status=status, to=to, allowed=allowed_moves(status))


def slots_held(slots: Any, user_id: Any) -> list[Any]:
    wanted = int(user_id)
    return [slot for slot in slots or () if _value(slot, "user_id") == wanted]


def caps_ok(slots: Any, user_id: Any, max_per_member: Any) -> bool:
    """0 means no ceiling; anything else counts what this member already holds here."""
    ceiling = int(max_per_member or 0)
    if ceiling <= 0:
        return True
    return len(slots_held(slots, user_id)) < ceiling


def open_positions(slots: Any) -> list[int]:
    return [
        int(_value(slot, "position"))
        for slot in slots or ()
        if _value(slot, "user_id") is None
    ]


def next_open_position(slots: Any) -> int | None:
    found = open_positions(slots)
    return min(found) if found else None


def slot_at(slots: Any, position: Any) -> Any:
    for slot in slots or ():
        if int(_value(slot, "position") or 0) == int(position):
            return slot
    return None


def neighbours(slots: Any, position: Any) -> tuple[Any, Any]:
    """Who raids into this slot and who it raids on to; either may be None."""
    wanted = int(position)
    return (slot_at(slots, wanted - 1), slot_at(slots, wanted + 1))


def filled(slots: Any) -> int:
    return len([slot for slot in slots or () if _value(slot, "user_id") is not None])


def twitch_url(login: Any) -> str:
    return TWITCH_URL.format(login=str(login or "").strip().lstrip("@"))


def _who(slot: Any) -> str:
    user_id = _value(slot, "user_id")
    if user_id is None:
        return "_open_"
    login = str(_value(slot, "twitch_login") or "").strip()
    named = f"<@{int(user_id)}>"
    return f"{named} ({twitch_url(login)})" if login else named


def _slot_line(slot: Any) -> str:
    start = parse_ts(_value(slot, "starts_at"))
    finish = parse_ts(_value(slot, "ends_at"))
    when = (
        f"<t:{unix(start)}:t>–<t:{unix(finish)}:t>"
        if start is not None and finish is not None
        else "time unreadable"
    )
    mark = " ✅" if _value(slot, "checked_in_at") else ""
    return f"`#{int(_value(slot, 'position') or 0):>2}` {when} — {_who(slot)}{mark}"


def render_lineup(train: Any, slots: Any, *, ping_role_id: Any = None) -> str:
    """The lineup post, edited in place on every change rather than posted again."""
    rows = sorted(slots or (), key=lambda one: int(_value(one, "position") or 0))
    starts = parse_ts(_value(train, "starts_at"))
    status = str(_value(train, "status") or OPEN)
    head = f"**{clamp(_value(train, 'title'), TITLE_LIMIT)}** — raid train"
    lines = [ping_prefix(ping_role_id) + head]
    if starts is not None:
        lines.append(f"Starts <t:{unix(starts)}:F> (<t:{unix(starts)}:R>)")
    lines.append(
        f"{filled(rows)}/{len(rows)} slot(s) filled · "
        f"{int(_value(train, 'slot_minutes') or 0)} minutes each · "
        f"{STATUS_WORDS.get(status, status)}"
    )
    description = clamp(_value(train, "description"), DESCRIPTION_LIMIT)
    if description:
        lines.append(description)
    if status == CANCELLED:
        reason = clamp(_value(train, "cancel_reason"), DESCRIPTION_LIMIT)
        lines.append(f"**This train is cancelled.** {reason}".strip())
    lines.append("")
    lines.extend(_slot_line(slot) for slot in rows)
    if status == OPEN:
        lines.append("")
        lines.append("Take an hour with `/raidtrain claim`; `/twitch link` first if you have not.")
    return "\n".join(lines)


def _neighbour_words(slot: Any, *, before: bool) -> str:
    if slot is None or _value(slot, "user_id") is None:
        return (
            "Nobody is booked into the slot before yours, so you open the train."
            if before
            else "Nobody is booked after you, so you close the train — no raid to send on."
        )
    login = str(_value(slot, "twitch_login") or "").strip()
    where = f" ({twitch_url(login)})" if login else ""
    if before:
        return f"<@{int(_value(slot, 'user_id'))}>{where} raids into you."
    return f"When you finish, raid <@{int(_value(slot, 'user_id'))}>{where}."


def reminder_text(train: Any, slot: Any, previous: Any, upcoming: Any, link: Any = None) -> str:
    """The DM a slot holder is owed: when, who raids in, who to raid on to."""
    start = parse_ts(_value(slot, "starts_at"))
    when = (
        f"<t:{unix(start)}:t> (<t:{unix(start)}:R>)" if start is not None else "soon"
    )
    lines = [
        f"Your slot on **{clamp(_value(train, 'title'), TITLE_LIMIT)}** starts {when}.",
        f"You are slot **#{int(_value(slot, 'position') or 0)}**.",
        _neighbour_words(previous, before=True),
        _neighbour_words(upcoming, before=False),
    ]
    if link:
        lines.append(f"The lineup: {link}")
    return "\n".join(lines)


def cancelled_text(train: Any, reason: Any = None) -> str:
    said = clamp(reason, DESCRIPTION_LIMIT)
    tail = f" The organizer said: {said}" if said else ""
    return (
        f"**{clamp(_value(train, 'title'), TITLE_LIMIT)}** has been called off, so the slot you "
        f"held on it is no longer happening.{tail}"
    )


def due_reminders(
    now: datetime,
    lead_minutes: Any,
    slots: Any,
    *,
    late_minutes: int = REMINDER_LATE_MINUTES,
) -> list[Any]:
    """Claimed slots inside the lead window whose start has not already gone by."""
    lead = timedelta(minutes=max(0, int(lead_minutes or 0)))
    floor = now - timedelta(minutes=int(late_minutes))
    found = []
    for slot in slots or ():
        if _value(slot, "user_id") is None or _value(slot, "reminded_at"):
            continue
        start = parse_ts(_value(slot, "starts_at"))
        if start is None or start > now + lead or start <= floor:
            continue
        found.append(slot)
    return sorted(found, key=lambda one: int(_value(one, "position") or 0))


def missed_reminders(
    now: datetime, slots: Any, *, late_minutes: int = REMINDER_LATE_MINUTES
) -> list[Any]:
    """Slots whose reminder is now pointless: stamped so the sweep never carries them again."""
    floor = now - timedelta(minutes=int(late_minutes))
    found = []
    for slot in slots or ():
        if _value(slot, "user_id") is None or _value(slot, "reminded_at"):
            continue
        start = parse_ts(_value(slot, "starts_at"))
        if start is not None and start <= floor:
            found.append(slot)
    return sorted(found, key=lambda one: int(_value(one, "position") or 0))


def due_checkins(
    now: datetime,
    slots: Any,
    live_user_ids: Any,
    *,
    early_minutes: int = CHECKIN_EARLY_MINUTES,
) -> list[Any]:
    """A slot holder who is already streaming inside their own window, not yet checked in."""
    live = {int(one) for one in live_user_ids or ()}
    early = timedelta(minutes=int(early_minutes))
    found = []
    for slot in slots or ():
        user_id = _value(slot, "user_id")
        if user_id is None or int(user_id) not in live or _value(slot, "checked_in_at"):
            continue
        start = parse_ts(_value(slot, "starts_at"))
        finish = parse_ts(_value(slot, "ends_at"))
        if start is None or finish is None:
            continue
        if start - early <= now < finish:
            found.append(slot)
    return sorted(found, key=lambda one: int(_value(one, "position") or 0))


def live_post_text(train: Any, slot: Any, upcoming: Any) -> str:
    """The `the train moves` line: who is on air, and who is up next."""
    login = str(_value(slot, "twitch_login") or "").strip()
    who = f"**{login}**" if login else f"<@{int(_value(slot, 'user_id') or 0)}>"
    where = f" — {twitch_url(login)}" if login else ""
    if upcoming is None or _value(upcoming, "user_id") is None:
        return f"{who} is live{where}. That is the last booked slot on this train."
    start = parse_ts(_value(upcoming, "starts_at"))
    when = f" at <t:{unix(start)}:t>" if start is not None else ""
    next_login = str(_value(upcoming, "twitch_login") or "").strip()
    next_who = f"**{next_login}**" if next_login else f"<@{int(_value(upcoming, 'user_id'))}>"
    return f"{who} is live{where}. Next up {next_who}{when}."


def positions_word(slots: Any) -> str:
    found = open_positions(slots)
    if not found:
        return "none"
    return ", ".join(f"#{one}" for one in sorted(found))


__all__ = [
    "CANCELLED",
    "CAP_REACHED",
    "DESCRIPTION_LIMIT",
    "DONE",
    "LIVE",
    "LOCKED",
    "NEEDS_LINK",
    "NOT_YOURS",
    "OPEN",
    "OPEN_STATUSES",
    "SLOT_COUNT_MAX",
    "SLOT_COUNT_MIN",
    "SLOT_MINUTES_MAX",
    "SLOT_MINUTES_MIN",
    "SLOT_TAKEN",
    "SLOT_UNKNOWN",
    "STATUSES",
    "STATUS_WORDS",
    "TERMINAL_STATUSES",
    "TITLE_LIMIT",
    "TRAIN_FULL",
    "TRAIN_LOCKED",
    "TRANSITIONS",
    "allowed_moves",
    "caps_ok",
    "cancelled_text",
    "due_checkins",
    "due_reminders",
    "ends_at",
    "filled",
    "live_post_text",
    "may_move",
    "missed_reminders",
    "move_refusal",
    "neighbours",
    "next_open_position",
    "open_positions",
    "positions_word",
    "reminder_text",
    "render_lineup",
    "slot_at",
    "slot_times",
    "slots_held",
    "twitch_url",
]
