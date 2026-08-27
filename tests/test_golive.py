from datetime import UTC, datetime, timedelta

import discord

from black_bloc.golive import (
    GAME_FALLBACK,
    StreamInfo,
    ended_text,
    enriched,
    extract_stream,
    from_twitch,
    is_streaming,
    parse_ts,
    passes_role_filters,
    platform_of,
    render,
    should_announce,
    twitch_login_from_url,
)
from black_bloc.settings_store import GOLIVE_TEMPLATE
from black_bloc.twitch import TwitchStream

NOW = datetime(2026, 8, 26, 12, 0, tzinfo=UTC)


class FakeActivity:
    def __init__(self, **kwargs):
        self.type = kwargs.pop("type", discord.ActivityType.playing)
        for name, value in kwargs.items():
            setattr(self, name, value)


class FakeMember:
    def __init__(self, display_name):
        self.display_name = display_name


def streaming(**kwargs):
    kwargs.setdefault("url", "https://www.twitch.tv/alice")
    kwargs.setdefault("game", "Celeste")
    kwargs.setdefault("details", "any% no major glitches")
    kwargs.setdefault("platform", "Twitch")
    return FakeActivity(type=discord.ActivityType.streaming, **kwargs)


def session(ended_at):
    return {"ended_at": ended_at}


def test_a_real_streaming_activity_is_recognised():
    activity = discord.Streaming(name="Twitch", url="https://www.twitch.tv/alice")
    assert is_streaming(activity)
    info = extract_stream([activity])
    assert info is not None and info.url == "https://www.twitch.tv/alice"


def test_extract_stream_reads_url_game_and_title():
    info = extract_stream([streaming()])
    assert info == StreamInfo(
        url="https://www.twitch.tv/alice",
        game="Celeste",
        title="any% no major glitches",
        platform="Twitch",
    )


def test_extract_stream_ignores_non_streaming_activities():
    playing = FakeActivity(type=discord.ActivityType.playing, name="Celeste")
    listening = FakeActivity(type=discord.ActivityType.listening, name="Spotify")
    assert extract_stream([playing, listening]) is None
    assert extract_stream([]) is None
    assert extract_stream(None) is None


def test_extract_stream_finds_the_stream_in_a_mixed_list():
    playing = FakeActivity(type=discord.ActivityType.playing, name="Celeste")
    info = extract_stream([playing, streaming()])
    assert info is not None and info.game == "Celeste"


def test_extract_stream_falls_back_to_state_and_name():
    activity = FakeActivity(
        type=discord.ActivityType.streaming,
        url="https://www.twitch.tv/bob",
        state="Hades",
        name="a title",
    )
    info = extract_stream([activity])
    assert info is not None and info.game == "Hades" and info.title == "a title"


def test_a_stream_with_no_game_reports_none():
    info = extract_stream([streaming(game="  ", details=None, name=None)])
    assert info is not None and info.game is None and info.title is None


def test_platform_comes_from_the_activity_then_the_url():
    assert platform_of(FakeActivity(platform="Twitch"), None) == "Twitch"
    assert platform_of(FakeActivity(), "https://www.twitch.tv/alice") == "Twitch"
    assert platform_of(FakeActivity(), "https://youtu.be/xyz") == "YouTube"
    assert platform_of(FakeActivity(), "https://example.com/live") is None


def test_render_matches_the_incumbent_wording():
    info = StreamInfo(url="https://www.twitch.tv/alice", game="Celeste", title="any%")
    text = render(GOLIVE_TEMPLATE, info, FakeMember("Alice"))
    assert text == (
        "REGULATORS! Mount up! **Alice** is currently streaming **Celeste**! "
        "Check it out: https://www.twitch.tv/alice"
    )


def test_render_never_prints_four_stars_for_an_empty_game():
    info = StreamInfo(url="https://www.twitch.tv/alice", game=None)
    text = render(GOLIVE_TEMPLATE, info, FakeMember("Alice"))
    assert "****" not in text
    assert f"**{GAME_FALLBACK}**" in text


def test_render_uses_the_display_name_and_falls_back_to_someone():
    info = StreamInfo(url="u", game="g")
    assert "**Alice**" in render("{name}: **{name}**", info, FakeMember("Alice"))
    assert render("{name}", info) == "Someone"


def test_render_prefixes_the_ping_role_when_one_is_set():
    info = StreamInfo(url="u", game="g")
    assert render("hi", info, ping_role_id=99) == "<@&99> hi"
    assert render("hi", info, ping_role_id=None) == "hi"


def test_render_survives_an_unknown_placeholder():
    info = StreamInfo(url="u", game="g")
    assert render("{name} {nope}", info, FakeMember("Alice")) == "Alice {nope}"


def test_a_broken_template_falls_back_to_the_default():
    info = StreamInfo(url="u", game="g")
    assert render("{unbalanced", info, FakeMember("Alice")) == render(
        GOLIVE_TEMPLATE, info, FakeMember("Alice")
    )


def test_render_fills_title_and_url():
    info = StreamInfo(url="https://twitch.tv/a", game="g", title="a title")
    assert render("{title} — {url}", info) == "a title — https://twitch.tv/a"
    assert render("{title}|{url}", StreamInfo()) == "|"


def test_should_announce_allows_a_first_stream():
    assert should_announce(NOW, None, 60) is True


def test_should_announce_refuses_while_a_session_is_open():
    assert should_announce(NOW, session(None), 60) is False


def test_should_announce_refuses_inside_the_cooldown():
    ended = (NOW - timedelta(minutes=59)).isoformat()
    assert should_announce(NOW, session(ended), 60) is False


def test_should_announce_allows_after_the_cooldown():
    ended = (NOW - timedelta(minutes=61)).isoformat()
    assert should_announce(NOW, session(ended), 60) is True
    assert should_announce(NOW, session((NOW - timedelta(minutes=60)).isoformat()), 60) is True


def test_a_zero_cooldown_always_allows_a_closed_session():
    assert should_announce(NOW, session(NOW.isoformat()), 0) is True


def test_should_announce_treats_an_unparseable_end_as_ended():
    assert should_announce(NOW, session("not-a-date"), 60) is True
    assert should_announce(NOW, session(""), 60) is False


def test_parse_ts_assumes_utc_for_a_naive_timestamp():
    assert parse_ts("2026-08-26T12:00:00") == NOW
    assert parse_ts(None) is None
    assert parse_ts("") is None


def test_role_filters():
    assert passes_role_filters([1, 2], None, None) is True
    assert passes_role_filters([1, 2], 2, None) is True
    assert passes_role_filters([1, 2], 3, None) is False
    assert passes_role_filters([1, 2], None, 2) is False
    assert passes_role_filters([1, 2], 1, 3) is True


def test_twitch_login_from_url():
    assert twitch_login_from_url("https://www.twitch.tv/Alice") == "alice"
    assert twitch_login_from_url("https://twitch.tv/bob/") == "bob"
    assert twitch_login_from_url("https://twitch.tv/bob?x=1") == "bob"
    assert twitch_login_from_url("https://youtube.com/live") is None
    assert twitch_login_from_url(None) is None


def test_enrichment_only_fills_the_gaps():
    stream = TwitchStream("1", "alice", "Alice", "Hades", "the real title", "2026-08-26T12:00:00Z")
    info = StreamInfo(url=None, game=None, title="presence title", platform=None)
    filled = enriched(info, stream)
    assert filled == StreamInfo(
        url="https://www.twitch.tv/alice",
        game="Hades",
        title="presence title",
        platform="Twitch",
    )
    assert enriched(info, None) is info


def test_from_twitch_builds_a_full_streaminfo():
    stream = TwitchStream("1", "alice", "Alice", "Hades", "a title", "2026-08-26T12:00:00Z")
    assert from_twitch(stream) == StreamInfo(
        url="https://www.twitch.tv/alice", game="Hades", title="a title", platform="Twitch"
    )


def test_ended_text_is_appended_once():
    assert ended_text("live!") == "live! — stream ended"
    assert ended_text("live! — stream ended") == "live! — stream ended"
