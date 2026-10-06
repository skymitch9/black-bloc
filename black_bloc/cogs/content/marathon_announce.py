"""BaF announcements: whether a marathon posts its BaF people publicly, who is opted out of
it, each run's own answer and who is written without an @."""

from __future__ import annotations

from typing import Any

import discord

from ... import marathon as mt
from ... import marathon_announce as ma
from ...actionlog import log_action
from ...logkinds import VIA_DISCORD, kind_via
from ...panels import Outcome, refusal
from ...settings_store import (
    MARATHON_ANNOUNCE_BUTTON_MENTION_KEY,
    MARATHON_ANNOUNCE_BUTTON_PLAIN_KEY,
    MARATHON_ANNOUNCE_BUTTON_RUN_DEFAULT_KEY,
    MARATHON_ANNOUNCE_BUTTON_RUN_IN_KEY,
    MARATHON_ANNOUNCE_BUTTON_RUN_OUT_KEY,
    MARATHON_ANNOUNCE_OPTED_IN_SAID_KEY,
    MARATHON_ANNOUNCE_OPTED_OUT_SAID_KEY,
    MARATHON_ANNOUNCE_PICK_KEY,
    MARATHON_ANNOUNCE_RUN_DEFAULT_SAID_KEY,
    MARATHON_ANNOUNCE_RUN_IN_SAID_KEY,
    MARATHON_ANNOUNCE_RUN_OUT_SAID_KEY,
    MARATHON_ANNOUNCE_STATE_LINE_KEY,
    MARATHON_ANNOUNCE_STATE_NO_KEY,
    MARATHON_ANNOUNCE_STATE_PLAIN_KEY,
    MARATHON_ANNOUNCE_STATE_YES_KEY,
    MARATHON_ANNOUNCE_WHY_DEFAULT_KEY,
    MARATHON_ANNOUNCE_WHY_HOSTS_OFF_KEY,
    MARATHON_ANNOUNCE_WHY_MARATHON_KEY,
    MARATHON_ANNOUNCE_WHY_OFF_KEY,
    MARATHON_ANNOUNCE_WHY_RUN_KEY,
    MARATHON_ANNOUNCEMENTS_DEFAULT_KEY,
    MARATHON_HOST_ANNOUNCEMENTS_DEFAULT_KEY,
    MARATHON_MENTION_ON_SAID_KEY,
    MARATHON_MENTION_PEOPLE_KEY,
    MARATHON_MENTION_PLAIN_SAID_KEY,
)
from .marathon import (
    NO_SUCH,
    NO_SUCH_RUN_CODE,
    cog_of,
    get_marathon,
    run_by_id,
    runs_of,
    said_default,
    update_marathon,
    update_run,
)

LABEL_KEYS = {
    ma.IN: MARATHON_ANNOUNCE_BUTTON_RUN_IN_KEY,
    ma.OUT: MARATHON_ANNOUNCE_BUTTON_RUN_OUT_KEY,
    ma.DEFAULT: MARATHON_ANNOUNCE_BUTTON_RUN_DEFAULT_KEY,
    ma.PLAIN: MARATHON_ANNOUNCE_BUTTON_PLAIN_KEY,
    ma.MENTION: MARATHON_ANNOUNCE_BUTTON_MENTION_KEY,
}
STATE_KEYS = {
    "line": MARATHON_ANNOUNCE_STATE_LINE_KEY,
    "yes": MARATHON_ANNOUNCE_STATE_YES_KEY,
    "no": MARATHON_ANNOUNCE_STATE_NO_KEY,
    ma.PLAIN: MARATHON_ANNOUNCE_STATE_PLAIN_KEY,
    ma.WHY_DEFAULT: MARATHON_ANNOUNCE_WHY_DEFAULT_KEY,
    ma.WHY_RUN: MARATHON_ANNOUNCE_WHY_RUN_KEY,
    ma.WHY_MARATHON: MARATHON_ANNOUNCE_WHY_MARATHON_KEY,
    ma.WHY_OFF: MARATHON_ANNOUNCE_WHY_OFF_KEY,
    ma.WHY_HOSTS_OFF: MARATHON_ANNOUNCE_WHY_HOSTS_OFF_KEY,
}
RUN_SAID = {
    ma.IN: MARATHON_ANNOUNCE_RUN_IN_SAID_KEY,
    ma.OUT: MARATHON_ANNOUNCE_RUN_OUT_SAID_KEY,
    None: MARATHON_ANNOUNCE_RUN_DEFAULT_SAID_KEY,
}
MENTION_SAID = {
    ma.PLAIN: MARATHON_MENTION_PLAIN_SAID_KEY,
    ma.MENTION: MARATHON_MENTION_ON_SAID_KEY,
}


def announces(bot: Any, guild_id: int, marathon: Any) -> bool:
    return ma.announces(marathon, bot.store.get(guild_id, MARATHON_ANNOUNCEMENTS_DEFAULT_KEY))


def policy_of(bot: Any, guild_id: int, marathon: Any, *, standing: bool = False) -> ma.Policy:
    found = ma.policy(
        marathon,
        master_default=bot.store.get(guild_id, MARATHON_ANNOUNCEMENTS_DEFAULT_KEY),
        hosts_default=bot.store.get(guild_id, MARATHON_HOST_ANNOUNCEMENTS_DEFAULT_KEY),
        mention_default=bot.store.get(guild_id, MARATHON_MENTION_PEOPLE_KEY),
    )
    return ma.standing(found) if standing else found


def words(bot: Any, guild_id: int, key: str, **fields: Any) -> str:
    return mt.render(bot.store.get(guild_id, key), said_default(key), **fields).text


def display_name(guild: Any, user_id: int, fallback: str) -> str:
    getter = getattr(guild, "get_member", None)
    member = getter(int(user_id)) if getter is not None else None
    return str(getattr(member, "display_name", "") or fallback)


def plain_name(guild: Any, person: dict[str, Any]) -> str:
    """A person's server name as plain text: no markdown, no mention."""
    name = display_name(guild, person["user_id"], str(person.get("name") or person["user_id"]))
    return discord.utils.escape_mentions(discord.utils.escape_markdown(name))


def named(guild: Any, found: ma.Policy, people: Any) -> list[dict[str, Any]]:
    """The people as a public post writes them: `plain` on whoever is written without an @."""
    return [
        dict(one) | {"plain": plain_name(guild, one)} if found.plain(one["user_id"]) else dict(one)
        for one in people or ()
    ]


def people_for(
    bot: Any,
    guild: Any,
    marathon: Any,
    row: Any,
    *,
    standing: bool = False,
    carried: bool = True,
) -> list[dict[str, Any]]:
    """Everyone of ours a run's public post names. `standing` is a post already up: the master
    going off never empties it, and (`carried`) neither does the host default going off."""
    found = policy_of(bot, guild.id, marathon, standing=standing)
    people = ma.run_people(row, found)
    if standing and carried and not people:
        people = ma.run_people(row, found._replace(hosts_on=True))
    return named(guild, found, people)


def speaking(
    bot: Any,
    guild: Any,
    marathon: Any,
    block: Any,
    *,
    standing: bool = False,
    carried: bool = True,
) -> list[dict[str, Any]]:
    """The hosts a block's public posts name; `standing` and `carried` as for a run."""
    found = policy_of(bot, guild.id, marathon, standing=standing)
    people = ma.block_people(block, found)
    if standing and carried and not people:
        people = ma.block_people(block, found._replace(hosts_on=True))
    return named(guild, found, people)


def labels_of(bot: Any, guild_id: int) -> dict[str, str]:
    return {to: str(bot.store.get(guild_id, key)) for to, key in LABEL_KEYS.items()}


def controls_of(bot: Any, guild: Any, marathon: Any, row: Any) -> tuple:
    """The per-person moves a run's post carries, as buttons or as one menu."""
    made = ma.moves(
        marathon["id"], row, policy_of(bot, guild.id, marathon), labels_of(bot, guild.id)
    )
    return ma.laid_out(marathon["id"], row, made, words(bot, guild.id, MARATHON_ANNOUNCE_PICK_KEY))


def state_lines(bot: Any, guild: Any, marathon: Any, row: Any, *, only: Any = None) -> list[str]:
    said = {name: str(bot.store.get(guild.id, key)) for name, key in STATE_KEYS.items()}
    return ma.state_lines(row, policy_of(bot, guild.id, marathon), said, only=only)


def person_state(
    bot: Any, guild: Any, marathon: Any, row: Any, user_id: Any
) -> dict[str, Any] | None:
    """One BaF person on one run as the site draws them: announced or not, why, in the state
    line's own words, and the one move their answer can take."""
    found = policy_of(bot, guild.id, marathon)
    person = next((one for one in ma.baf_on(row) if str(one["user_id"]) == str(user_id)), None)
    if person is None:
        return None
    said = ma.verdict(found, row, person["user_id"], person["role"])
    move = ma.run_move(found, row, person)
    name = str(person.get("name") or person["user_id"])
    lines = state_lines(bot, guild, marathon, row, only=person["user_id"])
    return {
        "role": person["role"],
        "answer": ma.run_answers(row).get(int(person["user_id"])),
        "announced": said.yes,
        "why": said.why,
        "said": lines[0] if lines else None,
        "move": move if ma.shown(row) else None,
        "move_label": mt.render(labels_of(bot, guild.id)[move], "{name}", name=name).text,
    }


def mention_state(bot: Any, guild: Any, marathon: Any, user_id: Any, name: str) -> dict[str, Any]:
    """How a BaF person's name is written on this marathon, and the move that changes it."""
    found = policy_of(bot, guild.id, marathon)
    plain = found.plain(user_id)
    move = ma.MENTION if plain else ma.PLAIN
    return {
        "plain": plain,
        "own": (found.mentions or {}).get(int(user_id)),
        "move": move,
        "move_label": mt.render(labels_of(bot, guild.id)[move], "{name}", name=name).text,
    }


async def baf_people(bot: Any, guild: Any, marathon: Any) -> dict[int, str]:
    """Everyone the marathon could announce: its BaF runners and its BaF hosts."""
    from .marathon_host_highlights import hosts_of

    found: dict[int, str] = {}
    for row in await runs_of(bot.db, marathon["id"]):
        for one in mt.ours(mt.people_of(row)):
            found.setdefault(int(one["user_id"]), str(one.get("name") or one["user_id"]))
    for user_id, name in (await hosts_of(bot, guild, marathon)).items():
        found.setdefault(int(user_id), name)
    return found


async def followed(cog: Any, guild: Any, marathon: Any, ids: Any, *, actor: Any, via: str) -> None:
    from .marathon_host_highlights import follow_opt as hosts_follow
    from .marathon_public import follow_opt as runners_follow

    await runners_follow(cog, guild, marathon, ids, actor=actor, via=via)
    await hosts_follow(cog, guild, marathon, ids, actor=actor, via=via)


async def set_opt_out(
    bot: Any,
    guild: Any,
    actor: Any,
    marathon: Any,
    user_ids: Any,
    out: Any,
    *,
    via: str = VIA_DISCORD,
) -> Outcome:
    """The one writer of a marathon's opt-outs: the runner post's button, the People slot view
    and the site all come here. It posts nothing; a highlight that names nobody any more is
    taken down, and one taken down comes back in place on opting back in."""
    wanted = ma.clean_opt(out)
    if wanted is None:
        return refusal(ma.BAD_OPT, ma.BAD_OPT_CODE, 422)
    cog = cog_of(bot)
    async with cog.lock(marathon["id"]):
        fresh = await get_marathon(bot.db, guild.id, marathon["id"])
        if fresh is None:
            return refusal(mt.NO_SUCH_MARATHON.format(given=marathon["id"]), NO_SUCH, 404)
        known = await baf_people(bot, guild, fresh)
        ids = [one for one in dict.fromkeys(int(one) for one in user_ids) if one in known]
        if not ids:
            return refusal(ma.NOT_BAF.format(marathon=fresh["name"]), ma.NOT_BAF_CODE, 404)
        was = ma.opted_out(fresh)
        now = ma.toggled(was, ids, wanted)
        if now != was:
            await update_marathon(bot.db, fresh["id"], **{ma.OPTED: ma.dump(now)})
            fresh = await get_marathon(bot.db, guild.id, fresh["id"])
            await log_action(
                bot,
                guild,
                kind_via(
                    "marathon.announce_opted_out" if wanted else "marathon.announce_opted_in", via
                ),
                actor=actor,
                details={
                    "marathon_id": fresh["id"],
                    "name": fresh["name"],
                    "members": ids,
                    "via": via,
                },
            )
            await followed(cog, guild, fresh, ids, actor=actor, via=via)
        await cog.sync_board(guild, fresh)
    names = ", ".join(display_name(guild, one, known[one]) for one in ids)
    key = MARATHON_ANNOUNCE_OPTED_OUT_SAID_KEY if wanted else MARATHON_ANNOUNCE_OPTED_IN_SAID_KEY
    return Outcome(True, words(bot, guild.id, key, name=names, marathon=fresh["name"]))


async def set_run_answer(
    bot: Any,
    guild: Any,
    actor: Any,
    marathon: Any,
    run_id: Any,
    user_id: Any,
    to: Any,
    *,
    via: str = VIA_DISCORD,
) -> Outcome:
    """The one writer of a run's own answer for a person: announce them for this run, do not,
    or back to the default. It posts nothing; the highlights follow as for an opt-out."""
    understood, wanted = ma.clean_run(to)
    if not understood:
        return refusal(ma.BAD_RUN, ma.BAD_RUN_CODE, 422)
    cog = cog_of(bot)
    async with cog.lock(marathon["id"]):
        fresh = await get_marathon(bot.db, guild.id, marathon["id"])
        if fresh is None:
            return refusal(mt.NO_SUCH_MARATHON.format(given=marathon["id"]), NO_SUCH, 404)
        row = await run_by_id(bot.db, fresh["id"], run_id)
        if row is None:
            return refusal(mt.NO_SUCH_RUN.format(name=fresh["name"]), NO_SUCH_RUN_CODE, 404)
        person = next(
            (one for one in ma.baf_on(row) if str(one["user_id"]) == str(user_id).strip()), None
        )
        if person is None:
            return refusal(ma.NOT_ON_RUN.format(game=row["game"]), ma.NOT_ON_RUN_CODE, 404)
        member = int(person["user_id"])
        answers = ma.run_answers(row)
        was = answers.get(member)
        if was != wanted:
            await update_run(
                bot.db,
                row["id"],
                **{ma.RUN_ANSWERS: ma.dump_answers(ma.answered(answers, member, wanted))},
            )
            await log_action(
                bot,
                guild,
                kind_via("marathon.announce_run_set", via),
                actor=actor,
                target=member,
                details={
                    "marathon_id": fresh["id"],
                    "name": fresh["name"],
                    "run_id": row["id"],
                    "game": row["game"],
                    "member": member,
                    "from": was or ma.DEFAULT,
                    "to": wanted or ma.DEFAULT,
                    "via": via,
                },
            )
            await followed(cog, guild, fresh, [member], actor=actor, via=via)
        await cog.sync_board(guild, fresh)
    name = display_name(guild, member, str(person.get("name") or member))
    return Outcome(
        True,
        words(bot, guild.id, RUN_SAID[wanted], name=name, game=row["game"], marathon=fresh["name"]),
    )


async def set_mention(
    bot: Any,
    guild: Any,
    actor: Any,
    marathon: Any,
    user_id: Any,
    to: Any,
    *,
    via: str = VIA_DISCORD,
) -> Outcome:
    """The one writer of how a person's name is written in a marathon's public posts: as an @,
    or as plain text. Posts already up are rewritten in place; nothing new is posted."""
    from .marathon_host_highlights import sync_host_highlights
    from .marathon_public import sync_highlights
    from .marathon_reminder_posts import sync_reminders

    wanted = ma.clean_mention(to)
    if wanted is None:
        return refusal(ma.BAD_MENTION, ma.BAD_MENTION_CODE, 422)
    cog = cog_of(bot)
    async with cog.lock(marathon["id"]):
        fresh = await get_marathon(bot.db, guild.id, marathon["id"])
        if fresh is None:
            return refusal(mt.NO_SUCH_MARATHON.format(given=marathon["id"]), NO_SUCH, 404)
        known = await baf_people(bot, guild, fresh)
        member = next((one for one in known if str(one) == str(user_id).strip()), None)
        if member is None:
            return refusal(ma.NOT_BAF.format(marathon=fresh["name"]), ma.NOT_BAF_CODE, 404)
        found = policy_of(bot, guild.id, fresh)
        was = ma.PLAIN if found.plain(member) else ma.MENTION
        stored = ma.answered(
            ma.mentions(fresh), member, ma.mention_stored(wanted, found.mention_default)
        )
        if stored != ma.mentions(fresh):
            await update_marathon(bot.db, fresh["id"], **{ma.MENTIONS: ma.dump_answers(stored)})
            fresh = await get_marathon(bot.db, guild.id, fresh["id"])
        if was != wanted:
            await log_action(
                bot,
                guild,
                kind_via("marathon.mention_set", via),
                actor=actor,
                target=member,
                details={
                    "marathon_id": fresh["id"],
                    "name": fresh["name"],
                    "member": member,
                    "from": was,
                    "to": wanted,
                    "via": via,
                },
            )
            await sync_highlights(cog, guild, fresh)
            await sync_host_highlights(cog, guild, fresh)
            await sync_reminders(cog, guild, fresh)
        await cog.sync_board(guild, fresh)
    name = display_name(guild, member, known[member])
    return Outcome(
        True, words(bot, guild.id, MENTION_SAID[wanted], name=name, marathon=fresh["name"])
    )


async def press(
    bot: Any,
    guild: Any,
    actor: Any,
    marathon_id: Any,
    run_id: Any,
    user_id: Any,
    to: str,
    *,
    via: str = VIA_DISCORD,
) -> Outcome:
    """A per-person move from a run's post: the run's own answer, or the person's @."""
    marathon = await get_marathon(bot.db, guild.id, marathon_id)
    if marathon is None or cog_of(bot) is None:
        return refusal(mt.NO_SUCH_MARATHON.format(given=marathon_id), NO_SUCH, 404)
    if to in (ma.PLAIN, ma.MENTION):
        return await set_mention(bot, guild, actor, marathon, user_id, to, via=via)
    return await set_run_answer(bot, guild, actor, marathon, run_id, user_id, to, via=via)


__all__ = [
    "announces",
    "baf_people",
    "controls_of",
    "mention_state",
    "people_for",
    "person_state",
    "policy_of",
    "press",
    "set_mention",
    "set_opt_out",
    "set_run_answer",
    "speaking",
    "state_lines",
]
