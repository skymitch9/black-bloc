from __future__ import annotations

import logging
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands

from ...actionlog import LOGS_DEFAULT, LOGS_MAX, LOGS_MIN, log_action, send_logs
from ...command_errors import NETWORK_ERRORS, AnswersErrors
from ...requests import (
    ALREADY_THAT,
    APPROVED,
    DECLINE_NEEDS_A_REASON,
    DECLINED,
    DM_STATUSES,
    DM_TEXT,
    FILED,
    FILED_APPROVED,
    LIST_PAGE,
    NO_SUCH_REQUEST,
    NOT_PENDING,
    NOT_YOURS,
    NOTHING_FILED_YET,
    NOTHING_OF_YOURS,
    NOTHING_PENDING,
    NOTIFY_LINE,
    PENDING,
    REASON_LIMIT,
    REQUESTS_OFF,
    STAFF_ONLY_FILES,
    STAFF_STATUSES,
    STATUS_WORDS,
    WHAT_LIMIT,
    WHY_LIMIT,
    WITHDRAWN,
    WITHDRAWN_SAID,
    RequestError,
    auto_approves,
    checked_fields,
    clamp,
    create_request,
    dms_on_decision,
    everyone_may_file,
    get_request,
    list_requests,
    page_of,
    requests_are_on,
    set_message,
    set_status,
    summary_line,
)
from ...settings_store import DB_UNAVAILABLE, GUILD_ONLY, require_staff

log = logging.getLogger(__name__)

DUE_PLACEHOLDER = "2026-09-15"
DUE_INPUT_LIMIT = 10
SET_SAID = "Request **#{request_id}** is now **{status}**."
NOT_AN_ID = (
    "**{given}** is not a request number, so nothing was done. `/request list` shows the numbers."
)
LIST_HEADING = {
    "mine": "**Your requests**",
    "pending": "**Waiting on a decision**",
    "all": "**Every request**",
}
PAGE_FOOT = "Page {page} of {pages} — `/request list page:{next}` for the next one."
SCOPES = ("mine", "pending", "all")


def guard_allows(bot: Any, channel: Any) -> bool:
    """The one place this cog asks the guard; a modal reply bypasses the patched send."""
    guard = getattr(bot, "guard", None)
    return guard is None or guard.allows_channel(channel)


def guard_refusal(bot: Any) -> str:
    guard = getattr(bot, "guard", None)
    return guard.refusal_message() if guard is not None else ""


async def answer(interaction: discord.Interaction, text: str) -> None:
    if interaction.response.is_done():
        await interaction.followup.send(
            text, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
        )
        return
    await interaction.response.send_message(
        text, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
    )


async def dm(user: Any, text: str) -> bool:
    """Whether the person actually got told."""
    send = getattr(user, "send", None)
    if send is None:
        return False
    try:
        await send(text, allowed_mentions=discord.AllowedMentions.none())
    except Exception as exc:
        log.info("requests: could not DM %s: %s", getattr(user, "id", "?"), exc)
        return False
    return True


async def tell_requester(bot: Any, guild: Any, row: Any, status: str) -> None:
    """A DM the requester is owed; a failure is a logged fact, never a silent one."""
    if status not in DM_STATUSES or not dms_on_decision(bot.store, guild.id):
        return
    text = DM_TEXT[status].format(
        request_id=row["id"],
        guild=getattr(guild, "name", "the server"),
        what=clamp(row["what"], 300),
        reason=row["decline_reason"] or "no reason was given",
    )
    member = guild.get_member(row["user_id"]) or bot.get_user(row["user_id"])
    if await dm(member, text):
        return
    await log_action(
        bot,
        guild,
        "request.dm_failed",
        target=row["user_id"],
        details={"request_id": row["id"], "status": status},
    )


async def notify(bot: Any, guild: Any, row: Any, who: Any) -> None:
    """One guarded line where staff watch; a channel the guard refuses is skipped, not raised."""
    channel_id = bot.store.get(guild.id, "request_notify_channel_id")
    if not channel_id:
        return
    channel = bot.get_channel(channel_id) or guild.get_channel(channel_id)
    if channel is None:
        log.warning("requests: %s is not a channel Black Bloc can see", channel_id)
        return
    if not guard_allows(bot, channel):
        log.warning("requests: test mode, so #%s was not told about %s", channel_id, row["id"])
        return
    line = NOTIFY_LINE.format(
        request_id=row["id"],
        who=getattr(who, "mention", f"<@{row['user_id']}>"),
        what=clamp(row["what"], 200),
    )
    try:
        message = await channel.send(line, allowed_mentions=discord.AllowedMentions.none())
    except NETWORK_ERRORS as exc:
        log.warning("requests: could not post the notice for %s: %s", row["id"], exc)
        await log_action(
            bot,
            guild,
            "request.notify_failed",
            details={"request_id": row["id"], "reason": f"{type(exc).__name__}: {exc}"},
        )
        return
    await set_message(bot.db, row["id"], message.id)


async def apply_decision(
    bot: Any, guild: Any, request_id: int, status: str, actor: Any, reason: Any = None
) -> tuple[str, Any]:
    """(what to say, the row as it now is or None) — the one path a status moves by."""
    row = await get_request(bot.db, request_id)
    if row is None or row["guild_id"] != guild.id:
        return (NO_SUCH_REQUEST.format(request_id=request_id), None)
    if row["status"] == status:
        return (ALREADY_THAT.format(request_id=request_id, status=status), None)
    kept = clamp(reason, REASON_LIMIT)
    if status == DECLINED and not kept:
        return (DECLINE_NEEDS_A_REASON, None)
    await set_status(
        bot.db,
        request_id,
        status,
        decided_by=getattr(actor, "id", None),
        decline_reason=kept or None,
    )
    fresh = await get_request(bot.db, request_id)
    await log_action(
        bot,
        guild,
        f"request.{status}",
        actor=actor,
        target=row["user_id"],
        reason=kept or None,
        details={"request_id": request_id, "was": row["status"]},
    )
    await tell_requester(bot, guild, fresh, status)
    return (SET_SAID.format(request_id=request_id, status=STATUS_WORDS.get(status, status)), fresh)


class RequestModal(AnswersErrors, discord.ui.Modal, title="Ask for something"):
    what = discord.ui.TextInput(
        label="What are you asking for?",
        style=discord.TextStyle.paragraph,
        max_length=WHAT_LIMIT,
    )
    why = discord.ui.TextInput(
        label="Why is it worth doing?",
        style=discord.TextStyle.paragraph,
        max_length=WHY_LIMIT,
    )
    due = discord.ui.TextInput(
        label="Needed by — YYYY-MM-DD",
        placeholder=DUE_PLACEHOLDER,
        max_length=DUE_INPUT_LIMIT,
        required=False,
    )

    def __init__(self, cog: Requests) -> None:
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await self.cog.submit(
            interaction,
            what=str(self.what),
            why=str(self.why),
            due=str(self.due),
        )


class Requests(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    request = app_commands.Group(name="request", description="Ask the server for something")

    async def _database_ready(self, interaction: discord.Interaction) -> bool:
        if self.bot.db.is_connected:
            return True
        log.warning("requests: refused a command — the database is not connected")
        await answer(interaction, DB_UNAVAILABLE)
        return False

    async def _ready(self, interaction: discord.Interaction) -> bool:
        if interaction.guild is None:
            await answer(interaction, GUILD_ONLY)
            return False
        return await self._database_ready(interaction)

    @request.command(name="create", description="Ask for something; staff decide on the site")
    async def request_create(self, interaction: discord.Interaction) -> None:
        if not await self._ready(interaction):
            return
        guild = interaction.guild
        if not requests_are_on(self.bot.store, guild.id):
            await answer(interaction, REQUESTS_OFF)
            return
        if not everyone_may_file(self.bot.store, guild.id) and not self.bot.store.is_staff(
            interaction.user
        ):
            await answer(interaction, STAFF_ONLY_FILES)
            return
        await interaction.response.send_modal(RequestModal(self))

    async def submit(
        self, interaction: discord.Interaction, *, what: str, why: str, due: str
    ) -> None:
        """What the modal does once it is filled in: one row, one notice, one ephemeral line."""
        if not guard_allows(self.bot, interaction.channel_id):
            await answer(interaction, guard_refusal(self.bot))
            return
        if not await self._ready(interaction):
            return
        guild = interaction.guild
        if not requests_are_on(self.bot.store, guild.id):
            await answer(interaction, REQUESTS_OFF)
            return
        staff = self.bot.store.is_staff(interaction.user)
        if not everyone_may_file(self.bot.store, guild.id) and not staff:
            await answer(interaction, STAFF_ONLY_FILES)
            return
        try:
            kept_what, kept_why, due_on = checked_fields(what, why, due)
        except RequestError as exc:
            await answer(interaction, str(exc))
            return
        approved = staff and auto_approves(self.bot.store, guild.id)
        await interaction.response.defer(ephemeral=True)
        request_id = await create_request(
            self.bot.db,
            guild.id,
            interaction.user.id,
            what=kept_what,
            why=kept_why,
            due_on=due_on,
            status=APPROVED if approved else PENDING,
            decided_by=interaction.user.id if approved else None,
        )
        await log_action(
            self.bot,
            guild,
            "request.filed",
            actor=interaction.user,
            target=interaction.user,
            details={"request_id": request_id, "what": clamp(kept_what, 120), "due_on": due_on},
        )
        if approved:
            await log_action(
                self.bot,
                guild,
                "request.auto_approved",
                actor=interaction.user,
                target=interaction.user,
                details={"request_id": request_id},
            )
        row = await get_request(self.bot.db, request_id)
        await notify(self.bot, guild, row, interaction.user)
        said = FILED_APPROVED if approved else FILED
        await answer(interaction, said.format(request_id=request_id))

    @request.command(name="list", description="Show the requests that have been filed")
    @app_commands.describe(
        scope="yours, the ones waiting on a decision, or every one of them",
        page="which page of ten to show",
    )
    @app_commands.choices(
        scope=[app_commands.Choice(name=name, value=name) for name in SCOPES]
    )
    async def request_list(
        self,
        interaction: discord.Interaction,
        scope: app_commands.Choice[str] | None = None,
        page: int = 1,
    ) -> None:
        if not await self._ready(interaction):
            return
        guild = interaction.guild
        wanted = scope.value if scope is not None else "mine"
        rows = await list_requests(
            self.bot.db,
            guild.id,
            statuses=(PENDING,) if wanted == "pending" else None,
            user_id=interaction.user.id if wanted == "mine" else None,
        )
        if not rows:
            empty = {
                "mine": NOTHING_OF_YOURS,
                "pending": NOTHING_PENDING,
                "all": NOTHING_FILED_YET,
            }[wanted]
            await answer(interaction, empty)
            return
        shown, at, pages = page_of(rows, page, LIST_PAGE)
        lines = [LIST_HEADING[wanted], *[summary_line(row) for row in shown]]
        if pages > 1:
            lines.append(PAGE_FOOT.format(page=at, pages=pages, next=min(at + 1, pages)))
        await answer(interaction, "\n".join(lines))

    @request.command(name="withdraw", description="Take back a request you filed")
    @app_commands.describe(request_id="The number `/request list` shows")
    async def request_withdraw(self, interaction: discord.Interaction, request_id: str) -> None:
        if not await self._ready(interaction):
            return
        digits = str(request_id).strip().lstrip("#")
        if not digits.isdigit():
            await answer(interaction, NOT_AN_ID.format(given=clamp(request_id, 40)))
            return
        guild = interaction.guild
        row = await get_request(self.bot.db, int(digits))
        if row is None or row["guild_id"] != guild.id:
            await answer(interaction, NO_SUCH_REQUEST.format(request_id=digits))
            return
        if row["user_id"] != interaction.user.id:
            await answer(interaction, NOT_YOURS.format(request_id=row["id"]))
            return
        if row["status"] != PENDING:
            await answer(
                interaction,
                NOT_PENDING.format(
                    request_id=row["id"], status=STATUS_WORDS.get(row["status"], row["status"])
                ),
            )
            return
        await interaction.response.defer(ephemeral=True)
        await set_status(self.bot.db, row["id"], WITHDRAWN)
        await log_action(
            self.bot,
            guild,
            "request.withdrawn",
            actor=interaction.user,
            target=interaction.user,
            details={"request_id": row["id"]},
        )
        await answer(interaction, WITHDRAWN_SAID.format(request_id=row["id"]))

    @request.command(name="set", description="Move a request along; staff only")
    @app_commands.describe(
        request_id="The number `/request list` shows",
        status="Where the request has got to",
        reason="Required when you decline one; the person who asked is sent it",
    )
    @app_commands.choices(
        status=[app_commands.Choice(name=name, value=name) for name in STAFF_STATUSES]
    )
    async def request_set(
        self,
        interaction: discord.Interaction,
        request_id: str,
        status: app_commands.Choice[str],
        reason: str | None = None,
    ) -> None:
        if not await require_staff(interaction):
            return
        if not await self._database_ready(interaction):
            return
        digits = str(request_id).strip().lstrip("#")
        if not digits.isdigit():
            await answer(interaction, NOT_AN_ID.format(given=clamp(request_id, 40)))
            return
        await interaction.response.defer(ephemeral=True)
        said, _ = await apply_decision(
            self.bot,
            interaction.guild,
            int(digits),
            status.value,
            interaction.user,
            reason=reason,
        )
        await answer(interaction, said)

    @request.command(name="logs", description="The last few request log lines")
    @app_commands.describe(
        count="How many lines, 1 to 50 (10 by default)",
        important_only="True to leave out the dry runs and the housekeeping",
    )
    async def request_logs(
        self,
        interaction: discord.Interaction,
        count: app_commands.Range[int, LOGS_MIN, LOGS_MAX] = LOGS_DEFAULT,
        important_only: bool = False,
    ) -> None:
        await send_logs(interaction, "request", count=count, important_only=important_only)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Requests(bot))


__all__ = [
    "Requests",
    "RequestModal",
    "apply_decision",
    "guard_allows",
    "notify",
    "tell_requester",
]
