from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from black_bloc import brackets_moves as moves
from black_bloc import brackets_store as store_
from black_bloc.config import load_settings
from black_bloc.logkinds import VIA_WEBSITE
from black_bloc.settings_store import SettingsStore

GUILD = 4242
STAFF = 7
TO = 8
ADA = 21
BEA = 22
CY = 23
STRANGER = 30
TO_ROLE = 555


class Role(SimpleNamespace):
    pass


class Member:
    def __init__(self, guild, user_id, name, *roles):
        self.id = user_id
        self.guild = guild
        self.display_name = name
        self.roles = [Role(id=one, name=f"role{one}") for one in roles]


class Guild:
    def __init__(self):
        self.id = GUILD
        self.members = {}
        self.roles = {TO_ROLE: Role(id=TO_ROLE, name="Tournament Organiser")}

    def get_member(self, user_id):
        return self.members.get(int(user_id))

    def get_role(self, role_id):
        return self.roles.get(int(role_id))

    def get_channel(self, channel_id):
        return None

    def add(self, user_id, name, *roles):
        self.members[user_id] = Member(self, user_id, name, *roles)
        return self.members[user_id]


class Bot:
    def __init__(self, db, store, guild):
        self.db = db
        self.store = store
        self.guild = guild
        self.guilds = [guild]

    def get_channel(self, channel_id):
        return None


@pytest.fixture
def guild():
    found = Guild()
    found.add(STAFF, "Sky")
    found.add(TO, "Tess", TO_ROLE)
    found.add(ADA, "Ada")
    found.add(BEA, "Bea")
    found.add(CY, "Cy")
    found.add(STRANGER, "Sam")
    return found


@pytest.fixture
async def bot(db, guild, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    store = SettingsStore(db, load_settings(_env_file=None))
    await store.load()
    store.is_staff = lambda member: getattr(member, "id", None) == STAFF
    await store.set(GUILD, "brackets_to_role_id", TO_ROLE)
    return Bot(db, store, guild)


def who(guild, user_id):
    return guild.get_member(user_id)


async def rows(db, kind_like="%brackets.%"):
    cur = await db.conn.execute(
        "SELECT kind, actor_id, target_id, details FROM action_log WHERE kind LIKE ? ORDER BY id",
        (kind_like,),
    )
    return [
        (row["kind"], row["actor_id"], row["target_id"], json.loads(row["details"] or "{}"))
        for row in await cur.fetchall()
    ]


async def made(bot, guild, **given):
    outcome = await moves.create(bot, guild, who(guild, TO), {"name": "Knuck Up 12", **given})
    assert outcome.ok, outcome.message
    return outcome.value


async def signed_up(bot, guild, *players, **given):
    tid = await made(bot, guild, **given)
    assert (await moves.open_signups(bot, guild, who(guild, TO), tid)).ok
    for player in players:
        outcome = await moves.join(bot, guild, who(guild, player), tid)
        assert outcome.ok, outcome.message
    return tid


async def entrant_id(bot, tid, user_id):
    return (await store_.entrant_of(bot.db, tid, user_id))["id"]


async def started(bot, guild, *players, **given):
    tid = await signed_up(bot, guild, *players, **given)
    assert (await moves.close_signups(bot, guild, who(guild, TO), tid)).ok
    outcome = await moves.start(bot, guild, who(guild, TO), tid)
    assert outcome.ok, outcome.message
    return tid


async def the_set(bot, tid, key):
    row = await store_.tournament(bot.db, GUILD, tid)
    return (await store_.bracket(bot.db, row)).matches[key]


async def test_a_tournament_organiser_creates_one_with_every_default_from_settings(bot, guild):
    tid = await made(bot, guild)
    row = await store_.tournament(bot.db, GUILD, tid)
    assert (row["format"], row["best_of"], row["best_of_finals"], row["grand_final_reset"]) == (
        "double",
        3,
        5,
        1,
    )
    assert (row["confirm_minutes"], row["check_in_minutes"], row["state"]) == (12, 30, "draft")
    assert (row["created_by"], row["to_user_id"], row["source"]) == (TO, TO, "own")
    assert await rows(bot.db) == [
        ("brackets.created", TO, None, {"via": "discord", "tournament": tid, "name": "Knuck Up 12"})
    ]


async def test_a_member_without_the_role_is_refused_in_words_naming_it(bot, guild):
    outcome = await moves.create(bot, guild, who(guild, ADA), {"name": "Mine"})
    assert (outcome.ok, outcome.code, outcome.status) == (False, "not_organiser", 403)
    assert "**Tournament Organiser**" in outcome.message
    await bot.store.clear(GUILD, "brackets_to_role_id")
    blank = await moves.create(bot, guild, who(guild, TO), {"name": "Mine"})
    assert "brackets_to_role_id" in blank.message


async def test_the_role_decides_so_the_creator_loses_the_right_with_it(bot, guild):
    tid = await made(bot, guild)
    guild.members[TO].roles = []
    outcome = await moves.open_signups(bot, guild, who(guild, TO), tid)
    assert outcome.code == "not_organiser"
    assert (await moves.open_signups(bot, guild, who(guild, STAFF), tid)).ok


async def test_off_refuses_every_move_in_words(bot, guild):
    await bot.store.set(GUILD, "brackets_mode", "off")
    outcome = await moves.create(bot, guild, who(guild, TO), {"name": "x"})
    assert (outcome.ok, outcome.code) == (False, "brackets_off")
    assert "brackets_mode" in outcome.message


@pytest.mark.parametrize(
    ("given", "field"),
    [
        ({"best_of": 4}, "best_of"),
        ({"format": "ladder"}, "format"),
        ({"confirm_minutes": 0}, "confirm_minutes"),
        ({"third_place": "yes"}, "third_place"),
        ({"starts_at": "next tuesday"}, "starts_at"),
    ],
)
async def test_a_bad_option_is_refused_in_words_naming_the_field(bot, guild, given, field):
    outcome = await moves.create(bot, guild, who(guild, TO), {"name": "x", **given})
    assert (outcome.ok, outcome.code, outcome.status) == (False, "bad_option", 400)
    assert outcome.message.startswith(field)


async def test_a_blank_name_is_refused(bot, guild):
    outcome = await moves.create(bot, guild, who(guild, TO), {"name": "   "})
    assert (outcome.code, outcome.status) == ("no_name", 400)


async def test_options_edit_until_the_start_and_not_after(bot, guild):
    tid = await signed_up(bot, guild, ADA, BEA)
    outcome = await moves.edit(
        bot, guild, who(guild, TO), tid, {"format": "single", "third_place": True}
    )
    assert outcome.ok
    row = await store_.tournament(bot.db, GUILD, tid)
    assert (row["format"], row["third_place"]) == ("single", 1)
    await moves.start(bot, guild, who(guild, TO), tid)
    late = await moves.edit(bot, guild, who(guild, TO), tid, {"best_of": 5})
    assert (late.code, late.status) == ("wrong_state", 409)
    assert "running" in late.message


async def test_signing_up_is_a_members_own_move_and_only_while_signups_are_open(bot, guild):
    tid = await made(bot, guild)
    early = await moves.join(bot, guild, who(guild, ADA), tid)
    assert (early.code, "a draft" in early.message) == ("wrong_state", True)
    await moves.open_signups(bot, guild, who(guild, TO), tid)
    assert (await moves.join(bot, guild, who(guild, ADA), tid)).ok
    again = await moves.join(bot, guild, who(guild, ADA), tid)
    assert again.code == "already_in"
    ada = await store_.entrant_of(bot.db, tid, ADA)
    assert (ada["name"], ada["added_by"], ada["seed"]) == ("Ada", ADA, 1)


async def test_two_sign_ups_at_once_leave_one_entrant(bot, guild):
    tid = await made(bot, guild)
    await moves.open_signups(bot, guild, who(guild, TO), tid)
    first, second = await asyncio.gather(
        moves.join(bot, guild, who(guild, ADA), tid), moves.join(bot, guild, who(guild, ADA), tid)
    )
    assert sorted([first.ok, second.ok]) == [False, True]
    assert len(await store_.entrants(bot.db, tid)) == 1


async def test_the_cap_stops_sign_ups_but_not_the_to(bot, guild):
    tid = await signed_up(bot, guild, ADA, BEA, entrant_cap=2)
    full = await moves.join(bot, guild, who(guild, CY), tid)
    assert (full.code, "full at 2" in full.message) == ("full", True)
    assert (await moves.add_entrant(bot, guild, who(guild, TO), tid, user_id=CY)).ok


async def test_leaving_lets_you_back_in_but_a_removal_stands(bot, guild):
    tid = await signed_up(bot, guild, ADA, BEA)
    ada, bea = await entrant_id(bot, tid, ADA), await entrant_id(bot, tid, BEA)
    left = await moves.drop(bot, guild, who(guild, ADA), tid, ada)
    assert (left.ok, left.message) == (True, "You have left **Knuck Up 12**.")
    assert (await moves.join(bot, guild, who(guild, ADA), tid)).ok
    assert (await moves.remove_entrant(bot, guild, who(guild, TO), tid, bea)).ok
    refused = await moves.join(bot, guild, who(guild, BEA), tid)
    assert refused.code == "removed"
    assert (await moves.restore_entrant(bot, guild, who(guild, TO), tid, bea)).ok
    assert not (await store_.entrant(bot.db, tid, bea))["dropped"]


async def test_nobody_drops_or_checks_in_somebody_else(bot, guild):
    tid = await signed_up(bot, guild, ADA, BEA)
    ada = await entrant_id(bot, tid, ADA)
    outcome = await moves.drop(bot, guild, who(guild, BEA), tid, ada)
    assert (outcome.code, outcome.status) == ("not_yours", 403)


async def test_a_guest_is_added_by_hand_and_needs_a_name(bot, guild):
    tid = await signed_up(bot, guild, ADA)
    nameless = await moves.add_entrant(bot, guild, who(guild, TO), tid)
    assert nameless.code == "no_name"
    outcome = await moves.add_entrant(bot, guild, who(guild, TO), tid, name="Remy (offline)")
    assert outcome.ok
    guest = [one for one in await store_.entrants(bot.db, tid) if one["user_id"] is None]
    assert [(one["name"], one["added_by"]) for one in guest] == [("Remy (offline)", TO)]


async def test_check_in_removes_no_shows_and_checks_guests_in_for_the_to(bot, guild):
    tid = await signed_up(bot, guild, ADA, BEA, CY)
    await moves.add_entrant(bot, guild, who(guild, TO), tid, name="Remy")
    assert (await moves.open_check_in(bot, guild, who(guild, TO), tid)).ok
    early = await moves.start(bot, guild, who(guild, TO), tid)
    assert early.code == "check_in_open"
    assert (
        await moves.set_check_in(bot, guild, who(guild, ADA), tid, await entrant_id(bot, tid, ADA))
    ).ok
    assert (
        await moves.set_check_in(bot, guild, who(guild, TO), tid, await entrant_id(bot, tid, BEA))
    ).ok
    closed = await moves.close_check_in(bot, guild, who(guild, TO), tid)
    assert closed.message == "Check-in for **Knuck Up 12** is closed — 1 no-show(s) taken out."
    cy = await store_.entrant_of(bot.db, tid, CY)
    assert (cy["dropped"], cy["dropped_why"]) == (1, "no_show")
    assert (await moves.start(bot, guild, who(guild, TO), tid)).ok
    row = await store_.tournament(bot.db, GUILD, tid)
    current = await store_.bracket(bot.db, row)
    names = {one["id"]: one["name"] for one in await store_.entrants(bot.db, tid)}
    assert sorted(names[one] for one in current.entrants) == ["Ada", "Bea", "Remy"]


async def test_check_in_closes_by_itself_once_its_window_passes(bot, guild):
    tid = await signed_up(bot, guild, ADA, BEA)
    await moves.open_check_in(bot, guild, who(guild, TO), tid)
    row = await store_.tournament(bot.db, GUILD, tid)
    closes = datetime.fromisoformat(row["check_in_closes_at"])
    assert await moves.close_due_check_ins(bot, guild, closes - timedelta(seconds=1)) == []
    assert await moves.close_due_check_ins(bot, guild, closes) == [tid]
    assert (await store_.tournament(bot.db, GUILD, tid))["state"] == "seeding"


async def test_starting_needs_two_entrants(bot, guild):
    tid = await signed_up(bot, guild, ADA)
    outcome = await moves.start(bot, guild, who(guild, TO), tid)
    assert (outcome.code, outcome.message) == (
        "too_few",
        "**Knuck Up 12** needs at least 2 entrants to start; it has 1.",
    )


async def test_seeding_by_hand_decides_round_one(bot, guild):
    tid = await signed_up(bot, guild, ADA, BEA, CY, format="single")
    ids = [await entrant_id(bot, tid, one) for one in (CY, ADA, BEA)]
    bad = await moves.seed(bot, guild, who(guild, TO), tid, order=ids[:2])
    assert bad.code == "bad_order"
    assert (await moves.seed(bot, guild, who(guild, TO), tid, order=ids)).ok
    await moves.start(bot, guild, who(guild, TO), tid)
    first = await the_set(bot, tid, "W1-1")
    assert (first.slot_a, first.slot_b, first.state) == (ids[0], None, "bye")
    assert (await moves.seed(bot, guild, who(guild, TO), tid, randomise=True)).code == "wrong_state"


async def test_a_player_reports_and_the_opponent_confirms_and_nobody_else_may(bot, guild):
    tid = await started(bot, guild, ADA, BEA, format="single", best_of_finals=3)
    stranger = await moves.report(bot, guild, who(guild, CY), tid, "W1-1", 2, 0)
    assert (stranger.code, stranger.status) == ("not_in_set", 403)
    reported = await moves.report(bot, guild, who(guild, ADA), tid, "W1-1", 2, 1)
    assert reported.message == (
        "W1-1 reported 2–1. It stands in 12 minute(s) unless Bea disputes it."
    )
    own = await moves.confirm(bot, guild, who(guild, ADA), tid, "W1-1")
    assert own.code == "own_report"
    final = await moves.confirm(bot, guild, who(guild, BEA), tid, "W1-1")
    assert final.message == "W1-1 is final: Ada wins 2–1."
    match = await the_set(bot, tid, "W1-1")
    assert (match.state, match.confirmed_how, match.confirmed_by) == ("complete", "opponent", BEA)
    assert [kind for kind, *_ in await rows(bot.db)][-2:] == [
        "brackets.set_reported",
        "brackets.set_confirmed",
    ]


async def test_a_score_that_does_not_fit_and_a_set_that_is_not_ready_are_refused(bot, guild):
    tid = await started(bot, guild, ADA, BEA, CY, STAFF, format="single")
    bad = await moves.report(bot, guild, who(guild, ADA), tid, "W1-1", 3, 0)
    assert (bad.code, bad.status, bad.message) == (
        "bad_score",
        400,
        "That score does not finish a best of 3: the winner has 2 game(s) and the loser fewer.",
    )
    waiting = await moves.report(bot, guild, who(guild, TO), tid, "W2-1", 2, 0)
    assert (waiting.code, waiting.message) == (
        "not_ready",
        "W2-1 is waiting for a player, so it cannot be played yet.",
    )
    missing = await moves.report(bot, guild, who(guild, TO), tid, "W9-9", 2, 0)
    assert (missing.code, missing.status) == ("no_set", 404)


async def test_a_to_report_is_final_at_once_and_reports_for_a_guest(bot, guild):
    tid = await signed_up(bot, guild, ADA, format="single", best_of_finals=3)
    await moves.add_entrant(bot, guild, who(guild, TO), tid, name="Remy")
    await moves.start(bot, guild, who(guild, TO), tid)
    outcome = await moves.report(bot, guild, who(guild, TO), tid, "W1-1", 0, 2)
    assert outcome.message == "W1-1 is final: Remy wins 2–0."
    match = await the_set(bot, tid, "W1-1")
    assert (match.state, match.confirmed_how) == ("complete", "to")
    assert (await rows(bot.db))[-1][0] == "brackets.set_overridden"


async def test_a_dispute_goes_to_the_to_who_decides_it(bot, guild):
    tid = await started(bot, guild, ADA, BEA, format="single", best_of_finals=3)
    await moves.report(bot, guild, who(guild, ADA), tid, "W1-1", 2, 0)
    disputed = await moves.dispute(bot, guild, who(guild, BEA), tid, "W1-1", "  wrong   stage ")
    assert disputed.message == "W1-1 is disputed; a tournament organiser decides it."
    assert (await the_set(bot, tid, "W1-1")).dispute_note == "wrong stage"
    to = await moves.dispute(bot, guild, who(guild, TO), tid, "W1-1", "x")
    assert to.code == "not_in_set"
    decided = await moves.override(bot, guild, who(guild, TO), tid, "W1-1", score_a=1, score_b=2)
    assert decided.message == "W1-1 is final: Bea wins 2–1."


async def test_a_forfeit_override_and_a_reset_that_clears_what_it_decided(bot, guild):
    tid = await started(bot, guild, ADA, BEA, CY, STAFF, format="single")
    ada = await entrant_id(bot, tid, ADA)
    first = await the_set(bot, tid, "W1-1")
    assert ada in (first.slot_a, first.slot_b)
    outcome = await moves.override(
        bot, guild, who(guild, TO), tid, "W1-1", winner=ada, forfeit=True
    )
    assert outcome.message == "W1-1 is final: Ada wins by forfeit."
    assert (await the_set(bot, tid, "W2-1")).slot_a == ada
    reset = await moves.reset(bot, guild, who(guild, TO), tid, "W1-1")
    assert reset.message == "W1-1 is open again; every set it decided after it is cleared."
    assert (await the_set(bot, tid, "W2-1")).slot_a is None
    member = await moves.reset(bot, guild, who(guild, ADA), tid, "W1-1")
    assert member.code == "not_organiser"


async def test_a_dq_forfeits_and_lifting_it_keeps_the_forfeit(bot, guild):
    tid = await started(bot, guild, ADA, BEA, format="single", best_of_finals=3)
    bea = await entrant_id(bot, tid, BEA)
    outcome = await moves.dq(bot, guild, who(guild, TO), tid, bea)
    assert (
        outcome.message
        == "Bea is disqualified from **Knuck Up 12**; their remaining sets are forfeited."
    )
    match = await the_set(bot, tid, "W1-1")
    assert (match.state, match.forfeit) == ("complete", "dq")
    twice = await moves.dq(bot, guild, who(guild, TO), tid, bea)
    assert twice.code == "already_out"
    assert (await moves.restore_entrant(bot, guild, who(guild, TO), tid, bea)).ok
    row = await store_.entrant(bot.db, tid, bea)
    assert (row["dq"], (await the_set(bot, tid, "W1-1")).forfeit) == (0, "dq")


async def test_a_player_dropping_mid_bracket_forfeits_their_sets(bot, guild):
    tid = await started(bot, guild, ADA, BEA, format="round_robin")
    ada = await entrant_id(bot, tid, ADA)
    outcome = await moves.drop(bot, guild, who(guild, ADA), tid, ada)
    assert outcome.ok
    entrant = await store_.entrant(bot.db, tid, ada)
    assert (entrant["dropped"], entrant["dropped_why"]) == (1, "dropped")
    assert (await the_set(bot, tid, "R1-1")).forfeit == "drop"


async def test_an_unanswered_report_stands_after_the_confirm_time(bot, guild):
    tid = await started(bot, guild, ADA, BEA, format="single", best_of_finals=3)
    await moves.report(bot, guild, who(guild, BEA), tid, "W1-1", 0, 2)
    reported = datetime.fromisoformat((await the_set(bot, tid, "W1-1")).reported_at)
    assert await moves.confirm_due(bot, guild, reported + timedelta(minutes=11)) == []
    assert await moves.confirm_due(bot, guild, reported + timedelta(minutes=12)) == [(tid, "W1-1")]
    match = await the_set(bot, tid, "W1-1")
    assert (match.state, match.confirmed_how, match.winner) == (
        "complete",
        "time",
        await entrant_id(bot, tid, BEA),
    )
    kind, actor, _, details = (await rows(bot.db))[-1]
    assert (kind, actor, details["how"], details["set"]) == (
        "brackets.set_confirmed",
        None,
        "time",
        "W1-1",
    )


async def test_completing_writes_placements_and_reopening_takes_them_back(bot, guild):
    tid = await started(bot, guild, ADA, BEA, format="single", best_of_finals=3)
    early = await moves.complete(bot, guild, who(guild, TO), tid)
    assert (early.code, early.message) == (
        "unfinished",
        "1 set(s) in **Knuck Up 12** are not final yet, so it cannot be completed.",
    )
    await moves.report(bot, guild, who(guild, TO), tid, "W1-1", 2, 0)
    assert (await moves.complete(bot, guild, who(guild, TO), tid)).ok
    placed = {one["name"]: one["placement"] for one in await store_.entrants(bot.db, tid)}
    assert placed == {"Ada": 1, "Bea": 2}
    assert (await moves.reopen(bot, guild, who(guild, TO), tid)).ok
    assert {one["placement"] for one in await store_.entrants(bot.db, tid)} == {None}


async def test_a_round_robin_tie_is_split_by_the_tos_order_at_completion(bot, guild):
    tid = await started(bot, guild, ADA, BEA, CY, format="round_robin")
    ids = {user: await entrant_id(bot, tid, user) for user in (ADA, BEA, CY)}
    row = await store_.tournament(bot.db, GUILD, tid)
    for match in (await store_.bracket(bot.db, row)).ordered():
        winner = {
            frozenset((ids[ADA], ids[BEA])): ids[ADA],
            frozenset((ids[BEA], ids[CY])): ids[BEA],
            frozenset((ids[ADA], ids[CY])): ids[CY],
        }[frozenset((match.slot_a, match.slot_b))]
        score = (2, 1) if match.slot_a == winner else (1, 2)
        assert (await moves.report(bot, guild, who(guild, TO), tid, match.key, *score)).ok
    bad = await moves.complete(bot, guild, who(guild, TO), tid, order=[ids[ADA], 999])
    assert bad.code == "bad_order"
    assert (
        await moves.complete(bot, guild, who(guild, TO), tid, order=[ids[CY], ids[ADA], ids[BEA]])
    ).ok
    placed = {one["user_id"]: one["placement"] for one in await store_.entrants(bot.db, tid)}
    assert placed == {CY: 1, ADA: 2, BEA: 3}


async def test_cancel_and_restore_put_it_back_where_it_was(bot, guild):
    tid = await signed_up(bot, guild, ADA)
    assert (await moves.cancel(bot, guild, who(guild, TO), tid)).ok
    assert (await moves.cancel(bot, guild, who(guild, TO), tid)).code == "wrong_state"
    assert (await moves.restore(bot, guild, who(guild, STAFF), tid)).ok
    assert (await store_.tournament(bot.db, GUILD, tid))["state"] == "signups"


async def test_unstart_clears_the_sets_and_goes_back_to_seeding(bot, guild):
    tid = await started(bot, guild, ADA, BEA, CY)
    assert (await moves.unstart(bot, guild, who(guild, STAFF), tid)).ok
    assert await store_.sets(bot.db, tid) == []
    assert (await store_.tournament(bot.db, GUILD, tid))["state"] == "seeding"


async def test_a_web_move_leaves_one_web_row_with_via(bot, guild):
    tid = await made(bot, guild)
    await moves.open_signups(bot, guild, who(guild, TO), tid, via=VIA_WEBSITE)
    kind, actor, _, details = (await rows(bot.db))[-1]
    assert (kind, actor, details) == (
        "web.brackets.signups_opened",
        TO,
        {"via": "website", "tournament": tid, "was": "draft"},
    )


async def test_a_tournament_from_another_server_is_not_found(bot, guild):
    tid = await made(bot, guild)
    guild.id = 1
    outcome = await moves.open_signups(bot, guild, who(guild, TO), tid)
    guild.id = GUILD
    assert (outcome.code, outcome.status) == ("no_tournament", 404)


async def test_staff_wording_is_used_and_a_broken_one_falls_back(bot, guild):
    await bot.store.set(GUILD, "brackets_created_said", "Made {name}!")
    assert (await moves.create(bot, guild, who(guild, TO), {"name": "A"})).message == "Made A!"
    bot.store._cache[(GUILD, "brackets_created_said")] = "Made {nope}!"
    assert (
        await moves.create(bot, guild, who(guild, TO), {"name": "B"})
    ).message == "Created **B**."


def test_the_lock_is_one_per_tournament():
    holder = SimpleNamespace()
    assert moves.lock_for(holder, 3) is moves.lock_for(holder, "3")
    assert moves.lock_for(holder, 3) is not moves.lock_for(holder, 4)


async def test_now_is_utc():
    assert datetime.fromisoformat(moves.now_stamp()).tzinfo == UTC
