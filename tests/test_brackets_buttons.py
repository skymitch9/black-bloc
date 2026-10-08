# ruff: noqa: F401, F811
from __future__ import annotations

from types import SimpleNamespace

import discord

from black_bloc import brackets_buttons as buttons_
from black_bloc import brackets_cards as cards
from black_bloc import brackets_moves as moves
from black_bloc import brackets_people as people
from black_bloc import brackets_sets as sets
from black_bloc import brackets_store as store_
from tests.test_brackets_moves import ADA, BEA, CY, GUILD, STAFF, TO, TO_ROLE, rows, who
from tests.test_brackets_thread import (
    REHEARSAL,
    bot,
    created,
    guild,
    moved,
    running,
    the_thread,
)


class FakeResponse:
    def __init__(self):
        self.messages = []
        self.modals = []
        self.deferred = None

    def is_done(self):
        return self.deferred is not None or bool(self.messages) or bool(self.modals)

    async def send_message(self, content=None, ephemeral=False, **kwargs):
        self.messages.append({"content": content, "ephemeral": ephemeral, **kwargs})

    async def send_modal(self, modal):
        self.modals.append(modal)

    async def defer(self, ephemeral=False, thinking=False):
        self.deferred = {"ephemeral": ephemeral, "thinking": thinking}


class FakeFollowup:
    def __init__(self, response):
        self.response = response

    async def send(self, content=None, ephemeral=False, **kwargs):
        self.response.messages.append({"content": content, "ephemeral": ephemeral, **kwargs})


class FakeInteraction:
    def __init__(self, bot, user_id):
        self.client = bot
        self.guild = bot.guild
        self.user = bot.guild.get_member(user_id)
        self.response = FakeResponse()
        self.followup = FakeFollowup(self.response)
        self.edits = []
        self.data = {}

    async def original_response(self):
        return SimpleNamespace(id=1, embeds=[])

    async def edit_original_response(self, **kwargs):
        self.edits.append(kwargs)
        return SimpleNamespace(id=2, embeds=[kwargs.get("embed")])

    @property
    def said(self):
        return [one["content"] for one in self.response.messages if one.get("content")]

    @property
    def modal(self):
        return self.response.modals[-1] if self.response.modals else None


def pressing(bot, user_id):
    return FakeInteraction(bot, user_id)


def fill(modal, **values):
    for name, value in values.items():
        getattr(modal, name)._value = value


async def card_of(bot, key):
    thread = the_thread(bot)
    return next(one for one in thread.cards if one.embed.title.startswith(f"{key} "))


async def test_sign_up_from_the_starter_card_answers_privately_and_the_card_counts_it(bot, guild):
    tid = await created(bot, guild)
    await moved(bot, guild, tid, moves.open_signups)
    press = pressing(bot, ADA)

    await buttons_.starter_pressed(press, tid, cards.JOIN)

    assert press.response.deferred == {"ephemeral": True, "thinking": True}
    assert press.said == ["You are in **Knuck Up 12**."]
    assert all(one["ephemeral"] for one in press.response.messages)
    assert "1 entrant(s)" in the_thread(bot).messages[0].embed.description


async def test_leave_and_check_in_from_someone_not_signed_up_are_refused_in_words(bot, guild):
    tid = await created(bot, guild)
    await moved(bot, guild, tid, moves.open_signups)
    for action in (cards.LEAVE, cards.CHECK_IN):
        press = pressing(bot, CY)
        await buttons_.starter_pressed(press, tid, action)
        assert press.said == ["You are not signed up for **Knuck Up 12**, so nothing was done."]


async def test_a_stale_leave_on_a_running_tournament_never_forfeits_anyone(bot, guild):
    tid = await running(bot, guild, ADA, BEA, format="single")
    press = pressing(bot, ADA)

    await buttons_.starter_pressed(press, tid, cards.LEAVE)

    assert press.said == ["**Knuck Up 12** is running, so that cannot be done now."]
    assert not (await store_.entrant_of(bot.db, tid, ADA))["dropped"]


async def test_check_in_from_the_starter_card(bot, guild):
    tid = await created(bot, guild)
    await moved(bot, guild, tid, moves.open_signups)
    await moved(bot, guild, tid, people.join, actor=ADA)
    await moved(bot, guild, tid, people.open_check_in)
    press = pressing(bot, ADA)

    await buttons_.starter_pressed(press, tid, cards.CHECK_IN)

    assert press.said == ["Ada is checked in for **Knuck Up 12**."]
    assert (await store_.entrant_of(bot.db, tid, ADA))["checked_in"]


async def test_report_from_a_stranger_is_refused_in_words_and_opens_no_form(bot, guild):
    tid = await running(bot, guild, ADA, BEA, format="single")
    press = pressing(bot, CY)

    await buttons_.set_pressed(press, tid, "W1-1", cards.REPORT)

    assert press.modal is None
    assert press.said == [
        "You are not playing in W1-1, so nothing was done. Its two players and tournament "
        "organisers can report it."
    ]


async def test_a_player_reports_through_the_form_and_the_card_waits_on_the_opponent(bot, guild):
    tid = await running(bot, guild, ADA, BEA, format="single", best_of_finals=3)
    press = pressing(bot, ADA)
    await buttons_.set_pressed(press, tid, "W1-1", cards.REPORT)
    modal = press.modal
    assert isinstance(modal, buttons_.ReportModal)
    assert modal.title == "Report W1-1 · best of 3"
    assert (modal.score_a.label, modal.score_b.label) == ("Ada — games won", "Bea — games won")

    fill(modal, score_a="two", score_b="1")
    await modal.on_submit(press)
    assert press.said[-1] == "A score is a whole number of games, so nothing was reported."

    fill(modal, score_a="2", score_b="1")
    await modal.on_submit(press)
    assert press.said[-1].startswith("W1-1 reported 2–1.")
    card = await card_of(bot, "W1-1")
    assert "Ada reported 2–1 — waiting on Bea" in card.embed.description


async def test_the_reporter_cannot_confirm_and_the_opponent_can(bot, guild):
    tid = await running(bot, guild, ADA, BEA, format="single", best_of_finals=3)
    await moved(bot, guild, tid, sets.report, "W1-1", 2, 0, actor=ADA)

    own = pressing(bot, ADA)
    await buttons_.set_pressed(own, tid, "W1-1", cards.CONFIRM)
    assert own.said == ["You reported W1-1, so your opponent confirms or disputes it."]

    stranger = pressing(bot, CY)
    await buttons_.set_pressed(stranger, tid, "W1-1", cards.CONFIRM)
    assert stranger.said[0].startswith("You are not playing in W1-1")

    opponent = pressing(bot, BEA)
    await buttons_.set_pressed(opponent, tid, "W1-1", cards.CONFIRM)
    assert opponent.said == ["W1-1 is final: Ada wins 2–0."]
    assert "W1-1 is final: Ada wins 2–0." in (await card_of(bot, "W1-1")).embed.description


async def test_a_dispute_from_the_opponent_shows_its_note_and_a_stranger_gets_no_form(bot, guild):
    tid = await running(bot, guild, ADA, BEA, format="single", best_of_finals=3)

    await moved(bot, guild, tid, sets.report, "W1-1", 2, 0, actor=ADA)

    stranger = pressing(bot, CY)
    await buttons_.set_pressed(stranger, tid, "W1-1", cards.DISPUTE)
    assert stranger.modal is None and stranger.said[0].startswith("You are not playing in W1-1")

    opponent = pressing(bot, BEA)
    await buttons_.set_pressed(opponent, tid, "W1-1", cards.DISPUTE)
    fill(opponent.modal, note="wrong stage")
    await opponent.modal.on_submit(opponent)

    assert opponent.said == ["W1-1 is disputed; a tournament organiser decides it."]
    card = await card_of(bot, "W1-1")
    assert "Disputed by Bea — an organiser decides\n“wrong stage”" in card.embed.description
    assert card.labels == ["Decide…", "Reset…"]


async def test_decide_and_reset_are_for_organisers_and_refused_in_words_to_a_player(bot, guild):
    tid = await running(bot, guild, ADA, BEA, format="single")
    for action in (cards.DECIDE, cards.RESET, cards.CALL):
        press = pressing(bot, ADA)
        await buttons_.set_pressed(press, tid, "W1-1", action)
        assert press.modal is None
        assert press.said[0].startswith(
            "Running a tournament is for staff and tournament organisers"
        )


async def test_a_role_taken_away_while_the_card_is_up_is_refused_on_the_next_press(bot, guild):
    tid = await running(bot, guild, ADA, BEA, format="single")
    guild.get_member(TO).roles = []
    press = pressing(bot, TO)

    await buttons_.set_pressed(press, tid, "W1-1", cards.DECIDE)

    assert press.modal is None
    assert press.said[0].startswith("Running a tournament is for staff and tournament organisers")


async def test_an_organiser_decides_through_the_form_and_both_players_are_told(bot, guild):
    tid = await running(bot, guild, ADA, BEA, format="single", best_of_finals=3)
    press = pressing(bot, TO)
    await buttons_.set_pressed(press, tid, "W1-1", cards.DECIDE)
    modal = press.modal
    assert isinstance(modal, buttons_.DecideModal) and modal.title == "Decide W1-1"

    fill(modal, score_a="0", score_b="2", reason="Ada left the venue")
    await modal.on_submit(press)

    assert press.said == ["W1-1 is final: Bea wins 2–0."]
    told = [
        (target, d["dm"])
        for kind, _, target, d in await rows(bot.db)
        if kind == "brackets.would_dm"
    ]
    assert told == [(ADA, "brackets_dm_decided"), (BEA, "brackets_dm_decided")]
    assert guild.get_member(ADA).dms == []


async def test_an_organiser_resets_a_set_and_its_card_is_ready_again(bot, guild):
    tid = await running(bot, guild, ADA, BEA, format="single", best_of_finals=3)
    await moved(bot, guild, tid, sets.report, "W1-1", 2, 0, actor=ADA)
    press = pressing(bot, STAFF)
    await buttons_.set_pressed(press, tid, "W1-1", cards.RESET)
    fill(press.modal, reason="")

    await press.modal.on_submit(press)

    assert press.said == ["W1-1 is open again; every set it decided after it is cleared."]
    card = await card_of(bot, "W1-1")
    assert "Ready to play" in card.embed.description
    assert card.labels == ["Report", "Call", "Decide…"]


async def test_an_organiser_calls_a_set_from_its_card(bot, guild):
    tid = await running(bot, guild, ADA, BEA, format="single")
    press = pressing(bot, TO)

    await buttons_.set_pressed(press, tid, "W1-1", cards.CALL)

    assert press.said == ["W1-1 is called: Ada v Bea."]
    assert "Called — play now" in (await card_of(bot, "W1-1")).embed.description


async def test_a_press_on_a_tournament_that_is_gone_says_so(bot, guild):
    press = pressing(bot, ADA)
    await buttons_.set_pressed(press, 99, "W1-1", cards.REPORT)
    assert press.said == ["There is no tournament 99 here, so nothing was done."]

    press = pressing(bot, ADA)
    await buttons_.starter_pressed(press, 99, cards.CHECK_IN)
    assert press.said == ["There is no tournament 99 here, so nothing was done."]


async def test_an_organiser_reporting_a_guests_set_decides_it_and_the_member_is_told(bot, guild):
    tid = await created(bot, guild, format="single", best_of_finals=3)
    await moved(bot, guild, tid, moves.open_signups)
    await moved(bot, guild, tid, people.join, actor=ADA)
    await moved(bot, guild, tid, people.add_entrant, name="Remy")
    await moved(bot, guild, tid, moves.close_signups)
    await moved(bot, guild, tid, moves.start)
    press = pressing(bot, TO)
    await buttons_.set_pressed(press, tid, "W1-1", cards.REPORT)
    fill(press.modal, score_a="2", score_b="0")

    await press.modal.on_submit(press)

    assert press.said == ["W1-1 is final: Ada wins 2–0."]
    told = [target for kind, _, target, _ in await rows(bot.db) if kind == "brackets.would_dm"]
    assert told == [ADA]


async def test_no_set_form_opens_while_the_mode_is_off(bot, guild):
    tid = await running(bot, guild, ADA, BEA, format="single", best_of_finals=3)
    await moved(bot, guild, tid, sets.report, "W1-1", 2, 0, actor=ADA)
    await bot.store.set(GUILD, "brackets_mode", "off")
    off = moves.said(bot.store, GUILD, "brackets_off_said")

    for user_id, action in (
        (ADA, cards.REPORT),
        (BEA, cards.DISPUTE),
        (TO, cards.DECIDE),
        (TO, cards.RESET),
    ):
        press = pressing(bot, user_id)
        await buttons_.set_pressed(press, tid, "W1-1", action)
        assert press.modal is None, action
        assert press.said == [off], action


async def test_an_organiser_deciding_their_own_set_is_not_told_about_it(bot, guild):
    tid = await running(bot, guild, TO, BEA, format="single", best_of_finals=3)
    press = pressing(bot, TO)
    await buttons_.set_pressed(press, tid, "W1-1", cards.DECIDE)
    fill(press.modal, score_a="2", score_b="0", reason="")

    await press.modal.on_submit(press)

    told = [target for kind, _, target, _ in await rows(bot.db) if kind == "brackets.would_dm"]
    assert told == [BEA]


async def test_leave_from_the_starter_card_works_while_seeding(bot, guild):
    tid = await created(bot, guild)
    await moved(bot, guild, tid, moves.open_signups)
    await moved(bot, guild, tid, people.join, actor=ADA)
    await moved(bot, guild, tid, moves.close_signups)
    starter = the_thread(bot).messages[0]
    assert starter.labels[0] == "Leave"
    press = pressing(bot, ADA)

    await buttons_.starter_pressed(press, tid, cards.LEAVE)

    assert (await store_.entrant_of(bot.db, tid, ADA))["dropped"]
    assert starter.labels == ["Open the bracket"]
