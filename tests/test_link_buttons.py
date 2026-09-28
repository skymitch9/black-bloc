import json

import discord

from black_bloc import link_buttons
from black_bloc.settings_store import BLOCKS_LIVE_DEFAULTS as SHIPPED


class Store:
    def __init__(self, **saved):
        self.saved = saved

    def get(self, guild_id, key):
        return self.saved.get(key)


ROWS = json.dumps(
    [
        {"label": "Our site", "url": "https://example.org"},
        {"label": "Schedule", "url": "https://example.org/when"},
    ]
)


def test_the_stored_rows_come_back_in_order():
    assert link_buttons.rows_of(ROWS) == [
        ("Our site", "https://example.org"),
        ("Schedule", "https://example.org/when"),
    ]
    assert link_buttons.rows_of("") == [] and link_buttons.rows_of(None) == []


def test_a_stored_value_that_no_longer_checks_draws_no_buttons_rather_than_a_bad_one():
    bad = json.dumps([{"label": "Old", "url": "http://plain.example"}])

    assert link_buttons.rows_of(bad) == []


def test_the_card_rides_above_the_buttons_unless_it_is_switched_off():
    on = link_buttons.links_look(Store(posts_block_links_rows=ROWS), 1)
    off = link_buttons.links_look(
        Store(posts_block_links_rows=ROWS, posts_block_links_card=False), 1
    )

    assert (on.title, on.text) == (
        SHIPPED["posts_block_links_title"],
        SHIPPED["posts_block_links_text"],
    )
    assert [label for label, _ in on.buttons] == ["Our site", "Schedule"]
    assert (off.title, off.text) == ("", "") and off.buttons == on.buttons


def test_an_editor_tick_overrides_the_saved_card_switch():
    store = Store(posts_block_links_card=False)

    assert link_buttons.shows_card(store, 1, "on") is True
    assert link_buttons.shows_card(Store(), 1, "off") is False
    assert link_buttons.shows_card(store, 1) is False


def test_the_block_goes_out_as_link_buttons_and_draws_nothing_with_nothing_to_show():
    bot = type("Bot", (), {})()
    guild = type("Guild", (), {"id": 1})()
    bot.store = Store(posts_block_links_rows=ROWS, posts_block_links_card=False)

    embed, view, stamp = link_buttons.links_parts(bot, guild, None)

    assert embed is None and stamp
    assert [one.style for one in view.children] == [discord.ButtonStyle.link] * 2
    bot.store = Store(posts_block_links_card=False)
    assert link_buttons.links_parts(bot, guild, None) is None
