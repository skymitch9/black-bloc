from __future__ import annotations

import time

import pytest

from black_bloc.api.auth import Refused
from black_bloc.api.writes import (
    MEMBER_RATE,
    READ_RATE,
    WRITE_RATE,
    WebActor,
    actor_for,
    bucket_for,
    guard_of,
    member_bucket_for,
    member_dependency,
    note,
    read_bucket_for,
    refuse_guarded,
    require_cog,
    require_db,
    require_guild,
    wanted_id,
)


def test_one_bucket_per_bot_so_the_limit_is_per_session_not_per_router(web):
    assert bucket_for(web) is bucket_for(web)
    assert bucket_for(web).limit == WRITE_RATE


def test_require_guild_says_it_is_a_setup_step_not_a_permission_problem(web):
    assert require_guild(web) is web.guild
    web.guild, web.guilds = None, []
    with pytest.raises(Refused) as raised:
        require_guild(web)
    assert raised.value.status == 503
    assert "not a fault with your access" in raised.value.message


def test_require_db_uses_the_read_shaped_database_sentence(web, wf):
    assert require_db(web) is web.db
    web.db = wf.Bot(web.settings, web.guild, None, web.store).db
    with pytest.raises(Refused) as raised:
        require_db(web)
    assert raised.value.status == 503
    assert raised.value.error == "database_unavailable"


def test_require_cog_names_the_feature_rather_than_showing_a_status(web):
    with pytest.raises(Refused) as raised:
        require_cog(web, "Modmail", "modmail")
    assert raised.value.status == 503
    assert "modmail" in raised.value.message
    web.cogs["Modmail"] = object()
    assert require_cog(web, "Modmail", "modmail") is web.cogs["Modmail"]


def test_a_guarded_refusal_is_409_and_the_slash_commands_own_sentence():
    with pytest.raises(Refused) as raised:
        refuse_guarded("Black Bloc is in **test mode**.")
    assert raised.value.status == 409
    assert raised.value.error == "test_mode"
    assert raised.value.message == "Black Bloc is in **test mode**."


def test_wanted_id_reads_a_mention_and_refuses_a_word():
    assert wanted_id("<@!7>") == 7
    assert wanted_id(" 42 ") == 42
    with pytest.raises(Refused) as raised:
        wanted_id("nobody")
    assert raised.value.status == 400
    assert "nobody" in raised.value.message


def test_the_actor_is_the_cached_member_when_discord_knows_them(web, guild, wf):
    known = wf.member(guild, 7, name="lead", staff=True)
    assert actor_for(web, {"id": "7", "name": "Lead"}) is known

    stranger = actor_for(web, {"id": "8", "name": "Someone"})
    assert isinstance(stranger, WebActor)
    assert (stranger.id, stranger.display_name, stranger.mention) == (8, "Someone", "<@8>")
    assert getattr(stranger, "send", None) is None


def test_guard_of_is_none_until_test_mode_installs_one(web, wf):
    assert guard_of(web) is None
    web.guard = wf.Guard()
    assert guard_of(web) is not None


async def test_note_writes_one_web_line_with_the_session_as_the_actor(web, wf):
    await note(web, web.guild, "web.settings.set", {"id": "7", "name": "Lead"}, target=9)

    cur = await web.db.conn.execute("SELECT kind, actor_id, target_id FROM action_log")
    row = await cur.fetchone()
    assert (row["kind"], row["actor_id"], row["target_id"]) == ("web.settings.set", 7, 9)
    assert await wf.kinds_in(web.db) == ["web.settings.set"]


def test_reads_and_writes_have_separate_buckets(web):
    assert read_bucket_for(web) is read_bucket_for(web)
    assert read_bucket_for(web) is not bucket_for(web)
    assert read_bucket_for(web).limit == READ_RATE


def drain_reads(web, uid: str = "7") -> None:
    """Drained against a clock a minute ahead, so the real request that follows finds no refill."""
    bucket = read_bucket_for(web)
    ahead = time.time() + 60
    for _ in range(READ_RATE):
        bucket.take(uid, now=ahead)


@pytest.mark.parametrize(
    "route", ["/api/ref/roles", "/api/ref/channels", "/api/actions", "/api/mod/cases"]
)
def test_a_read_flood_is_a_sentence_not_a_bare_429(client, sign_in, web, route):
    """One bucket per session across all four, so a loop on any of them is bounded."""
    sign_in(client)
    assert client.get(route).status_code == 200
    drain_reads(web)

    refused = client.get(route)

    assert refused.status_code == 429
    assert refused.json()["error"] == "slow_down"
    assert "wait a minute" in refused.json()["message"]


def test_the_read_limit_does_not_spend_the_write_allowance(client, sign_in, web):
    sign_in(client)
    drain_reads(web)

    assert client.get("/api/ref/roles").status_code == 429
    assert client.post("/api/rolemenus", json={"name": "c", "title": "C"}).status_code == 200


def test_another_session_is_not_slowed_down_by_this_ones_reads(client, sign_in, web):
    sign_in(client)
    drain_reads(web)
    assert client.get("/api/ref/roles").status_code == 429

    sign_in(client, uid=8)
    assert client.get("/api/ref/roles").status_code == 200


def test_the_member_bucket_is_its_own_and_far_smaller_than_the_staff_one(web):
    assert member_bucket_for(web) is member_bucket_for(web)
    assert member_bucket_for(web).limit == MEMBER_RATE
    assert MEMBER_RATE < WRITE_RATE
    assert member_bucket_for(web) is not bucket_for(web)


async def test_the_member_gate_takes_a_member_and_refuses_a_stranger(client, sign_in, web, wf):
    gate = member_dependency(web)
    wf.member(web.guild, 21, name="ada")
    sign_in(client, uid=21, staff=False)

    class _Ask:
        cookies = dict(client.cookies)

    who = await gate(_Ask())

    assert who["id"] == "21" and who["staff"] is False and who["member"] is True

    sign_in(client, uid=22, staff=False, cached=False)
    _Ask.cookies = dict(client.cookies)
    with pytest.raises(Refused) as raised:
        await gate(_Ask())

    assert raised.value.status == 403 and raised.value.error == "not_a_member"
    assert "Join the server" in raised.value.message


async def test_the_member_gate_says_it_could_not_check_rather_than_refusing_access(
    client, sign_in, web, wf
):
    wf.member(web.guild, 21, name="ada")
    sign_in(client, uid=21, staff=False)
    web.guild, web.guilds = None, []
    gate = member_dependency(web)

    class _Ask:
        cookies = dict(client.cookies)

    with pytest.raises(Refused) as raised:
        await gate(_Ask())

    assert raised.value.status == 503 and raised.value.error == "member_unknown"
    assert "try again in a minute" in raised.value.message
