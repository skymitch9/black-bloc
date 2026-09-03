from __future__ import annotations

import logging
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands

from ...actionlog import LOGS_DEFAULT, LOGS_MAX, LOGS_MIN, log_action, send_logs
from ...command_errors import NETWORK_ERRORS, AnswersErrors
from ...logkinds import VIA_DISCORD, kind_via
from ...requests import (
    DM_STATUSES,
    DM_TEXT,
    FILED,
    HOLD,
    LIST_PAGE,
    NO_SUCH_REQUEST,
    NOT_ON_HOLD,
    NOT_YOURS,
    NOTHING_FILED_YET,
    NOTHING_OF_YOURS,
    NOTHING_OPEN,
    NOTIFY_CHANNEL_KEY,
    NOTIFY_FAILED_KIND,
    NOTIFY_LINE,
    NOTIFY_MOVE,
    NOTIFY_SKIPPED_KIND,
    OPEN,
    OPEN_STATUSES,
    REASON_LIMIT,
    REQUESTS_OFF,
    STAFF_ONLY_FILES,
    STAFF_STATUSES,
    STATUS_WORDS,
    TOO_LATE_TO_WITHDRAW,
    WHAT_LIMIT,
    WHY_LIMIT,
    WITHDRAWABLE,
    WITHDRAWN,
    WITHDRAWN_SAID,
    RequestError,
    checked_fields,
    checked_move,
    clamp,
    create_request,
    dms_on_decision,
    everyone_may_file,
    get_request,
    held_words,
    list_requests,
    page_of,
    requests_are_on,
    resume_target,
    set_message,
    set_status,
    status_channel_id,
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
    "open": "**Still open**",
    "all": "**Every request**",
}
PAGE_FOOT = "Page {page} of {pages} — `/request list page:{next}` for the next one."
SCOPES = ("mine", "open", "all")
RESUMED_SAID = "Request **#{request_id}** is off hold and back to **{status}**."


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
    """A DM the requester is owed on every staff move; a failure is logged, never silent."""
    if status not in DM_STATUSES or not dms_on_decision(bot.store, guild.id):
        return
    text = DM_TEXT[status].format(
        request_id=row["id"],
        guild=getattr(guild, "name", "the server"),
        what=clamp(row["what"], 300),
        reason=row["decline_reason"] or "no reason was given",
        held_from=held_words(row) or "open",
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


async def post_line(bot: Any, guild: Any, channel_id: Any, row: Any, line: str, move: str) -> Any:
    """One guarded line where staff watch; a channel the guard refuses is skipped, not raised."""
    if not channel_id:
        return None
    channel = bot.get_channel(channel_id) or guild.get_channel(channel_id)
    if channel is None:
        log.warning("requests: %s is not a channel Black Bloc can see", channel_id)
        return None
    if not guard_allows(bot, channel):
        log.warning("requests: test mode, so #%s was not told about %s", channel_id, row["id"])
        await log_action(
            bot,
            guild,
            NOTIFY_SKIPPED_KIND,
            details={"request_id": row["id"], "move": move, "channel_id": int(channel_id)},
        )
        return None
    try:
        return await channel.send(line, allowed_mentions=discord.AllowedMentions.none())
    except NETWORK_ERRORS as exc:
        log.warning("requests: could not post the %s line for %s: %s", move, row["id"], exc)
        await log_action(
            bot,
            guild,
            NOTIFY_FAILED_KIND,
            details={
                "request_id": row["id"],
                "move": move,
                "reason": f"{type(exc).__name__}: {exc}",
            },
        )
        return None


async def notify(bot: Any, guild: Any, row: Any, who: Any) -> None:
    line = NOTIFY_LINE.format(
        request_id=row["id"],
        who=getattr(who, "mention", f"<@{row['user_id']}>"),
        what=clamp(row["what"], 200),
    )
    message = await post_line(
        bot, guild, bot.store.get(guild.id, NOTIFY_CHANNEL_KEY), row, line, "filed"
    )
    if message is not None:
        await set_message(bot.db, row["id"], message.id)


async def notify_move(bot: Any, guild: Any, row: Any, status: str) -> None:
    """The channel hears every staff move, not only the filing (owner, 2026-09-02)."""
    template = NOTIFY_MOVE.get(status)
    if template is None:
        return
    line = template.format(
        request_id=row["id"],
        who=f"<@{row['user_id']}>",
        what=clamp(row["what"], 200),
        reason=clamp(row["decline_reason"], 200) or "no reason was given",
    )
    await post_line(bot, guild, status_channel_id(bot.store, guild.id), row, line, status)


async def apply_decision(
    bot: Any,
    guild: Any,
    request_id: int,
    status: str,
    actor: Any,
    reason: Any = None,
    *,
    via: str = VIA_DISCORD,
) -> tuple[str, Any]:
    """(what to say, the row as it now is or None) — the one path a status moves by."""
    row = await get_request(bot.db, request_id)
    if row is None or row["guild_id"] != guild.id:
        return (NO_SUCH_REQUEST.format(request_id=request_id), None)
    kept = clamp(reason, REASON_LIMIT)
    try:
        wanted = checked_move(request_id, row["status"], status, kept)
    except RequestError as exc:
        return (str(exc), None)
    await set_status(
        bot.db,
        request_id,
        wanted,
        decided_by=getattr(actor, "id", None),
        decline_reason=kept or None,
        was=row["status"],
    )
    fresh = await get_request(bot.db, request_id)
    await log_action(
        bot,
        guild,
        kind_via(f"request.{wanted}", via),
        actor=actor,
        target=row["user_id"],
        reason=kept or None,
        details={"request_id": request_id, "was": row["status"], "via": via},
    )
    await tell_requester(bot, guild, fresh, wanted)
    await notify_move(bot, guild, fresh, wanted)
    return (SET_SAID.format(request_id=request_id, status=STATUS_WORDS.get(wanted, wanted)), fresh)


async def resume_request(
    bot: Any, guild: Any, request_id: int, actor: Any, *, via: str = VIA_DISCORD
) -> tuple[str, Any]:
    """Off hold and back where it was held from — the Resume button and `/request resume`."""
    row = await get_request(bot.db, request_id)
    if row is None or row["guild_id"] != guild.id:
        return (NO_SUCH_REQUEST.format(request_id=request_id), None)
    if row["status"] != HOLD:
        return (
            NOT_ON_HOLD.format(
                request_id=request_id,
                status=STATUS_WORDS.get(row["status"], row["status"]),
            ),
            None,
        )
    wanted = resume_target(row)
    await set_status(bot.db, request_id, wanted, decided_by=getattr(actor, "id", None))
    fresh = await get_request(bot.db, request_id)
    await log_action(
        bot,
        guild,
        kind_via("request.resumed", via),
        actor=actor,
        target=row["user_id"],
        details={"request_id": request_id, "was": HOLD, "held_from": wanted, "via": via},
    )
    await tell_requester(bot, guild, fresh, wanted)
    await notify_move(bot, guild, fresh, wanted)
    return (
        RESUMED_SAID.format(request_id=request_id, status=STATUS_WORDS.get(wanted, wanted)),
        fresh,
    )


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
        await interaction.response.defer(ephemeral=True)
        request_id = await create_request(
            self.bot.db,
            guild.id,
            interaction.user.id,
            what=kept_what,
            why=kept_why,
            due_on=due_on,
            status=OPEN,
        )
        await log_action(
            self.bot,
            guild,
            "request.filed",
            actor=interaction.user,
            target=interaction.user,
            details={"request_id": request_id, "what": clamp(kept_what, 120), "due_on": due_on},
        )
        row = await get_request(self.bot.db, request_id)
        await notify(self.bot, guild, row, interaction.user)
        await answer(interaction, FILED.format(request_id=request_id))

    @request.command(name="list", description="Show the requests that have been filed")
    @app_commands.describe(
        scope="yours, the ones still open, or every one of them",
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
            statuses=OPEN_STATUSES if wanted == "open" else None,
            user_id=interaction.user.id if wanted == "mine" else None,
        )
        if not rows:
            empty = {
                "mine": NOTHING_OF_YOURS,
                "open": NOTHING_OPEN,
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
        if row["status"] not in WITHDRAWABLE:
            await answer(
                interaction,
                TOO_LATE_TO_WITHDRAW.format(
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
        reason="Required for hold and declined; the person who asked is sent it",
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

    @request.command(name="hold", description="Park a request with a reason; staff only")
    @app_commands.describe(
        request_id="The number `/request list` shows",
        reason="Why it is waiting; the person who asked is sent this",
    )
    async def request_hold(
        self, interaction: discord.Interaction, request_id: str, reason: str
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
            self.bot, interaction.guild, int(digits), HOLD, interaction.user, reason=reason
        )
        await answer(interaction, said)

    @request.command(name="resume", description="Take a request off hold; staff only")
    @app_commands.describe(request_id="The number `/request list` shows")
    async def request_resume(self, interaction: discord.Interaction, request_id: str) -> None:
        if not await require_staff(interaction):
            return
        if not await self._database_ready(interaction):
            return
        digits = str(request_id).strip().lstrip("#")
        if not digits.isdigit():
            await answer(interaction, NOT_AN_ID.format(given=clamp(request_id, 40)))
            return
        await interaction.response.defer(ephemeral=True)
        said, _ = await resume_request(
            self.bot, interaction.guild, int(digits), interaction.user
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
    "notify_move",
    "post_line",
    "resume_request",
    "tell_requester",
]
