from __future__ import annotations

import asyncio
import logging
import re
from datetime import timedelta
from typing import Any

import discord

from ... import marathon as mt
from ... import marathon_baf_event as baf
from ... import marathon_events as me
from ... import marathon_hosts as mh
from ... import marathon_inbox as mi
from ... import marathon_ping as mping
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
    MARATHON_CONTROLS_ALREADY_ON_KEY,
    MARATHON_CONTROLS_ANNOUNCE_OFF_KEY,
    MARATHON_CONTROLS_ANNOUNCE_ON_KEY,
    MARATHON_CONTROLS_ARCHIVE_KEY,
    MARATHON_CONTROLS_BAF_ANSWERED_NO_KEY,
    MARATHON_CONTROLS_BAF_ANSWERED_YES_KEY,
    MARATHON_CONTROLS_BAF_NAMED_KEY,
    MARATHON_CONTROLS_BAF_RUNS_KEY,
    MARATHON_CONTROLS_BAF_SAID_NO_KEY,
    MARATHON_CONTROLS_BAF_SAID_UNSURE_KEY,
    MARATHON_CONTROLS_BAF_SAID_YES_KEY,
    MARATHON_CONTROLS_BAF_STAFF_NO_KEY,
    MARATHON_CONTROLS_BAF_STAFF_YES_KEY,
    MARATHON_CONTROLS_CANCELLED_KEY,
    MARATHON_CONTROLS_CANNOT_WAIT_KEY,
    MARATHON_CONTROLS_EVENT_OFF_KEY,
    MARATHON_CONTROLS_EVENT_ON_KEY,
    MARATHON_CONTROLS_HOST_ANNOUNCE_OFF_KEY,
    MARATHON_CONTROLS_HOST_ANNOUNCE_ON_KEY,
    MARATHON_CONTROLS_KEPT_REFUSED_KEY,
    MARATHON_CONTROLS_NO_CHANNEL_KEY,
    MARATHON_CONTROLS_NO_END_KEY,
    MARATHON_CONTROLS_PING_OFF_KEY,
    MARATHON_CONTROLS_PING_ON_KEY,
    MARATHON_CONTROLS_SPOTLIGHT_FOLLOW_OFF_KEY,
    MARATHON_CONTROLS_SPOTLIGHT_FOLLOW_ON_KEY,
    MARATHON_CONTROLS_SPOTLIGHT_KEPT_LINE_KEY,
    MARATHON_CONTROLS_SPOTLIGHT_NONE_LINE_KEY,
    MARATHON_CONTROLS_SPOTLIGHT_STARTS_LINE_KEY,
    MARATHON_CONTROLS_SPOTLIGHT_UNTIL_LINE_KEY,
    MARATHON_CONTROLS_STARTED_KEY,
    MARATHON_CONTROLS_TRACKER_KEY,
    MARATHON_CONTROLS_WAITS_KEY,
)
from ...spotlight import reason_of
from .marathon import (
    MODE_OFF,
    NO_SUCH,
    _cell,
    cog_of,
    get_marathon,
    now_for,
    runs_of,
    update_marathon,
)
from .marathon import mode_of as posts_mode_of
from .marathon_announce import announces, policy_of
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
    (mtc.SPOTLIGHT, mtc.ON): MARATHON_CONTROLS_SPOTLIGHT_FOLLOW_ON_KEY,
    (mtc.SPOTLIGHT, mtc.OFF): MARATHON_CONTROLS_SPOTLIGHT_FOLLOW_OFF_KEY,
    (mtc.PING, mtc.ON): MARATHON_CONTROLS_PING_ON_KEY,
    (mtc.PING, mtc.OFF): MARATHON_CONTROLS_PING_OFF_KEY,
    (mtc.ANNOUNCE, mtc.ON): MARATHON_CONTROLS_ANNOUNCE_ON_KEY,
    (mtc.ANNOUNCE, mtc.OFF): MARATHON_CONTROLS_ANNOUNCE_OFF_KEY,
    (mtc.HOST_ANNOUNCE, mtc.ON): MARATHON_CONTROLS_HOST_ANNOUNCE_ON_KEY,
    (mtc.HOST_ANNOUNCE, mtc.OFF): MARATHON_CONTROLS_HOST_ANNOUNCE_OFF_KEY,
    (mtc.ARCHIVE, mtc.ARCHIVE): MARATHON_CONTROLS_ARCHIVE_KEY,
    (mtc.LINK, ""): MARATHON_CONTROLS_TRACKER_KEY,
}
BAF_LABEL_KEYS = {
    mtc.BAF_SAID_YES: MARATHON_CONTROLS_BAF_SAID_YES_KEY,
    mtc.BAF_SAID_NO: MARATHON_CONTROLS_BAF_SAID_NO_KEY,
    mtc.BAF_SAID_UNSURE: MARATHON_CONTROLS_BAF_SAID_UNSURE_KEY,
    mtc.BAF_STAFF_YES: MARATHON_CONTROLS_BAF_STAFF_YES_KEY,
    mtc.BAF_STAFF_NO: MARATHON_CONTROLS_BAF_STAFF_NO_KEY,
    mtc.BAF_ANSWERED_YES: MARATHON_CONTROLS_BAF_ANSWERED_YES_KEY,
    mtc.BAF_ANSWERED_NO: MARATHON_CONTROLS_BAF_ANSWERED_NO_KEY,
}
SPOT_LINE_KEYS = {
    mtc.LINE_UNTIL: MARATHON_CONTROLS_SPOTLIGHT_UNTIL_LINE_KEY,
    mtc.LINE_STARTS: MARATHON_CONTROLS_SPOTLIGHT_STARTS_LINE_KEY,
    mtc.LINE_KEPT: MARATHON_CONTROLS_SPOTLIGHT_KEPT_LINE_KEY,
    mtc.LINE_NONE: MARATHON_CONTROLS_SPOTLIGHT_NONE_LINE_KEY,
}
RETIRED_SAID = {
    mtc.HOSTS: mh.SCAN_GONE,
    mtc.HOST_EVENTS: mh.HOST_EVENTS_GONE,
    mtc.RUNS: mtc.RUNS_GONE,
    mtc.OVERLAY: mtc.OVERLAY_GONE,
    mtc.HIGHLIGHT: mtc.HIGHLIGHT_GONE,
}
STYLES = {
    mtc.ON: discord.ButtonStyle.success,
    mtc.OFF: discord.ButtonStyle.secondary,
    mtc.ARCHIVE: discord.ButtonStyle.secondary,
}


def shown_lock(cog: Any, marathon_id: Any) -> asyncio.Lock:
    locks = cog.__dict__.setdefault("controls_locks", {})
    key = int(marathon_id)
    found = locks.get(key)
    if found is None:
        found = locks[key] = asyncio.Lock()
    return found


def shown_cache(cog: Any) -> dict[int, Any]:
    return cog.__dict__.setdefault("controls_shown", {})


def baf_button(bot: Any, guild: Any, marathon: Any, rows: Any) -> tuple[Any, dict[str, Any]]:
    """The BaF event button and the words its label takes."""
    from .marathon_baf_event import reading_for, reason_words

    followed = baf.judgement_of(reading_for(bot, guild.id, marathon, rows), own=False)
    reason = mtc.baf_reason(followed)
    if reason == mtc.REASON_NAMED:
        said = words(bot, guild.id, MARATHON_CONTROLS_BAF_NAMED_KEY, name=followed.name)
    elif reason == mtc.REASON_NO_RUNS:
        said = reason_words(bot, guild.id, followed)
    else:
        said = words(
            bot, guild.id, MARATHON_CONTROLS_BAF_RUNS_KEY, baf=followed.baf, runs=followed.runs
        )
    return (mtc.baf_control(baf.stored(marathon), followed), {"reason": said})


def stamp(value: Any) -> str:
    when = parse_ts(value)
    return f"<t:{int(when.timestamp())}:f>" if when else "—"


def spot_words(bot: Any, guild: Any, state: dict[str, Any]) -> str:
    line = mtc.spot_line(state["state"])
    if line is None:
        return ""
    return words(
        bot,
        guild.id,
        SPOT_LINE_KEYS[line],
        until=stamp(state.get("until")),
        starts=stamp(state.get("starts")),
    )


async def rendered(bot: Any, guild: Any, marathon: Any) -> tuple[str, tuple, tuple[str, ...]]:
    """`(content, controls, labels)` from the row, the channel row and the keys."""
    _row, state = await state_for(bot, guild, marathon)
    rows = await runs_of(bot.db, marathon["id"])
    over = mt.is_over(marathon, now_for(bot))
    shown_baf, fields = (None, {}) if over else baf_button(bot, guild, marathon, rows)
    controls = mtc.controls(
        me.mode_of(marathon),
        state["state"],
        follows=ms.mode_of(marathon) == ms.FOLLOW,
        ping=mping.pings_role(marathon),
        announce=announces(bot, guild.id, marathon),
        host_announce=policy_of(bot, guild.id, marathon).hosts_on,
        baf=shown_baf,
        over=over,
    )
    labels = tuple(mtc.label(words(bot, guild.id, label_key(one), **fields)) for one in controls)
    lines = [spot_words(bot, guild, state), role_ping_line(bot, guild, marathon, rows=rows)]
    return ("\n".join(one for one in lines if one), controls, labels)


def label_key(control: Any) -> str:
    if control.action == mtc.BAF:
        return BAF_LABEL_KEYS[control.label]
    return LABEL_KEYS[(control.action, control.word)]


def tracker_url(bot: Any, marathon: Any) -> str | None:
    return mtc.tracker_url(getattr(getattr(bot, "settings", None), "origin", ""), marathon["id"])


def view_of(
    marathon_id: Any, controls: tuple, labels: tuple[str, ...], link: Any = None
) -> discord.ui.View:
    view = discord.ui.View(timeout=None)
    for one, text in zip(controls, labels, strict=True):
        if one.action != mtc.LINK:
            view.add_item(ControlButton(marathon_id, one.action, one.to, text, one.word, one.row))
        elif link:
            view.add_item(
                discord.ui.Button(style=discord.ButtonStyle.link, label=text, url=link, row=one.row)
            )
    return view


async def post_controls(bot: Any, guild: Any, marathon: Any, thread: Any) -> Any:
    """Right after the thread's opening, with the marathon's lock held: posted, stored, pinned."""
    guard = getattr(bot, "guard", None)
    if guard is not None and not guard.allows_channel(thread.id):
        return None
    content, controls, labels = await rendered(bot, guild, marathon)
    link = tracker_url(bot, marathon)
    base = {"marathon_id": marathon["id"], "name": marathon["name"], "thread_id": int(thread.id)}
    try:
        message = await thread.send(
            content or None,
            view=view_of(marathon["id"], controls, labels, link),
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
            (content, controls, labels, link),
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
        shown = (*await rendered(bot, guild, fresh), tracker_url(bot, fresh))
        if shown_cache(cog).get(key) == (thread_id, message_id, shown):
            return "same"
        thread, _lost = await find_channel(bot, guild, thread_id)
        if thread is None:
            return "skipped"
        await reopened(thread)
        content, controls, labels, link = shown
        try:
            message = await message_in(thread, message_id)
            await message.edit(
                content=content or None,
                view=view_of(key, controls, labels, link),
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


async def archived_controls(bot: Any, guild: Any, marathon: Any) -> None:
    """An archived marathon's controls keep their state line and lose every button."""
    cog = cog_of(bot)
    thread_id, message_id = _cell(marathon, "thread_id"), _cell(marathon, "controls_message_id")
    if cog is None or not thread_id or not message_id:
        return
    shown_cache(cog).pop(int(marathon["id"]), None)
    thread, _lost = await find_channel(bot, guild, int(thread_id))
    if thread is None:
        return
    try:
        message = await message_in(await reopened(thread), int(message_id))
        await message.edit(view=None)
    except Exception as exc:
        log.info("marathon: could not clear the archived controls — %s", reason_of(exc))


# --- the moves -----------------------------------------------------------------------------------


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
    tail = tail_of(bot, guild.id)
    span = ms.span_of(marathon)
    if spot.is_spotlit(row):
        said = []
        if ms.mode_of(marathon) == ms.OFF:
            said.append(
                (await set_spotlight_mode(bot, guild, actor, marathon, ms.FOLLOW, via=via)).message
            )
        said.append(
            words(bot, guild.id, MARATHON_CONTROLS_ALREADY_ON_KEY, channel=login_of(row))
        )
        return Outcome(True, " ".join(one for one in said if one))
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


def during_show(bot: Any, guild: Any, marathon: Any, row: Any) -> bool:
    """The channel is spotlit for this show: held by it, or lit while the show is in reach."""
    if not spot.is_spotlit(row):
        return False
    if ms.held_by(row) == int(marathon["id"]):
        return True
    span = ms.span_of(marathon)
    return span is not None and ms.in_reach(
        span, now_for(bot), lead_of(bot, guild.id), tail_of(bot, guild.id)
    )


async def turn_off_spotlight(
    bot: Any, guild: Any, actor: Any, marathon: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    """The switch's off: a cancel before the show, a stop during it."""
    row = await _row_of(bot, guild, marathon)
    if row is None:
        return no_channel(bot, guild, marathon)
    if ms.is_kept(row) or during_show(bot, guild, marathon, row):
        return await stop_spotlight(bot, guild, actor, marathon, via=via)
    return await cancel_spotlight(bot, guild, actor, marathon, via=via)


async def archive_from_thread(
    bot: Any, guild: Any, actor: Any, marathon: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    from ... import marathon_archive as ma
    from .marathon_archive import archive_marathon

    return await archive_marathon(bot, guild, actor, marathon, why=ma.STAFF, via=via)


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
    if action in RETIRED_SAID:
        return refusal(RETIRED_SAID[action], GONE_CODE, 410)
    if action == mtc.ARCHIVE:
        return await archive_from_thread(bot, guild, actor, marathon, via=via)
    if action == mtc.EVENT:
        wanted = mtc.wanted_mode(me.mode_of(marathon), action, to)
        outcome = await set_event_mode(bot, guild, actor, marathon, wanted, via=via)
    elif action == mtc.PING:
        from .marathon_ping import set_ping_role

        outcome = await set_ping_role(bot, guild, actor, marathon, to == mtc.ON, via=via)
    elif action == mtc.ANNOUNCE:
        outcome = await set_switch(bot, guild, actor, marathon, mh.ANNOUNCE, to == mtc.ON, via=via)
    elif action == mtc.HOST_ANNOUNCE:
        outcome = await set_switch(
            bot, guild, actor, marathon, mh.HOST_ANNOUNCE, to == mtc.ON, via=via
        )
    elif action == mtc.BAF:
        from .marathon_baf_event import clear_answer, set_baf_event

        if to == mtc.CLEAR:
            outcome = await clear_answer(bot, guild, actor, marathon, via=via)
        else:
            outcome = await set_baf_event(bot, guild, actor, marathon, to, via=via)
    elif to == mtc.ON:
        outcome = await start_spotlight(bot, guild, actor, marathon, via=via)
    elif to == mtc.CANCEL:
        outcome = await cancel_spotlight(bot, guild, actor, marathon, via=via)
    else:
        outcome = await turn_off_spotlight(bot, guild, actor, marathon, via=via)
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
        word: str | None = None,
        row: int | None = None,
    ) -> None:
        self.marathon_id = int(marathon_id)
        self.action = action
        self.to = to
        super().__init__(
            discord.ui.Button(
                label=mtc.label(label or action),
                style=STYLES.get(word or "", discord.ButtonStyle.primary),
                custom_id=mtc.custom_id(marathon_id, action, to),
                row=row,
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
    "archived_controls",
    "cancel_spotlight",
    "controls_changed",
    "post_controls",
    "press",
    "refresh_controls",
    "row_changed",
    "start_spotlight",
    "stop_spotlight",
    "sync_controls",
    "turn_off_spotlight",
]
