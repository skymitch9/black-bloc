from __future__ import annotations

import logging
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands

from ...actionlog import log_action, send_logs
from ...command_errors import NETWORK_ERRORS, AnswersErrors
from ...logkinds import VIA_DISCORD, kind_via
from ...panels import (
    KEEP_IT,
    Outcome,
    Panel,
    answer,
    confirm,
    confirm_items,
    opened,
    refusal,
    retire,
    still_staff,
)
from ...panels import NoteModal as PanelNoteModal
from ...requests import (
    BUILT_LIMIT,
    CHECK_ASKED,
    CHECK_ASKED_CHANNEL,
    CHECK_ASKED_DM,
    CHECK_ASKED_NOBODY,
    COUNT_STATUSES,
    DECLINED,
    DM_LOOKS,
    DONE,
    EMBED_COLOURS,
    FILED,
    FILED_LOOK,
    FORUM_AUTO_ARCHIVE_MINUTES,
    FORUM_CHANNEL_KEY,
    FORUM_CHANNEL_NAME,
    FORUM_TOPIC,
    HOLD,
    HOW_TO_TEST_LIMIT,
    IN_PROGRESS,
    LIST_PAGE,
    LOOKS,
    NO_SUCH_REQUEST,
    NOT_ON_HOLD,
    NOT_READY_TO_CHECK,
    NOTHING_OPEN,
    NOTIFY_CHANNEL_KEY,
    NOTIFY_FAILED_KIND,
    NOTIFY_SKIPPED_KIND,
    OPEN,
    OPEN_STATUSES,
    PANEL_EMPTY,
    PANEL_INTRO,
    PANEL_TIMEOUT_FOOTER,
    PANEL_TITLE,
    REASON_LIMIT,
    REQUESTS_OFF,
    REVIEW,
    REVIEW_BY_SOMEBODY_ELSE,
    SELECT_CAP,
    SENT_BACK,
    SENT_BACK_LIMIT,
    SITE_BUTTON,
    STAFF_ONLY_FILES,
    STATUS_WORDS,
    TAKE_ONE_BACK,
    TOO_LATE_TO_WITHDRAW,
    WHAT_LIMIT,
    WHY_LIMIT,
    WITHDRAWABLE,
    RequestError,
    archives_at,
    card_buttons,
    card_footer_override,
    card_will_post,
    check_falls_back,
    checked_fields,
    checked_move,
    checks_on_ready,
    clamp,
    count_requests,
    counts_line,
    create_request,
    dms_on_decision,
    everyone_may_file,
    forum_channel_id,
    forum_tags,
    get_request,
    list_requests,
    look_for_status,
    look_of,
    may_accept,
    mention,
    move_line,
    now_iso,
    option_label,
    panel_minutes,
    panel_shows_own_list,
    pick_placeholder,
    post_title,
    posts_a_card,
    request_embed,
    requests_are_on,
    resume_target,
    row_value,
    set_check_asked,
    set_fields,
    set_message,
    set_status,
    set_thread,
    site_page_url,
    site_view,
    status_channel_id,
    summary_line,
    tags_for_status,
    withdraw_request,
)
from ...settings_store import DB_UNAVAILABLE, GUILD_ONLY, MODMAIL_CATEGORY_KEY

log = logging.getLogger(__name__)

DUE_PLACEHOLDER = "2026-09-15"
DUE_INPUT_LIMIT = 10
SET_SAID = "Request **#{request_id}** is now **{status}**."
RESUMED_SAID = "Request **#{request_id}** is off hold and back to **{status}**."
MOVE_LOOKS = tuple(one for one in LOOKS if one != FILED_LOOK)
READY_SAID = "Request **#{request_id}** is ready to check — staff will look at it."
ACCEPTED_SAID = "Request **#{request_id}** is done. The person who asked has been told."
SENT_BACK_SAID = "Request **#{request_id}** is back with whoever is working on it."
MOVE_SAID: dict[str, str] = {
    IN_PROGRESS: SET_SAID,
    REVIEW: READY_SAID,
    SENT_BACK: SENT_BACK_SAID,
    DONE: ACCEPTED_SAID,
    HOLD: SET_SAID,
    DECLINED: SET_SAID,
}
READY_MODAL_TITLE = "Ready to check"
WITHDRAW_YES = "Yes, take it back"

NOTE_TITLES: dict[str, str] = {
    "hold": "Put this on hold",
    "decline": "Decline this request",
    "sendback": "Send this back",
}
NOTE_LABELS: dict[str, str] = {
    "hold": "Why is it on hold? (sent to the asker)",
    "decline": "Why? (sent to the asker)",
    "sendback": "What's left? (sent to who marked it ready)",
}
NOTE_LIMITS: dict[str, int] = {
    "hold": REASON_LIMIT,
    "decline": REASON_LIMIT,
    "sendback": SENT_BACK_LIMIT,
}
NOTE_STATUS: dict[str, str] = {"hold": HOLD, "decline": DECLINED}
BUTTON_STYLES: dict[str, discord.ButtonStyle] = {
    "primary": discord.ButtonStyle.primary,
    "secondary": discord.ButtonStyle.secondary,
    "success": discord.ButtonStyle.success,
    "danger": discord.ButtonStyle.danger,
}
COG_NAME = "Requests"
MAKE_THE_FORUM = "Make the forum"
FORUM_EXISTS = (
    "<#{where}> is already the request forum, so nothing was made. Clear "
    "**request_forum_channel_id** on the Settings page first if you want a new one."
)
FORUM_NO_CATEGORY = (
    "**modmail_category_id** is not pointed at a category Black Bloc can see, so there is "
    "nowhere under Blackmail to make the forum. Point it at one with `/modmail` ▸ **Setup…** ▸ "
    "**Ticket category…** first."
)
FORUM_UNSUPPORTED = (
    "This server cannot be given a forum channel by Black Bloc — the library it runs on offers "
    "no way to make one here. Make a forum by hand and point **request_forum_channel_id** at it "
    "on the Settings page."
)
FORUM_FAILED_SAID = (
    "Black Bloc could not make the forum — {reason}. Check it has **Manage Channels** on the "
    "Blackmail category and try again; the log says `request.forum_failed`."
)
FORUM_MADE = (
    "<#{where}> is up: a forum under the Blackmail category, with its overwrites, and one tag "
    "for each place a request can be. Every request filed from now on gets its own post there."
)
FORUM_MADE_GUARDED = (
    " ⚠️ Black Bloc is in **test mode** and this forum is OUTSIDE the test channel — making a "
    "channel is not something the guard can see, so it was made anyway. Black Bloc claims each "
    "post in it — when it opens one and again whenever it writes to one — so the cards land "
    "there and nowhere else."
)


def guard_allows(bot: Any, channel: Any) -> bool:
    """The one place this cog asks the guard; a modal reply bypasses the patched send."""
    guard = getattr(bot, "guard", None)
    return guard is None or guard.allows_channel(channel)


def guard_refusal(bot: Any) -> str:
    guard = getattr(bot, "guard", None)
    return guard.refusal_message() if guard is not None else ""


async def dm(user: Any, **payload: Any) -> bool:
    """Whether the person actually got told."""
    send = getattr(user, "send", None)
    if send is None:
        return False
    try:
        await send(allowed_mentions=discord.AllowedMentions.none(), **payload)
    except Exception as exc:
        log.info("requests: could not DM %s: %s", getattr(user, "id", "?"), exc)
        return False
    return True


def person_told(bot: Any, guild: Any, row: Any, look: str) -> Any:
    """The requester on their own moves; the staffer who marked it ready when it comes back."""
    if look == SENT_BACK:
        return row_value(row, "ready_by")
    return row_value(row, "user_id") if look in DM_LOOKS else None


def card(bot: Any, guild: Any, row: Any, look: str) -> tuple[Any, Any]:
    """The one rendering both the channel and the DM send — embed plus its link button."""
    origin = getattr(getattr(bot, "settings", None), "origin", "")
    return (
        request_embed(row, move=look, origin=origin, guild=guild),
        site_view(origin, row_value(row, "id", "")),
    )


async def tell_person(bot: Any, guild: Any, row: Any, look: str) -> None:
    """The DM somebody is owed on a move; a failure is logged, never silent."""
    wanted = person_told(bot, guild, row, look)
    if wanted is None:
        return
    if look in DM_LOOKS and not dms_on_decision(bot.store, guild.id):
        return
    member = guild.get_member(wanted) or bot.get_user(wanted)
    embed, view = card(bot, guild, row, look)
    if await dm(member, embed=embed, view=view):
        return
    await log_action(
        bot,
        guild,
        "request.dm_failed",
        target=wanted,
        details={"request_id": row["id"], "status": look},
    )


async def post_line(
    bot: Any,
    guild: Any,
    channel_id: Any,
    row: Any,
    line: str,
    move: str,
    *,
    embed: Any = None,
    view: Any = None,
    ping: Any = None,
) -> Any:
    """One guarded card where staff watch; a channel the guard refuses is skipped, not raised."""
    if not channel_id:
        return None
    channel = bot.get_channel(channel_id) or guild.get_channel(channel_id)
    if channel is None:
        log.warning("requests: %s is not a channel Black Bloc can see", channel_id)
        return None
    if not guard_allows(bot, channel):
        log.warning("requests: test mode, so #%s never heard %r", channel_id, line)
        await log_action(
            bot,
            guild,
            NOTIFY_SKIPPED_KIND,
            details={"request_id": row["id"], "move": move, "channel_id": int(channel_id)},
        )
        return None
    allowed = (
        discord.AllowedMentions(users=[discord.Object(id=int(ping))])
        if ping
        else discord.AllowedMentions.none()
    )
    try:
        return await channel.send(
            content=mention(ping) if ping else None,
            embed=embed,
            view=view,
            allowed_mentions=allowed,
        )
    except NETWORK_ERRORS as exc:
        log.warning("requests: could not post %r for %s: %s", line, row["id"], exc)
        await log_action(
            bot,
            guild,
            NOTIFY_FAILED_KIND,
            details={
                "request_id": row["id"],
                "move": move,
                "reason": f"{type(exc).__name__}: {exc}",
            },
        )
        return None


def forum_of(bot: Any, guild: Any) -> Any:
    """The forum every request gets a post in, claimed for the guard each time it is read."""
    channel_id = forum_channel_id(bot.store, guild.id)
    if not channel_id:
        return None
    forum = bot.get_channel(channel_id) or guild.get_channel(channel_id)
    guard = getattr(bot, "guard", None)
    if forum is not None and guard is not None:
        guard.own_channel(forum)
    return forum


def thread_of(bot: Any, guild: Any, row: Any) -> Any:
    """This request's own post — claimed back on the way out, because a guard claim dies with
    the process that made it and a restart would otherwise drop every move card in silence."""
    thread_id = row_value(row, "thread_id")
    if not thread_id:
        return None
    finder = getattr(guild, "get_thread", None)
    thread = (finder(int(thread_id)) if finder is not None else None) or bot.get_channel(
        int(thread_id)
    )
    guard = getattr(bot, "guard", None)
    forum = forum_of(bot, guild)
    if guard is None or thread is None or forum is None:
        return thread
    parent = getattr(thread, "parent_id", None) or getattr(
        getattr(thread, "parent", None), "id", None
    )
    if parent == forum.id:
        guard.own_channel(thread)
    return thread


def moves_land_in(bot: Any, guild: Any, row: Any) -> Any:
    """Where a move card goes: this request's post when it has one, else the status channel."""
    thread = thread_of(bot, guild, row)
    return thread.id if thread is not None else status_channel_id(bot.store, guild.id)


async def open_forum_post(bot: Any, guild: Any, row: Any, embed: Any, view: Any) -> Any:
    """One post per request; the filed card and its buttons are its first message."""
    forum = forum_of(bot, guild)
    if forum is None:
        return None
    if not guard_allows(bot, forum.id):
        log.warning("requests: test mode, so the forum never heard request %s", row["id"])
        await log_action(
            bot,
            guild,
            NOTIFY_SKIPPED_KIND,
            details={
                "request_id": row["id"],
                "move": FILED_LOOK,
                "channel_id": int(forum.id),
            },
        )
        return None
    extra = {} if view is None else {"view": view}
    try:
        made = await forum.create_thread(
            name=post_title(row),
            content=move_line(row, FILED_LOOK),
            embed=embed,
            applied_tags=tags_for_status(forum, row_value(row, "status")),
            auto_archive_duration=FORUM_AUTO_ARCHIVE_MINUTES,
            allowed_mentions=discord.AllowedMentions.none(),
            reason=f"Black Bloc request {row['id']}",
            **extra,
        )
    except NETWORK_ERRORS as exc:
        log.warning("requests: could not open a post for %s: %s", row["id"], exc)
        await log_action(
            bot,
            guild,
            NOTIFY_FAILED_KIND,
            details={
                "request_id": row["id"],
                "move": FILED_LOOK,
                "reason": f"{type(exc).__name__}: {exc}",
            },
        )
        return None
    post = getattr(made, "thread", made)
    guard = getattr(bot, "guard", None)
    if guard is not None:
        guard.own_channel(post)
    await set_thread(bot.db, row["id"], post.id)
    starter = getattr(made, "message", None)
    if starter is not None:
        await set_message(bot.db, row["id"], starter.id)
    return post


async def retag_post(bot: Any, guild: Any, row: Any, thread: Any) -> None:
    """The post's own state: one tag for the status, and an archive once it is finished."""
    forum = getattr(thread, "parent", None) or forum_of(bot, guild)
    status = row_value(row, "status")
    wanted: dict[str, Any] = {"applied_tags": tags_for_status(forum, status)}
    if archives_at(status):
        wanted["archived"] = True
    try:
        await thread.edit(**wanted)
    except NETWORK_ERRORS as exc:
        log.warning("requests: could not re-tag the post for %s: %s", row["id"], exc)
        await log_action(
            bot,
            guild,
            NOTIFY_FAILED_KIND,
            details={
                "request_id": row["id"],
                "move": str(status),
                "reason": f"{type(exc).__name__}: {exc}",
            },
        )
        return
    guard = getattr(bot, "guard", None)
    if archives_at(status) and guard is not None:
        guard.disown_channel(thread)


async def notify(bot: Any, guild: Any, row: Any, who: Any) -> None:
    if not posts_a_card(bot.store, guild.id, FILED_LOOK):
        return
    embed, view = card(bot, guild, row, FILED_LOOK)
    if forum_of(bot, guild) is not None:
        await open_forum_post(bot, guild, row, embed, view)
        return
    message = await post_line(
        bot,
        guild,
        bot.store.get(guild.id, NOTIFY_CHANNEL_KEY),
        row,
        move_line(row, FILED_LOOK),
        FILED_LOOK,
        embed=embed,
        view=view,
    )
    if message is not None:
        await set_message(bot.db, row["id"], message.id)


async def notify_move(bot: Any, guild: Any, row: Any, look: str) -> None:
    """The channel hears every staff move, not only the filing (owner, 2026-09-02).

    With a forum, that channel is the request's own post — the card first, then the tag."""
    thread = thread_of(bot, guild, row)
    if look in MOVE_LOOKS and posts_a_card(bot.store, guild.id, look):
        embed, view = card(bot, guild, row, look)
        await post_line(
            bot,
            guild,
            thread.id if thread is not None else status_channel_id(bot.store, guild.id),
            row,
            move_line(row, look),
            look,
            embed=embed,
            view=view,
        )
    if thread is not None:
        await retag_post(bot, guild, row, thread)


async def apply_decision(
    bot: Any,
    guild: Any,
    request_id: int,
    status: str,
    actor: Any,
    reason: Any = None,
    *,
    built: Any = None,
    how_to_test: Any = None,
    note: Any = None,
    via: str = VIA_DISCORD,
) -> tuple[str, Any]:
    """(what to say, the row as it now is or None) — the one path a status moves by."""
    row = await get_request(bot.db, request_id)
    if row is None or row["guild_id"] != guild.id:
        return (NO_SUCH_REQUEST.format(request_id=request_id), None)
    kept = clamp(reason, REASON_LIMIT)
    kept_built = clamp(built, BUILT_LIMIT)
    kept_note = clamp(note, SENT_BACK_LIMIT)
    try:
        wanted = checked_move(
            request_id, row["status"], status, kept, built=kept_built, note=kept_note
        )
    except RequestError as exc:
        return (str(exc), None)
    if wanted == DONE and not may_accept(bot.store, guild.id, row, actor):
        return (REVIEW_BY_SOMEBODY_ELSE.format(request_id=request_id), None)
    look = look_of(row["status"], wanted)
    if wanted == REVIEW:
        await set_fields(
            bot.db,
            request_id,
            built=kept_built,
            how_to_test=clamp(how_to_test, HOW_TO_TEST_LIMIT) or None,
        )
    await set_status(
        bot.db,
        request_id,
        wanted,
        decided_by=getattr(actor, "id", None),
        decline_reason=kept or None,
        was=row["status"],
        ready_by=getattr(actor, "id", None),
        sent_back_reason=kept_note or None,
    )
    fresh = await get_request(bot.db, request_id)
    await log_action(
        bot,
        guild,
        kind_via(f"request.{look}", via),
        actor=actor,
        target=row["user_id"],
        reason=kept or kept_note or None,
        details={"request_id": request_id, "was": row["status"], "via": via},
        carded=card_will_post(bot.store, guild.id, look),
    )
    await tell_person(bot, guild, fresh, look)
    await notify_move(bot, guild, fresh, look)
    return (MOVE_SAID[look].format(
        request_id=request_id, status=STATUS_WORDS.get(wanted, wanted)
    ), fresh)


async def mark_ready(
    bot: Any,
    guild: Any,
    request_id: int,
    actor: Any,
    built: Any,
    how_to_test: Any = None,
    *,
    via: str = VIA_DISCORD,
) -> tuple[str, Any]:
    """The panel's Ready-to-check button and the site's — in progress into review."""
    said, fresh = await apply_decision(
        bot,
        guild,
        request_id,
        REVIEW,
        actor,
        built=built,
        how_to_test=how_to_test,
        via=via,
    )
    if fresh is not None and checks_on_ready(bot.store, guild.id):
        _, asked = await ask_check(bot, guild, request_id, actor, via=via)
        fresh = asked if asked is not None else fresh
    return (said, fresh)


async def accept(
    bot: Any, guild: Any, request_id: int, actor: Any, *, via: str = VIA_DISCORD
) -> tuple[str, Any]:
    """The panel's Accept button and the site's — review into done."""
    return await apply_decision(bot, guild, request_id, DONE, actor, via=via)


async def send_back(
    bot: Any, guild: Any, request_id: int, actor: Any, note: Any, *, via: str = VIA_DISCORD
) -> tuple[str, Any]:
    """The panel's Send back button and the site's — review into progress, with a note."""
    row = await get_request(bot.db, request_id)
    if row is None or row["guild_id"] != guild.id:
        return (NO_SUCH_REQUEST.format(request_id=request_id), None)
    if row["status"] != REVIEW:
        return (
            NOT_READY_TO_CHECK.format(
                request_id=request_id,
                status=STATUS_WORDS.get(row["status"], row["status"]),
                doing="send back",
            ),
            None,
        )
    return await apply_decision(bot, guild, request_id, IN_PROGRESS, actor, note=note, via=via)


async def resume_request(
    bot: Any, guild: Any, request_id: int, actor: Any, *, via: str = VIA_DISCORD
) -> tuple[str, Any]:
    """Off hold and back where it was held from — the panel's Resume button and the site's."""
    row = await get_request(bot.db, request_id)
    if row is None or row["guild_id"] != guild.id:
        return (NO_SUCH_REQUEST.format(request_id=request_id), None)
    if row["status"] != HOLD:
        return (
            NOT_ON_HOLD.format(
                request_id=request_id,
                status=STATUS_WORDS.get(row["status"], row["status"]),
            ),
            None,
        )
    wanted = resume_target(row)
    await set_status(
        bot.db,
        request_id,
        wanted,
        decided_by=getattr(actor, "id", None),
        ready_by=row_value(row, "ready_by"),
    )
    fresh = await get_request(bot.db, request_id)
    await log_action(
        bot,
        guild,
        kind_via("request.resumed", via),
        actor=actor,
        target=row["user_id"],
        details={"request_id": request_id, "was": HOLD, "held_from": wanted, "via": via},
        carded=card_will_post(bot.store, guild.id, wanted),
    )
    await tell_person(bot, guild, fresh, wanted)
    await notify_move(bot, guild, fresh, wanted)
    return (
        RESUMED_SAID.format(request_id=request_id, status=STATUS_WORDS.get(wanted, wanted)),
        fresh,
    )


CHECK_SAID: dict[str, str] = {
    "dm": CHECK_ASKED_DM,
    "channel": CHECK_ASKED_CHANNEL,
    "nobody": CHECK_ASKED_NOBODY,
}


async def ask_check(
    bot: Any, guild: Any, request_id: int, actor: Any, *, via: str = VIA_DISCORD
) -> tuple[str, Any]:
    """The panel's Ask-them-to-check button and the site's — the requester is told the work
    is theirs to try; the request does not move."""
    row = await get_request(bot.db, request_id)
    if row is None or row["guild_id"] != guild.id:
        return (NO_SUCH_REQUEST.format(request_id=request_id), None)
    if row["status"] != REVIEW:
        return (
            NOT_READY_TO_CHECK.format(
                request_id=request_id,
                status=STATUS_WORDS.get(row["status"], row["status"]),
                doing="ask them to check",
            ),
            None,
        )
    wanted = row["user_id"]
    await set_check_asked(bot.db, request_id, getattr(actor, "id", None), now_iso())
    fresh = await get_request(bot.db, request_id)
    embed, view = card(bot, guild, fresh, CHECK_ASKED)
    member = guild.get_member(wanted) or bot.get_user(wanted)
    told = "dm"
    if not await dm(member, embed=embed, view=view):
        told = "nobody"
        await log_action(
            bot,
            guild,
            "request.dm_failed",
            target=wanted,
            details={"request_id": request_id, "status": CHECK_ASKED},
        )
        if check_falls_back(bot.store, guild.id):
            posted = await post_line(
                bot,
                guild,
                moves_land_in(bot, guild, fresh),
                fresh,
                move_line(fresh, CHECK_ASKED),
                CHECK_ASKED,
                embed=embed,
                view=view,
                ping=wanted,
            )
            told = "channel" if posted is not None else "nobody"
    await log_action(
        bot,
        guild,
        kind_via("request.check_asked", via),
        actor=actor,
        target=wanted,
        details={"request_id": request_id, "told": told, "via": via},
        carded=told == "channel" or card_will_post(bot.store, guild.id, CHECK_ASKED),
    )
    if told != "channel":
        await notify_move(bot, guild, fresh, CHECK_ASKED)
    return (
        CHECK_SAID[told].format(request_id=request_id, who=mention(wanted)),
        fresh,
    )


async def make_forum(
    bot: Any, guild: Any, actor: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    """`/request`'s **Make the forum**: one forum under Blackmail, with a tag per place."""
    known = forum_channel_id(bot.store, guild.id)
    if known and (bot.get_channel(known) or guild.get_channel(known)) is not None:
        return refusal(FORUM_EXISTS.format(where=known), "forum_exists", 409)
    category_id = bot.store.get(guild.id, MODMAIL_CATEGORY_KEY)
    category = guild.get_channel(category_id) if category_id else None
    if category is None:
        return refusal(FORUM_NO_CATEGORY, "no_category", 409)
    create = getattr(guild, "create_forum", None)
    if create is None:
        return refusal(FORUM_UNSUPPORTED, "no_forum_api", 409)
    overwrites = dict(getattr(category, "overwrites", None) or {})
    me = getattr(guild, "me", None)
    if me is not None:
        overwrites[me] = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            manage_channels=True,
            manage_threads=True,
            send_messages_in_threads=True,
        )
    try:
        forum = await create(
            FORUM_CHANNEL_NAME,
            category=category,
            topic=FORUM_TOPIC,
            overwrites=overwrites,
            available_tags=forum_tags(),
            default_auto_archive_duration=FORUM_AUTO_ARCHIVE_MINUTES,
            reason="Black Bloc request forum",
        )
    except Exception as exc:
        log.warning("requests: could not make the forum: %s", exc)
        await log_action(
            bot,
            guild,
            "request.forum_failed",
            actor=actor,
            details={"category_id": category.id, "reason": f"{type(exc).__name__}: {exc}"},
        )
        return refusal(FORUM_FAILED_SAID.format(reason=exc), "forum_failed", 500)
    said = FORUM_MADE.format(where=forum.id)
    if getattr(bot, "guard", None) is not None:
        said += FORUM_MADE_GUARDED
    await bot.store.set(
        guild.id, FORUM_CHANNEL_KEY, forum.id, by=getattr(actor, "id", None)
    )
    await log_action(
        bot,
        guild,
        kind_via("request.forum_made", via),
        actor=actor,
        details={"channel_id": forum.id, "category_id": category.id, "via": via},
    )
    return Outcome(True, said, value=forum.id)


MOVE_FUNCS: dict[str, Any] = {
    "pickup": lambda bot, guild, rid, actor: apply_decision(bot, guild, rid, IN_PROGRESS, actor),
    "accept": lambda bot, guild, rid, actor: accept(bot, guild, rid, actor),
    "check": lambda bot, guild, rid, actor: ask_check(bot, guild, rid, actor),
    "resume": lambda bot, guild, rid, actor: resume_request(bot, guild, rid, actor),
}


def build_card(bot: Any, guild: Any, row: Any, actor: Any) -> tuple[discord.Embed, RequestView]:
    status = row_value(row, "status")
    origin = str(getattr(bot.settings, "origin", "") or "")
    embed = request_embed(row, move=look_for_status(status), origin=origin, guild=guild)
    may_accept_here = may_accept(bot.store, guild.id, row, actor)
    override = card_footer_override(status, row_value(row, "ready_by"), may_accept_here)
    if override:
        embed.set_footer(text=override)
    view = RequestView(panel_minutes(bot.store, guild.id))
    for spec in card_buttons(status, may_accept_here=may_accept_here):
        view.add_item(CardMoveButton(row_value(row, "id"), spec))
    view.add_item(BackButton())
    return embed, view


async def build_panel(bot: Any, guild: Any, actor: Any) -> tuple[discord.Embed, RequestView]:
    store = bot.store
    db = bot.db
    staff = store.is_staff(actor)
    own_rows = await list_requests(db, guild.id, user_id=actor.id)
    on = requests_are_on(store, guild.id)
    can_file = on and (everyone_may_file(store, guild.id) or staff)
    staff_rows: list[Any] = []
    total_open = 0
    counts: dict[str, int] | None = None
    if staff:
        counts = {
            status: await count_requests(db, guild.id, statuses=(status,))
            for status in COUNT_STATUSES
        }
        staff_rows = await list_requests(db, guild.id, statuses=OPEN_STATUSES, limit=SELECT_CAP)
        total_open = await count_requests(db, guild.id, statuses=OPEN_STATUSES)

    lines = [PANEL_INTRO]
    if counts is not None:
        lines.append(counts_line(counts))
    if staff or panel_shows_own_list(store, guild.id):
        if own_rows:
            lines.extend(summary_line(row) for row in own_rows[:LIST_PAGE])
        else:
            lines.append(PANEL_EMPTY)
    if not on:
        lines.append(REQUESTS_OFF)
    elif not can_file:
        lines.append(STAFF_ONLY_FILES)
    if staff and not staff_rows:
        lines.append(NOTHING_OPEN)

    embed = discord.Embed(
        title=PANEL_TITLE,
        description="\n".join(lines),
        colour=discord.Colour(EMBED_COLOURS[FILED_LOOK]),
    )
    view = RequestView(panel_minutes(store, guild.id))
    if can_file:
        view.add_item(FileButton())
    view.add_item(RefreshButton())
    page_url = site_page_url(str(getattr(bot.settings, "origin", "") or ""))
    if page_url:
        view.add_item(
            discord.ui.Button(
                style=discord.ButtonStyle.link, label=SITE_BUTTON, url=page_url, row=0
            )
        )
    withdrawable = [row for row in own_rows if row["status"] in WITHDRAWABLE]
    if withdrawable:
        view.add_item(WithdrawPick(withdrawable))
    if staff and staff_rows:
        view.add_item(RequestPick(staff_rows, total_open))
    if staff:
        view.add_item(LogsButton())
    if staff and not forum_channel_id(store, guild.id):
        view.add_item(MakeForumButton())
    return embed, view


async def render_panel(interaction: discord.Interaction, previous: Any = None) -> None:
    bot = interaction.client
    embed, view = await build_panel(bot, interaction.guild, interaction.user)
    retire(previous)
    msg = await interaction.edit_original_response(
        embed=embed,
        view=view,
        allowed_mentions=discord.AllowedMentions.none(),
    )
    view.message = msg


async def back_to_panel(interaction: discord.Interaction, previous: Any = None) -> None:
    if not await opened(interaction, staff=False):
        return
    await render_panel(interaction, previous)


async def finish_card(
    interaction: discord.Interaction,
    request_id: int,
    said: str,
    fresh: Any,
    previous: Any = None,
) -> None:
    bot = interaction.client
    row = fresh if fresh is not None else await get_request(bot.db, request_id)
    if row is None:
        await render_panel(interaction, previous)
    else:
        embed, view = build_card(bot, interaction.guild, row, interaction.user)
        retire(previous)
        msg = await interaction.edit_original_response(
            embed=embed,
            view=view,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        view.message = msg
    await interaction.followup.send(
        said, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
    )


async def open_card(
    interaction: discord.Interaction, request_id: int, previous: Any = None
) -> None:
    if not await opened(interaction, staff=False):
        return
    bot = interaction.client
    row = await get_request(bot.db, request_id)
    if row is None or row["guild_id"] != interaction.guild.id:
        await interaction.followup.send(
            NO_SUCH_REQUEST.format(request_id=request_id),
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        return
    embed, view = build_card(bot, interaction.guild, row, interaction.user)
    retire(previous)
    msg = await interaction.edit_original_response(
        embed=embed,
        view=view,
        allowed_mentions=discord.AllowedMentions.none(),
    )
    view.message = msg


async def open_withdraw_confirm(
    interaction: discord.Interaction, request_id: int, previous: Any = None
) -> None:
    if not await opened(interaction, staff=False):
        return
    bot = interaction.client
    row = await get_request(bot.db, request_id)
    theirs = row is not None and row["user_id"] == interaction.user.id
    if row is None or row["guild_id"] != interaction.guild.id or not theirs:
        await render_panel(interaction, previous)
        await interaction.followup.send(
            NO_SUCH_REQUEST.format(request_id=request_id),
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        return
    if row["status"] not in WITHDRAWABLE:
        await render_panel(interaction, previous)
        await interaction.followup.send(
            TOO_LATE_TO_WITHDRAW.format(
                request_id=request_id, status=STATUS_WORDS.get(row["status"], row["status"])
            ),
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        return
    origin = str(getattr(bot.settings, "origin", "") or "")
    embed = request_embed(
        row, move=look_for_status(row["status"]), origin=origin, guild=interaction.guild
    )
    await confirm(
        interaction,
        RequestView(panel_minutes(bot.store, interaction.guild.id)),
        embed,
        confirm_items(
            yes=WITHDRAW_YES,
            no=KEEP_IT,
            on_yes=lambda one, card: confirm_withdraw(one, request_id, card),
            on_no=back_to_panel,
        ),
        previous,
    )


async def confirm_withdraw(
    interaction: discord.Interaction, request_id: int, previous: Any = None
) -> None:
    if not await opened(interaction, staff=False):
        return
    bot = interaction.client
    row = await get_request(bot.db, request_id)
    if row is None:
        await render_panel(interaction, previous)
        return
    said, _ = await withdraw_request(bot, interaction.guild, row, interaction.user)
    await render_panel(interaction, previous)
    await interaction.followup.send(
        said, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
    )


async def run_move(
    interaction: discord.Interaction, request_id: int, action: str, previous: Any = None
) -> None:
    if not await opened(interaction, staff=False):
        return
    bot = interaction.client
    said, fresh = await MOVE_FUNCS[action](bot, interaction.guild, request_id, interaction.user)
    await finish_card(interaction, request_id, said, fresh, previous)


class RequestView(Panel):
    def __init__(self, minutes: int) -> None:
        super().__init__(minutes, footer=PANEL_TIMEOUT_FOOTER)


class FileButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label="File a request", style=discord.ButtonStyle.primary, row=0)

    async def callback(self, interaction: discord.Interaction) -> None:
        bot = interaction.client
        guild = interaction.guild
        if not requests_are_on(bot.store, guild.id):
            await answer(interaction, REQUESTS_OFF)
            return
        if not everyone_may_file(bot.store, guild.id) and not bot.store.is_staff(
            interaction.user
        ):
            await answer(interaction, STAFF_ONLY_FILES)
            return
        cog = bot.get_cog(COG_NAME)
        await interaction.response.send_modal(RequestModal(cog))


class RefreshButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label="Refresh", style=discord.ButtonStyle.secondary, row=0)

    async def callback(self, interaction: discord.Interaction) -> None:
        await back_to_panel(interaction, self.view)


class WithdrawPick(discord.ui.Select):
    def __init__(self, rows: list[Any]) -> None:
        options = [
            discord.SelectOption(
                label=option_label(row, with_status=False), value=str(row_value(row, "id"))
            )
            for row in rows[:SELECT_CAP]
        ]
        super().__init__(
            placeholder=TAKE_ONE_BACK, options=options, min_values=1, max_values=1, row=1
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await open_withdraw_confirm(interaction, int(self.values[0]), self.view)


class RequestPick(discord.ui.Select):
    def __init__(self, rows: list[Any], total: int) -> None:
        options = [
            discord.SelectOption(label=option_label(row), value=str(row_value(row, "id")))
            for row in rows
        ]
        super().__init__(
            placeholder=pick_placeholder(len(rows), total),
            options=options,
            min_values=1,
            max_values=1,
            row=2,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await open_card(interaction, int(self.values[0]), self.view)


class LogsButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label="Logs", style=discord.ButtonStyle.secondary, row=3)

    async def callback(self, interaction: discord.Interaction) -> None:
        await send_logs(interaction, "request")


class MakeForumButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label=MAKE_THE_FORUM, style=discord.ButtonStyle.secondary, row=3)

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await still_staff(interaction):
            return
        if not await opened(interaction, staff=False):
            return
        outcome = await make_forum(
            interaction.client, interaction.guild, interaction.user
        )
        await render_panel(interaction, self.view)
        await interaction.followup.send(
            outcome.message, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
        )


class BackButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label="Back", style=discord.ButtonStyle.secondary, row=1)

    async def callback(self, interaction: discord.Interaction) -> None:
        await back_to_panel(interaction, self.view)


class CardMoveButton(discord.ui.Button):
    def __init__(self, request_id: int, spec: Any) -> None:
        super().__init__(label=spec.label, style=BUTTON_STYLES[spec.style], row=0)
        self.request_id = request_id
        self.spec = spec

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await still_staff(interaction):
            return
        cog = interaction.client.get_cog(COG_NAME)
        if self.spec.action == "ready":
            row = await get_request(interaction.client.db, self.request_id)
            await interaction.response.send_modal(
                ReadyModal(cog, self.request_id, row, self.view)
            )
            return
        if self.spec.needs_modal:
            await interaction.response.send_modal(
                NoteModal(cog, self.request_id, self.spec.action, self.view)
            )
            return
        await run_move(interaction, self.request_id, self.spec.action, self.view)


class RequestModal(AnswersErrors, discord.ui.Modal, title="Ask for something"):
    what = discord.ui.TextInput(
        label="What are you asking for?",
        style=discord.TextStyle.paragraph,
        max_length=WHAT_LIMIT,
    )
    why = discord.ui.TextInput(
        label="Why is it worth doing?",
        style=discord.TextStyle.paragraph,
        max_length=WHY_LIMIT,
    )
    due = discord.ui.TextInput(
        label="Needed by — YYYY-MM-DD",
        placeholder=DUE_PLACEHOLDER,
        max_length=DUE_INPUT_LIMIT,
        required=False,
    )

    def __init__(self, cog: Requests) -> None:
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await self.cog.submit(
            interaction,
            what=str(self.what),
            why=str(self.why),
            due=str(self.due),
        )


class ReadyModal(AnswersErrors, discord.ui.Modal, title=READY_MODAL_TITLE):
    built = discord.ui.TextInput(
        label="What was built?",
        style=discord.TextStyle.paragraph,
        max_length=BUILT_LIMIT,
    )
    how_to_test = discord.ui.TextInput(
        label="How does somebody test it?",
        style=discord.TextStyle.paragraph,
        max_length=HOW_TO_TEST_LIMIT,
        required=False,
    )

    def __init__(
        self, cog: Requests, request_id: int, row: Any = None, previous: Any = None
    ) -> None:
        super().__init__()
        self.cog = cog
        self.request_id = request_id
        self.previous = previous
        self.built.default = clamp(row_value(row, "built"), BUILT_LIMIT) or None
        self.how_to_test.default = clamp(row_value(row, "how_to_test"), HOW_TO_TEST_LIMIT) or None

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await self.cog.ready_submit(
            interaction,
            self.request_id,
            built=str(self.built),
            how_to_test=str(self.how_to_test),
            previous=self.previous,
        )


class NoteModal(PanelNoteModal):
    def __init__(
        self, cog: Requests, request_id: int, kind: str, previous: Any = None
    ) -> None:
        self.cog = cog
        self.request_id = request_id
        self.kind = kind
        self.previous = previous
        super().__init__(
            title=NOTE_TITLES[kind],
            label=NOTE_LABELS[kind],
            max_length=NOTE_LIMITS[kind],
            on_submit=self.note_submit,
        )

    async def note_submit(self, interaction: discord.Interaction, text: str) -> None:
        await self.cog.note_submit(interaction, self.request_id, self.kind, text, self.previous)


class Requests(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def _database_ready(self, interaction: discord.Interaction) -> bool:
        if self.bot.db.is_connected:
            return True
        log.warning("requests: refused a command — the database is not connected")
        await answer(interaction, DB_UNAVAILABLE)
        return False

    async def _ready(self, interaction: discord.Interaction) -> bool:
        if interaction.guild is None:
            await answer(interaction, GUILD_ONLY)
            return False
        return await self._database_ready(interaction)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel) -> None:
        """Checklist 26: a forum somebody deleted is forgotten, never kept as a dead id."""
        if not self.bot.db.is_connected:
            return
        guild = channel.guild
        if channel.id != forum_channel_id(self.bot.store, guild.id):
            return
        await self.bot.store.clear(guild.id, FORUM_CHANNEL_KEY)
        await log_action(
            self.bot, guild, "request.forum_forgotten", details={"channel_id": channel.id}
        )

    @app_commands.command(
        name="request", description="Ask the server for something, or manage requests"
    )
    async def request(self, interaction: discord.Interaction) -> None:
        if not await self._ready(interaction):
            return
        embed, view = await build_panel(self.bot, interaction.guild, interaction.user)
        await interaction.response.send_message(
            embed=embed,
            view=view,
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        view.message = await interaction.original_response()

    async def submit(
        self, interaction: discord.Interaction, *, what: str, why: str, due: str
    ) -> None:
        """What the modal does once it is filled in: one row, one notice, one ephemeral line."""
        if not guard_allows(self.bot, interaction.channel_id):
            await answer(interaction, guard_refusal(self.bot))
            return
        if not await self._ready(interaction):
            return
        guild = interaction.guild
        if not requests_are_on(self.bot.store, guild.id):
            await answer(interaction, REQUESTS_OFF)
            return
        staff = self.bot.store.is_staff(interaction.user)
        if not everyone_may_file(self.bot.store, guild.id) and not staff:
            await answer(interaction, STAFF_ONLY_FILES)
            return
        try:
            kept_what, kept_why, due_on = checked_fields(what, why, due)
        except RequestError as exc:
            await answer(interaction, str(exc))
            return
        await interaction.response.defer(ephemeral=True)
        request_id = await create_request(
            self.bot.db,
            guild.id,
            interaction.user.id,
            what=kept_what,
            why=kept_why,
            due_on=due_on,
            status=OPEN,
        )
        await log_action(
            self.bot,
            guild,
            "request.filed",
            actor=interaction.user,
            target=interaction.user,
            details={"request_id": request_id, "what": clamp(kept_what, 120), "due_on": due_on},
        )
        row = await get_request(self.bot.db, request_id)
        await notify(self.bot, guild, row, interaction.user)
        await answer(interaction, FILED.format(request_id=request_id))

    async def ready_submit(
        self,
        interaction: discord.Interaction,
        request_id: int,
        *,
        built: str,
        how_to_test: str,
        previous: Any = None,
    ) -> None:
        """What the ready modal does once it is filled in — the one shared path, nothing else."""
        if not await still_staff(interaction):
            return
        if not await opened(interaction, staff=False):
            return
        said, fresh = await mark_ready(
            self.bot,
            interaction.guild,
            request_id,
            interaction.user,
            built,
            how_to_test,
        )
        await finish_card(interaction, request_id, said, fresh, previous)

    async def note_submit(
        self,
        interaction: discord.Interaction,
        request_id: int,
        kind: str,
        text: str,
        previous: Any = None,
    ) -> None:
        """What hold, decline and send-back all do once their one-line note is submitted."""
        if not await still_staff(interaction):
            return
        if not await opened(interaction, staff=False):
            return
        if kind == "sendback":
            said, fresh = await send_back(
                self.bot, interaction.guild, request_id, interaction.user, text
            )
        else:
            said, fresh = await apply_decision(
                self.bot,
                interaction.guild,
                request_id,
                NOTE_STATUS[kind],
                interaction.user,
                reason=text,
            )
        await finish_card(interaction, request_id, said, fresh, previous)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Requests(bot))


__all__ = [
    "BackButton",
    "CardMoveButton",
    "FileButton",
    "LogsButton",
    "MakeForumButton",
    "NoteModal",
    "ReadyModal",
    "RefreshButton",
    "RequestModal",
    "RequestPick",
    "RequestView",
    "Requests",
    "WithdrawPick",
    "accept",
    "apply_decision",
    "ask_check",
    "back_to_panel",
    "build_card",
    "build_panel",
    "card",
    "confirm_withdraw",
    "finish_card",
    "forum_of",
    "guard_allows",
    "make_forum",
    "mark_ready",
    "moves_land_in",
    "notify",
    "notify_move",
    "open_card",
    "open_forum_post",
    "retag_post",
    "thread_of",
    "open_withdraw_confirm",
    "opened",
    "person_told",
    "post_line",
    "render_panel",
    "resume_request",
    "retire",
    "run_move",
    "send_back",
    "still_staff",
    "tell_person",
]
