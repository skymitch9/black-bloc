"""Which tone each member hears on top of the cookout voice, and the staff pin that fixes it."""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from . import tone_keys
from .personas import (
    COOKOUT,
    DRIFT_CHANCE,
    DRIFT_EVERY_TURNS,
    POOL,
    Trope,
    enabled_tropes,
    pick_trope,
    step_from,
)

log = logging.getLogger(__name__)

WINDOW_MINUTES = 30
PINNED = "pinned"
NAMED = "named"
ROLLED = "rolled"
SET = "set"
DRIFTED = "drifted"
FEEDBACK = "feedback"
HOWS = (ROLLED, SET, DRIFTED, FEEDBACK)
MEAN = "mean"
WRONG = "wrong"
SETTLE_HALVES = 4
SETTLE_FLOOR = 0.02
NEW = "new"
SETTLING = "settling"
SETTLED = "settled"


@dataclass(frozen=True)
class Settle:
    """How a tone settles: the first chance of a step, how fast it halves, where it stops."""

    start: float = DRIFT_CHANCE
    halves: int = SETTLE_HALVES
    floor: float = SETTLE_FLOOR


STOCK = Settle()


def whole(store: Any, guild_id: Any, key: str) -> int:
    fallback = int(tone_keys.TONE_SETTINGS[key][1])
    try:
        return int(store.get(guild_id, key))
    except Exception:
        return fallback


def settle_of(store: Any, guild_id: Any) -> Settle:
    """The three numbers staff set, as the shape the tone's own arithmetic reads."""
    if store is None or guild_id is None:
        return STOCK
    return Settle(
        start=whole(store, guild_id, tone_keys.DRIFT_START_KEY) / 100,
        halves=whole(store, guild_id, tone_keys.DRIFT_HALVES_KEY),
        floor=whole(store, guild_id, tone_keys.DRIFT_FLOOR_KEY) / 100,
    )


@dataclass(frozen=True)
class Heard:
    trope: Trope | None
    source: str = COOKOUT
    turns: int = 0
    since: str | None = None
    how: str | None = None
    settled: int = 0
    heard: int = 0
    moved: tuple[str, str] | None = None
    chance: float = 0.0
    stored: bool = False
    was: str | None = None

    @property
    def name(self) -> str:
        return self.trope.name if self.trope is not None else COOKOUT


def share(value: Any) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def drift_chance(settled: Any, settle: Settle = STOCK) -> float:
    """The chance of one step, halved every `halves` quiet conversations, never under the floor."""
    start = share(settle.start)
    floor = min(share(settle.floor), start)
    passed = max(0, int(settled or 0))
    if int(settle.halves or 0) <= 0:
        return start
    return max(floor, start * 0.5 ** (passed / int(settle.halves)))


def settled_share(settled: Any, settle: Settle = STOCK) -> float:
    """0 while the tone is new, 1 once the chance has reached its floor."""
    start = share(settle.start)
    floor = min(share(settle.floor), start)
    if start <= floor:
        return 1.0
    return share((start - drift_chance(settled, settle)) / (start - floor))


def settled_word(settled: Any, settle: Settle = STOCK) -> str:
    found = settled_share(settled, settle)
    if found >= 1.0:
        return SETTLED
    return SETTLING if found >= 0.5 else NEW


def col(row: Any, name: str, fallback: Any = None) -> Any:
    try:
        found = row[name]
    except (KeyError, IndexError, TypeError):
        return fallback
    return fallback if found is None else found


def voice_key(guild_id: Any, user_id: Any, since: Any) -> str:
    return f"{int(guild_id or 0)}:{int(user_id or 0)}:{since}"


def window_start(now: datetime, minutes: int = WINDOW_MINUTES) -> str:
    return (now - timedelta(minutes=minutes)).isoformat()


async def voice_row(db: Any, guild_id: Any, user_id: Any) -> Any:
    cur = await db.conn.execute(
        "SELECT * FROM chat_voice WHERE guild_id = ? AND user_id = ?",
        (int(guild_id), int(user_id)),
    )
    return await cur.fetchone()


async def window_turns(db: Any, guild_id: Any, user_id: Any, *, now: datetime) -> int:
    """Model turns this member had anywhere in the server in the last half hour."""
    cur = await db.conn.execute(
        "SELECT COUNT(*) FROM chat_window WHERE guild_id = ? AND user_id = ? AND at >= ? "
        "AND tier IS NOT NULL",
        (int(guild_id), int(user_id), window_start(now)),
    )
    row = await cur.fetchone()
    return int((row[0] if row is not None else 0) or 0)


async def talking_now(db: Any, guild_id: Any, *, now: datetime) -> dict[int, int]:
    cur = await db.conn.execute(
        "SELECT user_id, COUNT(*) AS n FROM chat_window WHERE guild_id = ? AND at >= ? "
        "AND tier IS NOT NULL GROUP BY user_id",
        (int(guild_id), window_start(now)),
    )
    return {int(row["user_id"]): int(row["n"]) for row in await cur.fetchall()}


def heard_from(
    setting: Any,
    rows: Any,
    row: Any,
    *,
    guild_id: Any,
    user_id: Any,
    turns: int,
    now: datetime,
    settle: Settle = STOCK,
) -> Heard:
    """cookout for everyone > a member's pin > a named server mood > the member's stored tone."""
    said = str(setting or COOKOUT).strip().lower()
    if said == COOKOUT:
        return Heard(None)
    fresh = turns <= 0 or row is None or not row["since"]
    since = now.isoformat() if fresh else str(row["since"])
    counted = 0 if turns <= 0 else int(turns)
    pool = enabled_tropes(rows)
    pinned = str(row["pinned"] or "") if row is not None else ""
    if pinned:
        found = next((one for one in pool if one.name == pinned), None)
        if found is not None:
            return Heard(found, PINNED, counted, since)
        log.info("chat_voice: %s is pinned to %s, which is off", user_id, pinned)
    if said != POOL:
        found = pick_trope(said, rows)
        return Heard(found, NAMED if found else COOKOUT, counted, since)
    return stored_tone(
        pool,
        row,
        key=voice_key(guild_id, user_id, since),
        fresh=fresh,
        turns=counted,
        since=since,
        now=now,
        settle=settle,
    )


def lapsed(row: Any, now: datetime) -> bool:
    """A conversation in this tone came before this one, and its window has closed."""
    before = col(row, "since")
    if not before:
        return False
    try:
        then = datetime.fromisoformat(str(before))
    except ValueError:
        return False
    return now - then >= timedelta(minutes=WINDOW_MINUTES)


def stored_tone(
    pool: list[Trope],
    row: Any,
    *,
    key: str,
    fresh: bool,
    turns: int,
    since: str,
    now: datetime,
    settle: Settle = STOCK,
) -> Heard:
    """The member's own tone: rolled once, kept between conversations, a step less likely each."""
    if not pool:
        return Heard(None, COOKOUT, turns, since)
    live = {one.name: one for one in pool}
    was = col(row, "tone")
    tone = live.get(str(was or ""))
    if tone is None:
        rolled = pool[random.Random(key).randrange(len(pool))]
        return Heard(
            rolled,
            ROLLED,
            turns,
            since,
            how=ROLLED,
            heard=1,
            chance=drift_chance(0, settle),
            stored=True,
            was=was,
        )
    how = str(col(row, "how", ROLLED))
    settled = int(col(row, "settled", 0)) + (1 if fresh and lapsed(row, now) else 0)
    heard = int(col(row, "heard", 0)) + 1
    chance = drift_chance(settled, settle)
    moved = None
    if heard % DRIFT_EVERY_TURNS == 0:
        rng = random.Random(f"{key}:{heard}")
        if rng.random() < chance:
            stepped = step_from(tone, pool, rng)
            if stepped.name != tone.name:
                moved = (tone.name, stepped.name)
                tone, how, settled, heard = stepped, DRIFTED, 0, 0
    return Heard(
        tone,
        ROLLED,
        turns,
        since,
        how=how,
        settled=settled,
        heard=heard,
        moved=moved,
        chance=chance,
        stored=True,
        was=was,
    )


KEEP_HEARD = (
    "INSERT INTO chat_voice(guild_id, user_id, trope, turns, since) VALUES (?, ?, ?, ?, ?) "
    "ON CONFLICT(guild_id, user_id) DO UPDATE SET trope = excluded.trope, "
    "turns = excluded.turns, since = excluded.since"
)
KEEP_STORED = (
    "INSERT INTO chat_voice(guild_id, user_id, trope, turns, since, tone, how, settled, heard) "
    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(guild_id, user_id) DO UPDATE SET "
    "trope = excluded.trope, turns = excluded.turns, since = excluded.since, "
    "tone = excluded.tone, how = excluded.how, settled = excluded.settled, heard = excluded.heard "
    "WHERE chat_voice.tone IS ?"
)
KEEP_MOVED = (
    "UPDATE chat_voice SET moved_at = ?, moved_from = ?, moved_why = NULL, set_by = NULL "
    "WHERE guild_id = ? AND user_id = ? AND tone = ?"
)


async def remember_heard(
    db: Any, guild_id: Any, user_id: Any, heard: Heard, *, now: datetime | None = None
) -> None:
    where = (int(guild_id), int(user_id))
    if not heard.stored:
        await db.conn.execute(KEEP_HEARD, (*where, heard.name, heard.turns, heard.since))
        await db.conn.commit()
        return
    kept = (heard.name, heard.turns, heard.since, heard.name, heard.how, heard.settled, heard.heard)
    await db.conn.execute(KEEP_STORED, (*where, *kept, heard.was))
    if heard.moved is not None:
        at = (now or datetime.now(UTC)).isoformat()
        await db.conn.execute(KEEP_MOVED, (at, heard.moved[0], *where, heard.name))
    await db.conn.commit()


async def heard_for(
    db: Any,
    setting: Any,
    rows: Any,
    *,
    guild_id: Any,
    user_id: Any,
    now: datetime | None = None,
    settle: Settle = STOCK,
) -> Heard:
    """The tone for one reply, written down so the same member hears it in every channel."""
    at = now or datetime.now(UTC)
    if str(setting or COOKOUT).strip().lower() == COOKOUT:
        return Heard(None)
    try:
        row = await voice_row(db, guild_id, user_id)
        turns = await window_turns(db, guild_id, user_id, now=at)
    except Exception as exc:
        log.warning("chat_voice: the member's tone was not read — %s: %s", type(exc).__name__, exc)
        row, turns = None, 0
    heard = heard_from(
        setting, rows, row, guild_id=guild_id, user_id=user_id, turns=turns, now=at, settle=settle
    )
    if heard.trope is None:
        return heard
    try:
        await remember_heard(db, guild_id, user_id, heard, now=at)
    except Exception as exc:
        log.warning("chat_voice: the member's tone was not kept — %s: %s", type(exc).__name__, exc)
    return heard


async def pin(db: Any, guild_id: Any, user_id: Any, trope: str, *, by: Any = None) -> None:
    at = datetime.now(UTC).isoformat()
    await db.conn.execute(
        "INSERT INTO chat_voice(guild_id, user_id, pinned, pinned_by, pinned_at) "
        "VALUES (?, ?, ?, ?, ?) ON CONFLICT(guild_id, user_id) DO UPDATE SET "
        "pinned = excluded.pinned, pinned_by = excluded.pinned_by, pinned_at = excluded.pinned_at",
        (int(guild_id), int(user_id), str(trope), by, at),
    )
    await db.conn.commit()


async def unpin(db: Any, guild_id: Any, user_id: Any) -> bool:
    cur = await db.conn.execute(
        "UPDATE chat_voice SET pinned = NULL, pinned_by = NULL, pinned_at = NULL "
        "WHERE guild_id = ? AND user_id = ? AND pinned IS NOT NULL",
        (int(guild_id), int(user_id)),
    )
    await db.conn.commit()
    return bool(cur.rowcount)


SET_TONE = (
    "INSERT INTO chat_voice(guild_id, user_id, tone, how, set_by, moved_at, moved_from, trope) "
    "VALUES (?, ?, ?, ?, ?, ?, NULL, ?) ON CONFLICT(guild_id, user_id) DO UPDATE SET "
    "moved_from = chat_voice.tone, tone = excluded.tone, how = excluded.how, "
    "set_by = excluded.set_by, moved_at = excluded.moved_at, moved_why = NULL, settled = 0, "
    "heard = 0, since = NULL, turns = 0, fed_since = NULL, trope = excluded.trope"
)
FEED_TONE = (
    "UPDATE chat_voice SET moved_from = tone, tone = ?, trope = ?, how = ?, moved_at = ?, "
    "moved_why = ?, set_by = NULL, settled = 0, heard = 0, fed_since = since "
    "WHERE guild_id = ? AND user_id = ?"
)
CLAIM_FEEDBACK = (
    "UPDATE chat_voice SET fed_since = since WHERE guild_id = ? AND user_id = ? "
    "AND since IS NOT NULL AND (fed_since IS NULL OR fed_since != since)"
)


async def set_tone(
    db: Any,
    guild_id: Any,
    user_id: Any,
    tone: str,
    *,
    how: str = SET,
    by: Any = None,
    now: datetime | None = None,
) -> None:
    """A starting tone: used from the member's next answer, and free to drift like any other."""
    at = (now or datetime.now(UTC)).isoformat()
    await db.conn.execute(
        SET_TONE, (int(guild_id), int(user_id), str(tone), how, by, at, str(tone))
    )
    await db.conn.commit()


def another(pool: list[Trope], current: Any, rng: Any = None) -> Trope | None:
    """A reroll never lands on the tone the member already has while another one is on."""
    found = [one for one in pool if one.name != str(current or "")] or list(pool)
    if not found:
        return None
    return found[(rng or random.SystemRandom()).randrange(len(found))]


def fed_already(row: Any) -> bool:
    since = col(row, "since")
    return bool(since) and str(col(row, "fed_since", "")) == str(since)


async def move_for_feedback(
    db: Any, guild_id: Any, user_id: Any, tone: str, why: str, *, now: datetime | None = None
) -> None:
    at = (now or datetime.now(UTC)).isoformat()
    await db.conn.execute(
        FEED_TONE, (str(tone), str(tone), FEEDBACK, at, str(why), int(guild_id), int(user_id))
    )
    await db.conn.commit()


async def claim_feedback(db: Any, guild_id: Any, user_id: Any) -> bool:
    """This conversation's one verdict, taken in one statement so two at once cannot both win."""
    cur = await db.conn.execute(CLAIM_FEEDBACK, (int(guild_id), int(user_id)))
    await db.conn.commit()
    return bool(cur.rowcount)


def order_of(value: Any) -> tuple[str, ...]:
    found: list[str] = []
    for one in str(value or "").replace("\n", ",").split(","):
        name = one.strip().lower()
        if name and name not in found:
            found.append(name)
    return tuple(found)


def step_toward(tone: Any, order: Any, enabled: Any) -> str | None:
    """The nearest tone that is on, nearer the front of the order; None when there is none."""
    listed = order if isinstance(order, tuple) else order_of(order)
    live = set(enabled or ())
    name = str(tone or "")
    if name not in listed:
        return None
    for one in reversed(listed[: listed.index(name)]):
        if one in live:
            return one
    return None


async def voice_rows(db: Any, guild_id: Any) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT * FROM chat_voice WHERE guild_id = ? "
        "ORDER BY pinned IS NULL, COALESCE(since, moved_at, pinned_at) DESC, user_id",
        (int(guild_id),),
    )
    return list(await cur.fetchall())


def hears_now(setting: Any, row: Any, enabled: set[str]) -> str:
    """What the member's next answer is written in, as far as it can be known before it."""
    said = str(setting or COOKOUT).strip().lower()
    if said == COOKOUT:
        return COOKOUT
    pinned = str(row["pinned"] or "")
    if pinned and pinned in enabled:
        return pinned
    if said != POOL:
        return said if said in enabled else COOKOUT
    stored = str(col(row, "tone", ""))
    if stored:
        return stored if stored in enabled else COOKOUT
    return str(row["trope"] or COOKOUT)


def state_of(row: Any, live: set[str], setting: Any = POOL) -> str | None:
    """How the tone the member hears got there, as one word both doors turn into their own."""
    said = str(setting or COOKOUT).strip().lower()
    if said == COOKOUT:
        return None
    pinned = str(row["pinned"] or "")
    if pinned and pinned in live:
        return PINNED
    if said != POOL or not col(row, "tone"):
        return None
    how = str(col(row, "how", ROLLED))
    return how if how in HOWS else ROLLED


def roster(
    rows: Any,
    setting: Any,
    enabled: Any,
    talking: dict[int, int],
    settle: Settle = STOCK,
) -> list[dict[str, Any]]:
    """One entry per member with a row, in the shape both doors read."""
    live = set(enabled or ())
    found = []
    for row in rows or ():
        pinned = str(row["pinned"] or "") or None
        user_id = int(row["user_id"])
        settled = int(col(row, "settled", 0))
        found.append(
            {
                "user_id": user_id,
                "trope": hears_now(setting, row, live),
                "last_trope": row["trope"],
                "pinned": pinned,
                "pinned_by": row["pinned_by"],
                "pinned_at": row["pinned_at"],
                "waiting": bool(pinned) and pinned not in live,
                "since": row["since"],
                "turns": int(row["turns"] or 0),
                "active": user_id in talking,
                "tone": col(row, "tone"),
                "state": state_of(row, live, setting),
                "settled": settled,
                "settled_share": round(settled_share(settled, settle), 3),
                "settled_word": settled_word(settled, settle),
                "chance": round(drift_chance(settled, settle), 4),
                "set_by": col(row, "set_by"),
                "moved_at": col(row, "moved_at"),
                "moved_from": col(row, "moved_from"),
                "moved_why": col(row, "moved_why"),
            }
        )
    return found
