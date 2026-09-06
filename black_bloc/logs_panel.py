from __future__ import annotations

from typing import Any

import discord

from .actionlog import LOGS_DB_DOWN, lines_for, logs_embed, recent_rows
from .panels import Panel, answer, panel_minutes, still_staff
from .settings_store import (
    LOGS_COUNT,
    LOGS_IMPORTANT_ONLY,
    LOGS_MAX,
    LOGS_MIN,
    SETTINGS_PANEL_MINUTES,
)

MORE = "Show more"
ONLY_IMPORTANT = "Important only"
EVERYTHING = "Show everything"
PANEL_TIMEOUT_FOOTER = "This log has gone quiet — press Logs again"


def clamped_count(count: Any) -> int:
    """The one clamp on how many lines a Logs list asks for; the registry bounds the setting."""
    return max(LOGS_MIN, min(int(count), LOGS_MAX))


class MoreButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label=MORE, style=discord.ButtonStyle.secondary, row=0)

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        await view.refresh(interaction, count=clamped_count(view.count + view.step))


class ToggleButton(discord.ui.Button):
    def __init__(self, label: str) -> None:
        super().__init__(label=label, style=discord.ButtonStyle.secondary, row=0)

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        await view.refresh(interaction, important_only=not view.important_only)


class LogsPanel(Panel):
    """The buttons under a Logs list: more of it, or only the lines that matter."""

    def __init__(
        self,
        feature: str,
        *,
        count: int,
        important_only: bool,
        step: int,
        minutes: int,
        staff_only: bool = True,
    ) -> None:
        super().__init__(minutes, footer=PANEL_TIMEOUT_FOOTER)
        self.feature = feature
        self.count = count
        self.important_only = important_only
        self.step = step
        self.staff_only = staff_only
        self.ran_out = False

    def buttons_for(self) -> list[discord.ui.Button]:
        """A move nobody can make is not drawn: there is no more log to show at the cap."""
        found: list[discord.ui.Button] = []
        if not self.ran_out and self.count < LOGS_MAX:
            found.append(MoreButton())
        found.append(ToggleButton(EVERYTHING if self.important_only else ONLY_IMPORTANT))
        return found

    async def page(self, bot: Any, guild_id: int) -> discord.Embed:
        rows = await recent_rows(bot.db, guild_id, self.feature, self.count, self.important_only)
        self.ran_out = len(rows) < self.count
        self.clear_items()
        for item in self.buttons_for():
            self.add_item(item)
        return logs_embed(
            self.feature,
            lines_for(rows, self.important_only),
            self.important_only,
            bot.settings.origin,
        )

    async def refresh(
        self,
        interaction: discord.Interaction,
        *,
        count: int | None = None,
        important_only: bool | None = None,
    ) -> None:
        """Staff and the database are re-asked before the move is applied, never trusted."""
        if self.staff_only and not await still_staff(interaction):
            return
        if not interaction.client.db.is_connected:
            await answer(interaction, LOGS_DB_DOWN)
            return
        if count is not None:
            self.count = count
        if important_only is not None:
            self.important_only = important_only
        embed = await self.page(interaction.client, interaction.guild.id)
        await interaction.response.edit_message(
            embed=embed, view=self, allowed_mentions=discord.AllowedMentions.none()
        )


def panel_for(
    bot: Any,
    guild_id: int,
    feature: str,
    *,
    count: int | None = None,
    important_only: bool | None = None,
    staff_only: bool = True,
) -> LogsPanel:
    """Where every Logs list opens, and the size of the step Show more adds."""
    store = bot.store
    step = clamped_count(store.get(guild_id, LOGS_COUNT))
    return LogsPanel(
        feature,
        count=step if count is None else clamped_count(count),
        important_only=(
            bool(store.get(guild_id, LOGS_IMPORTANT_ONLY))
            if important_only is None
            else bool(important_only)
        ),
        step=step,
        minutes=panel_minutes(store, guild_id, SETTINGS_PANEL_MINUTES),
        staff_only=staff_only,
    )


__all__ = [
    "EVERYTHING",
    "MORE",
    "ONLY_IMPORTANT",
    "PANEL_TIMEOUT_FOOTER",
    "LogsPanel",
    "MoreButton",
    "ToggleButton",
    "clamped_count",
    "panel_for",
]
