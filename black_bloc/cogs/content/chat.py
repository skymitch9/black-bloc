from __future__ import annotations

import logging
import time
from datetime import UTC, datetime
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands, tasks

from ...actionlog import (
    LOGS_DEFAULT,
    LOGS_MAX,
    LOGS_MIN,
    log_action,
    send_logs,
    stamp,
)
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
from ...chat_llm import (
    LLM_MODE_KEY,
    REPLY_KIND,
    allowance,
    money,
    sweep_window,
    tier_errors,
)
from ...command_visibility import STAFF_ONLY
from ...emoji import tone_for, toned
from ...knowledge import (
    SERVER,
    SERVER_ROW_IS_NOT_YOURS,
    KnowledgeError,
    add_section,
    clean_body,
    clean_tag,
    clean_title,
    get_section,
    list_sections,
    remove_section,
    replace_server_sections,
    search,
    server_sections,
)
from ...llm import IMPORTANT, SIMPLE
from ...personas import (
    COOKOUT,
    PERSONALITY_CHOICES,
    PERSONALITY_KEY,
    POOL,
    forget_tropes,
    get_trope,
    list_tropes,
    seed_tropes,
    set_enabled,
)
from ...settings_store import (
    CHAT_COOLDOWN_SECONDS,
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
STATUS_ADMIN_ONLY = (
    "`/chat status` shows what the conversation models are spending, and this server keeps "
    "that to administrators — nothing was shown. Ask an Admin to read it out, or an Admin can "
    "switch `chat_status_admin_only` off if staff should see it too."
)
CHAT_KEYS = tuple(key for key in KEY_TYPES if key.startswith("chat_"))
SETTINGS_FOOTER = (
    "`/settings set` changes any of these, and the Chat page on the dashboard edits the words "
    "themselves."
)

INGEST_HOURS = 24
KNOWLEDGE_ADDED = "chat.knowledge_added"
KNOWLEDGE_REMOVED = "chat.knowledge_removed"
KNOWLEDGE_INGESTED = "chat.knowledge_ingested"
KNOWLEDGE_LIST_MAX = 15
NOTE_SAVED = "Saved as note **{id}** — **{title}**. Black Bloc will quote it when it fits."
NOTE_REMOVED = "Note **{id}** — **{title}** — is gone."
NO_SUCH_NOTE = (
    "There is no note **{id}** in this server, so nothing was removed. `/chat knowledge list` "
    "shows the ones there are."
)
NO_NOTES = (
    "Nothing has been written down yet. `/chat knowledge add` starts the list, and Black Bloc "
    "fills in the channels, roles and events by itself once a day."
)
NO_NOTES_MATCH = "Nothing written down matches **{query}**."
NOTES_HEADER = (
    "**{count}** note(s){about}. `server` notes are rewritten daily and cannot be edited."
)
DB_DOWN = (
    "Black Bloc cannot reach its own database right now, so nothing was changed. Wait a moment "
    "and run the command again, and tell a Lead if it keeps happening."
)

STATUS_MODE = "Answering @-mentions: **{mode}**. Conversation model: **{llm}**."
STATUS_OFF_TAIL = " Every answer comes from Black Bloc's own written lines."
STATUS_TIERS = "Tiers — the quick one: {simple}. The careful one: {important}."
TIER_READY = "ready"
TIER_NO_KEY = "no key set, so it does not exist"
TIER_TROUBLE = "last call failed ({why})"
STATUS_TURNS = (
    "Answers today: **{today}** of {today_of}. Yours in the last hour: **{mine}** of {of}."
)
STATUS_MONEY = "This month so far: **{spent}** of {cap}."
STATUS_CLOSED = (
    "The models are resting until the 1st, so every answer comes from the written lines. Nothing "
    "is broken."
)
STATUS_NOTES = "The server's own notes: **{count}** written down, last read {when}."
STATUS_NOTES_NEVER = (
    "The server's own notes: **{count}** written down; the daily read has not run yet."
)
STATUS_INGEST_TROUBLE = "The last daily read did not finish: {why}."
NO_CEILING = "no ceiling"

PERSONALITY_SET = "chat.personality_mode"
TROPE_ENABLED = "chat.trope_enabled"
TROPE_DISABLED = "chat.trope_disabled"
VOICE_NOW = "The voice is **{voice}** — {what}"
VOICE_MEANS: dict[str, str] = {
    COOKOUT: "the house voice, warm and easy, with no mood on top of it.",
    POOL: "each conversation picks one of the moods below and drifts a step at a time.",
}
VOICE_IS_A_MOOD = "every conversation sounds like this one mood until the setting changes."
VOICE_CHANGED = "The voice is **{voice}** from the next answer on."
VOICE_OFF = (
    "\nNothing is using it yet: `chat_llm_mode` is off, so every answer still comes from Black "
    "Bloc's own written lines."
)
MOODS_HEADER = "\n\n**The pool** — a mood that is off is never picked:"
MOOD_LINE = "· **{name}** ({label}) — {state}"
NO_MOODS = "\n\nThe pool has not been written yet; it fills itself in when Black Bloc starts up."
NO_SUCH_MOOD = (
    "**{name}** is not one of the moods, so nothing was changed. `/chat personality show` lists "
    "them."
)
MOOD_CHANGED = "**{name}** is {state}."


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


class Chat(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._answered: dict[int, float] = {}
        self._seeded: set[int] = set()
        self.last_ingest_at: str | None = None
        self.last_ingest_error: str | None = None

    def loop_health(self, name: str) -> tuple[str | None, str | None]:
        if name == "_ingest":
            return (self.last_ingest_at, self.last_ingest_error)
        return (None, None)

    chat = app_commands.Group(
        name="chat", description="How Black Bloc answers @-mentions",
        default_permissions=STAFF_ONLY,
    )
    chat_knowledge = app_commands.Group(
        name="knowledge", description="What Black Bloc knows about this server", parent=chat
    )

    def usable_db(self) -> Any:
        db = getattr(self.bot, "db", None)
        return db if db is not None and getattr(db, "is_connected", False) else None

    @chat.command(name="status", description="What chat is doing, and what it has spent")
    async def chat_status(self, interaction: discord.Interaction) -> None:
        if not await require_staff(interaction):
            return
        guild_id = interaction.guild.id
        store = self.bot.store
        if store.get(guild_id, "chat_status_admin_only") and not (
            interaction.user.guild_permissions.administrator
        ):
            await interaction.response.send_message(STATUS_ADMIN_ONLY, ephemeral=True)
            return
        llm_on = store.get(guild_id, LLM_MODE_KEY) == ON
        parts = [
            STATUS_MODE.format(mode=store.get(guild_id, "chat_mode"), llm="on" if llm_on else "off")
            + ("" if llm_on else STATUS_OFF_TAIL),
            STATUS_TIERS.format(
                simple=self.tier_words(SIMPLE), important=self.tier_words(IMPORTANT)
            ),
        ]
        db = self.usable_db()
        if db is not None:
            spent = await allowance(db, store, guild_id, interaction.user.id)
            parts.append(
                STATUS_TURNS.format(
                    today=spent.today,
                    today_of=spent.today_of or NO_CEILING,
                    mine=spent.person,
                    of=spent.person_of or NO_CEILING,
                )
            )
            parts.append(
                STATUS_MONEY.format(spent=money(spent.spent), cap=f"${int(spent.cap)}")
            )
            if not spent.ok:
                parts.append(STATUS_CLOSED)
            parts.append(await self.notes_words(db, guild_id))
        if self.last_ingest_error:
            parts.append(STATUS_INGEST_TROUBLE.format(why=self.last_ingest_error))
        await interaction.response.send_message(
            "\n".join(parts), ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
        )

    def tier_words(self, tier: str) -> str:
        """A tier that is down says so, the way a degraded poll does."""
        settings = self.bot.settings
        keyed = (
            settings.important_tier_configured
            if tier == IMPORTANT
            else settings.simple_tier_configured
        )
        if not keyed:
            return TIER_NO_KEY
        trouble = tier_errors(self.bot).get(tier)
        return TIER_TROUBLE.format(why=trouble) if trouble else TIER_READY

    async def notes_words(self, db: Any, guild_id: int) -> str:
        rows = await list_sections(db, guild_id)
        if self.last_ingest_at:
            return STATUS_NOTES.format(count=len(rows), when=stamp(self.last_ingest_at))
        return STATUS_NOTES_NEVER.format(count=len(rows))

    chat_personality = app_commands.Group(
        name="personality", description="The voice Black Bloc answers in", parent=chat
    )

    @chat_personality.command(name="show", description="Which voice is on, and what is in the pool")
    async def personality_show(self, interaction: discord.Interaction) -> None:
        if not await require_staff(interaction):
            return
        voice = str(self.bot.store.get(interaction.guild.id, PERSONALITY_KEY))
        parts = [VOICE_NOW.format(voice=voice, what=VOICE_MEANS.get(voice, VOICE_IS_A_MOOD))]
        if self.bot.store.get(interaction.guild.id, LLM_MODE_KEY) != ON:
            parts.append(VOICE_OFF)
        db = self.usable_db()
        rows = await list_tropes(db) if db is not None else []
        if not rows:
            parts.append(NO_MOODS)
        else:
            parts.append(MOODS_HEADER)
            parts += [
                MOOD_LINE.format(
                    name=row["name"],
                    label=row["label"],
                    state="on" if row["enabled"] else "off",
                )
                for row in rows
            ]
        await interaction.response.send_message(
            "\n".join(parts), ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
        )

    @chat_personality.command(name="set", description="Choose the voice for this server")
    @app_commands.describe(voice="cookout, pool, or one mood by name")
    @app_commands.choices(
        voice=[app_commands.Choice(name=one, value=one) for one in PERSONALITY_CHOICES]
    )
    async def personality_set(
        self, interaction: discord.Interaction, voice: app_commands.Choice[str]
    ) -> None:
        if not await require_staff(interaction):
            return
        await self.bot.store.set(
            interaction.guild.id, PERSONALITY_KEY, voice.value, by=interaction.user.id
        )
        await interaction.response.send_message(
            VOICE_CHANGED.format(voice=voice.value),
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        await log_action(
            self.bot,
            interaction.guild,
            PERSONALITY_SET,
            actor=interaction.user,
            details={"voice": voice.value},
        )

    @chat_personality.command(name="mood", description="Turn one mood in the pool on or off")
    @app_commands.describe(name="The mood's name", on="True to let the pool pick it again")
    async def personality_mood(
        self, interaction: discord.Interaction, name: str, on: bool
    ) -> None:
        if not await require_staff(interaction):
            return
        db = self.usable_db()
        if db is None:
            await interaction.response.send_message(DB_DOWN, ephemeral=True)
            return
        if await get_trope(db, name) is None:
            await interaction.response.send_message(
                NO_SUCH_MOOD.format(name=str(name)[:40]),
                ephemeral=True,
                allowed_mentions=discord.AllowedMentions.none(),
            )
            return
        await set_enabled(db, name, on, by=interaction.user.id)
        forget_tropes(self.bot)
        await interaction.response.send_message(
            MOOD_CHANGED.format(name=str(name).lower(), state="on" if on else "off"),
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        await log_action(
            self.bot,
            interaction.guild,
            TROPE_ENABLED if on else TROPE_DISABLED,
            actor=interaction.user,
            details={"mood": str(name).lower(), "enabled": bool(on)},
        )

    @chat_knowledge.command(name="add", description="Write something down for Black Bloc to quote")
    @app_commands.describe(
        title="What the note is about, in a few words",
        body="The note itself",
        tag="Optional one-word grouping, like events or rules",
    )
    async def knowledge_add(
        self, interaction: discord.Interaction, title: str, body: str, tag: str = ""
    ) -> None:
        if not await require_staff(interaction):
            return
        db = self.usable_db()
        if db is None:
            await interaction.response.send_message(DB_DOWN, ephemeral=True)
            return
        try:
            wanted = (clean_title(title), clean_body(body), clean_tag(tag))
        except KnowledgeError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return
        made = await add_section(
            db,
            interaction.guild.id,
            wanted[0],
            wanted[1],
            tag=wanted[2],
            by=interaction.user.id,
        )
        await interaction.response.send_message(
            NOTE_SAVED.format(id=made, title=wanted[0]),
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        await log_action(
            self.bot,
            interaction.guild,
            KNOWLEDGE_ADDED,
            actor=interaction.user,
            details={"id": made, "title": wanted[0]},
        )

    @chat_knowledge.command(name="list", description="The notes Black Bloc can quote")
    @app_commands.describe(query="Optional words to look for, the way a member's question would")
    async def knowledge_list(self, interaction: discord.Interaction, query: str = "") -> None:
        if not await require_staff(interaction):
            return
        db = self.usable_db()
        if db is None:
            await interaction.response.send_message(DB_DOWN, ephemeral=True)
            return
        rows = await list_sections(db, interaction.guild.id)
        if not rows:
            await interaction.response.send_message(NO_NOTES, ephemeral=True)
            return
        if query.strip():
            wanted = {hit.id for hit in search(rows, query, limit=KNOWLEDGE_LIST_MAX)}
            rows = [row for row in rows if int(row["id"]) in wanted]
            if not rows:
                await interaction.response.send_message(
                    NO_NOTES_MATCH.format(query=query[:60]),
                    ephemeral=True,
                    allowed_mentions=discord.AllowedMentions.none(),
                )
                return
        shown = rows[:KNOWLEDGE_LIST_MAX]
        about = f" matching **{query[:40]}**" if query.strip() else ""
        body = "\n".join(
            [NOTES_HEADER.format(count=len(rows), about=about), *(note_line(r) for r in shown)]
        )
        await interaction.response.send_message(
            body, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
        )

    @chat_knowledge.command(name="remove", description="Forget one written-down note")
    @app_commands.describe(note_id="The number `/chat knowledge list` shows beside it")
    async def knowledge_remove(self, interaction: discord.Interaction, note_id: int) -> None:
        if not await require_staff(interaction):
            return
        db = self.usable_db()
        if db is None:
            await interaction.response.send_message(DB_DOWN, ephemeral=True)
            return
        row = await get_section(db, note_id)
        if row is None or int(row["guild_id"]) != interaction.guild.id:
            await interaction.response.send_message(
                NO_SUCH_NOTE.format(id=note_id), ephemeral=True
            )
            return
        if str(row["source"]) == SERVER:
            await interaction.response.send_message(SERVER_ROW_IS_NOT_YOURS, ephemeral=True)
            return
        title = str(row["title"])
        await remove_section(db, note_id)
        await interaction.response.send_message(
            NOTE_REMOVED.format(id=note_id, title=title),
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        await log_action(
            self.bot,
            interaction.guild,
            KNOWLEDGE_REMOVED,
            actor=interaction.user,
            details={"id": int(note_id), "title": title},
        )

    @chat.command(name="logs", description="The last few chat log lines")
    @app_commands.describe(
        count="How many lines, 1 to 50 (10 by default)",
        important_only="True to leave out the dry runs and the housekeeping",
    )
    async def chat_logs(
        self,
        interaction: discord.Interaction,
        count: app_commands.Range[int, LOGS_MIN, LOGS_MAX] = LOGS_DEFAULT,
        important_only: bool = False,
    ) -> None:
        await send_logs(interaction, "chat", count=count, important_only=important_only)

    @chat.command(name="settings", description="Show how chat is set up for this server")
    async def chat_settings(self, interaction: discord.Interaction) -> None:
        if not await require_staff(interaction):
            return
        store = self.bot.store
        lines = [
            f"`{key}` — **{display_value(key, store.get(interaction.guild.id, key))}**"
            for key in CHAT_KEYS
        ]
        await interaction.response.send_message(
            "\n".join([*lines, "", SETTINGS_FOOTER]),
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )

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
        answer = await answer_for(text, author, self.bot, channel=channel, llm=True)
        if not answer.text:
            return
        if await self.waved_instead(message, text, guild_id, answer.intent):
            self._answered[user_id] = now
            return
        try:
            await message.reply(
                answer.text,
                mention_author=False,
                allowed_mentions=self.mentions_for(guild, author),
            )
        except Exception as exc:
            log.warning(
                "chat: %s could not be answered — %s: %s", user_id, type(exc).__name__, exc
            )
            return
        self._answered[user_id] = now
        log.info("chat: answered %s (%s)", user_id, answer.intent)
        if guild is None:
            return
        if answer.tier:
            await log_action(
                self.bot, guild, REPLY_KIND, actor=author, details={"tier": answer.tier}
            )
        if answer.intent == INSULT:
            await log_action(
                self.bot, guild, LOG_KIND, actor=author, details={"intent": answer.intent}
            )
        if answer.kind == ROUTE:
            await self.tell_staff(guild, message, author)
            await log_action(
                self.bot, guild, ROUTE_KIND, actor=author, details={"intent": answer.intent}
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
