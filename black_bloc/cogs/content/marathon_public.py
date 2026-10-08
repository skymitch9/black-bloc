"""Each BaF run's public highlight: posted by staff or when the run goes live, edited in step,
taken down by staff."""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any

import discord

from ... import marathon as mt
from ... import marathon_announce as ma
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
    DEFAULT_TIMEZONE_KEY,
    MARATHON_PUBLIC_CHANNEL_KEY,
    MARATHON_PUBLIC_DAY_EARLIER_KEY,
    MARATHON_PUBLIC_DAY_TODAY_KEY,
    MARATHON_PUBLIC_DONE_TEMPLATE_KEY,
    MARATHON_PUBLIC_REMOVED_KEY,
    MARATHON_PUBLIC_TEMPLATE_KEY,
    MARATHON_RUNNER_POST_UNLISTED_KEY,
)
from ...spotlight import reason_of
from ...timezones import DEFAULT_TZ, zone
from .marathon import (
    GOLIVE_CHANNEL_KEY,
    MODE_IS_OFF,
    MODE_OFF,
    MODE_ON,
    NO_CHANNEL,
    NOT_VISIBLE,
    TEST_MODE,
    channel_login,
    mode_of,
    now_for,
    runs_of,
    said_default,
    update_run,
    words_for,
)

log = logging.getLogger(__name__)

NOBODY = "nobody_announced"
WHOLE_MARATHON_GONE = (
    "That button is gone — opt someone out of every run on this marathon from People… in "
    "/event, so nothing was changed."
)
GONE_CODE = "gone"


def words(bot: Any, guild_id: int, key: str, **fields: Any) -> str:
    return mt.render(bot.store.get(guild_id, key), said_default(key), **fields).text


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


def shadowed(bot: Any, guild: Any, text: str, home: int | None = None) -> str:
    home = home if home is not None else public_channel(bot, guild.id)
    said = shadow_home.note_line(bot, guild, f"<#{home}>" if home else "#?")
    return f"{said}\n{text}" if said else text


def button_of(bot: Any, guild: Any, marathon: Any, row: Any) -> tuple:
    """What a run's post carries: each person's own moves for this run."""
    from .marathon_announce import controls_of

    return controls_of(bot, guild, marathon, row)


def people_for(
    bot: Any,
    guild: Any,
    marathon: Any,
    row: Any,
    *,
    standing: bool = False,
    recorded: Any = None,
    moved: Any = (),
) -> list[dict[str, Any]]:
    """Everyone of ours a public post about the run names, as it writes them."""
    from .marathon_announce import people_for as announced

    return announced(bot, guild, marathon, row, standing=standing, recorded=recorded, moved=moved)


def named_on(row: Any) -> list[dict[str, Any]] | None:
    """Who the run's highlight names, by its own record; None for one from before the record."""
    return ma.named_of(mt._cell(row, ma.NAMED))


def written(was: Any) -> list[dict[str, Any]] | None:
    """Who a highlight named, as it wrote them: its record, else everyone of ours on the run."""
    from .marathon_announce import as_written

    return as_written(was) if was else None


def policy_for(bot: Any, guild: Any, marathon: Any) -> ma.Policy:
    from .marathon_announce import policy_of

    return policy_of(bot, guild.id, marathon)


def why_down(bot: Any, guild: Any, marathon: Any, row: Any, was: Any, moved: Any = ()) -> str:
    named = was if was is not None else mt.ours(mt.people_of(row))
    return ma.run_because(row, policy_for(bot, guild, marathon), named, moved)


def view_of(buttons: Any, marathon_id: Any, run_id: Any) -> discord.ui.View | None:
    """A row a person, or the menus."""
    if not buttons:
        return None
    view = discord.ui.View(timeout=None)
    rows: dict[int, int] = {}
    for one in buttons:
        if isinstance(one, ma.Pick):
            view.add_item(
                AnnouncePick(
                    marathon_id,
                    run_id,
                    one.label,
                    one.options,
                    page=one.custom_id.rsplit(ma.PICK, 1)[-1],
                    row=one.row,
                )
            )
        elif isinstance(one, ma.Move):
            row = rows.setdefault(one.user_id, len(rows) + 1)
            view.add_item(
                AnnounceButton(marathon_id, run_id, one.user_id, one.to, one.label, row=row)
            )
        else:
            view.add_item(HighlightButton(marathon_id, run_id, one.to, one.label))
    return view


def day_of(bot: Any, guild: Any, row: Any, said: dict[str, str]) -> str:
    """{day} for a finished run: measured from when it ended, in the server's zone."""
    return mp.day_word(
        row,
        now_for(bot),
        zone(bot.store.get(guild.id, DEFAULT_TIMEZONE_KEY)) or zone(DEFAULT_TZ),
        today=said[MARATHON_PUBLIC_DAY_TODAY_KEY],
        earlier=said[MARATHON_PUBLIC_DAY_EARLIER_KEY],
        earlier_default=said_default(MARATHON_PUBLIC_DAY_EARLIER_KEY),
    )


async def public_text(
    bot: Any,
    guild: Any,
    marathon: Any,
    row: Any,
    *,
    removed: bool = False,
    people: Any = None,
    present: bool = False,
    over: Any = None,
) -> str:
    """A runner's highlight, or a host's when `people` names the BaF hosts: one template, and
    the past-tense one once the run is done. `present` asks for the words a done post carried
    before it had its own; `over` is the run whose end dates a host block."""
    said = words_for(bot, guild.id)
    done = mp.is_done(row) and not removed and not present
    key = (
        MARATHON_PUBLIC_REMOVED_KEY
        if removed
        else MARATHON_PUBLIC_DONE_TEMPLATE_KEY
        if done
        else MARATHON_PUBLIC_TEMPLATE_KEY
    )
    login = await channel_login(bot, marathon)
    url = mt.run_url(row, login, marathon["schedule_url"], people=people)
    if done:
        return mp.done_text(
            row,
            marathon,
            said,
            template=said[key],
            default=said_default(key),
            url=url,
            unlisted=said[MARATHON_RUNNER_POST_UNLISTED_KEY],
            day=day_of(bot, guild, over if over is not None else row, said),
            people=people,
        )
    return mp.text_of(
        row,
        marathon,
        said,
        template=said[key],
        default=said_default(key),
        url=url,
        unlisted=said[MARATHON_RUNNER_POST_UNLISTED_KEY],
        people=people,
    )


def since(cog: Any) -> datetime:
    """When this process first followed a highlight: a run over before it is not re-worded."""
    return cog.__dict__.setdefault("public_since", cog.clock())


async def stands(
    cog: Any,
    guild: Any,
    marathon: Any,
    row: Any,
    message: Any,
    text: str,
    *,
    people: Any = None,
    over: Any = None,
) -> bool:
    """The post already says it. A run that was over before this process started keeps the
    present-tense words it finished with, role mention and all."""
    content = getattr(message, "content", None) or ""
    done = mp.is_done(row)
    if mp.says(content, text, done=done):
        return True
    if not done:
        return False
    ended = mrp.over_at(over if over is not None else row)
    if ended is None or ended >= since(cog):
        return False
    before = await public_text(cog.bot, guild, marathon, row, people=people, present=True)
    return mp.says(content, before, done=False)


def mentions_for(roles: list[int]) -> discord.AllowedMentions:
    if not roles:
        return discord.AllowedMentions.none()
    return discord.AllowedMentions(
        everyone=False, users=False, roles=[discord.Object(one) for one in roles]
    )


async def send_public(
    bot: Any, guild: Any, text: str, roles: list[int], *, home: int | None = None
) -> tuple[Any, int | None, str | None]:
    """On: the public channel (or `home`). Shadow: its rehearsal home, with the note naming it."""
    mode = mode_of(bot, guild.id)
    if mode == MODE_OFF:
        return (None, None, MODE_IS_OFF)
    home = home if home is not None else public_channel(bot, guild.id)
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
    body = text if mode == MODE_ON else shadowed(bot, guild, text, home)
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
    people = people_for(bot, guild, marathon, row)
    base = details_of(marathon, row) | {"auto": auto, "via": via}
    if not people and mt.is_ours(row):
        await log_action(
            bot,
            guild,
            kind_via("marathon.public_highlight_failed", via),
            actor=actor,
            details=base | {"step": "post", "reason": NOBODY},
        )
        return (NOBODY, None)
    text = await public_text(bot, guild, marathon, row, people=people or None)
    shadow = mode_of(bot, guild.id) != MODE_ON
    if mp.message_id(row) and mp.is_removed(row):
        wanted = (
            shadow_home.channel_id(bot, guild, feature=mp.SHADOW_FEATURE)
            if shadow
            else public_channel(bot, guild.id)
        )
        if wanted is not None and mp.channel_of(row) == int(wanted):
            message, _lost = await fetch_public(bot, guild, row)
            if message is not None and await edit_public(bot, guild, message, text) is None:
                await update_run(
                    bot.db, row["id"], public_removed=0, **{ma.NAMED: ma.dump_named(people)}
                )
                public_cache(cog, marathon["id"])[int(row["id"])] = (int(wanted), text)
                await log_action(
                    bot,
                    guild,
                    kind_via("marathon.public_highlight_restored", via),
                    actor=actor,
                    details=base | {"message_id": str(message.id)} | rehearsal_of(bot, guild),
                )
                return (None, int(wanted))
    roles = [] if mp.is_done(row) else await cog._ping_roles(guild, marathon, row)
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
        **{ma.NAMED: ma.dump_named(people)},
    )
    public_cache(cog, marathon["id"])[int(row["id"])] = (int(channel_id), text)
    await log_action(
        bot,
        guild,
        kind_via(
            (
                "marathon.would_post_public_highlight"
                if shadow
                else "marathon.public_highlight_posted"
            ),
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
    cog: Any,
    guild: Any,
    marathon: Any,
    row: Any,
    *,
    actor: Any = None,
    via: str = VIA_DISCORD,
    because: str | None = None,
    moved: Any = (),
) -> None:
    """The decision is stored first; the edit to the key sentence is cosmetic and may fail. The
    line names who the post named."""
    bot = cog.bot
    was = named_on(row)
    because = because or why_down(bot, guild, marathon, row, was, moved)
    await update_run(bot.db, row["id"], public_removed=1)
    public_cache(cog, marathon["id"]).pop(int(row["id"]), None)
    message, _lost = await fetch_public(bot, guild, row)
    edited = False
    if message is not None:
        why = await edit_public(
            bot,
            guild,
            message,
            await public_text(bot, guild, marathon, row, removed=True, people=written(was)),
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
        | {
            "message_id": str(mp.message_id(row)),
            "edited": edited,
            "via": via,
            "because": because,
        },
    )


async def sync_highlights(cog: Any, guild: Any, marathon: Any) -> None:
    """Every highlight that is up follows its run; unchanged costs no Discord call. One that
    names nobody any more is taken down while its run is not over, and left as it stands after."""
    bot = cog.bot
    if marathon is None:
        return
    rows = [one for one in await runs_of(bot.db, marathon["id"]) if mp.is_up(one)]
    cache = public_cache(cog, marathon["id"])
    since(cog)
    for row in rows:
        key = int(row["id"])
        was = named_on(row)
        people = people_for(bot, guild, marathon, row, standing=True, recorded=was) or None
        if people is None and (was or mt.is_ours(row)):
            if not mp.is_done(row):
                await remove_highlight(cog, guild, marathon, row)
            continue
        if people is not None and ma.as_named(people) != was:
            await update_run(bot.db, key, **{ma.NAMED: ma.dump_named(people)})
        text = await public_text(bot, guild, marathon, row, people=people)
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
        if await stands(cog, guild, marathon, row, message, text, people=people):
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
    """The moment a run's shoutout fires: posted when someone on the run is announced, never
    again once staff took it down. A failure here never breaks the shoutout."""
    try:
        if not mi.is_tracked(marathon) or not mp.auto_wanted(row):
            return
        if mode_of(cog.bot, guild.id) == MODE_OFF or public_channel(cog.bot, guild.id) is None:
            return
        if not people_for(cog.bot, guild, marathon, row):
            return
        await post_highlight(cog, guild, marathon, row, auto=True)
    except Exception as exc:
        log.warning("marathon: the auto-highlight failed — %s", reason_of(exc))


async def press(*_: Any, **__: Any) -> Outcome:
    """The retired whole-marathon button on an old run post: it answers in words."""
    return refusal(WHOLE_MARATHON_GONE, GONE_CODE, 410)


async def put_back(
    cog: Any, guild: Any, marathon: Any, row: Any, *, actor: Any = None, via: str = VIA_DISCORD
) -> bool:
    """A highlight taken down comes back IN PLACE — an edit, never a new post."""
    bot = cog.bot
    message, _lost = await fetch_public(bot, guild, row)
    if message is None:
        return False
    people = people_for(bot, guild, marathon, row)
    if not people:
        return False
    text = await public_text(bot, guild, marathon, row, people=people)
    if await edit_public(bot, guild, message, text) is not None:
        return False
    await update_run(bot.db, row["id"], public_removed=0, **{ma.NAMED: ma.dump_named(people)})
    public_cache(cog, marathon["id"])[int(row["id"])] = (mp.channel_of(row), text)
    await log_action(
        bot,
        guild,
        kind_via("marathon.public_highlight_restored", via),
        actor=actor,
        details=details_of(marathon, row)
        | {"message_id": str(message.id), "via": via, "because": "opted_in"}
        | rehearsal_of(bot, guild),
    )
    return True


async def follow_opt(
    cog: Any, guild: Any, marathon: Any, user_ids: Any, *, actor: Any, via: str
) -> None:
    """After an answer changed: a highlight that names nobody any more is taken down, one
    that still names someone is rewritten in place, and one that was taken down comes back in
    place while its run is not over and the marathon still announces. Only the people the move
    was aimed at are weighed afresh."""
    bot = cog.bot
    wanted = {int(one) for one in user_ids}
    changed = False
    for row in await runs_of(bot.db, marathon["id"]):
        was = named_on(row)
        on = set(mt.member_ids(row)) | set(ma.ids_of(was) or ())
        if not mp.message_id(row) or not wanted & on:
            continue
        still = people_for(bot, guild, marathon, row, standing=True, recorded=was, moved=wanted)
        if mp.is_up(row) and not still:
            await remove_highlight(cog, guild, marathon, row, actor=actor, via=via, moved=wanted)
        elif mp.is_up(row):
            await update_run(bot.db, row["id"], **{ma.NAMED: ma.dump_named(still)})
            changed = True
        elif (
            mp.is_removed(row)
            and row["state"] in (mt.UPCOMING, mt.LIVE)
            and people_for(bot, guild, marathon, row)
        ):
            await put_back(cog, guild, marathon, row, actor=actor, via=via)
    if changed:
        await sync_highlights(cog, guild, marathon)


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
                    discord.ButtonStyle.primary
                    if mp.move_of(to) == mp.OPT_IN
                    else discord.ButtonStyle.secondary
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


async def gated(interaction: discord.Interaction) -> bool:
    """A press on a run's post: the test guard, staff re-checked, the database up."""
    bot = interaction.client
    guard = getattr(bot, "guard", None)
    if guard is not None and not guard.allows_channel(interaction.channel_id):
        await answer(interaction, guard.refusal_message())
        return False
    if not await still_staff(interaction):
        return False
    if not bot.db.is_connected:
        await answer(interaction, DB_UNAVAILABLE)
        return False
    await interaction.response.defer(ephemeral=True)
    return True


class AnnounceButton(
    SafeDynamicItem, discord.ui.DynamicItem[discord.ui.Button], template=ma.MOVE_TEMPLATE
):
    def __init__(
        self,
        marathon_id: int,
        run_id: int,
        user_id: int,
        to: str,
        label: str | None = None,
        row: int | None = None,
    ) -> None:
        self.marathon_id = int(marathon_id)
        self.run_id = int(run_id)
        self.user_id = int(user_id)
        self.to = to
        super().__init__(
            discord.ui.Button(
                label=ma.label(label or to),
                style=discord.ButtonStyle.secondary,
                custom_id=ma.MOVE_ID.format(
                    marathon_id=int(marathon_id), run_id=int(run_id), user_id=int(user_id), to=to
                ),
                row=row,
            )
        )

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: Any, match: re.Match):
        return cls(
            int(match["marathon_id"]), int(match["run_id"]), int(match["user_id"]), match["to"]
        )

    async def on_click(self, interaction: discord.Interaction) -> None:
        from .marathon_announce import press as person_press

        if not await gated(interaction):
            return
        outcome = await person_press(
            interaction.client,
            interaction.guild,
            interaction.user,
            self.marathon_id,
            self.run_id,
            self.user_id,
            self.to,
        )
        await answer(interaction, outcome.message)


class AnnouncePick(
    SafeDynamicItem, discord.ui.DynamicItem[discord.ui.Select], template=ma.PICK_TEMPLATE
):
    def __init__(
        self,
        marathon_id: int,
        run_id: int,
        placeholder: str | None = None,
        options: Any = (),
        page: Any = "",
        row: int = 1,
    ) -> None:
        self.marathon_id = int(marathon_id)
        self.run_id = int(run_id)
        super().__init__(
            discord.ui.Select(
                placeholder=ma.label(placeholder, ma.OPTION_LABEL_LIMIT),
                options=[discord.SelectOption(label=said, value=value) for value, said in options],
                custom_id=ma.PICK_ID.format(
                    marathon_id=int(marathon_id), run_id=int(run_id), page=page or ""
                ),
                row=row,
            )
        )

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: Any, match: re.Match):
        return cls(int(match["marathon_id"]), int(match["run_id"]), page=match["page"])

    async def on_click(self, interaction: discord.Interaction) -> None:
        from .marathon_announce import press as person_press

        if not await gated(interaction):
            return
        found = ma.option_of((self.item.values or [None])[0])
        if found is None:
            await answer(interaction, ma.BAD_RUN)
            return
        outcome = await person_press(
            interaction.client,
            interaction.guild,
            interaction.user,
            self.marathon_id,
            self.run_id,
            found[0],
            found[1],
        )
        await answer(interaction, outcome.message)


__all__ = [
    "AnnounceButton",
    "AnnouncePick",
    "HighlightButton",
    "auto_highlight",
    "button_of",
    "follow_opt",
    "named_on",
    "people_for",
    "post_highlight",
    "public_text",
    "press",
    "public_channel",
    "put_back",
    "send_public",
    "remove_highlight",
    "since",
    "stands",
    "sync_highlights",
    "view_of",
]
