from __future__ import annotations

import logging
from typing import Any, NamedTuple

from .actionlog import log_action
from .chat_llm import LLM_MODE_KEY, money
from .knowledge import (
    SERVER,
    SERVER_ROW_IS_NOT_YOURS,
    STAFF,
    KnowledgeError,
    add_section,
    clean_body,
    clean_tag,
    clean_title,
    get_section,
    remove_section,
    update_section,
)
from .logkinds import VIA_DISCORD, kind_via
from .panels import Outcome, refusal
from .panels import panel_minutes as library_panel_minutes
from .panels import site_page_url as library_site_page_url
from .personas import COOKOUT, PERSONALITY_KEY, POOL, forget_tropes, get_trope, list_tropes
from .personas import set_enabled as set_trope_enabled
from .settings_store import SettingError, coerce_value, parse_value

log = logging.getLogger(__name__)

MODE_KEY = "chat_mode"
PANEL_MINUTES_KEY = "chat_panel_minutes"
SITE_FEATURE = "chat"
ON = "on"
OFF = "off"

COOLDOWN_KEY = "chat_cooldown_seconds"
HOURLY_KEY = "chat_person_hourly_turns"
DAILY_KEY = "chat_daily_turns"
CAP_KEY = "chat_monthly_cap_usd"
SETTINGS_KEYS: tuple[str, ...] = (
    COOLDOWN_KEY,
    HOURLY_KEY,
    DAILY_KEY,
    CAP_KEY,
    PANEL_MINUTES_KEY,
)

PANEL_TITLE = "How Black Bloc answers"
PANEL_TIMEOUT_FOOTER = "This panel has gone quiet — run /chat again"

REFUSED = "chat_refused"
NO_SUCH_TROPE_CODE = "no_such_trope"
VOICE_IS_OFF_CODE = "voice_is_off"
VOICE_IN_USE_CODE = "voice_in_use"
LAST_VOICE_CODE = "last_voice"
TITLE_TAKEN_CODE = "title_taken"
NO_SUCH_SECTION_CODE = "no_such_section"
SERVER_ROW_CODE = "server_row"

STATUS_MODE = "Answering @-mentions: **{mode}**. Conversation model: **{llm}**."
STATUS_OFF_TAIL = " Every answer comes from Black Bloc's own written lines."
STATUS_TIERS = "Tiers — the quick one: {simple}. The careful one: {important}."
STATUS_TURNS = (
    "Answers today: **{today}** of {today_of}. Yours in the last hour: **{mine}** of {of}."
)
STATUS_MONEY = "This month so far: **{spent}** of {cap}."
STATUS_CLOSED = (
    "The models are resting until the 1st, so every answer comes from the written lines. Nothing "
    "is broken."
)
STATUS_INGEST_TROUBLE = "The last daily read did not finish: {why}."
STATUS_ADMIN_ONLY = (
    "What the conversation models have spent is kept to server administrators here, so those "
    "lines are not shown. Ask an Admin to read them out, or an Admin can switch "
    "`chat_status_admin_only` off if staff should see them too."
)
MEMORY_LINE = (
    "What Black Bloc remembers about a person is `/memory`'s, not this panel's — the eight "
    "`chat_memory_*` settings live on **Settings** and on the Chat page's Memory section."
)
NO_CEILING = "no ceiling"

VOICE_CHANGED = "The voice is **{voice}** from the next answer on."
MOOD_CHANGED = "**{name}** is {state}."
MODE_NEEDS_A_NAME = (
    "That arrived with no voice in it, so nothing was changed. Pick the cookout voice, the pool, "
    "or one of the names on the list."
)
NO_SUCH_TROPE = (
    "**{name}** is not one of the voices Black Bloc knows, so nothing was changed. The list on "
    "this page is all of them."
)
TROPE_IS_OFF = (
    "**{label}** is switched off in the pool, so Black Bloc cannot be it. Turn it back on first, "
    "or pick another one."
)
TROPE_IN_USE = (
    "Black Bloc is set to be **{label}** and nothing else, so that voice cannot be switched off. "
    "Point it at the cookout voice or the pool first."
)
LAST_TROPE_ON = (
    "**{label}** is the last voice left on and the pool is what Black Bloc is using, so it was "
    "left alone. Turn another one on first, or move the voice to the cookout one."
)
POOL_GUARDS = (
    "A mood the pool cannot do without is not on the list: the voice Black Bloc is set to, and "
    "the last one left on while the voice is `pool`. Move the voice first and they come back."
)

NOTE_SAVED = "Saved as note **{id}** — **{title}**. Black Bloc will quote it when it fits."
NOTE_EDITED = "Note **{id}** — **{title}** — is saved."
NOTE_REMOVED = "Note **{id}** — **{title}** — is gone."
NO_SUCH_NOTE = (
    "There is no note **{id}** in this server any more, so nothing was changed. Press "
    "**Refresh** and pick again."
)

MODE_SAVED = "**{key}** is now `{value}`."
SETTINGS_NOTHING = "Nothing was given, so nothing changed."
SETTINGS_SAVED = "Saved — "
SETTINGS_ONE = "**{key}** is now `{value}`"

PERSONALITY = "personality"
KNOWLEDGE = "knowledge"
SETTINGS = "settings"
CHAT_TOGGLE = "chat_toggle"
LLM_TOGGLE = "llm_toggle"
LOGS = "logs"
REFRESH = "refresh"
BACK = "back"
WRITE = "write"
FIND = "find"
REMOVE = "remove"
EDIT = "edit"
LIMITS = "limits"

ANSWER_ON = "Answer @-mentions"
ANSWER_OFF = "Stop answering @-mentions"
LLM_ON = "Turn the conversation models on"
LLM_OFF = "Turn the conversation models off"
REMOVE_QUESTION = "Remove note **{id}** — **{title}**? Black Bloc stops quoting it at once."
REMOVE_YES = "Yes, remove it"
KEEP_IT = "Keep it"


class PanelMove(NamedTuple):
    action: str
    label: str
    style: str = "secondary"
    row: int = 2


class PanelState(NamedTuple):
    chat_on: bool
    llm_on: bool


PERSONALITY_MOVE = PanelMove(PERSONALITY, "Personality…", row=0)
KNOWLEDGE_MOVE = PanelMove(KNOWLEDGE, "Knowledge…", row=0)
SETTINGS_MOVE = PanelMove(SETTINGS, "Settings", row=0)
LOGS_MOVE = PanelMove(LOGS, "Logs", row=2)
REFRESH_MOVE = PanelMove(REFRESH, "Refresh", row=2)
BACK_MOVE = PanelMove(BACK, "Back", row=2)
WRITE_MOVE = PanelMove(WRITE, "Write one down…", "primary", row=1)
FIND_MOVE = PanelMove(FIND, "Find…", row=1)
REMOVE_MOVE = PanelMove(REMOVE, "Remove", "danger", row=0)
EDIT_MOVE = PanelMove(EDIT, "Edit…", "primary", row=0)
NOTE_BACK_MOVE = PanelMove(BACK, "Back", row=0)
LIMITS_MOVE = PanelMove(LIMITS, "Limits…", "primary", row=0)

PANEL_MOVES: tuple[PanelMove, ...] = (
    PERSONALITY_MOVE,
    KNOWLEDGE_MOVE,
    SETTINGS_MOVE,
    PanelMove(CHAT_TOGGLE, ANSWER_ON, row=1),
    PanelMove(LLM_TOGGLE, LLM_ON, row=1),
    LOGS_MOVE,
    REFRESH_MOVE,
    BACK_MOVE,
    WRITE_MOVE,
    FIND_MOVE,
    REMOVE_MOVE,
    EDIT_MOVE,
    LIMITS_MOVE,
)


def toggle_move(state: PanelState, key: str) -> PanelMove:
    """One button that says what it will do, never a menu with two spellings of one move."""
    if key == MODE_KEY:
        return PanelMove(CHAT_TOGGLE, ANSWER_OFF if state.chat_on else ANSWER_ON, row=1)
    return PanelMove(LLM_TOGGLE, LLM_OFF if state.llm_on else LLM_ON, row=1)


def panel_state(store: Any, guild_id: int) -> PanelState:
    return PanelState(
        chat_on=str(store.get(guild_id, MODE_KEY)) == ON,
        llm_on=str(store.get(guild_id, LLM_MODE_KEY)) == ON,
    )


def panel_buttons(state: PanelState, *, staff: bool = True) -> tuple[PanelMove, ...]:
    """The §C root table as data; there is no member half of chat to render."""
    if not staff:
        return ()
    return (
        PERSONALITY_MOVE,
        KNOWLEDGE_MOVE,
        SETTINGS_MOVE,
        toggle_move(state, MODE_KEY),
        toggle_move(state, LLM_MODE_KEY),
        LOGS_MOVE,
        REFRESH_MOVE,
    )


def knowledge_buttons(*, notes: int) -> tuple[PanelMove, ...]:
    found = [WRITE_MOVE]
    if notes:
        found.append(FIND_MOVE)
    return (*found, BACK_MOVE, REFRESH_MOVE)


def note_buttons(source: Any) -> tuple[PanelMove, ...]:
    """A `server` row renders neither move — the daily read would undo both by morning."""
    if str(source) == STAFF:
        return (REMOVE_MOVE, EDIT_MOVE, NOTE_BACK_MOVE)
    return (NOTE_BACK_MOVE,)


def settings_buttons() -> tuple[PanelMove, ...]:
    return (LIMITS_MOVE, BACK_MOVE, REFRESH_MOVE)


def personality_buttons() -> tuple[PanelMove, ...]:
    return (BACK_MOVE, REFRESH_MOVE)


def status_lines(
    store: Any,
    guild_id: int,
    *,
    tiers: tuple[str, str],
    spend: Any = None,
    hidden: bool = False,
    notes: str = "",
    trouble: str = "",
) -> list[str]:
    """The status block as a list, so the panel embed and any later read share one home."""
    llm_on = str(store.get(guild_id, LLM_MODE_KEY)) == ON
    lines = [
        STATUS_MODE.format(mode=store.get(guild_id, MODE_KEY), llm=ON if llm_on else OFF)
        + ("" if llm_on else STATUS_OFF_TAIL),
        STATUS_TIERS.format(simple=tiers[0], important=tiers[1]),
    ]
    if spend is not None:
        lines.append(
            STATUS_TURNS.format(
                today=spend.today,
                today_of=spend.today_of or NO_CEILING,
                mine=spend.person,
                of=spend.person_of or NO_CEILING,
            )
        )
        lines.append(STATUS_MONEY.format(spent=money(spend.spent), cap=f"${int(spend.cap)}"))
        if not spend.ok:
            lines.append(STATUS_CLOSED)
    elif hidden:
        lines.append(STATUS_ADMIN_ONLY)
    if notes:
        lines.append(notes)
    if trouble:
        lines.append(STATUS_INGEST_TROUBLE.format(why=trouble))
    return lines


def mood_refusal(rows: Any, row: Any, enabled: bool, voice: Any) -> Outcome | None:
    """Fork F-C4's two guards, in the ONE place the select and `set_mood` both read."""
    if enabled:
        return None
    found = list(rows or ())
    name = str(row["name"])
    label = str(row["label"])
    if str(voice or "").strip().lower() == name:
        return refusal(TROPE_IN_USE.format(label=label), VOICE_IN_USE_CODE, 409)
    on_now = [one for one in found if one["enabled"]]
    if len(on_now) == 1 and str(on_now[0]["name"]) == name and str(voice) == POOL:
        return refusal(LAST_TROPE_ON.format(label=label), LAST_VOICE_CODE, 409)
    return None


def mood_options(rows: Any, voice: Any) -> tuple[tuple[Any, ...], tuple[Any, ...]]:
    """(may be turned off, may be turned on) — a mood the guards refuse is never offered."""
    found = list(rows or ())
    may_go_off = tuple(
        row
        for row in found
        if row["enabled"] and mood_refusal(found, row, False, voice) is None
    )
    may_come_on = tuple(row for row in found if not row["enabled"])
    return (may_go_off, may_come_on)


def guarded_moods(rows: Any, voice: Any) -> tuple[Any, ...]:
    """The enabled moods the guards hold back, so the embed can say why they are missing."""
    found = list(rows or ())
    return tuple(
        row
        for row in found
        if row["enabled"] and mood_refusal(found, row, False, voice) is not None
    )


def actor_id(actor: Any) -> int | None:
    return int(getattr(actor, "id", actor) or 0) or None


async def set_voice(
    bot: Any, guild: Any, actor: Any, wanted: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    """The voice for this server — both doors refuse the same three things."""
    said = str(wanted or "").strip().lower()
    if not said:
        return refusal(MODE_NEEDS_A_NAME, REFUSED, 400)
    if said not in (COOKOUT, POOL):
        row = await get_trope(bot.db, said)
        if row is None:
            return refusal(NO_SUCH_TROPE.format(name=said[:40]), NO_SUCH_TROPE_CODE, 404)
        if not row["enabled"]:
            return refusal(
                TROPE_IS_OFF.format(label=str(row["label"])), VOICE_IS_OFF_CODE, 409
            )
    await bot.store.set(guild.id, PERSONALITY_KEY, said, by=actor_id(actor))
    await log_action(
        bot,
        guild,
        kind_via("chat.personality_mode", via),
        actor=actor,
        details={"voice": said, "via": via},
    )
    return Outcome(True, VOICE_CHANGED.format(voice=said), value=said)


async def set_mood(
    bot: Any, guild: Any, actor: Any, name: Any, enabled: bool, *, via: str = VIA_DISCORD
) -> Outcome:
    """One mood in or out of the pool, with the pool-emptying guards on both doors."""
    said = str(name or "").strip().lower()
    row = await get_trope(bot.db, said)
    if row is None:
        return refusal(NO_SUCH_TROPE.format(name=said[:40]), NO_SUCH_TROPE_CODE, 404)
    rows = await list_tropes(bot.db)
    voice = bot.store.get(guild.id, PERSONALITY_KEY)
    held = mood_refusal(rows, row, bool(enabled), voice)
    if held is not None:
        return held
    await set_trope_enabled(bot.db, str(row["name"]), bool(enabled), by=actor_id(actor))
    forget_tropes(bot)
    await log_action(
        bot,
        guild,
        kind_via("chat.trope_enabled" if enabled else "chat.trope_disabled", via),
        actor=actor,
        details={"mood": str(row["name"]), "enabled": bool(enabled), "via": via},
    )
    return Outcome(
        True,
        MOOD_CHANGED.format(name=str(row["name"]), state=ON if enabled else OFF),
        value=str(row["name"]),
    )


async def add_note(
    bot: Any,
    guild: Any,
    actor: Any,
    title: Any,
    body: Any,
    tag: Any = "",
    *,
    via: str = VIA_DISCORD,
) -> Outcome:
    try:
        wanted = (clean_title(title), clean_body(body), clean_tag(tag))
    except KnowledgeError as exc:
        return refusal(str(exc), REFUSED, 400)
    try:
        made = await add_section(
            bot.db, guild.id, wanted[0], wanted[1], tag=wanted[2], by=actor_id(actor)
        )
    except KnowledgeError as exc:
        return refusal(str(exc), TITLE_TAKEN_CODE, 409)
    await log_action(
        bot,
        guild,
        kind_via("chat.knowledge_added", via),
        actor=actor,
        details={"id": made, "title": wanted[0], "via": via},
    )
    return Outcome(True, NOTE_SAVED.format(id=made, title=wanted[0]), value=made)


async def wanted_note(bot: Any, guild: Any, section_id: Any) -> tuple[Any, Outcome | None]:
    """One note of THIS server, or the refusal — the guild check both doors need."""
    try:
        wanted = int(section_id)
    except (TypeError, ValueError):
        return (None, refusal(NO_SUCH_NOTE.format(id=section_id), NO_SUCH_SECTION_CODE, 404))
    row = await get_section(bot.db, wanted)
    if row is None or int(row["guild_id"]) != guild.id:
        return (None, refusal(NO_SUCH_NOTE.format(id=wanted), NO_SUCH_SECTION_CODE, 404))
    if str(row["source"]) == SERVER:
        return (row, refusal(SERVER_ROW_IS_NOT_YOURS, SERVER_ROW_CODE, 409))
    return (row, None)


async def edit_note(
    bot: Any,
    guild: Any,
    actor: Any,
    section_id: Any,
    fields: Any,
    *,
    via: str = VIA_DISCORD,
) -> Outcome:
    """The same three fields the add modal takes, saved in place — same id, same row."""
    row, held = await wanted_note(bot, guild, section_id)
    if held is not None:
        return held
    given = dict(fields or {})
    wanted: dict[str, Any] = {}
    try:
        if "title" in given:
            wanted["title"] = clean_title(given["title"])
        if "body" in given:
            wanted["body"] = clean_body(given["body"])
        if "tag" in given:
            wanted["tag"] = clean_tag(given["tag"])
    except KnowledgeError as exc:
        return refusal(str(exc), REFUSED, 400)
    if not wanted:
        return refusal(SETTINGS_NOTHING, REFUSED, 400)
    changed = sorted(wanted)
    try:
        await update_section(bot.db, int(row["id"]), by=actor_id(actor), **wanted)
    except KnowledgeError as exc:
        return refusal(str(exc), TITLE_TAKEN_CODE, 409)
    title = str(wanted.get("title", row["title"]))
    await log_action(
        bot,
        guild,
        kind_via("chat.knowledge_edited", via),
        actor=actor,
        details={"id": int(row["id"]), "title": title, "changed": changed, "via": via},
    )
    return Outcome(
        True, NOTE_EDITED.format(id=int(row["id"]), title=title), value=int(row["id"])
    )


async def remove_note(
    bot: Any, guild: Any, actor: Any, section_id: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    row, held = await wanted_note(bot, guild, section_id)
    if held is not None:
        return held
    title = str(row["title"])
    wanted = int(row["id"])
    await remove_section(bot.db, wanted)
    await log_action(
        bot,
        guild,
        kind_via("chat.knowledge_removed", via),
        actor=actor,
        details={"id": wanted, "title": title, "via": via},
    )
    return Outcome(True, NOTE_REMOVED.format(id=wanted, title=title), value=wanted)


async def set_mode(
    bot: Any, guild: Any, actor: Any, key: str, value: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    """Either chat mode, one write and one `chat.mode` row, whichever door turned it."""
    if key not in (MODE_KEY, LLM_MODE_KEY):
        return refusal(SETTINGS_NOTHING, REFUSED, 400)
    try:
        wanted = coerce_value(key, value)
    except SettingError as exc:
        return refusal(str(exc), REFUSED, 400)
    await bot.store.set(guild.id, key, wanted, by=actor_id(actor))
    await log_action(
        bot,
        guild,
        kind_via("chat.mode", via),
        actor=actor,
        details={"key": key, "value": wanted, "via": via},
    )
    return Outcome(True, MODE_SAVED.format(key=key, value=wanted), value=wanted)


def read_limits(given: Any) -> Outcome:
    """Every field read and bounded BEFORE the first write, so a bad one saves nothing."""
    wanted: dict[str, Any] = {}
    for key in SETTINGS_KEYS:
        if key not in (given or {}):
            continue
        try:
            wanted[key] = coerce_value(key, parse_value(key, str(given[key])))
        except SettingError as exc:
            return refusal(str(exc), REFUSED, 400)
    if not wanted:
        return refusal(SETTINGS_NOTHING, REFUSED, 400)
    return Outcome(True, "", value=wanted)


async def save_settings(
    bot: Any, guild: Any, actor: Any, changes: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    """One dict, validated whole, then written key by key and logged exactly once."""
    wanted = {key: value for key, value in (changes or {}).items() if key in SETTINGS_KEYS}
    if not wanted:
        return refusal(SETTINGS_NOTHING, REFUSED, 400)
    for key, value in wanted.items():
        try:
            coerce_value(key, value)
        except SettingError as exc:
            return refusal(str(exc), REFUSED, 400)
    by = actor_id(actor)
    for key, value in wanted.items():
        await bot.store.set(guild.id, key, value, by=by)
    await log_action(
        bot,
        guild,
        kind_via("chat.settings", via),
        actor=actor,
        details={"changed": {key: str(value)[:80] for key, value in wanted.items()}, "via": via},
    )
    return Outcome(True, settings_saved(wanted), value=wanted)


def settings_saved(changed: dict[str, Any]) -> str:
    return SETTINGS_SAVED + ", ".join(
        SETTINGS_ONE.format(key=key, value=value) for key, value in changed.items()
    )


def panel_minutes(store: Any, guild_id: int) -> int:
    return library_panel_minutes(store, guild_id, PANEL_MINUTES_KEY)


def site_page_url(origin: Any) -> str | None:
    return library_site_page_url(origin, SITE_FEATURE)


__all__ = [
    "CAP_KEY",
    "COOLDOWN_KEY",
    "DAILY_KEY",
    "HOURLY_KEY",
    "LAST_TROPE_ON",
    "MODE_KEY",
    "MODE_NEEDS_A_NAME",
    "NOTE_REMOVED",
    "NOTE_SAVED",
    "NO_SUCH_NOTE",
    "NO_SUCH_TROPE",
    "PANEL_MINUTES_KEY",
    "PANEL_MOVES",
    "PANEL_TIMEOUT_FOOTER",
    "PANEL_TITLE",
    "POOL_GUARDS",
    "SETTINGS_KEYS",
    "TROPE_IN_USE",
    "TROPE_IS_OFF",
    "Outcome",
    "PanelMove",
    "PanelState",
    "add_note",
    "edit_note",
    "guarded_moods",
    "knowledge_buttons",
    "mood_options",
    "mood_refusal",
    "note_buttons",
    "panel_buttons",
    "panel_minutes",
    "panel_state",
    "personality_buttons",
    "read_limits",
    "remove_note",
    "save_settings",
    "set_mode",
    "set_mood",
    "set_voice",
    "settings_buttons",
    "settings_saved",
    "site_page_url",
    "status_lines",
    "toggle_move",
    "wanted_note",
]
