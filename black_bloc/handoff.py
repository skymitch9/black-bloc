from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any, NamedTuple

from .actionlog import log_action
from .logkinds import VIA_DISCORD, kind_via

log = logging.getLogger(__name__)

REQUEST = "request"
EVENT = "event"
TICKET = "ticket"
KINDS = (REQUEST, EVENT, TICKET)

MODE_KEY = "handoff_mode"
CONFIRM_HOURS_KEY = "handoff_confirm_hours"
MODES = ("off", "on")
CONFIRM_HOURS = 24
CONFIRM_HOURS_MIN = 1
CONFIRM_HOURS_MAX = 168

ASKED = "asked"
YES = "yes"
TABLES: dict[str, str] = {REQUEST: "requests", EVENT: "events", TICKET: "modmail_tickets"}

SEND_TO_EVENTS = "Send to events…"
NOT_AN_EVENT = "Not an event — make it a request"
MAKE_A_REQUEST = "Make this a request…"
MAKE_AN_EVENT = "Make this an event…"
OPEN_A_TICKET = "Open a ticket with them…"
MAKE_THE_EVENT = "Make the event…"
CONFIRM_YES = "Yes, file it"
CONFIRM_NO = "No, keep it private"

TITLE_LIMIT = 100
BODY_LIMIT = 1000

FILED_AS = "Filed as request #{request_id} by <@{user_id}>"
FROM_TICKET = "Filed from ticket #{ticket_id} by <@{user_id}>"
FROM_EVENT = "(filed from event #{event_id})"

REQUEST_TO_EVENT_DM = (
    "Your request **#{request_id}** on **{guild}** is now event **#{event_id}** — staff will "
    "review it there."
)
EVENT_TO_REQUEST_DM = (
    "Your event **#{event_id}** on **{guild}** is now request **#{request_id}** instead — staff "
    "will take it from there."
)
EVENT_TO_REQUEST_WHY = "filed as request #{request_id} instead"
REQUEST_MOVED_LINE = "→ event **#{event_id}**"
EVENT_MOVED_LINE = "→ request **#{request_id}**"
TICKET_MOVED_LINE = "→ {what} **#{ident}** — {who} said yes to filing it."
TICKET_SAID_NO_LINE = "{who} said no — nothing was filed and the ticket stays private."
TICKET_ASKED_LINE = (
    "{who} has been asked by DM whether this ticket may be filed as a {what}. No answer by "
    "{when} counts as no."
)
TICKET_SAID_YES_EVENT = (
    "{who} said yes. **{title}** still needs a date — press **Make the event…** to pick one."
)

ASKED_KIND = "handoff.asked"
REFUSED_KIND = "handoff.refused"
ASK_TITLE_FIELD = "What staff would file"
ASK_BODY_FIELD = "In your words"
ASK_FOOTER = "Black Bloc · nothing is filed unless you say yes"
ASK_DASH = "—"
ASKED_SAID = "{who} has been asked by DM whether this may be filed as a {what}."
CONFIRM_COLOUR = 0x5865F2
ASK_TITLE_LABEL = "What should it be called?"
ASK_BODY_LABEL = "What should it say? (the member sees this before they answer)"
ASK_MODAL_TITLE = {
    REQUEST: "File this ticket as a request",
    EVENT: "File this ticket as an event",
}
NO_SUCH_MEMBER = (
    "<@{user_id}> is not somebody Black Bloc can see on this server any more, so no ticket was "
    "opened. They may have left."
)
TICKET_SUBJECT = "Request #{request_id}"
TICKET_QUOTE = (
    "This is about your request **#{request_id}** — *{what}*\n\n> {why}\n\nTell us anything "
    "that would help."
)

CONFIRM_TITLE = "Staff would like to file your ticket"
CONFIRM_BODY = (
    "Staff on **{guild}** would like to file your ticket **#{ticket_id}** as a {what} in your "
    "name: **{title}**\n\nEveryone on staff will see it. Nothing is filed unless you say yes, "
    "and the ticket stays open either way."
)
CONFIRM_YES_SAID = "Thank you — it has been filed and staff can see it now."
CONFIRM_NO_SAID = "Nothing was filed. Your ticket stays private."
CONFIRM_DM_FAILED = (
    "Black Bloc could not DM {who}, so nothing was asked and nothing was filed. Their DMs are "
    "shut or Black Bloc is blocked — ask them in the ticket instead."
)

HANDOFF_OFF = (
    "**Send to…** is switched off on this server, so nothing was moved. It needs `handoff_mode` "
    "set to **on** — a Lead does that on the dashboard's Settings page under **request**, or "
    "with `/settings` ▸ **A setting group…** ▸ request."
)
ALREADY_FINAL = (
    "Request **#{request_id}** is already **{status}**, so there is nothing left to send "
    "anywhere."
)
EVENT_ALREADY_DECIDED = (
    "Event **#{event_id}** is already **{status}**, so there is nothing left to send anywhere."
)
ALREADY_ASKED = (
    "Black Bloc already asked {who} — it is waiting on their answer until {when}. Nothing else "
    "can be filed from this ticket until then."
)
ALREADY_SAID_YES = (
    "{who} already said yes to an event. Press **Make the event…** in the ticket to pick a date "
    "for it."
)
ALREADY_MOVED = (
    "Ticket **#{ticket_id}** has already been filed as {what} **#{ident}**, so nothing was "
    "filed twice."
)
CONFIRM_GONE = (
    "This question is no longer waiting on an answer — either it has run out of time or staff "
    "have taken it back. Nothing was filed."
)
NO_SUCH_TICKET = "That ticket is no longer there, so nothing was filed."


class Trail(NamedTuple):
    """What a `moved_to` cell says: where the thing went, or who is being waited on."""

    kind: str
    ident: int = 0
    until: str = ""


def mode(store: Any, guild_id: int) -> str:
    return str(store.get(guild_id, MODE_KEY) or "off")


def handoff_on(store: Any, guild_id: int) -> bool:
    return mode(store, guild_id) == "on"


def confirm_hours(store: Any, guild_id: int) -> int:
    found = store.get(guild_id, CONFIRM_HOURS_KEY)
    try:
        return max(CONFIRM_HOURS_MIN, min(CONFIRM_HOURS_MAX, int(found)))
    except (TypeError, ValueError):
        return CONFIRM_HOURS


def trail(kind: str, ident: Any) -> str:
    return f"{kind}:{int(ident)}"


def asked_trail(kind: str, until: datetime) -> str:
    return f"{ASKED}:{kind}:{until.isoformat()}"


def yes_trail(kind: str) -> str:
    return f"{YES}:{kind}"


def read_trail(text: Any) -> Trail | None:
    """One cell, three shapes: `kind:id`, `asked:kind:when`, `yes:kind`. Anything else is None."""
    parts = str(text or "").split(":", 2)
    head = parts[0]
    if head == ASKED and len(parts) == 3 and parts[1] in KINDS:
        return Trail(ASKED, 0, parts[2])
    if head == YES and len(parts) == 2 and parts[1] in KINDS:
        return Trail(YES, 0, parts[1])
    if head in KINDS and len(parts) == 2 and parts[1].isdigit():
        return Trail(head, int(parts[1]))
    return None


def asked_kind(text: Any) -> str:
    parts = str(text or "").split(":", 2)
    return parts[1] if parts[0] in (ASKED, YES) and len(parts) >= 2 else ""


def expired(text: Any, now: datetime) -> bool:
    """An unanswered question is a no once its hours are up; nothing sweeps, the read decides."""
    found = read_trail(text)
    if found is None or found.kind != ASKED:
        return False
    try:
        return datetime.fromisoformat(found.until) <= now
    except ValueError:
        return True


def waiting_on(text: Any, now: datetime) -> Trail | None:
    found = read_trail(text)
    if found is None or found.kind != ASKED or expired(text, now):
        return None
    return found


def until_stamp(text: Any) -> str:
    """The deadline as Discord renders it, so a refusal names a time the reader can see."""
    found = read_trail(text)
    try:
        when = datetime.fromisoformat(found.until) if found is not None else None
    except (ValueError, TypeError):
        return "soon"
    return f"<t:{int(when.timestamp())}:f>" if when is not None else "soon"


def deadline(store: Any, guild_id: int, now: datetime | None = None) -> datetime:
    at = now or datetime.now(UTC)
    return at + timedelta(hours=confirm_hours(store, guild_id))


def handoff_kind(source: str, target: str) -> str:
    return f"handoff.{source}_to_{target}"


async def set_moved_to(db: Any, kind: str, ident: Any, value: Any) -> None:
    """The trail column, in the one place that writes it; `kind` is never a caller's string."""
    table = TABLES[kind]
    await db.conn.execute(
        f"UPDATE {table} SET moved_to = ? WHERE id = ?", (value, int(ident))
    )
    await db.conn.commit()


async def log_handoff(
    bot: Any,
    guild: Any,
    source: str,
    source_id: Any,
    target: str,
    target_id: Any,
    *,
    actor: Any = None,
    member: Any = None,
    via: str = VIA_DISCORD,
) -> None:
    """One hand-off, one row, both ids on it — the whole trail an auditor needs."""
    await log_action(
        bot,
        guild,
        kind_via(handoff_kind(source, target), via),
        actor=actor,
        target=member,
        details={
            f"{source}_id": int(source_id),
            f"{target}_id": int(target_id) if target_id else None,
            "via": via,
        },
    )


def clamp(text: Any, limit: int) -> str:
    return str(text or "").strip()[:limit]


def moved_words(moved_to: Any) -> str:
    """Where a handed-off thing went, in words; a cell nothing wrote reads as nothing."""
    found = read_trail(moved_to)
    if found is None or found.kind not in (EVENT, REQUEST):
        return ""
    return f"{found.kind} #{found.ident}"


def refusal_for_request(store: Any, guild_id: int, row: Any) -> str:
    """Why this request cannot be sent anywhere — empty when it can."""
    from .requests import FINAL_STATUSES, STATUS_WORDS, row_value

    if not handoff_on(store, guild_id):
        return HANDOFF_OFF
    status = str(row_value(row, "status") or "")
    if status in FINAL_STATUSES:
        return ALREADY_FINAL.format(
            request_id=row_value(row, "id"), status=STATUS_WORDS.get(status, status)
        )
    return ""


def refusal_for_ticket(store: Any, guild_id: int, ticket: Any, now: Any = None) -> str:
    """Why nothing more can be filed from this ticket right now — empty when it can."""
    from .modmail import field_of

    if not handoff_on(store, guild_id):
        return HANDOFF_OFF
    cell = field_of(ticket, "moved_to")
    at = now or datetime.now(UTC)
    found = read_trail(cell)
    if found is None:
        return ""
    if found.kind == ASKED:
        if waiting_on(cell, at) is None:
            return ""
        return ALREADY_ASKED.format(
            who=mention(field_of(ticket, "user_id")), when=until_stamp(cell)
        )
    if found.kind == YES:
        return ALREADY_SAID_YES.format(who=mention(field_of(ticket, "user_id")))
    return ALREADY_MOVED.format(
        ticket_id=field_of(ticket, "id"), what=found.kind, ident=found.ident
    )


def mention(user_id: Any) -> str:
    return f"<@{int(user_id)}>" if user_id else "somebody"


def refusal_for_event(store: Any, guild_id: int, row: Any) -> str:
    """Why this event cannot be sent anywhere — empty when it can."""
    from .events import OPEN_STATUSES, cell

    if not handoff_on(store, guild_id):
        return HANDOFF_OFF
    status = str(cell(row, "status") or "")
    if status not in OPEN_STATUSES:
        return EVENT_ALREADY_DECIDED.format(event_id=cell(row, "id"), status=status)
    return ""


async def request_to_event(
    bot: Any, guild: Any, request_id: int, event_row: Any, actor: Any, *, via: str = VIA_DISCORD
) -> tuple[str, Any]:
    """The event exists; this is everything the request owes afterwards — one place, every door."""
    from .cogs.community.requests import notify_move, say_in_channel
    from .events import cell
    from .requests import MOVED, get_request, set_status

    event_id = int(cell(event_row, "id"))
    row = await get_request(bot.db, request_id)
    if row is None:
        return (REQUEST_MOVED_LINE.format(event_id=event_id), None)
    await set_status(bot.db, request_id, MOVED, decided_by=getattr(actor, "id", None))
    await set_moved_to(bot.db, REQUEST, request_id, trail(EVENT, event_id))
    fresh = await get_request(bot.db, request_id)
    await log_handoff(
        bot,
        guild,
        REQUEST,
        request_id,
        EVENT,
        event_id,
        actor=actor,
        member=row["user_id"],
        via=via,
    )
    await say_in_channel(bot, guild, fresh, REQUEST_MOVED_LINE.format(event_id=event_id))
    await notify_move(bot, guild, fresh, MOVED)
    member = guild.get_member(row["user_id"]) or bot.get_user(row["user_id"])
    await tell(
        bot,
        guild,
        member,
        REQUEST_TO_EVENT_DM.format(
            request_id=request_id, event_id=event_id, guild=guild.name
        ),
        request_id=request_id,
    )
    return (REQUEST_MOVED_LINE.format(event_id=event_id), fresh)


async def event_to_request(
    bot: Any, guild: Any, row: Any, actor: Any, *, via: str = VIA_DISCORD
) -> tuple[str, Any]:
    """Not an event — make it a request: the row is filed, then the event's own cancel runs."""
    from .cogs.community.requests import notify
    from .events import HANDED_OFF, cancel_for, cell, get_event
    from .requests import SOURCE_EVENT, WHAT_LIMIT, WHY_LIMIT, create_request, get_request

    event_id = int(cell(row, "id"))
    member_id = int(cell(row, "requester_id"))
    request_id = await create_request(
        bot.db,
        guild.id,
        member_id,
        what=clamp(cell(row, "title"), WHAT_LIMIT),
        why=clamp(cell(row, "description"), WHY_LIMIT) or FROM_EVENT.format(event_id=event_id),
        due_on=None,
        source=SOURCE_EVENT,
    )
    filed = await get_request(bot.db, request_id)
    said, fresh = await cancel_for(
        bot,
        guild,
        row,
        actor,
        note=EVENT_TO_REQUEST_WHY.format(request_id=request_id),
        reason=HANDED_OFF,
        via=via,
    )
    if fresh is None:
        return (said, None)
    await set_moved_to(bot.db, EVENT, event_id, trail(REQUEST, request_id))
    await log_handoff(
        bot, guild, EVENT, event_id, REQUEST, request_id, actor=actor, member=member_id, via=via
    )
    member = guild.get_member(member_id) or bot.get_user(member_id)
    await notify(bot, guild, filed, member)
    return (EVENT_MOVED_LINE.format(request_id=request_id), await get_event(bot.db, event_id))


async def request_to_ticket(
    bot: Any, guild: Any, row: Any, actor: Any, *, via: str = VIA_DISCORD
) -> Any:
    """Open a ticket with them… — the staff door, quoting the request; nothing is MOVED."""
    from .cogs.moderation.modmail import open_a_ticket
    from .modmail import SOURCE_STAFF
    from .panels import refusal
    from .requests import row_value

    request_id = row_value(row, "id")
    member_id = int(row_value(row, "user_id") or 0)
    member = guild.get_member(member_id) or bot.get_user(member_id)
    if member is None:
        return refusal(NO_SUCH_MEMBER.format(user_id=member_id), "no_member", 404)
    outcome = await open_a_ticket(
        bot,
        guild,
        member,
        source=SOURCE_STAFF,
        subject=TICKET_SUBJECT.format(request_id=request_id),
        text=TICKET_QUOTE.format(
            request_id=request_id,
            what=clamp(row_value(row, "what"), TITLE_LIMIT),
            why=clamp(row_value(row, "why"), BODY_LIMIT),
        ),
        actor=actor,
        check_toggle=False,
        via=via,
    )
    if outcome.ok:
        await log_handoff(
            bot,
            guild,
            REQUEST,
            request_id,
            TICKET,
            outcome.value,
            actor=actor,
            member=member_id,
            via=via,
        )
    return outcome


def confirm_embed(guild: Any, ticket: Any, kind: str, title: str, body: str) -> Any:
    """What the member is DMed — and, read back, the only place that wording is kept."""
    import discord

    from .modmail import field_of

    embed = discord.Embed(
        title=CONFIRM_TITLE,
        description=CONFIRM_BODY.format(
            guild=guild.name,
            ticket_id=field_of(ticket, "id"),
            what=kind,
            title=clamp(title, TITLE_LIMIT),
        ),
        colour=discord.Colour(CONFIRM_COLOUR),
    )
    embed.add_field(
        name=ASK_TITLE_FIELD, value=clamp(title, TITLE_LIMIT) or ASK_DASH, inline=False
    )
    embed.add_field(name=ASK_BODY_FIELD, value=clamp(body, BODY_LIMIT) or ASK_DASH, inline=False)
    embed.set_footer(text=ASK_FOOTER)
    return embed


def read_ask(embed: Any) -> tuple[str, str]:
    """The title and body read back off the card carrying them; no second row stores them."""
    found = {
        str(getattr(field, "name", "")): str(getattr(field, "value", ""))
        for field in (getattr(embed, "fields", None) or ())
    }
    kept = [found.get(ASK_TITLE_FIELD, ""), found.get(ASK_BODY_FIELD, "")]
    return tuple("" if one == ASK_DASH else one for one in kept)


async def reread(bot: Any, ticket_id: Any) -> Any:
    from .cogs.moderation.modmail import get_ticket

    return await get_ticket(bot.db, int(ticket_id))


async def ask_the_member(
    bot: Any,
    guild: Any,
    ticket: Any,
    kind: str,
    title: str,
    body: str,
    actor: Any,
    *,
    view: Any = None,
    via: str = VIA_DISCORD,
) -> Any:
    """A ticket is private, so nothing is filed until the member has said so (design §A)."""
    from .cogs.moderation.modmail import speak, ticket_dm
    from .modmail import field_of
    from .panels import Outcome, refusal

    ticket_id = int(field_of(ticket, "id"))
    who = mention(field_of(ticket, "user_id"))
    until = deadline(bot.store, guild.id)
    why_not = await ticket_dm(
        bot,
        guild,
        ticket,
        embed=confirm_embed(guild, ticket, kind, title, body),
        view=view,
    )
    if why_not is not None:
        return refusal(CONFIRM_DM_FAILED.format(who=who), "dms_shut", 409)
    await set_moved_to(bot.db, TICKET, ticket_id, asked_trail(kind, until))
    await log_action(
        bot,
        guild,
        kind_via(ASKED_KIND, via),
        actor=actor,
        target=field_of(ticket, "user_id"),
        details={"ticket_id": ticket_id, "what": kind, "until": until.isoformat(), "via": via},
    )
    await speak(
        bot,
        guild,
        ticket,
        content=TICKET_ASKED_LINE.format(
            who=who, what=kind, when=until_stamp(asked_trail(kind, until))
        ),
    )
    return Outcome(True, ASKED_SAID.format(who=who, what=kind))


async def ticket_became(
    bot: Any,
    guild: Any,
    ticket_id: int,
    kind: str,
    ident: Any,
    actor: Any,
    *,
    via: str = VIA_DISCORD,
) -> str:
    """The trail a filed ticket keeps: one cell, one log row, one line in the ticket itself."""
    from .cogs.moderation.modmail import speak
    from .modmail import field_of

    ticket = await reread(bot, ticket_id)
    if ticket is None:
        return NO_SUCH_TICKET
    await set_moved_to(bot.db, TICKET, ticket_id, trail(kind, ident))
    await log_handoff(
        bot,
        guild,
        TICKET,
        ticket_id,
        kind,
        ident,
        actor=actor,
        member=field_of(ticket, "user_id"),
        via=via,
    )
    said = TICKET_MOVED_LINE.format(
        what=kind, ident=ident, who=mention(field_of(ticket, "user_id"))
    )
    await speak(bot, guild, ticket, content=said)
    return said


async def member_said_yes(
    bot: Any,
    guild: Any,
    ticket: Any,
    kind: str,
    title: str,
    body: str,
    *,
    make_event_view: Any = None,
    via: str = VIA_DISCORD,
) -> str:
    """Yes files a request outright; an event still owes a date, so staff are handed the draft."""
    from .cogs.community.requests import notify
    from .cogs.moderation.modmail import speak
    from .modmail import field_of
    from .requests import SOURCE_TICKET, WHAT_LIMIT, WHY_LIMIT, create_request, get_request

    ticket_id = int(field_of(ticket, "id"))
    member_id = int(field_of(ticket, "user_id"))
    member = guild.get_member(member_id) or bot.get_user(member_id)
    if kind == EVENT:
        await set_moved_to(bot.db, TICKET, ticket_id, yes_trail(EVENT))
        await speak(
            bot,
            guild,
            ticket,
            content=TICKET_SAID_YES_EVENT.format(
                who=mention(member_id), title=clamp(title, TITLE_LIMIT)
            ),
            embed=confirm_embed(guild, ticket, kind, title, body),
            view=make_event_view,
        )
        return CONFIRM_YES_SAID
    request_id = await create_request(
        bot.db,
        guild.id,
        member_id,
        what=clamp(title, WHAT_LIMIT),
        why=clamp(body, WHY_LIMIT) or FROM_TICKET.format(ticket_id=ticket_id, user_id=member_id),
        due_on=None,
        source=SOURCE_TICKET,
    )
    await ticket_became(bot, guild, ticket_id, REQUEST, request_id, member, via=via)
    await notify(bot, guild, await get_request(bot.db, request_id), member)
    return CONFIRM_YES_SAID


async def member_said_no(
    bot: Any, guild: Any, ticket: Any, kind: str, *, via: str = VIA_DISCORD
) -> str:
    """No files nothing, clears the question so staff may ask again, and says so in the ticket."""
    from .cogs.moderation.modmail import speak
    from .modmail import field_of

    ticket_id = int(field_of(ticket, "id"))
    await set_moved_to(bot.db, TICKET, ticket_id, None)
    await log_action(
        bot,
        guild,
        kind_via(REFUSED_KIND, via),
        target=field_of(ticket, "user_id"),
        details={"ticket_id": ticket_id, "what": kind, "via": via},
    )
    await speak(
        bot,
        guild,
        ticket,
        content=TICKET_SAID_NO_LINE.format(who=mention(field_of(ticket, "user_id"))),
    )
    return CONFIRM_NO_SAID


async def tell(bot: Any, guild: Any, member: Any, said: str, *, request_id: Any = None) -> None:
    """The one DM a hand-off owes the member; a shut inbox is logged, never silent."""
    from .cogs.community.requests import dm

    if member is not None and await dm(member, content=said):
        return
    await log_action(
        bot,
        guild,
        "request.dm_failed",
        target=getattr(member, "id", member),
        details={"request_id": request_id, "status": "handoff"},
    )


def prefilled(row: Any, *, kind: str) -> tuple[str, str]:
    """(title, description) for an event draft raised from a request or a ticket."""
    from .requests import row_value

    if kind == REQUEST:
        head = FILED_AS.format(
            request_id=row_value(row, "id"), user_id=int(row_value(row, "user_id") or 0)
        )
        body = clamp(row_value(row, "why"), BODY_LIMIT)
        return (clamp(row_value(row, "what"), TITLE_LIMIT), f"{head}\n{body}".strip())
    head = FROM_TICKET.format(
        ticket_id=row_value(row, "id"), user_id=int(row_value(row, "user_id") or 0)
    )
    return ("", head)


__all__ = [
    "ALREADY_ASKED",
    "ALREADY_FINAL",
    "ALREADY_MOVED",
    "ALREADY_SAID_YES",
    "ASKED",
    "BODY_LIMIT",
    "CONFIRM_BODY",
    "CONFIRM_DM_FAILED",
    "CONFIRM_GONE",
    "CONFIRM_HOURS",
    "CONFIRM_HOURS_KEY",
    "CONFIRM_HOURS_MAX",
    "CONFIRM_HOURS_MIN",
    "CONFIRM_NO",
    "CONFIRM_NO_SAID",
    "CONFIRM_TITLE",
    "CONFIRM_YES",
    "CONFIRM_YES_SAID",
    "EVENT",
    "EVENT_ALREADY_DECIDED",
    "EVENT_MOVED_LINE",
    "EVENT_TO_REQUEST_DM",
    "EVENT_TO_REQUEST_WHY",
    "FILED_AS",
    "FROM_EVENT",
    "FROM_TICKET",
    "HANDOFF_OFF",
    "KINDS",
    "MAKE_AN_EVENT",
    "MAKE_A_REQUEST",
    "MAKE_THE_EVENT",
    "MODES",
    "MODE_KEY",
    "NOT_AN_EVENT",
    "NO_SUCH_TICKET",
    "OPEN_A_TICKET",
    "REQUEST",
    "REQUEST_MOVED_LINE",
    "REQUEST_TO_EVENT_DM",
    "SEND_TO_EVENTS",
    "TABLES",
    "TICKET",
    "TICKET_ASKED_LINE",
    "TICKET_MOVED_LINE",
    "TICKET_SAID_NO_LINE",
    "TICKET_SAID_YES_EVENT",
    "TITLE_LIMIT",
    "Trail",
    "YES",
    "asked_kind",
    "asked_trail",
    "clamp",
    "confirm_hours",
    "deadline",
    "expired",
    "handoff_kind",
    "handoff_on",
    "log_handoff",
    "mode",
    "moved_words",
    "prefilled",
    "event_to_request",
    "refusal_for_request",
    "refusal_for_event",
    "request_to_event",
    "tell",
    "ASKED_KIND",
    "ASKED_SAID",
    "ASK_BODY_FIELD",
    "ASK_BODY_LABEL",
    "ASK_DASH",
    "ASK_MODAL_TITLE",
    "ASK_TITLE_FIELD",
    "ASK_TITLE_LABEL",
    "NO_SUCH_MEMBER",
    "REFUSED_KIND",
    "TICKET_QUOTE",
    "TICKET_SUBJECT",
    "ask_the_member",
    "confirm_embed",
    "member_said_no",
    "member_said_yes",
    "read_ask",
    "refusal_for_ticket",
    "reread",
    "request_to_ticket",
    "ticket_became",
    "read_trail",
    "set_moved_to",
    "trail",
    "until_stamp",
    "waiting_on",
    "yes_trail",
]
