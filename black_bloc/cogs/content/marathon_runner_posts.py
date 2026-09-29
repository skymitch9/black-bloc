"""Each BaF run's own post in a tracked marathon's thread: posted, pinned, edited, unpinned."""

from __future__ import annotations

from typing import Any

import discord

from ... import marathon as mt
from ... import marathon_inbox as mi
from ... import marathon_public as mp
from ... import marathon_runner_posts as mrp
from ...actionlog import log_action
from ...settings_store import (
    MARATHON_RUNNER_POST_TEMPLATE_KEY,
    MARATHON_RUNNER_POST_UNLISTED_KEY,
    MARATHON_RUNNER_POSTS_KEY,
    MARATHON_RUNNER_POSTS_PINNED_KEY,
)
from ...spotlight import reason_of
from .marathon import (
    MODE_OFF,
    MODE_ON,
    channel_login,
    mode_of,
    rehearsal_details,
    runs_of,
    said_default,
    update_run,
    words_for,
)


def sent_cache(cog: Any, marathon_id: Any) -> dict[int, tuple[int, str, Any]]:
    found = cog.__dict__.setdefault("posts_sent", {})
    return found.setdefault(int(marathon_id), {})


def capped_channels(cog: Any) -> set[int]:
    return cog.__dict__.setdefault("pin_capped", set())


def details_of(marathon: Any, row: Any) -> dict[str, Any]:
    return {
        "marathon_id": marathon["id"],
        "run_id": row["id"],
        "members": mt.member_ids(row),
        "game": row["game"],
    }


async def sync_posts(cog: Any, guild: Any, marathon: Any) -> None:
    """After the board: one post per BaF run, posted once and edited when its words change."""
    bot = cog.bot
    if marathon is None or not bot.store.get(guild.id, MARATHON_RUNNER_POSTS_KEY):
        return
    mode = mode_of(bot, guild.id)
    if mode == MODE_OFF or not mi.is_tracked(marathon) or not marathon["board_message_id"]:
        return
    rows = mrp.wanted(await runs_of(bot.db, marathon["id"]))
    if not rows:
        return
    target, _why = await cog._place(guild, marathon)
    if target is None:
        return
    from .marathon_public import button_of

    words = words_for(bot, guild.id)
    login = await channel_login(bot, marathon)
    for row in rows:
        text = mrp.post_text(
            row,
            marathon,
            words,
            template=words[MARATHON_RUNNER_POST_TEMPLATE_KEY],
            default=said_default(MARATHON_RUNNER_POST_TEMPLATE_KEY),
            url=mt.run_url(row, login, marathon["schedule_url"]),
            unlisted=words[MARATHON_RUNNER_POST_UNLISTED_KEY],
        ).text
        button = button_of(bot, guild, marathon, row)
        await sync_one(
            cog, guild, marathon, row, int(target), text, shadow=mode != MODE_ON, button=button
        )


async def sync_one(
    cog: Any,
    guild: Any,
    marathon: Any,
    row: Any,
    target: int,
    text: str,
    *,
    shadow: bool,
    button: Any = None,
) -> None:
    cache = sent_cache(cog, marathon["id"])
    key = int(row["id"])
    if mrp.post_id(row) and mrp.post_channel(row) == target:
        if cache.get(key) == (target, text, button):
            return
        message = await cog._fetch(guild, target, mrp.post_id(row))
        if message is not None:
            await edit_one(
                cog, guild, marathon, row, message, target, text, shadow=shadow, button=button
            )
            return
    if not mt.is_ours(row) or mt._cell(row, "state") not in mrp.POSTABLE:
        return
    await post_one(cog, guild, marathon, row, target, text, shadow=shadow, button=button)


def view_for(marathon: Any, row: Any, button: Any) -> Any:
    from .marathon_public import view_of

    return view_of(button, marathon["id"], row["id"])


async def edit_one(
    cog: Any,
    guild: Any,
    marathon: Any,
    row: Any,
    message: Any,
    target: int,
    text: str,
    *,
    shadow: bool,
    button: Any = None,
) -> None:
    cache = sent_cache(cog, marathon["id"])
    key = int(row["id"])
    same_words = (getattr(message, "content", None) or "").endswith(text)
    if same_words and mp.shown_button(message) == button:
        cache[key] = (target, text, button)
        return
    try:
        await message.edit(
            content=cog._shadowed(guild, text) if shadow else text,
            view=view_for(marathon, row, button),
            allowed_mentions=discord.AllowedMentions.none(),
        )
    except Exception as exc:
        await log_action(
            cog.bot,
            guild,
            "marathon.runner_post_failed",
            details=details_of(marathon, row) | {"step": "edit", "reason": reason_of(exc)},
        )
        return
    cache[key] = (target, text, button)
    await log_action(
        cog.bot,
        guild,
        "marathon.would_edit_runner_post" if shadow else "marathon.runner_post_edited",
        details=details_of(marathon, row)
        | {"message_id": str(message.id), "state": row["state"]}
        | rehearsal_details(cog.bot, guild),
    )


async def post_one(
    cog: Any,
    guild: Any,
    marathon: Any,
    row: Any,
    target: int,
    text: str,
    *,
    shadow: bool,
    button: Any = None,
) -> None:
    bot = cog.bot
    sent, channel_id, why = await cog._send(
        guild, text, [], quiet=True, marathon=marathon, view=view_for(marathon, row, button)
    )
    if sent is None:
        await log_action(
            bot,
            guild,
            "marathon.runner_post_failed",
            details=details_of(marathon, row) | {"step": "post", "reason": why},
        )
        return
    await update_run(
        bot.db, row["id"], post_message_id=int(sent.id), post_channel_id=channel_id, post_pinned=0
    )
    sent_cache(cog, marathon["id"])[int(row["id"])] = (target, text, button)
    await log_action(
        bot,
        guild,
        "marathon.would_post_runner_post" if shadow else "marathon.runner_post_posted",
        details=details_of(marathon, row)
        | {"message_id": str(sent.id), "channel_id": channel_id}
        | rehearsal_details(bot, guild),
    )
    if (
        not shadow
        and bot.store.get(guild.id, MARATHON_RUNNER_POSTS_PINNED_KEY)
        and not mt.board_due_off(marathon, cog.clock())
        and mrp.pins_now(row, cog.clock())
    ):
        await pin_one(cog, guild, marathon, row, sent, int(channel_id or target))


async def pin_one(
    cog: Any, guild: Any, marathon: Any, row: Any, message: Any, channel_id: int
) -> None:
    try:
        await message.pin(reason=mrp.PIN_REASON)
    except Exception as exc:
        if mrp.is_pin_cap(exc):
            if channel_id not in capped_channels(cog):
                capped_channels(cog).add(channel_id)
                await log_action(
                    cog.bot,
                    guild,
                    "marathon.runner_post_pin_capped",
                    details=details_of(marathon, row)
                    | {"channel_id": channel_id, "reason": reason_of(exc)},
                )
            return
        await log_action(
            cog.bot,
            guild,
            "marathon.runner_post_pin_failed",
            details=details_of(marathon, row) | {"reason": reason_of(exc)},
        )
        return
    await update_run(cog.bot.db, row["id"], post_pinned=1)
    await log_action(
        cog.bot,
        guild,
        "marathon.runner_post_pinned",
        details=details_of(marathon, row) | {"message_id": str(message.id)},
    )


async def unpin_one(cog: Any, guild: Any, marathon: Any, row: Any, because: str) -> None:
    """Checklist 3: the pin comes off because the message carries one, whatever the keys say."""
    await update_run(cog.bot.db, row["id"], post_pinned=0)
    message = await cog._fetch(guild, mrp.post_channel(row), mrp.post_id(row))
    if message is None or not bool(getattr(message, "pinned", False)):
        return
    try:
        await message.unpin(reason=mrp.UNPIN_REASON)
    except Exception as exc:
        await log_action(
            cog.bot,
            guild,
            "marathon.runner_post_unpin_failed",
            details=details_of(marathon, row) | {"reason": reason_of(exc)},
        )
        return
    await log_action(
        cog.bot,
        guild,
        "marathon.runner_post_unpinned",
        details=details_of(marathon, row) | {"because": because},
    )


async def unpin_posts(
    cog: Any,
    guild: Any,
    marathon: Any,
    *,
    because: str,
    runs: Any = None,
    channel_id: int | None = None,
) -> None:
    """Every pinned runner post of the marathon, or only those in `channel_id`."""
    rows = runs if runs is not None else await runs_of(cog.bot.db, marathon["id"])
    for row in rows:
        if not mrp.is_pinned(row):
            continue
        if channel_id is not None and mrp.post_channel(row) != int(channel_id):
            continue
        await unpin_one(cog, guild, marathon, row, because)


async def unpin_due(cog: Any, guild: Any, marathon: Any) -> None:
    """Every tick, whatever the mode or the keys (checklist 38)."""
    rows = [one for one in await runs_of(cog.bot.db, marathon["id"]) if mrp.is_pinned(one)]
    if not rows:
        return
    now = cog.clock()
    over = mt.board_due_off(marathon, now)
    for row in rows:
        because = mrp.BECAUSE_MARATHON_OVER if over else mrp.unpin_because(row, now)
        if because is not None:
            await unpin_one(cog, guild, marathon, row, because)
