from __future__ import annotations

import logging
from typing import Any

from ... import marathon_feeds as mf
from ... import marathon_viewer as mv
from ...actionlog import log_action
from ...logkinds import VIA_DISCORD, kind_via
from ...marathon_sources import ScheduleError
from ...panels import Outcome, refusal
from ...settings_store import MARATHON_HOTFIX_VIEWER_URL_KEY
from .marathon import UNREADABLE, cog_of

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


__all__ = ["found_words", "page_of", "read_now", "viewer_of"]
