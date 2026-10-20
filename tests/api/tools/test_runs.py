from __future__ import annotations

import json

import pytest

OPERATOR_TOKEN = "operator-read-token-long-enough-to-be-taken"
BEARER = {"Authorization": f"Bearer {OPERATOR_TOKEN}"}
AT = "2026-10-01T00:00:00+00:00"

ROUTES = [
    ("GET", "/api/runs", None),
    ("GET", "/api/runs/games", None),
    ("GET", "/api/runs/export.csv", None),
    ("POST", "/api/runs", {"game": "x"}),
    ("PUT", "/api/runs/h1", {"game": "y"}),
    ("DELETE", "/api/runs/h1", None),
    ("POST", "/api/runs/t1/restore", None),
    ("PUT", "/api/runs/series/x", {"series": "y"}),
    ("PUT", "/api/runs/genre/x", {"genre": "y"}),
    ("POST", "/api/runs/import", {"csv": "game\nx\n"}),
]


@pytest.mark.parametrize(("method", "route", "payload"), ROUTES)
def test_every_runs_route_needs_a_session(client, method, route, payload):
    assert client.request(method, route, json=payload).status_code == 401


@pytest.mark.parametrize(("method", "route", "payload"), ROUTES)
def test_every_runs_route_refuses_a_non_staff_visitor(client, sign_in, method, route, payload):
    sign_in(client, uid=1234, staff=False)
    assert client.request(method, route, json=payload).status_code == 403


async def seed_tracked(web, wf, member_id):
    cur = await web.db.conn.execute(
        "INSERT INTO marathons(guild_id, name, schedule_url, source, source_ref, added_at) "
        "VALUES (?, 'SGDQ 2026', 'https://x/s', 'gdq', '60', ?)",
        (wf.GUILD_ID, AT),
    )
    marathon_id = cur.lastrowid
    people = [{"name": "kat", "login": None, "part": "runner", "user_id": member_id}]
    cur = await web.db.conn.execute(
        "INSERT INTO marathon_runs(marathon_id, external_id, game, category, people, state, "
        "scheduled_at, first_seen_at, last_seen_at) VALUES (?, '1', 'Celeste', 'Any%', ?, "
        "'done', ?, ?, ?)",
        (marathon_id, json.dumps(people), AT, AT, AT),
    )
    await web.db.conn.commit()
    return marathon_id, cur.lastrowid


async def test_add_edit_series_remove_from_the_page_each_leave_one_web_row(
    client, sign_in, web, wf
):
    sign_in(client)
    marathon_id, run_id = await seed_tracked(web, wf, 7)

    added = client.post(
        "/api/runs",
        json={"game": "Sonic 1/2", "date": "2025-06-30", "event": "BtB 2025", "note": "x"},
    )
    assert added.status_code == 200
    key = added.json()["value"]
    found = client.get("/api/runs").json()
    assert {row["key"] for row in found["rows"]} == {key, f"t{run_id}"}
    assert found["events"][0]["marathon_id"] == marathon_id
    assert found["sources"] == ["gdq", "gdq_hotfix"] and found["parts"] == ["runner"]

    assert client.put(f"/api/runs/t{run_id}", json={"category": "100%"}).status_code == 200
    assert client.put("/api/runs/series/sonic%201%2F2", json={"series": "Sonic"}).status_code == 200
    games = client.get("/api/runs/games").json()["games"]
    assert {one["game_key"]: one["series"] for one in games} == {
        "sonic 1/2": "Sonic",
        "celeste": "",
    }
    assert client.delete(f"/api/runs/t{run_id}").status_code == 200
    assert client.post(f"/api/runs/t{run_id}/restore").status_code == 200
    assert client.delete(f"/api/runs/{key}").status_code == 200

    kinds = [kind for kind in await wf.kinds_in(web.db) if "runs." in kind]
    assert kinds == [
        "web.runs.added",
        "web.runs.edited",
        "web.runs.series_set",
        "web.runs.removed",
        "web.runs.restored",
        "web.runs.removed",
    ]


async def test_a_genre_is_set_from_the_page_beside_the_series_with_one_web_row(
    client, sign_in, web, wf
):
    sign_in(client)
    await seed_tracked(web, wf, 7)

    assert client.put("/api/runs/series/celeste", json={"series": "Celeste"}).status_code == 200
    said = client.put("/api/runs/genre/celeste", json={"genre": "Platformer"})
    assert said.status_code == 200 and said.json()["message"] == (
        "**Celeste** is in the genre **Platformer**."
    )
    again = client.put("/api/runs/genre/celeste", json={"genre": "Platformer"})
    assert again.status_code == 409 and "nothing was saved" in again.json()["message"]

    found = client.get("/api/runs").json()
    assert found["genre_names"] == ["Platformer"] and found["series_names"] == ["Celeste"]
    assert [row["genre"] for row in found["rows"]] == ["Platformer"]
    assert client.get("/api/runs?genre=platformer").json()["rows"] == found["rows"]
    assert client.get("/api/runs?genre=rpg").json()["rows"] == []
    games = client.get("/api/runs/games").json()["games"]
    assert [(one["series"], one["genre"]) for one in games] == [("Celeste", "Platformer")]
    head = client.get("/api/runs/export.csv").text.splitlines()[0]
    assert ",series,genre,developer,category," in head

    kinds = [kind for kind in await wf.kinds_in(web.db) if "runs." in kind]
    assert kinds == ["web.runs.series_set", "web.runs.genre_set"]


async def test_a_refusal_says_what_happened_in_words(client, sign_in):
    sign_in(client)

    nothing = client.post("/api/runs/import", json={"dry_run": True})
    missing = client.put("/api/runs/h999", json={"game": "x"})
    bad = client.delete("/api/runs/zz")

    assert nothing.status_code == 400 and "nothing was read" in nothing.json()["message"]
    assert missing.status_code == 404 and "nothing was changed" in missing.json()["message"]
    assert bad.status_code == 400 and "not a run" in bad.json()["message"]


async def test_export_csv_imports_back_with_nothing_added(client, sign_in, web, wf):
    sign_in(client)
    await seed_tracked(web, wf, 7)
    client.post("/api/runs", json={"game": "Celeste 64", "event": "BtB 2025"})

    exported = client.get("/api/runs/export.csv")
    assert exported.status_code == 200
    assert exported.headers["content-type"].startswith("text/csv")
    dry = client.post("/api/runs/import", json={"csv": exported.text, "dry_run": True})
    real = client.post("/api/runs/import", json={"csv": exported.text, "dry_run": False})

    assert dry.json()["value"]["would_add"] == 0 and dry.json()["value"]["skipped"] == 2
    assert real.json()["value"]["added"] == 0
    assert "nothing was written" in dry.json()["message"].lower()


async def test_the_operator_token_reads_the_runs_and_cannot_write(client, web, wf):
    web.settings.operator_read_token = OPERATOR_TOKEN
    await seed_tracked(web, wf, 7)

    assert client.get("/api/runs", headers=BEARER).status_code == 200
    assert client.get("/api/runs/games", headers=BEARER).status_code == 200
    assert client.post("/api/runs", json={"game": "x"}, headers=BEARER).status_code == 403


async def test_filters_ride_the_query_string(client, sign_in, web, wf):
    sign_in(client)
    _, run_id = await seed_tracked(web, wf, 7)
    client.post("/api/runs", json={"game": "Other", "date": "2025-01-01"})

    found = client.get("/api/runs?year=2026").json()["rows"]
    removed = client.get("/api/runs?removed=true").json()["rows"]

    assert [row["key"] for row in found] == [f"t{run_id}"]
    assert removed == []


async def test_the_genre_filter_reads_the_family_and_the_payload_carries_the_families(
    client, sign_in, web, wf
):
    sign_in(client)
    await seed_tracked(web, wf, 7)

    assert client.put("/api/runs/genre/celeste", json={"genre": "Kart racer"}).status_code == 200

    found = client.get("/api/runs").json()
    assert [(row["genre"], row["genre_family"]) for row in found["rows"]] == [
        ("Kart racer", "racing")
    ]
    assert found["genre_families"][0] == {
        "family": "racing",
        "aliases": ["racer", "racers", "race", "kart racer", "kart racing"],
    }
    for wanted in ("racing", "Racer", "kart%20racing"):
        assert client.get(f"/api/runs?genre={wanted}").json()["rows"] == found["rows"]
    assert client.get("/api/runs?q=racers").json()["rows"] == found["rows"]
    assert client.get("/api/runs?genre=kart").json()["rows"] == []
    games = client.get("/api/runs/games").json()["games"]
    assert [one["genre_family"] for one in games] == ["racing"]


async def test_the_search_box_matches_words_in_any_order_initials_and_typos(
    client, sign_in, web, wf
):
    sign_in(client)
    for game in ("Donkey Kong Country 2", "Donkey Kong 64", "Sekiro: Shadows Die Twice"):
        assert client.post("/api/runs", json={"game": game, "event": "BtB 2025"}).status_code == 200

    def games_for(query):
        return sorted(row["game"] for row in client.get(f"/api/runs?q={query}").json()["rows"])

    assert games_for("dkc2") == ["Donkey Kong Country 2"]
    assert games_for("donkey%202") == ["Donkey Kong Country 2"]
    assert games_for("kong") == ["Donkey Kong 64", "Donkey Kong Country 2"]
    assert games_for("sekrio%20die") == ["Sekiro: Shadows Die Twice"]
    assert games_for("btb") == sorted(
        ("Donkey Kong Country 2", "Donkey Kong 64", "Sekiro: Shadows Die Twice")
    )
    assert games_for("dkc3") == []
    rows = client.get("/api/runs").json()["rows"]
    assert all(row["search"].splitlines()[0] == row["game"] for row in rows)


async def test_a_renamed_tracked_run_is_one_row_carrying_its_folded_keys(client, sign_in, web, wf):
    sign_in(client)
    marathon_id, first = await seed_tracked(web, wf, 7)
    people = [{"name": "kat", "login": None, "part": "runner", "user_id": 7}]
    cur = await web.db.conn.execute(
        "INSERT INTO marathon_runs(marathon_id, external_id, game, category, people, state, "
        "scheduled_at, first_seen_at, last_seen_at) VALUES (?, '2', 'Celeste', '100%', ?, "
        "'done', '2026-10-01T00:40:00+00:00', ?, ?)",
        (marathon_id, json.dumps(people), AT, AT),
    )
    await web.db.conn.commit()
    second = cur.lastrowid

    rows = client.get("/api/runs").json()["rows"]
    assert [(row["key"], row["category"], row["folded"]) for row in rows] == [
        (f"t{second}", "100%", [f"t{first}"])
    ]
    assert [one["times"] for one in client.get("/api/runs/games").json()["games"]] == [1]
    assert client.get("/api/runs/export.csv").text.count("Celeste") == 1
    assert len(client.get("/api/runs?q=celeste").json()["rows"]) == 1

    saved = client.put("/api/settings/runs_same_run_minutes", json={"value": 0})
    assert saved.status_code == 200
    assert len(client.get("/api/runs").json()["rows"]) == 2


async def test_a_developer_is_set_from_the_page_filtered_and_found_by_its_alias(
    client, sign_in, web, wf
):
    sign_in(client)
    await seed_tracked(web, wf, 7)

    said = client.put("/api/runs/developer/celeste", json={"developer": " Maddy  Makes Games "})
    assert said.status_code == 200 and said.json()["message"] == (
        "**Celeste** is by **Maddy Makes Games**."
    )
    again = client.put("/api/runs/developer/celeste", json={"developer": "Maddy Makes Games"})
    assert again.status_code == 409 and "nothing was saved" in again.json()["message"]

    found = client.get("/api/runs").json()
    assert found["developer_names"] == ["Maddy Makes Games"]
    assert [row["developer"] for row in found["rows"]] == ["Maddy Makes Games"]
    assert client.get("/api/runs?developer=maddy makes games").json()["rows"] == found["rows"]
    assert client.get("/api/runs?developer=fromsoftware").json()["rows"] == []
    games = client.get("/api/runs/games").json()["games"]
    assert [one["developer"] for one in games] == ["Maddy Makes Games"]
    head = client.get("/api/runs/export.csv").text.splitlines()[0]
    assert ",genre,developer,category," in head

    client.put("/api/runs/developer/celeste", json={"developer": "FromSoftware"})
    assert len(client.get("/api/runs?q=fromsoft").json()["rows"]) == 1
    assert len(client.get("/api/runs?q=from software").json()["rows"]) == 1

    kinds = [kind for kind in await wf.kinds_in(web.db) if "runs." in kind]
    assert kinds == ["web.runs.developer_set", "web.runs.developer_set"]


async def test_a_genre_list_carries_a_family_per_entry_and_a_third_is_refused_in_words(
    client, sign_in, web, wf
):
    sign_in(client)
    await seed_tracked(web, wf, 7)

    said = client.put("/api/runs/genre/celeste", json={"genre": "Soulslike,action-ADVENTURE"})
    assert said.status_code == 200 and said.json()["message"] == (
        "**Celeste** is in the genre **Soulslike, Action adventure**."
    )
    row = client.get("/api/runs").json()["rows"][0]
    assert row["genre"] == "Soulslike, Action adventure"
    assert (row["genre_family"], row["genre_families"]) == ("soulslike", ["soulslike", "adventure"])
    for wanted in ("adventure", "souls"):
        assert len(client.get(f"/api/runs?genre={wanted}").json()["rows"]) == 1

    refused = client.put("/api/runs/genre/celeste", json={"genre": "Platformer, Puzzle, Indie"})
    assert refused.status_code == 400
    body = refused.json()
    assert body["error"] == "too_many_genres"
    assert body["message"] == (
        "**Platformer, Puzzle, Indie** is 3 genres and a game may have 2, so nothing was saved. "
        "Keep the 2 that fit best, separated by commas, or raise the most genres a game may have "
        "on the Settings page."
    )
    assert client.get("/api/runs").json()["rows"][0]["genre"] == "Soulslike, Action adventure"
