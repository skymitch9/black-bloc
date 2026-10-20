from __future__ import annotations

from datetime import datetime
from typing import Any

import discord

from . import questions as rules
from . import questions_moves as moves
from . import questions_store as store
from .command_errors import AnswersErrors
from .panels import (
    KEEP_IT,
    Panel,
    answer,
    clamped,
    confirm,
    confirm_items,
    opened,
    option_label,
    retire,
    still_staff,
)

SELECT_MAX = 25


class QuestionsPanel(Panel):
    def __init__(self, minutes: int, *, question_id: int | None = None) -> None:
        super().__init__(minutes, footer=rules.PANEL_TIMEOUT_FOOTER, again=self.shown_again)
        self.question_id = question_id

    async def shown_again(self, interaction: discord.Interaction, previous: Any) -> None:
        if self.question_id is not None:
            await render_card(interaction, self.question_id, previous)
            return
        await render_root(interaction, previous)


def minutes_for(bot: Any, guild_id: int) -> int:
    return rules.panel_minutes(bot.store, guild_id)


def root_lines(
    bot: Any, guild: Any, found: dict[str, Any], queued: list[Any], owner: int | None
) -> list[str]:
    slot: datetime = found["slot"]
    schedule = found["schedule"]
    status = found["status"]
    shown = found["posted"] if status == rules.POSTED and found["posted"] else found["question"]
    lines = [
        rules.NEXT_LINE.format(when=rules.stamp(slot, "F"), relative=rules.stamp(slot, "R")),
        rules.STATE_LINE.format(state=rules.STATE_WORDS.get(status, status)),
        rules.QUESTION_LINE.format(body=shown["body"]) if shown else rules.NO_QUESTION_LINE,
        rules.QUEUED_LINE.format(count=len(queued)),
        rules.MODE_LINE.format(mode=found["mode"]),
    ]
    if found["mode"] != rules.OFF:
        wanted, why = moves.target_id(bot, guild, found["mode"])
        lines.append(rules.WHERE_LINE.format(where=f"<#{wanted}>" if wanted else why))
    grace = int(schedule.grace.total_seconds() // 60)
    lines.append(
        rules.OWNER_LINE.format(owner=owner, grace=grace) if owner else rules.NO_OWNER_LINE
    )
    return lines


def downable(found: dict[str, Any]) -> Any:
    posted = found["posted"]
    if found["status"] == rules.POSTED and posted is not None:
        return posted if posted["posted_by"] == rules.BY_BOT else None
    return found.get("extra")


def root_moves(found: dict[str, Any], queued: list[Any]) -> list[str]:
    status = found["status"]
    shown: list[str] = ["add"]
    if found["mode"] != rules.OFF and queued:
        shown.append("post")
    if status in (rules.PENDING, rules.SKIPPED_EMPTY):
        shown.append("skip")
    if status == rules.SKIPPED:
        shown.append("unskip")
    if downable(found) is not None:
        shown.append("take_down")
    shown.append("refresh")
    return shown


def card_moves(place: int, total: int) -> list[str]:
    shown = ["edit", "remove"]
    if place > 0:
        shown.append("up")
    if place < total - 1:
        shown.append("down")
    shown.append("back")
    return shown


async def build_root(bot: Any, guild: Any) -> tuple[discord.Embed, QuestionsPanel]:
    found = await moves.week(bot, guild)
    queued = await store.queued(bot.db, guild.id)
    lines = root_lines(bot, guild, found, queued, rules.owner_of(bot.store, guild.id))
    embed = discord.Embed(title=rules.PANEL_TITLE, description=clamped(lines))
    view = QuestionsPanel(minutes_for(bot, guild.id))
    for name in root_moves(found, queued):
        view.add_item(RootButton(name, found))
    if queued:
        view.add_item(QueuePick(queued))
    return embed, view


async def build_card(
    bot: Any, guild: Any, question_id: int
) -> tuple[discord.Embed, QuestionsPanel] | None:
    queued = await store.queued(bot.db, guild.id)
    place = next((at for at, one in enumerate(queued) if one["id"] == question_id), None)
    if place is None:
        return None
    row = queued[place]
    embed = discord.Embed(
        title=rules.CARD_TITLE.format(place=place + 1), description=clamped([row["body"]])
    )
    view = QuestionsPanel(minutes_for(bot, guild.id), question_id=int(row["id"]))
    for name in card_moves(place, len(queued)):
        view.add_item(CardButton(name, int(row["id"])))
    return embed, view


async def show(interaction: discord.Interaction, built: Any, previous: Any) -> None:
    embed, view = built
    retire(previous)
    view.message = await interaction.edit_original_response(
        embed=embed, view=view, allowed_mentions=discord.AllowedMentions.none()
    )


async def render_root(interaction: discord.Interaction, previous: Any = None) -> None:
    await show(interaction, await build_root(interaction.client, interaction.guild), previous)


async def render_card(
    interaction: discord.Interaction, question_id: int, previous: Any = None
) -> None:
    """A question gone from the queue by the time its card is asked for lands on the list."""
    built = await build_card(interaction.client, interaction.guild, int(question_id))
    if built is None:
        await render_root(interaction, previous)
        return
    await show(interaction, built, previous)


async def after(
    interaction: discord.Interaction, outcome: Any, previous: Any, question_id: int | None = None
) -> None:
    if question_id is not None and outcome.ok:
        await render_card(interaction, question_id, previous)
    else:
        await render_root(interaction, previous)
    await answer(interaction, outcome.message)


async def back_to_root(interaction: discord.Interaction, previous: Any = None) -> None:
    if not await opened(interaction):
        return
    await render_root(interaction, previous)


async def open_card(interaction: discord.Interaction, question_id: int, previous: Any) -> None:
    if not await opened(interaction):
        return
    await render_card(interaction, question_id, previous)


async def ask(
    interaction: discord.Interaction, text: str, yes: str, run: Any, previous: Any
) -> None:
    if not await opened(interaction):
        return
    view = QuestionsPanel(minutes_for(interaction.client, interaction.guild.id))
    await confirm(
        interaction,
        view,
        discord.Embed(title=rules.PANEL_TITLE, description=text[:4000]),
        confirm_items(yes=yes, no=KEEP_IT, on_yes=run, on_no=back_to_root),
        previous,
    )


async def run_post_now(interaction: discord.Interaction, previous: Any = None) -> None:
    if not await opened(interaction):
        return
    outcome = await moves.post_now(interaction.client, interaction.guild, interaction.user)
    await after(interaction, outcome, previous)


async def run_skip(interaction: discord.Interaction, previous: Any = None) -> None:
    if not await opened(interaction):
        return
    outcome = await moves.skip(interaction.client, interaction.guild, interaction.user)
    await after(interaction, outcome, previous)


async def run_unskip(interaction: discord.Interaction, previous: Any = None) -> None:
    if not await opened(interaction):
        return
    outcome = await moves.unskip(interaction.client, interaction.guild, interaction.user)
    await after(interaction, outcome, previous)


def take_down_run(question_id: int) -> Any:
    async def run(interaction: discord.Interaction, previous: Any = None) -> None:
        if not await opened(interaction):
            return
        outcome = await moves.take_down(
            interaction.client, interaction.guild, interaction.user, question_id
        )
        await after(interaction, outcome, previous)

    return run


def remove_run(question_id: int) -> Any:
    async def run(interaction: discord.Interaction, previous: Any = None) -> None:
        if not await opened(interaction):
            return
        outcome = await moves.remove(
            interaction.client, interaction.guild, interaction.user, question_id
        )
        await after(interaction, outcome, previous)

    return run


async def run_move(
    interaction: discord.Interaction, question_id: int, direction: str, previous: Any
) -> None:
    if not await opened(interaction):
        return
    outcome = await moves.move(
        interaction.client, interaction.guild, interaction.user, question_id, direction
    )
    await after(interaction, outcome, previous, question_id)


ROOT_BUTTONS: dict[str, tuple[str, discord.ButtonStyle]] = {
    "add": (rules.ADD_LABEL, discord.ButtonStyle.primary),
    "post": (rules.POST_NOW_LABEL, discord.ButtonStyle.success),
    "skip": (rules.SKIP_LABEL, discord.ButtonStyle.secondary),
    "unskip": (rules.UNSKIP_LABEL, discord.ButtonStyle.secondary),
    "take_down": (rules.TAKE_DOWN_LABEL, discord.ButtonStyle.danger),
    "refresh": (rules.REFRESH_LABEL, discord.ButtonStyle.secondary),
}
CARD_BUTTONS: dict[str, tuple[str, discord.ButtonStyle]] = {
    "edit": (rules.EDIT_LABEL, discord.ButtonStyle.primary),
    "remove": (rules.REMOVE_LABEL, discord.ButtonStyle.danger),
    "up": (rules.UP_LABEL, discord.ButtonStyle.secondary),
    "down": (rules.DOWN_LABEL, discord.ButtonStyle.secondary),
    "back": (rules.BACK_LABEL, discord.ButtonStyle.secondary),
}


class RootButton(discord.ui.Button):
    def __init__(self, name: str, found: dict[str, Any]) -> None:
        label, style = ROOT_BUTTONS[name]
        super().__init__(label=label, style=style, row=0)
        self.name = name
        self.found = found

    async def callback(self, interaction: discord.Interaction) -> None:
        if self.name == "add":
            if not await still_staff(interaction):
                return
            await interaction.response.send_modal(AddModal(previous=self.view))
            return
        if self.name == "post":
            body = self.found["question"]["body"] if self.found["question"] else ""
            await ask(
                interaction,
                rules.POST_CONFIRM.format(body=body[:200]),
                rules.POST_NOW_LABEL,
                run_post_now,
                self.view,
            )
            return
        if self.name == "skip":
            await run_skip(interaction, self.view)
            return
        if self.name == "unskip":
            await run_unskip(interaction, self.view)
            return
        if self.name == "take_down":
            posted = downable(self.found)
            await ask(
                interaction,
                rules.TAKE_DOWN_CONFIRM.format(body=str(posted["body"])[:200]),
                rules.TAKE_DOWN_LABEL,
                take_down_run(int(posted["id"])),
                self.view,
            )
            return
        await back_to_root(interaction, self.view)


class CardButton(discord.ui.Button):
    def __init__(self, name: str, question_id: int) -> None:
        label, style = CARD_BUTTONS[name]
        super().__init__(label=label, style=style, row=0)
        self.name = name
        self.question_id = question_id

    async def callback(self, interaction: discord.Interaction) -> None:
        if self.name == "edit":
            if not await still_staff(interaction):
                return
            row = await store.get(interaction.client.db, interaction.guild.id, self.question_id)
            await interaction.response.send_modal(
                EditModal(
                    question_id=self.question_id,
                    current=str(row["body"]) if row is not None else "",
                    previous=self.view,
                )
            )
            return
        if self.name == "remove":
            await ask(
                interaction,
                rules.REMOVE_CONFIRM,
                rules.REMOVE_LABEL,
                remove_run(self.question_id),
                self.view,
            )
            return
        if self.name in ("up", "down"):
            await run_move(interaction, self.question_id, self.name, self.view)
            return
        await back_to_root(interaction, self.view)


class QueuePick(discord.ui.Select):
    def __init__(self, queued: list[Any]) -> None:
        options = [
            discord.SelectOption(
                label=option_label(place, None, row["body"]),
                value=str(row["id"]),
            )
            for place, row in enumerate(queued[:SELECT_MAX], start=1)
        ]
        super().__init__(
            placeholder=rules.QUEUE_PLACEHOLDER, options=options, min_values=1, max_values=1, row=1
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await open_card(interaction, int(self.values[0]), self.view)


class AddModal(AnswersErrors, discord.ui.Modal):
    typed = discord.ui.TextInput(
        label=rules.ADD_FIELD,
        placeholder=rules.ADD_PLACEHOLDER,
        style=discord.TextStyle.paragraph,
        max_length=4000,
    )

    def __init__(self, previous: Any = None) -> None:
        super().__init__(title=rules.ADD_TITLE)
        self.previous = previous

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not await opened(interaction):
            return
        outcome = await moves.add(
            interaction.client, interaction.guild, interaction.user, str(self.typed)
        )
        await after(interaction, outcome, self.previous)


class EditModal(AnswersErrors, discord.ui.Modal):
    typed = discord.ui.TextInput(
        label=rules.EDIT_FIELD, style=discord.TextStyle.paragraph, max_length=rules.BODY_LIMIT
    )

    def __init__(self, question_id: int = 0, current: str = "", previous: Any = None) -> None:
        super().__init__(title=rules.EDIT_TITLE)
        self.question_id = int(question_id)
        self.previous = previous
        self.typed.default = current or None

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not await opened(interaction):
            return
        outcome = await moves.edit(
            interaction.client,
            interaction.guild,
            interaction.user,
            self.question_id,
            str(self.typed),
        )
        await after(interaction, outcome, self.previous, self.question_id)
