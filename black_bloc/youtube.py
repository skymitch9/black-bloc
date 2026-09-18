from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any, NamedTuple
from xml.etree import ElementTree

from .panels import KEEP_IT as KEEP_IT
from .panels import panel_minutes as _panel_minutes
from .settings_store import YOUTUBE_TEMPLATE
from .youtube_live import (
    LIVE_URL,
    PROBE_REFUSED,
    Confirm,
    Probe,
    read_confirm,
    read_page,
    read_search,
)

log = logging.getLogger(__name__)

FEED_URL = "https://www.youtube.com/feeds/videos.xml"
API_URL = "https://www.googleapis.com/youtube/v3"
CHANNEL_URL = "https://www.youtube.com/channel/{channel_id}"
WATCH_URL = "https://www.youtube.com/watch?v={video_id}"
REQUEST_TIMEOUT_SECONDS = 15
FEED_ATTEMPTS = 4
CLASSIFY_BATCH = 50
SHORT_SECONDS = 60
BROWSER_AGENT = (
    "Mozilla/5.0 (compatible; BlackBloc/1.0; +https://blackbloc.heygabi.ai)"
)

VIDEO = "video"
SHORT = "short"
LIVE = "live"
UNKNOWN = "unknown"

ATOM = "http://www.w3.org/2005/Atom"
YT = "http://www.youtube.com/xml/schemas/2015"
NS = {"a": ATOM, "yt": YT}

CHANNEL_ID = re.compile(r"^UC[A-Za-z0-9_-]{22}$")
CHANNEL_IN_URL = re.compile(r"youtube\.com/channel/(UC[A-Za-z0-9_-]{22})")
CANONICAL = re.compile(
    r'<link\s+rel="canonical"\s+href="https://www\.youtube\.com/channel/(UC[A-Za-z0-9_-]{22})"'
)
HANDLE = re.compile(r"^@?([A-Za-z0-9._-]{3,30})$")
HANDLE_IN_URL = re.compile(r"youtube\.com/(?:@|c/|user/)([A-Za-z0-9._-]{1,60})")
DURATION = re.compile(r"^P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$")

CANNOT_RESOLVE = (
    "I could not turn **{given}** into a YouTube channel id, so nothing was linked. Paste the "
    "channel address that starts with youtube.com/channel/UC…, or ask a Lead to set a YouTube "
    "API key so handles like @yourname can be looked up."
)
FEED_REFUSED = (
    "YouTube's feed server would not answer for that channel after {attempts} tries. That is "
    "usually the feed being flaky rather than the channel being wrong, so nothing was changed — "
    "try again in a minute."
)


class YouTubeError(RuntimeError):
    """YouTube refused a request or answered with something unusable."""

    def __init__(self, message: str, *, network: bool = False) -> None:
        super().__init__(message)
        self.network = network


@dataclass(frozen=True)
class Video:
    video_id: str
    title: str = ""
    url: str = ""
    published: str = ""
    channel_id: str = ""
    author: str = ""
    kind: str = VIDEO

    @property
    def link(self) -> str:
        return self.url or WATCH_URL.format(video_id=self.video_id)


class _Fields(dict):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def kind_of(url: Any) -> str:
    return SHORT if "/shorts/" in str(url or "") else VIDEO


def _text(node: Any, path: str) -> str:
    if node is None:
        return ""
    found = node.findtext(path, None, NS)
    return str(found).strip() if found else ""


def _entry(node: Any) -> Video | None:
    video_id = _text(node, "yt:videoId")
    if not video_id:
        return None
    link = node.find("a:link", NS)
    url = str(link.get("href") or "").strip() if link is not None else ""
    return Video(
        video_id=video_id,
        title=_text(node, "a:title"),
        url=url or WATCH_URL.format(video_id=video_id),
        published=_text(node, "a:published"),
        channel_id=_text(node, "yt:channelId"),
        author=_text(node, "a:author/a:name"),
        kind=kind_of(url),
    )


def parse_feed(xml: Any) -> list[Video]:
    """Every readable entry of a channel Atom feed; an entry with no video id is dropped."""
    body = xml.decode("utf-8", "replace") if isinstance(xml, bytes) else str(xml or "")
    if not body.strip():
        return []
    try:
        root = ElementTree.fromstring(body)
    except ElementTree.ParseError as exc:
        raise YouTubeError(
            f"YouTube's feed was not readable XML: {exc}", network=True
        ) from exc
    found: list[Video] = []
    for node in root.findall("a:entry", NS):
        video = _entry(node)
        if video is not None:
            found.append(video)
    return found


def feed_title(xml: Any) -> str:
    body = xml.decode("utf-8", "replace") if isinstance(xml, bytes) else str(xml or "")
    try:
        root = ElementTree.fromstring(body)
    except ElementTree.ParseError:
        return ""
    return _text(root, "a:title")


def duration_seconds(text: Any) -> int | None:
    match = DURATION.match(str(text or "").strip())
    if match is None:
        return None
    days, hours, minutes, seconds = (int(part or 0) for part in match.groups())
    return days * 86400 + hours * 3600 + minutes * 60 + seconds


def classify_row(row: dict[str, Any]) -> str:
    """One videos.list row to a kind; live beats short, and an unreadable length is unknown."""
    if row.get("liveStreamingDetails"):
        return LIVE
    details = row.get("contentDetails")
    if not isinstance(details, dict):
        return UNKNOWN
    length = duration_seconds(details.get("duration"))
    if length is None:
        return UNKNOWN
    return SHORT if length <= SHORT_SECONDS else VIDEO


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


def render(
    template: str,
    video: Video,
    member: Any = None,
    *,
    ping_role_id: int | None = None,
    fan_role_id: int | None = None,
) -> str:
    """The upload sentence; a broken template falls back to the default one with a warning."""
    from .golive import display_name, ping_prefix

    fields = _Fields(
        name=display_name(member),
        title=video.title or "a new video",
        url=video.link,
        channel=video.author or "",
        kind=video.kind,
    )
    try:
        text = template.format_map(fields)
    except Exception as exc:
        log.warning(
            "youtube: template %r could not be rendered (%s); using the default", template, exc
        )
        text = YOUTUBE_TEMPLATE.format_map(fields)
    return ping_prefix(ping_role_id, fan_role_id) + text


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

    async def fetch_feed(
        self, channel_id: str, etag: str | None = None
    ) -> tuple[int, str | None, list[Video]]:
        """The channel's entries, retried past the feed's own flakiness; 304 means unchanged."""
        headers = {"User-Agent": BROWSER_AGENT}
        if etag:
            headers["If-None-Match"] = etag
        status = 0
        seen: list[int] = []
        for _ in range(FEED_ATTEMPTS):
            status, response_headers, body = await self._request(
                "GET", FEED_URL, headers=headers, params={"channel_id": channel_id}
            )
            seen.append(status)
            if status == 304:
                return (status, etag, [])
            if status == 200:
                return (status, response_headers.get("ETag") or None, parse_feed(body))
        log.warning("youtube: the feed for %s answered %s", channel_id, seen)
        raise YouTubeError(FEED_REFUSED.format(attempts=FEED_ATTEMPTS), network=True)

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

    async def _title_of(self, channel_id: str) -> str:
        try:
            status, _headers, body = await self._request(
                "GET",
                FEED_URL,
                headers={"User-Agent": BROWSER_AGENT},
                params={"channel_id": channel_id},
            )
        except YouTubeError:
            return ""
        return feed_title(body) if status == 200 else ""

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

    async def classify(self, video_ids: Any) -> dict[str, str]:
        """Kind per video id from the API; without a key nothing is claimed, so it answers empty."""
        wanted = [str(one) for one in video_ids or () if str(one or "").strip()]
        if not wanted or not self.keyed:
            return {}
        found: dict[str, str] = {}
        for start in range(0, len(wanted), CLASSIFY_BATCH):
            chunk = wanted[start : start + CLASSIFY_BATCH]
            payload = await self._api(
                "videos",
                {"part": "contentDetails,liveStreamingDetails,snippet", "id": ",".join(chunk)},
            )
            for row in payload.get("items") or ():
                video_id = str(row.get("id") or "")
                if video_id:
                    found[video_id] = classify_row(row)
        return found


PANEL_MINUTES_KEY = "youtube_panel_minutes"
PANEL_TITLE = "Your YouTube channel"
PANEL_TIMEOUT_FOOTER = "This panel has gone quiet — run /youtube again"
SELECT_CAP = 25

NOT_SEEDED_YET = "not checked yet"
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
SETUP = "setup"
LOGS = "logs"
REFRESH = "refresh"
BACK = "back"

UNLINK_QUESTION = (
    "Forget your YouTube channel? Black Bloc stops watching it for new uploads. You can link "
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
SETUP_MOVE = PanelMove(SETUP, "Setup", "secondary", row=3)
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
    SETUP_MOVE,
    LOGS_MOVE,
)

CARD_BUTTONS: dict[tuple[bool, bool], tuple[PanelMove, ...]] = {
    (True, False): (LINK_MOVE,),
    (True, True): (RELINK_MOVE, UNLINK_MOVE),
    (False, False): (),
    (False, True): (RELINK_FOR_MOVE, UNLINK_FOR_MOVE),
}
STAFF_MOVES = (LINK_FOR_MOVE, SETUP_MOVE, LOGS_MOVE)


def card_buttons(*, linked: bool, mine: bool, staff: bool) -> tuple[PanelMove, ...]:
    """The §C table as data: what a card offers is the product of whose it is and its state."""
    found = list(CARD_BUTTONS[(bool(mine), bool(linked))])
    found.append(REFRESH_MOVE)
    if not mine:
        found.append(BACK_MOVE)
    elif staff:
        found.extend(STAFF_MOVES)
    return tuple(found)


def where_words(mode: str, channel_id: Any) -> str:
    """Why an upload would not be posted, in words — never a bare mode name on its own."""
    if mode != "on":
        return f"no — upload announcements are **{mode}** for this server at the moment"
    if not channel_id:
        return "no — nowhere is set to post them; a Lead picks one under **Setup** on this panel"
    return f"yes, in <#{channel_id}>"


def status_lines(row: Any, latest_title: Any, *, where: str, shorts: Any) -> list[str]:
    seen = latest_title or ("none yet" if row["seeded"] else NOT_SEEDED_YET)
    return [
        f"**channel** — {row['title'] or row['channel_id']}",
        f"**linked** — {row['linked_at']}",
        f"**last video seen** — {seen}",
        f"**announced here** — {where}",
        f"**Shorts** — {'announced too' if shorts else 'not announced'}",
    ]


def health_lines(
    *,
    mode: str,
    channel_id: Any,
    minutes: Any,
    keyed: bool,
    last_ok_at: Any,
    last_error: Any,
    failures: int,
    totals: dict[str, int],
    live: dict[str, Any] | None = None,
) -> list[str]:
    lines = [
        f"**mode** — {mode}",
        f"**channel** — {f'<#{channel_id}>' if channel_id else 'not set'}",
        f"**every** — {minutes} minute(s)",
        f"**api key** — {'set' if keyed else 'not set (feed only)'}",
        f"**last good sweep** — {last_ok_at or 'never'}",
        f"**last error** — {last_error or 'none'}"
        + (f" ({failures} sweep(s) in a row)" if failures else ""),
        f"**links** — {totals['links']} · **videos seen** — {totals['videos']} · "
        f"**announced** — {totals['announced']}",
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
        seen = "seeded" if row["seeded"] else NOT_SEEDED_YET
        lines.append(f"• {named} — {row['title'] or row['channel_id']} ({seen})")
    return lines


def panel_minutes(store: Any, guild_id: int) -> int:
    return _panel_minutes(store, guild_id, PANEL_MINUTES_KEY)
