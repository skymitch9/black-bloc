from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, NamedTuple

from .golive import parse_ts
from .marathon import (
    BY_BOTH,
    BY_CATEGORY,
    BY_TITLE,
    DONE,
    DROPPED,
    LIVE,
    NAME_FLOOR,
    TITLE_REACH,
    MarathonMove,
    _cell,
    normalise,
)
from .settings_store import MARATHON_SETUP_MAX

CHAIN_SLACK = timedelta(minutes=1)
CHAIN_REACH = timedelta(minutes=MARATHON_SETUP_MAX)
LOOK_AGAIN = timedelta(minutes=30)

SHEET_TIMES = "sheet_times"
SHEET_TIMES_MOVE = MarathonMove(SHEET_TIMES, "Back to the sheet's times", row=2)
RETIMED_LINE = (
    "**Times:** {count} run(s) re-timed from the stream — this schedule does not move itself, "
    "so Black Bloc keeps the clock."
)
SHEET_TIMES_DONE = "**{name}** is back on the sheet's times ({count} run(s))."
SHEET_TIMES_NONE = "**{name}** is on the sheet's times already, so nothing was changed."
SHEET_TIMES_CODE = "not_retimed"


class Match(NamedTuple):
    row: Any
    direct: bool


@dataclass(frozen=True)
class Verdict:
    row: Any
    because: str
    title_row: Any = None
    category_row: Any = None
    disagree: bool = False


class Retime(NamedTuple):
    row: Any
    starts_at: str | None
    ends_at: str | None


def same(one: Any, other: Any) -> bool:
    if one is None or other is None:
        return False
    return one is other or _cell(one, "id") == _cell(other, "id")


def looked_up(row: Any) -> bool:
    return bool(_cell(row, "twitch_looked_at"))


def no_category(row: Any) -> bool:
    return looked_up(row) and not _cell(row, "twitch_game_id")


def lookup_names(row: Any) -> list[str]:
    found: list[str] = []
    for key in ("twitch_game", "game", "display_name"):
        name = " ".join(str(_cell(row, key) or "").split())
        if name and name.lower() not in {one.lower() for one in found}:
            found.append(name)
    return found


def found_in(row: Any, named: dict[str, Any], searched: dict[str, list[Any]]) -> Any:
    """The category Twitch has for this run: an exact name first, then a search result whose
    name is the run's own name once punctuation and capitals are set aside."""
    names = lookup_names(row)
    for name in names:
        game = named.get(name.lower())
        if game is not None:
            return game
    wanted = {normalise(name) for name in names} - {""}
    for name in names:
        for game in searched.get(name, ()):
            if normalise(getattr(game, "name", "")) in wanted:
                return game
    return None


def wants_lookup(row: Any) -> bool:
    return _cell(row, "state") not in (DONE, DROPPED) and not looked_up(row)


def _within(haystack: str, needle: str) -> bool:
    return len(needle) >= NAME_FLOOR and f" {needle} " in f" {haystack} "


def _near(row: Any, now: datetime) -> bool:
    at = parse_ts(_cell(row, "scheduled_at"))
    return at is not None and abs(at - now) <= TITLE_REACH


def category_matches(
    game_id: Any, game_name: Any, rows: Any, now: datetime, *, retro: Any
) -> list[Match]:
    """Every open run the stream's category stands for. The Retro category stands only for runs
    Twitch has no category of their own for; any other is the run's category by id, or by name
    while the run has not been looked up."""
    said_id = str(game_id or "").strip()
    said = normalise(game_name)
    if not said_id and not said:
        return []
    retro_name = normalise(retro)
    is_retro = bool(said) and bool(retro_name) and said == retro_name
    found: list[Match] = []
    for row in rows or ():
        if _cell(row, "state") in (DONE, DROPPED) or not _near(row, now):
            continue
        if is_retro:
            if no_category(row):
                found.append(Match(row, False))
            continue
        own_id = str(_cell(row, "twitch_game_id") or "").strip()
        if said_id and own_id:
            if own_id == said_id:
                found.append(Match(row, True))
            continue
        if not said:
            continue
        names = {
            normalise(_cell(row, key))
            for key in ("game", "display_name", "twitch_game", "twitch_category")
        } - {""}
        if any(one == said or _within(one, said) or _within(said, one) for one in names):
            found.append(Match(row, True))
    return found


def _rank(match: Match, now: datetime) -> tuple[int, int, float]:
    at = parse_ts(_cell(match.row, "scheduled_at"))
    distance = abs((at - now).total_seconds()) if at is not None else float("inf")
    return (int(match.direct), int(_cell(match.row, "state") == LIVE), -distance)


def best_match(matches: list[Match], now: datetime) -> Match | None:
    """A direct category over Retro, the run already on over another, then the nearest."""
    return max(matches, key=lambda one: _rank(one, now)) if matches else None


def decide(title_row: Any, matches: list[Match], now: datetime) -> Verdict | None:
    """Title and category on one run is certain. Apart, a direct category wins over the title
    and the title wins over Retro."""
    if title_row is not None and any(same(one.row, title_row) for one in matches):
        return Verdict(title_row, BY_BOTH, title_row, title_row)
    best = best_match(matches, now)
    if best is None:
        return Verdict(title_row, BY_TITLE, title_row) if title_row is not None else None
    if title_row is None:
        return Verdict(best.row, BY_CATEGORY, None, best.row)
    if best.direct:
        return Verdict(best.row, BY_CATEGORY, title_row, best.row, disagree=True)
    return Verdict(title_row, BY_TITLE, title_row, best.row, disagree=True)


def is_certain(row: Any) -> bool:
    return _cell(row, "live_because") == BY_BOTH


# --- keeping the clock ---------------------------------------------------------------------------


def sheet_start(row: Any) -> datetime | None:
    return parse_ts(_cell(row, "sheet_at") or _cell(row, "scheduled_at"))


def sheet_end(row: Any) -> datetime | None:
    return parse_ts(_cell(row, "sheet_ends_at") or _cell(row, "ends_at"))


def length_of(row: Any) -> timedelta | None:
    seconds = _cell(row, "run_seconds")
    if seconds:
        return timedelta(seconds=int(seconds))
    start, end = sheet_start(row), sheet_end(row)
    return end - start if start is not None and end is not None else None


def chains(rows: Any) -> list[list[Any]]:
    """Runs the sheet puts back to back, or a setup buffer apart; a longer gap (the next day's
    show) starts a new chain."""
    ordered = sorted(
        (
            row
            for row in rows or ()
            if _cell(row, "state") != DROPPED and sheet_start(row) is not None
        ),
        key=lambda row: (sheet_start(row), int(_cell(row, "order_no") or 0)),
    )
    found: list[list[Any]] = []
    for row in ordered:
        if found:
            ended = sheet_end(found[-1][-1])
            if ended is not None and -CHAIN_SLACK <= sheet_start(row) - ended <= (
                CHAIN_REACH + CHAIN_SLACK
            ):
                found[-1].append(row)
                continue
        found.append([row])
    return found


def _iso(at: datetime | None) -> str | None:
    return at.isoformat() if at is not None else None


def _differs(stored: Any, wanted: datetime | None) -> bool:
    return parse_ts(stored) != wanted


def settled(row: Any) -> bool:
    return _cell(row, "state") in (LIVE, DONE)


def retimed(rows: Any, setup_minutes: int = 0) -> list[Retime]:
    """Each run's start where the stream puts it: a run seen starting is anchored there, and
    every later run of its chain starts `setup_minutes` after the one before it should end
    (its estimate). Runs before the first anchor keep the sheet's times; a run that is live
    or done and was never seen starting stays where it is."""
    setup = timedelta(minutes=max(0, int(setup_minutes or 0)))
    found: list[Retime] = []
    for chain in chains(rows):
        cursor: datetime | None = None
        for row in chain:
            actual = parse_ts(_cell(row, "actual_started_at"))
            ended = parse_ts(_cell(row, "actual_ended_at"))
            held = actual is None and settled(row)
            if actual is None and cursor is None and ended is None:
                if held:
                    continue
                if _differs(_cell(row, "scheduled_at"), sheet_start(row)) or _differs(
                    _cell(row, "ends_at"), sheet_end(row)
                ):
                    found.append(
                        Retime(
                            row,
                            _cell(row, "sheet_at") or _cell(row, "scheduled_at"),
                            _cell(row, "sheet_ends_at") or _cell(row, "ends_at"),
                        )
                    )
                continue
            kept = parse_ts(_cell(row, "scheduled_at")) if held else None
            start = actual or kept or cursor or sheet_start(row)
            span = length_of(row)
            end = ended or (parse_ts(_cell(row, "ends_at")) if kept is not None else None)
            if end is None and start is not None and span is not None:
                end = start + span
            cursor = end + setup if end is not None else None
            if _differs(_cell(row, "scheduled_at"), start) or _differs(_cell(row, "ends_at"), end):
                found.append(Retime(row, _iso(start), _iso(end)))
    return found


def day_of(row: Any, days: Any) -> list[Any]:
    for day in days or ():
        if any(same(one, row) for one in day):
            return list(day)
    return []


def early_line(row: Any, minutes: Any) -> datetime | None:
    planned = sheet_start(row)
    if planned is None or int(minutes or 0) <= 0:
        return None
    return planned - timedelta(minutes=int(minutes))


def day_line(row: Any, days: Any, minutes: Any) -> datetime | None:
    """From when the stream may call a run of this show-day live: so long before the day's
    first planned start. None once another run of the day is live or done, or nothing holds."""
    day = day_of(row, days)
    if not day or any(settled(one) for one in day if not same(one, row)):
        return None
    return early_line(day[0], minutes)


def is_retimed(row: Any) -> bool:
    sheet = sheet_start(row)
    return sheet is not None and parse_ts(_cell(row, "scheduled_at")) != sheet


def retimed_count(rows: Any) -> int:
    return sum(1 for row in rows or () if _cell(row, "state") != DROPPED and is_retimed(row))


def on_the_sheet(rows: Any) -> list[Retime]:
    """Every run back on the sheet's own times, for the staff move that clears the clock."""
    return [
        Retime(
            row,
            _cell(row, "sheet_at") or _cell(row, "scheduled_at"),
            _cell(row, "sheet_ends_at") or _cell(row, "ends_at"),
        )
        for row in rows or ()
        if _cell(row, "state") != DROPPED
        and (
            is_retimed(row)
            or _differs(_cell(row, "ends_at"), sheet_end(row))
            or _cell(row, "actual_started_at")
            or _cell(row, "actual_ended_at")
        )
    ]
