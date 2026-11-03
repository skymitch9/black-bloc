from types import SimpleNamespace

import discord
import pytest

from black_bloc import ninja
from black_bloc import ninja_panel as panel
from black_bloc import ninja_store as store
from tests.ninja_fakes import GUILD, PT, REAL, STAFF_ID, YATO, FakeInteraction, kinds, ninja_bot
from tests.questions_fakes import FakeMember


@pytest.fixture
async def bot(db, monkeypatch):
    return await ninja_bot(db, monkeypatch)


@pytest.fixture
def staff(bot):
    return bot.guild.get_member(STAFF_ID)


def labels(view):
    return [item.label for item in view.children if isinstance(item, discord.ui.Button)]


def of(view, kind):
    return [item for item in view.children if isinstance(item, kind)]


async def marked(bot, staff, *users, posts="1"):
    return await ninja.mark(bot, bot.guild, staff, list(users or (PT,)), REAL, posts, "")


def test_the_mode_button_is_the_move_away_from_the_mode_in_force():
    assert panel.root_moves("on") == ["mark", "off", "refresh"]
    assert panel.root_moves("off") == ["mark", "on", "refresh"]


def test_next_renders_only_once_somebody_and_somewhere_are_picked():
    assert panel.card_moves(panel.Draft()) == ["back"]
    assert panel.card_moves(panel.Draft(user_ids=[PT])) == ["back"]
    assert panel.card_moves(panel.Draft(channel_id=REAL)) == ["back"]
    assert panel.card_moves(panel.Draft(user_ids=[PT], channel_id=REAL)) == ["next", "back"]


async def test_the_root_lists_the_marks_the_emote_and_the_mode(bot, staff):
    embed, view = await panel.build_root(bot, bot.guild)
    assert embed.title == "Ninja marks"
    assert "Nobody is marked." in embed.description
    assert (
        "\U0001f977\U0001f3ff" in embed.description and "**ninja_mode** — on" in embed.description
    )
    assert labels(view) == ["Mark someone", "Turn off", "Refresh"]
    assert not of(view, panel.EndPick)

    await marked(bot, staff, PT, YATO, posts="3")
    embed, view = await panel.build_root(bot, bot.guild)
    assert f"<@{PT}> · <#{REAL}> · 3 post(s) · by <@{STAFF_ID}>" in embed.description
    [pick] = of(view, panel.EndPick)
    assert [option.label for option in pick.options] == [
        f"#1 · m{PT} · #qotw",
        f"#2 · m{YATO} · #qotw",
    ]


async def test_mark_someone_opens_a_card_on_the_question_channel(bot, staff):
    interaction = FakeInteraction(bot, staff)
    _, view = await panel.build_root(bot, bot.guild)
    [mark] = [item for item in view.children if getattr(item, "name", "") == "mark"]

    await mark.callback(interaction)

    card = interaction.edits[-1]["view"]
    assert card.draft.channel_id == REAL and card.draft.user_ids == []
    [where] = of(card, panel.WherePick)
    assert [one.id for one in where.default_values] == [REAL]
    [who] = of(card, panel.WhoPick)
    assert who.max_values == 25
    assert labels(card) == ["Back"]


async def test_picking_members_brings_next_and_the_form_marks_them(bot, staff):
    draft = panel.Draft(channel_id=REAL)
    _, card = panel.build_card(bot, bot.guild, draft)
    [who] = of(card, panel.WhoPick)
    who._values = [SimpleNamespace(id=PT), SimpleNamespace(id=YATO)]
    interaction = FakeInteraction(bot, staff)

    await who.callback(interaction)

    redrawn = interaction.edits[-1]["view"]
    assert labels(redrawn) == ["Next", "Back"]
    assert f"<@{PT}>, <@{YATO}> in <#{REAL}>" in interaction.edits[-1]["embed"].description
    [nxt] = [item for item in redrawn.children if getattr(item, "name", "") == "next"]
    opener = FakeInteraction(bot, staff)
    await nxt.callback(opener)
    [modal] = opener.response.modals
    assert modal.title == "How long"
    assert (modal.posts.default, modal.minutes.default) == ("1", None)
    assert modal.posts.placeholder == "No limit"

    modal.posts._value = "2"
    modal.minutes._value = "30"
    done = FakeInteraction(bot, staff)
    await modal.on_submit(done)

    assert done.said[0].startswith(f"<@{PT}>, <@{YATO}> marked in <#{REAL}> · 2 post(s) or until")
    assert len(await store.active(bot.db, GUILD)) == 2
    assert done.edits[-1]["embed"].title == "Ninja marks"


async def test_a_form_with_no_limit_is_refused_and_keeps_the_card(bot, staff):
    draft = panel.Draft(user_ids=[PT], channel_id=REAL)
    modal = panel.LimitsModal(bot, bot.guild, draft)
    modal.posts._value = ""
    modal.minutes._value = ""
    interaction = FakeInteraction(bot, staff)

    await modal.on_submit(interaction)

    assert interaction.said == [
        "Neither posts nor minutes is set, so nobody was marked. Set one or both."
    ]
    assert interaction.edits[-1]["view"].draft is draft
    assert await store.active(bot.db, GUILD) == []


async def test_end_from_the_panel_asks_then_ends(bot, staff):
    await marked(bot, staff)
    _, view = await panel.build_root(bot, bot.guild)
    [pick] = of(view, panel.EndPick)
    pick._values = [pick.options[0].value]
    interaction = FakeInteraction(bot, staff)

    await pick.callback(interaction)

    asked = interaction.edits[-1]
    assert f"End the mark on <@{PT}> in <#{REAL}>?" in asked["embed"].description
    yes, keep = asked["view"].children
    assert (yes.label, keep.label) == ("End", "Keep it")
    confirm = FakeInteraction(bot, staff)
    await yes.callback(confirm)

    assert confirm.said == [f"The mark on <@{PT}> in <#{REAL}> is ended."]
    assert await store.active(bot.db, GUILD) == []
    assert "ninja.ended" in await kinds(bot.db)


async def test_turn_off_and_on_from_the_panel_writes_the_setting(bot, staff):
    _, view = await panel.build_root(bot, bot.guild)
    [off] = [item for item in view.children if getattr(item, "name", "") == "off"]
    interaction = FakeInteraction(bot, staff)

    await off.callback(interaction)

    assert bot.store.get(GUILD, "ninja_mode") == "off"
    assert interaction.said == ["ninja_mode is off now."]
    assert "Turn on" in labels(interaction.edits[-1]["view"])
    assert "settings.set" in await kinds(bot.db)


async def test_somebody_who_is_not_staff_changes_nothing(bot):
    stranger = FakeMember(77)
    stranger.guild = bot.guild
    modal = panel.LimitsModal(bot, bot.guild, panel.Draft(user_ids=[PT], channel_id=REAL))
    modal.posts._value = "1"
    modal.minutes._value = ""
    interaction = FakeInteraction(bot, stranger)

    await modal.on_submit(interaction)

    assert await store.active(bot.db, GUILD) == []
    assert interaction.said and "staff only" in interaction.said[0]


async def test_every_word_on_the_panel_is_a_setting(bot, staff):
    await bot.store.set(GUILD, "ninja_mark_label", "Ninja someone")
    await bot.store.set(GUILD, "ninja_panel_title", "Ninjas")
    embed, view = await panel.build_root(bot, bot.guild)
    assert embed.title == "Ninjas" and labels(view)[0] == "Ninja someone"
