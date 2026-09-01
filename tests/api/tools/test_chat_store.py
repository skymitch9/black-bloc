import pytest

from black_bloc.api.tools import chat_store


@pytest.fixture
async def db(web):
    await chat_store.ensure_tables(web.db)
    return web.db


async def test_a_section_can_be_written_read_changed_and_removed(db, wf):
    made = await chat_store.add_section(db, wf.GUILD_ID, "Cookout hours", "Doors at six.", by=7)

    row = await chat_store.get_section(db, made)
    assert row["title"] == "Cookout hours"
    assert row["source"] == chat_store.STAFF
    assert row["updated_by"] == 7

    await chat_store.update_section(db, made, body="Doors at seven.", by=9)
    row = await chat_store.get_section(db, made)

    assert row["body"] == "Doors at seven."
    assert row["updated_by"] == 9
    assert await chat_store.delete_section(db, made) is True
    assert await chat_store.get_section(db, made) is None


async def test_two_sections_may_not_share_a_heading_within_one_source(db, wf):
    import sqlite3

    await chat_store.add_section(db, wf.GUILD_ID, "Rules", "Be kind.")

    with pytest.raises(sqlite3.IntegrityError):
        await chat_store.add_section(db, wf.GUILD_ID, "Rules", "Be kinder.")


async def test_a_server_row_and_a_staff_row_may_share_a_heading(db, wf):
    """One writer per row: the daily loop owns `server`, staff own `staff`."""
    await chat_store.add_section(db, wf.GUILD_ID, "Channels", "By hand.")
    await chat_store.add_section(
        db, wf.GUILD_ID, "Channels", "From the server.", source=chat_store.SERVER
    )

    rows = await chat_store.list_sections(db, wf.GUILD_ID)

    assert {row["source"] for row in rows} == {chat_store.STAFF, chat_store.SERVER}


async def test_the_ported_pool_is_seeded_once_and_never_overwritten(db, wf):
    made = await chat_store.seed_tropes(db, wf.GUILD_ID)
    await chat_store.set_trope_enabled(db, wf.GUILD_ID, "noir", False, by=7)
    again = await chat_store.seed_tropes(db, wf.GUILD_ID)

    rows = await chat_store.list_tropes(db, wf.GUILD_ID)

    assert made == len(chat_store.POOL_TROPES) == 11
    assert again == 0
    assert [row["name"] for row in rows] == list(chat_store.POOL_NAMES)
    assert (await chat_store.get_trope(db, wf.GUILD_ID, "noir"))["enabled"] == 0


async def test_the_persona_mode_starts_at_the_cookout_voice_and_is_written_in_place(db, wf):
    assert await chat_store.persona_mode(db, wf.GUILD_ID) == chat_store.COOKOUT

    await chat_store.set_persona_mode(db, wf.GUILD_ID, chat_store.POOL, by=7)
    await chat_store.set_persona_mode(db, wf.GUILD_ID, "noir", by=7)

    assert await chat_store.persona_mode(db, wf.GUILD_ID) == "noir"


async def test_the_ledger_counts_this_month_and_today_and_nothing_older(db, wf):
    await chat_store.add_ledger_entry(
        db, wf.GUILD_ID, provider="anthropic", model="claude-haiku-4-5", cost_microdollars=1_250_000
    )
    await chat_store.add_ledger_entry(
        db, wf.GUILD_ID, provider="groq", model="llama-3.3-70b-versatile", cost_microdollars=0
    )
    await chat_store.add_ledger_entry(
        db,
        wf.GUILD_ID,
        provider="anthropic",
        model="claude-haiku-4-5",
        cost_microdollars=9_000_000,
        at="2000-01-01T00:00:00+00:00",
    )

    assert await chat_store.spent_this_month(db, wf.GUILD_ID) == 1_250_000
    assert await chat_store.turns_today(db, wf.GUILD_ID) == 2
    assert await chat_store.last_turn_at(db, wf.GUILD_ID) is not None


async def test_an_empty_ledger_reads_as_zero_rather_than_as_nothing(db, wf):
    assert await chat_store.spent_this_month(db, wf.GUILD_ID) == 0
    assert await chat_store.turns_today(db, wf.GUILD_ID) == 0
    assert await chat_store.last_turn_at(db, wf.GUILD_ID) is None


async def test_the_ported_pool_names_its_source_so_nobody_has_to_guess():
    assert "personality.ts" in chat_store.POOL_SOURCE
    assert all(name and label and voice for name, label, voice in chat_store.POOL_TROPES)
