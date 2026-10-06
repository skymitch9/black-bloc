import json

from black_bloc import structure
from black_bloc.structure import (
    CHANNEL_FIELDS,
    GUILD_FIELDS,
    OVERWRITE_FIELDS,
    ROLE_FIELDS,
    SNAPSHOT_FIELDS,
    TAG_FIELDS,
    body_of,
    canonical,
    clean,
    counts,
    digest,
    export,
    export_name,
)


def body(**changes):
    found = {
        "guild": {"id": "7", "name": "Black Bloc", "verification_level": "low"},
        "roles": [
            {"id": "7", "name": "@everyone", "permissions": 1024, "position": 0},
            {"id": "11", "name": "Leads", "permissions": 8, "position": 2},
        ],
        "channels": [
            {"id": "40", "name": "Lobby", "type": "category", "position": 0},
            {
                "id": "41",
                "name": "general",
                "type": "text",
                "parent_id": "40",
                "position": 0,
                "overwrites": [
                    {"target_id": "11", "target_type": "role", "allow": 1024, "deny": 0},
                    {"target_id": "7", "target_type": "role", "allow": 0, "deny": 1024},
                ],
            },
        ],
    }
    found.update(changes)
    return found


def test_the_modes_ship_in_shadow():
    assert structure.MODES == ("off", "shadow", "on")
    assert structure.MODE_DEFAULT == "shadow"


def test_a_cleaned_body_holds_the_named_fields_and_nothing_else():
    dirty = body()
    dirty["members"] = [{"id": "900", "roles": ["11"]}]
    dirty["guild"]["owner_id"] = "900"
    dirty["roles"][0]["members"] = ["900"]
    dirty["channels"][1]["last_message"] = "hello"
    dirty["channels"][1]["overwrites"][0]["member_name"] = "sam"

    found = clean(dirty)

    assert set(found) == {"version", "guild", "roles", "channels"}
    assert tuple(found["guild"]) == GUILD_FIELDS
    assert all(tuple(role) == ROLE_FIELDS for role in found["roles"])
    for channel in found["channels"]:
        assert tuple(channel) == (*CHANNEL_FIELDS, "tags", "overwrites")
        assert all(tuple(one) == OVERWRITE_FIELDS for one in channel["overwrites"])
    assert "900" not in json.dumps(found)
    assert "hello" not in json.dumps(found)


def test_no_field_list_names_a_member_or_a_message():
    named = {*GUILD_FIELDS, *ROLE_FIELDS, *CHANNEL_FIELDS, *TAG_FIELDS, *OVERWRITE_FIELDS}

    assert not {one for one in named if "member" in one or "message" in one or "content" in one}


def test_the_same_structure_in_another_order_is_the_same_digest():
    one = body()
    two = body()
    two["roles"].reverse()
    two["channels"].reverse()
    two["channels"][0]["overwrites"].reverse()

    assert canonical(one) == canonical(two)
    assert digest(one) == digest(two)
    assert len(digest(one)) == 64


def test_any_change_is_another_digest():
    changed = body()
    changed["roles"][1]["permissions"] = 16

    assert digest(body()) != digest(changed)


def test_ids_sort_as_numbers_not_as_text():
    rows = [{"id": "100"}, {"id": "9"}, {"id": "20"}]

    assert [row["id"] for row in structure.in_id_order(rows)] == ["9", "20", "100"]


def test_counts_split_categories_from_channels():
    assert counts(body()) == {"roles": 2, "categories": 1, "channels": 1, "overwrites": 2}


def test_anything_that_is_not_a_body_is_an_empty_structure():
    assert counts(None) == {"roles": 0, "categories": 0, "channels": 0, "overwrites": 0}
    assert body_of({"body": "not json"})["roles"] == []
    assert body_of({})["channels"] == []


def row(**extra):
    found = {
        "id": 3,
        "guild_id": 7,
        "taken_at": "2026-10-05T11:00:00+00:00",
        "source": "daily",
        "taken_by": 900,
        "digest": "abc",
        "roles": 2,
        "categories": 1,
        "channels": 1,
        "overwrites": 2,
        "checked_at": "2026-10-06T11:00:00+00:00",
        "checks": 1,
        "body": canonical(body()),
    }
    found.update(extra)
    return found


def test_a_download_is_built_from_the_field_lists_never_from_the_row():
    found = export(row(secret="never", body=json.dumps(body() | {"members": ["900"]})))

    assert set(found) == {"snapshot", "version", "guild", "roles", "channels"}
    assert set(found["snapshot"]) == {*SNAPSHOT_FIELDS, "guild_id"}
    assert "taken_by" not in found["snapshot"]
    assert "never" not in json.dumps(found) and "900" not in json.dumps(found)
    assert found["snapshot"]["guild_id"] == "7"
    assert found["roles"][1]["name"] == "Leads"


def test_a_download_is_named_for_its_server_day_and_number():
    assert export_name(row()) == "structure-7-2026-10-05-3.json"
