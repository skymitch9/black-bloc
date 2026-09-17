import re

import pytest

from black_bloc.frontdoor import (
    CUSTOM_ID_TEMPLATE,
    EVENT,
    KINDS,
    LABEL_DEFAULTS,
    LABEL_KEYS,
    LABEL_LIMIT,
    REQUEST,
    TICKET,
    custom_id,
    door_embed,
    door_is_on,
    door_takes_over,
    door_text,
    door_title,
    door_where,
    followed_slug,
    label_for,
    labels,
    replaces_ticket_button,
)
from black_bloc.settings_store import (
    FRONTDOOR_CHANNEL,
    FRONTDOOR_EVENT_LABEL_DEFAULT,
    FRONTDOOR_FOLLOWS_POST,
    FRONTDOOR_MESSAGE,
    FRONTDOOR_MODE,
    FRONTDOOR_REPLACES_TICKET_BUTTON,
    FRONTDOOR_REQUEST_LABEL_DEFAULT,
    FRONTDOOR_TEXT,
    FRONTDOOR_TEXT_DEFAULT,
    FRONTDOOR_TICKET_LABEL,
    FRONTDOOR_TICKET_LABEL_DEFAULT,
    FRONTDOOR_TITLE,
    FRONTDOOR_TITLE_DEFAULT,
    KEY_TYPES,
    namespace_of,
)

GUILD = 7
CHANNEL = 800
MESSAGE = 1417000000000000000


class FakeStore:
    def __init__(self, values=None):
        self.values = dict(values or {})

    def get(self, guild_id, key):
        if key in self.values:
            return self.values[key]
        return DEFAULTS.get(key)


DEFAULTS = {
    FRONTDOOR_MODE: "on",
    FRONTDOOR_TITLE: FRONTDOOR_TITLE_DEFAULT,
    FRONTDOOR_TEXT: FRONTDOOR_TEXT_DEFAULT,
    FRONTDOOR_REPLACES_TICKET_BUTTON: True,
    FRONTDOOR_FOLLOWS_POST: "welcome",
}


def store(**values):
    return FakeStore(values)


@pytest.mark.parametrize("kind", KINDS)
def test_a_custom_id_says_which_door_it_is_and_which_guild(kind):
    found = custom_id(kind, GUILD)
    assert found == f"door:{kind}:{GUILD}"
    match = re.fullmatch(CUSTOM_ID_TEMPLATE, found)
    assert match is not None
    assert match["kind"] == kind and int(match["guild_id"]) == GUILD


def test_the_template_matches_the_three_doors_and_nothing_else():
    assert re.fullmatch(CUSTOM_ID_TEMPLATE, "door:ticket:1") is not None
    assert re.fullmatch(CUSTOM_ID_TEMPLATE, "door:thread:1") is None
    assert re.fullmatch(CUSTOM_ID_TEMPLATE, "door:ticket:abc") is None
    assert re.fullmatch(CUSTOM_ID_TEMPLATE, "modmail:ticket:1") is None


def test_the_three_kinds_are_named_once_and_each_has_a_key_and_a_default():
    assert KINDS == (TICKET, REQUEST, EVENT)
    assert set(LABEL_KEYS) == set(KINDS) == set(LABEL_DEFAULTS)
    assert LABEL_DEFAULTS[TICKET] == FRONTDOOR_TICKET_LABEL_DEFAULT
    assert LABEL_DEFAULTS[REQUEST] == FRONTDOOR_REQUEST_LABEL_DEFAULT
    assert LABEL_DEFAULTS[EVENT] == FRONTDOOR_EVENT_LABEL_DEFAULT


def test_every_front_door_key_is_in_the_registry_and_sits_with_modmail():
    every = [*LABEL_KEYS.values(), FRONTDOOR_MODE, FRONTDOOR_CHANNEL, FRONTDOOR_MESSAGE]
    for key in every:
        assert key in KEY_TYPES, key
        assert namespace_of(key) == "modmail", key


def test_a_blank_label_reads_as_the_shipped_wording_rather_than_an_empty_button():
    assert label_for(store(**{FRONTDOOR_TICKET_LABEL: ""}), GUILD, TICKET) == (
        FRONTDOOR_TICKET_LABEL_DEFAULT
    )
    assert label_for(store(**{FRONTDOOR_TICKET_LABEL: "   "}), GUILD, TICKET) == (
        FRONTDOOR_TICKET_LABEL_DEFAULT
    )
    assert label_for(store(**{FRONTDOOR_TICKET_LABEL: "Tell a mod"}), GUILD, TICKET) == (
        "Tell a mod"
    )


def test_a_label_is_cut_to_discords_own_eighty_characters():
    long = "x" * 200
    found = label_for(store(**{FRONTDOOR_TICKET_LABEL: long}), GUILD, TICKET)
    assert len(found) == LABEL_LIMIT


def test_labels_answers_all_three_at_once():
    found = labels(store(), GUILD)
    assert found == {kind: LABEL_DEFAULTS[kind] for kind in KINDS}


def test_the_heading_and_the_line_under_it_fall_back_to_the_shipped_words():
    assert door_title(store(**{FRONTDOOR_TITLE: ""}), GUILD) == FRONTDOOR_TITLE_DEFAULT
    assert door_text(store(**{FRONTDOOR_TEXT: ""}), GUILD) == FRONTDOOR_TEXT_DEFAULT
    assert door_title(store(**{FRONTDOOR_TITLE: "Stuck?"}), GUILD) == "Stuck?"


def test_the_card_is_the_heading_and_the_line_and_nothing_else():
    card = door_embed(store(), GUILD).to_dict()
    assert card["title"] == FRONTDOOR_TITLE_DEFAULT
    assert card["description"] == FRONTDOOR_TEXT_DEFAULT
    assert not card.get("fields")


def test_the_mode_is_read_as_a_word_never_as_a_truthy_value():
    assert door_is_on(store(**{FRONTDOOR_MODE: "on"}), GUILD)
    assert not door_is_on(store(**{FRONTDOOR_MODE: "off"}), GUILD)
    assert not door_is_on(store(**{FRONTDOOR_MODE: None}), GUILD)


def test_none_is_the_word_that_means_the_door_follows_no_post():
    assert followed_slug(store(**{FRONTDOOR_FOLLOWS_POST: "welcome"}), GUILD) == "welcome"
    assert followed_slug(store(**{FRONTDOOR_FOLLOWS_POST: "none"}), GUILD) == ""
    assert followed_slug(store(**{FRONTDOOR_FOLLOWS_POST: "NONE"}), GUILD) == ""
    assert followed_slug(store(**{FRONTDOOR_FOLLOWS_POST: ""}), GUILD) == ""


def test_where_the_door_is_reads_a_snowflake_back_out_of_text():
    found = store(**{FRONTDOOR_CHANNEL: CHANNEL, FRONTDOOR_MESSAGE: str(MESSAGE)})
    assert door_where(found, GUILD) == (CHANNEL, MESSAGE)
    assert door_where(store(), GUILD) == (None, None)


def test_the_door_only_takes_a_channel_over_when_it_is_actually_up_in_it():
    up = {FRONTDOOR_CHANNEL: CHANNEL, FRONTDOOR_MESSAGE: str(MESSAGE)}
    assert door_takes_over(store(**up), GUILD) == CHANNEL
    assert door_takes_over(store(**{**up, FRONTDOOR_MODE: "off"}), GUILD) is None
    assert (
        door_takes_over(store(**{**up, FRONTDOOR_REPLACES_TICKET_BUTTON: False}), GUILD) is None
    )
    assert door_takes_over(store(**{FRONTDOOR_CHANNEL: CHANNEL}), GUILD) is None
    assert door_takes_over(store(), GUILD) is None


def test_replacing_the_ticket_button_is_on_by_default_and_is_a_real_bool():
    assert replaces_ticket_button(store(), GUILD) is True
    assert replaces_ticket_button(store(**{FRONTDOOR_REPLACES_TICKET_BUTTON: False}), GUILD) is (
        False
    )
