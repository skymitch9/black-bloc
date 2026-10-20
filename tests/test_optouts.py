from types import SimpleNamespace

import pytest

from black_bloc import optouts

GUILD = 7
OTHER_GUILD = 8
AT = "2026-10-20T09:00:00+00:00"


async def golive_rows(db):
    cur = await db.conn.execute("SELECT user_id FROM golive_optout ORDER BY user_id")
    return [row["user_id"] for row in await cur.fetchall()]


async def test_one_row_per_person_kind_and_guild_and_a_second_write_is_a_no_op(db):
    assert await optouts.set_out(db, GUILD, 21, optouts.BIRTHDAY, by=9, reason="r", at=AT)
    assert not await optouts.set_out(db, GUILD, 21, optouts.BIRTHDAY, by=10)
    await optouts.set_out(db, OTHER_GUILD, 21, optouts.BIRTHDAY)

    row = await optouts.row_of(db, GUILD, 21, optouts.BIRTHDAY)
    assert (row["by"], row["reason"], row["at"]) == (9, "r", AT)
    assert await optouts.is_out(db, GUILD, 21, optouts.BIRTHDAY) is True
    assert await optouts.is_out(db, GUILD, 21, optouts.PBS) is False
    assert await optouts.out_of(db, GUILD, optouts.BIRTHDAY) == {21}
    assert await optouts.count(db, OTHER_GUILD, optouts.BIRTHDAY) == 1

    assert await optouts.clear_out(db, GUILD, 21, optouts.BIRTHDAY) is True
    assert await optouts.clear_out(db, GUILD, 21, optouts.BIRTHDAY) is False
    assert await optouts.is_out(db, OTHER_GUILD, 21, optouts.BIRTHDAY) is True


async def test_rows_lists_the_out_kinds_and_never_the_chat_memory_opt_in(db):
    await optouts.set_out(db, GUILD, 21, optouts.ANNOUNCE)
    await optouts.set_out(db, GUILD, 22, optouts.CHAT_MEMORY_IN)

    found = await optouts.rows(db, GUILD)

    assert [(row["user_id"], row["kind"]) for row in found] == [(21, "announce")]
    assert [row["user_id"] for row in await optouts.rows(db, GUILD, (optouts.CHAT_MEMORY_IN,))] == [
        22
    ]


async def test_an_unknown_kind_is_a_fault_in_the_code_and_never_a_silent_no(db):
    with pytest.raises(ValueError):
        await optouts.is_out(db, GUILD, 21, "anounce")
    with pytest.raises(ValueError):
        await optouts.set_out(db, GUILD, 21, "anounce")


async def test_an_unreadable_table_answers_out_so_nobody_is_announced_by_a_fault(db, caplog):
    await db.conn.execute("DROP TABLE person_optouts")
    await db.conn.commit()

    assert await optouts.is_out(db, GUILD, 21, optouts.ANNOUNCE) is True
    assert "opt-outs: announce was not read" in caplog.text


async def test_the_announce_kind_is_still_written_to_the_go_live_table_for_one_release(db):
    await optouts.set_out(db, GUILD, 21, optouts.ANNOUNCE)
    await optouts.set_out(db, GUILD, 22, optouts.BIRTHDAY)
    assert await golive_rows(db) == [21]

    await optouts.clear_out(db, GUILD, 21, optouts.ANNOUNCE)

    assert await golive_rows(db) == []


async def test_the_announce_opt_outs_are_held_in_memory_for_the_readers_that_cannot_wait(db):
    assert optouts.silenced(db, GUILD) == frozenset()
    await optouts.set_out(db, GUILD, 21, optouts.ANNOUNCE)
    await optouts.set_out(db, OTHER_GUILD, 23, optouts.ANNOUNCE)
    assert optouts.silenced(db, GUILD) == frozenset({21})

    await optouts.clear_out(db, GUILD, 21, optouts.ANNOUNCE)

    assert optouts.silenced(db, GUILD) == frozenset()
    assert optouts.silenced(db, OTHER_GUILD) == frozenset({23})
    assert optouts.silenced(None, GUILD) == frozenset()


async def test_a_row_written_behind_the_helpers_back_is_seen_after_a_load(db):
    await db.conn.execute(
        "INSERT INTO person_optouts(guild_id, user_id, kind, at) VALUES (?, ?, 'announce', ?)",
        (GUILD, 24, AT),
    )
    await db.conn.commit()

    assert await optouts.load(db) == {GUILD: frozenset({24})}
    assert optouts.silenced(db, GUILD) == frozenset({24})


def test_words_staff_broke_fall_back_to_the_shipped_ones():
    store = SimpleNamespace(get=lambda _guild, _key: "{nope}")

    said = optouts.said(store, GUILD, "golive_ignored_role_word", role="Lurker")

    assert said == "ignored by role (Lurker)"


async def test_an_override_is_one_row_with_the_actor_and_the_reason(db):
    from black_bloc.config import load_settings
    from black_bloc.settings_store import SettingsStore

    store = SettingsStore(db, load_settings(_env_file=None))
    await store.load()
    bot = SimpleNamespace(db=db, store=store, get_channel=lambda _id: None)

    await optouts.overridden(
        bot,
        SimpleNamespace(id=GUILD, get_channel=lambda _id: None),
        SimpleNamespace(id=9),
        21,
        kind=optouts.ANNOUNCE,
        move="golive_opt_back_in",
        via="website",
    )

    cur = await db.conn.execute("SELECT kind, actor_id, target_id, details FROM action_log")
    (row,) = await cur.fetchall()
    assert (row["kind"], row["actor_id"], row["target_id"]) == ("web.optouts.overridden", 9, 21)
    assert '"move": "golive_opt_back_in"' in row["details"]
