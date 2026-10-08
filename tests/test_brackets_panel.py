# ruff: noqa: F401, F811
from __future__ import annotations

import pytest

from black_bloc import brackets_moves as moves
from black_bloc import brackets_panel as panel
from black_bloc import brackets_people as people
from black_bloc import brackets_sets as sets
from black_bloc import brackets_store as store_
from black_bloc import brackets_thread as thread_
from tests.test_brackets_buttons import FakeInteraction, fill, pressing
from tests.test_brackets_moves import ADA, BEA, CY, GUILD, STAFF, TO, rows, who
from tests.test_brackets_thread import (
    KNUCK_UP,
    REHEARSAL,
    bot,
    created,
    guild,
    home,
    moved,
    running,
    the_thread,
)


def labels(view):
    return [getattr(one, "label", None) or type(one).__name__ for one in view.children]


def item(view, label):
    return next(one for one in view.children if getattr(one, "label", None) == label)


def shown(press):
    return press.edits[-1]


async def press(view, label, interaction):
    await item(view, label).callback(interaction)
    return shown(interaction)


async def tournament(bot, guild, user_id, tid):
    return await panel.build_tournament(bot, guild, guild.get_member(user_id), tid)


async def test_a_member_sees_open_tournaments_and_no_create(bot, guild):
    draft = await created(bot, guild)
    open_ = await created(bot, guild, name="Friday Fights")
    await moved(bot, guild, open_, moves.open_signups)

    embed, view = await panel.build_home(bot, guild, guild.get_member(ADA))

    assert embed.title == "Tournaments"
    assert embed.description == "**Friday Fights** · open for sign-ups · 0 entrant(s)"
    assert labels(view) == ["TournamentPick"]
    assert [one.value for one in view.children[0].options] == [str(open_)]
    assert draft


async def test_an_organiser_sees_every_tournament_and_create(bot, guild):
    await created(bot, guild)
    embed, view = await panel.build_home(bot, guild, guild.get_member(TO))
    assert "**Knuck Up 12** · a draft · 0 entrant(s)" in embed.description
    assert labels(view) == ["TournamentPick", "Create…"]


async def test_nobody_with_nothing_to_show_gets_one_line(bot, guild):
    embed, view = await panel.build_home(bot, guild, guild.get_member(ADA))
    assert embed.description == "No tournaments right now."
    assert labels(view) == []


async def test_slash_bracket_opens_an_ephemeral_panel_that_pings_nobody(bot, guild):
    interaction = FakeInteraction(bot, ADA)
    await panel.open_panel(interaction)
    sent = interaction.response.messages[0]
    assert sent["ephemeral"] is True
    assert sent["allowed_mentions"].to_dict() == {"parse": []}
    assert sent["view"].render_again is not None


@pytest.mark.parametrize(
    ("steps", "wanted"),
    [
        ([], ["Back", "Open sign-ups", "Add entrant…", "Cancel"]),
        (
            ["open"],
            ["Sign up", "Back", "Close sign-ups", "Open check-in", "Add entrant…", "Cancel"],
        ),
        (["open", "check_in"], ["Back", "Close check-in", "Add entrant…", "Cancel"]),
        (
            ["open", "close"],
            [
                "Back",
                "Open sign-ups",
                "Open check-in",
                "Seed…",
                "Shuffle",
                "Start",
                "Add entrant…",
                "Cancel",
            ],
        ),
        (["open", "close", "cancel"], ["Back", "Restore"]),
    ],
)
async def test_an_organiser_sees_only_the_moves_legal_in_each_state(bot, guild, steps, wanted):
    tid = await created(bot, guild)
    await moved(bot, guild, tid, moves.open_signups) if "open" in steps else None
    await moved(bot, guild, tid, people.join, actor=ADA) if "open" in steps else None
    if "check_in" in steps:
        await moved(bot, guild, tid, people.open_check_in)
    if "close" in steps:
        await moved(bot, guild, tid, moves.close_signups)
    if "cancel" in steps:
        await moved(bot, guild, tid, moves.cancel)

    _, view = await tournament(bot, guild, TO, tid)

    buttons = [one for one in labels(view) if one not in ("EntrantPick", "SetPick")]
    assert buttons == wanted


async def test_a_running_bracket_offers_call_and_complete_only_when_they_apply(bot, guild):
    tid = await running(bot, guild, ADA, BEA, format="single", best_of_finals=3)
    _, view = await tournament(bot, guild, TO, tid)
    assert labels(view) == [
        "Back",
        "Call ready sets",
        "Back to seeding",
        "Cancel",
        "EntrantPick",
        "SetPick",
    ]

    await moved(bot, guild, tid, sets.report, "W1-1", 2, 0, actor=TO)
    _, view = await tournament(bot, guild, TO, tid)
    assert labels(view)[:4] == ["Back", "Complete", "Back to seeding", "Cancel"]

    await moved(bot, guild, tid, moves.complete)
    _, view = await tournament(bot, guild, TO, tid)
    assert labels(view)[:3] == ["Back", "Reopen", "Cancel"]


@pytest.mark.parametrize(
    ("joined", "check_in", "wanted"),
    [
        (False, False, ["Sign up", "Back"]),
        (True, False, ["Leave", "Back"]),
        (True, True, ["Check in", "Leave", "Back"]),
    ],
)
async def test_a_member_sees_only_their_own_legal_moves(bot, guild, joined, check_in, wanted):
    tid = await created(bot, guild)
    await moved(bot, guild, tid, moves.open_signups)
    if joined:
        await moved(bot, guild, tid, people.join, actor=ADA)
    if check_in:
        await moved(bot, guild, tid, people.open_check_in)
    _, view = await tournament(bot, guild, ADA, tid)
    assert labels(view) == wanted


async def test_a_player_sees_their_own_sets_and_can_drop_out_after_being_asked(bot, guild):
    tid = await running(bot, guild, ADA, BEA, CY, STAFF, format="single")
    embed, view = await tournament(bot, guild, ADA, tid)
    assert labels(view) == ["Drop out", "Back", "SetPick"]
    assert embed.fields[0].name == "Your sets"
    assert embed.fields[0].value.startswith("**W1-1** · Ada v ")

    interaction = pressing(bot, ADA)
    asked = await press(view, "Drop out", interaction)
    assert "Drop out of **Knuck Up 12**? Your remaining sets are forfeited." in [
        one.value for one in asked["embed"].fields
    ]
    assert not (await store_.entrant_of(bot.db, tid, ADA))["dropped"]

    done = await press(asked["view"], "Drop out", pressing(bot, ADA))
    assert done["embed"].description.startswith(
        "Ada has dropped out of **Knuck Up 12**; their remaining sets are forfeited."
    )
    assert (await store_.entrant_of(bot.db, tid, ADA))["dropped"]


async def test_a_member_signs_up_from_the_panel_and_the_thread_card_follows(bot, guild):
    tid = await created(bot, guild)
    await moved(bot, guild, tid, moves.open_signups)
    _, view = await tournament(bot, guild, ADA, tid)

    after = await press(view, "Sign up", pressing(bot, ADA))

    assert after["embed"].description.startswith("You are in **Knuck Up 12**.")
    assert labels(after["view"]) == ["Leave", "Back"]
    assert "1 entrant(s)" in the_thread(bot).messages[0].embed.description


async def test_an_organiser_whose_role_went_is_refused_in_words_on_the_next_press(bot, guild):
    tid = await created(bot, guild)
    _, view = await tournament(bot, guild, TO, tid)
    guild.get_member(TO).roles = []

    after = await press(view, "Open sign-ups", pressing(bot, TO))

    assert after["embed"].description.startswith(
        "Running a tournament is for staff and tournament organisers, so nothing was done."
    )
    assert (await store_.tournament(bot.db, GUILD, tid))["state"] == "draft"


async def test_cancel_asks_first_and_keep_it_changes_nothing(bot, guild):
    tid = await created(bot, guild)
    _, view = await tournament(bot, guild, TO, tid)

    asked = await press(view, "Cancel", pressing(bot, TO))
    kept = await press(asked["view"], "Keep it", pressing(bot, TO))
    assert (await store_.tournament(bot.db, GUILD, tid))["state"] == "draft"
    assert "Open sign-ups" in labels(kept["view"])

    asked = await press(view, "Cancel", pressing(bot, TO))
    done = await press(asked["view"], "Cancel", pressing(bot, TO))
    assert done["embed"].description.startswith("**Knuck Up 12** is cancelled.")
    assert labels(done["view"])[:2] == ["Back", "Restore"]
    assert "**Cancelled**" in the_thread(bot).messages[0].embed.description


async def test_call_ready_sets_calls_every_ready_set_and_their_cards_say_so(bot, guild):
    tid = await running(bot, guild, ADA, BEA, CY, STAFF, format="single")
    _, view = await tournament(bot, guild, TO, tid)

    after = await press(view, "Call ready sets", pressing(bot, TO))

    assert after["embed"].description.startswith("Called 2 set(s) in **Knuck Up 12**.")
    assert all("Called — play now" in card.embed.description for card in the_thread(bot).cards)


async def test_the_seed_order_is_read_by_tag_or_by_name(bot, guild):
    tid = await created(bot, guild)
    await moved(bot, guild, tid, moves.open_signups)
    for player in (ADA, BEA, CY):
        await moved(bot, guild, tid, people.join, actor=player)
    everyone = await store_.entrants(bot.db, tid)
    ada, bea, cy = (one["id"] for one in everyone)

    assert panel.seed_text(everyone) == f"Ada #{ada}\nBea #{bea}\nCy #{cy}"
    assert panel.seed_order(f"Cy #{cy}\n1. bea\nAda", everyone) == ([cy, bea, ada], 0)
    assert panel.seed_order("Cy\nNobody", everyone) == (None, 2)


async def test_seeding_through_the_form_saves_the_order(bot, guild):
    tid = await created(bot, guild)
    await moved(bot, guild, tid, moves.open_signups)
    for player in (ADA, BEA):
        await moved(bot, guild, tid, people.join, actor=player)
    await moved(bot, guild, tid, moves.close_signups)
    _, view = await tournament(bot, guild, TO, tid)
    interaction = pressing(bot, TO)
    await item(view, "Seed…").callback(interaction)
    modal = interaction.modal
    fill(modal, order="Bea\nAda")

    await modal.on_submit(interaction)

    assert shown(interaction)["embed"].description.startswith(
        "Seeding for **Knuck Up 12** is saved."
    )
    seeds = {one["name"]: one["seed"] for one in await store_.entrants(bot.db, tid)}
    assert seeds == {"Bea": 1, "Ada": 2}


async def test_create_through_the_form_makes_the_tournament_and_its_thread(bot, guild):
    _, view = await panel.build_home(bot, guild, guild.get_member(TO))
    interaction = pressing(bot, TO)
    await item(view, "Create…").callback(interaction)
    modal = interaction.modal
    fill(modal, name="Friday Fights", game="Tekken 8", format="single", best_of="", cap="16")

    await modal.on_submit(interaction)

    after = shown(interaction)
    assert after["embed"].description.startswith("Created **Friday Fights**.")
    assert the_thread(bot).name == "Friday Fights"
    row = (await store_.tournaments(bot.db, GUILD))[0]
    assert (row["format"], row["game"], row["entrant_cap"]) == ("single", "Tekken 8", 16)


async def test_a_bad_option_in_the_create_form_is_refused_in_words(bot, guild):
    _, view = await panel.build_home(bot, guild, guild.get_member(TO))
    interaction = pressing(bot, TO)
    await item(view, "Create…").callback(interaction)
    fill(interaction.modal, name="X", game="", format="ladder", best_of="", cap="")

    await interaction.modal.on_submit(interaction)

    assert shown(interaction)["embed"].description.startswith("format cannot be ladder")
    assert await store_.tournaments(bot.db, GUILD) == []


async def test_a_member_never_gets_the_create_form(bot, guild):
    interaction = pressing(bot, ADA)
    await panel.CreateButton().callback(interaction)
    assert interaction.modal is None
    assert interaction.said[0].startswith("Running a tournament is for staff")


@pytest.mark.parametrize(
    ("state", "wanted"),
    [("signups", ["Remove…", "Back"]), ("check_in", ["Check out", "Remove…", "Back"])],
)
async def test_an_entrants_moves_before_the_start(bot, guild, state, wanted):
    tid = await created(bot, guild)
    await moved(bot, guild, tid, moves.open_signups)
    await moved(bot, guild, tid, people.add_entrant, name="Remy")
    if state == "check_in":
        await moved(bot, guild, tid, people.open_check_in)
    remy = (await store_.entrants(bot.db, tid))[0]

    _, view = await panel.build_entrant(bot, guild, guild.get_member(TO), tid, remy["id"])

    assert labels(view) == wanted


async def test_a_dq_takes_a_reason_and_the_player_is_told_only_in_the_log_in_shadow(bot, guild):
    tid = await running(bot, guild, ADA, BEA, format="single")
    ada = (await store_.entrant_of(bot.db, tid, ADA))["id"]
    _, view = await panel.build_entrant(bot, guild, guild.get_member(TO), tid, ada)
    assert labels(view) == ["DQ…", "Drop…", "Back"]
    interaction = pressing(bot, TO)
    await item(view, "DQ…").callback(interaction)
    fill(interaction.modal, reason="two no-shows")

    await interaction.modal.on_submit(interaction)

    assert shown(interaction)["embed"].description.startswith(
        "Ada is disqualified from **Knuck Up 12**"
    )
    assert labels(shown(interaction)["view"]) == ["Restore", "Back"]
    kind, _, target, details = (await rows(bot.db))[-1]
    assert (kind, target, details["dm"]) == ("brackets.would_dm", ADA, "brackets_dm_dq")
    assert guild.get_member(ADA).dms == []
    assert "W1-1 is final: Bea wins by forfeit." in the_thread(bot).cards[0].embed.description


async def test_a_dq_reaches_the_player_by_dm_when_on(bot, guild):
    await bot.store.set(GUILD, "brackets_mode", "on")
    tid = await running(bot, guild, ADA, BEA, format="single")
    ada = (await store_.entrant_of(bot.db, tid, ADA))["id"]
    _, view = await panel.build_entrant(bot, guild, guild.get_member(TO), tid, ada)
    interaction = pressing(bot, TO)
    await item(view, "DQ…").callback(interaction)
    fill(interaction.modal, reason="two no-shows")

    await interaction.modal.on_submit(interaction)

    assert guild.get_member(ADA).dms == [
        "A tournament organiser disqualified you from **Knuck Up 12**; your remaining sets are "
        "forfeited.\nReason: two no-shows"
    ]


async def test_the_reporter_is_never_offered_confirm_and_the_opponent_is(bot, guild):
    tid = await running(bot, guild, ADA, BEA, format="single", best_of_finals=3)
    _, view = await panel.build_set(bot, guild, guild.get_member(ADA), tid, "W1-1")
    assert labels(view) == ["Report", "Back"]

    await moved(bot, guild, tid, sets.report, "W1-1", 2, 0, actor=ADA)
    _, view = await panel.build_set(bot, guild, guild.get_member(ADA), tid, "W1-1")
    assert labels(view) == ["Back"]
    _, view = await panel.build_set(bot, guild, guild.get_member(BEA), tid, "W1-1")
    assert labels(view) == ["Confirm", "Dispute", "Back"]
    _, view = await panel.build_set(bot, guild, guild.get_member(TO), tid, "W1-1")
    assert labels(view) == [
        "Let it stand",
        "Decide…",
        "Ada by forfeit…",
        "Bea by forfeit…",
        "Reset…",
        "Back",
    ]


async def test_let_it_stand_and_a_forfeit_from_the_set_view(bot, guild):
    tid = await running(bot, guild, ADA, BEA, CY, STAFF, format="single", best_of_finals=3)
    await moved(bot, guild, tid, sets.report, "W1-1", 2, 0, actor=ADA)
    _, view = await panel.build_set(bot, guild, guild.get_member(TO), tid, "W1-1")

    after = await press(view, "Let it stand", pressing(bot, TO))
    lines = after["embed"].description.split("\n")
    assert lines.count("W1-1 is final: Ada wins 2–0.") == 1

    _, view = await panel.build_set(bot, guild, guild.get_member(TO), tid, "W1-2")
    names = [one for one in labels(view) if one.endswith("by forfeit…")]
    interaction = pressing(bot, TO)
    await item(view, names[1]).callback(interaction)
    fill(interaction.modal, reason="")
    await interaction.modal.on_submit(interaction)
    finals = [
        one
        for one in shown(interaction)["embed"].description.split("\n")
        if one.startswith("W1-2 is final:")
    ]
    assert len(finals) == 1 and finals[0].endswith("wins by forfeit.")


async def test_adding_a_guest_and_a_member_by_hand(bot, guild):
    tid = await created(bot, guild)
    _, view = await tournament(bot, guild, TO, tid)
    added = await press(view, "Add entrant…", pressing(bot, TO))
    assert labels(added["view"]) == ["AddMemberPick", "Add a guest…", "Back"]

    interaction = pressing(bot, TO)
    await item(added["view"], "Add a guest…").callback(interaction)
    fill(interaction.modal, name="Remy")
    await interaction.modal.on_submit(interaction)

    assert shown(interaction)["embed"].description == "Remy is in **Knuck Up 12**."
    assert [one["name"] for one in await store_.entrants(bot.db, tid)] == ["Remy"]


async def test_try_again_puts_the_member_back_where_they_were(bot, guild):
    tid = await created(bot, guild)
    _, view = await tournament(bot, guild, TO, tid)
    interaction = pressing(bot, TO)
    interaction.response.deferred = {}

    await view.render_again(interaction)

    assert shown(interaction)["embed"].title == "Knuck Up 12"


async def test_restoring_one_entrant_from_the_panel_edits_no_set_card(bot, guild):
    tid = await running(bot, guild, ADA, BEA, CY, STAFF, format="round_robin")
    await thread_.sweep(bot, guild)
    ada = (await store_.entrant_of(bot.db, tid, ADA))["id"]
    await moved(bot, guild, tid, people.dq, ada)
    thread = the_thread(bot)
    before = {card.id: card.edits for card in thread.cards}
    assert len(before) == 6

    _, view = await panel.build_entrant(bot, guild, guild.get_member(TO), tid, ada)
    after = await press(view, "Restore", pressing(bot, TO))

    assert after["embed"].description.startswith("Ada is back in **Knuck Up 12**.")
    assert {card.id: card.edits for card in thread.cards} == before


@pytest.mark.parametrize("state", ["draft", "seeding"])
async def test_leave_is_offered_and_works_wherever_it_is_legal(bot, guild, state):
    tid = await created(bot, guild)
    await moved(bot, guild, tid, people.add_entrant, user_id=ADA)
    if state == "seeding":
        await moved(bot, guild, tid, moves.open_signups)
        await moved(bot, guild, tid, moves.close_signups)
    _, view = await tournament(bot, guild, ADA, tid)
    assert labels(view) == ["Leave", "Back"]
    assert "Leave" in the_thread(bot).messages[0].labels

    after = await press(view, "Leave", pressing(bot, ADA))

    assert (await store_.entrant_of(bot.db, tid, ADA))["dropped"]
    assert labels(after["view"]) == ["Back"]


async def test_the_panels_set_lines_use_the_players_line_staff_can_edit(bot, guild):
    await bot.store.set(GUILD, "brackets_set_card_players", "{a} vs {b}")
    tid = await running(bot, guild, ADA, BEA, format="single")

    embed, view = await tournament(bot, guild, TO, tid)
    _, mine = await tournament(bot, guild, ADA, tid)

    assert embed.fields[0].value.startswith("**W1-1** · Ada vs Bea · ")
    picker = next(one for one in view.children if type(one).__name__ == "SetPick")
    assert picker.options[0].label.startswith("W1-1 · Ada vs Bea")
    assert mine.children[-1].options[0].label.startswith("W1-1 · Ada vs Bea")


async def test_only_staff_see_the_move_and_it_moves_the_rehearsal_into_knuck_up(bot, guild):
    tid = await running(bot, guild, ADA, BEA, format="single")
    _, view = await tournament(bot, guild, STAFF, tid)
    assert "Move to #knuck-up" not in labels(view)

    await bot.store.set(GUILD, "brackets_mode", "on")
    _, organiser = await tournament(bot, guild, TO, tid)
    assert "Move to #knuck-up" not in labels(organiser)
    _, view = await tournament(bot, guild, STAFF, tid)
    asked = await press(view, "Move to #knuck-up", pressing(bot, STAFF))
    assert (await store_.tournament(bot.db, GUILD, tid))["shadow"] == 1

    done = await press(asked["view"], "Move to #knuck-up", pressing(bot, STAFF))

    new = home(bot, KNUCK_UP).threads[0]
    assert done["embed"].description.startswith(f"**Knuck Up 12** is now in <#{new.id}>.")
    assert (await store_.tournament(bot.db, GUILD, tid))["shadow"] == 0
    assert len(new.cards) == 1 and new.messages[0].pinned
    assert "Move to #knuck-up" not in labels(done["view"])


async def test_a_form_never_opens_while_the_mode_is_off(bot, guild):
    tid = await created(bot, guild)
    await moved(bot, guild, tid, moves.open_signups)
    await moved(bot, guild, tid, people.join, actor=ADA)
    await moved(bot, guild, tid, moves.close_signups)
    _, view = await tournament(bot, guild, TO, tid)
    await bot.store.set(GUILD, "brackets_mode", "off")
    interaction = pressing(bot, TO)

    await item(view, "Seed…").callback(interaction)

    assert interaction.modal is None
    assert interaction.said == [moves.said(bot.store, GUILD, "brackets_off_said")]


async def test_pools_advance_after_asking_and_go_back_the_same_way(bot, guild):
    tid = await running(
        bot, guild, ADA, BEA, CY, STAFF, format="single", pools_format="round_robin"
    )
    assert (await store_.tournament(bot.db, GUILD, tid))["state"] == "pools"
    thread = the_thread(bot)
    titles = sorted(card.embed.title for card in thread.cards)
    assert titles == ["A.R1-1 · Pool A · round 1", "B.R1-1 · Pool B · round 1"]
    starter = thread.messages[0].embed.description.split("\n")
    assert "**In pools**" in starter and starter[-2].startswith("Pool A · Ada")

    _, view = await tournament(bot, guild, TO, tid)
    assert "Advance to the final" not in labels(view)
    await moved(bot, guild, tid, sets.report, "A.R1-1", 2, 0, actor=TO)
    await moved(bot, guild, tid, sets.report, "B.R1-1", 2, 0, actor=TO)
    _, view = await tournament(bot, guild, TO, tid)
    assert labels(view)[:4] == ["Back", "Advance to the final", "Back to seeding", "Cancel"]

    asked = await press(view, "Advance to the final", pressing(bot, TO))
    assert "Build **Knuck Up 12**'s final from the pools?" in [
        one.value for one in asked["embed"].fields
    ]
    assert (await store_.tournament(bot.db, GUILD, tid))["state"] == "pools"
    done = await press(asked["view"], "Advance to the final", pressing(bot, TO))
    assert done["embed"].description.startswith("**Knuck Up 12**'s final is built")
    assert labels(done["view"])[:5] == [
        "Back",
        "Call ready sets",
        "Back to pools",
        "Back to seeding",
        "Cancel",
    ]
    finals = [card for card in thread.cards if card.embed.title.startswith("W")]
    assert sorted(card.embed.title.split(" · ")[0] for card in finals) == ["W1-1", "W1-2"]
    pool_cards = [card for card in thread.cards if card.embed.title[1] == "."]
    assert all(card.custom_ids == [] for card in pool_cards)

    asked = await press(done["view"], "Back to pools", pressing(bot, TO))
    back = await press(asked["view"], "Back to pools", pressing(bot, TO))
    assert back["embed"].description.startswith("**Knuck Up 12** is back in its pools")
    assert (await store_.tournament(bot.db, GUILD, tid))["state"] == "pools"
    assert all("cleared" in (card.embed.description or "") for card in finals)
    assert all(card.custom_ids for card in pool_cards)
