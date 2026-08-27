from types import SimpleNamespace

from black_bloc.emoji import (
    SKIN_TONE_DEFAULT,
    SKIN_TONE_NAMES,
    SKIN_TONES,
    TONEABLE,
    tone_for,
    toned,
    toned_text,
)

WAVE = "\U0001f44b"
HEART = "\U0001f5a4"
DARK = "\U0001f3ff"


def test_the_default_tone_is_dark():
    assert SKIN_TONE_DEFAULT == "dark"
    assert SKIN_TONES["dark"] == DARK
    assert toned(WAVE) == WAVE + DARK


def test_the_tones_are_the_six_discord_offers_in_order():
    assert SKIN_TONE_NAMES == (
        "none",
        "light",
        "medium-light",
        "medium",
        "medium-dark",
        "dark",
    )
    assert [SKIN_TONES[name] for name in SKIN_TONE_NAMES[1:]] == [
        chr(cp) for cp in range(0x1F3FB, 0x1F400)
    ]


def test_every_tone_lands_on_a_hand():
    for name, modifier in SKIN_TONES.items():
        assert toned(WAVE, name) == WAVE + modifier


def test_a_heart_is_never_given_a_skin_tone():
    for name in SKIN_TONE_NAMES:
        assert toned(HEART, name) == HEART
        assert toned("❤️", name) == "❤️"
        assert toned("\U0001f36f", name) == "\U0001f36f"
        assert toned("⚠️", name) == "⚠️"


def test_hearts_and_status_glyphs_are_outside_the_toneable_set():
    for glyph in ("❤", "\U0001f5a4", "\U0001f49c", "⚠", "✅", "→"):
        assert glyph not in TONEABLE


def test_toning_replaces_a_tone_that_is_already_there():
    assert toned(WAVE + DARK, "light") == WAVE + SKIN_TONES["light"]
    assert toned(WAVE + DARK, "none") == WAVE


def test_a_variation_selector_gives_way_to_the_modifier():
    assert toned("☝️", "dark") == "☝" + DARK
    assert toned("☝️", "none") == "☝️"


def test_an_empty_string_and_plain_words_come_back_unchanged():
    assert toned("", "dark") == ""
    assert toned("hi", "dark") == "hi"
    assert toned_text("no emoji here", "dark") == "no emoji here"


def test_a_whole_line_is_toned_without_touching_the_words():
    line = f"Hi Alice {WAVE} I am on shift, and the heart {HEART} stays as it is."

    assert toned_text(line, "dark") == line.replace(WAVE, WAVE + DARK)
    assert toned_text(line, "none") == line
    assert toned_text(toned_text(line, "dark"), "medium") == line.replace(
        WAVE, WAVE + SKIN_TONES["medium"]
    )


def test_tone_for_reads_the_guilds_setting():
    bot = SimpleNamespace(store=SimpleNamespace(get=lambda gid, key: "light"))
    assert tone_for(bot, 1) == "light"


def test_a_dm_and_a_bot_with_no_store_both_get_the_default():
    bot = SimpleNamespace(store=SimpleNamespace(get=lambda gid, key: "light"))
    assert tone_for(bot, None) == SKIN_TONE_DEFAULT
    assert tone_for(SimpleNamespace(), 1) == SKIN_TONE_DEFAULT


def test_a_store_that_answers_with_nonsense_does_not_break_a_reply():
    def boom(gid, key):
        raise RuntimeError("no database")

    assert tone_for(SimpleNamespace(store=SimpleNamespace(get=boom)), 1) == SKIN_TONE_DEFAULT
    assert (
        tone_for(SimpleNamespace(store=SimpleNamespace(get=lambda g, k: "teal")), 1)
        == SKIN_TONE_DEFAULT
    )
