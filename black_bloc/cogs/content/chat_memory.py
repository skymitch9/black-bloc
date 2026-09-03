from __future__ import annotations

import logging
from typing import Any, NamedTuple

import discord
from discord import app_commands
from discord.ext import commands

from ...actionlog import log_action
from ...chat_memory import (
    BY_LEAVE,
    BY_SELF,
    CONSENT_KEY,
    FACT_NAME,
    FACT_NOTE,
    FACT_THREAD,
    FORGOT_KIND,
    MODE_KEY,
    OFF,
    ON,
    OPTIN_KIND,
    OPTOUT,
    OPTOUT_KIND,
    drop_fact,
    drop_matching,
    fact_at,
    fact_key,
    facts_of,
    forget,
    forget_everywhere,
    profile_for,
    remembers,
    save_profile,
    set_remembered,
)
from ...logkinds import VIA_DISCORD, kind_via
from ...panels import (
    NoteModal,
    Panel,
    answer,
    capped_placeholder,
    db_ready,
    db_up,
    option_label,
    panel_minutes,
    retire,
)
from ...settings_store import DB_UNAVAILABLE

log = logging.getLogger(__name__)

PANEL_MINUTES_KEY = "memory_panel_minutes"
PANEL_TITLE = "What Black Bloc remembers about you"
PANEL_TIMEOUT_FOOTER = "This panel has gone quiet — run /memory again"
COMMAND_DESCRIPTION = "What Black Bloc remembers about you"
SELECT_CAP = 25
WORDS_LIMIT = 200

MEMORY_IS_OFF = (
    "Black Bloc is not remembering anybody here at the moment, so nothing new is being written "
    "down. Whatever it already had is above, and the buttons still clear it. A Lead turns it "
    "back on with `/settings set-value key:chat_memory_mode value:on`."
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
    "Black Bloc is not remembering you, so nothing new is being written down. "
    "**Remember me again** lets it start."
)
HEADER = "Nobody else can read this."
CALL_ME_LINE = "**#{number}** It calls you **{text}**."
NOTE_LINE = "**#{number}** {text}"
THREAD_LINE = "**#{number}** *still open:* {text}"
DM_MARK = " *(learned in a DM — never used in a channel)*"
FORGOTTEN = "Cleared. Black Bloc remembers nothing about you here."
NOTHING_TO_FORGET = "There was nothing written down about you, so nothing was cleared."
DROPPED = "Dropped **{count}** line(s). What is left is above."
NO_MATCH = (
    "Nothing written down matches **{words}**, so nothing was dropped. **Forget one of these…** "
    "lists every line in the same words you can point at."
)
TURNED_OFF = (
    "Black Bloc will not write anything down about you from now on, and what it had is gone. "
    "**Remember me again** starts it."
)
ALREADY_OFF = "Black Bloc was already not remembering you. Nothing changed."
TURNED_ON = (
    "Black Bloc may write down your preferences again — what to call you and how you like to be "
    "answered, never what you said. The panel above reads it back."
)
ALREADY_ON = "Black Bloc was already allowed to remember you. Nothing changed."
FORGET_THIS_NEEDS_WORDS = (
    "Say a few words from the line you want dropped, the way the panel prints them, and send it "
    "again."
)
PROFILE_MOVED = (
    "That line is not there any more — Black Bloc wrote your profile up again while the panel "
    "was open, so nothing was dropped. The list above is what it holds now."
)

PICK_A_LINE = "Forget one of these…"
PICK_CAPPED = "{shown} of {total} — Forget by words… reaches the rest"
FORGET_WORDS_TITLE = "Forget by words"
FORGET_WORDS_LABEL = "A few words from the line you want dropped"
CONFIRM_TITLE = "Are you sure?"
FORGET_ALL_QUESTION = (
    "Clear everything Black Bloc has written down about you here? There is no undo."
)
STOP_QUESTION = (
    "Stop Black Bloc remembering you? It clears what it already has as well, and there is no "
    "undo."
)

FORGET_ALL = "forget_all"
FORGET_WORDS = "forget_words"
DROP_ONE = "drop_one"
STOP = "stop"
START = "start"
REFRESH = "refresh"

FACT_WORDS = {FACT_NAME: "what it calls you", FACT_NOTE: "", FACT_THREAD: "still open"}
FACT_LINES = {FACT_NAME: CALL_ME_LINE, FACT_NOTE: NOTE_LINE, FACT_THREAD: THREAD_LINE}
STYLES = {
    "primary": discord.ButtonStyle.primary,
    "secondary": discord.ButtonStyle.secondary,
    "success": discord.ButtonStyle.success,
    "danger": discord.ButtonStyle.danger,
}


class MemoryMove(NamedTuple):
    action: str
    label: str
    style: str
    question: str = ""
    yes: str = ""
    modal: bool = False


FORGET_ALL_MOVE = MemoryMove(
    FORGET_ALL, "Forget everything", "danger", FORGET_ALL_QUESTION, "Yes, forget it all"
)
FORGET_WORDS_MOVE = MemoryMove(FORGET_WORDS, "Forget by words…", "secondary", modal=True)
STOP_MOVE = MemoryMove(STOP, "Stop remembering me", "danger", STOP_QUESTION, "Yes, stop")
START_MOVE = MemoryMove(START, "Remember me again", "success")
REFRESH_MOVE = MemoryMove(REFRESH, "Refresh", "secondary")
KEEP_IT = "Keep it"

PANEL_MOVES = (FORGET_ALL_MOVE, FORGET_WORDS_MOVE, STOP_MOVE, START_MOVE, REFRESH_MOVE)


def moves_for(*, remembered: bool, facts: int) -> tuple[MemoryMove, ...]:
    """§C's table as data: the forget controls come from the count, never from the consent."""
    found: list[MemoryMove] = []
    if facts:
        found.append(FORGET_ALL_MOVE)
    if facts > SELECT_CAP:
        found.append(FORGET_WORDS_MOVE)
    found.append(STOP_MOVE if remembered else START_MOVE)
    found.append(REFRESH_MOVE)
    return tuple(found)


def scope_mark(note: Any) -> str:
    return DM_MARK if getattr(note, "where", "") == "dm" else ""


def fact_line(fact: Any, number: int) -> str:
    return FACT_LINES[fact.kind].format(number=number, text=fact.text) + scope_mark(fact)


def profile_words(profile: Any) -> list[str]:
    """What the person reads back; if a line would embarrass the bot here, it is content."""
    lines = [HEADER]
    lines += [fact_line(one, spot + 1) for spot, one in enumerate(facts_of(profile))]
    return lines


def home_of(bot: Any, interaction: discord.Interaction) -> int | None:
    """A DM has no server of its own, so it files under the one server Black Bloc is in."""
    guild = getattr(interaction, "guild", None)
    if guild is not None:
        return int(guild.id)
    found = getattr(getattr(bot, "settings", None), "dev_guild_id", None)
    return int(found) if found else None


def guild_for(bot: Any, home: int) -> Any:
    return bot.get_guild(home)


def consent_of(bot: Any, home: int) -> str:
    return str(bot.store.get(home, CONSENT_KEY) or OPTOUT)


def memory_on(bot: Any, home: int) -> bool:
    return bot.store.get(home, MODE_KEY) == ON


def minutes_for(bot: Any, home: int) -> int:
    return panel_minutes(bot.store, home, PANEL_MINUTES_KEY)


async def noted(
    bot: Any, guild: Any, kind: str, member: Any, details: dict[str, Any]
) -> None:
    if guild is None:
        return
    await log_action(bot, guild, kind, actor=member, target=member, details=details)


async def forget_profile(
    bot: Any,
    guild: Any,
    target: Any,
    actor: Any,
    *,
    home: int | None = None,
    who_asked: str = BY_SELF,
    via: str = VIA_DISCORD,
) -> tuple[str, Any]:
    """The one place a whole profile is cleared, from either door — one write, one log row."""
    where = int(home) if home is not None else int(guild.id)
    who = int(getattr(target, "id", target) or 0)
    if not await forget(bot.db, who, where):
        return (NOTHING_TO_FORGET, None)
    if guild is not None:
        await log_action(
            bot,
            guild,
            kind_via(FORGOT_KIND, via),
            actor=actor,
            target=target,
            details={"who_asked": who_asked, "via": via},
        )
    return (FORGOTTEN, None)


async def drop_one_fact(
    bot: Any,
    guild: Any,
    member: Any,
    home: int,
    profile: Any,
    key: Any,
    *,
    via: str = VIA_DISCORD,
) -> tuple[str, Any]:
    fresh, gone = drop_fact(profile, key)
    if not gone:
        return (PROFILE_MOVED, profile)
    await save_profile(bot.db, member.id, home, fresh)
    await noted(
        bot,
        guild,
        kind_via(FORGOT_KIND, via),
        member,
        {"who_asked": BY_SELF, "lines": gone, "via": via},
    )
    return (DROPPED.format(count=gone), fresh)


async def drop_by_words(
    bot: Any,
    guild: Any,
    member: Any,
    home: int,
    profile: Any,
    words: Any,
    *,
    via: str = VIA_DISCORD,
) -> tuple[str, Any]:
    wanted = str(words or "").strip()[:WORDS_LIMIT]
    if not wanted:
        return (FORGET_THIS_NEEDS_WORDS, profile)
    if profile is None or profile.empty:
        return (NOTHING_TO_FORGET, profile)
    fresh, gone = drop_matching(profile, wanted)
    if not gone:
        return (
            NO_MATCH.format(words=discord.utils.escape_markdown(wanted[:60])),
            profile,
        )
    await save_profile(bot.db, member.id, home, fresh)
    await noted(
        bot,
        guild,
        kind_via(FORGOT_KIND, via),
        member,
        {"who_asked": BY_SELF, "lines": gone, "via": via},
    )
    return (DROPPED.format(count=gone), fresh)


async def stop_remembering(
    bot: Any, guild: Any, member: Any, home: int, *, via: str = VIA_DISCORD
) -> tuple[str, Any]:
    """Opt out first, then wipe: the order is the promise, not an implementation detail."""
    consent = consent_of(bot, home)
    if not await remembers(bot.db, member.id, home, consent=consent):
        return (ALREADY_OFF, await profile_for(bot.db, member.id, home))
    await set_remembered(bot.db, member.id, home, consent=consent, wanted=False)
    await forget(bot.db, member.id, home)
    await noted(bot, guild, kind_via(OPTOUT_KIND, via), member, {"via": via})
    return (TURNED_OFF, None)


async def start_remembering(
    bot: Any, guild: Any, member: Any, home: int, *, via: str = VIA_DISCORD
) -> tuple[str, Any]:
    consent = consent_of(bot, home)
    profile = await profile_for(bot.db, member.id, home)
    if await remembers(bot.db, member.id, home, consent=consent):
        return (ALREADY_ON, profile)
    await set_remembered(bot.db, member.id, home, consent=consent, wanted=True)
    await noted(bot, guild, kind_via(OPTIN_KIND, via), member, {"via": via})
    return (TURNED_ON, profile)


MOVE_FUNCS: dict[str, Any] = {
    FORGET_ALL: lambda bot, guild, member, home, profile, extra: forget_profile(
        bot, guild, member, member, home=home
    ),
    FORGET_WORDS: lambda bot, guild, member, home, profile, extra: drop_by_words(
        bot, guild, member, home, profile, extra
    ),
    DROP_ONE: lambda bot, guild, member, home, profile, extra: drop_one_fact(
        bot, guild, member, home, profile, extra
    ),
    STOP: lambda bot, guild, member, home, profile, extra: stop_remembering(
        bot, guild, member, home
    ),
    START: lambda bot, guild, member, home, profile, extra: start_remembering(
        bot, guild, member, home
    ),
}


class MemoryPanel(Panel):
    def __init__(self, minutes: int) -> None:
        super().__init__(minutes, footer=PANEL_TIMEOUT_FOOTER)


async def panel_state(bot: Any, home: int, member: Any) -> tuple[bool, Any]:
    remembered = await remembers(
        bot.db, member.id, home, consent=consent_of(bot, home)
    )
    return (remembered, await profile_for(bot.db, member.id, home))


def memory_embed(bot: Any, home: int, remembered: bool, profile: Any) -> discord.Embed:
    lines = profile_words(profile)
    if not facts_of(profile):
        lines.append(NOTHING_YET)
    if not remembered:
        lines.append(YOU_ARE_OPTED_OUT)
    if not memory_on(bot, home):
        lines.append(MEMORY_IS_OFF)
    return discord.Embed(title=PANEL_TITLE, description="\n".join(lines))


async def build_panel(bot: Any, home: int, member: Any) -> tuple[discord.Embed, Any]:
    """One panel, mine only: the facts as numbered lines, and only the moves that are valid."""
    remembered, profile = await panel_state(bot, home, member)
    facts = facts_of(profile)
    embed = memory_embed(bot, home, remembered, profile)
    view = MemoryPanel(minutes_for(bot, home))
    if facts:
        view.add_item(ForgetOnePick(facts))
    for move in moves_for(remembered=remembered, facts=len(facts)):
        view.add_item(MoveButton(move))
    return (embed, view)


async def render_panel(interaction: discord.Interaction, previous: Any = None) -> None:
    bot = interaction.client
    home = home_of(bot, interaction)
    if home is None:
        await answer(interaction, NO_SERVER)
        return
    embed, view = await build_panel(bot, home, interaction.user)
    retire(previous)
    view.message = await interaction.edit_original_response(embed=embed, view=view)


async def back_to_panel(interaction: discord.Interaction, previous: Any = None) -> None:
    await interaction.response.defer()
    if not await db_ready(interaction):
        return
    await render_panel(interaction, previous)


async def open_confirm(
    interaction: discord.Interaction, move: MemoryMove, previous: Any = None
) -> None:
    await interaction.response.defer()
    if not await db_ready(interaction):
        return
    bot = interaction.client
    home = home_of(bot, interaction)
    if home is None:
        await answer(interaction, NO_SERVER)
        return
    remembered, profile = await panel_state(bot, home, interaction.user)
    embed = memory_embed(bot, home, remembered, profile)
    embed.add_field(name=CONFIRM_TITLE, value=move.question, inline=False)
    view = MemoryPanel(minutes_for(bot, home))
    view.add_item(ConfirmYesButton(move))
    view.add_item(KeepItButton())
    retire(previous)
    view.message = await interaction.edit_original_response(embed=embed, view=view)


async def run_move(
    interaction: discord.Interaction,
    action: str,
    extra: Any = None,
    previous: Any = None,
) -> None:
    await interaction.response.defer()
    if not await db_ready(interaction):
        return
    bot = interaction.client
    home = home_of(bot, interaction)
    if home is None:
        await answer(interaction, NO_SERVER)
        return
    member = interaction.user
    profile = await profile_for(bot.db, member.id, home)
    said, _ = await MOVE_FUNCS[action](
        bot, guild_for(bot, home), member, home, profile, extra
    )
    await render_panel(interaction, previous)
    await answer(interaction, said)


async def drop_picked(
    interaction: discord.Interaction, key: str, rendered: Any, previous: Any = None
) -> None:
    """A distillation can land between render and click, so the line is re-read before it goes."""
    await interaction.response.defer()
    if not await db_ready(interaction):
        return
    bot = interaction.client
    home = home_of(bot, interaction)
    if home is None:
        await answer(interaction, NO_SERVER)
        return
    member = interaction.user
    profile = await profile_for(bot.db, member.id, home)
    found = fact_at(profile, key)
    if rendered is None or found is None or found.text != rendered.text:
        await render_panel(interaction, previous)
        await answer(interaction, PROFILE_MOVED)
        return
    said, _ = await drop_one_fact(
        bot, guild_for(bot, home), member, home, profile, key
    )
    await render_panel(interaction, previous)
    await answer(interaction, said)


class ForgetOnePick(discord.ui.Select):
    def __init__(self, facts: Any) -> None:
        shown = list(facts)[:SELECT_CAP]
        self.shown = {fact_key(one): one for one in shown}
        super().__init__(
            placeholder=capped_placeholder(
                len(shown), len(facts), pick=PICK_A_LINE, capped=PICK_CAPPED
            ),
            options=[
                discord.SelectOption(
                    label=option_label(spot + 1, FACT_WORDS[one.kind], one.text),
                    value=fact_key(one),
                )
                for spot, one in enumerate(shown)
            ],
            min_values=1,
            max_values=1,
            row=0,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        picked = self.values[0]
        await drop_picked(interaction, picked, self.shown.get(picked), self.view)


class MoveButton(discord.ui.Button):
    def __init__(self, move: MemoryMove) -> None:
        super().__init__(label=move.label, style=STYLES[move.style], row=1)
        self.move = move

    async def callback(self, interaction: discord.Interaction) -> None:
        if self.move.modal:
            if not await db_up(interaction):
                return
            await interaction.response.send_modal(ForgetWordsModal(self.view))
            return
        if self.move.question:
            await open_confirm(interaction, self.move, self.view)
            return
        if self.move.action == REFRESH:
            await back_to_panel(interaction, self.view)
            return
        await run_move(interaction, self.move.action, None, self.view)


class ConfirmYesButton(discord.ui.Button):
    def __init__(self, move: MemoryMove) -> None:
        super().__init__(label=move.yes, style=discord.ButtonStyle.danger, row=0)
        self.move = move

    async def callback(self, interaction: discord.Interaction) -> None:
        await run_move(interaction, self.move.action, None, self.view)


class KeepItButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label=KEEP_IT, style=discord.ButtonStyle.secondary, row=0)

    async def callback(self, interaction: discord.Interaction) -> None:
        await back_to_panel(interaction, self.view)


class ForgetWordsModal(NoteModal):
    def __init__(self, previous: Any) -> None:
        self.previous = previous
        super().__init__(
            title=FORGET_WORDS_TITLE,
            label=FORGET_WORDS_LABEL,
            max_length=WORDS_LIMIT,
            on_submit=self.words_given,
            required=True,
        )

    async def words_given(self, interaction: discord.Interaction, note: str) -> None:
        await run_move(interaction, FORGET_WORDS, note, self.previous)


class ChatMemory(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    def home(self, interaction: discord.Interaction) -> int | None:
        return home_of(self.bot, interaction)

    def usable_db(self) -> Any:
        db = getattr(self.bot, "db", None)
        return db if db is not None and getattr(db, "is_connected", False) else None

    async def ready(self, interaction: discord.Interaction) -> tuple[Any, int] | None:
        """Two refusals, each a sentence; memory being off is a LINE on the panel, not a no."""
        home = self.home(interaction)
        if home is None:
            await answer(interaction, NO_SERVER)
            return None
        db = self.usable_db()
        if db is None:
            await answer(interaction, DB_UNAVAILABLE)
            return None
        return (db, home)

    @app_commands.command(name="memory", description=COMMAND_DESCRIPTION)
    async def memory(self, interaction: discord.Interaction) -> None:
        found = await self.ready(interaction)
        if found is None:
            return
        _, home = found
        embed, view = await build_panel(self.bot, home, interaction.user)
        await interaction.response.send_message(
            embed=embed,
            view=view,
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        view.message = await interaction.original_response()

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


__all__ = [
    "MEMORY_IS_OFF",
    "OFF",
    "PANEL_MINUTES_KEY",
    "PANEL_MOVES",
    "PANEL_TIMEOUT_FOOTER",
    "ChatMemory",
    "ForgetOnePick",
    "ForgetWordsModal",
    "MemoryMove",
    "MemoryPanel",
    "MoveButton",
    "build_panel",
    "drop_by_words",
    "drop_one_fact",
    "forget_profile",
    "moves_for",
    "profile_words",
    "render_panel",
    "start_remembering",
    "stop_remembering",
]
