import json

import pytest

from black_bloc.chat_memory import Note, Profile, profile_for, save_profile, set_override

LEAD = 7
ASKER = 21
STRANGER = 22
AT = "2026-09-02T00:00:00+00:00"


@pytest.fixture
async def people(web, wf, guild):
    wf.member(guild, LEAD, name="lead", staff=True)
    wf.member(guild, ASKER, name="ada")
    return guild


@pytest.fixture
async def as_staff(client, sign_in, people, web, wf):
    sign_in(client, uid=LEAD, staff=True)
    await web.store.set(wf.GUILD_ID, "chat_memory_mode", "on", by=LEAD)
    return client


async def a_profile(web, wf, *, user_id=ASKER, where="server"):
    await save_profile(
        web.db,
        user_id,
        wf.GUILD_ID,
        Profile(
            call_me="Sky",
            notes=(
                Note("likes short answers", "server", AT),
                Note("keep it simple", where, AT),
            ),
            threads=(Note("was asking about the cookout", "server", AT),),
            turns_seen=6,
            created_at=AT,
            updated_at=AT,
        ),
    )


async def test_the_page_gets_counts_and_never_the_notes_while_the_server_says_counts(
    as_staff, web, wf
):
    await a_profile(web, wf, where="dm")
    await set_override(web.db, STRANGER, wf.GUILD_ID)

    payload = as_staff.get("/api/chat/memory").json()
    row = payload["profiles"][0]

    assert payload["on"] is True and payload["mode"] == "on"
    assert payload["staff_view"] == "counts"
    assert payload["total"] == 1 and payload["opted_out"] == 1
    assert payload["dm_notes"] == 1
    assert row["member"] == {"id": str(ASKER), "name": "Ada"}
    assert row["notes"] == 2 and row["threads"] == 1 and row["turns_seen"] == 6
    assert row["call_me"] is None and row["lines"] == []
    assert "likes short answers" not in as_staff.get("/api/chat/memory").text


async def test_full_lets_staff_read_the_notes_themselves(as_staff, web, wf):
    await web.store.set(wf.GUILD_ID, "chat_memory_staff_view", "full", by=LEAD)
    await a_profile(web, wf, where="dm")

    row = as_staff.get("/api/chat/memory").json()["profiles"][0]

    assert row["call_me"] == "Sky"
    assert [one["text"] for one in row["lines"]] == [
        "likes short answers",
        "keep it simple",
        "was asking about the cookout",
    ]
    assert [one["kind"] for one in row["lines"]] == ["note", "note", "thread"]
    assert row["lines"][1]["where"] == "dm"


async def test_memory_off_says_so_in_words_rather_than_looking_broken(as_staff, web, wf):
    await web.store.set(wf.GUILD_ID, "chat_memory_mode", "off", by=LEAD)

    payload = as_staff.get("/api/chat/memory").json()

    assert payload["on"] is False
    assert "not remembering anybody" in payload["message"]
    assert "Memory switch" in payload["message"]


async def test_one_profile_is_refused_in_words_while_the_server_keeps_it_private(
    as_staff, web, wf
):
    """A person never sees a bare 403: what happened, what it needs, how to get it."""
    await a_profile(web, wf)

    refused = as_staff.get(f"/api/chat/memory/{ASKER}")

    assert refused.status_code == 403
    assert refused.json()["error"] == "memory_is_private"
    said = refused.json()["message"]
    assert "private to that member" in said
    assert "chat_memory_staff_view" in said and "full" in said
    assert "`/memory`" in said and "/memory show" not in said


async def test_one_profile_reads_back_once_the_server_has_said_full(as_staff, web, wf):
    await web.store.set(wf.GUILD_ID, "chat_memory_staff_view", "full", by=LEAD)
    await a_profile(web, wf)

    payload = as_staff.get(f"/api/chat/memory/{ASKER}").json()

    assert payload["profile"]["call_me"] == "Sky"
    assert payload["profile"]["notes"] == 2


async def test_a_member_with_nothing_written_down_is_a_sentence_and_a_404(as_staff, web, wf):
    await web.store.set(wf.GUILD_ID, "chat_memory_staff_view", "full", by=LEAD)

    missing = as_staff.get(f"/api/chat/memory/{ASKER}")

    assert missing.status_code == 404 and "remembers nothing" in missing.json()["message"]


async def test_staff_clear_a_profile_and_the_line_says_who_asked(as_staff, web, wf):
    """One web write, ONE log row: the route calls the shared forget and never notes it again."""
    await a_profile(web, wf)

    gone = as_staff.delete(f"/api/chat/memory/{ASKER}")

    assert gone.status_code == 200
    assert gone.json()["member"]["name"] == "Ada"
    assert "remembers nothing about Ada" in gone.json()["message"]
    assert await profile_for(web.db, ASKER, wf.GUILD_ID) is None
    kinds = await wf.kinds_in(web.db)
    assert kinds.count("web.chat.memory_forgot") == 1
    assert "chat.memory_forgot" not in kinds
    cur = await web.db.conn.execute(
        "SELECT details FROM action_log WHERE kind = 'web.chat.memory_forgot'"
    )
    rows = await cur.fetchall()
    assert len(rows) == 1
    assert json.loads(rows[0]["details"]) == {"who_asked": "staff", "via": "website"}


async def test_clearing_a_profile_that_is_not_there_is_a_sentence_and_a_404(as_staff, web, wf):
    missing = as_staff.delete(f"/api/chat/memory/{ASKER}")

    assert missing.status_code == 404 and "remembers nothing" in missing.json()["message"]


async def test_the_whole_namespace_is_staff_only(client, sign_in, people, web, wf):
    await a_profile(web, wf)
    sign_in(client, uid=ASKER, staff=False)

    assert client.get("/api/chat/memory").status_code == 403
    assert client.get(f"/api/chat/memory/{ASKER}").status_code == 403
    assert client.delete(f"/api/chat/memory/{ASKER}").status_code == 403
