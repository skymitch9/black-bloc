from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import discord

from . import pings
from .actionlog import log_action
from .cogs.community.role_menus import get_menu
from .logkinds import VIA_DISCORD, kind_via

log = logging.getLogger(__name__)

COMMUNITY = "COMMUNITY"
STREAMER_PROMPT_TITLE = "Which streamers?"
REASON = "Black Bloc pings onboarding"

SYNCED = "pings.onboarding_synced"
FAILED = "pings.onboarding_failed"
TOOK_OVER = "pings.onboarding_took_over"

NO_COMMUNITY = (
    "This server is not a Community server yet, so Discord has no onboarding screen to put "
    "anything on and nothing was changed. Turn Community on in **Server Settings ▸ Enable "
    "Community** first; until then the *Notifications* role menu is how members opt in."
)
NOT_MANAGED = (
    "Black Bloc is not managing this server's onboarding, so nothing was changed. **Manage "
    "onboarding again** on this panel turns it back on."
)
NOTHING_TO_SAY = (
    "There is nothing to put on the onboarding screen yet — staff have not set up the Events "
    "role or the raid-train role, and nobody has a ping role. Black Bloc left the prompts alone."
)
UNCHANGED = "Discord's onboarding screen already says exactly this, so nothing was written."
WROTE = "Done — Discord's onboarding screen now carries {prompts}. {what}"
WROTE_CAPPED = " **{more}** more streamer(s) are on `/pings` rather than the screen."
REFUSED = (
    "Discord refused the onboarding write, so nothing was changed: {why}. Black Bloc needs "
    "**Manage Server** and **Manage Roles**, and Discord will not take a prompt with no options "
    "on it. Nothing else about your pings changed."
)
CARD_MANAGED = (
    "Black Bloc keeps **{count}** onboarding prompt(s) in step with the ping roles. It never "
    "touches a prompt it did not make, and it never turns onboarding itself on or off."
)
CARD_NOT_MANAGED = (
    "Black Bloc is **not** managing this server's onboarding. The prompts are exactly as "
    "somebody left them and Black Bloc will not write to them."
)
CARD_NO_COMMUNITY = (
    "This server is not a Community server, so there is no onboarding screen. The "
    "*Notifications* role menu is the fallback until there is."
)
CARD_PROMPT = "**{title}** — {options}"
CARD_NO_OPTIONS = "nothing to offer yet"
CARD_LAST_SYNC = "Last written: {when}"
CARD_NEVER_SYNCED = "Black Bloc has not written to onboarding yet."
CARD_FOREIGN = (
    "**{count}** prompt(s) here belong to somebody else and are left exactly as they are."
)

EVENTS_OPTION = "Events"
GOLIVE_OPTION = "Go-lives"
BOTH_OPTION = "Events and go-lives"
RAID_OPTION = "Raid trains"
EVENTS_DESCRIPTION = "Get pinged when something is happening here"
GOLIVE_DESCRIPTION = "Get pinged when somebody goes live"
BOTH_DESCRIPTION = "Get pinged for events and when somebody goes live"
RAID_DESCRIPTION = "Get pinged when a raid train moves"
STREAMER_DESCRIPTION = "Get pinged when they go live"

FEED_OPTIONS = {
    pings.BOTH_FEEDS: (BOTH_OPTION, BOTH_DESCRIPTION),
    pings.GOLIVE_FEED: (GOLIVE_OPTION, GOLIVE_DESCRIPTION),
    pings.EVENTS_FEED: (EVENTS_OPTION, EVENTS_DESCRIPTION),
    pings.RAID_FEED: (RAID_OPTION, RAID_DESCRIPTION),
}

SKIPPED = "skipped"
NO_COMMUNITY_REASON = "no_community"
NOT_MANAGED_REASON = "not_managed"
NOTHING_REASON = "nothing_to_say"
UNCHANGED_REASON = "unchanged"
WROTE_REASON = "wrote"
REFUSED_REASON = "refused"

OPTION_TITLE_LIMIT = 100
PROMPT_TITLE_LIMIT = 100


@dataclass(frozen=True)
class Wanted:
    """One prompt as Black Bloc means it — titles and role ids, never Discord objects."""

    title: str
    options: tuple[tuple[str, tuple[int, ...], str], ...]


@dataclass
class Result:
    ok: bool
    reason: str
    message: str
    wrote: bool = False
    more: int = 0
    wanted: list[Wanted] = field(default_factory=list)
    foreign: int = 0


def is_community(guild: Any) -> bool:
    return COMMUNITY in (getattr(guild, "features", None) or ())


def managed(bot: Any, guild_id: int) -> bool:
    return bool(bot.store.get(guild_id, pings.ONBOARDING_MANAGED_KEY))


def prompt_title(bot: Any, guild_id: int) -> str:
    given = str(bot.store.get(guild_id, pings.ONBOARDING_TITLE_KEY) or "").strip()
    return (given or "What should ping you?")[:PROMPT_TITLE_LIMIT]


def option_cap(bot: Any, guild_id: int) -> int:
    return max(int(bot.store.get(guild_id, pings.ONBOARDING_CAP_KEY) or 1), 1)


def our_titles(bot: Any, guild_id: int) -> tuple[str, str]:
    return (prompt_title(bot, guild_id), STREAMER_PROMPT_TITLE)


def ours(prompt: Any, titles: tuple[str, str]) -> bool:
    return str(getattr(prompt, "title", "")) in titles


def feed_options(bot: Any, guild: Any) -> tuple[tuple[str, tuple[int, ...], str], ...]:
    found = []
    for feed, role_id in pings.all_feeds(bot, guild.id):
        if not role_id or pings.role_of(guild, role_id) is None:
            continue
        label, note = FEED_OPTIONS[feed]
        found.append((label[:OPTION_TITLE_LIMIT], (int(role_id),), note))
    return tuple(found)


async def streamer_options(
    bot: Any, guild: Any
) -> tuple[tuple[tuple[str, tuple[int, ...], str], ...], int]:
    """One option per streamer who HAS a role, most-followed first, capped; and how many more."""
    counts = await pings.follower_counts(bot, guild)
    listed = {int(row["user_id"]) for row in await pings.listed_streamers(bot.db, guild.id)}
    rows = [
        row
        for row in await pings.all_fan_roles(bot.db, guild.id)
        if int(row["user_id"]) in listed and pings.role_of(guild, row["role_id"]) is not None
    ]
    rows.sort(key=lambda row: (-counts.get(int(row["user_id"]), 0), int(row["user_id"])))
    cap = option_cap(bot, guild.id)
    found = tuple(
        (
            pings.option_label(guild, row)[:OPTION_TITLE_LIMIT],
            (int(row["role_id"]),),
            STREAMER_DESCRIPTION,
        )
        for row in rows[:cap]
    )
    return (found, max(len(rows) - cap, 0))


async def wanted_prompts(bot: Any, guild: Any) -> tuple[list[Wanted], int]:
    title, streamers_title = our_titles(bot, guild.id)
    found: list[Wanted] = []
    feeds = feed_options(bot, guild)
    if feeds:
        found.append(Wanted(title, feeds))
    people, more = await streamer_options(bot, guild)
    if people:
        found.append(Wanted(streamers_title, people))
    return (found, more)


def as_shape(prompt: Any) -> Wanted:
    """A live prompt reduced to what Black Bloc decides, so the diff never sees Discord's ids."""
    return Wanted(
        str(getattr(prompt, "title", "")),
        tuple(
            (
                str(getattr(option, "title", "")),
                tuple(sorted(int(one) for one in getattr(option, "role_ids", ()) or ())),
                str(getattr(option, "description", "") or ""),
            )
            for option in getattr(prompt, "options", ()) or ()
        ),
    )


def normalised(wanted: Wanted) -> Wanted:
    return Wanted(
        wanted.title,
        tuple((title, tuple(sorted(roles)), note) for title, roles, note in wanted.options),
    )


def built(wanted: Wanted) -> discord.OnboardingPrompt:
    return discord.OnboardingPrompt(
        type=discord.OnboardingPromptType.multiple_choice,
        title=wanted.title,
        single_select=False,
        required=False,
        in_onboarding=True,
        options=[
            discord.OnboardingPromptOption(
                title=title,
                description=note or None,
                roles=[discord.Object(id=one) for one in roles],
            )
            for title, roles, note in wanted.options
        ],
    )


async def reconcile(
    bot: Any, guild: Any, *, by: int | None = None, via: str = VIA_DISCORD, asked: bool = False
) -> Result:
    """C5: read, build, and write ONLY on a diff — every foreign prompt kept as it was found.

    `asked` marks a staff **Sync now**, which answers in words even when nothing happened; the
    sweep stays silent unless it actually wrote or Discord refused.
    """
    if not managed(bot, guild.id):
        return Result(False, NOT_MANAGED_REASON, NOT_MANAGED)
    if not is_community(guild):
        return Result(False, NO_COMMUNITY_REASON, NO_COMMUNITY)
    if not getattr(bot.db, "is_connected", False):
        return Result(False, SKIPPED, NOT_MANAGED)
    wanted, more = await wanted_prompts(bot, guild)
    titles = our_titles(bot, guild.id)
    try:
        current = await guild.onboarding()
    except Exception as exc:
        return await _refused(bot, guild, exc, by=by, via=via)
    live = list(getattr(current, "prompts", ()) or [])
    foreign = [prompt for prompt in live if not ours(prompt, titles)]
    theirs = [as_shape(prompt) for prompt in live if ours(prompt, titles)]
    if not wanted:
        return Result(False, NOTHING_REASON, NOTHING_TO_SAY, foreign=len(foreign))
    if theirs == [normalised(one) for one in wanted]:
        return Result(
            True, UNCHANGED_REASON, UNCHANGED, more=more, wanted=wanted, foreign=len(foreign)
        )
    try:
        await guild.edit_onboarding(
            prompts=[*foreign, *(built(one) for one in wanted)], reason=REASON
        )
    except Exception as exc:
        return await _refused(bot, guild, exc, by=by, via=via)
    await log_action(
        bot,
        guild,
        kind_via(SYNCED, via),
        actor=by,
        details={
            "prompts": [one.title for one in wanted],
            "options": [len(one.options) for one in wanted],
            "foreign_kept": len(foreign),
            "more_on_pings": more,
            "asked": asked,
            "via": via,
        },
    )
    await take_over(bot, guild, by=by, via=via)
    said = WROTE.format(
        prompts=", ".join(f"**{one.title}**" for one in wanted),
        what=(
            f"{len(foreign)} prompt(s) that are not Black Bloc's were left exactly as they were."
            if foreign
            else "Nothing else on that screen was touched."
        ),
    )
    if more:
        said += WROTE_CAPPED.format(more=more)
    return Result(
        True, WROTE_REASON, said, wrote=True, more=more, wanted=wanted, foreign=len(foreign)
    )


async def _refused(
    bot: Any, guild: Any, exc: BaseException, *, by: int | None, via: str
) -> Result:
    why = f"{type(exc).__name__}: {exc}"
    log.warning("pings: Discord refused the onboarding write — %s", why)
    await log_action(
        bot,
        guild,
        kind_via(FAILED, via),
        actor=by,
        details={"reason": why, "via": via},
    )
    return Result(False, REFUSED_REASON, REFUSED.format(why=why[:200]))


async def take_over(bot: Any, guild: Any, *, by: int | None, via: str) -> bool:
    """Onboarding now asks the question the Notifications menu asked, so that post comes down."""
    from . import rolemenu_panels as panels

    menu = await get_menu(bot.db, guild.id, pings.NOTIFICATIONS_MENU)
    if menu is None or not menu["message_id"]:
        return False
    if not await panels.unpost(bot, menu, by):
        return False
    await log_action(
        bot,
        guild,
        kind_via(TOOK_OVER, via),
        actor=by,
        details={"menu": pings.NOTIFICATIONS_MENU, "via": via},
    )
    return True


def card_lines(guild: Any, result: Result, *, managed_now: bool, last: Any = None) -> list[str]:
    """What the staff sub-panel says: what the prompts hold, and what is NOT Black Bloc's."""
    said: list[str] = []
    if not managed_now:
        said.append(CARD_NOT_MANAGED)
    if not is_community(guild):
        said.append(CARD_NO_COMMUNITY)
    if said:
        return said
    lines = [CARD_MANAGED.format(count=len(result.wanted))]
    for one in result.wanted:
        lines.append(
            CARD_PROMPT.format(
                title=one.title,
                options=", ".join(title for title, _roles, _note in one.options)
                or CARD_NO_OPTIONS,
            )
        )
    if not result.wanted:
        lines.append(NOTHING_TO_SAY)
    if result.more:
        lines.append(WROTE_CAPPED.format(more=result.more).strip())
    if result.foreign:
        lines.append(CARD_FOREIGN.format(count=result.foreign))
    lines.append(CARD_LAST_SYNC.format(when=last) if last else CARD_NEVER_SYNCED)
    return lines


async def last_sync(bot: Any, guild_id: int) -> str | None:
    """The Logs table is the one home for when this last happened — no second timestamp key."""
    if not getattr(bot.db, "is_connected", False):
        return None
    cur = await bot.db.conn.execute(
        "SELECT at FROM action_log WHERE guild_id = ? AND kind LIKE ? ORDER BY id DESC LIMIT 1",
        (int(guild_id), f"%{SYNCED}"),
    )
    row = await cur.fetchone()
    return str(row["at"]) if row else None
