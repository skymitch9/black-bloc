from black_bloc import marathon_ping as mp


def test_a_marathon_with_no_switch_set_pings_no_role():
    assert mp.pings_role({"ping_role": 0}) is False
    assert mp.pings_role({"ping_role": None}) is False
    assert mp.pings_role({}) is False
    assert mp.pings_role(None) is False
    assert mp.pings_role({"ping_role": 1}) is True


def test_the_switch_reads_booleans_words_and_zero_or_one_and_nothing_else():
    assert mp.clean_ping_role(True) is True and mp.clean_ping_role(False) is False
    assert mp.clean_ping_role(1) is True and mp.clean_ping_role(0) is False
    assert mp.clean_ping_role(" ON ") is True and mp.clean_ping_role("off") is False
    for bad in (2, -1, "maybe", None, ""):
        assert mp.clean_ping_role(bad) is None


def test_the_card_button_is_gone_with_the_shrunk_card():
    assert not hasattr(mp, "card_move") and not hasattr(mp, "MOVE_WANTS")
