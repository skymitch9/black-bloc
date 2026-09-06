import json

import pytest

from black_bloc.chat_llm import says_a_budget_word
from black_bloc.personas import (
    BY_NAME,
    COOKOUT,
    COOKOUT_SLOTS,
    CORE,
    DRIFT_CHANCE,
    DRIFT_EVERY_TURNS,
    FEATURES,
    GABI,
    INVARIANT,
    MANIFEST,
    PERSONALITY_CHOICES,
    POOL,
    POOL_NAMES,
    POOL_NEIGHBOURS,
    POOL_SLOTS,
    POOL_SORT,
    POOL_SOURCE,
    POOL_VERSION,
    REGISTER,
    RETIRED,
    TROPE_NAMES,
    TROPES,
    VOICES,
    PoolError,
    Trope,
    drifted,
    enabled_tropes,
    forget_tropes,
    get_trope,
    list_tropes,
    pick_trope,
    pooled,
    read_manifest,
    set_enabled,
    stable_core,
    sync_pool,
    sync_tropes,
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


def test_the_core_tells_it_to_take_a_side_rather_than_bounce_the_question_back():
    """Live 2026-09-01: "who is the strongest DBZ character" got "way outside my
    wheelhouse… Who's your pick?" and a member said to have it pick a character."""
    said = " ".join(CORE.lower().split())
    assert "take a side" in said
    assert "so pick one and give one playful reason for it" in said
    assert "outside my wheelhouse" in said and "is not an answer" in said
    assert "never make \"what's your pick?\" the whole reply" in said
    assert "an aside at the end, never the answer itself" in said
    assert said.index("take a side") > said.index("what is true")


def test_taking_a_side_did_not_loosen_the_two_rules_it_sits_between():
    said = " ".join(CORE.lower().split())
    assert "do not invent a fact about this server or about a member to back a pick up" in said
    assert "somebody's personal details, a moderation decision" in said
    assert "never invent a fact about a member" in said
    assert "quote them rather than inventing" in said


def test_the_new_rule_is_in_the_core_and_never_in_a_mood():
    said = "Take a side"
    assert said in stable_core()
    assert all(said not in trope.voice for trope in TROPES)
    assert said not in trope_block(BY_NAME["deadpan"])


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


async def test_every_command_a_member_can_run_is_in_the_block_the_model_reads(settings):
    """Live 2026-09-01: "i want to host an event" was answered "hit up @Admin".
    The table is hand-kept, so this is what fails the day a command is added to
    the tree and not to it."""
    from black_bloc.bot import COGS, BlackBlocBot

    bot = BlackBlocBot(settings)
    for name in COGS:
        await bot.load_extension(name)
    open_to_members = [
        one.name for one in bot.tree.get_commands() if one.default_permissions is None
    ]
    await bot.close()

    assert open_to_members
    for name in open_to_members:
        assert f"`/{name}`" in FEATURES, name


def test_the_command_block_is_inside_the_part_that_is_cached_and_never_a_mood(settings):
    assert FEATURES in stable_core()
    assert FEATURES not in trope_block(BY_NAME["noir"])
    assert system_blocks(BY_NAME["noir"])[0]["text"] == stable_core()


def test_the_core_says_to_name_its_own_command_before_pointing_at_staff():
    said = " ".join(CORE.lower().split())
    assert "read your own command list below first" in said
    assert "name that command" in said


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
        assert (await sync_tropes(db)).inserted == TROPE_NAMES
        again = await sync_tropes(db)
        assert not again.changed
        assert again.inserted == () and again.updated == () and again.retired == ()
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
        await sync_tropes(db)
        assert await set_enabled(db, "Flirty", False, by=900) is True
        await sync_tropes(db)
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
        await sync_tropes(db)
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


# --- the shared manifest -----------------------------------------------------------------------


def test_the_manifest_loads_and_says_which_commit_it_came_from():
    assert POOL_VERSION >= 1
    assert POOL_SOURCE.startswith("catalog-platform@")
    assert MANIFEST["locked_by"]
    assert DRIFT_EVERY_TURNS == MANIFEST["drift"]["every"]
    assert DRIFT_CHANCE == MANIFEST["drift"]["chance"]


def test_the_roster_and_the_graph_are_the_manifests_and_not_a_second_copy():
    assert TROPE_NAMES == POOL_NAMES
    for trope in TROPES:
        assert trope.neighbours == POOL_NEIGHBOURS[trope.name]
        assert trope.label == MANIFEST["tropes"][POOL_SORT[trope.name]]["label"]


def test_the_graph_is_symmetric_so_a_drift_can_always_come_back():
    for name, wings in POOL_NEIGHBOURS.items():
        for wing in wings:
            assert name in POOL_NEIGHBOURS[wing], (name, wing)


def test_the_cookout_voices_cover_the_manifest_exactly():
    assert set(VOICES) == set(POOL_NAMES)


def test_every_slot_the_manifest_names_is_one_this_bot_fills():
    built = {"invariant": INVARIANT, "register": REGISTER}
    assert set(POOL_SLOTS) == set(COOKOUT_SLOTS)
    for name, template in MANIFEST["clauses"].items():
        for slot in POOL_SLOTS:
            if "{" + slot + "}" in template:
                assert slot in COOKOUT_SLOTS, (name, slot)
        assert "{" not in built[name]


def test_a_missing_manifest_says_so_in_words_rather_than_raising_a_key_error(tmp_path):
    with pytest.raises(PoolError) as found:
        read_manifest(tmp_path / "gone.json")
    assert "sync_personality_pool.py" in str(found.value)


def test_a_manifest_that_is_not_json_says_so_in_words(tmp_path):
    path = tmp_path / "pool.json"
    path.write_text("{oops", encoding="utf-8")
    with pytest.raises(PoolError) as found:
        read_manifest(path)
    assert str(path) in str(found.value)


def test_a_manifest_with_no_tropes_at_all_says_so_in_words(tmp_path):
    path = tmp_path / "pool.json"
    path.write_text(json.dumps({"version": 1, "tropes": []}), encoding="utf-8")
    with pytest.raises(PoolError):
        read_manifest(path)


# --- the boot sync -----------------------------------------------------------------------------


async def stale_row(db, name="noir"):
    await db.conn.execute(
        "UPDATE personality_tropes SET label = ?, voice = ?, neighbours = ?, sort = ? "
        "WHERE name = ?",
        ("old", "an old voice", json.dumps(["shy"]), 99, name),
    )
    await db.conn.commit()


async def test_a_stale_gabi_row_is_brought_up_to_the_manifest(tmp_path):
    db = Database(tmp_path / "p.sqlite3")
    await db.connect()
    try:
        await sync_tropes(db)
        await stale_row(db)
        found = await sync_tropes(db)
        assert found.updated == ("noir",)
        row = await get_trope(db, "noir")
        assert row["label"] == BY_NAME["noir"].label
        assert row["voice"] == BY_NAME["noir"].voice
        assert json.loads(row["neighbours"]) == list(BY_NAME["noir"].neighbours)
        assert row["sort"] == POOL_SORT["noir"]
    finally:
        await db.close()


async def test_the_sync_never_writes_the_column_staff_own(tmp_path):
    db = Database(tmp_path / "p.sqlite3")
    await db.connect()
    try:
        await sync_tropes(db)
        await set_enabled(db, "noir", False)
        await stale_row(db)
        assert (await sync_tropes(db)).updated == ("noir",)
        assert (await get_trope(db, "noir"))["enabled"] == 0
    finally:
        await db.close()


async def test_a_name_that_has_left_the_manifest_is_retired_and_never_deleted(tmp_path):
    db = Database(tmp_path / "p.sqlite3")
    await db.connect()
    try:
        await sync_tropes(db)
        await db.conn.execute(
            "INSERT INTO personality_tropes(name, label, voice, neighbours, enabled, sort, "
            "source, updated_at) VALUES ('gone', 'gone', 'a voice', '[]', 1, 50, ?, 'now')",
            (GABI,),
        )
        await db.conn.commit()
        assert (await sync_tropes(db)).retired == ("gone",)
        row = await get_trope(db, "gone")
        assert row is not None
        assert row["source"] == RETIRED and row["enabled"] == 0
        assert row["voice"] == "a voice"
        assert not (await sync_tropes(db)).changed
    finally:
        await db.close()


async def test_a_row_staff_added_by_hand_is_not_the_manifests_to_retire(tmp_path):
    db = Database(tmp_path / "p.sqlite3")
    await db.connect()
    try:
        await sync_tropes(db)
        await db.conn.execute(
            "INSERT INTO personality_tropes(name, label, voice, neighbours, enabled, sort, "
            "source, updated_at) VALUES ('local', 'local', 'v', '[]', 1, 50, 'staff', 'now')"
        )
        await db.conn.commit()
        assert not (await sync_tropes(db)).changed
        assert (await get_trope(db, "local"))["enabled"] == 1
    finally:
        await db.close()


async def test_the_sync_held_off_still_adds_a_missing_name_and_changes_nothing_else(tmp_path):
    db = Database(tmp_path / "p.sqlite3")
    await db.connect()
    try:
        await sync_tropes(db)
        await stale_row(db)
        await db.conn.execute("DELETE FROM personality_tropes WHERE name = 'shy'")
        await db.conn.execute(
            "INSERT INTO personality_tropes(name, label, voice, neighbours, enabled, sort, "
            "source, updated_at) VALUES ('gone', 'gone', 'v', '[]', 1, 50, ?, 'now')",
            (GABI,),
        )
        await db.conn.commit()
        found = await sync_tropes(db, full=False)
        assert found.inserted == ("shy",)
        assert found.updated == () and found.retired == ()
        assert (await get_trope(db, "noir"))["label"] == "old"
        assert (await get_trope(db, "gone"))["source"] == GABI
    finally:
        await db.close()


class Guild:
    def __init__(self, guild_id=900):
        self.id = guild_id
        self.unavailable = False


class Store:
    def __init__(self, on=True):
        self.on = on

    def get(self, _guild_id, _key):
        return self.on


class LoggingBot:
    def __init__(self, db, *, on=True):
        self.db = db
        self.store = Store(on)
        self.guilds = [Guild()]
        self.rows = []


async def sync_with_log(bot, monkeypatch):
    async def note(_bot, guild, kind, **kwargs):
        bot.rows.append((guild.id, kind, kwargs.get("details") or {}))
        return 1

    monkeypatch.setattr("black_bloc.actionlog.log_action", note)
    return await sync_pool(bot)


async def test_a_boot_that_changes_the_pool_leaves_one_row_saying_what_moved(tmp_path, monkeypatch):
    db = Database(tmp_path / "p.sqlite3")
    await db.connect()
    try:
        bot = LoggingBot(db)
        found = await sync_with_log(bot, monkeypatch)
        assert found.inserted == TROPE_NAMES
        assert [kind for _, kind, _ in bot.rows] == ["chat.pool_synced"]
        assert bot.rows[0][2]["version"] == POOL_VERSION
        assert bot.rows[0][2]["inserted"] == list(TROPE_NAMES)
    finally:
        await db.close()


async def test_a_boot_that_changes_nothing_writes_nothing_and_logs_nothing(tmp_path, monkeypatch):
    db = Database(tmp_path / "p.sqlite3")
    await db.connect()
    try:
        bot = LoggingBot(db)
        await sync_with_log(bot, monkeypatch)
        bot.rows.clear()
        assert not (await sync_with_log(bot, monkeypatch)).changed
        assert bot.rows == []
    finally:
        await db.close()


async def test_a_retired_mood_leaves_its_own_row_beside_the_summary(tmp_path, monkeypatch):
    db = Database(tmp_path / "p.sqlite3")
    await db.connect()
    try:
        bot = LoggingBot(db)
        await sync_with_log(bot, monkeypatch)
        await db.conn.execute(
            "INSERT INTO personality_tropes(name, label, voice, neighbours, enabled, sort, "
            "source, updated_at) VALUES ('gone', 'gone', 'v', '[]', 1, 50, ?, 'now')",
            (GABI,),
        )
        await db.conn.commit()
        bot.rows.clear()
        await sync_with_log(bot, monkeypatch)
        assert [kind for _, kind, _ in bot.rows] == ["chat.pool_retired", "chat.pool_synced"]
        assert bot.rows[0][2]["name"] == "gone"
    finally:
        await db.close()


async def test_a_server_holding_the_sync_off_gets_the_insert_only_behaviour(tmp_path, monkeypatch):
    db = Database(tmp_path / "p.sqlite3")
    await db.connect()
    try:
        bot = LoggingBot(db, on=False)
        await sync_with_log(bot, monkeypatch)
        await db.conn.execute(
            "INSERT INTO personality_tropes(name, label, voice, neighbours, enabled, sort, "
            "source, updated_at) VALUES ('gone', 'gone', 'v', '[]', 1, 50, ?, 'now')",
            (GABI,),
        )
        await db.conn.commit()
        bot.rows.clear()
        assert not (await sync_with_log(bot, monkeypatch)).changed
        assert (await get_trope(db, "gone"))["source"] == GABI
        assert bot.rows == []
    finally:
        await db.close()
