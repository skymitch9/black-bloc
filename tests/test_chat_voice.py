import json
import random
from datetime import UTC, datetime, timedelta

import pytest

from black_bloc import tone_keys
from black_bloc.chat_memory import forget, forget_everywhere
from black_bloc.chat_voice import (
    DRIFTED,
    FEEDBACK,
    NAMED,
    NEW,
    PINNED,
    ROLLED,
    SET,
    SETTLED,
    SETTLING,
    TONE_OFF,
    UNTIL_STAFF,
    Heard,
    Settle,
    another,
    avoid_span,
    claim_feedback,
    drift_chance,
    eased,
    fed_already,
    heard_for,
    heard_from,
    hears_now,
    move_for_feedback,
    order_of,
    pin,
    remember_heard,
    roster,
    set_tone,
    settle_of,
    settled_share,
    settled_word,
    state_of,
    step_toward,
    stored_tone,
    talking_now,
    unpin,
    voice_key,
    voice_row,
    voice_rows,
    window_turns,
)
from black_bloc.personas import (
    BY_NAME,
    COOKOUT,
    DRIFT_CHANCE,
    DRIFT_EVERY_TURNS,
    POOL,
    TROPE_NAMES,
    enabled_tropes,
    from_the_pool,
)
from black_bloc.storage.db import Database

GUILD = 7
NOW = datetime(2026, 9, 23, 18, 0, tzinfo=UTC)


def rows(*names, enabled=True):
    return [
        {
            "name": name,
            "label": BY_NAME[name].label,
            "voice": BY_NAME[name].voice,
            "neighbours": json.dumps(list(BY_NAME[name].neighbours)),
            "enabled": 1 if enabled else 0,
        }
        for name in names
    ]


def row(**given):
    found = {"trope": None, "turns": 0, "since": None, "pinned": None, "pinned_by": None,
             "pinned_at": None, "user_id": 900}
    found.update(given)
    return found


@pytest.fixture
async def db(tmp_path):
    found = Database(tmp_path / "v.sqlite3")
    await found.connect()
    try:
        yield found
    finally:
        await found.close()


async def a_turn(db, user_id, channel_id, at, tier="simple"):
    await db.conn.execute(
        "INSERT INTO chat_window(guild_id, channel_id, user_id, at, speaker, content, tier) "
        "VALUES (?, ?, ?, ?, 'bot', 'hi', ?)",
        (GUILD, channel_id, user_id, at.isoformat(), tier),
    )
    await db.conn.commit()


def test_the_cookout_setting_is_no_tone_for_anybody_even_a_pinned_member():
    found = heard_from(COOKOUT, rows(*TROPE_NAMES), row(pinned="noir"), guild_id=GUILD,
                       user_id=900, turns=3, now=NOW)
    assert found == Heard(None)
    assert found.name == COOKOUT


def test_a_pin_beats_a_named_mood_and_the_pool():
    for setting in (POOL, "warm"):
        found = heard_from(setting, rows(*TROPE_NAMES), row(pinned="noir"), guild_id=GUILD,
                           user_id=900, turns=0, now=NOW)
        assert (found.name, found.source) == ("noir", PINNED)


def test_a_pin_to_a_mood_that_is_off_falls_through_to_the_setting():
    pool = rows("warm") + rows("noir", enabled=False)
    found = heard_from("warm", pool, row(pinned="noir"), guild_id=GUILD, user_id=900, turns=0,
                       now=NOW)
    assert (found.name, found.source) == ("warm", NAMED)


def test_a_named_mood_is_that_mood_for_everybody_without_a_pin():
    found = heard_from("deadpan", rows(*TROPE_NAMES), None, guild_id=GUILD, user_id=900, turns=0,
                       now=NOW)
    assert (found.name, found.source) == ("deadpan", NAMED)


def test_the_roll_is_seeded_by_guild_member_and_when_their_window_opened():
    pool = rows(*TROPE_NAMES)
    found = heard_from(POOL, pool, None, guild_id=GUILD, user_id=900, turns=0, now=NOW)
    assert found.source == ROLLED
    assert found.since == NOW.isoformat()
    from black_bloc.personas import enabled_tropes

    wanted = from_the_pool(enabled_tropes(pool), voice_key(GUILD, 900, NOW.isoformat()), 0)
    assert found.name == wanted.name


def test_an_open_window_keeps_its_start_and_the_stored_tone():
    since = (NOW - timedelta(minutes=10)).isoformat()
    kept = row(since=since, trope="warm", tone="warm", how=ROLLED, heard=1)
    found = heard_from(POOL, rows(*TROPE_NAMES), kept, guild_id=GUILD, user_id=900, turns=2,
                       now=NOW, settle=NEVER)
    assert found.since == since and found.turns == 2
    assert (found.name, found.settled, found.heard) == ("warm", 0, 2)


def test_an_empty_window_starts_a_new_conversation_from_the_stored_tone():
    since = (NOW - timedelta(hours=2)).isoformat()
    kept = row(since=since, trope="noir", tone="noir", how=ROLLED, settled=2, heard=1)
    found = heard_from(POOL, rows(*TROPE_NAMES), kept, guild_id=GUILD, user_id=900, turns=0,
                       now=NOW, settle=NEVER)
    assert found.since == NOW.isoformat() and found.turns == 0
    assert (found.name, found.settled, found.stored) == ("noir", 3, True)


def test_a_row_from_before_tones_were_stored_has_none_and_is_rolled_once():
    for old in (row(trope=COOKOUT), row(trope=None), None):
        found = heard_from(POOL, rows(*TROPE_NAMES), old, guild_id=GUILD, user_id=900, turns=0,
                           now=NOW)
        assert found.stored is True and found.how == ROLLED and found.settled == 0
        assert found.name in TROPE_NAMES


def test_the_chance_of_a_step_halves_and_never_goes_under_the_floor():
    settle = Settle(start=0.25, halves=4, floor=0.02)
    assert drift_chance(0, settle) == 0.25
    assert drift_chance(4, settle) == 0.125
    assert drift_chance(8, settle) == 0.0625
    assert drift_chance(16, settle) == 0.02
    assert drift_chance(10_000, settle) == 0.02
    found = [drift_chance(n, settle) for n in range(0, 60)]
    assert all(later <= earlier for earlier, later in zip(found, found[1:], strict=False))
    assert min(found) == 0.02 and max(found) == 0.25


def test_the_chance_takes_a_zero_floor_a_start_of_nothing_and_never_settling():
    assert drift_chance(400, Settle(start=0.25, halves=4, floor=0.0)) < 1e-20
    assert drift_chance(0, Settle(start=0.0, halves=4, floor=0.02)) == 0.0
    assert drift_chance(50, Settle(start=0.25, halves=0, floor=0.02)) == 0.25
    assert drift_chance(-3, Settle()) == DRIFT_CHANCE
    assert drift_chance(None, Settle(start=7, halves=4, floor=9)) == 1.0


def test_a_feedback_move_eases_a_tone_one_halving_back_and_never_past_new():
    """An adjustment, not a restart: 2 % becomes about 4 %, 3.1 % becomes 6.25 %."""
    settle = Settle(start=0.25, halves=4, floor=0.02)
    assert [eased(n, settle) for n in (0, 3, 4, 8, 12, 15, 40)] == [0, 0, 0, 4, 8, 10, 10]
    for n in range(0, 60):
        before, after = drift_chance(n, settle), drift_chance(eased(n, settle), settle)
        assert before <= after <= min(0.25, before * 2 + 0.005)
    assert eased(9, Settle(start=0.25, halves=0, floor=0.02)) == 9
    assert eased(9, Settle(start=0.0, halves=4, floor=0.0)) == 9
    assert eased(None, settle) == 0


def test_a_complained_about_tone_stays_out_of_reach_for_two_halvings_of_conversations():
    assert avoid_span(Settle(start=0.25, halves=4, floor=0.02)) == 8
    assert avoid_span(Settle(start=0.25, halves=1, floor=0.02)) == 2
    assert avoid_span(Settle(start=0.25, halves=0, floor=0.02)) == UNTIL_STAFF


def test_a_drift_step_never_lands_on_the_tone_a_member_complained_about():
    pool = enabled_tropes(rows(*TROPE_NAMES))

    def landed(**given):
        found = set()
        for seed in range(200):
            kept = row(since=NOW.isoformat(), tone="mischievous", how=FEEDBACK,
                       heard=DRIFT_EVERY_TURNS - 1, **given)
            found.add(stored_tone(pool, kept, key=f"s{seed}", fresh=False, turns=3,
                                  since=NOW.isoformat(), now=NOW, settle=ALWAYS).name)
        return found

    assert "tsundere" in landed()
    assert "tsundere" in landed(avoid="tsundere", avoid_left=0)
    held = landed(avoid="tsundere", avoid_left=8)
    assert "tsundere" not in held and held <= {"flirty", "dramatic", "peppy"}
    assert "tsundere" not in landed(avoid="tsundere", avoid_left=UNTIL_STAFF)


def test_a_tone_whose_only_neighbour_is_the_one_complained_about_stays_put():
    pool = enabled_tropes(rows("shy", "cozy"))
    kept = row(since=NOW.isoformat(), tone="shy", how=FEEDBACK, heard=DRIFT_EVERY_TURNS - 1,
               avoid="cozy", avoid_left=3)
    found = stored_tone(pool, kept, key="k", fresh=False, turns=3, since=NOW.isoformat(),
                        now=NOW, settle=ALWAYS)
    assert found.name == "shy" and found.moved is None and found.avoid_left == 3


def test_how_settled_a_tone_is_runs_from_new_to_settled():
    settle = Settle(start=0.25, halves=4, floor=0.02)
    assert settled_share(0, settle) == 0.0 and settled_word(0, settle) == NEW
    assert settled_word(3, settle) == NEW
    assert settled_word(5, settle) == SETTLING
    assert settled_share(16, settle) == 1.0 and settled_word(16, settle) == SETTLED
    assert settled_share(0, Settle(start=0.02, halves=4, floor=0.02)) == 1.0


def test_the_three_numbers_come_from_the_settings_and_fall_back_to_the_shipped_ones():
    class Store:
        def __init__(self, given):
            self.given = given

        def get(self, guild_id, key):
            return self.given[key]

    assert settle_of(None, GUILD) == Settle()
    found = settle_of(
        Store({tone_keys.DRIFT_START_KEY: 40, tone_keys.DRIFT_HALVES_KEY: 2,
               tone_keys.DRIFT_FLOOR_KEY: 0}),
        GUILD,
    )
    assert found == Settle(start=0.4, halves=2, floor=0.0)
    assert settle_of(Store({}), GUILD) == Settle(start=0.25, halves=4, floor=0.02)


ALWAYS = Settle(start=1.0, halves=0, floor=1.0)
NEVER = Settle(start=0.0, halves=4, floor=0.0)


def test_a_step_is_only_weighed_every_few_answers_and_is_one_step_along_the_graph():
    pool = enabled_tropes(rows(*TROPE_NAMES))
    kept = row(since=NOW.isoformat(), tone="warm", how=ROLLED, settled=5,
               heard=DRIFT_EVERY_TURNS - 2)
    quiet = stored_tone(pool, kept, key="k", fresh=False, turns=2, since=NOW.isoformat(),
                        now=NOW, settle=ALWAYS)
    assert quiet.moved is None and quiet.name == "warm" and quiet.settled == 5
    kept["heard"] = DRIFT_EVERY_TURNS - 1
    moved = stored_tone(pool, kept, key="k", fresh=False, turns=3, since=NOW.isoformat(),
                        now=NOW, settle=ALWAYS)
    assert moved.moved == ("warm", moved.name) and moved.name in BY_NAME["warm"].neighbours
    assert (moved.how, moved.settled, moved.heard) == (DRIFTED, 0, 0)


def test_a_tone_with_no_neighbour_switched_on_stays_where_it_is():
    pool = enabled_tropes(rows("shy", "noir"))
    kept = row(since=NOW.isoformat(), tone="shy", how=SET, heard=DRIFT_EVERY_TURNS - 1)
    found = stored_tone(pool, kept, key="k", fresh=False, turns=3, since=NOW.isoformat(),
                        now=NOW, settle=ALWAYS)
    assert found.moved is None and (found.name, found.how) == ("shy", SET)


def steps_taken(settled, tries=400):
    pool = enabled_tropes(rows(*TROPE_NAMES))
    moved = 0
    for n in range(tries):
        kept = row(since=NOW.isoformat(), tone="mischievous", how=ROLLED, settled=settled,
                   heard=DRIFT_EVERY_TURNS - 1)
        found = stored_tone(pool, kept, key=f"seed-{n}", fresh=False, turns=3,
                            since=NOW.isoformat(), now=NOW)
        moved += found.moved is not None
    return moved


def test_a_settled_tone_takes_fewer_steps_than_a_new_one():
    """Seeded: 400 weighings each, the same seeds, at 0, 8 and 40 quiet conversations."""
    new, settling, settled = steps_taken(0), steps_taken(8), steps_taken(40)
    assert new > settling > settled
    assert 70 <= new <= 130 and settled <= 20


def test_a_pin_never_drifts_and_never_settles():
    kept = row(pinned="noir", tone="warm", how=ROLLED, settled=3, heard=DRIFT_EVERY_TURNS - 1,
               since=NOW.isoformat())
    found = heard_from(POOL, rows(*TROPE_NAMES), kept, guild_id=GUILD, user_id=900, turns=3,
                       now=NOW, settle=ALWAYS)
    assert (found.name, found.source, found.stored, found.moved) == ("noir", PINNED, False, None)


def test_a_reroll_never_lands_on_the_tone_the_member_has():
    pool = enabled_tropes(rows("warm", "noir", "shy"))
    for seed in range(40):
        assert another(pool, "warm", random.Random(seed)).name in ("noir", "shy")
    assert another(enabled_tropes(rows("warm")), "warm", random.Random(1)).name == "warm"
    assert another([], "warm", random.Random(1)) is None


def test_an_order_is_read_from_commas_and_a_step_goes_to_the_nearest_tone_that_is_on():
    order = order_of(" Warm, cozy ,shy,, peppy, warm ")
    assert order == ("warm", "cozy", "shy", "peppy")
    assert step_toward("peppy", order, TROPE_NAMES) == "shy"
    assert step_toward("peppy", order, {"warm", "peppy"}) == "warm"
    assert step_toward("peppy", order, {"peppy"}) is None
    assert step_toward("warm", order, TROPE_NAMES) is None
    assert step_toward("noir", order, TROPE_NAMES) is None
    assert step_toward("cozy", "warm, cozy", TROPE_NAMES) == "warm"


def test_the_shipped_orders_name_every_tone_once():
    for key in tone_keys.ORDER_KEYS:
        assert sorted(order_of(tone_keys.TONE_SETTINGS[key][1])) == sorted(TROPE_NAMES)
    assert tone_keys.unknown_tone("warm, grumpy") == "grumpy"
    assert tone_keys.unknown_tone("warm, cozy") is None


def test_the_state_is_the_pin_then_how_the_stored_tone_got_there():
    live = set(TROPE_NAMES)
    assert state_of(row(pinned="noir", tone="warm", how=SET), live) == PINNED
    assert state_of(row(pinned="noir", tone="warm", how=SET), {"warm"}) == SET
    assert state_of(row(tone="warm", how=FEEDBACK), live) == FEEDBACK
    assert state_of(row(tone="warm", how="odd"), live) == ROLLED
    assert state_of(row(trope="warm"), live) is None
    assert state_of(row(tone="warm", how=SET), live, "deadpan") is None
    assert state_of(row(pinned="noir"), live, COOKOUT) is None


def test_an_empty_pool_is_the_cookout_voice():
    found = heard_from(POOL, [], None, guild_id=GUILD, user_id=900, turns=0, now=NOW)
    assert found.trope is None and found.source == COOKOUT


async def test_the_window_counts_model_turns_in_every_channel_and_nothing_older(db):
    await a_turn(db, 900, 11, NOW - timedelta(minutes=5))
    await a_turn(db, 900, 12, NOW - timedelta(minutes=20))
    await a_turn(db, 900, 12, NOW - timedelta(minutes=45))
    await a_turn(db, 900, 11, NOW - timedelta(minutes=1), tier=None)
    await a_turn(db, 901, 11, NOW - timedelta(minutes=1))
    assert await window_turns(db, GUILD, 900, now=NOW) == 2
    assert await talking_now(db, GUILD, now=NOW) == {900: 2, 901: 1}


async def test_the_tone_is_written_down_and_a_pin_survives_the_next_reply(db):
    first = await heard_for(db, POOL, rows(*TROPE_NAMES), guild_id=GUILD, user_id=900, now=NOW)
    stored = await voice_row(db, GUILD, 900)
    assert stored["trope"] == first.name and stored["since"] == NOW.isoformat()

    await pin(db, GUILD, 900, "scholar", by=7)
    again = await heard_for(db, POOL, rows(*TROPE_NAMES), guild_id=GUILD, user_id=900, now=NOW)
    stored = await voice_row(db, GUILD, 900)
    assert again.name == "scholar"
    assert (stored["pinned"], stored["pinned_by"], stored["trope"]) == ("scholar", 7, "scholar")


async def test_the_cookout_setting_writes_nothing_down(db):
    found = await heard_for(db, COOKOUT, rows(*TROPE_NAMES), guild_id=GUILD, user_id=900, now=NOW)
    assert found.trope is None
    assert await voice_row(db, GUILD, 900) is None


async def test_clearing_a_pin_leaves_the_roll_and_says_whether_there_was_one(db):
    await pin(db, GUILD, 900, "noir", by=7)
    assert await unpin(db, GUILD, 900) is True
    assert await unpin(db, GUILD, 900) is False
    stored = await voice_row(db, GUILD, 900)
    assert stored["pinned"] is None and stored["pinned_by"] is None


async def test_forgetting_a_members_memory_never_clears_their_pin(db):
    """`/memory` "forget the lot" is about what the bot knows, not the tone staff chose."""
    await pin(db, GUILD, 900, "noir", by=7)
    await forget(db, 900, GUILD)
    await forget_everywhere(db, 900)
    assert (await voice_row(db, GUILD, 900))["pinned"] == "noir"


async def test_the_roster_lists_pins_first_and_says_who_is_talking_now(db):
    await heard_for(db, POOL, rows(*TROPE_NAMES), guild_id=GUILD, user_id=901, now=NOW)
    await pin(db, GUILD, 900, "noir", by=7)
    found = roster(await voice_rows(db, GUILD), POOL, TROPE_NAMES, {901: 1})
    assert [one["user_id"] for one in found] == [900, 901]
    assert found[0]["trope"] == "noir" and found[0]["pinned_by"] == 7
    assert found[0]["active"] is False and found[1]["active"] is True


async def test_a_tone_carries_from_one_conversation_to_the_next_and_is_rolled_only_once(db):
    pool = rows(*TROPE_NAMES)
    first = await heard_for(db, POOL, pool, guild_id=GUILD, user_id=900, now=NOW, settle=NEVER)
    kept = await voice_row(db, GUILD, 900)
    assert (kept["tone"], kept["how"], kept["settled"], kept["heard"]) == (
        first.name, ROLLED, 0, 1)
    for days in (1, 2, 3):
        later = NOW + timedelta(days=days)
        again = await heard_for(db, POOL, pool, guild_id=GUILD, user_id=900, now=later,
                                settle=NEVER)
        assert again.name == first.name and again.since == later.isoformat()
    kept = await voice_row(db, GUILD, 900)
    assert (kept["tone"], kept["settled"], kept["heard"]) == (first.name, 3, 4)


async def test_a_second_answer_in_the_same_conversation_does_not_count_as_another_one(db):
    pool = rows(*TROPE_NAMES)
    await heard_for(db, POOL, pool, guild_id=GUILD, user_id=900, now=NOW, settle=NEVER)
    await a_turn(db, 900, 11, NOW)
    await heard_for(db, POOL, pool, guild_id=GUILD, user_id=900,
                    now=NOW + timedelta(minutes=5), settle=NEVER)
    kept = await voice_row(db, GUILD, 900)
    assert (kept["settled"], kept["heard"], kept["since"]) == (0, 2, NOW.isoformat())


async def test_an_answer_that_was_never_recorded_does_not_count_twice(db):
    """No model turn lands in the window, so the next call looks fresh — inside the half hour."""
    pool = rows(*TROPE_NAMES)
    await heard_for(db, POOL, pool, guild_id=GUILD, user_id=900, now=NOW, settle=NEVER)
    await heard_for(db, POOL, pool, guild_id=GUILD, user_id=900,
                    now=NOW + timedelta(minutes=2), settle=NEVER)
    assert (await voice_row(db, GUILD, 900))["settled"] == 0


async def test_staff_give_a_starting_tone_and_the_next_answer_uses_it(db):
    await set_tone(db, GUILD, 900, "scholar", by=7, now=NOW)
    kept = await voice_row(db, GUILD, 900)
    assert (kept["tone"], kept["how"], kept["set_by"], kept["moved_at"], kept["since"]) == (
        "scholar", SET, 7, NOW.isoformat(), None)
    later = NOW + timedelta(hours=3)
    found = await heard_for(db, POOL, rows(*TROPE_NAMES), guild_id=GUILD, user_id=900, now=later,
                            settle=NEVER)
    kept = await voice_row(db, GUILD, 900)
    assert (found.name, found.how, kept["settled"], kept["how"]) == ("scholar", SET, 0, SET)


async def test_setting_a_tone_again_remembers_the_one_before_and_starts_unsettled(db):
    await set_tone(db, GUILD, 900, "scholar", by=7, now=NOW)
    await db.conn.execute("UPDATE chat_voice SET settled = 9, heard = 30, since = 'x'")
    await set_tone(db, GUILD, 900, "warm", how=ROLLED, by=8, now=NOW + timedelta(days=1))
    kept = await voice_row(db, GUILD, 900)
    assert (kept["tone"], kept["moved_from"], kept["how"], kept["settled"], kept["heard"]) == (
        "warm", "scholar", ROLLED, 0, 0)
    assert kept["since"] is None and kept["set_by"] == 8


async def test_a_step_is_written_down_with_where_it_came_from(db):
    await set_tone(db, GUILD, 900, "warm", by=7, now=NOW)
    await db.conn.execute(
        "UPDATE chat_voice SET heard = ?, settled = 6", (DRIFT_EVERY_TURNS - 1,)
    )
    later = NOW + timedelta(hours=1)
    found = await heard_for(db, POOL, rows(*TROPE_NAMES), guild_id=GUILD, user_id=900, now=later,
                            settle=ALWAYS)
    kept = await voice_row(db, GUILD, 900)
    assert found.moved == ("warm", found.name)
    assert (kept["tone"], kept["how"], kept["moved_from"], kept["moved_at"]) == (
        found.name, DRIFTED, "warm", later.isoformat())
    assert (kept["settled"], kept["heard"], kept["set_by"]) == (0, 0, None)


async def test_a_tone_staff_set_while_an_answer_was_being_written_is_not_written_over(db):
    """The answer read `warm`; staff set `noir` before it was kept — the answer's copy loses."""
    pool = rows(*TROPE_NAMES)
    await set_tone(db, GUILD, 900, "warm", by=7, now=NOW)
    read = await voice_row(db, GUILD, 900)
    stale = heard_from(POOL, pool, read, guild_id=GUILD, user_id=900, turns=0, now=NOW,
                       settle=ALWAYS)
    await set_tone(db, GUILD, 900, "noir", by=8, now=NOW)

    await remember_heard(db, GUILD, 900, stale, now=NOW)

    kept = await voice_row(db, GUILD, 900)
    assert (stale.name, stale.was) == ("warm", "warm")
    assert (kept["tone"], kept["how"], kept["set_by"], kept["heard"]) == ("noir", SET, 8, 0)


async def test_a_stored_tone_that_was_switched_off_is_rolled_again_and_says_so(db):
    await set_tone(db, GUILD, 900, "noir", by=7, now=NOW)
    later = NOW + timedelta(hours=2)
    found = await heard_for(db, POOL, rows("warm", "cozy"), guild_id=GUILD, user_id=900,
                            now=later)
    kept = await voice_row(db, GUILD, 900)
    assert found.name in ("warm", "cozy") and found.how == TONE_OFF
    assert found.rerolled == ("noir", found.name)
    assert (kept["tone"], kept["how"], kept["moved_from"], kept["moved_at"], kept["set_by"]) == (
        found.name, TONE_OFF, "noir", later.isoformat(), None)
    assert state_of(kept, {"warm", "cozy"}) == TONE_OFF
    again = await heard_for(db, POOL, rows("warm", "cozy"), guild_id=GUILD, user_id=900,
                            now=later + timedelta(minutes=1))
    assert again.rerolled is None and again.name == found.name


async def test_a_first_roll_is_not_a_reroll(db):
    found = await heard_for(db, POOL, rows("warm", "cozy"), guild_id=GUILD, user_id=900, now=NOW)
    assert found.rerolled is None and found.how == ROLLED
    assert (await voice_row(db, GUILD, 900))["moved_from"] is None


async def test_a_placeholder_pin_whose_tone_is_switched_off_is_rerolled_out_loud(db):
    """The real conversion statement, then the member's next answer with that tone off."""
    from black_bloc.storage.db import (
        PLACEHOLDER_PIN_DAY,
        PLACEHOLDER_PINNED,
        PLACEHOLDER_PINS_TO_STARTING_TONES,
    )

    who = PLACEHOLDER_PINNED[0]
    await db.conn.execute(
        "INSERT INTO chat_voice(guild_id, user_id, trope, pinned, pinned_by, pinned_at) "
        "VALUES (?, ?, 'noir', 'noir', 42, '2026-10-05T18:52:10+00:00')",
        (GUILD, who),
    )
    await db.conn.execute(
        PLACEHOLDER_PINS_TO_STARTING_TONES, (PLACEHOLDER_PIN_DAY, *PLACEHOLDER_PINNED)
    )
    assert (await voice_row(db, GUILD, who))["tone"] == "noir"

    found = await heard_for(db, POOL, rows("warm", "cozy"), guild_id=GUILD, user_id=who, now=NOW)

    kept = await voice_row(db, GUILD, who)
    assert found.rerolled == ("noir", found.name) and found.name in ("warm", "cozy")
    assert (kept["how"], kept["moved_from"], kept["pinned"]) == (TONE_OFF, "noir", None)


async def test_a_feedback_move_keeps_the_old_tone_out_of_reach_and_counts_it_down(db):
    pool = rows(*TROPE_NAMES)
    await set_tone(db, GUILD, 900, "tsundere", by=7, now=NOW)
    await heard_for(db, POOL, pool, guild_id=GUILD, user_id=900, now=NOW, settle=NEVER)
    await move_for_feedback(db, GUILD, 900, "mischievous", "mean", now=NOW, settled=5,
                            avoid_for=2)
    kept = await voice_row(db, GUILD, 900)
    assert (kept["avoid"], kept["avoid_left"], kept["settled"]) == ("tsundere", 2, 5)
    for day, left in ((1, 1), (2, 0), (3, 0)):
        await heard_for(db, POOL, pool, guild_id=GUILD, user_id=900,
                        now=NOW + timedelta(days=day), settle=NEVER)
        assert (await voice_row(db, GUILD, 900))["avoid_left"] == left
    await move_for_feedback(db, GUILD, 900, "deadpan", "mean", now=NOW)
    assert (await voice_row(db, GUILD, 900))["avoid_left"] == UNTIL_STAFF
    await heard_for(db, POOL, pool, guild_id=GUILD, user_id=900, now=NOW + timedelta(days=9),
                    settle=NEVER)
    assert (await voice_row(db, GUILD, 900))["avoid_left"] == UNTIL_STAFF
    await set_tone(db, GUILD, 900, "warm", by=7, now=NOW)
    kept = await voice_row(db, GUILD, 900)
    assert (kept["avoid"], kept["avoid_left"]) == (None, 0)


async def test_a_pin_and_a_named_mood_leave_the_stored_tone_alone(db):
    await set_tone(db, GUILD, 900, "shy", by=7, now=NOW)
    await db.conn.execute("UPDATE chat_voice SET settled = 4, heard = 3")
    await pin(db, GUILD, 900, "noir", by=7)
    pinned = await heard_for(db, POOL, rows(*TROPE_NAMES), guild_id=GUILD, user_id=900, now=NOW,
                             settle=ALWAYS)
    named = await heard_for(db, "deadpan", rows(*TROPE_NAMES), guild_id=GUILD, user_id=901,
                            now=NOW, settle=ALWAYS)
    kept = await voice_row(db, GUILD, 900)
    assert (pinned.name, named.name) == ("noir", "deadpan")
    assert (kept["tone"], kept["settled"], kept["heard"], kept["trope"]) == ("shy", 4, 3, "noir")
    other = await voice_row(db, GUILD, 901)
    assert (other["tone"], other["trope"]) == (None, "deadpan")
    await unpin(db, GUILD, 900)
    back = await heard_for(db, POOL, rows(*TROPE_NAMES), guild_id=GUILD, user_id=900,
                           now=NOW + timedelta(minutes=1), settle=NEVER)
    assert back.name == "shy"


async def test_feedback_moves_the_tone_unsettles_it_and_counts_once_a_conversation(db):
    pool = rows(*TROPE_NAMES)
    await set_tone(db, GUILD, 900, "tsundere", by=7, now=NOW)
    await db.conn.execute("UPDATE chat_voice SET settled = 12, heard = 2")
    await heard_for(db, POOL, pool, guild_id=GUILD, user_id=900, now=NOW, settle=NEVER)
    assert fed_already(await voice_row(db, GUILD, 900)) is False
    at = NOW + timedelta(minutes=3)
    await move_for_feedback(db, GUILD, 900, "mischievous", "mean", now=at)
    kept = await voice_row(db, GUILD, 900)
    assert (kept["tone"], kept["trope"], kept["how"], kept["moved_from"], kept["moved_why"]) == (
        "mischievous", "mischievous", FEEDBACK, "tsundere", "mean")
    assert (kept["settled"], kept["heard"], kept["moved_at"]) == (0, 0, at.isoformat())
    assert fed_already(kept) is True
    await a_turn(db, 900, 11, at)
    await heard_for(db, POOL, pool, guild_id=GUILD, user_id=900,
                    now=at + timedelta(minutes=1), settle=NEVER)
    assert fed_already(await voice_row(db, GUILD, 900)) is True
    tomorrow = NOW + timedelta(days=1)
    found = await heard_for(db, POOL, pool, guild_id=GUILD, user_id=900, now=tomorrow,
                            settle=NEVER)
    assert found.name == "mischievous" and found.how == FEEDBACK
    assert fed_already(await voice_row(db, GUILD, 900)) is False


async def test_feedback_that_moved_nothing_is_still_the_one_for_this_conversation(db):
    assert await claim_feedback(db, GUILD, 900) is False
    await set_tone(db, GUILD, 900, "warm", by=7, now=NOW)
    assert await claim_feedback(db, GUILD, 900) is False
    await heard_for(db, POOL, rows("warm"), guild_id=GUILD, user_id=900, now=NOW, settle=NEVER)
    assert await claim_feedback(db, GUILD, 900) is True
    assert await claim_feedback(db, GUILD, 900) is False
    kept = await voice_row(db, GUILD, 900)
    assert fed_already(kept) is True and kept["tone"] == "warm" and kept["how"] == SET
    assert fed_already(row(since=None, fed_since=None)) is False
    assert fed_already(None) is False


async def test_the_roster_says_how_each_tone_got_there_and_how_settled_it_is(db):
    await set_tone(db, GUILD, 900, "scholar", by=7, now=NOW)
    await set_tone(db, GUILD, 901, "warm", how=ROLLED, by=7, now=NOW)
    await db.conn.execute("UPDATE chat_voice SET settled = 16 WHERE user_id = 901")
    await pin(db, GUILD, 902, "noir", by=7)
    found = {one["user_id"]: one
             for one in roster(await voice_rows(db, GUILD), POOL, TROPE_NAMES, {})}
    assert (found[900]["trope"], found[900]["state"], found[900]["settled_word"]) == (
        "scholar", SET, NEW)
    assert (found[901]["state"], found[901]["settled_word"], found[901]["settled_share"]) == (
        ROLLED, SETTLED, 1.0)
    assert found[901]["chance"] == 0.02 and found[900]["chance"] == 0.25
    assert (found[902]["state"], found[902]["tone"]) == (PINNED, None)
    assert found[900]["set_by"] == 7 and found[900]["moved_at"] == NOW.isoformat()


def test_what_a_member_hears_now_follows_the_same_precedence():
    kept = row(trope="warm", pinned="noir")
    assert hears_now(COOKOUT, kept, set(TROPE_NAMES)) == COOKOUT
    assert hears_now(POOL, kept, set(TROPE_NAMES)) == "noir"
    assert hears_now(POOL, kept, {"warm"}) == "warm"
    assert hears_now("deadpan", row(trope="warm"), set(TROPE_NAMES)) == "deadpan"
    assert hears_now("deadpan", row(trope="warm"), {"warm"}) == COOKOUT
    assert hears_now(POOL, row(trope="warm", tone="noir"), set(TROPE_NAMES)) == "noir"
    assert hears_now(POOL, row(trope="warm", tone="noir"), {"warm"}) == COOKOUT


def test_a_pin_to_a_mood_that_is_off_is_listed_as_waiting():
    found = roster([row(pinned="noir", trope="warm")], POOL, {"warm"}, {})
    assert found[0]["waiting"] is True and found[0]["trope"] == "warm"
