from __future__ import annotations

import importlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import discord

from .selftest import Check, CheckFailed, Run
from .settings_store import GOLIVE_LIVE_AUTHOR_KEY

MEMBER = "member"
GUILD = "guild"
HOME = "home"
MOD = "mod"
MODMAIL = "modmail"

NO_COG = "the {name} cog is not loaded, so its panel cannot be built"
NOT_A_CARD = "{name} did not build an embed and a view"
POSTED = "posted; {buttons} button(s), {selects} select(s)"
SENT = "posted; {what}"

SELFTEST_MARK = "Black Bloc self-test"
SELFTEST_NOTE = "A self-test card. It is deleted again in a few minutes."


@dataclass(frozen=True)
class PanelDoor:
    command: str
    feature: str
    module: str
    builder: str
    shape: str = MEMBER


PANELS: tuple[PanelDoor, ...] = (
    PanelDoor("settings", "core", "black_bloc.cogs.core", "build_root"),
    PanelDoor("automod", "automod", "black_bloc.cogs.moderation.automod", "build_root", GUILD),
    PanelDoor("honeypot", "honeypot", "black_bloc.cogs.moderation.honeypot", "build_root", GUILD),
    PanelDoor("mod", "mod", "black_bloc.cogs.moderation.modcmds", "build_root", MOD),
    PanelDoor("modmail", "modmail", "black_bloc.cogs.moderation.modmail", "build_root", MODMAIL),
    PanelDoor("event", "events", "black_bloc.cogs.community.events", "build_panel"),
    PanelDoor("poll", "poll", "black_bloc.cogs.community.polls", "build_panel"),
    PanelDoor("birthday", "birthday", "black_bloc.cogs.community.birthdays", "build_panel"),
    PanelDoor("rolemenu", "rolemenu", "black_bloc.cogs.community.role_menus", "build_panel"),
    PanelDoor("voice", "tempvoice", "black_bloc.cogs.community.tempvoice", "build_panel"),
    PanelDoor("request", "request", "black_bloc.cogs.community.requests", "build_panel"),
    PanelDoor("ask", "modmail", "black_bloc.cogs.community.frontdoor", "build_panel"),
    PanelDoor("apply", "applications", "black_bloc.cogs.community.applications", "build_panel"),
    PanelDoor("chat", "chat", "black_bloc.cogs.content.chat", "build_panel"),
    PanelDoor("memory", "chat", "black_bloc.cogs.content.chat_memory", "build_panel", HOME),
    PanelDoor("golive", "golive", "black_bloc.cogs.content.golive", "build_panel"),
    PanelDoor("youtube", "youtube", "black_bloc.cogs.content.youtube", "build_panel"),
    PanelDoor("pings", "pings", "black_bloc.cogs.content.pings", "build_panel"),
    PanelDoor("raidtrain", "raidtrain", "black_bloc.cogs.content.raidtrain", "build_panel"),
    PanelDoor("marathon", "marathon", "black_bloc.cogs.content.marathon", "build_panel"),
)


def panel_actor(one: Run) -> Any:
    """The member a card is built for: whoever asked, and the bot itself at boot."""
    wanted = getattr(one.actor, "id", None)
    found = one.guild.get_member(int(wanted)) if wanted else None
    return found or getattr(one.guild, "me", None) or one.actor


def counted(view: Any) -> dict[str, int]:
    children = list(getattr(view, "children", ()) or ())
    selects = sum(1 for item in children if isinstance(item, discord.ui.Select))
    return {"buttons": len(children) - selects, "selects": selects}


async def built(one: Run, door: PanelDoor) -> tuple[Any, Any]:
    """The SAME function the command handler calls — never a copy of what it does."""
    module = importlib.import_module(door.module)
    builder = getattr(module, door.builder)
    actor = panel_actor(one)
    if door.shape == GUILD:
        found = builder(one.bot, one.guild)
    elif door.shape == HOME:
        found = builder(one.bot, one.guild.id, actor)
    elif door.shape == MOD:
        found = builder(one.bot, one.guild, page=1, user_id=None)
    elif door.shape == MODMAIL:
        cog = one.bot.get_cog("Modmail")
        if cog is None:
            raise CheckFailed(NO_COG.format(name="Modmail"))
        found = builder(one.bot, one.guild, cog, actor=actor, staff=True)
    else:
        found = builder(one.bot, one.guild, actor)
    if hasattr(found, "__await__"):
        found = await found
    if not isinstance(found, tuple) or len(found) != 2:
        raise CheckFailed(NOT_A_CARD.format(name=door.builder))
    return found


def panel_check(door: PanelDoor) -> Check:
    async def run(one: Run) -> str:
        embed, view = await built(one, door)
        await one.post(embed=embed, view=view)
        return POSTED.format(**counted(view))

    return Check(f"panel.{door.command}", door.feature, run)


def panel_checks() -> tuple[Check, ...]:
    return tuple(panel_check(door) for door in PANELS)


# --- the senders ----------------------------------------------------------------------------------


def _member(one: Run) -> Any:
    return panel_actor(one)


def _name(member: Any) -> str:
    return str(getattr(member, "display_name", None) or getattr(member, "name", None) or "someone")


async def send_golive(one: Run) -> str:
    from . import golive

    info = golive.StreamInfo(
        url="https://twitch.tv/blackbloc",
        game=SELFTEST_MARK,
        title=SELFTEST_NOTE,
        platform="twitch",
    )
    member = _member(one)
    store = one.bot.store
    text = golive.render(store.get(one.guild.id, "golive_template"), info, member)
    await one.post(
        content=text,
        embed=golive.announcement_embed(
            info, member, "presence", author=store.get(one.guild.id, GOLIVE_LIVE_AUTHOR_KEY)
        ),
    )
    return SENT.format(what="the go-live card, with its sentence")


async def send_birthday(one: Run) -> str:
    from . import birthdays

    store = one.bot.store
    text = birthdays.render_description(
        store.get(one.guild.id, "birthday_template"), _name(_member(one)), None
    )
    colour = discord.Colour(birthdays.parse_color(store.get(one.guild.id, "birthday_color")))
    await one.post(embed=discord.Embed(description=text, colour=colour))
    return SENT.format(what="the birthday card")


async def send_events(one: Run) -> str:
    from . import events

    starts = datetime.now(UTC) + timedelta(hours=1)
    card = events.build_card(
        event_id=0,
        title=SELFTEST_MARK,
        requester_id=int(getattr(_member(one), "id", 0) or 0),
        starts_at=starts,
        minutes=60,
        where=events.Where(events.WHERE_OTHER, None, SELFTEST_NOTE),
        description=SELFTEST_NOTE,
    )
    text = events.announce_text(one.bot.store.get(one.guild.id, "events_ping_role_id"))
    await one.post(content=text, embed=card)
    return SENT.format(what="the event card and its announcement line")


async def send_pings(one: Run) -> str:
    """Ping roles never post a card of their own; what they contribute is the prefix."""
    from . import pings
    from .golive import ping_prefix

    store = one.bot.store
    events_role = pings.named_role(
        one.guild, store.get(one.guild.id, "pings_events_role_name")
    )
    wanted = [
        store.get(one.guild.id, "golive_ping_role_id"),
        getattr(events_role, "id", None),
    ]
    prefix = ping_prefix(*wanted)
    named = len([one_id for one_id in wanted if one_id])
    await one.post(content=f"{prefix}{SELFTEST_MARK} — {SELFTEST_NOTE}")
    return SENT.format(what=f"the ping prefix for {named} role(s)")


async def send_raidtrain(one: Run) -> str:
    from . import raidtrain

    starts = datetime.now(UTC) + timedelta(days=1)
    train = {
        "id": 0,
        "title": SELFTEST_MARK,
        "description": SELFTEST_NOTE,
        "starts_at": starts.isoformat(),
        "slot_minutes": 60,
        "status": raidtrain.OPEN,
        "cancel_reason": None,
    }
    slots = [
        {
            "id": 0,
            "position": 1,
            "user_id": None,
            "starts_at": starts.isoformat(),
            "twitch_login": None,
            "checked_in_at": None,
        }
    ]
    text = raidtrain.render_lineup(
        train, slots, ping_role_id=one.bot.store.get(one.guild.id, "raidtrain_ping_role_id")
    )
    await one.post(content=text)
    return SENT.format(what="the lineup post")


SENDERS: tuple[tuple[str, str, Any], ...] = (
    ("golive", "golive", send_golive),
    ("birthday", "birthday", send_birthday),
    ("events", "events", send_events),
    ("pings", "pings", send_pings),
    ("raidtrain", "raidtrain", send_raidtrain),
)


def send_checks() -> tuple[Check, ...]:
    return tuple(Check(f"send.{name}", feature, body) for name, feature, body in SENDERS)


__all__ = [
    "PANELS",
    "SENDERS",
    "PanelDoor",
    "built",
    "counted",
    "panel_actor",
    "panel_checks",
    "send_checks",
]
