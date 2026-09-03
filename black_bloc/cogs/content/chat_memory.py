from __future__ import annotations

import logging
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands

from ...actionlog import log_action
from ...chat_memory import (
    BY_LEAVE,
    BY_SELF,
    CONSENT_KEY,
    FORGOT_KIND,
    MODE_KEY,
    OFF,
    ON,
    OPTIN_KIND,
    OPTOUT,
    OPTOUT_KIND,
    drop_matching,
    forget,
    forget_everywhere,
    profile_for,
    remembers,
    save_profile,
    set_remembered,
)
from ...settings_store import DB_UNAVAILABLE

log = logging.getLogger(__name__)

MEMORY_IS_OFF = (
    "Black Bloc is not remembering anybody here at the moment, so there is nothing to show and "
    "nothing being written down. A Lead turns it on with `/settings set chat_memory_mode on`."
)
NO_SERVER = (
    "Black Bloc keeps what it remembers per server, and this conversation is not in one it "
    "knows, so there was nothing to look at. Run the command in the server instead."
)
NOTHING_YET = (
    "Black Bloc has not written anything down about you yet. It only keeps preferences — what to "
    "call you and how you like to be answered — and only after a conversation or two."
)
YOU_ARE_OPTED_OUT = (
    "Black Bloc is not remembering you, so there is nothing written down. `/memory on` lets it "
    "start again."
)
HEADER = "**What Black Bloc remembers about you.** Nobody else can read this."
CALL_ME_LINE = "· It calls you **{name}**."
NOTE_LINE = "· {text}"
THREAD_LINE = "· *still open:* {text}"
DM_MARK = " *(learned in a DM — never used in a channel)*"
SHOW_FOOT = (
    "`/memory forget-this <a few words>` drops one line, `/memory forget` clears the lot, and "
    "`/memory off` stops it writing anything down at all."
)
FORGOTTEN = "Cleared. Black Bloc remembers nothing about you here."
NOTHING_TO_FORGET = "There was nothing written down about you, so nothing was cleared."
DROPPED = "Dropped **{count}** line(s). `/memory show` is what is left."
NO_MATCH = (
    "Nothing written down matches **{words}**, so nothing was dropped. `/memory show` lists it "
    "in the same words you can point at."
)
TURNED_OFF = (
    "Black Bloc will not write anything down about you from now on, and what it had is gone. "
    "`/memory on` starts it again."
)
ALREADY_OFF = "Black Bloc was already not remembering you. Nothing changed."
TURNED_ON = (
    "Black Bloc may write down your preferences again — what to call you and how you like to be "
    "answered, never what you said. `/memory show` reads it back."
)
ALREADY_ON = "Black Bloc was already allowed to remember you. Nothing changed."
FORGET_THIS_NEEDS_WORDS = (
    "Say a few words from the line you want dropped, the way `/memory show` prints them, and "
    "send it again."
)

WORDS_LIMIT = 200


def scope_mark(note: Any) -> str:
    return DM_MARK if getattr(note, "where", "") == "dm" else ""


def profile_words(profile: Any) -> list[str]:
    """What the person reads back; if a line would embarrass the bot here, it is content."""
    lines = [HEADER]
    if profile.call_me:
        lines.append(CALL_ME_LINE.format(name=profile.call_me))
    lines += [NOTE_LINE.format(text=one.text) + scope_mark(one) for one in profile.notes]
    lines += [THREAD_LINE.format(text=one.text) + scope_mark(one) for one in profile.threads]
    lines.append(SHOW_FOOT)
    return lines


class ChatMemory(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    memory = app_commands.Group(
        name="memory", description="What Black Bloc remembers about you"
    )

    def home(self, interaction: discord.Interaction) -> int | None:
        """A DM has no server of its own, so it files under the one server Black Bloc is in."""
        guild = getattr(interaction, "guild", None)
        if guild is not None:
            return int(guild.id)
        found = getattr(self.bot.settings, "dev_guild_id", None)
        return int(found) if found else None

    def usable_db(self) -> Any:
        db = getattr(self.bot, "db", None)
        return db if db is not None and getattr(db, "is_connected", False) else None

    async def ready(self, interaction: discord.Interaction) -> tuple[Any, int] | None:
        """Every refusal is a sentence: no server, no database, or the feature switched off."""
        home = self.home(interaction)
        if home is None:
            await self.say(interaction, NO_SERVER)
            return None
        db = self.usable_db()
        if db is None:
            await self.say(interaction, DB_UNAVAILABLE)
            return None
        if self.bot.store.get(home, MODE_KEY) != ON:
            await self.say(interaction, MEMORY_IS_OFF)
            return None
        return (db, home)

    async def say(self, interaction: discord.Interaction, text: str) -> None:
        await interaction.response.send_message(
            text, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
        )

    def consent(self, home: int) -> str:
        return str(self.bot.store.get(home, CONSENT_KEY) or OPTOUT)

    async def noted(self, home: int, kind: str, user: Any, details: Any = None) -> None:
        guild = self.bot.get_guild(home)
        if guild is None:
            return
        await log_action(
            self.bot, guild, kind, actor=user, target=user, details=details or {}
        )

    @memory.command(name="show", description="Read back everything Black Bloc remembers about you")
    async def memory_show(self, interaction: discord.Interaction) -> None:
        found = await self.ready(interaction)
        if found is None:
            return
        db, home = found
        if not await remembers(db, interaction.user.id, home, consent=self.consent(home)):
            await self.say(interaction, YOU_ARE_OPTED_OUT)
            return
        profile = await profile_for(db, interaction.user.id, home)
        if profile is None or profile.empty:
            await self.say(interaction, NOTHING_YET)
            return
        await self.say(interaction, "\n".join(profile_words(profile)))

    @memory.command(name="forget", description="Clear everything Black Bloc remembers about you")
    async def memory_forget(self, interaction: discord.Interaction) -> None:
        found = await self.ready(interaction)
        if found is None:
            return
        db, home = found
        if not await forget(db, interaction.user.id, home):
            await self.say(interaction, NOTHING_TO_FORGET)
            return
        await self.say(interaction, FORGOTTEN)
        await self.noted(home, FORGOT_KIND, interaction.user, {"who_asked": BY_SELF})

    @memory.command(name="forget-this", description="Drop one line by a few of its words")
    @app_commands.describe(words="A few words from the line, as `/memory show` prints it")
    async def memory_forget_this(self, interaction: discord.Interaction, words: str) -> None:
        found = await self.ready(interaction)
        if found is None:
            return
        db, home = found
        wanted = str(words or "").strip()[:WORDS_LIMIT]
        if not wanted:
            await self.say(interaction, FORGET_THIS_NEEDS_WORDS)
            return
        profile = await profile_for(db, interaction.user.id, home)
        if profile is None or profile.empty:
            await self.say(interaction, NOTHING_TO_FORGET)
            return
        fresh, gone = drop_matching(profile, wanted)
        if not gone:
            await self.say(interaction, NO_MATCH.format(words=discord.utils.escape_markdown(
                wanted[:60]
            )))
            return
        await save_profile(db, interaction.user.id, home, fresh)
        await self.say(interaction, DROPPED.format(count=gone))
        await self.noted(
            home, FORGOT_KIND, interaction.user, {"who_asked": BY_SELF, "lines": gone}
        )

    @memory.command(name="off", description="Stop Black Bloc remembering you, and clear it")
    async def memory_off(self, interaction: discord.Interaction) -> None:
        found = await self.ready(interaction)
        if found is None:
            return
        db, home = found
        consent = self.consent(home)
        if not await remembers(db, interaction.user.id, home, consent=consent):
            await self.say(interaction, ALREADY_OFF)
            return
        await set_remembered(db, interaction.user.id, home, consent=consent, wanted=False)
        await forget(db, interaction.user.id, home)
        await self.say(interaction, TURNED_OFF)
        await self.noted(home, OPTOUT_KIND, interaction.user)

    @memory.command(name="on", description="Let Black Bloc remember your preferences again")
    async def memory_on(self, interaction: discord.Interaction) -> None:
        found = await self.ready(interaction)
        if found is None:
            return
        db, home = found
        consent = self.consent(home)
        if await remembers(db, interaction.user.id, home, consent=consent):
            await self.say(interaction, ALREADY_ON)
            return
        await set_remembered(db, interaction.user.id, home, consent=consent, wanted=True)
        await self.say(interaction, TURNED_ON)
        await self.noted(home, OPTIN_KIND, interaction.user)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        """Leaving the server clears the profile at once, whatever the retention setting says."""
        db = self.usable_db()
        if db is None:
            return
        gone = await forget_everywhere(db, getattr(member, "id", 0))
        if not gone:
            return
        guild = getattr(member, "guild", None)
        if guild is None:
            return
        await log_action(
            self.bot,
            guild,
            FORGOT_KIND,
            target=getattr(member, "id", None),
            details={"who_asked": BY_LEAVE, "profiles": gone},
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ChatMemory(bot))


__all__ = ["ChatMemory", "profile_words", "MEMORY_IS_OFF", "OFF"]
