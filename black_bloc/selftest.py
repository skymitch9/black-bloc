from __future__ import annotations

import inspect
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

import discord

from . import personas
from .actionlog import as_details, log_action
from .api.auth import Refused
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
    PERSONALITY_POOL_PEER_URL,
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
RUNNER_CHECK = "the self-test itself"
RUNNER_FAILED = (
    "The self-test stopped part way through — {detail}. That is a fault in the test rather than "
    "in what it was testing: whatever it had already checked is recorded above, the rest was "
    "never run, and any cards it had posted are still deleted on time. Run it again, and tell a "
    "Lead if it stops in the same place twice."
)

POOL_CHECK = "pool.in_step_with_gabi"
PEER_TIMEOUT_SECONDS = 5
PEER_VERSION_FIELD = "gabi_personality_pool_version"
PEER_TROPES_FIELD = "gabi_personality_tropes"
POOL_FIX = "python scripts/sync_personality_pool.py"
POOL_NO_PEER = "pool v{version} here; no peer address is set, so nothing was asked"
POOL_NO_FIELD = "pool v{version} here; GABI does not say its pool version yet"
POOL_UNREACHABLE = "could not reach GABI's health route ({reason}) — the pool itself is fine"
POOL_BEHIND = (
    "GABI is on personality pool v{theirs}, this bot on v{mine}, so {ahead} is ahead and the two "
    "rosters can differ. Bring them back into step by running `{fix}` and redeploying."
)
POOL_COUNT = (
    "GABI and this bot say the same pool version, and she lists {theirs} moods where this bot has "
    "{mine}. One side's copy is edited rather than synced — run `{fix}` and redeploy."
)
POOL_ROSTER = (
    "GABI and this bot say the same pool version, but her roster reads {theirs} where this bot's "
    "reads {mine}. One side's copy is edited rather than synced — run `{fix}` and redeploy."
)


class PeerUnreachable(RuntimeError):
    """The peer's health route did not answer. Not a pool failure — a network one."""


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


def _takes_a_query(endpoint: Any) -> bool:
    try:
        return bool(inspect.signature(endpoint).parameters)
    except (TypeError, ValueError):
        return False


def read_check(path: str, endpoint: Any) -> Check:
    lookup = _takes_a_query(endpoint)

    async def run(one: Run) -> str:
        try:
            payload = await endpoint()
        except Refused as refusal:
            if lookup:
                return f"refused in words with nothing picked: {refusal.error}"
            raise
        if payload is None:
            raise CheckFailed("answered nothing at all, so the page has nothing to render")
        if isinstance(payload, dict) and not payload:
            if lookup:
                return "200; nothing picked, nothing answered"
            raise CheckFailed("answered an object with no keys at all")
        return f"200; {shape_of(payload)}"

    return Check(f"read.{path}", SELFTEST, run)


def read_checks(bot: Any) -> tuple[Check, ...]:
    return tuple(read_check(path, endpoint) for path, endpoint in readable_routes(bot))


async def fetch_peer(url: str) -> dict[str, Any]:
    """One GET at the peer's health route, wrapped at the boundary so callers catch one type."""
    import aiohttp

    timeout = aiohttp.ClientTimeout(total=PEER_TIMEOUT_SECONDS)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session, session.get(url) as answer:
            answer.raise_for_status()
            found = await answer.json(content_type=None)
    except (TimeoutError, aiohttp.ClientError, OSError, ValueError) as exc:
        raise PeerUnreachable(f"{type(exc).__name__}: {exc}") from exc
    return found if isinstance(found, dict) else {}


async def check_pool(one: Run, *, fetch: Any = None) -> str:
    """Drift between the two bots' rosters, made visible; a network fault is not a drift fault."""
    url = str(one.bot.store.get(one.guild.id, PERSONALITY_POOL_PEER_URL) or "").strip()
    mine = personas.POOL_VERSION
    if not url:
        return POOL_NO_PEER.format(version=mine)
    try:
        payload = await (fetch or fetch_peer)(url)
    except PeerUnreachable as exc:
        return POOL_UNREACHABLE.format(reason=exc)
    theirs = payload.get(PEER_VERSION_FIELD)
    if theirs is None:
        return POOL_NO_FIELD.format(version=mine)
    if int(theirs) != mine:
        ahead = "GABI" if int(theirs) > mine else "this bot"
        raise CheckFailed(
            POOL_BEHIND.format(theirs=int(theirs), mine=mine, ahead=ahead, fix=POOL_FIX)
        )
    said = f"pool v{mine} on both; {len(personas.TROPES)} moods here"
    roster = payload.get(PEER_TROPES_FIELD)
    if roster is None:
        return f"{said}; GABI does not say how many she has"
    if isinstance(roster, (list, tuple)):
        theirs_names = tuple(str(name) for name in roster)
        if theirs_names != personas.POOL_NAMES:
            raise CheckFailed(
                POOL_ROSTER.format(
                    theirs=", ".join(theirs_names) or "nothing",
                    mine=", ".join(personas.POOL_NAMES),
                    fix=POOL_FIX,
                )
            )
        return f"{said}; GABI lists the same {len(theirs_names)}, in the same order"
    if int(roster) != len(personas.TROPES):
        raise CheckFailed(
            POOL_COUNT.format(theirs=int(roster), mine=len(personas.TROPES), fix=POOL_FIX)
        )
    return f"{said}; GABI has the same {int(roster)}"


def pool_checks() -> tuple[Check, ...]:
    return (Check(POOL_CHECK, "chat", check_pool),)


def panel_checks() -> tuple[Check, ...]:
    from .selftest_panels import panel_checks as built

    return built()


def send_checks() -> tuple[Check, ...]:
    from .selftest_panels import send_checks as built

    return built()


def checks_for(bot: Any) -> tuple[Check, ...]:
    """The registry, in the design's order: config, panels, reads, sends."""
    return (
        *config_checks(),
        *panel_checks(),
        *read_checks(bot),
        *pool_checks(),
        *send_checks(),
    )


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
        "AND json_extract(details, '$.run_id') = ? ORDER BY id",
        (int(guild_id), SELFTEST_CHECK, f"web.{SELFTEST_CHECK}", int(run_id)),
    )
    found: list[dict[str, Any]] = []
    for row in await cur.fetchall():
        details = as_details(row["details"]) or {}
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


async def begin(bot: Any, guild: Any, *, actor: Any = None, via: str = VIA_DISCORD) -> Run:
    """The row and the `started` line, so the website's door has a run_id to answer with."""
    found = running(bot, guild.id)
    if found is not None:
        raise SelfTestBusy(busy_sentence(found))
    one = Run(bot=bot, guild=guild, actor=actor, via=via, total=len(checks_for(bot)))
    _mark(bot, guild.id, one)
    try:
        one.run_id = await open_run(bot.db, one)
        await log_action(
            bot,
            guild,
            kind_via(SELFTEST_STARTED, via),
            actor=actor,
            details={"run_id": one.run_id, "checks": one.total, "via": via},
        )
    except Exception:
        _mark(bot, guild.id, None)
        raise
    return one


async def finish(one: Run) -> Run:
    """Every check runs; nothing stops on a failure, and the flag clears whatever happens."""
    try:
        for check in checks_for(one.bot):
            await record(one, await run_one(one, check))
        one.finished_at = datetime.now(UTC)
        await close_run(one.bot.db, one)
        _mark(one.bot, one.guild.id, None)
        await log_action(
            one.bot,
            one.guild,
            kind_via(SELFTEST_FINISHED, one.via),
            actor=one.actor,
            details={
                "run_id": one.run_id,
                "ok": one.ok,
                "failed": one.failed,
                "posted": one.posted,
                "via": one.via,
            },
        )
    finally:
        _mark(one.bot, one.guild.id, None)
    return one


async def close_after_crash(one: Run, detail: str) -> Run:
    """A runner that raises still owes a finished row, a closed run and a sentence saying why."""
    at = datetime.now(UTC)
    said = RUNNER_FAILED.format(detail=detail)
    result = Result(RUNNER_CHECK, SELFTEST, False, said, at.isoformat())
    one.finished_at = at
    try:
        await record(one, result)
        await close_run(one.bot.db, one)
        await log_action(
            one.bot,
            one.guild,
            kind_via(SELFTEST_FINISHED, one.via),
            actor=one.actor,
            details={
                "run_id": one.run_id,
                "ok": one.ok,
                "failed": one.failed,
                "posted": one.posted,
                "detail": result.detail,
                "via": one.via,
            },
        )
    except Exception:
        log.warning("selftest: run %s could not be closed after it failed", one.run_id)
    finally:
        _mark(one.bot, one.guild.id, None)
    return one


async def finish_quietly(one: Run) -> Run:
    """Nothing awaits the website's run, so the runner failing is a recorded run, not a warning."""
    try:
        return await finish(one)
    except Exception as exc:
        log.warning("selftest: the run itself failed", exc_info=True)
        return await close_after_crash(one, f"{type(exc).__name__}: {exc}")


async def run(bot: Any, guild: Any, *, actor: Any = None, via: str = VIA_DISCORD) -> Run:
    """The body the boot and Discord doors call and wait for; the website starts it and lets go."""
    return await finish_quietly(await begin(bot, guild, actor=actor, via=via))


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
    "POOL_BEHIND",
    "POOL_CHECK",
    "POOL_COUNT",
    "POOL_FIX",
    "POOL_NO_FIELD",
    "POOL_NO_PEER",
    "POOL_UNREACHABLE",
    "Check",
    "CheckFailed",
    "PeerUnreachable",
    "RUNNER_CHECK",
    "RUNNER_FAILED",
    "Result",
    "Run",
    "SelfTestBusy",
    "begin",
    "boot_lines",
    "busy_sentence",
    "checks_for",
    "check_pool",
    "checks_of",
    "close_after_crash",
    "config_checks",
    "failures_of",
    "fetch_peer",
    "finish",
    "finish_quietly",
    "on_boot",
    "one_run",
    "pool_checks",
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
