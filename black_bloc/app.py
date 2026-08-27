from __future__ import annotations

from .bot import BlackBlocBot
from .config import ConfigError, load_settings
from .errors import config_error_exit, run
from .logging_setup import configure_logging


def main() -> int:
    try:
        settings = load_settings()
        configure_logging(settings.log_level)
        settings.validate_test_mode()
        token = settings.require_token()
    except ConfigError as exc:
        return config_error_exit(exc)
    return run(BlackBlocBot(settings), token)
