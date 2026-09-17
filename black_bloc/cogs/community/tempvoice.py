from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime
from typing import Any, NamedTuple

import discord
from discord import app_commands
from discord.ext import commands, tasks

from ... import tempvoice as helpers
from ...actionlog import log_action, send_logs
from ...command_errors import AnswersErrors
from ...golive import now_iso, parse_ts
from ...logkinds import VIA_DISCORD, kind_via
from ...loops import wait_ready
from ...panels import (
    SELECT_OPTION_LIMIT,
    Panel,
    answer,
    capped_placeholder,
    clamped,
    confirm,
    confirm_items,
    db_ready,
    db_up,
    option_label,
    retire,
    still_staff,
)
from ...settings_store import (
    DB_UNAVAILABLE,
    GUILD_ONLY,
    TEMPVOICE_MODES,
    TEMPVOICE_NAME_TEMPLATE,
)
from ...spawned import reach_roles, staff_reach

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
AUTO_REGION = helpers.AUTO_REGION
VOICE_REGIONS = helpers.VOICE_REGIONS

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
    "Join the one you want, then press **Refresh**."
)
CANNOT_SET_REGION = (
    "Discord would not use **{region}** as this channel's voice region, so nothing changed. Pick "
    "one from the list, or **auto** to let Discord choose the closest server."
)
PREFS_CLEARED = (
    "Forgotten. Your next temporary channel starts from the server's defaults — name, limit, "
    "lock, hidden, bitrate, region, and everyone you had let in or shut out by name. The channel "
    "you are in now is not changed; **Refresh** shows it."
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
    "with **Forget a lobby…** on `/voice`."
)
STRAY_LOBBIES = (
    "**not kept track of** — {extras}. Each of those is called **{name}** and sits where the "
    "join-to-create channel belongs, but Black Bloc does not treat it as one. Press **Setup** on "
    "`/voice` to take it over and repair it, or delete the channel."
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
    "forgotten. `/voice` lists the ones it knows about."
)
OUTSIDE_TEST_ROOM = (
    "**{name}** sits outside the test channel's category and Black Bloc did not make it, so test "
    "mode stopped that change and nothing happened. Black Bloc only edits the temporary channels "
    "it made itself while test mode is on — turn test mode off to reach the rest."
)
LOBBY_FORGOTTEN = (
    "Black Bloc has forgotten **{channel_id}** — joining it no longer makes anybody a temporary "
    "channel."
)
MODE_SET = "Join-to-create is now **{mode}**."
NOT_A_MODE = (
    "**{given}** is not a setting Black Bloc knows for join-to-create, so nothing was changed. "
    "It is either **off** or **on**."
)
HANDED_OVER_DM = (
    "An Auntie/Uncle handed the temporary voice channel **{channel}** to **{who}**, so it is not "
    "yours any more. Join the join-to-create channel to make yourself another one."
)
LOST_THE_CHANNEL = (
    "That temporary voice channel is not yours any more, so nothing was changed. The panel above "
    "has been brought up to date."
)
NO_SUCH_MEMBER = (
    "**{member_id}** is not somebody Black Bloc can see in this server any more, so nothing was "
    "changed. Press **Refresh** and pick again."
)
NOT_A_LIMIT = (
    "That is not a number between 0 and 99, so nothing was changed. Type a whole number — 0 lets "
    "anyone in."
)
NOT_A_BITRATE = (
    "**{given}** is not a whole number of kbps, so nothing was changed. Type a number from "
    "**8** to **96** — higher needs a higher server boost level."
)
PEOPLE_INTRO = (
    "Who may be in your channel. Letting somebody in or shutting them out is remembered for your "
    "next channel too; moving somebody out is just for now."
)
REGION_INTRO = (
    "Which of Discord's servers carries the audio. **Automatic** lets Discord pick the closest "
    "one, which is usually what you want."
)
HAND_OVER_INTRO = (
    "Pick who should own **{channel}**. They get the controls and you do not — you keep whatever "
    "Black Bloc remembers for your own next channel."
)
LOBBY_INTRO = (
    "The channels Black Bloc treats as join-to-create. Forgetting one leaves the Discord channel "
    "alone; it just stops making anybody a temporary channel."
)
LOBBY_GONE = "not on the server any more"
CHANNEL_LEFT = "gone from the server"
SITE_BUTTON = "Open on the site"
CAPPED_HERE = "{shown} of {total} in the channel"
CAPPED_UNDO = "{shown} of {total} — the rest are on the site"
UNDO_LABELS = {
    "unpermit": "{name} — take their way in back",
    "unban": "{name} — let them back in",
}
ROOT = "root"
PEOPLE_VIEW = "people"
REGION_VIEW = "region"
HAND_OVER_VIEW = "hand_over"
LOBBY_VIEW = "lobbies"
STAFF_CARD_VIEW = "staff_card"
CONFIRM_VIEW = "confirm"

STYLES = {
    "primary": discord.ButtonStyle.primary,
    "secondary": discord.ButtonStyle.secondary,
    "success": discord.ButtonStyle.success,
    "danger": discord.ButtonStyle.danger,
}


def member_label(guild: Any, user_id: Any) -> str:
    member = guild.get_member(int(user_id)) if guild is not None else None
    name = getattr(member, "display_name", None) or str(user_id)
    return str(name)[:SELECT_OPTION_LIMIT]


async def forget_creator(
    bot: Any, guild: Any, channel_id: int, actor: Any = None, *, via: str = VIA_DISCORD
) -> bool:
    """Stop treating one channel id as join-to-create; False when it was not one."""
    ids = list(bot.store.get(guild.id, "tempvoice_creator_ids") or [])
    if channel_id not in ids:
        return False
    ids.remove(channel_id)
    await bot.store.set(guild.id, "tempvoice_creator_ids", ids, by=getattr(actor, "id", None))
    await log_action(
        bot,
        guild,
        kind_via("tempvoice.creator_removed", via),
        actor=actor,
        details={"channel_id": channel_id, "via": via},
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


def category_overwrites(source: Any) -> dict[Any, Any]:
    """A copy of a category's or a channel's own overwrites, so a new channel keeps what it says."""
    found: dict[Any, Any] = {}
    for target, overwrite in (getattr(source, "overwrites", None) or {}).items():
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


def creator_overwrites(
    category: Any, allow: Any = (), me: Any = None, *, staff: Any = ()
) -> dict[Any, Any]:
    found = allow_join(category_overwrites(category), allow)
    if me is not None:
        allow_join(found, [me], manage_channels=True, move_members=True)
    return staff_reach(found, staff, voice=True)


def owner_overwrites(
    guild: Any,
    member: Any,
    *,
    locked: bool = False,
    hidden: bool = False,
    source: Any = None,
    allow: Any = (),
    me: Any = None,
    staff: Any = (),
) -> Any:
    found = category_overwrites(source)
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
    return staff_reach(found, staff, voice=True)


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
            "try it. Press **Setup** on `/voice` again once test mode is off and it will go "
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
    if guard.owns_channel(getattr(channel, "id", channel)):
        return True
    test_channel = bot.get_channel(guard.test_channel_id) if guard.test_channel_id else None
    if test_channel is None:
        return False
    return getattr(channel, "category_id", None) == getattr(test_channel, "category_id", None)


def is_lobby(bot: Any, channel: Any) -> bool:
    """A join-to-create channel this guild has written down."""
    guild = getattr(channel, "guild", None)
    store = getattr(bot, "store", None)
    if guild is None or store is None:
        return False
    written = store.get(guild.id, "tempvoice_creator_ids") or []
    return getattr(channel, "id", None) in written


def may_spawn_from(bot: Any, channel: Any) -> bool:
    """A room made from a lobby is Black Bloc's own, so test mode lets any written-down lobby."""
    return is_lobby(bot, channel) or may_act_in(bot, channel)


def room_source(store: Any, guild_id: int, creator: Any) -> Any:
    """What a new room's permissions are copied from: the lobby itself, or its category."""
    if store.get(guild_id, "tempvoice_room_overwrites") == "category":
        return getattr(creator, "category", None)
    return creator


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
    bot: Any,
    guild: Any,
    actor: Any,
    live: list[Any],
    wanted: str,
    *,
    adopted: bool = False,
    via: str = VIA_DISCORD,
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
            overwrites=creator_overwrites(
                channel.category,
                allow,
                getattr(guild, "me", None),
                staff=reach_roles(bot, guild),
            ),
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
        kind_via("tempvoice.repair", via),
        actor=actor,
        details={"channel_id": channel.id, "name": wanted, "via": via},
    )
    said = (ADOPTED if adopted else REPAIRED).format(
        where=channel.mention, name=wanted, who=roles_sentence(allow)
    )
    if len(live) > 1:
        said += EXTRA_LOBBIES.format(extras=", ".join(f"<#{other.id}>" for other in live[1:]))
    return ("adopted" if adopted else "repaired", said)


async def adopt_creator_channel(
    bot: Any, guild: Any, actor: Any, found: list[Any], wanted: str, *, via: str = VIA_DISCORD
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
        kind_via("tempvoice.adopt", via),
        actor=actor,
        details={"channel_ids": [channel.id for channel in found], "name": wanted, "via": via},
    )
    return await repair_creator_channel(
        bot, guild, actor, found, wanted, adopted=True, via=via
    )


async def make_creator_channel(
    bot: Any, guild: Any, actor: Any, name: str | None = None, *, via: str = VIA_DISCORD
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
        return await repair_creator_channel(bot, guild, actor, live, wanted, via=via)
    category, position, where = creator_spot(bot, guild)
    if where == "no_test_channel":
        return ("no_test_channel", NO_TEST_CHANNEL)
    unknown = lobbies_by_name(category, wanted, ids)
    if unknown:
        return await adopt_creator_channel(bot, guild, actor, unknown, wanted, via=via)
    allow = join_roles(bot, guild)
    try:
        channel = await guild.create_voice_channel(
            wanted,
            category=category,
            position=position,
            overwrites=creator_overwrites(
                category, allow, getattr(guild, "me", None), staff=reach_roles(bot, guild)
            ),
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
        kind_via("tempvoice.setup", via),
        actor=actor,
        details={"channel_id": channel.id, "placed": where, "name": wanted, "via": via},
    )
    return (
        "created",
        f"**{channel.name}** is ready — {channel.mention}, and {roles_sentence(allow)} can "
        f"see it and join it. {where_sentence(where)}",
    )


class Target(NamedTuple):
    row: Any
    channel: Any


class Said(str):
    """The sentence an action answers with, carrying whether it changed anything."""

    ok: bool

    def __new__(cls, text: str, *, ok: bool = True) -> Said:
        found = super().__new__(cls, text)
        found.ok = ok
        return found


class Doer(NamedTuple):
    """Who is acting, shaped like the interaction the panel hands these helpers."""

    client: Any
    guild: Any
    user: Any
    via: str = VIA_DISCORD


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


async def panel_log(who: Any, kind: str, channel_id: Any, **details: Any) -> None:
    via = getattr(who, "via", VIA_DISCORD)
    await log_action(
        who.client,
        who.guild,
        kind_via(f"tempvoice.{kind}", via),
        actor=who.user,
        details={"channel_id": int(channel_id), "via": via} | details,
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


async def do_rename(who: Any, channel: Any, row: Any, wanted: str) -> Said:
    wanted = (wanted or "").strip()[:NAME_LIMIT]
    if not wanted:
        return Said("A channel needs a name, so nothing was changed.", ok=False)
    try:
        await channel.edit(name=wanted, reason="Black Bloc temp voice")
    except (discord.HTTPException, discord.RateLimited) as exc:
        log.warning("temp voice: rename refused in %s: %s", channel.id, exc)
        await panel_log(who, "rename_failed", channel.id, reason=str(exc))
        return Said(RENAMED_TOO_OFTEN if rate_limited(exc) else CANNOT_EDIT, ok=False)
    await save_prefs(who.client.db, row["owner_id"], name=wanted)
    await panel_log(who, "rename", channel.id, name=wanted)
    return Said(f"Renamed to **{wanted}**, and remembered for next time.")


async def do_limit(who: Any, channel: Any, row: Any, value: int) -> Said:
    try:
        await channel.edit(user_limit=value, reason="Black Bloc temp voice")
    except discord.HTTPException as exc:
        log.warning("temp voice: limit refused in %s: %s", channel.id, exc)
        await panel_log(who, "limit_failed", channel.id, reason=str(exc))
        return Said(CANNOT_EDIT, ok=False)
    await save_prefs(who.client.db, row["owner_id"], user_limit=value)
    await panel_log(who, "limit", channel.id, user_limit=value)
    return Said("Anyone can join now." if value == 0 else f"Capped at **{value}** people.")


async def do_privacy(
    who: Any,
    channel: Any,
    row: Any,
    permission: str,
    want: bool | None = None,
) -> Said:
    everyone = channel.guild.default_role
    async with channel_lock(who.client, channel.id):
        overwrite = channel.overwrites_for(everyone)
        was_off = getattr(overwrite, permission) is False
        turning_off = (not was_off) if want is None else want
        if turning_off == was_off:
            return Said(already_message(permission, was_off))
        setattr(overwrite, permission, False if turning_off else None)
        try:
            await channel.set_permissions(
                everyone, overwrite=overwrite, reason="Black Bloc temp voice"
            )
        except discord.HTTPException as exc:
            log.warning("temp voice: %s refused in %s: %s", permission, channel.id, exc)
            await panel_log(who, "privacy_failed", channel.id, reason=str(exc))
            return Said(CANNOT_EDIT, ok=False)
    if permission == "connect":
        await save_prefs(who.client.db, row["owner_id"], locked=turning_off)
        said = "Locked — nobody new may join." if turning_off else "Unlocked — anyone may join."
        kind = "lock" if turning_off else "unlock"
    else:
        await save_prefs(who.client.db, row["owner_id"], hidden=turning_off)
        said = (
            "Hidden — only people already in it can see it."
            if turning_off
            else "Visible again to everyone."
        )
        kind = "hide" if turning_off else "show"
    await panel_log(who, kind, channel.id)
    return Said(said)


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


def privacy_of(channel: Any) -> tuple[bool, bool]:
    """Locked and hidden, read off the channel's own `@everyone` overwrite."""
    try:
        overwrite = channel.overwrites_for(channel.guild.default_role)
    except (AttributeError, TypeError):
        return False, False
    return overwrite.connect is False, overwrite.view_channel is False


def info_lines(channel: Any, row: Any, role_ids: Any) -> list[str]:
    locked, hidden = privacy_of(channel)
    permitted, banned = member_lists(getattr(channel, "overwrites", {}), row["owner_id"], role_ids)
    limit = int(getattr(channel, "user_limit", 0) or 0)
    bitrate = int(getattr(channel, "bitrate", 0) or 0)
    cap = "no limit" if limit == 0 else f"{limit} people"
    speed = f"{bitrate // 1000} kbps" if bitrate else "whatever the server gives it"
    return [
        f"**channel** — <#{channel.id}>",
        f"**owner** — <@{row['owner_id']}>",
        f"**limit** — {cap}",
        f"**locked** — {'yes' if locked else 'no'}",
        f"**hidden** — {'yes' if hidden else 'no'}",
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
        "**Forget my settings** drops all of it.",
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


async def set_mode(who: Any, value: Any) -> Said:
    """Join-to-create off or on, from whichever door asked — one write, one log row."""
    wanted = str(value or "").strip().lower()
    if wanted not in TEMPVOICE_MODES:
        return Said(NOT_A_MODE.format(given=str(value)[:40]), ok=False)
    via = getattr(who, "via", VIA_DISCORD)
    await who.client.store.set(who.guild.id, "tempvoice_mode", wanted, by=who.user.id)
    await log_action(
        who.client,
        who.guild,
        kind_via("tempvoice.mode", via),
        actor=who.user,
        details={"mode": wanted, "via": via},
    )
    return Said(MODE_SET.format(mode=wanted))


async def reset_prefs(who: Any) -> Said:
    via = getattr(who, "via", VIA_DISCORD)
    if await clear_prefs(who.client.db, who.user.id):
        await log_action(
            who.client,
            who.guild,
            kind_via("tempvoice.prefs_reset", via),
            actor=who.user,
            target=who.user,
            details={"via": via},
        )
    return Said(PREFS_CLEARED)


async def staff_hand_over(who: Any, channel: Any, row: Any, target: Any) -> str:
    """Staff get the final say on a stored owner, and the person who loses it is told."""
    displaced = int(row["owner_id"])
    said = await do_transfer(who, channel, row, target)
    if said in (NOT_A_TEMP_CHANNEL, CLAIM_LOST) or displaced == int(target.id):
        return said
    member = channel.guild.get_member(displaced)
    if member is not None:
        try:
            await member.send(
                HANDED_OVER_DM.format(
                    channel=getattr(channel, "name", ""), who=target.display_name
                ),
                allowed_mentions=discord.AllowedMentions.none(),
            )
        except discord.HTTPException as exc:
            log.info("temp voice: could not DM %s about the hand over: %s", displaced, exc)
    return said


async def voice_gate(interaction: discord.Interaction) -> bool:
    """The half of the gate that has to refuse outright: a guild, and a database to read."""
    if interaction.guild is None:
        await answer(interaction, GUILD_ONLY)
        return False
    if not interaction.client.db.is_connected:
        log.warning("temp voice: refused the panel — the database is not connected")
        await answer(interaction, DB_UNAVAILABLE)
        return False
    return True


def has_voice_role(bot: Any, guild: Any, actor: Any) -> bool:
    return may_use_voice(bot.store.get(guild.id, "tempvoice_allowed_role_id"), actor)


def may_open(bot: Any, guild: Any, actor: Any) -> bool:
    """Staff never fall outside their own server's voice controls, allowed role or not."""
    return bot.store.is_staff(actor) or has_voice_role(bot, guild, actor)


def stray_lobbies(bot: Any, guild: Any) -> list[Any]:
    store = bot.store
    return lobbies_by_name(
        creator_spot(bot, guild)[0],
        store.get(guild.id, "tempvoice_creator_name"),
        store.get(guild.id, "tempvoice_creator_ids") or [],
    )


def lobby_choices(bot: Any, guild: Any) -> list[tuple[int, str]]:
    """Only the ids `forget_creator` can actually drop; the strays are named in the embed."""
    found: list[tuple[int, str]] = []
    for channel_id in bot.store.get(guild.id, "tempvoice_creator_ids") or []:
        channel = guild.get_channel(int(channel_id))
        found.append((int(channel_id), getattr(channel, "name", None) or LOBBY_GONE))
    return found


def voice_health(bot: Any) -> tuple[Any, Any]:
    finder = getattr(bot, "get_cog", None)
    cog = finder("TempVoice") if finder is not None else None
    return (getattr(cog, "last_ok_at", None), getattr(cog, "last_error", None))


def status_lines(bot: Any, guild: Any, rows: Any) -> list[str]:
    """The staff block — what `/tempvoice status` printed, written out rather than hidden."""
    store = bot.store
    creators = store.get(guild.id, "tempvoice_creator_ids") or []
    role_id = store.get(guild.id, "tempvoice_allowed_role_id")
    wanted = store.get(guild.id, "tempvoice_creator_name")
    last_ok, last_error = voice_health(bot)
    lines = [
        f"**mode** — {store.get(guild.id, 'tempvoice_mode')}",
        "**join-to-create** — "
        + (", ".join(f"<#{one}>" for one in creators) if creators else "not set up yet"),
        f"**name template** — `{store.get(guild.id, 'tempvoice_name_template')}`",
        f"**join-to-create name** — `{wanted}`",
        f"**allowed role** — {f'<@&{role_id}>' if role_id else 'anyone'}",
        f"**channels open now** — {len(list(rows or ()))}",
        f"**last reconcile** — {last_ok or 'not yet'}",
        f"**last error** — {last_error or 'none'}",
    ]
    unknown = stray_lobbies(bot, guild)
    if unknown:
        lines.append(
            STRAY_LOBBIES.format(
                extras=", ".join(f"<#{channel.id}>" for channel in unknown), name=wanted
            )
        )
    return lines


def role_ids_of(guild: Any) -> list[int]:
    found = [getattr(role, "id", 0) for role in getattr(guild, "roles", ())]
    found.append(getattr(getattr(guild, "default_role", None), "id", 0))
    return found


def minutes_for(bot: Any, guild_id: int) -> int:
    return helpers.panel_minutes(bot.store, guild_id)


def add_site_button(view: Any, bot: Any, row: int) -> None:
    """The dashboard page is behind the staff gate, so only staff are ever offered it."""
    url = helpers.site_page_url(getattr(getattr(bot, "settings", None), "origin", ""))
    if not url:
        return
    view.add_item(
        discord.ui.Button(style=discord.ButtonStyle.link, label=SITE_BUTTON, url=url, row=row)
    )


class Facts(NamedTuple):
    state: str
    row: Any
    channel: Any
    prefs: Any
    rows: list[Any]
    staff: bool
    has_role: bool


async def panel_facts(bot: Any, guild: Any, actor: Any) -> Facts:
    """Everything the panel renders from, re-read at every click — nothing is remembered."""
    rows = await rows_for_guild(bot.db, guild.id)
    here = getattr(getattr(actor, "voice", None), "channel", None)
    here_id = getattr(here, "id", None)
    state = helpers.panel_state(
        rows,
        actor.id,
        here_id,
        connected_ids(here) if here is not None else (),
        allowed=may_open(bot, guild, actor),
    )
    row = None
    if state in (helpers.OWNER, helpers.ORPHAN, helpers.GUEST):
        row = pick_row(rows, actor.id, here_id, owner_only=state == helpers.OWNER)
    channel = guild.get_channel(int(row["channel_id"])) if row is not None else None
    if channel is None and state != helpers.BLOCKED:
        state, row = helpers.NONE, None
    return Facts(
        state,
        row,
        channel,
        await get_prefs(bot.db, actor.id),
        rows,
        bot.store.is_staff(actor),
        has_voice_role(bot, guild, actor),
    )


def panel_lines(bot: Any, guild: Any, facts: Facts) -> list[str]:
    store = bot.store
    role_id = store.get(guild.id, "tempvoice_allowed_role_id")
    lines: list[str] = []
    if facts.state == helpers.BLOCKED:
        lines.append(VOICE_NEEDS_ROLE.format(role_id=role_id))
    elif facts.state == helpers.OWNER:
        lines.append(helpers.PANEL_INTRO)
        lines += info_lines(facts.channel, facts.row, role_ids_of(guild))
        lines += remembered_lines(facts.prefs)
    elif facts.state == helpers.ORPHAN:
        lines.append(helpers.ORPHAN_LINE.format(owner_id=facts.row["owner_id"]))
    elif facts.state == helpers.GUEST:
        lines.append(helpers.GUEST_LINE.format(owner_id=facts.row["owner_id"]))
    else:
        lines.append(
            NO_OWNED_CHANNEL.format(lobby=store.get(guild.id, "tempvoice_creator_name"))
        )
        if store.get(guild.id, "tempvoice_mode") != "on":
            lines.append(helpers.MODE_OFF_LINE)
    if facts.staff and not facts.has_role and role_id:
        lines.append(helpers.STAFF_WITHOUT_ROLE.format(role_id=role_id))
    if facts.staff:
        lines.append("")
        lines += status_lines(bot, guild, facts.rows)
    return lines


class VoicePanel(Panel):
    def __init__(self, minutes: int) -> None:
        super().__init__(minutes, footer=helpers.PANEL_TIMEOUT_FOOTER)
        self.where = ROOT
        self.channel_id: int | None = None


async def build_panel(bot: Any, guild: Any, actor: Any) -> tuple[discord.Embed, VoicePanel]:
    """One command, one panel: the caller's own channel, and the staff half only for staff."""
    facts = await panel_facts(bot, guild, actor)
    locked, hidden = privacy_of(facts.channel) if facts.channel is not None else (False, False)
    embed = discord.Embed(
        title=helpers.PANEL_TITLE, description=clamped(panel_lines(bot, guild, facts))
    )
    view = VoicePanel(minutes_for(bot, guild.id))
    for move in helpers.card_buttons(
        facts.state,
        locked=locked,
        hidden=hidden,
        has_prefs=facts.prefs is not None,
        staff=facts.staff,
        mode_on=bot.store.get(guild.id, "tempvoice_mode") == "on",
        has_lobbies=bool(lobby_choices(bot, guild)),
    ):
        view.add_item(MoveButton(move))
    if facts.staff:
        if facts.rows:
            view.add_item(ChannelPick(guild, facts.rows, row=3))
        add_site_button(view, bot, row=4)
    return (embed, view)


async def build_people(
    bot: Any, guild: Any, actor: Any
) -> tuple[discord.Embed | None, VoicePanel | None]:
    facts = await panel_facts(bot, guild, actor)
    if facts.state != helpers.OWNER:
        return (None, None)
    channel = facts.channel
    here = sorted(connected_ids(channel))
    others = [one for one in here if one != int(facts.row["owner_id"])]
    permitted, banned = member_lists(
        getattr(channel, "overwrites", {}), facts.row["owner_id"], role_ids_of(guild)
    )
    undo = helpers.undo_options(permitted, banned)
    embed = discord.Embed(
        title=helpers.PEOPLE_TITLE,
        description=clamped(
            [
                PEOPLE_INTRO,
                f"**in it now** — {mentions(here)}",
                f"**let in by name** — {mentions(permitted)}",
                f"**kept out by name** — {mentions(banned)}",
            ]
        ),
    )
    view = VoicePanel(minutes_for(bot, guild.id))
    view.where = PEOPLE_VIEW
    for control in helpers.people_controls(others_here=bool(others), has_lists=bool(undo)):
        if control == helpers.PERMIT_PICK:
            view.add_item(MemberPickOne("permit", helpers.PICK_PERMIT, row=0))
        elif control == helpers.BAN_PICK:
            view.add_item(MemberPickOne("ban", helpers.PICK_BAN, row=1))
        elif control == helpers.KICK_PICK:
            view.add_item(KickPick(guild, others, row=2))
        else:
            view.add_item(UndoPick(guild, undo, row=3))
    view.add_item(MoveButton(helpers.BACK_MOVE))
    return (embed, view)


def build_region(bot: Any, guild: Any, current: Any) -> tuple[discord.Embed, VoicePanel]:
    embed = discord.Embed(
        title=helpers.REGION_TITLE,
        description=clamped([REGION_INTRO, f"**now** — {current or 'automatic'}"]),
    )
    view = VoicePanel(minutes_for(bot, guild.id))
    view.where = REGION_VIEW
    view.add_item(RegionPick(current, row=0))
    view.add_item(MoveButton(helpers.AUTOMATIC_MOVE))
    view.add_item(MoveButton(helpers.BACK_MOVE._replace(row=1)))
    return (embed, view)


def build_hand_over(
    bot: Any, guild: Any, channel: Any, *, channel_id: int | None = None
) -> tuple[discord.Embed, VoicePanel]:
    embed = discord.Embed(
        title=helpers.HAND_OVER_TITLE,
        description=clamped([HAND_OVER_INTRO.format(channel=getattr(channel, "name", ""))]),
    )
    view = VoicePanel(minutes_for(bot, guild.id))
    view.where = HAND_OVER_VIEW
    view.channel_id = channel_id
    view.add_item(NewOwnerPick(row=0))
    view.add_item(MoveButton(helpers.BACK_MOVE._replace(row=1)))
    return (embed, view)


def build_lobbies(bot: Any, guild: Any) -> tuple[discord.Embed, VoicePanel]:
    found = lobby_choices(bot, guild)
    embed = discord.Embed(
        title=helpers.LOBBY_TITLE,
        description=clamped([LOBBY_INTRO] + status_lines(bot, guild, ())),
    )
    view = VoicePanel(minutes_for(bot, guild.id))
    view.where = LOBBY_VIEW
    if found:
        view.add_item(LobbyPick(found, row=0))
    view.add_item(MoveButton(helpers.BACK_MOVE._replace(row=1)))
    return (embed, view)


async def build_staff_card(
    bot: Any, guild: Any, channel_id: Any
) -> tuple[discord.Embed | None, VoicePanel | None]:
    row = await get_row(bot.db, int(channel_id))
    channel = guild.get_channel(int(channel_id)) if row is not None else None
    if row is None or channel is None:
        return (None, None)
    embed = discord.Embed(
        title=helpers.STAFF_CARD_TITLE,
        description=clamped(info_lines(channel, row, role_ids_of(guild))),
    )
    view = VoicePanel(minutes_for(bot, guild.id))
    view.where = STAFF_CARD_VIEW
    view.channel_id = int(channel_id)
    view.add_item(MoveButton(helpers.STAFF_TRANSFER_MOVE))
    view.add_item(MoveButton(helpers.BACK_MOVE._replace(row=0)))
    return (embed, view)


async def render(interaction: discord.Interaction, embed: Any, view: Any, previous: Any) -> None:
    retire(previous)
    view.message = await interaction.edit_original_response(
        embed=embed, view=view, allowed_mentions=discord.AllowedMentions.none()
    )


async def render_panel(interaction: discord.Interaction, previous: Any = None) -> None:
    embed, view = await build_panel(
        interaction.client, interaction.guild, interaction.user
    )
    await render(interaction, embed, view, previous)


async def render_people(interaction: discord.Interaction, previous: Any = None) -> None:
    embed, view = await build_people(
        interaction.client, interaction.guild, interaction.user
    )
    if view is None:
        await render_panel(interaction, previous)
        await answer(interaction, LOST_THE_CHANNEL)
        return
    await render(interaction, embed, view, previous)


async def render_staff_card(
    interaction: discord.Interaction, channel_id: Any, previous: Any = None
) -> None:
    embed, view = await build_staff_card(interaction.client, interaction.guild, channel_id)
    if view is None:
        await render_panel(interaction, previous)
        await answer(interaction, CHANNEL_GONE)
        return
    await render(interaction, embed, view, previous)


async def ready_to_move(interaction: discord.Interaction) -> bool:
    await interaction.response.defer()
    return await db_ready(interaction)


async def owned_now(interaction: discord.Interaction) -> Target | None:
    """The caller's own channel, re-read at click time — ownership moves while a card is open."""
    facts = await panel_facts(interaction.client, interaction.guild, interaction.user)
    if facts.state != helpers.OWNER:
        return None
    return Target(facts.row, facts.channel)


async def back_to_panel(interaction: discord.Interaction, previous: Any = None) -> None:
    if not await ready_to_move(interaction):
        return
    await render_panel(interaction, previous)


async def open_people(interaction: discord.Interaction, previous: Any = None) -> None:
    if not await ready_to_move(interaction):
        return
    await render_people(interaction, previous)


async def open_region(interaction: discord.Interaction, previous: Any = None) -> None:
    if not await ready_to_move(interaction):
        return
    found = await owned_now(interaction)
    if found is None:
        await render_panel(interaction, previous)
        await answer(interaction, LOST_THE_CHANNEL)
        return
    embed, view = build_region(
        interaction.client, interaction.guild, getattr(found.channel, "rtc_region", None)
    )
    await render(interaction, embed, view, previous)


async def open_hand_over(interaction: discord.Interaction, previous: Any = None) -> None:
    if not await ready_to_move(interaction):
        return
    found = await owned_now(interaction)
    if found is None:
        await render_panel(interaction, previous)
        await answer(interaction, LOST_THE_CHANNEL)
        return
    embed, view = build_hand_over(interaction.client, interaction.guild, found.channel)
    await render(interaction, embed, view, previous)


async def open_staff_hand_over(
    interaction: discord.Interaction, channel_id: Any, previous: Any = None
) -> None:
    if not await still_staff(interaction):
        return
    if not await ready_to_move(interaction):
        return
    channel = interaction.guild.get_channel(int(channel_id)) if channel_id else None
    if channel is None:
        await render_panel(interaction, previous)
        await answer(interaction, CHANNEL_GONE)
        return
    embed, view = build_hand_over(
        interaction.client, interaction.guild, channel, channel_id=int(channel_id)
    )
    await render(interaction, embed, view, previous)


async def open_lobbies(interaction: discord.Interaction, previous: Any = None) -> None:
    if not await still_staff(interaction):
        return
    if not await ready_to_move(interaction):
        return
    embed, view = build_lobbies(interaction.client, interaction.guild)
    await render(interaction, embed, view, previous)


async def open_staff_card(
    interaction: discord.Interaction, channel_id: Any, previous: Any = None
) -> None:
    if not await still_staff(interaction):
        return
    if not await ready_to_move(interaction):
        return
    await render_staff_card(interaction, channel_id, previous)


async def open_forget_confirm(interaction: discord.Interaction, previous: Any = None) -> None:
    if not await ready_to_move(interaction):
        return
    view = VoicePanel(minutes_for(interaction.client, interaction.guild.id))
    view.where = CONFIRM_VIEW
    await confirm(
        interaction,
        view,
        discord.Embed(
            title=helpers.FORGET_TITLE, description=clamped([helpers.FORGET_QUESTION])
        ),
        confirm_items(
            yes=helpers.FORGET_YES,
            no=helpers.KEEP_IT,
            on_yes=run_forget_prefs,
            on_no=back_to_panel,
        ),
        previous,
    )


async def act_on_own(
    interaction: discord.Interaction, handler: Any, *args: Any, previous: Any = None
) -> None:
    """Every owner move: defer, re-read the row, call the shared function, re-render, say so."""
    if not await ready_to_move(interaction):
        return
    found = await owned_now(interaction)
    if found is None:
        await render_panel(interaction, previous)
        await answer(interaction, LOST_THE_CHANNEL)
        return
    said = await handler(interaction, found.channel, found.row, *args)
    await render_panel(interaction, previous)
    await answer(interaction, str(said))


async def run_people_move(
    interaction: discord.Interaction, handler: Any, *args: Any, previous: Any = None
) -> None:
    if not await ready_to_move(interaction):
        return
    found = await owned_now(interaction)
    if found is None:
        await render_panel(interaction, previous)
        await answer(interaction, LOST_THE_CHANNEL)
        return
    said = await handler(interaction, found.channel, found.row, *args)
    await render_people(interaction, previous)
    await answer(interaction, str(said))


async def run_claim(interaction: discord.Interaction, previous: Any = None) -> None:
    if not await ready_to_move(interaction):
        return
    facts = await panel_facts(interaction.client, interaction.guild, interaction.user)
    if facts.state != helpers.ORPHAN:
        await render_panel(interaction, previous)
        await answer(interaction, CLAIM_NEEDS_A_CHANNEL)
        return
    said = await do_claim(interaction, facts.channel, facts.row)
    await render_panel(interaction, previous)
    await answer(interaction, said)


async def run_region(
    interaction: discord.Interaction, region: str, previous: Any = None
) -> None:
    if not await ready_to_move(interaction):
        return
    found = await owned_now(interaction)
    if found is None:
        await render_panel(interaction, previous)
        await answer(interaction, LOST_THE_CHANNEL)
        return
    said = await do_region(interaction, found.channel, found.row, region)
    embed, view = build_region(
        interaction.client, interaction.guild, getattr(found.channel, "rtc_region", None)
    )
    await render(interaction, embed, view, previous)
    await answer(interaction, said)


async def run_transfer(
    interaction: discord.Interaction, target: Any, channel_id: Any = None, previous: Any = None
) -> None:
    """The member's own hand-over is `do_transfer`; a staffer's also DMs the displaced owner."""
    if channel_id is None:
        await act_on_own(interaction, do_transfer, target, previous=previous)
        return
    if not await still_staff(interaction):
        return
    if not await ready_to_move(interaction):
        return
    row = await get_row(interaction.client.db, int(channel_id))
    channel = interaction.guild.get_channel(int(channel_id)) if row is not None else None
    if row is None or channel is None:
        await render_panel(interaction, previous)
        await answer(interaction, CHANNEL_GONE)
        return
    said = await staff_hand_over(interaction, channel, row, target)
    await render_staff_card(interaction, channel_id, previous)
    await answer(interaction, said)


async def run_forget_prefs(interaction: discord.Interaction, previous: Any = None) -> None:
    if not await ready_to_move(interaction):
        return
    said = await reset_prefs(interaction)
    await render_panel(interaction, previous)
    await answer(interaction, str(said))


async def run_mode(interaction: discord.Interaction, previous: Any = None) -> None:
    if not await still_staff(interaction):
        return
    if not await ready_to_move(interaction):
        return
    store = interaction.client.store
    now = store.get(interaction.guild.id, "tempvoice_mode")
    said = await set_mode(interaction, "off" if now == "on" else "on")
    await render_panel(interaction, previous)
    await answer(interaction, str(said))


async def run_setup(
    interaction: discord.Interaction, name: Any = None, previous: Any = None
) -> None:
    if not await still_staff(interaction):
        return
    if not await ready_to_move(interaction):
        return
    _, said = await make_creator_channel(
        interaction.client, interaction.guild, interaction.user, name
    )
    await render_panel(interaction, previous)
    await answer(interaction, said)


async def run_forget_lobby(
    interaction: discord.Interaction, channel_id: Any, previous: Any = None
) -> None:
    if not await still_staff(interaction):
        return
    if not await ready_to_move(interaction):
        return
    dropped = await forget_creator(
        interaction.client, interaction.guild, int(channel_id), interaction.user
    )
    said = (
        LOBBY_FORGOTTEN if dropped else NOT_A_LOBBY
    ).format(channel_id=int(channel_id))
    embed, view = build_lobbies(interaction.client, interaction.guild)
    await render(interaction, embed, view, previous)
    await answer(interaction, said)


class MoveButton(discord.ui.Button):
    def __init__(self, move: Any) -> None:
        super().__init__(label=move.label, style=STYLES[move.style], row=move.row)
        self.move = move

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        action = self.move.action
        if action == helpers.REFRESH:
            await back_to_panel(interaction, view)
            return
        if action == helpers.BACK:
            await back_from(interaction, view)
            return
        if action == helpers.LOGS:
            await send_logs(interaction, "tempvoice")
            return
        if action == helpers.PEOPLE:
            await open_people(interaction, view)
            return
        if action == helpers.REGION:
            await open_region(interaction, view)
            return
        if action == helpers.AUTOMATIC:
            await run_region(interaction, AUTO_REGION, view)
            return
        if action == helpers.TRANSFER:
            if view.where == STAFF_CARD_VIEW:
                await open_staff_hand_over(interaction, view.channel_id, view)
                return
            await open_hand_over(interaction, view)
            return
        if action == helpers.CLAIM:
            await run_claim(interaction, view)
            return
        if action == helpers.FORGET_PREFS:
            await open_forget_confirm(interaction, view)
            return
        if action in (helpers.LOCK, helpers.UNLOCK):
            await act_on_own(
                interaction, do_privacy, "connect", action == helpers.LOCK, previous=view
            )
            return
        if action in (helpers.HIDE, helpers.SHOW):
            await act_on_own(
                interaction, do_privacy, "view_channel", action == helpers.HIDE, previous=view
            )
            return
        if action == helpers.MODE:
            await run_mode(interaction, view)
            return
        if action == helpers.LOBBIES:
            await open_lobbies(interaction, view)
            return
        if action == helpers.SETUP:
            if not await still_staff(interaction):
                return
            if not await db_up(interaction):
                return
            await interaction.response.send_modal(
                SetupModal(interaction.client, interaction.guild.id, view)
            )
            return
        if not await db_up(interaction):
            return
        await interaction.response.send_modal(MODALS[action](view))


async def back_from(interaction: discord.Interaction, view: Any) -> None:
    if view.where == HAND_OVER_VIEW and view.channel_id is not None:
        await open_staff_card(interaction, view.channel_id, view)
        return
    await back_to_panel(interaction, view)


class MemberPickOne(discord.ui.UserSelect):
    def __init__(self, action: str, placeholder: str, row: int) -> None:
        super().__init__(placeholder=placeholder, min_values=1, max_values=1, row=row)
        self.action = action

    async def callback(self, interaction: discord.Interaction) -> None:
        handler = do_permit if self.action == "permit" else do_ban
        await run_people_move(
            interaction, handler, self.values[0], previous=self.view
        )


class KickPick(discord.ui.Select):
    def __init__(self, guild: Any, user_ids: Any, row: int) -> None:
        found = list(user_ids)
        shown = found[: helpers.SELECT_CAP]
        super().__init__(
            placeholder=capped_placeholder(
                len(shown), len(found), pick=helpers.PICK_KICK, capped=CAPPED_HERE
            ),
            options=[
                discord.SelectOption(label=member_label(guild, one), value=str(one))
                for one in shown
            ],
            min_values=1,
            max_values=1,
            row=row,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        target = interaction.guild.get_member(int(self.values[0]))
        if target is None:
            await back_to_panel(interaction, self.view)
            await answer(interaction, NO_SUCH_MEMBER.format(member_id=self.values[0]))
            return
        await run_people_move(interaction, do_kick, target, previous=self.view)


class UndoPick(discord.ui.Select):
    """One control whose options already know which undo they are (P3: never two spellings)."""

    def __init__(self, guild: Any, options: Any, row: int) -> None:
        found = list(options)
        shown = found[: helpers.SELECT_CAP]
        super().__init__(
            placeholder=capped_placeholder(
                len(shown), len(found), pick=helpers.PICK_UNDO, capped=CAPPED_UNDO
            ),
            options=[
                discord.SelectOption(
                    label=UNDO_LABELS[kind].format(name=member_label(guild, user_id))[
                        :SELECT_OPTION_LIMIT
                    ],
                    value=f"{kind}:{user_id}",
                )
                for user_id, kind in shown
            ],
            min_values=1,
            max_values=1,
            row=row,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        kind, _, user_id = self.values[0].partition(":")
        target = interaction.guild.get_member(int(user_id))
        if target is None:
            await back_to_panel(interaction, self.view)
            await answer(interaction, NO_SUCH_MEMBER.format(member_id=user_id))
            return
        await run_people_move(
            interaction, do_forget_member, target, kind, previous=self.view
        )


class RegionPick(discord.ui.Select):
    def __init__(self, current: Any, row: int) -> None:
        now = str(current or "")
        super().__init__(
            placeholder=helpers.PICK_REGION,
            options=[
                discord.SelectOption(label=name, value=name, default=(name == now))
                for name in helpers.named_regions()
            ],
            min_values=1,
            max_values=1,
            row=row,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await run_region(interaction, self.values[0], self.view)


class NewOwnerPick(discord.ui.UserSelect):
    def __init__(self, row: int) -> None:
        super().__init__(
            placeholder=helpers.PICK_NEW_OWNER, min_values=1, max_values=1, row=row
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        await run_transfer(interaction, self.values[0], view.channel_id, view)


class ChannelPick(discord.ui.Select):
    def __init__(self, guild: Any, rows: Any, row: int) -> None:
        found = list(rows)
        shown = found[: helpers.SELECT_CAP]
        super().__init__(
            placeholder=capped_placeholder(
                len(shown), len(found), pick=helpers.PICK_CHANNEL
            ),
            options=[
                discord.SelectOption(
                    label=option_label(
                        one["channel_id"],
                        None,
                        getattr(guild.get_channel(int(one["channel_id"])), "name", CHANNEL_LEFT),
                    ),
                    value=str(one["channel_id"]),
                )
                for one in shown
            ],
            min_values=1,
            max_values=1,
            row=row,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await open_staff_card(interaction, int(self.values[0]), self.view)


class LobbyPick(discord.ui.Select):
    def __init__(self, choices: Any, row: int) -> None:
        found = list(choices)
        shown = found[: helpers.SELECT_CAP]
        super().__init__(
            placeholder=capped_placeholder(len(shown), len(found), pick=helpers.PICK_LOBBY),
            options=[
                discord.SelectOption(
                    label=option_label(channel_id, None, name), value=str(channel_id)
                )
                for channel_id, name in shown
            ],
            min_values=1,
            max_values=1,
            row=row,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await run_forget_lobby(interaction, int(self.values[0]), self.view)


class RenameModal(AnswersErrors, discord.ui.Modal, title="Rename this channel"):
    name = discord.ui.TextInput(label="New name", max_length=NAME_LIMIT)

    def __init__(self, channel_id: int | None = None, previous: Any = None) -> None:
        super().__init__()
        self.channel_id = channel_id
        self.previous = previous

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if self.previous is not None:
            await act_on_own(interaction, do_rename, str(self.name), previous=self.previous)
            return
        found = await panel_context(interaction, channel_id=self.channel_id)
        if found is None:
            return
        await interaction.response.defer(ephemeral=True)
        await answer(
            interaction, await do_rename(interaction, found.channel, found.row, str(self.name))
        )


class LimitModal(AnswersErrors, discord.ui.Modal, title="How many people?"):
    limit = discord.ui.TextInput(label="0 to 99 (0 means no limit)", max_length=2)

    def __init__(self, channel_id: int | None = None, previous: Any = None) -> None:
        super().__init__()
        self.channel_id = channel_id
        self.previous = previous

    async def on_submit(self, interaction: discord.Interaction) -> None:
        value = parse_limit(str(self.limit))
        if self.previous is not None:
            if value is None:
                await answer(interaction, NOT_A_LIMIT)
                return
            await act_on_own(interaction, do_limit, value, previous=self.previous)
            return
        found = await panel_context(interaction, channel_id=self.channel_id)
        if found is None:
            return
        await interaction.response.defer(ephemeral=True)
        if value is None:
            await answer(interaction, NOT_A_LIMIT)
            return
        await answer(interaction, await do_limit(interaction, found.channel, found.row, value))


class BitrateModal(AnswersErrors, discord.ui.Modal, title="How good should it sound?"):
    kbps = discord.ui.TextInput(
        label=f"{MIN_BITRATE} to {MAX_BITRATE} kbps", max_length=3
    )

    def __init__(self, previous: Any = None) -> None:
        super().__init__()
        self.previous = previous

    async def on_submit(self, interaction: discord.Interaction) -> None:
        """The bound `app_commands.Range` used to enforce; a modal has none (checklist 22)."""
        given = str(self.kbps).strip()
        if not given.isdigit() or not MIN_BITRATE <= int(given) <= MAX_BITRATE:
            await answer(interaction, NOT_A_BITRATE.format(given=given[:40] or "nothing"))
            return
        await act_on_own(interaction, do_bitrate, int(given), previous=self.previous)


class SetupModal(AnswersErrors, discord.ui.Modal, title="The join-to-create channel"):
    name = discord.ui.TextInput(label="What it should be called", max_length=NAME_LIMIT)

    def __init__(self, bot: Any, guild_id: int, previous: Any = None) -> None:
        super().__init__()
        self.previous = previous
        self.name.default = str(bot.store.get(guild_id, "tempvoice_creator_name"))

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await run_setup(interaction, str(self.name), self.previous)


MODALS = {
    helpers.RENAME: lambda view: RenameModal(previous=view),
    helpers.LIMIT: lambda view: LimitModal(previous=view),
    helpers.BITRATE: lambda view: BitrateModal(view),
}


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
        await wait_ready(self.bot, self._reconcile_stopped)

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
        if not self._may_spawn_from(channel):
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
                source=room_source(store, guild.id, creator),
                allow=self._join_roles(guild),
                me=getattr(guild, "me", None),
                staff=reach_roles(self.bot, guild),
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

    def _may_spawn_from(self, channel: Any) -> bool:
        return may_spawn_from(self.bot, channel)

    def _creator_spot(self, guild: Any) -> tuple[Any, int, str]:
        return creator_spot(self.bot, guild)

    def _join_roles(self, guild: Any) -> list[Any]:
        return join_roles(self.bot, guild)

    def _lock(self, locks: dict[int, asyncio.Lock], key: int) -> asyncio.Lock:
        lock = locks.get(key)
        if lock is None:
            lock = locks[key] = asyncio.Lock()
        return lock

    async def _forget(self, guild: Any, channel_id: int, actor: Any = None) -> bool:
        return await forget_creator(self.bot, guild, channel_id, actor)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel) -> None:
        if not self.bot.db.is_connected:
            return
        await self._forget(channel.guild, channel.id)
        await delete_row(self.bot.db, channel.id)
        disown_channel(self.bot, channel.id)

    @app_commands.command(
        name="voice", description="Your temporary voice channel, and everything you can change"
    )
    async def voice_panel(self, interaction: discord.Interaction) -> None:
        if not await voice_gate(interaction):
            return
        embed, view = await build_panel(self.bot, interaction.guild, interaction.user)
        await interaction.response.send_message(
            embed=embed,
            view=view,
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        view.message = await interaction.original_response()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TempVoice(bot))
