from types import SimpleNamespace

import pytest

from black_bloc import marathon_role_ping as mrp

ROLE = SimpleNamespace(id=77, name="Marathon", mentionable=True)
QUIET_ROLE = SimpleNamespace(id=77, name="Marathon", mentionable=False)
ALL_ON = (
    (mrp.ROLE_PINGS_OFF, True),
    (mrp.REMINDER_PINGS_OFF, True),
    (mrp.PUBLIC_REMINDERS_OFF, True),
)


def decide(**given):
    asked = {
        "switch_on": True,
        "off": ALL_ON,
        "announces": True,
        "configured": 77,
        "role": ROLE,
        "may_mention_every_role": False,
    } | given
    return mrp.decide(**asked)


def test_everything_in_place_mentions_the_role():
    found = decide()
    assert found.mentions and found.role_id == 77 and found.reason is None
    assert found.name == "Marathon" and found.configured == 77


def test_the_marathons_own_switch_comes_first():
    found = decide(switch_on=False, configured=None, role=None)
    assert not found.mentions and found.reason == mrp.SWITCH_OFF


@pytest.mark.parametrize("reason", mrp.KEY_REASONS)
def test_each_key_off_is_named_as_itself(reason):
    off = tuple((one, one != reason) for one, _on in ALL_ON)
    found = decide(off=off)
    assert found.role_id is None and found.reason == reason


def test_the_first_key_that_is_off_is_the_one_named():
    off = ((mrp.ROLE_PINGS_OFF, False), (mrp.REMINDER_PINGS_OFF, False))
    assert decide(off=off).reason == mrp.ROLE_PINGS_OFF


def test_announcements_off_means_no_public_copy_to_carry_it():
    assert decide(announces=False).reason == mrp.ANNOUNCEMENTS_OFF


def test_a_rehearsal_never_mentions_it():
    assert decide(rehearsing=True).reason == mrp.REHEARSAL
    assert not decide(rehearsing=True).mentions


def test_no_role_picked_and_a_deleted_role_are_two_reasons():
    assert decide(configured=None, role=None).reason == mrp.UNSET
    gone = decide(role=None)
    assert gone.reason == mrp.GONE and gone.configured == 77 and gone.role_id is None


def test_a_role_discord_would_not_notify_is_left_out_unless_the_bot_may_mention_every_role():
    quiet = decide(role=QUIET_ROLE)
    assert quiet.reason == mrp.NOT_MENTIONABLE and quiet.role_id is None
    assert quiet.name == "Marathon"
    assert decide(role=QUIET_ROLE, may_mention_every_role=True).mentions
    assert mrp.notifies(ROLE, False) and not mrp.notifies(QUIET_ROLE, False)


def test_the_public_copy_gains_the_role_once_and_the_staff_copy_never_carries_it():
    found = decide()
    assert mrp.with_role([5, 77, 5], found) == [5, 77]
    assert mrp.with_role([5], found) == [5, 77]
    assert mrp.without_role([5, 77], found) == [5]
    quiet = decide(configured=None, role=None)
    assert mrp.with_role([5, 77], quiet) == [5, 77]
    assert mrp.without_role([5, 77], quiet) == [5, 77]
    assert mrp.with_role([5], None) == [5] and mrp.without_role([5, 5], None) == [5]


def test_a_copy_that_does_not_post_turns_a_mention_into_its_reason():
    found = mrp.unsent(decide(), mrp.NO_PUBLIC_COPY)
    assert found.role_id is None and found.reason == mrp.NO_PUBLIC_COPY
    assert found.configured == 77
    already = decide(configured=None, role=None)
    assert mrp.unsent(already, mrp.NO_PUBLIC_COPY) == already


def test_the_row_fields_say_which_role_or_why_not():
    assert mrp.row_fields(None) == {}
    assert mrp.row_fields(decide()) == {"marathon_role": 77, "marathon_role_reason": None}
    assert mrp.row_fields(decide(role=None)) == {
        "marathon_role": None,
        "marathon_role_reason": mrp.GONE,
    }


def test_every_reason_is_listed_once():
    assert len(set(mrp.REASONS)) == len(mrp.REASONS) == 13
