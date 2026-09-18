from __future__ import annotations

import logging
from datetime import UTC, date, datetime
from typing import Any, NamedTuple

import discord

from .actionlog import log_action
from .forums import AUTO_ARCHIVE_MINUTES, tag_named
from .forums import forum_tags as library_forum_tags
from .logkinds import FEATURE_PAGES, VIA_DISCORD, kind_via
from .panels import CAPPED_PLACEHOLDER, capped_placeholder
from .panels import option_label as library_option_label
from .panels import panel_minutes as library_panel_minutes
from .panels import site_page_url as library_site_page_url
from .timezones import DEFAULT_TZ, zone

log = logging.getLogger(__name__)

OPEN = "open"
IN_PROGRESS = "in_progress"
REVIEW = "review"
HOLD = "hold"
DONE = "done"
DECLINED = "declined"
WITHDRAWN = "withdrawn"
MOVED = "moved"

STATUSES = (OPEN, IN_PROGRESS, REVIEW, HOLD, DONE, DECLINED, WITHDRAWN, MOVED)

TRANSITIONS: dict[str, frozenset[str]] = {
    OPEN: frozenset({IN_PROGRESS, HOLD, DECLINED}),
    IN_PROGRESS: frozenset({REVIEW, HOLD, DECLINED}),
    REVIEW: frozenset({IN_PROGRESS, DONE, HOLD, DECLINED}),
    HOLD: frozenset({IN_PROGRESS, REVIEW, DECLINED}),
    DONE: frozenset(),
    DECLINED: frozenset(),
    WITHDRAWN: frozenset(),
    MOVED: frozenset(),
}
WITHDRAWABLE = (OPEN, HOLD)
STAFF_STATUSES = tuple(
    sorted({one for moves in TRANSITIONS.values() for one in moves})
)
OPEN_STATUSES = (OPEN, IN_PROGRESS, REVIEW, HOLD)
FINAL_STATUSES = tuple(one for one in STATUSES if not TRANSITIONS[one])
NEEDS_A_REASON = (HOLD, DECLINED)

FILED_LOOK = "filed"
SENT_BACK = "sent_back"
CHECK_ASKED = "check_asked"
LOOKS = (
    FILED_LOOK,
    IN_PROGRESS,
    REVIEW,
    SENT_BACK,
    DONE,
    HOLD,
    DECLINED,
    MOVED,
    CHECK_ASKED,
)
DM_LOOKS = (IN_PROGRESS, HOLD, DONE, DECLINED)
CHANNEL_LOOKS = tuple(one for one in LOOKS if one != MOVED)
CHANNEL_MOVES_KEY = "request_channel_moves"
REVIEW_BY_OTHER_KEY = "request_review_by_other"
PANEL_MINUTES_KEY = "request_panel_minutes"
PANEL_OWN_LIST_KEY = "request_panel_own_list"
CHECK_FALLBACK_KEY = "request_check_fallback_channel"
CHECK_ON_READY_KEY = "request_check_on_ready"
POST_BUTTONS_KEY = "request_post_buttons"

SELECT_CAP = 25
SELECT_OPTION_LIMIT = 100

WHAT_LIMIT = 1000
WHY_LIMIT = 1000
REASON_LIMIT = 400
NOTES_LIMIT = 1000
COMMENT_LIMIT = 1000
BUILT_LIMIT = 1000
HOW_TO_TEST_LIMIT = 1000
SENT_BACK_LIMIT = 500
PRIORITY_MAX = 5
DUE_SHAPE = "YYYY-MM-DD"
LIST_PAGE = 10
API_PAGE = 20
SEARCH_LIMIT = 80
FIELD_LIMIT = 1024
TITLE_LIMIT = 256
NAME_LIMIT = 100

STATUS_WORDS: dict[str, str] = {
    OPEN: "open",
    IN_PROGRESS: "being worked on",
    REVIEW: "ready to check",
    HOLD: "on hold",
    DONE: "done",
    DECLINED: "declined",
    WITHDRAWN: "withdrawn",
    MOVED: "moved",
}

REQUESTS_OFF = (
    "Requests are turned off on this server, so nothing was filed. A Lead turns them back on "
    "with `/settings` ▸ **Turn a feature back on…** — ask one if you have something to ask for."
)
STAFF_ONLY_FILES = (
    "Only staff may file a request on this server at the moment, so nothing was filed. Ask a Lead "
    "to put it in for you, or to set `request_who_can_file` to everyone."
)
NEEDS_WHAT = (
    "A request needs a line saying what you are asking for, so nothing was filed. Fill the What "
    "box in and send it again."
)
NEEDS_WHY = (
    "A request needs a line saying why it is worth doing, so nothing was filed. That is the part "
    "staff read first — fill the Why box in and send it again."
)
BAD_DUE = (
    "**{given}** is not a date Black Bloc can read, so nothing was filed. Write it as "
    f"`{DUE_SHAPE}` — `2026-09-15`, say — or leave the box empty if there is no deadline."
)
NO_SUCH_REQUEST = (
    "Black Bloc has no request **#{request_id}**, so nothing was done. `/request` shows the "
    "ones it has."
)
NOT_YOURS = (
    "Request **#{request_id}** is not yours, so nothing was withdrawn. Only the person who filed "
    "it can take it back; staff decline one instead."
)
TOO_LATE_TO_WITHDRAW = (
    "Request **#{request_id}** is **{status}**, so there was nothing to withdraw. You can take "
    "back one that is still open or on hold; ask staff if you want this one stopped."
)
ALREADY_THAT = "Request **#{request_id}** is already **{status}**, so nothing was changed."
UNKNOWN_STATUS = (
    "**{given}** is not a state a request can be in, so nothing was changed. They are {known}."
)
NO_SUCH_MOVE = (
    "Request **#{request_id}** is **{status}**, and staff cannot move it to **{wanted}** from "
    "there, so nothing was changed. {allowed}"
)
MOVES_ARE = "From **{status}** it can go to {moves}."
NO_MOVES_LEFT = "**{status}** is where a request finishes — nothing moves it now."
DECLINE_NEEDS_A_REASON = (
    "A declined request needs one line the person who asked is sent, so nothing was changed. Say "
    "why and send it again."
)
HOLD_NEEDS_A_REASON = (
    "A request put on hold needs one line the person who asked is sent, so nothing was changed. "
    "Say why it is waiting and send it again."
)
REASON_NEEDED: dict[str, str] = {
    DECLINED: DECLINE_NEEDS_A_REASON,
    HOLD: HOLD_NEEDS_A_REASON,
}
READY_NEEDS_WHAT_WAS_BUILT = (
    "Marking a request ready to check needs a line saying what was actually built, so nothing was "
    "changed. That sentence is what the person who asked reads on the card. "
    "**Ready to check** on its card opens a box for it — on the `/request` panel or on the site."
)
SENDING_BACK_NEEDS_A_NOTE = (
    "Sending a request back needs one line saying what is still to do, so nothing was changed. The "
    "staffer who marked it ready is sent exactly what you type — say what is missing and send it "
    "again."
)
TEXT_NEEDED: dict[str, str] = {
    REVIEW: READY_NEEDS_WHAT_WAS_BUILT,
    SENT_BACK: SENDING_BACK_NEEDS_A_NOTE,
}
DONE_NEEDS_A_CHECK = (
    "Request **#{request_id}** is **{status}**, and a request only finishes once somebody has "
    "checked it, so nothing was changed. **Ready to check** on its card marks it ready — what was "
    "built, and how to try it — and **Accept** finishes it after that. The buttons are on the "
    "`/request` panel and on the site."
)
REVIEW_BY_SOMEBODY_ELSE = (
    "You are the one who marked request **#{request_id}** ready to check, and this server asks "
    "somebody else on staff to check it, so nothing was changed. Ask another staffer to press "
    "Accept, or a Lead can turn `request_review_by_other` off if one pair of eyes is enough."
)
NOT_READY_TO_CHECK = (
    "Request **#{request_id}** is **{status}**, not ready to check, so there was nothing to "
    "{doing}. **Ready to check** on its card is what puts one there."
)
NOT_ON_HOLD = (
    "Request **#{request_id}** is **{status}**, not on hold, so there was nothing to resume. "
    "The buttons on its card are the moves it has from where it is."
)
BAD_PRIORITY = (
    "**{given}** is not a priority Black Bloc can read, so nothing was changed. Send a whole "
    f"number from 0 to {PRIORITY_MAX}, or nothing at all to leave it unranked."
)
COMMENT_NEEDS_TEXT = (
    "There is nothing to add, so no comment was left. Type what you want on the request and send "
    "it again."
)
WITHDRAWN_SAID = "Request **#{request_id}** is withdrawn. Nobody will pick it up now."
CHECK_ASKED_DM = "Request **#{request_id}** — {who} has been asked by DM to try it."
CHECK_ASKED_CHANNEL = (
    "Request **#{request_id}** — {who}'s DMs are closed, so they were pinged in the request "
    "channel instead."
)
CHECK_ASKED_NOBODY = (
    "Request **#{request_id}** — {who}'s DMs are closed and the channel fallback is off, so "
    "nobody was told. A Lead can turn `request_check_fallback_channel` on."
)
CHECK_ASKED_DESCRIPTION = (
    "Try it and tell {asked_by} how it went — say what works and what does not. Staff mark it "
    "done once you are happy."
)
FILED = (
    "Filed as **#{request_id}** — staff will see it on the site. You will get a DM every time it "
    "moves."
)
NOTHING_FILED_YET = "Nothing has been filed yet — `/request` puts the first one in."
NOTHING_OPEN = "Nothing is open — every request has been finished, declined or withdrawn."
NOTHING_OF_YOURS = "You have not filed a request yet — `/request` puts one in."
PANEL_TITLE = "Requests"
PANEL_INTRO = "Ask the server for something, or see where what you already asked for has got to."
PANEL_EMPTY = "You have not asked for anything yet."
PANEL_TIMEOUT_FOOTER = "This panel has gone quiet — run /request again"
ACCEPT_NEEDS_SOMEBODY_ELSE = "Only somebody other than {who} may accept this one."
PICK_A_REQUEST = "Pick a request…"
PICK_CAPPED = CAPPED_PLACEHOLDER
TAKE_ONE_BACK = "Take one back…"

MOVE_LINE: dict[str, str] = {
    FILED_LOOK: "New request **#{request_id}** from {who}: {what}",
    IN_PROGRESS: "Request **#{request_id}** from {who} is being worked on: {what}",
    REVIEW: "Request **#{request_id}** from {who} is ready to check: {what}",
    SENT_BACK: "Request **#{request_id}** from {who} was sent back — {note}",
    DONE: "Request **#{request_id}** from {who} is done: {what}",
    HOLD: "Request **#{request_id}** from {who} is on hold — {reason}",
    DECLINED: "Request **#{request_id}** from {who} was declined — {reason}",
    MOVED: "Request **#{request_id}** from {who} moved on: {what}",
    CHECK_ASKED: (
        "Request **#{request_id}** from {who} — they have been asked to check it: {what}"
    ),
}
NOTIFY_SKIPPED_KIND = "request.notify_skipped_test_mode"
NOTIFY_FAILED_KIND = "request.notify_failed"
STATUS_CHANNEL_KEY = "request_status_channel_id"
NOTIFY_CHANNEL_KEY = "request_notify_channel_id"
FORUM_CHANNEL_KEY = "request_forum_channel_id"
FORUM_CHANNEL_NAME = "requests"
FORUM_TOPIC = (
    "Black Bloc requests — one post per request. The card in each post is where staff move it."
)
FORUM_OPEN_TAG = "open"
FORUM_PICKED_UP_TAG = "picked up"
FORUM_READY_TAG = "ready to check"
FORUM_HOLD_TAG = "on hold"
FORUM_DONE_TAG = "done"
FORUM_DECLINED_TAG = "declined"
FORUM_MOVED_TAG = "moved"
FORUM_TAG_NAMES = (
    FORUM_OPEN_TAG,
    FORUM_PICKED_UP_TAG,
    FORUM_READY_TAG,
    FORUM_HOLD_TAG,
    FORUM_DONE_TAG,
    FORUM_DECLINED_TAG,
    FORUM_MOVED_TAG,
)
FORUM_TAG_EMOJI: dict[str, str] = {
    FORUM_OPEN_TAG: "\N{LARGE GREEN CIRCLE}",
    FORUM_PICKED_UP_TAG: "\N{LARGE YELLOW CIRCLE}",
    FORUM_READY_TAG: "\N{LEFT-POINTING MAGNIFYING GLASS}",
    FORUM_HOLD_TAG: "\N{DOUBLE VERTICAL BAR}",
    FORUM_DONE_TAG: "\N{WHITE HEAVY CHECK MARK}",
    FORUM_DECLINED_TAG: "\N{CROSS MARK}",
    FORUM_MOVED_TAG: "\N{BLACK RIGHTWARDS ARROW}",
}
FORUM_TAG_FOR: dict[str, str] = {
    OPEN: FORUM_OPEN_TAG,
    IN_PROGRESS: FORUM_PICKED_UP_TAG,
    REVIEW: FORUM_READY_TAG,
    HOLD: FORUM_HOLD_TAG,
    DONE: FORUM_DONE_TAG,
    DECLINED: FORUM_DECLINED_TAG,
    MOVED: FORUM_MOVED_TAG,
}
FORUM_ARCHIVE_STATUSES = (DONE, DECLINED, MOVED)
FORUM_AUTO_ARCHIVE_MINUTES = AUTO_ARCHIVE_MINUTES
ADOPTS_POSTS_KEY = "request_forum_adopts_posts"
SOURCE_PANEL = "panel"
SOURCE_FORUM = "forum"
SOURCE_EVENT = "event"
SOURCE_TICKET = "ticket"
ADOPTED_WHY = "(filed from a forum post)"
ADOPTED_NOT_YOURS_TO_FILE = (
    "{who} — this post was not turned into a request, because only staff may file one on this "
    "server at the moment. Nothing here has been deleted. File it with `/request`, or ask staff "
    "to put it in for you; a Lead can set **request_who_can_file** to everyone instead."
)
ADOPTED_REQUESTS_OFF = (
    "{who} — this post was not turned into a request, because requests are turned off on this "
    "server. Nothing here has been deleted. A Lead turns them back on with `/settings` ▸ **Turn "
    "a feature back on…** — ask one, or say what you need in here in the meantime."
)

EMBED_COLOURS: dict[str, int] = {
    FILED_LOOK: 0x5865F2,
    IN_PROGRESS: 0xFEE75C,
    REVIEW: 0x1ABC9C,
    SENT_BACK: 0xE67E22,
    DONE: 0x57F287,
    HOLD: 0x99AAB5,
    DECLINED: 0xED4245,
    MOVED: 0x9B59B6,
    CHECK_ASKED: 0x3498DB,
}
EMBED_TITLES: dict[str, str] = {
    FILED_LOOK: "New request #{request_id}",
    IN_PROGRESS: "Request #{request_id} is being worked on",
    REVIEW: "Request #{request_id} is ready to check 🔎",
    SENT_BACK: "Request #{request_id} was sent back",
    DONE: "Request #{request_id} is done ✅",
    HOLD: "Request #{request_id} is on hold",
    DECLINED: "Request #{request_id} was declined",
    MOVED: "Request #{request_id} moved on",
    CHECK_ASKED: "Request #{request_id} is ready for you to try 🙌",
}
EMBED_FIELDS: dict[str, tuple[str, ...]] = {
    FILED_LOOK: ("what", "why", "requester", "due"),
    IN_PROGRESS: ("what", "requester", "assignee"),
    REVIEW: ("what", "built", "how_to_test", "ready_by", "requester", "asked"),
    SENT_BACK: ("what", "needs_doing", "sent_back_by", "ready_by"),
    DONE: ("what", "built", "how_to_test", "accepted_by", "requester", "asked"),
    HOLD: ("what", "waiting", "was", "requester"),
    DECLINED: ("what", "reason", "requester"),
    MOVED: ("what", "moved_to", "requester"),
    CHECK_ASKED: ("what", "built", "how_to_test", "ready_by", "asked_by"),
}
FIELD_LABELS: dict[str, str] = {
    "what": "Asked for",
    "why": "Why",
    "built": "What was built",
    "how_to_test": "How to test",
    "needs_doing": "What needs doing",
    "waiting": "Why it is waiting",
    "reason": "Why",
    "moved_to": "Now",
    "requester": "Requested by",
    "assignee": "Assignee",
    "ready_by": "Marked ready by",
    "accepted_by": "Accepted by",
    "sent_back_by": "Sent back by",
    "due": "Due",
    "was": "Was",
    "asked": "Asked to check",
    "asked_by": "Asked by",
}
INLINE_FIELDS = frozenset(
    {
        "requester",
        "assignee",
        "ready_by",
        "accepted_by",
        "sent_back_by",
        "due",
        "was",
        "asked",
        "asked_by",
    }
)
EMBED_FOOTER = "Black Bloc · requests"
SITE_BUTTON = "Open on the site"
REQUEST_ANCHOR = "{origin}/" + FEATURE_PAGES["request"] + "#r-{request_id}"


class RequestError(ValueError):
    """Something a person typed cannot be stored; the message is the sentence they see."""


def clamp(text: Any, limit: int) -> str:
    return str(text or "").strip()[:limit]


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def parse_due(raw: Any) -> str | None:
    """`YYYY-MM-DD` or nothing; anything else is a sentence, never a silent drop."""
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        found = date.fromisoformat(text)
    except ValueError:
        raise RequestError(BAD_DUE.format(given=clamp(text, 40))) from None
    return found.isoformat()


def due_stamp(due_on: Any, tz_name: Any = DEFAULT_TZ) -> str | None:
    """`<t:…:D>` from local midnight in the server's zone; the stored value stays a date."""
    if not due_on:
        return None
    try:
        found = date.fromisoformat(str(due_on))
    except ValueError:
        return None
    at = datetime(found.year, found.month, found.day, tzinfo=zone(tz_name) or UTC)
    return f"<t:{int(at.timestamp())}:D>"


def wanted_priority(given: Any) -> int | None:
    if given is None or given == "":
        return None
    try:
        number = int(given)
    except (TypeError, ValueError):
        raise RequestError(BAD_PRIORITY.format(given=clamp(given, 40))) from None
    if isinstance(given, bool) or number < 0 or number > PRIORITY_MAX:
        raise RequestError(BAD_PRIORITY.format(given=clamp(given, 40)))
    return number


def moves_from(status: Any) -> tuple[str, ...]:
    """The one table every path asks — slash, web and tests alike."""
    return tuple(sorted(TRANSITIONS.get(str(status or ""), frozenset())))


def can_move(status: Any, wanted: Any) -> bool:
    return str(wanted or "") in TRANSITIONS.get(str(status or ""), frozenset())


def moves_sentence(status: Any) -> str:
    """A refusal always says where a request CAN go from where it is."""
    found = moves_from(status)
    if not found:
        return NO_MOVES_LEFT.format(status=STATUS_WORDS.get(str(status), str(status)))
    return MOVES_ARE.format(
        status=STATUS_WORDS.get(str(status), str(status)),
        moves=", ".join(f"**{one}**" for one in found),
    )


def wanted_status(given: Any) -> str:
    text = str(given or "").strip().lower()
    if text not in STAFF_STATUSES:
        raise RequestError(
            UNKNOWN_STATUS.format(given=clamp(given, 40), known=", ".join(STAFF_STATUSES))
        )
    return text


def look_of(was: Any, status: Any) -> str:
    """`sent_back` is a card look, not a state — the row is in progress again, from review."""
    where, to = str(was or ""), str(status or "")
    return SENT_BACK if to == IN_PROGRESS and where == REVIEW else to


def checked_move(
    request_id: Any,
    status: Any,
    wanted: Any,
    reason: Any = "",
    *,
    built: Any = "",
    note: Any = "",
) -> str:
    """The whole gate in one place: known state, a legal move, and the words a move is owed."""
    where = str(status or "")
    to = wanted_status(wanted)
    if where == to:
        raise RequestError(
            ALREADY_THAT.format(
                request_id=request_id, status=STATUS_WORDS.get(where, where)
            )
        )
    if not can_move(where, to):
        if to == DONE and where in OPEN_STATUSES:
            raise RequestError(
                DONE_NEEDS_A_CHECK.format(
                    request_id=request_id, status=STATUS_WORDS.get(where, where)
                )
            )
        raise RequestError(
            NO_SUCH_MOVE.format(
                request_id=request_id,
                status=STATUS_WORDS.get(where, where),
                wanted=to,
                allowed=moves_sentence(where),
            )
        )
    if to in NEEDS_A_REASON and not str(reason or "").strip():
        raise RequestError(REASON_NEEDED[to])
    look = look_of(where, to)
    owed = {REVIEW: built, SENT_BACK: note}.get(look)
    if look in TEXT_NEEDED and not str(owed or "").strip():
        raise RequestError(TEXT_NEEDED[look].format(request_id=request_id))
    return to


class MoveButton(NamedTuple):
    action: str
    label: str
    style: str
    needs_modal: bool = False


CARD_BUTTONS: dict[str, tuple[MoveButton, ...]] = {
    OPEN: (
        MoveButton("pickup", "Pick up", "primary"),
        MoveButton("hold", "Hold", "secondary", needs_modal=True),
        MoveButton("decline", "Decline", "danger", needs_modal=True),
    ),
    IN_PROGRESS: (
        MoveButton("ready", "Ready to check", "primary", needs_modal=True),
        MoveButton("hold", "Hold", "secondary", needs_modal=True),
        MoveButton("decline", "Decline", "danger", needs_modal=True),
    ),
    REVIEW: (
        MoveButton("accept", "Accept", "success"),
        MoveButton("check", "Ask them to check", "primary"),
        MoveButton("sendback", "Send back", "secondary", needs_modal=True),
        MoveButton("hold", "Hold", "secondary", needs_modal=True),
        MoveButton("decline", "Decline", "danger", needs_modal=True),
    ),
    HOLD: (
        MoveButton("resume", "Resume", "primary"),
        MoveButton("decline", "Decline", "danger", needs_modal=True),
    ),
    DONE: (),
    DECLINED: (),
    WITHDRAWN: (),
    MOVED: (),
}


def card_buttons(status: Any, *, may_accept_here: bool = True) -> tuple[MoveButton, ...]:
    found = CARD_BUTTONS.get(str(status or ""), ())
    if may_accept_here:
        return found
    return tuple(one for one in found if one.action != "accept")


MOVE_BY_ACTION: dict[str, MoveButton] = {
    one.action: one for moves in CARD_BUTTONS.values() for one in moves
}
MOVE_ACTIONS = tuple(MOVE_BY_ACTION)
ROW_CAP = 5


def post_move_custom_id(request_id: Any, action: Any) -> str:
    """What a move button on a forum post is called, so a restart can rebuild it from the id."""
    return f"request:{int(request_id)}:{action}"


def post_buttons_on(store: Any, guild_id: int) -> bool:
    return bool(store.get(guild_id, POST_BUTTONS_KEY))


def card_footer_override(status: Any, ready_by: Any, may_accept_here: bool) -> str | None:
    """When the default `EMBED_FOOTER` is not the whole story: why Accept is missing, or why
    nothing moves any more."""
    text = str(status or "")
    if text == REVIEW and not may_accept_here:
        return ACCEPT_NEEDS_SOMEBODY_ELSE.format(who=mention(ready_by))
    if not CARD_BUTTONS.get(text):
        return NO_MOVES_LEFT.format(status=STATUS_WORDS.get(text, text))
    return None


def look_for_status(status: Any) -> str:
    """The card look for a row's own status: itself, except `open`, which reads as `filed`."""
    text = str(status or "")
    return FILED_LOOK if text == OPEN else text


def option_label(row: Any, *, with_status: bool = True) -> str:
    """A select option's label, clamped to Discord's 100-character cap."""
    found = str(row_value(row, "status") or "")
    return library_option_label(
        row_value(row, "id", "?"),
        STATUS_WORDS.get(found, found) if with_status else None,
        row_value(row, "what"),
        SELECT_OPTION_LIMIT,
    )


def pick_placeholder(shown: int, total: int) -> str:
    return capped_placeholder(shown, total, pick=PICK_A_REQUEST, capped=PICK_CAPPED)


COUNT_STATUSES = (OPEN, IN_PROGRESS, REVIEW, HOLD)


def counts_line(counts: dict[str, int]) -> str:
    return " · ".join(
        f"**{counts.get(status, 0)}** {STATUS_WORDS[status]}" for status in COUNT_STATUSES
    )


def site_page_url(origin: Any) -> str | None:
    return library_site_page_url(origin, "request")


def panel_minutes(store: Any, guild_id: int) -> int:
    return library_panel_minutes(store, guild_id, PANEL_MINUTES_KEY)


def panel_shows_own_list(store: Any, guild_id: int) -> bool:
    return bool(store.get(guild_id, PANEL_OWN_LIST_KEY))


def wanted_statuses(given: Any) -> tuple[str, ...]:
    wanted = tuple(part.strip() for part in str(given or "").split(",") if part.strip())
    for part in wanted:
        if part not in STATUSES:
            raise RequestError(
                UNKNOWN_STATUS.format(given=clamp(part, 40), known=", ".join(STATUSES))
            )
    return wanted or STATUSES


def checked_fields(what: Any, why: Any, due: Any) -> tuple[str, str, str | None]:
    """The three the modal and the site both send, refused in the order a person meets them."""
    kept_what = clamp(what, WHAT_LIMIT)
    if not kept_what:
        raise RequestError(NEEDS_WHAT)
    kept_why = clamp(why, WHY_LIMIT)
    if not kept_why:
        raise RequestError(NEEDS_WHY)
    return kept_what, kept_why, parse_due(due)


def requests_are_on(store: Any, guild_id: int) -> bool:
    return store.get(guild_id, "request_mode") != "off"


def everyone_may_file(store: Any, guild_id: int) -> bool:
    return store.get(guild_id, "request_who_can_file") != "staff"


def dms_on_decision(store: Any, guild_id: int) -> bool:
    return bool(store.get(guild_id, "request_dm_on_decision"))


def status_channel_id(store: Any, guild_id: int) -> Any:
    """Its own channel if the server set one, otherwise the one filings already go to."""
    return store.get(guild_id, STATUS_CHANNEL_KEY) or store.get(guild_id, NOTIFY_CHANNEL_KEY)


def forum_channel_id(store: Any, guild_id: int) -> Any:
    """Blank keeps today's behaviour: one line in the notify channel, no post of its own."""
    return store.get(guild_id, FORUM_CHANNEL_KEY)


def forum_adopts_posts(store: Any, guild_id: int) -> bool:
    return bool(store.get(guild_id, ADOPTS_POSTS_KEY))


def adopted_fields(title: Any, said: Any) -> tuple[str, str]:
    """What a hand-made post asks for: its title, and its opening message or a stand-in."""
    return (clamp(title, WHAT_LIMIT), clamp(said, WHY_LIMIT) or ADOPTED_WHY)


def forum_tags(names: Any = FORUM_TAG_NAMES) -> list[discord.ForumTag]:
    """The tags a request forum is made with; their ids live in the forum, never in a key."""
    return library_forum_tags(names, FORUM_TAG_EMOJI)


def tags_for_status(forum: Any, status: Any) -> list[Any]:
    """The one tag a request post wears; a status with no tag, or a forum without it, wears none."""
    found = tag_named(forum, FORUM_TAG_FOR.get(str(status or "")))
    return [found] if found is not None else []


def archives_at(status: Any) -> bool:
    return str(status or "") in FORUM_ARCHIVE_STATUSES


def post_title(row: Any) -> str:
    """The post's own name: the request's number and its one-line summary, nothing else."""
    said = clamp(row_value(row, "what"), TITLE_LIMIT)
    return f"#{row_value(row, 'id', '?')} {said}"[:NAME_LIMIT]


def channel_moves(store: Any, guild_id: int) -> tuple[str, ...]:
    found = store.get(guild_id, CHANNEL_MOVES_KEY)
    if not isinstance(found, list | tuple):
        return CHANNEL_LOOKS
    return tuple(str(one) for one in found if str(one) in CHANNEL_LOOKS)


def posts_a_card(store: Any, guild_id: int, look: str) -> bool:
    return look in channel_moves(store, guild_id)


def card_will_post(store: Any, guild_id: int, look: str) -> bool:
    """The card is the Discord record of a move; the raw log line stays off Discord beside one."""
    return posts_a_card(store, guild_id, look) and bool(status_channel_id(store, guild_id))


def review_by_other(store: Any, guild_id: int) -> bool:
    return bool(store.get(guild_id, REVIEW_BY_OTHER_KEY))


def check_falls_back(store: Any, guild_id: int) -> bool:
    return bool(store.get(guild_id, CHECK_FALLBACK_KEY))


def checks_on_ready(store: Any, guild_id: int) -> bool:
    return bool(store.get(guild_id, CHECK_ON_READY_KEY))


def may_accept(store: Any, guild_id: int, row: Any, actor: Any) -> bool:
    """False only when the server asks for a second pair of eyes and this is the first pair."""
    if not review_by_other(store, guild_id):
        return True
    marked = row_value(row, "ready_by")
    who = getattr(actor, "id", None)
    return marked is None or who is None or int(marked) != int(who)


def held_words(row: Any) -> str:
    found = row_value(row, "held_from")
    return STATUS_WORDS.get(str(found or ""), str(found or "")) if found else ""


def row_value(row: Any, name: str, fallback: Any = None) -> Any:
    """A column a schema-22 file has not grown yet reads as nothing, never as a crash."""
    try:
        return row[name]
    except (KeyError, IndexError, TypeError):
        return fallback


def summary_line(row: Any) -> str:
    due = due_stamp(row["due_on"])
    when = f" · due {due}" if due else ""
    where = STATUS_WORDS.get(row["status"], row["status"])
    was = held_words(row)
    held = f" (was: {was})" if row["status"] == HOLD and was else ""
    return f"**#{row['id']}** {clamp(row['what'], 70)} — {where}{held}{when}"


def mention(user_id: Any) -> str:
    return f"<@{int(user_id)}>" if user_id else ""


def moment(row: Any, look: str) -> datetime:
    """The move's own time, so a card is stamped when it happened and not when it rendered."""
    column = {FILED_LOOK: "created_at", CHECK_ASKED: "check_asked_at"}.get(look, "decided_at")
    raw = row_value(row, column)
    try:
        found = datetime.fromisoformat(str(raw or ""))
    except ValueError:
        return datetime.now(UTC)
    return found if found.tzinfo is not None else found.replace(tzinfo=UTC)


def asked_stamp(row: Any) -> str:
    """Who last asked the requester to check, and when — empty on a card nobody has asked on."""
    raw = row_value(row, "check_asked_at")
    if not raw:
        return ""
    try:
        at = datetime.fromisoformat(str(raw))
    except ValueError:
        return mention(row_value(row, "check_asked_by"))
    if at.tzinfo is None:
        at = at.replace(tzinfo=UTC)
    return f"{mention(row_value(row, 'check_asked_by'))} · <t:{int(at.timestamp())}:R>"


def moved_words(row: Any) -> str:
    """Where a moved request went, bolded for a card; `handoff` owns the words."""
    from .handoff import moved_words as said

    found = said(row_value(row, "moved_to"))
    return found.replace("#", "**#") + "**" if found else ""


def field_value(row: Any, name: str) -> str:
    """One field's text; an empty one is left off the card rather than printed as nothing."""
    found = {
        "moved_to": moved_words(row),
        "what": row_value(row, "what"),
        "why": row_value(row, "why"),
        "built": row_value(row, "built"),
        "how_to_test": row_value(row, "how_to_test"),
        "needs_doing": row_value(row, "sent_back_reason"),
        "waiting": row_value(row, "decline_reason"),
        "reason": row_value(row, "decline_reason"),
        "requester": mention(row_value(row, "user_id")),
        "assignee": mention(row_value(row, "assignee_id")),
        "ready_by": mention(row_value(row, "ready_by")),
        "accepted_by": mention(row_value(row, "decided_by")),
        "sent_back_by": mention(row_value(row, "decided_by")),
        "due": due_stamp(row_value(row, "due_on")) or "",
        "was": held_words(row),
        "asked": asked_stamp(row),
        "asked_by": mention(row_value(row, "check_asked_by")),
    }.get(name, "")
    return clamp(found, FIELD_LIMIT)


def request_url(origin: Any, request_id: Any) -> str:
    return REQUEST_ANCHOR.format(origin=str(origin or "").rstrip("/"), request_id=request_id)


def request_embed(row: Any, *, move: str, origin: Any = "", guild: Any = None) -> discord.Embed:
    """One builder, seven looks — the channel card and the DM are the same rendering."""
    look = move if move in EMBED_TITLES else IN_PROGRESS
    request_id = row_value(row, "id", "?")
    embed = discord.Embed(
        title=clamp(EMBED_TITLES[look].format(request_id=request_id), TITLE_LIMIT),
        colour=discord.Colour(EMBED_COLOURS[look]),
        timestamp=moment(row, look),
    )
    name = getattr(guild, "name", None)
    if name:
        embed.set_author(name=clamp(name, TITLE_LIMIT))
    if look == CHECK_ASKED:
        embed.description = CHECK_ASKED_DESCRIPTION.format(
            asked_by=mention(row_value(row, "check_asked_by")) or "staff"
        )
    for one in EMBED_FIELDS[look]:
        text = field_value(row, one)
        if text:
            embed.add_field(name=FIELD_LABELS[one], value=text, inline=one in INLINE_FIELDS)
    embed.set_footer(text=EMBED_FOOTER)
    return embed


def site_button(origin: Any, request_id: Any, row: int = 0) -> discord.ui.Button | None:
    """The link to a request's own anchor; no origin means no button, never a bad link."""
    if not str(origin or "").strip():
        return None
    return discord.ui.Button(
        style=discord.ButtonStyle.link,
        label=SITE_BUTTON,
        url=request_url(origin, request_id),
        row=row,
    )


def site_view(origin: Any, request_id: Any) -> discord.ui.View | None:
    button = site_button(origin, request_id)
    if button is None:
        return None
    view = discord.ui.View(timeout=None)
    view.add_item(button)
    return view


def move_line(row: Any, look: str) -> str:
    """The plain one-liner the server log keeps when a card is skipped or refused."""
    template = MOVE_LINE.get(look)
    if template is None:
        return ""
    return template.format(
        request_id=row_value(row, "id", "?"),
        who=mention(row_value(row, "user_id")) or "somebody",
        what=clamp(row_value(row, "what"), 200),
        reason=clamp(row_value(row, "decline_reason"), 200) or "no reason was given",
        note=clamp(row_value(row, "sent_back_reason"), 200) or "no note was left",
    )


def page_of(rows: list[Any], page: int, per_page: int = LIST_PAGE) -> tuple[list[Any], int, int]:
    """(the rows on that page, the page actually shown, how many pages there are)."""
    pages = max(1, -(-len(rows) // per_page))
    at = max(1, min(int(page or 1), pages))
    start = (at - 1) * per_page
    return (rows[start : start + per_page], at, pages)


async def create_request(
    db: Any,
    guild_id: int,
    user_id: int,
    *,
    what: str,
    why: str,
    due_on: str | None,
    status: str = OPEN,
    decided_by: int | None = None,
    source: str = SOURCE_PANEL,
) -> int | None:
    decided_at = now_iso() if decided_by is not None else None
    cur = await db.conn.execute(
        "INSERT INTO requests(guild_id, user_id, what, why, due_on, status, created_at, "
        "decided_by, decided_at, source) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            guild_id,
            user_id,
            what,
            why,
            due_on,
            status,
            now_iso(),
            decided_by,
            decided_at,
            source,
        ),
    )
    await db.conn.commit()
    return cur.lastrowid


async def get_request(db: Any, request_id: int) -> Any:
    cur = await db.conn.execute("SELECT * FROM requests WHERE id = ?", (request_id,))
    return await cur.fetchone()


async def request_for_thread(db: Any, guild_id: int, thread_id: int) -> Any:
    """The row a forum post already belongs to; `None` is what makes adopting it safe."""
    cur = await db.conn.execute(
        "SELECT * FROM requests WHERE guild_id = ? AND thread_id = ?",
        (guild_id, int(thread_id)),
    )
    return await cur.fetchone()


UNASSIGNED = "none"


def _where(
    guild_id: int,
    *,
    statuses: Any = None,
    assignee_id: Any = None,
    user_id: int | None = None,
    query: str = "",
    named: Any = None,
) -> tuple[str, list[Any]]:
    """`assignee_id=UNASSIGNED` is the board's Unassigned column; `named` are id matches for `q`."""
    clauses = ["guild_id = ?"]
    params: list[Any] = [guild_id]
    if statuses:
        clauses.append(f"status IN ({', '.join('?' for _ in statuses)})")
        params.extend(statuses)
    if assignee_id == UNASSIGNED:
        clauses.append("assignee_id IS NULL")
    elif assignee_id is not None:
        clauses.append("assignee_id = ?")
        params.append(assignee_id)
    if user_id is not None:
        clauses.append("user_id = ?")
        params.append(user_id)
    if query:
        like = f"%{query}%"
        found = [int(one) for one in named or ()]
        by_name = f" OR user_id IN ({', '.join('?' for _ in found)})" if found else ""
        clauses.append(f"(what LIKE ? OR why LIKE ? OR notes LIKE ?{by_name})")
        params.extend([like, like, like, *found])
    return (" AND ".join(clauses), params)


async def list_requests(
    db: Any,
    guild_id: int,
    *,
    statuses: Any = None,
    assignee_id: Any = None,
    user_id: int | None = None,
    query: str = "",
    named: Any = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[Any]:
    """Pending first, then newest; the order the requests page and the `/request` panel show."""
    where, params = _where(
        guild_id,
        statuses=statuses,
        assignee_id=assignee_id,
        user_id=user_id,
        query=query,
        named=named,
    )
    tail = ""
    if limit is not None:
        tail = " LIMIT ? OFFSET ?"
        params = [*params, int(limit), int(offset)]
    cur = await db.conn.execute(
        f"SELECT * FROM requests WHERE {where} "
        f"ORDER BY (status <> '{OPEN}'), id DESC{tail}",
        tuple(params),
    )
    return list(await cur.fetchall())


async def count_requests(
    db: Any,
    guild_id: int,
    *,
    statuses: Any = None,
    assignee_id: Any = None,
    user_id: int | None = None,
    query: str = "",
    named: Any = None,
) -> int:
    where, params = _where(
        guild_id,
        statuses=statuses,
        assignee_id=assignee_id,
        user_id=user_id,
        query=query,
        named=named,
    )
    cur = await db.conn.execute(
        f"SELECT COUNT(*) AS found FROM requests WHERE {where}", tuple(params)
    )
    row = await cur.fetchone()
    return int(row["found"]) if row is not None else 0


async def set_status(
    db: Any,
    request_id: int,
    status: str,
    *,
    decided_by: int | None = None,
    decline_reason: str | None = None,
    was: str | None = None,
    ready_by: int | None = None,
    sent_back_reason: str | None = None,
) -> None:
    """Every column a move rewrites, in one place; a column with no rule for it is left alone."""
    at = now_iso()
    where = str(was or "")
    look = look_of(where, status)
    values: dict[str, Any] = {
        "status": status,
        "decline_reason": decline_reason if status in NEEDS_A_REASON else None,
        "held_from": (where or None) if status == HOLD else None,
    }
    if decided_by is not None:
        values["decided_by"] = decided_by
        values["decided_at"] = at
    if status == DONE:
        values["done_at"] = at
    if status == REVIEW:
        values["ready_by"] = ready_by
        values["sent_back_reason"] = None
    elif look == SENT_BACK:
        values["sent_back_reason"] = sent_back_reason or None
    sets = ", ".join(f"{name} = ?" for name in values)
    await db.conn.execute(
        f"UPDATE requests SET {sets} WHERE id = ?", (*values.values(), request_id)
    )
    await db.conn.commit()


SETTABLE_FIELDS = ("assignee_id", "priority", "notes", "built", "how_to_test")


async def set_fields(
    db: Any,
    request_id: int,
    *,
    assignee_id: Any = ...,
    priority: Any = ...,
    notes: Any = ...,
    built: Any = ...,
    how_to_test: Any = ...,
) -> list[str]:
    """Only the fields actually sent are written; `...` means 'leave it as it is'."""
    given = dict(
        zip(
            SETTABLE_FIELDS,
            (assignee_id, priority, notes, built, how_to_test),
            strict=True,
        )
    )
    wanted = {name: value for name, value in given.items() if value is not ...}
    if not wanted:
        return []
    sets = ", ".join(f"{name} = ?" for name in wanted)
    await db.conn.execute(
        f"UPDATE requests SET {sets} WHERE id = ?", (*wanted.values(), request_id)
    )
    await db.conn.commit()
    return list(wanted)


async def set_check_asked(db: Any, request_id: int, who: int | None, at: str) -> None:
    """Who last asked the requester to try it, and when; asking again simply overwrites both."""
    await db.conn.execute(
        "UPDATE requests SET check_asked_by = ?, check_asked_at = ? WHERE id = ?",
        (who, at, request_id),
    )
    await db.conn.commit()


async def set_message(db: Any, request_id: int, message_id: int | None) -> None:
    await db.conn.execute(
        "UPDATE requests SET message_id = ? WHERE id = ?", (message_id, request_id)
    )
    await db.conn.commit()


async def set_thread(db: Any, request_id: int, thread_id: int | None) -> None:
    await db.conn.execute(
        "UPDATE requests SET thread_id = ? WHERE id = ?", (thread_id, request_id)
    )
    await db.conn.commit()


async def add_comment(db: Any, request_id: int, author_id: int, text: str) -> int | None:
    cur = await db.conn.execute(
        "INSERT INTO request_comments(request_id, author_id, text, at) VALUES (?, ?, ?, ?)",
        (request_id, author_id, text, now_iso()),
    )
    await db.conn.commit()
    return cur.lastrowid


async def get_comment(db: Any, comment_id: int) -> Any:
    cur = await db.conn.execute("SELECT * FROM request_comments WHERE id = ?", (comment_id,))
    return await cur.fetchone()


async def comments_for(db: Any, request_id: int) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT * FROM request_comments WHERE request_id = ? ORDER BY id", (request_id,)
    )
    return list(await cur.fetchall())


async def comment_counts(db: Any, request_ids: Any) -> dict[int, int]:
    ids = [int(one) for one in request_ids]
    if not ids:
        return {}
    marks = ", ".join("?" for _ in ids)
    cur = await db.conn.execute(
        f"SELECT request_id, COUNT(*) AS found FROM request_comments "
        f"WHERE request_id IN ({marks}) GROUP BY request_id",
        tuple(ids),
    )
    return {int(row["request_id"]): int(row["found"]) for row in await cur.fetchall()}


async def open_count(db: Any, guild_id: int) -> int:
    return await count_requests(db, guild_id, statuses=(OPEN,))


def resume_target(row: Any) -> str:
    """Where Resume puts it: back where it was held from, or straight into progress."""
    found = str(row_value(row, "held_from") or "")
    return found if found in TRANSITIONS.get(HOLD, frozenset()) else IN_PROGRESS


async def withdraw_request(
    bot: Any, guild: Any, row: Any, actor: Any, *, via: str = VIA_DISCORD
) -> tuple[str, Any]:
    """The one path that takes a request back — the panel's confirm and the site's route."""
    status = row_value(row, "status")
    request_id = row_value(row, "id")
    if status not in WITHDRAWABLE:
        return (
            TOO_LATE_TO_WITHDRAW.format(
                request_id=request_id, status=STATUS_WORDS.get(status, status)
            ),
            None,
        )
    await set_status(bot.db, request_id, WITHDRAWN)
    await log_action(
        bot,
        guild,
        kind_via("request.withdrawn", via),
        actor=actor,
        target=row_value(row, "user_id"),
        details={"request_id": request_id, "via": via},
    )
    fresh = await get_request(bot.db, request_id)
    return (WITHDRAWN_SAID.format(request_id=request_id), fresh)


__all__ = [
    "CARD_BUTTONS",
    "CHANNEL_LOOKS",
    "CHECK_ASKED",
    "CHECK_ASKED_CHANNEL",
    "CHECK_ASKED_DESCRIPTION",
    "CHECK_ASKED_DM",
    "CHECK_ASKED_NOBODY",
    "CHECK_FALLBACK_KEY",
    "CHECK_ON_READY_KEY",
    "COUNT_STATUSES",
    "DECLINED",
    "DM_LOOKS",
    "DONE",
    "EMBED_COLOURS",
    "FILED_LOOK",
    "FINAL_STATUSES",
    "HOLD",
    "IN_PROGRESS",
    "LOOKS",
    "MOVE_ACTIONS",
    "MOVE_BY_ACTION",
    "MOVED",
    "MOVE_LINE",
    "MoveButton",
    "NEEDS_A_REASON",
    "NOTHING_FILED_YET",
    "NOTHING_OF_YOURS",
    "NOTHING_OPEN",
    "OPEN",
    "OPEN_STATUSES",
    "PANEL_EMPTY",
    "PANEL_INTRO",
    "PANEL_MINUTES_KEY",
    "POST_BUTTONS_KEY",
    "PANEL_OWN_LIST_KEY",
    "PANEL_TIMEOUT_FOOTER",
    "PANEL_TITLE",
    "REVIEW",
    "SELECT_CAP",
    "SELECT_OPTION_LIMIT",
    "SENT_BACK",
    "SOURCE_EVENT",
    "SOURCE_TICKET",
    "STAFF_STATUSES",
    "STATUSES",
    "STATUS_WORDS",
    "TRANSITIONS",
    "WITHDRAWABLE",
    "WITHDRAWN",
    "RequestError",
    "add_comment",
    "adopted_fields",
    "archives_at",
    "asked_stamp",
    "can_move",
    "card_buttons",
    "card_footer_override",
    "channel_moves",
    "check_falls_back",
    "checked_fields",
    "checked_move",
    "checks_on_ready",
    "clamp",
    "comment_counts",
    "comments_for",
    "count_requests",
    "counts_line",
    "create_request",
    "due_stamp",
    "field_value",
    "forum_adopts_posts",
    "forum_channel_id",
    "forum_tags",
    "get_comment",
    "get_request",
    "held_words",
    "list_requests",
    "look_for_status",
    "look_of",
    "may_accept",
    "mention",
    "moved_words",
    "move_line",
    "moves_from",
    "moves_sentence",
    "now_iso",
    "open_count",
    "option_label",
    "page_of",
    "panel_minutes",
    "panel_shows_own_list",
    "parse_due",
    "pick_placeholder",
    "card_will_post",
    "post_title",
    "request_for_thread",
    "post_buttons_on",
    "post_move_custom_id",
    "posts_a_card",
    "request_embed",
    "request_url",
    "resume_target",
    "review_by_other",
    "row_value",
    "set_check_asked",
    "set_fields",
    "set_message",
    "set_status",
    "set_thread",
    "site_button",
    "site_page_url",
    "site_view",
    "status_channel_id",
    "tag_named",
    "tags_for_status",
    "wanted_priority",
    "wanted_status",
    "wanted_statuses",
    "withdraw_request",
]
