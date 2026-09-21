from __future__ import annotations

from types import SimpleNamespace

import pytest

from black_bloc import frontdoor as door
from black_bloc import golive as gl
from black_bloc import preview
from black_bloc.config import load_settings
from black_bloc.settings_store import SettingsStore


def without_stamp(embed: dict) -> dict:
    return {key: value for key, value in embed.items() if key != "timestamp"}


@pytest.fixture
def guild():
    return SimpleNamespace(
        id=99,
        name="Black in a Flash!",
        get_role=lambda role_id: SimpleNamespace(id=role_id, name="Stream pings"),
        get_channel=lambda channel_id: SimpleNamespace(id=channel_id, name="live-now"),
    )


@pytest.fixture
def store(monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    return SettingsStore(None, load_settings(_env_file=None))


@pytest.fixture
def bot(store, guild):
    return SimpleNamespace(store=store, guild=guild, guilds=[guild])


def test_every_renderer_draws_something_the_bot_could_actually_send(bot, guild):
    for feature in preview.RENDERERS:
        found = preview.render(bot, guild, feature).to_dict()

        assert found["content"] or found["embeds"] or found["components"], (
            f"{feature} drew nothing at all, so the mock under the editor would be empty"
        )
        assert isinstance(found["mentions"]["roles"], list)


def test_the_live_announcement_is_the_bot_s_own_render_and_not_a_copy(bot, guild, store):
    found = preview.render(bot, guild, "golive_live")
    facts = preview.golive_sample({})
    info = preview.stream_of(facts)

    assert found.content == gl.render(
        store.get(guild.id, "golive_template"),
        info,
        name=facts["name"],
        ping_role_id=store.get(guild.id, "golive_ping_role_id"),
    )
    # `announcement_embed` stamps `now`, so the two calls differ by microseconds and by
    # nothing else — which is the whole assertion.
    wanted = gl.announcement_embed(info, source=facts["source"], name=facts["name"]).to_dict()
    assert found.embeds[0]["timestamp"]
    assert without_stamp(found.embeds[0]) == without_stamp(wanted)


def test_the_front_door_card_is_door_embed_and_its_buttons_are_the_stored_labels(bot, guild, store):
    found = preview.render(bot, guild, "frontdoor")

    assert found.embeds[0] == door.door_embed(store, guild.id).to_dict()
    assert [one["label"] for one in found.components[0]] == list(
        door.labels(store, guild.id).values()
    )
    assert found.components[0][0]["style"] == "primary"


def test_a_draft_reaches_the_render_and_is_never_written_to_the_store(bot, guild, store):
    before = store.get(guild.id, "golive_template")

    found = preview.render(
        bot, guild, "golive_live", {"golive_template": "{name} is on {platform}: {url}"}
    )

    assert found.content == "Casey is on Twitch: https://twitch.tv/caseyfast"
    assert store.get(guild.id, "golive_template") == before
    assert not store.is_stored(guild.id, "golive_template")


def test_a_draft_only_reaches_the_guild_it_was_drafted_for(store, guild):
    overlaid = preview.PreviewStore(store, guild.id, {"golive_template": "drafted"})

    assert overlaid.get(guild.id, "golive_template") == "drafted"
    assert overlaid.get(guild.id + 1, "golive_template") == store.get(
        guild.id + 1, "golive_template"
    )


def test_a_key_that_belongs_to_another_message_is_refused_in_words(bot, guild):
    with pytest.raises(preview.PreviewRefused) as raised:
        preview.render(bot, guild, "golive_live", {"frontdoor_title": "Not here"})

    assert raised.value.error == "not_this_features_key"
    assert "frontdoor_title" in raised.value.message
    assert raised.value.message.endswith(".")
    assert "400" not in raised.value.message


def test_a_feature_nothing_draws_is_refused_in_words(bot, guild):
    with pytest.raises(preview.PreviewRefused) as raised:
        preview.render(bot, guild, "no_such_thing")

    assert raised.value.error == "no_such_preview"
    assert "no_such_thing" in raised.value.message
    assert "reload the dashboard" in raised.value.message


def test_the_sample_is_the_renderer_s_own_and_a_key_it_does_not_know_is_ignored(bot, guild):
    found = preview.render(
        bot, guild, "golive_live", None, {"game": "Celeste", "made_up": "<@everyone>"}
    )

    assert "Celeste" in found.content
    assert "made_up" not in found.content


def test_asking_for_youtube_moves_the_sample_to_youtube(bot, guild):
    found = preview.render(bot, guild, "golive_live", None, {"platform": "youtube"})

    assert "youtube.com" in found.content
    assert found.embeds[0]["color"] == gl.EMBED_COLOURS["youtube"]


def test_a_role_mention_comes_back_named_so_the_site_can_draw_a_pill(bot, guild):
    found = preview.render(
        bot, guild, "golive_live", {"golive_template": "<@&4242> {name} is live"}
    )

    assert found.mentions["roles"] == [{"id": "4242", "name": "Stream pings"}]


def test_a_mention_of_something_gone_is_named_rather_than_left_as_an_id(store):
    gone = SimpleNamespace(id=99, get_role=lambda role_id: None, get_channel=lambda cid: None)

    found = preview.pills(gone, "<@&1> and <#2>")

    assert found["roles"] == [{"id": "1", "name": "unknown"}]
    assert found["channels"] == [{"id": "2", "name": "deleted-channel"}]


def test_the_live_top_line_is_drawn_from_the_draft_the_editor_holds(bot, guild):
    found = preview.render(
        bot, guild, "golive_live", {"golive_live_author": "{name} just went live on {platform}"}
    )

    assert found.embeds[0]["author"]["name"] == "Casey just went live on Twitch"


def test_the_live_editor_may_override_both_of_its_own_keys_and_nothing_else(bot, guild):
    assert preview.RENDERERS["golive_live"].keys == (
        "golive_template",
        "golive_live_author",
    )

    with pytest.raises(preview.PreviewRefused):
        preview.render(bot, guild, "golive_live", {"golive_end_author": "nope"})


def test_the_ended_wording_reads_only_the_end_keys(bot, guild):
    found = preview.render(
        bot, guild, "golive_ended", {"golive_end_author": "{name} has finished"}
    )

    assert found.embeds[0]["author"]["name"] == "Casey has finished"


def test_a_wording_the_bot_could_not_render_falls_back_the_way_the_bot_does(bot, guild, store):
    found = preview.render(bot, guild, "golive_live", {"golive_template": "{nope"})

    assert found.content == gl.render(
        store.get(guild.id, "golive_template"),
        preview.stream_of(preview.golive_sample({})),
        name="Casey",
        ping_role_id=store.get(guild.id, "golive_ping_role_id"),
    )


def test_the_features_map_names_one_feature_per_key_and_no_key_twice():
    payload = preview.features_payload()

    assert [one["feature"] for one in payload["features"]] == list(preview.RENDERERS)
    seen: list[str] = []
    for one in payload["features"]:
        seen.extend(one["keys"])
    assert len(seen) == len(set(seen))
    assert payload["keys"]["golive_template"] == "golive_live"


def test_every_key_a_renderer_claims_is_a_real_setting():
    from black_bloc.settings_store import KEY_TYPES

    for key in preview.KEY_FEATURES:
        assert key in KEY_TYPES, f"{key} is not in the registry"
        assert KEY_TYPES[key] in ("text", "longtext"), (
            f"{key} is a {KEY_TYPES[key]}, and a mock is only ever drawn under a text box"
        )


def test_a_move_tuple_becomes_discord_s_own_rows():
    moves = [
        SimpleNamespace(label="Pick up", style="primary", row=0),
        SimpleNamespace(label="Decline", style="danger", row=1),
    ]

    assert preview.moves_to_rows(moves) == (
        ({"label": "Pick up", "style": "primary", "url": None, "disabled": False, "emoji": None},),
        ({"label": "Decline", "style": "danger", "url": None, "disabled": False, "emoji": None},),
    )
    assert preview.moves_to_rows(()) == ()
