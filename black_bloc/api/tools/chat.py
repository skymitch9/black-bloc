from __future__ import annotations

import logging
import sqlite3
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Request

from ... import channel_drafts, chat_llm, chat_panel, knowledge, personas
from ...channel_notes import NOTE_CHARS, notes_for
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
from ...directory import directory_preview, hidden_category_ids, visibility_role, why_hidden
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
SECTION_MADE = "**{title}** is in. Black Bloc quotes it when somebody asks something it matches."
SECTION_SAVED = "**{title}** is saved."
SECTION_GONE = "**{title}** is gone. Black Bloc will not quote it again."

STAFF_WROTE_IT = "written here by staff"
SERVER_WROTE_IT = "written by Black Bloc from the server itself, every day"

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

ONE_VOICE = "trope"

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


UNCATEGORISED = -1


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
    own = source == knowledge.STAFF
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
    edited = personas.own_voice(row)
    return {
        "name": name,
        "label": str(row["label"]),
        "voice": str(row["voice"]),
        "shipped": personas.VOICES.get(name),
        "edited": edited,
        "edited_at": row["voice_edited_at"] if edited else None,
        "edited_by": person(guild, row["voice_edited_by"]) if edited else None,
        "enabled": bool(row["enabled"]),
        "in_use": mode == name,
        "updated_at": row["updated_at"],
        "updated_by": person(guild, row["updated_by"]),
    }


def voice_entry(guild: Any, entry: dict[str, Any], labels: dict[str, str]) -> dict[str, Any]:
    """One member of Who hears what, with names from the guild cache only."""
    tone = str(entry["trope"])
    pinned = entry["pinned"]
    return {
        "user_id": str(entry["user_id"]),
        "name": resolve_one(guild, entry["user_id"])["display_name"] or str(entry["user_id"]),
        "trope": tone,
        "label": labels.get(tone, tone),
        "pinned": pinned,
        "pinned_label": labels.get(pinned, pinned) if pinned else None,
        "pinned_by": person(guild, entry["pinned_by"]),
        "pinned_at": entry["pinned_at"],
        "waiting": bool(entry["waiting"]),
        "since": entry["since"],
        "turns": int(entry["turns"]),
        "active": bool(entry["active"]),
    }


def channel_order(channel: Any) -> tuple[int, int]:
    """Discord's own order: loose channels first, then category by category."""
    category = getattr(channel, "category", None)
    at = UNCATEGORISED if category is None else int(getattr(category, "position", 0) or 0)
    return (at, int(getattr(channel, "position", 0) or 0))


def channel_row(
    channel: Any,
    notes: dict[int, str],
    why: str | None,
    drafted: Any = None,
    guild: Any = None,
) -> dict[str, Any]:
    category = getattr(channel, "category", None)
    note = notes.get(int(channel.id)) or None
    return {
        "id": str(channel.id),
        "name": str(channel.name),
        "category": str(category.name) if category is not None else None,
        "category_id": _id(getattr(category, "id", None)),
        "topic": str(getattr(channel, "topic", "") or "") or None,
        "note": note,
        "shown": why is None,
        "hidden_because": why,
        "position": int(getattr(channel, "position", 0) or 0),
        **draft_fields(drafted, note, guild),
    }


def draft_fields(drafted: Any, note: Any, guild: Any) -> dict[str, Any]:
    if drafted is None:
        return {"draft": None, "status": None, "decided_by": None, "decided_at": None}
    status = channel_drafts.effective(drafted["status"], drafted["draft"], note)
    decided = status != channel_drafts.DRAFT
    return {
        "draft": str(drafted["draft"]),
        "status": status,
        "decided_by": person(guild, drafted["decided_by"]) if decided and guild else None,
        "decided_at": drafted["decided_at"] if decided else None,
    }


def mode_kind(mode: str) -> str:
    if mode == personas.COOKOUT:
        return personas.COOKOUT
    return personas.POOL if mode == personas.POOL else ONE_VOICE


def mode_word(mode: str, tropes: list[Any]) -> str:
    kind = mode_kind(mode)
    if kind == personas.COOKOUT:
        return COOKOUT_WORD
    if kind == personas.POOL:
        return POOL_WORD.format(count=sum(1 for row in tropes if row["enabled"]))
    label = next((str(row["label"]) for row in tropes if row["name"] == mode), mode)
    return TROPE_WORD.format(label=label)


def persona_mode(bot: Any, guild_id: int) -> str:
    return str(bot.store.get(guild_id, personas.PERSONALITY_KEY) or personas.COOKOUT)


def money(dollars: float) -> str:
    return f"${dollars:,.2f}"


def answered(outcome: Any) -> Any:
    """The shared function's refusal, in its own words, with the status the site expects."""
    if not outcome.ok:
        raise Refused(outcome.status, outcome.code, outcome.message)
    return outcome


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
        row = await knowledge.get_section(bot.db, section_id)
        if row is None or row["guild_id"] != guild.id:
            raise Refused(404, "no_such_section", NO_SUCH_SECTION.format(section_id=section_id))
        return row

    def _staff_row_only(row: Any) -> None:
        if str(row["source"]) != knowledge.STAFF:
            raise Refused(
                409, "written_by_the_bot", SERVER_ROW_LOCKED.format(title=str(row["title"]))
            )

    async def _knowledge(guild: Any) -> dict[str, Any]:
        rows = await knowledge.list_sections(bot.db, guild.id)
        shown = [section_row(guild, row) for row in rows]
        return {
            "sections": shown,
            "counts": {
                "total": len(shown),
                "staff": sum(1 for row in shown if row["source"] == knowledge.STAFF),
                "server": sum(1 for row in shown if row["source"] == knowledge.SERVER),
            },
            "budget": {
                "sections": knowledge.HITS_DEFAULT,
                "characters": knowledge.GROUNDING_BYTES,
                "word": (
                    f"At most {knowledge.HITS_DEFAULT} notes ride an answer, and a note "
                    "that will not fit is left out rather than cut short."
                ),
            },
            "notes": [],
        }

    @router.get("/knowledge")
    async def chat_knowledge() -> dict[str, Any]:
        guild = require_guild(bot)
        require_db(bot)
        return await _knowledge(guild)

    @router.post("/knowledge")
    async def chat_knowledge_add(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        outcome = await chat_panel.add_note(
            bot,
            guild,
            actor_for(bot, who, guild),
            payload.get("title"),
            payload.get("body"),
            payload.get("tag"),
            via=VIA_WEBSITE,
        )
        answered(outcome)
        row = await knowledge.get_section(bot.db, outcome.value)
        return {
            "section": section_row(guild, row),
            "message": SECTION_MADE.format(title=str(row["title"])),
        }

    @router.put("/knowledge/{section_id}")
    async def chat_knowledge_edit(
        request: Request, section_id: int, payload: dict[str, Any]
    ) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        row = await _wanted_section(guild, section_id)
        _staff_row_only(row)
        fields: dict[str, Any] = {}
        if payload.get("title") is not None:
            fields["title"] = payload["title"]
        if payload.get("body") is not None:
            fields["body"] = payload["body"]
        if "tag" in payload:
            fields["tag"] = payload["tag"]
        answered(
            await chat_panel.edit_note(
                bot,
                guild,
                actor_for(bot, who, guild),
                section_id,
                fields,
                via=VIA_WEBSITE,
            )
        )
        fresh = await knowledge.get_section(bot.db, section_id)
        return {
            "section": section_row(guild, fresh),
            "message": SECTION_SAVED.format(title=str(fresh["title"])),
        }

    @router.delete("/knowledge/{section_id}")
    async def chat_knowledge_delete(request: Request, section_id: int) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        row = await _wanted_section(guild, section_id)
        _staff_row_only(row)
        title = str(row["title"])
        answered(
            await chat_panel.remove_note(
                bot, guild, actor_for(bot, who, guild), section_id, via=VIA_WEBSITE
            )
        )
        return {
            "removed": True,
            "section_id": str(section_id),
            "message": SECTION_GONE.format(title=title),
        }

    async def _personality(guild: Any) -> dict[str, Any]:
        await personas.sync_tropes(bot.db, full=False)
        rows = await personas.list_tropes(bot.db)
        mode = persona_mode(bot, guild.id)
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
            "ported_from": personas.POOL_SOURCE,
            "notes": [],
        }

    @router.get("/personality")
    async def chat_personality() -> dict[str, Any]:
        """A guild that has never been seeded gets the ported pool here, so it is never blank."""
        guild = require_guild(bot)
        require_db(bot)
        return await _personality(guild)

    @router.put("/personality")
    async def chat_personality_mode(
        request: Request, payload: dict[str, Any]
    ) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        await personas.sync_tropes(bot.db, full=False)
        wanted = str(payload.get("mode") or "").strip().lower()
        answered(
            await chat_panel.set_voice(
                bot, guild, actor_for(bot, who, guild), wanted, via=VIA_WEBSITE
            )
        )
        said = MODE_SET_COOKOUT
        if wanted == personas.POOL:
            said = MODE_SET_POOL
        elif wanted != personas.COOKOUT:
            row = await personas.get_trope(bot.db, wanted)
            said = MODE_SET_TROPE.format(label=str(row["label"]))
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
        """`enabled` moves it in or out of the pool; `voice` rewrites it (blank puts it back)."""
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        await personas.sync_tropes(bot.db, full=False)
        said = str(name).strip().lower()
        actor = actor_for(bot, who, guild)
        mode = persona_mode(bot, guild.id)
        messages = []
        if "voice" in payload:
            edited = answered(
                await chat_panel.edit_tone(
                    bot, guild, actor, said, payload.get("voice"), via=VIA_WEBSITE
                )
            )
            messages.append(edited.message)
        if "enabled" in payload or "voice" not in payload:
            wanted = payload.get("enabled") is not False
            answered(await chat_panel.set_mood(bot, guild, actor, said, wanted, via=VIA_WEBSITE))
            fresh = await personas.get_trope(bot.db, said)
            messages.append(
                (TROPE_ON if wanted else TROPE_OFF).format(label=str(fresh["label"]))
            )
        fresh = await personas.get_trope(bot.db, said)
        return {"trope": trope_row(guild, fresh, mode), "message": " ".join(messages)}

    async def _voices(guild: Any) -> dict[str, Any]:
        await personas.sync_tropes(bot.db, full=False)
        found = await chat_panel.voice_roster(bot, guild)
        labels = found["labels"]
        rows = [voice_entry(guild, one, labels) for one in found["voices"]]
        return {
            "setting": found["setting"],
            "setting_kind": mode_kind(found["setting"]),
            "tropes": [{"name": name, "label": labels[name]} for name in found["enabled"]],
            "voices": rows,
            "counts": {
                "total": len(rows),
                "pinned": sum(1 for row in rows if row["pinned"]),
                "active": sum(1 for row in rows if row["active"]),
            },
            "notes": [],
        }

    async def _voice_answer(guild: Any, user_id: int, outcome: Any) -> dict[str, Any]:
        found = await _voices(guild)
        row = next((one for one in found["voices"] if one["user_id"] == str(user_id)), None)
        return {"voice": row, "setting": found["setting"], "message": outcome.message}

    @router.get("/voices")
    async def chat_voices() -> dict[str, Any]:
        """Who hears what: every member with a tone row, and the server's setting above them."""
        guild = require_guild(bot)
        require_db(bot)
        return await _voices(guild)

    @router.put("/voices/{user_id}")
    async def chat_voice_pin(
        request: Request, user_id: int, payload: dict[str, Any]
    ) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        await personas.sync_tropes(bot.db, full=False)
        outcome = answered(
            await chat_panel.pin_voice(
                bot,
                guild,
                actor_for(bot, who, guild),
                user_id,
                payload.get("trope"),
                via=VIA_WEBSITE,
            )
        )
        return await _voice_answer(guild, user_id, outcome)

    @router.delete("/voices/{user_id}")
    async def chat_voice_clear(request: Request, user_id: int) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        outcome = answered(
            await chat_panel.clear_voice(
                bot, guild, actor_for(bot, who, guild), user_id, via=VIA_WEBSITE
            )
        )
        return await _voice_answer(guild, user_id, outcome)

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

    async def _channels(guild: Any) -> dict[str, Any]:
        """Every text channel, the ones the model is not told about included, with the why."""
        notes = await notes_for(bot.db, guild.id)
        drafts = await channel_drafts.drafts_for(bot.db, guild.id)
        hidden = hidden_category_ids(bot, guild)
        viewer = visibility_role(bot, guild)
        found = sorted(getattr(guild, "text_channels", ()) or (), key=channel_order)
        rows = [
            channel_row(
                one,
                notes,
                why_hidden(guild, one, hidden, viewer),
                drafts.get(int(one.id)),
                guild,
            )
            for one in found
        ]
        shown = directory_preview(bot, guild, notes)
        return {
            "channels": rows,
            "directory": shown.block,
            "budget": {"used": shown.used, "cap": shown.cap, "trimmed": list(shown.trimmed)},
            "note_chars": NOTE_CHARS,
            "counts": {
                "total": len(rows),
                "shown": sum(1 for row in rows if row["shown"]),
                "noted": sum(1 for row in rows if row["note"]),
            },
            "review": channel_drafts.review_counts(rows),
            "notes": [],
        }

    async def _channel_answer(guild: Any, channel_id: int, outcome: Any) -> dict[str, Any]:
        found = await _channels(guild)
        row = next((one for one in found["channels"] if one["id"] == str(channel_id)), None)
        return {
            "channel": row,
            "directory": found["directory"],
            "budget": found["budget"],
            "review": found["review"],
            "message": outcome.message,
        }

    @router.get("/channels")
    async def chat_channels() -> dict[str, Any]:
        guild = require_guild(bot)
        require_db(bot)
        return await _channels(guild)

    @router.put("/channels/{channel_id}")
    async def chat_channel_note(
        request: Request, channel_id: int, payload: dict[str, Any]
    ) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        outcome = answered(
            await channel_drafts.save_wording(
                bot,
                guild,
                actor_for(bot, who, guild),
                channel_id,
                payload.get("note"),
                via=VIA_WEBSITE,
            )
        )
        return await _channel_answer(guild, channel_id, outcome)

    @router.delete("/channels/{channel_id}")
    async def chat_channel_note_clear(request: Request, channel_id: int) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        outcome = answered(
            await channel_drafts.no_note(
                bot, guild, actor_for(bot, who, guild), channel_id, via=VIA_WEBSITE
            )
        )
        return await _channel_answer(guild, channel_id, outcome)

    async def _draft_move(request: Request, channel_id: int, move: Any) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        outcome = answered(
            await move(bot, guild, actor_for(bot, who, guild), channel_id, via=VIA_WEBSITE)
        )
        return await _channel_answer(guild, channel_id, outcome)

    @router.post("/channels/{channel_id}/use")
    async def chat_channel_draft_use(request: Request, channel_id: int) -> dict[str, Any]:
        return await _draft_move(request, channel_id, channel_drafts.use_draft)

    @router.post("/channels/{channel_id}/none")
    async def chat_channel_draft_none(request: Request, channel_id: int) -> dict[str, Any]:
        return await _draft_move(request, channel_id, channel_drafts.no_note)

    @router.post("/channels/{channel_id}/reset")
    async def chat_channel_draft_reset(request: Request, channel_id: int) -> dict[str, Any]:
        return await _draft_move(request, channel_id, channel_drafts.reset_draft)

    @router.get("/spend")
    async def chat_spend() -> dict[str, Any]:
        """What the month has cost, what today has asked for, and which tiers are answering."""
        guild = require_guild(bot)
        require_db(bot)
        at = datetime.now(UTC)
        spent = await chat_llm.month_spend(bot.db, chat_llm.month_start(at))
        turns = await chat_llm.server_turns(bot.db, chat_llm.day_start(at))
        cap_usd = float(bot.store.get(guild.id, chat_llm.MONTHLY_CAP_KEY))
        daily = bot.store.get(guild.id, chat_llm.DAILY_TURNS_KEY)
        mode_on = str(bot.store.get(guild.id, chat_llm.LLM_MODE_KEY)) == chat_llm.ON
        spent_usd = round(spent / chat_llm.MICRODOLLARS_IN_A_DOLLAR, 2)
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
            "cap_key": chat_llm.MONTHLY_CAP_KEY,
            "last_turn_at": await chat_llm.last_turn_at(bot.db),
            "notes": [],
        }

    return router


__all__ = ["build_router", "channel_order", "channel_row", "intent_row", "line_row"]
