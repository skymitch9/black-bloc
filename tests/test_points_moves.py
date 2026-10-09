from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from black_bloc import points_moves as moves
from black_bloc import points_store as store_
from black_bloc.config import load_settings
from black_bloc.logkinds import VIA_WEBSITE
from black_bloc.points.model import APPROVED, PENDING, REJECTED, REMOVED
from black_bloc.settings_store import SettingsStore

GUILD = 4242
STAFF = 7
VERA = 9
ADA = 21
BEA = 22
CY = 23
VERIFIER_ROLE = 556
PROOF = "https://youtu.be/abc123"


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
        self.roles = {VERIFIER_ROLE: Role(id=VERIFIER_ROLE, name="Mentor")}

    def get_member(self, user_id):
        return self.members.get(int(user_id))

    def get_role(self, role_id):
        return self.roles.get(int(role_id))

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


def make_guild():
    found = Guild()
    found.add(STAFF, "Sky")
    found.add(VERA, "Vera", VERIFIER_ROLE)
    found.add(ADA, "Ada")
    found.add(BEA, "Bea")
    found.add(CY, "Cy")
    return found


async def make_bot(db, guild):
    store = SettingsStore(db, load_settings(_env_file=None))
    await store.load()
    store.is_staff = lambda member: getattr(member, "id", None) == STAFF
    await store.set(GUILD, "points_verifier_role_id", VERIFIER_ROLE)
    return Bot(db, store, guild)


@pytest.fixture
def guild():
    return make_guild()


@pytest.fixture
async def bot(db, guild, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    return await make_bot(db, guild)


def who(guild, user_id):
    return guild.get_member(user_id)


async def rows(db, like="%points.%"):
    cur = await db.conn.execute(
        "SELECT kind, actor_id, target_id, reason, details FROM action_log "
        "WHERE kind LIKE ? ORDER BY id",
        (like,),
    )
    return [
        (row["kind"], row["actor_id"], row["target_id"], json.loads(row["details"] or "{}"))
        for row in await cur.fetchall()
    ]


async def kinds(db):
    return [one[0] for one in await rows(db)]


async def submitted(bot, guild, by=ADA, **given):
    outcome = await moves.submit(
        bot,
        guild,
        who(guild, by),
        {"game": "Celeste", "time": "30:00", "proof_url": PROOF, **given},
    )
    assert outcome.ok, outcome.message
    return outcome.value.id


async def approved(bot, guild, by=ADA, **given):
    run_id = await submitted(bot, guild, by, **given)
    outcome = await moves.approve(bot, guild, who(guild, STAFF), run_id)
    assert outcome.ok, outcome.message
    return run_id


async def test_a_member_submits_a_run_that_waits_for_staff(bot, guild):
    outcome = await moves.submit(
        bot,
        guild,
        who(guild, ADA),
        {"game": " Celeste ", "category": "Any%", "time": "1:23:45.67", "proof_url": PROOF},
        via=VIA_WEBSITE,
    )

    assert outcome.ok
    assert outcome.message == (
        "Your **Celeste** run (1:23:45.67) is in. Staff check the proof before it counts."
    )
    assert outcome.changed == (f"run:{outcome.value.id}",)
    row = await store_.run(bot.db, GUILD, outcome.value.id)
    assert (row["user_id"], row["game"], row["category"], row["seconds"], row["state"]) == (
        ADA,
        "Celeste",
        "Any%",
        5025.67,
        PENDING,
    )
    ((kind, actor, target, details),) = await rows(bot.db)
    assert (kind, actor, target, details["via"], details["run"]) == (
        "web.points.submitted",
        ADA,
        ADA,
        "website",
        outcome.value.id,
    )


@pytest.mark.parametrize(
    ("given", "code", "words"),
    [
        ({"game": ""}, "no_game", "A run needs its game, at most 100 characters"),
        ({"game": "x" * 101}, "no_game", "at most 100 characters"),
        ({"time": ""}, "no_time", "A run needs its time"),
        ({"time": "fast"}, "bad_time", "**fast** is not a time Black Bloc can read"),
        ({"proof_url": ""}, "no_proof", "A run needs a link to its video or image"),
        ({"proof_url": "my clip"}, "bad_proof", "**my clip** is not a link"),
        ({"proof_url": "https://nowhere"}, "bad_proof", "is not a link"),
        ({"category": "c" * 101}, "too_long", "The category can be at most 100 characters"),
        ({"note": "n" * 301}, "too_long", "The note can be at most 300 characters"),
    ],
)
async def test_a_submission_missing_what_pawpette_asked_for_is_refused_in_words(
    bot, guild, given, code, words
):
    outcome = await moves.submit(
        bot,
        guild,
        who(guild, ADA),
        {"game": "Celeste", "time": "30:00", "proof_url": PROOF, **given},
    )

    assert (outcome.ok, outcome.code, outcome.status) == (False, code, 400)
    assert words in outcome.message
    assert await store_.runs(bot.db, GUILD) == []


async def test_staff_may_submit_for_a_member_and_a_member_may_not(bot, guild):
    run_id = await submitted(bot, guild, STAFF, user_id=str(BEA))
    assert (await store_.run(bot.db, GUILD, run_id))["user_id"] == BEA

    refused = await moves.submit(
        bot,
        guild,
        who(guild, ADA),
        {"game": "Celeste", "time": "1:00", "proof_url": PROOF, "user_id": BEA},
    )
    assert (refused.ok, refused.code) == (False, "not_staff")
    own = await moves.submit(
        bot,
        guild,
        who(guild, ADA),
        {"game": "Celeste", "time": "1:00", "proof_url": PROOF, "user_id": str(ADA)},
    )
    assert own.ok


async def test_while_off_every_move_refuses_and_nothing_is_written(bot, guild):
    run_id = await submitted(bot, guild)
    await bot.store.set(GUILD, "points_mode", "off")

    for outcome in (
        await moves.submit(bot, guild, who(guild, ADA), {"game": "x"}),
        await moves.approve(bot, guild, who(guild, STAFF), run_id),
        await moves.recompute(bot, guild, who(guild, STAFF)),
        await moves.bounty_create(bot, guild, who(guild, STAFF), {"name": "b"}),
    ):
        assert (outcome.ok, outcome.code, outcome.status) == (False, "points_off", 409)
        assert "switched **off**" in outcome.message
    assert (await store_.run(bot.db, GUILD, run_id))["state"] == PENDING


async def test_approving_scores_the_run_and_rehearses_the_top_places_post(bot, guild):
    run_id = await submitted(bot, guild)

    outcome = await moves.approve(bot, guild, who(guild, STAFF), run_id, via=VIA_WEBSITE)

    assert outcome.ok
    assert outcome.message == "Approved Ada's **Celeste** run (30:00) — 100 XP, 10 speedpoints."
    assert outcome.changed == (f"run:{run_id}", "board", "top")
    assert outcome.value.announce == ("Ada is in the top 10 at #1 with 10 speedpoints.",)
    row = await store_.run(bot.db, GUILD, run_id)
    assert (row["state"], row["xp"], row["speedpoints"], row["decided_by"]) == (
        APPROVED,
        100,
        10,
        STAFF,
    )
    assert await kinds(bot.db) == [
        "points.submitted",
        "web.points.approved",
        "web.points.would_announce",
    ]
    announced = (await rows(bot.db))[-1][3]
    assert announced["changes"] == [{"kind": "entered", "user_id": ADA, "was": None, "now": 1}]


async def test_with_the_mode_on_the_board_change_is_logged_as_the_real_thing(bot, guild):
    await bot.store.set(GUILD, "points_mode", "on")
    await approved(bot, guild)
    assert (await kinds(bot.db))[-1] == "points.top_changed"


async def test_xp_follows_the_tiers_and_speedpoints_are_ten_a_run(bot, guild):
    for time, xp in (("0:59", 5), ("1:00", 5), ("9:59", 5), ("10:00", 25), ("15:00", 50)):
        run_id = await approved(bot, guild, time=time)
        row = await store_.run(bot.db, GUILD, run_id)
        assert (row["xp"], row["speedpoints"]) == (xp, 10), time
    board = await moves.board(bot, GUILD)
    assert [(one.user_id, one.runs, one.xp, one.speedpoints) for one in board] == [(ADA, 5, 90, 50)]


async def test_a_verifier_approves_but_never_their_own_run_and_a_member_cannot(bot, guild):
    ada_run = await submitted(bot, guild)
    vera_run = await submitted(bot, guild, VERA)

    refused = await moves.approve(bot, guild, who(guild, BEA), ada_run)
    assert (refused.code, refused.status) == ("not_verifier", 403)
    assert refused.message == "Approving runs is for staff and **Mentor**, so nothing was done."
    own = await moves.approve(bot, guild, who(guild, VERA), vera_run)
    assert (own.code, own.message) == (
        "own_run",
        "You submitted that run, so someone else approves it.",
    )
    assert (await moves.approve(bot, guild, who(guild, VERA), ada_run)).ok
    staff_run = await submitted(bot, guild, STAFF)
    assert (await moves.approve(bot, guild, who(guild, STAFF), staff_run)).ok


async def test_without_a_verifier_role_the_refusal_says_none_is_picked(bot, guild):
    await bot.store.clear(GUILD, "points_verifier_role_id")
    run_id = await submitted(bot, guild)

    refused = await moves.reject(bot, guild, who(guild, VERA), run_id)

    assert "staff have not picked one yet" in refused.message


async def test_a_rejected_run_needs_a_staff_edit_before_it_can_be_approved(bot, guild):
    run_id = await submitted(bot, guild)

    rejected = await moves.reject(bot, guild, who(guild, VERA), run_id, "  no timer  in shot ")
    assert rejected.ok and rejected.message == "Rejected Ada's **Celeste** run (30:00)."
    assert rejected.value.dm == (
        "Your **Celeste** run (30:00) was not approved. Staff said: no timer in shot"
    )
    assert rejected.value.dm_to == ADA
    row = await store_.run(bot.db, GUILD, run_id)
    assert (row["state"], row["reason"]) == (REJECTED, "no timer in shot")

    again = await moves.approve(bot, guild, who(guild, STAFF), run_id)
    assert (again.code, again.status) == ("wrong_state", 409)
    assert again.message == "That run is not approved, so that cannot be done now."
    by_verifier = await moves.edit(bot, guild, who(guild, VERA), run_id, {"time": "29:00"})
    assert by_verifier.code == "not_staff"

    reopened = await moves.edit(bot, guild, who(guild, STAFF), run_id, {"proof_url": PROOF + "2"})
    assert reopened.message == (
        "Saved Ada's **Celeste** run (30:00); it is waiting for a decision again."
    )
    row = await store_.run(bot.db, GUILD, run_id)
    assert (row["state"], row["reason"], row["decided_by"], row["proof_url"]) == (
        PENDING,
        None,
        None,
        PROOF + "2",
    )
    assert (await moves.approve(bot, guild, who(guild, STAFF), run_id)).ok


async def test_a_rejection_with_no_reason_says_so_in_the_dm(bot, guild):
    run_id = await submitted(bot, guild)
    outcome = await moves.reject(bot, guild, who(guild, STAFF), run_id)
    assert outcome.value.dm.endswith("was not approved. Staff gave no reason.")


async def test_removing_an_approved_run_takes_it_off_the_board_and_tells_the_member(bot, guild):
    run_id = await approved(bot, guild)
    await approved(bot, guild, BEA, time="10:00")

    by_verifier = await moves.remove(bot, guild, who(guild, VERA), run_id, "dupe")
    assert by_verifier.code == "not_staff"
    outcome = await moves.remove(bot, guild, who(guild, STAFF), run_id, "dupe")

    assert (
        outcome.ok and outcome.message == "Took Ada's **Celeste** run (30:00) off the leaderboard."
    )
    assert outcome.value.dm == (
        "Your **Celeste** run (30:00) was taken off the leaderboard. Staff said: dupe"
    )
    assert outcome.value.announce == (
        "Bea moved up to #1 (was #2).",
        "Ada dropped out of the top 10.",
    )
    assert [one.user_id for one in await moves.board(bot, GUILD)] == [BEA]
    assert (await store_.run(bot.db, GUILD, run_id))["state"] == REMOVED
    pending = await submitted(bot, guild)
    assert (await moves.remove(bot, guild, who(guild, STAFF), pending)).code == "wrong_state"


async def test_a_removed_run_can_be_put_back_by_a_staff_edit_and_a_fresh_approval(bot, guild):
    run_id = await approved(bot, guild)
    await moves.remove(bot, guild, who(guild, STAFF), run_id)

    reopened = await moves.edit(bot, guild, who(guild, STAFF), run_id, {})
    assert reopened.ok and "waiting for a decision again" in reopened.message
    assert (await moves.approve(bot, guild, who(guild, STAFF), run_id)).ok
    assert [one.user_id for one in await moves.board(bot, GUILD)] == [ADA]


async def test_editing_an_approved_run_rescores_it(bot, guild):
    run_id = await approved(bot, guild)

    outcome = await moves.edit(
        bot, guild, who(guild, STAFF), run_id, {"time": "9:00", "category": "Any%"}
    )

    assert outcome.ok and outcome.message == "Saved Ada's **Celeste** run (9:00)."
    row = await store_.run(bot.db, GUILD, run_id)
    assert (row["state"], row["seconds"], row["xp"], row["category"]) == (APPROVED, 540, 5, "Any%")
    edited = (await rows(bot.db))[-1]
    assert edited[0] == "points.edited"
    assert edited[3]["changed"] == ["category", "seconds"]
    nothing = await moves.edit(bot, guild, who(guild, STAFF), run_id, {})
    assert nothing.code == "nothing_to_edit"


async def test_two_approvals_at_once_count_the_run_once(bot, guild):
    run_id = await submitted(bot, guild)

    first, second = await asyncio.gather(
        moves.approve(bot, guild, who(guild, STAFF), run_id),
        moves.approve(bot, guild, who(guild, VERA), run_id),
    )

    assert sorted([first.ok, second.ok]) == [False, True]
    assert (await kinds(bot.db)).count("points.approved") == 1


async def test_an_unknown_run_is_refused_in_words(bot, guild):
    outcome = await moves.approve(bot, guild, who(guild, STAFF), 999)
    assert (outcome.code, outcome.status, outcome.message) == (
        "no_run",
        404,
        "There is no run 999 here, so nothing was done.",
    )


def window(hours_before=1, hours_after=1):
    at = datetime.now(UTC)
    return (
        (at - timedelta(hours=hours_before)).isoformat(),
        (at + timedelta(hours=hours_after)).isoformat(),
    )


async def bounty(bot, guild, **given):
    starts, ends = window()
    outcome = await moves.bounty_create(
        bot,
        guild,
        who(guild, STAFF),
        {
            "name": "Celeste month",
            "games": ["celeste"],
            "kind": "extra",
            "amount": 15,
            "starts_at": starts,
            "ends_at": ends,
            **given,
        },
    )
    assert outcome.ok, outcome.message
    return outcome.value.id


async def test_a_live_bounty_adds_to_the_runs_speedpoints_and_says_which(bot, guild):
    bounty_id = await bounty(bot, guild)
    run_id = await submitted(bot, guild)

    outcome = await moves.approve(bot, guild, who(guild, STAFF), run_id)

    assert outcome.message == (
        "Approved Ada's **Celeste** run (30:00) — 100 XP, 25 speedpoints with the bounty "
        "**Celeste month**."
    )
    row = await store_.run(bot.db, GUILD, run_id)
    assert (row["speedpoints"], row["bounty_id"]) == (25, bounty_id)
    other = await approved(bot, guild, game="Hades")
    assert (await store_.run(bot.db, GUILD, other))["speedpoints"] == 10


async def test_the_best_bounty_wins_when_several_are_live(bot, guild):
    await bounty(bot, guild, kind="extra", amount=5)
    doubled = await bounty(bot, guild, name="Double", kind="multiplier", amount=2)
    run_id = await approved(bot, guild)
    row = await store_.run(bot.db, GUILD, run_id)
    assert (row["speedpoints"], row["bounty_id"]) == (20, doubled)


async def add_event(db, status, starts, ends):
    cur = await db.conn.execute(
        "INSERT INTO events(guild_id, requester_id, title, starts_at, ends_at, status, "
        "created_at) VALUES (?, 1, 'Speedrun Saturday', ?, ?, ?, ?)",
        (GUILD, starts, ends, status, datetime.now(UTC).isoformat()),
    )
    await db.conn.commit()
    return int(cur.lastrowid)


async def test_an_event_bounty_is_live_while_its_event_is(bot, guild):
    starts, ends = window()
    on = await add_event(bot.db, "approved", starts, ends)
    cancelled = await add_event(bot.db, "cancelled", starts, ends)
    later = await add_event(bot.db, "approved", *window(-5, 6))
    for event_id in (cancelled, later):
        await bounty(
            bot,
            guild,
            name=f"Ev {event_id}",
            event_id=event_id,
            starts_at=None,
            ends_at=None,
            amount=99,
        )
    tied = await bounty(bot, guild, name="Saturday", event_id=on, starts_at=None, ends_at=None)

    run_id = await approved(bot, guild)

    row = await store_.run(bot.db, GUILD, run_id)
    assert (row["speedpoints"], row["bounty_id"]) == (25, tied)


async def test_the_bounty_clock_can_judge_by_the_submission_instead(bot, guild):
    starts, ends = window(3, -2)
    await bounty(bot, guild, starts_at=starts, ends_at=ends)
    inside = (datetime.now(UTC) - timedelta(hours=2, minutes=30)).isoformat()
    run_id = await store_.add_run(
        bot.db, GUILD, ADA, {"game": "Celeste", "seconds": 60, "proof_url": PROOF}, at=inside
    )
    late = await store_.add_run(
        bot.db, GUILD, BEA, {"game": "Celeste", "seconds": 60, "proof_url": PROOF}, at=inside
    )

    await moves.approve(bot, guild, who(guild, STAFF), run_id)
    assert (await store_.run(bot.db, GUILD, run_id))["speedpoints"] == 10
    await bot.store.set(GUILD, "points_bounty_clock", "submitted")
    await moves.approve(bot, guild, who(guild, STAFF), late)
    assert (await store_.run(bot.db, GUILD, late))["speedpoints"] == 25


async def test_recompute_applies_todays_settings_to_every_approved_run(bot, guild):
    first = await approved(bot, guild)
    await approved(bot, guild, BEA, time="5:00")
    await bot.store.set(GUILD, "points_per_run", 20)
    await bot.store.set(GUILD, "points_xp_tiers", "1:00=1, 30:00=7")

    refused = await moves.recompute(bot, guild, who(guild, VERA))
    assert refused.code == "not_staff"
    outcome = await moves.recompute(bot, guild, who(guild, STAFF), via=VIA_WEBSITE)

    assert outcome.message == "Recomputed the approved runs: 2 of 2 changed."
    row = await store_.run(bot.db, GUILD, first)
    assert (row["xp"], row["speedpoints"]) == (7, 20)
    assert "web.points.recomputed" in await kinds(bot.db)
    again = await moves.recompute(bot, guild, who(guild, STAFF))
    assert again.message == "Recomputed the approved runs: 0 of 2 changed."


async def test_a_board_change_below_the_top_is_not_announced(bot, guild):
    await bot.store.set(GUILD, "points_top_n", 1)
    await approved(bot, guild)
    await approved(bot, guild)
    third = await submitted(bot, guild, BEA)

    outcome = await moves.approve(bot, guild, who(guild, STAFF), third)

    assert outcome.value.announce == ()
    assert outcome.changed == (f"run:{third}", "board")


async def test_staff_wording_that_cannot_be_filled_falls_back_to_the_shipped_words(bot, guild):
    real = bot.store.get
    bot.store.get = lambda gid, key: "{nope}" if key == "points_submitted_said" else real(gid, key)

    outcome = await moves.submit(
        bot, guild, who(guild, ADA), {"game": "Celeste", "time": "1:00", "proof_url": PROOF}
    )

    assert outcome.message.startswith("Your **Celeste** run (1:00) is in.")


async def test_a_game_name_cannot_smuggle_markdown_into_the_words(bot, guild):
    outcome = await moves.submit(
        bot,
        guild,
        who(guild, ADA),
        {"game": "**Big** [link](x)", "time": "1:00", "proof_url": PROOF},
    )
    assert "\\*\\*Big\\*\\*" in outcome.message


@pytest.mark.parametrize(
    ("given", "code"),
    [
        ({"name": ""}, "bad_bounty_name"),
        ({"games": []}, "bad_bounty_games"),
        ({"games": ["x" * 101]}, "bad_bounty_games"),
        ({"kind": "double"}, "bad_bounty_kind"),
        ({"kind": "multiplier", "amount": 1}, "bad_bounty_amount"),
        ({"kind": "multiplier", "amount": 11}, "bad_bounty_amount"),
        ({"kind": "extra", "amount": 1.5}, "bad_bounty_amount"),
        ({"kind": "extra", "amount": "lots"}, "bad_bounty_amount"),
        ({"starts_at": None, "ends_at": None}, "bad_bounty_window"),
        ({"event_id": 5}, "bad_bounty_window"),
        ({"starts_at": None, "ends_at": None, "event_id": 99999}, "no_event"),
        ({"starts_at": "soon"}, "bad_bounty_date"),
        ({"starts_at": "2026-10-10", "ends_at": "2026-10-09"}, "bounty_ends_first"),
    ],
)
async def test_a_bounty_that_cannot_work_is_refused_in_words(bot, guild, given, code):
    starts, ends = window()
    outcome = await moves.bounty_create(
        bot,
        guild,
        who(guild, STAFF),
        {
            "name": "B",
            "games": ["Celeste"],
            "kind": "extra",
            "amount": 5,
            "starts_at": starts,
            "ends_at": ends,
            **given,
        },
    )
    assert (outcome.ok, outcome.code, outcome.status) == (
        False,
        code,
        400 if code != "no_event" else 400,
    )
    assert outcome.message.endswith(".")
    assert await store_.bounties(bot.db, GUILD) == []


async def test_a_bare_end_date_counts_the_whole_day_in_the_servers_zone(bot, guild):
    bounty_id = await bounty(bot, guild, starts_at="2026-10-01", ends_at="2026-10-31")
    row = await store_.bounty(bot.db, GUILD, bounty_id)
    assert (row["starts_at"], row["ends_at"]) == (
        "2026-10-01T07:00:00+00:00",
        "2026-11-01T07:00:00+00:00",
    )


async def test_staff_edit_and_end_a_bounty_and_only_staff(bot, guild):
    bounty_id = await bounty(bot, guild)
    member = await moves.bounty_create(bot, guild, who(guild, VERA), {"name": "mine"})
    assert member.code == "not_staff"

    saved = await moves.bounty_edit(
        bot, guild, who(guild, STAFF), bounty_id, {"name": "Spooky", "games": "Hades"}
    )
    assert saved.message == "Saved the bounty **Spooky**."
    row = await store_.bounty(bot.db, GUILD, bounty_id)
    assert (row["name"], store_.games_of(row), row["amount"]) == ("Spooky", ["Hades"], 15)

    starts, ends = window()
    event = await add_event(bot.db, "approved", starts, ends)
    moved = await moves.bounty_edit(bot, guild, who(guild, STAFF), bounty_id, {"event_id": event})
    assert moved.ok
    row = await store_.bounty(bot.db, GUILD, bounty_id)
    assert (row["event_id"], row["starts_at"], row["ends_at"]) == (event, None, None)

    ended = await moves.bounty_end(bot, guild, who(guild, STAFF), bounty_id)
    assert ended.message == "Ended the bounty **Spooky**."
    assert not (await store_.bounty(bot.db, GUILD, bounty_id))["active"]
    twice = await moves.bounty_end(bot, guild, who(guild, STAFF), bounty_id)
    assert (twice.code, twice.status) == ("already_ended", 409)
    back = await moves.bounty_edit(bot, guild, who(guild, STAFF), bounty_id, {"active": True})
    assert back.ok and (await store_.bounty(bot.db, GUILD, bounty_id))["active"]
    assert (await moves.bounty_end(bot, guild, who(guild, STAFF), 999)).code == "no_bounty"
    assert [one[0] for one in await rows(bot.db, "%bounty%")] == [
        "points.bounty_set",
        "points.bounty_set",
        "points.bounty_set",
        "points.bounty_ended",
        "points.bounty_set",
    ]


async def test_an_ended_bounty_gives_nothing(bot, guild):
    bounty_id = await bounty(bot, guild)
    await moves.bounty_end(bot, guild, who(guild, STAFF), bounty_id)
    run_id = await approved(bot, guild)
    assert (await store_.run(bot.db, GUILD, run_id))["speedpoints"] == 10


async def test_a_run_submitted_through_a_ticket_is_decided_by_that_ticket(bot, guild):
    outcome = await moves.submit(
        bot,
        guild,
        who(guild, ADA),
        {"game": "Celeste", "time": "30:00", "proof_url": PROOF, "ticket_id": 999},
        ticket_id=41,
    )
    other = await submitted(bot, guild, BEA)

    assert (await store_.run(bot.db, GUILD, outcome.value.id))["ticket_id"] == 41
    assert (await store_.run(bot.db, GUILD, other))["ticket_id"] is None
    approved_by_ticket = await moves.approve(bot, guild, who(guild, STAFF), ticket_id=41)
    assert approved_by_ticket.ok and approved_by_ticket.value.id == outcome.value.id
    removed = await moves.remove(bot, guild, who(guild, STAFF), reason="dupe", ticket_id=41)
    assert removed.ok and removed.value.dm_to == ADA
    second = await moves.submit(
        bot,
        guild,
        who(guild, BEA),
        {"game": "Hades", "time": "1:00", "proof_url": PROOF},
        ticket_id=42,
    )
    rejected = await moves.reject(bot, guild, who(guild, VERA), None, "blurry", ticket_id=42)
    assert rejected.ok and rejected.value.id == second.value.id
    missing = await moves.approve(bot, guild, who(guild, STAFF), ticket_id=43)
    assert (missing.code, missing.message) == (
        "no_run",
        "There is no run for ticket 43 here, so nothing was done.",
    )
    nothing = await moves.approve(bot, guild, who(guild, STAFF))
    assert nothing.code == "no_run"


async def test_one_ticket_carries_one_run(bot, guild):
    import sqlite3

    await store_.add_run(
        bot.db, GUILD, ADA, {"game": "x", "seconds": 1, "proof_url": PROOF, "ticket_id": 7}
    )
    with pytest.raises(sqlite3.IntegrityError):
        await store_.add_run(
            bot.db, GUILD, BEA, {"game": "y", "seconds": 1, "proof_url": PROOF, "ticket_id": 7}
        )
    await bot.db.conn.rollback()
