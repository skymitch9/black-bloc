# ruff: noqa: F401, F811
from __future__ import annotations

import asyncio

from black_bloc import brackets_moves as moves
from black_bloc import brackets_store as store_
from black_bloc.bot import COGS
from black_bloc.brackets_cards import SetButton, StarterButton
from black_bloc.cogs.community import brackets as cog_module
from black_bloc.command_visibility import HIDDEN_WHEN_OFF
from black_bloc.settings_store import GUILD_ONLY
from tests.test_brackets_buttons import FakeInteraction
from tests.test_brackets_moves import ADA, BEA, GUILD, TO, who
from tests.test_brackets_thread import (
    REHEARSAL,
    bot,
    created,
    guild,
    home,
    moved,
    running,
    the_thread,
)


class Loop:
    def __init__(self):
        self.started = False

    def start(self):
        self.started = True

    def cancel(self):
        self.started = False


def cog_for(bot, monkeypatch):
    bot.dynamic = []
    bot.add_dynamic_items = lambda *items: bot.dynamic.extend(items)
    found = cog_module.Brackets(bot)
    loop = Loop()
    monkeypatch.setattr(type(found), "_sweep", loop, raising=False)
    return found, loop


def test_the_cog_is_loaded_and_bracket_hides_while_the_mode_is_off():
    assert "black_bloc.cogs.community.brackets" in COGS
    assert HIDDEN_WHEN_OFF["brackets_mode"] == ("bracket",)


async def test_loading_registers_the_card_buttons_and_starts_the_sweep(bot, monkeypatch):
    cog, loop = cog_for(bot, monkeypatch)
    await cog.cog_load()
    assert bot.dynamic == [StarterButton, SetButton]
    assert loop.started
    await cog.cog_unload()
    assert not loop.started


def test_the_sweep_reports_its_health(bot, monkeypatch):
    cog, _ = cog_for(bot, monkeypatch)
    assert cog.loop_health("_sweep") == (None, None)
    cog.last_ok_at = "2026-10-07T12:00:00+00:00"
    assert cog.loop_health("_sweep") == ("2026-10-07T12:00:00+00:00", None)
    assert cog.loop_health("nothing") == (None, None)


async def test_slash_bracket_outside_a_server_says_so(bot, monkeypatch):
    cog, _ = cog_for(bot, monkeypatch)
    interaction = FakeInteraction(bot, ADA)
    interaction.guild = None
    await cog.bracket.callback(cog, interaction)
    assert interaction.said == [GUILD_ONLY]


async def test_slash_bracket_opens_the_panel(bot, monkeypatch):
    cog, _ = cog_for(bot, monkeypatch)
    interaction = FakeInteraction(bot, ADA)
    await cog.bracket.callback(cog, interaction)
    assert interaction.response.messages[0]["embed"].title == "Tournaments"


async def test_two_reconciles_at_boot_post_one_thread_and_one_starter_card(bot, guild, monkeypatch):
    outcome = await moves.create(bot, guild, who(guild, TO), {"name": "Knuck Up 12"})
    body = cog_module.Brackets._sweep.coro
    cog, _ = cog_for(bot, monkeypatch)

    await asyncio.gather(body(cog), cog.on_ready(), body(cog), cog.on_ready())

    thread = the_thread(bot, REHEARSAL)
    assert len(thread.messages) == 1
    assert (await store_.tournament(bot.db, GUILD, outcome.value))["message_id"] == thread.messages[
        0
    ].id


async def test_the_tick_runs_the_sweep_for_every_available_guild(bot, guild, monkeypatch):
    cog, _ = cog_for(bot, monkeypatch)
    seen = []

    async def sweep(found_bot, found_guild, **given):
        seen.append(found_guild.id)

    monkeypatch.setattr(cog_module, "sweep", sweep)
    guild.unavailable = False
    await cog.tick()
    guild.unavailable = True
    await cog.tick()
    assert seen == [GUILD]


async def test_a_failed_tick_is_recorded_and_a_good_one_clears_it(bot, monkeypatch):
    body = cog_module.Brackets._sweep.coro
    cog, _ = cog_for(bot, monkeypatch)

    async def broken():
        raise RuntimeError("the database went away")

    monkeypatch.setattr(cog, "tick", broken)
    await body(cog)
    assert cog.last_error == "RuntimeError: the database went away"

    async def fine():
        return None

    monkeypatch.setattr(cog, "tick", fine)
    await body(cog)
    assert cog.last_error is None and cog.last_ok_at


async def test_the_first_tick_after_boot_is_the_full_pass(bot, guild, monkeypatch):
    await running(bot, guild, ADA, BEA, format="single")
    thread = the_thread(bot)
    thread.delete(thread.cards[0])
    bot.forget()
    body = cog_module.Brackets._sweep.coro
    cog, _ = cog_for(bot, monkeypatch)

    await body(cog)
    await cog.on_ready()

    [card] = thread.cards
    assert "Ready to play" in card.embed.description
    edits = card.edits
    await body(cog)
    assert card.edits == edits


async def test_a_reconnect_makes_the_next_tick_a_full_pass_again(bot, guild, monkeypatch):
    await running(bot, guild, ADA, BEA, format="single")
    thread = the_thread(bot)
    body = cog_module.Brackets._sweep.coro
    cog, _ = cog_for(bot, monkeypatch)
    await cog.on_ready()
    await body(cog)
    thread.delete(thread.cards[0])
    await body(cog)
    assert thread.cards == []

    await cog.on_ready()
    await body(cog)

    assert len(thread.cards) == 1
