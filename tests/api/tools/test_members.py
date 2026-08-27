from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from black_bloc.modcases import add_case

ROUTE = "/api/members"


def joined(days_ago: float) -> datetime:
    return datetime.now(UTC) - timedelta(days=days_ago)


@pytest.fixture
def roster(guild, wf):
    """A server with staff, a bot, a fresh join and somebody Discord forgot the date for."""
    guild.member_count = 6
    people = {
        "lead": wf.member(guild, 7, name="lead", staff=True),
        "ada": wf.member(guild, 21, name="ada"),
        "bo": wf.member(guild, 22, name="bo"),
        "fresh": wf.member(guild, 23, name="fresh"),
        "robot": wf.member(guild, 24, name="helperbot"),
        "nodate": wf.member(guild, 25, name="nodate"),
    }
    people["lead"].joined_at = joined(400)
    people["ada"].joined_at = joined(200)
    people["bo"].joined_at = joined(100)
    people["fresh"].joined_at = joined(2)
    people["robot"].joined_at = joined(300)
    people["robot"].bot = True
    people["nodate"].joined_at = None
    return people


def names_in(payload) -> list[str]:
    return [row["username"] for row in payload["members"]]


def test_the_route_needs_a_session(client):
    assert client.get(ROUTE).status_code == 401


def test_the_route_refuses_a_signed_in_stranger(client, sign_in):
    sign_in(client, uid=1234, staff=False)
    assert client.get(ROUTE).status_code == 403


async def test_the_roster_comes_back_with_the_counts_the_stat_strip_reads(
    client, sign_in, roster
):
    sign_in(client)

    found = client.get(ROUTE).json()

    assert found["total"] == 6
    assert found["humans"] == 5
    assert found["bots"] == 1
    assert found["staff"] == 1
    assert found["new_7d"] == 1
    assert found["shown"] == 6
    assert found["page"] == 1 and found["per_page"] == 50


async def test_a_row_carries_the_name_the_username_and_the_roles(client, sign_in, roster, wf):
    sign_in(client)

    row = next(r for r in client.get(ROUTE).json()["members"] if r["username"] == "lead")

    assert row["id"] == "7" and row["name"] == "Lead"
    assert row["staff"] is True and row["bot"] is False
    assert row["avatar"] == "https://cdn.test/7.png"
    assert [role["name"] for role in row["roles"]] == ["Aunties / Uncles"]
    assert row["roles"][0]["color"] == "#4eefff"
    assert row["roles"][0]["id"] == str(wf.STAFF_ROLE_ID)


async def test_a_member_discord_gave_no_join_date_for_says_so_rather_than_guessing(
    client, sign_in, roster
):
    sign_in(client)

    row = next(r for r in client.get(ROUTE).json()["members"] if r["username"] == "nodate")

    assert row["joined_at"] is None


async def test_a_bot_is_marked_as_one_and_never_counted_as_staff(
    client, sign_in, roster, guild, wf
):
    roster["robot"].roles = [guild.get_role(wf.STAFF_ROLE_ID)]
    sign_in(client)

    found = client.get(ROUTE).json()
    row = next(r for r in found["members"] if r["username"] == "helperbot")

    assert row["bot"] is True and row["staff"] is False
    assert found["staff"] == 1


async def test_search_matches_the_display_name_and_the_username_case_insensitively(
    client, sign_in, roster
):
    sign_in(client)

    assert sorted(names_in(client.get(f"{ROUTE}?q=AD").json())) == ["ada", "lead"]
    assert names_in(client.get(f"{ROUTE}?q=Fresh").json()) == ["fresh"]
    assert names_in(client.get(f"{ROUTE}?q=BOT").json()) == ["helperbot"]
    assert client.get(f"{ROUTE}?q=nobody").json()["members"] == []


async def test_each_filter_narrows_to_what_its_chip_says(client, sign_in, roster):
    sign_in(client)

    assert names_in(client.get(f"{ROUTE}?filter=staff").json()) == ["lead"]
    assert names_in(client.get(f"{ROUTE}?filter=bots").json()) == ["helperbot"]
    assert names_in(client.get(f"{ROUTE}?filter=new").json()) == ["fresh"]
    assert len(client.get(f"{ROUTE}?filter=all").json()["members"]) == 6


async def test_an_unknown_filter_or_sort_falls_back_rather_than_refusing(client, sign_in, roster):
    """A stale bookmark must show the page, not a bare status."""
    sign_in(client)

    found = client.get(f"{ROUTE}?filter=nonsense&sort=sideways").json()

    assert found["shown"] == 6
    assert names_in(found)[0] == "fresh"


async def test_sorting_puts_the_newest_first_the_oldest_first_or_the_names_in_order(
    client, sign_in, roster
):
    sign_in(client)

    newest = names_in(client.get(f"{ROUTE}?sort=joined_desc").json())
    oldest = names_in(client.get(f"{ROUTE}?sort=joined_asc").json())
    alpha = names_in(client.get(f"{ROUTE}?sort=name").json())

    assert newest[0] == "fresh" and oldest[0] == "lead"
    assert newest[-1] == "nodate" and oldest[-1] == "nodate", "no join date sorts last, both ways"
    assert alpha == ["ada", "bo", "fresh", "helperbot", "lead", "nodate"]


async def test_pagination_walks_the_roster_and_the_page_number_never_goes_below_one(
    client, sign_in, roster
):
    sign_in(client)

    first = client.get(f"{ROUTE}?per_page=2&page=1&sort=name").json()
    second = client.get(f"{ROUTE}?per_page=2&page=2&sort=name").json()
    past_the_end = client.get(f"{ROUTE}?per_page=2&page=99&sort=name").json()
    below_one = client.get(f"{ROUTE}?per_page=2&page=0&sort=name").json()

    assert names_in(first) == ["ada", "bo"]
    assert names_in(second) == ["fresh", "helperbot"]
    assert past_the_end["shown"] == 0 and past_the_end["members"] == []
    assert below_one["page"] == 1 and names_in(below_one) == ["ada", "bo"]


async def test_per_page_is_capped_so_one_call_cannot_ask_for_the_whole_server(
    client, sign_in, roster
):
    sign_in(client)

    assert client.get(f"{ROUTE}?per_page=9999").json()["per_page"] == 100
    assert client.get(f"{ROUTE}?per_page=0").json()["per_page"] == 1
    assert client.get(f"{ROUTE}?per_page=nonsense").json()["per_page"] == 50


async def test_the_case_counts_come_from_one_grouped_query_for_the_page(
    client, sign_in, roster, web, wf
):
    for _ in range(3):
        await add_case(web.db, wf.GUILD_ID, 21, "warn", moderator_id=7, reason="spam")
    await add_case(web.db, wf.GUILD_ID, 22, "warn", moderator_id=7, reason="spam")
    await add_case(web.db, 999999, 21, "warn", moderator_id=7, reason="another server")
    sign_in(client)

    rows = {r["username"]: r["cases"] for r in client.get(ROUTE).json()["members"]}

    assert rows["ada"] == 3, "three cases here, and the other server's is not counted"
    assert rows["bo"] == 1
    assert rows["fresh"] == 0 and rows["lead"] == 0


async def test_the_page_answers_when_the_bot_has_no_database(client, sign_in, roster, web):
    """A member list is worth showing without case counts; a dead db is not a dead page."""
    web.db = None
    sign_in(client)

    found = client.get(ROUTE).json()

    assert found["shown"] == 6
    assert all(row["cases"] == 0 for row in found["members"])


async def test_the_total_is_discords_own_count_not_what_the_cache_happens_to_hold(
    client, sign_in, roster, guild
):
    guild.member_count = 900
    sign_in(client)

    found = client.get(ROUTE).json()

    assert found["total"] == 900
    assert found["shown"] == 6, "the page still shows what the cache actually has"
