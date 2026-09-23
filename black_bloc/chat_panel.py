from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any, NamedTuple

from . import chat_review
from .actionlog import log_action
from .channel_notes import NOTE_CHARS, clean_note, clear_note, get_note, set_note
from .chat_llm import LLM_MODE_KEY, money
from .chat_voice import pin, roster, talking_now, unpin, voice_rows
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
from .panels import KEEP_IT as KEEP_IT
from .panels import Outcome, refusal
from .panels import panel_minutes as library_panel_minutes
from .panels import site_page_url as library_site_page_url
from .personas import (
    COOKOUT,
    PERSONALITY_KEY,
    POOL,
    forget_tropes,
    get_trope,
    list_tropes,
    reset_voice,
    write_voice,
)
from .personas import set_enabled as set_trope_enabled
from .settings_store import (
    CHANNEL_NOTE_CLEARED_KEY,
    CHANNEL_NOTE_NO_CHANNEL_KEY,
    CHANNEL_NOTE_NOTHING_KEY,
    CHANNEL_NOTE_SAVED_KEY,
    CHANNEL_NOTE_TOO_LONG_KEY,
    CHANNEL_NOTE_WORDS,
    CHANNEL_NOTES_BUTTON_KEY,
    REVIEW_ADDED_LINE_KEY,
    REVIEW_ADDED_PHRASE_KEY,
    REVIEW_DECIDED_KEY,
    REVIEW_DISMISSED_KEY,
    REVIEW_ITEM_KEY,
    REVIEW_LINE_KEY,
    REVIEW_MADE_INTENT_KEY,
    REVIEW_NO_SUCH_KEY,
    REVIEW_NOT_DISMISSED_KEY,
    REVIEW_NOTHING_KEY,
    REVIEW_REOPENED_KEY,
    TONE_EDITED_KEY,
    TONE_RESET_KEY,
    TONE_TOO_LONG_KEY,
    VOICE_ACTIVE_KEY,
    VOICE_CLEARED_KEY,
    VOICE_LINE_PINNED_KEY,
    VOICE_LINE_ROLLED_KEY,
    VOICE_LINE_WAITING_KEY,
    VOICE_NO_MEMBER_KEY,
    VOICE_NO_TONE_KEY,
    VOICE_NOTHING_KEY,
    VOICE_PINNED_KEY,
    VOICE_TONE_OFF_KEY,
    VOICE_WORDS,
    SettingError,
    coerce_value,
    parse_value,
)

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
NO_SUCH_CHANNEL_CODE = "no_such_channel"
NOTE_TOO_LONG_CODE = "note_too_long"
NO_SUCH_MEMBER_CODE = "no_such_member"
TONE_UNUSABLE_CODE = "tone_unusable"
TONE_TOO_LONG_CODE = "tone_too_long"
TONE_CHARS = 1200
WORDS: dict[str, tuple[str, tuple[str, ...], str]] = {**CHANNEL_NOTE_WORDS, **VOICE_WORDS}

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
VOICES = "voices"
CLEAR_PIN = "clear_pin"
PREVIOUS = "previous"
NEXT = "next"
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
CHANNELS = "channels"
REVIEW = "review"
REVIEW_PREVIOUS = "review_previous"
REVIEW_NEXT = "review_next"
APPROVE = "approve"
DISMISS = "dismiss"
FACT = "fact"

ANSWER_ON = "Answer @-mentions"
ANSWER_OFF = "Stop answering @-mentions"
LLM_ON = "Turn the conversation models on"
LLM_OFF = "Turn the conversation models off"
REMOVE_QUESTION = "Remove note **{id}** — **{title}**? Black Bloc stops quoting it at once."
REMOVE_YES = "Yes, remove it"


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
CHANNELS_MOVE = PanelMove(CHANNELS, CHANNEL_NOTE_WORDS[CHANNEL_NOTES_BUTTON_KEY][0], row=0)
VOICES_MOVE = PanelMove(VOICES, "Who hears what…", "primary", row=3)
CLEAR_PIN_MOVE = PanelMove(CLEAR_PIN, "Clear the pin", "danger", row=1)
PREVIOUS_MOVE = PanelMove(PREVIOUS, "‹ Previous", row=2)
NEXT_MOVE = PanelMove(NEXT, "Next ›", row=2)
VOICES_PAGE = 25

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
    CHANNELS_MOVE,
    VOICES_MOVE,
    CLEAR_PIN_MOVE,
    PREVIOUS_MOVE,
    NEXT_MOVE,
    PanelMove(REVIEW, "Review queue…", row=1),
    PanelMove(REVIEW_PREVIOUS, "‹ Previous", row=1),
    PanelMove(REVIEW_NEXT, "Next ›", row=1),
    PanelMove(APPROVE, "Approve", "success", row=1),
    PanelMove(FACT, "Write a fact…", "primary", row=1),
    PanelMove(DISMISS, "Dismiss", "danger", row=1),
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


def panel_buttons(
    state: PanelState, *, staff: bool = True, channels_label: str = "", review_label: str = ""
) -> tuple[PanelMove, ...]:
    """The §C root table as data; there is no member half of chat to render."""
    if not staff:
        return ()
    return (
        PERSONALITY_MOVE,
        KNOWLEDGE_MOVE,
        SETTINGS_MOVE,
        CHANNELS_MOVE._replace(label=channels_label or CHANNELS_MOVE.label),
        toggle_move(state, MODE_KEY),
        toggle_move(state, LLM_MODE_KEY),
        PanelMove(REVIEW, review_label or "Review queue…", row=1),
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


def channel_notes_buttons() -> tuple[PanelMove, ...]:
    return (BACK_MOVE._replace(row=1), REFRESH_MOVE._replace(row=1))


def settings_buttons() -> tuple[PanelMove, ...]:
    return (LIMITS_MOVE, BACK_MOVE, REFRESH_MOVE)


def personality_buttons(voices_label: str = "") -> tuple[PanelMove, ...]:
    return (
        VOICES_MOVE._replace(label=voices_label or VOICES_MOVE.label),
        BACK_MOVE._replace(row=3),
        REFRESH_MOVE._replace(row=3),
    )


def voices_buttons(
    page: int, pages: int, labels: tuple[str, str] = ("", "")
) -> tuple[PanelMove, ...]:
    """Previous and Next render only when there is somewhere to go."""
    found = []
    if page > 1:
        found.append(PREVIOUS_MOVE._replace(label=labels[0] or PREVIOUS_MOVE.label))
    if page < pages:
        found.append(NEXT_MOVE._replace(label=labels[1] or NEXT_MOVE.label))
    return (*found, BACK_MOVE._replace(row=3), REFRESH_MOVE._replace(row=3))


def member_buttons(pinned: bool, clear_label: str = "") -> tuple[PanelMove, ...]:
    """Clear renders only on a member who has a pin to clear."""
    found = [CLEAR_PIN_MOVE._replace(label=clear_label or CLEAR_PIN_MOVE.label)] if pinned else []
    return (*found, BACK_MOVE._replace(row=2), REFRESH_MOVE._replace(row=2))


def page_count(total: int) -> int:
    return max(1, -(-int(total or 0) // VOICES_PAGE))


def wanted_page(page: Any, pages: int) -> int:
    try:
        asked = int(page or 1)
    except (TypeError, ValueError):
        asked = 1
    return max(1, min(asked, pages))


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


def words(store: Any, guild_id: int, key: str, **values: Any) -> str:
    """Staff's wording, or the registry's when theirs will not format — never a crash."""
    try:
        return str(store.get(guild_id, key)).format(**values)
    except Exception as exc:
        log.warning("chat: %s would not format, so the default was said — %s", key, exc)
        return WORDS[key][0].format(**values)


def text_channel(guild: Any, channel_id: Any) -> Any:
    """Only a text channel of THIS guild takes a note; the directory reads nothing else."""
    try:
        wanted = int(getattr(channel_id, "id", channel_id))
    except (TypeError, ValueError):
        return None
    return next(
        (one for one in getattr(guild, "text_channels", ()) or () if one.id == wanted), None
    )


def no_such_channel(bot: Any, guild: Any, channel_id: Any) -> Outcome:
    return refusal(
        words(bot.store, guild.id, CHANNEL_NOTE_NO_CHANNEL_KEY, channel=str(channel_id)[:40]),
        NO_SUCH_CHANNEL_CODE,
        404,
    )


async def save_channel_note(
    bot: Any, guild: Any, actor: Any, channel_id: Any, text: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    """The one write both doors use; a blank note is a clear, never an empty row."""
    channel = text_channel(guild, channel_id)
    if channel is None:
        return no_such_channel(bot, guild, channel_id)
    note = clean_note(text)
    if not note:
        return await clear_channel_note(bot, guild, actor, channel.id, via=via)
    if len(note) > NOTE_CHARS:
        return refusal(
            words(
                bot.store,
                guild.id,
                CHANNEL_NOTE_TOO_LONG_KEY,
                length=len(note),
                limit=NOTE_CHARS,
                over=len(note) - NOTE_CHARS,
            ),
            NOTE_TOO_LONG_CODE,
            422,
        )
    await set_note(bot.db, guild.id, channel.id, note, by=actor_id(actor))
    await log_action(
        bot,
        guild,
        kind_via("chat.channel_note_set", via),
        actor=actor,
        details={"channel_id": str(channel.id), "channel": channel.name, "note": note, "via": via},
    )
    return Outcome(
        True,
        words(bot.store, guild.id, CHANNEL_NOTE_SAVED_KEY, channel=channel.name),
        value=note,
    )


async def clear_channel_note(
    bot: Any, guild: Any, actor: Any, channel_id: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    channel = text_channel(guild, channel_id)
    if channel is None:
        return no_such_channel(bot, guild, channel_id)
    if not await clear_note(bot.db, guild.id, channel.id):
        return Outcome(
            True, words(bot.store, guild.id, CHANNEL_NOTE_NOTHING_KEY, channel=channel.name)
        )
    await log_action(
        bot,
        guild,
        kind_via("chat.channel_note_cleared", via),
        actor=actor,
        details={"channel_id": str(channel.id), "channel": channel.name, "via": via},
    )
    return Outcome(True, words(bot.store, guild.id, CHANNEL_NOTE_CLEARED_KEY, channel=channel.name))


async def channel_note(bot: Any, guild: Any, channel_id: Any) -> str:
    row = await get_note(bot.db, guild.id, channel_id)
    return str(row["note"]) if row is not None else ""


def member_of(guild: Any, user_id: Any) -> Any:
    try:
        wanted = int(getattr(user_id, "id", user_id))
    except (TypeError, ValueError):
        return None
    getter = getattr(guild, "get_member", None)
    found = getter(wanted) if getter is not None else None
    return None if found is None or getattr(found, "bot", False) else found


def member_name(member: Any) -> str:
    return str(getattr(member, "display_name", None) or getattr(member, "name", "") or member.id)


async def usable_tone(bot: Any, guild: Any, tone: Any) -> tuple[Any, Outcome | None]:
    said = str(tone or "").strip().lower()
    row = None if said in ("", COOKOUT, POOL) else await get_trope(bot.db, said)
    if row is None:
        return (None, refusal(
            words(bot.store, guild.id, VOICE_NO_TONE_KEY, tone=said[:40] or "nothing"),
            TONE_UNUSABLE_CODE,
            422,
        ))
    if not row["enabled"]:
        return (None, refusal(
            words(bot.store, guild.id, VOICE_TONE_OFF_KEY, tone=str(row["label"])),
            TONE_UNUSABLE_CODE,
            422,
        ))
    return (row, None)


async def pin_voice(
    bot: Any, guild: Any, actor: Any, user_id: Any, tone: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    """The one write both doors use to fix a member's tone; staff's pin beats every roll."""
    member = member_of(guild, user_id)
    if member is None:
        return refusal(
            words(bot.store, guild.id, VOICE_NO_MEMBER_KEY, member=str(user_id)[:40]),
            NO_SUCH_MEMBER_CODE,
            404,
        )
    row, held = await usable_tone(bot, guild, tone)
    if held is not None:
        return held
    name = str(row["name"])
    await pin(bot.db, guild.id, member.id, name, by=actor_id(actor))
    await log_action(
        bot,
        guild,
        kind_via("chat.voice_pinned", via),
        actor=actor,
        target=member,
        details={"member": str(member.id), "tone": name, "via": via},
    )
    return Outcome(
        True,
        words(
            bot.store,
            guild.id,
            VOICE_PINNED_KEY,
            member=member_name(member),
            tone=str(row["label"]),
        ),
        value=name,
    )


async def clear_voice(
    bot: Any, guild: Any, actor: Any, user_id: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    """A cleared pin hands the member back to the server's setting; a missing one says so."""
    try:
        wanted = int(getattr(user_id, "id", user_id))
    except (TypeError, ValueError):
        return refusal(
            words(bot.store, guild.id, VOICE_NO_MEMBER_KEY, member=str(user_id)[:40]),
            NO_SUCH_MEMBER_CODE,
            404,
        )
    member = member_of(guild, wanted)
    name = member_name(member) if member is not None else str(wanted)
    if not await unpin(bot.db, guild.id, wanted):
        return Outcome(True, words(bot.store, guild.id, VOICE_NOTHING_KEY, member=name))
    await log_action(
        bot,
        guild,
        kind_via("chat.voice_cleared", via),
        actor=actor,
        target=member if member is not None else wanted,
        details={"member": str(wanted), "via": via},
    )
    return Outcome(True, words(bot.store, guild.id, VOICE_CLEARED_KEY, member=name))


async def voice_roster(bot: Any, guild: Any, *, now: Any = None) -> dict[str, Any]:
    """Who hears what: the rows, the server's setting, and which tones are on."""
    at = now or datetime.now(UTC)
    setting = str(bot.store.get(guild.id, PERSONALITY_KEY) or COOKOUT)
    tropes = await list_tropes(bot.db)
    enabled = [str(row["name"]) for row in tropes if row["enabled"]]
    rows = await voice_rows(bot.db, guild.id)
    talking = await talking_now(bot.db, guild.id, now=at)
    return {
        "setting": setting,
        "enabled": enabled,
        "labels": {str(row["name"]): str(row["label"]) for row in tropes},
        "voices": roster(rows, setting, enabled, talking),
    }


def voice_line(store: Any, guild_id: int, entry: dict[str, Any], labels: dict[str, str]) -> str:
    """One member's line on the Who hears what card, in the words staff chose."""
    member = f"<@{entry['user_id']}>"
    pinned = entry["pinned"]
    if entry["waiting"]:
        said = words(
            store, guild_id, VOICE_LINE_WAITING_KEY, member=member, tone=labels.get(pinned, pinned)
        )
    elif pinned:
        by = f"<@{entry['pinned_by']}>" if entry["pinned_by"] else "staff"
        said = words(
            store,
            guild_id,
            VOICE_LINE_PINNED_KEY,
            member=member,
            tone=labels.get(pinned, pinned),
            by=by,
        )
    else:
        tone = str(entry["trope"])
        said = words(
            store,
            guild_id,
            VOICE_LINE_ROLLED_KEY,
            member=member,
            tone=labels.get(tone, tone),
            turns=entry["turns"],
        )
    if entry["active"]:
        said = f"{said} · {words(store, guild_id, VOICE_ACTIVE_KEY)}"
    return said


async def edit_tone(
    bot: Any, guild: Any, actor: Any, name: Any, voice: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    """A tone's wording, written by staff and kept across syncs; blank puts the shipped one back."""
    said = str(name or "").strip().lower()
    row = await get_trope(bot.db, said)
    if row is None:
        return refusal(NO_SUCH_TROPE.format(name=said[:40]), NO_SUCH_TROPE_CODE, 404)
    text = str(voice or "").strip()
    label = str(row["label"])
    if len(text) > TONE_CHARS:
        return refusal(
            words(
                bot.store,
                guild.id,
                TONE_TOO_LONG_KEY,
                length=len(text),
                limit=TONE_CHARS,
                over=len(text) - TONE_CHARS,
            ),
            TONE_TOO_LONG_CODE,
            422,
        )
    by = actor_id(actor)
    if text:
        await write_voice(bot.db, said, text, by=by)
    else:
        await reset_voice(bot.db, said, by=by)
    forget_tropes(bot)
    await log_action(
        bot,
        guild,
        kind_via("chat.tone_edited", via),
        actor=actor,
        details={"mood": said, "reset": not text, "voice": text[:200], "via": via},
    )
    key = TONE_EDITED_KEY if text else TONE_RESET_KEY
    return Outcome(True, words(bot.store, guild.id, key, tone=label), value=said)


def settings_saved(changed: dict[str, Any]) -> str:
    return SETTINGS_SAVED + ", ".join(
        SETTINGS_ONE.format(key=key, value=value) for key, value in changed.items()
    )


def panel_minutes(store: Any, guild_id: int) -> int:
    return library_panel_minutes(store, guild_id, PANEL_MINUTES_KEY)


def site_page_url(origin: Any) -> str | None:
    return library_site_page_url(origin, SITE_FEATURE)


REVIEW_NO_SUCH_CODE = "no_such_review"
REVIEW_DECIDED_CODE = "already_decided"
REVIEW_NOTHING_CODE = "nothing_to_approve"
REVIEW_NOT_DISMISSED_CODE = "not_dismissed"
REVIEW_REFUSED_CODE = "review_refused"
REVIEW_PAGE_SIZE = 5
REVIEW_MOVE = PanelMove(REVIEW, "Review queue…", row=1)
REVIEW_PREVIOUS_MOVE = PanelMove(REVIEW_PREVIOUS, "‹ Previous", row=1)
REVIEW_NEXT_MOVE = PanelMove(REVIEW_NEXT, "Next ›", row=1)
APPROVE_MOVE = PanelMove(APPROVE, "Approve", "success", row=1)
FACT_MOVE = PanelMove(FACT, "Write a fact…", "primary", row=1)
DISMISS_MOVE = PanelMove(DISMISS, "Dismiss", "danger", row=1)


def review_words(bot: Any, guild: Any, key: str, **values: Any) -> str:
    return chat_review.words(bot.store, guild.id, key, **values)


def review_pages(total: int) -> int:
    return max(1, -(-int(total or 0) // REVIEW_PAGE_SIZE))


def review_buttons(
    page: int, pages: int, labels: tuple[str, str] = ("", "")
) -> tuple[PanelMove, ...]:
    """Previous and Next render only when there is somewhere to go."""
    found = []
    if page > 1:
        found.append(REVIEW_PREVIOUS_MOVE._replace(label=labels[0] or REVIEW_PREVIOUS_MOVE.label))
    if page < pages:
        found.append(REVIEW_NEXT_MOVE._replace(label=labels[1] or REVIEW_NEXT_MOVE.label))
    return (*found, BACK_MOVE, REFRESH_MOVE)


def review_item_buttons(
    *, can_approve: bool, labels: tuple[str, str, str] = ("", "", "")
) -> tuple[PanelMove, ...]:
    """Approve renders only on an item whose suggestion teaches something."""
    found = [APPROVE_MOVE._replace(label=labels[0] or APPROVE_MOVE.label)] if can_approve else []
    found.append(FACT_MOVE._replace(label=labels[1] or FACT_MOVE.label))
    found.append(DISMISS_MOVE._replace(label=labels[2] or DISMISS_MOVE.label))
    return (*found, BACK_MOVE, REFRESH_MOVE)


def teaches(row: Any) -> bool:
    found = chat_review.suggestion_of(row)
    return found is not None and found.kind in chat_review.TEACHES


async def wanted_review(bot: Any, guild: Any, item_id: Any) -> tuple[Any, Outcome | None]:
    """One review item of THIS server, or the refusal both doors say."""
    row = await chat_review.get_item(bot.db, item_id)
    if row is None or int(row["guild_id"]) != guild.id:
        said = review_words(bot, guild, REVIEW_NO_SUCH_KEY, id=str(item_id)[:20])
        return (None, refusal(said, REVIEW_NO_SUCH_CODE, 404))
    return (row, None)


def decided_already(bot: Any, guild: Any, row: Any) -> Outcome:
    said = review_words(bot, guild, REVIEW_DECIDED_KEY, id=int(row["id"]), status=row["status"])
    return refusal(said, REVIEW_DECIDED_CODE, 409)


def taught_word(bot: Any, guild: Any, taught: Any) -> str:
    if taught.kind == chat_review.KNOWLEDGE:
        return review_words(bot, guild, REVIEW_ADDED_LINE_KEY, section=taught.section)
    if taught.made:
        return review_words(
            bot, guild, REVIEW_MADE_INTENT_KEY, intent=taught.intent, phrase=taught.phrase
        )
    return review_words(
        bot, guild, REVIEW_ADDED_PHRASE_KEY, phrase=taught.phrase, intent=taught.intent
    )


def review_refusal(bot: Any, guild: Any, exc: Any) -> Outcome:
    said = review_words(bot, guild, exc.key, **exc.values) if exc.key else exc.said
    return refusal(said, REVIEW_REFUSED_CODE, 400)


async def settle_review(
    bot: Any, guild: Any, actor: Any, row: Any, found: Any, status: str, via: str
) -> Outcome:
    """Claim the item, then write; a write that is refused hands the item back open."""
    by = actor_id(actor)
    changed = status == chat_review.CHANGED
    if not await chat_review.decide(bot.db, int(row["id"]), status, by):
        fresh = await chat_review.get_item(bot.db, int(row["id"]))
        return decided_already(bot, guild, fresh or row)
    try:
        taught = await chat_review.teach(bot, guild.id, found, by)
    except chat_review.ReviewError as exc:
        await chat_review.undecide(bot.db, int(row["id"]), status)
        return review_refusal(bot, guild, exc)
    if changed:
        await chat_review.record_change(bot.db, int(row["id"]), found)
    kind = chat_review.CHANGED_KIND if changed else chat_review.APPROVED_KIND
    await log_action(
        bot,
        guild,
        kind_via(kind, via),
        actor=actor,
        target=int(row["user_id"]),
        details={
            "id": int(row["id"]),
            "kind": taught.kind,
            "intent": taught.intent,
            "phrase": taught.phrase,
            "section": taught.section,
            "reason": row["reason"],
            "via": via,
        },
    )
    return Outcome(True, taught_word(bot, guild, taught), value=int(row["id"]))


async def approve_review(
    bot: Any, guild: Any, actor: Any, item_id: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    row, held = await wanted_review(bot, guild, item_id)
    if held is not None:
        return held
    if row["status"] != chat_review.OPEN:
        return decided_already(bot, guild, row)
    if not teaches(row):
        said = review_words(bot, guild, REVIEW_NOTHING_KEY, id=int(row["id"]))
        return refusal(said, REVIEW_NOTHING_CODE, 409)
    found = chat_review.suggestion_of(row)
    return await settle_review(bot, guild, actor, row, found, chat_review.APPROVED, via)


async def change_review(
    bot: Any, guild: Any, actor: Any, item_id: Any, fields: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    """Staff's own phrase, intent or fact in place of the suggestion, written the same way."""
    row, held = await wanted_review(bot, guild, item_id)
    if held is not None:
        return held
    if row["status"] != chat_review.OPEN:
        return decided_already(bot, guild, row)
    given = dict(fields or {})
    found = chat_review.Suggestion(
        kind=str(given.get("kind") or "").strip().lower(),
        intent=str(given.get("intent") or "").strip() or None,
        phrase=" ".join(str(given.get("phrase") or "").split()) or None,
        line=" ".join(str(given.get("line") or "").split()) or None,
        section=str(given.get("section") or "").strip() or None,
    )
    return await settle_review(bot, guild, actor, row, found, chat_review.CHANGED, via)


async def dismiss_review(
    bot: Any, guild: Any, actor: Any, item_id: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    row, held = await wanted_review(bot, guild, item_id)
    if held is not None:
        return held
    if not await chat_review.decide(
        bot.db, int(row["id"]), chat_review.DISMISSED, actor_id(actor)
    ):
        fresh = await chat_review.get_item(bot.db, int(row["id"]))
        return decided_already(bot, guild, fresh or row)
    await log_action(
        bot,
        guild,
        kind_via(chat_review.DISMISSED_KIND, via),
        actor=actor,
        target=int(row["user_id"]),
        details={"id": int(row["id"]), "reason": row["reason"], "via": via},
    )
    said = review_words(bot, guild, REVIEW_DISMISSED_KEY, id=int(row["id"]))
    return Outcome(True, said, value=int(row["id"]))


async def reopen_review(
    bot: Any, guild: Any, actor: Any, item_id: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    """Staff's way back from a dismissal; an approved item is undone where it was written."""
    row, held = await wanted_review(bot, guild, item_id)
    if held is not None:
        return held
    if not await chat_review.reopen(bot.db, int(row["id"])):
        said = review_words(
            bot, guild, REVIEW_NOT_DISMISSED_KEY, id=int(row["id"]), status=row["status"]
        )
        return refusal(said, REVIEW_NOT_DISMISSED_CODE, 409)
    await log_action(
        bot,
        guild,
        kind_via(chat_review.REOPENED_KIND, via),
        actor=actor,
        target=int(row["user_id"]),
        details={"id": int(row["id"]), "via": via},
    )
    said = review_words(bot, guild, REVIEW_REOPENED_KEY, id=int(row["id"]))
    return Outcome(True, said, value=int(row["id"]))


def review_line(bot: Any, guild: Any, row: Any) -> str:
    return review_words(
        bot,
        guild,
        REVIEW_LINE_KEY,
        id=int(row["id"]),
        reason=chat_review.reason_word(bot.store, guild.id, row["reason"]),
        when=str(row["at"])[:16].replace("T", " "),
        asked=chat_review.clipped(row["asked"], 160),
        suggestion=chat_review.suggestion_word(
            bot.store, guild.id, chat_review.suggestion_of(row)
        ),
    )


def review_item_text(bot: Any, guild: Any, row: Any) -> str:
    found = chat_review.suggestion_of(row)
    return review_words(
        bot,
        guild,
        REVIEW_ITEM_KEY,
        reason=chat_review.reason_word(bot.store, guild.id, row["reason"]),
        when=str(row["at"])[:16].replace("T", " "),
        asked=chat_review.clipped(row["asked"], 700),
        answered=chat_review.clipped(row["answered"], 700),
        suggestion=chat_review.suggestion_word(bot.store, guild.id, found),
        why=f"_{found.why}_" if found is not None and found.why else "",
    )


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
    "approve_review",
    "change_review",
    "dismiss_review",
    "reopen_review",
    "review_buttons",
    "review_item_buttons",
    "review_item_text",
    "review_line",
    "review_pages",
    "wanted_review",
    "channel_note",
    "channel_notes_buttons",
    "clear_channel_note",
    "clear_voice",
    "edit_tone",
    "member_buttons",
    "member_of",
    "page_count",
    "pin_voice",
    "voice_line",
    "voice_roster",
    "voices_buttons",
    "wanted_page",
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
    "save_channel_note",
    "save_settings",
    "set_mode",
    "set_mood",
    "set_voice",
    "settings_buttons",
    "settings_saved",
    "site_page_url",
    "status_lines",
    "text_channel",
    "toggle_move",
    "wanted_note",
    "words",
]
