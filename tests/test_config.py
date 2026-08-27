import pytest

from black_bloc.config import ConfigError, load_settings


def test_defaults_without_env(monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    s = load_settings(_env_file=None)
    assert s.discord_token == ""
    assert s.api_enabled is False
    assert s.api_host == "127.0.0.1"


def test_require_token_rejects_missing(settings):
    with pytest.raises(ConfigError, match="DISCORD_TOKEN"):
        settings.require_token()


def test_env_is_read(monkeypatch):
    monkeypatch.setenv("DISCORD_TOKEN", "abc")
    monkeypatch.setenv("DEV_GUILD_ID", "123")
    s = load_settings(_env_file=None)
    assert s.require_token() == "abc"
    assert s.dev_guild_id == 123


def test_blank_dev_guild_id_means_unset(monkeypatch):
    monkeypatch.setenv("DEV_GUILD_ID", "")
    assert load_settings(_env_file=None).dev_guild_id is None


def test_garbage_dev_guild_id_is_a_config_error(monkeypatch):
    monkeypatch.setenv("DEV_GUILD_ID", "not-a-number")
    with pytest.raises(ConfigError, match="dev_guild_id"):
        load_settings(_env_file=None)


def test_blank_twitch_credentials_mean_unconfigured(monkeypatch):
    monkeypatch.setenv("TWITCH_CLIENT_ID", "")
    monkeypatch.setenv("TWITCH_CLIENT_SECRET", "")
    s = load_settings(_env_file=None)
    assert s.twitch_client_id is None and s.twitch_client_secret is None
    assert s.twitch_configured is False


def test_twitch_is_configured_only_with_both_halves(monkeypatch):
    monkeypatch.setenv("TWITCH_CLIENT_ID", "abc")
    monkeypatch.delenv("TWITCH_CLIENT_SECRET", raising=False)
    assert load_settings(_env_file=None).twitch_configured is False
    monkeypatch.setenv("TWITCH_CLIENT_SECRET", "shh")
    assert load_settings(_env_file=None).twitch_configured is True
