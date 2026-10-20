"""Everyone opted out of something: the one table, the role filters, and who staff count in."""

from __future__ import annotations

from typing import Any

from ... import marathon_announce as ma
from ... import optouts
from ...cogs.content.marathon import baf_overrides, list_marathons
from ...cogs.content.marathon_announce import baf_rule, override_reason, words
from ...cogs.content.spotlight import channels_for
from ...golive import ignored_by_role
from ...marathon_channels import takes_marathons
from ...settings_store import (
    GOLIVE_IGNORED_ROLE_WORD_KEY,
    MARATHON_POSTS_OPTED_OUT_WORD_KEY,
)
from ..names import avatar_url

MARATHON_ROLE = "marathon_role"
MARATHON_POSTS = "marathon_posts"
GOLIVE_IGNORE_ROLE = "golive_ignore_role"
SOURCES = (
    MARATHON_ROLE,
    MARATHON_POSTS,
    optouts.ANNOUNCE,
    GOLIVE_IGNORE_ROLE,
    optouts.CHAT_MEMORY,
    optouts.BIRTHDAY,
    optouts.PBS,
    optouts.STREAMER_LIST,
)


def chip(source: str, said: Any = None, *, marathons: Any = (), rule: Any = None) -> dict:
    return {"source": source, "said": said, "marathons": list(marathons), "rule": rule}


async def marathon_chips(bot: Any, guild: Any) -> list[tuple[int, dict[str, Any]]]:
    overrides = await baf_overrides(bot.db)
    held = ma.role_holders(guild, ma.optout_roles(guild, bot.store)) - set(overrides)
    found = []
    for user_id in sorted(held):
        rule = baf_rule(bot, guild, held=user_id)
        found.append((user_id, chip(MARATHON_ROLE, rule["said"], rule=rule)))
    posts: dict[int, list[dict[str, Any]]] = {}
    for row in await list_marathons(bot.db, guild.id):
        for user_id in sorted(ma.opted_out(row)):
            posts.setdefault(user_id, []).append({"id": int(row["id"]), "name": row["name"]})
    said = words(bot, guild.id, MARATHON_POSTS_OPTED_OUT_WORD_KEY)
    found.extend(
        (user_id, chip(MARATHON_POSTS, said, marathons=on)) for user_id, on in posts.items()
    )
    return found


def role_chips(bot: Any, guild: Any) -> list[tuple[int, dict[str, Any]]]:
    role_id, holders = ignored_by_role(guild, bot.store)
    if not holders:
        return []
    role = guild.get_role(int(role_id)) if hasattr(guild, "get_role") else None
    said = optouts.said(
        bot.store, guild.id, GOLIVE_IGNORED_ROLE_WORD_KEY, role=getattr(role, "name", "")
    )
    return [(user_id, chip(GOLIVE_IGNORE_ROLE, said)) for user_id in sorted(holders)]


async def table_chips(bot: Any, guild: Any) -> list[tuple[int, dict[str, Any]]]:
    return [
        (int(row["user_id"]), chip(str(row["kind"])))
        for row in await optouts.rows(bot.db, guild.id)
    ]


def person_row(guild: Any, user_id: int, **fields: Any) -> dict[str, Any]:
    member = guild.get_member(int(user_id))
    name = str(getattr(member, "name", "") or "")
    return {
        "user_id": str(user_id),
        "name": str(getattr(member, "display_name", None) or name or user_id),
        "username": name or None,
        "avatar": avatar_url(member) if member is not None else None,
        "here": member is not None,
        **fields,
    }


def by_name(guild: Any, user_id: Any) -> str | None:
    if not user_id:
        return None
    member = guild.get_member(int(user_id))
    return str(getattr(member, "display_name", None) or user_id)


async def counted_in(bot: Any, guild: Any) -> list[dict[str, Any]]:
    """Who staff count as BaF anyway: an opt-in, so never inside the opted-out list."""
    overrides = await baf_overrides(bot.db)
    found = []
    for user_id, row in overrides.items():
        rule = baf_rule(bot, guild, user_id=user_id, overrides=overrides)
        found.append(
            person_row(
                guild,
                user_id,
                said=rule["said"] if rule else None,
                reason=override_reason(bot, guild, row),
                by=str(row["by"]) if row["by"] else None,
                by_name=by_name(guild, row["by"]),
                at=row["at"],
                rule=rule,
            )
        )
    found.sort(key=lambda one: (not one["here"], one["name"].lower()))
    return found


async def roll_up(bot: Any, guild: Any) -> dict[str, Any]:
    """Read-only: the one table, the two role filters, and each marathon's own "not this one"."""
    by_person: dict[int, list[dict[str, Any]]] = {}
    gathered = [
        *await marathon_chips(bot, guild),
        *role_chips(bot, guild),
        *await table_chips(bot, guild),
    ]
    for user_id, one in gathered:
        by_person.setdefault(int(user_id), []).append(one)
    people = [
        person_row(
            guild,
            user_id,
            chips=sorted(chips, key=lambda one: SOURCES.index(one["source"])),
        )
        for user_id, chips in by_person.items()
    ]
    people.sort(key=lambda one: (not one["here"], one["name"].lower()))
    channels = [
        {
            "id": int(row["id"]),
            "login": row["twitch_login"],
            "name": row["display_name"] or row["twitch_login"],
        }
        for row in await channels_for(bot.db, guild.id)
        if not takes_marathons(row)
    ]
    return {
        "people": people,
        "counted_in": await counted_in(bot, guild),
        "channels": channels,
        "sources": list(SOURCES),
    }


__all__ = ["SOURCES", "counted_in", "roll_up"]
