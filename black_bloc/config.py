"""Settings, loaded from the environment and an optional `.env` file.

One place owns configuration. Nothing else in the package reads `os.environ`.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ConfigError(RuntimeError):
    """Raised when required configuration is missing or invalid."""


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

    # Owner rule 2026-08-26: until we are ready, the bot only speaks in ONE
    # channel (and DMs). Enforced by black_bloc/guard.py, not just documented.
    test_mode: bool = True
    test_channel_id: int | None = None

    @field_validator("dev_guild_id", "test_channel_id", mode="before")
    @classmethod
    def _blank_is_none(cls, v):
        # `.env.example` ships `DEV_GUILD_ID=`; a blank line must mean "unset",
        # not "the empty string is not an integer".
        if isinstance(v, str) and not v.strip():
            return None
        return v

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
    """Build Settings. Keyword overrides win over the environment (handy in tests).

    Raises ConfigError (not a pydantic traceback) when a value cannot be parsed.
    """
    try:
        return Settings(**overrides)
    except ValidationError as exc:
        problems = "; ".join(
            f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors()
        )
        raise ConfigError(f"invalid configuration — {problems} (check .env)") from exc
