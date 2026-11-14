from datetime import UTC, datetime, timedelta

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

WORDS = {
    rm.SET_END: "Change the end…",
    rm.END_MENU: "End it now",
    rm.USE_HELD: "Use the earlier end",
    rm.TYPE_DATE: "Type a date…",
    rm.BUFFER: "Buffer…",
    rm.NO_END_MOVE_ACTION: "No end",
    rm.NEW_EVENT: "New event…",
    rm.TIMED_ROLES: "Timed roles…",
    rm.ENDED: "Ended ({count})…",
    rm.GIVE: "Give roles…",
    rm.FILL: "Fill from the schedule",
    rm.TAKE_OFF: "Take roles off…",
    rm.ATTACH: "Attach a marathon…",
    rm.RENAME: "Rename…",
    rm.NO_MARATHON: "No marathon yet…",
    rm.FILL_YES: "Give them the roles",
}


def test_the_root_opens_on_events_with_the_ended_ones_folded_behind_a_count():
    assert actions(rm.root_buttons(ended=0, words=WORDS)) == [
        rm.NEW_EVENT,
        rm.TIMED_ROLES,
        rm.GRANTS,
        rm.LOGS,
        rm.REFRESH,
    ]
    folded = rm.root_buttons(ended=3, words=WORDS)
    assert rm.ENDED in actions(folded) and "Ended (3)…" in labels(folded)


# --- the event card ------------------------------------------------------------------------------


def card(**kwargs):
    wanted = {
        "open_": True,
        "roles": 2,
        "marathon": False,
        "attachable": True,
        "assigned": True,
        "held": False,
        "words": WORDS,
    }
    return rm.event_buttons(**(wanted | kwargs))


def test_an_open_dated_event_gives_takes_attaches_changes_ends_renames_and_deletes():
    assert actions(card()) == [
        rm.GIVE,
        rm.TAKE_OFF,
        rm.SET_END,
        rm.ATTACH,
        rm.RENAME,
        rm.END_MENU,
        rm.DELETE,
        rm.BACK,
        rm.REFRESH,
    ]
    assert "Change the end…" in labels(card()) and "End it now" in labels(card())


def test_fill_from_the_schedule_renders_only_with_a_marathon_and_attach_only_without():
    assert rm.FILL in actions(card(marathon=True, attachable=False))
    assert rm.ATTACH not in actions(card(marathon=True, attachable=False))
    assert rm.FILL not in actions(card())


def test_moves_that_need_roles_or_people_render_only_once_there_are_some():
    empty = actions(card(roles=0, assigned=False))
    assert rm.GIVE not in empty and rm.END_MENU not in empty and rm.TAKE_OFF not in empty
    assert rm.SET_END in empty and rm.DELETE in empty


def test_an_ended_event_cannot_be_given_to_attached_or_ended_again():
    over = actions(card(open_=False, assigned=False))
    for gone in (rm.GIVE, rm.FILL, rm.ATTACH, rm.END_MENU, rm.TAKE_OFF):
        assert gone not in over
    assert rm.SET_END in over and rm.RENAME in over and rm.DELETE in over


def test_use_the_earlier_end_renders_only_while_one_is_held():
    assert rm.USE_HELD not in actions(card())
    assert rm.USE_HELD in actions(card(held=True))


def test_no_control_sits_outside_discords_five_rows_or_crowds_a_row():
    for state in (
        card(),
        card(held=True, marathon=True, attachable=False),
        card(roles=0),
        rm.root_buttons(ended=2, words=WORDS),
        rm.new_event_buttons(WORDS),
        rm.fill_buttons(missing=3, words=WORDS),
        rm.back_buttons(),
    ):
        assert all(0 <= move.row <= 4 for move in state)
        rows = [move.row for move in state]
        assert all(rows.count(one) <= 5 for one in set(rows))


def test_set_the_end_offers_buffer_only_for_a_marathon_and_no_end_only_with_an_end():
    assert actions(rm.set_end_buttons(source=rm.NO_END, words=WORDS)) == [
        rm.TYPE_DATE,
        rm.BACK,
        rm.REFRESH,
    ]
    assert actions(rm.set_end_buttons(source=rm.DATE_END, words=WORDS)) == [
        rm.TYPE_DATE,
        rm.NO_END_MOVE_ACTION,
        rm.BACK,
        rm.REFRESH,
    ]
    assert actions(rm.set_end_buttons(source=rm.MARATHON_END, words=WORDS)) == [
        rm.TYPE_DATE,
        rm.BUFFER,
        rm.NO_END_MOVE_ACTION,
        rm.BACK,
        rm.REFRESH,
    ]


# --- the sub-panels ------------------------------------------------------------------------------


def test_new_event_offers_a_typed_event_and_fill_confirms_only_with_someone_missing():
    assert actions(rm.new_event_buttons(WORDS)) == [rm.NO_MARATHON, rm.BACK]
    assert actions(rm.fill_buttons(missing=0, words=WORDS)) == [rm.BACK, rm.REFRESH]
    assert actions(rm.fill_buttons(missing=2, words=WORDS)) == [rm.FILL_YES, rm.BACK, rm.REFRESH]


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


# --- the words -----------------------------------------------------------------------------------


def test_a_menus_heading_names_it_without_any_self_pick_state():
    assert rm.menu_heading(row("pronouns", "Pronouns", message_id=5)) == "**pronouns** — Pronouns"


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


def test_an_end_pulled_earlier_past_the_floor_by_the_end_or_the_last_told_one():
    pulls = rm.pulls_earlier
    current = "2027-03-01T05:00:00+00:00"
    assert pulls(current, current, "2027-03-01T03:59:00+00:00", 60)
    assert not pulls(current, current, "2027-03-01T04:00:00+00:00", 60)
    assert not pulls(current, current, "2027-03-02T05:00:00+00:00", 60)
    assert pulls(current, current, "2027-03-01T04:59:00+00:00", 0)
    assert pulls("2027-03-01T04:30:00+00:00", current, "2027-03-01T03:50:00+00:00", 60)
    assert not pulls(None, None, "2020-01-01T00:00:00+00:00", 60)
    assert not pulls(current, current, None, 60)
    assert pulls(current, None, "2020-01-01T00:00:00+00:00", "garbled")


def test_a_staff_word_left_blank_or_broken_falls_back_to_the_shipped_one():
    class Store:
        def __init__(self, stored):
            self.stored = stored

        def get(self, guild_id, key):
            return self.stored

        def default(self, key, guild_id=None):
            return "Set the end…"

    assert rm.said(Store("   "), GUILD, "rolemenu_set_end_button") == "Set the end…"
    assert rm.said(Store("{nope}"), GUILD, "rolemenu_set_end_button") == "Set the end…"
    assert rm.said(Store("Pick the end…"), GUILD, "rolemenu_set_end_button") == "Pick the end…"
