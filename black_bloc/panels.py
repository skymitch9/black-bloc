from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

import discord

from .command_errors import AnswersErrors
from .logkinds import FEATURE_PAGES
from .settings_store import DB_UNAVAILABLE

log = logging.getLogger(__name__)

CAPPED_PLACEHOLDER = "{shown} of {total} — the rest are on the site"
SELECT_OPTION_LIMIT = 100
DESCRIPTION_LIMIT = 4000


@dataclass(frozen=True)
class Outcome:
    """One answer both doors read: words for Discord, a status and a code for the website."""

    ok: bool
    message: str
    code: str = ""
    status: int = 0
    value: Any = field(default=None)


def refusal(message: str, code: str, status: int) -> Outcome:
    return Outcome(False, message, code, status)


async def answer(interaction: discord.Interaction, text: str) -> None:
    if interaction.response.is_done():
        await interaction.followup.send(
            text, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
        )
        return
    await interaction.response.send_message(
        text, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
    )


async def still_allowed(interaction: discord.Interaction, ok: bool, refusal: str) -> bool:
    """A gate can close while a card is open, so every move re-asks instead of trusting it."""
    if ok:
        return True
    await answer(interaction, refusal)
    return False


async def still_staff(interaction: discord.Interaction) -> bool:
    store = interaction.client.store
    return await still_allowed(
        interaction, store.is_staff(interaction.user), store.staff_refusal(interaction.guild.id)
    )


def retire(previous: Any) -> None:
    """The view being replaced stops, so its own timeout never edits the render that replaced it."""
    if previous is None:
        return
    previous.replaced = True
    previous.stop()


async def db_ready(interaction: discord.Interaction) -> bool:
    """Called after a component/modal has already deferred; answers a followup, never a crash."""
    if interaction.client.db.is_connected:
        return True
    await interaction.followup.send(
        DB_UNAVAILABLE, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
    )
    return False


async def db_up(interaction: discord.Interaction) -> bool:
    """`db_ready` answers a followup; this one is for the reads that happen BEFORE a defer."""
    if interaction.client.db.is_connected:
        return True
    await answer(interaction, DB_UNAVAILABLE)
    return False


def capped_placeholder(
    shown: int, total: int, *, pick: str, capped: str = CAPPED_PLACEHOLDER
) -> str:
    if total > shown:
        return capped.format(shown=shown, total=total)
    return pick


def option_label(
    ident: Any, status: Any, text: Any, limit: int = SELECT_OPTION_LIMIT
) -> str:
    """A select option's label — id, optionally a status word, then as much text as fits."""
    parts = [f"#{ident}"]
    if status:
        parts.append(str(status))
    prefix = " · ".join(parts) + " · "
    kept = str(text or "").strip()[: max(0, limit - len(prefix))]
    return (prefix + kept)[:limit]


def clamped(lines: list[str]) -> str:
    found: list[str] = []
    spent = 0
    for line in lines:
        if spent + len(line) + 1 > DESCRIPTION_LIMIT:
            break
        found.append(line)
        spent += len(line) + 1
    return "\n".join(found)


def panel_minutes(store: Any, guild_id: int, key: str) -> int:
    return int(store.get(guild_id, key))


def site_page_url(origin: Any, feature: str) -> str | None:
    """The one home for a feature's dashboard address; no origin means no link at all."""
    text = str(origin or "").strip()
    if not text:
        return None
    return f"{text.rstrip('/')}/{FEATURE_PAGES[feature]}"


class Panel(AnswersErrors, discord.ui.View):
    """The one ephemeral panel view every feature's panel inherits."""

    def __init__(self, minutes: int, *, footer: str) -> None:
        super().__init__(timeout=max(1, int(minutes or 1)) * 60)
        self.footer = footer
        self.message: Any = None
        self.last_interaction: Any = None
        self.replaced = False

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        self.last_interaction = interaction
        return True

    async def on_timeout(self) -> None:
        if self.replaced or self.message is None:
            return
        for item in self.children:
            item.disabled = True
        embeds = list(self.message.embeds)
        if embeds:
            embeds[0] = embeds[0].copy()
            embeds[0].set_footer(text=self.footer)
        await self.went_quiet(embeds)

    async def went_quiet(self, embeds: list[Any]) -> None:
        """The freshest interaction token first, the message's own second, neither ever raising."""
        for edit in (self.through_last_interaction, self.through_message):
            try:
                if await edit(embeds):
                    return
            except discord.HTTPException as exc:
                log.info("panel: could not disable a timed-out panel: %s", exc)

    async def through_last_interaction(self, embeds: list[Any]) -> bool:
        if self.last_interaction is None:
            return False
        await self.last_interaction.edit_original_response(embeds=embeds, view=self)
        return True

    async def through_message(self, embeds: list[Any]) -> bool:
        await self.message.edit(embeds=embeds, view=self)
        return True


class NoteModal(AnswersErrors, discord.ui.Modal):
    """One paragraph field whose label names what the note is for and who is sent it."""

    note = discord.ui.TextInput(style=discord.TextStyle.paragraph)

    def __init__(
        self,
        *,
        title: str,
        label: str,
        max_length: int,
        on_submit: Callable[[discord.Interaction, str], Awaitable[None]],
        required: bool = True,
    ) -> None:
        super().__init__(title=title)
        self.note.label = label
        self.note.max_length = max_length
        self.note.required = required
        self.takes_note = on_submit

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await self.takes_note(interaction, str(self.note))


__all__ = [
    "CAPPED_PLACEHOLDER",
    "DESCRIPTION_LIMIT",
    "SELECT_OPTION_LIMIT",
    "NoteModal",
    "Outcome",
    "Panel",
    "answer",
    "capped_placeholder",
    "clamped",
    "db_ready",
    "db_up",
    "option_label",
    "panel_minutes",
    "refusal",
    "retire",
    "site_page_url",
    "still_allowed",
    "still_staff",
]
