"""The /pb panel: a member's own match and opt-out, and the staff moves behind Manage…."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import discord

from . import pb_moves, pb_store
from .command_errors import AnswersErrors
from .panels import Panel, db_up, opened, retire, still_staff
from .pb_feed import OFF, PAGE, mode_of, said, time_words
from .pb_moves import NAME_LIMIT, REASON_LIMIT
from .points_moves import said as points_said
from .settings_store import PB_FEED_PANEL_MINUTES, PB_FEED_REMATCH_DAYS
from .timezones import unix

OPT_OUT = "opt_out"
OPT_IN = "opt_in"
MANAGE = "manage"
BACK = "back"
UNMATCH = "unmatch"
BLOCK = "block"
UNBLOCK = "unblock"
CLEAR = "clear"
SET = "set"
LOOK = "look"

MANAGE_LABEL = "Manage…"
SITE_LABEL = "Open on the site"
BACK_LABEL = "Back"
PICK_PLACEHOLDER = "Pick a member…"
SET_TITLE = "speedrun.com account"
SET_LABEL = "Their speedrun.com name"
REASON_LABEL = "Reason (the member is told)"
STAFF_LABELS = {
    UNMATCH: "Unmatch",
    BLOCK: "Block",
    UNBLOCK: "Unblock",
    CLEAR: "Clear the opt-out",
    SET: "Set by hand…",
    LOOK: "Look now",
}
STAFF_STYLES = {
    UNMATCH: discord.ButtonStyle.secondary,
    BLOCK: discord.ButtonStyle.danger,
    UNBLOCK: discord.ButtonStyle.success,
    CLEAR: discord.ButtonStyle.secondary,
    SET: discord.ButtonStyle.primary,
    LOOK: discord.ButtonStyle.secondary,
}
FEED_FIELD = "The feed"
MEMBER_FIELD = "Their match"
FEED_LINE = (
    "{mode} · {matched} matched · {none} with no match · {opted_out} opted out · "
    "{blocked} blocked"
)
LAST_OK = "last look {when}"
LAST_FAILED = "could not look {when} — {reason}"
STATE_WORDS = {
    pb_store.MATCHED: "matched to [{runner}]({link}) ({source})",
    pb_store.NONE: "no match",
    pb_store.OPTED_OUT: "opted out",
    pb_store.BLOCKED: "blocked by staff",
    None: "not looked up yet",
}
LOOKED_LINE = "last looked {when}"
LAST_PB_LINE = "last new personal best {when}"
REASONED = (UNMATCH, BLOCK, CLEAR)
AGAIN_CHOICES = 10
AGAIN_LINE = "{name} — {game} · {time}"
AGAIN_NOTE = "{outcome} · post {id}"
AGAIN_MARK = " · again"


class PbPanel(Panel):
    def __init__(
        self, bot: Any, guild_id: int, *, subject: int | None = None, home: bool = False
    ) -> None:
        super().__init__(
            int(bot.store.get(guild_id, PB_FEED_PANEL_MINUTES)),
            footer=said(bot.store, guild_id, "pb_feed_panel_footer"),
            again=self.shown_again,
        )
        self.subject = subject
        self.home = home

    async def shown_again(self, interaction: discord.Interaction, previous: Any) -> None:
        if self.subject is None:
            await render_own(interaction, previous)
            return
        await render_member(interaction, self.subject, previous)


def home_of(previous: Any) -> bool:
    """Opened from the leaderboard, so every render of this sub-panel keeps the way back."""
    return bool(getattr(previous, "home", False))


def when_words(at: Any) -> str:
    found = pb_store.parsed(at)
    return f"<t:{unix(found)}:R>" if isinstance(found, datetime) else ""


def own_line(store: Any, guild_id: int, row: Any, login: str | None) -> str:
    """What a member reads about themselves; one sentence per state."""
    state = row["state"] if row is not None else None
    if state == pb_store.OPTED_OUT:
        return said(store, guild_id, "pb_feed_you_opted_out")
    if state == pb_store.BLOCKED:
        return said(store, guild_id, "pb_feed_you_blocked")
    if state == pb_store.MATCHED:
        key = "pb_feed_you_set" if row["source"] == pb_store.STAFF else "pb_feed_you_matched"
        matched = said(
            store,
            guild_id,
            key,
            runner=row["src_name"],
            link=row["src_weblink"],
            login=row["twitch_login"] or login or "",
        )
        return f"{matched} {posting_line(store, guild_id)}"
    if not login:
        return said(store, guild_id, "pb_feed_you_unlinked")
    if state == pb_store.NONE:
        return said(
            store,
            guild_id,
            "pb_feed_you_none",
            login=login,
            days=store.get(guild_id, PB_FEED_REMATCH_DAYS),
        )
    return said(store, guild_id, "pb_feed_you_waiting")


def posting_line(store: Any, guild_id: int) -> str:
    """Whether a personal best is posted right now; it never promises a post the mode forbids."""
    return said(store, guild_id, f"pb_feed_posting_{mode_of(store, guild_id)}")


def own_move(row: Any) -> str | None:
    state = row["state"] if row is not None else None
    if state == pb_store.BLOCKED:
        return None
    return OPT_IN if state == pb_store.OPTED_OUT else OPT_OUT


def staff_moves(row: Any, mode: str) -> list[str]:
    """Only the moves that are valid on this member right now."""
    state = row["state"] if row is not None else None
    moves: list[str] = []
    if state != pb_store.OPTED_OUT and not (row is not None and row["opted_out_at"]):
        if mode != OFF:
            moves.append(SET)
    if state == pb_store.MATCHED:
        moves.append(UNMATCH)
        if mode != OFF:
            moves.append(LOOK)
    if state == pb_store.OPTED_OUT:
        moves.append(CLEAR)
    moves.append(UNBLOCK if state == pb_store.BLOCKED else BLOCK)
    return moves


def member_lines(row: Any) -> list[str]:
    state = row["state"] if row is not None else None
    lines = [
        STATE_WORDS[state].format(
            runner=row["src_name"] if row is not None else "",
            link=row["src_weblink"] if row is not None else "",
            source=row["source"] if row is not None else "",
        )
    ]
    if row is not None and row["looked_at"]:
        lines.append(LOOKED_LINE.format(when=when_words(row["looked_at"])))
    if row is not None and row["last_pb_at"]:
        lines.append(LAST_PB_LINE.format(when=when_words(row["last_pb_at"])))
    if row is not None and row["look_error"]:
        lines.append(str(row["look_error"]))
    return lines


async def feed_lines(bot: Any, guild: Any) -> list[str]:
    rows = await pb_store.matches(bot.db, guild.id)
    counts = {state: 0 for state in pb_store.STATES}
    for row in rows:
        if row["state"] in counts:
            counts[row["state"]] += 1
    lines = [FEED_LINE.format(mode=mode_of(bot.store, guild.id), **counts)]
    looked = await pb_store.looks(bot.db, guild.id)
    if looked is not None and looked["outcome"] == "failed":
        lines.append(
            LAST_FAILED.format(when=when_words(looked["last_at"]), reason=looked["reason"] or "")
        )
    elif looked is not None and looked["last_ok_at"]:
        lines.append(LAST_OK.format(when=when_words(looked["last_ok_at"])))
    return lines


def site_url(bot: Any) -> str | None:
    origin = str(getattr(getattr(bot, "settings", None), "origin", "") or "").strip()
    return f"{origin.rstrip('/')}/{PAGE}" if origin else None


async def build_own(
    bot: Any, guild: Any, member: Any, *, note: str = "", home: bool = False
) -> tuple[discord.Embed, PbPanel]:
    store = bot.store
    row = await pb_store.match(bot.db, guild.id, member.id)
    login = (await pb_store.links(bot.db)).get(int(member.id))
    lines = [note, own_line(store, guild.id, row, login)] if note else [
        own_line(store, guild.id, row, login)
    ]
    embed = discord.Embed(
        title=said(store, guild.id, "pb_feed_panel_title"), description="\n\n".join(lines)
    )
    view = PbPanel(bot, guild.id, home=home)
    move = own_move(row)
    if move is not None:
        view.add_item(OwnButton(move, said(store, guild.id, f"pb_feed_{move}_label")))
    if store.is_staff(member):
        embed.add_field(
            name=FEED_FIELD, value="\n".join(await feed_lines(bot, guild))[:1024], inline=False
        )
        view.add_item(ManageButton())
        url = site_url(bot)
        if url:
            view.add_item(
                discord.ui.Button(label=SITE_LABEL, style=discord.ButtonStyle.link, url=url, row=0)
            )
    if home:
        view.add_item(HomeButton(points_said(store, guild.id, "points_back_label")))
    return (embed, view)


async def build_manage(
    bot: Any, guild: Any, *, note: str = "", home: bool = False
) -> tuple[discord.Embed, PbPanel]:
    embed = discord.Embed(
        title=said(bot.store, guild.id, "pb_feed_panel_title"), description=note or None
    )
    embed.add_field(
        name=FEED_FIELD, value="\n".join(await feed_lines(bot, guild))[:1024], inline=False
    )
    view = PbPanel(bot, guild.id, home=home)
    view.add_item(MemberPick())
    if mode_of(bot.store, guild.id) != OFF:
        posts = await pb_store.posts(bot.db, guild.id, AGAIN_CHOICES)
        if posts:
            view.add_item(
                AgainPick(
                    [again_option(guild, row) for row in posts],
                    said(bot.store, guild.id, "pb_feed_post_again_pick"),
                )
            )
    view.add_item(BackButton(None))
    return (embed, view)


def again_option(guild: Any, row: Any) -> discord.SelectOption:
    member = guild.get_member(int(row["user_id"]))
    name = getattr(member, "display_name", None) or row["src_name"] or str(row["user_id"])
    line = AGAIN_LINE.format(name=name, game=row["game"] or "", time=time_words(row["seconds"]))
    note = AGAIN_NOTE.format(outcome=row["outcome"], id=row["id"])
    return discord.SelectOption(
        label=line[:100],
        value=str(row["id"]),
        description=(note + (AGAIN_MARK if row["again_of"] else ""))[:100],
    )


async def build_member(
    bot: Any, guild: Any, user_id: int, *, note: str = "", home: bool = False
) -> tuple[discord.Embed, PbPanel]:
    row = await pb_store.match(bot.db, guild.id, user_id)
    embed = discord.Embed(
        title=said(bot.store, guild.id, "pb_feed_panel_title"),
        description="\n\n".join(part for part in (note, pb_moves.mention(guild, user_id)) if part),
    )
    embed.add_field(name=MEMBER_FIELD, value="\n".join(member_lines(row))[:1024], inline=False)
    view = PbPanel(bot, guild.id, subject=int(user_id), home=home)
    for move in staff_moves(row, mode_of(bot.store, guild.id)):
        view.add_item(StaffButton(move, int(user_id)))
    view.add_item(BackButton(int(user_id)))
    return (embed, view)


async def show(interaction: discord.Interaction, built: Any, previous: Any) -> None:
    embed, view = built
    retire(previous)
    view.message = await interaction.edit_original_response(
        embed=embed, view=view, allowed_mentions=discord.AllowedMentions.none()
    )


async def render_own(
    interaction: discord.Interaction,
    previous: Any = None,
    *,
    note: str = "",
    home: bool | None = None,
) -> None:
    built = await build_own(
        interaction.client,
        interaction.guild,
        interaction.user,
        note=note,
        home=home_of(previous) if home is None else home,
    )
    await show(interaction, built, previous)


async def render_manage(
    interaction: discord.Interaction, previous: Any = None, *, note: str = ""
) -> None:
    built = await build_manage(
        interaction.client, interaction.guild, note=note, home=home_of(previous)
    )
    await show(interaction, built, previous)


async def render_member(
    interaction: discord.Interaction, user_id: int, previous: Any = None, *, note: str = ""
) -> None:
    built = await build_member(
        interaction.client, interaction.guild, user_id, note=note, home=home_of(previous)
    )
    await show(interaction, built, previous)


async def run_own(interaction: discord.Interaction, move: str, previous: Any = None) -> None:
    if not await opened(interaction, staff=False):
        return
    act = pb_moves.opt_in if move == OPT_IN else pb_moves.opt_out
    outcome = await act(interaction.client, interaction.guild, interaction.user)
    await render_own(interaction, previous, note=outcome.message)


async def run_staff(
    interaction: discord.Interaction,
    move: str,
    user_id: int,
    previous: Any = None,
    *,
    reason: str = "",
) -> None:
    if not await opened(interaction):
        return
    act = {
        UNMATCH: pb_moves.unmatch,
        BLOCK: pb_moves.block,
        UNBLOCK: pb_moves.unblock,
        CLEAR: pb_moves.clear_opt_out,
        LOOK: pb_moves.look_now,
    }[move]
    words = {"reason": reason} if move in REASONED else {}
    outcome = await act(interaction.client, interaction.guild, user_id, interaction.user, **words)
    await render_member(interaction, user_id, previous, note=outcome.message)


async def run_set(
    interaction: discord.Interaction,
    user_id: int,
    name: str,
    previous: Any = None,
    *,
    reason: str = "",
) -> None:
    if not await opened(interaction):
        return
    outcome = await pb_moves.set_by_hand(
        interaction.client, interaction.guild, user_id, name, interaction.user, reason=reason
    )
    await render_member(interaction, user_id, previous, note=outcome.message)


async def run_again(interaction: discord.Interaction, post_id: int, previous: Any = None) -> None:
    if not await opened(interaction):
        return
    outcome = await pb_moves.post_again(
        interaction.client, interaction.guild, post_id, interaction.user
    )
    await render_manage(interaction, previous, note=outcome.message)


async def open_modal(interaction: discord.Interaction, modal: discord.ui.Modal) -> None:
    """A modal has to be the first answer, so staff and the database are asked without a defer."""
    if not await still_staff(interaction):
        return
    if not await db_up(interaction):
        return
    await interaction.response.send_modal(modal)


class OwnButton(discord.ui.Button):
    def __init__(self, move: str, label: str) -> None:
        super().__init__(label=label[:80], style=discord.ButtonStyle.secondary, row=0)
        self.move = move

    async def callback(self, interaction: discord.Interaction) -> None:
        await run_own(interaction, self.move, self.view)


class ManageButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label=MANAGE_LABEL, style=discord.ButtonStyle.primary, row=0)

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await opened(interaction):
            return
        await render_manage(interaction, self.view)


class BackButton(discord.ui.Button):
    def __init__(self, subject: int | None) -> None:
        super().__init__(label=BACK_LABEL, style=discord.ButtonStyle.secondary, row=1)
        self.subject = subject

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await opened(interaction):
            return
        if self.subject is None:
            await render_own(interaction, self.view)
            return
        await render_manage(interaction, self.view)


class HomeButton(discord.ui.Button):
    def __init__(self, label: str) -> None:
        super().__init__(label=label[:80], style=discord.ButtonStyle.secondary, row=1)

    async def callback(self, interaction: discord.Interaction) -> None:
        from .points_panel import render_board

        if not await opened(interaction, staff=False):
            return
        await render_board(interaction, self.view)


class MemberPick(discord.ui.UserSelect):
    def __init__(self) -> None:
        super().__init__(placeholder=PICK_PLACEHOLDER, min_values=1, max_values=1, row=0)

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await opened(interaction):
            return
        await render_member(interaction, int(self.values[0].id), self.view)


class AgainPick(discord.ui.Select):
    def __init__(self, options: list[discord.SelectOption], placeholder: str) -> None:
        super().__init__(
            placeholder=placeholder[:150], min_values=1, max_values=1, options=options, row=2
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await run_again(interaction, int(self.values[0]), self.view)


class StaffButton(discord.ui.Button):
    def __init__(self, move: str, user_id: int) -> None:
        super().__init__(label=STAFF_LABELS[move], style=STAFF_STYLES[move], row=0)
        self.move = move
        self.user_id = int(user_id)

    async def callback(self, interaction: discord.Interaction) -> None:
        if self.move == SET:
            await open_modal(interaction, SetModal(self.user_id, self.view))
            return
        if self.move in REASONED:
            await open_modal(interaction, ReasonModal(self.move, self.user_id, self.view))
            return
        await run_staff(interaction, self.move, self.user_id, self.view)


class SetModal(AnswersErrors, discord.ui.Modal):
    runner = discord.ui.TextInput(
        label=SET_LABEL, style=discord.TextStyle.short, max_length=NAME_LIMIT
    )

    reason = discord.ui.TextInput(
        label=REASON_LABEL,
        style=discord.TextStyle.paragraph,
        max_length=REASON_LIMIT,
        required=False,
    )

    def __init__(self, user_id: int, previous: Any = None) -> None:
        super().__init__(title=SET_TITLE)
        self.user_id = int(user_id)
        self.previous = previous

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await run_set(
            interaction, self.user_id, str(self.runner), self.previous, reason=str(self.reason)
        )


class ReasonModal(AnswersErrors, discord.ui.Modal):
    reason = discord.ui.TextInput(
        label=REASON_LABEL,
        style=discord.TextStyle.paragraph,
        max_length=REASON_LIMIT,
        required=False,
    )

    def __init__(self, move: str, user_id: int, previous: Any = None) -> None:
        super().__init__(title=STAFF_LABELS[move])
        self.move = move
        self.user_id = int(user_id)
        self.previous = previous

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await run_staff(
            interaction, self.move, self.user_id, self.previous, reason=str(self.reason)
        )


async def open_panel(interaction: discord.Interaction) -> None:
    if not await db_up(interaction):
        return
    embed, view = await build_own(interaction.client, interaction.guild, interaction.user)
    await interaction.response.send_message(
        embed=embed, view=view, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
    )
    view.message = await interaction.original_response()


__all__ = [
    "AGAIN_CHOICES",
    "AgainPick",
    "BackButton",
    "HomeButton",
    "ManageButton",
    "MemberPick",
    "OwnButton",
    "PbPanel",
    "ReasonModal",
    "SetModal",
    "StaffButton",
    "build_manage",
    "build_member",
    "build_own",
    "member_lines",
    "open_panel",
    "own_line",
    "own_move",
    "posting_line",
    "staff_moves",
]
