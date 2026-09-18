from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from black_bloc.settings_store import YOUTUBE_TEMPLATE
from black_bloc.youtube import (
    BACK,
    FEED_ATTEMPTS,
    LINK,
    LINK_FOR,
    LIVE,
    LOGS,
    NOBODY_LINKED,
    NOT_SEEDED_YET,
    PANEL_MINUTES_KEY,
    PANEL_MOVES,
    PANEL_TIMEOUT_FOOTER,
    REFRESH,
    REFRESH_MOVE,
    RELINK,
    RELINK_FOR,
    SETUP,
    SHORT,
    UNKNOWN,
    UNLINK,
    UNLINK_FOR,
    VIDEO,
    YouTubeClient,
    YouTubeError,
    card_buttons,
    channel_id_in,
    classify_row,
    duration_seconds,
    feed_title,
    handle_in,
    health_lines,
    kind_of,
    link_lines,
    panel_minutes,
    parse_feed,
    render,
    status_lines,
    where_words,
)

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "youtube_feed.xml"
FEED = FIXTURE.read_text(encoding="utf-8")
CHANNEL = "UCsXVk37bltHxD1rDPwtNM8Q"
OTHER = "UC_x5XG1OV2P6uZZ5FSM9Ttw"


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


def ok(body=FEED, headers=None):
    return (200, headers or {}, body)


# --- parsing, against the real captured feed -------------------------------------------------


def test_the_captured_feed_parses_into_its_fifteen_trimmed_entries():
    videos = parse_feed(FEED)

    assert len(videos) == 5
    first = videos[0]
    assert first.video_id == "tZ8i1RxGSYM"
    assert first.title == "Can Earth Run Out of Water?"
    assert first.url == "https://www.youtube.com/shorts/tZ8i1RxGSYM"
    assert first.published == "2026-08-31T14:00:04+00:00"
    assert first.author.startswith("Kurzgesagt")


def test_the_entry_channel_id_is_used_because_the_feed_level_one_drops_its_UC():
    """Measured 2026-09-02: <feed><yt:channelId> reads sXVk…, only the entry carries UCsXVk…."""
    videos = parse_feed(FEED)

    assert all(video.channel_id == CHANNEL for video in videos)
    assert "<yt:channelId>sXVk37bltHxD1rDPwtNM8Q</yt:channelId>" in FEED


def test_shorts_are_told_apart_from_videos_by_the_link_alone():
    """Measured 2026-09-02: the feed links a Short as /shorts/<id>, so no API key is needed."""
    kinds = {video.video_id: video.kind for video in parse_feed(FEED)}

    assert kinds["tZ8i1RxGSYM"] == SHORT
    assert kinds["Cyl3X88KEgg"] == VIDEO
    assert [video.kind for video in parse_feed(FEED)].count(SHORT) == 3


def test_kind_of_reads_the_path_and_defaults_to_video():
    assert kind_of("https://www.youtube.com/shorts/abc") == SHORT
    assert kind_of("https://www.youtube.com/watch?v=abc") == VIDEO
    assert kind_of(None) == VIDEO


def test_an_entry_with_no_video_id_is_dropped_rather_than_half_parsed():
    body = FEED.replace("<yt:videoId>tZ8i1RxGSYM</yt:videoId>", "")

    videos = parse_feed(body)

    assert len(videos) == 4
    assert "tZ8i1RxGSYM" not in [video.video_id for video in videos]


def test_a_missing_title_or_author_is_empty_not_an_error():
    body = FEED.replace("<title>Can Earth Run Out of Water?</title>", "")

    first = parse_feed(body)[0]

    assert first.title == ""
    assert first.video_id == "tZ8i1RxGSYM"


def test_an_entry_with_no_link_falls_back_to_the_watch_address():
    link = '<link rel="alternate" href="https://www.youtube.com/shorts/tZ8i1RxGSYM"/>'
    body = FEED.replace(link, "")

    first = parse_feed(body)[0]

    assert first.url == "https://www.youtube.com/watch?v=tZ8i1RxGSYM"
    assert first.kind == VIDEO


def test_empty_and_blank_feeds_are_no_videos_not_a_crash():
    assert parse_feed("") == []
    assert parse_feed("   ") == []
    assert parse_feed(b"") == []


def test_unreadable_xml_is_a_youtube_error_in_words():
    with pytest.raises(YouTubeError, match="not readable XML"):
        parse_feed("<feed><entry>")


def test_bytes_are_decoded_the_same_way_text_is():
    assert parse_feed(FEED.encode("utf-8")) == parse_feed(FEED)


def test_the_feed_title_is_the_channel_name():
    assert feed_title(FEED).startswith("Kurzgesagt")
    assert feed_title("<not xml") == ""


# --- durations and classification ------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "seconds"),
    [
        ("PT45S", 45),
        ("PT1M", 60),
        ("PT1M1S", 61),
        ("PT2H3M4S", 7384),
        ("P1DT2H", 93600),
        ("nonsense", None),
        (None, None),
    ],
)
def test_durations_are_read_or_refused(text, seconds):
    assert duration_seconds(text) == seconds


def test_a_live_row_is_live_whatever_its_length_says():
    row = {
        "liveStreamingDetails": {"actualStartTime": "x"},
        "contentDetails": {"duration": "PT30S"},
    }

    assert classify_row(row) == LIVE


def test_a_minute_or_less_is_a_short_and_a_second_more_is_a_video():
    assert classify_row({"contentDetails": {"duration": "PT60S"}}) == SHORT
    assert classify_row({"contentDetails": {"duration": "PT61S"}}) == VIDEO


def test_a_row_with_no_readable_length_is_unknown_never_guessed():
    assert classify_row({}) == UNKNOWN
    assert classify_row({"contentDetails": {"duration": "???"}}) == UNKNOWN


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


# --- fetching, and the flakiness measured on 2026-09-02 --------------------------------------


async def test_a_two_hundred_answers_the_videos_and_whatever_etag_came_with_it():
    request = _Request(ok(headers={"ETag": "W/abc"}))
    client = YouTubeClient(None, request=request)

    status, etag, videos = await client.fetch_feed(CHANNEL)

    assert status == 200
    assert etag == "W/abc"
    assert len(videos) == 5
    assert request.calls[0]["params"] == {"channel_id": CHANNEL}


async def test_the_real_feed_sends_no_etag_so_none_is_carried_forward():
    """Measured 2026-09-02: the live feed sends neither ETag nor Last-Modified."""
    client = YouTubeClient(None, request=_Request(ok()))

    _status, etag, _videos = await client.fetch_feed(CHANNEL)

    assert etag is None


async def test_a_stored_etag_is_offered_and_a_304_means_nothing_changed():
    request = _Request((304, {}, ""))
    client = YouTubeClient(None, request=request)

    status, etag, videos = await client.fetch_feed(CHANNEL, "W/abc")

    assert (status, etag, videos) == (304, "W/abc", [])
    assert request.calls[0]["headers"]["If-None-Match"] == "W/abc"


async def test_a_404_is_retried_because_the_feed_404s_about_half_the_time():
    """Measured 2026-09-02: 15/30 200s, 12/30 404s, 3/30 500s on a channel that plainly exists."""
    request = _Request((404, {}, ""), (500, {}, ""), (404, {}, ""), ok())
    client = YouTubeClient(None, request=request)

    status, _etag, videos = await client.fetch_feed(CHANNEL)

    assert status == 200
    assert len(videos) == 5
    assert len(request.calls) == FEED_ATTEMPTS


async def test_a_feed_that_never_answers_refuses_in_words_and_never_says_the_channel_is_gone():
    request = _Request(*[(404, {}, "")] * FEED_ATTEMPTS)
    client = YouTubeClient(None, request=request)

    with pytest.raises(YouTubeError) as caught:
        await client.fetch_feed(CHANNEL)

    said = str(caught.value)
    assert "flaky" in said and "try again" in said
    assert "does not exist" not in said and "wrong" not in said.replace("being wrong", "")


async def test_the_feed_is_asked_with_a_browser_agent():
    request = _Request(ok())
    client = YouTubeClient(None, request=request)

    await client.fetch_feed(CHANNEL)

    assert "BlackBloc" in request.calls[0]["headers"]["User-Agent"]


# --- resolving --------------------------------------------------------------------------------


async def test_a_channel_id_resolves_without_reaching_for_a_handle_page():
    request = _Request(ok())
    client = YouTubeClient(None, request=request)

    channel_id, title = await client.resolve(f"https://www.youtube.com/channel/{CHANNEL}")

    assert channel_id == CHANNEL
    assert title.startswith("Kurzgesagt")
    assert all("/@" not in call["url"] for call in request.calls)


async def test_a_handle_resolves_off_the_pages_canonical_link_not_its_channelId_fields():
    """Measured 2026-09-02: the page's "channelId":"UC…" hits are OTHER channels, or absent."""
    page = (
        '<html><script>{"channelId":"UCwrongwrongwrongwrong11"}</script>'
        f'<link rel="canonical" href="https://www.youtube.com/channel/{CHANNEL}">'
        "</html>"
    )
    client = YouTubeClient(None, request=_Request(ok(page), ok()))

    channel_id, title = await client.resolve("@kurzgesagt")

    assert channel_id == CHANNEL
    assert title.startswith("Kurzgesagt")


async def test_a_handle_page_with_no_canonical_refuses_with_the_sentence_that_says_what_to_paste():
    client = YouTubeClient(None, request=_Request(ok("<html>nothing here</html>")))

    with pytest.raises(YouTubeError) as caught:
        await client.resolve("@nobodyhome")

    said = str(caught.value)
    assert "youtube.com/channel/UC" in said
    assert "API key" in said


async def test_something_that_is_no_kind_of_channel_is_refused_before_any_request():
    request = _Request()
    client = YouTubeClient(None, request=request)

    with pytest.raises(YouTubeError, match="could not turn"):
        await client.resolve("https://example.com/not-youtube")

    assert request.calls == []


async def test_a_title_that_cannot_be_fetched_is_blank_rather_than_a_failed_link():
    client = YouTubeClient(None, request=_Request(*[(404, {}, "")] * FEED_ATTEMPTS))

    channel_id, title = await client.resolve(CHANNEL)

    assert (channel_id, title) == (CHANNEL, "")


async def test_a_key_resolves_a_handle_through_the_api_first():
    payload = f'{{"items": [{{"id": "{CHANNEL}", "snippet": {{"title": "Kurzgesagt"}}}}]}}'
    request = _Request(ok(payload), ok())
    client = YouTubeClient("k-e-y", request=request)

    channel_id, title = await client.resolve("@kurzgesagt")

    assert (channel_id, title) == (CHANNEL, "Kurzgesagt")
    assert request.calls[0]["params"]["forHandle"] == "@kurzgesagt"
    assert request.calls[0]["params"]["key"] == "k-e-y"


async def test_a_key_that_finds_nothing_falls_back_to_the_channel_page():
    page = f'<link rel="canonical" href="https://www.youtube.com/channel/{OTHER}">'
    client = YouTubeClient("k-e-y", request=_Request(ok("{}"), ok("{}"), ok(page), ok()))

    channel_id, _title = await client.resolve("@somebody")

    assert channel_id == OTHER


# --- classifying with a key -------------------------------------------------------------------


async def test_without_a_key_nothing_is_classified_and_nothing_is_claimed():
    request = _Request()
    client = YouTubeClient(None, request=request)

    assert await client.classify(["a", "b"]) == {}
    assert request.calls == []


async def test_with_a_key_each_id_comes_back_with_a_kind():
    payload = (
        '{"items": ['
        '{"id": "a", "contentDetails": {"duration": "PT30S"}},'
        '{"id": "b", "contentDetails": {"duration": "PT10M"}},'
        '{"id": "c", "liveStreamingDetails": {"actualStartTime": "x"},'
        ' "contentDetails": {"duration": "PT2H"}}'
        "]}"
    )
    request = _Request(ok(payload))
    client = YouTubeClient("k-e-y", request=request)

    assert await client.classify(["a", "b", "c"]) == {"a": SHORT, "b": VIDEO, "c": LIVE}
    assert request.calls[0]["params"]["id"] == "a,b,c"


async def test_an_api_refusal_is_a_youtube_error_carrying_what_google_said():
    body = '{"error": {"message": "The request cannot be completed because you have exceeded."}}'
    client = YouTubeClient("k-e-y", request=_Request((403, {}, body)))

    with pytest.raises(YouTubeError, match="exceeded"):
        await client.classify(["a"])


async def test_an_empty_id_list_asks_nothing():
    request = _Request()
    client = YouTubeClient("k-e-y", request=request)

    assert await client.classify([]) == {}
    assert request.calls == []


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


# --- rendering ---------------------------------------------------------------------------------


def _video(**over):
    fields = {
        "video_id": "abc",
        "title": "Can Earth Run Out of Water?",
        "url": "https://www.youtube.com/watch?v=abc",
        "author": "Kurzgesagt",
        "kind": VIDEO,
    }
    from black_bloc.youtube import Video

    return Video(**(fields | over))


def test_the_default_wording_names_the_member_the_title_and_the_link():
    text = render(YOUTUBE_TEMPLATE, _video(), SimpleNamespace(display_name="Casey"))

    assert text == (
        "**Casey** just dropped a new video: **Can Earth Run Out of Water?** "
        "https://www.youtube.com/watch?v=abc"
    )


def test_a_missing_title_reads_as_a_new_video_never_as_empty_bold():
    text = render(YOUTUBE_TEMPLATE, _video(title=""), SimpleNamespace(display_name="Casey"))

    assert "****" not in text
    assert "a new video" in text


def test_the_ping_roles_go_in_front_in_the_order_they_were_given():
    text = render(
        YOUTUBE_TEMPLATE,
        _video(),
        SimpleNamespace(display_name="Casey"),
        ping_role_id=11,
        fan_role_id=22,
    )

    assert text.startswith("<@&11> <@&22> ")


def test_the_same_role_twice_is_mentioned_once():
    text = render(
        YOUTUBE_TEMPLATE, _video(), SimpleNamespace(display_name="C"), ping_role_id=7, fan_role_id=7
    )

    assert text.startswith("<@&7> ")
    assert text.count("<@&7>") == 1


def test_a_template_naming_a_field_that_does_not_exist_keeps_the_placeholder_visible():
    text = render("{name} posted {nonsense}", _video(), SimpleNamespace(display_name="Casey"))

    assert text == "Casey posted {nonsense}"


def test_a_broken_template_falls_back_to_the_default_rather_than_posting_nothing(caplog):
    text = render("{name} posted {", _video(), SimpleNamespace(display_name="Casey"))

    assert text.startswith("**Casey** just dropped")
    assert "using the default" in caplog.text


def test_a_member_the_bot_cannot_name_still_reads_as_somebody():
    assert render(YOUTUBE_TEMPLATE, _video(), None).startswith("**Someone**")


def test_the_channel_and_kind_fields_are_offered_to_a_staff_written_template():
    text = render("{channel} put out a {kind}", _video(kind=SHORT), None)

    assert text == "Kurzgesagt put out a short"


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


def test_staff_get_the_three_extra_moves_only_on_their_own_card():
    own = [move.action for move in card_buttons(linked=True, mine=True, staff=True)]
    theirs = [move.action for move in card_buttons(linked=True, mine=False, staff=True)]

    assert own[-3:] == [LINK_FOR, SETUP, LOGS]
    assert LOGS not in theirs
    assert theirs == [RELINK_FOR, UNLINK_FOR, REFRESH, BACK]


def test_a_card_for_somebody_with_nothing_linked_still_offers_a_way_back():
    found = [move.action for move in card_buttons(linked=False, mine=False, staff=True)]

    assert found == [REFRESH, BACK]


def test_a_member_is_never_offered_a_move_that_writes_for_somebody_else():
    for linked in (True, False):
        found = card_buttons(linked=linked, mine=True, staff=False)
        assert not {move.action for move in found} & {LINK_FOR, SETUP, LOGS, UNLINK_FOR}


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
        "seeded": 1,
        "user_id": 900,
    }
    return row | overrides


def test_the_status_lines_are_the_five_a_member_used_to_get_from_a_subcommand():
    lines = status_lines(_link_row(), "A video", where="yes, in <#5>", shorts=False)

    assert lines[0] == "**channel** — Kurzgesagt"
    assert lines[2] == "**last video seen** — A video"
    assert lines[3] == "**announced here** — yes, in <#5>"
    assert lines[4] == "**Shorts** — not announced"


def test_a_link_whose_feed_has_not_answered_says_so_rather_than_none_yet():
    unseeded = status_lines(_link_row(seeded=0), None, where="x", shorts=True)
    seeded = status_lines(_link_row(), None, where="x", shorts=True)

    assert NOT_SEEDED_YET in unseeded[2]
    assert "none yet" in seeded[2]
    assert seeded[4] == "**Shorts** — announced too"


def test_a_channel_with_no_title_falls_back_to_its_id_rather_than_a_blank():
    lines = status_lines(_link_row(title=None), None, where="x", shorts=False)

    assert lines[0] == "**channel** — UC123"


@pytest.mark.parametrize("mode", ["off", "shadow"])
def test_where_words_explains_the_mode_rather_than_saying_a_bare_no(mode):
    said = where_words(mode, 5)

    assert said.startswith("no —")
    assert f"**{mode}**" in said


def test_where_words_with_nowhere_set_names_the_panel_that_sets_it():
    said = where_words("on", None)

    assert "Setup" in said
    assert "/uploads" not in said


def test_where_words_on_with_a_channel_names_the_channel():
    assert where_words("on", 5) == "yes, in <#5>"


def test_the_health_lines_are_the_seven_the_staff_list_used_to_print():
    lines = health_lines(
        mode="shadow",
        channel_id=None,
        minutes=10,
        keyed=False,
        last_ok_at=None,
        last_error=None,
        failures=0,
        totals={"links": 2, "videos": 9, "announced": 1},
    )

    assert len(lines) == 7
    assert lines[0] == "**mode** — shadow"
    assert lines[1] == "**channel** — not set"
    assert lines[3] == "**api key** — not set (feed only)"
    assert lines[4] == "**last good sweep** — never"
    assert lines[5] == "**last error** — none"
    assert "**links** — 2" in lines[6]


def test_a_run_of_failures_is_counted_beside_the_error_rather_than_hidden():
    lines = health_lines(
        mode="on",
        channel_id=7,
        minutes=5,
        keyed=True,
        last_ok_at="then",
        last_error="youtube unreachable",
        failures=3,
        totals={"links": 0, "videos": 0, "announced": 0},
    )

    assert lines[1] == "**channel** — <#7>"
    assert lines[3] == "**api key** — set"
    assert lines[5] == "**last error** — youtube unreachable (3 sweep(s) in a row)"


def test_the_link_lines_name_the_member_when_the_bot_can_see_them():
    lines = link_lines([_link_row(), _link_row(user_id=901, seeded=0)], {900: "Casey"})

    assert lines[0] == "• Casey — Kurzgesagt (seeded)"
    assert lines[1] == f"• 901 — Kurzgesagt ({NOT_SEEDED_YET})"


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


async def test_a_feed_that_never_answers_raises_a_network_error(monkeypatch):
    client = YouTubeClient(
        None, request=_Request((500, {}, ""), (500, {}, ""), (500, {}, ""), (500, {}, ""))
    )

    with pytest.raises(YouTubeError) as raised:
        await client.fetch_feed("UC123")

    assert raised.value.network is True


async def test_a_paste_that_is_not_a_channel_is_not_a_network_error():
    client = YouTubeClient(None, request=_Request((200, {}, "")))

    with pytest.raises(YouTubeError) as raised:
        await client.resolve("not a channel at all/nor this")

    assert raised.value.network is False
