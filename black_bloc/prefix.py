from __future__ import annotations

from typing import Any


def no_prefix_commands(bot: Any, message: Any) -> list[str]:
    """Black Bloc is slash-only, so no message is ever a prefix-command attempt."""
    return []
