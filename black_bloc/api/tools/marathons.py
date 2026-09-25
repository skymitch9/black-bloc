from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Request

from ... import marathon as mt
from ...cogs.content.marathon import (
    add_next,
    create_marathon,
    dismiss_next,
    event_status_of,
    get_marathon,
    list_marathons,
    look_again,
    make_event_now,
    marathon_windows,
    mark_done,
    mark_live,
    mark_upcoming,
    pair_runner,
    pairing_by_id,
    pairings_of,
    post_board,
    refresh_marathon,
    remove_marathon,
    rename_marathon,
    run_by_id,
    runs_of,
    set_active,
    set_channel,
    shout_now,
    unlink_the_event,
    unpair_runner,
)
from ...cogs.content.marathon_events import (
    default_mode,
    make_run_event_now,
    set_event_mode,
    unlink_run_event,
)
from ...cogs.content.marathon_feeds import get_feed
from ...cogs.content.spotlight import channel_by_id
from ...events import get_event
from ...logkinds import VIA_WEBSITE
from ...marathon_events import MODE_WORDS, MODES
from ...marathon_events import mode_of as event_mode_of
from ...marathon_sources import SOURCE_WORDS, schedule_page
from ...settings_store import (
    MARATHON_LEAD_DAYS_KEY,
    MARATHON_MODE_KEY,
)
from ..auth import Refused, staff_dependency
from ..names import resolve_one
from ..writes import actor_for, require_cog, require_db, require_guild, wanted_id, writer_dependency

log = logging.getLogger(__name__)

COG = "Marathons"
FEATURE = "Marathon schedules"
STATE_WORDS = {
    mt.UPCOMING: "coming up",
    mt.LIVE: "on now",
    mt.DONE: "done",
    mt.DROPPED: "off the schedule",
}
BECAUSE_WORDS = {
    mt.BY_TITLE: "the stream's title",
    mt.BY_SCHEDULE: "the schedule's clock",
    mt.BY_STAFF: "staff",
}
TROUBLE = "could not be read since {when} — {why}"
NEVER_READ = "not read yet"
BAD_ACTIVE = "Say true to read this marathon or false to pause it, so nothing was changed."
BAD_DISMISS = "Say true to dismiss the suggested next event, so nothing was changed."
BAD_MAKE_EVENT = "Say true or false for making it an event, so nothing was added."


async def event_of(bot: Any, row: Any) -> dict[str, Any]:
    """The drawer's Event line: linked (with the event's own status), waiting, or none."""
    event_id = row["event_id"]
    wanted = mt.wants_its_event(row)
    status = await event_status_of(bot, row)
    return {
        "id": event_id,
        "status": status,
        "wanted": wanted,
        "waiting": wanted and not event_id,
        "line": mt.event_line(row, status),
    }


def _id(value: Any) -> str | None:
    return str(value) if value else None


def answered(outcome: Any) -> Any:
    """The shared function's refusal, in its own words, with the status the site expects."""
    if not outcome.ok:
        raise Refused(outcome.status, outcome.code, outcome.message)
    return outcome


def person_row(guild: Any, person: dict[str, Any]) -> dict[str, Any]:
    user_id = person.get("user_id")
    return {
        "name": person.get("name"),
        "login": person.get("login"),
        "part": person.get("part"),
        "user_id": _id(user_id),
        "member_name": resolve_one(guild, user_id)["display_name"] if user_id else None,
    }


def run_row(guild: Any, row: Any, statuses: dict[int, str] | None = None) -> dict[str, Any]:
    ours = mt.is_ours(row)
    state = str(row["state"])
    event_id = row["event_id"]
    return {
        "event_id": event_id or None,
        "event_status": (statuses or {}).get(int(event_id)) if event_id else None,
        "event_unlinked": event_id == 0,
        "id": row["id"],
        "external_id": row["external_id"],
        "order_no": row["order_no"],
        "game": row["game"],
        "category": row["category"],
        "runners_text": row["runners_text"],
        "people": [person_row(guild, one) for one in mt.people_of(row)],
        "scheduled_at": row["scheduled_at"],
        "ends_at": row["ends_at"],
        "previous_scheduled_at": row["previous_scheduled_at"],
        "moved_at": row["moved_at"],
        "moved": bool(row["moved_at"]),
        "state": state,
        "state_word": STATE_WORDS.get(state, state),
        "live_because": row["live_because"],
        "live_because_word": BECAUSE_WORDS.get(str(row["live_because"] or ""), None),
        "ours": ours,
        "shouted": bool(row["shout_message_id"]),
        "shoutable": ours and state in (mt.UPCOMING, mt.LIVE) and not row["shout_message_id"],
        "can_mark_done": state in (mt.UPCOMING, mt.LIVE),
        "can_mark_upcoming": mt.can_mark_upcoming(row),
        "can_mark_live": mt.can_mark_live(row),
        "held": mt.held(row),
        "reminders_sent": mt.marks_of(row),
    }


async def next_row(bot: Any, guild: Any, row: Any, now: datetime) -> dict[str, Any] | None:
    """The Next up card: only a GDQ marathon, and only once it is over or has a record."""
    record = mt.suggestion_of(row)
    over = mt.is_over(row, now)
    if not mt.suggests(row) or (record is None and not over):
        return None
    record = record or {}
    added_id = record.get("added_marathon_id")
    added = await get_marathon(bot.db, guild.id, added_id) if added_id else None
    return {
        "state": mt.next_state(record) if record else None,
        "event_id": record.get("event_id"),
        "short": record.get("short"),
        "name": record.get("name"),
        "datetime": record.get("datetime"),
        "url": record.get("url"),
        "found_at": record.get("found_at"),
        "dismissed_at": record.get("dismissed_at"),
        "added_marathon_id": added_id,
        "added_name": added["name"] if added is not None else None,
        "can_look_again": over,
    }


def pairing_row(guild: Any, row: Any) -> dict[str, Any]:
    return {
        "id": row["id"],
        "marathon_id": row["marathon_id"],
        "everywhere": row["marathon_id"] is None,
        "runner_name": row["runner_name"],
        "user_id": str(row["user_id"]),
        "member_name": resolve_one(guild, row["user_id"])["display_name"],
    }


def trouble_of(row: Any) -> str | None:
    if row["last_fetch_ok"] is None or int(row["last_fetch_ok"]):
        return None
    return TROUBLE.format(when=row["last_fetched_at"] or "", why=row["last_error"] or "")


async def marathon_row(bot: Any, guild: Any, row: Any, runs: Any = None) -> dict[str, Any]:
    db = bot.db
    rows = list(runs) if runs is not None else await runs_of(db, row["id"])
    channel = await channel_by_id(db, int(row["spotlight_id"])) if row["spotlight_id"] else None
    windows = await marathon_windows(db, row["id"])
    now = datetime.now(UTC)
    phase = mt.phase(row, now, lead_days=int(bot.store.get(guild.id, MARATHON_LEAD_DAYS_KEY)))
    upcoming = await next_row(bot, guild, row, now)
    added_by = row["added_by"]
    feed = await get_feed(db, guild.id, row["feed_id"]) if row["feed_id"] else None
    return {
        "id": row["id"],
        "name": row["name"],
        "schedule_url": row["schedule_url"],
        "schedule_page": schedule_page(row["source"], row["source_ref"]) or row["schedule_url"],
        "source": row["source"],
        "source_word": SOURCE_WORDS.get(row["source"], row["source"]),
        "source_ref": row["source_ref"],
        "spotlight_id": row["spotlight_id"],
        "channel_login": channel["twitch_login"] if channel is not None else None,
        "channel_gone": bool(row["spotlight_id"]) and channel is None,
        "starts_at": row["starts_at"],
        "ends_at": row["ends_at"],
        "active": bool(row["active"]),
        "poll_minutes": row["poll_minutes"],
        "phase": phase,
        "phase_word": mt.PHASE_WORDS.get(phase, phase),
        "runs": len([one for one in rows if one["state"] != mt.DROPPED]),
        "ours": len([one for one in rows if one["state"] != mt.DROPPED and mt.is_ours(one)]),
        "last_fetched_at": row["last_fetched_at"],
        "last_fetch_ok": None if row["last_fetch_ok"] is None else bool(row["last_fetch_ok"]),
        "last_error": row["last_error"],
        "fetch_failures": int(row["fetch_failures"] or 0),
        "trouble": trouble_of(row),
        "board_message_id": _id(row["board_message_id"]),
        "board_channel_id": _id(row["board_channel_id"]),
        "board_pinned": bool(row["board_pinned"]),
        "window": (
            {
                "id": windows[0]["id"],
                "starts_at": windows[0]["starts_at"],
                "ends_at": windows[0]["ends_at"],
            }
            if windows
            else None
        ),
        "added_at": row["added_at"],
        "added_by_name": resolve_one(guild, added_by)["display_name"] if added_by else None,
        "feed_id": row["feed_id"],
        "feed_name": feed["name"] if feed is not None else None,
        "next": upcoming,
        "next_waiting": bool(upcoming) and upcoming["state"] == mt.NEXT_OPEN,
        "event": await event_of(bot, row),
        "event_mode": event_mode_of(row),
        "event_mode_word": MODE_WORDS[event_mode_of(row)],
    }


async def event_statuses(bot: Any, runs: Any) -> dict[int, str]:
    found: dict[int, str] = {}
    for one in runs:
        if one["event_id"]:
            event = await get_event(bot.db, int(one["event_id"]))
            found[int(one["event_id"])] = str(event["status"]) if event is not None else "gone"
    return found


def event_modes() -> list[dict[str, str]]:
    return [{"value": one, "label": MODE_WORDS[one]} for one in MODES]


def build_router(bot: Any) -> APIRouter:
    writer = writer_dependency(bot)
    router = APIRouter(
        prefix="/api/marathons",
        tags=["marathons"],
        dependencies=[Depends(staff_dependency(bot))],
    )

    async def wanted(guild: Any, marathon_id: Any) -> Any:
        row = await get_marathon(bot.db, guild.id, marathon_id)
        if row is None:
            raise Refused(404, "not_found", mt.NO_SUCH_MARATHON.format(given=str(marathon_id)[:40]))
        return row

    async def wanted_run(marathon: Any, run_id: Any) -> Any:
        row = await run_by_id(bot.db, marathon["id"], run_id)
        if row is None:
            raise Refused(404, "no_such_run", mt.NO_SUCH_RUN.format(name=marathon["name"]))
        return row

    async def detail(guild: Any, marathon_id: Any) -> dict[str, Any]:
        row = await wanted(guild, marathon_id)
        runs = await runs_of(bot.db, row["id"])
        pairings = [
            pairing_row(guild, one)
            for one in await pairings_of(bot.db, guild.id)
            if one["marathon_id"] in (None, row["id"])
        ]
        statuses = await event_statuses(bot, runs)
        return await marathon_row(bot, guild, row, runs) | {
            "run_list": [run_row(guild, one, statuses) for one in runs],
            "pairings": pairings,
            "unmatched": mt.unmatched_names(runs),
        }

    async def people(guild: Any, marathon: Any) -> list[dict[str, Any]]:
        return [
            pairing_row(guild, one)
            for one in await pairings_of(bot.db, guild.id)
            if one["marathon_id"] in (None, marathon["id"])
        ]

    @router.get("")
    async def marathon_list() -> dict[str, Any]:
        guild = require_guild(bot)
        require_db(bot)
        rows = [
            await marathon_row(bot, guild, row) for row in await list_marathons(bot.db, guild.id)
        ]
        return {
            "mode": bot.store.get(guild.id, MARATHON_MODE_KEY),
            "marathons": rows,
            "next_waiting": len([one for one in rows if one["next_waiting"]]),
            "event_mode_default": default_mode(bot, guild.id),
            "event_modes": event_modes(),
        }

    @router.post("")
    async def marathon_create(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        require_cog(bot, COG, FEATURE)
        if payload.get("next_of") not in (None, ""):
            parent = await wanted(guild, payload["next_of"])
            linked = answered(
                await add_next(
                    bot,
                    guild,
                    actor_for(bot, who, guild),
                    parent,
                    event_id=payload.get("event_id"),
                    via=VIA_WEBSITE,
                )
            )
            return await detail(guild, linked.value["id"]) | {"message": linked.message}
        make_event = payload.get("make_event")
        if make_event is not None and not isinstance(make_event, bool):
            raise Refused(422, "bad_make_event", BAD_MAKE_EVENT)
        made = answered(
            await create_marathon(
                bot,
                guild,
                actor_for(bot, who, guild),
                name=payload.get("name"),
                url=payload.get("schedule_url"),
                spotlight_id=payload.get("spotlight_id"),
                make_event=make_event,
                event_mode=payload.get("event_mode"),
                via=VIA_WEBSITE,
            )
        )
        return await detail(guild, made.value["id"]) | {"message": made.message}

    @router.get("/{marathon_id}")
    async def marathon_one(marathon_id: int) -> dict[str, Any]:
        guild = require_guild(bot)
        require_db(bot)
        return await detail(guild, marathon_id)

    @router.patch("/{marathon_id}")
    async def marathon_patch(
        request: Request, marathon_id: int, payload: dict[str, Any]
    ) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        require_cog(bot, COG, FEATURE)
        row = await wanted(guild, marathon_id)
        actor = actor_for(bot, who, guild)
        said: list[str] = []
        if "active" in payload:
            if not isinstance(payload["active"], bool):
                raise Refused(422, "bad_active", BAD_ACTIVE)
            if bool(payload["active"]) != bool(row["active"]):
                done = answered(
                    await set_active(bot, guild, actor, row, payload["active"], via=VIA_WEBSITE)
                )
                said.append(done.message)
        if "spotlight_id" in payload:
            given = payload["spotlight_id"]
            wanted_channel = None if given in (None, "", 0, "0") else wanted_id(given)
            if wanted_channel != row["spotlight_id"]:
                answered(await set_channel(bot, guild, actor, row, wanted_channel, via=VIA_WEBSITE))
        if "name" in payload or "poll_minutes" in payload:
            poll = payload.get("poll_minutes")
            answered(
                await rename_marathon(
                    bot,
                    guild,
                    actor,
                    await wanted(guild, marathon_id),
                    payload.get("name"),
                    "" if "poll_minutes" in payload and poll is None else poll,
                    via=VIA_WEBSITE,
                )
            )
        if "event_mode" in payload:
            done = answered(
                await set_event_mode(
                    bot,
                    guild,
                    actor,
                    await wanted(guild, marathon_id),
                    payload["event_mode"],
                    via=VIA_WEBSITE,
                )
            )
            said.append(done.message)
        if "dismiss_next" in payload:
            if payload["dismiss_next"] is not True:
                raise Refused(422, "bad_dismiss", BAD_DISMISS)
            done = answered(
                await dismiss_next(
                    bot,
                    guild,
                    actor,
                    await wanted(guild, marathon_id),
                    event_id=payload.get("event_id"),
                    via=VIA_WEBSITE,
                )
            )
            said.append(done.message)
        return await detail(guild, marathon_id) | {"message": " ".join(said)}

    @router.delete("/{marathon_id}")
    async def marathon_delete(request: Request, marathon_id: int) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        require_cog(bot, COG, FEATURE)
        row = await wanted(guild, marathon_id)
        done = answered(
            await remove_marathon(bot, guild, actor_for(bot, who, guild), row, via=VIA_WEBSITE)
        )
        return {"removed": True, "id": marathon_id, "message": done.message}

    @router.post("/{marathon_id}/refresh")
    async def marathon_refresh(request: Request, marathon_id: int) -> dict[str, Any]:
        await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        require_cog(bot, COG, FEATURE)
        row = await wanted(guild, marathon_id)
        read = answered(await refresh_marathon(bot, guild, row))
        return await detail(guild, marathon_id) | {
            "message": mt.REFRESHED.format(
                name=row["name"],
                runs=(read.value or {}).get("runs", 0),
                ours=len([one for one in await runs_of(bot.db, row["id"]) if mt.is_ours(one)]),
            )
        }

    @router.post("/{marathon_id}/next")
    async def marathon_next(request: Request, marathon_id: int) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        require_cog(bot, COG, FEATURE)
        row = await wanted(guild, marathon_id)
        done = answered(
            await look_again(bot, guild, actor_for(bot, who, guild), row, via=VIA_WEBSITE)
        )
        return await detail(guild, marathon_id) | {"message": done.message}

    @router.post("/{marathon_id}/event")
    async def marathon_make_event(request: Request, marathon_id: int) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        require_cog(bot, COG, FEATURE)
        row = await wanted(guild, marathon_id)
        done = answered(
            await make_event_now(bot, guild, actor_for(bot, who, guild), row, via=VIA_WEBSITE)
        )
        return await detail(guild, marathon_id) | {"message": done.message}

    @router.delete("/{marathon_id}/event")
    async def marathon_unlink_event(request: Request, marathon_id: int) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        require_cog(bot, COG, FEATURE)
        row = await wanted(guild, marathon_id)
        done = answered(
            await unlink_the_event(bot, guild, actor_for(bot, who, guild), row, via=VIA_WEBSITE)
        )
        return await detail(guild, marathon_id) | {"message": done.message}

    @router.post("/{marathon_id}/board")
    async def marathon_board(request: Request, marathon_id: int) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        require_cog(bot, COG, FEATURE)
        row = await wanted(guild, marathon_id)
        done = answered(
            await post_board(bot, guild, actor_for(bot, who, guild), row, via=VIA_WEBSITE)
        )
        return await detail(guild, marathon_id) | {"message": done.message}

    @router.get("/{marathon_id}/people")
    async def marathon_people(marathon_id: int) -> list[dict[str, Any]]:
        guild = require_guild(bot)
        require_db(bot)
        return await people(guild, await wanted(guild, marathon_id))

    @router.post("/{marathon_id}/people")
    async def marathon_pair(
        request: Request, marathon_id: int, payload: dict[str, Any]
    ) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        require_cog(bot, COG, FEATURE)
        row = await wanted(guild, marathon_id)
        given = payload.get("user_id")
        done = answered(
            await pair_runner(
                bot,
                guild,
                actor_for(bot, who, guild),
                row,
                payload.get("runner_name"),
                wanted_id(given) if given not in (None, "") else None,
                everywhere=bool(payload.get("everywhere")),
                via=VIA_WEBSITE,
            )
        )
        return {"pairings": await people(guild, row), "message": done.message}

    @router.delete("/{marathon_id}/people/{pairing_id}")
    async def marathon_unpair(
        request: Request, marathon_id: int, pairing_id: int
    ) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        require_cog(bot, COG, FEATURE)
        row = await wanted(guild, marathon_id)
        pairing = await pairing_by_id(bot.db, guild.id, pairing_id)
        if pairing is None or pairing["marathon_id"] not in (None, row["id"]):
            raise Refused(404, "no_such_pairing", mt.NO_SUCH_PAIRING)
        done = answered(
            await unpair_runner(
                bot, guild, actor_for(bot, who, guild), row, pairing, via=VIA_WEBSITE
            )
        )
        return {"pairings": await people(guild, row), "message": done.message}

    @router.post("/{marathon_id}/runs/{run_id}/shout")
    async def marathon_shout(request: Request, marathon_id: int, run_id: int) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        require_cog(bot, COG, FEATURE)
        row = await wanted(guild, marathon_id)
        run = await wanted_run(row, run_id)
        done = answered(
            await shout_now(bot, guild, actor_for(bot, who, guild), row, run, via=VIA_WEBSITE)
        )
        return {
            "run": run_row(guild, await run_by_id(bot.db, row["id"], run_id)),
            "message": done.message,
        }

    @router.post("/{marathon_id}/runs/{run_id}/done")
    async def marathon_run_done(request: Request, marathon_id: int, run_id: int) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        require_cog(bot, COG, FEATURE)
        row = await wanted(guild, marathon_id)
        run = await wanted_run(row, run_id)
        done = answered(
            await mark_done(bot, guild, actor_for(bot, who, guild), row, run, via=VIA_WEBSITE)
        )
        return {
            "run": run_row(guild, await run_by_id(bot.db, row["id"], run_id)),
            "message": done.message,
        }

    async def run_step(request: Request, marathon_id: int, run_id: int, shared: Any) -> Any:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        require_cog(bot, COG, FEATURE)
        row = await wanted(guild, marathon_id)
        run = await wanted_run(row, run_id)
        done = answered(
            await shared(bot, guild, actor_for(bot, who, guild), row, run, via=VIA_WEBSITE)
        )
        return {
            "run": run_row(guild, await run_by_id(bot.db, row["id"], run_id)),
            "message": done.message,
        }

    @router.post("/{marathon_id}/runs/{run_id}/event")
    async def marathon_run_event(
        request: Request, marathon_id: int, run_id: int
    ) -> dict[str, Any]:
        return await run_event_step(request, marathon_id, run_id, make_run_event_now)

    @router.delete("/{marathon_id}/runs/{run_id}/event")
    async def marathon_run_unlink(
        request: Request, marathon_id: int, run_id: int
    ) -> dict[str, Any]:
        return await run_event_step(request, marathon_id, run_id, unlink_run_event)

    async def run_event_step(
        request: Request, marathon_id: int, run_id: int, shared: Any
    ) -> dict[str, Any]:
        found = await run_step(request, marathon_id, run_id, shared)
        run = await run_by_id(bot.db, int(marathon_id), run_id)
        return found | {"run": run_row(require_guild(bot), run, await event_statuses(bot, [run]))}

    @router.post("/{marathon_id}/runs/{run_id}/upcoming")
    async def marathon_run_upcoming(
        request: Request, marathon_id: int, run_id: int
    ) -> dict[str, Any]:
        return await run_step(request, marathon_id, run_id, mark_upcoming)

    @router.post("/{marathon_id}/runs/{run_id}/live")
    async def marathon_run_live(request: Request, marathon_id: int, run_id: int) -> dict[str, Any]:
        return await run_step(request, marathon_id, run_id, mark_live)

    return router
