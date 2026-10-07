"""The personal best feed in SQLite: who is matched, their baseline, what was posted, the outage."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from typing import Any

from .speedrun import VERIFIED, PersonalBest, Runner

MATCHED = "matched"
NONE = "none"
OPTED_OUT = "opted_out"
BLOCKED = "blocked"
STATES = (MATCHED, NONE, OPTED_OUT, BLOCKED)

AUTO = "auto"
STAFF = "staff"
MEMBER = "member"

POSTED = "posted"
REHEARSED = "rehearsed"
DRY = "dry"
HELD = "held"
FAILED = "failed"
CLAIMED = "claimed"
UNCONFIRMED = "unconfirmed"
SHOWN = (POSTED, REHEARSED, DRY, HELD, FAILED, UNCONFIRMED)

POSTS_LIMIT = 50
AGAIN_MARK = "#again"


class RunnerTaken(Exception):
    """Another member of this server already holds that speedrun.com account."""

    def __init__(self, holder_id: int) -> None:
        super().__init__(str(holder_id))
        self.holder_id = int(holder_id)


def stamp(now: datetime | None = None) -> str:
    return (now or datetime.now(UTC)).astimezone(UTC).isoformat()


def parsed(value: Any) -> datetime | None:
    try:
        found = datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None
    return found if found.tzinfo else found.replace(tzinfo=UTC)


async def links(db: Any) -> dict[int, str]:
    """Every member's linked Twitch login, as go-live stores it."""
    cur = await db.conn.execute("SELECT user_id, twitch_login FROM golive_links")
    return {
        int(row["user_id"]): str(row["twitch_login"]).casefold() for row in await cur.fetchall()
    }


async def match(db: Any, guild_id: int, user_id: int) -> Any:
    cur = await db.conn.execute(
        "SELECT * FROM pb_matches WHERE guild_id = ? AND user_id = ?", (guild_id, user_id)
    )
    return await cur.fetchone()


async def matches(db: Any, guild_id: int) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT * FROM pb_matches WHERE guild_id = ? ORDER BY user_id", (guild_id,)
    )
    return list(await cur.fetchall())


async def holder_of(db: Any, guild_id: int, src_user_id: str) -> int | None:
    cur = await db.conn.execute(
        "SELECT user_id FROM pb_matches WHERE guild_id = ? AND src_user_id = ?",
        (guild_id, src_user_id),
    )
    row = await cur.fetchone()
    return int(row["user_id"]) if row is not None else None


async def forget_runs(db: Any, guild_id: int, user_id: int) -> None:
    await db.conn.execute(
        "DELETE FROM pb_runs WHERE guild_id = ? AND user_id = ?", (guild_id, user_id)
    )


async def write_match(
    db: Any,
    guild_id: int,
    user_id: int,
    runner: Runner,
    *,
    source: str,
    twitch_login: str | None,
    set_by: int | None = None,
    now: datetime | None = None,
) -> Any:
    """A new identity for a member: the baseline goes, so the next look is a first sight."""
    holder = await holder_of(db, guild_id, runner.id)
    if holder is not None and holder != int(user_id):
        raise RunnerTaken(holder)
    at = stamp(now)
    before = await match(db, guild_id, user_id)
    back = before is not None and before["gone_src_user_id"] == runner.id
    try:
        if not back:
            await forget_runs(db, guild_id, user_id)
        await db.conn.execute(
            "INSERT INTO pb_matches(guild_id, user_id, twitch_login, src_user_id, src_name, "
            "src_weblink, source, state, state_by, set_by, reason, checked_at, matched_at, "
            "baseline_at, looked_at, look_error, last_pb_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, NULL, NULL, NULL, NULL, ?) "
            "ON CONFLICT(guild_id, user_id) DO UPDATE SET twitch_login = excluded.twitch_login, "
            "src_user_id = excluded.src_user_id, src_name = excluded.src_name, "
            "src_weblink = excluded.src_weblink, source = excluded.source, "
            "state = excluded.state, state_by = excluded.state_by, set_by = excluded.set_by, "
            "reason = NULL, checked_at = excluded.checked_at, matched_at = excluded.matched_at, "
            "baseline_at = CASE WHEN ? THEN baseline_at ELSE NULL END, looked_at = NULL, "
            "look_error = NULL, last_pb_at = NULL, misses = 0, gone_src_user_id = NULL, "
            "quiet = NULL, updated_at = excluded.updated_at",
            (
                guild_id,
                user_id,
                twitch_login,
                runner.id,
                runner.name,
                runner.weblink,
                source,
                MATCHED,
                source,
                set_by,
                at,
                at,
                at,
                1 if back else 0,
            ),
        )
        await db.conn.commit()
    except sqlite3.IntegrityError as exc:
        await db.conn.rollback()
        raise RunnerTaken(await holder_of(db, guild_id, runner.id) or 0) from exc
    return await match(db, guild_id, user_id)


async def write_state(
    db: Any,
    guild_id: int,
    user_id: int,
    state: str,
    *,
    state_by: str,
    set_by: int | None = None,
    reason: str | None = None,
    twitch_login: str | None = None,
    keep_runner: bool = False,
    now: datetime | None = None,
) -> Any:
    """Any state but `matched`. The runner is dropped unless told to keep it (an opt-out)."""
    at = stamp(now)
    before = await match(db, guild_id, user_id)
    kept = before is not None and keep_runner
    if not kept:
        await forget_runs(db, guild_id, user_id)
    await db.conn.execute(
        "INSERT INTO pb_matches(guild_id, user_id, twitch_login, state, state_by, set_by, "
        "reason, checked_at, updated_at, opted_out_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(guild_id, user_id) DO UPDATE SET state = excluded.state, "
        "state_by = excluded.state_by, set_by = excluded.set_by, reason = excluded.reason, "
        "checked_at = excluded.checked_at, updated_at = excluded.updated_at, "
        "opted_out_at = COALESCE(excluded.opted_out_at, opted_out_at)"
        + (
            ""
            if kept
            else ", twitch_login = excluded.twitch_login, src_user_id = NULL, src_name = NULL, "
            "src_weblink = NULL, source = NULL, matched_at = NULL, baseline_at = NULL, "
            "looked_at = NULL, look_error = NULL, last_pb_at = NULL, misses = 0, "
            "gone_src_user_id = NULL, quiet = NULL"
        ),
        (
            guild_id,
            user_id,
            twitch_login,
            state,
            state_by,
            set_by,
            reason,
            at,
            at,
            at if state == OPTED_OUT else None,
        ),
    )
    await db.conn.commit()
    return await match(db, guild_id, user_id)


async def runner_gone(
    db: Any, guild_id: int, user_id: int, reason: str, now: datetime | None = None
) -> Any:
    """An automatic match is undone; its baseline stays for the day the same runner is back."""
    at = stamp(now)
    await db.conn.execute(
        "UPDATE pb_matches SET state = ?, state_by = ?, set_by = NULL, reason = ?, "
        "checked_at = ?, updated_at = ?, gone_src_user_id = src_user_id, src_user_id = NULL, "
        "src_name = NULL, src_weblink = NULL, source = NULL, matched_at = NULL, "
        "looked_at = NULL, look_error = NULL, misses = 0 WHERE guild_id = ? AND user_id = ?",
        (NONE, AUTO, reason, at, at, guild_id, user_id),
    )
    await db.conn.commit()
    return await match(db, guild_id, user_id)


async def restore(
    db: Any,
    guild_id: int,
    user_id: int,
    *,
    state_by: str,
    set_by: int | None = None,
    ends_opt_out: bool = False,
) -> Any:
    """Out of a block or an opt-out. An opt-out outlives a block unless this move ends it."""
    before = await match(db, guild_id, user_id)
    if before is None:
        return None
    if before["opted_out_at"] and not ends_opt_out:
        state, state_by, set_by = OPTED_OUT, MEMBER, int(user_id)
    else:
        state = MATCHED if before["src_user_id"] else NONE
    await db.conn.execute(
        "UPDATE pb_matches SET state = ?, state_by = ?, set_by = ?, reason = NULL, "
        "checked_at = CASE WHEN ? = 'none' THEN NULL ELSE checked_at END, updated_at = ?, "
        "opted_out_at = CASE WHEN ? THEN NULL ELSE opted_out_at END "
        "WHERE guild_id = ? AND user_id = ?",
        (state, state_by, set_by, state, stamp(), 1 if ends_opt_out else 0, guild_id, user_id),
    )
    await db.conn.commit()
    return await match(db, guild_id, user_id)


async def baseline(db: Any, guild_id: int, user_id: int) -> dict[str, Any]:
    cur = await db.conn.execute(
        "SELECT * FROM pb_runs WHERE guild_id = ? AND user_id = ?", (guild_id, user_id)
    )
    return {str(row["slot"]): row for row in await cur.fetchall()}


async def record_look(
    db: Any,
    guild_id: int,
    user_id: int,
    bests: Any,
    *,
    first: bool,
    newest: bool = False,
    quiet: dict[str, Any] | None = None,
    now: datetime | None = None,
) -> None:
    """Upserts only: a slot a look did not return stays, so a short answer cannot arm a replay."""
    at = stamp(now)
    for best in bests:
        await db.conn.execute(
            "INSERT OR REPLACE INTO pb_runs(guild_id, user_id, slot, run_id, seconds, place, "
            "game, category, weblink, verified_at, seen_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                guild_id,
                user_id,
                best.slot,
                best.run_id,
                best.seconds,
                best.place,
                best.game,
                best.category,
                best.weblink,
                best.verified_at.isoformat() if best.verified_at else None,
                at,
            ),
        )
    await db.conn.execute(
        "UPDATE pb_matches SET looked_at = ?, look_error = NULL, misses = 0, "
        "baseline_at = CASE WHEN ? THEN ? ELSE baseline_at END, "
        "last_pb_at = CASE WHEN ? THEN ? ELSE last_pb_at END, "
        "quiet = COALESCE(?, quiet) "
        "WHERE guild_id = ? AND user_id = ?",
        (
            at,
            1 if first else 0,
            at,
            1 if newest else 0,
            at,
            json.dumps(quiet | {"at": at}) if quiet else None,
            guild_id,
            user_id,
        ),
    )
    await db.conn.commit()


def quiet_of(row: Any) -> dict[str, Any] | None:
    """The last runs a look recorded without posting, by reason, or None."""
    try:
        found = json.loads(row["quiet"]) if row is not None and row["quiet"] else None
    except (TypeError, ValueError):
        return None
    return found if isinstance(found, dict) else None


async def record_miss(
    db: Any, guild_id: int, user_id: int, reason: str, now: datetime | None = None
) -> int:
    """One more look in a row that speedrun.com answered with nothing; how many that makes."""
    await db.conn.execute(
        "UPDATE pb_matches SET looked_at = ?, look_error = ?, misses = misses + 1 "
        "WHERE guild_id = ? AND user_id = ?",
        (stamp(now), reason, guild_id, user_id),
    )
    await db.conn.commit()
    row = await match(db, guild_id, user_id)
    return int(row["misses"] or 0) if row is not None else 0


async def record_lookup_error(
    db: Any,
    guild_id: int,
    user_id: int,
    login: str | None,
    reason: str,
    code: str,
    now: datetime | None = None,
) -> bool:
    """A lookup that failed for this member alone; True the first time, so it is logged once."""
    before = await match(db, guild_id, user_id)
    fresh = before is None or not before["look_error"]
    await write_state(
        db, guild_id, user_id, NONE, state_by=AUTO, reason=code, twitch_login=login, now=now
    )
    await db.conn.execute(
        "UPDATE pb_matches SET look_error = ? WHERE guild_id = ? AND user_id = ?",
        (reason, guild_id, user_id),
    )
    await db.conn.commit()
    return fresh


async def record_look_error(
    db: Any, guild_id: int, user_id: int, reason: str, now: datetime | None = None
) -> bool:
    """True the first time this member's look fails, so it is logged once and not every hour."""
    before = await match(db, guild_id, user_id)
    fresh = before is not None and not before["look_error"]
    await db.conn.execute(
        "UPDATE pb_matches SET looked_at = ?, look_error = ? WHERE guild_id = ? AND user_id = ?",
        (stamp(now), reason, guild_id, user_id),
    )
    await db.conn.commit()
    return fresh


async def claim_post(
    db: Any,
    guild_id: int,
    user_id: int,
    best: PersonalBest,
    src_name: str,
    *,
    outcome: str = CLAIMED,
    now: datetime | None = None,
) -> int | None:
    """One row per run for the life of the database; None means another look already has it."""
    cur = await db.conn.execute(
        "INSERT OR IGNORE INTO pb_posts(guild_id, user_id, run_id, src_name, game, category, "
        "seconds, place, weblink, verified_at, outcome, at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, "
        "?, ?)",
        (
            guild_id,
            user_id,
            best.run_id,
            src_name,
            best.game,
            best.category,
            best.seconds,
            best.place,
            best.weblink,
            best.verified_at.isoformat() if best.verified_at else None,
            outcome,
            stamp(now),
        ),
    )
    await db.conn.commit()
    return int(cur.lastrowid) if cur.rowcount else None


def run_of(run_id: Any) -> str:
    """The speedrun.com run a post row is about; a repeat's own key carries a suffix."""
    return str(run_id or "").split(AGAIN_MARK, 1)[0]


def best_of(row: Any) -> PersonalBest:
    return PersonalBest(
        run_id=run_of(row["run_id"]),
        slot="",
        game=str(row["game"] or ""),
        category=str(row["category"] or ""),
        seconds=float(row["seconds"] or 0),
        place=row["place"],
        weblink=str(row["weblink"] or ""),
        status=VERIFIED,
        verified_at=parsed(row["verified_at"]) if row["verified_at"] else None,
    )


async def post(db: Any, guild_id: int, post_id: int) -> Any:
    cur = await db.conn.execute(
        "SELECT * FROM pb_posts WHERE guild_id = ? AND id = ?", (guild_id, int(post_id))
    )
    return await cur.fetchone()


async def claim_again(db: Any, source: Any, *, now: datetime | None = None) -> int:
    """A new row for a repeat of `source`; the run's own row and its claim stay as they were."""
    base = run_of(source["run_id"])
    cur = await db.conn.execute(
        "SELECT run_id FROM pb_posts WHERE guild_id = ? AND again_of IS NOT NULL",
        (source["guild_id"],),
    )
    taken = {str(row["run_id"]) for row in await cur.fetchall()}
    count = sum(1 for one in taken if run_of(one) == base) + 1
    while f"{base}{AGAIN_MARK}{count}" in taken:
        count += 1
    cur = await db.conn.execute(
        "INSERT INTO pb_posts(guild_id, user_id, run_id, src_name, game, category, seconds, "
        "place, weblink, verified_at, outcome, at, again_of) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            source["guild_id"],
            source["user_id"],
            f"{base}{AGAIN_MARK}{count}",
            source["src_name"],
            source["game"],
            source["category"],
            source["seconds"],
            source["place"],
            source["weblink"],
            source["verified_at"],
            CLAIMED,
            stamp(now),
            int(source["id"]),
        ),
    )
    await db.conn.commit()
    return int(cur.lastrowid)


async def settle_post(
    db: Any,
    post_id: int,
    outcome: str,
    *,
    channel_id: int | None = None,
    aimed_at: int | None = None,
    message_id: int | None = None,
    reason: str | None = None,
) -> None:
    await db.conn.execute(
        "UPDATE pb_posts SET outcome = ?, channel_id = ?, aimed_at = ?, message_id = ?, "
        "reason = ? WHERE id = ?",
        (outcome, channel_id, aimed_at, message_id, reason, post_id),
    )
    await db.conn.commit()


async def settle_stale_claims(db: Any, guild_id: int, reason: str) -> list[Any]:
    """Claims no look ever settled become `unconfirmed`, in words; the rows that were."""
    cur = await db.conn.execute(
        "SELECT * FROM pb_posts WHERE guild_id = ? AND outcome = ? ORDER BY id",
        (guild_id, CLAIMED),
    )
    rows = list(await cur.fetchall())
    if rows:
        await db.conn.execute(
            "UPDATE pb_posts SET outcome = ?, reason = ? WHERE guild_id = ? AND outcome = ?",
            (UNCONFIRMED, reason, guild_id, CLAIMED),
        )
        await db.conn.commit()
    return rows


async def posts(db: Any, guild_id: int, limit: int = POSTS_LIMIT) -> list[Any]:
    marks = ", ".join("?" for _ in SHOWN)
    cur = await db.conn.execute(
        f"SELECT * FROM pb_posts WHERE guild_id = ? AND outcome IN ({marks}) "
        "ORDER BY id DESC LIMIT ?",
        (guild_id, *SHOWN, max(1, int(limit))),
    )
    return list(await cur.fetchall())


async def looks(db: Any, guild_id: int) -> Any:
    cur = await db.conn.execute("SELECT * FROM pb_looks WHERE guild_id = ?", (guild_id,))
    return await cur.fetchone()


async def _looks_row(db: Any, guild_id: int) -> None:
    await db.conn.execute("INSERT OR IGNORE INTO pb_looks(guild_id) VALUES (?)", (guild_id,))


async def record_ok(db: Any, guild_id: int, *, found: int, now: datetime | None = None) -> bool:
    """True when this call ended an outage."""
    before = await looks(db, guild_id)
    ended = before is not None and int(before["failures"] or 0) > 0
    at = stamp(now)
    await _looks_row(db, guild_id)
    await db.conn.execute(
        "UPDATE pb_looks SET last_at = ?, last_ok_at = ?, outcome = 'ok', reason = NULL, "
        "failures = 0, outage_since = NULL, backoff_until = NULL, looks = looks + 1, "
        "found = found + ?, summary_at = COALESCE(summary_at, ?) WHERE guild_id = ?",
        (at, at, int(found), at, guild_id),
    )
    await db.conn.commit()
    return ended


async def record_outage(
    db: Any, guild_id: int, reason: str, backoff_until: datetime, now: datetime | None = None
) -> int:
    """How many calls in a row have failed, this one included; 1 is the start of an outage."""
    at = stamp(now)
    await _looks_row(db, guild_id)
    await db.conn.execute(
        "UPDATE pb_looks SET last_at = ?, outcome = 'failed', reason = ?, "
        "failures = failures + 1, outage_since = COALESCE(outage_since, ?), backoff_until = ? "
        "WHERE guild_id = ?",
        (at, reason, at, stamp(backoff_until), guild_id),
    )
    await db.conn.commit()
    return int((await looks(db, guild_id))["failures"])


async def take_summary(db: Any, guild_id: int, now: datetime | None = None) -> tuple[int, int]:
    """The looks and the news since the last summary, and the count starts again."""
    before = await looks(db, guild_id)
    if before is None:
        return (0, 0)
    await db.conn.execute(
        "UPDATE pb_looks SET looks = 0, found = 0, summary_at = ? WHERE guild_id = ?",
        (stamp(now), guild_id),
    )
    await db.conn.commit()
    return (int(before["looks"] or 0), int(before["found"] or 0))


__all__ = [
    "AGAIN_MARK",
    "AUTO",
    "BLOCKED",
    "CLAIMED",
    "DRY",
    "FAILED",
    "HELD",
    "MATCHED",
    "MEMBER",
    "NONE",
    "OPTED_OUT",
    "POSTED",
    "POSTS_LIMIT",
    "REHEARSED",
    "SHOWN",
    "STAFF",
    "STATES",
    "UNCONFIRMED",
    "RunnerTaken",
    "baseline",
    "best_of",
    "claim_again",
    "claim_post",
    "forget_runs",
    "holder_of",
    "links",
    "looks",
    "match",
    "matches",
    "parsed",
    "post",
    "posts",
    "quiet_of",
    "record_look",
    "record_look_error",
    "record_lookup_error",
    "record_miss",
    "record_ok",
    "record_outage",
    "restore",
    "run_of",
    "runner_gone",
    "settle_post",
    "settle_stale_claims",
    "stamp",
    "take_summary",
    "write_match",
    "write_state",
]
