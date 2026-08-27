from datetime import UTC, datetime, timedelta

import pytest

from black_bloc.automod import (
    DEFAULT_RULES,
    RULE_ORDER,
    TIMEOUT_MAX_SECONDS,
    MessageFacts,
    RuleError,
    WindowState,
    channel_exempt,
    describe_rule,
    evaluate,
    exempt_reason,
    facts_from,
    largest_window,
    matched_words,
    normalise_rule,
    rule_config,
    rules_summary,
    validate_rules,
)

START = datetime(2026, 8, 26, 12, 0, tzinfo=UTC)
USER = 900
CHANNEL = 333


class FakeRole:
    def __init__(self, role_id):
        self.id = role_id


class FakePerms:
    def __init__(self, manage_guild=False):
        self.manage_guild = manage_guild


class FakeMember:
    def __init__(self, user_id=USER, roles=(), manage_guild=False, bot=False):
        self.id = user_id
        self.roles = [FakeRole(r) for r in roles]
        self.guild_permissions = FakePerms(manage_guild=manage_guild)
        self.bot = bot


class FakeChannel:
    def __init__(self, channel_id=CHANNEL, parent_id=None):
        self.id = channel_id
        self.parent_id = parent_id


class FakeAttachment:
    pass


class FakeMessage:
    def __init__(self, content="", mentions=(), roles=(), attachments=0, at=START, message_id=1):
        self.content = content
        self.author = FakeMember()
        self.channel = FakeChannel()
        self.id = message_id
        self.created_at = at
        self.mentions = [FakeRole(m) for m in mentions]
        self.role_mentions = [FakeRole(r) for r in roles]
        self.attachments = [FakeAttachment() for _ in range(attachments)]


def mention_message(ids, at, message_id=1):
    return FakeMessage(mentions=ids, at=at, message_id=message_id)


def rules(**overrides):
    merged = {name: dict(DEFAULT_RULES[name]) for name in RULE_ORDER}
    for name, changes in overrides.items():
        merged[name].update(changes)
    return validate_rules(merged)


def only(name, **changes):
    """Every rule off except this one, so a test asserts one rule at a time."""
    off = {other: {"enabled": False} for other in RULE_ORDER}
    off[name] = {"enabled": True, **changes}
    return rules(**off)


def test_the_defaults_are_the_incumbents_live_config():
    book = validate_rules({})
    assert book["mention_spam"] == {
        "enabled": True,
        "window_s": 30,
        "threshold": 5,
        "actions": ["delete", "warn", "timeout"],
        "timeout_s": 300,
    }
    assert book["slowmode"]["window_s"] == 4 and book["slowmode"]["threshold"] == 6
    assert book["linkspam"]["window_s"] == 1 and book["linkspam"]["threshold"] == 1
    assert book["slowmode"]["actions"] == [] and book["linkspam"]["actions"] == []
    assert [name for name in RULE_ORDER if book[name]["enabled"]] == [
        "mention_spam",
        "slowmode",
        "linkspam",
    ]


def test_five_mentions_in_thirty_seconds_fires_and_thirty_one_does_not():
    state = WindowState()
    book = only("mention_spam")
    verdicts = []
    for index in range(5):
        at = START + timedelta(seconds=index * 7.5)
        verdicts = evaluate(facts_from(mention_message([index], at, index)), state, book, now=at)
    assert [v.rule for v in verdicts] == ["mention_spam"]
    assert verdicts[0].sentence == "5 mentions in 30s"
    assert verdicts[0].actions == ("delete", "warn", "timeout")
    assert verdicts[0].timeout_s == 300

    slow = WindowState()
    for index in range(5):
        at = START + timedelta(seconds=index * 7.75)
        late = evaluate(facts_from(mention_message([index], at, index)), slow, book, now=at)
    assert late == []


def test_every_mention_counts_even_the_same_person_five_times():
    state = WindowState()
    book = only("mention_spam")
    for index in range(5):
        at = START + timedelta(seconds=index)
        verdicts = evaluate(facts_from(mention_message([7], at, index)), state, book, now=at)
    assert [v.rule for v in verdicts] == ["mention_spam"]
    assert verdicts[0].sentence == "5 mentions in 30s"


def test_everyone_and_here_each_count_as_one_mention():
    state = WindowState()
    book = only("mention_spam")
    message = FakeMessage(content="@everyone @here @everyone @here @everyone", at=START)

    verdicts = evaluate(facts_from(message), state, book, now=START)

    assert [v.rule for v in verdicts] == ["mention_spam"]
    assert verdicts[0].sentence == "5 mentions in 30s"
    assert facts_from(FakeMessage(content="mail me at me@everyone.test")).everyone_count == 1


def test_a_verdict_fires_once_and_the_next_message_starts_the_window_again():
    state = WindowState()
    book = only("mention_spam")
    for index in range(5):
        at = START + timedelta(seconds=index)
        evaluate(facts_from(mention_message([index], at, index)), state, book, now=at)

    apology = FakeMessage(content="sorry", at=START + timedelta(seconds=6), message_id=99)
    after = evaluate(facts_from(apology), state, book, now=START + timedelta(seconds=6))
    assert after == []

    one_more = mention_message([9], START + timedelta(seconds=7), 100)
    assert evaluate(facts_from(one_more), state, book, now=START + timedelta(seconds=7)) == []


def test_one_message_mentioning_five_people_fires():
    state = WindowState()
    message = FakeMessage(mentions=[1, 2, 3], roles=[4, 5], at=START)

    verdicts = evaluate(facts_from(message), state, only("mention_spam"), now=START)

    assert [v.rule for v in verdicts] == ["mention_spam"]
    assert verdicts[0].message_ids == (1,)


def test_one_member_never_trips_anothers_window():
    state = WindowState()
    book = only("mention_spam")
    for index in range(4):
        at = START + timedelta(seconds=index)
        evaluate(facts_from(mention_message([index], at, index)), state, book, now=at)
    verdicts = evaluate(
        MessageFacts(
            author_id=USER + 1,
            channel_id=CHANNEL,
            message_id=9,
            created_at=START + timedelta(seconds=5),
            mention_ids=(99,),
        ),
        state,
        book,
        now=START + timedelta(seconds=5),
    )

    assert verdicts == []


def test_slowmode_counts_messages_and_linkspam_counts_links():
    state = WindowState()
    book = only("slowmode")
    for index in range(6):
        at = START + timedelta(seconds=index * 0.5)
        verdicts = evaluate(facts_from(FakeMessage(content="hi", at=at, message_id=index)), state,
                            book, now=at)
    assert [v.rule for v in verdicts] == ["slowmode"]
    assert verdicts[0].sentence == "6 messages in 4s"
    assert verdicts[0].actions == ()

    links = evaluate(
        facts_from(FakeMessage(content="see https://example.com now", at=START)),
        WindowState(),
        only("linkspam"),
        now=START,
    )
    assert [v.rule for v in links] == ["linkspam"] and links[0].sentence == "1 link in 1s"


def test_invites_attachments_caps_and_bad_words():
    invite = evaluate(
        facts_from(FakeMessage(content="join discord.gg/abc123", at=START)),
        WindowState(),
        only("invitespam"),
        now=START,
    )
    assert [v.rule for v in invite] == ["invitespam"]

    files = evaluate(
        facts_from(FakeMessage(attachments=5, at=START)),
        WindowState(),
        only("attachmentspam"),
        now=START,
    )
    assert [v.rule for v in files] == ["attachmentspam"]

    shouting = evaluate(
        facts_from(FakeMessage(content="STOP DOING THAT", at=START)),
        WindowState(),
        only("caps", threshold=70),
        now=START,
    )
    assert [v.rule for v in shouting] == ["caps"] and "capitals" in shouting[0].sentence

    quiet = evaluate(
        facts_from(FakeMessage(content="SHH", at=START)),
        WindowState(),
        only("caps", threshold=70),
        now=START,
    )
    assert quiet == []

    words = evaluate(
        facts_from(FakeMessage(content="you are a Grifter, mate", at=START)),
        WindowState(),
        only("bad_words", words=["grifter"]),
        now=START,
    )
    assert [v.rule for v in words] == ["bad_words"]


def test_bad_words_never_match_inside_another_word():
    assert matched_words("classic", ["ass"]) == []
    assert matched_words("what an ASS", ["ass"]) == ["ass"]


def test_facts_extraction_reads_mentions_links_invites_and_capitals():
    facts = facts_from(
        FakeMessage(
            content="HEY https://a.test and discord.gg/xyz",
            mentions=[1, 2],
            roles=[3],
            attachments=2,
        )
    )
    assert facts.mention_ids == (1, 2, 3)
    assert facts.links == ("https://a.test",)
    assert facts.invite_count == 1
    assert facts.attachment_count == 2
    assert facts.capitals == 3 and facts.letters == 28
    assert 0 < facts.caps_ratio < 1


def test_a_message_with_no_timestamp_still_produces_facts():
    message = FakeMessage(at=None)
    message.created_at = None

    facts = facts_from(message)

    assert facts.created_at.tzinfo is not None


def test_the_window_is_bounded_by_the_largest_window():
    state = WindowState()
    book = only("mention_spam")
    for index in range(200):
        at = START + timedelta(seconds=index)
        evaluate(facts_from(mention_message([index], at, index)), state, book, now=at)
    assert len(state) <= 31
    assert largest_window(book) == 30


def test_forgetting_a_member_empties_their_windows():
    state = WindowState()
    evaluate(facts_from(mention_message([1], START, 1)), state, only("mention_spam"), now=START)
    assert len(state) == 1

    state.forget(USER)

    assert len(state) == 0


def test_a_disabled_rule_never_fires():
    state = WindowState()
    book = rules(mention_spam={"enabled": False})
    for index in range(9):
        at = START + timedelta(seconds=index)
        verdicts = evaluate(facts_from(mention_message([index], at, index)), state, book, now=at)
    assert [v.rule for v in verdicts] == []


def test_the_exemption_matrix():
    staff = {5}
    exempt = {6}
    assert exempt_reason(FakeMember(bot=True), staff, exempt) == "bot"
    assert exempt_reason(FakeMember(manage_guild=True), staff, exempt) == "manage_guild"
    assert exempt_reason(FakeMember(roles=(5,)), staff, exempt) == "staff"
    assert exempt_reason(FakeMember(roles=(6,)), staff, exempt) == "exempt_role"
    assert exempt_reason(FakeMember(roles=(7,)), staff, exempt) is None


def test_exempt_and_honeypot_channels_and_their_threads_are_skipped():
    assert channel_exempt(FakeChannel(10), {10}, set()) is True
    assert channel_exempt(FakeChannel(11), set(), {11}) is True
    assert channel_exempt(FakeChannel(12, parent_id=10), {10}, set()) is True
    assert channel_exempt(FakeChannel(13), {10}, {11}) is False


def test_rule_validation_refuses_what_discord_would_refuse():
    with pytest.raises(RuleError):
        validate_rules({"nonsense": {}})
    with pytest.raises(RuleError):
        normalise_rule("mention_spam", {"actions": ["explode"]})
    with pytest.raises(RuleError):
        normalise_rule("mention_spam", {"timeout_s": TIMEOUT_MAX_SECONDS + 1})
    with pytest.raises(RuleError):
        normalise_rule("mention_spam", {"threshold": 0})
    with pytest.raises(RuleError):
        normalise_rule("caps", {"threshold": 101})
    with pytest.raises(RuleError):
        normalise_rule("mention_spam", {"enabled": "yes"})
    with pytest.raises(RuleError):
        normalise_rule("mention_spam", {"colour": "red"})
    assert normalise_rule("mention_spam", {"actions": "warn, delete"})["actions"] == [
        "delete",
        "warn",
    ]
    assert normalise_rule("bad_words", {"words": "A, b, a"})["words"] == ["a", "b"]


def test_a_broken_rule_book_falls_back_to_the_default_rather_than_raising():
    assert rule_config({"mention_spam": {"threshold": -1}}, "mention_spam") == DEFAULT_RULES[
        "mention_spam"
    ]
    assert rule_config("not a dict", "slowmode")["window_s"] == 4


def test_the_summary_names_the_armed_rules():
    assert "mention_spam 5/30s delete+warn+timeout" in rules_summary(validate_rules({}))
    assert rules_summary({name: {"enabled": False} for name in RULE_ORDER}) == "every rule is off"
    assert "log only" in describe_rule("slowmode", rule_config({}, "slowmode"))
