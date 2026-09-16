from __future__ import annotations

import hashlib
import json
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import pytest_asyncio
from discord.ext import tasks

from black_bloc import applications, guides, knowledge, pings, posts
from black_bloc import rolegrants as grants
from black_bloc.api.auth import SESSION_COOKIE, SESSION_TTL_SECONDS, sign_session
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
from black_bloc.events import WHERE_OTHER, Where, create_event, set_review
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


async def sign_in_staff(client, db, wf, uid: int = 7) -> None:
    """The staff cookie without the `sign_in` fixture, which a module-scoped seed cannot ask for."""
    at = datetime.now(UTC)
    sid = f"contract-{uid}"
    await db.conn.execute(
        "INSERT OR REPLACE INTO sessions(id, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
        (sid, uid, at.isoformat(), (at + timedelta(seconds=SESSION_TTL_SECONDS)).isoformat()),
    )
    await db.conn.commit()
    client.cookies.set(
        SESSION_COOKIE,
        sign_session(
            wf.SECRET,
            {
                "uid": str(uid),
                "name": "Mod",
                "avatar": None,
                "staff": True,
                "sid": sid,
                "exp": int(time.time()) + SESSION_TTL_SECONDS,
            },
        ),
    )


def seed_members(guild, wf) -> None:
    wf.member(guild, MEMBER_ID, name="ada")
    wf.member(guild, 7, name="lead", staff=True)
    # F14: {member_id} is given a ping role below, so the POST needs somebody who has none —
    # otherwise it answers the 409 that says they already have one.
    wf.member(guild, PING_MEMBER_ID, name="namu")


async def seed_world(client, web, guild, wf) -> dict:
    """One of everything the contract's routes read, so no route answers empty."""
    seed_members(guild, wf)
    db, guild_id = web.db, wf.GUILD_ID
    await sign_in_staff(client, db, wf)

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
    # A case already VOIDED, because /restore is only legal from there. The seed is built ONCE
    # per module now, so this id is spent by the single entry that restores it and by nothing else.
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
        where=Where(WHERE_OTHER, None, "the park"),
        starts_at=starts,
        finishes_at=starts + timedelta(hours=2),
    )
    # The room the events page's Remove-its-room entry acts on. The guild is rebuilt for every
    # entry, so the channel it deletes comes back with it.
    await set_review(db, event_id, wf.OTHER_CHANNEL_ID, None)
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
    # only legal from there and one entry owns it for the life of the module seed. The mock
    # seeds the same three as 25, 30 and 20.
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
    # Third pass: {review_request_id} is already ready to check, because /sendback and
    # /accept are only legal from there, and {progress_request_id} is being worked on,
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
    # Guides (G1): the seventeen Black Bloc ships with, one written here so DELETE has
    # something only staff made, and one shot already stale so /api/guides/stale is never
    # empty. The mock seeds the same shapes as golive-announce and house-rules.
    await guides.seed_guides(db, guild_id)
    scratch = await guides.create_guide(
        db,
        guild_id,
        slug="house-rules",
        title="Write the house rules down",
        goal="A guide staff wrote here rather than one Black Bloc ships with.",
        audience="staff",
        feature="core",
        published=False,
        by=7,
    )
    await guides.put_steps(
        db,
        scratch,
        [{"do_text": "Press **Edit this guide**.", "expect_text": "Every line becomes a box."}],
    )
    # Posts (§C4): the one Black Bloc ships with, pointed at a channel this guild HAS so the
    # publish entry reaches it; one already posted so the takedown entry has something to
    # remove; and one staff wrote here, which is the only kind DELETE takes.
    await posts.seed_posts(web, guild)
    welcome = await posts.get_post(db, guild_id, "welcome")
    await posts.set_post_fields(db, int(welcome["id"]), channel_id=wf.TEST_CHANNEL_ID)
    posted_id = await posts.create_post(
        db,
        guild_id,
        slug="opening-hours",
        title="When staff are around",
        body="\n".join(
            ["**Staff hours**", "> Somebody is usually around between 6pm and 11pm."]
        ),
        channel_id=wf.TEST_CHANNEL_ID,
        style=posts.EMBED,
        pin=False,
        by=7,
    )
    await posts.publish_post(
        web, guild, await posts.get_post_by_id(db, posted_id), guild.get_member(7)
    )
    await posts.set_post_fields(db, posted_id, body="Edited since it was posted.")
    await posts.create_post(
        db,
        guild_id,
        slug="scratch-post",
        title="A post staff wrote here",
        body="",
        by=7,
    )
    golive_guide = await guides.get_guide(db, guild_id, "golive-announce")
    first_step = (await guides.steps_of(db, golive_guide["id"]))[0]
    shot = await guides.save_media(
        web,
        guild_id,
        int(golive_guide["id"]),
        b"\x89PNG\r\n\x1a\n" + b"\x00" * 8 + (1280).to_bytes(4, "big")
        + (720).to_bytes(4, "big"),
        step_id=int(first_step["id"]),
        caption="the /golive panel",
        shot_release="v110",
        shot_by=7,
    )
    await db.conn.execute(
        "UPDATE guide_steps SET media_id = ? WHERE id = ?", (shot, int(first_step["id"]))
    )
    await db.conn.execute(
        "UPDATE guide_media SET stale = 1, stale_since = ? WHERE id = ?",
        (datetime.now(UTC).isoformat(), shot),
    )
    await db.conn.commit()
    # Wave 5: one finished self-test run with a check row and a card still waiting to be
    # deleted, so GET /api/selftest/{id} has a shape and the purge entry has something to do.
    selftest_run_id = await seed_selftest_run(db, guild_id, wf.TEST_CHANNEL_ID)
    # GET /api/chat/personality fills the trope pool the first time anybody reads it. The seed
    # takes that first read, so no contract entry is the one that writes on a GET.
    client.get("/api/chat/personality")
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
        "selftest_run_id": str(selftest_run_id),
        "guide_slug": "golive-announce",
        "scratch_guide_slug": "house-rules",
        "post_slug": "welcome",
        "posted_post_slug": "opening-hours",
        "scratch_post_slug": "scratch-post",
    }


class Seed:
    """The module's one seeded database and guild, plus what puts both back between entries."""

    def __init__(self, web, wf, ids: dict, rows: dict, sent: list, cogs: dict) -> None:
        self.web = web
        self.wf = wf
        self.ids = ids
        self.rows = rows
        self.sent = sent
        self.cogs = cogs

    async def rewind(self) -> None:
        # Three of the seed's marks are not rows: its members, the message the role menu was
        # posted as, and its cogs. Every other api fixture resets the shared bot, so the seed
        # puts all three back rather than assuming it ran last.
        guild = self.wf.Guild()
        self.wf.reset_bot(self.web, guild)
        seed_members(guild, self.wf)
        for kwargs in self.sent:
            await guild.get_channel(self.wf.TEST_CHANNEL_ID).send(**kwargs)
        self.web.cogs.update(self.cogs)
        await self.wf.put(self.web.db, self.rows)
        await self.web.store.load()


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def contract_seed(module_client, module_web, wf):
    """Seeded once for the whole file: ~430 ms of writes, one schema build, one FastAPI app."""
    guild = wf.Guild()
    wf.reset_bot(module_web, guild)
    ids = await seed_world(module_client, module_web, guild, wf)
    sent = [dict(one.kwargs) for one in guild.get_channel(wf.TEST_CHANNEL_ID).messages]
    rows = await wf.take(module_web.db)
    return Seed(module_web, wf, ids, rows, sent, dict(module_web.cogs))


@pytest.fixture
async def seeded(contract_seed):
    """Every entry starts on the seed exactly as written; only the building of it is shared."""
    await contract_seed.rewind()
    return contract_seed.ids


@pytest.fixture
async def fresh_seeded(fresh_client, fresh_web, guild, wf):
    """A database, app and seed of its own, for the entry that counts the `web.*` rows."""
    return await seed_world(fresh_client, fresh_web, guild, wf)


READ_ONLY = "GET"


async def snapshot(db) -> dict[str, str]:
    """One hash per table, so a read that writes is named with the tables it touched."""
    cur = await db.conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' "
        "ORDER BY name"
    )
    tables = [row["name"] for row in await cur.fetchall()]
    found: dict[str, str] = {}
    for table in tables:
        cur = await db.conn.execute(f"SELECT * FROM {table}")
        rows = sorted(repr(tuple(row)) for row in await cur.fetchall())
        found[table] = hashlib.sha256("\n".join(rows).encode()).hexdigest()
    return found


async def seed_selftest_run(db, guild_id: int, channel_id: int) -> int:
    """One finished run, one check row in the log, one card still waiting to be deleted."""
    at = datetime.now(UTC).isoformat()
    cur = await db.conn.execute(
        "INSERT INTO selftest_runs(guild_id, started_at, finished_at, ok, failed, posted, via, "
        "actor_id) VALUES (?, ?, ?, 1, 0, 1, 'website', 7)",
        (guild_id, at, at),
    )
    run_id = int(cur.lastrowid)
    await db.conn.execute(
        "INSERT INTO action_log(guild_id, at, kind, details) VALUES (?, ?, ?, ?)",
        (
            guild_id,
            at,
            "web.selftest.check",
            json.dumps(
                {
                    "run_id": run_id,
                    "name": "config.log_channel_id",
                    "feature": "core",
                    "ok": True,
                    "detail": "#blackbloc-logs (500); view_channel",
                    "via": "website",
                }
            ),
        ),
    )
    await db.conn.execute(
        "INSERT INTO selftest_messages(run_id, guild_id, channel_id, message_id, posted_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (run_id, guild_id, channel_id, 830042, at),
    )
    await db.conn.commit()
    return run_id


async def uploads_link(db):
    from black_bloc.cogs.content.youtube import get_link as get_youtube_link

    return await get_youtube_link(db, MEMBER_ID)


def fill(text: str, ids: dict) -> str:
    for name, value in ids.items():
        text = text.replace("{" + name + "}", value)
    return text


@pytest.mark.parametrize("spec", ROUTES, ids=IDS)
async def test_every_route_answers_with_the_keys_the_pages_read(
    module_client, module_web, seeded, spec
):
    path = fill(spec["path"], seeded)
    body = spec.get("body")
    if isinstance(body, dict):
        body = json.loads(fill(json.dumps(body), seeded))
    where = f"{spec['method']} {path}"
    reading = spec["method"] == READ_ONLY
    before = await snapshot(module_web.db) if reading else {}
    response = module_client.request(spec["method"], path, json=body)
    assert response.status_code == 200, f"{where} answered {response.status_code}: {response.text}"
    check(where, response.json(), spec)
    if reading:
        after = await snapshot(module_web.db)
        dirtied = sorted(name for name, digest in after.items() if before.get(name) != digest)
        assert not dirtied, (
            f"{where} is a read, but it changed {dirtied} — the seed the rest of the file "
            "shares is now dirty, so scope it back or make the route stop writing"
        )


def test_the_contracts_settings_block_is_the_registry_and_not_a_second_copy():
    """One home. `site/mock/check.mjs` reads the same block, so a bound invented in the mock,
    or one added to the registry and not mirrored, fails one half or the other by name."""
    from black_bloc.settings_store import CORE_KEYS, KEY_MAX, KEY_MIN

    block = contract()["settings"]

    assert block["core_keys"] == sorted(CORE_KEYS)
    assert block["min"] == {key: KEY_MIN[key] for key in sorted(KEY_MIN)}
    assert block["max"] == {key: KEY_MAX[key] for key in sorted(KEY_MAX)}


def test_the_real_settings_index_bounds_exactly_what_the_contract_says(client, sign_in, web, wf):
    """The other half of the same guard, against the real router rather than the mock."""
    sign_in(client)
    block = contract()["settings"]
    rows = {
        row["key"]: row | {"namespace": namespace}
        for namespace, found in client.get("/api/settings").json().items()
        for row in found
    }

    core = sorted(key for key, row in rows.items() if row["namespace"] == "core")
    assert core == sorted([*block["core_keys"], "core_log_level"])
    assert {key: row["max"] for key, row in rows.items() if "max" in row} == block["max"]
    assert {key: row["min"] for key, row in rows.items() if "min" in row} == block["min"]


def test_the_moderation_settings_all_live_in_the_automod_namespace(web, wf):
    """modlog and mod were one-key namespaces of their own; they are moderation keys."""
    found = grouped(web.store, wf.GUILD_ID)
    automod = {row["key"] for row in found["automod"]}

    assert {"modlog_channel_id", "mod_dm_on_action"} <= automod
    assert not {"modlog", "mod"} & set(found)


async def test_every_write_leaves_the_action_kind_the_audit_tab_filters_on(
    fresh_client, fresh_seeded, fresh_web, wf
):
    """The audit tab shows `web.` and nothing else, so every write route must spell it that way."""
    client, web, seeded = fresh_client, fresh_web, fresh_seeded
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
