from types import SimpleNamespace

import discord
import pytest

from black_bloc import actionlog, chat_panel, knowledge, personas
from black_bloc import chat as chat_module
from black_bloc import chat_llm as chat_llm_module
from black_bloc.actionlog import log_action
from black_bloc.chat import (
    BUILTIN_ORDER,
    UNKNOWN,
    add_line,
    invalidate,
    lines_for,
    list_intents,
    loaded_intents,
    seed_defaults,
    update_line,
)
from black_bloc.chat_llm import tier_errors
from black_bloc.cogs.content import chat as cog_module
from black_bloc.cogs.content.chat import Chat, in_a_thread, mentions_bot
from black_bloc.config import load_settings
from black_bloc.llm import ANTHROPIC, MODEL, Usage, record
from black_bloc.personas import list_tropes
from black_bloc.settings_store import (
    CHAT_COOLDOWN_SECONDS,
    DB_UNAVAILABLE,
    SettingsStore,
)
from black_bloc.storage.db import Database

GUILD = 7
CHANNEL = 111
LOG_CHANNEL = 222
USER = 900
BOT_ID = 55
ORIGIN = "https://blackbloc.example"


class StaffRole:
    def __init__(self, role_id, name):
        self.id = role_id
        self.name = name

    def is_default(self):
        return self.id == GUILD

    def is_bot_managed(self):
        return False


class FakePermissions:
    def __init__(self, view_channel):
        self.view_channel = view_channel


class FakeChannel:
    def __init__(self, channel_id=CHANNEL, kind="text"):
        self.id = channel_id
        self.type = SimpleNamespace(name=kind)
        self.mention = f"<#{channel_id}>"
        self.messages = []
        self.viewers = set()

    def permissions_for(self, role):
        return FakePermissions(getattr(role, "id", None) in self.viewers)

    async def send(self, content=None, **kwargs):
        self.messages.append({"content": content, "kwargs": kwargs})
        return None


EVERYONE = StaffRole(GUILD, "@everyone")


def open_channel(name, topic=None, category=None):
    return SimpleNamespace(
        name=name,
        topic=topic,
        category=category,
        category_id=getattr(category, "id", None),
        permissions_for=lambda role: FakePermissions(True),
    )


def shut_channel(name, topic=None, category=None):
    return SimpleNamespace(
        name=name,
        topic=topic,
        category=category,
        category_id=getattr(category, "id", None),
        permissions_for=lambda role: FakePermissions(False),
    )


class FakeGuild:
    def __init__(self):
        self.id = GUILD
        self.member_count = 12
        self.members = []
        self.roles = []
        self.default_role = EVERYONE
        self.text_channels = []
        self.channels = {CHANNEL: FakeChannel(CHANNEL), LOG_CHANNEL: FakeChannel(LOG_CHANNEL)}

    def get_channel(self, channel_id):
        return self.channels.get(channel_id)

    def get_role(self, role_id):
        return next((r for r in self.roles if r.id == int(role_id)), None)


class FakeMember:
    def __init__(
        self, guild, user_id=USER, display_name="Nia", bot=False, admin=True, roles=()
    ):
        self.id = user_id
        self.guild = guild
        self.display_name = display_name
        self.name = display_name
        self.bot = bot
        self.roles = list(roles)
        self.mention = f"<@{user_id}>"
        self.guild_permissions = SimpleNamespace(administrator=admin, manage_guild=False)


class FakeMessage:
    def __init__(
        self,
        author,
        content,
        *,
        guild=None,
        channel=None,
        mentions=None,
        mention_everyone=False,
        kind=discord.MessageType.default,
        webhook_id=None,
        raises=None,
    ):
        self.author = author
        self.content = content
        self.guild = guild
        self.channel = channel or FakeChannel()
        self.mentions = mentions if mentions is not None else []
        self.mention_everyone = mention_everyone
        self.type = kind
        self.webhook_id = webhook_id
        self.replies = []
        self.reactions = []
        self.raises = raises
        self.jump_url = "https://discord.test/1"

    async def reply(self, content=None, **kwargs):
        if self.raises is not None:
            raise self.raises
        self.replies.append({"content": content, "kwargs": kwargs})
        return None

    async def add_reaction(self, emoji):
        self.reactions.append(emoji)


class FakeUser:
    def __init__(self, user_id=BOT_ID):
        self.id = user_id


class FakeGuard:
    def __init__(self, allowed=CHANNEL):
        self.allowed = allowed

    def allows_channel(self, channel):
        return getattr(channel, "id", channel) == self.allowed


class FakeBot:
    def __init__(self, db, store, settings, guild):
        self.db = db
        self.store = store
        self.settings = settings
        self.guild = guild
        self.guilds = [guild]
        self.user = FakeUser()
        self.guard = None
        self.cogs = {}

    def get_channel(self, channel_id):
        return self.guild.get_channel(channel_id)

    def get_cog(self, name):
        return self.cogs.get(name)


@pytest.fixture
async def db(tmp_path):
    database = Database(tmp_path / "c.sqlite3")
    await database.connect()
    try:
        yield database
    finally:
        await database.close()


@pytest.fixture
async def bot(db, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    settings = load_settings(_env_file=None, test_mode=True, test_channel_id=CHANNEL)
    store = SettingsStore(db, settings)
    await store.load()
    await store.set(GUILD, "log_channel_id", LOG_CHANNEL)
    return FakeBot(db, store, settings, FakeGuild())


@pytest.fixture
def cog(bot):
    made = Chat(bot)
    bot.cogs["Chat"] = made
    return made


@pytest.fixture
async def off_the_site(db, monkeypatch):
    """A second bot with no dashboard address at all, so the link has nowhere to go."""
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    settings = load_settings(
        _env_file=None, test_mode=True, test_channel_id=CHANNEL, site_origin=""
    )
    store = SettingsStore(db, settings)
    await store.load()
    await store.set(GUILD, "log_channel_id", LOG_CHANNEL)
    alone = FakeBot(db, store, settings, FakeGuild())
    made = Chat(alone)
    alone.cogs["Chat"] = made
    return (made, alone)


@pytest.fixture
def member(bot):
    return FakeMember(bot.guild)


def pinged(bot, member, content="hi", **kwargs):
    kwargs.setdefault("mentions", [bot.user])
    return FakeMessage(
        member,
        content,
        guild=member.guild,
        channel=bot.guild.get_channel(CHANNEL),
        **kwargs,
    )


async def rows(db, kind):
    cur = await db.conn.execute("SELECT * FROM action_log WHERE kind = ?", (kind,))
    return await cur.fetchall()


def test_mentions_bot_ignores_everyone_and_role_pings():
    me = FakeUser()
    assert mentions_bot(FakeMessage(None, "hi", mentions=[me]), me) is True
    assert mentions_bot(FakeMessage(None, "hi", mentions=[]), me) is False
    assert (
        mentions_bot(FakeMessage(None, "hi", mentions=[me], mention_everyone=True), me) is False
    )
    assert mentions_bot(FakeMessage(None, "hi", mentions=[me]), None) is False


async def test_an_at_mention_gets_a_reply_that_pings_nobody(cog, bot, member):
    message = pinged(bot, member, "<@55> hi there")
    await cog.on_message(message)

    assert len(message.replies) == 1
    reply = message.replies[0]
    assert "Nia" in reply["content"]
    assert reply["kwargs"]["mention_author"] is False
    assert reply["kwargs"]["allowed_mentions"].everyone is False
    assert reply["kwargs"]["allowed_mentions"].users is False
    assert reply["kwargs"]["allowed_mentions"].roles is False


async def a_staff_member(bot):
    """The canonical rule: a role that can see the staff channel. Nothing else is invented."""
    role = StaffRole(11, "Aunties / Uncles")
    bot.guild.roles = [role, StaffRole(GUILD, "@everyone")]
    bot.guild.channels[LOG_CHANNEL].viewers = {11}
    await bot.store.set(GUILD, "staff_channel_id", LOG_CHANNEL)
    return FakeMember(bot.guild, user_id=901, display_name="Pawpette", roles=[role])


async def test_a_staff_member_may_let_the_answer_mention_a_role(cog, bot):
    lead = await a_staff_member(bot)

    message = pinged(bot, lead, "<@55> hi there")
    await cog.on_message(message)

    allowed = message.replies[0]["kwargs"]["allowed_mentions"]
    assert allowed.roles is True
    assert allowed.everyone is False and allowed.users is False


async def test_the_exception_can_be_switched_off_and_then_staff_ping_nobody_either(cog, bot):
    lead = await a_staff_member(bot)
    await bot.store.set(GUILD, "chat_staff_can_ping_roles", False)

    message = pinged(bot, lead, "<@55> hi there")
    await cog.on_message(message)

    assert message.replies[0]["kwargs"]["allowed_mentions"].roles is False


async def test_a_member_who_is_not_staff_can_never_make_it_ping_a_role(cog, bot, member):
    await a_staff_member(bot)

    message = pinged(bot, member, "<@55> hi there")
    await cog.on_message(message)

    allowed = message.replies[0]["kwargs"]["allowed_mentions"]
    assert allowed.roles is False and allowed.everyone is False and allowed.users is False


async def test_a_dm_pings_nobody_whoever_sent_it(cog, bot, member):
    message = pinged(bot, member, "<@55> hi there")
    message.guild = None

    await cog.on_message(message)

    allowed = message.replies[0]["kwargs"]["allowed_mentions"]
    assert allowed.roles is False and allowed.everyone is False


async def test_another_bot_is_never_answered(cog, bot):
    other = FakeMember(bot.guild, user_id=41, display_name="OtherBot", bot=True)
    message = pinged(bot, other)
    await cog.on_message(message)
    assert message.replies == []


async def test_a_message_without_the_mention_is_ignored(cog, bot, member):
    message = pinged(bot, member, "hi everyone", mentions=[])
    await cog.on_message(message)
    assert message.replies == []


async def test_a_webhook_or_system_message_is_ignored(cog, bot, member):
    hook = pinged(bot, member, "<@55> hi", webhook_id=99)
    await cog.on_message(hook)
    system = pinged(bot, member, "<@55> hi", kind=discord.MessageType.pins_add)
    await cog.on_message(system)
    assert hook.replies == [] and system.replies == []


async def test_chat_mode_off_says_nothing(cog, bot, member):
    await bot.store.set(GUILD, "chat_mode", "off")
    message = pinged(bot, member, "<@55> hi")
    await cog.on_message(message)
    assert message.replies == []


async def test_the_cooldown_is_honoured_and_the_cooled_down_user_gets_nothing(cog, bot, member):
    first = pinged(bot, member, "<@55> hi")
    await cog.on_message(first)
    second = pinged(bot, member, "<@55> hi again")
    await cog.on_message(second)

    assert len(first.replies) == 1
    assert second.replies == []


async def test_the_cooldown_is_per_user(cog, bot, member):
    await cog.on_message(pinged(bot, member, "<@55> hi"))
    other = FakeMember(bot.guild, user_id=901, display_name="Sam")
    second = pinged(bot, other, "<@55> hi")
    await cog.on_message(second)
    assert len(second.replies) == 1


async def test_a_zero_cooldown_answers_every_time(cog, bot, member):
    await bot.store.set(GUILD, "chat_cooldown_seconds", 5)
    cog._answered[USER] = -1000.0
    message = pinged(bot, member, "<@55> hi")
    await cog.on_message(message)
    assert len(message.replies) == 1


async def test_test_mode_outside_the_test_channel_is_silent_not_an_error(cog, bot, member, caplog):
    bot.guard = FakeGuard(allowed=CHANNEL)
    elsewhere = FakeChannel(999)
    message = FakeMessage(
        member,
        "<@55> hi",
        guild=bot.guild,
        channel=elsewhere,
        mentions=[bot.user],
    )
    with caplog.at_level("WARNING"):
        await cog.on_message(message)

    assert message.replies == []
    assert caplog.records == []


async def test_the_test_channel_is_still_answered_under_the_guard(cog, bot, member):
    bot.guard = FakeGuard(allowed=CHANNEL)
    message = pinged(bot, member, "<@55> hey")
    await cog.on_message(message)
    assert len(message.replies) == 1


async def test_an_insult_writes_an_action_row_and_a_greeting_does_not(cog, bot, member, db):
    await cog.on_message(pinged(bot, member, "<@55> you suck"))
    found = await rows(db, "chat.insult")
    assert len(found) == 1
    assert found[0]["actor_id"] == USER
    assert '"intent": "insult"' in found[0]["details"]

    other = FakeMember(bot.guild, user_id=902, display_name="Kay")
    await cog.on_message(pinged(bot, other, "<@55> hi"))
    assert len(await rows(db, "chat.insult")) == 1


async def test_a_failed_reply_leaves_no_cooldown_and_no_action_row(cog, bot, member, db):
    message = pinged(bot, member, "<@55> you suck", raises=RuntimeError("boom"))
    await cog.on_message(message)

    assert USER not in cog._answered
    assert await rows(db, "chat.insult") == []


async def test_a_reply_in_a_dm_needs_no_guild_setting_but_still_cools_down(cog, bot):
    lone = FakeMember(None, user_id=903, display_name="Ana")
    lone.guild = None
    first = FakeMessage(lone, "<@55> hi", guild=None, mentions=[bot.user])
    await cog.on_message(first)
    second = FakeMessage(lone, "<@55> hi", guild=None, mentions=[bot.user])
    await cog.on_message(second)

    assert len(first.replies) == 1
    assert second.replies == []
    assert cog.cooldown_seconds(None) == CHAT_COOLDOWN_SECONDS


async def test_the_cog_seeds_the_code_tables_the_first_time_it_loads(cog, bot, db):
    await cog.cog_load()

    stored = await loaded_intents(db, GUILD)

    assert {row["name"] for row in stored} == set(BUILTIN_ORDER) | {UNKNOWN}
    assert bot.guild.id in cog._seeded
    assert await seed_defaults(db, GUILD) == 0


async def test_seeding_runs_once_per_guild_however_often_on_ready_fires(cog, bot, db):
    await cog.on_ready()
    await cog.on_ready()

    cur = await db.conn.execute(
        "SELECT COUNT(*) AS n FROM chat_intents WHERE guild_id = ?", (GUILD,)
    )
    assert (await cur.fetchone())["n"] == len(BUILTIN_ORDER) + 1


async def test_an_edited_line_is_what_the_member_is_sent(cog, bot, db, member):
    await cog.cog_load()
    greeting = next(r for r in await list_intents(db, GUILD) if r["name"] == "greeting")
    for line in await lines_for(db, greeting["id"]):
        await update_line(db, line["id"], enabled=False)
    await add_line(db, greeting["id"], "Edited hello, {name}.")
    invalidate(bot, GUILD)

    message = pinged(bot, member, "<@55> hi there")
    await cog.on_message(message)

    assert message.replies[0]["content"] == "Edited hello, Nia."


async def test_a_settings_change_drops_the_cached_rows(cog, bot, db, member):
    await cog.cog_load()
    await cog.on_message(pinged(bot, member, "<@55> hi"))
    greeting = next(r for r in await list_intents(db, GUILD) if r["name"] == "greeting")
    for line in await lines_for(db, greeting["id"]):
        await update_line(db, line["id"], enabled=False)
    await add_line(db, greeting["id"], "After the change, {name}.")

    await bot.store.set(GUILD, "chat_reply_in_threads", True)

    other = FakeMember(bot.guild, user_id=905, display_name="Kay")
    message = pinged(bot, other, "<@55> hi")
    await cog.on_message(message)

    assert message.replies[0]["content"] == "After the change, Kay."


async def test_an_ignored_channel_is_never_answered(cog, bot, member):
    await bot.store.set(GUILD, "chat_ignore_channels", [CHANNEL])
    message = pinged(bot, member, "<@55> hi")
    await cog.on_message(message)
    assert message.replies == []


async def test_a_thread_is_answered_unless_the_server_says_otherwise(cog, bot, member):
    thread = FakeChannel(777, kind="public_thread")
    inside = FakeMessage(
        member, "<@55> hi", guild=bot.guild, channel=thread, mentions=[bot.user]
    )
    await cog.on_message(inside)
    assert len(inside.replies) == 1

    await bot.store.set(GUILD, "chat_reply_in_threads", False)
    other = FakeMember(bot.guild, user_id=906, display_name="Sam")
    quiet = FakeMessage(other, "<@55> hi", guild=bot.guild, channel=thread, mentions=[bot.user])
    await cog.on_message(quiet)
    assert quiet.replies == []


async def test_a_bare_hello_gets_a_toned_wave_instead_of_a_sentence(cog, bot, member):
    await bot.store.set(GUILD, "chat_greeting_reaction", True)

    message = pinged(bot, member, "<@55> hi")
    await cog.on_message(message)

    assert message.replies == []
    assert message.reactions == ["\U0001f44b\U0001f3ff"]
    assert USER in cog._answered


async def test_a_greeting_with_a_question_after_it_still_gets_words(cog, bot, member):
    await bot.store.set(GUILD, "chat_greeting_reaction", True)

    message = pinged(bot, member, "<@55> hi, how are you")
    await cog.on_message(message)

    assert len(message.replies) == 1 and message.reactions == []


async def test_the_wave_obeys_the_same_channel_guard_the_reply_does(cog, bot, member):
    await bot.store.set(GUILD, "chat_greeting_reaction", True)
    bot.guard = FakeGuard(allowed=CHANNEL)
    elsewhere = FakeChannel(999)
    message = FakeMessage(
        member, "<@55> hi", guild=bot.guild, channel=elsewhere, mentions=[bot.user]
    )

    await cog.on_message(message)

    assert message.replies == [] and message.reactions == []


async def test_a_data_intent_is_answered_from_live_state(cog, bot, member):
    message = pinged(bot, member, "<@55> how many of us are here")
    await cog.on_message(message)

    assert "12" in message.replies[0]["content"]


async def test_a_data_intent_with_nothing_to_report_uses_its_empty_line(cog, bot, member):
    message = pinged(bot, member, "<@55> whos live")
    await cog.on_message(message)

    assert "Nobody is streaming" in message.replies[0]["content"]


async def test_asking_for_a_mod_with_modmail_on_says_how_and_logs_the_route(cog, bot, member, db):
    await bot.store.set(GUILD, "modmail_enabled", True)

    message = pinged(bot, member, "<@55> i need a mod")
    await cog.on_message(message)

    assert "DM me" in message.replies[0]["content"]
    found = await rows(db, "chat.route")
    assert len(found) == 1 and found[0]["actor_id"] == USER


async def test_asking_for_a_mod_with_modmail_off_names_the_staff_roles(cog, bot, member, db):
    bot.guild.roles = [StaffRole(11, "Aunties / Uncles"), StaffRole(GUILD, "@everyone")]
    bot.guild.channels[LOG_CHANNEL].viewers = {11}
    await bot.store.set(GUILD, "staff_channel_id", LOG_CHANNEL)

    message = pinged(bot, member, "<@55> i need a mod")
    await cog.on_message(message)

    assert "Aunties / Uncles" in message.replies[0]["content"]
    assert len(await rows(db, "chat.route")) == 1


async def test_the_owners_live_sentence_answers_about_the_person_they_named(cog, bot, member):
    """2026-09-01: "im looking for a mod can I trust @Pawpette" got "I don't know, ping @Admin"."""
    lead = await a_staff_member(bot)
    bot.guild.members = [lead]
    bot.guild.get_member = lambda user_id: lead if int(user_id) == lead.id else None

    message = pinged(bot, member, f"<@55> im looking for a mod can i trust <@{lead.id}>")
    await cog.on_message(message)

    said = message.replies[0]["content"]
    assert "Pawpette" in said
    assert "Aunties / Uncles" in said
    assert said.count("Yes — that is staff") == 1


async def test_asking_for_a_mod_names_who_is_about_without_pinging_them(cog, bot, member):
    lead = await a_staff_member(bot)
    lead.status = SimpleNamespace(name="online")
    bot.guild.roles[0].members = [lead]

    message = pinged(bot, member, "<@55> im looking for a mod")
    await cog.on_message(message)

    said = message.replies[0]["content"]
    assert "Online right now: Pawpette" in said
    assert f"<@{lead.id}>" not in said


async def test_the_staff_note_is_posted_only_when_the_setting_asks_for_it(cog, bot, member):
    await bot.store.set(GUILD, "modmail_enabled", True)
    await bot.store.set(GUILD, "staff_channel_id", LOG_CHANNEL)
    staff = bot.guild.get_channel(LOG_CHANNEL)

    await cog.on_message(pinged(bot, member, "<@55> i need a mod"))
    assert [m for m in staff.messages if "asked for a mod" in str(m["content"])] == []

    await bot.store.set(GUILD, "chat_route_ping_staff", True)
    other = FakeMember(bot.guild, user_id=907, display_name="Ash")
    await cog.on_message(pinged(bot, other, "<@55> i need a mod"))

    note = [m for m in staff.messages if "asked for a mod" in str(m["content"])]
    assert len(note) == 1
    assert "https://discord.test/1" in note[0]["content"]
    assert note[0]["kwargs"]["allowed_mentions"].everyone is False


async def test_the_staff_note_is_not_posted_while_modmail_is_off(cog, bot, member):
    await bot.store.set(GUILD, "chat_route_ping_staff", True)
    await bot.store.set(GUILD, "staff_channel_id", LOG_CHANNEL)
    staff = bot.guild.get_channel(LOG_CHANNEL)

    await cog.on_message(pinged(bot, member, "<@55> i need a mod"))

    assert [m for m in staff.messages if "asked for a mod" in str(m["content"])] == []


async def test_the_staff_note_obeys_the_guard(cog, bot, member, caplog):
    await bot.store.set(GUILD, "modmail_enabled", True)
    await bot.store.set(GUILD, "chat_route_ping_staff", True)
    await bot.store.set(GUILD, "staff_channel_id", LOG_CHANNEL)
    bot.guard = FakeGuard(allowed=CHANNEL)
    staff = bot.guild.get_channel(LOG_CHANNEL)

    with caplog.at_level("WARNING"):
        await cog.on_message(pinged(bot, member, "<@55> i need a mod"))

    assert [m for m in staff.messages if "asked for a mod" in str(m["content"])] == []
    assert caplog.records == []


class PanelMessage:
    def __init__(self, message_id, **kwargs):
        self.id = message_id
        self.kwargs = kwargs

    async def edit(self, **kwargs):
        self.kwargs |= kwargs

    @property
    def embeds(self):
        one = self.kwargs.get("embed")
        return [one] if one is not None else list(self.kwargs.get("embeds") or ())


class FakeResponse:
    def __init__(self):
        self.messages = []
        self.modals = []
        self.deferred = False

    def is_done(self):
        return self.deferred or bool(self.messages)

    async def defer(self, ephemeral=False):
        self.deferred = True

    async def send_message(self, content=None, ephemeral=False, **kwargs):
        self.messages.append({"content": content, "ephemeral": ephemeral, **kwargs})

    async def send_modal(self, modal):
        self.modals.append(modal)
        self.deferred = True


class FakeFollowup:
    def __init__(self, response):
        self.response = response

    async def send(self, content=None, ephemeral=False, **kwargs):
        self.response.messages.append({"content": content, "ephemeral": ephemeral, **kwargs})


class FakeInteraction:
    def __init__(self, bot, user):
        self.client = bot
        self.user = user
        self.guild = bot.guild
        self.guild_id = bot.guild.id
        self.channel_id = CHANNEL
        self.response = FakeResponse()
        self.followup = FakeFollowup(self.response)
        self.edits = []

    async def original_response(self):
        return PanelMessage(1)

    async def edit_original_response(self, **kwargs):
        self.edits.append(kwargs)
        return PanelMessage(9500, **kwargs)

    @property
    def rendered(self):
        if self.edits:
            return self.edits[-1]
        return self.response.messages[-1] if self.response.messages else {}

    @property
    def view(self):
        return self.rendered.get("view")

    @property
    def embed(self):
        return self.rendered.get("embed")

    @property
    def sent(self):
        spoken = [
            one["content"] for one in self.response.messages if one.get("content") is not None
        ]
        return spoken[-1] if spoken else None


async def _always_staff(interaction):
    return True


def staff_is(bot, yes=True):
    bot.store.is_staff = lambda who: yes


def labels(view):
    return [one.label for one in view.children if getattr(one, "label", None)]


def placeholders(view):
    return [
        one.placeholder for one in view.children if getattr(one, "placeholder", None) is not None
    ]


def button(view, label):
    return next(one for one in view.children if getattr(one, "label", None) == label)


def picker(view, placeholder):
    return next(one for one in view.children if getattr(one, "placeholder", None) == placeholder)


def only_select(view):
    return next(one for one in view.children if isinstance(one, discord.ui.Select))


def options(view, placeholder):
    return [one.value for one in picker(view, placeholder).options]


async def pick_one(interaction, placeholder, value):
    control = picker(interaction.view, placeholder)
    control._values = [value]
    await control.callback(interaction)


def fill(modal, **fields):
    for name, value in fields.items():
        getattr(modal, name)._value = value


async def open_the_panel(cog, bot, who, monkeypatch):
    monkeypatch.setattr(cog_module, "require_staff", _always_staff)
    staff_is(bot)
    interaction = FakeInteraction(bot, who)
    await Chat.chat_panel_command.callback(cog, interaction)
    return interaction


async def kinds_of(db):
    cur = await db.conn.execute("SELECT kind FROM action_log ORDER BY id")
    return [row["kind"] for row in await cur.fetchall()]


def answering(said="Pull up a chair, Nia.", tier="simple"):
    seen = []

    async def reply(bot, *, guild, member, channel, text):
        seen.append({"text": text, "channel": getattr(channel, "id", None)})
        return (said, tier)

    return reply, seen


async def test_an_intent_that_matches_never_reaches_a_model(cog, bot, member, monkeypatch):
    """The intents stay the front door: a greeting is answered for free."""
    reply, seen = answering()
    monkeypatch.setattr(chat_llm_module, "conversational_reply", reply)
    await bot.store.set(GUILD, "chat_llm_mode", "on")

    await cog.on_message(pinged(bot, member, "<@55> hi there"))

    assert seen == []


async def test_a_message_no_intent_knows_is_answered_by_the_model_and_logged(
    cog, bot, member, db, monkeypatch
):
    reply, seen = answering()
    monkeypatch.setattr(chat_llm_module, "conversational_reply", reply)
    await bot.store.set(GUILD, "chat_llm_mode", "on")
    message = pinged(bot, member, "<@55> what do you make of all this then")

    await cog.on_message(message)

    assert seen and seen[0]["channel"] == CHANNEL
    assert message.replies[0]["content"] == "Pull up a chair, Nia."
    assert message.replies[0]["kwargs"]["allowed_mentions"].everyone is False
    assert [row["kind"] for row in await rows(db, "chat.llm_reply")] == ["chat.llm_reply"]


async def test_a_model_that_says_nothing_leaves_the_written_line_to_answer(
    cog, bot, member, db, monkeypatch
):
    reply, _ = answering(said=None, tier=None)
    monkeypatch.setattr(chat_llm_module, "conversational_reply", reply)
    await bot.store.set(GUILD, "chat_llm_mode", "on")
    message = pinged(bot, member, "<@55> what do you make of all this then")

    await cog.on_message(message)

    assert "/help" in message.replies[0]["content"]
    assert await rows(db, "chat.llm_reply") == []


async def test_a_model_that_throws_leaves_the_written_line_to_answer(
    cog, bot, member, monkeypatch, caplog
):
    async def boom(bot_arg, *, guild, member, channel, text):
        raise RuntimeError("the sky fell in")

    monkeypatch.setattr(chat_llm_module, "conversational_reply", boom)
    await bot.store.set(GUILD, "chat_llm_mode", "on")
    message = pinged(bot, member, "<@55> what do you make of all this then")

    with caplog.at_level("WARNING"):
        await cog.on_message(message)

    assert "/help" in message.replies[0]["content"]
    assert "the sky fell in" in caplog.text


async def test_a_role_question_matching_no_role_at_all_goes_to_the_model(
    cog, bot, member, monkeypatch
):
    async def a_pick(bot_arg, home, member_arg, channel, text):
        return ("Beerus, easily — destruction beats training arcs.", "simple")

    monkeypatch.setattr(chat_module, "a_model_answer", a_pick)
    await bot.store.set(GUILD, "chat_llm_mode", "on")
    message = pinged(bot, member, "<@55> whos the strongest dbz character")

    await cog.on_message(message)

    assert "Beerus" in message.replies[0]["content"]


async def test_the_same_question_with_no_model_keeps_the_worded_refusal(cog, bot, member):
    message = pinged(bot, member, "<@55> whos the strongest dbz character")

    await cog.on_message(message)

    assert "no role here called" in message.replies[0]["content"]


# --- the command ---------------------------------------------------------------------------


async def test_the_command_answers_one_ephemeral_panel_and_nothing_else(cog, bot, member,
                                                                       monkeypatch):
    interaction = await open_the_panel(cog, bot, member, monkeypatch)

    assert len(interaction.response.messages) == 1
    said = interaction.response.messages[0]
    assert said["ephemeral"] is True
    assert said["embed"].title == chat_panel.PANEL_TITLE
    assert said["allowed_mentions"].to_dict() == discord.AllowedMentions.none().to_dict()
    assert said["view"].message is not None


async def test_the_command_refuses_a_dm_in_words(cog, bot, member, monkeypatch):
    monkeypatch.setattr(cog_module, "require_staff", _always_staff)
    interaction = FakeInteraction(bot, member)
    interaction.guild = None

    await Chat.chat_panel_command.callback(cog, interaction)

    assert "has to be run in the server itself" in interaction.sent


async def test_the_command_refuses_somebody_who_is_not_staff(cog, bot, member):
    staff_is(bot, False)
    interaction = FakeInteraction(bot, member)

    await Chat.chat_panel_command.callback(cog, interaction)

    assert "for staff only" in interaction.sent
    assert interaction.rendered.get("view") is None


async def test_the_command_refuses_while_the_database_is_down(cog, bot, member, db, monkeypatch):
    monkeypatch.setattr(cog_module, "require_staff", _always_staff)
    staff_is(bot)
    await db.close()
    interaction = FakeInteraction(bot, member)

    await Chat.chat_panel_command.callback(cog, interaction)

    assert interaction.sent == DB_UNAVAILABLE


# --- the root panel ------------------------------------------------------------------------


async def test_the_root_says_what_is_on_and_that_nothing_is_keyed_yet(cog, bot, member,
                                                                     monkeypatch):
    interaction = await open_the_panel(cog, bot, member, monkeypatch)

    said = interaction.embed.description
    assert "Conversation model: **off**" in said
    assert said.count("no key set") == 2
    assert "Answers today: **0** of 200" in said
    assert "Yours in the last hour: **0** of 20" in said
    assert "This month so far: **$0.00** of $20" in said
    assert "the daily read has not run yet" in said


async def test_the_root_counts_what_the_ledger_holds_and_says_when_it_is_closed(
    cog, bot, member, db, monkeypatch
):
    await bot.store.set(GUILD, "chat_monthly_cap_usd", 1)
    for turn in ("t1", "t2"):
        await record(
            db,
            guild_id=GUILD,
            user_id=USER,
            turn=turn,
            provider=ANTHROPIC,
            model=MODEL,
            tier="important",
            usage=Usage(input_tokens=600_000),
        )

    interaction = await open_the_panel(cog, bot, member, monkeypatch)

    said = interaction.embed.description
    assert "Answers today: **2**" in said
    assert "This month so far: **$1.20** of $1" in said
    assert "resting until the 1st" in said


async def test_the_root_says_a_tier_is_down_rather_than_calling_it_ready(cog, bot, member,
                                                                        monkeypatch):
    """poll_degraded honesty: a tier that failed says so instead of reading as fine."""
    monkeypatch.setattr(type(bot.settings), "simple_tier_configured", property(lambda s: True))
    tier_errors(bot)["simple"] = "unreachable"

    interaction = await open_the_panel(cog, bot, member, monkeypatch)

    assert "last call failed (unreachable)" in interaction.embed.description


async def test_the_root_reports_the_notes_and_a_daily_read_that_did_not_finish(
    cog, bot, member, monkeypatch
):
    bot.guild.text_channels = [open_channel("general", "Chat.")]
    bot.guild.roles = []
    await cog.ingest_once()
    cog.last_ingest_error = "RuntimeError: no"

    interaction = await open_the_panel(cog, bot, member, monkeypatch)

    said = interaction.embed.description
    assert "**2** written down" in said
    assert "The last daily read did not finish: RuntimeError: no" in said


async def test_the_spend_block_is_hidden_from_a_non_admin_and_the_panel_still_opens(
    cog, bot, monkeypatch
):
    """The key now hides the BLOCK, not the command — the same command carries Knowledge."""
    staffer = FakeMember(bot.guild, user_id=USER + 1, display_name="Uncle", admin=False)

    interaction = await open_the_panel(cog, bot, staffer, monkeypatch)

    said = interaction.embed.description
    assert "administrators" in said and "chat_status_admin_only" in said
    assert "$" not in said
    assert "Knowledge…" in labels(interaction.view)
    assert "/chat status" not in said


async def test_the_spend_block_appears_once_the_key_is_off(cog, bot, monkeypatch):
    await bot.store.set(GUILD, "chat_status_admin_only", False)
    staffer = FakeMember(bot.guild, user_id=USER + 1, display_name="Uncle", admin=False)

    interaction = await open_the_panel(cog, bot, staffer, monkeypatch)

    said = interaction.embed.description
    assert "This month so far" in said
    assert chat_panel.STATUS_ADMIN_ONLY not in said


async def test_the_root_points_at_memory_with_a_line_and_never_a_button(cog, bot, member,
                                                                       monkeypatch):
    interaction = await open_the_panel(cog, bot, member, monkeypatch)

    assert chat_panel.MEMORY_LINE in interaction.embed.description
    assert not [one for one in labels(interaction.view) if "memory" in one.lower()]


async def test_nothing_the_panel_says_names_a_retired_subcommand(cog, bot, member, db,
                                                                 monkeypatch):
    await knowledge.add_section(db, GUILD, "Rules", "Be kind.")
    await cog.seed_guilds()
    interaction = await open_the_panel(cog, bot, member, monkeypatch)
    written = [interaction.embed.description]
    for opener in (cog_module.build_personality, cog_module.build_knowledge):
        embed, _view = await opener(bot, bot.guild)
        written.append(embed.description)
    embed, _view = cog_module.build_settings(bot, bot.guild)
    written.append(embed.description)

    said = "\n".join(written)

    for gone in ("/chat status", "/chat knowledge", "/chat personality", "/chat settings"):
        assert gone not in said, gone


@pytest.mark.parametrize(
    ("chat_on", "llm_on", "wanted"),
    [
        ("on", "off", (chat_panel.ANSWER_OFF, chat_panel.LLM_ON)),
        ("off", "on", (chat_panel.ANSWER_ON, chat_panel.LLM_OFF)),
    ],
)
async def test_a_mode_button_says_what_it_will_do_and_never_both(
    cog, bot, member, monkeypatch, chat_on, llm_on, wanted
):
    await bot.store.set(GUILD, "chat_mode", chat_on)
    await bot.store.set(GUILD, "chat_llm_mode", llm_on)

    interaction = await open_the_panel(cog, bot, member, monkeypatch)

    shown = labels(interaction.view)
    assert wanted[0] in shown and wanted[1] in shown
    assert chat_panel.ANSWER_ON not in shown or chat_panel.ANSWER_OFF not in shown
    assert chat_panel.LLM_ON not in shown or chat_panel.LLM_OFF not in shown


async def test_one_click_turns_the_models_on_and_leaves_one_row(cog, bot, member, db,
                                                                monkeypatch):
    """Fork F-C3: no confirm — the monthly cap is the brake, and it is on the embed above."""
    interaction = await open_the_panel(cog, bot, member, monkeypatch)

    await button(interaction.view, chat_panel.LLM_ON).callback(interaction)

    assert bot.store.get(GUILD, "chat_llm_mode") == "on"
    assert await kinds_of(db) == ["chat.mode"]
    assert chat_panel.LLM_OFF in labels(interaction.view)


async def test_the_answering_toggle_goes_both_ways(cog, bot, member, db, monkeypatch):
    interaction = await open_the_panel(cog, bot, member, monkeypatch)

    await button(interaction.view, chat_panel.ANSWER_OFF).callback(interaction)
    assert bot.store.get(GUILD, "chat_mode") == "off"

    await button(interaction.view, chat_panel.ANSWER_ON).callback(interaction)

    assert bot.store.get(GUILD, "chat_mode") == "on"
    assert await kinds_of(db) == ["chat.mode", "chat.mode"]


async def test_logs_answers_a_new_message_and_the_panel_stays(cog, bot, member, db, monkeypatch):
    monkeypatch.setattr(actionlog, "require_staff", _always_staff)
    for kind in ("chat.route", "poll.created", "chat.insult"):
        await log_action(bot, bot.guild, kind, actor=member)
    interaction = await open_the_panel(cog, bot, member, monkeypatch)
    view = interaction.view

    await button(view, "Logs").callback(interaction)

    said = interaction.response.messages[-1]
    assert said["ephemeral"] is True
    assert said["embed"].title == "Chat log"
    assert "`chat.insult`" in said["embed"].description
    assert "poll.created" not in said["embed"].description
    assert said["embed"].footer.text.endswith("/chat.html")
    assert view.replaced is False


async def test_a_staffer_demoted_while_the_panel_is_open_moves_nothing(cog, bot, member, db,
                                                                      monkeypatch):
    interaction = await open_the_panel(cog, bot, member, monkeypatch)
    view = interaction.view
    staff_is(bot, False)

    await button(view, chat_panel.ANSWER_OFF).callback(interaction)
    await button(view, "Knowledge…").callback(interaction)

    assert "for staff only" in interaction.sent
    assert bot.store.get(GUILD, "chat_mode") == "on"
    assert await kinds_of(db) == []


async def test_a_click_after_the_database_went_away_says_so_rather_than_crashing(
    cog, bot, member, db, monkeypatch
):
    interaction = await open_the_panel(cog, bot, member, monkeypatch)
    view = interaction.view
    await db.close()

    await button(view, "Refresh").callback(interaction)

    assert interaction.sent == DB_UNAVAILABLE


async def test_a_re_render_retires_the_view_it_replaced(cog, bot, member, monkeypatch):
    interaction = await open_the_panel(cog, bot, member, monkeypatch)
    first = interaction.view

    await button(first, "Settings").callback(interaction)

    assert first.replaced is True
    assert interaction.view is not first
    assert interaction.view.where == cog_module.SETTINGS_VIEW


async def test_a_timeout_greys_every_control_and_says_what_to_run(cog, bot, member, monkeypatch):
    interaction = await open_the_panel(cog, bot, member, monkeypatch)
    view = interaction.view
    view.message = PanelMessage(3, embed=interaction.embed)
    view.last_interaction = interaction

    await view.on_timeout()

    assert all(one.disabled for one in view.children)
    assert interaction.edits[-1]["embeds"][0].footer.text == chat_panel.PANEL_TIMEOUT_FOOTER
    assert "run /chat again" in chat_panel.PANEL_TIMEOUT_FOOTER


async def test_open_on_the_site_is_there_only_when_an_origin_is_configured(
    cog, bot, member, monkeypatch, off_the_site
):
    linked = await open_the_panel(cog, bot, member, monkeypatch)

    assert button(linked.view, cog_module.SITE_BUTTON).url == f"{bot.settings.origin}/chat.html"

    alone_cog, alone_bot = off_the_site
    alone = await open_the_panel(alone_cog, alone_bot, FakeMember(alone_bot.guild), monkeypatch)

    assert cog_module.SITE_BUTTON not in labels(alone.view)


# --- Personality ---------------------------------------------------------------------------


async def test_the_voice_and_the_pool_are_both_shown(cog, bot):
    await cog.seed_guilds()

    embed, view = await cog_module.build_personality(bot, bot.guild)

    assert "The voice is **cookout**" in embed.description
    assert "**noir** (noir) — on" in embed.description
    assert placeholders(view) == [
        cog_module.VOICE_PLACEHOLDER,
        cog_module.MOOD_OFF_PLACEHOLDER,
    ]


async def test_the_card_says_nothing_is_using_the_voice_while_the_models_are_off(cog, bot):
    await cog.seed_guilds()

    embed, _view = await cog_module.build_personality(bot, bot.guild)

    assert cog_module.VOICE_OFF in embed.description


async def test_the_voice_is_set_through_the_registry_so_the_website_sees_it_too(
    cog, bot, member, db, monkeypatch
):
    await cog.seed_guilds()
    interaction = await open_the_panel(cog, bot, member, monkeypatch)
    await button(interaction.view, "Personality…").callback(interaction)

    await pick_one(interaction, cog_module.VOICE_PLACEHOLDER, "pool")

    assert "The voice is **pool**" in interaction.sent
    assert bot.store.get(GUILD, "chat_personality") == "pool"
    assert await kinds_of(db) == ["chat.personality_mode"]


async def test_a_mood_moves_between_the_two_selects_and_the_cached_pool_is_dropped(
    cog, bot, member, db, monkeypatch
):
    await cog.seed_guilds()
    bot._chat_tropes = ("stale",)
    interaction = await open_the_panel(cog, bot, member, monkeypatch)
    await button(interaction.view, "Personality…").callback(interaction)

    await pick_one(interaction, cog_module.MOOD_OFF_PLACEHOLDER, "flirty")

    assert "**flirty** is off" in interaction.sent
    assert not hasattr(bot, "_chat_tropes")
    assert "flirty" in options(interaction.view, cog_module.MOOD_ON_PLACEHOLDER)
    assert "flirty" not in options(interaction.view, cog_module.MOOD_OFF_PLACEHOLDER)

    await pick_one(interaction, cog_module.MOOD_ON_PLACEHOLDER, "flirty")

    assert "**flirty** is on" in interaction.sent
    assert await kinds_of(db) == ["chat.trope_disabled", "chat.trope_enabled"]


async def test_the_mood_that_is_the_voice_is_not_on_the_select_at_all(cog, bot):
    """Fork F-C4: the panel never offers a move its own function would refuse."""
    await cog.seed_guilds()
    await bot.store.set(GUILD, "chat_personality", "noir")

    _embed, view = await cog_module.build_personality(bot, bot.guild)

    assert "noir" not in options(view, cog_module.MOOD_OFF_PLACEHOLDER)


async def test_the_card_says_why_a_mood_is_missing_from_the_off_select(cog, bot):
    await cog.seed_guilds()
    await bot.store.set(GUILD, "chat_personality", "noir")

    embed, _view = await cog_module.build_personality(bot, bot.guild)

    assert chat_panel.POOL_GUARDS in embed.description


async def test_the_off_select_is_not_rendered_when_nothing_may_be_turned_off(cog, bot, db):
    await cog.seed_guilds()
    await bot.store.set(GUILD, "chat_personality", "pool")
    pooled = await list_tropes(db)
    for row in pooled[:-1]:
        await personas.set_enabled(db, str(row["name"]), False)

    _embed, view = await cog_module.build_personality(bot, bot.guild)

    assert cog_module.MOOD_OFF_PLACEHOLDER not in placeholders(view)
    assert cog_module.MOOD_ON_PLACEHOLDER in placeholders(view)


# --- Knowledge -----------------------------------------------------------------------------


async def test_an_empty_list_offers_only_the_way_to_start_one(cog, bot, member, monkeypatch):
    interaction = await open_the_panel(cog, bot, member, monkeypatch)

    await button(interaction.view, "Knowledge…").callback(interaction)

    assert "Nothing has been written down yet" in interaction.embed.description
    assert placeholders(interaction.view) == []
    assert "Find…" not in labels(interaction.view)
    assert "Write one down…" in labels(interaction.view)


async def test_a_staff_note_is_saved_logged_and_then_listed(cog, bot, member, db, monkeypatch):
    interaction = await open_the_panel(cog, bot, member, monkeypatch)
    await button(interaction.view, "Knowledge…").callback(interaction)

    await button(interaction.view, "Write one down…").callback(interaction)
    modal = interaction.response.modals[-1]
    fill(modal, note_title="Cookout hours", body="Fridays.", tag="events")
    await modal.on_submit(interaction)

    assert "Saved as note" in interaction.sent
    assert await kinds_of(db) == ["chat.knowledge_added"]
    assert "Cookout hours" in interaction.embed.description
    assert "events" in interaction.embed.description
    assert cog_module.NOTE_PLACEHOLDER in placeholders(interaction.view)


async def test_a_note_that_is_refused_says_why_and_saves_nothing(cog, bot, member, db,
                                                                 monkeypatch):
    interaction = await open_the_panel(cog, bot, member, monkeypatch)
    await button(interaction.view, "Knowledge…").callback(interaction)
    await button(interaction.view, "Write one down…").callback(interaction)

    modal = interaction.response.modals[-1]
    fill(modal, note_title="   ", body="Fridays.", tag="")
    await modal.on_submit(interaction)

    assert "needs a title" in interaction.sent
    assert await knowledge.list_sections(db, GUILD) == []
    assert await kinds_of(db) == []


async def test_find_filters_the_list_and_leaves_no_row_behind_it(cog, bot, member, db,
                                                                 monkeypatch):
    await knowledge.add_section(db, GUILD, "Cookout hours", "Fridays.")
    await knowledge.add_section(db, GUILD, "Rules", "Be kind.")
    interaction = await open_the_panel(cog, bot, member, monkeypatch)
    await button(interaction.view, "Knowledge…").callback(interaction)

    await button(interaction.view, "Find…").callback(interaction)
    modal = interaction.response.modals[-1]
    modal.note._value = "cookout"
    await modal.on_submit(interaction)

    assert "Cookout hours" in interaction.embed.description
    assert "Rules" not in interaction.embed.description
    assert await kinds_of(db) == []

    await button(interaction.view, "Find…").callback(interaction)
    miss = interaction.response.modals[-1]
    miss.note._value = "parliament"
    await miss.on_submit(interaction)

    assert "Nothing written down matches" in interaction.embed.description


async def test_picking_a_note_shows_it_whole_with_both_moves(cog, bot, member, db, monkeypatch):
    made = await knowledge.add_section(db, GUILD, "Cookout hours", "Fridays.", tag="events")
    interaction = await open_the_panel(cog, bot, member, monkeypatch)
    await button(interaction.view, "Knowledge…").callback(interaction)

    await pick_one(interaction, cog_module.NOTE_PLACEHOLDER, str(made))

    assert "Fridays." in interaction.embed.description
    assert labels(interaction.view) == ["Remove", "Edit…", "Back"]


async def test_a_server_written_note_shows_neither_move_and_says_why(cog, bot, member, db,
                                                                    monkeypatch):
    """One writer per row: tomorrow's ingest would put an edit straight back."""
    made = await knowledge.add_section(
        db, GUILD, "#general", "Chat here.", tag="channel", source=knowledge.SERVER
    )
    interaction = await open_the_panel(cog, bot, member, monkeypatch)
    await button(interaction.view, "Knowledge…").callback(interaction)

    await pick_one(interaction, cog_module.NOTE_PLACEHOLDER, str(made))

    assert labels(interaction.view) == ["Back"]
    assert "overwritten by tomorrow" in interaction.embed.description


async def test_a_note_is_removed_only_after_a_yes(cog, bot, member, db, monkeypatch):
    made = await knowledge.add_section(db, GUILD, "Cookout hours", "Fridays.")
    interaction = await open_the_panel(cog, bot, member, monkeypatch)
    await button(interaction.view, "Knowledge…").callback(interaction)
    await pick_one(interaction, cog_module.NOTE_PLACEHOLDER, str(made))

    await button(interaction.view, "Remove").callback(interaction)
    assert chat_panel.KEEP_IT in labels(interaction.view)
    assert await knowledge.get_section(db, made) is not None

    await button(interaction.view, chat_panel.REMOVE_YES).callback(interaction)

    assert "is gone" in interaction.sent
    assert await kinds_of(db) == ["chat.knowledge_removed"]
    assert await knowledge.get_section(db, made) is None


async def test_keeping_it_puts_the_card_back_untouched(cog, bot, member, db, monkeypatch):
    made = await knowledge.add_section(db, GUILD, "Cookout hours", "Fridays.")
    interaction = await open_the_panel(cog, bot, member, monkeypatch)
    await button(interaction.view, "Knowledge…").callback(interaction)
    await pick_one(interaction, cog_module.NOTE_PLACEHOLDER, str(made))
    await button(interaction.view, "Remove").callback(interaction)

    await button(interaction.view, chat_panel.KEEP_IT).callback(interaction)

    assert labels(interaction.view) == ["Remove", "Edit…", "Back"]
    assert await knowledge.get_section(db, made) is not None


async def test_a_note_is_edited_in_place_keeping_its_number(cog, bot, member, db, monkeypatch):
    """Fork F-C2: one prefilled modal, the same id, one `chat.knowledge_edited` row."""
    made = await knowledge.add_section(db, GUILD, "Cookout hours", "Fridays.", tag="events")
    interaction = await open_the_panel(cog, bot, member, monkeypatch)
    await button(interaction.view, "Knowledge…").callback(interaction)
    await pick_one(interaction, cog_module.NOTE_PLACEHOLDER, str(made))

    await button(interaction.view, "Edit…").callback(interaction)
    modal = interaction.response.modals[-1]
    assert str(modal.note_title.default) == "Cookout hours"
    assert str(modal.body.default) == "Fridays."
    assert str(modal.tag.default) == "events"
    fill(modal, note_title="Cookout hours", body="Saturdays.", tag="events")
    await modal.on_submit(interaction)

    assert await kinds_of(db) == ["chat.knowledge_edited"]
    row = await knowledge.get_section(db, made)
    assert str(row["body"]) == "Saturdays." and int(row["id"]) == made
    assert "Saturdays." in interaction.embed.description


async def test_a_note_from_another_server_is_not_reachable_by_its_number(cog, bot, member, db):
    elsewhere = await knowledge.add_section(db, 999, "Elsewhere", "Not yours.")

    outcome = await chat_panel.remove_note(bot, bot.guild, member, elsewhere)

    assert not outcome.ok and "no note" in outcome.message
    assert await knowledge.get_section(db, elsewhere) is not None


async def test_past_twenty_five_notes_the_picker_says_how_many_and_where_the_rest_are(
    cog, bot, db
):
    for one in range(26):
        await knowledge.add_section(db, GUILD, f"Note {one}", "Words.")

    _embed, view = await cog_module.build_knowledge(bot, bot.guild)

    control = only_select(view)
    assert len(control.options) == 25
    assert "25 of 26" in control.placeholder
    assert "Knowledge section" in control.placeholder


# --- Settings ------------------------------------------------------------------------------


async def test_the_settings_card_lists_every_chat_key_and_names_memorys_home(cog, bot, member,
                                                                            monkeypatch):
    await bot.store.set(GUILD, "chat_log_level", "off")
    interaction = await open_the_panel(cog, bot, member, monkeypatch)

    await button(interaction.view, "Settings").callback(interaction)

    said = interaction.embed.description
    assert "`chat_mode` — **on**" in said
    assert "`chat_log_level` — **off**" in said
    assert "`chat_panel_minutes` — **10**" in said
    assert "`chat_memory_mode`" in said
    assert "/memory" in said
    assert "/settings set-value" in said


async def test_the_limits_modal_arrives_prefilled_and_saves_all_five_at_once(
    cog, bot, member, db, monkeypatch
):
    interaction = await open_the_panel(cog, bot, member, monkeypatch)
    await button(interaction.view, "Settings").callback(interaction)

    await button(interaction.view, "Limits…").callback(interaction)
    modal = interaction.response.modals[-1]
    assert str(modal.cap.default) == "20" and str(modal.stays.default) == "10"
    fill(modal, cooldown="9", hourly="11", daily="150", cap="25", stays="12")
    await modal.on_submit(interaction)

    assert bot.store.get(GUILD, "chat_cooldown_seconds") == 9
    assert bot.store.get(GUILD, "chat_monthly_cap_usd") == 25
    assert bot.store.get(GUILD, "chat_panel_minutes") == 12
    assert await kinds_of(db) == ["chat.settings"]
    assert "`chat_daily_turns` — **150**" in interaction.embed.description


async def test_one_bad_number_refuses_the_whole_modal_and_saves_nothing(
    cog, bot, member, db, monkeypatch
):
    interaction = await open_the_panel(cog, bot, member, monkeypatch)
    await button(interaction.view, "Settings").callback(interaction)
    await button(interaction.view, "Limits…").callback(interaction)

    modal = interaction.response.modals[-1]
    fill(modal, cooldown="9", hourly="11", daily="not a number", cap="25", stays="12")
    await modal.on_submit(interaction)

    assert "chat_daily_turns" in interaction.sent
    assert bot.store.get(GUILD, "chat_cooldown_seconds") != 9
    assert await kinds_of(db) == []


async def test_a_number_outside_its_range_names_the_field_and_the_range(
    cog, bot, member, db, monkeypatch
):
    interaction = await open_the_panel(cog, bot, member, monkeypatch)
    await button(interaction.view, "Settings").callback(interaction)
    await button(interaction.view, "Limits…").callback(interaction)

    modal = interaction.response.modals[-1]
    fill(modal, cooldown="9", hourly="11", daily="150", cap="999999", stays="12")
    await modal.on_submit(interaction)

    assert "chat_monthly_cap_usd" in interaction.sent
    assert "cannot be more than" in interaction.sent
    assert bot.store.get(GUILD, "chat_monthly_cap_usd") == 20
    assert await kinds_of(db) == []



async def test_the_daily_ingest_writes_the_server_rows_and_leaves_staff_rows_alone(
    cog, bot, member, db, monkeypatch
):
    await knowledge.add_section(db, GUILD, "Rules", "Be kind.")
    bot.guild.text_channels = [open_channel("general", "Chat about anything.")]
    bot.guild.roles = [SimpleNamespace(name="Member")]

    written = await cog.ingest_once()

    assert written >= 2
    cur = await db.conn.execute("SELECT title, source FROM knowledge_sections ORDER BY id")
    found = {(row["title"], row["source"]) for row in await cur.fetchall()}
    assert ("Rules", "staff") in found
    assert ("#general", "server") in found
    assert ("Channels in this server", "server") in found
    assert await rows(db, "chat.knowledge_ingested")


async def test_the_daily_ingest_leaves_out_private_archive_and_modmail_channels(cog, bot, db):
    """The 2026-09-01 leak: a dead archive channel recommended, five tickets with member ids."""
    archive = SimpleNamespace(id=50, name="Archive")
    modmail = SimpleNamespace(id=11, name="ModMail")
    await bot.store.set(GUILD, "modmail_category_id", 11)
    bot.guild.text_channels = [
        open_channel("general", "Chat about anything."),
        shut_channel("staff-room", "Staff only."),
        open_channel("black-support-hub", "Ask for help.", category=archive),
        open_channel("ticket-0001", "ModMail Channel 900 111", category=modmail),
    ]
    bot.guild.roles = []

    await cog.ingest_once()

    cur = await db.conn.execute("SELECT title, body FROM knowledge_sections ORDER BY id")
    found = list(await cur.fetchall())
    titles = [row["title"] for row in found]
    assert titles == ["Channels in this server", "#general"]
    listing = next(row["body"] for row in found if row["title"] == "Channels in this server")
    assert listing == "#general"
    assert not any("ModMail Channel" in row["body"] for row in found)


async def test_a_category_staff_asked_the_ingest_to_ignore_stays_out(cog, bot, db):
    committee = SimpleNamespace(id=99, name="Committee")
    await bot.store.set(GUILD, "chat_ignore_categories", [99])
    bot.guild.text_channels = [
        open_channel("general", "Chat."),
        open_channel("planning", "Committee talk.", category=committee),
    ]
    bot.guild.roles = []

    await cog.ingest_once()

    cur = await db.conn.execute("SELECT title FROM knowledge_sections ORDER BY id")
    assert [row["title"] for row in await cur.fetchall()] == [
        "Channels in this server",
        "#general",
    ]


async def test_the_daily_ingest_writes_out_who_holds_a_small_role(cog, bot, db):
    """Grounding for the phrasings `who_has` misses — and the holder rows come LAST."""
    bot.guild.text_channels = []
    bot.guild.roles = [
        SimpleNamespace(name="@everyone", members=[]),
        SimpleNamespace(
            name="Leads",
            members=[
                SimpleNamespace(display_name="Ada", name="Ada", bot=False),
                SimpleNamespace(display_name="Kai", name="Kai", bot=False),
            ],
        ),
    ]

    await cog.ingest_once()

    cur = await db.conn.execute(
        "SELECT title, body, source, tag FROM knowledge_sections ORDER BY id"
    )
    found = list(await cur.fetchall())
    assert found[-1]["title"] == "Who has the Leads role"
    assert found[-1]["body"] == "Leads — 2 members: Ada, Kai."
    assert found[-1]["source"] == "server" and found[-1]["tag"] == "role"
    assert "Roles in this server" in [row["title"] for row in found]


async def test_a_hand_written_note_survives_the_role_holder_ingest(
    cog, bot, member, db, monkeypatch
):
    await knowledge.add_section(db, GUILD, "Rules", "Be kind.")
    bot.guild.text_channels = []
    bot.guild.roles = [
        SimpleNamespace(
            name="Leads", members=[SimpleNamespace(display_name="Ada", name="Ada", bot=False)]
        )
    ]

    await cog.ingest_once()
    await cog.ingest_once()

    cur = await db.conn.execute("SELECT title, source FROM knowledge_sections ORDER BY id")
    found = [(row["title"], row["source"]) for row in await cur.fetchall()]
    assert ("Rules", "staff") in found
    assert found.count(("Who has the Leads role", "server")) == 1


async def test_the_ingest_runs_again_without_doubling_anything(cog, bot, db):
    bot.guild.text_channels = [open_channel("general", "Chat.")]
    bot.guild.roles = []

    await cog.ingest_once()
    await cog.ingest_once()

    cur = await db.conn.execute(
        "SELECT COUNT(*) AS n FROM knowledge_sections WHERE title = '#general'"
    )
    assert (await cur.fetchone())["n"] == 1


async def test_an_unavailable_server_is_skipped_rather_than_emptied(cog, bot, db):
    bot.guild.text_channels = [open_channel("general", "Chat.")]
    bot.guild.roles = []
    await cog.ingest_once()
    bot.guild.unavailable = True

    await cog.ingest_once()

    cur = await db.conn.execute("SELECT COUNT(*) AS n FROM knowledge_sections")
    assert (await cur.fetchone())["n"] > 0


async def test_the_expiring_turns_are_distilled_before_the_sweep_deletes_them(
    cog, bot, db, monkeypatch
):
    """The hook is on the sweep and never on the reply path, so the order is the whole point."""
    from datetime import UTC, datetime, timedelta

    from black_bloc.chat_llm import remember

    order = []
    at = datetime.now(UTC) - timedelta(hours=3)
    for number in range(2):
        await remember(
            db,
            guild_id=GUILD,
            channel_id=CHANNEL,
            user_id=900,
            speaker="member",
            content=f"turn {number}",
            at=at,
        )

    async def distil(_bot, **kwargs):
        cur = await db.conn.execute("SELECT COUNT(*) AS n FROM chat_window")
        order.append(("distil", (await cur.fetchone())["n"]))
        return {"looked": 1, "distilled": 1, "failed": 0, "expired": 0}

    async def sweep(_db, **kwargs):
        cur = await _db.conn.execute("SELECT COUNT(*) AS n FROM chat_window")
        order.append(("sweep", (await cur.fetchone())["n"]))
        return 0

    monkeypatch.setattr(cog_module, "distil_run", distil)
    monkeypatch.setattr(cog_module, "sweep_window", sweep)
    bot.guild.text_channels = []
    bot.guild.roles = []

    await cog.ingest_once()

    assert [name for name, _ in order] == ["distil", "sweep"]
    assert order[0][1] == 2
    assert cog.last_distil == {"looked": 1, "distilled": 1, "failed": 0, "expired": 0}


async def test_a_distillation_that_blows_up_never_stops_the_sweep(cog, bot, db, monkeypatch):
    swept = []

    async def boom(_bot, **kwargs):
        raise RuntimeError("no")

    async def sweep(_db, **kwargs):
        swept.append(True)
        return 0

    monkeypatch.setattr(cog_module, "distil_run", boom)
    monkeypatch.setattr(cog_module, "sweep_window", sweep)
    bot.guild.text_channels = []
    bot.guild.roles = []

    await cog.ingest_once()

    assert swept == [True]


async def test_the_ingest_loop_records_its_health_and_restarts_when_it_stops(cog, monkeypatch):
    async def boom():
        raise RuntimeError("no")

    monkeypatch.setattr(cog, "ingest_once", boom)
    await cog._ingest()
    assert cog.loop_health("_ingest") == (None, "RuntimeError: no")

    restarted = []
    monkeypatch.setattr(cog._ingest, "restart", lambda: restarted.append(True))
    await cog._ingest_stopped(RuntimeError("stopped"))
    assert restarted == [True]
    assert cog.loop_health("_ingest")[1] == "RuntimeError: stopped"


def test_a_thread_is_told_apart_from_an_ordinary_channel():
    assert in_a_thread(FakeChannel(1, kind="public_thread")) is True
    assert in_a_thread(FakeChannel(1, kind="private_thread")) is True
    assert in_a_thread(FakeChannel(1)) is False
    assert in_a_thread(None) is False
