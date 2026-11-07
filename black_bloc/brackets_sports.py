"""Sports brackets: Import from the feed, Build by hand, Sync, a set edited or held by hand."""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime
from typing import Any

from . import brackets_store as store_
from .brackets import play, sports_shape
from .brackets.model import COMPLETE, DONE, OPEN, WAITING, A, B
from .brackets_moves import (
    actor_id,
    answered,
    bad_option,
    done,
    engine,
    league_of,
    loaded,
    lock_for,
    note,
    now_stamp,
    require_on,
    require_runner,
    require_state,
    said,
    stop,
    touched,
    when,
)
from .brackets_sets import overridden, the_set
from .logkinds import VIA_DISCORD
from .panels import Outcome
from .settings_store import DEFAULT_TIMEZONE_KEY
from .sports import feeds
from .sports.model import FINAL, LIVE, SCHEDULED, SOURCE_NAMES, STATUSES
from .timezones import DEFAULT_TZ, zone

log = logging.getLogger(__name__)

FEED_HOW = "feed"
SCORE_LIMIT = 999
EDIT_FIELDS = ("scheduled_at", "score_a", "score_b", "live_status", "slot_a", "slot_b")
REASON_LIMIT = 300


def fetch_of(bot: Any) -> Any:
    return getattr(bot, "sports_fetch", None)


def require_sports(bot: Any, guild: Any, row: Any) -> None:
    if not store_.is_sports(row):
        raise stop(bot, guild, "not_sports", "not_sports", 409, name=row["name"])


def require_fed(bot: Any, guild: Any, row: Any) -> None:
    require_sports(bot, guild, row)
    if not store_.fed(row):
        raise stop(bot, guild, "not_fed", "not_fed", 409, name=row["name"])


async def fetched_bracket(bot: Any, row: Any) -> Any:
    return await feeds.bracket(league_of(row), str(row["season"] or ""), fetch=fetch_of(bot))


def round_of(game: Any) -> int:
    return game.round if isinstance(game.round, int) and game.round >= 0 else 1


def teams_of(found: Any) -> list[str]:
    seen: list[str] = []
    for game in found.games:
        for ext_id in (game.a_ext_id, game.b_ext_id):
            if ext_id and ext_id not in seen:
                seen.append(ext_id)
    for ext_id in found.seeds:
        if ext_id not in seen:
            seen.append(ext_id)
    return sorted(seen, key=lambda one: (found.seeds.get(one) or 99, seen.index(one)))


def live_values(game: Any) -> dict[str, Any]:
    return {
        "scheduled_at": game.starts_at,
        "live_status": game.status if game.status in STATUSES else SCHEDULED,
        "period_words": game.period_words,
    }


async def stored_people(bot: Any, row: Any) -> list[Any]:
    return await store_.entrants(bot.db, row["id"])


async def replaced_ok(bot: Any, guild: Any, row: Any, replace: bool, key: str, code: str) -> None:
    has = await store_.entrants(bot.db, row["id"]) or await store_.sets(bot.db, row["id"])
    if has and not replace:
        raise stop(bot, guild, key, code, 409, name=row["name"])


@answered
async def import_bracket(
    bot: Any,
    guild: Any,
    actor: Any,
    tournament_id: int,
    *,
    replace: bool = False,
    via: str = VIA_DISCORD,
) -> Outcome:
    """Teams and sets from the feed; again before the start replaces everything, once asked."""
    require_on(bot, guild)
    row = await loaded(bot, guild, tournament_id)
    require_runner(bot, guild, actor)
    require_fed(bot, guild, row)
    require_state(bot, guild, row, store_.DRAFT, store_.SEEDING)
    await replaced_ok(bot, guild, row, replace, "brackets_reimport_asks", "confirm_reimport")
    answer = await fetched_bracket(bot, row)
    async with lock_for(bot, tournament_id):
        row = await loaded(bot, guild, tournament_id)
        require_fed(bot, guild, row)
        require_state(bot, guild, row, store_.DRAFT, store_.SEEDING)
        await replaced_ok(bot, guild, row, replace, "brackets_reimport_asks", "confirm_reimport")
        if not answer.ok:
            raise stop(bot, guild, "feed_failed", "feed_down", 502, why=answer.why)
        found = answer.value
        if not found.games:
            name = SOURCE_NAMES.get(answer.via, answer.via or "")
            raise stop(bot, guild, "no_games", "no_games", 409, source=name, name=row["name"])
        gone = await store_.clear_sets(bot.db, row["id"])
        await store_.clear_entrants(bot.db, row["id"])
        ids: dict[str, int] = {}
        for ext_id in teams_of(found):
            entrant = await store_.add_entrant(
                bot.db,
                row["id"],
                found.names.get(ext_id) or ext_id,
                user_id=None,
                added_by=actor_id(actor),
                ext_source=answer.via,
                ext_id=ext_id,
            )
            await store_.update_entrant(bot.db, entrant, {"seed": found.seeds.get(ext_id)})
            ids[ext_id] = entrant
        planned = [
            sports_shape.Planned(
                game.source_key,
                round_of(game),
                ids.get(game.a_ext_id) if game.a_ext_id else None,
                ids.get(game.b_ext_id) if game.b_ext_id else None,
                found.best_of.get(game.source_key, 1),
            )
            for game in found.games
        ]
        bracket, sources = sports_shape.shaped(planned, found.links)
        stamp = now_stamp()
        play.settle(bracket, stamp)
        await store_.save(bot.db, row["id"], bracket, list(bracket.matches), [])
        by_key = {game.source_key: game for game in found.games}
        for key, source_key in sources.items():
            values = {"source_key": source_key, **live_values(by_key[source_key])}
            await store_.write_sports(bot.db, row["id"], key, values)
        await store_.update(bot.db, row["id"], {**feed_ok(stamp), "source": answer.via})
        await note(
            bot,
            guild,
            "imported",
            actor,
            row["id"],
            via,
            teams=len(ids),
            sets=len(sources),
            source=answer.via,
            replaced=bool(replace),
        )
        outcome = done(
            bot,
            guild,
            "imported",
            row["id"],
            name=row["name"],
            teams=len(ids),
            sets=len(sources),
            source=SOURCE_NAMES.get(answer.via, answer.via),
        )
        return Outcome(True, outcome.message, value=row["id"], gone=gone)


@answered
async def build(
    bot: Any,
    guild: Any,
    actor: Any,
    tournament_id: int,
    *,
    replace: bool = False,
    via: str = VIA_DISCORD,
) -> Outcome:
    """Single elimination from the entrants and their seeds, byes included, through the engine."""
    require_on(bot, guild)
    async with lock_for(bot, tournament_id):
        row = await loaded(bot, guild, tournament_id)
        require_runner(bot, guild, actor)
        require_sports(bot, guild, row)
        require_state(bot, guild, row, store_.DRAFT, store_.SEEDING)
        if await store_.sets(bot.db, row["id"]) and not replace:
            raise stop(bot, guild, "rebuild_asks", "confirm_rebuild", 409, name=row["name"])
        people = [one for one in await stored_people(bot, row) if not one["dropped"]]
        names = {"name": row["name"], "count": len(people)}
        ids = [one["id"] for one in people]
        built = engine(bot, guild, row, names, play.build, ids, store_.options_of(row), now_stamp())
        gone = await store_.clear_sets(bot.db, row["id"])
        await store_.save(bot.db, row["id"], built.bracket, built.changed, [])
        await note(bot, guild, "built", actor, row["id"], via, entrants=len(ids))
        sets = sum(1 for one in built.bracket.matches.values() if one.state not in DONE)
        outcome = done(bot, guild, "built", row["id"], name=row["name"], sets=sets)
        return Outcome(True, outcome.message, value=row["id"], gone=gone)


def feed_ok(stamp: str) -> dict[str, Any]:
    return {"feed_ok_at": stamp, "feed_failed_at": None, "feed_failures": 0, "feed_error": None}


def entrant_map(people: list[Any], via: str | None) -> dict[str, int]:
    return {
        str(one["ext_id"]): one["id"]
        for one in people
        if one["ext_id"] and (via is None or store_.column(one, "ext_source") == via)
    }


def ext_of(people: dict[int, Any], entrant: int | None, via: str | None = None) -> str | None:
    found = people.get(entrant) if entrant is not None else None
    if found is None or not found["ext_id"]:
        return None
    if via is not None and store_.column(found, "ext_source") != via:
        return None
    return str(found["ext_id"])


def oriented(game: Any, a_ext: str | None, b_ext: str | None) -> tuple[Any, Any] | None:
    if (game.a_ext_id, game.b_ext_id) == (a_ext, b_ext):
        return game.a_score, game.b_score
    if (game.a_ext_id, game.b_ext_id) == (b_ext, a_ext):
        return game.b_score, game.a_score
    return None


def paired(scores: list[Any], a_ext: str | None, b_ext: str | None, on: Any) -> Any:
    """A set with no feed key: the day's game between the same two teams, either way round."""
    if not a_ext or not b_ext:
        return None
    for game in scores:
        if {game.a_ext_id, game.b_ext_id} != {a_ext, b_ext}:
            continue
        starts = play.parsed(game.starts_at)
        if on is None or starts is None or starts.date() == on:
            return game
    return None


def seated_by_feed(match: Any, game: Any, ids: dict[str, int]) -> bool:
    """An empty slot takes the team the feed names on that side, unless it is already in."""
    moved = False
    for slot, ext_id in ((A, game.a_ext_id), (B, game.b_ext_id)):
        entrant = ids.get(ext_id) if ext_id else None
        if entrant is None or match.holds(entrant) or match.slot(slot) is not None:
            continue
        play.put(match, slot, entrant)
        moved = True
    return moved


async def failed_feed(bot: Any, guild: Any, row: Any, why: str, via: str) -> None:
    """A failure streak is logged once; the bracket keeps saying since when."""
    first = not int(store_.column(row, "feed_failures") or 0)
    values = {"feed_failures": int(store_.column(row, "feed_failures") or 0) + 1}
    values["feed_error"] = str(why or "")[:300]
    if first:
        values["feed_failed_at"] = now_stamp()
    await store_.update(bot.db, row["id"], values)
    if first:
        await note(bot, guild, "feed_failed", None, row["id"], via, why=values["feed_error"])


async def back_again(bot: Any, guild: Any, row: Any, via: str, source: str | None) -> None:
    if int(store_.column(row, "feed_failures") or 0):
        name = SOURCE_NAMES.get(source or "", source or "")
        line = said(bot.store, guild.id, "brackets_feed_back_line", source=name)
        await note(
            bot,
            guild,
            "feed_back",
            None,
            row["id"],
            via,
            failures=int(store_.column(row, "feed_failures") or 0),
            line=line,
        )
    await store_.update(bot.db, row["id"], feed_ok(now_stamp()))


async def structured(bot: Any, row: Any, found: Any, ids: dict[str, int], stamp: str) -> list:
    """Teams the feed now names fill empty slots and links the feed now knows are written."""
    current = await store_.bracket(bot.db, row)
    meta = await store_.sports_rows(bot.db, row["id"])
    if current is None:
        return []
    keyed = {value["source_key"]: key for key, value in meta.items() if value["source_key"]}
    work = play.working(current)
    for game in found.games:
        key = keyed.get(game.source_key)
        match = work.matches.get(key) if key else None
        if match is None or meta[key]["held"] or match.state in DONE:
            continue
        if seated_by_feed(match, game, ids):
            for slot in (A, B):
                if match.slot(slot) is not None:
                    sports_shape.let_go(work, match.key, slot)
        target = found.links.get(game.source_key)
        to_key = keyed.get(target[0]) if target else None
        if to_key and match.winner_to is None and not meta[to_key]["held"]:
            match.winner_to, match.winner_slot = to_key, target[1]
            sports_shape.let_go(work, to_key, target[1])
    moved = play.moved(work, current, stamp)
    if moved.changed or moved.removed:
        await store_.save(bot.db, row["id"], moved.bracket, moved.changed, moved.removed)
    return [*moved.changed, *moved.removed]


async def scored(
    bot: Any,
    guild: Any,
    row: Any,
    game: Any,
    key: str,
    people: dict[int, Any],
    via: str,
    stamp: str,
) -> tuple[list[str], bool]:
    """One set against its game: live words and score, or the final through the override."""
    current = await store_.bracket(bot.db, row)
    match = current.matches.get(key) if current is not None else None
    meta = (await store_.sports_rows(bot.db, row["id"])).get(key)
    if match is None or meta is None or meta["held"]:
        return [], False
    wanted = live_values(game)
    if game.starts_at is None:
        wanted["scheduled_at"] = meta["scheduled_at"]
    score = oriented(game, ext_of(people, match.slot_a), ext_of(people, match.slot_b))
    if score is None or match.state == WAITING:
        if game.status == FINAL:
            wanted.pop("live_status")
        return ([key] if await rewrote(bot, row, key, meta, wanted) else []), False
    final = game.status == FINAL and None not in score and score[0] != score[1]
    if final:
        side = A if score[0] > score[1] else B
        if (
            match.state == COMPLETE
            and match.winner == match.slot(side)
            and (
                match.score_a,
                match.score_b,
            )
            == tuple(score)
        ):
            return ([key] if await rewrote(bot, row, key, meta, wanted) else []), False
        if match.state == COMPLETE and meta["decided_by"] != store_.FEED:
            return [], False
        outcome = await overridden(
            bot,
            guild,
            None,
            row,
            current,
            people,
            match,
            via,
            event="feed_result",
            extra={"by": FEED_HOW, "source_key": game.source_key},
            score_a=score[0],
            score_b=score[1],
            winner=side,
            free=True,
            how=FEED_HOW,
        )
        await store_.write_sports(
            bot.db, row["id"], key, {**wanted, "decided_by": store_.FEED, "held": 0}
        )
        return list(outcome.changed) or [key], True
    if match.state not in OPEN:
        return [], False
    changed = await rewrote(bot, row, key, meta, wanted)
    if (match.score_a, match.score_b) != tuple(score) and game.status == LIVE:
        work = play.working(current)
        work.matches[key].score_a, work.matches[key].score_b = score
        await store_.save(bot.db, row["id"], work, [key], [])
        changed = True
    return ([key] if changed else []), False


async def rewrote(bot: Any, row: Any, key: str, meta: dict, wanted: dict) -> bool:
    fresh = {name: value for name, value in wanted.items() if meta.get(name) != value}
    if fresh:
        await store_.write_sports(bot.db, row["id"], key, fresh)
    return bool(fresh)


async def applied(
    bot: Any,
    guild: Any,
    tournament_id: int,
    answer: Any,
    scores: Any = None,
    *,
    actor: Any = None,
    via: str = VIA_DISCORD,
) -> tuple[list[str], int] | None:
    """Under the tournament's lock: a feed's answer written to one running bracket; answers the
    changed set keys and how many sets the feed decided, or None when the feed failed."""
    async with lock_for(bot, tournament_id):
        row = await store_.tournament(bot.db, guild.id, int(tournament_id))
        if row is None or row["state"] != store_.RUNNING or not store_.fed(row):
            return [], 0
        if not answer.ok:
            await failed_feed(bot, guild, row, answer.why, via)
            return None
        await back_again(bot, guild, row, via, answer.via)
        row = await store_.tournament(bot.db, guild.id, int(tournament_id))
        stamp = now_stamp()
        everyone = await stored_people(bot, row)
        ids = entrant_map(everyone, answer.via)
        people = {one["id"]: one for one in everyone}
        changed = await structured(bot, row, answer.value, ids, stamp)
        decided = 0
        meta = await store_.sports_rows(bot.db, row["id"])
        keyed = {value["source_key"]: key for key, value in meta.items() if value["source_key"]}
        games = sorted(answer.value.games, key=round_of)
        for game in games:
            key = keyed.get(game.source_key)
            if key is None:
                continue
            found, final = await scored(bot, guild, row, game, key, people, via, stamp)
            changed += found
            decided += int(final)
        if scores is not None and scores.ok:
            loose = await unkeyed(bot, row, meta)
            for key in loose:
                current = await store_.bracket(bot.db, row)
                match = current.matches[key]
                on = local_day(bot, guild, meta[key]["scheduled_at"])
                game = paired(
                    scores.value,
                    ext_of(people, match.slot_a, scores.via),
                    ext_of(people, match.slot_b, scores.via),
                    on,
                )
                if game is None:
                    continue
                found, final = await scored(bot, guild, row, game, key, people, via, stamp)
                changed += found
                decided += int(final)
        keys = list(dict.fromkeys(one for one in changed if not sports_shape.is_pending(one)))
        if keys:
            await note(
                bot,
                guild,
                "synced",
                actor,
                row["id"],
                via,
                sets=keys,
                decided=decided,
                source=answer.via,
            )
        return keys, decided


async def unkeyed(bot: Any, row: Any, meta: dict) -> list[str]:
    current = await store_.bracket(bot.db, row)
    if current is None:
        return []
    return [
        key
        for key, match in current.matches.items()
        if not sports_shape.is_pending(match)
        and not (meta.get(key) or {}).get("source_key")
        and not (meta.get(key) or {}).get("held")
        and match.state in (*OPEN, COMPLETE)
    ]


def local_day(bot: Any, guild: Any, stamp: Any) -> date | None:
    found = play.parsed(stamp)
    if found is None:
        return None
    name = bot.store.get(guild.id, DEFAULT_TIMEZONE_KEY) or DEFAULT_TZ
    return found.astimezone(zone(name) or zone(DEFAULT_TZ) or UTC).date()


def today_of(bot: Any, guild: Any, now: datetime | None = None) -> date:
    moment = (now or datetime.now(UTC)).astimezone(UTC)
    name = bot.store.get(guild.id, DEFAULT_TIMEZONE_KEY) or DEFAULT_TZ
    return moment.astimezone(zone(name) or zone(DEFAULT_TZ) or UTC).date()


async def wants_scores(bot: Any, row: Any) -> bool:
    meta = await store_.sports_rows(bot.db, row["id"])
    return bool(await unkeyed(bot, row, meta))


@answered
async def sync_now(
    bot: Any, guild: Any, actor: Any, tournament_id: int, *, via: str = VIA_DISCORD
) -> Outcome:
    """Staff read the feed at once; the feed call is never made under the tournament's lock."""
    require_on(bot, guild)
    row = await loaded(bot, guild, tournament_id)
    require_runner(bot, guild, actor)
    require_fed(bot, guild, row)
    require_state(bot, guild, row, store_.RUNNING)
    answer = await fetched_bracket(bot, row)
    scores = None
    if answer.ok and await wants_scores(bot, row):
        scores = await feeds.scores(league_of(row), today_of(bot, guild), fetch=fetch_of(bot))
    found = await applied(bot, guild, row["id"], answer, scores, actor=actor, via=via)
    if found is None:
        raise stop(bot, guild, "feed_failed", "feed_down", 502, why=answer.why)
    keys, decided = found
    key = "synced" if keys else "synced_none"
    outcome = done(bot, guild, key, row["id"], name=row["name"], count=len(keys))
    return Outcome(True, outcome.message, value=row["id"], changed=tuple(keys))


def score_given(bot: Any, guild: Any, given: dict[str, Any], field: str) -> int | None:
    value = given.get(field)
    if value in (None, ""):
        return None
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= SCORE_LIMIT:
        raise bad_option(bot, guild, given)(field, f"a whole number from 0 to {SCORE_LIMIT}")
    return value


def status_given(bot: Any, guild: Any, given: dict[str, Any]) -> str | None:
    value = given.get("live_status")
    if value in (None, ""):
        return None
    if value not in STATUSES:
        raise bad_option(bot, guild, given)("live_status", ", ".join(STATUSES))
    return value


def entrant_given(bot: Any, guild: Any, given: dict, field: str, people: dict) -> int | None:
    value = given.get(field)
    if value in (None, ""):
        return None
    try:
        found = int(value)
    except (TypeError, ValueError):
        found = 0
    person = people.get(found)
    if person is None or person["dropped"] or person["dq"]:
        raise bad_option(bot, guild, given)(field, "an entrant of this bracket")
    return found


def reseated(work: Any, match: Any, slot: str, entrant: int | None) -> None:
    play.put(match, slot, entrant)
    if entrant is None:
        sports_shape.hold_open(work)
    else:
        sports_shape.let_go(work, match.key, slot)
    if match.state != WAITING and (match.slot_a is None or match.slot_b is None):
        play.reset_state(match)


@answered
async def edit_set(
    bot: Any,
    guild: Any,
    actor: Any,
    tournament_id: int,
    key: str,
    given: dict[str, Any],
    *,
    via: str = VIA_DISCORD,
) -> Outcome:
    """Time, score line, status and (on a set with no result) its teams, by hand; the set is then
    held against the feed until Release hold."""
    require_on(bot, guild)
    async with lock_for(bot, tournament_id):
        row = await loaded(bot, guild, tournament_id)
        require_runner(bot, guild, actor)
        require_sports(bot, guild, row)
        require_state(bot, guild, row, *store_.BEFORE_START, store_.RUNNING)
        current = await store_.bracket(bot.db, row)
        if current is not None and sports_shape.is_pending(str(key)):
            current = None
        match = the_set(bot, guild, row, current, key)
        everyone = await stored_people(bot, row)
        people = {one["id"]: one for one in everyone}
        reason = " ".join(str((given or {}).get("reason") or "").split())[:REASON_LIMIT]
        given = {name: value for name, value in (given or {}).items() if name in EDIT_FIELDS}
        if not given:
            raise stop(bot, guild, "nothing_to_edit", "nothing_to_edit", 400, set=match.key)
        sports: dict[str, Any] = {"decided_by": store_.STAFF, "held": 1}
        if "scheduled_at" in given:
            bad = bad_option(bot, guild, given)
            sports["scheduled_at"] = when(
                bot, guild, given["scheduled_at"], lambda _, allowed: bad("scheduled_at", allowed)
            )
        if "live_status" in given:
            sports["live_status"] = status_given(bot, guild, given)
        score = [score_given(bot, guild, given, name) for name in ("score_a", "score_b")]
        slots = {
            slot: entrant_given(bot, guild, given, f"slot_{slot}", people)
            for slot in (A, B)
            if f"slot_{slot}" in given
        }
        stamp = now_stamp()
        moved = None
        outcome_keys: list[str] = [match.key]
        if slots:
            if match.state == COMPLETE:
                raise stop(bot, guild, "slot_played", "slot_played", 409, set=match.key)
            work = play.working(current)
            target = work.matches[match.key]
            for slot, entrant in slots.items():
                reseated(work, target, slot, entrant)
            if "score_a" in given or "score_b" in given:
                target.score_a, target.score_b = score
            moved = play.moved(work, current, stamp)
            await store_.save(bot.db, row["id"], moved.bracket, moved.changed, moved.removed)
            outcome_keys += [*moved.changed, *moved.removed]
        elif "score_a" in given or "score_b" in given:
            if match.state == COMPLETE and None not in score:
                side = match.side_of(match.winner) or A
                result = await overridden(
                    bot,
                    guild,
                    actor,
                    row,
                    current,
                    people,
                    match,
                    via,
                    score_a=score[0],
                    score_b=score[1],
                    winner=side,
                    free=True,
                )
                outcome_keys += list(result.changed)
            else:
                work = play.working(current)
                work.matches[match.key].score_a, work.matches[match.key].score_b = score
                await store_.save(bot.db, row["id"], work, [match.key], [])
        await store_.write_sports(bot.db, row["id"], match.key, sports)
        await note(
            bot,
            guild,
            "set_edited",
            actor,
            row["id"],
            via,
            set=match.key,
            changed=sorted(given),
            reason=reason or None,
        )
        outcome = done(bot, guild, "set_edited", row["id"], set=match.key)
        keys = tuple(dict.fromkeys(one for one in outcome_keys))
        return Outcome(True, outcome.message, value=row["id"], changed=keys)


@answered
async def release_hold(
    bot: Any, guild: Any, actor: Any, tournament_id: int, key: str, *, via: str = VIA_DISCORD
) -> Outcome:
    """A held set goes back under the feed; its result stands until the feed says otherwise."""
    require_on(bot, guild)
    async with lock_for(bot, tournament_id):
        row = await loaded(bot, guild, tournament_id)
        require_runner(bot, guild, actor)
        require_sports(bot, guild, row)
        current = await store_.bracket(bot.db, row)
        match = the_set(bot, guild, row, current, key)
        meta = (await store_.sports_rows(bot.db, row["id"])).get(match.key) or {}
        if not meta.get("held"):
            raise stop(bot, guild, "not_held", "not_held", 409, set=match.key)
        await store_.write_sports(bot.db, row["id"], match.key, {"held": 0})
        await note(bot, guild, "hold_released", actor, row["id"], via, set=match.key)
        return touched(
            done(bot, guild, "hold_released", row["id"], set=match.key),
            play.Moved(current, [match.key]),
        )


async def held_by_staff(bot: Any, row: Any, keys: Any) -> None:
    """A staff Decide or Reset on a sports set holds it against the feed."""
    if not store_.is_sports(row):
        return
    for key in keys:
        await store_.write_sports(bot.db, row["id"], key, {"decided_by": store_.STAFF, "held": 1})


__all__ = [
    "FEED_HOW",
    "applied",
    "build",
    "edit_set",
    "fetched_bracket",
    "held_by_staff",
    "import_bracket",
    "release_hold",
    "sync_now",
    "today_of",
    "wants_scores",
]
