from black_bloc.channel_notes import (
    clean_note,
    clear_note,
    get_note,
    notes_for,
    notes_or_nothing,
    set_note,
)
from black_bloc.storage.db import Database


async def test_a_note_is_set_replaced_read_and_cleared_per_guild(tmp_path):
    db = Database(tmp_path / "t.sqlite3")
    await db.connect()
    try:
        await set_note(db, 7, 100, "first", by=9, at="2026-09-23T00:00:00+00:00")
        await set_note(db, 7, 100, "second", by=10)
        await set_note(db, 8, 100, "another guild's")
        assert await notes_for(db, 7) == {100: "second"}
        row = await get_note(db, 7, 100)
        assert (row["note"], row["set_by"]) == ("second", 10)
        assert await clear_note(db, 7, 100) is True
        assert await clear_note(db, 7, 100) is False
        assert await notes_for(db, 7) == {}
        assert await notes_for(db, 8) == {100: "another guild's"}
    finally:
        await db.close()


async def test_notes_that_cannot_be_read_are_an_empty_map_never_a_raise(tmp_path):
    db = Database(tmp_path / "t.sqlite3")
    assert await notes_or_nothing(db, 7) == {}
    assert await notes_or_nothing(None, 7) == {}
    await db.connect()
    try:
        await db.conn.execute("DROP TABLE channel_notes")
        assert await notes_or_nothing(db, 7) == {}
    finally:
        await db.close()


def test_a_note_is_one_line_of_plain_spacing():
    assert clean_note("  two\n\nlines   here ") == "two lines here"
    assert clean_note(None) == ""
