import base64

import pytest

from black_bloc import guides as pure

LEAD = 7
READER = 21
STRANGER = 22
ADMIN = 23


def png(width: int = 800, height: int = 600, pad: int = 64) -> bytes:
    return (
        b"\x89PNG\r\n\x1a\n"
        + b"\x00" * 8
        + width.to_bytes(4, "big")
        + height.to_bytes(4, "big")
        + b"\x00" * pad
    )


def upload(raw: bytes, **fields):
    return {"data": base64.b64encode(raw).decode("ascii"), "filename": "shot.png"} | fields


@pytest.fixture
async def people(web, wf, guild):
    wf.member(guild, LEAD, name="lead", staff=True)
    wf.member(guild, READER, name="ada")
    guild.add_member(
        wf.Member(
            ADMIN,
            [guild.get_role(wf.STAFF_ROLE_ID), guild.get_role(wf.ADMIN_ROLE_ID)],
            name="boss",
            manage_guild=True,
        )
    )
    await pure.seed_guides(web.db, wf.GUILD_ID)
    return guild


@pytest.fixture
def as_staff(client, sign_in, people):
    sign_in(client, uid=LEAD, staff=True)
    return client


@pytest.fixture
def as_lead(client, sign_in, people):
    sign_in(client, uid=ADMIN, staff=True)
    return client


@pytest.fixture
def as_member(client, sign_in, people):
    sign_in(client, uid=READER, staff=False)
    return client


@pytest.fixture
def as_stranger(client, sign_in, people):
    sign_in(client, uid=STRANGER, staff=False, cached=False)
    return client


def become(client, sign_in, uid, *, staff, cached=True):
    """One TestClient is shared, so a test that needs two people swaps the cookie."""
    client.cookies.clear()
    sign_in(client, uid=uid, staff=staff, cached=cached)
    return client


def whole(client, slug="golive-announce"):
    return client.get(f"/api/guides/{slug}").json()


def save(client, slug, payload):
    return client.put(f"/api/guides/{slug}", json=payload)


def as_payload(body: dict) -> dict:
    return {
        "title": body["guide"]["title"],
        "goal": body["guide"]["goal"],
        "published": body["guide"]["published"],
        "steps": [
            {"id": one["id"], "do_text": one["do_text"], "expect_text": one["expect_text"]}
            for one in body["steps"]
        ],
        "faults": [
            {"symptom": one["symptom"], "answer": one["answer"]} for one in body["faults"]
        ],
        "facts": body["chosen_facts"],
    }


# --- the gate ---------------------------------------------------------------------------------


async def test_a_signed_out_read_is_refused_in_words_and_never_a_bare_status(client, people):
    answered = client.get("/api/guides")

    assert answered.status_code == 401
    body = answered.json()
    assert body["error"] == "not_signed_in"
    assert "Sign in with the Discord account" in body["message"]


async def test_somebody_who_is_not_in_the_server_is_told_so(as_stranger):
    answered = as_stranger.get("/api/guides")

    assert answered.status_code == 403
    assert answered.json()["error"] == "not_a_member"
    assert "Join the server" in answered.json()["message"]


async def test_a_member_sees_the_member_guides_and_no_staff_one(as_member):
    answered = as_member.get("/api/guides")

    assert answered.status_code == 200
    body = answered.json()
    assert {one["audience"] for one in body["guides"]} == {"member"}
    assert len(body["guides"]) == 10
    assert body["audience"] == "member" and body["may_edit"] is False


async def test_staff_see_every_guide_including_the_staff_ones(as_staff):
    body = as_staff.get("/api/guides").json()

    assert len(body["guides"]) == 17
    assert {one["audience"] for one in body["guides"]} == {"member", "staff"}
    assert body["may_edit"] is True


async def test_a_member_cannot_open_a_staff_guide_by_its_address(as_member):
    answered = as_member.get("/api/guides/mod-case")

    assert answered.status_code == 404
    assert "There is no guide called" in answered.json()["message"]


async def test_an_unpublished_guide_is_hidden_from_a_member_and_shown_to_staff(
    client, sign_in, people, web, wf
):
    await web.db.conn.execute(
        "UPDATE guides SET published = 0 WHERE guild_id = ? AND slug = 'voice-room'",
        (wf.GUILD_ID,),
    )
    await web.db.conn.commit()

    become(client, sign_in, READER, staff=False)
    assert client.get("/api/guides/voice-room").status_code == 404
    become(client, sign_in, LEAD, staff=True)
    assert client.get("/api/guides/voice-room").status_code == 200


async def test_ten_guide_reads_in_a_minute_are_not_rate_limited(as_member):
    answers = [as_member.get("/api/guides/golive-announce") for _ in range(10)]

    assert [one.status_code for one in answers] == [200] * 10


async def test_a_guide_read_does_not_spend_the_members_ten_writes_a_minute(as_member, wf):
    for _ in range(10):
        as_member.get("/api/guides")

    filed = as_member.post(
        "/api/requests", json={"what": "a guide about guides", "why": "so it is written down"}
    )

    assert filed.status_code == 200


async def test_the_read_bucket_still_says_slow_down_when_it_is_empty(as_member, web):
    from black_bloc.api.writes import member_read_bucket_for

    bucket = member_read_bucket_for(web)
    for _ in range(bucket.limit + 1):
        bucket.take(str(READER))

    answered = as_member.get("/api/guides")

    assert answered.status_code == 429
    assert "wait a minute" in answered.json()["message"]


# --- reading a guide --------------------------------------------------------------------------


async def test_a_guide_carries_its_steps_faults_and_live_values(as_member):
    body = whole(as_member)

    assert body["guide"]["slug"] == "golive-announce"
    assert body["guide"]["url"].endswith("/guides.html#golive-announce")
    assert len(body["steps"]) == 4 and body["steps"][0]["position"] == 1
    assert body["faults"] and body["facts"]
    assert {one["kind"] for one in body["facts"]} == {"setting", "probe"}
    assert all(one["read_at"] for one in body["facts"])
    assert body["media"] == []


async def test_the_live_values_are_left_out_when_staff_turn_them_off(as_member, web, wf):
    await web.store.set(wf.GUILD_ID, "guides_show_facts", False, by=LEAD)

    body = whole(as_member)

    assert body["facts"] == [] and body["chosen_facts"]


async def test_guides_off_refuses_a_member_in_words_and_lets_staff_in_with_a_note(
    client, sign_in, people, web, wf
):
    await web.store.set(wf.GUILD_ID, "guides_mode", "off", by=LEAD)

    become(client, sign_in, READER, staff=False)
    refused = client.get("/api/guides/golive-announce")
    assert refused.status_code == 409
    assert "turned off for this server" in refused.json()["message"]

    become(client, sign_in, LEAD, staff=True)
    allowed = client.get("/api/guides/golive-announce")
    assert allowed.status_code == 200
    assert allowed.json()["notes"] and "off for members" in allowed.json()["notes"][0]


async def test_a_step_carries_the_linter_s_warnings_and_what_put_the_original_back_would_restore(
    as_staff, web, wf
):
    await web.db.conn.execute(
        "UPDATE guide_steps SET do_text = 'Simply press the thing' WHERE guide_id = "
        "(SELECT id FROM guides WHERE guild_id = ? AND slug = 'golive-announce') AND position = 1",
        (wf.GUILD_ID,),
    )
    await web.db.conn.commit()

    step = whole(as_staff)["steps"][0]

    assert step["warnings"] and any("Simply" in one for one in step["warnings"])
    assert step["can_restore"] is True
    assert step["seed_do"].startswith("Type **/golive**")


# --- writing ----------------------------------------------------------------------------------


async def test_a_member_may_not_save_a_guide(as_member):
    answered = save(as_member, "golive-announce", {"title": "Mine now"})

    assert answered.status_code == 403
    assert answered.json()["error"] == "not_staff"
    assert "mods and admins" in answered.json()["message"]


async def test_staff_save_the_whole_guide_and_leave_one_row_with_the_diff(as_staff, web, wf):
    body = whole(as_staff)
    payload = as_payload(body)
    payload["steps"][0]["do_text"] = "Simply press the thing"
    payload["steps"].append({"do_text": "Press **Done**.", "expect_text": "The panel closes."})
    payload["faults"] = payload["faults"][:-1]

    answered = save(as_staff, "golive-announce", payload)

    assert answered.status_code == 200
    assert answered.json()["message"] == "**Get your stream announced in #live-now** is saved."
    saved = answered.json()
    assert saved["steps"][0]["do_text"] == "Simply press the thing"
    assert saved["steps"][0]["warnings"], "the linter warns and the save still happened"
    assert len(saved["steps"]) == 5

    details = await wf.one_web_row(web.db, "web.guide.edited")
    assert details["slug"] == "golive-announce"
    assert details["changed"] == "steps +1 −0 ~1, faults +0 −1 ~0, facts +0 −0 ~0"


async def test_a_step_with_nothing_in_it_is_refused_in_words(as_staff):
    payload = as_payload(whole(as_staff))
    payload["steps"][1]["do_text"] = "   "

    answered = save(as_staff, "golive-announce", payload)

    assert answered.status_code == 400
    assert "Step 2 has nothing in it" in answered.json()["message"]


async def test_a_fifth_live_value_and_a_private_key_are_both_refused_in_words(as_staff):
    payload = as_payload(whole(as_staff))
    payload["facts"] = [{"kind": "setting", "ref": "golive_mode"}] * 5

    too_many = save(as_staff, "golive-announce", payload)
    assert too_many.status_code == 400
    assert "at most 4 live values" in too_many.json()["message"]

    payload["facts"] = [{"kind": "setting", "ref": "staff_channel_id"}]
    private = save(as_staff, "golive-announce", payload)
    assert private.status_code == 400
    assert "who counts as staff" in private.json()["message"]

    payload["facts"] = [{"kind": "setting", "ref": "golive_log_level"}]
    level = save(as_staff, "golive-announce", payload)
    assert level.status_code == 400
    assert "Discord log" in level.json()["message"]


async def test_publishing_and_unpublishing_go_through_the_same_body(as_staff, web, wf):
    payload = as_payload(whole(as_staff))
    payload["published"] = False

    off = save(as_staff, "golive-announce", payload)
    assert off.status_code == 200
    assert "is unpublished" in off.json()["message"]
    kinds = [kind for kind, _ in await wf.web_rows_in(web.db)]
    assert kinds == ["web.guide.edited", "web.guide.unpublished"]

    payload["published"] = True
    on = save(as_staff, "golive-announce", payload)
    assert on.status_code == 200
    assert "is published" in on.json()["message"]


async def test_a_second_published_guide_for_one_command_is_refused_in_words(as_staff, web, wf):
    made = as_staff.post(
        "/api/guides",
        json={
            "title": "Another go-live guide",
            "goal": "A second way to say it.",
            "feature": "golive",
            "command": "/golive",
        },
    )
    assert made.status_code == 200
    slug = made.json()["guide"]["slug"]

    payload = as_payload(made.json())
    payload["published"] = True
    answered = save(as_staff, slug, payload)

    assert answered.status_code == 409
    assert "already has a published guide" in answered.json()["message"]
    assert "golive-announce" in answered.json()["message"]


async def test_guides_who_edits_manage_guild_refuses_a_plain_staffer_and_takes_a_lead(
    client, sign_in, people, web, wf
):
    await web.store.set(wf.GUILD_ID, "guides_who_edits", "manage_guild", by=ADMIN)
    become(client, sign_in, LEAD, staff=True)
    payload = as_payload(whole(client))

    refused = save(client, "golive-announce", payload)
    assert refused.status_code == 403
    assert refused.json()["error"] == "not_a_lead"
    assert "Manage Server" in refused.json()["message"]

    become(client, sign_in, ADMIN, staff=True)
    allowed = save(client, "golive-announce", payload)
    assert allowed.status_code == 200


# --- new, delete and reset --------------------------------------------------------------------


async def test_a_new_guide_starts_unpublished_with_a_slug_off_its_title(as_staff, web, wf):
    answered = as_staff.post(
        "/api/guides", json={"title": "How to water the plants", "goal": "Keep them alive."}
    )

    assert answered.status_code == 200
    row = answered.json()["guide"]
    assert row["slug"] == "how-to-water-the-plants"
    assert row["published"] is False and row["seeded"] is False
    assert "unpublished until you press Publish" in answered.json()["message"]
    assert (await wf.one_web_row(web.db, "web.guide.created"))["slug"] == row["slug"]

    again = as_staff.post("/api/guides", json={"title": "How to water the plants", "goal": "x"})
    assert again.status_code == 409
    assert "already a guide at" in again.json()["message"]


async def test_a_guide_with_no_letters_in_its_title_is_refused_in_words(as_staff):
    answered = as_staff.post("/api/guides", json={"title": "###", "goal": "A goal."})

    assert answered.status_code == 400
    assert "turn into a web address" in answered.json()["message"]


async def test_a_seeded_guide_is_never_deleted_and_the_refusal_says_unpublish(as_staff):
    answered = as_staff.delete("/api/guides/golive-announce")

    assert answered.status_code == 409
    assert "Press **Unpublish** instead" in answered.json()["message"]


async def test_a_guide_staff_wrote_here_can_be_deleted(as_staff, web, wf):
    made = as_staff.post("/api/guides", json={"title": "Scratch", "goal": "A goal."})
    slug = made.json()["guide"]["slug"]

    answered = as_staff.delete(f"/api/guides/{slug}")

    assert answered.status_code == 200 and answered.json()["deleted"] == slug
    assert as_staff.get(f"/api/guides/{slug}").status_code == 404
    kinds = [kind for kind, _ in await wf.web_rows_in(web.db)]
    assert kinds == ["web.guide.created", "web.guide.deleted"]


async def test_reset_puts_every_word_back_and_refuses_a_guide_with_no_original(
    as_staff, web, wf
):
    payload = as_payload(whole(as_staff))
    payload["steps"] = [{"do_text": "Press **Nothing**."}]
    save(as_staff, "golive-announce", payload)

    answered = as_staff.post("/api/guides/golive-announce/reset")

    assert answered.status_code == 200
    assert "back to the words it shipped with" in answered.json()["message"]
    assert len(answered.json()["steps"]) == 4

    made = as_staff.post("/api/guides", json={"title": "Scratch", "goal": "A goal."})
    slug = made.json()["guide"]["slug"]
    refused = as_staff.post(f"/api/guides/{slug}/reset")
    assert refused.status_code == 409
    assert "no original to put back" in refused.json()["message"]


# --- pictures ---------------------------------------------------------------------------------


async def test_a_picture_is_uploaded_against_a_step_and_served_back_to_a_member(
    client, sign_in, people, web, wf
):
    as_staff = become(client, sign_in, LEAD, staff=True)
    step_id = whole(as_staff)["steps"][0]["id"]
    raw = png()

    answered = as_staff.post(
        "/api/guides/golive-announce/media",
        json=upload(raw, step_id=step_id, caption="the panel", shot_release="v112"),
    )

    assert answered.status_code == 200
    row = answered.json()["media"]
    assert answered.json()["message"] == "The picture on step 1 is replaced."
    assert (row["width"], row["height"]) == (800, 600)
    assert row["stale"] is False and row["shot_release"] == "v112"
    assert (await wf.one_web_row(web.db, "web.guide.media_replaced"))["slug"] == "golive-announce"

    as_member = become(client, sign_in, READER, staff=False)
    shown = as_member.get(row["url"])
    assert shown.status_code == 200
    assert shown.content == raw
    assert shown.headers["cache-control"] == "private, max-age=86400"
    assert shown.headers["etag"].strip('"') == row["sha256"]

    again = as_member.get(row["url"], headers={"if-none-match": shown.headers["etag"]})
    assert again.status_code == 304

    become(client, sign_in, LEAD, staff=True)
    step = whole(client)["steps"][0]
    assert step["media"]["id"] == row["id"]
    assert step["media"]["alt"] == step["do_text"]


async def test_replacing_a_steps_picture_takes_the_old_one_away(as_staff, web, wf):
    step_id = whole(as_staff)["steps"][0]["id"]
    first = as_staff.post(
        "/api/guides/golive-announce/media", json=upload(png(), step_id=step_id)
    ).json()["media"]

    second = as_staff.post(
        "/api/guides/golive-announce/media", json=upload(png(640, 480), step_id=step_id)
    ).json()["media"]

    assert second["id"] != first["id"]
    body = whole(as_staff)
    assert [one["id"] for one in body["media"]] == [second["id"]]
    assert not pure.media_path(web, f"{first['id']}.png").exists()
    assert pure.media_path(web, f"{second['id']}.png").exists()


async def test_a_picture_a_member_may_not_see_is_refused_in_words(client, sign_in, people):
    become(client, sign_in, LEAD, staff=True)
    row = client.post(
        "/api/guides/golive-announce/media", json=upload(png())
    ).json()["media"]

    become(client, sign_in, STRANGER, staff=False, cached=False)
    assert client.get(row["url"]).status_code == 403
    become(client, sign_in, READER, staff=False)
    missing = client.get("/api/guides/media/9999")
    assert missing.status_code == 404
    assert "not one of this server's guide screenshots" in missing.json()["message"]


async def test_an_over_size_picture_is_refused_in_words_because_pillow_is_not_installed(as_staff):
    too_big = as_staff.post(
        "/api/guides/golive-announce/media",
        json=upload(png(pad=2 * 1024 * 1024)),
    )

    assert too_big.status_code == 413
    assert "keeps guide screenshots under" in too_big.json()["message"]

    too_wide = as_staff.post(
        "/api/guides/golive-announce/media", json=upload(png(2400, 1200))
    )
    assert too_wide.status_code == 413
    assert "cannot resize it for you" in too_wide.json()["message"]


async def test_a_file_that_is_not_a_picture_is_refused_in_words(as_staff):
    wrong = as_staff.post(
        "/api/guides/golive-announce/media", json=upload(png(), filename="shot.gif")
    )
    assert wrong.status_code == 415
    assert "not a picture Black Bloc can serve" in wrong.json()["message"]

    unreadable = as_staff.post(
        "/api/guides/golive-announce/media", json=upload(b"not a picture at all")
    )
    assert unreadable.status_code == 400
    assert "did not arrive as a picture" in unreadable.json()["message"]


async def test_the_stale_list_is_staff_only_and_names_the_guide_each_shot_belongs_to(
    client, sign_in, people, web, wf
):
    as_staff = become(client, sign_in, LEAD, staff=True)
    row = as_staff.post(
        "/api/guides/golive-announce/media", json=upload(png(), shot_release="v110")
    ).json()["media"]
    await web.db.conn.execute(
        "UPDATE guide_media SET stale = 1, stale_since = '2026-09-16T00:00:00+00:00' WHERE id = ?",
        (int(row["id"]),),
    )
    await web.db.conn.commit()

    become(client, sign_in, READER, staff=False)
    assert client.get("/api/guides/stale").status_code == 403

    as_staff = become(client, sign_in, LEAD, staff=True)
    body = as_staff.get("/api/guides/stale").json()
    assert body["count"] == 1
    assert body["shots"][0]["slug"] == "golive-announce"
    assert body["shots"][0]["feature"] == "golive"
    assert as_staff.get("/api/guides").json()["stale"] == 1
