# ruff: noqa: F401, F811
import re

import pytest

from black_bloc import marathon_near_miss as mnm
from black_bloc.cogs.content import marathon_near_miss as near
from black_bloc.cogs.content.marathon import Marathons, create_marathon, pairings_of
from tests.cogs.content.test_marathon import SKY, URL, FakeClient, Member, a_run, bot, cog
from tests.cogs.content.test_marathon_people import Named
from tests.cogs.content.test_marathon_runner_posts import (
    SHADOW_CHANNEL,
    events_room,
    fresh,
    the_thread,
    tracked,
)
from tests.cogs.content.test_spotlight import GUILD, FakeActor, FakeInteraction, details_of, kinds

CASS = 909587042609025034
PEAS = 7002
ASKS = "on the schedule looks like"


@pytest.fixture(autouse=True)
def schedule(cog, bot):
    cog.client.runs_given = [
        a_run(3, 30, game="Super Metroid", people=(("Sky", "skyruns", "runner"),)),
        a_run(4, 90, game="Dr. Mario", people=(("cassasaur", "cassasaur", "runner"),)),
        a_run(5, 150, game="Tetris", people=(("cassasaur", "cassasaur", "runner"),)),
        a_run(6, 210, game="Kirby", people=(("Peas", "peasplay", "runner"),)),
    ]
    cass = Named(CASS, "cassasaur")
    cass.display_name = "Cass"
    bot.guild.members = [cass, Named(PEAS, "peasplays")]


async def followed(bot, cog):
    marathon = await tracked(bot)
    await cog.follow(bot.guild, await fresh(bot, marathon))
    return marathon


def asks(thread):
    return [one for one in thread.messages if ASKS in one.content]


def labels_of(message):
    view = message.kwargs.get("view")
    return [getattr(one, "item", one).label for one in view.children]


async def test_an_exact_username_match_posts_once_naming_never_pinging(bot, cog):
    marathon = await followed(bot, cog)
    await cog.follow(bot.guild, await fresh(bot, marathon))
    await cog.tick_once()

    posts = asks(the_thread(bot))
    assert len(posts) == 1
    post = posts[0]
    assert post.content == f"**cassasaur** on the schedule looks like <@{CASS}> (Cass) — link them?"
    said = post.kwargs["allowed_mentions"]
    assert said.users is False and said.roles is False and said.everyone is False
    assert labels_of(post) == ["Link (this marathon)", "Link everywhere", "Not them"]
    ids = [getattr(one, "item", one).custom_id for one in post.kwargs["view"].children]
    assert ids == [f"marathon:nearmiss:{marathon['id']}:{one}" for one in mnm.ACTIONS]
    posted = await details_of(bot.db, mnm.POSTED)
    assert posted["runner_key"] == "cassasaur" and posted["member_id"] == CASS
    assert (await kinds(bot.db)).count(mnm.POSTED) == 1
    assert await pairings_of(bot.db, GUILD) == []


async def test_a_fuzzy_near_miss_posts_nothing(bot, cog):
    await followed(bot, cog)
    assert not any("Peas" in one.content for one in asks(the_thread(bot)))


async def test_link_this_marathon_pairs_edits_and_brings_the_runner_post(bot, cog):
    marathon = await followed(bot, cog)
    post = asks(the_thread(bot))[0]

    outcome = await near.press(bot, bot.guild, FakeActor(), marathon["id"], post.id, mnm.HERE)

    assert outcome.ok
    pairings = await pairings_of(bot.db, GUILD)
    assert [(one["runner_name"], one["user_id"], one["marathon_id"]) for one in pairings] == [
        ("cassasaur", CASS, marathon["id"])
    ]
    assert post.content.startswith(f"**cassasaur** is <@{CASS}> (Cass) on **SS4C** — linked by")
    assert post.edits[-1]["view"] is None
    assert post.edits[-1]["allowed_mentions"].users is False
    runner_posts = [
        one
        for one in the_thread(bot).messages
        if "**Dr. Mario**" in one.content and f"<@{CASS}>" in one.content
    ]
    assert len(runner_posts) == 1
    resolved = await details_of(bot.db, mnm.RESOLVED)
    assert resolved["outcome"] == mnm.HERE and resolved["member_id"] == CASS


async def test_link_everywhere_pairs_on_every_marathon(bot, cog):
    marathon = await followed(bot, cog)
    post = asks(the_thread(bot))[0]

    await near.press(bot, bot.guild, FakeActor(), marathon["id"], post.id, mnm.EVERYWHERE)

    pairings = await pairings_of(bot.db, GUILD)
    assert [(one["user_id"], one["marathon_id"]) for one in pairings] == [(CASS, None)]
    assert "on every marathon" in post.content


async def test_not_them_dismisses_and_never_posts_again(bot, cog):
    marathon = await followed(bot, cog)
    post = asks(the_thread(bot))[0]

    outcome = await near.press(bot, bot.guild, FakeActor(), marathon["id"], post.id, mnm.NOT_THEM)

    assert outcome.ok and "stays unlinked" in outcome.message
    assert await pairings_of(bot.db, GUILD) == []
    assert "is not" in post.content and post.edits[-1]["view"] is None
    await cog.follow(bot.guild, await fresh(bot, marathon))
    await cog.tick_once()
    assert asks(the_thread(bot)) == []
    assert (await kinds(bot.db)).count(mnm.POSTED) == 1

    again = await near.press(bot, bot.guild, FakeActor(), marathon["id"], post.id, mnm.HERE)
    assert "already answered" in again.message
    assert await pairings_of(bot.db, GUILD) == []


async def test_an_untracked_marathon_posts_nothing(bot, cog):
    made = await create_marathon(bot, bot.guild, FakeActor(), name="SS4C", url=URL)
    await cog.follow(bot.guild, made.value)
    await cog.tick_once()
    assert mnm.POSTED not in await kinds(bot.db)
    assert mnm.WOULD_POST not in await kinds(bot.db)


async def test_the_key_off_posts_nothing(bot, cog):
    await bot.store.set(GUILD, "marathon_near_miss_posts", False)
    await followed(bot, cog)
    assert asks(the_thread(bot)) == []
    assert mnm.POSTED not in await kinds(bot.db)


async def test_shadow_posts_in_the_shadow_home_as_a_would_row(bot, cog):
    await bot.store.set(GUILD, "marathon_mode", "shadow")
    await followed(bot, cog)
    thread = bot.guild.channels[SHADOW_CHANNEL].threads[-1]
    assert len(asks(thread)) == 1
    assert mnm.WOULD_POST in await kinds(bot.db) and mnm.POSTED not in await kinds(bot.db)


async def test_the_buttons_are_staff_only_and_rebuild_from_their_custom_id(bot, cog):
    marathon = await followed(bot, cog)
    post = asks(the_thread(bot))[0]
    custom = mnm.custom_id(marathon["id"], mnm.HERE)
    button = await near.NearMissButton.from_custom_id(
        None, None, re.fullmatch(mnm.TEMPLATE, custom)
    )
    assert (button.marathon_id, button.action) == (marathon["id"], mnm.HERE)

    bot.store.is_staff = lambda member: False
    stranger = FakeInteraction(bot, Member(42), bot.guild)
    stranger.message = post
    await button.on_click(stranger)
    assert "staff only" in stranger.sent and await pairings_of(bot.db, GUILD) == []

    bot.store.is_staff = lambda member: True
    lead = FakeInteraction(bot, FakeActor(), bot.guild)
    lead.message = post
    await button.on_click(lead)
    assert len(await pairings_of(bot.db, GUILD)) == 1


async def test_a_press_on_an_unknown_post_is_refused_in_words(bot, cog):
    marathon = await followed(bot, cog)
    outcome = await near.press(bot, bot.guild, FakeActor(), marathon["id"], 999999, mnm.HERE)
    assert not outcome.ok and "no longer on record" in outcome.message


async def test_the_buttons_outlive_a_restart():
    registered = []
    made = Marathons.__new__(Marathons)
    made.bot = type("Bot", (), {"db": type("Db", (), {"is_connected": False})()})()
    made.bot.add_dynamic_items = lambda *items: registered.extend(items)
    await Marathons.cog_load(made)
    assert near.NearMissButton in registered
