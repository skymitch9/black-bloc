from datetime import timedelta

import discord
import pytest

from black_bloc.cogs.moderation.modcmds import ModCommands
from black_bloc.config import load_settings
from black_bloc.modcases import CASES_PER_PAGE, add_case
from black_bloc.settings_store import SettingsStore
from black_bloc.storage.db import Database

GUILD = 7
TEST_CHANNEL = 111
LOG_CHANNEL = 222
STAFF_ROLE = 600
USER = 900
BOT_ID = 42


class _Response:
    def __init__(self, status):
        self.status = status
        self.reason = "refused"


def refused():
    return discord.HTTPException(_Response(403), "no")


def not_found():
    return discord.NotFound(_Response(404), "gone")


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
    def __init__(self, channel_id, name="channel"):
        self.id = channel_id
        self.name = name
        self.mention = f"<#{channel_id}>"
        self.visible_to = set()
        self.messages = []
        self.purged = []
        self.purge_raises = None

    def permissions_for(self, role):
        return FakePerms(view_channel=role.id in self.visible_to)

    async def send(self, content=None, **kwargs):
        message = FakeMessage(len(self.messages) + 1, content or "", **kwargs)
        self.messages.append(message)
        return message

    async def purge(self, limit=None, check=None):
        if self.purge_raises is not None:
            raise self.purge_raises
        self.purged.append((limit, check))
        return [object()] * min(limit or 0, 3)


class FakeGuild:
    def __init__(self):
        self.id = GUILD
        self.name = "Black Bloc"
        self.channels = {}
        self.members = {}
        self.roles = []
        self.default_role = FakeRole(GUILD)
        self.kicked = []
        self.bans = []
        self.unbans = []
        self.kick_raises = None
        self.ban_raises = None
        self.unban_raises = None

    def add(self, channel):
        channel.guild = self
        self.channels[channel.id] = channel
        return channel

    def get_channel(self, channel_id):
        return self.channels.get(channel_id)

    def get_member(self, user_id):
        return self.members.get(user_id)

    async def kick(self, member, reason=None):
        if self.kick_raises is not None:
            raise self.kick_raises
        self.kicked.append((member.id, reason))

    async def ban(self, member, reason=None, delete_message_seconds=None):
        if self.ban_raises is not None:
            raise self.ban_raises
        self.bans.append((member.id, reason, delete_message_seconds))

    async def unban(self, user, reason=None):
        if self.unban_raises is not None:
            raise self.unban_raises
        self.unbans.append((user.id, reason))


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


class FakeGuard:
    def __init__(self, test_channel_id=TEST_CHANNEL):
        self.test_channel_id = test_channel_id

    def allows_channel(self, channel_id):
        return channel_id == self.test_channel_id


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

    def get_channel(self, channel_id):
        return self.guild.get_channel(channel_id)


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
        self.channel = bot.guild.get_channel(channel_id)
        self.response = FakeResponse()
        self.followup = FakeFollowup(self.response)

    @property
    def sent(self):
        return self.response.messages[-1]["content"] if self.response.messages else None

    @property
    def embed(self):
        return self.response.messages[-1].get("embed")


async def action_kinds(db):
    cur = await db.conn.execute("SELECT kind FROM action_log ORDER BY id")
    return [row["kind"] for row in await cur.fetchall()]


async def cases(db):
    cur = await db.conn.execute("SELECT * FROM mod_cases ORDER BY id")
    return list(await cur.fetchall())


def cards(bot):
    return [m for m in bot.guild.get_channel(TEST_CHANNEL).messages if "embed" in m.kwargs]


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
    settings = load_settings(_env_file=None, test_mode=True, test_channel_id=TEST_CHANNEL)
    store = SettingsStore(db, settings)
    await store.load()
    await store.set(GUILD, "log_channel_id", LOG_CHANNEL)
    await store.set(GUILD, "modlog_channel_id", TEST_CHANNEL)
    guild = FakeGuild()
    guild.add(FakeChannel(TEST_CHANNEL, name="test"))
    guild.add(FakeChannel(LOG_CHANNEL, name="log"))
    return FakeBot(db, store, settings, guild)


@pytest.fixture
def cog(bot):
    return ModCommands(bot)


@pytest.fixture
def target(bot):
    return FakeMember(bot.guild)


@pytest.fixture
def lead(bot):
    return FakeMember(bot.guild, user_id=1, manage_guild=True)


async def test_warn_is_allowed_in_test_mode_and_dms_the_reason(cog, bot, lead, target, db):
    bot.guard = FakeGuard()
    interaction = FakeInteraction(bot, lead)

    await cog.warn.callback(cog, interaction, target, "stop that")

    rows = await cases(db)
    assert [(r["kind"], r["applied"], r["moderator_id"]) for r in rows] == [("warn", 1, lead.id)]
    assert target.dms and "stop that" in target.dms[0]
    assert "mod.warned" in await action_kinds(db)
    assert f"#{rows[0]['id']}" in interaction.sent
    assert cards(bot)[-1].kwargs["allowed_mentions"].everyone is False


async def test_warn_says_so_at_the_threshold_and_only_logs_it(cog, bot, lead, target, db):
    await bot.store.set(GUILD, "automod_warn_threshold", 2)

    await cog.warn.callback(cog, FakeInteraction(bot, lead), target, "one")
    second = FakeInteraction(bot, lead)
    await cog.warn.callback(cog, second, target, "two")

    assert "threshold of **2**" in second.sent
    assert "mod.warn_threshold" in await action_kinds(db)
    assert [r["kind"] for r in await cases(db)] == ["warn", "warn"]


async def test_the_dm_setting_is_obeyed(cog, bot, lead, target):
    await bot.store.set(GUILD, "mod_dm_on_action", "none")

    await cog.warn.callback(cog, FakeInteraction(bot, lead), target, "quiet")

    assert target.dms == []


async def test_timeout_kick_ban_and_purge_are_refused_in_test_mode(cog, bot, lead, target, db):
    bot.guard = FakeGuard()

    timed = FakeInteraction(bot, lead)
    await cog.timeout.callback(cog, timed, target, "10m", "spam")
    kicked = FakeInteraction(bot, lead)
    await cog.kick.callback(cog, kicked, target, "spam")
    banned = FakeInteraction(bot, lead)
    await cog.ban.callback(cog, banned, target, "spam", 1)
    purged = FakeInteraction(bot, lead)
    await cog.purge.callback(cog, purged, 10, target)

    assert target.timeouts == [] and bot.guild.kicked == [] and bot.guild.bans == []
    assert bot.guild.get_channel(TEST_CHANNEL).purged == []
    for interaction in (timed, kicked, banned, purged):
        assert "test mode" in interaction.sent
    assert [(r["kind"], r["applied"], r["mode"]) for r in await cases(db)] == [
        ("timeout", 0, "test_mode"),
        ("kick", 0, "test_mode"),
        ("ban", 0, "test_mode"),
        ("purge", 0, "test_mode"),
    ]
    assert await action_kinds(db) == [
        "mod.would_timeout",
        "mod.would_kick",
        "mod.would_ban",
        "mod.would_purge",
    ]


async def test_timeout_reads_the_duration_and_clamps_at_twenty_eight_days(cog, bot, lead, target,
                                                                         db):
    interaction = FakeInteraction(bot, lead)

    await cog.timeout.callback(cog, interaction, target, "10m", "spam")

    assert target.timeouts and target.timeouts[0][0] == timedelta(seconds=600)
    assert lead.display_name in target.timeouts[0][1] and "spam" in target.timeouts[0][1]
    assert [(r["kind"], r["duration_s"]) for r in await cases(db)] == [("timeout", 600)]
    assert "mod.timed_out" in await action_kinds(db)

    too_long = FakeInteraction(bot, lead)
    await cog.timeout.callback(cog, too_long, target, "30d", "spam")
    assert "28 days" in too_long.sent
    assert len(target.timeouts) == 1

    nonsense = FakeInteraction(bot, lead)
    await cog.timeout.callback(cog, nonsense, target, "ages", "spam")
    assert "not a length" in nonsense.sent


async def test_a_timeout_discord_refuses_is_its_own_log_kind_and_dms_nobody(cog, bot, lead, target,
                                                                           db):
    target.timeout_raises = refused()
    interaction = FakeInteraction(bot, lead)

    await cog.timeout.callback(cog, interaction, target, "10m", "spam")

    assert "Moderate Members" in interaction.sent
    assert target.dms == []
    kinds = await action_kinds(db)
    assert "mod.timeout_failed" in kinds and "mod.would_timeout" not in kinds
    assert await cases(db) == []


async def test_a_timeout_that_worked_tells_the_member_how_long_it_is(cog, bot, lead, target):
    await cog.timeout.callback(cog, FakeInteraction(bot, lead), target, "10m", "spam")

    assert target.dms and "timed out" in target.dms[0] and "10m" in target.dms[0]


async def test_untimeout_and_unban_are_refused_in_test_mode(cog, bot, lead, target, db):
    bot.guard = FakeGuard()
    lifted = FakeInteraction(bot, lead)
    unbanned = FakeInteraction(bot, lead)

    await cog.untimeout.callback(cog, lifted, target, "sorry")
    await cog.unban.callback(cog, unbanned, "123456789012345678", "appealed")

    assert target.timeouts == [] and bot.guild.unbans == []
    assert "test mode" in lifted.sent and "test mode" in unbanned.sent
    assert [(r["kind"], r["applied"]) for r in await cases(db)] == [
        ("untimeout", 0),
        ("unban", 0),
    ]
    assert await action_kinds(db) == ["mod.would_untimeout", "mod.would_unban"]


async def test_untimeout_lifts_it_once_test_mode_is_off(cog, bot, lead, target, db):
    interaction = FakeInteraction(bot, lead)

    await cog.untimeout.callback(cog, interaction, target, "sorry")

    assert target.timeouts and target.timeouts[0][0] is None
    assert [r["kind"] for r in await cases(db)] == ["untimeout"]
    assert "mod.untimed_out" in await action_kinds(db)


async def test_kick_and_ban_do_the_thing_and_record_the_purge_window(cog, bot, lead, db):
    kicked = FakeMember(bot.guild, user_id=USER + 1)
    banned = FakeMember(bot.guild, user_id=USER + 2)

    await cog.kick.callback(cog, FakeInteraction(bot, lead), kicked, "spam")
    interaction = FakeInteraction(bot, lead)
    await cog.ban.callback(cog, interaction, banned, "spam", 30)

    assert bot.guild.kicked[0][0] == kicked.id
    assert bot.guild.bans[0][0] == banned.id
    assert bot.guild.bans[0][2] == 7 * 86400
    assert "7 day(s)" in interaction.sent
    assert kicked.dms and banned.dms
    assert [r["kind"] for r in await cases(db)] == ["kick", "ban"]
    kinds = await action_kinds(db)
    assert "mod.kicked" in kinds and "mod.banned" in kinds


async def test_a_ban_discord_refuses_never_shares_a_kind_with_a_dry_run(cog, bot, lead, target, db):
    bot.guild.ban_raises = refused()
    interaction = FakeInteraction(bot, lead)

    await cog.ban.callback(cog, interaction, target, "spam", 0)

    assert "Ban Members" in interaction.sent
    kinds = await action_kinds(db)
    assert "mod.ban_failed" in kinds and "mod.would_ban" not in kinds
    assert await cases(db) == []


async def test_unban_takes_an_id_and_says_so_when_there_is_no_ban(cog, bot, lead, db):
    interaction = FakeInteraction(bot, lead)
    await cog.unban.callback(cog, interaction, "123456789012345678", "appealed")
    assert bot.guild.unbans[0][0] == 123456789012345678
    assert [r["kind"] for r in await cases(db)] == ["unban"]
    assert "mod.unbanned" in await action_kinds(db)

    bot.guild.unban_raises = not_found()
    missing = FakeInteraction(bot, lead)
    await cog.unban.callback(cog, missing, "123456789012345678", None)
    assert "not on this server's ban list" in missing.sent

    nonsense = FakeInteraction(bot, lead)
    await cog.unban.callback(cog, nonsense, "somebody", None)
    assert "not a member id" in nonsense.sent


async def test_purge_defers_before_it_deletes_and_refuses_a_silly_number(cog, bot, lead, target,
                                                                        db):
    interaction = FakeInteraction(bot, lead)

    await cog.purge.callback(cog, interaction, 10, target)

    assert interaction.response.messages[0].get("deferred") is True
    limit, check = bot.guild.get_channel(TEST_CHANNEL).purged[0]
    assert limit == 10 and check is not None
    assert [r["kind"] for r in await cases(db)] == ["purge"]
    assert "mod.purged" in await action_kinds(db)

    silly = FakeInteraction(bot, lead)
    await cog.purge.callback(cog, silly, 0, None)
    assert "between 1 and 100" in silly.sent
    assert silly.response.messages[0].get("deferred") is None


async def test_an_untargeted_purge_is_filed_against_the_channel(cog, bot, lead, target, db):
    await cog.purge.callback(cog, FakeInteraction(bot, lead), 5, None)

    rows = await cases(db)
    assert [(r["kind"], r["user_id"], r["channel_id"]) for r in rows] == [
        ("purge", None, TEST_CHANNEL)
    ]
    assert cards(bot)[-1].kwargs["embed"].fields[0].name == "Channel"

    theirs = FakeInteraction(bot, lead)
    await cog.cases.callback(cog, theirs, lead, 1)
    assert "no cases" in theirs.sent


async def test_a_purge_discord_refuses_says_what_it_needs(cog, bot, lead, db):
    bot.guild.get_channel(TEST_CHANNEL).purge_raises = refused()
    interaction = FakeInteraction(bot, lead)

    await cog.purge.callback(cog, interaction, 10, None)

    assert "Manage Messages" in interaction.sent
    assert "mod.purge_failed" in await action_kinds(db)
    assert await cases(db) == []


async def test_case_shows_one_card_and_refuses_another_guilds(cog, bot, lead, db):
    case_id = await add_case(db, GUILD, USER, "warn", moderator_id=lead.id, reason="spam")
    other = await add_case(db, GUILD + 1, USER, "warn", moderator_id=lead.id)
    interaction = FakeInteraction(bot, lead)

    await cog.case.callback(cog, interaction, case_id)
    assert interaction.embed.title == f"Case #{case_id} — warn"

    elsewhere = FakeInteraction(bot, lead)
    await cog.case.callback(cog, elsewhere, other)
    assert "no case" in elsewhere.sent

    missing = FakeInteraction(bot, lead)
    await cog.case.callback(cog, missing, 4242)
    assert "no case" in missing.sent


async def test_cases_pages_and_says_when_there_are_none(cog, bot, lead, target, db):
    empty = FakeInteraction(bot, lead)
    await cog.cases.callback(cog, empty, target, 1)
    assert "no cases" in empty.sent

    for index in range(12):
        await add_case(db, GUILD, target.id, "warn", moderator_id=lead.id, reason=f"n{index}")

    first = FakeInteraction(bot, lead)
    await cog.cases.callback(cog, first, target, 1)
    assert "page 1 of 2" in first.sent and "page:2" in first.sent
    assert first.sent.count("`warn`") == 10

    second = FakeInteraction(bot, lead)
    await cog.cases.callback(cog, second, target, 9)
    assert "page 2 of 2" in second.sent
    assert second.sent.count("`warn`") == 2


async def test_a_page_of_long_reasons_is_cut_and_split_so_discord_takes_it(cog, bot, lead, target,
                                                                          db):
    for index in range(CASES_PER_PAGE):
        await add_case(
            db, GUILD, target.id, "warn", moderator_id=lead.id, reason=f"{index} " + "x" * 400
        )
    interaction = FakeInteraction(bot, lead)

    await cog.cases.callback(cog, interaction, target, 1)

    said = [message["content"] for message in interaction.response.messages]
    assert all(len(chunk) <= 1900 for chunk in said)
    assert said[0].count("…") == CASES_PER_PAGE
    assert "x" * 200 not in said[0]


async def test_every_command_is_staff_only(cog, bot, target):
    for call in (
        lambda i: cog.warn.callback(cog, i, target, "x"),
        lambda i: cog.timeout.callback(cog, i, target, "10m", "x"),
        lambda i: cog.untimeout.callback(cog, i, target, "x"),
        lambda i: cog.kick.callback(cog, i, target, "x"),
        lambda i: cog.ban.callback(cog, i, target, "x", 0),
        lambda i: cog.unban.callback(cog, i, "123456789012345678", "x"),
        lambda i: cog.purge.callback(cog, i, 5, None),
        lambda i: cog.case.callback(cog, i, 1),
        lambda i: cog.cases.callback(cog, i, target, 1),
    ):
        interaction = FakeInteraction(bot, target)
        await call(interaction)
        assert "staff only" in interaction.sent

    assert bot.guild.kicked == [] and bot.guild.bans == [] and target.timeouts == []


async def test_a_staff_role_holder_may_run_them(cog, bot, target):
    role = FakeRole(STAFF_ROLE)
    bot.guild.roles.append(role)
    bot.guild.get_channel(TEST_CHANNEL).visible_to.add(STAFF_ROLE)
    moderator = FakeMember(bot.guild, user_id=USER + 9, roles=(STAFF_ROLE,))
    interaction = FakeInteraction(bot, moderator)

    await cog.warn.callback(cog, interaction, target, "stop")

    assert "Warned" in interaction.sent


async def test_mod_logs_reads_the_moderation_lines_a_warn_left_behind(cog, bot, lead, target, db):
    await cog.warn.callback(cog, FakeInteraction(bot, lead), target, "stop")
    interaction = FakeInteraction(bot, lead)

    await cog.mod_logs.callback(cog, interaction)

    said = interaction.response.messages[-1]
    assert said["ephemeral"] is True
    assert said["embed"].title == "Moderation log"
    assert "`mod.warned`" in said["embed"].description
    assert f"<@{lead.id}> → <@{target.id}>" in said["embed"].description
    assert said["embed"].footer.text.endswith("/moderation.html")


async def test_mod_logs_refuses_somebody_who_is_not_staff(cog, bot, target):
    interaction = FakeInteraction(bot, target)

    await cog.mod_logs.callback(cog, interaction)

    assert "staff only" in interaction.sent
    assert "embed" not in interaction.response.messages[-1]


async def test_mod_logs_says_so_when_there_is_nothing_yet(cog, bot, lead):
    interaction = FakeInteraction(bot, lead)

    await cog.mod_logs.callback(cog, interaction, 5, True)

    assert "Nothing important" in interaction.response.messages[-1]["embed"].description
