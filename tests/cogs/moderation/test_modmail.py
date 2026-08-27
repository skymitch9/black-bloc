import asyncio
from datetime import UTC, datetime

import discord
import pytest

from black_bloc.cogs.moderation.modmail import (
    Modmail,
    add_message,
    blocked_row,
    open_ticket_for,
    open_tickets,
    resolve_ticket,
    ticket_for_channel,
    ticket_messages,
)
from black_bloc.config import load_settings
from black_bloc.modmail import IN, NOTE, OUT, parse_topic
from black_bloc.settings_store import CHANNEL_MODE, THREAD_MODE, SettingsStore
from black_bloc.storage.db import Database

GUILD = 7
TEST_CHANNEL = 111
LOG_CHANNEL = 222
CATEGORY = 50
STAFF_ROLE = 555
USER = 900
LEAD = 1


class FakeRole:
    def __init__(self, role_id, name=None):
        self.id = role_id
        self.name = name or f"role-{role_id}"
        self.mention = f"<@&{role_id}>"


class FakeCategory:
    def __init__(self, category_id=CATEGORY):
        self.id = category_id
        self.name = f"category-{category_id}"
        self.channels = []


class _Response:
    def __init__(self, status):
        self.status = status
        self.reason = "refused"


def refused():
    return discord.HTTPException(_Response(403), "no")


class FakePerms:
    def __init__(self, manage_guild=False, view_channel=False):
        self.manage_guild = manage_guild
        self.view_channel = view_channel


class FakeMessage:
    def __init__(self, message_id, content, channel, author=None, **kwargs):
        self.id = message_id
        self.content = content
        self.channel = channel
        self.author = author
        self.kwargs = kwargs
        self.reactions = []

    async def add_reaction(self, emoji):
        self.reactions.append(emoji)


class FakeThread:
    def __init__(self, thread_id, parent, name, **kwargs):
        self.id = thread_id
        self.parent = parent
        self.parent_id = parent.id
        self.guild = parent.guild
        self.name = name
        self.kwargs = kwargs
        self.messages = []
        self.archived = False
        self.locked = False
        self.deleted = False

    async def send(self, content=None, **kwargs):
        message = FakeMessage(len(self.messages) + 1, content or "", self, **kwargs)
        self.messages.append(message)
        return message

    async def edit(self, **kwargs):
        self.archived = kwargs.get("archived", self.archived)
        self.locked = kwargs.get("locked", self.locked)

    async def delete(self, reason=None):
        self.deleted = True


class FakeText:
    def __init__(self, channel_id, guild=None, category=None, name="channel", topic=None):
        self.id = channel_id
        self.guild = guild
        self.name = name
        self.topic = topic
        self.mention = f"<#{channel_id}>"
        self.category = category
        self.category_id = category.id if category else None
        self.visible_to = set()
        self.messages = []
        self.threads = []
        self.deleted = False
        self.send_raises = None
        self.thread_raises = None

    def permissions_for(self, role):
        return FakePerms(view_channel=role.id in self.visible_to)

    async def send(self, content=None, **kwargs):
        if self.send_raises is not None:
            raise self.send_raises
        message = FakeMessage(len(self.messages) + 1, content or "", self, **kwargs)
        self.messages.append(message)
        return message

    async def create_thread(self, *, name, **kwargs):
        if self.thread_raises is not None:
            raise self.thread_raises
        self.guild._next_id += 1
        thread = FakeThread(self.guild._next_id, self, name, **kwargs)
        self.threads.append(thread)
        self.guild.threads[thread.id] = thread
        return thread

    async def delete(self, reason=None):
        self.deleted = True
        if self.guild is not None:
            self.guild.channels.pop(self.id, None)


class FakeGuild:
    def __init__(self):
        self.id = GUILD
        self.name = "Black in a Flash!"
        self.channels = {}
        self.threads = {}
        self.members = {}
        self.default_role = FakeRole(GUILD)
        self.roles = []
        self.created = []
        self.create_raises = None
        self.me = FakeRole(99, "Black Bloc")
        self._next_id = 2000

    def get_channel(self, channel_id):
        return self.channels.get(channel_id)

    def get_thread(self, thread_id):
        return self.threads.get(thread_id)

    def get_member(self, user_id):
        return self.members.get(user_id)

    def add(self, channel):
        channel.guild = self
        self.channels[channel.id] = channel
        return channel

    async def create_text_channel(
        self, name, *, category=None, topic=None, overwrites=None, reason=None
    ):
        if self.create_raises is not None:
            raise self.create_raises
        self._next_id += 1
        channel = FakeText(self._next_id, self, category, name=name, topic=topic)
        channel.given_overwrites = overwrites
        self.add(channel)
        self.created.append(channel)
        return channel


class FakeUser:
    def __init__(
        self, guild=None, user_id=USER, display_name="Alice", roles=(), manage_guild=False
    ):
        self.id = user_id
        self.guild = guild
        self.name = display_name.lower()
        self.display_name = display_name
        self.bot = False
        self.mention = f"<@{user_id}>"
        self.roles = [FakeRole(r) for r in roles]
        self.guild_permissions = FakePerms(manage_guild=manage_guild)
        self.created_at = datetime(2020, 1, 1, tzinfo=UTC)
        self.joined_at = datetime(2021, 1, 1, tzinfo=UTC)
        self.colour = discord.Colour(0xABCDEF)
        self.dms = []
        self.dm_raises = None
        if guild is not None:
            guild.members[user_id] = self

    async def send(self, content=None, **kwargs):
        if self.dm_raises is not None:
            raise self.dm_raises
        self.dms.append({"content": content, **kwargs})


class FakeDM:
    def __init__(self, channel_id=8000):
        self.id = channel_id


class FakeGuard:
    def __init__(self, test_channel_id=TEST_CHANNEL, dm_ids=(8000,)):
        self.test_channel_id = test_channel_id
        self.dm_ids = set(dm_ids)

    def allows_channel(self, channel_id):
        return channel_id == self.test_channel_id or channel_id in self.dm_ids

    def refusal_message(self):
        return "test mode"


class FakeBot:
    def __init__(self, db, store, settings, guild):
        self.db = db
        self.store = store
        self.settings = settings
        self.guard = None
        self.guilds = [guild]
        self.guild = guild
        self.users = {}

    def get_channel(self, channel_id):
        return self.guild.channels.get(channel_id) or self.guild.threads.get(channel_id)

    def get_guild(self, guild_id):
        return self.guild if guild_id == self.guild.id else None

    def get_user(self, user_id):
        return self.users.get(user_id)

    async def wait_until_ready(self):
        return None


class FakeResponse:
    def __init__(self):
        self.messages = []
        self.done = False

    def is_done(self):
        return self.done

    async def send_message(self, content=None, ephemeral=False, **kwargs):
        self.done = True
        self.messages.append({"content": content, "ephemeral": ephemeral, **kwargs})

    async def defer(self, ephemeral=False, **kwargs):
        self.done = True
        self.messages.append({"content": None, "deferred": True})


class FakeFollowup:
    def __init__(self, response):
        self.response = response

    async def send(self, content=None, ephemeral=False, **kwargs):
        self.response.messages.append({"content": content, "ephemeral": ephemeral, **kwargs})


class FakeInteraction:
    def __init__(self, bot, user, channel=None):
        self.client = bot
        self.user = user
        self.guild = bot.guild
        self.guild_id = bot.guild.id
        self.channel = channel
        self.channel_id = channel.id if channel is not None else TEST_CHANNEL
        self.response = FakeResponse()
        self.followup = FakeFollowup(self.response)

    @property
    def sent(self):
        said = [m["content"] for m in self.response.messages if m["content"] is not None]
        return said[-1] if said else None


async def action_kinds(db):
    cur = await db.conn.execute("SELECT kind FROM action_log ORDER BY id")
    return [row["kind"] for row in await cur.fetchall()]


@pytest.fixture
async def db(tmp_path):
    database = Database(tmp_path / "m.sqlite3")
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
    await store.set(GUILD, "modmail_enabled", True)
    guild = FakeGuild()
    guild.roles = [FakeRole(STAFF_ROLE, "Lead")]
    category = FakeCategory()
    guild.channels[CATEGORY] = category
    guild.add(FakeText(LOG_CHANNEL, name="log"))
    test_channel = guild.add(FakeText(TEST_CHANNEL, category=category, name="test"))
    test_channel.visible_to = {STAFF_ROLE}
    return FakeBot(db, store, settings, guild)


@pytest.fixture
def cog(bot):
    return Modmail(bot)


@pytest.fixture
def member(bot):
    user = FakeUser(bot.guild)
    bot.users[user.id] = user
    return user


@pytest.fixture
def lead(bot):
    user = FakeUser(bot.guild, user_id=LEAD, display_name="Meg", manage_guild=True)
    bot.users[user.id] = user
    return user


def dm_from(member, content="my ban was unfair", attachments=(), channel=None):
    message = FakeMessage(1, content, channel or FakeDM(), author=member)
    message.guild = None
    message.type = discord.MessageType.default
    message.webhook_id = None
    message.attachments = list(attachments)
    return message


def guild_message(channel, author, content):
    message = FakeMessage(2, content, channel, author=author)
    message.guild = channel.guild
    message.type = discord.MessageType.default
    message.webhook_id = None
    message.attachments = []
    return message


async def test_a_dm_opens_one_ticket_in_the_test_category_and_relays_it(cog, bot, member, db):
    bot.guard = FakeGuard()

    await cog.on_message(dm_from(member))

    ticket = await open_ticket_for(db, GUILD, member.id)
    assert ticket is not None and ticket["mode"] == CHANNEL_MODE
    made = bot.guild.created[0]
    assert made.category is bot.guild.channels[CATEGORY]
    assert made.name == "alice"
    assert parse_topic(made.topic) == (member.id, ticket["id"])
    rows = await ticket_messages(db, ticket["id"])
    assert [row["direction"] for row in rows] == [IN]
    assert "modmail.opened" in await action_kinds(db)


async def test_the_relay_lands_in_the_test_channel_while_the_guard_is_on(cog, bot, member):
    bot.guard = FakeGuard()

    await cog.on_message(dm_from(member))

    made = bot.guild.created[0]
    assert made.messages == []
    embeds = [m.kwargs.get("embed") for m in bot.guild.channels[TEST_CHANNEL].messages]
    assert [e.title for e in embeds if e] == ["Ticket #1", "From the member"]


async def test_two_dms_in_a_burst_make_exactly_one_ticket(cog, bot, member, db):
    bot.guard = FakeGuard()

    await asyncio.gather(
        cog.on_message(dm_from(member, "first")), cog.on_message(dm_from(member, "second"))
    )

    cur = await db.conn.execute("SELECT COUNT(*) AS n FROM modmail_tickets")
    assert (await cur.fetchone())["n"] == 1
    assert len(bot.guild.created) == 1
    ticket = await open_ticket_for(db, GUILD, member.id)
    said = {row["content"] for row in await ticket_messages(db, ticket["id"])}
    assert said == {"first", "second"}


async def test_a_second_dm_reuses_the_open_ticket_and_says_nothing_new(cog, bot, member, db):
    bot.guard = FakeGuard()
    await cog.on_message(dm_from(member, "first"))
    opening = len(member.dms)

    await cog.on_message(dm_from(member, "second"))

    assert len(bot.guild.created) == 1
    assert len(member.dms) == opening
    ticket = await open_ticket_for(db, GUILD, member.id)
    assert len(await ticket_messages(db, ticket["id"])) == 2


async def test_modmail_is_off_by_default_and_points_at_the_incumbent(cog, bot, member, db):
    bot.guard = FakeGuard()
    await bot.store.set(GUILD, "modmail_enabled", False)

    await cog.on_message(dm_from(member))

    assert await open_ticket_for(db, GUILD, member.id) is None
    assert "ModMail" in member.dms[-1]["content"]


async def test_a_blocked_member_is_told_once_and_the_log_records_it(cog, bot, member, db):
    bot.guard = FakeGuard()
    await db.conn.execute(
        "INSERT INTO modmail_blocks(user_id, by, reason, at) VALUES (?, ?, ?, ?)",
        (member.id, LEAD, "abuse", "2026-08-26T00:00:00+00:00"),
    )
    await db.conn.commit()

    await cog.on_message(dm_from(member))

    assert await open_ticket_for(db, GUILD, member.id) is None
    assert "stopped Black Bloc" in member.dms[-1]["content"]
    assert await action_kinds(db) == ["modmail.blocked_dm"]
    assert (await blocked_row(db, member.id))["reason"] == "abuse"


async def test_a_dm_from_somebody_in_no_guild_is_refused_with_a_sentence(cog, bot, db):
    bot.guard = FakeGuard()
    stranger = FakeUser(None, user_id=4242, display_name="Stranger")

    await cog.on_message(dm_from(stranger))

    cur = await db.conn.execute("SELECT COUNT(*) AS n FROM modmail_tickets")
    assert (await cur.fetchone())["n"] == 0
    assert "servers it looks after" in stranger.dms[-1]["content"]


async def test_a_system_message_is_never_treated_as_modmail(cog, bot, member, db):
    bot.guard = FakeGuard()
    message = dm_from(member)
    message.type = discord.MessageType.pins_add

    await cog.on_message(message)

    cur = await db.conn.execute("SELECT COUNT(*) AS n FROM modmail_tickets")
    assert (await cur.fetchone())["n"] == 0


async def test_attachments_are_relayed_as_links_and_never_re_uploaded(cog, bot, member, db):
    bot.guard = FakeGuard()

    class Attachment:
        url = "https://cdn/proof.png"

    await cog.on_message(dm_from(member, "see this", attachments=[Attachment()]))

    ticket = await open_ticket_for(db, GUILD, member.id)
    row = (await ticket_messages(db, ticket["id"]))[0]
    assert row["attachments"] == '["https://cdn/proof.png"]'
    posted = bot.guild.channels[TEST_CHANNEL].messages[-1]
    assert posted.kwargs.get("file") is None
    assert posted.kwargs["embed"].fields[0].value == "https://cdn/proof.png"


async def test_thread_mode_makes_a_private_thread_that_pings_the_staff_roles_once(
    cog, bot, member, db
):
    bot.guard = FakeGuard()
    await bot.store.set(GUILD, "modmail_mode", THREAD_MODE)

    await cog.on_message(dm_from(member))

    thread = bot.guild.channels[TEST_CHANNEL].threads[0]
    assert thread.kwargs["type"] is discord.ChannelType.private_thread
    assert thread.kwargs["invitable"] is False
    assert thread.kwargs["auto_archive_duration"] == 1440
    ticket = await open_ticket_for(db, GUILD, member.id)
    assert ticket["thread_id"] == thread.id and ticket["channel_id"] == TEST_CHANNEL
    invite = bot.guild.channels[TEST_CHANNEL].messages[0]
    assert f"<@&{STAFF_ROLE}>" in invite.content
    assert [role.id for role in invite.kwargs["allowed_mentions"].roles] == [STAFF_ROLE]
    assert invite.kwargs["allowed_mentions"].everyone is False


async def test_a_channel_discord_refuses_closes_the_row_and_tells_the_member(cog, bot, member, db):
    bot.guard = FakeGuard()
    bot.guild.create_raises = refused()

    await cog.on_message(dm_from(member))

    assert await open_ticket_for(db, GUILD, member.id) is None
    cur = await db.conn.execute("SELECT * FROM modmail_tickets")
    row = await cur.fetchone()
    assert row["status"] == "closed" and "never_got_a_place" in row["close_reason"]
    assert "could not open a ticket" in member.dms[-1]["content"]
    assert "modmail.open_failed" in await action_kinds(db)


async def open_one(cog, bot, member):
    bot.guard = bot.guard or FakeGuard()
    await cog.on_message(dm_from(member))
    return await open_ticket_for(bot.db, GUILD, member.id)


async def test_a_plain_message_in_a_ticket_is_relayed_to_the_member(cog, bot, member, lead, db):
    ticket = await open_one(cog, bot, member)
    channel = bot.guild.get_channel(ticket["channel_id"])
    lead.roles = [FakeRole(STAFF_ROLE)]

    message = guild_message(channel, lead, "we are looking into it")
    await cog.on_message(message)

    embed = member.dms[-1]["embed"]
    assert embed.description == "we are looking into it" and embed.author.name == "Meg"
    rows = await ticket_messages(db, ticket["id"])
    assert rows[-1]["direction"] == OUT and rows[-1]["anonymous"] == 0
    assert message.reactions == []


async def test_an_equals_message_is_a_note_the_member_never_sees(cog, bot, member, lead, db):
    ticket = await open_one(cog, bot, member)
    channel = bot.guild.get_channel(ticket["channel_id"])
    lead.roles = [FakeRole(STAFF_ROLE)]
    before = len(member.dms)

    message = guild_message(channel, lead, "= watch this one")
    await cog.on_message(message)

    rows = await ticket_messages(db, ticket["id"])
    assert rows[-1]["direction"] == NOTE and rows[-1]["content"] == "watch this one"
    assert len(member.dms) == before
    assert message.reactions == []


async def test_a_non_staff_message_in_a_ticket_is_ignored(cog, bot, member, db):
    ticket = await open_one(cog, bot, member)
    channel = bot.guild.get_channel(ticket["channel_id"])
    nosy = FakeUser(bot.guild, user_id=77, display_name="Nosy")

    await cog.on_message(guild_message(channel, nosy, "hello?"))

    assert len(await ticket_messages(db, ticket["id"])) == 1


async def test_a_member_who_blocked_the_bot_produces_dm_failed_shown_in_the_ticket(
    cog, bot, member, lead, db
):
    ticket = await open_one(cog, bot, member)
    channel = bot.guild.get_channel(ticket["channel_id"])
    lead.roles = [FakeRole(STAFF_ROLE)]
    member.dm_raises = discord.Forbidden(_Response(403), "cannot send")

    message = guild_message(channel, lead, "hello")
    await cog.on_message(message)

    kinds = await action_kinds(db)
    assert "modmail.dm_failed" in kinds and "modmail.would_dm" not in kinds
    warned = bot.guild.channels[TEST_CHANNEL].messages[-1]
    assert "could not DM the member" in warned.content
    assert message.reactions == []


async def live(bot):
    bot.guard = None
    await bot.store.set(GUILD, "modmail_category_id", CATEGORY)


async def test_with_the_guard_lifted_a_ticket_talks_in_its_own_channel(cog, bot, member, lead, db):
    await live(bot)
    await cog.on_message(dm_from(member))
    ticket = await open_ticket_for(db, GUILD, member.id)
    channel = bot.guild.get_channel(ticket["channel_id"])
    lead.roles = [FakeRole(STAFF_ROLE)]

    reply = guild_message(channel, lead, "we are on it")
    await cog.on_message(reply)
    noted = guild_message(channel, lead, "=prior warnings")
    await cog.on_message(noted)

    titles = [m.kwargs["embed"].title for m in channel.messages]
    assert titles == ["Ticket #1", "From the member", "Sent to the member"]
    assert reply.reactions == ["\N{WHITE HEAVY CHECK MARK}"]
    assert noted.reactions == ["\N{MEMO}"]
    assert bot.guild.channels[TEST_CHANNEL].messages == []


async def test_the_ticket_channel_is_hidden_from_everyone_and_shown_to_staff(cog, bot, member):
    await live(bot)
    bot.guild.channels[TEST_CHANNEL].visible_to = {STAFF_ROLE}

    await cog.on_message(dm_from(member))

    overwrites = bot.guild.created[0].given_overwrites
    assert overwrites[bot.guild.default_role].view_channel is False
    assert any(getattr(key, "id", None) == STAFF_ROLE for key in overwrites)


async def test_reply_from_the_test_channel_finds_the_only_open_ticket(cog, bot, member, lead, db):
    ticket = await open_one(cog, bot, member)
    interaction = FakeInteraction(bot, lead)

    await cog.reply.callback(cog, interaction, text="on it")

    assert member.dms[-1]["embed"].description == "on it"
    assert "Sent to the member" in interaction.sent
    rows = await ticket_messages(db, ticket["id"])
    assert rows[-1]["direction"] == OUT


async def test_an_anonymous_reply_never_names_the_staff_member(cog, bot, member, lead, db):
    ticket = await open_one(cog, bot, member)
    interaction = FakeInteraction(bot, lead)

    await cog.areply.callback(cog, interaction, text="from the team")

    embed = member.dms[-1]["embed"]
    assert embed.author.name == "Staff" and embed.footer.text is None
    rows = await ticket_messages(db, ticket["id"])
    assert rows[-1]["anonymous"] == 1


async def test_a_reply_with_no_text_and_no_snippet_is_refused(cog, bot, member, lead):
    await open_one(cog, bot, member)
    interaction = FakeInteraction(bot, lead)

    await cog.reply.callback(cog, interaction, text=None)

    assert "nothing was sent" in interaction.sent
    assert member.dms[-1].get("embed") is None


async def test_a_reply_by_snippet_sends_the_saved_text(cog, bot, member, lead, db):
    await open_one(cog, bot, member)
    await db.conn.execute(
        "INSERT INTO modmail_snippets(name, content, by, at) VALUES ('appeal', 'Appeals go to a "
        "Lead.', 1, '2026-08-26T00:00:00+00:00')"
    )
    await db.conn.commit()
    interaction = FakeInteraction(bot, lead)

    await cog.reply.callback(cog, interaction, snippet="appeal")

    assert member.dms[-1]["embed"].description == "Appeals go to a Lead."


async def test_an_unknown_snippet_sends_nothing(cog, bot, member, lead):
    await open_one(cog, bot, member)
    interaction = FakeInteraction(bot, lead)

    await cog.reply.callback(cog, interaction, snippet="nope")

    assert "no snippet called" in interaction.sent


async def test_the_note_command_records_a_note_and_never_dms(cog, bot, member, lead, db):
    ticket = await open_one(cog, bot, member)
    before = len(member.dms)
    interaction = FakeInteraction(bot, lead)

    await cog.note.callback(cog, interaction, text="prior warnings", ticket=str(ticket["id"]))

    rows = await ticket_messages(db, ticket["id"])
    assert rows[-1]["direction"] == NOTE and rows[-1]["content"] == "prior warnings"
    assert len(member.dms) == before
    assert "never sees it" in interaction.sent


async def test_naming_a_ticket_that_is_not_a_number_is_refused(cog, bot, member, lead):
    await open_one(cog, bot, member)
    interaction = FakeInteraction(bot, lead)

    await cog.reply.callback(cog, interaction, text="hi", ticket="banana")

    assert "not a ticket number" in interaction.sent


async def test_two_open_tickets_force_the_staffer_to_name_one(cog, bot, member, lead, db):
    await open_one(cog, bot, member)
    other = FakeUser(bot.guild, user_id=901, display_name="Bob")
    bot.users[other.id] = other
    await cog.on_message(dm_from(other))
    interaction = FakeInteraction(bot, lead)

    await cog.reply.callback(cog, interaction, text="hi")

    assert len(await open_tickets(db, GUILD)) == 2
    assert "cannot tell which ticket" in interaction.sent


async def test_a_ticket_is_found_by_its_channel_and_by_its_thread(cog, bot, member, db):
    ticket = await open_one(cog, bot, member)

    found = await ticket_for_channel(db, ticket["channel_id"])
    row, why_not = await resolve_ticket(bot, bot.guild, ticket["channel_id"], None)

    assert found["id"] == ticket["id"] and row["id"] == ticket["id"] and why_not == ""


async def test_a_non_staff_caller_is_refused_before_anything_is_sent(cog, bot, member):
    await open_one(cog, bot, member)
    interaction = FakeInteraction(bot, member)

    await cog.reply.callback(cog, interaction, text="hi")

    assert "for staff only" in interaction.sent
    assert all(dm.get("embed") is None for dm in member.dms)


async def test_every_relay_forbids_every_mention_except_the_staff_ping(cog, bot, member, lead):
    ticket = await open_one(cog, bot, member)
    channel = bot.guild.get_channel(ticket["channel_id"])
    lead.roles = [FakeRole(STAFF_ROLE)]

    await cog.on_message(guild_message(channel, lead, "@everyone hello"))

    for message in bot.guild.channels[TEST_CHANNEL].messages:
        allowed = message.kwargs["allowed_mentions"]
        assert allowed.everyone is False and allowed.users is False
    assert member.dms[-1]["allowed_mentions"].everyone is False
    assert member.dms[-1]["allowed_mentions"].roles is False


async def test_a_stored_message_keeps_its_direction_and_anonymity(db):
    await db.conn.execute(
        "INSERT INTO modmail_tickets(guild_id, user_id, mode, channel_id, status, opened_at) "
        "VALUES (7, 900, 'channel', 5, 'open', '2026-08-26T00:00:00+00:00')"
    )
    await db.conn.commit()

    await add_message(db, 1, 1, OUT, content="hi", anonymous=True)

    row = (await ticket_messages(db, 1))[0]
    assert row["anonymous"] == 1 and row["direction"] == OUT
