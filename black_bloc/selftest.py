from __future__ import annotations

import inspect
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

import discord

from .actionlog import as_details, log_action
from .logkinds import (
    SELFTEST,
    SELFTEST_CHECK,
    SELFTEST_FINISHED,
    SELFTEST_PURGED,
    SELFTEST_STARTED,
    VIA_BOOT,
    VIA_DISCORD,
    kind_via,
)
from .settings_store import (
    KEY_TYPES,
    SELFTEST_CHANNEL_ID,
    SELFTEST_ON_BOOT,
    SELFTEST_PURGE_MINUTES,
    namespace_of,
)

log = logging.getLogger(__name__)

RUNNING_ATTR = "_selftest_running"
PURGE_CHUNK = 100
API_PREFIX = "/api"
SKIP_PATHS = ("/api/auth/login", "/api/auth/callback", "/api/auth/logout")
CHANNEL_PERMISSIONS = ("view_channel", "send_messages", "embed_links")
DELETES_MESSAGES = ("honeypot", "automod")
DELETE_PERMISSION = "manage_messages"

NOT_SET = "not set"
BOOT_LINE = "selftest: {ok} ok, {failed} failed, {posted} messages posted (purge in {minutes} min)"
BOOT_FAILURE = "selftest: FAILED {name} — {detail}"
BUSY = (
    "A self-test is already running (started {started}, {done} of {total} checks done). Nothing "
    "was started a second time — wait for it to finish, or watch it on the dashboard's Health "
    "page."
)
NO_CHANNEL = (
    "The self-test has nowhere to post: selftest_channel_id is not set and Black Bloc has no "
    "test channel either. Point selftest_channel_id at a channel Black Bloc can talk in, from "
    "the dashboard's Settings page or `/settings` ▸ **A setting group…** ▸ **core**."
)
NO_RUN = (
    "Black Bloc has no self-test run numbered {run_id} for this server, so there was nothing to "
    "purge. Open the Health page to see the runs it does have."
)


class SelfTestBusy(RuntimeError):
    """A second start arrived while a run was going; the message is what a person is told."""


class CheckFailed(RuntimeError):
    """A check said no. The sentence is what the log row and the boot line carry."""


@dataclass(frozen=True)
class Check:
    name: str
    feature: str
    run: Callable[[Run], Awaitable[str]]


@dataclass(frozen=True)
class Result:
    name: str
    feature: str
    ok: bool
    detail: str
    at: str


@dataclass
class Run:
    bot: Any
    guild: Any
    actor: Any = None
    via: str = VIA_DISCORD
    run_id: int | None = None
    total: int = 0
    posted: int = 0
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = None
    results: list[Result] = field(default_factory=list)

    @property
    def ok(self) -> int:
        return sum(1 for one in self.results if one.ok)

    @property
    def failed(self) -> int:
        return sum(1 for one in self.results if not one.ok)

    @property
    def failures(self) -> list[Result]:
        return [one for one in self.results if not one.ok]

    async def post(self, **kwargs: Any) -> Any:
        """Every card the test posts goes through here, so nothing is posted unrecorded."""
        channel = selftest_channel(self.bot, self.guild)
        if channel is None:
            raise CheckFailed(NO_CHANNEL)
        message = await channel.send(allowed_mentions=discord.AllowedMentions.none(), **kwargs)
        await remember_message(self.bot.db, self, channel.id, getattr(message, "id", 0))
        self.posted += 1
        return message


def running(bot: Any, guild_id: int) -> Run | None:
    return (getattr(bot, RUNNING_ATTR, None) or {}).get(int(guild_id))


def busy_sentence(found: Run) -> str:
    return BUSY.format(
        started=found.started_at.strftime("%H:%M"),
        done=len(found.results),
        total=found.total or len(found.results),
    )


def _mark(bot: Any, guild_id: int, found: Run | None) -> None:
    book = getattr(bot, RUNNING_ATTR, None)
    if book is None:
        book = {}
        setattr(bot, RUNNING_ATTR, book)
    if found is None:
        book.pop(int(guild_id), None)
    else:
        book[int(guild_id)] = found


def selftest_channel(bot: Any, guild: Any) -> Any:
    """One home for where the cards go; unset falls back to the test channel, never elsewhere."""
    channel_id = bot.store.get(guild.id, SELFTEST_CHANNEL_ID)
    if not channel_id:
        return None
    return guild.get_channel(int(channel_id)) or bot.get_channel(int(channel_id))


def purge_minutes(bot: Any, guild_id: int) -> int:
    return int(bot.store.get(guild_id, SELFTEST_PURGE_MINUTES) or 1)


def runs_on_boot(bot: Any, guild_id: int) -> bool:
    return bool(bot.store.get(guild_id, SELFTEST_ON_BOOT))


# --- the checks -----------------------------------------------------------------------------------


def target_keys() -> tuple[tuple[str, str], ...]:
    """Every channel/role key, read off the registry's own type table rather than hand-listed."""
    return tuple(
        (key, kind) for key, kind in KEY_TYPES.items() if kind in ("channel", "role")
    )


def wanted_permissions(key: str) -> tuple[str, ...]:
    if namespace_of(key) in DELETES_MESSAGES:
        return (*CHANNEL_PERMISSIONS, DELETE_PERMISSION)
    return CHANNEL_PERMISSIONS


def bot_member(guild: Any) -> Any:
    return getattr(guild, "me", None)


async def check_role_key(one: Run, key: str) -> str:
    value = one.bot.store.get(one.guild.id, key)
    if not value:
        return NOT_SET
    role = one.guild.get_role(int(value))
    if role is None:
        raise CheckFailed(f"role {value} is not in this server any more")
    return f"{role.name} ({role.id})"


async def check_channel_key(one: Run, key: str) -> str:
    value = one.bot.store.get(one.guild.id, key)
    if not value:
        return NOT_SET
    channel = one.guild.get_channel(int(value)) or one.bot.get_channel(int(value))
    if channel is None:
        raise CheckFailed(f"channel {value} is not visible to Black Bloc any more")
    wanted = wanted_permissions(key)
    me = bot_member(one.guild)
    if me is None:
        return f"#{getattr(channel, 'name', value)} ({value}); permissions not readable"
    allowed = channel.permissions_for(me)
    missing = [name for name in wanted if not getattr(allowed, name, False)]
    if missing:
        raise CheckFailed(
            f"Black Bloc is missing {', '.join(missing)} in #{getattr(channel, 'name', value)}"
        )
    return f"#{getattr(channel, 'name', value)} ({value}); {', '.join(wanted)}"


def config_check(key: str, kind: str) -> Check:
    async def run(one: Run) -> str:
        if kind == "role":
            return await check_role_key(one, key)
        return await check_channel_key(one, key)

    return Check(f"config.{key}", namespace_of(key), run)


def config_checks() -> tuple[Check, ...]:
    return tuple(config_check(key, kind) for key, kind in target_keys())


def walk_routes(holder: Any, seen: set[int] | None = None) -> list[Any]:
    """FastAPI keeps an included router as ONE entry, so the table is a tree, not a list."""
    seen = set() if seen is None else seen
    if id(holder) in seen:
        return []
    seen.add(id(holder))
    found: list[Any] = []
    for route in getattr(holder, "routes", ()) or ():
        inner = getattr(route, "original_router", None) or getattr(route, "router", None)
        if inner is not None or getattr(route, "routes", None):
            found.extend(walk_routes(inner if inner is not None else route, seen))
            continue
        found.append(route)
    return found


def readable_routes(bot: Any) -> tuple[tuple[str, Any], ...]:
    """The GET routes a page reads: no path parameters, nothing the caller has to fill in."""
    from .api.server import api_app

    found: dict[str, Any] = {}
    for route in walk_routes(api_app(bot)):
        path = str(getattr(route, "path", ""))
        methods = set(getattr(route, "methods", ()) or ())
        endpoint = getattr(route, "endpoint", None)
        if "GET" not in methods or not path.startswith(API_PREFIX) or "{" in path:
            continue
        if path in SKIP_PATHS or endpoint is None or _needs_arguments(endpoint):
            continue
        found.setdefault(path, endpoint)
    return tuple(sorted(found.items(), key=lambda pair: pair[0]))


def _needs_arguments(endpoint: Any) -> bool:
    try:
        spec = inspect.signature(endpoint)
    except (TypeError, ValueError):
        return True
    return any(one.default is inspect.Parameter.empty for one in spec.parameters.values())


def shape_of(payload: Any) -> str:
    """The top-level keys are the shape a page reads; a list says how many rows came back."""
    if isinstance(payload, dict):
        return ", ".join(list(payload)[:8]) or "no keys"
    if isinstance(payload, list):
        return f"{len(payload)} row(s)"
    return type(payload).__name__


def read_check(path: str, endpoint: Any) -> Check:
    async def run(one: Run) -> str:
        payload = await endpoint()
        if payload is None:
            raise CheckFailed("answered nothing at all, so the page has nothing to render")
        if isinstance(payload, dict) and not payload:
            raise CheckFailed("answered an object with no keys at all")
        return f"200; {shape_of(payload)}"

    return Check(f"read.{path}", SELFTEST, run)


def read_checks(bot: Any) -> tuple[Check, ...]:
    return tuple(read_check(path, endpoint) for path, endpoint in readable_routes(bot))


def checks_for(bot: Any) -> tuple[Check, ...]:
    """The registry, in the design's order: config, reads."""
    return (*config_checks(), *read_checks(bot))


CHECKS = config_checks()


# --- persistence ----------------------------------------------------------------------------------


async def open_run(db: Any, one: Run) -> int:
    cur = await db.conn.execute(
        "INSERT INTO selftest_runs(guild_id, started_at, via, actor_id) VALUES (?, ?, ?, ?)",
        (
            one.guild.id,
            one.started_at.isoformat(),
            one.via,
            getattr(one.actor, "id", None),
        ),
    )
    await db.conn.commit()
    return int(cur.lastrowid or 0)


async def close_run(db: Any, one: Run) -> None:
    await db.conn.execute(
        "UPDATE selftest_runs SET finished_at = ?, ok = ?, failed = ?, posted = ? WHERE id = ?",
        (
            (one.finished_at or datetime.now(UTC)).isoformat(),
            one.ok,
            one.failed,
            one.posted,
            one.run_id,
        ),
    )
    await db.conn.commit()


async def remember_message(db: Any, one: Run, channel_id: int, message_id: int) -> None:
    """Written BEFORE the next check runs, so a restart mid-run still knows what to delete."""
    await db.conn.execute(
        "INSERT INTO selftest_messages(run_id, guild_id, channel_id, message_id, posted_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (one.run_id, one.guild.id, int(channel_id), int(message_id), datetime.now(UTC).isoformat()),
    )
    await db.conn.commit()


async def recent_runs(db: Any, guild_id: int, limit: int = 20) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT id, started_at, finished_at, ok, failed, posted, purged_at, via, actor_id "
        "FROM selftest_runs WHERE guild_id = ? ORDER BY id DESC LIMIT ?",
        (int(guild_id), int(limit)),
    )
    return list(await cur.fetchall())


async def one_run(db: Any, guild_id: int, run_id: int) -> Any:
    cur = await db.conn.execute(
        "SELECT id, started_at, finished_at, ok, failed, posted, purged_at, via, actor_id "
        "FROM selftest_runs WHERE guild_id = ? AND id = ?",
        (int(guild_id), int(run_id)),
    )
    return await cur.fetchone()


async def checks_of(db: Any, guild_id: int, run_id: int) -> list[dict[str, Any]]:
    """The check rows come back out of the action log — one write, one row (checklist 34)."""
    cur = await db.conn.execute(
        "SELECT at, kind, details FROM action_log WHERE guild_id = ? AND kind IN (?, ?) "
        "ORDER BY id",
        (int(guild_id), SELFTEST_CHECK, f"web.{SELFTEST_CHECK}"),
    )
    found: list[dict[str, Any]] = []
    for row in await cur.fetchall():
        details = as_details(row["details"]) or {}
        if int(details.get("run_id") or 0) != int(run_id):
            continue
        found.append(
            {
                "name": str(details.get("name") or ""),
                "feature": str(details.get("feature") or SELFTEST),
                "ok": bool(details.get("ok")),
                "detail": str(details.get("detail") or ""),
                "at": row["at"],
            }
        )
    return found


async def failures_of(db: Any, guild_id: int, run_id: int) -> list[dict[str, Any]]:
    return [row for row in await checks_of(db, guild_id, run_id) if not row["ok"]]


async def waiting_messages(db: Any, guild_id: int, run_id: int | None = None) -> list[Any]:
    sql = (
        "SELECT id, run_id, channel_id, message_id, posted_at FROM selftest_messages "
        "WHERE guild_id = ?"
    )
    params: tuple[Any, ...] = (int(guild_id),)
    if run_id is not None:
        sql += " AND run_id = ?"
        params += (int(run_id),)
    cur = await db.conn.execute(f"{sql} ORDER BY id", params)
    return list(await cur.fetchall())


# --- the run --------------------------------------------------------------------------------------


async def record(one: Run, result: Result) -> None:
    one.results.append(result)
    await log_action(
        one.bot,
        one.guild,
        kind_via(SELFTEST_CHECK, one.via),
        actor=one.actor,
        details={
            "run_id": one.run_id,
            "name": result.name,
            "feature": result.feature,
            "ok": result.ok,
            "detail": result.detail,
            "via": one.via,
        },
    )


async def run_one(one: Run, check: Check) -> Result:
    at = datetime.now(UTC).isoformat()
    try:
        detail = await check.run(one)
    except Exception as exc:
        log.warning("selftest: %s failed", check.name, exc_info=True)
        return Result(check.name, check.feature, False, f"{type(exc).__name__}: {exc}", at)
    return Result(check.name, check.feature, True, str(detail), at)


async def run(bot: Any, guild: Any, *, actor: Any = None, via: str = VIA_DISCORD) -> Run:
    """The one body all three doors call: every check runs, nothing stops on a failure."""
    found = running(bot, guild.id)
    if found is not None:
        raise SelfTestBusy(busy_sentence(found))
    checks = checks_for(bot)
    one = Run(bot=bot, guild=guild, actor=actor, via=via, total=len(checks))
    _mark(bot, guild.id, one)
    try:
        one.run_id = await open_run(bot.db, one)
        await log_action(
            bot,
            guild,
            kind_via(SELFTEST_STARTED, via),
            actor=actor,
            details={"run_id": one.run_id, "checks": len(checks), "via": via},
        )
        for check in checks:
            await record(one, await run_one(one, check))
        one.finished_at = datetime.now(UTC)
        await close_run(bot.db, one)
        await log_action(
            bot,
            guild,
            kind_via(SELFTEST_FINISHED, via),
            actor=actor,
            details={
                "run_id": one.run_id,
                "ok": one.ok,
                "failed": one.failed,
                "posted": one.posted,
                "via": via,
            },
        )
    finally:
        _mark(bot, guild.id, None)
    return one


async def on_boot(bot: Any) -> None:
    """The boot door: leftovers first, then one run per guild, then the line a deploy is read by."""
    if not getattr(bot.db, "is_connected", False):
        return
    for guild in list(getattr(bot, "guilds", ()) or ()):
        try:
            await purge(bot, guild, via=VIA_BOOT)
            if not runs_on_boot(bot, guild.id):
                continue
            one = await run(bot, guild, via=VIA_BOOT)
        except Exception as exc:
            log.warning("selftest: the boot run failed — %s: %s", type(exc).__name__, exc)
            continue
        for line in boot_lines(bot, one):
            log.info("%s", line)


def boot_lines(bot: Any, one: Run) -> list[str]:
    """What the hosting log says, so a deploy proves itself without opening Discord."""
    lines = [
        BOOT_LINE.format(
            ok=one.ok,
            failed=one.failed,
            posted=one.posted,
            minutes=purge_minutes(bot, one.guild.id),
        )
    ]
    lines += [
        BOOT_FAILURE.format(name=result.name, detail=result.detail) for result in one.failures
    ]
    return lines


# --- the purge ------------------------------------------------------------------------------------


async def _delete_messages(channel: Any, ids: list[int]) -> int:
    """Bulk first; anything Discord refuses in bulk goes one at a time, 404 counting as gone."""
    gone = 0
    for start in range(0, len(ids), PURGE_CHUNK):
        chunk = ids[start : start + PURGE_CHUNK]
        try:
            await channel.delete_messages([discord.Object(id=one) for one in chunk])
            gone += len(chunk)
            continue
        except Exception as exc:
            log.info("selftest: bulk delete refused (%s); deleting one at a time", exc)
        for message_id in chunk:
            try:
                await channel.get_partial_message(message_id).delete()
            except discord.NotFound:
                pass
            except Exception as exc:
                log.warning("selftest: message %s not deleted — %s", message_id, exc)
                continue
            gone += 1
    return gone


async def _forget(db: Any, row_ids: list[int]) -> None:
    if not row_ids:
        return
    marks = ", ".join("?" for _ in row_ids)
    await db.conn.execute(f"DELETE FROM selftest_messages WHERE id IN ({marks})", tuple(row_ids))
    await db.conn.commit()


async def _stamp_purged(bot: Any, guild: Any, run_id: int, gone: int, via: str) -> None:
    left = await waiting_messages(bot.db, guild.id, run_id)
    if left:
        return
    await bot.db.conn.execute(
        "UPDATE selftest_runs SET purged_at = ? WHERE id = ? AND purged_at IS NULL",
        (datetime.now(UTC).isoformat(), int(run_id)),
    )
    await bot.db.conn.commit()
    await log_action(
        bot,
        guild,
        kind_via(SELFTEST_PURGED, via),
        details={"run_id": int(run_id), "messages": gone, "via": via},
    )


async def purge(
    bot: Any,
    guild: Any,
    *,
    run_id: int | None = None,
    due_only: bool = True,
    via: str = VIA_DISCORD,
) -> int:
    """Delete what the test posted: everything past its minutes, or one run on demand."""
    if not getattr(bot.db, "is_connected", False):
        return 0
    rows = await waiting_messages(bot.db, guild.id, run_id)
    if not rows:
        return 0
    cutoff = datetime.now(UTC) - timedelta(minutes=purge_minutes(bot, guild.id))
    by_run: dict[int, dict[int, list[Any]]] = {}
    for row in rows:
        if due_only and not _older_than(row["posted_at"], cutoff):
            continue
        by_run.setdefault(int(row["run_id"]), {}).setdefault(int(row["channel_id"]), []).append(row)
    gone = 0
    for one_run_id, by_channel in by_run.items():
        went = 0
        for channel_id, found in by_channel.items():
            channel = guild.get_channel(channel_id) or bot.get_channel(channel_id)
            ids = [int(row["message_id"]) for row in found]
            went += await _delete_messages(channel, ids) if channel is not None else len(ids)
            await _forget(bot.db, [int(row["id"]) for row in found])
        gone += went
        await _stamp_purged(bot, guild, one_run_id, went, via)
    return gone


def _older_than(posted_at: Any, cutoff: datetime) -> bool:
    try:
        when = datetime.fromisoformat(str(posted_at))
    except (TypeError, ValueError):
        return True
    if when.tzinfo is None:
        when = when.replace(tzinfo=UTC)
    return when <= cutoff


__all__ = [
    "BOOT_LINE",
    "BUSY",
    "CHECKS",
    "NO_CHANNEL",
    "NO_RUN",
    "Check",
    "CheckFailed",
    "Result",
    "Run",
    "SelfTestBusy",
    "boot_lines",
    "busy_sentence",
    "checks_for",
    "checks_of",
    "config_checks",
    "failures_of",
    "on_boot",
    "one_run",
    "purge",
    "purge_minutes",
    "read_checks",
    "readable_routes",
    "recent_runs",
    "run",
    "running",
    "runs_on_boot",
    "selftest_channel",
    "waiting_messages",
]
