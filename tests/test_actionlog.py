import json
import logging

import pytest

from black_bloc.actionlog import build_embed, describe, entity_id, log_action
from black_bloc.config import load_settings
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
    bot = _Bot(db, store, _Channel(raises=RuntimeError("403 Forbidden")))
    with caplog.at_level(logging.WARNING, logger="black_bloc.actionlog"):
        await log_action(bot, _Guild(), "settings.set", actor=1)
    assert len(await _rows(db)) == 1
    assert "settings.set not posted" in caplog.text


async def test_missing_log_channel_is_warned_not_raised(wired, caplog):
    db, store = wired
    await store.set(7, "log_channel_id", 999)
    bot = _Bot(db, store, None)
    with caplog.at_level(logging.WARNING, logger="black_bloc.actionlog"):
        await log_action(bot, _Guild(), "settings.set")
    assert len(await _rows(db)) == 1
    assert "is not visible" in caplog.text


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
