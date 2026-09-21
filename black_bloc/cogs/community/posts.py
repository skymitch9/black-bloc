from __future__ import annotations

import logging
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands, tasks

from ...actionlog import log_action, send_logs
from ...command_errors import AnswersErrors
from ...command_visibility import STAFF_ONLY
from ...logkinds import VIA_BOOT
from ...loops import wait_ready
from ...panels import (
    KEEP_IT,
    Panel,
    answer,
    clamped,
    confirm,
    confirm_items,
    opened,
    retire,
    still_staff,
)
from ...posts import (
    CAPS,
    DO_NOT_PIN_IT,
    EMBED,
    MODE_SHADOW_SAID,
    MODES,
    NO_SUCH_POST,
    NO_SUCH_VERSION,
    PANEL_EMPTY,
    PANEL_INTRO,
    PANEL_TIMEOUT_FOOTER,
    PANEL_TITLE,
    PIN_IT,
    PLAIN,
    POSTS_OFF,
    SITE_BUTTON,
    STYLES,
    TAKE_IT_DOWN,
    TITLE_MAX,
    USE_THIS_VERSION,
    VERSIONS,
    VERSIONS_EMPTY,
    VERSIONS_INTRO,
    VERSIONS_SELECT_CAP,
    VERSIONS_TITLE,
    VIEW_IT,
    cap_for,
    count_posts,
    get_post,
    get_version,
    in_shadow,
    is_posted,
    is_seeded,
    is_shipped_version,
    list_posts,
    list_versions,
    make_post,
    mode_of,
    move_label,
    panel_minutes,
    posts_are_off,
    preview_of,
    publish_post,
    reconcile_posts,
    refresh_seeds,
    remove_post,
    render_message,
    restore_version,
    row_value,
    save_post,
    seed_posts,
    set_mode,
    shadow_channel_id,
    shadow_words,
    site_page_url,
    status_words,
    summary_chars,
    summary_of,
    take_down_post,
    version_line,
    where_words,
)
from ...settings_store import DB_UNAVAILABLE, GUILD_ONLY, require_staff

log = logging.getLogger(__name__)

COG_NAME = "Posts"
LOOP_NAME = "reconcile"
RECONCILE_MINUTES = 5
BODY_BOX_MAX = 4000
SELECT_CAP = 25
MODAL_TITLE = "Edit this post"
NEW_MODAL_TITLE = "A new post"
PICK_A_POST = "A post…"
NEW_POST = "New post…"
PICK_A_CHANNEL = "Channel…"
PICK_A_STYLE = "Style…"
DELETE_THIS_POST = "Delete this post"
DELETE_YES = "Yes, delete it"
USE_IT_YES = "Yes, use version {n}"
PICK_A_VERSION = "A version…"
VERSION_OPTION = "{line}"
VERSION_SUMMARY = "{summary}"
VERSION_DRAWER_TITLE = "Version {n} of {title}"
NOTHING_IN_IT = "Version {n} has nothing written in it — it is an empty message."
MODE_PICK = "Posts are: off / shadow / on"
MODE_OPTION = "Posts are: {mode}"
BACK = "Back"
LOGS = "Logs"
STYLE_LABELS: dict[str, str] = {
    PLAIN: f"Plain message — {CAPS[PLAIN]} characters, headers render",
    EMBED: f"Embed — {CAPS[EMBED]} characters, no headers",
}
NOT_POSTED_YET = "Nothing is in Discord for this one yet."
USE_IT_QUESTION = (
    "The post goes back to what version {n} said. What it says now is kept as a new version, so "
    "nothing is lost — and nothing reaches Discord until somebody presses Post it."
)
DELETE_QUESTION = "Every word goes with it. Nothing puts it back."


def line_for(guild: Any, row: Any) -> str:
    where = where_words(guild, row_value(row, "channel_id"))
    marks = " · ".join(status_words(row))
    return f"**{row['title']}** · {where} · {marks}"


def option_label(guild: Any, row: Any) -> str:
    marks = ", ".join(status_words(row))
    return f"{row['title']} · {marks}"[:100]


async def build_panel(bot: Any, guild: Any, actor: Any) -> tuple[discord.Embed, PostsView]:
    rows = await list_posts(bot.db, guild.id)
    mode = mode_of(bot.store, guild.id)
    lines = [PANEL_INTRO]
    lines.extend(line_for(guild, row) for row in rows)
    if not rows:
        lines.append(PANEL_EMPTY)
    if posts_are_off(bot.store, guild.id):
        lines.append(POSTS_OFF)
    elif in_shadow(bot.store, guild.id):
        lines.append(
            MODE_SHADOW_SAID.format(where=where_words(guild, shadow_channel_id(bot, guild)))
        )
    embed = discord.Embed(title=PANEL_TITLE, description=clamped(lines))
    view = PostsView(panel_minutes(bot.store, guild.id))
    view.add_item(NewPostButton())
    view.add_item(LogsButton())
    page = site_page_url(getattr(bot.settings, "origin", ""))
    if page:
        view.add_item(
            discord.ui.Button(
                style=discord.ButtonStyle.link, label=SITE_BUTTON, url=page, row=0
            )
        )
    view.add_item(ModePick(mode))
    if rows:
        view.add_item(PostPick(guild, rows))
    return embed, view


def build_card(bot: Any, guild: Any, row: Any) -> tuple[discord.Embed, PostsView]:
    lines = [line_for(guild, row)]
    if in_shadow(bot.store, guild.id):
        lines.append(shadow_words(bot, guild, row))
    body = preview_of(row)
    lines.append(body or NOT_POSTED_YET)
    embed = discord.Embed(title=row["title"], description=clamped(lines))
    slug = str(row["slug"])
    view = PostsView(panel_minutes(bot.store, guild.id))
    view.add_item(MoveButton(slug, move_label(row)))
    if is_posted(row):
        view.add_item(TakeDownButton(slug))
    view.add_item(EditButton(slug))
    view.add_item(PinButton(slug, bool(row_value(row, "pin"))))
    if not is_seeded(row):
        view.add_item(DeleteButton(slug))
    view.add_item(VersionsButton(slug))
    view.add_item(BackButton())
    view.add_item(ChannelPick(slug))
    view.add_item(StylePick(slug, str(row_value(row, "style", PLAIN))))
    return embed, view


def who_words(guild: Any, user_id: Any) -> str | None:
    if not user_id:
        return None
    member = guild.get_member(int(user_id)) if guild is not None else None
    return getattr(member, "display_name", None) or str(user_id)


async def build_versions(
    bot: Any, guild: Any, row: Any, picked: Any = None
) -> tuple[discord.Embed, PostsView]:
    rows = (await list_versions(bot.db, int(row["id"])))[:VERSIONS_SELECT_CAP]
    top = int(rows[0]["n"]) if rows else None
    shipped = frozenset(int(one["n"]) for one in rows if is_shipped_version(row, one))
    limit = summary_chars(bot.store, guild.id)
    lines = [VERSIONS_INTRO]
    if not rows:
        lines.append(VERSIONS_EMPTY)
    for one in rows:
        lines.append(
            version_line(
                one,
                who=who_words(guild, row_value(one, "saved_by")),
                current=int(one["n"]) == top,
                shipped=is_shipped_version(row, one),
            )
        )
        said = summary_of(one, limit)
        if said:
            lines.append(VERSION_SUMMARY.format(summary=said))
    embed = discord.Embed(
        title=VERSIONS_TITLE.format(title=row["title"]), description=clamped(lines)
    )
    slug = str(row["slug"])
    view = PostsView(panel_minutes(bot.store, guild.id))
    if picked is not None:
        view.add_item(ViewVersionButton(slug, int(picked)))
        if int(picked) != top:
            view.add_item(UseVersionButton(slug, int(picked)))
    view.add_item(CardButton(slug))
    if rows:
        view.add_item(VersionPick(slug, guild, rows, picked, top, shipped))
    return embed, view


async def render_versions(
    interaction: discord.Interaction,
    slug: str,
    picked: Any = None,
    previous: Any = None,
    said: str | None = None,
) -> None:
    bot = interaction.client
    row = await get_post(bot.db, interaction.guild.id, slug)
    if row is None:
        await render_panel(interaction, previous)
    else:
        embed, view = await build_versions(bot, interaction.guild, row, picked)
        retire(previous)
        view.message = await interaction.edit_original_response(
            embed=embed, view=view, allowed_mentions=discord.AllowedMentions.none()
        )
    if said:
        await interaction.followup.send(
            said, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
        )


async def use_version(
    interaction: discord.Interaction, slug: str, n: int, previous: Any = None
) -> None:
    if not await opened(interaction):
        return
    bot = interaction.client
    guild = interaction.guild
    if posts_are_off(bot.store, guild.id):
        await render_card(interaction, slug, previous, POSTS_OFF)
        return
    row = await get_post(bot.db, guild.id, slug)
    if row is None:
        await render_panel(interaction, previous)
        return
    found = await restore_version(bot, guild, row, interaction.user, n)
    await render_card(interaction, slug, previous, found.message)


async def render_panel(interaction: discord.Interaction, previous: Any = None) -> None:
    bot = interaction.client
    embed, view = await build_panel(bot, interaction.guild, interaction.user)
    retire(previous)
    view.message = await interaction.edit_original_response(
        embed=embed, view=view, allowed_mentions=discord.AllowedMentions.none()
    )


async def back_to_panel(interaction: discord.Interaction, previous: Any = None) -> None:
    if not await opened(interaction):
        return
    await render_panel(interaction, previous)


async def render_card(
    interaction: discord.Interaction, slug: str, previous: Any = None, said: str | None = None
) -> None:
    bot = interaction.client
    row = await get_post(bot.db, interaction.guild.id, slug)
    if row is None:
        await render_panel(interaction, previous)
    else:
        embed, view = build_card(bot, interaction.guild, row)
        retire(previous)
        view.message = await interaction.edit_original_response(
            embed=embed, view=view, allowed_mentions=discord.AllowedMentions.none()
        )
    if said:
        await interaction.followup.send(
            said, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
        )


async def run_move(
    interaction: discord.Interaction, slug: str, move: Any, previous: Any = None, **extra: Any
) -> None:
    """The one path every card button takes: staff re-asked, the shared move, the card again."""
    if not await opened(interaction):
        return
    bot = interaction.client
    guild = interaction.guild
    if posts_are_off(bot.store, guild.id):
        await render_card(interaction, slug, previous, POSTS_OFF)
        return
    row = await get_post(bot.db, guild.id, slug)
    if row is None:
        await render_panel(interaction, previous)
        return
    found = await move(bot, guild, row, interaction.user, **extra)
    await render_card(interaction, slug, previous, found.message)


class PostsView(Panel):
    def __init__(self, minutes: int) -> None:
        super().__init__(minutes, footer=PANEL_TIMEOUT_FOOTER)


class NewPostButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label=NEW_POST, style=discord.ButtonStyle.primary, row=0)

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await still_staff(interaction):
            return
        await interaction.response.send_modal(NewPostModal(self.view))


class ModePick(discord.ui.Select):
    def __init__(self, current: str) -> None:
        super().__init__(
            placeholder=MODE_PICK,
            options=[
                discord.SelectOption(
                    label=MODE_OPTION.format(mode=name), value=name, default=name == current
                )
                for name in MODES
            ],
            min_values=1,
            max_values=1,
            row=2,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await opened(interaction):
            return
        said = await set_mode(
            interaction.client, interaction.guild, interaction.user, self.values[0]
        )
        await render_panel(interaction, self.view)
        await interaction.followup.send(
            said, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
        )


class LogsButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label=LOGS, style=discord.ButtonStyle.secondary, row=0)

    async def callback(self, interaction: discord.Interaction) -> None:
        await send_logs(interaction, "posts")


class PostPick(discord.ui.Select):
    def __init__(self, guild: Any, rows: list[Any]) -> None:
        super().__init__(
            placeholder=PICK_A_POST,
            options=[
                discord.SelectOption(label=option_label(guild, row), value=str(row["slug"]))
                for row in rows[:SELECT_CAP]
            ],
            min_values=1,
            max_values=1,
            row=1,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await opened(interaction):
            return
        await render_card(interaction, self.values[0], self.view)


class BackButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label=BACK, style=discord.ButtonStyle.secondary, row=1)

    async def callback(self, interaction: discord.Interaction) -> None:
        await back_to_panel(interaction, self.view)


class MoveButton(discord.ui.Button):
    def __init__(self, slug: str, label: str) -> None:
        super().__init__(label=label, style=discord.ButtonStyle.success, row=0)
        self.slug = slug

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await still_staff(interaction):
            return
        await run_move(interaction, self.slug, publish_post, self.view)


class TakeDownButton(discord.ui.Button):
    def __init__(self, slug: str) -> None:
        super().__init__(label=TAKE_IT_DOWN, style=discord.ButtonStyle.danger, row=0)
        self.slug = slug

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await still_staff(interaction):
            return
        await run_move(interaction, self.slug, take_down_post, self.view)


class EditButton(discord.ui.Button):
    def __init__(self, slug: str) -> None:
        super().__init__(label="Edit…", style=discord.ButtonStyle.primary, row=0)
        self.slug = slug

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await still_staff(interaction):
            return
        row = await get_post(interaction.client.db, interaction.guild.id, self.slug)
        if row is None:
            await answer(interaction, NO_SUCH_POST.format(slug=self.slug))
            return
        await interaction.response.send_modal(EditPostModal(self.slug, row, self.view))


class PinButton(discord.ui.Button):
    def __init__(self, slug: str, pinned: bool) -> None:
        super().__init__(
            label=DO_NOT_PIN_IT if pinned else PIN_IT,
            style=discord.ButtonStyle.secondary,
            row=0,
        )
        self.slug = slug
        self.wanted = not pinned

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await still_staff(interaction):
            return
        await run_move(interaction, self.slug, save_post, self.view, pin=self.wanted)


class VersionsButton(discord.ui.Button):
    def __init__(self, slug: str) -> None:
        super().__init__(label=VERSIONS, style=discord.ButtonStyle.secondary, row=1)
        self.slug = slug

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await opened(interaction):
            return
        await render_versions(interaction, self.slug, None, self.view)


class CardButton(discord.ui.Button):
    def __init__(self, slug: str) -> None:
        super().__init__(label=BACK, style=discord.ButtonStyle.secondary, row=1)
        self.slug = slug

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await opened(interaction):
            return
        await render_card(interaction, self.slug, self.view)


class VersionPick(discord.ui.Select):
    def __init__(
        self,
        slug: str,
        guild: Any,
        rows: list[Any],
        picked: Any,
        top: Any,
        shipped: frozenset[int] = frozenset(),
    ) -> None:
        super().__init__(
            placeholder=PICK_A_VERSION,
            options=[
                discord.SelectOption(
                    label=VERSION_OPTION.format(
                        line=version_line(
                            one,
                            who=who_words(guild, row_value(one, "saved_by")),
                            current=int(one["n"]) == top,
                            shipped=one["n"] in shipped,
                        )
                    )[:100],
                    value=str(int(one["n"])),
                    default=picked is not None and int(one["n"]) == int(picked),
                )
                for one in rows
            ],
            min_values=1,
            max_values=1,
            row=2,
        )
        self.slug = slug

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await opened(interaction):
            return
        await render_versions(interaction, self.slug, int(self.values[0]), self.view)


class ViewVersionButton(discord.ui.Button):
    def __init__(self, slug: str, n: int) -> None:
        super().__init__(label=VIEW_IT, style=discord.ButtonStyle.primary, row=0)
        self.slug = slug
        self.n = n

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await opened(interaction):
            return
        bot = interaction.client
        row = await get_post(bot.db, interaction.guild.id, self.slug)
        if row is None:
            await render_panel(interaction, self.view)
            return
        version = await get_version(bot.db, int(row["id"]), self.n)
        if version is None:
            await render_versions(
                interaction,
                self.slug,
                None,
                self.view,
                NO_SUCH_VERSION.format(n=self.n, title=row["title"]),
            )
            return
        payload = render_message(version)
        content = str(payload.get("content") or "")
        embed = payload.get("embed")
        if not content.strip() and embed is None:
            await interaction.followup.send(
                NOTHING_IN_IT.format(n=self.n),
                ephemeral=True,
                allowed_mentions=discord.AllowedMentions.none(),
            )
            return
        await interaction.followup.send(
            content=content or None,
            embed=embed,
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )


class UseVersionButton(discord.ui.Button):
    def __init__(self, slug: str, n: int) -> None:
        super().__init__(label=USE_THIS_VERSION, style=discord.ButtonStyle.success, row=0)
        self.slug = slug
        self.n = n

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await opened(interaction):
            return
        bot = interaction.client
        row = await get_post(bot.db, interaction.guild.id, self.slug)
        if row is None:
            await render_panel(interaction, self.view)
            return
        version = await get_version(bot.db, int(row["id"]), self.n)
        if version is None:
            await render_versions(
                interaction,
                self.slug,
                None,
                self.view,
                NO_SUCH_VERSION.format(n=self.n, title=row["title"]),
            )
            return
        said = summary_of(version, summary_chars(bot.store, interaction.guild.id))
        await confirm(
            interaction,
            PostsView(panel_minutes(bot.store, interaction.guild.id)),
            discord.Embed(
                title=VERSION_DRAWER_TITLE.format(n=self.n, title=row["title"]),
                description=said or NOTHING_IN_IT.format(n=self.n),
            ),
            confirm_items(
                yes=USE_IT_YES.format(n=self.n),
                no=KEEP_IT,
                on_yes=lambda one, card: use_version(one, self.slug, self.n, card),
                on_no=lambda one, card: render_card(one, self.slug, card),
            ),
            self.view,
            question=USE_IT_QUESTION.format(n=self.n),
        )


class DeleteButton(discord.ui.Button):
    def __init__(self, slug: str) -> None:
        super().__init__(label=DELETE_THIS_POST, style=discord.ButtonStyle.danger, row=0)
        self.slug = slug

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await opened(interaction):
            return
        row = await get_post(interaction.client.db, interaction.guild.id, self.slug)
        if row is None:
            await render_panel(interaction, self.view)
            return
        await confirm(
            interaction,
            PostsView(panel_minutes(interaction.client.store, interaction.guild.id)),
            discord.Embed(title=row["title"], description=preview_of(row)),
            confirm_items(
                yes=DELETE_YES,
                no=KEEP_IT,
                on_yes=lambda one, card: remove_and_go_back(one, self.slug, card),
                on_no=back_to_panel,
            ),
            self.view,
            question=DELETE_QUESTION,
        )


async def remove_and_go_back(
    interaction: discord.Interaction, slug: str, previous: Any = None
) -> None:
    if not await opened(interaction):
        return
    bot = interaction.client
    row = await get_post(bot.db, interaction.guild.id, slug)
    if row is None:
        await render_panel(interaction, previous)
        return
    found = await remove_post(bot, interaction.guild, row, interaction.user)
    await render_panel(interaction, previous)
    await interaction.followup.send(
        found.message, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
    )


class ChannelPick(discord.ui.ChannelSelect):
    def __init__(self, slug: str) -> None:
        super().__init__(
            placeholder=PICK_A_CHANNEL,
            channel_types=[discord.ChannelType.text, discord.ChannelType.news],
            min_values=1,
            max_values=1,
            row=2,
        )
        self.slug = slug

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await still_staff(interaction):
            return
        await run_move(
            interaction, self.slug, save_post, self.view, channel_id=self.values[0].id
        )


class StylePick(discord.ui.Select):
    def __init__(self, slug: str, current: str) -> None:
        super().__init__(
            placeholder=PICK_A_STYLE,
            options=[
                discord.SelectOption(
                    label=STYLE_LABELS[style][:100], value=style, default=style == current
                )
                for style in STYLES
            ],
            min_values=1,
            max_values=1,
            row=3,
        )
        self.slug = slug

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await still_staff(interaction):
            return
        await run_move(interaction, self.slug, save_post, self.view, style=self.values[0])


class NewPostModal(AnswersErrors, discord.ui.Modal, title=NEW_MODAL_TITLE):
    heading = discord.ui.TextInput(label="What is it called?", max_length=TITLE_MAX)

    def __init__(self, previous: Any = None) -> None:
        super().__init__()
        self.previous = previous

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not await opened(interaction):
            return
        found = await make_post(
            interaction.client, interaction.guild, interaction.user, title=str(self.heading)
        )
        if not found.ok:
            await render_panel(interaction, self.previous)
            await interaction.followup.send(
                found.message, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
            )
            return
        await render_card(interaction, str(found.value["slug"]), self.previous, found.message)


class EditPostModal(AnswersErrors, discord.ui.Modal, title=MODAL_TITLE):
    heading = discord.ui.TextInput(label="Title", max_length=TITLE_MAX)
    body = discord.ui.TextInput(
        label="The message",
        style=discord.TextStyle.paragraph,
        max_length=BODY_BOX_MAX,
        required=False,
    )

    def __init__(self, slug: str, row: Any, previous: Any = None) -> None:
        super().__init__()
        self.slug = slug
        self.previous = previous
        self.heading.default = str(row["title"])[:TITLE_MAX]
        self.body.default = str(row_value(row, "body", ""))[:BODY_BOX_MAX] or None
        self.body.label = f"The message — up to {cap_for(row_value(row, 'style', PLAIN))}"

    async def on_submit(self, interaction: discord.Interaction) -> None:
        """Discord's box holds 4000, which is over the plain cap, so the cap is checked here."""
        await run_move(
            interaction,
            self.slug,
            save_post,
            self.previous,
            title=str(self.heading),
            body=str(self.body),
        )


class Posts(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.last_ok_at: str | None = None
        self.last_error: str | None = None

    async def cog_load(self) -> None:
        if not getattr(self.bot.db, "is_connected", False):
            return
        self._reconcile_loop.start()

    async def cog_unload(self) -> None:
        self._reconcile_loop.cancel()

    def loop_health(self, name: str) -> tuple[str | None, str | None]:
        if name.removeprefix("_").removesuffix("_loop") != LOOP_NAME:
            return (None, None)
        return (self.last_ok_at, self.last_error)

    @tasks.loop(minutes=RECONCILE_MINUTES)
    async def _reconcile_loop(self) -> None:
        """`cog_load` runs before any guild is known, so the first tick is where seeding lives."""
        if not getattr(self.bot.db, "is_connected", False):
            return
        for guild in list(getattr(self.bot, "guilds", ()) or ()):
            if bool(getattr(guild, "unavailable", False)):
                continue
            await self._seed(guild)
        await reconcile_posts(self.bot)
        self.last_ok_at = discord.utils.utcnow().isoformat()
        self.last_error = None

    @_reconcile_loop.before_loop
    async def _before_reconcile(self) -> None:
        await wait_ready(self.bot, self._reconcile_broke)

    @_reconcile_loop.error
    async def _reconcile_broke(self, exc: BaseException) -> None:
        self.last_error = f"{type(exc).__name__}: {exc}"
        log.warning("posts: the reconcile loop stopped — %s", self.last_error, exc_info=exc)
        self._reconcile_loop.restart()

    async def _seed(self, guild: Any) -> None:
        if await count_posts(self.bot.db, guild.id) == 0:
            made = await seed_posts(self.bot, guild)
            if made:
                await log_action(
                    self.bot, guild, "post.seeded", details={"count": made, "via": VIA_BOOT}
                )
            return
        await refresh_seeds(self.bot.db, guild.id)

    @app_commands.command(
        name="posts", description="The welcome, rules and other standing messages"
    )
    @app_commands.default_permissions(STAFF_ONLY)
    async def posts_panel_command(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await answer(interaction, GUILD_ONLY)
            return
        if not await require_staff(interaction):
            return
        if not self.bot.db.is_connected:
            log.warning("posts: refused the panel — the database is not connected")
            await answer(interaction, DB_UNAVAILABLE)
            return
        embed, view = await build_panel(self.bot, interaction.guild, interaction.user)
        await interaction.response.send_message(
            embed=embed,
            view=view,
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        view.message = await interaction.original_response()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Posts(bot))


__all__ = [
    "BackButton",
    "ChannelPick",
    "DeleteButton",
    "EditButton",
    "EditPostModal",
    "LogsButton",
    "ModePick",
    "MoveButton",
    "NewPostButton",
    "NewPostModal",
    "PinButton",
    "PostPick",
    "Posts",
    "PostsView",
    "StylePick",
    "TakeDownButton",
    "UseVersionButton",
    "VersionPick",
    "VersionsButton",
    "ViewVersionButton",
    "back_to_panel",
    "build_card",
    "build_panel",
    "build_versions",
    "line_for",
    "option_label",
    "remove_and_go_back",
    "render_card",
    "render_panel",
    "render_versions",
    "run_move",
    "use_version",
    "who_words",
]
