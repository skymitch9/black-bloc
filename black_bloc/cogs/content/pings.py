from __future__ import annotations

import logging
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands

from ... import pings
from ...actionlog import send_logs
from ...command_errors import AnswersErrors
from ...panels import (
    Panel,
    answer,
    capped_placeholder,
    db_ready,
    db_up,
    retire,
    still_staff,
)
from ...settings_store import (
    DB_UNAVAILABLE,
    GUILD_ONLY,
    PINGS_CREATORS,
    PINGS_MODES,
    PINGS_ON_UNLINK,
)
from .golive import get_link, latest_session

log = logging.getLogger(__name__)

ROOT = "root"
STREAMERS_VIEW = "streamers"
CARD_VIEW = "card"
SETTINGS_VIEW = "settings"
ROLE_VIEW = "role"

SETUP_PURPOSE = "setup"
GIVE_PURPOSE = "give"

STYLES = {
    "primary": discord.ButtonStyle.primary,
    "secondary": discord.ButtonStyle.secondary,
    "success": discord.ButtonStyle.success,
    "danger": discord.ButtonStyle.danger,
}

PANEL_INTRO = (
    "What Black Bloc pings you about, and how to change it. Nothing here is on until you turn "
    "it on."
)
SITE_BUTTON = "Open on the site"
FOLLOW_PLACEHOLDER = "Follow a streamer…"
UNFOLLOW_PLACEHOLDER = "Stop following…"
STREAMER_PLACEHOLDER = "A streamer…"
GIVE_PLACEHOLDER = "Give somebody a ping role…"
ROLE_PLACEHOLDER = "Use this role instead — leave it empty and one is made"
MODE_PLACEHOLDER = "Mode…"
CREATION_PLACEHOLDER = "Who may start one…"
UNLINK_PLACEHOLDER = "On unlink…"

MODE_LABELS = {
    "off": "off — nobody can opt in and nobody is pinged",
    "on": "on — members choose their pings",
}
CREATION_LABELS = {
    "self": "self — a streamer starts their own",
    "staff": "staff — only an Auntie/Uncle starts one",
    "auto": "auto — one is made the moment Twitch is linked",
}
UNLINK_LABELS = {
    "keep": "keep — the role is left alone",
    "delete": "delete — the role is taken off the server",
}

STREAMERS_TITLE = "Streamer ping roles"
SETTINGS_TITLE = "Ping-role settings"
SETUP_TITLE = "Set up the Events role"
GIVE_TITLE = "A ping role for {who}"
CONFIRM_TITLE = "Are you sure?"
NAMES_BUTTON = "Names…"
DELETE_ON = "Delete the role too: on"
DELETE_OFF = "Delete the role too: off"
SET_IT_UP = "Set it up"
MAKE_THE_ROLE = "Make the role"

ROLE_PICK_INTRO = (
    "Pick a role Black Bloc should use, or leave the picker empty and one is made from the "
    "name in **Settings**."
)
ROLE_PICKED = "Using **{role}**."
ROLE_NOT_PICKED = "Nothing picked, so a fresh role is made."

CARD_HEAD = "**{name}**"
CARD_ROLE = "role — {role}"
CARD_FOLLOWERS = "followers — {count}"
CARD_STARTED = "started — {when} by {who}"
CARD_ROLE_GONE = "the role is gone from the server"
CARD_NOBODY = "somebody"

NO_SUCH_MEMBER = (
    "**{member_id}** is not somebody Black Bloc can see in this server any more, so nothing was "
    "changed. Press **Refresh** and pick again."
)

NAMES_MODAL_TITLE = "Names and numbers"
EVENTS_NAME_LABEL = "What the shared Events role is called"
TEMPLATE_LABEL = "A streamer's role name — {name} is them"
PANEL_MINUTES_LABEL = "Minutes this panel stays live"
NOT_A_NUMBER = (
    "**{given}** is not a whole number, so nothing was changed. {label} takes a number of "
    "minutes — 1 or more."
)

DESCRIPTION_LIMIT = 4000
LABEL_LIMIT = 100

NAMES_MOVE = pings.PanelMove(pings.NAMES, NAMES_BUTTON, row=3)
DELETE_MOVE = pings.PanelMove(pings.DELETE_TOGGLE, DELETE_OFF, row=3)
SETTINGS_BACK_MOVE = pings.PanelMove(pings.BACK, "Back", row=3)


def minutes_for(bot: Any, guild_id: int) -> int:
    return pings.panel_minutes(bot.store, guild_id)


def add_site_button(view: Any, bot: Any, row: int) -> None:
    """No origin, no button — a link that goes nowhere is worse than no link at all."""
    url = pings.site_page_url(getattr(getattr(bot, "settings", None), "origin", ""))
    if not url:
        return
    view.add_item(
        discord.ui.Button(style=discord.ButtonStyle.link, label=SITE_BUTTON, url=url, row=row)
    )


def clamped(lines: list[str]) -> str:
    found: list[str] = []
    spent = 0
    for line in lines:
        if spent + len(line) + 1 > DESCRIPTION_LIMIT:
            break
        found.append(line)
        spent += len(line) + 1
    return "\n".join(found)


async def streams_now(bot: Any, guild: Any, user_id: int) -> bool:
    """A linked channel, or a stream Black Bloc has already seen, counts as streaming here."""
    if await get_link(bot.db, user_id) is not None:
        return True
    return await latest_session(bot.db, guild.id, user_id) is not None


class PingsPanel(Panel):
    def __init__(self, minutes: int) -> None:
        super().__init__(minutes, footer=pings.PANEL_TIMEOUT_FOOTER)
        self.where = ROOT
        self.streamer_id: int | None = None
        self.member_id: int | None = None
        self.purpose = ""
        self.picked_role_id: int | None = None


# --- what renders ------------------------------------------------------------------------------


def panel_lines(
    guild: Any, actor: Any, rows: Any, state: Any, feeds: Any, *, staff: bool
) -> list[str]:
    lines = [PANEL_INTRO]
    lines.extend(pings.notification_lines(guild, actor, rows, feeds))
    if not state.mode_on:
        lines.append(pings.PANEL_OFF_LINE)
    elif not rows:
        lines.append(pings.NO_STREAMERS)
    if state.mode_on and not state.own_role:
        if state.creation == pings.STAFF:
            lines.append(pings.STAFF_ONLY_CREATION)
        elif not state.streams:
            lines.append(pings.NOT_A_STREAMER)
    if staff:
        lines.append(pings.counts_line(rows, guild))
    return lines


async def panel_embed(bot: Any, guild: Any, actor: Any) -> tuple[discord.Embed, Any, Any]:
    staff = bot.store.is_staff(actor)
    rows = await pings.all_fan_roles(bot.db, guild.id)
    feeds = pings.events_feeds(bot, guild.id)
    state = pings.panel_state(
        bot, guild, actor, rows, streams=await streams_now(bot, guild, actor.id)
    )
    embed = discord.Embed(
        title=pings.PANEL_TITLE,
        description=clamped(panel_lines(guild, actor, rows, state, feeds, staff=staff)),
    )
    return (embed, rows, state)


async def build_panel(bot: Any, guild: Any, actor: Any) -> tuple[discord.Embed, PingsPanel]:
    """One command, one panel: the caller's own pings, and the staff half only for staff."""
    staff = bot.store.is_staff(actor)
    embed, rows, state = await panel_embed(bot, guild, actor)
    view = PingsPanel(minutes_for(bot, guild.id))
    live = [row for row in rows if pings.role_of(guild, row["role_id"]) is not None]
    worn = [row for row in live if pings.wears(actor, row["role_id"])]
    spare = [row for row in live if not pings.wears(actor, row["role_id"])]
    if state.mode_on and spare:
        view.add_item(FollowPick(guild, spare, adding=True, row=0))
    if worn:
        view.add_item(FollowPick(guild, worn, adding=False, row=1))
    for move in pings.panel_buttons(state, staff=staff):
        view.add_item(MoveButton(move))
    if staff:
        add_site_button(view, bot, row=3)
    return (embed, view)


async def build_streamers(bot: Any, guild: Any) -> tuple[discord.Embed, PingsPanel]:
    rows = await pings.all_fan_roles(bot.db, guild.id)
    embed = discord.Embed(
        title=STREAMERS_TITLE, description=clamped(pings.streamer_lines(guild, rows))
    )
    view = PingsPanel(minutes_for(bot, guild.id))
    view.where = STREAMERS_VIEW
    if rows:
        view.add_item(StreamerPick(guild, rows, row=0))
    view.add_item(GivePick(row=1))
    view.add_item(MoveButton(pings.REFRESH_MOVE._replace(row=2)))
    view.add_item(MoveButton(pings.BACK_MOVE._replace(row=2)))
    return (embed, view)


def card_lines(guild: Any, row: Any) -> list[str]:
    role = pings.role_of(guild, row["role_id"])
    started_by = row["created_by"]
    who = guild.get_member(int(started_by)) if started_by else None
    return [
        CARD_HEAD.format(name=pings.option_label(guild, row)),
        CARD_ROLE.format(
            role=f"<@&{row['role_id']}>" if role is not None else CARD_ROLE_GONE
        ),
        CARD_FOLLOWERS.format(count=pings.followers_word(guild, row["role_id"])),
        CARD_STARTED.format(
            when=row["created_at"],
            who=pings.display_name(who) if who is not None else (started_by or CARD_NOBODY),
        ),
    ]


async def build_card(
    bot: Any, guild: Any, user_id: Any
) -> tuple[discord.Embed, PingsPanel | None]:
    row = await pings.get_fan_role(bot.db, guild.id, int(user_id))
    if row is None:
        return (None, None)
    embed = discord.Embed(title=STREAMERS_TITLE, description=clamped(card_lines(guild, row)))
    view = PingsPanel(minutes_for(bot, guild.id))
    view.where = CARD_VIEW
    view.streamer_id = int(user_id)
    gone = pings.role_of(guild, row["role_id"]) is None
    for move in pings.card_buttons(role_gone=gone):
        view.add_item(MoveButton(move))
    return (embed, view)


def build_role_pick(
    bot: Any, guild: Any, *, purpose: str, member_id: Any = None, picked: Any = None
) -> tuple[discord.Embed, PingsPanel]:
    """One shape, two doors: /pingroles setup and streamer add both took an optional role."""
    who = guild.get_member(int(member_id)) if member_id else None
    title = SETUP_TITLE if purpose == SETUP_PURPOSE else GIVE_TITLE.format(
        who=pings.display_name(who) if who is not None else member_id
    )
    role = pings.role_of(guild, picked)
    lines = [ROLE_PICK_INTRO]
    lines.append(ROLE_PICKED.format(role=role.name) if role is not None else ROLE_NOT_PICKED)
    embed = discord.Embed(title=title[:LABEL_LIMIT], description=clamped(lines))
    view = PingsPanel(minutes_for(bot, guild.id))
    view.where = ROLE_VIEW
    view.purpose = purpose
    view.member_id = int(member_id) if member_id else None
    view.picked_role_id = int(picked) if picked else None
    view.add_item(RolePick(row=0))
    view.add_item(ConfirmRoleButton(purpose, row=1))
    view.add_item(MoveButton(pings.BACK_MOVE._replace(row=1)))
    return (embed, view)


def settings_lines(bot: Any, guild: Any) -> list[str]:
    store = bot.store
    return [
        f"**mode** — {store.get(guild.id, pings.MODE_KEY)}",
        f"**who may start one** — {store.get(guild.id, pings.CREATION_KEY)}",
        f"**on unlink** — {store.get(guild.id, pings.UNLINK_KEY)}",
        f"**delete the role too** — {'yes' if store.get(guild.id, pings.DELETE_KEY) else 'no'}",
        f"**the Events role is called** — {store.get(guild.id, pings.EVENTS_NAME_KEY)}",
        f"**a streamer's role is called** — {store.get(guild.id, pings.TEMPLATE_KEY)}",
        f"**this panel stays live** — {minutes_for(bot, guild.id)} minute(s)",
    ]


def build_settings(bot: Any, guild: Any) -> tuple[discord.Embed, PingsPanel]:
    store = bot.store
    embed = discord.Embed(title=SETTINGS_TITLE, description=clamped(settings_lines(bot, guild)))
    view = PingsPanel(minutes_for(bot, guild.id))
    view.where = SETTINGS_VIEW
    view.add_item(
        ChoicePick(pings.MODE_KEY, MODE_PLACEHOLDER, PINGS_MODES, MODE_LABELS,
                   store.get(guild.id, pings.MODE_KEY), row=0)
    )
    view.add_item(
        ChoicePick(pings.CREATION_KEY, CREATION_PLACEHOLDER, PINGS_CREATORS, CREATION_LABELS,
                   store.get(guild.id, pings.CREATION_KEY), row=1)
    )
    view.add_item(
        ChoicePick(pings.UNLINK_KEY, UNLINK_PLACEHOLDER, PINGS_ON_UNLINK, UNLINK_LABELS,
                   store.get(guild.id, pings.UNLINK_KEY), row=2)
    )
    view.add_item(MoveButton(NAMES_MOVE))
    deleting = bool(store.get(guild.id, pings.DELETE_KEY))
    view.add_item(MoveButton(DELETE_MOVE._replace(label=DELETE_ON if deleting else DELETE_OFF)))
    add_site_button(view, bot, row=3)
    view.add_item(MoveButton(SETTINGS_BACK_MOVE))
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


async def render_streamers(interaction: discord.Interaction, previous: Any = None) -> None:
    embed, view = await build_streamers(interaction.client, interaction.guild)
    await render(interaction, embed, view, previous)


async def render_card(
    interaction: discord.Interaction, user_id: Any, previous: Any = None
) -> None:
    embed, view = await build_card(interaction.client, interaction.guild, user_id)
    if view is None:
        await render_streamers(interaction, previous)
        await answer(interaction, pings.NO_SUCH_STREAMER.format(given=str(user_id)))
        return
    await render(interaction, embed, view, previous)


async def render_role_pick(
    interaction: discord.Interaction,
    *,
    purpose: str,
    member_id: Any = None,
    picked: Any = None,
    previous: Any = None,
) -> None:
    embed, view = build_role_pick(
        interaction.client, interaction.guild, purpose=purpose, member_id=member_id, picked=picked
    )
    await render(interaction, embed, view, previous)


async def render_settings(interaction: discord.Interaction, previous: Any = None) -> None:
    embed, view = build_settings(interaction.client, interaction.guild)
    await render(interaction, embed, view, previous)


async def back_to_panel(interaction: discord.Interaction, previous: Any = None) -> None:
    await interaction.response.defer()
    if not await db_ready(interaction):
        return
    await render_panel(interaction, previous)


async def open_streamers(interaction: discord.Interaction, previous: Any = None) -> None:
    if not await still_staff(interaction):
        return
    await interaction.response.defer()
    if not await db_ready(interaction):
        return
    await render_streamers(interaction, previous)


async def open_card(
    interaction: discord.Interaction, user_id: Any, previous: Any = None
) -> None:
    if not await still_staff(interaction):
        return
    await interaction.response.defer()
    if not await db_ready(interaction):
        return
    await render_card(interaction, user_id, previous)


async def open_settings(interaction: discord.Interaction, previous: Any = None) -> None:
    if not await still_staff(interaction):
        return
    await interaction.response.defer()
    if not await db_ready(interaction):
        return
    await render_settings(interaction, previous)


async def open_role_pick(
    interaction: discord.Interaction,
    purpose: str,
    member_id: Any = None,
    previous: Any = None,
    picked: Any = None,
) -> None:
    if not await still_staff(interaction):
        return
    await interaction.response.defer()
    if not await db_ready(interaction):
        return
    await render_role_pick(
        interaction, purpose=purpose, member_id=member_id, picked=picked, previous=previous
    )


async def open_confirm(
    interaction: discord.Interaction, move: Any, previous: Any = None
) -> None:
    await interaction.response.defer()
    if not await db_ready(interaction):
        return
    bot = interaction.client
    embed, _rows, _state = await panel_embed(bot, interaction.guild, interaction.user)
    embed.add_field(name=CONFIRM_TITLE, value=move.question, inline=False)
    view = PingsPanel(minutes_for(bot, interaction.guild.id))
    view.add_item(OwnDropYesButton(move))
    view.add_item(KeepItButton())
    await render(interaction, embed, view, previous)


async def open_card_confirm(
    interaction: discord.Interaction, user_id: Any, previous: Any = None
) -> None:
    if not await still_staff(interaction):
        return
    await interaction.response.defer()
    if not await db_ready(interaction):
        return
    bot = interaction.client
    guild = interaction.guild
    row = await pings.get_fan_role(bot.db, guild.id, int(user_id))
    if row is None:
        await render_streamers(interaction, previous)
        await answer(interaction, pings.NO_SUCH_STREAMER.format(given=str(user_id)))
        return
    name = pings.option_label(guild, row)
    embed = discord.Embed(title=STREAMERS_TITLE, description=clamped(card_lines(guild, row)))
    embed.add_field(
        name=CONFIRM_TITLE, value=pings.CARD_REMOVE_QUESTION.format(name=name), inline=False
    )
    view = PingsPanel(minutes_for(bot, guild.id))
    view.where = CARD_VIEW
    view.streamer_id = int(user_id)
    view.add_item(CardRemoveYesButton())
    view.add_item(KeepItButton())
    await render(interaction, embed, view, previous)


async def refresh_where(interaction: discord.Interaction, view: Any) -> None:
    if view.where == STREAMERS_VIEW:
        await open_streamers(interaction, view)
        return
    if view.where == CARD_VIEW:
        await open_card(interaction, view.streamer_id, view)
        return
    if view.where == SETTINGS_VIEW:
        await open_settings(interaction, view)
        return
    await back_to_panel(interaction, view)


async def back_from(interaction: discord.Interaction, view: Any) -> None:
    if view.where == CARD_VIEW or (view.where == ROLE_VIEW and view.purpose == GIVE_PURPOSE):
        await open_streamers(interaction, view)
        return
    await back_to_panel(interaction, view)


# --- the moves, one function each ----------------------------------------------------------------


async def run_follow(
    interaction: discord.Interaction, user_id: Any, *, add: bool, previous: Any = None
) -> None:
    await interaction.response.defer()
    if not await db_ready(interaction):
        return
    bot = interaction.client
    guild = interaction.guild
    rows = await pings.all_fan_roles(bot.db, guild.id)
    row = pings.row_for(rows, user_id)
    if row is None:
        said = pings.NO_SUCH_STREAMER.format(given=str(user_id))
    elif add and not pings.is_on(bot, guild.id):
        said = pings.OFF
    else:
        said = await pings.follow_streamer(bot, guild, interaction.user, row, add=add)
    await render_panel(interaction, previous)
    await answer(interaction, said)


async def run_events(
    interaction: discord.Interaction, *, add: bool, feed: str, previous: Any = None
) -> None:
    await interaction.response.defer()
    if not await db_ready(interaction):
        return
    bot = interaction.client
    guild = interaction.guild
    if not pings.is_on(bot, guild.id):
        said = pings.OFF
    else:
        said = await pings.set_event_pings(
            bot, guild, interaction.user, add=add, feed=feed or pings.BOTH_FEEDS
        )
    await render_panel(interaction, previous)
    await answer(interaction, said)


async def run_own(
    interaction: discord.Interaction, *, add: bool, previous: Any = None
) -> None:
    await interaction.response.defer()
    if not await db_ready(interaction):
        return
    bot = interaction.client
    guild = interaction.guild
    if add:
        outcome = await pings.start_own_fan_role(
            bot, guild, interaction.user, streams=await streams_now(bot, guild, interaction.user.id)
        )
    else:
        outcome = await pings.stop_own_fan_role(bot, guild, interaction.user)
    await render_panel(interaction, previous)
    await answer(interaction, outcome.message)


async def run_setup(
    interaction: discord.Interaction, role_id: Any = None, previous: Any = None
) -> None:
    if not await still_staff(interaction):
        return
    await interaction.response.defer()
    if not await db_ready(interaction):
        return
    guild = interaction.guild
    outcome = await pings.setup_events_role(
        interaction.client,
        guild,
        by=interaction.user.id,
        role=pings.role_of(guild, role_id),
    )
    await render_panel(interaction, previous)
    await answer(interaction, outcome.message)


async def run_give(
    interaction: discord.Interaction,
    member_id: Any,
    role_id: Any = None,
    previous: Any = None,
) -> None:
    if not await still_staff(interaction):
        return
    await interaction.response.defer()
    if not await db_ready(interaction):
        return
    guild = interaction.guild
    member = guild.get_member(int(member_id)) if member_id else None
    if member is None:
        await render_streamers(interaction, previous)
        await answer(interaction, NO_SUCH_MEMBER.format(member_id=member_id))
        return
    outcome = await pings.ensure_fan_role(
        interaction.client,
        guild,
        member,
        by=interaction.user.id,
        existing_role=pings.role_of(guild, role_id),
        staff=True,
    )
    await render_streamers(interaction, previous)
    await answer(interaction, outcome.message)


async def run_remove(
    interaction: discord.Interaction, user_id: Any, previous: Any = None
) -> None:
    if not await still_staff(interaction):
        return
    await interaction.response.defer()
    if not await db_ready(interaction):
        return
    outcome = await pings.remove_fan_role(
        interaction.client, interaction.guild, int(user_id), by=interaction.user.id
    )
    await render_streamers(interaction, previous)
    await answer(interaction, outcome.message)


async def run_remake(
    interaction: discord.Interaction, user_id: Any, previous: Any = None
) -> None:
    if not await still_staff(interaction):
        return
    await interaction.response.defer()
    if not await db_ready(interaction):
        return
    guild = interaction.guild
    member = guild.get_member(int(user_id)) if user_id else None
    if member is None:
        await render_streamers(interaction, previous)
        await answer(interaction, NO_SUCH_MEMBER.format(member_id=user_id))
        return
    outcome = await pings.ensure_fan_role(
        interaction.client, guild, member, by=interaction.user.id, staff=True
    )
    await render_card(interaction, user_id, previous)
    await answer(interaction, outcome.message)


async def run_settings(
    interaction: discord.Interaction,
    changes: dict[str, Any],
    previous: Any = None,
    *,
    echo: str = "",
) -> None:
    if not await still_staff(interaction):
        return
    await interaction.response.defer()
    if not await db_ready(interaction):
        return
    said = await pings.save_settings(
        interaction.client, interaction.guild, interaction.user, changes
    )
    await render_settings(interaction, previous)
    await answer(interaction, said + echo)


# --- the controls ------------------------------------------------------------------------------


class MoveButton(discord.ui.Button):
    def __init__(self, move: Any) -> None:
        super().__init__(label=move.label, style=STYLES[move.style], row=move.row)
        self.move = move

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        action = self.move.action
        if action == pings.REFRESH:
            await refresh_where(interaction, view)
            return
        if action == pings.BACK:
            await back_from(interaction, view)
            return
        if action == pings.LOGS:
            await send_logs(interaction, "pings")
            return
        if action == pings.STREAMERS:
            await open_streamers(interaction, view)
            return
        if action == pings.SETUP:
            await open_role_pick(interaction, SETUP_PURPOSE, None, view)
            return
        if action == pings.SETTINGS:
            await open_settings(interaction, view)
            return
        if action in (pings.EVENTS_ADD, pings.EVENTS_DROP):
            await run_events(
                interaction, add=action == pings.EVENTS_ADD, feed=self.move.feed, previous=view
            )
            return
        if action == pings.OWN_ADD:
            await run_own(interaction, add=True, previous=view)
            return
        if action == pings.OWN_DROP:
            await open_confirm(interaction, self.move, view)
            return
        if action == pings.CARD_REMOVE:
            await open_card_confirm(interaction, view.streamer_id, view)
            return
        if action == pings.CARD_REMAKE:
            await run_remake(interaction, view.streamer_id, view)
            return
        if action == pings.DELETE_TOGGLE:
            store = interaction.client.store
            await run_settings(
                interaction,
                {pings.DELETE_KEY: not store.get(interaction.guild.id, pings.DELETE_KEY)},
                view,
            )
            return
        if not await still_staff(interaction):
            return
        if not await db_up(interaction):
            return
        await interaction.response.send_modal(
            NamesModal(interaction.client, interaction.guild.id, view)
        )


class OwnDropYesButton(discord.ui.Button):
    def __init__(self, move: Any) -> None:
        super().__init__(label=move.yes, style=discord.ButtonStyle.danger, row=0)

    async def callback(self, interaction: discord.Interaction) -> None:
        await run_own(interaction, add=False, previous=self.view)


class CardRemoveYesButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label=pings.CARD_REMOVE_YES, style=discord.ButtonStyle.danger, row=0)

    async def callback(self, interaction: discord.Interaction) -> None:
        await run_remove(interaction, self.view.streamer_id, self.view)


class KeepItButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label=pings.KEEP_IT, style=discord.ButtonStyle.secondary, row=0)

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        if view.where == CARD_VIEW:
            await open_card(interaction, view.streamer_id, view)
            return
        await back_to_panel(interaction, view)


class FollowPick(discord.ui.Select):
    """The member's two selects; the cap points at the panels that page, not at the site."""

    def __init__(self, guild: Any, rows: Any, *, adding: bool, row: int) -> None:
        found = list(rows)
        shown = found[: pings.SELECT_CAP]
        self.adding = adding
        super().__init__(
            placeholder=capped_placeholder(
                len(shown),
                len(found),
                pick=FOLLOW_PLACEHOLDER if adding else UNFOLLOW_PLACEHOLDER,
                capped=pings.CAPPED_FOLLOW,
            ),
            options=[
                discord.SelectOption(
                    label=pings.option_label(guild, one)[:LABEL_LIMIT],
                    value=str(one["user_id"]),
                )
                for one in shown
            ],
            min_values=1,
            max_values=1,
            row=row,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await run_follow(
            interaction, int(self.values[0]), add=self.adding, previous=self.view
        )


class StreamerPick(discord.ui.Select):
    def __init__(self, guild: Any, rows: Any, row: int) -> None:
        found = list(rows)
        shown = found[: pings.SELECT_CAP]
        super().__init__(
            placeholder=capped_placeholder(len(shown), len(found), pick=STREAMER_PLACEHOLDER),
            options=[
                discord.SelectOption(
                    label=pings.option_label(guild, one)[:LABEL_LIMIT],
                    value=str(one["user_id"]),
                )
                for one in shown
            ],
            min_values=1,
            max_values=1,
            row=row,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await open_card(interaction, int(self.values[0]), self.view)


class GivePick(discord.ui.UserSelect):
    def __init__(self, row: int) -> None:
        super().__init__(placeholder=GIVE_PLACEHOLDER, min_values=1, max_values=1, row=row)

    async def callback(self, interaction: discord.Interaction) -> None:
        await open_role_pick(
            interaction, GIVE_PURPOSE, int(self.values[0].id), self.view
        )


class RolePick(discord.ui.RoleSelect):
    """min_values=0 so an empty submit means 'make one'; the confirm button does it too."""

    def __init__(self, row: int) -> None:
        super().__init__(placeholder=ROLE_PLACEHOLDER, min_values=0, max_values=1, row=row)

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        picked = int(self.values[0].id) if self.values else None
        await open_role_pick(interaction, view.purpose, view.member_id, view, picked)


class ConfirmRoleButton(discord.ui.Button):
    def __init__(self, purpose: str, row: int) -> None:
        label = SET_IT_UP if purpose == SETUP_PURPOSE else MAKE_THE_ROLE
        super().__init__(label=label, style=discord.ButtonStyle.primary, row=row)
        self.purpose = purpose

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        if self.purpose == SETUP_PURPOSE:
            await run_setup(interaction, view.picked_role_id, view)
            return
        await run_give(interaction, view.member_id, view.picked_role_id, view)


class ChoicePick(discord.ui.Select):
    def __init__(
        self, key: str, placeholder: str, choices: Any, labels: dict[str, str],
        current: Any, row: int,
    ) -> None:
        self.key = key
        super().__init__(
            placeholder=placeholder,
            options=[
                discord.SelectOption(
                    label=labels[name][:LABEL_LIMIT], value=name, default=(name == current)
                )
                for name in choices
            ],
            min_values=1,
            max_values=1,
            row=row,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await run_settings(interaction, {self.key: self.values[0]}, self.view)


class NamesModal(AnswersErrors, discord.ui.Modal):
    events_name = discord.ui.TextInput(
        label=EVENTS_NAME_LABEL, max_length=pings.ROLE_NAME_LIMIT
    )
    template = discord.ui.TextInput(label=TEMPLATE_LABEL, max_length=pings.ROLE_NAME_LIMIT)
    stays = discord.ui.TextInput(label=PANEL_MINUTES_LABEL, max_length=5)

    def __init__(self, bot: Any, guild_id: int, previous: Any = None) -> None:
        super().__init__(title=NAMES_MODAL_TITLE[:45])
        self.previous = previous
        store = bot.store
        self.events_name.default = str(store.get(guild_id, pings.EVENTS_NAME_KEY))
        self.template.default = str(store.get(guild_id, pings.TEMPLATE_KEY))
        self.stays.default = str(minutes_for(bot, guild_id))

    async def on_submit(self, interaction: discord.Interaction) -> None:
        """The template is echoed as it will RENDER, so a broken one cannot look saved."""
        given = str(self.stays).strip()
        if not given.isdigit():
            await answer(
                interaction,
                NOT_A_NUMBER.format(given=given[:40] or "nothing", label=PANEL_MINUTES_LABEL),
            )
            return
        template = str(self.template)
        example, broken = pings.template_preview(
            template, pings.display_name(interaction.user)
        )
        said = (
            pings.TEMPLATE_BROKEN.format(given=template[:60], example=example)
            if broken
            else pings.TEMPLATE_OK.format(example=example)
        )
        await run_settings(
            interaction,
            {
                pings.EVENTS_NAME_KEY: str(self.events_name),
                pings.TEMPLATE_KEY: template,
                pings.PANEL_MINUTES_KEY: int(given),
            },
            self.previous,
            echo="\n" + said,
        )


class Pings(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="pings", description="Choose which pings you get")
    async def pings_panel(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await answer(interaction, GUILD_ONLY)
            return
        if not self.bot.db.is_connected:
            log.warning("pings: refused the panel — the database is not connected")
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


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Pings(bot))


__all__ = [
    "CARD_ROLE_GONE",
    "DELETE_OFF",
    "DELETE_ON",
    "FOLLOW_PLACEHOLDER",
    "GIVE_PLACEHOLDER",
    "MAKE_THE_ROLE",
    "NAMES_BUTTON",
    "NOT_A_NUMBER",
    "NO_SUCH_MEMBER",
    "PANEL_INTRO",
    "ROLE_PLACEHOLDER",
    "SET_IT_UP",
    "SITE_BUTTON",
    "STREAMER_PLACEHOLDER",
    "UNFOLLOW_PLACEHOLDER",
    "CardRemoveYesButton",
    "ChoicePick",
    "ConfirmRoleButton",
    "FollowPick",
    "GivePick",
    "KeepItButton",
    "MoveButton",
    "NamesModal",
    "Pings",
    "PingsPanel",
    "RolePick",
    "StreamerPick",
    "build_card",
    "build_panel",
    "build_role_pick",
    "build_settings",
    "build_streamers",
    "card_lines",
    "run_events",
    "run_follow",
    "run_give",
    "run_own",
    "run_remake",
    "run_remove",
    "run_settings",
    "run_setup",
    "streams_now",
]
