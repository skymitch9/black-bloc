from __future__ import annotations

import logging
import re
from datetime import UTC, datetime, timedelta
from typing import Any

import discord

from .automod import TIMEOUT_MAX_SECONDS

log = logging.getLogger(__name__)

CASE_KINDS = (
    "warn",
    "timeout",
    "untimeout",
    "kick",
    "ban",
    "unban",
    "purge",
    "automod",
)

BAN_PURGE_MAX_DAYS = 7
PURGE_MAX = 100
CASES_PER_PAGE = 10
REASON_LIMIT = 500

DURATION_PATTERN = re.compile(
    r"^(?:(\d{1,4})w)?(?:(\d{1,5})d)?(?:(\d{1,6})h)?(?:(\d{1,7})m)?(?:(\d{1,8})s)?$"
)
DURATION_UNITS = (7 * 86400, 86400, 3600, 60, 1)

COLOURS: dict[str, int] = {
    "warn": 0xFEE75C,
    "timeout": 0xE67E22,
    "untimeout": 0x57F287,
    "kick": 0xED4245,
    "ban": 0x992D22,
    "unban": 0x57F287,
    "purge": 0x99AAB5,
    "automod": 0x5865F2,
}

DM_ACTIONS: dict[str, str] = {
    "warn": "warned",
    "timeout": "timed out",
    "untimeout": "let out of a timeout",
    "kick": "kicked",
    "ban": "banned",
    "unban": "unbanned",
    "automod": "warned by the automatic filter",
}

BAD_DURATION = (
    "**{given}** is not a length Black Bloc can read, so nothing was done. Write it as `10m`, "
    "`2h`, `1d` or `1h30m` — and keep it under 28 days, which is Discord's own ceiling for a "
    "timeout."
)
TEST_MODE_REFUSAL = (
    "Black Bloc is in **test mode**, so it refused to {action} anyone and logged what it would "
    "have done instead. Punishments start working when the owner turns test mode off — until "
    "then, do this one by hand if it is real."
)
NO_SUCH_CASE = (
    "Black Bloc has no case **#{case_id}**, so there is nothing to show. `/cases` lists the cases "
    "it has for one member."
)
NO_CASES = "Black Bloc has no cases for {who} yet."


def parse_duration(text: Any) -> int | None:
    """Seconds from `10m` / `2h` / `1d` / `1h30m`, or None when it cannot be read."""
    raw = str(text or "").strip().lower().replace(" ", "")
    if not raw:
        return None
    if raw.isdigit():
        return int(raw) * 60 or None
    match = DURATION_PATTERN.match(raw)
    if match is None or not any(match.groups()):
        return None
    seconds = sum(
        int(group or 0) * unit
        for group, unit in zip(match.groups(), DURATION_UNITS, strict=True)
    )
    return seconds or None


def describe_duration(seconds: Any) -> str:
    total = int(seconds or 0)
    if total <= 0:
        return "no time at all"
    parts = []
    for unit, label in ((86400, "d"), (3600, "h"), (60, "m"), (1, "s")):
        count, total = divmod(total, unit)
        if count:
            parts.append(f"{count}{label}")
    return " ".join(parts)


def clamp_timeout(seconds: Any) -> int:
    return max(0, min(int(seconds or 0), TIMEOUT_MAX_SECONDS))


def clamp_purge_days(days: Any) -> int:
    return max(0, min(int(days or 0), BAN_PURGE_MAX_DAYS))


def mentions() -> discord.AllowedMentions:
    """Nothing in a modlog embed or a DM may ping: reasons are staff text, names are theirs."""
    return discord.AllowedMentions.none()


def dm_text(style: Any, guild_name: Any, kind: str, reason: Any = None) -> str | None:
    """What the member is told, per `mod_dm_on_action`; None when they are told nothing."""
    if style == "none" or kind not in DM_ACTIONS:
        return None
    action = DM_ACTIONS[kind]
    line = f"You have been **{action}** in **{guild_name}**."
    if style == "server_action_reason" and str(reason or "").strip():
        line += f"\nReason: {str(reason).strip()[:REASON_LIMIT]}"
    return line


async def dm_member(user: Any, text: str | None) -> bool:
    """True when the member was told; a closed DM is never an error."""
    if not text:
        return False
    send = getattr(user, "send", None)
    if send is None:
        return False
    try:
        await send(text, allowed_mentions=mentions())
    except Exception as exc:
        log.info("mod: could not DM %s — %s: %s", getattr(user, "id", "?"), type(exc).__name__, exc)
        return False
    return True


def case_embed(
    *,
    case_id: Any,
    kind: str,
    user_id: int,
    moderator_id: int | None = None,
    reason: Any = None,
    duration_s: Any = None,
    applied: bool = True,
    mode: str | None = None,
    detail: Any = None,
    at: datetime | None = None,
) -> discord.Embed:
    """The one modlog card every mod action and every automod verdict posts."""
    title = f"Case #{case_id} — {kind}" if case_id else f"{kind} (no case)"
    embed = discord.Embed(
        title=title, colour=COLOURS.get(kind, COLOURS["automod"]), timestamp=at or datetime.now(UTC)
    )
    embed.add_field(name="Member", value=f"<@{user_id}>", inline=True)
    embed.add_field(
        name="Moderator", value=f"<@{moderator_id}>" if moderator_id else "Black Bloc", inline=True
    )
    if duration_s:
        embed.add_field(name="For", value=describe_duration(duration_s), inline=True)
    if detail:
        embed.add_field(name="What tripped it", value=str(detail)[:1024], inline=False)
    if str(reason or "").strip():
        embed.add_field(name="Reason", value=str(reason).strip()[:1024], inline=False)
    if not applied:
        embed.add_field(
            name="Not done",
            value=f"Black Bloc is in **{mode or 'shadow'}**, so nothing was done to them.",
            inline=False,
        )
    return embed


async def add_case(
    db: Any,
    guild_id: int,
    user_id: int,
    kind: str,
    *,
    moderator_id: int | None = None,
    reason: Any = None,
    duration_s: int | None = None,
    mode: str = "on",
    applied: bool = True,
) -> int | None:
    cur = await db.conn.execute(
        "INSERT INTO mod_cases(guild_id, user_id, kind, moderator_id, reason, duration_s, at, "
        "mode, applied) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            int(guild_id),
            int(user_id),
            kind,
            moderator_id,
            str(reason)[:REASON_LIMIT] if reason else None,
            duration_s,
            datetime.now(UTC).isoformat(),
            mode,
            1 if applied else 0,
        ),
    )
    await db.conn.commit()
    return cur.lastrowid


async def get_case(db: Any, case_id: int) -> Any:
    cur = await db.conn.execute("SELECT * FROM mod_cases WHERE id = ?", (int(case_id),))
    return await cur.fetchone()


async def set_case_applied(db: Any, case_id: int, applied: bool) -> None:
    await db.conn.execute(
        "UPDATE mod_cases SET applied = ? WHERE id = ?", (1 if applied else 0, int(case_id))
    )
    await db.conn.commit()


async def set_case_log_message(db: Any, case_id: int, message_id: int | None) -> None:
    if case_id is None or message_id is None:
        return
    await db.conn.execute(
        "UPDATE mod_cases SET log_message_id = ? WHERE id = ?", (int(message_id), int(case_id))
    )
    await db.conn.commit()


async def cases_for(db: Any, guild_id: int, user_id: int, limit: int, offset: int = 0) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT * FROM mod_cases WHERE guild_id = ? AND user_id = ? ORDER BY id DESC "
        "LIMIT ? OFFSET ?",
        (int(guild_id), int(user_id), int(limit), int(offset)),
    )
    return list(await cur.fetchall())


async def count_cases(db: Any, guild_id: int, user_id: int) -> int:
    cur = await db.conn.execute(
        "SELECT COUNT(*) AS n FROM mod_cases WHERE guild_id = ? AND user_id = ?",
        (int(guild_id), int(user_id)),
    )
    row = await cur.fetchone()
    return int(row["n"]) if row else 0


async def warn_count(db: Any, guild_id: int, user_id: int) -> int:
    cur = await db.conn.execute(
        "SELECT COUNT(*) AS n FROM mod_cases WHERE guild_id = ? AND user_id = ? "
        "AND kind IN ('warn', 'automod') AND applied = 1",
        (int(guild_id), int(user_id)),
    )
    row = await cur.fetchone()
    return int(row["n"]) if row else 0


async def shadow_verdicts_since(db: Any, guild_id: int, since: datetime) -> list[tuple[int, Any]]:
    cur = await db.conn.execute(
        "SELECT user_id, at FROM mod_cases WHERE guild_id = ? AND kind = 'automod' AND at >= ? "
        "ORDER BY id",
        (int(guild_id), since.isoformat()),
    )
    return [(int(row["user_id"]), row["at"]) for row in await cur.fetchall()]


def modlog_channel_id(store: Any, guild_id: int) -> int | None:
    return store.get(guild_id, "modlog_channel_id") or store.get(guild_id, "log_channel_id")


async def send_modlog(bot: Any, guild: Any, embed: discord.Embed, view: Any = None) -> int | None:
    """Post one case card to the modlog; a modlog that will not take it is never fatal."""
    channel_id = modlog_channel_id(bot.store, guild.id)
    if not channel_id:
        log.warning("mod: no modlog channel, so case card %r was not posted", embed.title)
        return None
    channel = bot.get_channel(channel_id) or guild.get_channel(channel_id)
    if channel is None:
        log.warning("mod: modlog channel %s is not visible", channel_id)
        return None
    guard = getattr(bot, "guard", None)
    if guard is not None and not guard.allows_channel(channel.id):
        log.warning("mod: TEST MODE — case card %r was not posted to %s", embed.title, channel_id)
        return None
    try:
        kwargs: dict[str, Any] = {"embed": embed, "allowed_mentions": mentions()}
        if view is not None:
            kwargs["view"] = view
        message = await channel.send(**kwargs)
    except Exception as exc:
        log.warning("mod: case card not posted — %s: %s", type(exc).__name__, exc)
        return None
    return getattr(message, "id", None)


def case_line(row: Any) -> str:
    when = str(row["at"])[:16].replace("T", " ")
    who = f"<@{row['moderator_id']}>" if row["moderator_id"] else "automod"
    tail = "" if row["applied"] else " *(not done)*"
    reason = f" — {row['reason']}" if row["reason"] else ""
    return f"**#{row['id']}** `{row['kind']}` {when} by {who}{reason}{tail}"


def duration_error(given: Any) -> str:
    return BAD_DURATION.format(given=str(given or "(nothing)")[:80])


def refusal_in_test_mode(action: str) -> str:
    return TEST_MODE_REFUSAL.format(action=action)


def within_days(days: Any, maximum: int) -> datetime:
    span = max(1, min(int(days or 1), maximum))
    return datetime.now(UTC) - timedelta(days=span)
