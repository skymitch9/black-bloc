from types import SimpleNamespace

import pytest

from black_bloc.chat_data import HOLDERS_SHOWN
from black_bloc.knowledge import (
    ALL_OF,
    ANY_OF,
    BODY_LIMIT,
    GROUNDING_BYTES,
    SERVER,
    STAFF,
    STRONG_SCORE,
    TITLE_LIMIT,
    TITLE_WEIGHT,
    KnowledgeError,
    add_section,
    channel_sections,
    clean_body,
    clean_source,
    clean_tag,
    clean_title,
    event_section,
    get_section,
    grounding,
    is_strong,
    list_sections,
    menu_section,
    remove_section,
    replace_server_sections,
    role_holder_sections,
    role_sections,
    score,
    search,
    shorten,
    snippet_of,
    tokenize,
    update_section,
    whole_word,
)
from black_bloc.storage.db import Database

NOTES = [
    {"id": 1, "title": "Cookout hours", "body": "The cookout runs Friday evenings.",
     "tag": "events", "source": STAFF},
    {"id": 2, "title": "Rules", "body": "Be kind. No spam. Staff decide the rest.", "tag": "",
     "source": STAFF},
    {"id": 3, "title": "#general", "body": "Chat about anything. The cookout lives here.",
     "tag": "channel", "source": SERVER},
]


def test_tokens_are_deduped_short_words_dropped_and_the_list_is_bounded():
    assert tokenize("Cookout the COOKOUT hours") == ("cookout", "the", "hours")
    assert tokenize("a b cd") == ("cd",)
    assert len(tokenize(" ".join(str(n) * 3 for n in range(20)))) == 8
    assert tokenize("") == ()


def test_a_title_hit_outscores_a_tag_hit_which_outscores_a_body_hit():
    note = {"title": "cookout", "tag": "", "body": ""}
    tagged = {"title": "", "tag": "cookout", "body": ""}
    written = {"title": "", "tag": "", "body": "cookout"}
    assert score(note, ("cookout",), ALL_OF) == 8
    assert score(tagged, ("cookout",), ALL_OF) == 4
    assert score(written, ("cookout",), ALL_OF) == 1


def test_body_occurrences_add_up_but_stop_counting_at_five():
    note = {"title": "", "tag": "", "body": "cookout " * 20}
    assert score(note, ("cookout",), ALL_OF) == 5


def test_a_pass_that_wants_every_token_refuses_a_row_that_has_only_one():
    note = {"title": "Cookout hours", "tag": "", "body": "Friday evenings."}
    assert score(note, ("cookout", "hours"), ALL_OF) > 0
    assert score(note, ("cookout", "birthday"), ALL_OF) == 0
    assert score(note, ("cookout", "birthday"), ANY_OF) > 0


def test_the_search_says_which_pass_answered_so_a_loose_match_is_never_sold_as_exact():
    exact = search(NOTES, "cookout hours")
    assert exact.matched == ALL_OF
    assert exact.hits[0].title == "Cookout hours"

    loose = search(NOTES, "cookout parliament")
    assert loose.matched == ANY_OF
    assert loose.hits


def test_only_the_every_token_pass_landing_on_whole_words_counts_as_a_strong_hit():
    """Measured 2026-09-01: the loose pass matched nearly everything, so `any hit`
    routed 8 of 8 live calls to the dear tier and Groq was never once chosen."""
    assert is_strong(search(NOTES, "cookout hours")) is True
    assert is_strong(search(NOTES, "cookout parliament")) is False
    assert is_strong(search(NOTES, "parliament")) is False
    assert is_strong(["a hit"]) is False
    assert search(NOTES, "cookout hours").strong is True


def test_a_word_hiding_inside_another_word_is_not_a_hit_worth_paying_more_for():
    """`hi` is inside `this`, which is how a greeting scored a title hit."""
    found = search(NOTES, "hi")
    assert found.matched == ALL_OF and found.hits
    assert found.strong is False
    assert whole_word("chat about anything", "hi") is False
    assert whole_word("say hi to them", "hi") is True
    assert whole_word("#off-topic is quiet", "off-topic") is True


def test_a_body_only_coincidence_does_not_reach_the_score_a_note_about_it_would():
    note = [{"id": 1, "title": "Rules", "body": "Be kind.", "tag": "", "source": STAFF}]
    assert search(note, "kind").hits[0].score < STRONG_SCORE
    assert is_strong(search(note, "kind")) is False
    assert STRONG_SCORE == TITLE_WEIGHT


def test_a_query_that_lands_nowhere_finds_nothing_rather_than_everything():
    assert search(NOTES, "parliament").hits == ()
    assert search(NOTES, "").hits == ()
    assert search([], "cookout").hits == ()


def test_the_search_reports_the_honest_denominator_and_the_terms_it_used():
    found = search(NOTES, "cookout")
    assert found.scanned == 3
    assert found.total == 2
    assert found.terms == ("cookout",)


def test_ties_break_the_same_way_every_time_so_one_query_answers_one_way():
    same = [
        {"id": 9, "title": "b", "body": "cookout", "tag": ""},
        {"id": 8, "title": "a", "body": "cookout", "tag": ""},
    ]
    assert [hit.title for hit in search(same, "cookout")] == ["a", "b"]


def test_the_limit_caps_the_hits_but_not_the_total():
    found = search(NOTES, "cookout", limit=1)
    assert len(found.hits) == 1 and found.total == 2


def test_a_snippet_is_centred_on_the_first_word_that_landed():
    body = "x" * 500 + " cookout " + "y" * 500
    said = snippet_of(body, ("cookout",))
    assert "cookout" in said
    assert said.startswith("…") and said.endswith("…")
    assert len(said) < 500


def test_a_short_note_is_its_own_snippet_with_no_ellipsis():
    assert snippet_of("Be kind.", ("kind",)) == "Be kind."


def test_grounding_quotes_the_notes_and_names_them_as_the_servers_own():
    said = grounding(search(NOTES, "cookout"))
    assert "quote it rather than inventing" in said
    assert "Cookout hours: The cookout runs Friday evenings." in said


def test_grounding_drops_a_note_that_will_not_fit_rather_than_cutting_it_in_half():
    big = {"id": 1, "title": "Big", "body": "z" * (GROUNDING_BYTES - 10), "tag": ""}
    small = {"id": 2, "title": "Small", "body": "fits", "tag": ""}
    said = grounding([big, small])
    assert "z" * 50 in said
    assert "Small: fits" not in said
    assert "…" not in said


def test_grounding_nothing_says_nothing_at_all():
    assert grounding([]) == ""
    assert grounding([{"title": "", "body": ""}]) == ""


def test_a_note_is_refused_in_words_when_it_is_missing_or_too_long():
    assert clean_title("  Cookout   hours ") == "Cookout hours"
    assert clean_body(" Friday. ") == "Friday."
    assert clean_tag(" EVENTS ") == "events"
    for bad, cleaner in (
        ("", clean_title),
        ("   ", clean_title),
        ("t" * (TITLE_LIMIT + 1), clean_title),
        ("", clean_body),
        ("b" * (BODY_LIMIT + 1), clean_body),
        ("g" * 41, clean_tag),
    ):
        with pytest.raises(KnowledgeError):
            cleaner(bad)


def test_a_note_comes_from_staff_or_from_the_server_and_nothing_else():
    assert clean_source(None) == STAFF
    assert clean_source("SERVER") == SERVER
    with pytest.raises(KnowledgeError):
        clean_source("somewhere")


async def store(tmp_path):
    db = Database(tmp_path / "k.sqlite3")
    await db.connect()
    return db


async def test_a_staff_note_is_stored_listed_edited_and_removed(tmp_path):
    db = await store(tmp_path)
    try:
        made = await add_section(db, 7, "Cookout hours", "Friday evenings.", tag="events", by=900)
        rows = await list_sections(db, 7)
        assert [row["title"] for row in rows] == ["Cookout hours"]
        assert rows[0]["source"] == STAFF and rows[0]["updated_by"] == 900
        await update_section(db, made, body="Saturday evenings.", by=901)
        assert (await get_section(db, made))["body"] == "Saturday evenings."
        assert await remove_section(db, made) is True
        assert await remove_section(db, made) is False
        assert await list_sections(db, 7) == []
    finally:
        await db.close()


async def test_the_daily_rewrite_replaces_every_server_row_and_touches_no_staff_row(tmp_path):
    db = await store(tmp_path)
    try:
        await add_section(db, 7, "Rules", "Be kind.", by=900)
        await replace_server_sections(db, 7, [("#general", "Chat", "channel")])
        await replace_server_sections(db, 7, [("#offtopic", "Anything", "channel")])
        rows = await list_sections(db, 7)
        assert sorted(row["title"] for row in rows) == ["#offtopic", "Rules"]
        assert await list_sections(db, 7, SERVER) != []
        assert [row["title"] for row in await list_sections(db, 7, STAFF)] == ["Rules"]
    finally:
        await db.close()


async def test_another_guilds_notes_are_not_swept_by_this_guilds_rewrite(tmp_path):
    db = await store(tmp_path)
    try:
        await replace_server_sections(db, 7, [("#general", "Chat", "channel")])
        await replace_server_sections(db, 8, [("#lounge", "Chat", "channel")])
        await replace_server_sections(db, 7, [])
        assert await list_sections(db, 7) == []
        assert [row["title"] for row in await list_sections(db, 8)] == ["#lounge"]
    finally:
        await db.close()


def channel(name, topic=None):
    return SimpleNamespace(name=name, topic=topic)


def test_the_channel_ingest_indexes_every_name_and_writes_a_note_per_topic():
    found = channel_sections([channel("general", "Chat here."), channel("quiet")])
    assert found[0][0] == "Channels in this server"
    assert "#general" in found[0][1] and "#quiet" in found[0][1]
    assert found[1] == ("#general", "Chat here.", "channel")
    assert len(found) == 2


def test_a_server_with_no_channels_writes_no_channel_notes():
    assert channel_sections([]) == []


def test_a_staff_channel_note_is_what_the_daily_read_writes_for_that_channel():
    speed = SimpleNamespace(id=5, name="speed-and-pbs", topic="general chat")
    quiet = SimpleNamespace(id=6, name="quiet", topic=None)
    found = channel_sections([speed, quiet], {5: "Speedrunning records.", 6: "Nothing much."})
    assert ("#speed-and-pbs", "Speedrunning records.", "channel") in found
    assert ("#quiet", "Nothing much.", "channel") in found
    assert all("general chat" not in body for _, body, _ in found)


def test_the_role_ingest_leaves_out_everyone():
    found = role_sections(
        SimpleNamespace(roles=[SimpleNamespace(name="@everyone"), SimpleNamespace(name="Member")])
    )
    assert found == [("Roles in this server", "Member", "role")]


def person(name, bot=False):
    return SimpleNamespace(display_name=name, name=name, bot=bot)


def a_role(name, members=()):
    return SimpleNamespace(name=name, members=list(members))


def test_a_small_role_is_written_out_by_name():
    found = role_holder_sections(
        SimpleNamespace(roles=[a_role("Leads", [person("Ada"), person("Kai"), person("Bo")])])
    )

    assert found == [("Who has the Leads role", "Leads — 3 members: Ada, Bo, Kai.", "role")]


def test_one_holder_is_a_member_not_members():
    found = role_holder_sections(SimpleNamespace(roles=[a_role("Mentor", [person("Ada")])]))
    assert found[0][1] == "Mentor — 1 member: Ada."


def test_a_role_bigger_than_the_cap_keeps_the_name_only_row_and_nothing_else():
    crowd = [person(f"Person {n}") for n in range(HOLDERS_SHOWN + 1)]
    guild = SimpleNamespace(roles=[a_role("Member", crowd), a_role("Leads", [person("Ada")])])

    assert [row[0] for row in role_holder_sections(guild)] == ["Who has the Leads role"]
    assert role_sections(guild)[0][1] == "Member, Leads"


def test_a_role_exactly_at_the_cap_is_still_written_out():
    crowd = [person(f"Person {n}") for n in range(HOLDERS_SHOWN)]
    found = role_holder_sections(SimpleNamespace(roles=[a_role("Member", crowd)]))

    assert len(found) == 1 and f"{HOLDERS_SHOWN} members" in found[0][1]


def test_a_role_nobody_holds_gets_no_note_of_its_own():
    assert role_holder_sections(SimpleNamespace(roles=[a_role("Leads")])) == []


def test_the_holder_notes_leave_out_bots_unless_that_is_all_there_is():
    guild = SimpleNamespace(
        roles=[
            a_role("Leads", [person("Ada"), person("Robo", bot=True)]),
            a_role("Webhooks", [person("Robo", bot=True)]),
        ]
    )

    found = {row[0]: row[1] for row in role_holder_sections(guild)}

    assert found["Who has the Leads role"] == "Leads — 1 member: Ada."
    assert found["Who has the Webhooks role"] == "Webhooks — 1 member: Robo."


def test_everyone_never_gets_a_holder_note():
    guild = SimpleNamespace(roles=[a_role("@everyone", [person("Ada")]), a_role("Leads")])
    assert role_holder_sections(guild) == []


def test_an_event_note_says_when_and_where_it_is():
    section = event_section(
        {"title": "Movie night", "starts_at": "2026-09-05T02:00:00+00:00", "location": "Voice 1",
         "description": "Bring snacks."}
    )
    assert section[0] == "Event: Movie night"
    assert "Voice 1" in section[1] and "Bring snacks." in section[1]
    assert event_section({"title": "", "starts_at": "x"}) is None


def test_an_event_note_gives_the_chat_a_bare_link_rather_than_markdown():
    """The knowledge sections are read by a language model, which reads words, not markdown."""
    section = event_section(
        {"title": "Raid", "starts_at": "2026-09-05T02:00:00+00:00",
         "location": "https://twitch.tv/bb"}
    )
    assert "https://twitch.tv/bb" in section[1] and "[" not in section[1]


def test_a_role_menu_note_lists_what_a_member_could_pick():
    guild = SimpleNamespace(get_role=lambda role_id: SimpleNamespace(name="Runner"))
    section = menu_section({"title": "Colours", "name": "colours"}, [{"label": "", "role_id": 1}],
                           guild)
    assert section[0] == "Role menu: Colours"
    assert "Runner" in section[1]
    assert menu_section({"title": "Colours"}, [], guild) is None


def test_the_ingest_trims_a_long_name_rather_than_refusing_it():
    """A refusal here would stop the whole daily loop over one badly named channel."""
    long_topic = shorten("t" * (BODY_LIMIT + 50), BODY_LIMIT)
    assert len(long_topic) == BODY_LIMIT and long_topic.endswith("…")
    assert shorten("  spaced  out ", 100) == "spaced out"
