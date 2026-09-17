"""C5: every path here is proved with fakes — no Community guild was available to the build."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from black_bloc import pings
from black_bloc import pings_onboarding as onboarding
from black_bloc.cogs.community.role_menus import get_menu, set_message
from black_bloc.config import load_settings
from black_bloc.settings_store import SettingsStore

GUILD = 7
LOG_CHANNEL = 222
STREAMER = 900
FAN = 901
STAFF = 5


class FakeRole:
    def __init__(self, role_id, name):
        self.id = role_id
        self.name = name
        self.members = []
        self.deleted = False

    def is_assignable(self):
        return True

    async def delete(self, reason=None):
        self.deleted = True


class FakeMember:
    def __init__(self, guild, user_id, display_name="Alice"):
        self.id = user_id
        self.guild = guild
        self.display_name = display_name
        self.name = display_name
        self.bot = False
        self.roles = []
        guild.members[user_id] = self

    async def add_roles(self, *roles, reason=None):
        self.roles += [role for role in roles if role not in self.roles]

    async def remove_roles(self, *roles, reason=None):
        self.roles = [role for role in self.roles if role not in roles]


class FakeChannel:
    def __init__(self, channel_id=LOG_CHANNEL):
        self.id = channel_id
        self.messages = []
        self.deleted = []

    async def send(self, content=None, **kwargs):
        found = SimpleNamespace(id=9000 + len(self.messages), content=content)
        self.messages.append(found)
        return found

    def get_partial_message(self, message_id):
        channel = self

        class Partial:
            async def delete(self_inner):
                channel.deleted.append(message_id)

        return Partial()


class FakeGuild:
    """Onboarding as discord.py hands it over: prompts in, prompts out, nothing else touched."""

    def __init__(self, features=("COMMUNITY",)):
        self.id = GUILD
        self.features = list(features)
        self.roles = []
        self.members = {}
        self.channel = FakeChannel()
        self.prompts: list = []
        self.default_channel_ids = {55, 66}
        self.enabled = True
        self.writes: list = []
        self.refuse = None

    def get_role(self, role_id):
        return next((role for role in self.roles if role.id == int(role_id)), None)

    def get_member(self, user_id):
        return self.members.get(int(user_id))

    def get_channel(self, channel_id):
        return self.channel if channel_id == self.channel.id else None

    def add_role(self, role):
        self.roles.append(role)
        return role

    async def create_role(self, name=None, mentionable=False, reason=None):
        return self.add_role(FakeRole(1000 + len(self.roles), name))

    async def onboarding(self):
        return SimpleNamespace(
            prompts=list(self.prompts),
            default_channel_ids=set(self.default_channel_ids),
            enabled=self.enabled,
        )

    async def edit_onboarding(self, *, prompts=None, reason=None, **rest):
        if self.refuse is not None:
            raise self.refuse
        self.writes.append(list(prompts or []))
        self.prompts = list(prompts or [])
        return await self.onboarding()


class FakeBot:
    def __init__(self, db, store, settings, guild):
        self.db = db
        self.store = store
        self.settings = settings
        self.guild = guild
        self.guilds = [guild]
        self.guard = None

    def get_channel(self, channel_id):
        return self.guild.get_channel(channel_id)

    def get_guild(self, guild_id):
        return self.guild if self.guild.id == guild_id else None

    def add_view(self, view, message_id=None):
        return None


def a_foreign_prompt(title="Where are you from?"):
    return SimpleNamespace(
        id=99,
        title=title,
        options=[SimpleNamespace(id=1, title="Here", role_ids={4242}, description=None)],
        single_select=True,
        required=True,
        in_onboarding=True,
    )


@pytest.fixture
async def bot(db, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    settings = load_settings(_env_file=None, test_mode=True, test_channel_id=LOG_CHANNEL)
    store = SettingsStore(db, settings)
    await store.load()
    await store.set(GUILD, "log_channel_id", LOG_CHANNEL)
    await store.set(GUILD, "pings_mode", "on")
    return FakeBot(db, store, settings, FakeGuild())


@pytest.fixture
def streamer(bot):
    return FakeMember(bot.guild, STREAMER, "SuperNamu")


async def kinds(db):
    cur = await db.conn.execute("SELECT kind FROM action_log ORDER BY id")
    return [row["kind"] for row in await cur.fetchall()]


async def details(db, kind):
    cur = await db.conn.execute(
        "SELECT details FROM action_log WHERE kind = ? ORDER BY id DESC LIMIT 1", (kind,)
    )
    row = await cur.fetchone()
    return json.loads(row["details"]) if row and row["details"] else None


async def a_followed_streamer(bot, streamer, fan_id=FAN):
    await pings.saw_streaming(bot, bot.guild, streamer, "twitch", None)
    made = await pings.ensure_fan_role(bot, bot.guild, streamer, by=STAFF, staff=True)
    role = bot.guild.get_role(made.role_id)
    role.members.append(FakeMember(bot.guild, fan_id, f"fan{fan_id}"))
    return role


# --- the gate ------------------------------------------------------------------------------------


async def test_without_the_community_feature_every_move_refuses_in_words(bot, streamer):
    bot.guild.features = []
    await pings.setup_events_role(bot, bot.guild, by=STAFF)

    result = await onboarding.reconcile(bot, bot.guild, by=STAFF, asked=True)

    assert result.ok is False and result.reason == onboarding.NO_COMMUNITY_REASON
    assert "not a Community server" in result.message
    assert bot.guild.writes == []
    assert not [one for one in await kinds(bot.db) if one.startswith("pings.onboarding")]


async def test_the_managed_switch_off_stops_every_write(bot):
    await pings.setup_events_role(bot, bot.guild, by=STAFF)
    await bot.store.set(GUILD, pings.ONBOARDING_MANAGED_KEY, False)

    result = await onboarding.reconcile(bot, bot.guild, by=STAFF, asked=True)

    assert result.reason == onboarding.NOT_MANAGED_REASON
    assert bot.guild.writes == []


async def test_nothing_worth_saying_writes_nothing_rather_than_an_empty_prompt(bot):
    """Discord will not take a prompt with no options on it, so Black Bloc never asks."""
    result = await onboarding.reconcile(bot, bot.guild, by=STAFF, asked=True)

    assert result.reason == onboarding.NOTHING_REASON
    assert bot.guild.writes == []


# --- what it writes ------------------------------------------------------------------------------


async def test_the_first_sync_writes_both_prompts_and_a_second_writes_nothing(bot, streamer):
    await pings.setup_events_role(bot, bot.guild, by=STAFF)
    await pings.setup_raidtrain_role(bot, bot.guild, by=STAFF)
    role = await a_followed_streamer(bot, streamer)

    first = await onboarding.reconcile(bot, bot.guild, by=STAFF, asked=True)

    assert first.ok and first.wrote and len(bot.guild.writes) == 1
    written = bot.guild.writes[0]
    assert [one.title for one in written] == [
        "What should ping you?",
        onboarding.STREAMER_PROMPT_TITLE,
    ]
    assert [one.title for one in written[0].options] == ["Events and go-lives", "Raid trains"]
    assert written[1].options[0].role_ids == {role.id}
    assert all(one.single_select is False and one.required is False for one in written)
    assert "pings.onboarding_synced" in await kinds(bot.db)

    again = await onboarding.reconcile(bot, bot.guild, by=STAFF, asked=True)

    assert again.ok and again.wrote is False
    assert again.reason == onboarding.UNCHANGED_REASON
    assert len(bot.guild.writes) == 1


async def test_a_foreign_prompt_is_carried_through_untouched(bot, streamer):
    foreign = a_foreign_prompt()
    bot.guild.prompts = [foreign]
    await pings.setup_events_role(bot, bot.guild, by=STAFF)

    result = await onboarding.reconcile(bot, bot.guild, by=STAFF, asked=True)

    written = bot.guild.writes[0]
    assert written[0] is foreign
    assert [one.title for one in written[1:]] == ["What should ping you?"]
    assert result.foreign == 1
    assert (await details(bot.db, "pings.onboarding_synced"))["foreign_kept"] == 1

    unchanged = await onboarding.reconcile(bot, bot.guild, by=STAFF, asked=True)
    assert unchanged.wrote is False and len(bot.guild.writes) == 1


async def test_the_default_channels_and_the_enabled_flag_are_never_passed(bot):
    """`edit_onboarding` only sends what it is given, so passing prompts alone leaves the
    default channels and `enabled` exactly as Discord had them (measured in discord/http.py)."""
    await pings.setup_events_role(bot, bot.guild, by=STAFF)

    await onboarding.reconcile(bot, bot.guild, by=STAFF, asked=True)

    assert bot.guild.default_channel_ids == {55, 66}
    assert bot.guild.enabled is True


async def test_discord_refusing_the_write_is_a_sentence_and_one_log_row(bot):
    await pings.setup_events_role(bot, bot.guild, by=STAFF)
    bot.guild.refuse = RuntimeError("Missing Permissions")

    result = await onboarding.reconcile(bot, bot.guild, by=STAFF, asked=True)

    assert result.ok is False and result.reason == onboarding.REFUSED_REASON
    assert "Missing Permissions" in result.message
    assert "Manage Server" in result.message
    assert (await kinds(bot.db)).count("pings.onboarding_failed") == 1


async def test_a_read_discord_refuses_never_writes_anything(bot):
    await pings.setup_events_role(bot, bot.guild, by=STAFF)

    async def boom():
        raise RuntimeError("Missing Access")

    bot.guild.onboarding = boom

    result = await onboarding.reconcile(bot, bot.guild, by=STAFF, asked=True)

    assert result.reason == onboarding.REFUSED_REASON and bot.guild.writes == []


# --- the streamer prompt -------------------------------------------------------------------------


async def test_the_streamer_prompt_is_most_followed_first_and_capped(bot):
    await bot.store.set(GUILD, pings.ONBOARDING_CAP_KEY, 2)
    for spot, followers in enumerate([1, 5, 3]):
        member = FakeMember(bot.guild, 800 + spot, f"streamer{spot}")
        role = await a_followed_streamer(bot, member, fan_id=7000 + spot)
        for extra in range(followers - 1):
            role.members.append(FakeMember(bot.guild, 7500 + spot * 10 + extra, "x"))

    options, more = await onboarding.streamer_options(bot, bot.guild)

    assert [title for title, _roles, _note in options] == ["streamer1 pings", "streamer2 pings"]
    assert more == 1


async def test_a_hidden_streamer_is_left_off_the_onboarding_prompt(bot, streamer):
    await a_followed_streamer(bot, streamer)
    await pings.hide_streamer(bot, bot.guild, STREAMER, by=STAFF)

    options, more = await onboarding.streamer_options(bot, bot.guild)

    assert options == () and more == 0


# --- taking over ---------------------------------------------------------------------------------


async def test_the_first_sync_takes_the_notifications_menu_down(bot):
    setup = await pings.setup_events_role(bot, bot.guild, by=STAFF)
    menu = await get_menu(bot.db, GUILD, pings.NOTIFICATIONS_MENU)
    await set_message(bot.db, menu["id"], LOG_CHANNEL, 4242)

    await onboarding.reconcile(bot, bot.guild, by=STAFF, asked=True)

    assert bot.guild.channel.deleted == [4242]
    assert "pings.onboarding_took_over" in await kinds(bot.db)
    assert setup.role_id is not None

    await bot.store.set(GUILD, pings.ONBOARDING_TITLE_KEY, "Pings?")
    await onboarding.reconcile(bot, bot.guild, by=STAFF, asked=True)

    assert (await kinds(bot.db)).count("pings.onboarding_took_over") == 1


# --- the staff card ------------------------------------------------------------------------------


async def test_the_card_says_what_the_prompts_hold_and_what_is_not_black_blocs(bot, streamer):
    bot.guild.prompts = [a_foreign_prompt()]
    await pings.setup_events_role(bot, bot.guild, by=STAFF)
    await a_followed_streamer(bot, streamer)
    result = await onboarding.reconcile(bot, bot.guild, by=STAFF, asked=True)

    lines = onboarding.card_lines(bot.guild, result, managed_now=True, last="2026-09-17")

    said = "\n".join(lines)
    assert "What should ping you?" in said and "Which streamers?" in said
    assert "SuperNamu pings" in said
    assert "belong to somebody else" in said
    assert "Last written: 2026-09-17" in said


async def test_the_card_says_the_two_reasons_there_is_nothing_to_show(bot):
    """Both reasons stand on their own and both are said when both apply — a card that named
    only the Community half would read as if the managed switch were still on."""
    empty = onboarding.Result(True, onboarding.UNCHANGED_REASON, "")
    assert onboarding.card_lines(bot.guild, empty, managed_now=False) == [
        onboarding.CARD_NOT_MANAGED
    ]

    bot.guild.features = []
    assert onboarding.card_lines(bot.guild, empty, managed_now=True) == [
        onboarding.CARD_NO_COMMUNITY
    ]
    assert onboarding.card_lines(bot.guild, empty, managed_now=False) == [
        onboarding.CARD_NOT_MANAGED,
        onboarding.CARD_NO_COMMUNITY,
    ]


async def test_the_last_sync_comes_off_the_log_and_never_a_second_timestamp_key(bot):
    assert await onboarding.last_sync(bot, GUILD) is None

    await pings.setup_events_role(bot, bot.guild, by=STAFF)
    await onboarding.reconcile(bot, bot.guild, by=STAFF, asked=True)

    assert await onboarding.last_sync(bot, GUILD) is not None
