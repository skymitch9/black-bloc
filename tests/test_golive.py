from datetime import UTC, datetime, timedelta

import discord
import pytest

from black_bloc.golive import (
    EMBED_COLOUR_DEFAULT,
    EMBED_COLOURS,
    EMBED_NO_TITLE,
    GAME_FALLBACK,
    PANEL_BUTTONS,
    PANEL_MINUTES_KEY,
    PANEL_TIMEOUT_FOOTER,
    PANEL_TITLE,
    SITE_BUTTON,
    STAFF_BUTTONS,
    StreamInfo,
    again_render,
    announcement_embed,
    card_lines,
    costream_author,
    costream_embed,
    costream_footer,
    costream_order,
    costream_render,
    embed_summary,
    end_marker,
    end_summary,
    ended_author,
    ended_embed,
    ended_footer,
    ended_render,
    enriched,
    extract_stream,
    from_twitch,
    humanise_duration,
    is_streaming,
    joins_session,
    panel_buttons,
    panel_minutes,
    parse_ts,
    passes_role_filters,
    ping_prefix,
    platform_of,
    presence_image,
    render,
    should_announce,
    single_embed,
    site_page_url,
    suppressed,
    twitch_enrichable,
    twitch_login_from_url,
    with_box_art,
)
from black_bloc.settings_store import (
    GOLIVE_COSTREAM_AUTHOR,
    GOLIVE_COSTREAM_TEMPLATE,
    GOLIVE_END_AUTHOR,
    GOLIVE_END_TEMPLATE,
    GOLIVE_LIVE_FIELD,
    GOLIVE_TEMPLATE,
)
from black_bloc.twitch import TwitchGame, TwitchStream

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


def test_every_shape_of_youtube_address_reads_as_youtube():
    for url in (
        "https://youtu.be/xyz",
        "https://www.youtube.com/watch?v=xyz",
        "https://youtube.com/live/xyz",
        "https://www.youtube.com/@blackbloc/live",
        "HTTPS://WWW.YOUTUBE.COM/WATCH?V=XYZ",
    ):
        assert platform_of(FakeActivity(), url) == "YouTube", url


def test_a_youtube_presence_is_read_as_a_youtube_stream():
    activity = discord.Streaming(name="YouTube", url="https://www.youtube.com/watch?v=xyz")
    info = extract_stream([activity])
    assert info == StreamInfo(
        url="https://www.youtube.com/watch?v=xyz", game=None, title=None, platform="YouTube"
    )


def test_the_platform_name_is_never_mistaken_for_the_stream_title():
    for name in ("YouTube", "Twitch"):
        activity = discord.Streaming(name=name, url=f"https://example.com/{name}")
        info = extract_stream([activity])
        assert info is not None and info.title is None


def test_only_a_twitch_or_unknown_stream_may_be_enriched_from_twitch():
    assert twitch_enrichable(StreamInfo(platform=None)) is True
    assert twitch_enrichable(StreamInfo(platform="Twitch")) is True
    assert twitch_enrichable(StreamInfo(platform="twitch")) is True
    assert twitch_enrichable(StreamInfo(platform="YouTube")) is False


def test_enrichment_never_overwrites_a_youtube_stream():
    stream = TwitchStream("1", "alice", "Alice", "Hades", "the real title", "2026-08-26T12:00:00Z")
    info = StreamInfo(url="https://youtu.be/xyz", platform="YouTube")
    assert enriched(info, stream) is info


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


def test_render_puts_the_streamers_own_role_after_the_one_everybody_shares():
    info = StreamInfo(url="u", game="g")
    assert render("hi", info, ping_role_id=99, fan_role_id=7) == "<@&99> <@&7> hi"
    assert render("hi", info, fan_role_id=7) == "<@&7> hi"
    assert render("hi", info, ping_role_id=99, fan_role_id=None) == "<@&99> hi"


def test_one_role_serving_as_both_is_mentioned_once():
    info = StreamInfo(url="u", game="g")
    assert render("hi", info, ping_role_id=99, fan_role_id=99) == "<@&99> hi"


def test_the_ping_prefix_keeps_the_order_it_was_given_and_drops_the_blanks():
    assert ping_prefix() == ""
    assert ping_prefix(None, 0, "") == ""
    assert ping_prefix(5, None, 6, 5) == "<@&5> <@&6> "


def test_render_survives_an_unknown_placeholder():
    info = StreamInfo(url="u", game="g")
    assert render("{name} {nope}", info, FakeMember("Alice")) == "Alice {nope}"


def test_a_broken_template_falls_back_to_the_default():
    info = StreamInfo(url="u", game="g")
    assert render("{unbalanced", info, FakeMember("Alice")) == render(
        GOLIVE_TEMPLATE, info, FakeMember("Alice")
    )


def test_render_fills_the_platform_and_leaves_an_unknown_one_blank():
    youtube = StreamInfo(url="https://youtu.be/xyz", game="Hades", platform="YouTube")
    assert render("live on {platform}", youtube) == "live on YouTube"
    assert render("live on {platform}", StreamInfo(url="u")) == "live on "


def test_a_template_without_the_platform_renders_exactly_as_before():
    youtube = StreamInfo(url="https://youtu.be/xyz", game="Hades", platform="YouTube")
    assert render(GOLIVE_TEMPLATE, youtube, FakeMember("Alice")) == (
        "REGULATORS! Mount up! **Alice** is currently streaming **Hades**! "
        "Check it out: https://youtu.be/xyz"
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


def test_the_end_summary_says_which_of_the_three_shapes_is_in_force():
    assert end_summary(GOLIVE_END_TEMPLATE) == 'edited (appended: "{live} — stream ended")'
    assert end_summary("{name} was live") == 'edited (rewritten: "{name} was live")'
    assert end_summary("   ") == "edited (the sentence as posted, nothing added)"
    assert end_summary(None) == "edited (the sentence as posted, nothing added)"


def test_the_end_summary_clips_a_long_rewrite_rather_than_filling_the_panel():
    assert end_summary("x" * 200) == 'edited (rewritten: "' + "x" * 39 + '…")'


def test_the_card_mark_is_whatever_the_one_end_wording_adds_after_live():
    assert end_marker(GOLIVE_END_TEMPLATE) == "stream ended"
    assert end_marker("{live} (over)") == "(over)"
    assert end_marker(f"{GOLIVE_LIVE_FIELD} — that is a wrap") == "that is a wrap"


def test_a_blank_end_wording_marks_the_card_with_nothing():
    assert end_marker("") == ""
    assert end_marker(None) == ""
    assert end_marker(GOLIVE_LIVE_FIELD) == ""


def test_an_end_wording_that_rewrites_keeps_the_default_card_mark():
    assert end_marker("**{name}** was streaming **{game}**. {url}") == "stream ended"
    assert end_marker("{live} — {name} is done") == "stream ended"


def test_the_card_footer_takes_the_mark_once_and_never_twice():
    assert ended_footer("Black Bloc · via Twitch", GOLIVE_END_TEMPLATE) == (
        "Black Bloc · via Twitch · stream ended"
    )
    assert ended_footer("Black Bloc · via Twitch · stream ended", GOLIVE_END_TEMPLATE) == (
        "Black Bloc · via Twitch · stream ended"
    )
    assert ended_footer("Black Bloc · via Twitch", "") == "Black Bloc · via Twitch"
    assert ended_footer("", GOLIVE_END_TEMPLATE) == "· stream ended"


ENDED_INFO = StreamInfo(
    url="https://www.twitch.tv/alice",
    game="Celeste",
    title="Any% attempts",
    platform="Twitch",
)
LIVE_CONTENT = "<@&55> **Sky** is currently streaming **Celeste**! Check it out: u"


def test_the_shipped_end_wording_appends_to_the_sentence_that_was_posted():
    assert ended_render(GOLIVE_END_TEMPLATE, ENDED_INFO, "Sky", content=LIVE_CONTENT) == (
        "**Sky** is currently streaming **Celeste**! Check it out: u — stream ended"
    )


def test_the_live_field_sits_anywhere_in_a_longer_wording():
    assert ended_render(
        "That is a wrap on {game}: {live} (ran {duration})",
        ENDED_INFO,
        "Sky",
        content="live!",
        duration="2 h 10 min",
    ) == "That is a wrap on Celeste: live! (ran 2 h 10 min)"


def test_a_wording_without_the_live_field_rewrites_the_whole_post():
    assert ended_render(
        "**{name}** was streaming **{game}**. {url}", ENDED_INFO, "Sky", content=LIVE_CONTENT
    ) == "**Sky** was streaming **Celeste**. https://www.twitch.tv/alice"


def test_a_blank_end_wording_keeps_the_bare_sentence_and_adds_nothing():
    assert ended_render("", ENDED_INFO, "Sky", content="live!") == "live!"
    assert ended_render(None, ENDED_INFO, "Sky", content="live!") == "live!"
    assert ended_render("   ", ENDED_INFO, "Sky", content="live! — stream ended") == (
        "live! — stream ended"
    )


def test_the_mention_is_dropped_unless_the_guild_keeps_it():
    assert ended_render("{name} is done", ENDED_INFO, "Sky", content=LIVE_CONTENT) == (
        "Sky is done"
    )
    assert ended_render(
        "{name} is done", ENDED_INFO, "Sky", content=LIVE_CONTENT, keep_mention=True
    ) == "<@&55> Sky is done"
    assert ended_render(GOLIVE_END_TEMPLATE, ENDED_INFO, "Sky", content=LIVE_CONTENT) == (
        "**Sky** is currently streaming **Celeste**! Check it out: u — stream ended"
    )
    assert ended_render(
        GOLIVE_END_TEMPLATE, ENDED_INFO, "Sky", content=LIVE_CONTENT, keep_mention=True
    ) == (LIVE_CONTENT + " — stream ended")


def test_the_length_is_shown_when_there_is_one_and_leaves_no_gap_when_there_is_not():
    template = "{name} streamed {game} for {duration}. {url}"
    assert ended_render(template, ENDED_INFO, "Sky", content="x", duration="2 h 10 min") == (
        "Sky streamed Celeste for 2 h 10 min. https://www.twitch.tv/alice"
    )
    assert ended_render(template, ENDED_INFO, "Sky", content="x") == (
        "Sky streamed Celeste. https://www.twitch.tv/alice"
    )


def test_an_empty_game_and_an_empty_url_never_show_as_a_gap():
    bare = StreamInfo()
    assert ended_render("**{name}** was streaming **{game}**. {url}", bare, "Sky", content="x") == (
        "**Sky** was streaming **something**."
    )
    assert ended_render("{name} played ({title})", bare, "Sky", content="x") == "Sky played"


def test_an_unreadable_end_wording_falls_back_to_the_default_and_never_raises(caplog):
    said = ended_render("{name} is {not closed", ENDED_INFO, "Sky", content="live!")
    assert said == "live! — stream ended"
    assert "could not be rendered" in caplog.text


def test_a_positional_field_falls_back_to_the_default_rather_than_raising(caplog):
    assert ended_render("{0} is done", ENDED_INFO, "Sky", content="live!") == (
        "live! — stream ended"
    )
    assert "could not be rendered" in caplog.text


def test_an_unknown_placeholder_is_left_standing_rather_than_losing_the_message():
    assert ended_render("{name} on {wibble}", ENDED_INFO, "Sky", content="x") == (
        "Sky on {wibble}"
    )


@pytest.mark.parametrize(
    ("seconds", "said"),
    [
        (0, "under a minute"),
        (59, "under a minute"),
        (60, "1 min"),
        (2880, "48 min"),
        (3600, "1 h"),
        (7800, "2 h 10 min"),
    ],
)
def test_a_stream_length_is_read_in_words(seconds, said):
    over = NOW + timedelta(seconds=seconds)
    assert humanise_duration(NOW.isoformat(), over.isoformat()) == said


def test_a_missing_or_unreadable_stamp_renders_as_nothing():
    assert humanise_duration(None, NOW.isoformat()) == ""
    assert humanise_duration(NOW.isoformat(), None) == ""
    assert humanise_duration(NOW.isoformat(), "") == ""
    assert humanise_duration("not a date", NOW.isoformat()) == ""


def test_the_shipped_end_author_line_is_the_registrys_and_not_a_second_copy():
    assert ended_author(GOLIVE_END_AUTHOR, "Sky", "Twitch") == "Sky was live on Twitch"


def test_a_blank_end_author_keeps_todays_line():
    assert ended_author("", "Sky", "Twitch") == "Sky was live on Twitch"
    assert ended_author(None, "Sky", None) == "Sky was live"


def test_an_end_author_without_a_platform_loses_the_dangling_on():
    assert ended_author(GOLIVE_END_AUTHOR, "Sky", None) == "Sky was live"
    assert ended_author("{name} streamed for {duration}", "Sky", "Twitch") == "Sky streamed"
    assert ended_author("{name} streamed for {duration}", "Sky", "Twitch", duration="48 min") == (
        "Sky streamed for 48 min"
    )


def test_an_unreadable_end_author_keeps_todays_line(caplog):
    assert ended_author("{name} was {live on", "Sky", "Twitch") == "Sky was live on Twitch"
    assert "could not be rendered" in caplog.text


def test_an_end_author_that_renders_to_nothing_keeps_todays_line():
    assert ended_author("{platform}", "Sky", None) == "Sky was live"


def twitch_info(**kwargs):
    kwargs.setdefault("url", "https://www.twitch.tv/alice")
    kwargs.setdefault("game", "Phantasy Star Online 2 New Genesis")
    kwargs.setdefault("title", "chill grind")
    kwargs.setdefault("platform", "Twitch")
    kwargs.setdefault("box_art_url", "https://static-cdn.jtvnw.net/ttv-boxart/1-285x380.jpg")
    return StreamInfo(**kwargs)


def test_the_embed_names_the_streamer_and_the_game_and_shows_the_box_art():
    embed = announcement_embed(twitch_info(), FakeMember("Alice"), "twitch")

    assert embed.author.name == "Alice is now live on Twitch!"
    assert embed.title == "chill grind" and embed.url == "https://www.twitch.tv/alice"
    assert [(f.name, f.value) for f in embed.fields] == [
        ("Game", "Phantasy Star Online 2 New Genesis")
    ]
    assert embed.image.url == "https://static-cdn.jtvnw.net/ttv-boxart/1-285x380.jpg"
    assert embed.colour.value == 0x9146FF
    assert embed.footer.text == "Black Bloc · via Twitch"
    assert embed.timestamp is not None


def test_the_embed_never_carries_an_avatar_anywhere():
    embed = announcement_embed(twitch_info(), FakeMember("Alice"), "twitch")
    payload = embed.to_dict()

    assert "icon_url" not in payload["author"]
    assert "thumbnail" not in payload
    assert payload["author"] == {"name": "Alice is now live on Twitch!"}


def test_a_youtube_embed_falls_back_to_the_presence_artwork():
    info = StreamInfo(
        url="https://www.youtube.com/watch?v=xyz",
        game="Celeste",
        title="any%",
        platform="YouTube",
        thumbnail_url="https://i.ytimg.com/vi/xyz/hqdefault.jpg",
    )

    embed = announcement_embed(info, FakeMember("Alice"), "presence")

    assert embed.author.name == "Alice is now live on YouTube!"
    assert embed.image.url == "https://i.ytimg.com/vi/xyz/hqdefault.jpg"
    assert embed.colour.value == 0xFF0000
    assert embed.footer.text == "Black Bloc · via Discord activity"


def test_box_art_wins_over_the_presence_artwork():
    info = twitch_info(thumbnail_url="https://preview/alice.jpg")
    assert announcement_embed(info).image.url.endswith("ttv-boxart/1-285x380.jpg")


def test_an_embed_with_nothing_known_still_reads_as_a_sentence():
    embed = announcement_embed(StreamInfo())

    assert embed.author.name == "Someone is now live!"
    assert embed.title == EMBED_NO_TITLE and embed.url is None
    assert [f.value for f in embed.fields] == [GAME_FALLBACK]
    assert embed.colour.value == EMBED_COLOUR_DEFAULT
    assert "image" not in embed.to_dict()


def test_an_overlong_title_is_clipped_to_what_discord_takes():
    embed = announcement_embed(twitch_info(title="x" * 400))
    assert len(embed.title) == 256 and embed.title.endswith("…")


def test_the_ended_embed_keeps_the_art_and_says_the_stream_is_over():
    live = announcement_embed(twitch_info(), FakeMember("Alice"), "twitch")

    over = ended_embed(live, "Alice", "Twitch")

    assert over.author.name == "Alice was live on Twitch"
    assert "icon_url" not in over.to_dict()["author"]
    assert over.image.url == live.image.url and over.url == live.url
    assert over.footer.text == "Black Bloc · via Twitch · stream ended"
    assert ended_embed(over, "Alice", "Twitch").footer.text == over.footer.text


def test_the_ended_embed_footer_says_what_the_guild_set():
    live = announcement_embed(twitch_info(), FakeMember("Alice"), "twitch")

    over = ended_embed(live, "Alice", "Twitch", "{live} (over)")

    assert over.footer.text == "Black Bloc · via Twitch · (over)"
    assert ended_embed(over, "Alice", "Twitch", "{live} (over)").footer.text == over.footer.text


def test_an_empty_ended_wording_leaves_the_embed_footer_alone():
    live = announcement_embed(twitch_info(), FakeMember("Alice"), "twitch")

    assert ended_embed(live, "Alice", "Twitch", "").footer.text == "Black Bloc · via Twitch"
    assert ended_embed(live, "Alice", "Twitch", None).footer.text == "Black Bloc · via Twitch"


def test_the_ended_embed_survives_an_unknown_platform():
    live = announcement_embed(StreamInfo(game="Celeste"))
    assert ended_embed(live, "Alice", None).author.name == "Alice was live"


def test_the_ended_embed_takes_the_author_line_the_guild_wrote():
    live = announcement_embed(twitch_info(), FakeMember("Alice"), "twitch")

    over = ended_embed(
        live,
        "Alice",
        "Twitch",
        author="{name} streamed on {platform} for {duration}",
        duration="2 h 10 min",
    )

    assert over.author.name == "Alice streamed on Twitch for 2 h 10 min"
    assert over.image.url == live.image.url and over.url == live.url


def test_a_blank_author_line_keeps_todays_ended_card():
    live = announcement_embed(twitch_info(), FakeMember("Alice"), "twitch")
    assert ended_embed(live, "Alice", "Twitch", author="").author.name == (
        "Alice was live on Twitch"
    )


def test_the_embed_summary_is_what_the_shadow_log_shows():
    embed = announcement_embed(twitch_info(), FakeMember("Alice"), "twitch")
    assert embed_summary(embed) == {
        "author": "Alice is now live on Twitch!",
        "title": "chill grind",
        "game": "Phantasy Star Online 2 New Genesis",
        "image": "https://static-cdn.jtvnw.net/ttv-boxart/1-285x380.jpg",
    }


def test_presence_artwork_is_worked_out_from_the_asset_without_a_lookup():
    assert presence_image(FakeActivity(assets={"large_image": "twitch:alice"})) == (
        "https://static-cdn.jtvnw.net/previews-ttv/live_user_alice-1280x720.jpg"
    )
    assert presence_image(FakeActivity(assets={"large_image": "youtube:xyz"})) == (
        "https://i.ytimg.com/vi/xyz/hqdefault.jpg"
    )
    assert presence_image(FakeActivity(assets={"large_image": "mp:external/a/b.png"})) == (
        "https://media.discordapp.net/external/a/b.png"
    )
    assert presence_image(FakeActivity(assets={"large_image": "https://cdn/a.png"})) == (
        "https://cdn/a.png"
    )


def test_unusable_presence_artwork_is_ignored_rather_than_guessed():
    assert presence_image(FakeActivity()) is None
    assert presence_image(FakeActivity(assets={})) is None
    assert presence_image(FakeActivity(assets={"large_image": "spotify:1"})) is None
    assert presence_image(FakeActivity(assets={"large_image": "https://a b/c.png"})) is None
    assert presence_image(FakeActivity(assets={"large_image": "http://cdn/a.png"})) is None


def test_a_generic_activitys_own_image_url_is_preferred():
    activity = FakeActivity(large_image_url="https://cdn/ready.png", assets={"large_image": "x"})
    assert presence_image(activity) == "https://cdn/ready.png"


def test_a_streaming_presence_carries_its_artwork_into_the_stream_info():
    activity = FakeActivity(
        type=discord.ActivityType.streaming,
        url="https://www.twitch.tv/alice",
        assets={"large_image": "twitch:alice"},
    )
    info = extract_stream([activity])
    assert info.thumbnail_url.endswith("live_user_alice-1280x720.jpg")


def test_a_twitch_row_carries_its_game_id_and_thumbnail():
    stream = TwitchStream(
        "1",
        "alice",
        "Alice",
        "Hades",
        "a title",
        "2026-08-26T12:00:00Z",
        game_id="509658",
        thumbnail_url="https://preview/alice-1280x720.jpg",
    )
    info = from_twitch(stream)
    assert info.game_id == "509658"
    assert info.thumbnail_url == "https://preview/alice-1280x720.jpg"
    filled = enriched(StreamInfo(url="https://www.twitch.tv/alice"), stream)
    assert filled.game_id == "509658" and filled.thumbnail_url == info.thumbnail_url


def test_box_art_is_only_filled_in_once():
    info = StreamInfo(game_id="1")
    art = TwitchGame("1", "Hades", "https://boxart/1.jpg")
    filled = with_box_art(info, art)
    assert filled.box_art_url == "https://boxart/1.jpg"
    assert with_box_art(filled, TwitchGame("1", "Hades", "https://other.jpg")) is filled
    assert with_box_art(info, TwitchGame("1", "Hades", "")) is info


@pytest.mark.parametrize("linked", [False, True])
@pytest.mark.parametrize("opted_out", [False, True])
@pytest.mark.parametrize("staff", [False, True])
def test_the_button_table_offers_one_link_move_and_one_opt_move(linked, opted_out, staff):
    """Eight member states; never both spellings of one move, never a move that is invalid."""
    found = panel_buttons(linked=linked, opted_out=opted_out, staff=staff)
    labels = [move.label for move in found]

    assert ("Link my Twitch channel" in labels) is not linked
    assert ("Change my channel" in labels) is linked
    assert ("Unlink" in labels) is linked
    assert ("Stop announcing my streams" in labels) is not opted_out
    assert ("Announce my streams again" in labels) is opted_out
    assert "Refresh" in labels
    assert ({"Logs", "Streamers…"} <= set(labels)) is staff
    assert len(labels) == len(set(labels))
    assert found == PANEL_BUTTONS[(linked, opted_out)] + (STAFF_BUTTONS if staff else ())


def test_the_link_moves_open_a_modal_and_nothing_else_does():
    every = {move for row in PANEL_BUTTONS.values() for move in row} | set(STAFF_BUTTONS)
    assert {move.action for move in every if move.needs_modal} == {"link", "change"}
    assert {move.row for move in every} == {0, 1, 2}


def test_the_card_says_whether_a_link_was_ever_checked():
    """Checklist 10: a link Twitch could not confirm never claims it was verified."""
    verified = card_lines("alice", "42", False)
    unverified = card_lines("alice", None, False)

    assert "twitch.tv/alice" in verified[1]
    assert "not verified" not in verified[1]
    assert "not verified with Twitch" in unverified[1]


def test_the_card_says_which_way_the_opt_out_points():
    assert "announced here whenever" in card_lines("alice", "42", False)[2]
    assert "because you opted out" in card_lines("alice", "42", True)[2]
    assert "none linked yet" in card_lines(None, None, False)[1]


def test_the_card_says_in_words_when_announcements_are_off_or_shadow():
    """P9: the feature being off is a LINE, never a refusal and never a dead button."""
    assert len(card_lines("alice", "42", False, mode="on")) == 3
    off = card_lines("alice", "42", False, mode="off")
    shadow = card_lines("alice", "42", False, mode="shadow")

    assert "**off** right now" in off[-1]
    assert "Linking still counts" in off[-1]
    assert "**shadow** right now" in shadow[-1]


def test_the_card_carries_a_channel_note_last_when_it_is_given_one():
    lines = card_lines("alice", "42", False, mode="on", channel_note="Test mode is on.")
    assert lines[-1] == "Test mode is on."
    assert card_lines("alice", "42", False, mode="on")[-1] != "Test mode is on."


def test_the_gone_quiet_footer_names_the_one_command_that_reopens_the_panel():
    assert PANEL_TIMEOUT_FOOTER == "This panel has gone quiet — run /golive again"
    assert PANEL_TITLE == "Go-live"
    assert SITE_BUTTON == "Open on the site"


def test_the_site_link_points_at_the_go_live_page_only_with_an_origin():
    assert site_page_url("https://blackbloc.test/") == "https://blackbloc.test/golive.html"
    assert site_page_url("") is None
    assert site_page_url(None) is None


def test_the_panel_minutes_key_reads_the_registry():
    class Store:
        def get(self, guild_id, key):
            assert key == PANEL_MINUTES_KEY
            return "12"

    assert panel_minutes(Store(), 7) == 12


# --- co-streaming: one announcement naming both platforms, Twitch first ------------------------


TWITCH_LIVE = StreamInfo(
    url="https://www.twitch.tv/alice",
    game="Celeste",
    title="Any% attempts",
    platform="Twitch",
)
YOUTUBE_LIVE = StreamInfo(
    url="https://www.youtube.com/watch?v=xyz", title="Live now", platform="YouTube"
)


def test_twitch_is_written_first_whichever_platform_arrived_first():
    assert costream_order(TWITCH_LIVE, YOUTUBE_LIVE) == (TWITCH_LIVE, YOUTUBE_LIVE)
    assert costream_order(YOUTUBE_LIVE, TWITCH_LIVE) == (TWITCH_LIVE, YOUTUBE_LIVE)


def test_two_platforms_that_are_neither_twitch_keep_the_order_they_arrived_in():
    kick = StreamInfo(url="https://kick.com/alice", platform="Kick")
    assert costream_order(YOUTUBE_LIVE, kick) == (YOUTUBE_LIVE, kick)


def test_only_the_twitch_link_previews_and_the_fill_is_what_suppresses_the_other():
    text = costream_render(GOLIVE_COSTREAM_TEMPLATE, TWITCH_LIVE, YOUTUBE_LIVE, "Alice")

    assert "Watch on Twitch: https://www.twitch.tv/alice ·" in text
    assert "<https://www.youtube.com/watch?v=xyz>" in text
    assert "<https://www.twitch.tv/alice>" not in text


def test_an_owner_cannot_unsuppress_the_second_link_by_rewriting_the_template():
    text = costream_render("{also_url}", TWITCH_LIVE, YOUTUBE_LIVE, "Alice")

    assert text == "<https://www.youtube.com/watch?v=xyz>"


def test_the_second_platform_with_no_url_reads_as_nothing_rather_than_empty_brackets():
    assert suppressed(None) == "" and suppressed("  ") == ""
    assert suppressed("https://x.test") == "<https://x.test>"


def test_the_co_stream_sentence_keeps_the_mention_the_message_already_carries():
    text = costream_render(
        GOLIVE_COSTREAM_TEMPLATE,
        TWITCH_LIVE,
        YOUTUBE_LIVE,
        "Alice",
        content="<@&77> REGULATORS! Mount up!",
    )

    assert text.startswith("<@&77> ")
    assert text.count("<@&77>") == 1


def test_an_unreadable_co_stream_template_falls_back_to_the_default_and_never_raises():
    text = costream_render("{nope}{", TWITCH_LIVE, YOUTUBE_LIVE, "Alice")

    assert text == costream_render(GOLIVE_COSTREAM_TEMPLATE, TWITCH_LIVE, YOUTUBE_LIVE, "Alice")


def test_an_empty_game_reads_something_on_the_co_stream_sentence_too():
    bare = StreamInfo(url="https://www.twitch.tv/alice", platform="Twitch")

    assert GAME_FALLBACK in costream_render(
        "{name} is playing {game}", bare, YOUTUBE_LIVE, "Alice"
    )


def test_the_card_top_line_names_both_platforms_and_blank_wording_keeps_todays():
    assert (
        costream_author(GOLIVE_COSTREAM_AUTHOR, TWITCH_LIVE, YOUTUBE_LIVE, "Alice")
        == "Alice is live on Twitch and YouTube"
    )
    assert (
        costream_author("", TWITCH_LIVE, YOUTUBE_LIVE, "Alice")
        == "Alice is now live on Twitch!"
    )


def test_the_footer_names_both_platforms_in_the_order_they_are_written():
    assert costream_footer(TWITCH_LIVE, YOUTUBE_LIVE) == "Black Bloc · via Twitch + YouTube"


def test_the_co_stream_card_is_the_twitch_card_with_both_platforms_on_it():
    card = announcement_embed(TWITCH_LIVE, None, "twitch")

    both = costream_embed(card, TWITCH_LIVE, YOUTUBE_LIVE, "Alice", GOLIVE_COSTREAM_AUTHOR)

    assert both.title == "Any% attempts"
    assert both.url == "https://www.twitch.tv/alice"
    assert both.colour.value == EMBED_COLOURS["twitch"]
    assert both.author.name == "Alice is live on Twitch and YouTube"
    assert both.footer.text == "Black Bloc · via Twitch + YouTube"
    assert embed_summary(both)["game"] == "Celeste"


def test_the_card_goes_back_to_one_platform_when_the_other_stops():
    card = costream_embed(
        announcement_embed(TWITCH_LIVE, None, "twitch"),
        TWITCH_LIVE,
        YOUTUBE_LIVE,
        "Alice",
        GOLIVE_COSTREAM_AUTHOR,
    )

    alone = single_embed(card, YOUTUBE_LIVE, "Alice", "youtube")

    assert alone.author.name == "Alice is now live on YouTube!"
    assert alone.url == "https://www.youtube.com/watch?v=xyz"
    assert alone.colour.value == EMBED_COLOURS["youtube"]
    assert alone.footer.text == "Black Bloc · via YouTube"


def test_the_live_sentence_re_rendered_for_an_edit_never_adds_a_mention_of_its_own():
    plain = again_render(GOLIVE_TEMPLATE, TWITCH_LIVE, "Alice")
    kept = again_render(GOLIVE_TEMPLATE, TWITCH_LIVE, "Alice", content="<@&77> anything")

    assert not plain.startswith("<@&")
    assert kept == "<@&77> " + plain


def test_a_second_platform_joins_only_when_the_mode_is_on_and_the_platform_is_new():
    row = {"platform": "Twitch", "also_source": None}

    assert joins_session(row, "YouTube", "on") is True
    assert joins_session(row, "Twitch", "on") is False
    assert joins_session(row, "twitch", "on") is False
    assert joins_session(row, "YouTube", "off") is False
    assert joins_session({"platform": None, "also_source": None}, "YouTube", "on") is False
    assert joins_session(row, None, "on") is False
    assert joins_session({"platform": "Twitch", "also_source": "youtube"}, "Kick", "on") is False
