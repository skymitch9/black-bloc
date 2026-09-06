import asyncio
from datetime import UTC, datetime, timedelta

import discord
import pytest

from black_bloc.cogs.moderation import modmail as modmail_cog
from black_bloc.cogs.moderation.modmail import (
    Modmail,
    add_message,
    block_member,
    blocked_row,
    get_ticket,
    open_ticket_for,
    open_tickets,
    resolve_ticket,
    ticket_for_channel,
    ticket_messages,
)
from black_bloc.config import load_settings
from black_bloc.modmail import COLOURS, IN, NOTE, OUT, UNDELIVERED_MARK, parse_topic
from black_bloc.settings_store import CHANNEL_MODE, THREAD_MODE, SettingsStore

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
        embed = kwargs.get("embed")
        self.embeds = kwargs.get("embeds") or ([embed] if embed is not None else [])

    async def add_reaction(self, emoji):
        self.reactions.append(emoji)


class FakePartialMessage:
    def __init__(self, channel, message_id):
        self.channel = channel
        self.id = message_id

    async def delete(self):
        found = [one for one in self.channel.messages if one.id == self.id]
        if not found:
            raise discord.NotFound(_Response(404), "gone")
        self.channel.messages.remove(found[0])
        self.channel.deleted_messages.append(self.id)


class Speaks:
    """The half of a channel or thread the card exercises: send, look up, delete by id."""

    def get_partial_message(self, message_id):
        return FakePartialMessage(self, message_id)

    async def fetch_message(self, message_id):
        for one in self.messages:
            if one.id == message_id:
                return one
        raise discord.NotFound(_Response(404), "gone")

    def next_message_id(self):
        self._last_message_id = getattr(self, "_last_message_id", 0) + 1
        return self._last_message_id


class FakeThread(Speaks):
    def __init__(self, thread_id, parent, name, **kwargs):
        self.id = thread_id
        self.parent = parent
        self.parent_id = parent.id
        self.guild = parent.guild
        self.name = name
        self.kwargs = kwargs
        self.messages = []
        self.deleted_messages = []
        self.archived = False
        self.locked = False
        self.deleted = False

    async def send(self, content=None, **kwargs):
        message = FakeMessage(self.next_message_id(), content or "", self, **kwargs)
        self.messages.append(message)
        return message

    async def edit(self, **kwargs):
        self.archived = kwargs.get("archived", self.archived)
        self.locked = kwargs.get("locked", self.locked)

    async def delete(self, reason=None):
        self.deleted = True


class FakeText(Speaks):
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
        self.deleted_messages = []
        self.threads = []
        self.deleted = False
        self.send_raises = None
        self.thread_raises = None

    def permissions_for(self, role):
        return FakePerms(view_channel=role.id in self.visible_to)

    async def send(self, content=None, **kwargs):
        if self.send_raises is not None:
            raise self.send_raises
        message = FakeMessage(self.next_message_id(), content or "", self, **kwargs)
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
        self.owned_channel_ids = set()

    def own_channel(self, channel):
        self.owned_channel_ids.add(getattr(channel, "id", channel))

    def disown_channel(self, channel):
        self.owned_channel_ids.discard(getattr(channel, "id", channel))

    def owns_channel(self, channel):
        return getattr(channel, "id", channel) in self.owned_channel_ids

    def allows_channel(self, channel_id):
        if channel_id in self.owned_channel_ids:
            return True
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
        self.dynamic = []

    def add_dynamic_items(self, *items):
        self.dynamic.extend(items)

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
        self.edits = []

    async def original_response(self):
        kept = {k: v for k, v in self.rendered.items() if k in ("embed", "view")}
        return FakeMessage(1, "", self.channel, **kept)

    async def edit_original_response(self, **kwargs):
        self.edits.append(kwargs)
        return FakeMessage(9500, "", self.channel, **kwargs)

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
        said = [m["content"] for m in self.response.messages if m["content"] is not None]
        return said[-1] if said else None


def labels(view):
    return [one.label for one in view.children if getattr(one, "label", None) is not None]


def button(view, label):
    return next(one for one in view.children if getattr(one, "label", None) == label)


def has(view, label):
    return any(getattr(one, "label", None) == label for one in view.children)


def control(view, placeholder):
    return next(
        one for one in view.children if getattr(one, "placeholder", None) == placeholder
    )


def placeholders(view):
    return [
        one.placeholder for one in view.children if getattr(one, "placeholder", None) is not None
    ]


async def pick(picker, values, interaction):
    picker._values = list(values)
    await picker.callback(interaction)


async def press(view, label, bot, who):
    interaction = FakeInteraction(bot, who)
    await button(view, label).callback(interaction)
    return interaction


async def choose(view, placeholder, values, bot, who):
    interaction = FakeInteraction(bot, who)
    await pick(control(view, placeholder), values, interaction)
    return interaction


async def open_panel(cog, bot, who):
    interaction = FakeInteraction(bot, who)
    await cog.modmail.callback(cog, interaction)
    return interaction


async def action_kinds(db):
    cur = await db.conn.execute("SELECT kind FROM action_log ORDER BY id")
    return [row["kind"] for row in await cur.fetchall()]



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
    made = FakeBot(db, store, settings, guild)
    try:
        yield made
    finally:
        modmail_cog.cancel_cards(made)


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
    """`/areply` retired into the card's **Reply as Staff**; the embed is byte-identical."""
    ticket = await open_one(cog, bot, member)
    lead.roles = [FakeRole(STAFF_ROLE)]
    card = await card_for(cog, bot, ticket)

    opened = await press_card(bot, lead, card, "Reply as Staff")
    modal = opened.response.modals[-1]
    modal.text._value = "from the team"
    await modal.on_submit(FakeInteraction(bot, lead))

    embed = member.dms[-1]["embed"]
    assert embed.author.name == "Staff" and embed.footer.text is None
    assert embed.colour.value == COLOURS[OUT]
    rows = await ticket_messages(db, ticket["id"])
    assert rows[-1]["anonymous"] == 1


async def test_a_named_reply_still_carries_the_staff_members_role_colour(cog, bot, member, lead):
    await open_one(cog, bot, member)

    await cog.reply.callback(cog, FakeInteraction(bot, lead), text="on it")

    assert member.dms[-1]["embed"].colour.value == 0xABCDEF


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


async def test_closing_files_a_transcript_deletes_the_channel_and_tells_the_member(
    cog, bot, member, lead, db
):
    ticket = await open_one(cog, bot, member)
    channel = bot.guild.get_channel(ticket["channel_id"])
    lead.roles = [FakeRole(STAFF_ROLE)]
    await cog.on_message(guild_message(channel, lead, "sorted for you"))

    interaction = await close_from_card(cog, bot, lead, ticket, reason="sorted")

    row = await get_ticket(db, ticket["id"])
    assert row["status"] == "closed" and row["close_reason"] == "sorted"
    assert row["closed_by"] == LEAD and row["log_message_id"] is not None
    posted = bot.guild.channels[TEST_CHANNEL].messages[-1]
    assert posted.kwargs["file"].filename == f"modmail-ticket-{ticket['id']}.txt"
    body = posted.kwargs["file"].fp.getvalue().decode()
    assert "MEMBER 900: my ban was unfair" in body and "STAFF 1: sorted for you" in body
    assert channel.deleted is True
    assert "has been closed" in member.dms[-1]["content"]
    kinds = await action_kinds(db)
    assert "modmail.transcript" in kinds and "modmail.closed" in kinds
    assert interaction.response.messages[0]["deferred"] is True


async def test_a_silent_close_files_the_transcript_without_dming_anybody(
    cog, bot, member, lead, db
):
    ticket = await open_one(cog, bot, member)
    before = len(member.dms)

    await close_from_card(cog, bot, lead, ticket, reason="spam", silent=True)

    assert (await get_ticket(db, ticket["id"]))["status"] == "closed"
    assert len(member.dms) == before


async def test_closing_a_ticket_twice_tells_the_second_staffer_rather_than_closing_again(
    cog, bot, member, lead, db
):
    ticket = await open_one(cog, bot, member)
    card = await card_for(cog, bot, ticket)
    await close_from_card(cog, bot, lead, ticket, reason="one", card=card)

    second = await press_card(bot, lead, card, "Close…")

    assert second.response.modals == [] and "already closed" in second.sent
    assert (await get_ticket(db, ticket["id"]))["close_reason"] == "one"


async def test_a_closed_ticket_frees_the_member_to_open_another(cog, bot, member, lead, db):
    first = await open_one(cog, bot, member)
    await close_from_card(cog, bot, lead, first, reason="done")

    await cog.on_message(dm_from(member, "hello again"))

    second = await open_ticket_for(db, GUILD, member.id)
    assert second is not None and second["id"] != first["id"]
    assert len(bot.guild.created) == 2


async def test_a_transcript_the_guard_would_refuse_is_a_would_not_a_failure(
    cog, bot, member, lead, db
):
    ticket = await open_one(cog, bot, member)
    await bot.store.set(GUILD, "modmail_log_channel_id", LOG_CHANNEL)

    interaction = await close_from_card(cog, bot, lead, ticket, reason="sorted")

    kinds = await action_kinds(db)
    assert "modmail.would_post_transcript" in kinds
    assert "modmail.transcript_failed" not in kinds
    assert (await get_ticket(db, ticket["id"]))["status"] == "closed"
    assert "transcript could not be posted" in interaction.sent


async def test_a_thread_ticket_is_archived_and_locked_not_deleted(cog, bot, member, lead, db):
    bot.guard = FakeGuard()
    await bot.store.set(GUILD, "modmail_mode", THREAD_MODE)
    await cog.on_message(dm_from(member))
    ticket = await open_ticket_for(db, GUILD, member.id)
    thread = bot.guild.threads[ticket["thread_id"]]

    await close_from_card(cog, bot, lead, ticket, reason="done")

    assert thread.archived is True and thread.locked is True and thread.deleted is False


async def test_a_ticket_whose_channel_has_gone_is_closed_on_the_second_miss(cog, bot, member, db):
    ticket = await open_one(cog, bot, member)
    bot.guild.channels.pop(ticket["channel_id"])
    before = len(member.dms)

    await cog.reconcile_tickets()
    assert (await get_ticket(db, ticket["id"]))["status"] == "open"

    await cog.reconcile_tickets()

    row = await get_ticket(db, ticket["id"])
    assert row["status"] == "closed" and row["close_reason"] == "ticket_channel_gone"
    assert "has been closed" in member.dms[-1]["content"]
    assert len(member.dms) == before + 1


async def test_a_channel_that_comes_back_between_two_ticks_is_left_open(cog, bot, member, db):
    ticket = await open_one(cog, bot, member)
    channel = bot.guild.channels.pop(ticket["channel_id"])

    await cog.reconcile_tickets()
    bot.guild.channels[channel.id] = channel
    await cog.reconcile_tickets()
    bot.guild.channels.pop(channel.id)
    await cog.reconcile_tickets()

    assert (await get_ticket(db, ticket["id"]))["status"] == "open"
    assert cog.last_ok_at is not None


async def test_a_ticket_that_never_got_a_channel_is_left_alone_inside_the_grace(cog, bot, db):
    await db.conn.execute(
        "INSERT INTO modmail_tickets(guild_id, user_id, mode, channel_id, status, opened_at) "
        "VALUES (?, ?, 'channel', 0, 'open', ?)",
        (GUILD, USER, datetime.now(UTC).isoformat()),
    )
    await db.conn.commit()

    await cog.reconcile_tickets()
    assert (await get_ticket(db, 1))["status"] == "open"

    await db.conn.execute(
        "UPDATE modmail_tickets SET opened_at = ?",
        ((datetime.now(UTC) - timedelta(hours=2)).isoformat(),),
    )
    await db.conn.commit()
    await cog.reconcile_tickets()

    row = await get_ticket(db, 1)
    assert row["status"] == "closed" and row["close_reason"] == "never_got_a_place"


async def test_a_lookup_that_could_not_be_made_never_closes_a_ticket(cog, bot, member, db):
    ticket = await open_one(cog, bot, member)
    bot.guild.channels.pop(ticket["channel_id"])

    async def broken(channel_id):
        raise discord.HTTPException(_Response(500), "later")

    bot.guild.fetch_channel = broken
    await cog.reconcile_tickets()

    assert (await get_ticket(db, ticket["id"]))["status"] == "open"


async def test_deleting_the_ticket_channel_closes_its_ticket_at_once(cog, bot, member, db):
    ticket = await open_one(cog, bot, member)
    channel = bot.guild.get_channel(ticket["channel_id"])
    bot.guild.channels.pop(channel.id)

    await cog.on_guild_channel_delete(channel)

    row = await get_ticket(db, ticket["id"])
    assert row["status"] == "closed" and row["close_reason"] == "ticket_channel_deleted"


async def test_a_deleted_category_or_staff_channel_is_forgotten(cog, bot, db):
    await live(bot)
    await bot.store.set(GUILD, "modmail_staff_channel_id", LOG_CHANNEL)
    category = bot.guild.channels[CATEGORY]
    category.guild = bot.guild

    await cog.on_guild_channel_delete(category)
    await cog.on_guild_channel_delete(bot.guild.channels[LOG_CHANNEL])

    assert bot.store.get(GUILD, "modmail_category_id") != CATEGORY
    assert bot.store.get(GUILD, "modmail_staff_channel_id") is None
    kinds = await action_kinds(db)
    assert "modmail.category_forgotten" in kinds
    assert "modmail.staff_channel_forgotten" in kinds


async def open_blocked_panel(cog, bot, lead):
    root = await open_panel(cog, bot, lead)
    return await press(root.view, "Blocked…", bot, lead)


async def open_snippets_panel(cog, bot, lead):
    root = await open_panel(cog, bot, lead)
    return await press(root.view, "Snippets…", bot, lead)


async def add_snippet(cog, bot, lead, name, content, *, view=None):
    panel = view or (await open_snippets_panel(cog, bot, lead)).view
    opened = await press(panel, "Add one…", bot, lead)
    modal = opened.response.modals[-1]
    modal.name._value = name
    modal.content._value = content
    submitted = FakeInteraction(bot, lead)
    await modal.on_submit(submitted)
    return submitted


async def test_blocking_and_unblocking_are_both_recorded(cog, bot, member, lead, db):
    panel = await open_blocked_panel(cog, bot, lead)
    chosen = await press(panel.view, "Block someone…", bot, lead)
    picked = await choose(chosen.view, modmail_cog.PICK_SOMEBODY, [member], bot, lead)
    asked = await press(picked.view, "Block them…", bot, lead)
    modal = asked.response.modals[-1]
    modal.note._value = "abuse"
    blocked = FakeInteraction(bot, lead)
    await modal.on_submit(blocked)

    assert (await blocked_row(db, member.id))["reason"] == "abuse"
    assert "can no longer open modmail tickets" in blocked.sent
    listed = await press(blocked.view, "Refresh", bot, lead)
    chosen_again = await choose(
        listed.view, modmail_cog.PICK_A_BLOCK, [str(member.id)], bot, lead
    )
    freed = await press(chosen_again.view, "Unblock them", bot, lead)

    assert await blocked_row(db, member.id) is None
    assert "can open modmail tickets again" in freed.sent
    kinds = await action_kinds(db)
    assert kinds.count("modmail.blocked") == 1 and kinds.count("modmail.unblocked") == 1


async def test_blocking_somebody_already_blocked_changes_nothing_and_says_so(
    cog, bot, member, lead, db
):
    await block_member(bot, bot.guild, lead, member, "abuse")
    panel = await open_blocked_panel(cog, bot, lead)
    chosen = await press(panel.view, "Block someone…", bot, lead)
    picked = await choose(chosen.view, modmail_cog.PICK_SOMEBODY, [member], bot, lead)
    asked = await press(picked.view, "Block them…", bot, lead)
    modal = asked.response.modals[-1]
    modal.note._value = "again"
    again = FakeInteraction(bot, lead)
    await modal.on_submit(again)

    assert "was already blocked" in again.sent
    assert (await blocked_row(db, member.id))["reason"] == "abuse"
    assert (await action_kinds(db)).count("modmail.blocked") == 1


async def test_unblock_is_not_drawn_until_somebody_is_picked(cog, bot, member, lead):
    await block_member(bot, bot.guild, lead, member, None)
    panel = await open_blocked_panel(cog, bot, lead)

    assert not has(panel.view, "Unblock them")
    picked = await choose(panel.view, modmail_cog.PICK_A_BLOCK, [str(member.id)], bot, lead)
    assert has(picked.view, "Unblock them")


async def test_changing_the_mode_says_open_tickets_keep_theirs(cog, bot, member, lead):
    await open_one(cog, bot, member)
    root = await open_panel(cog, bot, lead)
    setup = await press(root.view, "Setup…", bot, lead)
    picker = await press(setup.view, "Mode…", bot, lead)

    changed = await choose(picker.view, modmail_cog.PICK_A_MODE, [THREAD_MODE], bot, lead)

    assert bot.store.get(GUILD, "modmail_mode") == THREAD_MODE
    assert "1 ticket(s) already open keep the mode" in changed.sent
    assert "**mode** — thread" in changed.embed.description


async def test_answer_dms_is_one_button_that_names_what_it_will_do(cog, bot, lead, db):
    root = await open_panel(cog, bot, lead)
    setup = await press(root.view, "Setup…", bot, lead)

    assert has(setup.view, "Answer DMs off") and not has(setup.view, "Answer DMs on")
    turned = await press(setup.view, "Answer DMs off", bot, lead)

    assert bot.store.get(GUILD, "modmail_enabled") is False
    assert "stopped answering modmail DMs" in turned.sent
    assert has(turned.view, "Answer DMs on")
    assert "modmail.settings" in await action_kinds(db)


async def test_pointing_the_transcripts_channel_re_renders_setup_with_the_new_value(
    cog, bot, lead, db
):
    root = await open_panel(cog, bot, lead)
    setup = await press(root.view, "Setup…", bot, lead)
    picker = await press(setup.view, "Transcripts…", bot, lead)

    done = await choose(
        picker.view,
        modmail_cog.PICK_A_CHANNEL,
        [bot.guild.channels[LOG_CHANNEL]],
        bot,
        lead,
    )

    assert bot.store.get(GUILD, "modmail_log_channel_id") == LOG_CHANNEL
    assert f"**transcripts** — <#{LOG_CHANNEL}>" in done.embed.description
    assert (await action_kinds(db)).count("modmail.settings") == 1


async def test_the_panel_lists_the_open_tickets_and_the_resolved_staff(cog, bot, member, lead):
    ticket = await open_one(cog, bot, member)

    interaction = await open_panel(cog, bot, lead)

    said = interaction.response.messages[0]
    assert said["ephemeral"] is True and said["allowed_mentions"].everyone is False
    assert said["embed"].title == modmail_cog.PANEL_TITLE
    assert f"**#{ticket['id']}**" in said["embed"].description
    assert "Lead" in said["embed"].description
    assert labels(said["view"])[:3] == ["Setup…", "Blocked…", "Snippets…"]
    assert {"Logs", "Refresh"} <= set(labels(said["view"]))
    assert "/modmail status" not in said["embed"].description


async def test_the_panel_warns_loudly_when_no_staff_role_resolves(cog, bot, lead):
    bot.guild.channels[TEST_CHANNEL].visible_to = set()

    interaction = await open_panel(cog, bot, lead)

    assert "No staff roles resolve" in interaction.embed.description


async def test_forget_only_ever_offers_the_places_that_are_pointed(cog, bot, lead):
    root = await open_panel(cog, bot, lead)
    one = await press(root.view, "Forget…", bot, lead)
    assert [o.value for o in control(one.view, modmail_cog.PICK_A_PLACE).options] == [
        "modmail_log_channel_id"
    ]

    await live(bot)
    pointed = await open_panel(cog, bot, lead)
    two = await press(pointed.view, "Forget…", bot, lead)

    assert [o.value for o in control(two.view, modmail_cog.PICK_A_PLACE).options] == [
        "modmail_category_id",
        "modmail_log_channel_id",
    ]


async def test_snippets_are_saved_listed_and_removed(cog, bot, lead, db):
    saved = await add_snippet(cog, bot, lead, "Appeal", "Appeals go to a Lead.")

    assert "appeal" in saved.sent
    assert "**appeal** — Appeals go to a Lead." in saved.embed.description
    asked = await press(saved.view, "Remove it", bot, lead)
    assert "Remove the snippet **appeal**?" in asked.embed.description
    gone = await press(asked.view, "Yes, remove it", bot, lead)

    assert "is gone" in gone.sent
    cur = await db.conn.execute("SELECT COUNT(*) AS n FROM modmail_snippets")
    assert (await cur.fetchone())["n"] == 0
    assert "modmail.snippet_removed" in await action_kinds(db)


async def test_keeping_a_snippet_leaves_it_where_it_was(cog, bot, lead, db):
    saved = await add_snippet(cog, bot, lead, "appeal", "one")
    asked = await press(saved.view, "Remove it", bot, lead)

    kept = await press(asked.view, "Keep it", bot, lead)

    assert has(kept.view, "Remove it")
    cur = await db.conn.execute("SELECT COUNT(*) AS n FROM modmail_snippets")
    assert (await cur.fetchone())["n"] == 1
    assert "modmail.snippet_removed" not in await action_kinds(db)


async def test_a_snippet_name_with_spaces_is_refused(cog, bot, lead, db):
    refused = await add_snippet(cog, bot, lead, "ban appeal", "no")

    assert "is not a snippet name" in refused.sent
    cur = await db.conn.execute("SELECT COUNT(*) AS n FROM modmail_snippets")
    assert (await cur.fetchone())["n"] == 0


async def test_a_stranger_is_told_nothing_at_all_while_no_guild_has_modmail_on(cog, bot, db):
    bot.guard = FakeGuard()
    await bot.store.set(GUILD, "modmail_enabled", False)
    stranger = FakeUser(None, user_id=4242, display_name="Stranger")

    await cog.on_message(dm_from(stranger))

    assert stranger.dms == []
    cur = await db.conn.execute("SELECT COUNT(*) AS n FROM modmail_tickets")
    assert (await cur.fetchone())["n"] == 0


async def test_a_refusal_is_sent_once_per_member_until_the_cooldown_is_over(cog, bot, member):
    bot.guard = FakeGuard()
    await bot.store.set(GUILD, "modmail_enabled", False)

    await cog.on_message(dm_from(member, "first"))
    await cog.on_message(dm_from(member, "second"))
    await cog.on_message(dm_from(member, "third"))

    assert len(member.dms) == 1
    cog._refused.clear()
    await cog.on_message(dm_from(member, "much later"))
    assert len(member.dms) == 2


async def test_a_test_channel_with_no_category_opens_no_ticket_at_the_top_level(
    cog, bot, member, db
):
    bot.guard = FakeGuard()
    bot.guild.channels[TEST_CHANNEL].category = None
    bot.guild.channels[TEST_CHANNEL].category_id = None

    await cog.on_message(dm_from(member))

    assert bot.guild.created == []
    assert await open_ticket_for(db, GUILD, member.id) is None
    cur = await db.conn.execute("SELECT close_reason FROM modmail_tickets")
    assert "no_test_channel" in (await cur.fetchone())["close_reason"]
    assert "could not open a ticket" in member.dms[-1]["content"]


async def test_no_staff_role_resolving_means_no_ticket_is_opened_at_all(cog, bot, member, db):
    bot.guard = FakeGuard()
    bot.guild.channels[TEST_CHANNEL].visible_to = set()

    await cog.on_message(dm_from(member))

    assert bot.guild.created == []
    assert await open_ticket_for(db, GUILD, member.id) is None
    cur = await db.conn.execute("SELECT close_reason FROM modmail_tickets")
    assert "no_staff_roles" in (await cur.fetchone())["close_reason"]
    assert "modmail.open_failed" in await action_kinds(db)
    assert "could not open a ticket" in member.dms[-1]["content"]


async def test_a_relay_that_never_reached_the_ticket_gets_a_warning_reaction(cog, bot, member, db):
    bot.guard = FakeGuard()
    bot.guild.channels[TEST_CHANNEL].send_raises = refused()

    message = dm_from(member)
    await cog.on_message(message)

    assert message.reactions == ["\N{WARNING SIGN}"]
    assert "modmail.relay_failed" in await action_kinds(db)
    assert await open_ticket_for(db, GUILD, member.id) is not None


async def test_a_reply_the_member_never_got_is_marked_undelivered_in_the_transcript(
    cog, bot, member, lead, db
):
    ticket = await open_one(cog, bot, member)
    member.dm_raises = discord.Forbidden(_Response(403), "cannot send")

    await cog.reply.callback(cog, FakeInteraction(bot, lead), text="are you there")
    rows = await ticket_messages(db, ticket["id"])
    assert rows[-1]["delivered"] == 0

    member.dm_raises = None
    await close_from_card(cog, bot, lead, ticket, reason="no answer")

    body = bot.guild.channels[TEST_CHANNEL].messages[-1].kwargs["file"].fp.getvalue().decode()
    assert UNDELIVERED_MARK in body


async def test_a_transcript_that_could_not_be_filed_keeps_the_ticket_channel(
    cog, bot, member, lead, db
):
    ticket = await open_one(cog, bot, member)
    channel = bot.guild.get_channel(ticket["channel_id"])
    await bot.store.set(GUILD, "modmail_log_channel_id", LOG_CHANNEL)

    interaction = await close_from_card(cog, bot, lead, ticket, reason="sorted")

    assert channel.deleted is False
    assert (await get_ticket(db, ticket["id"]))["status"] == "closed"
    assert "left where it is" in interaction.sent
    assert "modmail.place_kept" in await action_kinds(db)
    assert len(await ticket_messages(db, ticket["id"])) == 1


async def test_every_panel_move_defers_before_it_edits(cog, bot, member, lead):
    await open_one(cog, bot, member)
    await live(bot)
    root = await open_panel(cog, bot, lead)

    for label in ("Setup…", "Blocked…", "Snippets…", "Forget…", "Refresh"):
        interaction = await press(root.view, label, bot, lead)
        assert interaction.response.messages[0].get("deferred") is True, label
        assert interaction.edits, label


async def test_a_demoted_staffer_moves_nothing_from_a_panel_already_open(cog, bot, lead, db):
    root = await open_panel(cog, bot, lead)
    setup = await press(root.view, "Setup…", bot, lead)
    lead.guild_permissions = FakePerms(manage_guild=False)
    lead.roles = []

    refused = await press(setup.view, "Answer DMs off", bot, lead)

    assert bot.store.get(GUILD, "modmail_enabled") is True
    assert refused.edits == []
    assert refused.sent is not None
    assert "modmail.settings" not in await action_kinds(db)


async def test_a_panel_that_goes_quiet_disables_every_button_and_writes_the_footer(
    cog, bot, lead
):
    interaction = await open_panel(cog, bot, lead)
    view = interaction.view
    view.message = await interaction.original_response()
    view.last_interaction = interaction

    await view.on_timeout()

    assert all(item.disabled for item in view.children)
    assert interaction.edits[-1]["embeds"][0].footer.text == modmail_cog.PANEL_TIMEOUT_FOOTER


async def test_a_non_staff_caller_gets_the_sentence_and_no_panel_at_all(cog, bot, member):
    interaction = await open_panel(cog, bot, member)

    assert interaction.view is None
    assert interaction.sent is not None


async def test_logs_answers_a_new_followup_and_leaves_the_panel_where_it_was(cog, bot, lead):
    root = await open_panel(cog, bot, lead)

    logs = await press(root.view, "Logs", bot, lead)

    assert logs.edits == []
    assert logs.response.messages and logs.response.messages[-1]["ephemeral"] is True
    assert root.view.replaced is False


async def test_the_blocked_list_stops_at_the_cap_and_names_the_site_for_the_rest(
    cog, bot, lead, db
):
    for user_id in range(500, 530):
        await block_member(bot, bot.guild, lead, user_id, None)

    panel = await open_blocked_panel(cog, bot, lead)

    picker = next(one for one in panel.view.children if getattr(one, "options", None))
    assert len(picker.options) == 25
    assert "25 of 30" in picker.placeholder
    assert "Modmail page" in panel.embed.description


async def test_somebody_past_the_cap_is_still_blockable_through_the_user_picker(
    cog, bot, member, lead, db
):
    for user_id in range(500, 530):
        await block_member(bot, bot.guild, lead, user_id, None)
    panel = await open_blocked_panel(cog, bot, lead)

    chosen = await press(panel.view, "Block someone…", bot, lead)

    assert modmail_cog.PICK_SOMEBODY in placeholders(chosen.view)
    assert modmail_cog.PICK_A_BLOCK not in placeholders(chosen.view)
    picked = await choose(chosen.view, modmail_cog.PICK_SOMEBODY, [member], bot, lead)
    asked = await press(picked.view, "Block them…", bot, lead)
    modal = asked.response.modals[-1]
    modal.note._value = ""
    await modal.on_submit(FakeInteraction(bot, lead))

    assert await blocked_row(db, member.id) is not None


async def test_a_re_render_retires_the_view_it_replaced(cog, bot, lead):
    root = await open_panel(cog, bot, lead)
    first = root.view

    await press(first, "Setup…", bot, lead)

    assert first.replaced is True and first.is_finished()


async def test_an_unavailable_guild_is_never_reconciled(cog, bot, member, db):
    ticket = await open_one(cog, bot, member)
    bot.guild.channels.pop(ticket["channel_id"])
    bot.guild.unavailable = True

    await cog.reconcile_tickets()
    await cog.reconcile_tickets()
    await cog.reconcile_tickets()

    assert (await get_ticket(db, ticket["id"]))["status"] == "open"


async def test_a_loop_that_raised_records_the_error_and_asks_to_be_restarted(cog):
    await cog._reconcile_error(RuntimeError("boom"))

    assert "boom" in cog.last_error and "RuntimeError" in cog.last_error


async def test_on_ready_starts_the_loop_when_cog_load_never_did(cog, bot):
    await cog.on_ready()

    try:
        assert cog._reconcile_loop.is_running() is True
        assert cog.last_ok_at is not None
    finally:
        await cog.cog_unload()


async def test_the_panel_shows_the_reconcilers_health_not_just_its_liveness(cog, bot, lead):
    await cog.reconcile_tickets()
    cog.last_error = "HTTPException: 500"

    interaction = await open_panel(cog, bot, lead)

    said = interaction.embed.description
    assert "last ok" in said and cog.last_ok_at in said
    assert "HTTPException: 500" in said


async def test_a_reply_into_an_archived_thread_unarchives_it_first(cog, bot, member, lead, db):
    bot.guard = FakeGuard()
    await bot.store.set(GUILD, "modmail_mode", THREAD_MODE)
    await cog.on_message(dm_from(member))
    ticket = await open_ticket_for(db, GUILD, member.id)
    thread = bot.guild.threads[ticket["thread_id"]]
    thread.archived = True
    bot.guard = None
    await bot.store.set(GUILD, "modmail_category_id", CATEGORY)

    await cog.reply.callback(cog, FakeInteraction(bot, lead), text="still here")

    assert thread.archived is False
    assert thread.messages[-1].kwargs["embed"].description == "still here"


async def test_a_ticket_number_written_in_exotic_digits_is_refused(cog, bot, member, lead):
    await open_one(cog, bot, member)
    interaction = FakeInteraction(bot, lead)

    await cog.reply.callback(cog, interaction, text="hi", ticket="²")

    assert "not a ticket number" in interaction.sent


async def test_forget_clears_one_place_and_says_which(cog, bot, lead, db):
    await live(bot)
    root = await open_panel(cog, bot, lead)
    panel = await press(root.view, "Forget…", bot, lead)

    cleared = await choose(
        panel.view, modmail_cog.PICK_A_PLACE, ["modmail_category_id"], bot, lead
    )

    assert bot.store.get(GUILD, "modmail_category_id") is None
    assert "modmail_category_id" in cleared.sent
    assert "modmail.forgotten" in await action_kinds(db)
    assert not has(cleared.view, "Forget…")


async def test_a_member_who_leaves_is_noted_in_the_ticket_which_stays_open(cog, bot, member, db):
    ticket = await open_one(cog, bot, member)

    await cog.on_member_remove(member)

    rows = await ticket_messages(db, ticket["id"])
    assert rows[-1]["direction"] == NOTE and "left the server" in rows[-1]["content"]
    assert (await get_ticket(db, ticket["id"]))["status"] == "open"
    assert "modmail.member_left" in await action_kinds(db)


async def test_a_snippet_is_never_overwritten_by_accident(cog, bot, lead, db):
    """`Add one…` refuses a name that is taken and names `Change it…`, which is the overwrite."""
    saved = await add_snippet(cog, bot, lead, "appeal", "one")

    clash = await add_snippet(cog, bot, lead, "appeal", "two", view=saved.view)

    assert "already a snippet" in clash.sent and "Change it…" in clash.sent
    picked = await choose(clash.view, modmail_cog.PICK_A_SNIPPET, ["appeal"], bot, lead)
    opened = await press(picked.view, "Change it…", bot, lead)
    modal = opened.response.modals[-1]
    assert modal.name.default == "appeal" and modal.content.default == "one"
    modal.name._value = "appeal"
    modal.content._value = "two"
    changed = FakeInteraction(bot, lead)
    await modal.on_submit(changed)

    assert "saved" in changed.sent
    cur = await db.conn.execute("SELECT content FROM modmail_snippets WHERE name = 'appeal'")
    assert (await cur.fetchone())["content"] == "two"


async def test_a_message_that_starts_by_mentioning_the_bot_is_not_a_reply(
    cog, bot, member, lead, db
):
    ticket = await open_one(cog, bot, member)
    channel = bot.guild.get_channel(ticket["channel_id"])
    lead.roles = [FakeRole(STAFF_ROLE)]
    bot.user = FakeRole(4242, "Black Bloc")
    before = len(member.dms)

    await cog.on_message(guild_message(channel, lead, "<@4242> status?"))

    assert len(await ticket_messages(db, ticket["id"])) == 1
    assert len(member.dms) == before


# --- the sticky ticket card ------------------------------------------------------------------


CARD_LABELS = ["Reply", "Reply as Staff", "Private note", "Close…"]


def cards_in(channel):
    return [one for one in channel.messages if one.kwargs.get("view") is not None]


async def card_for(cog, bot, ticket):
    modmail_cog.cancel_cards(bot)
    return await modmail_cog.refresh_card(bot, bot.guild, ticket["id"])


def choose_snippet(picker, name):
    """A RadioGroup answers with `value`; a Select answers with `values`."""
    if hasattr(picker, "values"):
        picker._values = [name]
    else:
        picker._value = name


async def quick_cards(monkeypatch, debounce=0.05):
    """The real debounce with the clock wound down — the coalescing is what is under test."""
    monkeypatch.setattr(modmail_cog, "CARD_DEBOUNCE_SECONDS", debounce)
    monkeypatch.setattr(modmail_cog, "CARD_MIN_GAP_SECONDS", 0.0)


async def close_from_card(cog, bot, lead, ticket, reason=None, silent=False, card=None):
    """`/close` retired into the card, so every close test presses the button instead."""
    lead.roles = [FakeRole(STAFF_ROLE)]
    on = card if card is not None else await card_for(cog, bot, ticket)
    opened = await press_card(bot, lead, on, "Close…")
    modal = opened.response.modals[-1]
    modal.reason._value = reason or ""
    if silent:
        modal.quiet._values = ["silent"]
    closed = FakeInteraction(bot, lead)
    await modal.on_submit(closed)
    return closed


async def press_card(bot, who, message, label, channel=None):
    view = message.kwargs["view"]
    item = next(one for one in view.children if one.item.label == label)
    interaction = FakeInteraction(bot, who, channel=channel)
    await item.callback(interaction)
    return interaction


async def test_the_card_carries_the_four_moves_and_lands_last(cog, bot, member, db):
    ticket = await open_one(cog, bot, member)

    message = await card_for(cog, bot, ticket)

    assert message is bot.guild.channels[TEST_CHANNEL].messages[-1]
    labels_on = [one.item.label for one in message.kwargs["view"].children]
    assert labels_on == CARD_LABELS
    assert message.kwargs["embed"].title == "Ticket #1"
    assert (await get_ticket(db, ticket["id"]))["card_message_id"] == message.id


async def test_a_member_message_moves_the_card_to_the_bottom(
    cog, bot, member, db, monkeypatch
):
    await quick_cards(monkeypatch)
    ticket = await open_one(cog, bot, member)
    first = await card_for(cog, bot, ticket)
    channel = bot.guild.channels[TEST_CHANNEL]

    await cog.on_message(dm_from(member, "still waiting"))
    await modmail_cog.settle_cards(bot)

    assert first.id in channel.deleted_messages
    assert len(cards_in(channel)) == 1
    assert channel.messages[-1] is cards_in(channel)[0]
    assert (await get_ticket(db, ticket["id"]))["card_message_id"] == channel.messages[-1].id


async def test_the_new_card_id_is_written_before_the_old_card_is_deleted(
    cog, bot, member, db, monkeypatch
):
    """Checklist 12: a failed delete leaves two working cards; a failed write leaves an orphan."""
    ticket = await open_one(cog, bot, member)
    first = await card_for(cog, bot, ticket)
    seen = []
    real = modmail_cog.drop_old_card

    async def watched(bot_, guild, row, channel, old_id):
        seen.append((await get_ticket(db, row["id"]))["card_message_id"])
        await real(bot_, guild, row, channel, old_id)

    monkeypatch.setattr(modmail_cog, "drop_old_card", watched)

    second = await card_for(cog, bot, ticket)

    assert seen == [second.id] and second.id != first.id


async def test_a_delete_the_guard_refuses_is_a_shadow_row_and_not_a_failure(
    cog, bot, member, db, monkeypatch
):
    ticket = await open_one(cog, bot, member)
    first = await card_for(cog, bot, ticket)
    bot.guard = FakeGuard(test_channel_id=0)
    monkeypatch.setattr(modmail_cog, "test_channel", lambda _bot: None)

    await modmail_cog.drop_old_card(
        bot, bot.guild, ticket, bot.guild.channels[TEST_CHANNEL], first.id
    )

    kinds = await action_kinds(db)
    assert "modmail.would_replace_card" in kinds
    assert "modmail.card_failed" not in kinds
    assert first.id not in bot.guild.channels[TEST_CHANNEL].deleted_messages


async def test_a_card_that_cannot_be_posted_says_so_once(cog, bot, member, db):
    ticket = await open_one(cog, bot, member)
    bot.guild.channels[TEST_CHANNEL].send_raises = refused()

    assert await modmail_cog.refresh_card(bot, bot.guild, ticket["id"]) is None
    kinds = await action_kinds(db)
    assert kinds.count("modmail.card_failed") == 1
    assert (await get_ticket(db, ticket["id"]))["card_message_id"] is None


async def test_a_card_move_that_raised_inside_its_task_leaves_a_row_not_just_a_warning(
    cog, bot, member, db, monkeypatch
):
    """Nothing awaits the debounced task, so a raise there used to be invisible on the Logs page."""
    await quick_cards(monkeypatch)
    ticket = await open_one(cog, bot, member)

    async def blows_up(*_args, **_kwargs):
        raise RuntimeError("the card went nowhere")

    monkeypatch.setattr(modmail_cog, "refresh_card", blows_up)
    await modmail_cog.bump_card(bot, bot.guild, ticket)
    await modmail_cog.settle_cards(bot)

    rows = await db.conn.execute(
        "SELECT kind, details FROM action_log WHERE kind = 'modmail.card_failed'"
    )
    found = await rows.fetchall()
    assert len(found) == 1
    assert str(ticket["id"]) in found[0]["details"]
    assert "the card went nowhere" in found[0]["details"]
    assert modmail_cog.card_clock(bot)["tasks"] == {}


async def test_a_burst_of_messages_coalesces_into_one_card_move(
    cog, bot, member, db, monkeypatch
):
    """The debounce is what stops five DMs costing fifteen calls; the clock is not waited on."""
    monkeypatch.setattr(modmail_cog, "CARD_DEBOUNCE_SECONDS", 30.0)
    ticket = await open_one(cog, bot, member)
    await card_for(cog, bot, ticket)
    channel = bot.guild.channels[TEST_CHANNEL]
    before = len(channel.deleted_messages)

    for _ in range(5):
        await cog.on_message(dm_from(member, "hello?"))

    assert list(modmail_cog.card_clock(bot)["tasks"]) == [ticket["id"]]
    assert len(channel.deleted_messages) == before

    modmail_cog.cancel_cards(bot)
    await modmail_cog.refresh_card(bot, bot.guild, ticket["id"])

    assert len(cards_in(channel)) == 1
    assert len(channel.deleted_messages) == before + 1


async def test_a_write_that_lands_mid_post_is_not_dropped(cog, bot, member, db, monkeypatch):
    """F-M1 (a) promises the card is LAST. A bump arriving while the post is in flight used to
    hit the pending-task guard and vanish; it now marks the ticket dirty and goes round again."""
    monkeypatch.setattr(modmail_cog, "CARD_DEBOUNCE_SECONDS", 0.0)
    monkeypatch.setattr(modmail_cog, "CARD_MIN_GAP_SECONDS", 0.0)
    ticket = await open_one(cog, bot, member)
    await card_for(cog, bot, ticket)
    channel = bot.guild.channels[TEST_CHANNEL]
    before = len(channel.deleted_messages)
    real = modmail_cog.refresh_card
    interrupted = []

    async def bumps_while_posting(client, guild, ticket_id):
        if not interrupted:
            await modmail_cog.bump_card(client, guild, await get_ticket(db, ticket_id))
            interrupted.append(sorted(modmail_cog.card_clock(client)["dirty"]))
        return await real(client, guild, ticket_id)

    monkeypatch.setattr(modmail_cog, "refresh_card", bumps_while_posting)

    await modmail_cog.bump_card(bot, bot.guild, ticket)
    await modmail_cog.settle_cards(bot)

    assert interrupted == [[ticket["id"]]]
    assert len(channel.deleted_messages) == before + 2
    assert len(cards_in(channel)) == 1
    assert channel.messages[-1] is cards_in(channel)[0]
    assert (await get_ticket(db, ticket["id"]))["card_message_id"] == channel.messages[-1].id
    assert modmail_cog.card_clock(bot)["dirty"] == set()
    assert modmail_cog.card_clock(bot)["tasks"] == {}


def test_the_card_clock_holds_a_ticket_to_its_floor_between_two_posts():
    clock = {"tasks": {}, "last": {}}

    assert modmail_cog.card_wait(clock, 1, 100.0) == modmail_cog.CARD_DEBOUNCE_SECONDS
    clock["last"][1] = 100.0
    assert modmail_cog.card_wait(clock, 1, 101.0) == modmail_cog.CARD_MIN_GAP_SECONDS - 1.0
    assert modmail_cog.card_wait(clock, 1, 140.0) == modmail_cog.CARD_DEBOUNCE_SECONDS


async def test_the_reconciler_gives_an_open_ticket_a_card_after_a_restart(cog, bot, member, db):
    ticket = await open_one(cog, bot, member)
    assert (await get_ticket(db, ticket["id"]))["card_message_id"] is None

    await cog.reconcile_tickets()

    card_id = (await get_ticket(db, ticket["id"]))["card_message_id"]
    assert card_id is not None
    channel = bot.guild.channels[TEST_CHANNEL]
    assert [one.id for one in cards_in(channel)] == [card_id]


async def test_the_reconciler_replaces_a_card_a_staffer_deleted_by_hand(cog, bot, member, db):
    ticket = await open_one(cog, bot, member)
    first = await card_for(cog, bot, ticket)
    channel = bot.guild.channels[TEST_CHANNEL]
    channel.messages.remove(first)

    await cog.reconcile_tickets()

    fresh = (await get_ticket(db, ticket["id"]))["card_message_id"]
    assert fresh is not None and fresh != first.id


async def test_the_reconciler_leaves_a_card_that_is_still_there_alone(cog, bot, member, db):
    ticket = await open_one(cog, bot, member)
    first = await card_for(cog, bot, ticket)

    await cog.reconcile_tickets()

    assert (await get_ticket(db, ticket["id"]))["card_message_id"] == first.id
    assert len(cards_in(bot.guild.channels[TEST_CHANNEL])) == 1


async def test_closing_a_ticket_takes_its_card_with_it(cog, bot, member, lead, db):
    await live(bot)
    await cog.on_message(dm_from(member))
    ticket = await open_ticket_for(db, GUILD, member.id)
    await bot.store.set(GUILD, "modmail_mode", THREAD_MODE)
    channel = bot.guild.get_channel(ticket["channel_id"])
    first = await card_for(cog, bot, ticket)

    await close_from_card(cog, bot, lead, ticket, reason="done", card=first)

    assert first.id in channel.deleted_messages
    assert (await get_ticket(db, ticket["id"]))["card_message_id"] is None


async def test_the_card_reply_button_sends_what_the_modal_carries(cog, bot, member, lead, db):
    ticket = await open_one(cog, bot, member)
    lead.roles = [FakeRole(STAFF_ROLE)]
    card = await card_for(cog, bot, ticket)

    opened = await press_card(bot, lead, card, "Reply")
    modal = opened.response.modals[-1]
    modal.text._value = "we are on it"
    sent = FakeInteraction(bot, lead)
    await modal.on_submit(sent)

    assert member.dms[-1]["embed"].description == "we are on it"
    assert "Sent to the member" in sent.sent
    rows = await ticket_messages(db, ticket["id"])
    assert rows[-1]["direction"] == OUT and rows[-1]["anonymous"] == 0
    kinds = await action_kinds(db)
    assert kinds.count("modmail.reply") == 1


async def test_the_cards_reply_modal_combines_the_snippet_and_the_typed_text(
    cog, bot, member, lead, db
):
    """F-M7 (a): byte-identical to `/reply text: snippet:` — the snippet first, then the words."""
    ticket = await open_one(cog, bot, member)
    lead.roles = [FakeRole(STAFF_ROLE)]
    await modmail_cog.put_snippet(bot, bot.guild, lead, "appeal", "Appeals go to a Lead.")
    card = await card_for(cog, bot, ticket)

    opened = await press_card(bot, lead, card, "Reply")
    modal = opened.response.modals[-1]
    modal.text._value = "and here is why"
    choose_snippet(modal.picker, "appeal")
    await modal.on_submit(FakeInteraction(bot, lead))

    assert member.dms[-1]["embed"].description == "Appeals go to a Lead.\n\nand here is why"


async def test_an_empty_card_reply_sends_nothing(cog, bot, member, lead):
    ticket = await open_one(cog, bot, member)
    lead.roles = [FakeRole(STAFF_ROLE)]
    card = await card_for(cog, bot, ticket)
    before = len(member.dms)

    opened = await press_card(bot, lead, card, "Reply")
    modal = opened.response.modals[-1]
    modal.text._value = ""
    sent = FakeInteraction(bot, lead)
    await modal.on_submit(sent)

    assert "nothing was sent" in sent.sent
    assert len(member.dms) == before


async def test_the_card_note_is_one_row_one_log_line_and_no_dm(cog, bot, member, lead, db):
    ticket = await open_one(cog, bot, member)
    lead.roles = [FakeRole(STAFF_ROLE)]
    card = await card_for(cog, bot, ticket)
    before = len(member.dms)

    opened = await press_card(bot, lead, card, "Private note")
    modal = opened.response.modals[-1]
    modal.note._value = "prior warnings"
    noted = FakeInteraction(bot, lead)
    await modal.on_submit(noted)

    rows = await ticket_messages(db, ticket["id"])
    assert rows[-1]["direction"] == NOTE and rows[-1]["content"] == "prior warnings"
    assert len(member.dms) == before
    assert (await action_kinds(db)).count("modmail.note") == 1
    assert "never sees it" in noted.sent


async def test_the_card_close_button_closes_quietly_when_the_box_is_ticked(
    cog, bot, member, lead, db
):
    ticket = await open_one(cog, bot, member)
    lead.roles = [FakeRole(STAFF_ROLE)]
    card = await card_for(cog, bot, ticket)
    before = len(member.dms)

    opened = await press_card(bot, lead, card, "Close…")
    modal = opened.response.modals[-1]
    modal.reason._value = "sorted"
    modal.quiet._values = ["silent"]
    closed = FakeInteraction(bot, lead)
    await modal.on_submit(closed)

    assert (await get_ticket(db, ticket["id"]))["status"] == "closed"
    assert len(member.dms) == before
    assert "not told" in closed.sent
    assert (await action_kinds(db)).count("modmail.closed") == 1


async def test_a_demoted_staffer_moves_nothing_from_the_card(cog, bot, member, lead, db):
    ticket = await open_one(cog, bot, member)
    card = await card_for(cog, bot, ticket)
    lead.roles = []
    lead.guild_permissions = FakePerms()

    refused_at = await press_card(bot, lead, card, "Reply")

    assert refused_at.response.modals == []
    assert refused_at.sent is not None
    assert (await get_ticket(db, ticket["id"]))["status"] == "open"


async def test_a_card_whose_ticket_has_closed_says_so_rather_than_dying(cog, bot, member, lead, db):
    ticket = await open_one(cog, bot, member)
    lead.roles = [FakeRole(STAFF_ROLE)]
    card = await card_for(cog, bot, ticket)
    await modmail_cog.close_ticket(bot, bot.guild, ticket, by=lead)

    pressed = await press_card(bot, lead, card, "Reply")

    assert pressed.response.modals == []
    assert "already closed" in pressed.sent


# --- the ticket card ON the panel ----------------------------------------------------------------


PANEL_CARD_LABELS = [*CARD_LABELS, "Back"]


async def ticket_card_panel(cog, bot, lead, ticket):
    root = await open_panel(cog, bot, lead)
    return await choose(
        root.view, modmail_cog.PICK_A_TICKET, [str(ticket["id"])], bot, lead
    )


async def card_modal_on(panel, label, bot, lead):
    opened = await press(panel.view, label, bot, lead)
    return opened.response.modals[-1]


async def test_a_ticket_select_is_drawn_only_once_something_is_open(cog, bot, member, lead):
    empty = await open_panel(cog, bot, lead)
    assert modmail_cog.PICK_A_TICKET not in placeholders(empty.view)

    ticket = await open_one(cog, bot, member)
    listed = await open_panel(cog, bot, lead)

    picker = control(listed.view, modmail_cog.PICK_A_TICKET)
    assert picker.row == 0
    assert [one.value for one in picker.options] == [str(ticket["id"])]
    assert picker.options[0].label == f"#{ticket['id']} · channel · Alice"


async def test_the_ticket_select_stops_at_the_cap_and_says_where_the_rest_are(
    cog, bot, lead, db
):
    for user_id in range(600, 626):
        await modmail_cog.create_ticket(db, GUILD, user_id, CHANNEL_MODE)

    root = await open_panel(cog, bot, lead)

    picker = next(one for one in root.view.children if getattr(one, "options", None))
    assert len(picker.options) == 25
    assert "25 of 26" in picker.placeholder
    assert modmail_cog.PICK_A_TICKET not in picker.placeholder


async def test_picking_a_ticket_draws_the_card_the_channel_carries(cog, bot, member, lead, db):
    """One embed shape, never two: the panel's copy is `ticket_card_embed`, as the sticky is."""
    ticket = await open_one(cog, bot, member)
    sticky = await card_for(cog, bot, ticket)

    panel = await ticket_card_panel(cog, bot, lead, ticket)

    assert labels(panel.view) == PANEL_CARD_LABELS
    assert panel.embed.title == sticky.kwargs["embed"].title == f"Ticket #{ticket['id']}"
    assert panel.embed.description == sticky.kwargs["embed"].description
    assert panel.view.picked_ticket == ticket["id"]
    assert panel.response.messages[0].get("deferred") is True


async def test_back_from_the_ticket_card_is_the_inbox_again(cog, bot, member, lead):
    ticket = await open_one(cog, bot, member)
    panel = await ticket_card_panel(cog, bot, lead, ticket)

    root = await press(panel.view, "Back", bot, lead)

    assert root.embed.title == modmail_cog.PANEL_TITLE
    assert modmail_cog.PICK_A_TICKET in placeholders(root.view)


async def test_the_panels_reply_sends_through_the_same_function_the_card_calls(
    cog, bot, member, lead, db
):
    ticket = await open_one(cog, bot, member)
    panel = await ticket_card_panel(cog, bot, lead, ticket)

    modal = await card_modal_on(panel, "Reply", bot, lead)
    modal.text._value = "we are on it"
    sent = FakeInteraction(bot, lead)
    await modal.on_submit(sent)

    assert member.dms[-1]["embed"].description == "we are on it"
    assert "Sent to the member" in sent.sent
    rows = await ticket_messages(db, ticket["id"])
    assert rows[-1]["direction"] == OUT and rows[-1]["anonymous"] == 0
    assert (await action_kinds(db)).count("modmail.reply") == 1
    assert labels(sent.view) == PANEL_CARD_LABELS


async def test_the_panels_anonymous_reply_never_names_the_staffer(cog, bot, member, lead):
    ticket = await open_one(cog, bot, member)
    panel = await ticket_card_panel(cog, bot, lead, ticket)

    modal = await card_modal_on(panel, "Reply as Staff", bot, lead)
    modal.text._value = "no names"
    sent = FakeInteraction(bot, lead)
    await modal.on_submit(sent)

    assert member.dms[-1]["embed"].author.name == "Staff"
    assert "Staff" in sent.sent


async def test_the_panels_private_note_is_one_row_one_log_line_and_no_dm(
    cog, bot, member, lead, db
):
    ticket = await open_one(cog, bot, member)
    panel = await ticket_card_panel(cog, bot, lead, ticket)
    before = len(member.dms)

    modal = await card_modal_on(panel, "Private note", bot, lead)
    modal.note._value = "prior warnings"
    noted = FakeInteraction(bot, lead)
    await modal.on_submit(noted)

    rows = await ticket_messages(db, ticket["id"])
    assert rows[-1]["direction"] == NOTE and rows[-1]["content"] == "prior warnings"
    assert len(member.dms) == before
    assert (await action_kinds(db)).count("modmail.note") == 1
    assert "never sees it" in noted.sent


async def test_closing_from_the_panel_leaves_a_card_that_offers_only_back(
    cog, bot, member, lead, db
):
    ticket = await open_one(cog, bot, member)
    panel = await ticket_card_panel(cog, bot, lead, ticket)

    modal = await card_modal_on(panel, "Close…", bot, lead)
    modal.reason._value = "sorted"
    closed = FakeInteraction(bot, lead)
    await modal.on_submit(closed)

    assert (await get_ticket(db, ticket["id"]))["status"] == "closed"
    assert "is closed" in closed.sent
    assert labels(closed.view) == ["Back"]
    assert closed.embed.footer.text == modmail_cog.CARD_CLOSED_FOOTER
    assert (await action_kinds(db)).count("modmail.closed") == 1


async def test_a_close_somebody_else_won_says_the_ticket_was_raced(
    cog, bot, member, lead, db, monkeypatch
):
    ticket = await open_one(cog, bot, member)
    panel = await ticket_card_panel(cog, bot, lead, ticket)
    modal = await card_modal_on(panel, "Close…", bot, lead)

    async def lost(*_args, **_kwargs):
        return False, None

    monkeypatch.setattr(modmail_cog, "close_ticket", lost)
    raced = FakeInteraction(bot, lead)
    await modal.on_submit(raced)

    assert "closed by somebody else" in raced.sent
    assert (await get_ticket(db, ticket["id"]))["status"] == "open"


async def test_a_ticket_closed_under_the_panel_says_so_rather_than_opening_a_modal(
    cog, bot, member, lead, db
):
    ticket = await open_one(cog, bot, member)
    panel = await ticket_card_panel(cog, bot, lead, ticket)
    await modmail_cog.close_ticket(bot, bot.guild, ticket, by=lead)

    pressed = await press(panel.view, "Reply", bot, lead)

    assert pressed.response.modals == []
    assert "already closed" in pressed.sent


async def test_a_demoted_staffer_moves_nothing_from_the_panels_ticket_card(
    cog, bot, member, lead, db
):
    ticket = await open_one(cog, bot, member)
    panel = await ticket_card_panel(cog, bot, lead, ticket)
    lead.roles = []
    lead.guild_permissions = FakePerms()

    refused_at = await press(panel.view, "Close…", bot, lead)

    assert refused_at.response.modals == [] and refused_at.edits == []
    assert refused_at.sent is not None
    assert (await get_ticket(db, ticket["id"]))["status"] == "open"


async def test_the_panels_card_retires_the_view_it_replaced(cog, bot, member, lead):
    ticket = await open_one(cog, bot, member)
    root = await open_panel(cog, bot, lead)
    first = root.view

    await choose(first, modmail_cog.PICK_A_TICKET, [str(ticket["id"])], bot, lead)

    assert first.replaced is True and first.is_finished()


async def test_a_ticket_that_has_gone_falls_back_to_the_inbox_in_words(cog, bot, member, lead):
    await open_one(cog, bot, member)
    root = await open_panel(cog, bot, lead)

    picked = await choose(root.view, modmail_cog.PICK_A_TICKET, ["4242"], bot, lead)

    assert picked.embed.title == modmail_cog.PANEL_TITLE
    assert "no record of ticket #4242" in picked.sent


# --- the relay gate ----------------------------------------------------------------------------


async def typed_in_ticket(cog, bot, lead, ticket, text):
    channel = bot.guild.get_channel(ticket["channel_id"])
    lead.roles = [FakeRole(STAFF_ROLE)]
    message = guild_message(channel, lead, text)
    await cog.on_message(message)
    return message


@pytest.mark.parametrize("style", ["typing", "both"])
async def test_a_typed_message_still_relays_under_typing_and_both(
    cog, bot, member, lead, db, style
):
    ticket = await open_one(cog, bot, member)
    await bot.store.set(GUILD, "modmail_reply_style", style)
    before = len(member.dms)

    await typed_in_ticket(cog, bot, lead, ticket, "we are looking into it")

    assert len(member.dms) == before + 1
    assert member.dms[-1]["embed"].description == "we are looking into it"
    assert (await ticket_messages(db, ticket["id"]))[-1]["direction"] == OUT


async def test_buttons_stops_the_typed_relay_dead(cog, bot, member, lead, db):
    """The one thing `modmail_reply_style` is for: a ticket channel staff can talk in."""
    ticket = await open_one(cog, bot, member)
    await bot.store.set(GUILD, "modmail_reply_style", "buttons")
    before = len(member.dms)

    message = await typed_in_ticket(cog, bot, lead, ticket, "we are looking into it")

    assert len(member.dms) == before
    assert message.reactions == []
    assert [row["direction"] for row in await ticket_messages(db, ticket["id"])] == [IN]
    assert "modmail.reply" not in await action_kinds(db)


@pytest.mark.parametrize("style", ["buttons", "typing", "both"])
async def test_an_equals_note_is_a_note_in_every_style(cog, bot, member, lead, db, style):
    """Guard lifted, so the reactions are visible: 📝 for the note whatever the style is."""
    await live(bot)
    await cog.on_message(dm_from(member))
    ticket = await open_ticket_for(db, GUILD, member.id)
    await bot.store.set(GUILD, "modmail_reply_style", style)
    before = len(member.dms)

    message = await typed_in_ticket(cog, bot, lead, ticket, "= watch this one")

    rows = await ticket_messages(db, ticket["id"])
    assert rows[-1]["direction"] == NOTE and rows[-1]["content"] == "watch this one"
    assert message.reactions == ["\N{MEMO}"]
    assert len(member.dms) == before
    assert (await action_kinds(db)).count("modmail.note") == 1


async def test_the_card_and_the_command_both_work_while_buttons_is_on(
    cog, bot, member, lead, db
):
    ticket = await open_one(cog, bot, member)
    await bot.store.set(GUILD, "modmail_reply_style", "buttons")
    lead.roles = [FakeRole(STAFF_ROLE)]

    await cog.reply.callback(cog, FakeInteraction(bot, lead), text="typed door")
    card = await card_for(cog, bot, ticket)
    opened = await press_card(bot, lead, card, "Reply")
    modal = opened.response.modals[-1]
    modal.text._value = "button door"
    await modal.on_submit(FakeInteraction(bot, lead))

    said = [one["embed"].description for one in member.dms if one.get("embed")]
    assert said[-2:] == ["typed door", "button door"]


async def test_the_reply_style_is_set_from_the_setup_panel_and_says_what_changed(
    cog, bot, lead, db
):
    root = await open_panel(cog, bot, lead)
    setup = await press(root.view, "Setup…", bot, lead)
    picker = await press(setup.view, "Reply style…", bot, lead)

    chosen = await choose(picker.view, modmail_cog.PICK_A_REPLY_STYLE, ["buttons"], bot, lead)

    assert bot.store.get(GUILD, "modmail_reply_style") == "buttons"
    assert "buttons" in chosen.sent
    assert (await action_kinds(db)).count("modmail.settings") == 1
    assert "**reply style** — buttons" in chosen.embed.description


# --- the practice ticket -------------------------------------------------------------------------


async def practise(cog, bot, lead):
    bot.guard = bot.guard or FakeGuard()
    lead.roles = [FakeRole(STAFF_ROLE)]
    return await modmail_cog.open_practice(bot, bot.guild, lead)


async def practice_ticket(bot, outcome):
    return await get_ticket(bot.db, outcome.value)


async def test_a_practice_ticket_is_a_claimed_private_thread_on_the_test_channel(
    cog, bot, lead, db
):
    outcome = await practise(cog, bot, lead)

    assert outcome.ok
    ticket = await practice_ticket(bot, outcome)
    assert ticket["practice"] == 1 and ticket["user_id"] == lead.id
    thread = bot.guild.threads[ticket["thread_id"]]
    assert thread.parent_id == TEST_CHANNEL
    assert thread.kwargs["type"] is discord.ChannelType.private_thread
    assert bot.guard.owns_channel(thread)
    titles = [one.kwargs["embed"].title for one in thread.messages]
    assert titles == [f"Ticket #{ticket['id']}", f"Practice ticket #{ticket['id']}"]
    assert thread.messages[-1].kwargs.get("view") is not None


async def test_the_practice_card_carries_the_two_extra_moves(cog, bot, lead):
    outcome = await practise(cog, bot, lead)
    ticket = await practice_ticket(bot, outcome)
    thread = bot.guild.threads[ticket["thread_id"]]

    labels_on = [one.item.label for one in thread.messages[-1].kwargs["view"].children]

    assert labels_on == [*CARD_LABELS, "Speak as the member", "End the practice"]


async def test_speaking_as_the_member_writes_an_inbound_row_and_moves_the_card(
    cog, bot, lead, db
):
    outcome = await practise(cog, bot, lead)
    ticket = await practice_ticket(bot, outcome)
    thread = bot.guild.threads[ticket["thread_id"]]
    first = thread.messages[-1]

    opened = await press_card(bot, lead, first, "Speak as the member", channel=thread)
    modal = opened.response.modals[-1]
    modal.text._value = "hello?"
    said = FakeInteraction(bot, lead, channel=thread)
    await modal.on_submit(said)
    modmail_cog.cancel_cards(bot)
    await modmail_cog.refresh_card(bot, bot.guild, ticket["id"])

    rows = await ticket_messages(db, ticket["id"])
    assert [row["direction"] for row in rows] == [IN]
    assert rows[0]["author_id"] == lead.id
    assert first.id in thread.deleted_messages
    assert len(cards_in(thread)) == 1
    assert thread.messages[-1] is cards_in(thread)[0]


async def test_a_practice_reply_never_dms_anybody_and_never_says_a_dm_failed(
    cog, bot, lead, db
):
    """Checklist 2 and 10: a suppressed DM is not a failed one, and neither is a claimed check."""
    outcome = await practise(cog, bot, lead)
    ticket = await practice_ticket(bot, outcome)
    thread = bot.guild.threads[ticket["thread_id"]]
    before = len(lead.dms)

    card = thread.messages[-1]
    opened = await press_card(bot, lead, card, "Reply", channel=thread)
    modal = opened.response.modals[-1]
    modal.text._value = "we are on it"
    sent = FakeInteraction(bot, lead, channel=thread)
    await modal.on_submit(sent)

    assert len(lead.dms) == before
    kinds = await action_kinds(db)
    assert "modmail.dm_failed" not in kinds
    assert kinds.count("modmail.reply") == 1
    assert (await ticket_messages(db, ticket["id"]))[-1]["delivered"] == 1
    assert "Sent to the member" in sent.sent


async def test_ending_the_practice_files_a_transcript_marked_practice_and_disowns_the_thread(
    cog, bot, lead, db
):
    outcome = await practise(cog, bot, lead)
    ticket = await practice_ticket(bot, outcome)
    thread = bot.guild.threads[ticket["thread_id"]]
    before = len(lead.dms)

    ended = await press_card(bot, lead, thread.messages[-1], "End the practice", channel=thread)

    assert (await get_ticket(db, ticket["id"]))["status"] == "closed"
    assert "PRACTICE" in ended.sent
    assert len(lead.dms) == before
    assert thread.archived and thread.locked
    assert not bot.guard.owns_channel(thread)
    filed = [
        one for one in bot.guild.channels[TEST_CHANNEL].messages if one.kwargs.get("file")
    ]
    assert len(filed) == 1
    assert filed[0].kwargs["embed"].title == f"Practice ticket #{ticket['id']} closed"
    assert filed[0].kwargs["file"].filename == f"modmail-practice-ticket-{ticket['id']}.txt"
    assert "modmail.transcript" in await action_kinds(db)


async def test_a_staffer_with_a_real_open_ticket_is_refused_in_words(cog, bot, lead, db):
    bot.guard = FakeGuard()
    bot.users[lead.id] = lead
    await cog.on_message(dm_from(lead))
    assert await open_ticket_for(db, GUILD, lead.id) is not None

    outcome = await practise(cog, bot, lead)

    assert not outcome.ok and "already have a modmail ticket" in outcome.message
    cur = await db.conn.execute("SELECT COUNT(*) AS n FROM modmail_tickets WHERE practice = 1")
    assert (await cur.fetchone())["n"] == 0


async def test_practice_is_refused_when_no_staff_role_resolves(cog, bot, lead):
    bot.guard = FakeGuard()
    bot.guild.roles = []

    outcome = await modmail_cog.open_practice(bot, bot.guild, lead)

    assert not outcome.ok and "No staff role" in outcome.message
    assert bot.guild.threads == {}


async def test_the_panel_asks_before_it_opens_a_practice_ticket(cog, bot, lead, db):
    root = await open_panel(cog, bot, lead)
    assert has(root.view, "Try a fake ticket")

    asked = await press(root.view, "Try a fake ticket", bot, lead)

    assert labels(asked.view) == ["Yes, open one", "No"]
    assert "fake ticket" in asked.embed.description
    cur = await db.conn.execute("SELECT COUNT(*) AS n FROM modmail_tickets")
    assert (await cur.fetchone())["n"] == 0

    made = await press(asked.view, "Yes, open one", bot, lead)

    assert "Practice ticket #1 is open" in made.sent
    assert (await get_ticket(db, 1))["practice"] == 1
    assert has(made.view, "Try a fake ticket")


async def test_saying_no_to_the_practice_confirm_opens_nothing(cog, bot, lead, db):
    root = await open_panel(cog, bot, lead)
    asked = await press(root.view, "Try a fake ticket", bot, lead)

    kept = await press(asked.view, "No", bot, lead)

    cur = await db.conn.execute("SELECT COUNT(*) AS n FROM modmail_tickets")
    assert (await cur.fetchone())["n"] == 0
    assert has(kept.view, "Try a fake ticket")


async def test_the_practice_button_is_absent_when_no_staff_role_resolves(cog, bot, lead):
    bot.guild.roles = []

    root = await open_panel(cog, bot, lead)

    assert not has(root.view, "Try a fake ticket")
    assert "No staff roles" in root.embed.description


async def test_speaking_for_a_real_member_is_refused(cog, bot, member, lead, db):
    ticket = await open_one(cog, bot, member)

    outcome = await modmail_cog.practice_message(bot, bot.guild, ticket, lead, "hello")

    assert not outcome.ok and "real ticket" in outcome.message
    assert len(await ticket_messages(db, ticket["id"])) == 1


async def test_a_stored_message_keeps_its_direction_and_anonymity(db):
    await db.conn.execute(
        "INSERT INTO modmail_tickets(guild_id, user_id, mode, channel_id, status, opened_at) "
        "VALUES (7, 900, 'channel', 5, 'open', '2026-08-26T00:00:00+00:00')"
    )
    await db.conn.commit()

    await add_message(db, 1, 1, OUT, content="hi", anonymous=True)

    row = (await ticket_messages(db, 1))[0]
    assert row["anonymous"] == 1 and row["direction"] == OUT
