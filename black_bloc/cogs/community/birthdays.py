from __future__ import annotations

import asyncio
import logging
from datetime import UTC, date, datetime
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands, tasks

from ...actionlog import log_action, send_logs
from ...birthdays import (
    DATE_INPUT_LIMIT,
    DATE_LABEL,
    DATE_PLACEHOLDER,
    DATE_UNREADABLE,
    EVERY_MONTH,
    LOOKUP_PLACEHOLDER,
    MODE_PLACEHOLDER,
    MODE_WARNINGS,
    MONTH_NAMES,
    MONTH_PLACEHOLDER,
    NEXT_LIMIT,
    PANEL_INTRO,
    PANEL_NEXT_HEADING,
    PANEL_NEXT_IS_STAFF_ONLY,
    PANEL_TIMEOUT_FOOTER,
    PANEL_TITLE,
    age,
    card_lines,
    celebrates_today,
    chunked,
    clamp_month_day,
    date_modal_title,
    date_problem,
    local_today,
    member_zone_name,
    month_day_text,
    month_lines,
    next_occurrence,
    panel_allows_lookup,
    panel_buttons,
    panel_minutes,
    panel_shows_next,
    parse_birthday_input,
    parse_color,
    render_description,
    status_lines,
    stored_line,
    stored_prefill,
    stored_sentence,
    upcoming,
    upcoming_lines,
    year_problem,
)
from ...command_errors import AnswersErrors
from ...loops import wait_ready
from ...panels import (
    KEEP_IT,
    Panel,
    answer,
    confirm,
    confirm_items,
    opened,
    retire,
    still_staff,
)
from ...settings_store import (
    BIRTHDAY_MODES,
    DB_UNAVAILABLE,
    GUILD_ONLY,
    staff_roles_sentence,
)
from ..core import clear_key

log = logging.getLogger(__name__)

LOOP_MINUTES = 5
ROLE_REASON = "Black Bloc birthday"
COG_NAME = "Birthdays"

NOT_STORED = (
    "Black Bloc has no birthday for you, so there is nothing to change. Add one with the "
    "**Set my birthday** button — the year is optional, and leaving it out keeps your age "
    "private."
)
NOT_STORED_FOR = (
    "Black Bloc has no birthday for {who}. They can add one themselves with **Set my "
    "birthday** on `/birthday`, and staff can with **Set their birthday** here."
)
REMOVED = "Your birthday is forgotten. Nothing will be posted for you."
REMOVED_FOR = "**{who}**'s birthday is forgotten. Nothing will be posted for them."
FORGOTTEN_BY_STAFF = (
    "Staff have removed the birthday Black Bloc had stored for you in **{guild}**, so nothing "
    "will be posted for you. You can set it again yourself with `/birthday`."
)
OPTED_OUT = (
    "You are opted out — your birthday is still stored, but nothing will be posted. "
    "**Opt in** turns it back on, and **Remove** forgets it entirely."
)
OPTED_IN = "You are opted back in. Black Bloc will post on the day again."
ALREADY_OPTED = "You were already opted {state}, so nothing changed."
NOBODY_YET = (
    "Nobody has a birthday stored yet. People add their own with **Set my birthday** on "
    "`/birthday`."
)
NONE_THIS_MONTH = "Nobody has a birthday stored in **{month}**."
NOTHING_UPCOMING = (
    "There are no birthdays to show — everyone stored is opted out, or nobody has set one yet."
)
MODE_SET = "Birthday wishes are now **{mode}**."
REMOVE_CONFIRM = (
    "Forget your birthday? Black Bloc will stop posting for you and will not remember the "
    "date. You can set it again at any time."
)
FORGET_CONFIRM = (
    "Forget **{who}**'s birthday? Black Bloc will stop posting for them, and they are sent a "
    "DM saying staff removed it. They can set it again themselves."
)
ROLE_CLEAR_CONFIRM = (
    "Stop giving a birthday role at all? A role somebody already has for today still comes "
    "off tomorrow."
)
ROLE_CLEARED = (
    "No birthday role will be given any more. A role somebody already has for today still "
    "comes off tomorrow. Set one again with `/settings` ▸ **A setting group…** ▸ birthday."
)
ROLE_NOT_SET = (
    "There was no birthday role set, so nothing changed. `/settings` ▸ **A setting group…** "
    "▸ birthday is how one is chosen."
)
BUTTON_STYLES: dict[str, discord.ButtonStyle] = {
    "primary": discord.ButtonStyle.primary,
    "secondary": discord.ButtonStyle.secondary,
    "success": discord.ButtonStyle.success,
    "danger": discord.ButtonStyle.danger,
}

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


async def dm(user: Any, text: str) -> bool:
    """Whether the person actually got told; a closed DM is logged, never raised."""
    send = getattr(user, "send", None)
    if send is None:
        return False
    try:
        await send(text, allowed_mentions=discord.AllowedMentions.none())
    except Exception as exc:
        log.info("birthdays: could not DM %s: %s", getattr(user, "id", "?"), exc)
        return False
    return True


async def store_birthday(
    cog: Any,
    guild: Any,
    actor: Any,
    member: Any,
    month: Any,
    day: Any,
    year: Any,
    source: str,
) -> str:
    """The one path a birthday is written by — the refusal sentence, or the confirmation."""
    bot = cog.bot
    zone = await member_zone_name(bot.db, member.id)
    problem = date_problem(month, day) or year_problem(year, local_today(zone))
    if problem is not None:
        return problem
    m, d = clamp_month_day(month, day)
    async with cog._lock(member.id):
        await save_birthday(bot.db, guild.id, member.id, m, d, year, source)
    whose = "Your" if member.id == actor.id else f"**{member.display_name}**'s"
    await log_action(
        bot,
        guild,
        "birthday.set",
        actor=actor,
        target=member,
        details={"date": month_day_text(m, d), "year": year, "source": source},
    )
    return stored_sentence(whose, m, d, year, zone, next_occurrence(m, d, zone))


async def forget_birthday(
    cog: Any, guild: Any, actor: Any, member: Any = None, *, source: str = "self"
) -> str:
    """The row goes, and the role goes back first — review finding 3 of Phase 5."""
    bot = cog.bot
    target = member if member is not None else actor
    mine = target.id == actor.id
    async with cog._lock(target.id):
        row = await get_birthday(bot.db, target.id)
        if row is None:
            return (
                NOT_STORED
                if mine
                else NOT_STORED_FOR.format(who=f"**{target.display_name}**")
            )
        await cog._return_role(guild, row)
        await delete_birthday(bot.db, target.id)
    await log_action(
        bot,
        guild,
        "birthday.remove",
        actor=actor,
        target=target,
        details={"source": source},
    )
    if mine:
        return REMOVED
    await dm(target, FORGOTTEN_BY_STAFF.format(guild=guild.name))
    return REMOVED_FOR.format(who=target.display_name)


async def change_opt(cog: Any, guild: Any, actor: Any, *, opted_in: bool) -> str:
    bot = cog.bot
    row = await get_birthday(bot.db, actor.id)
    if row is None:
        return NOT_STORED
    if bool(row["opted_in"]) == opted_in:
        return ALREADY_OPTED.format(state="in" if opted_in else "out")
    async with cog._lock(actor.id):
        await set_opted_in(bot.db, actor.id, opted_in)
        if not opted_in:
            await cog._return_role(guild, row)
    await log_action(
        bot,
        guild,
        "birthday.optin" if opted_in else "birthday.optout",
        actor=actor,
    )
    return OPTED_IN if opted_in else OPTED_OUT


async def set_mode(bot: Any, guild: Any, actor: Any, mode: str) -> str:
    await bot.store.set(guild.id, "birthday_mode", mode, by=actor.id)
    await log_action(bot, guild, "birthday.mode", actor=actor, details={"mode": mode})
    return MODE_SET.format(mode=mode)


async def clear_role(bot: Any, guild: Any, actor: Any) -> str:
    """The shared writer keeps the row's shape; the words stay this feature's own."""
    outcome = await clear_key(bot, guild, "birthday_role_id", actor)
    return ROLE_CLEARED if outcome.ok else ROLE_NOT_SET


async def person_lines(bot: Any, guild: Any, member: Any, row: Any, *, mine: bool) -> list[str]:
    zone = await member_zone_name(bot.db, member.id)
    when = next_occurrence(row["month"], row["day"], zone)
    years = (
        age(row["year"], when.date())
        if row["year"] and bot.store.get(guild.id, "birthday_show_age")
        else None
    )
    return card_lines(
        member.display_name,
        row["month"],
        row["day"],
        row["year"],
        zone,
        when,
        years,
        bool(row["opted_in"]),
        mine,
    )


async def next_lines(bot: Any, guild: Any) -> list[str]:
    rows = [row for row in await rows_for_guild(bot.db, guild.id) if row["opted_in"]]
    if not rows:
        return [NOTHING_UPCOMING]
    entries = [
        {
            "user_id": row["user_id"],
            "month": row["month"],
            "day": row["day"],
            "year": row["year"],
            "tz": await member_zone_name(bot.db, row["user_id"]),
        }
        for row in rows
    ]
    found = upcoming_lines(entries, upcoming(entries, limit=NEXT_LIMIT))
    return [PANEL_NEXT_HEADING, *found]


def panel_colour(store: Any, guild_id: int) -> discord.Colour:
    return discord.Colour(parse_color(store.get(guild_id, "birthday_color")))


async def build_panel(bot: Any, guild: Any, actor: Any) -> tuple[discord.Embed, BirthdayView]:
    store = bot.store
    staff = store.is_staff(actor)
    row = await get_birthday(bot.db, actor.id)
    has_date = row is not None
    opted_out = bool(has_date and not row["opted_in"])
    mode = str(store.get(guild.id, "birthday_mode"))

    lines = [PANEL_INTRO]
    warning = MODE_WARNINGS.get(mode)
    if warning:
        lines.append(warning)
    if has_date:
        lines.extend(await person_lines(bot, guild, actor, row, mine=True))
    else:
        lines.append(NOT_STORED)
    if staff or panel_shows_next(store, guild.id):
        lines.extend(await next_lines(bot, guild))
    else:
        lines.append(PANEL_NEXT_IS_STAFF_ONLY)
    if staff:
        lines.append(stored_line(await stored_counts(bot.db, guild.id)))

    embed = discord.Embed(
        title=PANEL_TITLE,
        description="\n".join(lines),
        colour=panel_colour(store, guild.id),
    )
    view = BirthdayView(panel_minutes(store, guild.id))
    for spec in panel_buttons(has_date, opted_out):
        view.add_item(MoveButton(spec))
    if staff or panel_allows_lookup(store, guild.id):
        view.add_item(LookupSelect())
    if staff:
        view.add_item(MonthSelect())
        view.add_item(ModeSelect(mode))
        view.add_item(StatusButton())
        view.add_item(ClearRoleButton())
        view.add_item(LogsButton())
    return embed, view


async def build_card(
    bot: Any, guild: Any, actor: Any, member: Any
) -> tuple[discord.Embed, BirthdayView]:
    store = bot.store
    staff = store.is_staff(actor)
    mine = member.id == actor.id
    row = await get_birthday(bot.db, member.id)
    if row is None:
        lines = [
            NOT_STORED if mine else NOT_STORED_FOR.format(who=f"**{member.display_name}**")
        ]
    else:
        lines = await person_lines(bot, guild, member, row, mine=mine)
    embed = discord.Embed(
        title=f"{member.display_name} — birthday",
        description="\n".join(lines),
        colour=panel_colour(store, guild.id),
    )
    view = BirthdayView(panel_minutes(store, guild.id))
    if staff:
        view.add_item(SetTheirsButton(member))
        if row is not None:
            view.add_item(ForgetTheirsButton(member))
    view.add_item(BackButton())
    return embed, view


async def render_panel(interaction: discord.Interaction, previous: Any = None) -> None:
    bot = interaction.client
    embed, view = await build_panel(bot, interaction.guild, interaction.user)
    retire(previous)
    view.message = await interaction.edit_original_response(
        embed=embed, view=view, allowed_mentions=discord.AllowedMentions.none()
    )


async def render_card(
    interaction: discord.Interaction, member: Any, previous: Any = None
) -> None:
    bot = interaction.client
    embed, view = await build_card(bot, interaction.guild, interaction.user, member)
    retire(previous)
    view.message = await interaction.edit_original_response(
        embed=embed, view=view, allowed_mentions=discord.AllowedMentions.none()
    )


async def said_after(interaction: discord.Interaction, said: str) -> None:
    await interaction.followup.send(
        said, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
    )


async def back_to_panel(interaction: discord.Interaction, previous: Any = None) -> None:
    if not await opened(interaction, staff=False):
        return
    await render_panel(interaction, previous)


async def open_card(
    interaction: discord.Interaction, member: Any, previous: Any = None
) -> None:
    if not await opened(interaction, staff=False):
        return
    await render_card(interaction, member, previous)


async def open_confirm(
    interaction: discord.Interaction, text: str, items: list[Any], previous: Any = None
) -> None:
    """The question is the card's whole description here, so no `Are you sure?` field is added."""
    bot = interaction.client
    await confirm(
        interaction,
        BirthdayView(panel_minutes(bot.store, interaction.guild.id)),
        discord.Embed(
            title=PANEL_TITLE,
            description=text,
            colour=panel_colour(bot.store, interaction.guild.id),
        ),
        items,
        previous,
    )


async def open_remove_confirm(interaction: discord.Interaction, previous: Any = None) -> None:
    if not await opened(interaction, staff=False):
        return
    row = await get_birthday(interaction.client.db, interaction.user.id)
    if row is None:
        await render_panel(interaction, previous)
        await said_after(interaction, NOT_STORED)
        return
    await open_confirm(
        interaction,
        REMOVE_CONFIRM,
        confirm_items(
            yes="Yes, forget it",
            no=KEEP_IT,
            on_yes=run_remove,
            on_no=back_to_panel,
        ),
        previous,
    )


async def open_forget_confirm(
    interaction: discord.Interaction, member: Any, previous: Any = None
) -> None:
    if not await still_staff(interaction):
        return
    if not await opened(interaction, staff=False):
        return
    await open_confirm(
        interaction,
        FORGET_CONFIRM.format(who=member.display_name),
        confirm_items(
            yes="Yes, forget it",
            no=KEEP_IT,
            on_yes=lambda one, card: run_forget(one, member, card),
            on_no=lambda one, card: open_card(one, member, card),
        ),
        previous,
    )


async def open_role_clear_confirm(
    interaction: discord.Interaction, previous: Any = None
) -> None:
    if not await still_staff(interaction):
        return
    if not await opened(interaction, staff=False):
        return
    await open_confirm(
        interaction,
        ROLE_CLEAR_CONFIRM,
        confirm_items(
            yes="Yes, clear it",
            no="Cancel",
            on_yes=run_clear_role,
            on_no=back_to_panel,
        ),
        previous,
    )


async def run_opt(
    interaction: discord.Interaction, opted_in: bool, previous: Any = None
) -> None:
    if not await opened(interaction, staff=False):
        return
    cog = interaction.client.get_cog(COG_NAME)
    said = await change_opt(cog, interaction.guild, interaction.user, opted_in=opted_in)
    await render_panel(interaction, previous)
    await said_after(interaction, said)


async def run_remove(interaction: discord.Interaction, previous: Any = None) -> None:
    if not await opened(interaction, staff=False):
        return
    cog = interaction.client.get_cog(COG_NAME)
    said = await forget_birthday(cog, interaction.guild, interaction.user)
    await render_panel(interaction, previous)
    await said_after(interaction, said)


async def run_forget(
    interaction: discord.Interaction, member: Any, previous: Any = None
) -> None:
    if not await still_staff(interaction):
        return
    if not await opened(interaction, staff=False):
        return
    cog = interaction.client.get_cog(COG_NAME)
    said = await forget_birthday(
        cog, interaction.guild, interaction.user, member, source="staff"
    )
    await render_card(interaction, member, previous)
    await said_after(interaction, said)


async def run_mode(
    interaction: discord.Interaction, mode: str, previous: Any = None
) -> None:
    if not await still_staff(interaction):
        return
    if not await opened(interaction, staff=False):
        return
    said = await set_mode(interaction.client, interaction.guild, interaction.user, mode)
    await render_panel(interaction, previous)
    await said_after(interaction, said)


async def run_clear_role(interaction: discord.Interaction, previous: Any = None) -> None:
    if not await still_staff(interaction):
        return
    if not await opened(interaction, staff=False):
        return
    said = await clear_role(interaction.client, interaction.guild, interaction.user)
    await render_panel(interaction, previous)
    await said_after(interaction, said)


async def send_month(interaction: discord.Interaction, month: int) -> None:
    if not await still_staff(interaction):
        return
    if not await opened(interaction, staff=False):
        return
    bot = interaction.client
    rows = await rows_for_guild(bot.db, interaction.guild.id)
    if month:
        rows = [row for row in rows if row["month"] == month]
    if not rows:
        await said_after(
            interaction,
            NONE_THIS_MONTH.format(month=MONTH_NAMES[month - 1]) if month else NOBODY_YET,
        )
        return
    for page in chunked(month_lines(rows)):
        await said_after(interaction, page)


async def send_status(interaction: discord.Interaction) -> None:
    if not await still_staff(interaction):
        return
    if not await opened(interaction, staff=False):
        return
    bot = interaction.client
    guild = interaction.guild
    store = bot.store
    cog = bot.get_cog(COG_NAME)
    values = {
        "mode": store.get(guild.id, "birthday_mode"),
        "channel_id": store.get(guild.id, "birthday_channel_id"),
        "template": store.get(guild.id, "birthday_template"),
        "color": store.get(guild.id, "birthday_color"),
        "role_id": store.get(guild.id, "birthday_role_id"),
        "test_mode": getattr(bot, "guard", None) is not None,
        "show_age": store.get(guild.id, "birthday_show_age"),
        "totals": await stored_counts(bot.db, guild.id),
        "staff": staff_roles_sentence(store.staff_roles(guild)),
        "last_run_at": cog.last_run_at,
        "last_error": cog.last_error,
        "loop_minutes": LOOP_MINUTES,
    }
    await said_after(interaction, "\n".join(status_lines(values)))


class BirthdayView(Panel):
    def __init__(self, minutes: int) -> None:
        super().__init__(minutes, footer=PANEL_TIMEOUT_FOOTER)


class MoveButton(discord.ui.Button):
    def __init__(self, spec: Any) -> None:
        super().__init__(label=spec.label, style=BUTTON_STYLES[spec.style], row=0)
        self.spec = spec

    async def callback(self, interaction: discord.Interaction) -> None:
        if self.spec.needs_modal:
            await open_date_modal(interaction, interaction.user, mine=True, previous=self.view)
            return
        if self.spec.action == "remove":
            await open_remove_confirm(interaction, self.view)
            return
        if self.spec.action == "refresh":
            await back_to_panel(interaction, self.view)
            return
        await run_opt(interaction, self.spec.action == "optin", self.view)


class LookupSelect(discord.ui.UserSelect):
    def __init__(self) -> None:
        super().__init__(placeholder=LOOKUP_PLACEHOLDER, min_values=1, max_values=1, row=1)

    async def callback(self, interaction: discord.Interaction) -> None:
        await open_card(interaction, self.values[0], self.view)


class MonthSelect(discord.ui.Select):
    def __init__(self) -> None:
        options = [discord.SelectOption(label=EVERY_MONTH, value="0")] + [
            discord.SelectOption(label=name, value=str(number))
            for number, name in enumerate(MONTH_NAMES, start=1)
        ]
        super().__init__(
            placeholder=MONTH_PLACEHOLDER, options=options, min_values=1, max_values=1, row=2
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await send_month(interaction, int(self.values[0]))


class ModeSelect(discord.ui.Select):
    def __init__(self, current: str) -> None:
        options = [
            discord.SelectOption(label=name, value=name, default=name == current)
            for name in BIRTHDAY_MODES
        ]
        super().__init__(
            placeholder=MODE_PLACEHOLDER, options=options, min_values=1, max_values=1, row=3
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await run_mode(interaction, self.values[0], self.view)


class StatusButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label="Status", style=discord.ButtonStyle.secondary, row=4)

    async def callback(self, interaction: discord.Interaction) -> None:
        await send_status(interaction)


class ClearRoleButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(
            label="Clear the birthday role", style=discord.ButtonStyle.danger, row=4
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await open_role_clear_confirm(interaction, self.view)


class LogsButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label="Logs", style=discord.ButtonStyle.secondary, row=4)

    async def callback(self, interaction: discord.Interaction) -> None:
        await send_logs(interaction, "birthday")


class BackButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label="Back", style=discord.ButtonStyle.secondary, row=1)

    async def callback(self, interaction: discord.Interaction) -> None:
        await back_to_panel(interaction, self.view)


class SetTheirsButton(discord.ui.Button):
    def __init__(self, member: Any) -> None:
        super().__init__(label="Set their birthday", style=discord.ButtonStyle.primary, row=0)
        self.member = member

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await still_staff(interaction):
            return
        await open_date_modal(interaction, self.member, mine=False, previous=self.view)


class ForgetTheirsButton(discord.ui.Button):
    def __init__(self, member: Any) -> None:
        super().__init__(
            label="Forget their birthday", style=discord.ButtonStyle.danger, row=0
        )
        self.member = member

    async def callback(self, interaction: discord.Interaction) -> None:
        await open_forget_confirm(interaction, self.member, self.view)


class DateModal(AnswersErrors, discord.ui.Modal):
    typed = discord.ui.TextInput(
        label=DATE_LABEL, placeholder=DATE_PLACEHOLDER, max_length=DATE_INPUT_LIMIT
    )

    def __init__(
        self,
        cog: Any,
        member: Any,
        *,
        mine: bool,
        previous: Any = None,
        current: str | None = None,
    ) -> None:
        super().__init__(title=date_modal_title(mine, getattr(member, "display_name", "")))
        self.cog = cog
        self.member = member
        self.mine = mine
        self.previous = previous
        self.typed.default = current or None

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await self.cog.date_submit(
            interaction, self.member, str(self.typed), mine=self.mine, previous=self.previous
        )


async def open_date_modal(
    interaction: discord.Interaction, member: Any, *, mine: bool, previous: Any = None
) -> None:
    """A modal cannot follow a defer, so the prefill is read before anything is acknowledged."""
    bot = interaction.client
    if not bot.db.is_connected:
        await answer(interaction, DB_UNAVAILABLE)
        return
    row = await get_birthday(bot.db, member.id)
    current = (
        stored_prefill(row["month"], row["day"], row["year"]) if row is not None else None
    )
    await interaction.response.send_modal(
        DateModal(
            bot.get_cog(COG_NAME), member, mine=mine, previous=previous, current=current
        )
    )


class Birthdays(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._locks: dict[int, asyncio.Lock] = {}
        self._said: dict[tuple[int, str], str] = {}
        self.last_run_at: str | None = None
        self.last_error: str | None = None

    def loop_health(self, name: str) -> tuple[str | None, str | None]:
        if name == "_sweep":
            return (self.last_run_at, self.last_error)
        return (None, None)

    async def cog_load(self) -> None:
        if not self.bot.db.is_connected:
            return
        self._sweep.start()

    async def cog_unload(self) -> None:
        self._sweep.cancel()

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
        await wait_ready(self.bot, self._sweep_stopped)

    @_sweep.error
    async def _sweep_stopped(self, exc: BaseException) -> None:
        """The loop stops for the life of the process unless it is started again."""
        self.last_error = f"{type(exc).__name__}: {exc}"
        log.error("birthdays: the sweep stopped; restarting it", exc_info=exc)
        self._sweep.restart()

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        if not self.bot.db.is_connected:
            return
        if not self._sweep.is_running():
            self._sweep.start()

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
            await answer(interaction, GUILD_ONLY)
            return False
        if not self.bot.db.is_connected:
            log.warning("birthdays: refused a command — the database is not connected")
            await answer(interaction, DB_UNAVAILABLE)
            return False
        return True

    async def _zone_of(self, user_id: int) -> str:
        return await member_zone_name(self.bot.db, user_id)

    @app_commands.command(
        name="birthday", description="Your birthday, and whose is coming up"
    )
    async def birthday(self, interaction: discord.Interaction) -> None:
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

    async def date_submit(
        self,
        interaction: discord.Interaction,
        member: Any,
        typed: str,
        *,
        mine: bool,
        previous: Any = None,
    ) -> None:
        """What the one date modal does once it is filled in, for the self and staff paths."""
        if not mine and not await still_staff(interaction):
            return
        if not await opened(interaction, staff=False):
            return
        parsed = parse_birthday_input(typed)
        if parsed is None:
            said = DATE_UNREADABLE
        else:
            month, day, year = parsed
            said = await store_birthday(
                self,
                interaction.guild,
                interaction.user,
                member,
                month,
                day,
                year,
                "self" if mine else "staff",
            )
        if mine:
            await render_panel(interaction, previous)
        else:
            await render_card(interaction, member, previous)
        await said_after(interaction, said)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Birthdays(bot))
