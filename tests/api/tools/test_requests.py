import pytest

from black_bloc import requests as pure

LEAD = 7
ASKER = 21
STRANGER = 22
FILED = {"what": "a request board", "why": "the google doc is a mess"}


@pytest.fixture
async def people(web, wf, guild):
    wf.member(guild, LEAD, name="lead", staff=True)
    wf.member(guild, ASKER, name="ada")
    return guild


@pytest.fixture
def as_staff(client, sign_in, people):
    sign_in(client, uid=LEAD, staff=True)
    return client


@pytest.fixture
def as_member(client, sign_in, people):
    sign_in(client, uid=ASKER, staff=False)
    return client


async def file_one(client, **fields):
    return client.post("/api/requests", json=FILED | fields)


async def kinds(web, wf):
    return await wf.kinds_in(web.db)


async def test_a_member_may_file_from_the_site_and_it_waits_for_staff(as_member, web, wf):
    made = await file_one(as_member)

    assert made.status_code == 200
    row = made.json()["request"]
    assert row["status"] == "open" and row["id"] == "1"
    assert row["requester"] == {
        "id": str(ASKER),
        "name": "Ada",
        "avatar": f"https://cdn.test/{ASKER}.png",
    }
    assert row["assignee"] is None and row["comment_count"] == 0
    assert "#1" in made.json()["message"]
    assert "web.request.filed" in await kinds(web, wf)


async def test_a_filed_row_carries_every_field_the_requests_page_reads(as_member):
    row = (await file_one(as_member, due_on="2026-09-15")).json()["request"]

    for key in (
        "id",
        "what",
        "why",
        "due_on",
        "status",
        "priority",
        "notes",
        "requester",
        "assignee",
        "comment_count",
        "created_at",
        "decided_by",
        "decided_at",
        "decline_reason",
        "held_from",
        "held_word",
        "built",
        "how_to_test",
        "ready_by",
        "ready_by_name",
        "sent_back_reason",
        "check_asked_by",
        "check_asked_by_name",
        "check_asked_at",
        "moves",
        "resume_to",
        "done_at",
    ):
        assert key in row
    assert row["due_on"] == "2026-09-15"
    assert row["moves"] == ["declined", "hold", "in_progress"]
    assert row["held_from"] is None and row["resume_to"] is None


async def test_a_staffers_own_filing_waits_like_anybody_elses(as_staff, web, wf):
    """Owner, 2026-09-02: nothing approves itself, and the key that did is gone."""
    from black_bloc.settings_store import KEY_TYPES

    row = (await file_one(as_staff)).json()["request"]

    assert row["status"] == "open" and row["decided_by"] is None
    assert "request_auto_approve_staff" not in KEY_TYPES


async def test_a_signed_in_stranger_is_told_they_are_not_in_the_server(client, sign_in, people):
    sign_in(client, uid=STRANGER, staff=False, cached=False)

    made = await file_one(client)

    assert made.status_code == 403
    assert made.json()["error"] == "not_a_member"
    assert "member of Black in a Flash" in made.json()["message"]


async def test_filing_is_refused_in_words_while_requests_are_off(as_member, web, wf):
    await web.store.set(wf.GUILD_ID, "request_mode", "off", by=LEAD)

    made = await file_one(as_member)

    assert made.status_code == 409 and "turned off" in made.json()["message"]


async def test_a_member_is_refused_while_the_server_says_staff_only(as_member, web, wf):
    await web.store.set(wf.GUILD_ID, "request_who_can_file", "staff", by=LEAD)

    made = await file_one(as_member)

    assert made.status_code == 403 and "Only staff may file" in made.json()["message"]


async def test_a_date_the_bot_cannot_read_is_refused_before_anything_is_written(as_member, web):
    made = await file_one(as_member, due_on="15/09/2026")

    assert made.status_code == 400 and "YYYY-MM-DD" in made.json()["message"]
    assert await pure.count_requests(web.db, web.guild.id) == 0


async def test_an_empty_box_is_refused_with_the_box_it_means(as_member):
    assert "what you are asking for" in (await file_one(as_member, what=" ")).json()["message"]
    assert "why it is worth doing" in (await file_one(as_member, why="")).json()["message"]


async def test_a_member_filing_faster_than_the_limit_is_slowed_down(as_member, monkeypatch):
    from black_bloc.api import writes

    monkeypatch.setattr(writes, "MEMBER_RATE", 2)
    last = None
    for _ in range(4):
        last = await file_one(as_member)

    assert last.status_code == 429
    assert last.json()["error"] == "slow_down"
    assert "wait a minute" in last.json()["message"]


async def test_a_member_sees_their_own_rows_in_every_state_and_nobody_elses(as_member, sign_in):
    client = as_member
    await file_one(client, what="mine")
    sign_in(client, uid=LEAD, staff=True)
    await file_one(client, what="theirs")
    sign_in(client, uid=ASKER, staff=False)

    mine = client.get("/api/requests/mine").json()

    assert [row["what"] for row in mine["requests"]] == ["mine"]
    assert mine["total"] == 1 and mine["page"] == 1 and mine["pages"] == 1


async def test_a_stranger_cannot_read_the_mine_list_either(client, sign_in, people):
    sign_in(client, uid=STRANGER, staff=False, cached=False)

    assert client.get("/api/requests/mine").status_code == 403


async def test_the_member_routes_are_the_only_three_that_are_not_staff_only(as_member):
    await file_one(as_member)

    assert as_member.get("/api/requests").status_code == 403
    assert as_member.get("/api/requests/1").status_code == 403
    assert as_member.post("/api/requests/1/hold", json={"reason": "no"}).status_code == 403
    assert as_member.post("/api/requests/1/resume", json={}).status_code == 403
    assert as_member.post("/api/requests/1/decline", json={"reason": "no"}).status_code == 403
    assert as_member.post("/api/requests/1/status", json={"status": "done"}).status_code == 403
    assert as_member.post("/api/requests/1/comments", json={"text": "hi"}).status_code == 403
    assert as_member.get("/api/requests/export.csv").status_code == 403


async def test_a_member_withdraws_their_own_open_row(as_member, web, wf):
    await file_one(as_member)

    gone = as_member.post("/api/requests/1/withdraw", json={})

    assert gone.status_code == 200
    assert gone.json()["request"]["status"] == "withdrawn"
    assert "withdrawn" in gone.json()["message"]
    assert "web.request.withdrawn" in await kinds(web, wf)


async def test_a_member_cannot_withdraw_somebody_elses(as_staff, client, sign_in):
    await file_one(client)
    sign_in(client, uid=ASKER, staff=False)

    gone = client.post("/api/requests/1/withdraw", json={})

    assert gone.status_code == 403 and "not yours" in gone.json()["message"]


async def test_a_row_being_worked_on_cannot_be_withdrawn_any_more(as_member, client, sign_in, web):
    await file_one(client)
    await pure.set_status(web.db, 1, pure.IN_PROGRESS, decided_by=LEAD)

    gone = client.post("/api/requests/1/withdraw", json={})

    assert gone.status_code == 409 and "nothing to withdraw" in gone.json()["message"]


async def test_a_row_on_hold_may_still_be_taken_back(as_member, client, sign_in, web):
    await file_one(client)
    await pure.set_status(
        web.db, 1, pure.HOLD, decided_by=LEAD, decline_reason="waiting", was=pure.OPEN
    )

    gone = client.post("/api/requests/1/withdraw", json={})

    assert gone.status_code == 200 and gone.json()["request"]["status"] == "withdrawn"


async def test_the_staff_list_is_open_first_and_counts_what_is_waiting(
    as_staff, client, sign_in, web
):
    await file_one(client, what="one")
    await file_one(client, what="two")
    await pure.set_status(web.db, 1, pure.IN_PROGRESS, decided_by=LEAD)
    await pure.set_status(web.db, 2, pure.IN_PROGRESS, decided_by=LEAD)
    sign_in(client, uid=ASKER, staff=False)
    await file_one(client, what="three")
    sign_in(client, uid=LEAD, staff=True)

    payload = client.get("/api/requests").json()

    assert payload["requests"][0]["status"] == "open"
    assert payload["total"] == 3 and payload["per_page"] == pure.API_PAGE
    assert payload["open"] == 1


async def test_the_staff_list_filters_by_status_by_assignee_and_by_words(as_staff, client, web):
    await file_one(client, what="a request board")
    await file_one(client, what="a karaoke night")
    await pure.set_fields(web.db, 2, assignee_id=LEAD)
    await pure.set_status(web.db, 2, pure.IN_PROGRESS, decided_by=LEAD)

    by_status = client.get("/api/requests?status=in_progress").json()
    by_word = client.get("/api/requests?q=karaoke").json()
    by_assignee = client.get(f"/api/requests?assignee={LEAD}").json()

    assert [row["id"] for row in by_status["requests"]] == ["2"]
    assert [row["what"] for row in by_word["requests"]] == ["a karaoke night"]
    assert [row["id"] for row in by_assignee["requests"]] == ["2"]
    assert by_assignee["requests"][0]["assignee"]["name"] == "Lead"


async def test_the_unassigned_column_asks_for_assignee_none(as_staff, client, web):
    await file_one(client, what="nobody has this")
    await file_one(client, what="somebody has this")
    await pure.set_fields(web.db, 2, assignee_id=LEAD)

    unassigned = client.get("/api/requests?assignee=none").json()

    assert [row["id"] for row in unassigned["requests"]] == ["1"]
    assert all(row["assignee"] is None for row in unassigned["requests"])


async def test_a_search_matches_the_requesters_name_as_well_as_the_text(
    as_staff, client, sign_in
):
    await file_one(client, what="a request board")
    sign_in(client, uid=ASKER, staff=False)
    await file_one(client, what="a karaoke night")
    sign_in(client, uid=LEAD, staff=True)

    by_name = client.get("/api/requests?q=ada").json()

    assert [row["id"] for row in by_name["requests"]] == ["2"]
    assert by_name["requests"][0]["requester"]["name"] == "Ada"
    assert client.get("/api/requests?q=nobodyhere").json()["requests"] == []


async def test_the_status_route_walks_the_table_and_refuses_a_move_that_skips_it(as_staff, client):
    await file_one(client)

    skipped = client.post("/api/requests/1/status", json={"status": "review"})

    assert skipped.status_code == 409 and "cannot move it" in skipped.json()["message"]

    picked = client.post("/api/requests/1/status", json={"status": "in_progress"})
    ready = client.post("/api/requests/1/ready", json={"built": "the board"})
    finished = client.post("/api/requests/1/status", json={"status": "done"})

    assert picked.status_code == 200 and picked.json()["request"]["status"] == "in_progress"
    assert ready.status_code == 200 and ready.json()["request"]["status"] == "review"
    assert finished.status_code == 200 and finished.json()["request"]["status"] == "done"
    assert finished.json()["request"]["moves"] == []


async def test_the_status_route_refuses_done_from_anywhere_but_review_in_words(as_staff, client):
    """Owner, 2026-09-03: `done` is reachable only from `review`, and the refusal says how."""
    await file_one(client)
    client.post("/api/requests/1/status", json={"status": "in_progress"})

    early = client.post("/api/requests/1/status", json={"status": "done"})

    assert early.status_code == 409
    said = early.json()["message"]
    assert "checked it" in said and "Ready to check" in said
    assert client.get("/api/requests/1").json()["request"]["status"] == "in_progress"


async def test_the_ready_route_records_both_fields_and_leaves_one_log_row(
    as_staff, client, web, wf
):
    await file_one(client)
    client.post("/api/requests/1/status", json={"status": "in_progress"})
    await wf.web_rows_in(web.db)
    await web.db.conn.execute("DELETE FROM action_log")
    await web.db.conn.commit()

    ready = client.post(
        "/api/requests/1/ready",
        json={"built": "the board, with a CSV export", "how_to_test": "press Export"},
    )

    assert ready.status_code == 200
    row = ready.json()["request"]
    assert row["status"] == "review" and row["status_word"] == "ready to check"
    assert row["built"] == "the board, with a CSV export"
    assert row["how_to_test"] == "press Export"
    assert row["ready_by"] == str(LEAD) and row["ready_by_name"]
    assert (await wf.one_web_row(web.db, "web.request.review"))["request_id"] == 1


async def test_the_ready_route_refuses_an_empty_what_was_built_in_words(as_staff, client):
    await file_one(client)
    client.post("/api/requests/1/status", json={"status": "in_progress"})

    bare = client.post("/api/requests/1/ready", json={"built": "   "})

    assert bare.status_code == 400 and "what was actually built" in bare.json()["message"]
    assert client.get("/api/requests/1").json()["request"]["status"] == "in_progress"


async def test_the_accept_route_finishes_it_and_leaves_one_log_row(as_staff, client, web, wf):
    await file_one(client)
    client.post("/api/requests/1/status", json={"status": "in_progress"})
    client.post("/api/requests/1/ready", json={"built": "the board"})
    await web.db.conn.execute("DELETE FROM action_log")
    await web.db.conn.commit()

    done = client.post("/api/requests/1/accept", json={})

    assert done.status_code == 200 and done.json()["request"]["status"] == "done"
    assert done.json()["request"]["done_at"]
    assert (await wf.one_web_row(web.db, "web.request.done"))["was"] == "review"


async def test_the_accept_route_refuses_the_same_pair_of_eyes_when_the_server_asks_for_two(
    as_staff, client, web
):
    await file_one(client)
    client.post("/api/requests/1/status", json={"status": "in_progress"})
    client.post("/api/requests/1/ready", json={"built": "the board"})
    await web.store.set(web.guild.id, "request_review_by_other", True)

    refused_now = client.post("/api/requests/1/accept", json={})

    assert refused_now.status_code == 409
    assert "somebody else on staff" in refused_now.json()["message"]
    assert client.get("/api/requests/1").json()["request"]["status"] == "review"


async def test_the_check_route_asks_the_requester_and_leaves_one_log_row(
    as_staff, client, sign_in, web, wf
):
    sign_in(client, uid=ASKER, staff=False)
    await file_one(client)
    sign_in(client, uid=LEAD, staff=True)
    client.post("/api/requests/1/status", json={"status": "in_progress"})
    client.post("/api/requests/1/ready", json={"built": "the board"})
    await web.db.conn.execute("DELETE FROM action_log")
    await web.db.conn.commit()

    asked = client.post("/api/requests/1/check", json={})

    assert asked.status_code == 200
    row = asked.json()["request"]
    assert row["status"] == "review"
    assert row["check_asked_by"] == str(LEAD) and row["check_asked_by_name"]
    assert row["check_asked_at"]
    assert "#1" in asked.json()["message"]
    left = await wf.web_rows_in(web.db)
    assert [kind for kind, _ in left] == ["web.request.check_asked"], left
    assert left[0][1]["via"] == wf.VIA_WEBSITE and left[0][1]["told"] == "dm"
    assert [kind for kind in await kinds(web, wf) if kind == "request.check_asked"] == []


async def test_the_check_route_refuses_a_request_nobody_has_marked_ready(as_staff, client, web):
    await file_one(client)

    early = client.post("/api/requests/1/check", json={})

    assert early.status_code == 409 and early.json()["error"] == "not_decided"
    assert "not ready to check" in early.json()["message"]
    assert client.get("/api/requests/1").json()["request"]["check_asked_at"] is None


async def test_the_sendback_route_needs_a_note_and_leaves_one_log_row(as_staff, client, web, wf):
    await file_one(client)
    client.post("/api/requests/1/status", json={"status": "in_progress"})
    client.post("/api/requests/1/ready", json={"built": "the board"})

    bare = client.post("/api/requests/1/sendback", json={})

    assert bare.status_code == 400 and "what is still to do" in bare.json()["message"]

    await web.db.conn.execute("DELETE FROM action_log")
    await web.db.conn.commit()
    sent = client.post("/api/requests/1/sendback", json={"reason": "the CSV has no header row"})

    assert sent.status_code == 200
    row = sent.json()["request"]
    assert row["status"] == "in_progress"
    assert row["sent_back_reason"] == "the CSV has no header row"
    assert row["ready_by"] == str(LEAD)
    assert (await wf.one_web_row(web.db, "web.request.sent_back"))["was"] == "review"


async def test_the_sendback_route_refuses_a_request_nobody_has_marked_ready(as_staff, client):
    await file_one(client)
    client.post("/api/requests/1/status", json={"status": "in_progress"})

    early = client.post("/api/requests/1/sendback", json={"reason": "not yet"})

    assert early.status_code == 409 and "not ready to check" in early.json()["message"]


async def test_built_and_how_to_test_are_editable_on_a_review_or_done_card(
    as_staff, client, web, wf
):
    """A typo in "how to test" must not need a state change to fix (owner, 2026-09-03)."""
    await file_one(client)
    client.post("/api/requests/1/status", json={"status": "in_progress"})
    client.post("/api/requests/1/ready", json={"built": "the board", "how_to_test": "press it"})
    await web.db.conn.execute("DELETE FROM action_log")
    await web.db.conn.commit()

    fixed = client.post("/api/requests/1/status", json={"how_to_test": "press Export"})

    assert fixed.status_code == 200
    assert fixed.json()["request"]["how_to_test"] == "press Export"
    assert fixed.json()["request"]["status"] == "review"
    assert (await wf.one_web_row(web.db, "web.request.updated"))["changed"] == ["how_to_test"]

    client.post("/api/requests/1/accept", json={})
    after = client.post("/api/requests/1/status", json={"built": "the board and its export"})

    assert after.status_code == 200
    assert after.json()["request"]["built"] == "the board and its export"
    assert after.json()["request"]["status"] == "done"


async def test_hold_needs_a_reason_remembers_where_it_came_from_and_resume_puts_it_back(
    as_staff, client, web, wf
):
    await file_one(client)
    client.post("/api/requests/1/status", json={"status": "in_progress"})

    bare = client.post("/api/requests/1/hold", json={})

    assert bare.status_code == 400 and "needs one line" in bare.json()["message"]

    parked = client.post("/api/requests/1/hold", json={"reason": "waiting on the bill"})
    row = parked.json()["request"]

    assert row["status"] == "hold" and row["held_from"] == "in_progress"
    assert row["held_word"] == "being worked on" and row["resume_to"] == "in_progress"
    assert row["decline_reason"] == "waiting on the bill"

    back = client.post("/api/requests/1/resume", json={})

    assert back.status_code == 200
    assert back.json()["request"]["status"] == "in_progress"
    assert back.json()["request"]["held_from"] is None
    left = await kinds(web, wf)
    assert "web.request.hold" in left and "web.request.resumed" in left


async def test_resuming_something_that_is_not_on_hold_is_refused_in_words(as_staff, client):
    await file_one(client)

    refused = client.post("/api/requests/1/resume", json={})

    assert refused.status_code == 409 and "not on hold" in refused.json()["message"]


async def test_filing_from_the_site_is_not_guard_refused_while_test_mode_is_on(
    as_member, web, wf
):
    """The route is a database write; only the notice line is a channel post."""
    web.guard = wf.Guard()

    made = await file_one(as_member)

    assert made.status_code == 200
    assert made.json()["request"]["status"] == "open"


async def test_a_due_date_stays_a_plain_date_on_the_way_out(as_member):
    row = (await file_one(as_member, due_on="2026-09-15")).json()["request"]

    assert row["due_on"] == "2026-09-15" and "T" not in row["due_on"]


async def test_a_status_filter_the_bot_does_not_know_is_refused_by_name(as_staff, client):
    refused = client.get("/api/requests?status=shipped")

    assert refused.status_code == 400 and "shipped" in refused.json()["message"]


async def test_one_request_comes_back_with_its_comments(as_staff, client, web):
    await file_one(client)
    await pure.add_comment(web.db, 1, LEAD, "looking at it")

    payload = client.get("/api/requests/1").json()

    assert payload["request"]["comment_count"] == 1
    assert payload["comments"][0]["text"] == "looking at it"
    assert payload["comments"][0]["author"]["name"] == "Lead"
    assert payload["comments"][0]["id"] == "1"


async def test_a_number_nobody_filed_is_a_sentence_and_a_404(as_staff, client):
    missing = client.get("/api/requests/99")

    assert missing.status_code == 404 and "no request" in missing.json()["message"]


async def test_staff_pick_it_up_from_the_site_and_the_asker_is_dmed(
    as_staff, client, sign_in, web, wf
):
    sign_in(client, uid=ASKER, staff=False)
    await file_one(client)
    sign_in(client, uid=LEAD, staff=True)

    done = client.post("/api/requests/1/status", json={"status": "in_progress"})

    assert done.status_code == 200
    assert done.json()["request"]["status"] == "in_progress"
    assert web.guild.get_member(ASKER).dms
    assert "web.request.in_progress" in await kinds(web, wf)


async def test_a_decision_from_the_site_leaves_one_row_and_not_two(as_staff, client, web, wf):
    """Owner, 2026-09-03: "The app double posted all messages with a web.request and a request".

    The shared `apply_decision` logged `request.done` and the route noted `web.request.done` on
    top of it, so one click left two rows and two embeds. It takes `via` now and notes nothing.
    """
    await file_one(client)

    done = client.post("/api/requests/1/decline", json={"reason": "we already have one"})

    assert done.status_code == 200
    left = await wf.web_rows_in(web.db)
    assert [kind for kind, _ in left] == ["web.request.filed", "web.request.declined"], left
    details = left[-1][1]
    assert details["request_id"] == 1 and details["was"] == "open"
    assert details["via"] == wf.VIA_WEBSITE
    assert [kind for kind in await kinds(web, wf) if kind.startswith("request.")] == []


async def test_resuming_from_the_site_leaves_one_row_and_not_two(as_staff, client, web, wf):
    await file_one(client)
    client.post("/api/requests/1/hold", json={"reason": "waiting on the bill"})

    back = client.post("/api/requests/1/resume", json={})

    assert back.status_code == 200
    left = [kind for kind, _ in await wf.web_rows_in(web.db)]
    assert left == ["web.request.filed", "web.request.hold", "web.request.resumed"], left


async def test_a_decline_without_a_line_is_refused(as_staff, client):
    await file_one(client)

    refused = client.post("/api/requests/1/decline", json={})

    assert refused.status_code == 400 and "needs one line" in refused.json()["message"]


async def test_a_decline_carries_its_reason_into_the_row(as_staff, client, web, wf):
    await file_one(client)

    done = client.post("/api/requests/1/decline", json={"reason": "we already have one"})

    assert done.json()["request"]["decline_reason"] == "we already have one"
    assert "web.request.declined" in await kinds(web, wf)


async def test_the_status_route_saves_assignee_priority_and_notes_in_one_go(
    as_staff, client, web, wf
):
    await file_one(client)

    saved = client.post(
        "/api/requests/1/status",
        json={"assignee_id": str(LEAD), "priority": 2, "notes": "after the hosting bill"},
    )
    row = saved.json()["request"]

    assert row["assignee"]["id"] == str(LEAD) and row["priority"] == 2
    assert row["notes"] == "after the hosting bill" and row["status"] == "open"
    assert "web.request.updated" in await kinds(web, wf)


async def test_the_status_route_moves_the_state_last_so_a_bad_field_stops_it(as_staff, client):
    await file_one(client)

    refused = client.post(
        "/api/requests/1/status", json={"status": "in_progress", "assignee_id": "404404404"}
    )

    assert refused.status_code == 400 and "not somebody Black Bloc can see" in (
        refused.json()["message"]
    )
    assert client.get("/api/requests/1").json()["request"]["status"] == "open"


async def test_a_field_can_be_cleared_again_from_the_page(as_staff, client):
    await file_one(client)
    client.post("/api/requests/1/status", json={"assignee_id": str(LEAD), "priority": 3})

    cleared = client.post("/api/requests/1/status", json={"assignee_id": "", "priority": None})
    row = cleared.json()["request"]

    assert row["assignee"] is None and row["priority"] is None


async def test_a_save_with_nothing_in_it_is_refused_rather_than_logged(as_staff, client, web, wf):
    await file_one(client)

    refused = client.post("/api/requests/1/status", json={})

    assert refused.status_code == 400 and "nothing in it" in refused.json()["message"]
    assert "web.request.updated" not in await kinds(web, wf)


async def test_a_priority_the_page_should_not_have_sent_is_refused(as_staff, client):
    await file_one(client)

    refused = client.post("/api/requests/1/status", json={"priority": 99})

    assert refused.status_code == 400 and "0 to" in refused.json()["message"]


async def test_a_state_only_the_bot_owns_cannot_be_set_from_the_page(as_staff, client):
    await file_one(client)

    for bad in ("withdrawn", "open", "approved", "planned", "pending", "shipped"):
        refused = client.post("/api/requests/1/status", json={"status": bad})
        assert refused.status_code == 400, bad


async def test_moving_a_row_to_where_it_already_is_says_so_and_changes_nothing(as_staff, client):
    await file_one(client)
    client.post("/api/requests/1/status", json={"status": "in_progress"})

    again = client.post("/api/requests/1/status", json={"status": "in_progress"})

    assert again.status_code == 409 and "already" in again.json()["message"]


async def test_a_comment_lands_on_the_row_and_is_counted(as_staff, client, web, wf):
    await file_one(client)

    made = client.post("/api/requests/1/comments", json={"text": "next week"})

    assert made.status_code == 200
    assert made.json()["comment"]["text"] == "next week"
    assert made.json()["comment"]["author"]["id"] == str(LEAD)
    assert client.get("/api/requests/1").json()["request"]["comment_count"] == 1
    assert "web.request.comment" in await kinds(web, wf)


async def test_an_empty_comment_is_refused_in_words(as_staff, client):
    await file_one(client)

    refused = client.post("/api/requests/1/comments", json={"text": "   "})

    assert refused.status_code == 400 and "nothing to add" in refused.json()["message"]


async def test_the_export_is_a_csv_with_a_header_and_one_line_per_request(as_staff, client, web):
    await file_one(client, what="a request board", due_on="2026-09-15")
    await pure.add_comment(web.db, 1, LEAD, "looking at it")

    export = client.get("/api/requests/export.csv")

    assert export.status_code == 200
    assert export.headers["content-type"].startswith("text/csv")
    assert "requests.csv" in export.headers["content-disposition"]
    lines = export.text.strip().splitlines()
    assert lines[0].startswith("id,status,what,why,due_on")
    assert "built,how_to_test,ready_by,sent_back_reason" in lines[0]
    assert "a request board" in lines[1] and "2026-09-15" in lines[1]
    assert lines[1].endswith(",1")


async def test_the_export_carries_what_was_built_and_how_to_test_it(as_staff, client):
    """The CSV is the record of what asking actually got built, so it carries the words."""
    await file_one(client, what="a request board")
    client.post("/api/requests/1/status", json={"status": "in_progress"})
    client.post(
        "/api/requests/1/ready", json={"built": "the board", "how_to_test": "press Export"}
    )

    export = client.get("/api/requests/export.csv")

    assert "review" in export.text
    assert "the board" in export.text and "press Export" in export.text


async def test_the_export_takes_the_same_filters_the_list_does(as_staff, client):
    await file_one(client, what="a request board")
    await file_one(client, what="a karaoke night")

    export = client.get("/api/requests/export.csv?q=karaoke")

    assert "karaoke" in export.text and "request board" not in export.text


async def test_a_request_filed_in_another_server_is_not_found_here(as_staff, client, web):
    await pure.create_request(web.db, 99, ASKER, what="elsewhere", why="elsewhere", due_on=None)

    assert client.get("/api/requests/1").status_code == 404
    assert client.get("/api/requests").json()["total"] == 0


async def test_the_website_makes_the_request_forum_and_leaves_one_web_row(
    as_staff, web, guild, wf
):
    await web.store.set(wf.GUILD_ID, "modmail_category_id", wf.CATEGORY_ID)

    made = as_staff.post("/api/requests/forum", json={})

    assert made.status_code == 200 and made.json()["made"] is True
    forum = guild.created[-1]
    assert forum.name == "requests" and forum.type.name == "forum"
    assert [tag.name for tag in forum.available_tags] == [
        "open",
        "picked up",
        "ready to check",
        "on hold",
        "done",
        "declined",
    ]
    assert web.store.get(wf.GUILD_ID, "request_forum_channel_id") == forum.id
    found = await kinds(web, wf)
    assert "web.request.forum_made" in found and "request.forum_made" not in found


async def test_the_website_refuses_a_second_request_forum_in_words(as_staff, web, wf):
    await web.store.set(wf.GUILD_ID, "modmail_category_id", wf.CATEGORY_ID)
    as_staff.post("/api/requests/forum", json={})

    again = as_staff.post("/api/requests/forum", json={})

    assert again.status_code == 409
    assert "already the request forum" in again.json()["message"]


async def test_the_website_says_which_key_a_request_forum_needs(as_staff):
    refused = as_staff.post("/api/requests/forum", json={})

    assert refused.status_code == 409
    assert "modmail_category_id" in refused.json()["message"]


def test_making_the_request_forum_needs_a_session(client):
    assert client.post("/api/requests/forum", json={}).status_code == 401


def test_making_the_request_forum_refuses_a_member(as_member):
    assert as_member.post("/api/requests/forum", json={}).status_code == 403
