from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands

from ...actionlog import log_action, send_logs
from ...automod import TIMEOUT_MAX_SECONDS
from ...command_errors import AnswersErrors
from ...command_visibility import STAFF_ONLY
from ...logkinds import VIA_DISCORD, kind_via
from ...modcases import (
    ALREADY_RESTORED,
    ALREADY_VOIDED,
    BACK,
    BARE_ACTIONS_FOOTER,
    CASE_SELECT,
    CASES_HEADER,
    CASES_PER_PAGE,
    EDIT_REASON,
    EVERYONE,
    GRANTS,
    JUMP,
    LINK,
    LOGS,
    NEWER,
    NO_CASES,
    NO_SUCH_CASE,
    NOT_A_CASE_NUMBER,
    NOTE,
    NOTE_SAVED,
    NOTHING_IN_THE_NOTE,
    NOTHING_TO_SAY,
    OLDER,
    PANEL_TIMEOUT_FOOTER,
    PANEL_TITLE,
    PICK_A_CASE,
    PURGE_MAX,
    REASON_LIMIT,
    REASON_SAVED,
    REFRESH,
    RESTORE,
    RESTORED_SAID,
    USER_SELECT,
    VOID_NEEDS_A_REASON,
    VOID_UNDOES_NOTHING,
    VOIDED_SAID,
    WHOSE_CASES,
    add_case,
    card_buttons,
    card_embed_for,
    case_embed,
    case_is_void,
    case_line,
    case_status,
    cases_for,
    clamp_purge_days,
    clamp_timeout,
    clear_case_void,
    count_all_cases,
    count_cases,
    describe_duration,
    dm_member,
    dm_text,
    duration_error,
    edit_case_card,
    get_case,
    mark_case_void,
    page_count,
    panel_minutes,
    parse_duration,
    recent_cases,
    refusal_in_test_mode,
    root_buttons,
    row_value,
    send_modlog,
    set_case_log_message,
    set_case_reason,
    wanted_page,
    warn_count,
    write_case_note,
)
from ...panels import (
    NoteModal,
    Outcome,
    Panel,
    answer,
    clamped,
    db_up,
    opened,
    option_label,
    refusal,
    retire,
    site_page_url,
    still_staff,
)
from ...settings_store import DB_UNAVAILABLE, GUILD_ONLY, require_staff
from ..community.role_menus import open_grants_from

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
    "list and choose Copy User ID, or read it off the case in `/mod`."
)
NOT_BANNED = (
    "**{user_id}** is not on this server's ban list, so there was nothing to lift. `/mod` shows "
    "what Black Bloc has done."
)
BAD_COUNT = (
    "**{given}** is not a number of messages Black Bloc can delete, so nothing was deleted. Pick "
    f"a number between 1 and {PURGE_MAX} — Discord will not bulk-delete more than that at once."
)
WARN_THRESHOLD_REACHED = (
    " That is warning **{count}** — at or over the threshold of **{threshold}**, which Black Bloc "
    "only logs. Decide what happens next yourself."
)
THIS_SERVER = "this server"
NOBODY_TO_TELL = (
    "This case belongs to a channel rather than a member, so there is nobody to tell about it."
)
REASON_TITLE = "Why this case was opened"
REASON_LABEL = "The reason — it is on the case card"
NOTE_TITLE = "A note on this case"
NOTE_LABEL = "What the next moderator should know"
VOID_TITLE = "Void this case"
VOID_LABEL = "Why it was wrong — the member is told this"
JUMP_TITLE = "Open a case by number"
JUMP_LABEL = "The case number"
CASE_ID_LIMIT = 12

STYLES = {
    "primary": discord.ButtonStyle.primary,
    "secondary": discord.ButtonStyle.secondary,
    "success": discord.ButtonStyle.success,
    "danger": discord.ButtonStyle.danger,
}


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
    via: str = VIA_DISCORD,
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
        kind_via(f"mod.would_{kind}", via),
        actor=moderator,
        target=target_id,
        reason=reason,
        details={"case_id": case_id, "reason": "test_mode", "via": via},
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


async def warn_member(
    bot: Any, guild: Any, member: Any, moderator: Any, reason: Any, *, via: str = VIA_DISCORD
) -> str:
    await tell_member(bot, guild, member, "warn", reason)
    case_id = await record_case(bot, guild, member.id, "warn", moderator=moderator, reason=reason)
    await log_action(
        bot,
        guild,
        kind_via("mod.warned", via),
        actor=moderator,
        target=member,
        reason=reason,
        details={"case_id": case_id, "via": via},
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
    bot: Any,
    guild: Any,
    member: Any,
    moderator: Any,
    seconds: int,
    reason: Any,
    *,
    via: str = VIA_DISCORD,
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
        kind_via("mod.timed_out", via),
        actor=moderator,
        target=member,
        reason=reason,
        details={"case_id": case_id, "duration_s": clamp_timeout(seconds), "via": via},
    )
    return (
        f"Timed **{member.display_name}** out for {describe_duration(seconds)} — case "
        f"**#{case_id}**."
    )


async def untimeout_member(
    bot: Any, guild: Any, member: Any, moderator: Any, reason: Any, *, via: str = VIA_DISCORD
) -> str:
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
        kind_via("mod.untimed_out", via),
        actor=moderator,
        target=member,
        reason=reason,
        details={"case_id": case_id, "via": via},
    )
    return f"**{member.display_name}** is out of their timeout — case **#{case_id}**."


async def kick_member(
    bot: Any, guild: Any, member: Any, moderator: Any, reason: Any, *, via: str = VIA_DISCORD
) -> str:
    await tell_member(bot, guild, member, "kick", reason)
    try:
        await guild.kick(member, reason=audit_reason(moderator, reason))
    except discord.HTTPException as exc:
        return await note_failure(bot, guild, member, "kick", moderator, reason, exc)
    case_id = await record_case(bot, guild, member.id, "kick", moderator=moderator, reason=reason)
    await log_action(
        bot,
        guild,
        kind_via("mod.kicked", via),
        actor=moderator,
        target=member,
        reason=reason,
        details={"case_id": case_id, "via": via},
    )
    return f"Kicked **{member.display_name}** — case **#{case_id}**."


async def ban_member(
    bot: Any,
    guild: Any,
    member: Any,
    moderator: Any,
    reason: Any,
    purge_days: int = 0,
    *,
    via: str = VIA_DISCORD,
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
        kind_via("mod.banned", via),
        actor=moderator,
        target=member,
        reason=reason,
        details={"case_id": case_id, "purge_days": days, "via": via},
    )
    return (
        f"Banned **{member.display_name}** and deleted {days} day(s) of their messages — case "
        f"**#{case_id}**."
    )


async def unban_member(
    bot: Any, guild: Any, user_id: int, moderator: Any, reason: Any, *, via: str = VIA_DISCORD
) -> str:
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
        kind_via("mod.unbanned", via),
        actor=moderator,
        target=int(user_id),
        reason=reason,
        details={"case_id": case_id, "via": via},
    )
    return f"Lifted the ban on **{user_id}** — case **#{case_id}**."


# --- correcting the record, one function each, one write and one log row --------------------------


async def wanted_case(bot: Any, guild: Any, case_id: Any) -> Any:
    row = await get_case(bot.db, case_id)
    return None if row is None or row["guild_id"] != guild.id else row


async def rewrite_case_card(bot: Any, guild: Any, case_id: Any) -> None:
    row = await get_case(bot.db, case_id)
    if row is not None:
        await edit_case_card(bot, guild, row, card_embed_for(row))


async def tell_them_about_the_case(bot: Any, guild: Any, row: Any, kind: str, reason: Any) -> None:
    """A case that belongs to a channel has nobody to tell, and a closed DM is never an error."""
    user_id = row["user_id"]
    if not user_id:
        return
    member = guild.get_member(user_id)
    if member is None:
        return
    await tell_member(bot, guild, member, kind, reason)


async def edit_case_reason(
    bot: Any,
    guild: Any,
    case_id: Any,
    reason: Any,
    moderator: Any,
    *,
    via: str = VIA_DISCORD,
) -> Outcome:
    said = str(reason or "").strip()
    if not said:
        return refusal(NOTHING_TO_SAY, "bad_reason", 400)
    row = await wanted_case(bot, guild, case_id)
    if row is None:
        return refusal(NO_SUCH_CASE.format(case_id=case_id), "no_such_case", 404)
    await set_case_reason(bot.db, case_id, said)
    await log_action(
        bot,
        guild,
        kind_via("case.reason_edited", via),
        actor=moderator,
        target=row["user_id"],
        reason=said,
        details={"case_id": int(case_id), "via": via, "was": row["reason"]},
    )
    await rewrite_case_card(bot, guild, case_id)
    return Outcome(True, REASON_SAVED.format(case_id=case_id), value=int(case_id))


async def set_case_note(
    bot: Any,
    guild: Any,
    case_id: Any,
    note: Any,
    moderator: Any,
    *,
    via: str = VIA_DISCORD,
) -> Outcome:
    said = str(note or "").strip()
    if not said:
        return refusal(NOTHING_IN_THE_NOTE, "bad_note", 400)
    row = await wanted_case(bot, guild, case_id)
    if row is None:
        return refusal(NO_SUCH_CASE.format(case_id=case_id), "no_such_case", 404)
    await write_case_note(bot.db, case_id, said, getattr(moderator, "id", moderator))
    await log_action(
        bot,
        guild,
        kind_via("case.noted", via),
        actor=moderator,
        target=row["user_id"],
        details={"case_id": int(case_id), "via": via},
    )
    await rewrite_case_card(bot, guild, case_id)
    return Outcome(True, NOTE_SAVED.format(case_id=case_id), value=int(case_id))


async def void_case(
    bot: Any,
    guild: Any,
    case_id: Any,
    reason: Any,
    moderator: Any,
    *,
    via: str = VIA_DISCORD,
) -> Outcome:
    said = str(reason or "").strip()
    if not said:
        return refusal(VOID_NEEDS_A_REASON, "bad_reason", 400)
    row = await wanted_case(bot, guild, case_id)
    if row is None:
        return refusal(NO_SUCH_CASE.format(case_id=case_id), "no_such_case", 404)
    if not await mark_case_void(bot.db, case_id, getattr(moderator, "id", moderator), said):
        return refusal(ALREADY_VOIDED, "already_voided", 409)
    await log_action(
        bot,
        guild,
        kind_via("case.voided", via),
        actor=moderator,
        target=row["user_id"],
        reason=said,
        details={"case_id": int(case_id), "via": via, "kind": row["kind"]},
    )
    await tell_them_about_the_case(bot, guild, row, "void", said)
    await rewrite_case_card(bot, guild, case_id)
    return Outcome(True, VOIDED_SAID.format(case_id=case_id), value=int(case_id))


async def restore_case(
    bot: Any, guild: Any, case_id: Any, moderator: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    row = await wanted_case(bot, guild, case_id)
    if row is None:
        return refusal(NO_SUCH_CASE.format(case_id=case_id), "no_such_case", 404)
    if not await clear_case_void(bot.db, case_id):
        return refusal(ALREADY_RESTORED, "not_voided", 409)
    await log_action(
        bot,
        guild,
        kind_via("case.restored", via),
        actor=moderator,
        target=row["user_id"],
        details={"case_id": int(case_id), "via": via, "kind": row["kind"]},
    )
    await tell_them_about_the_case(bot, guild, row, "restore", None)
    await rewrite_case_card(bot, guild, case_id)
    return Outcome(True, RESTORED_SAID.format(case_id=case_id), value=int(case_id))


class ModCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="mod", description="What Black Bloc has done to members")
    @app_commands.default_permissions(STAFF_ONLY)
    @app_commands.describe(member="Only this member's cases")
    async def mod(
        self, interaction: discord.Interaction, member: discord.Member | None = None
    ) -> None:
        if interaction.guild is None:
            await answer(interaction, GUILD_ONLY)
            return
        if not await require_staff(interaction):
            return
        if not await db_up(interaction):
            return
        embed, view = await build_root(
            self.bot, interaction.guild, page=1, user_id=member.id if member else None
        )
        await interaction.response.send_message(
            embed=embed,
            view=view,
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        view.message = await interaction.original_response()

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
    @app_commands.default_permissions(STAFF_ONLY)
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
    @app_commands.default_permissions(STAFF_ONLY)
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
    @app_commands.default_permissions(STAFF_ONLY)
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
    @app_commands.default_permissions(STAFF_ONLY)
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
    @app_commands.default_permissions(STAFF_ONLY)
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
    @app_commands.default_permissions(STAFF_ONLY)
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
    @app_commands.default_permissions(STAFF_ONLY)
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


# --- the panel -----------------------------------------------------------------------------------


class ModPanel(Panel):
    def __init__(
        self, minutes: int, *, page: int = 1, user_id: Any = None, case_id: Any = None
    ) -> None:
        super().__init__(minutes, footer=PANEL_TIMEOUT_FOOTER)
        self.page = int(page)
        self.user_id = user_id
        self.case_id = case_id


async def build_root(bot: Any, guild: Any, *, page: Any, user_id: Any) -> tuple[Any, ModPanel]:
    total = (
        await count_cases(bot.db, guild.id, user_id)
        if user_id
        else await count_all_cases(bot.db, guild.id)
    )
    pages = page_count(total)
    at = wanted_page(page, pages)
    offset = (at - 1) * CASES_PER_PAGE
    rows = (
        await cases_for(bot.db, guild.id, user_id, CASES_PER_PAGE, offset)
        if user_id
        else await recent_cases(bot.db, guild.id, CASES_PER_PAGE, offset)
    )
    who = f"<@{user_id}>" if user_id else THIS_SERVER
    if total:
        lines = [CASES_HEADER.format(total=total, who=who, page=at, pages=pages), ""]
        lines += [case_line(row) for row in rows]
    else:
        lines = [NO_CASES.format(who=who)]
    embed = discord.Embed(title=PANEL_TITLE, description=clamped(lines))
    embed.set_footer(text=BARE_ACTIONS_FOOTER)
    view = ModPanel(panel_minutes(bot.store, guild.id), page=at, user_id=user_id)
    url = site_page_url(getattr(getattr(bot, "settings", None), "origin", ""), "mod")
    for move in root_buttons(
        has_rows=bool(rows),
        page=at,
        pages=pages,
        filtered=user_id is not None,
        has_site=url is not None,
    ):
        add_control(view, move, rows=rows, url=url)
    return (embed, view)


def add_control(view: Any, move: Any, *, rows: Any = (), url: Any = None) -> None:
    if move.kind == CASE_SELECT:
        view.add_item(CasePick(rows))
    elif move.kind == USER_SELECT:
        view.add_item(WhosePick())
    elif move.kind == LINK:
        view.add_item(SiteButton(move, url))
    else:
        view.add_item(MoveButton(move))


async def build_card(
    bot: Any, guild: Any, case_id: Any, previous: Any
) -> tuple[Any, ModPanel] | None:
    row = await wanted_case(bot, guild, case_id)
    if row is None:
        return None
    embed = card_embed_for(row)
    said = [] if case_is_void(row) else [VOID_UNDOES_NOTHING]
    if not row["user_id"]:
        said.append(NOBODY_TO_TELL)
    embed.description = "\n\n".join(said) or None
    view = ModPanel(
        panel_minutes(bot.store, guild.id),
        page=getattr(previous, "page", 1),
        user_id=getattr(previous, "user_id", None),
        case_id=int(row["id"]),
    )
    for move in card_buttons(row):
        view.add_item(MoveButton(move))
    return (embed, view)


async def show(interaction: discord.Interaction, built: Any, previous: Any) -> None:
    embed, view = built
    retire(previous)
    view.message = await interaction.edit_original_response(
        embed=embed, view=view, allowed_mentions=discord.AllowedMentions.none()
    )


async def render_root(
    interaction: discord.Interaction, *, page: Any, user_id: Any, previous: Any = None
) -> None:
    built = await build_root(interaction.client, interaction.guild, page=page, user_id=user_id)
    await show(interaction, built, previous)


async def open_case(interaction: discord.Interaction, case_id: Any, previous: Any) -> None:
    """A number that is nothing answers a NEW message and leaves the panel exactly as it was."""
    built = await build_card(interaction.client, interaction.guild, case_id, previous)
    if built is None:
        await answer(interaction, NO_SUCH_CASE.format(case_id=case_id))
        return
    await show(interaction, built, previous)


async def navigate(interaction: discord.Interaction, action: str, view: Any) -> None:
    if not await opened(interaction):
        return
    if action == BACK:
        await render_root(interaction, page=view.page, user_id=view.user_id, previous=view)
    elif action == EVERYONE:
        await render_root(interaction, page=1, user_id=None, previous=view)
    elif action == NEWER:
        await render_root(interaction, page=view.page - 1, user_id=view.user_id, previous=view)
    elif action == OLDER:
        await render_root(interaction, page=view.page + 1, user_id=view.user_id, previous=view)
    elif action == REFRESH and view.case_id is None:
        await render_root(interaction, page=view.page, user_id=view.user_id, previous=view)
    else:
        await open_case(interaction, view.case_id, view)


def home_of(previous: Any) -> Any:
    """Back from the Grants console lands on the /mod page and filter it was opened from."""
    page, user_id = previous.page, previous.user_id

    async def home(interaction: discord.Interaction, view: Any) -> None:
        if not await opened(interaction):
            return
        await render_root(interaction, page=page, user_id=user_id, previous=view)

    return home


async def run_move(interaction: discord.Interaction, move: Any, rest: Any, view: Any) -> None:
    """A refused move is answered and the card is NOT re-rendered, so it cannot read as a save."""
    if not await opened(interaction):
        return
    outcome = await move(
        interaction.client, interaction.guild, view.case_id, *rest, interaction.user
    )
    if not outcome.ok:
        await answer(interaction, outcome.message)
        return
    await open_case(interaction, view.case_id, view)
    await answer(interaction, outcome.message)


class MoveButton(discord.ui.Button):
    def __init__(self, move: Any) -> None:
        super().__init__(label=move.label, style=STYLES[move.style], row=move.row)
        self.move = move

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        if self.move.action == LOGS:
            await send_logs(interaction, "mod")
            return
        if self.move.modal:
            await self.open_modal(interaction, view)
            return
        if self.move.action == RESTORE:
            await run_move(interaction, restore_case, (), view)
            return
        if self.move.action == GRANTS:
            await open_grants_from(interaction, view, home_of(view))
            return
        await navigate(interaction, self.move.action, view)

    async def open_modal(self, interaction: discord.Interaction, view: Any) -> None:
        if not await still_staff(interaction):
            return
        if not await db_up(interaction):
            return
        if self.move.action == JUMP:
            await interaction.response.send_modal(JumpModal(view))
            return
        row = await wanted_case(interaction.client, interaction.guild, view.case_id)
        if row is None:
            await answer(interaction, NO_SUCH_CASE.format(case_id=view.case_id))
            return
        await interaction.response.send_modal(modal_for(self.move.action, row, view))


def modal_for(action: str, row: Any, view: Any) -> Any:
    if action == EDIT_REASON:
        return PrefilledModal(
            title=REASON_TITLE,
            label=REASON_LABEL,
            max_length=REASON_LIMIT,
            default=str(row["reason"] or ""),
            on_submit=submits(edit_case_reason, view),
        )
    if action == NOTE:
        return PrefilledModal(
            title=NOTE_TITLE,
            label=NOTE_LABEL,
            max_length=REASON_LIMIT,
            default=str(row_value(row, "note") or ""),
            on_submit=submits(set_case_note, view),
        )
    return PrefilledModal(
        title=VOID_TITLE,
        label=VOID_LABEL,
        max_length=REASON_LIMIT,
        on_submit=submits(void_case, view),
    )


def submits(move: Any, view: Any) -> Any:
    async def taken(interaction: discord.Interaction, given: str) -> None:
        await run_move(interaction, move, (given,), view)

    return taken


class PrefilledModal(NoteModal):
    """`panels.NoteModal` cannot prefill; the conductor folds `default=` into it at the merge."""

    def __init__(self, *, default: str = "", **rest: Any) -> None:
        super().__init__(**rest)
        self.note.default = default or None


class JumpModal(AnswersErrors, discord.ui.Modal):
    number = discord.ui.TextInput(label=JUMP_LABEL, max_length=CASE_ID_LIMIT)

    def __init__(self, previous: Any = None) -> None:
        super().__init__(title=JUMP_TITLE)
        self.previous = previous

    async def on_submit(self, interaction: discord.Interaction) -> None:
        given = str(self.number).strip()
        if not given.isdigit():
            await answer(interaction, NOT_A_CASE_NUMBER.format(given=given[:40] or "nothing"))
            return
        if not await opened(interaction):
            return
        await open_case(interaction, int(given), self.previous)


class SiteButton(discord.ui.Button):
    def __init__(self, move: Any, url: str) -> None:
        super().__init__(label=move.label, style=discord.ButtonStyle.link, url=url, row=move.row)


class CasePick(discord.ui.Select):
    def __init__(self, rows: Any) -> None:
        super().__init__(
            placeholder=PICK_A_CASE,
            options=[
                discord.SelectOption(
                    label=option_label(row["id"], case_status(row), row["reason"]),
                    value=str(row["id"]),
                )
                for row in rows
            ],
            min_values=1,
            max_values=1,
            row=0,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await opened(interaction):
            return
        await open_case(interaction, int(self.values[0]), self.view)


class WhosePick(discord.ui.UserSelect):
    def __init__(self) -> None:
        super().__init__(placeholder=WHOSE_CASES, min_values=1, max_values=1, row=1)

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await opened(interaction):
            return
        await render_root(interaction, page=1, user_id=self.values[0].id, previous=self.view)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ModCommands(bot))
