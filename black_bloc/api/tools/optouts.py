"""Everyone opted out of something, one reader per place they are out of."""

from __future__ import annotations

from typing import Any

from ... import marathon_announce as ma
from ... import pb_store
from ...chat_memory import CONSENT_KEY, off_default
from ...cogs.community.birthdays import rows_for_guild
from ...cogs.content.golive import all_optouts
from ...cogs.content.marathon import baf_overrides, list_marathons
from ...cogs.content.marathon_announce import baf_rule, words
from ...cogs.content.spotlight import channels_for
from ...marathon_channels import takes_marathons
from ...settings_store import MARATHON_POSTS_OPTED_OUT_WORD_KEY
from ..names import avatar_url

MARATHON_ROLE = "marathon_role"
MARATHON_OVERRIDE = "marathon_override"
MARATHON_POSTS = "marathon_posts"
GOLIVE = "golive"
CHAT_MEMORY = "chat_memory"
BIRTHDAYS = "birthdays"
PBS = "pbs"
SOURCES = (MARATHON_ROLE, MARATHON_OVERRIDE, MARATHON_POSTS, GOLIVE, CHAT_MEMORY, BIRTHDAYS, PBS)


def chip(source: str, said: Any = None, *, marathons: Any = (), rule: Any = None) -> dict:
    return {"source": source, "said": said, "marathons": list(marathons), "rule": rule}


async def marathon_chips(bot: Any, guild: Any) -> list[tuple[int, dict[str, Any]]]:
    overrides = await baf_overrides(bot.db)
    held = ma.role_holders(guild, ma.optout_roles(guild, bot.store)) - set(overrides)
    found = []
    for user_id in sorted(held):
        rule = baf_rule(bot, guild, held=user_id)
        found.append((user_id, chip(MARATHON_ROLE, rule["said"], rule=rule)))
    for user_id in sorted(overrides):
        rule = baf_rule(bot, guild, user_id=user_id, overrides=overrides)
        found.append((user_id, chip(MARATHON_OVERRIDE, rule["said"], rule=rule)))
    posts: dict[int, list[dict[str, Any]]] = {}
    for row in await list_marathons(bot.db, guild.id):
        for user_id in sorted(ma.opted_out(row)):
            posts.setdefault(user_id, []).append({"id": int(row["id"]), "name": row["name"]})
    said = words(bot, guild.id, MARATHON_POSTS_OPTED_OUT_WORD_KEY)
    found.extend(
        (user_id, chip(MARATHON_POSTS, said, marathons=on)) for user_id, on in posts.items()
    )
    return found


async def other_chips(bot: Any, guild: Any) -> list[tuple[int, dict[str, Any]]]:
    found = [(int(row["user_id"]), chip(GOLIVE)) for row in await all_optouts(bot.db)]
    consent = bot.store.get(guild.id, CONSENT_KEY)
    found.extend(
        (user_id, chip(CHAT_MEMORY))
        for user_id in await off_default(bot.db, guild.id, consent=consent)
    )
    found.extend(
        (int(row["user_id"]), chip(BIRTHDAYS))
        for row in await rows_for_guild(bot.db, guild.id)
        if not row["opted_in"]
    )
    found.extend(
        (int(row["user_id"]), chip(PBS))
        for row in await pb_store.matches(bot.db, guild.id)
        if row["state"] == pb_store.OPTED_OUT
    )
    return found


def person_row(guild: Any, user_id: int, chips: list[dict[str, Any]]) -> dict[str, Any]:
    member = guild.get_member(int(user_id))
    name = str(getattr(member, "name", "") or "")
    return {
        "user_id": str(user_id),
        "name": str(getattr(member, "display_name", None) or name or user_id),
        "username": name or None,
        "avatar": avatar_url(member) if member is not None else None,
        "here": member is not None,
        "chips": sorted(chips, key=lambda one: SOURCES.index(one["source"])),
    }


async def roll_up(bot: Any, guild: Any) -> dict[str, Any]:
    """Read-only: every opt-out stays in its own store; this only reads each one."""
    by_person: dict[int, list[dict[str, Any]]] = {}
    for user_id, one in [*await marathon_chips(bot, guild), *await other_chips(bot, guild)]:
        by_person.setdefault(int(user_id), []).append(one)
    people = [person_row(guild, user_id, chips) for user_id, chips in by_person.items()]
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
    return {"people": people, "channels": channels, "sources": list(SOURCES)}


__all__ = ["SOURCES", "roll_up"]
