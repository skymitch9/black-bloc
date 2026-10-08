"""What a tournament's thread shows: the starter card, each set's card, and their buttons."""

from __future__ import annotations

import re
from typing import Any

import discord

from . import brackets_store as store_
from .brackets import play, pools, standings
from .brackets.model import (
    BYE,
    CALLED,
    COMPLETE,
    DISPUTED,
    DOUBLE,
    ELIMINATION,
    GRAND,
    LOSERS,
    READY,
    REPORTED,
    SINGLE,
    SWISS,
    THIRD,
    VOID,
    WAITING,
    WINNERS,
)
from .brackets_moves import said
from .command_errors import SafeDynamicItem
from .settings_store import BRACKETS_CHANNEL
from .shadow import note_line

JOIN = "join"
LEAVE = "leave"
CHECK_IN = "check_in"
STARTER_ACTIONS = (JOIN, LEAVE, CHECK_IN)

REPORT = "report"
CONFIRM = "confirm"
DISPUTE = "dispute"
CALL = "call"
DECIDE = "decide"
RESET = "reset"
PLAYER_ACTIONS = (REPORT, CONFIRM, DISPUTE)
TO_ACTIONS = (CALL, DECIDE, RESET)
SET_ACTIONS = (*PLAYER_ACTIONS, *TO_ACTIONS)

PREFIX = "brackets"
KEY_PATTERN = r"(?:[A-Z]\.)?[A-Z][0-9]+-[0-9]+"
STARTER_TEMPLATE = rf"{PREFIX}:(?P<tid>[0-9]+):(?P<action>{'|'.join(STARTER_ACTIONS)})"
SET_TEMPLATE = (
    rf"{PREFIX}:(?P<tid>[0-9]+):(?P<key>{KEY_PATTERN}):(?P<action>{'|'.join(SET_ACTIONS)})"
)

OPEN_CARD = (READY, CALLED, REPORTED, DISPUTED)
CLEARED = (WAITING, BYE, VOID)
PLACINGS_SHOWN = 8
NAME_LIMIT = 100
LABEL_LIMIT = 80
TITLE_LIMIT = 256

STARTER_MOVES: dict[str, tuple[str, ...]] = {
    store_.DRAFT: (LEAVE,),
    store_.SIGNUPS: (JOIN, LEAVE),
    store_.CHECK_IN: (CHECK_IN, LEAVE),
    store_.SEEDING: (LEAVE,),
}
SET_MOVES: dict[str, tuple[str, ...]] = {
    READY: (REPORT, CALL, DECIDE),
    CALLED: (REPORT, DECIDE, RESET),
    REPORTED: (CONFIRM, DISPUTE, DECIDE, RESET),
    DISPUTED: (DECIDE, RESET),
    COMPLETE: (DECIDE, RESET),
}
LABEL_KEYS = {
    JOIN: "brackets_sign_up_label",
    LEAVE: "brackets_leave_label",
    CHECK_IN: "brackets_check_in_label",
    REPORT: "brackets_report_label",
    CONFIRM: "brackets_confirm_label",
    DISPUTE: "brackets_dispute_label",
}
TO_LABELS = {CALL: "Call", DECIDE: "Decide…", RESET: "Reset…"}
STYLES = {
    JOIN: discord.ButtonStyle.success,
    LEAVE: discord.ButtonStyle.secondary,
    CHECK_IN: discord.ButtonStyle.primary,
    REPORT: discord.ButtonStyle.primary,
    CONFIRM: discord.ButtonStyle.success,
    DISPUTE: discord.ButtonStyle.danger,
    CALL: discord.ButtonStyle.secondary,
    DECIDE: discord.ButtonStyle.secondary,
    RESET: discord.ButtonStyle.secondary,
}
FORMAT_KEYS = {
    SINGLE: "brackets_format_single_words",
    DOUBLE: "brackets_format_double_words",
    "round_robin": "brackets_format_round_robin_words",
    SWISS: "brackets_format_swiss_words",
}
SITE_PAGE = "brackets.html"


def words(store: Any, guild_id: int, key: str, **fields: Any) -> str:
    return said(store, guild_id, key, **fields)


def label(store: Any, guild_id: int, action: str) -> str:
    if action in TO_LABELS:
        return TO_LABELS[action]
    return words(store, guild_id, LABEL_KEYS[action])[:LABEL_LIMIT] or action


def starter_custom_id(tournament_id: int, action: str) -> str:
    return f"{PREFIX}:{int(tournament_id)}:{action}"


def set_custom_id(tournament_id: int, key: str, action: str) -> str:
    return f"{PREFIX}:{int(tournament_id)}:{key}:{action}"


def set_prefix(tournament_id: int, key: str) -> str:
    return f"{PREFIX}:{int(tournament_id)}:{key}:"


def starter_moves(state: str, entrants: int = 1) -> tuple[str, ...]:
    """Leave wherever it is legal (before the start) while someone is in to press it."""
    return tuple(one for one in STARTER_MOVES.get(state, ()) if one != LEAVE or entrants > 0)


def custom_ids(message: Any) -> list[str]:
    return [
        str(getattr(child, "custom_id", "") or "")
        for row in getattr(message, "components", None) or ()
        for child in getattr(row, "children", None) or ()
    ]


def is_starter_id(custom_id: str, tournament_id: int) -> bool:
    found = re.fullmatch(STARTER_TEMPLATE, custom_id)
    return found is not None and int(found["tid"]) == int(tournament_id)


def is_set_id(custom_id: str, tournament_id: int) -> bool:
    found = re.fullmatch(SET_TEMPLATE, custom_id)
    return found is not None and int(found["tid"]) == int(tournament_id)


def embeds_of(message: Any) -> list[Any]:
    found = getattr(message, "embeds", None)
    if found is None:
        one = getattr(message, "embed", None)
        found = [one] if one is not None else []
    return list(found)


def set_moves(tournament_state: str, set_state: str, pool: int | None = None) -> tuple[str, ...]:
    """A pool set's card goes quiet once the final is built; Back to pools wakes it."""
    if tournament_state not in store_.PLAYING:
        return ()
    if pool and tournament_state == store_.RUNNING:
        return ()
    return SET_MOVES.get(set_state, ())


def mention(person: Any) -> str:
    if person is None:
        return "—"
    if person["user_id"] is not None:
        return f"<@{int(person['user_id'])}>"
    return str(person["name"])


def name_of(people: dict[int, Any], entrant: int | None) -> str:
    found = people.get(entrant) if entrant is not None else None
    return str(found["name"]) if found is not None else "—"


def site_url(origin: Any, tournament_id: int) -> str | None:
    text = str(origin or "").strip()
    if not text:
        return None
    return f"{text.rstrip('/')}/{SITE_PAGE}#{int(tournament_id)}"


def capitalised(text: str) -> str:
    return text[:1].upper() + text[1:]


def state_words(store: Any, guild_id: int, state: str) -> str:
    return words(store, guild_id, f"brackets_state_{state}")


def format_line(store: Any, guild_id: int, row: Any) -> str:
    gid = guild_id
    found = [
        words(
            store,
            gid,
            "brackets_card_format_line",
            format=words(store, gid, FORMAT_KEYS.get(row["format"], FORMAT_KEYS[DOUBLE])),
            best_of=row["best_of"],
        )
    ]
    if row["format"] == DOUBLE and row["grand_final_reset"]:
        found.append(words(store, gid, "brackets_card_reset_words"))
    if row["format"] == SINGLE and row["third_place"]:
        found.append(words(store, gid, "brackets_card_third_words"))
    if row["format"] == SWISS and row["swiss_rounds"]:
        found.append(words(store, gid, "brackets_card_rounds_words", rounds=row["swiss_rounds"]))
    if row["pools_format"] in pools.POOL_FORMATS:
        found.append(
            words(
                store,
                gid,
                "brackets_card_pools_words",
                count=row["pool_count"],
                format=words(store, gid, FORMAT_KEYS[row["pools_format"]]),
                advance=row["advance_per_pool"],
            )
        )
        if row["format"] == DOUBLE and row["advance_losers_from"]:
            found.append(
                words(store, gid, "brackets_card_losers_words", place=row["advance_losers_from"])
            )
    if row["format"] in ELIMINATION:
        if row["best_of_from_round"]:
            found.append(
                words(
                    store,
                    gid,
                    "brackets_card_late_words",
                    best_of=row["best_of_late"],
                    top=row["best_of_from_round"],
                )
            )
        if row["best_of_finals"] != row["best_of"]:
            found.append(
                words(store, gid, "brackets_card_finals_words", best_of=row["best_of_finals"])
            )
    return " · ".join(part for part in found if part)


def when_words(stamp: Any, style: str = "f") -> str | None:
    found = play.parsed(stamp) if stamp else None
    return f"<t:{int(found.timestamp())}:{style}>" if found is not None else None


def pool_lines(store: Any, guild_id: int, bracket: Any, people: list[Any]) -> list[str]:
    """Each pool's leaders while the pools play: as many names as go through."""
    if bracket is None or bracket.plan is None:
        return []
    named = {one["id"]: one["name"] for one in people}
    found = []
    for number, one in enumerate(pools.pool_parts(bracket), start=1):
        top = [named.get(row.entrant, "—") for row in standings.table(one)]
        found.append(
            words(
                store,
                guild_id,
                "brackets_card_pool_line",
                pool=pools.letter(number),
                top=", ".join(top[: bracket.plan.advance]),
            )
        )
    return found


def starter_lines(
    store: Any, guild_id: int, row: Any, people: list[Any], bracket: Any = None
) -> list[str]:
    gid = guild_id
    count = sum(1 for one in people if not one["dropped"])
    lines = [str(row["game"])] if row["game"] else []
    lines.append(format_line(store, gid, row))
    state = capitalised(state_words(store, gid, row["state"]))
    lines.append(words(store, gid, "brackets_card_state_line", state=state))
    if row["entrant_cap"]:
        lines.append(
            words(
                store, gid, "brackets_card_entrants_cap_line", count=count, cap=row["entrant_cap"]
            )
        )
    else:
        lines.append(words(store, gid, "brackets_card_entrants_line", count=count))
    starts = when_words(row["starts_at"])
    if starts and row["state"] in store_.BEFORE_START:
        lines.append(words(store, gid, "brackets_card_starts_line", when=starts))
    closes = when_words(row["check_in_closes_at"], "R")
    if closes and row["state"] == store_.CHECK_IN:
        lines.append(words(store, gid, "brackets_card_check_in_line", when=closes))
    if row["to_user_id"]:
        lines.append(words(store, gid, "brackets_card_to_line", to=f"<@{int(row['to_user_id'])}>"))
    if row["state"] == store_.POOLS:
        lines.extend(pool_lines(store, gid, bracket, people))
    if row["state"] == store_.COMPLETE:
        placed = sorted(
            (one for one in people if one["placement"] is not None),
            key=lambda one: (one["placement"], one["seed"] or 0),
        )
        lines.extend(
            words(store, gid, "brackets_card_place_line", place=one["placement"], name=one["name"])
            for one in placed[:PLACINGS_SHOWN]
        )
    return lines


def starter_embed(
    store: Any, guild_id: int, row: Any, people: list[Any], bracket: Any = None
) -> discord.Embed:
    return discord.Embed(
        title=str(row["name"])[:TITLE_LIMIT],
        description="\n".join(starter_lines(store, guild_id, row, people, bracket))[:4000],
    )


def rehearsal_line(bot: Any, guild: Any, row: Any) -> str | None:
    if not row["shadow"]:
        return None
    real = bot.store.get(guild.id, BRACKETS_CHANNEL)
    return note_line(bot, guild, f"<#{int(real)}>" if real else "#?") or None


def round_words(store: Any, guild_id: int, match: Any) -> str:
    if match.pool:
        return words(
            store,
            guild_id,
            "brackets_round_pool",
            pool=pools.letter(match.pool),
            round=match.round,
        )
    if match.side == WINNERS:
        return words(store, guild_id, "brackets_round_winners", round=match.round)
    if match.side == LOSERS:
        return words(store, guild_id, "brackets_round_losers", round=match.round)
    if match.side == GRAND:
        key = "brackets_round_reset" if match.round > 1 else "brackets_round_grand"
        return words(store, guild_id, key)
    if match.side == THIRD:
        return words(store, guild_id, "brackets_round_third")
    return words(store, guild_id, "brackets_round_plain", round=match.round)


def result_words(store: Any, guild_id: int, match: Any, people: dict[int, Any]) -> str:
    if match.score_a is None or match.forfeit:
        result = words(store, guild_id, "brackets_forfeit_words")
    else:
        result = f"{max(match.score_a, match.score_b)}–{min(match.score_a, match.score_b)}"
    return words(
        store,
        guild_id,
        "brackets_set_final_said",
        set=match.key,
        winner=name_of(people, match.winner),
        result=result,
    )


def status_line(
    store: Any, guild_id: int, match: Any, people: dict[int, Any], confirm_minutes: int
) -> list[str]:
    gid = guild_id
    if match.state == READY:
        return [words(store, gid, "brackets_set_card_ready")]
    if match.state == CALLED:
        return [words(store, gid, "brackets_set_card_called")]
    if match.state == REPORTED:
        side = match.reported_side or "a"
        due = play.confirms_at(match, confirm_minutes)
        return [
            words(
                store,
                gid,
                "brackets_set_card_reported",
                reporter=name_of(people, match.slot(side)),
                score=f"{match.score_a}–{match.score_b}",
                opponent=name_of(people, match.slot("b" if side == "a" else "a")),
                when=f"<t:{int(due.timestamp())}:R>" if due else "",
            )
        ]
    if match.state == DISPUTED:
        who = next(
            (
                one["name"]
                for one in people.values()
                if one["user_id"] is not None and one["user_id"] == match.disputed_by
            ),
            "—",
        )
        found = [words(store, gid, "brackets_set_card_disputed", who=who)]
        if match.dispute_note:
            found.append(words(store, gid, "brackets_set_card_note", note=match.dispute_note))
        return found
    if match.state == COMPLETE:
        return [result_words(store, gid, match, people)]
    return [words(store, gid, "brackets_set_card_cleared", set=match.key)]


def set_embed(
    store: Any, guild_id: int, match: Any, people: dict[int, Any], confirm_minutes: int
) -> discord.Embed:
    gid = guild_id
    head = [words(store, gid, "brackets_set_card_best_of", best_of=match.best_of)]
    if match.rematch:
        head.append(words(store, gid, "brackets_set_card_rematch"))
    lines = [" · ".join(head), *status_line(store, gid, match, people, confirm_minutes)]
    return discord.Embed(
        title=words(
            store,
            gid,
            "brackets_set_card_title",
            set=match.key,
            round=round_words(store, gid, match),
        )[:TITLE_LIMIT],
        description="\n".join(lines)[:4000],
    )


def players_line(store: Any, guild_id: int, match: Any, people: dict[int, Any]) -> str:
    return words(
        store,
        guild_id,
        "brackets_set_card_players",
        a=mention(people.get(match.slot_a)),
        b=mention(people.get(match.slot_b)),
    )


def cleared_embed(store: Any, guild_id: int, key: str) -> discord.Embed:
    return discord.Embed(description=words(store, guild_id, "brackets_set_card_cleared", set=key))


def player_ids(match: Any, people: dict[int, Any]) -> list[int]:
    found: list[int] = []
    for entrant in (match.slot_a, match.slot_b):
        person = people.get(entrant) if entrant is not None else None
        if person is not None and person["user_id"] is not None:
            found.append(int(person["user_id"]))
    return found


def winner_ids(match: Any, people: dict[int, Any]) -> list[int]:
    person = people.get(match.winner) if match.winner is not None else None
    return [int(person["user_id"])] if person is not None and person["user_id"] is not None else []


def ping_mentions(user_ids: list[int], *, rehearsal: bool) -> discord.AllowedMentions:
    if rehearsal or not user_ids:
        return discord.AllowedMentions.none()
    return discord.AllowedMentions(
        everyone=False, roles=False, users=[discord.Object(id=one) for one in user_ids]
    )


class StarterButton(
    SafeDynamicItem, discord.ui.DynamicItem[discord.ui.Button], template=STARTER_TEMPLATE
):
    """A member's move on the tournament's starter card."""

    def __init__(self, tournament_id: Any, action: str, text: str = "") -> None:
        self.tournament_id = int(tournament_id)
        self.action = action
        super().__init__(
            discord.ui.Button(
                label=(text or action)[:LABEL_LIMIT],
                style=STYLES[action],
                custom_id=starter_custom_id(tournament_id, action),
            )
        )

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: Any, match: Any):
        return cls(int(match["tid"]), str(match["action"]))

    async def on_click(self, interaction: discord.Interaction) -> None:
        from .brackets_buttons import starter_pressed

        await starter_pressed(interaction, self.tournament_id, self.action)


class SetButton(SafeDynamicItem, discord.ui.DynamicItem[discord.ui.Button], template=SET_TEMPLATE):
    """A move on one set's card; who may make it is decided on the press."""

    def __init__(self, tournament_id: Any, key: str, action: str, text: str = "") -> None:
        self.tournament_id = int(tournament_id)
        self.key = str(key)
        self.action = action
        super().__init__(
            discord.ui.Button(
                label=(text or action)[:LABEL_LIMIT],
                style=STYLES[action],
                custom_id=set_custom_id(tournament_id, key, action),
            ),
            row=0 if action in PLAYER_ACTIONS else 1,
        )

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: Any, match: Any):
        return cls(int(match["tid"]), str(match["key"]), str(match["action"]))

    async def on_click(self, interaction: discord.Interaction) -> None:
        from .brackets_buttons import set_pressed

        await set_pressed(interaction, self.tournament_id, self.key, self.action)


def starter_view(
    store: Any, guild_id: int, row: Any, origin: Any = None, people: list[Any] | None = None
) -> discord.ui.View:
    view = discord.ui.View(timeout=None)
    count = 1 if people is None else sum(1 for one in people if not one["dropped"])
    for action in starter_moves(row["state"], count):
        view.add_item(StarterButton(row["id"], action, label(store, guild_id, action)))
    url = site_url(origin, row["id"])
    if url:
        view.add_item(
            discord.ui.Button(
                label=words(store, guild_id, "brackets_card_link_label")[:LABEL_LIMIT] or "Bracket",
                style=discord.ButtonStyle.link,
                url=url,
            )
        )
    return view


def set_view(store: Any, guild_id: int, row: Any, match: Any) -> discord.ui.View:
    view = discord.ui.View(timeout=None)
    for action in set_moves(row["state"], match.state, match.pool):
        view.add_item(SetButton(row["id"], match.key, action, label(store, guild_id, action)))
    return view


def carries(message: Any, prefix: str) -> bool:
    """Whether a posted message is the card whose buttons start with this custom-id prefix."""
    return any(one.startswith(prefix) for one in custom_ids(message))


__all__ = [
    "CALL",
    "CHECK_IN",
    "CLEARED",
    "CONFIRM",
    "DECIDE",
    "DISPUTE",
    "JOIN",
    "LEAVE",
    "OPEN_CARD",
    "REPORT",
    "RESET",
    "SET_TEMPLATE",
    "STARTER_TEMPLATE",
    "SetButton",
    "StarterButton",
    "carries",
    "cleared_embed",
    "custom_ids",
    "embeds_of",
    "is_set_id",
    "is_starter_id",
    "label",
    "mention",
    "name_of",
    "ping_mentions",
    "player_ids",
    "players_line",
    "rehearsal_line",
    "result_words",
    "round_words",
    "set_custom_id",
    "set_embed",
    "set_moves",
    "set_prefix",
    "set_view",
    "site_url",
    "starter_custom_id",
    "starter_embed",
    "starter_moves",
    "starter_view",
    "state_words",
    "winner_ids",
    "words",
]
