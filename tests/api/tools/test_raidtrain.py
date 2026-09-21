from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from black_bloc.api.tools.raidtrain import slot_row, train_row
from black_bloc.cogs.content.raidtrain import create_train, get_train, slots_for
from black_bloc.raidtrain import CANCELLED, DONE, LOCKED, OPEN

GUILD = 4242
ALICE = 21
BOB = 22
START = datetime(2099, 9, 14, 19, 0, tzinfo=UTC)

ROUTES = [
    ("GET", "/api/raidtrains"),
    ("GET", "/api/raidtrains/status"),
    ("GET", "/api/raidtrains/1"),
    ("POST", "/api/raidtrains"),
    ("POST", "/api/raidtrains/1/slots/1"),
    ("POST", "/api/raidtrains/1/swap"),
    ("POST", "/api/raidtrains/1/status"),
]


class FakeCog:
    """The cog the router reaches for: it owns the sweep's health and the lineup post."""

    def __init__(self):
        self.sweep = _Loop()
        self.last_sweep_ok_at = "2026-09-02T00:00:00+00:00"
        self.last_sweep_error = None
        self.sweep_failures = 0
        self.published: list[int] = []
        self.refreshed: list[int] = []
        self.cancelled: list[tuple[int, str]] = []

    async def publish_lineup(self, guild, train_id):
        self.published.append(int(train_id))

    async def _refresh_lineup(self, guild, train_id):
        self.refreshed.append(int(train_id))

    async def cancel_train(self, guild, train, reason, actor, *, via="discord"):
        from black_bloc.actionlog import log_action
        from black_bloc.cogs.content.raidtrain import set_status
        from black_bloc.logkinds import kind_via

        await set_status(self.db, train["id"], CANCELLED, reason=reason)
        await log_action(
            self.bot,
            guild,
            kind_via("raidtrain.cancel", via),
            actor=actor,
            details={"train_id": train["id"], "via": via},
        )
        self.cancelled.append((int(train["id"]), reason, via))
        return 1


class _Loop:
    def is_running(self):
        return True


async def a_train(db, *, starts=START, count=3, minutes=60, guild_id=GUILD):
    return await create_train(
        db,
        guild_id,
        99,
        title="Saturday train",
        description="Everyone welcome.",
        starts_at=starts,
        slot_minutes=minutes,
        slot_count=count,
    )


async def link(db, user_id, login):
    await db.conn.execute(
        "INSERT OR REPLACE INTO golive_links(user_id, twitch_login, linked_at) VALUES (?, ?, ?)",
        (user_id, login, "2026-09-01T00:00:00+00:00"),
    )
    await db.conn.commit()


@pytest.fixture
def cogged(web):
    cog = FakeCog()
    cog.db = web.db
    cog.bot = web
    web.cogs["RaidTrains"] = cog
    return cog


@pytest.mark.parametrize(("method", "route"), ROUTES)
def test_every_raid_train_route_needs_a_session(client, method, route):
    assert client.request(method, route).status_code == 401


@pytest.mark.parametrize(("method", "route"), ROUTES)
def test_every_raid_train_route_refuses_a_non_staff_visitor(client, sign_in, method, route):
    sign_in(client, uid=1234, staff=False)
    assert client.request(method, route).status_code == 403


async def test_the_list_carries_the_counts_the_table_draws(client, sign_in, web):
    train_id = await a_train(web.db)
    sign_in(client)

    rows = client.get("/api/raidtrains").json()

    assert len(rows) == 1
    assert rows[0]["id"] == train_id
    assert rows[0]["title"] == "Saturday train"
    assert rows[0]["filled"] == 0 and rows[0]["slots_total"] == 3
    assert rows[0]["status"] == OPEN
    assert rows[0]["status_word"] == "open for sign-ups"
    assert rows[0]["editable"] is True


async def test_a_finished_train_is_only_in_the_past_and_the_all_scopes(client, sign_in, web):
    train_id = await a_train(web.db)
    await web.db.conn.execute(
        "UPDATE raid_trains SET status = ? WHERE id = ?", (DONE, train_id)
    )
    await web.db.conn.commit()
    sign_in(client)

    assert client.get("/api/raidtrains?scope=upcoming").json() == []
    assert len(client.get("/api/raidtrains?scope=past").json()) == 1
    assert len(client.get("/api/raidtrains?scope=all").json()) == 1
    assert len(client.get("/api/raidtrains?scope=nonsense").json()) == 0


async def test_one_train_carries_its_slots_and_the_lineup_as_it_reads(
    client, sign_in, web, guild, wf
):
    wf.member(guild, ALICE, name="ada")
    train_id = await a_train(web.db)
    slots = await slots_for(web.db, train_id)
    await web.db.conn.execute(
        "UPDATE raid_slots SET user_id = ?, twitch_login = ? WHERE id = ?",
        (ALICE, "adastreams", slots[0]["id"]),
    )
    await web.db.conn.commit()
    sign_in(client)

    body = client.get(f"/api/raidtrains/{train_id}").json()

    assert [row["position"] for row in body["slots"]] == [1, 2, 3]
    assert body["slots"][0]["user_name"] == "Ada"
    assert body["slots"][0]["state"] == "taken"
    assert body["slots"][1]["state"] == "open"
    assert body["slots"][1]["user_id"] is None
    assert "Saturday train" in body["lineup"]
    assert body["filled"] == 1


def test_a_train_that_is_not_there_says_where_to_look(client, sign_in):
    sign_in(client)

    response = client.get("/api/raidtrains/404")

    assert response.status_code == 404
    assert "no raid train" in response.json()["message"]


async def test_the_status_route_reports_the_sweeps_own_health(client, sign_in, web, cogged):
    await a_train(web.db)
    sign_in(client)

    body = client.get("/api/raidtrains/status").json()

    assert body["mode"] == "off"
    assert body["running"] is True
    assert body["last_ok_at"] == "2026-09-02T00:00:00+00:00"
    assert body["last_error"] is None
    assert body["upcoming"] == 1 and body["slots"] == 3 and body["claimed"] == 0
    assert body["every_minutes"] == 5


async def test_creating_a_train_writes_its_slots_and_posts_the_lineup(
    client, sign_in, web, cogged, wf
):
    sign_in(client)

    response = client.post(
        "/api/raidtrains",
        json={
            "title": "Saturday train",
            "description": "Everyone welcome.",
            "start": "2099-09-14 19:30",
            "tz": "UTC",
            "slot_minutes": 60,
            "slot_count": 4,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["slots_total"] == 4
    assert "4 slot(s) of 60 minutes" in body["message"]
    assert len(await slots_for(web.db, body["id"])) == 4
    assert cogged.published == [body["id"]]
    await wf.one_web_row(web.db, "web.raidtrain.create")


@pytest.mark.parametrize(
    ("payload", "said"),
    [
        ({"title": "", "start": "2099-09-14 19:30"}, "needs a title"),
        ({"title": "T", "start": "not a date"}, "YYYY-MM-DD HH:MM"),
        ({"title": "T", "start": "2020-01-01 10:00"}, "already gone by"),
        (
            {"title": "T", "start": "2099-09-14 19:30", "slot_minutes": 5, "slot_count": 3},
            "15 to 720 minutes",
        ),
        (
            {"title": "T", "start": "2099-09-14 19:30", "slot_minutes": 60, "slot_count": 99},
            "1 to 24 slots",
        ),
    ],
)
async def test_a_train_nobody_could_run_is_refused_in_words(
    client, sign_in, web, cogged, payload, said
):
    sign_in(client)

    response = client.post("/api/raidtrains", json={"tz": "UTC", **payload})

    assert response.status_code == 400
    assert said in response.json()["message"]
    assert await web.db.conn.execute("SELECT * FROM raid_trains")
    assert client.get("/api/raidtrains?scope=all").json() == []


async def test_creating_without_the_cog_loaded_says_the_feature_is_not_loaded(
    client, sign_in, web
):
    sign_in(client)

    response = client.post(
        "/api/raidtrains",
        json={"title": "T", "start": "2099-09-14 19:30", "tz": "UTC", "slot_count": 3},
    )

    assert response.status_code == 503
    assert "Raid trains" in response.json()["message"]


async def test_a_slot_is_filled_and_emptied_through_one_route(
    client, sign_in, web, guild, wf, cogged
):
    wf.member(guild, ALICE, name="ada")
    await link(web.db, ALICE, "adastreams")
    train_id = await a_train(web.db)
    sign_in(client)

    filled = client.post(
        f"/api/raidtrains/{train_id}/slots/2", json={"member_id": str(ALICE)}
    ).json()
    assert "now belongs to Ada" in filled["message"]
    assert filled["slots"][1]["user_id"] == str(ALICE)
    assert filled["slots"][1]["twitch_login"] == "adastreams"

    emptied = client.post(f"/api/raidtrains/{train_id}/slots/2", json={"member_id": None}).json()
    assert "open again" in emptied["message"]
    assert emptied["slots"][1]["user_id"] is None
    rows = await wf.web_rows_in(web.db)
    assert [kind for kind, _ in rows] == ["web.raidtrain.assign", "web.raidtrain.unassign"]
    assert all(details.get("via") == wf.VIA_WEBSITE for _, details in rows)
    assert [one for one in await wf.kinds_in(web.db) if one.startswith("raidtrain.")] == []
    assert cogged.refreshed == [train_id, train_id]


async def test_emptying_a_slot_nobody_holds_is_a_sentence_not_a_crash(
    client, sign_in, web, cogged
):
    train_id = await a_train(web.db)
    sign_in(client)

    response = client.post(f"/api/raidtrains/{train_id}/slots/1", json={"member_id": None})

    assert response.status_code == 409
    assert "already empty" in response.json()["message"]


async def test_a_slot_number_off_the_end_says_how_many_there_are(client, sign_in, web, cogged):
    train_id = await a_train(web.db, count=3)
    sign_in(client)

    response = client.post(f"/api/raidtrains/{train_id}/slots/9", json={"member_id": None})

    assert response.status_code == 404
    assert "#1 to #3" in response.json()["message"]


async def test_assigning_somebody_with_no_twitch_link_names_the_command(
    client, sign_in, web, guild, wf, cogged
):
    wf.member(guild, BOB, name="bo")
    train_id = await a_train(web.db)
    sign_in(client)

    response = client.post(
        f"/api/raidtrains/{train_id}/slots/1", json={"member_id": str(BOB)}
    )

    assert response.status_code == 409
    assert "**Link my Twitch channel**" in response.json()["message"]
    assert (await slots_for(web.db, train_id))[0]["user_id"] is None


async def test_the_link_requirement_can_be_turned_off_for_an_assignment(
    client, sign_in, web, guild, wf, cogged
):
    wf.member(guild, BOB, name="bo")
    await web.store.set(GUILD, "raidtrain_require_link", False)
    train_id = await a_train(web.db)
    sign_in(client)

    body = client.post(
        f"/api/raidtrains/{train_id}/slots/1", json={"member_id": str(BOB)}
    ).json()

    assert body["slots"][0]["user_id"] == str(BOB)
    assert body["slots"][0]["twitch_login"] is None


async def test_a_swap_moves_the_people_and_leaves_the_times(
    client, sign_in, web, guild, wf, cogged
):
    wf.member(guild, ALICE, name="ada")
    wf.member(guild, BOB, name="bo")
    await link(web.db, ALICE, "adastreams")
    await link(web.db, BOB, "bostreams")
    train_id = await a_train(web.db)
    sign_in(client)
    client.post(f"/api/raidtrains/{train_id}/slots/1", json={"member_id": str(ALICE)})
    client.post(f"/api/raidtrains/{train_id}/slots/2", json={"member_id": str(BOB)})
    before = [row["starts_at"] for row in await slots_for(web.db, train_id)]

    body = client.post(f"/api/raidtrains/{train_id}/swap", json={"a": 1, "b": 2}).json()

    assert "changed places" in body["message"]
    assert [row["user_id"] for row in body["slots"]] == [str(BOB), str(ALICE), None]
    assert [row["starts_at"] for row in await slots_for(web.db, train_id)] == before
    assert [kind for kind, _ in await wf.web_rows_in(web.db)] == [
        "web.raidtrain.assign",
        "web.raidtrain.assign",
        "web.raidtrain.swap",
    ]


async def test_swapping_a_slot_with_itself_is_refused(client, sign_in, web, cogged):
    train_id = await a_train(web.db)
    sign_in(client)

    response = client.post(f"/api/raidtrains/{train_id}/swap", json={"a": 2, "b": 2})

    assert response.status_code == 400
    assert "same slot" in response.json()["message"]


async def test_locking_and_unlocking_go_through_the_transition_table(
    client, sign_in, web, cogged, wf
):
    train_id = await a_train(web.db)
    sign_in(client)

    locked = client.post(f"/api/raidtrains/{train_id}/status", json={"status": "locked"})
    assert locked.status_code == 200
    assert (await get_train(web.db, GUILD, train_id))["status"] == LOCKED

    again = client.post(f"/api/raidtrains/{train_id}/status", json={"status": "locked"})
    assert again.status_code == 409
    assert "cannot be marked **locked**" in again.json()["message"]

    opened = client.post(f"/api/raidtrains/{train_id}/status", json={"status": "open"})
    assert opened.status_code == 200
    assert (await get_train(web.db, GUILD, train_id))["status"] == OPEN
    assert [kind for kind, _ in await wf.web_rows_in(web.db)] == [
        "web.raidtrain.lock",
        "web.raidtrain.unlock",
    ]
    assert [one for one in await wf.kinds_in(web.db) if one.startswith("raidtrain.")] == []


async def test_a_status_that_is_not_one_of_the_five_is_named_back(client, sign_in, web, cogged):
    train_id = await a_train(web.db)
    sign_in(client)

    response = client.post(f"/api/raidtrains/{train_id}/status", json={"status": "sideways"})

    assert response.status_code == 400
    assert "sideways" in response.json()["message"]


async def test_cancelling_needs_a_reason_and_then_goes_through_the_cog(
    client, sign_in, web, cogged, wf
):
    """A website cancellation used to read Via = Discord; the `via` keyword is what fixes it."""
    train_id = await a_train(web.db)
    sign_in(client)

    bare = client.post(f"/api/raidtrains/{train_id}/status", json={"status": "cancelled"})
    assert bare.status_code == 400
    assert "needs a reason" in bare.json()["message"]

    done = client.post(
        f"/api/raidtrains/{train_id}/status",
        json={"status": "cancelled", "reason": "the venue fell through"},
    )
    assert done.status_code == 200
    assert cogged.cancelled == [(train_id, "the venue fell through", wf.VIA_WEBSITE)]
    assert (await get_train(web.db, GUILD, train_id))["status"] == CANCELLED
    await wf.one_web_row(web.db, "web.raidtrain.cancel")


async def test_the_row_shapes_never_leak_a_raw_snowflake_as_a_number(client, web, guild, wf):
    wf.member(guild, ALICE, name="ada")
    train_id = await a_train(web.db)
    train = await get_train(web.db, GUILD, train_id)
    slots = await slots_for(web.db, train_id)

    row = train_row(guild, train, slots)
    assert isinstance(row["organizer_id"], str)
    assert row["channel_id"] is None and row["scheduled"] is False

    empty = slot_row(guild, slots[0])
    assert empty["user_id"] is None and empty["user_name"] is None


async def test_a_train_in_another_server_is_invisible(client, sign_in, web):
    await a_train(web.db, guild_id=GUILD + 1)
    sign_in(client)

    assert client.get("/api/raidtrains?scope=all").json() == []


async def test_a_slot_route_on_a_train_that_is_not_there_says_so(client, sign_in, web, cogged):
    sign_in(client)

    response = client.post("/api/raidtrains/404/slots/1", json={"member_id": None})

    assert response.status_code == 404
    assert "no raid train" in response.json()["message"]


async def test_a_start_may_also_arrive_as_an_iso_timestamp(client, sign_in, web, cogged):
    sign_in(client)
    when = (datetime.now(UTC) + timedelta(days=3)).isoformat()

    response = client.post(
        "/api/raidtrains",
        json={"title": "ISO train", "start": when, "tz": "UTC", "slot_count": 2},
    )

    assert response.status_code == 200
    assert response.json()["slots_total"] == 2


# --- the event a train can carry ------------------------------------------------------------------


async def review_ready(web, wf):
    """A review room needs a category to go in; without one `submit_event` refuses."""
    await web.store.set(GUILD, "events_category_id", wf.CATEGORY_ID, by=7)
    await web.store.set(GUILD, "events_create_scheduled", False, by=7)


async def events_in(db):
    cur = await db.conn.execute("SELECT * FROM events ORDER BY id")
    return [dict(row) for row in await cur.fetchall()]


def test_the_event_route_needs_a_session(client):
    assert client.post("/api/raidtrains/1/event", json={}).status_code == 401


def test_the_event_route_refuses_a_non_staff_visitor(client, sign_in):
    sign_in(client, uid=1234, staff=False)
    assert client.post("/api/raidtrains/1/event", json={}).status_code == 403


async def test_making_a_train_with_make_event_leaves_an_event_in_review(
    client, sign_in, web, wf, cogged
):
    await review_ready(web, wf)
    sign_in(client)

    body = client.post("/api/raidtrains", json={
        "title": "Saturday train",
        "start": "2099-09-14 19:30",
        "tz": "UTC",
        "slot_minutes": 60,
        "slot_count": 3,
        "make_event": True,
    }).json()

    rows = await events_in(web.db)
    assert len(rows) == 1 and rows[0]["status"] == "pending"
    assert body["event_id"] == rows[0]["id"]
    assert body["event_status"] == "pending"
    assert f"#{rows[0]['id']}" in body["message"]


async def test_making_a_train_without_it_leaves_none(client, sign_in, web, wf, cogged):
    await review_ready(web, wf)
    sign_in(client)

    body = client.post("/api/raidtrains", json={
        "title": "Saturday train",
        "start": "2099-09-14 19:30",
        "tz": "UTC",
        "slot_minutes": 60,
        "slot_count": 3,
    }).json()

    assert await events_in(web.db) == []
    assert body["event_id"] is None and body["event_status"] is None


async def test_the_key_decides_when_the_body_says_nothing(client, sign_in, web, wf, cogged):
    await review_ready(web, wf)
    await web.store.set(GUILD, "raidtrain_event_default", True, by=7)
    sign_in(client)

    body = client.post("/api/raidtrains", json={
        "title": "Saturday train",
        "start": "2099-09-14 19:30",
        "tz": "UTC",
        "slot_minutes": 60,
        "slot_count": 3,
    }).json()

    assert body["event_id"] is not None
    assert len(await events_in(web.db)) == 1


async def test_an_explicit_no_beats_the_key(client, sign_in, web, wf, cogged):
    await review_ready(web, wf)
    await web.store.set(GUILD, "raidtrain_event_default", True, by=7)
    sign_in(client)

    body = client.post("/api/raidtrains", json={
        "title": "Saturday train",
        "start": "2099-09-14 19:30",
        "tz": "UTC",
        "slot_minutes": 60,
        "slot_count": 3,
        "make_event": False,
    }).json()

    assert body["event_id"] is None
    assert await events_in(web.db) == []


async def test_an_existing_train_can_have_its_event_made_later(
    client, sign_in, web, wf, cogged
):
    await review_ready(web, wf)
    train_id = await a_train(web.db)
    sign_in(client)

    body = client.post(f"/api/raidtrains/{train_id}/event", json={}).json()

    rows = await events_in(web.db)
    assert len(rows) == 1
    assert body["event_id"] == rows[0]["id"] and body["event_status"] == "pending"
    row = await get_train(web.db, GUILD, train_id)
    assert row["event_id"] == rows[0]["id"]


async def test_a_second_event_for_one_train_is_refused_in_words(
    client, sign_in, web, wf, cogged
):
    await review_ready(web, wf)
    train_id = await a_train(web.db)
    sign_in(client)
    client.post(f"/api/raidtrains/{train_id}/event", json={})

    response = client.post(f"/api/raidtrains/{train_id}/event", json={})

    assert response.status_code == 409
    assert "already has event" in response.json()["message"]
    assert len(await events_in(web.db)) == 1


async def test_a_settled_train_raises_nothing_and_says_why(client, sign_in, web, wf, cogged):
    await review_ready(web, wf)
    train_id = await a_train(web.db)
    await web.db.conn.execute(
        "UPDATE raid_trains SET status = ? WHERE id = ?", (DONE, train_id)
    )
    await web.db.conn.commit()
    sign_in(client)

    response = client.post(f"/api/raidtrains/{train_id}/event", json={})

    assert response.status_code == 409
    assert "done" in response.json()["message"]
    assert await events_in(web.db) == []


async def test_the_event_route_says_where_to_look_when_the_train_is_gone(client, sign_in, cogged):
    sign_in(client)

    response = client.post("/api/raidtrains/404/event", json={})

    assert response.status_code == 404
    assert "no raid train" in response.json()["message"]


async def test_the_list_and_the_row_both_carry_the_event_the_train_holds(
    client, sign_in, web, wf, cogged
):
    await review_ready(web, wf)
    train_id = await a_train(web.db)
    sign_in(client)
    client.post(f"/api/raidtrains/{train_id}/event", json={})

    listed = client.get("/api/raidtrains").json()
    one = client.get(f"/api/raidtrains/{train_id}").json()

    assert listed[0]["event_id"] == one["event_id"]
    assert listed[0]["event_status"] == "pending" and one["event_status"] == "pending"


async def test_a_website_event_is_logged_as_the_website(client, sign_in, web, wf, cogged):
    await review_ready(web, wf)
    train_id = await a_train(web.db)
    sign_in(client)

    client.post(f"/api/raidtrains/{train_id}/event", json={})

    cur = await web.db.conn.execute("SELECT kind FROM action_log ORDER BY id")
    kinds = [row["kind"] for row in await cur.fetchall()]
    assert kinds.count("web.raidtrain.event_made") == 1
    assert "raidtrain.event_made" not in kinds
