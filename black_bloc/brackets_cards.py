"""What a tournament's thread shows: the starter card, each set's card, and their buttons."""

from __future__ import annotations

import re
from typing import Any

import discord

from . import brackets_store as store_
from .brackets import play, pools
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
from .sports.model import SOURCE_NAMES

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
VOTE_A = "vote_a"
VOTE_B = "vote_b"
PICK_A = "pick_a"
PICK_B = "pick_b"
CLOSE_VOTE = "close_vote"
EDIT_SET = "edit_set"
RELEASE = "release"
PLAYER_ACTIONS = (REPORT, CONFIRM, DISPUTE)
VOTE_ACTIONS = (VOTE_A, VOTE_B)
TO_ACTIONS = (CALL, DECIDE, RESET)
LIST_TO_ACTIONS = (PICK_A, PICK_B, CLOSE_VOTE)
SPORTS_TO_ACTIONS = (EDIT_SET, RELEASE)
SET_ACTIONS = (
    *PLAYER_ACTIONS,
    *TO_ACTIONS,
    *VOTE_ACTIONS,
    *LIST_TO_ACTIONS,
    *SPORTS_TO_ACTIONS,
)

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
PICK_LABEL = "{name} wins…"
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
    VOTE_A: discord.ButtonStyle.primary,
    VOTE_B: discord.ButtonStyle.primary,
    PICK_A: discord.ButtonStyle.secondary,
    PICK_B: discord.ButtonStyle.secondary,
    CLOSE_VOTE: discord.ButtonStyle.secondary,
    EDIT_SET: discord.ButtonStyle.secondary,
    RELEASE: discord.ButtonStyle.secondary,
}
SPORTS_LABEL_KEYS = {
    EDIT_SET: "brackets_edit_set_label",
    RELEASE: "brackets_release_hold_label",
}
LEAGUE_KEY = "brackets_league_{league}_words"
KIND_KEYS = {
    store_.FIGHTERS: "brackets_kind_fighters_words",
    store_.SPORTS: "brackets_kind_sports_words",
    store_.LIST: "brackets_kind_list_words",
}
DECIDE_KEYS = {
    store_.VOTES: "brackets_decide_votes_words",
    store_.ORGANISER: "brackets_decide_organiser_words",
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


def list_line(store: Any, guild_id: int, row: Any) -> str:
    found = [
        words(store, guild_id, KIND_KEYS[store_.LIST]),
        words(store, guild_id, FORMAT_KEYS.get(row["format"], FORMAT_KEYS[SINGLE])),
    ]
    decide = DECIDE_KEYS.get(store_.column(row, "decide_by"))
    if decide:
        found.append(words(store, guild_id, decide))
    if row["format"] == DOUBLE and row["grand_final_reset"]:
        found.append(words(store, guild_id, "brackets_card_reset_words"))
    if row["format"] == SINGLE and row["third_place"]:
        found.append(words(store, guild_id, "brackets_card_third_words"))
    return " · ".join(part for part in found if part)


def format_line(store: Any, guild_id: int, row: Any) -> str:
    gid = guild_id
    if store_.kind_of(row) == store_.LIST:
        return list_line(store, gid, row)
    if store_.is_sports(row):
        return " · ".join(
            words(store, gid, key) for key in (KIND_KEYS[store_.SPORTS], FORMAT_KEYS[SINGLE])
        )
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
        top = [named.get(entrant, "—") for entrant in pools.leaders(one, bracket.plan.advance)]
        found.append(
            words(
                store,
                guild_id,
                "brackets_card_pool_line",
                pool=pools.letter(number),
                top=", ".join(top),
            )
        )
    return found


def league_line(store: Any, guild_id: int, row: Any) -> str | None:
    league = store_.column(row, "league")
    if not store_.is_sports(row) or not league:
        return None
    found = [words(store, guild_id, LEAGUE_KEY.format(league=league))]
    if store_.column(row, "season"):
        found.append(str(row["season"]))
    return " · ".join(part for part in found if part)


def feed_line(store: Any, guild_id: int, row: Any, *, discord_time: bool = True) -> str | None:
    """Where a sports bracket's results come from: the feed and when it last answered, the
    feed down since when, or by hand."""
    if not store_.is_sports(row):
        return None
    if not store_.fed(row):
        return words(store, guild_id, "brackets_source_own_words")
    if store_.column(row, "feed_failed_at"):
        when = when_words(row["feed_failed_at"]) if discord_time else row["feed_failed_at"]
        return words(store, guild_id, "brackets_feed_down_line", when=when or "")
    if not store_.column(row, "feed_ok_at"):
        return None
    ago = when_words(row["feed_ok_at"], "R") if discord_time else row["feed_ok_at"]
    source = SOURCE_NAMES.get(row["source"], str(row["source"]))
    return words(store, guild_id, "brackets_feed_via_line", source=source, ago=ago or "")


def score_line(store: Any, guild_id: int, match: Any, meta: Any) -> str | None:
    """A sports set's line: Final a–b, the period and the score while live, else its time."""
    meta = meta or {}
    a_score = "–" if match.score_a is None else match.score_a
    b_score = "–" if match.score_b is None else match.score_b
    if match.state == COMPLETE and match.score_a is not None:
        return words(store, guild_id, "brackets_score_final_line", a_score=a_score, b_score=b_score)
    if meta.get("live_status") == "live":
        return words(
            store,
            guild_id,
            "brackets_score_live_line",
            period=meta.get("period_words") or "",
            a_score=a_score,
            b_score=b_score,
        ).strip(" ·")
    starts = when_words(meta.get("scheduled_at"))
    if starts:
        return words(store, guild_id, "brackets_score_scheduled_line", when=starts)
    return None


def sports_embed(
    store: Any, guild_id: int, match: Any, people: dict[int, Any], meta: Any
) -> discord.Embed:
    gid = guild_id
    lines = [one for one in (score_line(store, gid, match, meta),) if one]
    if match.state == COMPLETE:
        lines.append(result_words(store, gid, match, people))
    if (meta or {}).get("held"):
        lines.append(words(store, gid, "brackets_held_note"))
    return discord.Embed(
        title=words(
            store,
            gid,
            "brackets_set_card_title",
            set=match.key,
            round=round_words(store, gid, match),
        )[:TITLE_LIMIT],
        description="\n".join(lines)[:4000] or None,
    )


def sports_moves(row: Any, match: Any, meta: Any = None) -> tuple[str, ...]:
    """A sports set: no player buttons; the organiser's pick, reset, edit and release."""
    if row["state"] != store_.RUNNING or match.state not in (*OPEN_CARD, COMPLETE):
        return ()
    found = [PICK_A, PICK_B]
    if match.state != READY:
        found.append(RESET)
    found.append(EDIT_SET)
    if (meta or {}).get("held"):
        found.append(RELEASE)
    return tuple(found)


def starter_lines(
    store: Any, guild_id: int, row: Any, people: list[Any], bracket: Any = None
) -> list[str]:
    gid = guild_id
    count = sum(1 for one in people if not one["dropped"])
    lines = [str(row["game"])] if row["game"] else []
    lines.append(format_line(store, gid, row))
    lines += [one for one in (league_line(store, gid, row), feed_line(store, gid, row)) if one]
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
    if match.score_a is None and not match.forfeit and match.winner is not None:
        result = words(store, guild_id, "brackets_no_score_words")
    elif match.score_a is None or match.forfeit:
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


def vote_lines(
    store: Any, guild_id: int, match: Any, people: dict[int, Any], ballot: Any, visible: bool
) -> list[str]:
    """A voted list set: the counts (or how many voted) while open, tied, or the result."""
    counts = {
        "a": name_of(people, match.slot_a),
        "b": name_of(people, match.slot_b),
        "votes_a": ballot["a"],
        "votes_b": ballot["b"],
    }
    if match.state in store_.VOTE_OPEN and not ballot["closed_at"]:
        closes = when_words(ballot["closes_at"], "R") or ""
        if visible:
            return [words(store, guild_id, "brackets_vote_open_line", closes=closes, **counts)]
        total = ballot["a"] + ballot["b"]
        return [words(store, guild_id, "brackets_vote_hidden_line", count=total, closes=closes)]
    if match.state == REPORTED:
        return [words(store, guild_id, "brackets_vote_tied_line", **counts)]
    if match.state == COMPLETE:
        return [
            result_words(store, guild_id, match, people),
            words(store, guild_id, "brackets_vote_closed_line", **counts),
        ]
    return status_line(store, guild_id, match, people, 0)


def set_embed(
    store: Any,
    guild_id: int,
    match: Any,
    people: dict[int, Any],
    confirm_minutes: int,
    *,
    listed: bool = False,
    ballot: Any = None,
    visible: bool = True,
) -> discord.Embed:
    """A list set (`listed`) has no best-of; a voted one (`ballot`) reads its vote."""
    gid = guild_id
    head = [] if listed else [words(store, gid, "brackets_set_card_best_of", best_of=match.best_of)]
    if match.rematch:
        head.append(words(store, gid, "brackets_set_card_rematch"))
    if ballot is not None:
        status = vote_lines(store, gid, match, people, ballot, visible)
    elif listed and match.state == COMPLETE:
        status = [result_words(store, gid, match, people)]
    else:
        status = status_line(store, gid, match, people, confirm_minutes)
    lines = [" · ".join(head), *status] if head else status
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
            row=0 if action in (*PLAYER_ACTIONS, *VOTE_ACTIONS) else 1,
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


def list_moves(row: Any, match: Any, ballot: Any = None) -> tuple[str, ...]:
    """A list set: the two vote buttons while its vote is open, the organiser's picks always."""
    if row["state"] != store_.RUNNING or match.state not in (*OPEN_CARD, COMPLETE):
        return ()
    voting = ballot is not None and match.state in store_.VOTE_OPEN and not ballot["closed_at"]
    found = [VOTE_A, VOTE_B] if voting else []
    found += [PICK_A, PICK_B]
    if voting:
        found.append(CLOSE_VOTE)
    if match.state not in (READY,):
        found.append(RESET)
    return tuple(found)


def list_label(store: Any, guild_id: int, action: str, match: Any, people: dict) -> str:
    if action in VOTE_ACTIONS:
        return name_of(people, match.slot(action[-1]))[:LABEL_LIMIT] or "—"
    if action in (PICK_A, PICK_B):
        return PICK_LABEL.format(name=name_of(people, match.slot(action[-1])))[:LABEL_LIMIT]
    if action == CLOSE_VOTE:
        return words(store, guild_id, "brackets_close_vote_label")[:LABEL_LIMIT] or action
    if action in SPORTS_LABEL_KEYS:
        return words(store, guild_id, SPORTS_LABEL_KEYS[action])[:LABEL_LIMIT] or action
    return label(store, guild_id, action)


def set_view(
    store: Any,
    guild_id: int,
    row: Any,
    match: Any,
    *,
    people: dict | None = None,
    ballot: Any = None,
) -> discord.ui.View:
    view = discord.ui.View(timeout=None)
    if store_.is_sports(row):
        for action in sports_moves(row, match, ballot):
            text = list_label(store, guild_id, action, match, people or {})
            view.add_item(SetButton(row["id"], match.key, action, text))
        return view
    if store_.kind_of(row) == store_.LIST:
        for action in list_moves(row, match, ballot):
            text = list_label(store, guild_id, action, match, people or {})
            view.add_item(SetButton(row["id"], match.key, action, text))
        return view
    for action in set_moves(row["state"], match.state, match.pool):
        view.add_item(SetButton(row["id"], match.key, action, label(store, guild_id, action)))
    return view


def carries(message: Any, prefix: str) -> bool:
    """Whether a posted message is the card whose buttons start with this custom-id prefix."""
    return any(one.startswith(prefix) for one in custom_ids(message))


__all__ = [
    "EDIT_SET",
    "RELEASE",
    "feed_line",
    "league_line",
    "score_line",
    "sports_embed",
    "sports_moves",
    "CALL",
    "CHECK_IN",
    "CLOSE_VOTE",
    "PICK_A",
    "PICK_B",
    "VOTE_A",
    "VOTE_B",
    "list_label",
    "list_moves",
    "vote_lines",
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
