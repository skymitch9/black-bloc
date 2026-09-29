"""A BaF run's public highlight: where it goes, what it says, and the button that moves it."""

from __future__ import annotations

from typing import Any, NamedTuple

from . import marathon as mt
from . import marathon_runner_posts as mrp

POST = "post"
REMOVE = "remove"
TEMPLATE = r"marathon:highlight:(?P<marathon_id>[0-9]+):(?P<run_id>[0-9]+):(?P<to>post|remove)"
CUSTOM_ID = "marathon:highlight:{marathon_id}:{run_id}:{to}"
SHADOW_FEATURE = "marathon_public"
LABEL_LIMIT = 80
YES = ("on", "true", "yes", "1")
NO = ("off", "false", "no", "0")
BAD_SWITCH = (
    "Say on or off for whether the marathon highlights BaF runs by itself, so nothing was changed."
)
BAD_SWITCH_CODE = "bad_public_highlight"


class Button(NamedTuple):
    custom_id: str
    label: str
    to: str


def custom_id(marathon_id: Any, run_id: Any, to: str) -> str:
    return CUSTOM_ID.format(marathon_id=int(marathon_id), run_id=int(run_id), to=to)


def message_id(row: Any) -> int | None:
    found = mt._cell(row, "public_message_id")
    return int(found) if found else None


def channel_of(row: Any) -> int | None:
    found = mt._cell(row, "public_channel_id")
    return int(found) if found else None


def is_removed(row: Any) -> bool:
    return bool(mt._cell(row, "public_removed"))


def is_up(row: Any) -> bool:
    return bool(message_id(row)) and not is_removed(row)


def postable(row: Any) -> bool:
    return mt.is_ours(row) and mt._cell(row, "state") in mrp.POSTABLE


def highlights(marathon: Any) -> bool:
    """NULL or a missing column reads as off, the owner's default."""
    return bool(mt._cell(marathon, "public_highlight", 0))


def auto_wanted(marathon: Any, row: Any) -> bool:
    """Staff removed it: the switch never puts it back."""
    return highlights(marathon) and postable(row) and not message_id(row)


def clean_switch(given: Any) -> bool | None:
    if isinstance(given, bool):
        return given
    if isinstance(given, int):
        return {0: False, 1: True}.get(given)
    word = str(given if given is not None else "").strip().lower()
    if word in YES:
        return True
    if word in NO:
        return False
    return None


def label(text: Any) -> str:
    return str(text or "").strip()[:LABEL_LIMIT] or "…"


def button_for(
    marathon_id: Any, row: Any, *, has_channel: bool, post_label: str, remove_label: str
) -> Button | None:
    """Remove while it is up; Highlight while it could be; nothing otherwise."""
    if is_up(row):
        return Button(custom_id(marathon_id, row["id"], REMOVE), label(remove_label), REMOVE)
    if has_channel and postable(row):
        return Button(custom_id(marathon_id, row["id"], POST), label(post_label), POST)
    return None


def shown_button(message: Any) -> Button | None | bool:
    """What a fetched message carries: a Button, None for no button, or False when the
    message cannot say (it was never read with its components)."""
    rows = getattr(message, "components", None)
    if rows is None:
        return False
    for one in rows:
        for child in getattr(one, "children", ()) or ():
            wanted = str(getattr(child, "custom_id", "") or "")
            if wanted.startswith("marathon:highlight:"):
                to = REMOVE if wanted.endswith(":" + REMOVE) else POST
                return Button(wanted, str(getattr(child, "label", "") or ""), to)
    return None


def text_of(
    row: Any,
    marathon: Any,
    words: dict[str, str],
    *,
    template: Any,
    default: str,
    url: str,
    unlisted: str,
    people: Any = None,
) -> str:
    return mrp.post_text(
        row,
        marathon,
        words,
        template=template,
        default=default,
        url=url,
        unlisted=unlisted,
        people=people,
    ).text


__all__ = [
    "BAD_SWITCH",
    "BAD_SWITCH_CODE",
    "Button",
    "POST",
    "REMOVE",
    "SHADOW_FEATURE",
    "TEMPLATE",
    "auto_wanted",
    "button_for",
    "channel_of",
    "clean_switch",
    "custom_id",
    "highlights",
    "is_removed",
    "is_up",
    "label",
    "message_id",
    "postable",
    "shown_button",
    "text_of",
]
