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
        location="the park",
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
        location="L" * 300,
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
        location="the park",
        when={"day": date(2026, 9, 12), "hour": 19, "minute": 30},
    )

    fields, why = events.draft_check(draft, NOW)

    assert why == ""
    assert isinstance(fields, events.EventFields)
    assert fields.title == "Cookout" and fields.minutes == 120
    assert fields.location == "the park"
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
