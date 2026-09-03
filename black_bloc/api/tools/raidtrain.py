from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Request

from ...cogs.content.raidtrain import (
    MEMBER_NOT_LINKED,
    counts,
    create_train,
    empty_slot,
    get_train,
    list_trains,
    slots_for,
    swap_holders,
    take_slot,
    twitch_login_of,
)
from ...events import DESCRIPTION_LIMIT, START_IN_THE_PAST, clamp, start_error
from ...golive import parse_ts
from ...raidtrain import (
    CANCELLED,
    LOCKED,
    OPEN,
    SLOT_COUNT_MAX,
    SLOT_COUNT_MIN,
    SLOT_MINUTES_MAX,
    SLOT_MINUTES_MIN,
    SLOT_TAKEN,
    SLOT_UNKNOWN,
    STATUS_WORDS,
    TITLE_LIMIT,
    filled,
    may_move,
    move_refusal,
    render_lineup,
    slot_at,
)
from ...timezones import DEFAULT_TZ, START_EXAMPLE, parse_start
from ..auth import Refused, staff_dependency
from ..names import resolve_one
from ..writes import note, require_cog, require_db, require_guild, wanted_id, writer_dependency

log = logging.getLogger(__name__)

COG = "RaidTrains"
FEATURE = "Raid trains"
SCOPES = ("upcoming", "past", "all")

NO_SUCH_TRAIN = (
    "Black Bloc has no raid train **{train_id}** in this server, so nothing was done. The table "
    "above lists the ones it does have."
)
NO_TITLE = "A raid train needs a title, so nothing was made. Give it one and try again."
BAD_SIZE = (
    "A raid train runs {count_min} to {count_max} slots of {min} to {max} minutes each, so "
    "nothing was made. Discord will not carry a longer lineup in one message."
)
BAD_STATUS = (
    "**{status}** is not a state a raid train can be in. It is one of open, locked, live, done "
    "or cancelled, and only some of those can be reached from where this one is."
)
CREATED = "**{title}** is up with {count} slot(s) of {minutes} minutes each."
ASSIGNED = "Slot #{position} now belongs to {who}."
UNASSIGNED = "Slot #{position} is open again."
NOBODY_THERE = "Slot #{position} is already empty, so there was nothing to take off it."
SWAPPED = "Slots #{a} and #{b} have changed places."
SAME_SLOT = "Those are the same slot, so nothing was changed."
STATUS_SET = "**{title}** is now **{status}**."
CANCEL_NEEDS_REASON = (
    "Cancelling tells everybody who signed up, so it needs a reason to tell them. Type one and "
    "try again."
)


def with_name(guild: Any, user_id: Any) -> dict[str, Any]:
    if user_id is None:
        return {"user_id": None, "user_name": None}
    return {
        "user_id": str(user_id),
        "user_name": resolve_one(guild, user_id)["display_name"],
    }


def slot_row(guild: Any, row: Any) -> dict[str, Any]:
    return with_name(guild, row["user_id"]) | {
        "id": row["id"],
        "position": row["position"],
        "starts_at": row["starts_at"],
        "ends_at": row["ends_at"],
        "twitch_login": row["twitch_login"],
        "claimed_at": row["claimed_at"],
        "assigned_by": (str(row["assigned_by"]) if row["assigned_by"] else None),
        "reminded_at": row["reminded_at"],
        "checked_in_at": row["checked_in_at"],
        "state": "open" if row["user_id"] is None else "taken",
    }


def train_row(guild: Any, row: Any, slots: Any) -> dict[str, Any]:
    rows = list(slots or ())
    return {
        "id": row["id"],
        "title": row["title"],
        "description": row["description"],
        "starts_at": row["starts_at"],
        "slot_minutes": row["slot_minutes"],
        "slot_count": row["slot_count"],
        "status": row["status"],
        "status_word": STATUS_WORDS.get(str(row["status"]), str(row["status"])),
        "filled": filled(rows),
        "slots_total": len(rows),
        "channel_id": (str(row["channel_id"]) if row["channel_id"] else None),
        "lineup_message_id": (
            str(row["lineup_message_id"]) if row["lineup_message_id"] else None
        ),
        "thread_id": (str(row["thread_id"]) if row["thread_id"] else None),
        "scheduled": bool(row["scheduled_event_id"]),
        "cancel_reason": row["cancel_reason"],
        "created_at": row["created_at"],
        "organizer_id": str(row["organizer_id"]),
        "organizer_name": resolve_one(guild, row["organizer_id"])["display_name"],
        "editable": str(row["status"]) in (OPEN, LOCKED),
    }


def build_router(bot: Any) -> APIRouter:
    writer = writer_dependency(bot)
    router = APIRouter(
        prefix="/api/raidtrains",
        tags=["raidtrains"],
        dependencies=[Depends(staff_dependency(bot))],
    )

    async def wanted_train(guild: Any, db: Any, train_id: Any) -> Any:
        row = await get_train(db, guild.id, train_id)
        if row is None:
            raise Refused(404, "not_found", NO_SUCH_TRAIN.format(train_id=train_id))
        return row

    @router.get("/status")
    async def raidtrain_status() -> dict[str, Any]:
        """The sweep's health, the mode and the totals — the Health tab reads the same shape."""
        guild = require_guild(bot)
        db = require_db(bot)
        cog = bot.get_cog(COG) if callable(getattr(bot, "get_cog", None)) else None
        totals = await counts(db, guild.id)
        return {
            "mode": bot.store.get(guild.id, "raidtrain_mode"),
            "channel_id": (
                str(bot.store.get(guild.id, "raidtrain_channel_id") or "") or None
            ),
            "running": bool(cog is not None and cog.sweep.is_running()),
            "last_ok_at": getattr(cog, "last_sweep_ok_at", None),
            "last_error": getattr(cog, "last_sweep_error", None),
            "failures": int(getattr(cog, "sweep_failures", 0) or 0),
            "every_minutes": bot.store.get(guild.id, "raidtrain_poll_minutes"),
            "trains": totals["trains"],
            "upcoming": totals["upcoming"],
            "slots": totals["slots"],
            "claimed": totals["claimed"],
        }

    @router.get("")
    async def raidtrain_list(scope: str = "upcoming") -> list[dict[str, Any]]:
        guild = require_guild(bot)
        db = require_db(bot)
        wanted = scope if scope in SCOPES else "upcoming"
        return [
            train_row(guild, row, await slots_for(db, row["id"]))
            for row in await list_trains(db, guild.id, scope=wanted)
        ]

    @router.get("/{train_id}")
    async def raidtrain_one(train_id: int) -> dict[str, Any]:
        guild = require_guild(bot)
        db = require_db(bot)
        row = await wanted_train(guild, db, train_id)
        slots = await slots_for(db, train_id)
        return train_row(guild, row, slots) | {
            "slots": [slot_row(guild, one) for one in slots],
            "lineup": render_lineup(row, slots),
        }

    @router.post("")
    async def raidtrain_create(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        db = require_db(bot)
        cog = require_cog(bot, COG, FEATURE)
        title = clamp(payload.get("title"), TITLE_LIMIT)
        if not title:
            raise Refused(400, "bad_request", NO_TITLE)
        tz_name = str(payload.get("tz") or DEFAULT_TZ)
        given = str(payload.get("start") or "")
        starts = parse_start(given, tz_name) or parse_ts(given)
        if starts is None:
            raise Refused(400, "bad_start", start_error(given, tz_name, START_EXAMPLE))
        if starts <= datetime.now(UTC):
            raise Refused(
                400,
                "start_in_the_past",
                START_IN_THE_PAST.format(given=clamp(given, 80), tz=tz_name),
            )
        minutes = _whole(
            payload.get("slot_minutes"), bot.store.get(guild.id, "raidtrain_slot_minutes")
        )
        count = _whole(payload.get("slot_count"), 0)
        if not (SLOT_MINUTES_MIN <= minutes <= SLOT_MINUTES_MAX) or not (
            SLOT_COUNT_MIN <= count <= SLOT_COUNT_MAX
        ):
            raise Refused(
                400,
                "bad_size",
                BAD_SIZE.format(
                    min=SLOT_MINUTES_MIN,
                    max=SLOT_MINUTES_MAX,
                    count_min=SLOT_COUNT_MIN,
                    count_max=SLOT_COUNT_MAX,
                ),
            )
        train_id = await create_train(
            db,
            guild.id,
            int(who["id"]),
            title=title,
            description=clamp(payload.get("description"), DESCRIPTION_LIMIT),
            starts_at=starts,
            slot_minutes=minutes,
            slot_count=count,
        )
        await note(
            bot,
            guild,
            "web.raidtrain.create",
            who,
            details={
                "train_id": train_id,
                "title": title,
                "slot_minutes": minutes,
                "slot_count": count,
            },
        )
        await cog.publish_lineup(guild, train_id)
        row = await get_train(db, guild.id, train_id)
        return train_row(guild, row, await slots_for(db, train_id)) | {
            "message": CREATED.format(title=title, count=count, minutes=minutes)
        }

    @router.post("/{train_id}/slots/{position}")
    async def raidtrain_slot(
        request: Request, train_id: int, position: int, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """One route for both halves of a seat: a member id fills it, null empties it."""
        who = await writer(request)
        guild = require_guild(bot)
        db = require_db(bot)
        cog = require_cog(bot, COG, FEATURE)
        train = await wanted_train(guild, db, train_id)
        slots = await slots_for(db, train_id)
        wanted = slot_at(slots, position)
        if wanted is None:
            raise Refused(
                404,
                "no_such_slot",
                SLOT_UNKNOWN.format(position=position, last=len(slots)),
            )
        given = payload.get("member_id")
        if given in (None, "", "null"):
            if not await empty_slot(db, wanted["id"]):
                raise Refused(409, "already_empty", NOBODY_THERE.format(position=position))
            await note(
                bot,
                guild,
                "web.raidtrain.unassign",
                who,
                target=wanted["user_id"],
                details={"train_id": train_id, "position": position},
            )
            said = UNASSIGNED.format(position=position)
        else:
            member_id = wanted_id(given)
            login = await twitch_login_of(db, member_id)
            named = resolve_one(guild, member_id)["display_name"]
            if not login and bot.store.get(guild.id, "raidtrain_require_link"):
                raise Refused(409, "not_linked", MEMBER_NOT_LINKED.format(who=named))
            if wanted["user_id"] is not None:
                await empty_slot(db, wanted["id"])
            if not await take_slot(db, wanted["id"], member_id, login, int(who["id"])):
                raise Refused(409, "slot_taken", SLOT_TAKEN.format(position=position))
            await note(
                bot,
                guild,
                "web.raidtrain.assign",
                who,
                target=member_id,
                details={"train_id": train_id, "position": position, "twitch_login": login},
            )
            said = ASSIGNED.format(position=position, who=named)
        await cog._refresh_lineup(guild, train_id)
        fresh = await slots_for(db, train_id)
        return train_row(guild, train, fresh) | {
            "slots": [slot_row(guild, one) for one in fresh],
            "message": said,
        }

    @router.post("/{train_id}/swap")
    async def raidtrain_swap(
        request: Request, train_id: int, payload: dict[str, Any]
    ) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        db = require_db(bot)
        cog = require_cog(bot, COG, FEATURE)
        train = await wanted_train(guild, db, train_id)
        first, second = _whole(payload.get("a"), 0), _whole(payload.get("b"), 0)
        if first == second:
            raise Refused(400, "bad_request", SAME_SLOT)
        slots = await slots_for(db, train_id)
        one, other = slot_at(slots, first), slot_at(slots, second)
        if one is None or other is None:
            raise Refused(
                404,
                "no_such_slot",
                SLOT_UNKNOWN.format(
                    position=first if one is None else second, last=len(slots)
                ),
            )
        await swap_holders(db, one, other)
        await note(
            bot,
            guild,
            "web.raidtrain.swap",
            who,
            details={"train_id": train_id, "a": first, "b": second},
        )
        await cog._refresh_lineup(guild, train_id)
        fresh = await slots_for(db, train_id)
        return train_row(guild, train, fresh) | {
            "slots": [slot_row(guild, one) for one in fresh],
            "message": SWAPPED.format(a=first, b=second),
        }

    @router.post("/{train_id}/status")
    async def raidtrain_status_set(
        request: Request, train_id: int, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Lock, unlock and cancel all ask the same transition table the buttons in Discord ask."""
        who = await writer(request)
        guild = require_guild(bot)
        db = require_db(bot)
        cog = require_cog(bot, COG, FEATURE)
        train = await wanted_train(guild, db, train_id)
        wanted = str(payload.get("status") or "").strip().lower()
        if wanted not in STATUS_WORDS:
            raise Refused(400, "bad_status", BAD_STATUS.format(status=wanted or "(nothing)"))
        if not may_move(train["status"], wanted):
            raise Refused(409, "bad_move", move_refusal(train["status"], wanted))
        reason = clamp(payload.get("reason"), DESCRIPTION_LIMIT)
        if wanted == CANCELLED:
            if not reason:
                raise Refused(400, "bad_request", CANCEL_NEEDS_REASON)
            actor = guild.get_member(int(who["id"])) or int(who["id"])
            await cog.cancel_train(guild, train, reason, actor)
        else:
            from ...cogs.content.raidtrain import set_status

            await set_status(db, train_id, wanted)
            await note(
                bot,
                guild,
                "web.raidtrain.lock" if wanted == LOCKED else "web.raidtrain.unlock",
                who,
                details={"train_id": train_id, "title": train["title"]},
            )
            await cog._refresh_lineup(guild, train_id)
        fresh = await get_train(db, guild.id, train_id)
        slots = await slots_for(db, train_id)
        return train_row(guild, fresh, slots) | {
            "slots": [slot_row(guild, one) for one in slots],
            "message": STATUS_SET.format(title=train["title"], status=wanted),
        }

    return router


def _whole(given: Any, fallback: int) -> int:
    try:
        return int(str(given).strip())
    except (TypeError, ValueError):
        return int(fallback)
