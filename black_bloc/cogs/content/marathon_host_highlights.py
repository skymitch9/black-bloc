"""Each BaF host's public highlight and heads-up, per run they host, in the runner's words and
at the runner's moments: a host never makes a run ours."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from ... import marathon as mt
from ... import marathon_host_highlights as mhh
from ... import marathon_inbox as mi
from ... import shadow as shadow_home
from ...actionlog import log_action
from ...logkinds import VIA_DISCORD, kind_via
from ...panels import Outcome, refusal
from ...settings_store import (
    MARATHON_HOST_HIGHLIGHTS_KEY,
    MARATHON_PING_MINUTES_KEY,
    MARATHON_PUBLIC_ALREADY_KEY,
    MARATHON_PUBLIC_FAILED_KEY,
    MARATHON_PUBLIC_NO_CHANNEL_KEY,
    MARATHON_PUBLIC_NOT_UP_KEY,
    MARATHON_PUBLIC_POSTED_SAID_KEY,
    MARATHON_PUBLIC_REMOVED_SAID_KEY,
    MARATHON_REMINDER_STALE_KEY,
)
from ...spotlight import reason_of
from .marathon import (
    MODE_OFF,
    MODE_ON,
    NO_SUCH,
    channel_login,
    cog_of,
    get_marathon,
    mode_of,
    runs_of,
    update_marathon,
)
from .marathon_hosts import scans
from .marathon_public import (
    edit_public,
    fetch_public,
    public_channel,
    public_text,
    rehearsal_of,
    send_public,
)
from .marathon_public import words as public_words
from .marathon_public_reminders import reminder_channel, reminder_text
from .marathon_public_reminders import wanted as public_reminders_wanted

log = logging.getLogger(__name__)

SHADOW_FEATURE = "marathon_public"
NO_PUBLIC_CODE = "no_public_channel"
FAILED_CODE = "post_failed"


def switched_on(bot: Any, guild_id: int) -> bool:
    return bool(bot.store.get(guild_id, MARATHON_HOST_HIGHLIGHTS_KEY))


def wanted(bot: Any, guild: Any, marathon: Any) -> bool:
    """New posts and heads-ups: the key, a tracked active marathon that scans its hosts."""
    return (
        switched_on(bot, guild.id)
        and bool(mt._cell(marathon, "active"))
        and mi.is_tracked(marathon)
        and mode_of(bot, guild.id) != MODE_OFF
        and scans(bot, guild.id, marathon)
    )


def sent_cache(cog: Any, marathon_id: Any) -> dict[int, tuple[int | None, str]]:
    found = cog.__dict__.setdefault("host_sent", {})
    return found.setdefault(int(marathon_id), {})


def pointer(record: dict[str, Any]) -> dict[str, Any]:
    return {"public_message_id": record["message_id"], "public_channel_id": record["channel_id"]}


async def highlight_text(
    bot: Any, guild: Any, marathon: Any, item: mhh.Hosted, *, removed: bool = False
) -> str:
    return await public_text(bot, guild, marathon, item.run, removed=removed, people=item.hosts)


def details_of(marathon: Any, item: mhh.Hosted, **extra: Any) -> dict[str, Any]:
    return {
        "marathon_id": marathon["id"],
        "run_id": item.run_id,
        "members": item.user_ids,
        "hosts": item.names,
        "game": mt._cell(item.run, "game"),
    } | extra


async def save(bot: Any, marathon: Any, found: list[dict[str, Any]]) -> None:
    await update_marathon(bot.db, marathon["id"], **{mhh.COLUMN: mhh.dump(found)})


async def hosted_of(bot: Any, guild: Any, marathon: Any) -> list[mhh.Hosted]:
    if not scans(bot, guild.id, marathon):
        return []
    return mhh.hosted(await runs_of(bot.db, marathon["id"]))


def attached(found: list[dict[str, Any]], item: mhh.Hosted) -> tuple[dict[str, Any], bool]:
    record = mhh.record_for(found, item)
    if record is None:
        record = mhh.new_record(item)
        found.append(record)
        return (record, True)
    if record.get("hosts") != item.hosts:
        record["hosts"] = [dict(one) for one in item.hosts]
        return (record, True)
    return (record, False)


def member_name(guild: Any, user_id: Any) -> str:
    try:
        member = guild.get_member(int(user_id))
    except (TypeError, ValueError, AttributeError):
        member = None
    return str(getattr(member, "display_name", "") or user_id)


def rehearsing(bot: Any, guild: Any) -> bool:
    return mode_of(bot, guild.id) != MODE_ON


async def put_back(
    cog: Any,
    guild: Any,
    marathon: Any,
    record: dict[str, Any],
    found: list[dict[str, Any]],
    text: str,
    base: dict[str, Any],
    *,
    actor: Any,
    via: str,
) -> int | None:
    bot = cog.bot
    home = (
        shadow_home.channel_id(bot, guild, feature=SHADOW_FEATURE)
        if rehearsing(bot, guild)
        else public_channel(bot, guild.id)
    )
    if home is None or record["channel_id"] != int(home):
        return None
    message, _lost = await fetch_public(bot, guild, pointer(record))
    if message is None or await edit_public(bot, guild, message, text) is not None:
        return None
    record["removed"] = False
    await save(bot, marathon, found)
    sent_cache(cog, marathon["id"])[record["message_id"]] = (record["channel_id"], text)
    await log_action(
        bot,
        guild,
        kind_via("marathon.host_highlight_restored", via),
        actor=actor,
        details=base | {"message_id": str(message.id)} | rehearsal_of(bot, guild),
    )
    return record["channel_id"]


async def post_one(
    cog: Any,
    guild: Any,
    marathon: Any,
    item: mhh.Hosted,
    record: dict[str, Any],
    found: list[dict[str, Any]],
    *,
    actor: Any = None,
    via: str = VIA_DISCORD,
    auto: bool = True,
) -> tuple[str | None, int | None]:
    """`tried` is stored before the send, so a restart mid-send never posts it twice. A highlight
    staff took down comes back in place when it is still where one would go now."""
    bot = cog.bot
    text = await highlight_text(bot, guild, marathon, item)
    base = details_of(marathon, item, auto=auto, via=via)
    if record["message_id"] and record["removed"]:
        back = await put_back(cog, guild, marathon, record, found, text, base, actor=actor, via=via)
        if back is not None:
            return (None, back)
    record["tried"] = True
    await save(bot, marathon, found)
    sent, channel_id, why = await send_public(bot, guild, text, [])
    if sent is None:
        await log_action(
            bot,
            guild,
            kind_via("marathon.host_highlight_failed", via),
            actor=actor,
            details=base | {"step": "post", "reason": why},
        )
        return (why, None)
    record.update(message_id=int(sent.id), channel_id=int(channel_id), removed=False)
    await save(bot, marathon, found)
    sent_cache(cog, marathon["id"])[int(sent.id)] = (int(channel_id), text)
    await log_action(
        bot,
        guild,
        kind_via(
            "marathon.would_post_host_highlight"
            if rehearsing(bot, guild)
            else "marathon.host_highlight_posted",
            via,
        ),
        actor=actor,
        details=base
        | {"message_id": str(sent.id), "channel_id": channel_id, "state": mhh.state_of(item)}
        | rehearsal_of(bot, guild),
    )
    return (None, int(channel_id))


async def follow_one(
    cog: Any, guild: Any, marathon: Any, item: mhh.Hosted, record: dict[str, Any]
) -> bool:
    """An unchanged run costs no Discord call; a message deleted by hand is forgotten (True:
    the record changed)."""
    bot = cog.bot
    text = await highlight_text(bot, guild, marathon, item)
    cache = sent_cache(cog, marathon["id"])
    key = record["message_id"]
    if cache.get(key) == (record["channel_id"], text):
        return False
    message, lost = await fetch_public(bot, guild, pointer(record))
    if message is None:
        if not lost:
            return False
        cache.pop(key, None)
        await log_action(
            bot,
            guild,
            "marathon.host_highlight_lost",
            details=details_of(marathon, item, message_id=str(key)),
        )
        record.update(message_id=None, channel_id=None)
        return True
    if (getattr(message, "content", None) or "").endswith(text):
        cache[key] = (record["channel_id"], text)
        return False
    why = await edit_public(bot, guild, message, text)
    if why is not None:
        await log_action(
            bot,
            guild,
            "marathon.host_highlight_failed",
            details=details_of(marathon, item, step="edit", reason=why),
        )
        return False
    cache[key] = (record["channel_id"], text)
    await log_action(
        bot,
        guild,
        "marathon.would_edit_host_highlight"
        if rehearsing(bot, guild)
        else "marathon.host_highlight_edited",
        details=details_of(marathon, item, message_id=str(key), state=mhh.state_of(item))
        | rehearsal_of(bot, guild),
    )
    return False


async def sync_host_highlights(cog: Any, guild: Any, marathon: Any) -> None:
    """Under the marathon lock: every post that is up follows its run to the end, whatever the
    switches say now."""
    bot = cog.bot
    fresh = await get_marathon(bot.db, guild.id, marathon["id"]) if marathon else None
    if fresh is None or not mi.is_tracked(fresh) or mode_of(bot, guild.id) == MODE_OFF:
        return
    try:
        found = mhh.records(fresh)
        if not any(mhh.is_up(one) for one in found):
            return
        changed = False
        seen: set[int] = set()
        for item in await hosted_of(bot, guild, fresh):
            if not mhh.is_up(mhh.record_for(found, item)):
                continue
            record, moved = attached(found, item)
            seen.add(item.run_id)
            changed = moved or changed
            if await follow_one(cog, guild, fresh, item, record):
                changed = True
        runs = await runs_of(bot.db, fresh["id"])
        for record in found:
            if record["run_id"] in seen or not mhh.is_up(record):
                continue
            item = mhh.left_behind(record, runs)
            if item is not None and await follow_one(cog, guild, fresh, item, record):
                changed = True
        if changed:
            await save(bot, fresh, found)
    except Exception as exc:
        log.warning("marathon: the host highlights failed — %s", reason_of(exc))


async def went_live(cog: Any, guild: Any, marathon: Any, run_id: Any) -> None:
    """The moment a hosted run goes live, as a runner's auto-highlight: posted when the
    marathon's Auto-highlight switch is on, never again once tried or taken down."""
    bot = cog.bot
    try:
        fresh = await get_marathon(bot.db, guild.id, marathon["id"]) if marathon else None
        if fresh is None or not wanted(bot, guild, fresh):
            return
        if public_channel(bot, guild.id) is None:
            return
        item = next(
            (one for one in await hosted_of(bot, guild, fresh) if one.run_id == int(run_id)),
            None,
        )
        if item is None:
            return
        found = mhh.records(fresh)
        if not mhh.auto_wanted(fresh, item, mhh.record_for(found, item)):
            return
        record, _moved = attached(found, item)
        await post_one(cog, guild, fresh, item, record, found)
    except Exception as exc:
        log.warning("marathon: a host auto-highlight failed — %s", reason_of(exc))


async def remind_hosts(cog: Any, guild: Any, marathon: Any, now: datetime) -> None:
    """One public heads-up per hosted run at a runner reminder's moment (marathon_ping_minutes);
    the marker is stored before the send, so a restart never posts it twice."""
    bot = cog.bot
    fresh = await get_marathon(bot.db, guild.id, marathon["id"]) if marathon else None
    if fresh is None or not wanted(bot, guild, fresh):
        return
    if not public_reminders_wanted(bot, guild.id):
        return
    try:
        minutes = int(bot.store.get(guild.id, MARATHON_PING_MINUTES_KEY))
        stale = int(bot.store.get(guild.id, MARATHON_REMINDER_STALE_KEY))
        found = mhh.records(fresh)
        for item in await hosted_of(bot, guild, fresh):
            record = mhh.record_for(found, item)
            if mhh.rearm(record, item, now, minutes=minutes):
                record["reminded"] = False
                await save(bot, fresh, found)
            due = mhh.heads_up_due(item, record, now, minutes=minutes, stale_minutes=stale)
            if due is None:
                continue
            record, _moved = attached(found, item)
            record["reminded"] = True
            await save(bot, fresh, found)
            base = details_of(fresh, item, mark=minutes)
            if due == mhh.SKIP:
                await log_action(
                    bot,
                    guild,
                    "marathon.host_reminder_skipped",
                    details=base | {"because": "late"},
                )
                continue
            await heads_up(bot, guild, fresh, item, base)
    except Exception as exc:
        log.warning("marathon: a host heads-up failed — %s", reason_of(exc))


async def heads_up(
    bot: Any, guild: Any, marathon: Any, item: mhh.Hosted, base: dict[str, Any]
) -> None:
    home = reminder_channel(bot, guild.id)
    if home is None:
        await log_action(
            bot, guild, "marathon.host_reminder_failed", details=base | {"reason": "no_channel"}
        )
        return
    login = await channel_login(bot, marathon)
    url = mt.run_url(item.run, login, marathon["schedule_url"], people=item.hosts)
    text = reminder_text(bot, guild, marathon, item.run, url=url, people=item.hosts)
    message, channel_id, why = await send_public(bot, guild, text, [], home=home)
    details = base | {
        "channel_id": channel_id,
        "message_id": str(getattr(message, "id", "")) or None,
    }
    if message is None:
        await log_action(
            bot, guild, "marathon.host_reminder_failed", details=details | {"reason": why}
        )
        return
    await log_action(
        bot,
        guild,
        "marathon.would_remind_host" if rehearsing(bot, guild) else "marathon.host_reminded",
        details=details | rehearsal_of(bot, guild),
    )


async def take_down(
    cog: Any,
    guild: Any,
    marathon: Any,
    item: mhh.Hosted,
    record: dict[str, Any],
    found: list[dict[str, Any]],
    *,
    actor: Any,
    via: str,
) -> None:
    """The decision is stored first; the edit to the taken-down line may fail on its own."""
    bot = cog.bot
    record["removed"] = True
    await save(bot, marathon, found)
    sent_cache(cog, marathon["id"]).pop(record["message_id"], None)
    message, _lost = await fetch_public(bot, guild, pointer(record))
    edited = False
    if message is not None:
        text = await highlight_text(bot, guild, marathon, item, removed=True)
        why = await edit_public(bot, guild, message, text)
        edited = why is None
        if why is not None:
            await log_action(
                bot,
                guild,
                kind_via("marathon.host_highlight_failed", via),
                actor=actor,
                details=details_of(marathon, item, step="remove", reason=why, via=via),
            )
    await log_action(
        bot,
        guild,
        kind_via("marathon.host_highlight_removed", via),
        actor=actor,
        details=details_of(
            marathon, item, message_id=str(record["message_id"]), edited=edited, via=via
        ),
    )


async def post_move(
    cog: Any,
    guild: Any,
    marathon: Any,
    item: mhh.Hosted,
    record: dict[str, Any],
    found: list[dict[str, Any]],
    *,
    actor: Any,
    via: str,
) -> Outcome:
    bot = cog.bot
    if mhh.is_up(record):
        return Outcome(
            True,
            public_words(
                bot,
                guild.id,
                MARATHON_PUBLIC_ALREADY_KEY,
                runner=item.names,
                channel=f"<#{record['channel_id']}>",
            ),
        )
    if public_channel(bot, guild.id) is None:
        return refusal(
            public_words(bot, guild.id, MARATHON_PUBLIC_NO_CHANNEL_KEY), NO_PUBLIC_CODE, 409
        )
    why, channel_id = await post_one(
        cog, guild, marathon, item, record, found, actor=actor, via=via, auto=False
    )
    if why is not None:
        return refusal(
            public_words(bot, guild.id, MARATHON_PUBLIC_FAILED_KEY, runner=item.names, reason=why),
            FAILED_CODE,
            409,
        )
    return Outcome(
        True,
        public_words(
            bot,
            guild.id,
            MARATHON_PUBLIC_POSTED_SAID_KEY,
            runner=item.names,
            channel=f"<#{channel_id}>",
        ),
    )


async def remove_move(
    cog: Any,
    guild: Any,
    marathon: Any,
    item: mhh.Hosted,
    record: dict[str, Any],
    found: list[dict[str, Any]],
    *,
    actor: Any,
    via: str,
) -> Outcome:
    bot = cog.bot
    if not mhh.is_up(record):
        return Outcome(
            True, public_words(bot, guild.id, MARATHON_PUBLIC_NOT_UP_KEY, runner=item.names)
        )
    await take_down(cog, guild, marathon, item, record, found, actor=actor, via=via)
    return Outcome(
        True,
        public_words(
            bot,
            guild.id,
            MARATHON_PUBLIC_REMOVED_SAID_KEY,
            runner=item.names,
            channel=f"<#{record['channel_id']}>",
        ),
    )


MOVES = {mhh.POST: post_move, mhh.REMOVE: remove_move}


def fits_move(move: str, record: Any, item: mhh.Hosted) -> bool:
    if move == mhh.REMOVE:
        return mhh.is_up(record)
    return not mhh.is_up(record) and mhh.postable(item)


async def press(
    bot: Any,
    guild: Any,
    actor: Any,
    marathon: Any,
    user_id: Any,
    to: Any,
    *,
    run_id: Any = None,
    via: str = VIA_DISCORD,
) -> Outcome:
    """Staff final say on a host's highlight: post (or put back) or take down — for the run
    `run_id`, or else every run they host that the move fits."""
    move = mhh.clean_move(to)
    if move is None:
        return refusal(mhh.BAD_MOVE, mhh.BAD_MOVE_CODE, 422)
    cog = cog_of(bot)
    async with cog.lock(marathon["id"]):
        fresh = await get_marathon(bot.db, guild.id, marathon["id"])
        if fresh is None:
            return refusal(mt.NO_SUCH_MARATHON.format(given=marathon["id"]), NO_SUCH, 404)
        if not scans(bot, guild.id, fresh):
            return refusal(
                mhh.NOT_SCANNED.format(marathon=fresh["name"]), mhh.NOT_SCANNED_CODE, 409
            )
        mine = [
            one
            for one in await hosted_of(bot, guild, fresh)
            if str(user_id) in map(str, one.user_ids)
            and (run_id in (None, "") or str(run_id) == str(one.run_id))
        ]
        if not mine:
            return refusal(
                mhh.NOT_HOSTING.format(name=member_name(guild, user_id), marathon=fresh["name"]),
                mhh.NOT_HOSTING_CODE,
                404,
            )
        found = mhh.records(fresh)
        if len(mine) > 1:
            mine = [
                one for one in mine if fits_move(move, mhh.record_for(found, one), one)
            ] or mine[:1]
        said = []
        for item in mine:
            record, _moved = attached(found, item)
            outcome = await MOVES[move](
                cog, guild, fresh, item, record, found, actor=actor, via=via
            )
            await save(bot, fresh, found)
            if not outcome.ok:
                return outcome
            said.append(outcome.message)
    return Outcome(True, "\n".join(dict.fromkeys(said)))


async def state_for(bot: Any, guild: Any, marathon: Any) -> dict[int, dict[str, Any]]:
    """Per BaF host: each hosted run's highlight — up, or could be posted — and the whole."""
    found = mhh.records(marathon)
    posting = public_channel(bot, guild.id) is not None and mode_of(bot, guild.id) != MODE_OFF
    shown: dict[int, dict[str, Any]] = {}
    for item in await hosted_of(bot, guild, marathon):
        record = mhh.record_for(found, item)
        up = mhh.is_up(record)
        one = {
            "run_id": str(item.run_id),
            "up": up,
            "channel_id": str(record["channel_id"]) if up else None,
            "can_post": posting and not up and mhh.postable(item),
        }
        for user_id in item.user_ids:
            mine = shown.setdefault(
                user_id, {"up": False, "channel_id": None, "can_post": False, "runs": []}
            )
            mine["runs"].append(one)
            mine["up"] = mine["up"] or up
            mine["can_post"] = mine["can_post"] or one["can_post"]
            mine["channel_id"] = mine["channel_id"] or one["channel_id"]
    return shown


def run_state(shown: dict[int, dict[str, Any]], user_id: Any, run_id: Any = None) -> Any:
    """The hosted run `run_id`, or the host's whole answer; None for someone who hosts none."""
    found = shown.get(int(user_id)) if user_id else None
    if found is None or run_id is None:
        return found
    return next((one for one in found["runs"] if one["run_id"] == str(run_id)), None)


__all__ = [
    "press",
    "remind_hosts",
    "run_state",
    "state_for",
    "switched_on",
    "sync_host_highlights",
    "wanted",
    "went_live",
]
