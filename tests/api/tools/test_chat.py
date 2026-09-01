import pytest

from black_bloc.api.tools import chat_store
from black_bloc.chat import BUILTIN_ORDER, UNKNOWN, loaded_intents, seed_defaults


@pytest.fixture
async def seeded(client, sign_in, web, wf, guild):
    wf.member(guild, 7, name="lead", staff=True)
    sign_in(client)
    await seed_defaults(web.db, wf.GUILD_ID)
    return client


def intents_of(client):
    return client.get("/api/chat/intents").json()["intents"]


def named(client, name):
    return next(row for row in intents_of(client) if row["name"] == name)


async def test_the_page_lists_every_intent_with_its_lines(seeded, client):
    payload = client.get("/api/chat/intents").json()

    assert {row["name"] for row in payload["intents"]} == set(BUILTIN_ORDER) | {UNKNOWN}
    greeting = named(client, "greeting")
    assert greeting["kind"] == "canned" and greeting["builtin"] is True
    assert isinstance(greeting["id"], str) and greeting["lines"]
    assert all(isinstance(line["id"], str) for line in greeting["lines"])
    assert "slots" in payload and "filled" in payload["slots"]


async def test_each_intent_carries_the_tokens_the_page_offers_as_chips(seeded, client):
    by_name = {row["name"]: row for row in intents_of(client)}

    assert by_name["head_count"]["tokens"] == ["{count}"]
    assert by_name["who_is_live"]["tokens"] == ["{names}", "{links}"]
    assert by_name["whats_next"]["tokens"] == ["{title}", "{when}", "{channel}"]
    assert by_name["birthdays"]["tokens"] == ["{list}"]
    assert by_name["my_roles"]["tokens"] == ["{menus}", "{roles}"]
    assert by_name["time_for_me"]["tokens"] == ["{time}"]
    assert by_name["greeting"]["tokens"] == []


async def test_the_page_gets_the_chat_settings_in_the_shape_settings_uses(seeded, client):
    rows = client.get("/api/chat/intents").json()["settings"]

    assert {row["key"] for row in rows} == {
        "chat_mode",
        "chat_cooldown_seconds",
        "chat_ignore_channels",
        "chat_greeting_reaction",
        "chat_reply_in_threads",
        "chat_route_ping_staff",
        "chat_llm_mode",
        "chat_simple_model",
        "chat_personality",
        "chat_person_hourly_turns",
        "chat_daily_turns",
        "chat_monthly_cap_usd",
        "chat_log_level",
    }
    for row in rows:
        assert {"key", "type", "value", "default", "help"} <= set(row)
    mode = next(row for row in rows if row["key"] == "chat_mode")
    assert mode["choices"] == ["off", "on"]
    assert next(row for row in rows if row["key"] == "chat_reply_in_threads")["default"] is True


async def test_a_guild_never_seeded_is_seeded_on_the_first_read(client, sign_in, wf, guild):
    wf.member(guild, 7, name="lead", staff=True)
    sign_in(client)

    first = client.get("/api/chat/intents").json()["intents"]
    second = client.get("/api/chat/intents").json()["intents"]

    assert len(first) == len(BUILTIN_ORDER) + 1
    assert [row["id"] for row in first] == [row["id"] for row in second]


async def test_a_new_intent_can_be_made_edited_and_deleted(seeded, client, web, wf):
    made = client.post(
        "/api/chat/intents",
        json={"name": "Cookout Hours", "triggers": ["when is the cookout"], "text": "Six sharp."},
    )
    assert made.status_code == 200, made.text
    intent = made.json()["intent"]
    assert intent["name"] == "cookout_hours" and intent["builtin"] is False
    assert intent["triggers"] == ["when is the cookout"]
    assert [line["text"] for line in intent["lines"]] == ["Six sharp."]

    edited = client.put(
        f"/api/chat/intents/{intent['id']}",
        json={"triggers": ["cookout time"], "enabled": False, "sort": 3},
    )
    assert edited.status_code == 200, edited.text
    assert edited.json()["intent"]["triggers"] == ["cookout time"]
    assert edited.json()["intent"]["enabled"] is False
    assert edited.json()["intent"]["sort"] == 3

    gone = client.delete(f"/api/chat/intents/{intent['id']}")
    assert gone.status_code == 200
    assert gone.json()["removed"] is True
    assert "cookout_hours" not in {row["name"] for row in intents_of(client)}


async def test_a_built_in_intent_can_be_turned_off_but_not_deleted(seeded, client):
    greeting = named(client, "greeting")

    off = client.put(f"/api/chat/intents/{greeting['id']}", json={"enabled": False})
    assert off.status_code == 200 and off.json()["intent"]["enabled"] is False

    refused = client.delete(f"/api/chat/intents/{greeting['id']}")
    assert refused.status_code == 409
    assert "cannot be deleted" in refused.json()["message"]
    assert "greeting" in refused.json()["message"]


async def test_a_built_in_intent_keeps_its_name(seeded, client):
    greeting = named(client, "greeting")

    refused = client.put(f"/api/chat/intents/{greeting['id']}", json={"name": "hello"})

    assert refused.status_code == 409
    assert "name cannot change" in refused.json()["message"]


async def test_a_second_intent_cannot_take_a_name_already_in_use(seeded, client):
    client.post("/api/chat/intents", json={"name": "cookout", "triggers": ["cookout"]})

    again = client.post("/api/chat/intents", json={"name": "cookout", "triggers": ["party"]})

    assert again.status_code == 409
    assert "already has an intent" in again.json()["message"]


async def test_a_new_intent_cannot_take_a_built_in_name(seeded, client):
    refused = client.post("/api/chat/intents", json={"name": "greeting", "triggers": ["hi"]})

    assert refused.status_code == 400
    assert "own intents" in refused.json()["message"]


async def test_an_intent_needs_a_usable_name_and_at_least_one_trigger(seeded, client):
    for payload in (
        {"name": "9lives", "triggers": ["hi"]},
        {"name": "cookout", "triggers": []},
        {"name": "cookout", "triggers": ["x" * 61]},
    ):
        refused = client.post("/api/chat/intents", json=payload)
        assert refused.status_code == 400, payload
        assert refused.json()["message"]


async def test_a_line_can_be_added_edited_and_removed(seeded, client):
    greeting = named(client, "greeting")

    added = client.post(
        f"/api/chat/intents/{greeting['id']}/lines", json={"text": "Well hello, {name}."}
    )
    assert added.status_code == 200, added.text
    line = added.json()["line"]
    assert line["slot"] == "filled" and line["enabled"] is True

    edited = client.put(
        f"/api/chat/lines/{line['id']}", json={"text": "Hi {name}.", "enabled": False}
    )
    assert edited.status_code == 200
    assert edited.json()["line"]["text"] == "Hi {name}."
    assert edited.json()["line"]["enabled"] is False

    gone = client.delete(f"/api/chat/lines/{line['id']}")
    assert gone.status_code == 200 and gone.json()["removed"] is True
    assert line["id"] not in {one["id"] for one in named(client, "greeting")["lines"]}


async def test_an_empty_state_line_can_be_edited_on_a_data_intent(seeded, client):
    live = named(client, "who_is_live")
    empty = next(line for line in live["lines"] if line["slot"] == "empty")

    edited = client.put(f"/api/chat/lines/{empty['id']}", json={"text": "Nobody, {name}."})

    assert edited.status_code == 200 and edited.json()["line"]["slot"] == "empty"


async def test_a_line_needs_words_and_a_slot_that_exists(seeded, client):
    greeting = named(client, "greeting")
    for payload in ({"text": "  "}, {"text": "hi", "slot": "somewhere"}, {"text": "x" * 501}):
        refused = client.post(f"/api/chat/intents/{greeting['id']}/lines", json=payload)
        assert refused.status_code == 400, payload


async def test_an_intent_or_line_from_another_server_is_not_found(seeded, client, web, wf):
    other = await seed_defaults(web.db, 9999)
    assert other

    assert client.put("/api/chat/intents/999999", json={"enabled": False}).status_code == 404
    assert client.delete("/api/chat/intents/999999").status_code == 404
    assert client.put("/api/chat/lines/999999", json={"text": "hi"}).status_code == 404
    assert client.delete("/api/chat/lines/999999").status_code == 404
    assert client.post("/api/chat/intents/999999/lines", json={"text": "hi"}).status_code == 404


async def test_try_it_says_which_intent_a_sentence_would_hit(seeded, client):
    said = client.post("/api/chat/try", json={"text": "hi there"})

    assert said.status_code == 200, said.text
    assert said.json()["intent"] == "greeting"
    assert said.json()["kind"] == "canned"
    assert said.json()["line"]


async def test_try_it_renders_a_data_intent_with_live_data(seeded, client):
    said = client.post("/api/chat/try", json={"text": "whos live"}).json()

    assert said["intent"] == "who_is_live"
    assert said["kind"] == "data"
    assert said["slot"] == "empty"
    assert "Nobody is streaming" in said["line"]


async def test_try_it_uses_the_edited_line_straight_away(seeded, client):
    greeting = named(client, "greeting")
    for line in greeting["lines"]:
        client.put(f"/api/chat/lines/{line['id']}", json={"enabled": False})
    client.post(f"/api/chat/intents/{greeting['id']}/lines", json={"text": "Only line."})

    said = client.post("/api/chat/try", json={"text": "hi"}).json()

    assert said["line"] == "Only line."


async def test_try_it_needs_something_to_try(seeded, client):
    refused = client.post("/api/chat/try", json={"text": "   "})
    assert refused.status_code == 400
    assert "nothing to try" in refused.json()["message"]


async def test_try_it_sends_nothing_and_writes_no_action_row(seeded, client, web, wf):
    client.post("/api/chat/try", json={"text": "hi"})

    assert [kind for kind in await wf.kinds_in(web.db) if kind.startswith("web.chat")] == []


async def test_every_write_leaves_its_own_web_chat_line(seeded, client, web, wf):
    made = client.post(
        "/api/chat/intents", json={"name": "cookout", "triggers": ["cookout"]}
    ).json()["intent"]
    client.put(f"/api/chat/intents/{made['id']}", json={"enabled": False})
    line = client.post(
        f"/api/chat/intents/{made['id']}/lines", json={"text": "Six sharp."}
    ).json()["line"]
    client.put(f"/api/chat/lines/{line['id']}", json={"text": "Six."})
    client.delete(f"/api/chat/lines/{line['id']}")
    client.delete(f"/api/chat/intents/{made['id']}")

    kinds = [kind for kind in await wf.kinds_in(web.db) if kind.startswith("web.chat")]

    assert kinds == [
        "web.chat.intent_created",
        "web.chat.intent_edited",
        "web.chat.line_added",
        "web.chat.line_edited",
        "web.chat.line_deleted",
        "web.chat.intent_deleted",
    ]


async def test_a_write_drops_the_cached_rows_so_the_bot_answers_with_the_new_words(
    seeded, client, web, wf
):
    from black_bloc.chat import guild_intents

    before = await guild_intents(web, wf.GUILD_ID)
    greeting = named(client, "greeting")
    client.put(f"/api/chat/intents/{greeting['id']}", json={"triggers": ["ahoy"]})

    after = await guild_intents(web, wf.GUILD_ID)

    assert after is not before
    assert next(row for row in after if row["name"] == "greeting")["triggers"] == ("ahoy",)


async def test_the_whole_page_is_staff_only(client, sign_in, guild, wf):
    wf.member(guild, 8, name="ada")
    sign_in(client, uid=8, staff=False)

    for method, path, body in (
        ("GET", "/api/chat/intents", None),
        ("POST", "/api/chat/intents", {"name": "x", "triggers": ["x"]}),
        ("POST", "/api/chat/try", {"text": "hi"}),
    ):
        response = client.request(method, path, json=body)
        assert response.status_code == 403, path
        assert response.json()["message"]


async def test_the_rows_the_bot_reads_match_what_the_page_shows(seeded, client, web, wf):
    stored = {row["name"]: row for row in await loaded_intents(web.db, wf.GUILD_ID)}
    shown = {row["name"]: row for row in intents_of(client)}

    assert set(stored) == set(shown)
    for name, row in stored.items():
        assert list(row["triggers"]) == shown[name]["triggers"]
        assert row["kind"] == shown[name]["kind"]


async def test_the_knowledge_list_says_who_wrote_each_note_and_when(seeded, client):
    made = client.post(
        "/api/chat/knowledge",
        json={"title": "Cookout hours", "body": "Doors at six, food at seven.", "tag": "cookout"},
    )
    assert made.status_code == 200, made.text

    payload = client.get("/api/chat/knowledge").json()
    row = payload["sections"][0]

    assert payload["counts"] == {"total": 1, "staff": 1, "server": 0}
    assert row["title"] == "Cookout hours" and row["tag"] == "cookout"
    assert row["source"] == "staff" and row["source_word"]
    assert row["editable"] is True and row["locked_why"] is None
    assert row["updated_by"]["id"] == "7" and row["updated_by"]["name"] == "Lead"
    assert row["characters"] == len("Doors at six, food at seven.")
    assert payload["budget"]["sections"] == 3 and payload["budget"]["word"]


async def test_a_note_can_be_written_edited_and_removed(seeded, client):
    made = client.post("/api/chat/knowledge", json={"title": "Rules", "body": "Be kind."}).json()[
        "section"
    ]

    edited = client.put(
        f"/api/chat/knowledge/{made['id']}", json={"body": "Be kind. Bring a chair."}
    )
    assert edited.status_code == 200, edited.text
    assert edited.json()["section"]["body"] == "Be kind. Bring a chair."
    assert "Rules" in edited.json()["message"]

    gone = client.delete(f"/api/chat/knowledge/{made['id']}")
    assert gone.status_code == 200 and gone.json()["removed"] is True
    assert client.get("/api/chat/knowledge").json()["sections"] == []


async def test_a_note_the_bot_wrote_itself_is_shown_but_refused_in_words(seeded, client, web, wf):
    await chat_store.ensure_tables(web.db)
    section_id = await chat_store.add_section(
        web.db, wf.GUILD_ID, "Channels", "general, cookout", source=chat_store.SERVER
    )

    row = next(
        one
        for one in client.get("/api/chat/knowledge").json()["sections"]
        if one["source"] == "server"
    )
    edited = client.put(f"/api/chat/knowledge/{section_id}", json={"body": "mine now"})
    gone = client.delete(f"/api/chat/knowledge/{section_id}")

    assert row["editable"] is False
    assert "cannot be changed by hand" in row["locked_why"]
    assert edited.status_code == 409 and "cannot be changed by hand" in edited.json()["message"]
    assert gone.status_code == 409 and gone.json()["message"]


async def test_a_note_needs_a_heading_and_some_words_and_is_bounded(seeded, client):
    for payload in (
        {"title": "  ", "body": "words"},
        {"title": "Rules", "body": "   "},
        {"title": "x" * 81, "body": "words"},
        {"title": "Rules", "body": "x" * 4001},
        {"title": "Rules", "body": "words", "tag": "x" * 41},
    ):
        refused = client.post("/api/chat/knowledge", json=payload)
        assert refused.status_code == 400, payload
        assert refused.json()["message"]


async def test_two_notes_cannot_share_a_heading(seeded, client):
    client.post("/api/chat/knowledge", json={"title": "Rules", "body": "Be kind."})

    again = client.post("/api/chat/knowledge", json={"title": "Rules", "body": "Be kinder."})

    assert again.status_code == 409
    assert "already has a note" in again.json()["message"]


async def test_a_note_from_another_server_is_not_found(seeded, client, web):
    await chat_store.ensure_tables(web.db)
    elsewhere = await chat_store.add_section(web.db, 9999, "Theirs", "not ours")

    assert client.put(f"/api/chat/knowledge/{elsewhere}", json={"body": "x"}).status_code == 404
    assert client.delete(f"/api/chat/knowledge/{elsewhere}").status_code == 404


async def test_the_personality_page_seeds_the_ported_pool_on_the_first_read(seeded, client):
    first = client.get("/api/chat/personality").json()
    second = client.get("/api/chat/personality").json()

    assert first["mode"] == "cookout" and first["mode_kind"] == "cookout"
    assert first["counts"] == {"total": 11, "enabled": 11}
    assert [row["name"] for row in first["tropes"]] == [row["name"] for row in second["tropes"]]
    assert all(row["voice"] and row["label"] for row in first["tropes"])
    assert "personality.ts" in first["ported_from"]
    assert first["mode_word"]


async def test_the_voice_can_move_to_the_pool_and_to_one_named_trope(seeded, client):
    pooled = client.put("/api/chat/personality", json={"mode": "pool"})
    assert pooled.status_code == 200, pooled.text
    assert pooled.json()["mode_kind"] == "pool" and "11 voices" in pooled.json()["mode_word"]

    pinned = client.put("/api/chat/personality", json={"mode": "noir"})

    assert pinned.status_code == 200
    assert pinned.json()["mode"] == "noir" and pinned.json()["mode_kind"] == "trope"
    assert "noir" in pinned.json()["message"]
    shown = client.get("/api/chat/personality").json()["tropes"]
    assert next(row for row in shown if row["name"] == "noir")["in_use"] is True


async def test_a_voice_nobody_has_is_refused_in_words(seeded, client):
    refused = client.put("/api/chat/personality", json={"mode": "swashbuckling"})
    empty = client.put("/api/chat/personality", json={"mode": "  "})

    assert refused.status_code == 404 and "not one of the voices" in refused.json()["message"]
    assert empty.status_code == 400 and empty.json()["message"]


async def test_a_trope_can_be_switched_off_and_back_on(seeded, client):
    client.get("/api/chat/personality")

    off = client.put("/api/chat/personality/noir", json={"enabled": False})
    assert off.status_code == 200, off.text
    assert off.json()["trope"]["enabled"] is False
    assert client.get("/api/chat/personality").json()["counts"]["enabled"] == 10

    on = client.put("/api/chat/personality/noir", json={"enabled": True})

    assert on.status_code == 200 and on.json()["trope"]["enabled"] is True


async def test_a_voice_that_is_off_cannot_be_the_one_black_bloc_uses(seeded, client):
    client.put("/api/chat/personality/noir", json={"enabled": False})

    refused = client.put("/api/chat/personality", json={"mode": "noir"})

    assert refused.status_code == 409
    assert "switched off" in refused.json()["message"]


async def test_the_voice_in_use_cannot_be_switched_off_underneath_itself(seeded, client):
    client.put("/api/chat/personality", json={"mode": "noir"})

    refused = client.put("/api/chat/personality/noir", json={"enabled": False})

    assert refused.status_code == 409
    assert "cannot be switched off" in refused.json()["message"]


async def test_the_last_voice_in_the_pool_stays_on_while_the_pool_is_what_is_used(seeded, client):
    client.put("/api/chat/personality", json={"mode": "pool"})
    for name in [row["name"] for row in client.get("/api/chat/personality").json()["tropes"]][:-1]:
        client.put(f"/api/chat/personality/{name}", json={"enabled": False})

    last = client.get("/api/chat/personality").json()["tropes"][-1]["name"]
    refused = client.put(f"/api/chat/personality/{last}", json={"enabled": False})

    assert refused.status_code == 409
    assert "last voice left on" in refused.json()["message"]


async def test_a_trope_nobody_has_is_not_found(seeded, client):
    refused = client.put("/api/chat/personality/swashbuckling", json={"enabled": False})

    assert refused.status_code == 404 and refused.json()["message"]


async def test_the_spend_route_words_the_month_the_day_and_every_tier(seeded, client, web, wf):
    await chat_store.ensure_tables(web.db)
    await chat_store.add_ledger_entry(
        web.db,
        wf.GUILD_ID,
        provider="anthropic",
        model="claude-haiku-4-5",
        input_tokens=900,
        output_tokens=200,
        cost_microdollars=1_900_000,
    )

    payload = client.get("/api/chat/spend").json()

    assert payload["month"]["spent_usd"] == 1.9
    assert payload["month"]["cap_usd"] == 20
    assert payload["month"]["left_usd"] == 18.1
    assert "$1.90" in payload["month"]["word"] and "$20.00" in payload["month"]["word"]
    assert payload["today"]["turns"] == 1 and "1 answers" in payload["today"]["word"]
    assert payload["capped"] is False
    assert [row["name"] for row in payload["tiers"]] == ["intents", "important", "simple"]
    assert payload["tiers"][0]["live"] is True
    assert payload["cap_key"] == "chat_monthly_cap_usd"
    assert payload["last_turn_at"]


async def test_a_tier_with_no_key_says_so_rather_than_claiming_it_is_live(
    seeded, client, monkeypatch
):
    monkeypatch.setattr(chat_store, "LLM_MODE_DEFAULT", "on")

    payload = client.get("/api/chat/spend").json()
    haiku = next(row for row in payload["tiers"] if row["name"] == "important")

    assert haiku["live"] is False
    assert "ANTHROPIC_API_KEY" in haiku["word"]


async def test_a_tier_with_a_key_and_the_mode_on_is_live(seeded, client, web, monkeypatch):
    monkeypatch.setattr(chat_store, "LLM_MODE_DEFAULT", "on")
    web.settings.__dict__["anthropic_api_key"] = "sk-contract"

    haiku = next(
        row for row in client.get("/api/chat/spend").json()["tiers"] if row["name"] == "important"
    )

    assert haiku["live"] is True and haiku["word"].startswith("Live")


async def test_the_mode_being_off_is_why_a_tier_is_quiet_and_it_says_which(seeded, client, web):
    web.settings.__dict__["anthropic_api_key"] = "sk-contract"

    haiku = next(
        row for row in client.get("/api/chat/spend").json()["tiers"] if row["name"] == "important"
    )

    assert haiku["live"] is False and "chat_llm_mode" in haiku["word"]


async def test_a_spent_month_shuts_both_model_tiers_and_says_so(
    seeded, client, web, wf, monkeypatch
):
    monkeypatch.setattr(chat_store, "LLM_MODE_DEFAULT", "on")
    web.settings.__dict__["anthropic_api_key"] = "sk-contract"
    web.settings.__dict__["groq_api_key"] = "gsk-contract"
    await chat_store.ensure_tables(web.db)
    await chat_store.add_ledger_entry(
        web.db,
        wf.GUILD_ID,
        provider="anthropic",
        model="claude-haiku-4-5",
        cost_microdollars=20_000_000,
    )

    payload = client.get("/api/chat/spend").json()

    assert payload["capped"] is True
    assert payload["month"]["left_usd"] == 0
    assert "shut until" in payload["month"]["word"]
    assert all(row["live"] is False for row in payload["tiers"] if row["name"] != "intents")
    assert all("$20.00" in row["word"] for row in payload["tiers"] if row["name"] != "intents")


async def test_every_new_write_leaves_its_own_web_chat_line_with_the_website_on_it(
    seeded, client, web, wf
):
    made = client.post("/api/chat/knowledge", json={"title": "Rules", "body": "Be kind."}).json()[
        "section"
    ]
    client.put(f"/api/chat/knowledge/{made['id']}", json={"body": "Be kinder."})
    client.delete(f"/api/chat/knowledge/{made['id']}")
    client.put("/api/chat/personality", json={"mode": "pool"})
    client.put("/api/chat/personality/noir", json={"enabled": False})
    client.put("/api/chat/personality/noir", json={"enabled": True})

    kinds = [kind for kind in await wf.kinds_in(web.db) if kind.startswith("web.chat")]

    assert kinds == [
        "web.chat.knowledge_added",
        "web.chat.knowledge_edited",
        "web.chat.knowledge_removed",
        "web.chat.personality_mode",
        "web.chat.trope_disabled",
        "web.chat.trope_enabled",
    ]
    cur = await web.db.conn.execute(
        "SELECT details FROM action_log WHERE kind = 'web.chat.knowledge_added'"
    )
    assert '"via": "website"' in str((await cur.fetchone())["details"])


async def test_reading_the_new_pages_writes_no_action_row(seeded, client, web, wf):
    client.get("/api/chat/knowledge")
    client.get("/api/chat/personality")
    client.get("/api/chat/spend")

    assert [kind for kind in await wf.kinds_in(web.db) if kind.startswith("web.chat")] == []


async def test_the_new_routes_are_staff_only_too(client, sign_in, guild, wf):
    wf.member(guild, 8, name="ada")
    sign_in(client, uid=8, staff=False)

    for method, path, body in (
        ("GET", "/api/chat/knowledge", None),
        ("POST", "/api/chat/knowledge", {"title": "x", "body": "y"}),
        ("GET", "/api/chat/personality", None),
        ("PUT", "/api/chat/personality", {"mode": "pool"}),
        ("PUT", "/api/chat/personality/noir", {"enabled": False}),
        ("GET", "/api/chat/spend", None),
    ):
        response = client.request(method, path, json=body)
        assert response.status_code == 403, path
        assert response.json()["message"]
