"""A tournament's thread: made once where the mode says, its starter card, one card per set."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import discord

from . import brackets_cards as cards
from . import brackets_people, brackets_sets, shadow
from . import brackets_store as store_
from .actionlog import log_action
from .brackets.model import COMPLETE
from .brackets_moves import OFF, mode_of
from .settings_store import BRACKETS_CHANNEL, BRACKETS_PING_ROLE

log = logging.getLogger(__name__)

ON = "on"
SHADOW = "shadow"
LOCKS_ATTR = "_brackets_card_locks"
MISSING_ATTR = "_brackets_missing"
LOST_ATTR = "_brackets_lost_threads"
FAILED_ATTR = "_brackets_failures_told"
STARTER = "starter"
AUTO_ARCHIVE_MINUTES = 10080
THREAD_NAME_LIMIT = 100
POSTS_PER_PASS = 5
SCAN_LIMIT = 100
LOST_TWICE = 2
LIVE = (*store_.BEFORE_START, store_.RUNNING)
REASON = "Black Bloc tournament {id}"
START = "start"
EVERY_CARD = ("complete", "reopen", "cancel", "restore")


class Budget:
    """How many new set cards one pass may still post; the rest wait for the next tick."""

    def __init__(self, left: int = POSTS_PER_PASS) -> None:
        self.left = left

    def take(self) -> bool:
        if self.left <= 0:
            return False
        self.left -= 1
        return True


def card_lock(bot: Any, tournament_id: int) -> asyncio.Lock:
    locks = bot.__dict__.setdefault(LOCKS_ATTR, {})
    found = locks.get(int(tournament_id))
    if found is None:
        found = locks[int(tournament_id)] = asyncio.Lock()
    return found


def missing(bot: Any) -> set[tuple[int, str]]:
    return bot.__dict__.setdefault(MISSING_ATTR, set())


def lost_counts(bot: Any) -> dict[int, int]:
    return bot.__dict__.setdefault(LOST_ATTR, {})


def as_id(value: Any) -> int | None:
    try:
        return int(value) if value else None
    except (TypeError, ValueError):
        return None


def reason_of(exc: BaseException) -> str:
    if isinstance(exc, discord.HTTPException):
        return f"{getattr(exc, 'status', '')} {getattr(exc, 'text', '')}".strip()[:200]
    return f"{type(exc).__name__}: {exc}"[:200]


def origin_of(bot: Any) -> str | None:
    return getattr(getattr(bot, "settings", None), "origin", None)


def rehearsing(row: Any) -> bool:
    return bool(row["shadow"])


def parent_id(bot: Any, guild: Any) -> tuple[int | None, bool]:
    """Where a NEW thread goes: #knuck-up while on, the rehearsal home while shadow."""
    mode = mode_of(bot.store, guild.id)
    if mode == ON:
        return (as_id(bot.store.get(guild.id, BRACKETS_CHANNEL)), False)
    if mode == SHADOW:
        return (shadow.channel_id(bot, guild, feature="brackets"), True)
    return (None, False)


async def note(bot: Any, guild: Any, kind: str, row: Any, **details: Any) -> None:
    try:
        await log_action(bot, guild, kind, details={"tournament": row["id"], **details})
    except Exception:
        log.exception("brackets: could not write the %s row", kind)


def told_once(bot: Any, row: Any, what: str, reason: str) -> bool:
    seen = bot.__dict__.setdefault(FAILED_ATTR, set())
    wanted = (int(row["id"]), what, reason)
    if wanted in seen:
        return False
    seen.add(wanted)
    return True


async def failed(bot: Any, guild: Any, row: Any, what: str, reason: str, **details: Any) -> None:
    """Logged every time, written to the action log once per tournament and reason a run."""
    log.warning("brackets: tournament %s %s failed — %s", row["id"], what, reason)
    if not told_once(bot, row, what, reason):
        return
    if what == "thread":
        await note(bot, guild, "brackets.thread_failed", row, reason=reason, **details)
        return
    await note(bot, guild, "brackets.card_failed", row, card=what, reason=reason, **details)


async def find_thread(bot: Any, guild: Any, thread_id: Any) -> tuple[Any, bool]:
    """`(thread, lost)`: lost only on a NotFound, never on a network hiccup."""
    found = shadow.channel_of(bot, guild, thread_id)
    if found is None:
        fetch = getattr(guild, "fetch_channel", None)
        if fetch is None:
            return (None, True)
        try:
            found = await fetch(int(thread_id))
        except discord.NotFound:
            return (None, True)
        except Exception as exc:
            log.info("brackets: could not read thread %s — %s", thread_id, reason_of(exc))
            return (None, False)
    if getattr(found, "archived", False):
        try:
            await found.edit(archived=False)
        except Exception as exc:
            log.warning("brackets: could not reopen thread %s — %s", thread_id, reason_of(exc))
    return (found, False)


def starter_payload(bot: Any, guild: Any, row: Any, people: list[Any]) -> dict[str, Any]:
    return {
        "content": cards.rehearsal_line(bot, guild, row),
        "embed": cards.starter_embed(bot.store, guild.id, row, people),
        "view": cards.starter_view(bot.store, guild.id, row, origin_of(bot)),
        "allowed_mentions": discord.AllowedMentions.none(),
    }


async def make_thread(bot: Any, guild: Any, row: Any) -> Any:
    wanted, rehearsal = parent_id(bot, guild)
    if wanted is None:
        if mode_of(bot.store, guild.id) == ON:
            await failed(bot, guild, row, "thread", "brackets_channel_id is blank")
        else:
            log.warning(
                "brackets: no rehearsal home or log channel, so no thread for %s", row["id"]
            )
        return None
    guard = getattr(bot, "guard", None)
    if guard is not None and hasattr(guard, "allows_channel") and not guard.allows_channel(wanted):
        await failed(bot, guild, row, "thread", "test mode keeps it out of that channel")
        return None
    parent = shadow.channel_of(bot, guild, wanted)
    if parent is None or not hasattr(parent, "create_thread"):
        await failed(bot, guild, row, "thread", f"channel {wanted} cannot hold a thread")
        return None
    people = await store_.entrants(bot.db, row["id"])
    name = " ".join(str(row["name"]).split())[:THREAD_NAME_LIMIT] or f"#{row['id']}"
    first = None
    try:
        if getattr(parent, "type", None) == discord.ChannelType.forum:
            made = await parent.create_thread(
                name=name,
                auto_archive_duration=AUTO_ARCHIVE_MINUTES,
                reason=REASON.format(id=row["id"]),
                **starter_payload(bot, guild, dict(row) | {"shadow": int(rehearsal)}, people),
            )
            thread, first = getattr(made, "thread", made), getattr(made, "message", None)
        else:
            thread = await parent.create_thread(
                name=name,
                type=discord.ChannelType.public_thread,
                auto_archive_duration=AUTO_ARCHIVE_MINUTES,
                reason=REASON.format(id=row["id"]),
            )
    except Exception as exc:
        await failed(bot, guild, row, "thread", reason_of(exc))
        return None
    await store_.update(
        bot.db,
        row["id"],
        {
            "channel_id": int(parent.id),
            "thread_id": int(thread.id),
            "shadow": int(rehearsal),
            "message_id": int(first.id) if first is not None else None,
        },
    )
    if guard is not None and hasattr(guard, "own_channel"):
        guard.own_channel(thread)
    lost_counts(bot).pop(int(row["id"]), None)
    await note(
        bot,
        guild,
        "brackets.thread_made",
        row,
        channel=int(parent.id),
        thread=int(thread.id),
        shadow=rehearsal,
    )
    return thread


async def fresh(bot: Any, guild: Any, tournament_id: int) -> Any:
    return await store_.tournament(bot.db, guild.id, int(tournament_id))


async def ensured(bot: Any, guild: Any, row: Any) -> tuple[Any, Any]:
    """The tournament's thread, made when it has none or was lost twice running; and the row."""
    if row["thread_id"]:
        thread, lost = await find_thread(bot, guild, row["thread_id"])
        if thread is not None:
            lost_counts(bot).pop(int(row["id"]), None)
            return (thread, row)
        if not lost:
            return (None, row)
        counts = lost_counts(bot)
        counts[int(row["id"])] = counts.get(int(row["id"]), 0) + 1
        if counts[int(row["id"])] < LOST_TWICE:
            return (None, row)
        for key in await store_.card_rows(bot.db, row["id"]):
            await store_.set_card(bot.db, row["id"], key, None, None)
        await store_.update(bot.db, row["id"], {"thread_id": None, "message_id": None})
        await note(bot, guild, "brackets.thread_lost", row, thread=int(row["thread_id"]))
    if mode_of(bot.store, guild.id) == OFF:
        return (None, row)
    thread = await make_thread(bot, guild, await fresh(bot, guild, row["id"]))
    return (thread, await fresh(bot, guild, row["id"]))


async def oldest_own(bot: Any, thread: Any) -> Any:
    me = getattr(getattr(bot, "user", None), "id", None)
    try:
        async for message in thread.history(limit=1, oldest_first=True):
            if me is not None and getattr(message.author, "id", None) == me:
                return message
    except Exception as exc:
        log.info("brackets: could not read thread %s — %s", thread.id, reason_of(exc))
    return None


async def post_starter(bot: Any, guild: Any, row: Any, thread: Any, people: list[Any]) -> None:
    adopted = None if row["message_id"] else await oldest_own(bot, thread)
    if adopted is not None:
        await store_.update(bot.db, row["id"], {"message_id": int(adopted.id)})
        await edit_starter(bot, guild, await fresh(bot, guild, row["id"]), thread, people)
        return
    try:
        message = await thread.send(**starter_payload(bot, guild, row, people))
    except Exception as exc:
        await failed(bot, guild, row, STARTER, reason_of(exc))
        return
    await store_.update(bot.db, row["id"], {"message_id": int(message.id)})
    missing(bot).discard((int(row["id"]), STARTER))
    try:
        await message.pin(reason=REASON.format(id=row["id"]))
    except Exception as exc:
        log.info("brackets: could not pin tournament %s's card — %s", row["id"], reason_of(exc))


async def edit_starter(bot: Any, guild: Any, row: Any, thread: Any, people: list[Any]) -> bool:
    """False when the stored card is gone; the reconcile posts it again."""
    try:
        await thread.get_partial_message(int(row["message_id"])).edit(
            **starter_payload(bot, guild, row, people)
        )
    except discord.NotFound:
        missing(bot).add((int(row["id"]), STARTER))
        return False
    except Exception as exc:
        await failed(bot, guild, row, STARTER, reason_of(exc))
    return True


async def sync_starter(
    bot: Any, guild: Any, row: Any, thread: Any, *, edit: bool = True, repost: bool = False
) -> None:
    people = await store_.entrants(bot.db, row["id"])
    if not row["message_id"]:
        await post_starter(bot, guild, row, thread, people)
        return
    if not edit and not repost:
        return
    if await edit_starter(bot, guild, row, thread, people) or not repost:
        return
    await store_.update(bot.db, row["id"], {"message_id": None})
    await note(bot, guild, "brackets.card_reposted", row, card=STARTER)
    await post_starter(bot, guild, await fresh(bot, guild, row["id"]), thread, people)


def set_payload(bot: Any, guild: Any, row: Any, match: Any, people: dict) -> dict[str, Any]:
    return {
        "content": cards.players_line(bot.store, guild.id, match, people),
        "embed": cards.set_embed(bot.store, guild.id, match, people, row["confirm_minutes"]),
        "view": cards.set_view(bot.store, guild.id, row, match),
    }


async def adopt(bot: Any, row: Any, thread: Any, key: str) -> Any:
    """A card posted just before a restart, before its id was stored: found by its buttons."""
    me = getattr(getattr(bot, "user", None), "id", None)
    prefix = cards.set_prefix(row["id"], key)
    try:
        async for message in thread.history(limit=SCAN_LIMIT):
            if getattr(message.author, "id", None) == me and cards.carries(message, prefix):
                return message
    except Exception as exc:
        log.info("brackets: could not read thread %s — %s", thread.id, reason_of(exc))
    return None


async def post_card(
    bot: Any, guild: Any, row: Any, thread: Any, match: Any, people: dict, budget: Budget
) -> None:
    held = (await store_.card_rows(bot.db, row["id"])).get(match.key, (None, None))
    if held[1] and not held[0]:
        found = await adopt(bot, row, thread, match.key)
        if found is not None:
            await store_.set_card(bot.db, row["id"], match.key, int(found.id), held[1])
            await edit_card(bot, guild, row, thread, match, people, int(found.id))
            return
    if not budget.take():
        return
    stamp = store_.stamp()
    await store_.set_card(bot.db, row["id"], match.key, None, stamp)
    payload = set_payload(bot, guild, row, match, people)
    users = cards.player_ids(match, people)
    try:
        message = await thread.send(
            **payload, allowed_mentions=cards.ping_mentions(users, rehearsal=rehearsing(row))
        )
    except Exception as exc:
        await store_.set_card(bot.db, row["id"], match.key, None, None)
        await failed(bot, guild, row, match.key, reason_of(exc))
        return
    await store_.set_card(bot.db, row["id"], match.key, int(message.id), stamp)
    missing(bot).discard((int(row["id"]), match.key))


async def edit_card(
    bot: Any, guild: Any, row: Any, thread: Any, match: Any, people: dict, message_id: int
) -> bool:
    try:
        await thread.get_partial_message(int(message_id)).edit(
            **set_payload(bot, guild, row, match, people),
            allowed_mentions=discord.AllowedMentions.none(),
        )
    except discord.NotFound:
        missing(bot).add((int(row["id"]), match.key))
        return False
    except Exception as exc:
        await failed(bot, guild, row, match.key, reason_of(exc))
    return True


async def clear_card(
    bot: Any, guild: Any, row: Any, thread: Any, key: str, message_id: int
) -> None:
    try:
        await thread.get_partial_message(int(message_id)).edit(
            content=None,
            embed=cards.cleared_embed(bot.store, guild.id, key),
            view=None,
            allowed_mentions=discord.AllowedMentions.none(),
        )
    except discord.NotFound:
        return
    except Exception as exc:
        await failed(bot, guild, row, key, reason_of(exc))


async def sync_card(
    bot: Any,
    guild: Any,
    row: Any,
    thread: Any,
    match: Any,
    people: dict,
    held: tuple[int | None, str | None],
    budget: Budget,
    *,
    repost: bool = False,
) -> None:
    message_id = held[0]
    if match.state in cards.CLEARED:
        if message_id:
            await clear_card(bot, guild, row, thread, match.key, message_id)
            await store_.set_card(bot.db, row["id"], match.key, None, None)
        return
    if message_id:
        if await edit_card(bot, guild, row, thread, match, people, message_id) or not repost:
            return
        if match.state == COMPLETE:
            await store_.set_card(bot.db, row["id"], match.key, None, None)
            return
        await store_.set_card(bot.db, row["id"], match.key, None, None)
        await note(bot, guild, "brackets.card_reposted", row, card=match.key)
    if match.state in cards.OPEN_CARD:
        await post_card(bot, guild, row, thread, match, people, budget)


async def ping_start(bot: Any, guild: Any, row: Any, thread: Any) -> None:
    role_id = as_id(bot.store.get(guild.id, BRACKETS_PING_ROLE))
    if role_id is None:
        return
    text = cards.words(
        bot.store, guild.id, "brackets_start_ping", role=f"<@&{role_id}>", name=row["name"]
    )
    rehearsal = rehearsing(row) or mode_of(bot.store, guild.id) != ON
    mentions = (
        discord.AllowedMentions.none()
        if rehearsal
        else discord.AllowedMentions(
            everyone=False, users=False, roles=[discord.Object(id=role_id)]
        )
    )
    try:
        await thread.send(text, allowed_mentions=mentions)
    except Exception as exc:
        await failed(bot, guild, row, "ping", reason_of(exc))
        return
    if rehearsal:
        await note(bot, guild, "brackets.would_ping", row, role=role_id)


async def sync(
    bot: Any,
    guild: Any,
    row: Any,
    *,
    keys: tuple[str, ...] | None = None,
    gone: dict[str, int] | None = None,
    budget: Budget | None = None,
    full: bool = False,
    started: bool = False,
    starter: bool = True,
) -> None:
    """Under the tournament's card lock: the thread, the starter card, then the set cards."""
    budget = budget if budget is not None else Budget()
    async with card_lock(bot, row["id"]):
        thread, row = await ensured(bot, guild, await fresh(bot, guild, row["id"]))
        if thread is None or row is None:
            return
        lost = missing(bot)
        await sync_starter(
            bot,
            guild,
            row,
            thread,
            edit=starter or full,
            repost=full or (int(row["id"]), STARTER) in lost,
        )
        row = await fresh(bot, guild, row["id"])
        if started:
            await ping_start(bot, guild, row, thread)
        for key, message_id in (gone or {}).items():
            await clear_card(bot, guild, row, thread, key, message_id)
        current = await store_.bracket(bot.db, row)
        if current is None:
            return
        people = {one["id"]: one for one in await store_.entrants(bot.db, row["id"])}
        held = await store_.card_rows(bot.db, row["id"])
        for match in current.ordered():
            wanted = keys is None or match.key in keys
            redo = full or (int(row["id"]), match.key) in lost
            if (
                not wanted
                and not redo
                and not (
                    match.state in cards.OPEN_CARD and not held.get(match.key, (None, None))[0]
                )
            ):
                continue
            await sync_card(
                bot,
                guild,
                row,
                thread,
                match,
                people,
                held.get(match.key, (None, None)),
                budget,
                repost=redo,
            )


async def follow(
    bot: Any, guild: Any, tournament_id: Any, outcome: Any, *, move: str | None = None
) -> None:
    """After any move, from either door: the cards catch up. Never raises — it is cosmetic."""
    try:
        if not getattr(outcome, "ok", False) or tournament_id is None:
            return
        row = await fresh(bot, guild, int(tournament_id))
        if row is None:
            return
        await sync(
            bot,
            guild,
            row,
            keys=None if move in EVERY_CARD else tuple(outcome.changed),
            gone=dict(outcome.gone),
            started=move == START,
        )
    except Exception:
        log.exception("brackets: the cards for tournament %s did not catch up", tournament_id)


async def reconcile(
    bot: Any, guild: Any, *, full: bool = False, budget: Budget | None = None
) -> None:
    """Every live tournament: thread, starter card and a card for each open set, by stored id."""
    if getattr(guild, "unavailable", False) or mode_of(bot.store, guild.id) == OFF:
        return
    budget = budget if budget is not None else Budget()
    for row in await store_.tournaments(bot.db, guild.id):
        if row["state"] not in LIVE:
            continue
        try:
            await sync(bot, guild, row, keys=(), budget=budget, full=full, starter=False)
        except Exception:
            log.exception("brackets: reconciling tournament %s failed", row["id"])


async def sweep(bot: Any, guild: Any) -> None:
    """The minute's work: reports that stand, check-ins that close, then the cards catch up."""
    if getattr(guild, "unavailable", False) or mode_of(bot.store, guild.id) == OFF:
        return
    confirmed = await brackets_sets.confirm_due(bot, guild)
    closed = await brackets_people.close_due_check_ins(bot, guild)
    budget = Budget()
    for tournament_id in dict.fromkeys([*(one for one, _ in confirmed), *closed]):
        row = await fresh(bot, guild, tournament_id)
        if row is None:
            continue
        keys = tuple(key for one, key in confirmed if one == tournament_id)
        try:
            await sync(bot, guild, row, keys=keys, budget=budget)
        except Exception:
            log.exception("brackets: the sweep's cards for tournament %s failed", tournament_id)
    await reconcile(bot, guild, budget=budget)


async def dm(member: Any, text: str) -> bool:
    send = getattr(member, "send", None)
    if send is None:
        return False
    try:
        await send(text, allowed_mentions=discord.AllowedMentions.none())
    except Exception as exc:
        log.info("brackets: could not DM %s — %s", getattr(member, "id", "?"), reason_of(exc))
        return False
    return True


async def tell(
    bot: Any, guild: Any, row: Any, user_id: Any, key: str, reason: str = "", **fields: Any
) -> None:
    """An organiser's move that lands on a member: they are told, with the reason given."""
    wanted = as_id(user_id)
    if wanted is None or row is None:
        return
    text = cards.words(bot.store, guild.id, key, name=row["name"], **fields)
    words = " ".join(str(reason or "").split())
    if words:
        text = f"{text}\n{cards.words(bot.store, guild.id, 'brackets_dm_reason', reason=words)}"
    details = {"tournament": row["id"], "dm": key}
    try:
        if mode_of(bot.store, guild.id) != ON or rehearsing(row):
            await log_action(bot, guild, "brackets.would_dm", target=wanted, details=details)
            return
        member = guild.get_member(wanted) if hasattr(guild, "get_member") else None
        if member is None or not await dm(member, text):
            await log_action(bot, guild, "brackets.dm_failed", target=wanted, details=details)
    except Exception:
        log.exception("brackets: the DM to %s was not recorded", wanted)


__all__ = [
    "Budget",
    "card_lock",
    "ensured",
    "follow",
    "make_thread",
    "parent_id",
    "reconcile",
    "sweep",
    "sync",
    "tell",
]
