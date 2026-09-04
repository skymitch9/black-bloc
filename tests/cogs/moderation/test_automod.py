import asyncio
import re
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import discord
import pytest

from black_bloc.automod import RULE_HELP, RULE_ORDER, rule_config
from black_bloc.cogs.moderation import automod as automod_cog
from black_bloc.cogs.moderation.automod import (
    APPLY_TEMPLATE,
    ApplyNowButton,
    AutoMod,
    apply_custom_id,
    user_lock,
)
from black_bloc.config import load_settings
from black_bloc.modcases import add_case, get_case, set_case_log_message
from black_bloc.settings_store import SettingsStore
from black_bloc.storage.db import Database

GUILD = 7
TEST_CHANNEL = 111
LOG_CHANNEL = 222
ELSEWHERE = 444
HONEYPOT = 555
STAFF_CHANNEL = 666
STAFF_ROLE = 600
EXEMPT_ROLE = 601
USER = 900
SNOWFLAKE = 123456789012345678
BOT_ID = 42
NOW = datetime(2026, 8, 26, 12, 0, tzinfo=UTC)


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


class FakePartialMessage:
    def __init__(self, channel, message_id):
        self.channel = channel
        self.id = message_id

    async def delete(self):
        known = self.channel.sent_messages.get(self.id)
        if known is not None:
            await known.delete()
        else:
            self.channel.deleted.append(self.id)

    async def edit(self, **kwargs):
        self.channel.edits.append({"message_id": self.id, **kwargs})


class FakeChannel:
    def __init__(self, channel_id, name="channel", parent_id=None):
        self.id = channel_id
        self.name = name
        self.mention = f"<#{channel_id}>"
        self.parent_id = parent_id
        self.visible_to = set()
        self.messages = []
        self.sent_messages = {}
        self.deleted = []
        self.edits = []

    def permissions_for(self, role):
        return FakePerms(view_channel=role.id in self.visible_to)

    def get_partial_message(self, message_id):
        return FakePartialMessage(self, int(message_id))

    async def send(self, content=None, **kwargs):
        message = FakeMessage(len(self.messages) + 1, content or "", **kwargs)
        self.messages.append(message)
        return message


class FakeGuild:
    def __init__(self):
        self.id = GUILD
        self.name = "Black Bloc"
        self.channels = {}
        self.members = {}
        self.roles = []
        self.default_role = FakeRole(GUILD)

    def add(self, channel):
        channel.guild = self
        self.channels[channel.id] = channel
        return channel

    def get_channel(self, channel_id):
        return self.channels.get(channel_id)

    def get_member(self, user_id):
        return self.members.get(user_id)

    def get_role(self, role_id):
        return next((one for one in self.roles if one.id == role_id), None)


class FakeMember:
    def __init__(self, guild, user_id=USER, roles=(), manage_guild=False, bot=False):
        self.id = user_id
        self.guild = guild
        self.name = f"member-{user_id}"
        self.display_name = self.name
        self.mention = f"<@{user_id}>"
        self.bot = bot
        self.roles = [FakeRole(r) for r in roles]
        self.guild_permissions = FakePerms(manage_guild=manage_guild)
        self.dms = []
        self.timeouts = []
        self.timeout_raises = None
        guild.members[user_id] = self

    async def send(self, content=None, **kwargs):
        self.dms.append(content)

    async def timeout(self, until, reason=None):
        if self.timeout_raises is not None:
            raise self.timeout_raises
        self.timeouts.append((until, reason))


class FakePost:
    def __init__(self, guild, author, channel, content="", mentions=(), message_id=5, at=NOW):
        self.guild = guild
        self.author = author
        self.channel = channel
        self.content = content
        self.id = message_id
        self.created_at = at
        self.type = discord.MessageType.default
        self.webhook_id = None
        self.mentions = [FakeRole(m) for m in mentions]
        self.role_mentions = []
        self.attachments = []
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


async def cases(db):
    cur = await db.conn.execute("SELECT * FROM mod_cases ORDER BY id")
    return list(await cur.fetchall())


def cards(bot, channel_id=TEST_CHANNEL):
    return [m for m in bot.guild.get_channel(channel_id).messages if "embed" in m.kwargs]


@pytest.fixture
async def db(tmp_path):
    database = Database(tmp_path / "a.sqlite3")
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
    await store.set(GUILD, "modlog_channel_id", TEST_CHANNEL)
    await store.set(GUILD, "honeypot_channel_ids", [HONEYPOT])
    guild = FakeGuild()
    guild.add(FakeChannel(TEST_CHANNEL, name="test"))
    guild.add(FakeChannel(LOG_CHANNEL, name="log"))
    guild.add(FakeChannel(ELSEWHERE, name="general"))
    guild.add(FakeChannel(HONEYPOT, name="trap"))
    guild.add(FakeChannel(STAFF_CHANNEL, name="staff"))
    return FakeBot(db, store, settings, guild)


@pytest.fixture
def cog(bot):
    return AutoMod(bot)


@pytest.fixture
def spammer(bot):
    return FakeMember(bot.guild)


@pytest.fixture
def lead(bot):
    return FakeMember(bot.guild, user_id=1, manage_guild=True)


def give_staff(bot, role_id=STAFF_ROLE, channel_id=TEST_CHANNEL):
    role = FakeRole(role_id)
    bot.guild.roles.append(role)
    bot.guild.get_channel(channel_id).visible_to.add(role_id)
    return role


def spam(bot, author, channel_id=TEST_CHANNEL, message_id=5):
    return FakePost(
        bot.guild,
        author,
        bot.guild.get_channel(channel_id),
        content="look at this",
        mentions=(1, 2, 3, 4, 5),
        message_id=message_id,
    )


async def test_shadow_deletes_nothing_warns_nobody_and_offers_the_button(cog, bot, spammer, db):
    post = spam(bot, spammer)

    await cog.on_message(post)

    assert post.deleted is False and spammer.timeouts == [] and spammer.dms == []
    rows = await cases(db)
    assert [(r["kind"], r["applied"], r["mode"]) for r in rows] == [("automod", 0, "shadow")]
    assert rows[0]["reason"] == "5 mentions in 30s" and rows[0]["duration_s"] == 300
    kinds = await action_kinds(db)
    assert kinds == ["automod.would_delete", "automod.would_warn", "automod.would_timeout"]
    card = cards(bot)[-1]
    assert card.kwargs["view"].children[0].custom_id == apply_custom_id(rows[0]["id"])
    assert card.kwargs["allowed_mentions"].everyone is False


async def test_off_mode_touches_nothing(cog, bot, spammer, db):
    await bot.store.set(GUILD, "automod_mode", "off")

    await cog.on_message(spam(bot, spammer))

    assert await cases(db) == [] and await action_kinds(db) == []


async def test_on_mode_deletes_dms_and_times_out(cog, bot, spammer, db):
    await bot.store.set(GUILD, "automod_mode", "on")
    post = spam(bot, spammer)

    await cog.on_message(post)

    assert post.deleted is True
    assert spammer.timeouts and spammer.timeouts[0][0] == timedelta(seconds=300)
    assert "5 mentions in 30s" in spammer.timeouts[0][1]
    assert spammer.dms and "timed out by the automatic filter" in spammer.dms[0]
    assert "5m" in spammer.dms[0]
    rows = await cases(db)
    assert [r["applied"] for r in rows] == [1]
    assert rows[0]["done"] == '["delete", "warn", "timeout"]'
    assert rows[0]["message_id"] == post.id and rows[0]["channel_id"] == TEST_CHANNEL
    kinds = await action_kinds(db)
    assert kinds == ["automod.deleted", "automod.warned", "automod.timed_out"]
    assert cards(bot)[-1].kwargs.get("view") is None


async def test_the_dm_setting_decides_what_the_member_is_told(cog, bot, spammer):
    await bot.store.set(GUILD, "automod_mode", "on")
    await bot.store.set(GUILD, "mod_dm_on_action", "none")

    await cog.on_message(spam(bot, spammer))

    assert spammer.dms == []


async def test_a_timeout_is_refused_in_test_mode_and_logged_as_would_timeout(cog, bot, spammer, db):
    await bot.store.set(GUILD, "automod_mode", "on")
    bot.guard = FakeGuard()

    await cog.on_message(spam(bot, spammer))

    assert spammer.timeouts == []
    kinds = await action_kinds(db)
    assert "automod.would_timeout" in kinds and "automod.timed_out" not in kinds
    assert [r["applied"] for r in await cases(db)] == [0]
    assert cards(bot)[-1].kwargs.get("view") is not None


async def test_a_timeout_discord_refuses_is_never_confused_with_a_dry_run(cog, bot, spammer, db):
    await bot.store.set(GUILD, "automod_mode", "on")
    spammer.timeout_raises = refused()

    await cog.on_message(spam(bot, spammer))

    kinds = await action_kinds(db)
    assert "automod.timeout_failed" in kinds and "automod.would_timeout" not in kinds
    rows = await cases(db)
    assert [r["applied"] for r in rows] == [1]
    assert rows[0]["done"] == '["delete", "warn"]' and rows[0]["failed"] == '["timeout"]'
    card = cards(bot)[-1]
    assert card.kwargs.get("view") is None
    names = [field.name for field in card.kwargs["embed"].fields]
    assert "Done" in names and "Refused" in names and "Not done" not in names


async def test_a_message_that_cannot_be_deleted_is_still_acted_on(cog, bot, spammer, db):
    await bot.store.set(GUILD, "automod_mode", "on")
    post = spam(bot, spammer)
    post.delete_raises = refused()

    await cog.on_message(post)

    kinds = await action_kinds(db)
    assert "automod.delete_failed" in kinds and "automod.timed_out" in kinds
    assert spammer.timeouts != []


async def test_a_delete_is_refused_while_the_guard_is_installed(bot, spammer):
    post = spam(bot, spammer)
    bot.guard = FakeGuard()

    failure = await automod_cog.do_delete(bot, post)

    assert failure == "test_mode" and post.deleted is False

    bot.guard = None
    assert await automod_cog.do_delete(bot, post) is None and post.deleted is True


async def test_a_log_only_rule_is_a_log_line_and_nothing_else(cog, bot, spammer, db):
    book = dict(bot.store.get(GUILD, "automod_rules"))
    book["mention_spam"] = {"enabled": False}
    await bot.store.set(GUILD, "automod_rules", book)
    post = FakePost(
        bot.guild, spammer, bot.guild.get_channel(TEST_CHANNEL), content="https://example.com"
    )

    await cog.on_message(post)

    assert await cases(db) == []
    assert await action_kinds(db) == ["automod.observed"]
    assert cards(bot) == []


async def test_staff_bots_exempt_roles_and_exempt_channels_never_reach_the_engine(cog, bot, db):
    role = give_staff(bot)
    await bot.store.set(GUILD, "automod_exempt_role_ids", [EXEMPT_ROLE])
    await bot.store.set(GUILD, "automod_exempt_channel_ids", [ELSEWHERE])
    moderator = FakeMember(bot.guild, user_id=USER + 1, roles=(role.id,))
    friend = FakeMember(bot.guild, user_id=USER + 2, roles=(EXEMPT_ROLE,))
    a_bot = FakeMember(bot.guild, user_id=USER + 3, bot=True)
    lead = FakeMember(bot.guild, user_id=USER + 4, manage_guild=True)
    stranger = FakeMember(bot.guild, user_id=USER + 5)

    for member in (moderator, friend, a_bot, lead):
        await cog.on_message(spam(bot, member))
    await cog.on_message(spam(bot, stranger, channel_id=ELSEWHERE))
    await cog.on_message(spam(bot, stranger, channel_id=HONEYPOT))

    assert await cases(db) == []


async def test_a_thread_of_an_exempt_channel_is_exempt_too(cog, bot, spammer, db):
    await bot.store.set(GUILD, "automod_exempt_channel_ids", [ELSEWHERE])
    thread = bot.guild.add(FakeChannel(4242, name="thread", parent_id=ELSEWHERE))

    await cog.on_message(
        FakePost(bot.guild, spammer, thread, content="@x", mentions=(1, 2, 3, 4, 5))
    )

    assert await cases(db) == []


async def test_the_engine_only_ever_sees_the_test_channel_while_the_guard_is_on(cog, bot, db):
    bot.guard = FakeGuard()
    stranger = FakeMember(bot.guild, user_id=USER + 6)

    await cog.on_message(spam(bot, stranger, channel_id=ELSEWHERE))

    assert await cases(db) == []

    await cog.on_message(spam(bot, stranger, channel_id=TEST_CHANNEL))

    assert len(await cases(db)) == 1


async def test_system_messages_webhooks_dms_and_the_bot_itself_are_ignored(cog, bot, spammer, db):
    joined = spam(bot, spammer)
    joined.type = discord.MessageType.new_member
    await cog.on_message(joined)

    hooked = spam(bot, spammer, message_id=6)
    hooked.webhook_id = 99
    await cog.on_message(hooked)

    direct = spam(bot, spammer, message_id=7)
    direct.guild = None
    await cog.on_message(direct)

    itself = FakeMember(bot.guild, user_id=BOT_ID, bot=True)
    await cog.on_message(spam(bot, itself, message_id=8))

    assert await cases(db) == []


async def test_a_reply_still_counts(cog, bot, spammer, db):
    post = spam(bot, spammer)
    post.type = discord.MessageType.reply

    await cog.on_message(post)

    assert len(await cases(db)) == 1


async def test_a_burst_from_one_account_is_serialised(cog, bot, spammer, db):
    await bot.store.set(GUILD, "automod_mode", "on")

    await asyncio.gather(
        cog.on_message(spam(bot, spammer, message_id=5)),
        cog.on_message(spam(bot, spammer, message_id=6)),
    )

    assert len(spammer.timeouts) == 2
    assert user_lock(bot, spammer.id) is user_lock(bot, spammer.id)
    assert user_lock(bot, spammer.id) is not user_lock(bot, spammer.id + 1)


async def test_the_apply_button_custom_id_matches_its_template():
    assert apply_custom_id(12) == "automod:apply:12"
    match = re.fullmatch(APPLY_TEMPLATE, apply_custom_id(12))
    assert match is not None and int(match["case_id"]) == 12
    assert re.fullmatch(APPLY_TEMPLATE, "automod:apply:x") is None
    assert ApplyNowButton(12).item.custom_id == "automod:apply:12"


async def shadow_case(db, **changes):
    fields = {
        "reason": "5 mentions in 30s",
        "duration_s": 300,
        "mode": "shadow",
        "applied": False,
        "actions": ["warn", "timeout"],
    }
    return await add_case(db, GUILD, USER, "automod", **(fields | changes))


async def test_the_apply_button_is_staff_only(bot, spammer, db):
    case_id = await shadow_case(db)

    await ApplyNowButton(case_id).callback(FakeInteraction(bot, spammer))

    assert spammer.timeouts == [] and (await get_case(db, case_id))["applied"] == 0


async def test_the_apply_button_times_the_member_out(bot, spammer, lead, db):
    case_id = await shadow_case(db)
    interaction = FakeInteraction(bot, lead)

    await ApplyNowButton(case_id).callback(interaction)

    assert spammer.timeouts and spammer.timeouts[0][0] == timedelta(seconds=300)
    assert spammer.dms != []
    assert (await get_case(db, case_id))["applied"] == 1
    assert interaction.response.messages[0].get("deferred") is True
    assert "Applied case" in interaction.sent
    kinds = await action_kinds(db)
    assert "automod.warned" in kinds and "automod.timed_out" in kinds


async def test_the_apply_button_applies_exactly_what_the_rule_asked_for(bot, spammer, lead, db):
    post = spam(bot, spammer)
    bot.guild.get_channel(TEST_CHANNEL).sent_messages[post.id] = post
    case_id = await shadow_case(
        db, actions=["delete", "warn"], duration_s=None, message_id=post.id,
        channel_id=TEST_CHANNEL,
    )

    await ApplyNowButton(case_id).callback(FakeInteraction(bot, lead))

    assert post.deleted is True and spammer.timeouts == []
    assert (await get_case(db, case_id))["done"] == '["delete", "warn"]'


async def test_the_second_staffer_to_click_is_told_somebody_beat_them_to_it(
    bot, spammer, lead, db, monkeypatch
):
    case_id = await shadow_case(db)
    first = FakeInteraction(bot, lead)
    second = FakeInteraction(bot, lead)

    await ApplyNowButton(case_id).callback(first)
    stale = dict(await get_case(db, case_id)) | {"applied": 0}

    async def read_a_stale_row(_db, _case_id):
        return stale

    monkeypatch.setattr(automod_cog, "get_case", read_a_stale_row)
    await ApplyNowButton(case_id).callback(second)

    assert "Applied case" in first.sent
    assert "Someone just applied this case" in second.sent
    assert len(spammer.timeouts) == 1


async def test_a_click_that_discord_refuses_leaves_the_case_open(bot, spammer, lead, db):
    spammer.timeout_raises = refused()
    case_id = await shadow_case(db, actions=["timeout"])
    interaction = FakeInteraction(bot, lead)

    await ApplyNowButton(case_id).callback(interaction)

    assert "Moderate Members" in interaction.sent
    assert (await get_case(db, case_id))["applied"] == 0
    assert "automod.timeout_failed" in await action_kinds(db)


async def test_a_successful_click_rewrites_the_shadow_card(bot, spammer, lead, db):
    case_id = await shadow_case(db)
    channel = bot.guild.get_channel(TEST_CHANNEL)
    card = await channel.send(embed=object(), view=object())
    await set_case_log_message(db, case_id, card.id)

    await ApplyNowButton(case_id).callback(FakeInteraction(bot, lead))

    edit = channel.edits[-1]
    assert edit["message_id"] == card.id and edit["view"] is None
    assert f"<@{lead.id}>" in edit["embed"].description


async def test_the_apply_button_refuses_in_test_mode_with_a_sentence(bot, spammer, lead, db):
    bot.guard = FakeGuard()
    case_id = await shadow_case(db)
    interaction = FakeInteraction(bot, lead)

    await ApplyNowButton(case_id).callback(interaction)

    assert spammer.timeouts == []
    assert "test mode" in interaction.sent
    assert (await get_case(db, case_id))["applied"] == 0
    assert "automod.would_timeout" in await action_kinds(db)


async def test_the_apply_button_says_so_when_it_is_already_applied_or_gone(bot, lead, db):
    case_id = await add_case(db, GUILD, USER, "automod", duration_s=300, applied=True)
    done = FakeInteraction(bot, lead)
    await ApplyNowButton(case_id).callback(done)
    assert "already been applied" in done.sent

    missing = FakeInteraction(bot, lead)
    await ApplyNowButton(4242).callback(missing)
    assert "no record" in missing.sent


def labels(view):
    return [one.label for one in view.children if getattr(one, "label", None)]


def placeholders(view):
    return [
        one.placeholder for one in view.children if getattr(one, "placeholder", None) is not None
    ]


def options(view, placeholder):
    picker = next(one for one in view.children if getattr(one, "placeholder", None) == placeholder)
    return picker.options


def control(view, placeholder):
    return next(
        one for one in view.children if getattr(one, "placeholder", None) == placeholder
    )


def button(view, label):
    return next(one for one in view.children if getattr(one, "label", None) == label)


def has(view, label):
    return any(getattr(one, "label", None) == label for one in view.children)


async def pick(picker, values, interaction):
    picker._values = list(values)
    await picker.callback(interaction)


def armable(bot, role_id=STAFF_ROLE):
    """A real staff channel that resolves at least one role — state S3."""
    give_staff(bot, role_id=role_id, channel_id=STAFF_CHANNEL)
    return bot.store.set(GUILD, "staff_channel_id", STAFF_CHANNEL)


async def open_panel(cog, bot, who):
    interaction = FakeInteraction(bot, who)
    await cog.automod.callback(cog, interaction)
    return interaction


async def test_the_command_answers_one_ephemeral_panel_carrying_the_whole_status_block(
    cog, bot, lead, db
):
    give_staff(bot)
    await add_case(db, GUILD, USER, "automod", mode="shadow", applied=False)

    interaction = await open_panel(cog, bot, lead)

    assert len(interaction.response.messages) == 1
    said = interaction.response.messages[0]
    assert said["ephemeral"] is True and said["allowed_mentions"].everyone is False
    embed = said["embed"]
    assert embed.title == automod_cog.PANEL_TITLE
    for line in ("**mode** — shadow", "**warn threshold**", "**modlog**", "1 logged only"):
        assert line in embed.description
    assert "**mention_spam** — on · 5 in 30s · delete, warn, timeout (300s)" in embed.description
    assert "**caps** — off" in embed.description
    assert "/automod status" not in embed.description
    assert "/automod rule" not in embed.description
    assert placeholders(said["view"]) == [automod_cog.PICK_A_RULE, automod_cog.MODE_PLACEHOLDER]
    assert labels(said["view"]) == [
        "Exemptions…",
        "Settings…",
        "Refresh",
        "Logs",
        "Open on the site",
    ]


async def test_the_panel_is_staff_only_and_says_so_in_words(cog, bot, spammer):
    interaction = await open_panel(cog, bot, spammer)

    assert "staff only" in interaction.sent
    assert interaction.response.messages[-1].get("embed") is None


async def test_the_panel_says_so_rather_than_opening_when_the_database_is_down(cog, bot, lead):
    bot.db = SimpleNamespace(is_connected=False, conn=bot.db.conn)
    interaction = await open_panel(cog, bot, lead)

    assert "cannot reach its own database" in interaction.sent
    assert interaction.view is None


@pytest.mark.parametrize("mode", ["off", "shadow", "on"])
@pytest.mark.parametrize("state", ["test_channel", "no_roles", "armable"])
async def test_every_state_renders_exactly_its_row_of_the_mode_table(cog, bot, lead, mode, state):
    """Checklist 3 and 12: `on` is not offered where arming would be refused, it is absent."""
    if state != "test_channel":
        await bot.store.set(GUILD, "staff_channel_id", STAFF_CHANNEL)
    if state == "armable":
        give_staff(bot, channel_id=STAFF_CHANNEL)
    await bot.store.set(GUILD, "automod_mode", mode)

    embed, view = await automod_cog.build_root(bot, bot.guild)

    offered = [one.value for one in options(view, automod_cog.MODE_PLACEHOLDER)]
    if state == "armable":
        assert offered == ["off", "shadow", "on"]
        assert "still the test channel" not in embed.description
        assert "cannot work out who counts as staff" not in embed.description
    else:
        assert offered == ["off", "shadow"]
        wanted = (
            "still the test channel" if state == "test_channel" else "cannot work out who counts"
        )
        assert wanted in embed.description
    assert [one.default for one in options(view, automod_cog.MODE_PLACEHOLDER)].count(True) <= 1
    assert ("No staff roles resolve" in embed.description) == (
        mode == "on" and state != "armable"
    )


async def test_the_panel_says_out_loud_when_every_rule_is_off(cog, bot, lead):
    book = {name: {"enabled": False} for name in RULE_ORDER}
    await bot.store.set(GUILD, "automod_rules", book)

    embed, _view = await automod_cog.build_root(bot, bot.guild)

    assert "Every rule is off" in embed.description

    await bot.store.set(GUILD, "automod_rules", {})
    again, _view = await automod_cog.build_root(bot, bot.guild)
    assert "Every rule is off" not in again.description


async def test_there_is_no_site_button_when_there_is_nowhere_to_send_anybody(bot):
    bot.settings = bot.settings.model_copy(update={"site_origin": ""})

    _embed, view = await automod_cog.build_root(bot, bot.guild)

    assert not has(view, "Open on the site")


@pytest.mark.parametrize("name", list(RULE_ORDER))
async def test_a_rule_card_offers_one_spelling_of_each_move_and_says_how_it_counts(bot, name):
    embed, view = automod_cog.build_card(bot, bot.guild, name)
    cfg = rule_config(bot.store.get(GUILD, "automod_rules"), name)

    assert f"**{name}**" in embed.description
    assert RULE_HELP[name] in embed.description
    assert ("one message at a time" in embed.description) == (cfg["window_s"] == 0)
    assert has(view, "Turn it off") is cfg["enabled"]
    assert has(view, "Turn it on") is not cfg["enabled"]
    assert has(view, "Log only") is bool(cfg["actions"])
    assert has(view, "Words…") is (name == "bad_words")
    assert labels(view)[-1] == "Back"
    assert placeholders(view) == [automod_cog.WHAT_IT_DOES]
    assert len([one for one in view.children if getattr(one, "label", None)]) <= 5


async def test_the_rule_picker_opens_the_card_and_back_returns_to_the_panel(cog, bot, lead):
    interaction = await open_panel(cog, bot, lead)
    root = interaction.view

    await pick(control(root, automod_cog.PICK_A_RULE), ["mention_spam"], interaction)

    assert root.replaced is True
    card = interaction.view
    assert card.rule_name == "mention_spam"

    await button(card, "Back").callback(interaction)

    assert card.replaced is True
    assert placeholders(interaction.view) == [
        automod_cog.PICK_A_RULE,
        automod_cog.MODE_PLACEHOLDER,
    ]


async def test_turning_a_rule_off_flips_the_button_and_leaves_one_log_row(cog, bot, lead, db):
    _embed, card = automod_cog.build_card(bot, bot.guild, "mention_spam")
    interaction = FakeInteraction(bot, lead)

    await button(card, "Turn it off").callback(interaction)

    assert bot.store.get(GUILD, "automod_rules")["mention_spam"]["enabled"] is False
    assert has(interaction.view, "Turn it on") and not has(interaction.view, "Turn it off")
    assert (await action_kinds(db)).count("automod.rule") == 1


async def test_log_only_clears_the_actions_and_then_stops_being_offered(cog, bot, lead):
    _embed, card = automod_cog.build_card(bot, bot.guild, "mention_spam")
    interaction = FakeInteraction(bot, lead)

    await button(card, "Log only").callback(interaction)

    assert bot.store.get(GUILD, "automod_rules")["mention_spam"]["actions"] == []
    assert not has(interaction.view, "Log only")


async def test_the_actions_picker_is_the_other_door_onto_the_same_move(cog, bot, lead):
    _embed, card = automod_cog.build_card(bot, bot.guild, "mention_spam")
    interaction = FakeInteraction(bot, lead)
    picker = control(card, automod_cog.WHAT_IT_DOES)

    assert [one.default for one in picker.options] == [True, True, True]

    await pick(picker, ["warn"], interaction)

    assert bot.store.get(GUILD, "automod_rules")["mention_spam"]["actions"] == ["warn"]

    await pick(control(interaction.view, automod_cog.WHAT_IT_DOES), [], interaction)

    assert bot.store.get(GUILD, "automod_rules")["mention_spam"]["actions"] == []


async def test_the_numbers_modal_arrives_full_and_writes_nothing_when_one_field_is_refused(
    cog, bot, lead, db
):
    _embed, card = automod_cog.build_card(bot, bot.guild, "mention_spam")
    interaction = FakeInteraction(bot, lead)

    await button(card, "Change the numbers…").callback(interaction)
    modal = interaction.response.modals[0]

    assert [str(item.default) for item, _key in modal.fields()] == ["30", "5", "300"]
    assert "0 = one message" in modal.window.label

    modal.window._value = "abc"
    modal.threshold._value = "9"
    modal.timeout._value = "60"
    refused = FakeInteraction(bot, lead)
    await modal.on_submit(refused)

    assert "whole number" in refused.sent
    assert refused.edits == []
    rule = bot.store.get(GUILD, "automod_rules")["mention_spam"]
    assert (rule["window_s"], rule["threshold"], rule["timeout_s"]) == (30, 5, 300)
    assert "automod.rule" not in await action_kinds(db)


async def test_a_number_the_engine_bounds_is_refused_in_words_and_saves_nothing(cog, bot, lead):
    _embed, card = automod_cog.build_card(bot, bot.guild, "mention_spam")
    opening = FakeInteraction(bot, lead)
    await button(card, "Change the numbers…").callback(opening)
    modal = opening.response.modals[0]
    modal.window._value = "4000"
    modal.threshold._value = "5"
    modal.timeout._value = "300"
    interaction = FakeInteraction(bot, lead)

    await modal.on_submit(interaction)

    assert "between 0 and 3600" in interaction.sent
    assert interaction.edits == []
    assert bot.store.get(GUILD, "automod_rules")["mention_spam"]["window_s"] == 30


async def test_the_caps_card_asks_for_a_percent_and_refuses_a_count(cog, bot, lead):
    _embed, card = automod_cog.build_card(bot, bot.guild, "caps")
    opening = FakeInteraction(bot, lead)
    await button(card, "Change the numbers…").callback(opening)
    modal = opening.response.modals[0]

    assert modal.threshold.label == "Percent capitals, 1–100"

    modal.window._value = "0"
    modal.threshold._value = "200"
    modal.timeout._value = "0"
    interaction = FakeInteraction(bot, lead)
    await modal.on_submit(interaction)

    assert "between 1 and 100" in interaction.sent
    assert bot.store.get(GUILD, "automod_rules")["caps"]["threshold"] == 70


async def test_the_words_box_arrives_full_and_one_per_line_saves_them_all(cog, bot, lead):
    book = dict(bot.store.get(GUILD, "automod_rules"))
    book["bad_words"] = {"words": ["grifter"]}
    await bot.store.set(GUILD, "automod_rules", book)
    _embed, card = automod_cog.build_card(bot, bot.guild, "bad_words")
    opening = FakeInteraction(bot, lead)

    await button(card, "Words…").callback(opening)
    modal = opening.response.modals[0]

    assert modal.words.default == "grifter"

    modal.words._value = "grifter\nwrecker\nscab"
    interaction = FakeInteraction(bot, lead)
    await modal.on_submit(interaction)

    assert bot.store.get(GUILD, "automod_rules")["bad_words"]["words"] == [
        "grifter",
        "wrecker",
        "scab",
    ]


async def test_a_word_list_too_long_for_the_box_says_to_use_the_website(cog, bot, lead):
    book = dict(bot.store.get(GUILD, "automod_rules"))
    book["bad_words"] = {"words": [f"{one}{'x' * 60}" for one in range(100)]}
    await bot.store.set(GUILD, "automod_rules", book)
    _embed, card = automod_cog.build_card(bot, bot.guild, "bad_words")
    interaction = FakeInteraction(bot, lead)

    await button(card, "Words…").callback(interaction)

    assert interaction.response.modals == []
    assert "dashboard" in interaction.sent


async def test_more_words_than_the_engine_holds_is_refused_in_words(cog, bot, lead):
    _embed, card = automod_cog.build_card(bot, bot.guild, "bad_words")
    opening = FakeInteraction(bot, lead)
    await button(card, "Words…").callback(opening)
    modal = opening.response.modals[0]
    modal.words._value = "\n".join(str(one) for one in range(300))
    interaction = FakeInteraction(bot, lead)

    await modal.on_submit(interaction)

    assert "more than 200 words" in interaction.sent
    assert bot.store.get(GUILD, "automod_rules")["bad_words"]["words"] == []


async def test_arming_from_the_panel_asks_once_more_and_only_then_writes(cog, bot, lead, db):
    await armable(bot)
    _embed, root = await automod_cog.build_root(bot, bot.guild)
    interaction = FakeInteraction(bot, lead)

    await pick(control(root, automod_cog.MODE_PLACEHOLDER), ["on"], interaction)

    assert bot.store.get(GUILD, "automod_mode") == "shadow"
    confirm = interaction.view
    assert labels(confirm) == ["Yes, arm it", "Keep it in shadow"]
    assert "Are you sure?" in [one.name for one in interaction.embed.fields]

    await button(confirm, "Yes, arm it").callback(interaction)

    assert bot.store.get(GUILD, "automod_mode") == "on"
    assert (await action_kinds(db)).count("automod.mode") == 1


async def test_keeping_it_in_shadow_changes_nothing_and_goes_back(cog, bot, lead, db):
    await armable(bot)
    _embed, root = await automod_cog.build_root(bot, bot.guild)
    interaction = FakeInteraction(bot, lead)
    await pick(control(root, automod_cog.MODE_PLACEHOLDER), ["on"], interaction)

    await button(interaction.view, "Keep it in shadow").callback(interaction)

    assert bot.store.get(GUILD, "automod_mode") == "shadow"
    assert await action_kinds(db) == []
    assert placeholders(interaction.view) == [
        automod_cog.PICK_A_RULE,
        automod_cog.MODE_PLACEHOLDER,
    ]


async def test_going_quieter_never_asks_twice(cog, bot, lead, db):
    await armable(bot)
    _embed, root = await automod_cog.build_root(bot, bot.guild)
    interaction = FakeInteraction(bot, lead)

    await pick(control(root, automod_cog.MODE_PLACEHOLDER), ["off"], interaction)

    assert bot.store.get(GUILD, "automod_mode") == "off"
    assert (await action_kinds(db)).count("automod.mode") == 1
    assert "Automod is now **off**." == interaction.sent


async def test_the_confirm_can_be_turned_off_and_then_arming_is_one_press(cog, bot, lead):
    await armable(bot)
    await bot.store.set(GUILD, "automod_arm_needs_confirm", False)
    _embed, root = await automod_cog.build_root(bot, bot.guild)
    interaction = FakeInteraction(bot, lead)

    await pick(control(root, automod_cog.MODE_PLACEHOLDER), ["on"], interaction)

    assert bot.store.get(GUILD, "automod_mode") == "on"


async def test_arming_is_refused_by_the_same_answer_the_picker_read(cog, bot, lead, db):
    """The website can still write `on`; `set_mode` refuses it with the sentence, not silently."""
    said = await automod_cog.set_mode(bot, bot.guild, "on", lead)

    assert "still the test channel" in said
    assert bot.store.get(GUILD, "automod_mode") == "shadow"

    await bot.store.set(GUILD, "staff_channel_id", STAFF_CHANNEL)
    said = await automod_cog.set_mode(bot, bot.guild, "on", lead)

    assert "cannot work out who counts as staff" in said
    assert bot.store.get(GUILD, "automod_mode") == "shadow"
    assert await action_kinds(db) == []

    give_staff(bot, channel_id=STAFF_CHANNEL)
    said = await automod_cog.set_mode(bot, bot.guild, "on", lead)

    assert bot.store.get(GUILD, "automod_mode") == "on" and "**on**" in said
    assert await action_kinds(db) == ["automod.mode"]


async def test_a_mode_written_from_the_website_takes_the_web_head_and_says_so(bot, lead, db):
    await armable(bot)

    await automod_cog.set_mode(bot, bot.guild, "off", lead, via="website")

    assert await action_kinds(db) == ["web.automod.mode"]


async def test_exemptions_add_both_kinds_and_take_them_off_one_select(cog, bot, lead, db):
    role = give_staff(bot, role_id=EXEMPT_ROLE)
    channel = bot.guild.get_channel(ELSEWHERE)
    interaction = FakeInteraction(bot, lead)
    _embed, root = await automod_cog.build_root(bot, bot.guild)

    await button(root, "Exemptions…").callback(interaction)
    page = interaction.view

    assert automod_cog.REMOVE_PLACEHOLDER not in placeholders(page)
    assert placeholders(page) == [automod_cog.ADD_ROLE, automod_cog.ADD_CHANNEL]

    await pick(control(page, automod_cog.ADD_ROLE), [role], interaction)
    await pick(control(interaction.view, automod_cog.ADD_CHANNEL), [channel], interaction)

    assert bot.store.get(GUILD, "automod_exempt_role_ids") == [EXEMPT_ROLE]
    assert bot.store.get(GUILD, "automod_exempt_channel_ids") == [ELSEWHERE]
    removal = control(interaction.view, automod_cog.REMOVE_PLACEHOLDER)
    assert [one.value for one in removal.options] == [
        f"role:{EXEMPT_ROLE}",
        f"channel:{ELSEWHERE}",
    ]
    assert [one.label for one in removal.options] == [
        f"role — {role.name}",
        f"channel — #{channel.name}",
    ]

    await pick(removal, [f"role:{EXEMPT_ROLE}"], interaction)

    assert bot.store.get(GUILD, "automod_exempt_role_ids") == []
    kinds = await action_kinds(db)
    assert kinds == ["automod.exempt_add", "automod.exempt_add", "automod.exempt_remove"]


async def test_adding_the_same_exemption_twice_changes_nothing_and_says_so(cog, bot, lead, db):
    await bot.store.set(GUILD, "automod_exempt_role_ids", [EXEMPT_ROLE])

    said = await automod_cog.set_exempt(bot, bot.guild, "role", EXEMPT_ROLE, lead, add=True)

    assert "was already exempt" in said
    assert bot.store.get(GUILD, "automod_exempt_role_ids") == [EXEMPT_ROLE]
    assert await action_kinds(db) == []

    gone = await automod_cog.set_exempt(bot, bot.guild, "channel", ELSEWHERE, lead, add=False)

    assert "was already not exempt" in gone
    assert await action_kinds(db) == []


async def test_something_discord_no_longer_has_is_still_offered_for_removal(cog, bot, lead):
    await bot.store.set(GUILD, "automod_exempt_role_ids", [4242])

    _embed, page = automod_cog.build_exemptions(bot, bot.guild)
    removal = control(page, automod_cog.REMOVE_PLACEHOLDER)

    assert [one.label for one in removal.options] == ["a role Discord no longer has (4242)"]

    interaction = FakeInteraction(bot, lead)
    await pick(removal, ["role:4242"], interaction)

    assert bot.store.get(GUILD, "automod_exempt_role_ids") == []


async def test_the_honeypots_are_named_as_never_read_and_are_not_on_the_removal_select(bot):
    embed, page = automod_cog.build_exemptions(bot, bot.guild)

    assert f"<#{HONEYPOT}>" in embed.description
    assert "the honeypot owns them" in embed.description
    assert automod_cog.REMOVE_PLACEHOLDER not in placeholders(page)


async def test_the_settings_page_says_what_it_owns_and_what_the_site_owns(cog, bot, lead, db):
    interaction = FakeInteraction(bot, lead)
    _embed, root = await automod_cog.build_root(bot, bot.guild)

    await button(root, "Settings…").callback(interaction)
    page = interaction.view

    assert "**this panel stays live** — 10 minute(s)" in interaction.embed.description
    assert "Moderation page" in interaction.embed.description
    assert labels(page) == ["Numbers…", "Stop asking before arming", "Back"]

    await button(page, "Stop asking before arming").callback(interaction)

    assert bot.store.get(GUILD, "automod_arm_needs_confirm") is False
    assert has(interaction.view, "Ask before arming")
    assert (await action_kinds(db)).count("automod.settings") == 1


async def test_the_panel_minutes_modal_refuses_nonsense_and_saves_a_number(cog, bot, lead):
    _embed, page = automod_cog.build_settings(bot, bot.guild)
    opening = FakeInteraction(bot, lead)

    await button(page, "Numbers…").callback(opening)
    modal = opening.response.modals[0]

    assert modal.stays.default == "10"

    modal.stays._value = "0"
    refused = FakeInteraction(bot, lead)
    await modal.on_submit(refused)

    assert "is not a whole number" in refused.sent
    assert bot.store.get(GUILD, "automod_panel_minutes") == 10

    modal.stays._value = "25"
    saved = FakeInteraction(bot, lead)
    await modal.on_submit(saved)

    assert bot.store.get(GUILD, "automod_panel_minutes") == 25
    assert automod_cog.minutes_for(bot, GUILD) == 25


async def test_logs_answers_a_new_message_and_leaves_the_panel_where_it_is(cog, bot, lead, db):
    give_staff(bot)
    interaction = await open_panel(cog, bot, lead)
    root = interaction.view

    await button(root, "Logs").callback(interaction)

    assert root.replaced is False
    assert interaction.edits == []
    assert len(interaction.response.messages) == 2


async def test_a_staffer_demoted_mid_panel_moves_nothing_at_all(cog, bot, lead, db):
    _embed, root = await automod_cog.build_root(bot, bot.guild)
    _embed, card = automod_cog.build_card(bot, bot.guild, "mention_spam")
    _embed, page = automod_cog.build_exemptions(bot, bot.guild)
    bot.store.is_staff = lambda who: False

    for control_and_args in (
        (button(root, "Exemptions…").callback,),
        (button(root, "Settings…").callback,),
        (button(root, "Refresh").callback,),
        (button(card, "Turn it off").callback,),
        (button(card, "Change the numbers…").callback,),
        (button(page, "Back").callback,),
    ):
        interaction = FakeInteraction(bot, lead)
        await control_and_args[0](interaction)
        assert "staff only" in interaction.sent
        assert interaction.edits == [] and interaction.response.modals == []

    picking = FakeInteraction(bot, lead)
    await pick(control(root, automod_cog.PICK_A_RULE), ["caps"], picking)
    assert "staff only" in picking.sent and picking.edits == []

    moding = FakeInteraction(bot, lead)
    await pick(control(root, automod_cog.MODE_PLACEHOLDER), ["off"], moding)
    assert "staff only" in moding.sent
    assert bot.store.get(GUILD, "automod_rules")["mention_spam"]["enabled"] is True
    assert bot.store.get(GUILD, "automod_mode") == "shadow"


async def test_every_click_re_checks_the_database_after_the_defer(cog, bot, lead):
    _embed, root = await automod_cog.build_root(bot, bot.guild)
    _embed, card = automod_cog.build_card(bot, bot.guild, "mention_spam")
    bot.db = SimpleNamespace(is_connected=False, conn=bot.db.conn)

    for click in (
        button(root, "Exemptions…").callback,
        button(root, "Settings…").callback,
        button(card, "Turn it off").callback,
    ):
        interaction = FakeInteraction(bot, lead)
        await click(interaction)
        assert interaction.response.messages[0].get("deferred") is True
        assert "cannot reach its own database" in interaction.sent
        assert interaction.edits == []

    modal = FakeInteraction(bot, lead)
    await button(card, "Change the numbers…").callback(modal)
    assert modal.response.modals == [] and "cannot reach its own database" in modal.sent
    assert bot.store.get(GUILD, "automod_rules")["mention_spam"]["enabled"] is True


async def test_every_message_that_fed_the_window_is_deleted(cog, bot, spammer, db):
    await bot.store.set(GUILD, "automod_mode", "on")
    book = dict(bot.store.get(GUILD, "automod_rules"))
    book["mention_spam"] = {"threshold": 6}
    await bot.store.set(GUILD, "automod_rules", book)
    channel = bot.guild.get_channel(TEST_CHANNEL)
    first = FakePost(bot.guild, spammer, channel, content="one", mentions=(1, 2, 3), message_id=5)
    second = FakePost(bot.guild, spammer, channel, content="two", mentions=(4, 5, 6), message_id=6)
    channel.sent_messages[first.id] = first

    await cog.on_message(first)
    await cog.on_message(second)

    assert first.deleted is True and second.deleted is True
    assert "automod.deleted" in await action_kinds(db)


async def test_a_message_that_cannot_be_found_again_is_logged_not_fatal(cog, bot, spammer, db):
    await bot.store.set(GUILD, "automod_mode", "on")
    channel = bot.guild.get_channel(TEST_CHANNEL)
    post = spam(bot, spammer)
    gone = FakePost(bot.guild, spammer, channel, content="gone", mentions=(9,), message_id=6)
    gone.delete_raises = refused()
    channel.sent_messages[gone.id] = gone

    await cog.on_message(gone)
    await cog.on_message(post)

    kinds = await action_kinds(db)
    assert "automod.delete_failed" in kinds and "automod.deleted" in kinds


async def test_an_apology_after_the_verdict_is_not_a_second_verdict(cog, bot, spammer, db):
    await cog.on_message(spam(bot, spammer))
    assert len(await cases(db)) == 1

    await cog.on_message(
        FakePost(
            bot.guild,
            spammer,
            bot.guild.get_channel(TEST_CHANNEL),
            content="sorry everyone",
            message_id=6,
        )
    )

    assert len(await cases(db)) == 1


async def test_an_edit_is_read_as_a_new_fact_only_when_the_words_changed(cog, bot, spammer, db):
    quiet = FakePost(
        bot.guild, spammer, bot.guild.get_channel(TEST_CHANNEL), content="hello", message_id=5
    )
    loud = spam(bot, spammer, message_id=5)

    await cog.on_message_edit(quiet, quiet)
    assert await cases(db) == []

    await cog.on_message_edit(quiet, loud)
    assert len(await cases(db)) == 1


async def test_staff_is_resolved_once_a_minute_not_once_a_message(cog, bot, spammer):
    give_staff(bot)
    seen = []
    original = bot.store.staff_role_ids
    bot.store.staff_role_ids = lambda guild: seen.append(guild.id) or original(guild)

    await cog.on_message(spam(bot, spammer, message_id=5))
    await cog.on_message(spam(bot, spammer, message_id=6))

    assert len(seen) == 1


async def test_the_cog_registers_its_button_on_load(cog, bot):
    await cog.cog_load()

    assert ApplyNowButton in bot.dynamic
