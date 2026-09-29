"""Each BaF host's public highlight and heads-up, beside the runner highlights and apart from
them: a host never makes a run ours."""

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
from ...marathon_sources import schedule_page
from ...panels import Outcome, refusal
from ...settings_store import (
    MARATHON_HOST_HIGHLIGHT_DONE_TEMPLATE_KEY,
    MARATHON_HOST_HIGHLIGHT_LIVE_TEMPLATE_KEY,
    MARATHON_HOST_HIGHLIGHT_TEMPLATE_KEY,
    MARATHON_HOST_HIGHLIGHTS_KEY,
    MARATHON_HOST_REMINDER_TEMPLATE_KEY,
    MARATHON_PART_HOST_KEY,
    MARATHON_PING_MINUTES_KEY,
    MARATHON_PUBLIC_ALREADY_KEY,
    MARATHON_PUBLIC_FAILED_KEY,
    MARATHON_PUBLIC_NO_CHANNEL_KEY,
    MARATHON_PUBLIC_NOT_UP_KEY,
    MARATHON_PUBLIC_POSTED_SAID_KEY,
    MARATHON_PUBLIC_REMOVED_KEY,
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
    said_default,
    update_marathon,
)
from .marathon_hosts import scans
from .marathon_public import edit_public, fetch_public, public_channel, rehearsal_of, send_public
from .marathon_public import words as public_words
from .marathon_public_reminders import reminder_channel
from .marathon_public_reminders import wanted as public_reminders_wanted

log = logging.getLogger(__name__)

TEMPLATES = {
    mhh.UPCOMING: MARATHON_HOST_HIGHLIGHT_TEMPLATE_KEY,
    mhh.LIVE: MARATHON_HOST_HIGHLIGHT_LIVE_TEMPLATE_KEY,
    mhh.DONE: MARATHON_HOST_HIGHLIGHT_DONE_TEMPLATE_KEY,
}
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


async def watch_url(bot: Any, marathon: Any) -> str:
    login = await channel_login(bot, marathon)
    if login:
        return mt.TWITCH_URL.format(login=login)
    return schedule_page(marathon["source"], marathon["source_ref"]) or marathon["schedule_url"]


async def text_of(bot: Any, guild: Any, marathon: Any, span: mhh.Span, key: str) -> str:
    fields = mhh.fields_of(span, marathon, url=await watch_url(bot, marathon))
    said = mt.render(bot.store.get(guild.id, key), said_default(key), **fields).text
    return said.strip()[: mt.MESSAGE_LIMIT]


async def highlight_text(bot: Any, guild: Any, marathon: Any, span: mhh.Span) -> str:
    return await text_of(bot, guild, marathon, span, TEMPLATES[mhh.state_of(span)])


async def removed_text(bot: Any, guild: Any, marathon: Any, span: mhh.Span) -> str:
    fields = mhh.fields_of(span, marathon, url=await watch_url(bot, marathon))
    return mt.render(
        bot.store.get(guild.id, MARATHON_PUBLIC_REMOVED_KEY),
        said_default(MARATHON_PUBLIC_REMOVED_KEY),
        runner=span.name,
        mention=fields["mention"],
        game=fields["games"],
        category="",
        part=bot.store.get(guild.id, MARATHON_PART_HOST_KEY) or mt.HOST,
        when=fields["when"],
        relative=fields["relative"],
        url=fields["url"],
        marathon=fields["show"],
        state="",
    ).text


def details_of(marathon: Any, span: mhh.Span, **extra: Any) -> dict[str, Any]:
    return {
        "marathon_id": marathon["id"],
        "member_id": span.user_id,
        "host": span.name,
        "runs": span.run_ids,
    } | extra


async def save(bot: Any, marathon: Any, found: list[dict[str, Any]]) -> None:
    await update_marathon(bot.db, marathon["id"], **{mhh.COLUMN: mhh.dump(found)})


async def spans_of(bot: Any, guild: Any, marathon: Any) -> list[mhh.Span]:
    if not scans(bot, guild.id, marathon):
        return []
    return mhh.spans(await runs_of(bot.db, marathon["id"]))


def attached(found: list[dict[str, Any]], span: mhh.Span) -> tuple[dict[str, Any], bool]:
    record = mhh.record_for(found, span)
    if record is None:
        record = mhh.new_record(span)
        found.append(record)
        return (record, True)
    fresh = {"runs": span.run_ids, "name": span.name, "login": span.login}
    if any(record.get(key) != value for key, value in fresh.items()):
        record.update(fresh)
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
    span: mhh.Span,
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
    span: mhh.Span,
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
    text = await highlight_text(bot, guild, marathon, span)
    base = details_of(marathon, span, auto=auto, via=via)
    if record["message_id"] and record["removed"]:
        back = await put_back(
            cog, guild, marathon, span, record, found, text, base, actor=actor, via=via
        )
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
        | {"message_id": str(sent.id), "channel_id": channel_id, "state": mhh.state_of(span)}
        | rehearsal_of(bot, guild),
    )
    return (None, int(channel_id))


async def follow_one(
    cog: Any, guild: Any, marathon: Any, span: mhh.Span, record: dict[str, Any]
) -> bool:
    """An unchanged block costs no Discord call; a message deleted by hand is forgotten (True:
    the record changed)."""
    bot = cog.bot
    text = await highlight_text(bot, guild, marathon, span)
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
            details=details_of(marathon, span, message_id=str(key)),
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
            details=details_of(marathon, span, step="edit", reason=why),
        )
        return False
    cache[key] = (record["channel_id"], text)
    await log_action(
        bot,
        guild,
        "marathon.would_edit_host_highlight"
        if rehearsing(bot, guild)
        else "marathon.host_highlight_edited",
        details=details_of(marathon, span, message_id=str(key), state=mhh.state_of(span))
        | rehearsal_of(bot, guild),
    )
    return False


async def sync_host_highlights(cog: Any, guild: Any, marathon: Any) -> None:
    """Under the marathon lock: each block gets its post once, and every post that is up follows
    its block. The key off stops new posts; a post already up keeps following."""
    bot = cog.bot
    fresh = await get_marathon(bot.db, guild.id, marathon["id"]) if marathon else None
    if fresh is None or not mi.is_tracked(fresh) or mode_of(bot, guild.id) == MODE_OFF:
        return
    try:
        found = mhh.records(fresh)
        posting = wanted(bot, guild, fresh) and public_channel(bot, guild.id) is not None
        changed = False
        seen: list[int] = []
        for span in await spans_of(bot, guild, fresh):
            fresh_block = posting and mhh.state_of(span) != mhh.DONE
            if mhh.record_for(found, span) is None and not fresh_block:
                continue
            record, moved = attached(found, span)
            seen.append(id(record))
            changed = changed or moved
            if not record["tried"] and fresh_block:
                await post_one(cog, guild, fresh, span, record, found)
                continue
            if mhh.is_up(record) and await follow_one(cog, guild, fresh, span, record):
                changed = True
        runs = await runs_of(bot.db, fresh["id"])
        for record in found:
            if id(record) in seen or not mhh.is_up(record):
                continue
            span = mhh.left_behind(record, runs)
            if span is not None and await follow_one(cog, guild, fresh, span, record):
                changed = True
        if changed:
            await save(bot, fresh, found)
    except Exception as exc:
        log.warning("marathon: the host highlights failed — %s", reason_of(exc))


async def remind_hosts(cog: Any, guild: Any, marathon: Any, now: datetime) -> None:
    """One public heads-up per block, marathon_ping_minutes before its first run; the marker is
    stored before the send, so a restart never posts it twice."""
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
        for span in await spans_of(bot, guild, fresh):
            due = mhh.heads_up_due(
                span, mhh.record_for(found, span), now, minutes=minutes, stale_minutes=stale
            )
            if due is None:
                continue
            record, _moved = attached(found, span)
            record["reminded"] = True
            await save(bot, fresh, found)
            base = details_of(fresh, span, mark=minutes)
            if due == mhh.SKIP:
                await log_action(
                    bot,
                    guild,
                    "marathon.host_reminder_skipped",
                    details=base | {"because": "late"},
                )
                continue
            await heads_up(bot, guild, fresh, span, base)
    except Exception as exc:
        log.warning("marathon: a host heads-up failed — %s", reason_of(exc))


async def heads_up(
    bot: Any, guild: Any, marathon: Any, span: mhh.Span, base: dict[str, Any]
) -> None:
    home = reminder_channel(bot, guild.id)
    if home is None:
        await log_action(
            bot, guild, "marathon.host_reminder_failed", details=base | {"reason": "no_channel"}
        )
        return
    text = await text_of(bot, guild, marathon, span, MARATHON_HOST_REMINDER_TEMPLATE_KEY)
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
    span: mhh.Span,
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
        why = await edit_public(bot, guild, message, await removed_text(bot, guild, marathon, span))
        edited = why is None
        if why is not None:
            await log_action(
                bot,
                guild,
                kind_via("marathon.host_highlight_failed", via),
                actor=actor,
                details=details_of(marathon, span, step="remove", reason=why, via=via),
            )
    await log_action(
        bot,
        guild,
        kind_via("marathon.host_highlight_removed", via),
        actor=actor,
        details=details_of(
            marathon, span, message_id=str(record["message_id"]), edited=edited, via=via
        ),
    )


async def post_move(
    cog: Any,
    guild: Any,
    marathon: Any,
    span: mhh.Span,
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
                runner=span.name,
                channel=f"<#{record['channel_id']}>",
            ),
        )
    if public_channel(bot, guild.id) is None:
        return refusal(
            public_words(bot, guild.id, MARATHON_PUBLIC_NO_CHANNEL_KEY), NO_PUBLIC_CODE, 409
        )
    why, channel_id = await post_one(
        cog, guild, marathon, span, record, found, actor=actor, via=via, auto=False
    )
    if why is not None:
        return refusal(
            public_words(bot, guild.id, MARATHON_PUBLIC_FAILED_KEY, runner=span.name, reason=why),
            FAILED_CODE,
            409,
        )
    return Outcome(
        True,
        public_words(
            bot,
            guild.id,
            MARATHON_PUBLIC_POSTED_SAID_KEY,
            runner=span.name,
            channel=f"<#{channel_id}>",
        ),
    )


async def remove_move(
    cog: Any,
    guild: Any,
    marathon: Any,
    span: mhh.Span,
    record: dict[str, Any],
    found: list[dict[str, Any]],
    *,
    actor: Any,
    via: str,
) -> Outcome:
    bot = cog.bot
    if not mhh.is_up(record):
        return Outcome(
            True, public_words(bot, guild.id, MARATHON_PUBLIC_NOT_UP_KEY, runner=span.name)
        )
    await take_down(cog, guild, marathon, span, record, found, actor=actor, via=via)
    return Outcome(
        True,
        public_words(
            bot,
            guild.id,
            MARATHON_PUBLIC_REMOVED_SAID_KEY,
            runner=span.name,
            channel=f"<#{record['channel_id']}>",
        ),
    )


MOVES = {mhh.POST: post_move, mhh.REMOVE: remove_move}


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
    """Staff final say on a host's highlight: post (or put back) or take down — the block that
    holds `run_id`, or every block they host."""
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
            for one in await spans_of(bot, guild, fresh)
            if str(one.user_id) == str(user_id)
            and (run_id in (None, "") or str(run_id) in map(str, one.run_ids))
        ]
        if not mine:
            return refusal(
                mhh.NOT_HOSTING.format(name=member_name(guild, user_id), marathon=fresh["name"]),
                mhh.NOT_HOSTING_CODE,
                404,
            )
        found = mhh.records(fresh)
        said = []
        for span in mine:
            record, _moved = attached(found, span)
            outcome = await MOVES[move](
                cog, guild, fresh, span, record, found, actor=actor, via=via
            )
            await save(bot, fresh, found)
            if not outcome.ok:
                return outcome
            said.append(outcome.message)
    return Outcome(True, "\n".join(dict.fromkeys(said)))


async def state_for(bot: Any, guild: Any, marathon: Any) -> dict[int, dict[str, Any]]:
    """Per BaF host: each block's highlight — up, or could be posted — and the whole of it."""
    found = mhh.records(marathon)
    posting = public_channel(bot, guild.id) is not None and mode_of(bot, guild.id) != MODE_OFF
    shown: dict[int, dict[str, Any]] = {}
    for span in await spans_of(bot, guild, marathon):
        record = mhh.record_for(found, span)
        up = mhh.is_up(record)
        block = {
            "runs": [str(one) for one in span.run_ids],
            "up": up,
            "channel_id": str(record["channel_id"]) if up else None,
            "can_post": posting and not up,
        }
        mine = shown.setdefault(
            span.user_id, {"up": False, "channel_id": None, "can_post": False, "blocks": []}
        )
        mine["blocks"].append(block)
        mine["up"] = mine["up"] or up
        mine["can_post"] = mine["can_post"] or block["can_post"]
        mine["channel_id"] = mine["channel_id"] or block["channel_id"]
    return shown


def block_state(shown: dict[int, dict[str, Any]], user_id: Any, run_id: Any = None) -> Any:
    """The block holding `run_id`, or the host's whole answer; None for someone who hosts none."""
    found = shown.get(int(user_id)) if user_id else None
    if found is None or run_id is None:
        return found
    return next((one for one in found["blocks"] if str(run_id) in one["runs"]), None)


__all__ = [
    "block_state",
    "press",
    "remind_hosts",
    "state_for",
    "switched_on",
    "sync_host_highlights",
    "wanted",
]
