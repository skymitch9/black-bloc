from __future__ import annotations

import json
import logging
import re
from typing import Any, NamedTuple

from .panels import KEEP_IT as KEEP_IT
from .panels import panel_minutes as _panel_minutes
from .youtube_live import (
    BOT_CHECK,
    LIVE_URL,
    PROBE_REFUSED,
    WATCH_URL,
    Confirm,
    Probe,
    read_confirm,
    read_page,
    read_search,
)

log = logging.getLogger(__name__)

API_URL = "https://www.googleapis.com/youtube/v3"
REQUEST_TIMEOUT_SECONDS = 15
BROWSER_AGENT = (
    "Mozilla/5.0 (compatible; BlackBloc/1.0; +https://blackbloc.heygabi.ai)"
)

CHANNEL_ID = re.compile(r"^UC[A-Za-z0-9_-]{22}$")
CHANNEL_IN_URL = re.compile(r"youtube\.com/channel/(UC[A-Za-z0-9_-]{22})")
CANONICAL = re.compile(
    r'<link\s+rel="canonical"\s+href="https://www\.youtube\.com/channel/(UC[A-Za-z0-9_-]{22})"'
)
HANDLE = re.compile(r"^@?([A-Za-z0-9._-]{3,30})$")
HANDLE_IN_URL = re.compile(r"youtube\.com/(?:@|c/|user/)([A-Za-z0-9._-]{1,60})")

VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
VIDEO_IN_URL = re.compile(
    r"(?:youtube\.com/(?:watch\?(?:\S*?&(?:amp;)?)?v=|live/|shorts/|embed/)|youtu\.be/)"
    r"([A-Za-z0-9_-]{11})"
)
VIDEO_CHANNEL_META = re.compile(
    r'<meta\s+itemprop="channelId"\s+content="(UC[A-Za-z0-9_-]{22})"'
)
VIDEO_CHANNEL_JSON = re.compile(
    r'"(?:channelId|externalChannelId)"\s*:\s*"(UC[A-Za-z0-9_-]{22})"'
)
VIDEO_OWNER_NAME = re.compile(r'"ownerChannelName"\s*:\s*"([^"]{1,120})"')

CANNOT_RESOLVE = (
    "I could not turn **{given}** into a YouTube channel id, so nothing was linked. Paste the "
    "channel address that starts with youtube.com/channel/UC…, or ask a Lead to set a YouTube "
    "API key so handles like @yourname can be looked up."
)
CANNOT_READ_VIDEO = (
    "I could not tell which channel the video **{given}** belongs to, so nothing was linked. "
    "Paste the channel address that starts with youtube.com/channel/UC… instead."
)
VIDEO_PAGE_REFUSED = (
    "YouTube answered {status} for the video {video}, so the channel behind it is unknown."
)
VIDEO_CHALLENGED = (
    "YouTube asked Black Bloc to sign in and prove it is not a robot instead of showing the "
    "video {video}, so the channel behind it could not be read."
)


class YouTubeError(RuntimeError):
    """YouTube refused a request or answered with something unusable."""

    def __init__(self, message: str, *, network: bool = False) -> None:
        super().__init__(message)
        self.network = network


def channel_id_in(text: Any) -> str | None:
    """A channel id out of a bare id or a /channel/ address; never out of a handle."""
    given = str(text or "").strip()
    if CHANNEL_ID.match(given):
        return given
    found = CHANNEL_IN_URL.search(given)
    return found.group(1) if found else None


def handle_in(text: Any) -> str | None:
    given = str(text or "").strip()
    found = HANDLE_IN_URL.search(given)
    if found:
        return found.group(1)
    if "/" in given or " " in given:
        return None
    named = HANDLE.match(given)
    return named.group(1) if named else None


def video_id_in(text: Any) -> str | None:
    """A video id out of the four address shapes YouTube uses; never out of a bare word."""
    found = VIDEO_IN_URL.search(str(text or "").strip())
    return found.group(1) if found else None


def _json_text(raw: str) -> str:
    try:
        return str(json.loads(f'"{raw.rstrip(chr(92))}"'))
    except ValueError:
        return raw


def read_video_channel(html: Any) -> tuple[str, str] | None:
    """The owner's channel off a watch page; a challenge page names nobody and answers None."""
    body = html if isinstance(html, str) else str(html or "")
    found = VIDEO_CHANNEL_META.search(body) or VIDEO_CHANNEL_JSON.search(body)
    if found is None:
        return None
    named = VIDEO_OWNER_NAME.search(body)
    return (found.group(1), _json_text(named.group(1)) if named else "")


def title_of(payload: Any) -> str:
    """The channel title out of one `channels.list` answer; anything else is no title at all."""
    if not isinstance(payload, dict):
        return ""
    for row in payload.get("items") or ():
        snippet = row.get("snippet") if isinstance(row, dict) else None
        title = str((snippet or {}).get("title") or "").strip()
        if title:
            return title
    return ""


class YouTubeClient:
    def __init__(self, api_key: str | None = None, *, request: Any = None) -> None:
        self.api_key = (api_key or "").strip() or None
        self._request = request or self._aiohttp_request
        self._session: Any = None

    @property
    def keyed(self) -> bool:
        return self.api_key is not None

    async def _aiohttp_request(
        self, method: str, url: str, *, headers: Any = None, params: Any = None
    ) -> tuple[int, dict[str, str], str]:
        import aiohttp

        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT_SECONDS)
            )
        try:
            async with self._session.request(
                method, url, headers=headers, params=params
            ) as response:
                return (response.status, dict(response.headers), await response.text())
        except (TimeoutError, aiohttp.ClientError, OSError) as exc:
            raise YouTubeError(
                f"youtube unreachable: {type(exc).__name__}: {exc}", network=True
            ) from exc

    async def close(self) -> None:
        if self._session is not None and not self._session.closed:
            await self._session.close()
        self._session = None

    async def _api(self, path: str, params: dict[str, str]) -> dict[str, Any]:
        if not self.keyed:
            raise YouTubeError("YouTube's own API needs YOUTUBE_API_KEY, which is not set.")
        status, _headers, body = await self._request(
            "GET", f"{API_URL}/{path}", params={**params, "key": self.api_key}
        )
        try:
            payload = json.loads(body or "{}")
        except ValueError:
            payload = {}
        if status != 200 or not isinstance(payload, dict):
            said = ""
            if isinstance(payload, dict):
                said = str((payload.get("error") or {}).get("message") or "")
            raise YouTubeError(
                f"YouTube's API answered {status} for {path}. {said}".strip(), network=True
            )
        return payload

    async def resolve(self, text: Any) -> tuple[str, str]:
        """A channel id and its title from an id, an address or a handle; the key is optional."""
        given = str(text or "").strip()
        found = channel_id_in(given)
        if found:
            return (found, await self._title_of(found))
        handle = handle_in(given)
        if handle is None:
            raise YouTubeError(CANNOT_RESOLVE.format(given=given[:60] or "nothing"))
        if self.keyed:
            return await self._resolve_with_key(handle, given)
        return await self.resolve_without_key(handle, given)

    async def _resolve_with_key(self, handle: str, given: str) -> tuple[str, str]:
        for field in ("forHandle", "forUsername"):
            wanted = f"@{handle}" if field == "forHandle" else handle
            payload = await self._api("channels", {"part": "snippet", field: wanted})
            for row in payload.get("items") or ():
                channel_id = str(row.get("id") or "")
                if CHANNEL_ID.match(channel_id):
                    title = str((row.get("snippet") or {}).get("title") or "")
                    return (channel_id, title)
        return await self.resolve_without_key(handle, given)

    async def resolve_without_key(self, handle: str, given: str = "") -> tuple[str, str]:
        """The channel page's canonical link; its `channelId` fields are other channels'."""
        status, _headers, body = await self._request(
            "GET",
            f"https://www.youtube.com/@{handle}",
            headers={"User-Agent": BROWSER_AGENT},
        )
        found = CANONICAL.search(body or "") if status == 200 else None
        if found is None:
            raise YouTubeError(CANNOT_RESOLVE.format(given=(given or handle)[:60]))
        channel_id = found.group(1)
        return (channel_id, await self._title_of(channel_id))

    async def resolve_video_channel(self, video_id: Any) -> tuple[str, str]:
        """Which channel a video belongs to: one API unit with a key, else the watch page."""
        wanted = str(video_id or "").strip()
        if not VIDEO_ID.match(wanted):
            raise YouTubeError(CANNOT_READ_VIDEO.format(given=wanted[:60] or "nothing"))
        if self.keyed:
            found = await self._video_channel_with_key(wanted)
            if found is not None:
                return found
        status, _headers, body = await self._request(
            "GET",
            WATCH_URL.format(video_id=wanted),
            headers={"User-Agent": BROWSER_AGENT},
        )
        if status != 200:
            raise YouTubeError(
                VIDEO_PAGE_REFUSED.format(status=status, video=wanted), network=True
            )
        found = read_video_channel(body)
        if found is None:
            raise YouTubeError(
                VIDEO_CHALLENGED.format(video=wanted)
                if BOT_CHECK.search(body or "")
                else CANNOT_READ_VIDEO.format(given=wanted)
            )
        return found

    async def _video_channel_with_key(self, video_id: str) -> tuple[str, str] | None:
        """One unit; an empty answer falls through to the page rather than refusing."""
        payload = await self._api("videos", {"part": "snippet", "id": video_id})
        for row in payload.get("items") or ():
            snippet = (row.get("snippet") if isinstance(row, dict) else None) or {}
            channel_id = str(snippet.get("channelId") or "")
            if CHANNEL_ID.match(channel_id):
                return (channel_id, str(snippet.get("channelTitle") or ""))
        return None

    async def _title_of(self, channel_id: str) -> str:
        """One unit, and only where a key exists; without one a channel goes by its id."""
        if not self.keyed:
            return ""
        try:
            payload = await self._api("channels", {"part": "snippet", "id": channel_id})
        except YouTubeError:
            return ""
        return title_of(payload)

    async def probe_live(self, channel_id: str) -> Probe:
        """The quota-free `/live` page: two facts, a tolerant parse, no key and no units."""
        status, _headers, body = await self._request(
            "GET",
            LIVE_URL.format(channel_id=channel_id),
            headers={"User-Agent": BROWSER_AGENT},
        )
        if status != 200:
            raise YouTubeError(
                PROBE_REFUSED.format(status=status, channel=channel_id), network=True
            )
        return read_page(body)

    async def confirm_live(self, video_id: Any) -> Confirm | None:
        """One unit of quota; without a key nothing is claimed, so it answers None."""
        wanted = str(video_id or "").strip()
        if not wanted or not self.keyed:
            return None
        payload = await self._api(
            "videos", {"part": "snippet,liveStreamingDetails", "id": wanted}
        )
        return read_confirm(payload, wanted)

    async def search_live(self, channel_id: Any) -> str | None:
        """100 units, so it is asked only where the page would not say: which video is live."""
        wanted = str(channel_id or "").strip()
        if not wanted or not self.keyed:
            return None
        payload = await self._api(
            "search",
            {
                "part": "id",
                "channelId": wanted,
                "eventType": "live",
                "type": "video",
                "maxResults": "1",
            },
        )
        return read_search(payload)


PANEL_MINUTES_KEY = "youtube_panel_minutes"
PANEL_TITLE = "Your YouTube channel"
PANEL_TIMEOUT_FOOTER = "This panel has gone quiet — run /youtube again"
SELECT_CAP = 25

NOBODY_LINKED = "Nobody has linked a YouTube channel yet."
LIVE_NO_KEY = (
    "**quota used today** — none; with no YOUTUBE_API_KEY a live stream is announced from the "
    "page alone, so its title reads *Live now*"
)
BOT_CHECKED = (
    "yes — YouTube served the last probe its *Sign in to confirm you're not a bot* page, which "
    "carries no video id; the stream is still spotted, and with a key the id is searched for"
)

LINK = "link"
RELINK = "relink"
UNLINK = "unlink"
RELINK_FOR = "relink_for"
UNLINK_FOR = "unlink_for"
LINK_FOR = "link_for"
LOGS = "logs"
REFRESH = "refresh"
BACK = "back"

UNLINK_QUESTION = (
    "Forget your YouTube channel? Black Bloc stops watching it for live streams. You can link "
    "it again whenever you like."
)
UNLINK_YES = "Yes, forget it"


class PanelMove(NamedTuple):
    action: str
    label: str
    style: str = "secondary"
    row: int = 0
    question: str = ""
    yes: str = ""
    modal: bool = False


LINK_MOVE = PanelMove(LINK, "Link my channel", "primary", modal=True)
RELINK_MOVE = PanelMove(RELINK, "Relink…", "secondary", modal=True)
UNLINK_MOVE = PanelMove(
    UNLINK, "Unlink", "danger", question=UNLINK_QUESTION, yes=UNLINK_YES
)
RELINK_FOR_MOVE = PanelMove(RELINK_FOR, "Relink for…", "secondary", modal=True)
UNLINK_FOR_MOVE = PanelMove(UNLINK_FOR, "Unlink for", "danger", modal=True)
REFRESH_MOVE = PanelMove(REFRESH, "Refresh", "secondary")
BACK_MOVE = PanelMove(BACK, "Back", "secondary")
LINK_FOR_MOVE = PanelMove(LINK_FOR, "Link for somebody…", "secondary", row=3)
LOGS_MOVE = PanelMove(LOGS, "Logs", "secondary", row=3)

PANEL_MOVES = (
    LINK_MOVE,
    RELINK_MOVE,
    UNLINK_MOVE,
    RELINK_FOR_MOVE,
    UNLINK_FOR_MOVE,
    REFRESH_MOVE,
    BACK_MOVE,
    LINK_FOR_MOVE,
    LOGS_MOVE,
)

CARD_BUTTONS: dict[tuple[bool, bool], tuple[PanelMove, ...]] = {
    (True, False): (LINK_MOVE,),
    (True, True): (RELINK_MOVE, UNLINK_MOVE),
    (False, False): (),
    (False, True): (RELINK_FOR_MOVE, UNLINK_FOR_MOVE),
}
STAFF_MOVES = (LINK_FOR_MOVE, LOGS_MOVE)


def card_buttons(*, linked: bool, mine: bool, staff: bool) -> tuple[PanelMove, ...]:
    """The §C table as data: what a card offers is the product of whose it is and its state."""
    found = list(CARD_BUTTONS[(bool(mine), bool(linked))])
    found.append(REFRESH_MOVE)
    if not mine:
        found.append(BACK_MOVE)
    elif staff:
        found.extend(STAFF_MOVES)
    return tuple(found)


def where_words(mode: str, golive_mode: str, channel_id: Any) -> str:
    """Why a live stream would not be announced, in words — never a bare mode name on its own."""
    if mode != "on":
        return f"no — live-stream announcements are **{mode}** for this server at the moment"
    if not channel_id:
        return (
            "no — a live stream is announced through the go-live feature and no go-live channel "
            "is set; a Lead picks one under **Setup** on `/golive`"
        )
    if golive_mode != "on":
        return (
            f"no — go-live announcements are **{golive_mode}**, and a live stream is announced "
            "through them"
        )
    return f"yes, in <#{channel_id}>"


def status_lines(row: Any, *, where: str) -> list[str]:
    return [
        f"**channel** — {row['title'] or row['channel_id']}",
        f"**linked** — {row['linked_at']}",
        f"**announced here** — {where}",
    ]


def health_lines(
    *,
    keyed: bool,
    links: int,
    live: dict[str, Any] | None = None,
) -> list[str]:
    lines = [
        f"**api key** — {'set' if keyed else 'not set (the live page alone)'}",
        f"**links** — {links}",
    ]
    return lines + live_lines(live, keyed=keyed)


def live_lines(live: dict[str, Any] | None, *, keyed: bool = False) -> list[str]:
    """What the live poller is doing; the quota line only exists where a key does."""
    if not live:
        return []
    lines = [
        f"**live streams** — {live.get('mode')}",
        f"**probed every** — {live.get('minutes')} minute(s)",
        f"**last probe** — {live.get('last_probe_at') or 'never'}",
        f"**last probe error** — {live.get('last_probe_error') or 'none'}",
        f"**channels probed** — {live.get('probed') or 0}",
        f"**live now** — {live.get('open') or 0}",
        f"**reading live now** — {live.get('reading_live') or 0}",
        f"**bot check** — {BOT_CHECKED if live.get('botcheck') else 'no'}",
    ]
    if keyed:
        lines.append(f"**quota used today** — {live.get('quota') or 0} unit(s)")
    else:
        lines.append(LIVE_NO_KEY)
    return lines


def link_lines(rows: Any, names: dict[int, str] | None = None) -> list[str]:
    found = list(rows or ())
    if not found:
        return [NOBODY_LINKED]
    known = names or {}
    lines = []
    for row in found:
        named = known.get(int(row["user_id"])) or row["user_id"]
        lines.append(f"• {named} — {row['title'] or row['channel_id']}")
    return lines


def panel_minutes(store: Any, guild_id: int) -> int:
    return _panel_minutes(store, guild_id, PANEL_MINUTES_KEY)
