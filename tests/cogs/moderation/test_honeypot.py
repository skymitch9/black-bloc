import asyncio
import re
from types import SimpleNamespace

import discord
import pytest

from black_bloc.cogs.moderation import honeypot as honeypot_cog
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
from black_bloc.honeypot import (
    EXEMPT_PLACEHOLDER,
    FORGET_PLACEHOLDER,
    MODE_PLACEHOLDER,
    PANEL_TITLE,
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
        self.modals = []
        self.deferred = False

    def is_done(self):
        return self.deferred or bool(self.messages)

    async def send_message(self, content=None, ephemeral=False, **kwargs):
        self.messages.append({"content": content, "ephemeral": ephemeral, **kwargs})

    async def send_modal(self, modal):
        self.modals.append(modal)
        self.deferred = True

    async def defer(self, ephemeral=False):
        self.deferred = True
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
        self.edits = []

    async def original_response(self):
        return FakeMessage(1, "")

    async def edit_original_response(self, **kwargs):
        self.edits.append(kwargs)
        return FakeMessage(9500, "", **kwargs)

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
        said = [
            one["content"] for one in self.response.messages if one.get("content") is not None
        ]
        return said[-1] if said else None


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
    assert bot.guild.get_channel(LOG_CHANNEL).messages == []

    await bot.store.set(GUILD, "honeypot_log_level", "all")
    await cog.on_message(FakePost(bot.guild, a_bot, trap))
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


def labels(view):
    return [one.label for one in view.children if getattr(one, "label", None)]


def placeholders(view):
    return [
        one.placeholder for one in view.children if getattr(one, "placeholder", None) is not None
    ]


def control(view, placeholder):
    return next(
        one for one in view.children if getattr(one, "placeholder", None) == placeholder
    )


def options(view, placeholder):
    return control(view, placeholder).options


def button(view, label):
    return next(one for one in view.children if getattr(one, "label", None) == label)


def has(view, label):
    return any(getattr(one, "label", None) == label for one in view.children)


async def pick(picker, values, interaction):
    picker._values = list(values)
    await picker.callback(interaction)


async def open_panel(cog, bot, who):
    interaction = FakeInteraction(bot, who)
    await cog.honeypot.callback(cog, interaction)
    return interaction


async def press(bot, who, view, label):
    interaction = FakeInteraction(bot, who)
    await button(view, label).callback(interaction)
    return interaction


async def do_setup(cog, bot, who, name=""):
    """Setup… is a modal, so the sweep is: open the panel, press it, submit the box."""
    panel = await open_panel(cog, bot, who)
    opened = await press(bot, who, panel.view, "Setup…")
    modal = opened.response.modals[-1]
    modal.trap._value = name
    submitted = FakeInteraction(bot, who)
    await modal.on_submit(submitted)
    return submitted


async def test_setup_makes_the_trap_in_the_test_category_and_skips_the_notice(cog, bot, lead):
    await bot.store.set(GUILD, "honeypot_channel_ids", [])
    category = bot.guild.get_channel(TEST_CHANNEL).category
    bot.guard = FakeGuard()

    interaction = await do_setup(cog, bot, lead)

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

    interaction = await do_setup(cog, bot, lead)

    made = bot.guild.created[0]
    assert made.messages[0].content.startswith("This channel is a trap for bots.")
    assert made.messages[0].pinned is True
    assert "pinned" in interaction.sent


async def test_setup_is_staff_only(cog, bot, spammer):
    interaction = await open_panel(cog, bot, spammer)

    assert bot.guild.created == [] and "staff only" in interaction.sent
    assert interaction.view is None


async def test_the_role_picker_is_the_whole_list_and_one_write_does_add_and_remove(
    cog, bot, lead, db
):
    panel = await open_panel(cog, bot, lead)

    chosen = FakeInteraction(bot, lead)
    await pick(
        control(panel.view, EXEMPT_PLACEHOLDER),
        [FakeRole(EXEMPT_ROLE), FakeRole(EXEMPT_ROLE + 1)],
        chosen,
    )

    assert bot.store.get(GUILD, "honeypot_exempt_role_ids") == [EXEMPT_ROLE, EXEMPT_ROLE + 1]
    assert (await action_kinds(db)).count("honeypot.exempt_set") == 1
    assert f"<@&{EXEMPT_ROLE}>" in chosen.sent
    assert [one.id for one in control(chosen.view, EXEMPT_PLACEHOLDER)._underlying.default_values]
    assert f"<@&{EXEMPT_ROLE}>" in chosen.embed.description

    dropped = FakeInteraction(bot, lead)
    await pick(control(chosen.view, EXEMPT_PLACEHOLDER), [FakeRole(EXEMPT_ROLE)], dropped)

    assert bot.store.get(GUILD, "honeypot_exempt_role_ids") == [EXEMPT_ROLE]
    assert (await action_kinds(db)).count("honeypot.exempt_set") == 2
    assert f"stops ignoring <@&{EXEMPT_ROLE + 1}>" in dropped.sent


async def test_a_submit_that_changes_nothing_writes_no_row_at_all(cog, bot, lead, db):
    await bot.store.set(GUILD, "honeypot_exempt_role_ids", [EXEMPT_ROLE])
    panel = await open_panel(cog, bot, lead)

    again = FakeInteraction(bot, lead)
    await pick(control(panel.view, EXEMPT_PLACEHOLDER), [FakeRole(EXEMPT_ROLE)], again)

    assert "nothing changed" in again.sent
    assert "honeypot.exempt_set" not in await action_kinds(db)


async def test_exempt_nobody_empties_the_list_and_then_stops_being_offered(cog, bot, lead, db):
    await bot.store.set(GUILD, "honeypot_exempt_role_ids", [EXEMPT_ROLE])
    panel = await open_panel(cog, bot, lead)
    assert has(panel.view, "Exempt nobody")

    cleared = await press(bot, lead, panel.view, "Exempt nobody")

    assert bot.store.get(GUILD, "honeypot_exempt_role_ids") == []
    assert (await action_kinds(db)).count("honeypot.exempt_set") == 1
    assert "nobody but staff" in cleared.sent
    assert not has(cleared.view, "Exempt nobody")


async def test_more_roles_than_a_picker_can_edit_withholds_it_rather_than_dropping_them(
    cog, bot, lead
):
    await bot.store.set(GUILD, "honeypot_exempt_role_ids", list(range(9000, 9026)))

    embed, view = await honeypot_cog.build_root(bot, bot.guild)

    assert EXEMPT_PLACEHOLDER not in placeholders(view)
    assert "26 roles are exempt" in embed.description
    assert has(view, "Exempt nobody")

    await bot.store.set(GUILD, "honeypot_exempt_role_ids", list(range(9000, 9025)))
    _again, back = await honeypot_cog.build_root(bot, bot.guild)
    picker = control(back, EXEMPT_PLACEHOLDER)
    assert [one.id for one in picker._underlying.default_values] == list(range(9000, 9025))


async def test_the_command_answers_one_ephemeral_panel_carrying_the_whole_status_block(
    cog, bot, lead, db
):
    give_staff(bot)
    await record_hit(db, GUILD, USER, TRAP, 5, "x", "shadow", "would_ban")

    interaction = await open_panel(cog, bot, lead)

    assert len(interaction.response.messages) == 1
    said = interaction.response.messages[0]
    assert said["ephemeral"] is True and said["allowed_mentions"].everyone is False
    embed = said["embed"]
    assert embed.title == PANEL_TITLE
    for line in ("**mode** — shadow", "**purge** — 1 day(s)", "1 logged in shadow"):
        assert line in embed.description
    assert f"<#{TRAP}>" in embed.description
    assert "/honeypot status" not in embed.description
    assert "/honeypot setup" not in embed.description
    assert "/honeypot exempt" not in embed.description
    assert placeholders(said["view"]) == [MODE_PLACEHOLDER, EXEMPT_PLACEHOLDER]
    assert labels(said["view"]) == ["Forget…", "Settings…", "Refresh", "Logs", "Open on the site"]


async def test_the_panel_says_so_rather_than_opening_when_the_database_is_down(cog, bot, lead):
    bot.db = SimpleNamespace(is_connected=False, conn=bot.db.conn)

    interaction = await open_panel(cog, bot, lead)

    assert "cannot reach its own database" in interaction.sent
    assert interaction.view is None


async def test_there_is_no_site_button_when_there_is_nowhere_to_send_anybody(bot):
    bot.settings = bot.settings.model_copy(update={"site_origin": ""})

    _embed, view = await honeypot_cog.build_root(bot, bot.guild)

    assert not has(view, "Open on the site")


@pytest.mark.parametrize("mode", ["off", "shadow", "on"])
@pytest.mark.parametrize("state", ["no_roles", "nothing_recorded", "a_live_trap", "a_dead_id"])
async def test_every_state_renders_exactly_its_row_of_the_table(cog, bot, lead, mode, state):
    """Checklist 3 and 12: a move the shared function would refuse is absent, not refused."""
    if state != "no_roles":
        give_staff(bot)
    if state == "nothing_recorded":
        await bot.store.set(GUILD, "honeypot_channel_ids", [])
    if state == "a_dead_id":
        await bot.store.set(GUILD, "honeypot_channel_ids", [4747])
    await bot.store.set(GUILD, "honeypot_mode", mode)

    embed, view = await honeypot_cog.build_root(bot, bot.guild)

    offered = [one.value for one in options(view, MODE_PLACEHOLDER)]
    if state == "no_roles":
        assert offered == ["off", "shadow"]
        assert "cannot work out who counts as staff" in embed.description
    else:
        assert offered == ["off", "shadow", "on"]
        assert "cannot work out who counts as staff" not in embed.description
    assert [one.default for one in options(view, MODE_PLACEHOLDER)].count(True) <= 1
    assert has(view, "Setup…") is (state in ("nothing_recorded", "a_dead_id"))
    assert has(view, "Forget…") is (state != "nothing_recorded")
    assert not has(view, "Exempt nobody")
    assert ("recorded but gone" in embed.description) is (state == "a_dead_id")
    assert ("no trap channel yet" in embed.description) is (
        mode == "on" and state in ("nothing_recorded", "a_dead_id")
    )
    assert ("No staff roles resolve" in embed.description) == (
        mode == "on" and state == "no_roles"
    )


async def test_test_mode_says_out_loud_that_nobody_will_be_banned(bot):
    bot.guard = FakeGuard()

    embed, _view = await honeypot_cog.build_root(bot, bot.guild)

    assert "nobody will" in embed.description and "test channel's category" in embed.description

    bot.guard = None
    again, _view = await honeypot_cog.build_root(bot, bot.guild)
    assert "nobody will" not in again.description


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


async def test_a_second_trap_is_not_offered_rather_than_offered_and_refused(cog, bot, lead):
    panel = await open_panel(cog, bot, lead)

    assert not has(panel.view, "Setup…")
    assert bot.store.get(GUILD, "honeypot_channel_ids") == [TRAP]

    _, said = await honeypot_cog.make_trap_channel(bot, bot.guild, lead)
    assert bot.guild.created == []
    assert "/honeypot forget" not in said and "forget it from the honeypot panel" in said


async def test_forget_drops_a_trap_id_with_no_id_typed_anywhere(cog, bot, lead, db):
    panel = await open_panel(cog, bot, lead)
    card = await press(bot, lead, panel.view, "Forget…")
    assert [one.value for one in options(card.view, FORGET_PLACEHOLDER)] == [str(TRAP)]

    chosen = FakeInteraction(bot, lead)
    await pick(control(card.view, FORGET_PLACEHOLDER), [str(TRAP)], chosen)

    assert bot.store.get(GUILD, "honeypot_channel_ids") == []
    assert "honeypot.trap_removed" in await action_kinds(db)
    assert has(chosen.view, "Setup…") and not has(chosen.view, "Forget…")


async def test_a_channel_discord_no_longer_has_is_still_offered_for_forgetting(cog, bot, lead):
    await bot.store.set(GUILD, "honeypot_channel_ids", [4747])

    _embed, view = honeypot_cog.build_forget(bot, bot.guild)

    assert [one.label for one in options(view, FORGET_PLACEHOLDER)] == [
        "a channel Discord no longer has (4747)"
    ]


async def test_forgetting_the_same_id_twice_is_answered_in_words(cog, bot, lead):
    outcome = await honeypot_cog.forget_trap(bot, bot.guild, 4747, lead)

    assert outcome.ok is False and "not one of" in outcome.message


async def test_the_panel_is_staff_only_and_says_so_in_words(cog, bot, spammer):
    interaction = await open_panel(cog, bot, spammer)

    assert bot.store.get(GUILD, "honeypot_channel_ids") == [TRAP]
    assert "staff only" in interaction.sent


async def test_deleting_the_trap_channel_makes_black_bloc_forget_it(cog, bot, db):
    await cog.on_guild_channel_delete(bot.guild.get_channel(TRAP))

    assert bot.store.get(GUILD, "honeypot_channel_ids") == []
    assert "honeypot.trap_removed" in await action_kinds(db)


async def test_arming_is_refused_by_the_same_answer_the_picker_read(cog, bot, lead, db):
    """The mode picker and `set_mode` read one `arming_refusal`, so they cannot disagree."""
    outcome = await honeypot_cog.set_mode(bot, bot.guild, "on", lead)

    assert outcome.ok is False and "staff_channel_id" in outcome.message
    assert bot.store.get(GUILD, "honeypot_mode") == "shadow"
    assert "honeypot.mode" not in await action_kinds(db)


async def test_the_mode_picker_writes_one_row_and_re_renders(cog, bot, lead, db):
    give_staff(bot)
    panel = await open_panel(cog, bot, lead)

    chosen = FakeInteraction(bot, lead)
    await pick(control(panel.view, MODE_PLACEHOLDER), ["on"], chosen)

    assert bot.store.get(GUILD, "honeypot_mode") == "on"
    assert (await action_kinds(db)).count("honeypot.mode") == 1
    assert "The trap is now **on**." in chosen.sent
    assert "**mode** — on" in chosen.embed.description


async def test_the_panel_names_the_resolved_staff_roles(cog, bot, lead):
    role = give_staff(bot)

    embed, _view = await honeypot_cog.build_root(bot, bot.guild)

    assert "1 role(s)" in embed.description and role.name in embed.description


async def test_the_panel_warns_loudly_when_the_trap_is_on_with_no_staff(cog, bot, lead):
    await bot.store.set(GUILD, "honeypot_mode", "on")

    embed, _view = await honeypot_cog.build_root(bot, bot.guild)

    assert "no roles at all" in embed.description
    assert "No staff roles resolve" in embed.description


async def test_the_name_box_carries_the_bound_the_name_parameter_used_to(cog, bot, lead):
    await bot.store.set(GUILD, "honeypot_channel_ids", [])
    panel = await open_panel(cog, bot, lead)

    opened = await press(bot, lead, panel.view, "Setup…")
    modal = opened.response.modals[-1]

    assert modal.trap.max_length == 100
    assert modal.trap.default == TRAP_NAME
    assert modal.trap.required is False


async def test_an_empty_name_box_falls_back_to_the_default_trap_name(cog, bot, lead):
    await bot.store.set(GUILD, "honeypot_channel_ids", [])

    await do_setup(cog, bot, lead, name="")

    assert bot.guild.created[0].name == TRAP_NAME


async def test_the_numbers_modal_arrives_full_and_writes_nothing_when_one_field_is_refused(
    cog, bot, lead, db
):
    panel = await open_panel(cog, bot, lead)
    card = await press(bot, lead, panel.view, "Settings…")
    opened = await press(bot, lead, card.view, "Numbers…")
    modal = opened.response.modals[-1]

    assert modal.stays.default == "10" and modal.purge.default == "1"

    modal.stays._value = "20"
    modal.purge._value = "9"
    refused = FakeInteraction(bot, lead)
    await modal.on_submit(refused)

    assert "more than 7" in refused.sent
    assert bot.store.get(GUILD, "honeypot_panel_minutes") == 10
    assert bot.store.get(GUILD, "honeypot_purge_days") == 1
    assert "honeypot.settings" not in await action_kinds(db)
    assert refused.edits == []

    modal.purge._value = "3"
    saved = FakeInteraction(bot, lead)
    await modal.on_submit(saved)

    assert bot.store.get(GUILD, "honeypot_panel_minutes") == 20
    assert bot.store.get(GUILD, "honeypot_purge_days") == 3
    assert (await action_kinds(db)).count("honeypot.settings") == 1


async def test_a_word_where_a_number_belongs_is_refused_in_one_sentence(cog, bot, lead, db):
    modal = honeypot_cog.NumbersModal(10, 1)
    modal.stays._value = "soon"
    modal.purge._value = "1"
    interaction = FakeInteraction(bot, lead)

    await modal.on_submit(interaction)

    assert "not a whole number" in interaction.sent
    assert bot.store.get(GUILD, "honeypot_panel_minutes") == 10
    assert "honeypot.settings" not in await action_kinds(db)


async def test_the_settings_card_says_how_to_get_the_command_back_when_the_mode_is_off(bot):
    _embed, view = honeypot_cog.build_settings(bot, bot.guild)
    embed, _again = honeypot_cog.build_settings(bot, bot.guild)

    assert "/settings set-value honeypot_mode" in embed.description
    assert labels(view) == ["Numbers…", "Back"]


async def test_logs_answers_a_new_message_and_leaves_the_panel_where_it_is(cog, bot, lead, db):
    await record_hit(db, GUILD, USER, TRAP, 5, "x", "shadow", "would_ban")
    panel = await open_panel(cog, bot, lead)

    pressed = await press(bot, lead, panel.view, "Logs")

    assert pressed.edits == []
    assert pressed.response.messages


async def test_a_staffer_demoted_mid_panel_moves_nothing_at_all(cog, bot, lead, spammer, db):
    give_staff(bot)
    panel = await open_panel(cog, bot, lead)
    before = await action_kinds(db)

    for label in ("Forget…", "Settings…", "Refresh"):
        refused = FakeInteraction(bot, spammer)
        await button(panel.view, label).callback(refused)
        assert "staff only" in refused.sent
        assert refused.edits == []

    mode = FakeInteraction(bot, spammer)
    await pick(control(panel.view, MODE_PLACEHOLDER), ["on"], mode)
    assert "staff only" in mode.sent

    roles = FakeInteraction(bot, spammer)
    await pick(control(panel.view, EXEMPT_PLACEHOLDER), [FakeRole(EXEMPT_ROLE)], roles)
    assert "staff only" in roles.sent

    assert bot.store.get(GUILD, "honeypot_mode") == "shadow"
    assert bot.store.get(GUILD, "honeypot_exempt_role_ids") == []
    assert await action_kinds(db) == before


async def test_every_click_re_checks_the_database_after_the_defer(cog, bot, lead):
    """The four subcommands that skipped the DB check cannot skip it any more."""
    panel = await open_panel(cog, bot, lead)
    bot.db = SimpleNamespace(is_connected=False, conn=bot.db.conn)

    for label in ("Forget…", "Settings…", "Refresh"):
        refused = FakeInteraction(bot, lead)
        await button(panel.view, label).callback(refused)
        assert "cannot reach its own database" in refused.sent
        assert refused.edits == []

    mode = FakeInteraction(bot, lead)
    await pick(control(panel.view, MODE_PLACEHOLDER), ["shadow"], mode)
    assert "cannot reach its own database" in mode.sent

    roles = FakeInteraction(bot, lead)
    await pick(control(panel.view, EXEMPT_PLACEHOLDER), [FakeRole(EXEMPT_ROLE)], roles)
    assert "cannot reach its own database" in roles.sent


async def test_the_panel_is_retired_when_it_is_replaced(cog, bot, lead):
    panel = await open_panel(cog, bot, lead)
    view = panel.view

    await press(bot, lead, view, "Refresh")

    assert view.replaced is True and view.is_finished()


async def test_every_move_passes_via_at_its_discord_default(cog, bot, lead, db):
    """Checklist 34: one write, one log row, and no `web.` head from a Discord door."""
    give_staff(bot)
    await honeypot_cog.set_mode(bot, bot.guild, "on", lead)
    await honeypot_cog.set_exempt_roles(bot, bot.guild, [EXEMPT_ROLE], lead)
    await honeypot_cog.forget_trap(bot, bot.guild, TRAP, lead)
    await honeypot_cog.save_settings(bot, bot.guild, {"honeypot_purge_days": 2}, lead)

    kinds = await action_kinds(db)
    assert [one for one in kinds if one.startswith("web.")] == []
    assert kinds == [
        "honeypot.mode",
        "honeypot.exempt_set",
        "honeypot.trap_removed",
        "honeypot.settings",
    ]


async def test_a_website_move_takes_the_web_head_and_says_so(bot, lead, db):
    give_staff(bot)

    await honeypot_cog.set_exempt_roles(bot, bot.guild, [EXEMPT_ROLE], lead, via="website")

    assert await action_kinds(db) == ["web.honeypot.exempt_set"]


async def test_a_staff_role_is_exempt_because_it_can_see_the_staff_channel(cog, bot, db):
    role = give_staff(bot)
    moderator = FakeMember(bot.guild, user_id=USER + 8, roles=(role.id,))
    post = FakePost(bot.guild, moderator, bot.guild.get_channel(TRAP))

    await cog.on_message(post)

    assert post.deleted is False
    assert [h["action"] for h in await hits(db)] == ["exempt"]
