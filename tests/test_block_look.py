from black_bloc import block_look


class Store:
    def __init__(self, **saved):
        self.saved = saved

    def get(self, guild_id, key):
        return self.saved.get(key)


def test_a_blank_word_is_the_shipped_one_and_a_saved_one_is_cut_to_its_limit():
    assert block_look.word(Store(), 1, "golive_block_title") == "Live now"
    assert block_look.word(Store(golive_block_title="  "), 1, "golive_block_title") == "Live now"
    assert block_look.word(Store(golive_block_title="x" * 300), 1, "golive_block_title", 256) == (
        "x" * 256
    )


def test_a_number_that_does_not_read_falls_back_to_the_shipped_one():
    assert block_look.number(Store(golive_block_max=3), 1, "golive_block_max") == 3
    assert block_look.number(Store(golive_block_max="many"), 1, "golive_block_max") == 10
    assert block_look.number(Store(), 1, "events_block_max") == 5


def test_member_words_cannot_bold_link_or_ping():
    said = block_look.plain("**hi** [x](https://evil) @everyone")

    assert "\\*\\*hi\\*\\*" in said
    assert "\\[x\\]" in said
    assert "@everyone" not in said


def test_a_link_is_drawn_only_for_a_web_address_with_nothing_that_breaks_markdown():
    assert block_look.linked("Watch", "https://www.twitch.tv/casey") == (
        "[Watch](https://www.twitch.tv/casey)"
    )
    assert block_look.linked("Watch", "javascript:alert(1)") == "Watch"
    assert block_look.linked("Watch", "https://a.b/x)y") == "Watch"
    assert block_look.linked("Watch", None) == "Watch"


def test_only_whole_lines_that_fit_one_card_are_kept():
    lines = ["a" * 30, "b" * 30, "c" * 30]

    assert block_look.lines_within(lines, 61) == "\n".join(lines[:2])
    assert block_look.lines_within(lines, 10) == ""


def test_the_stamp_moves_only_when_what_is_drawn_moves():
    one = block_look.Look("Live now", "**Casey** — late night")
    same = block_look.Look("Live now", "**Casey** — late night")
    other = block_look.Look("Live now", "**Casey** — early morning")

    assert one.stamp() == same.stamp()
    assert one.stamp() != other.stamp()


def test_a_look_with_no_words_draws_no_card_and_its_buttons_go_five_to_a_row():
    buttons = tuple((f"L{n}", f"https://example.org/{n}") for n in range(7))
    embed, view, stamp = block_look.parts_of(block_look.Look("", "", buttons))

    assert embed is None and stamp
    assert [(one.label, one.url, one.row) for one in view.children][4:6] == [
        ("L4", "https://example.org/4", 0),
        ("L5", "https://example.org/5", 1),
    ]
    assert block_look.view_of(block_look.Look("Links", "")) is None
