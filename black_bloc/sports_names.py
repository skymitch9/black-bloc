"""The sports names cache: teams, schools and players, searched locally and refreshed nightly."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any

from .actionlog import log_action
from .logkinds import VIA_DISCORD
from .settings_store import (
    BRACKETS_MODE,
    BRACKETS_NAMES_REFRESH_HOUR,
    DEFAULT_TIMEZONE_KEY,
)
from .sports import feeds
from .sports.model import (
    LEAGUES,
    PLAYER,
    PRO_LEAGUES,
    SCHOOL,
    SOURCE_NAMES,
    TEAM,
    Player,
    Team,
)
from .timezones import DEFAULT_TZ, zone

log = logging.getLogger(__name__)

SEARCH_LIMIT = 25
CANDIDATES = 400
ALIAS_JOIN = " | "
LISTS: tuple[tuple[str, str], ...] = (
    *((TEAM, league) for league in LEAGUES),
    (SCHOOL, ""),
    *((PLAYER, league) for league in PRO_LEAGUES),
)
STALE_HOURS = 20
OFF = "off"
STATE_ATTR = "_sports_names_state"
TASK_ATTR = "_sports_names_task"
LOCK_ATTR = "_sports_names_lock"


@dataclass
class Failing:
    at: str
    why: str
    via: str | None


def now_stamp(now: datetime | None = None) -> str:
    return (now or datetime.now(UTC)).astimezone(UTC).isoformat(timespec="seconds")


def list_key(kind: str, league: str) -> str:
    return f"{kind}:{league}" if league else kind


def failures(bot: Any) -> dict[str, Failing]:
    return bot.__dict__.setdefault(STATE_ATTR, {})


def joined(values: tuple[str, ...]) -> str | None:
    return ALIAS_JOIN.join(values) if values else None


def row_of(one: Team | Player) -> tuple[Any, ...]:
    if isinstance(one, Player):
        return (one.ext_id, one.name, one.short, None, one.team_ext_id)
    return (one.ext_id, one.name, one.short, joined(one.aliases), None)


async def upsert(
    db: Any, kind: str, league: str, source: str, rows: list[Any], now: str | None = None
) -> int:
    """New names are added and known ones refreshed in place; a name a feed dropped is kept."""
    at = now or now_stamp()
    await db.conn.executemany(
        "INSERT INTO sports_names(kind, league, source, ext_id, name, short, aliases, "
        "team_ext_id, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(source, kind, league, ext_id) DO UPDATE SET name = excluded.name, "
        "short = excluded.short, aliases = excluded.aliases, "
        "team_ext_id = excluded.team_ext_id, updated_at = excluded.updated_at",
        [(kind, league, source, *row_of(one), at) for one in rows],
    )
    await db.conn.commit()
    return len(rows)


async def counts(db: Any) -> dict[str, dict[str, Any]]:
    cur = await db.conn.execute(
        "SELECT kind, league, COUNT(*) AS n, MAX(updated_at) AS at, "
        "GROUP_CONCAT(DISTINCT source) AS sources FROM sports_names GROUP BY kind, league"
    )
    return {
        list_key(row["kind"], row["league"]): {
            "rows": int(row["n"]),
            "updated_at": row["at"],
            "sources": sorted(str(row["sources"] or "").split(",")) if row["sources"] else [],
        }
        for row in await cur.fetchall()
    }


async def newest(db: Any) -> str | None:
    cur = await db.conn.execute("SELECT MAX(updated_at) AS at FROM sports_names")
    found = await cur.fetchone()
    return found["at"] if found else None


async def known(db: Any, source: Any, ext_id: Any) -> Any:
    cur = await db.conn.execute(
        "SELECT * FROM sports_names WHERE source = ? AND ext_id = ? ORDER BY kind LIMIT 1",
        (str(source), str(ext_id)),
    )
    return await cur.fetchone()


async def labels(db: Any, pairs: list[tuple[Any, Any]]) -> dict[tuple[str, str], Any]:
    """The names rows a set of `(source, ext_id)` pairs point at, for the page to show."""
    wanted = list(dict.fromkeys((str(s), str(e)) for s, e in pairs if s and e))
    if not wanted:
        return {}
    marks = ", ".join("(?, ?)" for _ in wanted)
    cur = await db.conn.execute(
        f"SELECT source, ext_id, kind, league, name FROM sports_names "
        f"WHERE (source, ext_id) IN (VALUES {marks}) ORDER BY kind",
        tuple(value for pair in wanted for value in pair),
    )
    found: dict[tuple[str, str], Any] = {}
    for row in await cur.fetchall():
        found.setdefault((row["source"], row["ext_id"]), row)
    return found


def escaped(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def rank(row: Any, wanted: str) -> tuple[int, str]:
    """Prefix of the name, then a word of it, then the short name or an alias, then anywhere."""
    name = str(row["name"]).lower()
    short = str(row["short"] or "").lower()
    aliases = [one.lower() for one in str(row["aliases"] or "").split(ALIAS_JOIN) if one]
    if name.startswith(wanted):
        place = 0
    elif any(word.startswith(wanted) for word in name.split()):
        place = 1
    elif short.startswith(wanted) or any(one.startswith(wanted) for one in aliases):
        place = 2
    else:
        place = 3
    return (place, name)


def shown(row: Any) -> dict[str, Any]:
    return {
        "ext_id": row["ext_id"],
        "name": row["name"],
        "short": row["short"],
        "league": row["league"],
        "team": row["team_name"],
        "source": row["source"],
        "kind": row["kind"],
    }


async def search(
    db: Any, kind: str, league: str = "", query: str = "", limit: int = SEARCH_LIMIT
) -> list[dict[str, Any]]:
    """Up to `limit` names of one kind (and league) holding the typed text, the closest first."""
    wanted = " ".join(str(query or "").lower().split())
    if not wanted or kind not in (TEAM, SCHOOL, PLAYER):
        return []
    like = f"%{escaped(wanted)}%"
    where = ["n.kind = ?"]
    given: list[Any] = [kind]
    if league and kind != SCHOOL:
        where.append("n.league = ?")
        given.append(league)
    where.append(
        "(lower(n.name) LIKE ? ESCAPE '\\' OR lower(COALESCE(n.short, '')) LIKE ? ESCAPE '\\' "
        "OR lower(COALESCE(n.aliases, '')) LIKE ? ESCAPE '\\')"
    )
    given += [like, like, like]
    cur = await db.conn.execute(
        "SELECT n.*, t.name AS team_name FROM sports_names n LEFT JOIN sports_names t "
        "ON t.kind = 'team' AND t.source = n.source AND t.league = n.league "
        f"AND t.ext_id = n.team_ext_id WHERE {' AND '.join(where)} LIMIT ?",
        (*given, CANDIDATES),
    )
    rows = sorted(await cur.fetchall(), key=lambda row: rank(row, wanted))
    return [shown(row) for row in rows[: max(1, min(int(limit), SEARCH_LIMIT))]]


async def fetched(kind: str, league: str, fetch: Any, today: date | None) -> Any:
    if kind == SCHOOL:
        return await feeds.schools(fetch=fetch)
    if kind == PLAYER:
        return await feeds.players(league, fetch=fetch, today=today)
    return await feeds.teams(league, fetch=fetch)


async def logged(bot: Any, guilds: list[Any], actor: Any, details: dict, *, failing: bool) -> None:
    for guild in guilds:
        try:
            await log_action(
                bot,
                guild,
                "sports.names_failed" if failing else "sports.names_refreshed",
                actor=actor,
                details=details,
            )
        except Exception:
            log.exception("sports: could not write a names row")


async def refresh(
    bot: Any,
    guilds: list[Any],
    *,
    actor: Any = None,
    via: str = VIA_DISCORD,
    fetch: Any = None,
    today: date | None = None,
) -> dict[str, Any]:
    """Each list that answers is upserted; one that fails keeps its rows, logged once a streak."""
    held = failures(bot)
    refreshed: dict[str, int] = {}
    failed: dict[str, str] = {}
    for kind, league in LISTS:
        key = list_key(kind, league)
        answer = await fetched(kind, league, fetch, today)
        if answer.ok:
            refreshed[key] = await upsert(bot.db, kind, league, answer.via, answer.value)
            held.pop(key, None)
            continue
        failed[key] = str(answer.why)
        if key not in held:
            details = {"via": via, "list": key, "why": answer.why, "source": answer.via}
            await logged(bot, guilds, actor, details, failing=True)
        held[key] = Failing(now_stamp(), str(answer.why), answer.via)
    if refreshed:
        details = {"via": via, "counts": refreshed, "failed": sorted(failed)}
        await logged(bot, guilds, actor, details, failing=False)
    return {"refreshed": refreshed, "failed": failed}


def lock_of(bot: Any) -> asyncio.Lock:
    found = bot.__dict__.get(LOCK_ATTR)
    if found is None:
        found = bot.__dict__[LOCK_ATTR] = asyncio.Lock()
    return found


def running(bot: Any) -> asyncio.Task | None:
    task = bot.__dict__.get(TASK_ATTR)
    return task if task is not None and not task.done() else None


async def refreshed_once(bot: Any, guilds: list[Any], **given: Any) -> dict[str, Any]:
    async with lock_of(bot):
        return await refresh(bot, guilds, **given)


def start_refresh(bot: Any, guilds: list[Any], **given: Any) -> asyncio.Task | None:
    """The website's door: one refresh at a time, run behind the answer; None when one runs."""
    if running(bot) is not None or lock_of(bot).locked():
        return None
    task = asyncio.create_task(refreshed_once(bot, guilds, **given), name="sports-names-refresh")
    bot.__dict__[TASK_ATTR] = task
    task.add_done_callback(finished)
    return task


def finished(task: asyncio.Task) -> None:
    if not task.cancelled() and task.exception() is not None:
        log.error("sports: a names refresh ended badly", exc_info=task.exception())


async def status(bot: Any) -> dict[str, Any]:
    """Per list: how many names, when they were last refreshed, and the failure standing now."""
    held, stored = failures(bot), await counts(bot.db)
    lists = []
    for kind, league in LISTS:
        key = list_key(kind, league)
        found, failing = stored.get(key, {}), held.get(key)
        lists.append(
            {
                "list": key,
                "kind": kind,
                "league": league,
                "rows": found.get("rows", 0),
                "updated_at": found.get("updated_at"),
                "sources": [SOURCE_NAMES.get(one, one) for one in found.get("sources", [])],
                "failed_at": failing.at if failing else None,
                "why": failing.why if failing else None,
            }
        )
    return {"running": running(bot) is not None, "lists": lists}


def local_now(store: Any, guild_id: int, now: datetime) -> datetime:
    named = zone(store.get(guild_id, DEFAULT_TIMEZONE_KEY)) or zone(DEFAULT_TZ) or UTC
    return now.astimezone(named)


def stale(newest_at: str | None, now: datetime) -> bool:
    """No names yet, or an unreadable stamp, is stale (checklist 5)."""
    if not newest_at:
        return True
    try:
        held = datetime.fromisoformat(str(newest_at))
    except ValueError:
        return True
    if held.tzinfo is None:
        held = held.replace(tzinfo=UTC)
    return now - held >= timedelta(hours=STALE_HOURS)


def due(bot: Any, guild: Any, now: datetime, newest_at: str | None, tried_on: Any) -> bool:
    """Once a local day, from the refresh hour on, when the names are stale; at once when none."""
    if getattr(guild, "unavailable", False) or bot.store.get(guild.id, BRACKETS_MODE) == OFF:
        return False
    local = local_now(bot.store, guild.id, now)
    if tried_on == local.date():
        return False
    if not newest_at:
        return True
    hour = int(bot.store.get(guild.id, BRACKETS_NAMES_REFRESH_HOUR))
    return local.hour >= hour and stale(newest_at, now)


__all__ = [
    "LISTS",
    "SEARCH_LIMIT",
    "counts",
    "due",
    "local_now",
    "stale",
    "known",
    "labels",
    "list_key",
    "newest",
    "refresh",
    "refreshed_once",
    "running",
    "search",
    "start_refresh",
    "status",
    "upsert",
]
