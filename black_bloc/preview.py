"""Every editable posted text, drawn by the bot's own render functions and nothing else."""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

import discord

from . import birthdays, frontdoor, minutes, modmail, polls, posts, shadow, spotlight
from . import events as ev
from . import golive as gl
from . import requests as reqs
from .settings_store import (
    GOLIVE_COSTREAM_AUTHOR_KEY,
    GOLIVE_COSTREAM_TEMPLATE_KEY,
    SPOTLIGHT_BUMP_TEMPLATE_KEY,
)

log = logging.getLogger(__name__)

GOLIVE_TEMPLATE_KEY = "golive_template"
GOLIVE_LIVE_AUTHOR_KEY = "golive_live_author"
GOLIVE_PING_ROLE_KEY = "golive_ping_role_id"
GOLIVE_END_TEMPLATE_KEY = "golive_end_template"
GOLIVE_END_AUTHOR_KEY = "golive_end_author"
GOLIVE_END_KEEP_MENTION_KEY = "golive_end_keep_mention"
BIRTHDAY_TEMPLATE_KEY = "birthday_template"
BIRTHDAY_COLOR_KEY = "birthday_color"

SAMPLE_LIMIT = 4000
OVERRIDE_LIMIT = 4000
ROW_CAP = 5

ROLE_MENTION = re.compile(r"<@&(\d+)>")
CHANNEL_MENTION = re.compile(r"<#(\d+)>")

UNKNOWN_FEATURE = (
    "Black Bloc draws no preview for **{feature}**, so nothing was shown. That is a fault in "
    "the page rather than a problem with your access — reload the dashboard, and tell a Lead if "
    "it keeps happening."
)
UNKNOWN_KEY = (
    "**{key}** is not one of the words {feature} posts, so nothing was drawn. A preview only "
    "ever shows a setting inside the message it really belongs to — edit {key} where its own "
    "feature lives, or on the Settings page."
)


class PreviewRefused(Exception):
    """A preview was asked for something it does not draw; `message` is the sentence."""

    def __init__(self, error: str, message: str) -> None:
        super().__init__(error)
        self.error = error
        self.message = message


class PreviewStore:
    """The settings store with a draft laid over it. It never writes, and never can."""

    def __init__(self, store: Any, guild_id: int, overrides: dict[str, str]) -> None:
        self._store = store
        self._guild_id = int(guild_id)
        self._overrides = dict(overrides or {})

    def get(self, guild_id: Any, key: str) -> Any:
        if int(guild_id or 0) == self._guild_id and key in self._overrides:
            return self._overrides[key]
        return self._store.get(guild_id, key)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._store, name)


class PreviewBot:
    """The bot with a `PreviewStore` in front of its own; everything else is the real one."""

    def __init__(self, bot: Any, store: PreviewStore) -> None:
        self._bot = bot
        self.store = store

    def __getattr__(self, name: str) -> Any:
        return getattr(self._bot, name)


@dataclass(frozen=True)
class Rendered:
    """Exactly what the bot would send: the text, the cards, the buttons, the pills."""

    content: str = ""
    embeds: tuple[dict[str, Any], ...] = ()
    components: tuple[tuple[dict[str, Any], ...], ...] = ()
    mentions: dict[str, list[dict[str, str]]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "content": self.content,
            "embeds": [dict(one) for one in self.embeds],
            "components": [[dict(one) for one in row] for row in self.components],
            "mentions": {
                "roles": list(self.mentions.get("roles", ())),
                "channels": list(self.mentions.get("channels", ())),
            },
        }


@dataclass(frozen=True)
class Renderer:
    """One feature's message, the keys that write it, and the facts it makes up."""

    feature: str
    title: str
    where: str
    build: Callable[[Any, Any, Any, dict[str, Any]], Rendered]
    keys: tuple[str, ...] = ()
    sample: dict[str, Any] = field(default_factory=dict)


def button(label: Any, style: str = "secondary", *, url: Any = None, disabled: bool = False,
           emoji: Any = None) -> dict[str, Any]:
    return {
        "label": str(label or ""),
        "style": "link" if url else str(style or "secondary"),
        "url": str(url) if url else None,
        "disabled": bool(disabled),
        "emoji": str(emoji) if emoji else None,
    }


def moves_to_rows(moves: Any) -> tuple[tuple[dict[str, Any], ...], ...]:
    """A feature's own move tuples as Discord's rows: their `row`, else five to a line."""
    found: dict[int, list[dict[str, Any]]] = {}
    for at, move in enumerate(moves or ()):
        line = int(getattr(move, "row", at // ROW_CAP) or 0)
        found.setdefault(line, []).append(
            button(getattr(move, "label", move), getattr(move, "style", "secondary"))
        )
    return tuple(tuple(found[line]) for line in sorted(found) if found[line])


def _named(guild: Any, how: str, wanted: str, fallback: str) -> str:
    look = getattr(guild, how, None)
    found = look(int(wanted)) if callable(look) else None
    return str(getattr(found, "name", None) or fallback)


def pills(guild: Any, *texts: Any) -> dict[str, list[dict[str, str]]]:
    """The roles and channels the text names, so the site draws a pill and not a raw id."""
    joined = "\n".join(str(one or "") for one in texts)
    return {
        "roles": [
            {"id": one, "name": _named(guild, "get_role", one, "unknown")}
            for one in dict.fromkeys(ROLE_MENTION.findall(joined))
        ],
        "channels": [
            {"id": one, "name": _named(guild, "get_channel", one, "deleted-channel")}
            for one in dict.fromkeys(CHANNEL_MENTION.findall(joined))
        ],
    }


def made(
    guild: Any,
    *,
    content: Any = "",
    embeds: Any = (),
    components: Any = (),
) -> Rendered:
    text = str(content or "")
    cards = [one.to_dict() if isinstance(one, discord.Embed) else dict(one) for one in embeds]
    said = [text, *(_embed_words(card) for card in cards)]
    return Rendered(
        content=text,
        embeds=tuple(cards),
        components=tuple(tuple(row) for row in components if row),
        mentions=pills(guild, *said),
    )


def _embed_words(card: dict[str, Any]) -> str:
    parts = [str(card.get("title") or ""), str(card.get("description") or "")]
    for one in card.get("fields") or ():
        parts.append(str(one.get("name") or ""))
        parts.append(str(one.get("value") or ""))
    return "\n".join(parts)


# --- the samples ------------------------------------------------------------------------------

GOLIVE_SAMPLE = {
    "name": "Casey",
    "game": "Lethal Company",
    "title": "late night runs",
    "platform": gl.TWITCH,
    "duration": "2 h 10 min",
}
PLATFORM_FACTS = {
    "twitch": {"platform": gl.TWITCH, "url": "https://twitch.tv/caseyfast", "source": "twitch"},
    "youtube": {
        "platform": gl.YOUTUBE,
        "url": "https://youtube.com/watch?v=caseyfast",
        "source": "youtube",
    },
}
OTHER_PLATFORM = {"twitch": "youtube", "youtube": "twitch"}


def platform_facts(platform: Any) -> dict[str, str]:
    """The address and the watcher a platform implies; nobody types a sample URL."""
    return PLATFORM_FACTS.get(str(platform or "").strip().casefold(), PLATFORM_FACTS["twitch"])


def golive_sample(sample: dict[str, Any]) -> dict[str, Any]:
    return GOLIVE_SAMPLE | sample | platform_facts(sample.get("platform"))


def stream_of(sample: dict[str, Any]) -> gl.StreamInfo:
    return gl.StreamInfo(
        url=sample.get("url"),
        game=sample.get("game"),
        title=sample.get("title"),
        platform=sample.get("platform"),
    )


def other_stream(sample: dict[str, Any]) -> gl.StreamInfo:
    """The second platform in a co-stream: whichever of the two the sample is not."""
    lead = platform_facts(sample.get("platform"))["source"]
    other = PLATFORM_FACTS[OTHER_PLATFORM[lead]]
    return gl.StreamInfo(
        url=other["url"],
        game=sample.get("game"),
        title=sample.get("title"),
        platform=other["platform"],
    )


# --- the renderers ----------------------------------------------------------------------------


def _live(bot: Any, guild: Any, store: Any, sample: dict[str, Any]) -> tuple[str, discord.Embed]:
    facts = golive_sample(sample)
    info = stream_of(facts)
    name = str(facts["name"])
    content = gl.render(
        store.get(guild.id, GOLIVE_TEMPLATE_KEY),
        info,
        name=name,
        ping_role_id=store.get(guild.id, GOLIVE_PING_ROLE_KEY),
    )
    embed = gl.announcement_embed(
        info,
        source=facts.get("source"),
        name=name,
        author=store.get(guild.id, GOLIVE_LIVE_AUTHOR_KEY),
    )
    return content, embed


def golive_live(bot: Any, guild: Any, store: Any, sample: dict[str, Any]) -> Rendered:
    content, embed = _live(bot, guild, store, sample)
    return made(guild, content=content, embeds=[embed])


def golive_ended(bot: Any, guild: Any, store: Any, sample: dict[str, Any]) -> Rendered:
    facts = golive_sample(sample)
    live, embed = _live(bot, guild, store, sample)
    name = str(facts["name"])
    duration = str(facts.get("duration") or "")
    content = gl.ended_render(
        store.get(guild.id, GOLIVE_END_TEMPLATE_KEY),
        stream_of(facts),
        name,
        content=live,
        duration=duration,
        keep_mention=bool(store.get(guild.id, GOLIVE_END_KEEP_MENTION_KEY)),
    )
    finished = gl.ended_embed(
        embed,
        name,
        facts.get("platform"),
        author=store.get(guild.id, GOLIVE_END_AUTHOR_KEY),
        duration=duration,
    )
    return made(guild, content=content, embeds=[finished])


def golive_costream(bot: Any, guild: Any, store: Any, sample: dict[str, Any]) -> Rendered:
    facts = golive_sample(sample)
    live, embed = _live(bot, guild, store, sample)
    name = str(facts["name"])
    first, second = gl.costream_order(stream_of(facts), other_stream(facts))
    content = gl.costream_render(
        store.get(guild.id, GOLIVE_COSTREAM_TEMPLATE_KEY), first, second, name, content=live
    )
    both = gl.costream_embed(
        embed, first, second, name, store.get(guild.id, GOLIVE_COSTREAM_AUTHOR_KEY)
    )
    return made(guild, content=content, embeds=[both])


def spotlight_bump(bot: Any, guild: Any, store: Any, sample: dict[str, Any]) -> Rendered:
    facts = golive_sample(sample)
    content = spotlight.bump_render(
        store.get(guild.id, SPOTLIGHT_BUMP_TEMPLATE_KEY),
        stream_of(facts),
        str(facts["name"]),
        str(facts.get("duration") or ""),
    )
    return made(guild, content=content)


def front_door(bot: Any, guild: Any, store: Any, sample: dict[str, Any]) -> Rendered:
    labels = frontdoor.labels(store, guild.id)
    row = [button(labels[kind], "primary" if kind == frontdoor.TICKET else "secondary")
           for kind in frontdoor.KINDS]
    return made(
        guild, embeds=[frontdoor.door_embed(store, guild.id)], components=[row]
    )


def ticket_button(bot: Any, guild: Any, store: Any, sample: dict[str, Any]) -> Rendered:
    embed = modmail.ticket_button_embed(
        store.get(guild.id, modmail.PANEL_HEADING_KEY),
        store.get(guild.id, modmail.PANEL_TEXT_KEY),
    )
    return made(guild, embeds=[embed], components=[[button(modmail.TICKET_MOVE.label, "primary")]])


def rehearsal(bot: Any, guild: Any, store: Any, sample: dict[str, Any]) -> Rendered:
    where = str(sample.get("channel") or "#live-now")
    line = shadow.note_line(PreviewBot(bot, store), guild, where)
    return made(guild, content=line)


def request_filed(bot: Any, guild: Any, store: Any, sample: dict[str, Any]) -> Rendered:
    return made(guild, content=reqs.filed_line(store, guild.id, sample.get("request_id") or 14))


REQUEST_ROW = {
    "id": 14,
    "user_id": 424242424242424242,
    "what": "A pinned index of every guide",
    "why": "people keep asking the same three questions in #general",
    "status": reqs.OPEN,
    "created_at": "",
}


def request_card(bot: Any, guild: Any, store: Any, sample: dict[str, Any]) -> Rendered:
    row = REQUEST_ROW | {
        "what": sample.get("what") or REQUEST_ROW["what"],
        "why": sample.get("why") or REQUEST_ROW["why"],
        "created_at": datetime.now(UTC).isoformat(),
    }
    look = reqs.look_for_status(row["status"])
    embed = reqs.request_embed(row, move=look, guild=guild)
    return made(
        guild, embeds=[embed], components=moves_to_rows(reqs.card_buttons(row["status"]))
    )


def event_card(bot: Any, guild: Any, store: Any, sample: dict[str, Any]) -> Rendered:
    starts = datetime.now(UTC) + timedelta(days=2)
    row = {
        "id": 9,
        "title": str(sample.get("title") or "Movie night — Paprika"),
        "requester_id": 424242424242424242,
        "starts_at": starts.isoformat(),
        "ends_at": (starts + timedelta(minutes=120)).isoformat(),
        "description": str(sample.get("description") or "Subtitles on, chat in the voice room."),
        "status": ev.PENDING,
        "deny_reason": None,
        "moved_to": None,
        "where_kind": None,
        "where_channel_id": None,
        "location": "the cinema room",
    }
    return made(
        guild,
        embeds=[ev.card_for(row)],
        components=moves_to_rows(ev.card_buttons(row["status"])),
    )


def modmail_relay(bot: Any, guild: Any, store: Any, sample: dict[str, Any]) -> Rendered:
    embed = modmail.relay_embed(
        modmail.IN,
        author_name=str(sample.get("name") or "Casey"),
        author_id=424242424242424242,
        content=str(sample.get("text") or "Someone is posting links in #general again."),
    )
    return made(guild, embeds=[embed])


def post_message(bot: Any, guild: Any, store: Any, sample: dict[str, Any]) -> Rendered:
    row = {
        "style": str(sample.get("style") or posts.PLAIN),
        "title": str(sample.get("title") or ""),
        "body": str(sample.get("body") or ""),
    }
    found = posts.render_message(row)
    embed = found.get("embed")
    return made(
        guild, content=found.get("content") or "", embeds=[embed] if embed is not None else []
    )


def birthday(bot: Any, guild: Any, store: Any, sample: dict[str, Any]) -> Rendered:
    years = sample.get("age")
    text = birthdays.render_description(
        store.get(guild.id, BIRTHDAY_TEMPLATE_KEY),
        str(sample.get("name") or "Casey"),
        int(years) if str(years or "").strip().isdigit() else None,
    )
    embed = discord.Embed(
        description=text,
        colour=discord.Colour(birthdays.parse_color(store.get(guild.id, BIRTHDAY_COLOR_KEY))),
    )
    return made(guild, embeds=[embed])


def poll_card(bot: Any, guild: Any, store: Any, sample: dict[str, Any]) -> Rendered:
    counts = [
        {"label": "Saturday", "votes": 7, "position": 1},
        {"label": "Sunday", "votes": 3, "position": 2},
    ]
    embed = polls.panel_embed(
        poll_id=3,
        question=str(sample.get("question") or "Which day for the next movie night?"),
        counts=counts,
        voters=10,
    )
    note = polls.shadow_note(store, guild.id, str(sample.get("channel") or "#announcements"))
    return made(guild, content=note, embeds=[embed])


def minutes_notes(bot: Any, guild: Any, store: Any, sample: dict[str, Any]) -> Rendered:
    row = {
        "channel_id": None,
        "started_at": datetime.now(UTC).isoformat(),
        "notes": str(sample.get("notes") or "Agreed to ship the guide index on Friday."),
    }
    embed = minutes.notes_embed(PreviewBot(bot, store), guild, row, [])
    return made(guild, content=minutes.start_text(store, guild.id), embeds=[embed])


RENDERERS: dict[str, Renderer] = {
    one.feature: one
    for one in (
        Renderer(
            "golive_live",
            "The announcement while they are live",
            "golive.html",
            golive_live,
            keys=(GOLIVE_TEMPLATE_KEY, GOLIVE_LIVE_AUTHOR_KEY),
            sample=dict(GOLIVE_SAMPLE),
        ),
        Renderer(
            "golive_ended",
            "The announcement once the stream has ended",
            "golive.html",
            golive_ended,
            keys=(GOLIVE_END_TEMPLATE_KEY, GOLIVE_END_AUTHOR_KEY),
            sample=dict(GOLIVE_SAMPLE),
        ),
        Renderer(
            "golive_costream",
            "The announcement while both platforms are live",
            "golive.html",
            golive_costream,
            keys=(GOLIVE_COSTREAM_TEMPLATE_KEY, GOLIVE_COSTREAM_AUTHOR_KEY),
            sample=dict(GOLIVE_SAMPLE),
        ),
        Renderer(
            "spotlight_bump",
            "The spotlight reminder",
            "golive.html",
            spotlight_bump,
            keys=(SPOTLIGHT_BUMP_TEMPLATE_KEY,),
            sample=dict(GOLIVE_SAMPLE),
        ),
        Renderer(
            "frontdoor",
            "The front door",
            "modmail.html",
            front_door,
            keys=(
                frontdoor.FRONTDOOR_TITLE,
                frontdoor.FRONTDOOR_TEXT,
                frontdoor.FRONTDOOR_TICKET_LABEL,
                frontdoor.FRONTDOOR_REQUEST_LABEL,
                frontdoor.FRONTDOOR_EVENT_LABEL,
            ),
        ),
        Renderer(
            "ticket_button",
            "The Open a ticket message",
            "modmail.html",
            ticket_button,
            keys=(modmail.PANEL_HEADING_KEY, modmail.PANEL_TEXT_KEY),
        ),
        Renderer(
            "rehearsal",
            "The line a rehearsal copy carries",
            "settings.html",
            rehearsal,
            keys=(shadow.NOTE_KEY,),
            sample={"channel": "#live-now"},
        ),
        Renderer(
            "request_filed",
            "What a member is told when they file a request",
            "requests.html",
            request_filed,
            keys=(reqs.REQUEST_FILED_KEY,),
            sample={"request_id": 14},
        ),
        Renderer(
            "request_card",
            "A request's card",
            "requests.html",
            request_card,
            sample={"what": "", "why": ""},
        ),
        Renderer(
            "event_card",
            "An event's card",
            "events.html",
            event_card,
            sample={"title": "", "description": ""},
        ),
        Renderer(
            "modmail_relay",
            "A relayed modmail message",
            "modmail.html",
            modmail_relay,
            sample={"name": "", "text": ""},
        ),
        Renderer(
            "post",
            "A post",
            "posts.html",
            post_message,
            sample={
                "style": posts.PLAIN,
                "title": "Welcome",
                "body": "**Welcome!** Start with the pinned guide, then say hello.",
            },
        ),
        Renderer(
            "birthday",
            "A birthday announcement",
            "birthdays.html",
            birthday,
            keys=(BIRTHDAY_TEMPLATE_KEY,),
            sample={"name": "Casey", "age": ""},
        ),
        Renderer(
            "poll_card",
            "A poll, and the line its rehearsal copy carries",
            "polls.html",
            poll_card,
            keys=(polls.SHADOW_NOTE_KEY,),
            sample={"question": "", "channel": "#announcements"},
        ),
        Renderer(
            "minutes_notes",
            "What minutes post when a meeting starts and ends",
            "minutes.html",
            minutes_notes,
            keys=(minutes.START_TEXT_KEY, minutes.NOTES_TITLE_KEY),
            sample={"notes": ""},
        ),
    )
}

KEY_FEATURES: dict[str, str] = {
    key: one.feature for one in RENDERERS.values() for key in one.keys
}


def features_payload() -> dict[str, Any]:
    """The map the site reads to know which key has a mock and which has none."""
    return {
        "features": [
            {
                "feature": one.feature,
                "title": one.title,
                "where": one.where,
                "keys": list(one.keys),
                "sample": dict(one.sample),
            }
            for one in RENDERERS.values()
        ],
        "keys": dict(KEY_FEATURES),
    }


def _clamped(value: Any, limit: int) -> str:
    text = "" if value is None else str(value)
    return text[:limit]


def wanted_overrides(one: Renderer, overrides: Any) -> dict[str, str]:
    found = {}
    for key, value in dict(overrides or {}).items():
        if key not in one.keys:
            raise PreviewRefused(
                "not_this_features_key",
                UNKNOWN_KEY.format(key=str(key)[:60], feature=one.title),
            )
        found[str(key)] = _clamped(value, OVERRIDE_LIMIT)
    return found


def wanted_sample(one: Renderer, sample: Any) -> dict[str, Any]:
    found = dict(one.sample)
    for key, value in dict(sample or {}).items():
        if key in found:
            found[key] = _clamped(value, SAMPLE_LIMIT)
    return found


def render(
    bot: Any, guild: Any, feature: Any, overrides: Any = None, sample: Any = None
) -> Rendered:
    """The one way in: the draft is laid over the store and the bot's own function draws it."""
    one = RENDERERS.get(str(feature or ""))
    if one is None:
        raise PreviewRefused(
            "no_such_preview", UNKNOWN_FEATURE.format(feature=str(feature or "nothing")[:60])
        )
    store = PreviewStore(bot.store, guild.id, wanted_overrides(one, overrides))
    return one.build(bot, guild, store, wanted_sample(one, sample))
