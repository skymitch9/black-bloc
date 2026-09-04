from __future__ import annotations

import logging
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from typing import Any

import discord

from .panels import panel_minutes as library_panel_minutes
from .panels import site_page_url as library_site_page_url
from .settings_store import GOLIVE_END_EDIT, GOLIVE_END_SUFFIX, GOLIVE_TEMPLATE

log = logging.getLogger(__name__)

GAME_FALLBACK = "something"
TWITCH = "Twitch"
YOUTUBE = "YouTube"
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
EMBED_END_MARK = "·"
ANNOUNCEMENT_LEFT = "left"
END_TRIM = " \t—–-·|,;:"
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


def end_marker(suffix: str | None) -> str:
    """The stream-ended wording with its leading separator taken off, for the footer."""
    return (suffix or "").strip(END_TRIM)


def ended_footer(footer: str, suffix: str | None) -> str:
    marker = end_marker(suffix)
    if not marker:
        return footer
    tail = f"{EMBED_END_MARK} {marker}"
    if footer.endswith(tail):
        return footer
    return f"{footer} {tail}" if footer else tail


def ended_embed(
    embed: Any, name: str, platform: str | None, suffix: str | None = GOLIVE_END_SUFFIX
) -> discord.Embed:
    """The same card once the stream is over; the art and the link stay put."""
    finished = discord.Embed.from_dict(embed.to_dict())
    finished.set_author(name=author_line(name, platform, ended=True))
    footer = _text(getattr(getattr(embed, "footer", None), "text", None)) or ""
    finished.set_footer(text=ended_footer(footer, suffix) or None)
    return finished


def embed_summary(embed: Any) -> dict[str, Any]:
    fields = {field.name: field.value for field in getattr(embed, "fields", ())}
    return {
        "author": getattr(getattr(embed, "author", None), "name", None),
        "title": getattr(embed, "title", None),
        "game": fields.get(EMBED_GAME_FIELD),
        "image": getattr(getattr(embed, "image", None), "url", None),
    }


def ping_prefix(*role_ids: Any) -> str:
    """The role mentions in front of an announcement: given order, no repeats, none is empty."""
    seen: list[int] = []
    for role_id in role_ids:
        if role_id and int(role_id) not in seen:
            seen.append(int(role_id))
    return "".join(f"<@&{role_id}> " for role_id in seen)


def render(
    template: str,
    info: StreamInfo,
    member: Any = None,
    *,
    ping_role_id: int | None = None,
    fan_role_id: int | None = None,
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
    return ping_prefix(ping_role_id, fan_role_id) + text


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


def edits_on_end(end_mode: Any) -> bool:
    """True only for the one mode that touches the announcement once the stream is over."""
    return end_mode == GOLIVE_END_EDIT


def end_details(end_mode: Any) -> dict[str, str]:
    return {} if edits_on_end(end_mode) else {"announcement": ANNOUNCEMENT_LEFT}


def end_summary(end_mode: Any, suffix: str | None = GOLIVE_END_SUFFIX) -> str:
    """One phrase for the staff panel: what happens to an announcement once the stream ends."""
    if edits_on_end(end_mode):
        return f'{GOLIVE_END_EDIT} ("{suffix or ""}")'
    return f"{end_mode} (left as posted)"


def ended_text(text: str, suffix: str | None = GOLIVE_END_SUFFIX) -> str:
    tail = suffix or ""
    if not tail.strip() or text.endswith(tail):
        return text
    return text + tail


PANEL_MINUTES_KEY = "golive_panel_minutes"
PANEL_TITLE = "Go-live"
PANEL_TIMEOUT_FOOTER = "This panel has gone quiet — run /golive again"
SITE_BUTTON = "Open on the site"
PANEL_INTRO = "Your Twitch channel, and whether your streams get announced."
NO_LINK_LINE = (
    "**Your Twitch channel** — none linked yet. Linking one lets Black Bloc fill in your game "
    "and title, and spot streams Discord does not show."
)
LINK_LINE = "**Your Twitch channel** — twitch.tv/{login}"
LINK_UNVERIFIED = (
    " — not verified with Twitch, so the game and title may not fill in. **Change my channel** "
    "re-checks it."
)
OPTED_OUT_LINE = (
    "**Your streams** — not announced, because you opted out. **Announce my streams again** "
    "undoes that."
)
ANNOUNCED_LINE = "**Your streams** — announced here whenever Black Bloc sees you go live."
MODE_LINES = {
    "off": (
        "Go-live announcements are **off** right now, so nobody's streams are announced. "
        "Linking still counts: raid trains and fan roles read it."
    ),
    "shadow": (
        "Go-live announcements are in **shadow** right now — the log says what would have been "
        "posted and nothing is."
    ),
}


@dataclass(frozen=True)
class PanelMove:
    """One control on the go-live panel: what it says, where it sits, what it does."""

    label: str
    style: str
    action: str
    row: int = 0
    needs_modal: bool = False


LINK_CHANNEL = PanelMove("Link my Twitch channel", "primary", "link", needs_modal=True)
CHANGE_CHANNEL = PanelMove("Change my channel", "secondary", "change", needs_modal=True)
UNLINK_CHANNEL = PanelMove("Unlink", "danger", "unlink")
STOP_ANNOUNCING = PanelMove("Stop announcing my streams", "danger", "optout", row=1)
ANNOUNCE_AGAIN = PanelMove("Announce my streams again", "success", "optin", row=1)
REFRESH = PanelMove("Refresh", "secondary", "refresh", row=2)
LOGS = PanelMove("Logs", "secondary", "logs", row=2)
STREAMERS = PanelMove("Streamers…", "secondary", "streamers", row=2)

PANEL_BUTTONS: dict[tuple[bool, bool], tuple[PanelMove, ...]] = {
    (False, False): (LINK_CHANNEL, STOP_ANNOUNCING, REFRESH),
    (False, True): (LINK_CHANNEL, ANNOUNCE_AGAIN, REFRESH),
    (True, False): (CHANGE_CHANNEL, UNLINK_CHANNEL, STOP_ANNOUNCING, REFRESH),
    (True, True): (CHANGE_CHANNEL, UNLINK_CHANNEL, ANNOUNCE_AGAIN, REFRESH),
}
STAFF_BUTTONS: tuple[PanelMove, ...] = (LOGS, STREAMERS)


def panel_buttons(
    *, linked: bool, opted_out: bool, staff: bool = False
) -> tuple[PanelMove, ...]:
    """The controls this panel actually offers — never one the shared function would refuse."""
    found = PANEL_BUTTONS[(bool(linked), bool(opted_out))]
    return found + STAFF_BUTTONS if staff else found


def card_lines(
    login: Any,
    verified: Any,
    opted_out: Any,
    *,
    mode: Any = None,
    channel_note: Any = None,
) -> list[str]:
    """The half of the embed that is about the person reading it."""
    lines = [PANEL_INTRO]
    if login:
        lines.append(LINK_LINE.format(login=login) + ("" if verified else LINK_UNVERIFIED))
    else:
        lines.append(NO_LINK_LINE)
    lines.append(OPTED_OUT_LINE if opted_out else ANNOUNCED_LINE)
    said = MODE_LINES.get(str(mode or ""))
    if said:
        lines.append(said)
    if channel_note:
        lines.append(str(channel_note))
    return lines


def panel_minutes(store: Any, guild_id: int) -> int:
    return library_panel_minutes(store, guild_id, PANEL_MINUTES_KEY)


def site_page_url(origin: Any) -> str | None:
    return library_site_page_url(origin, "golive")
