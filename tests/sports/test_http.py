import pytest

from black_bloc.sports import http
from tests.sports_fakes import Recorded


async def test_a_200_answers_the_parsed_body():
    answer = await http.get_json("https://x.test/a", fetch=Recorded({"/a": {"ok": 1}}))
    assert (answer.ok, answer.value) == (True, {"ok": 1})


async def test_a_refusal_is_worded_with_its_status():
    answer = await http.get_json("https://x.test/a", fetch=Recorded({"/a": (403, b"no")}))
    assert (answer.ok, answer.why) == (False, "refused the request")


async def test_a_body_that_is_not_json_is_a_failure():
    answer = await http.get_json("https://x.test/a", fetch=Recorded({"/a": (200, b"<html>")}))
    assert answer.why == "answered with something that is not JSON"


async def test_a_transport_error_is_a_failure_and_never_raises():
    answer = await http.get_json("https://x.test/a", fetch=Recorded({"/a": TimeoutError()}))
    assert answer.ok is False
    assert answer.why == "did not answer in time"
    lost = await http.get_json("https://x.test/a", fetch=Recorded({"/a": OSError("refused")}))
    assert lost.why == "could not be reached"


async def test_a_body_over_the_cap_is_not_read():
    big = (200, bytes(http.MAX_BODY_BYTES + 1))
    answer = await http.get_json("https://x.test/a", fetch=Recorded({"/a": big}))
    assert answer.why == "sent more than Black Bloc reads"


async def test_every_call_says_who_it_is_and_nba_gets_its_headers():
    fetch = Recorded({"": {"ok": 1}})
    await http.get_json("https://site.api.espn.com/x", fetch=fetch)
    await http.get_json("https://stats.nba.com/stats/x", fetch=fetch)
    espn_headers, nba_headers = (headers for _, headers in fetch.asked)
    assert espn_headers["User-Agent"] == "Mozilla/5.0 (Black Bloc)"
    assert "Referer" not in espn_headers
    assert nba_headers["Referer"] == "https://www.nba.com/"
    assert nba_headers["Origin"] == "https://www.nba.com"


async def test_the_pacer_keeps_a_hosts_minimum_gap():
    now = [100.0]
    slept: list[float] = []

    async def sleep(seconds):
        slept.append(round(seconds, 3))
        now[0] += seconds

    pacer = http.Pacer(clock=lambda: now[0], sleep=sleep)
    await pacer.wait("ncaa-api.henrygd.me")
    now[0] += 0.1
    await pacer.wait("ncaa-api.henrygd.me")
    await pacer.wait("site.api.espn.com")
    assert slept == [0.3]


async def test_the_suite_never_reaches_the_network():
    with pytest.raises(BaseException, match="a test asked a sports feed"):
        await http.get_json("https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams")


def test_every_refusal_is_words_and_never_a_bare_status():
    assert http.refusal(404) == "had nothing at that address"
    assert http.refusal(429) == "asked Black Bloc to slow down"
    assert http.refusal(502) == "had a server error"
    assert http.refusal(418) == "answered in a way Black Bloc cannot read"
