"""The moves a member and staff make on the personal best feed; both doors call these."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from . import pb_match, pb_store
from .actionlog import entity_id, log_action
from .logkinds import VIA_DISCORD, kind_via
from .panels import Outcome, refusal
from .pb_feed import OFF, mode_of, said
from .pb_looks import feed_of, safely
from .speedrun import SpeedrunError

log = logging.getLogger(__name__)

NAME_LIMIT = 64


def mention(guild: Any, user_id: int) -> str:
    member = guild.get_member(int(user_id))
    return getattr(member, "mention", None) or f"<@{int(user_id)}>"


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
        row = await back_in(bot, guild, user_id, pb_store.MEMBER, user_id)
    await note(bot, guild, "pbfeed.opted_in", member, user_id, via)
    return Outcome(True, said(bot.store, guild.id, "pb_feed_opted_in_said"), value=row)


async def back_in(bot: Any, guild: Any, user_id: int, state_by: str, set_by: Any) -> Any:
    """Out of an opt-out or a block, with the baseline taken again so nothing old is posted."""
    await pb_store.restore(bot.db, guild.id, user_id, state_by=state_by, set_by=set_by)
    await pb_store.forget_runs(bot.db, guild.id, user_id)
    await bot.db.conn.execute(
        "UPDATE pb_matches SET baseline_at = NULL, looked_at = NULL WHERE guild_id = ? "
        "AND user_id = ?",
        (guild.id, user_id),
    )
    await bot.db.conn.commit()
    return await pb_store.match(bot.db, guild.id, user_id)


async def set_by_hand(
    bot: Any, guild: Any, user_id: int, name: Any, actor: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    """Staff name the speedrun.com account; it must be exactly one account's name."""
    store = bot.store
    given = str(name or "").strip().lstrip("@")[:NAME_LIMIT]
    who = mention(guild, user_id)
    if not given:
        return refusal(
            said(store, guild.id, "pb_feed_no_runner_said", given=""), "bad_request", 400
        )
    feed = feed_of(bot)
    async with feed.lock:
        row = await pb_store.match(bot.db, guild.id, user_id)
        if row is not None and row["state"] == pb_store.OPTED_OUT:
            return refusal(
                said(store, guild.id, "pb_feed_not_now_said", member=who), "opted_out", 409
            )
        before = int(feed.client.requests)
        try:
            answer = await pb_match.by_name(feed.client, given)
        except SpeedrunError as exc:
            feed.count(before, datetime.now(UTC))
            log.warning("pb feed: could not look a runner up — %s", exc)
            return refusal(
                said(store, guild.id, "pb_feed_failed_said", reason=str(exc)), "could_not_look", 502
            )
        feed.count(before, datetime.now(UTC))
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
    allowed: tuple[str, ...],
) -> Outcome:
    store = bot.store
    who = mention(guild, user_id)
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
    await note(bot, guild, kind, actor, user_id, via, runner=before)
    return Outcome(True, said(store, guild.id, words, member=who), value=row)


async def unmatch(
    bot: Any, guild: Any, user_id: int, actor: Any, *, via: str = VIA_DISCORD
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
    )


async def block(
    bot: Any, guild: Any, user_id: int, actor: Any, *, via: str = VIA_DISCORD
) -> Outcome:
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
    )


async def _staff_back_in(
    bot: Any, guild: Any, user_id: int, actor: Any, via: str, *, was: str, kind: str
) -> Outcome:
    store = bot.store
    who = mention(guild, user_id)
    async with feed_of(bot).lock:
        row = await pb_store.match(bot.db, guild.id, user_id)
        if row is None or row["state"] != was:
            return refusal(
                said(store, guild.id, "pb_feed_nothing_to_do_said", member=who),
                "nothing_to_do",
                409,
            )
        row = await back_in(bot, guild, user_id, pb_store.STAFF, entity_id(actor))
    await note(bot, guild, kind, actor, user_id, via)
    return Outcome(True, said(store, guild.id, "pb_feed_unblocked_said", member=who), value=row)


async def unblock(
    bot: Any, guild: Any, user_id: int, actor: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    return await _staff_back_in(
        bot, guild, user_id, actor, via, was=pb_store.BLOCKED, kind="pbfeed.unblocked"
    )


async def clear_opt_out(
    bot: Any, guild: Any, user_id: int, actor: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    """Staff have the final say over a member's opt-out; the row says who."""
    return await _staff_back_in(
        bot, guild, user_id, actor, via, was=pb_store.OPTED_OUT, kind="pbfeed.opt_out_cleared"
    )


async def look_now(
    bot: Any, guild: Any, user_id: int, actor: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    """One member, now: outside the spread and the backoff, inside the request count."""
    store = bot.store
    who = mention(guild, user_id)
    if mode_of(store, guild.id) == OFF:
        return refusal(said(store, guild.id, "pb_feed_off_said"), "pb_feed_off", 409)
    row = await pb_store.match(bot.db, guild.id, user_id)
    if row is None or row["state"] != pb_store.MATCHED:
        return refusal(
            said(store, guild.id, "pb_feed_nothing_to_do_said", member=who), "nothing_to_do", 409
        )
    try:
        looked = await feed_of(bot).look(guild, user_id)
    except SpeedrunError as exc:
        log.warning("pb feed: Look now failed — %s", exc)
        return refusal(
            said(store, guild.id, "pb_feed_failed_said", reason=str(exc)), "could_not_look", 502
        )
    if looked.trouble or looked.gone:
        reason = looked.trouble or said(store, guild.id, "pb_feed_unmatched_said", member=who)
        return refusal(
            said(store, guild.id, "pb_feed_failed_said", reason=reason), "could_not_look", 502
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


__all__ = [
    "block",
    "clear_opt_out",
    "look_now",
    "opt_in",
    "opt_out",
    "set_by_hand",
    "unblock",
    "unmatch",
]
