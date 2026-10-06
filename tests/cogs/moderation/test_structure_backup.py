import ast
import asyncio
import json
import pathlib
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import discord
import pytest

from black_bloc import settings_panel, structure_store
from black_bloc import structure as structure_rules
from black_bloc.cogs.moderation import structure_backup as sb
from black_bloc.config import load_settings
from black_bloc.settings_panel import mode_lines, reachable_on_the_panel
from black_bloc.settings_store import (
    CORE_KEYS,
    KEY_CHOICES,
    KEY_HELP,
    KEY_MAX,
    KEY_MIN,
    KEY_TYPES,
    STRUCTURE_BACKUP_DEFAULTS,
    STRUCTURE_BACKUP_KEYS,
    STRUCTURE_BACKUP_LIMITS,
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
OWNER = 901
PHOENIX_5AM = datetime(2026, 10, 5, 12, 0, tzinfo=UTC)
PHOENIX_3AM = datetime(2026, 10, 5, 10, 0, tzinfo=UTC)


class _Response:
    def __init__(self, status):
        self.status = status
        self.reason = "refused"


REFUSED: list[str] = []


class Refuses:
    """Anything a fake was not told it may do: reading it is harmless, calling it is not."""

    def __init__(self, owner, name):
        self.what = f"{owner}.{name}"

    def __call__(self, *args, **kwargs):
        REFUSED.append(self.what)
        raise AssertionError(f"structure backup must never call {self.what}")


class Strict:
    KIND = "thing"
    __hash__ = object.__hash__

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        return Refuses(self.KIND, name)


@pytest.fixture(autouse=True)
def nothing_outside_the_read_list_was_called():
    REFUSED.clear()
    yield
    assert not REFUSED, REFUSED


class FakeRole(Strict):
    KIND = "role"

    def __init__(self, role_id, name, permissions=0, position=0):
        self.id = role_id
        self.name = name
        self.color = 0
        self.permissions = discord.Permissions(permissions)
        self.position = position
        self.hoist = False
        self.mentionable = False
        self.managed = False


def role(role_id, name, permissions=0, position=0):
    return FakeRole(role_id, name, permissions, position)


class FakeChannel(Strict):
    KIND = "channel"

    def __init__(self, channel_id, name, kind=discord.ChannelType.text, category_id=None):
        self.id = channel_id
        self.name = name
        self.type = kind
        self.category_id = category_id
        self.position = 0
        self.topic = None
        self.slowmode_delay = 0
        self.nsfw = False
        self.bitrate = None
        self.user_limit = None
        self.available_tags = []
        self.overwrites = {}
        self.sent = []
        self.send_raises = None

    async def send(self, content=None, **kwargs):
        if self.send_raises is not None:
            raise self.send_raises
        self.sent.append({"content": content, **kwargs})
        return SimpleNamespace(id=len(self.sent))


class FakeHTTP(Strict):
    KIND = "bot.http"


class FakeGuild(Strict):
    KIND = "guild"

    def __init__(self):
        self.id = GUILD
        self.owner_id = OWNER
        self.name = "Black Bloc"
        self.unavailable = False
        self.verification_level = discord.VerificationLevel.low
        self.default_notifications = discord.NotificationLevel.only_mentions
        self.system_channel = None
        self.rules_channel = None
        self.system_channel_id = None
        self.rules_channel_id = None
        self.hangs = False
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
        if self.hangs:
            await asyncio.sleep(60)
        if self.fetch_raises is not None:
            raise self.fetch_raises
        return list(self.roles)

    async def fetch_channels(self):
        return list(self.channels.values())


class FakeBot:
    def __init__(self, db, store, settings, guild):
        self.db = db
        self.store = store
        self.settings = settings
        self.guard = None
        self.guild = guild
        self.guilds = [guild]
        self.user = SimpleNamespace(id=42)
        self.http = FakeHTTP()

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
    def __init__(self, bot, *, staff=True, guild=True, lead=None, roles=None):
        self.client = bot
        self.guild = bot.guild if guild else None
        held = [LEADS] if staff and roles is None else list(roles or [])
        self.user = SimpleNamespace(
            id=USER,
            guild=SimpleNamespace(id=GUILD, roles=[], get_channel=lambda _id: None),
            roles=[SimpleNamespace(id=one) for one in held],
            guild_permissions=SimpleNamespace(
                manage_guild=staff, administrator=staff if lead is None else lead
            ),
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
    await store.set(GUILD, "structure_backup_shadow_channel_id", LOGS)
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
    return [item.label for item in view.children if isinstance(item, discord.ui.Button)]


def button(view, label):
    return next(item for item in view.children if getattr(item, "label", None) == label)


def mode_pick(view):
    return next(item for item in view.children if isinstance(item, sb.ModePick))


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
    assert len(STRUCTURE_BACKUP_KEYS) == len(set(STRUCTURE_BACKUP_KEYS)) == 33
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
    assert not [key for key in KEY_TYPES if key.startswith("structure_backup_say_")]
    for name in WORDS:
        with pytest.raises(SettingError):
            bot.store.get(GUILD, f"structure_backup_say_{name}")
    with pytest.raises(SettingError):
        coerce_value("structure_backup_notice_text", "{member} changes")
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


async def test_a_change_sentence_stored_before_they_left_the_settings_is_ignored_at_boot(
    bot, guild, db, caplog
):
    await sb.take_snapshot(bot, guild)
    await db.conn.execute(
        "INSERT INTO settings(guild_id, key, value, updated_at) VALUES (?, ?, ?, ?)",
        (GUILD, "structure_backup_say_role_added", json.dumps("New role: {role}"), "2026-10-05"),
    )
    await db.conn.commit()
    guild.roles.append(role(MODS, "Mods", 2, 1))

    with caplog.at_level("WARNING", logger="black_bloc.settings_store"):
        await bot.store.load()
    taken = await sb.take_snapshot(bot, guild)

    assert "settings ignored: structure_backup_say_role_added" in caplog.text
    assert [one["text"] for one in taken.changes] == ["Role **Mods** was added."]
    assert "structure_backup_say_role_added" not in bot.store.all(GUILD)


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
        await sb.run_daily(bot, guild, PHOENIX_5AM + timedelta(days=n))

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


async def test_a_failed_daily_look_is_tried_three_times_spread_across_the_day(bot, guild, db):
    guild.fetch_raises = refused()

    outcomes = []
    for minutes in (0, 10, 230, 240, 250, 480, 490, 720, 900):
        taken = await sb.run_daily(bot, guild, PHOENIX_5AM + timedelta(minutes=minutes))
        outcomes.append(getattr(taken, "outcome", None))

    assert outcomes == [FAILED, None, None, FAILED, None, FAILED, None, None, None]
    assert (await kinds(db)).count("structure.capture_failed") == 3
    guild.fetch_raises = None
    assert (await sb.run_daily(bot, guild, PHOENIX_5AM + timedelta(days=1))).outcome == SAVED


def test_a_late_hour_still_fits_its_three_tries_into_the_day():
    assert [sb.retry_gap(hour) for hour in (0, 4, 12, 20, 23)] == [240, 240, 240, 80, 20]


async def test_the_daily_look_does_nothing_while_off(bot, guild, db):
    await bot.store.set(GUILD, "structure_backup_mode", "off")
    assert await sb.run_daily(bot, guild, PHOENIX_5AM) is None

    assert await kinds(db) == [] and guild.fetches == 0
    assert await structure_store.look(db, GUILD) is None


async def test_a_daily_look_at_an_unavailable_server_leaves_a_row_that_says_why(
    bot, guild, db
):
    guild.unavailable = True

    taken = await sb.run_daily(bot, guild, PHOENIX_5AM)

    assert taken.outcome == FAILED and guild.fetches == 0
    looked = await structure_store.look(db, GUILD)
    assert (looked["outcome"], looked["last_day"], looked["attempts"]) == (
        FAILED,
        "2026-10-05",
        1,
    )
    assert looked["reason"] == sb.UNAVAILABLE
    assert await kinds(db) == ["structure.capture_failed"]
    assert await sb.run_daily(bot, guild, PHOENIX_5AM + timedelta(minutes=10)) is None
    guild.unavailable = False
    again = await sb.run_daily(bot, guild, PHOENIX_5AM + timedelta(hours=4))
    assert again.outcome == SAVED


async def changed_overnight(bot, guild):
    await sb.run_daily(bot, guild, PHOENIX_5AM)
    guild.roles.append(role(MODS, "Mods", 2, 1))
    return await sb.run_daily(bot, guild, PHOENIX_5AM + timedelta(days=1))


async def test_the_first_snapshot_ever_posts_no_notice(bot, guild, db):
    await sb.run_daily(bot, guild, PHOENIX_5AM)

    assert all(not channel.sent for channel in guild.channels.values())
    assert not {"structure.notice_posted", "structure.would_notice"} & set(await kinds(db))


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
    found = await details_of(db, "structure.would_notice")
    assert (found["mode"], found["channel_id"], found["aimed_at"]) == ("shadow", REHEARSAL, ALERTS)
    assert "structure.notice_posted" not in await kinds(db)


async def test_on_the_notice_goes_to_its_channel_with_no_rehearsal_line(bot, guild, db):
    await bot.store.set(GUILD, "structure_backup_mode", "on")
    await bot.store.set(GUILD, "structure_backup_channel_id", ALERTS)
    await bot.store.set(GUILD, "shadow_channel_id", REHEARSAL)

    await changed_overnight(bot, guild)

    (sent,) = guild.channels[ALERTS].sent
    assert sent["content"] is None
    assert not guild.channels[REHEARSAL].sent
    assert (await details_of(db, "structure.notice_posted"))["mode"] == "on"
    assert "structure.would_notice" not in await kinds(db)


async def test_the_notice_is_optional(bot, guild, db):
    await bot.store.set(GUILD, "structure_backup_notify", False)

    taken = await changed_overnight(bot, guild)

    assert taken.outcome == SAVED and taken.changes
    assert all(not channel.sent for channel in guild.channels.values())
    assert not {"structure.notice_posted", "structure.would_notice"} & set(await kinds(db))


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
    assert [one.name for one in shown["embed"].fields] == ["Mode", "Notice", "Latest snapshot"]
    assert field(shown["embed"], "Notice") == f"<#{LOGS}>"
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


ADMIN = discord.Permissions(administrator=True).value
EVERYTHING = discord.Permissions.all().value
MORE = "…and {n} more — the Structure page lists every one."


async def test_a_snapshot_taken_by_hand_never_hides_a_change_from_the_daily_notice(
    bot, guild, db
):
    guild.roles.append(role(MODS, "Mods", 2, 1))
    first = await sb.run_daily(bot, guild, PHOENIX_5AM)
    guild.roles[-1].permissions = discord.Permissions(2 | ADMIN)
    by_hand = await sb.take_snapshot(bot, guild, actor=SimpleNamespace(id=USER))
    assert by_hand.outcome == SAVED and not guild.channels[LOGS].sent

    daily = await sb.run_daily(bot, guild, PHOENIX_5AM + timedelta(days=1))

    assert daily.outcome == UNCHANGED
    (sent,) = guild.channels[LOGS].sent
    said = sent["embed"].description.splitlines()
    assert said[0] == f"1 change(s) since the snapshot of {sb.when_words(first.row['taken_at'])}."
    assert said[1:] == ["• Role **Mods** gained: Administrator."]
    found = await details_of(db, "structure.would_notice")
    assert (found["since_id"], found["snapshot_id"]) == (first.row["id"], by_hand.row["id"])
    assert (await structure_store.look(db, GUILD))["noticed_id"] == by_hand.row["id"]

    await sb.run_daily(bot, guild, PHOENIX_5AM + timedelta(days=2))
    assert len(guild.channels[LOGS].sent) == 1


async def test_a_notice_covers_every_snapshot_since_the_last_one_it_covered(bot, guild, db):
    await sb.run_daily(bot, guild, PHOENIX_5AM)
    guild.roles.append(role(MODS, "Mods", 2, 1))
    await sb.take_snapshot(bot, guild)
    guild.roles.append(role(100, "Streamers", 0, 3))
    await sb.take_snapshot(bot, guild)
    guild.channels[STAFF].name = "staff-room"

    daily = await sb.run_daily(bot, guild, PHOENIX_5AM + timedelta(days=1))

    assert daily.outcome == SAVED and len(daily.changes) == 1
    said = guild.channels[LOGS].sent[0]["embed"].description.splitlines()
    assert said[0].startswith("3 change(s) since the snapshot of ")
    assert sorted(said[1:]) == [
        "• Channel **staff** was renamed **staff-room**.",
        "• Role **Mods** was added.",
        "• Role **Streamers** was added.",
    ]


async def test_a_change_made_and_undone_between_two_daily_looks_is_not_a_notice(bot, guild, db):
    await sb.run_daily(bot, guild, PHOENIX_5AM)
    guild.roles.append(role(MODS, "Mods", 2, 1))
    await sb.take_snapshot(bot, guild)
    guild.roles.pop()

    daily = await sb.run_daily(bot, guild, PHOENIX_5AM + timedelta(days=1))

    assert daily.outcome == SAVED and not guild.channels[LOGS].sent
    assert (await structure_store.look(db, GUILD))["noticed_id"] == daily.row["id"]


async def test_a_notice_that_failed_is_owed_and_the_next_daily_look_pays_it(bot, guild, db):
    guild.channels[LOGS].send_raises = refused()
    await changed_overnight(bot, guild)
    assert (await kinds(db))[-1] == "structure.notice_failed"
    guild.channels[LOGS].send_raises = None

    daily = await sb.run_daily(bot, guild, PHOENIX_5AM + timedelta(days=2))

    assert daily.outcome == UNCHANGED
    notices = [one for one in guild.channels[LOGS].sent if one.get("embed") is not None]
    assert "• Role **Mods** was added." in notices[-1]["embed"].description


async def test_with_the_notice_switched_off_nothing_is_owed_when_it_comes_back_on(
    bot, guild, db
):
    await bot.store.set(GUILD, "structure_backup_notify", False)
    await changed_overnight(bot, guild)
    await bot.store.set(GUILD, "structure_backup_notify", True)

    await sb.run_daily(bot, guild, PHOENIX_5AM + timedelta(days=2))

    assert all(not channel.sent for channel in guild.channels.values())


async def test_keeping_one_snapshot_still_keeps_the_one_the_next_notice_starts_from(
    bot, guild, db
):
    await bot.store.set(GUILD, "structure_backup_keep", 1)
    first = await sb.run_daily(bot, guild, PHOENIX_5AM)
    guild.roles.append(role(MODS, "Mods", 2, 1))
    await sb.take_snapshot(bot, guild)
    assert await structure_store.get(db, GUILD, first.row["id"]) is not None

    await sb.run_daily(bot, guild, PHOENIX_5AM + timedelta(days=1))

    assert "• Role **Mods** was added." in guild.channels[LOGS].sent[0]["embed"].description
    guild.roles.append(role(100, "Streamers", 0, 3))
    await sb.take_snapshot(bot, guild)
    assert await structure_store.get(db, GUILD, first.row["id"]) is None
    assert await structure_store.count(db, GUILD) == 2


async def test_the_first_snapshot_ever_taken_by_hand_is_where_the_first_notice_starts(
    bot, guild, db
):
    first = await sb.take_snapshot(bot, guild)
    guild.roles.append(role(MODS, "Mods", 2, 1))
    await sb.take_snapshot(bot, guild)

    await sb.run_daily(bot, guild, PHOENIX_5AM)

    found = await details_of(db, "structure.would_notice")
    assert found["since_id"] == first.row["id"] and found["changes"] == 1


async def test_a_look_by_hand_that_fails_never_brings_a_second_daily_look(bot, guild, db):
    assert (await sb.run_daily(bot, guild, PHOENIX_5AM)).outcome == SAVED
    guild.fetch_raises = refused()
    assert (await sb.take_snapshot(bot, guild)).outcome == FAILED
    guild.fetch_raises = None

    for hours in (1, 4, 8):
        assert await sb.run_daily(bot, guild, PHOENIX_5AM + timedelta(hours=hours)) is None

    assert guild.fetches == 2


def shown_and_more(text):
    lines = text.splitlines()
    return ([line for line in lines if line.startswith("• ")], lines)


def forty_roles_reversed(guild):
    for n in range(40):
        guild.roles.append(role(100 + n, f"role-{n:02d}", 0, 3 + n))

    def change():
        for one in guild.roles[1:]:
            one.position = 43 - one.position

    return change


async def test_forty_moves_keep_the_line_that_counts_the_rest_on_the_panel(bot, guild):
    await bot.store.set(GUILD, "structure_backup_notice_lines", 40)
    change = forty_roles_reversed(guild)
    await sb.take_snapshot(bot, guild)
    change()
    _, view = await sb.build_panel(bot, guild)
    press = FakeInteraction(bot)

    await button(view, "What changed").callback(press)

    value = field(press.rendered["embed"], "What changed")
    shown, lines = shown_and_more(value)
    assert len(value) <= 1024 and 1 <= len(shown) < 40
    assert all(line.endswith(".") and "moved" in line for line in shown)
    assert lines == [*shown, MORE.format(n=40 - len(shown))]


async def test_forty_moves_all_fit_the_notice_and_fifteen_say_how_many_more(bot, guild):
    await bot.store.set(GUILD, "structure_backup_notice_lines", 40)
    change = forty_roles_reversed(guild)
    await sb.run_daily(bot, guild, PHOENIX_5AM)
    change()

    await sb.run_daily(bot, guild, PHOENIX_5AM + timedelta(days=1))
    await bot.store.set(GUILD, "structure_backup_notice_lines", 15)
    change()
    await sb.run_daily(bot, guild, PHOENIX_5AM + timedelta(days=2))

    whole, cut = (one["embed"].description for one in guild.channels[LOGS].sent)
    shown, lines = shown_and_more(whole)
    assert lines[0].startswith("40 change(s)") and lines[1:] == shown and len(shown) == 40
    shown, lines = shown_and_more(cut)
    assert len(shown) == 15 and lines[-1] == MORE.format(n=25) and len(lines) == 17


def allowed(everything):
    allow, deny = (EVERYTHING, 0) if everything else (0, EVERYTHING)
    return discord.PermissionOverwrite.from_pair(
        discord.Permissions(allow), discord.Permissions(deny)
    )


def thirty_long_overwrites(guild):
    leads = guild.roles[1]
    rooms = [FakeChannel(600 + n, f"room-{n:02d}", category_id=40) for n in range(30)]
    for room in rooms:
        guild.channels[room.id] = room

    def flip(everything):
        for room in rooms:
            room.overwrites = {leads: allowed(everything)}

    flip(True)
    return flip


async def test_thirty_long_permission_lines_never_push_out_the_count_of_the_rest(bot, guild):
    await bot.store.set(GUILD, "structure_backup_notice_lines", 40)
    flip = thirty_long_overwrites(guild)
    await sb.run_daily(bot, guild, PHOENIX_5AM)
    flip(False)

    await sb.run_daily(bot, guild, PHOENIX_5AM + timedelta(days=1))
    _, view = await sb.build_panel(bot, guild)
    flip(True)
    press = FakeInteraction(bot)
    await button(view, "What changed").callback(press)

    described = guild.channels[LOGS].sent[0]["embed"].description
    shown, lines = shown_and_more(described)
    assert len(described) <= 4096 and lines[0].startswith("30 change(s)")
    assert 1 <= len(shown) < 30 and all(line.endswith(".") for line in shown)
    assert lines[1:] == [*shown, MORE.format(n=30 - len(shown))]
    value = field(press.rendered["embed"], "What changed")
    shown, lines = shown_and_more(value)
    assert len(value) <= 1024 and len(shown) == 1
    assert lines == [*shown, MORE.format(n=29)]


async def test_one_line_longer_than_the_field_is_cut_at_a_word_with_an_ellipsis(bot, guild):
    leads = guild.roles[1]
    guild.channels[STAFF].overwrites = {leads: allowed(True)}
    taken = await sb.take_snapshot(bot, guild)
    guild.channels[STAFF].overwrites = {leads: allowed(False)}
    (whole,) = await sb.changes_since(bot, guild, taken.row)
    full = f"• {whole['text']}"
    assert len(full) > 1024
    _, view = await sb.build_panel(bot, guild)
    press = FakeInteraction(bot)

    await button(view, "What changed").callback(press)

    value = field(press.rendered["embed"], "What changed")
    assert len(value) <= 1024 and "\n" not in value and value.endswith("…")
    kept = value[:-1]
    assert len(kept) > 512 and full.startswith(kept) and full[len(kept)] == " "
    assert "more" not in value.splitlines()[-1]


def test_cutting_keeps_whole_words_and_never_runs_past_the_limit():
    assert sb.cut("one two three", 13) == "one two three"
    assert sb.cut("one two three", 12) == "one two…"
    assert sb.cut("one two three", 8) == "one two…"
    assert sb.cut("x" * 50, 10) == "x" * 9 + "…"
    assert sb.cut("ab", 1) == "…" and sb.cut("ab", 0) == ""


async def test_a_line_longer_than_the_whole_notice_is_cut_and_nothing_is_miscounted(bot):
    long = [{"text": "word " * 2000}, {"text": "short"}]

    lines = sb.change_lines(bot.store, GUILD, long, 4000)

    assert len(lines) == 2 and lines[0].endswith("…") and lines[1] == MORE.format(n=1)
    assert len("\n".join(lines)) <= 4000


LIMITS = [
    ("structure_backup_take_label", 80),
    ("structure_backup_changes_label", 80),
    ("structure_backup_site_label", 80),
    ("structure_backup_mode_label", 150),
    ("structure_backup_panel_title", 256),
    ("structure_backup_notice_title", 256),
    ("structure_backup_latest_label", 256),
    ("structure_backup_look_label", 256),
    ("structure_backup_panel_footer", 256),
    ("structure_backup_none_yet", 1024),
    ("structure_backup_no_changes_said", 1024),
    ("structure_backup_off_said", 4096),
]


@pytest.mark.parametrize(("key", "limit"), LIMITS)
def test_wording_longer_than_discord_holds_is_refused_at_save_in_words(key, limit):
    assert coerce_value(key, "x" * limit) == "x" * limit

    with pytest.raises(SettingError) as refused_save:
        coerce_value(key, "x" * (limit + 1))

    said = str(refused_save.value)
    assert f"{limit + 1} characters" in said and f"holds {limit} on Discord" in said
    assert "nothing was changed" in said and "Take 1 out" in said


def test_every_structure_wording_key_has_a_limit_its_own_default_fits():
    words = [key for key in STRUCTURE_BACKUP_KEYS if KEY_TYPES[key] == "text"]

    assert set(STRUCTURE_BACKUP_LIMITS) == set(words) and len(words) == 24
    for key in words:
        assert len(STRUCTURE_BACKUP_DEFAULTS[key]) <= STRUCTURE_BACKUP_LIMITS[key], key
    assert set(STRUCTURE_BACKUP_LIMITS.values()) == {80, 150, 256, 1024, 4096}


def stored_already(bot, monkeypatch, **values):
    real = bot.store.get
    monkeypatch.setattr(
        bot.store, "get", lambda guild_id, key, *rest: values.get(key, real(guild_id, key, *rest))
    )


async def test_wording_stored_before_the_limits_cannot_break_the_panel(
    bot, guild, monkeypatch
):
    await sb.take_snapshot(bot, guild)
    guild.roles.append(role(MODS, "Mods", 2, 1))
    stored_already(
        bot,
        monkeypatch,
        **{key: "word " * 2000 for key in STRUCTURE_BACKUP_LIMITS},
    )
    found = await sb.changes_since(bot, guild, await structure_store.latest(bot.db, GUILD))

    embed, view = await sb.build_panel(bot, guild, note="word " * 2000, found=found)

    assert len(embed.title) <= 256 and len(embed) + len(view.footer) <= 6000
    assert len(embed.fields) == 5
    for one in embed.fields:
        assert 1 <= len(one.name) <= 256 and 1 <= len(one.value) <= 1024
    assert all(len(label) <= 80 for label in labels(view))
    assert len(mode_pick(view).placeholder) <= 150 and len(view.footer) <= 256
    assert embed.to_dict() and all(item.to_component_dict() for item in view.children)


async def test_wording_stored_before_the_limits_cannot_break_the_notice(
    bot, guild, monkeypatch
):
    stored_already(
        bot,
        monkeypatch,
        structure_backup_notice_title="word " * 2000,
        structure_backup_notice_text="word " * 2000,
        structure_backup_notice_more="word " * 2000,
        structure_backup_notice_lines=1,
    )
    await sb.run_daily(bot, guild, PHOENIX_5AM)
    guild.roles.append(role(MODS, "Mods", 2, 1))
    guild.roles.append(role(100, "Streamers", 0, 3))

    await sb.run_daily(bot, guild, PHOENIX_5AM + timedelta(days=1))

    embed = guild.channels[LOGS].sent[0]["embed"]
    assert len(embed.title) <= 256 and len(embed.description) <= 4096 and len(embed) <= 6000
    assert "• Role **Mods** was added." in embed.description.splitlines()


@pytest.mark.parametrize("broken", ["{id.nope}", "{id[a]}", "{id!x}", "{0}", "{id:q}"])
async def test_a_template_that_breaks_in_any_way_falls_back_to_the_shipped_wording(
    bot, monkeypatch, broken
):
    stored_already(bot, monkeypatch, structure_backup_saved_said=broken)

    assert sb.said(bot.store, GUILD, "structure_backup_saved_said", id=3) == "Snapshot #3 saved."


def test_settings_lists_structure_backup_with_every_other_feature_mode(bot):
    assert "**Structure backup** — shadow · `/structure` to change" in mode_lines(
        bot.store, GUILD
    )


async def test_the_panel_carries_the_mode_control_and_it_changes_the_mode(bot, guild, db):
    _, view = await sb.build_panel(bot, guild)
    pick = mode_pick(view)
    assert pick.placeholder == "Mode"
    assert [(one.value, one.default) for one in pick.options] == [
        ("off", False),
        ("shadow", True),
        ("on", False),
    ]
    press = FakeInteraction(bot)
    pick._values = ["on"]

    await pick.callback(press)

    assert bot.store.get(GUILD, "structure_backup_mode") == "on"
    shown = press.rendered
    assert field(shown["embed"], "Mode") == "on"
    assert shown["embed"].description == "**structure_backup_mode** is now on."
    assert [one.default for one in mode_pick(shown["view"]).options] == [False, False, True]
    found = await details_of(db, "settings.set")
    assert (found["key"], found["value"], found["actor_id"]) == (
        "structure_backup_mode",
        "on",
        USER,
    )


async def test_the_mode_control_brings_the_feature_back_from_off(bot, guild):
    await bot.store.set(GUILD, "structure_backup_mode", "off")
    _, view = await sb.build_panel(bot, guild)
    assert labels(view) == ["Open the Structure page"]
    press = FakeInteraction(bot)
    pick = mode_pick(view)
    pick._values = ["shadow"]

    await pick.callback(press)

    assert labels(press.rendered["view"]) == ["Take one now", "Open the Structure page"]


async def test_the_mode_control_is_refused_to_someone_who_is_not_staff(bot, guild):
    _, view = await sb.build_panel(bot, guild)
    press = FakeInteraction(bot, staff=False)
    pick = mode_pick(view)
    pick._values = ["off"]

    await pick.callback(press)

    assert "staff only" in press.said[0] and not press.edits
    assert bot.store.get(GUILD, "structure_backup_mode") == "shadow"


def test_reachable_on_the_panel_counts_the_picker_cap_and_the_search(monkeypatch):
    beyond = settings_panel.keys_in("core")[settings_panel.SELECT_LIMIT]
    first = settings_panel.keys_in("core")[0]
    assert beyond not in settings_panel.editable_options("core").keys
    assert reachable_on_the_panel(beyond) and reachable_on_the_panel(first)

    monkeypatch.setattr(settings_panel, "needs_find", lambda group: False)

    assert reachable_on_the_panel(first) and not reachable_on_the_panel(beyond)


EVIL = "**x** [click](https://evil.example)"
TAMED = "\\*\\*x\\*\\* \\[click](https://evil.example)"


async def test_a_name_written_as_markdown_is_shown_as_written_on_the_panel(bot, guild):
    await sb.take_snapshot(bot, guild)
    guild.roles.append(role(MODS, EVIL, 2, 1))
    guild.channels[STAFF].topic = EVIL
    _, view = await sb.build_panel(bot, guild)
    press = FakeInteraction(bot)

    await button(view, "What changed").callback(press)

    value = field(press.rendered["embed"], "What changed")
    assert value.splitlines() == [
        f"• Role **{TAMED}** was added.",
        f"• Channel **staff**'s topic changed from nothing to {TAMED}.",
    ]


async def test_a_name_written_as_markdown_is_shown_as_written_in_the_notice(bot, guild):
    await sb.run_daily(bot, guild, PHOENIX_5AM)
    guild.roles.append(role(MODS, EVIL, 2, 1))

    taken = await sb.run_daily(bot, guild, PHOENIX_5AM + timedelta(days=1))

    said = guild.channels[LOGS].sent[0]["embed"].description
    assert f"• Role **{TAMED}** was added." in said and " [click](" not in said
    assert [one["text"] for one in taken.changes] == [f"Role **{EVIL}** was added."]


async def test_a_capture_with_no_channels_never_replaces_the_only_good_snapshot(
    bot, guild, db
):
    await bot.store.set(GUILD, "structure_backup_keep", 1)
    good = await sb.take_snapshot(bot, guild)
    held = dict(guild.channels)
    guild.channels.clear()

    taken = await sb.take_snapshot(bot, guild)

    guild.channels.update(held)
    assert taken.outcome == FAILED and "no channels" in taken.reason
    assert (await structure_store.latest(db, GUILD))["id"] == good.row["id"]
    assert await structure_store.count(db, GUILD) == 1


async def test_discord_not_answering_is_a_timeout_in_words_and_the_lock_is_let_go(
    bot, guild, db, monkeypatch
):
    monkeypatch.setattr(sb, "FETCH_SECONDS", 0.05)
    guild.hangs = True

    taken = await sb.take_snapshot(bot, guild)

    assert taken.outcome == FAILED
    assert "Discord could not be reached" in taken.reason
    assert "refused" not in taken.reason and "View Channels" not in taken.reason
    assert not sb.lock_for(bot).locked()
    guild.hangs = False
    assert (await sb.take_snapshot(bot, guild)).outcome == SAVED


def test_a_network_failure_is_never_worded_as_a_permission_problem():
    for exc in (TimeoutError(), ConnectionResetError("reset"), OSError("down")):
        said = sb.failure_reason(exc)
        assert "Discord could not be reached" in said and "refused" not in said


def test_the_fakes_refuse_every_call_they_were_not_told_about(bot, guild):
    tried = (
        (guild, "edit"),
        (guild, "create_role"),
        (guild, "create_text_channel"),
        (guild, "edit_role_positions"),
        (guild.roles[0], "edit"),
        (guild.roles[0], "delete"),
        (guild.channels[STAFF], "set_permissions"),
        (guild.channels[STAFF], "clone"),
        (guild.channels[STAFF], "create_webhook"),
        (guild.channels[STAFF], "create_invite"),
        (guild.channels[STAFF], "create_thread"),
        (bot.http, "request"),
        (bot.http, "edit_role"),
    )
    for thing, name in tried:
        with pytest.raises(AssertionError, match="must never call"):
            getattr(thing, name)()

    assert len(REFUSED) == len(tried)
    REFUSED.clear()


WRITE_NAMES = frozenset(
    {
        "edit",
        "delete",
        "move",
        "clone",
        "set_permissions",
        "add_roles",
        "remove_roles",
        "ban",
        "unban",
        "kick",
        "timeout",
        "purge",
        "prune_members",
        "follow",
        "publish",
        "pin",
        "unpin",
        "leave",
    }
)
WRITE_PREFIXES = ("create_", "delete_", "edit_", "bulk_")
NOT_A_WRITE = frozenset({"edit_original_response"})
REFLECTION = frozenset({"getattr", "setattr", "delattr", "hasattr"})
NEVER_NAMED = frozenset(
    {"Route", "http", "eval", "exec", "vars", "globals", "locals", "__import__"}
)
ALLOWED_IMPORTS = frozenset(
    {
        "__future__",
        "asyncio",
        "bisect",
        "collections",
        "collections.abc",
        "dataclasses",
        "datetime",
        "hashlib",
        "json",
        "logging",
        "typing",
        "discord",
        "discord.ext",
        "fastapi",
        "fastapi.responses",
        "black_bloc.actionlog",
        "black_bloc.command_visibility",
        "black_bloc.logkinds",
        "black_bloc.loops",
        "black_bloc.panels",
        "black_bloc.settings_store",
        "black_bloc.shadow",
        "black_bloc.structure",
        "black_bloc.structure_capture",
        "black_bloc.structure_diff",
        "black_bloc.structure_store",
        "black_bloc.timezones",
        "black_bloc.cogs.core",
        "black_bloc.cogs.moderation.structure_backup",
        "black_bloc.api.auth",
        "black_bloc.api.names",
        "black_bloc.api.writes",
    }
)
STRUCTURE_MODULES = (
    "structure.py",
    "structure_capture.py",
    "structure_diff.py",
    "structure_store.py",
    "cogs/moderation/structure_backup.py",
    "api/tools/structure.py",
)
COG = "cogs/moderation/structure_backup.py"


def is_write(name):
    if name in NOT_A_WRITE:
        return False
    return name in WRITE_NAMES or name.startswith(WRITE_PREFIXES)


def reached(module, node):
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    package = ["black_bloc", *module.split("/")[:-1]]
    base = package[: len(package) - (node.level - 1)] if node.level else []
    if node.module:
        return [".".join([*base, node.module])]
    return [".".join([*base, alias.name]) for alias in node.names]


def named_badly(name):
    return name in NEVER_NAMED or is_write(name)


def write_paths(source, module=COG):
    """Every way this source could reach a write: by name, by reflection, by http, by import."""
    found = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Attribute) and named_badly(node.attr):
            found.append(f"line {node.lineno}: .{node.attr}")
        elif isinstance(node, ast.Name) and named_badly(node.id):
            found.append(f"line {node.lineno}: {node.id}")
        elif isinstance(node, ast.Import | ast.ImportFrom):
            for wanted in reached(module, node):
                if wanted not in ALLOWED_IMPORTS:
                    found.append(f"line {node.lineno}: import of {wanted}")
            for alias in node.names:
                for name in (alias.name.rsplit(".", 1)[-1], alias.asname or ""):
                    if named_badly(name):
                        found.append(f"line {node.lineno}: import named {name}")
        elif isinstance(node, ast.Call) and getattr(node.func, "id", None) in REFLECTION:
            name = node.args[1] if len(node.args) > 1 else None
            if not (isinstance(name, ast.Constant) and isinstance(name.value, str)):
                found.append(f"line {node.lineno}: {node.func.id} with a computed name")
            elif named_badly(name.value):
                found.append(f"line {node.lineno}: {node.func.id} of {name.value}")
    return found


def test_no_structure_module_can_write_a_role_a_channel_or_a_permission():
    """Capture and compare only: restoring is the owner's separate decision."""
    package = pathlib.Path(sb.__file__).resolve().parents[2]
    found = {
        name: write_paths((package / name).read_text(encoding="utf-8"), name)
        for name in STRUCTURE_MODULES
    }

    assert not {name: paths for name, paths in found.items() if paths}


SPELLINGS = [
    "async def go(role):\n    await role.edit(name='x')",
    "getattr(role, 'edit')(name='x')",
    "go = role.edit\nresult = go(name='x')",
    "role.delete",
    "bot.http.edit_role(1, 2, name='x')",
    "client = bot.http",
    "Route('PATCH', '/guilds/1/roles/2')",
    "from discord.http import Route",
    "import discord.http",
    "from discord import http",
    "from x import set_permissions",
    "from discord.abc import GuildChannel as edit",
    "from ..community.events import change_settings",
    "from ... import modcases",
    "import importlib",
    "channel.clone()",
    "channel.create_webhook(name='x')",
    "channel.create_invite()",
    "channel.create_thread(name='x')",
    "guild.create_role(name='x')",
    "guild.edit_role_positions({})",
    "channel.set_permissions(role, overwrite=None)",
    "getattr(role, name)()",
    "setattr(role, name, 1)",
    "getattr(bot, 'http')",
    "vars(role)['edit']()",
    "member.timeout(None)",
]


@pytest.mark.parametrize("source", SPELLINGS)
def test_the_guard_trips_on_every_spelling_of_a_write(source):
    assert write_paths(source), source


def test_the_guard_lets_the_reads_this_feature_makes_through():
    reads = (
        "async def go(guild, channel, interaction):\n"
        "    roles = await guild.fetch_roles()\n"
        "    channels = await guild.fetch_channels()\n"
        "    for target, overwrite in channel.overwrites.items():\n"
        "        allow, deny = overwrite.pair()\n"
        "    name = getattr(channel, 'name', None)\n"
        "    await channel.send('x')\n"
        "    await interaction.response.send_message('x')\n"
        "    await interaction.response.defer()\n"
        "    await interaction.edit_original_response(content='x')\n"
        "from ... import shadow, structure_store\n"
        "from ..core import set_key\n"
        "import discord\n"
    )

    assert write_paths(reads) == []


# ---------------------------------------------------------------- leads only (2026-10-05)

PRIVATE_ROLE = "Zebra Council"
PRIVATE_CHANNEL = "zebra-private"
LOG_DETAIL_KEYS = frozenset(
    {
        "via",
        "source",
        "snapshot_id",
        "previous_id",
        "since_id",
        "roles",
        "categories",
        "channels",
        "overwrites",
        "changes",
        "removed",
        "reason",
        "mode",
        "key",
        "channel_id",
        "aimed_at",
        "actor_id",
    }
)


async def opened_by(bot, interaction):
    cog = sb.StructureBackup(bot)
    await cog.structure.callback(cog, interaction)
    return interaction


def test_the_rule_is_the_owner_an_administrator_or_the_role_and_nobody_else(bot, guild):
    def person(user_id=USER, *, admin=False, roles=()):
        return SimpleNamespace(
            id=user_id,
            roles=[SimpleNamespace(id=one) for one in roles],
            guild_permissions=SimpleNamespace(manage_guild=True, administrator=admin),
        )

    assert sb.may_see(bot.store, guild, person(OWNER))
    assert sb.may_see(bot.store, guild, OWNER) and sb.may_see(bot.store, guild, str(OWNER))
    assert sb.may_see(bot.store, guild, person(admin=True))
    assert not sb.may_see(bot.store, guild, person(roles=[LEADS, MODS]))
    assert not sb.may_see(bot.store, guild, USER)
    assert not sb.may_see(bot.store, guild, None)
    assert not sb.may_see(bot.store, None, person(admin=True))
    assert not sb.may_see(bot.store, guild, "not an id")
    truthy = SimpleNamespace(id=USER, roles=[], guild_permissions=SimpleNamespace(administrator=1))
    assert not sb.may_see(bot.store, guild, truthy)


async def test_the_owner_opens_the_panel_holding_no_role_and_no_permission_bit(bot, guild):
    guild.owner_id = USER

    shown = await opened_by(bot, FakeInteraction(bot, lead=False, roles=[]))

    assert shown.rendered["embed"].title == "Server structure" and shown.rendered["view"]


async def test_an_administrator_opens_the_panel(bot):
    shown = await opened_by(bot, FakeInteraction(bot, lead=True, roles=[]))

    assert shown.rendered["embed"].title == "Server structure"


async def test_a_holder_of_the_structure_role_opens_the_panel(bot):
    await bot.store.set(GUILD, "structure_backup_role_id", MODS)

    shown = await opened_by(bot, FakeInteraction(bot, lead=False, roles=[MODS]))

    assert shown.rendered["embed"].title == "Server structure"


async def test_ordinary_staff_are_refused_at_the_command_in_words(bot, db):
    await bot.store.set(GUILD, "structure_backup_role_id", MODS)

    refused_ = await opened_by(bot, FakeInteraction(bot, lead=False, roles=[LEADS]))

    assert refused_.said == [sb.LEADS_ONLY] and not refused_.edits
    assert "view" not in refused_.response.messages[0]
    assert refused_.response.messages[0]["ephemeral"] is True
    for needed in ("every role, channel and permission", "server's leads", "Ask the server owner"):
        assert needed in sb.LEADS_ONLY
    assert await kinds(db) == []


async def test_with_no_role_set_only_the_owner_and_administrators_get_in(bot):
    assert bot.store.get(GUILD, "structure_backup_role_id") is None

    refused_ = await opened_by(bot, FakeInteraction(bot, lead=False, roles=[LEADS, MODS, 0]))

    assert refused_.said == [sb.LEADS_ONLY]
    assert (await opened_by(bot, FakeInteraction(bot, lead=True))).rendered["view"]


async def test_a_member_is_still_refused_as_not_staff_before_the_leads_rule_is_asked(bot):
    await bot.store.set(GUILD, "structure_backup_role_id", MODS)
    outsider = FakeInteraction(bot, staff=False, roles=[MODS])

    await opened_by(bot, outsider)

    assert "staff only" in outsider.said[0] and sb.LEADS_ONLY not in outsider.said


async def full_panel(bot, guild):
    await sb.take_snapshot(bot, guild)
    _, view = await sb.build_panel(bot, guild)
    return view


def controls(view):
    return [item for item in view.children if getattr(item, "url", None) is None]


async def test_every_control_on_the_panel_refuses_ordinary_staff_in_words(bot, guild, db):
    view = await full_panel(bot, guild)
    before = await kinds(db)

    assert [type(item) for item in controls(view)] == [
        sb.TakeButton,
        sb.ChangesButton,
        sb.ModePick,
    ]
    assert len(view.children) == len(controls(view)) + 1
    for item in controls(view):
        press = FakeInteraction(bot, lead=False, roles=[LEADS])
        if isinstance(item, sb.ModePick):
            item._values = ["off"]
        await item.callback(press)
        assert press.said == [sb.LEADS_ONLY], type(item)
        assert not press.edits and not press.response.deferred, type(item)
    assert guild.fetches == 1
    assert await structure_store.count(db, GUILD) == 1
    assert bot.store.get(GUILD, "structure_backup_mode") == "shadow"
    assert await kinds(db) == before


async def test_someone_who_loses_the_role_mid_panel_is_refused_on_the_next_press(bot, guild, db):
    await bot.store.set(GUILD, "structure_backup_role_id", MODS)
    opening = await opened_by(bot, FakeInteraction(bot, lead=False, roles=[LEADS, MODS]))
    view = opening.rendered["view"]
    held = FakeInteraction(bot, lead=False, roles=[LEADS, MODS])
    await button(view, "Take one now").callback(held)
    assert held.rendered["embed"].description.startswith("Snapshot #")

    lost = FakeInteraction(bot, lead=False, roles=[LEADS])
    await button(held.rendered["view"], "What changed").callback(lost)
    unset = FakeInteraction(bot, lead=False, roles=[LEADS, MODS])
    await bot.store.clear(GUILD, "structure_backup_role_id")
    await button(held.rendered["view"], "Take one now").callback(unset)

    assert lost.said == [sb.LEADS_ONLY] and not lost.edits
    assert unset.said == [sb.LEADS_ONLY] and not unset.edits
    assert await structure_store.count(db, GUILD) == 1


def test_every_door_in_the_cog_is_behind_the_one_gate():
    source = pathlib.Path(sb.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)

    def calls(node):
        return {
            getattr(one.func, "id", None) for one in ast.walk(node) if isinstance(one, ast.Call)
        }

    pressed = [
        (one.name, item)
        for one in tree.body
        if isinstance(one, ast.ClassDef)
        for item in one.body
        if isinstance(item, ast.AsyncFunctionDef) and item.name == "callback"
    ]
    assert [name for name, _ in pressed] == ["TakeButton", "ChangesButton", "ModePick"]
    for name, item in pressed:
        first = item.body[0]
        assert isinstance(first, ast.If) and "lead_opened" in calls(first.test), name
        assert isinstance(first.body[0], ast.Return), name
    items = [
        one.name
        for one in tree.body
        if isinstance(one, ast.ClassDef)
        and any("ui" in ast.unparse(base) and "View" not in ast.unparse(base) for base in one.bases)
    ]
    assert items == [name for name, _ in pressed]
    commands_ = [
        item
        for one in tree.body
        if isinstance(one, ast.ClassDef)
        for item in one.body
        if isinstance(item, ast.AsyncFunctionDef)
        and any("app_commands.command" in ast.unparse(mark) for mark in item.decorator_list)
    ]
    assert [item.name for item in commands_] == ["structure"]
    assert "require_lead" in calls(commands_[0])
    gates = {
        one.name: calls(one)
        for one in tree.body
        if isinstance(one, ast.AsyncFunctionDef | ast.FunctionDef)
        and one.name in ("require_lead", "lead_opened", "is_lead")
    }
    assert "is_lead" in gates["require_lead"] and "is_lead" in gates["lead_opened"]
    assert gates["is_lead"] == {"may_see"}
    opened_calls = [
        one
        for one in ast.walk(tree)
        if isinstance(one, ast.Call) and getattr(one.func, "id", None) == "opened"
    ]
    assert len(opened_calls) == 1 and sb.may_see is structure_rules.may_see


async def test_in_shadow_with_no_channel_of_its_own_no_notice_is_posted_anywhere(bot, guild, db):
    await bot.store.clear(GUILD, "structure_backup_shadow_channel_id")
    await bot.store.set(GUILD, "shadow_channel_id", REHEARSAL)
    await bot.store.set(GUILD, "staff_channel_id", STAFF)
    await bot.store.set(GUILD, "structure_backup_channel_id", ALERTS)
    bot.guard = SimpleNamespace(test_channel_id=STAFF)

    taken = await changed_overnight(bot, guild)

    assert taken.outcome == SAVED and await structure_store.count(db, GUILD) == 2
    assert all(not channel.sent for channel in guild.channels.values())
    found = await kinds(db)
    assert found.count("structure.notice_unsent") == 1
    posted = {"structure.would_notice", "structure.notice_posted", "structure.notice_failed"}
    assert not posted & set(found)
    row = await details_of(db, "structure.notice_unsent")
    assert (row["mode"], row["key"], row["changes"]) == (
        "shadow",
        "structure_backup_shadow_channel_id",
        1,
    )
    assert row["reason"] == sb.NOTICE_UNSENT.format(key="structure_backup_shadow_channel_id")
    assert "Mods" not in json.dumps(row)


async def test_on_with_no_channel_set_no_notice_is_posted_and_nothing_falls_back(bot, guild, db):
    await bot.store.set(GUILD, "structure_backup_mode", "on")
    await bot.store.set(GUILD, "staff_channel_id", STAFF)
    await bot.store.set(GUILD, "shadow_channel_id", REHEARSAL)
    await bot.store.set(GUILD, "structure_backup_shadow_channel_id", ALERTS)

    await changed_overnight(bot, guild)

    assert all(not channel.sent for channel in guild.channels.values())
    row = await details_of(db, "structure.notice_unsent")
    assert (row["mode"], row["key"]) == ("on", "structure_backup_channel_id")
    assert "structure.notice_posted" not in await kinds(db)


async def test_a_notice_with_nowhere_to_go_is_said_once_and_is_not_owed(bot, guild, db):
    await bot.store.clear(GUILD, "structure_backup_shadow_channel_id")
    await changed_overnight(bot, guild)

    await sb.run_daily(bot, guild, PHOENIX_5AM + timedelta(days=2))
    await bot.store.set(GUILD, "structure_backup_shadow_channel_id", ALERTS)
    await sb.run_daily(bot, guild, PHOENIX_5AM + timedelta(days=3))

    assert (await kinds(db)).count("structure.notice_unsent") == 1
    assert not guild.channels[ALERTS].sent


async def test_in_shadow_the_rehearsal_line_says_when_the_real_notice_has_nowhere_to_go(
    bot, guild
):
    await changed_overnight(bot, guild)

    (sent,) = guild.channels[LOGS].sent
    assert sent["content"] == (
        "Rehearsal — this is where it would go: Nowhere — structure_backup_channel_id is blank."
    )


async def test_the_panel_states_where_the_notice_goes_or_that_it_goes_nowhere(bot, guild):
    async def notice():
        embed, _ = await sb.build_panel(bot, guild)
        return next((one.value for one in embed.fields if one.name == "Notice"), None)

    assert await notice() == f"<#{LOGS}>"
    await bot.store.clear(GUILD, "structure_backup_shadow_channel_id")
    await bot.store.set(GUILD, "shadow_channel_id", REHEARSAL)
    assert await notice() == "Nowhere — structure_backup_shadow_channel_id is blank."
    await bot.store.set(GUILD, "structure_backup_mode", "on")
    await bot.store.set(GUILD, "staff_channel_id", STAFF)
    assert await notice() == "Nowhere — structure_backup_channel_id is blank."
    await bot.store.set(GUILD, "structure_backup_channel_id", ALERTS)
    assert await notice() == f"<#{ALERTS}>"
    await bot.store.set(GUILD, "structure_backup_notify", False)
    assert await notice() == "Off — structure_backup_notify is false."
    await bot.store.set(GUILD, "structure_backup_mode", "off")
    assert await notice() is None


def test_the_two_notice_keys_say_blank_means_nowhere():
    for key, never in (
        ("structure_backup_channel_id", "staff channel"),
        ("structure_backup_shadow_channel_id", "shadow_channel_id"),
    ):
        assert "Blank means no notice is posted" in KEY_HELP[key], key
        assert "never falls back" in KEY_HELP[key] and never in KEY_HELP[key], key
    assert "Either one blank means no notice is posted" in KEY_HELP["structure_backup_mode"]
    assert KEY_TYPES["structure_backup_role_id"] == "role"
    assert "Blank means the owner and administrators only" in KEY_HELP["structure_backup_role_id"]
    assert "structure_backup_role_id" not in STRUCTURE_BACKUP_DEFAULTS


async def test_no_structure_log_row_carries_a_role_or_channel_name_or_a_change_list(
    bot, guild, db
):
    guild.roles.append(role(77, PRIVATE_ROLE, 8, 3))
    guild.channels[77] = FakeChannel(77, PRIVATE_CHANNEL, category_id=40)
    await bot.store.set(GUILD, "structure_backup_keep", 1)
    await sb.run_daily(bot, guild, PHOENIX_5AM)
    guild.roles[-1].name = f"{PRIVATE_ROLE} II"
    guild.channels[77].topic = f"what {PRIVATE_ROLE} decides"
    await sb.run_daily(bot, guild, PHOENIX_5AM + timedelta(days=1))
    await bot.store.clear(GUILD, "structure_backup_shadow_channel_id")
    guild.channels[77].name = f"{PRIVATE_CHANNEL}-2"
    await sb.run_daily(bot, guild, PHOENIX_5AM + timedelta(days=2))
    await bot.store.set(GUILD, "structure_backup_mode", "on")
    await bot.store.set(GUILD, "structure_backup_channel_id", 99999)
    guild.roles[-1].name = PRIVATE_ROLE
    await sb.run_daily(bot, guild, PHOENIX_5AM + timedelta(days=3))
    await bot.store.set(GUILD, "structure_backup_channel_id", ALERTS)
    await sb.run_daily(bot, guild, PHOENIX_5AM + timedelta(days=4))
    taken = await sb.take_snapshot(bot, guild, actor=SimpleNamespace(id=USER))
    await sb.record_download(bot, guild, SimpleNamespace(id=USER), taken.row)
    guild.fetch_raises = refused()
    await sb.take_snapshot(bot, guild)

    cur = await db.conn.execute(
        "SELECT kind, details, reason FROM action_log WHERE kind LIKE 'structure.%' ORDER BY id"
    )
    rows = await cur.fetchall()
    assert {row["kind"] for row in rows} == {
        "structure.captured",
        "structure.unchanged",
        "structure.pruned",
        "structure.would_notice",
        "structure.notice_unsent",
        "structure.notice_failed",
        "structure.notice_posted",
        "structure.downloaded",
        "structure.capture_failed",
    }
    assert PRIVATE_ROLE in guild.channels[ALERTS].sent[0]["embed"].description
    for row in rows:
        details = json.loads(row["details"] or "{}")
        assert set(details) <= LOG_DETAIL_KEYS, (row["kind"], set(details) - LOG_DETAIL_KEYS)
        said = f"{row['details']} {row['reason']}".lower()
        assert "zebra" not in said, row["kind"]
        assert not [one for one in details.values() if isinstance(one, list | dict)], row["kind"]
