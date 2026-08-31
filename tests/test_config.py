import pytest

from black_bloc.config import SESSION_SECRET_MIN, ConfigError, load_settings


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


def test_a_samesite_of_none_is_refused_with_a_sentence(monkeypatch):
    monkeypatch.setenv("SESSION_COOKIE_SAMESITE", "none")
    with pytest.raises(ConfigError, match="lax") as raised:
        load_settings(_env_file=None)
    assert "another site" in str(raised.value)


def test_samesite_is_taken_in_any_case_and_only_the_two_choices(monkeypatch):
    monkeypatch.setenv("SESSION_COOKIE_SAMESITE", "STRICT")
    assert load_settings(_env_file=None).session_cookie_samesite == "strict"
    monkeypatch.setenv("SESSION_COOKIE_SAMESITE", "sideways")
    with pytest.raises(ConfigError):
        load_settings(_env_file=None)


def test_the_poll_vote_key_is_off_until_it_is_set_and_blank_counts_as_unset(monkeypatch):
    monkeypatch.delenv("POLL_VOTE_SECRET", raising=False)
    assert load_settings(_env_file=None).poll_vote_secret is None
    assert load_settings(_env_file=None).poll_votes_keyed is False

    monkeypatch.setenv("POLL_VOTE_SECRET", "   ")
    assert load_settings(_env_file=None).poll_votes_keyed is False

    monkeypatch.setenv("POLL_VOTE_SECRET", "a-key-nobody-else-has")
    keyed = load_settings(_env_file=None)
    assert keyed.poll_vote_secret == "a-key-nobody-else-has"
    assert keyed.poll_votes_keyed is True


def test_a_short_session_secret_disables_sign_in_and_warns(monkeypatch, caplog):
    for name in ("DISCORD_CLIENT_ID", "DISCORD_CLIENT_SECRET"):
        monkeypatch.setenv(name, "set")
    monkeypatch.setenv("SESSION_SECRET", "x" * (SESSION_SECRET_MIN - 1))
    with caplog.at_level("WARNING"):
        short = load_settings(_env_file=None)
    assert short.site_login_configured is False
    assert "SESSION_SECRET" in caplog.text

    monkeypatch.setenv("SESSION_SECRET", "x" * SESSION_SECRET_MIN)
    assert load_settings(_env_file=None).site_login_configured is True
