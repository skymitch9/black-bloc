"""A tournament as both doors read it: the row, entrants, sets, standings, who waits on what."""

from __future__ import annotations

from typing import Any

from . import brackets_store as store_
from .brackets import play, standings
from .brackets.model import ELIMINATION

SUMMARY_FIELDS = (
    "name",
    "game",
    "format",
    "state",
    "starts_at",
    "created_at",
    "updated_at",
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


def set_row(match: Any, names: dict[int, str], confirm_minutes: int) -> dict[str, Any]:
    due = play.confirms_at(match, confirm_minutes)
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
    }


def standing_rows(bracket: Any, names: dict[int, str]) -> list[dict[str, Any]]:
    if bracket is None:
        return []
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
        }
        for row in standings.table(bracket)
    ]


def waiting_rows(bracket: Any, names: dict[int, str]) -> list[dict[str, Any]]:
    if bracket is None:
        return []
    return [
        {"entrant": entrant, "name": names.get(entrant), **found}
        for entrant, found in standings.waiting_on(bracket).items()
    ]


async def full(db: Any, row: Any, *, viewer: int | None = None, runs: bool = False) -> dict:
    people = await store_.entrants(db, row["id"])
    bracket = await store_.bracket(db, row)
    names = {one["id"]: one["name"] for one in people}
    mine = next((one["id"] for one in people if viewer and one["user_id"] == viewer), None)
    found = {
        "id": row["id"],
        **{name: row[name] for name in SUMMARY_FIELDS},
        **{name: row[name] for name in TIME_FIELDS},
        **{name: as_id(row[name]) for name in ID_FIELDS},
        "options": options(row),
        "entrant_count": sum(1 for one in people if not one["dropped"]),
        "finished": bool(bracket is not None and play.finished(bracket)),
        "may_run": runs,
        "mine": mine,
        "entrants": [entrant_row(one) for one in people],
        "sets": [
            set_row(match, names, row["confirm_minutes"])
            for match in (bracket.ordered() if bracket else [])
        ],
        "standings": standing_rows(bracket, names),
        "waiting_on": waiting_rows(bracket, names),
    }
    return found
