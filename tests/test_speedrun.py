import json
import pathlib
from datetime import UTC, datetime

import pytest

from black_bloc import speedrun
from black_bloc.speedrun import (
    API_URL,
    BAD_ANSWER,
    EMBED_FULL,
    EMBED_PLAIN,
    NOT_FOUND,
    REFUSED,
    SERVER,
    THROTTLED,
    TOO_LARGE,
    UNREACHABLE,
    SpeedrunClient,
    SpeedrunError,
    category_words,
    personal_best_from,
    runner_from,
    twitch_login_of,
)

FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "speedrun"


def fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class Site:
    """speedrun.com as a list of answers; every question asked is kept."""

    def __init__(self, *answers):
        self.answers = list(answers)
        self.asked = []

    async def __call__(self, url, headers):
        self.asked.append((url, headers))
        found = self.answers.pop(0) if len(self.answers) > 1 else self.answers[0]
        if isinstance(found, Exception):
            raise found
        return found


@pytest.mark.parametrize(
    ("uri", "login"),
    [
        ("https://www.twitch.tv/Zfg1", "zfg1"),
        ("http://twitch.tv/SuperNamu/", "supernamu"),
        ("twitch.tv/ada", "ada"),
        ("https://www.twitch.tv/ada/videos", None),
        ("https://www.youtube.com/user/ZFG", None),
        ("https://nottwitch.tv/ada", None),
        ("", None),
        (None, None),
    ],
)
def test_a_twitch_address_names_one_login_or_none(uri, login):
    assert twitch_login_of(uri) == login


def test_the_real_users_answer_reads_as_one_runner_with_the_login_case_folded():
    rows = fixture("users_by_twitch.json")["data"]

    found = runner_from(rows[0])

    assert (found.id, found.name, found.twitch_login) == ("e8e5v680", "zfg", "zfg1")
    assert found.weblink == "https://www.speedrun.com/users/zfg"
    assert runner_from({}) is None and runner_from("zfg") is None


def test_the_real_personal_bests_answer_reads_run_by_run():
    rows = fixture("personal_bests.json")["data"]

    found = [personal_best_from(row) for row in rows]

    first = found[0]
    assert (first.run_id, first.game, first.category) == ("pm3126z0", "NightSky", "100% Normal")
    assert (first.seconds, first.place, first.status) == (2129.0, 6, "verified")
    assert first.verified_at is None
    assert first.weblink == "https://www.speedrun.com/nightsky/runs/pm3126z0"
    assert first.slot == "946wwn6r|mndxgj2q||"
    level_run = found[1]
    assert level_run.slot.split("|")[2] != "" and ": " in level_run.category
    assert level_run.seconds == 616.9
    dated = found[3]
    assert dated.verified_at == datetime(2020, 1, 23, 13, 9, 52, tzinfo=UTC)
    assert len({one.slot for one in found}) == 4


def test_sub_category_values_are_part_of_the_slot_and_the_words():
    item = {
        "place": 2,
        "run": {
            "id": "r1",
            "weblink": "https://www.speedrun.com/x/runs/r1",
            "game": "g1",
            "category": "c1",
            "level": None,
            "status": {"status": "verified", "verify-date": "2026-10-05T10:00:00Z"},
            "times": {"primary_t": 61.5},
            "values": {"v1": "a", "v2": "z"},
        },
        "game": {"data": {"id": "g1", "names": {"international": "Game"}}},
        "category": {
            "data": {
                "id": "c1",
                "name": "Any%",
                "variables": {
                    "data": [
                        {
                            "id": "v1",
                            "is-subcategory": True,
                            "values": {"values": {"a": {"label": "Glitchless"}}},
                        },
                        {
                            "id": "v2",
                            "is-subcategory": False,
                            "values": {"values": {"z": {"label": "PC"}}},
                        },
                    ]
                },
            }
        },
        "level": {"data": []},
    }

    found = personal_best_from(item)

    assert found.category == "Any% (Glitchless)"
    assert found.slot == "g1|c1||v1=a"


def test_a_run_without_a_time_or_an_id_is_not_a_personal_best():
    assert personal_best_from({"run": {"id": "r1", "times": {"primary_t": None}}}) is None
    assert personal_best_from({"run": {"id": "", "times": {"primary_t": 5}}}) is None
    assert personal_best_from({"run": {"id": "r1", "times": {"primary_t": 0}}}) is None
    assert personal_best_from({"place": 1}) is None


def test_a_place_of_zero_is_no_place():
    item = {"place": 0, "run": {"id": "r1", "times": {"primary_t": 5}}}

    assert personal_best_from(item).place is None


def test_category_words_join_the_level_the_category_and_the_choices():
    assert category_words("", "Any%", []) == "Any%"
    assert category_words("Forest", "Any%", []) == "Forest: Any%"
    assert category_words("Forest", "Any%", ["NG+", "Easy"]) == "Forest: Any% (NG+, Easy)"
    assert category_words("Forest", "", []) == "Forest"


async def test_the_lookup_asks_the_documented_address_under_a_descriptive_agent():
    site = Site((200, fixture("users_by_twitch.json")))
    client = SpeedrunClient(request=site, origin="https://blackbloc.example")

    found = await client.users_by_twitch("zfg1")

    url, headers = site.asked[0]
    assert url == f"{API_URL}/users?twitch=zfg1&max=20"
    assert headers["User-Agent"].startswith("BlackBloc/")
    assert "speedrunning community" in headers["User-Agent"]
    assert "https://blackbloc.example" in headers["User-Agent"]
    assert [one.name for one in found] == ["zfg"] and client.requests == 1


async def test_a_prefix_of_a_login_finds_nobody_as_the_real_api_answered():
    client = SpeedrunClient(request=Site((200, fixture("users_by_twitch_prefix.json"))))

    assert await client.users_by_twitch("zfg") == []


async def test_a_login_cannot_smuggle_a_second_parameter_into_the_address():
    site = Site((200, {"data": []}))

    await SpeedrunClient(request=site).users_by_twitch("ada&max=200#")

    assert site.asked[0][0] == f"{API_URL}/users?twitch=ada%26max%3D200%23&max=20"


async def test_personal_bests_are_read_from_one_unpaginated_answer():
    site = Site((200, fixture("personal_bests.json")))
    client = SpeedrunClient(request=site)

    found = await client.personal_bests("e8e5v680")

    assert len(found) == 4 and len(site.asked) == 1
    assert site.asked[0][0] == (
        f"{API_URL}/users/e8e5v680/personal-bests?embed={EMBED_FULL}&max=200&offset=0"
    )


async def test_a_full_page_with_a_pagination_block_is_followed_and_then_stops():
    def page(count):
        rows = [
            {"place": 1, "run": {"id": f"r{count}-{at}", "times": {"primary_t": 5}}}
            for at in range(count)
        ]
        return (200, {"data": rows, "pagination": {"size": count, "max": 200}})

    site = Site(page(200), page(3))

    found = await SpeedrunClient(request=site).personal_bests("u1")

    assert len(found) == 203
    assert [url.rsplit("offset=", 1)[1] for url, _ in site.asked] == ["0", "200"]


async def test_a_refused_nested_embed_falls_back_once_and_is_remembered():
    site = Site((400, None), (200, fixture("personal_bests.json")))
    client = SpeedrunClient(request=site)

    first = await client.personal_bests("u1")
    await client.personal_bests("u1")

    assert len(first) == 4 and client.embed == EMBED_PLAIN
    asked = [url for url, _ in site.asked]
    assert EMBED_FULL in asked[0] and all(f"embed={EMBED_PLAIN}&" in url for url in asked[1:])
    assert len(asked) == 3


@pytest.mark.parametrize(
    ("status", "kind", "outage"),
    [
        (420, THROTTLED, True),
        (429, THROTTLED, True),
        (500, SERVER, True),
        (503, SERVER, True),
        (404, NOT_FOUND, False),
        (403, REFUSED, False),
    ],
)
async def test_every_status_becomes_one_error_type_said_in_words(status, kind, outage):
    client = SpeedrunClient(request=Site((status, None)))

    with pytest.raises(SpeedrunError) as caught:
        await client.users_by_twitch("ada")

    assert (caught.value.kind, caught.value.outage) == (kind, outage)
    assert "speedrun.com" in str(caught.value) and len(str(caught.value)) > 60


@pytest.mark.parametrize("body", [None, [], {"error": "nope"}, "text"])
async def test_an_answer_that_is_not_the_documented_json_is_a_bad_answer(body):
    client = SpeedrunClient(request=Site((200, body)))

    with pytest.raises(SpeedrunError) as caught:
        await client.personal_bests("u1")

    assert caught.value.kind == BAD_ANSWER and caught.value.outage


def test_a_network_failure_is_never_worded_as_a_permission_failure():
    said = str(SpeedrunError(UNREACHABLE, why="TimeoutError")).casefold()

    assert "network" in said
    assert not any(word in said for word in ("permission", "access", "allowed", "role"))
    assert SpeedrunError(TOO_LARGE).outage is False


class _Content:
    def __init__(self, body):
        self.body = body

    async def iter_chunked(self, size):
        for start in range(0, len(self.body), 5):
            yield self.body[start : start + 5]


class _Answer:
    def __init__(self, status, body):
        self.status = status
        self.content = _Content(body)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class _Session:
    closed = False

    def __init__(self, answer):
        self.answer = answer
        self.asked = []

    def get(self, url, headers=None):
        self.asked.append((url, headers))
        if isinstance(self.answer, Exception):
            raise self.answer
        return self.answer

    async def close(self):
        self.closed = True


async def test_the_transport_wraps_a_timeout_and_reads_json(monkeypatch):
    client = SpeedrunClient()
    client._session = _Session(_Answer(200, b'{"data": []}'))

    assert await client.users_by_twitch("ada") == []
    assert client._session.asked[0][1]["User-Agent"] == client.agent

    client._session = _Session(TimeoutError())
    with pytest.raises(SpeedrunError) as caught:
        await client.users_by_twitch("ada")
    assert caught.value.kind == UNREACHABLE and "TimeoutError" in str(caught.value)

    client._session = _Session(_Answer(200, b"<html>"))
    with pytest.raises(SpeedrunError) as caught:
        await client.users_by_twitch("ada")
    assert caught.value.kind == BAD_ANSWER

    monkeypatch.setattr(speedrun, "MAX_BODY_BYTES", 4)
    client._session = _Session(_Answer(200, b'{"data": []}'))
    with pytest.raises(SpeedrunError) as caught:
        await client.users_by_twitch("ada")
    assert caught.value.kind == TOO_LARGE

    session = client._session
    await client.close()
    assert session.closed and client._session is None


def test_every_call_has_a_timeout():
    assert 0 < speedrun.REQUEST_TIMEOUT_SECONDS <= 30


def padded(size):
    """A personal-bests answer that is exactly `size` bytes of real JSON."""
    empty = len(json.dumps({"data": [], "pad": ""}))
    return json.dumps({"data": [], "pad": "x" * (size - empty)}).encode()


async def loopback(body, *, chunked):
    """A real aiohttp server on 127.0.0.1 answering every GET with `body`."""
    import asyncio

    from aiohttp import web

    async def answer(request):
        if not chunked:
            return web.Response(body=body, content_type="application/json")
        response = web.StreamResponse(headers={"Content-Type": "application/json"})
        response.enable_chunked_encoding()
        await response.prepare(request)
        for start in range(0, len(body), 1024):
            await response.write(body[start : start + 1024])
            await asyncio.sleep(0)
        await response.write_eof()
        return response

    app = web.Application()
    app.router.add_get("/{tail:.*}", answer)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]
    return runner, f"http://127.0.0.1:{port}"


@pytest.mark.parametrize("chunked", [False, True])
@pytest.mark.parametrize("size", [500, 11_000, 110_000])
async def test_the_real_transport_reads_a_whole_answer_from_a_real_server(
    monkeypatch, chunked, size
):
    import aiohttp

    body = padded(size)
    runner, origin = await loopback(body, chunked=chunked)
    monkeypatch.setattr(speedrun, "API_URL", origin)
    client = SpeedrunClient()
    client._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))
    try:
        found = await client.get("/users/u1/personal-bests")
    finally:
        await client.close()
        await runner.cleanup()

    assert found == json.loads(body) and len(body) == size


@pytest.mark.parametrize("chunked", [False, True])
async def test_the_real_transport_refuses_only_an_answer_that_really_passes_the_cap(
    monkeypatch, chunked
):
    import aiohttp

    monkeypatch.setattr(speedrun, "MAX_BODY_BYTES", 50_000)
    under, over = padded(50_000), padded(50_001)
    for body, wanted in ((under, None), (over, TOO_LARGE)):
        runner, origin = await loopback(body, chunked=chunked)
        monkeypatch.setattr(speedrun, "API_URL", origin)
        client = SpeedrunClient()
        client._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))
        try:
            if wanted is None:
                assert await client.get("/x") == json.loads(body)
            else:
                with pytest.raises(SpeedrunError) as caught:
                    await client.get("/x")
                assert caught.value.kind == wanted
        finally:
            await client.close()
            await runner.cleanup()


ODD = [
    None,
    True,
    0,
    -1,
    3.5,
    float("nan"),
    float("inf"),
    "",
    "text",
    "https://[bad",
    [],
    ["a"],
    [[]],
    {},
    {"data": []},
    {"data": None},
    {"data": {"id": []}},
    {"id": {"a": 1}},
    {"uri": "https://[bad"},
    {"values": ["a"]},
    {"values": {"values": ["a"]}},
    {"values": {"values": {"v1": "text"}}},
]


def shapes():
    """A valid item with one field after another swapped for something speedrun.com never said."""
    for odd in ODD:
        yield odd
        yield {"run": odd}
        yield {"place": odd, "run": run_with()}
        for key in ("id", "times", "values", "status", "game", "category", "level", "weblink"):
            yield {"place": 1, "run": run_with(**{key: odd})}
        yield {"place": 1, "run": run_with(times={"primary_t": odd})}
        yield {"place": 1, "run": run_with(status={"status": odd, "verify-date": odd})}
        for embed in ("game", "category", "level"):
            yield {"place": 1, "run": run_with(), embed: odd}
            yield {"place": 1, "run": run_with(), embed: {"data": odd}}
        for variable in (
            odd,
            {"id": odd, "is-subcategory": True, "values": {"values": {"a": {"label": "A"}}}},
            {"id": "v1", "is-subcategory": True, "values": odd},
            {"id": "v1", "is-subcategory": True, "values": {"values": odd}},
            {"id": "v1", "is-subcategory": True, "values": {"values": {"a": odd}}},
        ):
            yield {
                "place": 1,
                "run": run_with(values={"v1": "a"}),
                "category": {"data": {"id": "c1", "variables": {"data": [variable]}}},
            }
            yield {
                "place": 1,
                "run": run_with(values={"v1": odd}),
                "category": {"data": {"id": "c1", "variables": {"data": [variable]}}},
            }


def run_with(**changed):
    return {
        "id": "r1",
        "weblink": "https://www.speedrun.com/x/runs/r1",
        "game": "g1",
        "category": "c1",
        "level": None,
        "times": {"primary_t": 61.5},
        "values": {},
        "status": {"status": "verified", "verify-date": "2026-10-01T00:00:00Z"},
    } | changed


def test_no_malformed_shape_ever_raises_out_of_the_parser():
    count = 0
    for shape in shapes():
        count += 1
        found = personal_best_from(shape)
        assert found is None or (found.seconds > 0 and found.seconds != float("inf"))
        runner_from(shape)
        runner_from({"id": "u1", "names": shape, "twitch": shape, "weblink": shape})
        runner_from({"id": "u1", "twitch": {"uri": shape}})
        twitch_login_of(shape)
    assert count > 500


@pytest.mark.parametrize("seconds", [float("nan"), float("inf"), "fast", [], {}, None, True, -3])
def test_a_time_that_is_not_a_real_number_of_seconds_is_no_personal_best(seconds):
    assert personal_best_from({"place": 1, "run": run_with(times={"primary_t": seconds})}) is None


def test_a_profile_address_that_cannot_be_parsed_names_no_login():
    assert twitch_login_of("https://[bad") is None
    assert runner_from({"id": "u1", "twitch": {"uri": "https://[bad"}}).twitch_login is None


async def test_personal_bests_that_are_not_a_list_are_that_runners_trouble_not_an_outage():
    client = SpeedrunClient(request=Site((200, {"data": {"oops": 1}})))

    with pytest.raises(SpeedrunError) as caught:
        await client.personal_bests("u1")

    assert caught.value.kind == speedrun.MALFORMED and not caught.value.outage


async def test_a_400_that_is_not_about_the_embed_flips_nothing():
    site = Site((400, None), (400, None), (200, fixture("personal_bests.json")))
    client = SpeedrunClient(request=site)

    with pytest.raises(SpeedrunError) as caught:
        await client.personal_bests("not a runner")
    found = await client.personal_bests("u1")

    assert caught.value.kind == REFUSED and not caught.value.outage
    assert client.embed == EMBED_FULL and len(found) == 4
    assert EMBED_FULL in site.asked[-1][0]


async def test_the_nested_embed_is_asked_for_again_after_a_while():
    clock = [1000.0]
    site = Site((400, None), (200, fixture("personal_bests.json")))
    client = SpeedrunClient(request=site, clock=lambda: clock[0])

    await client.personal_bests("u1")
    clock[0] += speedrun.EMBED_RETRY_SECONDS - 1
    await client.personal_bests("u1")
    still = client.embed
    clock[0] += 2
    await client.personal_bests("u1")

    assert still == EMBED_PLAIN and client.embed == EMBED_FULL
    assert [EMBED_FULL in url for url, _ in site.asked] == [True, False, False, True]


def sub_item(run_id, value, seconds):
    return {
        "place": 1,
        "run": run_with(id=run_id, values={"v1": value, "v2": "pc"}, times={"primary_t": seconds}),
        "category": {
            "data": {
                "id": "c1",
                "name": "Any%",
                "variables": {
                    "data": [
                        {
                            "id": "v1",
                            "is-subcategory": True,
                            "values": {
                                "values": {"a": {"label": "Glitched"}, "b": {"label": "NMG"}}
                            },
                        },
                        {"id": "v2", "is-subcategory": False, "values": {"values": {}}},
                    ]
                },
            }
        },
    }


def test_without_the_variables_two_sub_categories_are_never_one_slot():
    fast, slow = sub_item("r1", "a", 100.0), sub_item("r2", "b", 200.0)
    for item in (fast, slow):
        item["category"] = {"data": {"id": "c1", "name": "Any%"}}

    told = [
        personal_best_from(sub_item("r1", "a", 100.0)),
        personal_best_from(sub_item("r2", "b", 200.0)),
    ]
    untold = [personal_best_from(fast, nested=False), personal_best_from(slow, nested=False)]

    assert told[0].slot == "g1|c1||v1=a" and told[1].slot == "g1|c1||v1=b"
    assert untold[0].slot == "g1|c1||?v1=a,v2=pc" and untold[1].slot == "g1|c1||?v1=b,v2=pc"
    assert personal_best_from({"place": 1, "run": run_with()}, nested=False).slot == "g1|c1||"
