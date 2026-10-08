"""A tournament as both doors read it: the row, entrants, sets, standings, who waits on what."""

from __future__ import annotations

from typing import Any

from . import brackets_store as store_
from .brackets import play, pools, standings, swiss
from .brackets.model import ELIMINATION, FINAL, POOLS, SWISS
from .settings_store import BRACKETS_DEFAULTS

PAGE_WORDS = (
    "brackets_state_draft",
    "brackets_state_signups",
    "brackets_state_check_in",
    "brackets_state_seeding",
    "brackets_state_running",
    "brackets_state_complete",
    "brackets_state_cancelled",
    "brackets_format_single_words",
    "brackets_format_double_words",
    "brackets_format_round_robin_words",
    "brackets_format_swiss_words",
    "brackets_sign_up_label",
    "brackets_leave_label",
    "brackets_check_in_label",
    "brackets_drop_label",
    "brackets_drop_confirm",
    "brackets_report_label",
    "brackets_confirm_label",
    "brackets_dispute_label",
    "brackets_report_title",
    "brackets_dispute_title",
    "brackets_dispute_note_label",
    "brackets_round_winners",
    "brackets_round_losers",
    "brackets_round_grand",
    "brackets_round_reset",
    "brackets_round_third",
    "brackets_round_plain",
    "brackets_set_card_best_of",
    "brackets_set_card_rematch",
    "brackets_set_card_ready",
    "brackets_set_card_called",
    "brackets_set_card_reported",
    "brackets_set_card_disputed",
    "brackets_forfeit_words",
    "brackets_your_sets_title",
    "brackets_waiting_play",
    "brackets_waiting_called",
    "brackets_waiting_confirm",
    "brackets_waiting_opponent_confirms",
    "brackets_waiting_to_decides",
    "brackets_waiting_waits",
    "brackets_waiting_next_round",
    "brackets_waiting_done",
    "brackets_waiting_out",
    "brackets_discord_label",
    "brackets_card_reset_words",
    "brackets_card_third_words",
    "brackets_card_rounds_words",
    "brackets_card_late_words",
    "brackets_card_finals_words",
    "brackets_state_pools",
    "brackets_round_pool",
    "brackets_pool_title",
    "brackets_card_pools_words",
    "brackets_card_losers_words",
    "brackets_waiting_final",
    "brackets_pool_tied",
    "brackets_pool_raise_label",
)

SUMMARY_FIELDS = (
    "name",
    "game",
    "format",
    "state",
    "starts_at",
    "created_at",
    "updated_at",
    "entrant_cap",
    "pools_format",
)
OPTION_FIELDS = (
    "format",
    "third_place",
    "grand_final_reset",
    "swiss_rounds",
    "best_of",
    "best_of_from_round",
    "best_of_late",
    "best_of_finals",
    "entrant_cap",
    "check_in_minutes",
    "confirm_minutes",
    *store_.POOL_COLUMNS,
)
FLAG_FIELDS = ("third_place", "grand_final_reset")
TIME_FIELDS = (
    "rules_text",
    "check_in_opened_at",
    "check_in_closes_at",
    "started_at",
    "completed_at",
    "cancelled_at",
    "source",
    "source_ref",
)
ID_FIELDS = ("created_by", "to_user_id", "channel_id", "thread_id", "message_id")


def as_id(value: Any) -> str | None:
    return str(value) if value is not None else None


def page_words(store: Any, guild_id: int) -> dict[str, str]:
    """The player-facing words the site page draws, as staff wrote them or as shipped."""
    return {
        key: str(store.get(guild_id, key) or "").strip() or str(BRACKETS_DEFAULTS[key])
        for key in PAGE_WORDS
    }


def page_defaults(defaults: dict[str, Any]) -> dict[str, Any]:
    """A new tournament's options as the create form fills them in."""
    return {name: bool(value) if name in FLAG_FIELDS else value for name, value in defaults.items()}


def rounds_to_play(row: Any, bracket: Any, people: list[Any]) -> int | None:
    """The Swiss rounds the engine plays: the stored number, else enough for the field."""
    if row["format"] != SWISS:
        return None
    field = len(bracket.entrants) if bracket is not None else sum(
        1 for one in people if not one["dropped"] and not one["dq"]
    )
    return swiss.rounds_for(field, row["swiss_rounds"])


def summary(row: Any) -> dict[str, Any]:
    found = {"id": row["id"], **{name: row[name] for name in SUMMARY_FIELDS}}
    found["entrant_count"] = row["entrant_count"] if "entrant_count" in row.keys() else None
    found["to_user_id"] = as_id(row["to_user_id"])
    return found


def options(row: Any) -> dict[str, Any]:
    found = {name: row[name] for name in OPTION_FIELDS}
    for name in FLAG_FIELDS:
        found[name] = bool(found[name])
    return found


def entrant_row(row: Any) -> dict[str, Any]:
    return {
        "id": row["id"],
        "user_id": as_id(row["user_id"]),
        "name": row["name"],
        "guest": row["user_id"] is None,
        "seed": row["seed"],
        "checked_in": bool(row["checked_in"]),
        "dropped": bool(row["dropped"]),
        "dropped_why": row["dropped_why"],
        "dq": bool(row["dq"]),
        "placement": row["placement"],
        "final_rank": row["final_rank"],
    }


def set_row(
    match: Any, names: dict[int, str], confirm_minutes: int, card: tuple | None = None
) -> dict[str, Any]:
    due = play.confirms_at(match, confirm_minutes)
    message_id, card_at = card or (None, None)
    return {
        "key": match.key,
        "side": match.side,
        "round": match.round,
        "position": match.position,
        "best_of": match.best_of,
        "state": match.state,
        "slot_a": match.slot_a,
        "slot_b": match.slot_b,
        "a_name": names.get(match.slot_a),
        "b_name": names.get(match.slot_b),
        "score_a": match.score_a,
        "score_b": match.score_b,
        "winner": match.winner,
        "loser": match.loser,
        "forfeit": match.forfeit,
        "winner_to": match.winner_to,
        "loser_to": match.loser_to,
        "called_at": match.called_at,
        "reported_by": as_id(match.reported_by),
        "reported_side": match.reported_side,
        "reported_at": match.reported_at,
        "confirms_at": due.isoformat() if due else None,
        "confirmed_by": as_id(match.confirmed_by),
        "confirmed_how": match.confirmed_how,
        "disputed_by": as_id(match.disputed_by),
        "dispute_note": match.dispute_note,
        "placement_winner": match.placement_winner,
        "placement_loser": match.placement_loser,
        "rematch": bool(match.rematch),
        "phase": match.phase,
        "pool": match.pool,
        "message_id": as_id(message_id),
        "card_at": card_at,
    }


def placed_rows(placed: dict[int, int], entrants: list[int], names: dict) -> list[dict]:
    return [
        {"entrant": entrant, "name": names.get(entrant), "place": placed.get(entrant)}
        for entrant in sorted(entrants, key=lambda one: placed.get(one) or 10**6)
    ]


def standing_rows(bracket: Any, names: dict[int, str]) -> list[dict[str, Any]]:
    if bracket is None:
        return []
    if bracket.plan is not None:
        return placed_rows(pools.placements(bracket), bracket.entrants, names)
    if bracket.format in ELIMINATION:
        placed = standings.placements(bracket)
        return [
            {"entrant": entrant, "name": names.get(entrant), "place": placed.get(entrant)}
            for entrant in sorted(bracket.entrants, key=lambda one: placed.get(one) or 10**6)
        ]
    finished = play.finished(bracket)
    return [
        {
            "entrant": row.entrant,
            "name": names.get(row.entrant),
            "place": row.place if finished else None,
            "rank": row.place,
            "set_wins": row.record.set_wins,
            "set_losses": row.record.set_losses,
            "game_wins": row.record.game_wins,
            "game_losses": row.record.game_losses,
            "byes": row.record.byes,
            "opponents_rate": row.opponents_rate,
            "withdrawn": row.entrant in bracket.withdrawn,
        }
        for row in standings.table(bracket)
    ]


def waiting_rows(bracket: Any, names: dict[int, str]) -> list[dict[str, Any]]:
    if bracket is None:
        return []
    return [
        {"entrant": entrant, "name": names.get(entrant), **found}
        for entrant, found in pools.waiting_on(bracket).items()
    ]


def phase_of(bracket: Any) -> str | None:
    if bracket is None or bracket.plan is None:
        return None
    return FINAL if pools.final_part(bracket) is not None else POOLS


def pool_rows(
    bracket: Any, names: dict[int, str], confirm_minutes: int, held: dict
) -> list[dict[str, Any]]:
    """Each pool: who is in it, its sets, its table, where the line falls and who goes through."""
    if bracket is None or bracket.plan is None:
        return []
    plan = bracket.plan
    final = pools.final_part(bracket)
    through = set(final.entrants) if final is not None else set()
    found = []
    for number, one in enumerate(pools.pool_parts(bracket), start=1):
        finished = play.finished(one)
        tie = pools.tie_of(one, plan.advance, number)
        if tie:
            going = [] if finished else pools.leaders(one, plan.advance)
        else:
            going = pools.cut(one, plan.advance, number)
        sets = [
            set_row(match, names, confirm_minutes, held.get(pools.prefixed(number, match.key)))
            | {"key": pools.prefixed(number, match.key), "phase": POOLS, "pool": number}
            for match in one.ordered()
        ]
        found.append(
            {
                "pool": number,
                "letter": pools.letter(number),
                "entrants": list(one.entrants),
                "sets": sets,
                "standings": standing_rows(one, names),
                "finished": finished,
                "cut": plan.advance,
                "advancing": [e for e in going if not through or e in through],
                "tied": tie if finished else [],
                "rounds_to_play": (
                    swiss.rounds_for(len(one.entrants), plan.swiss_rounds)
                    if plan.format == SWISS
                    else None
                ),
            }
        )
    return found


async def full(db: Any, row: Any, *, viewer: int | None = None, runs: bool = False) -> dict:
    people = await store_.entrants(db, row["id"])
    bracket = await store_.bracket(db, row)
    held = await store_.cards(db, row["id"]) if bracket is not None else {}
    names = {one["id"]: one["name"] for one in people}
    mine = next((one["id"] for one in people if viewer and one["user_id"] == viewer), None)
    found = {
        "id": row["id"],
        **{name: row[name] for name in SUMMARY_FIELDS},
        **{name: row[name] for name in TIME_FIELDS},
        **{name: as_id(row[name]) for name in ID_FIELDS},
        "shadow": bool(row["shadow"]),
        "options": options(row),
        "entrant_count": sum(1 for one in people if not one["dropped"]),
        "finished": bool(bracket is not None and pools.finished(bracket)),
        "phase": phase_of(bracket),
        "pools_finished": bool(bracket is not None and pools.pools_finished(bracket)),
        "rounds_to_play": rounds_to_play(row, bracket, people),
        "may_run": runs,
        "mine": mine,
        "entrants": [entrant_row(one) for one in people],
        "sets": [
            set_row(match, names, row["confirm_minutes"], held.get(match.key))
            for match in (bracket.ordered() if bracket else [])
            if match.phase != POOLS
        ],
        "pools": pool_rows(bracket, names, row["confirm_minutes"], held),
        "standings": standing_rows(bracket, names),
        "waiting_on": waiting_rows(bracket, names),
    }
    return found
