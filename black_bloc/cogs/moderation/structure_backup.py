from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands, tasks

from ... import shadow, structure_store
from ...actionlog import entity_id, log_action
from ...command_visibility import STAFF_ONLY
from ...logkinds import VIA_DISCORD, kind_via
from ...loops import wait_ready
from ...panels import Panel, answer, clamped, db_up, opened, retire
from ...settings_store import (
    DEFAULT_TIMEZONE_KEY,
    GUILD_ONLY,
    STRUCTURE_BACKUP_CHANNEL,
    STRUCTURE_BACKUP_DEFAULTS,
    STRUCTURE_BACKUP_HOUR,
    STRUCTURE_BACKUP_KEEP,
    STRUCTURE_BACKUP_MODE,
    STRUCTURE_BACKUP_NOTICE_LINES,
    STRUCTURE_BACKUP_NOTIFY,
    STRUCTURE_BACKUP_PANEL_MINUTES,
    STRUCTURE_SAY_KEYS,
    require_staff,
)
from ...structure import (
    DAILY,
    FAILED,
    FEATURE,
    MANUAL,
    MODES,
    OFF,
    PAGE,
    SAVED,
    UNCHANGED,
    body_of,
)
from ...structure_capture import CaptureError, capture
from ...structure_diff import changes as changes_between
from ...timezones import unix, zone

log = logging.getLogger(__name__)

COG_NAME = "StructureBackup"
LOOP_MINUTES = 10
DAILY_RETRIES = 3
LOCK_ATTR = "_structure_backup_lock"

UNAVAILABLE = (
    "Discord says the server is unavailable right now, so its roles and channels could not be "
    "read. Try again in a few minutes."
)
FORBIDDEN = (
    "Discord refused to list the server's roles and channels (Discord said: {said}). Check "
    "that Black Bloc is still in the server with View Channels, then try again."
)
DISCORD_ERROR = (
    "Discord answered with an error ({status}: {said}), so nothing was read. Try again in a "
    "minute."
)
UNEXPECTED = (
    "something unexpected went wrong ({what}). The bot's own log has the detail; tell a Lead "
    "if it keeps happening."
)
NO_NOTICE_CHANNEL = "the channel the notice is aimed at is not one Black Bloc can find"


@dataclass(frozen=True)
class Taken:
    """What one look answered with, in the words both doors show."""

    outcome: str
    said: str
    row: Any = None
    previous: Any = None
    changes: tuple[dict[str, str], ...] = ()
    reason: str = ""


def mode_of(bot: Any, guild_id: int) -> str:
    found = str(bot.store.get(guild_id, STRUCTURE_BACKUP_MODE))
    return found if found in MODES else OFF


def said(store: Any, guild_id: int, key: str, **fields: Any) -> str:
    """Staff wording first; a template that cannot be filled falls back to the shipped one."""
    wording = str(store.get(guild_id, key) or "").strip()
    if wording:
        try:
            return wording.format(**fields)
        except (IndexError, KeyError, ValueError):
            log.warning("structure: %s could not be filled in; the shipped wording was used", key)
    return str(STRUCTURE_BACKUP_DEFAULTS[key]).format(**fields)


def say_words(store: Any, guild_id: int) -> dict[str, str]:
    return {name: store.get(guild_id, key) for name, key in STRUCTURE_SAY_KEYS.items()}


def when_words(at: Any) -> str:
    try:
        return f"<t:{unix(datetime.fromisoformat(str(at)))}:f>"
    except (TypeError, ValueError):
        return str(at or "")


def failure_reason(exc: BaseException) -> str:
    if isinstance(exc, CaptureError):
        return str(exc)
    if isinstance(exc, discord.Forbidden):
        return FORBIDDEN.format(said=exc.text or exc.status)
    if isinstance(exc, discord.HTTPException):
        return DISCORD_ERROR.format(status=exc.status, said=exc.text or type(exc).__name__)
    return UNEXPECTED.format(what=type(exc).__name__)


def lock_for(bot: Any) -> asyncio.Lock:
    found = getattr(bot, LOCK_ATTR, None)
    if found is None:
        found = asyncio.Lock()
        setattr(bot, LOCK_ATTR, found)
    return found


async def read_structure(guild: Any) -> dict[str, Any]:
    """Reads only. Nothing in this feature writes a role, a channel or a permission."""
    if getattr(guild, "unavailable", False):
        raise CaptureError(UNAVAILABLE)
    roles = await guild.fetch_roles()
    channels = await guild.fetch_channels()
    return capture(guild, roles, channels)


async def safely(writing: Any, what: str) -> Any:
    try:
        return await writing
    except Exception as exc:
        log.warning("structure: %s not written — %s: %s", what, type(exc).__name__, exc)
        return None


def snapshot_details(row: Any, source: str) -> dict[str, Any]:
    return {
        "snapshot_id": row["id"],
        "source": source,
        "roles": row["roles"],
        "categories": row["categories"],
        "channels": row["channels"],
        "overwrites": row["overwrites"],
    }


async def take_snapshot(
    bot: Any,
    guild: Any,
    *,
    source: str = MANUAL,
    actor: Any = None,
    via: str = VIA_DISCORD,
    day: str | None = None,
    now: datetime | None = None,
) -> Taken:
    """The one door every snapshot goes through. It never raises; a failure is an outcome."""
    store = bot.store
    if mode_of(bot, guild.id) == OFF:
        return Taken(OFF, said(store, guild.id, "structure_backup_off_said"))
    async with lock_for(bot):
        try:
            body = await read_structure(guild)
            stored = await structure_store.store(
                bot.db,
                guild.id,
                body,
                source=source,
                taken_by=entity_id(actor),
                keep=int(store.get(guild.id, STRUCTURE_BACKUP_KEEP)),
                now=now,
            )
        except Exception as exc:
            return await failed(bot, guild, exc, source=source, actor=actor, via=via, day=day)
        await safely(
            structure_store.record_look(bot.db, guild.id, stored.outcome, day=day, now=now),
            "the look",
        )
    row = stored.row
    if stored.outcome == UNCHANGED:
        await safely(
            log_action(
                bot,
                guild,
                kind_via("structure.unchanged", via),
                actor=actor,
                details={"via": via, "snapshot_id": row["id"], "source": source},
            ),
            "the log row",
        )
        return Taken(
            UNCHANGED, said(store, guild.id, "structure_backup_unchanged_said", id=row["id"]), row
        )
    found: list[dict[str, str]] = []
    if stored.previous is not None:
        found = changes_between(body_of(stored.previous), body, say_words(store, guild.id))
    details = snapshot_details(row, source) | {"via": via, "changes": len(found)}
    if stored.previous is not None:
        details["previous_id"] = stored.previous["id"]
    await safely(
        log_action(bot, guild, kind_via("structure.captured", via), actor=actor, details=details),
        "the log row",
    )
    if stored.pruned:
        await safely(
            log_action(bot, guild, "structure.pruned", details={"removed": stored.pruned}),
            "the log row",
        )
    return Taken(
        SAVED,
        said(store, guild.id, "structure_backup_saved_said", id=row["id"]),
        row,
        stored.previous,
        tuple(found),
    )


async def failed(
    bot: Any, guild: Any, exc: BaseException, *, source: str, actor: Any, via: str, day: Any
) -> Taken:
    reason = failure_reason(exc)
    log.warning("structure: no snapshot of guild %s — %s: %s", guild.id, type(exc).__name__, exc)
    await safely(
        structure_store.record_look(bot.db, guild.id, FAILED, day=day, reason=reason),
        "the look",
    )
    await safely(
        log_action(
            bot,
            guild,
            kind_via("structure.capture_failed", via),
            actor=actor,
            details={"via": via, "source": source, "reason": reason},
        ),
        "the log row",
    )
    return Taken(
        FAILED,
        said(bot.store, guild.id, "structure_backup_failed_said", reason=reason),
        reason=reason,
    )


async def changes_since(bot: Any, guild: Any, row: Any) -> list[dict[str, str]]:
    """A stored snapshot against the server as it is now; read, compared, thrown away."""
    return changes_between(
        body_of(row), await read_structure(guild), say_words(bot.store, guild.id)
    )


async def record_download(
    bot: Any, guild: Any, actor: Any, row: Any, *, via: str = VIA_DISCORD
) -> None:
    await log_action(
        bot,
        guild,
        kind_via("structure.downloaded", via),
        actor=actor,
        details={"via": via, "snapshot_id": row["id"]},
    )


def change_lines(store: Any, guild_id: int, found: Any) -> list[str]:
    limit = int(store.get(guild_id, STRUCTURE_BACKUP_NOTICE_LINES))
    lines = [f"• {one['text']}" for one in list(found)[:limit]]
    left = len(found) - len(lines)
    if left > 0:
        lines.append(said(store, guild_id, "structure_backup_notice_more", n=left))
    return lines


def notice_embed(bot: Any, guild: Any, taken: Taken) -> discord.Embed:
    store = bot.store
    first = said(
        store,
        guild.id,
        "structure_backup_notice_text",
        n=len(taken.changes),
        when=when_words(taken.previous["taken_at"]),
    )
    return discord.Embed(
        title=said(store, guild.id, "structure_backup_notice_title"),
        description=clamped([first, *change_lines(store, guild.id, taken.changes)]),
    )


def notice_home(bot: Any, guild: Any) -> tuple[int | None, int | None, str]:
    """Where the notice goes, where it is aimed, and the rehearsal line when those differ."""
    store = bot.store
    aimed = shadow.as_channel_id(
        store.get(guild.id, STRUCTURE_BACKUP_CHANNEL) or store.get(guild.id, "staff_channel_id")
    )
    if mode_of(bot, guild.id) != "shadow":
        return (aimed, aimed, "")
    home = shadow.channel_id(bot, guild, feature=FEATURE)
    words = f"<#{aimed}>" if aimed else ""
    return (home, aimed, shadow.note_line(bot, guild, words))


async def post_notice(bot: Any, guild: Any, taken: Taken) -> bool:
    """The only thing this feature posts: staff are told a daily snapshot differs."""
    if not taken.changes or taken.previous is None:
        return False
    if not bot.store.get(guild.id, STRUCTURE_BACKUP_NOTIFY):
        return False
    mode = mode_of(bot, guild.id)
    home, aimed, note = notice_home(bot, guild)
    details = {"mode": mode, "channel_id": home, "aimed_at": aimed, "snapshot_id": taken.row["id"]}
    channel = shadow.channel_of(bot, guild, home)
    try:
        if channel is None:
            raise CaptureError(NO_NOTICE_CHANNEL)
        await channel.send(
            note or None,
            embed=notice_embed(bot, guild, taken),
            allowed_mentions=discord.AllowedMentions.none(),
        )
    except Exception as exc:
        reason = str(exc) if isinstance(exc, CaptureError) else f"{type(exc).__name__}: {exc}"
        log.warning("structure: the notice was not posted — %s", reason)
        await safely(
            log_action(
                bot, guild, "structure.notice_failed", details=details | {"reason": reason}
            ),
            "the log row",
        )
        return False
    await safely(
        log_action(bot, guild, "structure.notice_posted", details=details), "the log row"
    )
    return True


def local_now(bot: Any, guild_id: int, now: datetime | None = None) -> datetime:
    moment = now or datetime.now(UTC)
    return moment.astimezone(zone(bot.store.get(guild_id, DEFAULT_TIMEZONE_KEY)) or UTC)


async def run_daily(bot: Any, guild: Any, now: datetime | None = None) -> Taken | None:
    """One guild's turn: nothing before the hour, once a day after it, a failure tried again."""
    if mode_of(bot, guild.id) == OFF or getattr(guild, "unavailable", False):
        return None
    local = local_now(bot, guild.id, now)
    if local.hour < int(bot.store.get(guild.id, STRUCTURE_BACKUP_HOUR)):
        return None
    day = local.date().isoformat()
    looked = await structure_store.look(bot.db, guild.id)
    if not structure_store.daily_due(looked, day, retries=DAILY_RETRIES):
        return None
    taken = await take_snapshot(bot, guild, source=DAILY, day=day, now=now)
    if taken.outcome == SAVED:
        await post_notice(bot, guild, taken)
    return taken


class StructurePanel(Panel):
    def __init__(self, bot: Any, guild_id: int) -> None:
        super().__init__(
            int(bot.store.get(guild_id, STRUCTURE_BACKUP_PANEL_MINUTES)),
            footer=said(bot.store, guild_id, "structure_backup_panel_footer"),
            again=render_panel,
        )


class TakeButton(discord.ui.Button):
    def __init__(self, label: str) -> None:
        super().__init__(label=label, style=discord.ButtonStyle.primary, row=0)

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await opened(interaction):
            return
        taken = await take_snapshot(
            interaction.client, interaction.guild, source=MANUAL, actor=interaction.user
        )
        await render_panel(interaction, self.view, note=taken.said)


class ChangesButton(discord.ui.Button):
    def __init__(self, label: str) -> None:
        super().__init__(label=label, style=discord.ButtonStyle.secondary, row=0)

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await opened(interaction):
            return
        bot, guild = interaction.client, interaction.guild
        row = await structure_store.latest(bot.db, guild.id)
        if row is None:
            await render_panel(interaction, self.view)
            return
        try:
            found = await changes_since(bot, guild, row)
        except Exception as exc:
            reason = failure_reason(exc)
            log.warning("structure: could not compare — %s: %s", type(exc).__name__, exc)
            note = said(bot.store, guild.id, "structure_backup_failed_said", reason=reason)
            await render_panel(interaction, self.view, note=note)
            return
        await render_panel(interaction, self.view, found=found)


def look_line(store: Any, guild_id: int, looked: Any) -> str | None:
    if looked is None:
        return None
    key = {
        SAVED: "structure_backup_look_saved",
        UNCHANGED: "structure_backup_look_unchanged",
        FAILED: "structure_backup_look_failed",
    }.get(looked["outcome"])
    if key is None:
        return None
    return said(
        store, guild_id, key, when=when_words(looked["last_at"]), reason=looked["reason"] or ""
    )


def latest_line(store: Any, guild_id: int, row: Any) -> str:
    if row is None:
        return said(store, guild_id, "structure_backup_none_yet")
    return said(
        store,
        guild_id,
        "structure_backup_latest_line",
        id=row["id"],
        when=when_words(row["taken_at"]),
        roles=row["roles"],
        categories=row["categories"],
        channels=row["channels"],
        overwrites=row["overwrites"],
    )


def site_url(bot: Any) -> str | None:
    origin = str(getattr(getattr(bot, "settings", None), "origin", "") or "").strip()
    return f"{origin.rstrip('/')}/{PAGE}" if origin else None


async def build_panel(
    bot: Any, guild: Any, *, note: str = "", found: Any = None
) -> tuple[discord.Embed, StructurePanel]:
    store, guild_id = bot.store, guild.id
    mode = mode_of(bot, guild_id)
    row = await structure_store.latest(bot.db, guild_id)
    looked = await structure_store.look(bot.db, guild_id)
    embed = discord.Embed(
        title=said(store, guild_id, "structure_backup_panel_title"), description=note or None
    )
    embed.add_field(
        name=said(store, guild_id, "structure_backup_mode_label"), value=mode, inline=False
    )
    embed.add_field(
        name=said(store, guild_id, "structure_backup_latest_label"),
        value=latest_line(store, guild_id, row)[:1024],
        inline=False,
    )
    last = look_line(store, guild_id, looked)
    if last:
        embed.add_field(
            name=said(store, guild_id, "structure_backup_look_label"),
            value=last[:1024],
            inline=False,
        )
    if found is not None:
        lines = change_lines(store, guild_id, found) or [
            said(store, guild_id, "structure_backup_no_changes_said")
        ]
        embed.add_field(
            name=said(store, guild_id, "structure_backup_changes_label"),
            value=fitted(lines),
            inline=False,
        )
    view = StructurePanel(bot, guild_id)
    if mode != OFF:
        view.add_item(TakeButton(said(store, guild_id, "structure_backup_take_label")))
    if row is not None:
        view.add_item(ChangesButton(said(store, guild_id, "structure_backup_changes_label")))
    url = site_url(bot)
    if url:
        view.add_item(
            discord.ui.Button(
                label=said(store, guild_id, "structure_backup_site_label"),
                style=discord.ButtonStyle.link,
                url=url,
                row=0,
            )
        )
    return (embed, view)


def fitted(lines: list[str], limit: int = 1024) -> str:
    """An embed field holds 1024 characters; whole lines are kept until the next would not fit."""
    kept: list[str] = []
    spent = 0
    for line in lines:
        if spent + len(line) + 1 > limit:
            break
        kept.append(line)
        spent += len(line) + 1
    return "\n".join(kept) or lines[0][:limit]


async def render_panel(
    interaction: discord.Interaction, previous: Any = None, *, note: str = "", found: Any = None
) -> None:
    embed, view = await build_panel(
        interaction.client, interaction.guild, note=note, found=found
    )
    retire(previous)
    view.message = await interaction.edit_original_response(
        embed=embed, view=view, allowed_mentions=discord.AllowedMentions.none()
    )


class StructureBackup(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.last_run_at: str | None = None
        self.last_error: str | None = None

    def loop_health(self, name: str) -> tuple[str | None, str | None]:
        if name == "_daily":
            return (self.last_run_at, self.last_error)
        return (None, None)

    async def cog_load(self) -> None:
        if not self.bot.db.is_connected:
            return
        self._daily.start()

    async def cog_unload(self) -> None:
        self._daily.cancel()

    async def run_once(self, now: datetime | None = None) -> None:
        for guild in list(self.bot.guilds):
            await run_daily(self.bot, guild, now)

    @tasks.loop(minutes=LOOP_MINUTES)
    async def _daily(self) -> None:
        if not self.bot.db.is_connected:
            return
        try:
            await self.run_once()
        except Exception as exc:
            self.last_error = f"{type(exc).__name__}: {exc}"
            log.exception("structure: the daily look failed")
            return
        self.last_error = None
        self.last_run_at = datetime.now(UTC).isoformat()

    @_daily.before_loop
    async def _before_daily(self) -> None:
        await wait_ready(self.bot, self._daily_stopped)

    @_daily.error
    async def _daily_stopped(self, exc: BaseException) -> None:
        """The loop stops for the life of the process unless it is started again."""
        self.last_error = f"{type(exc).__name__}: {exc}"
        log.error("structure: the daily loop stopped; restarting it", exc_info=exc)
        self._daily.restart()

    @app_commands.command(
        name="structure", description="The saved copies of roles, channels and permissions"
    )
    @app_commands.default_permissions(STAFF_ONLY)
    async def structure(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await answer(interaction, GUILD_ONLY)
            return
        if not await require_staff(interaction):
            return
        if not await db_up(interaction):
            return
        embed, view = await build_panel(self.bot, interaction.guild)
        await interaction.response.send_message(
            embed=embed,
            view=view,
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        view.message = await interaction.original_response()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(StructureBackup(bot))
