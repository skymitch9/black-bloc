from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime
from typing import Any, NamedTuple

import discord
from discord import app_commands
from discord.ext import commands, tasks

from ...actionlog import (
    LOGS_DEFAULT,
    LOGS_MAX,
    LOGS_MIN,
    log_action,
    send_logs,
)
from ...command_errors import AnswersErrors
from ...golive import now_iso, parse_ts
from ...settings_store import (
    DB_UNAVAILABLE,
    GUILD_ONLY,
    TEMPVOICE_MODES,
    TEMPVOICE_NAME_TEMPLATE,
    require_staff,
)

log = logging.getLogger(__name__)

AFK_FALLBACK_NAME = "You Still Here?"
PANEL_PREFIX = "tempvoice"
RECONCILE_GRACE_SECONDS = 60
RECONCILE_MINUTES = 5
NAME_LIMIT = 100
LOCKS_ATTR = "_tempvoice_channel_locks"
MIN_BITRATE = 8
MAX_BITRATE = 96
MEMBER_MEMORY_MAX = 50
PERMITTED = "permitted"
BANNED = "banned"
FORGOTTEN = "forgotten"
AUTO_REGION = "auto"
VOICE_REGIONS = (
    AUTO_REGION,
    "brazil",
    "bucharest",
    "buenos-aires",
    "dubai",
    "finland",
    "frankfurt",
    "hongkong",
    "india",
    "japan",
    "madrid",
    "milan",
    "rotterdam",
    "russia",
    "santiago",
    "singapore",
    "south-korea",
    "southafrica",
    "stockholm",
    "sydney",
    "tel-aviv",
    "us-central",
    "us-east",
    "us-south",
    "us-west",
    "warsaw",
)

NOT_A_TEMP_CHANNEL = (
    "This panel is not attached to a temporary voice channel any more, so nothing was changed. "
    "Join the join-to-create channel again to get a fresh one."
)
NOT_ALLOWED = (
    "Black Bloc did not make you a voice channel because join-to-create is for members with the "
    "<@&{role_id}> role. Ask a Lead for that role, then join the channel again."
)
CANNOT_EDIT = (
    "Discord refused that change, so nothing happened. Black Bloc needs the Manage Channels and "
    "Move Members permissions in this category. Ask a Lead to check them, then try again."
)
NOT_IN_CHANNEL = (
    "**{name}** is not in this channel, so nothing was changed. They have to be connected here "
    "before they can be moved out."
)
OWNER_STILL_HERE = (
    "This channel still belongs to <@{owner_id}>, and they are still in it, so it cannot be "
    "claimed. Ask them to hand it over with the Transfer button."
)
NO_TEST_CHANNEL = (
    "Black Bloc is in test mode and cannot see its test channel, so no channel was created. Set "
    "TEST_CHANNEL_ID to a channel the bot can read, restart it, then run this again."
)
CANNOT_CREATE = (
    "Discord refused to create the channel, so nothing was made. Black Bloc needs the Manage "
    "Channels permission in this server. Ask an admin to give it that, then run this again."
)
CLAIM_LOST = (
    "Someone else just claimed this channel, so nothing was changed. Ask them to hand it over "
    "with the Transfer button, or make your own by joining the join-to-create channel."
)
CLAIM_NEEDS_CONNECTION = (
    "You have to be connected to this channel before you can claim it, so nothing was changed. "
    "Join the voice channel, then press Claim again."
)
CHANNEL_GONE = (
    "That temporary voice channel is gone, so nothing was changed. Join the join-to-create "
    "channel again to get a fresh one."
)
RENAMED_TOO_OFTEN = (
    "Discord only lets a channel be renamed **twice every 10 minutes**, and this one has used "
    "both, so the name did not change. Wait a few minutes and try again."
)
VOICE_NEEDS_ROLE = (
    "Voice controls are for members with the <@&{role_id}> role, so nothing was changed. Ask a "
    "Lead for that role, then try again."
)
NO_OWNED_CHANNEL = (
    "You don't own a temp channel right now — join **{lobby}** to make one."
)
CLAIM_NEEDS_A_CHANNEL = (
    "You are not in one of Black Bloc's temporary voice channels, so there is nothing to claim. "
    "Join the one you want, then run `/voice claim` again."
)
CANNOT_SET_REGION = (
    "Discord would not use **{region}** as this channel's voice region, so nothing changed. Pick "
    "one from the list, or **auto** to let Discord choose the closest server."
)
PREFS_CLEARED = (
    "Forgotten. Your next temporary channel starts from the server's defaults — name, limit, "
    "lock, hidden, bitrate, region, and everyone you had let in or shut out by name. The channel "
    "you are in now is not changed; `/voice info` shows it."
)
NOTHING_REMEMBERED = (
    "There was nothing to forget — Black Bloc keeps no voice settings for you yet. It starts "
    "remembering the first time you rename, cap, lock, hide, permit or ban in one of your "
    "channels."
)
REPAIRED = (
    "Black Bloc repaired the join-to-create channel it already had — {where} — instead of making "
    "a second one. It is called **{name}** again, and {who} can see it and join it."
)
ADOPTED = (
    "Black Bloc found a join-to-create channel it was not keeping track of — {where} — and took "
    "it over instead of making a second one. It is called **{name}**, and {who} can see it and "
    "join it."
)
EXTRA_LOBBIES = (
    " There are other join-to-create channels too — {extras} — so drop the ones you do not want "
    "with `/tempvoice forget <id>`."
)
STRAY_LOBBIES = (
    "**not kept track of** — {extras}. Each of those is called **{name}** and sits where the "
    "join-to-create channel belongs, but Black Bloc does not treat it as one. Run `/tempvoice "
    "setup` to take it over and repair it, or delete the channel."
)
CANNOT_REPAIR = (
    "Discord refused to change {where}, so nothing was repaired. Black Bloc needs the Manage "
    "Channels and Manage Roles permissions in that category. Ask an admin to check them, then "
    "run this again."
)
OUTSIDE_TEST_CATEGORY = (
    "{where} is Black Bloc's join-to-create channel, but it sits outside the test channel's "
    "category, so test mode stopped it being repaired. Delete that channel and run this again, "
    "or turn test mode off first."
)
NOT_A_LOBBY = (
    "**{channel_id}** is not one of Black Bloc's join-to-create channels, so nothing was "
    "forgotten. `/tempvoice status` lists the ones it knows about."
)
NOT_AN_ID = (
    "**{given}** is not a channel id, so nothing was forgotten. Right-click the channel and "
    "choose Copy Channel ID, or read the id out of `/tempvoice status`."
)
LOBBY_FORGOTTEN = (
    "Black Bloc has forgotten **{channel_id}** — joining it no longer makes anybody a temporary "
    "channel."
)


async def forget_creator(bot: Any, guild: Any, channel_id: int, actor: Any = None) -> bool:
    """Stop treating one channel id as join-to-create; False when it was not one."""
    ids = list(bot.store.get(guild.id, "tempvoice_creator_ids") or [])
    if channel_id not in ids:
        return False
    ids.remove(channel_id)
    await bot.store.set(guild.id, "tempvoice_creator_ids", ids, by=getattr(actor, "id", None))
    await log_action(
        bot,
        guild,
        "tempvoice.creator_removed",
        actor=actor,
        details={"channel_id": channel_id},
    )
    return True


def channel_name(template: str, member_name: str, saved: str | None = None) -> str:
    """A spawned channel's name: the member's remembered one, else the rendered template."""
    name = (saved or "").strip()
    if not name:
        try:
            name = template.format(user=member_name).strip()
        except Exception:
            log.warning("temp voice: the name template %r could not be rendered", template)
            name = TEMPVOICE_NAME_TEMPLATE.format(user=member_name)
    return name[:NAME_LIMIT] or TEMPVOICE_NAME_TEMPLATE.format(user=member_name)[:NAME_LIMIT]


def same_lobby_name(name: Any, wanted: Any) -> bool:
    return str(name or "").strip().casefold() == str(wanted or "").strip().casefold()


def lobbies_by_name(category: Any, wanted: Any, known: Any = ()) -> list[Any]:
    """Voice channels in the category that carry the lobby's name and are not in the id list."""
    ids = {int(channel_id) for channel_id in known}
    return [
        channel
        for channel in (getattr(category, "voice_channels", None) or ())
        if int(channel.id) not in ids and same_lobby_name(getattr(channel, "name", ""), wanted)
    ]


def bottom_position(positions: Any) -> int:
    values = [int(p) for p in positions]
    return max(values) + 1 if values else 0


def creator_position(afk_position: int | None, fallback: int) -> int:
    """Taking the AFK channel's own slot puts the new channel directly above it."""
    if afk_position is None:
        return max(fallback, 0)
    return max(afk_position, 0)


def spawn_position(creator: int) -> int:
    return max(creator, 0) + 1


def parse_limit(raw: str) -> int | None:
    text = raw.strip()
    if not text.isdigit():
        return None
    value = int(text)
    return value if 0 <= value <= 99 else None


def is_panel_owner(owner_id: Any, clicker_id: Any) -> bool:
    return int(owner_id) == int(clicker_id)


def may_use_voice(role_id: Any, member: Any) -> bool:
    if not role_id:
        return True
    return any(getattr(role, "id", None) == role_id for role in getattr(member, "roles", ()))


def pick_row(rows: Any, user_id: int, here_id: Any, *, owner_only: bool = True) -> Any:
    """The channel a `/voice` command acts on: the one you are in, else the one you own."""
    connected = None
    if here_id is not None:
        connected = next((r for r in rows if int(r["channel_id"]) == int(here_id)), None)
    if not owner_only:
        return connected
    if connected is not None and int(connected["owner_id"]) == int(user_id):
        return connected
    return next((r for r in rows if int(r["owner_id"]) == int(user_id)), None)


def not_owner_message(owner_id: int) -> str:
    return (
        f"This panel belongs to <@{owner_id}>, so nothing was changed. Make your own channel by "
        "joining the join-to-create channel, or ask them to use the Permit button."
    )


def is_stale(created_at: Any, now: datetime, grace_seconds: int) -> bool:
    """An empty channel old enough to delete; an unreadable timestamp counts as old."""
    started = parse_ts(created_at)
    if started is None:
        return True
    return (now - started).total_seconds() >= grace_seconds


def panel_id(action: str) -> str:
    return f"{PANEL_PREFIX}:{action}"


def channel_lock(bot: Any, channel_id: int) -> asyncio.Lock:
    locks = getattr(bot, LOCKS_ATTR, None)
    if locks is None:
        locks = {}
        setattr(bot, LOCKS_ATTR, locks)
    lock = locks.get(channel_id)
    if lock is None:
        lock = locks[channel_id] = asyncio.Lock()
    return lock


def connected_ids(channel: Any) -> set[int]:
    """Who Discord says is in the voice channel right now."""
    return {int(user_id) for user_id in getattr(channel, "voice_states", {})}


def category_overwrites(category: Any) -> dict[Any, Any]:
    """A copy of the category's own overwrites, so a new channel keeps what the category says."""
    found: dict[Any, Any] = {}
    for target, overwrite in (getattr(category, "overwrites", None) or {}).items():
        found[target] = discord.PermissionOverwrite(**dict(overwrite))
    return found


def allow_join(overwrites: dict[Any, Any], targets: Any, **extra: Any) -> dict[Any, Any]:
    """Let each target see and connect, on top of whatever the category already gave them."""
    for target in targets:
        if target is None:
            continue
        overwrite = overwrites.get(target) or discord.PermissionOverwrite()
        overwrite.view_channel = True
        overwrite.connect = True
        for name, value in extra.items():
            setattr(overwrite, name, value)
        overwrites[target] = overwrite
    return overwrites


def creator_overwrites(category: Any, allow: Any = (), me: Any = None) -> dict[Any, Any]:
    found = allow_join(category_overwrites(category), allow)
    if me is not None:
        allow_join(found, [me], manage_channels=True, move_members=True)
    return found


def owner_overwrites(
    guild: Any,
    member: Any,
    *,
    locked: bool = False,
    hidden: bool = False,
    category: Any = None,
    allow: Any = (),
    me: Any = None,
) -> Any:
    found = category_overwrites(category)
    everyone = found.get(guild.default_role) or discord.PermissionOverwrite()
    if locked:
        everyone.connect = False
    if hidden:
        everyone.view_channel = False
    found[guild.default_role] = everyone
    allow_join(found, allow)
    if me is not None:
        allow_join(found, [me], manage_channels=True, move_members=True)
    found[member] = discord.PermissionOverwrite(
        view_channel=True,
        connect=True,
        manage_channels=True,
        move_members=True,
        mute_members=True,
        deafen_members=True,
    )
    return found


def roles_sentence(roles: Any) -> str:
    names = [f"**{getattr(role, 'name', role)}**" for role in roles]
    return ", ".join(names) if names else "everyone the category already lets in"


def panel_text(member: Any, channel: Any, *, elsewhere: bool = False) -> str:
    first = f"Controls for <#{channel.id}>\n" if elsewhere else ""
    return (
        f"{first}**{member.display_name}'s channel** — the buttons below belong to "
        f"<@{member.id}>. Rename it, cap it, lock it, hide it, or hand it to someone else."
    )


def panel_home(bot: Any, channel: Any) -> Any:
    """The panel goes in the voice chat, or in the test channel while the guard would refuse it."""
    guard = getattr(bot, "guard", None)
    if guard is None or guard.allows_channel(channel.id):
        return channel
    return bot.get_channel(guard.test_channel_id) if guard.test_channel_id else None


def own_channel(bot: Any, channel_id: Any) -> None:
    """Tell the test-mode guard this is one of Black Bloc's own channels."""
    guard = getattr(bot, "guard", None)
    if guard is not None:
        guard.own_channel(channel_id)


def disown_channel(bot: Any, channel_id: Any) -> None:
    guard = getattr(bot, "guard", None)
    if guard is not None:
        guard.disown_channel(channel_id)


async def add_channel(
    db: Any, channel_id: int, guild_id: int, owner_id: int, creator_id: int
) -> None:
    await db.conn.execute(
        "INSERT OR REPLACE INTO tempvoice_channels(channel_id, guild_id, owner_id, creator_id, "
        "created_at) VALUES (?, ?, ?, ?, ?)",
        (channel_id, guild_id, owner_id, creator_id, now_iso()),
    )
    await db.conn.commit()


async def get_row(db: Any, channel_id: int) -> Any:
    cur = await db.conn.execute(
        "SELECT * FROM tempvoice_channels WHERE channel_id = ?", (channel_id,)
    )
    return await cur.fetchone()


async def rows_for_guild(db: Any, guild_id: int) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT * FROM tempvoice_channels WHERE guild_id = ? ORDER BY channel_id", (guild_id,)
    )
    return list(await cur.fetchall())


async def delete_row(db: Any, channel_id: int) -> bool:
    cur = await db.conn.execute(
        "DELETE FROM tempvoice_channels WHERE channel_id = ?", (channel_id,)
    )
    await db.conn.commit()
    return cur.rowcount > 0


async def get_row_by_panel(db: Any, message_id: int) -> Any:
    cur = await db.conn.execute(
        "SELECT * FROM tempvoice_channels WHERE panel_message_id = ?", (message_id,)
    )
    return await cur.fetchone()


async def set_panel_message(
    db: Any, channel_id: int, message_id: int, panel_channel_id: int | None = None
) -> None:
    await db.conn.execute(
        "UPDATE tempvoice_channels SET panel_message_id = ?, panel_channel_id = ? "
        "WHERE channel_id = ?",
        (message_id, panel_channel_id, channel_id),
    )
    await db.conn.commit()


async def set_owner(db: Any, channel_id: int, owner_id: int) -> None:
    await db.conn.execute(
        "UPDATE tempvoice_channels SET owner_id = ? WHERE channel_id = ?", (owner_id, channel_id)
    )
    await db.conn.commit()


async def get_prefs(db: Any, user_id: int) -> Any:
    cur = await db.conn.execute("SELECT * FROM tempvoice_prefs WHERE user_id = ?", (user_id,))
    return await cur.fetchone()


async def save_prefs(
    db: Any,
    user_id: int,
    *,
    name: str | None = None,
    user_limit: int | None = None,
    locked: bool | None = None,
    hidden: bool | None = None,
    bitrate: int | None = None,
    region: str | None = None,
    permitted_ids: str | None = None,
    banned_ids: str | None = None,
) -> None:
    """Remember one setting for next time; the others keep whatever they already were."""
    row = await get_prefs(db, user_id)
    current: dict[str, Any] = {
        "name": None,
        "user_limit": None,
        "locked": 0,
        "hidden": 0,
        "bitrate": None,
        "region": None,
        "permitted_ids": None,
        "banned_ids": None,
    }
    if row is not None:
        current = {key: pref(row, key) for key in current}
    given = {
        "name": name,
        "user_limit": user_limit,
        "locked": locked,
        "hidden": hidden,
        "bitrate": bitrate,
        "region": region,
        "permitted_ids": permitted_ids,
        "banned_ids": banned_ids,
    }
    merged = {key: (current[key] if value is None else value) for key, value in given.items()}
    await db.conn.execute(
        "INSERT OR REPLACE INTO tempvoice_prefs(user_id, name, user_limit, locked, hidden, "
        "bitrate, region, permitted_ids, banned_ids) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            user_id,
            merged["name"],
            merged["user_limit"],
            int(bool(merged["locked"])),
            int(bool(merged["hidden"])),
            merged["bitrate"],
            merged["region"],
            merged["permitted_ids"],
            merged["banned_ids"],
        ),
    )
    await db.conn.commit()


async def clear_prefs(db: Any, user_id: int) -> bool:
    """Forget everything remembered for one member; False when there was nothing to forget."""
    cur = await db.conn.execute(
        "DELETE FROM tempvoice_prefs WHERE user_id = ?", (int(user_id),)
    )
    await db.conn.commit()
    return bool(cur.rowcount)


def id_list(raw: Any) -> list[int]:
    """The member ids in a stored JSON list, skipping anything that is not one."""
    found = raw
    if isinstance(raw, str):
        try:
            found = json.loads(raw)
        except ValueError:
            return []
    if not isinstance(found, list):
        return []
    ids: list[int] = []
    for item in found:
        try:
            value = int(item)
        except (TypeError, ValueError):
            continue
        if value not in ids:
            ids.append(value)
    return ids


def with_member(raw: Any, user_id: Any, keep: bool) -> str:
    ids = [found for found in id_list(raw) if found != int(user_id)]
    if keep:
        ids.append(int(user_id))
    return json.dumps(ids[-MEMBER_MEMORY_MAX:])


async def remember_access(db: Any, owner_id: Any, target_id: Any, state: str) -> None:
    row = await get_prefs(db, int(owner_id))
    await save_prefs(
        db,
        int(owner_id),
        permitted_ids=with_member(pref(row, "permitted_ids"), target_id, state == PERMITTED),
        banned_ids=with_member(pref(row, "banned_ids"), target_id, state == BANNED),
    )


def apply_remembered_members(
    overwrites: dict[Any, Any], guild: Any, permitted: Any, banned: Any, owner_id: Any
) -> dict[Any, Any]:
    """Put back who this owner let in and who they shut out; anyone no longer here is skipped."""
    wanted = [(user_id, True) for user_id in permitted] + [(user_id, False) for user_id in banned]
    for user_id, allowed in wanted:
        if int(user_id) == int(owner_id):
            continue
        member = guild.get_member(int(user_id))
        if member is None:
            continue
        overwrites[member] = discord.PermissionOverwrite(
            view_channel=allowed, connect=allowed
        )
    return overwrites


def pref(row: Any, key: str) -> Any:
    if row is None:
        return None
    try:
        return row[key]
    except (IndexError, KeyError):
        return None


def creator_spot(bot: Any, guild: Any) -> tuple[Any, int, str]:
    guard = getattr(bot, "guard", None)
    if guard is not None:
        test_channel = bot.get_channel(guard.test_channel_id) if guard.test_channel_id else None
        if test_channel is None:
            return None, 0, "no_test_channel"
        category = test_channel.category
        voice = list(getattr(category, "voice_channels", ())) if category is not None else []
        return category, bottom_position(c.position for c in voice), "test_category"
    afk = getattr(guild, "afk_channel", None)
    if afk is None:
        afk = next((c for c in guild.voice_channels if c.name == AFK_FALLBACK_NAME), None)
    if afk is not None:
        return afk.category, creator_position(afk.position, 0), "above_afk"
    return None, bottom_position(c.position for c in guild.voice_channels), "bottom"


def where_sentence(where: str) -> str:
    if where == "test_category":
        return (
            "Test mode is on, so it went in the test channel's category — join it there to "
            "try it. Run `/tempvoice setup` again once test mode is off and it will go "
            "directly above the AFK channel."
        )
    if where == "above_afk":
        return "It sits directly above the AFK channel, as asked."
    return (
        "Black Bloc could not find an AFK channel to sit above, so it went to the bottom of "
        "the list — drag it where you want it."
    )


def may_act_in(bot: Any, channel: Any) -> bool:
    guard = getattr(bot, "guard", None)
    if guard is None:
        return True
    test_channel = bot.get_channel(guard.test_channel_id) if guard.test_channel_id else None
    if test_channel is None:
        return False
    return getattr(channel, "category_id", None) == getattr(test_channel, "category_id", None)


def join_roles(bot: Any, guild: Any) -> list[Any]:
    """The allowed role and every resolved staff role, as role objects."""
    found = list(bot.store.staff_roles(guild))
    role_id = bot.store.get(guild.id, "tempvoice_allowed_role_id")
    if not role_id:
        return found
    allowed = guild.get_role(role_id)
    if allowed is None:
        log.warning(
            "temp voice: the allowed role %s is gone, so it was left out of the overwrites",
            role_id,
        )
        return found
    if any(getattr(role, "id", None) == role_id for role in found):
        return found
    return [allowed, *found]


async def repair_creator_channel(
    bot: Any, guild: Any, actor: Any, live: list[Any], wanted: str, *, adopted: bool = False
) -> tuple[str, str]:
    """Put the lobby the server already has back to its name and its own overwrites."""
    channel = live[0]
    if not may_act_in(bot, channel):
        return (
            "outside_test_category",
            OUTSIDE_TEST_CATEGORY.format(where=channel.mention),
        )
    allow = join_roles(bot, guild)
    try:
        await channel.edit(
            name=wanted,
            overwrites=creator_overwrites(channel.category, allow, getattr(guild, "me", None)),
            reason="Black Bloc temp voice: repairing the join-to-create channel",
        )
    except discord.HTTPException as exc:
        log.warning("temp voice: could not repair the lobby %s: %s", channel.id, exc)
        await log_action(
            bot,
            guild,
            "tempvoice.repair_failed",
            actor=actor,
            details={"channel_id": channel.id, "reason": f"{type(exc).__name__}: {exc}"},
        )
        return ("repair_refused", CANNOT_REPAIR.format(where=channel.mention))
    await log_action(
        bot,
        guild,
        "tempvoice.repair",
        actor=actor,
        details={"channel_id": channel.id, "name": wanted},
    )
    said = (ADOPTED if adopted else REPAIRED).format(
        where=channel.mention, name=wanted, who=roles_sentence(allow)
    )
    if len(live) > 1:
        said += EXTRA_LOBBIES.format(extras=", ".join(f"<#{other.id}>" for other in live[1:]))
    return ("adopted" if adopted else "repaired", said)


async def adopt_creator_channel(
    bot: Any, guild: Any, actor: Any, found: list[Any], wanted: str
) -> tuple[str, str]:
    """Store a lobby that carries the name but was never written down, then repair it."""
    ids = list(bot.store.get(guild.id, "tempvoice_creator_ids") or [])
    ids.extend(channel.id for channel in found if channel.id not in ids)
    await bot.store.set(
        guild.id, "tempvoice_creator_ids", ids, by=getattr(actor, "id", actor)
    )
    await log_action(
        bot,
        guild,
        "tempvoice.adopt",
        actor=actor,
        details={"channel_ids": [channel.id for channel in found], "name": wanted},
    )
    return await repair_creator_channel(bot, guild, actor, found, wanted, adopted=True)


async def make_creator_channel(
    bot: Any, guild: Any, actor: Any, name: str | None = None
) -> tuple[str, str]:
    """Set up or repair join-to-create, for slash and web alike: (what happened, what to say)."""
    by = getattr(actor, "id", actor)
    wanted = (name or "").strip()[:NAME_LIMIT]
    if wanted:
        await bot.store.set(guild.id, "tempvoice_creator_name", wanted, by=by)
    else:
        wanted = bot.store.get(guild.id, "tempvoice_creator_name")
    ids = list(bot.store.get(guild.id, "tempvoice_creator_ids") or [])
    live = [guild.get_channel(cid) for cid in ids if guild.get_channel(cid) is not None]
    if live:
        return await repair_creator_channel(bot, guild, actor, live, wanted)
    category, position, where = creator_spot(bot, guild)
    if where == "no_test_channel":
        return ("no_test_channel", NO_TEST_CHANNEL)
    unknown = lobbies_by_name(category, wanted, ids)
    if unknown:
        return await adopt_creator_channel(bot, guild, actor, unknown, wanted)
    allow = join_roles(bot, guild)
    try:
        channel = await guild.create_voice_channel(
            wanted,
            category=category,
            position=position,
            overwrites=creator_overwrites(category, allow, getattr(guild, "me", None)),
            reason="Black Bloc temp voice: join-to-create",
        )
    except discord.HTTPException as exc:
        log.warning("temp voice: setup could not create the creator channel: %s", exc)
        return ("refused", CANNOT_CREATE)
    if channel.id not in ids:
        ids.append(channel.id)
    await bot.store.set(guild.id, "tempvoice_creator_ids", ids, by=by)
    await log_action(
        bot,
        guild,
        "tempvoice.setup",
        actor=actor,
        details={"channel_id": channel.id, "placed": where, "name": wanted},
    )
    return (
        "created",
        f"**{channel.name}** is ready — {channel.mention}, and {roles_sentence(allow)} can "
        f"see it and join it. {where_sentence(where)}",
    )


class Target(NamedTuple):
    row: Any
    channel: Any


def temp_channel(interaction: discord.Interaction, channel_id: Any) -> Any:
    guild = getattr(interaction, "guild", None)
    found = guild.get_channel(int(channel_id)) if guild is not None else None
    if found is None:
        found = interaction.client.get_channel(int(channel_id))
    return found


async def panel_row(interaction: discord.Interaction, channel_id: int | None) -> Any:
    """The row this click belongs to: the id it carries, else the panel message, else the chat."""
    db = interaction.client.db
    if channel_id is not None:
        return await get_row(db, int(channel_id))
    message = getattr(interaction, "message", None)
    if message is not None:
        row = await get_row_by_panel(db, message.id)
        if row is not None:
            return row
    return await get_row(db, interaction.channel_id)


async def panel_context(
    interaction: discord.Interaction, *, owner_only: bool = True, channel_id: int | None = None
) -> Target | None:
    """This click's temp channel and its row, or None once the clicker has been answered."""
    bot = interaction.client
    guard = getattr(bot, "guard", None)
    if guard is not None and not guard.allows_channel(interaction.channel_id):
        await interaction.response.send_message(guard.refusal_message(), ephemeral=True)
        return None
    if not bot.db.is_connected:
        await interaction.response.send_message(DB_UNAVAILABLE, ephemeral=True)
        return None
    row = await panel_row(interaction, channel_id)
    if row is None:
        await interaction.response.send_message(NOT_A_TEMP_CHANNEL, ephemeral=True)
        return None
    if owner_only and not is_panel_owner(row["owner_id"], interaction.user.id):
        await interaction.response.send_message(
            not_owner_message(row["owner_id"]),
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        return None
    channel = temp_channel(interaction, row["channel_id"])
    if channel is None:
        await interaction.response.send_message(CHANNEL_GONE, ephemeral=True)
        return None
    return Target(row, channel)


async def panel_log(
    interaction: discord.Interaction, kind: str, channel_id: Any, **details: Any
) -> None:
    await log_action(
        interaction.client,
        interaction.guild,
        f"tempvoice.{kind}",
        actor=interaction.user,
        details={"channel_id": int(channel_id)} | details,
    )


async def answer(interaction: discord.Interaction, text: str) -> None:
    if interaction.response.is_done():
        await interaction.followup.send(
            text, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
        )
        return
    await interaction.response.send_message(
        text, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
    )


def rate_limited(exc: Any) -> bool:
    return isinstance(exc, discord.RateLimited) or getattr(exc, "status", None) == 429


def already_message(permission: str, was_off: bool) -> str:
    if permission == "connect":
        state = "locked" if was_off else "unlocked"
    else:
        state = "hidden" if was_off else "visible to everyone"
    return f"This channel is already {state}, so nothing was changed."


async def move_out(interaction: discord.Interaction, target: Any) -> bool:
    try:
        await target.move_to(None, reason="Black Bloc temp voice")
    except discord.HTTPException as exc:
        log.warning("temp voice: could not move %s out: %s", target.id, exc)
        return False
    return True


async def do_rename(interaction: discord.Interaction, channel: Any, row: Any, wanted: str) -> str:
    wanted = (wanted or "").strip()[:NAME_LIMIT]
    if not wanted:
        return "A channel needs a name, so nothing was changed."
    try:
        await channel.edit(name=wanted, reason="Black Bloc temp voice")
    except (discord.HTTPException, discord.RateLimited) as exc:
        log.warning("temp voice: rename refused in %s: %s", channel.id, exc)
        await panel_log(interaction, "rename_failed", channel.id, reason=str(exc))
        return RENAMED_TOO_OFTEN if rate_limited(exc) else CANNOT_EDIT
    await save_prefs(interaction.client.db, row["owner_id"], name=wanted)
    await panel_log(interaction, "rename", channel.id, name=wanted)
    return f"Renamed to **{wanted}**, and remembered for next time."


async def do_limit(interaction: discord.Interaction, channel: Any, row: Any, value: int) -> str:
    try:
        await channel.edit(user_limit=value, reason="Black Bloc temp voice")
    except discord.HTTPException as exc:
        log.warning("temp voice: limit refused in %s: %s", channel.id, exc)
        await panel_log(interaction, "limit_failed", channel.id, reason=str(exc))
        return CANNOT_EDIT
    await save_prefs(interaction.client.db, row["owner_id"], user_limit=value)
    await panel_log(interaction, "limit", channel.id, user_limit=value)
    return "Anyone can join now." if value == 0 else f"Capped at **{value}** people."


async def do_privacy(
    interaction: discord.Interaction,
    channel: Any,
    row: Any,
    permission: str,
    want: bool | None = None,
) -> str:
    everyone = channel.guild.default_role
    async with channel_lock(interaction.client, channel.id):
        overwrite = channel.overwrites_for(everyone)
        was_off = getattr(overwrite, permission) is False
        turning_off = (not was_off) if want is None else want
        if turning_off == was_off:
            return already_message(permission, was_off)
        setattr(overwrite, permission, False if turning_off else None)
        try:
            await channel.set_permissions(
                everyone, overwrite=overwrite, reason="Black Bloc temp voice"
            )
        except discord.HTTPException as exc:
            log.warning("temp voice: %s refused in %s: %s", permission, channel.id, exc)
            await panel_log(interaction, "privacy_failed", channel.id, reason=str(exc))
            return CANNOT_EDIT
    if permission == "connect":
        await save_prefs(interaction.client.db, row["owner_id"], locked=turning_off)
        said = "Locked — nobody new may join." if turning_off else "Unlocked — anyone may join."
        kind = "lock" if turning_off else "unlock"
    else:
        await save_prefs(interaction.client.db, row["owner_id"], hidden=turning_off)
        said = (
            "Hidden — only people already in it can see it."
            if turning_off
            else "Visible again to everyone."
        )
        kind = "hide" if turning_off else "show"
    await panel_log(interaction, kind, channel.id)
    return said


async def do_kick(interaction: discord.Interaction, channel: Any, row: Any, target: Any) -> str:
    if target.id not in connected_ids(channel):
        return NOT_IN_CHANNEL.format(name=target.display_name)
    if not await move_out(interaction, target):
        return CANNOT_EDIT
    await panel_log(interaction, "kick", channel.id, target_id=target.id)
    return f"Moved **{target.display_name}** out of the channel."


async def do_ban(interaction: discord.Interaction, channel: Any, row: Any, target: Any) -> str:
    try:
        await channel.set_permissions(
            target, connect=False, view_channel=False, reason="Black Bloc temp voice: banned"
        )
    except discord.HTTPException as exc:
        log.warning("temp voice: ban refused in %s: %s", channel.id, exc)
        await panel_log(interaction, "ban_failed", channel.id, target_id=target.id, reason=str(exc))
        return CANNOT_EDIT
    if target.id in connected_ids(channel):
        await move_out(interaction, target)
    await panel_log(interaction, "ban", channel.id, target_id=target.id)
    await remember_access(interaction.client.db, row["owner_id"], target.id, BANNED)
    return (
        f"**{target.display_name}** can no longer join this channel, now or in your next one. "
        "Unban undoes it."
    )


async def do_permit(interaction: discord.Interaction, channel: Any, row: Any, target: Any) -> str:
    try:
        await channel.set_permissions(
            target, connect=True, view_channel=True, reason="Black Bloc temp voice: permitted"
        )
    except discord.HTTPException as exc:
        log.warning("temp voice: permit refused in %s: %s", channel.id, exc)
        await panel_log(
            interaction, "permit_failed", channel.id, target_id=target.id, reason=str(exc)
        )
        return CANNOT_EDIT
    await panel_log(interaction, "permit", channel.id, target_id=target.id)
    await remember_access(interaction.client.db, row["owner_id"], target.id, PERMITTED)
    return f"**{target.display_name}** can join this channel now, and your next one."


async def do_forget_member(
    interaction: discord.Interaction, channel: Any, row: Any, target: Any, kind: str
) -> str:
    """Undo a ban or a permit: the member's own connect/view overwrite goes back to the default."""
    async with channel_lock(interaction.client, channel.id):
        overwrite = channel.overwrites_for(target)
        overwrite.connect = None
        overwrite.view_channel = None
        empty = bool(getattr(overwrite, "is_empty", bool)())
        try:
            await channel.set_permissions(
                target,
                overwrite=None if empty else overwrite,
                reason=f"Black Bloc temp voice: {kind}",
            )
        except discord.HTTPException as exc:
            log.warning("temp voice: %s refused in %s: %s", kind, channel.id, exc)
            await panel_log(
                interaction, f"{kind}_failed", channel.id, target_id=target.id, reason=str(exc)
            )
            return CANNOT_EDIT
    await panel_log(interaction, kind, channel.id, target_id=target.id)
    await remember_access(interaction.client.db, row["owner_id"], target.id, FORGOTTEN)
    if kind == "unban":
        return f"**{target.display_name}** may join this channel again."
    return (
        f"**{target.display_name}** no longer has their own way in — this channel's own rules "
        "apply to them again."
    )


def guild_bitrate_ceiling(guild: Any) -> int:
    try:
        return int(getattr(guild, "bitrate_limit", 0)) or MAX_BITRATE * 1000
    except (TypeError, ValueError):
        return MAX_BITRATE * 1000


def clamp_bitrate(kbps: Any, ceiling: Any) -> int:
    """What Discord will accept: the asked-for kbps in bits, capped by the guild's boost tier."""
    try:
        wanted = int(kbps)
    except (TypeError, ValueError):
        wanted = MAX_BITRATE
    wanted = min(max(wanted, MIN_BITRATE), MAX_BITRATE) * 1000
    try:
        top = int(ceiling)
    except (TypeError, ValueError):
        top = MAX_BITRATE * 1000
    return min(wanted, max(top, MIN_BITRATE * 1000))


def region_choices(current: str) -> list[str]:
    text = (current or "").strip().lower()
    return [name for name in VOICE_REGIONS if text in name][:25]


def member_lists(overwrites: Any, owner_id: Any, role_ids: Any) -> tuple[list[int], list[int]]:
    """Who this channel lets in by name and who it shuts out by name, from its own overwrites."""
    permitted: list[int] = []
    banned: list[int] = []
    skip = {int(owner_id)} | {int(role_id) for role_id in role_ids}
    for target, overwrite in (overwrites or {}).items():
        target_id = int(getattr(target, "id", 0))
        if target_id in skip:
            continue
        if overwrite.connect is False:
            banned.append(target_id)
        elif overwrite.connect is True:
            permitted.append(target_id)
    return permitted, banned


def mentions(ids: Any) -> str:
    return ", ".join(f"<@{user_id}>" for user_id in ids) or "nobody"


def info_lines(channel: Any, row: Any, role_ids: Any) -> list[str]:
    everyone = channel.overwrites_for(channel.guild.default_role)
    permitted, banned = member_lists(getattr(channel, "overwrites", {}), row["owner_id"], role_ids)
    limit = int(getattr(channel, "user_limit", 0) or 0)
    bitrate = int(getattr(channel, "bitrate", 0) or 0)
    cap = "no limit" if limit == 0 else f"{limit} people"
    speed = f"{bitrate // 1000} kbps" if bitrate else "whatever the server gives it"
    return [
        f"**channel** — <#{channel.id}>",
        f"**owner** — <@{row['owner_id']}>",
        f"**limit** — {cap}",
        f"**locked** — {'yes' if everyone.connect is False else 'no'}",
        f"**hidden** — {'yes' if everyone.view_channel is False else 'no'}",
        f"**bitrate** — {speed}",
        f"**region** — {getattr(channel, 'rtc_region', None) or 'automatic'}",
        f"**let in by name** — {mentions(permitted)}",
        f"**kept out by name** — {mentions(banned)}",
    ]


def remembered_lines(prefs: Any) -> list[str]:
    """What the next channel this member makes will start from."""
    if prefs is None:
        return [
            "",
            "**remembered for next time** — nothing yet. Anything you change here is kept and "
            "put back on your next channel.",
        ]
    limit = pref(prefs, "user_limit")
    bitrate = pref(prefs, "bitrate")
    region = pref(prefs, "region")
    return [
        "",
        "**remembered for next time**",
        f"• name — {pref(prefs, 'name') or 'the server default'}",
        f"• limit — {'no limit' if not limit else f'{int(limit)} people'}",
        f"• locked — {'yes' if pref(prefs, 'locked') else 'no'}"
        f" · hidden — {'yes' if pref(prefs, 'hidden') else 'no'}",
        f"• bitrate — {f'{int(bitrate) // 1000} kbps' if bitrate else 'whatever the server gives'}",
        f"• region — {'automatic' if not region or region == AUTO_REGION else region}",
        f"• let in by name — {mentions(id_list(pref(prefs, 'permitted_ids')))}",
        f"• kept out by name — {mentions(id_list(pref(prefs, 'banned_ids')))}",
        "`/voice reset` forgets all of it.",
    ]


async def do_bitrate(interaction: discord.Interaction, channel: Any, row: Any, kbps: int) -> str:
    bits = clamp_bitrate(kbps, guild_bitrate_ceiling(channel.guild))
    try:
        await channel.edit(bitrate=bits, reason="Black Bloc temp voice")
    except discord.HTTPException as exc:
        log.warning("temp voice: bitrate refused in %s: %s", channel.id, exc)
        await panel_log(interaction, "bitrate_failed", channel.id, reason=str(exc))
        return CANNOT_EDIT
    await save_prefs(interaction.client.db, row["owner_id"], bitrate=bits)
    await panel_log(interaction, "bitrate", channel.id, bitrate=bits)
    said = f"Bitrate set to **{bits // 1000} kbps**, and remembered for next time."
    if bits < min(int(kbps), MAX_BITRATE) * 1000:
        said += " That is as high as this server's boost level allows."
    return said


async def do_region(interaction: discord.Interaction, channel: Any, row: Any, region: str) -> str:
    wanted = (region or AUTO_REGION).strip().lower()
    try:
        await channel.edit(
            rtc_region=None if wanted == AUTO_REGION else wanted, reason="Black Bloc temp voice"
        )
    except (discord.HTTPException, ValueError, TypeError) as exc:
        log.warning("temp voice: region %s refused in %s: %s", wanted, channel.id, exc)
        await panel_log(interaction, "region_failed", channel.id, region=wanted, reason=str(exc))
        return CANNOT_SET_REGION.format(region=wanted)
    await panel_log(interaction, "region", channel.id, region=wanted)
    await save_prefs(interaction.client.db, row["owner_id"], region=wanted)
    if wanted == AUTO_REGION:
        return "Voice region is **automatic** again — Discord picks the closest server."
    return f"Voice region set to **{wanted}**, and remembered for next time."


async def do_transfer(interaction: discord.Interaction, channel: Any, row: Any, target: Any) -> str:
    async with channel_lock(interaction.client, channel.id):
        fresh = await get_row(interaction.client.db, channel.id)
        if fresh is None:
            return NOT_A_TEMP_CHANNEL
        if int(fresh["owner_id"]) != int(row["owner_id"]):
            return CLAIM_LOST
        await hand_over(interaction.client, channel, fresh["owner_id"], target)
        await panel_log(
            interaction, "transfer", channel.id, target_id=target.id, from_id=fresh["owner_id"]
        )
    return f"**{target.display_name}** owns this channel now."


async def do_claim(interaction: discord.Interaction, channel: Any, row: Any) -> str:
    async with channel_lock(interaction.client, channel.id):
        fresh = await get_row(interaction.client.db, channel.id)
        if fresh is None:
            return NOT_A_TEMP_CHANNEL
        owner_id = fresh["owner_id"]
        if is_panel_owner(owner_id, interaction.user.id):
            return "You already own this channel, so nothing changed."
        if int(owner_id) != int(row["owner_id"]):
            return CLAIM_LOST
        here = connected_ids(channel)
        if interaction.user.id not in here:
            return CLAIM_NEEDS_CONNECTION
        if owner_id in here:
            return OWNER_STILL_HERE.format(owner_id=owner_id)
        await hand_over(interaction.client, channel, owner_id, interaction.user)
        await panel_log(interaction, "claim", channel.id, from_id=owner_id)
    return "This channel is yours now."


class RenameModal(AnswersErrors, discord.ui.Modal, title="Rename this channel"):
    name = discord.ui.TextInput(label="New name", max_length=NAME_LIMIT)

    def __init__(self, channel_id: int | None = None) -> None:
        super().__init__()
        self.channel_id = channel_id

    async def on_submit(self, interaction: discord.Interaction) -> None:
        found = await panel_context(interaction, channel_id=self.channel_id)
        if found is None:
            return
        await interaction.response.defer(ephemeral=True)
        await answer(
            interaction, await do_rename(interaction, found.channel, found.row, str(self.name))
        )


class LimitModal(AnswersErrors, discord.ui.Modal, title="How many people?"):
    limit = discord.ui.TextInput(label="0 to 99 (0 means no limit)", max_length=2)

    def __init__(self, channel_id: int | None = None) -> None:
        super().__init__()
        self.channel_id = channel_id

    async def on_submit(self, interaction: discord.Interaction) -> None:
        found = await panel_context(interaction, channel_id=self.channel_id)
        if found is None:
            return
        await interaction.response.defer(ephemeral=True)
        value = parse_limit(str(self.limit))
        if value is None:
            await answer(
                interaction,
                "That is not a number between 0 and 99, so nothing was changed. Type a whole "
                "number — 0 lets anyone in.",
            )
            return
        await answer(interaction, await do_limit(interaction, found.channel, found.row, value))


MEMBER_ACTIONS = {
    "kick": do_kick,
    "ban": do_ban,
    "permit": do_permit,
    "transfer": do_transfer,
}


class MemberPick(discord.ui.UserSelect):
    def __init__(self, action: str, placeholder: str, channel_id: int | None = None) -> None:
        super().__init__(placeholder=placeholder, min_values=1, max_values=1)
        self.action = action
        self.channel_id = channel_id

    async def callback(self, interaction: discord.Interaction) -> None:
        found = await panel_context(interaction, channel_id=self.channel_id)
        if found is None:
            return
        await interaction.response.defer(ephemeral=True)
        target = self.values[0]
        handler = MEMBER_ACTIONS.get(self.action)
        if handler is None:
            said = await do_forget_member(
                interaction, found.channel, found.row, target, self.action
            )
        else:
            said = await handler(interaction, found.channel, found.row, target)
        await answer(interaction, said)


class MemberPickView(AnswersErrors, discord.ui.View):
    def __init__(self, action: str, placeholder: str, channel_id: int | None = None) -> None:
        super().__init__(timeout=180)
        self.add_item(MemberPick(action, placeholder, channel_id))


async def hand_over(bot: Any, channel: Any, old_owner_id: int, new_owner: Any) -> None:
    """Move the owner overwrite to the new owner and record them on the row."""
    await set_owner(bot.db, channel.id, new_owner.id)
    old = channel.guild.get_member(old_owner_id)
    try:
        if old is not None and old.id != new_owner.id:
            await channel.set_permissions(old, overwrite=None, reason="Black Bloc temp voice")
        await channel.set_permissions(
            new_owner,
            overwrite=owner_overwrites(channel.guild, new_owner)[new_owner],
            reason="Black Bloc temp voice",
        )
    except discord.HTTPException as exc:
        log.warning("temp voice: could not move the owner overwrite in %s: %s", channel.id, exc)


class TempVoicePanel(AnswersErrors, discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(label="Rename", custom_id=panel_id("rename"), row=0)
    async def rename(self, interaction: discord.Interaction, button: Any) -> None:
        found = await panel_context(interaction)
        if found is None:
            return
        await interaction.response.send_modal(RenameModal(found.row["channel_id"]))

    @discord.ui.button(label="Limit", custom_id=panel_id("limit"), row=0)
    async def limit(self, interaction: discord.Interaction, button: Any) -> None:
        found = await panel_context(interaction)
        if found is None:
            return
        await interaction.response.send_modal(LimitModal(found.row["channel_id"]))

    @discord.ui.button(label="Lock / Unlock", custom_id=panel_id("lock"), row=0)
    async def lock(self, interaction: discord.Interaction, button: Any) -> None:
        await self._toggle(interaction, "connect")

    @discord.ui.button(label="Hide / Show", custom_id=panel_id("hide"), row=0)
    async def hide(self, interaction: discord.Interaction, button: Any) -> None:
        await self._toggle(interaction, "view_channel")

    @discord.ui.button(label="Kick", custom_id=panel_id("kick"), row=1)
    async def kick(self, interaction: discord.Interaction, button: Any) -> None:
        await self._pick(interaction, "kick", "Who should leave this channel?")

    @discord.ui.button(label="Ban", custom_id=panel_id("ban"), row=1)
    async def ban(self, interaction: discord.Interaction, button: Any) -> None:
        await self._pick(interaction, "ban", "Who should be kept out of this channel?")

    @discord.ui.button(label="Unban", custom_id=panel_id("unban"), row=1)
    async def unban(self, interaction: discord.Interaction, button: Any) -> None:
        await self._pick(interaction, "unban", "Who should be let back in?")

    @discord.ui.button(label="Permit", custom_id=panel_id("permit"), row=1)
    async def permit(self, interaction: discord.Interaction, button: Any) -> None:
        await self._pick(interaction, "permit", "Who should be let in?")

    @discord.ui.button(label="Unpermit", custom_id=panel_id("unpermit"), row=1)
    async def unpermit(self, interaction: discord.Interaction, button: Any) -> None:
        await self._pick(interaction, "unpermit", "Whose invite should be taken back?")

    @discord.ui.button(label="Transfer", custom_id=panel_id("transfer"), row=2)
    async def transfer(self, interaction: discord.Interaction, button: Any) -> None:
        await self._pick(interaction, "transfer", "Who should own this channel?")

    @discord.ui.button(label="Claim", custom_id=panel_id("claim"), row=2)
    async def claim(self, interaction: discord.Interaction, button: Any) -> None:
        found = await panel_context(interaction, owner_only=False)
        if found is None:
            return
        await interaction.response.defer(ephemeral=True)
        await answer(interaction, await do_claim(interaction, found.channel, found.row))

    async def _pick(self, interaction: discord.Interaction, action: str, placeholder: str) -> None:
        found = await panel_context(interaction)
        if found is None:
            return
        await interaction.response.send_message(
            placeholder,
            view=MemberPickView(action, placeholder, found.row["channel_id"]),
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )

    async def _toggle(self, interaction: discord.Interaction, permission: str) -> None:
        found = await panel_context(interaction)
        if found is None:
            return
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)
        await answer(
            interaction, await do_privacy(interaction, found.channel, found.row, permission)
        )


class TempVoice(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._creator_locks: dict[int, asyncio.Lock] = {}
        self.last_ok_at: str | None = None
        self.last_error: str | None = None

    tempvoice = app_commands.Group(
        name="tempvoice", description="Temporary voice channels people make by joining one"
    )
    voice = app_commands.Group(
        name="voice", description="Change your own temporary voice channel"
    )

    def loop_health(self, name: str) -> tuple[str | None, str | None]:
        if name != "_reconcile_loop":
            return (None, None)
        return (self.last_ok_at, self.last_error)

    async def cog_load(self) -> None:
        self.bot.add_view(TempVoicePanel())
        if not self.bot.db.is_connected:
            return
        await self.reconcile_channels()
        self._reconcile_loop.start()

    async def cog_unload(self) -> None:
        self._reconcile_loop.cancel()

    @tasks.loop(minutes=RECONCILE_MINUTES)
    async def _reconcile_loop(self) -> None:
        if not self.bot.db.is_connected:
            return
        try:
            await self.reconcile_channels()
        except Exception as exc:
            self.last_error = f"{type(exc).__name__}: {exc}"
            log.exception("temp voice: the five-minute reconcile failed")
            return
        self.last_error = None
        self.last_ok_at = now_iso()

    @_reconcile_loop.before_loop
    async def _before_reconcile(self) -> None:
        await self.bot.wait_until_ready()

    @_reconcile_loop.error
    async def _reconcile_stopped(self, exc: BaseException) -> None:
        """The loop stops for the life of the process unless it is started again."""
        self.last_error = f"{type(exc).__name__}: {exc}"
        log.error("temp voice: the reconcile loop stopped; restarting it", exc_info=exc)
        self._reconcile_loop.restart()

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        if not self.bot.db.is_connected:
            return
        await self.reconcile_channels()
        if not self._reconcile_loop.is_running():
            self._reconcile_loop.start()

    async def reconcile_channels(self) -> None:
        """Forget rows whose channel is gone, and delete temp channels nobody is in."""
        now = datetime.now(UTC)
        for guild in list(getattr(self.bot, "guilds", ())):
            for row in await rows_for_guild(self.bot.db, guild.id):
                channel = guild.get_channel(row["channel_id"])
                if channel is None:
                    await delete_row(self.bot.db, row["channel_id"])
                    disown_channel(self.bot, row["channel_id"])
                    log.info("temp voice: forgot channel %s — it is gone", row["channel_id"])
                    continue
                own_channel(self.bot, channel.id)
                if connected_ids(channel):
                    continue
                if not is_stale(row["created_at"], now, RECONCILE_GRACE_SECONDS):
                    continue
                await self._delete_channel(guild, channel, "reconciled")

    @commands.Cog.listener()
    async def on_voice_state_update(
        self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState
    ) -> None:
        if member.bot or not self.bot.db.is_connected:
            return
        left = before.channel
        joined = after.channel
        if left is not None and (joined is None or joined.id != left.id):
            await self._maybe_delete(member.guild, left)
        if joined is not None and (left is None or left.id != joined.id):
            await self._maybe_create(member, joined)

    async def _maybe_delete(self, guild: Any, channel: Any) -> None:
        if await get_row(self.bot.db, channel.id) is None:
            return
        if connected_ids(channel):
            return
        await self._delete_channel(guild, channel, "empty")

    async def _delete_channel(self, guild: Any, channel: Any, reason: str) -> None:
        async with channel_lock(self.bot, channel.id):
            row = await get_row(self.bot.db, channel.id)
            if row is None:
                return
            try:
                await channel.delete(reason="Black Bloc temp voice: nobody left in it")
            except discord.HTTPException as exc:
                log.warning("temp voice: could not delete channel %s: %s", channel.id, exc)
                await log_action(
                    self.bot,
                    guild,
                    "tempvoice.delete_failed",
                    details={
                        "channel_id": channel.id,
                        "reason": f"{type(exc).__name__}: {exc}",
                    },
                )
                return
            await delete_row(self.bot.db, channel.id)
            disown_channel(self.bot, channel.id)
            await log_action(
                self.bot,
                guild,
                "tempvoice.delete",
                target=row["owner_id"],
                details={"channel_id": channel.id, "reason": reason},
            )

    async def _maybe_create(self, member: Any, channel: Any) -> None:
        guild = member.guild
        store = self.bot.store
        if store.get(guild.id, "tempvoice_mode") != "on":
            return
        if channel.id not in (store.get(guild.id, "tempvoice_creator_ids") or []):
            return
        if not self._may_act_in(channel):
            log.warning(
                "temp voice: TEST MODE — ignoring the creator channel %s outside the test "
                "channel's category",
                channel.id,
            )
            return
        async with self._lock(self._creator_locks, channel.id):
            await self._create_for(member, channel)

    async def _create_for(self, member: Any, creator: Any) -> None:
        guild = member.guild
        store = self.bot.store
        role_id = store.get(guild.id, "tempvoice_allowed_role_id")
        if role_id and not any(r.id == role_id for r in getattr(member, "roles", ())):
            await self._turn_away(member, role_id)
            return
        prefs = await get_prefs(self.bot.db, member.id)
        name = channel_name(
            store.get(guild.id, "tempvoice_name_template"),
            member.display_name,
            pref(prefs, "name"),
        )
        remembered = pref(prefs, "bitrate")
        extra: dict[str, Any] = {}
        if remembered:
            extra["bitrate"] = clamp_bitrate(
                int(remembered) // 1000, guild_bitrate_ceiling(guild)
            )
        region = pref(prefs, "region")
        if region and region != AUTO_REGION:
            extra["rtc_region"] = region
        overwrites = apply_remembered_members(
            owner_overwrites(
                guild,
                member,
                locked=bool(pref(prefs, "locked")),
                hidden=bool(pref(prefs, "hidden")),
                category=creator.category,
                allow=self._join_roles(guild),
                me=getattr(guild, "me", None),
            ),
            guild,
            id_list(pref(prefs, "permitted_ids")),
            id_list(pref(prefs, "banned_ids")),
            member.id,
        )
        try:
            channel = await guild.create_voice_channel(
                name,
                category=creator.category,
                position=spawn_position(creator.position),
                overwrites=overwrites,
                user_limit=int(pref(prefs, "user_limit") or 0),
                reason=f"Black Bloc temp voice for {member}",
                **extra,
            )
        except discord.HTTPException as exc:
            log.warning("temp voice: could not create a channel for %s: %s", member.id, exc)
            await log_action(
                self.bot,
                guild,
                "tempvoice.create_failed",
                target=member,
                details={"reason": f"{type(exc).__name__}: {exc}"},
            )
            return
        await add_channel(self.bot.db, channel.id, guild.id, member.id, creator.id)
        own_channel(self.bot, channel.id)
        await log_action(
            self.bot,
            guild,
            "tempvoice.create",
            actor=member,
            target=member,
            details={"channel_id": channel.id, "name": name},
        )
        try:
            await member.move_to(channel, reason="Black Bloc temp voice")
        except discord.HTTPException as exc:
            log.warning("temp voice: could not move %s into %s: %s", member.id, channel.id, exc)
            await log_action(
                self.bot,
                guild,
                "tempvoice.move_failed",
                target=member,
                details={"channel_id": channel.id, "reason": f"{type(exc).__name__}: {exc}"},
            )
        await self._post_panel(guild, channel, member)

    async def _turn_away(self, member: Any, role_id: int) -> None:
        guild = member.guild
        try:
            await member.move_to(
                getattr(guild, "afk_channel", None), reason="Black Bloc temp voice: not a member"
            )
        except discord.HTTPException as exc:
            log.warning("temp voice: could not move %s out of the creator: %s", member.id, exc)
        try:
            await member.send(
                NOT_ALLOWED.format(role_id=role_id),
                allowed_mentions=discord.AllowedMentions.none(),
            )
        except discord.HTTPException as exc:
            log.info("temp voice: could not DM %s about the missing role: %s", member.id, exc)
        await log_action(
            self.bot,
            guild,
            "tempvoice.turned_away",
            target=member,
            details={"role_id": role_id},
        )

    async def _post_panel(self, guild: Any, channel: Any, member: Any) -> None:
        home = panel_home(self.bot, channel)
        if home is None:
            log.warning("temp voice: TEST MODE — no test channel to put the panel for %s in",
                        channel.id)
            await log_action(
                self.bot,
                guild,
                "tempvoice.panel_failed",
                target=member,
                details={"channel_id": channel.id, "reason": "no_test_channel"},
            )
            return
        elsewhere = home.id != channel.id
        try:
            message = await home.send(
                panel_text(member, channel, elsewhere=elsewhere),
                view=TempVoicePanel(),
                allowed_mentions=discord.AllowedMentions.none(),
            )
        except Exception as exc:
            log.warning("temp voice: could not post the panel in %s: %s", home.id, exc)
            await log_action(
                self.bot,
                guild,
                "tempvoice.panel_failed",
                target=member,
                details={"channel_id": channel.id, "reason": f"{type(exc).__name__}: {exc}"},
            )
            return
        await set_panel_message(self.bot.db, channel.id, message.id, home.id)
        if elsewhere:
            await log_action(
                self.bot,
                guild,
                "tempvoice.panel_elsewhere",
                target=member,
                details={"channel_id": channel.id, "panel_channel_id": home.id},
            )

    def _may_act_in(self, channel: Any) -> bool:
        return may_act_in(self.bot, channel)

    def _creator_spot(self, guild: Any) -> tuple[Any, int, str]:
        return creator_spot(self.bot, guild)

    def _join_roles(self, guild: Any) -> list[Any]:
        return join_roles(self.bot, guild)

    def _lock(self, locks: dict[int, asyncio.Lock], key: int) -> asyncio.Lock:
        lock = locks.get(key)
        if lock is None:
            lock = locks[key] = asyncio.Lock()
        return lock

    async def _database_ready(self, interaction: discord.Interaction) -> bool:
        if self.bot.db.is_connected:
            return True
        log.warning("temp voice: refused a command — the database is not connected")
        await interaction.response.send_message(DB_UNAVAILABLE, ephemeral=True)
        return False

    @tempvoice.command(name="setup", description="Create or repair the join-to-create channel")
    @app_commands.describe(name="What the join-to-create channel is called")
    async def setup_channel(
        self, interaction: discord.Interaction, name: str | None = None
    ) -> None:
        if not await require_staff(interaction):
            return
        if not await self._database_ready(interaction):
            return
        await interaction.response.defer(ephemeral=True)
        _, said = await make_creator_channel(
            self.bot, interaction.guild, interaction.user, name
        )
        await interaction.followup.send(
            said, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
        )

    @tempvoice.command(name="forget", description="Stop treating a channel id as join-to-create")
    @app_commands.describe(channel_id="The id of the join-to-create channel to forget")
    async def forget(self, interaction: discord.Interaction, channel_id: str) -> None:
        if not await require_staff(interaction):
            return
        digits = channel_id.strip().lstrip("<#").rstrip(">")
        if not digits.isdigit():
            await interaction.response.send_message(
                NOT_AN_ID.format(given=channel_id), ephemeral=True
            )
            return
        removed = await self._forget(interaction.guild, int(digits), actor=interaction.user)
        if not removed:
            await interaction.response.send_message(
                NOT_A_LOBBY.format(channel_id=digits), ephemeral=True
            )
            return
        await interaction.response.send_message(
            LOBBY_FORGOTTEN.format(channel_id=digits), ephemeral=True
        )

    async def _forget(self, guild: Any, channel_id: int, actor: Any = None) -> bool:
        return await forget_creator(self.bot, guild, channel_id, actor)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel) -> None:
        if not self.bot.db.is_connected:
            return
        await self._forget(channel.guild, channel.id)
        await delete_row(self.bot.db, channel.id)
        disown_channel(self.bot, channel.id)

    @tempvoice.command(name="status", description="Show how temporary voice channels are set up")
    async def status(self, interaction: discord.Interaction) -> None:
        if not await require_staff(interaction):
            return
        if not await self._database_ready(interaction):
            return
        guild = interaction.guild
        store = self.bot.store
        creators = store.get(guild.id, "tempvoice_creator_ids") or []
        role_id = store.get(guild.id, "tempvoice_allowed_role_id")
        wanted = store.get(guild.id, "tempvoice_creator_name")
        rows = await rows_for_guild(self.bot.db, guild.id)
        category, _, _ = self._creator_spot(guild)
        unknown = lobbies_by_name(category, wanted, creators)
        lines = [
            f"**mode** — {store.get(guild.id, 'tempvoice_mode')}",
            "**join-to-create** — "
            + (", ".join(f"<#{c}>" for c in creators) if creators else "not set up yet"),
            f"**name template** — `{store.get(guild.id, 'tempvoice_name_template')}`",
            f"**join-to-create name** — `{wanted}`",
            f"**allowed role** — {f'<@&{role_id}>' if role_id else 'anyone'}",
            f"**channels open now** — {len(rows)}",
            f"**last reconcile** — {self.last_ok_at or 'not yet'}",
            f"**last error** — {self.last_error or 'none'}",
        ]
        if unknown:
            lines.append(
                STRAY_LOBBIES.format(
                    extras=", ".join(f"<#{channel.id}>" for channel in unknown), name=wanted
                )
            )
        await interaction.response.send_message(
            "\n".join(lines), ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
        )

    @tempvoice.command(name="mode", description="Turn join-to-create off or on")
    @app_commands.describe(mode="off, or on (join-to-create makes channels)")
    @app_commands.choices(
        mode=[app_commands.Choice(name=name, value=name) for name in TEMPVOICE_MODES]
    )
    async def mode(
        self, interaction: discord.Interaction, mode: app_commands.Choice[str]
    ) -> None:
        if not await require_staff(interaction):
            return
        await self.bot.store.set(
            interaction.guild.id, "tempvoice_mode", mode.value, by=interaction.user.id
        )
        await interaction.response.send_message(
            f"Join-to-create is now **{mode.value}**.", ephemeral=True
        )
        await log_action(
            self.bot,
            interaction.guild,
            "tempvoice.mode",
            actor=interaction.user,
            details={"mode": mode.value},
        )

    async def _voice_allowed(self, interaction: discord.Interaction) -> bool:
        """The half of the `/voice` gate that needs no channel: guild, role, database."""
        if interaction.guild is None:
            await interaction.response.send_message(GUILD_ONLY, ephemeral=True)
            return False
        role_id = self.bot.store.get(interaction.guild.id, "tempvoice_allowed_role_id")
        if not may_use_voice(role_id, interaction.user):
            await interaction.response.send_message(
                VOICE_NEEDS_ROLE.format(role_id=role_id),
                ephemeral=True,
                allowed_mentions=discord.AllowedMentions.none(),
            )
            return False
        return await self._database_ready(interaction)

    async def _voice_target(
        self, interaction: discord.Interaction, *, owner_only: bool = True
    ) -> Target | None:
        """The temp channel this command acts on, or None once the caller has been answered."""
        if not await self._voice_allowed(interaction):
            return None
        store = self.bot.store
        rows = await rows_for_guild(self.bot.db, interaction.guild.id)
        here = getattr(getattr(interaction.user, "voice", None), "channel", None)
        row = pick_row(rows, interaction.user.id, getattr(here, "id", None), owner_only=owner_only)
        if row is None:
            lobby = store.get(interaction.guild.id, "tempvoice_creator_name")
            await interaction.response.send_message(
                NO_OWNED_CHANNEL.format(lobby=lobby) if owner_only else CLAIM_NEEDS_A_CHANNEL,
                ephemeral=True,
                allowed_mentions=discord.AllowedMentions.none(),
            )
            return None
        channel = temp_channel(interaction, row["channel_id"])
        if channel is None:
            await interaction.response.send_message(CHANNEL_GONE, ephemeral=True)
            return None
        return Target(row, channel)

    async def _act(
        self, interaction: discord.Interaction, handler: Any, *args: Any, owner_only: bool = True
    ) -> None:
        found = await self._voice_target(interaction, owner_only=owner_only)
        if found is None:
            return
        await interaction.response.defer(ephemeral=True)
        await answer(interaction, await handler(interaction, found.channel, found.row, *args))

    @voice.command(name="logs", description="The last few temp voice log lines")
    @app_commands.describe(
        count="How many lines, 1 to 50 (10 by default)",
        important_only="True to leave out the dry runs and the housekeeping",
    )
    async def voice_logs(
        self,
        interaction: discord.Interaction,
        count: app_commands.Range[int, LOGS_MIN, LOGS_MAX] = LOGS_DEFAULT,
        important_only: bool = False,
    ) -> None:
        await send_logs(interaction, "tempvoice", count=count, important_only=important_only)

    @voice.command(name="rename", description="Rename your temporary voice channel")
    @app_commands.describe(name="What the channel should be called")
    async def voice_rename(self, interaction: discord.Interaction, name: str) -> None:
        await self._act(interaction, do_rename, name)

    @voice.command(name="limit", description="Cap how many people can be in your channel")
    @app_commands.describe(people="0 to 99; 0 means no limit")
    async def voice_limit(
        self, interaction: discord.Interaction, people: app_commands.Range[int, 0, 99]
    ) -> None:
        await self._act(interaction, do_limit, int(people))

    @voice.command(name="lock", description="Stop anyone new joining your channel")
    async def voice_lock(self, interaction: discord.Interaction) -> None:
        await self._act(interaction, do_privacy, "connect", True)

    @voice.command(name="unlock", description="Let people join your channel again")
    async def voice_unlock(self, interaction: discord.Interaction) -> None:
        await self._act(interaction, do_privacy, "connect", False)

    @voice.command(name="hide", description="Hide your channel from everyone not in it")
    async def voice_hide(self, interaction: discord.Interaction) -> None:
        await self._act(interaction, do_privacy, "view_channel", True)

    @voice.command(name="show", description="Show your channel to everyone again")
    async def voice_show(self, interaction: discord.Interaction) -> None:
        await self._act(interaction, do_privacy, "view_channel", False)

    @voice.command(name="kick", description="Move somebody out of your channel")
    @app_commands.describe(member="Who should leave")
    async def voice_kick(self, interaction: discord.Interaction, member: discord.Member) -> None:
        await self._act(interaction, do_kick, member)

    @voice.command(name="ban", description="Keep somebody out of your channel")
    @app_commands.describe(member="Who should be kept out")
    async def voice_ban(self, interaction: discord.Interaction, member: discord.Member) -> None:
        await self._act(interaction, do_ban, member)

    @voice.command(name="unban", description="Let somebody you banned back in")
    @app_commands.describe(member="Who should be let back in")
    async def voice_unban(self, interaction: discord.Interaction, member: discord.Member) -> None:
        await self._act(interaction, do_forget_member, member, "unban")

    @voice.command(name="permit", description="Let somebody into your channel by name")
    @app_commands.describe(member="Who should be let in")
    async def voice_permit(self, interaction: discord.Interaction, member: discord.Member) -> None:
        await self._act(interaction, do_permit, member)

    @voice.command(name="unpermit", description="Take back somebody's way into your channel")
    @app_commands.describe(member="Whose invite should be taken back")
    async def voice_unpermit(
        self, interaction: discord.Interaction, member: discord.Member
    ) -> None:
        await self._act(interaction, do_forget_member, member, "unpermit")

    @voice.command(name="claim", description="Take over the channel you are in when its owner left")
    async def voice_claim(self, interaction: discord.Interaction) -> None:
        await self._act(interaction, do_claim, owner_only=False)

    @voice.command(name="transfer", description="Hand your channel to somebody else")
    @app_commands.describe(member="Who should own it")
    async def voice_transfer(
        self, interaction: discord.Interaction, member: discord.Member
    ) -> None:
        await self._act(interaction, do_transfer, member)

    @voice.command(name="bitrate", description="Set your channel's audio quality")
    @app_commands.describe(kbps="8 to 96; higher needs a higher server boost level")
    async def voice_bitrate(
        self, interaction: discord.Interaction, kbps: app_commands.Range[int, MIN_BITRATE,
                                                                        MAX_BITRATE]
    ) -> None:
        await self._act(interaction, do_bitrate, int(kbps))

    @voice.command(name="region", description="Pick which of Discord's servers carries the audio")
    @app_commands.describe(region="A region, or auto to let Discord choose")
    async def voice_region(self, interaction: discord.Interaction, region: str) -> None:
        await self._act(interaction, do_region, region)

    @voice_region.autocomplete("region")
    async def _region_options(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        return [app_commands.Choice(name=name, value=name) for name in region_choices(current)]

    @voice.command(name="info", description="Show how your temporary channel is set up")
    async def voice_info(self, interaction: discord.Interaction) -> None:
        found = await self._voice_target(interaction)
        if found is None:
            return
        role_ids = [getattr(role, "id", 0) for role in getattr(interaction.guild, "roles", ())]
        role_ids.append(getattr(interaction.guild.default_role, "id", 0))
        prefs = await get_prefs(self.bot.db, interaction.user.id)
        await interaction.response.send_message(
            "\n".join(info_lines(found.channel, found.row, role_ids) + remembered_lines(prefs)),
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @voice.command(
        name="reset", description="Forget the settings Black Bloc keeps for your voice channels"
    )
    async def voice_reset(self, interaction: discord.Interaction) -> None:
        if not await self._voice_allowed(interaction):
            return
        cleared = await clear_prefs(self.bot.db, interaction.user.id)
        if cleared:
            await log_action(
                self.bot,
                interaction.guild,
                "tempvoice.prefs_reset",
                actor=interaction.user,
                target=interaction.user,
            )
        await interaction.response.send_message(
            PREFS_CLEARED if cleared else NOTHING_REMEMBERED,
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TempVoice(bot))
