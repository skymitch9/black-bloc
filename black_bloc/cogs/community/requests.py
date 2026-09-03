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
    BUILT_LIMIT,
    DECLINED,
    DM_LOOKS,
    DONE,
    FILED,
    FILED_LOOK,
    HOLD,
    HOW_TO_TEST_LIMIT,
    IN_PROGRESS,
    LIST_PAGE,
    LOOKS,
    NO_SUCH_REQUEST,
    NOT_ON_HOLD,
    NOT_READY_TO_CHECK,
    NOT_YOURS,
    NOTHING_FILED_YET,
    NOTHING_OF_YOURS,
    NOTHING_OPEN,
    NOTIFY_CHANNEL_KEY,
    NOTIFY_FAILED_KIND,
    NOTIFY_SKIPPED_KIND,
    OPEN,
    OPEN_STATUSES,
    REASON_LIMIT,
    REQUESTS_OFF,
    REVIEW,
    REVIEW_BY_SOMEBODY_ELSE,
    SENT_BACK,
    SENT_BACK_LIMIT,
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
    list_requests,
    look_of,
    may_accept,
    move_line,
    page_of,
    posts_a_card,
    request_embed,
    requests_are_on,
    resume_target,
    row_value,
    set_fields,
    set_message,
    set_status,
    site_view,
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
MOVE_LOOKS = tuple(one for one in LOOKS if one != FILED_LOOK)
READY_SAID = "Request **#{request_id}** is ready to check — staff will look at it."
ACCEPTED_SAID = "Request **#{request_id}** is done. The person who asked has been told."
SENT_BACK_SAID = "Request **#{request_id}** is back with whoever is working on it."
MOVE_SAID: dict[str, str] = {
    IN_PROGRESS: SET_SAID,
    REVIEW: READY_SAID,
    SENT_BACK: SENT_BACK_SAID,
    DONE: ACCEPTED_SAID,
    HOLD: SET_SAID,
    DECLINED: SET_SAID,
}
READY_MODAL_TITLE = "Ready to check"
READY_HINT = (
    "What was built, and how somebody tries it. Both show on the card and on the site; the "
    "site is where either can be edited afterwards."
)


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


async def dm(user: Any, **payload: Any) -> bool:
    """Whether the person actually got told."""
    send = getattr(user, "send", None)
    if send is None:
        return False
    try:
        await send(allowed_mentions=discord.AllowedMentions.none(), **payload)
    except Exception as exc:
        log.info("requests: could not DM %s: %s", getattr(user, "id", "?"), exc)
        return False
    return True


def person_told(bot: Any, guild: Any, row: Any, look: str) -> Any:
    """The requester on their own moves; the staffer who marked it ready when it comes back."""
    if look == SENT_BACK:
        return row_value(row, "ready_by")
    return row_value(row, "user_id") if look in DM_LOOKS else None


def card(bot: Any, guild: Any, row: Any, look: str) -> tuple[Any, Any]:
    """The one rendering both the channel and the DM send — embed plus its link button."""
    origin = getattr(getattr(bot, "settings", None), "origin", "")
    return (
        request_embed(row, move=look, origin=origin, guild=guild),
        site_view(origin, row_value(row, "id", "")),
    )


async def tell_person(bot: Any, guild: Any, row: Any, look: str) -> None:
    """The DM somebody is owed on a move; a failure is logged, never silent."""
    wanted = person_told(bot, guild, row, look)
    if wanted is None:
        return
    if look in DM_LOOKS and not dms_on_decision(bot.store, guild.id):
        return
    member = guild.get_member(wanted) or bot.get_user(wanted)
    embed, view = card(bot, guild, row, look)
    if await dm(member, embed=embed, view=view):
        return
    await log_action(
        bot,
        guild,
        "request.dm_failed",
        target=wanted,
        details={"request_id": row["id"], "status": look},
    )


async def post_line(
    bot: Any,
    guild: Any,
    channel_id: Any,
    row: Any,
    line: str,
    move: str,
    *,
    embed: Any = None,
    view: Any = None,
) -> Any:
    """One guarded card where staff watch; a channel the guard refuses is skipped, not raised."""
    if not channel_id:
        return None
    channel = bot.get_channel(channel_id) or guild.get_channel(channel_id)
    if channel is None:
        log.warning("requests: %s is not a channel Black Bloc can see", channel_id)
        return None
    if not guard_allows(bot, channel):
        log.warning("requests: test mode, so #%s never heard %r", channel_id, line)
        await log_action(
            bot,
            guild,
            NOTIFY_SKIPPED_KIND,
            details={"request_id": row["id"], "move": move, "channel_id": int(channel_id)},
        )
        return None
    try:
        return await channel.send(
            embed=embed, view=view, allowed_mentions=discord.AllowedMentions.none()
        )
    except NETWORK_ERRORS as exc:
        log.warning("requests: could not post %r for %s: %s", line, row["id"], exc)
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
    if not posts_a_card(bot.store, guild.id, FILED_LOOK):
        return
    embed, view = card(bot, guild, row, FILED_LOOK)
    message = await post_line(
        bot,
        guild,
        bot.store.get(guild.id, NOTIFY_CHANNEL_KEY),
        row,
        move_line(row, FILED_LOOK),
        FILED_LOOK,
        embed=embed,
        view=view,
    )
    if message is not None:
        await set_message(bot.db, row["id"], message.id)


async def notify_move(bot: Any, guild: Any, row: Any, look: str) -> None:
    """The channel hears every staff move, not only the filing (owner, 2026-09-02)."""
    if look not in MOVE_LOOKS or not posts_a_card(bot.store, guild.id, look):
        return
    embed, view = card(bot, guild, row, look)
    await post_line(
        bot,
        guild,
        status_channel_id(bot.store, guild.id),
        row,
        move_line(row, look),
        look,
        embed=embed,
        view=view,
    )


async def apply_decision(
    bot: Any,
    guild: Any,
    request_id: int,
    status: str,
    actor: Any,
    reason: Any = None,
    *,
    built: Any = None,
    how_to_test: Any = None,
    note: Any = None,
    via: str = VIA_DISCORD,
) -> tuple[str, Any]:
    """(what to say, the row as it now is or None) — the one path a status moves by."""
    row = await get_request(bot.db, request_id)
    if row is None or row["guild_id"] != guild.id:
        return (NO_SUCH_REQUEST.format(request_id=request_id), None)
    kept = clamp(reason, REASON_LIMIT)
    kept_built = clamp(built, BUILT_LIMIT)
    kept_note = clamp(note, SENT_BACK_LIMIT)
    try:
        wanted = checked_move(
            request_id, row["status"], status, kept, built=kept_built, note=kept_note
        )
    except RequestError as exc:
        return (str(exc), None)
    if wanted == DONE and not may_accept(bot.store, guild.id, row, actor):
        return (REVIEW_BY_SOMEBODY_ELSE.format(request_id=request_id), None)
    look = look_of(row["status"], wanted)
    if wanted == REVIEW:
        await set_fields(
            bot.db,
            request_id,
            built=kept_built,
            how_to_test=clamp(how_to_test, HOW_TO_TEST_LIMIT) or None,
        )
    await set_status(
        bot.db,
        request_id,
        wanted,
        decided_by=getattr(actor, "id", None),
        decline_reason=kept or None,
        was=row["status"],
        ready_by=getattr(actor, "id", None),
        sent_back_reason=kept_note or None,
    )
    fresh = await get_request(bot.db, request_id)
    await log_action(
        bot,
        guild,
        kind_via(f"request.{look}", via),
        actor=actor,
        target=row["user_id"],
        reason=kept or kept_note or None,
        details={"request_id": request_id, "was": row["status"], "via": via},
    )
    await tell_person(bot, guild, fresh, look)
    await notify_move(bot, guild, fresh, look)
    return (MOVE_SAID[look].format(
        request_id=request_id, status=STATUS_WORDS.get(wanted, wanted)
    ), fresh)


async def mark_ready(
    bot: Any,
    guild: Any,
    request_id: int,
    actor: Any,
    built: Any,
    how_to_test: Any = None,
    *,
    via: str = VIA_DISCORD,
) -> tuple[str, Any]:
    """`/request ready` and the site's Ready-to-check button — in progress into review."""
    return await apply_decision(
        bot,
        guild,
        request_id,
        REVIEW,
        actor,
        built=built,
        how_to_test=how_to_test,
        via=via,
    )


async def accept(
    bot: Any, guild: Any, request_id: int, actor: Any, *, via: str = VIA_DISCORD
) -> tuple[str, Any]:
    """`/request accept` and the site's Accept button — review into done."""
    return await apply_decision(bot, guild, request_id, DONE, actor, via=via)


async def send_back(
    bot: Any, guild: Any, request_id: int, actor: Any, note: Any, *, via: str = VIA_DISCORD
) -> tuple[str, Any]:
    """`/request sendback` and the site's Send back button — review into progress, with a note."""
    row = await get_request(bot.db, request_id)
    if row is None or row["guild_id"] != guild.id:
        return (NO_SUCH_REQUEST.format(request_id=request_id), None)
    if row["status"] != REVIEW:
        return (
            NOT_READY_TO_CHECK.format(
                request_id=request_id,
                status=STATUS_WORDS.get(row["status"], row["status"]),
                doing="send back",
            ),
            None,
        )
    return await apply_decision(bot, guild, request_id, IN_PROGRESS, actor, note=note, via=via)


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
    await set_status(
        bot.db,
        request_id,
        wanted,
        decided_by=getattr(actor, "id", None),
        ready_by=row_value(row, "ready_by"),
    )
    fresh = await get_request(bot.db, request_id)
    await log_action(
        bot,
        guild,
        kind_via("request.resumed", via),
        actor=actor,
        target=row["user_id"],
        details={"request_id": request_id, "was": HOLD, "held_from": wanted, "via": via},
    )
    await tell_person(bot, guild, fresh, wanted)
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


class ReadyModal(AnswersErrors, discord.ui.Modal, title=READY_MODAL_TITLE):
    built = discord.ui.TextInput(
        label="What was built?",
        style=discord.TextStyle.paragraph,
        max_length=BUILT_LIMIT,
    )
    how_to_test = discord.ui.TextInput(
        label="How does somebody test it?",
        style=discord.TextStyle.paragraph,
        max_length=HOW_TO_TEST_LIMIT,
        required=False,
    )

    def __init__(self, cog: Requests, request_id: int, row: Any = None) -> None:
        super().__init__()
        self.cog = cog
        self.request_id = request_id
        self.built.default = clamp(row_value(row, "built"), BUILT_LIMIT) or None
        self.how_to_test.default = clamp(row_value(row, "how_to_test"), HOW_TO_TEST_LIMIT) or None

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await self.cog.ready_submit(
            interaction,
            self.request_id,
            built=str(self.built),
            how_to_test=str(self.how_to_test),
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

    async def _wanted_id(self, interaction: discord.Interaction, request_id: str) -> int | None:
        """Staff, a database and a number, or the sentence that says which one is missing."""
        if not await require_staff(interaction):
            return None
        if not await self._database_ready(interaction):
            return None
        digits = str(request_id).strip().lstrip("#")
        if not digits.isdigit():
            await answer(interaction, NOT_AN_ID.format(given=clamp(request_id, 40)))
            return None
        return int(digits)

    @request.command(
        name="ready",
        description="Say a request is built and ready to check; staff only",
    )
    @app_commands.describe(request_id="The number `/request list` shows")
    async def request_ready(self, interaction: discord.Interaction, request_id: str) -> None:
        wanted = await self._wanted_id(interaction, request_id)
        if wanted is None:
            return
        row = await get_request(self.bot.db, wanted)
        if row is None or row["guild_id"] != interaction.guild.id:
            await answer(interaction, NO_SUCH_REQUEST.format(request_id=wanted))
            return
        await interaction.response.send_modal(ReadyModal(self, wanted, row))

    async def ready_submit(
        self,
        interaction: discord.Interaction,
        request_id: int,
        *,
        built: str,
        how_to_test: str,
    ) -> None:
        """What the ready modal does once it is filled in — the one shared path, nothing else."""
        await interaction.response.defer(ephemeral=True)
        said, _ = await mark_ready(
            self.bot,
            interaction.guild,
            request_id,
            interaction.user,
            built,
            how_to_test,
        )
        await answer(interaction, said)

    @request.command(name="accept", description="Finish a request you have checked; staff only")
    @app_commands.describe(request_id="The number `/request list` shows")
    async def request_accept(self, interaction: discord.Interaction, request_id: str) -> None:
        wanted = await self._wanted_id(interaction, request_id)
        if wanted is None:
            return
        await interaction.response.defer(ephemeral=True)
        said, _ = await accept(self.bot, interaction.guild, wanted, interaction.user)
        await answer(interaction, said)

    @request.command(
        name="sendback",
        description="Send a request back with what is still to do; staff only",
    )
    @app_commands.describe(
        request_id="The number `/request list` shows",
        note="What is still to do; whoever marked it ready is sent this",
    )
    async def request_sendback(
        self, interaction: discord.Interaction, request_id: str, note: str
    ) -> None:
        wanted = await self._wanted_id(interaction, request_id)
        if wanted is None:
            return
        await interaction.response.defer(ephemeral=True)
        said, _ = await send_back(self.bot, interaction.guild, wanted, interaction.user, note)
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
    "ReadyModal",
    "RequestModal",
    "Requests",
    "accept",
    "apply_decision",
    "card",
    "guard_allows",
    "mark_ready",
    "notify",
    "notify_move",
    "person_told",
    "post_line",
    "resume_request",
    "send_back",
    "tell_person",
]
