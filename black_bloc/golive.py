from __future__ import annotations

import logging
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from typing import Any

import discord

from .settings_store import GOLIVE_TEMPLATE

log = logging.getLogger(__name__)

GAME_FALLBACK = "something"
TWITCH = "Twitch"
YOUTUBE = "YouTube"
END_SUFFIX = " — stream ended"
END_GRACE_SECONDS = 120
POLL_SECONDS = 60

NOBODY = "Someone"
EMBED_COLOURS = {TWITCH.casefold(): 0x9146FF, YOUTUBE.casefold(): 0xFF0000}
EMBED_COLOUR_DEFAULT = 0x5865F2
EMBED_NO_TITLE = "Live now"
EMBED_GAME_FIELD = "Game"
EMBED_FOOTER = "Black Bloc · via {source}"
EMBED_SOURCE_TWITCH = "Twitch"
EMBED_SOURCE_PRESENCE = "Discord activity"
EMBED_END_FOOTER = "· stream ended"
LIVE_VERB = "is now live"
ENDED_VERB = "was live"
AUTHOR_LIMIT = 256
TITLE_LIMIT = 256
FIELD_LIMIT = 1024
DISCORD_MEDIA = "https://media.discordapp.net/"
TWITCH_PREVIEW = "https://static-cdn.jtvnw.net/previews-ttv/live_user_{name}-1280x720.jpg"
YOUTUBE_THUMBNAIL = "https://i.ytimg.com/vi/{video}/hqdefault.jpg"


@dataclass(frozen=True)
class StreamInfo:
    url: str | None = None
    game: str | None = None
    title: str | None = None
    platform: str | None = None
    game_id: str | None = None
    box_art_url: str | None = None
    thumbnail_url: str | None = None


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
        return TWITCH
    if "youtube.com" in lowered or "youtu.be" in lowered:
        return YOUTUBE
    return None


def presence_image(activity: Any) -> str | None:
    """A streaming presence's own artwork, worked out from the asset, never fetched."""
    ready = _text(getattr(activity, "large_image_url", None))
    if ready:
        return ready
    assets = getattr(activity, "assets", None)
    raw = _text(assets.get("large_image")) if isinstance(assets, dict) else None
    if raw is None or any(ch.isspace() for ch in raw):
        return None
    if raw.startswith("mp:"):
        return DISCORD_MEDIA + raw[3:]
    if raw.startswith("twitch:"):
        return TWITCH_PREVIEW.format(name=raw[7:])
    if raw.startswith("youtube:"):
        return YOUTUBE_THUMBNAIL.format(video=raw[8:])
    return raw if raw.startswith("https://") else None


def extract_stream(activities: Any) -> StreamInfo | None:
    """The first streaming activity as a StreamInfo, or None when nobody is live."""
    for activity in activities or ():
        if not is_streaming(activity):
            continue
        url = _text(getattr(activity, "url", None))
        platform = platform_of(activity, url)
        title = _text(getattr(activity, "details", None)) or _text(getattr(activity, "name", None))
        return StreamInfo(
            url=url,
            game=_text(getattr(activity, "game", None)) or _text(getattr(activity, "state", None)),
            title=None if title == platform else title,
            platform=platform,
            thumbnail_url=presence_image(activity),
        )
    return None


def twitch_enrichable(info: StreamInfo) -> bool:
    """True only while a Twitch lookup could still be about this stream."""
    return (info.platform or TWITCH).casefold() == TWITCH.casefold()


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
        platform=TWITCH,
        game_id=_text(getattr(stream, "game_id", None)),
        thumbnail_url=_text(getattr(stream, "thumbnail_url", None)),
    )


def enriched(info: StreamInfo, stream: Any) -> StreamInfo:
    """Fill gaps in a presence StreamInfo from a Twitch stream row."""
    if stream is None or not twitch_enrichable(info):
        return info
    return StreamInfo(
        url=info.url or _text(getattr(stream, "url", None)),
        game=info.game or _text(getattr(stream, "game_name", None)),
        title=info.title or _text(getattr(stream, "title", None)),
        platform=info.platform or TWITCH,
        game_id=info.game_id or _text(getattr(stream, "game_id", None)),
        box_art_url=info.box_art_url,
        thumbnail_url=info.thumbnail_url or _text(getattr(stream, "thumbnail_url", None)),
    )


def with_box_art(info: StreamInfo, game: Any) -> StreamInfo:
    art = _text(getattr(game, "box_art_url", None))
    if not art or info.box_art_url:
        return info
    return replace(info, box_art_url=art)


def display_name(member: Any) -> str:
    return (
        _text(getattr(member, "display_name", None))
        or _text(getattr(member, "name", None))
        or NOBODY
    )


def _clip(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


def author_line(name: str, platform: str | None, *, ended: bool = False) -> str:
    verb = ENDED_VERB if ended else LIVE_VERB
    line = f"{name} {verb} on {platform}" if platform else f"{name} {verb}"
    return _clip(line if ended else line + "!", AUTHOR_LIMIT)


def embed_colour(platform: str | None) -> int:
    return EMBED_COLOURS.get((platform or "").casefold(), EMBED_COLOUR_DEFAULT)


def embed_footer(source: str | None) -> str:
    named = EMBED_SOURCE_TWITCH if source == "twitch" else EMBED_SOURCE_PRESENCE
    return EMBED_FOOTER.format(source=named)


def announcement_embed(
    info: StreamInfo, member: Any = None, source: str | None = None
) -> discord.Embed:
    """The go-live card: the streamer, the game and the game's art, never an avatar."""
    embed = discord.Embed(
        title=_clip(info.title or EMBED_NO_TITLE, TITLE_LIMIT),
        url=info.url or None,
        colour=discord.Colour(embed_colour(info.platform)),
        timestamp=datetime.now(UTC),
    )
    embed.set_author(name=author_line(display_name(member), info.platform))
    embed.add_field(name=EMBED_GAME_FIELD, value=_clip(info.game or GAME_FALLBACK, FIELD_LIMIT))
    image = info.box_art_url or info.thumbnail_url
    if image:
        embed.set_image(url=image)
    embed.set_footer(text=embed_footer(source))
    return embed


def ended_embed(embed: Any, name: str, platform: str | None) -> discord.Embed:
    """The same card once the stream is over; the art and the link stay put."""
    finished = discord.Embed.from_dict(embed.to_dict())
    finished.set_author(name=author_line(name, platform, ended=True))
    footer = _text(getattr(getattr(embed, "footer", None), "text", None)) or ""
    if not footer.endswith(EMBED_END_FOOTER):
        footer = f"{footer} {EMBED_END_FOOTER}" if footer else EMBED_END_FOOTER
    finished.set_footer(text=footer)
    return finished


def embed_summary(embed: Any) -> dict[str, Any]:
    fields = {field.name: field.value for field in getattr(embed, "fields", ())}
    return {
        "author": getattr(getattr(embed, "author", None), "name", None),
        "title": getattr(embed, "title", None),
        "game": fields.get(EMBED_GAME_FIELD),
        "image": getattr(getattr(embed, "image", None), "url", None),
    }


def render(
    template: str, info: StreamInfo, member: Any = None, *, ping_role_id: int | None = None
) -> str:
    """The announcement sentence; an empty game reads 'something', never '****'."""
    name = display_name(member)
    fields = _Fields(
        name=name,
        game=info.game or GAME_FALLBACK,
        title=info.title or "",
        url=info.url or "",
        platform=info.platform or "",
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
