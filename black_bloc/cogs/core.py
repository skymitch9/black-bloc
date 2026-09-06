from __future__ import annotations

import logging
from functools import partial
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands, tasks

from .. import __version__, selftest
from .. import settings_panel as sp
from ..actionlog import log_action, send_logs
from ..command_errors import AnswersErrors
from ..command_visibility import STAFF_ONLY, hidden_names
from ..logkinds import CORE, SELFTEST, VIA_DISCORD
from ..modcases import pages_under_limit
from ..panels import (
    Outcome,
    Panel,
    answer,
    clamped,
    db_ready,
    db_up,
    refusal,
    retire,
    still_staff,
)
from ..settings_store import (
    GUILD_ONLY,
    KEY_CHOICES,
    KEY_HELP,
    KEY_MAX,
    KEY_MIN,
    SettingError,
    display_value,
    is_staff_command,
    namespace_of,
    parse_value,
    require_staff,
)
from .presence import COG_NAME as PRESENCE_COG
from .presence import reapply_presence

CLEARED = "**{key}** is no longer set, so Black Bloc is back to its own default for it."
NOT_SET = "**{key}** was not set for this server, so nothing changed."
STAFF_SUFFIX = " (staff)"
HELP_HEADER = (
    "Every command Black Bloc can run here. The ones marked (staff) need the Manage Server "
    "permission or a role that can see the staff channel."
)
NO_MATCH = (
    "No command matches **{filter}**, so there is nothing to list. Run `/help` with nothing in "
    "the filter to see all of them."
)
HIDDEN_NOTE = (
    "\n*{count} command(s) are not listed because their feature is turned off. A Lead brings "
    "one back from the dashboard's Settings page, or with `/settings` ▸ "
    "**Turn a feature back on…**.*"
)


SAVED = "**{key}** is now {value}."
BAD_VALUE = "bad_value"
NOTHING_STORED = "nothing_stored"

log = logging.getLogger(__name__)

PURGE_EVERY_SECONDS = 60
PURGE_LOOP = "purge_loop"


def actor_id(actor: Any) -> int | None:
    return int(getattr(actor, "id", actor) or 0) or None


async def set_key(
    bot: Any, guild: Any, key: str, value: Any, actor: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    """One write and one `settings.set` row, whatever control on the panel made the change."""
    try:
        stored = await bot.store.set(guild.id, key, value, by=actor_id(actor))
    except SettingError as exc:
        return refusal(str(exc), BAD_VALUE, 400)
    await log_action(
        bot,
        guild,
        "settings.set",
        actor=actor,
        details={"key": key, "value": stored, "via": via},
    )
    return Outcome(True, SAVED.format(key=key, value=display_value(key, stored)), value=stored)


async def clear_key(
    bot: Any, guild: Any, key: str, actor: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    """One delete and one `settings.clear` row; `value` is whether a row was actually there."""
    try:
        cleared = await bot.store.clear(guild.id, key, by=actor_id(actor))
    except SettingError as exc:
        return refusal(str(exc), BAD_VALUE, 400)
    if not cleared:
        return refusal(NOT_SET.format(key=key), NOTHING_STORED, 409)
    await log_action(
        bot,
        guild,
        "settings.clear",
        actor=actor,
        details={"key": key, "via": via},
    )
    return Outcome(True, CLEARED.format(key=key), value=True)


def command_line(command: Any, path: str, *, heading: bool = False) -> str:
    shown = f"**{path}**" if heading else path
    suffix = STAFF_SUFFIX if is_staff_command(command) else ""
    return f"{shown} — {command.description}{suffix}"


def subcommand_lines(command: Any, path: str) -> list[str]:
    """One line per runnable command, walking groups and their subgroups."""
    children = sorted(getattr(command, "commands", ()) or (), key=lambda child: child.name)
    if not children:
        return [command_line(command, path)]
    return [line for child in children for line in subcommand_lines(child, f"{path} {child.name}")]


def help_lines(entries: Any, wanted: str = "") -> list[str]:
    """A bold heading per top-level command, then the commands under it, filtered and sorted."""
    needle = wanted.strip().lower()
    found: list[str] = []
    for command in sorted(entries, key=lambda item: item.name):
        path = f"/{command.name}"
        heading = command_line(command, path, heading=True)
        if not (getattr(command, "commands", ()) or ()):
            if not needle or needle in heading.lower():
                found.append(heading)
            continue
        body = subcommand_lines(command, path)
        if needle:
            kept = [line for line in body if needle in line.lower()]
            if not kept and needle not in heading.lower():
                continue
            body = kept or body
        found.extend([heading, *body])
    return found


def tree_commands(tree: Any, guild: Any = None) -> list[Any]:
    """The global tree plus the guild-synced copies, one entry per name."""
    found: dict[str, Any] = {}
    for command in tree.get_commands():
        found[command.name] = command
    if guild is not None:
        for command in tree.get_commands(guild=guild):
            found[command.name] = command
    return list(found.values())


class Core(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.last_purge_ok_at: Any = None
        self.last_purge_error: Any = None

    async def cog_load(self) -> None:
        self.purge_loop.start()

    async def cog_unload(self) -> None:
        self.purge_loop.cancel()

    @tasks.loop(seconds=PURGE_EVERY_SECONDS)
    async def purge_loop(self) -> None:
        """The first tick is on boot, so a run that died mid-way is cleared before a new one."""
        if not getattr(self.bot.db, "is_connected", False):
            return
        for guild in list(getattr(self.bot, "guilds", ()) or ()):
            gone = await selftest.purge(self.bot, guild)
            if gone:
                log.info("selftest: purged %d message(s) in %s", gone, guild.id)
        self.last_purge_ok_at = discord.utils.utcnow().isoformat()
        self.last_purge_error = None

    @purge_loop.before_loop
    async def _before_purge(self) -> None:
        await self.bot.wait_until_ready()

    @purge_loop.error
    async def _purge_failed(self, exc: BaseException) -> None:
        self.last_purge_error = f"{type(exc).__name__}: {exc}"
        log.warning("selftest: the purge loop stopped — %s", self.last_purge_error, exc_info=exc)

    def loop_health(self, name: str) -> tuple[Any, Any]:
        if name != PURGE_LOOP:
            return (None, None)
        return (self.last_purge_ok_at, self.last_purge_error)

    @app_commands.command(name="ping", description="Check that Black Bloc is alive")
    async def ping(self, interaction: discord.Interaction) -> None:
        latency_ms = round(self.bot.latency * 1000)
        await interaction.response.send_message(
            f"Pong — gateway latency {latency_ms} ms", ephemeral=True
        )

    @app_commands.command(name="about", description="What Black Bloc is")
    async def about(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(
            f"**Black Bloc** v{__version__} — moderation and content bot.", ephemeral=True
        )

    @app_commands.command(name="help", description="List every command Black Bloc can run")
    @app_commands.describe(filter="Only list commands whose name or description contains this")
    async def help_command(
        self, interaction: discord.Interaction, filter: str | None = None
    ) -> None:
        guild = self._help_guild(interaction)
        hidden = hidden_names(self.bot, getattr(guild, "id", None))
        entries = [
            command
            for command in tree_commands(self.bot.tree, guild)
            if command.name not in hidden
        ]
        lines = help_lines(entries, filter or "")
        if not lines:
            await interaction.response.send_message(
                NO_MATCH.format(filter=str(filter)[:80]),
                ephemeral=True,
                allowed_mentions=discord.AllowedMentions.none(),
            )
            return
        if hidden and not (filter or "").strip():
            lines.append(HIDDEN_NOTE.format(count=len(hidden)))
        for index, chunk in enumerate(pages_under_limit([HELP_HEADER, *lines])):
            answer = interaction.followup.send if index else interaction.response.send_message
            await answer(
                chunk, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
            )

    def _help_guild(self, interaction: discord.Interaction) -> Any:
        if interaction.guild is not None:
            return interaction.guild
        dev_guild_id = getattr(getattr(self.bot, "settings", None), "dev_guild_id", None)
        return discord.Object(id=dev_guild_id) if dev_guild_id else None

    @app_commands.command(
        name="settings", description="Read and change Black Bloc's settings for this server"
    )
    @app_commands.default_permissions(STAFF_ONLY)
    async def settings(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await answer(interaction, GUILD_ONLY)
            return
        if not await require_staff(interaction):
            return
        if not await db_up(interaction):
            return
        embed, view = build_root(self.bot, interaction.guild, interaction.user)
        await interaction.response.send_message(
            embed=embed,
            view=view,
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        view.message = await interaction.original_response()


# --- the panel ------------------------------------------------------------------------------------


STYLES = {
    "primary": discord.ButtonStyle.primary,
    "secondary": discord.ButtonStyle.secondary,
    "success": discord.ButtonStyle.success,
    "danger": discord.ButtonStyle.danger,
}

ROLES_CHANNELS_TITLE = "Who counts as staff, and where Black Bloc talks"
LOOKS_TITLE = "How Black Bloc looks"
PANELS_TITLE = "Panels and commands"
LOG_LEVELS_TITLE = "How much reaches the Discord log channel"
GROUP_TITLE = "The {group} settings"
KEY_TITLE = "{key}"

BIO_NOW = "**About Me** — {value}"
STATUS_NOW = "**status** — {value}"
SKIN_TONE_NOW = "**skin tone** — {value}"
STATUS_LOOP_OK = "**the status loop last succeeded** — {when}"
STATUS_LOOP_NEVER = "**the status loop** — it has not succeeded yet in this process"
STATUS_LOOP_ERROR = "**its last error** — {error}"
HOSTING_NOW = "**the hosting bill** — {value} US dollars a month"
OPERATOR_LOG_NOW = "**an operator-token read leaves a log line** — {value}"
OPERATOR_LOG_IS_FOR_A_LEAD = (
    "Whether an operator-token read leaves a log line is changed by somebody with Manage "
    "Server, so that button is not drawn for you."
)
OPERATOR_LOG_REFUSED = (
    "Nothing was changed: whether an operator-token read leaves a log line is changed by "
    "somebody with Manage Server, and this panel no longer has it. Ask a Lead if it needs to "
    "change; press **Refresh** and the card will say the same."
)
PANEL_MINUTES_INTRO = (
    "**How long a panel stays open** — {count} panels have their own number, and the picker "
    "below opens any of them."
)
LEVELS_INTRO = (
    "Every feature keeps every line on the dashboard's Logs page. This decides how much of it "
    "is repeated in the Discord log channel as well."
)
GROUP_INTRO = "{count} setting(s) in **{group}**. Pick one to see what it is and change it."
NOT_A_NUMBER = (
    "**{label}** takes a whole number and you typed `{given}`, so nothing was changed. Open it "
    "again and type digits only."
)

NUMBER_LABEL = "A whole number"
NUMBER_BOTH = "A whole number from {low} to {high}"
NUMBER_MAX = "A whole number, no more than {high}"
NUMBER_MIN = "A whole number, at least {low}"
TEXT_LABEL = "The words"
COLOUR_LABEL = "A hex colour like #4eefff"
MODAL_TITLE_MAX = 45
LABEL_MAX = 45
BUTTON_LABEL_MAX = 80
OPTION_LABEL_MAX = 100
TEXT_FIELD_MAX = 4000
COLOUR_FIELD_MAX = 7
NUMBER_FIELD_MAX = 10

MODAL_LABELS = {
    sp.NUMBER_MODAL: NUMBER_LABEL,
    sp.TEXT_MODAL: TEXT_LABEL,
    sp.COLOUR_MODAL: COLOUR_LABEL,
}


class SettingsPanel(Panel):
    def __init__(self, minutes: int, *, back: Any = None) -> None:
        super().__init__(minutes, footer=sp.PANEL_TIMEOUT_FOOTER)
        self.back = back or render_root
        self.rerender = render_root


def minutes_for(bot: Any, guild_id: int) -> int:
    return sp.panel_minutes(bot.store, guild_id)


def site_url(bot: Any) -> str | None:
    return sp.site_page_url(getattr(getattr(bot, "settings", None), "origin", ""))


def manages_guild(member: Any) -> bool:
    """Checklist 21 — the COMPUTED permission, never an explicit overwrite."""
    perms = getattr(member, "guild_permissions", None)
    return bool(getattr(perms, "manage_guild", False))


def may_edit_core(bot: Any, guild_id: int, member: Any) -> bool:
    return sp.may_edit_core_keys(bot.store, guild_id, manage_guild=manages_guild(member))


def presence_cog(bot: Any) -> Any:
    getter = getattr(bot, "get_cog", None)
    return getter(PRESENCE_COG) if getter is not None else None


def number_label(key: str) -> str:
    """Checklist 22 — the bound that vanished with `Range` is rebuilt on the field itself."""
    low, high = KEY_MIN.get(key), KEY_MAX.get(key)
    if low is not None and high is not None:
        return NUMBER_BOTH.format(low=low, high=high)
    if high is not None:
        return NUMBER_MAX.format(high=high)
    if low is not None:
        return NUMBER_MIN.format(low=low)
    return NUMBER_LABEL


def field_max(key: str, editor: str) -> int:
    if editor == sp.TEXT_MODAL:
        return TEXT_FIELD_MAX
    if editor == sp.COLOUR_MODAL:
        return COLOUR_FIELD_MAX
    limit = KEY_MAX.get(key)
    return len(str(limit)) if limit is not None else NUMBER_FIELD_MAX


def choice_options(key: str, picked: Any) -> list[discord.SelectOption]:
    chosen = picked if isinstance(picked, list | tuple) else [picked]
    return [
        discord.SelectOption(
            label=str(one)[:OPTION_LABEL_MAX], value=str(one), default=one in chosen
        )
        for one in KEY_CHOICES.get(key, ())[: sp.SELECT_LIMIT]
    ]


# --- the cards ------------------------------------------------------------------------------------


def build_root(bot: Any, guild: Any, member: Any) -> tuple[discord.Embed, SettingsPanel]:
    hidden = hidden_names(bot, guild.id)
    core_ok = may_edit_core(bot, guild.id, member)
    lines = sp.root_lines(bot, guild, hidden)
    if not core_ok:
        lines.append(sp.CORE_KEYS_ARE_FOR_A_LEAD)
    back_on = sp.back_on_options(bot, guild.id)
    url = site_url(bot)
    view = SettingsPanel(minutes_for(bot, guild.id))
    for move in sp.root_buttons(
        may_turn_back_on=bool(back_on), may_edit_core=core_ok, has_site=url is not None
    ):
        if move.action == sp.BACK_ON:
            view.add_item(BackOnPick(move, back_on))
        elif move.action == sp.GROUP:
            view.add_item(GroupPick(move))
        elif move.kind == sp.LINK:
            view.add_item(SiteButton(move, url or ""))
        else:
            view.add_item(MoveButton(move))
    view.rerender = render_root
    return (discord.Embed(title=sp.PANEL_TITLE, description=clamped(lines)), view)


def build_roles_channels(bot: Any, guild: Any) -> tuple[discord.Embed, SettingsPanel]:
    store = bot.store
    lines: list[str] = []
    for key in sp.CORE_CHANNEL_KEYS:
        lines.append(
            f"**{sp.KEY_PURPOSE[key]}** — {display_value(key, store.get(guild.id, key))}"
        )
        lines.append(KEY_HELP.get(key, ""))
    view = SettingsPanel(minutes_for(bot, guild.id))
    for move in sp.roles_channels_buttons():
        if move.kind == sp.SELECT:
            key = move.action.split(":", 1)[1]
            view.add_item(CoreChannelPick(move, key, store.get(guild.id, key)))
        else:
            view.add_item(MoveButton(move))
    view.rerender = render_roles_channels
    return (discord.Embed(title=ROLES_CHANNELS_TITLE, description=clamped(lines)), view)


def looks_lines(bot: Any, guild: Any) -> list[str]:
    store = bot.store
    lines = [
        BIO_NOW.format(value=display_value(sp.BIO_KEY, store.get(guild.id, sp.BIO_KEY))),
        STATUS_NOW.format(value=display_value(sp.STATUS_KEY, store.get(guild.id, sp.STATUS_KEY))),
        SKIN_TONE_NOW.format(value=store.get(guild.id, sp.SKIN_TONE_KEY)),
    ]
    cog = presence_cog(bot)
    if cog is None:
        lines.append(sp.PRESENCE_NOT_RUNNING)
        return lines
    last_ok, last_error = cog.loop_health("status")
    lines.append(STATUS_LOOP_OK.format(when=last_ok) if last_ok else STATUS_LOOP_NEVER)
    if last_error:
        lines.append(STATUS_LOOP_ERROR.format(error=str(last_error)[:200]))
    return lines


def build_looks(bot: Any, guild: Any) -> tuple[discord.Embed, SettingsPanel]:
    view = SettingsPanel(minutes_for(bot, guild.id))
    tone = bot.store.get(guild.id, sp.SKIN_TONE_KEY)
    for move in sp.looks_buttons(presence_loaded=presence_cog(bot) is not None):
        if move.action == sp.SKIN_TONE:
            view.add_item(OneOfPick(move, sp.SKIN_TONE_KEY, tone))
        else:
            view.add_item(MoveButton(move))
    view.rerender = render_looks
    return (
        discord.Embed(title=LOOKS_TITLE, description=clamped(looks_lines(bot, guild))),
        view,
    )


def panels_lines(bot: Any, guild: Any, member: Any) -> list[str]:
    store = bot.store
    hiding = store.get(guild.id, sp.HIDE_COMMANDS_WHEN_OFF)
    lines = [
        sp.HIDE_ON_STATE if hiding else sp.HIDE_OFF_STATE,
        PANEL_MINUTES_INTRO.format(count=len(sp.panel_minutes_keys())),
        HOSTING_NOW.format(value=store.get(guild.id, sp.HOSTING_KEY)),
    ]
    if manages_guild(member):
        lines.append(
            OPERATOR_LOG_NOW.format(value=store.get(guild.id, sp.OPERATOR_READ_LOG_KEY))
        )
    else:
        lines.append(OPERATOR_LOG_IS_FOR_A_LEAD)
    return lines


def build_panels(bot: Any, guild: Any, member: Any) -> tuple[discord.Embed, SettingsPanel]:
    view = SettingsPanel(minutes_for(bot, guild.id))
    for move in sp.panels_commands_buttons(
        bot.store, guild.id, manage_guild=manages_guild(member)
    ):
        if move.action == sp.PANEL_MINUTES_PICK:
            view.add_item(KeyPick(move, sp.panel_minutes_options(bot.store, guild.id)))
        else:
            view.add_item(MoveButton(move))
    view.rerender = render_panels
    return (
        discord.Embed(title=PANELS_TITLE, description=clamped(panels_lines(bot, guild, member))),
        view,
    )


async def selftest_card_state(bot: Any, guild: Any) -> dict[str, Any]:
    """One read of everything the self-test card says, so the embed and its buttons agree."""
    runs = await selftest.recent_runs(bot.db, guild.id, 1)
    last = runs[0] if runs else None
    waiting = await selftest.waiting_messages(bot.db, guild.id)
    return {
        "last": last,
        "failures": await selftest.failures_of(bot.db, guild.id, last["id"]) if last else [],
        "waiting": len(waiting),
        "running": selftest.running(bot, guild.id),
    }


async def build_selftest(bot: Any, guild: Any) -> tuple[discord.Embed, SettingsPanel]:
    state = await selftest_card_state(bot, guild)
    view = SettingsPanel(minutes_for(bot, guild.id))
    for move in sp.selftest_buttons(
        running=state["running"] is not None, has_messages=state["waiting"] > 0
    ):
        view.add_item(MoveButton(move))
    view.rerender = render_selftest
    lines = sp.selftest_lines(
        bot.store,
        guild.id,
        last=state["last"],
        failures=state["failures"],
        waiting=state["waiting"],
        running=sp.SELFTEST_IS_RUNNING if state["running"] is not None else "",
    )
    return (discord.Embed(title=sp.SELFTEST_TITLE, description=clamped(lines)), view)


def build_log_levels(bot: Any, guild: Any) -> tuple[discord.Embed, SettingsPanel]:
    view = SettingsPanel(minutes_for(bot, guild.id))
    for move in sp.log_levels_buttons():
        if move.action == sp.LEVEL_PICK:
            view.add_item(LevelKeyPick(move, sp.log_level_options(bot.store, guild.id)))
        else:
            view.add_item(MoveButton(move))
    view.rerender = render_log_levels
    return (discord.Embed(title=LOG_LEVELS_TITLE, description=clamped([LEVELS_INTRO])), view)


def build_level(bot: Any, guild: Any, key: str) -> tuple[discord.Embed, SettingsPanel]:
    store = bot.store
    view = SettingsPanel(minutes_for(bot, guild.id), back=render_log_levels)
    for move in sp.level_buttons(store.get(guild.id, key)):
        view.add_item(MoveButton(move, key=key))
    view.rerender = partial(render_level, key=key)
    return (
        discord.Embed(
            title=KEY_TITLE.format(key=key)[:MODAL_TITLE_MAX],
            description=clamped(sp.key_card_lines(store, guild.id, key)),
        ),
        view,
    )


def build_group(bot: Any, guild: Any, group: str, needle: str = "") -> tuple[Any, SettingsPanel]:
    store = bot.store
    keys = sp.keys_in(group)
    lines = [GROUP_INTRO.format(count=len(keys), group=group), ""]
    lines += [
        sp.KEY_LINE.format(key=key, value=display_value(key, store.get(guild.id, key)))
        for key in keys
    ]
    options = sp.editable_options(group, needle)
    view = SettingsPanel(minutes_for(bot, guild.id))
    for move in sp.group_buttons(group):
        if move.action == sp.KEY_PICK:
            view.add_item(
                KeyPick(
                    move,
                    tuple((key, key) for key in options.keys),
                    placeholder=options.placeholder,
                    group=group,
                )
            )
        else:
            view.add_item(MoveButton(move, group=group))
    view.rerender = partial(render_group, group=group, needle=needle)
    return (
        discord.Embed(title=GROUP_TITLE.format(group=group), description=clamped(lines)),
        view,
    )


def build_key(
    bot: Any, guild: Any, key: str, *, confirming: bool = False
) -> tuple[discord.Embed, SettingsPanel]:
    store = bot.store
    group = namespace_of(key)
    stored = store.is_stored(guild.id, key)
    lines = sp.key_card_lines(store, guild.id, key)
    if stored:
        lines.append(sp.default_sentence(store, guild.id, key))
    if confirming:
        lines = [sp.CONFIRM_TITLE, *sp.confirm_lines(store, guild.id, key)] + lines
    view = SettingsPanel(minutes_for(bot, guild.id), back=partial(render_group, group=group))
    value = store.get(guild.id, key)
    for move in sp.key_card_buttons(store, guild.id, key, stored=stored, confirming=confirming):
        view.add_item(editor_control(move, key, value) or MoveButton(move, key=key, group=group))
    view.rerender = partial(render_key, key=key)
    return (
        discord.Embed(
            title=KEY_TITLE.format(key=key)[:MODAL_TITLE_MAX], description=clamped(lines)
        ),
        view,
    )


def editor_control(move: Any, key: str, value: Any) -> Any:
    """One control per §C row; a picker becomes a select, everything typed becomes a modal."""
    editor = move.action.partition(":")[2] if move.action.startswith(f"{sp.EDIT}:") else ""
    if editor == sp.CHANNEL_PICKER:
        return ChannelOne(move, key, value)
    if editor == sp.ROLE_PICKER:
        return RoleOne(move, key, value)
    if editor == sp.CHANNEL_LIST:
        return ChannelMany(move, key, value)
    if editor == sp.ROLE_LIST:
        return RoleMany(move, key, value)
    if editor == sp.ONE_OF:
        return OneOfPick(move, key, value)
    if editor == sp.ANY_OF:
        return AnyOfPick(move, key, value)
    return None


# --- the renders ----------------------------------------------------------------------------------


async def show(interaction: discord.Interaction, built: Any, previous: Any) -> None:
    embed, view = built
    retire(previous)
    view.message = await interaction.edit_original_response(
        embed=embed, view=view, allowed_mentions=discord.AllowedMentions.none()
    )


async def render_root(interaction: discord.Interaction, previous: Any = None) -> None:
    await show(
        interaction,
        build_root(interaction.client, interaction.guild, interaction.user),
        previous,
    )


async def render_roles_channels(interaction: discord.Interaction, previous: Any = None) -> None:
    await show(interaction, build_roles_channels(interaction.client, interaction.guild), previous)


async def render_looks(interaction: discord.Interaction, previous: Any = None) -> None:
    await show(interaction, build_looks(interaction.client, interaction.guild), previous)


async def render_panels(interaction: discord.Interaction, previous: Any = None) -> None:
    await show(
        interaction,
        build_panels(interaction.client, interaction.guild, interaction.user),
        previous,
    )


async def render_selftest(interaction: discord.Interaction, previous: Any = None) -> None:
    await show(
        interaction, await build_selftest(interaction.client, interaction.guild), previous
    )


async def render_log_levels(interaction: discord.Interaction, previous: Any = None) -> None:
    await show(interaction, build_log_levels(interaction.client, interaction.guild), previous)


async def render_level(
    interaction: discord.Interaction, previous: Any = None, *, key: str = ""
) -> None:
    await show(interaction, build_level(interaction.client, interaction.guild, key), previous)


async def render_group(
    interaction: discord.Interaction, previous: Any = None, *, group: str = "", needle: str = ""
) -> None:
    await show(
        interaction, build_group(interaction.client, interaction.guild, group, needle), previous
    )


async def render_key(
    interaction: discord.Interaction,
    previous: Any = None,
    *,
    key: str = "",
    confirming: bool = False,
) -> None:
    await show(
        interaction,
        build_key(interaction.client, interaction.guild, key, confirming=confirming),
        previous,
    )


# --- the moves ------------------------------------------------------------------------------------


async def opened(interaction: discord.Interaction) -> bool:
    """Staff are re-asked before every move, the reads included, and then the database is."""
    if not await still_staff(interaction):
        return False
    await interaction.response.defer()
    return await db_ready(interaction)


async def core_keys_allowed(interaction: discord.Interaction) -> bool:
    """The gate can close while the card is open, so the move re-asks instead of trusting it."""
    if may_edit_core(interaction.client, interaction.guild.id, interaction.user):
        return True
    await answer(interaction, sp.CORE_KEYS_ARE_FOR_A_LEAD)
    return False


async def operator_log_allowed(interaction: discord.Interaction) -> bool:
    """Drawn only for Manage Server, and re-asked here — a Lead can lose it mid-panel."""
    if manages_guild(interaction.user):
        return True
    await answer(interaction, OPERATOR_LOG_REFUSED)
    return False


async def go_back(interaction: discord.Interaction, view: Any) -> None:
    if not await opened(interaction):
        return
    await view.back(interaction, view)


async def again(interaction: discord.Interaction, view: Any) -> None:
    await view.rerender(interaction, view)


async def open_card(interaction: discord.Interaction, view: Any, render: Any) -> None:
    if not await opened(interaction):
        return
    await render(interaction, view)


async def run_set(
    interaction: discord.Interaction, view: Any, key: str, value: Any, *, said: str = ""
) -> None:
    """A refused value is answered and nothing is re-rendered, so it cannot read as a save."""
    if not await opened(interaction):
        return
    outcome = await set_key(interaction.client, interaction.guild, key, value, interaction.user)
    if not outcome.ok:
        await answer(interaction, outcome.message)
        return
    await again(interaction, view)
    await answer(interaction, said or outcome.message)


async def run_gated_set(
    interaction: discord.Interaction, view: Any, key: str, value: Any, gate: Any
) -> None:
    """A control drawn for one permission is re-asked for it here, never trusted to the draw."""
    if not await opened(interaction):
        return
    if not await gate(interaction):
        return
    outcome = await set_key(interaction.client, interaction.guild, key, value, interaction.user)
    if not outcome.ok:
        await answer(interaction, outcome.message)
        return
    await again(interaction, view)
    await answer(interaction, outcome.message)


async def run_core_set(
    interaction: discord.Interaction, view: Any, key: str, value: Any
) -> None:
    await run_gated_set(interaction, view, key, value, core_keys_allowed)


async def run_operator_toggle(interaction: discord.Interaction, view: Any) -> None:
    key = sp.OPERATOR_READ_LOG_KEY
    now = interaction.client.store.get(interaction.guild.id, key)
    await run_gated_set(interaction, view, key, not now, operator_log_allowed)


async def run_toggle(interaction: discord.Interaction, view: Any, key: str, said: str = "") -> None:
    store = interaction.client.store
    now = store.get(interaction.guild.id, key)
    await run_set(interaction, view, key, not now, said=said)


async def run_hide_toggle(interaction: discord.Interaction, view: Any) -> None:
    store = interaction.client.store
    wanted = not store.get(interaction.guild.id, sp.HIDE_COMMANDS_WHEN_OFF)
    said = sp.HIDE_CHANGED.format(state=sp.HIDE_ON_STATE if wanted else sp.HIDE_OFF_STATE)
    await run_set(interaction, view, sp.HIDE_COMMANDS_WHEN_OFF, wanted, said=said)


async def run_back_on(interaction: discord.Interaction, view: Any, key: str) -> None:
    await run_set(interaction, view, key, sp.BACK_ON_VALUE)


async def run_reset(interaction: discord.Interaction, view: Any, key: str) -> None:
    if sp.needs_confirm(key):
        if not await opened(interaction):
            return
        await render_key(interaction, view, key=key, confirming=True)
        return
    await run_clear(interaction, view, key)


async def run_clear(interaction: discord.Interaction, view: Any, key: str) -> None:
    if not await opened(interaction):
        return
    outcome = await clear_key(interaction.client, interaction.guild, key, interaction.user)
    if not outcome.ok:
        await answer(interaction, outcome.message)
        return
    await render_key(interaction, view, key=key)
    await answer(interaction, outcome.message)


async def run_typed(interaction: discord.Interaction, view: Any, key: str, raw: str) -> None:
    """A modal has no `Range`, so the bound is rebuilt where the value now enters."""
    if not await opened(interaction):
        return
    try:
        value = parse_value(key, raw)
    except SettingError as exc:
        await answer(interaction, str(exc))
        return
    outcome = await set_key(interaction.client, interaction.guild, key, value, interaction.user)
    if not outcome.ok:
        await answer(interaction, outcome.message)
        return
    await render_key(interaction, view, key=key)
    said = outcome.message
    if key == sp.PANEL_MINUTES_KEY:
        said = f"{said} {sp.PANEL_MINUTES_NEXT_TIME}"
    await answer(interaction, said)


async def run_find(interaction: discord.Interaction, view: Any, group: str, needle: str) -> None:
    if not await opened(interaction):
        return
    found = sp.editable_options(group, needle)
    if not found.keys:
        await render_group(interaction, view, group=group)
        await answer(interaction, sp.NOTHING_MATCHES.format(group=group, needle=needle[:60]))
        return
    await render_group(interaction, view, group=group, needle=needle)


async def run_selftest(interaction: discord.Interaction, view: Any) -> None:
    if not await opened(interaction):
        return
    bot, guild = interaction.client, interaction.guild
    try:
        one = await selftest.run(bot, guild, actor=interaction.user, via=VIA_DISCORD)
    except selftest.SelfTestBusy as exc:
        await answer(interaction, str(exc))
        return
    said = sp.SELFTEST_DONE.format(
        ok=one.ok,
        failed=one.failed,
        posted=one.posted,
        minutes=selftest.purge_minutes(bot, guild.id),
    )
    body = [said] + (
        [sp.SELFTEST_FAILURE.format(name=row.name, detail=row.detail) for row in one.failures]
        or [sp.SELFTEST_ALL_WELL]
    )
    await render_selftest(interaction, view)
    await answer(interaction, clamped(body))


async def run_selftest_purge(interaction: discord.Interaction, view: Any) -> None:
    if not await opened(interaction):
        return
    gone = await selftest.purge(
        interaction.client, interaction.guild, due_only=False, via=VIA_DISCORD
    )
    await render_selftest(interaction, view)
    await answer(
        interaction,
        sp.SELFTEST_PURGE_DONE.format(count=gone) if gone else sp.SELFTEST_NOTHING_TO_PURGE,
    )


async def run_reapply(interaction: discord.Interaction, view: Any) -> None:
    if not await opened(interaction):
        return
    said = await reapply_presence(interaction.client)
    await render_looks(interaction, view)
    await answer(interaction, said or sp.PRESENCE_NOT_RUNNING)


async def open_modal(interaction: discord.Interaction, modal: Any) -> None:
    """A modal cannot be deferred first, so the gates are asked before it is sent."""
    if not await still_staff(interaction):
        return
    if not await db_up(interaction):
        return
    await interaction.response.send_modal(modal)


# --- the controls ---------------------------------------------------------------------------------


class MoveButton(discord.ui.Button):
    def __init__(self, move: Any, *, key: str = "", group: str = "") -> None:
        super().__init__(
            label=(move.label or " ")[:BUTTON_LABEL_MAX], style=STYLES[move.style], row=move.row
        )
        self.move = move
        self.key = key
        self.group = group

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        action = self.move.action
        if action == sp.LOGS:
            await send_logs(interaction, CORE)
            return
        if action == sp.SELFTEST_LOGS:
            await send_logs(interaction, SELFTEST)
            return
        if action == sp.SELFTEST_RUN:
            await run_selftest(interaction, view)
            return
        if action == sp.SELFTEST_PURGE:
            await run_selftest_purge(interaction, view)
            return
        if action == sp.REFRESH:
            await open_card(interaction, view, render_root)
            return
        if action == sp.BACK:
            await go_back(interaction, view)
            return
        if action in OPENS:
            await open_card(interaction, view, OPENS[action])
            return
        if action.startswith(f"{sp.LEVEL_SET}:"):
            await run_set(interaction, view, self.key, action.partition(":")[2])
            return
        if action == sp.HIDE_TOGGLE:
            await run_hide_toggle(interaction, view)
            return
        if action == sp.OPERATOR_TOGGLE:
            await run_operator_toggle(interaction, view)
            return
        if action == f"{sp.EDIT}:{sp.TOGGLE}":
            await run_toggle(interaction, view, self.key)
            return
        if action == sp.CLEAR_LIST:
            await run_set(interaction, view, self.key, [])
            return
        if action == sp.RESET:
            await run_reset(interaction, view, self.key)
            return
        if action == sp.CONFIRM_RESET:
            await run_clear(interaction, view, self.key)
            return
        if action == sp.CANCEL:
            await open_card(interaction, view, partial(render_key, key=self.key))
            return
        if action == sp.REAPPLY:
            await run_reapply(interaction, view)
            return
        await self.send_its_modal(interaction, view)

    async def send_its_modal(self, interaction: discord.Interaction, view: Any) -> None:
        action = self.move.action
        if action == sp.FIND:
            await open_modal(interaction, FindModal(self.group, view))
            return
        key = MODAL_KEYS.get(action, self.key)
        current = interaction.client.store.get(interaction.guild.id, key)
        await open_modal(interaction, KeyModal(key, sp.control_for(key), current, view))


class SiteButton(discord.ui.Button):
    def __init__(self, move: Any, url: str) -> None:
        super().__init__(
            label=move.label[:BUTTON_LABEL_MAX],
            style=discord.ButtonStyle.link,
            url=url,
            row=move.row,
        )


class BackOnPick(discord.ui.Select):
    def __init__(self, move: Any, options: Any) -> None:
        super().__init__(
            placeholder=move.label,
            options=[
                discord.SelectOption(label=one.label[:OPTION_LABEL_MAX], value=one.key)
                for one in options[: sp.SELECT_LIMIT]
            ],
            min_values=1,
            max_values=1,
            row=move.row,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await run_back_on(interaction, self.view, self.values[0])


class GroupPick(discord.ui.Select):
    def __init__(self, move: Any) -> None:
        super().__init__(
            placeholder=move.label,
            options=[
                discord.SelectOption(label=group[:OPTION_LABEL_MAX], value=group)
                for group in sp.groups()[: sp.SELECT_LIMIT]
            ],
            min_values=1,
            max_values=1,
            row=move.row,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await open_card(
            interaction, self.view, partial(render_group, group=self.values[0])
        )


class KeyPick(discord.ui.Select):
    """One picker for every list of keys — the group card's, and the panel-minutes family's."""

    def __init__(
        self, move: Any, options: Any, *, placeholder: str = "", group: str = ""
    ) -> None:
        super().__init__(
            placeholder=placeholder or move.label,
            options=[
                discord.SelectOption(label=label[:OPTION_LABEL_MAX], value=key)
                for key, label in tuple(options)[: sp.SELECT_LIMIT]
            ],
            min_values=1,
            max_values=1,
            row=move.row,
        )
        self.group = group

    async def callback(self, interaction: discord.Interaction) -> None:
        await open_card(interaction, self.view, partial(render_key, key=self.values[0]))


class LevelKeyPick(KeyPick):
    async def callback(self, interaction: discord.Interaction) -> None:
        await open_card(interaction, self.view, partial(render_level, key=self.values[0]))


class CoreChannelPick(discord.ui.ChannelSelect):
    def __init__(self, move: Any, key: str, current: Any) -> None:
        super().__init__(
            placeholder=move.label[:OPTION_LABEL_MAX],
            channel_types=[discord.ChannelType.text],
            min_values=1,
            max_values=1,
            default_values=[discord.Object(id=current)] if current else [],
            row=move.row,
        )
        self.key = key

    async def callback(self, interaction: discord.Interaction) -> None:
        await run_core_set(interaction, self.view, self.key, self.values[0].id)


class ChannelOne(discord.ui.ChannelSelect):
    def __init__(self, move: Any, key: str, current: Any) -> None:
        super().__init__(
            placeholder=move.label,
            channel_types=[discord.ChannelType.text],
            min_values=1,
            max_values=1,
            default_values=[discord.Object(id=current)] if current else [],
            row=move.row,
        )
        self.key = key

    async def callback(self, interaction: discord.Interaction) -> None:
        await run_set(interaction, self.view, self.key, self.values[0].id)


class RoleOne(discord.ui.RoleSelect):
    def __init__(self, move: Any, key: str, current: Any) -> None:
        super().__init__(
            placeholder=move.label,
            min_values=1,
            max_values=1,
            default_values=[discord.Object(id=current)] if current else [],
            row=move.row,
        )
        self.key = key

    async def callback(self, interaction: discord.Interaction) -> None:
        await run_set(interaction, self.view, self.key, self.values[0].id)


class ChannelMany(discord.ui.ChannelSelect):
    """The selection IS the list, so adding and removing are one move (checklist 26)."""

    def __init__(self, move: Any, key: str, current: Any) -> None:
        stored = list(current or ())[: sp.LIST_EDIT_MAX]
        super().__init__(
            placeholder=move.label,
            channel_types=[discord.ChannelType.text],
            min_values=0,
            max_values=sp.LIST_EDIT_MAX,
            default_values=[discord.Object(id=one) for one in stored],
            row=move.row,
        )
        self.key = key

    async def callback(self, interaction: discord.Interaction) -> None:
        await run_set(interaction, self.view, self.key, [one.id for one in self.values])


class RoleMany(discord.ui.RoleSelect):
    def __init__(self, move: Any, key: str, current: Any) -> None:
        stored = list(current or ())[: sp.LIST_EDIT_MAX]
        super().__init__(
            placeholder=move.label,
            min_values=0,
            max_values=sp.LIST_EDIT_MAX,
            default_values=[discord.Object(id=one) for one in stored],
            row=move.row,
        )
        self.key = key

    async def callback(self, interaction: discord.Interaction) -> None:
        await run_set(interaction, self.view, self.key, [one.id for one in self.values])


class OneOfPick(discord.ui.Select):
    def __init__(self, move: Any, key: str, current: Any) -> None:
        super().__init__(
            placeholder=move.label,
            options=choice_options(key, current),
            min_values=1,
            max_values=1,
            row=move.row,
        )
        self.key = key

    async def callback(self, interaction: discord.Interaction) -> None:
        await run_set(interaction, self.view, self.key, self.values[0])


class AnyOfPick(discord.ui.Select):
    def __init__(self, move: Any, key: str, current: Any) -> None:
        options = choice_options(key, current)
        super().__init__(
            placeholder=move.label,
            options=options,
            min_values=0,
            max_values=max(1, len(options)),
            row=move.row,
        )
        self.key = key

    async def callback(self, interaction: discord.Interaction) -> None:
        await run_set(interaction, self.view, self.key, list(self.values))


# --- the modals -----------------------------------------------------------------------------------


class KeyModal(AnswersErrors, discord.ui.Modal):
    """One submit path for every typed value — a number, some words or a colour."""

    field = discord.ui.TextInput(label=TEXT_LABEL)

    def __init__(self, key: str, editor: str, current: Any, previous: Any = None) -> None:
        super().__init__(title=KEY_TITLE.format(key=key)[:MODAL_TITLE_MAX])
        self.key = key
        self.previous = previous
        label = (
            number_label(key)
            if editor == sp.NUMBER_MODAL
            else MODAL_LABELS.get(editor, TEXT_LABEL)
        )
        self.field.label = label[:LABEL_MAX]
        self.field.max_length = field_max(key, editor)
        self.field.style = (
            discord.TextStyle.paragraph
            if editor == sp.TEXT_MODAL
            else discord.TextStyle.short
        )
        self.field.default = "" if current is None else str(current)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await run_typed(interaction, self.previous, self.key, str(self.field))


class FindModal(AnswersErrors, discord.ui.Modal):
    needle = discord.ui.TextInput(label=sp.FIND_LABEL, required=False, max_length=60)

    def __init__(self, group: str, previous: Any = None) -> None:
        super().__init__(title=sp.FIND_TITLE[:MODAL_TITLE_MAX])
        self.group = group
        self.previous = previous

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await run_find(interaction, self.previous, self.group, str(self.needle).strip())


OPENS = {
    sp.ROLES_CHANNELS: render_roles_channels,
    sp.LOOKS: render_looks,
    sp.PANELS: render_panels,
    sp.LOG_LEVELS: render_log_levels,
    sp.SELFTEST: render_selftest,
}
MODAL_KEYS = {
    sp.BIO: sp.BIO_KEY,
    sp.STATUS: sp.STATUS_KEY,
    sp.HOSTING: sp.HOSTING_KEY,
}


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Core(bot))
