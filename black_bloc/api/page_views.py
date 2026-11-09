"""Who may open which site page, read by each page's `view_<page>_role_ids`."""

from __future__ import annotations

from typing import Any

from ..settings_store import VIEW_MEMBER_PAGES, VIEW_PAGES, view_key

STAFF_PAGE_PREFIXES: dict[str, tuple[str, ...]] = {
    "overview": ("/api/actions", "/api/status"),
    "health": ("/api/actions", "/api/costs", "/api/selftest", "/api/status"),
    "audit": ("/api/actions", "/api/settings/audit"),
    "moderation": ("/api/mod/cases",),
    "members": ("/api/members",),
    "automod": ("/api/mod/rules",),
    "honeypot": ("/api/honeypot",),
    "modmail": ("/api/modmail", "/api/frontdoor"),
    "posts": (
        "/api/posts",
        "/api/post-blocks",
        "/api/sticky",
        "/api/bluesky",
        "/api/ninja",
        "/api/questions",
    ),
    "golive": ("/api/golive", "/api/pings", "/api/youtube"),
    "pbs": ("/api/pbs",),
    "events": ("/api/events", "/api/marathons"),
    "runs": ("/api/runs",),
    "raidtrain": ("/api/raidtrains",),
    "birthdays": ("/api/birthdays",),
    "tempvoice": ("/api/tempvoice",),
    "rolemenus": ("/api/rolemenus", "/api/applications", "/api/roles"),
    "polls": ("/api/polls",),
    "chat": ("/api/chat",),
    "settings": ("/api/settings",),
}
MEMBER_PAGE_PREFIXES: dict[str, tuple[str, ...]] = {
    "requests": ("/api/requests",),
    "guides": ("/api/guides",),
    "brackets": ("/api/brackets", "/api/sports"),
    "leaderboard": ("/api/points",),
}
SHARED_READ_PREFIXES: tuple[str, ...] = ("/api/ref",)
READ_METHODS = frozenset({"GET", "HEAD"})


def under(path: str, prefix: str) -> bool:
    return path == prefix or path.startswith(prefix + "/")


def pages_at(path: str, table: dict[str, tuple[str, ...]]) -> list[str]:
    return [page for page, prefixes in table.items() if any(under(path, p) for p in prefixes)]


def role_ids_of(member: Any) -> set[int]:
    found = {getattr(role, "id", None) for role in getattr(member, "roles", None) or ()}
    return {one for one in found if isinstance(one, int)}


def may_view(store: Any, guild: Any, member: Any, page: str) -> bool:
    if guild is None or member is None or page not in VIEW_PAGES:
        return False
    try:
        wanted = {int(one) for one in store.get(guild.id, view_key(page)) or ()}
    except (TypeError, ValueError):
        return False
    return guild.id in wanted or bool(wanted & role_ids_of(member))


def viewable(store: Any, guild: Any, member: Any) -> list[str]:
    return [page for page in VIEW_PAGES if may_view(store, guild, member, page)]


def staff_pages_viewed(store: Any, guild: Any, member: Any) -> list[str]:
    return [page for page in viewable(store, guild, member) if page not in VIEW_MEMBER_PAGES]


def viewer_may_read(store: Any, guild: Any, member: Any, path: str) -> bool:
    """A staff-only GET a non-staff member may make because a page they view reads it."""
    seen = staff_pages_viewed(store, guild, member)
    if not seen:
        return False
    if any(under(path, prefix) for prefix in SHARED_READ_PREFIXES):
        return True
    return any(page in seen for page in pages_at(path, STAFF_PAGE_PREFIXES))


def views_a_page_at(store: Any, guild: Any, member: Any, path: str) -> bool:
    seen = staff_pages_viewed(store, guild, member)
    return any(page in seen for page in pages_at(path, STAFF_PAGE_PREFIXES))


def member_page_closed(store: Any, guild: Any, member: Any, path: str) -> bool:
    """True when the path belongs to a member page whose roles this member does not wear."""
    pages = pages_at(path, MEMBER_PAGE_PREFIXES)
    return bool(pages) and not any(may_view(store, guild, member, page) for page in pages)
