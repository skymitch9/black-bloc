from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import discord

from .settings_store import GOLIVE_TEMPLATE

log = logging.getLogger(__name__)

GAME_FALLBACK = "something"
END_SUFFIX = " — stream ended"
END_GRACE_SECONDS = 120
POLL_SECONDS = 60


@dataclass(frozen=True)
class StreamInfo:
    url: str | None = None
    game: str | None = None
    title: str | None = None
    platform: str | None = None


class _Fields(dict):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def is_streaming(activity: Any) -> bool:
    if isinstance(activity, discord.Streaming):
        return True
    return getattr(activity, "type", None) == discord.ActivityType.streaming


def platform_of(activity: Any, url: str | None) -> str | None:
    named = _text(getattr(activity, "platform", None))
    if named:
        return named
    lowered = (url or "").lower()
    if "twitch.tv" in lowered:
        return "Twitch"
    if "youtube.com" in lowered or "youtu.be" in lowered:
        return "YouTube"
    return None


def extract_stream(activities: Any) -> StreamInfo | None:
    """The first streaming activity as a StreamInfo, or None when nobody is live."""
    for activity in activities or ():
        if not is_streaming(activity):
            continue
        url = _text(getattr(activity, "url", None))
        return StreamInfo(
            url=url,
            game=_text(getattr(activity, "game", None)) or _text(getattr(activity, "state", None)),
            title=_text(getattr(activity, "details", None))
            or _text(getattr(activity, "name", None)),
            platform=platform_of(activity, url),
        )
    return None


def twitch_login_from_url(url: str | None) -> str | None:
    lowered = (url or "").strip().lower()
    if "twitch.tv/" not in lowered:
        return None
    tail = lowered.split("twitch.tv/", 1)[1]
    login = tail.split("?")[0].split("/")[0].strip()
    return login or None


def from_twitch(stream: Any) -> StreamInfo:
    return StreamInfo(
        url=getattr(stream, "url", None),
        game=_text(getattr(stream, "game_name", None)),
        title=_text(getattr(stream, "title", None)),
        platform="Twitch",
    )


def enriched(info: StreamInfo, stream: Any) -> StreamInfo:
    """Fill gaps in a presence StreamInfo from a Twitch stream row."""
    if stream is None:
        return info
    return StreamInfo(
        url=info.url or _text(getattr(stream, "url", None)),
        game=info.game or _text(getattr(stream, "game_name", None)),
        title=info.title or _text(getattr(stream, "title", None)),
        platform=info.platform or "Twitch",
    )


def render(
    template: str, info: StreamInfo, member: Any = None, *, ping_role_id: int | None = None
) -> str:
    """The announcement sentence; an empty game reads 'something', never '****'."""
    name = (
        _text(getattr(member, "display_name", None))
        or _text(getattr(member, "name", None))
        or "Someone"
    )
    fields = _Fields(
        name=name,
        game=info.game or GAME_FALLBACK,
        title=info.title or "",
        url=info.url or "",
    )
    try:
        text = template.format_map(fields)
    except Exception as exc:
        log.warning(
            "go-live: template %r could not be rendered (%s); using the default", template, exc
        )
        text = GOLIVE_TEMPLATE.format_map(fields)
    if ping_role_id:
        return f"<@&{ping_role_id}> {text}"
    return text


def parse_ts(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def should_announce(now: datetime, last_session: Any, cooldown_minutes: int) -> bool:
    """False while a session is open, and until the cooldown has passed since the last one."""
    if last_session is None:
        return True
    raw = last_session["ended_at"]
    if raw is None or str(raw).strip() == "":
        return False
    ended = parse_ts(raw)
    if ended is None:
        log.warning(
            "go-live: session ended_at %r is unreadable; treating the session as ended", raw
        )
        return True
    return now - ended >= timedelta(minutes=max(0, int(cooldown_minutes)))


def passes_role_filters(
    role_ids: Any, require_role_id: int | None, ignore_role_id: int | None
) -> bool:
    held = {int(role_id) for role_id in role_ids}
    if require_role_id and int(require_role_id) not in held:
        return False
    if ignore_role_id and int(ignore_role_id) in held:
        return False
    return True


def ended_text(text: str) -> str:
    if text.endswith(END_SUFFIX):
        return text
    return text + END_SUFFIX
