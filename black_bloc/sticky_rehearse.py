"""Sticky messages: Post to test, one plain copy of a sticky in its rehearsal home."""

from __future__ import annotations

from typing import Any

import discord

from . import posts, rehearsal_copy
from . import shadow as shadow_home
from . import sticky as rules
from .actionlog import log_action
from .logkinds import VIA_DISCORD, kind_via
from .panels import Outcome, refusal
from .sticky_posts import desk_of, is_empty, post_message

LABEL = "Post to test"
TESTED = (
    "A test copy of the sticky message in <#{channel_id}> is in <#{home}>. The sticky itself "
    "is unchanged."
)
ALREADY = "It already rehearses in <#{home}> — the copy there is live, so nothing was sent."
SWITCHED_OFF = (
    "**{key}** is off, so no test copy was sent. Turn it on in Settings, or with `/settings`, "
    "first."
)
NO_HOME = (
    "There is nowhere to send a test copy: no rehearsal home is set. Pick "
    "{feature}_shadow_channel_id or shadow_channel_id in Settings."
)
OWN_HOME = (
    "The rehearsal home is <#{channel_id}> itself, so a test copy would land in front of members "
    "and nothing was sent. Pick another {feature}_shadow_channel_id in Settings."
)
HOME_GONE = "Black Bloc cannot see the rehearsal home <#{home}>, so nothing was sent."
NOTHING = "That sticky message has nothing to show, so no test copy was sent."
REFUSED = "Discord would not take the test copy ({why}), so nothing was sent. Try again."


def mode_key(feature: str) -> str:
    return f"{feature}_mode"


def home_of(bot: Any, guild: Any, feature: str) -> int | None:
    return shadow_home.channel_id(bot, guild, feature=feature)


def can_test(bot: Any, guild: Any, row: Any, mode: str, feature: str) -> bool:
    """Rendered only when a press would send: on, not already rehearsing, a home elsewhere."""
    if mode == rules.OFF or rules.state_of(row, mode) == rules.REHEARSING:
        return False
    home = home_of(bot, guild, feature)
    return home is not None and int(home) != int(row["channel_id"])


async def payload_of(bot: Any, guild: Any, row: Any) -> dict[str, Any] | None:
    if not rules.is_post(row):
        text = str(row["text"] or "")
        return {"content": text} if text.strip() else None
    post = await posts.get_post_by_id(bot.db, int(row["post_id"]))
    if post is None:
        return None
    made, _ = await post_message(bot, guild, post)
    return None if is_empty(made) else made


async def rehearse(
    bot: Any, guild: Any, channel_id: int, actor: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    """Sends one unpinned copy; the sticky's row, state, copy and pin are never touched."""
    row = await rules.get_row(bot.db, guild.id, channel_id)
    if row is None:
        return refusal(rules.NO_STICKY, "no_sticky", 404)
    mode, feature = await desk_of(bot).rule_of(guild, row)
    if mode == rules.OFF:
        return refusal(SWITCHED_OFF.format(key=mode_key(feature)), "sticky_off", 409)
    home = home_of(bot, guild, feature)
    if rules.state_of(row, mode) == rules.REHEARSING:
        where = row["posted_channel_id"] or home
        return Outcome(True, ALREADY.format(home=where), "already_rehearsing", 200, row)
    if home is None:
        return refusal(NO_HOME.format(feature=feature), "no_shadow_channel", 409)
    if int(home) == int(channel_id):
        return refusal(OWN_HOME.format(channel_id=channel_id, feature=feature), "own_home", 409)
    channel, failure = rehearsal_copy.reach(bot, guild, home)
    if failure == rehearsal_copy.TEST_MODE:
        return refusal(posts.guard_refusal(bot), "test_mode", 409)
    if channel is None:
        return refusal(HOME_GONE.format(home=home), "channel_gone", 409)
    payload = await payload_of(bot, guild, row)
    if payload is None:
        return refusal(NOTHING, "nothing_to_post", 409)
    payload["allowed_mentions"] = discord.AllowedMentions.none()
    try:
        message, _ = await rehearsal_copy.deliver(channel, payload)
    except discord.HTTPException as exc:
        why = f"{exc.status} {exc.text}".strip()
        return refusal(REFUSED.format(why=why), "post_failed", 409)
    details: dict[str, Any] = {
        "via": via,
        "channel_id": int(channel_id),
        "shadow_home": int(channel.id),
        "message_id": int(message.id),
        "url": rehearsal_copy.message_url(guild, channel, message),
    }
    if rules.is_post(row):
        details["post_id"] = int(row["post_id"])
    await log_action(bot, guild, kind_via("sticky.rehearsed", via), actor=actor, details=details)
    said = TESTED.format(channel_id=int(channel_id), home=int(channel.id))
    return Outcome(True, said, "rehearsed", 200, row)


__all__ = [
    "ALREADY",
    "HOME_GONE",
    "LABEL",
    "NOTHING",
    "NO_HOME",
    "OWN_HOME",
    "REFUSED",
    "SWITCHED_OFF",
    "TESTED",
    "can_test",
    "home_of",
    "mode_key",
    "payload_of",
    "rehearse",
]
