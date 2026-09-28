import pytest

from black_bloc import tempvoice as helpers
from black_bloc.tempvoice import (
    AUTO_REGION,
    BLOCKED,
    CARD_BUTTONS,
    GUEST,
    NONE,
    ORPHAN,
    OWNER,
    VOICE_REGIONS,
    card_buttons,
    makes_rooms,
    named_regions,
    panel_minutes,
    panel_state,
    people_controls,
    site_page_url,
    undo_options,
)

OWNER_ID = 900
OTHER = 901


class FakeStore:
    def __init__(self, value):
        self.value = value

    def get(self, guild_id, key):
        assert key == helpers.PANEL_MINUTES_KEY
        return self.value


def rows(*pairs):
    return [{"channel_id": channel_id, "owner_id": owner_id} for channel_id, owner_id in pairs]


def labels(moves):
    return [move.label for move in moves]


def test_the_named_regions_are_exactly_the_twenty_five_a_select_holds():
    assert len(named_regions()) == 25
    assert AUTO_REGION not in named_regions()
    assert set(named_regions()) | {AUTO_REGION} == set(VOICE_REGIONS)


def test_no_state_is_reached_without_the_role_unless_the_caller_is_staff():
    assert panel_state(rows((10, OWNER_ID)), OWNER_ID, 10, allowed=False) == BLOCKED


def test_owning_a_channel_wins_over_standing_in_someone_else_s():
    found = rows((10, OWNER_ID), (11, OTHER))

    assert panel_state(found, OWNER_ID, 11, connected=[OTHER]) == OWNER
    assert panel_state(found, OWNER_ID, 10, connected=[OWNER_ID]) == OWNER
    assert panel_state(found, OWNER_ID, None) == OWNER


def test_standing_in_nothing_of_black_bloc_s_is_the_empty_state():
    assert panel_state(rows((11, OTHER)), OWNER_ID, None) == NONE
    assert panel_state([], OWNER_ID, 99) == NONE
    assert panel_state(rows((11, OTHER)), OWNER_ID, 99) == NONE


def test_the_owner_being_gone_is_what_separates_a_claim_from_a_visit():
    found = rows((11, OTHER))

    assert panel_state(found, OWNER_ID, 11, connected=[OWNER_ID]) == ORPHAN
    assert panel_state(found, OWNER_ID, 11, connected=[OWNER_ID, OTHER]) == GUEST
    assert panel_state(found, OWNER_ID, 11, connected=()) == ORPHAN


@pytest.mark.parametrize("state", [BLOCKED, NONE, OWNER, ORPHAN, GUEST])
@pytest.mark.parametrize("locked", [False, True])
@pytest.mark.parametrize("hidden", [False, True])
@pytest.mark.parametrize("has_prefs", [False, True])
@pytest.mark.parametrize("staff", [False, True])
def test_every_state_renders_exactly_its_row_of_the_table(
    state, locked, hidden, has_prefs, staff
):
    """Checklist 3 and 12: the table is data, and no state may render a move it forbids."""
    found = card_buttons(
        state,
        locked=locked,
        hidden=hidden,
        has_prefs=has_prefs,
        staff=staff,
        has_lobbies=staff,
    )
    said = labels(found)

    assert len(said) == len(set(said))
    assert ("Lock" in said) != ("Unlock" in said) if state == OWNER else True
    assert not (state != OWNER and ("Lock" in said or "Unlock" in said))
    assert ("Hide" in said) != ("Show" in said) if state == OWNER else True
    assert ("Claim" in said) == (state == ORPHAN)
    assert ("Forget my settings" in said) == (has_prefs and state != BLOCKED)
    assert ("Rename" in said) == (state == OWNER)
    assert "Refresh" in said
    for staff_label in ("Setup", "Forget a lobby…", "Logs", "Mode…"):
        assert (staff_label in said) == staff
    assert all(move in CARD_BUTTONS or move.action in {m.action for m in CARD_BUTTONS}
               for move in found)


def test_a_locked_or_hidden_channel_offers_the_move_back_and_never_both():
    plain = labels(card_buttons(OWNER))
    shut = labels(card_buttons(OWNER, locked=True, hidden=True))

    assert "Lock" in plain and "Hide" in plain
    assert "Unlock" in shut and "Show" in shut
    assert "Lock" not in shut and "Hide" not in shut


def test_the_owner_card_never_spills_past_five_buttons_a_row():
    found = card_buttons(OWNER, has_prefs=True, staff=True, has_lobbies=True)
    rows_used: dict[int, int] = {}
    for move in found:
        rows_used[move.row] = rows_used.get(move.row, 0) + 1

    assert max(rows_used.values()) <= 5
    assert max(rows_used) <= 4


def test_a_staffer_with_no_lobby_at_all_is_not_offered_one_to_forget():
    assert "Forget a lobby…" not in labels(card_buttons(NONE, staff=True, has_lobbies=False))
    assert "Forget a lobby…" in labels(card_buttons(NONE, staff=True, has_lobbies=True))


def test_the_people_selects_render_only_when_there_is_somebody_for_them():
    assert people_controls() == (helpers.PERMIT_PICK, helpers.BAN_PICK)
    assert helpers.KICK_PICK in people_controls(others_here=True)
    assert helpers.UNDO_PICK in people_controls(has_lists=True)
    assert helpers.KICK_PICK not in people_controls(has_lists=True)


def test_every_undo_option_carries_the_word_for_its_own_kind():
    assert undo_options([1, 2], [3]) == [
        (1, helpers.UNPERMIT_KIND),
        (2, helpers.UNPERMIT_KIND),
        (3, helpers.UNBAN_KIND),
    ]
    assert undo_options(None, None) == []


def test_shadow_counts_as_working_everywhere_the_mode_is_read():
    """Shadow only hides the lobby — spawning, the panel and the reconcile treat it as on."""
    assert makes_rooms("shadow") is True
    assert makes_rooms("on") is True
    assert makes_rooms("off") is False
    assert makes_rooms(None) is False
    assert set(helpers.MODE_MEANS) == {"off", "shadow", "on"}


def test_the_lobby_block_shows_only_while_members_can_see_the_lobby():
    assert helpers.shows_block("on") is True
    assert helpers.shows_block("shadow") is False
    assert helpers.shows_block("off") is False
    assert helpers.shows_block(None) is False


def test_the_panel_minutes_key_reads_the_registry_and_the_site_page_is_the_shared_one():
    assert panel_minutes(FakeStore(12), 7) == 12
    assert site_page_url("https://x.test/") == "https://x.test/tempvoice.html"
    assert site_page_url("") is None


# --- the lobby block's words (blocks-convert, 2026-09-28) --------------------------------------


class WordStore:
    def __init__(self, **values):
        self.values = values

    def get(self, guild_id, key):
        return self.values.get(key)


def test_the_block_says_the_shipped_words_while_its_keys_are_blank():
    look = helpers.block_look(WordStore(), 7, [(333, "join to create a channel")])

    assert look.title == helpers.TEMPVOICE_BLOCK_DEFAULTS[helpers.TEMPVOICE_BLOCK_TITLE]
    assert look.text == helpers.TEMPVOICE_BLOCK_DEFAULTS[helpers.TEMPVOICE_BLOCK_TEXT]
    assert look.buttons == (
        ("🔊 join to create a channel", "https://discord.com/channels/7/333"),
        (helpers.CONTROLS_LABEL_DEFAULT, None),
    )


def test_each_lobby_gets_its_own_button_from_the_label_template_capped_at_four():
    store = WordStore(tempvoice_block_lobby_label="Hop into {lobby}!")
    lobbies = [(n, f"lobby {n}") for n in range(1, 7)]

    look = helpers.block_look(store, 7, lobbies)

    wanted = [f"Hop into lobby {n}!" for n in range(1, 5)]
    assert [label for label, _ in look.buttons[:-1]] == wanted
    assert len(look.buttons) == helpers.BLOCK_LOBBIES_MAX + 1
    assert all(len(label) <= 80 for label, _ in look.buttons)


def test_the_controls_button_follows_its_key_and_an_editor_s_unsaved_tick():
    off = WordStore(tempvoice_block_show_controls=False)

    assert helpers.block_look(off, 7, []).buttons == ()
    assert helpers.block_look(off, 7, [], controls="on").buttons[-1][1] is None
    assert helpers.block_look(WordStore(), 7, [], controls="off").buttons == ()


def test_the_stamp_moves_when_any_word_or_lobby_moves():
    one = helpers.block_look(WordStore(), 7, [(1, "a")]).stamp()

    assert one == helpers.block_look(WordStore(), 7, [(1, "a")]).stamp()
    assert one != helpers.block_look(WordStore(tempvoice_block_title="Hi"), 7, [(1, "a")]).stamp()
    assert one != helpers.block_look(WordStore(), 7, [(1, "b")]).stamp()


def test_the_block_s_button_never_shares_a_custom_id_with_the_in_channel_controls():
    assert helpers.block_custom_id(7) == "tvblock:open:7"
    assert not helpers.block_custom_id(7).startswith(helpers_panel_prefix())


def helpers_panel_prefix():
    from black_bloc.cogs.community.tempvoice import PANEL_PREFIX

    return f"{PANEL_PREFIX}:"
