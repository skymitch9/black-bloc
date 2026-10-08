# ruff: noqa: F401, F811
from __future__ import annotations

import asyncio
import itertools
from types import SimpleNamespace

import discord
import pytest

from black_bloc import brackets_moves as moves
from black_bloc import brackets_people as people
from black_bloc import brackets_sets as sets
from black_bloc import brackets_store as store_
from black_bloc import brackets_thread as thread_
from black_bloc.config import load_settings
from black_bloc.settings_store import SettingsStore
from tests.test_brackets_moves import (
    ADA,
    BEA,
    CY,
    GUILD,
    STAFF,
    TO,
    TO_ROLE,
    Guild,
    rows,
    who,
)

KNUCK_UP = 1076005097617760296
REHEARSAL = 900
LOGS = 901
BOT_ID = 1
PING_ROLE = 777
IDS = itertools.count(5000)


class Response:
    def __init__(self, status):
        self.status = status
        self.reason = "gone"


def not_found():
    return discord.NotFound(Response(404), "gone")


def server_error():
    return discord.HTTPException(Response(503), "upstream connect error")


def no_access():
    return discord.Forbidden(Response(403), {"code": 50001, "message": "Missing Access"})


def system_message():
    return discord.HTTPException(
        Response(400), {"code": 50021, "message": "Cannot execute action on a system message"}
    )


class FakeMessage:
    def __init__(self, channel, content=None, **kwargs):
        self.id = next(IDS)
        self.channel = channel
        self.type = discord.MessageType.default
        self.author = SimpleNamespace(id=BOT_ID)
        self.pinned = False
        self.edits = 0
        self.sent = kwargs
        self.embed = None
        self.view = None
        self.apply(content=content, **kwargs)

    def apply(self, **kwargs):
        for name, value in kwargs.items():
            setattr(self, name, value)
        view = getattr(self, "view", None)
        self.components = [SimpleNamespace(children=list(view.children))] if view else []

    @property
    def labels(self):
        return [
            getattr(getattr(one, "item", one), "label", None)
            for row in self.components
            for one in row.children
        ]

    @property
    def custom_ids(self):
        return [getattr(one, "custom_id", None) for row in self.components for one in row.children]

    async def pin(self, reason=None):
        self.pinned = True


class FakePartial:
    def __init__(self, channel, message_id):
        self.channel = channel
        self.id = message_id

    async def edit(self, **kwargs):
        found = self.channel.find(self.id)
        if found is None:
            raise not_found()
        if found.type != discord.MessageType.default:
            raise system_message()
        if found.id in self.channel.broken:
            raise self.channel.broken[found.id]
        found.edits += 1
        found.apply(**kwargs)
        return found


class FakeThread:
    def __init__(self, parent, name):
        self.id = next(IDS)
        self.parent = parent
        self.name = name
        self.archived = False
        self.messages: list[FakeMessage] = []
        self.type = discord.ChannelType.public_thread
        self.broken: dict[int, Exception] = {}
        self.fetches = 0

    def find(self, message_id):
        return next((one for one in self.messages if one.id == int(message_id)), None)

    async def send(self, content=None, **kwargs):
        message = FakeMessage(self, content, **kwargs)
        self.messages.append(message)
        return message

    def get_partial_message(self, message_id):
        return FakePartial(self, message_id)

    async def fetch_message(self, message_id):
        self.fetches += 1
        found = self.find(message_id)
        if found is None:
            raise not_found()
        return found

    def notice(self, after, kind=discord.MessageType.pins_add):
        """A system message Discord writes as the bot, e.g. "pinned a message"."""
        made = FakeMessage(self, None)
        made.type = kind
        self.messages.insert(self.messages.index(after) + 1, made)
        return made

    async def history(self, limit=100, oldest_first=False):
        found = self.messages if oldest_first else list(reversed(self.messages))
        for one in found[:limit]:
            yield one

    async def edit(self, **kwargs):
        for name, value in kwargs.items():
            setattr(self, name, value)

    def delete(self, message):
        self.messages.remove(message)

    @property
    def cards(self):
        return [one for one in self.messages if one.embed is not None and not one.pinned]


class FakeChannel:
    def __init__(self, bot, channel_id):
        self.id = channel_id
        self.bot = bot
        self.type = discord.ChannelType.text
        self.threads: list[FakeThread] = []
        self.posted: list[object] = []

    async def send(self, content=None, **kwargs):
        self.posted.append((content, kwargs))
        return FakeMessage(self, content, **kwargs)

    async def create_thread(self, *, name, type=None, auto_archive_duration=None, reason=None):
        made = FakeThread(self, name)
        self.threads.append(made)
        self.bot.channels[made.id] = made
        return made


class FakeMember:
    def __init__(self, guild, user_id, name, *roles):
        self.id = user_id
        self.guild = guild
        self.display_name = name
        self.roles = [SimpleNamespace(id=one, name=f"role{one}") for one in roles]
        self.dms: list[str] = []
        self.closed = False

    async def send(self, text, **kwargs):
        if self.closed:
            raise discord.Forbidden(Response(403), "closed")
        self.dms.append(text)


class ThreadGuild(Guild):
    def add(self, user_id, name, *roles):
        self.members[user_id] = FakeMember(self, user_id, name, *roles)
        return self.members[user_id]


class ThreadBot:
    def __init__(self, db, store, guild):
        self.db = db
        self.store = store
        self.guild = guild
        self.guilds = [guild]
        self.user = SimpleNamespace(id=BOT_ID)
        self.settings = SimpleNamespace(origin="https://blackbloc.example")
        self.channels: dict[int, object] = {}
        for one in (KNUCK_UP, REHEARSAL, LOGS):
            self.channels[one] = FakeChannel(self, one)

    def get_channel(self, channel_id):
        return self.channels.get(int(channel_id))

    def forget(self):
        """What a restart loses: everything the process kept in memory."""
        for name in list(self.__dict__):
            if name.startswith("_brackets"):
                del self.__dict__[name]


@pytest.fixture
def guild():
    found = ThreadGuild()
    found.add(STAFF, "Sky")
    found.add(TO, "Tess", TO_ROLE)
    found.add(ADA, "Ada")
    found.add(BEA, "Bea")
    found.add(CY, "Cy")
    for user_id in range(40, 52):
        found.add(user_id, f"P{user_id}")
    return found


@pytest.fixture
async def bot(db, guild, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    store = SettingsStore(db, load_settings(_env_file=None))
    await store.load()
    store.is_staff = lambda member: getattr(member, "id", None) == STAFF
    await store.set(GUILD, "brackets_to_role_id", TO_ROLE)
    await store.set(GUILD, "shadow_channel_id", REHEARSAL)
    await store.set(GUILD, "log_channel_id", LOGS)
    return ThreadBot(db, store, guild)


async def mode(bot, value):
    await bot.store.set(GUILD, "brackets_mode", value)


def home(bot, channel_id):
    return bot.channels[channel_id]


def the_thread(bot, channel_id=REHEARSAL):
    found = home(bot, channel_id).threads
    assert len(found) == 1, found
    return found[0]


async def created(bot, guild, **given):
    outcome = await moves.create(bot, guild, who(guild, TO), {"name": "Knuck Up 12", **given})
    assert outcome.ok, outcome.message
    await thread_.follow(bot, guild, outcome.value, outcome, move="create")
    return outcome.value


async def moved(bot, guild, tid, move, *args, actor=TO, **kw):
    outcome = await move(bot, guild, who(guild, actor), tid, *args, **kw)
    assert outcome.ok, outcome.message
    await thread_.follow(bot, guild, tid, outcome, move=move.__name__)
    return outcome


async def running(bot, guild, *players, **given):
    tid = await created(bot, guild, **given)
    await moved(bot, guild, tid, moves.open_signups)
    for player in players:
        await moved(bot, guild, tid, people.join, actor=player)
    await moved(bot, guild, tid, moves.close_signups)
    await moved(bot, guild, tid, moves.start)
    return tid


async def row_of(bot, tid):
    return await store_.tournament(bot.db, GUILD, tid)


async def card_ids(bot, tid):
    return {key: found[0] for key, found in (await store_.card_rows(bot.db, tid)).items()}


async def test_in_shadow_the_thread_is_made_in_the_rehearsal_home_and_never_in_knuck_up(bot, guild):
    tid = await created(bot, guild)

    thread = the_thread(bot, REHEARSAL)
    assert home(bot, KNUCK_UP).threads == []
    row = await row_of(bot, tid)
    assert (row["channel_id"], row["thread_id"], row["shadow"]) == (REHEARSAL, thread.id, 1)
    starter = thread.messages[0]
    assert row["message_id"] == starter.id and starter.pinned
    assert starter.content == f"Rehearsal — this is where it would go: <#{KNUCK_UP}>"
    assert starter.embed.title == "Knuck Up 12"
    assert "**A draft**" in starter.embed.description
    assert starter.labels == ["Open the bracket"]
    assert "brackets.thread_made" in [kind for kind, *_ in await rows(bot.db)]


async def test_on_the_thread_is_made_under_knuck_up_with_no_rehearsal_line(bot, guild):
    await mode(bot, "on")
    tid = await created(bot, guild)

    thread = the_thread(bot, KNUCK_UP)
    assert home(bot, REHEARSAL).threads == []
    row = await row_of(bot, tid)
    assert (row["channel_id"], row["shadow"]) == (KNUCK_UP, 0)
    assert thread.messages[0].content is None


async def test_a_mode_flip_never_moves_a_thread_already_made(bot, guild):
    tid = await created(bot, guild)
    await mode(bot, "on")
    await moved(bot, guild, tid, moves.open_signups)

    assert home(bot, KNUCK_UP).threads == []
    assert len(the_thread(bot, REHEARSAL).messages) == 1


async def test_off_makes_no_thread_anywhere(bot, guild):
    outcome = await moves.create(bot, guild, who(guild, TO), {"name": "Knuck Up 12"})
    await mode(bot, "off")
    await thread_.follow(bot, guild, outcome.value, outcome, move="create")

    assert all(
        not channel.threads for channel in bot.channels.values() if hasattr(channel, "threads")
    )
    assert thread_.parent_id(bot, guild) == (None, False)


async def test_the_starter_card_is_edited_in_place_and_never_reposted(bot, guild):
    tid = await created(bot, guild)
    thread = the_thread(bot)
    starter = thread.messages[0]

    await moved(bot, guild, tid, moves.open_signups)
    await moved(bot, guild, tid, people.join, actor=ADA)

    assert thread.messages == [starter]
    assert starter.edits == 2
    assert starter.labels == ["Sign up", "Leave", "Open the bracket"]
    assert "1 entrant(s)" in starter.embed.description
    assert starter.custom_ids[:2] == [f"brackets:{tid}:join", f"brackets:{tid}:leave"]


async def test_one_card_per_ready_set_mentions_its_players_only_when_on(bot, guild):
    await mode(bot, "on")
    tid = await running(bot, guild, ADA, BEA, format="single", best_of_finals=3)
    thread = the_thread(bot, KNUCK_UP)

    [card] = thread.cards
    assert card.content == f"<@{ADA}> v <@{BEA}>"
    mentioned = card.sent["allowed_mentions"]
    assert {one.id for one in mentioned.users} == {ADA, BEA}
    assert mentioned.everyone is False and mentioned.roles is False
    assert card.embed.title == "W1-1 · Winners round 1"
    assert card.labels == ["Report", "Call", "Decide…"]
    assert (await card_ids(bot, tid))["W1-1"] == card.id


async def test_in_shadow_a_set_card_names_its_players_and_pings_nobody(bot, guild):
    await running(bot, guild, ADA, BEA, format="single")

    [card] = the_thread(bot).cards
    assert card.content == f"<@{ADA}> v <@{BEA}>"
    assert card.sent["allowed_mentions"].to_dict() == discord.AllowedMentions.none().to_dict()


async def test_a_guest_is_named_and_never_mentioned(bot, guild):
    await mode(bot, "on")
    tid = await created(bot, guild, format="single")
    await moved(bot, guild, tid, moves.open_signups)
    await moved(bot, guild, tid, people.join, actor=ADA)
    await moved(bot, guild, tid, people.add_entrant, name="Remy")
    await moved(bot, guild, tid, moves.close_signups)
    await moved(bot, guild, tid, moves.start)

    [card] = the_thread(bot, KNUCK_UP).cards
    assert card.content == f"<@{ADA}> v Remy"
    assert [one.id for one in card.sent["allowed_mentions"].users] == [ADA]


async def test_the_card_follows_the_set_and_a_report_confirm_edit_it_in_place(bot, guild):
    tid = await running(bot, guild, ADA, BEA, format="single", best_of_finals=3)
    thread = the_thread(bot)
    [card] = thread.cards

    await moved(bot, guild, tid, sets.report, "W1-1", 2, 1, actor=ADA)
    assert "Ada reported 2–1 — waiting on Bea, stands <t:" in card.embed.description
    assert card.labels == ["Confirm", "Dispute", "Decide…", "Reset…"]

    await moved(bot, guild, tid, sets.confirm_report, "W1-1", actor=BEA)
    assert "W1-1 is final: Ada wins 2–1." in card.embed.description
    assert card.labels == ["Decide…", "Reset…"]
    assert thread.cards == [card]


async def test_two_follows_and_two_reconciles_at_once_leave_one_card_per_set(bot, guild):
    tid = await running(bot, guild, ADA, BEA, CY, STAFF, format="single")
    thread = the_thread(bot)
    before = len(thread.cards)
    bot.forget()
    for key in await card_ids(bot, tid):
        await store_.set_card(bot.db, tid, key, None, None)
    for one in list(thread.cards):
        thread.delete(one)

    await asyncio.gather(
        thread_.reconcile(bot, guild),
        thread_.reconcile(bot, guild),
        thread_.sync(bot, guild, await row_of(bot, tid), keys=()),
    )

    assert before == 2
    assert len(thread.cards) == 2
    assert sorted(card.embed.title.split(" ·")[0] for card in thread.cards) == ["W1-1", "W1-2"]


async def test_a_restart_between_the_post_and_the_store_adopts_the_card_it_posted(bot, guild):
    tid = await running(bot, guild, ADA, BEA, format="single")
    thread = the_thread(bot)
    [card] = thread.cards
    stamp = (await store_.card_rows(bot.db, tid))["W1-1"][1]
    await store_.set_card(bot.db, tid, "W1-1", None, stamp)
    bot.forget()

    await thread_.reconcile(bot, guild, full=True)

    assert thread.cards == [card]
    assert (await card_ids(bot, tid))["W1-1"] == card.id


async def test_a_stored_card_that_no_longer_resolves_is_posted_again_once(bot, guild):
    tid = await running(bot, guild, ADA, BEA, format="single")
    thread = the_thread(bot)
    [card] = thread.cards
    thread.delete(card)

    await thread_.reconcile(bot, guild, full=True)
    await thread_.reconcile(bot, guild, full=True)

    [again] = thread.cards
    assert again.id != card.id
    assert (await card_ids(bot, tid))["W1-1"] == again.id
    reposted = [d for kind, _, _, d in await rows(bot.db) if kind == "brackets.card_reposted"]
    assert [(one["tournament"], one["card"]) for one in reposted] == [(tid, "W1-1")]


async def test_a_card_a_move_finds_gone_is_reposted_by_the_next_tick_not_by_the_move(bot, guild):
    tid = await running(bot, guild, ADA, BEA, format="single", best_of_finals=3)
    thread = the_thread(bot)
    thread.delete(thread.cards[0])

    await moved(bot, guild, tid, sets.report, "W1-1", 2, 0, actor=ADA)
    assert thread.cards == []

    await thread_.sweep(bot, guild)
    [card] = thread.cards
    assert "Ada reported 2–0" in card.embed.description


async def test_a_starter_card_that_is_gone_is_reposted_by_the_reconcile(bot, guild):
    tid = await created(bot, guild)
    thread = the_thread(bot)
    thread.delete(thread.messages[0])

    await moved(bot, guild, tid, moves.open_signups)
    assert thread.messages == []

    await thread_.reconcile(bot, guild)
    [starter] = thread.messages
    assert (await row_of(bot, tid))["message_id"] == starter.id and starter.pinned


async def test_the_sweep_posts_what_confirm_due_changed(bot, guild):
    tid = await running(bot, guild, ADA, BEA, CY, STAFF, format="single", best_of_finals=3)
    thread = the_thread(bot)
    await moved(bot, guild, tid, sets.report, "W1-1", 2, 0, actor=ADA)
    first = next(one for one in thread.cards if one.embed.title.startswith("W1-1"))
    await bot.db.conn.execute(
        "UPDATE tournament_sets SET reported_at = '2020-01-01T00:00:00+00:00' WHERE key = 'W1-1'"
    )
    await bot.db.conn.commit()

    await thread_.sweep(bot, guild)

    assert "W1-1 is final: Ada wins 2–0." in first.embed.description
    assert (await store_.bracket(bot.db, await row_of(bot, tid))).matches[
        "W1-1"
    ].state == "complete"


async def test_the_sweep_closes_a_due_check_in_and_the_starter_card_says_so(bot, guild):
    tid = await created(bot, guild)
    await moved(bot, guild, tid, moves.open_signups)
    await moved(bot, guild, tid, people.join, actor=ADA)
    await moved(bot, guild, tid, people.open_check_in)
    starter = the_thread(bot).messages[0]
    assert starter.labels[:2] == ["Check in", "Leave"]
    await store_.update(bot.db, tid, {"check_in_closes_at": "2020-01-01T00:00:00+00:00"})

    await thread_.sweep(bot, guild)

    assert (await row_of(bot, tid))["state"] == "seeding"
    assert "**Being seeded**" in starter.embed.description
    assert starter.labels == ["Open the bracket"]


async def test_a_pass_posts_a_handful_and_the_next_tick_the_rest(bot, guild):
    players = list(range(40, 52))
    tid = await running(bot, guild, *players, format="round_robin")
    thread = the_thread(bot)
    assert len(thread.cards) == thread_.POSTS_PER_PASS

    await thread_.sweep(bot, guild)
    assert len(thread.cards) == 2 * thread_.POSTS_PER_PASS
    ids = await card_ids(bot, tid)
    assert len([one for one in ids.values() if one]) == 2 * thread_.POSTS_PER_PASS


async def test_back_to_seeding_clears_every_card_and_takes_its_buttons(bot, guild):
    tid = await running(bot, guild, ADA, BEA, format="single")
    [card] = the_thread(bot).cards

    await moved(bot, guild, tid, moves.unstart)

    assert card.embed.description == "W1-1 was cleared"
    assert card.view is None and card.content is None
    assert await card_ids(bot, tid) == {}


async def test_a_cancel_takes_every_set_cards_buttons_and_restore_brings_them_back(bot, guild):
    tid = await running(bot, guild, ADA, BEA, format="single")
    [card] = the_thread(bot).cards

    await moved(bot, guild, tid, moves.cancel)
    assert card.labels == []
    await moved(bot, guild, tid, moves.restore)
    assert card.labels == ["Report", "Call", "Decide…"]


async def test_a_thread_lost_twice_running_is_made_again_with_its_cards(bot, guild):
    tid = await running(bot, guild, ADA, BEA, format="single")
    old = the_thread(bot)
    del bot.channels[old.id]

    await thread_.reconcile(bot, guild)
    assert len(home(bot, REHEARSAL).threads) == 1

    await thread_.reconcile(bot, guild)
    new = home(bot, REHEARSAL).threads[1]
    assert (await row_of(bot, tid))["thread_id"] == new.id
    assert len(new.cards) == 1 and new.messages[0].pinned
    assert "brackets.thread_lost" in [kind for kind, *_ in await rows(bot.db)]


async def test_in_shadow_the_start_ping_names_the_role_and_pings_nobody(bot, guild):
    await bot.store.set(GUILD, "brackets_ping_role_id", PING_ROLE)
    await running(bot, guild, ADA, BEA, format="single")
    [ping] = [one for one in the_thread(bot).messages if one.embed is None]
    assert ping.content == f"<@&{PING_ROLE}> **Knuck Up 12** has started."
    assert ping.sent["allowed_mentions"].to_dict() == discord.AllowedMentions.none().to_dict()
    assert "brackets.would_ping" in [kind for kind, *_ in await rows(bot.db)]


async def test_the_start_ping_reaches_the_role_when_on(bot, guild):
    await mode(bot, "on")
    await bot.store.set(GUILD, "brackets_ping_role_id", PING_ROLE)
    await running(bot, guild, ADA, BEA, format="single")
    [ping] = [one for one in the_thread(bot, KNUCK_UP).messages if one.embed is None]
    assert [one.id for one in ping.sent["allowed_mentions"].roles] == [PING_ROLE]


async def test_a_dm_is_only_logged_in_shadow_and_sent_when_on(bot, guild):
    tid = await created(bot, guild)
    row = await row_of(bot, tid)

    await thread_.tell(bot, guild, row, ADA, "brackets_dm_dq", "no-show twice")
    assert guild.get_member(ADA).dms == []
    assert [kind for kind, *_ in await rows(bot.db)][-1] == "brackets.would_dm"

    await mode(bot, "on")
    await store_.update(bot.db, tid, {"shadow": 0})
    await thread_.tell(bot, guild, await row_of(bot, tid), ADA, "brackets_dm_dq", "no-show twice")
    assert guild.get_member(ADA).dms == [
        "A tournament organiser disqualified you from **Knuck Up 12**; your remaining sets are "
        "forfeited.\nReason: no-show twice"
    ]


async def test_a_dm_that_cannot_land_is_an_important_row(bot, guild):
    await mode(bot, "on")
    tid = await created(bot, guild)
    guild.get_member(BEA).closed = True

    await thread_.tell(bot, guild, await row_of(bot, tid), BEA, "brackets_dm_removed")

    kind, _, target, details = (await rows(bot.db))[-1]
    assert (kind, target, details["dm"]) == ("brackets.dm_failed", BEA, "brackets_dm_removed")


async def test_a_rehearsal_tournament_never_dms_even_after_the_mode_goes_on(bot, guild):
    tid = await created(bot, guild)
    await mode(bot, "on")

    await thread_.tell(bot, guild, await row_of(bot, tid), ADA, "brackets_dm_removed")

    assert guild.get_member(ADA).dms == []


async def test_a_thread_that_cannot_be_made_is_written_down_once(bot, guild):
    await mode(bot, "on")
    del bot.channels[KNUCK_UP]
    tid = await created(bot, guild)
    await moved(bot, guild, tid, moves.open_signups)

    failed = [d for kind, _, _, d in await rows(bot.db) if kind == "brackets.thread_failed"]
    assert len(failed) == 1 and str(KNUCK_UP) in failed[0]["reason"]


async def test_follow_never_raises_into_the_move_that_called_it(bot, guild, monkeypatch):
    tid = await created(bot, guild)

    async def broken(*args, **kwargs):
        raise RuntimeError("discord is down")

    monkeypatch.setattr(thread_, "sync", broken)
    outcome = await moves.open_signups(bot, guild, who(guild, TO), tid)
    await thread_.follow(bot, guild, tid, outcome)
    assert outcome.ok


async def entrant_id(bot, tid, user_id):
    return (await store_.entrant_of(bot.db, tid, user_id))["id"]


def kinds(found, kind):
    return [d for one, _, _, d in found if one == kind]


async def test_a_deleted_starter_is_posted_fresh_and_never_adopts_a_set_card(bot, guild):
    tid = await running(bot, guild, ADA, BEA, format="single")
    thread = the_thread(bot)
    starter = thread.messages[0]
    [card] = thread.cards
    title = card.embed.title
    thread.delete(starter)

    await thread_.reconcile(bot, guild, full=True)

    stored = (await row_of(bot, tid))["message_id"]
    assert stored not in (starter.id, card.id)
    again = thread.find(stored)
    assert again.pinned and again.embed.title == "Knuck Up 12"
    assert card.embed.title == title and card.labels == ["Report", "Call", "Decide…"]
    assert (await card_ids(bot, tid))["W1-1"] == card.id


async def test_a_pin_notice_is_never_taken_for_the_starter(bot, guild):
    tid = await running(bot, guild, ADA, BEA, format="single")
    thread = the_thread(bot)
    starter = thread.messages[0]
    pinned = thread.notice(starter)
    thread.delete(starter)

    await thread_.reconcile(bot, guild, full=True)

    stored = (await row_of(bot, tid))["message_id"]
    assert stored != pinned.id
    assert thread.find(stored).pinned and thread.find(stored).embed.title == "Knuck Up 12"
    assert not kinds(await rows(bot.db), "brackets.card_failed")


async def test_a_starter_the_restart_lost_is_adopted_by_its_own_buttons(bot, guild):
    tid = await created(bot, guild)
    await moved(bot, guild, tid, moves.open_signups)
    thread = the_thread(bot)
    starter = thread.messages[0]
    await store_.update(bot.db, tid, {"message_id": None})
    bot.forget()

    await thread_.reconcile(bot, guild, full=True)

    assert thread.messages == [starter]
    assert (await row_of(bot, tid))["message_id"] == starter.id


async def test_a_thread_made_on_pings_and_dms_nobody_once_the_mode_is_not_on(bot, guild):
    await mode(bot, "on")
    await bot.store.set(GUILD, "brackets_ping_role_id", PING_ROLE)
    tid = await created(bot, guild, format="single")
    await moved(bot, guild, tid, moves.open_signups)
    for player in (ADA, BEA):
        await moved(bot, guild, tid, people.join, actor=player)
    await moved(bot, guild, tid, moves.close_signups)
    await mode(bot, "shadow")

    await moved(bot, guild, tid, moves.start)
    await thread_.tell(bot, guild, await row_of(bot, tid), ADA, "brackets_dm_dq")

    thread = the_thread(bot, KNUCK_UP)
    [card] = thread.cards
    [ping] = [one for one in thread.messages if one.embed is None]
    none = discord.AllowedMentions.none().to_dict()
    assert card.sent["allowed_mentions"].to_dict() == none
    assert ping.sent["allowed_mentions"].to_dict() == none
    assert guild.get_member(ADA).dms == []
    assert kinds(await rows(bot.db), "brackets.would_dm")
    row = await row_of(bot, tid)
    assert thread_.live(bot, guild, row) is False
    await mode(bot, "on")
    assert thread_.live(bot, guild, row) is True


async def test_a_thread_the_bot_may_not_read_is_written_down_once_as_a_permission(
    bot, guild, caplog
):
    await running(bot, guild, ADA, BEA, format="single")
    thread = the_thread(bot)
    del bot.channels[thread.id]

    async def fetch_channel(channel_id):
        raise no_access()

    guild.fetch_channel = fetch_channel
    for _ in range(3):
        await thread_.sweep(bot, guild)

    [failed] = kinds(await rows(bot.db), "brackets.thread_failed")
    assert "permission" in failed["reason"] and str(thread.id) in failed["reason"]
    told = [one for one in caplog.records if one.levelname == "WARNING" and "failed" in one.message]
    assert len(told) == 1


async def test_a_thread_discord_could_not_return_is_never_called_a_permission(bot, guild):
    await running(bot, guild, ADA, BEA, format="single")
    thread = the_thread(bot)
    del bot.channels[thread.id]

    async def fetch_channel(channel_id):
        raise server_error()

    guild.fetch_channel = fetch_channel
    await thread_.sweep(bot, guild)
    await thread_.sweep(bot, guild)

    [failed] = kinds(await rows(bot.db), "brackets.thread_failed")
    assert "permission" not in failed["reason"] and "reach" in failed["reason"]


async def test_the_minute_tick_finds_a_starter_card_deleted_while_nobody_looked(bot, guild):
    tid = await running(bot, guild, ADA, BEA, format="single")
    thread = the_thread(bot)
    starter = thread.messages[0]
    thread.delete(starter)

    await thread_.sweep(bot, guild)

    stored = (await row_of(bot, tid))["message_id"]
    assert stored != starter.id and thread.find(stored).pinned
    assert thread.find(stored).embed.title == "Knuck Up 12"


async def test_a_would_dm_and_a_failed_dm_carry_the_words_and_the_reason(bot, guild):
    tid = await created(bot, guild)
    await thread_.tell(bot, guild, await row_of(bot, tid), ADA, "brackets_dm_dq", "no-show twice")
    await mode(bot, "on")
    await store_.update(bot.db, tid, {"shadow": 0})
    guild.get_member(BEA).closed = True
    await thread_.tell(bot, guild, await row_of(bot, tid), BEA, "brackets_dm_removed", "spam")

    found = await rows(bot.db)
    [would] = kinds(found, "brackets.would_dm")
    [failed] = kinds(found, "brackets.dm_failed")
    assert would["text"].startswith("A tournament organiser disqualified you from **Knuck Up 12**")
    assert would["text"].endswith("Reason: no-show twice") and would["reason"] == "no-show twice"
    assert failed["text"] == "A tournament organiser took you out of **Knuck Up 12**.\nReason: spam"
    assert failed["reason"] == "spam" and "403" in failed["why"]


async def four_up(bot, guild):
    tid = await running(bot, guild, ADA, BEA, CY, STAFF, format="single", best_of_finals=3)
    for key in ("W1-1", "W1-2"):
        await moved(bot, guild, tid, sets.override, key, score_a=2, score_b=0)
    return tid


async def test_a_clear_that_fails_for_any_reason_but_404_keeps_the_card_it_could_not_clear(
    bot, guild
):
    tid = await four_up(bot, guild)
    thread = the_thread(bot)
    final = next(one for one in thread.cards if one.embed.title.startswith("W2-1"))
    thread.broken[final.id] = server_error()

    await moved(bot, guild, tid, sets.reset, "W1-1")
    assert (await card_ids(bot, tid))["W2-1"] == final.id

    del thread.broken[final.id]
    await moved(bot, guild, tid, sets.override, "W1-1", score_a=2, score_b=0)

    assert [one for one in thread.cards if one.embed.title.startswith("W2-1")] == [final]
    assert "Ready to play" in final.embed.description and "Report" in final.labels


async def test_a_clear_that_failed_is_tried_again_by_the_next_tick(bot, guild):
    tid = await four_up(bot, guild)
    thread = the_thread(bot)
    final = next(one for one in thread.cards if one.embed.title.startswith("W2-1"))
    thread.broken[final.id] = server_error()
    await moved(bot, guild, tid, sets.reset, "W1-1")
    del thread.broken[final.id]

    await thread_.sweep(bot, guild)

    assert final.embed.description == "W2-1 was cleared" and final.view is None
    assert (await card_ids(bot, tid)).get("W2-1") is None


async def test_a_set_that_fills_already_forfeited_gets_its_final_card_once(bot, guild):
    tid = await running(bot, guild, ADA, BEA, CY, STAFF, format="double", best_of_finals=3)
    await moved(bot, guild, tid, people.dq, await entrant_id(bot, tid, ADA))
    await moved(bot, guild, tid, sets.override, "W1-2", score_a=2, score_b=0)
    thread = the_thread(bot)

    await thread_.reconcile(bot, guild, full=True)
    await thread_.sweep(bot, guild)

    walkover = [one for one in thread.cards if one.embed.title.startswith("L1-1")]
    assert len(walkover) == 1
    assert "L1-1 is final: Cy wins by forfeit" in walkover[0].embed.description
    assert walkover[0].labels == ["Decide…", "Reset…"]


async def test_the_empty_rehearsal_home_is_warned_about_once(bot, guild, caplog):
    await bot.store.clear(GUILD, "shadow_channel_id")
    await bot.store.clear(GUILD, "log_channel_id")
    tid = await created(bot, guild)
    await moved(bot, guild, tid, moves.open_signups)
    await thread_.sweep(bot, guild)
    await thread_.sweep(bot, guild)

    warned = [one for one in caplog.records if "no rehearsal home" in one.message]
    assert len(warned) == 1


def test_the_modes_have_one_home():
    assert (thread_.ON, thread_.SHADOW, thread_.OFF) == (moves.ON, moves.SHADOW, moves.OFF)
    assert thread_.ON is moves.ON and thread_.SHADOW is moves.SHADOW


async def test_a_card_edit_refused_for_any_reason_but_404_is_kept_and_tried_again(bot, guild):
    tid = await running(bot, guild, ADA, BEA, format="single", best_of_finals=3)
    thread = the_thread(bot)
    [card] = thread.cards
    thread.broken[card.id] = server_error()

    await moved(bot, guild, tid, sets.report, "W1-1", 2, 0, actor=ADA)
    await thread_.sweep(bot, guild)
    await thread_.reconcile(bot, guild, full=True)

    assert thread.cards == [card]
    assert (await card_ids(bot, tid))["W1-1"] == card.id
    assert len(kinds(await rows(bot.db), "brackets.card_failed")) == 1
    assert not kinds(await rows(bot.db), "brackets.card_reposted")

    del thread.broken[card.id]
    await thread_.sweep(bot, guild)
    assert "Ada reported 2–0" in card.embed.description


async def test_a_starter_edit_refused_for_any_reason_but_404_is_kept_and_tried_again(bot, guild):
    tid = await created(bot, guild)
    thread = the_thread(bot)
    starter = thread.messages[0]
    thread.broken[starter.id] = server_error()

    await moved(bot, guild, tid, moves.open_signups)
    await thread_.reconcile(bot, guild, full=True)
    assert thread.messages == [starter]
    assert (await row_of(bot, tid))["message_id"] == starter.id

    del thread.broken[starter.id]
    await thread_.sweep(bot, guild)
    assert starter.labels[0] == "Sign up"


async def rehearsed_then_on(bot, guild, *players):
    tid = await running(bot, guild, *players, format="single")
    await mode(bot, "on")
    return tid


async def test_staff_move_a_rehearsal_to_knuck_up_with_its_starter_and_open_cards(bot, guild):
    tid = await rehearsed_then_on(bot, guild, ADA, BEA, CY, STAFF)
    old = the_thread(bot, REHEARSAL)
    old_starter = old.messages[0]
    before = list(old.messages)

    outcome = await thread_.move_home(bot, guild, who(guild, STAFF), tid)
    await thread_.follow(bot, guild, tid, outcome, move=thread_.MOVE)

    assert outcome.ok
    new = the_thread(bot, KNUCK_UP)
    assert outcome.message == f"**Knuck Up 12** is now in <#{new.id}>."
    row = await row_of(bot, tid)
    assert (row["channel_id"], row["thread_id"], row["shadow"]) == (KNUCK_UP, new.id, 0)
    starter = new.messages[0]
    assert row["message_id"] == starter.id and starter.pinned and starter.content is None
    assert sorted(one.embed.title.split(" ·")[0] for one in new.cards) == ["W1-1", "W1-2"]
    assert {one.id for one in new.cards[0].sent["allowed_mentions"].users} <= {ADA, BEA, CY, STAFF}
    assert old.messages == before
    assert old_starter.content == f"This tournament moved to <#{new.id}>."
    assert old_starter.embed is None and old_starter.view is None
    [(actor, details)] = [
        (actor, d) for kind, actor, _, d in await rows(bot.db) if kind == "brackets.thread_moved"
    ]
    assert actor == STAFF
    assert details["via"] == "discord" and details["to_thread"] == new.id
    assert details["from_thread"] == old.id


async def test_the_move_is_refused_in_words_unless_staff_on_and_a_rehearsal(bot, guild):
    tid = await running(bot, guild, ADA, BEA, format="single")

    shadowed = await thread_.move_home(bot, guild, who(guild, STAFF), tid)
    assert not shadowed.ok and shadowed.status == 409
    assert "brackets_mode is shadow" in shadowed.message

    await mode(bot, "on")
    organiser = await thread_.move_home(bot, guild, who(guild, TO), tid)
    assert not organiser.ok and organiser.status == 403
    assert "staff" in organiser.message

    assert (await thread_.move_home(bot, guild, who(guild, STAFF), tid)).ok
    again = await thread_.move_home(bot, guild, who(guild, STAFF), tid)
    assert not again.ok and again.status == 409 and "already" in again.message
    assert len(home(bot, KNUCK_UP).threads) == 1


async def test_a_move_whose_thread_cannot_be_made_moves_nothing(bot, guild):
    tid = await rehearsed_then_on(bot, guild, ADA, BEA)
    del bot.channels[KNUCK_UP]

    outcome = await thread_.move_home(bot, guild, who(guild, STAFF), tid)

    assert not outcome.ok and outcome.status == 502
    assert str(KNUCK_UP) in outcome.message
    row = await row_of(bot, tid)
    assert (row["shadow"], row["thread_id"]) == (1, the_thread(bot, REHEARSAL).id)
