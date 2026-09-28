from types import SimpleNamespace

import discord
import pytest

from black_bloc.cogs.moderation.quiet_pins import QuietPins, pin_details, should_quiet
from black_bloc.config import load_settings
from black_bloc.settings_store import CORE_KEYS, KEY_TYPES, QUIET_BOT_PINS, SettingsStore

GUILD = 7
BOT_ID = 42
HUMAN = 900
CHANNEL = 333
THREAD = 444
FORUM = 445
PINNED = 5150


class _Response:
    def __init__(self, status):
        self.status = status
        self.reason = "refused"


class FakeChannel:
    def __init__(self, channel_id, name="board", parent_id=None):
        self.id = channel_id
        self.name = name
        if parent_id is not None:
            self.parent_id = parent_id


class FakeMessage:
    _next = 1000

    def __init__(self, author_id, kind, channel, refuses=None):
        FakeMessage._next += 1
        self.id = FakeMessage._next
        self.author = SimpleNamespace(id=author_id)
        self.type = kind
        self.channel = channel
        self.guild = SimpleNamespace(id=GUILD, get_channel=lambda _id: None)
        self.reference = SimpleNamespace(message_id=PINNED)
        self.refuses = refuses
        self.deleted = 0

    async def delete(self):
        if self.refuses is not None:
            raise self.refuses
        self.deleted += 1


@pytest.fixture
async def bot(db, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    store = SettingsStore(db, load_settings(_env_file=None))
    await store.load()
    return SimpleNamespace(
        user=SimpleNamespace(id=BOT_ID), db=db, store=store, get_channel=lambda _id: None
    )


@pytest.fixture
def cog(bot):
    return QuietPins(bot)


async def kinds(db):
    cur = await db.conn.execute("SELECT kind, details FROM action_log ORDER BY id")
    return [row["kind"] for row in await cur.fetchall()]


def pin(author_id=BOT_ID, channel=None, refuses=None, kind=discord.MessageType.pins_add):
    return FakeMessage(author_id, kind, channel or FakeChannel(CHANNEL), refuses)


def test_the_key_is_a_core_bool_that_ships_on(bot):
    assert KEY_TYPES[QUIET_BOT_PINS] == "bool"
    assert QUIET_BOT_PINS in CORE_KEYS
    assert bot.store.get(GUILD, QUIET_BOT_PINS) is True


async def test_a_pin_notice_the_bot_made_is_deleted_and_logged_routine(cog, bot, db):
    notice = pin()
    await cog.on_message(notice)
    assert notice.deleted == 1
    assert await kinds(db) == ["quiet_pins.deleted"]
    cur = await db.conn.execute("SELECT details FROM action_log")
    details = (await cur.fetchone())["details"]
    assert str(PINNED) in details and str(CHANNEL) in details


async def test_a_pin_a_person_made_is_left_alone(cog, bot, db):
    notice = pin(author_id=HUMAN)
    await cog.on_message(notice)
    assert notice.deleted == 0
    assert await kinds(db) == []


@pytest.mark.parametrize(
    "kind",
    [
        discord.MessageType.default,
        discord.MessageType.reply,
        discord.MessageType.thread_created,
        discord.MessageType.channel_name_change,
    ],
)
async def test_nothing_but_a_pin_notice_is_touched(cog, bot, db, kind):
    message = pin(kind=kind)
    await cog.on_message(message)
    assert message.deleted == 0
    assert await kinds(db) == []


async def test_the_key_off_leaves_the_notice(cog, bot, db):
    await bot.store.set(GUILD, QUIET_BOT_PINS, False)
    notice = pin()
    await cog.on_message(notice)
    assert notice.deleted == 0
    assert await kinds(db) == []


@pytest.mark.parametrize(
    "refusal",
    [
        discord.Forbidden(_Response(403), "Missing Permissions"),
        discord.NotFound(_Response(404), "Unknown Message"),
        discord.HTTPException(_Response(500), "boom"),
    ],
)
async def test_a_refusal_is_logged_once_per_channel_and_never_raises(cog, bot, db, refusal):
    for _ in range(3):
        await cog.on_message(pin(refuses=refusal))
    assert await kinds(db) == ["quiet_pins.delete_failed"]
    await cog.on_message(pin(channel=FakeChannel(CHANNEL + 1), refuses=refusal))
    assert await kinds(db) == ["quiet_pins.delete_failed", "quiet_pins.delete_failed"]


async def test_forbidden_names_the_permission_it_needs(cog, bot, db):
    await cog.on_message(pin(refuses=discord.Forbidden(_Response(403), "Missing Permissions")))
    cur = await db.conn.execute("SELECT details FROM action_log")
    assert "Manage Messages" in (await cur.fetchone())["details"]


async def test_a_notice_in_a_thread_or_forum_post_is_deleted_too(cog, bot, db):
    notice = pin(channel=FakeChannel(THREAD, name="runner post", parent_id=FORUM))
    await cog.on_message(notice)
    assert notice.deleted == 1
    assert pin_details(notice)["parent_id"] == FORUM
    assert await kinds(db) == ["quiet_pins.deleted"]


async def test_a_dm_or_no_signed_in_user_is_ignored(bot):
    message = pin()
    message.guild = None
    assert not should_quiet(bot, message)
    bot.user = None
    assert not should_quiet(bot, pin())


async def test_a_database_that_is_down_still_deletes_and_never_raises(cog, bot, monkeypatch):
    monkeypatch.setattr(type(bot.db), "is_connected", property(lambda _self: False))
    notice = pin()
    await cog.on_message(notice)
    assert notice.deleted == 1
    await cog.on_message(pin(refuses=discord.Forbidden(_Response(403), "no")))
