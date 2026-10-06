import ast
import json
import pathlib
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import discord
import pytest

from black_bloc import structure_store
from black_bloc.cogs.moderation import structure_backup as sb
from black_bloc.config import load_settings
from black_bloc.settings_panel import reachable_on_the_panel
from black_bloc.settings_store import (
    CORE_KEYS,
    KEY_CHOICES,
    KEY_HELP,
    KEY_MAX,
    KEY_MIN,
    KEY_TYPES,
    STRUCTURE_BACKUP_DEFAULTS,
    STRUCTURE_BACKUP_KEYS,
    STRUCTURE_SAY_KEYS,
    SettingError,
    SettingsStore,
    coerce_value,
    namespace_of,
)
from black_bloc.structure import DAILY, FAILED, MANUAL, OFF, SAVED, UNCHANGED
from black_bloc.structure_diff import WORDS

GUILD = 7
LEADS = 11
MODS = 12
STAFF = 500
LOGS = 501
REHEARSAL = 502
ALERTS = 503
USER = 900
PHOENIX_5AM = datetime(2026, 10, 5, 12, 0, tzinfo=UTC)
PHOENIX_3AM = datetime(2026, 10, 5, 10, 0, tzinfo=UTC)


class _Response:
    def __init__(self, status):
        self.status = status
        self.reason = "refused"


class Thing(SimpleNamespace):
    __hash__ = object.__hash__


def role(role_id, name, permissions=0, position=0):
    return Thing(
        id=role_id,
        name=name,
        color=0,
        permissions=discord.Permissions(permissions),
        position=position,
        hoist=False,
        mentionable=False,
        managed=False,
    )


class FakeChannel:
    def __init__(self, channel_id, name, kind=discord.ChannelType.text, category_id=None):
        self.id = channel_id
        self.name = name
        self.type = kind
        self.category_id = category_id
        self.position = 0
        self.overwrites = {}
        self.sent = []
        self.send_raises = None

    async def send(self, content=None, **kwargs):
        if self.send_raises is not None:
            raise self.send_raises
        self.sent.append({"content": content, **kwargs})
        return SimpleNamespace(id=len(self.sent))


class FakeGuild:
    def __init__(self):
        self.id = GUILD
        self.name = "Black Bloc"
        self.unavailable = False
        self.verification_level = discord.VerificationLevel.low
        self.default_notifications = discord.NotificationLevel.only_mentions
        self.system_channel = None
        self.rules_channel = None
        self.roles = [role(GUILD, "@everyone", 1024), role(LEADS, "Leads", 8, 2)]
        self.channels = {
            one.id: one
            for one in (
                FakeChannel(40, "Lobby", discord.ChannelType.category),
                FakeChannel(STAFF, "staff", category_id=40),
                FakeChannel(LOGS, "logs", category_id=40),
                FakeChannel(REHEARSAL, "rehearsal", category_id=40),
                FakeChannel(ALERTS, "alerts", category_id=40),
            )
        }
        self.fetch_raises = None
        self.fetches = 0
        self.written = []

    def get_channel(self, channel_id):
        return self.channels.get(channel_id)

    async def fetch_roles(self):
        self.fetches += 1
        if self.fetch_raises is not None:
            raise self.fetch_raises
        return list(self.roles)

    async def fetch_channels(self):
        return list(self.channels.values())

    def __getattr__(self, name):
        if name.startswith(("create_", "edit", "delete")):
            raise AssertionError(f"structure backup must never call guild.{name}")
        raise AttributeError(name)


class FakeBot:
    def __init__(self, db, store, settings, guild):
        self.db = db
        self.store = store
        self.settings = settings
        self.guard = None
        self.guild = guild
        self.guilds = [guild]
        self.user = SimpleNamespace(id=42)

    def get_channel(self, channel_id):
        return self.guild.get_channel(channel_id)


class FakeResponse:
    def __init__(self):
        self.messages = []
        self.deferred = False

    def is_done(self):
        return self.deferred or bool(self.messages)

    async def send_message(self, content=None, ephemeral=False, **kwargs):
        self.messages.append({"content": content, "ephemeral": ephemeral, **kwargs})

    async def defer(self, ephemeral=False):
        self.deferred = True


class FakeFollowup:
    def __init__(self, response):
        self.response = response

    async def send(self, content=None, ephemeral=False, **kwargs):
        self.response.messages.append({"content": content, "ephemeral": ephemeral, **kwargs})


class FakeInteraction:
    def __init__(self, bot, *, staff=True, guild=True):
        self.client = bot
        self.guild = bot.guild if guild else None
        roles = [SimpleNamespace(id=LEADS)] if staff else []
        self.user = SimpleNamespace(
            id=USER,
            guild=bot.guild,
            roles=roles,
            guild_permissions=SimpleNamespace(manage_guild=staff),
        )
        self.response = FakeResponse()
        self.followup = FakeFollowup(self.response)
        self.edits = []

    async def original_response(self):
        return SimpleNamespace(id=1, embeds=[])

    async def edit_original_response(self, **kwargs):
        self.edits.append(kwargs)
        return SimpleNamespace(id=2, embeds=[kwargs.get("embed")])

    @property
    def rendered(self):
        return self.edits[-1] if self.edits else self.response.messages[-1]

    @property
    def said(self):
        return [one["content"] for one in self.response.messages if one.get("content")]


@pytest.fixture
def guild():
    return FakeGuild()


@pytest.fixture
async def bot(db, guild, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    settings = load_settings(_env_file=None, test_channel_id=STAFF)
    store = SettingsStore(db, settings)
    await store.load()
    await store.set(GUILD, "log_channel_id", LOGS)
    return FakeBot(db, store, settings, guild)


async def kinds(db):
    cur = await db.conn.execute("SELECT kind FROM action_log ORDER BY id")
    return [row["kind"] for row in await cur.fetchall()]


async def details_of(db, kind):
    cur = await db.conn.execute(
        "SELECT details, actor_id FROM action_log WHERE kind = ? ORDER BY id DESC LIMIT 1",
        (kind,),
    )
    row = await cur.fetchone()
    return json.loads(row["details"]) | {"actor_id": row["actor_id"]}


def labels(view):
    return [item.label for item in view.children]


def button(view, label):
    return next(item for item in view.children if item.label == label)


def field(embed, name):
    return next(one.value for one in embed.fields if one.name == name)


def refused(status=403):
    kind = discord.Forbidden if status == 403 else discord.HTTPException
    return kind(_Response(status), "Missing Access")


def test_the_feature_ships_in_shadow_with_every_key_under_core():
    assert STRUCTURE_BACKUP_DEFAULTS["structure_backup_mode"] == "shadow"
    assert KEY_CHOICES["structure_backup_mode"] == ("off", "shadow", "on")
    assert STRUCTURE_BACKUP_DEFAULTS["structure_backup_hour"] == 4
    assert STRUCTURE_BACKUP_DEFAULTS["structure_backup_keep"] == 60
    assert (KEY_MIN.get("structure_backup_hour"), KEY_MAX["structure_backup_hour"]) == (None, 23)
    assert (KEY_MIN["structure_backup_keep"], KEY_MAX["structure_backup_keep"]) == (1, 365)
    assert len(STRUCTURE_BACKUP_KEYS) == len(set(STRUCTURE_BACKUP_KEYS)) == 75
    for key in STRUCTURE_BACKUP_KEYS:
        assert key in CORE_KEYS and namespace_of(key) == "core", key
        assert KEY_HELP.get(key), key
        assert reachable_on_the_panel(key), key
    assert KEY_TYPES["structure_backup_shadow_channel_id"] == "channel"
    assert "structure_backup_shadow_channel_id" not in STRUCTURE_BACKUP_DEFAULTS


async def test_every_default_reaches_the_store_and_every_word_is_a_text_key(bot):
    for key, shipped in STRUCTURE_BACKUP_DEFAULTS.items():
        assert bot.store.get(GUILD, key) == shipped
    assert bot.store.get(GUILD, "structure_backup_channel_id") is None
    assert set(STRUCTURE_SAY_KEYS) == set(WORDS)
    for name, key in STRUCTURE_SAY_KEYS.items():
        assert KEY_TYPES[key] == "text" and bot.store.get(GUILD, key) == WORDS[name][0]
    with pytest.raises(SettingError):
        coerce_value("structure_backup_say_role_added", "Role {member} joined")
    with pytest.raises(SettingError):
        coerce_value("structure_backup_hour", 24)
    with pytest.raises(SettingError):
        coerce_value("structure_backup_keep", 0)


async def test_a_snapshot_is_stored_and_logged_with_its_counts(bot, guild, db):
    actor = SimpleNamespace(id=USER)

    taken = await sb.take_snapshot(bot, guild, actor=actor)

    assert taken.outcome == SAVED and taken.said == f"Snapshot #{taken.row['id']} saved."
    assert taken.changes == () and taken.previous is None
    assert await kinds(db) == ["structure.captured"]
    found = await details_of(db, "structure.captured")
    assert found["source"] == MANUAL and found["actor_id"] == USER
    assert (found["roles"], found["categories"], found["channels"]) == (2, 1, 4)
    assert (await structure_store.look(db, GUILD))["outcome"] == SAVED
    assert (await structure_store.look(db, GUILD))["last_day"] is None


async def test_an_unchanged_server_is_a_look_not_a_second_copy_and_its_own_log_kind(
    bot, guild, db
):
    first = await sb.take_snapshot(bot, guild)

    again = await sb.take_snapshot(bot, guild)

    assert again.outcome == UNCHANGED
    assert again.said == (
        f"Nothing has changed since snapshot #{first.row['id']}, so no second copy was stored."
    )
    assert await structure_store.count(db, GUILD) == 1
    assert await kinds(db) == ["structure.captured", "structure.unchanged"]
    assert (await structure_store.look(db, GUILD))["outcome"] == UNCHANGED


async def test_a_changed_server_is_a_new_snapshot_that_carries_the_changes_in_words(
    bot, guild, db
):
    await sb.take_snapshot(bot, guild)
    guild.roles.append(role(MODS, "Mods", 2, 1))

    taken = await sb.take_snapshot(bot, guild)

    assert taken.outcome == SAVED
    assert [one["text"] for one in taken.changes] == ["Role **Mods** was added."]
    found = await details_of(db, "structure.captured")
    assert found["changes"] == 1 and found["previous_id"] == taken.previous["id"]


async def test_the_change_list_uses_the_wording_staff_stored(bot, guild):
    await sb.take_snapshot(bot, guild)
    await bot.store.set(GUILD, "structure_backup_say_role_added", "New role: {role}")
    guild.roles.append(role(MODS, "Mods", 2, 1))

    taken = await sb.take_snapshot(bot, guild)

    assert [one["text"] for one in taken.changes] == ["New role: Mods"]


async def test_off_captures_nothing_and_says_how_to_turn_it_on(bot, guild, db):
    await bot.store.set(GUILD, "structure_backup_mode", "off")

    taken = await sb.take_snapshot(bot, guild)

    assert taken.outcome == OFF
    assert "structure_backup_mode" in taken.said and "/settings" in taken.said
    assert guild.fetches == 0
    assert await structure_store.count(db, GUILD) == 0
    assert await kinds(db) == []


@pytest.mark.parametrize(
    ("raises", "said"),
    [
        (refused(403), "Discord refused to list the server's roles and channels"),
        (refused(500), "Discord answered with an error (500"),
        (RuntimeError("boom"), "something unexpected went wrong (RuntimeError)"),
    ],
)
async def test_a_failure_is_an_outcome_in_words_with_its_own_kind_and_never_raises(
    bot, guild, db, raises, said
):
    guild.fetch_raises = raises

    taken = await sb.take_snapshot(bot, guild)

    assert taken.outcome == FAILED and said in taken.reason
    assert taken.said.startswith("No snapshot was taken — ")
    assert "403" not in taken.said.replace("(403", "")
    assert await kinds(db) == ["structure.capture_failed"]
    assert said in (await details_of(db, "structure.capture_failed"))["reason"]
    looked = await structure_store.look(db, GUILD)
    assert looked["outcome"] == FAILED and said in looked["reason"]
    assert await structure_store.count(db, GUILD) == 0


async def test_an_unavailable_server_is_refused_before_discord_is_asked(bot, guild):
    guild.unavailable = True

    taken = await sb.take_snapshot(bot, guild)

    assert taken.outcome == FAILED and "unavailable" in taken.reason
    assert guild.fetches == 0


async def test_success_unchanged_and_failure_are_three_different_log_kinds(bot, guild, db):
    await sb.take_snapshot(bot, guild)
    await sb.take_snapshot(bot, guild)
    guild.fetch_raises = refused()
    await sb.take_snapshot(bot, guild)

    assert await kinds(db) == [
        "structure.captured",
        "structure.unchanged",
        "structure.capture_failed",
    ]


async def test_the_oldest_snapshots_are_pruned_and_the_log_says_how_many(bot, guild, db):
    await bot.store.set(GUILD, "structure_backup_keep", 2)
    for n in range(4):
        guild.roles.append(role(100 + n, f"role-{n}", 0, 3 + n))
        await sb.take_snapshot(bot, guild)

    assert await structure_store.count(db, GUILD) == 2
    assert (await kinds(db)).count("structure.pruned") == 2
    assert (await details_of(db, "structure.pruned"))["removed"] == 1


async def test_the_daily_look_waits_for_the_hour_in_the_servers_own_time_zone(bot, guild, db):
    assert await sb.run_daily(bot, guild, PHOENIX_3AM) is None
    assert guild.fetches == 0

    taken = await sb.run_daily(bot, guild, PHOENIX_5AM)

    assert taken.outcome == SAVED
    assert (await details_of(db, "structure.captured"))["source"] == DAILY
    assert (await structure_store.look(db, GUILD))["last_day"] == "2026-10-05"


async def test_the_daily_look_runs_once_a_day_and_again_the_next(bot, guild, db):
    await sb.run_daily(bot, guild, PHOENIX_5AM)

    assert await sb.run_daily(bot, guild, PHOENIX_5AM + timedelta(minutes=10)) is None
    assert guild.fetches == 1
    tomorrow = await sb.run_daily(bot, guild, PHOENIX_5AM + timedelta(days=1))

    assert tomorrow.outcome == UNCHANGED
    assert await kinds(db) == ["structure.captured", "structure.unchanged"]


async def test_the_hour_is_a_key(bot, guild):
    await bot.store.set(GUILD, "structure_backup_hour", 2)

    assert (await sb.run_daily(bot, guild, PHOENIX_3AM)).outcome == SAVED


async def test_a_failed_daily_look_is_tried_three_times_that_day_then_waits(bot, guild, db):
    guild.fetch_raises = refused()

    outcomes = []
    for n in range(5):
        taken = await sb.run_daily(bot, guild, PHOENIX_5AM + timedelta(minutes=10 * n))
        outcomes.append(getattr(taken, "outcome", None))

    assert outcomes == [FAILED, FAILED, FAILED, None, None]
    assert (await kinds(db)).count("structure.capture_failed") == 3
    guild.fetch_raises = None
    assert (await sb.run_daily(bot, guild, PHOENIX_5AM + timedelta(days=1))).outcome == SAVED


async def test_the_daily_look_does_nothing_while_off_or_while_the_server_is_unavailable(
    bot, guild, db
):
    guild.unavailable = True
    assert await sb.run_daily(bot, guild, PHOENIX_5AM) is None
    guild.unavailable = False
    await bot.store.set(GUILD, "structure_backup_mode", "off")
    assert await sb.run_daily(bot, guild, PHOENIX_5AM) is None

    assert await kinds(db) == [] and guild.fetches == 0


async def changed_overnight(bot, guild):
    await sb.run_daily(bot, guild, PHOENIX_5AM)
    guild.roles.append(role(MODS, "Mods", 2, 1))
    return await sb.run_daily(bot, guild, PHOENIX_5AM + timedelta(days=1))


async def test_the_first_snapshot_ever_posts_no_notice(bot, guild, db):
    await sb.run_daily(bot, guild, PHOENIX_5AM)

    assert all(not channel.sent for channel in guild.channels.values())
    assert "structure.notice_posted" not in await kinds(db)


async def test_in_shadow_the_notice_goes_to_the_features_own_rehearsal_home(bot, guild, db):
    await bot.store.set(GUILD, "shadow_channel_id", LOGS)
    await bot.store.set(GUILD, "structure_backup_shadow_channel_id", REHEARSAL)
    await bot.store.set(GUILD, "structure_backup_channel_id", ALERTS)

    await changed_overnight(bot, guild)

    assert not guild.channels[ALERTS].sent and not guild.channels[LOGS].sent
    (sent,) = guild.channels[REHEARSAL].sent
    assert sent["content"] == f"Rehearsal — this is where it would go: <#{ALERTS}>"
    assert sent["embed"].title == "Server structure changed"
    assert "1 change(s) since the snapshot of <t:" in sent["embed"].description
    assert "• Role **Mods** was added." in sent["embed"].description
    assert sent["allowed_mentions"].to_dict() == discord.AllowedMentions.none().to_dict()
    found = await details_of(db, "structure.notice_posted")
    assert (found["mode"], found["channel_id"], found["aimed_at"]) == ("shadow", REHEARSAL, ALERTS)


async def test_in_shadow_with_no_home_of_its_own_the_notice_follows_the_rehearsal_home(
    bot, guild
):
    await bot.store.set(GUILD, "shadow_channel_id", REHEARSAL)

    await changed_overnight(bot, guild)

    assert len(guild.channels[REHEARSAL].sent) == 1
    assert not guild.channels[STAFF].sent


async def test_on_the_notice_goes_to_its_channel_with_no_rehearsal_line(bot, guild, db):
    await bot.store.set(GUILD, "structure_backup_mode", "on")
    await bot.store.set(GUILD, "structure_backup_channel_id", ALERTS)
    await bot.store.set(GUILD, "shadow_channel_id", REHEARSAL)

    await changed_overnight(bot, guild)

    (sent,) = guild.channels[ALERTS].sent
    assert sent["content"] is None
    assert not guild.channels[REHEARSAL].sent
    assert (await details_of(db, "structure.notice_posted"))["mode"] == "on"


async def test_on_with_no_channel_set_the_notice_goes_to_the_staff_channel(bot, guild):
    await bot.store.set(GUILD, "structure_backup_mode", "on")

    await changed_overnight(bot, guild)

    assert len(guild.channels[STAFF].sent) == 1


async def test_the_notice_is_optional(bot, guild, db):
    await bot.store.set(GUILD, "structure_backup_notify", False)

    taken = await changed_overnight(bot, guild)

    assert taken.outcome == SAVED and taken.changes
    assert all(not channel.sent for channel in guild.channels.values())
    assert "structure.notice_posted" not in await kinds(db)


async def test_a_snapshot_taken_by_hand_posts_no_notice(bot, guild):
    await sb.take_snapshot(bot, guild)
    guild.roles.append(role(MODS, "Mods", 2, 1))

    await sb.take_snapshot(bot, guild)

    assert all(not channel.sent for channel in guild.channels.values())


async def test_an_unchanged_daily_look_posts_no_notice(bot, guild):
    await sb.run_daily(bot, guild, PHOENIX_5AM)
    await sb.run_daily(bot, guild, PHOENIX_5AM + timedelta(days=1))

    assert all(not channel.sent for channel in guild.channels.values())


async def test_a_notice_that_cannot_be_posted_is_a_failed_row_and_the_snapshot_stays(
    bot, guild, db
):
    guild.channels[LOGS].send_raises = refused()

    taken = await changed_overnight(bot, guild)

    assert taken.outcome == SAVED and await structure_store.count(db, GUILD) == 2
    assert (await kinds(db))[-1] == "structure.notice_failed"
    assert "Forbidden" in (await details_of(db, "structure.notice_failed"))["reason"]


async def test_a_notice_aimed_at_a_channel_that_is_gone_says_so(bot, guild, db):
    await bot.store.set(GUILD, "structure_backup_mode", "on")
    await bot.store.set(GUILD, "structure_backup_channel_id", 99999)

    await changed_overnight(bot, guild)

    assert (await details_of(db, "structure.notice_failed"))["reason"] == sb.NO_NOTICE_CHANNEL


async def test_a_long_change_list_is_cut_at_the_key_and_says_how_many_more(bot, guild):
    await bot.store.set(GUILD, "structure_backup_notice_lines", 2)
    await sb.run_daily(bot, guild, PHOENIX_5AM)
    for n in range(5):
        guild.roles.append(role(100 + n, f"role-{n}", 0, 3 + n))

    await sb.run_daily(bot, guild, PHOENIX_5AM + timedelta(days=1))

    said = guild.channels[LOGS].sent[0]["embed"].description.splitlines()
    assert said[0].startswith("5 change(s)")
    assert len(said) == 4
    assert said[-1] == "…and 3 more — the Structure page lists every one."


async def test_a_role_named_like_a_ping_cannot_ping_from_the_notice(bot, guild):
    await sb.run_daily(bot, guild, PHOENIX_5AM)
    guild.roles.append(role(MODS, "@everyone", 2, 1))

    await sb.run_daily(bot, guild, PHOENIX_5AM + timedelta(days=1))

    sent = guild.channels[LOGS].sent[0]
    assert sent["allowed_mentions"].to_dict() == {"parse": []}


async def test_the_loop_runs_every_guild_and_reports_its_health(bot, guild, db):
    cog = sb.StructureBackup(bot)

    await cog.run_once(PHOENIX_5AM)

    assert await structure_store.count(db, GUILD) == 1
    assert cog.loop_health("_daily") == (None, None)
    assert cog.loop_health("other") == (None, None)


async def test_the_panel_opens_with_the_state_and_only_the_moves_that_are_valid(bot, guild):
    cog = sb.StructureBackup(bot)
    interaction = FakeInteraction(bot)

    await cog.structure.callback(cog, interaction)

    shown = interaction.rendered
    assert shown["ephemeral"] is True
    assert shown["embed"].title == "Server structure"
    assert field(shown["embed"], "Mode") == "shadow"
    assert field(shown["embed"], "Latest snapshot") == "No snapshot has been taken yet."
    assert [one.name for one in shown["embed"].fields] == ["Mode", "Latest snapshot"]
    assert labels(shown["view"]) == ["Take one now", "Open the Structure page"]
    link = button(shown["view"], "Open the Structure page")
    assert link.url == f"{bot.settings.origin}/structure.html"


async def test_take_one_now_stores_a_snapshot_and_says_so_on_the_card(bot, guild, db):
    cog = sb.StructureBackup(bot)
    opening = FakeInteraction(bot)
    await cog.structure.callback(cog, opening)
    press = FakeInteraction(bot)

    await button(opening.rendered["view"], "Take one now").callback(press)

    shown = press.rendered
    row = await structure_store.latest(db, GUILD)
    assert shown["embed"].description == f"Snapshot #{row['id']} saved."
    latest = field(shown["embed"], "Latest snapshot")
    assert latest.startswith(f"#{row['id']} · <t:")
    assert latest.endswith("2 roles · 1 categories · 4 channels · 0 permission overwrites")
    assert field(shown["embed"], "Last look").endswith("— a new snapshot was stored.")
    assert labels(shown["view"]) == ["Take one now", "What changed", "Open the Structure page"]
    assert (await details_of(db, "structure.captured"))["actor_id"] == USER


async def test_what_changed_compares_the_latest_with_now_and_stores_nothing(bot, guild, db):
    await sb.take_snapshot(bot, guild)
    _, view = await sb.build_panel(bot, guild)
    same = FakeInteraction(bot)
    await button(view, "What changed").callback(same)
    assert field(same.rendered["embed"], "What changed") == (
        "Nothing has changed since the latest snapshot."
    )

    guild.roles.append(role(MODS, "Mods", 2, 1))
    press = FakeInteraction(bot)
    await button(view, "What changed").callback(press)

    assert field(press.rendered["embed"], "What changed") == "• Role **Mods** was added."
    assert await structure_store.count(db, GUILD) == 1
    assert await kinds(db) == ["structure.captured"]


async def test_what_changed_says_why_when_discord_will_not_answer(bot, guild):
    await sb.take_snapshot(bot, guild)
    _, view = await sb.build_panel(bot, guild)
    guild.fetch_raises = refused()
    press = FakeInteraction(bot)

    await button(view, "What changed").callback(press)

    assert press.rendered["embed"].description.startswith("No snapshot was taken — Discord refused")


async def test_while_off_the_panel_still_opens_and_offers_no_capture(bot, guild):
    await sb.take_snapshot(bot, guild)
    await bot.store.set(GUILD, "structure_backup_mode", "off")

    embed, view = await sb.build_panel(bot, guild)

    assert field(embed, "Mode") == "off"
    assert labels(view) == ["What changed", "Open the Structure page"]


async def test_the_panel_reads_its_words_from_the_keys(bot, guild):
    await bot.store.set(GUILD, "structure_backup_panel_title", "Our layout")
    await bot.store.set(GUILD, "structure_backup_take_label", "Snapshot")

    embed, view = await sb.build_panel(bot, guild)

    assert embed.title == "Our layout" and labels(view)[0] == "Snapshot"


async def test_the_command_is_staff_only_and_a_press_by_someone_demoted_is_refused(
    bot, guild, db
):
    cog = sb.StructureBackup(bot)
    outsider = FakeInteraction(bot, staff=False)

    await cog.structure.callback(cog, outsider)

    assert "staff only" in outsider.said[0] and not outsider.edits
    _, view = await sb.build_panel(bot, guild)
    press = FakeInteraction(bot, staff=False)
    await button(view, "Take one now").callback(press)
    assert "staff only" in press.said[0]
    assert await structure_store.count(db, GUILD) == 0


async def test_the_command_refuses_a_dm_in_words(bot):
    cog = sb.StructureBackup(bot)
    interaction = FakeInteraction(bot, guild=False)

    await cog.structure.callback(cog, interaction)

    assert "server" in interaction.said[0]


async def test_a_download_leaves_a_row_that_names_the_door(bot, guild, db):
    taken = await sb.take_snapshot(bot, guild)

    await sb.record_download(bot, guild, SimpleNamespace(id=USER), taken.row, via="website")

    assert (await kinds(db))[-1] == "web.structure.downloaded"
    assert (await details_of(db, "web.structure.downloaded"))["snapshot_id"] == taken.row["id"]


WRITES = {
    "create_role",
    "create_text_channel",
    "create_voice_channel",
    "create_category",
    "create_forum",
    "create_stage_channel",
    "edit",
    "edit_role_positions",
    "set_permissions",
    "delete",
    "move",
    "add_roles",
    "remove_roles",
    "ban",
    "kick",
}
STRUCTURE_MODULES = (
    "structure.py",
    "structure_capture.py",
    "structure_diff.py",
    "structure_store.py",
    "cogs/moderation/structure_backup.py",
    "api/tools/structure.py",
)


def test_no_structure_module_can_write_a_role_a_channel_or_a_permission():
    """Capture and compare only: restoring is the owner's separate decision."""
    package = pathlib.Path(sb.__file__).resolve().parents[2]
    called: set[str] = set()
    for name in STRUCTURE_MODULES:
        tree = ast.parse((package / name).read_text(encoding="utf-8"))
        called |= {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }

    assert not (called & WRITES), sorted(called & WRITES)
