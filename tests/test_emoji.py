from types import SimpleNamespace

import pytest

from black_bloc.emoji import (
    NO_EMOJI,
    SKIN_TONE_DEFAULT,
    SKIN_TONE_NAMES,
    SKIN_TONES,
    TEST_MODE,
    TONEABLE,
    react_with,
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


@pytest.mark.parametrize(
    "glyph",
    [HEART, "❤️", "❤", "💜", "🍯", "⚠️", "⚠", "✅", "→"],
    ids=[
        "black-heart",
        "red-heart-vs16",
        "red-heart",
        "purple-heart",
        "honey",
        "warning-vs16",
        "warning",
        "check",
        "arrow",
    ],
)
def test_hearts_and_status_glyphs_are_never_given_a_skin_tone(glyph):
    assert glyph not in TONEABLE
    for name in SKIN_TONE_NAMES:
        assert toned(glyph, name) == glyph


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


class Reactable:
    def __init__(self, raises=None):
        self.channel = SimpleNamespace(id=1)
        self.reactions = []
        self.raises = raises

    async def add_reaction(self, emoji):
        if self.raises is not None:
            raise self.raises
        self.reactions.append(emoji)


async def test_react_with_puts_a_unicode_or_server_emoji_on_and_answers_none():
    bot = SimpleNamespace(guard=None)
    message = Reactable()
    assert await react_with(bot, message, "🥷🏿") is None
    assert await react_with(bot, message, "<:bloc:123456789012345678>") is None
    assert str(message.reactions[0]) == "🥷🏿"
    assert message.reactions[1].id == 123456789012345678


async def test_react_with_says_why_not_and_never_raises():
    message = Reactable(raises=RuntimeError("refused"))
    assert await react_with(SimpleNamespace(guard=None), message, "x") == "RuntimeError: refused"
    assert await react_with(SimpleNamespace(guard=None), Reactable(), "") == NO_EMOJI
    held = SimpleNamespace(guard=SimpleNamespace(allows_channel=lambda channel: False))
    quiet = Reactable()
    assert await react_with(held, quiet, "🎵") == TEST_MODE
    assert quiet.reactions == []
