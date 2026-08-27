from __future__ import annotations

from pathlib import Path

from pydantic import Field, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ConfigError(RuntimeError):
    """Required configuration is missing or invalid."""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    discord_token: str = Field(
        default="", description="Bot token from the Discord Developer Portal"
    )
    dev_guild_id: int | None = Field(
        default=None, description="Guild to sync slash commands to instantly during development"
    )
    command_prefix: str = "!"
    log_level: str = "INFO"
    database_path: Path = Path("data/black_bloc.sqlite3")

    api_enabled: bool = False
    api_host: str = "127.0.0.1"
    api_port: int = 8080
    site_root: Path = Path("site/public")

    twitch_client_id: str | None = Field(
        default=None, description="Twitch application client id (go-live fallback path)"
    )
    twitch_client_secret: str | None = Field(
        default=None, description="Twitch application client secret"
    )

    test_mode: bool = True
    test_channel_id: int | None = None

    site_origin: str = "https://blackbloc.heygabi.ai"
    session_cookie_samesite: str = "lax"
    discord_client_id: str | None = None
    discord_client_secret: str | None = None
    session_secret: str | None = None

    @field_validator(
        "dev_guild_id", "test_channel_id", "twitch_client_id", "twitch_client_secret",
        "discord_client_id", "discord_client_secret", "session_secret",
        mode="before",
    )
    @classmethod
    def _blank_is_none(cls, v):
        if isinstance(v, str) and not v.strip():
            return None
        return v

    @property
    def twitch_configured(self) -> bool:
        return bool(self.twitch_client_id and self.twitch_client_secret)

    @property
    def site_login_configured(self) -> bool:
        return bool(self.discord_client_id and self.discord_client_secret and self.session_secret)

    @property
    def origin(self) -> str:
        return self.site_origin.rstrip("/")

    @property
    def oauth_redirect_uri(self) -> str:
        return f"{self.origin}/api/auth/callback"

    def validate_test_mode(self) -> None:
        if self.test_mode and not self.test_channel_id:
            raise ConfigError(
                "TEST_MODE is on but TEST_CHANNEL_ID is not set. Set it in .env, or set "
                "TEST_MODE=false — only when the owner has said the bot may leave the "
                "test channel (docs/access/setup.md, Test policy)."
            )

    def require_token(self) -> str:
        if not self.discord_token.strip():
            raise ConfigError(
                "DISCORD_TOKEN is not set. Copy .env.example to .env and fill it in "
                "(see docs/access/setup.md)."
            )
        return self.discord_token.strip()


def load_settings(**overrides) -> Settings:
    """Build Settings; keyword overrides win over the environment."""
    try:
        return Settings(**overrides)
    except ValidationError as exc:
        problems = "; ".join(
            f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors()
        )
        raise ConfigError(f"invalid configuration — {problems} (check .env)") from exc
