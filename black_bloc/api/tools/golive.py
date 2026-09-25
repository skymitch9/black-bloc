from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Request

from ... import pings
from ... import spotlight as spot
from ...cogs.content.golive import (
    LINK_TAKEN,
    all_links,
    all_optouts,
    clean_login,
    get_link,
    link_channel,
    link_from_history,
    opt_in,
    opt_out,
    recent_sessions,
    unlink_channel,
)
from ...cogs.content.marathon_channels import set_marathons
from ...cogs.content.spotlight import (
    add_ping_window,
    bump_now,
    changed_spotlight,
    channel_by_id,
    channels_for,
    forget_spotlight,
    link_youtube,
    open_session,
    ping_wording_for,
    remove_ping_window,
    set_ping_mode,
    spotlight_channel,
    unlink_youtube,
    windows_for,
    windows_in_guild,
    wording_for,
)
from ...cogs.content.spotlight import recent_sessions as recent_spotlight_sessions
from ...golive import optout_said
from ...logkinds import VIA_WEBSITE
from ...marathon_channels import takes_marathons
from ...settings_store import (
    DEFAULT_TIMEZONE_KEY,
    SPOTLIGHT_BAD_DATE_KEY,
    SPOTLIGHT_BUMP_HOURS_KEY,
    SPOTLIGHT_END_BEFORE_START_KEY,
)
from ..auth import Refused, staff_dependency
from ..names import resolve_one
from ..writes import (
    actor_for,
    require_db,
    require_guild,
    wanted_id,
    writer_dependency,
)

log = logging.getLogger(__name__)

SESSIONS_DEFAULT_LIMIT = 50
SESSIONS_MAX_LIMIT = 200

NOT_LINKED = (
    "**{user_id}** has no Twitch account linked, so there was nothing to unlink. The links table "
    "shows who has one."
)
NOT_OPTED_OUT = (
    "**{user_id}** was not opted out, so there was nothing to undo. The opt-outs table lists "
    "everyone who is."
)
BAD_LOGIN = (
    "**{given}** is not a Twitch channel name Black Bloc can use, so nothing was linked. Give the "
    "name out of the channel's own address — letters, numbers and underscores, 25 at most."
)
LINKED = (
    "**{name}** is linked to twitch.tv/{login}. Black Bloc did not check that channel exists — it "
    "finds that out the first time it looks for a stream."
)
OPTED_OUT = "**{name}** is opted out, so no stream of theirs is announced from now on."
OPTED_IN = (
    "**{name}** is no longer opted out, so their streams can be announced again. A stream they "
    "are already running is not announced after the fact; the next one they start is."
)
SPOTLIGHT_SESSIONS = 5
BAD_DAYS = (
    "**{given}** is not a number of days, so nothing was changed. Give a whole number of "
    "days, or say it is kept for ever."
)
SPOTLIGHT_CHANGED = "**{login}** now runs {when}."
SPOTLIGHT_BUMPED = "Reminded the go-live channel that **{login}** is still live."


def with_name(guild: Any, user_id: Any) -> dict[str, Any]:
    return {
        "user_id": str(user_id),
        "user_name": resolve_one(guild, user_id)["display_name"],
    }


def link_row(guild: Any, row: Any) -> dict[str, Any]:
    return with_name(guild, row["user_id"]) | {
        "twitch_login": row["twitch_login"],
        "twitch_user_id": row["twitch_user_id"],
        "linked_at": row["linked_at"],
    }


def session_row(guild: Any, row: Any) -> dict[str, Any]:
    return with_name(guild, row["user_id"]) | {
        "id": row["id"],
        "source": row["source"],
        "url": row["url"],
        "game": row["game"],
        "title": row["title"],
        "platform": row["platform"],
        "also_source": row["also_source"],
        "also_url": row["also_url"],
        "also_platform": row["also_platform"],
        "started_at": row["started_at"],
        "ended_at": row["ended_at"],
        "mode": row["mode"],
        "announced_message_id": (
            str(row["announced_message_id"]) if row["announced_message_id"] else None
        ),
    }


def spotlight_session_row(row: Any) -> dict[str, Any]:
    return {
        "id": row["id"],
        "started_at": row["started_at"],
        "ended_at": row["ended_at"],
        "title": row["title"],
        "game": row["game"],
        "url": row["url"],
        "mode": row["mode"],
        "bump_count": row["bump_count"],
        "announced_message_id": (
            str(row["announced_message_id"]) if row["announced_message_id"] else None
        ),
    }


def window_row(window: Any, tz_name: Any = None) -> dict[str, Any]:
    return {
        "id": window["id"],
        "spotlight_id": window["spotlight_id"],
        "starts_at": window["starts_at"],
        "ends_at": window["ends_at"],
        "note": window["note"],
        "source": window["source"],
        "source_id": window["source_id"],
        "source_words": spot.window_source_words(window) or None,
        "staff": spot.is_staff_window(window),
        "open": spot.window_is_open(window),
        "line": spot.window_line(window, None, tz_name),
        "added_by": str(window["added_by"]) if window["added_by"] else None,
        "added_at": window["added_at"],
    }


def _ranged(said: dict[str, Any]) -> dict[str, Any]:
    return {name: said[name] for name in ("template", "kept_template") if name in said}


def spotlight_row(
    guild: Any,
    row: Any,
    live: Any,
    sessions: list[Any],
    held: Any = None,
    said: dict[str, Any] | None = None,
    windows: list[Any] | None = None,
    pinged: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """A spotlight as the Go-live page reads it: a streamer row with no member behind it."""
    said = dict(said or {})
    pinged = dict(pinged or {})
    tz_name = pinged.pop("tz_name", None)
    windows = list(windows or [])
    role = guild.get_role(int(held["role_id"])) if held is not None else None
    return {
        "role_id": str(held["role_id"]) if held is not None else None,
        "role": role.name if role is not None else None,
        "role_wearers": len(getattr(role, "members", ()) or ()) if role is not None else None,
        "id": row["id"],
        "twitch_login": row["twitch_login"],
        "display_name": row["display_name"] or row["twitch_login"],
        "note": row["note"],
        "added_by": str(row["added_by"]) if row["added_by"] else None,
        "added_by_name": (
            resolve_one(guild, row["added_by"])["display_name"] if row["added_by"] else None
        ),
        "added_at": row["added_at"],
        "starts_at": spot.starts_at_of(row),
        "expires_at": row["expires_at"],
        "kept": spot.keeps_forever(row),
        "scheduled": spot.is_scheduled(row),
        "until": spot.until_words(row),
        "range": spot.range_words(row, **_ranged(said)),
        "announced": spot.announced_words(row, **said),
        "bump_hours": row["bump_hours"],
        "pin": bool(row["pin"]),
        "spotlight": spot.is_spotlit(row),
        "announce": spot.announces(row),
        "opted_out": not spot.announces(row),
        "marathons": takes_marathons(row),
        "youtube_channel_id": spot.youtube_of(row),
        "youtube_handle": row["youtube_handle"],
        "youtube_url": spot.youtube_url(spot.youtube_of(row)),
        "event_id": row["event_id"],
        "url": spot.channel_url(row["twitch_login"]),
        "live": live is not None,
        "session": spotlight_session_row(live) if live is not None else None,
        "sessions": [spotlight_session_row(one) for one in sessions],
        "ping_mode": spot.ping_mode_of(row),
        "pinging": spot.pings_now(row, windows),
        "ping_state": spot.ping_state_words(row, windows, None, tz_name, **pinged),
        "windows": [window_row(one, tz_name) for one in windows],
    }


async def spotlight_rows(bot: Any, guild: Any) -> list[dict[str, Any]]:
    recent = await recent_spotlight_sessions(bot.db, guild.id, 200)
    held = await pings.spotlight_fan_roles(bot.db, guild.id)
    said = wording_for(bot, guild.id)
    pinged = ping_wording_for(bot, guild.id)
    windows = await windows_in_guild(bot.db, guild.id)
    found = []
    for row in await channels_for(bot.db, guild.id):
        mine = [one for one in recent if int(one["spotlight_id"]) == int(row["id"])]
        found.append(
            spotlight_row(
                guild,
                row,
                await open_session(bot.db, row["id"]),
                mine[:SPOTLIGHT_SESSIONS],
                pings.spotlight_row_for(held, row["id"]),
                said,
                [one for one in windows if int(one["spotlight_id"]) == int(row["id"])],
                pinged,
            )
        )
    return found


async def one_spotlight(bot: Any, guild: Any, spotlight_id: int) -> dict[str, Any]:
    row = await channel_by_id(bot.db, spotlight_id)
    if row is None or int(row["guild_id"]) != int(guild.id):
        raise Refused(404, "no_spotlight", spot.NO_SUCH_ROW)
    return spotlight_row(
        guild,
        row,
        await open_session(bot.db, spotlight_id),
        [],
        await pings.get_spotlight_fan_role(bot.db, guild.id, spotlight_id),
        wording_for(bot, guild.id),
        await windows_for(bot.db, spotlight_id),
        ping_wording_for(bot, guild.id),
    )


def wanted_ping_mode(payload: dict[str, Any]) -> Any:
    """Checked BEFORE anything is written, so a bad mode never lands half a PATCH."""
    if "ping_mode" not in payload:
        return None
    given = payload.get("ping_mode")
    wanted = spot.clean_ping_mode(given)
    if wanted is None:
        raise Refused(
            422, spot.BAD_MODE, spot.PING_MODE_REFUSED.format(given=str(given or "")[:40])
        )
    return wanted


def bad_date(bot: Any, guild: Any, given: Any) -> Refused:
    return Refused(
        422,
        "bad_date",
        spot.bad_date_said(given, bot.store.get(guild.id, SPOTLIGHT_BAD_DATE_KEY)),
    )


def read_or_refuse(bot: Any, guild: Any, payload: dict[str, Any], name: str, end: bool) -> Any:
    """A blank or a null CLEARS the date; anything unreadable is 422 in words, never bare."""
    given = payload.get(name)
    read = spot.read_end if end else spot.read_moment
    found, trouble = read(given, payload.get("tz"))
    if trouble is not None:
        raise bad_date(bot, guild, given)
    return found


def refuse_backwards(bot: Any, guild: Any, starts_at: Any, expires_at: Any) -> None:
    if spot.range_problem(starts_at, expires_at) is None:
        return
    raise Refused(
        422,
        "end_before_start",
        spot.end_before_start_said(
            starts_at, expires_at, bot.store.get(guild.id, SPOTLIGHT_END_BEFORE_START_KEY)
        ),
    )


def wanted_days(payload: dict[str, Any]) -> Any:
    given = payload.get("days")
    if given is None or str(given).strip() == "":
        return None
    if not str(given).strip().isdigit():
        raise Refused(400, "bad_days", BAD_DAYS.format(given=str(given)[:40]))
    return int(str(given).strip())


def build_router(bot: Any) -> APIRouter:
    writer = writer_dependency(bot)
    router = APIRouter(
        prefix="/api/golive", tags=["golive"], dependencies=[Depends(staff_dependency(bot))]
    )

    @router.get("/links")
    async def golive_links() -> list[dict[str, Any]]:
        guild = require_guild(bot)
        require_db(bot)
        return [link_row(guild, row) for row in await all_links(bot.db)]

    @router.delete("/links/{user_id}")
    async def golive_unlink(request: Request, user_id: str) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        wanted = wanted_id(user_id)
        removed, _ = await unlink_channel(
            bot, guild, actor_for(bot, who, guild), wanted, via=VIA_WEBSITE
        )
        if not removed:
            raise Refused(404, "not_linked", NOT_LINKED.format(user_id=wanted))
        return {"unlinked": True, "user_id": str(wanted)}

    @router.post("/links")
    async def golive_link(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        wanted = wanted_id(payload.get("user_id"))
        given = str(payload.get("twitch_login") or "")
        outcome, _ = await link_channel(
            bot,
            guild,
            actor_for(bot, who, guild),
            wanted,
            given,
            helix=None,
            via=VIA_WEBSITE,
        )
        if outcome == "bad_login":
            raise Refused(400, "bad_login", BAD_LOGIN.format(given=given[:40] or "nothing"))
        if outcome == "taken":
            raise Refused(409, "link_taken", LINK_TAKEN.format(channel=clean_login(given)))
        row = link_row(guild, await get_link(bot.db, wanted))
        return row | {
            "checked": False,
            "message": LINKED.format(
                name=row["user_name"] or wanted, login=row["twitch_login"]
            ),
        }

    @router.post("/links/sweep")
    async def golive_link_sweep(request: Request) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        found = await link_from_history(
            bot, guild, actor_for(bot, who, guild), via=VIA_WEBSITE
        )
        return {
            "linked": len(found["linked"]),
            "opted_out": len(found["opted_out"]),
            "taken": len(found["taken"]),
            "unreadable": len(found["unreadable"]),
            "left": len(found["left"]),
            "message": found["message"],
        }

    @router.get("/optouts")
    async def golive_optouts() -> list[dict[str, Any]]:
        guild = require_guild(bot)
        require_db(bot)
        return [
            with_name(guild, row["user_id"]) | {"at": row["at"]}
            for row in await all_optouts(bot.db)
        ]

    @router.post("/optouts")
    async def golive_opt_out(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        wanted = wanted_id(payload.get("user_id"))
        _, settled = await opt_out(
            bot, guild, actor_for(bot, who, guild), wanted, via=VIA_WEBSITE
        )
        named = with_name(guild, wanted)
        return named | {
            "opted_out": True,
            "message": optout_said(
                OPTED_OUT.format(name=named["user_name"] or wanted), settled
            ),
        }

    @router.delete("/optouts/{user_id}")
    async def golive_opt_in(request: Request, user_id: str) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        wanted = wanted_id(user_id)
        if not await opt_in(bot, guild, actor_for(bot, who, guild), wanted, via=VIA_WEBSITE):
            raise Refused(404, "not_opted_out", NOT_OPTED_OUT.format(user_id=wanted))
        named = with_name(guild, wanted)
        return named | {
            "opted_out": False,
            "message": OPTED_IN.format(name=named["user_name"] or wanted),
        }

    @router.get("/spotlight")
    async def golive_spotlight_list() -> list[dict[str, Any]]:
        guild = require_guild(bot)
        require_db(bot)
        return await spotlight_rows(bot, guild)

    @router.post("/spotlight")
    async def golive_spotlight_add(
        request: Request, payload: dict[str, Any]
    ) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        given = str(payload.get("twitch_login") or "")
        wanted_youtube = str(payload.get("youtube") or "").strip()
        days = wanted_days(payload)
        keep = bool(payload.get("keep")) or days is None
        starts_at = read_or_refuse(bot, guild, payload, "starts_at", end=False)
        wanted_end: Any = False
        if "expires_at" in payload:
            wanted_end = read_or_refuse(bot, guild, payload, "expires_at", end=True)
            keep = wanted_end is None
        elif starts_at is not None and days is not None:
            wanted_end = spot.expiry_in_days(days)
        if wanted_end is not False:
            refuse_backwards(bot, guild, starts_at, wanted_end)
        if not str(given).strip() and wanted_youtube:
            raise Refused(
                400,
                "needs_twitch",
                spot.NEEDS_A_TWITCH_NAME.format(given=wanted_youtube[:60]),
            )
        outcome, row = await spotlight_channel(
            bot,
            guild,
            actor_for(bot, who, guild),
            given,
            days=days,
            keep=keep,
            expires_at=wanted_end,
            starts_at=starts_at,
            pin=payload.get("pin"),
            bump_hours=payload.get("bump_hours"),
            note=payload.get("note"),
            spotlight=payload.get("spotlight"),
            announce=payload.get("announce", True),
            via=VIA_WEBSITE,
        )
        if outcome == "bad_login":
            raise Refused(
                400, "bad_login", spot.BAD_LOGIN.format(given=given[:40] or "nothing")
            )
        if outcome == "already":
            raise Refused(
                409,
                "already_spotlit",
                spot.ALREADY_SPOTLIT.format(login=spot.clean_login(given) or given[:25]),
            )
        said = ""
        if wanted_youtube:
            linked, fresh, said = await link_youtube(
                bot,
                guild,
                actor_for(bot, who, guild),
                row["id"],
                wanted_youtube,
                via=VIA_WEBSITE,
            )
            if linked == "linked" and fresh is not None:
                row = fresh
        hours = spot.bump_hours_for(row, bot.store.get(guild.id, SPOTLIGHT_BUMP_HOURS_KEY))
        worded = spot.added_said(row, hours, **wording_for(bot, guild.id))
        return await one_spotlight(bot, guild, row["id"]) | {
            "message": f"{worded} {said}".strip()
        }

    @router.patch("/spotlight/{spotlight_id}")
    async def golive_spotlight_change(
        request: Request, spotlight_id: int, payload: dict[str, Any]
    ) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        seen = await one_spotlight(bot, guild, spotlight_id)
        ping_mode = wanted_ping_mode(payload)
        fields: dict[str, Any] = {}
        starts_at = seen["starts_at"]
        expires_at = seen["expires_at"]
        if "starts_at" in payload:
            starts_at = read_or_refuse(bot, guild, payload, "starts_at", end=False)
            fields["starts_at"] = starts_at
        if payload.get("keep") is True:
            expires_at = None
            fields["expires_at"] = None
        elif "expires_at" in payload:
            expires_at = read_or_refuse(bot, guild, payload, "expires_at", end=True)
            fields["expires_at"] = expires_at
        elif payload.get("days") is not None:
            expires_at = spot.expiry_in_days(wanted_days(payload))
            fields["expires_at"] = expires_at
        if "starts_at" in fields or "expires_at" in fields:
            refuse_backwards(bot, guild, starts_at, expires_at)
        if "bump_hours" in payload:
            fields["bump_hours"] = payload["bump_hours"] or None
        if "pin" in payload:
            fields["pin"] = 1 if payload["pin"] else 0
        if "note" in payload:
            fields["note"] = payload["note"] or None
        if "spotlight" in payload:
            fields["spotlight"] = 1 if payload["spotlight"] else 0
        if "announce" in payload:
            fields["announce"] = 1 if payload["announce"] else 0
        who_acts = actor_for(bot, who, guild)
        said = None
        fresh: Any = None
        if "youtube" in payload:
            given = str(payload["youtube"] or "").strip()
            move = unlink_youtube if not given else link_youtube
            outcome, fresh, said = await (
                move(bot, guild, who_acts, spotlight_id, via=VIA_WEBSITE)
                if not given
                else move(bot, guild, who_acts, spotlight_id, given, via=VIA_WEBSITE)
            )
            if outcome == "no_row":
                raise Refused(404, "no_spotlight", spot.NO_SUCH_ROW)
            if outcome == "bad_channel":
                raise Refused(400, "bad_channel", said)
            if outcome == "no_cog":
                raise Refused(503, "no_cog", said)
            if outcome == "not_linked":
                raise Refused(404, "not_linked", said)
        if "marathons" in payload:
            fresh, marathons_said = await set_marathons(
                bot, guild, who_acts, spotlight_id, bool(payload["marathons"]), via=VIA_WEBSITE
            )
            if fresh is None:
                raise Refused(404, "no_spotlight", spot.NO_SUCH_ROW)
            said = " ".join(one for one in (said, marathons_said) if one) or None
        if ping_mode is not None:
            outcome, fresh, moded = await set_ping_mode(
                bot, guild, who_acts, spotlight_id, ping_mode, via=VIA_WEBSITE
            )
            if outcome == "no_row":
                raise Refused(404, "no_spotlight", spot.NO_SUCH_ROW)
            said = said or moded
        settled = None
        if fields or said is None:
            fresh, settled = await changed_spotlight(
                bot, guild, who_acts, spotlight_id, via=VIA_WEBSITE, **fields
            )
        if fresh is None:
            raise Refused(404, "no_spotlight", spot.NO_SUCH_ROW)
        if said is None and "announce" in payload:
            said = spot.announce_said(fresh, settled)
        elif said is None and "spotlight" in payload:
            said = spot.spotlight_said(fresh, settled)
        elif said is None and ("starts_at" in fields or "expires_at" in fields):
            said = spot.dates_said(fresh, **wording_for(bot, guild.id))
        return await one_spotlight(bot, guild, spotlight_id) | {
            "message": said
            or SPOTLIGHT_CHANGED.format(
                login=fresh["twitch_login"], when=spot.until_words(fresh)
            )
        }

    @router.delete("/spotlight/{spotlight_id}")
    async def golive_spotlight_remove(request: Request, spotlight_id: int) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        gone = await forget_spotlight(
            bot, guild, actor_for(bot, who, guild), spotlight_id, via=VIA_WEBSITE
        )
        if gone is None:
            raise Refused(404, "no_spotlight", spot.NO_SUCH_ROW)
        return {
            "id": spotlight_id,
            "twitch_login": gone["twitch_login"],
            "removed": True,
            "message": spot.REMOVED.format(login=gone["twitch_login"]),
        }

    @router.post("/spotlight/{spotlight_id}/bump")
    async def golive_spotlight_bump(request: Request, spotlight_id: int) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        await one_spotlight(bot, guild, spotlight_id)
        outcome, row = await bump_now(
            bot, guild, actor_for(bot, who, guild), spotlight_id, via=VIA_WEBSITE
        )
        if outcome == "no_row":
            raise Refused(404, "no_spotlight", spot.NO_SUCH_ROW)
        if outcome == "not_live":
            raise Refused(409, "not_live", spot.NOT_LIVE.format(login=row["twitch_login"]))
        if outcome == "no_cog":
            raise Refused(503, "no_cog", spot.NO_COG.format(login=row["twitch_login"]))
        if outcome == "bump_failed":
            raise Refused(
                502,
                "bump_failed",
                spot.BUMP_FAILED.format(login=row["twitch_login"], reason=spot.NO_CHANNEL),
            )
        return await one_spotlight(bot, guild, spotlight_id) | {
            "bumped": True,
            "message": SPOTLIGHT_BUMPED.format(login=row["twitch_login"]),
        }

    @router.get("/spotlight/{spotlight_id}/windows")
    async def golive_spotlight_windows(spotlight_id: int) -> list[dict[str, Any]]:
        guild = require_guild(bot)
        require_db(bot)
        seen = await one_spotlight(bot, guild, spotlight_id)
        return seen["windows"]

    @router.post("/spotlight/{spotlight_id}/windows")
    async def golive_spotlight_window_add(
        request: Request, spotlight_id: int, payload: dict[str, Any]
    ) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        await one_spotlight(bot, guild, spotlight_id)
        starts_at = read_or_refuse(bot, guild, payload, "starts_at", end=False)
        ends_at = read_or_refuse(bot, guild, payload, "ends_at", end=False)
        outcome, _, window, said = await add_ping_window(
            bot,
            guild,
            actor_for(bot, who, guild),
            spotlight_id,
            starts_at,
            ends_at,
            payload.get("note"),
            via=VIA_WEBSITE,
        )
        if outcome == "no_row":
            raise Refused(404, "no_spotlight", said)
        if window is None:
            raise Refused(422, str(outcome), said)
        tz_name = bot.store.get(guild.id, DEFAULT_TIMEZONE_KEY)
        return await one_spotlight(bot, guild, spotlight_id) | {
            "window": window_row(window, tz_name),
            "message": said,
        }

    @router.delete("/spotlight/{spotlight_id}/windows/{window_id}")
    async def golive_spotlight_window_remove(
        request: Request, spotlight_id: int, window_id: int
    ) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        await one_spotlight(bot, guild, spotlight_id)
        outcome, _, _, said = await remove_ping_window(
            bot, guild, actor_for(bot, who, guild), spotlight_id, window_id, via=VIA_WEBSITE
        )
        if outcome == "no_row":
            raise Refused(404, "no_spotlight", said)
        if outcome == "no_window":
            raise Refused(404, "no_window", said)
        if outcome == "not_staff":
            raise Refused(409, "not_staff_window", said)
        return await one_spotlight(bot, guild, spotlight_id) | {
            "removed": True,
            "window_id": int(window_id),
            "message": said,
        }

    @router.get("/sessions")
    async def golive_sessions(limit: int = SESSIONS_DEFAULT_LIMIT) -> list[dict[str, Any]]:
        guild = require_guild(bot)
        require_db(bot)
        wanted = max(1, min(int(limit), SESSIONS_MAX_LIMIT))
        return [
            session_row(guild, row) for row in await recent_sessions(bot.db, guild.id, wanted)
        ]

    return router
