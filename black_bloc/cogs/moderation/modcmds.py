from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands

from ...actionlog import (
    LOGS_DEFAULT,
    LOGS_MAX,
    LOGS_MIN,
    log_action,
    send_logs,
)
from ...automod import TIMEOUT_MAX_SECONDS
from ...modcases import (
    CASES_PER_PAGE,
    PURGE_MAX,
    add_case,
    case_embed,
    case_line,
    cases_for,
    clamp_purge_days,
    clamp_timeout,
    count_cases,
    describe_duration,
    dm_member,
    dm_text,
    duration_error,
    get_case,
    pages_under_limit,
    parse_duration,
    refusal_in_test_mode,
    send_modlog,
    set_case_log_message,
    warn_count,
)
from ...settings_store import DB_UNAVAILABLE, require_staff

log = logging.getLogger(__name__)

TIMEOUT_TOO_LONG = (
    "Discord itself refuses a timeout longer than 28 days, so nobody was timed out. Pick a length "
    "up to `28d` — anything longer has to be a ban."
)
REFUSED = {
    "timeout": (
        "Discord refused the timeout, so nothing was done to them. Black Bloc needs the Moderate "
        "Members permission and its own role has to sit above theirs in Server Settings → Roles. "
        "Ask an admin to fix that, then do it by hand."
    ),
    "untimeout": (
        "Discord refused to lift the timeout, so it is still running. Black Bloc needs the "
        "Moderate Members permission and its own role has to sit above theirs. Ask an admin to fix "
        "that, then lift it by hand."
    ),
    "kick": (
        "Discord refused the kick, so they are still here. Black Bloc needs the Kick Members "
        "permission and its own role has to sit above theirs in Server Settings → Roles. Ask an "
        "admin to fix that, then kick by hand."
    ),
    "ban": (
        "Discord refused the ban, so they are still here. Black Bloc needs the Ban Members "
        "permission and its own role has to sit above theirs in Server Settings → Roles. Ask an "
        "admin to fix that, then ban by hand."
    ),
    "unban": (
        "Discord refused the unban, so they are still banned. Black Bloc needs the Ban Members "
        "permission. Ask an admin to give it that, then lift the ban by hand."
    ),
    "purge": (
        "Discord refused to delete those messages, so they are still there. Black Bloc needs the "
        "Manage Messages permission in this channel, and Discord will not bulk-delete anything "
        "older than 14 days. Ask an admin to check the permission, then try a smaller number."
    ),
}
NOT_AN_ID = (
    "**{given}** is not a member id, so nobody was unbanned. Right-click the account in the ban "
    "list and choose Copy User ID, or read it out of `/case`."
)
NOT_BANNED = (
    "**{user_id}** is not on this server's ban list, so there was nothing to lift. `/case` and "
    "`/cases` show what Black Bloc has done."
)
BAD_COUNT = (
    "**{given}** is not a number of messages Black Bloc can delete, so nothing was deleted. Pick "
    f"a number between 1 and {PURGE_MAX} — Discord will not bulk-delete more than that at once."
)
NO_SUCH_CASE = (
    "Black Bloc has no case **#{case_id}**, so there is nothing to show. `/cases` lists the cases "
    "it has for one member."
)
NO_CASES = "Black Bloc has no cases for <@{user_id}> yet."
WARN_THRESHOLD_REACHED = (
    " That is warning **{count}** — at or over the threshold of **{threshold}**, which Black Bloc "
    "only logs. Decide what happens next yourself."
)


def in_test_mode(bot: Any) -> bool:
    return getattr(bot, "guard", None) is not None


def audit_reason(moderator: Any, reason: Any) -> str:
    who = getattr(moderator, "display_name", getattr(moderator, "id", moderator))
    return f"{who}: {reason}" if reason else f"{who} (no reason given)"


async def record_case(
    bot: Any,
    guild: Any,
    user_id: int | None,
    kind: str,
    *,
    moderator: Any = None,
    reason: Any = None,
    duration_s: int | None = None,
    applied: bool = True,
    mode: str = "on",
    detail: Any = None,
    channel_id: int | None = None,
) -> int | None:
    """One case row and its modlog card; the one place either is written."""
    case_id = await add_case(
        bot.db,
        guild.id,
        user_id,
        kind,
        moderator_id=getattr(moderator, "id", None),
        reason=reason,
        duration_s=duration_s,
        mode=mode,
        applied=applied,
        channel_id=channel_id,
    )
    message_id = await send_modlog(
        bot,
        guild,
        case_embed(
            case_id=case_id,
            kind=kind,
            user_id=user_id,
            moderator_id=getattr(moderator, "id", None),
            reason=reason,
            duration_s=duration_s,
            applied=applied,
            mode=mode,
            detail=detail,
            channel_id=channel_id,
        ),
    )
    await set_case_log_message(bot.db, case_id, message_id)
    return case_id


async def refuse_in_test_mode(
    bot: Any,
    guild: Any,
    target: Any,
    kind: str,
    wording: str,
    *,
    moderator: Any = None,
    reason: Any = None,
    duration_s: int | None = None,
    channel_id: int | None = None,
) -> str:
    """Record what would have happened and give back the refusal to say."""
    target_id = getattr(target, "id", target)
    case_id = await record_case(
        bot,
        guild,
        target_id,
        kind,
        moderator=moderator,
        reason=reason,
        duration_s=duration_s,
        applied=False,
        mode="test_mode",
        channel_id=channel_id,
    )
    await log_action(
        bot,
        guild,
        f"mod.would_{kind}",
        actor=moderator,
        target=target_id,
        reason=reason,
        details={"case_id": case_id, "reason": "test_mode"},
    )
    return refusal_in_test_mode(wording)


async def note_failure(
    bot: Any, guild: Any, target: Any, kind: str, moderator: Any, reason: Any, exc: Exception
) -> str:
    target_id = getattr(target, "id", target)
    log.warning("mod: %s refused for %s: %s", kind, target_id, exc)
    await log_action(
        bot,
        guild,
        f"mod.{kind}_failed",
        actor=moderator,
        target=target_id,
        reason=reason,
        details={"reason": f"{type(exc).__name__}: {exc}"},
    )
    return REFUSED[kind]


async def tell_member(
    bot: Any, guild: Any, member: Any, kind: str, reason: Any, duration_s: Any = None
) -> None:
    await dm_member(
        member,
        dm_text(
            bot.store.get(guild.id, "mod_dm_on_action"),
            guild.name,
            kind,
            reason,
            duration_s=duration_s,
        ),
    )


async def warn_member(bot: Any, guild: Any, member: Any, moderator: Any, reason: Any) -> str:
    await tell_member(bot, guild, member, "warn", reason)
    case_id = await record_case(bot, guild, member.id, "warn", moderator=moderator, reason=reason)
    await log_action(
        bot,
        guild,
        "mod.warned",
        actor=moderator,
        target=member,
        reason=reason,
        details={"case_id": case_id},
    )
    count = await warn_count(bot.db, guild.id, member.id)
    threshold = int(bot.store.get(guild.id, "automod_warn_threshold") or 0)
    tail = ""
    if threshold and count >= threshold:
        tail = WARN_THRESHOLD_REACHED.format(count=count, threshold=threshold)
        await log_action(
            bot,
            guild,
            "mod.warn_threshold",
            actor=moderator,
            target=member,
            details={"case_id": case_id, "count": count, "threshold": threshold},
        )
    return f"Warned **{member.display_name}** — case **#{case_id}**.{tail}"


async def timeout_member(
    bot: Any, guild: Any, member: Any, moderator: Any, seconds: int, reason: Any
) -> str:
    try:
        await member.timeout(
            timedelta(seconds=clamp_timeout(seconds)), reason=audit_reason(moderator, reason)
        )
    except discord.HTTPException as exc:
        return await note_failure(bot, guild, member, "timeout", moderator, reason, exc)
    await tell_member(bot, guild, member, "timeout", reason, duration_s=clamp_timeout(seconds))
    case_id = await record_case(
        bot,
        guild,
        member.id,
        "timeout",
        moderator=moderator,
        reason=reason,
        duration_s=clamp_timeout(seconds),
    )
    await log_action(
        bot,
        guild,
        "mod.timed_out",
        actor=moderator,
        target=member,
        reason=reason,
        details={"case_id": case_id, "duration_s": clamp_timeout(seconds)},
    )
    return (
        f"Timed **{member.display_name}** out for {describe_duration(seconds)} — case "
        f"**#{case_id}**."
    )


async def untimeout_member(bot: Any, guild: Any, member: Any, moderator: Any, reason: Any) -> str:
    try:
        await member.timeout(None, reason=audit_reason(moderator, reason))
    except discord.HTTPException as exc:
        return await note_failure(bot, guild, member, "untimeout", moderator, reason, exc)
    await tell_member(bot, guild, member, "untimeout", reason)
    case_id = await record_case(
        bot, guild, member.id, "untimeout", moderator=moderator, reason=reason
    )
    await log_action(
        bot,
        guild,
        "mod.untimed_out",
        actor=moderator,
        target=member,
        reason=reason,
        details={"case_id": case_id},
    )
    return f"**{member.display_name}** is out of their timeout — case **#{case_id}**."


async def kick_member(bot: Any, guild: Any, member: Any, moderator: Any, reason: Any) -> str:
    await tell_member(bot, guild, member, "kick", reason)
    try:
        await guild.kick(member, reason=audit_reason(moderator, reason))
    except discord.HTTPException as exc:
        return await note_failure(bot, guild, member, "kick", moderator, reason, exc)
    case_id = await record_case(bot, guild, member.id, "kick", moderator=moderator, reason=reason)
    await log_action(
        bot,
        guild,
        "mod.kicked",
        actor=moderator,
        target=member,
        reason=reason,
        details={"case_id": case_id},
    )
    return f"Kicked **{member.display_name}** — case **#{case_id}**."


async def ban_member(
    bot: Any, guild: Any, member: Any, moderator: Any, reason: Any, purge_days: int = 0
) -> str:
    days = clamp_purge_days(purge_days)
    await tell_member(bot, guild, member, "ban", reason)
    try:
        await guild.ban(
            member, reason=audit_reason(moderator, reason), delete_message_seconds=days * 86400
        )
    except discord.HTTPException as exc:
        return await note_failure(bot, guild, member, "ban", moderator, reason, exc)
    case_id = await record_case(
        bot,
        guild,
        member.id,
        "ban",
        moderator=moderator,
        reason=reason,
        detail=f"{days} day(s) of their messages deleted",
    )
    await log_action(
        bot,
        guild,
        "mod.banned",
        actor=moderator,
        target=member,
        reason=reason,
        details={"case_id": case_id, "purge_days": days},
    )
    return (
        f"Banned **{member.display_name}** and deleted {days} day(s) of their messages — case "
        f"**#{case_id}**."
    )


async def unban_member(bot: Any, guild: Any, user_id: int, moderator: Any, reason: Any) -> str:
    try:
        await guild.unban(discord.Object(id=int(user_id)), reason=audit_reason(moderator, reason))
    except discord.NotFound:
        return NOT_BANNED.format(user_id=user_id)
    except discord.HTTPException as exc:
        return await note_failure(bot, guild, int(user_id), "unban", moderator, reason, exc)
    case_id = await record_case(
        bot, guild, int(user_id), "unban", moderator=moderator, reason=reason
    )
    await log_action(
        bot,
        guild,
        "mod.unbanned",
        actor=moderator,
        target=int(user_id),
        reason=reason,
        details={"case_id": case_id},
    )
    return f"Lifted the ban on **{user_id}** — case **#{case_id}**."


class ModCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    mod = app_commands.Group(name="mod", description="What Black Bloc has done to members")

    @mod.command(name="logs", description="The last few moderation log lines")
    @app_commands.describe(
        count="How many lines, 1 to 50 (10 by default)",
        important_only="True to leave out the dry runs and the housekeeping",
    )
    async def mod_logs(
        self,
        interaction: discord.Interaction,
        count: app_commands.Range[int, LOGS_MIN, LOGS_MAX] = LOGS_DEFAULT,
        important_only: bool = False,
    ) -> None:
        await send_logs(interaction, "mod", count=count, important_only=important_only)

    def _in_test_mode(self) -> bool:
        return in_test_mode(self.bot)

    async def _ready(self, interaction: discord.Interaction) -> bool:
        if not await require_staff(interaction):
            return False
        if not self.bot.db.is_connected:
            log.warning("mod: refused a command — the database is not connected")
            await interaction.response.send_message(DB_UNAVAILABLE, ephemeral=True)
            return False
        return True

    async def _record(self, guild: Any, user_id: int | None, kind: str, **rest: Any) -> int | None:
        return await record_case(self.bot, guild, user_id, kind, **rest)

    async def _refuse_in_test_mode(
        self,
        interaction: discord.Interaction,
        member: Any,
        kind: str,
        wording: str,
        *,
        reason: Any = None,
        duration_s: int | None = None,
        deferred: bool = False,
        channel_id: int | None = None,
    ) -> None:
        said = await refuse_in_test_mode(
            self.bot,
            interaction.guild,
            member,
            kind,
            wording,
            moderator=interaction.user,
            reason=reason,
            duration_s=duration_s,
            channel_id=channel_id,
        )
        answer = interaction.followup.send if deferred else interaction.response.send_message
        await answer(said, ephemeral=True)

    async def _tell(
        self, guild: Any, member: Any, kind: str, reason: Any, duration_s: Any = None
    ) -> None:
        await tell_member(self.bot, guild, member, kind, reason, duration_s=duration_s)

    @app_commands.command(name="warn", description="Warn a member and record it")
    @app_commands.describe(member="Who to warn", reason="Why — they are told this")
    async def warn(
        self, interaction: discord.Interaction, member: discord.Member, reason: str
    ) -> None:
        if not await self._ready(interaction):
            return
        await interaction.response.send_message(
            await warn_member(self.bot, interaction.guild, member, interaction.user, reason),
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @app_commands.command(name="timeout", description="Time a member out")
    @app_commands.describe(
        member="Who to time out", duration="How long — 10m, 2h, 1d (28 days at most)",
        reason="Why — they are told this",
    )
    async def timeout(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        duration: str,
        reason: str | None = None,
    ) -> None:
        if not await self._ready(interaction):
            return
        seconds = parse_duration(duration)
        if seconds is None:
            await interaction.response.send_message(duration_error(duration), ephemeral=True)
            return
        if seconds > TIMEOUT_MAX_SECONDS:
            await interaction.response.send_message(TIMEOUT_TOO_LONG, ephemeral=True)
            return
        if self._in_test_mode():
            await self._refuse_in_test_mode(
                interaction, member, "timeout", "time out", reason=reason, duration_s=seconds
            )
            return
        await interaction.response.send_message(
            await timeout_member(
                self.bot, interaction.guild, member, interaction.user, seconds, reason
            ),
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @app_commands.command(name="untimeout", description="Lift a member's timeout early")
    @app_commands.describe(member="Who to let out", reason="Why")
    async def untimeout(
        self, interaction: discord.Interaction, member: discord.Member, reason: str | None = None
    ) -> None:
        if not await self._ready(interaction):
            return
        if self._in_test_mode():
            await self._refuse_in_test_mode(
                interaction, member, "untimeout", "lift anyone's timeout", reason=reason
            )
            return
        await interaction.response.send_message(
            await untimeout_member(
                self.bot, interaction.guild, member, interaction.user, reason
            ),
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @app_commands.command(name="kick", description="Kick a member out of the server")
    @app_commands.describe(member="Who to kick", reason="Why — they are told this")
    async def kick(
        self, interaction: discord.Interaction, member: discord.Member, reason: str | None = None
    ) -> None:
        if not await self._ready(interaction):
            return
        if self._in_test_mode():
            await self._refuse_in_test_mode(interaction, member, "kick", "kick", reason=reason)
            return
        await interaction.response.send_message(
            await kick_member(self.bot, interaction.guild, member, interaction.user, reason),
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @app_commands.command(name="ban", description="Ban a member from the server")
    @app_commands.describe(
        member="Who to ban",
        reason="Why — they are told this",
        purge_days="Days of their messages to delete with them, 0 to 7",
    )
    async def ban(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str | None = None,
        purge_days: int = 0,
    ) -> None:
        if not await self._ready(interaction):
            return
        if self._in_test_mode():
            await self._refuse_in_test_mode(interaction, member, "ban", "ban", reason=reason)
            return
        await interaction.response.send_message(
            await ban_member(
                self.bot, interaction.guild, member, interaction.user, reason, purge_days
            ),
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @app_commands.command(name="unban", description="Lift a ban")
    @app_commands.describe(user_id="The banned account's id", reason="Why")
    async def unban(
        self, interaction: discord.Interaction, user_id: str, reason: str | None = None
    ) -> None:
        if not await self._ready(interaction):
            return
        digits = str(user_id).strip().lstrip("<@!").rstrip(">")
        if not digits.isdigit():
            await interaction.response.send_message(
                NOT_AN_ID.format(given=user_id), ephemeral=True
            )
            return
        if self._in_test_mode():
            await self._refuse_in_test_mode(
                interaction, int(digits), "unban", "lift anyone's ban", reason=reason
            )
            return
        await interaction.response.send_message(
            await unban_member(
                self.bot, interaction.guild, int(digits), interaction.user, reason
            ),
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @app_commands.command(name="purge", description="Delete the last few messages in this channel")
    @app_commands.describe(
        count=f"How many messages to look at, 1 to {PURGE_MAX}",
        member="Only delete this member's messages",
    )
    async def purge(
        self,
        interaction: discord.Interaction,
        count: int,
        member: discord.Member | None = None,
    ) -> None:
        if not await self._ready(interaction):
            return
        if not 1 <= int(count) <= PURGE_MAX:
            await interaction.response.send_message(
                BAD_COUNT.format(given=count), ephemeral=True
            )
            return
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        target_id = member.id if member is not None else None
        if self._in_test_mode():
            await self._refuse_in_test_mode(
                interaction,
                target_id,
                "purge",
                "delete anyone's messages",
                deferred=True,
                channel_id=interaction.channel_id,
            )
            return
        check = (lambda m: m.author.id == member.id) if member is not None else None
        try:
            deleted = await interaction.channel.purge(limit=int(count), check=check)
        except discord.HTTPException as exc:
            log.warning("mod: purge refused in %s: %s", interaction.channel_id, exc)
            await log_action(
                self.bot,
                guild,
                "mod.purge_failed",
                actor=interaction.user,
                target=target_id,
                details={
                    "channel_id": interaction.channel_id,
                    "reason": f"{type(exc).__name__}: {exc}",
                },
            )
            await interaction.followup.send(REFUSED["purge"], ephemeral=True)
            return
        case_id = await self._record(
            guild,
            target_id,
            "purge",
            moderator=interaction.user,
            detail=f"{len(deleted)} message(s) in <#{interaction.channel_id}>",
            channel_id=interaction.channel_id,
        )
        await log_action(
            self.bot,
            guild,
            "mod.purged",
            actor=interaction.user,
            target=target_id,
            details={
                "case_id": case_id,
                "channel_id": interaction.channel_id,
                "deleted": len(deleted),
            },
        )
        await interaction.followup.send(
            f"Deleted {len(deleted)} message(s) — case **#{case_id}**.", ephemeral=True
        )

    @app_commands.command(name="case", description="Show one mod case")
    @app_commands.describe(case_id="The case number")
    async def case(self, interaction: discord.Interaction, case_id: int) -> None:
        if not await self._ready(interaction):
            return
        row = await get_case(self.bot.db, case_id)
        if row is None or row["guild_id"] != interaction.guild.id:
            await interaction.response.send_message(
                NO_SUCH_CASE.format(case_id=case_id), ephemeral=True
            )
            return
        await interaction.response.send_message(
            embed=case_embed(
                case_id=row["id"],
                kind=row["kind"],
                user_id=row["user_id"],
                moderator_id=row["moderator_id"],
                reason=row["reason"],
                duration_s=row["duration_s"],
                applied=bool(row["applied"]),
                mode=row["mode"],
            ),
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @app_commands.command(name="cases", description="List a member's mod cases")
    @app_commands.describe(member="Whose cases", page="Which page, starting at 1")
    async def cases(
        self, interaction: discord.Interaction, member: discord.Member, page: int = 1
    ) -> None:
        if not await self._ready(interaction):
            return
        guild = interaction.guild
        total = await count_cases(self.bot.db, guild.id, member.id)
        if not total:
            await interaction.response.send_message(
                NO_CASES.format(user_id=member.id),
                ephemeral=True,
                allowed_mentions=discord.AllowedMentions.none(),
            )
            return
        pages = max(1, -(-total // CASES_PER_PAGE))
        wanted = max(1, min(int(page or 1), pages))
        rows = await cases_for(
            self.bot.db, guild.id, member.id, CASES_PER_PAGE, (wanted - 1) * CASES_PER_PAGE
        )
        lines = [f"**{total}** case(s) for <@{member.id}> — page {wanted} of {pages}"]
        lines += [case_line(row) for row in rows]
        if wanted < pages:
            lines.append(f"`/cases member:{member.display_name} page:{wanted + 1}` for more.")
        await self._say_in_chunks(interaction, pages_under_limit(lines))

    async def _say_in_chunks(
        self, interaction: discord.Interaction, chunks: list[str]
    ) -> None:
        for index, chunk in enumerate(chunks):
            answer = interaction.followup.send if index else interaction.response.send_message
            await answer(
                chunk, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
            )

    def _audit(self, interaction: discord.Interaction, reason: Any) -> str:
        return audit_reason(interaction.user, reason)

    async def _failed(
        self, interaction: discord.Interaction, target: Any, kind: str, reason: Any, exc: Exception
    ) -> None:
        said = await note_failure(
            self.bot, interaction.guild, target, kind, interaction.user, reason, exc
        )
        await interaction.response.send_message(said, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ModCommands(bot))
