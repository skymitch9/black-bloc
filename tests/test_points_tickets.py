# ruff: noqa: F401, F811
import json

import discord
import pytest

from black_bloc import points_store as store_
from black_bloc import points_tickets as tickets
from black_bloc.cogs.moderation import modmail as modmail_cog
from black_bloc.config import load_settings
from black_bloc.logkinds import VIA_WEBSITE
from black_bloc.modmail import APPROVE_MOVE, CARD_CLOSE_MOVE, REJECT_MOVE, SOURCE_POINTS
from black_bloc.points.model import APPROVED, PENDING, REJECTED, REMOVED
from black_bloc.settings_store import THREAD_MODE, SettingsStore
from tests.cogs.moderation.test_modmail import (
    CATEGORY,
    GUILD,
    LEAD,
    LOG_CHANNEL,
    STAFF_ROLE,
    TEST_CHANNEL,
    USER,
    FakeBot,
    FakeCategory,
    FakeGuild,
    FakeInteraction,
    FakeRole,
    FakeText,
    FakeUser,
)

SPEED = 333
REHEARSAL = 444
VERIFIER = 556
VERA = 9
PROOF = "https://youtu.be/abc123"
GIVEN = {
    "game": "Celeste",
    "category": "Any%",
    "time": "30:00",
    "proof_url": PROOF,
    "note": "",
}


@pytest.fixture
async def bot(db, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    settings = load_settings(_env_file=None)
    store = SettingsStore(db, settings)
    await store.load()
    for key, value in (
        ("log_channel_id", LOG_CHANNEL),
        ("modmail_enabled", True),
        ("modmail_mode", THREAD_MODE),
        ("modmail_log_channel_id", LOG_CHANNEL),
        ("staff_channel_id", TEST_CHANNEL),
        ("points_channel_id", SPEED),
        ("shadow_channel_id", REHEARSAL),
        ("points_verifier_role_id", VERIFIER),
    ):
        await store.set(GUILD, key, value)
    guild = FakeGuild()
    guild.roles = [FakeRole(STAFF_ROLE, "Lead"), FakeRole(VERIFIER, "Mentor")]
    guild.get_role = lambda role_id: next((r for r in guild.roles if r.id == role_id), None)
    guild.channels[CATEGORY] = FakeCategory()
    guild.add(FakeText(LOG_CHANNEL, name="log"))
    staff = guild.add(FakeText(TEST_CHANNEL, name="staff"))
    staff.visible_to = {STAFF_ROLE}
    guild.add(FakeText(SPEED, name="speed-and-pbs"))
    guild.add(FakeText(REHEARSAL, name="welcome-test"))
    made = FakeBot(db, store, settings, guild)
    try:
        yield made
    finally:
        modmail_cog.cancel_cards(made)


def person(bot, user_id, name, *roles, manage=False):
    user = FakeUser(bot.guild, user_id=user_id, display_name=name, roles=roles, manage_guild=manage)
    bot.users[user.id] = user
    return user


@pytest.fixture
def ada(bot):
    return person(bot, USER, "Ada")


@pytest.fixture
def lead(bot):
    return person(bot, LEAD, "Meg", STAFF_ROLE, manage=True)


@pytest.fixture
def vera(bot):
    return person(bot, VERA, "Vera", VERIFIER)


async def kinds(db, like="%"):
    cur = await db.conn.execute(
        "SELECT kind FROM action_log WHERE kind LIKE ? ORDER BY id", (like,)
    )
    return [row["kind"] for row in await cur.fetchall()]


async def details(db, kind):
    cur = await db.conn.execute(
        "SELECT details FROM action_log WHERE kind = ? ORDER BY id DESC LIMIT 1", (kind,)
    )
    row = await cur.fetchone()
    return json.loads(row["details"]) if row else None


async def sent_in(bot, ada, **given):
    outcome = await tickets.submit(bot, bot.guild, ada, {**GIVEN, **given})
    ticket = await modmail_cog.open_ticket_for(bot.db, GUILD, ada.id)
    return outcome, ticket


async def card_of(bot, ticket):
    modmail_cog.cancel_cards(bot)
    return await modmail_cog.refresh_card(bot, bot.guild, ticket["id"])


async def press(bot, who, card, label):
    view = card.kwargs["view"]
    item = next(one for one in view.children if one.item.label == label)
    interaction = FakeInteraction(bot, who, message=card)
    await item.callback(interaction)
    return interaction


def thread_of(bot, ticket):
    return bot.guild.threads[ticket["thread_id"]]


async def test_a_run_opens_a_ticket_in_the_members_name_and_dms_nobody(bot, ada, db):
    outcome, ticket = await sent_in(bot, ada)

    assert outcome.ok and outcome.message.startswith("Your **Celeste** run (30:00) is in.")
    assert ticket["source"] == SOURCE_POINTS and ticket["user_id"] == ada.id
    run = await store_.run_by_ticket(db, GUILD, ticket["id"])
    assert run["state"] == PENDING and run["ticket_id"] == ticket["id"]
    assert ada.dms == []
    first = (await modmail_cog.ticket_messages(db, ticket["id"]))[0]
    assert first["author_id"] == ada.id
    assert first["content"].startswith("**Run: Celeste — 30:00**\n**Game:** Celeste\n")
    assert f"**Proof:** {PROOF}" in first["content"] and "**Note:** —" in first["content"]
    said = [one.content for one in thread_of(bot, ticket).messages]
    assert PROOF in said
    logged = await kinds(db)
    assert "points.submitted" in logged
    assert "modmail.opened" not in logged
    assert (await details(db, "points.submitted"))["ticket"] == ticket["id"]


async def test_a_bad_time_is_refused_before_any_ticket_is_made(bot, ada, db):
    outcome, ticket = await sent_in(bot, ada, time="soon")

    assert not outcome.ok and outcome.code == "bad_time"
    assert ticket is None
    cur = await db.conn.execute("SELECT COUNT(*) AS n FROM modmail_tickets")
    assert (await cur.fetchone())["n"] == 0


async def test_a_second_run_waits_for_the_first_in_words(bot, ada, db):
    await sent_in(bot, ada)

    again, _ = await sent_in(bot, ada, game="Hades")

    assert not again.ok and again.code == "run_waiting"
    assert again.message.startswith("Your **Celeste** run is still waiting for staff")
    assert len(await store_.runs(db, GUILD, limit=-1)) == 1


async def test_an_open_ordinary_ticket_holds_a_run_back_in_words(bot, ada, db):
    await modmail_cog.open_a_ticket(bot, bot.guild, ada, source="panel", text="hello")

    outcome, _ = await sent_in(bot, ada)

    assert not outcome.ok and outcome.code == "already_open"
    assert "already have a ticket open with staff" in outcome.message


async def test_modmail_switched_off_refuses_a_run_in_points_words(bot, ada):
    await bot.store.set(GUILD, "modmail_enabled", False)

    outcome, ticket = await sent_in(bot, ada)

    assert not outcome.ok and outcome.code == "disabled" and ticket is None
    assert outcome.message.startswith("Runs reach staff through modmail")


async def test_the_card_of_a_run_carries_approve_and_reject_and_no_send_to(bot, ada):
    _, ticket = await sent_in(bot, ada)

    card = await card_of(bot, ticket)

    labels = [one.item.label for one in card.kwargs["view"].children]
    assert labels == ["Reply", "Reply as Staff", "Private note", "Close…", "Approve", "Reject…"]
    assert (
        "**run** — Celeste (Any%) · 30:00 · waiting for staff" in card.kwargs["embed"].description
    )


async def test_close_is_refused_in_words_while_the_run_waits(bot, ada, lead, db):
    _, ticket = await sent_in(bot, ada)
    card = await card_of(bot, ticket)

    pressed = await press(bot, lead, card, CARD_CLOSE_MOVE.label)

    assert pressed.response.modals == []
    assert pressed.sent.startswith("This run is still waiting for a decision")
    raced = FakeInteraction(bot, lead)
    await modmail_cog.run_card_close(raced, ticket["id"], "done", False)
    assert raced.sent.startswith("This run is still waiting for a decision")
    assert (await modmail_cog.get_ticket(db, ticket["id"]))["status"] == "open"


async def test_approve_on_the_card_counts_the_run_closes_the_ticket_and_rehearses(
    bot, ada, lead, db
):
    _, ticket = await sent_in(bot, ada)
    card = await card_of(bot, ticket)

    pressed = await press(bot, lead, card, APPROVE_MOVE.label)

    run = await store_.run_by_ticket(db, GUILD, ticket["id"])
    assert run["state"] == APPROVED and run["xp"] == 100 and run["speedpoints"] == 10
    closed = await modmail_cog.get_ticket(db, ticket["id"])
    assert closed["status"] == "closed" and closed["close_reason"].startswith("Approved Ada's")
    assert thread_of(bot, ticket).archived is True
    assert pressed.sent.startswith("Approved Ada's **Celeste** run (30:00)")
    assert "points_mode is **shadow**" in pressed.sent
    assert ada.dms == []
    posted = bot.guild.channels[REHEARSAL].messages
    assert len(posted) == 1 and posted[0].content.startswith("Rehearsal")
    assert posted[0].kwargs["embed"].description == (
        "Ada is in the top 10 at #1 with 10 speedpoints."
    )
    assert bot.guild.channels[SPEED].messages == []
    logged = await kinds(db, "points.%")
    assert logged == [
        "points.submitted",
        "points.approved",
        "points.would_announce",
        "points.would_dm",
    ]
    decision = thread_of(bot, ticket).messages[-1]
    assert decision.content.startswith("Approved Ada's")
    assert [one.item.label for one in decision.kwargs["view"].children] == [tickets.REMOVE_LABEL]


async def test_approve_while_on_posts_the_top_and_dms_the_closed_ticket_plus_the_points(
    bot, ada, lead, db
):
    await bot.store.set(GUILD, "points_mode", "on")
    await bot.store.set(GUILD, "points_ping_role_id", 777)
    _, ticket = await sent_in(bot, ada)
    card = await card_of(bot, ticket)

    await press(bot, lead, card, APPROVE_MOVE.label)

    [dm] = ada.dms
    assert dm["content"].startswith("Your modmail ticket on **Black in a Flash!** has been closed.")
    assert dm["content"].endswith(
        "Your **Celeste** run (30:00) is approved — 100 XP and 10 speedpoints."
    )
    [post] = bot.guild.channels[SPEED].messages
    assert post.content == "<@&777>"
    assert [role.id for role in post.kwargs["allowed_mentions"].roles] == [777]
    assert post.kwargs["allowed_mentions"].everyone is False
    assert bot.guild.channels[REHEARSAL].messages == []
    assert "points.top_changed" in await kinds(db)


async def test_reject_asks_a_reason_and_the_member_is_told_it(bot, ada, lead, db):
    await bot.store.set(GUILD, "points_mode", "on")
    _, ticket = await sent_in(bot, ada)
    card = await card_of(bot, ticket)

    pressed = await press(bot, lead, card, REJECT_MOVE.label)
    modal = pressed.response.modals[-1]
    modal.reason._value = "no timer on screen"
    answered = FakeInteraction(bot, lead)
    await modal.on_submit(answered)

    run = await store_.run_by_ticket(db, GUILD, ticket["id"])
    assert run["state"] == REJECTED and run["reason"] == "no timer on screen"
    closed = await modmail_cog.get_ticket(db, ticket["id"])
    assert closed["status"] == "closed"
    assert closed["close_reason"] == "Rejected Ada's **Celeste** run (30:00). — no timer on screen"
    assert [one["content"] for one in ada.dms] == [
        "Your **Celeste** run (30:00) was not approved. Staff said: no timer on screen"
    ]
    assert answered.sent.startswith("Rejected Ada's **Celeste** run")
    assert thread_of(bot, ticket).messages[-1].kwargs.get("view") is None


async def test_a_member_cannot_approve_and_a_verifier_may_but_not_their_own(bot, ada, vera, db):
    _, ticket = await sent_in(bot, ada)
    card = await card_of(bot, ticket)

    refused = await press(bot, ada, card, APPROVE_MOVE.label)
    assert refused.sent == "Approving runs is for staff and **Mentor**, so nothing was done."
    refused = await press(bot, ada, card, REJECT_MOVE.label)
    assert refused.response.modals == []

    await bot.store.set(GUILD, "modmail_enabled", True)
    own_outcome = await tickets.submit(bot, bot.guild, vera, GIVEN)
    own_ticket = await modmail_cog.open_ticket_for(db, GUILD, vera.id)
    assert own_outcome.ok
    own = await press(bot, vera, await card_of(bot, own_ticket), APPROVE_MOVE.label)
    assert own.sent == "You submitted that run, so someone else approves it."
    assert (await store_.run_by_ticket(db, GUILD, own_ticket["id"]))["state"] == PENDING

    await press(bot, vera, card, APPROVE_MOVE.label)
    assert (await store_.run_by_ticket(db, GUILD, ticket["id"]))["state"] == APPROVED


async def test_remove_on_the_decided_run_takes_it_off_and_dms_the_reason(bot, ada, lead, db):
    await bot.store.set(GUILD, "points_mode", "on")
    _, ticket = await sent_in(bot, ada)
    await press(bot, lead, await card_of(bot, ticket), APPROVE_MOVE.label)
    decision = thread_of(bot, ticket).messages[-1]
    button = decision.kwargs["view"].children[0]

    refused = FakeInteraction(bot, ada, message=decision)
    await button.callback(refused)
    assert refused.response.modals == [] and "staff only" in refused.sent

    pressed = FakeInteraction(bot, lead, message=decision)
    await button.callback(pressed)
    modal = pressed.response.modals[-1]
    modal.reason._value = "duplicate"
    answered = FakeInteraction(bot, lead)
    await modal.on_submit(answered)

    run = await store_.run_by_ticket(db, GUILD, ticket["id"])
    assert run["state"] == REMOVED and run["reason"] == "duplicate"
    assert ada.dms[-1]["content"] == (
        "Your **Celeste** run (30:00) was taken off the leaderboard. Staff said: duplicate"
    )
    assert answered.sent.startswith("Took Ada's **Celeste** run (30:00) off the leaderboard.")
    assert bot.guild.channels[SPEED].messages[-1].kwargs["embed"].description == (
        "Ada dropped out of the top 10."
    )


async def test_the_sites_reject_closes_the_runs_ticket_the_same_way(bot, ada, lead, db):
    from black_bloc import points_moves as moves

    _, ticket = await sent_in(bot, ada)
    run = await store_.run_by_ticket(db, GUILD, ticket["id"])

    outcome = await moves.reject(bot, bot.guild, lead, run["id"], "blurry", via=VIA_WEBSITE)
    said = await tickets.settle(bot, bot.guild, lead, outcome, tickets.REJECT, via=VIA_WEBSITE)

    assert said.startswith("Rejected Ada's")
    assert (await modmail_cog.get_ticket(db, ticket["id"]))["status"] == "closed"
    assert "web.modmail.closed" in await kinds(db)
    assert "web.points.would_dm" in await kinds(db)


async def test_the_pending_list_is_the_open_run_tickets_only(bot, ada, lead, vera, db):
    await sent_in(bot, ada)
    await modmail_cog.open_a_ticket(bot, bot.guild, vera, source="panel", text="hello")

    found = await tickets.pending(bot, bot.guild)

    assert [row["game"] for _, row in found] == ["Celeste"]
    ticket, row = found[0]
    line = tickets.pending_line(bot.guild, ticket, row)
    assert line == f"#{ticket['id']} · Ada — **Celeste** (30:00) · <#{ticket['thread_id']}>"


async def test_the_inbox_tags_a_run_ticket(bot, ada):
    _, ticket = await sent_in(bot, ada)

    assert modmail_cog.ticket_label(ticket, "Ada") == f"#{ticket['id']} · thread · run · Ada"
