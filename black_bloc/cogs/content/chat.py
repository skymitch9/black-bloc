from __future__ import annotations

import logging
import time
from datetime import UTC, datetime
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands, tasks

from ... import chat_panel
from ...actionlog import log_action, send_logs, stamp
from ...chat import (
    GREETING,
    INSULT,
    ROUTE,
    answer_for,
    bare_greeting,
    guild_intents,
    invalidate,
    seed_defaults,
)
from ...chat_distil import run as distil_run
from ...chat_llm import (
    LLM_MODE_KEY,
    REPLY_KIND,
    allowance,
    sweep_window,
    tier_errors,
)
from ...command_errors import AnswersErrors
from ...command_visibility import STAFF_ONLY
from ...emoji import tone_for, toned
from ...knowledge import (
    BODY_LIMIT,
    SERVER,
    SERVER_ROW_IS_NOT_YOURS,
    TAG_LIMIT,
    TITLE_LIMIT,
    list_sections,
    replace_server_sections,
    search,
    server_sections,
)
from ...llm import IMPORTANT, SIMPLE
from ...panels import (
    SELECT_OPTION_LIMIT,
    NoteModal,
    Panel,
    answer,
    capped_placeholder,
    clamped,
    db_ready,
    db_up,
    retire,
    still_staff,
)
from ...personas import (
    COOKOUT,
    PERSONALITY_CHOICES,
    PERSONALITY_KEY,
    POOL,
    forget_tropes,
    list_tropes,
    seed_tropes,
)
from ...settings_store import (
    CHAT_COOLDOWN_SECONDS,
    DB_UNAVAILABLE,
    GUILD_ONLY,
    KEY_TYPES,
    display_value,
    require_staff,
)

log = logging.getLogger(__name__)

MESSAGE_TYPES = (discord.MessageType.default, discord.MessageType.reply)
THREAD_TYPES = ("public_thread", "private_thread", "news_thread")
ON = "on"
STAFF_PING_KEY = "chat_staff_can_ping_roles"
LOG_KIND = "chat.insult"
ROUTE_KIND = "chat.route"
WAVE = "\U0001f44b"
WATCHED = (
    "chat_ignore_channels",
    "chat_greeting_reaction",
    "chat_reply_in_threads",
    "chat_route_ping_staff",
)
STAFF_NOTE = "{who} asked for a mod in {where}. {link}"
ADMIN_ONLY_KEY = "chat_status_admin_only"
CHAT_KEYS = tuple(key for key in KEY_TYPES if key.startswith("chat_"))
MEMORY_PREFIX = "chat_memory_"
SETTINGS_FOOTER = (
    "`/settings` ▸ **A setting group…** ▸ chat changes any of these, and the Chat page on "
    "the dashboard edits the words themselves."
)
MEMORY_SETTINGS_HEADER = (
    "\n**What Black Bloc remembers about a person** — `/memory` and the Chat page's Memory "
    "section are their home:"
)

INGEST_HOURS = 24
KNOWLEDGE_INGESTED = "chat.knowledge_ingested"
KNOWLEDGE_LIST_MAX = 15
NO_NOTES = (
    "Nothing has been written down yet. **Write one down…** starts the list, and Black Bloc "
    "fills in the channels, roles and events by itself once a day."
)
NO_NOTES_MATCH = "Nothing written down matches **{query}**."
NOTES_HEADER = (
    "**{count}** note(s){about}. `server` notes are rewritten daily and cannot be edited."
)

TIER_READY = "ready"
TIER_NO_KEY = "no key set, so it does not exist"
TIER_TROUBLE = "last call failed ({why})"
STATUS_NOTES = "The server's own notes: **{count}** written down, last read {when}."
STATUS_NOTES_NEVER = (
    "The server's own notes: **{count}** written down; the daily read has not run yet."
)

VOICE_NOW = "The voice is **{voice}** — {what}"
VOICE_MEANS: dict[str, str] = {
    COOKOUT: "the house voice, warm and easy, with no mood on top of it.",
    POOL: "each conversation picks one of the moods below and drifts a step at a time.",
}
VOICE_IS_A_MOOD = "every conversation sounds like this one mood until the setting changes."
VOICE_OFF = (
    "Nothing is using it yet: `chat_llm_mode` is off, so every answer still comes from Black "
    "Bloc's own written lines."
)
MOODS_HEADER = "\n**The pool** — a mood that is off is never picked:"
MOOD_LINE = "· **{name}** ({label}) — {state}"
NO_MOODS = "\nThe pool has not been written yet; it fills itself in when Black Bloc starts up."

SELECT_CAP = 25
ROOT = "root"
PERSONALITY_VIEW = "personality"
KNOWLEDGE_VIEW = "knowledge"
NOTE_VIEW = "note"
SETTINGS_VIEW = "settings"

STYLES = {
    "primary": discord.ButtonStyle.primary,
    "secondary": discord.ButtonStyle.secondary,
    "success": discord.ButtonStyle.success,
    "danger": discord.ButtonStyle.danger,
}

SITE_BUTTON = "Open on the site"
PERSONALITY_TITLE = "The voice Black Bloc answers in"
KNOWLEDGE_TITLE = "What Black Bloc knows about this server"
NOTE_TITLE = "Note {id}"
SETTINGS_TITLE = "How chat is set up"
CONFIRM_TITLE = "Are you sure?"

VOICE_PLACEHOLDER = "The voice…"
MOOD_OFF_PLACEHOLDER = "Turn a mood off…"
MOOD_ON_PLACEHOLDER = "Turn a mood on…"
NOTE_PLACEHOLDER = "A note…"
NOTE_CAPPED = "{shown} of {total} — the rest are on the Chat page's Knowledge section"

ADD_MODAL_TITLE = "Write something down"
EDIT_MODAL_TITLE = "Edit this note"
LIMITS_MODAL_TITLE = "The numbers chat runs on"
FIND_MODAL_TITLE = "Find a note"
FIND_LABEL = "Words to look for, the way a member would ask"
FIND_LIMIT = 200
TITLE_LABEL = "What the note is about, in a few words"
BODY_LABEL = "The note itself"
TAG_LABEL = "Optional one-word grouping, like events or rules"

COOLDOWN_LABEL = "Seconds between one person's answers"
HOURLY_LABEL = "Answers one person may have in an hour"
DAILY_LABEL = "Answers the whole server may have in a day"
CAP_LABEL = "Dollars the models may spend in a month"
MINUTES_LABEL = "Minutes this panel stays live"

CARD_SOURCE = "written by: {source}"
CARD_TAG = "tag: {tag}"
CARD_NO_TAG = "tag: none"


def mentions_bot(message: Any, me: Any) -> bool:
    """A direct @-mention of Black Bloc; @everyone and role pings are not one."""
    if me is None or getattr(message, "mention_everyone", False):
        return False
    return any(
        getattr(user, "id", None) == getattr(me, "id", None)
        for user in getattr(message, "mentions", ()) or ()
    )


def in_a_thread(channel: Any) -> bool:
    return str(getattr(getattr(channel, "type", None), "name", "")) in THREAD_TYPES


def note_line(row: Any) -> str:
    tag = str(row["tag"] or "")
    return (
        f"`{int(row['id'])}` · **{row['title']}** · {row['source']}"
        f"{f' · {tag}' if tag else ''}\n> {str(row['body'])[:160]}"
    )


def minutes_for(bot: Any, guild_id: int) -> int:
    return chat_panel.panel_minutes(bot.store, guild_id)


def add_site_button(view: Any, bot: Any, row: int) -> None:
    """No origin, no button — a link that goes nowhere is worse than no link at all."""
    url = chat_panel.site_page_url(getattr(getattr(bot, "settings", None), "origin", ""))
    if not url:
        return
    view.add_item(
        discord.ui.Button(style=discord.ButtonStyle.link, label=SITE_BUTTON, url=url, row=row)
    )


def chat_cog(bot: Any) -> Any:
    getter = getattr(bot, "get_cog", None)
    return getter("Chat") if getter is not None else None


def ingest_health(bot: Any) -> tuple[str | None, str | None]:
    cog = chat_cog(bot)
    if cog is None:
        return (None, None)
    return (cog.last_ingest_at, cog.last_ingest_error)


def tier_words(bot: Any, tier: str) -> str:
    """A tier that is down says so, the way a degraded poll does."""
    settings = bot.settings
    keyed = (
        settings.important_tier_configured
        if tier == IMPORTANT
        else settings.simple_tier_configured
    )
    if not keyed:
        return TIER_NO_KEY
    trouble = tier_errors(bot).get(tier)
    return TIER_TROUBLE.format(why=trouble) if trouble else TIER_READY


def spend_readable(bot: Any, guild: Any, actor: Any) -> bool:
    if not bot.store.get(guild.id, ADMIN_ONLY_KEY):
        return True
    return bool(getattr(getattr(actor, "guild_permissions", None), "administrator", False))


def notes_words(rows: Any, when: Any) -> str:
    if when:
        return STATUS_NOTES.format(count=len(rows), when=stamp(when))
    return STATUS_NOTES_NEVER.format(count=len(rows))


# --- what renders ------------------------------------------------------------------------------


class ChatPanel(Panel):
    def __init__(self, minutes: int) -> None:
        super().__init__(minutes, footer=chat_panel.PANEL_TIMEOUT_FOOTER)
        self.where = ROOT
        self.note_id: int | None = None
        self.query = ""


async def panel_lines(bot: Any, guild: Any, actor: Any) -> list[str]:
    """The whole status block, written out always — a warning behind a button is a lost one."""
    readable = spend_readable(bot, guild, actor)
    spend = None
    notes = ""
    if bot.db.is_connected:
        rows = await list_sections(bot.db, guild.id)
        notes = notes_words(rows, ingest_health(bot)[0])
        if readable:
            spend = await allowance(bot.db, bot.store, guild.id, actor.id)
    lines = chat_panel.status_lines(
        bot.store,
        guild.id,
        tiers=(tier_words(bot, SIMPLE), tier_words(bot, IMPORTANT)),
        spend=spend,
        hidden=not readable,
        notes=notes,
        trouble=ingest_health(bot)[1] or "",
    )
    lines.append(chat_panel.MEMORY_LINE)
    return lines


async def build_panel(bot: Any, guild: Any, actor: Any) -> tuple[discord.Embed, ChatPanel]:
    """One command, one staff panel — chat has no member half to reveal."""
    embed = discord.Embed(
        title=chat_panel.PANEL_TITLE, description=clamped(await panel_lines(bot, guild, actor))
    )
    view = ChatPanel(minutes_for(bot, guild.id))
    state = chat_panel.panel_state(bot.store, guild.id)
    for move in chat_panel.panel_buttons(state):
        view.add_item(MoveButton(move))
    add_site_button(view, bot, row=2)
    return (embed, view)


def personality_lines(bot: Any, guild: Any, rows: Any) -> list[str]:
    voice = str(bot.store.get(guild.id, PERSONALITY_KEY))
    lines = [VOICE_NOW.format(voice=voice, what=VOICE_MEANS.get(voice, VOICE_IS_A_MOOD))]
    if str(bot.store.get(guild.id, LLM_MODE_KEY)) != ON:
        lines.append(VOICE_OFF)
    if not rows:
        lines.append(NO_MOODS)
        return lines
    lines.append(MOODS_HEADER)
    lines += [
        MOOD_LINE.format(
            name=row["name"], label=row["label"], state=ON if row["enabled"] else "off"
        )
        for row in rows
    ]
    if chat_panel.guarded_moods(rows, voice):
        lines.append(chat_panel.POOL_GUARDS)
    return lines


async def build_personality(bot: Any, guild: Any) -> tuple[discord.Embed, ChatPanel]:
    rows = await list_tropes(bot.db)
    voice = str(bot.store.get(guild.id, PERSONALITY_KEY))
    embed = discord.Embed(
        title=PERSONALITY_TITLE, description=clamped(personality_lines(bot, guild, rows))
    )
    view = ChatPanel(minutes_for(bot, guild.id))
    view.where = PERSONALITY_VIEW
    view.add_item(VoicePick(voice, row=0))
    may_go_off, may_come_on = chat_panel.mood_options(rows, voice)
    if may_go_off:
        view.add_item(MoodPick(may_go_off, enabling=False, row=1))
    if may_come_on:
        view.add_item(MoodPick(may_come_on, enabling=True, row=2))
    for move in chat_panel.personality_buttons():
        view.add_item(MoveButton(move._replace(row=3)))
    return (embed, view)


def knowledge_lines(rows: Any, shown: Any, query: str) -> list[str]:
    about = f" matching **{query[:40]}**" if query.strip() else ""
    return [
        NOTES_HEADER.format(count=len(rows), about=about),
        *(note_line(row) for row in shown),
    ]


async def build_knowledge(
    bot: Any, guild: Any, query: str = ""
) -> tuple[discord.Embed, ChatPanel]:
    rows = await list_sections(bot.db, guild.id)
    found = rows
    if query.strip():
        wanted = {hit.id for hit in search(rows, query, limit=KNOWLEDGE_LIST_MAX)}
        found = [row for row in rows if int(row["id"]) in wanted]
    if not rows:
        body = NO_NOTES
    elif not found:
        body = NO_NOTES_MATCH.format(query=query[:60])
    else:
        body = clamped(knowledge_lines(found, found[:KNOWLEDGE_LIST_MAX], query))
    embed = discord.Embed(title=KNOWLEDGE_TITLE, description=body)
    view = ChatPanel(minutes_for(bot, guild.id))
    view.where = KNOWLEDGE_VIEW
    view.query = query
    if found:
        view.add_item(NotePick(found, row=0))
    for move in chat_panel.knowledge_buttons(notes=len(rows)):
        view.add_item(MoveButton(move))
    return (embed, view)


def note_lines(row: Any) -> list[str]:
    tag = str(row["tag"] or "")
    lines = [
        f"**{row['title']}**",
        CARD_SOURCE.format(source=row["source"]),
        CARD_TAG.format(tag=tag) if tag else CARD_NO_TAG,
        "",
        str(row["body"]),
    ]
    if str(row["source"]) == SERVER:
        lines.append("")
        lines.append(SERVER_ROW_IS_NOT_YOURS)
    return lines


async def build_note(
    bot: Any, guild: Any, note_id: Any
) -> tuple[discord.Embed | None, ChatPanel | None]:
    row, held = await chat_panel.wanted_note(bot, guild, note_id)
    if row is None:
        return (None, None)
    embed = discord.Embed(
        title=NOTE_TITLE.format(id=int(row["id"])), description=clamped(note_lines(row))
    )
    view = ChatPanel(minutes_for(bot, guild.id))
    view.where = NOTE_VIEW
    view.note_id = int(row["id"])
    for move in chat_panel.note_buttons(row["source"]):
        view.add_item(MoveButton(move))
    return (embed, view)


def settings_lines(bot: Any, guild: Any) -> list[str]:
    store = bot.store
    mine = [key for key in CHAT_KEYS if not key.startswith(MEMORY_PREFIX)]
    theirs = [key for key in CHAT_KEYS if key.startswith(MEMORY_PREFIX)]
    said = [f"`{key}` — **{display_value(key, store.get(guild.id, key))}**" for key in mine]
    said.append(MEMORY_SETTINGS_HEADER)
    said += [f"`{key}` — **{display_value(key, store.get(guild.id, key))}**" for key in theirs]
    said.append("")
    said.append(SETTINGS_FOOTER)
    return said


def build_settings(bot: Any, guild: Any) -> tuple[discord.Embed, ChatPanel]:
    embed = discord.Embed(
        title=SETTINGS_TITLE, description=clamped(settings_lines(bot, guild))
    )
    view = ChatPanel(minutes_for(bot, guild.id))
    view.where = SETTINGS_VIEW
    for move in chat_panel.settings_buttons():
        view.add_item(MoveButton(move))
    add_site_button(view, bot, row=2)
    return (embed, view)


# --- rendering ---------------------------------------------------------------------------------


async def render(interaction: discord.Interaction, embed: Any, view: Any, previous: Any) -> None:
    retire(previous)
    view.message = await interaction.edit_original_response(
        embed=embed, view=view, allowed_mentions=discord.AllowedMentions.none()
    )


async def render_panel(interaction: discord.Interaction, previous: Any = None) -> None:
    embed, view = await build_panel(interaction.client, interaction.guild, interaction.user)
    await render(interaction, embed, view, previous)


async def render_personality(interaction: discord.Interaction, previous: Any = None) -> None:
    embed, view = await build_personality(interaction.client, interaction.guild)
    await render(interaction, embed, view, previous)


async def render_knowledge(
    interaction: discord.Interaction, query: str = "", previous: Any = None
) -> None:
    embed, view = await build_knowledge(interaction.client, interaction.guild, query)
    await render(interaction, embed, view, previous)


async def render_note(
    interaction: discord.Interaction, note_id: Any, previous: Any = None
) -> None:
    """The card carries the list's `Find…` words, so Back returns to the list you were in."""
    query = str(getattr(previous, "query", "") or "")
    embed, view = await build_note(interaction.client, interaction.guild, note_id)
    if view is None:
        await render_knowledge(interaction, query, previous)
        await answer(interaction, chat_panel.NO_SUCH_NOTE.format(id=note_id))
        return
    view.query = query
    await render(interaction, embed, view, previous)


async def render_settings(interaction: discord.Interaction, previous: Any = None) -> None:
    embed, view = build_settings(interaction.client, interaction.guild)
    await render(interaction, embed, view, previous)


async def open_root(interaction: discord.Interaction, previous: Any = None) -> None:
    if not await still_staff(interaction):
        return
    await interaction.response.defer()
    if not await db_ready(interaction):
        return
    await render_panel(interaction, previous)


async def open_personality(interaction: discord.Interaction, previous: Any = None) -> None:
    if not await still_staff(interaction):
        return
    await interaction.response.defer()
    if not await db_ready(interaction):
        return
    await render_personality(interaction, previous)


async def open_knowledge(
    interaction: discord.Interaction, query: str = "", previous: Any = None
) -> None:
    if not await still_staff(interaction):
        return
    await interaction.response.defer()
    if not await db_ready(interaction):
        return
    await render_knowledge(interaction, query, previous)


async def open_note(
    interaction: discord.Interaction, note_id: Any, previous: Any = None
) -> None:
    if not await still_staff(interaction):
        return
    await interaction.response.defer()
    if not await db_ready(interaction):
        return
    await render_note(interaction, note_id, previous)


async def open_settings(interaction: discord.Interaction, previous: Any = None) -> None:
    if not await still_staff(interaction):
        return
    await interaction.response.defer()
    if not await db_ready(interaction):
        return
    await render_settings(interaction, previous)


async def open_remove_confirm(interaction: discord.Interaction, view: Any) -> None:
    if not await still_staff(interaction):
        return
    await interaction.response.defer()
    if not await db_ready(interaction):
        return
    bot = interaction.client
    guild = interaction.guild
    row, _held = await chat_panel.wanted_note(bot, guild, view.note_id)
    if row is None:
        await render_knowledge(interaction, view.query, view)
        await answer(interaction, chat_panel.NO_SUCH_NOTE.format(id=view.note_id))
        return
    embed = discord.Embed(
        title=NOTE_TITLE.format(id=int(row["id"])), description=clamped(note_lines(row))
    )
    embed.add_field(
        name=CONFIRM_TITLE,
        value=chat_panel.REMOVE_QUESTION.format(id=int(row["id"]), title=str(row["title"])),
        inline=False,
    )
    fresh = ChatPanel(minutes_for(bot, guild.id))
    fresh.where = NOTE_VIEW
    fresh.note_id = int(row["id"])
    fresh.query = view.query
    fresh.add_item(RemoveYesButton())
    fresh.add_item(KeepItButton())
    await render(interaction, embed, fresh, view)


async def refresh_where(interaction: discord.Interaction, view: Any) -> None:
    if view.where == PERSONALITY_VIEW:
        await open_personality(interaction, view)
        return
    if view.where == KNOWLEDGE_VIEW:
        await open_knowledge(interaction, view.query, view)
        return
    if view.where == NOTE_VIEW:
        await open_note(interaction, view.note_id, view)
        return
    if view.where == SETTINGS_VIEW:
        await open_settings(interaction, view)
        return
    await open_root(interaction, view)


async def back_from(interaction: discord.Interaction, view: Any) -> None:
    if view.where == NOTE_VIEW:
        await open_knowledge(interaction, view.query, view)
        return
    await open_root(interaction, view)


# --- the moves, one function each ---------------------------------------------------------------


async def run_voice(interaction: discord.Interaction, wanted: str, previous: Any) -> None:
    if not await still_staff(interaction):
        return
    await interaction.response.defer()
    if not await db_ready(interaction):
        return
    outcome = await chat_panel.set_voice(
        interaction.client, interaction.guild, interaction.user, wanted
    )
    await render_personality(interaction, previous)
    await answer(interaction, outcome.message)


async def run_mood(
    interaction: discord.Interaction, name: str, enabled: bool, previous: Any
) -> None:
    if not await still_staff(interaction):
        return
    await interaction.response.defer()
    if not await db_ready(interaction):
        return
    outcome = await chat_panel.set_mood(
        interaction.client, interaction.guild, interaction.user, name, enabled
    )
    await render_personality(interaction, previous)
    await answer(interaction, outcome.message)


async def run_add_note(
    interaction: discord.Interaction, fields: dict[str, Any], previous: Any
) -> None:
    if not await still_staff(interaction):
        return
    await interaction.response.defer()
    if not await db_ready(interaction):
        return
    outcome = await chat_panel.add_note(
        interaction.client,
        interaction.guild,
        interaction.user,
        fields["title"],
        fields["body"],
        fields["tag"],
    )
    await render_knowledge(interaction, "", previous)
    await answer(interaction, outcome.message)


async def run_edit_note(
    interaction: discord.Interaction, note_id: Any, fields: dict[str, Any], previous: Any
) -> None:
    if not await still_staff(interaction):
        return
    await interaction.response.defer()
    if not await db_ready(interaction):
        return
    outcome = await chat_panel.edit_note(
        interaction.client, interaction.guild, interaction.user, note_id, fields
    )
    await render_note(interaction, note_id, previous)
    await answer(interaction, outcome.message)


async def run_remove_note(interaction: discord.Interaction, note_id: Any, previous: Any) -> None:
    if not await still_staff(interaction):
        return
    await interaction.response.defer()
    if not await db_ready(interaction):
        return
    outcome = await chat_panel.remove_note(
        interaction.client, interaction.guild, interaction.user, note_id
    )
    await render_knowledge(interaction, "", previous)
    await answer(interaction, outcome.message)


async def run_mode(interaction: discord.Interaction, key: str, previous: Any) -> None:
    """One click, both ways — the monthly cap is the brake, not a confirm (fork F-C3)."""
    if not await still_staff(interaction):
        return
    await interaction.response.defer()
    if not await db_ready(interaction):
        return
    bot = interaction.client
    wanted = "off" if str(bot.store.get(interaction.guild.id, key)) == ON else ON
    outcome = await chat_panel.set_mode(
        bot, interaction.guild, interaction.user, key, wanted
    )
    await render_panel(interaction, previous)
    await answer(interaction, outcome.message)


async def run_limits(
    interaction: discord.Interaction, given: dict[str, Any], previous: Any
) -> None:
    if not await still_staff(interaction):
        return
    await interaction.response.defer()
    if not await db_ready(interaction):
        return
    read = chat_panel.read_limits(given)
    if not read.ok:
        await render_settings(interaction, previous)
        await answer(interaction, read.message)
        return
    outcome = await chat_panel.save_settings(
        interaction.client, interaction.guild, interaction.user, read.value
    )
    await render_settings(interaction, previous)
    await answer(interaction, outcome.message)


async def run_find(interaction: discord.Interaction, query: str, previous: Any) -> None:
    """A pure read: it filters the list and leaves no row behind it."""
    if not await still_staff(interaction):
        return
    await interaction.response.defer()
    if not await db_ready(interaction):
        return
    await render_knowledge(interaction, query, previous)


# --- the controls ------------------------------------------------------------------------------


class MoveButton(discord.ui.Button):
    def __init__(self, move: Any) -> None:
        super().__init__(label=move.label, style=STYLES[move.style], row=move.row)
        self.move = move

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        action = self.move.action
        if action == chat_panel.REFRESH:
            await refresh_where(interaction, view)
            return
        if action == chat_panel.BACK:
            await back_from(interaction, view)
            return
        if action == chat_panel.LOGS:
            await send_logs(interaction, "chat")
            return
        if action == chat_panel.PERSONALITY:
            await open_personality(interaction, view)
            return
        if action == chat_panel.KNOWLEDGE:
            await open_knowledge(interaction, "", view)
            return
        if action == chat_panel.SETTINGS:
            await open_settings(interaction, view)
            return
        if action == chat_panel.CHAT_TOGGLE:
            await run_mode(interaction, chat_panel.MODE_KEY, view)
            return
        if action == chat_panel.LLM_TOGGLE:
            await run_mode(interaction, LLM_MODE_KEY, view)
            return
        if action == chat_panel.REMOVE:
            await open_remove_confirm(interaction, view)
            return
        await self.open_modal(interaction, view, action)

    async def open_modal(self, interaction: discord.Interaction, view: Any, action: str) -> None:
        if not await still_staff(interaction):
            return
        if not await db_up(interaction):
            return
        if action == chat_panel.WRITE:
            await interaction.response.send_modal(NoteFieldsModal(view))
            return
        if action == chat_panel.EDIT:
            row, _held = await chat_panel.wanted_note(
                interaction.client, interaction.guild, view.note_id
            )
            if row is None:
                await answer(interaction, chat_panel.NO_SUCH_NOTE.format(id=view.note_id))
                return
            await interaction.response.send_modal(NoteFieldsModal(view, row=row))
            return
        if action == chat_panel.LIMITS:
            await interaction.response.send_modal(
                LimitsModal(interaction.client, interaction.guild.id, view)
            )
            return
        await interaction.response.send_modal(
            NoteModal(
                title=FIND_MODAL_TITLE,
                label=FIND_LABEL,
                max_length=FIND_LIMIT,
                on_submit=lambda one, text: run_find(one, text, view),
            )
        )


class RemoveYesButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label=chat_panel.REMOVE_YES, style=discord.ButtonStyle.danger, row=0)

    async def callback(self, interaction: discord.Interaction) -> None:
        await run_remove_note(interaction, self.view.note_id, self.view)


class KeepItButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label=chat_panel.KEEP_IT, style=discord.ButtonStyle.secondary, row=0)

    async def callback(self, interaction: discord.Interaction) -> None:
        await open_note(interaction, self.view.note_id, self.view)


class VoicePick(discord.ui.Select):
    def __init__(self, current: str, row: int) -> None:
        super().__init__(
            placeholder=VOICE_PLACEHOLDER,
            options=[
                discord.SelectOption(label=one, value=one, default=(one == current))
                for one in PERSONALITY_CHOICES
            ],
            min_values=1,
            max_values=1,
            row=row,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await run_voice(interaction, self.values[0], self.view)


class MoodPick(discord.ui.Select):
    """Two selects, never one toggle: each option offers exactly one unambiguous move."""

    def __init__(self, rows: Any, *, enabling: bool, row: int) -> None:
        self.enabling = enabling
        found = list(rows)
        super().__init__(
            placeholder=MOOD_ON_PLACEHOLDER if enabling else MOOD_OFF_PLACEHOLDER,
            options=[
                discord.SelectOption(
                    label=str(one["label"])[:SELECT_OPTION_LIMIT], value=str(one["name"])
                )
                for one in found
            ],
            min_values=1,
            max_values=1,
            row=row,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await run_mood(interaction, self.values[0], self.enabling, self.view)


class NotePick(discord.ui.Select):
    def __init__(self, rows: Any, row: int) -> None:
        found = list(rows)
        shown = found[:SELECT_CAP]
        super().__init__(
            placeholder=capped_placeholder(
                len(shown), len(found), pick=NOTE_PLACEHOLDER, capped=NOTE_CAPPED
            ),
            options=[
                discord.SelectOption(
                    label=f"{one['id']} · {one['title']}"[:SELECT_OPTION_LIMIT],
                    value=str(one["id"]),
                )
                for one in shown
            ],
            min_values=1,
            max_values=1,
            row=row,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await open_note(interaction, int(self.values[0]), self.view)


class NoteFieldsModal(AnswersErrors, discord.ui.Modal):
    """One shape for both doors onto a note — the limits come from `knowledge.py`, never retyped."""

    note_title = discord.ui.TextInput(label=TITLE_LABEL, max_length=TITLE_LIMIT)
    body = discord.ui.TextInput(
        label=BODY_LABEL, style=discord.TextStyle.paragraph, max_length=BODY_LIMIT
    )
    tag = discord.ui.TextInput(label=TAG_LABEL, max_length=TAG_LIMIT, required=False)

    def __init__(self, previous: Any = None, *, row: Any = None) -> None:
        super().__init__(title=EDIT_MODAL_TITLE if row is not None else ADD_MODAL_TITLE)
        self.previous = previous
        self.note_id = int(row["id"]) if row is not None else None
        if row is not None:
            self.note_title.default = str(row["title"])
            self.body.default = str(row["body"])
            self.tag.default = str(row["tag"] or "")

    async def on_submit(self, interaction: discord.Interaction) -> None:
        fields = {
            "title": str(self.note_title),
            "body": str(self.body),
            "tag": str(self.tag),
        }
        if self.note_id is None:
            await run_add_note(interaction, fields, self.previous)
            return
        await run_edit_note(interaction, self.note_id, fields, self.previous)


class LimitsModal(AnswersErrors, discord.ui.Modal):
    """Five fields is Discord's maximum, so nothing else can join them."""

    cooldown = discord.ui.TextInput(label=COOLDOWN_LABEL, max_length=6)
    hourly = discord.ui.TextInput(label=HOURLY_LABEL, max_length=6)
    daily = discord.ui.TextInput(label=DAILY_LABEL, max_length=6)
    cap = discord.ui.TextInput(label=CAP_LABEL, max_length=6)
    stays = discord.ui.TextInput(label=MINUTES_LABEL, max_length=6)

    def __init__(self, bot: Any, guild_id: int, previous: Any = None) -> None:
        super().__init__(title=LIMITS_MODAL_TITLE)
        self.previous = previous
        store = bot.store
        self.cooldown.default = str(store.get(guild_id, chat_panel.COOLDOWN_KEY))
        self.hourly.default = str(store.get(guild_id, chat_panel.HOURLY_KEY))
        self.daily.default = str(store.get(guild_id, chat_panel.DAILY_KEY))
        self.cap.default = str(store.get(guild_id, chat_panel.CAP_KEY))
        self.stays.default = str(minutes_for(bot, guild_id))

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await run_limits(
            interaction,
            {
                chat_panel.COOLDOWN_KEY: str(self.cooldown),
                chat_panel.HOURLY_KEY: str(self.hourly),
                chat_panel.DAILY_KEY: str(self.daily),
                chat_panel.CAP_KEY: str(self.cap),
                chat_panel.PANEL_MINUTES_KEY: str(self.stays),
            },
            self.previous,
        )


class Chat(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._answered: dict[int, float] = {}
        self._seeded: set[int] = set()
        self.last_ingest_at: str | None = None
        self.last_ingest_error: str | None = None
        self.last_distil: dict[str, int] | None = None

    def loop_health(self, name: str) -> tuple[str | None, str | None]:
        if name == "_ingest":
            return (self.last_ingest_at, self.last_ingest_error)
        return (None, None)

    def usable_db(self) -> Any:
        db = getattr(self.bot, "db", None)
        return db if db is not None and getattr(db, "is_connected", False) else None

    @app_commands.command(name="chat", description="How Black Bloc answers @-mentions")
    @app_commands.default_permissions(STAFF_ONLY)
    async def chat_panel_command(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await answer(interaction, GUILD_ONLY)
            return
        if not await require_staff(interaction):
            return
        if not self.bot.db.is_connected:
            log.warning("chat: refused the panel — the database is not connected")
            await answer(interaction, DB_UNAVAILABLE)
            return
        embed, view = await build_panel(self.bot, interaction.guild, interaction.user)
        await interaction.response.send_message(
            embed=embed,
            view=view,
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        view.message = await interaction.original_response()

    async def cog_load(self) -> None:
        for key in WATCHED:
            self.bot.store.on_change(key, self._settings_changed)
        await self.seed_guilds()
        if self.usable_db() is not None:
            self._ingest.start()

    async def cog_unload(self) -> None:
        self._ingest.cancel()

    @tasks.loop(hours=INGEST_HOURS)
    async def _ingest(self) -> None:
        if self.usable_db() is None:
            return
        try:
            await self.ingest_once()
        except Exception as exc:
            self.last_ingest_error = f"{type(exc).__name__}: {exc}"
            log.exception("chat: the daily knowledge ingest failed")
            return
        self.last_ingest_error = None
        self.last_ingest_at = datetime.now(UTC).isoformat()

    @_ingest.before_loop
    async def _before_ingest(self) -> None:
        await self.bot.wait_until_ready()

    @_ingest.error
    async def _ingest_stopped(self, exc: BaseException) -> None:
        """The loop stops for the life of the process unless it is started again."""
        self.last_ingest_error = f"{type(exc).__name__}: {exc}"
        log.error("chat: the knowledge ingest stopped; restarting it", exc_info=exc)
        self._ingest.restart()

    async def ingest_once(self) -> int:
        """One pass: what the server says about itself becomes the `server` notes, whole."""
        db = self.usable_db()
        if db is None:
            return 0
        try:
            self.last_distil = await distil_run(self.bot)
        except Exception as exc:
            log.warning("chat: nothing was remembered — %s: %s", type(exc).__name__, exc)
        try:
            await sweep_window(db)
        except Exception as exc:
            log.warning("chat: the window was not swept — %s: %s", type(exc).__name__, exc)
        written = 0
        for guild in list(getattr(self.bot, "guilds", ()) or ()):
            if getattr(guild, "unavailable", False):
                log.info("chat: knowledge skipped %s — the server is unavailable", guild.id)
                continue
            try:
                sections = await server_sections(self.bot, guild, db)
                count = await replace_server_sections(db, guild.id, sections)
            except Exception as exc:
                log.warning(
                    "chat: %s was not ingested — %s: %s", guild.id, type(exc).__name__, exc
                )
                continue
            written += count
            await log_action(
                self.bot, guild, KNOWLEDGE_INGESTED, details={"sections": count}
            )
        return written

    def _settings_changed(self, guild_id: int, key: str, value: Any, by: Any) -> None:
        invalidate(self.bot, guild_id)

    async def seed_guilds(self) -> None:
        """The code tables become editable rows the first time Black Bloc sees a server."""
        db = getattr(self.bot, "db", None)
        if db is None or not getattr(db, "is_connected", False):
            return
        try:
            if await seed_tropes(db):
                forget_tropes(self.bot)
        except Exception as exc:
            log.warning("chat: the mood pool was not seeded — %s: %s", type(exc).__name__, exc)
        for guild in getattr(self.bot, "guilds", ()) or ():
            if guild.id in self._seeded:
                continue
            try:
                made = await seed_defaults(db, guild.id)
            except Exception as exc:
                log.warning(
                    "chat: %s was not seeded — %s: %s", guild.id, type(exc).__name__, exc
                )
                continue
            self._seeded.add(guild.id)
            if made:
                invalidate(self.bot, guild.id)

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        await self.seed_guilds()

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild) -> None:
        await self.seed_guilds()

    def cooldown_seconds(self, guild_id: int | None) -> int:
        """A DM has no guild to read the setting from, so it gets the registry's default."""
        if guild_id is None:
            return CHAT_COOLDOWN_SECONDS
        return int(self.bot.store.get(guild_id, "chat_cooldown_seconds") or 0)

    def cooling(self, user_id: int, seconds: int, now: float) -> bool:
        last = self._answered.get(user_id)
        return last is not None and now - last < seconds

    def welcome_here(self, guild_id: int | None, channel: Any) -> bool:
        if guild_id is None:
            return True
        ignored = self.bot.store.get(guild_id, "chat_ignore_channels") or []
        if getattr(channel, "id", None) in ignored:
            return False
        if in_a_thread(channel) and not self.bot.store.get(guild_id, "chat_reply_in_threads"):
            return False
        return True

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        me = getattr(self.bot, "user", None)
        author = getattr(message, "author", None)
        if author is None or getattr(author, "bot", False):
            return
        if getattr(message, "webhook_id", None) is not None:
            return
        if getattr(message, "type", None) not in MESSAGE_TYPES:
            return
        if not mentions_bot(message, me):
            return
        guild = getattr(message, "guild", None)
        guild_id = getattr(guild, "id", None)
        if guild_id is not None and self.bot.store.get(guild_id, "chat_mode") != ON:
            return
        channel = getattr(message, "channel", None)
        if not self.welcome_here(guild_id, channel):
            log.debug("chat: %s is a channel Black Bloc keeps out of", getattr(channel, "id", "?"))
            return
        guard = getattr(self.bot, "guard", None)
        if guard is not None and not guard.allows_channel(channel):
            log.debug(
                "chat: test mode, so %s was not answered in channel %s",
                getattr(author, "id", "?"),
                getattr(channel, "id", "?"),
            )
            return
        now = time.monotonic()
        user_id = getattr(author, "id", 0)
        if self.cooling(user_id, self.cooldown_seconds(guild_id), now):
            return
        text = str(getattr(message, "content", "") or "")
        said = await answer_for(text, author, self.bot, channel=channel, llm=True)
        if not said.text:
            return
        if await self.waved_instead(message, text, guild_id, said.intent):
            self._answered[user_id] = now
            return
        try:
            await message.reply(
                said.text,
                mention_author=False,
                allowed_mentions=self.mentions_for(guild, author),
            )
        except Exception as exc:
            log.warning(
                "chat: %s could not be answered — %s: %s", user_id, type(exc).__name__, exc
            )
            return
        self._answered[user_id] = now
        log.info("chat: answered %s (%s)", user_id, said.intent)
        if guild is None:
            return
        if said.tier:
            await log_action(
                self.bot, guild, REPLY_KIND, actor=author, details={"tier": said.tier}
            )
        if said.intent == INSULT:
            await log_action(
                self.bot, guild, LOG_KIND, actor=author, details={"intent": said.intent}
            )
        if said.kind == ROUTE:
            await self.tell_staff(guild, message, author)
            await log_action(
                self.bot, guild, ROUTE_KIND, actor=author, details={"intent": said.intent}
            )

    def mentions_for(self, guild: Any, author: Any) -> discord.AllowedMentions:
        """Nobody, ever — unless staff started it and the server left the exception on."""
        quiet = discord.AllowedMentions.none()
        if guild is None:
            return quiet
        try:
            if not self.bot.store.get(guild.id, STAFF_PING_KEY):
                return quiet
            if not self.bot.store.is_staff(author):
                return quiet
        except Exception as exc:
            log.warning("chat: who may ping was unreadable — %s: %s", type(exc).__name__, exc)
            return quiet
        return discord.AllowedMentions(
            everyone=False, users=False, roles=True, replied_user=False
        )

    async def waved_instead(
        self, message: Any, text: str, guild_id: int | None, intent: str
    ) -> bool:
        """A bare hello gets a wave rather than a sentence, when a server asks for that."""
        if intent != GREETING or guild_id is None:
            return False
        if not self.bot.store.get(guild_id, "chat_greeting_reaction"):
            return False
        if not bare_greeting(text, await guild_intents(self.bot, guild_id)):
            return False
        try:
            await message.add_reaction(toned(WAVE, tone_for(self.bot, guild_id)))
        except Exception as exc:
            log.warning("chat: the wave did not land — %s: %s", type(exc).__name__, exc)
            return False
        return True

    async def tell_staff(self, guild: Any, message: Any, author: Any) -> None:
        """One line in the staff channel, only when modmail is the way in and staff asked for it."""
        if not self.bot.store.get(guild.id, "chat_route_ping_staff"):
            return
        if not self.bot.store.get(guild.id, "modmail_enabled"):
            return
        channel_id = self.bot.store.get(guild.id, "staff_channel_id")
        channel = guild.get_channel(channel_id) if channel_id else None
        if channel is None:
            log.warning("chat: no staff channel is set, so the route note was not posted")
            return
        guard = getattr(self.bot, "guard", None)
        if guard is not None and not guard.allows_channel(channel):
            log.debug("chat: test mode, so the route note was not posted in %s", channel_id)
            return
        try:
            await channel.send(
                STAFF_NOTE.format(
                    who=getattr(author, "mention", getattr(author, "id", "somebody")),
                    where=getattr(message.channel, "mention", "a channel"),
                    link=getattr(message, "jump_url", ""),
                ),
                allowed_mentions=discord.AllowedMentions.none(),
            )
        except Exception as exc:
            log.warning(
                "chat: the staff note was not posted — %s: %s", type(exc).__name__, exc
            )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Chat(bot))
