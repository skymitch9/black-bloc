from types import SimpleNamespace

import discord
import pytest

from black_bloc import sticky as rules
from black_bloc import sticky_panel as panel
from black_bloc.command_errors import render_again_of
from black_bloc.config import load_settings
from black_bloc.panels import KEEP_IT
from black_bloc.settings_store import SettingsStore
from black_bloc.sticky_posts import desk_of

GUILD = 7
RUNS = 333
HELP = 334
HOME = 444
WORDS = "How to submit a run."


class FakeMessage:
    def __init__(self, channel, message_id, content):
        self.channel = channel
        self.id = message_id
        self.content = content

    async def delete(self):
        if self in self.channel.messages:
            self.channel.messages.remove(self)


class FakeChannel:
    _next = 7000

    def __init__(self, channel_id, name):
        self.id = channel_id
        self.name = name
        self.type = SimpleNamespace(name="text")
        self.messages = []

    async def send(self, content=None, **kwargs):
        FakeChannel._next += 1
        message = FakeMessage(self, FakeChannel._next, content)
        self.messages.append(message)
        return message

    def get_partial_message(self, message_id):
        found = next((one for one in self.messages if one.id == int(message_id)), None)
        return found if found is not None else FakeMessage(self, int(message_id), "")


class FakeGuild:
    def __init__(self):
        self.id = GUILD
        self.roles = []
        self.channels = {
            RUNS: FakeChannel(RUNS, "runs"),
            HELP: FakeChannel(HELP, "help"),
            HOME: FakeChannel(HOME, "welcome-test"),
        }

    def get_channel(self, channel_id):
        return self.channels.get(int(channel_id))


class FakeResponse:
    def __init__(self):
        self.messages = []
        self.modals = []
        self.deferred = False

    def is_done(self):
        return self.deferred or bool(self.messages)

    async def send_message(self, content=None, ephemeral=False, **kwargs):
        self.messages.append({"content": content, "ephemeral": ephemeral, **kwargs})

    async def send_modal(self, modal):
        self.modals.append(modal)
        self.deferred = True

    async def defer(self, ephemeral=False):
        self.deferred = True


class FakeFollowup:
    def __init__(self, response):
        self.response = response

    async def send(self, content=None, ephemeral=False, **kwargs):
        self.response.messages.append({"content": content, "ephemeral": ephemeral, **kwargs})


class FakeInteraction:
    def __init__(self, bot, user):
        self.client = bot
        self.user = user
        self.guild = bot.guild
        self.response = FakeResponse()
        self.followup = FakeFollowup(self.response)
        self.edits = []

    async def edit_original_response(self, **kwargs):
        self.edits.append(kwargs)
        return SimpleNamespace(id=9500, embeds=[kwargs.get("embed")])

    @property
    def view(self):
        return self.edits[-1]["view"]

    @property
    def embed(self):
        return self.edits[-1]["embed"]

    @property
    def sent(self):
        said = [one["content"] for one in self.response.messages if one.get("content")]
        return said[-1] if said else None


@pytest.fixture
async def bot(db, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    store = SettingsStore(db, load_settings(_env_file=None, site_origin="https://bb.test"))
    await store.load()
    await store.set(GUILD, "shadow_channel_id", HOME)
    guild = FakeGuild()
    return SimpleNamespace(
        db=db,
        store=store,
        settings=SimpleNamespace(origin="https://bb.test"),
        guard=None,
        guild=guild,
        guilds=[guild],
        user=SimpleNamespace(id=42),
        get_channel=guild.get_channel,
    )


@pytest.fixture
def lead(bot):
    return SimpleNamespace(
        id=1,
        guild=bot.guild,
        roles=[],
        guild_permissions=SimpleNamespace(manage_guild=True),
    )


@pytest.fixture
def member(bot):
    return SimpleNamespace(
        id=2,
        guild=bot.guild,
        roles=[],
        guild_permissions=SimpleNamespace(manage_guild=False),
    )


def labels(view):
    return [one.label for one in view.children if getattr(one, "label", None)]


def control(view, kind):
    return next(one for one in view.children if isinstance(one, kind))


def button(view, label):
    return next(one for one in view.children if getattr(one, "label", None) == label)


async def root(bot, who):
    interaction = FakeInteraction(bot, who)
    await panel.back_to_root(interaction)
    return interaction


async def press(bot, who, view, label):
    interaction = FakeInteraction(bot, who)
    await button(view, label).callback(interaction)
    return interaction


async def pick(bot, who, view, kind, values):
    interaction = FakeInteraction(bot, who)
    picker = control(view, kind)
    picker._values = values
    await picker.callback(interaction)
    return interaction


async def write(bot, who, modal, text):
    interaction = FakeInteraction(bot, who)
    modal.words._value = text
    await modal.on_submit(interaction)
    return interaction


async def a_sticky(bot, lead, channel_id=RUNS, mode="on"):
    await bot.store.set(GUILD, "sticky_mode", mode)
    await desk_of(bot).save(bot.guild, channel_id, WORDS, lead)


async def test_an_empty_panel_has_the_add_picker_the_mode_and_no_sticky_picker(bot, lead):
    opened = await root(bot, lead)

    assert opened.embed.title == rules.PANEL_TITLE
    assert opened.embed.description == f"**mode** — shadow\n\n{rules.NONE_YET}"
    kinds = [type(one) for one in opened.view.children]
    assert panel.StickyPick not in kinds
    assert panel.AddPick in kinds and panel.ModePick in kinds
    assert labels(opened.view) == ["Refresh", "Logs", "Open on the site"]
    assert button(opened.view, "Open on the site").url == "https://bb.test/posts.html#sect-sticky"
    assert control(opened.view, panel.AddPick).channel_types == [
        discord.ChannelType.text,
        discord.ChannelType.news,
    ]


async def test_adding_is_pick_a_channel_then_type_the_words(bot, lead):
    opened = await root(bot, lead)

    picked = await pick(bot, lead, opened.view, panel.AddPick, [SimpleNamespace(id=RUNS)])
    modal = picked.response.modals[-1]
    assert modal.title == rules.WORDS_TITLE and modal.words.default is None
    saved = await write(bot, lead, modal, WORDS)

    assert (await rules.get_row(bot.db, GUILD, RUNS))["text"] == WORDS
    assert saved.embed.title == "#runs" and saved.embed.description.startswith(WORDS)
    assert "rehearsing" in saved.embed.description
    assert "shadow" in saved.sent
    assert labels(saved.view) == ["Edit…", "Pause", "Remove", "Back"]
    assert len(bot.guild.get_channel(HOME).messages) == 1


async def test_picking_a_channel_that_has_one_opens_its_words_to_edit(bot, lead):
    await a_sticky(bot, lead)
    opened = await root(bot, lead)

    picked = await pick(bot, lead, opened.view, panel.AddPick, [SimpleNamespace(id=RUNS)])

    assert picked.response.modals[-1].words.default == WORDS


async def test_the_list_opens_a_card_whose_buttons_are_only_the_valid_moves(bot, lead):
    await a_sticky(bot, lead)
    opened = await root(bot, lead)
    assert f"<#{RUNS}> — live" in opened.embed.description
    options = control(opened.view, panel.StickyPick).options
    assert [(one.label, one.value) for one in options] == [(f"#runs · {WORDS}", str(RUNS))]

    card = await pick(bot, lead, opened.view, panel.StickyPick, [str(RUNS)])
    assert labels(card.view) == ["Edit…", "Pause", "Remove", "Back"]

    paused = await press(bot, lead, card.view, "Pause")
    assert labels(paused.view) == ["Edit…", "Resume", "Remove", "Back"]
    assert bot.guild.get_channel(RUNS).messages == []
    assert paused.sent == rules.PAUSED_NOW.format(where=RUNS)

    resumed = await press(bot, lead, paused.view, "Resume")
    assert labels(resumed.view) == ["Edit…", "Pause", "Remove", "Back"]
    assert len(bot.guild.get_channel(RUNS).messages) == 1


async def test_a_stopped_sticky_offers_try_again_and_says_why(bot, lead):
    await a_sticky(bot, lead)
    await rules.write_trouble(bot.db, GUILD, RUNS, "Black Bloc is missing Send Messages.")
    opened = await root(bot, lead)

    card = await pick(bot, lead, opened.view, panel.StickyPick, [str(RUNS)])
    assert labels(card.view) == ["Edit…", "Try again", "Remove", "Back"]
    assert "missing Send Messages" in card.embed.description

    again = await press(bot, lead, card.view, "Try again")
    assert labels(again.view) == ["Edit…", "Pause", "Remove", "Back"]
    assert (await rules.get_row(bot.db, GUILD, RUNS))["trouble"] is None


async def test_remove_asks_first_and_keep_it_changes_nothing(bot, lead):
    await a_sticky(bot, lead)
    opened = await root(bot, lead)
    card = await pick(bot, lead, opened.view, panel.StickyPick, [str(RUNS)])

    asked = await press(bot, lead, card.view, "Remove")
    assert labels(asked.view) == [rules.REMOVE_YES, "Back"]
    assert asked.embed.fields[-1].value == rules.REMOVE_QUESTION.format(channel_id=RUNS)
    assert KEEP_IT not in labels(asked.view)

    kept = await press(bot, lead, asked.view, "Back")
    assert labels(kept.view) == ["Edit…", "Pause", "Remove", "Back"]
    assert await rules.get_row(bot.db, GUILD, RUNS) is not None

    asked = await press(bot, lead, kept.view, "Remove")
    gone = await press(bot, lead, asked.view, rules.REMOVE_YES)

    assert await rules.get_row(bot.db, GUILD, RUNS) is None
    assert bot.guild.get_channel(RUNS).messages == []
    assert gone.embed.title == rules.PANEL_TITLE
    assert gone.sent == rules.REMOVED_NOW.format(channel_id=RUNS)


async def test_the_mode_picker_sets_the_mode_and_redraws_the_list(bot, lead):
    opened = await root(bot, lead)
    assert [one.default for one in control(opened.view, panel.ModePick).options] == [
        False,
        True,
        False,
    ]

    changed = await pick(bot, lead, opened.view, panel.ModePick, ["on"])

    assert bot.store.get(GUILD, "sticky_mode") == "on"
    assert changed.embed.description.startswith("**mode** — on")
    assert changed.sent == rules.MODE_SET.format(mode="on")


async def test_a_refused_save_is_answered_and_the_card_is_left_alone(bot, lead):
    await a_sticky(bot, lead)
    modal = panel.WordsModal(RUNS, WORDS)

    refused = await write(bot, lead, modal, "   ")

    assert refused.sent == rules.NO_WORDS and refused.edits == []
    assert (await rules.get_row(bot.db, GUILD, RUNS))["text"] == WORDS


async def test_every_move_asks_again_whether_the_presser_is_staff(bot, lead, member):
    await a_sticky(bot, lead)
    opened = await root(bot, lead)
    card = await pick(bot, lead, opened.view, panel.StickyPick, [str(RUNS)])

    for label in ("Pause", "Remove", "Edit…", "Back"):
        refused = await press(bot, member, card.view, label)
        assert "staff only" in refused.sent
        assert refused.edits == [] and refused.response.modals == []
    added = await pick(bot, member, opened.view, panel.AddPick, [SimpleNamespace(id=HELP)])
    assert "staff only" in added.sent and added.response.modals == []
    assert (await rules.get_row(bot.db, GUILD, RUNS))["paused"] == 0


async def test_a_card_whose_sticky_is_gone_lands_back_on_the_list(bot, lead):
    await a_sticky(bot, lead)
    opened = await root(bot, lead)
    card = await pick(bot, lead, opened.view, panel.StickyPick, [str(RUNS)])
    await desk_of(bot).remove(bot.guild, RUNS, lead)

    asked = await press(bot, lead, card.view, "Remove")

    assert asked.embed.title == rules.PANEL_TITLE and asked.sent == rules.NO_STICKY


async def test_a_panel_and_its_modal_can_both_be_drawn_again_after_an_error(bot, lead):
    await a_sticky(bot, lead)
    opened = await root(bot, lead)
    card = await pick(bot, lead, opened.view, panel.StickyPick, [str(RUNS)])

    assert render_again_of(opened.view) is not None
    assert render_again_of(panel.WordsModal(RUNS, WORDS, card.view)) is not None
    again = FakeInteraction(bot, lead)
    await render_again_of(card.view)(again)
    assert again.embed.title == "#runs"
    back = FakeInteraction(bot, lead)
    await render_again_of(opened.view)(back)
    assert back.embed.title == rules.PANEL_TITLE


async def test_more_stickies_than_one_picker_holds_says_so(bot, lead):
    for ident in range(1000, 1030):
        await rules.write_words(bot.db, GUILD, ident, f"words {ident}", 1)

    opened = await root(bot, lead)
    picker = control(opened.view, panel.StickyPick)

    assert len(picker.options) == 25
    assert picker.placeholder == "25 of 30 — the rest are on the site"
    assert len(opened.embed.description) <= 4000
