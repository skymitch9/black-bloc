import asyncio
import re
from datetime import UTC, datetime, timedelta

import discord
import pytest

from black_bloc.cogs.moderation.automod import (
    APPLY_TEMPLATE,
    ApplyNowButton,
    AutoMod,
    apply_custom_id,
    user_lock,
)
from black_bloc.config import load_settings
from black_bloc.modcases import add_case, get_case
from black_bloc.settings_store import SettingsStore
from black_bloc.storage.db import Database

GUILD = 7
TEST_CHANNEL = 111
LOG_CHANNEL = 222
ELSEWHERE = 444
HONEYPOT = 555
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


def forbidden():
    return discord.Forbidden(_Response(403), "no")


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


class FakeChannel:
    def __init__(self, channel_id, name="channel", parent_id=None):
        self.id = channel_id
        self.name = name
        self.mention = f"<#{channel_id}>"
        self.parent_id = parent_id
        self.visible_to = set()
        self.messages = []
        self.history_items = []
        self.history_raises = None

    def permissions_for(self, role):
        return FakePerms(view_channel=role.id in self.visible_to)

    async def send(self, content=None, **kwargs):
        message = FakeMessage(len(self.messages) + 1, content or "", **kwargs)
        self.messages.append(message)
        return message

    def history(self, limit=None, after=None):
        items = list(self.history_items)
        raises = self.history_raises

        async def walk():
            if raises is not None:
                raise raises
            for item in items:
                yield item

        return walk()


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


class FakeEmbed:
    def __init__(self, description):
        self.description = description
        self.title = ""
        self.fields = []
        self.footer = None


class FakeCarlPost:
    def __init__(self, user_id, at):
        self.content = f"Case for member (ID: {user_id})"
        self.embeds = []
        self.created_at = at


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


def give_staff(bot, role_id=STAFF_ROLE):
    role = FakeRole(role_id)
    bot.guild.roles.append(role)
    bot.guild.get_channel(TEST_CHANNEL).visible_to.add(role_id)
    return role


def spam(bot, author, channel_id=TEST_CHANNEL, message_id=5):
    return FakePost(
        bot.guild,
        author,
        bot.guild.get_channel(channel_id),
        content="@here @there",
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
    assert spammer.dms and "warned by the automatic filter" in spammer.dms[0]
    assert [r["applied"] for r in await cases(db)] == [1]
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
    assert [r["applied"] for r in await cases(db)] == [0]


async def test_a_message_that_cannot_be_deleted_is_still_acted_on(cog, bot, spammer, db):
    await bot.store.set(GUILD, "automod_mode", "on")
    post = spam(bot, spammer)
    post.delete_raises = refused()

    await cog.on_message(post)

    kinds = await action_kinds(db)
    assert "automod.delete_failed" in kinds and "automod.timed_out" in kinds
    assert spammer.timeouts != []


async def test_a_log_only_rule_records_a_case_with_no_button(cog, bot, spammer, db):
    book = dict(bot.store.get(GUILD, "automod_rules"))
    book["mention_spam"] = {"enabled": False}
    await bot.store.set(GUILD, "automod_rules", book)
    post = FakePost(
        bot.guild, spammer, bot.guild.get_channel(TEST_CHANNEL), content="https://example.com"
    )

    await cog.on_message(post)

    assert [r["kind"] for r in await cases(db)] == ["automod"]
    assert await action_kinds(db) == ["automod.detected"]
    assert cards(bot)[-1].kwargs.get("view") is None


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


async def test_the_apply_button_is_staff_only(bot, spammer, db):
    case_id = await add_case(
        db, GUILD, USER, "automod", reason="5 mentions in 30s", duration_s=300,
        mode="shadow", applied=False,
    )

    await ApplyNowButton(case_id).callback(FakeInteraction(bot, spammer))

    assert spammer.timeouts == [] and (await get_case(db, case_id))["applied"] == 0


async def test_the_apply_button_times_the_member_out(bot, spammer, lead, db):
    case_id = await add_case(
        db, GUILD, USER, "automod", reason="5 mentions in 30s", duration_s=300,
        mode="shadow", applied=False,
    )
    interaction = FakeInteraction(bot, lead)

    await ApplyNowButton(case_id).callback(interaction)

    assert spammer.timeouts and spammer.timeouts[0][0] == timedelta(seconds=300)
    assert spammer.dms != []
    assert (await get_case(db, case_id))["applied"] == 1
    assert "Applied case" in interaction.sent
    kinds = await action_kinds(db)
    assert "automod.warned" in kinds and "automod.timed_out" in kinds


async def test_the_apply_button_refuses_in_test_mode_with_a_sentence(bot, spammer, lead, db):
    bot.guard = FakeGuard()
    case_id = await add_case(
        db, GUILD, USER, "automod", duration_s=300, mode="shadow", applied=False
    )
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


async def test_arming_automod_is_refused_while_no_staff_role_resolves(cog, bot, lead):
    interaction = FakeInteraction(bot, lead)

    await cog.mode.callback(
        cog, interaction, discord.app_commands.Choice(name="on", value="on")
    )

    assert bot.store.get(GUILD, "automod_mode") == "shadow"
    assert "staff_channel_id" in interaction.sent

    give_staff(bot)
    again = FakeInteraction(bot, lead)
    await cog.mode.callback(cog, again, discord.app_commands.Choice(name="on", value="on"))
    assert bot.store.get(GUILD, "automod_mode") == "on"


async def test_status_names_the_mode_the_staff_and_every_rule(cog, bot, lead, db):
    role = give_staff(bot)
    await add_case(db, GUILD, USER, "automod", mode="shadow", applied=False)
    interaction = FakeInteraction(bot, lead)

    await cog.status.callback(cog, interaction)

    assert "**mode** — shadow" in interaction.sent
    assert role.name in interaction.sent
    assert "**mention_spam** — on · 5 in 30s · delete, warn, timeout (300s)" in interaction.sent
    assert "**caps** — off" in interaction.sent
    assert "1 logged only" in interaction.sent


async def test_status_warns_loudly_when_armed_with_no_staff(cog, bot, lead):
    await bot.store.set(GUILD, "automod_mode", "on")
    interaction = FakeInteraction(bot, lead)

    await cog.status.callback(cog, interaction)

    assert "No staff roles resolve" in interaction.sent


async def test_a_rule_is_enabled_disabled_and_tuned(cog, bot, lead):
    await cog.rule_disable.callback(cog, FakeInteraction(bot, lead), "mention_spam")
    assert bot.store.get(GUILD, "automod_rules")["mention_spam"]["enabled"] is False

    await cog.rule_enable.callback(cog, FakeInteraction(bot, lead), "mention_spam")
    assert bot.store.get(GUILD, "automod_rules")["mention_spam"]["enabled"] is True

    await cog.rule_set.callback(
        cog,
        FakeInteraction(bot, lead),
        "mention_spam",
        discord.app_commands.Choice(name="threshold", value="threshold"),
        "3",
    )
    assert bot.store.get(GUILD, "automod_rules")["mention_spam"]["threshold"] == 3

    await cog.rule_set.callback(
        cog,
        FakeInteraction(bot, lead),
        "bad_words",
        discord.app_commands.Choice(name="words", value="words"),
        "grifter, wrecker",
    )
    assert bot.store.get(GUILD, "automod_rules")["bad_words"]["words"] == ["grifter", "wrecker"]


async def test_a_rule_change_discord_would_refuse_is_answered_with_a_sentence(cog, bot, lead):
    over = FakeInteraction(bot, lead)
    await cog.rule_set.callback(
        cog, over, "mention_spam",
        discord.app_commands.Choice(name="timeout_s", value="timeout_s"), "9999999",
    )
    assert "between" in over.sent
    assert bot.store.get(GUILD, "automod_rules")["mention_spam"]["timeout_s"] == 300

    nonsense = FakeInteraction(bot, lead)
    await cog.rule_set.callback(
        cog, nonsense, "mention_spam",
        discord.app_commands.Choice(name="threshold", value="threshold"), "lots",
    )
    assert "whole number" in nonsense.sent

    unknown = FakeInteraction(bot, lead)
    await cog.rule_enable.callback(cog, unknown, "shouting")
    assert "not one of" in unknown.sent

    wrong_field = FakeInteraction(bot, lead)
    await cog.rule_set.callback(
        cog, wrong_field, "mention_spam",
        discord.app_commands.Choice(name="words", value="words"), "a, b",
    )
    assert "not something an automod rule has" in wrong_field.sent


async def test_a_rule_command_is_staff_only(cog, bot, spammer):
    interaction = FakeInteraction(bot, spammer)

    await cog.rule_disable.callback(cog, interaction, "mention_spam")

    assert bot.store.get(GUILD, "automod_rules")["mention_spam"]["enabled"] is True
    assert "staff only" in interaction.sent


async def test_exempt_roles_and_channels_are_added_and_removed(cog, bot, lead, db):
    role = FakeRole(EXEMPT_ROLE)
    channel = bot.guild.get_channel(ELSEWHERE)

    await cog.exempt_add.callback(cog, FakeInteraction(bot, lead), role, channel)
    assert bot.store.get(GUILD, "automod_exempt_role_ids") == [EXEMPT_ROLE]
    assert bot.store.get(GUILD, "automod_exempt_channel_ids") == [ELSEWHERE]

    again = FakeInteraction(bot, lead)
    await cog.exempt_add.callback(cog, again, role, None)
    assert "already exempt" in again.sent

    await cog.exempt_remove.callback(cog, FakeInteraction(bot, lead), role, channel)
    assert bot.store.get(GUILD, "automod_exempt_role_ids") == []
    assert bot.store.get(GUILD, "automod_exempt_channel_ids") == []

    empty = FakeInteraction(bot, lead)
    await cog.exempt_add.callback(cog, empty, None, None)
    assert "Name a role or a channel" in empty.sent
    assert "automod.exempt_add" in await action_kinds(db)


async def test_parity_counts_agreement_against_carls_log(cog, bot, lead, db):
    carl_channel = bot.guild.add(FakeChannel(999, name="carlbot-logs"))
    await bot.store.set(GUILD, "carl_modlog_channel_id", 999)
    await add_case(db, GUILD, SNOWFLAKE, "automod", mode="shadow", applied=False)
    carl_channel.history_items = [FakeCarlPost(SNOWFLAKE, datetime.now(UTC))]
    interaction = FakeInteraction(bot, lead)

    await cog.parity.callback(cog, interaction, 7)

    assert "**1** agree" in interaction.sent
    assert "**0** Carl-only" in interaction.sent
    assert "**0** Bloc-only" in interaction.sent


async def test_parity_says_what_it_needs_when_discord_refuses_the_history(cog, bot, lead, db):
    carl_channel = bot.guild.add(FakeChannel(999, name="carlbot-logs"))
    await bot.store.set(GUILD, "carl_modlog_channel_id", 999)
    carl_channel.history_raises = forbidden()
    interaction = FakeInteraction(bot, lead)

    await cog.parity.callback(cog, interaction, 7)

    assert "Read Message History" in interaction.sent
    assert "<#999>" in interaction.sent


async def test_parity_says_so_when_it_cannot_see_carls_log_at_all(cog, bot, lead):
    await bot.store.set(GUILD, "carl_modlog_channel_id", 12345)
    interaction = FakeInteraction(bot, lead)

    await cog.parity.callback(cog, interaction, 7)

    assert "carl_modlog_channel_id" in interaction.sent


async def test_parity_defers_before_reading_history(cog, bot, lead):
    bot.guild.add(FakeChannel(999, name="carlbot-logs"))
    await bot.store.set(GUILD, "carl_modlog_channel_id", 999)
    interaction = FakeInteraction(bot, lead)

    await cog.parity.callback(cog, interaction, 7)

    assert interaction.response.messages[0].get("deferred") is True


async def test_the_cog_registers_its_button_on_load(cog, bot):
    await cog.cog_load()

    assert ApplyNowButton in bot.dynamic
