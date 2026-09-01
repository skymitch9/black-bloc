import pytest

from black_bloc.chat_llm import (
    BUDGET_WORDS,
    CONVERSATION_TURNS,
    QUESTION_WORDS,
    a_conversation,
    a_real_question,
    about_staff,
    ladder,
    llm_turns,
    says_a_budget_word,
    spoken,
    tier_for,
    word_count,
)
from black_bloc.llm import IMPORTANT, SIMPLE

LONG = "hey can somebody tell me how the role menus work and where I pick my colour?"
SHORT_Q = "you good?"


def turn(tier=None):
    return {"speaker": "bot", "content": "words", "tier": tier}


def test_the_mention_comes_out_but_the_punctuation_stays():
    assert spoken("<@123> what time is it?") == "what time is it?"
    assert spoken("<@!123>   spaced   out  ") == "spaced out"
    assert spoken(None) == ""


def test_a_word_count_ignores_the_mention():
    assert word_count("<@123> one two three") == 3
    assert word_count("<@123>") == 0


def test_a_long_question_needs_both_the_mark_and_the_words():
    assert word_count(LONG) > QUESTION_WORDS
    assert a_real_question(LONG) is True
    assert a_real_question(SHORT_Q) is False
    assert a_real_question(LONG.replace("?", ".")) is False


def test_staff_topics_are_matched_on_whole_words_not_fragments():
    assert about_staff("can a mod look at this") is True
    assert about_staff("I want to report someone") is True
    assert about_staff("modern art is great") is False
    assert about_staff("banner colours") is False


def test_only_a_turn_a_model_answered_counts_towards_a_conversation():
    window = [turn(), turn(IMPORTANT), turn(), turn(SIMPLE)]
    assert llm_turns(window) == 2
    assert llm_turns([]) == 0
    assert a_conversation(window) is True
    assert a_conversation([turn(SIMPLE)]) is False
    assert CONVERSATION_TURNS == 2


RULES = [
    ("a knowledge hit means the answer must be grounded", "when is the cookout", ["a hit"], [],
     IMPORTANT),
    ("a long question is a real question", LONG, [], [], IMPORTANT),
    ("a short question is still banter", SHORT_Q, [], [], SIMPLE),
    ("two model turns already means a conversation", "and then?", [],
     [turn(SIMPLE), turn(SIMPLE)], IMPORTANT),
    ("one model turn is not a conversation yet", "ha", [], [turn(SIMPLE)], SIMPLE),
    ("staff topics are never answered by the cheap tier", "is a mod around", [], [], IMPORTANT),
    ("a greeting that slipped past the intents", "heyyy", [], [], SIMPLE),
    ("a one-liner", "lol", [], [], SIMPLE),
    ("an empty message", "", [], [], SIMPLE),
]


@pytest.mark.parametrize(
    "why, message, hits, window, wanted", RULES, ids=[row[0] for row in RULES]
)
def test_the_tier_table(why, message, hits, window, wanted):
    assert tier_for(message, hits, window) == wanted


def test_a_hit_wins_over_everything_else_because_grounding_is_the_point():
    assert tier_for("lol", ["a hit"], []) == IMPORTANT


def test_the_ladder_tries_the_cheap_tier_first_then_one_expensive_attempt():
    assert ladder(SIMPLE, important=True, simple=True) == (SIMPLE, IMPORTANT)


def test_an_important_turn_never_falls_back_to_the_cheap_tier_when_both_exist():
    """A grounded answer from the wrong model is worse than the canned line."""
    assert ladder(IMPORTANT, important=True, simple=True) == (IMPORTANT,)


def test_a_tier_with_no_key_is_simply_not_on_the_list():
    assert ladder(SIMPLE, important=False, simple=True) == (SIMPLE,)
    assert ladder(SIMPLE, important=True, simple=False) == (IMPORTANT,)
    assert ladder(IMPORTANT, important=False, simple=True) == (SIMPLE,)
    assert ladder(IMPORTANT, important=True, simple=False) == (IMPORTANT,)


def test_with_no_keys_at_all_there_is_no_ladder_and_the_canned_line_answers():
    assert ladder(SIMPLE, important=False, simple=False) == ()
    assert ladder(IMPORTANT, important=False, simple=False) == ()


def test_the_forbidden_words_are_found_on_a_word_boundary():
    assert says_a_budget_word("we hit the cap for today") == "cap"
    assert says_a_budget_word("that is my limit") == "limit"
    assert says_a_budget_word("capable people wear caps") is None
    assert says_a_budget_word("Pull up a chair, friend.") is None
    assert set(BUDGET_WORDS) >= {"budget", "cap", "quota", "limit"}
