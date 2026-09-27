import re
from datetime import UTC, datetime, timedelta

from black_bloc import marathon as mt
from black_bloc import marathon_inbox as mi

NOW = datetime(2026, 9, 26, 18, 0, tzinfo=UTC)


def row(**given):
    return {"tracked_at": None, "ignored_at": None, "active": 1, **given}


def test_a_row_is_found_tracked_ignored_or_archived_and_ignoring_wins_over_tracking():
    assert mi.state_of(row()) == mi.FOUND
    assert mi.state_of(row(tracked_at="x")) == mi.TRACKED
    assert mi.state_of(row(ignored_at="x")) == mi.IGNORED
    assert mi.state_of(row(tracked_at="x", ignored_at="y")) == mi.IGNORED
    assert not mi.is_tracked(row(tracked_at="x", ignored_at="y"))
    assert mi.state_of(row(tracked_at="x"), archived=True) == mi.ARCHIVED
    assert mi.state_of(row(archived_at="z")) == mi.ARCHIVED


def test_each_state_offers_only_the_moves_that_change_something():
    assert mi.moves_of(row()) == (mi.TRACK, mi.IGNORE)
    assert mi.moves_of(row(tracked_at="x")) == (mi.UNTRACK,)
    assert mi.moves_of(row(ignored_at="x")) == (mi.ANYWAY,)
    assert mi.moves_of(row(), archived=True) == ()
    assert [one.label for one in mi.panel_moves(row())] == ["Track", "Ignore"]
    assert all(one.row == 4 for one in mi.panel_moves(row()))


def test_every_custom_id_round_trips_through_the_template():
    for action in mi.ACTIONS:
        found = re.fullmatch(mi.INBOX_TEMPLATE, mi.custom_id(12, action))
        assert found and found["marathon_id"] == "12" and found["action"] == action


def test_the_home_follows_the_mode_and_off_has_none():
    assert mi.home_of("on") == mi.HOME_ON
    assert mi.home_of("shadow") == mi.HOME_SHADOW
    assert mi.home_of("off") is None


def test_an_ignored_marathon_is_read_on_the_far_cadence_only():
    last = (NOW - timedelta(hours=5)).isoformat()
    assert mi.ignored_read_due(row(last_fetched_at=None), NOW, 24)
    assert not mi.ignored_read_due(row(last_fetched_at=last), NOW, 24)
    assert mi.ignored_read_due(row(last_fetched_at=last), NOW, 4)
    assert not mi.ignored_read_due(row(active=0, last_fetched_at=None), NOW, 4)


def test_a_thread_name_is_one_line_within_discords_limit_and_never_empty():
    assert mi.thread_name("  Fall   Fest\n2026 ") == "Fall Fest 2026"
    assert len(mi.thread_name("x" * 300)) == mi.THREAD_NAME_LIMIT
    assert mi.thread_name("   ") == mi.THREAD_NAME_FALLBACK


def test_links_need_every_id_and_dates_render_as_discord_times():
    assert mi.channel_url(1, 2) == "https://discord.com/channels/1/2"
    assert mi.channel_url(1, None) is None
    assert mi.message_url(1, 2, 3) == "https://discord.com/channels/1/2/3"
    assert mi.message_url(1, 2, None) is None
    assert mi.when_of(NOW.isoformat()) == f"<t:{int(NOW.timestamp())}:d>"
    assert mi.when_of(None) == "" and mi.date_of(NOW.isoformat()) == "26 Sep 2026"


def test_a_posted_message_and_a_fresh_render_compare_by_what_they_show():
    class Field:
        def __init__(self, name, value):
            self.name, self.value = name, value

    class Embed:
        title = "SS4C"
        fields = [Field("When", "soon")]

    assert mi.comparable("hi", [Embed()]) == ("hi", "SS4C", (("When", "soon"),))
    assert mi.comparable(None, []) == ("", "", ())


def test_the_schedule_view_offers_post_it_now_only_while_no_inbox_message_is_up():
    poll = mt.POLL_MOVE._replace(row=2)
    assert mi.schedule_moves(row(inbox_message_id=None)) == (
        mi.LINK_MOVE,
        poll,
        mi.POST_NOW_MOVE,
        mt.BACK_MOVE,
    )
    assert mi.schedule_moves(row(inbox_message_id=9)) == (mi.LINK_MOVE, poll, mt.BACK_MOVE)
    archived = row(inbox_message_id=None, archived_at="2026-09-26T00:00:00+00:00")
    assert mi.POST_NOW_MOVE not in mi.schedule_moves(archived)
