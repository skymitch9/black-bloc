import json
import re
from datetime import UTC, datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

from black_bloc import marathon_public as mp

SKY = json.dumps([{"name": "Sky", "user_id": 9001, "login": "skyruns", "part": "runner"}])
NOBODY = json.dumps([{"name": "Somebody", "user_id": None, "login": None, "part": "runner"}])


def a_row(state="upcoming", people=SKY, **fields):
    return {"id": 3, "state": state, "people": people, "game": "Celeste"} | fields


@pytest.mark.parametrize("to", [mp.OPT_OUT, mp.OPT_IN, mp.POST, mp.REMOVE])
def test_the_custom_id_matches_the_template_and_fits(to):
    found = re.fullmatch(mp.TEMPLATE, mp.custom_id(7, 3, to))
    assert found and (found["marathon_id"], found["run_id"], found["to"]) == ("7", "3", to)
    assert len(mp.custom_id(10**18, 10**18, mp.OPT_OUT)) <= 100


def test_a_button_posted_before_the_opt_out_maps_to_the_toggle():
    assert mp.move_of(mp.POST) == mp.OPT_IN and mp.move_of(mp.REMOVE) == mp.OPT_OUT
    assert mp.move_of(mp.OPT_OUT) == mp.OPT_OUT and mp.move_of(mp.OPT_IN) == mp.OPT_IN


def test_auto_wants_a_switched_on_marathon_and_a_run_never_highlighted():
    on, off = {"public_highlight": 1}, {"public_highlight": 0}
    assert mp.auto_wanted(on, a_row(state="live"))
    assert not mp.auto_wanted(off, a_row(state="live"))
    assert not mp.auto_wanted({}, a_row(state="live"))
    removed = a_row(state="live", public_message_id=55, public_removed=1)
    assert not mp.auto_wanted(on, removed)


@pytest.mark.parametrize(
    ("given", "wanted"),
    [
        (True, True),
        (False, False),
        ("on", True),
        ("Off", False),
        (1, True),
        (0, False),
        ("loud", None),
        (2, None),
    ],
)
def test_the_switch_takes_on_and_off_in_any_spelling(given, wanted):
    assert mp.clean_switch(given) is wanted


def test_a_fetched_message_says_which_button_it_carries():
    button = SimpleNamespace(custom_id="marathon:highlight:7:3:remove", label="Remove")
    message = SimpleNamespace(components=[SimpleNamespace(children=[button])])
    assert mp.shown_button(message) == (
        mp.Button("marathon:highlight:7:3:remove", "Remove", "remove"),
    )
    assert mp.shown_button(SimpleNamespace(components=[])) == ()
    assert mp.shown_button(SimpleNamespace()) is False


def test_a_label_is_clamped_and_never_empty():
    assert mp.label("x" * 200) == "x" * 80
    assert mp.label("  ") == "…"


# --- a finished run: the past tense, the day, and no role mention ---------------------------------

WORDS = {
    "marathon_part_runner": "runs",
    "marathon_part_host": "hosts",
    "marathon_part_commentator": "is on commentary",
    "marathon_part_runner_done": "ran",
    "marathon_part_host_done": "hosted",
    "marathon_part_commentator_done": "was on commentary",
    "marathon_state_done": "done",
}
DONE_TEMPLATE = "**{runner}** {part} **{game}** — {category} {day} on **{marathon}** · {url}"
ENDED = "2026-10-03T19:40:00+00:00"
PHOENIX = ZoneInfo("America/Phoenix")


def done_row(people=SKY):
    return a_row(
        state="done",
        people=people,
        category="Any%",
        scheduled_at="2026-10-03T19:03:00+00:00",
        ends_at=ENDED,
    )


def at_utc(text):
    return datetime.fromisoformat(text).replace(tzinfo=UTC)


def day(now, zone=PHOENIX, row=None):
    return mp.day_word(
        row or done_row(),
        at_utc(now),
        zone,
        today="today",
        earlier="on {date}",
        earlier_default="on {date}",
    )


def test_a_done_post_swaps_each_part_word_for_its_past_tense_and_nothing_else():
    found = mp.done_words(WORDS)
    assert found["marathon_part_runner"] == "ran" and found["marathon_part_host"] == "hosted"
    assert found["marathon_part_commentator"] == "was on commentary"
    assert found["marathon_state_done"] == "done" and WORDS["marathon_part_runner"] == "runs"
    assert mp.done_words({"marathon_part_runner": "runs"}) == {"marathon_part_runner": "runs"}


def test_the_day_is_today_until_the_servers_midnight_then_the_date_the_run_ended():
    stamp = f"on <t:{int(at_utc(ENDED).timestamp())}:D>"
    assert day("2026-10-03T19:40:30") == "today"
    assert day("2026-10-04T06:59:00") == "today"
    assert day("2026-10-04T07:00:00") == stamp
    assert day("2026-10-09T12:00:00") == stamp
    assert day("2026-10-04T00:30:00", zone=UTC) == stamp


def test_a_run_with_no_end_on_record_or_not_over_reads_today():
    assert day("2026-10-09T12:00:00", row=a_row(state="done")) == "today"
    assert day("2026-10-09T12:00:00", row=a_row(state="live", ends_at=ENDED)) == "today"


def test_an_earlier_day_template_that_will_not_fill_falls_back_to_the_shipped_words():
    said = mp.day_word(
        done_row(),
        at_utc("2026-10-09T12:00:00"),
        PHOENIX,
        today="today",
        earlier="back {then}",
        earlier_default="on {date}",
    )
    assert said == f"on <t:{int(at_utc(ENDED).timestamp())}:D>"


@pytest.mark.parametrize(
    ("part", "name", "said"),
    [
        ("runner", "JR", "**JR** ran **Celeste** — Any% today on **GDQueer** · https://x"),
        ("host", "JR", "**JR** hosted **Celeste** — Any% today on **GDQueer** · https://x"),
    ],
)
def test_the_default_done_words_are_the_owners_sentence(part, name, said):
    people = [{"name": name, "user_id": 9001, "login": None, "part": part}]
    found = mp.done_text(
        done_row(people=json.dumps(people)),
        {"name": "GDQueer"},
        WORDS,
        template=DONE_TEMPLATE,
        default=DONE_TEMPLATE,
        url="https://x",
        unlisted="",
        day="today",
        people=people,
    )
    assert found == said and "<@&" not in found


def test_a_done_post_stands_only_without_a_role_mention_in_front_of_it():
    text = "**JR** ran **Celeste**"
    assert mp.says(text, text, done=True) and mp.says(f"note\n{text}", text, done=True)
    assert not mp.says(f"<@&5> {text}", text, done=True)
    assert mp.says(f"<@&5> {text}", text, done=False)
    assert not mp.says("something else", text, done=False) and not mp.says(text, "", done=False)
    assert mp.says("<@&5> said by staff", "<@&5> said by staff", done=True)


def test_a_done_template_that_will_not_fill_falls_back_to_the_shipped_words():
    found = mp.done_text(
        done_row(),
        {"name": "GDQueer"},
        WORDS,
        template="{runner} {nope}",
        default=DONE_TEMPLATE,
        url="https://x",
        unlisted="",
        day="today",
    )
    assert found == "**Sky** ran **Celeste** — Any% today on **GDQueer** · https://x"
