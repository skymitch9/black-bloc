from datetime import timedelta

import discord
import pytest

from black_bloc.cogs.moderation.modcmds import ModCommands
from black_bloc.config import load_settings
from black_bloc.modcases import add_case
from black_bloc.settings_store import SettingsStore

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


class FakeSentMessage:
    def __init__(self, said):
        self.said = dict(said)
        self.embeds = [said["embed"]] if said.get("embed") is not None else []
        self.edits = []

    async def edit(self, **kwargs):
        self.edits.append(kwargs)


class FakeResponse:
    def __init__(self):
        self.messages = []
        self.modals = []
        self.done = False

    def is_done(self):
        return self.done

    async def send_message(self, content=None, ephemeral=False, **kwargs):
        self.messages.append({"content": content, "ephemeral": ephemeral, **kwargs})
        self.done = True

    async def defer(self, ephemeral=False):
        self.messages.append({"content": None, "deferred": True})
        self.done = True

    async def send_modal(self, modal):
        self.modals.append(modal)
        self.done = True


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

    async def edit_original_response(self, **kwargs):
        self.response.messages.append({"content": None, **kwargs})
        return FakeSentMessage(kwargs)

    async def original_response(self):
        return FakeSentMessage(self.response.messages[-1])


async def action_kinds(db):
    cur = await db.conn.execute("SELECT kind FROM action_log ORDER BY id")
    return [row["kind"] for row in await cur.fetchall()]


async def cases(db):
    cur = await db.conn.execute("SELECT * FROM mod_cases ORDER BY id")
    return list(await cur.fetchall())


def cards(bot):
    return [m for m in bot.guild.get_channel(TEST_CHANNEL).messages if "embed" in m.kwargs]


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
    await cog.mod.callback(cog, theirs, lead)
    assert "no cases" in theirs.embed.description


async def test_a_purge_discord_refuses_says_what_it_needs(cog, bot, lead, db):
    bot.guild.get_channel(TEST_CHANNEL).purge_raises = refused()
    interaction = FakeInteraction(bot, lead)

    await cog.purge.callback(cog, interaction, 10, None)

    assert "Manage Messages" in interaction.sent
    assert "mod.purge_failed" in await action_kinds(db)
    assert await cases(db) == []


async def test_every_command_is_staff_only(cog, bot, target):
    for call in (
        lambda i: cog.warn.callback(cog, i, target, "x"),
        lambda i: cog.timeout.callback(cog, i, target, "10m", "x"),
        lambda i: cog.untimeout.callback(cog, i, target, "x"),
        lambda i: cog.kick.callback(cog, i, target, "x"),
        lambda i: cog.ban.callback(cog, i, target, "x", 0),
        lambda i: cog.unban.callback(cog, i, "123456789012345678", "x"),
        lambda i: cog.purge.callback(cog, i, 5, None),
        lambda i: cog.mod.callback(cog, i, None),
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


# --- the /mod panel ------------------------------------------------------------------------------

SITE_ROOT_LABELS = ["Jump to case #…", "Refresh", "Logs", "Open on the site"]


def rendered(interaction):
    """The last thing the panel drew, ignoring any followup sentence sent after it."""
    for said in reversed(interaction.response.messages):
        if said.get("view") is not None:
            return said
    return None


def labels(interaction):
    view = rendered(interaction)["view"]
    return [item.label for item in view.children if getattr(item, "label", None)]


def placeholders(interaction):
    view = rendered(interaction)["view"]
    return [item.placeholder for item in view.children if getattr(item, "placeholder", None)]


def view_of(interaction):
    return rendered(interaction)["view"]


def control(interaction, label):
    return next(item for item in view_of(interaction).children if
                getattr(item, "label", None) == label)


def select_of(interaction, placeholder):
    return next(item for item in view_of(interaction).children if
                getattr(item, "placeholder", None) == placeholder)


async def press(bot, who, interaction, label):
    item = control(interaction, label)
    pressed = FakeInteraction(bot, who)
    await item.callback(pressed)
    return pressed


async def open_panel(cog, bot, who, member=None):
    interaction = FakeInteraction(bot, who)
    await cog.mod.callback(cog, interaction, member)
    return interaction


async def a_case(db, lead, reason="spam", kind="warn", user_id=USER):
    return await add_case(db, GUILD, user_id, kind, moderator_id=lead.id, reason=reason)


async def test_mod_opens_one_ephemeral_panel_over_the_lines_cases_used_to_print(
    cog, bot, lead, target, db
):
    for index in range(3):
        await a_case(db, lead, reason=f"n{index}", user_id=target.id)

    interaction = await open_panel(cog, bot, lead)

    said = interaction.response.messages[-1]
    assert said["ephemeral"] is True and said["view"] is not None
    assert said["embed"].title == "What Black Bloc has done"
    assert "3** case(s) for this server — page 1 of 1" in said["embed"].description
    assert said["embed"].description.count("`warn`") == 3
    assert "/warn" in said["embed"].footer.text
    assert "`/case" not in said["embed"].description
    assert labels(interaction) == SITE_ROOT_LABELS
    assert placeholders(interaction) == ["A case…", "Whose cases?"]


async def test_a_guild_with_no_cases_says_so_over_no_select_and_no_pager(cog, bot, lead):
    interaction = await open_panel(cog, bot, lead)

    assert "no cases for this server" in interaction.embed.description
    assert placeholders(interaction) == ["Whose cases?"]
    assert labels(interaction) == SITE_ROOT_LABELS


async def test_mod_at_a_member_with_no_cases_says_so_and_offers_the_way_out(
    cog, bot, lead, target, db
):
    await a_case(db, lead, user_id=USER + 5)

    interaction = await open_panel(cog, bot, lead, target)

    assert f"no cases for <@{target.id}>" in interaction.embed.description
    assert "Everyone's cases" in labels(interaction)
    assert placeholders(interaction) == ["Whose cases?"]


async def test_the_pager_arrows_are_absent_rather_than_there_and_refusing(
    cog, bot, lead, target, db
):
    for index in range(12):
        await a_case(db, lead, reason=f"n{index}", user_id=target.id)

    first = await open_panel(cog, bot, lead, target)
    assert "page 1 of 2" in first.embed.description
    assert "‹ Newer" not in labels(first)
    assert "Older ›" in labels(first)

    second = await press(bot, lead, first, "Older ›")
    assert "page 2 of 2" in rendered(second)["embed"].description
    assert "‹ Newer" in labels(second)
    assert "Older ›" not in labels(second)

    back = await press(bot, lead, second, "‹ Newer")
    assert "page 1 of 2" in rendered(back)["embed"].description
    assert "‹ Newer" not in labels(back)


async def test_a_member_filter_is_escapable_and_everyone_only_shows_while_it_is_on(
    cog, bot, lead, target, db
):
    await a_case(db, lead, user_id=target.id)
    await a_case(db, lead, user_id=USER + 5)

    filtered = await open_panel(cog, bot, lead, target)
    assert f"1** case(s) for <@{target.id}>" in filtered.embed.description
    assert "Everyone's cases" in labels(filtered)

    everyone = await press(bot, lead, filtered, "Everyone's cases")
    assert "for this server" in rendered(everyone)["embed"].description
    assert "Everyone's cases" not in labels(everyone)


async def test_a_case_opens_its_card_over_five_moves_and_says_void_undoes_nothing(
    cog, bot, lead, target, db
):
    case_id = await a_case(db, lead, user_id=target.id)
    interaction = await open_panel(cog, bot, lead)

    picked = FakeInteraction(bot, lead)
    select = select_of(interaction, "A case…")
    select._values = [str(case_id)]
    await select.callback(picked)

    card = rendered(picked)
    assert card["embed"].title == f"Case #{case_id} — warn"
    assert "does not undo the punishment" in card["embed"].description
    assert labels(picked) == [
        "Edit reason…", "Add a note…", "Void this case…", "Back", "Refresh"
    ]

    home = await press(bot, lead, picked, "Back")
    assert rendered(home)["embed"].title == "What Black Bloc has done"


async def a_card(cog, bot, lead, db, case_id):
    root = await open_panel(cog, bot, lead)
    picked = FakeInteraction(bot, lead)
    select = select_of(root, "A case…")
    select._values = [str(case_id)]
    await select.callback(picked)
    return picked


async def test_an_empty_reason_is_refused_in_one_sentence_and_saves_nothing(
    cog, bot, lead, target, db
):
    case_id = await a_case(db, lead, reason="spam", user_id=target.id)
    card = await a_card(cog, bot, lead, db, case_id)

    opener = FakeInteraction(bot, lead)
    await control(card, "Edit reason…").callback(opener)
    modal = opener.response.modals[-1]
    assert modal.note.default == "spam"

    typed = FakeInteraction(bot, lead)
    modal.note._value = "   "
    await modal.on_submit(typed)

    assert "nobody can read" in typed.response.messages[-1]["content"]
    assert rendered(typed) is None
    assert (await cases(db))[0]["reason"] == "spam"
    assert await action_kinds(db) == []


async def test_a_real_reason_saves_once_and_rewrites_the_card_in_the_modlog(
    cog, bot, lead, target, db
):
    case_id = await a_case(db, lead, reason="spam", user_id=target.id)
    await db.conn.execute("UPDATE mod_cases SET log_message_id = 1 WHERE id = ?", (case_id,))
    await db.conn.commit()
    rewritten = []
    bot.guild.get_channel(TEST_CHANNEL).get_partial_message = lambda mid: _Partial(rewritten)
    card = await a_card(cog, bot, lead, db, case_id)

    opener = FakeInteraction(bot, lead)
    await control(card, "Edit reason…").callback(opener)
    modal = opener.response.modals[-1]
    modal.note._value = "posting links"
    typed = FakeInteraction(bot, lead)
    await modal.on_submit(typed)

    assert (await cases(db))[0]["reason"] == "posting links"
    assert await action_kinds(db) == ["case.reason_edited"]
    assert "reason now reads" in typed.response.messages[-1]["content"]
    assert "posting links" in str(rendered(typed)["embed"].fields[-1].value)
    assert len(rewritten) == 1
    assert "posting links" in str(rewritten[0]["embed"].fields[-1].value)


class _Partial:
    def __init__(self, seen):
        self.seen = seen

    async def edit(self, **kwargs):
        self.seen.append(kwargs)


async def test_a_modlog_card_that_cannot_be_rewritten_never_aborts_the_void(
    cog, bot, lead, target, db
):
    """Checklist 12: the row, the log and the DM are done before the card is even tried."""
    case_id = await a_case(db, lead, user_id=target.id)
    await db.conn.execute("UPDATE mod_cases SET log_message_id = 1 WHERE id = ?", (case_id,))
    await db.conn.commit()

    bot.guild.get_channel(TEST_CHANNEL).get_partial_message = lambda mid: _Angry()
    card = await a_card(cog, bot, lead, db, case_id)
    opener = FakeInteraction(bot, lead)
    await control(card, "Void this case…").callback(opener)
    modal = opener.response.modals[-1]
    modal.note._value = "wrong member"
    typed = FakeInteraction(bot, lead)
    await modal.on_submit(typed)

    assert (await cases(db))[0]["voided_at"]
    assert await action_kinds(db) == ["case.voided"]
    assert target.dms
    assert "marked cancelled" in typed.response.messages[-1]["content"]


class _Angry:
    async def edit(self, **kwargs):
        raise discord.HTTPException(_Response(403), "no")


async def test_the_note_button_says_add_then_edit_and_never_both(cog, bot, lead, target, db):
    case_id = await a_case(db, lead, user_id=target.id)
    card = await a_card(cog, bot, lead, db, case_id)

    assert "Add a note…" in labels(card) and "Edit the note…" not in labels(card)

    opener = FakeInteraction(bot, lead)
    await control(card, "Add a note…").callback(opener)
    modal = opener.response.modals[-1]
    modal.note._value = "they apologised"
    typed = FakeInteraction(bot, lead)
    await modal.on_submit(typed)

    assert labels(typed) == [
        "Edit reason…", "Edit the note…", "Void this case…", "Back", "Refresh"
    ]
    assert "Add a note…" not in labels(typed)
    assert await action_kinds(db) == ["case.noted"]
    names = [field.name for field in rendered(typed)["embed"].fields]
    assert "Note" in names

    blank = FakeInteraction(bot, lead)
    await control(typed, "Edit the note…").callback(blank)
    again = blank.response.modals[-1]
    assert again.note.default == "they apologised"


async def test_voiding_dms_the_member_marks_the_case_and_cannot_be_done_twice(
    cog, bot, lead, target, db
):
    case_id = await a_case(db, lead, user_id=target.id)
    card = await a_card(cog, bot, lead, db, case_id)

    opener = FakeInteraction(bot, lead)
    await control(card, "Void this case…").callback(opener)
    modal = opener.response.modals[-1]
    assert modal.note.default is None
    modal.note._value = "wrong member"
    typed = FakeInteraction(bot, lead)
    await modal.on_submit(typed)

    row = (await cases(db))[0]
    assert row["voided_at"] and row["void_reason"] == "wrong member"
    assert await action_kinds(db) == ["case.voided"]
    assert target.dms and "cancelled" in target.dms[-1]
    assert "not undone" in target.dms[-1]
    assert labels(typed) == [
        "Restore this case", "Edit reason…", "Add a note…", "Back", "Refresh"
    ]
    assert "Void this case…" not in labels(typed)

    stale = FakeInteraction(bot, lead)
    await control(card, "Void this case…").callback(stale)
    twice = FakeInteraction(bot, lead)
    second = stale.response.modals[-1]
    second.note._value = "again"
    await second.on_submit(twice)

    assert "a moment ago" in twice.response.messages[-1]["content"]
    assert await action_kinds(db) == ["case.voided"]


async def test_a_voided_case_is_struck_through_on_the_list_and_stops_counting(
    cog, bot, lead, target, db
):
    case_id = await a_case(db, lead, reason="spam", user_id=target.id)
    card = await a_card(cog, bot, lead, db, case_id)
    opener = FakeInteraction(bot, lead)
    await control(card, "Void this case…").callback(opener)
    modal = opener.response.modals[-1]
    modal.note._value = "wrong member"
    voided = FakeInteraction(bot, lead)
    await modal.on_submit(voided)

    home = await press(bot, lead, voided, "Back")

    assert "~~**#" in rendered(home)["embed"].description
    assert select_of(home, "A case…").options[0].label.startswith(f"#{case_id} · voided")


async def test_restore_takes_the_void_back_off_and_no_state_is_terminal(
    cog, bot, lead, target, db
):
    case_id = await a_case(db, lead, user_id=target.id)
    card = await a_card(cog, bot, lead, db, case_id)
    opener = FakeInteraction(bot, lead)
    await control(card, "Void this case…").callback(opener)
    modal = opener.response.modals[-1]
    modal.note._value = "wrong member"
    voided = FakeInteraction(bot, lead)
    await modal.on_submit(voided)

    back = await press(bot, lead, voided, "Restore this case")

    assert (await cases(db))[0]["voided_at"] is None
    assert await action_kinds(db) == ["case.voided", "case.restored"]
    assert labels(back) == [
        "Edit reason…", "Add a note…", "Void this case…", "Back", "Refresh"
    ]
    assert target.dms[-1].startswith("A case against you")

    stale = FakeInteraction(bot, lead)
    await control(voided, "Restore this case").callback(stale)
    assert "a moment ago" in stale.response.messages[-1]["content"]


async def test_jump_opens_a_case_by_number_and_a_bad_one_leaves_the_panel_alone(
    cog, bot, lead, target, db
):
    case_id = await a_case(db, lead, user_id=target.id)
    root = await open_panel(cog, bot, lead)

    opener = FakeInteraction(bot, lead)
    await control(root, "Jump to case #…").callback(opener)
    modal = opener.response.modals[-1]
    modal.number._value = str(case_id)
    jumped = FakeInteraction(bot, lead)
    await modal.on_submit(jumped)

    assert rendered(jumped)["embed"].title == f"Case #{case_id} — warn"

    missing = FakeInteraction(bot, lead)
    await control(root, "Jump to case #…").callback(missing)
    gone = missing.response.modals[-1]
    gone.number._value = "99999"
    told = FakeInteraction(bot, lead)
    await gone.on_submit(told)

    assert "no case **#99999**" in told.response.messages[-1]["content"]
    assert rendered(told) is None

    words = FakeInteraction(bot, lead)
    await control(root, "Jump to case #…").callback(words)
    typed = words.response.modals[-1]
    typed.number._value = "abc"
    refused_it = FakeInteraction(bot, lead)
    await typed.on_submit(refused_it)

    assert "**abc** is not a case number" in refused_it.response.messages[-1]["content"]
    assert rendered(refused_it) is None


async def test_a_case_from_another_guild_is_never_opened(cog, bot, lead, db):
    other = await add_case(db, GUILD + 1, USER, "warn", moderator_id=lead.id)
    root = await open_panel(cog, bot, lead)

    opener = FakeInteraction(bot, lead)
    await control(root, "Jump to case #…").callback(opener)
    modal = opener.response.modals[-1]
    modal.number._value = str(other)
    told = FakeInteraction(bot, lead)
    await modal.on_submit(told)

    assert "no case" in told.response.messages[-1]["content"]
    assert rendered(told) is None


async def test_a_case_that_belongs_to_a_channel_says_there_is_nobody_to_tell(
    cog, bot, lead, db
):
    case_id = await add_case(
        db, GUILD, None, "purge", moderator_id=lead.id, channel_id=TEST_CHANNEL
    )
    card = await a_card(cog, bot, lead, db, case_id)

    assert "nobody to tell" in rendered(card)["embed"].description

    opener = FakeInteraction(bot, lead)
    await control(card, "Void this case…").callback(opener)
    modal = opener.response.modals[-1]
    modal.note._value = "not needed"
    typed = FakeInteraction(bot, lead)
    await modal.on_submit(typed)

    assert (await cases(db))[0]["voided_at"]
    assert await action_kinds(db) == ["case.voided"]


@pytest.mark.parametrize(
    "label", ["Jump to case #…", "Refresh", "Logs"]
)
async def test_a_staffer_demoted_mid_panel_moves_nothing_the_reads_included(
    cog, bot, lead, target, db, label
):
    await a_case(db, lead, user_id=target.id)
    root = await open_panel(cog, bot, lead)

    demoted = FakeInteraction(bot, target)
    await control(root, label).callback(demoted)

    assert "staff only" in demoted.sent
    assert rendered(demoted) is None


async def test_a_move_on_the_card_refuses_a_demoted_staffer_before_it_writes(
    cog, bot, lead, target, db
):
    case_id = await a_case(db, lead, user_id=target.id)
    card = await a_card(cog, bot, lead, db, case_id)

    for label in ("Edit reason…", "Add a note…", "Void this case…", "Back"):
        demoted = FakeInteraction(bot, target)
        await control(card, label).callback(demoted)
        assert "staff only" in demoted.sent, label
        assert demoted.response.modals == [], label

    assert await action_kinds(db) == []


async def test_the_logs_button_reads_the_lines_a_warn_left_behind(cog, bot, lead, target, db):
    await cog.warn.callback(cog, FakeInteraction(bot, lead), target, "stop")
    root = await open_panel(cog, bot, lead)

    pressed = await press(bot, lead, root, "Logs")

    said = pressed.response.messages[-1]
    assert said["ephemeral"] is True
    assert said["embed"].title == "Moderation log"
    assert "`mod.warned`" in said["embed"].description
    assert f"<@{lead.id}> → <@{target.id}>" in said["embed"].description
    assert said["embed"].footer.text.endswith("/moderation.html")


async def test_the_logs_button_refuses_somebody_who_is_not_staff(cog, bot, lead, target, db):
    await a_case(db, lead, user_id=target.id)
    root = await open_panel(cog, bot, lead)

    pressed = await press(bot, target, root, "Logs")

    assert "staff only" in pressed.sent
    assert "embed" not in pressed.response.messages[-1]


async def test_a_re_render_retires_the_view_it_replaced(cog, bot, lead, target, db):
    for index in range(12):
        await a_case(db, lead, reason=f"n{index}", user_id=target.id)
    first = await open_panel(cog, bot, lead)
    old = view_of(first)

    second = await press(bot, lead, first, "Older ›")

    assert old.replaced is True and old.is_finished() is True
    assert view_of(second).replaced is False


async def test_the_timeout_greys_every_control_and_says_to_run_mod_again(cog, bot, lead, db):
    interaction = await open_panel(cog, bot, lead)
    view = view_of(interaction)
    view.message = FakeSentMessage(rendered(interaction))

    await view.on_timeout()

    assert all(item.disabled for item in view.children)
    footer = view.message.edits[-1]["embeds"][0].footer.text
    assert "gone quiet" in footer and "/mod again" in footer


async def test_the_panel_says_the_database_is_down_rather_than_drawing_a_dead_one(
    cog, bot, lead, db
):
    await db.close()
    interaction = FakeInteraction(bot, lead)

    await cog.mod.callback(cog, interaction, None)

    assert "database" in interaction.sent.lower()
    assert "view" not in interaction.response.messages[-1]
