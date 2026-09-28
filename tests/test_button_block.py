import re

import discord

from black_bloc import button_block as bb

DEFAULTS = {"t": "Shipped heading", "x": "Shipped line", "b": "Shipped button", "s": "Hi {role}."}
WORDS = bb.Words("t", "x", "b")


class Store:
    def __init__(self, **values):
        self.values = values

    def get(self, guild_id, key):
        return self.values.get(key)


def test_a_blank_key_says_the_shipped_words():
    look = bb.look(Store(), 7, WORDS, DEFAULTS)

    assert look == bb.ButtonLook("Shipped heading", "Shipped line", "Shipped button")


def test_saved_words_win_and_each_is_cut_to_discord_s_own_cap():
    look = bb.look(Store(t="h" * 300, x="Mine", b="b" * 100), 7, WORDS, DEFAULTS)

    assert len(look.title) == bb.TITLE_MAX and look.text == "Mine"
    assert len(look.label) == bb.LABEL_MAX


def test_the_stamp_moves_when_any_word_moves():
    one = bb.look(Store(), 7, WORDS, DEFAULTS).stamp()

    assert one == bb.look(Store(), 7, WORDS, DEFAULTS).stamp()
    assert one != bb.look(Store(b="Press"), 7, WORDS, DEFAULTS).stamp()


def test_the_custom_id_is_guild_keyed_and_its_template_reads_it_back():
    found = re.fullmatch(bb.template("x:open"), bb.custom_id("x:open", 7))

    assert bb.custom_id("x:open", 7) == "x:open:7"
    assert found and found["guild_id"] == "7"
    assert re.fullmatch(bb.template("x:open"), "xyopen:7") is None


def test_parts_is_one_card_and_one_persistent_button():
    item = discord.ui.Button(label="Press", custom_id="x:open:7")
    look = bb.look(Store(), 7, WORDS, DEFAULTS)

    embed, view, stamp = bb.parts(look, item)

    assert embed.title == "Shipped heading" and embed.description == "Shipped line"
    assert view.timeout is None and view.children == [item]
    assert stamp == look.stamp()


def test_an_answer_fills_its_fields_and_a_broken_one_falls_back_to_the_shipped_words():
    assert bb.said(Store(), 7, "s", DEFAULTS, role="Marathon") == "Hi Marathon."
    assert bb.said(Store(s="Yo {role}!"), 7, "s", DEFAULTS, role="M") == "Yo M!"
    assert bb.said(Store(s="Oops {nope}"), 7, "s", DEFAULTS, role="M") == "Hi M."
