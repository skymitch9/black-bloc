from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from black_bloc import chat_data
from black_bloc.chat_data import (
    at_local,
    clock,
    display_of,
    tokens_for,
    wanted_time,
)
from black_bloc.cogs.community.birthdays import save_birthday
from black_bloc.cogs.community.events import create_event, set_status
from black_bloc.cogs.community.role_menus import add_option, create_menu, get_menu
from black_bloc.cogs.content.golive import set_link, start_session
from black_bloc.config import load_settings
from black_bloc.events import APPROVED
from black_bloc.golive import StreamInfo
from black_bloc.settings_store import SettingsStore
from black_bloc.storage.db import Database
from black_bloc.timezones import set_timezone

GUILD = 7
STAFF_CHANNEL = 500
MEMBER = 901
CHANNEL = 111


class FakeRole:
    def __init__(self, role_id, name, viewers=()):
        self.id = role_id
        self.name = name
        self.viewers = set(viewers)

    def is_default(self):
        return self.id == GUILD

    def is_bot_managed(self):
        return False


class FakePermissions:
    def __init__(self, view_channel):
        self.view_channel = view_channel


class FakeChannel:
    def __init__(self, channel_id, viewers=()):
        self.id = channel_id
        self.viewers = set(viewers)
        self.mention = f"<#{channel_id}>"

    def permissions_for(self, role):
        return FakePermissions(role.id in self.viewers)


class FakeMember:
    def __init__(self, user_id=MEMBER, display_name="Nia", roles=()):
        self.id = user_id
        self.display_name = display_name
        self.name = display_name
        self.bot = False
        self.roles = list(roles)


class FakeGuild:
    def __init__(self, member_count=12):
        self.id = GUILD
        self.member_count = member_count
        self.roles = [
            FakeRole(GUILD, "@everyone"),
            FakeRole(11, "Aunties / Uncles"),
            FakeRole(22, "Member"),
        ]
        self.channels = {STAFF_CHANNEL: FakeChannel(STAFF_CHANNEL, viewers={11})}
        self.members = {}

    def get_member(self, user_id):
        return self.members.get(int(user_id))

    def get_role(self, role_id):
        return next((r for r in self.roles if r.id == int(role_id)), None)

    def get_channel(self, channel_id):
        return self.channels.get(int(channel_id))


class FakeBot:
    def __init__(self, db, store, guild):
        self.db = db
        self.store = store
        self.guild = guild
        self.guilds = [guild]


@pytest.fixture
async def db(tmp_path):
    database = Database(tmp_path / "d.sqlite3")
    await database.connect()
    try:
        yield database
    finally:
        await database.close()


@pytest.fixture
async def bot(db, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    settings = load_settings(_env_file=None, test_mode=False)
    store = SettingsStore(db, settings)
    await store.load()
    await store.set(GUILD, "staff_channel_id", STAFF_CHANNEL)
    guild = FakeGuild()
    guild.members[MEMBER] = FakeMember()
    return FakeBot(db, store, guild)


async def asked(bot, intent, text="", member=None):
    return await tokens_for(bot, bot.guild, member or bot.guild.get_member(MEMBER), intent, text)


def test_a_name_falls_back_to_a_mention_when_the_cache_never_saw_them():
    guild = FakeGuild()
    guild.members[MEMBER] = FakeMember()
    assert display_of(guild, MEMBER) == "Nia"
    assert display_of(guild, 404) == "<@404>"
    assert display_of(None, 404) == "<@404>"


async def test_a_canned_intent_needs_no_lookup_and_counts_as_filled(bot):
    assert await asked(bot, "greeting") == ({}, True)


async def test_who_is_live_names_the_open_sessions_and_links_them(bot, db):
    await set_link(db, MEMBER, "nia", "t-1")
    await start_session(
        db, GUILD, MEMBER, "twitch", StreamInfo(url="https://twitch.tv/nia", game="Balatro"), "on"
    )

    tokens, filled = await asked(bot, "who_is_live")

    assert filled is True
    assert tokens["names"] == "Nia"
    assert tokens["links"] == "<https://twitch.tv/nia>"
    assert tokens["count"] == 1


async def test_who_is_live_with_nobody_streaming_is_the_empty_state(bot):
    tokens, filled = await asked(bot, "who_is_live")
    assert filled is False and tokens["count"] == 0


async def test_whats_next_is_the_soonest_approved_event_still_to_come(bot, db):
    soon = datetime.now(UTC) + timedelta(hours=2)
    later = datetime.now(UTC) + timedelta(days=3)
    for title, starts in (("Later one", later), ("Movie night", soon)):
        event_id = await create_event(
            db,
            GUILD,
            MEMBER,
            title=title,
            description=None,
            location="the park",
            starts_at=starts,
            finishes_at=starts + timedelta(hours=1),
        )
        await set_status(db, event_id, APPROVED)

    tokens, filled = await asked(bot, "whats_next")

    assert filled is True
    assert tokens["title"] == "Movie night"
    assert tokens["when"].startswith("<t:") and tokens["when"].endswith(":R>")
    assert tokens["channel"] == "the park"


async def test_an_event_that_has_already_started_is_not_whats_next(bot, db):
    gone = datetime.now(UTC) - timedelta(hours=2)
    event_id = await create_event(
        db,
        GUILD,
        MEMBER,
        title="Gone",
        description=None,
        location=None,
        starts_at=gone,
        finishes_at=gone + timedelta(hours=1),
    )
    await set_status(db, event_id, APPROVED)

    assert await asked(bot, "whats_next") == ({}, False)


async def test_a_pending_event_is_not_announced_by_chat_either(bot, db):
    soon = datetime.now(UTC) + timedelta(hours=2)
    await create_event(
        db,
        GUILD,
        MEMBER,
        title="Not approved",
        description=None,
        location=None,
        starts_at=soon,
        finishes_at=soon + timedelta(hours=1),
    )

    assert await asked(bot, "whats_next") == ({}, False)


async def test_birthdays_lists_the_next_three_and_skips_the_opted_out(bot, db):
    for user_id, month, day in ((MEMBER, 3, 4), (902, 5, 6), (903, 7, 8), (904, 9, 10)):
        await save_birthday(db, GUILD, user_id, month, day, None, "self")
    await db.conn.execute("UPDATE birthdays SET opted_in = 0 WHERE user_id = ?", (MEMBER,))
    await db.conn.commit()

    tokens, filled = await asked(bot, "birthdays")

    assert filled is True and tokens["count"] == 3
    assert "Nia" not in tokens["list"]


async def test_no_stored_birthdays_is_the_empty_state(bot):
    assert await asked(bot, "birthdays") == ({}, False)


async def test_the_head_count_is_the_one_the_status_line_shows(bot):
    tokens, filled = await asked(bot, "head_count")
    assert filled is True and tokens["count"] == 12


async def test_a_guild_with_no_member_count_yet_is_the_empty_state(bot):
    bot.guild.member_count = None
    assert await asked(bot, "head_count") == ({}, False)


async def test_my_roles_names_the_menus_and_the_roles_they_already_hold(bot, db):
    await bot.store.set(GUILD, "rolemenu_mode", "on")
    await create_menu(db, GUILD, "colours", "Colours")
    menu = await get_menu(db, GUILD, "colours")
    await add_option(db, menu["id"], 22, "Member", None)
    member = FakeMember(roles=[bot.guild.get_role(22)])

    tokens, filled = await asked(bot, "my_roles", member=member)

    assert filled is True
    assert tokens["menus"] == "Colours"
    assert tokens["roles"] == "Member"


async def test_my_roles_says_nothing_held_rather_than_leaving_a_hole(bot, db):
    await bot.store.set(GUILD, "rolemenu_mode", "on")
    await create_menu(db, GUILD, "colours", "Colours")
    menu = await get_menu(db, GUILD, "colours")
    await add_option(db, menu["id"], 22, "Member", None)

    tokens, filled = await asked(bot, "my_roles", member=FakeMember())

    assert filled is True and tokens["roles"] == "nothing from them yet"


async def test_my_roles_is_the_empty_state_while_picking_is_off(bot, db):
    await create_menu(db, GUILD, "colours", "Colours")
    menu = await get_menu(db, GUILD, "colours")
    await add_option(db, menu["id"], 22, "Member", None)

    assert await asked(bot, "my_roles") == ({}, False)


async def test_my_roles_with_picking_on_but_no_menus_is_the_empty_state(bot):
    await bot.store.set(GUILD, "rolemenu_mode", "on")
    assert await asked(bot, "my_roles") == ({}, False)


def test_a_time_is_read_from_a_stamp_a_12_hour_clock_or_a_24_hour_one():
    assert wanted_time("meet at <t:1780000000:t>") == datetime.fromtimestamp(1780000000, UTC)
    assert wanted_time("doors at 7pm") == at_local(19, 0)
    assert wanted_time("doors at 7:30 PM") == at_local(19, 30)
    assert wanted_time("doors at 19:30") == at_local(19, 30)
    assert wanted_time("doors at 12am") == at_local(0, 0)
    assert wanted_time("no time in here") is None


def test_the_clock_is_written_the_same_way_on_every_machine():
    when = datetime(2026, 8, 27, 19, 5, tzinfo=UTC)
    assert clock(when) == "7:05 pm"
    assert clock(when.replace(hour=0, minute=0)) == "12:00 am"
    assert clock(when.replace(hour=12, minute=0)) == "12:00 pm"


async def test_time_for_me_converts_into_the_members_own_zone(bot, db):
    await set_timezone(db, MEMBER, "Europe/London")

    tokens, filled = await asked(bot, "time_for_me", text="what time is that for me <t:1780000000>")

    assert filled is True
    assert tokens["zone"] == "Europe/London"
    there = datetime.fromtimestamp(1780000000, UTC).astimezone(ZoneInfo("Europe/London"))
    assert tokens["time"] == clock(there)


async def test_time_for_me_with_no_stored_zone_is_the_empty_state(bot):
    assert await asked(bot, "time_for_me", text="<t:1780000000>") == ({}, False)


async def test_time_for_me_with_no_time_in_the_message_is_the_empty_state(bot, db):
    await set_timezone(db, MEMBER, "Europe/London")
    assert await asked(bot, "time_for_me", text="what time is that for me") == ({}, False)


async def test_need_a_mod_is_filled_when_modmail_is_answering(bot):
    await bot.store.set(GUILD, "modmail_enabled", True)
    tokens, filled = await asked(bot, "need_a_mod")
    assert filled is True


async def test_need_a_mod_names_the_staff_roles_when_modmail_is_off(bot):
    tokens, filled = await asked(bot, "need_a_mod")
    assert filled is False
    assert tokens["roles"] == "**Aunties / Uncles**"


async def test_need_a_mod_with_no_staff_channel_still_says_something(bot):
    await bot.store.clear(GUILD, "staff_channel_id")
    tokens, filled = await asked(bot, "need_a_mod")
    assert filled is False and tokens["roles"] == "the mods"


async def test_a_lookup_that_throws_falls_back_to_the_empty_line(bot, monkeypatch, caplog):
    """A broken lookup must not raise inside on_message; it becomes 'nothing to report'."""

    async def boom(*args, **kwargs):
        raise RuntimeError("no")

    monkeypatch.setitem(chat_data.RESOLVERS, "head_count", boom)
    with caplog.at_level("WARNING"):
        assert await asked(bot, "head_count") == ({}, False)
    assert any("head_count" in record.getMessage() for record in caplog.records)
