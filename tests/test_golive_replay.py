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
