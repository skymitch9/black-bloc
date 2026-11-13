from datetime import UTC, datetime, timedelta

import pytest

from black_bloc import rolegrants as grants
from black_bloc import rolemenus as rm
from black_bloc.config import load_settings
from black_bloc.settings_store import SettingsStore

GUILD = 7
OPTIONS_MAX = 25


def actions(moves):
    return [move.action for move in moves]


def labels(moves):
    return [move.label for move in moves]


def row(name, title="Title", mode="multiple", message_id=None, menu_id=1):
    return {"id": menu_id, "name": name, "title": title, "mode": mode, "message_id": message_id}


def option(role_id, label, emoji=None):
    return {"role_id": role_id, "label": label, "emoji": emoji}


def grant(user_id=900, role_id=5, expires_at=None, removed_at=None, grant_id=1):
    return {
        "id": grant_id,
        "user_id": user_id,
        "role_id": role_id,
        "expires_at": expires_at,
        "removed_at": removed_at,
    }


# --- the root table ------------------------------------------------------------------------------


@pytest.mark.parametrize("has_menus", [True, False])
@pytest.mark.parametrize("picking_on", [True, False])
def test_the_root_always_offers_the_same_moves_whatever_the_mode(has_menus, picking_on):
    """The mode never takes a control off the ROOT — the button that turns it back on is here."""
    found = actions(rm.root_buttons(has_menus=has_menus, picking_on=picking_on))

    assert found == [rm.NEW_MENU, rm.SEED, rm.GRANTS, rm.MODE, rm.LOGS, rm.REFRESH]


def test_the_mode_button_says_what_it_will_do():
    assert rm.mode_move(True).label == rm.MODE_OFF_LABEL
    assert rm.mode_move(False).label == rm.MODE_ON_LABEL


def test_waiting_on_staff_renders_only_when_something_is_waiting():
    with_none = actions(rm.root_buttons(has_menus=True, picking_on=True, pending=0))
    with_two = rm.root_buttons(has_menus=True, picking_on=True, pending=2)

    assert rm.REQUESTS not in with_none
    assert rm.REQUESTS in actions(with_two)
    assert "Waiting on staff (2)…" in labels(with_two)


# --- the menu card -------------------------------------------------------------------------------


def card(**kwargs):
    wanted = {
        "posted": False,
        "options": 2,
        "menu_mode": "multiple",
        "picking_on": True,
        "approval": False,
        "options_max": OPTIONS_MAX,
    }
    return rm.menu_buttons(**(wanted | kwargs))


def test_a_full_menu_stops_offering_another_role():
    assert rm.ADD_ROLE in actions(card(options=OPTIONS_MAX - 1))
    assert rm.ADD_ROLE not in actions(card(options=OPTIONS_MAX))


def test_post_it_is_absent_on_a_staff_menu_on_an_empty_one_and_while_the_mode_is_off():
    assert rm.POST in actions(card())
    assert rm.POST not in actions(card(menu_mode="staff"))
    assert rm.POST not in actions(card(options=0))
    assert rm.POST not in actions(card(picking_on=False))


def test_post_it_becomes_move_it_once_the_menu_is_posted():
    assert rm.POST_LABEL in labels(card(posted=False))
    assert rm.MOVE_LABEL in labels(card(posted=True))


def test_take_it_down_needs_a_posted_panel():
    assert rm.TAKE_DOWN not in actions(card(posted=False))
    assert rm.TAKE_DOWN in actions(card(posted=True))


def test_handing_roles_out_needs_options_and_survives_the_mode_going_off():
    """§C6 of the pings remake: the mode governs MEMBER picking, so a staff hand-out is not
    its business. Post it still goes; Hand roles out… stays whatever the mode says."""
    assert rm.HAND_OUT in actions(card(menu_mode="staff"))
    assert rm.HAND_OUT not in actions(card(options=0))
    assert rm.HAND_OUT in actions(card(picking_on=False))


def test_the_approval_button_says_what_it_will_do():
    assert rm.APPROVAL_ON_LABEL in labels(card(approval=False))
    assert rm.APPROVAL_OFF_LABEL in labels(card(approval=True))


def test_every_menu_card_can_be_left_and_deleted():
    for state in (card(), card(options=0), card(picking_on=False), card(menu_mode="staff")):
        assert rm.DELETE in actions(state)
        assert rm.BACK in actions(state)


def test_no_control_sits_outside_discords_five_rows():
    for state in (card(), card(posted=True), card(options=0), card(picking_on=False)):
        assert all(0 <= move.row <= 4 for move in state)
    assert all(0 <= move.row <= 4 for move in rm.root_buttons(has_menus=True, picking_on=True))


# --- the sub-panels ------------------------------------------------------------------------------


def test_a_role_has_to_be_picked_before_it_can_be_named():
    assert actions(rm.add_role_buttons(picked=False)) == [rm.BACK]
    assert actions(rm.add_role_buttons(picked=True)) == [
        rm.USE_ROLE_NAME,
        rm.LABEL_IT,
        rm.BACK,
    ]


def test_taking_roles_back_renders_only_when_they_hold_one():
    assert actions(rm.hand_out_buttons(picked=False, holds_any=True)) == [rm.BACK]
    assert actions(rm.hand_out_buttons(picked=True, holds_any=False)) == [rm.GIVE, rm.BACK]
    assert actions(rm.hand_out_buttons(picked=True, holds_any=True)) == [
        rm.GIVE,
        rm.TAKE_BACK,
        rm.BACK,
    ]


def test_a_new_grant_asks_how_long_only_once_it_knows_who_and_which():
    assert actions(rm.new_grant_buttons(member=False, role=False)) == [rm.BACK]
    assert actions(rm.new_grant_buttons(member=True, role=False)) == [rm.BACK]
    assert actions(rm.new_grant_buttons(member=True, role=True)) == [rm.HOW_LONG, rm.BACK]


# --- the grant card ------------------------------------------------------------------------------


def test_a_grant_with_no_end_date_cannot_be_pushed_back():
    assert actions(rm.grant_buttons(ends=True, removed=False)) == [
        rm.PUSH_BACK,
        rm.END_NOW,
        rm.BACK,
    ]
    assert actions(rm.grant_buttons(ends=False, removed=False)) == [rm.END_NOW, rm.BACK]


def test_a_grant_that_is_already_over_offers_no_move_at_all():
    assert actions(rm.grant_buttons(ends=True, removed=True)) == [rm.BACK]


# --- the request card ----------------------------------------------------------------------------


def test_only_a_pending_request_can_be_decided():
    assert actions(rm.request_buttons(grants.PENDING, timed=False)) == [
        rm.APPROVE,
        rm.DENY,
        rm.BACK,
    ]
    assert actions(rm.request_buttons(grants.APPROVED, timed=False)) == [rm.BACK]
    assert actions(rm.request_buttons(grants.DENIED, timed=True)) == [rm.BACK]


def test_a_menu_with_a_clock_asks_how_long_when_it_approves():
    assert rm.APPROVE_DAYS in actions(rm.request_buttons(grants.PENDING, timed=True))
    assert rm.APPROVE not in actions(rm.request_buttons(grants.PENDING, timed=True))


# --- the words -----------------------------------------------------------------------------------


def test_menu_lines_say_what_rolemenu_show_used_to_print():
    menu = row("pronouns", "Pronouns")
    lines = rm.menu_lines(menu, [option(1, "He/Him", "❤️"), option(2, "She/Her")])

    assert lines[0] == "**pronouns** — Pronouns (multiple, not posted)"
    assert lines[1] == "❤️ He/Him — <@&1>"
    assert lines[2] == "• She/Her — <@&2>"


def test_an_empty_menu_says_so_and_a_staff_menu_says_nobody_picks_it():
    assert rm.NO_ROLES_YET in rm.menu_lines(row("m"), [])
    assert rm.NOBODY_PICKS_THESE in rm.menu_lines(row("m", mode="staff"), [option(1, "One")])
    assert rm.NOBODY_PICKS_THESE not in rm.menu_lines(row("m"), [option(1, "One")])


def test_the_menu_card_carries_the_same_note_the_posted_panel_shows():
    lines = rm.menu_lines(row("m"), [option(1, "One")], note="Picking a role here asks staff.")

    assert lines[-1] == "Picking a role here asks staff."


def test_list_lines_say_what_rolemenu_list_used_to_print():
    menus = [row("pronouns", menu_id=1), row("runner", mode="staff", message_id=5, menu_id=2)]

    assert rm.list_lines(menus, {1: 9, 2: 3}) == [
        "**pronouns** — 9 role(s), multiple, not posted",
        "**runner** — 3 role(s), staff, posted",
    ]


def test_a_menu_the_count_map_has_never_heard_of_reads_zero():
    assert rm.list_lines([row("m")], {}) == ["**m** — 0 role(s), multiple, not posted"]


# --- the audit (§I-amend) ------------------------------------------------------------------------


NOW = datetime(2026, 9, 4, 12, 0, tzinfo=UTC)


def at(days):
    return (NOW + timedelta(days=days)).isoformat()


def test_time_left_reads_the_end_date_and_says_when_there_is_none():
    assert rm.time_left(None, at=NOW) == rm.ENDS_NEVER
    assert rm.time_left("not a date", at=NOW) == rm.ENDS_NEVER
    assert rm.time_left(at(-1), at=NOW) == rm.DUE_NOW
    assert rm.time_left(at(0.5), at=NOW) == rm.UNDER_A_DAY
    assert rm.time_left(at(3), at=NOW) == "3 day(s) left"


def test_the_audit_puts_the_soonest_first_and_a_no_end_grant_last():
    rows = [
        grant(grant_id=1, expires_at=at(9)),
        grant(grant_id=2, expires_at=None),
        grant(grant_id=3, expires_at=at(1)),
    ]

    assert [one["id"] for one in sorted(rows, key=rm.grant_order)] == [3, 1, 2]


def test_an_audit_line_carries_the_member_the_role_the_time_left_and_the_end_date():
    line = rm.grant_line(grant(user_id=900, role_id=5, expires_at=at(2)), at=NOW)

    assert line.startswith("<@900> · <@&5> · 2 day(s) left · <t:")


def test_a_grant_with_no_end_date_says_no_end_date_twice_over():
    line = rm.grant_line(grant(expires_at=None), at=NOW)

    assert line.endswith(f"{rm.ENDS_NEVER} · {rm.NO_END_DATE}")


def test_an_empty_audit_says_so_differently_for_the_server_and_for_one_member():
    assert rm.grant_lines([], at=NOW) == [rm.NO_GRANTS]
    assert rm.grant_lines([], one_member=True, at=NOW) == [rm.NO_GRANTS_FOR_ONE]


def test_the_audit_header_counts_every_grant_even_the_ones_it_cannot_show():
    rows = [grant(grant_id=i, expires_at=at(i + 1)) for i in range(30)]

    lines = rm.grant_lines(rows, at=NOW)

    assert lines[0] == rm.GRANTS_HEADER.format(count=30)
    assert len(lines) == 1 + rm.AUDIT_MAX + 1
    assert lines[-1] == rm.GRANTS_CAPPED.format(shown=rm.AUDIT_MAX, total=30)


def test_an_audit_that_fits_says_nothing_about_the_site():
    lines = rm.grant_lines([grant(expires_at=at(1))], at=NOW)

    assert len(lines) == 2 and "the rest" not in lines[-1]


async def test_active_grants_leaves_out_the_ones_that_are_over(db):
    soon = await grants.add_grant(db, GUILD, 900, 1, "staff", until=grants.expires_at(1))
    later = await grants.add_grant(db, GUILD, 901, 2, "staff", until=grants.expires_at(9))
    forever = await grants.add_grant(db, GUILD, 902, 3, "staff")
    closed = await grants.add_grant(db, GUILD, 903, 4, "staff", until=grants.expires_at(2))
    await grants.end_grant(db, closed, grants.ENDED_BY_STAFF)

    found = await rm.active_grants(db, GUILD)

    assert [row["id"] for row in found] == [soon, later, forever]


async def test_the_audit_narrows_to_one_member_without_changing_its_order(db):
    await grants.add_grant(db, GUILD, 900, 1, "staff", until=grants.expires_at(9))
    mine = await grants.add_grant(db, GUILD, 901, 2, "staff", until=grants.expires_at(5))
    also_mine = await grants.add_grant(db, GUILD, 901, 3, "staff", until=grants.expires_at(1))

    found = await rm.active_grants(db, GUILD, user_id=901)

    assert [row["id"] for row in found] == [also_mine, mine]


async def test_another_servers_grants_are_never_in_the_audit(db):
    mine = await grants.add_grant(db, GUILD, 900, 1, "staff", until=grants.expires_at(1))
    await grants.add_grant(db, GUILD + 1, 900, 1, "staff", until=grants.expires_at(1))

    assert [row["id"] for row in await rm.active_grants(db, GUILD)] == [mine]


# --- the settings key ----------------------------------------------------------------------------


async def test_panel_minutes_reads_the_key_and_defaults_to_ten(db, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    store = SettingsStore(db, load_settings(_env_file=None))
    await store.load()

    assert rm.panel_minutes(store, GUILD) == 10

    await store.set(GUILD, rm.PANEL_MINUTES_KEY, 4)

    assert rm.panel_minutes(store, GUILD) == 4


def test_no_origin_means_no_link_at_all():
    assert rm.site_page_url("") is None
    assert rm.site_page_url("https://bb.example/") == "https://bb.example/rolemenus.html"


# --- temporary roles: one end per menu (request #17) ----------------------------------------------


def end_row(source="none", ends_at=None, buffer_days=None, ended_at=None):
    return {
        "ends_source": source,
        "ends_at": ends_at,
        "buffer_days": buffer_days,
        "ended_at": ended_at,
    }


def test_a_typed_date_ends_at_one_minute_to_midnight_guild_local():
    end = rm.typed_end("2027-02-28", "America/Phoenix")
    assert end == datetime(2027, 3, 1, 6, 59, tzinfo=UTC)


def test_a_typed_date_and_time_ends_at_that_minute_guild_local():
    assert rm.typed_end("2027-02-28 18:00", "America/Phoenix") == datetime(
        2027, 3, 1, 1, 0, tzinfo=UTC
    )
    assert rm.typed_end("the 28th", "America/Phoenix") is None
    assert rm.typed_end("", "America/Phoenix") is None


def test_a_date_end_is_the_stored_moment_in_one_utc_form():
    menu = end_row("date", "2027-03-01T06:59:00+00:00")
    assert rm.ends_at_of(menu, None, 1) == "2027-03-01T06:59:00+00:00"
    shifted = end_row("date", "2027-02-28T23:59:00-07:00")
    assert rm.ends_at_of(shifted, None, 1) == "2027-03-01T06:59:00+00:00"


def test_a_marathon_end_is_the_marathons_end_plus_the_default_buffer():
    marathon = {"ends_at": "2027-02-28T05:00:00+00:00"}
    assert rm.ends_at_of(end_row("marathon"), marathon, 1) == "2027-03-01T05:00:00+00:00"
    assert rm.ends_at_of(end_row("marathon"), marathon, 0) == "2027-02-28T05:00:00+00:00"


def test_a_menus_own_buffer_beats_the_default_and_zero_is_a_buffer():
    marathon = {"ends_at": "2027-02-28T05:00:00+00:00"}
    assert rm.ends_at_of(end_row("marathon", buffer_days=3), marathon, 1) == (
        "2027-03-03T05:00:00+00:00"
    )
    assert rm.ends_at_of(end_row("marathon", buffer_days=0), marathon, 1) == (
        "2027-02-28T05:00:00+00:00"
    )


def test_no_end_is_no_moment_whatever_the_row_still_holds():
    assert rm.ends_at_of(end_row("none", "2027-03-01T00:00:00+00:00"), None, 1) is None
    assert rm.ends_at_of({}, None, 1) is None
    assert rm.ends_at_of(end_row("sometimes", "2027-03-01T00:00:00+00:00"), None, 1) is None


def test_a_marathon_with_no_end_yet_binds_to_no_moment():
    assert rm.ends_at_of(end_row("marathon"), {"ends_at": None}, 1) is None


def test_a_marathon_row_that_is_gone_keeps_the_last_computed_end():
    menu = end_row("marathon", "2027-03-01T05:00:00+00:00")
    assert rm.ends_at_of(menu, None, 1) == "2027-03-01T05:00:00+00:00"


def test_an_end_moves_only_when_the_instant_changes():
    assert not rm.end_moved("2027-03-01T05:00:00+00:00", "2027-02-28T22:00:00-07:00")
    assert rm.end_moved("2027-03-01T05:00:00+00:00", "2027-03-01T06:00:00+00:00")
    assert rm.end_moved(None, "2027-03-01T05:00:00+00:00")
    assert rm.end_moved("2027-03-01T05:00:00+00:00", None)
    assert not rm.end_moved(None, None)


def test_staff_are_told_only_about_a_move_past_the_floor():
    was = "2027-03-01T05:00:00+00:00"
    assert not rm.moved_far(was, "2027-03-01T05:20:00+00:00", 60)
    assert rm.moved_far(was, "2027-03-01T06:00:00+00:00", 60)
    assert rm.moved_far(was, "2027-03-01T04:00:00+00:00", 60)
    assert rm.moved_far(None, was, 60) and rm.moved_far(was, None, 60)
    assert not rm.moved_far(was, was, 0)


def test_a_menu_is_due_once_its_end_has_passed_and_never_twice():
    now = datetime(2027, 3, 2, tzinfo=UTC)
    assert rm.is_due(end_row("date", "2027-03-01T06:59:00+00:00"), now)
    assert not rm.is_due(end_row("date", "2027-03-03T06:59:00+00:00"), now)
    assert not rm.is_due(
        end_row("date", "2027-03-01T06:59:00+00:00", ended_at="2027-03-01T07:00:00+00:00"), now
    )
    assert not rm.is_due(end_row("none"), now)


def test_an_unreadable_end_is_never_due():
    assert not rm.is_due(end_row("date", "the end of february"), datetime(2099, 1, 1, tzinfo=UTC))


class _Wearer:
    def __init__(self, user_id, *role_ids):
        self.id = user_id
        self.roles = [type("R", (), {"id": one})() for one in role_ids]


def test_wearers_lists_everyone_wearing_any_role_with_the_ones_they_wear():
    alice, bob, cara = _Wearer(1, 10, 99), _Wearer(2, 99), _Wearer(3, 11, 10)
    found = rm.wearers([alice, bob, cara], [10, 11])
    assert [(member.id, worn) for member, worn in found] == [(1, [10]), (3, [10, 11])]
    assert rm.wearers([alice], []) == []


def test_what_ended_is_the_marathons_name_or_the_date():
    marathon_menu = end_row("marathon", "2027-03-01T05:00:00+00:00")
    assert rm.what_ended(marathon_menu, "Back to Black 2027") == "Back to Black 2027"
    assert rm.what_ended(end_row("date", "2027-03-01T05:00:00+00:00"), None) == "<t:1803877200:D>"
