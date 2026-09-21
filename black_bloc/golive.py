from __future__ import annotations

import logging
import re
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from typing import Any

import discord

from .panels import panel_minutes as library_panel_minutes
from .panels import site_page_url as library_site_page_url
from .settings_store import (
    GOLIVE_COSTREAM_AUTHOR,
    GOLIVE_COSTREAM_ON,
    GOLIVE_COSTREAM_TEMPLATE,
    GOLIVE_END_TEMPLATE,
    GOLIVE_LIVE_FIELD,
    GOLIVE_TEMPLATE,
)

log = logging.getLogger(__name__)

GAME_FALLBACK = "something"
TWITCH = "Twitch"
YOUTUBE = "YouTube"
END_GRACE_SECONDS = 120
POLL_SECONDS = 60

HISTORY_NAME_CAP = 10
HISTORY_AND_MORE = "{shown}, and {more} more"
HISTORY_PERSON = "person"
HISTORY_PEOPLE = "people"
HISTORY_NOTHING = (
    "Nothing to link — nobody in the go-live history is missing a channel, so nothing changed."
)
HISTORY_NOBODY = "Linked nobody new"
HISTORY_LINKED = "Linked {count} {people} ({names})"
HISTORY_OPTED_OUT = "skipped {count} who asked not to be announced"
HISTORY_TAKEN_ONE = "1 channel already belongs to somebody else ({names})"
HISTORY_TAKEN_MANY = "{count} channels already belong to somebody else ({names})"
HISTORY_UNREADABLE = "{count} could not be read ({names})"
HISTORY_LEFT = "skipped {count} who have left"

NOBODY = "Someone"
EMBED_COLOURS = {TWITCH.casefold(): 0x9146FF, YOUTUBE.casefold(): 0xFF0000}
EMBED_COLOUR_DEFAULT = 0x5865F2
EMBED_NO_TITLE = "Live now"
EMBED_GAME_FIELD = "Game"
EMBED_FOOTER = "Black Bloc · via {source}"
COSTREAM_SOURCE = "{first} + {second}"
SUPPRESSED = "<{url}>"
EMBED_SOURCE_TWITCH = "Twitch"
EMBED_SOURCE_PRESENCE = "Discord activity"
EMBED_SOURCE_YOUTUBE = "YouTube"
EMBED_SOURCES = {"twitch": EMBED_SOURCE_TWITCH, "youtube": EMBED_SOURCE_YOUTUBE}
EMBED_END_MARK = "·"
END_TRIM = " \t—–-·|,;:"
END_MARK_DEFAULT = "stream ended"
LIVE_VERB = "is now live"
ENDED_VERB = "was live"
DURATION_SHORT = "under a minute"
DURATION_MINUTES = "{minutes} min"
DURATION_HOURS = "{hours} h"
DURATION_BOTH = "{hours} h {minutes} min"
SUMMARY_CHARS = 40
MENTION_PREFIX = re.compile(r"^(?:<@&\d+>[ \t]*)+")
EMPTY_BRACKETS = re.compile(r"\([ \t]*\)|\[[ \t]*\]")
DANGLING = re.compile(
    r"[ \t]+(?:for|on|in|at|—|–|·)(?=[ \t]*(?:[.,;:!?)\]]|$))", re.IGNORECASE | re.MULTILINE
)
DOUBLE_SPACE = re.compile(r"[ \t]{2,}")
SPACE_BEFORE_STOP = re.compile(r"[ \t]+([.,;:!?])")
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


def platform_of_url(url: Any) -> str | None:
    lowered = str(url or "").lower()
    if "twitch.tv" in lowered:
        return TWITCH
    if "youtube.com" in lowered or "youtu.be" in lowered:
        return YOUTUBE
    return None


def platform_of(activity: Any, url: str | None) -> str | None:
    named = _text(getattr(activity, "platform", None))
    return named or platform_of_url(url)


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


def live_author(template: Any, name: str, platform: str | None) -> str:
    """The card's top line while they are live; blank wording keeps 'is now live on'."""
    wanted = str(template or "").strip()
    if wanted:
        try:
            line = tidy(wanted.format_map(_Fields(name=name, platform=platform or "")))
        except Exception as exc:
            log.warning(
                "go-live: live author %r could not be rendered (%s); using the default",
                template,
                exc,
            )
            line = ""
        if line:
            return _clip(line, AUTHOR_LIMIT)
    return author_line(name, platform)


def embed_colour(platform: str | None) -> int:
    return EMBED_COLOURS.get((platform or "").casefold(), EMBED_COLOUR_DEFAULT)


def embed_footer(source: str | None) -> str:
    named = EMBED_SOURCES.get(str(source or ""), EMBED_SOURCE_PRESENCE)
    return EMBED_FOOTER.format(source=named)


def announcement_embed(
    info: StreamInfo,
    member: Any = None,
    source: str | None = None,
    *,
    name: Any = None,
    author: Any = "",
) -> discord.Embed:
    """The go-live card: the streamer, the game and the game's art, never an avatar."""
    embed = discord.Embed(
        title=_clip(info.title or EMBED_NO_TITLE, TITLE_LIMIT),
        url=info.url or None,
        colour=discord.Colour(embed_colour(info.platform)),
        timestamp=datetime.now(UTC),
    )
    embed.set_author(name=live_author(author, name or display_name(member), info.platform))
    embed.add_field(name=EMBED_GAME_FIELD, value=_clip(info.game or GAME_FALLBACK, FIELD_LIMIT))
    image = info.box_art_url or info.thumbnail_url
    if image:
        embed.set_image(url=image)
    embed.set_footer(text=embed_footer(source))
    return embed


def end_marker(template: Any) -> str:
    """What the one end wording adds after `{live}`, for the card's footer."""
    wanted = str(template or "").strip()
    if not wanted:
        return ""
    if GOLIVE_LIVE_FIELD not in wanted:
        return END_MARK_DEFAULT
    tail = wanted.rsplit(GOLIVE_LIVE_FIELD, 1)[-1].strip(END_TRIM)
    return END_MARK_DEFAULT if "{" in tail else tail


def ended_footer(footer: str, template: Any) -> str:
    marker = end_marker(template)
    if not marker:
        return footer
    tail = f"{EMBED_END_MARK} {marker}"
    if footer.endswith(tail):
        return footer
    return f"{footer} {tail}" if footer else tail


def tidy(text: str) -> str:
    """The gaps an empty placeholder leaves: no `()`, no doubled space, no dangling `for`."""
    cleaned = EMPTY_BRACKETS.sub("", text)
    cleaned = DANGLING.sub("", cleaned)
    cleaned = DOUBLE_SPACE.sub(" ", cleaned)
    return SPACE_BEFORE_STOP.sub(r"\1", cleaned).strip()


def humanise_duration(started_at: Any, ended_at: Any) -> str:
    """How long a stream ran, in words; a missing or unreadable stamp renders as nothing."""
    began = parse_ts(started_at)
    over = parse_ts(ended_at)
    if began is None or over is None:
        return ""
    minutes = int((over - began).total_seconds()) // 60
    if minutes < 1:
        return DURATION_SHORT
    hours, left = divmod(minutes, 60)
    if not hours:
        return DURATION_MINUTES.format(minutes=left)
    return (
        DURATION_HOURS.format(hours=hours)
        if not left
        else DURATION_BOTH.format(hours=hours, minutes=left)
    )


def as_info(source: Any) -> StreamInfo:
    """A StreamInfo whether the caller holds one or a `golive_sessions` row."""
    if isinstance(source, StreamInfo):
        return source
    wanted = ("url", "game", "title", "platform")
    return StreamInfo(**{name: _row_field(source, name) for name in wanted})


def _row_field(source: Any, key: str) -> Any:
    if source is None:
        return None
    try:
        return source[key]
    except (IndexError, KeyError, TypeError):
        return getattr(source, key, None)


def history_urls(rows: Any) -> dict[int, dict[str, str]]:
    """The newest address per member per platform, out of session rows newest first."""
    found: dict[int, dict[str, str]] = {}
    for row in rows or ():
        user_id = _row_field(row, "user_id")
        if user_id is None:
            continue
        mine = found.setdefault(int(user_id), {})
        for key in ("url", "also_url"):
            url = _text(_row_field(row, key))
            platform = platform_of_url(url)
            if url and platform and platform not in mine:
                mine[platform] = url
    return {user_id: urls for user_id, urls in found.items() if urls}


def _named(names: Any) -> str:
    found = list(names or ())
    shown = ", ".join(found[:HISTORY_NAME_CAP])
    if len(found) <= HISTORY_NAME_CAP:
        return shown
    return HISTORY_AND_MORE.format(shown=shown, more=len(found) - HISTORY_NAME_CAP)


def history_said(
    *,
    linked: Any,
    opted_out: Any,
    taken: Any,
    unreadable: Any,
    left: Any,
) -> str:
    """The sweep's answer in words: who was linked, and everybody it would not touch."""
    if not any((linked, opted_out, taken, unreadable, left)):
        return HISTORY_NOTHING
    bits = [
        HISTORY_LINKED.format(
            count=len(linked),
            people=HISTORY_PERSON if len(linked) == 1 else HISTORY_PEOPLE,
            names=_named(linked),
        )
        if linked
        else HISTORY_NOBODY
    ]
    if opted_out:
        bits.append(HISTORY_OPTED_OUT.format(count=len(opted_out)))
    if taken:
        said = HISTORY_TAKEN_ONE if len(taken) == 1 else HISTORY_TAKEN_MANY
        bits.append(said.format(count=len(taken), names=_named(taken)))
    if unreadable:
        bits.append(HISTORY_UNREADABLE.format(count=len(unreadable), names=_named(unreadable)))
    if left:
        bits.append(HISTORY_LEFT.format(count=len(left)))
    return ", ".join(bits) + "."


def mention_prefix(content: Any) -> str:
    """The role mentions `render` put at the very front of an announcement, if any."""
    found = MENTION_PREFIX.match(str(content or ""))
    return found.group(0) if found else ""


def without_mention(content: Any) -> str:
    return MENTION_PREFIX.sub("", str(content or ""))


def ended_fields(info: Any, name: str, duration: str) -> dict[str, str]:
    stream = as_info(info)
    return _Fields(
        name=name,
        game=stream.game or GAME_FALLBACK,
        title=stream.title or "",
        url=stream.url or "",
        platform=stream.platform or "",
        duration=duration or "",
    )


def ended_render(
    template: Any,
    info_or_row: Any,
    name: str,
    *,
    content: Any = "",
    duration: str = "",
    keep_mention: bool = False,
) -> str:
    """The announcement once the stream is over; `{live}` is the sentence as it was posted."""
    prefix = mention_prefix(content) if keep_mention else ""
    plain = without_mention(content)
    fields = ended_fields(info_or_row, name, duration)
    fields["live"] = plain
    wanted = str(template or "").strip()
    if not wanted:
        return prefix + plain
    try:
        return prefix + tidy(wanted.format_map(fields))
    except Exception as exc:
        log.warning(
            "go-live: end wording %r could not be rendered (%s); using the default wording",
            template,
            exc,
        )
        return prefix + tidy(GOLIVE_END_TEMPLATE.format_map(fields))


def ended_author(
    template: Any, name: str, platform: str | None, *, duration: str = ""
) -> str:
    """The card's top line once the stream is over; blank wording keeps 'was live on'."""
    wanted = str(template or "").strip()
    if wanted:
        try:
            line = tidy(
                wanted.format_map(
                    _Fields(name=name, platform=platform or "", duration=duration or "")
                )
            )
        except Exception as exc:
            log.warning(
                "go-live: end author %r could not be rendered (%s); using the default",
                template,
                exc,
            )
            line = ""
        if line:
            return _clip(line, AUTHOR_LIMIT)
    return author_line(name, platform, ended=True)


def ended_embed(
    embed: Any,
    name: str,
    platform: str | None,
    template: Any = GOLIVE_END_TEMPLATE,
    *,
    author: Any = "",
    duration: str = "",
) -> discord.Embed:
    """The same card once the stream is over; the art and the link stay put."""
    finished = discord.Embed.from_dict(embed.to_dict())
    finished.set_author(name=ended_author(author, name, platform, duration=duration))
    footer = _text(getattr(getattr(embed, "footer", None), "text", None)) or ""
    finished.set_footer(text=ended_footer(footer, template) or None)
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


def live_fields(info: StreamInfo, name: str) -> _Fields:
    return _Fields(
        name=name,
        game=info.game or GAME_FALLBACK,
        title=info.title or "",
        url=info.url or "",
        platform=info.platform or "",
    )


def _filled(template: Any, fields: _Fields, fallback: str) -> str:
    try:
        return template.format_map(fields)
    except Exception as exc:
        log.warning(
            "go-live: template %r could not be rendered (%s); using the default", template, exc
        )
        return fallback.format_map(fields)


def render(
    template: str,
    info: StreamInfo,
    member: Any = None,
    *,
    ping_role_id: int | None = None,
    fan_role_id: int | None = None,
    name: Any = None,
) -> str:
    """The announcement sentence; an empty game reads 'something', never '****'."""
    fields = live_fields(info, name or display_name(member))
    return ping_prefix(ping_role_id, fan_role_id) + _filled(template, fields, GOLIVE_TEMPLATE)


def again_render(template: Any, info_or_row: Any, name: str, *, content: Any = "") -> str:
    """The same sentence for an EDIT: the message keeps whatever prefix it already carries."""
    fields = live_fields(as_info(info_or_row), name)
    return mention_prefix(content) + _filled(template, fields, GOLIVE_TEMPLATE)


def suppressed(url: Any) -> str:
    """A link Discord must not preview; the fill wraps it, never the wording."""
    text = _text(url)
    return SUPPRESSED.format(url=text) if text else ""


def leads(platform: Any) -> bool:
    return (platform or "").casefold() == TWITCH.casefold()


def costream_order(first: StreamInfo, second: StreamInfo) -> tuple[StreamInfo, StreamInfo]:
    """Twitch is written first whichever arrived first, and is the only link with a preview."""
    if leads(second.platform) and not leads(first.platform):
        return second, first
    return first, second


def costream_fields(first: StreamInfo, second: StreamInfo, name: str) -> _Fields:
    fields = live_fields(first, name)
    fields["also_url"] = suppressed(second.url)
    fields["also_platform"] = second.platform or ""
    return fields


def costream_render(
    template: Any, first: StreamInfo, second: StreamInfo, name: str, *, content: Any = ""
) -> str:
    """Both platforms in one sentence, for an edit of the announcement already posted."""
    fields = costream_fields(first, second, name)
    return mention_prefix(content) + _filled(template, fields, GOLIVE_COSTREAM_TEMPLATE)


def costream_author(
    template: Any, first: StreamInfo, second: StreamInfo, name: str
) -> str:
    """The card's top line while two platforms are live; blank wording keeps today's."""
    fields = costream_fields(first, second, name)
    wanted = str(template or "").strip()
    if wanted:
        line = tidy(_filled(wanted, fields, GOLIVE_COSTREAM_AUTHOR))
        if line:
            return _clip(line, AUTHOR_LIMIT)
    return author_line(name, first.platform)


def costream_footer(first: StreamInfo, second: StreamInfo) -> str:
    return EMBED_FOOTER.format(
        source=COSTREAM_SOURCE.format(
            first=first.platform or EMBED_SOURCE_PRESENCE,
            second=second.platform or EMBED_SOURCE_PRESENCE,
        )
    )


def costream_embed(
    embed: Any, first: StreamInfo, second: StreamInfo, name: str, author: Any = ""
) -> discord.Embed:
    """The same card with both platforms on it; the art and the Twitch link stay put."""
    both = discord.Embed.from_dict(embed.to_dict())
    both.set_author(name=costream_author(author, first, second, name))
    both.colour = discord.Colour(embed_colour(first.platform))
    both.url = first.url or None
    both.set_footer(text=costream_footer(first, second))
    return both


def single_embed(
    embed: Any, info: StreamInfo, name: str, source: Any = None, author: Any = ""
) -> discord.Embed:
    """The card back on one platform once the other has gone; the session is still live."""
    alone = discord.Embed.from_dict(embed.to_dict())
    alone.set_author(name=live_author(author, name, info.platform))
    alone.colour = discord.Colour(embed_colour(info.platform))
    alone.url = info.url or None
    alone.set_footer(text=embed_footer(source))
    return alone


def joins_session(row: Any, platform: Any, mode: Any) -> bool:
    """True when a second platform joins the open session rather than being held back."""
    if str(mode or "") != GOLIVE_COSTREAM_ON:
        return False
    if _text(_row_field(row, "also_source")):
        return False
    open_platform = _text(_row_field(row, "platform"))
    wanted = _text(platform)
    if not open_platform or not wanted:
        return False
    return open_platform.casefold() != wanted.casefold()



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


def end_summary(template: Any = "") -> str:
    """One phrase for the staff panel: what an announcement says once the stream ends."""
    wanted = str(template or "").strip()
    if not wanted:
        return "edited (the sentence as posted, nothing added)"
    if GOLIVE_LIVE_FIELD in wanted:
        return f'edited (appended: "{_clip(wanted, SUMMARY_CHARS)}")'
    return f'edited (rewritten: "{_clip(wanted, SUMMARY_CHARS)}")'


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
SPOTLIGHT = PanelMove("Channels…", "secondary", "spotlight", row=2)
LINK_HISTORY = PanelMove("Link from history", "secondary", "history", row=1)

PANEL_BUTTONS: dict[tuple[bool, bool], tuple[PanelMove, ...]] = {
    (False, False): (LINK_CHANNEL, STOP_ANNOUNCING, REFRESH),
    (False, True): (LINK_CHANNEL, ANNOUNCE_AGAIN, REFRESH),
    (True, False): (CHANGE_CHANNEL, UNLINK_CHANNEL, STOP_ANNOUNCING, REFRESH),
    (True, True): (CHANGE_CHANNEL, UNLINK_CHANNEL, ANNOUNCE_AGAIN, REFRESH),
}
STAFF_BUTTONS: tuple[PanelMove, ...] = (LOGS, STREAMERS, SPOTLIGHT, LINK_HISTORY)


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
