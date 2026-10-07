"""A BaF event: the staff answer, the one question to Leads, and each show-day's one
Marathon-role ping."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta
from typing import Any

import discord

from ... import marathon as mt
from ... import marathon_baf_event as baf
from ... import marathon_host_highlights as mhh
from ... import marathon_inbox as mi
from ... import marathon_reminder_posts as mrem
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
    MARATHON_BAF_EVENT_ASK_FAILED_KEY,
    MARATHON_BAF_EVENT_ASK_NO_KEY,
    MARATHON_BAF_EVENT_ASK_NOWHERE_KEY,
    MARATHON_BAF_EVENT_ASK_PENDING_KEY,
    MARATHON_BAF_EVENT_ASK_PERCENT_KEY,
    MARATHON_BAF_EVENT_ASK_ROLE_KEY,
    MARATHON_BAF_EVENT_ASK_TEXT_KEY,
    MARATHON_BAF_EVENT_ASK_YES_KEY,
    MARATHON_BAF_EVENT_DAY_LINE_KEY,
    MARATHON_BAF_EVENT_LINE_KEY,
    MARATHON_BAF_EVENT_MIN_RUNS_KEY,
    MARATHON_BAF_EVENT_NAMES_KEY,
    MARATHON_BAF_EVENT_PING_DONE_KEY,
    MARATHON_BAF_EVENT_PING_FALLBACK_KEY,
    MARATHON_BAF_EVENT_PING_MINUTES_KEY,
    MARATHON_BAF_EVENT_PING_NO_RUN_KEY,
    MARATHON_BAF_EVENT_PING_NOBODY_KEY,
    MARATHON_BAF_EVENT_PING_NONE_KEY,
    MARATHON_BAF_EVENT_PING_UNCONFIRMED_KEY,
    MARATHON_BAF_EVENT_PING_WILL_KEY,
    MARATHON_BAF_EVENT_REASON_ALL_RUNS_KEY,
    MARATHON_BAF_EVENT_REASON_FEW_RUNS_KEY,
    MARATHON_BAF_EVENT_REASON_LEADS_KEY,
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
ASK_TRIES = 3
NEVER_POSTED = "never_posted"
LINES_MAX = 3
BY_QUESTION = "question"
NO_QUESTION = (
    "That question is not one the bot still holds for **{marathon}**, so nothing was changed. "
    "Use the BaF event switch on the thread's controls instead."
)
NO_QUESTION_CODE = "no_baf_question"
ANSWER_KEYS = {
    baf.YES: MARATHON_BAF_EVENT_WORD_YES_KEY,
    baf.NO: MARATHON_BAF_EVENT_WORD_NO_KEY,
    baf.UNSURE: MARATHON_BAF_EVENT_WORD_UNSURE_KEY,
    baf.FOLLOW: MARATHON_BAF_EVENT_WORD_FOLLOW_KEY,
}
REASON_KEYS = {
    baf.BY_STAFF: MARATHON_BAF_EVENT_REASON_STAFF_KEY,
    baf.BY_LEADS: MARATHON_BAF_EVENT_REASON_LEADS_KEY,
    baf.BY_NAME: MARATHON_BAF_EVENT_REASON_NAME_KEY,
    baf.BY_RUNS: MARATHON_BAF_EVENT_REASON_ALL_RUNS_KEY,
    baf.BY_SHARE: MARATHON_BAF_EVENT_REASON_SHARE_KEY,
    baf.BY_FEW: MARATHON_BAF_EVENT_REASON_FEW_RUNS_KEY,
    baf.BY_MIXED: MARATHON_BAF_EVENT_REASON_MIXED_KEY,
    baf.BY_NO_RUNS: MARATHON_BAF_EVENT_REASON_NO_RUNS_KEY,
}
PING_KEYS = {
    baf.PING_WILL: MARATHON_BAF_EVENT_PING_WILL_KEY,
    baf.PING_DONE: MARATHON_BAF_EVENT_PING_DONE_KEY,
    baf.PING_UNCONFIRMED: MARATHON_BAF_EVENT_PING_UNCONFIRMED_KEY,
    baf.NOBODY_TO_NAME: MARATHON_BAF_EVENT_PING_NOBODY_KEY,
    baf.NO_BAF_RUN: MARATHON_BAF_EVENT_PING_NO_RUN_KEY,
    baf.MARKS_SPENT: MARATHON_BAF_EVENT_PING_NONE_KEY,
}
ASK_LINE_KEYS = {
    baf.ASK_PENDING: MARATHON_BAF_EVENT_ASK_PENDING_KEY,
    baf.ASK_FAILED: MARATHON_BAF_EVENT_ASK_FAILED_KEY,
    baf.ASK_NOWHERE: MARATHON_BAF_EVENT_ASK_NOWHERE_KEY,
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


def speaks_for(bot: Any, guild: Any, marathon: Any) -> Any:
    return lambda row: bool(people_for(bot, guild, marathon, row))


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
    plan = baf.plan(found, current, mark, speaks=speaks_for(cog.bot, guild, fresh))
    if plan.kind == baf.PER_RUN:
        if int(mark) != ping_mark:
            return (None, None)
        verdict = verdict_for(bot, guild, fresh)
        if plan.day is None or not verdict.mentions:
            return (verdict, None)
        return (verdict, await claim_day(cog, fresh, found, plan, current, mark, per_run=True))
    starts = baf.span_of(plan.day)[0]
    verdict = mrp.on_day(verdict_for(bot, guild, fresh), starts.isoformat() if starts else None)
    if plan.kind == baf.QUIET:
        if int(mark) > found.limit and int(mark) != ping_mark:
            return (None, None)
        return (mrp.unsent(verdict, plan.reason), None)
    if not verdict.mentions:
        return (verdict, None)
    return (verdict, await claim_day(cog, fresh, found, plan, current, mark))


async def claim_day(
    cog: Any, marathon: Any, found: baf.Reading, plan: baf.Plan, row: Any, mark: int, **extra: Any
) -> dict[str, Any]:
    claim = baf.record_for(plan.day, row, mark, cog.clock(), reason=plan.judgement.reason, **extra)
    await update_marathon(
        cog.bot.db, marathon["id"], **{baf.PINGS_COLUMN: baf.dump_pings([*found.records, claim])}
    )
    return claim


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
    bot: Any, guild: Any, found: baf.Reading, state: baf.DayState, ping: str, role: str
) -> str:
    """What the day's one ping did, may have done or will do; empty where the per-run rule
    decides or the role would not be mentioned anyway."""
    key = PING_KEYS.get(ping)
    if key is None:
        return ""
    record, row = state.record, state.carrier
    game = record.get("game") if record is not None else row["game"] if row is not None else ""
    said = words(
        bot,
        guild.id,
        key,
        role=role,
        minutes=record.get("mark") if record is not None else state.carrier_mark,
        game=game or "",
    )
    if ping == baf.PING_WILL and found.fell_back:
        said += " " + words(
            bot,
            guild.id,
            MARATHON_BAF_EVENT_PING_FALLBACK_KEY,
            wanted=found.wanted_mark,
            minutes=found.limit,
        )
    return said


def ask_words(bot: Any, guild: Any, judged: baf.Judgement, ask: str | None) -> str:
    """What became of the question while the bot is still not sure about the event."""
    if judged.answer != baf.UNSURE:
        return ""
    key = ASK_LINE_KEYS.get(ask)
    return words(bot, guild.id, key) if key else ""


def shown(states: list[baf.DayState]) -> list[baf.DayState]:
    ahead = [one for one in states if not one.over]
    return ahead[:LINES_MAX] if ahead else states[-1:]


def state_of(
    bot: Any, guild: Any, marathon: Any, rows: Any, *, mention: bool = False
) -> dict[str, Any]:
    """The tri-state, the event's answer and why in one line, then what becomes of each
    show-day's ping."""
    found = reading_for(bot, guild.id, marathon, rows)
    states = baf.day_states(found, speaks=speaks_for(bot, guild, marathon))
    verdict = verdict_for(bot, guild, marathon)
    role = role_word(verdict, mention=mention)
    own = baf.stored(marathon)
    judged = baf.judgement_of(found)
    worked = baf.judgement_of(found, own=False)
    ask = baf.ask_state(baf.question(found.asks))
    line = " ".join(
        one
        for one in (
            words(
                bot,
                guild.id,
                MARATHON_BAF_EVENT_LINE_KEY,
                marathon=marathon["name"],
                answer=answer_word(bot, guild.id, judged.answer),
                reason=reason_words(bot, guild.id, judged),
            ),
            ask_words(bot, guild, judged, ask),
        )
        if one
    )
    days = []
    for state in states:
        ping = baf.ping_state(state, verdict.mentions)
        said = ping_words(bot, guild, found, state, ping, role)
        runs, ours = baf.counts(state.day)
        days.append(
            {
                "starts_at": state.starts_at.isoformat() if state.starts_at else None,
                "runs": runs,
                "baf": ours,
                "over": state.over,
                "governed": state.governed,
                "ping": ping,
                "no_ping": state.cause,
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
                "line": said
                and words(
                    bot,
                    guild.id,
                    MARATHON_BAF_EVENT_DAY_LINE_KEY,
                    day=day_word(bot, guild, marathon, state.starts_at, mention=mention),
                    ping=said,
                ),
            }
        )
    listed = shown(states)
    kept = {id(one) for one in listed}
    return {
        "own": own,
        "choice": baf.choice_of(own),
        "answer": judged.answer,
        "reason": judged.reason,
        "runs": judged.runs,
        "baf": judged.baf,
        "answer_word": answer_word(bot, guild.id, judged.answer),
        "reason_word": reason_words(bot, guild.id, judged),
        "worked_out": {
            "answer": worked.answer,
            "reason": worked.reason,
            "answer_word": answer_word(bot, guild.id, worked.answer),
            "reason_word": reason_words(bot, guild.id, worked),
        },
        "asked": any(one.get("message_id") for one in found.asks),
        "ask": ask,
        "line": line,
        "ping_minutes": found.limit,
        "ping_fell_back": found.fell_back,
        "days": days,
        "lines": [
            line,
            *[
                one["line"]
                for one, state in zip(days, states, strict=True)
                if id(state) in kept and one["line"]
            ],
        ],
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
        "per_run": bool(record.get(baf.PER_RUN)),
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
    """The marathon's switch: yes, no, or None to follow the answer to its question and then
    what the bot works out. The thread controls and the site come here."""
    from .marathon_thread_controls import controls_changed

    understood, wanted = baf.clean(given)
    if not understood:
        return refusal(baf.BAD_CHOICE.format(marathon=marathon["name"]), baf.BAD_CHOICE_CODE, 422)
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
        held = [one for one in baf.asks_of(fresh) if one.get("message_id") or one.get("answer")]
        await update_marathon(
            bot.db,
            fresh["id"],
            **{
                baf.COLUMN: None if wanted is None else int(wanted),
                baf.ASK_COLUMN: baf.dump_asks(held),
            },
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
    await controls_changed(bot, guild, fresh["id"])
    return Outcome(
        True,
        words(bot, guild.id, MARATHON_BAF_EVENT_SET_SAID_KEY, marathon=fresh["name"], answer=said),
        value=await get_marathon(bot.db, guild.id, fresh["id"]),
    )


def question_of(asks: Any, message_id: Any) -> dict[str, Any] | None:
    posted = [one for one in asks or () if one.get("message_id")]
    if message_id is None:
        return posted[0] if len(posted) == 1 else None
    return next((one for one in posted if int(one["message_id"]) == int(message_id)), None)


async def set_answer(
    bot: Any,
    guild: Any,
    actor: Any,
    marathon: Any,
    message_id: Any,
    yes: bool,
    *,
    via: str = VIA_DISCORD,
) -> Outcome:
    """The answer to the event's question, for every show-day; the marathon's switch is left
    as it stands and still beats it."""
    from .marathon_thread_controls import controls_changed

    cog = cog_of(bot)
    wanted = baf.YES if yes else baf.NO
    async with cog.lock(marathon["id"]):
        fresh = await get_marathon(bot.db, guild.id, marathon["id"])
        if fresh is None:
            return refusal(mt.NO_SUCH_MARATHON.format(given=marathon["id"]), NO_SUCH, 404)
        asks = baf.asks_of(fresh)
        record = question_of(asks, message_id)
        if record is None:
            return refusal(NO_QUESTION.format(marathon=fresh["name"]), NO_QUESTION_CODE, 404)
        was = baf.answer_of(asks)
        fields = {"marathon": fresh["name"], "answer": answer_word(bot, guild.id, wanted)}
        if was == wanted:
            return Outcome(
                True,
                words(bot, guild.id, MARATHON_BAF_EVENT_SAME_SAID_KEY, **fields),
                value=fresh,
            )
        said = record | {
            "answer": wanted,
            "answered_by": actor_id(actor),
            "answered_at": cog.clock().isoformat(),
        }
        await update_marathon(
            bot.db,
            fresh["id"],
            **{baf.ASK_COLUMN: baf.dump_asks([*baf.without(asks, record), said])},
        )
    await log_action(
        bot,
        guild,
        kind_via("marathon.baf_event_set", via),
        actor=actor,
        details={
            "marathon_id": fresh["id"],
            "name": fresh["name"],
            "from": was or baf.FOLLOW,
            "to": wanted,
            "by": BY_QUESTION,
            "via": via,
        },
    )
    await note_answer(bot, guild, fresh, said, actor, fields["answer"])
    await controls_changed(bot, guild, fresh["id"])
    return Outcome(
        True,
        words(bot, guild.id, MARATHON_BAF_EVENT_SET_SAID_KEY, **fields),
        value=await get_marathon(bot.db, guild.id, fresh["id"]),
    )


async def note_answer(
    bot: Any, guild: Any, marathon: Any, ask: dict[str, Any], actor: Any, said: str
) -> None:
    """The question says who answered what; the answer is stored already, so a failed edit
    changes nothing."""
    from .marathon_inbox import find_channel, reopened

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


def may_ask(record: Any, same: bool, now: datetime) -> bool:
    """Once per marathon: never again once posted or answered; a post that failed, or a claim
    nothing followed, waits twice as long each time and stops after ASK_TRIES, until the
    event's runs change."""
    if not record or record.get("blocked"):
        return True
    if record.get("message_id") or record.get("answer"):
        return False
    if not same:
        return True
    if record.get("gave_up"):
        return False
    last = parse_ts(record.get("failed_at") or record.get("asked_at"))
    tries = max(1, int(record.get("tries") or 1))
    return last is None or now - last >= RETRY_AFTER * 2 ** (tries - 1)


async def put_ask(bot: Any, guild: Any, marathon: Any, old: Any, new: Any) -> None:
    fresh = await get_marathon(bot.db, guild.id, marathon["id"]) or marathon
    kept = [one for one in baf.asks_of(fresh) if one != old]
    await update_marathon(bot.db, marathon["id"], **{baf.ASK_COLUMN: baf.dump_asks([*kept, new])})


async def ask_thread(bot: Any, guild: Any, marathon: Any) -> Any:
    from .marathon_inbox import find_channel
    from .marathon_thread_controls import has_home

    if not has_home(bot, guild, marathon):
        return None
    thread, _lost = await find_channel(bot, guild, marathon["thread_id"])
    guard = getattr(bot, "guard", None)
    if thread is None or (guard is not None and not guard.allows_channel(thread.id)):
        return None
    return thread


async def ask_if_unsure(
    cog: Any, guild: Any, marathon: Any, found: baf.Reading, states: list[baf.DayState], now: Any
) -> bool:
    """The event's one question, while nothing has decided it and a show-day is still to
    come."""
    if not baf.asks(found, states):
        return False
    judged = baf.judgement_of(found)
    record = baf.question(found.asks)
    same = bool(record) and baf.same_schedule(record, found.rows, judged)
    if not may_ask(record, same, now):
        return False
    return await ask_about(cog, guild, marathon, found, judged, record, now)


async def ask_about(
    cog: Any,
    guild: Any,
    marathon: Any,
    found: baf.Reading,
    judged: baf.Judgement,
    record: Any,
    now: datetime,
) -> bool:
    from .marathon_inbox import reopened

    bot = cog.bot
    event = {
        key: value
        for key, value in baf.record_for(found.rows, None, None, now).items()
        if key in ("runs", "starts_at", "ends_at")
    } | {baf.EVENT: True, "baf": judged.baf}
    thread = await ask_thread(bot, guild, marathon)
    if thread is None:
        if not (record or {}).get("blocked"):
            await put_ask(bot, guild, marathon, record, event | {"blocked": True})
        return False
    counted = bool(record) and baf.same_schedule(record, found.rows, judged)
    tries = (int(record.get("tries") or 0) if counted else 0) + 1
    base = {
        "marathon_id": marathon["id"],
        "name": marathon["name"],
        "thread_id": int(thread.id),
        "runs": judged.runs,
        "baf": judged.baf,
    }

    async def failed(reason: str, old: Any, tried: int) -> bool:
        gave_up = tried >= ASK_TRIES
        await put_ask(
            bot,
            guild,
            marathon,
            old,
            event
            | {
                "failed_at": now.isoformat(),
                "reason": reason,
                "tries": tried,
                "gave_up": gave_up,
            },
        )
        await log_action(
            bot,
            guild,
            "marathon.baf_event_ask_failed",
            details=base | {"reason": reason, "try": tried, "gave_up": gave_up},
        )
        return False

    if tries > ASK_TRIES:
        return await failed(NEVER_POSTED, record, ASK_TRIES)
    role = ask_role(bot, guild) if verdict_for(bot, guild, marathon).mentions else None
    text = ping_prefix(getattr(role, "id", None)) + words(
        bot,
        guild.id,
        MARATHON_BAF_EVENT_ASK_TEXT_KEY,
        marathon=marathon["name"],
        baf=judged.baf,
        runs=judged.runs,
    )
    claim = event | {"asked_at": now.isoformat(), "claimed": True, "tries": tries}
    await put_ask(bot, guild, marathon, record, claim)
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
        return await failed(reason_of(exc), claim, tries)
    asked = event | {
        "asked_at": now.isoformat(),
        "channel_id": int(thread.id),
        "message_id": int(message.id),
        "text": text,
        "tries": tries,
    }
    await put_ask(bot, guild, marathon, claim, asked)
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


async def reconcile(
    cog: Any, guild: Any, marathon: Any, found: baf.Reading, rows: Any
) -> baf.Reading:
    """A claim nothing marked sent: confirmed from what its run remembers posting, given
    back, or kept closing its day with one row that says so."""
    bot = cog.bot
    role_id = verdict_for(bot, guild, marathon).configured
    kept: list[dict[str, Any]] = []
    silenced: list[dict[str, Any]] = []
    for record in found.records:
        if record.get("missed") or record.get("sent") or record.get("unconfirmed"):
            kept.append(record)
            continue
        what, message_id, channel_id = baf.proof_of(record, rows, role_id)
        if what == baf.SENT:
            kept.append(record | {"sent": True, "message_id": message_id, "channel_id": channel_id})
        elif what == baf.UNKNOWN and not closes(found, record):
            kept.append(record)
        elif what == baf.UNKNOWN:
            kept.append(record | {"unconfirmed": True})
            silenced.append(record)
    if kept == found.records:
        return found
    await update_marathon(bot.db, marathon["id"], **{baf.PINGS_COLUMN: baf.dump_pings(kept)})
    for one in silenced:
        await log_action(
            bot,
            guild,
            "marathon.baf_event_ping_unconfirmed",
            details={
                "marathon_id": marathon["id"],
                "name": marathon["name"],
                "day": one.get("starts_at"),
                "run_id": one.get("run_id"),
                "game": one.get("game"),
                "mark": one.get("mark"),
                "claimed_at": one.get("at"),
            },
        )
    return found._replace(records=kept)


def closes(found: baf.Reading, record: dict[str, Any]) -> bool:
    """Whether the record closes a day as things stand: any day's own ping does, a per-run
    mention only while the marathon is a BaF event."""
    if not record.get(baf.PER_RUN):
        return True
    return baf.judgement_of(found).yes and any(
        baf.covers(record, day, found.days) for day in found.days
    )


async def note_host_pings(
    cog: Any, guild: Any, marathon: Any, found: baf.Reading, rows: Any
) -> baf.Reading:
    """A host block's heads-up that carried the Marathon role counts as a per-run mention of
    its day."""
    bot = cog.bot
    role_id = verdict_for(bot, guild, marathon).configured
    known = {one.get("message_id") for one in found.records if one.get("host")}
    added = []
    for block in mhh.records(marathon) if role_id else ():
        copy = (block.get(mrem.HOST_FIELD) or {}).get(found.ping_mark, {}).get(mrem.PUBLIC)
        if not copy or f"<@&{int(role_id)}>" not in str(copy.get("head") or ""):
            continue
        row = next((one for one in rows if one["id"] == block.get("start_run_id")), None)
        day = baf.day_of(row, found.days) if row is not None else None
        if day is None or copy.get("message_id") in known:
            continue
        added.append(
            baf.record_for(
                day,
                row,
                found.ping_mark,
                cog.clock(),
                per_run=True,
                host=True,
                sent=True,
                message_id=copy.get("message_id"),
                channel_id=copy.get("channel_id"),
            )
        )
    if not added:
        return found
    records = [*found.records, *added]
    await update_marathon(bot.db, marathon["id"], **{baf.PINGS_COLUMN: baf.dump_pings(records)})
    return found._replace(records=records)


async def note_missed(
    cog: Any, guild: Any, marathon: Any, found: baf.Reading, states: Any, now: datetime
) -> None:
    """One row for a BaF event day whose ping has nothing left to ride, saying which of the
    three causes it was."""
    bot = cog.bot
    if not verdict_for(bot, guild, marathon).mentions:
        return
    records = list(found.records)
    added = []
    for state in states:
        if not state.judgement.yes or state.record is not None or state.carrier is not None:
            continue
        if state.over or state.starts_at is None:
            continue
        if baf.missed(records, state.day, found.days) is not None:
            continue
        if now < state.starts_at - timedelta(minutes=found.limit):
            continue
        if state.cause == baf.NO_BAF_RUN and baf.may_be_matched(state.day, now):
            continue
        added.append(
            baf.record_for(
                state.day,
                None,
                None,
                now,
                missed=True,
                reason=state.judgement.reason,
                because=state.cause,
            )
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
                "because": one["because"],
                "reason": one["reason"],
            },
        )


async def sync(cog: Any, guild: Any, marathon: Any, now: datetime) -> None:
    """The minute tick, with the marathon's lock held: settle what a stopped tick left, ask
    the event's question once, and say so once when a BaF event day has nothing left to carry
    its ping."""
    bot = cog.bot
    if marathon is None or not mi.is_tracked(marathon) or mode_of(bot, guild.id) == MODE_OFF:
        return
    try:
        fresh = await get_marathon(bot.db, guild.id, marathon["id"])
        if fresh is None:
            return
        rows = await runs_of(bot.db, fresh["id"])
        found = reading_for(bot, guild.id, fresh, rows)
        found = await reconcile(cog, guild, fresh, found, rows)
        found = await note_host_pings(cog, guild, fresh, found, rows)
        states = baf.day_states(found, speaks=speaks_for(cog.bot, guild, fresh))
        if await ask_if_unsure(cog, guild, fresh, found, states, now):
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
            bot,
            interaction.guild,
            interaction.user,
            self.marathon_id,
            self.to,
            getattr(getattr(interaction, "message", None), "id", None),
        )
        await answer(interaction, outcome.message)


async def answered(
    bot: Any, guild: Any, actor: Any, marathon_id: Any, to: str, message_id: Any = None
) -> Outcome:
    """A press on the event's question; with no message given, the marathon's only one."""
    marathon = await get_marathon(bot.db, guild.id, marathon_id)
    if marathon is None:
        return refusal(mt.NO_SUCH_MARATHON.format(given=marathon_id), NO_SUCH, 404)
    return await set_answer(bot, guild, actor, marathon, message_id, to == baf.YES)


__all__ = [
    "AskButton",
    "answered",
    "ask_about",
    "ask_if_unsure",
    "heads_up_role",
    "note_answer",
    "note_host_pings",
    "note_missed",
    "quiet_for",
    "reading_for",
    "reading_now",
    "reconcile",
    "set_baf_event",
    "set_answer",
    "settle",
    "speaks_for",
    "state_of",
    "sync",
    "words",
]
