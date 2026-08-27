import pytest

from black_bloc.bot import BlackBlocBot
from black_bloc.config import ConfigError, load_settings
from black_bloc.guard import TestModeViolation

TEST_CH = 111
OTHER_CH = 222
CATEGORY = 50


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


async def test_edit_outside_test_channel_is_refused(guarded_bot):
    with pytest.raises(TestModeViolation):
        guarded_bot.http.edit_message(OTHER_CH, 1, params=None)
    await guarded_bot.close()


async def test_edit_in_test_channel_passes_through(guarded_bot, monkeypatch):
    seen = []
    monkeypatch.setattr(
        guarded_bot.guard, "_original_edit", lambda cid, *a, **k: seen.append(cid)
    )
    guarded_bot.http.edit_message(TEST_CH, 1, params=None)
    assert seen == [TEST_CH]
    await guarded_bot.close()


class _Interaction:
    def __init__(self, guild_id, channel_id):
        self.guild_id = guild_id
        self.channel_id = channel_id


async def test_interaction_policy(guarded_bot):
    g = guarded_bot.guard
    assert g.allows_interaction(_Interaction(guild_id=1, channel_id=TEST_CH))
    assert g.allows_interaction(_Interaction(guild_id=None, channel_id=OTHER_CH))
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


class _Category:
    def __init__(self, category_id):
        self.id = category_id


class _Channel:
    def __init__(self, channel_id, category_id=None):
        self.id = channel_id
        self.category_id = category_id
        self.category = _Category(category_id) if category_id else None


def _cache(bot, *channels):
    known = {c.id: c for c in channels}
    bot.get_channel = lambda channel_id: known.get(channel_id)


async def test_deleting_a_channel_outside_the_test_category_is_refused(guarded_bot):
    _cache(guarded_bot, _Channel(TEST_CH, category_id=CATEGORY), _Channel(OTHER_CH, category_id=99))

    with pytest.raises(TestModeViolation):
        guarded_bot.http.delete_channel(OTHER_CH)
    await guarded_bot.close()


async def test_deleting_a_channel_in_the_test_category_passes_through(guarded_bot, monkeypatch):
    seen = []
    sibling = _Channel(333, category_id=CATEGORY)
    _cache(guarded_bot, _Channel(TEST_CH, category_id=CATEGORY), sibling)
    monkeypatch.setattr(
        guarded_bot.guard, "_original_delete", lambda cid, *a, **k: seen.append(cid)
    )

    guarded_bot.http.delete_channel(sibling.id)

    assert seen == [sibling.id]
    await guarded_bot.close()


async def test_deleting_a_channel_black_bloc_cannot_see_is_refused(guarded_bot):
    _cache(guarded_bot, _Channel(TEST_CH, category_id=CATEGORY))

    with pytest.raises(TestModeViolation):
        guarded_bot.http.delete_channel(4242)
    await guarded_bot.close()


async def test_a_test_channel_with_no_category_allows_no_place_at_all(guarded_bot):
    _cache(guarded_bot, _Channel(TEST_CH), _Channel(OTHER_CH, category_id=CATEGORY))
    g = guarded_bot.guard

    assert g.test_category_id() is None
    assert g.allows_place(_Channel(OTHER_CH, category_id=CATEGORY)) is False
    assert g.allows_place(_Channel(TEST_CH)) is True
    await guarded_bot.close()


async def test_the_channel_gate_takes_a_channel_object_as_well_as_an_id(guarded_bot):
    _cache(guarded_bot, _Channel(TEST_CH, category_id=CATEGORY))
    g = guarded_bot.guard

    assert g.allows_channel(_Channel(TEST_CH, category_id=CATEGORY)) is True
    assert g.allows_channel(_Channel(OTHER_CH)) is False
    assert g.allows_channel(None) is False
    await guarded_bot.close()
