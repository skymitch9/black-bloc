"""The starter card's bracket picture: what to draw, drawn off the loop, kept by fingerprint."""

from __future__ import annotations

import asyncio
import logging
from io import BytesIO
from typing import Any

import discord

from . import brackets_cards as cards
from . import brackets_store as store_
from .actionlog import log_action
from .brackets import play, pools
from .brackets.model import COMPLETE, SINGLE, BracketError
from .brackets.picture import Extra, Words, fingerprint, render, scene
from .settings_store import BRACKETS_PICTURE, BRACKETS_PICTURE_MAX, BRACKETS_VOTES_VISIBLE

log = logging.getLogger(__name__)

FILENAME = "bracket.png"
DRAWN_ATTR = "_brackets_pictures"
FAILING_ATTR = "_brackets_picture_failing"
HEAD_SPLIT = "|"


def drawn(bot: Any) -> dict[int, tuple[str, bytes]]:
    return bot.__dict__.setdefault(DRAWN_ATTR, {})


def failing(bot: Any) -> set[int]:
    return bot.__dict__.setdefault(FAILING_ATTR, set())


def active(people: list[Any]) -> list[Any]:
    return [one for one in people if not one["dropped"] and not one["dq"]]


def preview(row: Any, people: list[Any]) -> Any:
    """Before the start: the bracket Start would build from today's seed order, or None."""
    ids = [one["id"] for one in active(people)]
    if len(ids) < 2:
        return None
    plan = store_.plan_of(row)
    try:
        if plan is None:
            return play.build(ids, store_.options_of(row)).bracket
        return pools.build(ids, store_.options_of(row), plan).bracket
    except BracketError:
        return None


async def bracket_of(bot: Any, row: Any, people: list[Any]) -> Any:
    found = await store_.bracket(bot.db, row)
    if found is None and row["state"] in store_.BEFORE_START:
        return preview(row, people)
    return found


def sports_line(store: Any, gid: int, match: Any, meta: dict[str, Any]) -> str | None:
    a_score = "–" if match.score_a is None else match.score_a
    b_score = "–" if match.score_b is None else match.score_b
    if match.state == COMPLETE and match.score_a is not None:
        return cards.words(
            store, gid, "brackets_score_final_line", a_score=a_score, b_score=b_score
        )
    if meta.get("live_status") == "live":
        return cards.words(
            store,
            gid,
            "brackets_score_live_line",
            period=meta.get("period_words") or "",
            a_score=a_score,
            b_score=b_score,
        ).strip(" ·")
    return None


async def extras_of(bot: Any, gid: int, row: Any, bracket: Any) -> dict[str, Extra]:
    if store_.is_sports(row):
        metas = await store_.sports_rows(bot.db, row["id"])
        return {
            key: Extra(
                line=sports_line(bot.store, gid, match, metas.get(key) or {}),
                held=bool((metas.get(key) or {}).get("held")),
            )
            for key, match in bracket.matches.items()
        }
    if not store_.votes_decide(row) or not bot.store.get(gid, BRACKETS_VOTES_VISIBLE):
        return {}
    return {
        key: Extra(votes=(held["a"], held["b"]))
        for key, held in (await store_.ballots(bot.db, row["id"])).items()
        if not held["closed_at"]
        and key in bracket.matches
        and bracket.matches[key].state in store_.VOTE_OPEN
    }


def champion_of(store: Any, gid: int, row: Any, people: list[Any]) -> str:
    if row["state"] != store_.COMPLETE:
        return ""
    first = next((one for one in people if one["placement"] == 1), None)
    if first is None:
        return ""
    return cards.words(store, gid, "brackets_picture_champion_line", name=first["name"])


def words_of(store: Any, gid: int, row: Any, people: list[Any], bracket: Any) -> Words:
    kind = store_.kind_of(row)
    form = SINGLE if store_.is_sports(row) else row["format"]
    heads = cards.words(store, gid, "brackets_picture_standings_head").split(HEAD_SPLIT)
    return Words(
        title=str(row["name"]),
        format=cards.words(store, gid, cards.FORMAT_KEYS.get(form, cards.FORMAT_KEYS[SINGLE])),
        state=cards.capitalised(cards.state_words(store, gid, row["state"])),
        kind=cards.words(store, gid, cards.KIND_KEYS[kind]) if kind in cards.KIND_KEYS else "",
        champion=champion_of(store, gid, row, people),
        held=cards.words(store, gid, "brackets_held_note"),
        heads=tuple(one.strip() for one in heads),
        rounds={
            key: cards.round_words(store, gid, match) for key, match in bracket.matches.items()
        },
        pools={
            number: cards.words(store, gid, "brackets_pool_title", pool=pools.letter(number))
            for number in range(1, (bracket.plan.count if bracket.plan else 0) + 1)
        },
    )


async def failed(bot: Any, guild: Any, row: Any, reason: str) -> None:
    try:
        details = {"tournament": row["id"], "reason": reason}
        await log_action(bot, guild, "brackets.picture_failed", details=details)
    except Exception:
        log.exception("brackets: could not write the picture_failed row")


async def back(bot: Any, guild: Any, row: Any) -> None:
    try:
        await log_action(bot, guild, "brackets.picture_back", details={"tournament": row["id"]})
    except Exception:
        log.exception("brackets: could not write the picture_back row")


async def picture_of(bot: Any, guild: Any, row: Any, people: list[Any]) -> bytes | None:
    """The PNG, or None when there is nothing to draw or drawing failed (logged once a streak)."""
    tid = int(row["id"])
    try:
        bracket = await bracket_of(bot, row, people)
        if bracket is None:
            return None
        made = scene(
            bracket,
            {one["id"]: str(one["name"]) for one in people},
            words_of(bot.store, guild.id, row, people, bracket),
            await extras_of(bot, guild.id, row, bracket),
        )
        mark = fingerprint(made)
        kept = drawn(bot).get(tid)
        if kept is not None and kept[0] == mark:
            data = kept[1]
        else:
            data = await asyncio.to_thread(render, made)
            drawn(bot)[tid] = (mark, data)
    except Exception as exc:
        log.warning("brackets: tournament %s's picture was not drawn — %r", tid, exc)
        if tid not in failing(bot):
            failing(bot).add(tid)
            await failed(bot, guild, row, repr(exc)[:200])
        return None
    if tid in failing(bot):
        failing(bot).discard(tid)
        await back(bot, guild, row)
    return data


def too_big(store: Any, gid: int, embed: Any, count: int, most: int) -> None:
    line = cards.words(store, gid, "brackets_picture_too_big_line", count=count, most=most)
    text = "\n".join(part for part in (embed.description, line) if part)
    embed.description = text[:4000]


async def dressed(
    bot: Any, guild: Any, row: Any, people: list[Any], payload: dict[str, Any], *, editing: bool
) -> dict[str, Any]:
    """The starter payload and its picture: `file` to send, a replacing `attachments` to edit."""
    gid = guild.id
    data = None
    if bot.store.get(gid, BRACKETS_PICTURE):
        count = len(active(people))
        most = int(bot.store.get(gid, BRACKETS_PICTURE_MAX) or 0)
        if most and count > most:
            too_big(bot.store, gid, payload["embed"], count, most)
        else:
            data = await picture_of(bot, guild, row, people)
    if data is None:
        if editing:
            payload["attachments"] = []
        return payload
    file = discord.File(BytesIO(data), filename=FILENAME)
    payload["embed"].set_image(url=f"attachment://{FILENAME}")
    payload["attachments" if editing else "file"] = [file] if editing else file
    return payload


__all__ = ["FILENAME", "dressed", "picture_of", "preview"]
