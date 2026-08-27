from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from black_bloc.api.server import create_app
from black_bloc.api.status import DB_UNREACHABLE, loop_health, mode_keys, open_counts
from black_bloc.settings_store import DB_UNAVAILABLE, KEY_TYPES
from black_bloc.storage.db import Database


def _named(name: str):
    def coro():
        return None

    coro.__name__ = name
    return coro


class FakeLoop:
    def __init__(self, name: str, *, running: bool = True, failed: bool = False, **health) -> None:
        self.coro = _named(name)
        self._running = running
        self._failed = failed
        self.next_iteration = datetime(2026, 8, 26, 12, 0, tzinfo=UTC)
        for key, value in health.items():
            setattr(self, key, value)

    def is_running(self) -> bool:
        return self._running

    def failed(self) -> bool:
        return self._failed


class FakeCog:
    def __init__(self, *loops) -> None:
        self._loops = loops

    def get_tasks(self):
        return self._loops


def client_for(bot) -> TestClient:
    return TestClient(create_app(bot), base_url="https://testserver")


@pytest.fixture
async def db(tmp_path):
    database = Database(tmp_path / "status.sqlite3")
    await database.connect()
    yield database
    await database.close()


def test_status_needs_a_session(bot):
    response = client_for(bot).get("/api/status")
    assert response.status_code == 401
    assert response.json()["error"] == "not_signed_in"


def test_status_refuses_a_signed_in_non_staff_visitor_with_a_sentence(bot, sign_in):
    client = client_for(bot)
    sign_in(client, uid=1234, staff=False)
    response = client.get("/api/status")
    assert response.status_code == 403
    assert response.json()["error"] == "not_staff"
    assert "Ask a Lead" in response.json()["message"]


def test_status_reports_the_bot_and_every_feature_mode(bot, sign_in, fakes):
    bot.store.values = {"golive_mode": "shadow", "honeypot_mode": "on"}
    client = client_for(bot)
    sign_in(client)
    body = client.get("/api/status").json()
    assert body["bot"]["ready"] is True
    assert body["bot"]["latency_ms"] == 42
    assert body["bot"]["guilds"] == 1
    assert body["bot"]["uptime_seconds"] >= 0
    assert body["bot"]["version"]
    assert body["guild"]["id"] == str(fakes.GUILD_ID)
    modes = {row["key"]: row["mode"] for row in body["features"]}
    assert set(modes) == {key for key in KEY_TYPES if key.endswith("_mode")}
    assert modes["golive_mode"] == "shadow"


def test_every_mode_key_in_the_registry_is_reported():
    assert mode_keys() == [
        "golive_mode",
        "tempvoice_mode",
        "honeypot_mode",
        "events_mode",
    ]


def test_status_leaves_the_counts_blank_rather_than_claiming_zero(bot, sign_in):
    client = client_for(bot)
    sign_in(client)
    body = client.get("/api/status").json()
    assert body["open"] is None
    assert "left blank rather than shown as zero" in body["notes"][0]


async def test_open_counts_read_the_real_tables(bot, db, fakes):
    guild_id = fakes.GUILD_ID
    now = datetime.now(UTC)
    await db.conn.execute(
        "INSERT INTO role_menus(guild_id, name, title, message_id) VALUES (?, 'a', 'A', 5)",
        (guild_id,),
    )
    await db.conn.execute(
        "INSERT INTO role_menus(guild_id, name, title, message_id) VALUES (?, 'b', 'B', NULL)",
        (guild_id,),
    )
    await db.conn.execute(
        "INSERT INTO tempvoice_channels(channel_id, guild_id, owner_id, creator_id, created_at) "
        "VALUES (1, ?, 2, 3, ?)",
        (guild_id, now.isoformat()),
    )
    for age_days, in ((1,), (30,)):
        await db.conn.execute(
            "INSERT INTO honeypot_hits(guild_id, user_id, channel_id, at, mode, action) "
            "VALUES (?, 1, 2, ?, 'on', 'banned')",
            (guild_id, (now - timedelta(days=age_days)).isoformat()),
        )
    for status in ("pending", "approved", "denied"):
        await db.conn.execute(
            "INSERT INTO events(guild_id, requester_id, title, starts_at, status, created_at) "
            "VALUES (?, 1, 't', ?, ?, ?)",
            (guild_id, now.isoformat(), status, now.isoformat()),
        )
    await db.conn.commit()

    bot.db = db
    counts = await open_counts(bot, guild_id)
    assert counts == {
        "role_menus_posted": 1,
        "temp_channels": 1,
        "honeypot_hits_7d": 1,
        "open_events": 2,
    }


async def test_actions_returns_the_last_rows_newest_first(bot, db, sign_in, fakes):
    for n in range(3):
        await db.conn.execute(
            "INSERT INTO action_log(guild_id, at, kind, actor_id, reason, details) "
            "VALUES (?, ?, ?, 9, 'because', ?)",
            (fakes.GUILD_ID, f"2026-08-2{n}T00:00:00+00:00", f"kind.{n}", json.dumps({"n": n})),
        )
    await db.conn.commit()
    bot.db = db

    client = client_for(bot)
    sign_in(client)
    body = client.get("/api/actions", params={"limit": 2}).json()
    assert [row["kind"] for row in body["actions"]] == ["kind.2", "kind.1"]
    assert body["actions"][0]["actor_id"] == "9"
    assert body["limit"] == 2


async def test_actions_withholds_details_unless_they_are_asked_for(bot, db, sign_in, fakes):
    """F13: the blob can hold anything a feature put in it; the page never shows it."""
    await db.conn.execute(
        "INSERT INTO action_log(guild_id, at, kind, actor_id, reason, details) "
        "VALUES (?, '2026-08-26T00:00:00+00:00', 'k', 9, 'because', ?)",
        (fakes.GUILD_ID, json.dumps({"secretish": "value"})),
    )
    await db.conn.commit()
    bot.db = db

    client = client_for(bot)
    sign_in(client)
    assert "details" not in client.get("/api/actions").json()["actions"][0]
    asked = client.get("/api/actions", params={"details": 1}).json()
    assert asked["actions"][0]["details"] == {"secretish": "value"}


def test_a_malformed_query_string_is_a_sentence(bot, sign_in):
    """F11: FastAPI's own `detail` list is not something a person can read."""
    client = client_for(bot)
    sign_in(client)
    response = client.get("/api/actions", params={"limit": "all of them"})
    assert response.status_code == 400
    body = response.json()
    assert set(body) == {"error", "message"}
    assert body["error"] == "bad_request"
    assert body["message"].endswith(".")


async def test_actions_clamps_a_silly_limit(bot, db, sign_in):
    bot.db = db
    client = client_for(bot)
    sign_in(client)
    assert client.get("/api/actions", params={"limit": 100000}).json()["limit"] == 200
    assert client.get("/api/actions", params={"limit": 0}).json()["limit"] == 1


def test_actions_says_the_database_is_unreachable_rather_than_returning_nothing(bot, sign_in):
    """F12: the API's own read-shaped sentence, not the slash commands' write-shaped one."""
    client = client_for(bot)
    sign_in(client)
    response = client.get("/api/actions")
    assert response.status_code == 503
    assert response.json()["error"] == "database_unavailable"
    assert response.json()["message"] == DB_UNREACHABLE
    assert "nothing was changed" not in response.json()["message"]
    assert response.json()["message"] != DB_UNAVAILABLE


def test_loop_health_reports_running_and_the_health_a_cog_records(bot):
    ok_at = datetime(2026, 8, 26, 11, 0, tzinfo=UTC)
    bot.cogs = {
        "GoLive": FakeCog(FakeLoop("poller", last_ok_at=ok_at)),
        "Events": FakeCog(
            FakeLoop("_golive_loop", running=False, failed=True, last_error="boom"),
            FakeLoop("_reconcile_loop"),
        ),
    }
    rows = {row["name"]: row for row in loop_health(bot)}
    assert rows["poller"]["state"] == "ok"
    assert rows["poller"]["last_ok_at"] == ok_at.isoformat()
    assert rows["poller"]["last_error"] is None
    assert rows["_golive_loop"]["state"] == "danger"
    assert rows["_golive_loop"]["last_error"] == "boom"
    assert rows["_reconcile_loop"]["cog"] == "Events"


def test_loop_health_ignores_a_cog_with_no_loops(bot):
    bot.cogs = {"Core": object()}
    assert loop_health(bot) == []


def test_no_guild_is_staff_unknown_rather_than_a_report_on_nothing(api_settings, sign_in, fakes):
    """F2: with no guild the staff question has no answer, so the gate says so first."""
    client = client_for(fakes.Bot(api_settings, None))
    sign_in(client)
    response = client.get("/api/status")
    assert response.status_code == 503
    assert response.json()["error"] == "staff_unknown"


def test_status_says_so_when_the_guild_goes_away_mid_request(bot, guild, sign_in):
    client = client_for(bot)
    sign_in(client)
    once = iter([guild])
    bot.get_guild, bot.guilds = (lambda _id: next(once, None)), []
    body = client.get("/api/status").json()
    assert body["guild"] is None
    assert body["features"] == []
    assert "not in a server it can report on yet" in body["notes"][0]


def test_status_reports_no_latency_when_the_gateway_has_not_measured_one(bot, sign_in):
    """F3: round(nan) raises, and a status page must not 500 on a missing figure."""
    client = client_for(bot)
    sign_in(client)
    bot.latency = float("nan")
    assert client.get("/api/status").json()["bot"]["latency_ms"] is None
    bot.latency = float("inf")
    assert client.get("/api/status").json()["bot"]["latency_ms"] is None
