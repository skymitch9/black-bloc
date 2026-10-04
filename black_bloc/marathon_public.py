"""A BaF run's public highlight: where it goes, what it says, and the button that moves it."""

from __future__ import annotations

from datetime import datetime, tzinfo
from typing import Any, NamedTuple

from . import marathon as mt
from . import marathon_announce as ma
from . import marathon_runner_posts as mrp
from .settings_store import (
    MARATHON_PART_COMMENTATOR_DONE_KEY,
    MARATHON_PART_COMMENTATOR_KEY,
    MARATHON_PART_HOST_DONE_KEY,
    MARATHON_PART_HOST_KEY,
    MARATHON_PART_RUNNER_DONE_KEY,
    MARATHON_PART_RUNNER_KEY,
)

POST = "post"
REMOVE = "remove"
OPT_OUT = ma.OPT_OUT
OPT_IN = ma.OPT_IN
LEGACY = {POST: OPT_IN, REMOVE: OPT_OUT}
TEMPLATE = (
    r"marathon:highlight:(?P<marathon_id>[0-9]+):(?P<run_id>[0-9]+)"
    r":(?P<to>post|remove|optout|optin)"
)
CUSTOM_ID = "marathon:highlight:{marathon_id}:{run_id}:{to}"
SHADOW_FEATURE = "marathon_public"
LABEL_LIMIT = 80
YES = ("on", "true", "yes", "1")
NO = ("off", "false", "no", "0")
BAD_SWITCH = (
    "Say on or off for whether the marathon highlights BaF runs by itself, so nothing was changed."
)
BAD_SWITCH_CODE = "bad_public_highlight"
DONE_PARTS = {
    MARATHON_PART_RUNNER_KEY: MARATHON_PART_RUNNER_DONE_KEY,
    MARATHON_PART_HOST_KEY: MARATHON_PART_HOST_DONE_KEY,
    MARATHON_PART_COMMENTATOR_KEY: MARATHON_PART_COMMENTATOR_DONE_KEY,
}
ROLE_MENTION = "<@&"
DATE_STAMP = "<t:{unix}:D>"


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


def move_of(to: Any) -> str:
    """A button posted before the opt-out answers as the toggle it stands for: Highlight opts
    the run's people back in, Remove the highlight opts them out."""
    return LEGACY.get(str(to), str(to))


def button_for(
    marathon_id: Any, row: Any, *, opted: set[int], out_label: str, in_label: str
) -> Button | None:
    """Opt back in while everyone of ours on the run is opted out; Opt out otherwise; nothing
    for a run nobody from BaF is on. It posts nothing."""
    members = mt.member_ids(row)
    if not members:
        return None
    if ma.all_out(members, opted):
        return Button(custom_id(marathon_id, row["id"], OPT_IN), label(in_label), OPT_IN)
    return Button(custom_id(marathon_id, row["id"], OPT_OUT), label(out_label), OPT_OUT)


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
                to = wanted.rsplit(":", 1)[-1]
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


def is_done(row: Any) -> bool:
    return mt._cell(row, "state") == mt.DONE


def done_words(words: dict[str, str]) -> dict[str, str]:
    """The same words with each part in the past tense: {part} is all a done post swaps."""
    return dict(words) | {
        present: words[past] for present, past in DONE_PARTS.items() if past in words
    }


def day_word(
    row: Any, now: datetime, zone: tzinfo, *, today: str, earlier: Any, earlier_default: str
) -> str:
    """Today while it is still the day the run ended in the server's zone, else its date."""
    ended = mrp.over_at(row)
    if ended is None or ended.astimezone(zone).date() >= now.astimezone(zone).date():
        return today
    return mt.render(
        earlier, earlier_default, date=DATE_STAMP.format(unix=mt.unix(ended))
    ).text


def done_text(
    row: Any,
    marathon: Any,
    words: dict[str, str],
    *,
    template: Any,
    default: str,
    url: str,
    unlisted: str,
    day: str,
    people: Any = None,
) -> str:
    fields = mrp.fields_of(
        row, marathon, done_words(words), url=url, unlisted=unlisted, people=people
    )
    return mt.render(template, default, **(fields | {"day": day})).text[: mt.MESSAGE_LIMIT]


def says(content: Any, text: str, *, done: bool) -> bool:
    """Whether a post already ends in these words; a done post must also carry no role mention
    in front of them."""
    content = str(content or "")
    if not text or not content.endswith(text):
        return False
    return not done or ROLE_MENTION not in content[: len(content) - len(text)]


__all__ = [
    "DONE_PARTS",
    "day_word",
    "done_text",
    "done_words",
    "is_done",
    "says",
    "BAD_SWITCH",
    "BAD_SWITCH_CODE",
    "Button",
    "LEGACY",
    "OPT_IN",
    "OPT_OUT",
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
    "move_of",
    "postable",
    "shown_button",
    "text_of",
]
