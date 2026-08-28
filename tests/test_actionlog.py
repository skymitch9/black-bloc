import json
import logging

import pytest

from black_bloc.actionlog import (
    NOTHING_IMPORTANT,
    NOTHING_YET,
    build_embed,
    describe,
    entity_id,
    feature_clause,
    level_for,
    log_action,
    recent_lines,
    stamp,
)
from black_bloc.config import load_settings
from black_bloc.logkinds import FEATURES
from black_bloc.settings_store import SettingsStore
from black_bloc.storage.db import Database

TEST_CH = 111


class _Guild:
    def __init__(self, id=7, channel=None):
        self.id = id
        self._channel = channel

    def get_channel(self, channel_id):
        return self._channel


class _Channel:
    def __init__(self, id=TEST_CH, raises=None):
        self.id = id
        self.raises = raises
        self.sent = []

    async def send(self, **kwargs):
        if self.raises is not None:
            raise self.raises
        self.sent.append(kwargs)


class _Bot:
    def __init__(self, db, store, channel=None):
        self.db = db
        self.store = store
        self._channel = channel

    def get_channel(self, channel_id):
        return self._channel


@pytest.fixture
async def wired(tmp_path, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    settings = load_settings(_env_file=None, test_mode=True, test_channel_id=TEST_CH)
    db = Database(tmp_path / "a.sqlite3")
    await db.connect()
    store = SettingsStore(db, settings)
    await store.load()
    try:
        yield db, store
    finally:
        await db.close()


async def _rows(db):
    cur = await db.conn.execute("SELECT * FROM action_log ORDER BY id")
    return await cur.fetchall()


async def test_row_written_and_embed_posted(wired):
    db, store = wired
    await store.set(7, "rolemenu_log_level", "all")
    channel = _Channel()
    bot = _Bot(db, store, channel)
    row_id = await log_action(
        bot,
        _Guild(),
        "role_menu.update",
        actor=42,
        target=43,
        reason="clicked a menu",
        details={"added": [1]},
    )
    rows = await _rows(db)
    assert row_id == rows[0]["id"]
    assert rows[0]["kind"] == "role_menu.update"
    assert rows[0]["guild_id"] == 7
    assert rows[0]["actor_id"] == 42 and rows[0]["target_id"] == 43
    assert rows[0]["reason"] == "clicked a menu"
    assert json.loads(rows[0]["details"]) == {"added": [1]}
    assert channel.sent[0]["embed"].title == "role_menu.update"


async def test_discord_failure_is_swallowed_and_warned(wired, caplog):
    db, store = wired
    await store.set(7, "core_log_level", "all")
    bot = _Bot(db, store, _Channel(raises=RuntimeError("403 Forbidden")))
    with caplog.at_level(logging.WARNING, logger="black_bloc.actionlog"):
        await log_action(bot, _Guild(), "settings.set", actor=1)
    assert len(await _rows(db)) == 1
    assert "settings.set not posted" in caplog.text


async def test_missing_log_channel_is_warned_not_raised(wired, caplog):
    db, store = wired
    await store.set(7, "log_channel_id", 999)
    await store.set(7, "core_log_level", "all")
    bot = _Bot(db, store, None)
    with caplog.at_level(logging.WARNING, logger="black_bloc.actionlog"):
        await log_action(bot, _Guild(), "settings.set")
    assert len(await _rows(db)) == 1
    assert "is not visible" in caplog.text


async def test_the_default_level_writes_the_row_and_keeps_discord_quiet(wired):
    db, store = wired
    channel = _Channel()
    bot = _Bot(db, store, channel)

    await log_action(bot, _Guild(), "poll.created", actor=1)

    assert len(await _rows(db)) == 1
    assert channel.sent == []


async def test_the_default_level_still_posts_what_acted_on_a_member(wired):
    db, store = wired
    channel = _Channel()
    bot = _Bot(db, store, channel)

    await log_action(bot, _Guild(), "mod.banned", actor=1, target=2)

    assert [sent["embed"].title for sent in channel.sent] == ["mod.banned"]


async def test_off_writes_the_row_and_posts_nothing_at_all(wired):
    db, store = wired
    await store.set(7, "mod_log_level", "off")
    channel = _Channel()
    bot = _Bot(db, store, channel)

    await log_action(bot, _Guild(), "mod.banned", actor=1, target=2)

    assert len(await _rows(db)) == 1
    assert channel.sent == []


async def test_notify_forces_the_line_through_any_level(wired):
    db, store = wired
    await store.set(7, "poll_log_level", "off")
    channel = _Channel()
    bot = _Bot(db, store, channel)

    await log_action(bot, _Guild(), "poll.created", actor=1, notify=True)

    assert [sent["embed"].title for sent in channel.sent] == ["poll.created"]


async def test_each_feature_is_gated_on_its_own_key(wired):
    db, store = wired
    await store.set(7, "poll_log_level", "all")
    channel = _Channel()
    bot = _Bot(db, store, channel)

    await log_action(bot, _Guild(), "poll.created")
    await log_action(bot, _Guild(), "golive.announce")

    assert [sent["embed"].title for sent in channel.sent] == ["poll.created"]


async def test_a_bot_with_no_store_behaves_the_way_it_always_did(wired):
    db, _ = wired
    bot = _Bot(db, None, _Channel())

    assert level_for(bot, _Guild(), "poll.created") == "all"
    assert level_for(bot, object(), "poll.created") == "all"


async def test_a_store_that_raises_is_a_warning_and_todays_behaviour(wired, caplog):
    db, _ = wired

    class _Angry:
        def get(self, guild_id, key):
            raise RuntimeError("no cache yet")

    bot = _Bot(db, _Angry(), _Channel())
    with caplog.at_level(logging.WARNING, logger="black_bloc.actionlog"):
        assert level_for(bot, _Guild(), "poll.created") == "all"
    assert "level unreadable" in caplog.text


def test_embed_fields_are_only_what_was_given():
    embed = build_embed("x.y")
    assert embed.fields == []
    embed = build_embed("x.y", actor=5, target=6, reason="because", details={"a": 1})
    assert [f.name for f in embed.fields] == ["Actor", "Target", "Reason", "Details"]
    assert embed.fields[0].value == "<@5>"
    assert '"a": 1' in embed.fields[3].value


def test_entity_helpers_accept_ids_and_objects():
    class _Thing:
        id = 9
        mention = "<@9>"

    assert entity_id(None) is None and entity_id(5) == 5 and entity_id(_Thing()) == 9
    assert describe(None) is None and describe(5) == "<@5>" and describe(_Thing()) == "<@9>"


async def _seed(db, store, kinds):
    bot = _Bot(db, store, _Channel())
    for kind in kinds:
        await log_action(bot, _Guild(), kind, actor=42, target=43, reason=f"because {kind}")


async def test_recent_lines_reads_one_feature_newest_first(wired):
    db, store = wired
    await _seed(db, store, ["poll.created", "golive.announce", "poll.closed"])

    lines = await recent_lines(db, 7, "poll", 10)

    assert len(lines) == 2
    assert "`poll.closed`" in lines[0] and "`poll.created`" in lines[1]
    assert all("golive" not in line for line in lines)


async def test_recent_lines_counts_web_and_alias_kinds_as_the_same_feature(wired):
    db, store = wired
    await _seed(db, store, ["role.granted", "role_menu.update", "web.role.extended"])

    lines = await recent_lines(db, 7, "rolemenu", 10)

    assert len(lines) == 3


async def test_core_is_everything_no_other_feature_claims(wired):
    db, store = wired
    await _seed(db, store, ["settings.set", "presence.bio_set", "nonsense.happened", "poll.closed"])

    lines = await recent_lines(db, 7, "core", 10)

    assert len(lines) == 3
    assert all("poll.closed" not in line for line in lines)


async def test_important_only_drops_the_routine_ones(wired):
    db, store = wired
    await _seed(db, store, ["mod.warned", "mod.would_ban", "mod.banned"])

    assert len(await recent_lines(db, 7, "mod", 10)) == 3
    lines = await recent_lines(db, 7, "mod", 10, important_only=True)
    assert len(lines) == 2
    assert all("would_ban" not in line for line in lines)


async def test_the_limit_is_honoured_after_the_important_filter(wired):
    db, store = wired
    await _seed(db, store, ["mod.would_ban"] * 5 + ["mod.banned"] * 3)

    assert len(await recent_lines(db, 7, "mod", 2, important_only=True)) == 2


async def test_an_empty_feature_says_so_rather_than_showing_nothing(wired):
    db, store = wired

    assert await recent_lines(db, 7, "chat", 10) == [NOTHING_YET]
    assert await recent_lines(db, 7, "chat", 10, important_only=True) == [NOTHING_IMPORTANT]


async def test_a_line_carries_a_relative_stamp_and_stays_under_the_limit(wired):
    db, store = wired
    bot = _Bot(db, store, _Channel())
    await log_action(bot, _Guild(), "mod.banned", actor=42, target=43, reason="x" * 400)

    line = (await recent_lines(db, 7, "mod", 1))[0]

    stamp, _, body = line.partition(" · ")
    assert stamp.startswith("<t:") and stamp.endswith(":R>")
    assert len(body) <= 100
    assert body.startswith("`mod.banned` · <@42> → <@43>")
    assert body.endswith("…")


async def test_details_stand_in_when_there_is_no_reason(wired):
    db, store = wired
    bot = _Bot(db, store, _Channel())
    await log_action(bot, _Guild(), "poll.created", details={"poll_id": 3, "hours": 24})

    line = (await recent_lines(db, 7, "poll", 1))[0]

    assert "poll_id=3, hours=24" in line
    assert "→" not in line


def test_every_feature_has_a_clause_and_core_asks_it_backwards():
    for feature in FEATURES:
        clause, params = feature_clause(feature)
        assert clause.count("?") == len(params)
    assert feature_clause("core")[0].startswith("NOT (")
    assert feature_clause("poll") == ("(kind LIKE ? OR kind LIKE ?)", ("poll.%", "web.poll.%"))


def test_an_unparseable_timestamp_is_shown_as_it_was_stored():
    assert stamp("not a date") == "not a date"
    assert stamp("2026-08-27T00:00:00+00:00").startswith("<t:")
