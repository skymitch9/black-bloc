from __future__ import annotations

from datetime import timedelta

import discord
import pytest

from black_bloc.modcases import add_case, get_case

ROUTES = [
    ("GET", "/api/mod/cases", None),
    ("GET", "/api/mod/cases/1", None),
    ("POST", "/api/mod/cases/1/apply", None),
    ("POST", "/api/mod/warn", {"user_id": "21", "reason": "no"}),
    ("POST", "/api/mod/timeout", {"user_id": "21", "duration": "10m"}),
    ("POST", "/api/mod/untimeout", {"user_id": "21"}),
    ("POST", "/api/mod/kick", {"user_id": "21"}),
    ("POST", "/api/mod/ban", {"user_id": "21"}),
    ("POST", "/api/mod/unban", {"user_id": "21"}),
    ("GET", "/api/mod/rules", None),
    ("PUT", "/api/mod/rules/caps", {"enabled": True}),
]

PUNISHMENTS = ["timeout", "untimeout", "kick", "ban", "unban"]


class _Response:
    def __init__(self, status: int) -> None:
        self.status = status
        self.reason = "refused"


def refused() -> discord.HTTPException:
    return discord.HTTPException(_Response(403), "no")


@pytest.mark.parametrize(("method", "route", "payload"), ROUTES)
def test_every_mod_route_needs_a_session(client, method, route, payload):
    assert client.request(method, route, json=payload).status_code == 401


@pytest.mark.parametrize(("method", "route", "payload"), ROUTES)
def test_every_mod_route_refuses_a_non_staff_visitor(client, sign_in, method, route, payload):
    sign_in(client, uid=1234, staff=False)
    assert client.request(method, route, json=payload).status_code == 403


async def test_cases_paginate_and_resolve_both_names(client, sign_in, web, guild, wf):
    wf.member(guild, 21, name="spammer")
    wf.member(guild, 7, name="lead", staff=True)
    for n in range(12):
        await add_case(web.db, wf.GUILD_ID, 21, "warn", moderator_id=7, reason=f"number {n}")
    sign_in(client)

    first = client.get("/api/mod/cases").json()
    second = client.get("/api/mod/cases", params={"page": 2}).json()

    assert (first["total"], first["pages"], first["page"]) == (12, 2, 1)
    assert len(first["cases"]) == 10 and len(second["cases"]) == 2
    assert first["cases"][0]["user_name"] == "Spammer"
    assert first["cases"][0]["moderator_name"] == "Lead"
    assert first["cases"][0]["applied"] is True


async def test_cases_can_be_filtered_by_member(client, sign_in, web, wf):
    await add_case(web.db, wf.GUILD_ID, 21, "warn")
    await add_case(web.db, wf.GUILD_ID, 22, "warn")
    sign_in(client)

    body = client.get("/api/mod/cases", params={"user_id": "22"}).json()

    assert body["total"] == 1
    assert body["cases"][0]["user_id"] == "22"
    assert client.get("/api/mod/cases", params={"user_id": "nobody"}).status_code == 400


async def test_one_case_comes_back_whole(client, sign_in, web, wf):
    case_id = await add_case(
        web.db, wf.GUILD_ID, 21, "automod", reason="5 mentions in 30s", actions=["warn", "timeout"]
    )
    sign_in(client)

    body = client.get(f"/api/mod/cases/{case_id}").json()

    assert body["kind"] == "automod"
    assert body["actions"] == ["warn", "timeout"]
    assert client.get("/api/mod/cases/4242").status_code == 404


async def test_warn_works_in_test_mode_because_it_only_tells_them(
    client, sign_in, web, guild, wf
):
    member = wf.member(guild, 21, name="spammer")
    web.guard = wf.Guard()
    sign_in(client)

    response = client.post("/api/mod/warn", json={"user_id": "21", "reason": "settle down"})

    assert response.status_code == 200
    assert "Warned" in response.json()["message"]
    assert member.dms
    kinds = await wf.kinds_in(web.db)
    assert "mod.warned" in kinds and "web.mod.warn" in kinds


@pytest.mark.parametrize("kind", PUNISHMENTS)
async def test_every_destructive_route_is_409_while_the_guard_is_on(
    client, sign_in, web, guild, wf, kind
):
    member = wf.member(guild, 21, name="spammer")
    web.guard = wf.Guard()
    sign_in(client)

    response = client.post(
        f"/api/mod/{kind}", json={"user_id": "21", "reason": "x", "duration": "10m"}
    )

    assert response.status_code == 409
    assert response.json()["error"] == "test_mode"
    assert "test mode" in response.json()["message"]
    assert (guild.bans, guild.kicks, guild.unbans, member.timeouts) == ([], [], [], [])
    kinds = await wf.kinds_in(web.db)
    assert f"mod.would_{kind}" in kinds
    assert not [row for row in kinds if row.startswith("web.mod.")]


async def test_a_timeout_times_them_out_and_records_a_case(client, sign_in, web, guild, wf):
    member = wf.member(guild, 21, name="spammer")
    sign_in(client)

    response = client.post(
        "/api/mod/timeout", json={"user_id": "21", "duration": "10m", "reason": "spam"}
    )

    assert response.status_code == 200
    assert member.timeouts[0][0] == timedelta(seconds=600)
    assert "Timed" in response.json()["message"]
    kinds = await wf.kinds_in(web.db)
    assert "mod.timed_out" in kinds and "web.mod.timeout" in kinds


def test_a_duration_nobody_can_read_is_refused(client, sign_in, guild, wf):
    wf.member(guild, 21, name="spammer")
    sign_in(client)

    bad = client.post("/api/mod/timeout", json={"user_id": "21", "duration": "ages"})
    long = client.post("/api/mod/timeout", json={"user_id": "21", "duration": "40d"})

    assert bad.status_code == 400 and bad.json()["error"] == "bad_duration"
    assert long.status_code == 400 and "28 days" in long.json()["message"]


def test_punishing_somebody_who_is_not_here_says_so(client, sign_in):
    sign_in(client)
    response = client.post("/api/mod/kick", json={"user_id": "999999"})
    assert response.status_code == 404
    assert response.json()["error"] == "not_a_member"


async def test_a_ban_and_an_unban_go_through_the_guild(client, sign_in, web, guild, wf):
    wf.member(guild, 21, name="spammer")
    sign_in(client)

    banned = client.post("/api/mod/ban", json={"user_id": "21", "purge_days": 2})
    unbanned = client.post("/api/mod/unban", json={"user_id": "21"})

    assert banned.status_code == 200 and guild.bans[0][2] == 2 * 86400
    assert unbanned.status_code == 200 and guild.unbans[0][0] == 21
    kinds = await wf.kinds_in(web.db)
    assert "mod.banned" in kinds and "mod.unbanned" in kinds


async def test_a_kick_discord_refuses_is_not_reported_as_done(client, sign_in, web, guild, wf):
    wf.member(guild, 21, name="spammer")

    async def refuse(*_args, **_kwargs):
        raise refused()

    guild.kick = refuse
    sign_in(client)

    response = client.post("/api/mod/kick", json={"user_id": "21"})

    assert response.status_code == 502
    assert response.json()["error"] == "discord_refused"
    assert "Kick Members" in response.json()["message"]
    assert "mod.kick_failed" in await wf.kinds_in(web.db)


async def test_apply_now_carries_out_a_shadow_verdict(client, sign_in, web, guild, wf):
    member = wf.member(guild, 21, name="spammer")
    case_id = await add_case(
        web.db,
        wf.GUILD_ID,
        21,
        "automod",
        reason="5 mentions in 30s",
        duration_s=300,
        mode="shadow",
        applied=False,
        actions=["warn", "timeout"],
    )
    sign_in(client)

    response = client.post(f"/api/mod/cases/{case_id}/apply")

    assert response.status_code == 200
    assert member.timeouts and member.timeouts[0][0] == timedelta(seconds=300)
    assert (await get_case(web.db, case_id))["applied"] == 1
    kinds = await wf.kinds_in(web.db)
    assert "automod.timed_out" in kinds and "web.mod.apply" in kinds


async def test_apply_now_is_refused_in_test_mode_and_when_it_is_done(
    client, sign_in, web, guild, wf
):
    wf.member(guild, 21, name="spammer")
    case_id = await add_case(
        web.db, wf.GUILD_ID, 21, "automod", duration_s=300, mode="shadow", applied=False,
        actions=["timeout"],
    )
    web.guard = wf.Guard()
    sign_in(client)

    guarded = client.post(f"/api/mod/cases/{case_id}/apply")

    assert guarded.status_code == 409 and guarded.json()["error"] == "test_mode"
    assert (await get_case(web.db, case_id))["applied"] == 0
    assert "automod.would_timeout" in await wf.kinds_in(web.db)

    web.guard = None
    client.post(f"/api/mod/cases/{case_id}/apply")
    again = client.post(f"/api/mod/cases/{case_id}/apply")
    assert again.status_code == 409 and again.json()["error"] == "already_applied"


async def test_a_case_this_server_does_not_have_cannot_be_applied(client, sign_in):
    sign_in(client)
    assert client.post("/api/mod/cases/4242/apply").status_code == 404


def test_the_rule_book_comes_back_with_help_for_every_rule(client, sign_in):
    sign_in(client)

    rules = {row["name"]: row for row in client.get("/api/mod/rules").json()}

    assert set(rules) >= {"mention_spam", "caps", "bad_words"}
    assert rules["mention_spam"]["threshold"] == 5
    assert rules["mention_spam"]["actions"] == ["delete", "warn", "timeout"]
    assert rules["caps"]["help"]
    assert rules["bad_words"]["words"] == []


async def test_a_rule_change_is_stored_and_logged(client, sign_in, web, wf):
    sign_in(client)

    response = client.put(
        "/api/mod/rules/caps", json={"enabled": True, "threshold": 80, "actions": ["delete"]}
    )

    assert response.status_code == 200
    assert (response.json()["enabled"], response.json()["threshold"]) == (True, 80)
    stored = web.store.get(wf.GUILD_ID, "automod_rules")["caps"]
    assert stored["threshold"] == 80 and stored["actions"] == ["delete"]
    kinds = await wf.kinds_in(web.db)
    assert "automod.rule" in kinds and "web.mod.rule" in kinds


def test_a_rule_out_of_range_is_refused_with_the_validators_sentence(client, sign_in):
    sign_in(client)

    bad_number = client.put("/api/mod/rules/caps", json={"threshold": 900})
    bad_action = client.put("/api/mod/rules/caps", json={"actions": ["explode"]})
    unknown = client.put("/api/mod/rules/nonsense", json={"enabled": True})

    assert bad_number.status_code == 400 and "between 1 and 100" in bad_number.json()["message"]
    assert bad_action.status_code == 400 and "punishment" in bad_action.json()["message"]
    assert unknown.status_code == 400 and "nonsense" in unknown.json()["message"]


@pytest.mark.parametrize("given", ["seven", "3.5", "-1", "8", True, {"days": 1}])
async def test_purge_days_nobody_can_read_is_a_sentence_and_nobody_is_banned(
    client, sign_in, web, guild, wf, given
):
    """It was int(payload.get(...)) — a word there was a 500, and a 500 is a bare status."""
    wf.member(guild, 21, name="spammer")
    sign_in(client)

    response = client.post("/api/mod/ban", json={"user_id": "21", "purge_days": given})

    assert response.status_code == 400
    assert response.json()["error"] == "bad_purge_days"
    assert "0 to 7" in response.json()["message"]
    assert guild.bans == []
    assert await wf.kinds_in(web.db) == []


@pytest.mark.parametrize(("given", "seconds"), [(None, 0), ("", 0), (0, 0), ("7", 7 * 86400)])
async def test_purge_days_takes_the_numbers_discord_takes(
    client, sign_in, guild, wf, given, seconds
):
    wf.member(guild, 21, name="spammer")
    sign_in(client)

    body = {"user_id": "21"} if given is None else {"user_id": "21", "purge_days": given}
    assert client.post("/api/mod/ban", json=body).status_code == 200
    assert guild.bans[0][2] == seconds
