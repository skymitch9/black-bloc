"""Whether the Marathon role rides a marathon's ping-mark heads-up, and why not when it does not."""

from __future__ import annotations

from typing import Any, NamedTuple

SWITCH_OFF = "switch_off"
ROLE_PINGS_OFF = "role_pings_off"
REMINDER_PINGS_OFF = "reminder_pings_off"
PUBLIC_REMINDERS_OFF = "public_reminders_off"
ANNOUNCEMENTS_OFF = "announcements_off"
UNSET = "unset"
GONE = "gone"
NOT_MENTIONABLE = "not_mentionable"
NO_PUBLIC_COPY = "no_public_copy"
RUNNER_COPY = "runner_copy"
REHEARSAL = "rehearsal"
KEY_REASONS = (ROLE_PINGS_OFF, REMINDER_PINGS_OFF, PUBLIC_REMINDERS_OFF)
REASONS = (
    SWITCH_OFF,
    *KEY_REASONS,
    ANNOUNCEMENTS_OFF,
    UNSET,
    GONE,
    NOT_MENTIONABLE,
    NO_PUBLIC_COPY,
    RUNNER_COPY,
    REHEARSAL,
)


class Verdict(NamedTuple):
    role_id: int | None
    reason: str | None
    configured: int | None = None
    name: str = ""

    @property
    def mentions(self) -> bool:
        return self.role_id is not None


def notifies(role: Any, may_mention_every_role: bool) -> bool:
    """Discord notifies a role's members only when the role is mentionable or the sender holds
    Mention Everyone where it posts."""
    return bool(getattr(role, "mentionable", False)) or bool(may_mention_every_role)


def decide(
    *,
    switch_on: bool,
    off: tuple[tuple[str, bool], ...],
    announces: bool,
    rehearsing: bool = False,
    configured: int | None,
    role: Any,
    may_mention_every_role: bool,
) -> Verdict:
    """`off` is each (reason, key is on) pair in the order staff should hear about them."""
    name = str(getattr(role, "name", "") or "")
    if not switch_on:
        return Verdict(None, SWITCH_OFF, configured, name)
    for reason, on in off:
        if not on:
            return Verdict(None, reason, configured, name)
    if not announces:
        return Verdict(None, ANNOUNCEMENTS_OFF, configured, name)
    if rehearsing:
        return Verdict(None, REHEARSAL, configured, name)
    if configured is None:
        return Verdict(None, UNSET)
    if role is None:
        return Verdict(None, GONE, configured)
    if not notifies(role, may_mention_every_role):
        return Verdict(None, NOT_MENTIONABLE, configured, name)
    return Verdict(int(configured), None, int(configured), name)


def unsent(verdict: Verdict, reason: str) -> Verdict:
    """A verdict that would have mentioned, on a copy that will not."""
    if not verdict.mentions:
        return verdict
    return Verdict(None, reason, verdict.configured, verdict.name)


def with_role(roles: Any, verdict: Verdict | None) -> list[int]:
    found = [int(one) for one in roles or ()]
    if verdict is not None and verdict.mentions:
        found.append(int(verdict.role_id))
    return list(dict.fromkeys(found))


def without_role(roles: Any, verdict: Verdict | None) -> list[int]:
    """The staff thread's copy never carries the Marathon role, whoever else it mentions."""
    found = list(dict.fromkeys(int(one) for one in roles or ()))
    if verdict is None or not verdict.mentions:
        return found
    return [one for one in found if one != int(verdict.role_id)]


def row_fields(verdict: Verdict | None) -> dict[str, Any]:
    if verdict is None:
        return {}
    return {"marathon_role": verdict.role_id, "marathon_role_reason": verdict.reason}


__all__ = [
    "ANNOUNCEMENTS_OFF",
    "GONE",
    "KEY_REASONS",
    "NOT_MENTIONABLE",
    "NO_PUBLIC_COPY",
    "PUBLIC_REMINDERS_OFF",
    "REASONS",
    "REHEARSAL",
    "REMINDER_PINGS_OFF",
    "ROLE_PINGS_OFF",
    "RUNNER_COPY",
    "SWITCH_OFF",
    "UNSET",
    "Verdict",
    "decide",
    "notifies",
    "row_fields",
    "unsent",
    "with_role",
    "without_role",
]
