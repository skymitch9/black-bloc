"""What a press on a tournament card does, and the forms a press opens; both doors share them."""

from __future__ import annotations

import logging
from typing import Any

import discord

from . import brackets_cards as cards
from . import brackets_people as people_
from . import brackets_sets as sets_
from . import brackets_store as store_
from . import brackets_thread as thread_
from .brackets import access
from .brackets_moves import NOTE_LIMIT, WRONG_STATE, role_words, said
from .command_errors import AnswersErrors
from .panels import Outcome, answer, db_ready, db_up, refusal

log = logging.getLogger(__name__)

TITLE_LIMIT = 45
LABEL_LIMIT = 45
REASON_LIMIT = 300
SCORE_LIMIT = 2
DECIDE_TITLE = "Decide {set}"
RESET_TITLE = "Reset {set}"
FORFEIT_TITLE = "{name} wins {set} by forfeit"
REASON_LABEL = "Reason (sent to the players)"


class CardLanding:
    """A move pressed on a posted card: the answer is a private line, then the cards catch up."""

    async def begin(self, interaction: discord.Interaction) -> None:
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True, thinking=True)

    async def end(
        self, interaction: discord.Interaction, tournament_id: int, outcome: Outcome, move: str
    ) -> None:
        await answer(interaction, outcome.message)
        await thread_.follow(
            interaction.client, interaction.guild, tournament_id, outcome, move=move
        )


ON_CARD = CardLanding()


def no_tournament(bot: Any, guild: Any, tournament_id: int) -> Outcome:
    return refusal(
        said(bot.store, guild.id, "brackets_no_tournament_said", id=tournament_id),
        "no_tournament",
        404,
    )


def not_organiser(bot: Any, guild: Any) -> Outcome:
    return refusal(
        said(bot.store, guild.id, "brackets_not_organiser_said", role=role_words(bot, guild)),
        "not_organiser",
        403,
    )


def not_in_set(bot: Any, guild: Any, key: str) -> Outcome:
    return refusal(
        said(bot.store, guild.id, "brackets_not_in_set_said", set=key), "not_in_set", 403
    )


def not_entered(bot: Any, guild: Any, row: Any) -> Outcome:
    return refusal(
        said(bot.store, guild.id, "brackets_not_entered_said", name=row["name"]), "not_entered", 404
    )


def wrong_state(bot: Any, guild: Any, row: Any) -> Outcome:
    return refusal(
        said(
            bot.store,
            guild.id,
            WRONG_STATE,
            name=row["name"],
            state=cards.state_words(bot.store, guild.id, row["state"]),
        ),
        "wrong_state",
        409,
    )


async def member_move(bot: Any, guild: Any, user: Any, tournament_id: int, action: str) -> Outcome:
    """Sign up, leave before the start, or check in — the member's own entrant, found by id."""
    if action == cards.JOIN:
        return await people_.join(bot, guild, user, tournament_id)
    row = await store_.tournament(bot.db, guild.id, int(tournament_id))
    if row is None:
        return no_tournament(bot, guild, tournament_id)
    if action == cards.LEAVE and row["state"] not in store_.BEFORE_START:
        return wrong_state(bot, guild, row)
    mine = await store_.entrant_of(bot.db, row["id"], int(user.id))
    if mine is None or (mine["dropped"] and action == cards.CHECK_IN):
        return not_entered(bot, guild, row)
    if action == cards.LEAVE:
        return await people_.drop(bot, guild, user, row["id"], mine["id"])
    return await people_.set_check_in(bot, guild, user, row["id"], mine["id"], True)


async def starter_pressed(
    interaction: discord.Interaction, tournament_id: int, action: str
) -> None:
    if not await db_up(interaction):
        return
    await ON_CARD.begin(interaction)
    outcome = await member_move(
        interaction.client, interaction.guild, interaction.user, tournament_id, action
    )
    await ON_CARD.end(interaction, tournament_id, outcome, action)


class Seat:
    """One set as a press sees it: the tournament, the set, its people and who is pressing."""

    def __init__(self, row: Any, match: Any, people: dict[int, Any], user: Any) -> None:
        self.row = row
        self.match = match
        self.people = people
        self.side = next(
            (
                side
                for side in ("a", "b")
                if match.slot(side) is not None
                and people.get(match.slot(side)) is not None
                and people[match.slot(side)]["user_id"] == getattr(user, "id", None)
            ),
            None,
        )

    def name(self, side: str) -> str:
        return cards.name_of(self.people, self.match.slot(side))

    def user_ids(self) -> list[int]:
        return cards.player_ids(self.match, self.people)


async def seat_of(bot: Any, guild: Any, user: Any, tournament_id: int, key: str) -> Seat | Outcome:
    row = await store_.tournament(bot.db, guild.id, int(tournament_id))
    if row is None:
        return no_tournament(bot, guild, tournament_id)
    current = await store_.bracket(bot.db, row)
    match = current.matches.get(str(key)) if current is not None else None
    if match is None:
        return refusal(
            said(bot.store, guild.id, "brackets_no_set_said", set=str(key)[:20], name=row["name"]),
            "no_set",
            404,
        )
    people = {one["id"]: one for one in await store_.entrants(bot.db, row["id"])}
    return Seat(row, match, people, user)


def may_run(interaction: discord.Interaction) -> bool:
    return access.may_run(interaction.client.store, interaction.guild, interaction.user)


async def set_pressed(
    interaction: discord.Interaction, tournament_id: int, key: str, action: str
) -> None:
    await set_move(interaction, tournament_id, key, action, ON_CARD)


async def set_move(
    interaction: discord.Interaction, tournament_id: int, key: str, action: str, land: Any
) -> None:
    """Who may press is asked on every press; a form opens only for someone it would serve."""
    bot, guild, user = interaction.client, interaction.guild, interaction.user
    if not await db_up(interaction):
        return
    if action in (cards.CONFIRM, cards.CALL):
        await land.begin(interaction)
        if action == cards.CONFIRM:
            outcome = await sets_.confirm_report(bot, guild, user, tournament_id, key)
        else:
            outcome = await sets_.call(bot, guild, user, tournament_id, key)
        await land.end(interaction, tournament_id, outcome, action)
        return
    seat = await seat_of(bot, guild, user, tournament_id, key)
    if isinstance(seat, Outcome):
        await answer(interaction, seat.message)
        return
    organiser = may_run(interaction)
    if action == cards.REPORT and seat.side is None and not organiser:
        await answer(interaction, not_in_set(bot, guild, seat.match.key).message)
        return
    if action == cards.DISPUTE and seat.side is None:
        await answer(interaction, not_in_set(bot, guild, seat.match.key).message)
        return
    if action in (cards.DECIDE, cards.RESET) and not organiser:
        await answer(interaction, not_organiser(bot, guild).message)
        return
    form = {
        cards.REPORT: ReportModal,
        cards.DISPUTE: DisputeModal,
        cards.DECIDE: DecideModal,
        cards.RESET: ResetModal,
    }[action]
    await interaction.response.send_modal(form(bot, guild, seat, land))


def score_of(text: Any) -> int | None:
    found = str(text or "").strip()
    return int(found) if found.isdigit() else None


def clipped(text: str, limit: int) -> str:
    return text[:limit] or "—"


async def told_players(
    bot: Any, guild: Any, seat: Seat, key: str, reason: str, **fields: Any
) -> None:
    row = await store_.tournament(bot.db, guild.id, seat.row["id"]) or seat.row
    for user_id in seat.user_ids():
        await thread_.tell(bot, guild, row, user_id, key, reason, set=seat.match.key, **fields)


class SetForm(AnswersErrors, discord.ui.Modal):
    """A form opened from a set: it holds the set it was opened on and where the answer lands."""

    def __init__(self, title: str, bot: Any, guild: Any, seat: Seat, land: Any) -> None:
        super().__init__(title=clipped(title, TITLE_LIMIT))
        self.seat = seat
        self.land = land
        self.previous = getattr(land, "previous", None)

    async def landed(self, interaction: discord.Interaction, outcome: Outcome, move: str) -> None:
        await self.land.end(interaction, self.seat.row["id"], outcome, move)

    async def started(self, interaction: discord.Interaction) -> bool:
        await self.land.begin(interaction)
        return await db_ready(interaction)


class ReportModal(SetForm):
    def __init__(self, bot: Any, guild: Any, seat: Seat, land: Any) -> None:
        store, gid = bot.store, guild.id
        super().__init__(
            said(
                store, gid, "brackets_report_title", set=seat.match.key, best_of=seat.match.best_of
            ),
            bot,
            guild,
            seat,
            land,
        )
        self.score_a = discord.ui.TextInput(
            label=clipped(
                said(store, gid, "brackets_score_label", name=seat.name("a")), LABEL_LIMIT
            ),
            max_length=SCORE_LIMIT,
        )
        self.score_b = discord.ui.TextInput(
            label=clipped(
                said(store, gid, "brackets_score_label", name=seat.name("b")), LABEL_LIMIT
            ),
            max_length=SCORE_LIMIT,
        )
        self.add_item(self.score_a)
        self.add_item(self.score_b)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not await self.started(interaction):
            return
        bot, guild = interaction.client, interaction.guild
        a, b = score_of(self.score_a.value), score_of(self.score_b.value)
        if a is None or b is None:
            outcome = refusal(
                said(bot.store, guild.id, "brackets_score_not_number_said"), "bad_score", 400
            )
        else:
            outcome = await sets_.report(
                bot, guild, interaction.user, self.seat.row["id"], self.seat.match.key, a, b
            )
            if outcome.ok and self.seat.side is None:
                await told_players(
                    bot, guild, self.seat, "brackets_dm_decided", "", result=outcome.message
                )
        await self.landed(interaction, outcome, cards.REPORT)


class DisputeModal(SetForm):
    def __init__(self, bot: Any, guild: Any, seat: Seat, land: Any) -> None:
        store, gid = bot.store, guild.id
        super().__init__(
            said(store, gid, "brackets_dispute_title", set=seat.match.key), bot, guild, seat, land
        )
        self.note = discord.ui.TextInput(
            label=clipped(said(store, gid, "brackets_dispute_note_label"), LABEL_LIMIT),
            style=discord.TextStyle.paragraph,
            max_length=NOTE_LIMIT,
            required=False,
        )
        self.add_item(self.note)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not await self.started(interaction):
            return
        outcome = await sets_.dispute(
            interaction.client,
            interaction.guild,
            interaction.user,
            self.seat.row["id"],
            self.seat.match.key,
            self.note.value,
        )
        await self.landed(interaction, outcome, cards.DISPUTE)


def reason_input() -> discord.ui.TextInput:
    return discord.ui.TextInput(
        label=REASON_LABEL,
        style=discord.TextStyle.paragraph,
        max_length=REASON_LIMIT,
        required=False,
    )


class DecideModal(SetForm):
    def __init__(self, bot: Any, guild: Any, seat: Seat, land: Any) -> None:
        super().__init__(DECIDE_TITLE.format(set=seat.match.key), bot, guild, seat, land)
        store, gid = bot.store, guild.id
        self.score_a = discord.ui.TextInput(
            label=clipped(
                said(store, gid, "brackets_score_label", name=seat.name("a")), LABEL_LIMIT
            ),
            max_length=SCORE_LIMIT,
        )
        self.score_b = discord.ui.TextInput(
            label=clipped(
                said(store, gid, "brackets_score_label", name=seat.name("b")), LABEL_LIMIT
            ),
            max_length=SCORE_LIMIT,
        )
        self.reason = reason_input()
        for one in (self.score_a, self.score_b, self.reason):
            self.add_item(one)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not await self.started(interaction):
            return
        bot, guild = interaction.client, interaction.guild
        a, b = score_of(self.score_a.value), score_of(self.score_b.value)
        if a is None or b is None:
            outcome = refusal(
                said(bot.store, guild.id, "brackets_score_not_number_said"), "bad_score", 400
            )
        else:
            outcome = await sets_.override(
                bot,
                guild,
                interaction.user,
                self.seat.row["id"],
                self.seat.match.key,
                score_a=a,
                score_b=b,
            )
            if outcome.ok:
                await told_players(
                    bot,
                    guild,
                    self.seat,
                    "brackets_dm_decided",
                    self.reason.value,
                    result=outcome.message,
                )
        await self.landed(interaction, outcome, cards.DECIDE)


class ResetModal(SetForm):
    def __init__(self, bot: Any, guild: Any, seat: Seat, land: Any) -> None:
        super().__init__(RESET_TITLE.format(set=seat.match.key), bot, guild, seat, land)
        self.reason = reason_input()
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not await self.started(interaction):
            return
        bot, guild = interaction.client, interaction.guild
        outcome = await sets_.reset(
            bot, guild, interaction.user, self.seat.row["id"], self.seat.match.key
        )
        if outcome.ok:
            await told_players(bot, guild, self.seat, "brackets_dm_reset", self.reason.value)
        await self.landed(interaction, outcome, cards.RESET)


class ForfeitModal(SetForm):
    def __init__(self, bot: Any, guild: Any, seat: Seat, land: Any, side: str) -> None:
        super().__init__(
            FORFEIT_TITLE.format(name=seat.name(side), set=seat.match.key), bot, guild, seat, land
        )
        self.side = side
        self.reason = reason_input()
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not await self.started(interaction):
            return
        bot, guild = interaction.client, interaction.guild
        outcome = await sets_.override(
            bot,
            guild,
            interaction.user,
            self.seat.row["id"],
            self.seat.match.key,
            winner=self.side,
            forfeit=True,
        )
        if outcome.ok:
            await told_players(
                bot,
                guild,
                self.seat,
                "brackets_dm_decided",
                self.reason.value,
                result=outcome.message,
            )
        await self.landed(interaction, outcome, cards.DECIDE)


__all__ = [
    "ON_CARD",
    "CardLanding",
    "DecideModal",
    "DisputeModal",
    "ForfeitModal",
    "ReportModal",
    "ResetModal",
    "Seat",
    "member_move",
    "may_run",
    "not_organiser",
    "seat_of",
    "set_move",
    "set_pressed",
    "starter_pressed",
    "told_players",
]
