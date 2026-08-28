from __future__ import annotations

import time
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from black_bloc.api.auth import (
    BUCKET_MAX_KEYS,
    LOGIN_RATE,
    SESSION_COOKIE,
    STATE_COOKIE,
    Refused,
    TokenBucket,
    current_session,
    is_admitted,
    read_session,
    role_ids_from,
    sign_session,
)
from black_bloc.api.server import SAME_ORIGIN, SAME_SITE_HEADER, create_app

USER_ID = 7


class FakeDiscord:
    """Stands in for Discord's OAuth endpoints; no socket is ever opened."""

    def __init__(
        self, *, member: dict | None, token_status: int = 200, member_status: int = 200
    ) -> None:
        self.member = member
        self.token_status = token_status
        self.member_status = member_status
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
            if self.member_status != 200:
                return (self.member_status, {"message": "Internal Server Error"})
            if self.member is None:
                return (404, {"message": "Unknown Guild"})
            return (200, self.member)
        return (404, {})


def client_for(bot, discord: FakeDiscord | None = None) -> TestClient:
    return TestClient(
        create_app(bot, oauth_request=discord),
        follow_redirects=False,
        base_url="https://testserver",
        headers={SAME_SITE_HEADER: SAME_ORIGIN},
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
    assert query["redirect_uri"] == ["https://testserver/api/auth/callback"]
    assert query["response_type"] == ["code"]
    assert response.cookies.get(STATE_COOKIE)


def set_cookie(response, name: str) -> str:
    return next(h for h in response.headers.get_list("set-cookie") if h.startswith(f"{name}="))


def test_both_cookies_are_host_prefixed_secure_and_httponly(bot, guild, fakes):
    """__Host- is only honoured with Secure, Path=/ and no Domain (F8)."""
    guild.members[USER_ID] = fakes.Member(
        USER_ID, [fakes.Role(fakes.STAFF_ROLE_ID, "Aunties / Uncles")]
    )
    _, done = sign_in_through_discord(bot, {"roles": [str(fakes.STAFF_ROLE_ID)]})
    headers = [
        set_cookie(client_for(bot).get("/api/auth/login"), STATE_COOKIE),
        set_cookie(done, SESSION_COOKIE),
    ]
    assert STATE_COOKIE.startswith("__Host-") and SESSION_COOKIE.startswith("__Host-")
    for header in headers:
        assert "; Secure" in header
        assert "; HttpOnly" in header
        assert "; Path=/" in header
        assert "Domain=" not in header
        assert "SameSite=lax" in header


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
    assert done.headers["location"] == f"{fakes.ORIGIN}/?signin=ok"
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
    assert me.json()["member"] is True
    assert me.json()["state"] == "not_staff"
    assert "you can still file a request" in me.json()["message"]


def test_a_staffer_is_a_member_too_and_gets_no_message_at_all(bot, guild, fakes):
    guild.members[USER_ID] = fakes.Member(USER_ID, [fakes.Role(fakes.STAFF_ROLE_ID, "Lead")])
    client, _ = sign_in_through_discord(bot, {"roles": [str(fakes.STAFF_ROLE_ID)]})
    me = client.get("/api/auth/me").json()

    assert me["staff"] is True and me["member"] is True
    assert me["state"] == "staff" and me["message"] is None


def test_someone_not_in_the_guild_is_signed_in_but_not_staff(bot, fakes):
    _, done = sign_in_through_discord(bot, None)
    _, payload = read_session(fakes.SECRET, done.cookies[SESSION_COOKIE])
    assert payload["staff"] is False


def test_someone_not_in_the_guild_is_not_a_member_either(bot, fakes):
    client, _ = sign_in_through_discord(bot, None)
    me = client.get("/api/auth/me").json()

    assert me["staff"] is False and me["member"] is False
    assert me["state"] == "not_staff"
    assert "does not hold a staff role" in me["message"]


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
    body = client.get("/api/auth/me").json()
    assert body["staff"] is False
    assert body["state"] == "not_staff"


def test_a_member_the_guild_has_never_heard_of_is_not_staff(bot, sign_in):
    """F2: the guild answered, and its answer is no — the cookie does not overrule it."""
    client = client_for(bot)
    sign_in(client, uid=USER_ID, staff=True, cached=False)
    body = client.get("/api/auth/me").json()
    assert body["staff"] is False
    assert body["state"] == "not_staff"
    assert client.get("/api/status").status_code == 403


def test_a_guild_that_cannot_be_consulted_is_unknown_not_a_refusal(api_settings, fakes, sign_in):
    """F7: bot not ready / no cached guild is its own state, never NOT_STAFF."""
    for headless in (fakes.Bot(api_settings, None), fakes.Bot(api_settings, fakes.Guild())):
        if headless.guild is not None:
            headless.is_ready = lambda: False
        client = client_for(headless)
        sign_in(client, uid=USER_ID, staff=True, cached=False)
        body = client.get("/api/auth/me").json()
        assert body["state"] == "staff_unknown"
        assert body["staff"] is False
        assert "could not check your roles" in body["message"]
        refused = client.get("/api/status")
        assert refused.status_code == 503
        assert refused.json()["error"] == "staff_unknown"


def test_discord_refusing_the_member_lookup_still_signs_them_in(bot, guild, fakes):
    """F7: a 5xx on the member read is not evidence they are not staff."""
    guild.members[USER_ID] = fakes.Member(
        USER_ID, [fakes.Role(fakes.STAFF_ROLE_ID, "Aunties / Uncles")]
    )
    discord = FakeDiscord(member=None, member_status=500)
    client = client_for(bot, discord)
    state = start_login(client)
    done = client.get("/api/auth/callback", params={"code": "abc", "state": state})
    assert done.headers["location"].endswith("?signin=ok")
    _, payload = read_session(fakes.SECRET, done.cookies[SESSION_COOKIE])
    assert payload["staff"] is False
    assert client.get("/api/auth/me").json()["staff"] is True


def test_a_non_ascii_state_is_a_mismatch_not_a_crash(bot):
    """F3: hmac.compare_digest raises TypeError on non-ASCII text."""
    client = client_for(bot)
    start_login(client)
    done = client.get("/api/auth/callback", params={"code": "abc", "state": "sté"})
    assert done.status_code == 303
    assert done.headers["location"].endswith("?signin=state")


def test_a_rejected_state_clears_the_state_cookie(bot):
    """F13: a state that did not match is spent — leaving it invites a replay."""
    client = client_for(bot)
    start_login(client)
    done = client.get("/api/auth/callback", params={"code": "abc", "state": "forged"})
    cleared = set_cookie(done, STATE_COOKIE)
    assert "Max-Age=0" in cleared or "expires=Thu, 01 Jan 1970" in cleared
    assert "; Secure" in cleared and "; Path=/" in cleared


def login(client, headers: dict[str, str]):
    return client.get("/api/auth/login", headers=headers)


def test_sign_in_is_rate_limited_per_client_ip(bot):
    """F4: ten a minute, and the eleventh is a sentence, not a bare 429."""
    client = client_for(bot)
    mine = {"Fly-Client-IP": "1.2.3.4"}
    for _ in range(LOGIN_RATE):
        assert login(client, mine).status_code == 303
    refused = login(client, mine)
    assert refused.status_code == 429
    assert refused.json()["error"] == "slow_down"
    assert "wait a minute" in refused.json()["message"]
    assert login(client, {"Fly-Client-IP": "5.6.7.8"}).status_code == 303


def test_the_callback_shares_the_limit(bot):
    client = client_for(bot)
    mine = {"Fly-Client-IP": "1.2.3.4"}
    for _ in range(LOGIN_RATE):
        login(client, mine)
    refused = client.get("/api/auth/callback", params={"code": "abc"}, headers=mine)
    assert refused.status_code == 429
    assert refused.json()["error"] == "slow_down"


def test_the_bucket_refills_and_cannot_grow_without_bound():
    bucket = TokenBucket(limit=2, window=60)
    assert bucket.take("a", now=0) and bucket.take("a", now=0)
    assert not bucket.take("a", now=0)
    assert bucket.take("a", now=31)
    for n in range(BUCKET_MAX_KEYS + 500):
        bucket.take(str(n), now=10_000)
    assert len(bucket._seen) == BUCKET_MAX_KEYS
    assert "0" not in bucket._seen
    assert str(BUCKET_MAX_KEYS + 499) in bucket._seen


def test_a_flood_of_spoofed_keys_evicts_the_oldest_not_the_one_in_use():
    """A header a caller can write must not be able to buy anybody a fresh allowance."""
    bucket = TokenBucket(limit=1, window=60)
    assert bucket.take("mine", now=0)
    for n in range(BUCKET_MAX_KEYS - 1):
        bucket.take(f"spoofed-{n}", now=0)
    bucket.take("mine", now=0)
    for n in range(BUCKET_MAX_KEYS):
        bucket.take(f"more-{n}", now=0)

    assert len(bucket._seen) == BUCKET_MAX_KEYS
    assert "spoofed-0" not in bucket._seen


def test_a_forged_forwarded_header_cannot_mint_a_new_bucket(bot):
    """Fly's proxy sets Fly-Client-IP; X-Forwarded-For is the caller's to write."""
    client = client_for(bot)
    for n in range(LOGIN_RATE):
        login(client, {"Fly-Client-IP": "1.2.3.4", "X-Forwarded-For": f"9.9.9.{n}"})
    refused = login(client, {"Fly-Client-IP": "1.2.3.4", "X-Forwarded-For": "9.9.9.99"})
    assert refused.status_code == 429


def test_the_forwarded_header_is_used_when_fly_sets_none(bot):
    client = client_for(bot)
    for _ in range(LOGIN_RATE):
        login(client, {"X-Forwarded-For": "7.7.7.7, 10.0.0.1"})
    assert login(client, {"X-Forwarded-For": "7.7.7.7"}).status_code == 429


@pytest.mark.parametrize("raw", ["bódy.deadbeef", "body.mác", "é.é"])
def test_a_non_ascii_cookie_is_invalid_not_a_crash(raw, bot, fakes):
    """F3: str.encode('ascii') on the cookie was a 500. httpx refuses to SEND one,
    so the assertion is at the boundary that reads it."""
    assert read_session(fakes.SECRET, raw) == ("invalid", None)
    request = SimpleNamespace(cookies={SESSION_COOKIE: raw})
    with pytest.raises(Refused) as refused:
        current_session(request, bot)
    assert refused.value.error == "not_signed_in"


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
