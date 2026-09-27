"""Each BaF run's public highlight: posted by staff or when the run goes live, edited in step,
taken down by staff."""

from __future__ import annotations

import logging
import re
from typing import Any

import discord

from ... import marathon as mt
from ... import marathon_inbox as mi
from ... import marathon_public as mp
from ... import marathon_runner_posts as mrp
from ... import shadow as shadow_home
from ...actionlog import log_action
from ...command_errors import SafeDynamicItem
from ...golive import ping_prefix
from ...logkinds import VIA_DISCORD, kind_via
from ...panels import Outcome, answer, refusal, still_staff
from ...settings_store import (
    DB_UNAVAILABLE,
    MARATHON_PUBLIC_ALREADY_KEY,
    MARATHON_PUBLIC_AUTO_OFF_SAID_KEY,
    MARATHON_PUBLIC_AUTO_ON_SAID_KEY,
    MARATHON_PUBLIC_AUTO_SAME_KEY,
    MARATHON_PUBLIC_BUTTON_POST_KEY,
    MARATHON_PUBLIC_BUTTON_REMOVE_KEY,
    MARATHON_PUBLIC_CHANNEL_KEY,
    MARATHON_PUBLIC_DEFAULT_KEY,
    MARATHON_PUBLIC_FAILED_KEY,
    MARATHON_PUBLIC_NO_CHANNEL_KEY,
    MARATHON_PUBLIC_NOT_POSTABLE_KEY,
    MARATHON_PUBLIC_NOT_UP_KEY,
    MARATHON_PUBLIC_POSTED_SAID_KEY,
    MARATHON_PUBLIC_REMOVED_KEY,
    MARATHON_PUBLIC_REMOVED_SAID_KEY,
    MARATHON_PUBLIC_TEMPLATE_KEY,
    MARATHON_RUNNER_POST_UNLISTED_KEY,
)
from ...spotlight import reason_of
from .marathon import (
    GOLIVE_CHANNEL_KEY,
    MODE_IS_OFF,
    MODE_OFF,
    MODE_ON,
    NO_CHANNEL,
    NO_SUCH,
    NO_SUCH_RUN_CODE,
    NOT_VISIBLE,
    TEST_MODE,
    channel_login,
    cog_of,
    get_marathon,
    mode_of,
    run_by_id,
    runs_of,
    said_default,
    update_marathon,
    update_run,
    words_for,
)

log = logging.getLogger(__name__)

NO_PUBLIC_CODE = "no_public_channel"
NOT_POSTABLE_CODE = "not_postable"
FAILED_CODE = "post_failed"


def words(bot: Any, guild_id: int, key: str, **fields: Any) -> str:
    return mt.render(bot.store.get(guild_id, key), said_default(key), **fields).text


def default_for_new(bot: Any, guild_id: int) -> int:
    return 1 if bot.store.get(guild_id, MARATHON_PUBLIC_DEFAULT_KEY) else 0


def public_channel(bot: Any, guild_id: int) -> int | None:
    """The public channel the key names, else go-live."""
    for key in (MARATHON_PUBLIC_CHANNEL_KEY, GOLIVE_CHANNEL_KEY):
        found = shadow_home.as_channel_id(bot.store.get(guild_id, key))
        if found is not None:
            return found
    return None


def channel_name(bot: Any, guild: Any, channel_id: Any) -> str:
    found = shadow_home.channel_of(bot, guild, channel_id)
    return str(getattr(found, "name", None) or channel_id or "?")


def public_cache(cog: Any, marathon_id: Any) -> dict[int, tuple[int, str]]:
    found = cog.__dict__.setdefault("public_sent", {})
    return found.setdefault(int(marathon_id), {})


def details_of(marathon: Any, row: Any) -> dict[str, Any]:
    return {
        "marathon_id": marathon["id"],
        "run_id": row["id"],
        "members": mt.member_ids(row),
        "game": row["game"],
    }


def rehearsal_of(bot: Any, guild: Any) -> dict[str, Any]:
    if mode_of(bot, guild.id) == MODE_ON:
        return {}
    return {"shadow_home": shadow_home.channel_id(bot, guild, feature=mp.SHADOW_FEATURE)}


def shadowed(bot: Any, guild: Any, text: str) -> str:
    home = public_channel(bot, guild.id)
    said = shadow_home.note_line(bot, guild, f"<#{home}>" if home else "#?")
    return f"{said}\n{text}" if said else text


def button_of(bot: Any, guild: Any, marathon_id: Any, row: Any) -> mp.Button | None:
    channel = public_channel(bot, guild.id)
    return mp.button_for(
        marathon_id,
        row,
        has_channel=channel is not None,
        post_label=words(
            bot,
            guild.id,
            MARATHON_PUBLIC_BUTTON_POST_KEY,
            channel=channel_name(bot, guild, channel) if channel else "?",
        ),
        remove_label=words(bot, guild.id, MARATHON_PUBLIC_BUTTON_REMOVE_KEY),
    )


def view_of(button: mp.Button | None, marathon_id: Any, run_id: Any) -> discord.ui.View | None:
    if button is None:
        return None
    view = discord.ui.View(timeout=None)
    view.add_item(HighlightButton(marathon_id, run_id, button.to, button.label))
    return view


async def public_text(
    bot: Any, guild: Any, marathon: Any, row: Any, *, removed: bool = False
) -> str:
    said = words_for(bot, guild.id)
    key = MARATHON_PUBLIC_REMOVED_KEY if removed else MARATHON_PUBLIC_TEMPLATE_KEY
    login = await channel_login(bot, marathon)
    return mp.text_of(
        row,
        marathon,
        said,
        template=said[key],
        default=said_default(key),
        url=mt.run_url(row, login, marathon["schedule_url"]),
        unlisted=said[MARATHON_RUNNER_POST_UNLISTED_KEY],
    )


def mentions_for(roles: list[int]) -> discord.AllowedMentions:
    if not roles:
        return discord.AllowedMentions.none()
    return discord.AllowedMentions(
        everyone=False, users=False, roles=[discord.Object(one) for one in roles]
    )


async def send_public(
    bot: Any, guild: Any, text: str, roles: list[int]
) -> tuple[Any, int | None, str | None]:
    """On: the public channel. Shadow: its rehearsal home, with the note naming it."""
    mode = mode_of(bot, guild.id)
    if mode == MODE_OFF:
        return (None, None, MODE_IS_OFF)
    home = public_channel(bot, guild.id)
    if home is None:
        return (None, None, NO_CHANNEL)
    channel_id = (
        home if mode == MODE_ON else shadow_home.channel_id(bot, guild, feature=mp.SHADOW_FEATURE)
    )
    if channel_id is None:
        return (None, None, NO_CHANNEL)
    guard = getattr(bot, "guard", None)
    if guard is not None and not guard.allows_channel(channel_id):
        return (None, None, TEST_MODE)
    channel = shadow_home.channel_of(bot, guild, channel_id)
    if channel is None:
        return (None, None, NOT_VISIBLE)
    body = text if mode == MODE_ON else shadowed(bot, guild, text)
    try:
        message = await channel.send(body, allowed_mentions=mentions_for(roles))
    except Exception as exc:
        return (None, channel_id, reason_of(exc))
    return (message, int(channel_id), None)


async def fetch_public(bot: Any, guild: Any, row: Any) -> tuple[Any, bool]:
    """`(message, lost)`: lost only when Discord says the message or its channel is gone."""
    from .marathon_inbox import find_channel

    channel, lost = await find_channel(bot, guild, mp.channel_of(row))
    if channel is None:
        return (None, lost)
    try:
        return (await channel.fetch_message(int(mp.message_id(row))), False)
    except (discord.NotFound, LookupError):
        return (None, True)
    except Exception as exc:
        log.info("marathon: could not read a highlight — %s", reason_of(exc))
        return (None, False)


async def edit_public(bot: Any, guild: Any, message: Any, text: str) -> str | None:
    shadow = mode_of(bot, guild.id) != MODE_ON
    try:
        await message.edit(
            content=shadowed(bot, guild, text) if shadow else text,
            allowed_mentions=discord.AllowedMentions.none(),
        )
    except Exception as exc:
        return reason_of(exc)
    return None


async def post_highlight(
    cog: Any,
    guild: Any,
    marathon: Any,
    row: Any,
    *,
    actor: Any = None,
    via: str = VIA_DISCORD,
    auto: bool = False,
) -> tuple[str | None, int | None]:
    """`(why, channel_id)`: a highlight staff took down comes back in place when it is still in
    the channel it would go to now; otherwise a new one is posted."""
    bot = cog.bot
    text = await public_text(bot, guild, marathon, row)
    shadow = mode_of(bot, guild.id) != MODE_ON
    base = details_of(marathon, row) | {"auto": auto, "via": via}
    if mp.message_id(row) and mp.is_removed(row):
        wanted = (
            shadow_home.channel_id(bot, guild, feature=mp.SHADOW_FEATURE)
            if shadow
            else public_channel(bot, guild.id)
        )
        if wanted is not None and mp.channel_of(row) == int(wanted):
            message, _lost = await fetch_public(bot, guild, row)
            if message is not None and await edit_public(bot, guild, message, text) is None:
                await update_run(bot.db, row["id"], public_removed=0)
                public_cache(cog, marathon["id"])[int(row["id"])] = (int(wanted), text)
                await log_action(
                    bot,
                    guild,
                    kind_via("marathon.public_highlight_restored", via),
                    actor=actor,
                    details=base | {"message_id": str(message.id)} | rehearsal_of(bot, guild),
                )
                return (None, int(wanted))
    roles = await cog._ping_roles(guild, marathon, row)
    sent, channel_id, why = await send_public(bot, guild, ping_prefix(*roles) + text, roles)
    if sent is None:
        await log_action(
            bot,
            guild,
            kind_via("marathon.public_highlight_failed", via),
            actor=actor,
            details=base | {"step": "post", "reason": why},
        )
        return (why, None)
    await update_run(
        bot.db,
        row["id"],
        public_message_id=int(sent.id),
        public_channel_id=channel_id,
        public_removed=0,
    )
    public_cache(cog, marathon["id"])[int(row["id"])] = (int(channel_id), text)
    await log_action(
        bot,
        guild,
        kind_via(
            "marathon.would_post_public_highlight" if shadow else "marathon.public_highlight_posted",
            via,
        ),
        actor=actor,
        details=base
        | {"message_id": str(sent.id), "channel_id": channel_id, "pinged": bool(roles)}
        | {"roles": roles}
        | rehearsal_of(bot, guild),
    )
    return (None, channel_id)


async def remove_highlight(
    cog: Any, guild: Any, marathon: Any, row: Any, *, actor: Any = None, via: str = VIA_DISCORD
) -> None:
    """The decision is stored first; the edit to the key sentence is cosmetic and may fail."""
    bot = cog.bot
    await update_run(bot.db, row["id"], public_removed=1)
    public_cache(cog, marathon["id"]).pop(int(row["id"]), None)
    message, _lost = await fetch_public(bot, guild, row)
    edited = False
    if message is not None:
        why = await edit_public(
            bot, guild, message, await public_text(bot, guild, marathon, row, removed=True)
        )
        edited = why is None
        if why is not None:
            await log_action(
                bot,
                guild,
                kind_via("marathon.public_highlight_failed", via),
                actor=actor,
                details=details_of(marathon, row) | {"step": "remove", "reason": why, "via": via},
            )
    await log_action(
        bot,
        guild,
        kind_via("marathon.public_highlight_removed", via),
        actor=actor,
        details=details_of(marathon, row)
        | {"message_id": str(mp.message_id(row)), "edited": edited, "via": via},
    )


async def sync_highlights(cog: Any, guild: Any, marathon: Any) -> None:
    """Every highlight that is up follows its run; unchanged costs no Discord call."""
    bot = cog.bot
    if marathon is None:
        return
    rows = [one for one in await runs_of(bot.db, marathon["id"]) if mp.is_up(one)]
    cache = public_cache(cog, marathon["id"])
    for row in rows:
        key = int(row["id"])
        text = await public_text(bot, guild, marathon, row)
        if cache.get(key) == (mp.channel_of(row), text):
            continue
        message, lost = await fetch_public(bot, guild, row)
        if message is None:
            if lost:
                await update_run(bot.db, key, public_message_id=None, public_channel_id=None)
                cache.pop(key, None)
                await log_action(
                    bot,
                    guild,
                    "marathon.public_highlight_lost",
                    details=details_of(marathon, row) | {"message_id": str(mp.message_id(row))},
                )
            continue
        if (getattr(message, "content", None) or "").endswith(text):
            cache[key] = (mp.channel_of(row), text)
            continue
        why = await edit_public(bot, guild, message, text)
        if why is not None:
            await log_action(
                bot,
                guild,
                "marathon.public_highlight_failed",
                details=details_of(marathon, row) | {"step": "edit", "reason": why},
            )
            continue
        cache[key] = (mp.channel_of(row), text)
        shadow = mode_of(bot, guild.id) != MODE_ON
        await log_action(
            bot,
            guild,
            "marathon.would_edit_public_highlight"
            if shadow
            else "marathon.public_highlight_edited",
            details=details_of(marathon, row)
            | {"message_id": str(message.id), "state": row["state"]}
            | rehearsal_of(bot, guild),
        )


async def auto_highlight(cog: Any, guild: Any, marathon: Any, row: Any) -> None:
    """The moment a run's shoutout fires: posted when the marathon's switch is on, never
    again once staff took it down. A failure here never breaks the shoutout."""
    try:
        if not mi.is_tracked(marathon) or not mp.auto_wanted(marathon, row):
            return
        if mode_of(cog.bot, guild.id) == MODE_OFF or public_channel(cog.bot, guild.id) is None:
            return
        await post_highlight(cog, guild, marathon, row, auto=True)
    except Exception as exc:
        log.warning("marathon: the auto-highlight failed — %s", reason_of(exc))


async def rerender_post(cog: Any, guild: Any, marathon_id: Any) -> None:
    from .marathon_runner_posts import sync_posts

    try:
        await sync_posts(cog, guild, await get_marathon(cog.bot.db, guild.id, marathon_id))
    except Exception as exc:
        log.warning("marathon: a runner post re-render failed — %s", reason_of(exc))


async def press(
    bot: Any,
    guild: Any,
    actor: Any,
    marathon_id: Any,
    run_id: Any,
    to: str,
    *,
    via: str = VIA_DISCORD,
) -> Outcome:
    cog = cog_of(bot)
    marathon = await get_marathon(bot.db, guild.id, marathon_id)
    if marathon is None or cog is None:
        return refusal(mt.NO_SUCH_MARATHON.format(given=marathon_id), NO_SUCH, 404)
    async with cog.lock(marathon["id"]):
        row = await run_by_id(bot.db, marathon["id"], run_id)
        if row is None:
            return refusal(mt.NO_SUCH_RUN.format(name=marathon["name"]), NO_SUCH_RUN_CODE, 404)
        runner = mrp.names_of(row)
        if to == mp.POST:
            outcome = await highlight_now(cog, guild, actor, marathon, row, runner, via=via)
        elif not mp.is_up(row):
            outcome = Outcome(True, words(bot, guild.id, MARATHON_PUBLIC_NOT_UP_KEY, runner=runner))
        else:
            await remove_highlight(cog, guild, marathon, row, actor=actor, via=via)
            outcome = Outcome(
                True,
                words(
                    bot,
                    guild.id,
                    MARATHON_PUBLIC_REMOVED_SAID_KEY,
                    runner=runner,
                    channel=f"<#{mp.channel_of(row)}>",
                ),
            )
        await rerender_post(cog, guild, marathon["id"])
    return outcome


async def highlight_now(
    cog: Any, guild: Any, actor: Any, marathon: Any, row: Any, runner: str, *, via: str
) -> Outcome:
    bot = cog.bot
    if mp.is_up(row):
        return Outcome(
            True,
            words(
                bot,
                guild.id,
                MARATHON_PUBLIC_ALREADY_KEY,
                runner=runner,
                channel=f"<#{mp.channel_of(row)}>",
            ),
        )
    if not mp.postable(row):
        return refusal(
            words(bot, guild.id, MARATHON_PUBLIC_NOT_POSTABLE_KEY, runner=runner, game=row["game"]),
            NOT_POSTABLE_CODE,
            409,
        )
    if public_channel(bot, guild.id) is None:
        return refusal(words(bot, guild.id, MARATHON_PUBLIC_NO_CHANNEL_KEY), NO_PUBLIC_CODE, 409)
    why, channel_id = await post_highlight(cog, guild, marathon, row, actor=actor, via=via)
    if why is not None:
        return refusal(
            words(bot, guild.id, MARATHON_PUBLIC_FAILED_KEY, runner=runner, reason=why),
            FAILED_CODE,
            409,
        )
    return Outcome(
        True,
        words(
            bot,
            guild.id,
            MARATHON_PUBLIC_POSTED_SAID_KEY,
            runner=runner,
            channel=f"<#{channel_id}>",
        ),
    )


async def set_public_highlight(
    bot: Any, guild: Any, actor: Any, marathon: Any, given: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    """The one writer of `marathons.public_highlight`: the thread controls, the drawer and the
    PATCH all come here, and the controls re-render after."""
    from .marathon_thread_controls import controls_changed

    wanted = mp.clean_switch(given)
    if wanted is None:
        return refusal(mp.BAD_SWITCH, mp.BAD_SWITCH_CODE, 422)
    cog = cog_of(bot)
    async with cog.lock(marathon["id"]):
        fresh = await get_marathon(bot.db, guild.id, marathon["id"])
        if fresh is None:
            return refusal(mt.NO_SUCH_MARATHON.format(given=marathon["id"]), NO_SUCH, 404)
        was = mp.highlights(fresh)
        if was == wanted:
            said = words(bot, guild.id, MARATHON_PUBLIC_AUTO_SAME_KEY, marathon=fresh["name"])
            return Outcome(True, said, value=fresh)
        await update_marathon(bot.db, fresh["id"], public_highlight=1 if wanted else 0)
        fresh = await get_marathon(bot.db, guild.id, fresh["id"])
    await log_action(
        bot,
        guild,
        kind_via("marathon.public_highlight_set", via),
        actor=actor,
        details={
            "marathon_id": fresh["id"],
            "name": fresh["name"],
            "from": was,
            "to": wanted,
            "via": via,
        },
    )
    await controls_changed(bot, guild, fresh["id"])
    channel = public_channel(bot, guild.id)
    key = MARATHON_PUBLIC_AUTO_ON_SAID_KEY if wanted else MARATHON_PUBLIC_AUTO_OFF_SAID_KEY
    return Outcome(
        True,
        words(
            bot,
            guild.id,
            key,
            marathon=fresh["name"],
            channel=f"<#{channel}>" if channel else "#?",
        ),
        value=fresh,
    )


class HighlightButton(
    SafeDynamicItem, discord.ui.DynamicItem[discord.ui.Button], template=mp.TEMPLATE
):
    def __init__(self, marathon_id: int, run_id: int, to: str, label: str | None = None) -> None:
        self.marathon_id = int(marathon_id)
        self.run_id = int(run_id)
        self.to = to
        super().__init__(
            discord.ui.Button(
                label=mp.label(label or to),
                style=(
                    discord.ButtonStyle.primary if to == mp.POST else discord.ButtonStyle.secondary
                ),
                custom_id=mp.custom_id(marathon_id, run_id, to),
            )
        )

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: Any, match: re.Match):
        return cls(int(match["marathon_id"]), int(match["run_id"]), match["to"])

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
        outcome = await press(
            bot, interaction.guild, interaction.user, self.marathon_id, self.run_id, self.to
        )
        await answer(interaction, outcome.message)


__all__ = [
    "HighlightButton",
    "auto_highlight",
    "button_of",
    "default_for_new",
    "post_highlight",
    "press",
    "public_channel",
    "remove_highlight",
    "set_public_highlight",
    "sync_highlights",
    "view_of",
]
