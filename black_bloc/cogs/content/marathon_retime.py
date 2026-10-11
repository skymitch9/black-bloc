from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Any

import discord

from ... import marathon as mt
from ... import marathon_overlay as overlay
from ... import marathon_retime as rt
from ... import marathon_signals as sig
from ...actionlog import log_action
from ...command_errors import AnswersErrors, SafeDynamicItem
from ...logkinds import VIA_DISCORD, VIA_WEBSITE, kind_via
from ...marathon_hotfix import local_words
from ...marathon_schedule_page import STATE_WORDS
from ...panels import Outcome, answer, refusal, still_staff
from ...settings_store import (
    DB_UNAVAILABLE,
    DEFAULT_TIMEZONE_KEY,
    MARATHON_DAY_SHIFTED_SAID_KEY,
    MARATHON_RETIME_AT_LABEL_KEY,
    MARATHON_RETIME_AT_PLACEHOLDER_KEY,
    MARATHON_RETIME_BAD_MINUTES_SAID_KEY,
    MARATHON_RETIME_BAD_TIME_SAID_KEY,
    MARATHON_RETIME_BEFORE_AHEAD_SAID_KEY,
    MARATHON_RETIME_MINUTES_LABEL_KEY,
    MARATHON_RETIME_MINUTES_PLACEHOLDER_KEY,
    MARATHON_RETIME_NOT_UPCOMING_SAID_KEY,
    MARATHON_RETIME_NOTHING_SAID_KEY,
    MARATHON_RETIME_RUN_LABEL_KEY,
    MARATHON_RETIME_SAME_SAID_KEY,
    MARATHON_RETIME_SHIFT_TITLE_KEY,
    MARATHON_RETIME_START_TITLE_KEY,
    MARATHON_RETIME_TRACKER_SAID_KEY,
    MARATHON_SHIFT_MAX_KEY,
    MARATHON_START_SET_SAID_KEY,
)
from ...timezones import is_known, unix
from .marathon import (
    NO_SUCH,
    NO_SUCH_RUN_CODE,
    cog_of,
    get_marathon,
    refused_with,
    run_by_id,
    runs_of,
    said_default,
    update_run,
)

TRACKER_CODE = "retimes_itself"
NOT_UPCOMING_CODE = "not_upcoming"
BAD_TIME_CODE = "bad_time"
BAD_MINUTES_CODE = "bad_minutes"
SAME_CODE = "same_time"
BEFORE_CODE = "before_the_run_ahead"
NOTHING_CODE = "nothing_upcoming"
TEMPLATE = r"marathon:retime:(?P<marathon_id>[0-9]+):(?P<move>start|shift)"
CUSTOM_ID = "marathon:retime:{marathon_id}:{move}"
FORM_ID = "marathon:retime:form:"
SHORT = 45
LONG = 100
GIVEN = 40


def words(bot: Any, guild_id: int, key: str, **fields: Any) -> str:
    return mt.render(bot.store.get(guild_id, key), said_default(key), **fields).text


def clipped(text: Any, limit: int) -> str:
    return str(text or "").strip()[:limit] or "…"


def server_zone(bot: Any, guild: Any) -> str:
    return str(bot.store.get(guild.id, DEFAULT_TIMEZONE_KEY) or "UTC")


def moment(at: datetime | None, via: str) -> str:
    """A moment in the answer: a Discord stamp, or the site's `{{at:ISO}}` token."""
    if at is None:
        return "—"
    if via == VIA_WEBSITE:
        return "{{at:" + at.isoformat() + "}}"
    return f"<t:{unix(at)}:f>"


def tracker_refusal(bot: Any, guild: Any, marathon: Any) -> Outcome:
    return refused_with(
        bot,
        guild.id,
        MARATHON_RETIME_TRACKER_SAID_KEY,
        TRACKER_CODE,
        409,
        marathon=marathon["name"],
    )


def days_of(marathon: Any, rows: list[Any]) -> list[list[Any]]:
    return overlay.chains(rows) if overlay.applied(marathon) else sig.chains(rows)


async def set_start(
    bot: Any,
    guild: Any,
    actor: Any,
    marathon: Any,
    run: Any,
    at: Any,
    tz: Any = None,
    *,
    via: str = VIA_DISCORD,
) -> Outcome:
    """Staff give one run a start; the later runs of its day walk from it."""
    zone_name = str(tz) if tz and is_known(tz) else server_zone(bot, guild)

    def wanted(row: Any) -> Any:
        found = rt.target_of(at, zone_name, rt.current(row))
        if found is None:
            return refused_with(
                bot,
                guild.id,
                MARATHON_RETIME_BAD_TIME_SAID_KEY,
                BAD_TIME_CODE,
                400,
                given=str(at or "").strip()[:GIVEN] or "Nothing",
                zone=zone_name,
            )
        return found

    return await moved(bot, guild, actor, marathon, run, wanted, rt.START_SET, None, via=via)


async def shift_day(
    bot: Any,
    guild: Any,
    actor: Any,
    marathon: Any,
    run: Any,
    minutes: Any,
    *,
    via: str = VIA_DISCORD,
) -> Outcome:
    """Staff move a run and every later run of its day by a number of minutes."""
    most = int(bot.store.get(guild.id, MARATHON_SHIFT_MAX_KEY))
    count = rt.minutes_of(minutes)
    if rt.minutes_trouble(count, most):
        return refused_with(
            bot,
            guild.id,
            MARATHON_RETIME_BAD_MINUTES_SAID_KEY,
            BAD_MINUTES_CODE,
            400,
            given=str(minutes if minutes is not None else "").strip()[:GIVEN] or "Nothing",
            most=most,
        )

    def wanted(row: Any) -> Any:
        return rt.current(row) + timedelta(minutes=count)

    return await moved(bot, guild, actor, marathon, run, wanted, rt.DAY_SHIFTED, count, via=via)


async def moved(
    bot: Any,
    guild: Any,
    actor: Any,
    marathon: Any,
    run: Any,
    wanted: Any,
    kind: str,
    minutes: int | None,
    *,
    via: str,
) -> Outcome:
    from .marathon_signals import retime

    cog = cog_of(bot)
    async with cog.lock(marathon["id"]):
        fresh = await get_marathon(bot.db, guild.id, marathon["id"])
        if fresh is None:
            return refusal(mt.NO_SUCH_MARATHON.format(given=marathon["id"]), NO_SUCH, 404)
        if not sig.takes_staff_times(fresh["source"]):
            return tracker_refusal(bot, guild, fresh)
        row = await run_by_id(bot.db, fresh["id"], run["id"])
        if row is None:
            return refusal(mt.NO_SUCH_RUN.format(name=fresh["name"]), NO_SUCH_RUN_CODE, 404)
        if row["state"] != mt.UPCOMING:
            return refused_with(
                bot,
                guild.id,
                MARATHON_RETIME_NOT_UPCOMING_SAID_KEY,
                NOT_UPCOMING_CODE,
                409,
                game=row["game"],
                state=STATE_WORDS.get(row["state"], row["state"]),
            )
        target = wanted(row)
        if isinstance(target, Outcome):
            return target
        was = rt.current(row)
        if target == was:
            return refused_with(
                bot,
                guild.id,
                MARATHON_RETIME_SAME_SAID_KEY,
                SAME_CODE,
                409,
                game=row["game"],
                at=moment(target, via),
            )
        rows = await runs_of(bot.db, fresh["id"])
        chain = rt.chain_of(days_of(fresh, rows), row)
        ahead = rt.ahead_started(chain, row)
        began = sig.anchor_of(ahead) if ahead is not None else None
        if began is not None and target < began:
            return refused_with(
                bot,
                guild.id,
                MARATHON_RETIME_BEFORE_AHEAD_SAID_KEY,
                BEFORE_CODE,
                409,
                at=moment(target, via),
                ahead=ahead["game"],
                started=moment(began, via),
            )
        stamp = cog.clock().isoformat()
        actor_id = getattr(actor, "id", None)
        for one, at in rt.anchors(chain, row, target):
            await update_run(
                bot.db,
                one["id"],
                staff_start_at=at.isoformat(),
                staff_start_by=int(actor_id) if actor_id else None,
                staff_start_set_at=stamp,
            )
        count = await retime(cog, guild, fresh, because=mt.BY_STAFF)
        await log_action(
            bot,
            guild,
            kind_via(kind, via),
            actor=actor,
            details={
                "marathon_id": fresh["id"],
                "run_id": row["id"],
                "game": row["game"],
                "from": was.isoformat() if was is not None else None,
                "to": target.isoformat(),
                "minutes": minutes,
                "runs": count,
                "actor": int(actor_id) if actor_id else None,
                "via": via,
            },
        )
        await cog.sync_board(guild, await get_marathon(bot.db, guild.id, fresh["id"]))
    fields = {
        "game": row["game"],
        "at": moment(target, via),
        "was": moment(was, via),
        "runs": count,
    }
    if kind == rt.DAY_SHIFTED:
        return Outcome(
            True,
            words(
                bot, guild.id, MARATHON_DAY_SHIFTED_SAID_KEY, minutes=rt.signed(minutes), **fields
            ),
        )
    return Outcome(True, words(bot, guild.id, MARATHON_START_SET_SAID_KEY, **fields))


# --- the Discord door ----------------------------------------------------------------------


def custom_id(marathon_id: Any, move: str) -> str:
    return CUSTOM_ID.format(marathon_id=int(marathon_id), move=move)


def run_choice(row: Any, zone_name: str) -> tuple[str, str]:
    when = local_words(mt._cell(row, "scheduled_at"), zone_name) or ""
    return (clipped(f"{when} · {row['game']}" if when else row["game"], LONG), str(row["id"]))


class RetimeModal(AnswersErrors, discord.ui.Modal):
    """Set start or Shift the day from the thread: a run, then a time or minutes."""

    def __init__(
        self,
        marathon_id: int,
        move: str,
        title: str,
        run_label: str,
        choices: list[tuple[str, str]],
        field_label: str,
        placeholder: str,
    ) -> None:
        super().__init__(title=clipped(title, SHORT))
        self.marathon_id = int(marathon_id)
        self.move = move
        self.run = discord.ui.Select(
            custom_id=f"{FORM_ID}run",
            options=[
                discord.SelectOption(label=label, value=value, default=index == 0)
                for index, (label, value) in enumerate(choices)
            ],
            min_values=1,
            max_values=1,
        )
        self.typed = discord.ui.TextInput(
            custom_id=f"{FORM_ID}{move}",
            max_length=GIVEN,
            placeholder=clipped(placeholder, LONG),
        )
        self.add_item(discord.ui.Label(text=clipped(run_label, SHORT), component=self.run))
        self.add_item(discord.ui.Label(text=clipped(field_label, SHORT), component=self.typed))

    async def on_submit(self, interaction: discord.Interaction) -> None:
        bot, guild = interaction.client, interaction.guild
        if not await still_staff(interaction):
            return
        if not bot.db.is_connected:
            await answer(interaction, DB_UNAVAILABLE)
            return
        await interaction.response.defer(ephemeral=True)
        outcome = await submitted(
            bot,
            guild,
            interaction.user,
            self.marathon_id,
            self.move,
            (self.run.values or [""])[0],
            str(self.typed.value or ""),
        )
        await answer(interaction, outcome.message)


async def submitted(
    bot: Any, guild: Any, actor: Any, marathon_id: Any, move: str, run_id: Any, typed: str
) -> Outcome:
    marathon = await get_marathon(bot.db, guild.id, marathon_id)
    if marathon is None:
        return refusal(mt.NO_SUCH_MARATHON.format(given=marathon_id), NO_SUCH, 404)
    run = await run_by_id(bot.db, marathon["id"], run_id)
    if run is None:
        return refusal(mt.NO_SUCH_RUN.format(name=marathon["name"]), NO_SUCH_RUN_CODE, 404)
    if move == rt.SHIFT:
        return await shift_day(bot, guild, actor, marathon, run, typed)
    return await set_start(bot, guild, actor, marathon, run, typed)


async def form_for(bot: Any, guild: Any, marathon_id: Any, move: str) -> Any:
    """The form to open, or the Outcome that refuses in words."""
    marathon = await get_marathon(bot.db, guild.id, marathon_id)
    if marathon is None:
        return refusal(mt.NO_SUCH_MARATHON.format(given=marathon_id), NO_SUCH, 404)
    if not sig.takes_staff_times(marathon["source"]):
        return tracker_refusal(bot, guild, marathon)
    runs = rt.pickable(await runs_of(bot.db, marathon["id"]))
    if not runs:
        return refused_with(
            bot,
            guild.id,
            MARATHON_RETIME_NOTHING_SAID_KEY,
            NOTHING_CODE,
            409,
            marathon=marathon["name"],
        )
    zone_name = server_zone(bot, guild)
    shift = move == rt.SHIFT
    return RetimeModal(
        marathon["id"],
        move,
        words(
            bot,
            guild.id,
            MARATHON_RETIME_SHIFT_TITLE_KEY if shift else MARATHON_RETIME_START_TITLE_KEY,
        ),
        words(bot, guild.id, MARATHON_RETIME_RUN_LABEL_KEY),
        [run_choice(one, zone_name) for one in runs],
        words(
            bot,
            guild.id,
            MARATHON_RETIME_MINUTES_LABEL_KEY if shift else MARATHON_RETIME_AT_LABEL_KEY,
            zone=zone_name,
        ),
        words(
            bot,
            guild.id,
            MARATHON_RETIME_MINUTES_PLACEHOLDER_KEY
            if shift
            else MARATHON_RETIME_AT_PLACEHOLDER_KEY,
        ),
    )


class RetimeButton(SafeDynamicItem, discord.ui.DynamicItem[discord.ui.Button], template=TEMPLATE):
    def __init__(
        self, marathon_id: int, move: str, label: str | None = None, row: int | None = None
    ) -> None:
        self.marathon_id = int(marathon_id)
        self.move = move
        super().__init__(
            discord.ui.Button(
                label=clipped(label or move, 80),
                style=discord.ButtonStyle.secondary,
                custom_id=custom_id(marathon_id, move),
                row=row,
            )
        )

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: Any, match: re.Match):
        return cls(int(match["marathon_id"]), match["move"])

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
        found = await form_for(bot, interaction.guild, self.marathon_id, self.move)
        if isinstance(found, Outcome):
            await answer(interaction, found.message)
            return
        await interaction.response.send_modal(found)


__all__ = [
    "RetimeButton",
    "RetimeModal",
    "form_for",
    "set_start",
    "shift_day",
    "submitted",
]
