from __future__ import annotations

import logging
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands, tasks

from ... import pings
from ... import pings_onboarding as onboarding
from ...actionlog import send_logs
from ...command_errors import AnswersErrors
from ...golive import now_iso
from ...loops import wait_ready
from ...panels import (
    SELECT_OPTION_LIMIT,
    Panel,
    answer,
    capped_placeholder,
    clamped,
    confirm,
    confirm_items,
    db_up,
    opened,
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
ONBOARDING_VIEW = "onboarding"

SETUP_PURPOSE = "setup"
RAID_PURPOSE = "raid"
GIVE_PURPOSE = "give"

SWEEP_MINUTES = 5

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
CREATION_PLACEHOLDER = "When a streamer's role is made…"
UNLINK_PLACEHOLDER = "On unlink…"

MODE_LABELS = {
    "off": "off — nobody can opt in and nobody is pinged",
    "on": "on — members choose their pings",
}
CREATION_LABELS = {
    "self": "self — a streamer starts their own",
    "staff": "staff — only an Auntie/Uncle starts one",
    "auto": "auto — one is made the moment Twitch is linked",
    "follow": "follow — the first person to follow them makes it",
}
UNLINK_LABELS = {
    "keep": "keep — the role is left alone",
    "delete": "delete — the role is taken off the server",
}

STREAMERS_TITLE = "The streamer list"
SETTINGS_TITLE = "Ping-role settings"
SETUP_TITLE = "Set up the Events role"
RAID_TITLE = "Set up the raid-train role"
ONBOARDING_TITLE = "Discord onboarding"
GIVE_TITLE = "A ping role for {who}"
NAMES_BUTTON = "Names…"
NUMBERS_BUTTON = "Numbers…"
DELETE_ON = "Delete the role too: on"
DELETE_OFF = "Delete the role too: off"
SET_IT_UP = "Set it up"
MAKE_THE_ROLE = "Make the role"

ONBOARDING_STOPPED = (
    "Done — Black Bloc will not write to this server's onboarding again. The prompts stay "
    "exactly as they are now; **Manage onboarding again** puts it back."
)
ONBOARDING_STARTED = (
    "Done — Black Bloc will keep its onboarding prompts in step again. Press **Sync now** to "
    "write them straight away, or wait five minutes."
)

ROLE_PICK_INTRO = (
    "Pick a role Black Bloc should use, or leave the picker empty and one is made from the "
    "name in **Settings**."
)
ROLE_PICKED = "Using **{role}**."
ROLE_NOT_PICKED = "Nothing picked, so a fresh role is made."

CARD_HEAD = "**{name}**"
CARD_LISTED = "on the list — {state} · last live {when} · seen live {count} time(s)"
CARD_ROLE = "role — {role}"
CARD_NO_ROLE = "role — none yet; the first person to follow them makes it"
CARD_FOLLOWERS = "followers — {count}"
CARD_STARTED = "started — {when} by {who}"
CARD_ROLE_GONE = "the role is gone from the server"
CARD_NOBODY = "somebody"
CARD_NEVER_LIVE = "never — Black Bloc has not seen them stream"

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

NAMES_MOVE = pings.PanelMove(pings.NAMES, NAMES_BUTTON, row=3)
NUMBERS_MOVE = pings.PanelMove(pings.NUMBERS, NUMBERS_BUTTON, row=3)
DELETE_MOVE = pings.PanelMove(pings.DELETE_TOGGLE, DELETE_OFF, row=3)
SETTINGS_BACK_MOVE = pings.PanelMove(pings.BACK, "Back", row=4)

NUMBERS_MODAL_TITLE = "Days and ceilings"
STALE_DAYS_LABEL = "Days on the list without a go-live"
EMPTY_ROLE_DAYS_LABEL = "Days an unworn ping role survives"
CAP_LABEL = "Streamers on the onboarding prompt"


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
    guild: Any, actor: Any, rows: Any, state: Any, feeds: Any, *, staff: bool, streamers: Any
) -> list[str]:
    lines = [PANEL_INTRO]
    lines.extend(pings.notification_lines(guild, actor, rows, feeds))
    mine = pings.listed_line(state.listed)
    if mine:
        lines.append(mine)
    if not state.mode_on:
        lines.append(pings.PANEL_OFF_LINE)
    elif not streamers:
        lines.append(pings.NO_STREAMERS)
    if state.mode_on and not state.own_role and state.creation == pings.STAFF:
        lines.append(pings.STAFF_ONLY_CREATION)
    if staff:
        lines.append(pings.counts_line(streamers, rows, guild))
    return lines


async def panel_embed(bot: Any, guild: Any, actor: Any) -> tuple[discord.Embed, Any, Any]:
    staff = bot.store.is_staff(actor)
    rows = await pings.all_fan_roles(bot.db, guild.id)
    streamers = await pings.all_streamers(bot.db, guild.id)
    feeds = pings.all_feeds(bot, guild.id)
    state = pings.panel_state(
        bot,
        guild,
        actor,
        rows,
        streams=await streams_now(bot, guild, actor.id),
        streamers=streamers,
        mine=pings.row_for(streamers, actor.id),
    )
    embed = discord.Embed(
        title=pings.PANEL_TITLE,
        description=clamped(
            panel_lines(guild, actor, rows, state, feeds, staff=staff, streamers=streamers)
        ),
    )
    return (embed, (rows, streamers), state)


async def build_panel(bot: Any, guild: Any, actor: Any) -> tuple[discord.Embed, PingsPanel]:
    """One command, one panel: the caller's own pings, and the staff half only for staff."""
    staff = bot.store.is_staff(actor)
    embed, (rows, streamers), state = await panel_embed(bot, guild, actor)
    view = PingsPanel(minutes_for(bot, guild.id))
    spare = pings.followable(guild, actor, streamers, rows)
    worn = pings.following(guild, actor, rows)
    if state.mode_on and spare:
        view.add_item(FollowPick(guild, spare, adding=True, row=0, staff=staff))
    if worn:
        view.add_item(FollowPick(guild, worn, adding=False, row=1, staff=staff))
    moves = pings.panel_buttons(state, staff=staff)
    for move in moves:
        view.add_item(MoveButton(move))
    if staff:
        add_site_button(view, bot, row=pings.site_row(moves))
    return (embed, view)


async def build_streamers(bot: Any, guild: Any) -> tuple[discord.Embed, PingsPanel]:
    """The staff list is the STREAMER list — Black Bloc puts people on it, nobody adds one."""
    rows = await pings.all_fan_roles(bot.db, guild.id)
    streamers = await pings.all_streamers(bot.db, guild.id)
    embed = discord.Embed(
        title=STREAMERS_TITLE, description=clamped(pings.streamer_lines(guild, streamers, rows))
    )
    view = PingsPanel(minutes_for(bot, guild.id))
    view.where = STREAMERS_VIEW
    if streamers:
        view.add_item(StreamerPick(guild, streamers, row=0))
    view.add_item(GivePick(row=1))
    view.add_item(MoveButton(pings.REFRESH_MOVE._replace(row=2)))
    view.add_item(MoveButton(pings.BACK_MOVE._replace(row=2)))
    return (embed, view)


async def build_onboarding(bot: Any, guild: Any) -> tuple[discord.Embed, PingsPanel]:
    """C5's staff sub-panel: what the prompts hold, when they were last written, and the way out."""
    managed = onboarding.managed(bot, guild.id)
    result = await onboarding_preview(bot, guild)
    lines = onboarding.card_lines(
        guild, result, managed_now=managed, last=await onboarding.last_sync(bot, guild.id)
    )
    embed = discord.Embed(title=ONBOARDING_TITLE, description=clamped(lines))
    view = PingsPanel(minutes_for(bot, guild.id))
    view.where = ONBOARDING_VIEW
    for move in pings.onboarding_buttons(
        managed=managed, community=onboarding.is_community(guild)
    ):
        view.add_item(MoveButton(move))
    return (embed, view)


async def onboarding_preview(bot: Any, guild: Any) -> Any:
    """What the prompts WOULD hold — reading the tables, never writing and never asking Discord."""
    wanted, more = await onboarding.wanted_prompts(bot, guild)
    return onboarding.Result(
        True, onboarding.UNCHANGED_REASON, "", wanted=list(wanted), more=more
    )


def card_lines(guild: Any, listing: Any, row: Any = None) -> list[str]:
    """One card for one streamer: the listing, the role if there is one, and who started it."""
    lines = [
        CARD_HEAD.format(name=pings.streamer_name(guild, listing)),
        CARD_LISTED.format(
            state=pings.LISTED_WORD if listing["listed"] else pings.HIDDEN_WORD,
            when=listing["last_live_at"],
            count=listing["live_count"],
        ),
    ]
    if row is None:
        lines.append(CARD_NO_ROLE)
        return lines
    role = pings.role_of(guild, row["role_id"])
    started_by = row["created_by"]
    who = guild.get_member(int(started_by)) if started_by else None
    lines.append(
        CARD_ROLE.format(role=f"<@&{row['role_id']}>" if role is not None else CARD_ROLE_GONE)
    )
    lines.append(CARD_FOLLOWERS.format(count=pings.followers_word(guild, row["role_id"])))
    lines.append(
        CARD_STARTED.format(
            when=row["created_at"],
            who=pings.display_name(who) if who is not None else (started_by or CARD_NOBODY),
        )
    )
    return lines


async def build_card(
    bot: Any, guild: Any, user_id: Any
) -> tuple[discord.Embed, PingsPanel | None]:
    listing = await pings.get_streamer(bot.db, guild.id, int(user_id))
    row = await pings.get_fan_role(bot.db, guild.id, int(user_id))
    if listing is None and row is None:
        return (None, None)
    if listing is None:
        listing = {
            "user_id": int(user_id),
            "listed": 0,
            "last_live_at": CARD_NEVER_LIVE,
            "live_count": 0,
            "login": None,
        }
    embed = discord.Embed(
        title=STREAMERS_TITLE, description=clamped(card_lines(guild, listing, row))
    )
    view = PingsPanel(minutes_for(bot, guild.id))
    view.where = CARD_VIEW
    view.streamer_id = int(user_id)
    gone = row is None or pings.role_of(guild, row["role_id"]) is None
    for move in pings.card_buttons(role_gone=gone, listed=pings.listed_state(listing)):
        view.add_item(MoveButton(move))
    return (embed, view)


def build_role_pick(
    bot: Any, guild: Any, *, purpose: str, member_id: Any = None, picked: Any = None
) -> tuple[discord.Embed, PingsPanel]:
    """One shape, three doors: the Events role, the raid-train role and a streamer's own."""
    who = guild.get_member(int(member_id)) if member_id else None
    if purpose == SETUP_PURPOSE:
        title = SETUP_TITLE
    elif purpose == RAID_PURPOSE:
        title = RAID_TITLE
    else:
        title = GIVE_TITLE.format(
            who=pings.display_name(who) if who is not None else member_id
        )
    role = pings.role_of(guild, picked)
    lines = [ROLE_PICK_INTRO]
    lines.append(ROLE_PICKED.format(role=role.name) if role is not None else ROLE_NOT_PICKED)
    embed = discord.Embed(title=title[:SELECT_OPTION_LIMIT], description=clamped(lines))
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
        f"**when a streamer's role is made** — {store.get(guild.id, pings.CREATION_KEY)}",
        f"**on unlink** — {store.get(guild.id, pings.UNLINK_KEY)}",
        f"**delete the role too** — {'yes' if store.get(guild.id, pings.DELETE_KEY) else 'no'}",
        f"**the Events role is called** — {store.get(guild.id, pings.EVENTS_NAME_KEY)}",
        f"**a streamer's role is called** — {store.get(guild.id, pings.TEMPLATE_KEY)}",
        f"**days on the list without a go-live** — {store.get(guild.id, pings.STALE_DAYS_KEY)}",
        "**days an unworn ping role survives** — "
        f"{store.get(guild.id, pings.EMPTY_ROLE_DAYS_KEY)}",
        "**streamers on the onboarding prompt** — "
        f"{store.get(guild.id, pings.ONBOARDING_CAP_KEY)}",
        "**the onboarding prompt is called** — "
        f"{store.get(guild.id, pings.ONBOARDING_TITLE_KEY)}",
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
    view.add_item(MoveButton(NUMBERS_MOVE))
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


async def render_onboarding(interaction: discord.Interaction, previous: Any = None) -> None:
    embed, view = await build_onboarding(interaction.client, interaction.guild)
    await render(interaction, embed, view, previous)


async def open_onboarding(interaction: discord.Interaction, previous: Any = None) -> None:
    if not await still_staff(interaction):
        return
    if not await opened(interaction, staff=False):
        return
    await render_onboarding(interaction, previous)


async def back_to_panel(interaction: discord.Interaction, previous: Any = None) -> None:
    if not await opened(interaction, staff=False):
        return
    await render_panel(interaction, previous)


async def open_streamers(interaction: discord.Interaction, previous: Any = None) -> None:
    if not await still_staff(interaction):
        return
    if not await opened(interaction, staff=False):
        return
    await render_streamers(interaction, previous)


async def open_card(
    interaction: discord.Interaction, user_id: Any, previous: Any = None
) -> None:
    if not await still_staff(interaction):
        return
    if not await opened(interaction, staff=False):
        return
    await render_card(interaction, user_id, previous)


async def open_settings(interaction: discord.Interaction, previous: Any = None) -> None:
    if not await still_staff(interaction):
        return
    if not await opened(interaction, staff=False):
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
    if not await opened(interaction, staff=False):
        return
    await render_role_pick(
        interaction, purpose=purpose, member_id=member_id, picked=picked, previous=previous
    )


async def open_confirm(
    interaction: discord.Interaction, move: Any, previous: Any = None
) -> None:
    if not await opened(interaction, staff=False):
        return
    bot = interaction.client
    embed, _found, _state = await panel_embed(bot, interaction.guild, interaction.user)
    if move.action == pings.LIST_OUT:
        def on_yes(one: Any, card: Any) -> Any:
            return run_listing(one, listed=False, previous=card)
    else:
        def on_yes(one: Any, card: Any) -> Any:
            return run_own(one, add=False, previous=card)

    await confirm(
        interaction,
        PingsPanel(minutes_for(bot, interaction.guild.id)),
        embed,
        confirm_items(yes=move.yes, no=pings.KEEP_IT, on_yes=on_yes, on_no=back_to_panel),
        previous,
        question=move.question,
    )


async def open_card_confirm(
    interaction: discord.Interaction, user_id: Any, previous: Any = None
) -> None:
    if not await still_staff(interaction):
        return
    if not await opened(interaction, staff=False):
        return
    bot = interaction.client
    guild = interaction.guild
    row = await pings.get_fan_role(bot.db, guild.id, int(user_id))
    if row is None:
        await render_streamers(interaction, previous)
        await answer(interaction, pings.NO_SUCH_STREAMER.format(given=str(user_id)))
        return
    name = pings.option_label(guild, row)
    embed, _view = await build_card(bot, guild, user_id)
    view = PingsPanel(minutes_for(bot, guild.id))
    view.where = CARD_VIEW
    view.streamer_id = int(user_id)
    await confirm(
        interaction,
        view,
        embed,
        confirm_items(
            yes=pings.CARD_REMOVE_YES,
            no=pings.KEEP_IT,
            on_yes=lambda one, card: run_remove(one, card.streamer_id, card),
            on_no=lambda one, card: open_card(one, card.streamer_id, card),
        ),
        previous,
        question=pings.CARD_REMOVE_QUESTION.format(name=name),
    )


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
    if view.where == ONBOARDING_VIEW:
        await open_onboarding(interaction, view)
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
    """Following goes through the LIST and may make the role; stopping goes through the role."""
    if not await opened(interaction, staff=False):
        return
    bot = interaction.client
    guild = interaction.guild
    if add:
        said = await pings.follow_from_list(bot, guild, interaction.user, int(user_id))
    else:
        row = pings.row_for(await pings.all_fan_roles(bot.db, guild.id), user_id)
        said = (
            pings.NO_SUCH_STREAMER.format(given=str(user_id))
            if row is None
            else await pings.follow_streamer(bot, guild, interaction.user, row, add=False)
        )
    await render_panel(interaction, previous)
    await answer(interaction, said)


async def run_listing(
    interaction: discord.Interaction, *, listed: bool, previous: Any = None
) -> None:
    """The member's own streamer-list switch; taking yourself off never needs the mode on."""
    if not await opened(interaction, staff=False):
        return
    bot = interaction.client
    guild = interaction.guild
    who = interaction.user
    if listed and not pings.is_on(bot, guild.id):
        outcome = pings.Outcome(False, pings.OFF)
    elif listed:
        outcome = await pings.restore_streamer(bot, guild, who.id, by=who.id)
    else:
        outcome = await pings.hide_streamer(bot, guild, who.id, by=who.id)
    await render_panel(interaction, previous)
    await answer(interaction, outcome.message)


async def run_card_listing(
    interaction: discord.Interaction, user_id: Any, *, listed: bool, previous: Any = None
) -> None:
    """Staff always get the final say: the hide a member made is one a staff press reverses."""
    if not await still_staff(interaction):
        return
    if not await opened(interaction, staff=False):
        return
    bot = interaction.client
    guild = interaction.guild
    move = pings.restore_streamer if listed else pings.hide_streamer
    outcome = await move(bot, guild, int(user_id), by=interaction.user.id)
    await render_card(interaction, user_id, previous)
    await answer(interaction, outcome.message)


async def run_onboarding_sync(
    interaction: discord.Interaction, previous: Any = None
) -> None:
    if not await still_staff(interaction):
        return
    if not await opened(interaction, staff=False):
        return
    result = await onboarding.reconcile(
        interaction.client, interaction.guild, by=interaction.user.id, asked=True
    )
    await render_onboarding(interaction, previous)
    await answer(interaction, result.message)


async def run_onboarding_managed(
    interaction: discord.Interaction, *, managed: bool, previous: Any = None
) -> None:
    if not await still_staff(interaction):
        return
    if not await opened(interaction, staff=False):
        return
    await pings.save_settings(
        interaction.client,
        interaction.guild,
        interaction.user,
        {pings.ONBOARDING_MANAGED_KEY: managed},
    )
    await render_onboarding(interaction, previous)
    await answer(interaction, ONBOARDING_STARTED if managed else ONBOARDING_STOPPED)


async def run_events(
    interaction: discord.Interaction, *, add: bool, feed: str, previous: Any = None
) -> None:
    if not await opened(interaction, staff=False):
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
    if not await opened(interaction, staff=False):
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
    interaction: discord.Interaction,
    role_id: Any = None,
    previous: Any = None,
    *,
    purpose: str = SETUP_PURPOSE,
) -> None:
    """Two sibling set-ups, one door: the Events role and the raid-train role."""
    if not await still_staff(interaction):
        return
    if not await opened(interaction, staff=False):
        return
    guild = interaction.guild
    make = (
        pings.setup_raidtrain_role if purpose == RAID_PURPOSE else pings.setup_events_role
    )
    outcome = await make(
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
    if not await opened(interaction, staff=False):
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
    if not await opened(interaction, staff=False):
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
    if not await opened(interaction, staff=False):
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
    if not await opened(interaction, staff=False):
        return
    said = await pings.save_settings(
        interaction.client, interaction.guild, interaction.user, changes
    )
    await render_settings(interaction, previous)
    await answer(interaction, said + echo if said.startswith(pings.SETTINGS_SAVED) else said)


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
        if action == pings.RAID_SETUP:
            await open_role_pick(interaction, RAID_PURPOSE, None, view)
            return
        if action == pings.ONBOARDING:
            await open_onboarding(interaction, view)
            return
        if action == pings.ONBOARDING_SYNC:
            await run_onboarding_sync(interaction, view)
            return
        if action == pings.ONBOARDING_STOP:
            wanted = not onboarding.managed(interaction.client, interaction.guild.id)
            await run_onboarding_managed(interaction, managed=wanted, previous=view)
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
        if action == pings.LIST_OUT:
            await open_confirm(interaction, self.move, view)
            return
        if action == pings.LIST_IN:
            await run_listing(interaction, listed=True, previous=view)
            return
        if action == pings.CARD_REMOVE:
            await open_card_confirm(interaction, view.streamer_id, view)
            return
        if action == pings.CARD_REMAKE:
            await run_remake(interaction, view.streamer_id, view)
            return
        if action in (pings.CARD_HIDE, pings.CARD_RESTORE):
            await run_card_listing(
                interaction, view.streamer_id, listed=action == pings.CARD_RESTORE, previous=view
            )
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
        modal = NumbersModal if action == pings.NUMBERS else NamesModal
        await interaction.response.send_modal(
            modal(interaction.client, interaction.guild.id, view)
        )


class FollowPick(discord.ui.Select):
    """Follow is over the LIST, stop-following over the ROLES worn; P10 caps both at 25."""

    def __init__(
        self, guild: Any, rows: Any, *, adding: bool, row: int, staff: bool = False
    ) -> None:
        found = list(rows)
        shown = found[: pings.SELECT_CAP]
        self.adding = adding
        label = pings.streamer_name if adding else pings.option_label
        super().__init__(
            placeholder=capped_placeholder(
                len(shown),
                len(found),
                pick=FOLLOW_PLACEHOLDER if adding else UNFOLLOW_PLACEHOLDER,
                capped=pings.STREAMERS_CAPPED if staff else pings.STREAMERS_CAPPED_MEMBER,
            ),
            options=[
                discord.SelectOption(
                    label=label(guild, one)[:SELECT_OPTION_LIMIT],
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
            placeholder=capped_placeholder(
                len(shown), len(found), pick=STREAMER_PLACEHOLDER, capped=pings.STREAMERS_CAPPED
            ),
            options=[
                discord.SelectOption(
                    label=pings.streamer_name(guild, one)[:SELECT_OPTION_LIMIT],
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
        label = SET_IT_UP if purpose in (SETUP_PURPOSE, RAID_PURPOSE) else MAKE_THE_ROLE
        super().__init__(label=label, style=discord.ButtonStyle.primary, row=row)
        self.purpose = purpose

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        if self.purpose in (SETUP_PURPOSE, RAID_PURPOSE):
            await run_setup(interaction, view.picked_role_id, view, purpose=self.purpose)
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
                    label=labels[name][:SELECT_OPTION_LIMIT], value=name, default=(name == current)
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


class NumbersModal(AnswersErrors, discord.ui.Modal):
    stale_days = discord.ui.TextInput(label=STALE_DAYS_LABEL, max_length=4)
    empty_days = discord.ui.TextInput(label=EMPTY_ROLE_DAYS_LABEL, max_length=4)
    cap = discord.ui.TextInput(label=CAP_LABEL, max_length=3)

    def __init__(self, bot: Any, guild_id: int, previous: Any = None) -> None:
        super().__init__(title=NUMBERS_MODAL_TITLE[:45])
        self.previous = previous
        store = bot.store
        self.stale_days.default = str(store.get(guild_id, pings.STALE_DAYS_KEY))
        self.empty_days.default = str(store.get(guild_id, pings.EMPTY_ROLE_DAYS_KEY))
        self.cap.default = str(store.get(guild_id, pings.ONBOARDING_CAP_KEY))

    async def on_submit(self, interaction: discord.Interaction) -> None:
        """Every field is checked before any of them is written — a bad one saves none."""
        wanted: dict[str, Any] = {}
        for field, key, label in (
            (self.stale_days, pings.STALE_DAYS_KEY, STALE_DAYS_LABEL),
            (self.empty_days, pings.EMPTY_ROLE_DAYS_KEY, EMPTY_ROLE_DAYS_LABEL),
            (self.cap, pings.ONBOARDING_CAP_KEY, CAP_LABEL),
        ):
            given = str(field).strip()
            if not given.isdigit():
                await answer(
                    interaction,
                    NOT_A_NUMBER.format(given=given[:40] or "nothing", label=label),
                )
                return
            wanted[key] = int(given)
        await run_settings(interaction, wanted, self.previous)


class Pings(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.last_ok_at: str = ""
        self.last_error: str = ""
        self.sweep.start()

    async def cog_unload(self) -> None:
        self.sweep.cancel()

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

    @tasks.loop(minutes=SWEEP_MINUTES)
    async def sweep(self) -> None:
        """C1/C2/C5 on one clock: the stale list, the unworn roles, and onboarding."""
        if not self.bot.db.is_connected:
            return
        for guild in list(getattr(self.bot, "guilds", ())):
            if getattr(guild, "unavailable", False):
                log.info("pings: %s is unavailable, so its list is left alone", guild.id)
                continue
            await self.sweep_guild(guild)
        self.last_ok_at = now_iso()

    async def sweep_guild(self, guild: Any) -> None:
        pruned = await pings.prune_stale_streamers(self.bot, guild)
        deleted = await pings.prune_empty_roles(self.bot, guild)
        result = await onboarding.reconcile(self.bot, guild)
        if pruned or deleted or result.wrote:
            log.info(
                "pings: swept %s — %d off the list, %d role(s) pruned, onboarding %s",
                guild.id,
                len(pruned),
                len(deleted),
                result.reason,
            )

    @sweep.before_loop
    async def _before_sweep(self) -> None:
        await wait_ready(self.bot, self._sweep_broke)

    @sweep.error
    async def _sweep_broke(self, exc: BaseException) -> None:
        """discord.py stops a loop that raises anything but an HTTP error, so it is restarted."""
        self.last_error = f"{now_iso()} · {type(exc).__name__}: {exc}"
        log.exception("pings: the sweep raised and is being restarted", exc_info=exc)
        self.sweep.restart()


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
    "NUMBERS_BUTTON",
    "ONBOARDING_STARTED",
    "ONBOARDING_STOPPED",
    "ONBOARDING_TITLE",
    "PANEL_INTRO",
    "RAID_TITLE",
    "ROLE_PLACEHOLDER",
    "SET_IT_UP",
    "SITE_BUTTON",
    "STREAMER_PLACEHOLDER",
    "UNFOLLOW_PLACEHOLDER",
    "ChoicePick",
    "ConfirmRoleButton",
    "FollowPick",
    "GivePick",
    "MoveButton",
    "NamesModal",
    "NumbersModal",
    "Pings",
    "PingsPanel",
    "RolePick",
    "StreamerPick",
    "build_card",
    "build_onboarding",
    "build_panel",
    "build_role_pick",
    "build_settings",
    "build_streamers",
    "card_lines",
    "run_card_listing",
    "run_events",
    "run_follow",
    "run_give",
    "run_listing",
    "run_onboarding_managed",
    "run_onboarding_sync",
    "run_own",
    "run_remake",
    "run_remove",
    "run_settings",
    "run_setup",
    "streams_now",
]
