"""Polls: Post to test, a copy of a poll that is not posted yet, in the rehearsal home."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import discord

from . import rehearsal_copy
from . import shadow as shadow_home
from .actionlog import log_action
from .logkinds import VIA_DISCORD, kind_via
from .panels import Outcome, refusal
from .polls import (
    MODE_KEY,
    OFF,
    PANEL,
    clamp,
    closes_at,
    open_text,
    panel_embed,
)

LABEL = "Post to test"
TESTED = "A test copy of the poll is in <#{where}>. Nothing was posted or saved."
TEST_OFF = "Polls are off, so no test copy was sent. Turn poll_mode on in Settings first."
NO_HOME = (
    "There is nowhere to send a test copy: no rehearsal home is set. Pick shadow_channel_id in "
    "Settings first."
)
HOME_GONE = "Black Bloc cannot see the rehearsal home <#{home}>, so nothing was sent."
TEST_MODE = "Test mode keeps Black Bloc out of channel {channel}, so no test copy was sent."
REFUSED = "Discord would not take the test copy ({why}), so nothing was sent. Try again."
QUESTION_LIMIT = 300
TEST_POLL_ID = "test"


def home_of(bot: Any, guild: Any) -> int | None:
    return shadow_home.channel_id(bot, guild)


def is_off(store: Any, guild_id: int) -> bool:
    return str(store.get(guild_id, MODE_KEY) or "").strip().lower() == OFF


def payload_of(plan: dict[str, Any], creator_id: Any) -> dict[str, Any]:
    """What members would see, minus anything a vote could reach: no buttons, no pings."""
    said: dict[str, Any] = {
        "content": open_text(creator_id),
        "allowed_mentions": discord.AllowedMentions.none(),
    }
    if plan["surface"] == PANEL:
        counts = [
            {"position": at, "label": label, "votes": 0}
            for at, label in enumerate(plan["labels"], start=1)
        ]
        said["embed"] = panel_embed(
            poll_id=TEST_POLL_ID,
            question=plan["question"],
            counts=counts,
            voters=0,
            kind=plan["kind"],
            multi=bool(plan["multi"]),
            anonymous=bool(plan["anonymous"]),
            hidden=plan["results"] != "live",
            closes_at=closes_at(int(plan["hours"])),
        )
        return said
    made = discord.Poll(
        question=clamp(plan["question"], QUESTION_LIMIT),
        duration=timedelta(hours=int(plan["hours"])),
        multiple=bool(plan["multi"]),
    )
    for label in plan["labels"]:
        made.add_answer(text=label)
    said["poll"] = made
    return said


async def rehearse(
    bot: Any, guild: Any, actor: Any, plan: dict[str, Any], *, via: str = VIA_DISCORD
) -> Outcome:
    """Sends one copy and writes no poll row, no vote and no draft."""
    if is_off(bot.store, guild.id):
        return refusal(TEST_OFF, "polls_off", 409)
    target = home_of(bot, guild)
    if target is None:
        return refusal(NO_HOME, "no_shadow_channel", 409)
    channel, failure = rehearsal_copy.reach(bot, guild, target)
    if failure == rehearsal_copy.TEST_MODE:
        return refusal(TEST_MODE.format(channel=target), "test_mode", 409)
    if channel is None:
        return refusal(HOME_GONE.format(home=target), "channel_gone", 409)
    try:
        message, _ = await rehearsal_copy.deliver(
            channel, payload_of(plan, getattr(actor, "id", actor))
        )
    except discord.HTTPException as exc:
        why = f"{exc.status} {exc.text}".strip()
        return refusal(REFUSED.format(why=why), "post_failed", 409)
    await log_action(
        bot,
        guild,
        kind_via("poll.rehearsed", via),
        actor=actor,
        details={
            "via": via,
            "question": plan["question"],
            "surface": plan["surface"],
            "shadow_home": int(channel.id),
            "message_id": int(message.id),
            "url": rehearsal_copy.message_url(guild, channel, message),
        },
    )
    return Outcome(True, TESTED.format(where=int(channel.id)), "rehearsed", 200)


__all__ = [
    "HOME_GONE",
    "LABEL",
    "NO_HOME",
    "REFUSED",
    "TESTED",
    "TEST_MODE",
    "TEST_OFF",
    "home_of",
    "is_off",
    "payload_of",
    "rehearse",
]
