from __future__ import annotations

import logging
from typing import Any

import discord

from ... import marathon as mt
from ... import marathon_archive as ma
from ... import marathon_inbox as mi
from ... import marathon_spotlight as ms
from ...actionlog import log_action
from ...golive import parse_ts
from ...logkinds import VIA_DISCORD, kind_via
from ...marathon_sources import SOURCE_WORDS
from ...panels import (
    KEEP_IT,
    Outcome,
    answer,
    clamped,
    confirm,
    confirm_items,
    opened,
    refusal,
)
from ...settings_store import (
    MARATHON_ARCHIVE_AFTER_DAYS_KEY,
    MARATHON_ARCHIVE_QUESTION_KEY,
    MARATHON_ARCHIVED_SAID_KEY,
    MARATHON_ARCHIVED_WORD_KEY,
    MARATHON_NOT_ARCHIVED_KEY,
    MARATHON_RESTORE_QUESTION_KEY,
    MARATHON_RESTORE_TAKEN_KEY,
    MARATHON_RESTORED_SAID_KEY,
)
from ...storage.db import ARCHIVED_TABLES
from ...timezones import unix
from . import marathon_late_track as late_track
from .marathon import (
    ARCHIVE_VIEW,
    NO_SUCH,
    MarathonPanel,
    _cell,
    actor_id,
    cancel_linked_event,
    cog_of,
    counts_of,
    get_marathon,
    marathon_by_url,
    minutes_for,
    open_card,
    open_root,
    render,
    said_default,
)

log = logging.getLogger(__name__)

MARATHONS = "marathons"
RUNS = "marathon_runs"
PEOPLE = "marathon_people"
NO_SUCH_ARCHIVED = "not_archived"
RESTORE_TAKEN = "restore_taken"


def words(bot: Any, guild_id: int, key: str, **fields: Any) -> str:
    return mt.render(bot.store.get(guild_id, key), said_default(key), **fields).text


# --- the tables -------------------------------------------------------------------------------


async def columns_of(db: Any, table: str) -> list[str]:
    cur = await db.conn.execute(f"PRAGMA table_info({table})")
    return [str(row["name"]) for row in await cur.fetchall()]


async def copy_rows(
    db: Any, source: str, target: str, where: str, params: tuple, extra: dict | None = None
) -> int:
    """Spelled-out columns both tables share, never SELECT * (checklist 6)."""
    wanted = set(await columns_of(db, target))
    shared = [name for name in await columns_of(db, source) if name in wanted]
    names = ", ".join(shared)
    extra = extra or {}
    added = "".join(f", {name}" for name in extra)
    marks = "".join(", ?" for _ in extra)
    cur = await db.conn.execute(
        f"INSERT INTO {target}({names}{added}) SELECT {names}{marks} FROM {source} WHERE {where}",
        (*extra.values(), *params),
    )
    return cur.rowcount


async def archive_rows(db: Any, marathon_id: int, *, why: str, by: int | None, at: str) -> bool:
    """One transaction: the row, its runs and its people copied, then the live rows deleted."""
    wanted = (int(marathon_id),)
    try:
        moved = await copy_rows(
            db,
            MARATHONS,
            ARCHIVED_TABLES[MARATHONS],
            "id = ?",
            wanted,
            {"archived_at": at, "archived_by": by, "archived_why": why},
        )
        if not moved:
            await db.conn.rollback()
            return False
        await copy_rows(db, RUNS, ARCHIVED_TABLES[RUNS], "marathon_id = ?", wanted)
        await copy_rows(db, PEOPLE, ARCHIVED_TABLES[PEOPLE], "marathon_id = ?", wanted)
        for sql in (
            "DELETE FROM marathon_runs WHERE marathon_id = ?",
            "DELETE FROM marathon_people WHERE marathon_id = ?",
            "DELETE FROM marathon_spotlights WHERE marathon_id = ?",
            "DELETE FROM spotlight_ping_windows WHERE source = 'marathon' AND source_id = ?",
            "DELETE FROM marathons WHERE id = ?",
        ):
            await db.conn.execute(sql, wanted)
        await db.conn.commit()
    except Exception:
        await db.conn.rollback()
        raise
    return True


async def restore_rows(db: Any, marathon_id: int) -> bool:
    """The reverse move; a restored marathon comes back paused."""
    wanted = (int(marathon_id),)
    try:
        moved = await copy_rows(db, ARCHIVED_TABLES[MARATHONS], MARATHONS, "id = ?", wanted)
        if not moved:
            await db.conn.rollback()
            return False
        await copy_rows(db, ARCHIVED_TABLES[RUNS], RUNS, "marathon_id = ?", wanted)
        await copy_rows(db, ARCHIVED_TABLES[PEOPLE], PEOPLE, "marathon_id = ?", wanted)
        await db.conn.execute(
            "UPDATE marathons SET active = 0, board_pinned = 0 WHERE id = ?", wanted
        )
        await db.conn.execute(
            "UPDATE marathon_runs SET post_pinned = 0 WHERE marathon_id = ?", wanted
        )
        for table in ARCHIVED_TABLES.values():
            key = "id" if table == ARCHIVED_TABLES[MARATHONS] else "marathon_id"
            await db.conn.execute(f"DELETE FROM {table} WHERE {key} = ?", wanted)
        await db.conn.commit()
    except Exception:
        await db.conn.rollback()
        raise
    return True


async def archived_marathon(db: Any, guild_id: int, marathon_id: Any) -> Any:
    try:
        wanted = int(marathon_id)
    except (TypeError, ValueError):
        return None
    cur = await db.conn.execute(
        "SELECT * FROM marathons_archive WHERE id = ? AND guild_id = ?", (wanted, int(guild_id))
    )
    return await cur.fetchone()


async def list_archived(db: Any, guild_id: int, limit: int = 50, offset: int = 0) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT * FROM marathons_archive WHERE guild_id = ? "
        "ORDER BY archived_at DESC, id DESC LIMIT ? OFFSET ?",
        (int(guild_id), int(limit), int(offset)),
    )
    return list(await cur.fetchall())


async def count_archived(db: Any, guild_id: int) -> int:
    cur = await db.conn.execute(
        "SELECT COUNT(*) FROM marathons_archive WHERE guild_id = ?", (int(guild_id),)
    )
    return int((await cur.fetchone())[0])


async def archived_runs(db: Any, marathon_id: int) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT * FROM marathon_runs_archive WHERE marathon_id = ? "
        "ORDER BY COALESCE(scheduled_at, '9999'), order_no, id",
        (int(marathon_id),),
    )
    return list(await cur.fetchall())


async def archived_pairings(db: Any, marathon_id: int) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT * FROM marathon_people_archive WHERE marathon_id = ? ORDER BY runner_name, id",
        (int(marathon_id),),
    )
    return list(await cur.fetchall())


async def marathon_by_id_any(db: Any, guild_id: int, marathon_id: Any) -> Any:
    """Live first, then the archive: an event's marathon line survives the move."""
    found = await get_marathon(db, guild_id, marathon_id)
    return found if found is not None else await archived_marathon(db, guild_id, marathon_id)


async def archived_people_state(bot: Any, guild: Any, marathon: Any) -> dict[str, Any]:
    """The People card of an archived marathon: its own pairings and the everywhere ones."""
    from ... import marathon_people as mp
    from .marathon import links_of

    runs = await archived_runs(bot.db, marathon["id"])
    entries = mp.group_people(runs)
    cur = await bot.db.conn.execute(
        "SELECT * FROM marathon_people WHERE guild_id = ? AND marathon_id IS NULL",
        (int(guild.id),),
    )
    pairings = [*await archived_pairings(bot.db, marathon["id"]), *await cur.fetchall()]
    links = await links_of(bot.db)
    for entry in entries:
        how, pairing_id = mp.matched_by(entry, pairings, links, marathon_id=marathon["id"])
        entry.update(matched_by=how, pairing_id=pairing_id, looks_like=None)
    baf, others = mp.split_people(entries)
    return {"runs": runs, "entries": entries, "baf": baf, "others": others, "pairings": pairings}


# --- the moves --------------------------------------------------------------------------------


def details_of(marathon: Any, runs: list[Any], why: str, via: str) -> dict[str, Any]:
    total, ours = counts_of(runs)
    return {
        "marathon_id": marathon["id"],
        "name": marathon["name"],
        "source": marathon["source"],
        "ref": marathon["source_ref"],
        "runs": total,
        "baf": ours,
        "archived_why": why,
        "via": via,
    }


async def _lift_held(bot: Any, guild: Any, marathon: Any) -> None:
    from .marathon_spotlight import lift
    from .spotlight import channel_by_id

    spotlight_id = _cell(marathon, "spotlight_id")
    if not spotlight_id:
        return
    row = await channel_by_id(bot.db, int(spotlight_id))
    if row is not None and ms.held_by(row) == int(marathon["id"]):
        await lift(bot, guild, row, marathon["id"], ma.BECAUSE_ARCHIVED)


async def archive_held(
    bot: Any, guild: Any, actor: Any, marathon: Any, why: str, *, via: str = VIA_DISCORD
) -> bool:
    """Called with the marathon's lock held. The row moves first; the knock-ons follow it."""
    from .marathon import runs_of
    from .marathon_events import cancel_every_run_event
    from .marathon_inbox import archived_inbox
    from .marathon_thread_controls import archived_controls

    cog = cog_of(bot)
    runs = await runs_of(bot.db, marathon["id"])
    if why != ma.ENDED:
        await cancel_linked_event(bot, guild, actor, marathon, via=via)
        await cancel_every_run_event(bot, guild, marathon, actor=actor)
    await cog.drop_windows(guild, marathon)
    await _lift_held(bot, guild, marathon)
    at = cog.clock().isoformat()
    moved = await archive_rows(bot.db, marathon["id"], why=why, by=actor_id(actor), at=at)
    if not moved:
        return False
    cog.forget(marathon["id"])
    await log_action(
        bot,
        guild,
        kind_via("marathon.removed" if why == ma.REMOVED else "marathon.archived", via),
        actor=actor,
        details=details_of(marathon, runs, why, via),
    )
    await cog.unpin_board(guild, marathon, because=ma.UNPIN_BECAUSE, runs=runs)
    await archived_controls(bot, guild, marathon)
    await archived_inbox(bot, guild, marathon, at)
    return True


async def archive_marathon(
    bot: Any, guild: Any, actor: Any, marathon: Any, *, why: str = ma.STAFF, via: str = VIA_DISCORD
) -> Outcome:
    why = ma.clean_why(why)
    async with cog_of(bot).lock(marathon["id"]):
        fresh = await get_marathon(bot.db, guild.id, marathon["id"])
        if fresh is None:
            return refusal(mt.NO_SUCH_MARATHON.format(given=marathon["id"]), NO_SUCH, 404)
        await archive_held(bot, guild, actor, fresh, why, via=via)
    return Outcome(True, words(bot, guild.id, MARATHON_ARCHIVED_SAID_KEY, name=fresh["name"]))


async def restore_marathon(
    bot: Any, guild: Any, actor: Any, marathon_id: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    """Staff final say: one move puts an archived marathon back on the list, paused."""
    from .marathon_inbox import sync_inbox

    row = await archived_marathon(bot.db, guild.id, marathon_id)
    if row is None:
        return refusal(
            words(bot, guild.id, MARATHON_NOT_ARCHIVED_KEY, given=str(marathon_id)[:40]),
            NO_SUCH_ARCHIVED,
            404,
        )
    async with cog_of(bot).lock(row["id"]):
        row = await archived_marathon(bot.db, guild.id, row["id"])
        if row is None:
            return refusal(
                words(bot, guild.id, MARATHON_NOT_ARCHIVED_KEY, given=str(marathon_id)[:40]),
                NO_SUCH_ARCHIVED,
                404,
            )
        taken = await marathon_by_url(bot.db, guild.id, row["schedule_url"])
        if taken is not None:
            return refusal(
                words(
                    bot, guild.id, MARATHON_RESTORE_TAKEN_KEY, name=row["name"], other=taken["name"]
                ),
                RESTORE_TAKEN,
                409,
            )
        runs = await archived_runs(bot.db, row["id"])
        await restore_rows(bot.db, row["id"])
        if mi.is_tracked(row):
            await late_track.arm(bot.db, row["id"])
    await log_action(
        bot,
        guild,
        kind_via("marathon.restored", via),
        actor=actor,
        details=details_of(row, runs, str(row["archived_why"]), via)
        | {"archived_at": row["archived_at"]},
    )
    async with cog_of(bot).lock(row["id"]):
        fresh = await get_marathon(bot.db, guild.id, row["id"])
        await sync_inbox(bot, guild, fresh, force=True)
    return Outcome(
        True, words(bot, guild.id, MARATHON_RESTORED_SAID_KEY, name=row["name"]), value=fresh
    )


async def archive_one(cog: Any, guild: Any, rows: list[Any]) -> bool:
    """The tick's one move per pass, under the marathon's own lock (checklist 37)."""
    bot = cog.bot
    after = int(bot.store.get(guild.id, MARATHON_ARCHIVE_AFTER_DAYS_KEY))
    found = ma.first_ended(rows, cog.clock(), after)
    if found is None:
        return False
    async with cog.lock(found["id"]):
        fresh = await get_marathon(bot.db, guild.id, found["id"])
        if fresh is None or not ma.is_ended(fresh, cog.clock(), after):
            return False
        return await archive_held(bot, guild, None, fresh, ma.ENDED)


def archived_word(bot: Any, guild_id: int, row: Any) -> str:
    at = parse_ts(_cell(row, "archived_at"))
    when = at.strftime("%d %b %Y") if at is not None else ""
    return words(bot, guild_id, MARATHON_ARCHIVED_WORD_KEY, when=when)


# --- the Discord panel ------------------------------------------------------------------------


def archive_line(row: Any, runs: list[Any]) -> str:
    total, ours = counts_of(runs)
    starts = parse_ts(row["starts_at"])
    ends = parse_ts(row["ends_at"])
    dates = f"<t:{unix(starts)}:d> – <t:{unix(ends or starts)}:d>" if starts else mt.NO_DATES
    at = parse_ts(row["archived_at"])
    return ma.ARCHIVE_LINE.format(
        name=row["name"],
        source=SOURCE_WORDS.get(row["source"], row["source"]),
        dates=dates,
        runs=total,
        ours=ours,
        why=ma.WHY_WORDS.get(row["archived_why"], row["archived_why"]),
        when=f"<t:{unix(at)}:R>" if at is not None else "",
    )


async def build_archive(bot: Any, guild: Any) -> tuple[discord.Embed, MarathonPanel]:
    rows = await list_archived(bot.db, guild.id, limit=25)
    total = await count_archived(bot.db, guild.id)
    lines = [archive_line(row, await archived_runs(bot.db, row["id"])) for row in rows]
    if not rows:
        days = int(bot.store.get(guild.id, MARATHON_ARCHIVE_AFTER_DAYS_KEY))
        lines = [ma.ARCHIVE_EMPTY.format(days=days)]
    embed = discord.Embed(title=ma.ARCHIVE_TITLE.format(count=total), description=clamped(lines))
    view = MarathonPanel(minutes_for(bot, guild.id), ARCHIVE_VIEW)
    if rows:
        view.add_item(ArchivedPick(rows))
    from .marathon import add_moves

    add_moves(view, (mt.BACK_MOVE,))
    return (embed, view)


async def open_archive(interaction: discord.Interaction, previous: Any = None) -> None:
    if not await opened(interaction):
        return
    embed, view = await build_archive(interaction.client, interaction.guild)
    await render(interaction, embed, view, previous)


async def ask_archive(interaction: discord.Interaction, view: Any) -> None:
    from .marathon import build_card, run_move

    if not await opened(interaction):
        return
    bot, guild = interaction.client, interaction.guild
    row = await get_marathon(bot.db, guild.id, view.marathon_id)
    if row is None:
        await open_root(interaction, view)
        return
    embed, fresh = await build_card(bot, guild, row["id"])
    fresh.clear_items()

    async def yes(one: discord.Interaction, card: Any) -> None:
        await run_move(
            one,
            card,
            lambda bot, guild, actor, marathon: archive_marathon(bot, guild, actor, marathon),
        )

    async def no(one: discord.Interaction, card: Any) -> None:
        await open_card(one, row["id"], card)

    await confirm(
        interaction,
        fresh,
        embed,
        confirm_items(yes=ma.ARCHIVE_MOVE.label, no=KEEP_IT, on_yes=yes, on_no=no),
        view,
        question=words(bot, guild.id, MARATHON_ARCHIVE_QUESTION_KEY, name=row["name"]),
    )


async def ask_restore(interaction: discord.Interaction, view: Any, marathon_id: Any) -> None:
    if not await opened(interaction):
        return
    bot, guild = interaction.client, interaction.guild
    row = await archived_marathon(bot.db, guild.id, marathon_id)
    if row is None:
        await open_archive(interaction, view)
        await answer(
            interaction, words(bot, guild.id, MARATHON_NOT_ARCHIVED_KEY, given=str(marathon_id))
        )
        return
    embed, fresh = await build_archive(bot, guild)
    fresh.clear_items()

    async def yes(one: discord.Interaction, card: Any) -> None:
        if not await opened(one):
            return
        done = await restore_marathon(bot, guild, one.user, row["id"])
        if done.ok:
            await open_card(one, row["id"], card)
        else:
            await open_archive(one, card)
        await answer(one, done.message)

    async def no(one: discord.Interaction, card: Any) -> None:
        await open_archive(one, card)

    await confirm(
        interaction,
        fresh,
        embed,
        confirm_items(
            yes=ma.RESTORE_LABEL,
            no=KEEP_IT,
            on_yes=yes,
            on_no=no,
            yes_style=discord.ButtonStyle.primary,
        ),
        view,
        question=words(bot, guild.id, MARATHON_RESTORE_QUESTION_KEY, name=row["name"]),
    )


class ArchivedPick(discord.ui.Select):
    def __init__(self, rows: list[Any]) -> None:
        super().__init__(
            placeholder=ma.PICK_ARCHIVED,
            options=[
                discord.SelectOption(
                    label=str(row["name"])[:100],
                    value=str(row["id"]),
                    description=ma.WHY_WORDS.get(row["archived_why"], "")[:100] or None,
                )
                for row in rows[:25]
            ],
            row=0,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await ask_restore(interaction, self.view, self.values[0])


__all__ = [
    "archive_held",
    "archive_marathon",
    "archive_one",
    "archive_rows",
    "archived_marathon",
    "archived_pairings",
    "archived_people_state",
    "archived_runs",
    "archived_word",
    "ask_archive",
    "count_archived",
    "list_archived",
    "marathon_by_id_any",
    "open_archive",
    "restore_marathon",
    "restore_rows",
]
