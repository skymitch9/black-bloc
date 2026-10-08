import re
from datetime import timedelta

import pytest

from black_bloc import marathon as mt
from black_bloc import marathon_people as mp
from black_bloc.cogs.content import marathon as cogmod
from black_bloc.cogs.content import marathon_people as people
from black_bloc.cogs.content.marathon import create_marathon, get_marathon, runs_of
from black_bloc.cogs.content.marathon_archive import archive_marathon
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
from tests.cogs.content.test_marathon import a_run as show_run
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
    await archive_marathon(bot, bot.guild, FakeActor(), marathon)
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


JR = 125393218408939520
GDQUEER = [a_run(5, 240, "Spyro", [("Jr", "Jr", "runner")])]


async def jr_paired(bot, cog, login="junior_sm"):  # noqa: F811
    cog.client = FakeClient(runs=SCHEDULE + GDQUEER)
    marathon = await added(bot)
    outcome = await cogmod.pair_runner(
        bot, bot.guild, FakeActor(), marathon, "Jr", JR, twitch_login=login
    )
    assert outcome.ok, outcome.message
    return marathon


async def test_jr_s_twitch_fix_is_what_spotlight_uses_and_the_card_shows_it(bot, cog):  # noqa: F811
    marathon = await jr_paired(bot, cog)
    jr = next(one for one in (await state_of(bot, marathon))["baf"] if one["name"] == "Jr")
    assert (jr["login"], jr["sheet_login"], jr["user_id"]) == ("junior_sm", "Jr", JR)
    spyro = await run_named(bot, marathon, "Spyro")
    assert mt.people_of(spyro)[0]["login"] == "junior_sm"
    outcome = await people.spotlight_runner(bot, bot.guild, FakeActor(), marathon, "Jr")
    assert outcome.ok, outcome.message
    assert await channel_by_login(bot.db, GUILD, "junior_sm") is not None
    assert await channel_by_login(bot.db, GUILD, "jr") is None
    stopped = await people.unspotlight_runner(bot, bot.guild, FakeActor(), marathon, "jr")
    assert stopped.ok, stopped.message
    assert await channel_by_login(bot.db, GUILD, "junior_sm") is None


async def test_clearing_jr_s_fix_gives_back_the_sheets_login(bot, cog):  # noqa: F811
    marathon = await jr_paired(bot, cog)
    jr = next(one for one in (await state_of(bot, marathon))["baf"] if one["name"] == "Jr")
    pairing = await cogmod.pairing_by_id(bot.db, GUILD, jr["pairing_id"])
    cleared = await cogmod.set_pairing_login(bot, bot.guild, FakeActor(), marathon, pairing, "")
    assert cleared.ok and cleared.message == "**jr** is back to the schedule's Twitch channel."
    jr = next(one for one in (await state_of(bot, marathon))["baf"] if one["name"] == "Jr")
    assert (jr["login"], jr["sheet_login"]) == ("Jr", None)
    row = await details_of(bot.db, "marathon.pairing_login_set")
    assert (row["from"], row["to"]) == ("junior_sm", None)


async def test_a_bad_twitch_fix_is_refused_in_words_and_nothing_changes(bot, cog):  # noqa: F811
    marathon = await jr_paired(bot, cog)
    jr = next(one for one in (await state_of(bot, marathon))["baf"] if one["name"] == "Jr")
    pairing = await cogmod.pairing_by_id(bot.db, GUILD, jr["pairing_id"])
    refused = await cogmod.set_pairing_login(
        bot, bot.guild, FakeActor(), marathon, pairing, "junior sm!"
    )
    assert not refused.ok and refused.message.startswith(
        "**junior sm!** is not a Twitch channel name"
    )
    paired = await cogmod.pair_runner(
        bot, bot.guild, FakeActor(), marathon, "Jr", JR, twitch_login="no good"
    )
    assert not paired.ok and "is not a Twitch channel name" in paired.message
    assert (await cogmod.pairing_by_id(bot.db, GUILD, jr["pairing_id"]))["twitch_login"] == (
        "junior_sm"
    )


async def test_relinking_keeps_the_fix_unless_a_new_one_is_given(bot, cog):  # noqa: F811
    marathon = await jr_paired(bot, cog)
    again = await cogmod.pair_runner(bot, bot.guild, FakeActor(), marathon, "Jr", JR)
    assert again.ok
    assert (await cogmod.pairing_by_id(bot.db, GUILD, again.value))["twitch_login"] == "junior_sm"


async def test_an_everywhere_fix_reaches_every_active_schedule(bot, cog):  # noqa: F811
    cog.client = FakeClient(runs=SCHEDULE + GDQUEER)
    first = await added(bot)
    second = await create_marathon(
        bot, bot.guild, FakeActor(), name="GDQueer", url=URL.replace("74", "75")
    )
    assert second.ok, second.message
    paired = await cogmod.pair_runner(
        bot, bot.guild, FakeActor(), first, "Jr", JR, everywhere=True
    )
    pairing = await cogmod.pairing_by_id(bot.db, GUILD, paired.value)
    fixed = await cogmod.set_pairing_login(
        bot, bot.guild, FakeActor(), first, pairing, "junior_sm"
    )
    assert fixed.ok, fixed.message
    for marathon in (first, second.value):
        spyro = await run_named(bot, marathon, "Spyro")
        assert mt.people_of(spyro)[0]["login"] == "junior_sm"


async def test_the_slot_view_offers_twitch_name_for_a_linked_person(bot, cog):  # noqa: F811
    marathon = await jr_paired(bot, cog)
    spyro = await run_named(bot, marathon, "Spyro")
    embed, view = await people.build_people(
        bot, bot.guild, FakeActor(), marathon["id"], run_id=spyro["id"], person="Jr"
    )
    labels = [getattr(one, "label", None) for one in view.children]
    assert "Twitch name…" in labels
    assert "twitch.tv/junior_sm" in embed.description


async def test_a_baf_persons_slot_offers_opt_out_and_opt_back_in(bot, cog):  # noqa: F811
    from black_bloc import marathon_announce as ma
    from tests.cogs.content.test_marathon_host_highlights import ANARCHY, HOSTED_ONLY, show

    await bot.store.set(GUILD, "events_create_scheduled", False)
    marathon = await show(bot, cog, HOSTED_ONLY)
    run = (await runs_of(bot.db, marathon["id"]))[1]

    async def slot(person="anarchy"):
        _, view = await people.build_people(
            bot, bot.guild, FakeActor(), marathon["id"], run_id=run["id"], person=person
        )
        return [one for one in view.children if isinstance(one, people.PeopleMove)]

    (move,) = [one for one in await slot() if one.action == people.OPT_OUT]
    assert move.label == "Opt out of every run on this marathon" and move.user_id == ANARCHY
    said = await people.doing_for(move.action, "anarchy", run["id"], move.user_id)(
        bot, bot.guild, FakeActor(), marathon
    )
    assert said.ok and "is opted out of" in said.message
    assert ma.opted_out(await get_marathon(bot.db, GUILD, marathon["id"])) == {ANARCHY}
    (move,) = [one for one in await slot() if one.action == people.OPT_IN]
    assert move.label == "Opt back in to this marathon"
    said = await people.doing_for(move.action, "anarchy", run["id"], move.user_id)(
        bot, bot.guild, FakeActor(), marathon
    )
    assert said.ok and "is back in" in said.message
    assert ma.opted_out(await get_marathon(bot.db, GUILD, marathon["id"])) == set()
    assert not any(
        getattr(one, "action", None) in (people.OPT_OUT, people.OPT_IN)
        for one in await slot("Vee")
    )


MO = 8202
MIXED = [
    show_run(
        1,
        30,
        game="Alpha",
        people=(("Sky", "skyruns", "runner"), ("anarchy", "anarchyasf", "host")),
    ),
    show_run(
        2,
        90,
        game="Beta",
        people=(("anarchy", "anarchyasf", "runner"), ("Mo", "mohosts", "host")),
    ),
]


async def test_a_runner_a_host_and_both_get_one_set_of_moves_and_their_part_tag(
    bot,  # noqa: F811
    cog,  # noqa: F811
):
    from black_bloc.cogs.content.marathon import pair_runner
    from tests.cogs.content.test_marathon_host_highlights import show

    await bot.store.set(GUILD, "events_create_scheduled", False)
    marathon = await show(bot, cog, MIXED)
    for name, user_id in (("Sky", SKY), ("Mo", MO)):
        paired = await pair_runner(bot, bot.guild, FakeActor(), marathon, name, user_id)
        assert paired.ok, paired.message
    alpha, beta = await runs_of(bot.db, marathon["id"])

    async def slot(run, person):
        embed, view = await people.build_people(
            bot, bot.guild, FakeActor(), marathon["id"], run_id=run["id"], person=person
        )
        moves = sorted(
            one.action for one in view.children if isinstance(one, people.PeopleMove)
        )
        return (embed.description, moves)

    words, sky_moves = await slot(alpha, "Sky")
    assert f"<@{SKY}> (runs) ✦BaF" in words
    assert "(runs + hosts) ✦BaF" in words
    _, anarchy_moves = await slot(alpha, "anarchy")
    words, mo_moves = await slot(beta, "Mo")
    assert f"<@{MO}> (hosts) ✦BaF" in words
    assert sky_moves == anarchy_moves == mo_moves
    assert people.OPT_OUT in sky_moves and people.SPOTLIGHT in sky_moves
    state = await people.people_state(
        bot, bot.guild, await get_marathon(bot.db, GUILD, marathon["id"])
    )
    tags = {one["name"]: people.part_words(bot, bot.guild, one["parts"]) for one in state["baf"]}
    assert tags == {"Sky": "runs", "anarchy": "runs + hosts", "Mo": "hosts"}


async def test_a_baf_persons_slot_offers_this_runs_answer_and_their_at(bot, cog):  # noqa: F811
    from black_bloc import marathon_announce as ma
    from tests.cogs.content.test_marathon_host_highlights import ANARCHY, HOSTED_ONLY, show

    await bot.store.set(GUILD, "events_create_scheduled", False)
    marathon = await show(bot, cog, HOSTED_ONLY, hosts=False)
    run = (await runs_of(bot.db, marathon["id"]))[1]

    async def slot(person="anarchy"):
        embed, view = await people.build_people(
            bot, bot.guild, FakeActor(), marathon["id"], run_id=run["id"], person=person
        )
        moves = [one for one in view.children if isinstance(one, people.PeopleMove)]
        return embed.description, {one.action: one for one in moves}

    words, moves = await slot()
    assert moves[people.RUN_ANSWER].label == "Announce anarchy for this run"
    assert (moves[people.RUN_ANSWER].to, moves[people.RUN_ANSWER].row) == ("in", 3)
    assert moves[people.MENTION].label == "No @ for anarchy" and moves[people.MENTION].to == "plain"
    assert "anarchy: not announced for this run — host announcements are off" in words
    move = moves[people.RUN_ANSWER]
    said = await people.doing_for(move.action, "anarchy", run["id"], move.user_id, move.to)(
        bot, bot.guild, FakeActor(), marathon
    )
    assert said.ok and "is announced for" in said.message
    rows = await runs_of(bot.db, marathon["id"])
    assert ma.run_answers(rows[1]) == {ANARCHY: "in"} and ma.run_answers(rows[0]) == {}
    move = moves[people.MENTION]
    said = await people.doing_for(move.action, "anarchy", run["id"], move.user_id, move.to)(
        bot, bot.guild, FakeActor(), marathon
    )
    assert said.ok and "with no @" in said.message

    words, moves = await slot()
    assert moves[people.RUN_ANSWER].label == "anarchy: back to the default for this run"
    assert moves[people.MENTION].label == "@ anarchy again"
    assert "anarchy: announced for this run — set for this run · written without an @" in words
    _, others = await slot("Vee")
    assert people.RUN_ANSWER not in others and people.MENTION not in others
