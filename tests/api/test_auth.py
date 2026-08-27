from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from black_bloc.api.auth import (
    SESSION_COOKIE,
    STATE_COOKIE,
    is_admitted,
    read_session,
    role_ids_from,
    sign_session,
)
from black_bloc.api.server import create_app

USER_ID = 7


class FakeDiscord:
    """Stands in for Discord's OAuth endpoints; no socket is ever opened."""

    def __init__(self, *, member: dict | None, token_status: int = 200) -> None:
        self.member = member
        self.token_status = token_status
        self.calls: list[str] = []

    async def __call__(self, method, url, *, headers=None, data=None):
        self.calls.append(url)
        if url.endswith("/oauth2/token"):
            if self.token_status != 200:
                return (self.token_status, {"error": "invalid_grant"})
            return (200, {"access_token": "user-token", "token_type": "Bearer"})
        if url.endswith("/users/@me"):
            return (200, {"id": str(USER_ID), "username": "mod", "global_name": "Mod"})
        if url.endswith("/member"):
            if self.member is None:
                return (404, {"message": "Unknown Guild"})
            return (200, self.member)
        return (404, {})


def client_for(bot, discord: FakeDiscord | None = None) -> TestClient:
    return TestClient(
        create_app(bot, oauth_request=discord),
        follow_redirects=False,
        base_url="http://testserver",
    )


def start_login(client) -> str:
    from urllib.parse import parse_qs, urlparse

    response = client.get("/api/auth/login")
    return parse_qs(urlparse(response.headers["location"]).query)["state"][0]


def sign_in_through_discord(bot, member: dict | None):
    discord = FakeDiscord(member=member)
    client = client_for(bot, discord)
    state = start_login(client)
    return client, client.get("/api/auth/callback", params={"code": "abc", "state": state})


def test_login_redirects_to_discord_with_the_two_scopes(bot):
    from urllib.parse import parse_qs, urlparse

    response = client_for(bot).get("/api/auth/login")
    assert response.status_code == 303
    target = urlparse(response.headers["location"])
    query = parse_qs(target.query)
    assert target.netloc == "discord.com"
    assert query["scope"] == ["identify guilds.members.read"]
    assert query["redirect_uri"] == ["http://testserver/api/auth/callback"]
    assert query["response_type"] == ["code"]
    assert response.cookies.get(STATE_COOKIE)


def test_login_says_so_when_the_app_is_not_configured(bot):
    bot.settings.discord_client_secret = None
    response = client_for(bot).get("/api/auth/login")
    assert response.status_code == 503
    assert response.json()["error"] == "login_unavailable"
    assert "not switched on" in response.json()["message"]


def test_staff_member_is_admitted_and_gets_a_session(bot, guild, fakes):
    guild.members[USER_ID] = fakes.Member(
        USER_ID, [fakes.Role(fakes.STAFF_ROLE_ID, "Aunties / Uncles")]
    )
    client, done = sign_in_through_discord(bot, {"roles": [str(fakes.STAFF_ROLE_ID)]})
    assert done.status_code == 303
    assert done.headers["location"] == "https://blackbloc.heygabi.ai/?signin=ok"
    state, payload = read_session(fakes.SECRET, done.cookies[SESSION_COOKIE])
    assert state == "ok"
    assert payload["staff"] is True
    assert client.get("/api/auth/me").json()["staff"] is True


def test_manage_guild_is_admitted_without_a_staff_role(bot, guild, fakes):
    guild.members[USER_ID] = fakes.Member(
        USER_ID, [fakes.Role(fakes.ADMIN_ROLE_ID, "Admin")], manage_guild=True
    )
    _, done = sign_in_through_discord(bot, {"roles": [str(fakes.ADMIN_ROLE_ID)]})
    _, payload = read_session(fakes.SECRET, done.cookies[SESSION_COOKIE])
    assert payload["staff"] is True


def test_plain_member_is_signed_in_but_not_staff(bot, guild, fakes):
    guild.members[USER_ID] = fakes.Member(USER_ID, [fakes.Role(fakes.PLAIN_ROLE_ID, "Member")])
    client, done = sign_in_through_discord(bot, {"roles": [str(fakes.PLAIN_ROLE_ID)]})
    _, payload = read_session(fakes.SECRET, done.cookies[SESSION_COOKIE])
    assert payload["staff"] is False
    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["staff"] is False
    assert "does not hold a staff role" in me.json()["message"]


def test_someone_not_in_the_guild_is_signed_in_but_not_staff(bot, fakes):
    _, done = sign_in_through_discord(bot, None)
    _, payload = read_session(fakes.SECRET, done.cookies[SESSION_COOKIE])
    assert payload["staff"] is False


def test_a_bad_state_never_reaches_discord(bot):
    discord = FakeDiscord(member={"roles": []})
    client = client_for(bot, discord)
    start_login(client)
    done = client.get("/api/auth/callback", params={"code": "abc", "state": "a-forged-state"})
    assert done.headers["location"].endswith("?signin=state")
    assert SESSION_COOKIE not in done.cookies
    assert discord.calls == []


def test_discord_refusing_the_exchange_reads_as_a_failure_not_a_refusal(bot):
    discord = FakeDiscord(member={"roles": []}, token_status=400)
    client = client_for(bot, discord)
    state = start_login(client)
    done = client.get("/api/auth/callback", params={"code": "abc", "state": state})
    assert done.headers["location"].endswith("?signin=failed")
    assert SESSION_COOKIE not in done.cookies


def test_the_user_declining_at_discord_comes_back_denied(bot):
    done = client_for(bot).get("/api/auth/callback", params={"error": "access_denied"})
    assert done.headers["location"].endswith("?signin=denied")


def test_no_cookie_is_not_signed_in(bot):
    response = client_for(bot).get("/api/auth/me")
    assert response.status_code == 401
    assert response.json()["error"] == "not_signed_in"


def test_an_expired_cookie_says_expired_not_forbidden(bot, fakes):
    client = client_for(bot)
    client.cookies.set(
        SESSION_COOKIE,
        sign_session(fakes.SECRET, {"uid": "7", "staff": True, "exp": int(time.time()) - 1}),
    )
    response = client.get("/api/auth/me")
    assert response.status_code == 401
    assert response.json()["error"] == "session_expired"
    assert "expired" in response.json()["message"]


def test_a_forged_cookie_is_not_signed_in(bot):
    client = client_for(bot)
    client.cookies.set(
        SESSION_COOKIE,
        sign_session("some-other-secret", {"uid": "7", "staff": True, "exp": 4102444800}),
    )
    assert client.get("/api/auth/me").json()["error"] == "not_signed_in"


def test_logout_clears_the_cookie(bot, sign_in):
    client = client_for(bot)
    sign_in(client)
    response = client.post("/api/auth/logout")
    assert response.status_code == 200
    cleared = response.headers["set-cookie"]
    assert cleared.startswith(f'{SESSION_COOKIE}=""') or cleared.startswith(f"{SESSION_COOKIE}=;")
    assert "Max-Age=0" in cleared or "expires=Thu, 01 Jan 1970" in cleared


def test_a_demoted_mod_loses_access_without_signing_out(bot, guild, fakes, sign_in):
    guild.members[USER_ID] = fakes.Member(USER_ID, [fakes.Role(fakes.PLAIN_ROLE_ID, "Member")])
    client = client_for(bot)
    sign_in(client, uid=USER_ID, staff=True)
    assert client.get("/api/auth/me").json()["staff"] is False


@pytest.mark.parametrize("raw", ["", "no-dot", "body.deadbeef"])
def test_read_session_rejects_rubbish(raw, fakes):
    assert read_session(fakes.SECRET, raw) == ("invalid", None)


def test_read_session_rejects_a_payload_with_no_expiry(fakes):
    assert read_session(fakes.SECRET, sign_session(fakes.SECRET, {"uid": "7"})) == ("invalid", None)


def test_role_ids_from_ignores_unparseable_ids():
    assert role_ids_from({"roles": ["11", "not-a-number", 22]}) == {11, 22}


def test_is_admitted_falls_back_to_the_payload_roles_when_the_member_is_not_cached(
    bot, guild, fakes
):
    assert is_admitted(guild, bot.store, USER_ID, {fakes.STAFF_ROLE_ID}) is True
    assert is_admitted(guild, bot.store, USER_ID, {fakes.ADMIN_ROLE_ID}) is True
    assert is_admitted(guild, bot.store, USER_ID, {fakes.PLAIN_ROLE_ID}) is False
    assert is_admitted(guild, bot.store, guild.owner_id, set()) is True
    assert is_admitted(None, bot.store, USER_ID, {fakes.STAFF_ROLE_ID}) is False
