import pytest

from black_bloc.twitch import (
    HELIX_URL,
    TOKEN_URL,
    TwitchClient,
    TwitchError,
    batches,
)


class FakeHttp:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    async def __call__(self, method, url, *, headers=None, params=None, data=None):
        self.calls.append({"method": method, "url": url, "headers": headers, "params": params})
        if not self.responses:
            raise AssertionError(f"unexpected request: {method} {url}")
        return self.responses.pop(0)


def token_ok(value="tok-1"):
    return (200, {"access_token": value, "expires_in": 5000})


def streams(*logins):
    return (
        200,
        {
            "data": [
                {
                    "user_id": str(100 + i),
                    "user_login": login,
                    "user_name": login.title(),
                    "game_name": "Celeste",
                    "title": "any%",
                    "started_at": "2026-08-26T12:00:00Z",
                }
                for i, login in enumerate(logins)
            ]
        },
    )


def test_batches_are_capped_at_a_hundred():
    logins = [f"user{i}" for i in range(250)]
    chunks = batches(logins)
    assert [len(c) for c in chunks] == [100, 100, 50]
    assert batches([]) == []
    assert batches(["MiXeD"]) == [["mixed"]]


async def test_token_is_fetched_once_and_cached():
    http = FakeHttp([token_ok(), streams("alice"), streams("bob")])
    client = TwitchClient("id", "secret", request=http)

    first = await client.get_streams(["alice"])
    second = await client.get_streams(["bob"])

    assert [s.user_login for s in first] == ["alice"]
    assert [s.user_login for s in second] == ["bob"]
    assert [c["url"] for c in http.calls] == [
        TOKEN_URL,
        f"{HELIX_URL}/streams",
        f"{HELIX_URL}/streams",
    ]
    assert http.calls[1]["headers"]["Authorization"] == "Bearer tok-1"
    assert http.calls[1]["headers"]["Client-Id"] == "id"


async def test_expired_token_is_refreshed_on_401():
    http = FakeHttp([token_ok("old"), (401, {}), token_ok("new"), streams("alice")])
    client = TwitchClient("id", "secret", request=http)

    found = await client.get_streams(["alice"])

    assert [s.user_login for s in found] == ["alice"]
    assert [c["url"] for c in http.calls] == [
        TOKEN_URL,
        f"{HELIX_URL}/streams",
        TOKEN_URL,
        f"{HELIX_URL}/streams",
    ]
    assert http.calls[1]["headers"]["Authorization"] == "Bearer old"
    assert http.calls[3]["headers"]["Authorization"] == "Bearer new"


async def test_get_streams_batches_requests_of_a_hundred():
    logins = [f"user{i}" for i in range(150)]
    http = FakeHttp([token_ok(), streams("user0"), streams("user100")])
    client = TwitchClient("id", "secret", request=http)

    found = await client.get_streams(logins)

    assert [s.user_login for s in found] == ["user0", "user100"]
    assert len(http.calls) == 3
    assert [len(c["params"]) for c in http.calls[1:]] == [100, 50]
    assert http.calls[1]["params"][0] == ("user_login", "user0")


async def test_streams_carry_a_url_and_offline_logins_are_absent():
    http = FakeHttp([token_ok(), streams("alice")])
    client = TwitchClient("id", "secret", request=http)

    found = await client.get_streams(["alice", "ghost"])

    assert len(found) == 1
    assert found[0].url == "https://www.twitch.tv/alice"
    assert found[0].game_name == "Celeste"


async def test_get_users_looks_up_logins():
    http = FakeHttp(
        [token_ok(), (200, {"data": [{"id": "9", "login": "alice", "display_name": "Alice"}]})]
    )
    client = TwitchClient("id", "secret", request=http)

    found = await client.get_users(["Alice"])

    assert (found[0].id, found[0].login, found[0].display_name) == ("9", "alice", "Alice")
    assert http.calls[1]["url"] == f"{HELIX_URL}/users"
    assert http.calls[1]["params"] == [("login", "alice")]


async def test_unknown_login_returns_nothing():
    http = FakeHttp([token_ok(), (200, {"data": []})])
    client = TwitchClient("id", "secret", request=http)
    assert await client.get_users(["nobody"]) == []


async def test_bad_credentials_raise_a_named_error():
    http = FakeHttp([(400, {"message": "invalid client"})])
    client = TwitchClient("id", "wrong", request=http)
    with pytest.raises(TwitchError, match="TWITCH_CLIENT_SECRET"):
        await client.get_streams(["alice"])


async def test_helix_failure_raises():
    http = FakeHttp([token_ok(), (500, {})])
    client = TwitchClient("id", "secret", request=http)
    with pytest.raises(TwitchError, match="500"):
        await client.get_streams(["alice"])
