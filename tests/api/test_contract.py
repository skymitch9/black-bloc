from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from discord.ext import tasks

from black_bloc import applications, knowledge, pings
from black_bloc import rolegrants as grants
from black_bloc.api.settings_api import grouped
from black_bloc.chat import add_line as add_chat_line
from black_bloc.chat import create_intent
from black_bloc.chat import seed_defaults as seed_chat
from black_bloc.chat_memory import Note as MemoryNote
from black_bloc.chat_memory import Profile as MemoryProfile
from black_bloc.chat_memory import save_profile
from black_bloc.cogs.community.birthdays import save_birthday
from black_bloc.cogs.community.polls import add_options as add_poll_options
from black_bloc.cogs.community.polls import (
    create_poll,
    options_of,
    record_vote,
    set_posted,
    set_recurrence,
)
from black_bloc.cogs.community.role_menus import add_option, create_menu, get_menu
from black_bloc.cogs.community.tempvoice import add_channel
from black_bloc.cogs.content.golive import set_link, set_optout, start_session
from black_bloc.cogs.content.raidtrain import create_train
from black_bloc.cogs.content.raidtrain import set_status as set_train_status
from black_bloc.cogs.content.youtube import YouTube
from black_bloc.cogs.content.youtube import set_link as set_youtube_link
from black_bloc.cogs.moderation.honeypot import record_hit
from black_bloc.cogs.moderation.modmail import add_message, create_ticket, set_ticket_place
from black_bloc.events import create_event
from black_bloc.golive import StreamInfo
from black_bloc.llm import ANTHROPIC, GROQ, Usage
from black_bloc.llm import MODEL as HAIKU
from black_bloc.llm import record as llm_record
from black_bloc.modcases import add_case, mark_case_void
from black_bloc.modmail import IN
from black_bloc.polls import next_occurrence
from black_bloc.requests import HOLD, IN_PROGRESS, OPEN, REVIEW, create_request
from black_bloc.requests import add_comment as add_request_comment
from black_bloc.requests import set_fields as set_request_fields
from black_bloc.requests import set_status as set_request_status
from black_bloc.youtube import Video

CONTRACT = Path(__file__).resolve().parents[2] / "site" / "mock" / "contract.json"
MEMBER_ID = 21
YT_CHANNEL = "UCsXVk37bltHxD1rDPwtNM8Q"
PING_MEMBER_ID = 22


class FakeFeed:
    """The uploads client, offline: the contract checks payload shapes, never YouTube."""

    keyed = False

    async def resolve(self, text):
        return (YT_CHANNEL, "Ada Makes")

    async def fetch_feed(self, channel_id, etag=None):
        return (200, None, [seed_video()])

    async def close(self):
        return None


def seed_video() -> Video:
    return Video(
        video_id="vidcontract",
        title="How the cookout runs",
        url="https://www.youtube.com/watch?v=vidcontract",
        published="2026-09-01T00:00:00+00:00",
        channel_id=YT_CHANNEL,
        author="Ada Makes",
    )


class FakeCog:
    """One loop-bearing cog, because /api/status reports nothing without one."""

    @tasks.loop(minutes=5)
    async def _sweep(self) -> None:
        return None

    def loop_health(self, name: str):
        return (datetime.now(UTC).isoformat(), None)


class FakeRaidTrains:
    """The raid-train cog's three side effects, without a Discord channel to post into."""

    @tasks.loop(minutes=5)
    async def sweep(self) -> None:
        return None

    last_sweep_ok_at = None
    last_sweep_error = None
    sweep_failures = 0

    def loop_health(self, name: str):
        return (datetime.now(UTC).isoformat(), None)

    async def publish_lineup(self, guild, train_id) -> None:
        return None

    async def _refresh_lineup(self, guild, train_id) -> None:
        return None

    async def cancel_train(self, guild, train, reason, actor) -> int:
        await set_train_status(self.db, train["id"], "cancelled", reason=reason)
        return 0


def contract() -> dict:
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


ROUTES = contract()["routes"]
IDS = [f"{route['method']} {route['path']}" for route in ROUTES]


def missing(found: dict, keys: list[str]) -> list[str]:
    return [key for key in keys if key not in found]


def check_rows(where: str, rows: list, keys: list[str], *, allow_empty: bool = False) -> None:
    assert isinstance(rows, list), f"{where} is {type(rows).__name__}, not a list"
    if not rows:
        assert allow_empty, f"{where} came back empty, so its row shape was never checked"
        return
    for row in rows:
        assert not missing(row, keys), f"{where} row is missing {missing(row, keys)}"


def check(where: str, payload, spec: dict) -> None:
    keys = spec.get("keys", [])
    shape = spec["shape"]
    if shape == "list":
        check_rows(where, payload, keys)
    elif shape == "map":
        assert isinstance(payload, dict) and payload, f"{where} came back empty"
        for value in payload.values():
            assert not missing(value, keys), f"{where} entry is missing {missing(value, keys)}"
    elif shape == "namespaces":
        assert isinstance(payload, dict)
        for namespace in spec["namespaces"]:
            assert namespace in payload, f"{where} has no {namespace} namespace"
            check_rows(f"{where}[{namespace}]", payload[namespace], keys)
        for namespace in spec["no_namespaces"]:
            assert namespace not in payload, (
                f"{where} still groups {namespace} on its own; it belongs in automod"
            )
    else:
        assert isinstance(payload, dict), f"{where} is {type(payload).__name__}, not an object"
        assert not missing(payload, keys), f"{where} is missing {missing(payload, keys)}"
    for field, row_keys in (spec.get("rows") or {}).items():
        if shape == "list":
            for row in payload:
                check_rows(f"{where}.{field}", row[field], row_keys)
        else:
            check_rows(f"{where}.{field}", payload[field], row_keys)
    for field, nested_keys in (spec.get("nested") or {}).items():
        found = payload[field]
        assert isinstance(found, dict), f"{where}.{field} is not an object"
        assert not missing(found, nested_keys), (
            f"{where}.{field} is missing {missing(found, nested_keys)}"
        )


async def make_request(
    db, guild_id: int, user_id: int, what: str, status: str, decided_by: int | None = None
) -> int:
    return await create_request(
        db,
        guild_id,
        user_id,
        what=what,
        why="the google doc nobody can find is where ideas go to die",
        due_on=None,
        status=status,
        decided_by=decided_by,
    )


async def make_poll(db, guild_id: int, question: str, status: str) -> int:
    poll_id = await create_poll(
        db,
        guild_id,
        MEMBER_ID,
        question=question,
        kind="single",
        surface="native",
        multi=False,
        anonymous=False,
        results="live",
        hours=24,
        channel_id=None,
        ping_role_id=None,
        status=status,
    )
    await add_poll_options(db, poll_id, ["Saturday", "Sunday"])
    return poll_id


@pytest.fixture
async def seeded(client, sign_in, web, guild, wf):
    """One of everything the contract's routes read, so no route answers empty."""
    wf.member(guild, MEMBER_ID, name="ada")
    wf.member(guild, 7, name="lead", staff=True)
    # F14: {member_id} is given a ping role below, so the POST needs somebody who has none —
    # otherwise it answers the 409 that says they already have one.
    wf.member(guild, PING_MEMBER_ID, name="namu")
    sign_in(client)
    db, guild_id = web.db, wf.GUILD_ID

    web.cogs["Contract"] = FakeCog()
    await web.store.set(guild_id, "events_create_scheduled", False, by=7)
    await web.store.set(guild_id, "rolemenu_mode", "on", by=7)
    await web.store.set(guild_id, "pings_mode", "on", by=7)
    await pings.set_fan_role(db, guild_id, MEMBER_ID, wf.PLAIN_ROLE_ID, 7)

    case_id = await add_case(
        db,
        guild_id,
        MEMBER_ID,
        "warn",
        moderator_id=7,
        reason="contract seed",
        mode="shadow",
        applied=False,
        actions=["warn"],
    )
    # A case already VOIDED, because /restore is only legal from there and every contract entry
    # runs against a fresh seed.
    voided_case_id = await add_case(
        db, guild_id, MEMBER_ID, "warn", moderator_id=7, reason="contract seed, voided"
    )
    await mark_case_void(db, voided_case_id, 7, "wrong member")
    starts = datetime.now(UTC) + timedelta(days=1)
    event_id = await create_event(
        db,
        guild_id,
        MEMBER_ID,
        title="Bloc night",
        description="come along",
        location="the park",
        starts_at=starts,
        finishes_at=starts + timedelta(hours=2),
    )
    ticket_id = await create_ticket(db, guild_id, MEMBER_ID, "channel")
    await set_ticket_place(db, ticket_id, wf.TEST_CHANNEL_ID, None)
    await add_message(db, ticket_id, MEMBER_ID, IN, content="are you there?")
    hit_id = await record_hit(
        db, guild_id, MEMBER_ID, wf.OTHER_CHANNEL_ID, 999, "buy my coins", "shadow", "would_ban"
    )
    await set_link(db, MEMBER_ID, "adastreams", "t-1")
    uploads = YouTube(web)
    uploads.client = FakeFeed()
    web.cogs["YouTube"] = uploads
    await set_youtube_link(db, MEMBER_ID, YT_CHANNEL, "@ada", "Ada Makes")
    await uploads._seed(MEMBER_ID, await uploads_link(db), [seed_video()], None)
    await set_optout(db, MEMBER_ID)
    await start_session(
        db,
        guild_id,
        MEMBER_ID,
        "presence",
        StreamInfo(url="https://twitch.tv/ada", game="Balatro", title="one more"),
        "on",
    )
    await save_birthday(db, guild_id, MEMBER_ID, 3, 4, None, "staff")
    await add_channel(db, wf.VOICE_CHANNEL_ID, guild_id, MEMBER_ID, wf.OTHER_CHANNEL_ID)
    await web.store.set(guild_id, "tempvoice_creator_ids", [wf.VOICE_CHANNEL_ID], by=7)
    client.post(
        "/api/rolemenus",
        json={"name": "contract", "title": "Contract", "mode": "multiple"},
    )
    client.put(
        "/api/rolemenus/contract",
        json={
            "title": "Contract",
            "mode": "multiple",
            "options": [{"role_id": str(wf.PLAIN_ROLE_ID), "label": "Member"}],
        },
    )
    client.post(
        "/api/rolemenus/contract/post", json={"channel_id": str(wf.TEST_CHANNEL_ID)}
    )
    client.put("/api/settings/poll_auto_thread", json={"value": True})
    client.post("/api/modmail/snippets", json={"name": "contract", "content": "hello"})
    client.post("/api/modmail/blocks", json={"user_id": str(MEMBER_ID)})
    await create_menu(
        db, guild_id, "runner", "Runner", None, "multiple", approval=True, expires_days=7
    )
    runner = await get_menu(db, guild_id, "runner")
    await add_option(db, runner["id"], wf.STAFF_ROLE_ID, "Runner", None)
    request_id = await grants.create_request(
        db, guild_id, runner["id"], MEMBER_ID, wf.STAFF_ROLE_ID
    )
    poll_id = await make_poll(db, guild_id, "Best day for the cookout?", "open")
    await set_posted(
        db,
        poll_id,
        channel_id=wf.TEST_CHANNEL_ID,
        message_id=830001,
        finishes_at=datetime.now(UTC) + timedelta(hours=20),
    )
    await record_vote(db, poll_id, (await options_of(db, poll_id))[0]["id"], MEMBER_ID)
    poll_request_id = await make_poll(db, guild_id, "Movie night?", "pending_review")
    recurrence_id = await make_poll(db, guild_id, "Are we running tonight?", "recurring")
    await set_recurrence(
        db,
        recurrence_id,
        "daily",
        "09:00",
        "America/Phoenix",
        next_occurrence("daily", "09:00", "America/Phoenix").isoformat(),
    )
    await seed_chat(db, guild_id, by=7)
    chat_intent_id = await create_intent(
        db, guild_id, "cookout_hours", ["when is the cookout"], by=7
    )
    chat_line_id = await add_chat_line(db, chat_intent_id, "Doors at six, {name}.", by=7)
    # 14b. {chat_section_id} is a STAFF note, the only kind the write entries may touch; the
    # server-written one beside it is what makes the list's two sources both real.
    chat_section_id = await knowledge.add_section(
        db, guild_id, "Cookout hours", "Doors at six, food at seven.", tag="cookout", by=7
    )
    await knowledge.add_section(
        db, guild_id, "Channels", "general, cookout-planning", source=knowledge.SERVER
    )
    # One paid turn and one free one, so /api/costs' model rows are never an empty list —
    # an empty one there would mean the ledger query broke, not that nothing was spent.
    await llm_record(
        db,
        guild_id=guild_id,
        user_id=MEMBER_ID,
        turn="contract-haiku",
        provider=ANTHROPIC,
        model=HAIKU,
        tier="important",
        usage=Usage(input_tokens=1200, output_tokens=300),
    )
    await llm_record(
        db,
        guild_id=guild_id,
        user_id=MEMBER_ID,
        turn="contract-groq",
        provider=GROQ,
        model="llama-3.3-70b-versatile",
        tier="simple",
        usage=Usage(input_tokens=400, output_tokens=90),
    )
    # {feature_request_id} is the signed-in staffer's own OPEN row, so /api/requests/mine
    # is never empty and the staff moves have something to move; {member_request_id} is
    # somebody else's, also open. {held_request_id} is already on hold, because /resume is
    # only legal from there and every route runs against a fresh seed. The mock seeds the
    # same three as 25, 30 and 20.
    feature_request_id = await make_request(
        db, guild_id, 7, "A requests board on the site", OPEN
    )
    await add_request_comment(db, feature_request_id, 7, "Looking at this one this week.")
    member_request_id = await make_request(
        db, guild_id, MEMBER_ID, "Karaoke night", OPEN
    )
    held_request_id = await make_request(
        db, guild_id, MEMBER_ID, "Role menu descriptions", OPEN
    )
    await set_request_status(
        db,
        held_request_id,
        HOLD,
        decided_by=7,
        decline_reason="waiting on the role menu rewrite",
        was=OPEN,
    )
    # Third pass: {review_request_id} is already ready to check, because /accept and
    # /sendback are only legal from there, and {progress_request_id} is being worked on,
    # which is where /ready is legal. The mock seeds the same two as 11 and 12.
    review_request_id = await make_request(
        db, guild_id, MEMBER_ID, "Threads should not get an answer", OPEN
    )
    await set_request_fields(
        db,
        review_request_id,
        built="A chat_reply_in_threads setting, on by default.",
        how_to_test="Turn it off, @-mention the bot in a thread, watch it stay quiet.",
    )
    await set_request_status(
        db, review_request_id, REVIEW, decided_by=7, was=IN_PROGRESS, ready_by=7
    )
    progress_request_id = await make_request(
        db, guild_id, MEMBER_ID, "Honeypot should say what it caught", OPEN
    )
    await set_request_status(
        db, progress_request_id, IN_PROGRESS, decided_by=7, was=OPEN
    )
    # Phase 17: one profile, so GET /api/chat/memory has a row shape to read and DELETE has
    # something to clear. Preferences only, and one of them scoped to a DM.
    await save_profile(
        db,
        MEMBER_ID,
        guild_id,
        MemoryProfile(
            call_me="Sky",
            notes=(
                MemoryNote("likes short answers", "server", "2026-09-02T00:00:00+00:00"),
                MemoryNote("keep it simple", "dm", "2026-09-02T00:00:00+00:00"),
            ),
            threads=(
                MemoryNote("was asking about the cookout", "server", "2026-09-02T00:00:00+00:00"),
            ),
            turns_seen=6,
            created_at="2026-09-01T00:00:00+00:00",
            updated_at="2026-09-02T00:00:00+00:00",
        ),
    )
    raid_trains = FakeRaidTrains()
    raid_trains.db = db
    web.cogs["RaidTrains"] = raid_trains
    raid_train_id = await create_train(
        db,
        guild_id,
        7,
        title="Saturday raid train",
        description="Everyone welcome.",
        starts_at=datetime.now(UTC) + timedelta(days=2),
        slot_minutes=60,
        slot_count=3,
    )
    # Phase 19: one form with questions and somebody waiting on it, plus an empty second
    # form for the DELETE entry — a form with an application waiting refuses to be deleted.
    await web.store.set(guild_id, "applications_mode", "on", by=7)
    application_form_id = client.post(
        "/api/applications/forms",
        json={
            "name": "twitch-team",
            "title": "Twitch Team",
            "description": "join the Team",
            "role_id": str(wf.PLAIN_ROLE_ID),
        },
    ).json()["id"]
    client.put(
        f"/api/applications/forms/{application_form_id}/questions",
        json={"questions": [{"label": "Twitch handle"}, {"label": "Why the Team"}]},
    )
    empty_form_id = client.post(
        "/api/applications/forms",
        json={"name": "mod-team", "title": "Mod Team", "role_id": str(wf.PLAIN_ROLE_ID)},
    ).json()["id"]
    # Every form in the list needs a question, or the list entry's row check never runs.
    client.put(
        f"/api/applications/forms/{empty_form_id}/questions",
        json={"questions": [{"label": "Why do you want to help moderate", "style": "long"}]},
    )
    application_id = await applications.create_application(
        db,
        guild_id,
        application_form_id,
        MEMBER_ID,
        applications.answers_json([("Twitch handle", "ada"), ("Why the Team", "the vibes")]),
    )
    # The no-role pass: a form that keeps a LIST, with one member approved onto it, so the
    # roster entry has a row and the remove entry has somebody to take off.
    listed_form_id = client.post(
        "/api/applications/forms",
        json={"name": "stream-team", "title": "Stream Team"},
    ).json()["id"]
    client.put(
        f"/api/applications/forms/{listed_form_id}/questions",
        json={"questions": [{"label": "Twitch handle"}]},
    )
    listed_application_id = await applications.create_application(
        db,
        guild_id,
        listed_form_id,
        MEMBER_ID,
        applications.answers_json([("Twitch handle", "ada")]),
    )
    await applications.decide_application(
        db, listed_application_id, grants.APPROVED, decided_by=7
    )
    grant_id = await grants.add_grant(
        db,
        guild_id,
        MEMBER_ID,
        wf.PLAIN_ROLE_ID,
        grants.STAFF,
        granted_by=7,
        until=grants.expires_at(7),
    )
    return {
        "member_id": str(MEMBER_ID),
        "case_id": str(case_id),
        "voided_case_id": str(voided_case_id),
        "event_id": str(event_id),
        "ticket_id": str(ticket_id),
        "hit_id": str(hit_id),
        "test_channel_id": str(wf.TEST_CHANNEL_ID),
        "lobby_channel_id": str(wf.VOICE_CHANNEL_ID),
        "room_channel_id": str(wf.VOICE_CHANNEL_ID),
        "plain_role_id": str(wf.PLAIN_ROLE_ID),
        "request_id": str(request_id),
        "grant_id": str(grant_id),
        "poll_id": str(poll_id),
        "poll_request_id": str(poll_request_id),
        "poll_recurrence_id": str(recurrence_id),
        "chat_intent_id": str(chat_intent_id),
        "chat_line_id": str(chat_line_id),
        "chat_section_id": str(chat_section_id),
        "feature_request_id": str(feature_request_id),
        "member_request_id": str(member_request_id),
        "held_request_id": str(held_request_id),
        "review_request_id": str(review_request_id),
        "progress_request_id": str(progress_request_id),
        "raid_train_id": str(raid_train_id),
        "ping_member_id": str(PING_MEMBER_ID),
        "application_form_id": str(application_form_id),
        "empty_form_id": str(empty_form_id),
        "application_id": str(application_id),
        "listed_form_id": str(listed_form_id),
        "listed_application_id": str(listed_application_id),
    }


async def uploads_link(db):
    from black_bloc.cogs.content.youtube import get_link as get_youtube_link

    return await get_youtube_link(db, MEMBER_ID)


def fill(text: str, ids: dict) -> str:
    for name, value in ids.items():
        text = text.replace("{" + name + "}", value)
    return text


@pytest.mark.parametrize("spec", ROUTES, ids=IDS)
async def test_every_route_answers_with_the_keys_the_pages_read(client, seeded, spec):
    path = fill(spec["path"], seeded)
    body = spec.get("body")
    if isinstance(body, dict):
        body = json.loads(fill(json.dumps(body), seeded))
    response = client.request(spec["method"], path, json=body)
    where = f"{spec['method']} {path}"
    assert response.status_code == 200, f"{where} answered {response.status_code}: {response.text}"
    check(where, response.json(), spec)


def test_the_moderation_settings_all_live_in_the_automod_namespace(web, wf):
    """modlog and mod were one-key namespaces of their own; they are moderation keys."""
    found = grouped(web.store, wf.GUILD_ID)
    automod = {row["key"] for row in found["automod"]}

    assert {"modlog_channel_id", "mod_dm_on_action"} <= automod
    assert not {"modlog", "mod"} & set(found)


async def test_every_write_leaves_the_action_kind_the_audit_tab_filters_on(
    client, seeded, web, wf
):
    """The audit tab shows `web.` and nothing else, so every write route must spell it that way."""
    client.put("/api/settings/birthday_show_age", json={"value": True})
    client.post("/api/mod/warn", json={"user_id": seeded["member_id"], "reason": "contract"})
    client.post("/api/modmail/snippets", json={"name": "second", "content": "hi"})
    client.post(
        f"/api/rolemenus/requests/{seeded['request_id']}/deny", json={"reason": "contract"}
    )
    client.delete(f"/api/roles/grants/{seeded['grant_id']}")

    kinds = [kind for kind in await wf.kinds_in(web.db) if kind.startswith("web")]

    assert kinds, "no write left a web.* line at all"
    known = set(contract()["action_kinds"])
    assert all(kind.startswith("web.") for kind in kinds), kinds
    assert set(kinds) <= known, f"unlisted kinds: {sorted(set(kinds) - known)}"
