from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import discord

log = logging.getLogger(__name__)

QUESTION_LIMIT = 300
LABEL_LIMIT = 55
MAX_NATIVE_OPTIONS = 10
MIN_OPTIONS = 2
MIN_HOURS = 1
MAX_HOURS = 32 * 24
DEFAULT_HOURS = 24
RATING_SLOTS = 5
BAR_CELLS = 20
FULL = "█"
EMPTY = "░"
LABEL_COLUMN = 18
THREAD_NAME_LIMIT = 100

SINGLE = "single"
CHECKBOX = "checkbox"
YESNO = "yesno"
RATING = "rating"
DATE = "date"
FREE_TEXT = "text"
NUMBER = "number"
RANKED = "ranked"
NATIVE_KINDS = (SINGLE, CHECKBOX, YESNO, RATING)
LATER_KINDS = (DATE, FREE_TEXT, NUMBER, RANKED)
KINDS = NATIVE_KINDS + LATER_KINDS
GENERATED_KINDS = (YESNO, RATING)

NATIVE = "native"
PANEL = "panel"
SURFACES = (NATIVE, PANEL)

LIVE = "live"
AT_CLOSE = "close"
RESULTS_CHOICES = (LIVE, AT_CLOSE)

DRAFT = "draft"
PENDING_REVIEW = "pending_review"
OPEN = "open"
CLOSED = "closed"
ARCHIVED = "archived"
DENIED = "denied"
CANCELLED = "cancelled"
STATUSES = (DRAFT, PENDING_REVIEW, OPEN, CLOSED, ARCHIVED, DENIED, CANCELLED)
OPEN_STATUSES = (DRAFT, PENDING_REVIEW, OPEN)
SETTLED_STATUSES = (CLOSED, CANCELLED, DENIED, ARCHIVED)

TRANSITIONS: dict[str, tuple[str, ...]] = {
    DRAFT: (PENDING_REVIEW, OPEN, CANCELLED),
    PENDING_REVIEW: (OPEN, DENIED, CANCELLED),
    OPEN: (CLOSED, CANCELLED),
    CLOSED: (ARCHIVED,),
    CANCELLED: (ARCHIVED,),
    DENIED: (),
    ARCHIVED: (),
}

TERMINAL_STATUSES = tuple(status for status, allowed in TRANSITIONS.items() if not allowed)

COLOURS: dict[str, int] = {
    DRAFT: 0x5865F2,
    PENDING_REVIEW: 0x5865F2,
    OPEN: 0x57F287,
    CLOSED: 0x99AAB5,
    ARCHIVED: 0x99AAB5,
    DENIED: 0xED4245,
    CANCELLED: 0xED4245,
}

KIND_NAMES: dict[str, str] = {
    SINGLE: "single choice",
    CHECKBOX: "checkbox",
    YESNO: "yes / no",
    RATING: "rating 1-5",
    DATE: "date",
    FREE_TEXT: "free text",
    NUMBER: "number",
    RANKED: "ranked choice",
}

LATER_KIND_NAMES: dict[str, str] = {
    DATE: "A **date** poll",
    FREE_TEXT: "A **free text** poll",
    NUMBER: "A **number** poll",
    RANKED: "A **ranked choice** poll",
}

NEXT_UPDATE = "that kind of poll arrives with the next update"

KIND_NOT_YET = (
    "{what} needs a voting surface Black Bloc does not have yet, so nothing was posted — "
    f"{NEXT_UPDATE}. Until then a poll can be single choice, checkbox, yes/no or a "
    "1-5 rating."
)
ANONYMOUS_NOT_YET = (
    "Discord's own polls list everybody who voted, so Black Bloc will not label one "
    "**anonymous** and make a promise it cannot keep — nothing was posted, and "
    f"{NEXT_UPDATE}. Run it with anonymous off if it cannot wait."
)
HIDDEN_NOT_YET = (
    "Discord's own polls show the bars as the votes come in and there is no way to hide them, so "
    "**results at close** could not be honoured and nothing was posted — "
    f"{NEXT_UPDATE}. Run it with results **live** if it cannot wait."
)
TOO_MANY_NOT_YET = (
    "**{count}** options is more than the {limit} a Discord poll can carry, so nothing was "
    f"posted — {NEXT_UPDATE}. Until then, cut it to {{limit}} options or fewer."
)

NO_QUESTION = (
    "A poll needs a question, so nothing was posted. Put the thing you are asking in the "
    "question box — it is the heading everybody votes under."
)
QUESTION_TOO_LONG = (
    "That question is **{given}** characters and Discord allows {limit}, so nothing was posted. "
    "Shorten it and run the command again; the long version can go in the channel underneath."
)
TOO_FEW_OPTIONS = (
    "A poll needs at least {limit} options and this one has **{given}**, so nothing was posted. "
    "Write them separated by `|` — `Pizza | Tacos | Neither` is three."
)
LABEL_TOO_LONG = (
    "The option **{given}** is longer than the {limit} characters Discord allows on a poll "
    "answer, so nothing was posted. Shorten that one and run the command again."
)
DUPLICATE_OPTION = (
    "**{given}** is in the options twice, so nothing was posted — two identical answers split "
    "the votes and nobody can tell them apart. Remove one of them and try again."
)
BAD_HOURS = (
    "**{given}** is not a length Black Bloc can give a poll, so nothing was posted. Discord "
    "counts poll length in whole hours, from {low} to {high} (32 days)."
)

RESULTS_TITLE = "{question}"
NO_VOTES = "Nobody voted."
WINNER_MARK = "  <- winner"
TIED = "It is a tie between {names}."
AVERAGE = "Average rating: **{mean}** out of {top}."


class NeedsPanel(ValueError):
    """The poll asked for something only the (not yet built) panel surface can do."""


def clamp(text: Any, limit: int) -> str:
    return str(text or "").strip()[:limit]


def can_transition(before: Any, after: Any) -> bool:
    return str(after) in TRANSITIONS.get(str(before), ())


def split_options(text: Any) -> list[str]:
    """`Pizza | Tacos` is two options; blank entries are dropped, not counted."""
    return [part.strip() for part in str(text or "").split("|") if part.strip()]


def options_for(kind: str, text: Any) -> list[str]:
    """Yes/no and rating generate their own answers; everything else is what was typed."""
    if kind == YESNO:
        return ["Yes", "No"]
    if kind == RATING:
        return [str(number) for number in range(1, RATING_SLOTS + 1)]
    return split_options(text)


def validate(question: Any, labels: Any, hours: Any) -> str | None:
    """The refusal sentence, or None when the poll is postable."""
    asked = str(question or "").strip()
    if not asked:
        return NO_QUESTION
    if len(asked) > QUESTION_LIMIT:
        return QUESTION_TOO_LONG.format(given=len(asked), limit=QUESTION_LIMIT)
    found = list(labels or ())
    if len(found) < MIN_OPTIONS:
        return TOO_FEW_OPTIONS.format(limit=MIN_OPTIONS, given=len(found))
    seen: set[str] = set()
    for label in found:
        if len(label) > LABEL_LIMIT:
            return LABEL_TOO_LONG.format(given=clamp(label, 60), limit=LABEL_LIMIT)
        folded = label.casefold()
        if folded in seen:
            return DUPLICATE_OPTION.format(given=clamp(label, 60))
        seen.add(folded)
    if not whole_hours(hours):
        return BAD_HOURS.format(given=clamp(hours, 40), low=MIN_HOURS, high=MAX_HOURS)
    return None


def whole_hours(hours: Any) -> bool:
    if isinstance(hours, bool) or not isinstance(hours, int):
        return False
    return MIN_HOURS <= hours <= MAX_HOURS


def surface_for(kind: str, anonymous: bool, results: str, slot_count: int) -> str:
    """`native`, or a sentence saying which part of the ask the panel slice owns."""
    if kind in LATER_KINDS:
        raise NeedsPanel(
            KIND_NOT_YET.format(what=LATER_KIND_NAMES.get(kind, f"A **{kind}** poll"))
        )
    if kind not in NATIVE_KINDS:
        raise NeedsPanel(KIND_NOT_YET.format(what=f"A **{clamp(kind, 40)}** poll"))
    if anonymous:
        raise NeedsPanel(ANONYMOUS_NOT_YET)
    if results == AT_CLOSE:
        raise NeedsPanel(HIDDEN_NOT_YET)
    if int(slot_count) > MAX_NATIVE_OPTIONS:
        raise NeedsPanel(
            TOO_MANY_NOT_YET.format(count=int(slot_count), limit=MAX_NATIVE_OPTIONS)
        )
    return NATIVE


def is_multi(kind: str) -> bool:
    return kind == CHECKBOX


def closes_at(hours: int, now: datetime | None = None) -> datetime:
    return (now or datetime.now(UTC)) + timedelta(hours=max(int(hours), MIN_HOURS))


def describe_hours(hours: Any) -> str:
    total = max(int(hours or 0), 0)
    days, rest = divmod(total, 24)
    if days and rest:
        return f"{days}d {rest}h"
    if days:
        return f"{days}d"
    return f"{total}h"


def bar(votes: Any, total: Any, cells: int = BAR_CELLS) -> str:
    counted = max(int(votes or 0), 0)
    everyone = max(int(total or 0), 0)
    filled = round(cells * counted / everyone) if everyone else 0
    filled = max(0, min(cells, filled))
    return FULL * filled + EMPTY * (cells - filled)


def share(votes: Any, total: Any) -> int:
    everyone = max(int(total or 0), 0)
    if not everyone:
        return 0
    return round(100 * max(int(votes or 0), 0) / everyone)


def ranked(counts: Any) -> list[dict[str, Any]]:
    """Most votes first; ties keep the order the options were written in."""
    rows = [dict(row) for row in counts or ()]
    return sorted(rows, key=lambda row: (-int(row.get("votes") or 0), int(row.get("position", 0))))


def winners(counts: Any) -> list[dict[str, Any]]:
    rows = ranked(counts)
    if not rows or not int(rows[0].get("votes") or 0):
        return []
    best = int(rows[0]["votes"])
    return [row for row in rows if int(row.get("votes") or 0) == best]


def results_text(counts: Any, total: Any) -> str:
    """The bar chart every surface shows, in one monospaced block."""
    rows = ranked(counts)
    if not rows:
        return NO_VOTES
    top = winners(counts)
    top_positions = {int(row["position"]) for row in top}
    alone = len(top) == 1
    lines: list[str] = []
    for row in rows:
        label = clamp(row.get("label"), LABEL_COLUMN).ljust(LABEL_COLUMN)
        votes = int(row.get("votes") or 0)
        mark = WINNER_MARK if alone and int(row["position"]) in top_positions else ""
        lines.append(
            f"{label} {bar(votes, total)} {votes:>4}  ({share(votes, total):>3}%){mark}"
        )
    return "\n".join(lines)


def average_rating(counts: Any) -> float | None:
    """The mean of a rating poll, or None when nothing numeric was voted for."""
    total = 0
    weighted = 0.0
    for row in counts or ():
        try:
            value = float(str(row.get("label")).strip())
        except (TypeError, ValueError):
            return None
        votes = max(int(row.get("votes") or 0), 0)
        total += votes
        weighted += value * votes
    if not total:
        return None
    return round(weighted / total, 2)


def results_embed(
    *,
    poll_id: Any,
    question: str,
    counts: Any,
    total: Any,
    status: str = CLOSED,
    kind: str = SINGLE,
    closed_at: Any = None,
    approximate: bool = False,
) -> discord.Embed:
    """The one results card: the slash command, the loop and the review card all use it."""
    embed = discord.Embed(
        title=clamp(question, QUESTION_LIMIT),
        description=f"```\n{results_text(counts, total)}\n```",
        colour=COLOURS.get(status, COLOURS[CLOSED]),
    )
    counted = max(int(total or 0), 0)
    embed.add_field(name="Status", value=status, inline=True)
    embed.add_field(
        name="Votes", value=f"{counted}{' so far' if approximate else ''}", inline=True
    )
    if kind == RATING:
        mean = average_rating(counts)
        if mean is not None:
            embed.add_field(
                name="Average", value=AVERAGE.format(mean=mean, top=RATING_SLOTS), inline=False
            )
    won = winners(counts)
    if len(won) > 1:
        names = ", ".join(f"**{clamp(row['label'], LABEL_LIMIT)}**" for row in won)
        embed.add_field(name="Winner", value=TIED.format(names=names), inline=False)
    if closed_at:
        embed.add_field(name="Closed", value=str(closed_at), inline=False)
    embed.set_footer(text=f"Poll #{poll_id}")
    return embed


def review_card(
    *,
    poll_id: Any,
    question: str,
    creator_id: int,
    kind: str,
    labels: Any,
    hours: Any,
    status: str = PENDING_REVIEW,
    deny_reason: str | None = None,
) -> discord.Embed:
    """The card staff approve or deny, and the one the creator is DM'd."""
    embed = discord.Embed(
        title=clamp(question, QUESTION_LIMIT),
        colour=COLOURS.get(status, COLOURS[PENDING_REVIEW]),
    )
    embed.add_field(name="Who", value=f"<@{creator_id}>", inline=True)
    embed.add_field(name="Status", value=status, inline=True)
    embed.add_field(name="Kind", value=KIND_NAMES.get(kind, kind), inline=True)
    embed.add_field(name="Open for", value=describe_hours(hours), inline=True)
    shown = "\n".join(
        f"{n}. {clamp(label, LABEL_LIMIT)}" for n, label in enumerate(labels or (), 1)
    )
    embed.add_field(name="Options", value=shown or "none", inline=False)
    if deny_reason:
        embed.add_field(name="Why not", value=clamp(deny_reason, 1024), inline=False)
    embed.set_footer(text=f"Poll #{poll_id}")
    return embed


def mentions(ping_role_id: Any = None) -> discord.AllowedMentions:
    """Nothing a poll's author typed may ping; only the configured role may."""
    return discord.AllowedMentions(
        everyone=False,
        users=False,
        roles=[discord.Object(int(ping_role_id))] if ping_role_id else False,
    )


def open_text(creator_id: Any, ping_role_id: Any = None) -> str:
    prefix = f"<@&{ping_role_id}> " if ping_role_id else ""
    return f"{prefix}<@{creator_id}> started a poll."


def reminder_text(question: str, when: Any = None) -> str:
    tail = f" It closes {when}." if when else ""
    return f"Last call on **{clamp(question, 80)}** — the poll is still open.{tail}"


def closed_text(question: str) -> str:
    return f"**{clamp(question, 80)}** is closed. Here is how it went."


def thread_name(question: str) -> str:
    return clamp(question, THREAD_NAME_LIMIT) or "Poll"


def counts_from_options(rows: Any) -> list[dict[str, Any]]:
    """The stored options turned into the shape every renderer and the API read."""
    return [
        {
            "position": int(row["position"]),
            "label": str(row["label"]),
            "votes": int(row["final_votes"] or 0),
        }
        for row in rows or ()
    ]
