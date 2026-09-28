from __future__ import annotations

import hashlib
import json
from typing import Any, NamedTuple

from .panels import KEEP_IT
from .panels import panel_minutes as library_panel_minutes
from .panels import site_page_url as library_site_page_url
from .settings_store import (
    TEMPVOICE_BLOCK_CONTROLS_LABEL,
    TEMPVOICE_BLOCK_DEFAULTS,
    TEMPVOICE_BLOCK_LOBBY_LABEL,
    TEMPVOICE_BLOCK_SHOW_CONTROLS,
    TEMPVOICE_BLOCK_TEXT,
    TEMPVOICE_BLOCK_TITLE,
)

AUTO_REGION = "auto"
VOICE_REGIONS = (
    AUTO_REGION,
    "brazil",
    "bucharest",
    "buenos-aires",
    "dubai",
    "finland",
    "frankfurt",
    "hongkong",
    "india",
    "japan",
    "madrid",
    "milan",
    "rotterdam",
    "russia",
    "santiago",
    "singapore",
    "south-korea",
    "southafrica",
    "stockholm",
    "sydney",
    "tel-aviv",
    "us-central",
    "us-east",
    "us-south",
    "us-west",
    "warsaw",
)

BLOCK_CUSTOM_ID_HEAD = "tvblock:open"
BLOCK_CUSTOM_ID_TEMPLATE = r"tvblock:open:(?P<guild_id>[0-9]+)"
BLOCK_LOBBIES_MAX = 4
BLOCK_LABEL_MAX = 80
BLOCK_TITLE_MAX = 256
BLOCK_TEXT_MAX = 4000
LOBBY_TOKEN = "{lobby}"
LOBBY_URL = "https://discord.com/channels/{guild_id}/{channel_id}"
CONTROLS_LABEL_DEFAULT = str(TEMPVOICE_BLOCK_DEFAULTS[TEMPVOICE_BLOCK_CONTROLS_LABEL])

PANEL_MINUTES_KEY = "voice_panel_minutes"
SITE_FEATURE = "tempvoice"
SELECT_CAP = 25

PANEL_TITLE = "Your voice channel"
PANEL_TIMEOUT_FOOTER = "This panel has gone quiet — run /voice again"

PANEL_INTRO = (
    "Your own temporary voice channel, and everything you can change about it. Nothing here "
    "touches anybody else's."
)
MODE_OFF_LINE = (
    "Join-to-create is **off** for this server at the moment, so joining the lobby makes no "
    "channel. Channels that already exist keep working."
)
SHADOW_LINE = (
    "The lobby is hidden from members while temp voice is in **shadow** — staff can still see "
    "it, and a room it makes is hidden the same way."
)
ORPHAN_LINE = (
    "You are in <@{owner_id}>'s channel and they have left it, so **Claim** makes it yours."
)
GUEST_LINE = (
    "You are in <@{owner_id}>'s channel and they are still in it, so it cannot be claimed. Ask "
    "them to press **Hand it over…** on their own `/voice` panel."
)
STAFF_WITHOUT_ROLE = (
    "You do not have the <@&{role_id}> role, so Black Bloc keeps no channel of your own here — "
    "the staff controls below still work."
)
NOTHING_TO_SEE = (
    "Nobody has a temporary voice channel open right now, so there is nothing to hand over."
)

PICK_CHANNEL = "A channel…"
PICK_LOBBY = "A lobby to forget…"
PICK_REGION = "A region…"
PICK_PERMIT = "Let someone in…"
PICK_BAN = "Keep someone out…"
PICK_KICK = "Move someone out…"
PICK_UNDO = "Undo for…"
PICK_NEW_OWNER = "Who should own it?"
PICK_MODE = "What join-to-create should do…"

OFF_MODE = "off"
SHADOW_MODE = "shadow"
ON_MODE = "on"
MODE_MEANS: dict[str, str] = {
    OFF_MODE: "Joining the lobby makes nothing. Rooms that exist keep working.",
    SHADOW_MODE: "It works, but only staff see the lobby — and a room it makes follows it.",
    ON_MODE: "The lobby is visible to whoever its category shows.",
}
MODE_INTRO = "What joining the lobby does, and who can see it."

PEOPLE_TITLE = "Who may be in your channel"
REGION_TITLE = "Where the audio goes"
MODE_TITLE = "What join-to-create does"
HAND_OVER_TITLE = "Hand your channel over"
LOBBY_TITLE = "Join-to-create lobbies"
STAFF_CARD_TITLE = "A temporary voice channel"
FORGET_TITLE = "Are you sure?"

FORGET_QUESTION = (
    "Forget everything Black Bloc remembers about your voice channels? The channel you are in "
    "now is not changed."
)
FORGET_YES = "Yes, forget it"

BLOCKED = "blocked"
NONE = "none"
OWNER = "owner"
ORPHAN = "orphan"
GUEST = "guest"

RENAME = "rename"
LIMIT = "limit"
LOCK = "lock"
UNLOCK = "unlock"
HIDE = "hide"
SHOW = "show"
BITRATE = "bitrate"
PEOPLE = "people"
REGION = "region"
TRANSFER = "transfer"
FORGET_PREFS = "forget_prefs"
REFRESH = "refresh"
CLAIM = "claim"
BACK = "back"
AUTOMATIC = "automatic"
SETUP = "setup"
LOBBIES = "lobbies"
MODE = "mode"
LOGS = "logs"

PERMIT_PICK = "permit"
BAN_PICK = "ban"
KICK_PICK = "kick"
UNDO_PICK = "undo"

UNPERMIT_KIND = "unpermit"
UNBAN_KIND = "unban"


class VoiceMove(NamedTuple):
    action: str
    label: str
    style: str = "secondary"
    row: int = 0


RENAME_MOVE = VoiceMove(RENAME, "Rename")
LIMIT_MOVE = VoiceMove(LIMIT, "Limit")
LOCK_MOVE = VoiceMove(LOCK, "Lock")
UNLOCK_MOVE = VoiceMove(UNLOCK, "Unlock")
HIDE_MOVE = VoiceMove(HIDE, "Hide")
SHOW_MOVE = VoiceMove(SHOW, "Show")
BITRATE_MOVE = VoiceMove(BITRATE, "Bitrate")
PEOPLE_MOVE = VoiceMove(PEOPLE, "People…", row=1)
REGION_MOVE = VoiceMove(REGION, "Region…", row=1)
TRANSFER_MOVE = VoiceMove(TRANSFER, "Hand it over…", row=1)
FORGET_PREFS_MOVE = VoiceMove(FORGET_PREFS, "Forget my settings", "danger", row=1)
REFRESH_MOVE = VoiceMove(REFRESH, "Refresh", row=1)
CLAIM_MOVE = VoiceMove(CLAIM, "Claim", "success")
BACK_MOVE = VoiceMove(BACK, "Back", row=4)
AUTOMATIC_MOVE = VoiceMove(AUTOMATIC, "Automatic", "primary", row=1)
SETUP_MOVE = VoiceMove(SETUP, "Setup", row=2)
LOBBIES_MOVE = VoiceMove(LOBBIES, "Forget a lobby…", row=2)
MODE_MOVE = VoiceMove(MODE, "Mode…", row=2)
LOGS_MOVE = VoiceMove(LOGS, "Logs", row=2)
STAFF_TRANSFER_MOVE = VoiceMove(TRANSFER, "Hand it over…", row=0)

CARD_BUTTONS = (
    RENAME_MOVE,
    LIMIT_MOVE,
    LOCK_MOVE,
    UNLOCK_MOVE,
    HIDE_MOVE,
    SHOW_MOVE,
    BITRATE_MOVE,
    PEOPLE_MOVE,
    REGION_MOVE,
    TRANSFER_MOVE,
    FORGET_PREFS_MOVE,
    REFRESH_MOVE,
    CLAIM_MOVE,
    SETUP_MOVE,
    LOBBIES_MOVE,
    MODE_MOVE,
    LOGS_MOVE,
)


def makes_rooms(mode: Any) -> bool:
    """Shadow works exactly like on — it only changes who can see the lobby."""
    return str(mode or "") in (SHADOW_MODE, ON_MODE)


def shows_block(mode: Any) -> bool:
    """The lobby block is drawn only while members can see the lobby."""
    return str(mode or "") == ON_MODE


def named_regions() -> tuple[str, ...]:
    """Discord's regions without `auto`, which is a button — exactly 25, so no select is capped."""
    return tuple(name for name in VOICE_REGIONS if name != AUTO_REGION)


def panel_state(
    rows: Any, user_id: Any, here_id: Any, connected: Any = (), *, allowed: bool = True
) -> str:
    """Which row of the button table the caller is on, from the same rules `pick_row` applies."""
    if not allowed:
        return BLOCKED
    found = list(rows or ())
    me = int(user_id)
    here = None if here_id is None else int(here_id)
    mine = None
    if here is not None:
        mine = next((row for row in found if int(row["channel_id"]) == here), None)
    if mine is not None and int(mine["owner_id"]) == me:
        return OWNER
    if next((row for row in found if int(row["owner_id"]) == me), None) is not None:
        return OWNER
    if mine is None:
        return NONE
    inside = {int(one) for one in connected or ()}
    return GUEST if int(mine["owner_id"]) in inside else ORPHAN


def card_buttons(
    state: str,
    *,
    locked: bool = False,
    hidden: bool = False,
    has_prefs: bool = False,
    staff: bool = False,
    has_lobbies: bool = False,
) -> tuple[VoiceMove, ...]:
    """The state table as data — no state offers a move the shared function would refuse."""
    found: list[VoiceMove] = []
    if state == OWNER:
        found += [
            RENAME_MOVE,
            LIMIT_MOVE,
            UNLOCK_MOVE if locked else LOCK_MOVE,
            SHOW_MOVE if hidden else HIDE_MOVE,
            BITRATE_MOVE,
            PEOPLE_MOVE,
            REGION_MOVE,
            TRANSFER_MOVE,
        ]
        if has_prefs:
            found.append(FORGET_PREFS_MOVE)
        found.append(REFRESH_MOVE)
    else:
        if state == ORPHAN:
            found.append(CLAIM_MOVE)
        if has_prefs and state != BLOCKED:
            found.append(FORGET_PREFS_MOVE._replace(row=0))
        found.append(REFRESH_MOVE._replace(row=0))
    if staff:
        found.append(SETUP_MOVE)
        if has_lobbies:
            found.append(LOBBIES_MOVE)
        found.append(MODE_MOVE)
        found.append(LOGS_MOVE)
    return tuple(found)


def people_controls(*, others_here: bool = False, has_lists: bool = False) -> tuple[str, ...]:
    """The People sub-panel's selects; the two that need somebody render only when there is one."""
    found = [PERMIT_PICK, BAN_PICK]
    if others_here:
        found.append(KICK_PICK)
    if has_lists:
        found.append(UNDO_PICK)
    return tuple(found)


def undo_options(permitted: Any, banned: Any) -> list[tuple[int, str]]:
    """One control, options that already know which undo they are."""
    found = [(int(user_id), UNPERMIT_KIND) for user_id in permitted or ()]
    found += [(int(user_id), UNBAN_KIND) for user_id in banned or ()]
    return found


def panel_minutes(store: Any, guild_id: int) -> int:
    return library_panel_minutes(store, guild_id, PANEL_MINUTES_KEY)


def site_page_url(origin: Any) -> str | None:
    return library_site_page_url(origin, SITE_FEATURE)


def block_word(store: Any, guild_id: int, key: str, limit: int) -> str:
    """A block word as saved, or the shipped one while it is blank."""
    text = str(store.get(guild_id, key) or "").strip()
    return (text or str(TEMPVOICE_BLOCK_DEFAULTS[key]))[:limit]


def block_custom_id(guild_id: Any) -> str:
    return f"{BLOCK_CUSTOM_ID_HEAD}:{int(guild_id)}"


def lobby_url(guild_id: Any, channel_id: Any) -> str:
    return LOBBY_URL.format(guild_id=int(guild_id), channel_id=int(channel_id))


def lobby_label(store: Any, guild_id: int, name: Any) -> str:
    template = block_word(store, guild_id, TEMPVOICE_BLOCK_LOBBY_LABEL, BLOCK_TEXT_MAX)
    said = template.replace(LOBBY_TOKEN, str(name or "")).strip()
    return said[:BLOCK_LABEL_MAX] or str(name or "")[:BLOCK_LABEL_MAX]


def shows_controls(store: Any, guild_id: int, wanted: Any = "") -> bool:
    """`wanted` is an editor's unsaved tick ("on" / "off"); blank reads the key."""
    said = str(wanted or "").strip().lower()
    if said in ("on", "true", "1"):
        return True
    if said in ("off", "false", "0"):
        return False
    found = store.get(guild_id, TEMPVOICE_BLOCK_SHOW_CONTROLS)
    return True if found is None else bool(found)


class BlockLook(NamedTuple):
    title: str
    text: str
    buttons: tuple[tuple[str, str | None], ...]

    def stamp(self) -> str:
        return hashlib.sha256(json.dumps(list(self), ensure_ascii=False).encode()).hexdigest()


def block_look(
    store: Any, guild_id: int, lobbies: Any, *, controls: Any = ""
) -> BlockLook:
    """What the lobby block says and links to: one button per lobby, then /voice's own panel."""
    buttons = [
        (lobby_label(store, guild_id, name), lobby_url(guild_id, channel_id))
        for channel_id, name in list(lobbies or ())[:BLOCK_LOBBIES_MAX]
    ]
    if shows_controls(store, guild_id, controls):
        buttons.append(
            (block_word(store, guild_id, TEMPVOICE_BLOCK_CONTROLS_LABEL, BLOCK_LABEL_MAX), None)
        )
    return BlockLook(
        block_word(store, guild_id, TEMPVOICE_BLOCK_TITLE, BLOCK_TITLE_MAX),
        block_word(store, guild_id, TEMPVOICE_BLOCK_TEXT, BLOCK_TEXT_MAX),
        tuple(buttons),
    )


__all__ = [
    "AUTOMATIC",
    "AUTOMATIC_MOVE",
    "AUTO_REGION",
    "BACK",
    "BACK_MOVE",
    "BAN_PICK",
    "BITRATE",
    "BLOCKED",
    "BLOCK_CUSTOM_ID_HEAD",
    "BLOCK_CUSTOM_ID_TEMPLATE",
    "BLOCK_LOBBIES_MAX",
    "BlockLook",
    "CONTROLS_LABEL_DEFAULT",
    "block_custom_id",
    "block_look",
    "block_word",
    "lobby_label",
    "lobby_url",
    "shows_controls",
    "CARD_BUTTONS",
    "CLAIM",
    "FORGET_PREFS",
    "FORGET_QUESTION",
    "FORGET_TITLE",
    "FORGET_YES",
    "GUEST",
    "GUEST_LINE",
    "HAND_OVER_TITLE",
    "HIDE",
    "KEEP_IT",
    "KICK_PICK",
    "LIMIT",
    "LOBBIES",
    "LOBBY_TITLE",
    "LOCK",
    "LOGS",
    "MODE",
    "MODE_INTRO",
    "MODE_MEANS",
    "MODE_MOVE",
    "MODE_OFF_LINE",
    "MODE_TITLE",
    "NONE",
    "NOTHING_TO_SEE",
    "OFF_MODE",
    "ON_MODE",
    "ORPHAN",
    "ORPHAN_LINE",
    "OWNER",
    "PANEL_INTRO",
    "PANEL_MINUTES_KEY",
    "PANEL_TIMEOUT_FOOTER",
    "PANEL_TITLE",
    "PEOPLE",
    "PEOPLE_TITLE",
    "PERMIT_PICK",
    "PICK_BAN",
    "PICK_CHANNEL",
    "PICK_KICK",
    "PICK_LOBBY",
    "PICK_MODE",
    "PICK_NEW_OWNER",
    "PICK_PERMIT",
    "PICK_REGION",
    "PICK_UNDO",
    "REFRESH",
    "REGION",
    "REGION_TITLE",
    "RENAME",
    "SELECT_CAP",
    "SETUP",
    "SHADOW_LINE",
    "SHADOW_MODE",
    "SHOW",
    "SITE_FEATURE",
    "STAFF_CARD_TITLE",
    "STAFF_TRANSFER_MOVE",
    "STAFF_WITHOUT_ROLE",
    "TRANSFER",
    "UNBAN_KIND",
    "UNDO_PICK",
    "UNLOCK",
    "UNPERMIT_KIND",
    "VOICE_REGIONS",
    "VoiceMove",
    "card_buttons",
    "makes_rooms",
    "shows_block",
    "named_regions",
    "panel_minutes",
    "panel_state",
    "people_controls",
    "site_page_url",
    "undo_options",
]
