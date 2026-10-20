"""Weekly questions: Post to test, a copy of this week's question in the rehearsal home."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import discord

from . import questions as rules
from . import questions_moves as moves
from . import rehearsal_copy
from . import shadow as shadow_home
from .actionlog import log_action
from .logkinds import VIA_DISCORD, kind_via
from .panels import Outcome, refusal

LABEL = "Post to test"
TESTED = "A test copy of this week's question is in <#{where}>. Nothing in the queue changed."
TEST_OFF = (
    "Posts are off, so no test copy was sent. Turn posts_mode on on the Posts page first."
)
NOTHING_TO_TEST = (
    "There is no question to send a test copy of: the queue is empty. Add a question first."
)
NO_HOME_LINE = (
    "**Post to test** — no test channel is set. Pick the test channel (shadow_channel_id) "
    "in Settings."
)


def home_of(bot: Any, guild: Any) -> int | None:
    return shadow_home.channel_id(bot, guild)


def this_weeks_question(found: dict[str, Any]) -> Any:
    """The question This week shows: the one posted for it, else the top of the queue."""
    posted = found.get("posted")
    if found.get("status") == rules.POSTED and posted is not None:
        return posted
    return found.get("question")


def can_test(bot: Any, guild: Any, found: dict[str, Any]) -> bool:
    return (
        found["mode"] != rules.OFF
        and this_weeks_question(found) is not None
        and home_of(bot, guild) is not None
    )


async def rehearse(
    bot: Any, guild: Any, actor: Any, *, via: str = VIA_DISCORD, now: datetime | None = None
) -> Outcome:
    """Sends one copy and touches nothing else: no slot, no queue order, no posted_by."""
    found = await moves.week(bot, guild, now)
    if found["mode"] == rules.OFF:
        return refusal(TEST_OFF, "questions_off", 409)
    question = this_weeks_question(found)
    if question is None:
        return refusal(NOTHING_TO_TEST, "queue_empty", 409)
    target = home_of(bot, guild)
    if target is None:
        return refusal(rules.NO_REHEARSAL, "no_shadow_channel", 409)
    channel, failure = rehearsal_copy.reach(bot, guild, target)
    if failure == rehearsal_copy.TEST_MODE:
        return refusal(rules.TEST_MODE_REFUSED.format(channel=target), "test_mode", 409)
    if channel is None:
        return refusal(rules.CHANNEL_GONE.format(channel=target), "channel_gone", 409)
    payload = {
        "content": rules.rendered(bot.store, guild.id, question["body"]),
        "allowed_mentions": discord.AllowedMentions.none(),
    }
    try:
        message, _ = await rehearsal_copy.deliver(channel, payload)
    except discord.HTTPException as exc:
        why = f"{exc.status} {exc.text}".strip()
        return refusal(rules.POST_REFUSED.format(why=why), "not_posted", 409)
    await log_action(
        bot,
        guild,
        kind_via("question.rehearsed", via),
        actor=actor,
        details={
            "via": via,
            "question_id": int(question["id"]),
            "question": question["body"],
            "shadow_home": int(channel.id),
            "message_id": int(message.id),
            "url": rehearsal_copy.message_url(guild, channel, message),
        },
    )
    return Outcome(True, TESTED.format(where=int(channel.id)), value=int(question["id"]))


__all__ = [
    "LABEL",
    "NO_HOME_LINE",
    "NOTHING_TO_TEST",
    "TESTED",
    "TEST_OFF",
    "home_of",
    "rehearse",
    "this_weeks_question",
    "can_test",
]
