from datetime import UTC, datetime, timedelta

import discord

from black_bloc.golive import (
    EMBED_COLOUR_DEFAULT,
    EMBED_NO_TITLE,
    GAME_FALLBACK,
    StreamInfo,
    announcement_embed,
    edits_on_end,
    embed_summary,
    end_details,
    end_summary,
    ended_embed,
    ended_text,
    enriched,
    extract_stream,
    from_twitch,
    is_streaming,
    parse_ts,
    passes_role_filters,
    platform_of,
    presence_image,
    render,
    should_announce,
    twitch_enrichable,
    twitch_login_from_url,
    with_box_art,
)
from black_bloc.settings_store import (
    GOLIVE_END_EDIT,
    GOLIVE_END_MODES,
    GOLIVE_END_OFF,
    GOLIVE_END_SUFFIX,
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


def test_only_the_edit_mode_touches_the_announcement():
    assert edits_on_end("edit") is True
    assert edits_on_end("off") is False
    assert edits_on_end(None) is False
    assert edits_on_end("on") is False


def test_the_end_log_says_the_announcement_was_left_alone_only_when_it_was():
    assert end_details("off") == {"announcement": "left"}
    assert end_details(None) == {"announcement": "left"}
    assert end_details("edit") == {}


def test_the_edit_mode_name_is_the_registrys_and_not_a_second_copy():
    assert edits_on_end(GOLIVE_END_EDIT) is True
    assert GOLIVE_END_MODES == (GOLIVE_END_OFF, GOLIVE_END_EDIT)


def test_the_end_summary_names_the_mode_and_shows_the_wording_only_when_it_is_used():
    assert end_summary(GOLIVE_END_OFF) == "off (left as posted)"
    assert end_summary(GOLIVE_END_EDIT) == f'edit ("{GOLIVE_END_SUFFIX}")'
    assert end_summary(GOLIVE_END_EDIT, " (over)") == 'edit (" (over)")'


def test_the_end_summary_never_calls_an_unreadable_mode_off():
    assert end_summary("wibble") == "wibble (left as posted)"
    assert end_summary(None) == "None (left as posted)"


def test_ended_text_is_appended_once():
    assert ended_text("live!") == "live! — stream ended"
    assert ended_text("live! — stream ended") == "live! — stream ended"


def test_the_default_ended_wording_is_the_registrys_and_not_a_second_copy():
    assert ended_text("live!") == "live!" + GOLIVE_END_SUFFIX


def test_ended_text_uses_the_wording_the_guild_set():
    assert ended_text("live!", " (over)") == "live! (over)"
    assert ended_text("live! (over)", " (over)") == "live! (over)"


def test_an_empty_ended_wording_adds_nothing():
    assert ended_text("live!", "") == "live!"
    assert ended_text("live!", "   ") == "live!"
    assert ended_text("live!", None) == "live!"


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

    over = ended_embed(live, "Alice", "Twitch", " (over)")

    assert over.footer.text == "Black Bloc · via Twitch · (over)"
    assert ended_embed(over, "Alice", "Twitch", " (over)").footer.text == over.footer.text


def test_an_empty_ended_wording_leaves_the_embed_footer_alone():
    live = announcement_embed(twitch_info(), FakeMember("Alice"), "twitch")

    assert ended_embed(live, "Alice", "Twitch", "").footer.text == "Black Bloc · via Twitch"
    assert ended_embed(live, "Alice", "Twitch", None).footer.text == "Black Bloc · via Twitch"


def test_the_ended_embed_survives_an_unknown_platform():
    live = announcement_embed(StreamInfo(game="Celeste"))
    assert ended_embed(live, "Alice", None).author.name == "Alice was live"


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
