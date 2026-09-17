from __future__ import annotations

import importlib
import json
from datetime import UTC, datetime, timedelta

import pytest
from discord.ext import tasks
from discord.utils import MISSING
from fastapi.testclient import TestClient

from black_bloc.api.server import create_app
from black_bloc.api.status import (
    DB_UNREACHABLE,
    NOT_A_FEATURE,
    loop_health,
    mode_keys,
    open_counts,
)
from black_bloc.settings_store import DB_UNAVAILABLE, KEY_TYPES


def _named(name: str):
    async def coro():
        return None

    coro.__name__ = name
    return coro


class FakeLoop(tasks.Loop):
    """A real `tasks.Loop`, because the page finds loops by type now, not by asking the cog."""

    _running = False
    _broke = False

    def __init__(self, name: str, *, running: bool = True, failed: bool = False) -> None:
        super().__init__(
            _named(name),
            seconds=60,
            hours=MISSING,
            minutes=MISSING,
            time=MISSING,
            count=None,
            reconnect=True,
            name=None,
        )
        self._running = running
        self._broke = failed

    def is_running(self) -> bool:
        return self._running

    def failed(self) -> bool:
        return self._broke

    @property
    def next_iteration(self):
        return datetime(2026, 8, 26, 12, 0, tzinfo=UTC)


class FakeCog:
    def __init__(self, *loops, health: dict | None = None) -> None:
        for loop in loops:
            setattr(self, loop.coro.__name__, loop)
        self._health = health or {}

    def loop_health(self, name: str):
        return self._health.get(name, (None, None))


class SilentCog(FakeCog):
    """A cog that records no loop health at all — TempVoice is one today."""

    loop_health = None


def client_for(bot) -> TestClient:
    return TestClient(create_app(bot), base_url="https://testserver")


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
    assert set(modes) == set(mode_keys())
    assert modes["golive_mode"] == "shadow"


def test_every_mode_key_in_the_registry_is_reported():
    assert mode_keys() == [
        key for key in KEY_TYPES if key.endswith("_mode") and key not in NOT_A_FEATURE
    ]
    assert set(mode_keys()) >= {
        "golive_mode",
        "tempvoice_mode",
        "honeypot_mode",
        "events_mode",
        "birthday_mode",
        "modmail_mode",
        "automod_mode",
        "rolemenu_mode",
        "poll_mode",
    }


def test_the_go_live_end_switch_is_not_offered_as_a_feature_of_its_own():
    assert "golive_end_mode" in KEY_TYPES
    assert "golive_end_mode" not in mode_keys()


def test_the_poll_review_switch_is_not_a_feature_but_polls_themselves_are():
    assert "poll_review_mode" in KEY_TYPES
    assert "poll_review_mode" not in mode_keys()
    assert "poll_mode" in mode_keys()


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
    for ticket_status in ("open", "closed"):
        await db.conn.execute(
            "INSERT INTO modmail_tickets"
            "(guild_id, user_id, mode, channel_id, status, opened_at) "
            "VALUES (?, 1, 'channel', 2, ?, ?)",
            (guild_id, ticket_status, now.isoformat()),
        )
    await db.conn.commit()

    bot.db = db
    counts = await open_counts(bot, guild_id)
    assert counts == {
        "role_menus_posted": 1,
        "temp_channels": 1,
        "honeypot_hits_7d": 1,
        "open_events": 2,
        "open_modmail": 1,
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
        "GoLive": FakeCog(FakeLoop("poller"), health={"poller": (ok_at, None)}),
        "Events": FakeCog(
            FakeLoop("_golive_loop", running=False, failed=True),
            FakeLoop("_reconcile_loop"),
            health={"_golive_loop": (None, "boom")},
        ),
    }
    rows = {row["name"]: row for row in loop_health(bot)}
    assert rows["poller"]["state"] == "ok"
    assert rows["poller"]["last_ok_at"] == ok_at.isoformat()
    assert rows["poller"]["last_error"] is None
    assert rows["_golive_loop"]["state"] == "danger"
    assert rows["_golive_loop"]["last_error"] == "boom"
    assert rows["_reconcile_loop"]["cog"] == "Events"


def test_loop_health_is_blank_for_a_cog_that_records_none(bot):
    bot.cogs = {"TempVoice": SilentCog(FakeLoop("_reconcile_loop"))}
    row = loop_health(bot)[0]
    assert (row["last_ok_at"], row["last_error"]) == (None, None)
    assert row["running"] is True


def test_loop_health_ignores_a_cog_with_no_loops(bot):
    bot.cogs = {"Core": object()}
    assert loop_health(bot) == []


OK_AT = "2026-08-26T00:00:00+00:00"


def _record(attr):
    def set_on(cog, value):
        setattr(cog, attr, value)

    return set_on


def _record_key(attr, key):
    def set_on(cog, value):
        getattr(cog, attr)[key] = value

    return set_on


REAL_COGS = [
    ("black_bloc.cogs.presence", "Presence", {"status": _record("last_ok_at")}),
    ("black_bloc.cogs.content.golive", "GoLive", {"poller": _record("last_poll_ok_at")}),
    (
        "black_bloc.cogs.content.youtube",
        "YouTube",
        {"poller": _record("last_poll_ok_at"), "live_poller": _record("last_probe_at")},
    ),
    ("black_bloc.cogs.content.raidtrain", "RaidTrains", {"sweep": _record("last_sweep_ok_at")}),
    (
        "black_bloc.cogs.community.birthdays",
        "Birthdays",
        {"_sweep": _record("last_run_at"), "_import_loop": _record("last_import_at")},
    ),
    (
        "black_bloc.cogs.community.events",
        "Events",
        {
            "_golive_loop": _record_key("last_ok_at", "golive"),
            "_reconcile_loop": _record_key("last_ok_at", "reconcile"),
        },
    ),
    (
        "black_bloc.cogs.community.role_menus",
        "RoleMenus",
        {"_expiry_loop": _record_key("last_ok_at", "expiry")},
    ),
    (
        "black_bloc.cogs.community.tempvoice",
        "TempVoice",
        {"_reconcile_loop": _record("last_ok_at")},
    ),
    (
        "black_bloc.cogs.moderation.modmail",
        "Modmail",
        {"_reconcile_loop": _record("last_ok_at")},
    ),
]


@pytest.mark.parametrize(
    ("module", "cog", "recorders"), REAL_COGS, ids=[row[1] for row in REAL_COGS]
)
def test_every_loop_a_real_cog_owns_reaches_the_health_tab(bot, sign_in, module, cog, recorders):
    """Discovery finds them by type; the health beside each one is the cog's own record of it."""
    cls = getattr(importlib.import_module(module), cog)
    instance = cls(bot)
    bot.cogs = {cog: instance}
    for name, record_ok in recorders.items():
        assert instance.loop_health(name) == (None, None)
        assert instance.loop_health("not_a_loop_here") == (None, None)
        record_ok(instance, OK_AT)

    client = client_for(bot)
    sign_in(client)
    rows = {row["name"]: row for row in client.get("/api/status").json()["loops"]}

    assert set(rows) == set(recorders)
    for name, row in rows.items():
        assert row["cog"] == cog
        assert row["last_ok_at"] == OK_AT, name
        assert row["last_error"] is None
        assert row["running"] is False
        assert row["state"] == "danger"


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


async def _log(db, guild_id, kind, actor=None, target=None, at="2026-08-26T00:00:00+00:00"):
    await db.conn.execute(
        "INSERT INTO action_log(guild_id, at, kind, actor_id, target_id) VALUES (?, ?, ?, ?, ?)",
        (guild_id, at, kind, actor, target),
    )
    await db.conn.commit()


async def test_actions_carry_the_names_the_tables_show(bot, db, sign_in, guild, wf):
    wf.member(guild, 7, name="lead", staff=True)
    wf.member(guild, 21, name="spammer")
    await _log(db, wf.GUILD_ID, "web.mod.ban", actor=7, target=21)
    await _log(db, wf.GUILD_ID, "mod.warned", actor=7, target=999999)
    bot.db = db

    client = client_for(bot)
    sign_in(client)
    rows = client.get("/api/actions").json()["actions"]

    newest, older = rows
    assert newest["kind"] == "mod.warned" and newest["target_name"] is None
    assert older["actor_name"] == "Lead" and older["target_name"] == "Spammer"
    assert older["actor_id"] == "7"


async def test_actions_can_be_filtered_by_kind_and_by_member(bot, db, sign_in, guild, wf):
    await _log(db, wf.GUILD_ID, "web.mod.ban", actor=7, target=21)
    await _log(db, wf.GUILD_ID, "web.settings.set", actor=7)
    await _log(db, wf.GUILD_ID, "mod.warned", actor=8, target=22)
    bot.db = db

    client = client_for(bot)
    sign_in(client)

    web_only = client.get("/api/actions", params={"kind": "web"}).json()["actions"]
    one_kind = client.get("/api/actions", params={"kind": "web.mod.ban"}).json()["actions"]
    theirs = client.get("/api/actions", params={"user_id": "21"}).json()["actions"]

    assert {row["kind"] for row in web_only} == {"web.mod.ban", "web.settings.set"}
    assert [row["kind"] for row in one_kind] == ["web.mod.ban"]
    assert [row["kind"] for row in theirs] == ["web.mod.ban"]
    assert client.get("/api/actions", params={"user_id": "8"}).json()["actions"]


async def test_an_actions_filter_that_is_not_an_id_is_a_sentence(bot, db, sign_in):
    bot.db = db
    client = client_for(bot)
    sign_in(client)
    response = client.get("/api/actions", params={"user_id": "nobody"})
    assert response.status_code == 400
    assert set(response.json()) == {"error", "message"}
    assert "nobody" in response.json()["message"]


async def test_every_action_row_says_which_feature_it_is_and_whether_it_matters(
    bot, db, sign_in, wf
):
    await _log(db, wf.GUILD_ID, "web.role.granted", actor=7, target=21)
    await _log(db, wf.GUILD_ID, "poll.created", actor=7)
    bot.db = db

    client = client_for(bot)
    sign_in(client)
    rows = {row["kind"]: row for row in client.get("/api/actions").json()["actions"]}

    assert rows["web.role.granted"]["feature"] == "rolemenu"
    assert rows["web.role.granted"]["important"] is True
    assert rows["poll.created"]["feature"] == "poll"
    assert rows["poll.created"]["important"] is False


async def test_the_page_gets_the_kind_chips_without_a_second_request(bot, db, sign_in, wf):
    for kind in ("poll.created", "poll.created", "poll.closed", "mod.banned"):
        await _log(db, wf.GUILD_ID, kind)
    bot.db = db

    client = client_for(bot)
    sign_in(client)

    assert client.get("/api/actions").json()["kinds"] == [
        "mod.banned",
        "poll.closed",
        "poll.created",
    ]
    narrowed = client.get("/api/actions", params={"feature": "poll"}).json()
    assert narrowed["kinds"] == ["poll.closed", "poll.created"]


async def test_the_chips_are_what_this_guild_logged_not_the_page_it_asked_for(
    bot, db, sign_in, wf
):
    """`kinds` follows `feature` only — paging past the end must not empty the chips."""
    for n in range(4):
        await _log(db, wf.GUILD_ID, f"poll.k{n}", at=f"2026-08-2{n}T00:00:00+00:00")
    bot.db = db

    client = client_for(bot)
    sign_in(client)
    body = client.get("/api/actions", params={"per_page": 1, "page": 9, "q": "nothing"}).json()

    assert body["actions"] == []
    assert body["kinds"] == ["poll.k0", "poll.k1", "poll.k2", "poll.k3"]


async def test_every_row_carries_a_summary_even_when_details_are_withheld(bot, db, sign_in, wf):
    await db.conn.execute(
        "INSERT INTO action_log(guild_id, at, kind, reason, details) "
        "VALUES (?, '2026-08-26T00:00:00+00:00', 'poll.created', NULL, ?)",
        (wf.GUILD_ID, json.dumps({"poll_id": 3, "hours": 24})),
    )
    await _log(db, wf.GUILD_ID, "mod.banned", at="2026-08-27T00:00:00+00:00")
    await db.conn.execute(
        "UPDATE action_log SET reason = 'scam links' WHERE kind = 'mod.banned'"
    )
    await db.conn.commit()
    bot.db = db

    client = client_for(bot)
    sign_in(client)
    rows = {row["kind"]: row for row in client.get("/api/actions").json()["actions"]}

    assert "details" not in rows["poll.created"]
    assert rows["poll.created"]["summary"] == "poll_id=3, hours=24"
    assert rows["mod.banned"]["summary"] == "scam links"


async def test_actions_can_be_filtered_by_feature(bot, db, sign_in, wf):
    for kind in ("role.granted", "role_menu.update", "web.rolemenu.post", "poll.created"):
        await _log(db, wf.GUILD_ID, kind)
    bot.db = db

    client = client_for(bot)
    sign_in(client)
    body = client.get("/api/actions", params={"feature": "rolemenu"}).json()

    assert body["total"] == 3
    assert all(row["feature"] == "rolemenu" for row in body["actions"])


async def test_the_default_view_leaves_the_test_rows_out_and_the_test_filter_shows_only_them(
    bot, db, sign_in, wf
):
    """Owner, 2026-09-05: 'keep the logs on the website tho under test' — kept, and out of the
    way of the real ones. The chips follow, or the Logs page would offer a dead filter."""
    for kind in ("poll.created", "selftest.started", "selftest.check", "web.selftest.finished"):
        await _log(db, wf.GUILD_ID, kind)
    bot.db = db

    client = client_for(bot)
    sign_in(client)
    default = client.get("/api/actions").json()

    assert {row["kind"] for row in default["actions"]} == {"poll.created"}
    assert default["total"] == 1
    assert default["kinds"] == ["poll.created"]

    only_test = client.get("/api/actions", params={"feature": "selftest"}).json()

    assert {row["kind"] for row in only_test["actions"]} == {
        "selftest.started",
        "selftest.check",
        "web.selftest.finished",
    }
    assert all(row["feature"] == "selftest" for row in only_test["actions"])
    # Asking for the kind by name reaches them too, so a deep link is never a dead end.
    by_kind = client.get("/api/actions", params={"kind": "selftest."}).json()
    assert by_kind["total"] == 2


async def test_the_csv_export_leaves_the_test_rows_out_the_same_way_the_page_does(
    bot, db, sign_in, wf
):
    for kind in ("poll.created", "selftest.check"):
        await _log(db, wf.GUILD_ID, kind)
    bot.db = db

    client = client_for(bot)
    sign_in(client)
    body = client.get("/api/actions/export.csv").text

    assert "poll.created" in body
    assert "selftest.check" not in body
    assert "selftest.check" in client.get(
        "/api/actions/export.csv", params={"feature": "selftest"}
    ).text


async def test_a_feature_nobody_has_is_a_sentence_that_names_the_ones_there_are(bot, db, sign_in):
    bot.db = db
    client = client_for(bot)
    sign_in(client)
    response = client.get("/api/actions", params={"feature": "rolemenus"})
    assert response.status_code == 400
    assert "rolemenus" in response.json()["message"]
    assert "tempvoice" in response.json()["message"]


async def test_important_leaves_out_the_dry_runs(bot, db, sign_in, wf):
    for kind in ("mod.would_ban", "mod.banned", "mod.warned"):
        await _log(db, wf.GUILD_ID, kind)
    bot.db = db

    client = client_for(bot)
    sign_in(client)
    body = client.get("/api/actions", params={"important": 1}).json()

    assert {row["kind"] for row in body["actions"]} == {"mod.banned", "mod.warned"}
    assert body["total"] == 2


async def test_q_searches_the_kind_the_names_and_the_details(bot, db, sign_in, guild, wf):
    wf.member(guild, 21, name="spammer")
    await _log(db, wf.GUILD_ID, "mod.banned", actor=7, target=21)
    await db.conn.execute(
        "INSERT INTO action_log(guild_id, at, kind, reason, details) "
        "VALUES (?, '2026-08-26T00:00:00+00:00', 'poll.created', 'a question', ?)",
        (wf.GUILD_ID, json.dumps({"poll_id": 77})),
    )
    await db.conn.commit()
    bot.db = db

    client = client_for(bot)
    sign_in(client)
    hits = lambda text: {  # noqa: E731
        row["kind"] for row in client.get("/api/actions", params={"q": text}).json()["actions"]
    }

    assert hits("banned") == {"mod.banned"}
    assert hits("spamm") == {"mod.banned"}
    assert hits("poll_id") == {"poll.created"}
    assert hits("a question") == {"poll.created"}
    assert hits("nothing like that") == set()


async def test_since_and_until_read_a_bare_date_as_the_whole_day(bot, db, sign_in, wf):
    await _log(db, wf.GUILD_ID, "poll.created", at="2026-08-25T23:00:00+00:00")
    await _log(db, wf.GUILD_ID, "poll.closed", at="2026-08-26T18:00:00+00:00")
    await _log(db, wf.GUILD_ID, "poll.opened", at="2026-08-27T01:00:00+00:00")
    bot.db = db

    client = client_for(bot)
    sign_in(client)
    within = client.get(
        "/api/actions", params={"since": "2026-08-26", "until": "2026-08-26"}
    ).json()

    assert [row["kind"] for row in within["actions"]] == ["poll.closed"]
    after = client.get("/api/actions", params={"since": "2026-08-26T18:00:00Z"}).json()
    assert {row["kind"] for row in after["actions"]} == {"poll.closed", "poll.opened"}


async def test_a_date_nobody_can_read_is_a_sentence(bot, db, sign_in):
    bot.db = db
    client = client_for(bot)
    sign_in(client)
    response = client.get("/api/actions", params={"since": "last tuesday"})
    assert response.status_code == 400
    assert "last tuesday" in response.json()["message"]


async def test_paging_reports_the_whole_count_and_the_page_it_gave_back(bot, db, sign_in, wf):
    for n in range(7):
        await _log(db, wf.GUILD_ID, f"poll.k{n}", at=f"2026-08-2{n}T00:00:00+00:00")
    bot.db = db

    client = client_for(bot)
    sign_in(client)
    first = client.get("/api/actions", params={"per_page": 3, "page": 1}).json()
    last = client.get("/api/actions", params={"per_page": 3, "page": 3}).json()
    past_the_end = client.get("/api/actions", params={"per_page": 3, "page": 9}).json()

    assert (first["total"], first["shown"], first["per_page"]) == (7, 3, 3)
    assert [row["kind"] for row in first["actions"]] == ["poll.k6", "poll.k5", "poll.k4"]
    assert [row["kind"] for row in last["actions"]] == ["poll.k0"]
    assert (past_the_end["total"], past_the_end["shown"]) == (7, 0)
    assert past_the_end["actions"] == []


async def test_per_page_is_clamped_and_limit_still_works_for_the_old_pages(bot, db, sign_in):
    bot.db = db
    client = client_for(bot)
    sign_in(client)
    assert client.get("/api/actions", params={"per_page": 100000}).json()["per_page"] == 200
    assert client.get("/api/actions", params={"per_page": 0, "limit": 10}).json()["per_page"] == 10
    assert client.get("/api/actions", params={"page": -4}).json()["page"] == 1


async def test_the_export_is_csv_with_the_same_filters(bot, db, sign_in, guild, wf):
    wf.member(guild, 21, name="spammer")
    await _log(db, wf.GUILD_ID, "mod.banned", actor=7, target=21)
    await _log(db, wf.GUILD_ID, "poll.created")
    bot.db = db

    client = client_for(bot)
    sign_in(client)
    response = client.get("/api/actions/export.csv", params={"feature": "mod"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "black-bloc-log.csv" in response.headers["content-disposition"]
    lines = response.text.strip().splitlines()
    assert lines[0].startswith("id,at,kind,feature,important,")
    assert len(lines) == 2
    assert "mod.banned,mod,true" in lines[1]
    assert "Spammer" in lines[1]


async def test_the_export_refuses_the_same_way_the_list_does(bot, db, sign_in):
    bot.db = db
    client = client_for(bot)
    sign_in(client)
    assert client.get("/api/actions/export.csv", params={"feature": "nope"}).status_code == 400
    assert client.get("/api/actions/export.csv", params={"user_id": "x"}).status_code == 400


def test_the_export_needs_a_session_like_every_other_read(bot):
    client = client_for(bot)
    assert client.get("/api/actions/export.csv").status_code == 401
