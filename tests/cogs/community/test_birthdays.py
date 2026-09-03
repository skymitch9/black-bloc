import asyncio
import json
from datetime import UTC, datetime

import discord
import pytest

from black_bloc.birthdays import (
    ImportRow,
    local_today,
    next_occurrence,
    panel_buttons,
)
from black_bloc.cogs.community import birthdays as birthdays_cog
from black_bloc.cogs.community.birthdays import (
    Birthdays,
    BirthdayView,
    DateModal,
    change_opt,
    forget_birthday,
    get_birthday,
    report_lines,
    rows_for_guild,
    save_birthday,
    stored_counts,
)
from black_bloc.config import load_settings
from black_bloc.settings_store import BIRTHDAY_MODES, BIRTHDAY_TZ, SettingsStore
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
        self.dms = []
        self.dm_raises = None
        guild.member_cache[user_id] = self

    async def send(self, content=None, **kwargs):
        if self.dm_raises is not None:
            raise self.dm_raises
        self.dms.append({"content": content, **kwargs})

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
        self._cog = None

    def get_channel(self, channel_id):
        return self.guild.get_channel(channel_id)

    def get_cog(self, name):
        return self._cog


class FakeMessage:
    def __init__(self, message_id, **kwargs):
        self.id = message_id
        self.kwargs = kwargs
        embed = kwargs.get("embed")
        self.embeds = list(kwargs.get("embeds") or ([embed] if embed is not None else []))
        self.view = kwargs.get("view")

    async def edit(self, **kwargs):
        self.kwargs = kwargs
        if "embeds" in kwargs:
            self.embeds = list(kwargs["embeds"])
        if "view" in kwargs:
            self.view = kwargs["view"]


class FakeResponse:
    def __init__(self):
        self.messages = []
        self.modals = []
        self.done = False

    def is_done(self):
        return self.done

    async def send_message(self, content=None, ephemeral=False, **kwargs):
        self.done = True
        self.messages.append({"content": content, "ephemeral": ephemeral, **kwargs})

    async def send_modal(self, modal):
        self.done = True
        self.modals.append(modal)

    async def defer(self, ephemeral=False, **kwargs):
        self.done = True
        self.messages.append({"content": None, "deferred": True, "ephemeral": ephemeral})


class FakeFollowup:
    def __init__(self, response):
        self.response = response

    async def send(self, content=None, ephemeral=False, **kwargs):
        self.response.messages.append({"content": content, "ephemeral": ephemeral, **kwargs})


class FakeInteraction:
    def __init__(self, bot, user, channel_id=TEST_CHANNEL, guild=True):
        self.client = bot
        self.user = user
        self.guild = bot.guild if guild else None
        self.guild_id = bot.guild.id if guild else None
        self.channel_id = channel_id
        self.response = FakeResponse()
        self.followup = FakeFollowup(self.response)
        self._message = None

    async def edit_original_response(self, **kwargs):
        self._message = FakeMessage(9500, **kwargs)
        return self._message

    async def original_response(self):
        last = self.response.messages[-1]
        kept = {k: v for k, v in last.items() if k not in ("ephemeral", "content", "deferred")}
        self._message = FakeMessage(9500, **kept)
        return self._message

    @property
    def message(self):
        return self._message

    @property
    def sent(self):
        said = [m["content"] for m in self.response.messages if m["content"] is not None]
        return said[-1] if said else None

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
    found = Birthdays(bot)
    bot._cog = found
    return found


@pytest.fixture
def birthday_person(bot):
    return FakeMember(bot.guild)


def give_staff(bot, member, role_id=STAFF_ROLE):
    role = FakeRole(role_id)
    bot.guild.roles.append(role)
    bot.guild.get_channel(TEST_CHANNEL).visible_to.add(role_id)
    member.roles.append(role)
    return role


async def open_panel(cog, bot, who):
    interaction = FakeInteraction(bot, who)
    await cog.birthday.callback(cog, interaction)
    return interaction


def panel_view(interaction):
    return interaction.response.messages[-1]["view"]


def panel_embed(interaction):
    return interaction.response.messages[-1]["embed"]


def labels(view):
    return [item.label for item in view.children if getattr(item, "label", None)]


def placeholders(view):
    return [
        item.placeholder for item in view.children if getattr(item, "placeholder", None)
    ]


def find_item(view, label):
    return next(item for item in view.children if getattr(item, "label", None) == label)


def find_select(view, placeholder):
    return next(
        item for item in view.children if getattr(item, "placeholder", None) == placeholder
    )


async def click(bot, who, item):
    interaction = FakeInteraction(bot, who)
    await item.callback(interaction)
    return interaction


def card_embed(interaction):
    return interaction.message.kwargs.get("embed")


def card_view(interaction):
    return interaction.message.kwargs.get("view")


async def set_through_the_modal(cog, bot, who, typed, *, member=None, mine=True):
    interaction = FakeInteraction(bot, who)
    await cog.date_submit(interaction, member or who, typed, mine=mine)
    return interaction


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


async def test_a_member_the_cache_cannot_see_is_reported_once_and_not_marked_done(bot, cog):
    await bot.store.set(GUILD, "birthday_mode", "on")
    await stored(bot)

    await cog.run_once(MORNING)
    await cog.run_once(MORNING)

    assert await action_kinds(bot.db) == ["birthday.member_missing"]
    assert party_posts(bot) == []
    assert (await get_birthday(bot.db, USER))["last_announced_on"] is None

    FakeMember(bot.guild)
    await cog.run_once(MORNING)

    assert len(party_posts(bot)) == 1
    assert (await get_birthday(bot.db, USER))["last_announced_on"] == "2026-08-10"


async def test_an_unavailable_server_is_left_alone(bot, cog, birthday_person):
    await bot.store.set(GUILD, "birthday_mode", "on")
    await stored(bot)
    bot.guild.unavailable = True

    await cog.run_once(MORNING)

    assert party_posts(bot) == []
    assert await action_kinds(bot.db) == []
    assert (await get_birthday(bot.db, USER))["last_announced_on"] is None


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

    said = await forget_birthday(cog, bot.guild, birthday_person)

    assert birthday_person.role_calls[-1] == ("remove", CAKE_ROLE, "Black Bloc birthday")
    assert await get_birthday(bot.db, USER) is None
    assert "forgotten" in said


async def test_opting_out_on_your_birthday_hands_the_role_back(bot, cog, birthday_person):
    bot.guild.roles.append(FakeRole(CAKE_ROLE))
    await bot.store.set(GUILD, "birthday_mode", "on")
    await bot.store.set(GUILD, "birthday_role_id", CAKE_ROLE)
    await stored(bot)
    await cog.run_once(MORNING)

    await change_opt(cog, bot.guild, birthday_person, opted_in=False)

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


# --- the one command and its two panels -------------------------------------------------


async def test_the_command_answers_ephemerally_with_a_panel(cog, bot, birthday_person):
    interaction = await open_panel(cog, bot, birthday_person)

    assert interaction.response.messages[0]["ephemeral"] is True
    assert isinstance(panel_view(interaction), BirthdayView)
    assert panel_embed(interaction).title == "Birthdays"
    assert panel_embed(interaction).colour.value == 0x4EEFFF


async def test_the_command_run_in_a_dm_says_it_belongs_in_the_server(cog, bot, birthday_person):
    interaction = FakeInteraction(bot, birthday_person, guild=False)

    await cog.birthday.callback(cog, interaction)

    assert "in the server itself" in interaction.sent


async def test_the_command_refuses_in_words_when_the_database_is_down(cog, bot, birthday_person):
    class Closed:
        is_connected = False

    bot.db = Closed()
    interaction = FakeInteraction(bot, birthday_person)

    await cog.birthday.callback(cog, interaction)

    assert "database" in interaction.sent


def test_the_group_and_its_twelve_subcommands_are_gone():
    assert isinstance(Birthdays.birthday, discord.app_commands.Command)
    for gone in (
        "birthday_role",
        "birthday_logs",
        "set_mine",
        "set_for",
        "remove",
        "optout",
        "optin",
        "show",
        "next_up",
        "list_all",
        "mode",
        "role_clear",
        "status",
    ):
        assert not hasattr(Birthdays, gone), gone


@pytest.mark.parametrize(
    ("has_date", "opted_out", "expected"),
    [
        (False, False, ["Set my birthday", "Refresh"]),
        (True, False, ["Change my birthday", "Remove", "Opt out", "Refresh"]),
        (True, True, ["Change my birthday", "Remove", "Opt in", "Refresh"]),
    ],
)
async def test_every_state_renders_exactly_its_row_and_nothing_else(
    cog, bot, birthday_person, has_date, opted_out, expected
):
    if has_date:
        await stored(bot)
    if opted_out:
        await set_opted_out(bot.db, USER)

    view = panel_view(await open_panel(cog, bot, birthday_person))

    assert labels(view) == expected
    assert placeholders(view) == ["Look someone up…"]
    assert panel_buttons(has_date, opted_out) == birthdays_cog.panel_buttons(
        has_date, opted_out
    )


async def test_a_staff_panel_fills_all_five_of_discords_rows(cog, bot, birthday_person):
    give_staff(bot, birthday_person)
    await stored(bot)

    view = panel_view(await open_panel(cog, bot, birthday_person))

    assert labels(view) == [
        "Change my birthday",
        "Remove",
        "Opt out",
        "Refresh",
        "Status",
        "Clear the birthday role",
        "Logs",
    ]
    assert placeholders(view) == ["Look someone up…", "List a month…", "Wishes are…"]
    assert sorted({item.row for item in view.children}) == [0, 1, 2, 3, 4]


async def test_a_member_is_offered_no_staff_control_at_all(cog, bot, birthday_person):
    view = panel_view(await open_panel(cog, bot, birthday_person))

    assert "Logs" not in labels(view)
    assert "Status" not in labels(view)
    assert "List a month…" not in placeholders(view)
    assert "Wishes are…" not in placeholders(view)


async def test_the_panel_says_in_words_that_nothing_is_posted_yet(cog, bot, birthday_person):
    shadow = panel_embed(await open_panel(cog, bot, birthday_person)).description
    assert "**shadow**" in shadow and "nothing is posted" in shadow

    await bot.store.set(GUILD, "birthday_mode", "off")
    off = panel_embed(await open_panel(cog, bot, birthday_person)).description
    assert "**off**" in off and "nothing is posted" in off

    await bot.store.set(GUILD, "birthday_mode", "on")
    on = panel_embed(await open_panel(cog, bot, birthday_person)).description
    assert "nothing is posted" not in on


async def test_a_member_with_nothing_stored_is_pointed_at_the_button_not_a_command(
    cog, bot, birthday_person
):
    description = panel_embed(await open_panel(cog, bot, birthday_person)).description

    assert "**Set my birthday** button" in description
    assert "/birthday set" not in description


async def test_your_own_block_carries_the_date_the_year_and_the_next_one(
    cog, bot, birthday_person
):
    await stored(bot, year=1987)

    interaction = await open_panel(cog, bot, birthday_person)

    description = panel_embed(interaction).description
    assert "August 10" in description and "(1987)" in description
    assert "<t:" in description and BIRTHDAY_TZ in description
    assert interaction.response.messages[-1]["allowed_mentions"].everyone is False


async def test_the_age_is_worked_out_at_the_next_birthday_not_this_year(
    cog, bot, birthday_person
):
    await bot.store.set(GUILD, "birthday_show_age", True)
    await stored(bot, month=1, day=2, year=1990)

    description = panel_embed(await open_panel(cog, bot, birthday_person)).description

    when = next_occurrence(1, 2, BIRTHDAY_TZ)
    assert when.date() >= local_today(BIRTHDAY_TZ)
    assert f"turning {when.year - 1990}" in description


async def test_the_panel_says_when_you_are_opted_out(cog, bot, birthday_person):
    await stored(bot)
    await set_opted_out(bot.db, USER)

    description = panel_embed(await open_panel(cog, bot, birthday_person)).description

    assert "You are **opted out**" in description


async def test_coming_up_is_a_key_and_staff_see_it_either_way(cog, bot, birthday_person):
    await stored(bot)

    with_it = panel_embed(await open_panel(cog, bot, birthday_person)).description
    assert "Next birthdays" in with_it and f"<@{USER}>" in with_it

    await bot.store.set(GUILD, "birthday_panel_next_for_members", False)
    without = panel_embed(await open_panel(cog, bot, birthday_person)).description
    assert "Next birthdays" not in without
    assert "for staff" in without

    give_staff(bot, birthday_person)
    staff = panel_embed(await open_panel(cog, bot, birthday_person)).description
    assert "Next birthdays" in staff


async def test_coming_up_shows_at_most_five_soonest_first(cog, bot):
    for index, (month, day) in enumerate([(12, 24), (9, 3), (1, 2), (8, 26), (6, 17), (7, 2)]):
        member = FakeMember(bot.guild, user_id=1000 + index, display_name=f"m{index}")
        await stored(bot, month=month, day=day, user_id=member.id)
    cog = Birthdays(bot)
    bot._cog = cog

    description = panel_embed(
        await open_panel(cog, bot, bot.guild.get_member(1000))
    ).description

    assert description.count("· <@") == 5


async def test_coming_up_says_so_when_there_is_nothing(cog, bot, birthday_person):
    description = panel_embed(await open_panel(cog, bot, birthday_person)).description

    assert "no birthdays to show" in description


async def test_staff_see_the_counts_a_member_never_does(cog, bot, birthday_person):
    await stored(bot)
    plain = panel_embed(await open_panel(cog, bot, birthday_person)).description
    assert "**stored**" not in plain

    give_staff(bot, birthday_person)
    staff = panel_embed(await open_panel(cog, bot, birthday_person)).description
    assert "**stored** — 1 (1 opted in · 0 imported · 1 set by the person)" in staff


async def test_the_lookup_select_is_a_key_and_staff_keep_it(cog, bot, birthday_person):
    assert "Look someone up…" in placeholders(
        panel_view(await open_panel(cog, bot, birthday_person))
    )

    await bot.store.set(GUILD, "birthday_panel_lookup", False)
    assert "Look someone up…" not in placeholders(
        panel_view(await open_panel(cog, bot, birthday_person))
    )

    give_staff(bot, birthday_person)
    assert "Look someone up…" in placeholders(
        panel_view(await open_panel(cog, bot, birthday_person))
    )


# --- the date modal ---------------------------------------------------------------------


async def test_change_my_birthday_opens_a_modal_prefilled_with_what_is_stored(
    cog, bot, birthday_person
):
    await stored(bot, year=1987)
    view = panel_view(await open_panel(cog, bot, birthday_person))

    interaction = await click(bot, birthday_person, find_item(view, "Change my birthday"))

    modal = interaction.response.modals[0]
    assert isinstance(modal, DateModal)
    assert modal.title == "Your birthday"
    assert modal.typed.default == "08-10-1987"
    assert modal.typed.max_length == 10


async def test_setting_a_birthday_stores_it_and_answers_with_the_next_one(
    cog, bot, birthday_person
):
    interaction = await set_through_the_modal(cog, bot, birthday_person, "08-10")

    row = await get_birthday(bot.db, USER)
    assert (row["month"], row["day"], row["source"]) == (8, 10, "self")
    assert "August 10" in interaction.sent and "<t:" in interaction.sent
    assert interaction.response.messages[-1]["ephemeral"] is True
    assert await action_kinds(bot.db) == ["birthday.set"]
    assert "August 10" in card_embed(interaction).description


async def test_the_modal_takes_every_separator_and_both_shapes(cog, bot, birthday_person):
    for typed, expected in (("09/15", (9, 15)), ("09.15", (9, 15)), ("09 15", (9, 15))):
        await set_through_the_modal(cog, bot, birthday_person, typed)
        row = await get_birthday(bot.db, USER)
        assert (row["month"], row["day"]) == expected

    await set_through_the_modal(cog, bot, birthday_person, "09-15-1994")
    assert (await get_birthday(bot.db, USER))["year"] == 1994


async def test_the_date_modal_answers_each_refusal_with_todays_exact_sentence(
    cog, bot, birthday_person
):
    unreadable = await set_through_the_modal(cog, bot, birthday_person, "next tuesday")
    assert "could not read that as a date" in unreadable.sent
    assert await get_birthday(bot.db, USER) is None

    impossible = await set_through_the_modal(cog, bot, birthday_person, "2-30")
    assert "no day" in impossible.sent

    future = await set_through_the_modal(cog, bot, birthday_person, "02-10-2199")
    assert "not a birth year" in future.sent
    assert await get_birthday(bot.db, USER) is None
    assert await action_kinds(bot.db) == []


async def test_setting_a_birthday_again_lets_todays_wish_still_land(bot, cog, birthday_person):
    await bot.store.set(GUILD, "birthday_mode", "on")
    await stored(bot)
    await cog.run_once(MORNING)
    assert len(party_posts(bot)) == 1

    await set_through_the_modal(cog, bot, birthday_person, "08-10")
    await cog.run_once(MORNING)

    assert len(party_posts(bot)) == 2


# --- the member's own moves -------------------------------------------------------------


async def test_opt_out_and_opt_in_swap_the_button_and_move_the_row(cog, bot, birthday_person):
    await stored(bot)
    view = panel_view(await open_panel(cog, bot, birthday_person))

    out = await click(bot, birthday_person, find_item(view, "Opt out"))
    assert (await get_birthday(bot.db, USER))["opted_in"] == 0
    assert labels(card_view(out)) == ["Change my birthday", "Remove", "Opt in", "Refresh"]
    assert "opted out" in out.sent

    await click(bot, birthday_person, find_item(card_view(out), "Opt in"))

    assert (await get_birthday(bot.db, USER))["opted_in"] == 1
    assert await action_kinds(bot.db) == ["birthday.optout", "birthday.optin"]


async def test_remove_asks_first_and_keep_it_changes_nothing(cog, bot, birthday_person):
    await stored(bot)
    view = panel_view(await open_panel(cog, bot, birthday_person))

    confirm = await click(bot, birthday_person, find_item(view, "Remove"))
    assert labels(card_view(confirm)) == ["Yes, forget it", "Keep it"]

    kept = await click(bot, birthday_person, find_item(card_view(confirm), "Keep it"))
    assert await get_birthday(bot.db, USER) is not None
    assert "Change my birthday" in labels(card_view(kept))

    again = await click(bot, birthday_person, find_item(card_view(kept), "Remove"))
    gone = await click(bot, birthday_person, find_item(card_view(again), "Yes, forget it"))

    assert await get_birthday(bot.db, USER) is None
    assert "forgotten" in gone.sent
    assert await action_kinds(bot.db) == ["birthday.remove"]


async def test_no_render_of_the_panel_can_ping_anybody(cog, bot, birthday_person):
    """Checklist 11 — the coming-up list interpolates `<@id>` and display names."""
    await stored(bot)
    interaction = await open_panel(cog, bot, birthday_person)
    assert interaction.response.messages[-1]["allowed_mentions"].users is False

    refreshed = await click(
        bot, birthday_person, find_item(panel_view(interaction), "Refresh")
    )

    assert refreshed.message.kwargs["allowed_mentions"].users is False
    assert refreshed.message.kwargs["allowed_mentions"].everyone is False


async def test_a_re_render_retires_the_view_it_replaced(cog, bot, birthday_person):
    view = panel_view(await open_panel(cog, bot, birthday_person))

    refreshed = await click(bot, birthday_person, find_item(view, "Refresh"))

    assert view.replaced is True
    assert card_view(refreshed) is not view


async def test_the_view_disables_every_item_and_says_so_on_timeout(cog, bot, birthday_person):
    interaction = await open_panel(cog, bot, birthday_person)
    view = panel_view(interaction)
    view.message = await interaction.original_response()

    await view.on_timeout()

    assert all(item.disabled for item in view.children)
    assert view.message.embeds[0].footer.text == (
        "This panel has gone quiet — run /birthday again"
    )


async def test_a_click_after_the_database_goes_away_answers_in_words(
    cog, bot, birthday_person
):
    view = panel_view(await open_panel(cog, bot, birthday_person))
    refresh = find_item(view, "Refresh")
    set_mine = find_item(view, "Set my birthday")

    class Closed:
        is_connected = False

    bot.db = Closed()

    assert "database" in (await click(bot, birthday_person, refresh)).sent
    assert "database" in (await click(bot, birthday_person, set_mine)).sent


# --- looking somebody up ----------------------------------------------------------------


async def test_looking_somebody_up_opens_their_card(cog, bot, birthday_person):
    other = FakeMember(bot.guild, user_id=1001, display_name="Nadia")
    await stored(bot, user_id=other.id, month=1, day=2)
    view = panel_view(await open_panel(cog, bot, birthday_person))
    select = find_select(view, "Look someone up…")
    select._values = [other]

    interaction = await click(bot, birthday_person, select)

    assert "Nadia" in card_embed(interaction).title
    assert "January 2" in card_embed(interaction).description
    assert labels(card_view(interaction)) == ["Back"]

    back = await click(bot, birthday_person, find_item(card_view(interaction), "Back"))
    assert card_embed(back).title == "Birthdays"


async def test_a_card_gives_staff_the_two_moves_a_member_never_sees(
    cog, bot, birthday_person
):
    give_staff(bot, birthday_person)
    other = FakeMember(bot.guild, user_id=1001, display_name="Nadia")
    view = panel_view(await open_panel(cog, bot, birthday_person))
    select = find_select(view, "Look someone up…")
    select._values = [other]

    empty = await click(bot, birthday_person, select)
    assert labels(card_view(empty)) == ["Set their birthday", "Back"]
    assert "no birthday for **Nadia**" in card_embed(empty).description

    opened = await click(
        bot, birthday_person, find_item(card_view(empty), "Set their birthday")
    )
    assert opened.response.modals[0].title == "Set Nadia's birthday"

    filled = FakeInteraction(bot, birthday_person)
    await cog.date_submit(filled, other, "01-02", mine=False)

    row = await get_birthday(bot.db, other.id)
    assert (row["month"], row["day"], row["source"]) == (1, 2, "staff")
    assert "Nadia" in filled.sent
    assert labels(card_view(filled)) == [
        "Set their birthday",
        "Forget their birthday",
        "Back",
    ]


async def test_staff_can_forget_somebody_elses_birthday_and_that_person_is_told(
    cog, bot, birthday_person
):
    give_staff(bot, birthday_person)
    other = FakeMember(bot.guild, user_id=1001, display_name="Nadia")
    await stored(bot, user_id=other.id)
    _, card = await birthdays_cog.build_card(bot, bot.guild, birthday_person, other)

    confirm = await click(bot, birthday_person, find_item(card, "Forget their birthday"))
    assert labels(card_view(confirm)) == ["Yes, forget it", "Keep it"]

    gone = await click(bot, birthday_person, find_item(card_view(confirm), "Yes, forget it"))

    assert await get_birthday(bot.db, other.id) is None
    assert "Nadia" in gone.sent
    assert other.dms and "staff have removed" in other.dms[0]["content"].lower()
    assert await action_kinds(bot.db) == ["birthday.remove"]


async def test_a_member_can_never_forget_or_set_somebody_elses_birthday(
    cog, bot, birthday_person
):
    other = FakeMember(bot.guild, user_id=1001, display_name="Nadia")
    await stored(bot, user_id=other.id)

    _, card = await birthdays_cog.build_card(bot, bot.guild, birthday_person, other)

    assert labels(card) == ["Back"]


# --- the staff controls -----------------------------------------------------------------


async def test_listing_a_month_answers_as_followups_and_leaves_the_panel(
    cog, bot, birthday_person
):
    give_staff(bot, birthday_person)
    await stored(bot)
    await stored(bot, month=1, day=2, user_id=1001, source="import")
    view = panel_view(await open_panel(cog, bot, birthday_person))
    select = find_select(view, "List a month…")
    assert len(select.options) == 13

    select._values = ["0"]
    everything = await click(bot, birthday_person, select)
    assert "**January**" in everything.sent and "**August**" in everything.sent
    assert "import" in everything.sent
    assert everything.message is None

    select._values = ["8"]
    august = await click(bot, birthday_person, select)
    assert "**August**" in august.sent and "**January**" not in august.sent

    select._values = ["3"]
    empty = await click(bot, birthday_person, select)
    assert "stored in **March**" in empty.sent


async def test_a_long_month_arrives_as_more_than_one_message(cog, bot, birthday_person):
    give_staff(bot, birthday_person)
    for index in range(120):
        await stored(bot, month=8, day=1 + index % 28, user_id=3000 + index, source="import")
    view = panel_view(await open_panel(cog, bot, birthday_person))
    select = find_select(view, "List a month…")
    select._values = ["8"]

    interaction = await click(bot, birthday_person, select)

    assert len(interaction.texts) > 1
    assert all(len(page) <= 1900 for page in interaction.texts)


async def test_the_mode_select_writes_the_setting_and_the_warning_changes(
    cog, bot, birthday_person
):
    give_staff(bot, birthday_person)
    view = panel_view(await open_panel(cog, bot, birthday_person))
    select = find_select(view, "Wishes are…")
    assert [option.value for option in select.options] == list(BIRTHDAY_MODES)
    assert [option.value for option in select.options if option.default] == ["shadow"]
    select._values = ["on"]

    interaction = await click(bot, birthday_person, select)

    assert bot.store.get(GUILD, "birthday_mode") == "on"
    assert await action_kinds(bot.db) == ["birthday.mode"]
    assert "nothing is posted" not in card_embed(interaction).description
    assert "now **on**" in interaction.sent


async def test_status_shows_health_not_just_liveness(cog, bot, birthday_person):
    give_staff(bot, birthday_person)
    await stored(bot)
    view = panel_view(await open_panel(cog, bot, birthday_person))

    interaction = await click(bot, birthday_person, find_item(view, "Status"))

    text = interaction.sent
    assert "**mode** — shadow" in text
    assert "**last sweep** — not yet" in text
    assert "**last error** — none" in text
    assert "1 opted in" in text
    assert "role(s)" in text
    assert interaction.message is None


async def test_clearing_the_birthday_role_asks_first_and_says_when_there_was_none(
    cog, bot, birthday_person
):
    give_staff(bot, birthday_person)
    view = panel_view(await open_panel(cog, bot, birthday_person))

    confirm = await click(bot, birthday_person, find_item(view, "Clear the birthday role"))
    assert labels(card_view(confirm)) == ["Yes, clear it", "Cancel"]

    empty = await click(bot, birthday_person, find_item(card_view(confirm), "Yes, clear it"))
    assert "was no birthday role" in empty.sent

    await bot.store.set(GUILD, "birthday_role_id", CAKE_ROLE)
    again = await click(
        bot, birthday_person, find_item(card_view(empty), "Clear the birthday role")
    )
    cleared = await click(bot, birthday_person, find_item(card_view(again), "Yes, clear it"))

    assert bot.store.get(GUILD, "birthday_role_id") is None
    assert "No birthday role" in cleared.sent
    assert await action_kinds(bot.db) == ["settings.clear"]


async def test_the_logs_button_answers_a_new_message_and_refuses_a_stranger(
    cog, bot, birthday_person
):
    give_staff(bot, birthday_person)
    view = panel_view(await open_panel(cog, bot, birthday_person))
    logs = find_item(view, "Logs")

    interaction = await click(bot, birthday_person, logs)
    assert interaction.response.messages[-1].get("embed") is not None
    assert interaction.message is None

    stranger = FakeMember(bot.guild, user_id=1002, display_name="Plain")
    refused = FakeInteraction(bot, stranger)
    await logs.callback(refused)
    assert "staff only" in refused.sent


async def test_a_staffer_demoted_while_the_panel_is_open_moves_nothing(
    cog, bot, birthday_person
):
    role = give_staff(bot, birthday_person)
    other = FakeMember(bot.guild, user_id=1001, display_name="Nadia")
    await stored(bot, user_id=other.id)
    view = panel_view(await open_panel(cog, bot, birthday_person))
    _, card = await birthdays_cog.build_card(bot, bot.guild, birthday_person, other)
    mode = find_select(view, "Wishes are…")
    mode._values = ["on"]
    month = find_select(view, "List a month…")
    month._values = ["0"]

    birthday_person.roles.remove(role)

    for item in (
        mode,
        month,
        find_item(view, "Status"),
        find_item(view, "Clear the birthday role"),
        find_item(card, "Set their birthday"),
        find_item(card, "Forget their birthday"),
    ):
        refused = await click(bot, birthday_person, item)
        assert "staff only" in refused.sent, item.__class__.__name__

    assert bot.store.get(GUILD, "birthday_mode") == "shadow"
    assert await get_birthday(bot.db, other.id) is not None
    assert await action_kinds(bot.db) == []


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


def seed(monkeypatch, rows, as_of=2026):
    monkeypatch.setattr(birthdays_cog, "load_import_rows", lambda *a, **k: list(rows))
    monkeypatch.setattr(birthdays_cog, "import_as_of_year", lambda *a, **k: as_of)


def test_the_import_is_no_longer_a_slash_command():
    assert not hasattr(Birthdays, "import_seed")
    assert not hasattr(Birthdays.birthday, "commands")


async def test_the_daily_loop_brings_the_seed_over_and_records_that_it_ran(
    bot, cog, monkeypatch
):
    pt = FakeMember(bot.guild, user_id=2001, display_name="PT")
    seed(monkeypatch, [ImportRow("[Tired of Planes] PT", 8, 10, 39)])

    await cog._import_loop()

    row = await get_birthday(bot.db, pt.id)
    assert (row["month"], row["day"], row["source"]) == (8, 10, "import")
    assert cog.last_import_at is not None
    assert cog.last_import_error is None
    assert await action_kinds(bot.db) == ["birthday.import"]
    details = json.loads((await details_for(bot.db, "birthday.import"))[0])
    assert details["imported"] == 1
    assert details["trigger"] == "daily"
    assert details["searched"] == len(bot.guild.members)
    assert bot.guild.queries == []


async def test_a_second_daily_run_that_takes_nothing_new_writes_no_log_line(
    bot, cog, monkeypatch
):
    """A daily `0 imported` line in the log channel is noise, so it stays in the process log."""
    FakeMember(bot.guild, user_id=2001, display_name="PT")
    seed(monkeypatch, [ImportRow("[Tired of Planes] PT", 8, 10, 39)])

    await cog._import_loop()
    await cog._import_loop()

    assert await action_kinds(bot.db) == ["birthday.import"]
    assert len(await rows_for_guild(bot.db, GUILD)) == 1
    assert cog.last_import_error is None


async def test_an_empty_seed_file_logs_nothing_and_does_not_raise(bot, cog, monkeypatch):
    seed(monkeypatch, [])

    await cog._import_loop()

    assert await action_kinds(bot.db) == []
    assert await rows_for_guild(bot.db, GUILD) == []
    assert cog.last_import_error is None
    assert cog.last_import_at is not None


async def test_an_import_that_throws_is_recorded_and_does_not_kill_the_loop(
    bot, cog, monkeypatch
):
    async def boom(*args, **kwargs):
        raise RuntimeError("nope")

    seed(monkeypatch, [ImportRow("PT", 8, 10, None)])
    monkeypatch.setattr(cog, "_import", boom)

    await cog._import_loop()

    assert cog.last_import_error == "RuntimeError: nope"
    assert cog.last_import_at is None
    assert await action_kinds(bot.db) == []


async def test_the_daily_import_leaves_an_unavailable_server_alone(bot, cog, monkeypatch):
    FakeMember(bot.guild, user_id=2001, display_name="PT")
    seed(monkeypatch, [ImportRow("[Tired of Planes] PT", 8, 10, 39)])
    bot.guild.unavailable = True

    await cog._import_loop()

    assert await rows_for_guild(bot.db, GUILD) == []
    assert cog.last_import_error is None


async def test_an_import_loop_that_stops_is_recorded_and_started_again(bot, cog):
    await cog._import_stopped(RuntimeError("gateway went away"))

    assert cog.last_import_error == "RuntimeError: gateway went away"


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


async def test_the_counts_used_by_status(bot):
    await stored(bot, user_id=1, source="self")
    await stored(bot, user_id=2, source="import")
    await set_opted_out(bot.db, 2)

    totals = await stored_counts(bot.db, GUILD)

    assert totals == {"stored": 2, "opted_in": 1, "imported": 1, "self": 1}


async def set_opted_out(db, user_id):
    await db.conn.execute("UPDATE birthdays SET opted_in = 0 WHERE user_id = ?", (user_id,))
    await db.conn.commit()


async def test_the_loops_are_registered_on_load_and_cancelled_on_unload(bot, cog):
    await cog.cog_load()
    assert cog._sweep.is_running()
    assert cog._import_loop.is_running()

    await cog.cog_unload()
    await asyncio.sleep(0)
    await asyncio.sleep(0)

    assert not cog._sweep.is_running()
    assert not cog._import_loop.is_running()


async def test_the_loops_are_started_from_on_ready_when_the_database_was_late(bot, cog):
    class Closed:
        is_connected = False

    live = bot.db
    bot.db = Closed()
    await cog.cog_load()
    assert not cog._sweep.is_running()
    assert not cog._import_loop.is_running()

    bot.db = live
    await cog.on_ready()
    assert cog._sweep.is_running()
    assert cog._import_loop.is_running()

    await cog.cog_unload()
    await asyncio.sleep(0)
    await asyncio.sleep(0)


async def test_a_loop_that_stops_is_recorded_and_started_again(bot, cog):
    await cog._sweep_stopped(RuntimeError("gateway went away"))

    assert cog.last_error == "RuntimeError: gateway went away"


async def test_a_sweep_that_throws_is_recorded_not_swallowed_silently(bot, cog, monkeypatch):
    async def boom(*args, **kwargs):
        raise RuntimeError("nope")

    monkeypatch.setattr(cog, "run_once", boom)

    await cog._sweep()

    assert cog.last_error == "RuntimeError: nope"
    assert cog.last_run_at is None
