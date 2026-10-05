import pytest

from black_bloc import settings_store, tone_keys
from black_bloc.chat_voice import Settle, order_of, settle_of
from black_bloc.config import load_settings
from black_bloc.personas import DRIFT_CHANCE, TROPE_NAMES
from black_bloc.settings_store import SettingError, SettingsStore, coerce_value, parse_value
from black_bloc.storage.db import Database

GUILD = 7


@pytest.fixture
async def store(tmp_path, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    db = Database(tmp_path / "t.sqlite3")
    await db.connect()
    found = SettingsStore(db, load_settings(_env_file=None, test_mode=True))
    await found.load()
    try:
        yield found
    finally:
        await db.close()


def test_every_tone_key_is_a_chat_setting_with_help_and_a_shipped_default(store):
    for key, (kind, default, said) in tone_keys.TONE_SETTINGS.items():
        assert settings_store.KEY_TYPES[key] == kind
        assert settings_store.namespace_of(key) == "chat"
        assert settings_store.KEY_HELP[key] == said and len(said.split()) >= 10
        assert store.default(key) == default == store.get(GUILD, key)
    for key, (default, fields, said) in tone_keys.TONE_WORDS.items():
        assert settings_store.KEY_TYPES[key] == "text"
        assert settings_store.namespace_of(key) == "chat"
        assert store.default(key) == default and settings_store.KEY_HELP[key] == said
        assert default.format(**{name: "x" for name in fields})


def test_the_shipped_numbers_are_the_manifests_chance_four_conversations_and_two_percent(store):
    assert tone_keys.DRIFT_START_PERCENT == round(DRIFT_CHANCE * 100) == 25
    assert settle_of(store, GUILD) == Settle(start=0.25, halves=4, floor=0.02)
    assert store.get(GUILD, tone_keys.FEEDBACK_MODE_KEY) == "on"


async def test_the_three_numbers_are_set_from_either_door_and_bounded(store):
    for key, top in (
        (tone_keys.DRIFT_START_KEY, 100),
        (tone_keys.DRIFT_HALVES_KEY, 1000),
        (tone_keys.DRIFT_FLOOR_KEY, 100),
    ):
        assert coerce_value(key, parse_value(key, "0")) == 0
        assert coerce_value(key, top) == top
        with pytest.raises(SettingError):
            coerce_value(key, top + 1)
        with pytest.raises(SettingError):
            coerce_value(key, -1)
    await store.set(GUILD, tone_keys.DRIFT_START_KEY, 40)
    await store.set(GUILD, tone_keys.DRIFT_HALVES_KEY, 2)
    await store.set(GUILD, tone_keys.DRIFT_FLOOR_KEY, 0)
    assert settle_of(store, GUILD) == Settle(start=0.4, halves=2, floor=0.0)


async def test_an_order_takes_known_tones_only_and_is_stored_tidy(store):
    await store.set(GUILD, tone_keys.GENTLE_ORDER_KEY, " Warm ,COZY,, shy ")
    assert store.get(GUILD, tone_keys.GENTLE_ORDER_KEY) == "warm, cozy, shy"
    with pytest.raises(SettingError) as refused:
        await store.set(GUILD, tone_keys.CAREFUL_ORDER_KEY, "scholar, grumpy")
    assert "**grumpy** is not one of the tones" in str(refused.value)
    await store.set(GUILD, tone_keys.CAREFUL_ORDER_KEY, "")
    assert order_of(store.get(GUILD, tone_keys.CAREFUL_ORDER_KEY)) == ()


async def test_the_cues_may_be_blank_and_the_mode_is_on_or_off(store):
    await store.set(GUILD, tone_keys.FEEDBACK_CUES_KEY, "")
    assert store.get(GUILD, tone_keys.FEEDBACK_CUES_KEY) == ""
    await store.set(GUILD, tone_keys.FEEDBACK_MODE_KEY, "off")
    with pytest.raises(SettingError):
        await store.set(GUILD, tone_keys.FEEDBACK_MODE_KEY, "shadow")


def test_the_shipped_orders_are_the_eleven_tones_gentle_first_and_careful_first():
    gentle = order_of(tone_keys.GENTLE_ORDER)
    careful = order_of(tone_keys.CAREFUL_ORDER)
    assert sorted(gentle) == sorted(careful) == sorted(TROPE_NAMES)
    assert (gentle[0], gentle[-1]) == ("warm", "tsundere")
    assert (careful[0], careful[-1]) == ("scholar", "dramatic")
    assert sorted(tone_keys.KNOWN_TONES) == sorted(TROPE_NAMES)


async def test_a_word_refuses_a_slot_it_does_not_have(store):
    with pytest.raises(SettingError):
        await store.set(GUILD, tone_keys.REROLLED_KEY, "Rolled {nothing}")
    await store.set(GUILD, tone_keys.REROLLED_KEY, "{member}: {tone}")
    assert store.get(GUILD, tone_keys.REROLLED_KEY) == "{member}: {tone}"
