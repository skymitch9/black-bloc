from __future__ import annotations

import asyncio
import logging
from datetime import UTC, date, datetime
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands, tasks

from ...actionlog import (
    LOGS_DEFAULT,
    LOGS_MAX,
    LOGS_MIN,
    log_action,
    send_logs,
)
from ...birthdays import (
    MONTH_NAMES,
    age,
    celebrates_today,
    clamp_month_day,
    date_problem,
    import_as_of_year,
    load_import_rows,
    local_today,
    member_zone_name,
    month_day_text,
    next_occurrence,
    parse_color,
    render_description,
    resolve,
    stamp,
    upcoming,
    year_from_age,
    year_problem,
)
from ...settings_store import (
    BIRTHDAY_MODES,
    DB_UNAVAILABLE,
    GUILD_ONLY,
    require_staff,
    staff_roles_sentence,
)

log = logging.getLogger(__name__)

LOOP_MINUTES = 5
IMPORT_HOURS = 24
NEXT_LIMIT = 5
MESSAGE_LIMIT = 1900
CANDIDATES_SHOWN = 3
ROLE_REASON = "Black Bloc birthday"

NOT_STORED = (
    "Black Bloc has no birthday for you, so there is nothing to change. Add one with "
    "`/birthday set` — the year is optional, and leaving it out keeps your age private."
)
NOT_STORED_FOR = (
    "Black Bloc has no birthday for {who}. They can add one with `/birthday set`, or staff can "
    "with `/birthday set-for`."
)
REMOVED = "Your birthday is forgotten. Nothing will be posted for you."
OPTED_OUT = (
    "You are opted out — your birthday is still stored, but nothing will be posted. "
    "`/birthday optin` turns it back on, and `/birthday remove` forgets it entirely."
)
OPTED_IN = "You are opted back in. Black Bloc will post on the day again."
ALREADY_OPTED = "You were already opted {state}, so nothing changed."
NOBODY_YET = (
    "Nobody has a birthday stored yet. People add their own with `/birthday set`, and the "
    "Birthday Bot list is brought over automatically once a day."
)
NONE_THIS_MONTH = "Nobody has a birthday stored in **{month}**."
NOTHING_UPCOMING = (
    "There are no birthdays to show — everyone stored is opted out, or nobody has set one yet."
)
ROLE_CLEARED = (
    "No birthday role will be given any more. A role somebody already has for today still "
    "comes off tomorrow. Set one again with `/settings set-role birthday_role_id`."
)
ROLE_NOT_SET = (
    "There was no birthday role set, so nothing changed. `/settings set-role birthday_role_id` "
    "is how one is chosen."
)

def _row_value(row: Any, key: str, fallback: Any = None) -> Any:
    if row is None:
        return fallback
    try:
        value = row[key]
    except (KeyError, IndexError, TypeError):
        return fallback
    return fallback if value is None else value


async def get_birthday(db: Any, user_id: int) -> Any:
    cur = await db.conn.execute("SELECT * FROM birthdays WHERE user_id = ?", (int(user_id),))
    return await cur.fetchone()


async def save_birthday(
    db: Any,
    guild_id: int,
    user_id: int,
    month: int,
    day: int,
    year: int | None,
    source: str,
) -> None:
    """Store one birthday; a change clears the announced-on stamp so today can still post."""
    await db.conn.execute(
        "INSERT INTO birthdays(user_id, guild_id, month, day, year, opted_in, source, set_at, "
        "last_announced_on) VALUES (?, ?, ?, ?, ?, 1, ?, ?, NULL) "
        "ON CONFLICT(user_id) DO UPDATE SET guild_id = excluded.guild_id, "
        "month = excluded.month, day = excluded.day, year = excluded.year, opted_in = 1, "
        "source = excluded.source, set_at = excluded.set_at, last_announced_on = NULL",
        (
            int(user_id),
            int(guild_id),
            int(month),
            int(day),
            int(year) if year else None,
            source,
            datetime.now(UTC).isoformat(),
        ),
    )
    await db.conn.commit()


async def delete_birthday(db: Any, user_id: int) -> bool:
    cur = await db.conn.execute("DELETE FROM birthdays WHERE user_id = ?", (int(user_id),))
    await db.conn.commit()
    return bool(cur.rowcount)


async def set_opted_in(db: Any, user_id: int, opted_in: bool) -> None:
    await db.conn.execute(
        "UPDATE birthdays SET opted_in = ? WHERE user_id = ?",
        (1 if opted_in else 0, int(user_id)),
    )
    await db.conn.commit()


async def mark_announced(db: Any, user_id: int, day_text: str) -> None:
    await db.conn.execute(
        "UPDATE birthdays SET last_announced_on = ? WHERE user_id = ?", (day_text, int(user_id))
    )
    await db.conn.commit()


async def set_role_added(
    db: Any, user_id: int, added: bool, role_id: int | None = None
) -> None:
    """Record that the role went on, and which role it was, so it can come off again."""
    await db.conn.execute(
        "UPDATE birthdays SET role_added = ?, role_added_id = ? WHERE user_id = ?",
        (1 if added else 0, int(role_id) if added and role_id else None, int(user_id)),
    )
    await db.conn.commit()


async def rows_for_guild(db: Any, guild_id: int) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT * FROM birthdays WHERE guild_id = ? ORDER BY month, day, user_id",
        (int(guild_id),),
    )
    return list(await cur.fetchall())


async def stored_counts(db: Any, guild_id: int) -> dict[str, int]:
    cur = await db.conn.execute(
        "SELECT opted_in, source, COUNT(*) AS n FROM birthdays WHERE guild_id = ? "
        "GROUP BY opted_in, source",
        (int(guild_id),),
    )
    totals = {"stored": 0, "opted_in": 0, "imported": 0, "self": 0}
    for row in await cur.fetchall():
        totals["stored"] += int(row["n"])
        if row["opted_in"]:
            totals["opted_in"] += int(row["n"])
        if row["source"] == "import":
            totals["imported"] += int(row["n"])
        if row["source"] == "self":
            totals["self"] += int(row["n"])
    return totals


def chunked(lines: list[str], limit: int = MESSAGE_LIMIT) -> list[str]:
    """The lines packed into as few messages as Discord's length cap allows."""
    pages: list[str] = []
    current = ""
    for line in lines:
        piece = line[:limit]
        if current and len(current) + len(piece) + 1 > limit:
            pages.append(current)
            current = piece
        else:
            current = f"{current}\n{piece}" if current else piece
    if current:
        pages.append(current)
    return pages


def candidate_text(match: Any) -> str:
    shown = ", ".join(
        f"{c.display_name} (<@{c.user_id}>)" for c in match.candidates[:CANDIDATES_SHOWN]
    )
    more = len(match.candidates) - CANDIDATES_SHOWN
    return shown + (f" and {more} more" if more > 0 else "")


async def members_of(guild: Any) -> list[Any]:
    """Every member Black Bloc can see, chunking first when the cache is short."""
    members = list(getattr(guild, "members", ()) or ())
    expected = int(getattr(guild, "member_count", 0) or 0)
    if expected and len(members) < expected:
        try:
            await guild.chunk()
        except Exception as exc:
            log.warning("birthdays: could not fill the member cache (%s)", exc)
        members = list(getattr(guild, "members", ()) or ())
    return members


async def import_rows(
    bot: Any, guild: Any, rows: list[Any], as_of: int, members: list[Any]
) -> dict[str, list[str]]:
    """The Birthday Bot seed, for slash and web alike: what was taken and what was not."""
    result: dict[str, list[str]] = {
        "imported": [],
        "already": [],
        "ambiguous": [],
        "not_found": [],
    }
    for row in rows:
        where = f"{row.display_name} — {month_day_text(row.month, row.day)}"
        match = resolve(row, members)
        if match.status == "not_found":
            result["not_found"].append(where)
            continue
        if match.status == "ambiguous":
            result["ambiguous"].append(f"{where} → {candidate_text(match)}")
            continue
        user_id = match.member_id
        existing = await get_birthday(bot.db, user_id)
        if existing is not None:
            result["already"].append(
                f"{where} → <@{user_id}> (kept the {existing['source']} entry)"
            )
            continue
        await save_birthday(
            bot.db,
            guild.id,
            user_id,
            row.month,
            row.day,
            year_from_age(row.age_shown, as_of),
            "import",
        )
        result["imported"].append(f"{where} → <@{user_id}>")
    return result


def report_lines(result: dict[str, list[str]], as_of_year: int, searched: int = 0) -> list[str]:
    lines = [
        f"**{len(result['imported'])} imported** · {len(result['already'])} already stored · "
        f"{len(result['ambiguous'])} ambiguous · {len(result['not_found'])} not found",
        f"Matched against the **{searched}** members Black Bloc can see in this server.",
    ]
    if result["imported"]:
        lines.append(
            f"Ages came from the {as_of_year} export, so a stored year can be a year out until "
            "the person corrects it with `/birthday set`."
        )
    for heading, key in (
        ("Imported", "imported"),
        ("Already stored, left alone", "already"),
        ("Ambiguous — set these by hand with `/birthday set-for`", "ambiguous"),
        ("Not found — nobody in the server matched", "not_found"),
    ):
        if not result[key]:
            continue
        lines.append(f"**{heading}**")
        lines += [f"· {entry}" for entry in result[key]]
    return lines


class Birthdays(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._locks: dict[int, asyncio.Lock] = {}
        self._said: dict[tuple[int, str], str] = {}
        self.last_run_at: str | None = None
        self.last_error: str | None = None
        self.last_import_at: str | None = None
        self.last_import_error: str | None = None

    def loop_health(self, name: str) -> tuple[str | None, str | None]:
        if name == "_sweep":
            return (self.last_run_at, self.last_error)
        if name == "_import_loop":
            return (self.last_import_at, self.last_import_error)
        return (None, None)

    birthday = app_commands.Group(name="birthday", description="Birthday wishes on the day")
    birthday_role = app_commands.Group(
        name="role", description="The role given for the day", parent=birthday
    )

    async def cog_load(self) -> None:
        if not self.bot.db.is_connected:
            return
        self._sweep.start()
        self._import_loop.start()

    async def cog_unload(self) -> None:
        self._sweep.cancel()
        self._import_loop.cancel()

    @tasks.loop(minutes=LOOP_MINUTES)
    async def _sweep(self) -> None:
        if not self.bot.db.is_connected:
            return
        try:
            await self.run_once()
        except Exception as exc:
            self.last_error = f"{type(exc).__name__}: {exc}"
            log.exception("birthdays: the five-minute sweep failed")
            return
        self.last_error = None
        self.last_run_at = datetime.now(UTC).isoformat()

    @_sweep.before_loop
    async def _before_sweep(self) -> None:
        await self.bot.wait_until_ready()

    @_sweep.error
    async def _sweep_stopped(self, exc: BaseException) -> None:
        """The loop stops for the life of the process unless it is started again."""
        self.last_error = f"{type(exc).__name__}: {exc}"
        log.error("birthdays: the sweep stopped; restarting it", exc_info=exc)
        self._sweep.restart()

    @tasks.loop(hours=IMPORT_HOURS)
    async def _import_loop(self) -> None:
        if not self.bot.db.is_connected:
            return
        try:
            await self.import_once()
        except Exception as exc:
            self.last_import_error = f"{type(exc).__name__}: {exc}"
            log.exception("birthdays: the daily import failed")
            return
        self.last_import_error = None
        self.last_import_at = datetime.now(UTC).isoformat()

    @_import_loop.before_loop
    async def _before_import(self) -> None:
        await self.bot.wait_until_ready()

    @_import_loop.error
    async def _import_stopped(self, exc: BaseException) -> None:
        """The loop stops for the life of the process unless it is started again."""
        self.last_import_error = f"{type(exc).__name__}: {exc}"
        log.error("birthdays: the daily import stopped; restarting it", exc_info=exc)
        self._import_loop.restart()

    async def import_once(self) -> None:
        """One pass of the Birthday Bot seed; the log channel only hears about new rows."""
        rows = load_import_rows()
        if not rows:
            log.warning("birthdays: the seed file has no rows, so there was nothing to import")
            return
        as_of = import_as_of_year()
        for guild in list(getattr(self.bot, "guilds", ())):
            if getattr(guild, "unavailable", False):
                log.info("birthdays: import skipped %s — the server is unavailable", guild.id)
                continue
            members = await self.members_of(guild)
            result = await self._import(guild, rows, as_of, members)
            counts = {key: len(value) for key, value in result.items()}
            if not result["imported"]:
                log.info("birthdays: the daily import took nothing new — %s", counts)
                continue
            await log_action(
                self.bot,
                guild,
                "birthday.import",
                actor=None,
                details=counts | {"searched": len(members), "trigger": "daily"},
            )

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        if not self.bot.db.is_connected:
            return
        if not self._sweep.is_running():
            self._sweep.start()
        if not self._import_loop.is_running():
            self._import_loop.start()

    async def run_once(self, now: datetime | None = None) -> None:
        """One pass: today's birthdays announced once, yesterday's role taken back."""
        moment = now or datetime.now(UTC)
        for guild in list(getattr(self.bot, "guilds", ())):
            if getattr(guild, "unavailable", False):
                log.info("birthdays: skipped %s — the server is unavailable", guild.id)
                continue
            mode = self.bot.store.get(guild.id, "birthday_mode")
            for row in await rows_for_guild(self.bot.db, guild.id):
                async with self._lock(row["user_id"]):
                    await self._sweep_row(guild, row, mode, moment)

    async def _sweep_row(self, guild: Any, row: Any, mode: str, moment: datetime) -> None:
        zone = await member_zone_name(self.bot.db, row["user_id"])
        today = local_today(zone, moment)
        today_text = today.isoformat()
        if _row_value(row, "role_added", 0) and row["last_announced_on"] != today_text:
            await self._take_role_back(guild, row, today)
        if not row["opted_in"] or mode == "off":
            return
        if not celebrates_today(row["month"], row["day"], today):
            return
        if row["last_announced_on"] == today_text:
            return
        await self._celebrate(guild, row, mode, today, today_text)

    async def _celebrate(
        self, guild: Any, row: Any, mode: str, today: date, today_text: str
    ) -> None:
        store = self.bot.store
        member = guild.get_member(row["user_id"])
        details: dict[str, Any] = {
            "mode": mode,
            "date": month_day_text(row["month"], row["day"]),
            "local_date": today_text,
        }
        if member is None:
            if self._say_once(row["user_id"], "member_missing", today_text):
                await log_action(
                    self.bot,
                    guild,
                    "birthday.member_missing",
                    target=row["user_id"],
                    details=details | {"reason": "not_in_the_member_cache"},
                )
            return
        years = age(row["year"], today) if store.get(guild.id, "birthday_show_age") else None
        text = render_description(
            store.get(guild.id, "birthday_template"), member.display_name, years
        )
        colour = discord.Colour(parse_color(store.get(guild.id, "birthday_color")))
        embed = discord.Embed(description=text, colour=colour)
        details = details | {"text": text}
        failure = await self._post(guild, embed) if mode == "on" else "shadow"
        if failure is not None and failure not in ("shadow", "test_mode"):
            if self._say_once(row["user_id"], "announce_failed", today_text):
                await log_action(
                    self.bot,
                    guild,
                    "birthday.announce_failed",
                    target=member,
                    details=details | {"reason": failure},
                )
            return
        await mark_announced(self.bot.db, row["user_id"], today_text)
        await log_action(
            self.bot,
            guild,
            "birthday.announce" if failure is None else "birthday.would_announce",
            target=member,
            details=details | ({"reason": failure} if failure else {}),
        )
        await self._give_role(guild, member, mode, today_text)

    async def _post(self, guild: Any, embed: discord.Embed) -> str | None:
        """None when the wish was posted; otherwise why it was not."""
        channel_id = self.bot.store.get(guild.id, "birthday_channel_id")
        if not channel_id:
            log.warning("birthdays: not posted — birthday_channel_id is not set")
            return "no_channel_configured"
        guard = getattr(self.bot, "guard", None)
        if guard is not None and not guard.allows_channel(channel_id):
            log.warning("birthdays: TEST MODE — refused to post to channel %s", channel_id)
            return "test_mode"
        channel = self.bot.get_channel(channel_id) or guild.get_channel(channel_id)
        if channel is None:
            log.warning("birthdays: not posted — channel %s is not visible", channel_id)
            return "channel_not_visible"
        try:
            await channel.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())
        except Exception as exc:
            log.warning("birthdays: not posted — %s: %s", type(exc).__name__, exc)
            return f"{type(exc).__name__}: {exc}"
        return None

    def _role(self, guild: Any) -> Any:
        role_id = self.bot.store.get(guild.id, "birthday_role_id")
        if not role_id:
            return None
        role = guild.get_role(role_id)
        if role is None:
            log.warning("birthdays: role %s is not in this server", role_id)
        return role

    async def _give_role(self, guild: Any, member: Any, mode: str, today_text: str) -> None:
        role = self._role(guild)
        if role is None:
            return
        if mode != "on" or getattr(self.bot, "guard", None) is not None:
            log.info("birthdays: would give %s the birthday role (mode %s)", member.id, mode)
            await log_action(
                self.bot,
                guild,
                "birthday.would_add_role",
                target=member,
                details={"role_id": role.id, "mode": mode, "local_date": today_text},
            )
            return
        try:
            await member.add_roles(role, reason=ROLE_REASON)
        except discord.HTTPException as exc:
            log.warning("birthdays: could not give %s the birthday role: %s", member.id, exc)
            await log_action(
                self.bot,
                guild,
                "birthday.add_role_failed",
                target=member,
                details={"role_id": role.id, "reason": f"{type(exc).__name__}: {exc}"},
            )
            return
        await set_role_added(self.bot.db, member.id, True, role.id)
        await log_action(
            self.bot, guild, "birthday.add_role", target=member, details={"role_id": role.id}
        )

    async def _take_role_back(self, guild: Any, row: Any, today: date) -> None:
        """The day is over, so the role that went on comes off — whatever the mode says now."""
        role_id = _row_value(row, "role_added_id") or self.bot.store.get(
            guild.id, "birthday_role_id"
        )
        member = guild.get_member(row["user_id"])
        if member is None or not role_id:
            await set_role_added(self.bot.db, row["user_id"], False)
            return
        if getattr(self.bot, "guard", None) is not None:
            await set_role_added(self.bot.db, row["user_id"], False)
            await log_action(
                self.bot,
                guild,
                "birthday.would_remove_role",
                target=member,
                details={"role_id": role_id},
            )
            return
        try:
            await member.remove_roles(discord.Object(id=int(role_id)), reason=ROLE_REASON)
        except discord.HTTPException as exc:
            log.warning("birthdays: could not take the birthday role off %s: %s", member.id, exc)
            if self._say_once(row["user_id"], "remove_role_failed", today.isoformat()):
                await log_action(
                    self.bot,
                    guild,
                    "birthday.remove_role_failed",
                    target=member,
                    details={"role_id": role_id, "reason": f"{type(exc).__name__}: {exc}"},
                )
            return
        await set_role_added(self.bot.db, row["user_id"], False)
        await log_action(
            self.bot, guild, "birthday.remove_role", target=member, details={"role_id": role_id}
        )

    async def _return_role(self, guild: Any, row: Any) -> None:
        if not _row_value(row, "role_added", 0):
            return
        await self._take_role_back(guild, row, local_today(await self._zone_of(row["user_id"])))

    def _say_once(self, user_id: int, kind: str, day_text: str) -> bool:
        key = (int(user_id), kind)
        if self._said.get(key) == day_text:
            return False
        self._said[key] = day_text
        return True

    def _lock(self, user_id: int) -> asyncio.Lock:
        lock = self._locks.get(user_id)
        if lock is None:
            lock = self._locks[user_id] = asyncio.Lock()
        return lock

    async def _ready(self, interaction: discord.Interaction) -> bool:
        if interaction.guild is None:
            await interaction.response.send_message(GUILD_ONLY, ephemeral=True)
            return False
        if not self.bot.db.is_connected:
            log.warning("birthdays: refused a command — the database is not connected")
            await interaction.response.send_message(DB_UNAVAILABLE, ephemeral=True)
            return False
        return True

    async def _zone_of(self, user_id: int) -> str:
        return await member_zone_name(self.bot.db, user_id)

    @birthday.command(name="logs", description="The last few birthday log lines")
    @app_commands.describe(
        count="How many lines, 1 to 50 (10 by default)",
        important_only="True to leave out the dry runs and the housekeeping",
    )
    async def birthday_logs(
        self,
        interaction: discord.Interaction,
        count: app_commands.Range[int, LOGS_MIN, LOGS_MAX] = LOGS_DEFAULT,
        important_only: bool = False,
    ) -> None:
        await send_logs(interaction, "birthday", count=count, important_only=important_only)

    @birthday.command(name="set", description="Tell Black Bloc when your birthday is")
    @app_commands.describe(
        month="1 for January through 12 for December",
        day="The day of that month",
        year="Optional — only stored so an age can be shown",
    )
    async def set_mine(
        self,
        interaction: discord.Interaction,
        month: app_commands.Range[int, 1, 12],
        day: app_commands.Range[int, 1, 31],
        year: app_commands.Range[int, 1900, 2200] | None = None,
    ) -> None:
        if not await self._ready(interaction):
            return
        await self._store_for(interaction, interaction.user, month, day, year, "self")

    @birthday.command(name="set-for", description="Store someone else's birthday (staff)")
    @app_commands.describe(
        user="Whose birthday it is",
        month="1 for January through 12 for December",
        day="The day of that month",
        year="Optional — only stored so an age can be shown",
    )
    async def set_for(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        month: app_commands.Range[int, 1, 12],
        day: app_commands.Range[int, 1, 31],
        year: app_commands.Range[int, 1900, 2200] | None = None,
    ) -> None:
        if not await require_staff(interaction):
            return
        if not await self._ready(interaction):
            return
        await self._store_for(interaction, user, month, day, year, "staff")

    async def _store_for(
        self,
        interaction: discord.Interaction,
        member: Any,
        month: int,
        day: int,
        year: int | None,
        source: str,
    ) -> None:
        today = local_today(await self._zone_of(member.id))
        problem = date_problem(month, day) or year_problem(year, today)
        if problem is not None:
            await interaction.response.send_message(problem, ephemeral=True)
            return
        m, d = clamp_month_day(month, day)
        async with self._lock(member.id):
            await save_birthday(
                self.bot.db, interaction.guild.id, member.id, m, d, year, source
            )
        zone = await self._zone_of(member.id)
        whose = "Your" if member.id == interaction.user.id else f"**{member.display_name}**'s"
        await interaction.response.send_message(
            f"{whose} birthday is **{month_day_text(m, d)}**"
            + (f" ({year})" if year else "")
            + f". Black Bloc posts it at midnight in **{zone}**, and the next one is "
            + stamp(next_occurrence(m, d, zone), "D")
            + ".",
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        await log_action(
            self.bot,
            interaction.guild,
            "birthday.set",
            actor=interaction.user,
            target=member,
            details={"date": month_day_text(m, d), "year": year, "source": source},
        )

    @birthday.command(name="remove", description="Forget your birthday")
    async def remove(self, interaction: discord.Interaction) -> None:
        if not await self._ready(interaction):
            return
        async with self._lock(interaction.user.id):
            row = await get_birthday(self.bot.db, interaction.user.id)
            if row is None:
                await interaction.response.send_message(NOT_STORED, ephemeral=True)
                return
            await self._return_role(interaction.guild, row)
            await delete_birthday(self.bot.db, interaction.user.id)
        await interaction.response.send_message(REMOVED, ephemeral=True)
        await log_action(
            self.bot, interaction.guild, "birthday.remove", actor=interaction.user
        )

    @birthday.command(name="optout", description="Keep your birthday stored but post nothing")
    async def optout(self, interaction: discord.Interaction) -> None:
        await self._change_opt(interaction, opted_in=False)

    @birthday.command(name="optin", description="Let Black Bloc post on your birthday again")
    async def optin(self, interaction: discord.Interaction) -> None:
        await self._change_opt(interaction, opted_in=True)

    async def _change_opt(self, interaction: discord.Interaction, *, opted_in: bool) -> None:
        if not await self._ready(interaction):
            return
        row = await get_birthday(self.bot.db, interaction.user.id)
        if row is None:
            await interaction.response.send_message(NOT_STORED, ephemeral=True)
            return
        if bool(row["opted_in"]) == opted_in:
            await interaction.response.send_message(
                ALREADY_OPTED.format(state="in" if opted_in else "out"), ephemeral=True
            )
            return
        async with self._lock(interaction.user.id):
            await set_opted_in(self.bot.db, interaction.user.id, opted_in)
            if not opted_in:
                await self._return_role(interaction.guild, row)
        await interaction.response.send_message(
            OPTED_IN if opted_in else OPTED_OUT, ephemeral=True
        )
        await log_action(
            self.bot,
            interaction.guild,
            "birthday.optin" if opted_in else "birthday.optout",
            actor=interaction.user,
        )

    @birthday.command(name="show", description="Show a stored birthday")
    @app_commands.describe(user="Whose birthday to show — yours if you leave this out")
    async def show(
        self, interaction: discord.Interaction, user: discord.Member | None = None
    ) -> None:
        if not await self._ready(interaction):
            return
        member = user or interaction.user
        row = await get_birthday(self.bot.db, member.id)
        if row is None:
            await interaction.response.send_message(
                NOT_STORED
                if member.id == interaction.user.id
                else NOT_STORED_FOR.format(who=f"**{member.display_name}**"),
                ephemeral=True,
                allowed_mentions=discord.AllowedMentions.none(),
            )
            return
        zone = await self._zone_of(member.id)
        when = next_occurrence(row["month"], row["day"], zone)
        years = (
            age(row["year"], when.date())
            if row["year"] and self.bot.store.get(interaction.guild.id, "birthday_show_age")
            else None
        )
        lines = [
            f"**{member.display_name}** — {month_day_text(row['month'], row['day'])}"
            + (f", turning {years}" if years is not None else ""),
            f"Next: {stamp(when, 'D')} ({stamp(when, 'R')}), midnight in **{zone}**",
        ]
        if not row["opted_in"]:
            lines.append("They are **opted out**, so nothing will be posted.")
        await interaction.response.send_message(
            "\n".join(lines), ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
        )

    @birthday.command(name="next", description="The birthdays coming up soonest")
    async def next_up(self, interaction: discord.Interaction) -> None:
        if not await self._ready(interaction):
            return
        rows = [r for r in await rows_for_guild(self.bot.db, interaction.guild.id) if r["opted_in"]]
        if not rows:
            await interaction.response.send_message(NOTHING_UPCOMING, ephemeral=True)
            return
        entries = [
            {
                "user_id": row["user_id"],
                "month": row["month"],
                "day": row["day"],
                "year": row["year"],
                "tz": await self._zone_of(row["user_id"]),
            }
            for row in rows
        ]
        by_id = {entry["user_id"]: entry for entry in entries}
        lines = [
            f"· <@{item.user_id}> — "
            f"{month_day_text(by_id[item.user_id]['month'], by_id[item.user_id]['day'])} "
            f"({stamp(item.when, 'D')}, {stamp(item.when, 'R')})"
            for item in upcoming(entries, limit=NEXT_LIMIT)
        ]
        await interaction.response.send_message(
            "**Next birthdays**\n" + "\n".join(lines),
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @birthday.command(name="list", description="Every stored birthday, by month (staff)")
    @app_commands.describe(month="Show one month only")
    @app_commands.choices(
        month=[
            app_commands.Choice(name=name, value=number)
            for number, name in enumerate(MONTH_NAMES, start=1)
        ]
    )
    async def list_all(
        self, interaction: discord.Interaction, month: app_commands.Choice[int] | None = None
    ) -> None:
        if not await require_staff(interaction):
            return
        if not await self._ready(interaction):
            return
        rows = await rows_for_guild(self.bot.db, interaction.guild.id)
        if month is not None:
            rows = [r for r in rows if r["month"] == month.value]
        if not rows:
            await interaction.response.send_message(
                NONE_THIS_MONTH.format(month=month.name) if month is not None else NOBODY_YET,
                ephemeral=True,
            )
            return
        lines: list[str] = []
        seen: int | None = None
        for row in rows:
            if row["month"] != seen:
                seen = row["month"]
                lines.append(f"**{MONTH_NAMES[seen - 1]}**")
            marks = "" if row["opted_in"] else " · opted out"
            lines.append(
                f"· {row['day']} — <@{row['user_id']}> ({row['source']}{marks})"
            )
        pages = chunked(lines)
        await interaction.response.send_message(
            pages[0], ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
        )
        for page in pages[1:]:
            await interaction.followup.send(
                page, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
            )

    @birthday.command(name="mode", description="Turn birthday wishes off, to shadow, or on")
    @app_commands.describe(mode="off, shadow (log only) or on (post the wish)")
    @app_commands.choices(
        mode=[app_commands.Choice(name=name, value=name) for name in BIRTHDAY_MODES]
    )
    async def mode(
        self, interaction: discord.Interaction, mode: app_commands.Choice[str]
    ) -> None:
        if not await require_staff(interaction):
            return
        if not await self._ready(interaction):
            return
        await self.bot.store.set(
            interaction.guild.id, "birthday_mode", mode.value, by=interaction.user.id
        )
        await interaction.response.send_message(
            f"Birthday wishes are now **{mode.value}**.", ephemeral=True
        )
        await log_action(
            self.bot,
            interaction.guild,
            "birthday.mode",
            actor=interaction.user,
            details={"mode": mode.value},
        )

    @birthday_role.command(name="clear", description="Stop giving a birthday role at all (staff)")
    async def role_clear(self, interaction: discord.Interaction) -> None:
        if not await require_staff(interaction):
            return
        if not await self._ready(interaction):
            return
        cleared = await self.bot.store.clear(
            interaction.guild.id, "birthday_role_id", by=interaction.user.id
        )
        await interaction.response.send_message(
            ROLE_CLEARED if cleared else ROLE_NOT_SET, ephemeral=True
        )
        if not cleared:
            return
        await log_action(
            self.bot,
            interaction.guild,
            "settings.clear",
            actor=interaction.user,
            details={"key": "birthday_role_id"},
        )

    @birthday.command(name="status", description="What birthdays are set to, and how they run")
    async def status(self, interaction: discord.Interaction) -> None:
        if not await require_staff(interaction):
            return
        if not await self._ready(interaction):
            return
        store = self.bot.store
        guild = interaction.guild
        totals = await stored_counts(self.bot.db, guild.id)
        channel_id = store.get(guild.id, "birthday_channel_id")
        role_id = store.get(guild.id, "birthday_role_id")
        ran = self.last_run_at or "not yet"
        lines = [
            f"**mode** — {store.get(guild.id, 'birthday_mode')}",
            f"**channel** — {f'<#{channel_id}>' if channel_id else 'not set'}",
            f"**template** — `{store.get(guild.id, 'birthday_template')}`",
            f"**colour** — {store.get(guild.id, 'birthday_color')}",
            f"**role** — {f'<@&{role_id}>' if role_id else 'none'}"
            + (" (test mode gives no roles)" if getattr(self.bot, "guard", None) else ""),
            f"**ages shown** — {store.get(guild.id, 'birthday_show_age')}",
            f"**stored** — {totals['stored']} ({totals['opted_in']} opted in · "
            f"{totals['imported']} imported · {totals['self']} set by the person)",
            f"**staff** — {staff_roles_sentence(store.staff_roles(guild))}",
            f"**last sweep** — {ran} (every {LOOP_MINUTES} minutes)",
            f"**last error** — {self.last_error or 'none'}",
            f"**last import** — {self.last_import_at or 'not yet'} (every {IMPORT_HOURS} hours)",
            f"**last import error** — {self.last_import_error or 'none'}",
        ]
        await interaction.response.send_message(
            "\n".join(lines), ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
        )

    async def members_of(self, guild: Any) -> list[Any]:
        return await members_of(guild)

    async def _import(
        self, guild: Any, rows: list[Any], as_of: int, members: list[Any]
    ) -> dict[str, list[str]]:
        return await import_rows(self.bot, guild, rows, as_of, members)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Birthdays(bot))
