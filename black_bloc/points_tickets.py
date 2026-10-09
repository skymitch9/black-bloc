"""A run submitted on /pb as a modmail ticket: opened silently, decided on its card, closed."""

from __future__ import annotations

import logging
from typing import Any

import discord

from . import points_moves as moves
from . import points_store as store_
from .actionlog import log_action
from .cogs.moderation import modmail as mm
from .command_errors import AnswersErrors, SafeDynamicItem
from .logkinds import VIA_DISCORD, kind_via
from .modmail import CARD_APPROVE, OPEN, SOURCE_POINTS, closing_dm, is_run
from .panels import Outcome, answer, db_ready, db_up, opened, refusal, still_staff
from .pb_feed import plain
from .points import clock
from .points.model import APPROVED, PENDING, REJECTED
from .points_announce import announce

log = logging.getLogger(__name__)

APPROVE = "approve"
REJECT = "reject"
REMOVE = "remove"
EDIT = "edit"
RECOMPUTE = "recompute"
BLANK = "—"
REASON_LIMIT = moves.REASON_LIMIT
REMOVE_TEMPLATE = r"points:remove:(?P<run_id>[0-9]+)"
REMOVE_LABEL = "Take it off the board…"
REJECT_TITLE = "Reject this run"
REMOVE_TITLE = "Take this run off the board"
REASON_LABEL = "Why — the member is told this"
RUN_LINE = "**run** — {game}{category} · {time} · {state} · [proof]({proof})"
PENDING_LINE = "#{ticket} · {name} — **{game}** ({time}) · <#{place}>"
REJECTED_WITH = "{said} — {reason}"
NOT_TOLD = " The member was not DM'd: points_mode is **{mode}**."
DM_SHUT = " ⚠️ The DM did not reach them — their DMs are shut or Black Bloc is blocked."
NOT_CLOSED = " ⚠️ The ticket could not be closed; the log says why."
REFUSED_KEYS = {
    "disabled": "points_modmail_off_said",
    "blocked": "points_blocked_said",
    "already_open": "points_ticket_open_said",
    "cannot_open": "points_cannot_open_said",
    "a_bot": "points_cannot_open_said",
}


def said(bot: Any, guild: Any, key: str, **fields: Any) -> str:
    return moves.said(bot.store, guild.id, key, **fields)


def typed(given: dict[str, Any], field: str) -> str:
    return " ".join(str(given.get(field) or "").split())


def ticket_words(given: dict[str, Any]) -> dict[str, str]:
    """The fields as the member typed them; a blank one reads as a dash."""
    return {
        "game": plain(typed(given, "game")),
        "category": plain(typed(given, "category")) or BLANK,
        "time": plain(typed(given, "time")),
        "proof": str(given.get("proof_url") or "").strip(),
        "note": plain(typed(given, "note")) or BLANK,
    }


async def busy_words(bot: Any, guild: Any, member: Any) -> Outcome | None:
    existing = await mm.open_ticket_for(bot.db, guild.id, member.id)
    if existing is None:
        return None
    if is_run(existing):
        row = await store_.run_by_ticket(bot.db, guild.id, existing["id"])
        if row is not None and row["state"] == PENDING:
            words = said(bot, guild, "points_run_waiting_said", game=plain(row["game"]))
            return refusal(words, "run_waiting", 409)
    return refusal(said(bot, guild, "points_ticket_open_said"), "already_open", 409)


async def submit(bot: Any, guild: Any, member: Any, given: dict[str, Any]) -> Outcome:
    """Checked first, then the ticket in the member's name, then the run that points at it."""
    try:
        moves.require_on(bot, guild)
        moves.run_values(bot, guild, given, creating=True)
    except moves.Stop as stop:
        return stop.outcome
    busy = await busy_words(bot, guild, member)
    if busy is not None:
        return busy
    words = ticket_words(given)
    opened_ticket = await mm.open_a_ticket(
        bot,
        guild,
        member,
        source=SOURCE_POINTS,
        subject=said(bot, guild, "points_ticket_subject", **words),
        text=said(bot, guild, "points_ticket_body", **words),
    )
    if not opened_ticket.ok:
        key = REFUSED_KEYS.get(opened_ticket.code, "points_cannot_open_said")
        return refusal(said(bot, guild, key), opened_ticket.code, opened_ticket.status or 409)
    ticket_id = int(opened_ticket.value)
    outcome = await moves.submit(bot, guild, member, given, ticket_id=ticket_id)
    ticket = await mm.get_ticket(bot.db, ticket_id)
    if not outcome.ok:
        if ticket is not None:
            await mm.close_ticket(bot, guild, ticket, reason=outcome.code, silent=True)
        return outcome
    if ticket is not None and words["proof"]:
        await mm.speak(bot, guild, ticket, content=words["proof"])
        await mm.bump_card(bot, guild, ticket)
    return outcome


async def close_held(bot: Any, guild: Any, ticket: Any) -> str | None:
    """A run's ticket stays open while the run waits: Approve or Reject is what closes it."""
    if ticket is None or not is_run(ticket):
        return None
    row = await store_.run_by_ticket(bot.db, guild.id, int(ticket["id"]))
    if row is None or row["state"] != PENDING:
        return None
    return said(bot, guild, "points_close_refused_said")


async def card_line(bot: Any, guild: Any, ticket: Any) -> str | None:
    row = await store_.run_by_ticket(bot.db, guild.id, int(ticket["id"]))
    if row is None:
        return None
    return RUN_LINE.format(
        game=plain(row["game"]),
        category=f" ({plain(row['category'])})" if row["category"] else "",
        time=clock.shown(row["seconds"]),
        state=moves.state_words(bot, guild, row["state"]),
        proof=row["proof_url"],
    )


async def pending(bot: Any, guild: Any) -> list[tuple[Any, Any]]:
    """The open run tickets whose run still waits — the queue IS the inbox, filtered."""
    found = []
    for ticket in await mm.open_tickets(bot.db, guild.id):
        if not is_run(ticket):
            continue
        row = await store_.run_by_ticket(bot.db, guild.id, int(ticket["id"]))
        if row is not None and row["state"] == PENDING:
            found.append((ticket, row))
    return found


def pending_line(guild: Any, ticket: Any, row: Any) -> str:
    return PENDING_LINE.format(
        ticket=ticket["id"],
        name=moves.name_of(guild, row["user_id"]),
        game=plain(row["game"]),
        time=clock.shown(row["seconds"]),
        place=mm.ticket_place_id(ticket),
    )


async def noted(bot: Any, guild: Any, kind: str, actor: Any, user_id: int, **details: Any) -> None:
    try:
        await log_action(bot, guild, kind, actor=actor, target=user_id, details=details)
    except Exception:
        log.exception("points: could not write the %s row", kind)


async def tell(
    bot: Any, guild: Any, actor: Any, user_id: int, text: str, move: str, via: str
) -> str:
    """The member's DM; never sent while points_mode is not on, and never in the move's way."""
    mode = moves.mode_of(bot.store, guild.id)
    details = {"via": via, "move": move, "text": text}
    if mode != moves.ON:
        await noted(bot, guild, kind_via("points.would_dm", via), actor, user_id, **details)
        return NOT_TOLD.format(mode=mode)
    finder = getattr(bot, "get_user", None)
    user = guild.get_member(int(user_id)) or (finder(int(user_id)) if finder else None)
    why_not = await mm.deliver_dm(user, text)
    if why_not is None:
        return ""
    await noted(
        bot, guild, kind_via("points.dm_failed", via), actor, user_id, **details, reason=why_not
    )
    return DM_SHUT


def approved_dm(bot: Any, guild: Any, row: Any) -> str:
    approved = said(
        bot,
        guild,
        "points_dm_approved",
        game=plain(row["game"]),
        time=clock.shown(row["seconds"]),
        xp=row["xp"],
        points=row["speedpoints"],
    )
    return f"{closing_dm(guild.name)}\n\n{approved}"


async def close_with(bot: Any, guild: Any, actor: Any, row: Any, words: str, via: str) -> str:
    """The ticket a run came through closes with the decision; an approval leaves Remove behind."""
    ticket = await mm.get_ticket(bot.db, int(row["ticket_id"])) if row["ticket_id"] else None
    if ticket is None or ticket["status"] != OPEN:
        return ""
    view = remove_view(row["id"]) if row["state"] == APPROVED else None
    await mm.speak(bot, guild, ticket, content=words, view=view)
    closed, _ = await mm.close_ticket(
        bot, guild, ticket, by=actor, reason=words, silent=True, via=via
    )
    return "" if closed else NOT_CLOSED


async def settle(
    bot: Any, guild: Any, actor: Any, outcome: Outcome, move: str, *, via: str = VIA_DISCORD
) -> str:
    """What every door does after a run move: close its ticket, tell the member, post the top."""
    if not outcome.ok:
        return outcome.message
    result = outcome.value
    words = outcome.message
    row = await store_.run(bot.db, guild.id, int(result.id)) if result.id else None
    extra = ""
    text = result.dm
    if row is not None and move in (APPROVE, REJECT):
        decided = (
            REJECTED_WITH.format(said=words, reason=row["reason"])
            if row["state"] == REJECTED and row["reason"]
            else words
        )
        had_ticket = bool(row["ticket_id"])
        extra += await close_with(bot, guild, actor, row, decided, via)
        if row["state"] == APPROVED:
            text = approved_dm(bot, guild, row) if had_ticket else None
    user_id = result.dm_to if result.dm_to is not None else (row["user_id"] if row else None)
    if text and user_id is not None:
        extra += await tell(bot, guild, actor, int(user_id), text, move, via)
    await announce(bot, guild, outcome, via=via)
    return words + extra


async def card_open(interaction: discord.Interaction, ticket_id: int, previous: Any) -> Any:
    """The card in the room answers ephemerally; the panel's copy edits itself."""
    if previous is not None:
        if not await opened(interaction):
            return None
    else:
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)
        if not await db_ready(interaction):
            return None
    return await mm.card_ticket(interaction, ticket_id)


async def run_decision(
    interaction: discord.Interaction,
    ticket_id: int,
    move: str,
    *,
    reason: str = "",
    previous: Any = None,
) -> None:
    ticket = await card_open(interaction, ticket_id, previous)
    if ticket is None:
        return
    bot, guild, actor = interaction.client, interaction.guild, interaction.user
    if move == APPROVE:
        outcome = await moves.approve(bot, guild, actor, ticket_id=int(ticket_id))
    else:
        outcome = await moves.reject(bot, guild, actor, reason=reason, ticket_id=int(ticket_id))
    words = await settle(bot, guild, actor, outcome, move)
    await mm.card_moved(interaction, int(ticket_id), previous, words)


def not_verifier(bot: Any, guild: Any) -> str:
    return said(bot, guild, "points_not_verifier_said", role=moves.role_words(bot, guild))


async def pressed(
    interaction: discord.Interaction, action: str, ticket_id: int, previous: Any = None
) -> None:
    """Approve and Reject are for staff and the verifier role; the move asks again."""
    bot, guild = interaction.client, interaction.guild
    if not moves.may_verify(bot.store, guild, interaction.user):
        await answer(interaction, not_verifier(bot, guild))
        return
    if not await db_up(interaction):
        return
    if action == CARD_APPROVE:
        await run_decision(interaction, ticket_id, APPROVE, previous=previous)
        return
    if await mm.card_ticket(interaction, ticket_id) is None:
        return
    await interaction.response.send_modal(RejectModal(ticket_id, previous))


def reason_input() -> discord.ui.TextInput:
    return discord.ui.TextInput(
        style=discord.TextStyle.paragraph, max_length=REASON_LIMIT, required=False
    )


class RejectModal(AnswersErrors, discord.ui.Modal):
    def __init__(self, ticket_id: int, previous: Any = None) -> None:
        super().__init__(title=REJECT_TITLE)
        self.ticket_id = int(ticket_id)
        self.previous = previous
        self.reason = reason_input()
        self.add_item(discord.ui.Label(text=REASON_LABEL, component=self.reason))

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await run_decision(
            interaction,
            self.ticket_id,
            REJECT,
            reason=str(self.reason),
            previous=self.previous,
        )


class RemoveModal(AnswersErrors, discord.ui.Modal):
    def __init__(self, run_id: int) -> None:
        super().__init__(title=REMOVE_TITLE)
        self.run_id = int(run_id)
        self.reason = reason_input()
        self.add_item(discord.ui.Label(text=REASON_LABEL, component=self.reason))

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await run_remove(interaction, self.run_id, str(self.reason))


async def run_remove(interaction: discord.Interaction, run_id: int, reason: str) -> None:
    if not await opened(interaction):
        return
    bot, guild, actor = interaction.client, interaction.guild, interaction.user
    outcome = await moves.remove(bot, guild, actor, int(run_id), reason)
    await answer(interaction, await settle(bot, guild, actor, outcome, REMOVE))


def remove_custom_id(run_id: Any) -> str:
    return f"points:remove:{int(run_id)}"


class RemoveButton(
    SafeDynamicItem, discord.ui.DynamicItem[discord.ui.Button], template=REMOVE_TEMPLATE
):
    """Left under an approved run's decision line, so staff can take it back from the ticket."""

    def __init__(self, run_id: Any) -> None:
        self.run_id = int(run_id)
        super().__init__(
            discord.ui.Button(
                label=REMOVE_LABEL,
                style=discord.ButtonStyle.danger,
                custom_id=remove_custom_id(run_id),
            )
        )

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: Any, match: Any):
        return cls(int(match["run_id"]))

    async def on_click(self, interaction: discord.Interaction) -> None:
        if not await still_staff(interaction):
            return
        if not await db_up(interaction):
            return
        await interaction.response.send_modal(RemoveModal(self.run_id))


def remove_view(run_id: int) -> discord.ui.View:
    view = discord.ui.View(timeout=None)
    view.add_item(RemoveButton(run_id))
    return view


__all__ = [
    "APPROVE",
    "EDIT",
    "RECOMPUTE",
    "REJECT",
    "REMOVE",
    "RejectModal",
    "RemoveButton",
    "RemoveModal",
    "card_line",
    "close_held",
    "pending",
    "pending_line",
    "pressed",
    "settle",
    "submit",
    "tell",
]
