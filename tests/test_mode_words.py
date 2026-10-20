from black_bloc.mode_words import mode_word, stored_mode, words_for

THREE = ("off", "shadow", "on")


def test_shadow_reads_test_and_temp_voice_reads_staff_only():
    assert mode_word("automod_mode", "shadow") == "test"
    assert mode_word("tempvoice_mode", "shadow") == "staff only"
    assert mode_word("automod_mode", "on") == "on"
    assert mode_word("automod_mode", None) == "None"


def test_a_typed_word_is_read_back_as_the_stored_value():
    assert stored_mode("honeypot_mode", "test", THREE) == "shadow"
    assert stored_mode("tempvoice_mode", "staff only", THREE) == "shadow"
    assert stored_mode("tempvoice_mode", "test", THREE) == "test"
    assert stored_mode("rolemenu_mode", "test", ("off", "on")) == "test"
    assert stored_mode("honeypot_mode", "on", THREE) == "on"


def test_the_choices_are_listed_in_the_words_a_person_reads():
    assert words_for("automod_mode", THREE) == "off, test, on"
    assert words_for("tempvoice_mode", THREE) == "off, staff only, on"
