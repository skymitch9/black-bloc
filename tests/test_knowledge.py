from types import SimpleNamespace

import pytest

from black_bloc.knowledge import (
    ALL_OF,
    ANY_OF,
    BODY_LIMIT,
    GROUNDING_BYTES,
    SERVER,
    STAFF,
    TITLE_LIMIT,
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
    list_sections,
    menu_section,
    remove_section,
    replace_server_sections,
    role_sections,
    score,
    search,
    shorten,
    snippet_of,
    tokenize,
    update_section,
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
    found = channel_sections(
        SimpleNamespace(text_channels=[channel("general", "Chat here."), channel("quiet")])
    )
    assert found[0][0] == "Channels in this server"
    assert "#general" in found[0][1] and "#quiet" in found[0][1]
    assert found[1] == ("#general", "Chat here.", "channel")
    assert len(found) == 2


def test_a_server_with_no_channels_writes_no_channel_notes():
    assert channel_sections(SimpleNamespace(text_channels=[])) == []


def test_the_role_ingest_leaves_out_everyone():
    found = role_sections(
        SimpleNamespace(roles=[SimpleNamespace(name="@everyone"), SimpleNamespace(name="Member")])
    )
    assert found == [("Roles in this server", "Member", "role")]


def test_an_event_note_says_when_and_where_it_is():
    section = event_section(
        {"title": "Movie night", "starts_at": "2026-09-05T02:00:00+00:00", "location": "Voice 1",
         "description": "Bring snacks."}
    )
    assert section[0] == "Event: Movie night"
    assert "Voice 1" in section[1] and "Bring snacks." in section[1]
    assert event_section({"title": "", "starts_at": "x"}) is None


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
