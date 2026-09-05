import pytest

from black_bloc.honeypot import (
    CLEAR_EXEMPT,
    EXEMPT_SELECT_MAX,
    FORGET,
    LOGS,
    PANEL_MINUTES_KEY,
    PANEL_MOVES,
    REFRESH,
    SETTINGS,
    SETUP,
    SITE,
    exempt_defaults,
    exempt_diff,
    exempt_editable,
    exempt_sentence,
    forget_buttons,
    mode_options,
    panel_minutes,
    root_buttons,
    settings_buttons,
    trap_options,
)

GUILD = 7


class FakeStore:
    def __init__(self, values):
        self.values = values

    def get(self, guild_id, key):
        return self.values.get(key)


def actions(moves):
    return [move.action for move in moves]


def test_every_move_is_distinct_and_every_label_is_plain_text():
    assert len({move.action for move in PANEL_MOVES}) == len(PANEL_MOVES)
    for move in PANEL_MOVES:
        assert move.label == move.label.strip() and move.label
        assert not set(move.label) & set("*_`~|#")


def test_the_root_offers_setup_and_forget_and_clear_only_where_they_are_valid():
    every = root_buttons(may_setup=True, may_forget=True, may_clear=True, has_site=True)
    assert actions(every) == [SETUP, FORGET, CLEAR_EXEMPT, SETTINGS, REFRESH, LOGS, SITE]

    bare = root_buttons(may_setup=False, may_forget=False, may_clear=False, has_site=False)
    assert actions(bare) == [SETTINGS, REFRESH, LOGS]


@pytest.mark.parametrize(
    "state,may_setup,may_forget",
    [
        ("S2 — nothing recorded", True, False),
        ("S3 — a live trap", False, True),
        ("S4 — a recorded id Discord lost", True, True),
    ],
)
def test_setup_and_forget_are_the_state_machine_not_a_pair_of_toggles(
    state, may_setup, may_forget
):
    found = actions(
        root_buttons(may_setup=may_setup, may_forget=may_forget, may_clear=False, has_site=False)
    )
    assert (SETUP in found) is may_setup, state
    assert (FORGET in found) is may_forget, state


def test_exempt_nobody_is_absent_while_the_list_is_already_empty():
    assert CLEAR_EXEMPT not in actions(
        root_buttons(may_setup=False, may_forget=False, may_clear=False, has_site=False)
    )
    assert CLEAR_EXEMPT in actions(
        root_buttons(may_setup=False, may_forget=False, may_clear=True, has_site=False)
    )


def test_the_settings_and_forget_cards_can_always_be_left():
    assert actions(settings_buttons()) == ["panel_numbers", "back"]
    assert actions(forget_buttons()) == ["back"]


def test_the_rows_never_pass_discords_five_per_row():
    every = root_buttons(may_setup=True, may_forget=True, may_clear=True, has_site=True)
    for row in {move.row for move in every}:
        assert len([move for move in every if move.row == row]) <= 5


@pytest.mark.parametrize("current", ["off", "shadow", "on"])
def test_on_is_absent_from_the_picker_while_arming_would_be_refused(current):
    armable = mode_options(current, True)
    assert [value for value, _label, _now in armable] == ["off", "shadow", "on"]

    blocked = mode_options(current, False)
    assert [value for value, _label, _now in blocked] == ["off", "shadow"]

    assert [now for _v, _l, now in armable].count(True) == 1
    for _value, label, _now in armable:
        assert not set(label) & set("*_`~|#")


def test_the_current_mode_is_flagged_and_nothing_else_is():
    assert mode_options("shadow", True)[1][2] is True
    assert [now for _v, _l, now in mode_options("nonsense", True)] == [False, False, False]


def test_a_channel_discord_no_longer_has_still_gets_a_row_that_says_so():
    found = trap_options([111, 222], {111: "do-not-post-here"})

    assert found[0] == ("#do-not-post-here", 111, True)
    assert found[1] == ("a channel Discord no longer has (222)", 222, False)
    assert trap_options([]) == [] and trap_options(None) == []


def test_a_very_long_channel_name_is_cut_to_what_a_select_option_holds():
    (label, ident, live) = trap_options([111], {111: "x" * 300})[0]

    assert len(label) <= 100 and ident == 111 and live is True


@pytest.mark.parametrize("count", [0, 1, 25, 26])
def test_the_prefill_is_exact_up_to_the_cap_and_the_picker_is_withheld_past_it(count):
    ids = list(range(1000, 1000 + count))

    assert exempt_defaults(ids) == ids
    assert exempt_editable(ids) is (count <= EXEMPT_SELECT_MAX)


def test_the_prefill_de_duplicates_and_keeps_the_order_it_was_given():
    assert exempt_defaults([3, 1, 3, 2, 1]) == [3, 1, 2]
    assert exempt_defaults(["5", 5]) == [5]
    assert exempt_defaults(None) == []


def test_the_diff_is_what_the_one_log_row_carries():
    assert exempt_diff([1, 2], [1, 2, 3]) == ([3], [])
    assert exempt_diff([1, 2, 3], [1]) == ([], [2, 3])
    assert exempt_diff([1, 2], [2, 4]) == ([4], [1])
    assert exempt_diff([1, 2], [2, 1]) == ([], [])
    assert exempt_diff([1, 1, 2], [2, 2, 1]) == ([], [])
    assert exempt_diff([], []) == ([], [])


def test_a_submit_that_changed_nothing_says_so_rather_than_claiming_a_write():
    assert "nothing changed" in exempt_sentence([], [])
    assert "<@&5>" in exempt_sentence([5], [])
    said = exempt_sentence([5], [6])
    assert "now ignores <@&5>" in said and "stops ignoring <@&6>" in said


def test_the_panel_minutes_key_is_read_off_the_registry():
    assert PANEL_MINUTES_KEY == "honeypot_panel_minutes"
    assert panel_minutes(FakeStore({PANEL_MINUTES_KEY: 15}), GUILD) == 15
