import pytest

from black_bloc import pb_match
from black_bloc.pb_match import AMBIGUOUS, FOUND, NOBODY, exact, named
from black_bloc.speedrun import Runner

ZFG = Runner("e8e5v680", "zfg", "https://www.speedrun.com/users/zfg", "zfg1")
TWIN = Runner("x2", "copycat", "", "zfg1")
NO_TWITCH = Runner("x3", "zfg1", "", None)
NEAR = Runner("x4", "zfg11", "", "zfg11")


class Client:
    def __init__(self, found):
        self.found = found
        self.asked = []

    async def users_by_twitch(self, login):
        self.asked.append(("twitch", login))
        return self.found

    async def users_by_name(self, name):
        self.asked.append(("name", name))
        return self.found


def test_the_one_runner_whose_profile_names_the_login_is_the_match():
    found = exact("ZFG1", [ZFG, NEAR])

    assert (found.outcome, found.runner, found.candidates) == (FOUND, ZFG, 1)


@pytest.mark.parametrize(
    ("login", "runners", "outcome"),
    [
        ("zfg1", [], NOBODY),
        ("zfg1", [NEAR], NOBODY),
        ("zfg1", [NO_TWITCH], NOBODY),
        ("zfg", [ZFG], NOBODY),
        ("zfg1", [ZFG, TWIN], AMBIGUOUS),
        ("", [ZFG], NOBODY),
        (None, [ZFG], NOBODY),
    ],
)
def test_anything_but_exactly_one_exact_login_is_no_match(login, runners, outcome):
    found = exact(login, runners)

    assert found.outcome == outcome and found.runner is None


def test_a_name_that_is_only_similar_never_matches():
    assert exact("zfg1", [Runner("x5", "zfg1", "", "zfg_1")]).outcome == NOBODY
    assert exact("zfg1", [Runner("x6", "zfg1", "", "zfg1x")]).outcome == NOBODY


def test_the_same_runner_returned_twice_is_still_one_runner():
    assert exact("zfg1", [ZFG, ZFG]).outcome == FOUND


def test_a_name_set_by_hand_must_be_exactly_one_accounts_name():
    assert named("ZFG", [ZFG, NEAR]).runner is ZFG
    assert named("zfg", [NEAR]).outcome == NOBODY
    assert named("zfg1", [NO_TWITCH, Runner("x7", "ZFG1", "", None)]).outcome == AMBIGUOUS
    assert named("  ", [ZFG]).outcome == NOBODY


async def test_the_client_is_asked_once_and_its_answer_is_filtered():
    client = Client([ZFG, NEAR])

    by_login = await pb_match.by_twitch(client, "zfg1")
    by_name = await pb_match.by_name(client, "zfg11")

    assert by_login.runner is ZFG and by_name.runner is NEAR
    assert client.asked == [("twitch", "zfg1"), ("name", "zfg11")]
