from __future__ import annotations

import logging
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Request

from ...birthdays import (
    date_problem,
    month_day_text,
    year_problem,
)
from ...cogs.community.birthdays import (
    delete_birthday,
    rows_for_guild,
    save_birthday,
    set_opted_in,
)
from ..auth import Refused, staff_dependency
from ..names import as_id, resolve_one
from ..writes import (
    note,
    require_db,
    require_guild,
    wanted_id,
    writer_dependency,
)

log = logging.getLogger(__name__)

WEB_SOURCE = "staff"

NO_BIRTHDAY = (
    "Black Bloc has no birthday stored for **{user_id}**, so there was nothing to remove. The "
    "birthdays page lists the ones it has."
)
NEEDS_A_DATE = (
    "A birthday needs a month and a day, so nothing was stored. Pick both and send it again."
)
WISHED = "**{name}** gets a birthday wish again."
NOT_WISHED = "**{name}** is opted out, so Black Bloc says nothing on their birthday."


def birthday_row(guild: Any, row: Any) -> dict[str, Any]:
    return {
        "user_id": str(row["user_id"]),
        "user_name": resolve_one(guild, row["user_id"])["display_name"],
        "month": int(row["month"]),
        "day": int(row["day"]),
        "year": int(row["year"]) if row["year"] else None,
        "when": month_day_text(row["month"], row["day"]),
        "opted_in": bool(row["opted_in"]),
        "source": row["source"],
        "set_at": row["set_at"],
        "last_announced_on": row["last_announced_on"],
    }


def wanted_date(payload: dict[str, Any]) -> tuple[int, int, int | None]:
    month, day = as_id(payload.get("month")), as_id(payload.get("day"))
    if month is None or day is None:
        raise Refused(400, "bad_request", NEEDS_A_DATE)
    problem = date_problem(month, day)
    if problem:
        raise Refused(400, "bad_date", problem)
    year = as_id(payload.get("year")) if payload.get("year") not in (None, "") else None
    if year is not None:
        said = year_problem(year, date.today())
        if said:
            raise Refused(400, "bad_year", said)
    return int(month), int(day), year


def build_router(bot: Any) -> APIRouter:
    writer = writer_dependency(bot)
    router = APIRouter(
        prefix="/api/birthdays", tags=["birthdays"], dependencies=[Depends(staff_dependency(bot))]
    )

    @router.get("")
    async def birthdays_index() -> list[dict[str, Any]]:
        guild = require_guild(bot)
        require_db(bot)
        return [birthday_row(guild, row) for row in await rows_for_guild(bot.db, guild.id)]

    @router.put("/{user_id}")
    async def birthday_set(
        request: Request, user_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        wanted = wanted_id(user_id)
        month, day, year = wanted_date(payload)
        await save_birthday(bot.db, guild.id, wanted, month, day, year, WEB_SOURCE)
        await note(
            bot,
            guild,
            "web.birthday.set",
            who,
            target=wanted,
            details={"month": month, "day": day, "year": year},
        )
        rows = await rows_for_guild(bot.db, guild.id)
        stored = next(row for row in rows if int(row["user_id"]) == wanted)
        return birthday_row(guild, stored)

    @router.post("/{user_id}/optin")
    async def birthday_optin(
        request: Request, user_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        wanted = wanted_id(user_id)
        rows = await rows_for_guild(bot.db, guild.id)
        if not any(int(row["user_id"]) == wanted for row in rows):
            raise Refused(404, "no_birthday", NO_BIRTHDAY.format(user_id=wanted))
        opted = payload.get("opted_in", True) is not False
        await set_opted_in(bot.db, wanted, opted)
        await note(
            bot, guild, "web.birthday.optin", who, target=wanted, details={"opted_in": opted}
        )
        rows = await rows_for_guild(bot.db, guild.id)
        stored = birthday_row(guild, next(row for row in rows if int(row["user_id"]) == wanted))
        said = WISHED if opted else NOT_WISHED
        return stored | {"message": said.format(name=stored["user_name"] or wanted)}

    @router.delete("/{user_id}")
    async def birthday_clear(request: Request, user_id: str) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        wanted = wanted_id(user_id)
        if not await delete_birthday(bot.db, wanted):
            raise Refused(404, "no_birthday", NO_BIRTHDAY.format(user_id=wanted))
        await note(bot, guild, "web.birthday.clear", who, target=wanted)
        return {"removed": True, "user_id": str(wanted)}

    return router
