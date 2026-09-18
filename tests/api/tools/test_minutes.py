from __future__ import annotations

import pytest

from black_bloc import minutes as mins
from black_bloc.llm import Reply, Usage

ROUTES = [
    ("GET", "/api/minutes", None),
    ("GET", "/api/minutes/1", None),
    ("PUT", "/api/minutes/1", {"notes": "hello"}),
    ("POST", "/api/minutes/1/write", {}),
    ("POST", "/api/minutes/1/post", {}),
    ("DELETE", "/api/minutes/1", None),
]


class FakeNotes:
    def __init__(self, text="Summary.\nDecisions: none."):
        self.text = text
        self.calls = []

    async def reply(self, *, system, messages):
        self.calls.append((list(system), list(messages)))
        return Reply(text=self.text, provider="anthropic", model="m", usage=Usage())


@pytest.fixture(autouse=True)
async def mode_is_on(web, wf):
    """Off is the key's default; every test that does not say otherwise is `on`."""
    await web.store.set(wf.GUILD_ID, mins.MODE_KEY, mins.ON)
    web.minutes_notes_client = FakeNotes()
    web.settings = web.store.settings = web.settings.model_copy(
        update={"anthropic_api_key": "k" * 10, "groq_api_key": "k" * 10}
    )


async def a_meeting(web, wf, *, lines=True, ended=True, notes="Summary."):
    row = await mins.start_row(web.db, wf.GUILD_ID, wf.TEST_CHANNEL_ID, 7)
    if lines:
        for at, speaker in ((1, "Mod"), (2, "Casey")):
            await mins.add_line(
                web.db,
                int(row["id"]),
                speaker_id=7 + at,
                speaker=speaker,
                started_at=f"2026-09-17T18:0{at}:00+00:00",
                text=f"Line {at}.",
            )
    if ended:
        await mins.end_row(web.db, int(row["id"]), mins.BY_HAND)
        if notes:
            await mins.save_notes_row(web.db, int(row["id"]), notes, mins.DONE)
    return await mins.get_meeting(web.db, wf.GUILD_ID, row["id"])


@pytest.mark.parametrize("method,route,payload", ROUTES)
def test_every_route_is_staff_only(client, sign_in, web, wf, method, route, payload):
    sign_in(client, uid=9, staff=False)

    response = client.request(method, route, json=payload)

    assert response.status_code == 403
    assert response.json()["error"] == "not_staff"


@pytest.mark.parametrize("method,route,payload", ROUTES)
def test_every_route_says_so_when_nobody_is_signed_in(client, web, wf, method, route, payload):
    client.cookies.clear()

    response = client.request(method, route, json=payload)

    assert response.status_code == 401
    assert len(response.json()["message"].split()) > 5


async def test_the_list_carries_the_mode_the_guard_and_what_the_host_can_do(
    client, sign_in, web, wf
):
    sign_in(client)
    await a_meeting(web, wf)

    found = client.get("/api/minutes").json()

    assert found["mode"] == mins.ON
    assert len(found["meetings"]) == 1
    assert set(found["guard"]) == {"test_mode", "test_channel", "said"}
    assert set(found["host"]) == {"extension", "opus", "transcriber", "notes_writer"}


async def test_the_list_says_in_words_that_the_prototype_is_off(client, sign_in, web, wf):
    sign_in(client)
    await web.store.set(wf.GUILD_ID, mins.MODE_KEY, mins.OFF)

    found = client.get("/api/minutes").json()

    assert any("prototype" in line for line in found["notes"])


async def test_one_meeting_carries_its_transcript_in_the_order_it_was_said(
    client, sign_in, web, wf
):
    sign_in(client)
    row = await a_meeting(web, wf)

    found = client.get(f"/api/minutes/{row['id']}").json()

    assert [one["text"] for one in found["transcript"]] == ["Line 1.", "Line 2."]
    assert found["speakers"] == ["Mod", "Casey"]
    assert found["meeting"]["lines"] == 2


async def test_a_meeting_that_is_not_there_is_refused_in_words(client, sign_in, web, wf):
    sign_in(client)

    response = client.get("/api/minutes/9999")

    assert response.status_code == 404
    assert response.json()["error"] == "no_such_meeting"
    assert "9999" in response.json()["message"]


async def test_staff_can_rewrite_the_notes_and_the_row_says_the_website_did_it(
    client, sign_in, web, wf
):
    sign_in(client)
    row = await a_meeting(web, wf)

    found = client.put(
        f"/api/minutes/{row['id']}", json={"notes": "Staff wrote this."}
    ).json()

    assert found["meeting"]["notes"] == "Staff wrote this."
    assert await wf.kinds_in(web.db) == ["web.minutes.notes_edited"]


async def test_blank_notes_are_refused_in_words_and_nothing_is_stored(client, sign_in, web, wf):
    sign_in(client)
    row = await a_meeting(web, wf, notes="Kept.")

    response = client.put(f"/api/minutes/{row['id']}", json={"notes": "   "})

    assert response.status_code == 400
    assert response.json()["error"] == "notes_blank"
    fresh = await mins.get_meeting(web.db, wf.GUILD_ID, row["id"])
    assert fresh["notes"] == "Kept."


async def test_notes_past_the_cap_are_refused_with_the_count_to_take_out(
    client, sign_in, web, wf
):
    sign_in(client)
    row = await a_meeting(web, wf)

    response = client.put(
        f"/api/minutes/{row['id']}", json={"notes": "x" * (mins.NOTES_MAX + 2)}
    )

    assert response.status_code == 400
    assert "Take 2 characters out" in response.json()["message"]


async def test_writing_the_notes_again_reads_the_transcript_and_says_the_website_did_it(
    client, sign_in, web, wf
):
    sign_in(client)
    row = await a_meeting(web, wf, notes="Old.")

    found = client.post(f"/api/minutes/{row['id']}/write", json={}).json()

    assert found["meeting"]["notes"] == "Summary.\nDecisions: none."
    assert await wf.kinds_in(web.db) == ["web.minutes.notes_written"]


async def test_a_meeting_still_recording_refuses_both_notes_moves_in_words(
    client, sign_in, web, wf
):
    sign_in(client)
    row = await a_meeting(web, wf, ended=False)

    for path in ("write", "post"):
        response = client.post(f"/api/minutes/{row['id']}/{path}", json={})
        assert response.status_code == 409
        assert response.json()["error"] == "still_recording"
        assert "Press **Stop**" in response.json()["message"]


async def test_a_meeting_nobody_spoke_in_refuses_the_rewrite_in_words(client, sign_in, web, wf):
    sign_in(client)
    row = await a_meeting(web, wf, lines=False)

    response = client.post(f"/api/minutes/{row['id']}/write", json={})

    assert response.status_code == 409
    assert response.json()["error"] == "nothing_heard"


async def test_posting_again_records_where_it_went_and_leaves_one_row(
    client, sign_in, web, wf, guild
):
    sign_in(client)
    row = await a_meeting(web, wf)

    found = client.post(f"/api/minutes/{row['id']}/post", json={}).json()

    assert found["meeting"]["posted"] is True
    assert await wf.kinds_in(web.db) == ["web.minutes.posted"]


async def test_deleting_a_meeting_takes_its_transcript_and_says_so(client, sign_in, web, wf):
    sign_in(client)
    row = await a_meeting(web, wf)

    found = client.delete(f"/api/minutes/{row['id']}").json()

    assert found["deleted"] == str(row["id"])
    assert await mins.get_meeting(web.db, wf.GUILD_ID, row["id"]) is None
    assert await mins.count_lines(web.db, int(row["id"])) == 0
    assert await wf.kinds_in(web.db) == ["web.minutes.deleted"]


async def test_the_website_never_writes_the_bare_kind_beside_the_web_one(
    client, sign_in, web, wf
):
    """Checklist 34: one web write leaves ONE row, and it wears the `web.` head."""
    sign_in(client)
    row = await a_meeting(web, wf)

    client.put(f"/api/minutes/{row['id']}", json={"notes": "One row only."})
    client.post(f"/api/minutes/{row['id']}/post", json={})

    kinds = await wf.kinds_in(web.db)
    assert kinds == ["web.minutes.notes_edited", "web.minutes.posted"]
    assert all(kind.startswith("web.") for kind in kinds)
