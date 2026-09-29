"""Runner/Host announcements: whether a marathon posts its BaF people publicly, and who is
opted out of it."""

from __future__ import annotations

from typing import Any

from ... import marathon as mt
from ... import marathon_announce as ma
from ...actionlog import log_action
from ...logkinds import VIA_DISCORD, kind_via
from ...panels import Outcome, refusal
from ...settings_store import (
    MARATHON_ANNOUNCE_OPTED_IN_SAID_KEY,
    MARATHON_ANNOUNCE_OPTED_OUT_SAID_KEY,
    MARATHON_ANNOUNCEMENTS_DEFAULT_KEY,
)
from .marathon import NO_SUCH, cog_of, get_marathon, runs_of, said_default, update_marathon


def announces(bot: Any, guild_id: int, marathon: Any) -> bool:
    return ma.announces(marathon, bot.store.get(guild_id, MARATHON_ANNOUNCEMENTS_DEFAULT_KEY))


def words(bot: Any, guild_id: int, key: str, **fields: Any) -> str:
    return mt.render(bot.store.get(guild_id, key), said_default(key), **fields).text


def display_name(guild: Any, user_id: int, fallback: str) -> str:
    getter = getattr(guild, "get_member", None)
    member = getter(int(user_id)) if getter is not None else None
    return str(getattr(member, "display_name", "") or fallback)


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
    from .marathon_host_highlights import follow_opt as hosts_follow
    from .marathon_public import follow_opt as runners_follow

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
            await runners_follow(cog, guild, fresh, ids, actor=actor, via=via)
            await hosts_follow(cog, guild, fresh, ids, actor=actor, via=via)
        await cog.sync_board(guild, fresh)
    names = ", ".join(display_name(guild, one, known[one]) for one in ids)
    key = MARATHON_ANNOUNCE_OPTED_OUT_SAID_KEY if wanted else MARATHON_ANNOUNCE_OPTED_IN_SAID_KEY
    return Outcome(True, words(bot, guild.id, key, name=names, marathon=fresh["name"]))


__all__ = ["announces", "baf_people", "set_opt_out"]
