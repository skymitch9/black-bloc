"""A BaF event day: the staff answer, the question to Leads, and the one Marathon-role ping."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta
from typing import Any

import discord

from ... import marathon as mt
from ... import marathon_baf_event as baf
from ... import marathon_inbox as mi
from ... import marathon_role_ping as mrp
from ...actionlog import log_action
from ...command_errors import SafeDynamicItem
from ...golive import parse_ts, ping_prefix
from ...logkinds import VIA_DISCORD, kind_via
from ...panels import Outcome, answer, refusal, still_staff
from ...settings_store import (
    DB_UNAVAILABLE,
    DEFAULT_TIMEZONE_KEY,
    MARATHON_BAF_EVENT_ANSWERED_KEY,
    MARATHON_BAF_EVENT_ASK_NO_KEY,
    MARATHON_BAF_EVENT_ASK_PERCENT_KEY,
    MARATHON_BAF_EVENT_ASK_ROLE_KEY,
    MARATHON_BAF_EVENT_ASK_TEXT_KEY,
    MARATHON_BAF_EVENT_ASK_YES_KEY,
    MARATHON_BAF_EVENT_LINE_KEY,
    MARATHON_BAF_EVENT_MIN_RUNS_KEY,
    MARATHON_BAF_EVENT_NAMES_KEY,
    MARATHON_BAF_EVENT_PING_DONE_KEY,
    MARATHON_BAF_EVENT_PING_FALLBACK_KEY,
    MARATHON_BAF_EVENT_PING_MINUTES_KEY,
    MARATHON_BAF_EVENT_PING_NONE_KEY,
    MARATHON_BAF_EVENT_PING_WILL_KEY,
    MARATHON_BAF_EVENT_REASON_ALL_RUNS_KEY,
    MARATHON_BAF_EVENT_REASON_FEW_RUNS_KEY,
    MARATHON_BAF_EVENT_REASON_MIXED_KEY,
    MARATHON_BAF_EVENT_REASON_NAME_KEY,
    MARATHON_BAF_EVENT_REASON_NO_RUNS_KEY,
    MARATHON_BAF_EVENT_REASON_SHARE_KEY,
    MARATHON_BAF_EVENT_REASON_STAFF_KEY,
    MARATHON_BAF_EVENT_SAME_SAID_KEY,
    MARATHON_BAF_EVENT_SET_SAID_KEY,
    MARATHON_BAF_EVENT_WORD_FOLLOW_KEY,
    MARATHON_BAF_EVENT_WORD_NO_KEY,
    MARATHON_BAF_EVENT_WORD_UNSURE_KEY,
    MARATHON_BAF_EVENT_WORD_YES_KEY,
    MARATHON_PING_MINUTES_KEY,
    MARATHON_REMINDER_MINUTES_KEY,
)
from ...spotlight import reason_of
from ...timezones import DEFAULT_TZ, zone
from .marathon import (
    MODE_OFF,
    MODE_ON,
    NO_SUCH,
    actor_id,
    cog_of,
    get_marathon,
    mode_of,
    runs_of,
    said_default,
    update_marathon,
)
from .marathon_public import people_for
from .marathon_role_ping import may_mention_every_role, role_word, verdict_for

log = logging.getLogger(__name__)

ASK_TEMPLATE = r"marathon:bafevent:(?P<marathon_id>[0-9]+):(?P<to>yes|no)"
ASK_ID = "marathon:bafevent:{marathon_id}:{to}"
RETRY_AFTER = timedelta(minutes=10)
LINES_MAX = 3
BY_QUESTION = "question"
ANSWER_KEYS = {
    baf.YES: MARATHON_BAF_EVENT_WORD_YES_KEY,
    baf.NO: MARATHON_BAF_EVENT_WORD_NO_KEY,
    baf.UNSURE: MARATHON_BAF_EVENT_WORD_UNSURE_KEY,
    baf.FOLLOW: MARATHON_BAF_EVENT_WORD_FOLLOW_KEY,
}
REASON_KEYS = {
    baf.BY_STAFF: MARATHON_BAF_EVENT_REASON_STAFF_KEY,
    baf.BY_NAME: MARATHON_BAF_EVENT_REASON_NAME_KEY,
    baf.BY_RUNS: MARATHON_BAF_EVENT_REASON_ALL_RUNS_KEY,
    baf.BY_SHARE: MARATHON_BAF_EVENT_REASON_SHARE_KEY,
    baf.BY_FEW: MARATHON_BAF_EVENT_REASON_FEW_RUNS_KEY,
    baf.BY_MIXED: MARATHON_BAF_EVENT_REASON_MIXED_KEY,
    baf.BY_NO_RUNS: MARATHON_BAF_EVENT_REASON_NO_RUNS_KEY,
}


def words(bot: Any, guild_id: int, key: str, /, **fields: Any) -> str:
    return mt.render(bot.store.get(guild_id, key), said_default(key), **fields).text


def reading_for(bot: Any, guild_id: int, marathon: Any, rows: Any) -> baf.Reading:
    store = bot.store
    ping_mark = int(store.get(guild_id, MARATHON_PING_MINUTES_KEY))
    return baf.reading(
        marathon,
        rows,
        marks=mt.reminder_marks(store.get(guild_id, MARATHON_REMINDER_MINUTES_KEY), ping_mark),
        ping_mark=ping_mark,
        wanted_mark=int(store.get(guild_id, MARATHON_BAF_EVENT_PING_MINUTES_KEY)),
        names=baf.names_of(store.get(guild_id, MARATHON_BAF_EVENT_NAMES_KEY)),
        min_runs=int(store.get(guild_id, MARATHON_BAF_EVENT_MIN_RUNS_KEY)),
        ask_percent=int(store.get(guild_id, MARATHON_BAF_EVENT_ASK_PERCENT_KEY)),
        tz_name=store.get(guild_id, DEFAULT_TIMEZONE_KEY),
    )


def speaks_for(marathon: Any) -> Any:
    return lambda row: bool(people_for(marathon, row))


async def reading_now(bot: Any, guild: Any, marathon: Any) -> baf.Reading:
    return reading_for(bot, guild.id, marathon, await runs_of(bot.db, marathon["id"]))


# --- the ping -----------------------------------------------------------------------------------


async def heads_up_role(
    cog: Any, guild: Any, marathon: Any, row: Any, mark: int
) -> tuple[mrp.Verdict | None, dict[str, Any] | None]:
    """`(the verdict this heads-up posts with, the day's claim when it carries the ping)`. The
    claim is stored before the send, so a restart can never ping the day twice."""
    bot = cog.bot
    ping_mark = int(bot.store.get(guild.id, MARATHON_PING_MINUTES_KEY))
    fresh = await get_marathon(bot.db, guild.id, marathon["id"]) or marathon
    rows = await runs_of(bot.db, fresh["id"])
    found = reading_for(bot, guild.id, fresh, rows)
    current = next((one for one in rows if one["id"] == row["id"]), row)
    plan = baf.plan(found, current, mark, speaks=speaks_for(fresh))
    if plan.kind == baf.PER_RUN:
        return (verdict_for(bot, guild, fresh) if int(mark) == ping_mark else None, None)
    starts = baf.span_of(plan.day)[0]
    verdict = mrp.on_day(verdict_for(bot, guild, fresh), starts.isoformat() if starts else None)
    if plan.kind == baf.QUIET:
        if int(mark) > found.limit and int(mark) != ping_mark:
            return (None, None)
        return (mrp.unsent(verdict, plan.reason), None)
    if not verdict.mentions:
        return (verdict, None)
    claim = baf.record_for(plan.day, current, mark, cog.clock(), reason=plan.judgement.reason)
    await update_marathon(
        bot.db, fresh["id"], **{baf.PINGS_COLUMN: baf.dump_pings([*found.records, claim])}
    )
    return (verdict, claim)


async def settle(cog: Any, guild: Any, marathon: Any, claim: Any, public: Any) -> None:
    """The claim becomes the day's ping when the public copy carried the role, else it is
    given back so the next heads-up may carry it."""
    if claim is None:
        return
    bot = cog.bot
    fresh = await get_marathon(bot.db, guild.id, marathon["id"])
    if fresh is None:
        return
    records = baf.pings_of(fresh)
    copy = (public or {}).get("copy")
    if copy and (public or {}).get("marathon_role") is not None:
        records = baf.sent(
            records, claim, message_id=copy.get("message_id"), channel_id=copy.get("channel_id")
        )
    else:
        records = baf.without(records, claim)
    await update_marathon(bot.db, fresh["id"], **{baf.PINGS_COLUMN: baf.dump_pings(records)})


def quiet_for(found: baf.Reading | None, row: Any, verdict: mrp.Verdict) -> mrp.Verdict | None:
    """A host block's verdict on a day that has, or had, its own one ping; None on any other."""
    reason = baf.quiet_reason(found, row) if found is not None else None
    if reason is None:
        return None
    starts = baf.span_of(baf.day_of(row, found.days))[0]
    return mrp.unsent(mrp.on_day(verdict, starts.isoformat() if starts else None), reason)


# --- the words staff read -----------------------------------------------------------------------


def day_word(bot: Any, guild: Any, marathon: Any, starts: Any, *, mention: bool) -> str:
    if starts is None:
        return str(marathon["name"])
    if mention:
        return f"<t:{int(starts.timestamp())}:D>"
    here = starts.astimezone(
        zone(str(bot.store.get(guild.id, DEFAULT_TIMEZONE_KEY) or "")) or zone(DEFAULT_TZ)
    )
    return f"{here:%a} {here.day} {here:%b}"


def reason_words(bot: Any, guild_id: int, judgement: baf.Judgement) -> str:
    return words(
        bot,
        guild_id,
        REASON_KEYS[judgement.reason],
        name=judgement.name,
        runs=judgement.runs,
        baf=judgement.baf,
        min=int(bot.store.get(guild_id, MARATHON_BAF_EVENT_MIN_RUNS_KEY)),
    )


def answer_word(bot: Any, guild_id: int, answer_is: str) -> str:
    return words(bot, guild_id, ANSWER_KEYS[answer_is])


def ping_words(
    bot: Any, guild: Any, found: baf.Reading, state: baf.DayState, verdict: mrp.Verdict, role: str
) -> str:
    """What the day's one ping did or will do; empty when the day is not governed by it or the
    role would not be mentioned anyway (the ping switch's own line says why)."""
    if not state.governed:
        return ""
    record = state.record
    if record is not None:
        return words(
            bot,
            guild.id,
            MARATHON_BAF_EVENT_PING_DONE_KEY,
            role=role,
            minutes=record.get("mark"),
            game=record.get("game") or "",
        )
    if not verdict.mentions:
        return ""
    if state.carrier is None:
        return words(bot, guild.id, MARATHON_BAF_EVENT_PING_NONE_KEY, role=role)
    said = words(
        bot,
        guild.id,
        MARATHON_BAF_EVENT_PING_WILL_KEY,
        role=role,
        minutes=state.carrier_mark,
        game=state.carrier["game"],
    )
    if found.fell_back:
        said += " " + words(
            bot,
            guild.id,
            MARATHON_BAF_EVENT_PING_FALLBACK_KEY,
            wanted=found.wanted_mark,
            minutes=found.limit,
        )
    return said


def shown(states: list[baf.DayState]) -> list[baf.DayState]:
    ahead = [one for one in states if not one.over]
    return ahead[:LINES_MAX] if ahead else states[-1:]


def state_of(
    bot: Any, guild: Any, marathon: Any, rows: Any, *, mention: bool = False
) -> dict[str, Any]:
    """The tri-state, what the bot worked out and why, and each show-day in words."""
    found = reading_for(bot, guild.id, marathon, rows)
    states = baf.day_states(found, speaks=speaks_for(marathon))
    verdict = verdict_for(bot, guild, marathon)
    role = role_word(verdict, mention=mention)
    own = baf.stored(marathon)
    now = baf.current(states)
    judged = now.judgement if now is not None else baf.judgement_of(found, [])
    worked = now.worked if now is not None else baf.judgement_of(found, [], own=False)
    days = []
    for state in states:
        line = words(
            bot,
            guild.id,
            MARATHON_BAF_EVENT_LINE_KEY,
            day=day_word(bot, guild, marathon, state.starts_at, mention=mention),
            answer=answer_word(bot, guild.id, state.judgement.answer),
            reason=reason_words(bot, guild.id, state.judgement),
            marathon=marathon["name"],
        )
        ping = ping_words(bot, guild, found, state, verdict, role)
        days.append(
            {
                "starts_at": state.starts_at.isoformat() if state.starts_at else None,
                "answer": state.judgement.answer,
                "reason": state.judgement.reason,
                "runs": state.judgement.runs,
                "baf": state.judgement.baf,
                "over": state.over,
                "governed": state.governed,
                "pinged": pinged_row(state.record),
                "carrier": (
                    None
                    if state.carrier is None
                    else {
                        "run_id": state.carrier["id"],
                        "game": state.carrier["game"],
                        "minutes": state.carrier_mark,
                    }
                ),
                "line": f"{line} {ping}".strip(),
            }
        )
    listed = shown(states)
    kept = {id(one) for one in listed}
    lines = [one["line"] for one, state in zip(days, states, strict=True) if id(state) in kept]
    if not states:
        lines = [
            words(
                bot,
                guild.id,
                MARATHON_BAF_EVENT_LINE_KEY,
                day=marathon["name"],
                answer=answer_word(bot, guild.id, judged.answer),
                reason=reason_words(bot, guild.id, judged),
                marathon=marathon["name"],
            )
        ]
    return {
        "own": own,
        "choice": baf.choice_of(own),
        "answer": judged.answer,
        "reason": judged.reason,
        "answer_word": answer_word(bot, guild.id, judged.answer),
        "reason_word": reason_words(bot, guild.id, judged),
        "worked_out": {
            "answer": worked.answer,
            "reason": worked.reason,
            "answer_word": answer_word(bot, guild.id, worked.answer),
            "reason_word": reason_words(bot, guild.id, worked),
        },
        "asked": bool(baf.ask_of(marathon).get("message_id")),
        "ping_minutes": found.limit,
        "ping_fell_back": found.fell_back,
        "days": days,
        "lines": lines,
        "all_governed": bool(listed) and all(one.governed for one in listed),
    }


def pinged_row(record: Any) -> dict[str, Any] | None:
    if record is None:
        return None
    return {
        "run_id": record.get("run_id"),
        "game": record.get("game"),
        "minutes": record.get("mark"),
        "at": record.get("at"),
        "sent": bool(record.get("sent")),
    }


# --- the one writer -----------------------------------------------------------------------------


async def set_baf_event(
    bot: Any,
    guild: Any,
    actor: Any,
    marathon: Any,
    given: Any,
    *,
    via: str = VIA_DISCORD,
    by: str | None = None,
) -> Outcome:
    """The marathon's own answer: yes, no, or None to follow what the bot works out. The
    question's buttons, the thread controls and the site all come here."""
    from .marathon_thread_controls import controls_changed

    understood, wanted = baf.clean(given)
    if not understood:
        return refusal(
            baf.BAD_CHOICE.format(marathon=marathon["name"]), baf.BAD_CHOICE_CODE, 422
        )
    async with cog_of(bot).lock(marathon["id"]):
        fresh = await get_marathon(bot.db, guild.id, marathon["id"])
        if fresh is None:
            return refusal(mt.NO_SUCH_MARATHON.format(given=marathon["id"]), NO_SUCH, 404)
        was = baf.stored(fresh)
        said = answer_word(bot, guild.id, baf.choice_of(wanted))
        if was == wanted:
            return Outcome(
                True,
                words(
                    bot,
                    guild.id,
                    MARATHON_BAF_EVENT_SAME_SAID_KEY,
                    marathon=fresh["name"],
                    answer=said,
                ),
                value=fresh,
            )
        await update_marathon(
            bot.db, fresh["id"], **{baf.COLUMN: None if wanted is None else int(wanted)}
        )
        fresh = await get_marathon(bot.db, guild.id, fresh["id"])
    await log_action(
        bot,
        guild,
        kind_via("marathon.baf_event_set", via),
        actor=actor,
        details={
            "marathon_id": fresh["id"],
            "name": fresh["name"],
            "from": baf.choice_of(was),
            "to": baf.choice_of(wanted),
            "by": by,
            "via": via,
        },
    )
    await note_answer(bot, guild, fresh, actor, said)
    await controls_changed(bot, guild, fresh["id"])
    return Outcome(
        True,
        words(bot, guild.id, MARATHON_BAF_EVENT_SET_SAID_KEY, marathon=fresh["name"], answer=said),
        value=await get_marathon(bot.db, guild.id, fresh["id"]),
    )


async def note_answer(bot: Any, guild: Any, marathon: Any, actor: Any, said: str) -> None:
    """The question says who answered what; the answer is stored already, so a failed edit
    changes nothing."""
    from .marathon_inbox import find_channel, reopened

    ask = baf.ask_of(marathon)
    if not ask.get("message_id") or not ask.get("channel_id"):
        return
    who = f"<@{actor_id(actor)}>" if actor_id(actor) else "Staff"
    line = words(
        bot,
        guild.id,
        MARATHON_BAF_EVENT_ANSWERED_KEY,
        who=who,
        answer=said,
        marathon=marathon["name"],
    )
    try:
        thread, _lost = await find_channel(bot, guild, ask["channel_id"])
        if thread is None:
            return
        await reopened(thread)
        partial = getattr(thread, "get_partial_message", None)
        message = (
            partial(int(ask["message_id"]))
            if callable(partial)
            else await thread.fetch_message(int(ask["message_id"]))
        )
        await message.edit(
            content=f"{ask.get('text') or ''}\n{line}".strip(),
            allowed_mentions=discord.AllowedMentions.none(),
        )
    except Exception as exc:
        log.warning("marathon: the BaF event question could not be edited — %s", reason_of(exc))


# --- the question -------------------------------------------------------------------------------


def ask_view(bot: Any, guild_id: int, marathon_id: Any) -> discord.ui.View:
    view = discord.ui.View(timeout=None)
    for to, key, style in (
        (baf.YES, MARATHON_BAF_EVENT_ASK_YES_KEY, discord.ButtonStyle.success),
        (baf.NO, MARATHON_BAF_EVENT_ASK_NO_KEY, discord.ButtonStyle.secondary),
    ):
        view.add_item(AskButton(marathon_id, to, words(bot, guild_id, key), style))
    return view


def ask_role(bot: Any, guild: Any) -> Any:
    found = bot.store.get(guild.id, MARATHON_BAF_EVENT_ASK_ROLE_KEY)
    try:
        role_id = int(found) if found else None
    except (TypeError, ValueError):
        return None
    getter = getattr(guild, "get_role", None)
    return getter(role_id) if role_id is not None and callable(getter) else None


def may_ask(ask: dict[str, Any], now: datetime) -> bool:
    """Once per marathon: never again once asked or claimed; a failed post waits and retries."""
    if not ask:
        return True
    if ask.get("message_id") or not ask.get("failed_at"):
        return False
    failed = parse_ts(ask.get("failed_at"))
    return failed is None or now - failed >= RETRY_AFTER


async def ask_if_unsure(
    cog: Any, guild: Any, marathon: Any, states: list[baf.DayState], now: datetime
) -> bool:
    from .marathon_inbox import find_channel, reopened
    from .marathon_thread_controls import has_home

    bot = cog.bot
    state = baf.asks(states)
    if state is None or baf.stored(marathon) is not None:
        return False
    if not may_ask(baf.ask_of(marathon), now) or not has_home(bot, guild, marathon):
        return False
    thread, _lost = await find_channel(bot, guild, marathon["thread_id"])
    guard = getattr(bot, "guard", None)
    if thread is None or (guard is not None and not guard.allows_channel(thread.id)):
        return False
    role = ask_role(bot, guild) if mode_of(bot, guild.id) == MODE_ON else None
    text = ping_prefix(getattr(role, "id", None)) + words(
        bot,
        guild.id,
        MARATHON_BAF_EVENT_ASK_TEXT_KEY,
        marathon=marathon["name"],
        baf=state.judgement.baf,
        runs=state.judgement.runs,
        day=day_word(bot, guild, marathon, state.starts_at, mention=True),
    )
    base = {
        "marathon_id": marathon["id"],
        "name": marathon["name"],
        "thread_id": int(thread.id),
        "day": state.starts_at.isoformat() if state.starts_at else None,
        "runs": state.judgement.runs,
        "baf": state.judgement.baf,
    }
    claim = {"asked_at": now.isoformat(), "claimed": True}
    await update_marathon(bot.db, marathon["id"], **{baf.ASK_COLUMN: baf.dump_ask(claim)})
    try:
        message = await (await reopened(thread)).send(
            text,
            view=ask_view(bot, guild.id, marathon["id"]),
            allowed_mentions=(
                discord.AllowedMentions(
                    everyone=False, users=False, roles=[discord.Object(int(role.id))]
                )
                if role is not None
                else discord.AllowedMentions.none()
            ),
        )
    except Exception as exc:
        failed = {"failed_at": now.isoformat(), "reason": reason_of(exc)}
        await update_marathon(bot.db, marathon["id"], **{baf.ASK_COLUMN: baf.dump_ask(failed)})
        await log_action(
            bot,
            guild,
            "marathon.baf_event_ask_failed",
            details=base | {"reason": failed["reason"]},
        )
        return False
    asked = {
        "asked_at": now.isoformat(),
        "channel_id": int(thread.id),
        "message_id": int(message.id),
        "text": text,
    }
    await update_marathon(bot.db, marathon["id"], **{baf.ASK_COLUMN: baf.dump_ask(asked)})
    await log_action(
        bot,
        guild,
        "marathon.baf_event_asked",
        details=base
        | {
            "message_id": int(message.id),
            "role": int(role.id) if role is not None else None,
            "notifies": role is not None
            and mrp.notifies(role, may_mention_every_role(bot, guild, thread.id)),
        },
    )
    return True


async def note_missed(
    cog: Any, guild: Any, marathon: Any, found: baf.Reading, states: Any, now: datetime
) -> None:
    """One row for a BaF event day whose ping has no heads-up left to ride."""
    bot = cog.bot
    if not verdict_for(bot, guild, marathon).mentions:
        return
    records = list(found.records)
    added = []
    for state in states:
        if not state.judgement.yes or state.record is not None or state.carrier is not None:
            continue
        if state.over or state.starts_at is None or baf.missed(records, state.day) is not None:
            continue
        if now < state.starts_at - timedelta(minutes=found.limit):
            continue
        added.append(
            baf.record_for(state.day, None, None, now, missed=True, reason=state.judgement.reason)
        )
    if not added:
        return
    await update_marathon(
        bot.db, marathon["id"], **{baf.PINGS_COLUMN: baf.dump_pings([*records, *added])}
    )
    for one in added:
        await log_action(
            bot,
            guild,
            "marathon.baf_event_no_ping",
            details={
                "marathon_id": marathon["id"],
                "name": marathon["name"],
                "day": one["starts_at"],
                "runs": len(one["runs"]),
                "because": "no_heads_up_left",
                "reason": one["reason"],
            },
        )


async def sync(cog: Any, guild: Any, marathon: Any, now: datetime) -> None:
    """The minute tick, with the marathon's lock held: ask once when unsure, and say so once
    when a BaF event day has nothing left to carry its ping."""
    bot = cog.bot
    if marathon is None or not mi.is_tracked(marathon) or mode_of(bot, guild.id) == MODE_OFF:
        return
    try:
        fresh = await get_marathon(bot.db, guild.id, marathon["id"])
        if fresh is None:
            return
        found = await reading_now(bot, guild, fresh)
        states = baf.day_states(found, speaks=speaks_for(fresh))
        if await ask_if_unsure(cog, guild, fresh, states, now):
            return
        await note_missed(cog, guild, fresh, found, states, now)
    except Exception as exc:
        log.warning("marathon: the BaF event check failed — %s", reason_of(exc))


class AskButton(SafeDynamicItem, discord.ui.DynamicItem[discord.ui.Button], template=ASK_TEMPLATE):
    def __init__(
        self,
        marathon_id: int,
        to: str,
        label: str | None = None,
        style: discord.ButtonStyle = discord.ButtonStyle.secondary,
    ) -> None:
        self.marathon_id = int(marathon_id)
        self.to = to
        super().__init__(
            discord.ui.Button(
                label=str(label or to)[:80],
                style=style,
                custom_id=ASK_ID.format(marathon_id=int(marathon_id), to=to),
            )
        )

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: Any, match: re.Match):
        return cls(int(match["marathon_id"]), match["to"])

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
        outcome = await answered(
            bot, interaction.guild, interaction.user, self.marathon_id, self.to
        )
        await answer(interaction, outcome.message)


async def answered(bot: Any, guild: Any, actor: Any, marathon_id: Any, to: str) -> Outcome:
    marathon = await get_marathon(bot.db, guild.id, marathon_id)
    if marathon is None:
        return refusal(mt.NO_SUCH_MARATHON.format(given=marathon_id), NO_SUCH, 404)
    return await set_baf_event(bot, guild, actor, marathon, to == baf.YES, by=BY_QUESTION)


__all__ = [
    "AskButton",
    "answered",
    "ask_if_unsure",
    "heads_up_role",
    "note_answer",
    "note_missed",
    "quiet_for",
    "reading_for",
    "reading_now",
    "set_baf_event",
    "settle",
    "speaks_for",
    "state_of",
    "sync",
    "words",
]
