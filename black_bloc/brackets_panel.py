"""The /bracket panel: a member's tournaments and sets, an organiser's legal moves."""

from __future__ import annotations

import re
from typing import Any

import discord

from . import brackets_buttons as buttons_
from . import brackets_cards as cards
from . import brackets_moves as moves_
from . import brackets_people as people_
from . import brackets_sets as sets_
from . import brackets_store as store_
from . import brackets_thread as thread_
from .brackets import access, pools
from .brackets.model import (
    CALLED,
    COMPLETE,
    DISPUTED,
    DOUBLE,
    FORMATS,
    READY,
    REPORTED,
    ROUND_ROBIN,
    SINGLE,
    SWISS,
    BracketError,
)
from .brackets_moves import said
from .command_errors import AnswersErrors
from .panels import (
    KEEP_IT,
    Outcome,
    Panel,
    answer,
    capped_placeholder,
    confirm,
    confirm_items,
    db_up,
    opened,
    refusal,
    retire,
)
from .settings_store import BRACKETS_LENGTHS, BRACKETS_PANEL_MINUTES

HOME = "home"
TOURNAMENT = "tournament"
ENTRANT = "entrant"
SET = "set"
ADD = "add"

OPTIONS_LIMIT = 25
OPTION_TEXT = 100
FIELD_LIMIT = 1024
SEED_LIMIT = 4000
SETS_SHOWN = 10

OPEN_SIGNUPS = "open_signups"
CLOSE_SIGNUPS = "close_signups"
OPEN_CHECK_IN = "open_check_in"
CLOSE_CHECK_IN = "close_check_in"
SEED = "seed"
SHUFFLE = "shuffle"
START = "start"
CALL_READY = "call_ready"
UNSTART = "unstart"
COMPLETE_MOVE = "complete"
REOPEN = "reopen"
CANCEL = "cancel"
RESTORE = "restore"
ADD_ENTRANT = "add"
DROP_OUT = "drop_out"
MOVE = thread_.MOVE
RESTORE_ENTRANT = "restore_entrant"
ADVANCE = "advance"
UNADVANCE = "unadvance"

TO_LABELS = {
    OPEN_SIGNUPS: "Open sign-ups",
    CLOSE_SIGNUPS: "Close sign-ups",
    OPEN_CHECK_IN: "Open check-in",
    CLOSE_CHECK_IN: "Close check-in",
    SEED: "Seed…",
    SHUFFLE: "Shuffle",
    START: "Start",
    CALL_READY: "Call ready sets",
    UNSTART: "Back to seeding",
    COMPLETE_MOVE: "Complete",
    REOPEN: "Reopen",
    CANCEL: "Cancel",
    RESTORE: "Restore",
    ADD_ENTRANT: "Add entrant…",
    MOVE: "Move to #knuck-up",
    ADVANCE: "Advance to the final",
    UNADVANCE: "Back to pools",
}
TO_STYLES = {
    ADVANCE: discord.ButtonStyle.success,
    UNADVANCE: discord.ButtonStyle.danger,
    START: discord.ButtonStyle.success,
    COMPLETE_MOVE: discord.ButtonStyle.success,
    CANCEL: discord.ButtonStyle.danger,
    UNSTART: discord.ButtonStyle.danger,
}
TO_MOVES: dict[str, tuple[str, ...]] = {
    store_.DRAFT: (OPEN_SIGNUPS, ADD_ENTRANT, CANCEL),
    store_.SIGNUPS: (CLOSE_SIGNUPS, OPEN_CHECK_IN, ADD_ENTRANT, CANCEL),
    store_.CHECK_IN: (CLOSE_CHECK_IN, ADD_ENTRANT, CANCEL),
    store_.SEEDING: (OPEN_SIGNUPS, OPEN_CHECK_IN, SEED, SHUFFLE, START, ADD_ENTRANT, CANCEL),
    store_.POOLS: (CALL_READY, ADVANCE, UNSTART, CANCEL),
    store_.RUNNING: (CALL_READY, COMPLETE_MOVE, UNADVANCE, UNSTART, CANCEL),
    store_.COMPLETE: (REOPEN, CANCEL),
    store_.CANCELLED: (RESTORE,),
}
CONFIRMED = {
    CANCEL: "Cancel **{name}**? Every result stays and Restore brings it back.",
    UNSTART: "Send **{name}** back to seeding? Every set and result is cleared.",
    MOVE: "Move **{name}** into #knuck-up? Its players are pinged there.",
    ADVANCE: "Build **{name}**'s final from the pools?",
    UNADVANCE: "Send **{name}** back to its pools? The final's sets are cleared.",
}
MEMBER_LISTED = (store_.SIGNUPS, store_.CHECK_IN, store_.SEEDING, *store_.PLAYING)

CREATE_PICK = "Create…"
CREATE_NAME = "Name"
CREATE_GAME = "Game"
CREATE_BEST_OF = "Best of"
CREATE_CAP = "Entrant cap (blank: none)"
CREATE_THIRD = "Third-place set"
CREATE_RESET = "Grand-final reset"
CREATE_ROUNDS = "Swiss rounds (blank: automatic)"
CREATE_ID = "bk-create-"
FORMAT_LINES = {
    SINGLE: "One loss and out",
    DOUBLE: "Two losses and out",
    ROUND_ROBIN: "Everyone plays everyone",
    SWISS: "Paired by record each round",
}
FORMAT_EXTRAS = {
    SINGLE: ("third_place",),
    DOUBLE: ("grand_final_reset",),
    ROUND_ROBIN: (),
    SWISS: ("rounds",),
}
SEED_TITLE = "Seeding, top seed first"
SEED_LABEL = "One entrant per line"
SEED_UNKNOWN = "Line {line} names nobody in **{name}**, so nothing was changed."
CALLED_SETS = "Called {count} set(s) in **{name}**."
NOTHING_READY = "No set in **{name}** is ready to call."
OPEN_SETS = "Open sets"
ENTRANT_PICK = "Pick an entrant…"
SET_PICK_TO = "Pick a set…"
MEMBER_PICK = "Add a member…"
GUEST_LABEL = "Add a guest…"
GUEST_TITLE = "Add a guest"
GUEST_NAME = "Their name"
FORFEIT_LABEL = "{name} by forfeit…"
LET_STAND = "Let it stand"
ENTRANT_LABELS = {
    "remove": "Remove…",
    "restore": "Restore",
    "check_in": "Check in",
    "check_out": "Check out",
    "dq": "DQ…",
    "drop": "Drop…",
}
ENTRANT_TITLES = {
    "remove": "Remove {entrant}",
    "dq": "Disqualify {entrant}",
    "drop": "Drop {entrant}",
}
ENTRANT_DMS = {
    "remove": "brackets_dm_removed",
    "dq": "brackets_dm_dq",
    "drop": "brackets_dm_dropped",
}
ENTRANT_LINES = {
    "seed": "Seed {seed}",
    "checked_in": "Checked in",
    "dq": "Disqualified",
    "out": "Out — {why}",
    "guest": "Guest",
}


class BracketPanel(Panel):
    def __init__(self, bot: Any, guild_id: int, place: tuple[Any, ...]) -> None:
        super().__init__(
            int(bot.store.get(guild_id, BRACKETS_PANEL_MINUTES)),
            footer=said(bot.store, guild_id, "brackets_panel_footer"),
            again=self.shown_again,
        )
        self.place = place

    async def shown_again(self, interaction: discord.Interaction, previous: Any) -> None:
        await render(interaction, self.place, previous)


class PanelLanding:
    """A move pressed on the panel: it re-renders with the answer, then the cards catch up."""

    def __init__(self, place: tuple[Any, ...], previous: Any) -> None:
        self.place = place
        self.previous = previous

    async def begin(self, interaction: discord.Interaction) -> None:
        if not interaction.response.is_done():
            await interaction.response.defer()

    async def end(
        self, interaction: discord.Interaction, tournament_id: int, outcome: Outcome, move: str
    ) -> None:
        await render(interaction, self.place, self.previous, note=outcome.message)
        await thread_.follow(
            interaction.client, interaction.guild, tournament_id, outcome, move=move
        )


def words(bot: Any, guild: Any, key: str, **fields: Any) -> str:
    return said(bot.store, guild.id, key, **fields)


def organiser(bot: Any, guild: Any, user: Any) -> bool:
    return access.may_run(bot.store, guild, user)


def text(value: Any, limit: int = OPTION_TEXT) -> str:
    return str(value or "")[:limit] or "—"


def with_note(note: str, body: str) -> str:
    return "\n\n".join(part for part in (note, body) if part)[:4000]


async def build_home(
    bot: Any, guild: Any, user: Any, *, note: str = ""
) -> tuple[discord.Embed, BracketPanel]:
    runs = organiser(bot, guild, user)
    rows = await store_.tournaments(bot.db, guild.id)
    shown = [row for row in rows if runs or row["state"] in MEMBER_LISTED]
    lines = [
        words(
            bot,
            guild,
            "brackets_panel_line",
            name=row["name"],
            state=cards.state_words(bot.store, guild.id, row["state"]),
            count=row["entrant_count"],
        )
        for row in shown[:OPTIONS_LIMIT]
    ] or [words(bot, guild, "brackets_panel_empty")]
    embed = discord.Embed(
        title=words(bot, guild, "brackets_panel_title"),
        description=with_note(note, "\n".join(lines)),
    )
    view = BracketPanel(bot, guild.id, (HOME,))
    if shown:
        view.add_item(TournamentPick(bot, guild, shown))
    if runs:
        view.add_item(FormatPick(bot, guild))
    return (embed, view)


def legal_to_moves(row: Any, current: Any) -> list[str]:
    found = list(TO_MOVES.get(row["state"], ()))
    if row["state"] in store_.PLAYING:
        if current is None or not any(one.state == READY for one in current.matches.values()):
            found.remove(CALL_READY)
    if row["state"] == store_.RUNNING:
        if current is None or not pools.finished(current):
            found.remove(COMPLETE_MOVE)
        if not may_unadvance(current):
            found.remove(UNADVANCE)
    if row["state"] == store_.POOLS and (current is None or not pools.pools_finished(current)):
        found.remove(ADVANCE)
    return found


def may_unadvance(current: Any) -> bool:
    if current is None or current.plan is None:
        return False
    try:
        pools.unadvance(current)
    except BracketError:
        return False
    return True


def member_moves(row: Any, mine: Any) -> list[str]:
    """Leave wherever it is legal — in, before the start — as the starter card offers it."""
    state = row["state"]
    inside = mine is not None and not mine["dropped"] and not mine["dq"]
    if state == store_.SIGNUPS and not inside:
        return [cards.JOIN]
    if state == store_.CHECK_IN and inside and not mine["checked_in"]:
        return [cards.CHECK_IN, cards.LEAVE]
    if state in store_.BEFORE_START and inside:
        return [cards.LEAVE]
    if state in store_.PLAYING and inside:
        return [DROP_OUT]
    return []


def may_move(bot: Any, guild: Any, user: Any, row: Any) -> bool:
    return (
        access.is_staff(bot.store, user)
        and bool(row["shadow"])
        and moves_.mode_of(bot.store, guild.id) == moves_.ON
    )


def players(bot: Any, guild: Any, match: Any, people: dict) -> str:
    return words(
        bot,
        guild,
        "brackets_set_card_players",
        a=cards.name_of(people, match.slot_a),
        b=cards.name_of(people, match.slot_b),
    )


def set_line(bot: Any, guild: Any, row: Any, match: Any, people: dict) -> str:
    status = cards.status_line(bot.store, guild.id, match, people, row["confirm_minutes"])
    return f"**{match.key}** · {players(bot, guild, match, people)} · {status[0]}"


def entrant_option(person: Any) -> discord.SelectOption:
    state = (
        "DQ" if person["dq"] else (person["dropped_why"] or "out") if person["dropped"] else "in"
    )
    return discord.SelectOption(
        label=text(f"{person['seed'] or '—'}. {person['name']}"),
        value=str(person["id"]),
        description=text(state),
    )


def set_option(bot: Any, guild: Any, row: Any, match: Any, people: dict) -> discord.SelectOption:
    return discord.SelectOption(
        label=text(f"{match.key} · {players(bot, guild, match, people)}"),
        value=match.key,
        description=text(cards.status_line(bot.store, guild.id, match, people, 0)[0]),
    )


async def build_tournament(
    bot: Any, guild: Any, user: Any, tournament_id: int, *, note: str = ""
) -> tuple[discord.Embed, BracketPanel]:
    row = await store_.tournament(bot.db, guild.id, int(tournament_id))
    if row is None:
        return await build_home(
            bot, guild, user, note=buttons_.no_tournament(bot, guild, tournament_id).message
        )
    runs = organiser(bot, guild, user)
    everyone = await store_.entrants(bot.db, row["id"])
    people = {one["id"]: one for one in everyone}
    mine = next((one for one in everyone if one["user_id"] == getattr(user, "id", None)), None)
    current = await store_.bracket(bot.db, row)
    embed = cards.starter_embed(bot.store, guild.id, row, everyone, current)
    embed.description = with_note(note, embed.description or "")
    playing = [
        one for one in (current.ordered() if current else []) if one.state not in cards.CLEARED
    ]
    own = [one for one in playing if mine is not None and one.holds(mine["id"])]
    open_own = [one for one in own if one.state in cards.OPEN_CARD]
    if open_own:
        embed.add_field(
            name=words(bot, guild, "brackets_your_sets_title"),
            value="\n".join(set_line(bot, guild, row, one, people) for one in open_own)[
                :FIELD_LIMIT
            ],
            inline=False,
        )
    open_all = [one for one in playing if one.state in cards.OPEN_CARD]
    if runs and open_all:
        embed.add_field(
            name=OPEN_SETS,
            value="\n".join(
                set_line(bot, guild, row, one, people) for one in open_all[:SETS_SHOWN]
            )[:FIELD_LIMIT],
            inline=False,
        )
    view = BracketPanel(bot, guild.id, (TOURNAMENT, row["id"]))
    for move in member_moves(row, mine):
        view.add_item(MemberButton(bot, guild, row["id"], move))
    view.add_item(BackButton(bot, guild, (HOME,)))
    if runs:
        moves = legal_to_moves(row, current)
        moves += [MOVE] if may_move(bot, guild, user, row) else []
        for index, move in enumerate(moves):
            if move == SEED and not seed_text(everyone):
                continue
            view.add_item(ToButton(row["id"], move, row=1 if index < 5 else 2))
        if everyone:
            view.add_item(EntrantPick(row["id"], everyone))
    pickable = sorted(playing, key=lambda one: one.state == COMPLETE) if runs else own
    if pickable:
        view.add_item(SetPick(bot, guild, row, pickable, people, runs))
    return (embed, view)


def entrant_moves(row: Any, person: Any) -> list[str]:
    state = row["state"]
    out = bool(person["dropped"] or person["dq"])
    if state in store_.BEFORE_START:
        found = ["restore"] if out else ["remove"]
        if state == store_.CHECK_IN and not out:
            found.insert(0, "check_out" if person["checked_in"] else "check_in")
        return found
    if state in store_.PLAYING:
        return ["restore"] if out else ["dq", "drop"]
    return []


def entrant_lines(person: Any) -> list[str]:
    found = []
    if person["seed"] is not None:
        found.append(ENTRANT_LINES["seed"].format(seed=person["seed"]))
    if person["user_id"] is None:
        found.append(ENTRANT_LINES["guest"])
    else:
        found.append(f"<@{int(person['user_id'])}>")
    if person["checked_in"]:
        found.append(ENTRANT_LINES["checked_in"])
    if person["dq"]:
        found.append(ENTRANT_LINES["dq"])
    elif person["dropped"]:
        found.append(ENTRANT_LINES["out"].format(why=person["dropped_why"] or "—"))
    return found


async def build_entrant(
    bot: Any, guild: Any, user: Any, tournament_id: int, entrant_id: int, *, note: str = ""
) -> tuple[discord.Embed, BracketPanel]:
    row = await store_.tournament(bot.db, guild.id, int(tournament_id))
    person = await store_.entrant(bot.db, int(tournament_id), int(entrant_id)) if row else None
    if row is None or person is None:
        return await build_tournament(bot, guild, user, tournament_id, note=note)
    embed = discord.Embed(
        title=text(person["name"], 256),
        description=with_note(note, "\n".join(entrant_lines(person))),
    )
    view = BracketPanel(bot, guild.id, (ENTRANT, row["id"], person["id"]))
    for move in entrant_moves(row, person):
        view.add_item(EntrantButton(row["id"], person["id"], move))
    view.add_item(BackButton(bot, guild, (TOURNAMENT, row["id"])))
    return (embed, view)


def set_moves_for(row: Any, seat: Any, runs: bool) -> list[str]:
    state = seat.match.state
    found: list[str] = []
    if row["state"] not in store_.PLAYING:
        return found
    if row["state"] == store_.RUNNING and seat.match.pool:
        return found
    if seat.side is not None and state in (READY, CALLED):
        found.append(cards.REPORT)
    if seat.side is not None and state == REPORTED and seat.match.reported_side != seat.side:
        found += [cards.CONFIRM, cards.DISPUTE]
    if not runs:
        return found
    if seat.side is None and state in (READY, CALLED):
        found.append(cards.REPORT)
    if state == READY:
        found.append(cards.CALL)
    if state in (REPORTED, DISPUTED) and seat.side is None:
        found.append(LET_STAND)
    if state in (READY, CALLED, REPORTED, DISPUTED, COMPLETE):
        found += [cards.DECIDE, "forfeit_a", "forfeit_b"]
    if state in (CALLED, REPORTED, DISPUTED, COMPLETE):
        found.append(cards.RESET)
    return found


async def build_set(
    bot: Any, guild: Any, user: Any, tournament_id: int, key: str, *, note: str = ""
) -> tuple[discord.Embed, BracketPanel]:
    seat = await buttons_.seat_of(bot, guild, user, tournament_id, key)
    if isinstance(seat, Outcome):
        return await build_tournament(bot, guild, user, tournament_id, note=note or seat.message)
    row, match, people = seat.row, seat.match, seat.people
    embed = cards.set_embed(bot.store, guild.id, match, people, row["confirm_minutes"])
    players = cards.players_line(bot.store, guild.id, match, people)
    body = f"{players}\n{embed.description or ''}"
    embed.description = with_note("" if note in body.split("\n") else note, body)
    view = BracketPanel(bot, guild.id, (SET, row["id"], match.key))
    for move in set_moves_for(row, seat, organiser(bot, guild, user)):
        view.add_item(SetMoveButton(row["id"], match.key, move, seat_label(bot, guild, seat, move)))
    view.add_item(BackButton(bot, guild, (TOURNAMENT, row["id"])))
    return (embed, view)


def seat_label(bot: Any, guild: Any, seat: Any, move: str) -> str:
    if move == LET_STAND:
        return LET_STAND
    if move in ("forfeit_a", "forfeit_b"):
        return FORFEIT_LABEL.format(name=seat.name(move[-1]))[:80]
    return cards.label(bot.store, guild.id, move)


async def build_add(
    bot: Any, guild: Any, user: Any, tournament_id: int, *, note: str = ""
) -> tuple[discord.Embed, BracketPanel]:
    row = await store_.tournament(bot.db, guild.id, int(tournament_id))
    if row is None:
        return await build_home(bot, guild, user, note=note)
    embed = discord.Embed(title=text(row["name"], 256), description=note or None)
    view = BracketPanel(bot, guild.id, (ADD, row["id"]))
    view.add_item(AddMemberPick(row["id"]))
    view.add_item(GuestButton(row["id"]))
    view.add_item(BackButton(bot, guild, (TOURNAMENT, row["id"])))
    return (embed, view)


async def built(
    interaction: discord.Interaction, place: tuple[Any, ...], note: str = ""
) -> tuple[discord.Embed, BracketPanel]:
    bot, guild, user = interaction.client, interaction.guild, interaction.user
    kind = place[0]
    if kind == TOURNAMENT:
        return await build_tournament(bot, guild, user, place[1], note=note)
    if kind == ENTRANT:
        return await build_entrant(bot, guild, user, place[1], place[2], note=note)
    if kind == SET:
        return await build_set(bot, guild, user, place[1], place[2], note=note)
    if kind == ADD:
        return await build_add(bot, guild, user, place[1], note=note)
    return await build_home(bot, guild, user, note=note)


async def render(
    interaction: discord.Interaction,
    place: tuple[Any, ...],
    previous: Any = None,
    *,
    note: str = "",
) -> None:
    embed, view = await built(interaction, place, note)
    retire(previous)
    view.message = await interaction.edit_original_response(
        content=None, embed=embed, view=view, allowed_mentions=discord.AllowedMentions.none()
    )


async def open_panel(interaction: discord.Interaction) -> None:
    if not await db_up(interaction):
        return
    embed, view = await build_home(interaction.client, interaction.guild, interaction.user)
    await interaction.response.send_message(
        embed=embed, view=view, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
    )
    view.message = await interaction.original_response()


async def landed(
    interaction: discord.Interaction,
    place: tuple[Any, ...],
    previous: Any,
    tournament_id: int,
    outcome: Outcome,
    move: str,
) -> None:
    await PanelLanding(place, previous).end(interaction, tournament_id, outcome, move)


async def form_opened(interaction: discord.Interaction, modal: discord.ui.Modal) -> None:
    """A form is the first answer, so the organiser and the database are asked without a defer."""
    if not await db_up(interaction):
        return
    refused = buttons_.off_now(interaction.client, interaction.guild)
    if refused:
        await answer(interaction, refused)
        return
    if not organiser(interaction.client, interaction.guild, interaction.user):
        await answer(
            interaction, buttons_.not_organiser(interaction.client, interaction.guild).message
        )
        return
    await interaction.response.send_modal(modal)


class BackButton(discord.ui.Button):
    def __init__(self, bot: Any, guild: Any, place: tuple[Any, ...]) -> None:
        super().__init__(
            label=text(words(bot, guild, "brackets_back_label"), 80),
            style=discord.ButtonStyle.secondary,
            row=0,
        )
        self.place = place

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await opened(interaction, staff=False):
            return
        await render(interaction, self.place, self.view)


class TournamentPick(discord.ui.Select):
    def __init__(self, bot: Any, guild: Any, rows: list[Any]) -> None:
        options = [
            discord.SelectOption(
                label=text(row["name"]),
                value=str(row["id"]),
                description=text(cards.state_words(bot.store, guild.id, row["state"])),
            )
            for row in rows[:OPTIONS_LIMIT]
        ]
        pick = text(words(bot, guild, "brackets_pick_placeholder"), 150)
        super().__init__(
            placeholder=capped_placeholder(len(options), len(rows), pick=pick)[:150],
            options=options,
            row=1,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await opened(interaction, staff=False):
            return
        await render(interaction, (TOURNAMENT, int(self.values[0])), self.view)


class FormatPick(discord.ui.Select):
    def __init__(self, bot: Any, guild: Any) -> None:
        options = [
            discord.SelectOption(
                label=text(words(bot, guild, cards.FORMAT_KEYS[one])),
                value=one,
                description=FORMAT_LINES[one],
            )
            for one in FORMATS
        ]
        super().__init__(placeholder=CREATE_PICK, options=options, row=2)

    async def callback(self, interaction: discord.Interaction) -> None:
        bot, guild = interaction.client, interaction.guild
        modal = CreateModal(bot, guild, self.values[0], self.view)
        await form_opened(interaction, modal)


def typed(
    custom: str, limit: int, *, required: bool = False, default: Any = None
) -> discord.ui.TextInput:
    return discord.ui.TextInput(
        custom_id=CREATE_ID + custom,
        max_length=limit,
        required=required,
        default=None if default is None else str(default),
    )


def whole(value: str) -> Any:
    value = value.strip()
    if not value:
        return None
    return int(value) if value.isdigit() else value


class CreateModal(AnswersErrors, discord.ui.Modal):
    def __init__(self, bot: Any, guild: Any, chosen: str, previous: Any = None) -> None:
        super().__init__(title=text(words(bot, guild, cards.FORMAT_KEYS[chosen]), 45))
        self.chosen = chosen
        self.previous = previous
        defaults = moves_.option_defaults(bot.store, guild.id)
        self.name = self.ask(typed("name", moves_.NAME_LIMIT, required=True), CREATE_NAME)
        self.game = self.ask(typed("game", moves_.GAME_LIMIT), CREATE_GAME)
        self.best_of = self.ask(
            discord.ui.Select(
                custom_id=CREATE_ID + "best_of",
                options=[
                    discord.SelectOption(
                        label=f"{CREATE_BEST_OF} {one}",
                        value=one,
                        default=one == str(defaults["best_of"]),
                    )
                    for one in BRACKETS_LENGTHS
                ],
            ),
            CREATE_BEST_OF,
        )
        self.cap = self.ask(typed("cap", 4, default=defaults["entrant_cap"]), CREATE_CAP)
        extras = FORMAT_EXTRAS[chosen]
        if "third_place" in extras:
            self.third_place = self.ask(self.tick("third_place", defaults), CREATE_THIRD)
        if "grand_final_reset" in extras:
            self.grand_final_reset = self.ask(
                self.tick("grand_final_reset", defaults), CREATE_RESET
            )
        if "rounds" in extras:
            self.rounds = self.ask(
                typed("rounds", 2, default=defaults["swiss_rounds"]), CREATE_ROUNDS
            )

    def ask(self, component: Any, label: str) -> Any:
        self.add_item(discord.ui.Label(text=label, component=component))
        return component

    @staticmethod
    def tick(field: str, defaults: dict[str, Any]) -> discord.ui.Checkbox:
        return discord.ui.Checkbox(custom_id=CREATE_ID + field, default=bool(defaults[field]))

    def given(self) -> dict[str, Any]:
        found: dict[str, Any] = {
            "name": self.name.value,
            "game": self.game.value,
            "format": self.chosen,
            "entrant_cap": whole(self.cap.value),
        }
        if self.best_of.values:
            found["best_of"] = int(self.best_of.values[0])
        for field in ("third_place", "grand_final_reset"):
            if field in FORMAT_EXTRAS[self.chosen]:
                found[field] = bool(getattr(self, field).value)
        if "rounds" in FORMAT_EXTRAS[self.chosen]:
            found["swiss_rounds"] = whole(self.rounds.value)
        return found

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not await opened(interaction, staff=False):
            return
        bot, guild = interaction.client, interaction.guild
        outcome = await moves_.create(bot, guild, interaction.user, self.given())
        if not outcome.ok:
            await render(interaction, (HOME,), self.previous, note=outcome.message)
            return
        await landed(
            interaction,
            (TOURNAMENT, outcome.value),
            self.previous,
            outcome.value,
            outcome,
            "create",
        )


def seed_text(everyone: list[Any]) -> str:
    lines = [
        f"{one['name']} #{one['id']}" for one in everyone if not one["dropped"] and not one["dq"]
    ]
    found = "\n".join(lines)
    return found if 0 < len(found) <= SEED_LIMIT else ""


def seed_order(text_value: str, everyone: list[Any]) -> tuple[list[int] | None, int]:
    playing = [one for one in everyone if not one["dropped"] and not one["dq"]]
    ids = {one["id"] for one in playing}
    by_name: dict[str, list[int]] = {}
    for one in playing:
        by_name.setdefault(str(one["name"]).strip().lower(), []).append(one["id"])
    order: list[int] = []
    for number, line in enumerate(
        (one.strip() for one in text_value.splitlines() if one.strip()), start=1
    ):
        tagged = re.search(r"#(\d+)\s*$", line)
        if tagged and int(tagged.group(1)) in ids:
            order.append(int(tagged.group(1)))
            continue
        named = by_name.get(re.sub(r"^\d+[.)]\s*", "", line).strip().lower(), [])
        if len(named) != 1:
            return (None, number)
        order.append(named[0])
    return (order, 0)


class SeedModal(AnswersErrors, discord.ui.Modal, title=SEED_TITLE):
    order = discord.ui.TextInput(
        label=SEED_LABEL, style=discord.TextStyle.paragraph, max_length=SEED_LIMIT
    )

    def __init__(self, tournament_id: int, everyone: list[Any], previous: Any = None) -> None:
        super().__init__()
        self.tournament_id = int(tournament_id)
        self.everyone = everyone
        self.order.default = seed_text(everyone)
        self.previous = previous

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not await opened(interaction, staff=False):
            return
        bot, guild = interaction.client, interaction.guild
        row = await store_.tournament(bot.db, guild.id, self.tournament_id)
        everyone = await store_.entrants(bot.db, self.tournament_id) if row else []
        order, line = seed_order(self.order.value, everyone)
        if row is None:
            outcome = buttons_.no_tournament(bot, guild, self.tournament_id)
        elif order is None:
            outcome = refusal(SEED_UNKNOWN.format(line=line, name=row["name"]), "bad_order", 400)
        else:
            outcome = await moves_.seed(
                bot, guild, interaction.user, self.tournament_id, order=order
            )
        await landed(
            interaction,
            (TOURNAMENT, self.tournament_id),
            self.previous,
            self.tournament_id,
            outcome,
            SEED,
        )


async def call_ready(bot: Any, guild: Any, user: Any, tournament_id: int) -> Outcome:
    row = await store_.tournament(bot.db, guild.id, int(tournament_id))
    if row is None:
        return buttons_.no_tournament(bot, guild, tournament_id)
    current = await store_.bracket(bot.db, row)
    ready = [one.key for one in (current.ordered() if current else []) if one.state == READY]
    if not ready:
        return refusal(NOTHING_READY.format(name=row["name"]), "nothing_ready", 409)
    changed: list[str] = []
    for key in ready:
        outcome = await sets_.call(bot, guild, user, row["id"], key)
        if not outcome.ok:
            return outcome
        changed.extend(outcome.changed)
    return Outcome(
        True,
        CALLED_SETS.format(count=len(ready), name=row["name"]),
        value=row["id"],
        changed=tuple(dict.fromkeys(changed)),
    )


async def run_to_move(interaction: discord.Interaction, tournament_id: int, move: str) -> Outcome:
    bot, guild, user = interaction.client, interaction.guild, interaction.user
    plain = {
        OPEN_SIGNUPS: moves_.open_signups,
        CLOSE_SIGNUPS: moves_.close_signups,
        OPEN_CHECK_IN: people_.open_check_in,
        CLOSE_CHECK_IN: people_.close_check_in,
        START: moves_.start,
        UNSTART: moves_.unstart,
        COMPLETE_MOVE: moves_.complete,
        REOPEN: moves_.reopen,
        CANCEL: moves_.cancel,
        RESTORE: moves_.restore,
        MOVE: thread_.move_home,
        ADVANCE: moves_.advance,
        UNADVANCE: moves_.unadvance,
    }
    if move == SHUFFLE:
        return await moves_.seed(bot, guild, user, tournament_id, randomise=True)
    if move == CALL_READY:
        return await call_ready(bot, guild, user, tournament_id)
    return await plain[move](bot, guild, user, tournament_id)


async def to_pressed(
    interaction: discord.Interaction, tournament_id: int, move: str, previous: Any
) -> None:
    place = (TOURNAMENT, tournament_id)
    if move == SEED:
        everyone = await store_.entrants(interaction.client.db, tournament_id)
        await form_opened(interaction, SeedModal(tournament_id, everyone, previous))
        return
    if not await opened(interaction, staff=False):
        return
    if move == ADD_ENTRANT:
        await render(interaction, (ADD, tournament_id), previous)
        return
    if move in CONFIRMED:
        await ask_first(interaction, tournament_id, move, previous)
        return
    outcome = await run_to_move(interaction, tournament_id, move)
    await landed(interaction, place, previous, tournament_id, outcome, move)


async def ask_first(
    interaction: discord.Interaction, tournament_id: int, move: str, previous: Any
) -> None:
    bot, guild, user = interaction.client, interaction.guild, interaction.user
    row = await store_.tournament(bot.db, guild.id, int(tournament_id))
    if row is None:
        await render(interaction, (HOME,), previous)
        return
    place = (TOURNAMENT, row["id"])
    embed, _ = await build_tournament(bot, guild, user, row["id"])
    view = BracketPanel(bot, guild.id, place)
    if move == DROP_OUT:
        question = words(bot, guild, "brackets_drop_confirm", name=row["name"])
        yes = text(words(bot, guild, "brackets_drop_label"), 80)
    else:
        question = CONFIRMED[move].format(name=row["name"])
        yes = TO_LABELS[move]

    async def on_yes(pressed: discord.Interaction, shown: Any) -> None:
        if not await opened(pressed, staff=False):
            return
        if move == DROP_OUT:
            outcome = await drop_out(pressed, row["id"])
        else:
            outcome = await run_to_move(pressed, row["id"], move)
        await landed(pressed, place, shown, row["id"], outcome, move)

    async def on_no(pressed: discord.Interaction, shown: Any) -> None:
        if not await opened(pressed, staff=False):
            return
        await render(pressed, place, shown)

    await confirm(
        interaction,
        view,
        embed,
        confirm_items(yes=yes, no=KEEP_IT, on_yes=on_yes, on_no=on_no, row=1),
        previous,
        question=question,
    )


async def drop_out(interaction: discord.Interaction, tournament_id: int) -> Outcome:
    bot, guild, user = interaction.client, interaction.guild, interaction.user
    row = await store_.tournament(bot.db, guild.id, int(tournament_id))
    if row is None:
        return buttons_.no_tournament(bot, guild, tournament_id)
    mine = await store_.entrant_of(bot.db, row["id"], int(user.id))
    if mine is None:
        return buttons_.not_entered(bot, guild, row)
    return await people_.drop(bot, guild, user, row["id"], mine["id"])


class ToButton(discord.ui.Button):
    def __init__(self, tournament_id: int, move: str, *, row: int) -> None:
        super().__init__(
            label=TO_LABELS[move],
            style=TO_STYLES.get(move, discord.ButtonStyle.secondary),
            row=row,
        )
        self.tournament_id = int(tournament_id)
        self.move = move

    async def callback(self, interaction: discord.Interaction) -> None:
        await to_pressed(interaction, self.tournament_id, self.move, self.view)


class MemberButton(discord.ui.Button):
    def __init__(self, bot: Any, guild: Any, tournament_id: int, move: str) -> None:
        if move == DROP_OUT:
            shown, style = words(bot, guild, "brackets_drop_label"), discord.ButtonStyle.danger
        else:
            shown, style = cards.label(bot.store, guild.id, move), cards.STYLES[move]
        super().__init__(label=text(shown, 80), style=style, row=0)
        self.tournament_id = int(tournament_id)
        self.move = move

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await opened(interaction, staff=False):
            return
        if self.move == DROP_OUT:
            await ask_first(interaction, self.tournament_id, DROP_OUT, self.view)
            return
        outcome = await buttons_.member_move(
            interaction.client, interaction.guild, interaction.user, self.tournament_id, self.move
        )
        await landed(
            interaction,
            (TOURNAMENT, self.tournament_id),
            self.view,
            self.tournament_id,
            outcome,
            self.move,
        )


class EntrantPick(discord.ui.Select):
    def __init__(self, tournament_id: int, everyone: list[Any]) -> None:
        options = [entrant_option(one) for one in everyone[:OPTIONS_LIMIT]]
        super().__init__(
            placeholder=capped_placeholder(len(options), len(everyone), pick=ENTRANT_PICK),
            options=options,
            row=3,
        )
        self.tournament_id = int(tournament_id)

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await opened(interaction, staff=False):
            return
        await render(interaction, (ENTRANT, self.tournament_id, int(self.values[0])), self.view)


class SetPick(discord.ui.Select):
    def __init__(
        self, bot: Any, guild: Any, row: Any, matches: list[Any], people: dict, runs: bool
    ) -> None:
        options = [set_option(bot, guild, row, one, people) for one in matches[:OPTIONS_LIMIT]]
        pick = (
            SET_PICK_TO if runs else text(words(bot, guild, "brackets_pick_set_placeholder"), 150)
        )
        super().__init__(
            placeholder=capped_placeholder(len(options), len(matches), pick=pick)[:150],
            options=options,
            row=4,
        )
        self.tournament_id = int(row["id"])

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await opened(interaction, staff=False):
            return
        await render(interaction, (SET, self.tournament_id, self.values[0]), self.view)


class EntrantButton(discord.ui.Button):
    def __init__(self, tournament_id: int, entrant_id: int, move: str) -> None:
        style = discord.ButtonStyle.danger if move in ENTRANT_DMS else discord.ButtonStyle.secondary
        super().__init__(label=ENTRANT_LABELS[move], style=style, row=1)
        self.tournament_id = int(tournament_id)
        self.entrant_id = int(entrant_id)
        self.move = move

    async def callback(self, interaction: discord.Interaction) -> None:
        place = (ENTRANT, self.tournament_id, self.entrant_id)
        if self.move in ENTRANT_DMS:
            person = await store_.entrant(
                interaction.client.db, self.tournament_id, self.entrant_id
            )
            modal = EntrantReasonModal(
                self.tournament_id, self.entrant_id, self.move, person, self.view
            )
            await form_opened(interaction, modal)
            return
        if not await opened(interaction, staff=False):
            return
        bot, guild, user = interaction.client, interaction.guild, interaction.user
        if self.move == "restore":
            outcome = await people_.restore_entrant(
                bot, guild, user, self.tournament_id, self.entrant_id
            )
        else:
            outcome = await people_.set_check_in(
                bot,
                guild,
                user,
                self.tournament_id,
                self.entrant_id,
                self.move == "check_in",
            )
        move = RESTORE_ENTRANT if self.move == "restore" else self.move
        await landed(interaction, place, self.view, self.tournament_id, outcome, move)


class EntrantReasonModal(AnswersErrors, discord.ui.Modal):
    def __init__(
        self, tournament_id: int, entrant_id: int, move: str, person: Any, previous: Any = None
    ) -> None:
        name = person["name"] if person is not None else f"#{entrant_id}"
        super().__init__(title=ENTRANT_TITLES[move].format(entrant=name)[:45])
        self.tournament_id = int(tournament_id)
        self.entrant_id = int(entrant_id)
        self.move = move
        self.previous = previous
        self.reason = buttons_.reason_input()
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not await opened(interaction, staff=False):
            return
        bot, guild, user = interaction.client, interaction.guild, interaction.user
        act = {
            "remove": people_.remove_entrant,
            "dq": people_.dq,
            "drop": people_.drop,
        }[self.move]
        person = await store_.entrant(bot.db, self.tournament_id, self.entrant_id)
        outcome = await act(bot, guild, user, self.tournament_id, self.entrant_id)
        if outcome.ok and person is not None:
            row = await store_.tournament(bot.db, guild.id, self.tournament_id)
            await thread_.tell(
                bot,
                guild,
                row,
                person["user_id"],
                ENTRANT_DMS[self.move],
                self.reason.value,
                actor=user,
            )
        await landed(
            interaction,
            (ENTRANT, self.tournament_id, self.entrant_id),
            self.previous,
            self.tournament_id,
            outcome,
            self.move,
        )


class SetMoveButton(discord.ui.Button):
    def __init__(self, tournament_id: int, key: str, move: str, shown: str) -> None:
        player = move in cards.PLAYER_ACTIONS
        super().__init__(
            label=text(shown, 80),
            style=cards.STYLES.get(move, discord.ButtonStyle.secondary),
            row=1 if player else 2,
        )
        self.tournament_id = int(tournament_id)
        self.key = key
        self.move = move

    async def callback(self, interaction: discord.Interaction) -> None:
        place = (SET, self.tournament_id, self.key)
        land = PanelLanding(place, self.view)
        if self.move in ("forfeit_a", "forfeit_b"):
            bot, guild = interaction.client, interaction.guild
            if not await db_up(interaction):
                return
            seat = await buttons_.seat_of(
                bot, guild, interaction.user, self.tournament_id, self.key
            )
            if isinstance(seat, Outcome):
                await answer(interaction, seat.message)
                return
            await form_opened(
                interaction, buttons_.ForfeitModal(bot, guild, seat, land, self.move[-1])
            )
            return
        if self.move == LET_STAND:
            if not await opened(interaction, staff=False):
                return
            outcome = await sets_.confirm_report(
                interaction.client,
                interaction.guild,
                interaction.user,
                self.tournament_id,
                self.key,
            )
            await land.end(interaction, self.tournament_id, outcome, cards.CONFIRM)
            return
        await buttons_.set_move(interaction, self.tournament_id, self.key, self.move, land)


class AddMemberPick(discord.ui.UserSelect):
    def __init__(self, tournament_id: int) -> None:
        super().__init__(placeholder=MEMBER_PICK, min_values=1, max_values=1, row=1)
        self.tournament_id = int(tournament_id)

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await opened(interaction, staff=False):
            return
        outcome = await people_.add_entrant(
            interaction.client,
            interaction.guild,
            interaction.user,
            self.tournament_id,
            user_id=int(self.values[0].id),
        )
        await landed(
            interaction, (ADD, self.tournament_id), self.view, self.tournament_id, outcome, ADD
        )


class GuestButton(discord.ui.Button):
    def __init__(self, tournament_id: int) -> None:
        super().__init__(label=GUEST_LABEL, style=discord.ButtonStyle.secondary, row=0)
        self.tournament_id = int(tournament_id)

    async def callback(self, interaction: discord.Interaction) -> None:
        await form_opened(interaction, GuestModal(self.tournament_id, self.view))


class GuestModal(AnswersErrors, discord.ui.Modal, title=GUEST_TITLE):
    name = discord.ui.TextInput(label=GUEST_NAME, max_length=moves_.NAME_LIMIT)

    def __init__(self, tournament_id: int, previous: Any = None) -> None:
        super().__init__()
        self.tournament_id = int(tournament_id)
        self.previous = previous

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not await opened(interaction, staff=False):
            return
        outcome = await people_.add_entrant(
            interaction.client,
            interaction.guild,
            interaction.user,
            self.tournament_id,
            name=self.name.value,
        )
        await landed(
            interaction, (ADD, self.tournament_id), self.previous, self.tournament_id, outcome, ADD
        )


__all__ = [
    "BracketPanel",
    "build_add",
    "build_entrant",
    "build_home",
    "build_set",
    "build_tournament",
    "entrant_moves",
    "legal_to_moves",
    "member_moves",
    "open_panel",
    "render",
    "seed_order",
    "set_moves_for",
]
