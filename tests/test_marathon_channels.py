from black_bloc import marathon_channels as mc


def test_a_row_the_migration_has_not_reached_takes_marathons():
    assert mc.takes_marathons({"twitch_login": "gdq"})
    assert not mc.takes_marathons({"marathons": 0})
    assert mc.takes_marathons({"marathons": 1})


def test_esa_is_the_one_seeded_opt_out_and_its_marker_is_its_own():
    assert mc.OPTED_OUT_SEEDS == ("esamarathon",)
    assert mc.seed_key("ESAMarathon") == "optout:esamarathon"


def test_the_panel_line_says_on_or_off():
    assert mc.panel_line({"marathons": 1}) == "Marathons: **on**"
    assert mc.panel_line({"marathons": 0}).startswith("Marathons: **off")
