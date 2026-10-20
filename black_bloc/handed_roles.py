"""A feature switched off takes back the roles it handed out, after staff see how many."""

from __future__ import annotations

import json
import logging
from typing import Any, NamedTuple

import discord

from . import optouts
from . import rolegrants as grants
from .actionlog import log_action
from .settings_store import (
    PINGS_OFF_BUTTON_KEY,
    PINGS_OFF_CONFIRM_KEY,
    ROLEMENU_OFF_BUTTON_KEY,
    ROLEMENU_OFF_CONFIRM_KEY,
    ROLEMENU_OFF_DM_KEY,
)

log = logging.getLogger(__name__)

OFF = "off"
CONFIRM_CODE = "confirm_needed"
PINGS = "pings_mode"
ROLEMENUS = "rolemenu_mode"
KEYS: tuple[str, ...] = (PINGS, ROLEMENUS)
ASKS = {PINGS: PINGS_OFF_CONFIRM_KEY, ROLEMENUS: ROLEMENU_OFF_CONFIRM_KEY}
BUTTONS = {PINGS: PINGS_OFF_BUTTON_KEY, ROLEMENUS: ROLEMENU_OFF_BUTTON_KEY}
FEATURE_OFF = "feature_off"
PINGS_TAKEN = "pings.roles_taken_back"
MENUS_TAKEN = "role_menu.roles_taken_back"
PINGS_GIVEN = ("pings.follow", "pings.events_on")
PINGS_DROPPED = ("pings.unfollow", "pings.events_off")
PINGS_LEDGER = (*PINGS_GIVEN, *PINGS_DROPPED, PINGS_TAKEN)
MENU_SOURCES = (grants.MENU, grants.APPROVAL)
REASONS = {
    PINGS: "Black Bloc: pings were switched off",
    ROLEMENUS: "Black Bloc: role menus were switched off",
}
HOOK_ATTR = "_handed_roles_hooked"


class Held(NamedTuple):
    """One role the feature put on one member, still worn."""

    user_id: int
    role_id: int
    grant_id: int | None = None
    told: bool = False
    label: str = ""


def _details(text: Any) -> dict[str, Any]:
    try:
        found = json.loads(text) if text else {}
    except (TypeError, ValueError):
        return {}
    return found if isinstance(found, dict) else {}


def _bare(kind: str) -> str:
    return kind.removeprefix("web.")


async def pings_ledger(db: Any, guild_id: int) -> dict[tuple[int, int], bool]:
    """The pings feature's own record of who it gave a role to: its follow and events rows,
    newest last, and the take-back rows that closed them."""
    kinds = (*PINGS_LEDGER, *(f"web.{kind}" for kind in PINGS_LEDGER))
    cur = await db.conn.execute(
        f"SELECT kind, target_id, details FROM action_log WHERE guild_id = ? AND kind IN "
        f"({', '.join('?' for _ in kinds)}) ORDER BY id",
        (int(guild_id), *kinds),
    )
    ledger: dict[tuple[int, int], bool] = {}
    for row in await cur.fetchall():
        kind = _bare(row["kind"])
        details = _details(row["details"])
        if kind == PINGS_TAKEN:
            for user_id, role_id in details.get("taken") or ():
                ledger[(int(user_id), int(role_id))] = False
            continue
        role_id = details.get("role_id")
        if role_id is None or row["target_id"] is None:
            continue
        ledger[(int(row["target_id"]), int(role_id))] = kind in PINGS_GIVEN
    return ledger


async def menu_grants(db: Any, guild_id: int) -> list[Any]:
    """Open grants of a menu role a member picked from a panel or asked for; never one staff
    handed over, one added by hand, or an application's role."""
    cur = await db.conn.execute(
        "SELECT g.id, g.user_id, g.role_id, g.source, "
        "(SELECT o.label FROM role_menu_options o JOIN role_menus m ON m.id = o.menu_id "
        " WHERE m.guild_id = g.guild_id AND o.role_id = g.role_id LIMIT 1) AS label "
        "FROM role_grants g WHERE g.guild_id = ? AND g.removed_at IS NULL "
        f"AND g.source IN ({', '.join('?' for _ in MENU_SOURCES)}) "
        "AND g.role_id IN (SELECT o.role_id FROM role_menu_options o JOIN role_menus m "
        " ON m.id = o.menu_id WHERE m.guild_id = g.guild_id) "
        "AND g.id NOT IN (SELECT grant_id FROM applications WHERE grant_id IS NOT NULL) "
        "ORDER BY g.id",
        (int(guild_id), *MENU_SOURCES),
    )
    return list(await cur.fetchall())


def wears(guild: Any, user_id: int, role_id: int) -> bool:
    member = guild.get_member(int(user_id))
    return member is not None and any(
        int(role.id) == int(role_id) for role in getattr(member, "roles", ())
    )


async def held(bot: Any, guild: Any, key: str) -> list[Held]:
    """The dry run: every role this feature handed out that its member still wears."""
    if key == PINGS:
        ledger = await pings_ledger(bot.db, guild.id)
        return [
            Held(user_id, role_id)
            for (user_id, role_id), given in sorted(ledger.items())
            if given and wears(guild, user_id, role_id)
        ]
    if key == ROLEMENUS:
        found: dict[tuple[int, int], Held] = {}
        for row in await menu_grants(bot.db, guild.id):
            pair = (int(row["user_id"]), int(row["role_id"]))
            if pair in found or not wears(guild, *pair):
                continue
            found[pair] = Held(
                *pair,
                grant_id=int(row["id"]),
                told=row["source"] == grants.APPROVAL,
                label=str(row["label"] or ""),
            )
        return list(found.values())
    return []


def members_in(found: list[Held]) -> int:
    return len({one.user_id for one in found})


async def asked(bot: Any, guild: Any, key: str, value: Any) -> str | None:
    """The count sentence staff confirm before an off, or None when nothing would be taken."""
    if key not in KEYS or str(value) != OFF:
        return None
    found = await held(bot, guild, key)
    if not found:
        return None
    return optouts.said(bot.store, guild.id, ASKS[key], count=members_in(found))


def button_label(store: Any, guild_id: int, key: str) -> str:
    return str(store.get(guild_id, BUTTONS[key]) or "")


async def _take(bot: Any, guild: Any, key: str, one: Held) -> bool:
    member = guild.get_member(one.user_id)
    role = guild.get_role(one.role_id) if hasattr(guild, "get_role") else None
    if member is None or role is None:
        return False
    if key == PINGS:
        from .pings import wear

        return await wear(bot, guild, member, role, add=False) is None
    from .cogs.community.role_menus import change_roles

    return await change_roles(bot, member, guild, set(), {one.role_id}, REASONS[key])


async def _tell(bot: Any, guild: Any, one: Held) -> bool:
    member = guild.get_member(one.user_id)
    if member is None:
        return False
    text = optouts.said(
        bot.store, guild.id, ROLEMENU_OFF_DM_KEY, guild=guild.name, label=one.label or "a role"
    )
    try:
        await member.send(text, allowed_mentions=discord.AllowedMentions.none())
    except Exception as exc:
        log.info("handed roles: no DM for %s — %s: %s", one.user_id, type(exc).__name__, exc)
        return False
    return True


async def take_back(bot: Any, guild: Any, key: str, actor: Any = None) -> dict[str, Any] | None:
    """Every role the dry run names comes off, one log row says how many, and a DM goes only
    where the feature already DM'd on the grant."""
    if key not in KEYS:
        return None
    found = await held(bot, guild, key)
    if not found:
        return None
    taken: list[list[int]] = []
    failed = 0
    told = 0
    for one in found:
        if not await _take(bot, guild, key, one):
            failed += 1
            continue
        taken.append([one.user_id, one.role_id])
        if one.grant_id is not None:
            await grants.end_grant(bot.db, one.grant_id, FEATURE_OFF)
        if one.told and await _tell(bot, guild, one):
            told += 1
    details = {
        "key": key,
        "members": len({user_id for user_id, _ in taken}),
        "roles": len(taken),
        "failed": failed,
        "dms": told,
        "taken": taken,
    }
    await log_action(
        bot,
        guild,
        "pings.roles_taken_back" if key == PINGS else "role_menu.roles_taken_back",
        actor=actor,
        details=details,
        notify=True,
    )
    return details


def install(bot: Any) -> None:
    """One trigger path: every write that leaves pings or role menus off, wherever it is made."""
    if getattr(bot, HOOK_ATTR, False):
        return

    async def switched(guild_id: int, key: str, _value: Any, by: Any) -> None:
        if str(bot.store.get(guild_id, key)) != OFF:
            return
        guild = bot.get_guild(guild_id)
        if guild is not None:
            await take_back(bot, guild, key, by)

    for key in KEYS:
        bot.store.on_change(key, switched)
    setattr(bot, HOOK_ATTR, True)


__all__ = [
    "CONFIRM_CODE",
    "FEATURE_OFF",
    "KEYS",
    "Held",
    "asked",
    "button_label",
    "held",
    "install",
    "members_in",
    "menu_grants",
    "pings_ledger",
    "take_back",
]
