from __future__ import annotations

from black_bloc.api.settings_api import CORE_KEYS, namespace_of
from black_bloc.api.writes import WRITE_RATE
from black_bloc.settings_store import KEY_TYPES


def test_every_registry_key_lands_in_a_namespace():
    for key in KEY_TYPES:
        assert namespace_of(key)
    assert all(namespace_of(key) == "core" for key in CORE_KEYS)
    assert namespace_of("golive_mode") == "golive"
    assert namespace_of("automod_rules") == "automod"


async def test_the_role_menu_switch_round_trips_through_the_settings_api(
    client, sign_in, web, wf
):
    """The Role menus tab's On/Off switch is this key and nothing else."""
    sign_in(client)

    listed = {row["key"]: row for row in client.get("/api/settings").json()["rolemenu"]}
    assert listed["rolemenu_mode"]["value"] == "off"
    assert listed["rolemenu_mode"]["choices"] == ["off", "on"]

    stored = client.put("/api/settings/rolemenu_mode", json={"value": "on"})

    assert stored.status_code == 200 and stored.json()["value"] == "on"
    assert web.store.get(wf.GUILD_ID, "rolemenu_mode") == "on"
    refused = client.put("/api/settings/rolemenu_mode", json={"value": "shadow"})
    assert refused.status_code == 400 and "off, on" in refused.json()["message"]
    assert web.store.get(wf.GUILD_ID, "rolemenu_mode") == "on"


def test_settings_need_a_session(client):
    assert client.get("/api/settings").status_code == 401
    assert client.put("/api/settings/golive_mode", json={"value": "on"}).status_code == 401
    assert client.delete("/api/settings/golive_mode").status_code == 401
    assert client.get("/api/settings/audit").status_code == 401


def test_settings_refuse_a_non_staff_visitor(client, sign_in):
    sign_in(client, uid=1234, staff=False)
    assert client.get("/api/settings").status_code == 403
    assert client.put("/api/settings/golive_mode", json={"value": "on"}).status_code == 403
    assert client.delete("/api/settings/golive_mode").status_code == 403
    assert client.get("/api/settings/audit").status_code == 403


def test_the_index_is_grouped_by_namespace_with_type_default_and_help(client, sign_in):
    sign_in(client)
    body = client.get("/api/settings").json()

    assert set(body) >= {"core", "golive", "tempvoice", "honeypot", "events", "automod", "modmail"}
    core = {row["key"] for row in body["core"]}
    assert core == set(CORE_KEYS) | {"core_log_level"}
    golive = {row["key"]: row for row in body["golive"]}
    assert golive["golive_mode"]["type"] == "enum"
    assert golive["golive_mode"]["choices"] == ["off", "shadow", "on"]
    assert golive["golive_mode"]["value"] == "shadow"
    assert golive["golive_template"]["help"]
    assert {row["key"] for rows in body.values() for row in rows} == set(KEY_TYPES)


def test_ids_are_strings_so_a_snowflake_survives_the_page(client, sign_in, wf):
    sign_in(client)
    client.put("/api/settings/log_channel_id", json={"value": str(wf.TEST_CHANNEL_ID)})
    body = client.get("/api/settings").json()
    row = next(r for r in body["core"] if r["key"] == "log_channel_id")
    assert row["value"] == str(wf.TEST_CHANNEL_ID)


async def test_a_change_is_stored_logged_and_audited(client, sign_in, web, wf):
    sign_in(client, uid=7)

    response = client.put("/api/settings/golive_mode", json={"value": "on"})

    assert response.status_code == 200
    assert response.json()["value"] == "on"
    assert web.store.get(wf.GUILD_ID, "golive_mode") == "on"
    assert "web.settings.set" in await wf.kinds_in(web.db)
    audit = client.get("/api/settings/audit").json()["audit"]
    assert audit[0]["key"] == "golive_mode"
    assert audit[0]["updated_by_id"] == "7"


async def test_the_audit_resolves_who_changed_it(client, sign_in, web, guild, wf):
    wf.member(guild, 7, name="lead", staff=True)
    sign_in(client, uid=7)
    client.put("/api/settings/golive_cooldown_minutes", json={"value": 30})

    row = client.get("/api/settings/audit").json()["audit"][0]

    assert row["updated_by_name"] == "Lead"
    assert row["value"] == 30
    assert row["namespace"] == "golive"


def test_a_refused_value_comes_back_as_the_validators_own_sentence(client, sign_in, web, wf):
    sign_in(client)

    response = client.put("/api/settings/golive_mode", json={"value": "sideways"})

    assert response.status_code == 400
    assert response.json()["error"] == "bad_value"
    assert "off, shadow, on" in response.json()["message"]
    assert web.store.get(wf.GUILD_ID, "golive_mode") == "shadow"


def test_the_clamped_keys_refuse_with_the_reason_not_just_the_number(client, sign_in):
    sign_in(client)
    response = client.put("/api/settings/honeypot_purge_days", json={"value": 9})
    assert response.status_code == 400
    assert "Discord itself refuses" in response.json()["message"]


def test_an_unknown_key_is_refused_by_name(client, sign_in):
    sign_in(client)
    response = client.put("/api/settings/not_a_setting", json={"value": 1})
    assert response.status_code == 400
    assert response.json()["error"] == "unknown_setting"
    assert "not_a_setting" in response.json()["message"]
    assert client.delete("/api/settings/not_a_setting").status_code == 400


def test_a_change_with_no_value_at_all_says_so(client, sign_in):
    sign_in(client)
    response = client.put("/api/settings/golive_mode", json={})
    assert response.status_code == 400
    assert response.json()["error"] == "no_value"


def test_a_channel_can_be_sent_as_a_string_or_a_number(client, sign_in, web, wf):
    sign_in(client)

    assert client.put(
        "/api/settings/golive_channel_id", json={"value": str(wf.OTHER_CHANNEL_ID)}
    ).json()["value"] == str(wf.OTHER_CHANNEL_ID)
    assert web.store.get(wf.GUILD_ID, "golive_channel_id") == wf.OTHER_CHANNEL_ID

    client.put("/api/settings/golive_channel_id", json={"value": wf.TEST_CHANNEL_ID})
    assert web.store.get(wf.GUILD_ID, "golive_channel_id") == wf.TEST_CHANNEL_ID


def test_a_list_of_channels_arrives_as_strings_and_stores_as_numbers(client, sign_in, web, wf):
    sign_in(client)
    response = client.put(
        "/api/settings/honeypot_channel_ids",
        json={"value": [str(wf.OTHER_CHANNEL_ID), str(wf.TEST_CHANNEL_ID)]},
    )
    assert response.json()["value"] == [str(wf.OTHER_CHANNEL_ID), str(wf.TEST_CHANNEL_ID)]
    assert web.store.get(wf.GUILD_ID, "honeypot_channel_ids") == [
        wf.OTHER_CHANNEL_ID,
        wf.TEST_CHANNEL_ID,
    ]


def test_a_bool_takes_true_and_refuses_a_word(client, sign_in, web, wf):
    sign_in(client)
    assert client.put("/api/settings/birthday_show_age", json={"value": True}).status_code == 200
    assert web.store.get(wf.GUILD_ID, "birthday_show_age") is True
    assert client.put("/api/settings/birthday_show_age", json={"value": "yes"}).status_code == 400


async def test_delete_puts_the_default_back(client, sign_in, web, wf):
    sign_in(client)
    client.put("/api/settings/golive_mode", json={"value": "on"})

    response = client.delete("/api/settings/golive_mode")

    assert response.status_code == 200
    assert response.json()["cleared"] is True
    assert response.json()["value"] == "shadow"
    assert web.store.get(wf.GUILD_ID, "golive_mode") == "shadow"
    assert "web.settings.clear" in await wf.kinds_in(web.db)


def test_the_audit_limit_is_clamped(client, sign_in):
    sign_in(client)
    assert client.get("/api/settings/audit", params={"limit": 10000}).json()["limit"] == 500
    assert client.get("/api/settings/audit", params={"limit": 0}).json()["limit"] == 1


def test_writes_are_rate_limited_per_session(client, sign_in):
    sign_in(client)
    for _ in range(WRITE_RATE):
        assert client.put("/api/settings/golive_mode", json={"value": "on"}).status_code == 200

    response = client.put("/api/settings/golive_mode", json={"value": "on"})

    assert response.status_code == 429
    assert response.json()["error"] == "slow_down"
    assert client.get("/api/settings").status_code == 200
