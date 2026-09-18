from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace

import pytest

from black_bloc import events
from black_bloc.events import (
    APPROVED,
    CANCELLED,
    DEFAULT_DURATION_MINUTES,
    DENIED,
    DESCRIPTION_LIMIT,
    DONE,
    LIVE,
    MAX_DURATION_MINUTES,
    MOVE_TARGETS,
    OPEN_STATUSES,
    PENDING,
    STATUSES,
    SWEPT_STATUSES,
    TERMINAL_STATUSES,
    TITLE_LIMIT,
    TRANSITIONS,
    WHERE_OTHER,
    WHERE_TEXT,
    WHERE_UNSET,
    WHERE_VOICE,
    Where,
    announce_text,
    build_card,
    can_transition,
    card_buttons,
    card_footer_override,
    channel_name,
    checked_numbers,
    clamp,
    counts_line,
    counts_of,
    describe_duration,
    ends_at,
    event_line,
    golive_text,
    is_due,
    list_lines,
    may_cancel,
    mentions,
    option_label,
    parse_duration,
    pick_placeholder,
    read_where,
    review_channel_url,
    settings_lines,
    site_page_url,
    slugify,
    start_error,
    wanted_event_id,
    when_line,
    write_settings,
    zone_line,
)
from black_bloc.linkcheck import LINK_MISSING, LINK_OK, LINK_UNREACHABLE
from black_bloc.settings_store import (
    EVENTS_APPROVER_ROLE_KEY,
    EVENTS_FORUM_CHANNEL_KEY,
    EVENTS_MOVED_LINE,
    EVENTS_MOVED_LINE_KEY,
    EVENTS_POSTS_WHERE_KEY,
    EVENTS_REVIEW_MODE_KEY,
    EVENTS_ROOM_DELETE_KEY,
    EVENTS_ROOM_NOTICE_KEY,
    EVENTS_TEST_RETENTION_KEY,
    POSTS_ANNOUNCE,
    POSTS_BOTH,
    POSTS_ROOM,
    REVIEW_FORUM,
    REVIEW_ROOM,
    ROOM_DELETE_APPROVER,
    WHERE_HINT,
    WHERE_HINT_KEY,
)
from black_bloc.timezones import START_EXAMPLE, local_time, unix
from black_bloc.when_picker import WhenDraft

WHEN = datetime(2026, 9, 15, 2, 30, tzinfo=UTC)


def test_slugify_keeps_only_what_discord_allows_in_a_channel_name():
    assert slugify("Sky's Block Party!") == "sky-s-block-party"
    assert slugify("  spaced   out  ") == "spaced-out"
    assert slugify("Ünïcödé Ríde") == "unicode-ride"
    assert slugify("---") == ""
    assert slugify(None) == ""
    assert slugify("🎉🎉🎉") == ""


def test_a_channel_name_is_the_status_then_the_person_then_the_event():
    assert channel_name(PENDING, "sky", "Block Party") == "pending-sky-block-party"
    assert channel_name(APPROVED, "sky", "Block Party") == "approved-sky-block-party"
    assert channel_name(DONE, "sky", "Block Party") == "done-sky-block-party"


def test_a_channel_name_never_passes_discord_s_hundred_characters():
    name = channel_name(PENDING, "A" * 60, "B" * 90)
    assert len(name) == 100
    assert not name.endswith("-")


def test_a_nameless_event_still_gets_a_channel_name():
    assert channel_name(PENDING, "🎉", "🎉") == "pending"
    assert channel_name(PENDING, "", "") == "pending"


def test_durations_are_read_in_hours_and_minutes():
    assert parse_duration("1h30m") == 90
    assert parse_duration("2h") == 120
    assert parse_duration("45m") == 45
    assert parse_duration("1h 30m") == 90
    assert parse_duration("1H30M") == 90


def test_an_empty_duration_means_two_hours():
    assert parse_duration("") == DEFAULT_DURATION_MINUTES
    assert parse_duration(None) == DEFAULT_DURATION_MINUTES
    assert parse_duration("   ") == DEFAULT_DURATION_MINUTES


def test_a_duration_black_bloc_cannot_read_is_refused_rather_than_guessed():
    assert parse_duration("2") is None
    assert parse_duration("a while") is None
    assert parse_duration("0h0m") is None
    assert parse_duration("90") is None
    assert parse_duration(f"{MAX_DURATION_MINUTES + 1}m") is None


def test_durations_read_back_the_way_they_were_written():
    assert describe_duration(90) == "1h 30m"
    assert describe_duration(120) == "2h"
    assert describe_duration(45) == "45m"
    assert describe_duration(0) == "0m"


def test_the_status_machine_refuses_the_moves_that_would_lose_a_decision():
    assert can_transition(PENDING, APPROVED) is True
    assert can_transition(PENDING, DENIED) is True
    assert can_transition(APPROVED, LIVE) is True
    assert can_transition(LIVE, DONE) is True
    assert can_transition(DENIED, APPROVED) is True
    assert can_transition(DONE, LIVE) is False
    assert can_transition(CANCELLED, APPROVED) is False
    assert can_transition(APPROVED, DENIED) is False
    assert can_transition("nonsense", APPROVED) is False


def test_every_status_can_be_cancelled_only_while_it_is_still_open():
    assert can_transition(PENDING, CANCELLED) is True
    assert can_transition(APPROVED, CANCELLED) is True
    assert can_transition(LIVE, CANCELLED) is True
    assert can_transition(DONE, CANCELLED) is False
    assert can_transition(DENIED, CANCELLED) is False


def test_the_transition_table_names_only_real_statuses():
    assert set(TRANSITIONS) == set(STATUSES)
    for allowed in TRANSITIONS.values():
        assert set(allowed) <= set(STATUSES)


def test_a_card_carries_both_hammertime_stamps():
    card = build_card(
        event_id=4,
        title="Block Party",
        requester_id=900,
        starts_at=WHEN,
        minutes=90,
        where=Where(WHERE_OTHER, None, "the park"),
        description="bring a chair",
    )
    when = next(field.value for field in card.fields if field.name == "When")
    assert f"<t:{unix(WHEN)}:F>" in when
    assert f"<t:{unix(WHEN)}:R>" in when
    assert card.footer.text == "Event #4"


def test_a_card_clamps_what_the_requester_typed():
    card = build_card(
        event_id=1,
        title="T" * 300,
        requester_id=900,
        starts_at=WHEN,
        minutes=60,
        description="D" * 4000,
        where=Where(WHERE_OTHER, None, "L" * 300),
    )
    assert len(card.title) == TITLE_LIMIT
    assert len(card.description) == DESCRIPTION_LIMIT
    assert len(next(f.value for f in card.fields if f.name == "Where")) == 100


def test_a_card_leaves_out_what_was_not_given():
    card = build_card(
        event_id=1, title="Block Party", requester_id=900, starts_at=WHEN, minutes=60
    )
    names = [field.name for field in card.fields]
    assert "Where" not in names and "Why not" not in names
    assert card.description is None


def test_a_denied_card_says_why():
    card = build_card(
        event_id=1,
        title="Block Party",
        requester_id=900,
        starts_at=WHEN,
        minutes=60,
        status=DENIED,
        deny_reason="clashes with the marathon",
    )
    assert "clashes with the marathon" in [f.value for f in card.fields]


@pytest.mark.parametrize("status", STATUSES)
def test_every_status_has_a_colour(status):
    card = build_card(
        event_id=1,
        title="t",
        requester_id=1,
        starts_at=WHEN,
        minutes=60,
        status=status,
    )
    assert card.colour is not None


def test_only_the_configured_role_may_ever_be_pinged():
    none_allowed = mentions(None)
    assert none_allowed.everyone is False
    assert none_allowed.users is False
    assert none_allowed.roles is False

    one_allowed = mentions(42)
    assert one_allowed.everyone is False and one_allowed.users is False
    assert [role.id for role in one_allowed.roles] == [42]


def test_the_announcement_only_mentions_the_role_when_there_is_one():
    assert announce_text(None).startswith("A new event")
    assert announce_text(42).startswith("<@&42> ")
    assert golive_text("Block Party") == "**Block Party** is starting now!"
    assert golive_text("Block Party", 42).startswith("<@&42> ")


def test_a_title_full_of_pings_cannot_smuggle_one_into_the_go_live_line():
    said = golive_text("@everyone come here")
    assert "@everyone come here" in said
    assert mentions(None).everyone is False


def test_the_end_time_is_the_start_plus_the_duration():
    assert ends_at(WHEN, 90) == WHEN + timedelta(minutes=90)
    assert ends_at(WHEN, 0) == WHEN + timedelta(minutes=1)


def test_due_is_true_once_the_time_has_passed_and_never_on_a_bad_timestamp():
    now = datetime(2026, 9, 15, 3, 0, tzinfo=UTC)
    assert is_due(WHEN.isoformat(), now) is True
    assert is_due((now + timedelta(minutes=1)).isoformat(), now) is False
    assert is_due("sometime soon", now) is False
    assert is_due(None, now) is False


def test_the_start_refusal_shows_an_example_and_names_the_zone():
    said = start_error("next tuesday", "America/Phoenix", START_EXAMPLE)
    assert "next tuesday" in said
    assert START_EXAMPLE in said and "America/Phoenix" in said
    assert "My time zone" in said


def test_clamp_trims_and_cuts():
    assert clamp("  hello  ", 100) == "hello"
    assert clamp("x" * 200, 10) == "x" * 10
    assert clamp(None, 10) == ""


def test_the_announcement_only_promises_an_interested_button_when_one_exists():
    with_event = announce_text(None, has_scheduled=True, event_url="https://discord.com/events/1/2")
    assert "Interested" in with_event
    assert "https://discord.com/events/1/2" in with_event

    no_url = announce_text(None, has_scheduled=True)
    assert "Interested" in no_url and "http" not in no_url

    without = announce_text(None, has_scheduled=False)
    assert "Interested" not in without
    assert "watch this channel" in without


def test_the_announcement_keeps_its_ping_prefix_whichever_wording_it_uses():
    assert announce_text(42, has_scheduled=True, event_url="u").startswith("<@&42> ")
    assert announce_text(42, has_scheduled=False).startswith("<@&42> ")


def test_the_statuses_a_finished_channel_sweep_covers_are_the_settled_ones():
    assert set(SWEPT_STATUSES) == {DONE, DENIED, CANCELLED}
    assert not set(SWEPT_STATUSES) & set(OPEN_STATUSES)


def test_the_terminal_statuses_are_exactly_the_ones_nothing_leaves():
    assert set(TERMINAL_STATUSES) == {DONE, CANCELLED}
    for status in TERMINAL_STATUSES:
        assert TRANSITIONS[status] == ()


# --- the panel's own pure layer (wave 1) -------------------------------------------------------


class FakeRow(dict):
    """A stored event as sqlite3.Row hands it over: subscriptable by column name."""


def a_row(**fields):
    starts = fields.pop("starts", WHEN)
    row = {
        "id": 1,
        "guild_id": 7,
        "requester_id": 900,
        "title": "Block Party",
        "description": None,
        "location": "the park",
        "where_kind": None,
        "where_channel_id": None,
        "starts_at": starts.isoformat(),
        "ends_at": (starts + timedelta(minutes=90)).isoformat(),
        "status": PENDING,
        "deny_reason": None,
        "review_channel_id": None,
        "review_message_id": None,
        "card_channel_id": None,
        "announce_message_id": None,
        "scheduled_event_id": None,
        "created_at": starts.isoformat(),
    }
    row.update(fields)
    return FakeRow(row)


class FakeStore:
    def __init__(self, staff_ids=(), values=None):
        self.staff_ids = set(staff_ids)
        self.values = dict(values or {})
        self.written = []
        self.cleared = []

    def is_staff(self, actor):
        return getattr(actor, "id", actor) in self.staff_ids

    def get(self, guild_id, key):
        return self.values.get(key)

    async def set(self, guild_id, key, value, by=None):
        self.values[key] = value
        self.written.append((key, value, by))
        return value

    async def clear(self, guild_id, key):
        self.values.pop(key, None)
        self.cleared.append(key)

    def staff_roles(self, guild):
        return []


class FakeActor:
    def __init__(self, user_id):
        self.id = user_id


def test_the_card_table_only_ever_offers_a_move_the_state_machine_allows():
    """§C is data, and the data is checked against TRANSITIONS rather than trusted."""
    for status in STATUSES:
        for move in card_buttons(status):
            assert MOVE_TARGETS[move.action] in TRANSITIONS[status], (status, move)


def test_every_status_that_can_still_move_renders_at_least_one_button():
    for status in STATUSES:
        if TRANSITIONS[status]:
            assert card_buttons(status), status
        else:
            assert card_buttons(status) == ()


def test_no_state_is_one_staff_cannot_leave_while_it_is_still_open():
    """The owner's staff-final-say rule: Call it off renders in every non-terminal state."""
    for status in OPEN_STATUSES:
        assert any(move.action == "cancel" for move in card_buttons(status)), status


def test_a_denied_event_can_be_approved_after_all_while_its_room_is_still_there():
    assert [one.label for one in card_buttons(DENIED)] == ["Approve after all"]
    assert card_buttons(DENIED, room_resolves=False) == ()
    assert "cleaned up" in card_footer_override(DENIED, room_resolves=False)
    assert card_footer_override(DENIED) is None


def test_a_finished_card_says_so_in_its_footer_rather_than_showing_nothing():
    assert "nothing moves it now" in card_footer_override(DONE)
    assert "nothing moves it now" in card_footer_override(CANCELLED)
    assert card_footer_override(PENDING) is None


def test_a_card_drops_call_it_off_for_somebody_who_may_not():
    labels = [one.label for one in card_buttons(PENDING, may_cancel_here=False)]

    assert labels == ["Approve", "Deny"]


def test_the_id_parser_reads_a_hash_and_refuses_anything_else():
    assert wanted_event_id("#12") == 12
    assert wanted_event_id("12") == 12
    assert wanted_event_id("the block party") is None
    assert wanted_event_id("") is None
    assert wanted_event_id(None) is None


def test_who_may_call_one_off_is_the_requester_or_staff_and_only_while_it_is_open():
    store = FakeStore(staff_ids={1})
    row = a_row()

    assert may_cancel(store, row, FakeActor(900)) is True
    assert may_cancel(store, row, FakeActor(1)) is True
    assert may_cancel(store, row, FakeActor(2)) is False
    assert may_cancel(store, a_row(status=DENIED), FakeActor(900)) is False
    assert may_cancel(store, None, FakeActor(900)) is False


def test_one_line_per_event_names_the_number_the_status_and_when():
    said = event_line(a_row(review_channel_id=99))

    assert said.startswith("**#1** Block Party — pending")
    assert "<#99>" in said and "1h 30m" in said


def test_the_staff_list_names_who_may_approve_and_warns_when_nobody_does():
    lines = list_lines([a_row()], [])

    assert lines[0].startswith("**staff (who may approve)**")
    assert "Block Party" in lines[1]
    assert "No staff roles resolve" in lines[-1]


def test_the_counts_line_counts_only_the_open_states():
    counts = counts_of([a_row(), a_row(status=APPROVED), a_row(status=DONE)])

    assert counts == {PENDING: 1, APPROVED: 1, LIVE: 0}
    assert counts_line(counts) == "**1** pending · **1** approved · **0** live"


def test_a_select_option_names_the_id_and_the_status_and_stays_inside_discords_cap():
    label = option_label(a_row(title="x" * 200))

    assert label.startswith("#1 · pending · ")
    assert len(label) == 100


def test_the_select_placeholder_says_how_many_are_left_once_it_is_capped():
    assert pick_placeholder(3, 3) == "Pick an event…"
    assert pick_placeholder(25, 30) == "25 of 30 — the rest are on the site"


def test_the_zone_line_is_what_timezone_show_said():
    chosen = zone_line("Asia/Tokyo", chosen=True)
    default = zone_line("America/Phoenix", chosen=False)

    assert "Asia/Tokyo" in chosen and "My time zone" in chosen
    assert "not set a time zone" in default and "America/Phoenix" in default


def test_a_confirmation_shows_the_typed_time_and_the_stamp_everybody_else_reads():
    said = when_line(WHEN, "America/Phoenix")

    assert "America/Phoenix" in said
    assert f"<t:{unix(WHEN)}:F>" in said


def test_the_numbers_modal_takes_only_whole_numbers_inside_their_bounds():
    wanted, why = checked_numbers("3", "45")
    assert wanted == {"events_channel_retention_days": 3, "events_max_late_minutes": 45}
    assert why == ""

    refused, why = checked_numbers("three", "45")
    assert refused is None and "three" in why and "between" in why

    refused, why = checked_numbers("9999", "45")
    assert refused is None and "9999" in why

    refused, why = checked_numbers("3", "-1")
    assert refused is None


async def test_writing_settings_sets_what_was_given_and_clears_what_was_not():
    store = FakeStore(values={"events_ping_role_id": 4242})

    changed = await write_settings(
        store, 7, 1, {"events_mode": "on", "events_ping_role_id": None, "nonsense": 1}
    )

    assert changed == {"events_mode": "on", "events_ping_role_id": None}
    assert store.written == [("events_mode", "on", 1)]
    assert store.cleared == ["events_ping_role_id"]


def test_the_settings_lines_say_every_key_and_end_with_the_health_they_were_given():
    store = FakeStore(
        values={
            "events_mode": "on",
            "events_category_id": 50,
            "events_channel_retention_days": 3,
            "events_max_late_minutes": 45,
            "events_create_scheduled": True,
        }
    )
    guild = SimpleNamespace(id=7)

    lines = settings_lines(store, guild, ["**golive loop** — last finished never yet"])

    assert lines[0] == "**mode** — on"
    assert "<#50>" in lines[1]
    assert "not set" in lines[2]
    assert "nobody" in lines[3]
    assert "3 day(s)" in lines[5]
    assert "45 minute(s)" in lines[6]
    assert lines[-1].startswith("**golive loop**")


def test_the_site_link_needs_an_origin_and_points_at_the_events_page():
    assert site_page_url("") is None
    assert site_page_url("https://x.test/") == "https://x.test/events.html"


def test_a_review_channel_link_is_a_real_discord_url():
    assert review_channel_url(7, 99) == "https://discord.com/channels/7/99"


# The draft's own gate (`docs/info/when-picker-design.md` §2, §4 and §5b). One sentence at a
# time, the same ones `checked_fields` already says, and one name for Discord's calendar.

NOW = datetime(2026, 9, 10, 22, 7, tzinfo=UTC)


def a_draft(**kept):
    when = WhenDraft(zone="America/Phoenix", **kept.pop("when", {}))
    return events.EventDraft(when=when, duration=kept.pop("duration", "2h"), **kept)


def test_a_draft_with_no_title_says_so_before_it_says_anything_about_the_time():
    fields, why = events.draft_check(a_draft(), NOW)

    assert fields is None
    assert why == events.NO_TITLE


def test_a_titled_draft_with_no_time_says_what_is_left_to_pick():
    fields, why = events.draft_check(a_draft(title="Cookout"), NOW)

    assert fields is None
    assert "a day, an hour and a minute" in why


def test_a_complete_draft_comes_back_as_the_fields_submit_event_already_takes():
    draft = a_draft(
        title="Cookout",
        description="bring a chair",
        where=Where(WHERE_OTHER, None, "the park"),
        when={"day": date(2026, 9, 12), "hour": 19, "minute": 30},
    )

    fields, why = events.draft_check(draft, NOW)

    assert why == ""
    assert isinstance(fields, events.EventFields)
    assert fields.title == "Cookout" and fields.minutes == 120
    assert fields.where == Where(WHERE_OTHER, None, "the park")
    assert local_time("America/Phoenix", fields.starts) == "2026-09-12 19:30"


def test_the_draft_reuses_the_dst_and_past_sentences_rather_than_writing_new_ones():
    gap = a_draft(title="Cookout", when={"day": date(2027, 3, 14), "hour": 2, "minute": 30})
    gap.when.zone = "America/New_York"
    fields, why = events.draft_check(gap, NOW)
    assert fields is None and "never happens" in why

    past = a_draft(title="Cookout", when={"day": date(2020, 1, 1), "hour": 19, "minute": 30})
    fields, why = events.draft_check(past, NOW)
    assert fields is None and "already gone by" in why


def test_the_draft_card_says_what_is_missing_once_and_never_twice():
    lines = events.draft_lines(a_draft(title="Cookout"), NOW, chosen=True, why="")
    said = "\n".join(lines)

    assert "**Title** — Cookout" in said
    assert "a day, an hour and a minute" in said
    assert said.count("a day, an hour and a minute") == 1

    _fields, why = events.draft_check(a_draft(title="Cookout"), NOW)
    full = "\n".join(events.draft_lines(a_draft(title="Cookout"), NOW, chosen=True, why=why))
    assert full.count("a day, an hour and a minute") == 1
    assert events.STILL_NEEDED.format(why=why) not in full


def test_a_problem_that_is_not_the_time_gets_its_own_still_needed_line():
    draft = a_draft(when={"day": date(2026, 9, 12), "hour": 19, "minute": 30})

    _fields, why = events.draft_check(draft, NOW)
    said = "\n".join(events.draft_lines(draft, NOW, chosen=True, why=why))

    assert "**Still needed:**" in said and "needs a name" in said
    assert "Fri Sep 11" not in said and "Sat Sep 12 · 7:30 PM" in said


def test_the_draft_card_names_the_empty_boxes_rather_than_leaving_them_blank():
    said = "\n".join(events.draft_lines(a_draft(title="Cookout"), NOW, chosen=True))

    assert "**Where** — (not set)" in said
    assert "**What** — (nothing yet)" in said
    assert "**How long** — 2h" in said


def test_the_draft_where_line_says_how_to_find_a_channel_while_nothing_is_picked():
    said = "\n".join(events.draft_lines(a_draft(title="C"), NOW, chosen=True, hint=WHERE_HINT))

    assert f"**Where** — (not set) *{WHERE_HINT}*" in said


def test_the_draft_where_line_drops_the_hint_the_moment_somewhere_is_picked():
    picked = a_draft(title="C", where=Where(WHERE_VOICE, 55, ""))
    typed = a_draft(title="C", where=Where(WHERE_OTHER, None, "the park"))

    assert WHERE_HINT not in "\n".join(
        events.draft_lines(picked, NOW, chosen=True, hint=WHERE_HINT)
    )
    assert WHERE_HINT not in "\n".join(
        events.draft_lines(typed, NOW, chosen=True, hint=WHERE_HINT)
    )


def test_a_blank_hint_leaves_the_draft_where_line_exactly_as_it_was():
    def where_line_of(hint):
        lines = events.draft_lines(a_draft(title="C"), NOW, chosen=True, hint=hint)
        return next(line for line in lines if line.startswith("**Where**"))

    assert where_line_of("") == "**Where** — (not set)"
    assert where_line_of("   ") == "**Where** — (not set)"
    assert where_line_of("Type it.") == "**Where** — (not set) *Type it.*"


def test_the_what_line_is_cut_so_a_long_description_cannot_take_the_card_over():
    draft = a_draft(title="Cookout", description="x" * 500)

    said = "\n".join(events.draft_lines(draft, NOW, chosen=True))

    assert "x" * events.DRAFT_WHAT_LIMIT in said
    assert "x" * (events.DRAFT_WHAT_LIMIT + 1) not in said


def test_the_zone_line_says_the_server_chose_it_only_while_nobody_has():
    hint = "\n".join(events.draft_lines(a_draft(title="C"), NOW, chosen=False))
    own = "\n".join(events.draft_lines(a_draft(title="C"), NOW, chosen=True))

    assert "the server's default" in hint and "America/Phoenix" in hint
    assert "the server's default" not in own and "America/Phoenix" in own


def test_a_length_the_dropdown_could_not_have_produced_is_shown_as_it_was_typed():
    said = "\n".join(events.draft_lines(a_draft(title="C", duration="a while"), NOW, chosen=True))

    assert "**How long** — a while" in said


def test_the_calendar_name_puts_the_title_into_the_template_staff_typed():
    assert events.scheduled_name("{title} Feat. BaF", "Cookout") == "Cookout Feat. BaF"
    assert events.scheduled_name("BaF: {title}", " Cookout ") == "BaF: Cookout"


def test_a_long_title_is_cut_so_discord_never_refuses_the_scheduled_event():
    made = events.scheduled_name("{title} Feat. BaF", "C" * 200)

    assert len(made) == events.EVENT_NAME_LIMIT == 100


def test_a_template_that_will_not_render_falls_back_rather_than_losing_the_event():
    """Checklist 17: staff-editable text is caught, not trusted, however it got stored."""
    made = events.scheduled_name("{title} on {date}", "Cookout")

    assert made == "Cookout Feat. BaF"


def test_a_caller_may_name_its_own_fallback_so_a_raid_train_keeps_the_plain_title():
    """The default is untouched, so `/event` still falls back to the Feat. BaF wording."""
    assert events.scheduled_name("{title} on {date}", "Cookout", fallback="{title}") == "Cookout"
    assert events.scheduled_name("{title} on {date}", "Cookout") == "Cookout Feat. BaF"


def test_a_template_that_is_not_text_at_all_still_produces_a_name():
    assert events.scheduled_name(None, "Cookout") == "Cookout"
    assert events.scheduled_name("", "Cookout") == "Cookout"


class _Store:
    def __init__(self, **values):
        self.values = values

    def get(self, guild_id, key):
        return self.values.get(key)


def test_the_default_length_and_the_zone_come_from_the_guild_not_from_a_constant():
    store = _Store(
        events_default_minutes=45,
        default_timezone="Europe/London",
        timezone_choices="Europe/London, Asia/Tokyo",
        time_step_minutes=30,
    )

    assert events.default_minutes(store, 7) == 45
    assert events.guild_zone(store, 7) == "Europe/London"
    assert events.zone_choices(store, 7) == ["Europe/London", "Asia/Tokyo"]
    assert events.minute_step(store, 7) == 30


def test_a_guild_that_has_stored_nothing_lands_on_the_shipped_figures():
    store = _Store()

    assert events.default_minutes(store, 7) == events.DEFAULT_DURATION_MINUTES == 120
    assert events.guild_zone(store, 7) == "America/Phoenix"
    assert events.zone_choices(store, 7) == []
    assert events.minute_step(store, 7) == 15


# The hint above the picker (`docs/info/where-picker-design.md`, follow-up 5). Discord's native
# channel select lists one page until somebody types, and this guild has 136 channels it allows.


def test_the_where_panel_ends_on_the_sentence_that_says_to_start_typing():
    lines = events.where_panel_lines(WHERE_HINT)

    assert lines[-1] == WHERE_HINT
    assert lines[:-1] == [events.WHERE_PANEL_INTRO, events.WHERE_JOIN_NOTE]


def test_a_blank_hint_leaves_the_where_panel_with_the_words_it_always_had():
    assert events.where_panel_lines("") == [events.WHERE_PANEL_INTRO, events.WHERE_JOIN_NOTE]
    assert events.where_panel_lines("  ") == events.where_panel_lines()


def test_the_hint_is_whatever_the_guild_stored_and_is_read_at_every_render():
    store = _Store(**{WHERE_HINT_KEY: "Start typing, it is in there."})

    assert events.where_hint(store, 7) == "Start typing, it is in there."
    assert events.where_panel_lines(events.where_hint(store, 7))[-1] == (
        "Start typing, it is in there."
    )
    store.values[WHERE_HINT_KEY] = ""
    assert events.where_hint(store, 7) == ""
    assert events.where_panel_lines(events.where_hint(store, 7))[-1] == events.WHERE_JOIN_NOTE


def test_a_hint_long_enough_to_break_an_embed_is_cut_before_it_gets_there():
    store = _Store(**{WHERE_HINT_KEY: "x" * (DESCRIPTION_LIMIT + 50)})

    assert events.where_hint(store, 7) == "x" * DESCRIPTION_LIMIT


# The "Where?" picker (`docs/info/where-picker-design.md`) — one `Where` through the pure half,
# and the four kinds Discord's own create-event dialog offers.


def test_a_where_reads_back_off_the_row_it_was_written_to():
    assert read_where(a_row(where_kind=None, where_channel_id=None, location=None)) == WHERE_UNSET
    assert read_where(a_row(where_kind=WHERE_VOICE, where_channel_id=55, location=None)) == Where(
        WHERE_VOICE, 55, ""
    )
    assert read_where(a_row(where_kind=WHERE_TEXT, where_channel_id=56, location=None)) == Where(
        WHERE_TEXT, 56, ""
    )
    assert read_where(a_row(location="twitch.tv/blackbloc")) == Where(
        WHERE_OTHER, None, "twitch.tv/blackbloc"
    )


def test_a_row_written_before_schema_34_still_reads_as_a_typed_place():
    """Every event that existed before the picker had its place in `location` and nothing else."""
    old = FakeRow({"location": "the park"})

    assert read_where(old) == Where(WHERE_OTHER, None, "the park")


def test_a_channel_kind_with_no_channel_falls_back_to_whatever_was_typed():
    assert read_where(a_row(where_kind=WHERE_VOICE, where_channel_id=None)) == Where(
        WHERE_OTHER, None, "the park"
    )


def test_the_where_line_is_a_mention_for_a_channel_and_the_words_for_anything_else():
    assert events.where_line(Where(WHERE_VOICE, 55, "")) == "<#55>"
    assert events.where_line(Where(WHERE_TEXT, 56, "")) == "<#56>"
    assert events.where_line(Where(WHERE_OTHER, None, "the park")) == "the park"
    assert events.where_line(WHERE_UNSET) == ""
    assert len(events.where_line(Where(WHERE_OTHER, None, "x" * 300))) == 100


def test_a_button_label_says_the_channel_by_name_because_a_mention_would_not_render():
    channel = SimpleNamespace(id=55, name="Raid Night")

    assert events.where_button_label(WHERE_UNSET) == "Where"
    assert events.where_button_label(Where(WHERE_VOICE, 55, ""), channel) == "Where: 🔊 Raid Night"
    assert events.where_button_label(Where(WHERE_TEXT, 55, ""), channel) == "Where: #Raid Night"
    assert events.where_button_label(Where(WHERE_OTHER, None, "twitch.tv/bb")) == (
        "Where: twitch.tv/bb"
    )
    assert events.where_button_label(Where(WHERE_VOICE, 55, "")) == "Where: a channel that has gone"


def test_a_button_label_stays_inside_discords_eighty_characters():
    label = events.where_button_label(Where(WHERE_OTHER, None, "x" * 100))

    assert len(label) == events.BUTTON_LABEL_LIMIT == 80


def test_the_card_shows_a_channel_as_a_mention_and_leaves_the_field_out_when_unset():
    with_channel = build_card(
        event_id=1,
        title="Block Party",
        requester_id=900,
        starts_at=WHEN,
        minutes=60,
        where=Where(WHERE_VOICE, 55, ""),
    )
    without = build_card(
        event_id=1, title="Block Party", requester_id=900, starts_at=WHEN, minutes=60
    )

    assert next(f.value for f in with_channel.fields if f.name == "Where") == "<#55>"
    assert "Where" not in [f.name for f in without.fields]


def test_checked_fields_clamps_the_typed_place_and_refuses_nothing_new():
    fields, why = events.checked_fields(
        title="Cookout",
        description="",
        where=Where(WHERE_OTHER, None, "x" * 300),
        start=events.local_time("America/Phoenix", datetime.now(UTC) + timedelta(days=2)),
        duration="2h",
        tz_name="America/Phoenix",
        now=datetime.now(UTC),
    )

    assert why == "" and fields is not None
    assert len(fields.where.text) == events.LOCATION_LIMIT == 100

    kept, why = events.checked_fields(
        title="Cookout",
        description="",
        where=Where(WHERE_VOICE, 55, ""),
        start=events.local_time("America/Phoenix", datetime.now(UTC) + timedelta(days=2)),
        duration="2h",
        tz_name="America/Phoenix",
        now=datetime.now(UTC),
    )

    assert why == "" and kept.where == Where(WHERE_VOICE, 55, "")


def test_the_draft_card_names_the_channel_it_was_pointed_at():
    draft = a_draft(title="Cookout", where=Where(WHERE_VOICE, 55, ""))

    assert "**Where** — <#55>" in "\n".join(events.draft_lines(draft, NOW, chosen=True))


class FakeChannelType:
    def __init__(self, name):
        self.name = name


class FakeChannel:
    def __init__(self, channel_id, kind, name="general"):
        self.id = channel_id
        self.type = FakeChannelType(kind)
        self.name = name


def test_a_channel_decides_which_of_the_two_channel_kinds_it_is():
    assert events.where_of_channel(FakeChannel(55, "voice")) == Where(WHERE_VOICE, 55, "")
    assert events.where_of_channel(FakeChannel(55, "stage_voice")) == Where(WHERE_VOICE, 55, "")
    assert events.where_of_channel(FakeChannel(55, "text")) == Where(WHERE_TEXT, 55, "")
    assert events.where_of_channel(FakeChannel(55, "news")) == Where(WHERE_TEXT, 55, "")
    assert events.where_of_channel(FakeChannel(55, "category")) == WHERE_UNSET
    assert events.where_of_channel(FakeChannel(55, "forum")) == WHERE_UNSET


class FakeWhereGuild:
    def __init__(self, *channels):
        self.id = 7
        self.channels = {one.id: one for one in channels}

    def get_channel(self, channel_id):
        return self.channels.get(channel_id)


def test_the_website_door_takes_the_three_kinds_and_refuses_the_rest_in_words():
    guild = FakeWhereGuild(FakeChannel(55, "voice", "Raid Night"), FakeChannel(60, "category"))

    assert events.checked_where(guild, None, None, "") == (WHERE_UNSET, "")
    assert events.checked_where(guild, "", None, "the park") == (
        Where(WHERE_OTHER, None, "the park"),
        "",
    )
    assert events.checked_where(guild, WHERE_OTHER, None, "") == (WHERE_UNSET, "")
    assert events.checked_where(guild, WHERE_VOICE, 55, "") == (Where(WHERE_VOICE, 55, ""), "")

    refused, why = events.checked_where(guild, "nowhere", None, "")
    assert refused is None and "nowhere" in why and "voice channel" in why

    refused, why = events.checked_where(guild, WHERE_VOICE, None, "")
    assert refused is None and "has to be picked" in why

    refused, why = events.checked_where(guild, WHERE_VOICE, 999, "")
    assert refused is None and "999" in why and "cannot find" in why

    refused, why = events.checked_where(guild, WHERE_TEXT, 60, "")
    assert refused is None and "not somewhere an event can happen" in why


def test_the_channel_itself_decides_the_kind_whatever_the_website_called_it():
    """A text channel sent as `voice` would make Discord refuse the event, so it is corrected."""
    guild = FakeWhereGuild(FakeChannel(56, "text"))

    assert events.checked_where(guild, WHERE_VOICE, 56, "") == (Where(WHERE_TEXT, 56, ""), "")


# The follow-up (`docs/info/where-picker-design.md` § Follow-up): a channel AND a link together,
# so `text` means something for every kind and the link rides in the description.


def test_a_link_typed_beside_a_channel_reads_back_off_the_row_with_the_channel():
    assert read_where(
        a_row(where_kind=WHERE_VOICE, where_channel_id=55, location="twitch.tv/blackbloc")
    ) == Where(WHERE_VOICE, 55, "twitch.tv/blackbloc")
    assert read_where(
        a_row(where_kind=WHERE_TEXT, where_channel_id=56, location="twitch.tv/blackbloc")
    ) == Where(WHERE_TEXT, 56, "twitch.tv/blackbloc")


def test_the_where_line_says_the_channel_and_the_link_when_there_are_both():
    masked = "[twitch.tv/bb](https://twitch.tv/bb)"

    assert events.where_line(Where(WHERE_VOICE, 55, "twitch.tv/bb")) == f"<#55> · {masked}"
    assert events.where_line(Where(WHERE_TEXT, 56, "twitch.tv/bb")) == f"<#56> · {masked}"
    assert events.where_line(Where(WHERE_VOICE, 55, "")) == "<#55>"
    assert events.where_line(Where(WHERE_VOICE, 55, "twitch.tv/bb"), linked=False) == (
        "<#55> · twitch.tv/bb"
    )


def test_a_button_label_says_the_channel_and_the_link_in_words():
    channel = SimpleNamespace(id=55, name="Raid Night")

    assert events.where_said(Where(WHERE_VOICE, 55, "twitch.tv/bb"), channel) == (
        "🔊 Raid Night · twitch.tv/bb"
    )
    assert events.where_button_label(Where(WHERE_TEXT, 55, "twitch.tv/bb"), channel) == (
        "Where: #Raid Night · twitch.tv/bb"
    )
    assert len(events.where_button_label(Where(WHERE_VOICE, 55, "x" * 100), channel)) == 80


def test_the_website_door_keeps_what_was_typed_beside_a_channel():
    guild = FakeWhereGuild(FakeChannel(55, "voice", "Raid Night"), FakeChannel(56, "text"))

    assert events.checked_where(guild, WHERE_VOICE, 55, "twitch.tv/bb") == (
        Where(WHERE_VOICE, 55, "twitch.tv/bb"),
        "",
    )
    assert events.checked_where(guild, WHERE_VOICE, 56, "twitch.tv/bb") == (
        Where(WHERE_TEXT, 56, "twitch.tv/bb"),
        "",
    )
    assert events.checked_where(guild, WHERE_VOICE, 55, "x" * 300)[0].text == "x" * 100


def test_the_three_spellings_of_nowhere_still_collapse_to_one_unset():
    guild = FakeWhereGuild(FakeChannel(55, "voice"))

    assert events.checked_where(guild, None, None, "") == (WHERE_UNSET, "")
    assert events.checked_where(guild, WHERE_OTHER, None, "  ") == (WHERE_UNSET, "")
    assert events.checked_where(guild, "", 55, None) == (WHERE_UNSET, "")


def test_the_link_is_appended_to_the_description_only_for_a_channel_kind():
    beside = Where(WHERE_VOICE, 55, "twitch.tv/bb")

    assert events.described_with_where("bring a chair", beside) == (
        "bring a chair\n\nhttps://twitch.tv/bb"
    )
    assert events.described_with_where("", beside) == "https://twitch.tv/bb"
    assert events.described_with_where("bring a chair", beside, appended=False) == "bring a chair"
    assert (
        events.described_with_where("bring a chair", Where(WHERE_OTHER, None, "the park"))
        == "bring a chair"
    )
    assert events.described_with_where("bring a chair", WHERE_UNSET) == "bring a chair"
    assert events.described_with_where("bring a chair", Where(WHERE_VOICE, 55, "")) == (
        "bring a chair"
    )


def test_the_appended_link_wins_when_the_description_has_to_give():
    """The link is the whole reason the description was touched, so it is what survives."""
    said = events.described_with_where("d" * DESCRIPTION_LIMIT, Where(WHERE_VOICE, 55, "x" * 100))

    assert len(said) == DESCRIPTION_LIMIT
    assert said.endswith("\n\n" + "x" * 100)
    assert said.startswith("d" * (DESCRIPTION_LIMIT - 102))


# Follow-up 2 (`docs/info/where-picker-design.md` § Follow-up 2): a typed link LOOKS like a link.


def test_a_link_is_one_token_with_a_scheme_and_a_place_is_not_a_link():
    assert events.where_link("https://twitch.tv/mitchland") == "https://twitch.tv/mitchland"
    assert events.where_link("http://example.com") == "http://example.com"
    assert events.where_link("  https://twitch.tv/bb  ") == "https://twitch.tv/bb"
    assert events.where_link("HTTPS://Twitch.TV/BB") == "HTTPS://Twitch.TV/BB"
    assert events.where_link("www.twitch.tv/bb") == "https://www.twitch.tv/bb"
    assert events.where_link("the park") is None
    assert events.where_link("the.bar at 8") is None
    assert events.where_link("https://a.com https://b.com") is None
    assert events.where_link("") is None
    assert events.where_link(None) is None


def test_a_bare_scheme_with_nothing_after_it_is_not_a_link():
    """`[](https://)` is a broken control, so half a link counts as none."""
    assert events.where_link("https://") is None
    assert events.where_link("www.") is None


def test_the_masked_form_shows_the_place_and_hides_the_scheme():
    assert events.where_shown("https://twitch.tv/mitchland") == (
        "[twitch.tv/mitchland](https://twitch.tv/mitchland)"
    )
    assert events.where_shown("https://twitch.tv/bb/") == "[twitch.tv/bb](https://twitch.tv/bb/)"
    assert events.where_shown("www.twitch.tv/bb") == (
        "[www.twitch.tv/bb](https://www.twitch.tv/bb)"
    )
    assert events.where_shown("the park") == "the park"
    assert events.where_shown("") == ""


def test_a_bracket_cannot_break_the_markdown_around_a_link():
    assert events.where_shown("https://x.com/a]b") == "[x.com/ab](https://x.com/a]b)"
    assert events.where_shown("https://x.com/a(b)c") == "https://x.com/a(b)c"


def test_the_masked_label_is_clamped_like_every_other_typed_place():
    said = events.where_shown("https://x.com/" + "y" * 300)
    label, _, href = said[1:-1].partition("](")

    assert len(href) == events.LOCATION_LIMIT == 100
    assert label == "x.com/" + "y" * 86


def test_the_where_line_masks_a_link_for_an_embed_and_leaves_it_bare_for_a_reader():
    where = Where(WHERE_VOICE, 55, "https://twitch.tv/bb")

    assert events.where_line(where) == "<#55> · [twitch.tv/bb](https://twitch.tv/bb)"
    assert events.where_line(where, linked=False) == "<#55> · https://twitch.tv/bb"
    assert events.where_line(Where(WHERE_OTHER, None, "https://twitch.tv/bb")) == (
        "[twitch.tv/bb](https://twitch.tv/bb)"
    )
    assert events.where_line(Where(WHERE_OTHER, None, "the park"), linked=False) == "the park"


def test_the_card_s_where_field_carries_the_masked_link():
    card = build_card(
        event_id=1,
        title="Block Party",
        requester_id=900,
        starts_at=WHEN,
        minutes=60,
        where=Where(WHERE_OTHER, None, "https://twitch.tv/bb"),
    )

    assert next(f.value for f in card.fields if f.name == "Where") == (
        "[twitch.tv/bb](https://twitch.tv/bb)"
    )


def test_the_draft_line_carries_the_masked_link_too():
    draft = a_draft(title="Cookout", where=Where(WHERE_VOICE, 55, "https://twitch.tv/bb"))

    assert "**Where** — <#55> · [twitch.tv/bb](https://twitch.tv/bb)" in "\n".join(
        events.draft_lines(draft, NOW, chosen=True)
    )


def test_the_scheduled_event_s_description_keeps_the_bare_url():
    """Discord auto-links a description; a masked link in one is not reliable."""
    said = events.described_with_where("bring a chair", Where(WHERE_VOICE, 55, "https://tw.tv/b"))

    assert said == "bring a chair\n\nhttps://tw.tv/b"


def test_a_button_label_never_masks_a_link_because_a_label_cannot_carry_one():
    assert events.where_said(Where(WHERE_OTHER, None, "https://twitch.tv/bb")) == (
        "https://twitch.tv/bb"
    )
    assert events.where_button_label(Where(WHERE_OTHER, None, "https://twitch.tv/bb")) == (
        "Where: https://twitch.tv/bb"
    )


# Follow-up 4 (`docs/info/where-picker-design.md` § Follow-up 4): a shorthand becomes a link.


def test_a_bare_host_is_a_link_with_or_without_a_path():
    assert events.where_link("twitch.tv/skyaiva") == "https://twitch.tv/skyaiva"
    assert events.where_link("kick.com") == "https://kick.com"
    assert events.where_link("youtube.com/@skyaiva") == "https://youtube.com/@skyaiva"
    assert events.where_link("discord.gg/baf") == "https://discord.gg/baf"
    assert events.where_link("TWITCH.TV/SkyAiva") == "https://TWITCH.TV/SkyAiva"
    assert events.where_link("  twitch.tv/skyaiva  ") == "https://twitch.tv/skyaiva"


def test_a_number_and_a_one_letter_tld_are_not_hosts():
    """`8.30` is a time and `e.g` is an abbreviation; a TLD is letters, and at least two."""
    assert events.where_link("8.30") is None
    assert events.where_link("e.g") is None
    assert events.where_link("7.30pm") is None
    assert events.where_link("meet.me at the.bar") is None
    assert events.where_link("the park") is None


def test_a_shorthand_becomes_the_link_it_means():
    assert events.where_typed("ttv/skyaiva") == "https://twitch.tv/skyaiva"
    assert events.where_typed("ttv skyaiva") == "https://twitch.tv/skyaiva"
    assert events.where_typed("TTV/SkyAiva") == "https://twitch.tv/SkyAiva"
    assert events.where_typed("kick/skyaiva") == "https://kick.com/skyaiva"
    assert events.where_typed("discord/baf") == "https://discord.gg/baf"


def test_a_leading_at_is_stripped_so_a_template_never_renders_two():
    assert events.where_typed("yt @skyaiva") == "https://youtube.com/@skyaiva"
    assert events.where_typed("yt skyaiva") == "https://youtube.com/@skyaiva"
    assert events.where_typed("ig/@skyaiva") == "https://instagram.com/skyaiva"


def test_anything_that_is_not_two_readable_parts_is_left_as_words():
    assert events.where_typed("nope/skyaiva") == "nope/skyaiva"
    assert events.where_typed("ttv/sky/aiva") == "ttv/sky/aiva"
    assert events.where_typed("ttv sky aiva") == "ttv sky aiva"
    assert events.where_typed("ttv/") == "ttv/"
    assert events.where_typed("ttv @") == "ttv @"
    assert events.where_typed("the park") == "the park"
    assert events.where_typed("") == ""
    assert events.where_typed(None) == ""
    assert events.where_typed("ttv/" + "x" * 65) == "ttv/" + "x" * 65


def test_a_link_typed_in_full_is_never_run_through_the_table():
    assert events.where_typed("https://twitch.tv/skyaiva") == "https://twitch.tv/skyaiva"
    assert events.where_typed("twitch.tv/skyaiva") == "twitch.tv/skyaiva"


def test_the_table_is_staff_editable_so_where_typed_takes_its_own():
    mine = "cb=https://caffeine.tv/{handle}"

    assert events.where_typed("cb/skyaiva", mine) == "https://caffeine.tv/skyaiva"
    assert events.where_typed("ttv/skyaiva", mine) == "ttv/skyaiva"
    assert events.where_typed("cb/skyaiva", "") == "cb/skyaiva"


def test_the_website_door_normalises_a_shorthand_too():
    guild = FakeWhereGuild(FakeChannel(55, "voice", "Raid Night"))

    assert events.checked_where(guild, WHERE_OTHER, None, "ttv skyaiva") == (
        Where(WHERE_OTHER, None, "https://twitch.tv/skyaiva"),
        "",
    )
    assert events.checked_where(guild, WHERE_VOICE, 55, "yt @skyaiva") == (
        Where(WHERE_VOICE, 55, "https://youtube.com/@skyaiva"),
        "",
    )
    assert events.checked_where(guild, WHERE_OTHER, None, "the park") == (
        Where(WHERE_OTHER, None, "the park"),
        "",
    )


def test_a_bare_host_stored_before_this_build_still_reaches_the_calendar_with_its_scheme():
    """The row keeps what was typed; the description is where the scheme is put back."""
    said = events.described_with_where("bring a chair", Where(WHERE_VOICE, 55, "twitch.tv/bb"))

    assert said == "bring a chair\n\nhttps://twitch.tv/bb"
    assert events.described_with_where("bring a chair", Where(WHERE_VOICE, 55, "the park")) == (
        "bring a chair\n\nthe park"
    )


def test_the_draft_s_where_line_carries_the_note_and_the_row_never_does():
    draft = a_draft(title="Cookout", where=Where(WHERE_OTHER, None, "https://twitch.tv/bb"))
    draft.where_note = "that page answered 404 — check the name"

    assert "**Where** — [twitch.tv/bb](https://twitch.tv/bb) — ⚠️ that page answered 404" in (
        "\n".join(events.draft_lines(draft, NOW, chosen=True))
    )
    assert events.EventDraft().where_note == ""
    assert "where_note" not in events.described_with_where("x", draft.where)


def test_a_draft_with_nowhere_set_still_says_so_before_the_note():
    draft = a_draft(title="Cookout")
    draft.where_note = "nothing.example did not answer within 2 s"

    assert "**Where** — (not set) — ⚠️ nothing.example did not answer" in "\n".join(
        events.draft_lines(draft, NOW, chosen=True)
    )


def test_the_note_names_the_trouble_and_says_the_link_was_kept():
    assert events.where_note(LINK_MISSING, "https://youtube.com/@nope", 2) == (
        "that page answered 404 — check the name"
    )
    assert events.where_note(LINK_UNREACHABLE, "https://slow.example/x", 2) == (
        "slow.example did not answer within 2 s — the link is kept as typed"
    )
    assert events.where_note(LINK_OK, "https://twitch.tv/bb", 2) == ""


def test_the_refusing_mode_names_the_link_the_trouble_and_the_way_out():
    missing = events.where_refused(LINK_MISSING, "https://youtube.com/@nope", 2)

    assert "https://youtube.com/@nope" in missing
    assert "404" in missing and "misspelt" in missing
    assert "events_where_link_check" in missing and "warn" in missing
    assert "nowhere was saved and the old place was kept" in missing

    unreachable = events.where_refused(LINK_UNREACHABLE, "https://slow.example/x", 3)

    assert "https://slow.example/x" in unreachable and "3 seconds" in unreachable
    assert "events_where_link_check" in unreachable
    assert not any(said.isdigit() and len(said) == 3 for said in unreachable.split())


# Follow-up 3 (`docs/info/where-picker-design.md` § Follow-up 3): a refused event's room counts
# from the decision, not from a start that was never going to happen.


def test_a_finished_event_s_room_counts_from_when_it_ended():
    row = a_row(status=DONE, decided_at=WHEN.isoformat())

    assert events.swept_anchor(row) == WHEN + timedelta(minutes=90)


def test_a_denied_or_cancelled_room_counts_from_the_decision_instead():
    decided = WHEN - timedelta(days=30)
    for status in (DENIED, CANCELLED):
        assert events.swept_anchor(a_row(status=status, decided_at=decided.isoformat())) == decided


def test_a_decision_with_no_stamp_falls_back_to_the_end_and_then_to_the_row_s_birth():
    assert events.swept_anchor(a_row(status=DENIED, decided_at=None)) == WHEN + timedelta(
        minutes=90
    )
    assert events.swept_anchor(a_row(status=DENIED, decided_at=None, ends_at=None)) == WHEN
    assert events.swept_anchor(a_row(status=DENIED, decided_at="", ends_at="soon")) == WHEN


def test_a_row_with_nothing_readable_on_it_has_no_anchor_and_is_left_alone():
    assert events.swept_anchor(a_row(status=DONE, ends_at=None)) is None
    assert events.swept_anchor(a_row(status=DONE, ends_at="whenever")) is None
    assert (
        events.swept_anchor(a_row(status=DENIED, decided_at=None, ends_at=None, created_at=None))
        is None
    )


# Event rooms (`docs/info/events-rooms-design.md`): where an event's posts go, who may remove
# its room, and the words the notice message says how long it has left in.


def test_where_an_events_posts_go_defaults_to_its_own_room():
    store = FakeStore()

    assert events.posts_where(store, 7) == POSTS_ROOM
    assert events.posts_in_room(store, 7) is True
    assert events.posts_in_announce(store, 7) is False


@pytest.mark.parametrize(
    ("value", "room", "announce"),
    [
        (POSTS_ROOM, True, False),
        (POSTS_ANNOUNCE, False, True),
        (POSTS_BOTH, True, True),
    ],
)
def test_each_value_opens_exactly_the_doors_it_names(value, room, announce):
    store = FakeStore(values={EVENTS_POSTS_WHERE_KEY: value})

    assert events.posts_in_room(store, 7) is room
    assert events.posts_in_announce(store, 7) is announce


def test_the_notice_says_minutes_while_testing_and_days_when_it_is_live():
    store = FakeStore(
        values={"events_channel_retention_days": 7, EVENTS_TEST_RETENTION_KEY: 5}
    )

    assert events.room_keeps(store, 7, testing=True) == "5 minutes after it ends"
    assert events.room_keeps(store, 7, testing=False) == "7 days after it ends"


def test_staff_may_always_remove_a_room_and_so_may_the_approver_role():
    staff_only = FakeStore(staff_ids={1})
    lead = FakeActor(1)
    lead.roles = []
    other = FakeActor(2)
    other.roles = [SimpleNamespace(id=99)]

    assert events.may_delete_room(staff_only, 7, lead) is True
    assert events.may_delete_room(staff_only, 7, other) is False

    approver = FakeStore(
        staff_ids={1},
        values={EVENTS_ROOM_DELETE_KEY: ROOM_DELETE_APPROVER, EVENTS_APPROVER_ROLE_KEY: 99},
    )

    assert events.may_delete_room(approver, 7, other) is True
    assert events.may_delete_room(approver, 7, lead) is True


def test_an_approver_mode_with_no_role_set_falls_back_to_staff():
    store = FakeStore(staff_ids={1}, values={EVENTS_ROOM_DELETE_KEY: ROOM_DELETE_APPROVER})
    other = FakeActor(2)
    other.roles = [SimpleNamespace(id=99)]

    assert events.room_delete_role_id(store, 7) is None
    assert events.may_delete_room(store, 7, other) is False


def test_the_cancel_reason_a_removed_room_gives_reads_as_one_sentence():
    said = events.DM_CANCELLED.format(
        title="Block Party", guild="Black Bloc", why=events.CANCEL_WHY["room_deleted"]
    ) + events.CANCEL_NOTE.format(note="we are done in here")

    assert "has been cancelled — staff removed its room." in said
    assert "The reason given was: we are done in here" in said


def test_the_rooms_page_says_all_four_keys_in_words():
    store = FakeStore(
        values={
            EVENTS_POSTS_WHERE_KEY: POSTS_BOTH,
            EVENTS_ROOM_DELETE_KEY: ROOM_DELETE_APPROVER,
            EVENTS_APPROVER_ROLE_KEY: 99,
            EVENTS_ROOM_NOTICE_KEY: True,
            "events_channel_retention_days": 7,
            EVENTS_TEST_RETENTION_KEY: 5,
        }
    )

    lines = events.rooms_lines(store, SimpleNamespace(id=7))

    assert "both the room and the announce channel" in lines[0]
    assert ROOM_DELETE_APPROVER in lines[1]
    assert "<@&99>" in lines[2]
    assert "posted in every room" in lines[3]
    assert "5 minutes after it ends" in lines[4]


def test_an_approval_that_only_reached_the_room_does_not_claim_nothing_was_announced():
    said = events.approve_extra(None, None, where=POSTS_ROOM)

    assert "the event's own room" in said
    assert "Nothing was announced" not in said
    assert "Nothing was announced" in events.approve_extra(None, None, where=POSTS_ANNOUNCE)


# --- events as a forum post (events-forum-design.md §A, §C) -----------------------------


class FakeTag:
    def __init__(self, tag_id, name):
        self.id = tag_id
        self.name = name


def a_forum(names=STATUSES):
    return SimpleNamespace(
        id=555, available_tags=[FakeTag(i, name) for i, name in enumerate(names, start=1)]
    )


def test_a_row_from_before_schema_45_reads_as_a_room_and_never_as_a_post():
    assert events.review_kind(a_row()) == events.ROOM
    assert events.review_kind(a_row(review_kind=None)) == events.ROOM
    assert events.review_kind(a_row(review_kind="room")) == events.ROOM
    assert events.review_kind(a_row(review_kind="post")) == events.POST
    assert events.review_kind(a_row(review_kind="nonsense")) == events.ROOM


def test_the_forum_carries_one_tag_for_every_status_an_event_can_hold():
    """The design named five; `events.py` holds six, and the tags match it one for one."""
    assert [tag.name for tag in events.forum_tags()] == list(STATUSES)
    assert set(events.FORUM_TAG_EMOJI) == set(STATUSES)


def test_a_post_wears_the_one_tag_its_status_names_and_nothing_when_the_forum_lacks_it():
    forum = a_forum()

    assert [tag.name for tag in events.tags_for_status(forum, APPROVED)] == [APPROVED]
    assert events.tags_for_status(forum, "never heard of it") == []
    assert events.tags_for_status(a_forum(names=(PENDING,)), DONE) == []
    assert events.tags_for_status(None, PENDING) == []


def test_only_a_settled_event_archives_its_post():
    for status in (DENIED, DONE, CANCELLED):
        assert events.archives_at(status) is True
    for status in (PENDING, APPROVED, LIVE):
        assert events.archives_at(status) is False


def test_a_post_already_wearing_the_right_tag_costs_no_second_edit():
    tag = FakeTag(1, PENDING)
    place = SimpleNamespace(applied_tags=[tag], archived=False)

    assert events.post_is_right(place, [tag], False) is True
    assert events.post_is_right(place, [tag], True) is False
    assert events.post_is_right(place, [FakeTag(2, DONE)], False) is False


def test_the_posts_name_is_the_title_and_the_day_it_happens():
    store = FakeStore(values={"default_timezone": "America/Phoenix"})
    row = a_row(starts=datetime(2026, 9, 20, 2, 30, tzinfo=UTC))

    assert events.post_title(store, row) == "Block Party · 2026-09-19"


def test_a_post_name_with_an_unreadable_start_is_still_the_title():
    store = FakeStore()
    row = a_row()
    row["starts_at"] = "not a time"

    assert events.post_title(store, row) == "Block Party"


def test_a_post_name_never_outgrows_what_discord_takes():
    store = FakeStore(values={"default_timezone": "UTC"})
    row = a_row(title="x" * 300)

    assert len(events.post_title(store, row)) <= events.CHANNEL_NAME_LIMIT


def test_events_are_reviewed_in_a_room_until_somebody_says_otherwise():
    store = FakeStore()

    assert events.review_mode(store, 7) == REVIEW_ROOM
    assert events.reviews_in_forum(store, 7) is False
    assert events.forum_channel_id(store, 7) is None

    store.values[EVENTS_REVIEW_MODE_KEY] = REVIEW_FORUM
    store.values[EVENTS_FORUM_CHANNEL_KEY] = 909

    assert events.reviews_in_forum(store, 7) is True
    assert events.forum_channel_id(store, 7) == 909


def test_a_forum_key_that_is_not_a_number_is_read_as_no_forum_rather_than_raising():
    store = FakeStore(values={EVENTS_FORUM_CHANNEL_KEY: "nonsense"})

    assert events.forum_channel_id(store, 7) is None


def test_every_sentence_the_delete_button_says_names_the_place_it_is_on():
    room = events.PLACE_WORDS[events.ROOM]
    post = events.PLACE_WORDS[events.POST]

    assert post.button == "Delete this post" and room.button == "Delete this room"
    for said in (post.not_staff, post.not_this_event, post.already_gone, post.deleted):
        assert "post" in said and "this room" not in said
    assert post.cancel_reason == "post_deleted"
    assert events.CANCEL_WHY[post.cancel_reason] == "staff removed its post."


def test_removing_a_post_never_cancels_an_event_twice_over():
    """`post_deleted` joins the quiet reasons for the same reason `room_deleted` is there."""
    assert "post_deleted" in events.ROOM_QUIET_REASONS


def test_the_delete_message_counts_down_in_a_room_and_says_archive_in_a_live_post():
    store = FakeStore(
        values={"events_channel_retention_days": 7, EVENTS_TEST_RETENTION_KEY: 5}
    )
    room = a_row()
    post = a_row(review_kind="post")

    assert "7 days after it ends" in events.notice_said(store, 7, room, testing=False)
    assert "5 minutes after it ends" in events.notice_said(store, 7, room, testing=True)
    assert events.notice_said(store, 7, post, testing=False) == events.POST_NOTICE
    assert "5 minutes after it ends" in events.notice_said(store, 7, post, testing=True)


def test_an_approval_in_the_forum_says_the_post_not_the_room():
    said = events.approve_extra(None, None, where=POSTS_ROOM, kind=events.POST)

    assert "own post" in said and "own room" not in said


def test_the_forum_page_says_the_mode_the_forum_and_what_is_missing():
    store = FakeStore(values={EVENTS_REVIEW_MODE_KEY: REVIEW_FORUM})

    lines = events.forum_lines(store, SimpleNamespace(id=7))

    assert "one post in the events forum" in lines[0]
    assert "not set" in lines[1]
    assert "only reaches the ones" in lines[2]
    assert events.MAKE_THE_FORUM in lines[-1]


def test_the_forum_page_stops_warning_once_the_forum_is_there():
    store = FakeStore(
        values={EVENTS_REVIEW_MODE_KEY: REVIEW_FORUM, EVENTS_FORUM_CHANNEL_KEY: 909}
    )

    lines = events.forum_lines(store, SimpleNamespace(id=7))

    assert "<#909>" in lines[1]
    assert not any(events.MAKE_THE_FORUM in line for line in lines)


def test_room_mode_with_no_forum_is_not_a_warning():
    lines = events.forum_lines(FakeStore(), SimpleNamespace(id=7))

    assert "a text channel of its own" in lines[0]
    assert not any(events.MAKE_THE_FORUM in line for line in lines)


def test_a_blank_forum_is_refused_in_words_that_differ_for_staff_and_a_member():
    assert events.MAKE_THE_FORUM in events.FORUM_NOT_SET_STAFF
    assert "events_review_mode" in events.FORUM_NOT_SET_STAFF
    assert "Staff have not set up the events forum yet" in events.FORUM_NOT_SET_MEMBER
    assert "events_forum_channel_id" not in events.FORUM_NOT_SET_MEMBER


def test_the_two_forum_keys_reach_the_write_path_the_panel_uses():
    assert EVENTS_REVIEW_MODE_KEY in events.SETTINGS_KEYS
    assert EVENTS_FORUM_CHANNEL_KEY in events.SETTINGS_KEYS


def test_the_card_link_says_which_kind_of_place_it_opens():
    assert events.PLACE_LINK_BUTTON[events.ROOM] == "The review channel"
    assert events.PLACE_LINK_BUTTON[events.POST] == "The review post"


# --- §H: what the doors render on, and the words the move says -------------------------


def a_forum_store(**values):
    return FakeStore(
        staff_ids=(1,),
        values={EVENTS_REVIEW_MODE_KEY: "forum", EVENTS_FORUM_CHANNEL_KEY: 555, **values},
    )


def a_room_row(**fields):
    return a_row(review_channel_id=4242, review_kind=events.ROOM, **fields)


def test_only_an_open_room_with_a_forum_to_go_to_offers_the_move():
    store = a_forum_store()

    assert events.may_move_to_forum(store, 7, a_room_row()) is True
    assert events.may_move_to_forum(store, 7, a_room_row(status=APPROVED)) is True
    assert events.may_move_to_forum(store, 7, a_room_row(status=LIVE)) is True


@pytest.mark.parametrize("status", (DENIED, DONE, CANCELLED))
def test_a_settled_event_is_never_offered_the_move(status):
    assert events.may_move_to_forum(a_forum_store(), 7, a_room_row(status=status)) is False


def test_a_post_a_roomless_row_and_a_missing_row_are_never_offered_the_move():
    store = a_forum_store()

    assert events.may_move_to_forum(store, 7, None) is False
    assert events.may_move_to_forum(store, 7, a_row(review_kind=events.POST)) is False
    assert events.may_move_to_forum(store, 7, a_row()) is False
    assert (
        events.may_move_to_forum(store, 7, a_row(review_channel_id=4242, review_kind="post"))
        is False
    )


def test_room_mode_or_a_blank_forum_hides_the_move_even_on_an_open_room():
    """§H: the doors render only while the mode is forum AND a forum is set."""
    assert (
        events.may_move_to_forum(
            a_forum_store(**{EVENTS_REVIEW_MODE_KEY: "room"}), 7, a_room_row()
        )
        is False
    )
    assert (
        events.may_move_to_forum(
            a_forum_store(**{EVENTS_FORUM_CHANNEL_KEY: None}), 7, a_room_row()
        )
        is False
    )


def test_the_moved_line_is_the_default_until_staff_change_it():
    store = a_forum_store()

    assert events.moved_line(store, 7, 99) == (
        "This event now lives in its own post: <#99>. This room is being removed."
    )
    store.values[EVENTS_MOVED_LINE_KEY] = "We are over in {post} now."
    assert events.moved_line(store, 7, 99) == "We are over in <#99> now."


def test_a_moved_line_whose_braces_went_wrong_falls_back_rather_than_raising():
    """Checklist 17: staff-editable text never takes the feature down with it."""
    store = a_forum_store(**{EVENTS_MOVED_LINE_KEY: "Off to {nowhere} we go."})

    assert events.moved_line(store, 7, 99) == EVENTS_MOVED_LINE.format(post="<#99>")


def test_every_refusal_the_move_gives_says_what_to_do_about_it():
    assert "already reviewed in a post" in events.MOVE_ALREADY_A_POST
    assert "{status}" in events.MOVE_SETTLED
    assert events.MAKE_THE_FORUM in events.MOVE_NO_FORUM
    assert "events_forum_channel_id" in events.MOVE_NO_FORUM
    assert "test mode" in events.MOVE_REFUSED_TEST
    assert "Create Posts" in events.MOVE_FAILED
    assert "Call it off" in events.MOVE_NOT_STAFF
    assert set(events.MOVE_WHY) == {"no_forum", "test_mode", "failed"}


def test_the_moved_line_key_reaches_the_write_path_the_panel_uses():
    assert EVENTS_MOVED_LINE_KEY in events.SETTINGS_KEYS


def test_the_forum_page_names_the_move_and_shows_the_line_it_leaves():
    lines = events.forum_lines(a_forum_store(), SimpleNamespace(id=7))

    assert any(events.MOVE_TO_FORUM_BUTTON in line for line in lines)
    assert any("{post}" in line for line in lines)
