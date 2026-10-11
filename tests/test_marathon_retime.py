from datetime import UTC, datetime, timedelta

from black_bloc import marathon as mt
from black_bloc import marathon_retime as rt
from black_bloc import marathon_signals as sig

NOW = datetime(2026, 10, 3, 17, 0, tzinfo=UTC)
PHOENIX = "America/Phoenix"


def iso(minutes):
    return (NOW + timedelta(minutes=minutes)).isoformat()


def row(ident, at, length=60, *, state=mt.UPCOMING, **extra):
    return {
        "id": ident,
        "order_no": ident,
        "game": f"Game {ident}",
        "state": state,
        "scheduled_at": iso(at),
        "ends_at": iso(at + length),
        "sheet_at": iso(at),
        "sheet_ends_at": iso(at + length),
        "run_seconds": length * 60,
        **extra,
    }


def test_a_clock_time_lands_on_the_day_nearest_the_runs_start():
    near = NOW + timedelta(minutes=30)
    assert rt.target_of("10:45 am", PHOENIX, near) == NOW + timedelta(minutes=45)
    assert rt.target_of("10:45", PHOENIX, near) == NOW + timedelta(minutes=45)
    assert rt.target_of("10:45AM", PHOENIX, near) == NOW + timedelta(minutes=45)
    late = datetime(2026, 10, 4, 6, 50, tzinfo=UTC)
    assert rt.target_of("12:10 AM", PHOENIX, late) == datetime(2026, 10, 4, 7, 10, tzinfo=UTC)


def test_a_date_and_time_is_read_in_the_zone_and_an_iso_moment_keeps_its_offset():
    assert rt.target_of("2026-10-03 10:00", PHOENIX, None) == NOW
    assert rt.target_of("2026-10-03 2:30 PM", PHOENIX, None) == NOW + timedelta(hours=4.5)
    assert rt.target_of("2026-10-03T17:00:00+00:00", PHOENIX, None) == NOW
    assert rt.target_of("soon", PHOENIX, NOW) is None
    assert rt.target_of("", PHOENIX, NOW) is None
    assert rt.target_of("25:00", PHOENIX, NOW) is None


def test_minutes_take_a_sign_and_a_typographic_minus():
    assert rt.minutes_of("10") == 10
    assert rt.minutes_of("+15") == 15
    assert rt.minutes_of(" -5 ") == -5
    assert rt.minutes_of("−20") == -20
    assert rt.minutes_of("ten") is None
    assert rt.minutes_trouble(0, 240) and rt.minutes_trouble(241, 240)
    assert rt.minutes_trouble(None, 240) and not rt.minutes_trouble(-240, 240)
    assert rt.signed(10) == "+10" and rt.signed(-5) == "-5"


def test_a_new_start_carries_the_later_staff_starts_of_its_day_by_the_same_amount():
    rows = [
        row(1, 0),
        row(2, 60),
        row(3, 120, staff_start_at=iso(130)),
        row(4, 180, state=mt.DONE, staff_start_at=iso(185)),
    ]
    chain = rt.chain_of(sig.chains(rows), rows[1])
    found = [(one["id"], at) for one, at in rt.anchors(chain, rows[1], NOW + timedelta(minutes=70))]
    assert found == [(2, NOW + timedelta(minutes=70)), (3, NOW + timedelta(minutes=140))]


def test_the_run_ahead_that_began_is_the_floor():
    rows = [row(1, 0, state=mt.LIVE, actual_started_at=iso(5)), row(2, 60), row(3, 120)]
    chain = rt.chain_of(sig.chains(rows), rows[2])
    assert rt.ahead_started(chain, rows[2])["id"] == 1
    assert rt.ahead_started(chain, rows[0]) is None


def test_the_picker_holds_runs_not_yet_started_soonest_first_and_at_most_25():
    rows = [row(ident, ident * 10) for ident in range(30, 0, -1)]
    rows.append(row(99, -10, state=mt.LIVE))
    found = rt.pickable(rows)
    assert len(found) == 25 and [one["id"] for one in found[:2]] == [1, 2]
