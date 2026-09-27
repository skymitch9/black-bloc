"""One post per exact near miss in a tracked marathon's thread; staff link or dismiss it."""

from __future__ import annotations

import re
from typing import Any

import discord

from ... import marathon as mt
from ... import marathon_inbox as mi
from ... import marathon_near_miss as mnm
from ... import marathon_people as mp
from ...actionlog import log_action
from ...command_errors import SafeDynamicItem
from ...logkinds import VIA_DISCORD
from ...panels import Outcome, answer, refusal, still_staff
from ...settings_store import (
    DB_UNAVAILABLE,
    MARATHON_MATCH_HOSTS_KEY,
    MARATHON_NEAR_MISS_ANSWERED_KEY,
    MARATHON_NEAR_MISS_DISMISSED_KEY,
    MARATHON_NEAR_MISS_DISMISSED_SAID_KEY,
    MARATHON_NEAR_MISS_EVERYWHERE_KEY,
    MARATHON_NEAR_MISS_GONE_KEY,
    MARATHON_NEAR_MISS_HERE_KEY,
    MARATHON_NEAR_MISS_LINKED_EVERYWHERE_KEY,
    MARATHON_NEAR_MISS_LINKED_KEY,
    MARATHON_NEAR_MISS_NOT_KEY,
    MARATHON_NEAR_MISS_POST_KEY,
    MARATHON_NEAR_MISS_POSTS_KEY,
)
from ...spotlight import reason_of
from .marathon import (
    MODE_OFF,
    MODE_ON,
    NO_SUCH,
    cog_of,
    get_marathon,
    mode_of,
    pair_runner,
    rehearsal_details,
    runs_of,
    usernames_of,
)
from .marathon_inbox import words

GONE_CODE = "near_miss_gone"
LABEL_KEYS = {
    mnm.HERE: MARATHON_NEAR_MISS_HERE_KEY,
    mnm.EVERYWHERE: MARATHON_NEAR_MISS_EVERYWHERE_KEY,
    mnm.NOT_THEM: MARATHON_NEAR_MISS_NOT_KEY,
}
DONE_KEYS = {
    mnm.HERE: MARATHON_NEAR_MISS_LINKED_KEY,
    mnm.EVERYWHERE: MARATHON_NEAR_MISS_LINKED_EVERYWHERE_KEY,
    mnm.NOT_THEM: MARATHON_NEAR_MISS_DISMISSED_KEY,
}
STYLES = {
    mnm.HERE: discord.ButtonStyle.primary,
    mnm.EVERYWHERE: discord.ButtonStyle.secondary,
    mnm.NOT_THEM: discord.ButtonStyle.secondary,
}
KEPT = ("marathon_id", "runner", "runner_key", "member_id", "message_id", "channel_id")


async def rows_of(db: Any, guild_id: int, marathon_id: int) -> list[Any]:
    marks = ", ".join("?" for _ in mnm.SEEN_KINDS)
    cur = await db.conn.execute(
        f"SELECT id, kind, details FROM action_log WHERE guild_id = ? AND kind IN ({marks}) "
        "AND json_extract(details, '$.marathon_id') = ? ORDER BY id DESC",
        (int(guild_id), *mnm.SEEN_KINDS, int(marathon_id)),
    )
    return list(await cur.fetchall())


def member_words(guild: Any, user_id: int, username: str) -> dict[str, str]:
    getter = getattr(guild, "get_member", None)
    member = getter(int(user_id)) if callable(getter) else None
    if member is None:
        member = next(
            (one for one in getattr(guild, "members", None) or () if int(one.id) == int(user_id)),
            None,
        )
    shown = getattr(member, "display_name", None) or username
    return {"member": f"<@{int(user_id)}>", "username": username, "display_name": str(shown)}


def view_of(bot: Any, guild_id: int, marathon_id: Any) -> discord.ui.View:
    view = discord.ui.View(timeout=None)
    for action in mnm.ACTIONS:
        label = mnm.label(words(bot, guild_id, LABEL_KEYS[action]))
        view.add_item(NearMissButton(marathon_id, action, label))
    return view


async def sync_near_misses(cog: Any, guild: Any, marathon: Any) -> None:
    """After the runner posts: one post per exact near miss, once per runner per place."""
    bot = cog.bot
    if marathon is None or not bot.store.get(guild.id, MARATHON_NEAR_MISS_POSTS_KEY):
        return
    mode = mode_of(bot, guild.id)
    if mode == MODE_OFF or not mi.is_tracked(marathon):
        return
    usernames = usernames_of(guild)
    if not usernames:
        return
    hosts = bool(bot.store.get(guild.id, MARATHON_MATCH_HOSTS_KEY))
    found = [
        (entry, near)
        for entry in mp.group_people(await runs_of(bot.db, marathon["id"]))
        for near in [mnm.exact_match(entry, usernames, match_hosts=hosts)]
        if near is not None
    ]
    if not found:
        return
    target, _why = await cog._place(guild, marathon)
    if target is None:
        return
    seen = mnm.seen_of(await rows_of(bot.db, guild.id, marathon["id"]))
    for entry, near in found:
        key = mp.person_key(entry)
        if key in seen.resolved or (key, int(target)) in seen.posted:
            continue
        await post_one(cog, guild, marathon, entry, near, shadow=mode != MODE_ON)


async def post_one(
    cog: Any,
    guild: Any,
    marathon: Any,
    entry: dict[str, Any],
    near: tuple[str, int],
    *,
    shadow: bool,
) -> None:
    bot = cog.bot
    username, user_id = near
    base = {
        "marathon_id": marathon["id"],
        "runner": entry["name"],
        "runner_key": mp.person_key(entry),
        "login": entry.get("login"),
        "member_id": int(user_id),
        "username": username,
    }
    text = words(
        bot,
        guild.id,
        MARATHON_NEAR_MISS_POST_KEY,
        runner=entry["name"],
        marathon=marathon["name"],
        **member_words(guild, user_id, username),
    )[: mt.MESSAGE_LIMIT]
    view = view_of(bot, guild.id, marathon["id"])
    sent, channel_id, why = await cog._send(
        guild, text, [], quiet=True, marathon=marathon, view=view
    )
    if sent is None:
        await log_action(
            bot, guild, "marathon.near_miss_failed", details=base | {"step": "post", "reason": why}
        )
        return
    await log_action(
        bot,
        guild,
        "marathon.would_post_near_miss" if shadow else "marathon.near_miss_posted",
        target=int(user_id),
        details=base
        | {"message_id": str(sent.id), "channel_id": channel_id}
        | rehearsal_details(bot, guild),
    )


async def press(
    bot: Any,
    guild: Any,
    actor: Any,
    marathon_id: Any,
    message_id: Any,
    action: str,
    *,
    via: str = VIA_DISCORD,
) -> Outcome:
    """Link through the one `pair_runner`, or dismiss as a `near_miss_resolved` row; then the
    post says what staff chose and loses its buttons."""
    marathon = await get_marathon(bot.db, guild.id, marathon_id)
    if marathon is None:
        return refusal(mt.NO_SUCH_MARATHON.format(given=marathon_id), NO_SUCH, 404)
    rows = await rows_of(bot.db, guild.id, marathon["id"])
    found = mnm.post_for(rows, message_id)
    if found is None:
        return refusal(words(bot, guild.id, MARATHON_NEAR_MISS_GONE_KEY), GONE_CODE, 404)
    row, details = found
    fields = {
        "runner": str(details.get("runner") or ""),
        "marathon": marathon["name"],
        **member_words(guild, int(details["member_id"]), str(details.get("username") or "")),
    }
    before = mnm.answered(rows, str(details.get("runner_key") or ""))
    if before is not None:
        await settle(bot, guild, row, details, before.get("outcome"), before.get("staff"), fields)
        return Outcome(True, words(bot, guild.id, MARATHON_NEAR_MISS_ANSWERED_KEY, **fields))
    if action in (mnm.HERE, mnm.EVERYWHERE):
        outcome = await pair_runner(
            bot,
            guild,
            actor,
            marathon,
            details.get("runner"),
            details["member_id"],
            everywhere=action == mnm.EVERYWHERE,
            via=via,
        )
        if not outcome.ok:
            return outcome
    else:
        said = words(bot, guild.id, MARATHON_NEAR_MISS_DISMISSED_SAID_KEY, **fields)
        outcome = Outcome(True, said)
    staff = f"<@{int(actor.id)}>"
    await log_action(
        bot,
        guild,
        "marathon.near_miss_resolved",
        actor=actor,
        target=int(details["member_id"]),
        details={key: details.get(key) for key in KEPT}
        | {"outcome": action, "staff": staff, "via": via},
    )
    await settle(bot, guild, row, details, action, staff, fields)
    return outcome


async def settle(
    bot: Any,
    guild: Any,
    row: Any,
    details: dict[str, Any],
    action: Any,
    staff: Any,
    fields: dict[str, str],
) -> None:
    """The post's own words become the outcome, with no buttons; a lost post is only logged."""
    cog = cog_of(bot)
    key = DONE_KEYS.get(str(action))
    if cog is None or key is None:
        return
    text = words(bot, guild.id, key, staff=staff or "staff", **fields)[: mt.MESSAGE_LIMIT]
    message = await cog._fetch(guild, details.get("channel_id"), details.get("message_id"))
    base = {"marathon_id": details.get("marathon_id"), "runner": details.get("runner")}
    if message is None:
        await log_action(
            bot,
            guild,
            "marathon.near_miss_failed",
            details=base | {"step": "edit", "reason": "gone"},
        )
        return
    try:
        await message.edit(
            content=cog._shadowed(guild, text) if row["kind"] == mnm.WOULD_POST else text,
            view=None,
            allowed_mentions=discord.AllowedMentions.none(),
        )
    except Exception as exc:
        await log_action(
            bot,
            guild,
            "marathon.near_miss_failed",
            details=base | {"step": "edit", "reason": reason_of(exc)},
        )


class NearMissButton(
    SafeDynamicItem, discord.ui.DynamicItem[discord.ui.Button], template=mnm.TEMPLATE
):
    def __init__(self, marathon_id: int, action: str, label: str | None = None) -> None:
        self.marathon_id = int(marathon_id)
        self.action = action
        super().__init__(
            discord.ui.Button(
                label=mnm.label(label or action),
                style=STYLES.get(action, discord.ButtonStyle.secondary),
                custom_id=mnm.custom_id(marathon_id, action),
            )
        )

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: Any, match: re.Match):
        return cls(int(match["marathon_id"]), match["action"])

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
        message = getattr(interaction, "message", None)
        outcome = await press(
            bot,
            interaction.guild,
            interaction.user,
            self.marathon_id,
            getattr(message, "id", None),
            self.action,
        )
        await answer(interaction, outcome.message)


__all__ = ["NearMissButton", "press", "sync_near_misses"]
