import random
import re
from types import SimpleNamespace

import pytest

from black_bloc.chat import (
    ATTENDEE,
    ATTENDEE_LINES,
    BUILTIN_KINDS,
    BUILTIN_NAMES,
    BUILTIN_ORDER,
    CANNED,
    DATA,
    DATA_INTENTS,
    DATA_LINES,
    EMPTY,
    FILLED,
    INTENTS,
    LINE_LIMIT,
    LINES,
    ORDER,
    ROUTE,
    ROUTE_INTENTS,
    ROUTE_LINES,
    UNKNOWN,
    ChatError,
    add_line,
    attendees_for,
    bare_greeting,
    classify,
    clean_name,
    clean_slot,
    clean_text,
    clean_triggers,
    create_intent,
    delete_intent,
    display_name,
    guild_intents,
    invalidate,
    kind_of,
    lines_for,
    list_intents,
    loaded_intents,
    mentioned_user_ids,
    normalise,
    others_mentioned,
    pool,
    render,
    reply_for,
    respond,
    seed_defaults,
    tokens_of,
    top_up_triggers,
    update_intent,
    update_line,
    with_extra,
)
from black_bloc.emoji import SKIN_TONES

WAVE = "\U0001f44b"
HEART = "\U0001f5a4"
DARK = SKIN_TONES["dark"]


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


SELF_SERVICE = [
    # The owner's own sentence, 2026-09-01: it was answered "hit up @Admin".
    ("i want to host an event, can you show me how to do that", "host_an_event", "/event"),
    ("how do i make an event", "host_an_event", "/event"),
    ("can i file a request", "file_a_request", "/request"),
    ("i want to make a suggestion", "file_a_request", "/request"),
    ("how do i link my twitch", "link_twitch", "/golive"),
    ("can you announce my streams", "link_twitch", "/golive"),
    ("how do i set my birthday", "set_a_birthday", "/birthday"),
    ("where do i add my birthday", "set_a_birthday", "/birthday"),
]


@pytest.mark.parametrize(
    "said, intent, command", SELF_SERVICE, ids=[row[0] for row in SELF_SERVICE]
)
def test_the_bot_names_its_own_command_instead_of_sending_somebody_to_staff(said, intent, command):
    assert classify(f"<@1> {said}") == intent
    assert all(command in line for line in LINES[intent]), intent


def test_asking_for_roles_lands_on_the_role_menus_rather_than_on_who_holds_what():
    assert classify("<@1> how do i get roles") == "my_roles"
    assert classify("<@1> where are the role menus") == "my_roles"
    assert classify("<@1> who has the lead role") == "who_has"


def test_the_new_self_service_intents_do_not_swallow_the_questions_that_came_first():
    assert classify("<@1> whats the next event") == "whats_next"
    assert classify("<@1> whose birthday is it") == "birthdays"
    assert classify("<@1> i need a mod") == "need_a_mod"
    assert classify("<@1> whos streaming") == "who_is_live"


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


async def test_reply_for_is_the_one_seam_and_answers_in_the_bots_voice():
    said = await reply_for("<@1> hi", FakeMember(display="Nia"), FakeBot(), rng=random.Random(0))
    assert "Nia" in said
    assert len(said) <= LINE_LIMIT


class PicksTheGesture:
    @staticmethod
    def choice(options):
        return next(line for line in options if WAVE in line)


class TonedBot(FakeBot):
    def __init__(self, tone):
        super().__init__()
        self.store = SimpleNamespace(get=lambda guild_id, key: tone)


async def test_a_gesture_in_a_line_comes_out_dark_by_default():
    member = FakeMember(display="Nia", guild=FakeGuild())

    said = await reply_for("<@1> hi", member, FakeBot(), rng=PicksTheGesture)

    assert WAVE + DARK in said and WAVE + " " not in said


async def test_a_guild_that_picked_another_tone_gets_it():
    member = FakeMember(display="Nia", guild=FakeGuild())

    said = await reply_for("<@1> hi", member, TonedBot("light"), rng=PicksTheGesture)

    assert WAVE + SKIN_TONES["light"] in said


async def test_tone_none_leaves_the_gesture_bare():
    member = FakeMember(display="Nia", guild=FakeGuild())

    said = await reply_for("<@1> hi", member, TonedBot("none"), rng=PicksTheGesture)

    assert WAVE in said and not any(mark in said for mark in SKIN_TONES.values() if mark)


async def test_a_heart_in_a_line_is_left_exactly_as_written():
    picks_the_heart = SimpleNamespace(
        choice=lambda options: next(line for line in options if HEART in line)
    )
    member = FakeMember(display="Nia", guild=FakeGuild())

    said = await reply_for("<@1> love you", member, FakeBot(), rng=picks_the_heart)

    assert HEART in said and DARK not in said


def test_no_line_is_written_with_a_tone_already_on_it():
    """The tone is a setting applied at send time, so the tables stay bare."""
    written = [line for lines in LINES.values() for line in lines]
    written += [line for lines in ATTENDEE_LINES.values() for line in lines]
    for table in (DATA_LINES, ROUTE_LINES):
        written += [line for slots in table.values() for lines in slots.values() for line in lines]
    assert not any(mark in line for line in written for mark in SKIN_TONES.values() if mark)


GUILD = 7


class StoredBot(FakeBot):
    """A bot with a database, which is all `guild_intents` needs to read a guild's rows."""

    def __init__(self, db, guilds=()):
        super().__init__(guilds=guilds)
        self.db = db


async def rows(db, guild_id=GUILD):
    return await loaded_intents(db, guild_id)


async def named(db, name, guild_id=GUILD):
    return next(row for row in await list_intents(db, guild_id) if row["name"] == name)


async def test_the_seed_puts_every_built_in_intent_in_reach_of_the_page(db):
    made = await seed_defaults(db, GUILD, by=1)

    stored = {row["name"]: row for row in await rows(db)}
    assert made == len(stored) == len(BUILTIN_ORDER) + 1
    assert set(stored) == set(BUILTIN_ORDER) | {UNKNOWN}
    assert stored["greeting"]["kind"] == CANNED
    assert stored["who_is_live"]["kind"] == DATA
    assert stored["need_a_mod"]["kind"] == ROUTE
    assert stored["greeting"]["triggers"] == INTENTS["greeting"]
    assert set(stored["greeting"]["lines"][FILLED]) == set(LINES["greeting"])
    assert set(stored["greeting"]["lines"][ATTENDEE]) == set(ATTENDEE_LINES["greeting"])


async def test_every_data_and_route_intent_is_seeded_with_both_states(db):
    await seed_defaults(db, GUILD)

    stored = {row["name"]: row for row in await rows(db)}
    for name in (*DATA_INTENTS, *ROUTE_INTENTS):
        assert stored[name]["lines"][FILLED], name
        assert stored[name]["lines"][EMPTY], name


async def test_seeding_twice_changes_nothing_and_leaves_edits_alone(db):
    await seed_defaults(db, GUILD)
    before = {row["name"]: row["id"] for row in await rows(db)}
    greeting = await named(db, "greeting")
    line = (await lines_for(db, greeting["id"]))[0]
    await update_line(db, line["id"], text="Edited hello, {name}.")

    assert await seed_defaults(db, GUILD) == 0

    assert {row["name"]: row["id"] for row in await rows(db)} == before
    stored = {row["name"]: row for row in await rows(db)}
    assert "Edited hello, {name}." in stored["greeting"]["lines"][FILLED]


async def test_a_guild_seeded_before_a_new_built_in_gets_it_on_the_next_pass(db):
    """How a NEW built-in reaches an old guild: `seed_defaults` runs again every startup."""
    await seed_defaults(db, GUILD)
    before = await named(db, "who_has")
    await delete_intent(db, before["id"])

    assert await seed_defaults(db, GUILD) == 1

    stored = {row["name"]: row for row in await rows(db)}
    assert stored["who_has"]["kind"] == DATA
    assert stored["who_has"]["triggers"] == DATA_INTENTS["who_has"]
    assert stored["who_has"]["lines"][FILLED] and stored["who_has"]["lines"][EMPTY]


async def test_a_new_built_in_answers_from_the_code_table_before_its_row_lands(db):
    await seed_defaults(db, GUILD)
    row = await named(db, "who_has")
    await delete_intent(db, row["id"])

    stored = await rows(db)

    assert classify("whos a lead", stored) == "who_has"
    assert kind_of("who_has", stored) == DATA
    assert pool("who_has", intents=stored, slot=FILLED) == DATA_LINES["who_has"][FILLED]


async def test_a_second_guild_gets_its_own_copy(db):
    await seed_defaults(db, GUILD)
    assert await seed_defaults(db, 8) == len(BUILTIN_ORDER) + 1
    assert len(await rows(db, 8)) == len(BUILTIN_ORDER) + 1


def test_with_no_rows_at_all_the_code_tables_still_answer():
    assert classify("hi there", ()) == "greeting"
    assert respond("greeting", name="Nia", rng=random.Random(0), intents=()) in [
        line.format(name="Nia", attendees=None) for line in LINES["greeting"]
    ]


async def test_an_intent_whose_lines_are_all_disabled_falls_back_to_the_code_table(db):
    await seed_defaults(db, GUILD)
    greeting = await named(db, "greeting")
    for line in await lines_for(db, greeting["id"]):
        await update_line(db, line["id"], enabled=False)

    said = respond("greeting", name="Nia", rng=random.Random(0), intents=await rows(db))

    assert said in [line.format(name="Nia", attendees=None) for line in LINES["greeting"]]


async def test_a_guilds_own_line_is_used_over_the_code_one(db):
    await seed_defaults(db, GUILD)
    greeting = await named(db, "greeting")
    for line in await lines_for(db, greeting["id"]):
        await update_line(db, line["id"], enabled=False)
    await add_line(db, greeting["id"], "Only line, {name}.")

    assert respond("greeting", name="Nia", intents=await rows(db)) == "Only line, Nia."


async def test_turning_off_the_head_count_lines_actually_turns_them_off(db):
    """The code table is the fallback for an ANSWER, never for the optional extras."""
    await seed_defaults(db, GUILD)
    greeting = await named(db, "greeting")
    for line in await lines_for(db, greeting["id"]):
        if line["slot"] == ATTENDEE:
            await update_line(db, line["id"], enabled=False)

    stored = await rows(db)

    assert not any(
        "{attendees}" in line for line in pool("greeting", 12, stored)
    )
    assert "{attendees}" in " ".join(pool("greeting", 12, ()))


async def test_a_custom_intent_beats_a_built_in_one(db):
    await seed_defaults(db, GUILD)
    made = await create_intent(db, GUILD, "cookout_hours", ["hi", "when is the cookout"])
    await add_line(db, made, "Doors at six, {name}.")

    stored = await rows(db)

    assert classify("hi", stored) == "cookout_hours"
    assert respond("cookout_hours", name="Nia", intents=stored) == "Doors at six, Nia."


async def test_custom_intents_are_tried_in_the_order_staff_put_them_in(db):
    later = await create_intent(db, GUILD, "second", ["cookout"], sort=5)
    await add_line(db, later, "second")
    sooner = await create_intent(db, GUILD, "first", ["cookout"], sort=1)
    await add_line(db, sooner, "first")

    assert classify("is there a cookout", await rows(db)) == "first"


async def test_a_custom_intent_with_nothing_to_say_is_skipped(db):
    """An empty intent must not swallow a message a built-in could still answer."""
    await create_intent(db, GUILD, "empty_one", ["hi"])

    assert classify("hi", await rows(db)) == "greeting"


async def test_a_disabled_built_in_falls_through_to_the_next_one(db):
    await seed_defaults(db, GUILD)
    await update_intent(db, (await named(db, "greeting"))["id"], enabled=False)

    assert classify("hi", await rows(db)) == UNKNOWN


async def test_a_disabled_love_intent_stops_the_heart_shortcut_too(db):
    await seed_defaults(db, GUILD)
    await update_intent(db, (await named(db, "love"))["id"], enabled=False)

    assert classify("❤", await rows(db)) == UNKNOWN


async def test_edited_triggers_are_what_classification_reads(db):
    await seed_defaults(db, GUILD)
    await update_intent(db, (await named(db, "greeting"))["id"], triggers=["ahoy"])

    stored = await rows(db)

    assert classify("ahoy", stored) == "greeting"
    assert classify("hi", stored) == UNKNOWN


def test_the_built_in_tables_all_line_up():
    assert set(BUILTIN_ORDER) | {UNKNOWN} == set(BUILTIN_NAMES)
    assert set(BUILTIN_KINDS) == set(BUILTIN_NAMES)
    assert set(DATA_INTENTS) == set(DATA_LINES)
    assert set(ROUTE_INTENTS) == set(ROUTE_LINES)


@pytest.mark.parametrize(
    "text, intent",
    [
        ("whos live right now", "who_is_live"),
        ("anyone streaming", "who_is_live"),
        ("whats next", "whats_next"),
        ("when is the next thing", "whats_next"),
        ("any birthdays coming", "birthdays"),
        ("whose birthday is it", "birthdays"),
        ("how many of us are here", "head_count"),
        ("member count", "head_count"),
        ("what roles can i pick", "my_roles"),
        ("my roles", "my_roles"),
        ("what time is that for me", "time_for_me"),
        ("in my time zone", "time_for_me"),
        ("i need a mod", "need_a_mod"),
        ("staff please", "need_a_mod"),
        ("help me", "need_a_mod"),
        ("whos a lead", "who_has"),
        ("who is a mentor", "who_has"),
        ("who are the leads", "who_has"),
        ("tell me who's a mentor", "who_has"),
        ("who has the mentor role", "who_has"),
        ("whos our leads", "who_has"),
        ("whos got the mod hat", "who_has"),
        ("who is the auntie around here", "who_has"),
    ],
)
def test_the_data_and_route_phrases_land_on_their_own_intents(text, intent):
    assert classify(text) == intent


def test_a_birthday_question_is_not_read_as_the_next_event():
    """`when is the next` is a whats_next phrase, so birthdays has to be asked first."""
    assert classify("when is the next birthday") == "birthdays"


@pytest.mark.parametrize(
    "text, intent",
    [
        ("who is live", "who_is_live"),
        ("whos streaming", "who_is_live"),
        ("who are you", "what_can_you_do"),
        ("who are you exactly", "what_can_you_do"),
        ("who is the best bot", "love"),
    ],
)
def test_asking_who_does_not_swallow_the_questions_that_came_first(text, intent):
    assert classify(text) == intent


def test_every_token_a_seeded_line_uses_is_one_the_page_advertises():
    """The token help is a promise: a chip the page shows has to render."""
    for table in (DATA_LINES, ROUTE_LINES):
        for intent, slots in table.items():
            allowed = {"name", "attendees"} | {one.strip("{}") for one in tokens_of(intent)}
            for lines in slots.values():
                for line in lines:
                    used = set(re.findall(r"\{([a-z_]+)\}", line))
                    assert used <= allowed, f"{intent}: {sorted(used - allowed)}"


def test_a_canned_intent_advertises_no_tokens_of_its_own():
    assert tokens_of("greeting") == ()
    assert tokens_of("head_count") == ("{count}",)
    assert tokens_of("nothing_like_it") == ()


def test_the_kind_of_an_intent_is_known_without_any_rows():
    assert kind_of("greeting") == CANNED
    assert kind_of("head_count") == DATA
    assert kind_of("need_a_mod") == ROUTE
    assert kind_of("nothing_like_it") == CANNED


def test_a_data_line_renders_its_own_tokens():
    said = respond(
        "head_count", name="Nia", slot=FILLED, tokens={"count": 412}, rng=random.Random(0)
    )
    assert "412" in said and "Nia" in said


def test_an_empty_state_uses_the_empty_line_rather_than_the_filled_one():
    said = respond("who_is_live", name="Nia", slot=EMPTY, rng=random.Random(0))
    assert said in [line.format(name="Nia") for line in DATA_LINES["who_is_live"][EMPTY]]


def test_a_token_nobody_filled_in_is_left_as_typed_rather_than_raising():
    assert render("Doors at {when}, {name}.", {"name": "Nia"}) == "Doors at {when}, Nia."


def test_a_line_with_broken_bracing_is_sent_as_written():
    assert render("half a {token", {"name": "Nia"}) == "half a {token"


def test_a_bare_hello_is_told_apart_from_a_sentence_that_starts_with_one():
    assert bare_greeting("<@1> hi") is True
    assert bare_greeting("  Hey!  ") is True
    assert bare_greeting("<@1> hi, when is the cookout") is False
    assert bare_greeting("") is False


async def test_the_cache_is_read_once_and_dropped_when_something_is_saved(db):
    bot = StoredBot(db)
    await seed_defaults(db, GUILD)

    first = await guild_intents(bot, GUILD)
    await update_intent(db, (await named(db, "greeting"))["id"], triggers=["ahoy"])

    assert await guild_intents(bot, GUILD) is first
    invalidate(bot, GUILD)
    assert classify("ahoy", await guild_intents(bot, GUILD)) == "greeting"


async def test_a_dm_and_a_bot_with_no_database_both_read_no_rows(db):
    assert await guild_intents(StoredBot(db), None) == ()
    assert await guild_intents(FakeBot(), GUILD) == ()


def test_a_new_intents_name_has_to_be_one_black_bloc_can_store():
    assert clean_name(" Cookout Hours ") == "cookout_hours"
    for given in ("", "9lives", "hey there!", "x" * 61):
        with pytest.raises(ChatError):
            clean_name(given)


def test_a_new_intent_cannot_take_a_built_in_name():
    with pytest.raises(ChatError) as caught:
        clean_name("greeting")
    assert "greeting" in str(caught.value)


def test_triggers_are_tidied_de_duplicated_and_capped():
    assert clean_triggers([" hi ", "hi", "good  morning"]) == ["hi", "good morning"]
    assert clean_triggers("hi, there") == ["hi", "there"]
    for given in ([], [""], ["x" * 61], [f"p{n}" for n in range(41)]):
        with pytest.raises(ChatError):
            clean_triggers(given)


BOT = SimpleNamespace(user=SimpleNamespace(id=55))


def test_a_trust_question_only_lands_when_somebody_was_actually_pointed_at():
    for said in ("<@4001> is a mod", "<@4001> can i trust", "<@4001> is staff"):
        assert classify(said, mentions_member=True) == "about_member", said
        assert classify(said) != "about_member", said


def test_asking_who_holds_a_role_still_reaches_who_has_when_nobody_is_named():
    assert classify("whos a mod") == "who_has"
    assert classify("who is a lead") == "who_has"
    assert classify("who has the leads role") == "who_has"


def test_looking_for_a_mod_never_reaches_a_model():
    """The owner's live phrasing, 2026-09-01."""
    assert classify("im looking for a mod") == "need_a_mod"
    assert classify("looking for a mod") == "need_a_mod"
    assert classify("i am looking for a mod right now") == "need_a_mod"


def test_the_owners_live_sentence_answers_the_trust_question_first():
    said = "im looking for a mod can i trust <@4001>"
    assert classify(said, mentions_member=True) == "about_member"


def test_black_blocs_own_mention_is_not_somebody_being_pointed_at():
    assert mentioned_user_ids("<@55> <@!4001> <@&900> hi") == (55, 4001)
    assert others_mentioned("<@55> hi", BOT) == ()
    assert others_mentioned("<@55> <@4001> hi", BOT) == (4001,)
    assert others_mentioned("<@4001> hi", SimpleNamespace()) == (4001,)


def test_a_sentence_a_stored_line_could_not_carry_is_appended_once():
    assert with_extra("Staff to ask.", {"extra": " Online: A."}) == "Staff to ask. Online: A."
    assert with_extra("Staff to ask. Online: A.", {"extra": " Online: A."}) == (
        "Staff to ask. Online: A."
    )
    assert with_extra("Staff to ask.", {}) == "Staff to ask."
    assert with_extra("Staff to ask.", None) == "Staff to ask."


async def test_a_phrase_added_to_a_built_in_reaches_a_guild_seeded_before_it(db):
    """The row already exists in every live guild, so a code-table edit needs a top-up."""
    await seed_defaults(db, GUILD)
    row = await named(db, "need_a_mod")
    await update_intent(db, row["id"], triggers=["i need a mod", "a phrase staff added"])

    assert await top_up_triggers(db, GUILD) == len(ROUTE_INTENTS["need_a_mod"]) - 1

    stored = {one["name"]: one for one in await rows(db)}
    assert "a phrase staff added" in stored["need_a_mod"]["triggers"]
    assert "looking for a mod" in stored["need_a_mod"]["triggers"]
    assert classify("im looking for a mod", await rows(db)) == "need_a_mod"


async def test_the_top_up_is_idempotent_and_never_touches_an_intent_of_your_own(db):
    await seed_defaults(db, GUILD)
    mine = await create_intent(db, GUILD, "cookout_hours", ["when is the cookout"])

    assert await top_up_triggers(db, GUILD) == 0

    stored = {one["name"]: one for one in await rows(db)}
    assert stored["cookout_hours"]["triggers"] == ("when is the cookout",)
    assert mine


def test_a_line_needs_words_and_a_slot_has_to_be_one_of_three():
    assert clean_text("  hello  ") == "hello"
    assert clean_slot(None) == FILLED
    for given in ("   ", "x" * 501):
        with pytest.raises(ChatError):
            clean_text(given)
    with pytest.raises(ChatError):
        clean_slot("somewhere")
