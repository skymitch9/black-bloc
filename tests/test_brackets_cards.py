# ruff: noqa: F401, F811
from __future__ import annotations

import re

import discord
import pytest

from black_bloc import brackets_cards as cards
from black_bloc import brackets_store as store_
from black_bloc.brackets.model import Match
from tests.test_brackets_moves import GUILD, bot, guild


def row(**given):
    found = {
        "id": 3,
        "name": "Knuck Up 12",
        "game": "Street Fighter 6",
        "format": "double",
        "state": "signups",
        "best_of": 3,
        "best_of_late": 5,
        "best_of_finals": 5,
        "best_of_from_round": None,
        "grand_final_reset": 1,
        "third_place": 0,
        "swiss_rounds": None,
        "entrant_cap": None,
        "starts_at": None,
        "check_in_closes_at": None,
        "to_user_id": 8,
        "shadow": 0,
    }
    found.update(given)
    return found


def person(entrant_id, name, user_id=None, **given):
    return {
        "id": entrant_id,
        "name": name,
        "user_id": user_id,
        "dropped": 0,
        "placement": None,
        "seed": entrant_id,
        **given,
    }


PEOPLE = {1: person(1, "Ada", 21), 2: person(2, "Remy")}


def match(**given):
    return Match(
        key="W1-1", side="winners", round=1, position=1, best_of=3, slot_a=1, slot_b=2, **given
    )


@pytest.mark.parametrize(
    ("state", "wanted"),
    [
        ("draft", ()),
        ("signups", ("join", "leave")),
        ("check_in", ("check_in", "leave")),
        ("seeding", ()),
        ("running", ()),
        ("complete", ()),
        ("cancelled", ()),
    ],
)
def test_the_starter_card_offers_only_the_member_moves_legal_now(state, wanted):
    assert cards.starter_moves(state) == wanted


@pytest.mark.parametrize(
    ("set_state", "wanted"),
    [
        ("waiting", ()),
        ("ready", ("report", "call", "decide")),
        ("called", ("report", "decide", "reset")),
        ("reported", ("confirm", "dispute", "decide", "reset")),
        ("disputed", ("decide", "reset")),
        ("complete", ("decide", "reset")),
        ("bye", ()),
        ("void", ()),
    ],
)
def test_a_set_card_offers_only_the_moves_its_state_allows(set_state, wanted):
    assert cards.set_moves("running", set_state) == wanted
    assert cards.set_moves("complete", set_state) == ()


def test_custom_ids_are_inside_discords_limit_and_match_their_templates():
    starter = cards.starter_custom_id(123456, "check_in")
    one = cards.set_custom_id(123456, "L12-3", "dispute")
    assert re.fullmatch(cards.STARTER_TEMPLATE, starter)
    assert re.fullmatch(cards.SET_TEMPLATE, one)
    assert not re.fullmatch(cards.STARTER_TEMPLATE, one)
    assert not re.fullmatch(cards.SET_TEMPLATE, starter)
    assert max(len(starter), len(one)) <= 100
    assert one.startswith(cards.set_prefix(123456, "L12-3"))


async def test_the_format_line_names_each_option_in_words(bot):
    store = bot.store
    assert (
        cards.format_line(store, GUILD, row(best_of_finals=3))
        == "Double elimination · best of 3 · grand-final reset"
    )
    single = row(format="single", third_place=1, best_of_from_round=8, best_of_finals=7)
    assert cards.format_line(store, GUILD, single) == (
        "Single elimination · best of 3 · third-place set · best of 5 from top 8 · finals best of 7"
    )
    assert cards.format_line(store, GUILD, row(format="swiss", swiss_rounds=4)) == (
        "Swiss · best of 3 · 4 rounds"
    )


async def test_the_starter_card_reads_state_count_cap_organiser_and_placings(bot):
    store = bot.store
    people = [person(1, "Ada", 21), person(2, "Bea", 22, dropped=1)]
    embed = cards.starter_embed(store, GUILD, row(entrant_cap=16, best_of_finals=3), people)
    assert embed.title == "Knuck Up 12"
    assert embed.description.split("\n") == [
        "Street Fighter 6",
        "Double elimination · best of 3 · grand-final reset",
        "**Open for sign-ups**",
        "1 of 16 entrants",
        "Organiser: <@8>",
    ]
    done = [person(1, "Ada", 21, placement=2), person(2, "Bea", 22, placement=1)]
    lines = cards.starter_embed(store, GUILD, row(state="complete"), done).description.split("\n")
    assert lines[-2:] == ["1. Bea", "2. Ada"]


async def test_every_starter_word_is_a_setting_staff_can_change(bot):
    await bot.store.set(GUILD, "brackets_card_entrants_line", "{count} fighters")
    await bot.store.set(GUILD, "brackets_sign_up_label", "I'm in")
    embed = cards.starter_embed(bot.store, GUILD, row(), [person(1, "Ada", 21)])
    assert "1 fighters" in embed.description
    view = cards.starter_view(bot.store, GUILD, row(), "https://blackbloc.example")
    assert [one.item.label if hasattr(one, "item") else one.label for one in view.children] == [
        "I'm in",
        "Leave",
        "Open the bracket",
    ]
    assert view.children[-1].url == "https://blackbloc.example/brackets.html#3"


async def test_a_set_card_reads_its_round_best_of_rematch_and_state(bot):
    store = bot.store
    embed = cards.set_embed(store, GUILD, match(state="ready", rematch=True), PEOPLE, 12)
    assert embed.title == "W1-1 · Winners round 1"
    assert embed.description == "Best of 3 · Rematch\nReady to play"
    reported = match(
        state="reported",
        score_a=1,
        score_b=2,
        reported_side="b",
        reported_at="2026-10-07T12:00:00+00:00",
    )
    line = cards.set_embed(store, GUILD, reported, PEOPLE, 12).description.split("\n")[1]
    assert line == "Remy reported 1–2 — waiting on Ada, stands <t:1791375120:R>"
    won = match(state="complete", score_a=2, score_b=0, winner=1)
    assert cards.set_embed(store, GUILD, won, PEOPLE, 12).description.endswith(
        "W1-1 is final: Ada wins 2–0."
    )
    forfeit = match(state="complete", winner=2, forfeit="dq")
    assert cards.set_embed(store, GUILD, forfeit, PEOPLE, 12).description.endswith(
        "W1-1 is final: Remy wins by forfeit."
    )


@pytest.mark.parametrize(
    ("side", "round_", "wanted"),
    [
        ("winners", 2, "Winners round 2"),
        ("losers", 3, "Losers round 3"),
        ("grand", 1, "Grand final"),
        ("grand", 2, "Grand final reset"),
        ("third", 1, "Third place"),
        ("swiss", 4, "Round 4"),
        ("rr", 1, "Round 1"),
    ],
)
async def test_every_round_has_its_words(bot, side, round_, wanted):
    one = Match(key="X", side=side, round=round_, position=1, best_of=3)
    assert cards.round_words(bot.store, GUILD, one) == wanted


def test_a_member_is_mentioned_and_a_guest_is_named():
    assert cards.mention(PEOPLE[1]) == "<@21>"
    assert cards.mention(PEOPLE[2]) == "Remy"
    assert cards.player_ids(match(), PEOPLE) == [21]


def test_mentions_reach_the_two_players_only_and_nobody_in_a_rehearsal():
    live = cards.ping_mentions([21, 22], rehearsal=False)
    assert [one.id for one in live.users] == [21, 22]
    assert live.everyone is False and live.roles is False
    quiet = cards.ping_mentions([21, 22], rehearsal=True)
    assert quiet.to_dict() == discord.AllowedMentions.none().to_dict()


async def test_the_persistent_buttons_rebuild_from_their_custom_ids():
    starter = cards.StarterButton(7, "join", "Sign up")
    found = re.fullmatch(cards.STARTER_TEMPLATE, starter.custom_id)
    again = await cards.StarterButton.from_custom_id(None, None, found)
    assert (again.tournament_id, again.action) == (7, "join")
    one = cards.SetButton(7, "G2-1", "confirm", "Confirm")
    found = re.fullmatch(cards.SET_TEMPLATE, one.custom_id)
    again = await cards.SetButton.from_custom_id(None, None, found)
    assert (again.tournament_id, again.key, again.action) == (7, "G2-1", "confirm")


def test_a_card_is_recognised_by_its_buttons():
    view = discord.ui.View()
    view.add_item(cards.SetButton(7, "W1-1", "report", "Report"))
    message = type("M", (), {"components": [type("R", (), {"children": view.children})()]})()
    assert cards.carries(message, cards.set_prefix(7, "W1-1"))
    assert not cards.carries(message, cards.set_prefix(7, "W1-2"))
