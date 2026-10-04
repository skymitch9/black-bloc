from __future__ import annotations

import asyncio
import logging
import re
from datetime import timedelta
from typing import Any

import discord

from ... import marathon as mt
from ... import marathon_events as me
from ... import marathon_hosts as mh
from ... import marathon_inbox as mi
from ... import marathon_overlay as mo
from ... import marathon_ping as mping
from ... import marathon_public as mp
from ... import marathon_spotlight as ms
from ... import marathon_thread_controls as mtc
from ... import spotlight as spot
from ...actionlog import log_action
from ...command_errors import SafeDynamicItem
from ...golive import parse_ts
from ...logkinds import VIA_DISCORD
from ...marathon_channels import takes_marathons
from ...panels import Outcome, answer, refusal, still_staff
from ...settings_store import (
    DB_UNAVAILABLE,
    DEFAULT_TIMEZONE_KEY,
    MARATHON_CONTROLS_ALREADY_ON_KEY,
    MARATHON_CONTROLS_ANNOUNCE_OFF_KEY,
    MARATHON_CONTROLS_ANNOUNCE_ON_KEY,
    MARATHON_CONTROLS_CANCELLED_KEY,
    MARATHON_CONTROLS_CANNOT_WAIT_KEY,
    MARATHON_CONTROLS_EVENT_OFF_KEY,
    MARATHON_CONTROLS_EVENT_ON_KEY,
    MARATHON_CONTROLS_HELP_KEY,
    MARATHON_CONTROLS_HIGHLIGHT_OFF_KEY,
    MARATHON_CONTROLS_HIGHLIGHT_ON_KEY,
    MARATHON_CONTROLS_KEPT_REFUSED_KEY,
    MARATHON_CONTROLS_NO_CHANNEL_KEY,
    MARATHON_CONTROLS_NO_END_KEY,
    MARATHON_CONTROLS_OVERLAY_OFF_KEY,
    MARATHON_CONTROLS_OVERLAY_ON_KEY,
    MARATHON_CONTROLS_PING_OFF_KEY,
    MARATHON_CONTROLS_PING_ON_KEY,
    MARATHON_CONTROLS_RUNS_OFF_KEY,
    MARATHON_CONTROLS_RUNS_ON_KEY,
    MARATHON_CONTROLS_SPOTLIGHT_KEPT_KEY,
    MARATHON_CONTROLS_SPOTLIGHT_NONE_KEY,
    MARATHON_CONTROLS_SPOTLIGHT_OFF_KEY,
    MARATHON_CONTROLS_SPOTLIGHT_ON_KEY,
    MARATHON_CONTROLS_SPOTLIGHT_WAITING_KEY,
    MARATHON_CONTROLS_STARTED_KEY,
    MARATHON_CONTROLS_WAITS_KEY,
)
from ...spotlight import reason_of, window_when
from ...timezones import DEFAULT_TZ, zone
from .marathon import (
    MODE_OFF,
    NO_SUCH,
    _cell,
    cog_of,
    get_marathon,
    now_for,
    update_marathon,
)
from .marathon import mode_of as posts_mode_of
from .marathon_announce import announces
from .marathon_channels import locked, marathons_on_channel
from .marathon_events import set_event_mode
from .marathon_hosts import set_switch
from .marathon_inbox import find_channel, home_now, reopened, words
from .marathon_role_ping import status_line as role_ping_line
from .marathon_spotlight import (
    _row_of,
    after_staff_dim,
    enabled,
    lead_of,
    set_spotlight_mode,
    state_for,
    tail_of,
)
from .spotlight import changed_spotlight, set_spotlight, update_channel

log = logging.getLogger(__name__)

NO_CHANNEL_CODE = "no_channel"
KEPT_CODE = "kept"
NO_END_CODE = "no_end"
CANNOT_WAIT_CODE = "cannot_wait"
GONE_CODE = "gone"
LABEL_KEYS = {
    (mtc.EVENT, mtc.ON): MARATHON_CONTROLS_EVENT_ON_KEY,
    (mtc.EVENT, mtc.OFF): MARATHON_CONTROLS_EVENT_OFF_KEY,
    (mtc.RUNS, mtc.ON): MARATHON_CONTROLS_RUNS_ON_KEY,
    (mtc.RUNS, mtc.OFF): MARATHON_CONTROLS_RUNS_OFF_KEY,
    (mtc.SPOTLIGHT, mtc.SPOT_ON): MARATHON_CONTROLS_SPOTLIGHT_ON_KEY,
    (mtc.SPOTLIGHT, mtc.SPOT_OFF): MARATHON_CONTROLS_SPOTLIGHT_OFF_KEY,
    (mtc.SPOTLIGHT, mtc.SPOT_KEPT): MARATHON_CONTROLS_SPOTLIGHT_KEPT_KEY,
    (mtc.SPOTLIGHT, mtc.SPOT_NONE): MARATHON_CONTROLS_SPOTLIGHT_NONE_KEY,
    (mtc.SPOTLIGHT, mtc.SPOT_WAITING): MARATHON_CONTROLS_SPOTLIGHT_WAITING_KEY,
    (mtc.HIGHLIGHT, mtc.ON): MARATHON_CONTROLS_HIGHLIGHT_ON_KEY,
    (mtc.HIGHLIGHT, mtc.OFF): MARATHON_CONTROLS_HIGHLIGHT_OFF_KEY,
    (mtc.PING, mtc.ON): MARATHON_CONTROLS_PING_ON_KEY,
    (mtc.PING, mtc.OFF): MARATHON_CONTROLS_PING_OFF_KEY,
    (mtc.ANNOUNCE, mtc.ON): MARATHON_CONTROLS_ANNOUNCE_ON_KEY,
    (mtc.ANNOUNCE, mtc.OFF): MARATHON_CONTROLS_ANNOUNCE_OFF_KEY,
    (mtc.OVERLAY, mtc.ON): MARATHON_CONTROLS_OVERLAY_ON_KEY,
    (mtc.OVERLAY, mtc.OFF): MARATHON_CONTROLS_OVERLAY_OFF_KEY,
}
STYLES = {
    mtc.ON: discord.ButtonStyle.success,
    mtc.OFF: discord.ButtonStyle.secondary,
}


def overlay_switch(bot: Any, guild_id: int, marathon: Any) -> bool | None:
    """The Event schedule button's state — None (no button) unless a sheet matches."""
    from .marathon_hosts import switch_state

    if mo.state_of(marathon) is None:
        return None
    return bool(switch_state(bot, guild_id, marathon, mh.OVERLAY)["on"])


def shown_lock(cog: Any, marathon_id: Any) -> asyncio.Lock:
    locks = cog.__dict__.setdefault("controls_locks", {})
    key = int(marathon_id)
    found = locks.get(key)
    if found is None:
        found = locks[key] = asyncio.Lock()
    return found


def shown_cache(cog: Any) -> dict[int, Any]:
    return cog.__dict__.setdefault("controls_shown", {})


async def rendered(bot: Any, guild: Any, marathon: Any) -> tuple[str, tuple, tuple[str, ...]]:
    """`(content, controls, labels)` from the row, the channel row and the keys."""
    _row, state = await state_for(bot, guild, marathon)
    controls = mtc.controls(
        me.mode_of(marathon),
        state["state"],
        mp.highlights(marathon),
        mping.pings_role(marathon),
        announces(bot, guild.id, marathon),
        overlay_switch(bot, guild.id, marathon),
    )
    starts = label_moment(state.get("starts"), bot.store.get(guild.id, DEFAULT_TIMEZONE_KEY))
    labels = tuple(
        mtc.label(words(bot, guild.id, LABEL_KEYS[(one.action, one.word)], starts=starts))
        for one in controls
    )
    content = words(bot, guild.id, MARATHON_CONTROLS_HELP_KEY, marathon=marathon["name"])
    if state["state"] == ms.NO_CHANNEL:
        content += "\n" + words(
            bot, guild.id, MARATHON_CONTROLS_NO_CHANNEL_KEY, marathon=marathon["name"]
        )
    role_line = role_ping_line(bot, guild, marathon)
    if role_line:
        content += "\n" + role_line
    return (content, controls, labels)


def label_moment(value: Any, tz_name: Any) -> str:
    """A button cannot carry a Discord timestamp, so the date is written in the server's zone."""
    when = parse_ts(value)
    if when is None:
        return "—"
    local = when.astimezone(zone(tz_name) or zone(DEFAULT_TZ))
    return f"{window_when(value, tz_name)} {local.tzname() or ''}".strip()


def view_of(marathon_id: Any, controls: tuple, labels: tuple[str, ...]) -> discord.ui.View:
    view = discord.ui.View(timeout=None)
    for one, text in zip(controls, labels, strict=True):
        view.add_item(ControlButton(marathon_id, one.action, one.to, text, one.disabled, one.word))
    return view


async def post_controls(bot: Any, guild: Any, marathon: Any, thread: Any) -> Any:
    """Right after the thread's opening, with the marathon's lock held: posted, stored, pinned."""
    guard = getattr(bot, "guard", None)
    if guard is not None and not guard.allows_channel(thread.id):
        return None
    content, controls, labels = await rendered(bot, guild, marathon)
    base = {"marathon_id": marathon["id"], "name": marathon["name"], "thread_id": int(thread.id)}
    try:
        message = await thread.send(
            content,
            view=view_of(marathon["id"], controls, labels),
            allowed_mentions=discord.AllowedMentions.none(),
        )
    except Exception as exc:
        await log_action(
            bot,
            guild,
            "marathon.controls_failed",
            details=base | {"step": "post", "reason": reason_of(exc)},
        )
        return None
    await update_marathon(bot.db, marathon["id"], controls_message_id=int(message.id))
    cog = cog_of(bot)
    if cog is not None:
        shown_cache(cog)[int(marathon["id"])] = (
            int(thread.id),
            int(message.id),
            (content, controls, labels),
        )
    pinned = True
    try:
        await message.pin(reason=mtc.POSTED_REASON)
    except Exception as exc:
        pinned = False
        await log_action(
            bot,
            guild,
            "marathon.controls_failed",
            details=base | {"step": "pin", "reason": reason_of(exc)},
        )
    await log_action(
        bot,
        guild,
        "marathon.controls_posted",
        details=base | {"message_id": int(message.id), "pinned": pinned},
    )
    return message


def has_home(bot: Any, guild: Any, marathon: Any) -> bool:
    home = home_now(bot, guild)
    return (
        home is not None
        and marathon is not None
        and mi.is_tracked(marathon)
        and bool(_cell(marathon, "thread_id"))
        and _cell(marathon, "thread_home") == home
    )


async def message_in(thread: Any, message_id: int) -> Any:
    partial = getattr(thread, "get_partial_message", None)
    if callable(partial):
        return partial(message_id)
    return await thread.fetch_message(message_id)


async def refresh_controls(bot: Any, guild: Any, marathon_id: Any) -> str:
    """Edit in place when what it shows changed; never posts. `same`, `edited`, `lost`,
    `skipped` or `failed`."""
    cog = cog_of(bot)
    if cog is None or guild is None:
        return "skipped"
    key = int(marathon_id)
    async with shown_lock(cog, key):
        fresh = await get_marathon(bot.db, guild.id, key)
        if not has_home(bot, guild, fresh) or not _cell(fresh, "controls_message_id"):
            return "skipped"
        thread_id, message_id = int(fresh["thread_id"]), int(fresh["controls_message_id"])
        shown = await rendered(bot, guild, fresh)
        if shown_cache(cog).get(key) == (thread_id, message_id, shown):
            return "same"
        thread, _lost = await find_channel(bot, guild, thread_id)
        if thread is None:
            return "skipped"
        await reopened(thread)
        content, controls, labels = shown
        try:
            message = await message_in(thread, message_id)
            await message.edit(
                content=content,
                view=view_of(key, controls, labels),
                allowed_mentions=discord.AllowedMentions.none(),
            )
        except (discord.NotFound, LookupError):
            await update_marathon(bot.db, key, controls_message_id=None)
            shown_cache(cog).pop(key, None)
            await log_action(
                bot,
                guild,
                "marathon.controls_lost",
                details={"marathon_id": key, "thread_id": thread_id, "message_id": message_id},
            )
            return "lost"
        except Exception as exc:
            log.warning("marathon: could not edit controls %s — %s", message_id, reason_of(exc))
            return "failed"
        shown_cache(cog)[key] = (thread_id, message_id, shown)
        return "edited"


async def sync_controls(bot: Any, guild: Any, marathon: Any) -> None:
    """The tick, with the marathon's lock held: re-render, or post once for a tracked thread
    that has none (an id compare, no Discord call while it has one and nothing changed)."""
    if not has_home(bot, guild, marathon):
        return
    if _cell(marathon, "controls_message_id"):
        if await refresh_controls(bot, guild, marathon["id"]) != "lost":
            return
        marathon = await get_marathon(bot.db, guild.id, marathon["id"])
    thread, _lost = await find_channel(bot, guild, marathon["thread_id"])
    if thread is None:
        return
    await post_controls(bot, guild, marathon, await reopened(thread))


async def controls_changed(bot: Any, guild: Any, marathon_id: Any) -> None:
    """The hook the canonical writers call; a failure here never breaks the write."""
    try:
        await refresh_controls(bot, guild, marathon_id)
    except Exception as exc:
        log.warning("marathon: controls re-render failed for %s — %s", marathon_id, exc)


async def row_changed(bot: Any, guild: Any, spotlight_id: Any) -> None:
    if cog_of(bot) is None or guild is None or not spotlight_id:
        return
    try:
        marathons = await marathons_on_channel(bot.db, guild.id, spotlight_id)
    except Exception as exc:
        log.warning("marathon: controls could not read the channel's marathons — %s", exc)
        return
    for one in marathons:
        await controls_changed(bot, guild, one["id"])


# --- the three moves ---------------------------------------------------------------------------


def login_of(row: Any) -> str:
    return str(_cell(row, "twitch_login") or "")


def no_channel(bot: Any, guild: Any, marathon: Any) -> Outcome:
    return refusal(
        words(bot, guild.id, MARATHON_CONTROLS_NO_CHANNEL_KEY, marathon=marathon["name"]),
        NO_CHANNEL_CODE,
        409,
    )


def no_end(bot: Any, guild: Any, marathon: Any) -> Outcome:
    return refusal(
        words(bot, guild.id, MARATHON_CONTROLS_NO_END_KEY, marathon=marathon["name"]),
        NO_END_CODE,
        409,
    )


async def start_spotlight(
    bot: Any, guild: Any, actor: Any, marathon: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    """On now, held by this marathon until its span end plus the tail, through the one write
    the Go-live doors use; a marathon whose follow was off follows again."""
    row = await _row_of(bot, guild, marathon)
    if row is None:
        return no_channel(bot, guild, marathon)
    if spot.is_spotlit(row):
        return Outcome(
            True, words(bot, guild.id, MARATHON_CONTROLS_ALREADY_ON_KEY, channel=login_of(row))
        )
    tail = tail_of(bot, guild.id)
    span = ms.span_of(marathon)
    if span is None or ms.reach_end(span, tail) <= now_for(bot):
        return no_end(bot, guild, marathon)
    if not ms.in_reach(span, now_for(bot), lead_of(bot, guild.id), tail):
        return await start_later(bot, guild, actor, marathon, row, span, via=via)
    said: list[str] = []
    if ms.mode_of(marathon) == ms.OFF:
        moved = await set_spotlight_mode(bot, guild, actor, marathon, ms.FOLLOW, via=via)
        said.append(moved.message)
    async with locked(cog_of(bot), marathon["id"]):
        fresh = await get_marathon(bot.db, guild.id, marathon["id"]) or marathon
        row = await _row_of(bot, guild, fresh)
        span = ms.span_of(fresh)
        if row is None or span is None:
            return no_end(bot, guild, fresh)
        if not spot.is_spotlit(row):
            if ms.held_by(row) is not None:
                await update_channel(bot.db, int(row["id"]), spotlit_by_marathon=None)
            row, _settled = await changed_spotlight(
                bot,
                guild,
                actor,
                int(row["id"]),
                via=via,
                spotlight=1,
                expires_at=ms.reach_end(span, tail).isoformat(),
                spotlit_by_marathon=int(fresh["id"]),
            )
    until = parse_ts(_cell(row, "expires_at"))
    said.append(
        words(
            bot,
            guild.id,
            MARATHON_CONTROLS_STARTED_KEY,
            channel=login_of(row),
            marathon=marathon["name"],
            until=f"<t:{int(until.timestamp())}:f>" if until else "—",
            tail=tail,
        )
    )
    return Outcome(True, " ".join(one for one in said if one))


def follow_can_start(bot: Any, guild: Any, row: Any) -> bool:
    return (
        enabled(bot, guild.id) and posts_mode_of(bot, guild.id) != MODE_OFF and takes_marathons(row)
    )


async def start_later(
    bot: Any, guild: Any, actor: Any, marathon: Any, row: Any, span: Any, *, via: str
) -> Outcome:
    """Before the lead window nothing is spotlit: the marathon follows, and its follow turns the
    row on at the lead and gives it back at span end plus the tail."""
    lead, tail = lead_of(bot, guild.id), tail_of(bot, guild.id)
    if not follow_can_start(bot, guild, row):
        return refusal(
            words(
                bot,
                guild.id,
                MARATHON_CONTROLS_CANNOT_WAIT_KEY,
                marathon=marathon["name"],
                channel=login_of(row),
                lead=lead,
            ),
            CANNOT_WAIT_CODE,
            409,
        )
    if ms.mode_of(marathon) == ms.OFF:
        moved = await set_spotlight_mode(bot, guild, actor, marathon, ms.FOLLOW, via=via)
        if not moved.ok:
            return moved
    opening = span[0] - timedelta(minutes=max(0, lead))
    return Outcome(
        True,
        words(
            bot,
            guild.id,
            MARATHON_CONTROLS_WAITS_KEY,
            lead=lead,
            when=f"<t:{int(opening.timestamp())}:f>",
            tail=tail,
            channel=login_of(row),
            marathon=marathon["name"],
        ),
    )


async def cancel_spotlight(
    bot: Any, guild: Any, actor: Any, marathon: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    """The marathon stops following; the row is left alone unless this marathon holds it."""
    row = await _row_of(bot, guild, marathon)
    if row is None:
        return no_channel(bot, guild, marathon)
    if ms.mode_of(marathon) != ms.OFF:
        moved = await set_spotlight_mode(bot, guild, actor, marathon, ms.OFF, via=via)
        if not moved.ok:
            return moved
    return Outcome(
        True,
        words(
            bot,
            guild.id,
            MARATHON_CONTROLS_CANCELLED_KEY,
            marathon=marathon["name"],
            channel=login_of(row),
        ),
    )


async def stop_spotlight(
    bot: Any, guild: Any, actor: Any, marathon: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    """Off exactly as a staff Off on Go-live, and this marathon stops following; a kept
    spotlight is refused in words."""
    row = await _row_of(bot, guild, marathon)
    if row is None:
        return no_channel(bot, guild, marathon)
    if ms.is_kept(row):
        return refusal(
            words(bot, guild.id, MARATHON_CONTROLS_KEPT_REFUSED_KEY, channel=login_of(row)),
            KEPT_CODE,
            409,
        )
    said: list[str] = []
    if spot.is_spotlit(row):
        fresh_row, settled = await set_spotlight(bot, guild, actor, int(row["id"]), False, via=via)
        said.append(spot.spotlight_said(fresh_row, settled))
        said.append(await after_staff_dim(bot, guild, actor, row, fresh_row, via=via))
    again = await get_marathon(bot.db, guild.id, marathon["id"])
    if again is not None and ms.mode_of(again) != ms.OFF:
        moved = await set_spotlight_mode(bot, guild, actor, again, ms.OFF, via=via)
        said.append(moved.message)
    return Outcome(True, " ".join(one for one in said if one))


async def press(
    bot: Any,
    guild: Any,
    actor: Any,
    marathon_id: Any,
    action: str,
    to: str,
    *,
    via: str = VIA_DISCORD,
) -> Outcome:
    marathon = await get_marathon(bot.db, guild.id, marathon_id)
    if marathon is None:
        return refusal(mt.NO_SUCH_MARATHON.format(given=marathon_id), NO_SUCH, 404)
    if action in (mtc.EVENT, mtc.RUNS):
        wanted = mtc.wanted_mode(me.mode_of(marathon), action, to)
        outcome = await set_event_mode(bot, guild, actor, marathon, wanted, via=via)
    elif action == mtc.HIGHLIGHT:
        from .marathon_public import set_public_highlight

        outcome = await set_public_highlight(bot, guild, actor, marathon, to == mtc.ON, via=via)
    elif action == mtc.PING:
        from .marathon_ping import set_ping_role

        outcome = await set_ping_role(bot, guild, actor, marathon, to == mtc.ON, via=via)
    elif action == mtc.HOSTS:
        outcome = refusal(mh.SCAN_GONE, GONE_CODE, 410)
    elif action == mtc.HOST_EVENTS:
        outcome = refusal(mh.HOST_EVENTS_GONE, GONE_CODE, 410)
    elif action == mtc.ANNOUNCE:
        outcome = await set_switch(bot, guild, actor, marathon, mh.ANNOUNCE, to == mtc.ON, via=via)
    elif action == mtc.OVERLAY:
        outcome = await set_switch(bot, guild, actor, marathon, mh.OVERLAY, to == mtc.ON, via=via)
    elif to == mtc.ON:
        outcome = await start_spotlight(bot, guild, actor, marathon, via=via)
    elif to == mtc.CANCEL:
        outcome = await cancel_spotlight(bot, guild, actor, marathon, via=via)
    else:
        outcome = await stop_spotlight(bot, guild, actor, marathon, via=via)
    await controls_changed(bot, guild, marathon_id)
    return outcome


class ControlButton(
    SafeDynamicItem, discord.ui.DynamicItem[discord.ui.Button], template=mtc.TEMPLATE
):
    def __init__(
        self,
        marathon_id: int,
        action: str,
        to: str,
        label: str | None = None,
        disabled: bool = False,
        word: str | None = None,
    ) -> None:
        self.marathon_id = int(marathon_id)
        self.action = action
        self.to = to
        super().__init__(
            discord.ui.Button(
                label=mtc.label(label or action),
                style=STYLES.get(word or "", discord.ButtonStyle.primary),
                custom_id=mtc.custom_id(marathon_id, action, to),
                disabled=disabled,
            )
        )

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: Any, match: re.Match):
        return cls(int(match["marathon_id"]), match["action"], match["to"])

    async def on_click(self, interaction: discord.Interaction) -> None:
        bot = interaction.client
        guard = getattr(bot, "guard", None)
        if guard is not None and not guard.allows_channel(interaction.channel_id):
            await answer(interaction, guard.refusal_message())
            return
        if not await still_staff(interaction):
            return
        if not bot.db.is_connected:
            await answer(interaction, DB_UNAVAILABLE)
            return
        await interaction.response.defer(ephemeral=True)
        outcome = await press(
            bot, interaction.guild, interaction.user, self.marathon_id, self.action, self.to
        )
        await answer(interaction, outcome.message)


__all__ = [
    "ControlButton",
    "cancel_spotlight",
    "controls_changed",
    "post_controls",
    "press",
    "refresh_controls",
    "row_changed",
    "start_spotlight",
    "stop_spotlight",
    "sync_controls",
]
