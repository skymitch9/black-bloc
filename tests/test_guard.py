"""The test-mode gate must refuse anything outside the test channel or a DM."""

import pytest

from black_bloc.bot import BlackBlocBot
from black_bloc.config import ConfigError, load_settings
from black_bloc.guard import TestModeViolation

TEST_CH = 111
OTHER_CH = 222


@pytest.fixture
def guarded_bot(tmp_path, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    s = load_settings(
        _env_file=None,
        database_path=tmp_path / "t.sqlite3",
        test_mode=True,
        test_channel_id=TEST_CH,
    )
    return BlackBlocBot(s)


async def test_send_outside_test_channel_is_refused(guarded_bot):
    with pytest.raises(TestModeViolation):
        guarded_bot.http.send_message(OTHER_CH, params=None)
    await guarded_bot.close()


async def test_send_to_test_channel_passes_through(guarded_bot, monkeypatch):
    seen = []
    monkeypatch.setattr(guarded_bot.guard, "_original_send", lambda cid, *a, **k: seen.append(cid))
    guarded_bot.http.send_message(TEST_CH, params=None)
    assert seen == [TEST_CH]
    await guarded_bot.close()


class _Interaction:
    def __init__(self, guild_id, channel_id):
        self.guild_id = guild_id
        self.channel_id = channel_id


async def test_interaction_policy(guarded_bot):
    g = guarded_bot.guard
    assert g.allows_interaction(_Interaction(guild_id=1, channel_id=TEST_CH))
    assert g.allows_interaction(_Interaction(guild_id=None, channel_id=OTHER_CH))  # DM
    assert not g.allows_interaction(_Interaction(guild_id=1, channel_id=OTHER_CH))
    await guarded_bot.close()


def test_test_mode_without_channel_is_a_config_error(monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    s = load_settings(_env_file=None, test_mode=True, test_channel_id=None)
    with pytest.raises(ConfigError, match="TEST_CHANNEL_ID"):
        s.validate_test_mode()


def test_test_mode_off_installs_no_guard(tmp_path, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    s = load_settings(_env_file=None, database_path=tmp_path / "t.sqlite3", test_mode=False)
    assert BlackBlocBot(s).guard is None
