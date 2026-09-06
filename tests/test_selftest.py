import inspect
import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import discord
import pytest

from black_bloc import selftest
from black_bloc.config import load_settings
from black_bloc.logkinds import VIA_BOOT, VIA_WEBSITE
from black_bloc.settings_store import KEY_TYPES, SettingsStore
from black_bloc.storage.db import Database

GUILD = 7
TEST_CHANNEL = 111
OTHER_CHANNEL = 222
STAFF_ROLE = 555
BOT_ID = 900


class FakePerms:
    def __init__(self, **granted):
        self.granted = granted

    def __getattr__(self, name):
        return self.granted.get(name, False)


class FakeRole:
    def __init__(self, role_id):
        self.id = role_id
        self.name = f"role-{role_id}"


class FakeMessage:
    def __init__(self, message_id, channel, kwargs):
        self.id = message_id
        self.channel = channel
        self.kwargs = kwargs


class FakeChannel:
    def __init__(self, channel_id, **granted):
        self.id = channel_id
        self.name = f"channel-{channel_id}"
        self.granted = granted or {
            "view_channel": True,
            "send_messages": True,
            "embed_links": True,
            "manage_messages": True,
        }
        self.messages = []
        self.bulk = []
        self.one_by_one = []
        self.refuse_bulk = False
        self.gone = set()

    def permissions_for(self, member):
        return FakePerms(**self.granted)

    async def send(self, **kwargs):
        message = FakeMessage(9000 + len(self.messages), self, kwargs)
        self.messages.append(message)
        return message

    async def delete_messages(self, messages):
        if self.refuse_bulk:
            raise discord.HTTPException(SimpleNamespace(status=400), "too old")
        self.bulk.append([one.id for one in messages])

    def get_partial_message(self, message_id):
        return SimpleNamespace(delete=lambda: self._delete_one(message_id))

    async def _delete_one(self, message_id):
        if message_id in self.gone:
            raise discord.NotFound(SimpleNamespace(status=404, reason="Not Found"), "gone")
        self.one_by_one.append(message_id)


class FakeGuild:
    def __init__(self):
        self.id = GUILD
        self.name = "Black in a Flash!"
        self.channels = {}
        self.roles = {}
        self.me = SimpleNamespace(id=BOT_ID)

    def add_channel(self, channel):
        self.channels[channel.id] = channel
        return channel

    def add_role(self, role):
        self.roles[role.id] = role
        return role

    def get_channel(self, channel_id):
        return self.channels.get(channel_id)

    def get_role(self, role_id):
        return self.roles.get(role_id)


class FakeBot:
    def __init__(self, db, store, settings, guild):
        self.db = db
        self.store = store
        self.settings = settings
        self.guild = guild
        self.guilds = [guild]

    def get_channel(self, channel_id):
        return self.guild.get_channel(channel_id)

    def is_ready(self):
        return True


@pytest.fixture
async def bot(tmp_path, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    settings = load_settings(
        _env_file=None, database_path=tmp_path / "t.sqlite3", test_channel_id=TEST_CHANNEL
    )
    db = Database(tmp_path / "t.sqlite3")
    await db.connect()
    store = SettingsStore(db, settings)
    await store.load()
    guild = FakeGuild()
    guild.add_channel(FakeChannel(TEST_CHANNEL))
    guild.add_channel(FakeChannel(OTHER_CHANNEL))
    guild.add_role(FakeRole(STAFF_ROLE))
    try:
        yield FakeBot(db, store, settings, guild)
    finally:
        await db.close()


def only(*checks):
    """Run against a named handful, so a test says what it is proving rather than 81 things."""

    def chosen(_bot):
        return tuple(checks)

    return chosen


async def kinds_in(db):
    cur = await db.conn.execute("SELECT kind, details FROM action_log ORDER BY id")
    return [(row["kind"], json.loads(row["details"] or "{}")) for row in await cur.fetchall()]


# --- the check registry ---------------------------------------------------------------------------


def test_the_config_family_is_read_off_the_registry_and_never_hand_listed():
    """Adding a channel key to `KEY_TYPES` must add a check with no edit here."""
    names = {check.name for check in selftest.config_checks()}
    wanted = {
        f"config.{key}" for key, kind in KEY_TYPES.items() if kind in ("channel", "role")
    }

    assert names == wanted
    assert "config.log_channel_id" in names
    assert "config.golive_live_role_id" in names
    # A list of channels is not one channel; the honeypot's traps are checked by the feature.
    assert "config.honeypot_channel_ids" not in names


def test_the_pool_check_is_one_check_of_its_own_inside_the_chat_feature():
    found = selftest.pool_checks()

    assert [check.name for check in found] == [selftest.POOL_CHECK]
    assert found[0].feature == "chat"


def test_the_registry_is_the_four_families_plus_the_one_pool_check(bot):
    names = [check.name for check in selftest.checks_for(bot)]

    assert names.count(selftest.POOL_CHECK) == 1
    assert len(names) == len(set(names))
    assert len(names) == (
        len(selftest.config_checks())
        + len(selftest.panel_checks())
        + len(selftest.read_checks(bot))
        + 1
        + len(selftest.send_checks())
    )


def answers(payload):
    async def fetch(_url):
        return payload

    return fetch


def refuses(reason="ClientError: nope"):
    async def fetch(_url):
        raise selftest.PeerUnreachable(reason)

    return fetch


async def test_the_pool_check_passes_when_both_bots_are_on_the_same_version(bot):
    from black_bloc.personas import POOL_VERSION, TROPES

    one = selftest.Run(bot=bot, guild=bot.guild)
    said = await selftest.check_pool(
        one,
        fetch=answers(
            {"gabi_personality_pool_version": POOL_VERSION, "gabi_personality_tropes": len(TROPES)}
        ),
    )

    assert f"pool v{POOL_VERSION} on both" in said
    assert f"same {len(TROPES)}" in said


async def test_the_pool_check_fails_by_name_and_says_which_side_is_ahead(bot):
    from black_bloc.personas import POOL_VERSION

    one = selftest.Run(bot=bot, guild=bot.guild)

    with pytest.raises(selftest.CheckFailed) as raised:
        await selftest.check_pool(
            one, fetch=answers({"gabi_personality_pool_version": POOL_VERSION + 1})
        )

    said = str(raised.value)
    assert f"v{POOL_VERSION + 1}" in said and f"v{POOL_VERSION}" in said
    assert "GABI is ahead" in said
    assert selftest.POOL_FIX in said


async def test_the_pool_check_says_this_bot_is_ahead_when_it_is(bot):
    from black_bloc.personas import POOL_VERSION

    one = selftest.Run(bot=bot, guild=bot.guild)

    with pytest.raises(selftest.CheckFailed) as raised:
        await selftest.check_pool(
            one, fetch=answers({"gabi_personality_pool_version": POOL_VERSION - 1})
        )

    assert "this bot is ahead" in str(raised.value)


async def test_a_matching_version_with_a_different_count_is_still_a_failure(bot):
    from black_bloc.personas import POOL_VERSION

    one = selftest.Run(bot=bot, guild=bot.guild)

    with pytest.raises(selftest.CheckFailed) as raised:
        await selftest.check_pool(
            one,
            fetch=answers(
                {"gabi_personality_pool_version": POOL_VERSION, "gabi_personality_tropes": 3}
            ),
        )

    assert "3 moods" in str(raised.value)


async def test_a_peer_that_does_not_say_its_pool_version_yet_is_a_pass_in_words(bot):
    one = selftest.Run(bot=bot, guild=bot.guild)

    said = await selftest.check_pool(one, fetch=answers({"ok": True}))

    assert "does not say its pool version yet" in said


async def test_a_network_failure_is_not_a_pool_failure(bot):
    one = selftest.Run(bot=bot, guild=bot.guild)

    said = await selftest.check_pool(one, fetch=refuses("TimeoutError: "))

    assert "could not reach GABI's health route" in said
    assert "TimeoutError" in said


async def test_no_peer_address_asks_nobody_and_says_so(bot, monkeypatch):
    """The registry refuses blank text, so this is the belt-and-braces path, not the panel's."""
    monkeypatch.setattr(bot.store, "get", lambda _guild_id, _key: "")
    one = selftest.Run(bot=bot, guild=bot.guild)

    assert "nothing was asked" in await selftest.check_pool(one, fetch=refuses())


def test_a_feature_that_deletes_messages_asks_for_manage_messages_and_the_rest_do_not():
    assert selftest.wanted_permissions("honeypot_channel_ids") == (
        "view_channel",
        "send_messages",
        "embed_links",
        "manage_messages",
    )
    assert selftest.wanted_permissions("modlog_channel_id")[-1] == "manage_messages"
    assert selftest.wanted_permissions("birthday_channel_id") == (
        "view_channel",
        "send_messages",
        "embed_links",
    )


async def test_an_unset_key_is_ok_because_unset_is_a_state_and_not_a_fault(bot):
    await bot.store.clear(GUILD, "golive_ping_role_id")
    one = selftest.Run(bot=bot, guild=bot.guild)

    assert await selftest.check_role_key(one, "golive_ping_role_id") == "not set"


async def test_a_role_that_left_the_server_fails_by_name(bot):
    await bot.store.set(GUILD, "golive_live_role_id", 4321)
    one = selftest.Run(bot=bot, guild=bot.guild)

    with pytest.raises(selftest.CheckFailed) as raised:
        await selftest.check_role_key(one, "golive_live_role_id")

    assert "4321" in str(raised.value) and "not in this server" in str(raised.value)


async def test_a_channel_missing_a_permission_fails_and_says_which_one(bot):
    thin = bot.guild.add_channel(
        FakeChannel(333, view_channel=True, send_messages=True, embed_links=False)
    )
    await bot.store.set(GUILD, "birthday_channel_id", thin.id)
    one = selftest.Run(bot=bot, guild=bot.guild)

    with pytest.raises(selftest.CheckFailed) as raised:
        await selftest.check_channel_key(one, "birthday_channel_id")

    assert "embed_links" in str(raised.value)

    await bot.store.set(GUILD, "birthday_channel_id", TEST_CHANNEL)
    said = await selftest.check_channel_key(one, "birthday_channel_id")

    assert "embed_links" in said and str(TEST_CHANNEL) in said


async def test_a_channel_that_is_gone_fails_rather_than_reading_as_unset(bot):
    await bot.store.set(GUILD, "birthday_channel_id", 999999)
    one = selftest.Run(bot=bot, guild=bot.guild)

    with pytest.raises(selftest.CheckFailed):
        await selftest.check_channel_key(one, "birthday_channel_id")


def test_the_read_family_is_the_apps_own_route_table_and_skips_what_needs_filling_in(bot):
    found = dict(selftest.readable_routes(bot))

    assert "/api/status" in found and "/api/actions" in found
    # A path parameter has nothing to fill it in with, and the sign-in routes are not a page read.
    assert not [path for path in found if "{" in path]
    assert "/api/auth/login" not in found
    # `/api/auth/me` takes the Request, so there is nothing to call it with either.
    assert "/api/auth/me" not in found
    assert len(found) > 30


async def test_a_lookup_answering_nothing_for_nothing_picked_is_not_a_fault(bot):
    from black_bloc.api.auth import Refused

    async def names(ids: str = ""):
        return {}

    async def roster(form: str = ""):
        raise Refused(404, "no_such_form", "no form with that number")

    async def status():
        return {}

    run = selftest.Run(bot, bot.guilds[0])
    assert "nothing picked" in await selftest.read_check("/api/ref/names", names).run(run)
    assert "no_such_form" in await selftest.read_check("/api/applications/roster", roster).run(run)
    # A page read that takes NOTHING and answers nothing is still the fault it always was.
    with pytest.raises(selftest.CheckFailed):
        await selftest.read_check("/api/status", status).run(run)


# --- the run --------------------------------------------------------------------------------------


async def test_a_run_leaves_a_started_row_one_row_per_check_and_a_finished_row(bot, monkeypatch):
    async def yes(_one):
        return "fine"

    async def no(_one):
        raise selftest.CheckFailed("the thing is missing")

    monkeypatch.setattr(
        selftest,
        "checks_for",
        only(
            selftest.Check("config.one", "core", yes),
            selftest.Check("config.two", "core", no),
        ),
    )

    one = await selftest.run(bot, bot.guild)

    assert (one.ok, one.failed, one.posted) == (1, 1, 0)
    assert [row.name for row in one.failures] == ["config.two"]
    assert "the thing is missing" in one.failures[0].detail

    rows = await kinds_in(bot.db)
    assert [kind for kind, _ in rows] == [
        "selftest.started",
        "selftest.check",
        "selftest.check",
        "selftest.finished",
    ]
    assert rows[0][1]["checks"] == 2
    assert rows[1][1]["ok"] is True and rows[2][1]["ok"] is False
    assert rows[3][1] == {
        "run_id": one.run_id,
        "ok": 1,
        "failed": 1,
        "posted": 0,
        "via": "discord",
    }


async def test_the_run_row_carries_the_counts_and_the_door_that_asked_for_it(bot, monkeypatch):
    async def yes(_one):
        return "fine"

    monkeypatch.setattr(selftest, "checks_for", only(selftest.Check("config.one", "core", yes)))

    one = await selftest.run(bot, bot.guild, actor=SimpleNamespace(id=42), via=VIA_WEBSITE)
    rows = await selftest.recent_runs(bot.db, GUILD)

    assert len(rows) == 1
    assert rows[0]["id"] == one.run_id
    assert (rows[0]["ok"], rows[0]["failed"], rows[0]["posted"]) == (1, 0, 0)
    assert rows[0]["via"] == VIA_WEBSITE and rows[0]["actor_id"] == 42
    assert rows[0]["finished_at"] and rows[0]["purged_at"] is None
    # The website door's rows wear the `web.` head, so the Logs page can tell them apart.
    assert [kind for kind, _ in await kinds_in(bot.db)][0] == "web.selftest.started"


async def test_the_checks_come_back_out_of_the_log_not_a_table_of_their_own(bot, monkeypatch):
    async def yes(_one):
        return "fine"

    async def no(_one):
        raise RuntimeError("nope")

    monkeypatch.setattr(
        selftest,
        "checks_for",
        only(selftest.Check("config.one", "core", yes), selftest.Check("read.two", "selftest", no)),
    )

    one = await selftest.run(bot, bot.guild)
    found = await selftest.checks_of(bot.db, GUILD, one.run_id)

    assert [row["name"] for row in found] == ["config.one", "read.two"]
    assert [row["feature"] for row in found] == ["core", "selftest"]
    assert found[0]["ok"] is True and found[1]["ok"] is False
    assert found[1]["detail"] == "RuntimeError: nope"
    assert [row["name"] for row in await selftest.failures_of(bot.db, GUILD, one.run_id)] == [
        "read.two"
    ]


class BrokenRegistry:
    """`len()` answers, so the run opens; iterating is what falls over, the way a real one would."""

    def __len__(self):
        return 3

    def __iter__(self):
        raise RuntimeError("the check registry fell over")


async def test_a_runner_that_falls_over_closes_its_own_run_and_says_why(bot, monkeypatch):
    """Nothing awaits the website's task, so a runner that RAISES has to record itself."""
    monkeypatch.setattr(selftest, "checks_for", lambda _bot: BrokenRegistry())

    one = await selftest.run(bot, bot.guild)

    assert (one.ok, one.failed) == (0, 1)
    assert one.failures[0].name == selftest.RUNNER_CHECK
    assert "the check registry fell over" in one.failures[0].detail
    assert "stopped part way through" in one.failures[0].detail
    assert selftest.running(bot, GUILD) is None

    rows = await selftest.recent_runs(bot.db, GUILD)
    assert rows[0]["finished_at"] and (rows[0]["ok"], rows[0]["failed"]) == (0, 1)
    kinds = [kind for kind, _ in await kinds_in(bot.db)]
    assert kinds == ["selftest.started", "selftest.check", "selftest.finished"]
    found = await selftest.checks_of(bot.db, GUILD, one.run_id)
    assert [row["name"] for row in found] == [selftest.RUNNER_CHECK]
    assert found[0]["ok"] is False


async def test_the_website_door_starts_the_run_through_the_wrapper_that_records_a_crash():
    from black_bloc.api import selftest_api

    assert "finish_quietly" in inspect.getsource(selftest_api.build_router)


async def test_one_runs_check_rows_are_picked_out_in_sql_not_in_python(bot, monkeypatch):
    """The Python filter grew one run's worth of rows per run; the WHERE clause does not."""
    async def yes(_one):
        return "fine"

    monkeypatch.setattr(selftest, "checks_for", only(selftest.Check("config.one", "core", yes)))

    first = await selftest.run(bot, bot.guild)
    second = await selftest.run(bot, bot.guild)
    await bot.db.conn.execute(
        "INSERT INTO action_log(guild_id, at, kind, details) VALUES (?, ?, ?, ?)",
        (GUILD, datetime.now(UTC).isoformat(), "selftest.check", None),
    )
    await bot.db.conn.commit()

    assert len(await selftest.checks_of(bot.db, GUILD, first.run_id)) == 1
    assert len(await selftest.checks_of(bot.db, GUILD, second.run_id)) == 1
    assert await selftest.checks_of(bot.db, GUILD, 9999) == []
    assert "json_extract" in inspect.getsource(selftest.checks_of)


async def test_a_second_start_refuses_in_words_and_never_with_a_bare_status(bot, monkeypatch):
    started = []

    async def slow(one):
        started.append(one)
        with pytest.raises(selftest.SelfTestBusy) as raised:
            await selftest.run(one.bot, one.guild)
        started.append(str(raised.value))
        return "fine"

    monkeypatch.setattr(selftest, "checks_for", only(selftest.Check("config.one", "core", slow)))

    await selftest.run(bot, bot.guild)
    said = started[1]

    assert "already running" in said
    assert "of 1 checks done" in said
    assert "409" not in said and said.endswith(".")
    # The flag is cleared once it finishes, so the next start is not refused for ever.
    assert selftest.running(bot, GUILD) is None
    await selftest.run(bot, bot.guild)


async def test_every_posted_card_is_written_down_before_the_next_check_runs(bot, monkeypatch):
    async def posts(one):
        await one.post(content="a card")
        return "posted"

    monkeypatch.setattr(
        selftest,
        "checks_for",
        only(
            selftest.Check("panel.one", "core", posts),
            selftest.Check("panel.two", "core", posts),
        ),
    )

    one = await selftest.run(bot, bot.guild)
    waiting = await selftest.waiting_messages(bot.db, GUILD)

    assert one.posted == 2
    assert len(waiting) == 2
    assert {row["channel_id"] for row in waiting} == {TEST_CHANNEL}
    assert {row["run_id"] for row in waiting} == {one.run_id}
    assert len(bot.guild.get_channel(TEST_CHANNEL).messages) == 2


async def test_the_cards_go_to_the_self_test_channel_and_a_missing_one_is_said_in_words(
    bot, monkeypatch
):
    assert selftest.selftest_channel(bot, bot.guild).id == TEST_CHANNEL

    await bot.store.set(GUILD, "selftest_channel_id", OTHER_CHANNEL)
    assert selftest.selftest_channel(bot, bot.guild).id == OTHER_CHANNEL

    bot.guild.channels.pop(OTHER_CHANNEL)
    one = selftest.Run(bot=bot, guild=bot.guild)
    with pytest.raises(selftest.CheckFailed) as raised:
        await one.post(content="a card")

    assert "selftest_channel_id" in str(raised.value)
    assert "Settings page" in str(raised.value)


# --- the purge ------------------------------------------------------------------------------------


async def older(db, minutes):
    await db.conn.execute(
        "UPDATE selftest_messages SET posted_at = ?",
        ((datetime.now(UTC) - timedelta(minutes=minutes)).isoformat(),),
    )
    await db.conn.commit()


async def a_run_that_posted(bot, monkeypatch, count=2):
    async def posts(one):
        for _ in range(count):
            await one.post(content="a card")
        return "posted"

    monkeypatch.setattr(selftest, "checks_for", only(selftest.Check("panel.one", "core", posts)))
    return await selftest.run(bot, bot.guild)


async def test_nothing_is_deleted_before_its_minutes_are_up(bot, monkeypatch):
    await a_run_that_posted(bot, monkeypatch)

    assert await selftest.purge(bot, bot.guild) == 0
    assert len(await selftest.waiting_messages(bot.db, GUILD)) == 2
    assert bot.guild.get_channel(TEST_CHANNEL).bulk == []


async def test_the_purge_deletes_what_is_due_stamps_the_run_and_leaves_one_row(bot, monkeypatch):
    one = await a_run_that_posted(bot, monkeypatch)
    await older(bot.db, 6)

    gone = await selftest.purge(bot, bot.guild)

    assert gone == 2
    assert await selftest.waiting_messages(bot.db, GUILD) == []
    assert len(bot.guild.get_channel(TEST_CHANNEL).bulk) == 1
    assert (await selftest.one_run(bot.db, GUILD, one.run_id))["purged_at"]
    purged = [row for row in await kinds_in(bot.db) if row[0] == "selftest.purged"]
    assert len(purged) == 1
    assert purged[0][1]["messages"] == 2 and purged[0][1]["run_id"] == one.run_id


async def test_purge_now_takes_the_cards_down_without_waiting_for_the_minutes(bot, monkeypatch):
    one = await a_run_that_posted(bot, monkeypatch)

    gone = await selftest.purge(bot, bot.guild, due_only=False)

    assert gone == 2
    assert (await selftest.one_run(bot.db, GUILD, one.run_id))["purged_at"]


async def test_a_message_discord_will_not_bulk_delete_goes_one_at_a_time_and_a_404_counts(
    bot, monkeypatch
):
    """Past fourteen days Discord refuses the bulk call; a message somebody already deleted
    is gone, which is the outcome the purge wanted."""
    await a_run_that_posted(bot, monkeypatch, count=2)
    channel = bot.guild.get_channel(TEST_CHANNEL)
    channel.refuse_bulk = True
    channel.gone = {channel.messages[0].id}
    await older(bot.db, 60)

    gone = await selftest.purge(bot, bot.guild)

    assert gone == 2
    assert channel.one_by_one == [channel.messages[1].id]
    assert await selftest.waiting_messages(bot.db, GUILD) == []


async def test_a_channel_the_bot_can_no_longer_see_still_clears_its_rows(bot, monkeypatch):
    """Otherwise the table grows for ever on a channel nobody can delete from."""
    one = await a_run_that_posted(bot, monkeypatch)
    bot.guild.channels.pop(TEST_CHANNEL)
    await older(bot.db, 6)

    gone = await selftest.purge(bot, bot.guild)

    assert gone == 2
    assert await selftest.waiting_messages(bot.db, GUILD) == []
    assert (await selftest.one_run(bot.db, GUILD, one.run_id))["purged_at"]


# --- the boot door --------------------------------------------------------------------------------


def test_the_boot_line_is_the_one_a_deploy_is_read_by(bot):
    one = selftest.Run(bot=bot, guild=bot.guild, posted=3)
    one.results = [
        selftest.Result("config.one", "core", True, "fine", "now"),
        selftest.Result("read./api/status", "selftest", False, "TypeError: no", "now"),
    ]

    lines = selftest.boot_lines(bot, one)

    assert lines[0] == "selftest: 1 ok, 1 failed, 3 messages posted (purge in 5 min)"
    assert lines[1] == "selftest: FAILED read./api/status — TypeError: no"
    assert len(lines) == 2


async def test_the_boot_run_purges_the_leftovers_even_when_it_is_switched_off(bot, monkeypatch):
    one = await a_run_that_posted(bot, monkeypatch)
    await older(bot.db, 6)
    await bot.store.set(GUILD, "selftest_on_boot", False)
    monkeypatch.setattr(selftest, "checks_for", only())

    await selftest.on_boot(bot)

    assert await selftest.waiting_messages(bot.db, GUILD) == []
    assert len(await selftest.recent_runs(bot.db, GUILD)) == 1
    assert (await selftest.recent_runs(bot.db, GUILD))[0]["id"] == one.run_id


async def test_the_boot_run_records_itself_as_the_bot_at_boot(bot, monkeypatch):
    async def yes(_one):
        return "fine"

    monkeypatch.setattr(selftest, "checks_for", only(selftest.Check("config.one", "core", yes)))

    await selftest.on_boot(bot)
    rows = await kinds_in(bot.db)

    assert [kind for kind, _ in rows][0] == "selftest.started"
    assert all(details["via"] == VIA_BOOT for _, details in rows)
    assert (await selftest.recent_runs(bot.db, GUILD))[0]["via"] == VIA_BOOT


async def test_a_boot_run_that_throws_does_not_stop_the_bot_from_starting(bot, monkeypatch):
    def explode(_bot):
        raise RuntimeError("the registry is broken")

    monkeypatch.setattr(selftest, "checks_for", explode)

    await selftest.on_boot(bot)

    assert await selftest.recent_runs(bot.db, GUILD) == []
