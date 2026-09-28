from __future__ import annotations

import asyncio

import aiohttp
import pytest

from black_bloc import doc_import
from black_bloc.doc_import import DocImportError, Hop

DOC = "1AbCdEfGhIjKlMnOpQrStUvWxYz_0123456789-xy"
EXPORT = doc_import.EXPORT_URL.format(id=DOC)
REAL_HOP = doc_import.aiohttp_hop
PAGE = (
    '<html><head><meta content="text/html; charset=UTF-8" http-equiv="content-type">'
    '<style type="text/css">.c1{font-weight:700}</style><title>Welcome &amp; rules</title>'
    '</head><body class="c3 doc-content"><p class="c2"><span class="c1">Hi</span></p></body></html>'
)
SIGN_IN_PAGE = (
    "<html><body><form action=\"https://accounts.google.com/v3/signin/identifier\">"
    "<input name=identifier></form></body></html>"
)


class Fake:
    """Answers by URL and remembers every URL it was asked for."""

    def __init__(self, answers):
        self.answers = answers
        self.asked: list[str] = []

    async def __call__(self, url, *, seconds, limit):
        self.asked.append(url)
        found = self.answers.get(url)
        if found is None:
            raise AssertionError(f"the fetch asked for {url}, which no test offered")
        if isinstance(found, BaseException):
            raise found
        return found


def page(body=PAGE, kind="text/html; charset=utf-8"):
    return Hop(200, None, kind, body.encode("utf-8"))


@pytest.mark.parametrize(
    "url",
    [
        f"https://docs.google.com/document/d/{DOC}/edit?usp=sharing",
        f"https://docs.google.com/document/d/{DOC}",
        f"https://docs.google.com/document/d/{DOC}/",
        f"https://docs.google.com/document/u/1/d/{DOC}/view#heading=h.x",
        f"http://DOCS.google.com/document/d/{DOC}/edit",
        f"docs.google.com/document/d/{DOC}/edit",
        f"  https://docs.google.com/document/d/{DOC}/edit  ",
        f"https://drive.google.com/file/d/{DOC}/view?usp=drive_link",
        f"https://drive.google.com/open?id={DOC}",
        f"https://drive.google.com/uc?id={DOC}&export=download",
    ],
)
def test_a_google_docs_or_drive_link_gives_its_id(url):
    assert doc_import.doc_id(url) == DOC


@pytest.mark.parametrize(
    "url",
    [
        "",
        None,
        "not a link",
        f"https://evil.example/document/d/{DOC}/edit",
        f"https://docs.google.com.evil.example/document/d/{DOC}/edit",
        f"https://evil.example/docs.google.com/document/d/{DOC}",
        f"https://docs.google.com@evil.example/document/d/{DOC}/edit",
        f"https://user:pw@docs.google.com/document/d/{DOC}/edit",
        f"https://docs.google.com:8443/document/d/{DOC}/edit",
        f"https://docs.google.com/spreadsheets/d/{DOC}/edit",
        f"https://docs.google.com/document/d/{DOC[:19]}/edit",
        "https://docs.google.com/document/d/e/2PACX-short/pub",
        f"https://drive.google.com/drive/folders/{DOC}",
        f"https://drive.google.com/open?id={DOC}&id={DOC}",
        f"ftp://docs.google.com/document/d/{DOC}/edit",
        f"javascript:alert('docs.google.com/document/d/{DOC}')",
        f"https://docs.google.com/document/d/{DOC}/edit x",
        "https://docs.google.com/document/d/" + "a" * 3000,
    ],
)
def test_anything_else_gives_no_id(url):
    assert doc_import.doc_id(url) is None


def test_the_link_says_whether_it_came_from_drive():
    assert doc_import.parse_link(f"https://docs.google.com/document/d/{DOC}/edit") == (
        DOC,
        doc_import.FROM_DOCS,
    )
    assert doc_import.parse_link(f"https://drive.google.com/file/d/{DOC}/view") == (
        DOC,
        doc_import.FROM_DRIVE,
    )


async def test_the_fetch_asks_for_the_export_it_built_never_the_link_it_was_given():
    fake = Fake({EXPORT: page()})

    found = await doc_import.import_link(
        f"https://docs.google.com/document/d/{DOC}/edit?usp=sharing&x=https://evil.example",
        get=fake,
    )

    assert fake.asked == [EXPORT]
    assert found.doc_id == DOC and found.title == "Welcome & rules"
    assert found.html == PAGE and found.size == len(PAGE.encode("utf-8"))


async def test_a_redirect_to_googles_content_host_is_followed():
    there = "https://doc-0s-9c-docs.googleusercontent.com/docs/securesc/abc/export"
    fake = Fake({EXPORT: Hop(307, there), there: page()})

    found = await doc_import.fetch_doc(DOC, get=fake)

    assert fake.asked == [EXPORT, there]
    assert found.title == "Welcome & rules"


async def test_a_relative_redirect_stays_on_docs_and_is_followed():
    there = f"https://docs.google.com/document/d/{DOC}/export?format=html&hl=en"
    fake = Fake({EXPORT: Hop(302, f"/document/d/{DOC}/export?format=html&hl=en"), there: page()})

    found = await doc_import.fetch_doc(DOC, get=fake)

    assert fake.asked == [EXPORT, there] and found.doc_id == DOC


@pytest.mark.parametrize(
    "elsewhere",
    [
        "https://evil.example/steal",
        "https://docs.google.com.evil.example/x",
        "http://docs.google.com/document/d/x/export",
        "https://googleusercontent.com.evil.example/x",
        "https://docs.google.com:8443/x",
        "http://169.254.169.254/latest/meta-data/",
        "https://drive.google.com/uc?id=x",
    ],
)
async def test_a_redirect_off_google_docs_is_never_fetched(elsewhere):
    """The SSRF guard: the only URL a hop may reach is docs.google.com or Google's content host."""
    fake = Fake({EXPORT: Hop(302, elsewhere)})

    with pytest.raises(DocImportError) as refused:
        await doc_import.fetch_doc(DOC, get=fake)

    assert fake.asked == [EXPORT]
    assert refused.value.code == "doc_redirect_refused"
    assert "not the doc's sharing" in refused.value.message


async def test_the_sign_in_wall_is_not_public_and_says_how_to_share_it():
    fake = Fake({EXPORT: Hop(302, "https://accounts.google.com/ServiceLogin?continue=x")})

    with pytest.raises(DocImportError) as refused:
        await doc_import.fetch_doc(DOC, get=fake)

    assert fake.asked == [EXPORT]
    assert (refused.value.status, refused.value.code) == (409, "doc_not_public")
    assert "Anyone with the link" in refused.value.message and "Viewer" in refused.value.message


@pytest.mark.parametrize("status", [401, 403])
async def test_a_refusal_from_google_is_not_public(status):
    with pytest.raises(DocImportError) as refused:
        await doc_import.fetch_doc(DOC, get=Fake({EXPORT: Hop(status)}))

    assert refused.value.code == "doc_not_public" and refused.value.status == 409


async def test_a_sign_in_page_answered_with_200_is_not_public():
    with pytest.raises(DocImportError) as refused:
        await doc_import.fetch_doc(DOC, get=Fake({EXPORT: page(SIGN_IN_PAGE)}))

    assert refused.value.code == "doc_not_public"


async def test_a_doc_that_only_links_to_the_sign_in_page_is_still_a_doc():
    body = PAGE.replace("Hi", '<a href="https://accounts.google.com/signin">sign in</a>')

    found = await doc_import.fetch_doc(DOC, get=Fake({EXPORT: page(body)}))

    assert found.html == body


async def test_a_missing_doc_says_so_in_words():
    with pytest.raises(DocImportError) as refused:
        await doc_import.import_link(
            f"https://docs.google.com/document/d/{DOC}/edit", get=Fake({EXPORT: Hop(404)})
        )

    assert (refused.value.status, refused.value.code) == (404, "doc_not_found")
    assert "Share" not in refused.value.message


async def test_a_drive_file_that_is_not_a_doc_says_only_google_docs_convert():
    with pytest.raises(DocImportError) as refused:
        await doc_import.import_link(
            f"https://drive.google.com/file/d/{DOC}/view", get=Fake({EXPORT: Hop(404)})
        )

    assert refused.value.code == "not_a_google_doc"
    assert "Save as Google Docs" in refused.value.message


async def test_an_export_that_is_not_html_is_not_a_google_doc():
    fake = Fake({EXPORT: Hop(200, None, "application/pdf", b"%PDF-1.7")})

    with pytest.raises(DocImportError) as refused:
        await doc_import.fetch_doc(DOC, get=fake)

    assert refused.value.code == "not_a_google_doc"


async def test_a_page_over_the_cap_is_refused_as_too_big():
    fake = Fake({EXPORT: Hop(200, None, "text/html", b"x" * 10, True)})

    with pytest.raises(DocImportError) as refused:
        await doc_import.fetch_doc(DOC, get=fake)

    assert (refused.value.status, refused.value.code) == (413, "doc_too_big")


@pytest.mark.parametrize(
    "trouble,code",
    [
        (TimeoutError(), "doc_timeout"),
        (OSError("reset"), "doc_unreachable"),
        (RuntimeError("anything"), "doc_unreachable"),
        (DocImportError(502, "doc_unreachable", doc_import.DOC_UNREACHABLE), "doc_unreachable"),
    ],
)
async def test_a_fetch_failure_is_a_fetch_problem_never_an_access_problem(trouble, code):
    """Owner rule: an outage must never be mislabelled as permission."""
    with pytest.raises(DocImportError) as refused:
        await doc_import.fetch_doc(DOC, get=Fake({EXPORT: trouble}))

    assert refused.value.code == code
    assert refused.value.status >= 500
    assert "not a problem with the doc's sharing" in refused.value.message
    assert "Anyone with the link" not in refused.value.message


@pytest.mark.parametrize("status", [500, 503, 429, 204])
async def test_an_odd_answer_from_google_is_a_fetch_problem(status):
    with pytest.raises(DocImportError) as refused:
        await doc_import.fetch_doc(DOC, get=Fake({EXPORT: Hop(status)}))

    assert refused.value.code == "doc_unreachable"


async def test_the_whole_fetch_has_one_deadline(monkeypatch):
    monkeypatch.setattr(doc_import, "TIMEOUT_SECONDS", 0.05)

    async def slow(url, *, seconds, limit):
        await asyncio.sleep(5)

    with pytest.raises(DocImportError) as refused:
        await doc_import.fetch_doc(DOC, get=slow)

    assert refused.value.code == "doc_timeout"


async def test_a_redirect_loop_stops():
    fake = Fake({EXPORT: Hop(302, EXPORT)})

    with pytest.raises(DocImportError) as refused:
        await doc_import.fetch_doc(DOC, get=fake)

    assert refused.value.code == "doc_unreachable"
    assert len(fake.asked) == doc_import.MAX_HOPS + 1


async def test_a_redirect_with_no_location_is_a_fetch_problem():
    with pytest.raises(DocImportError) as refused:
        await doc_import.fetch_doc(DOC, get=Fake({EXPORT: Hop(302, None)}))

    assert refused.value.code == "doc_unreachable"


@pytest.mark.parametrize(
    "url,code",
    [
        ("", "no_link"),
        ("   ", "no_link"),
        ("https://example.com/a-doc", "not_a_google_doc_link"),
    ],
)
async def test_a_bad_link_is_refused_before_anything_is_fetched(url, code):
    fake = Fake({})

    with pytest.raises(DocImportError) as refused:
        await doc_import.import_link(url, get=fake)

    assert fake.asked == []
    assert (refused.value.status, refused.value.code) == (400, code)


def test_the_export_url_refuses_an_id_that_is_not_one():
    with pytest.raises(DocImportError):
        doc_import.export_url("../../evil")
    assert doc_import.export_url(DOC) == EXPORT


def test_the_title_is_read_from_the_head_and_squeezed():
    assert doc_import.title_of("<title>\n  A   doc &amp; more </title>") == "A doc & more"
    assert doc_import.title_of("<p>no title</p>") == ""


class FakeResponse:
    def __init__(self, status, *, headers=None, body=b"", length=None):
        self.status = status
        self.headers = headers or {}
        self.content_length = length
        self._body = body
        self.content = self

    async def read(self, n):
        piece, self._body = self._body[: min(n, 7)], self._body[min(n, 7) :]
        return piece

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class FakeSession:
    seen: list = []

    def __init__(self, *, timeout):
        self.timeout = timeout

    def get(self, url, **kwargs):
        FakeSession.seen.append((url, kwargs))
        return FakeSession.answer(url)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


@pytest.fixture
def session(monkeypatch):
    """The real `aiohttp_hop` over a fake ClientSession, so no socket is ever opened."""
    FakeSession.seen = []
    monkeypatch.setattr(aiohttp, "ClientSession", FakeSession)
    return FakeSession


async def call_real_hop(url, **kw):
    return await REAL_HOP(url, **kw)


async def test_the_real_hop_never_follows_a_redirect_itself(session):
    session.answer = lambda url: FakeResponse(302, headers={"Location": "https://evil.example/"})

    hop = await call_real_hop(EXPORT, seconds=1, limit=100)

    assert (hop.status, hop.location) == (302, "https://evil.example/")
    assert session.seen[0][1]["allow_redirects"] is False


async def test_the_real_hop_reads_one_byte_past_the_cap_and_no_further(session):
    session.answer = lambda url: FakeResponse(
        200, headers={"Content-Type": "text/html"}, body=b"y" * 50
    )

    small = await call_real_hop(EXPORT, seconds=1, limit=100)
    big = await call_real_hop(EXPORT, seconds=1, limit=20)

    assert (small.body, small.too_big) == (b"y" * 50, False)
    assert (len(big.body), big.too_big) == (20, True)


async def test_the_real_hop_trusts_a_content_length_over_the_cap(session):
    session.answer = lambda url: FakeResponse(200, headers={}, body=b"", length=10**9)

    hop = await call_real_hop(EXPORT, seconds=1, limit=100)

    assert hop.too_big is True


@pytest.mark.parametrize(
    "trouble,code",
    [
        (aiohttp.ClientConnectionError("no route"), "doc_unreachable"),
        (TimeoutError(), "doc_timeout"),
        (OSError("reset"), "doc_unreachable"),
    ],
)
async def test_the_real_hop_wraps_transport_errors_in_its_own(session, trouble, code):
    def boom(url):
        raise trouble

    session.answer = boom

    with pytest.raises(DocImportError) as refused:
        await call_real_hop(EXPORT, seconds=1, limit=100)

    assert refused.value.code == code
