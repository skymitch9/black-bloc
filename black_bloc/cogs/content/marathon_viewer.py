from __future__ import annotations

import logging
from typing import Any

from ... import marathon as mt
from ... import marathon_feeds as mf
from ... import marathon_viewer as mv
from ...actionlog import log_action
from ...logkinds import VIA_DISCORD, kind_via
from ...marathon_sources import GDQ_HOTFIX, ScheduleError
from ...panels import Outcome, refusal
from ...settings_store import MARATHON_HOTFIX_VIEWER_URL_KEY
from .marathon import UNREADABLE, cog_of, runs_of

log = logging.getLogger(__name__)

VIEWER_OFF_CODE = "viewer_off"
NOT_HOTFIX_CODE = "not_hotfix"


def page_of(bot: Any, guild: Any) -> str:
    return str(bot.store.get(guild.id, MARATHON_HOTFIX_VIEWER_URL_KEY) or "").strip()


async def viewer_of(
    bot: Any, guild: Any, *, force: bool = False, with_rows: bool = False
) -> tuple[Any, str | None]:
    """(the viewer as last read, what went wrong this time). A blank link is (None, None); a
    failed read answers the last good copy of the same page and never raises."""
    page = page_of(bot, guild)
    cog = cog_of(bot)
    read = getattr(getattr(cog, "client", None), "viewer", None)
    if not page or not callable(read):
        return (None, None)
    cache = mv.cache_of(cog)
    async with cache.lock:
        now = cog.clock()
        if not force and (cache.fresh(page, now) or cache.waiting(page, now)):
            return (cache.copy_for(page), cache.trouble if cache.waiting(page, now) else None)
        try:
            viewer = await read(page, with_rows=with_rows)
        except ScheduleError as exc:
            why = str(exc)[:300]
        except Exception as exc:
            log.exception("marathon: the viewer read broke")
            why = type(exc).__name__
        else:
            cache.keep(viewer, now)
            return (viewer, None)
        cache.failed(page, why, now)
        if cache.said != (page, why):
            cache.said = (page, why)
            await log_action(
                bot,
                guild,
                "marathon.viewer_failed",
                details={
                    "page": page[:300],
                    "reason": why,
                    "kept_copy": cache.copy_for(page) is not None,
                },
            )
        return (cache.copy_for(page), why)


def found_words(found: dict[str, Any]) -> str:
    said = [
        mv.READ_FOUND.format(
            rows=mv.NO_ROWS if found["rows"] is None else found["rows"],
            hosts=found["hosts"],
            events=len(found["events"]),
        )
    ]
    if found["rows_trouble"]:
        said.append(mv.ROWS_TROUBLE.format(why=found["rows_trouble"]))
    for one in found["events"]:
        said.append(mv.EVENT_READ.format(label=one["label"]))
    for one in found["skipped"]:
        said.append(mv.EVENT_SKIPPED.format(label=one["label"], why=one["why"]))
    return " ".join(said)


async def read_now(
    bot: Any, guild: Any, actor: Any, feed: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    """Staff read the viewer page at once; the answer says what was found, or what failed."""
    if feed["source"] != mf.HOTFIX_FEED:
        return refusal(mv.NOT_HOTFIX.format(name=feed["name"]), NOT_HOTFIX_CODE, 409)
    if not page_of(bot, guild):
        return refusal(mv.VIEWER_OFF, VIEWER_OFF_CODE, 409)
    viewer, trouble = await viewer_of(bot, guild, force=True, with_rows=True)
    if trouble is not None or viewer is None:
        return refusal(mv.VIEWER_UNREADABLE.format(why=trouble or "?"), UNREADABLE, 502)
    found = mv.summary(viewer)
    await log_action(
        bot,
        guild,
        kind_via("marathon.viewer_read", via),
        actor=actor,
        details={
            "feed_id": feed["id"],
            "page": viewer.page[:300],
            "rows": found["rows"],
            "hosts": found["hosts"],
            "events": [one["label"] for one in found["events"]],
            "skipped": found["skipped"],
            "via": via,
        },
    )
    return Outcome(True, found_words(found), value=found)


def stored_logins(rows: Any) -> dict[str, str]:
    """The viewer's host table as the stored runs last held it."""
    found: dict[str, str] = {}
    for row in rows or ():
        for one in mt.people_of(row):
            login = str(one.get("sheet_login") or one.get("login") or "")
            if one.get("login_from") == mv.FROM_VIEWER and login:
                found.setdefault(mt.runner_key(one.get("name")), login)
    return found


async def host_logins(
    bot: Any, guild: Any, marathon: Any, runs: list[Any], rows: Any, viewer: Any
) -> list[Any]:
    """Hosts take the viewer table's Twitch names — the stored ones while the viewer cannot be
    read; a login not stored yet is logged."""
    known = stored_logins(rows)
    found, filled = mv.with_host_logins(runs, known if viewer is None else viewer.hosts)
    fresh = {
        name: login for name, login in filled.items() if known.get(mt.runner_key(name)) != login
    }
    if fresh:
        await log_action(
            bot,
            guild,
            "marathon.viewer_logins",
            details={
                "marathon_id": marathon["id"],
                "name": marathon["name"],
                "page": page_of(bot, guild)[:300],
                "hosts": [{"name": name, "login": login} for name, login in fresh.items()],
            },
        )
    return found


async def decorated(bot: Any, guild: Any, marathon: Any, runs: list[Any]) -> list[Any]:
    """A Hotfix marathon's runs with what the viewer adds. A blank link adds nothing; a viewer
    that cannot be read keeps what the stored runs last took from it; anything going wrong here
    leaves the GDQ sheet's runs exactly as they were read."""
    if marathon["source"] != GDQ_HOTFIX or not runs or not page_of(bot, guild):
        return runs
    try:
        viewer, trouble = await viewer_of(bot, guild)
        if viewer is None and trouble is None:
            return runs
        rows = await runs_of(bot.db, marathon["id"])
        return await host_logins(bot, guild, marathon, runs, rows, viewer)
    except Exception:
        log.exception("marathon: the viewer could not be laid over %s", marathon["id"])
        return runs


__all__ = ["decorated", "found_words", "page_of", "read_now", "stored_logins", "viewer_of"]
