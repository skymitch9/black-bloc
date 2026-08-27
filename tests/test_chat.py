import random

import pytest

from black_bloc.chat import (
    ATTENDEE_LINES,
    INTENTS,
    LINE_LIMIT,
    LINES,
    ORDER,
    UNKNOWN,
    attendees_for,
    classify,
    display_name,
    normalise,
    reply_for,
    respond,
)


class FakeMember:
    def __init__(self, display=None, name=None, guild=None):
        if display is not None:
            self.display_name = display
        if name is not None:
            self.name = name
        if guild is not None:
            self.guild = guild


class FakeGuild:
    def __init__(self, member_count=None, members=()):
        self.id = 7
        self.member_count = member_count
        self.members = list(members)


class FakeBot:
    def __init__(self, guilds=()):
        self.guilds = list(guilds)


@pytest.mark.parametrize(
    "text, intent",
    [
        ("hi", "greeting"),
        ("hey there black bloc", "greeting"),
        ("good morning everyone", "greeting"),
        ("yo", "greeting"),
        ("wassup", "greeting"),
        ("thanks!", "thanks"),
        ("thank you so much", "thanks"),
        ("ty", "thanks"),
        ("how are you today", "how_are_you"),
        ("hows it going", "how_are_you"),
        ("you good?", "how_are_you"),
        ("what can you do", "what_can_you_do"),
        ("who are you exactly", "what_can_you_do"),
        ("help", "help"),
        ("how do i join a voice channel", "help"),
        ("i love you", "love"),
        ("good bot", "love"),
        ("ily", "love"),
        ("you suck", "insult"),
        ("shut up", "insult"),
        ("bad bot", "insult"),
        ("the cookout is at six on saturday", UNKNOWN),
        ("", UNKNOWN),
        ("   ", UNKNOWN),
    ],
)
def test_classify_reads_each_intent(text, intent):
    assert classify(text) == intent


@pytest.mark.parametrize(
    "text",
    ["this is a thing", "think about it", "history", "yolo", "supply run", "helpful people"],
)
def test_classify_matches_whole_words_not_substrings(text):
    assert classify(text) == UNKNOWN


def test_classify_strips_the_mention_and_ignores_case():
    assert classify("<@123456789> HI!!!") == "greeting"
    assert classify("<@!123456789> Thank You") == "thanks"
    assert classify("<@&999> <@123> How Are You?") == "how_are_you"


def test_classify_reads_a_heart_as_love():
    assert classify("<@123> ❤") == "love"
    assert classify("<@123> <3") == "love"


def test_classify_reads_apostrophes_the_same_either_way():
    assert classify("what's up") == "greeting"
    assert classify("whats up") == "greeting"
    assert classify("you're the best") == "love"


def test_an_insult_never_reads_as_a_greeting():
    assert classify("hey you suck") == "insult"


def test_normalise_leaves_words_only():
    assert normalise("<@42> Hey!!! How's it going?") == "hey hows it going"


def test_every_intent_has_at_least_five_lines():
    for intent in (*ORDER, UNKNOWN):
        assert len(LINES[intent]) >= 5, intent


def test_every_intent_in_the_table_has_lines_and_the_other_way_round():
    assert set(INTENTS) == set(ORDER)
    assert set(LINES) == set(ORDER) | {UNKNOWN}
    assert set(ATTENDEE_LINES) <= set(LINES)


def test_no_line_is_longer_than_the_limit():
    for intent, lines in (*LINES.items(), *ATTENDEE_LINES.items()):
        for line in lines:
            rendered = line.format(name="Someveryverylongnickname", attendees=1234)
            assert len(rendered) <= LINE_LIMIT, (intent, rendered)


def test_the_unknown_lines_all_point_at_help():
    assert all("/help" in line for line in LINES[UNKNOWN])


def test_respond_puts_the_name_in():
    for intent in (*ORDER, UNKNOWN):
        said = respond(intent, name="Nia", rng=random.Random(1))
        assert "Nia" in said
        assert "{name}" not in said


def test_respond_is_seedable():
    first = respond("greeting", name="Nia", rng=random.Random(4))
    again = respond("greeting", name="Nia", rng=random.Random(4))
    assert first == again


def test_respond_only_offers_the_attendee_lines_when_there_is_a_count():
    without = {respond("greeting", name="Nia", rng=random.Random(s)) for s in range(60)}
    assert not any("cookout attendees" in line.lower() for line in without)
    with_count = {
        respond("greeting", name="Nia", attendees=412, rng=random.Random(s)) for s in range(60)
    }
    assert any("412" in line for line in with_count)


def test_an_unknown_intent_name_falls_back_to_the_unknown_lines():
    said = respond("nonsense", name="Nia", rng=random.Random(2))
    assert "/help" in said


def test_display_name_prefers_the_nickname_and_has_a_fallback():
    assert display_name(FakeMember(display="Nia", name="nia_x")) == "Nia"
    assert display_name(FakeMember(name="nia_x")) == "nia_x"
    assert display_name(object()) == "friend"


def test_attendees_come_from_the_members_guild_then_the_bots():
    guild = FakeGuild(member_count=10, members=[FakeMember(display="b")])
    guild.members[0].bot = True
    member = FakeMember(display="Nia", guild=guild)
    assert attendees_for(member, FakeBot()) == 9
    assert attendees_for(FakeMember(display="Nia"), FakeBot(guilds=[guild])) == 9
    assert attendees_for(FakeMember(display="Nia"), FakeBot()) is None


def test_reply_for_is_the_one_seam_and_answers_in_the_bots_voice():
    said = reply_for("<@1> hi", FakeMember(display="Nia"), FakeBot(), rng=random.Random(0))
    assert "Nia" in said
    assert len(said) <= LINE_LIMIT
