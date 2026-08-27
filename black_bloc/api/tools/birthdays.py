from __future__ import annotations

import logging
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Request

from ...actionlog import log_action
from ...birthdays import (
    date_problem,
    import_as_of_year,
    load_import_rows,
    month_day_text,
    year_problem,
)
from ...cogs.community.birthdays import (
    delete_birthday,
    import_rows,
    members_of,
    report_lines,
    rows_for_guild,
    save_birthday,
    set_opted_in,
)
from ..auth import Refused, staff_dependency
from ..names import as_id, resolve_one
from ..writes import (
    actor_for,
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
IMPORT_EMPTY = (
    "There is no Birthday Bot export to read, so nothing was imported. The seed file ships with "
    "Black Bloc; ask whoever deployed it whether it was left out."
)


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

    @router.post("/import")
    async def birthdays_import(request: Request) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        rows = load_import_rows()
        if not rows:
            raise Refused(409, "nothing_to_import", IMPORT_EMPTY)
        as_of = import_as_of_year()
        members = await members_of(guild)
        result = await import_rows(bot, guild, rows, as_of, members)
        await log_action(
            bot,
            guild,
            "birthday.import",
            actor=actor_for(bot, who, guild),
            details={key: len(value) for key, value in result.items()}
            | {"searched": len(members)},
        )
        await note(
            bot,
            guild,
            "web.birthday.import",
            who,
            details={key: len(value) for key, value in result.items()},
        )
        return {
            "counts": {key: len(value) for key, value in result.items()},
            "searched": len(members),
            "as_of_year": as_of,
            "report": result,
            "notes": report_lines(result, as_of, len(members)),
        }

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
