"""Who may create and run tournaments."""

from __future__ import annotations

from typing import Any

TO_ROLE_KEY = "brackets_to_role_id"


def holds_role(person: Any, role_id: int) -> bool:
    return any(
        getattr(role, "id", None) == role_id for role in getattr(person, "roles", None) or ()
    )


def may_run(store: Any, guild: Any, person: Any) -> bool:
    """Staff, or a holder of the Tournament Organiser role; the role decides, not authorship."""
    if guild is None or person is None:
        return False
    if getattr(person, "guild", None) is not None and store.is_staff(person):
        return True
    try:
        wanted = int(store.get(guild.id, TO_ROLE_KEY) or 0)
    except (TypeError, ValueError):
        return False
    return bool(wanted) and holds_role(person, wanted)


def is_staff(store: Any, person: Any) -> bool:
    return getattr(person, "guild", None) is not None and bool(store.is_staff(person))
