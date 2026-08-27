import asyncio
from datetime import UTC, datetime

import discord
import pytest

from black_bloc.birthdays import ImportRow, local_today, next_occurrence
from black_bloc.cogs.community.birthdays import (
    Birthdays,
    chunked,
    get_birthday,
    report_lines,
    rows_for_guild,
    save_birthday,
    stored_counts,
)
from black_bloc.config import load_settings
from black_bloc.settings_store import BIRTHDAY_TZ, SettingsStore
from black_bloc.storage.db import Database

GUILD = 7
TEST_CHANNEL = 111
LOG_CHANNEL = 222
PARTY_CHANNEL = 333
STAFF_ROLE = 555
CAKE_ROLE = 777
USER = 900

MORNING = datetime(2026, 8, 10, 8, 0, tzinfo=UTC)
EVENING_BEFORE = datetime(2026, 8, 10, 4, 30, tzinfo=UTC)
NEXT_DAY = datetime(2026, 8, 11, 8, 0, tzinfo=UTC)


class _Response:
    def __init__(self, status):
        self.status = status
        self.reason = "refused"


def refused():
    return discord.HTTPException(_Response(403), "no")


class FakeRole:
    def __init__(self, role_id):
        self.id = role_id
        self.name = f"role-{role_id}"


class FakePerms:
    def __init__(self, manage_guild=False, view_channel=None):
        self.manage_guild = manage_guild
        self.view_channel = view_channel


class FakeChannel:
    def __init__(self, channel_id, name="channel"):
        self.id = channel_id
        self.name = name
        self.mention = f"<#{channel_id}>"
        self.messages = []
        self.send_raises = None
        self.visible_to = set()

    def permissions_for(self, role):
        return FakePerms(view_channel=role.id in self.visible_to)

    async def send(self, content=None, **kwargs):
        if self.send_raises is not None:
            raise self.send_raises
        self.messages.append({"content": content, **kwargs})
        return self.messages[-1]


class FakeMember:
    def __init__(self, guild, user_id=USER, display_name="PT", username=None, manage_guild=False):
        self.id = user_id
        self.guild = guild
        self.display_name = display_name
        self.name = username or display_name
        self.mention = f"<@{user_id}>"
        self.roles = []
        self.guild_permissions = FakePerms(manage_guild=manage_guild)
        self.role_calls = []
        self.role_raises = None
        self.global_name = None
        guild.member_cache[user_id] = self

    async def add_roles(self, role, reason=None):
        if self.role_raises is not None:
            raise self.role_raises
        self.role_calls.append(("add", role.id, reason))
        self.roles.append(role)

    async def remove_roles(self, role, reason=None):
        if self.role_raises is not None:
            raise self.role_raises
        self.role_calls.append(("remove", role.id, reason))
        self.roles = [r for r in self.roles if r.id != role.id]


class FakeGuild:
    def __init__(self):
        self.id = GUILD
        self.name = "Black Bloc"
        self.channels = {}
        self.member_cache = {}
        self.roles = []
        self.queries = []
        self.query_answer = {}
        self.query_raises = None
        self.member_count = 0
        self.chunks = 0
        self.hidden = []

    @property
    def members(self):
        return list(self.member_cache.values())

    async def chunk(self):
        self.chunks += 1
        for member in self.hidden:
            self.member_cache[member.id] = member
        self.hidden = []

    def add(self, channel):
        channel.guild = self
        self.channels[channel.id] = channel
        return channel

    def get_channel(self, channel_id):
        return self.channels.get(channel_id)

    def get_member(self, user_id):
        return self.member_cache.get(user_id)

    def get_role(self, role_id):
        return next((r for r in self.roles if r.id == role_id), None)

    async def query_members(self, query=None, limit=10):
        self.queries.append(query)
        if self.query_raises is not None:
            raise self.query_raises
        return self.query_answer.get(query, [])


class FakeGuard:
    def __init__(self, test_channel_id=TEST_CHANNEL):
        self.test_channel_id = test_channel_id

    def allows_channel(self, channel_id):
        return channel_id == self.test_channel_id


class FakeBot:
    def __init__(self, db, store, settings, guild):
        self.db = db
        self.store = store
        self.settings = settings
        self.guard = None
        self.guilds = [guild]
        self.guild = guild

    def get_channel(self, channel_id):
        return self.guild.get_channel(channel_id)


class FakeResponse:
    def __init__(self):
        self.messages = []

    async def send_message(self, content=None, ephemeral=False, **kwargs):
        self.messages.append({"content": content, "ephemeral": ephemeral, **kwargs})

    async def defer(self, ephemeral=False):
        self.messages.append({"content": None, "deferred": True, "ephemeral": ephemeral})


class FakeFollowup:
    def __init__(self, response):
        self.response = response

    async def send(self, content=None, ephemeral=False, **kwargs):
        self.response.messages.append({"content": content, "ephemeral": ephemeral, **kwargs})


class FakeInteraction:
    def __init__(self, bot, user, channel_id=TEST_CHANNEL):
        self.client = bot
        self.user = user
        self.guild = bot.guild
        self.guild_id = bot.guild.id
        self.channel_id = channel_id
        self.response = FakeResponse()
        self.followup = FakeFollowup(self.response)

    @property
    def sent(self):
        return self.response.messages[-1]["content"] if self.response.messages else None

    @property
    def texts(self):
        return [m["content"] for m in self.response.messages if m["content"]]


async def action_kinds(db):
    cur = await db.conn.execute("SELECT kind FROM action_log ORDER BY id")
    return [row["kind"] for row in await cur.fetchall()]


async def details_for(db, kind):
    cur = await db.conn.execute(
        "SELECT details FROM action_log WHERE kind = ? ORDER BY id", (kind,)
    )
    return [row["details"] for row in await cur.fetchall()]


@pytest.fixture
async def db(tmp_path):
    database = Database(tmp_path / "b.sqlite3")
    await database.connect()
    try:
        yield database
    finally:
        await database.close()


@pytest.fixture
async def bot(db, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    settings = load_settings(_env_file=None, test_mode=True, test_channel_id=TEST_CHANNEL)
    store = SettingsStore(db, settings)
    await store.load()
    await store.set(GUILD, "log_channel_id", LOG_CHANNEL)
    guild = FakeGuild()
    guild.add(FakeChannel(TEST_CHANNEL, name="test"))
    guild.add(FakeChannel(LOG_CHANNEL, name="log"))
    guild.add(FakeChannel(PARTY_CHANNEL, name="return-of-the-gen"))
    return FakeBot(db, store, settings, guild)


@pytest.fixture
def cog(bot):
    return Birthdays(bot)


@pytest.fixture
def birthday_person(bot):
    return FakeMember(bot.guild)


def give_staff(bot, member, role_id=STAFF_ROLE):
    role = FakeRole(role_id)
    bot.guild.roles.append(role)
    bot.guild.get_channel(TEST_CHANNEL).visible_to.add(role_id)
    member.roles.append(role)
    return role


def party_posts(bot, channel_id=TEST_CHANNEL):
    return [m for m in bot.guild.get_channel(channel_id).messages if m.get("embed") is not None]


async def stored(bot, month=8, day=10, year=None, source="self", user_id=USER):
    await save_birthday(bot.db, GUILD, user_id, month, day, year, source)


async def test_the_sweep_posts_once_on_the_day_and_never_twice(bot, cog, birthday_person):
    await bot.store.set(GUILD, "birthday_mode", "on")
    await stored(bot)

    await cog.run_once(MORNING)
    await cog.run_once(MORNING)

    posts = party_posts(bot)
    assert len(posts) == 1
    assert posts[0]["embed"].description == "Happy Birthday **PT**!"
    assert posts[0]["embed"].colour.value == 0x4EEFFF
    assert posts[0]["allowed_mentions"].everyone is False
    assert await action_kinds(bot.db) == ["birthday.announce"]
    row = await get_birthday(bot.db, USER)
    assert row["last_announced_on"] == "2026-08-10"


async def test_a_display_name_that_looks_like_a_ping_cannot_ping(bot, cog):
    await bot.store.set(GUILD, "birthday_mode", "on")
    FakeMember(bot.guild, display_name="@everyone")
    await stored(bot)

    await cog.run_once(MORNING)

    posted = party_posts(bot)[0]
    assert "@everyone" in posted["embed"].description
    assert posted["allowed_mentions"].everyone is False
    assert posted["allowed_mentions"].roles is False
    assert posted["allowed_mentions"].users is False


async def test_only_todays_rows_are_picked(bot, cog, birthday_person):
    await bot.store.set(GUILD, "birthday_mode", "on")
    await stored(bot)
    tomorrow = FakeMember(bot.guild, user_id=901, display_name="Later")
    await stored(bot, month=8, day=11, user_id=tomorrow.id)
    yesterday = FakeMember(bot.guild, user_id=902, display_name="Earlier")
    await stored(bot, month=8, day=9, user_id=yesterday.id)

    await cog.run_once(MORNING)

    assert [p["embed"].description for p in party_posts(bot)] == ["Happy Birthday **PT**!"]


async def test_shadow_logs_a_dry_run_and_posts_nothing(bot, cog, birthday_person):
    await stored(bot)

    await cog.run_once(MORNING)

    assert party_posts(bot) == []
    assert await action_kinds(bot.db) == ["birthday.would_announce"]
    assert (await get_birthday(bot.db, USER))["last_announced_on"] == "2026-08-10"

    await cog.run_once(MORNING)
    assert await action_kinds(bot.db) == ["birthday.would_announce"]


async def test_off_does_nothing_at_all(bot, cog, birthday_person):
    await bot.store.set(GUILD, "birthday_mode", "off")
    await stored(bot)

    await cog.run_once(MORNING)

    assert party_posts(bot) == []
    assert await action_kinds(bot.db) == []
    assert (await get_birthday(bot.db, USER))["last_announced_on"] is None


async def test_an_opted_out_row_is_left_alone(bot, cog, birthday_person):
    await bot.store.set(GUILD, "birthday_mode", "on")
    await stored(bot)
    await bot.db.conn.execute("UPDATE birthdays SET opted_in = 0")
    await bot.db.conn.commit()

    await cog.run_once(MORNING)

    assert party_posts(bot) == []
    assert await action_kinds(bot.db) == []


async def test_a_post_that_fails_is_named_a_failure_and_tried_again(bot, cog, birthday_person):
    await bot.store.set(GUILD, "birthday_mode", "on")
    await stored(bot)
    bot.guild.get_channel(TEST_CHANNEL).send_raises = refused()

    await cog.run_once(MORNING)

    assert await action_kinds(bot.db) == ["birthday.announce_failed"]
    assert (await get_birthday(bot.db, USER))["last_announced_on"] is None

    await cog.run_once(MORNING)
    assert await action_kinds(bot.db) == ["birthday.announce_failed"]

    bot.guild.get_channel(TEST_CHANNEL).send_raises = None
    await cog.run_once(MORNING)
    assert await action_kinds(bot.db) == ["birthday.announce_failed", "birthday.announce"]


async def test_a_channel_outside_test_mode_is_a_dry_run_not_a_failure(bot, cog, birthday_person):
    bot.guard = FakeGuard()
    await bot.store.set(GUILD, "birthday_mode", "on")
    await bot.store.set(GUILD, "birthday_channel_id", PARTY_CHANNEL)
    await stored(bot)

    await cog.run_once(MORNING)

    assert party_posts(bot, PARTY_CHANNEL) == []
    assert await action_kinds(bot.db) == ["birthday.would_announce"]


async def test_a_member_who_left_is_skipped_once(bot, cog):
    await bot.store.set(GUILD, "birthday_mode", "on")
    await stored(bot)

    await cog.run_once(MORNING)
    await cog.run_once(MORNING)

    assert await action_kinds(bot.db) == ["birthday.skipped"]
    assert party_posts(bot) == []


async def test_the_role_is_never_added_in_test_mode(bot, cog, birthday_person):
    bot.guard = FakeGuard()
    bot.guild.roles.append(FakeRole(CAKE_ROLE))
    await bot.store.set(GUILD, "birthday_mode", "on")
    await bot.store.set(GUILD, "birthday_role_id", CAKE_ROLE)
    await stored(bot)

    await cog.run_once(MORNING)

    assert birthday_person.role_calls == []
    assert await action_kinds(bot.db) == ["birthday.announce", "birthday.would_add_role"]
    assert (await get_birthday(bot.db, USER))["role_added"] == 0


async def test_shadow_never_really_gives_the_role_out(bot, cog, birthday_person):
    bot.guild.roles.append(FakeRole(CAKE_ROLE))
    await bot.store.set(GUILD, "birthday_role_id", CAKE_ROLE)
    await stored(bot)

    await cog.run_once(MORNING)

    assert birthday_person.role_calls == []
    assert await action_kinds(bot.db) == ["birthday.would_announce", "birthday.would_add_role"]
    row = await get_birthday(bot.db, USER)
    assert row["role_added"] == 0 and row["role_added_id"] is None


async def test_the_role_that_comes_off_is_the_one_that_went_on(bot, cog, birthday_person):
    bot.guild.roles.append(FakeRole(CAKE_ROLE))
    await bot.store.set(GUILD, "birthday_mode", "on")
    await bot.store.set(GUILD, "birthday_role_id", CAKE_ROLE)
    await stored(bot)
    await cog.run_once(MORNING)
    assert (await get_birthday(bot.db, USER))["role_added_id"] == CAKE_ROLE

    other = 888
    bot.guild.roles.append(FakeRole(other))
    await bot.store.set(GUILD, "birthday_role_id", other)
    await cog.run_once(NEXT_DAY)

    assert birthday_person.role_calls[-1] == ("remove", CAKE_ROLE, "Black Bloc birthday")
    row = await get_birthday(bot.db, USER)
    assert row["role_added"] == 0 and row["role_added_id"] is None


async def test_a_role_whose_setting_was_cleared_still_comes_off(bot, cog, birthday_person):
    bot.guild.roles.append(FakeRole(CAKE_ROLE))
    await bot.store.set(GUILD, "birthday_mode", "on")
    await bot.store.set(GUILD, "birthday_role_id", CAKE_ROLE)
    await stored(bot)
    await cog.run_once(MORNING)

    bot.guild.roles.clear()
    await cog.run_once(NEXT_DAY)

    assert birthday_person.role_calls[-1] == ("remove", CAKE_ROLE, "Black Bloc birthday")
    assert (await get_birthday(bot.db, USER))["role_added"] == 0


async def test_removing_your_birthday_hands_the_role_back_first(bot, cog, birthday_person):
    bot.guild.roles.append(FakeRole(CAKE_ROLE))
    await bot.store.set(GUILD, "birthday_mode", "on")
    await bot.store.set(GUILD, "birthday_role_id", CAKE_ROLE)
    await stored(bot)
    await cog.run_once(MORNING)
    interaction = FakeInteraction(bot, birthday_person)

    await cog.remove.callback(cog, interaction)

    assert birthday_person.role_calls[-1] == ("remove", CAKE_ROLE, "Black Bloc birthday")
    assert await get_birthday(bot.db, USER) is None
    assert "forgotten" in interaction.sent


async def test_opting_out_on_your_birthday_hands_the_role_back(bot, cog, birthday_person):
    bot.guild.roles.append(FakeRole(CAKE_ROLE))
    await bot.store.set(GUILD, "birthday_mode", "on")
    await bot.store.set(GUILD, "birthday_role_id", CAKE_ROLE)
    await stored(bot)
    await cog.run_once(MORNING)
    interaction = FakeInteraction(bot, birthday_person)

    await cog.optout.callback(cog, interaction)

    assert birthday_person.role_calls[-1] == ("remove", CAKE_ROLE, "Black Bloc birthday")
    row = await get_birthday(bot.db, USER)
    assert row["opted_in"] == 0 and row["role_added"] == 0


async def test_the_role_goes_on_for_the_day_and_comes_off_after(bot, cog, birthday_person):
    bot.guild.roles.append(FakeRole(CAKE_ROLE))
    await bot.store.set(GUILD, "birthday_mode", "on")
    await bot.store.set(GUILD, "birthday_role_id", CAKE_ROLE)
    await stored(bot)

    await cog.run_once(MORNING)
    assert birthday_person.role_calls == [("add", CAKE_ROLE, "Black Bloc birthday")]
    assert (await get_birthday(bot.db, USER))["role_added"] == 1

    await cog.run_once(MORNING)
    assert len(birthday_person.role_calls) == 1

    await cog.run_once(NEXT_DAY)
    assert birthday_person.role_calls[-1] == ("remove", CAKE_ROLE, "Black Bloc birthday")
    assert (await get_birthday(bot.db, USER))["role_added"] == 0
    assert await action_kinds(bot.db) == [
        "birthday.announce",
        "birthday.add_role",
        "birthday.remove_role",
    ]


async def test_the_role_comes_off_even_after_the_mode_is_turned_off(bot, cog, birthday_person):
    bot.guild.roles.append(FakeRole(CAKE_ROLE))
    await bot.store.set(GUILD, "birthday_mode", "on")
    await bot.store.set(GUILD, "birthday_role_id", CAKE_ROLE)
    await stored(bot)
    await cog.run_once(MORNING)

    await bot.store.set(GUILD, "birthday_mode", "off")
    await cog.run_once(NEXT_DAY)

    assert birthday_person.role_calls[-1][0] == "remove"
    assert (await get_birthday(bot.db, USER))["role_added"] == 0


async def test_a_role_that_will_not_come_off_is_reported_once_a_day(bot, cog, birthday_person):
    bot.guild.roles.append(FakeRole(CAKE_ROLE))
    await bot.store.set(GUILD, "birthday_mode", "on")
    await bot.store.set(GUILD, "birthday_role_id", CAKE_ROLE)
    await stored(bot)
    await cog.run_once(MORNING)
    birthday_person.role_raises = refused()

    await cog.run_once(NEXT_DAY)
    await cog.run_once(NEXT_DAY)

    assert await action_kinds(bot.db) == [
        "birthday.announce",
        "birthday.add_role",
        "birthday.remove_role_failed",
    ]
    assert (await get_birthday(bot.db, USER))["role_added"] == 1


async def test_a_member_east_of_phoenix_is_wished_on_their_own_date(bot, cog, birthday_person):
    await bot.store.set(GUILD, "birthday_mode", "on")
    await stored(bot)
    await bot.db.conn.execute(
        "CREATE TABLE user_timezones (user_id INTEGER PRIMARY KEY, tz TEXT NOT NULL, "
        "set_at TEXT NOT NULL)"
    )
    await bot.db.conn.execute(
        "INSERT INTO user_timezones(user_id, tz, set_at) VALUES (?, 'America/New_York', 'now')",
        (USER,),
    )
    await bot.db.conn.commit()

    await cog.run_once(EVENING_BEFORE)

    assert len(party_posts(bot)) == 1
    assert (await get_birthday(bot.db, USER))["last_announced_on"] == "2026-08-10"


async def test_a_member_without_a_zone_waits_for_phoenix_midnight(bot, cog, birthday_person):
    await bot.store.set(GUILD, "birthday_mode", "on")
    await stored(bot)

    await cog.run_once(EVENING_BEFORE)

    assert party_posts(bot) == []


async def test_the_age_is_only_shown_when_the_setting_says_so(bot, cog, birthday_person):
    await bot.store.set(GUILD, "birthday_mode", "on")
    await bot.store.set(GUILD, "birthday_template", "{name} turns {age} today!")
    await stored(bot, year=1987)

    await cog.run_once(MORNING)
    assert party_posts(bot)[0]["embed"].description == "PT turns  today!"

    await bot.store.set(GUILD, "birthday_show_age", True)
    await bot.db.conn.execute("UPDATE birthdays SET last_announced_on = NULL")
    await bot.db.conn.commit()
    await cog.run_once(MORNING)
    assert party_posts(bot)[1]["embed"].description == "PT turns 39 today!"


async def test_setting_a_birthday_stores_it_and_answers_with_the_next_one(
    bot, cog, birthday_person
):
    interaction = FakeInteraction(bot, birthday_person)

    await cog.set_mine.callback(cog, interaction, 8, 10, None)

    row = await get_birthday(bot.db, USER)
    assert (row["month"], row["day"], row["source"]) == (8, 10, "self")
    assert "August 10" in interaction.sent and "<t:" in interaction.sent
    assert interaction.response.messages[-1]["ephemeral"] is True
    assert await action_kinds(bot.db) == ["birthday.set"]


async def test_an_impossible_date_is_refused_with_a_sentence(bot, cog, birthday_person):
    interaction = FakeInteraction(bot, birthday_person)

    await cog.set_mine.callback(cog, interaction, 2, 30, None)

    assert "no day" in interaction.sent
    assert await get_birthday(bot.db, USER) is None


async def test_a_birth_year_in_the_future_is_refused(bot, cog, birthday_person):
    interaction = FakeInteraction(bot, birthday_person)

    await cog.set_mine.callback(cog, interaction, 2, 10, 2199)

    assert "not a birth year" in interaction.sent
    assert await get_birthday(bot.db, USER) is None


async def test_setting_a_birthday_again_lets_todays_wish_still_land(bot, cog, birthday_person):
    await bot.store.set(GUILD, "birthday_mode", "on")
    await stored(bot)
    await cog.run_once(MORNING)
    assert len(party_posts(bot)) == 1

    interaction = FakeInteraction(bot, birthday_person)
    await cog.set_mine.callback(cog, interaction, 8, 10, None)
    await cog.run_once(MORNING)

    assert len(party_posts(bot)) == 2


async def test_set_for_is_staff_only(bot, cog, birthday_person):
    plain = FakeMember(bot.guild, user_id=1, display_name="Plain")
    interaction = FakeInteraction(bot, plain)

    await cog.set_for.callback(cog, interaction, birthday_person, 8, 10, None)
    assert "staff only" in interaction.sent
    assert await get_birthday(bot.db, USER) is None

    lead = FakeMember(bot.guild, user_id=2, display_name="Lead")
    give_staff(bot, lead)
    staff_interaction = FakeInteraction(bot, lead)
    await cog.set_for.callback(cog, staff_interaction, birthday_person, 8, 10, None)

    assert (await get_birthday(bot.db, USER))["source"] == "staff"
    assert "PT" in staff_interaction.sent


async def test_remove_optout_and_optin(bot, cog, birthday_person):
    interaction = FakeInteraction(bot, birthday_person)
    await cog.remove.callback(cog, interaction)
    assert "no birthday for you" in interaction.sent

    await stored(bot)
    await cog.optout.callback(cog, interaction)
    assert (await get_birthday(bot.db, USER))["opted_in"] == 0
    await cog.optout.callback(cog, interaction)
    assert "already opted out" in interaction.sent
    await cog.optin.callback(cog, interaction)
    assert (await get_birthday(bot.db, USER))["opted_in"] == 1

    await cog.remove.callback(cog, interaction)
    assert await get_birthday(bot.db, USER) is None
    assert await action_kinds(bot.db) == [
        "birthday.optout",
        "birthday.optin",
        "birthday.remove",
    ]


async def test_show_and_next_render_hammertime_and_never_ping(bot, cog, birthday_person):
    await stored(bot, year=1987)
    interaction = FakeInteraction(bot, birthday_person)

    await cog.show.callback(cog, interaction, None)
    assert "August 10" in interaction.sent and "<t:" in interaction.sent
    assert interaction.response.messages[-1]["allowed_mentions"].everyone is False

    await cog.next_up.callback(cog, interaction)
    assert f"<@{USER}>" in interaction.sent
    assert interaction.response.messages[-1]["allowed_mentions"].users is False


async def test_show_gives_the_age_at_the_next_birthday_not_this_year(bot, cog, birthday_person):
    await bot.store.set(GUILD, "birthday_show_age", True)
    await stored(bot, month=1, day=2, year=1990)
    interaction = FakeInteraction(bot, birthday_person)

    await cog.show.callback(cog, interaction, None)

    when = next_occurrence(1, 2, BIRTHDAY_TZ)
    assert when.date() >= local_today(BIRTHDAY_TZ)
    assert f"turning {when.year - 1990}" in interaction.sent


async def test_show_says_when_someone_is_opted_out(bot, cog, birthday_person):
    await stored(bot)
    await bot.db.conn.execute("UPDATE birthdays SET opted_in = 0")
    await bot.db.conn.commit()
    interaction = FakeInteraction(bot, birthday_person)

    await cog.show.callback(cog, interaction, None)

    assert "opted out" in interaction.sent


async def test_next_shows_at_most_five_soonest_first(bot, cog):
    for index, (month, day) in enumerate([(12, 24), (9, 3), (1, 2), (8, 26), (6, 17), (7, 2)]):
        member = FakeMember(bot.guild, user_id=1000 + index, display_name=f"m{index}")
        await stored(bot, month=month, day=day, user_id=member.id)
    interaction = FakeInteraction(bot, bot.guild.get_member(1000))

    await cog.next_up.callback(cog, interaction)

    assert interaction.sent.count("·") == 5


async def test_next_says_so_when_there_is_nothing(bot, cog, birthday_person):
    interaction = FakeInteraction(bot, birthday_person)
    await cog.next_up.callback(cog, interaction)
    assert "no birthdays to show" in interaction.sent


async def test_list_is_staff_only_and_groups_by_month(bot, cog, birthday_person):
    interaction = FakeInteraction(bot, birthday_person)
    await cog.list_all.callback(cog, interaction, None)
    assert "staff only" in interaction.sent

    give_staff(bot, birthday_person)
    await stored(bot)
    await stored(bot, month=1, day=2, user_id=1001, source="import")
    staff_interaction = FakeInteraction(bot, birthday_person)

    await cog.list_all.callback(cog, staff_interaction, None)

    assert "**January**" in staff_interaction.sent and "**August**" in staff_interaction.sent
    assert "import" in staff_interaction.sent


async def test_mode_is_staff_only_and_records_the_change(bot, cog, birthday_person):
    interaction = FakeInteraction(bot, birthday_person)
    choice = discord.app_commands.Choice(name="on", value="on")

    await cog.mode.callback(cog, interaction, choice)
    assert "staff only" in interaction.sent
    assert bot.store.get(GUILD, "birthday_mode") == "shadow"

    give_staff(bot, birthday_person)
    staff_interaction = FakeInteraction(bot, birthday_person)
    await cog.mode.callback(cog, staff_interaction, choice)

    assert bot.store.get(GUILD, "birthday_mode") == "on"
    assert await action_kinds(bot.db) == ["birthday.mode"]


async def test_status_shows_health_not_just_liveness(bot, cog, birthday_person):
    give_staff(bot, birthday_person)
    await stored(bot)
    interaction = FakeInteraction(bot, birthday_person)

    await cog.status.callback(cog, interaction)

    text = interaction.sent
    assert "**mode** — shadow" in text
    assert "**last sweep** — not yet" in text
    assert "**last error** — none" in text
    assert "1 opted in" in text
    assert "role(s)" in text


async def test_import_matches_the_member_list_including_tagged_nicknames(bot, cog):
    shin = FakeMember(bot.guild, user_id=2000, display_name="[Straight Hands] ShinDarkShadow")
    pt = FakeMember(bot.guild, user_id=2001, display_name="PT")
    nadia = FakeMember(bot.guild, user_id=2002, display_name="nadia")
    FakeMember(bot.guild, user_id=2003, display_name="Prez")
    FakeMember(bot.guild, user_id=2004, display_name="Prez")
    rows = [
        ImportRow("[Straight Hands] ShinDarkShadow", 1, 2, None),
        ImportRow("[Tired of Planes] PT", 8, 10, 39),
        ImportRow("(Umazing) nadia", 7, 26, None),
        ImportRow("Prez", 6, 17, 39),
        ImportRow("ghost", 1, 1, None),
    ]

    result = await cog._import(bot.guild, rows, 2026, bot.guild.members)

    assert len(result["imported"]) == 3
    assert f"<@{shin.id}>" in result["imported"][0]
    assert f"<@{pt.id}>" in result["imported"][1]
    assert f"<@{nadia.id}>" in result["imported"][2]
    assert len(result["ambiguous"]) == 1 and "Prez" in result["ambiguous"][0]
    assert result["not_found"] == ["ghost — January 1"]
    assert bot.guild.queries == []
    stored_pt = await get_birthday(bot.db, 2001)
    assert (stored_pt["month"], stored_pt["day"], stored_pt["year"]) == (8, 10, 1987)
    assert stored_pt["source"] == "import"

    again = await cog._import(bot.guild, rows, 2026, bot.guild.members)
    assert again["imported"] == []
    assert len(again["already"]) == 3
    assert len(await rows_for_guild(bot.db, GUILD)) == 3


async def test_import_never_overwrites_what_someone_set_themselves(bot, cog):
    pt = FakeMember(bot.guild, user_id=2001, display_name="PT")
    await save_birthday(bot.db, GUILD, pt.id, 3, 3, None, "self")

    rows = [ImportRow("[Tired of Planes] PT", 8, 10, 39)]
    result = await cog._import(bot.guild, rows, 2026, bot.guild.members)

    row = await get_birthday(bot.db, 2001)
    assert (row["month"], row["day"], row["source"]) == (3, 3, "self")
    assert "kept the self entry" in result["already"][0]


async def test_a_half_filled_member_cache_is_chunked_before_anyone_is_matched(bot, cog):
    late = FakeMember(bot.guild, user_id=2001, display_name="PT")
    bot.guild.member_cache.pop(late.id)
    bot.guild.hidden = [late]
    bot.guild.member_count = 1

    members = await cog.members_of(bot.guild)
    result = await cog._import(bot.guild, [ImportRow("PT", 8, 10, None)], 2026, members)

    assert bot.guild.chunks == 1
    assert [m.id for m in members] == [late.id]
    assert len(result["imported"]) == 1
    assert bot.guild.queries == []


async def test_the_import_command_defers_and_says_how_many_members_it_searched(
    bot, cog, birthday_person
):
    give_staff(bot, birthday_person)
    interaction = FakeInteraction(bot, birthday_person)

    await cog.import_seed.callback(cog, interaction)

    assert interaction.response.messages[0]["deferred"] is True
    assert "imported" in interaction.texts[0]
    assert f"**{len(bot.guild.members)}** members" in interaction.texts[0]
    assert bot.guild.queries == []
    assert await action_kinds(bot.db) == ["birthday.import"]


async def test_the_import_command_is_staff_only(bot, cog, birthday_person):
    interaction = FakeInteraction(bot, birthday_person)

    await cog.import_seed.callback(cog, interaction)

    assert "staff only" in interaction.sent
    assert bot.guild.queries == []


async def test_the_report_counts_every_bucket_and_carries_the_age_caveat():
    result = {
        "imported": ["a → <@1>"],
        "already": ["b"],
        "ambiguous": ["c"],
        "not_found": ["d"],
    }
    text = "\n".join(report_lines(result, 2026, 412))
    assert "**1 imported** · 1 already stored · 1 ambiguous · 1 not found" in text
    assert "**412** members" in text
    assert "a year out" in text
    assert "2026 export" in text


def test_long_reports_are_split_into_messages_discord_will_take():
    pages = chunked([f"line {n} " + "x" * 100 for n in range(60)])
    assert len(pages) > 1
    assert all(len(page) <= 1900 for page in pages)
    assert chunked([]) == []


async def test_the_counts_used_by_status(bot):
    await stored(bot, user_id=1, source="self")
    await stored(bot, user_id=2, source="import")
    await set_opted_out(bot.db, 2)

    totals = await stored_counts(bot.db, GUILD)

    assert totals == {"stored": 2, "opted_in": 1, "imported": 1, "self": 1}


async def set_opted_out(db, user_id):
    await db.conn.execute("UPDATE birthdays SET opted_in = 0 WHERE user_id = ?", (user_id,))
    await db.conn.commit()


async def test_commands_say_so_when_the_database_is_not_there(bot, cog, birthday_person):
    class Closed:
        is_connected = False

    bot.db = Closed()
    interaction = FakeInteraction(bot, birthday_person)

    await cog.set_mine.callback(cog, interaction, 8, 10, None)

    assert "database" in interaction.sent


async def test_the_loop_is_registered_on_load_and_cancelled_on_unload(bot, cog):
    await cog.cog_load()
    assert cog._sweep.is_running()

    await cog.cog_unload()
    await asyncio.sleep(0)
    await asyncio.sleep(0)

    assert not cog._sweep.is_running()


async def test_a_sweep_that_throws_is_recorded_not_swallowed_silently(bot, cog, monkeypatch):
    async def boom(*args, **kwargs):
        raise RuntimeError("nope")

    monkeypatch.setattr(cog, "run_once", boom)

    await cog._sweep()

    assert cog.last_error == "RuntimeError: nope"
    assert cog.last_run_at is None
