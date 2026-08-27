import aiohttp
import pytest

from black_bloc.twitch import (
    HELIX_URL,
    REQUEST_TIMEOUT_SECONDS,
    TOKEN_URL,
    TwitchClient,
    TwitchError,
    batches,
    sized,
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
                    "game_id": "509658",
                    "title": "any%",
                    "started_at": "2026-08-26T12:00:00Z",
                    "thumbnail_url": (
                        f"https://static-cdn.jtvnw.net/previews-ttv/live_user_{login}-"
                        "{width}x{height}.jpg"
                    ),
                }
                for i, login in enumerate(logins)
            ]
        },
    )


def games(*rows):
    return (
        200,
        {
            "data": [
                {
                    "id": game_id,
                    "name": name,
                    "box_art_url": (
                        f"https://static-cdn.jtvnw.net/ttv-boxart/{game_id}-" "{width}x{height}.jpg"
                    ),
                }
                for game_id, name in rows
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


class DeadSession:
    closed = False

    def __init__(self, exc):
        self.exc = exc

    def request(self, *args, **kwargs):
        raise self.exc


@pytest.mark.parametrize(
    "exc",
    [
        OSError("no route to host"),
        aiohttp.ClientError("connection reset"),
        TimeoutError(),
    ],
)
async def test_a_network_failure_becomes_a_twitch_error(exc):
    client = TwitchClient("id", "secret")
    client._session = DeadSession(exc)

    with pytest.raises(TwitchError, match="twitch unreachable"):
        await client._aiohttp_request("GET", f"{HELIX_URL}/streams")


async def test_a_network_failure_reaches_the_caller_of_get_streams():
    client = TwitchClient("id", "secret")
    client._session = DeadSession(OSError("no route to host"))

    with pytest.raises(TwitchError, match="twitch unreachable"):
        await client.get_streams(["alice"])


def test_requests_carry_a_timeout():
    assert REQUEST_TIMEOUT_SECONDS == 15


def test_sized_fills_twitchs_placeholders_and_survives_a_missing_address():
    assert sized("a/{width}x{height}.jpg", 285, 380) == "a/285x380.jpg"
    assert sized(None, 285, 380) == ""
    assert sized("a/plain.jpg", 285, 380) == "a/plain.jpg"


async def test_a_stream_carries_its_game_id_and_a_sized_thumbnail():
    http = FakeHttp([token_ok(), streams("alice")])
    client = TwitchClient("id", "secret", request=http)

    found = await client.get_streams(["alice"])

    assert found[0].game_id == "509658"
    assert found[0].thumbnail_url == (
        "https://static-cdn.jtvnw.net/previews-ttv/live_user_alice-1280x720.jpg"
    )


async def test_get_games_returns_box_art_at_the_size_discord_shows():
    http = FakeHttp([token_ok(), games(("509658", "Just Chatting"))])
    client = TwitchClient("id", "secret", request=http)

    found = await client.get_games(["509658"])

    assert (found[0].id, found[0].name) == ("509658", "Just Chatting")
    assert found[0].box_art_url == "https://static-cdn.jtvnw.net/ttv-boxart/509658-285x380.jpg"
    assert http.calls[1]["url"] == f"{HELIX_URL}/games"
    assert http.calls[1]["params"] == [("id", "509658")]


async def test_a_game_is_only_asked_for_once():
    http = FakeHttp([token_ok(), games(("509658", "Just Chatting"))])
    client = TwitchClient("id", "secret", request=http)

    first = await client.get_games(["509658"])
    second = await client.get_games(["509658", "509658"])

    assert first == second
    assert [c["url"] for c in http.calls] == [TOKEN_URL, f"{HELIX_URL}/games"]


async def test_get_games_asks_only_about_the_ids_it_has_not_seen():
    http = FakeHttp([token_ok(), games(("1", "One")), games(("2", "Two"))])
    client = TwitchClient("id", "secret", request=http)

    await client.get_games(["1"])
    both = await client.get_games(["1", "2"])

    assert sorted(game.id for game in both) == ["1", "2"]
    assert http.calls[2]["params"] == [("id", "2")]


async def test_get_games_ignores_empty_ids_and_never_calls_helix_for_nothing():
    http = FakeHttp([])
    client = TwitchClient("id", "secret", request=http)

    assert await client.get_games([None, "", "  "]) == []
    assert http.calls == []


async def test_a_helix_failure_on_games_reaches_the_caller():
    http = FakeHttp([token_ok(), (500, {})])
    client = TwitchClient("id", "secret", request=http)

    with pytest.raises(TwitchError, match="500"):
        await client.get_games(["509658"])
