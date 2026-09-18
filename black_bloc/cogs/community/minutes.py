from __future__ import annotations

import logging
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands, tasks

from ... import minutes as mins
from ...actionlog import log_action, send_logs
from ...command_errors import AnswersErrors
from ...command_visibility import STAFF_ONLY
from ...loops import wait_ready
from ...minutes_session import Session, finish
from ...panels import (
    KEEP_IT,
    Outcome,
    Panel,
    answer,
    clamped,
    confirm,
    confirm_items,
    opened,
    refusal,
    retire,
    still_staff,
)
from ...settings_store import DB_UNAVAILABLE, GUILD_ONLY, require_staff

log = logging.getLogger(__name__)

COG_NAME = "Minutes"
LOOP_NAME = "sweep"
SWEEP_MINUTES = 5
SELECT_CAP = 25
NOTES_BOX_MAX = 4000
PICK_A_MEETING = "A meeting…"
PICK_A_CHANNEL = "Where the notes go…"
BACK = "Back"
EDIT_LABEL = "Edit the notes…"
REWRITE_LABEL = "Write the notes again"
DELETE_YES = "Yes, delete it"
DELETE_QUESTION = (
    "The notes and every word of the transcript go with it. Nothing puts them back."
)
EDIT_MODAL_TITLE = "The notes for this meeting"
NOTES_FIELD = "The notes"
NOT_WRITTEN_YET = "No notes were written for this one."
CHANNEL_SET = "Notes and announcements will go to {where} from now on."


def meeting_line(guild: Any, row: Any) -> str:
    where = mins.where_words(guild, row["channel_id"])
    started = str(row["started_at"])[:16].replace("T", " ")
    return f"**#{row['id']}** · {where} · {started} · {mins.status_words(row)}"


def option_label(guild: Any, row: Any) -> str:
    return f"#{row['id']} · {str(row['started_at'])[:16].replace('T', ' ')}"[:100]


def running_in(bot: Any, guild_id: int) -> Session | None:
    return getattr(bot, "minutes_sessions", {}).get(int(guild_id))


def sessions_of(bot: Any) -> dict[int, Session]:
    found = getattr(bot, "minutes_sessions", None)
    if found is None:
        found = {}
        bot.minutes_sessions = found
    return found


async def build_panel(bot: Any, guild: Any) -> tuple[discord.Embed, MinutesView]:
    rows = await mins.list_meetings(bot.db, guild.id)
    session = running_in(bot, guild.id)
    lines = [mins.PANEL_INTRO]
    if session is not None:
        lines.extend(session.status_lines())
    if mins.minutes_are_off(bot.store, guild.id):
        lines.append(mins.MINUTES_OFF)
    lines.extend(meeting_line(guild, row) for row in rows)
    if not rows:
        lines.append(mins.PANEL_EMPTY)
    embed = discord.Embed(title=mins.PANEL_TITLE, description=clamped(lines))
    view = MinutesView(mins.panel_minutes(bot.store, guild.id))
    if session is None:
        view.add_item(StartButton())
    else:
        view.add_item(StopButton())
    view.add_item(WhereButton())
    view.add_item(LogsButton())
    page = mins.site_page_url(getattr(bot.settings, "origin", ""))
    if page:
        view.add_item(
            discord.ui.Button(
                style=discord.ButtonStyle.link, label=mins.SITE_LABEL, url=page, row=0
            )
        )
    if rows:
        view.add_item(MeetingPick(guild, rows))
    return embed, view


def build_card(bot: Any, guild: Any, row: Any) -> tuple[discord.Embed, MinutesView]:
    lines = [meeting_line(guild, row), str(mins.row_value(row, "notes", "")) or NOT_WRITTEN_YET]
    embed = discord.Embed(title=f"Meeting #{row['id']}", description=clamped(lines))
    meeting_id = int(row["id"])
    view = MinutesView(mins.panel_minutes(bot.store, guild.id))
    if str(mins.row_value(row, "status", mins.RECORDING)) != mins.RECORDING:
        view.add_item(PostAgainButton(meeting_id))
        view.add_item(EditNotesButton(meeting_id))
        view.add_item(RewriteButton(meeting_id))
    view.add_item(DeleteButton(meeting_id))
    view.add_item(BackButton())
    return embed, view


async def render_panel(interaction: discord.Interaction, previous: Any = None) -> None:
    embed, view = await build_panel(interaction.client, interaction.guild)
    retire(previous)
    view.message = await interaction.edit_original_response(
        embed=embed, view=view, allowed_mentions=discord.AllowedMentions.none()
    )


async def back_to_panel(interaction: discord.Interaction, previous: Any = None) -> None:
    if not await opened(interaction):
        return
    await render_panel(interaction, previous)


async def render_card(
    interaction: discord.Interaction, meeting_id: int, previous: Any = None, said: str | None = None
) -> None:
    bot = interaction.client
    row = await mins.get_meeting(bot.db, interaction.guild.id, meeting_id)
    if row is None:
        await render_panel(interaction, previous)
    else:
        embed, view = build_card(bot, interaction.guild, row)
        retire(previous)
        view.message = await interaction.edit_original_response(
            embed=embed, view=view, allowed_mentions=discord.AllowedMentions.none()
        )
    if said:
        await interaction.followup.send(
            said, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
        )


async def start_meeting(bot: Any, guild: Any, member: Any) -> Any:
    """Every refusal first, then the row, the join, and the announcement."""
    voice = getattr(getattr(member, "voice", None), "channel", None)
    allowed = await mins.may_start(bot, guild, member, voice)
    if not allowed.ok:
        return allowed
    row = await mins.start_row(bot.db, guild.id, voice.id, member.id)
    session = Session(bot, guild, voice, row)
    joined = await session.start()
    if not joined.ok:
        return joined
    sessions_of(bot)[int(guild.id)] = session
    note = await session.announce()
    await log_action(
        bot,
        guild,
        mins.STARTED,
        actor=member,
        details={"meeting": session.meeting_id, "channel": voice.id},
    )
    said = mins.STARTED_SAID.format(where=getattr(voice, "name", voice))
    return Outcome(True, f"{said} {note}".strip(), value=session)


async def stop_meeting(bot: Any, guild: Any, reason: str) -> Any:
    session = sessions_of(bot).pop(int(guild.id), None)
    if session is None:
        return refusal(mins.NO_MEETING_RUNNING, "no_meeting", 409)
    stopped = await session.stop(reason)
    if not stopped.ok:
        return stopped
    written = await finish(bot, guild, session.meeting_id)
    said = mins.STOPPED_SAID.format(where=mins.where_words(guild, session.channel.id))
    return Outcome(True, f"{said} {written.message}".strip(), value=session.meeting_id)


class MinutesView(Panel):
    def __init__(self, minutes: int) -> None:
        super().__init__(minutes, footer=mins.PANEL_TIMEOUT_FOOTER)


class StartButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label=mins.START_LABEL, style=discord.ButtonStyle.success, row=0)

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await opened(interaction):
            return
        found = await start_meeting(interaction.client, interaction.guild, interaction.user)
        await render_panel(interaction, self.view)
        await interaction.followup.send(
            found.message, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
        )


class StopButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label=mins.STOP_LABEL, style=discord.ButtonStyle.danger, row=0)

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await opened(interaction):
            return
        found = await stop_meeting(interaction.client, interaction.guild, mins.BY_HAND)
        await render_panel(interaction, self.view)
        await interaction.followup.send(
            found.message, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
        )


class WhereButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label=mins.WHERE_LABEL, style=discord.ButtonStyle.secondary, row=0)

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await opened(interaction):
            return
        embed, view = await build_panel(interaction.client, interaction.guild)
        view.add_item(ChannelPick())
        retire(self.view)
        view.message = await interaction.edit_original_response(
            embed=embed, view=view, allowed_mentions=discord.AllowedMentions.none()
        )


class ChannelPick(discord.ui.ChannelSelect):
    def __init__(self) -> None:
        super().__init__(
            placeholder=PICK_A_CHANNEL,
            channel_types=[discord.ChannelType.text, discord.ChannelType.news],
            min_values=1,
            max_values=1,
            row=2,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await opened(interaction):
            return
        bot = interaction.client
        picked = self.values[0]
        await bot.store.set(
            interaction.guild.id, mins.CHANNEL_KEY, picked.id, by=interaction.user.id
        )
        await render_panel(interaction, self.view)
        await interaction.followup.send(
            CHANNEL_SET.format(where=mins.where_words(interaction.guild, picked.id)),
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )


class LogsButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label=mins.LOGS_LABEL, style=discord.ButtonStyle.secondary, row=0)

    async def callback(self, interaction: discord.Interaction) -> None:
        await send_logs(interaction, "minutes")


class MeetingPick(discord.ui.Select):
    def __init__(self, guild: Any, rows: list[Any]) -> None:
        super().__init__(
            placeholder=PICK_A_MEETING,
            options=[
                discord.SelectOption(label=option_label(guild, row), value=str(row["id"]))
                for row in rows[:SELECT_CAP]
            ],
            min_values=1,
            max_values=1,
            row=1,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await opened(interaction):
            return
        await render_card(interaction, int(self.values[0]), self.view)


class BackButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label=BACK, style=discord.ButtonStyle.secondary, row=1)

    async def callback(self, interaction: discord.Interaction) -> None:
        await back_to_panel(interaction, self.view)


class PostAgainButton(discord.ui.Button):
    def __init__(self, meeting_id: int) -> None:
        super().__init__(label=mins.POST_AGAIN_LABEL, style=discord.ButtonStyle.primary, row=0)
        self.meeting_id = meeting_id

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await opened(interaction):
            return
        bot = interaction.client
        row = await mins.get_meeting(bot.db, interaction.guild.id, self.meeting_id)
        if row is None:
            await render_panel(interaction, self.view)
            return
        found = await mins.post_notes(bot, interaction.guild, row)
        await render_card(interaction, self.meeting_id, self.view, found.message)


class RewriteButton(discord.ui.Button):
    def __init__(self, meeting_id: int) -> None:
        super().__init__(label=REWRITE_LABEL, style=discord.ButtonStyle.secondary, row=0)
        self.meeting_id = meeting_id

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await opened(interaction):
            return
        bot = interaction.client
        row = await mins.get_meeting(bot.db, interaction.guild.id, self.meeting_id)
        if row is None:
            await render_panel(interaction, self.view)
            return
        found = await mins.write_notes(bot, interaction.guild, row)
        await render_card(interaction, self.meeting_id, self.view, found.message)


class EditNotesButton(discord.ui.Button):
    def __init__(self, meeting_id: int) -> None:
        super().__init__(label=EDIT_LABEL, style=discord.ButtonStyle.primary, row=0)
        self.meeting_id = meeting_id

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await still_staff(interaction):
            return
        row = await mins.get_meeting(
            interaction.client.db, interaction.guild.id, self.meeting_id
        )
        if row is None:
            await answer(interaction, mins.NO_SUCH_MEETING.format(meeting_id=self.meeting_id))
            return
        await interaction.response.send_modal(EditNotesModal(self.meeting_id, row, self.view))


class DeleteButton(discord.ui.Button):
    def __init__(self, meeting_id: int) -> None:
        super().__init__(label=mins.DELETE_LABEL, style=discord.ButtonStyle.danger, row=0)
        self.meeting_id = meeting_id

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await opened(interaction):
            return
        bot = interaction.client
        row = await mins.get_meeting(bot.db, interaction.guild.id, self.meeting_id)
        if row is None:
            await render_panel(interaction, self.view)
            return
        await confirm(
            interaction,
            MinutesView(mins.panel_minutes(bot.store, interaction.guild.id)),
            discord.Embed(
                title=f"Meeting #{self.meeting_id}",
                description=meeting_line(interaction.guild, row),
            ),
            confirm_items(
                yes=DELETE_YES,
                no=KEEP_IT,
                on_yes=lambda one, card: delete_and_go_back(one, self.meeting_id, card),
                on_no=back_to_panel,
            ),
            self.view,
            question=DELETE_QUESTION,
        )


async def delete_and_go_back(
    interaction: discord.Interaction, meeting_id: int, previous: Any = None
) -> None:
    if not await opened(interaction):
        return
    bot = interaction.client
    row = await mins.get_meeting(bot.db, interaction.guild.id, meeting_id)
    if row is None:
        await render_panel(interaction, previous)
        return
    found = await mins.delete_meeting(bot, interaction.guild, row, interaction.user)
    await render_panel(interaction, previous)
    await interaction.followup.send(
        found.message, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
    )


class EditNotesModal(AnswersErrors, discord.ui.Modal, title=EDIT_MODAL_TITLE):
    notes = discord.ui.TextInput(
        label=NOTES_FIELD, style=discord.TextStyle.paragraph, max_length=NOTES_BOX_MAX
    )

    def __init__(self, meeting_id: int, row: Any, previous: Any = None) -> None:
        super().__init__()
        self.meeting_id = meeting_id
        self.previous = previous
        self.notes.default = str(mins.row_value(row, "notes", ""))[:NOTES_BOX_MAX] or None

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not await opened(interaction):
            return
        bot = interaction.client
        row = await mins.get_meeting(bot.db, interaction.guild.id, self.meeting_id)
        if row is None:
            await render_panel(interaction, self.previous)
            return
        found = await mins.edit_notes(
            bot, interaction.guild, row, interaction.user, str(self.notes)
        )
        await render_card(interaction, self.meeting_id, self.previous, found.message)


class Minutes(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.last_ok_at: str | None = None
        self.last_error: str | None = None
        sessions_of(bot)

    async def cog_load(self) -> None:
        if not getattr(self.bot.db, "is_connected", False):
            return
        self._sweep_loop.start()

    async def cog_unload(self) -> None:
        self._sweep_loop.cancel()
        for guild_id in list(sessions_of(self.bot)):
            guild = self.bot.get_guild(guild_id)
            if guild is not None:
                await stop_meeting(self.bot, guild, mins.BY_SHUTDOWN)

    def loop_health(self, name: str) -> tuple[str | None, str | None]:
        if name.removeprefix("_").removesuffix("_loop") != LOOP_NAME:
            return (None, None)
        return (self.last_ok_at, self.last_error)

    @tasks.loop(minutes=SWEEP_MINUTES)
    async def _sweep_loop(self) -> None:
        if not getattr(self.bot.db, "is_connected", False):
            return
        for guild in list(getattr(self.bot, "guilds", ()) or ()):
            if bool(getattr(guild, "unavailable", False)):
                continue
            await self.sweep_guild(guild)
        self.last_ok_at = discord.utils.utcnow().isoformat()
        self.last_error = None

    @_sweep_loop.before_loop
    async def _before_sweep(self) -> None:
        await wait_ready(self.bot, self._sweep_broke)

    @_sweep_loop.error
    async def _sweep_broke(self, exc: BaseException) -> None:
        self.last_error = f"{type(exc).__name__}: {exc}"
        log.warning("minutes: the sweep loop stopped — %s", self.last_error, exc_info=exc)
        self._sweep_loop.restart()

    async def sweep_guild(self, guild: Any) -> None:
        """Max hours, the transcript purge, and a row left open by a restart."""
        session = running_in(self.bot, guild.id)
        if session is not None and session.ran_over(mins.max_hours(self.bot.store, guild.id)):
            await stop_meeting(self.bot, guild, mins.BY_MAX_HOURS)
            return
        if session is None:
            stranded = await mins.open_meeting(self.bot.db, guild.id)
            if stranded is not None:
                await mins.end_row(self.bot.db, int(stranded["id"]), mins.BY_SHUTDOWN)
                await finish(self.bot, guild, int(stranded["id"]))
        gone = await mins.purge_old_lines(
            self.bot.db, guild.id, mins.keep_days(self.bot.store, guild.id)
        )
        if gone:
            await log_action(self.bot, guild, mins.PURGED, details={"lines": gone})

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: Any, before: Any, after: Any) -> None:
        guild = getattr(member, "guild", None)
        session = running_in(self.bot, getattr(guild, "id", 0)) if guild is not None else None
        if session is None or session.ending:
            return
        channel = self.bot.get_channel(int(session.channel.id)) or session.channel
        states = getattr(channel, "voice_states", {}) or {}
        me = getattr(getattr(self.bot, "user", None), "id", None)
        if any(int(one) != me for one in states):
            return
        await stop_meeting(self.bot, guild, mins.BY_EMPTY)

    @commands.Cog.listener()
    async def on_message(self, message: Any) -> None:
        guild = getattr(message, "guild", None)
        if guild is None or getattr(getattr(message, "author", None), "bot", False):
            return
        session = running_in(self.bot, guild.id)
        if session is None or session.ending:
            return
        if mins.STOP_PHRASE not in str(getattr(message, "content", "")).lower():
            return
        if int(getattr(message.channel, "id", 0)) != int(session.channel.id):
            return
        await stop_meeting(self.bot, guild, mins.BY_WORDS)

    @app_commands.command(
        name="minutes", description="Have Black Bloc take notes in a voice meeting"
    )
    @app_commands.default_permissions(STAFF_ONLY)
    async def minutes_panel_command(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await answer(interaction, GUILD_ONLY)
            return
        if not await require_staff(interaction):
            return
        if not self.bot.db.is_connected:
            log.warning("minutes: refused the panel — the database is not connected")
            await answer(interaction, DB_UNAVAILABLE)
            return
        embed, view = await build_panel(self.bot, interaction.guild)
        await interaction.response.send_message(
            embed=embed,
            view=view,
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        view.message = await interaction.original_response()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Minutes(bot))


__all__ = [
    "BackButton",
    "ChannelPick",
    "DeleteButton",
    "EditNotesButton",
    "EditNotesModal",
    "LogsButton",
    "MeetingPick",
    "Minutes",
    "MinutesView",
    "PostAgainButton",
    "RewriteButton",
    "StartButton",
    "StopButton",
    "WhereButton",
    "back_to_panel",
    "build_card",
    "build_panel",
    "delete_and_go_back",
    "meeting_line",
    "option_label",
    "render_card",
    "render_panel",
    "running_in",
    "sessions_of",
    "start_meeting",
    "stop_meeting",
]
