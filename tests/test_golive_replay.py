from datetime import UTC, datetime, timedelta

import pytest

from black_bloc import golive_replay as replays
from black_bloc.settings_store import GOLIVE_REPLAY_DEFAULTS, GOLIVE_REPLAY_WORDS_KEY

WORDS = replays.words_of(GOLIVE_REPLAY_DEFAULTS[GOLIVE_REPLAY_WORDS_KEY])
LIVE = ("live",)


def read(title, stream_type=None, *, marathon=False, words=WORDS, live_words=LIVE):
    return replays.verdict(
        title, stream_type, words=words, live_words=live_words, marathon=marathon
    )


def test_the_default_words_are_the_owners_six():
    assert WORDS == ("replay", "rerun", "rebroadcast", "re-broadcast", "vod", "encore")


def test_words_are_split_on_commas_trimmed_folded_and_deduplicated():
    assert replays.words_of(" Replay,REPLAY ,, vod\nEncore ") == ("replay", "vod", "encore")
    assert replays.words_of("") == ()
    assert replays.words_of(None) == ()


def test_twitchs_own_rerun_type_is_a_replay_whatever_the_title_says():
    seen = read("AGDQ 2027 — Celeste Any%", "rerun")
    assert seen.replay and seen.reason == replays.REASON_TYPE
    assert read("LIVE now", "Rerun").replay


def test_a_rerun_type_is_a_replay_even_inside_a_marathon():
    assert read("AGDQ", "rerun", marathon=True).replay


def test_twitchs_live_type_and_an_empty_type_decide_nothing_on_their_own():
    assert not read("AGDQ 2027", "live").replay
    assert not read("AGDQ 2027", "").replay
    assert not read("AGDQ 2027", None).replay


@pytest.mark.parametrize(
    ("title", "word"),
    [
        ("[REPLAY] AGDQ 2026 — Celeste Any% by Hotfix", "replay"),
        ("Replay: SGDQ 2025 Super Metroid", "replay"),
        ("(Rerun) ESA Summer 2025 — Hollow Knight", "rerun"),
        ("VOD — AGDQ 2024 highlights", "vod"),
        ("RERUN of ESA Winter 2025", "rerun"),
        ("rebroadcast: Frost Fatales 2026", "rebroadcast"),
        ("GDQ Re-Broadcast | Mega Man X", "re-broadcast"),
        ("ENCORE — the best runs of SGDQ", "encore"),
        ("SGDQ 2025 [Replay]", "replay"),
        ("ESA 2025 - replay - day 3", "replay"),
        ("replay", "replay"),
        ("GDQ | REPLAY | Zelda", "replay"),
        ("Hotfix #replay night", "replay"),
    ],
)
def test_gdq_and_esa_replay_titles_are_replays_outside_a_marathon(title, word):
    seen = read(title)
    assert seen.replay, title
    assert seen.reason == replays.TITLE_HEAD + word
    assert seen.matched == word


@pytest.mark.parametrize(
    "title",
    [
        "AGDQ 2027 — Celeste Any% by Hotfix",
        "Replayability tier list — any% glitchless",
        "Vodka Tonic Speedruns — Hades",
        "Rerunner Deluxe any%",
        "The Replayers relay race",
        "Encores and Encoring: a TAS showcase",
        "Chrono Trigger by vodkadude",
        "Rebroadcasting? no, this is fresh",
        "SuperReplay 64 randomizer",
        "Hunt_replay_bot blind race",
        "",
    ],
)
def test_a_word_inside_a_longer_word_or_name_is_not_a_replay(title):
    seen = read(title)
    assert not seen.replay, title
    assert seen.overruled is None


def test_a_title_word_inside_a_marathon_span_is_live_and_says_it_was_overruled():
    seen = read("[REPLAY] AGDQ 2026 — Celeste", marathon=True)
    assert not seen.replay
    assert seen.overruled == replays.OVERRULED_MARATHON and seen.matched == "replay"


@pytest.mark.parametrize(
    "title",
    [
        "[REPLAY] + LIVE commentary — AGDQ",
        "Rerun of the finale, then LIVE bonus stage",
        "Live! (replay of day 1 at 3pm)",
    ],
)
def test_a_title_that_also_says_live_is_live(title):
    seen = read(title)
    assert not seen.replay
    assert seen.overruled == replays.LIVE_HEAD + "live"


def test_live_inside_a_longer_word_does_not_overrule():
    assert read("[REPLAY] Alive in Tokyo — Deliverance%").replay


def test_edited_words_change_what_is_read():
    assert not read("Throwback: SGDQ 2019", words=replays.words_of("replay")).replay
    assert read("Throwback: SGDQ 2019", words=replays.words_of("replay, throwback")).replay
    assert read("[REPLAY] LIVE", live_words=()).replay
    assert not read("[REPLAY] fresh", live_words=replays.words_of("fresh")).replay
    assert not read("[REPLAY] AGDQ", words=()).replay


def test_a_marathon_span_holds_now_with_the_lead_and_the_tail():
    now = datetime(2026, 9, 27, 20, 0, tzinfo=UTC)

    def one(start_minutes, end_minutes):
        return {
            "starts_at": (now + timedelta(minutes=start_minutes)).isoformat(),
            "ends_at": (now + timedelta(minutes=end_minutes)).isoformat(),
        }

    assert replays.in_marathon([one(-60, 60)], now)
    assert not replays.in_marathon([one(10, 60)], now)
    assert replays.in_marathon([one(10, 60)], now, lead_minutes=15)
    assert not replays.in_marathon([one(-120, -30)], now)
    assert replays.in_marathon([one(-120, -30)], now, tail_minutes=60)
    assert not replays.in_marathon([{"starts_at": None, "ends_at": None}], now)
    assert not replays.in_marathon([], now)


def test_a_session_is_a_replay_until_it_is_cleared():
    assert replays.is_replay({"replay_reason": "title:replay", "replay_cleared": None})
    assert not replays.is_replay({"replay_reason": "title:replay", "replay_cleared": "staff"})
    assert not replays.is_replay({"replay_reason": None, "replay_cleared": None})
    assert not replays.is_replay(None)
    assert not replays.is_replay({})


def test_the_state_line_is_written_in_the_keys_words():
    session = {"replay_reason": "title:rerun", "replay_cleared": None}
    said = replays.state_line(session, "Replay ({reason})", "Twitch says rerun", "title: {word}")
    assert said == "Replay (title: rerun)"
    typed = {"replay_reason": "type", "replay_cleared": None}
    assert replays.state_line(typed, "{reason}", "Twitch says rerun", "x") == "Twitch says rerun"
    assert replays.state_line({"replay_reason": None}, "{reason}", "a", "b") is None


def test_why_a_replay_became_live_without_staff():
    live = replays.Verdict(False)
    marathon = replays.Verdict(False, overruled=replays.OVERRULED_MARATHON, matched="replay")
    assert replays.cleared_because("title:replay", live, "plain") == replays.CLEARED_TITLE
    assert replays.cleared_because("type", live, "plain") == replays.CLEARED_TYPE
    assert replays.cleared_because("title:replay", marathon, "plain") == replays.CLEARED_MARATHON
    assert replays.cleared_because("title:replay", live, "live") == replays.CLEARED_ACTION


# --- a leading tag is certain (spotlight-design.md, Follow-up 2026-10-04) ----------------------

GDQUEER_REPLAY = "[Replay] GDQueer Day 1 - tune in live for Day 2 starting at 1pm Eastern!"


def tagged(title, stream_type="live", *, marathon=False, tag_certain=True):
    return replays.verdict(
        title,
        stream_type,
        words=WORDS,
        live_words=LIVE,
        marathon=marathon,
        tag_certain=tag_certain,
    )


@pytest.mark.parametrize(
    ("title", "word"),
    [
        (GDQUEER_REPLAY, "replay"),
        ("[RERUN] AGDQ 2026 live", "rerun"),
        ("(Replay) the finale, live commentary", "replay"),
        ("  [ replay ] day one", "replay"),
        ("Replay: day one live", "replay"),
        ("Replay - day one live", "replay"),
        ("VOD | day one live", "vod"),
        ("[Replay of Day 1] live at 1pm", "replay"),
        ("【Replay】 day one", "replay"),
    ],
)
def test_a_replay_word_opening_the_title_is_certain_whatever_else_it_says(title, word):
    seen = tagged(title)
    assert seen.replay and seen.reason == replays.TAG_HEAD + word
    assert replays.is_certain(seen.reason)
    assert tagged(title, marathon=True).replay


@pytest.mark.parametrize(
    "title",
    [
        "Replay value is high",
        "No replay: live now",
        "GDQueer Day 1 [Replay]",
        "Day 2 (replay of day 1 later)",
        "Replay-Value Podcast",
        "Replays: the best of",
        "[LIVE] replay of the finals",
    ],
)
def test_a_replay_word_that_does_not_open_the_title_stays_fuzzy(title):
    seen = tagged(title)
    assert not replays.is_certain(seen.reason)
    assert not tagged(title, marathon=True).replay
    assert replays.tag_in(title, WORDS) is None


def test_with_the_tag_key_off_a_leading_tag_reads_as_any_title_word():
    seen = tagged(GDQUEER_REPLAY, tag_certain=False)
    assert not seen.replay and seen.overruled == "live:live"
    assert tagged("[Replay] day one", tag_certain=False).reason == "title:replay"
    assert read(GDQUEER_REPLAY) == seen


def test_only_the_type_and_a_tag_are_certain():
    assert replays.is_certain("type") and replays.is_certain("tag:replay")
    assert not replays.is_certain("title:replay") and not replays.is_certain(None)


def test_the_state_line_names_a_tag_in_its_own_words():
    session = {"replay_reason": "tag:replay", "replay_cleared": None}
    said = replays.state_line(
        session, "Replay ({reason})", "a rerun", "title says {word}", "opens with {word}"
    )
    assert said == "Replay (opens with replay)"
    assert replays.reason_words("tag:vod", "a rerun", "says {word}") == "says vod"
    assert replays.cleared_because("tag:replay", replays.Verdict(False), "plain") == "title"


# --- the marathon exemption only while a run is around ----------------------------------------

DAY_ONE = datetime(2026, 10, 3, 17, 0, tzinfo=UTC)
DAY_TWO = datetime(2026, 10, 4, 17, 0, tzinfo=UTC)


def run(start, minutes, **fields):
    return {
        "state": "upcoming",
        "order_no": 0,
        "sheet_at": start.isoformat(),
        "sheet_ends_at": (start + timedelta(minutes=minutes)).isoformat(),
        "scheduled_at": start.isoformat(),
        "ends_at": (start + timedelta(minutes=minutes)).isoformat(),
    } | fields


def two_days():
    return [
        run(DAY_ONE, 60),
        run(DAY_ONE + timedelta(minutes=60), 90),
        run(DAY_ONE + timedelta(minutes=165), 75),
        run(DAY_TWO, 30),
        run(DAY_TWO + timedelta(minutes=30), 60),
    ]


GDQUEER = {
    "starts_at": DAY_ONE.isoformat(),
    "ends_at": (DAY_TWO + timedelta(minutes=90)).isoformat(),
}


def test_the_runs_fall_into_one_block_per_show_day():
    assert replays.day_blocks(two_days()) == [
        (DAY_ONE, DAY_ONE + timedelta(minutes=240)),
        (DAY_TWO, DAY_TWO + timedelta(minutes=90)),
    ]
    assert replays.day_blocks([]) == []
    assert replays.day_blocks([run(DAY_ONE, 60, state="dropped")]) == []


@pytest.mark.parametrize(
    ("minutes", "around"),
    [
        (-31, False),
        (-30, True),
        (0, True),
        (239, True),
        (240 + 59, True),
        (240 + 60, False),
        (20 * 60 + 40, False),
        (24 * 60 - 30, True),
        (24 * 60 + 90 + 59, True),
        (24 * 60 + 90 + 60, False),
    ],
)
def test_a_run_is_around_from_a_days_first_run_less_the_lead_to_its_last_plus_the_tail(
    minutes, around
):
    now = DAY_ONE + timedelta(minutes=minutes)
    assert replays.run_around([(GDQUEER, two_days())], now, 30, 60) is around


def test_the_whole_span_would_have_covered_the_overnight_gap():
    overnight = DAY_ONE + timedelta(hours=20, minutes=40)
    assert replays.in_marathon([GDQUEER], overnight, 30, 60)
    assert not replays.run_around([(GDQUEER, two_days())], overnight, 30, 60)


def test_a_run_running_late_holds_its_day_open_by_its_re_timed_end():
    late = two_days()
    late[2] = late[2] | {"ends_at": (DAY_ONE + timedelta(minutes=330)).isoformat()}
    assert replays.run_around([(GDQUEER, late)], DAY_ONE + timedelta(minutes=380), 30, 60)
    assert not replays.run_around([(GDQUEER, late)], DAY_ONE + timedelta(minutes=390), 30, 60)


def test_a_marathon_with_no_timed_runs_keeps_its_whole_span():
    overnight = DAY_ONE + timedelta(hours=20, minutes=40)
    assert replays.run_around([(GDQUEER, [])], overnight, 30, 60)
    untimed = [{"state": "upcoming", "sheet_at": None, "scheduled_at": None}]
    assert replays.run_around([(GDQUEER, untimed)], overnight, 30, 60)
    assert not replays.run_around([(GDQUEER, [])], DAY_TWO + timedelta(days=2), 30, 60)
    assert not replays.run_around([], overnight, 30, 60)


def test_any_marathon_on_the_channel_with_a_run_around_counts():
    other = {
        "starts_at": DAY_TWO.isoformat(),
        "ends_at": (DAY_TWO + timedelta(hours=1)).isoformat(),
    }
    now = DAY_TWO + timedelta(minutes=10)
    assert replays.run_around([(GDQUEER, two_days()[:3]), (other, [run(DAY_TWO, 60)])], now, 0, 0)
    assert not replays.run_around([(GDQUEER, two_days()[:3])], now, 0, 0)
