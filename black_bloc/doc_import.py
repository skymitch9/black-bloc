from __future__ import annotations

import asyncio
import html as html_text
import logging
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qs, urljoin, urlsplit

from .linkcheck import USER_AGENT

log = logging.getLogger(__name__)

EXPORT_URL = "https://docs.google.com/document/d/{id}/export?format=html"
DOCS_HOST = "docs.google.com"
DRIVE_HOST = "drive.google.com"
CONTENT_HOST_TAIL = ".googleusercontent.com"
SIGN_IN_HOST = "accounts.google.com"
ID = r"[A-Za-z0-9_-]{20,}"
DOC_PATH = re.compile(rf"^/document(?:/u/\d+)?/d/({ID})(?:/.*)?$")
FILE_PATH = re.compile(rf"^/file(?:/u/\d+)?/d/({ID})(?:/.*)?$")
OPEN_PATHS = ("/open", "/uc")
ONLY_ID = re.compile(rf"^{ID}$")
TITLE = re.compile(r"<title[^>]*>(.*?)</title\s*>", re.IGNORECASE | re.DOTALL)
SIGN_IN_MARKS = (
    "accounts.google.com/ServiceLogin",
    "accounts.google.com/v3/signin",
    "accounts.google.com/signin",
)
REDIRECTS = (301, 302, 303, 307, 308)
NOT_ALLOWED = (401, 403)
MISSING = (404, 410)
LINK_MAX = 2048
TITLE_MAX = 200
MAX_HOPS = 5
MAX_BYTES = 2 * 1024 * 1024
TIMEOUT_SECONDS = 8
FROM_DOCS = "doc"
FROM_DRIVE = "drive"

NO_LINK = "Paste a Google Doc's link into the box first — nothing was fetched."
NOT_A_GOOGLE_LINK = (
    "That is not a Google Docs link, so nothing was fetched. Paste the address of a Google Doc "
    "— it starts https://docs.google.com/document/d/ — or its Drive link "
    "(https://drive.google.com/file/d/…)."
)
DOC_NOT_PUBLIC = (
    "Google would not show that doc to Black Bloc because it is not shared publicly, so nothing "
    "was imported. In the doc press **Share → General access → Anyone with the link → Viewer**, "
    "then press Import again. Black Bloc never signs in to Google, so it can only read a doc "
    "anyone with the link can open."
)
DOC_NOT_FOUND = (
    "Google says there is no doc at that link, so nothing was imported. Check the link is the "
    "whole address and that the doc has not been deleted."
)
NOT_A_DOC = (
    "That link is a file in Drive that is not a Google Doc (a Word file or a PDF uploaded to "
    "Drive), so it cannot be converted — only Google Docs convert. Open it and use **File → Save "
    "as Google Docs**, share the new copy (Anyone with the link → Viewer) and import that link."
)
DOC_TOO_BIG = (
    "That doc is bigger than Black Bloc will fetch (2 MB of page), so nothing was imported. A "
    "post is a few thousand characters at most — copy the part you want and paste it into the "
    "box instead; pasting keeps the formatting too."
)
DOC_TIMEOUT = (
    "Google did not answer within {seconds} seconds, so nothing was imported. That is a problem "
    "reaching Google, not a problem with the doc's sharing — try again in a minute."
)
DOC_UNREACHABLE = (
    "Black Bloc could not fetch the doc from Google just now, so nothing was imported. That is a "
    "problem reaching Google, not a problem with the doc's sharing — try again in a minute."
)
DOC_WENT_ELSEWHERE = (
    "Google sent Black Bloc somewhere other than Google Docs while fetching that doc, so it "
    "stopped and imported nothing. That is a fetch problem, not the doc's sharing — try again, "
    "and tell a Lead if it keeps happening."
)
IMPORTED = (
    "Imported **{title}** into the box. Nothing is saved or posted until you press Save Changes "
    "or Post it."
)


@dataclass(frozen=True)
class Hop:
    status: int
    location: str | None = None
    content_type: str = ""
    body: bytes = b""
    too_big: bool = False


@dataclass(frozen=True)
class Doc:
    doc_id: str
    html: str
    title: str
    size: int


class DocImportError(Exception):
    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(code)
        self.status = status
        self.code = code
        self.message = message


def parse_link(url: Any) -> tuple[str, str] | None:
    """(id, where it came from) for a Google Docs or Drive link, else None."""
    text = str(url or "").strip()
    if not text or len(text) > LINK_MAX or any(ch.isspace() for ch in text):
        return None
    if "://" not in text and text.lower().startswith((DOCS_HOST, DRIVE_HOST)):
        text = f"https://{text}"
    try:
        parts = urlsplit(text)
        port = parts.port
    except ValueError:
        return None
    if parts.scheme.lower() not in ("http", "https") or port is not None:
        return None
    if parts.username is not None or parts.password is not None:
        return None
    host = (parts.hostname or "").lower()
    if host == DOCS_HOST:
        found = DOC_PATH.match(parts.path)
        return (found.group(1), FROM_DOCS) if found else None
    if host != DRIVE_HOST:
        return None
    found = FILE_PATH.match(parts.path)
    if found:
        return (found.group(1), FROM_DRIVE)
    if parts.path.rstrip("/") in OPEN_PATHS:
        ids = parse_qs(parts.query).get("id") or []
        if len(ids) == 1 and ONLY_ID.match(ids[0]):
            return (ids[0], FROM_DRIVE)
    return None


def doc_id(url: Any) -> str | None:
    found = parse_link(url)
    return found[0] if found else None


def export_url(found_id: str) -> str:
    if not ONLY_ID.match(str(found_id or "")):
        raise DocImportError(400, "not_a_google_doc_link", NOT_A_GOOGLE_LINK)
    return EXPORT_URL.format(id=found_id)


def hop_allowed(
    url: str, hosts: tuple[str, ...] = (DOCS_HOST,), tails: tuple[str, ...] = (CONTENT_HOST_TAIL,)
) -> bool:
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError:
        return False
    host = (parts.hostname or "").lower()
    if parts.scheme.lower() != "https" or port not in (None, 443):
        return False
    if parts.username is not None or parts.password is not None:
        return False
    return host in hosts or any(host.endswith(tail) for tail in tails)


def is_sign_in(url: str) -> bool:
    try:
        return (urlsplit(url).hostname or "").lower() == SIGN_IN_HOST
    except ValueError:
        return False


def looks_like_sign_in(page: str) -> bool:
    return "<form" in page.lower() and any(mark in page for mark in SIGN_IN_MARKS)


def title_of(page: str) -> str:
    found = TITLE.search(page)
    said = html_text.unescape(found.group(1)) if found else ""
    return " ".join(said.split())[:TITLE_MAX]


async def aiohttp_hop(
    url: str, *, seconds: float, limit: int, agent: str = USER_AGENT
) -> Hop:
    """One GET, redirects NOT followed, the body read up to one byte past the cap."""
    import aiohttp

    try:
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=seconds)
        ) as session:
            async with session.get(
                url, allow_redirects=False, headers={"User-Agent": agent}
            ) as response:
                location = response.headers.get("Location")
                kind = response.headers.get("Content-Type", "")
                if response.status != 200:
                    return Hop(int(response.status), location, kind)
                if (response.content_length or 0) > limit:
                    return Hop(200, location, kind, b"", True)
                chunks: list[bytes] = []
                total = 0
                while total <= limit:
                    chunk = await response.content.read(min(65536, limit + 1 - total))
                    if not chunk:
                        break
                    chunks.append(chunk)
                    total += len(chunk)
                body = b"".join(chunks)
                return Hop(200, location, kind, body[:limit], total > limit)
    except TimeoutError as exc:
        raise DocImportError(
            504, "doc_timeout", DOC_TIMEOUT.format(seconds=TIMEOUT_SECONDS)
        ) from exc
    except (aiohttp.ClientError, OSError) as exc:
        raise DocImportError(502, "doc_unreachable", DOC_UNREACHABLE) from exc


def _missing(source: str) -> DocImportError:
    if source == FROM_DRIVE:
        return DocImportError(422, "not_a_google_doc", NOT_A_DOC)
    return DocImportError(404, "doc_not_found", DOC_NOT_FOUND)


async def _walk(found_id: str, source: str, get: Any) -> Doc:
    url = export_url(found_id)
    for _ in range(MAX_HOPS + 1):
        if is_sign_in(url):
            raise DocImportError(409, "doc_not_public", DOC_NOT_PUBLIC)
        if not hop_allowed(url):
            log.info("doc_import: %s redirected off Google Docs to %s", found_id, url[:120])
            raise DocImportError(502, "doc_redirect_refused", DOC_WENT_ELSEWHERE)
        hop = await get(url, seconds=TIMEOUT_SECONDS, limit=MAX_BYTES)
        if hop.status in REDIRECTS:
            if not hop.location:
                raise DocImportError(502, "doc_unreachable", DOC_UNREACHABLE)
            url = urljoin(url, hop.location)
            continue
        if hop.status in NOT_ALLOWED:
            raise DocImportError(409, "doc_not_public", DOC_NOT_PUBLIC)
        if hop.status in MISSING:
            raise _missing(source)
        if hop.status != 200:
            log.info("doc_import: %s answered %s", found_id, hop.status)
            raise DocImportError(502, "doc_unreachable", DOC_UNREACHABLE)
        if hop.too_big:
            raise DocImportError(413, "doc_too_big", DOC_TOO_BIG)
        if "text/html" not in str(hop.content_type or "").lower():
            raise DocImportError(422, "not_a_google_doc", NOT_A_DOC)
        page = bytes(hop.body).decode("utf-8", errors="replace")
        if looks_like_sign_in(page):
            raise DocImportError(409, "doc_not_public", DOC_NOT_PUBLIC)
        return Doc(found_id, page, title_of(page), len(hop.body))
    log.info("doc_import: %s redirected more than %s times", found_id, MAX_HOPS)
    raise DocImportError(502, "doc_unreachable", DOC_UNREACHABLE)


async def fetch_doc(found_id: str, *, source: str = FROM_DOCS, get: Any = None) -> Doc:
    """The export of one public Google Doc; every failure is a DocImportError in words."""
    request = get or aiohttp_hop
    try:
        async with asyncio.timeout(TIMEOUT_SECONDS):
            return await _walk(found_id, source, request)
    except DocImportError:
        raise
    except TimeoutError as exc:
        raise DocImportError(
            504, "doc_timeout", DOC_TIMEOUT.format(seconds=TIMEOUT_SECONDS)
        ) from exc
    except Exception as exc:
        log.info("doc_import: %s could not be fetched: %s", found_id, type(exc).__name__)
        raise DocImportError(502, "doc_unreachable", DOC_UNREACHABLE) from exc


async def import_link(url: Any, *, get: Any = None) -> Doc:
    if not str(url or "").strip():
        raise DocImportError(400, "no_link", NO_LINK)
    found = parse_link(url)
    if found is None:
        raise DocImportError(400, "not_a_google_doc_link", NOT_A_GOOGLE_LINK)
    return await fetch_doc(found[0], source=found[1], get=get)


__all__ = [
    "DOC_NOT_FOUND",
    "DOC_NOT_PUBLIC",
    "DOC_TIMEOUT",
    "DOC_TOO_BIG",
    "DOC_UNREACHABLE",
    "DOC_WENT_ELSEWHERE",
    "EXPORT_URL",
    "IMPORTED",
    "MAX_BYTES",
    "NOT_A_DOC",
    "NOT_A_GOOGLE_LINK",
    "NO_LINK",
    "TIMEOUT_SECONDS",
    "Doc",
    "DocImportError",
    "Hop",
    "aiohttp_hop",
    "doc_id",
    "export_url",
    "fetch_doc",
    "hop_allowed",
    "import_link",
    "parse_link",
]
