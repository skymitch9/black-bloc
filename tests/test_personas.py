import json

from black_bloc.chat_llm import says_a_budget_word
from black_bloc.personas import (
    BY_NAME,
    COOKOUT,
    CORE,
    DRIFT_EVERY_TURNS,
    GABI,
    INVARIANT,
    PERSONALITY_CHOICES,
    POOL,
    REGISTER,
    TROPE_NAMES,
    TROPES,
    Trope,
    drifted,
    enabled_tropes,
    forget_tropes,
    get_trope,
    list_tropes,
    pick_trope,
    pooled,
    seed_tropes,
    set_enabled,
    stable_core,
    system_blocks,
    system_text,
    trope_block,
)
from black_bloc.storage.db import Database


def test_the_roster_is_the_eleven_gabi_locked():
    assert len(TROPES) == 11
    assert set(TROPE_NAMES) == {
        "peppy",
        "dramatic",
        "mischievous",
        "flirty",
        "warm",
        "cozy",
        "shy",
        "scholar",
        "noir",
        "deadpan",
        "tsundere",
    }


def test_every_wing_of_the_graph_points_at_a_trope_that_exists():
    for trope in TROPES:
        assert trope.neighbours
        for name in trope.neighbours:
            assert name in BY_NAME, name


def test_the_graph_is_a_chain_so_the_two_ends_are_never_one_step_apart():
    assert "noir" not in BY_NAME["shy"].neighbours
    assert "shy" not in BY_NAME["noir"].neighbours


def test_the_ported_text_talks_about_this_server_and_not_about_books():
    for trope in TROPES:
        said = trope.voice.lower()
        for gone in ("book", "catalog", "catalogue", "librarian", "passage", "shelf"):
            assert gone not in said, (trope.name, gone)


def test_the_core_carries_the_four_hard_rules():
    said = " ".join(CORE.lower().split())
    assert "black bloc" in said
    assert "never invent a fact about a member" in said
    assert "not moderating anybody" in said
    assert "quote them rather than inventing" in said


def test_no_part_of_the_voice_teaches_the_bot_to_talk_about_its_own_spending():
    for text in (CORE, stable_core(), REGISTER, INVARIANT, *(t.voice for t in TROPES)):
        assert says_a_budget_word(text) is None, text[:60]


def test_a_mood_is_appended_after_the_rules_so_it_can_never_delete_one():
    blocks = system_blocks(BY_NAME["noir"])
    assert len(blocks) == 2
    assert blocks[0]["text"] == stable_core()
    assert blocks[0]["cache_control"] == {"type": "ephemeral"}
    assert "HARD-BOILED" in blocks[1]["text"]
    assert "cache_control" not in blocks[1]


def test_the_house_voice_sends_one_block_and_no_mood_at_all():
    blocks = system_blocks(None)
    assert len(blocks) == 1
    assert trope_block(None) == ""


def test_the_core_tells_the_bot_to_name_only_what_it_was_given():
    said = " ".join(CORE.lower().split())
    assert "point people only at channels that are in the channel list below" in said
    assert "never name a channel, a role or a member that is not in that list" in said


def test_the_channel_list_sits_after_the_cached_core_and_before_the_mood():
    blocks = system_blocks(BY_NAME["noir"], "## The channels of this server\n#general")
    assert [block["text"] for block in blocks][0] == stable_core()
    assert "#general" in blocks[1]["text"]
    assert "cache_control" not in blocks[1]
    assert "HARD-BOILED" in blocks[2]["text"]


def test_a_blank_channel_list_adds_no_block_of_its_own():
    assert len(system_blocks(None, "")) == 1
    assert len(system_blocks(None, "   ")) == 1


def test_every_mood_block_carries_the_register_and_the_invariance_clause():
    for trope in TROPES:
        said = trope_block(trope)
        assert REGISTER in said
        assert INVARIANT in said
        assert "mood, not a different person" in said


def test_the_one_string_form_is_the_same_stack_a_provider_without_blocks_gets():
    said = system_text(BY_NAME["warm"])
    assert stable_core() in said
    assert "You are WARM today" in said


def test_the_setting_choices_are_the_house_voice_the_pool_and_every_mood():
    assert PERSONALITY_CHOICES[:2] == (COOKOUT, POOL)
    assert set(PERSONALITY_CHOICES[2:]) == set(TROPE_NAMES)


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


def test_the_house_voice_picks_no_mood_whatever_is_in_the_pool():
    assert pick_trope(COOKOUT, rows(*TROPE_NAMES)) is None
    assert pick_trope(None, rows(*TROPE_NAMES)) is None


def test_naming_a_mood_pins_it_and_a_mood_that_is_off_falls_back_to_the_house_voice():
    assert pick_trope("noir", rows("noir")).name == "noir"
    assert pick_trope("noir", rows("noir", enabled=False)) is None
    assert pick_trope("nonsense", rows("noir")) is None


def test_the_pool_gives_one_conversation_one_voice_however_often_it_is_asked():
    pool = rows(*TROPE_NAMES)
    first = pick_trope(POOL, pool, key="111:900", turns=0)
    again = pick_trope(POOL, pool, key="111:900", turns=0)
    assert first is not None and first.name == again.name


def test_two_conversations_do_not_have_to_sound_the_same():
    pool = rows(*TROPE_NAMES)
    names = {pick_trope(POOL, pool, key=f"111:{n}", turns=0).name for n in range(40)}
    assert len(names) > 1


def test_an_empty_pool_means_the_house_voice_rather_than_a_crash():
    assert pick_trope(POOL, []) is None
    assert pick_trope(POOL, rows(*TROPE_NAMES, enabled=False)) is None


def test_a_drift_only_ever_moves_one_step_along_the_graph():
    pool = enabled_tropes(rows(*TROPE_NAMES))
    start = BY_NAME["shy"]
    landed = {drifted(start, pool, f"key-{n}", 1).name for n in range(60)}
    assert landed <= {"shy", *start.neighbours}


def test_drift_is_counted_in_whole_blocks_of_turns():
    pool = rows(*TROPE_NAMES)
    early = [
        pick_trope(POOL, pool, key="k", turns=n).name for n in range(DRIFT_EVERY_TURNS)
    ]
    assert len(set(early)) == 1


def test_a_long_conversation_can_end_up_somewhere_else_entirely():
    pool = enabled_tropes(rows(*TROPE_NAMES))
    walked = {drifted(BY_NAME["warm"], pool, f"k{n}", 12).name for n in range(60)}
    assert len(walked) > 1


def test_a_neighbour_that_is_switched_off_is_never_drifted_into():
    pool = enabled_tropes(rows("shy", "cozy"))
    assert drifted(BY_NAME["cozy"], pool, "k", 8).name in {"shy", "cozy"}


def test_a_trope_object_may_be_passed_straight_in_as_the_pool():
    assert enabled_tropes([BY_NAME["warm"]]) == [BY_NAME["warm"]]


def test_neighbours_that_will_not_parse_read_as_a_dead_end_rather_than_raising():
    pool = enabled_tropes([{"name": "warm", "label": "warm", "voice": "v", "neighbours": "{oops",
                            "enabled": 1}])
    assert pool[0].neighbours == ()
    assert drifted(pool[0], pool, "k", 20).name == "warm"


async def test_the_pool_is_seeded_once_and_never_twice(tmp_path):
    db = Database(tmp_path / "p.sqlite3")
    await db.connect()
    try:
        assert await seed_tropes(db) == 11
        assert await seed_tropes(db) == 0
        stored = await list_tropes(db)
        assert len(stored) == 11
        assert [row["source"] for row in stored] == [GABI] * 11
        assert all(row["enabled"] for row in stored)
    finally:
        await db.close()


async def test_a_mood_switched_off_stays_off_across_a_reseed(tmp_path):
    db = Database(tmp_path / "p.sqlite3")
    await db.connect()
    try:
        await seed_tropes(db)
        assert await set_enabled(db, "Flirty", False, by=900) is True
        await seed_tropes(db)
        assert (await get_trope(db, "flirty"))["enabled"] == 0
        assert await set_enabled(db, "nonsense", False) is False
    finally:
        await db.close()


class FakeDb:
    def __init__(self, db):
        self._db = db

    @property
    def is_connected(self):
        return True

    @property
    def conn(self):
        return self._db.conn


class FakeBot:
    def __init__(self, db=None):
        self.db = db


async def test_the_pool_is_read_once_and_remembered_on_the_bot(tmp_path):
    db = Database(tmp_path / "p.sqlite3")
    await db.connect()
    try:
        await seed_tropes(db)
        bot = FakeBot(FakeDb(db))
        assert len(await pooled(bot)) == 11
        await set_enabled(db, "warm", False)
        assert all(row["enabled"] for row in await pooled(bot))
        forget_tropes(bot)
        assert not all(row["enabled"] for row in await pooled(bot))
    finally:
        await db.close()


async def test_a_bot_with_no_database_has_an_empty_pool_rather_than_an_error():
    assert await pooled(FakeBot(None)) == ()


def test_a_trope_is_a_value_and_stays_one():
    warm = Trope("warm", "warm", "v", ())
    assert warm == Trope("warm", "warm", "v", ())
