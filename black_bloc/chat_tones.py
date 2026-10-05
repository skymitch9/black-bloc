"""Staff's moves on a member's own tone: reroll it, give it a start, roll one for a role."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from . import tone_keys
from .actionlog import log_action
from .chat_panel import (
    NO_SUCH_MEMBER_CODE,
    actor_id,
    member_name,
    member_of,
    usable_tone,
    words,
)
from .chat_voice import ROLLED, SET, another, col, set_tone, voice_row
from .logkinds import VIA_DISCORD, kind_via
from .panels import Outcome, refusal
from .personas import enabled_tropes, list_tropes
from .settings_store import VOICE_NO_MEMBER_KEY

log = logging.getLogger(__name__)

PINNED_CODE = "voice_is_pinned"
NO_TONES_CODE = "no_tones_on"
NO_SUCH_ROLE_CODE = "no_such_role"
LOGGED_TONES = 50


def no_member(bot: Any, guild: Any, user_id: Any) -> Outcome:
    return refusal(
        words(bot.store, guild.id, VOICE_NO_MEMBER_KEY, member=str(user_id)[:40]),
        NO_SUCH_MEMBER_CODE,
        404,
    )


async def labels_of(bot: Any) -> dict[str, str]:
    return {str(row["name"]): str(row["label"]) for row in await list_tropes(bot.db)}


async def held_by_pin(bot: Any, guild: Any, member: Any) -> Outcome | None:
    """A pinned member is staff's own decision; a roll or a start never talks over it."""
    row = await voice_row(bot.db, guild.id, member.id)
    pinned = str(col(row, "pinned", ""))
    if not pinned:
        return None
    labels = await labels_of(bot)
    return refusal(
        words(
            bot.store,
            guild.id,
            tone_keys.IS_PINNED_KEY,
            member=member_name(member),
            tone=labels.get(pinned, pinned),
        ),
        PINNED_CODE,
        409,
    )


async def reroll_voice(
    bot: Any,
    guild: Any,
    actor: Any,
    user_id: Any,
    *,
    via: str = VIA_DISCORD,
    rng: Any = None,
    now: datetime | None = None,
) -> Outcome:
    """A new starting tone at random, never the one the member has while another is on."""
    member = member_of(guild, user_id)
    if member is None:
        return no_member(bot, guild, user_id)
    held = await held_by_pin(bot, guild, member)
    if held is not None:
        return held
    row = await voice_row(bot.db, guild.id, member.id)
    before = col(row, "tone")
    found = another(enabled_tropes(await list_tropes(bot.db)), before, rng)
    if found is None:
        return refusal(words(bot.store, guild.id, tone_keys.NO_TONES_KEY), NO_TONES_CODE, 409)
    await set_tone(
        bot.db, guild.id, member.id, found.name, how=ROLLED, by=actor_id(actor), now=now
    )
    await log_action(
        bot,
        guild,
        kind_via("chat.voice_rerolled", via),
        actor=actor,
        target=member,
        details={"member": str(member.id), "from": before, "tone": found.name, "via": via},
    )
    return Outcome(
        True,
        words(
            bot.store,
            guild.id,
            tone_keys.REROLLED_KEY,
            member=member_name(member),
            tone=found.label,
        ),
        value=found.name,
    )


async def start_voice(
    bot: Any,
    guild: Any,
    actor: Any,
    user_id: Any,
    tone: Any,
    *,
    via: str = VIA_DISCORD,
    now: datetime | None = None,
) -> Outcome:
    """A starting tone staff chose: used from the next answer, free to drift like any other."""
    member = member_of(guild, user_id)
    if member is None:
        return no_member(bot, guild, user_id)
    held = await held_by_pin(bot, guild, member)
    if held is not None:
        return held
    wanted, refused = await usable_tone(bot, guild, tone)
    if refused is not None:
        return refused
    row = await voice_row(bot.db, guild.id, member.id)
    name = str(wanted["name"])
    await set_tone(bot.db, guild.id, member.id, name, how=SET, by=actor_id(actor), now=now)
    await log_action(
        bot,
        guild,
        kind_via("chat.voice_set", via),
        actor=actor,
        target=member,
        details={"member": str(member.id), "from": col(row, "tone"), "tone": name, "via": via},
    )
    return Outcome(
        True,
        words(
            bot.store,
            guild.id,
            tone_keys.TONE_SET_KEY,
            member=member_name(member),
            tone=str(wanted["label"]),
        ),
        value=name,
    )


def role_of(guild: Any, role_id: Any) -> Any:
    try:
        wanted = int(getattr(role_id, "id", role_id))
    except (TypeError, ValueError):
        return None
    getter = getattr(guild, "get_role", None)
    return getter(wanted) if getter is not None else None


def role_lines(store: Any, guild_id: int, found: dict[str, Any]) -> list[str]:
    """Who got what, then who was left alone because staff pinned them."""
    lines = [
        words(
            store,
            guild_id,
            tone_keys.ROLE_LINE_KEY,
            member=f"<@{one['user_id']}>",
            tone=one["label"],
        )
        for one in found["rolled"]
    ]
    lines += [
        words(
            store,
            guild_id,
            tone_keys.ROLE_PINNED_LINE_KEY,
            member=f"<@{one['user_id']}>",
            tone=one["label"],
        )
        for one in found["pinned"]
    ]
    return lines


async def roll_role(
    bot: Any,
    guild: Any,
    actor: Any,
    role_id: Any,
    *,
    everyone: bool = False,
    via: str = VIA_DISCORD,
    rng: Any = None,
    now: datetime | None = None,
) -> Outcome:
    """A starting tone for each member of a role; a pin is skipped and said so."""
    role = role_of(guild, role_id)
    if role is None:
        return refusal(
            words(bot.store, guild.id, tone_keys.NO_ROLE_KEY), NO_SUCH_ROLE_CODE, 404
        )
    pool = enabled_tropes(await list_tropes(bot.db))
    if not pool:
        return refusal(words(bot.store, guild.id, tone_keys.NO_TONES_KEY), NO_TONES_CODE, 409)
    labels = await labels_of(bot)
    members = sorted(
        (one for one in getattr(role, "members", ()) or () if not getattr(one, "bot", False)),
        key=lambda one: int(one.id),
    )
    rolled, pinned, kept = [], [], 0
    by = actor_id(actor)
    for member in members:
        row = await voice_row(bot.db, guild.id, member.id)
        fixed = str(col(row, "pinned", ""))
        entry = {"user_id": int(member.id), "name": member_name(member)}
        if fixed:
            pinned.append({**entry, "tone": fixed, "label": labels.get(fixed, fixed)})
            continue
        before = col(row, "tone")
        if before and not everyone:
            kept += 1
            continue
        found = another(pool, before, rng)
        await set_tone(bot.db, guild.id, member.id, found.name, how=ROLLED, by=by, now=now)
        rolled.append({**entry, "tone": found.name, "label": found.label})
    name = str(getattr(role, "name", role.id))
    await log_action(
        bot,
        guild,
        kind_via("chat.voice_role_rolled", via),
        actor=actor,
        details={
            "role_id": str(role.id),
            "role": name,
            "everyone": bool(everyone),
            "rolled": len(rolled),
            "pinned": len(pinned),
            "kept": kept,
            "tones": {str(one["user_id"]): one["tone"] for one in rolled[:LOGGED_TONES]},
            "via": via,
        },
    )
    return Outcome(
        True,
        words(
            bot.store,
            guild.id,
            tone_keys.ROLE_ROLLED_KEY,
            rolled=len(rolled),
            role=name,
            pinned=len(pinned),
            kept=kept,
        ),
        value={"role": name, "rolled": rolled, "pinned": pinned, "kept": kept},
    )
