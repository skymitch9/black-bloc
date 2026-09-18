from __future__ import annotations

from types import SimpleNamespace

import pytest

from black_bloc.youtube import (
    BACK,
    LINK,
    LINK_FOR,
    LOGS,
    NOBODY_LINKED,
    PANEL_MINUTES_KEY,
    PANEL_MOVES,
    PANEL_TIMEOUT_FOOTER,
    REFRESH,
    REFRESH_MOVE,
    RELINK,
    RELINK_FOR,
    UNLINK,
    UNLINK_FOR,
    YouTubeClient,
    YouTubeError,
    card_buttons,
    channel_id_in,
    handle_in,
    health_lines,
    link_lines,
    panel_minutes,
    status_lines,
    title_of,
    where_words,
)

CHANNEL = "UCsXVk37bltHxD1rDPwtNM8Q"
OTHER = "UC_x5XG1OV2P6uZZ5FSM9Ttw"
TITLED = f'{{"items": [{{"id": "{CHANNEL}", "snippet": {{"title": "Kurzgesagt"}}}}]}}'


class _Request:
    """Stands in for the aiohttp call; every reply is (status, headers, body)."""

    def __init__(self, *replies):
        self.replies = list(replies)
        self.calls: list[dict] = []

    async def __call__(self, method, url, *, headers=None, params=None):
        self.calls.append(
            {"method": method, "url": url, "headers": headers or {}, "params": params or {}}
        )
        return self.replies.pop(0) if self.replies else (500, {}, "")


def ok(body="", headers=None):
    return (200, headers or {}, body)


# --- what a channel reference can be ---------------------------------------------------------


@pytest.mark.parametrize(
    "given",
    [CHANNEL, f"https://www.youtube.com/channel/{CHANNEL}", f"  youtube.com/channel/{CHANNEL}  "],
)
def test_a_channel_id_is_found_without_asking_youtube_anything(given):
    assert channel_id_in(given) == CHANNEL


@pytest.mark.parametrize("given", ["@kurzgesagt", "kurzgesagt", "", "UCtooshort", None])
def test_a_handle_is_not_a_channel_id(given):
    assert channel_id_in(given) is None


@pytest.mark.parametrize(
    ("given", "handle"),
    [
        ("@kurzgesagt", "kurzgesagt"),
        ("kurzgesagt", "kurzgesagt"),
        ("https://www.youtube.com/@kurzgesagt", "kurzgesagt"),
        ("https://www.youtube.com/c/kurzgesagt", "kurzgesagt"),
        ("https://www.youtube.com/user/kurzgesagt", "kurzgesagt"),
    ],
)
def test_a_handle_is_read_out_of_every_address_shape(given, handle):
    assert handle_in(given) == handle


def test_something_that_is_neither_is_refused_rather_than_guessed():
    assert handle_in("https://example.com/somebody") is None
    assert handle_in("two words") is None


# --- resolving --------------------------------------------------------------------------------


async def test_a_channel_id_with_no_key_resolves_to_itself_and_asks_youtube_nothing():
    """The uploads feed was where a title came from; without a key there is nowhere left."""
    request = _Request()
    client = YouTubeClient(None, request=request)

    channel_id, title = await client.resolve(f"https://www.youtube.com/channel/{CHANNEL}")

    assert (channel_id, title) == (CHANNEL, "")
    assert request.calls == []


async def test_a_channel_id_with_a_key_gets_its_title_from_one_channels_call():
    request = _Request(ok(TITLED))
    client = YouTubeClient("k-e-y", request=request)

    channel_id, title = await client.resolve(CHANNEL)

    assert (channel_id, title) == (CHANNEL, "Kurzgesagt")
    assert request.calls[0]["url"].endswith("/channels")
    assert request.calls[0]["params"]["id"] == CHANNEL


async def test_a_title_the_api_refuses_is_blank_rather_than_a_failed_link():
    client = YouTubeClient("k-e-y", request=_Request((403, {}, "{}")))

    channel_id, title = await client.resolve(CHANNEL)

    assert (channel_id, title) == (CHANNEL, "")


def test_a_channels_answer_that_is_not_one_reads_as_no_title_at_all():
    assert title_of(None) == ""
    assert title_of({}) == ""
    assert title_of({"items": [{"snippet": {}}]}) == ""
    assert title_of({"items": [{"snippet": {"title": "Kurzgesagt"}}]}) == "Kurzgesagt"


async def test_a_handle_resolves_off_the_pages_canonical_link_not_its_channelId_fields():
    """Measured 2026-09-02: the page's "channelId":"UC…" hits are OTHER channels, or absent."""
    page = (
        '<html><script>{"channelId":"UCwrongwrongwrongwrong11"}</script>'
        f'<link rel="canonical" href="https://www.youtube.com/channel/{CHANNEL}">'
        "</html>"
    )
    client = YouTubeClient(None, request=_Request(ok(page)))

    channel_id, title = await client.resolve("@kurzgesagt")

    assert (channel_id, title) == (CHANNEL, "")


async def test_a_handle_page_with_no_canonical_refuses_with_the_sentence_that_says_what_to_paste():
    client = YouTubeClient(None, request=_Request(ok("<html>nothing here</html>")))

    with pytest.raises(YouTubeError) as caught:
        await client.resolve("@nobodyhome")

    said = str(caught.value)
    assert "youtube.com/channel/UC" in said
    assert "API key" in said


async def test_the_handle_page_is_asked_with_a_browser_agent():
    request = _Request(ok("<html>nothing here</html>"))
    client = YouTubeClient(None, request=request)

    with pytest.raises(YouTubeError):
        await client.resolve("@nobodyhome")

    assert "BlackBloc" in request.calls[0]["headers"]["User-Agent"]


async def test_something_that_is_no_kind_of_channel_is_refused_before_any_request():
    request = _Request()
    client = YouTubeClient(None, request=request)

    with pytest.raises(YouTubeError, match="could not turn"):
        await client.resolve("https://example.com/not-youtube")

    assert request.calls == []


async def test_a_key_resolves_a_handle_through_the_api_first():
    request = _Request(ok(TITLED))
    client = YouTubeClient("k-e-y", request=request)

    channel_id, title = await client.resolve("@kurzgesagt")

    assert (channel_id, title) == (CHANNEL, "Kurzgesagt")
    assert request.calls[0]["params"]["forHandle"] == "@kurzgesagt"
    assert request.calls[0]["params"]["key"] == "k-e-y"


async def test_a_key_that_finds_nothing_falls_back_to_the_channel_page():
    page = f'<link rel="canonical" href="https://www.youtube.com/channel/{OTHER}">'
    client = YouTubeClient("k-e-y", request=_Request(ok("{}"), ok("{}"), ok(page), ok("{}")))

    channel_id, _title = await client.resolve("@somebody")

    assert channel_id == OTHER


async def test_an_api_refusal_is_a_youtube_error_carrying_what_google_said():
    body = '{"error": {"message": "The request cannot be completed because you have exceeded."}}'
    client = YouTubeClient("k-e-y", request=_Request((403, {}, body)))

    with pytest.raises(YouTubeError, match="exceeded"):
        await client.search_live(CHANNEL)


async def test_the_live_search_asks_for_one_live_video_on_that_channel_and_nothing_else():
    """100 units: the one call that finds the id the bot-check page will not carry."""
    request = _Request(ok('{"items": [{"id": {"videoId": "ZZZZZZZZZZZ"}}]}'))
    client = YouTubeClient("k-e-y", request=request)

    assert await client.search_live(CHANNEL) == "ZZZZZZZZZZZ"
    params = request.calls[0]["params"]
    assert params["channelId"] == CHANNEL and params["eventType"] == "live"
    assert params["type"] == "video" and params["part"] == "id" and params["maxResults"] == "1"
    assert request.calls[0]["url"].endswith("/search")


async def test_the_live_search_asks_nothing_without_a_key_or_a_channel():
    request = _Request()
    keyless = YouTubeClient(None, request=request)
    keyed = YouTubeClient("k-e-y", request=request)

    assert await keyless.search_live(CHANNEL) is None
    assert await keyed.search_live("") is None
    assert request.calls == []


# --- the panel's table, as data ------------------------------------------------------------------


@pytest.mark.parametrize("mine", [True, False])
@pytest.mark.parametrize("linked", [True, False])
@pytest.mark.parametrize("staff", [True, False])
def test_the_button_table_offers_a_refresh_from_every_state(mine, linked, staff):
    found = card_buttons(linked=linked, mine=mine, staff=staff)

    assert REFRESH_MOVE in found
    assert len(found) == len(set(found))


def test_my_card_offers_link_when_there_is_nothing_linked_and_never_an_unlink():
    found = card_buttons(linked=False, mine=True, staff=False)

    assert [move.action for move in found] == [LINK, REFRESH]


def test_my_card_offers_relink_and_unlink_once_a_channel_is_linked():
    found = card_buttons(linked=True, mine=True, staff=False)

    assert [move.action for move in found] == [RELINK, UNLINK, REFRESH]


def test_staff_get_the_two_extra_moves_only_on_their_own_card():
    """The Setup sub-panel went with the uploads half; what is left is the pair."""
    own = [move.action for move in card_buttons(linked=True, mine=True, staff=True)]
    theirs = [move.action for move in card_buttons(linked=True, mine=False, staff=True)]

    assert own[-2:] == [LINK_FOR, LOGS]
    assert LOGS not in theirs
    assert theirs == [RELINK_FOR, UNLINK_FOR, REFRESH, BACK]


def test_no_move_in_the_table_opens_an_uploads_setup_panel_any_more():
    assert "setup" not in {move.action for move in PANEL_MOVES}


def test_a_card_for_somebody_with_nothing_linked_still_offers_a_way_back():
    found = [move.action for move in card_buttons(linked=False, mine=False, staff=True)]

    assert found == [REFRESH, BACK]


def test_a_member_is_never_offered_a_move_that_writes_for_somebody_else():
    for linked in (True, False):
        found = card_buttons(linked=linked, mine=True, staff=False)
        assert not {move.action for move in found} & {LINK_FOR, LOGS, UNLINK_FOR}


def test_only_the_unlink_asks_first_and_only_the_link_moves_open_a_modal():
    asking = [move.action for move in PANEL_MOVES if move.question]
    modal = [move.action for move in PANEL_MOVES if move.modal]

    assert asking == [UNLINK]
    assert modal == [LINK, RELINK, RELINK_FOR, UNLINK_FOR]


def test_every_move_in_the_table_has_a_style_the_panel_knows():
    assert {move.style for move in PANEL_MOVES} <= {"primary", "secondary", "success", "danger"}


# --- the lines the panel prints -------------------------------------------------------------------


def _link_row(**overrides):
    row = {
        "title": "Kurzgesagt",
        "channel_id": "UC123",
        "linked_at": "2026-09-01T00:00:00+00:00",
        "user_id": 900,
    }
    return row | overrides


def test_the_status_lines_are_the_channel_when_it_was_linked_and_where_it_is_announced():
    lines = status_lines(_link_row(), where="yes, in <#5>")

    assert lines == [
        "**channel** — Kurzgesagt",
        "**linked** — 2026-09-01T00:00:00+00:00",
        "**announced here** — yes, in <#5>",
    ]


def test_a_channel_with_no_title_falls_back_to_its_id_rather_than_a_blank():
    lines = status_lines(_link_row(title=None), where="x")

    assert lines[0] == "**channel** — UC123"


@pytest.mark.parametrize("mode", ["off", "shadow"])
def test_where_words_explains_the_live_mode_rather_than_saying_a_bare_no(mode):
    said = where_words(mode, "on", 5)

    assert said.startswith("no —")
    assert f"**{mode}**" in said


def test_where_words_with_no_golive_channel_names_the_panel_that_sets_it():
    said = where_words("on", "on", None)

    assert "Setup" in said
    assert "/golive" in said


def test_where_words_says_so_when_go_live_itself_is_not_on():
    said = where_words("on", "shadow", 5)

    assert said.startswith("no —")
    assert "**shadow**" in said


def test_where_words_on_with_a_channel_names_the_channel():
    assert where_words("on", "on", 5) == "yes, in <#5>"


def test_the_health_lines_are_the_key_the_link_count_and_the_live_half():
    lines = health_lines(keyed=False, links=2, live=None)

    assert lines == ["**api key** — not set (the live page alone)", "**links** — 2"]


def test_a_key_that_is_set_says_so_and_the_live_lines_follow_the_two():
    lines = health_lines(
        keyed=True,
        links=1,
        live={"mode": "on", "minutes": 5, "probed": 3, "quota": 101, "reading_live": 1},
    )

    assert lines[0] == "**api key** — set"
    assert lines[1] == "**links** — 1"
    assert lines[2] == "**live streams** — on"
    assert lines[-1] == "**quota used today** — 101 unit(s)"


def test_nothing_in_the_health_lines_mentions_a_sweep_or_an_upload_any_more():
    said = " ".join(
        health_lines(
            keyed=False,
            links=0,
            live={"mode": "off", "minutes": 5, "probed": 0, "quota": 0, "reading_live": 0},
        )
    ).lower()

    assert "sweep" not in said
    assert "upload" not in said


def test_the_link_lines_name_the_member_when_the_bot_can_see_them():
    lines = link_lines([_link_row(), _link_row(user_id=901)], {900: "Casey"})

    assert lines[0] == "• Casey — Kurzgesagt"
    assert lines[1] == "• 901 — Kurzgesagt"


def test_nobody_linked_is_a_sentence_not_an_empty_list():
    assert link_lines([], {}) == [NOBODY_LINKED]


def test_the_panel_minutes_come_from_the_key_the_settings_page_edits():
    store = SimpleNamespace(get=lambda guild_id, key: 4 if key == PANEL_MINUTES_KEY else 99)

    assert panel_minutes(store, 7) == 4


def test_the_gone_quiet_footer_names_the_command_that_opens_the_panel_again():
    assert "/youtube" in PANEL_TIMEOUT_FOOTER


# --- an outage and a bad paste are different things -----------------------------------------------


def test_an_error_says_at_the_raise_site_whether_it_was_the_network():
    assert YouTubeError("bad paste").network is False
    assert YouTubeError("down", network=True).network is True


async def test_a_live_page_that_refuses_raises_a_network_error():
    client = YouTubeClient(None, request=_Request((500, {}, "")))

    with pytest.raises(YouTubeError) as raised:
        await client.probe_live("UC123")

    assert raised.value.network is True


async def test_a_paste_that_is_not_a_channel_is_not_a_network_error():
    client = YouTubeClient(None, request=_Request((200, {}, "")))

    with pytest.raises(YouTubeError) as raised:
        await client.resolve("not a channel at all/nor this")

    assert raised.value.network is False


# --- what the uploads half left behind ------------------------------------------------------------


def test_the_feed_parser_and_the_upload_wording_are_gone_from_the_module():
    import black_bloc.youtube as module

    for name in ("FEED_URL", "parse_feed", "feed_title", "render", "Video", "classify_row"):
        assert not hasattr(module, name), name
    assert not hasattr(YouTubeClient, "fetch_feed")
    assert not hasattr(YouTubeClient, "classify")
