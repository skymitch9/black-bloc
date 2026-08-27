import asyncio
import re

import discord
import pytest

from black_bloc.cogs.moderation.honeypot import (
    BAN_TEMPLATE,
    TRAP_NAME,
    BanNowButton,
    Honeypot,
    ban_custom_id,
    banned_already,
    exempt_reason,
    get_hit,
    hit_counts,
    offer_text,
    record_hit,
    set_hit_action,
    trimmed,
)
from black_bloc.config import load_settings
from black_bloc.settings_store import SettingsStore
from black_bloc.storage.db import Database

GUILD = 7
TEST_CHANNEL = 111
LOG_CHANNEL = 222
TRAP = 333
STAFF_ROLE = 555
EXEMPT_ROLE = 666
USER = 900
BOT_ID = 42


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


class FakeMessage:
    def __init__(self, message_id, content, **kwargs):
        self.id = message_id
        self.content = content
        self.kwargs = kwargs
        self.pinned = False

    async def pin(self, reason=None):
        self.pinned = True


class FakeCategory:
    def __init__(self, category_id):
        self.id = category_id
        self.name = f"category-{category_id}"


class FakeChannel:
    def __init__(
        self, channel_id, name="channel", category=None, overwrites=None, parent_id=None
    ):
        self.id = channel_id
        self.name = name
        self.mention = f"<#{channel_id}>"
        self.category = category
        self.category_id = category.id if category else None
        self.parent_id = parent_id
        self.overwrites = overwrites or {}
        self.visible_to = set()
        self.messages = []
        self.send_raises = None

    def permissions_for(self, role):
        return FakePerms(view_channel=role.id in self.visible_to)

    async def send(self, content=None, **kwargs):
        if self.send_raises is not None:
            raise self.send_raises
        message = FakeMessage(len(self.messages) + 1, content or "", **kwargs)
        self.messages.append(message)
        return message


class FakeGuild:
    def __init__(self):
        self.id = GUILD
        self.name = "Black Bloc"
        self.channels = {}
        self.members = {}
        self.default_role = FakeRole(GUILD)
        self.roles = []
        self.bans = []
        self.created = []
        self._next_id = 1000

    def add(self, channel):
        channel.guild = self
        self.channels[channel.id] = channel
        return channel

    def get_channel(self, channel_id):
        return self.channels.get(channel_id)

    def get_member(self, user_id):
        return self.members.get(user_id)

    @property
    def text_channels(self):
        return list(self.channels.values())

    async def ban(self, user, reason=None, delete_message_seconds=None):
        self.bans.append((user.id, reason, delete_message_seconds))

    async def create_text_channel(
        self, name, *, category=None, position=0, overwrites=None, slowmode_delay=0, reason=None
    ):
        self._next_id += 1
        channel = FakeChannel(self._next_id, name=name, category=category, overwrites=overwrites)
        channel.guild = self
        channel.position = position
        channel.slowmode_delay = slowmode_delay
        self.add(channel)
        self.created.append(channel)
        return channel


class FakeMember:
    def __init__(
        self, guild, user_id=USER, display_name="Spam", roles=(), manage_guild=False, bot=False
    ):
        self.id = user_id
        self.guild = guild
        self.display_name = display_name
        self.name = display_name
        self.bot = bot
        self.mention = f"<@{user_id}>"
        self.roles = [FakeRole(r) for r in roles]
        self.guild_permissions = FakePerms(manage_guild=manage_guild)
        self.dms = []
        self.dm_raises = None
        guild.members[user_id] = self

    async def send(self, content=None, **kwargs):
        if self.dm_raises is not None:
            raise self.dm_raises
        self.dms.append(content)


class FakePost:
    def __init__(self, guild, author, channel, content="buy coins", message_id=5):
        self.guild = guild
        self.author = author
        self.channel = channel
        self.content = content
        self.id = message_id
        self.type = discord.MessageType.default
        self.webhook_id = None
        self.deleted = False
        self.delete_raises = None

    async def delete(self):
        if self.delete_raises is not None:
            raise self.delete_raises
        self.deleted = True


class FakeGuard:
    def __init__(self, test_channel_id=TEST_CHANNEL):
        self.test_channel_id = test_channel_id

    def allows_channel(self, channel_id):
        return channel_id == self.test_channel_id

    def refusal_message(self):
        return "test mode"


class FakeUser:
    def __init__(self, user_id=BOT_ID):
        self.id = user_id


class FakeBot:
    def __init__(self, db, store, settings, guild):
        self.db = db
        self.store = store
        self.settings = settings
        self.guard = None
        self.guilds = [guild]
        self.guild = guild
        self.user = FakeUser()
        self.dynamic = []

    def get_channel(self, channel_id):
        return self.guild.get_channel(channel_id)

    def add_dynamic_items(self, *items):
        self.dynamic += list(items)


class FakeResponse:
    def __init__(self):
        self.messages = []

    async def send_message(self, content=None, ephemeral=False, **kwargs):
        self.messages.append({"content": content, "ephemeral": ephemeral, **kwargs})

    async def defer(self, ephemeral=False):
        self.messages.append({"content": None, "deferred": True})


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


async def action_kinds(db):
    cur = await db.conn.execute("SELECT kind FROM action_log ORDER BY id")
    return [row["kind"] for row in await cur.fetchall()]


def ban_buttons(bot):
    log_channel = bot.guild.get_channel(LOG_CHANNEL)
    return [m for m in log_channel.messages if "view" in m.kwargs]


async def hits(db):
    cur = await db.conn.execute("SELECT * FROM honeypot_hits ORDER BY id")
    return list(await cur.fetchall())


@pytest.fixture
async def db(tmp_path):
    database = Database(tmp_path / "h.sqlite3")
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
    await store.set(GUILD, "honeypot_channel_ids", [TRAP])
    guild = FakeGuild()
    category = FakeCategory(50)
    guild.add(FakeChannel(TEST_CHANNEL, name="test", category=category))
    guild.add(FakeChannel(LOG_CHANNEL, name="log"))
    guild.add(FakeChannel(TRAP, name="do-not-post-here", category=category))
    return FakeBot(db, store, settings, guild)


@pytest.fixture
def cog(bot):
    return Honeypot(bot)


def give_staff(bot, role_id=STAFF_ROLE):
    role = FakeRole(role_id)
    bot.guild.roles.append(role)
    bot.guild.get_channel(TEST_CHANNEL).visible_to.add(role_id)
    return role


@pytest.fixture
def spammer(bot):
    return FakeMember(bot.guild)


@pytest.fixture
def lead(bot):
    return FakeMember(bot.guild, user_id=1, display_name="Lead", manage_guild=True)


@pytest.fixture
def post(bot, spammer):
    return FakePost(bot.guild, spammer, bot.guild.get_channel(TRAP))


def test_the_exemption_matrix():
    guild = FakeGuild()
    staff = {STAFF_ROLE}
    exempt = {EXEMPT_ROLE}
    assert exempt_reason(FakeMember(guild, bot=True), staff, exempt) == "bot"
    assert exempt_reason(FakeMember(guild, manage_guild=True), staff, exempt) == "manage_guild"
    assert exempt_reason(FakeMember(guild, roles=(STAFF_ROLE,)), staff, exempt) == "staff"
    assert exempt_reason(FakeMember(guild, roles=(EXEMPT_ROLE,)), staff, exempt) == "exempt_role"
    assert exempt_reason(FakeMember(guild, roles=(999,)), staff, exempt) is None
    assert exempt_reason(FakeMember(guild), set(), set()) is None


def test_content_is_trimmed_for_the_log():
    assert trimmed("a" * 900) == "a" * 500
    assert trimmed(None) == ""


def test_the_ban_button_custom_id_matches_its_template():
    assert ban_custom_id(12) == "honeypot:ban:12"
    match = re.fullmatch(BAN_TEMPLATE, ban_custom_id(12))
    assert match is not None and int(match["hit_id"]) == 12
    assert re.fullmatch(BAN_TEMPLATE, "honeypot:ban:abc") is None
    assert BanNowButton(12).item.custom_id == "honeypot:ban:12"


def test_the_offer_never_pings_and_shows_the_post():
    assert "<@900>" in offer_text(900, "buy coins")
    assert "buy coins" in offer_text(900, "buy coins")
    assert "(no text)" in offer_text(900, "")


async def test_hits_round_trip(db):
    hit_id = await record_hit(db, GUILD, USER, TRAP, 5, "buy coins", "shadow", "would_ban")
    row = await get_hit(db, hit_id)
    assert row["user_id"] == USER and row["action"] == "would_ban" and row["mode"] == "shadow"
    assert await banned_already(db, GUILD, USER) is False
    await set_hit_action(db, hit_id, "banned")
    assert (await get_hit(db, hit_id))["action"] == "banned"
    assert await banned_already(db, GUILD, USER) is True
    assert await hit_counts(db, GUILD) == {"banned": 1}


async def test_shadow_deletes_the_post_logs_it_and_offers_the_ban(cog, bot, post, db):
    await cog.on_message(post)

    assert post.deleted is True
    assert bot.guild.bans == []
    assert [h["action"] for h in await hits(db)] == ["would_ban"]
    assert "honeypot.would_ban" in await action_kinds(db)
    offered = bot.guild.get_channel(LOG_CHANNEL).messages[-1]
    assert "buy coins" in offered.content
    assert offered.kwargs["view"].children[0].custom_id.startswith("honeypot:ban:")


async def test_off_mode_touches_nothing(cog, bot, post, db):
    await bot.store.set(GUILD, "honeypot_mode", "off")

    await cog.on_message(post)

    assert post.deleted is False and await hits(db) == [] and await action_kinds(db) == []


async def test_on_mode_dms_then_bans_and_deletes_first(cog, bot, post, spammer, db):
    await bot.store.set(GUILD, "honeypot_mode", "on")
    bot.guard = None

    await cog.on_message(post)

    assert post.deleted is True
    assert bot.guild.bans == [(spammer.id, "Honeypot: posted in #do-not-post-here", 86400)]
    assert spammer.dms and "banned from **Black Bloc**" in spammer.dms[0]
    assert [h["action"] for h in await hits(db)] == ["banned"]
    assert "honeypot.banned" in await action_kinds(db)


async def test_a_ban_is_refused_in_test_mode_and_logged_as_would_ban(cog, bot, post, db):
    await bot.store.set(GUILD, "honeypot_mode", "on")
    bot.guard = FakeGuard()

    await cog.on_message(post)

    assert post.deleted is True and bot.guild.bans == []
    assert [h["action"] for h in await hits(db)] == ["would_ban"]
    kinds = await action_kinds(db)
    assert "honeypot.would_ban" in kinds and "honeypot.banned" not in kinds


async def test_a_ban_discord_refuses_is_never_confused_with_a_dry_run(cog, bot, post, db):
    await bot.store.set(GUILD, "honeypot_mode", "on")

    async def refusing_ban(user, reason=None, delete_message_seconds=None):
        raise refused()

    bot.guild.ban = refusing_ban

    await cog.on_message(post)

    assert [h["action"] for h in await hits(db)] == ["ban_failed"]
    kinds = await action_kinds(db)
    assert "honeypot.ban_failed" in kinds and "honeypot.would_ban" not in kinds


async def test_a_post_that_cannot_be_deleted_is_still_acted_on(cog, bot, post, db):
    post.delete_raises = refused()

    await cog.on_message(post)

    kinds = await action_kinds(db)
    assert "honeypot.delete_failed" in kinds and "honeypot.would_ban" in kinds


async def test_staff_and_bots_are_ignored_and_their_posts_are_left_alone(cog, bot, db):
    trap = bot.guild.get_channel(TRAP)
    a_bot = FakeMember(bot.guild, user_id=USER + 1, bot=True)

    await cog.on_message(FakePost(bot.guild, a_bot, trap))

    assert [h["action"] for h in await hits(db)] == ["exempt"]
    assert "honeypot.exempt" in await action_kinds(db)
    assert bot.guild.get_channel(LOG_CHANNEL).messages != []


async def test_an_exempt_role_is_ignored(cog, bot, db):
    await bot.store.set(GUILD, "honeypot_exempt_role_ids", [EXEMPT_ROLE])
    trap = bot.guild.get_channel(TRAP)
    friend = FakeMember(bot.guild, user_id=USER + 2, roles=(EXEMPT_ROLE,))
    post = FakePost(bot.guild, friend, trap)

    await cog.on_message(post)

    assert post.deleted is False
    assert [h["action"] for h in await hits(db)] == ["exempt"]


async def test_posts_outside_the_trap_are_ignored(cog, bot, spammer, db):
    elsewhere = bot.guild.add(FakeChannel(4242, name="general"))

    await cog.on_message(FakePost(bot.guild, spammer, elsewhere))

    assert await hits(db) == []


async def test_black_bloc_s_own_posts_and_webhooks_and_dms_are_ignored(cog, bot, db):
    trap = bot.guild.get_channel(TRAP)
    itself = FakeMember(bot.guild, user_id=BOT_ID, bot=True)
    await cog.on_message(FakePost(bot.guild, itself, trap))

    webhook_post = FakePost(bot.guild, FakeMember(bot.guild, user_id=USER + 3), trap)
    webhook_post.webhook_id = 99
    await cog.on_message(webhook_post)

    dm_post = FakePost(bot.guild, FakeMember(bot.guild, user_id=USER + 4), trap)
    dm_post.guild = None
    await cog.on_message(dm_post)

    assert await hits(db) == []


async def test_a_burst_from_one_account_bans_it_once(cog, bot, spammer, db):
    await bot.store.set(GUILD, "honeypot_mode", "on")
    trap = bot.guild.get_channel(TRAP)
    first = FakePost(bot.guild, spammer, trap, message_id=5)
    second = FakePost(bot.guild, spammer, trap, message_id=6)

    await asyncio.gather(cog.on_message(first), cog.on_message(second))

    assert len(bot.guild.bans) == 1
    assert [h["action"] for h in await hits(db)] == ["banned", "banned"]


async def test_the_ban_button_is_staff_only(cog, bot, spammer, db):
    hit_id = await record_hit(db, GUILD, USER, TRAP, 5, "buy coins", "shadow", "would_ban")
    interaction = FakeInteraction(bot, spammer)

    await BanNowButton(hit_id).callback(interaction)

    assert bot.guild.bans == []
    assert "staff only" in interaction.sent


async def test_the_ban_button_bans_the_account_it_names(cog, bot, lead, db):
    hit_id = await record_hit(db, GUILD, USER, TRAP, 5, "buy coins", "shadow", "would_ban")
    interaction = FakeInteraction(bot, lead)

    await BanNowButton(hit_id).callback(interaction)

    assert bot.guild.bans == [(USER, "Honeypot: posted in #do-not-post-here", 86400)]
    assert (await get_hit(db, hit_id))["action"] == "banned"
    assert "honeypot.banned" in await action_kinds(db)


async def test_the_ban_button_refuses_in_test_mode_with_a_sentence(cog, bot, lead, db):
    bot.guard = FakeGuard()
    hit_id = await record_hit(db, GUILD, USER, TRAP, 5, "buy coins", "shadow", "would_ban")
    interaction = FakeInteraction(bot, lead)

    await BanNowButton(hit_id).callback(interaction)

    assert bot.guild.bans == []
    assert "test mode" in interaction.sent
    assert (await get_hit(db, hit_id))["action"] == "would_ban"
    assert "honeypot.would_ban" in await action_kinds(db)


async def test_the_ban_button_says_so_when_the_account_is_already_banned(cog, bot, lead, db):
    hit_id = await record_hit(db, GUILD, USER, TRAP, 5, "buy coins", "shadow", "banned")
    interaction = FakeInteraction(bot, lead)

    await BanNowButton(hit_id).callback(interaction)

    assert bot.guild.bans == [] and "already banned" in interaction.sent


async def test_the_ban_button_says_so_when_the_hit_is_gone(cog, bot, lead, db):
    interaction = FakeInteraction(bot, lead)

    await BanNowButton(4242).callback(interaction)

    assert bot.guild.bans == [] and "no record" in interaction.sent


async def test_setup_makes_the_trap_in_the_test_category_and_skips_the_notice(cog, bot, lead):
    await bot.store.set(GUILD, "honeypot_channel_ids", [])
    category = bot.guild.get_channel(TEST_CHANNEL).category
    bot.guard = FakeGuard()
    interaction = FakeInteraction(bot, lead)

    await cog.setup_channel.callback(cog, interaction, None)

    made = bot.guild.created[0]
    assert made.name == TRAP_NAME and made.category is category
    everyone = made.overwrites[bot.guild.default_role]
    assert everyone.send_messages is True and everyone.view_channel is True
    assert everyone.create_public_threads is False and everyone.add_reactions is False
    assert everyone.send_messages_in_threads is False and everyone.attach_files is False
    assert made.messages == []
    assert bot.store.get(GUILD, "honeypot_channel_ids") == [made.id]
    assert "test mode" in interaction.sent


async def test_setup_posts_and_pins_the_notice_when_the_guard_is_off(cog, bot, lead):
    await bot.store.set(GUILD, "honeypot_channel_ids", [])
    interaction = FakeInteraction(bot, lead)

    await cog.setup_channel.callback(cog, interaction, None)

    made = bot.guild.created[0]
    assert made.messages[0].content.startswith("This channel is a trap for bots.")
    assert made.messages[0].pinned is True
    assert "pinned" in interaction.sent


async def test_setup_is_staff_only(cog, bot, spammer):
    interaction = FakeInteraction(bot, spammer)

    await cog.setup_channel.callback(cog, interaction, None)

    assert bot.guild.created == [] and "staff only" in interaction.sent


async def test_exempt_roles_are_added_and_removed(cog, bot, lead):
    role = FakeRole(EXEMPT_ROLE)

    await cog.exempt_add.callback(cog, FakeInteraction(bot, lead), role)
    assert bot.store.get(GUILD, "honeypot_exempt_role_ids") == [EXEMPT_ROLE]

    again = FakeInteraction(bot, lead)
    await cog.exempt_add.callback(cog, again, role)
    assert "already exempt" in again.sent

    await cog.exempt_remove.callback(cog, FakeInteraction(bot, lead), role)
    assert bot.store.get(GUILD, "honeypot_exempt_role_ids") == []


async def test_status_reads_the_mode_and_the_tally(cog, bot, lead, db):
    await record_hit(db, GUILD, USER, TRAP, 5, "x", "shadow", "would_ban")
    interaction = FakeInteraction(bot, lead)

    await cog.status.callback(cog, interaction)

    assert "**mode** — shadow" in interaction.sent
    assert "1 logged in shadow" in interaction.sent
    assert f"<#{TRAP}>" in interaction.sent


async def test_a_system_message_never_trips_the_trap(cog, bot, spammer, db):
    joined = FakePost(bot.guild, spammer, bot.guild.get_channel(TRAP))
    joined.type = discord.MessageType.new_member

    await cog.on_message(joined)

    assert joined.deleted is False and await hits(db) == [] and await action_kinds(db) == []


async def test_a_reply_in_the_trap_is_still_caught(cog, bot, spammer, db):
    reply = FakePost(bot.guild, spammer, bot.guild.get_channel(TRAP))
    reply.type = discord.MessageType.reply

    await cog.on_message(reply)

    assert reply.deleted is True and [h["action"] for h in await hits(db)] == ["would_ban"]


async def test_a_post_in_a_thread_of_the_trap_is_caught(cog, bot, spammer, db):
    thread = bot.guild.add(
        FakeChannel(4444, name="thread", category=bot.guild.get_channel(TRAP).category,
                    parent_id=TRAP)
    )

    await cog.on_message(FakePost(bot.guild, spammer, thread))

    assert [h["action"] for h in await hits(db)] == ["would_ban"]


async def test_a_thread_somewhere_else_is_ignored(cog, bot, spammer, db):
    thread = bot.guild.add(FakeChannel(4445, name="thread", parent_id=9999))

    await cog.on_message(FakePost(bot.guild, spammer, thread))

    assert await hits(db) == []


async def test_the_delete_is_refused_outside_the_test_category(cog, bot, spammer, db):
    bot.guard = FakeGuard()
    elsewhere = bot.guild.add(FakeChannel(4446, name="far-away", category=FakeCategory(51)))
    await bot.store.set(GUILD, "honeypot_channel_ids", [elsewhere.id])
    post = FakePost(bot.guild, spammer, elsewhere)

    await cog.on_message(post)

    assert post.deleted is False
    kinds = await action_kinds(db)
    assert "honeypot.would_delete" in kinds and "honeypot.delete_failed" not in kinds


async def test_a_second_shadow_hit_is_recorded_without_a_second_button(cog, bot, spammer, db):
    trap = bot.guild.get_channel(TRAP)

    await cog.on_message(FakePost(bot.guild, spammer, trap, message_id=5))
    await cog.on_message(FakePost(bot.guild, spammer, trap, message_id=6))

    assert [h["action"] for h in await hits(db)] == ["would_ban", "would_ban"]
    kinds = await action_kinds(db)
    assert kinds.count("honeypot.would_ban") == 1
    assert kinds.count("honeypot.hit_recorded") == 1
    assert len(ban_buttons(bot)) == 1


async def test_another_account_still_gets_its_own_button(cog, bot, spammer, db):
    trap = bot.guild.get_channel(TRAP)
    other = FakeMember(bot.guild, user_id=USER + 7)

    await cog.on_message(FakePost(bot.guild, spammer, trap, message_id=5))
    await cog.on_message(FakePost(bot.guild, other, trap, message_id=6))

    assert len(ban_buttons(bot)) == 2


async def test_setup_refuses_a_second_trap_and_says_how_to_forget_the_first(cog, bot, lead):
    interaction = FakeInteraction(bot, lead)

    await cog.setup_channel.callback(cog, interaction, None)

    assert bot.guild.created == []
    assert "/honeypot forget" in interaction.sent
    assert bot.store.get(GUILD, "honeypot_channel_ids") == [TRAP]


async def test_forget_drops_a_trap_id_and_refuses_anything_else(cog, bot, lead, db):
    interaction = FakeInteraction(bot, lead)
    await cog.forget.callback(cog, interaction, str(TRAP))
    assert bot.store.get(GUILD, "honeypot_channel_ids") == []
    assert "honeypot.trap_removed" in await action_kinds(db)

    again = FakeInteraction(bot, lead)
    await cog.forget.callback(cog, again, str(TRAP))
    assert "not one of" in again.sent

    nonsense = FakeInteraction(bot, lead)
    await cog.forget.callback(cog, nonsense, "the honeypot")
    assert "not a channel id" in nonsense.sent


async def test_forget_is_staff_only(cog, bot, spammer):
    interaction = FakeInteraction(bot, spammer)

    await cog.forget.callback(cog, interaction, str(TRAP))

    assert bot.store.get(GUILD, "honeypot_channel_ids") == [TRAP]
    assert "staff only" in interaction.sent


async def test_deleting_the_trap_channel_makes_black_bloc_forget_it(cog, bot, db):
    await cog.on_guild_channel_delete(bot.guild.get_channel(TRAP))

    assert bot.store.get(GUILD, "honeypot_channel_ids") == []
    assert "honeypot.trap_removed" in await action_kinds(db)


async def test_turning_the_trap_on_is_refused_while_no_staff_role_resolves(cog, bot, lead):
    interaction = FakeInteraction(bot, lead)

    await cog.mode.callback(cog, interaction, discord.app_commands.Choice(name="on", value="on"))

    assert bot.store.get(GUILD, "honeypot_mode") == "shadow"
    assert "staff_channel_id" in interaction.sent


async def test_turning_the_trap_on_works_once_staff_resolve(cog, bot, lead):
    give_staff(bot)
    interaction = FakeInteraction(bot, lead)

    await cog.mode.callback(cog, interaction, discord.app_commands.Choice(name="on", value="on"))

    assert bot.store.get(GUILD, "honeypot_mode") == "on"


async def test_status_names_the_resolved_staff_roles(cog, bot, lead):
    role = give_staff(bot)
    interaction = FakeInteraction(bot, lead)

    await cog.status.callback(cog, interaction)

    assert "1 role(s)" in interaction.sent and role.name in interaction.sent


async def test_status_warns_loudly_when_the_trap_is_on_with_no_staff(cog, bot, lead):
    await bot.store.set(GUILD, "honeypot_mode", "on")
    interaction = FakeInteraction(bot, lead)

    await cog.status.callback(cog, interaction)

    assert "no roles at all" in interaction.sent
    assert "No staff roles resolve" in interaction.sent


async def test_a_staff_role_is_exempt_because_it_can_see_the_staff_channel(cog, bot, db):
    role = give_staff(bot)
    moderator = FakeMember(bot.guild, user_id=USER + 8, roles=(role.id,))
    post = FakePost(bot.guild, moderator, bot.guild.get_channel(TRAP))

    await cog.on_message(post)

    assert post.deleted is False
    assert [h["action"] for h in await hits(db)] == ["exempt"]
