from __future__ import annotations

import pytest

from black_bloc.api.names import (
    channel_kind,
    channels,
    named,
    parse_ids,
    resolve,
    resolve_one,
    roles,
    search_members,
)


class NoNetworkGuild:
    """Every lookup the resolver is allowed to make is a cache read; the rest explode."""

    def __init__(self, inner) -> None:
        self._inner = inner
        self.id = inner.id
        self.roles = inner.roles
        self.channels = inner.channels
        self.members = inner.members

    def get_member(self, user_id):
        return self._inner.get_member(user_id)

    def get_role(self, role_id):
        return self._inner.get_role(role_id)

    def get_channel(self, channel_id):
        return self._inner.get_channel(channel_id)

    async def fetch_member(self, user_id):
        raise AssertionError("the name resolver asked Discord for a member")

    async def fetch_channels(self):
        raise AssertionError("the name resolver asked Discord for the channels")

    async def fetch_roles(self):
        raise AssertionError("the name resolver asked Discord for the roles")


def test_parse_ids_takes_a_comma_list_and_ignores_rubbish():
    assert parse_ids("1,2,3") == [1, 2, 3]
    assert parse_ids("<#500>, <@&11>, <@!7>") == [500, 11, 7]
    assert parse_ids("1,1,2") == [1, 2]
    assert parse_ids("nine") == []
    assert len(parse_ids(",".join(str(n) for n in range(500)), limit=10)) == 10


@pytest.mark.parametrize("bad", [None, "", "  "])
def test_parse_ids_survives_nothing_at_all(bad):
    assert parse_ids(bad) == []


def test_channel_kind_maps_every_discord_type_onto_the_four_the_site_shows(wf):
    assert channel_kind(wf.Channel(1, "a", kind="text")) == "text"
    assert channel_kind(wf.Channel(1, "a", kind="news")) == "text"
    assert channel_kind(wf.Channel(1, "a", kind="voice")) == "voice"
    assert channel_kind(wf.Channel(1, "a", kind="stage_voice")) == "voice"
    assert channel_kind(wf.Channel(1, "a", kind="category")) == "category"
    assert channel_kind(wf.Channel(1, "a", kind="forum")) == "forum"


def test_channels_and_roles_come_out_shaped_for_the_pickers(guild, wf):
    rows = {row["id"]: row for row in channels(guild)}
    assert rows[str(wf.TEST_CHANNEL_ID)]["type"] == "text"
    assert rows[str(wf.TEST_CHANNEL_ID)]["category_id"] == str(wf.CATEGORY_ID)
    assert rows[str(wf.VOICE_CHANNEL_ID)]["type"] == "voice"
    assert rows[str(wf.OTHER_CHANNEL_ID)]["category_id"] is None

    top = roles(guild)[0]
    assert top["name"] == "Admin"
    assert isinstance(top["id"], str) and top["managed"] is False


def test_the_resolver_batches_members_roles_and_channels_in_one_pass(guild, wf):
    wf.member(guild, 7, name="lead", staff=True)
    found = resolve(
        NoNetworkGuild(guild), [7, wf.STAFF_ROLE_ID, wf.TEST_CHANNEL_ID, 123456789, "7"]
    )

    assert found["7"]["kind"] == "member" and found["7"]["display_name"] == "Lead"
    assert found[str(wf.STAFF_ROLE_ID)] == {
        "name": "Aunties / Uncles",
        "display_name": "Aunties / Uncles",
        "kind": "role",
    }
    assert found[str(wf.TEST_CHANNEL_ID)]["kind"] == "channel"
    assert found[str(wf.TEST_CHANNEL_ID)]["display_name"].startswith("#")
    assert found["123456789"]["kind"] == "unknown"
    assert len(found) == 4


def test_an_id_that_is_nothing_is_unknown_rather_than_a_guess(guild):
    assert resolve_one(guild, "not a number")["kind"] == "unknown"
    assert resolve_one(None, 7)["kind"] == "unknown"
    assert resolve_one(guild, 5)["name"] is None


def test_member_search_reads_the_cache_and_never_asks_discord(guild, wf):
    wf.member(guild, 7, name="ada")
    wf.member(guild, 8, name="grace")
    wf.member(guild, 9, name="adalovelace")
    cached = NoNetworkGuild(guild)

    assert [row["name"] for row in search_members(cached, "ada")] == ["ada", "adalovelace"]
    assert [row["name"] for row in search_members(cached, "")] == ["ada", "adalovelace", "grace"]
    assert len(search_members(cached, "", limit=1)) == 1
    assert search_members(cached, "nobody") == []
    assert search_members(cached, "8")[0]["id"] == "8"


def test_search_rows_carry_the_avatar_the_table_shows(guild, wf):
    wf.member(guild, 7, name="ada")
    row = search_members(guild, "ada")[0]
    assert row["avatar_url"].endswith("/7.png")
    assert row["display_name"] == "Ada"


def test_named_puts_a_name_beside_every_id_and_leaves_a_missing_one_missing(guild, wf):
    wf.member(guild, 7, name="lead")
    row = named({"actor_id": "7", "target_id": None}, guild, "actor", "target")
    assert row["actor_name"] == "Lead"
    assert row["target_name"] is None
