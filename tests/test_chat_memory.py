import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from black_bloc.chat_memory import (
    DM,
    RULE_AVAILABILITY,
    RULE_EVENT,
    RULE_LONG,
    RULE_QUOTE,
    RULE_SENSITIVE,
    RULE_THIRD,
    SERVER,
    Distilled,
    Note,
    Profile,
    clear_override,
    distil_prompt,
    drop_fact,
    drop_matching,
    expire,
    fact_at,
    fact_key,
    facts_of,
    forget,
    forget_everywhere,
    memory_note,
    merge,
    optout_count,
    other_names,
    overridden,
    parse_distilled,
    profile_for,
    profile_rows,
    remembered,
    remembers,
    save_profile,
    set_override,
    set_remembered,
    why_dropped,
)
from black_bloc.storage.db import Database

AT = "2026-09-02T00:00:00+00:00"

TURNS = [
    {"speaker": "member", "content": "everyone calls me Skylar but I go by Sky"},
    {"speaker": "bot", "content": "Sky it is."},
    {"speaker": "member", "content": "keep answers short please, I read on my phone"},
]


def a_profile(**kw):
    return Profile(
        call_me=kw.get("call_me", "Sky"),
        notes=kw.get("notes", (Note("likes short answers", SERVER, AT),)),
        threads=kw.get("threads", (Note("was asking about the community night", SERVER, AT),)),
        turns_seen=kw.get("turns_seen", 4),
        created_at=AT,
        updated_at=AT,
    )


async def a_db(tmp_path, name="m.sqlite3"):
    db = Database(tmp_path / name)
    await db.connect()
    return db


def test_the_prompt_names_the_json_shape_and_carries_the_turns():
    system, messages = distil_prompt(a_profile(), TURNS)
    assert '"call_me"' in system and '"notes"' in system and '"threads"' in system
    assert "JSON only" in system
    assert len(messages) == 1 and messages[0]["role"] == "user"
    said = messages[0]["content"]
    assert "likes short answers" in said
    assert "member: everyone calls me Skylar but I go by Sky" in said
    assert "bot: Sky it is." in said


def test_a_public_distillation_is_never_shown_the_dm_notes():
    profile = a_profile(
        notes=(Note("prefers she/her", DM, AT), Note("likes short answers", SERVER, AT))
    )
    _, messages = distil_prompt(profile, TURNS, where=SERVER)
    assert "she/her" not in messages[0]["content"]
    _, in_dm = distil_prompt(profile, TURNS, where=DM)
    assert "she/her" in in_dm[0]["content"]


def test_a_profile_with_nothing_in_it_still_makes_a_prompt():
    system, messages = distil_prompt(None, [])
    assert system
    assert "(nothing)" in messages[0]["content"]


def test_bad_json_is_a_no_op_rather_than_a_partial_write():
    assert parse_distilled("not json at all") is None
    assert parse_distilled("") is None
    assert parse_distilled("[1, 2, 3]") is None
    assert parse_distilled('"a string"') is None


def test_an_unknown_key_is_a_no_op():
    assert parse_distilled('{"call_me": "Sky", "mood": "happy"}') is None
    assert parse_distilled('{"notes": ["fine"], "extra": 1}') is None


def test_an_over_long_call_me_is_a_no_op():
    assert parse_distilled(json.dumps({"call_me": "S" * 41})) is None
    assert parse_distilled(json.dumps({"call_me": "S" * 40})) is not None


def test_a_code_fence_is_the_one_wrapper_tolerated():
    found = parse_distilled('```json\n{"call_me": "Sky", "notes": [], "threads": []}\n```')
    assert found is not None and found.call_me == "Sky"


def test_a_missing_key_is_an_empty_list_not_a_refusal():
    found = parse_distilled('{"call_me": null}')
    assert found is not None and found.notes == () and found.threads == ()
    assert found.empty


def test_a_note_that_is_not_a_string_is_a_no_op():
    assert parse_distilled('{"notes": [{"text": "x"}]}') is None
    assert parse_distilled('{"notes": "one note"}') is None


def test_one_bad_note_is_dropped_and_the_rest_of_the_profile_still_saves():
    found = parse_distilled(
        json.dumps(
            {
                "call_me": "Sky",
                "notes": ["likes short answers", "usually on at 9pm"],
                "threads": [],
            }
        )
    )
    assert found is not None
    assert found.call_me == "Sky"
    assert found.notes == ("likes short answers",)
    assert found.dropped == (RULE_AVAILABILITY,)


def test_a_note_may_not_quote_six_words_anybody_typed():
    said = [{"speaker": "member", "content": "keep answers short please I read on my phone"}]
    found = parse_distilled(
        json.dumps({"notes": ["keep answers short please I read on my phone"]}), turns=said
    )
    assert found is not None and found.notes == () and found.dropped == (RULE_QUOTE,)


def test_the_rules_each_name_themselves():
    assert why_dropped("") == "empty"
    assert why_dropped("x" * 121) == RULE_LONG
    assert why_dropped('said "I go by Sky"') == RULE_QUOTE
    assert why_dropped("namu said he is quitting") == RULE_THIRD
    assert why_dropped("ping <@123> for this") == RULE_THIRD
    assert why_dropped("lives in Phoenix") == RULE_AVAILABILITY
    assert why_dropped("usually on at 9") == RULE_AVAILABILITY
    assert why_dropped("was banned last month") == RULE_EVENT
    assert why_dropped("is in therapy") == RULE_SENSITIVE
    assert why_dropped("voted in the last election") == RULE_SENSITIVE
    assert why_dropped("likes short answers") is None
    assert why_dropped("goes by Sky") is None
    assert why_dropped("English is their second language, keep it simple") is None


def test_a_thread_may_be_a_topic_but_never_an_outcome():
    assert why_dropped("was asking about the Thursday event", thread=True) is None
    assert why_dropped("was asking about the Thursday event") == RULE_EVENT
    assert why_dropped("namu quitting the server", thread=True) == RULE_EVENT


def test_a_note_naming_another_member_is_dropped():
    guild = SimpleNamespace(
        members=[
            SimpleNamespace(id=1, display_name="Sky", bot=False),
            SimpleNamespace(id=2, display_name="Namu", bot=False),
            SimpleNamespace(id=3, display_name="Black Bloc", bot=True),
        ]
    )
    names = other_names(guild, 1)
    assert names == ("namu",)
    found = parse_distilled(
        json.dumps({"notes": ["is close friends with namu"]}), others=names
    )
    assert found is not None and found.notes == () and found.dropped == (RULE_THIRD,)


def test_merge_keeps_the_newest_name_and_caps_the_lists():
    old = a_profile(
        call_me="Skylar",
        notes=tuple(Note(f"old {n}", SERVER, AT) for n in range(6)),
    )
    fresh = Distilled(call_me="Sky", notes=("brand new",), threads=("a topic",))
    found = merge(old, fresh, where=SERVER, at=AT, notes_max=6, threads_max=5, seen=3)
    assert found.call_me == "Sky"
    assert len(found.notes) == 6
    assert found.notes[0].text == "brand new"
    assert found.notes[-1].text == "old 4"
    assert found.turns_seen == 7
    assert found.created_at == AT


def test_merge_dedupes_by_the_words_themselves():
    old = a_profile(notes=(Note("Likes short answers.", SERVER, AT),))
    found = merge(old, Distilled(notes=("likes short answers",)), where=SERVER, at=AT)
    assert [one.text for one in found.notes] == ["likes short answers"]


def test_a_note_learned_in_a_dm_and_again_in_the_server_stays_public():
    old = a_profile(notes=(Note("likes short answers", DM, AT),))
    found = merge(old, Distilled(notes=("likes short answers",)), where=SERVER, at=AT)
    assert [(one.text, one.where) for one in found.notes] == [("likes short answers", SERVER)]


def test_a_dm_note_never_reaches_a_public_channel():
    profile = a_profile(
        notes=(Note("prefers she/her", DM, AT), Note("likes short answers", SERVER, AT)),
        threads=(Note("was asking about a ticket", DM, AT),),
    )
    public = memory_note(profile, in_dm=False)
    assert "she/her" not in public
    assert "likes short answers" in public
    assert "ticket" not in public
    private = memory_note(profile, in_dm=True)
    assert "she/her" in private and "ticket" in private


def test_the_shared_setting_lets_a_dm_note_through_when_the_owner_asks_for_it():
    profile = a_profile(notes=(Note("prefers she/her", DM, AT),))
    assert "she/her" in memory_note(profile, in_dm=False, shared=True)


def test_the_memory_block_says_it_may_never_claim_somebody_is_online():
    said = memory_note(a_profile(), in_dm=False)
    assert "never claim" in said
    assert "they go by Sky" in said
    assert said.startswith("(") and said.endswith(")")


def test_no_profile_and_an_empty_profile_are_both_no_block_at_all():
    assert memory_note(None, in_dm=False) == ""
    assert memory_note(Profile(), in_dm=False) == ""
    assert memory_note(a_profile(call_me="", notes=(), threads=()), in_dm=True) == ""


def test_a_person_can_drop_one_note_by_a_few_of_its_words():
    profile = a_profile(
        notes=(Note("likes short answers", SERVER, AT), Note("hates emoji", SERVER, AT))
    )
    found, gone = drop_matching(profile, "emoji")
    assert gone == 1
    assert [one.text for one in found.notes] == ["likes short answers"]
    assert drop_matching(profile, "nothing like this")[1] == 0


def test_dropping_the_name_by_name_works_too():
    found, gone = drop_matching(a_profile(), "sky")
    assert gone == 1 and found.call_me == ""


def a_numbered_profile():
    return a_profile(
        notes=(Note("likes short answers", SERVER, AT), Note("prefers she/her", DM, AT)),
        threads=(Note("was asking about the cookout", SERVER, AT),),
    )


def test_the_facts_read_back_in_the_order_the_panel_numbers_them():
    facts = facts_of(a_numbered_profile())

    assert [one.kind for one in facts] == ["name", "note", "note", "thread"]
    assert [one.text for one in facts] == [
        "Sky",
        "likes short answers",
        "prefers she/her",
        "was asking about the cookout",
    ]
    assert [one.index for one in facts] == [0, 0, 1, 0]
    assert [one.where for one in facts] == [SERVER, SERVER, DM, SERVER]
    assert facts_of(None) == () and facts_of(Profile()) == ()


def test_a_fact_key_round_trips_and_a_stale_one_finds_nothing():
    profile = a_numbered_profile()
    keys = [fact_key(one) for one in facts_of(profile)]

    assert keys == ["name:0", "note:0", "note:1", "thread:0"]
    assert fact_at(profile, "note:1").text == "prefers she/her"
    assert fact_at(profile, "note:9") is None
    assert fact_at(profile, "bogus") is None and fact_at(profile, None) is None
    assert fact_at(Profile(), "name:0") is None


def test_dropping_one_fact_by_identity_leaves_every_other_one_alone():
    profile = a_numbered_profile()

    found, gone = drop_fact(profile, "note:0")

    assert gone == 1
    assert [one.text for one in found.notes] == ["prefers she/her"]
    assert found.call_me == "Sky" and len(found.threads) == 1
    assert found.turns_seen == profile.turns_seen


def test_dropping_the_name_and_a_thread_by_identity():
    profile = a_numbered_profile()

    without_name, gone = drop_fact(profile, "name:0")
    without_thread, also = drop_fact(profile, "thread:0")

    assert gone == 1 and without_name.call_me == "" and len(without_name.notes) == 2
    assert also == 1 and without_thread.threads == () and without_thread.call_me == "Sky"


def test_a_key_that_points_at_nothing_changes_nothing():
    profile = a_numbered_profile()

    found, gone = drop_fact(profile, "note:7")

    assert gone == 0 and found is profile


def test_drop_fact_takes_one_line_where_drop_matching_would_take_two():
    """Both exist on purpose: words match every line that contains them, a pick matches one."""
    profile = a_profile(
        notes=(Note("likes short answers", SERVER, AT), Note("likes short names", SERVER, AT)),
        threads=(),
    )

    assert drop_matching(profile, "likes short")[1] == 2
    assert drop_fact(profile, "note:0")[1] == 1


async def test_a_profile_is_written_read_back_and_forgotten(tmp_path):
    db = await a_db(tmp_path)
    try:
        assert await profile_for(db, 9, 7) is None
        profile = a_profile()
        assert await save_profile(db, 9, 7, profile)
        found = await profile_for(db, 9, 7)
        assert found is not None
        assert found.call_me == "Sky"
        assert [one.text for one in found.notes] == ["likes short answers"]
        assert found.notes[0].where == SERVER
        assert found.turns_seen == 4
        assert await save_profile(db, 9, 7, merge(found, Distilled(call_me="Skylar"), at=AT))
        again = await profile_for(db, 9, 7)
        assert again is not None and again.call_me == "Skylar"
        assert again.created_at == AT
        assert await forget(db, 9, 7) is True
        assert await forget(db, 9, 7) is False
        assert await profile_for(db, 9, 7) is None
    finally:
        await db.close()


async def test_a_leaver_is_forgotten_in_every_server_at_once(tmp_path):
    db = await a_db(tmp_path, "leave.sqlite3")
    try:
        await save_profile(db, 9, 7, a_profile())
        await save_profile(db, 9, 8, a_profile())
        await save_profile(db, 10, 7, a_profile())
        assert await forget_everywhere(db, 9) == 2
        assert await profile_for(db, 10, 7) is not None
    finally:
        await db.close()


def test_a_row_means_the_person_is_off_the_servers_default_whichever_way_round_it_is():
    """One table, one meaning: they overrode the default. D1 decides what the default is."""
    assert remembered("optout", False) is True
    assert remembered("optout", True) is False
    assert remembered("optin", False) is False
    assert remembered("optin", True) is True
    assert remembered("optout", None) is False
    assert remembered("optin", None) is False


async def test_a_choice_is_remembered_and_can_be_lifted(tmp_path):
    db = await a_db(tmp_path, "opt.sqlite3")
    try:
        assert await overridden(db, 9, 7) is False
        assert await remembers(db, 9, 7, consent="optout") is True
        assert await set_override(db, 9, 7, at=AT)
        assert await overridden(db, 9, 7) is True
        assert await remembers(db, 9, 7, consent="optout") is False
        assert await remembers(db, 9, 7, consent="optin") is True
        assert await optout_count(db, 7) == 1
        assert await clear_override(db, 9, 7) is True
        assert await clear_override(db, 9, 7) is False
        assert await overridden(db, 9, 7) is False
    finally:
        await db.close()


async def test_saying_off_and_on_lands_the_same_way_under_either_consent_model(tmp_path):
    db = await a_db(tmp_path, "consent.sqlite3")
    try:
        for consent in ("optout", "optin"):
            await set_remembered(db, 9, 7, consent=consent, wanted=False)
            assert await remembers(db, 9, 7, consent=consent) is False, consent
            await set_remembered(db, 9, 7, consent=consent, wanted=True)
            assert await remembers(db, 9, 7, consent=consent) is True, consent
    finally:
        await db.close()


async def test_an_unreadable_choice_table_means_nobody_is_remembered(tmp_path):
    db = await a_db(tmp_path, "broken.sqlite3")
    try:
        await db.conn.execute("DROP TABLE chat_memory_optout")
        await db.conn.commit()
        assert await overridden(db, 9, 7) is None
        assert await remembers(db, 9, 7, consent="optout") is False
        assert await remembers(db, 9, 7, consent="optin") is False
    finally:
        await db.close()


async def test_a_profile_nobody_added_to_expires_and_forever_means_forever(tmp_path):
    db = await a_db(tmp_path, "old.sqlite3")
    try:
        now = datetime.now(UTC)
        stale = (now - timedelta(days=200)).isoformat()
        fresh = (now - timedelta(days=2)).isoformat()
        await save_profile(db, 9, 7, Profile(call_me="Old", created_at=stale, updated_at=stale))
        await save_profile(db, 10, 7, Profile(call_me="New", created_at=fresh, updated_at=fresh))
        assert await expire(db, days=0, now=now) == 0
        assert await expire(db, days=180, now=now) == 1
        rows = await profile_rows(db, 7)
        assert [row["call_me"] for row in rows] == ["New"]
        assert await expire(db, days=180, now=now) == 0
    finally:
        await db.close()
