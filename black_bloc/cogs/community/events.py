from __future__ import annotations

import logging
import re
from datetime import UTC, datetime, timedelta
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands, tasks

from ...actionlog import log_action, send_logs
from ...command_errors import NETWORK_ERRORS, AnswersErrors, SafeDynamicItem
from ...events import (
    ALREADY_DECIDED as EVENT_ALREADY_DECIDED,
)
from ...events import (
    APPROVED,
    CALL_ONE_OFF,
    CANCEL_NOTE_LIMIT,
    COLOURS,
    DENIED,
    DENY_LIMIT,
    DESCRIPTION_LIMIT,
    DM_MISSED,
    DONE,
    DRAFT_TITLE,
    ENDED_TEXT,
    EVENTS_OFF,
    FORUM_BUTTON,
    FORUM_CHANNEL_PLACEHOLDER,
    FORUM_TITLE,
    LIST_PAGE,
    LIVE,
    LOCATION_LIMIT,
    MAKE_THE_FORUM,
    MOVE_TARGETS,
    NO_SUCH_EVENT,
    NOTHING_OPEN,
    OPEN_STATUSES,
    PANEL_EMPTY,
    PANEL_INTRO,
    PANEL_TIMEOUT_FOOTER,
    PANEL_TITLE,
    PENDING,
    PLACE_LINK_BUTTON,
    PLACE_WORDS,
    POST,
    POSTS_WHERE_PLACEHOLDER,
    REVIEW_MODE_PLACEHOLDER,
    ROOM,
    ROOM_APPROVER_PLACEHOLDER,
    ROOM_DELETE_BUTTON,
    ROOM_DELETE_LABEL,
    ROOM_DELETE_PLACEHOLDER,
    ROOM_NOTICE_BUTTON,
    ROOMS_BUTTON,
    ROOMS_TITLE,
    ROW_ITEM_CAP,
    SELECT_CAP,
    SITE_BUTTON,
    SUBMIT_BUTTON,
    SWEEP_KEPT_DAYS,
    SWEEP_KEPT_MINUTES,
    SWEPT_STATUSES,
    TEXT_BUTTON,
    TEXT_MODAL_TITLE,
    TITLE_LIMIT,
    WHERE_CHANNEL_KINDS,
    WHERE_CLEAR_BUTTON,
    WHERE_JOIN_NOTE,
    WHERE_LINK_BUTTON,
    WHERE_LINK_MODAL_TITLE,
    WHERE_MODAL_LABEL,
    WHERE_MODAL_TITLE,
    WHERE_OPEN_LINK_BUTTON,
    WHERE_OTHER,
    WHERE_OTHER_BUTTON,
    WHERE_PANEL_INTRO,
    WHERE_PANEL_TITLE,
    WHERE_PLACEHOLDER,
    WHERE_UNSET,
    ZONE_BUTTON,
    ZONE_PANEL_BUTTON,
    ZONE_PANEL_INTRO,
    ZONE_PANEL_TITLE,
    EventDraft,
    Where,
    apply_decision,
    can_transition,
    cancel_event,
    cancel_for,
    card_buttons,
    card_footer_override,
    card_for,
    checked_numbers,
    clamp,
    counts_line,
    counts_of,
    default_minutes,
    delete_room,
    disown_room,
    dm,
    draft_check,
    draft_lines,
    drop_lock,
    due_events,
    event_for_channel,
    event_line,
    event_lock,
    events_by_status,
    forget_room,
    forum_lines,
    forum_of,
    get_event,
    golive_text,
    guild_zone,
    link_check_mode,
    link_check_seconds,
    list_lines,
    make_forum,
    may_cancel,
    may_delete_room,
    minute_step,
    option_label,
    own_events,
    own_room,
    panel_minutes,
    panel_shows_own_list,
    pick_placeholder,
    place_words,
    post_event,
    post_to_room,
    posts_in_room,
    read_where,
    rename_channel,
    retag_post,
    review_channel_url,
    review_kind,
    review_mode,
    review_place,
    rooms_lines,
    set_review,
    set_status,
    set_where,
    settings_lines,
    site_page_url,
    stored_zone,
    submit_event,
    swept_anchor,
    tell_or_log,
    when_line,
    where_aliases,
    where_button_label,
    where_link,
    where_note,
    where_of_channel,
    where_refused,
    where_typed,
    write_settings,
    zone_choices,
    zone_line,
)
from ...events import (
    NUMBERS_LABELS as EVENT_NUMBERS_LABELS,
)
from ...events import (
    set_zone as store_zone,
)
from ...golive import now_iso, parse_ts
from ...handoff import EVENT as HANDOFF_EVENT
from ...handoff import (
    NOT_AN_EVENT,
    event_to_request,
    handoff_on,
    prefilled,
    refusal_for_event,
    request_to_event,
    reread,
    ticket_became,
)
from ...handoff import REQUEST as HANDOFF_REQUEST
from ...handoff import TICKET as HANDOFF_TICKET
from ...linkcheck import LINK_OK, link_answers
from ...loops import wait_ready
from ...panels import (
    KEEP_IT,
    Panel,
    answer,
    confirm,
    confirm_items,
    opened,
    retire,
    still_staff,
)
from ...panels import NoteModal as PanelNoteModal
from ...settings_store import (
    DB_UNAVAILABLE,
    EVENTS_APPROVER_ROLE_KEY,
    EVENTS_FORUM_CHANNEL_KEY,
    EVENTS_MODES,
    EVENTS_POSTS_WHERE_KEY,
    EVENTS_POSTS_WHERES,
    EVENTS_REVIEW_MODE_KEY,
    EVENTS_REVIEW_MODES,
    EVENTS_ROOM_DELETE_KEY,
    EVENTS_ROOM_DELETE_WHOS,
    EVENTS_ROOM_NOTICE_KEY,
    EVENTS_TEST_RETENTION_KEY,
    GUILD_ONLY,
    WHERE_CHECK_OFF,
    WHERE_CHECK_REFUSE,
    require_staff,
)
from ...when_picker import (
    DaySelect,
    DurationSelect,
    HourSelect,
    MinuteSelect,
    WhenDraft,
    ZonePanel,
    duration_for,
)
from ...when_picker import ZoneModal as WhenZoneModal

log = logging.getLogger(__name__)

DECISION_TEMPLATE = (
    r"event:(?P<event_id>[0-9]+):(?P<action>approve|deny|delete_room|make_request)"
)
DELETE_ROOM = "delete_room"
MAKE_REQUEST = "make_request"
DECISION_LABELS: dict[str, str] = {
    "approve": "Approve",
    "deny": "Deny",
    DELETE_ROOM: ROOM_DELETE_BUTTON,
    MAKE_REQUEST: NOT_AN_EVENT,
}
GOLIVE_MINUTES = 1
RECONCILE_MINUTES = 5
LOOP_NAMES = ("golive", "reconcile")
ORPHAN_GRACE_MINUTES = 5
COG_NAME = "Events"

SETTINGS_TITLE = "Events — settings"
PROPOSE_BUTTON = "Propose an event"
SETTINGS_BUTTON = "Settings"
NUMBERS_BUTTON = "Numbers…"
FORGET_BUTTON = "Forget…"
CANCEL_YES = "Yes, call it off"
FORGET_PLACEHOLDER = "Forget which one?"
SCHEDULED_BUTTON = "Scheduled events: {state}"
MODE_PLACEHOLDER = "How events behave…"
CATEGORY_PLACEHOLDER = "Where review channels go (pick nothing to forget it)"
ANNOUNCE_PLACEHOLDER = "Where approved events are announced"
PING_PLACEHOLDER = "Role mentioned when one is announced"
ZONE_MODAL_TITLE = "Your time zone"
ZONE_MODAL_LABEL = "Region/City — Phoenix is America/Phoenix"
ZONE_INPUT_LIMIT = 60
DRAFT_BUTTON_ROW = 4
CARD_LINK_ROWS = (1, 2, 3, 4)
LINK_FETCH: Any = None
NUMBERS_MODAL_TITLE = "Events — numbers"
FORGOT_NOTHING = "Nothing was picked, so nothing was forgotten."

BUTTON_STYLES: dict[str, discord.ButtonStyle] = {
    "primary": discord.ButtonStyle.primary,
    "secondary": discord.ButtonStyle.secondary,
    "success": discord.ButtonStyle.success,
    "danger": discord.ButtonStyle.danger,
}
DECISION_STYLES: dict[str, discord.ButtonStyle] = {
    "approve": discord.ButtonStyle.success,
    "deny": discord.ButtonStyle.danger,
    DELETE_ROOM: discord.ButtonStyle.danger,
    MAKE_REQUEST: discord.ButtonStyle.secondary,
}
NOTE_TITLES: dict[str, str] = {"deny": "Why not?", "cancel": "Why is it off?"}
NOTE_LABELS: dict[str, str] = {
    "deny": "One line the requester will be sent",
    "cancel": "One line the requester will be sent",
}
NOTE_LIMITS: dict[str, int] = {"deny": DENY_LIMIT, "cancel": CANCEL_NOTE_LIMIT}
NOTE_REQUIRED: dict[str, bool] = {"deny": True, "cancel": False}
FORGETTABLE: tuple[tuple[str, str], ...] = (
    ("events_category_id", "the category review channels go in"),
    ("events_announce_channel_id", "where approved events are announced"),
    ("events_ping_role_id", "the role that gets mentioned"),
    (EVENTS_FORUM_CHANNEL_KEY, "the events forum"),
)


def decision_id(event_id: int, action: str) -> str:
    return f"event:{event_id}:{action}"


def review_view(event_id: int, *, handoff: bool = False) -> discord.ui.View:
    view = discord.ui.View(timeout=None)
    view.add_item(DecisionButton(event_id, "approve"))
    view.add_item(DecisionButton(event_id, "deny"))
    if handoff:
        view.add_item(DecisionButton(event_id, MAKE_REQUEST))
    return view


def handoff_review_view(bot: Any, guild: Any) -> Any:
    """`submit_event` takes a one-argument factory; the store is read here, not inside it."""
    on = handoff_on(bot.store, guild.id)
    return lambda event_id: review_view(event_id, handoff=on)


def room_notice_view(event_id: int, kind: str = ROOM) -> discord.ui.View:
    """The Delete button, labelled for the place it is about to be posted in."""
    view = discord.ui.View(timeout=None)
    view.add_item(DecisionButton(event_id, DELETE_ROOM, label=PLACE_WORDS[kind].button))
    return view


async def decide(
    interaction: discord.Interaction, event_id: int, status: str, reason: str | None = None
) -> None:
    said, fresh = await apply_decision(
        interaction.client, interaction.guild, event_id, status, interaction.user, reason
    )
    if fresh is not None:
        await close_card(interaction, fresh)
    await answer(interaction, said)


async def make_it_a_request(interaction: discord.Interaction, event_id: int) -> None:
    """Not an event — make it a request: the review room's own hand-off (send-to-design §A)."""
    row = await decision_context(interaction, event_id)
    if row is None:
        return
    refused = refusal_for_event(interaction.client.store, interaction.guild.id, row)
    if refused:
        await answer(interaction, refused)
        return
    await interaction.response.defer(ephemeral=True)
    said, fresh = await event_to_request(
        interaction.client, interaction.guild, row, interaction.user
    )
    if fresh is not None:
        await close_card(interaction, fresh)
        await say_in_the_room(interaction.client, interaction.guild, fresh, said)
    await answer(interaction, said)


async def say_in_the_room(bot: Any, guild: Any, row: Any, said: str) -> None:
    """The trail line the review place keeps beside the card it just closed."""
    room = review_place(bot, guild, row)
    guard = getattr(bot, "guard", None)
    if room is None or (guard is not None and not guard.allows_channel(room.id)):
        return
    try:
        await room.send(said, allowed_mentions=discord.AllowedMentions.none())
    except NETWORK_ERRORS as exc:
        log.warning("events: could not leave the hand-off line for %s: %s", row["id"], exc)


async def close_card(interaction: discord.Interaction, row: Any) -> None:
    message = getattr(interaction, "message", None)
    if message is None:
        return
    try:
        await message.edit(
            embed=card_for(row), view=None, allowed_mentions=discord.AllowedMentions.none()
        )
    except Exception as exc:
        log.warning("events: could not close the card for event %s: %s", row["id"], exc)


async def decision_context(
    interaction: discord.Interaction, event_id: int, *, staff: bool = True
) -> Any:
    """This click's event row, or None once the clicker has been answered."""
    bot = interaction.client
    guard = getattr(bot, "guard", None)
    if guard is not None and not guard.allows_channel(interaction.channel_id):
        await interaction.response.send_message(guard.refusal_message(), ephemeral=True)
        return None
    if staff and not await require_staff(interaction):
        return None
    if not bot.db.is_connected:
        await interaction.response.send_message(DB_UNAVAILABLE, ephemeral=True)
        return None
    row = await get_event(bot.db, event_id)
    if row is None:
        await interaction.response.send_message(NO_SUCH_EVENT, ephemeral=True)
        return None
    return row


class EventView(Panel):
    def __init__(self, minutes: int) -> None:
        super().__init__(minutes, footer=PANEL_TIMEOUT_FOOTER)


def origin_of(bot: Any) -> str:
    return str(getattr(getattr(bot, "settings", None), "origin", "") or "")


async def build_panel(bot: Any, guild: Any, actor: Any) -> tuple[discord.Embed, EventView]:
    store = bot.store
    staff = store.is_staff(actor)
    on = store.get(guild.id, "events_mode") != "off"
    zone_name, chosen = await stored_zone(bot.db, actor.id, guild_zone(store, guild.id))
    own = await own_events(bot.db, guild.id, actor.id)
    staff_rows: list[Any] = []

    lines = [PANEL_INTRO, zone_line(zone_name, chosen=chosen)]
    if staff:
        staff_rows = await events_by_status(bot.db, guild.id, OPEN_STATUSES)
        lines.append(counts_line(counts_of(staff_rows)))
        lines.extend(list_lines(staff_rows[:LIST_PAGE], store.staff_roles(guild)))
    elif panel_shows_own_list(store, guild.id):
        lines.extend(
            [event_line(row) for row in own[:LIST_PAGE]] if own else [PANEL_EMPTY]
        )
    if not on:
        lines.append(EVENTS_OFF)
    if staff and not staff_rows:
        lines.append(NOTHING_OPEN)

    embed = discord.Embed(
        title=PANEL_TITLE, description="\n".join(lines), colour=discord.Colour(COLOURS[PENDING])
    )
    view = EventView(panel_minutes(store, guild.id))
    if on:
        view.add_item(ProposeButton())
        view.add_item(ZoneButton())
    view.add_item(RefreshButton())
    page = site_page_url(origin_of(bot))
    if page:
        view.add_item(
            discord.ui.Button(
                style=discord.ButtonStyle.link, label=SITE_BUTTON, url=page, row=0
            )
        )
    mine = [row for row in own if may_cancel(store, row, actor)]
    if mine:
        view.add_item(CallOffPick(mine))
    if staff and staff_rows:
        view.add_item(EventPick(staff_rows[:SELECT_CAP], len(staff_rows)))
    if staff:
        view.add_item(SettingsButton())
        view.add_item(LogsButton())
    return embed, view


def add_open_link(view: EventView, text: Any, rows: Any) -> None:
    """A typed link becomes a real button on the first of `rows` with a slot still free."""
    url = where_link(text)
    if not url:
        return
    taken = [item.row for item in view.children]
    room = next((one for one in rows if taken.count(one) < ROW_ITEM_CAP), None)
    if room is None:
        return
    view.add_item(
        discord.ui.Button(
            style=discord.ButtonStyle.link, label=WHERE_OPEN_LINK_BUTTON, url=url, row=room
        )
    )


def build_card(bot: Any, guild: Any, row: Any, actor: Any) -> tuple[discord.Embed, EventView]:
    room = review_place(bot, guild, row)
    embed = card_for(row)
    override = card_footer_override(row["status"], room_resolves=room is not None)
    if override:
        embed.set_footer(text=override)
    view = EventView(panel_minutes(bot.store, guild.id))
    for spec in card_buttons(
        row["status"],
        may_cancel_here=may_cancel(bot.store, row, actor),
        room_resolves=room is not None,
    ):
        view.add_item(CardMoveButton(row["id"], spec))
    if bot.store.is_staff(actor) and row["status"] in OPEN_STATUSES:
        where = read_where(row)
        view.add_item(
            CardWhereButton(row["id"], where, guild.get_channel(where.channel_id or 0))
        )
    view.add_item(BackButton())
    if room is not None:
        view.add_item(
            discord.ui.Button(
                style=discord.ButtonStyle.link,
                label=PLACE_LINK_BUTTON[review_kind(row)],
                url=review_channel_url(guild.id, room.id),
                row=1,
            )
        )
    add_open_link(view, read_where(row).text, CARD_LINK_ROWS)
    return embed, view


def build_settings(bot: Any, guild: Any, health: Any = ()) -> tuple[discord.Embed, EventView]:
    store = bot.store
    embed = discord.Embed(
        title=SETTINGS_TITLE,
        description="\n".join(settings_lines(store, guild, health)),
        colour=discord.Colour(COLOURS[PENDING]),
    )
    view = EventView(panel_minutes(store, guild.id))
    view.add_item(ModeSelect(str(store.get(guild.id, "events_mode"))))
    view.add_item(CategorySelect())
    view.add_item(AnnounceSelect())
    view.add_item(PingRoleSelect())
    view.add_item(ScheduledButton(bool(store.get(guild.id, "events_create_scheduled"))))
    view.add_item(NumbersButton())
    view.add_item(ForgetButton())
    view.add_item(RoomsButton())
    view.add_item(BackButton(row=4))
    return embed, view


def build_rooms(bot: Any, guild: Any) -> tuple[discord.Embed, EventView]:
    """The four room keys, on their own page because a settings row holds one select."""
    store = bot.store
    embed = discord.Embed(
        title=ROOMS_TITLE,
        description="\n".join(rooms_lines(store, guild)),
        colour=discord.Colour(COLOURS[PENDING]),
    )
    view = EventView(panel_minutes(store, guild.id))
    view.add_item(PostsWhereSelect(str(store.get(guild.id, EVENTS_POSTS_WHERE_KEY))))
    view.add_item(RoomDeleteSelect(str(store.get(guild.id, EVENTS_ROOM_DELETE_KEY))))
    view.add_item(RoomApproverSelect())
    view.add_item(RoomNoticeButton(bool(store.get(guild.id, EVENTS_ROOM_NOTICE_KEY))))
    view.add_item(ForumButton())
    view.add_item(SettingsButton(row=3))
    page = site_page_url(origin_of(bot))
    if page:
        view.add_item(
            discord.ui.Button(
                style=discord.ButtonStyle.link, label=SITE_BUTTON, url=page, row=3
            )
        )
    return embed, view


def build_forum(bot: Any, guild: Any) -> tuple[discord.Embed, EventView]:
    """The two forum keys and **Make the forum**, on their own page for want of a fifth row."""
    store = bot.store
    embed = discord.Embed(
        title=FORUM_TITLE,
        description="\n".join(forum_lines(store, guild)),
        colour=discord.Colour(COLOURS[PENDING]),
    )
    view = EventView(panel_minutes(store, guild.id))
    view.add_item(ReviewModeSelect(review_mode(store, guild.id)))
    view.add_item(ForumSelect())
    view.add_item(MakeForumButton(forum_of(bot, guild) is not None))
    view.add_item(RoomsButton(row=2))
    page = site_page_url(origin_of(bot))
    if page:
        view.add_item(
            discord.ui.Button(
                style=discord.ButtonStyle.link, label=SITE_BUTTON, url=page, row=2
            )
        )
    return embed, view


async def render_forum(interaction: discord.Interaction, previous: Any = None) -> None:
    embed, view = build_forum(interaction.client, interaction.guild)
    retire(previous)
    view.message = await interaction.edit_original_response(
        embed=embed,
        view=view,
        allowed_mentions=discord.AllowedMentions.none(),
    )


async def open_forum(interaction: discord.Interaction, previous: Any = None) -> None:
    if not await still_staff(interaction):
        return
    if not await opened(interaction, staff=False):
        return
    await render_forum(interaction, previous)


async def make_the_forum(interaction: discord.Interaction, previous: Any = None) -> None:
    """One press, one path — the website's **Make the forum** calls the same function."""
    if not await still_staff(interaction):
        return
    if not await opened(interaction, staff=False):
        return
    outcome = await make_forum(interaction.client, interaction.guild, interaction.user)
    await render_forum(interaction, previous)
    await interaction.followup.send(
        outcome.message, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
    )


def build_forget(bot: Any, guild: Any) -> tuple[discord.Embed, EventView]:
    embed = discord.Embed(
        title=SETTINGS_TITLE,
        description="\n".join(settings_lines(bot.store, guild)),
        colour=discord.Colour(COLOURS[PENDING]),
    )
    view = EventView(panel_minutes(bot.store, guild.id))
    view.add_item(ForgetPick())
    view.add_item(SettingsButton(row=1))
    return embed, view


async def render_panel(interaction: discord.Interaction, previous: Any = None) -> None:
    embed, view = await build_panel(interaction.client, interaction.guild, interaction.user)
    retire(previous)
    view.message = await interaction.edit_original_response(
        embed=embed,
        view=view,
        allowed_mentions=discord.AllowedMentions.none(),
    )


async def render_settings(interaction: discord.Interaction, previous: Any = None) -> None:
    cog = interaction.client.get_cog(COG_NAME)
    health = cog.health_lines() if cog is not None else ()
    embed, view = build_settings(interaction.client, interaction.guild, health)
    retire(previous)
    view.message = await interaction.edit_original_response(
        embed=embed,
        view=view,
        allowed_mentions=discord.AllowedMentions.none(),
    )


async def render_rooms(interaction: discord.Interaction, previous: Any = None) -> None:
    embed, view = build_rooms(interaction.client, interaction.guild)
    retire(previous)
    view.message = await interaction.edit_original_response(
        embed=embed,
        view=view,
        allowed_mentions=discord.AllowedMentions.none(),
    )


async def open_rooms(interaction: discord.Interaction, previous: Any = None) -> None:
    if not await still_staff(interaction):
        return
    if not await opened(interaction, staff=False):
        return
    await render_rooms(interaction, previous)


async def back_to_panel(interaction: discord.Interaction, previous: Any = None) -> None:
    if not await opened(interaction, staff=False):
        return
    await render_panel(interaction, previous)


async def open_settings(interaction: discord.Interaction, previous: Any = None) -> None:
    if not await still_staff(interaction):
        return
    if not await opened(interaction, staff=False):
        return
    await render_settings(interaction, previous)


async def open_forget(interaction: discord.Interaction, previous: Any = None) -> None:
    if not await still_staff(interaction):
        return
    if not await opened(interaction, staff=False):
        return
    embed, view = build_forget(interaction.client, interaction.guild)
    retire(previous)
    view.message = await interaction.edit_original_response(
        embed=embed,
        view=view,
        allowed_mentions=discord.AllowedMentions.none(),
    )


async def change_settings(
    interaction: discord.Interaction,
    changes: dict[str, Any],
    previous: Any = None,
    render: Any = None,
) -> None:
    """Every settings control lands here: one write per key, one log row, one re-render."""
    if not await still_staff(interaction):
        return
    if not await opened(interaction, staff=False):
        return
    bot = interaction.client
    changed = await write_settings(
        bot.store, interaction.guild.id, interaction.user.id, changes
    )
    await (render or render_settings)(interaction, previous)
    if changed:
        await log_action(
            bot, interaction.guild, "event.settings", actor=interaction.user, details=changed
        )


async def render_card(
    interaction: discord.Interaction, event_id: int, previous: Any = None
) -> None:
    """The card itself, for the callers that have already deferred their own interaction."""
    bot = interaction.client
    row = await get_event(bot.db, event_id)
    if row is None or row["guild_id"] != interaction.guild.id:
        await interaction.followup.send(
            NO_SUCH_EVENT, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
        )
        return
    embed, view = build_card(bot, interaction.guild, row, interaction.user)
    retire(previous)
    view.message = await interaction.edit_original_response(
        embed=embed,
        view=view,
        allowed_mentions=discord.AllowedMentions.none(),
    )


async def open_card(
    interaction: discord.Interaction, event_id: int, previous: Any = None
) -> None:
    if not await opened(interaction, staff=False):
        return
    await render_card(interaction, event_id, previous)


async def finish_card(
    interaction: discord.Interaction,
    event_id: int,
    said: str,
    fresh: Any,
    previous: Any = None,
) -> None:
    bot = interaction.client
    row = fresh if fresh is not None else await get_event(bot.db, event_id)
    if row is None:
        await render_panel(interaction, previous)
    else:
        embed, view = build_card(bot, interaction.guild, row, interaction.user)
        retire(previous)
        view.message = await interaction.edit_original_response(
            embed=embed,
            view=view,
            allowed_mentions=discord.AllowedMentions.none(),
        )
    await interaction.followup.send(
        said, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
    )


async def run_move(
    interaction: discord.Interaction, event_id: int, action: str, previous: Any = None
) -> None:
    if not await opened(interaction, staff=False):
        return
    said, fresh = await apply_decision(
        interaction.client, interaction.guild, event_id, MOVE_TARGETS[action], interaction.user
    )
    await finish_card(interaction, event_id, said, fresh, previous)


async def open_cancel_confirm(
    interaction: discord.Interaction, event_id: int, previous: Any = None
) -> None:
    if not await opened(interaction, staff=False):
        return
    bot = interaction.client
    row = await get_event(bot.db, event_id)
    if row is None or row["guild_id"] != interaction.guild.id:
        await render_panel(interaction, previous)
        await interaction.followup.send(
            NO_SUCH_EVENT, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
        )
        return
    if not may_cancel(bot.store, row, interaction.user):
        await render_panel(interaction, previous)
        await interaction.followup.send(
            EVENT_ALREADY_DECIDED.format(event_id=event_id, status=row["status"]),
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        return
    await confirm(
        interaction,
        EventView(panel_minutes(bot.store, interaction.guild.id)),
        card_for(row),
        confirm_items(
            yes=CANCEL_YES,
            no=KEEP_IT,
            on_yes=lambda one, card: confirm_cancel(one, event_id, card),
            on_no=back_to_panel,
        ),
        previous,
    )


async def confirm_cancel(
    interaction: discord.Interaction, event_id: int, previous: Any = None
) -> None:
    if not await opened(interaction, staff=False):
        return
    bot = interaction.client
    row = await get_event(bot.db, event_id)
    if row is None:
        await render_panel(interaction, previous)
        return
    if not may_cancel(bot.store, row, interaction.user):
        await render_panel(interaction, previous)
        await interaction.followup.send(
            EVENT_ALREADY_DECIDED.format(event_id=event_id, status=row["status"]),
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        return
    said, _ = await cancel_for(bot, interaction.guild, row, interaction.user)
    await render_panel(interaction, previous)
    await interaction.followup.send(
        said, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
    )


class EventDraftPanel(Panel):
    """The draft the four dropdowns and the text modal write into; nothing here refuses."""

    def __init__(self, minutes: int, fields: EventDraft) -> None:
        super().__init__(minutes, footer=PANEL_TIMEOUT_FOOTER, again=self.reopen)
        self.fields = fields

    @property
    def draft(self) -> WhenDraft:
        return self.fields.when

    async def reopen(self, interaction: discord.Interaction, previous: Any = None) -> None:
        """Try again lands here: the same `fields`, so the title they typed comes back with it."""
        await open_draft(interaction, self.fields, previous)

    async def rerender(self, interaction: discord.Interaction) -> None:
        await open_draft(interaction, self.fields, self)

    async def take_later(self, interaction: discord.Interaction, text: str) -> None:
        self.fields.when.later_text = str(text or "").strip()
        self.fields.when.day = None
        await self.rerender(interaction)

    async def take_duration(self, interaction: discord.Interaction, value: str) -> None:
        self.fields.duration = value
        await self.rerender(interaction)


async def build_draft(
    bot: Any, guild: Any, actor: Any, fields: EventDraft
) -> tuple[discord.Embed, EventDraftPanel]:
    store = bot.store
    now = datetime.now(UTC)
    zone_name, chosen = await stored_zone(bot.db, actor.id, guild_zone(store, guild.id))
    fields.when.zone = zone_name
    checked, why = draft_check(fields, now)
    embed = discord.Embed(
        title=DRAFT_TITLE,
        description="\n".join(draft_lines(fields, now, chosen=chosen, why=why)),
        colour=discord.Colour(COLOURS[PENDING]),
    )
    view = EventDraftPanel(panel_minutes(store, guild.id), fields)
    view.add_item(DaySelect(fields.when, now))
    view.add_item(HourSelect(fields.when))
    view.add_item(MinuteSelect(fields.when, minute_step(store, guild.id)))
    view.add_item(DurationSelect(fields.duration))
    view.add_item(TextButton())
    view.add_item(WhereButton(fields.where, guild.get_channel(fields.where.channel_id or 0)))
    view.add_item(DraftZoneButton())
    if checked is not None:
        view.add_item(SubmitButton())
    view.add_item(BackButton(row=DRAFT_BUTTON_ROW))
    return embed, view


async def render_draft(
    interaction: discord.Interaction, fields: EventDraft, previous: Any = None
) -> None:
    embed, view = await build_draft(
        interaction.client, interaction.guild, interaction.user, fields
    )
    retire(previous)
    view.message = await interaction.edit_original_response(
        embed=embed, view=view, allowed_mentions=discord.AllowedMentions.none()
    )


async def open_draft(
    interaction: discord.Interaction, fields: EventDraft, previous: Any = None
) -> None:
    if not await opened(interaction, staff=False):
        return
    await render_draft(interaction, fields, previous)


def handed_over(fields: EventDraft) -> bool:
    return bool(fields.from_request or fields.from_ticket)


def proposer(guild: Any, fields: EventDraft) -> Any:
    """Whose name an event is filed in: the member a hand-off names, else whoever pressed."""
    if not fields.requester_id:
        return None
    return guild.get_member(int(fields.requester_id)) or int(fields.requester_id)


async def open_request_draft(
    interaction: discord.Interaction, row: Any, previous: Any = None
) -> None:
    """Send to events… — the `/event` draft, pre-filled and proposed in the requester's name."""
    bot = interaction.client
    title, description = prefilled(row, kind=HANDOFF_REQUEST)
    await render_draft(
        interaction,
        EventDraft(
            duration=duration_for(default_minutes(bot.store, interaction.guild.id)),
            title=title,
            description=description,
            requester_id=int(row["user_id"]),
            from_request=int(row["id"]),
        ),
        previous,
    )


async def open_ticket_draft(
    interaction: discord.Interaction, ticket: Any, title: str, body: str, previous: Any = None
) -> None:
    """The same draft, raised from a ticket the member has already said yes to."""
    bot = interaction.client
    _, head = prefilled(ticket, kind=HANDOFF_TICKET)
    await render_draft(
        interaction,
        EventDraft(
            duration=duration_for(default_minutes(bot.store, interaction.guild.id)),
            title=clamp(title, TITLE_LIMIT),
            description=f"{head}\n{body}".strip(),
            requester_id=int(ticket["user_id"]),
            from_ticket=int(ticket["id"]),
        ),
        previous,
    )


async def submit_draft(interaction: discord.Interaction, previous: Any) -> None:
    """The Submit button and nothing else: `checked_fields` onward, exactly as the modal did."""
    fields = previous.fields
    bot = interaction.client
    if not await opened(interaction, staff=False):
        return
    if bot.store.get(interaction.guild.id, "events_mode") == "off":
        await render_panel(interaction, previous)
        await answer(interaction, EVENTS_OFF)
        return
    checked, why = draft_check(fields, datetime.now(UTC))
    if checked is None:
        await render_draft(interaction, fields, previous)
        await answer(interaction, why)
        return
    said, row = await submit_event(
        bot,
        interaction.guild,
        interaction.user,
        checked,
        review_view=handoff_review_view(bot, interaction.guild),
        room_view=room_notice_view,
        requester=proposer(interaction.guild, fields),
    )
    if row is None:
        await render_draft(interaction, fields, previous)
        await answer(interaction, said)
        return
    trail = await close_what_it_came_from(interaction, fields, row)
    await render_panel(interaction, previous)
    await answer(
        interaction, f"{said} {when_line(checked.starts, fields.when.zone)}{trail}"
    )
    if not handed_over(fields):
        await dm(interaction.user, f"Submitted on **{interaction.guild.name}**.", card_for(row))


async def close_what_it_came_from(
    interaction: discord.Interaction, fields: EventDraft, row: Any
) -> str:
    """A hand-off's second half: the request closes as moved, or the ticket gains its link."""
    if fields.from_request:
        line, _ = await request_to_event(
            interaction.client,
            interaction.guild,
            int(fields.from_request),
            row,
            interaction.user,
        )
        return f" {line}"
    if fields.from_ticket:
        from ..moderation.modmail import bump_card

        line = await ticket_became(
            interaction.client,
            interaction.guild,
            int(fields.from_ticket),
            HANDOFF_EVENT,
            row["id"],
            interaction.user,
        )
        ticket = await reread(interaction.client, int(fields.from_ticket))
        if ticket is not None:
            await bump_card(interaction.client, interaction.guild, ticket)
        return f" {line}"
    return ""


async def open_where_panel(
    interaction: discord.Interaction, where: Where, previous: Any, on_pick: Any, back: Any
) -> None:
    """One Where panel, from the draft and from a staff card; `on_pick` decides what it writes."""
    if not await opened(interaction, staff=False):
        return
    store = interaction.client.store
    embed = discord.Embed(
        title=WHERE_PANEL_TITLE,
        description="\n".join([WHERE_PANEL_INTRO, WHERE_JOIN_NOTE]),
        colour=discord.Colour(COLOURS[PENDING]),
    )
    view = WherePanel(
        panel_minutes(store, interaction.guild.id),
        where=where,
        on_pick=on_pick,
        on_back=back,
        known=interaction.guild.get_channel(where.channel_id or 0) is not None,
    )
    retire(previous)
    view.message = await interaction.edit_original_response(
        embed=embed, view=view, allowed_mentions=discord.AllowedMentions.none()
    )


class WherePanel(Panel):
    """The channel picker, the typed door and the way back; what it writes is handed in."""

    def __init__(
        self, minutes: int, *, where: Where, on_pick: Any, on_back: Any, known: bool = True
    ) -> None:
        super().__init__(minutes, footer=PANEL_TIMEOUT_FOOTER)
        self.where = where
        self.where_note = ""
        self.takes_where = on_pick
        self.goes_back = on_back
        self.add_item(WhereSelect(where, known=known))
        self.add_item(WhereOtherButton(where))
        if where.kind is not None:
            self.add_item(WhereClearButton())
        self.add_item(WhereBackButton())

    async def take_where(self, interaction: discord.Interaction, where: Where) -> None:
        await self.takes_where(interaction, where, self)

    async def go_back(self, interaction: discord.Interaction) -> None:
        await self.goes_back(interaction, self)


class WhereSelect(discord.ui.ChannelSelect):
    """Discord's own picker, so there is no 25 cap and no option list to keep in step."""

    def __init__(self, where: Where, *, known: bool = True) -> None:
        super().__init__(
            placeholder=WHERE_PLACEHOLDER,
            channel_types=[
                discord.ChannelType.voice,
                discord.ChannelType.stage_voice,
                discord.ChannelType.text,
            ],
            min_values=0,
            max_values=1,
            row=0,
            default_values=(
                [discord.Object(id=int(where.channel_id))] if where.channel_id and known else []
            ),
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        picked = self.values[0] if self.values else None
        kept = clamp(self.view.where.text, LOCATION_LIMIT)
        if picked is None:
            await self.view.take_where(
                interaction, Where(WHERE_OTHER, None, kept) if kept else WHERE_UNSET
            )
            return
        found = where_of_channel(picked)
        await self.view.take_where(
            interaction, found._replace(text=kept) if found.kind else WHERE_UNSET
        )


class WhereOtherButton(discord.ui.Button):
    """One door to the box, whose words change with what the channel picker already holds."""

    def __init__(self, where: Where) -> None:
        beside = where.kind in WHERE_CHANNEL_KINDS and bool(where.channel_id)
        super().__init__(
            label=WHERE_LINK_BUTTON if beside else WHERE_OTHER_BUTTON,
            style=discord.ButtonStyle.secondary,
            row=1,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(WhereModal(self.view))


class WhereClearButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label=WHERE_CLEAR_BUTTON, style=discord.ButtonStyle.secondary, row=1)

    async def callback(self, interaction: discord.Interaction) -> None:
        await self.view.take_where(interaction, WHERE_UNSET)


class WhereBackButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label="Back", style=discord.ButtonStyle.secondary, row=1)

    async def callback(self, interaction: discord.Interaction) -> None:
        await self.view.go_back(interaction)


class WhereModal(AnswersErrors, discord.ui.Modal, title=WHERE_MODAL_TITLE):
    """One optional box, no failure path: beside a channel a link, alone the place itself."""

    place = discord.ui.TextInput(
        label=WHERE_MODAL_LABEL, max_length=LOCATION_LIMIT, required=False
    )

    def __init__(self, previous: Any) -> None:
        super().__init__()
        self.previous = previous
        where = previous.where
        self.beside = where.kind in WHERE_CHANNEL_KINDS and bool(where.channel_id)
        if self.beside:
            self.title = WHERE_LINK_MODAL_TITLE
        self.place.default = where.text or None

    async def on_submit(self, interaction: discord.Interaction) -> None:
        store = interaction.client.store
        guild_id = interaction.guild.id
        typed = clamp(
            where_typed(clamp(self.place, LOCATION_LIMIT), where_aliases(store, guild_id)),
            LOCATION_LIMIT,
        )
        url, mode = where_link(typed), link_check_mode(store, guild_id)
        note = ""
        if url is not None and mode != WHERE_CHECK_OFF:
            seconds = link_check_seconds(store, guild_id)
            verdict = await link_answers(url, seconds=seconds, fetch=LINK_FETCH)
            if verdict != LINK_OK and mode == WHERE_CHECK_REFUSE:
                await answer(interaction, where_refused(verdict, url, seconds))
                return
            note = where_note(verdict, url, seconds)
        self.previous.where_note = note
        where = self.previous.where
        if self.beside:
            await self.previous.take_where(interaction, where._replace(text=typed))
            return
        await self.previous.take_where(
            interaction, Where(WHERE_OTHER, None, typed) if typed else WHERE_UNSET
        )


async def open_zone_panel(interaction: discord.Interaction, previous: Any, back: Any) -> None:
    """One zone panel, from `/event` and from both drafts; `back` decides where Back goes."""
    if not await opened(interaction, staff=False):
        return
    bot, store = interaction.client, interaction.client.store
    guild_default = guild_zone(store, interaction.guild.id)
    zone_name, chosen = await stored_zone(bot.db, interaction.user.id, guild_default)
    current = zone_name if chosen else ""
    embed = discord.Embed(
        title=ZONE_PANEL_TITLE,
        description="\n".join([ZONE_PANEL_INTRO, zone_line(zone_name, chosen=chosen)]),
        colour=discord.Colour(COLOURS[PENDING]),
    )
    view = ZonePanel(
        panel_minutes(store, interaction.guild.id),
        footer=PANEL_TIMEOUT_FOOTER,
        choices=zone_choices(store, interaction.guild.id),
        stored=current or None,
        guild_default=guild_default,
        on_pick=lambda one, name, panel: pick_zone(one, name, panel, back),
        on_other=lambda one, panel: open_zone_modal(one, current, panel, back),
        on_back=back,
        again=back,
    )
    retire(previous)
    view.message = await interaction.edit_original_response(
        embed=embed, view=view, allowed_mentions=discord.AllowedMentions.none()
    )


async def open_zone_modal(
    interaction: discord.Interaction, current: str, previous: Any, back: Any
) -> None:
    await interaction.response.send_modal(
        ZoneModal(interaction.client.get_cog(COG_NAME), current, previous, back)
    )


async def pick_zone(
    interaction: discord.Interaction, given: str, previous: Any, back: Any
) -> None:
    """`store_zone` writes the row and says the sentence; the panel adds neither of its own."""
    cog = interaction.client.get_cog(COG_NAME)
    await cog.zone_submit(interaction, given, previous, back)


class ProposeButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label=PROPOSE_BUTTON, style=discord.ButtonStyle.primary, row=0)

    async def callback(self, interaction: discord.Interaction) -> None:
        bot = interaction.client
        if bot.store.get(interaction.guild.id, "events_mode") == "off":
            await answer(interaction, EVENTS_OFF)
            return
        if not bot.db.is_connected:
            await answer(interaction, DB_UNAVAILABLE)
            return
        fields = EventDraft(
            duration=duration_for(default_minutes(bot.store, interaction.guild.id))
        )
        await open_draft(interaction, fields, self.view)


class TextButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(
            label=TEXT_BUTTON, style=discord.ButtonStyle.primary, row=DRAFT_BUTTON_ROW
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(EventTextModal(self.view))


class SubmitButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(
            label=SUBMIT_BUTTON, style=discord.ButtonStyle.success, row=DRAFT_BUTTON_ROW
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await submit_draft(interaction, self.view)


class WhereButton(discord.ui.Button):
    """The fifth button on the draft's row; its label carries the pick so the card is not read."""

    def __init__(self, where: Where, channel: Any = None) -> None:
        super().__init__(
            label=where_button_label(where, channel),
            style=discord.ButtonStyle.secondary,
            row=DRAFT_BUTTON_ROW,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        fields = self.view.fields
        await open_where_panel(
            interaction,
            fields.where,
            self.view,
            lambda one, where, prev: take_draft_where(one, fields, where, prev),
            lambda one, prev: open_draft(one, fields, prev),
        )


async def take_draft_where(
    interaction: discord.Interaction, fields: EventDraft, where: Where, previous: Any
) -> None:
    fields.where = where
    fields.where_note = str(getattr(previous, "where_note", "") or "")
    await open_draft(interaction, fields, previous)


class DraftZoneButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(
            label=ZONE_PANEL_BUTTON, style=discord.ButtonStyle.secondary, row=DRAFT_BUTTON_ROW
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        fields = self.view.fields
        await open_zone_panel(
            interaction, self.view, lambda one, prev: open_draft(one, fields, prev)
        )


class ZoneButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label=ZONE_BUTTON, style=discord.ButtonStyle.secondary, row=0)

    async def callback(self, interaction: discord.Interaction) -> None:
        if not interaction.client.db.is_connected:
            await answer(interaction, DB_UNAVAILABLE)
            return
        await open_zone_panel(interaction, self.view, back_to_panel)


class RefreshButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label="Refresh", style=discord.ButtonStyle.secondary, row=0)

    async def callback(self, interaction: discord.Interaction) -> None:
        await back_to_panel(interaction, self.view)


class BackButton(discord.ui.Button):
    def __init__(self, row: int = 1) -> None:
        super().__init__(label="Back", style=discord.ButtonStyle.secondary, row=row)

    async def callback(self, interaction: discord.Interaction) -> None:
        await back_to_panel(interaction, self.view)


class SettingsButton(discord.ui.Button):
    def __init__(self, row: int = 3) -> None:
        super().__init__(label=SETTINGS_BUTTON, style=discord.ButtonStyle.secondary, row=row)

    async def callback(self, interaction: discord.Interaction) -> None:
        await open_settings(interaction, self.view)


class LogsButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label="Logs", style=discord.ButtonStyle.secondary, row=3)

    async def callback(self, interaction: discord.Interaction) -> None:
        await send_logs(interaction, "events")


class NumbersButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label=NUMBERS_BUTTON, style=discord.ButtonStyle.secondary, row=4)

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await still_staff(interaction):
            return
        store = interaction.client.store
        await interaction.response.send_modal(
            NumbersModal(
                interaction.client.get_cog(COG_NAME),
                store.get(interaction.guild.id, "events_channel_retention_days"),
                store.get(interaction.guild.id, "events_max_late_minutes"),
                self.view,
            )
        )


class ForgetButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label=FORGET_BUTTON, style=discord.ButtonStyle.secondary, row=4)

    async def callback(self, interaction: discord.Interaction) -> None:
        await open_forget(interaction, self.view)


class ScheduledButton(discord.ui.Button):
    def __init__(self, on: bool) -> None:
        super().__init__(
            label=SCHEDULED_BUTTON.format(state="on" if on else "off"),
            style=discord.ButtonStyle.success if on else discord.ButtonStyle.secondary,
            row=4,
        )
        self.on = on

    async def callback(self, interaction: discord.Interaction) -> None:
        await change_settings(
            interaction, {"events_create_scheduled": not self.on}, self.view
        )


class ModeSelect(discord.ui.Select):
    def __init__(self, current: str) -> None:
        super().__init__(
            placeholder=MODE_PLACEHOLDER,
            options=[
                discord.SelectOption(label=name, value=name, default=name == current)
                for name in EVENTS_MODES
            ],
            min_values=1,
            max_values=1,
            row=0,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await change_settings(interaction, {"events_mode": self.values[0]}, self.view)


class CategorySelect(discord.ui.ChannelSelect):
    def __init__(self) -> None:
        super().__init__(
            placeholder=CATEGORY_PLACEHOLDER,
            channel_types=[discord.ChannelType.category],
            min_values=0,
            max_values=1,
            row=1,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        picked = self.values[0].id if self.values else None
        await change_settings(interaction, {"events_category_id": picked}, self.view)


class AnnounceSelect(discord.ui.ChannelSelect):
    def __init__(self) -> None:
        super().__init__(
            placeholder=ANNOUNCE_PLACEHOLDER,
            channel_types=[discord.ChannelType.text],
            min_values=0,
            max_values=1,
            row=2,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        picked = self.values[0].id if self.values else None
        await change_settings(interaction, {"events_announce_channel_id": picked}, self.view)


class PingRoleSelect(discord.ui.RoleSelect):
    def __init__(self) -> None:
        super().__init__(placeholder=PING_PLACEHOLDER, min_values=0, max_values=1, row=3)

    async def callback(self, interaction: discord.Interaction) -> None:
        picked = self.values[0].id if self.values else None
        await change_settings(interaction, {"events_ping_role_id": picked}, self.view)


class RoomsButton(discord.ui.Button):
    def __init__(self, row: int = 4) -> None:
        super().__init__(label=ROOMS_BUTTON, style=discord.ButtonStyle.secondary, row=row)

    async def callback(self, interaction: discord.Interaction) -> None:
        await open_rooms(interaction, self.view)


class ForumButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label=FORUM_BUTTON, style=discord.ButtonStyle.secondary, row=3)

    async def callback(self, interaction: discord.Interaction) -> None:
        await open_forum(interaction, self.view)


class ReviewModeSelect(discord.ui.Select):
    def __init__(self, current: str) -> None:
        super().__init__(
            placeholder=REVIEW_MODE_PLACEHOLDER,
            options=[
                discord.SelectOption(label=name, value=name, default=name == current)
                for name in EVENTS_REVIEW_MODES
            ],
            min_values=1,
            max_values=1,
            row=0,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await change_settings(
            interaction, {EVENTS_REVIEW_MODE_KEY: self.values[0]}, self.view, render_forum
        )


class ForumSelect(discord.ui.ChannelSelect):
    def __init__(self) -> None:
        super().__init__(
            placeholder=FORUM_CHANNEL_PLACEHOLDER,
            channel_types=[discord.ChannelType.forum],
            min_values=0,
            max_values=1,
            row=1,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        picked = self.values[0].id if self.values else None
        await change_settings(
            interaction, {EVENTS_FORUM_CHANNEL_KEY: picked}, self.view, render_forum
        )


class MakeForumButton(discord.ui.Button):
    def __init__(self, known: bool) -> None:
        super().__init__(
            label=MAKE_THE_FORUM,
            style=discord.ButtonStyle.secondary if known else discord.ButtonStyle.primary,
            row=2,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await make_the_forum(interaction, self.view)


class PostsWhereSelect(discord.ui.Select):
    def __init__(self, current: str) -> None:
        super().__init__(
            placeholder=POSTS_WHERE_PLACEHOLDER,
            options=[
                discord.SelectOption(label=name, value=name, default=name == current)
                for name in EVENTS_POSTS_WHERES
            ],
            min_values=1,
            max_values=1,
            row=0,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await change_settings(
            interaction, {EVENTS_POSTS_WHERE_KEY: self.values[0]}, self.view, render_rooms
        )


class RoomDeleteSelect(discord.ui.Select):
    def __init__(self, current: str) -> None:
        super().__init__(
            placeholder=ROOM_DELETE_PLACEHOLDER,
            options=[
                discord.SelectOption(label=name, value=name, default=name == current)
                for name in EVENTS_ROOM_DELETE_WHOS
            ],
            min_values=1,
            max_values=1,
            row=1,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await change_settings(
            interaction, {EVENTS_ROOM_DELETE_KEY: self.values[0]}, self.view, render_rooms
        )


class RoomApproverSelect(discord.ui.RoleSelect):
    def __init__(self) -> None:
        super().__init__(placeholder=ROOM_APPROVER_PLACEHOLDER, min_values=0, max_values=1, row=2)

    async def callback(self, interaction: discord.Interaction) -> None:
        picked = self.values[0].id if self.values else None
        await change_settings(
            interaction, {EVENTS_APPROVER_ROLE_KEY: picked}, self.view, render_rooms
        )


class RoomNoticeButton(discord.ui.Button):
    def __init__(self, on: bool) -> None:
        super().__init__(
            label=ROOM_NOTICE_BUTTON.format(state="on" if on else "off"),
            style=discord.ButtonStyle.success if on else discord.ButtonStyle.secondary,
            row=3,
        )
        self.on = on

    async def callback(self, interaction: discord.Interaction) -> None:
        await change_settings(
            interaction, {EVENTS_ROOM_NOTICE_KEY: not self.on}, self.view, render_rooms
        )


class ForgetPick(discord.ui.Select):
    def __init__(self) -> None:
        super().__init__(
            placeholder=FORGET_PLACEHOLDER,
            options=[
                discord.SelectOption(label=words, value=key) for key, words in FORGETTABLE
            ],
            min_values=0,
            max_values=1,
            row=0,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if not self.values:
            await answer(interaction, FORGOT_NOTHING)
            return
        await change_settings(interaction, {self.values[0]: None}, self.view)


class EventPick(discord.ui.Select):
    def __init__(self, rows: list[Any], total: int) -> None:
        super().__init__(
            placeholder=pick_placeholder(len(rows), total),
            options=[
                discord.SelectOption(label=option_label(row), value=str(row["id"]))
                for row in rows
            ],
            min_values=1,
            max_values=1,
            row=2,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await open_card(interaction, int(self.values[0]), self.view)


class CallOffPick(discord.ui.Select):
    def __init__(self, rows: list[Any]) -> None:
        super().__init__(
            placeholder=CALL_ONE_OFF,
            options=[
                discord.SelectOption(label=option_label(row), value=str(row["id"]))
                for row in rows[:SELECT_CAP]
            ],
            min_values=1,
            max_values=1,
            row=1,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await open_cancel_confirm(interaction, int(self.values[0]), self.view)


class CardMoveButton(discord.ui.Button):
    def __init__(self, event_id: int, spec: Any) -> None:
        super().__init__(label=spec.label, style=BUTTON_STYLES[spec.style], row=0)
        self.event_id = event_id
        self.spec = spec

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await still_staff(interaction):
            return
        if self.spec.needs_modal:
            await interaction.response.send_modal(
                NoteModal(
                    interaction.client.get_cog(COG_NAME),
                    self.event_id,
                    self.spec.action,
                    self.view,
                )
            )
            return
        await run_move(interaction, self.event_id, self.spec.action, self.view)


class CardWhereButton(discord.ui.Button):
    """Staff final say: the same three kinds on a card that is already in review."""

    def __init__(self, event_id: int, where: Where, channel: Any = None) -> None:
        super().__init__(
            label=where_button_label(where, channel),
            style=discord.ButtonStyle.secondary,
            row=1,
        )
        self.event_id = event_id
        self.where = where

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await still_staff(interaction):
            return
        await open_where_panel(
            interaction,
            self.where,
            self.view,
            lambda one, where, prev: store_card_where(one, self.event_id, where, prev),
            lambda one, prev: open_card(one, self.event_id, prev),
        )


async def store_card_where(
    interaction: discord.Interaction, event_id: int, where: Where, previous: Any
) -> None:
    """One write, one log row, then the card the change is now on."""
    if not await still_staff(interaction):
        return
    if not await opened(interaction, staff=False):
        return
    bot = interaction.client
    row = await get_event(bot.db, event_id)
    if row is None:
        await render_panel(interaction, previous)
        await interaction.followup.send(
            NO_SUCH_EVENT, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
        )
        return
    await set_where(bot.db, event_id, where)
    await log_action(
        bot,
        interaction.guild,
        "event.edited",
        actor=interaction.user,
        target=row["requester_id"],
        details={"event_id": event_id, "where_kind": where.kind},
    )
    await render_card(interaction, event_id, previous)


class NoteModal(PanelNoteModal):
    def __init__(self, cog: Events, event_id: int, kind: str, previous: Any = None) -> None:
        self.cog = cog
        self.event_id = event_id
        self.kind = kind
        self.previous = previous
        super().__init__(
            title=NOTE_TITLES[kind],
            label=NOTE_LABELS[kind],
            max_length=NOTE_LIMITS[kind],
            required=NOTE_REQUIRED[kind],
            on_submit=self.note_submit,
        )

    async def note_submit(self, interaction: discord.Interaction, text: str) -> None:
        await self.cog.note_submit(interaction, self.event_id, self.kind, text, self.previous)


class ZoneModal(WhenZoneModal):
    def __init__(
        self, cog: Events, current: str = "", previous: Any = None, back: Any = None
    ) -> None:
        self.cog = cog
        self.previous = previous
        self.back = back
        super().__init__(current=current, on_submit=self.zone_submit)

    async def zone_submit(self, interaction: discord.Interaction, given: str) -> None:
        await self.cog.zone_submit(interaction, given, self.previous, self.back)


class NumbersModal(AnswersErrors, discord.ui.Modal, title=NUMBERS_MODAL_TITLE):
    retention = discord.ui.TextInput(label=EVENT_NUMBERS_LABELS["retention"], max_length=6)
    late = discord.ui.TextInput(label=EVENT_NUMBERS_LABELS["late"], max_length=6)

    def __init__(
        self, cog: Events, retention: Any = None, late: Any = None, previous: Any = None
    ) -> None:
        super().__init__()
        self.cog = cog
        self.previous = previous
        self.retention.default = str(retention) if retention is not None else None
        self.late.default = str(late) if late is not None else None

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await self.cog.numbers_submit(
            interaction, str(self.retention), str(self.late), self.previous
        )


class DenyModal(AnswersErrors, discord.ui.Modal, title="Why not?"):
    reason = discord.ui.TextInput(
        label="One line the requester will be sent",
        style=discord.TextStyle.paragraph,
        max_length=DENY_LIMIT,
    )

    def __init__(self, event_id: int) -> None:
        super().__init__()
        self.event_id = event_id

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        await decide(interaction, self.event_id, DENIED, clamp(self.reason, DENY_LIMIT))


class DecisionButton(
    SafeDynamicItem, discord.ui.DynamicItem[discord.ui.Button], template=DECISION_TEMPLATE
):
    def __init__(self, event_id: int, action: str, label: str | None = None) -> None:
        self.event_id = event_id
        self.action = action
        super().__init__(
            discord.ui.Button(
                label=label or DECISION_LABELS[action],
                style=DECISION_STYLES[action],
                custom_id=decision_id(event_id, action),
            )
        )

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: Any, match: re.Match):
        return cls(int(match["event_id"]), match["action"])

    async def on_click(self, interaction: discord.Interaction) -> None:
        if self.action == DELETE_ROOM:
            await ask_to_delete_room(interaction, self.event_id)
            return
        if self.action == MAKE_REQUEST:
            await make_it_a_request(interaction, self.event_id)
            return
        row = await decision_context(interaction, self.event_id)
        if row is None:
            return
        wanted = APPROVED if self.action == "approve" else DENIED
        if not can_transition(row["status"], wanted):
            await interaction.response.send_message(
                EVENT_ALREADY_DECIDED.format(event_id=self.event_id, status=row["status"]),
                ephemeral=True,
            )
            return
        if self.action == "deny":
            await interaction.response.send_modal(DenyModal(self.event_id))
            return
        await interaction.response.defer(ephemeral=True)
        await decide(interaction, self.event_id, APPROVED)


async def ask_to_delete_room(interaction: discord.Interaction, event_id: int) -> None:
    """The gate, in words: the approver role or staff open the box, the host is told why not."""
    row = await decision_context(interaction, event_id, staff=False)
    if row is None:
        return
    store = interaction.client.store
    words = place_words(row)
    if not may_delete_room(store, interaction.guild.id, interaction.user):
        said = (
            words.not_staff
            if interaction.user.id == row["requester_id"]
            else store.staff_refusal(interaction.guild.id)
        )
        await interaction.response.send_message(said, ephemeral=True)
        return
    await interaction.response.send_modal(RoomDeleteModal(event_id, words))


async def said_after_the_room(interaction: discord.Interaction, said: str) -> None:
    try:
        await interaction.followup.send(
            said, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
        )
    except Exception as exc:
        log.debug("events: could not answer after removing a room: %s", exc)


async def remove_this_room(
    interaction: discord.Interaction, event_id: int, note: str
) -> None:
    """Deferred first, because a reply into a channel that is about to go raises."""
    bot = interaction.client
    await interaction.response.defer(ephemeral=True)
    fresh = await get_event(bot.db, event_id)
    if fresh is None:
        await said_after_the_room(interaction, NO_SUCH_EVENT)
        return
    words = place_words(fresh)
    if fresh["review_channel_id"] is None:
        await said_after_the_room(interaction, words.already_gone.format(event_id=event_id))
        return
    if fresh["review_channel_id"] != interaction.channel_id:
        await said_after_the_room(interaction, words.not_this_event.format(event_id=event_id))
        return
    said, _ = await delete_room(
        bot, interaction.guild, fresh, by=interaction.user, note=note or None
    )
    await said_after_the_room(interaction, said)


class RoomDeleteModal(PanelNoteModal):
    def __init__(self, event_id: int, words: Any = PLACE_WORDS[ROOM]) -> None:
        self.event_id = event_id
        super().__init__(
            title=words.modal_title,
            label=ROOM_DELETE_LABEL,
            max_length=CANCEL_NOTE_LIMIT,
            required=False,
            on_submit=self.room_submit,
        )

    async def room_submit(self, interaction: discord.Interaction, text: str) -> None:
        await remove_this_room(interaction, self.event_id, text)


class EventTextModal(AnswersErrors, discord.ui.Modal, title=TEXT_MODAL_TITLE):
    """Two boxes with no failure path: what is typed lands on the draft, which judges it."""

    event_title = discord.ui.TextInput(label="Title", max_length=TITLE_LIMIT, required=False)
    description = discord.ui.TextInput(
        label="What is it?",
        style=discord.TextStyle.paragraph,
        max_length=DESCRIPTION_LIMIT,
        required=False,
    )

    def __init__(self, previous: Any) -> None:
        super().__init__()
        self.previous = previous
        self.event_title.default = previous.fields.title or None
        self.description.default = previous.fields.description or None

    async def on_submit(self, interaction: discord.Interaction) -> None:
        fields = self.previous.fields
        fields.title = clamp(self.event_title, TITLE_LIMIT)
        fields.description = clamp(self.description, DESCRIPTION_LIMIT)
        await open_draft(interaction, fields, self.previous)


class Events(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.last_ok_at: dict[str, str | None] = {name: None for name in LOOP_NAMES}
        self.last_error: dict[str, str | None] = {name: None for name in LOOP_NAMES}
        self._missing_since: dict[int, str] = {}

    async def cog_load(self) -> None:
        self.bot.add_dynamic_items(DecisionButton)
        if not self.bot.db.is_connected:
            return
        await self.reconcile_events()
        self._golive_loop.start()
        self._reconcile_loop.start()

    async def cog_unload(self) -> None:
        self._golive_loop.cancel()
        self._reconcile_loop.cancel()

    def loop_health(self, name: str) -> tuple[str | None, str | None]:
        key = name.removeprefix("_").removesuffix("_loop")
        if key not in LOOP_NAMES:
            return (None, None)
        return (self.last_ok_at[key], self.last_error[key])

    def loop_failed(self, name: str, exc: BaseException, loop: Any) -> None:
        """A loop that raised is restarted, and its failure is on the record until it is not."""
        self.last_error[name] = f"{now_iso()} · {type(exc).__name__}: {exc}"
        log.exception("events: the %s loop raised and is being restarted", name, exc_info=exc)
        loop.restart()

    @tasks.loop(minutes=GOLIVE_MINUTES)
    async def _golive_loop(self) -> None:
        if self.bot.db.is_connected:
            await self.run_due_events()
        self.last_ok_at["golive"] = now_iso()

    @_golive_loop.before_loop
    async def _before_golive(self) -> None:
        await wait_ready(self.bot, self._golive_broke)

    @_golive_loop.error
    async def _golive_broke(self, exc: BaseException) -> None:
        self.loop_failed("golive", exc, self._golive_loop)

    @tasks.loop(minutes=RECONCILE_MINUTES)
    async def _reconcile_loop(self) -> None:
        if self.bot.db.is_connected:
            await self.reconcile_events()
        self.last_ok_at["reconcile"] = now_iso()

    @_reconcile_loop.before_loop
    async def _before_reconcile(self) -> None:
        await wait_ready(self.bot, self._reconcile_broke)

    @_reconcile_loop.error
    async def _reconcile_broke(self, exc: BaseException) -> None:
        self.loop_failed("reconcile", exc, self._reconcile_loop)

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        if self.bot.db.is_connected:
            await self.reconcile_events()

    async def run_due_events(self) -> None:
        """Approved events that have started go live; live ones that have finished are done."""
        now = datetime.now(UTC)
        stamp = now.isoformat()
        seen = {guild.id: guild for guild in getattr(self.bot, "guilds", ())}
        for row in await due_events(self.bot.db, APPROVED, "starts_at", stamp):
            guild = seen.get(row["guild_id"])
            if guild is not None:
                await self._go_live(guild, row, now)
        for row in await due_events(self.bot.db, LIVE, "ends_at", stamp):
            guild = seen.get(row["guild_id"])
            if guild is not None:
                await self._finish(guild, row)

    async def _go_live(self, guild: Any, row: Any, now: datetime) -> None:
        async with event_lock(self.bot, row["id"]):
            fresh = await get_event(self.bot.db, row["id"])
            if fresh is None or not can_transition(fresh["status"], LIVE):
                return
            finishes = parse_ts(fresh["ends_at"])
            if finishes is not None and finishes <= now:
                await self._missed(guild, fresh)
                return
            starts = parse_ts(fresh["starts_at"])
            late = int((now - starts).total_seconds() // 60) if starts is not None else 0
            cap = int(self.bot.store.get(guild.id, "events_max_late_minutes") or 0)
            await set_status(self.bot.db, fresh["id"], LIVE)
            fresh = await get_event(self.bot.db, fresh["id"])
            if review_kind(fresh) == POST:
                await retag_post(self.bot, guild, fresh)
            if late > cap:
                await log_action(
                    self.bot,
                    guild,
                    "event.announce_skipped_late",
                    target=fresh["requester_id"],
                    details={
                        "event_id": fresh["id"],
                        "late_minutes": late,
                        "allowed_minutes": cap,
                    },
                )
                return
            await post_event(
                self.bot,
                guild,
                fresh,
                golive_text(fresh["title"], self.bot.store.get(guild.id, "events_ping_role_id")),
                None,
                "go_live",
            )

    async def _missed(self, guild: Any, row: Any) -> None:
        """An approved event whose end has already gone by is never announced, only recorded."""
        await set_status(self.bot.db, row["id"], DONE)
        drop_lock(self.bot, row["id"])
        await log_action(
            self.bot,
            guild,
            "event.missed",
            target=row["requester_id"],
            details={"event_id": row["id"], "title": row["title"]},
        )
        fresh = await get_event(self.bot.db, row["id"])
        member = guild.get_member(row["requester_id"])
        await tell_or_log(
            self.bot,
            guild,
            member,
            fresh,
            DM_MISSED.format(title=row["title"], guild=guild.name),
        )
        await rename_channel(
            self.bot,
            guild,
            fresh,
            DONE,
            getattr(member, "display_name", str(row["requester_id"])),
        )

    async def _finish(self, guild: Any, row: Any) -> None:
        async with event_lock(self.bot, row["id"]):
            fresh = await get_event(self.bot.db, row["id"])
            if fresh is None or not can_transition(fresh["status"], DONE):
                return
            await set_status(self.bot.db, fresh["id"], DONE)
            drop_lock(self.bot, fresh["id"])
            await log_action(
                self.bot,
                guild,
                "event.done",
                target=fresh["requester_id"],
                details={"event_id": fresh["id"]},
            )
            member = guild.get_member(fresh["requester_id"])
            await rename_channel(
                self.bot,
                guild,
                fresh,
                DONE,
                getattr(member, "display_name", str(fresh["requester_id"])),
            )
            if posts_in_room(self.bot.store, guild.id):
                await post_to_room(
                    self.bot,
                    guild,
                    fresh,
                    ENDED_TEXT.format(title=clamp(fresh["title"], TITLE_LIMIT)),
                    None,
                    "ended",
                    ping=False,
                )

    async def reconcile_events(self) -> None:
        """Events whose review channel has gone are cancelled; finished ones are tidied away."""
        now = datetime.now(UTC)
        for guild in list(getattr(self.bot, "guilds", ())):
            if getattr(guild, "unavailable", False):
                log.info("events: %s is unavailable, so nothing about it is reconciled", guild.id)
                continue
            for row in await events_by_status(self.bot.db, guild.id, OPEN_STATUSES):
                await self._recheck(guild, row, now)
            await self._sweep_finished(guild, now)

    async def _recheck(self, guild: Any, row: Any, now: datetime) -> None:
        if parse_ts(row["starts_at"]) is None:
            await self._cancel(guild, row, "unreadable_start")
            return
        channel_id = row["review_channel_id"]
        if channel_id is None:
            created = parse_ts(row["created_at"])
            if created is not None and now - created < timedelta(minutes=ORPHAN_GRACE_MINUTES):
                return
            await self._cancel(guild, row, "never_got_a_channel")
            return
        room = review_place(self.bot, guild, row)
        if room is not None:
            own_room(self.bot, room)
            self._missing_since.pop(row["id"], None)
            return
        if review_kind(row) == POST:
            # A post that auto-archives leaves discord.py's thread cache, and a cancel from
            # that would kill an event for being early. `on_thread_delete` is what says gone.
            log.debug(
                "events: post %s for event %s is not in the cache; leaving it alone",
                channel_id,
                row["id"],
            )
            return
        if row["id"] not in self._missing_since:
            self._missing_since[row["id"]] = now_iso()
            log.info(
                "events: channel %s for event %s is missing; deciding at the next pass",
                channel_id,
                row["id"],
            )
            return
        self._missing_since.pop(row["id"], None)
        await self._cancel(guild, row, "review_channel_gone")

    async def _cancel(self, guild: Any, row: Any, reason: str, *, by: int | None = None) -> None:
        await cancel_event(self.bot, guild, row, reason, by=by)

    async def _sweep_finished(self, guild: Any, now: datetime) -> None:
        store = self.bot.store
        days = int(store.get(guild.id, "events_channel_retention_days") or 0)
        minutes = int(store.get(guild.id, EVENTS_TEST_RETENTION_KEY) or 0)
        guard = getattr(self.bot, "guard", None)
        testing = guard is not None
        kept = timedelta(minutes=minutes) if testing else timedelta(days=days)
        for row in await events_by_status(self.bot.db, guild.id, SWEPT_STATUSES):
            channel = review_place(self.bot, guild, row)
            if channel is None:
                if row["review_channel_id"] and review_kind(row) == ROOM:
                    await forget_room(self.bot, guild, row)
                continue
            own_room(self.bot, channel)
            if review_kind(row) == POST and not testing:
                await self._archive_post(guild, row, channel)
                continue
            finished = swept_anchor(row)
            if finished is None or now - finished < kept:
                continue
            if guard is not None and not guard.allows_place(channel):
                await log_action(
                    self.bot,
                    guild,
                    "event.would_delete_channel",
                    details={"event_id": row["id"], "channel_id": channel.id},
                )
                continue
            said = SWEEP_KEPT_MINUTES if testing else SWEEP_KEPT_DAYS
            try:
                await channel.delete(
                    reason=said.format(event_id=row["id"], kept=minutes if testing else days)
                )
            except NETWORK_ERRORS as exc:
                log.warning("events: could not delete %s: %s", channel.id, exc)
                continue
            disown_room(self.bot, channel)
            await set_review(
                self.bot.db,
                row["id"],
                None,
                row["review_message_id"],
                row["card_channel_id"],
            )
            await log_action(
                self.bot,
                guild,
                "event.channel_deleted",
                details={
                    "event_id": row["id"],
                    "channel_id": channel.id,
                    **({"kept_minutes": minutes} if testing else {"kept_days": days}),
                },
            )

    async def _archive_post(self, guild: Any, row: Any, place: Any) -> None:
        """Retention is a ROOM rule: a settled post is tagged and archived, never deleted."""
        if getattr(place, "archived", False):
            return
        await retag_post(self.bot, guild, row)
        await log_action(
            self.bot,
            guild,
            "event.post_archived",
            details={"event_id": row["id"], "channel_id": place.id, "kind": POST},
        )

    @commands.Cog.listener()
    async def on_thread_delete(self, thread: discord.Thread) -> None:
        """A post somebody deleted by hand settles its event, as a deleted room does."""
        if not self.bot.db.is_connected:
            return
        disown_room(self.bot, thread)
        row = await event_for_channel(self.bot.db, thread.id)
        if row is None or review_kind(row) != POST:
            return
        if row["status"] in OPEN_STATUSES:
            await self._cancel(thread.guild, row, "review_channel_deleted")
            return
        await forget_room(self.bot, thread.guild, row)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel) -> None:
        if not self.bot.db.is_connected:
            return
        guild = channel.guild
        for key, kind in (
            ("events_category_id", "event.category_forgotten"),
            ("events_announce_channel_id", "event.announce_channel_forgotten"),
            (EVENTS_FORUM_CHANNEL_KEY, "event.forum_forgotten"),
        ):
            if channel.id == self.bot.store.get(guild.id, key):
                await self.bot.store.clear(guild.id, key)
                await log_action(self.bot, guild, kind, details={"channel_id": channel.id})
        disown_room(self.bot, channel)
        row = await event_for_channel(self.bot.db, channel.id)
        if row is not None and row["status"] in OPEN_STATUSES:
            await self._cancel(guild, row, "review_channel_deleted")

    def health_lines(self) -> list[str]:
        """Checklist 9: the loops report last success and last error, never `is_running`."""
        lines = []
        for name in LOOP_NAMES:
            ok = self.last_ok_at[name] or "never yet"
            broke = self.last_error[name]
            trouble = f" · last error {broke}" if broke else " · no errors"
            lines.append(f"**{name} loop** — last finished {ok}{trouble}")
        return lines

    async def _database_ready(self, interaction: discord.Interaction) -> bool:
        if self.bot.db.is_connected:
            return True
        log.warning("events: refused a command — the database is not connected")
        await answer(interaction, DB_UNAVAILABLE)
        return False

    async def _ready(self, interaction: discord.Interaction) -> bool:
        if interaction.guild is None:
            await answer(interaction, GUILD_ONLY)
            return False
        return await self._database_ready(interaction)

    @app_commands.command(
        name="event", description="Propose an event, or run the ones already on the go"
    )
    async def event(self, interaction: discord.Interaction) -> None:
        if not await self._ready(interaction):
            return
        embed, view = await build_panel(self.bot, interaction.guild, interaction.user)
        await interaction.response.send_message(
            embed=embed,
            view=view,
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        view.message = await interaction.original_response()

    async def zone_submit(
        self,
        interaction: discord.Interaction,
        given: str,
        previous: Any = None,
        back: Any = None,
    ) -> None:
        """Store it or refuse, then render whatever asked — the panel, or the draft it left."""
        if not await opened(interaction, staff=False):
            return
        _, said = await store_zone(self.bot.db, interaction.user.id, given)
        if back is None:
            await render_panel(interaction, previous)
        else:
            await back(interaction, previous)
        await interaction.followup.send(
            said, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
        )

    async def note_submit(
        self,
        interaction: discord.Interaction,
        event_id: int,
        kind: str,
        text: str,
        previous: Any = None,
    ) -> None:
        """What Deny and Call it off both do once their one line is in."""
        if not await still_staff(interaction):
            return
        if not await opened(interaction, staff=False):
            return
        if kind == "deny":
            said, fresh = await apply_decision(
                self.bot, interaction.guild, event_id, DENIED, interaction.user, text
            )
            await finish_card(interaction, event_id, said, fresh, previous)
            return
        row = await get_event(self.bot.db, event_id)
        if row is None:
            await render_panel(interaction, previous)
            await interaction.followup.send(
                NO_SUCH_EVENT, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
            )
            return
        said, fresh = await cancel_for(
            self.bot, interaction.guild, row, interaction.user, note=text or None
        )
        await finish_card(interaction, event_id, said, fresh, previous)

    async def numbers_submit(
        self,
        interaction: discord.Interaction,
        retention: str,
        late: str,
        previous: Any = None,
    ) -> None:
        """The two numbers `/event settings` clamped, clamped by the same bounds."""
        if not await still_staff(interaction):
            return
        changes, why = checked_numbers(retention, late)
        if changes is None:
            await answer(interaction, why)
            return
        await change_settings(interaction, changes, previous)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Events(bot))


__all__ = [
    "BackButton",
    "CallOffPick",
    "CardMoveButton",
    "CardWhereButton",
    "DecisionButton",
    "DenyModal",
    "EventDraftPanel",
    "EventPick",
    "EventTextModal",
    "EventView",
    "Events",
    "ForgetPick",
    "LogsButton",
    "ModeSelect",
    "NoteModal",
    "NumbersModal",
    "PostsWhereSelect",
    "ProposeButton",
    "RefreshButton",
    "RoomApproverSelect",
    "RoomDeleteModal",
    "RoomDeleteSelect",
    "RoomNoticeButton",
    "RoomsButton",
    "SettingsButton",
    "SubmitButton",
    "TextButton",
    "WhereButton",
    "WhereClearButton",
    "WhereModal",
    "WhereOtherButton",
    "WherePanel",
    "WhereSelect",
    "ZoneButton",
    "ZoneModal",
    "ask_to_delete_room",
    "back_to_panel",
    "build_card",
    "build_draft",
    "build_panel",
    "build_rooms",
    "build_settings",
    "change_settings",
    "close_card",
    "confirm_cancel",
    "decide",
    "decision_context",
    "decision_id",
    "finish_card",
    "open_cancel_confirm",
    "open_card",
    "open_draft",
    "open_rooms",
    "open_settings",
    "open_where_panel",
    "open_zone_panel",
    "remove_this_room",
    "render_card",
    "render_draft",
    "render_panel",
    "render_rooms",
    "render_settings",
    "review_view",
    "room_notice_view",
    "run_move",
    "store_card_where",
    "submit_draft",
    "take_draft_where",
]
