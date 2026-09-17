from __future__ import annotations

from pathlib import Path

import pytest

from black_bloc.golive import YOUTUBE
from black_bloc.youtube_live import (
    LIVE_URL,
    Confirm,
    Probe,
    after_probe,
    is_over,
    read_confirm,
    read_page,
    stream_info,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures"
LIVE_PAGE = (FIXTURES / "youtube_live_page.html").read_text(encoding="utf-8")
OFFLINE_PAGE = (FIXTURES / "youtube_not_live_page.html").read_text(encoding="utf-8")
UPCOMING_PAGE = (FIXTURES / "youtube_upcoming_page.html").read_text(encoding="utf-8")
VIDEO = "3PFJ9SETS4M"


# --- the probe parser ---------------------------------------------------------------------------


def test_a_live_page_reads_as_live_with_the_canonical_watch_id():
    found = read_page(LIVE_PAGE)

    assert found == Probe(live=True, upcoming=False, video_id=VIDEO, readable=True)
    assert found.announceable


def test_a_channel_that_is_not_live_reads_as_offline_and_still_readable():
    found = read_page(OFFLINE_PAGE)

    assert found.readable and not found.live and not found.announceable


def test_a_scheduled_stream_is_upcoming_and_is_not_announced():
    found = read_page(UPCOMING_PAGE)

    assert found.upcoming and not found.live and not found.announceable
    assert found.video_id == "abcdefghijk"


def test_a_page_that_is_not_the_shape_this_reads_says_so_rather_than_raising():
    for given in ("", None, "<html><body>maintenance</body></html>", b"\xff\xfe nonsense"):
        found = read_page(given)
        assert found == Probe() and not found.readable


def test_bytes_are_decoded_the_same_way_text_is():
    assert read_page(LIVE_PAGE.encode("utf-8")) == read_page(LIVE_PAGE)


def test_a_live_page_with_no_video_id_anywhere_is_not_announceable():
    body = LIVE_PAGE.replace(f'watch?v={VIDEO}', "watch?v=").replace(f'"{VIDEO}"', '""')

    found = read_page(body)

    assert found.live and found.video_id is None and not found.announceable


def test_the_probe_url_is_the_channels_own_live_page():
    assert LIVE_URL.format(channel_id="UC123") == "https://www.youtube.com/channel/UC123/live"


# --- the confirm parser -------------------------------------------------------------------------


def _payload(**details):
    return {
        "items": [
            {
                "id": VIDEO,
                "snippet": {
                    "title": "lofi radio",
                    "channelTitle": "Lofi Girl",
                    "thumbnails": {
                        "medium": {"url": "https://i.ytimg.com/vi/x/mq.jpg"},
                        "maxres": {"url": "https://i.ytimg.com/vi/x/max.jpg"},
                    },
                },
                "liveStreamingDetails": details,
            }
        ]
    }


def test_a_started_broadcast_with_no_end_time_is_live():
    found = read_confirm(_payload(actualStartTime="2026-09-17T10:00:00Z"), VIDEO)

    assert found.live and found.started and not found.ended
    assert found.title == "lofi radio" and found.channel_title == "Lofi Girl"
    assert found.thumbnail == "https://i.ytimg.com/vi/x/max.jpg"


def test_a_broadcast_with_an_end_time_is_not_live_any_more():
    found = read_confirm(
        _payload(actualStartTime="2026-09-17T10:00:00Z", actualEndTime="2026-09-17T12:00:00Z"),
        VIDEO,
    )

    assert found.started and found.ended and not found.live


def test_a_broadcast_that_never_started_is_not_live():
    assert not read_confirm(_payload(scheduledStartTime="2026-09-18T10:00:00Z"), VIDEO).live


def test_an_answer_about_another_video_confirms_nothing():
    assert read_confirm(_payload(actualStartTime="x"), "somethingelse") is None


def test_an_empty_or_unusable_answer_confirms_nothing():
    for given in ({}, {"items": []}, None, "nonsense", {"items": ["not a row"]}):
        assert read_confirm(given, VIDEO) is None


def test_a_row_with_no_snippet_still_answers_with_the_live_facts():
    found = read_confirm(
        {"items": [{"id": VIDEO, "liveStreamingDetails": {"actualStartTime": "x"}}]}, VIDEO
    )

    assert found.live and found.title == "" and found.thumbnail == ""


# --- the miss counter ---------------------------------------------------------------------------


def test_a_live_read_clears_the_misses():
    assert after_probe(4, True) == 0


def test_every_other_read_adds_one():
    assert after_probe(0, False) == 1
    assert after_probe(1, False) == 2
    assert after_probe(None, False) == 1


@pytest.mark.parametrize(
    ("misses", "limit", "over"),
    [(0, 2, False), (1, 2, False), (2, 2, True), (3, 2, True), (1, 1, True), (4, 5, False)],
)
def test_a_stream_is_over_only_once_the_misses_reach_the_limit(misses, limit, over):
    assert is_over(misses, limit) is over


def test_a_nonsense_limit_never_ends_a_stream_on_a_single_quiet_probe():
    assert is_over(0, 0) is False
    assert is_over(1, 0) is True


# --- what the go-live path is handed --------------------------------------------------------------


def test_the_stream_handed_to_go_live_is_a_youtube_watch_page_with_no_game():
    info = stream_info(VIDEO, "lofi radio")

    assert info.url == f"https://www.youtube.com/watch?v={VIDEO}"
    assert info.platform == YOUTUBE
    assert info.title == "lofi radio"
    assert info.game is None


def test_with_no_confirmed_title_the_card_falls_back_to_its_own_wording():
    info = stream_info(VIDEO)

    assert info.title is None
    assert info.thumbnail_url == f"https://i.ytimg.com/vi/{VIDEO}/hqdefault.jpg"


def test_a_confirmed_thumbnail_is_used_ahead_of_the_guessed_one():
    info = stream_info(VIDEO, "t", "https://i.ytimg.com/vi/x/max.jpg")

    assert info.thumbnail_url == "https://i.ytimg.com/vi/x/max.jpg"


def test_a_confirm_reads_live_only_when_it_started_and_has_not_ended():
    assert Confirm(started=True).live
    assert not Confirm(started=True, ended=True).live
    assert not Confirm().live
