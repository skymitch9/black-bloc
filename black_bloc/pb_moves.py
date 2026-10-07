"""The moves a member and staff make on the personal best feed; both doors call these."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import discord

from . import pb_match, pb_store
from .actionlog import entity_id, log_action
from .logkinds import VIA_DISCORD, kind_via
from .panels import Outcome, refusal
from .pb_feed import (
    CHANNEL_GONE,
    JUST_LOOKED,
    LOOK_NOW_COOLDOWN_MINUTES,
    NO_CHANNEL,
    NO_SHADOW_HOME,
    OFF,
    ON,
    TEST_MODE_REFUSED,
    minutes_until,
    mode_of,
    said,
)
from .pb_looks import feed_of, safely
from .speedrun import SpeedrunError

log = logging.getLogger(__name__)

NAME_LIMIT = 64
REASON_LIMIT = 300
DM_LIMIT = 1900
DM_REFUSED = (
    "Discord would not deliver the DM: their DMs are closed, or they are no longer somewhere "
    "Black Bloc can reach them. The move itself was made; tell them yourself if it matters."
)
NOT_ON = (
    "pb_feed_mode is {mode}, so nothing is sent to a member. This is the DM they would have got."
)


def mention(guild: Any, user_id: int) -> str:
    member = guild.get_member(int(user_id))
    return getattr(member, "mention", None) or f"<@{int(user_id)}>"


def given_reason(reason: Any) -> str:
    return " ".join(str(reason or "").split())[:REASON_LIMIT]


async def note(
    bot: Any, guild: Any, kind: str, actor: Any, user_id: int, via: str, **details: Any
) -> None:
    await safely(
        log_action(
            bot,
            guild,
            kind_via(kind, via),
            actor=actor,
            target=int(user_id),
            details={"via": via, **details},
        ),
        "the log row",
    )


async def dm(user: Any, text: str) -> bool:
    """Whether the member actually got told."""
    send = getattr(user, "send", None)
    if send is None:
        return False
    try:
        await send(text[:DM_LIMIT], allowed_mentions=discord.AllowedMentions.none())
    except Exception as exc:
        log.info("pb feed: could not DM %s: %s", getattr(user, "id", "?"), exc)
        return False
    return True


async def tell(
    bot: Any, guild: Any, user_id: int, move: str, key: str, reason: str, **fields: Any
) -> None:
    """The DM a member is owed when staff change their part; never in the way of the move."""
    store = bot.store
    text = said(
        store,
        guild.id,
        key,
        server=discord.utils.escape_markdown(str(getattr(guild, "name", "") or "")),
        reason=discord.utils.escape_markdown(reason)
        or said(store, guild.id, "pb_feed_dm_no_reason"),
        **fields,
    )
    details = {"move": move, "text": text}
    mode = mode_of(store, guild.id)
    if mode != ON:
        await safely(
            log_action(
                bot,
                guild,
                "pbfeed.would_dm",
                target=int(user_id),
                details=details | {"reason": NOT_ON.format(mode=mode)},
            ),
            "the log row",
        )
        return
    finder = getattr(bot, "get_user", None)
    member = guild.get_member(int(user_id)) or (finder(int(user_id)) if finder else None)
    if await dm(member, text):
        return
    await safely(
        log_action(
            bot,
            guild,
            "pbfeed.dm_failed",
            target=int(user_id),
            details=details | {"reason": DM_REFUSED},
        ),
        "the log row",
    )


async def login_of(bot: Any, user_id: int) -> str | None:
    return (await pb_store.links(bot.db)).get(int(user_id))


async def opt_out(bot: Any, guild: Any, member: Any, *, via: str = VIA_DISCORD) -> Outcome:
    """A member's own move. Their runner is kept, so opting back in needs no lookup."""
    user_id = int(member.id)
    async with feed_of(bot).lock:
        row = await pb_store.match(bot.db, guild.id, user_id)
        if row is not None and row["state"] == pb_store.BLOCKED:
            return refusal(said(bot.store, guild.id, "pb_feed_you_blocked"), "blocked", 409)
        row = await pb_store.write_state(
            bot.db,
            guild.id,
            user_id,
            pb_store.OPTED_OUT,
            state_by=pb_store.MEMBER,
            set_by=user_id,
            twitch_login=await login_of(bot, user_id),
            keep_runner=True,
        )
    await note(bot, guild, "pbfeed.opted_out", member, user_id, via)
    return Outcome(True, said(bot.store, guild.id, "pb_feed_opted_out_said"), value=row)


async def opt_in(bot: Any, guild: Any, member: Any, *, via: str = VIA_DISCORD) -> Outcome:
    user_id = int(member.id)
    async with feed_of(bot).lock:
        row = await pb_store.match(bot.db, guild.id, user_id)
        if row is not None and row["state"] == pb_store.BLOCKED:
            return refusal(said(bot.store, guild.id, "pb_feed_you_blocked"), "blocked", 409)
        if row is None or row["state"] != pb_store.OPTED_OUT:
            return Outcome(True, said(bot.store, guild.id, "pb_feed_opted_in_said"), value=row)
        row = await back_in(bot, guild, user_id, pb_store.MEMBER, user_id, ends_opt_out=True)
    await note(bot, guild, "pbfeed.opted_in", member, user_id, via)
    return Outcome(True, said(bot.store, guild.id, "pb_feed_opted_in_said"), value=row)


async def back_in(
    bot: Any, guild: Any, user_id: int, state_by: str, set_by: Any, *, ends_opt_out: bool
) -> Any:
    """Out of an opt-out or a block, with the baseline taken again so nothing old is posted."""
    await pb_store.restore(
        bot.db, guild.id, user_id, state_by=state_by, set_by=set_by, ends_opt_out=ends_opt_out
    )
    await pb_store.forget_runs(bot.db, guild.id, user_id)
    await bot.db.conn.execute(
        "UPDATE pb_matches SET baseline_at = NULL, looked_at = NULL WHERE guild_id = ? "
        "AND user_id = ?",
        (guild.id, user_id),
    )
    await bot.db.conn.commit()
    return await pb_store.match(bot.db, guild.id, user_id)


async def set_by_hand(
    bot: Any,
    guild: Any,
    user_id: int,
    name: Any,
    actor: Any,
    *,
    reason: Any = None,
    via: str = VIA_DISCORD,
    now: datetime | None = None,
) -> Outcome:
    """Staff name the speedrun.com account; it must be exactly one account's name."""
    store = bot.store
    given = str(name or "").strip().lstrip("@")[:NAME_LIMIT]
    why = given_reason(reason)
    who = mention(guild, user_id)
    if mode_of(store, guild.id) == OFF:
        return refusal(said(store, guild.id, "pb_feed_off_said"), "pb_feed_off", 409)
    if not given:
        return refusal(
            said(store, guild.id, "pb_feed_no_runner_said", given=""), "bad_request", 400
        )
    feed = feed_of(bot)
    async with feed.lock:
        row = await pb_store.match(bot.db, guild.id, user_id)
        if row is not None and (row["state"] == pb_store.OPTED_OUT or row["opted_out_at"]):
            return refusal(
                said(store, guild.id, "pb_feed_not_now_said", member=who), "opted_out", 409
            )
        now = now or datetime.now(UTC)
        held = await feed.hold(guild.id, now)
        if held:
            return refusal(
                said(store, guild.id, "pb_feed_failed_said", reason=held), "not_yet", 429
            )
        before = int(feed.client.requests)
        try:
            answer = await pb_match.by_name(feed.client, given)
        except SpeedrunError as exc:
            log.warning("pb feed: could not look a runner up — %s", exc)
            return refusal(
                said(store, guild.id, "pb_feed_failed_said", reason=str(exc)), "could_not_look", 502
            )
        finally:
            feed.count(before, now)
        if answer.outcome != pb_match.FOUND:
            return refusal(
                said(store, guild.id, "pb_feed_no_runner_said", given=given), "no_such_runner", 404
            )
        runner = answer.runner
        try:
            row = await pb_store.write_match(
                bot.db,
                guild.id,
                user_id,
                runner,
                source=pb_store.STAFF,
                twitch_login=await login_of(bot, user_id),
                set_by=entity_id(actor),
            )
        except pb_store.RunnerTaken as exc:
            return refusal(
                said(
                    store,
                    guild.id,
                    "pb_feed_taken_said",
                    runner=runner.name,
                    holder=mention(guild, exc.holder_id),
                ),
                "runner_taken",
                409,
            )
    await note(
        bot,
        guild,
        "pbfeed.set_by_hand",
        actor,
        user_id,
        via,
        runner=runner.name,
        runner_id=runner.id,
        reason=why,
    )
    await tell(
        bot,
        guild,
        user_id,
        "set_by_hand",
        "pb_feed_dm_set",
        why,
        runner=discord.utils.escape_markdown(runner.name),
    )
    return Outcome(
        True, said(store, guild.id, "pb_feed_set_said", member=who, runner=runner.name), value=row
    )


async def _to_state(
    bot: Any,
    guild: Any,
    user_id: int,
    actor: Any,
    via: str,
    *,
    state: str,
    kind: str,
    words: str,
    allowed: tuple[str | None, ...],
    reason: Any,
    dm_key: str,
) -> Outcome:
    store = bot.store
    who = mention(guild, user_id)
    why = given_reason(reason)
    async with feed_of(bot).lock:
        row = await pb_store.match(bot.db, guild.id, user_id)
        found = row["state"] if row is not None else None
        if found == pb_store.OPTED_OUT and pb_store.OPTED_OUT not in allowed:
            return refusal(
                said(store, guild.id, "pb_feed_not_now_said", member=who), "opted_out", 409
            )
        if found not in allowed:
            return refusal(
                said(store, guild.id, "pb_feed_nothing_to_do_said", member=who),
                "nothing_to_do",
                409,
            )
        before = row["src_name"] if row is not None else None
        row = await pb_store.write_state(
            bot.db,
            guild.id,
            user_id,
            state,
            state_by=pb_store.STAFF,
            set_by=entity_id(actor),
            twitch_login=await login_of(bot, user_id),
        )
    move = kind.rsplit(".", 1)[-1]
    await note(bot, guild, kind, actor, user_id, via, runner=before, reason=why)
    await tell(
        bot,
        guild,
        user_id,
        move,
        dm_key,
        why,
        runner=discord.utils.escape_markdown(str(before or "")),
    )
    return Outcome(True, said(store, guild.id, words, member=who), value=row)


async def unmatch(
    bot: Any, guild: Any, user_id: int, actor: Any, *, reason: Any = None, via: str = VIA_DISCORD
) -> Outcome:
    return await _to_state(
        bot,
        guild,
        user_id,
        actor,
        via,
        state=pb_store.NONE,
        kind="pbfeed.unmatched",
        words="pb_feed_unmatched_said",
        allowed=(pb_store.MATCHED,),
        reason=reason,
        dm_key="pb_feed_dm_unmatched",
    )


async def block(
    bot: Any, guild: Any, user_id: int, actor: Any, *, reason: Any = None, via: str = VIA_DISCORD
) -> Outcome:
    """An opt-out is remembered under a block, and is what an unblock goes back to."""
    return await _to_state(
        bot,
        guild,
        user_id,
        actor,
        via,
        state=pb_store.BLOCKED,
        kind="pbfeed.blocked",
        words="pb_feed_blocked_said",
        allowed=(None, pb_store.MATCHED, pb_store.NONE, pb_store.OPTED_OUT),
        reason=reason,
        dm_key="pb_feed_dm_blocked",
    )


async def unblock(
    bot: Any, guild: Any, user_id: int, actor: Any, *, reason: Any = None, via: str = VIA_DISCORD
) -> Outcome:
    """Back to where the member stood: opted out if they had opted out, else in the feed."""
    store = bot.store
    who = mention(guild, user_id)
    async with feed_of(bot).lock:
        row = await pb_store.match(bot.db, guild.id, user_id)
        if row is None or row["state"] != pb_store.BLOCKED:
            return refusal(
                said(store, guild.id, "pb_feed_nothing_to_do_said", member=who),
                "nothing_to_do",
                409,
            )
        row = await back_in(
            bot, guild, user_id, pb_store.STAFF, entity_id(actor), ends_opt_out=False
        )
    out = row is not None and row["state"] == pb_store.OPTED_OUT
    await note(
        bot,
        guild,
        "pbfeed.unblocked",
        actor,
        user_id,
        via,
        reason=given_reason(reason),
        still_opted_out=out,
    )
    words = "pb_feed_unblocked_opted_out_said" if out else "pb_feed_unblocked_said"
    return Outcome(True, said(store, guild.id, words, member=who), value=row)


async def clear_opt_out(
    bot: Any, guild: Any, user_id: int, actor: Any, *, reason: Any = None, via: str = VIA_DISCORD
) -> Outcome:
    """Staff have the final say over a member's opt-out; the row says who, the member is told."""
    store = bot.store
    who = mention(guild, user_id)
    why = given_reason(reason)
    async with feed_of(bot).lock:
        row = await pb_store.match(bot.db, guild.id, user_id)
        if row is None or row["state"] != pb_store.OPTED_OUT:
            return refusal(
                said(store, guild.id, "pb_feed_nothing_to_do_said", member=who),
                "nothing_to_do",
                409,
            )
        row = await back_in(
            bot, guild, user_id, pb_store.STAFF, entity_id(actor), ends_opt_out=True
        )
    await note(bot, guild, "pbfeed.opt_out_cleared", actor, user_id, via, reason=why)
    await tell(bot, guild, user_id, "opt_out_cleared", "pb_feed_dm_opt_out_cleared", why)
    return Outcome(True, said(store, guild.id, "pb_feed_unblocked_said", member=who), value=row)


async def look_now(
    bot: Any,
    guild: Any,
    user_id: int,
    actor: Any,
    *,
    via: str = VIA_DISCORD,
    now: datetime | None = None,
) -> Outcome:
    """One member, now: outside the spread; inside the backoff, the cap and its own cooldown."""
    store = bot.store
    who = mention(guild, user_id)
    if mode_of(store, guild.id) == OFF:
        return refusal(said(store, guild.id, "pb_feed_off_said"), "pb_feed_off", 409)
    row = await pb_store.match(bot.db, guild.id, user_id)
    if row is None or row["state"] != pb_store.MATCHED:
        return refusal(
            said(store, guild.id, "pb_feed_nothing_to_do_said", member=who), "nothing_to_do", 409
        )
    feed = feed_of(bot)
    now = now or datetime.now(UTC)
    held = await feed.hold(guild.id, now) or just_looked(row, now)
    if held:
        return refusal(said(store, guild.id, "pb_feed_failed_said", reason=held), "not_yet", 429)
    try:
        looked = await feed.look(guild, user_id, now=now)
    except SpeedrunError as exc:
        log.warning("pb feed: Look now failed — %s", exc)
        await feed.outage(guild, exc, now)
        return refusal(
            said(store, guild.id, "pb_feed_failed_said", reason=str(exc)), "could_not_look", 502
        )
    if looked.trouble or looked.gone:
        gone = said(store, guild.id, "pb_feed_unmatched_said", member=who)
        return refusal(
            said(store, guild.id, "pb_feed_failed_said", reason=looked.trouble or gone),
            "could_not_look",
            502,
        )
    await note(
        bot, guild, "pbfeed.looked", actor, user_id, via, found=looked.found, seen=looked.seen
    )
    return Outcome(
        True,
        said(
            store,
            guild.id,
            "pb_feed_looked_said",
            runner=row["src_name"],
            found=looked.found,
            seen=looked.seen,
        ),
        value=await pb_store.match(bot.db, guild.id, user_id),
    )


OUT_OF_FEED = {
    None: "not matched",
    pb_store.NONE: "not matched",
    pb_store.OPTED_OUT: "opted out",
    pb_store.BLOCKED: "blocked",
}
NOWHERE = (NO_CHANNEL, CHANNEL_GONE, NO_SHADOW_HOME, TEST_MODE_REFUSED)


async def post_again(
    bot: Any,
    guild: Any,
    post_id: int,
    actor: Any,
    *,
    via: str = VIA_DISCORD,
    now: datetime | None = None,
) -> Outcome:
    """A stored post sent again where the mode sends one now, as a new row; staff's test."""
    store = bot.store
    feed = feed_of(bot)
    async with feed.lock:
        source = await pb_store.post(bot.db, guild.id, post_id)
        if source is None:
            return refusal(
                said(store, guild.id, "pb_feed_no_post_said", post=post_id), "no_such_post", 404
            )
        if mode_of(store, guild.id) == OFF:
            return refusal(said(store, guild.id, "pb_feed_again_off_said"), "pb_feed_off", 409)
        sent = await feed.repost(guild, source, actor=actor, via=via, now=now)
        row = await pb_store.post(bot.db, guild.id, sent.post_id)
    user_id = int(source["user_id"])
    who = mention(guild, user_id)
    match = await pb_store.match(bot.db, guild.id, user_id)
    state = match["state"] if match is not None else None
    aside = (
        ""
        if state == pb_store.MATCHED
        else " "
        + said(
            store,
            guild.id,
            "pb_feed_again_not_in_feed_said",
            member=who,
            state=OUT_OF_FEED.get(state, str(state)),
        )
    )
    if sent.outcome not in (pb_store.POSTED, pb_store.REHEARSED):
        status = 409 if sent.reason in NOWHERE else 502
        words = said(store, guild.id, "pb_feed_again_failed_said", reason=sent.reason or "")
        return refusal(words + aside, "not_posted", status)
    key = (
        "pb_feed_rehearsed_again_said"
        if sent.outcome == pb_store.REHEARSED
        else "pb_feed_posted_again_said"
    )
    words = said(
        store,
        guild.id,
        key,
        member=who,
        game=discord.utils.escape_markdown(str(source["game"] or "")),
        channel=f"<#{sent.channel_id}>",
    )
    return Outcome(True, words + aside, value=row)


def just_looked(row: Any, now: datetime) -> str | None:
    """Why this member cannot be looked at by hand again yet, in words, or None."""
    looked = pb_store.parsed(row["looked_at"])
    again = looked + timedelta(minutes=LOOK_NOW_COOLDOWN_MINUTES) if looked else None
    if again is None or now >= again or now < looked:
        return None
    ago = max(0, int((now - looked).total_seconds() // 60))
    return JUST_LOOKED.format(ago=ago, minutes=minutes_until(again, now))


__all__ = [
    "NAME_LIMIT",
    "REASON_LIMIT",
    "block",
    "clear_opt_out",
    "look_now",
    "opt_in",
    "opt_out",
    "post_again",
    "set_by_hand",
    "unblock",
    "unmatch",
]
