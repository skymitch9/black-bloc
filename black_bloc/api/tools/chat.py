from __future__ import annotations

import logging
import sqlite3
from typing import Any

from fastapi import APIRouter, Depends, Request

from ...chat import (
    BUILTIN_NAMES,
    CANNED,
    SLOTS,
    ChatError,
    add_line,
    answer_for,
    clean_name,
    clean_slot,
    clean_text,
    clean_triggers,
    create_intent,
    delete_intent,
    delete_line,
    get_intent,
    get_line,
    invalidate,
    lines_for,
    list_intents,
    read_triggers,
    seed_defaults,
    tokens_of,
    update_intent,
    update_line,
)
from ...logkinds import VIA_WEBSITE
from ...settings_store import KEY_TYPES
from ..auth import Refused, staff_dependency
from ..names import as_id, resolve_one
from ..settings_api import key_row, namespace_of
from ..writes import (
    actor_for,
    note,
    reader_dependency,
    require_db,
    require_guild,
    writer_dependency,
)
from . import chat_store

log = logging.getLogger(__name__)

NAMESPACE = "chat"

NO_SUCH_INTENT = (
    "Black Bloc has no chat intent **#{intent_id}** any more, so nothing was done. The Chat page "
    "lists the ones it has."
)
NO_SUCH_LINE = (
    "Black Bloc has no chat line **#{line_id}** any more, so nothing was done. Somebody may have "
    "removed it while this page was open."
)
BUILT_IN_STAYS = (
    "**{name}** is one of Black Bloc's own intents, so it cannot be deleted — turn it off instead "
    "and it will stop answering, or edit its triggers and lines to say something else."
)
BUILT_IN_KEEPS_ITS_NAME = (
    "**{name}** is one of Black Bloc's own intents and its name is what the bot looks it up by, "
    "so the name cannot change. Its triggers, its lines and its on/off switch all can."
)
NAME_TAKEN = (
    "This server already has an intent called **{name}**, so nothing was saved. Pick another name, "
    "or edit the one that is there."
)
TRY_NEEDS_TEXT = (
    "There is nothing to try yet, so nothing was worked out. Type the sentence somebody would say "
    "and send it again."
)
INTENT_MADE = "**{name}** is in. It will answer as soon as it has a line to say."
INTENT_SAVED = "**{name}** is saved."
INTENT_GONE = "**{name}** is gone. Nothing answers to those phrases any more."
LINE_ADDED = "That line is in — **{name}** may say it from now on."
LINE_SAVED = "That line is saved."
LINE_GONE = "That line is gone."

NO_SUCH_SECTION = (
    "Black Bloc has no note **#{section_id}** any more, so nothing was done. Somebody may have "
    "removed it while this page was open."
)
SERVER_ROW_LOCKED = (
    "**{title}** is one of the notes Black Bloc writes for itself out of the server — the channel "
    "list, the roles, what is coming up — so it cannot be changed by hand. It is written again "
    "from scratch every day, and an edit here would be gone by morning. Write your own note "
    "beside it and Black Bloc reads both."
)
NEEDS_TITLE = (
    "A note needs a heading, so nothing was saved. That is the line Black Bloc matches a question "
    "against — something like `Cookout hours`."
)
TITLE_TOO_LONG = (
    "A note's heading has to be {limit} characters or fewer, so nothing was saved. Shorten it and "
    "send it again."
)
NEEDS_BODY = (
    "A note needs some words under the heading, so nothing was saved. Write what you would tell "
    "somebody who asked."
)
BODY_TOO_LONG = (
    "A note has to be {limit} characters or fewer, so nothing was saved. Anything longer will not "
    "fit in an answer — split it into two notes with headings of their own."
)
TAG_TOO_LONG = "A tag has to be {limit} characters or fewer, so nothing was saved."
TITLE_TAKEN = (
    "This server already has a note called **{title}**, so nothing was saved. Edit that one, or "
    "give this one a heading of its own."
)
SECTION_MADE = "**{title}** is in. Black Bloc quotes it when somebody asks something it matches."
SECTION_SAVED = "**{title}** is saved."
SECTION_GONE = "**{title}** is gone. Black Bloc will not quote it again."

STAFF_WROTE_IT = "written here by staff"
SERVER_WROTE_IT = "written by Black Bloc from the server itself, every day"

NO_SUCH_TROPE = (
    "**{name}** is not one of the voices Black Bloc knows, so nothing was changed. The list on "
    "this page is all of them."
)
MODE_NEEDS_A_NAME = (
    "That arrived with no voice in it, so nothing was changed. Pick the cookout voice, the pool, "
    "or one of the names on the list."
)
TROPE_IS_OFF = (
    "**{label}** is switched off in the pool, so Black Bloc cannot be it. Turn it back on first, "
    "or pick another one."
)
LAST_TROPE_ON = (
    "**{label}** is the last voice left on and the pool is what Black Bloc is using, so it was "
    "left alone. Turn another one on first, or move the voice to the cookout one."
)
TROPE_IN_USE = (
    "Black Bloc is set to be **{label}** and nothing else, so that voice cannot be switched off. "
    "Point it at the cookout voice or the pool first."
)
MODE_SET_COOKOUT = "Black Bloc talks in the cookout voice from now on."
MODE_SET_POOL = (
    "Black Bloc picks a voice out of the pool for each conversation from now on, and moves a step "
    "at a time as people talk."
)
MODE_SET_TROPE = "Black Bloc is **{label}** with everybody from now on."
TROPE_ON = "**{label}** is back in the pool."
TROPE_OFF = "**{label}** is out of the pool. Black Bloc will not pick it again."

COOKOUT_WORD = (
    "Everybody gets the cookout voice — warm, playful, the one the rest of the site is written in."
)
POOL_WORD = (
    "Each conversation gets one of the {count} voices left on, and it moves a step at a time as "
    "people talk."
)
TROPE_WORD = "Black Bloc is **{label}** with everybody, and it does not drift."

TIER_INTENTS = "intents"
TIER_IMPORTANT = "important"
TIER_SIMPLE = "simple"

INTENTS_ALWAYS = (
    "Always on. The phrases on this page answer first, they cost nothing, and they are checked "
    "before any model is asked."
)
TIER_LIVE = {
    TIER_IMPORTANT: "Live. Grounded answers and longer questions go here.",
    TIER_SIMPLE: "Live. Greetings and one-liners that slipped past the phrases go here.",
}
TIER_MODE_OFF = (
    "Not in use: `chat_llm_mode` is off, so Black Bloc answers from the phrases on this page and "
    "nothing else."
)
TIER_NO_KEY = (
    "Black Bloc has not been given a **{key}** yet, so this tier does not exist and the answer "
    "falls through to the next one. A Lead sets it on the host."
)
TIER_CAPPED = (
    "Closed until the 1st: this month's {cap} is spent. Black Bloc is answering from the phrases "
    "on this page in the meantime."
)
MONTH_WORD = "{spent} of the {cap} Black Bloc may spend this month, so {left} is left."
MONTH_CAPPED_WORD = (
    "{spent} of the {cap} Black Bloc may spend this month, so the two model tiers are shut until "
    "the 1st."
)
TODAY_WORD = "{turns} answers came from a model today, out of the {limit} a day Black Bloc gives."
TODAY_WORD_NO_LIMIT = "{turns} answers came from a model today."


def _id(value: Any) -> str | None:
    return str(value) if value is not None else None


def line_row(row: Any) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "intent_id": str(row["intent_id"]),
        "text": str(row["text"]),
        "slot": str(row["slot"]),
        "enabled": bool(row["enabled"]),
        "created_by": _id(row["created_by"]),
        "updated_at": row["updated_at"],
    }


def intent_row(row: Any, lines: Any) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "name": str(row["name"]),
        "kind": str(row["kind"]),
        "enabled": bool(row["enabled"]),
        "sort": int(row["sort"]),
        "triggers": list(read_triggers(row["triggers"])),
        "builtin": str(row["name"]) in BUILTIN_NAMES,
        "tokens": list(tokens_of(str(row["name"]))),
        "created_by": _id(row["created_by"]),
        "updated_at": row["updated_at"],
        "lines": [line_row(one) for one in lines],
    }


def chat_settings(bot: Any, guild_id: int) -> list[dict[str, Any]]:
    """The chat namespace in the same row shape /api/settings uses."""
    return [
        key_row(bot.store, guild_id, key)
        for key in KEY_TYPES
        if namespace_of(key) == NAMESPACE
    ]


def person(guild: Any, user_id: Any) -> dict[str, Any] | None:
    number = as_id(user_id)
    if number is None:
        return None
    return {"id": str(number), "name": resolve_one(guild, number)["display_name"] or str(number)}


def section_row(guild: Any, row: Any) -> dict[str, Any]:
    source = str(row["source"])
    own = source == chat_store.STAFF
    title = str(row["title"])
    return {
        "id": str(row["id"]),
        "title": title,
        "body": str(row["body"]),
        "tag": row["tag"],
        "source": source,
        "source_word": STAFF_WROTE_IT if own else SERVER_WROTE_IT,
        "editable": own,
        "locked_why": None if own else SERVER_ROW_LOCKED.format(title=title),
        "characters": len(str(row["body"])),
        "updated_at": row["updated_at"],
        "updated_by": person(guild, row["updated_by"]),
    }


def trope_row(guild: Any, row: Any, mode: str) -> dict[str, Any]:
    name = str(row["name"])
    return {
        "name": name,
        "label": str(row["label"]),
        "voice": str(row["voice"]),
        "enabled": bool(row["enabled"]),
        "in_use": mode == name,
        "updated_at": row["updated_at"],
        "updated_by": person(guild, row["updated_by"]),
    }


def mode_kind(mode: str) -> str:
    if mode == chat_store.COOKOUT:
        return chat_store.COOKOUT
    return chat_store.POOL if mode == chat_store.POOL else chat_store.TROPE


def mode_word(mode: str, tropes: list[Any]) -> str:
    kind = mode_kind(mode)
    if kind == chat_store.COOKOUT:
        return COOKOUT_WORD
    if kind == chat_store.POOL:
        return POOL_WORD.format(count=sum(1 for row in tropes if row["enabled"]))
    label = next((str(row["label"]) for row in tropes if row["name"] == mode), mode)
    return TROPE_WORD.format(label=label)


def setting_or(bot: Any, guild_id: int, key: str, fallback: Any) -> Any:
    """A registry key when the bot has one; 14a's keys land after 14b's page does."""
    if key not in KEY_TYPES:
        return fallback
    found = bot.store.get(guild_id, key)
    return fallback if found is None else found


def money(dollars: float) -> str:
    return f"${dollars:,.2f}"


def clean_title(value: Any) -> str:
    said = " ".join(str(value or "").split())
    if not said:
        raise Refused(400, "chat_refused", NEEDS_TITLE)
    if len(said) > chat_store.TITLE_LIMIT:
        raise Refused(
            400, "chat_refused", TITLE_TOO_LONG.format(limit=chat_store.TITLE_LIMIT)
        )
    return said


def clean_body(value: Any) -> str:
    said = str(value or "").strip()
    if not said:
        raise Refused(400, "chat_refused", NEEDS_BODY)
    if len(said) > chat_store.BODY_LIMIT:
        raise Refused(400, "chat_refused", BODY_TOO_LONG.format(limit=chat_store.BODY_LIMIT))
    return said


def clean_tag(value: Any) -> str | None:
    said = " ".join(str(value or "").split())
    if not said:
        return None
    if len(said) > chat_store.TAG_LIMIT:
        raise Refused(400, "chat_refused", TAG_TOO_LONG.format(limit=chat_store.TAG_LIMIT))
    return said


def refused(exc: ChatError) -> Refused:
    return Refused(400, "chat_refused", str(exc))


def wanted_enabled(payload: dict[str, Any], key: str = "enabled") -> Any:
    given = payload.get(key)
    return None if given is None else bool(given)


def build_router(bot: Any) -> APIRouter:
    writer = writer_dependency(bot)
    reader = reader_dependency(bot)
    router = APIRouter(
        prefix="/api/chat", tags=["chat"], dependencies=[Depends(staff_dependency(bot))]
    )

    async def _shown(guild: Any, row: Any) -> dict[str, Any]:
        return intent_row(row, await lines_for(bot.db, row["id"]))

    async def _wanted_intent(guild: Any, intent_id: int) -> Any:
        row = await get_intent(bot.db, intent_id)
        if row is None or row["guild_id"] != guild.id:
            raise Refused(404, "no_such_intent", NO_SUCH_INTENT.format(intent_id=intent_id))
        return row

    async def _wanted_line(guild: Any, line_id: int) -> tuple[Any, Any]:
        row = await get_line(bot.db, line_id)
        owner = await get_intent(bot.db, row["intent_id"]) if row is not None else None
        if owner is None or owner["guild_id"] != guild.id:
            raise Refused(404, "no_such_line", NO_SUCH_LINE.format(line_id=line_id))
        return row, owner

    @router.get("/intents")
    async def chat_intents() -> dict[str, Any]:
        """A guild that has never been seeded is seeded here, so the page is never blank."""
        guild = require_guild(bot)
        require_db(bot)
        rows = await list_intents(bot.db, guild.id)
        if not rows:
            await seed_defaults(bot.db, guild.id)
            invalidate(bot, guild.id)
            rows = await list_intents(bot.db, guild.id)
        return {
            "intents": [await _shown(guild, row) for row in rows],
            "settings": chat_settings(bot, guild.id),
            "slots": list(SLOTS),
            "notes": [],
        }

    @router.post("/intents")
    async def chat_intent_create(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        try:
            name = clean_name(payload.get("name"))
            triggers = clean_triggers(payload.get("triggers"))
        except ChatError as exc:
            raise refused(exc) from exc
        try:
            intent_id = await create_intent(
                bot.db,
                guild.id,
                name,
                triggers,
                kind=CANNED,
                enabled=payload.get("enabled") is not False,
                sort=int(payload.get("sort") or 0),
                by=int(who["id"]),
            )
        except sqlite3.IntegrityError as exc:
            raise Refused(409, "name_taken", NAME_TAKEN.format(name=name)) from exc
        text = payload.get("text")
        if text:
            try:
                await add_line(bot.db, intent_id, clean_text(text), by=int(who["id"]))
            except ChatError as exc:
                raise refused(exc) from exc
        invalidate(bot, guild.id)
        await note(bot, guild, "web.chat.intent_created", who, details={"name": name})
        row = await get_intent(bot.db, intent_id)
        return {"intent": await _shown(guild, row), "message": INTENT_MADE.format(name=name)}

    @router.put("/intents/{intent_id}")
    async def chat_intent_edit(
        request: Request, intent_id: int, payload: dict[str, Any]
    ) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        row = await _wanted_intent(guild, intent_id)
        built_in = str(row["name"]) in BUILTIN_NAMES
        fields: dict[str, Any] = {}
        try:
            if payload.get("name") is not None and str(payload["name"]) != row["name"]:
                if built_in:
                    raise Refused(
                        409, "built_in", BUILT_IN_KEEPS_ITS_NAME.format(name=row["name"])
                    )
                fields["name"] = clean_name(payload["name"])
            if payload.get("triggers") is not None:
                fields["triggers"] = clean_triggers(payload["triggers"])
        except ChatError as exc:
            raise refused(exc) from exc
        enabled = wanted_enabled(payload)
        if enabled is not None:
            fields["enabled"] = enabled
        if payload.get("sort") is not None:
            fields["sort"] = int(payload["sort"])
        try:
            await update_intent(bot.db, intent_id, **fields)
        except sqlite3.IntegrityError as exc:
            raise Refused(
                409, "name_taken", NAME_TAKEN.format(name=fields.get("name"))
            ) from exc
        invalidate(bot, guild.id)
        await note(
            bot,
            guild,
            "web.chat.intent_edited",
            who,
            details={"intent_id": intent_id, "changed": sorted(fields)},
        )
        fresh = await get_intent(bot.db, intent_id)
        return {
            "intent": await _shown(guild, fresh),
            "message": INTENT_SAVED.format(name=fresh["name"]),
        }

    @router.delete("/intents/{intent_id}")
    async def chat_intent_delete(request: Request, intent_id: int) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        row = await _wanted_intent(guild, intent_id)
        if str(row["name"]) in BUILTIN_NAMES:
            raise Refused(409, "built_in", BUILT_IN_STAYS.format(name=row["name"]))
        await delete_intent(bot.db, intent_id)
        invalidate(bot, guild.id)
        await note(
            bot, guild, "web.chat.intent_deleted", who, details={"name": str(row["name"])}
        )
        return {
            "removed": True,
            "intent_id": str(intent_id),
            "message": INTENT_GONE.format(name=row["name"]),
        }

    @router.post("/intents/{intent_id}/lines")
    async def chat_line_add(
        request: Request, intent_id: int, payload: dict[str, Any]
    ) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        row = await _wanted_intent(guild, intent_id)
        try:
            text = clean_text(payload.get("text"))
            slot = clean_slot(payload.get("slot"))
        except ChatError as exc:
            raise refused(exc) from exc
        line_id = await add_line(
            bot.db,
            intent_id,
            text,
            slot=slot,
            enabled=payload.get("enabled") is not False,
            by=int(who["id"]),
        )
        invalidate(bot, guild.id)
        await note(
            bot,
            guild,
            "web.chat.line_added",
            who,
            details={"intent_id": intent_id, "slot": slot},
        )
        return {
            "line": line_row(await get_line(bot.db, line_id)),
            "message": LINE_ADDED.format(name=row["name"]),
        }

    @router.put("/lines/{line_id}")
    async def chat_line_edit(
        request: Request, line_id: int, payload: dict[str, Any]
    ) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        await _wanted_line(guild, line_id)
        fields: dict[str, Any] = {}
        try:
            if payload.get("text") is not None:
                fields["text"] = clean_text(payload["text"])
            if payload.get("slot") is not None:
                fields["slot"] = clean_slot(payload["slot"])
        except ChatError as exc:
            raise refused(exc) from exc
        enabled = wanted_enabled(payload)
        if enabled is not None:
            fields["enabled"] = enabled
        await update_line(bot.db, line_id, **fields)
        invalidate(bot, guild.id)
        await note(
            bot,
            guild,
            "web.chat.line_edited",
            who,
            details={"line_id": line_id, "changed": sorted(fields)},
        )
        return {"line": line_row(await get_line(bot.db, line_id)), "message": LINE_SAVED}

    @router.delete("/lines/{line_id}")
    async def chat_line_delete(request: Request, line_id: int) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        row, owner = await _wanted_line(guild, line_id)
        await delete_line(bot.db, line_id)
        invalidate(bot, guild.id)
        await note(
            bot,
            guild,
            "web.chat.line_deleted",
            who,
            details={"intent_id": int(owner["id"]), "slot": str(row["slot"])},
        )
        return {"removed": True, "line_id": str(line_id), "message": LINE_GONE}

    @router.post("/try")
    async def chat_try(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
        """A dry run: the real classifier and the real live data, and nothing is sent."""
        who = await reader(request)
        guild = require_guild(bot)
        require_db(bot)
        text = str(payload.get("text") or "").strip()
        if not text:
            raise Refused(400, "no_text", TRY_NEEDS_TEXT)
        answer = await answer_for(text, actor_for(bot, who, guild), bot, guild=guild)
        return {
            "intent": answer.intent,
            "kind": answer.kind,
            "slot": answer.slot,
            "line": answer.text,
        }

    async def _wanted_section(guild: Any, section_id: int) -> Any:
        row = await chat_store.get_section(bot.db, section_id)
        if row is None or row["guild_id"] != guild.id:
            raise Refused(404, "no_such_section", NO_SUCH_SECTION.format(section_id=section_id))
        return row

    def _staff_row_only(row: Any) -> None:
        if str(row["source"]) != chat_store.STAFF:
            raise Refused(
                409, "written_by_the_bot", SERVER_ROW_LOCKED.format(title=str(row["title"]))
            )

    async def _knowledge(guild: Any) -> dict[str, Any]:
        rows = await chat_store.list_sections(bot.db, guild.id)
        shown = [section_row(guild, row) for row in rows]
        return {
            "sections": shown,
            "counts": {
                "total": len(shown),
                "staff": sum(1 for row in shown if row["source"] == chat_store.STAFF),
                "server": sum(1 for row in shown if row["source"] == chat_store.SERVER),
            },
            "budget": {
                "sections": chat_store.GROUNDING_SECTIONS,
                "characters": chat_store.GROUNDING_BUDGET_BYTES,
                "word": (
                    f"At most {chat_store.GROUNDING_SECTIONS} notes ride an answer, and a note "
                    "that will not fit is left out rather than cut short."
                ),
            },
            "notes": [],
        }

    @router.get("/knowledge")
    async def chat_knowledge() -> dict[str, Any]:
        guild = require_guild(bot)
        require_db(bot)
        await chat_store.ensure_tables(bot.db)
        return await _knowledge(guild)

    @router.post("/knowledge")
    async def chat_knowledge_add(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        await chat_store.ensure_tables(bot.db)
        title = clean_title(payload.get("title"))
        body = clean_body(payload.get("body"))
        tag = clean_tag(payload.get("tag"))
        try:
            section_id = await chat_store.add_section(
                bot.db, guild.id, title, body, tag=tag, by=int(who["id"])
            )
        except sqlite3.IntegrityError as exc:
            raise Refused(409, "title_taken", TITLE_TAKEN.format(title=title)) from exc
        await note(
            bot,
            guild,
            "web.chat.knowledge_added",
            who,
            details={"title": title, "via": VIA_WEBSITE},
        )
        row = await chat_store.get_section(bot.db, section_id)
        return {
            "section": section_row(guild, row),
            "message": SECTION_MADE.format(title=title),
        }

    @router.put("/knowledge/{section_id}")
    async def chat_knowledge_edit(
        request: Request, section_id: int, payload: dict[str, Any]
    ) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        await chat_store.ensure_tables(bot.db)
        row = await _wanted_section(guild, section_id)
        _staff_row_only(row)
        fields: dict[str, Any] = {}
        if payload.get("title") is not None:
            fields["title"] = clean_title(payload["title"])
        if payload.get("body") is not None:
            fields["body"] = clean_body(payload["body"])
        if "tag" in payload:
            fields["tag"] = clean_tag(payload["tag"])
        try:
            await chat_store.update_section(bot.db, section_id, by=int(who["id"]), **fields)
        except sqlite3.IntegrityError as exc:
            raise Refused(
                409, "title_taken", TITLE_TAKEN.format(title=fields.get("title"))
            ) from exc
        await note(
            bot,
            guild,
            "web.chat.knowledge_edited",
            who,
            details={"section_id": section_id, "changed": sorted(fields), "via": VIA_WEBSITE},
        )
        fresh = await chat_store.get_section(bot.db, section_id)
        return {
            "section": section_row(guild, fresh),
            "message": SECTION_SAVED.format(title=str(fresh["title"])),
        }

    @router.delete("/knowledge/{section_id}")
    async def chat_knowledge_delete(request: Request, section_id: int) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        await chat_store.ensure_tables(bot.db)
        row = await _wanted_section(guild, section_id)
        _staff_row_only(row)
        title = str(row["title"])
        await chat_store.delete_section(bot.db, section_id)
        await note(
            bot,
            guild,
            "web.chat.knowledge_removed",
            who,
            details={"title": title, "via": VIA_WEBSITE},
        )
        return {
            "removed": True,
            "section_id": str(section_id),
            "message": SECTION_GONE.format(title=title),
        }

    async def _personality(guild: Any) -> dict[str, Any]:
        await chat_store.seed_tropes(bot.db, guild.id)
        rows = await chat_store.list_tropes(bot.db, guild.id)
        mode = await chat_store.persona_mode(bot.db, guild.id)
        shown = [trope_row(guild, row, mode) for row in rows]
        return {
            "mode": mode,
            "mode_kind": mode_kind(mode),
            "mode_word": mode_word(mode, rows),
            "tropes": shown,
            "counts": {
                "total": len(shown),
                "enabled": sum(1 for row in shown if row["enabled"]),
            },
            "ported_from": chat_store.POOL_SOURCE,
            "notes": [],
        }

    @router.get("/personality")
    async def chat_personality() -> dict[str, Any]:
        """A guild that has never been seeded gets the ported pool here, so it is never blank."""
        guild = require_guild(bot)
        require_db(bot)
        await chat_store.ensure_tables(bot.db)
        return await _personality(guild)

    @router.put("/personality")
    async def chat_personality_mode(
        request: Request, payload: dict[str, Any]
    ) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        await chat_store.ensure_tables(bot.db)
        await chat_store.seed_tropes(bot.db, guild.id)
        wanted = str(payload.get("mode") or "").strip().lower()
        if not wanted:
            raise Refused(400, "chat_refused", MODE_NEEDS_A_NAME)
        said = MODE_SET_COOKOUT
        if wanted not in (chat_store.COOKOUT, chat_store.POOL):
            row = await chat_store.get_trope(bot.db, guild.id, wanted)
            if row is None:
                raise Refused(404, "no_such_trope", NO_SUCH_TROPE.format(name=wanted))
            if not row["enabled"]:
                raise Refused(409, "voice_is_off", TROPE_IS_OFF.format(label=str(row["label"])))
            said = MODE_SET_TROPE.format(label=str(row["label"]))
        elif wanted == chat_store.POOL:
            said = MODE_SET_POOL
        await chat_store.set_persona_mode(bot.db, guild.id, wanted, by=int(who["id"]))
        await note(
            bot,
            guild,
            "web.chat.personality_mode",
            who,
            details={"mode": wanted, "via": VIA_WEBSITE},
        )
        found = await _personality(guild)
        return {
            "mode": found["mode"],
            "mode_kind": found["mode_kind"],
            "mode_word": found["mode_word"],
            "message": said,
        }

    @router.put("/personality/{name}")
    async def chat_trope_switch(
        request: Request, name: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        await chat_store.ensure_tables(bot.db)
        await chat_store.seed_tropes(bot.db, guild.id)
        row = await chat_store.get_trope(bot.db, guild.id, str(name).strip().lower())
        if row is None:
            raise Refused(404, "no_such_trope", NO_SUCH_TROPE.format(name=name))
        label = str(row["label"])
        wanted = payload.get("enabled") is not False
        mode = await chat_store.persona_mode(bot.db, guild.id)
        if not wanted and mode == str(row["name"]):
            raise Refused(409, "voice_in_use", TROPE_IN_USE.format(label=label))
        rows = await chat_store.list_tropes(bot.db, guild.id)
        on_now = [one for one in rows if one["enabled"]]
        last_one = len(on_now) == 1 and on_now[0]["name"] == row["name"]
        if not wanted and last_one and mode == chat_store.POOL:
            raise Refused(409, "last_voice", LAST_TROPE_ON.format(label=label))
        await chat_store.set_trope_enabled(
            bot.db, guild.id, str(row["name"]), wanted, by=int(who["id"])
        )
        await note(
            bot,
            guild,
            "web.chat.trope_enabled" if wanted else "web.chat.trope_disabled",
            who,
            details={"trope": str(row["name"]), "via": VIA_WEBSITE},
        )
        fresh = await chat_store.get_trope(bot.db, guild.id, str(row["name"]))
        return {
            "trope": trope_row(guild, fresh, mode),
            "message": (TROPE_ON if wanted else TROPE_OFF).format(label=label),
        }

    def _tier(name: str, label: str, key: str, *, mode_on: bool, cap_said: str | None):
        """Liveness is measured — the mode, the key and the cap — never assumed."""
        said = TIER_LIVE[name]
        live = True
        if not mode_on:
            said, live = TIER_MODE_OFF, False
        elif not str(getattr(bot.settings, key.lower(), "") or ""):
            said, live = TIER_NO_KEY.format(key=key), False
        elif cap_said is not None:
            said, live = TIER_CAPPED.format(cap=cap_said), False
        return {"name": name, "label": label, "live": live, "word": said}

    @router.get("/spend")
    async def chat_spend() -> dict[str, Any]:
        """What the month has cost, what today has asked for, and which tiers are answering."""
        guild = require_guild(bot)
        require_db(bot)
        await chat_store.ensure_tables(bot.db)
        spent = await chat_store.spent_this_month(bot.db, guild.id)
        turns = await chat_store.turns_today(bot.db, guild.id)
        cap_usd = float(
            setting_or(bot, guild.id, chat_store.CAP_KEY, chat_store.MONTHLY_CAP_USD)
        )
        daily = setting_or(bot, guild.id, chat_store.DAILY_KEY, chat_store.DAILY_TURNS)
        mode_on = str(
            setting_or(bot, guild.id, chat_store.LLM_MODE_KEY, chat_store.LLM_MODE_DEFAULT)
        ) == "on"
        spent_usd = round(spent / chat_store.MICRODOLLARS, 2)
        left_usd = round(max(cap_usd - spent_usd, 0.0), 2)
        capped = cap_usd > 0 and spent_usd >= cap_usd
        cap_said = money(cap_usd)
        month_word = (
            MONTH_CAPPED_WORD if capped else MONTH_WORD
        ).format(spent=money(spent_usd), cap=cap_said, left=money(left_usd))
        shut = cap_said if capped else None
        tiers = [
            {"name": TIER_INTENTS, "label": "Phrases", "live": True, "word": INTENTS_ALWAYS},
            _tier(
                TIER_IMPORTANT, "Claude Haiku", "ANTHROPIC_API_KEY", mode_on=mode_on, cap_said=shut
            ),
            _tier(TIER_SIMPLE, "Groq Llama", "GROQ_API_KEY", mode_on=mode_on, cap_said=shut),
        ]
        return {
            "month": {
                "spent_usd": spent_usd,
                "cap_usd": cap_usd,
                "left_usd": left_usd,
                "share": round(spent_usd / cap_usd, 4) if cap_usd > 0 else 0.0,
                "word": month_word,
            },
            "today": {
                "turns": turns,
                "limit": int(daily) if daily else None,
                "word": (
                    TODAY_WORD.format(turns=turns, limit=int(daily))
                    if daily
                    else TODAY_WORD_NO_LIMIT.format(turns=turns)
                ),
            },
            "tiers": tiers,
            "capped": capped,
            "cap_key": chat_store.CAP_KEY,
            "last_turn_at": await chat_store.last_turn_at(bot.db, guild.id),
            "notes": [],
        }

    return router


__all__ = ["build_router", "intent_row", "line_row"]
