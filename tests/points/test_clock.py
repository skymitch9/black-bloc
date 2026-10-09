from __future__ import annotations

import pytest

from black_bloc.points.clock import MAX_SECONDS, seconds_of, shown
from black_bloc.points.model import PointsError


@pytest.mark.parametrize(
    ("given", "seconds"),
    [
        ("1:23:45.67", 5025.67),
        ("23:45", 1425),
        ("45.2", 45.2),
        ("45", 45),
        ("1h 2m 3s", 3723),
        ("1h2m3s", 3723),
        ("2m", 120),
        ("1h", 3600),
        ("90s", 90),
        ("1 hour 5 minutes", 3900),
        ("  0:59  ", 59),
        ("90:00", 5400),
        ("0:00:01.5", 1.5),
        ("1H 2M", 3720),
    ],
)
def test_every_way_a_member_writes_a_time_reads_as_seconds(given, seconds):
    assert seconds_of(given) == pytest.approx(seconds)


@pytest.mark.parametrize(
    "given",
    [
        "fast",
        "1:60",
        "1:61:00",
        "1:00:60",
        "12:3a",
        "-5",
        "0",
        "0:00",
        "1m 2h",
        "1m 1m",
        "1x",
        "1:2:3:4",
        ":30",
        "1h and 2m",
        "4.5.6",
        f"{MAX_SECONDS + 1}",
    ],
)
def test_junk_is_refused_with_what_was_typed(given):
    with pytest.raises(PointsError) as refused:
        seconds_of(given)
    assert refused.value.code == "bad_time"
    assert refused.value.fields["given"] == given[:40]


@pytest.mark.parametrize("given", ["", "   ", None])
def test_nothing_typed_is_its_own_refusal(given):
    with pytest.raises(PointsError) as refused:
        seconds_of(given)
    assert refused.value.code == "no_time"


@pytest.mark.parametrize(
    ("seconds", "text"),
    [
        (5025.67, "1:23:45.67"),
        (1425, "23:45"),
        (45.2, "0:45.20"),
        (3600, "1:00:00"),
        (59.999, "1:00"),
    ],
)
def test_a_time_is_shown_the_speedrun_way(seconds, text):
    assert shown(seconds) == text


def test_shown_reads_back_as_the_same_time():
    for seconds in (1, 59, 61.5, 599, 600, 1800, 3723.25, 18000):
        assert seconds_of(shown(seconds)) == pytest.approx(seconds)
