from __future__ import annotations

import re
from typing import Any

SKIN_TONES: dict[str, str] = {
    "none": "",
    "light": "\U0001f3fb",
    "medium-light": "\U0001f3fc",
    "medium": "\U0001f3fd",
    "medium-dark": "\U0001f3fe",
    "dark": "\U0001f3ff",
}
SKIN_TONE_NAMES: tuple[str, ...] = tuple(SKIN_TONES)
SKIN_TONE_DEFAULT = "dark"
MODIFIERS = frozenset(value for value in SKIN_TONES.values() if value)
VARIATION = "️"

MODIFIER_BASE = (
    "261D 26F9 270A 270B 270C 270D "
    "1F385 1F3C2 1F3C3 1F3C4 1F3C7 1F3CA 1F3CB 1F3CC "
    "1F442 1F443 1F446 1F447 1F448 1F449 1F44A 1F44B 1F44C 1F44D 1F44E 1F44F 1F450 "
    "1F466 1F467 1F468 1F469 1F46B 1F46C 1F46D 1F46E 1F470 1F471 1F472 1F473 1F474 "
    "1F475 1F476 1F477 1F478 1F47C 1F481 1F482 1F483 1F485 1F486 1F487 1F48F 1F491 "
    "1F4AA 1F574 1F575 1F57A 1F590 1F595 1F596 "
    "1F645 1F646 1F647 1F64B 1F64C 1F64D 1F64E 1F64F "
    "1F6A3 1F6B4 1F6B5 1F6B6 1F6C0 1F6CC "
    "1F90C 1F90F 1F918 1F919 1F91A 1F91B 1F91C 1F91D 1F91E 1F91F "
    "1F926 1F930 1F931 1F932 1F933 1F934 1F935 1F936 1F937 1F938 1F939 1F93D 1F93E "
    "1F977 1F9B5 1F9B6 1F9B8 1F9B9 1F9BB 1F9CD 1F9CE 1F9CF "
    "1F9D1 1F9D2 1F9D3 1F9D4 1F9D5 1F9D6 1F9D7 1F9D8 1F9D9 1F9DA 1F9DB 1F9DC 1F9DD "
    "1FAC3 1FAC4 1FAC5 1FAF0 1FAF1 1FAF2 1FAF3 1FAF4 1FAF5 1FAF6 1FAF7 1FAF8"
)
TONEABLE: frozenset[str] = frozenset(chr(int(code, 16)) for code in MODIFIER_BASE.split())

_TONEABLE_RE = re.compile(
    "([" + "".join(sorted(TONEABLE)) + "])(️?)([\U0001f3fb-\U0001f3ff]?)"
)


def toned(emoji: str, tone: str = SKIN_TONE_DEFAULT) -> str:
    """One emoji wearing a skin tone, if that emoji is one Unicode lets wear one."""
    if not emoji or emoji[0] not in TONEABLE:
        return emoji
    modifier = SKIN_TONES.get(tone, "")
    tail = "".join(ch for ch in emoji[1:] if ch not in MODIFIERS)
    if not modifier:
        return emoji[0] + tail
    return emoji[0] + modifier + tail.replace(VARIATION, "")


def toned_text(text: str, tone: str = SKIN_TONE_DEFAULT) -> str:
    """Every skin-tone-capable emoji in a line, wearing the same tone."""
    modifier = SKIN_TONES.get(tone, "")
    if not modifier:
        return _TONEABLE_RE.sub(lambda m: m.group(1) + m.group(2), text)
    return _TONEABLE_RE.sub(lambda m: m.group(1) + modifier, text)


def tone_for(bot: Any, guild_id: int | None) -> str:
    """The tone a guild picked; a DM and a bot without a store both get the default."""
    store = getattr(bot, "store", None)
    if store is None or guild_id is None:
        return SKIN_TONE_DEFAULT
    try:
        chosen = store.get(guild_id, "emoji_skin_tone")
    except Exception:
        return SKIN_TONE_DEFAULT
    return chosen if chosen in SKIN_TONES else SKIN_TONE_DEFAULT
