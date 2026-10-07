import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from black_bloc import marathon as mt
from black_bloc import marathon_reminder_posts as mrem

NOW = datetime(2027, 1, 4, 18, 0, tzinfo=UTC)


def iso(minutes):
    return (NOW + timedelta(minutes=minutes)).isoformat()


def a_copy(message_id=5, text="words", head="", at=None):
    return {"channel_id": 9, "message_id": message_id, "text": text, "head": head, "at": at}


def test_a_copy_remembers_where_it_is_what_it_says_and_what_stood_before_the_words():
    message = SimpleNamespace(id=77, content="<@&5> a note\nSky runs Game")
    found = mrem.copy_of(message, 9, "Sky runs Game", iso(30))

    assert found == {
        "channel_id": 9,
        "message_id": 77,
        "text": "Sky runs Game",
        "head": "<@&5> a note\n",
        "at": iso(30),
    }
    assert mrem.body(found, "Sky runs Game later") == "<@&5> a note\nSky runs Game later"
    assert mrem.copy_of(None, 9, "x", None) is None
    assert mrem.copy_of(message, None, "x", None) is None


def test_an_entry_is_posted_only_when_a_copy_went_out():
    assert mrem.entry_of(staff=a_copy(), public=None) == {"posted": True, "staff": a_copy()}
    assert mrem.entry_of(staff=None, public=None) == {"posted": False}
    assert mrem.with_skipped({15: mrem.entry_of(staff=a_copy())}, [120]) == {
        15: {"posted": True, "staff": a_copy()},
        120: {"posted": False},
    }


def test_what_was_stored_reads_back_and_rubbish_reads_as_nothing():
    found = {15: mrem.entry_of(staff=a_copy(1), public=a_copy(2)), 120: {"posted": False}}
    assert mrem.posts_of(mrem.dump(found)) == found
    assert mrem.of_run({mrem.COLUMN: mrem.dump(found)}) == found
    for raw in (None, "", "nope", "[]", 7):
        assert mrem.posts_of(raw) == {}
    assert mrem.posts_of({"x": {}, "15": {"posted": 1, "staff": {"message_id": 0}}}) == {
        15: {"posted": True}
    }


def test_the_copies_stand_nearest_mark_first_and_the_public_one_first():
    found = {
        120: mrem.entry_of(staff=a_copy(1)),
        15: mrem.entry_of(staff=a_copy(2), public=a_copy(3)),
        1440: {"posted": False},
    }
    assert [(mark, name, copy["message_id"]) for mark, name, copy in mrem.standing(found)] == [
        (15, "public", 3),
        (15, "staff", 2),
        (120, "staff", 1),
    ]


def test_repost_forgets_every_mark_whose_moment_is_ahead_again_exactly_as_before():
    found = {15: mrem.entry_of(staff=a_copy()), 120: mrem.entry_of(staff=a_copy(6))}
    for start in (200, 60, 10):
        marks, kept = mrem.rearmed([120, 15], found, iso(start), NOW, mrem.REPOST)
        assert marks == mt.rearmed([120, 15], iso(start), NOW)
        assert sorted(kept) == marks


def test_edit_never_fires_a_posted_mark_again_but_a_skipped_one_fires_at_its_new_moment():
    found = {15: mrem.entry_of(staff=a_copy()), 120: {"posted": False}}
    marks, kept = mrem.rearmed([120, 15], found, iso(200), NOW, mrem.EDIT)

    assert marks == [15]
    assert kept == {15: mrem.entry_of(staff=a_copy())}


def test_a_mark_sent_before_posts_were_remembered_is_never_fired_again():
    assert mrem.held({}, [120, 15]) == {120, 15}
    assert mrem.rearmed([120, 15], {}, iso(200), NOW, mrem.EDIT) == ([15, 120], {})
    assert mrem.rearmed([120, 15], {}, iso(200), NOW, mrem.REPOST) == ([], {})


def test_a_mark_whose_message_is_gone_stays_posted_with_no_id():
    found = {15: mrem.entry_of(staff=a_copy(1), public=a_copy(2))}
    mrem.forget(found, 15, "public")

    assert found == {15: {"posted": True, "staff": a_copy(1)}}
    mrem.forget(found, 15, "staff")
    assert found == {15: {"posted": True}} and mrem.standing(found) == []
    assert mrem.rearmed([15], found, iso(200), NOW, mrem.EDIT)[0] == [15]


def test_an_edit_is_remembered_as_what_the_post_now_says():
    found = {15: mrem.entry_of(public=a_copy(2, head="<@&5> ", at=iso(30)))}
    mrem.shown(found, 15, "public", "new words", iso(45))

    assert found[15]["public"] == a_copy(2, text="new words", head="<@&5> ", at=iso(45))


def test_the_fields_a_moved_run_is_written_with_carry_marks_and_posts_together():
    row = {
        "reminders_sent": json.dumps([120, 15]),
        mrem.COLUMN: mrem.dump({15: mrem.entry_of(staff=a_copy()), 120: {"posted": False}}),
    }
    fields = mrem.run_fields(row, iso(200), NOW, mrem.EDIT)

    assert json.loads(fields["reminders_sent"]) == [15]
    assert mrem.posts_of(fields[mrem.COLUMN]) == {15: mrem.entry_of(staff=a_copy())}
    again = mrem.run_fields(row, iso(200), NOW, mrem.REPOST)
    assert json.loads(again["reminders_sent"]) == [] and again[mrem.COLUMN] == "{}"


def test_a_budget_counts_what_it_let_through_and_what_waits():
    budget = mrem.Budget(2)
    assert [budget.take() for _ in range(4)] == [True, True, False, False]
    assert (budget.left, budget.waiting) == (0, 2)
    assert mrem.Budget(-3).take() is False


def test_a_public_copy_remembers_who_it_names_and_one_from_before_names_nobody_in_particular():
    message = SimpleNamespace(id=77, content="Sky runs Game")
    found = mrem.copy_of(message, 9, "Sky runs Game", iso(30), people=[9001])
    assert found["people"] == [9001]
    assert "people" not in mrem.copy_of(message, 9, "Sky runs Game", iso(30))
    posts = mrem.posts_of(mrem.dump({15: mrem.entry_of(public=found, staff=a_copy())}))
    assert posts[15]["public"]["people"] == [9001] and "people" not in posts[15]["staff"]
    bad = mrem.posts_of({"15": {"public": a_copy() | {"people": "x"}}})
    assert "people" not in bad[15]["public"]

    mrem.shown(posts, 15, "public", "Sky, Mo run Game", iso(45), [9001, 9002])
    assert posts[15]["public"]["people"] == [9001, 9002]
    mrem.shown(posts, 15, "staff", "words later", iso(45))
    assert "people" not in posts[15]["staff"]
    assert mrem.names(posts, 15, "public", []) and posts[15]["public"]["people"] == []
    assert not mrem.names(posts, 15, "public", []) and not mrem.names(posts, 15, "public", None)
