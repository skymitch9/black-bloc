import re
from datetime import timedelta

import pytest

from black_bloc import marathon as mt
from black_bloc import marathon_people as mp
from black_bloc.cogs.content import marathon as cogmod
from black_bloc.cogs.content import marathon_people as people
from black_bloc.cogs.content.marathon import create_marathon, get_marathon, runs_of
from black_bloc.cogs.content.spotlight import channel_by_login, forget_spotlight
from black_bloc.marathon_sources import Person, Run
from tests.cogs.content.test_marathon import (  # noqa: F401
    NOW,
    SKY,
    URL,
    FakeClient,
    Member,
    at,
    bot,
)
from tests.cogs.content.test_spotlight import (
    GUILD,
    FakeActor,
    FakeInteraction,
    details_of,
    kinds,
)

CASEY = 7001
PEAS = 7002


class Named:
    def __init__(self, user_id, name):
        self.id = user_id
        self.name = name
        self.display_name = name.title()
        self.bot = False


def a_run(ident, start, game, people_on):
    return Run(
        str(ident),
        ident,
        game,
        game,
        "Any%",
        at(start),
        at(start + 60),
        3600,
        tuple(Person(*one) for one in people_on),
    )


RACE = [
    ("Sky", "skyruns", "runner"),
    ("TheKing", "thekingspride", "runner"),
    ("Peas", "peasplays", "runner"),
    ("Bobbeigh", "bobbeightv", "runner"),
]
SCHEDULE = [
    a_run(1, -120, "Halo 2", [("Somebody", None, "runner")]),
    a_run(2, 30, "Super Mario 64", RACE),
    a_run(3, 1500, "Celeste", [("Sky", "skyruns", "runner"), ("Commentary", None, "host")]),
    a_run(4, 90, "Blaster Master", [("Loner", None, "runner")]),
]


@pytest.fixture
def cog(bot):  # noqa: F811
    made = cogmod.Marathons(bot)
    made.client = FakeClient(runs=SCHEDULE)
    made.clock = lambda: NOW
    bot.cogs[cogmod.COG_NAME] = made
    bot.guild.members = [Named(PEAS, "peasplays"), Named(CASEY, "bobbeigh")]
    return made


async def added(bot):  # noqa: F811
    outcome = await create_marathon(bot, bot.guild, FakeActor(), name="AGDQ 2027", url=URL)
    assert outcome.ok, outcome.message
    return outcome.value


async def state_of(bot, marathon):  # noqa: F811
    fresh = await get_marathon(bot.db, GUILD, marathon["id"])
    return await people.people_state(bot, bot.guild, fresh)


async def run_named(bot, marathon, game):  # noqa: F811
    return next(one for one in await runs_of(bot.db, marathon["id"]) if one["game"] == game)


def names(rows):
    return [one["name"] for one in rows]


async def test_the_board_puts_baf_on_top_and_everyone_else_below(bot, cog):  # noqa: F811
    marathon = await added(bot)
    state = await state_of(bot, marathon)
    assert names(state["baf"]) == ["Sky"]
    sky = state["baf"][0]
    assert [one["game"] for one in sky["runs"]] == ["Super Mario 64", "Celeste"]
    assert sky["matched_by"] == mp.BY_LINK
    assert "TheKing" in names(state["others"]) and "Bobbeigh" in names(state["others"])
    bob = next(one for one in state["others"] if one["name"] == "Bobbeigh")
    assert bob["looks_like"] == {"username": "bobbeigh", "user_id": CASEY}


async def test_link_to_a_member_moves_them_into_baf_and_makes_the_run_ours(bot, cog):  # noqa: F811
    marathon = await added(bot)
    loner = await run_named(bot, marathon, "Blaster Master")
    assert not mt.is_ours(loner)
    outcome = await cogmod.pair_runner(bot, bot.guild, FakeActor(), marathon, "Loner", PEAS)
    assert outcome.ok
    state = await state_of(bot, marathon)
    loner_row = next(one for one in state["baf"] if one["name"] == "Loner")
    assert loner_row["user_id"] == PEAS and loner_row["matched_by"] == mp.BY_PAIRING
    assert loner_row["pairing_id"]
    loner = await run_named(bot, marathon, "Blaster Master")
    assert mt.is_ours(loner)
    undone = await people.unlink_person(bot, bot.guild, FakeActor(), marathon, "Loner")
    assert undone.ok
    assert "Loner" in names((await state_of(bot, marathon))["others"])


async def test_spotlight_from_the_baf_block_spans_every_run_through_the_spotlight_path(
    bot,  # noqa: F811
    cog,
):
    marathon = await added(bot)
    outcome = await people.spotlight_runner(bot, bot.guild, FakeActor(), marathon, "skyruns")
    assert outcome.ok, outcome.message
    row = await channel_by_login(bot.db, GUILD, "skyruns")
    assert row is not None and row["spotlight"] == 1 and row["announce"] == 1
    assert row["event_id"] is None and row["note"] == "Sky at AGDQ 2027"
    assert row["expires_at"] == (NOW + timedelta(minutes=1500 + 60 + 120)).isoformat()
    assert row["starts_at"] is None
    assert "golive.spotlight_added" in await kinds(bot.db)
    spotlit = await details_of(bot.db, "marathon.runner_spotlit")
    assert spotlit["login"] == "skyruns" and spotlit["spotlight_id"] == row["id"]
    sky = (await state_of(bot, marathon))["baf"][0]
    assert sky["spotlight_id"] == row["id"] and sky["spotlight_until"] == row["expires_at"]


async def test_spotlight_from_a_slot_honours_that_runs_window(bot, cog):  # noqa: F811
    marathon = await added(bot)
    celeste = await run_named(bot, marathon, "Celeste")
    outcome = await people.spotlight_runner(
        bot, bot.guild, FakeActor(), marathon, "Sky", run_id=celeste["id"]
    )
    assert outcome.ok, outcome.message
    row = await channel_by_login(bot.db, GUILD, "skyruns")
    assert row["starts_at"] == (NOW + timedelta(minutes=1500 - 120)).isoformat()
    assert row["expires_at"] == (NOW + timedelta(minutes=1560 + 120)).isoformat()


async def test_stop_spotlighting_removes_the_row_the_go_live_way_and_forgets_it(bot, cog):  # noqa: F811
    marathon = await added(bot)
    await people.spotlight_runner(bot, bot.guild, FakeActor(), marathon, "skyruns")
    outcome = await people.unspotlight_runner(bot, bot.guild, FakeActor(), marathon, "skyruns")
    assert outcome.ok and "no longer spotlit" in outcome.message
    assert await channel_by_login(bot.db, GUILD, "skyruns") is None
    assert "golive.spotlight_removed" in await kinds(bot.db)
    assert (await details_of(bot.db, "marathon.runner_unspotlit"))["row_was_gone"] is False
    assert await people.remembered_of(bot.db, marathon["id"]) == {}
    again = await people.unspotlight_runner(bot, bot.guild, FakeActor(), marathon, "skyruns")
    assert not again.ok and again.status == 404


async def test_a_row_removed_on_go_live_is_forgotten_without_a_second_removal(bot, cog):  # noqa: F811
    marathon = await added(bot)
    done = await people.spotlight_runner(bot, bot.guild, FakeActor(), marathon, "skyruns")
    await forget_spotlight(bot, bot.guild, FakeActor(), done.value["spotlight_id"])
    state = await state_of(bot, marathon)
    assert state["baf"][0]["spotlight_id"] is None and state["baf"][0]["channel_id"] is None
    outcome = await people.unspotlight_runner(bot, bot.guild, FakeActor(), marathon, "skyruns")
    assert outcome.ok and "already off the Go-live page" in outcome.message


async def test_an_existing_channel_row_is_recognised_and_never_doubled(bot, cog):  # noqa: F811
    marathon = await added(bot)
    await people.spotlight_runner(bot, bot.guild, FakeActor(), marathon, "skyruns")
    other = await create_marathon(
        bot, bot.guild, FakeActor(), name="SGDQ", url="https://gamesdonequick.com/schedule/75"
    )
    state = await state_of(bot, other.value)
    assert state["baf"][0]["channel_id"] and state["baf"][0]["spotlight_id"] is None
    refused = await people.spotlight_runner(bot, bot.guild, FakeActor(), other.value, "skyruns")
    assert not refused.ok and refused.status == 409
    assert "already on the Go-live page" in refused.message


async def test_refusals_are_in_words_no_login_nobody_and_runs_over(bot, cog):  # noqa: F811
    marathon = await added(bot)
    no_login = await people.spotlight_runner(bot, bot.guild, FakeActor(), marathon, "Loner")
    assert no_login.status == 422 and "no Twitch channel" in no_login.message
    nobody = await people.spotlight_runner(bot, bot.guild, FakeActor(), marathon, "ghost")
    assert nobody.status == 404 and "Nobody called" in nobody.message
    cog.client.runs_given = [a_run(9, -600, "Old", [("Past", "pastrunner", "runner")])]
    await cog.refresh(bot.guild, await get_marathon(bot.db, GUILD, marathon["id"]))
    over = await people.spotlight_runner(bot, bot.guild, FakeActor(), marathon, "pastrunner")
    assert over.status == 409 and "are over" in over.message
    assert await channel_by_login(bot.db, GUILD, "pastrunner") is None


async def test_removing_the_marathon_forgets_its_spotlights_and_keeps_the_rows(bot, cog):  # noqa: F811
    marathon = await added(bot)
    await people.spotlight_runner(bot, bot.guild, FakeActor(), marathon, "skyruns")
    await cogmod.remove_marathon(bot, bot.guild, FakeActor(), marathon)
    assert await people.remembered_of(bot.db, marathon["id"]) == {}
    assert await channel_by_login(bot.db, GUILD, "skyruns") is not None


# --- /event ▸ Marathons… ▸ People… -------------------------------------------------------------


def labels_of(view):
    return [getattr(one, "label", None) for one in view.children]


async def test_a_member_reads_the_baf_block_and_nothing_more(bot, cog):  # noqa: F811
    marathon = await added(bot)
    bot.store.is_staff = lambda member: False
    _, root = await cogmod.build_panel(bot, bot.guild, Member(42))
    assert any(isinstance(one, people.MarathonPeoplePick) for one in root.children)
    embed, view = await people.build_people(bot, bot.guild, Member(42), marathon["id"])
    assert "<@9001>" in embed.description and "twitch.tv/skyruns" in embed.description
    assert "TheKing" not in embed.description and "The schedule" not in embed.description
    assert labels_of(view) == ["Back"]
    assert view.render_again is not None


async def test_staff_pick_a_day_then_a_slot_then_a_person_and_the_race_is_one_slot(bot, cog):  # noqa: F811
    marathon = await added(bot)
    _, card = await cogmod.build_card(bot, bot.guild, marathon["id"])
    assert "People…" in labels_of(card)
    embed, view = await people.build_people(bot, bot.guild, FakeActor(), marathon["id"])
    assert "The schedule" in embed.description
    days = next(one for one in view.children if isinstance(one, people.DayPick))
    first = days.options[0].value
    assert "BaF" in days.options[0].label
    _, view = await people.build_people(bot, bot.guild, FakeActor(), marathon["id"], day=first)
    slots = next(one for one in view.children if isinstance(one, people.SlotPick))
    race = next(one for one in slots.options if "Super Mario 64" in one.label)
    assert race.description.startswith("Sky ✦BaF, TheKing, Peas, Bobbeigh")
    embed, view = await people.build_people(
        bot, bot.guild, FakeActor(), marathon["id"], run_id=race.value
    )
    assert embed.description.count("\n") >= 5
    assert "looks like **@bobbeigh**" in embed.description
    pick = next(one for one in view.children if isinstance(one, people.PersonPick))
    assert [one.value for one in pick.options] == ["Sky", "TheKing", "Peas", "Bobbeigh"]
    _, view = await people.build_people(
        bot, bot.guild, FakeActor(), marathon["id"], run_id=race.value, person="TheKing"
    )
    assert any(isinstance(one, people.LinkPick) for one in view.children)
    assert "Spotlight" in labels_of(view)
    _, view = await people.build_people(
        bot, bot.guild, FakeActor(), marathon["id"], run_id=race.value, person="Bobbeigh"
    )
    assert "Link @bobbeigh" in labels_of(view) and "Unlink" not in labels_of(view)


async def test_the_slot_view_links_a_member_with_the_user_select(bot, cog):  # noqa: F811
    marathon = await added(bot)
    race = await run_named(bot, marathon, "Super Mario 64")
    _, view = await people.build_people(
        bot, bot.guild, FakeActor(), marathon["id"], run_id=race["id"], person="TheKing"
    )
    interaction = FakeInteraction(bot, FakeActor(), bot.guild)
    await people.people_move(
        interaction,
        view,
        people.doing_for(people.LINK_NEAR, "TheKing", race["id"], PEAS),
    )
    assert "TheKing" in names((await state_of(bot, marathon))["baf"])
    assert interaction.view is not None and interaction.view.run_id == race["id"]
    assert "<@7002>" in interaction.words


async def test_the_notice_people_button_rebuilds_from_its_custom_id_and_opens_privately(
    bot,  # noqa: F811
    cog,
):
    marathon = await added(bot)
    view = people.with_people(None, marathon["id"])
    custom = view.children[0].item.custom_id
    match = re.fullmatch(people.PEOPLE_TEMPLATE, custom)
    button = await people.PeopleButton.from_custom_id(None, None, match)
    assert button.marathon_id == marathon["id"]
    interaction = FakeInteraction(bot, FakeActor(), bot.guild)
    await button.on_click(interaction)
    sent = interaction.response.messages[-1]
    assert sent["content"] is None
    assert isinstance(sent["kwargs"]["view"], people.PeoplePanel)
    assert "<@9001>" in sent["kwargs"]["embed"].description
