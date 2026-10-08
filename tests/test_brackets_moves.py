from __future__ import annotations

import json
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from black_bloc import brackets_moves as moves
from black_bloc import brackets_people as people
from black_bloc import brackets_sets as sets
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
        outcome = await people.join(bot, guild, who(guild, player), tid)
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


async def test_completing_writes_placements_and_reopening_takes_them_back(bot, guild):
    tid = await started(bot, guild, ADA, BEA, format="single", best_of_finals=3)
    early = await moves.complete(bot, guild, who(guild, TO), tid)
    assert (early.code, early.message) == (
        "unfinished",
        "1 set(s) in **Knuck Up 12** are not final yet, so it cannot be completed.",
    )
    await sets.report(bot, guild, who(guild, TO), tid, "W1-1", 2, 0)
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
        assert (await sets.report(bot, guild, who(guild, TO), tid, match.key, *score)).ok
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
    tid = await made(bot, guild)
    await moves.open_signups(bot, guild, who(guild, TO), tid)
    await bot.store.set(GUILD, "brackets_joined_said", "In {name}!")
    assert (await people.join(bot, guild, who(guild, ADA), tid)).message == "In Knuck Up 12!"
    bot.store._cache[(GUILD, "brackets_joined_said")] = "In {nope}!"
    assert (
        await people.join(bot, guild, who(guild, BEA), tid)
    ).message == "You are in **Knuck Up 12**."


def test_the_lock_is_one_per_tournament():
    holder = SimpleNamespace()
    assert moves.lock_for(holder, 3) is moves.lock_for(holder, "3")
    assert moves.lock_for(holder, 3) is not moves.lock_for(holder, 4)


async def test_now_is_utc():
    assert datetime.fromisoformat(moves.now_stamp()).tzinfo == UTC


async def test_a_swiss_start_with_more_rounds_than_the_field_can_carry_is_refused(bot, guild):
    tid = await signed_up(bot, guild, ADA, BEA, CY, STAFF, format="swiss", swiss_rounds=4)
    await moves.close_signups(bot, guild, who(guild, TO), tid)
    outcome = await moves.start(bot, guild, who(guild, TO), tid)
    assert (outcome.ok, outcome.code, outcome.status) == (False, "too_many_rounds", 409)
    assert outcome.message == (
        "**Knuck Up 12** has 4 entrants, so it can play at most 3 Swiss round(s) without a "
        "rematch; it is set to 4. Lower swiss_rounds, or add entrants."
    )
    assert (await store_.tournament(bot.db, GUILD, tid))["state"] == "seeding"
    assert (await moves.edit(bot, guild, who(guild, TO), tid, {"swiss_rounds": 3})).ok
    assert (await moves.start(bot, guild, who(guild, TO), tid)).ok


@pytest.mark.parametrize(
    ("players", "given", "said"),
    [
        (4, {}, "**Knuck Up 12** has started — up to 7 set(s) to play."),
        (4, {"grand_final_reset": False}, "**Knuck Up 12** has started — 6 set(s) to play."),
        (3, {"format": "single"}, "**Knuck Up 12** has started — 2 set(s) to play."),
    ],
)
async def test_started_counts_only_the_sets_that_will_be_played(bot, guild, players, given, said):
    everyone = (ADA, BEA, CY, STAFF)[:players]
    tid = await signed_up(bot, guild, *everyone, **given)
    await moves.close_signups(bot, guild, who(guild, TO), tid)
    assert (await moves.start(bot, guild, who(guild, TO), tid)).message == said


async def test_back_to_seeding_leaves_every_entrant_a_seed_of_their_own(bot, guild):
    tid = await signed_up(bot, guild, ADA, BEA, CY, STAFF)
    bea = await entrant_id(bot, tid, BEA)
    assert (await people.drop(bot, guild, who(guild, BEA), tid, bea)).ok
    await moves.close_signups(bot, guild, who(guild, TO), tid)
    assert (await moves.start(bot, guild, who(guild, TO), tid)).ok
    assert (await moves.unstart(bot, guild, who(guild, TO), tid)).ok
    seeds = [one["seed"] for one in await store_.entrants(bot.db, tid)]
    assert sorted(seeds) == [1, 2, 3, 4]
    assert (await store_.entrant(bot.db, tid, bea))["seed"] == 4


async def test_a_staff_wording_that_breaks_in_any_way_falls_back(bot, guild):
    tid = await made(bot, guild)
    await moves.open_signups(bot, guild, who(guild, TO), tid)
    bot.store._cache[(GUILD, "brackets_joined_said")] = "In {name.nothing}!"
    joined = await people.join(bot, guild, who(guild, ADA), tid)
    assert (joined.ok, joined.message) == (True, "You are in **Knuck Up 12**.")


async def test_start_and_back_to_seeding_say_which_sets_changed(bot, guild):
    tid = await signed_up(bot, guild, ADA, BEA, CY, format="single")
    await moves.close_signups(bot, guild, who(guild, TO), tid)
    started_ = await moves.start(bot, guild, who(guild, TO), tid)
    assert started_.changed == ("W1-1", "W1-2", "W2-1")
    await store_.set_card(bot.db, tid, "W1-2", 9001, "2026-10-07T12:00:00+00:00")
    back = await moves.unstart(bot, guild, who(guild, TO), tid)
    assert (back.changed, back.gone) == (("W1-1", "W1-2", "W2-1"), {"W1-2": 9001})
    assert (await moves.open_signups(bot, guild, who(guild, TO), tid)).changed == ()


async def pooled(bot, guild, count=8, **given):
    given = {"format": "double", "pools_format": "round_robin", "best_of_finals": 3, **given}
    tid = await made(bot, guild, **given)
    for at in range(count):
        outcome = await people.add_entrant(bot, guild, who(guild, TO), tid, name=f"P{at + 1}")
        assert outcome.ok, outcome.message
    return tid


async def play_pools(bot, guild, tid, decide=None):
    row = await store_.tournament(bot.db, GUILD, tid)
    for match in (await store_.bracket(bot.db, row)).ordered():
        if match.state != "ready":
            continue
        a_wins = match.slot_a < match.slot_b if decide is None else decide(match)
        score = (2, 0) if a_wins else (0, 2)
        outcome = await sets.report(bot, guild, who(guild, TO), tid, match.key, *score)
        assert outcome.ok, outcome.message


async def test_a_pools_tournament_starts_in_pools_and_says_so(bot, guild):
    tid = await pooled(bot, guild)
    outcome = await moves.start(bot, guild, who(guild, TO), tid)
    assert outcome.ok and outcome.message == "**Knuck Up 12** has started — 12 set(s) to play."
    assert outcome.changed[:2] == ("A.R1-1", "A.R1-2")
    row = await store_.tournament(bot.db, GUILD, tid)
    assert row["state"] == "pools"
    stored = await store_.sets(bot.db, tid)
    assert {(one["phase"], one["pool"]) for one in stored} == {("pools", 1), ("pools", 2)}


async def test_advance_builds_the_final_and_back_to_pools_takes_it_away(bot, guild):
    tid = await pooled(bot, guild)
    await moves.start(bot, guild, who(guild, TO), tid)
    early = await moves.advance(bot, guild, who(guild, TO), tid)
    assert (early.code, early.message) == (
        "pools_unfinished",
        "12 pool set(s) in **Knuck Up 12** are not final yet, so it cannot advance.",
    )
    await play_pools(bot, guild, tid)
    member = await moves.advance(bot, guild, who(guild, ADA), tid)
    assert member.code == "not_organiser"
    outcome = await moves.advance(bot, guild, who(guild, TO), tid)
    assert outcome.ok, outcome.message
    assert outcome.message.startswith("**Knuck Up 12**'s final is built")
    assert "W1-1" in outcome.changed and not any("." in key for key in outcome.changed)
    row = await store_.tournament(bot.db, GUILD, tid)
    assert row["state"] == "running"
    final = {one["key"]: one for one in await store_.sets(bot.db, tid) if one["phase"] == "final"}
    assert {"W1-1", "W1-2", "G1-1"} <= set(final)
    reset = await sets.reset(bot, guild, who(guild, TO), tid, "A.R1-1")
    assert (reset.code, reset.status) == ("pools_closed", 409)
    assert "A.R1-1" in reset.message
    back = await moves.unadvance(bot, guild, who(guild, TO), tid)
    assert back.ok and set(back.changed) == set(final)
    assert (await store_.tournament(bot.db, GUILD, tid))["state"] == "pools"
    assert all(one["phase"] == "pools" for one in await store_.sets(bot.db, tid))
    assert (await sets.reset(bot, guild, who(guild, TO), tid, "A.R1-1")).ok
    kinds = [kind for kind, *_ in await rows(bot.db)]
    assert "brackets.advanced" in kinds and "brackets.unadvanced" in kinds


async def test_back_to_pools_is_refused_once_the_final_has_a_result(bot, guild):
    tid = await pooled(bot, guild)
    await moves.start(bot, guild, who(guild, TO), tid)
    await play_pools(bot, guild, tid)
    await moves.advance(bot, guild, who(guild, TO), tid)
    assert (await sets.report(bot, guild, who(guild, TO), tid, "W1-1", 2, 0)).ok
    back = await moves.unadvance(bot, guild, who(guild, TO), tid)
    assert (back.code, back.status) == ("final_played", 409)
    assert "W1-1" in back.message


async def test_a_tie_on_the_cut_names_the_players_and_the_order_settles_it(bot, guild):
    tid = await pooled(bot, guild, count=6, advance_per_pool=1)
    await moves.start(bot, guild, who(guild, TO), tid)
    row = await store_.tournament(bot.db, GUILD, tid)
    bracket = await store_.bracket(bot.db, row)
    pool_a = sorted(
        {e for m in bracket.matches.values() if m.pool == 1 for e in (m.slot_a, m.slot_b)}
    )
    x, y, z = pool_a
    beats = {frozenset((x, y)): x, frozenset((y, z)): y, frozenset((x, z)): z}
    await play_pools(
        bot,
        guild,
        tid,
        decide=lambda m: beats.get(frozenset((m.slot_a, m.slot_b)), min(m.slot_a, m.slot_b))
        == m.slot_a,
    )
    tied = await moves.advance(bot, guild, who(guild, TO), tid)
    assert tied.code == "pool_tie"
    named = {one["id"]: one["name"] for one in await store_.entrants(bot.db, tid)}
    assert tied.message.startswith("Pool A is tied across the top 1: ")
    assert all(named[one] in tied.message for one in pool_a)
    bad = await moves.advance(bot, guild, who(guild, TO), tid, order=[999])
    assert bad.code == "bad_order"
    outcome = await moves.advance(bot, guild, who(guild, TO), tid, order=[z, x, y])
    assert outcome.ok, outcome.message
    seated = {e for one in await store_.sets(bot.db, tid) if one["phase"] == "final"
              for e in (one["slot_a"], one["slot_b"]) if e}
    assert z in seated and x not in seated


async def test_completing_a_pools_tournament_places_everyone(bot, guild):
    tid = await pooled(bot, guild)
    await moves.start(bot, guild, who(guild, TO), tid)
    await play_pools(bot, guild, tid)
    await moves.advance(bot, guild, who(guild, TO), tid)
    early = await moves.complete(bot, guild, who(guild, TO), tid)
    assert early.code == "unfinished"
    await play_pools(bot, guild, tid)
    await play_pools(bot, guild, tid)
    await play_pools(bot, guild, tid)
    await play_pools(bot, guild, tid)
    assert (await moves.complete(bot, guild, who(guild, TO), tid)).ok
    placed = sorted(one["placement"] for one in await store_.entrants(bot.db, tid))
    assert placed == [1, 2, 3, 4, 5, 5, 7, 7]


async def test_pools_need_an_elimination_bracket_and_a_round_robin_drops_the_default(bot, guild):
    bad = await moves.create(
        bot, guild, who(guild, TO), {"name": "x", "format": "swiss", "pools_format": "swiss"}
    )
    assert (bad.code, bad.status) == ("pools_need_elimination", 400)
    await bot.store.set(GUILD, "brackets_pools_format_default", "round_robin")
    plain = await made(bot, guild, format="round_robin")
    assert (await store_.tournament(bot.db, GUILD, plain))["pools_format"] == "none"
    pooled_default = await made(bot, guild)
    assert (await store_.tournament(bot.db, GUILD, pooled_default))["pools_format"] == (
        "round_robin"
    )
    edit = await moves.edit(bot, guild, who(guild, TO), pooled_default, {"format": "swiss"})
    assert edit.code == "pools_need_elimination"
    wrong = await moves.edit(bot, guild, who(guild, TO), plain, {"pools_format": "ladder"})
    assert wrong.code == "bad_option"


async def test_a_field_too_small_for_its_pools_is_refused_at_the_start(bot, guild):
    tid = await pooled(bot, guild, count=5, pool_count=3)
    outcome = await moves.start(bot, guild, who(guild, TO), tid)
    assert (outcome.code, outcome.message) == (
        "too_few_for_pools",
        "**Knuck Up 12** has 5 entrants, too few for 3 pools of at least 2 each.",
    )


async def test_back_to_seeding_from_pools_clears_every_set(bot, guild):
    tid = await pooled(bot, guild)
    await moves.start(bot, guild, who(guild, TO), tid)
    outcome = await moves.unstart(bot, guild, who(guild, TO), tid)
    assert outcome.ok and len(outcome.changed) == 12
    assert await store_.sets(bot.db, tid) == []
