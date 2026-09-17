from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .golive import YOUTUBE, YOUTUBE_THUMBNAIL, StreamInfo

LIVE_URL = "https://www.youtube.com/channel/{channel_id}/live"
WATCH_URL = "https://www.youtube.com/watch?v={video_id}"
UNREADABLE_EVERY_SECONDS = 3600

IS_LIVE = re.compile(r'"isLive"\s*:\s*true')
IS_UPCOMING = re.compile(r'"isUpcoming"\s*:\s*true')
CANONICAL_WATCH = re.compile(
    r'<link\s+rel="canonical"\s+href="https://www\.youtube\.com/watch\?v=([A-Za-z0-9_-]{11})"'
)
VIDEO_ID = re.compile(r'"videoId"\s*:\s*"([A-Za-z0-9_-]{11})"')
READABLE = re.compile(r'ytInitialData|<link\s+rel="canonical"')

THUMBNAIL_ORDER = ("maxres", "standard", "high", "medium", "default")

PROBE_REFUSED = "YouTube answered {status} for {channel}'s live page."
CONFIRM_REFUSED = "YouTube's API said nothing about {video_id}."


@dataclass(frozen=True)
class Probe:
    """The two facts the /live page is read for, and whether it was readable at all."""

    live: bool = False
    upcoming: bool = False
    video_id: str | None = None
    readable: bool = False

    @property
    def announceable(self) -> bool:
        return self.live and bool(self.video_id)


@dataclass(frozen=True)
class Confirm:
    started: bool = False
    ended: bool = False
    title: str = ""
    channel_title: str = ""
    thumbnail: str = ""
    video_id: str = ""

    @property
    def live(self) -> bool:
        return self.started and not self.ended


def _body(html: Any) -> str:
    if isinstance(html, bytes):
        return html.decode("utf-8", "replace")
    return str(html or "")


def read_page(html: Any) -> Probe:
    """A page that is not the shape this reads stays `readable=False`, never a raise."""
    body = _body(html)
    if not READABLE.search(body):
        return Probe()
    upcoming = IS_UPCOMING.search(body) is not None
    live = IS_LIVE.search(body) is not None and not upcoming
    found = CANONICAL_WATCH.search(body) or VIDEO_ID.search(body)
    return Probe(
        live=live,
        upcoming=upcoming,
        video_id=found.group(1) if found else None,
        readable=True,
    )


def _thumbnail(snippet: Any) -> str:
    art = (snippet or {}).get("thumbnails")
    if not isinstance(art, dict):
        return ""
    for name in THUMBNAIL_ORDER:
        one = art.get(name)
        url = str(one.get("url") or "").strip() if isinstance(one, dict) else ""
        if url:
            return url
    return ""


def read_confirm(payload: Any, video_id: Any = "") -> Confirm | None:
    """One `videos.list` answer; anything that is not that row reads as nothing confirmed."""
    if not isinstance(payload, dict):
        return None
    wanted = str(video_id or "")
    rows = [row for row in (payload.get("items") or ()) if isinstance(row, dict)]
    row = next((one for one in rows if str(one.get("id") or "") == wanted), None)
    if row is None:
        row = rows[0] if rows and not wanted else None
    if row is None:
        return None
    details = row.get("liveStreamingDetails")
    details = details if isinstance(details, dict) else {}
    snippet = row.get("snippet")
    snippet = snippet if isinstance(snippet, dict) else {}
    return Confirm(
        started=bool(str(details.get("actualStartTime") or "").strip()),
        ended=bool(str(details.get("actualEndTime") or "").strip()),
        title=str(snippet.get("title") or "").strip(),
        channel_title=str(snippet.get("channelTitle") or "").strip(),
        thumbnail=_thumbnail(snippet),
        video_id=str(row.get("id") or wanted),
    )


def after_probe(misses: Any, live: Any) -> int:
    """A live read clears the count; anything else adds one, so a hiccup never ends a stream."""
    return 0 if live else max(0, int(misses or 0)) + 1


def is_over(misses: Any, limit: Any) -> bool:
    return max(0, int(misses or 0)) >= max(1, int(limit or 1))


def stream_info(
    video_id: Any, title: Any = "", thumbnail: Any = ""
) -> StreamInfo:
    """What the go-live path is handed: no game, so the card reads `something`, never a guess."""
    wanted = str(video_id or "")
    return StreamInfo(
        url=WATCH_URL.format(video_id=wanted),
        game=None,
        title=str(title or "").strip() or None,
        platform=YOUTUBE,
        thumbnail_url=str(thumbnail or "").strip()
        or YOUTUBE_THUMBNAIL.format(video=wanted),
    )
