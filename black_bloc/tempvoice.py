from __future__ import annotations

from typing import Any, NamedTuple

from .panels import KEEP_IT
from .panels import panel_minutes as library_panel_minutes
from .panels import site_page_url as library_site_page_url

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

PEOPLE_TITLE = "Who may be in your channel"
REGION_TITLE = "Where the audio goes"
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
MODE_OFF_MOVE = VoiceMove(MODE, "Turn join-to-create off", row=2)
MODE_ON_MOVE = VoiceMove(MODE, "Turn join-to-create on", row=2)
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
    MODE_OFF_MOVE,
    MODE_ON_MOVE,
    LOGS_MOVE,
)


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
    mode_on: bool = True,
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
        found.append(MODE_OFF_MOVE if mode_on else MODE_ON_MOVE)
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


__all__ = [
    "AUTOMATIC",
    "AUTOMATIC_MOVE",
    "AUTO_REGION",
    "BACK",
    "BACK_MOVE",
    "BAN_PICK",
    "BITRATE",
    "BLOCKED",
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
    "MODE_OFF_LINE",
    "NONE",
    "NOTHING_TO_SEE",
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
    "named_regions",
    "panel_minutes",
    "panel_state",
    "people_controls",
    "site_page_url",
    "undo_options",
]
