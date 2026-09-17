from __future__ import annotations

from typing import Any

import discord

from .events import clamp
from .settings_store import (
    FRONTDOOR_CHANNEL,
    FRONTDOOR_EVENT_LABEL,
    FRONTDOOR_EVENT_LABEL_DEFAULT,
    FRONTDOOR_FOLLOWS_NOTHING,
    FRONTDOOR_FOLLOWS_POST,
    FRONTDOOR_MESSAGE,
    FRONTDOOR_MODE,
    FRONTDOOR_REPLACES_TICKET_BUTTON,
    FRONTDOOR_REQUEST_LABEL,
    FRONTDOOR_REQUEST_LABEL_DEFAULT,
    FRONTDOOR_TEXT,
    FRONTDOOR_TEXT_DEFAULT,
    FRONTDOOR_TICKET_LABEL,
    FRONTDOOR_TICKET_LABEL_DEFAULT,
    FRONTDOOR_TITLE,
    FRONTDOOR_TITLE_DEFAULT,
)

TICKET = "ticket"
REQUEST = "request"
EVENT = "event"
KINDS: tuple[str, ...] = (TICKET, REQUEST, EVENT)

ON = "on"
OFF = "off"
MODES: tuple[str, ...] = (OFF, ON)

LABEL_LIMIT = 80
TITLE_LIMIT = 256
TEXT_LIMIT = 4000
DOOR_COLOUR = 0x5865F2

CUSTOM_ID_HEAD = "door"
CUSTOM_ID_TEMPLATE = r"door:(?P<kind>ticket|request|event):(?P<guild_id>[0-9]+)"

LABEL_KEYS: dict[str, str] = {
    TICKET: FRONTDOOR_TICKET_LABEL,
    REQUEST: FRONTDOOR_REQUEST_LABEL,
    EVENT: FRONTDOOR_EVENT_LABEL,
}
LABEL_DEFAULTS: dict[str, str] = {
    TICKET: FRONTDOOR_TICKET_LABEL_DEFAULT,
    REQUEST: FRONTDOOR_REQUEST_LABEL_DEFAULT,
    EVENT: FRONTDOOR_EVENT_LABEL_DEFAULT,
}

DOOR_OFF = (
    "The front door is switched off, so there is nothing to open here. A Lead turns "
    "`frontdoor_mode` back on from the dashboard's Settings page under **modmail**, or from "
    "`/settings` ▸ **A setting group…** ▸ modmail — every other way in (a DM to Black Bloc, "
    "`/modmail`, `/request`, `/event`) still works meanwhile."
)
DOOR_NOT_UP = (
    "There is no front door posted anywhere, so nothing was taken down. **Post the front "
    "door** on the Modmail page is what puts one up."
)
DOOR_GUARDED = (
    "Black Bloc is in test mode, so it only posts in its own test channel. The front door was "
    "not posted. Turn test mode off, or point `frontdoor_channel_id` at the test channel."
)
DOOR_NO_CHANNEL = (
    "That is not a channel Black Bloc can see, so the front door was not posted. Pick one from "
    "the list and try again."
)
DOOR_STUCK = (
    "Black Bloc could not post the front door in that channel. It needs **View Channel**, "
    "**Send Messages** and **Embed Links** there — give it those and try again."
)
DOOR_POSTED_SAID = "The front door is up in <#{where}>."
DOOR_MOVED_SAID = "The front door has moved to <#{where}>."
DOOR_DOWN_SAID = "The front door is down. Nothing else changed, and `/ask` still works."

PANEL_TIMEOUT_FOOTER = "This panel has gone quiet — run /ask again"
EVENT_HANDOFF_TITLE = "Propose an event"
EVENT_HANDOFF_TEXT = (
    "An event is a card you fill in — the day, the time, where it is — rather than one form, "
    "so it opens here where only you can see it. Press the button to start."
)


def custom_id(kind: str, guild_id: Any) -> str:
    return f"{CUSTOM_ID_HEAD}:{kind}:{int(guild_id)}"


def door_is_on(store: Any, guild_id: int) -> bool:
    return str(store.get(guild_id, FRONTDOOR_MODE) or OFF) == ON


def replaces_ticket_button(store: Any, guild_id: int) -> bool:
    return bool(store.get(guild_id, FRONTDOOR_REPLACES_TICKET_BUTTON))


def label_for(store: Any, guild_id: int, kind: str) -> str:
    """A blank label reads as "leave it alone", so the shipped word is what is drawn."""
    found = str(store.get(guild_id, LABEL_KEYS[kind]) or "").strip()
    return clamp(found, LABEL_LIMIT) or LABEL_DEFAULTS[kind]


def labels(store: Any, guild_id: int) -> dict[str, str]:
    return {kind: label_for(store, guild_id, kind) for kind in KINDS}


def door_title(store: Any, guild_id: int) -> str:
    return clamp(store.get(guild_id, FRONTDOOR_TITLE), TITLE_LIMIT) or FRONTDOOR_TITLE_DEFAULT


def door_text(store: Any, guild_id: int) -> str:
    return clamp(store.get(guild_id, FRONTDOOR_TEXT), TEXT_LIMIT) or FRONTDOOR_TEXT_DEFAULT


def door_embed(store: Any, guild_id: int) -> discord.Embed:
    """The one card both doors wear: the posted message and the `/ask` panel are the same."""
    return discord.Embed(
        title=door_title(store, guild_id),
        description=door_text(store, guild_id),
        colour=discord.Colour(DOOR_COLOUR),
    )


def followed_slug(store: Any, guild_id: int) -> str:
    """The post the door sits under; `none` never moves the door for that reason."""
    found = str(store.get(guild_id, FRONTDOOR_FOLLOWS_POST) or "").strip()
    return "" if found.casefold() == FRONTDOOR_FOLLOWS_NOTHING else found


def door_where(store: Any, guild_id: int) -> tuple[int | None, int | None]:
    channel_id = store.get(guild_id, FRONTDOOR_CHANNEL)
    message_id = store.get(guild_id, FRONTDOOR_MESSAGE)
    return (
        int(channel_id) if channel_id else None,
        int(message_id) if message_id else None,
    )


def door_takes_over(store: Any, guild_id: int) -> int | None:
    """The channel the front door owns outright — modmail's own button stays down in it."""
    if not door_is_on(store, guild_id) or not replaces_ticket_button(store, guild_id):
        return None
    channel_id, message_id = door_where(store, guild_id)
    return channel_id if channel_id and message_id else None


__all__ = [
    "CUSTOM_ID_TEMPLATE",
    "DOOR_COLOUR",
    "DOOR_DOWN_SAID",
    "DOOR_GUARDED",
    "DOOR_MOVED_SAID",
    "DOOR_NOT_UP",
    "DOOR_NO_CHANNEL",
    "DOOR_OFF",
    "DOOR_POSTED_SAID",
    "DOOR_STUCK",
    "EVENT",
    "EVENT_HANDOFF_TEXT",
    "EVENT_HANDOFF_TITLE",
    "KINDS",
    "LABEL_DEFAULTS",
    "LABEL_KEYS",
    "LABEL_LIMIT",
    "MODES",
    "OFF",
    "ON",
    "PANEL_TIMEOUT_FOOTER",
    "REQUEST",
    "TICKET",
    "custom_id",
    "door_embed",
    "door_is_on",
    "door_takes_over",
    "door_text",
    "door_title",
    "door_where",
    "followed_slug",
    "label_for",
    "labels",
    "replaces_ticket_button",
]
