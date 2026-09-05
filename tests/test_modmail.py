from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from black_bloc.modmail import (
    ANONYMOUS_NAME,
    BLOCK_PICK,
    BLOCK_REASON,
    CARD_MOVES,
    CARD_ROW_LIMIT,
    COLOURS,
    DISABLE,
    ENABLE,
    FORGET,
    IN,
    LOGS,
    NOTE,
    OUT,
    PANEL_MINUTES_KEY,
    PANEL_MOVES,
    REFRESH,
    SITE,
    SNIPPET_ADD,
    SNIPPET_CHANGE,
    SNIPPET_REMOVE,
    SNIPPET_REMOVE_NO,
    SNIPPET_REMOVE_YES,
    SOURCES,
    TRUNCATED_MARK,
    UNBLOCK,
    UNDELIVERED_MARK,
    attachment_urls,
    blocked_buttons,
    blocked_lines,
    card_buttons,
    chunk_lines,
    clamp_bytes,
    closing_dm,
    count_directions,
    dump_attachments,
    forget_buttons,
    header_embed,
    is_note,
    is_practice,
    load_attachments,
    mentions,
    modes_sentence,
    note_body,
    panel_minutes,
    parse_topic,
    picked_values,
    relay_embed,
    root_buttons,
    setup_buttons,
    snippet_buttons,
    snippet_lines,
    staff_ping,
    thread_invite,
    thread_name,
    ticket_card_embed,
    ticket_card_lines,
    ticket_channel_name,
    ticket_topic,
    transcript_embed,
    transcript_filename,
    transcript_text,
    valid_snippet_name,
)

USER = 900
STAFF = 12
TICKET = 4


class FakeAttachment:
    def __init__(self, url):
        self.url = url


def row(direction, content, *, author_id=USER, anonymous=0, attachments=None, at=None):
    return {
        "at": at or "2026-08-26T12:00:00+00:00",
        "author_id": author_id,
        "direction": direction,
        "anonymous": anonymous,
        "content": content,
        "attachments": attachments,
    }


def test_a_ticket_channel_is_named_after_the_member_by_discords_rules():
    assert ticket_channel_name("Käpt'n Blaubär", TICKET) == "kapt-n-blaubar"
    assert ticket_channel_name("!!!", TICKET) == f"ticket-{TICKET}"


def test_the_topic_carries_both_ids_and_reads_back():
    topic = ticket_topic(USER, TICKET)

    assert topic == f"Black Bloc modmail | user {USER} | ticket {TICKET}"
    assert parse_topic(topic) == (USER, TICKET)


def test_the_incumbents_topic_is_not_mistaken_for_ours():
    assert parse_topic("ModMail Channel 280397245206102028 1267275219777884263") is None
    assert parse_topic(None) is None


def test_a_thread_is_named_for_the_member_and_the_ticket_and_fits_discords_cap():
    assert thread_name("Alice", TICKET) == f"Alice · #{TICKET}"
    assert len(thread_name("a" * 200, TICKET)) == 100


def test_the_equals_prefix_is_what_makes_a_message_a_private_note():
    assert is_note("=watch this one") is True
    assert is_note("  = spaced out") is True
    assert is_note("normal reply") is False
    assert note_body("=  watch this one") == "watch this one"
    assert note_body("normal reply") == "normal reply"


def test_snippet_names_are_lowercase_slugs():
    assert valid_snippet_name("appeal") is True
    assert valid_snippet_name("ban-appeal_2") is True
    assert valid_snippet_name("Ban Appeal") is False
    assert valid_snippet_name("") is False


def test_attachments_round_trip_as_a_json_list_of_urls():
    urls = attachment_urls([FakeAttachment("https://cdn/1.png"), FakeAttachment("https://cdn/2")])

    assert urls == ["https://cdn/1.png", "https://cdn/2"]
    assert load_attachments(dump_attachments(urls)) == urls
    assert dump_attachments([]) is None
    assert load_attachments(None) == []
    assert load_attachments("not json") == []


def test_an_inbound_relay_shows_the_member_and_their_attachments():
    embed = relay_embed(
        IN,
        author_name="Alice",
        author_id=USER,
        content="my ban was unfair",
        attachments=[FakeAttachment("https://cdn/proof.png")],
    )

    assert embed.description == "my ban was unfair"
    assert embed.author.name == "Alice"
    assert str(USER) in embed.footer.text
    assert embed.fields[0].value == "https://cdn/proof.png"


def test_an_anonymous_reply_names_no_staff_member_anywhere():
    embed = relay_embed(
        OUT,
        author_name="Mod Meg",
        author_id=STAFF,
        content="looking into it",
        anonymous=True,
        colour=0xABCDEF,
    )

    assert embed.author.name == ANONYMOUS_NAME
    assert embed.footer.text is None
    assert embed.colour.value == COLOURS[OUT]
    rendered = f"{embed.author.name}{embed.description}{embed.title}"
    assert "Meg" not in rendered


def test_a_named_reply_keeps_the_staff_members_name_and_role_colour():
    embed = relay_embed(
        OUT, author_name="Mod Meg", author_id=STAFF, content="on it", colour=0xABCDEF
    )

    assert embed.author.name == "Mod Meg" and embed.colour.value == 0xABCDEF


def test_a_message_with_only_an_attachment_still_renders():
    embed = relay_embed(IN, author_name="Alice", author_id=USER, content="")

    assert embed.description == "*(no text)*"


def test_the_header_says_who_they_are_and_how_many_tickets_came_before():
    embed = header_embed(
        ticket_id=TICKET,
        user_id=USER,
        user_label="Alice",
        created_at=datetime(2020, 1, 1, tzinfo=UTC),
        joined_at=None,
        roles=[],
        prior_tickets=3,
    )

    values = {field.name: field.value for field in embed.fields}
    assert values["Joined the server"] == "not in the server"
    assert values["Roles"] == "none"
    assert values["Earlier tickets"] == "3"
    assert f"<@{USER}>" in embed.description


def test_only_the_named_staff_roles_may_ever_be_mentioned():
    allowed = mentions([5, 6])

    assert allowed.everyone is False and allowed.users is False
    assert [role.id for role in allowed.roles] == [5, 6]
    assert mentions().roles is False


def test_the_thread_invite_pings_the_staff_roles_once_and_says_so_when_there_are_none():
    assert staff_ping([5, 6]) == "<@&5> <@&6>"
    assert thread_invite([5], TICKET, "Alice").startswith("<@&5>")
    assert "No staff role resolves" in thread_invite([], TICKET, "Alice")


def test_the_transcript_is_chronological_with_notes_marked_and_links_kept():
    rows = [
        row(IN, "hello"),
        row(OUT, "hi there", author_id=STAFF, at="2026-08-26T12:01:00+00:00"),
        row(OUT, "anon line", author_id=STAFF, anonymous=1, at="2026-08-26T12:02:00+00:00"),
        row(
            NOTE,
            "watch this one",
            author_id=STAFF,
            at="2026-08-26T12:03:00+00:00",
            attachments='["https://cdn/proof.png"]',
        ),
    ]

    text = transcript_text(
        rows,
        ticket_id=TICKET,
        user_id=USER,
        user_label="Alice",
        guild_name="Black in a Flash!",
        opened_at="2026-08-26T12:00:00+00:00",
        closed_at="2026-08-26T12:30:00+00:00",
        closed_by=STAFF,
        reason="sorted",
    )
    lines = [line for line in text.splitlines() if line.startswith("[")]

    assert lines[0].endswith(f"MEMBER {USER}: hello")
    assert lines[1].endswith(f"STAFF {STAFF}: hi there")
    assert "(anonymous)" in lines[2]
    assert lines[3].startswith("[2026-08-26 12:03:00 UTC] NOTE")
    assert "    attachment: https://cdn/proof.png" in text
    assert "1 from the member, 2 sent, 1 note(s)" in text
    assert "sorted" in text


def test_an_empty_ticket_still_renders_a_transcript():
    text = transcript_text(
        [], ticket_id=TICKET, user_id=USER, user_label="Alice", guild_name="Server"
    )

    assert "(nothing was said)" in text
    assert transcript_filename(TICKET) == f"modmail-ticket-{TICKET}.txt"


def test_an_unreadable_timestamp_is_printed_rather_than_dropped():
    text = transcript_text(
        [row(IN, "hello", at="not a date")],
        ticket_id=TICKET,
        user_id=USER,
        user_label="Alice",
        guild_name="Server",
    )

    assert "[not a date]" in text


def test_the_summary_embed_counts_every_direction():
    rows = [row(IN, "a"), row(OUT, "b"), row(NOTE, "c"), row(NOTE, "d")]
    counts = count_directions(rows)

    embed = transcript_embed(
        ticket_id=TICKET,
        user_id=USER,
        user_label="Alice",
        counts=counts,
        closed_by=STAFF,
        reason="sorted",
    )
    values = {field.name: field.value for field in embed.fields}

    assert counts == {IN: 1, OUT: 1, NOTE: 2}
    assert values["Messages"] == "1 in · 1 out · 2 note(s)"
    assert values["Closed by"] == f"<@{STAFF}>"
    assert values["Reason"] == "sorted"


def test_the_closing_dm_repeats_the_reason_when_there_is_one():
    assert "sorted" in closing_dm("Server", "sorted")
    assert "reason given" not in closing_dm("Server")


def test_each_mode_is_described_in_words():
    assert "channels" in modes_sentence("channel")
    assert "private threads" in modes_sentence("thread")


def test_the_transcript_is_cut_on_bytes_not_characters_and_says_it_was_cut():
    body = "é" * 100

    cut = clamp_bytes(body, limit=150)

    assert len(cut.encode("utf-8")) <= 150
    assert cut.endswith(TRUNCATED_MARK)
    assert "�" not in cut
    assert clamp_bytes(body, limit=10_000) == body


def test_a_reply_that_never_reached_the_member_is_marked_in_the_transcript():
    rows = [row(IN, "hello"), row(OUT, "are you there", author_id=STAFF) | {"delivered": 0}]

    text = transcript_text(
        rows, ticket_id=TICKET, user_id=USER, user_label="Alice", guild_name="Server"
    )

    assert UNDELIVERED_MARK in text
    assert text.count(UNDELIVERED_MARK) == 1


def test_the_transcript_header_warns_that_attachment_links_die():
    text = transcript_text(
        [row(IN, "see this", attachments='["https://cdn/proof.png"]')],
        ticket_id=TICKET,
        user_id=USER,
        user_label="Alice",
        guild_name="Server",
    )

    assert "24 hours" in text


def test_a_long_list_is_cut_into_messages_discord_will_take():
    chunks = chunk_lines([f"line {n} " + "x" * 200 for n in range(40)])

    assert len(chunks) > 1
    assert all(len(chunk) <= 1900 for chunk in chunks)
    assert chunks[0].startswith("line 0")
    assert chunk_lines([]) == []
    assert chunk_lines(["one", "two"]) == ["one\ntwo"]


def actions(moves):
    return [move.action for move in moves]


def test_the_root_draws_forget_only_where_something_is_pointed():
    bare = root_buttons(has_forget=False, has_site=False)
    full = root_buttons(has_forget=True, has_site=True)

    assert actions(bare) == ["setup", "blocked", "snippets", LOGS, REFRESH]
    assert actions(full) == ["setup", "blocked", "snippets", FORGET, LOGS, REFRESH, SITE]


def test_setup_names_the_switchs_own_effect_rather_than_offering_both():
    on = actions(setup_buttons(enabled=True))
    off = actions(setup_buttons(enabled=False))

    assert DISABLE in on and ENABLE not in on
    assert ENABLE in off and DISABLE not in off
    assert on[:4] == ["category", "staff_channel", "transcripts", "mode"]


def test_unblock_is_drawn_only_once_somebody_is_picked():
    assert UNBLOCK not in actions(blocked_buttons(picked=False, blocking=False))
    assert UNBLOCK in actions(blocked_buttons(picked=True, blocking=False))


def test_blocking_swaps_the_picker_for_the_reason_modal_never_both():
    idle = actions(blocked_buttons(picked=False, blocking=False))
    chosen = actions(blocked_buttons(picked=False, blocking=True))

    assert BLOCK_PICK in idle and BLOCK_REASON not in idle
    assert BLOCK_REASON in chosen and BLOCK_PICK not in chosen


def test_a_snippet_card_offers_change_and_remove_only_once_one_is_picked():
    idle = actions(snippet_buttons(picked=False, confirming=False))
    chosen = actions(snippet_buttons(picked=True, confirming=False))
    asked = actions(snippet_buttons(picked=True, confirming=True))

    assert idle.count(SNIPPET_ADD) == 1
    assert SNIPPET_REMOVE not in idle and SNIPPET_CHANGE not in idle
    assert SNIPPET_REMOVE in chosen and SNIPPET_CHANGE in chosen
    assert asked[:2] == [SNIPPET_REMOVE_YES, SNIPPET_REMOVE_NO]
    assert SNIPPET_ADD not in asked


@pytest.mark.parametrize(
    "built",
    [
        root_buttons(has_forget=True, has_site=True),
        setup_buttons(enabled=True),
        setup_buttons(enabled=False),
        blocked_buttons(picked=True, blocking=False),
        blocked_buttons(picked=False, blocking=True),
        snippet_buttons(picked=True, confirming=False),
        snippet_buttons(picked=True, confirming=True),
        forget_buttons(),
    ],
)
def test_every_state_fits_inside_discords_five_by_five(built):
    """Row 0 is kept free for a select, and no other row may pass Discord's five."""
    rows: dict[int, int] = {}
    for move in built:
        rows[move.row] = rows.get(move.row, 0) + 1
    assert 0 not in rows
    assert max(rows) <= 4
    assert all(count <= 5 for count in rows.values()), rows


def test_every_move_the_panel_can_draw_is_in_one_table():
    known = {move.action for move in PANEL_MOVES}
    drawn: set[str] = set()
    for built in (
        root_buttons(has_forget=True, has_site=True),
        setup_buttons(enabled=True),
        setup_buttons(enabled=False),
        blocked_buttons(picked=True, blocking=True),
        snippet_buttons(picked=True, confirming=False),
        snippet_buttons(picked=True, confirming=True),
        forget_buttons(),
    ):
        drawn |= {move.action for move in built}
    assert drawn <= known


def test_a_blocked_list_longer_than_the_cap_says_where_the_rest_are():
    rows = [{"user_id": n, "reason": None, "at": "2026-09-05T10:00:00+00:00"} for n in range(30)]

    lines = blocked_lines(rows)

    assert len(lines) == 26
    assert lines[0] == "<@0> — no reason given (2026-09-05)"
    assert "5 more" in lines[-1] and "Modmail page" in lines[-1]
    assert blocked_lines([]) == []


def test_a_snippet_list_shows_a_clamped_preview_and_names_the_site_past_the_cap():
    rows = [{"name": f"s{n}", "content": "x" * 300} for n in range(26)]

    lines = snippet_lines(rows)

    assert lines[0].startswith("**s0** — ") and len(lines[0]) < 200
    assert "1 more" in lines[-1]
    assert snippet_lines([{"name": "a", "content": "b"}]) == ["**a** — b"]


def test_the_panel_minutes_key_is_read_through_the_shared_helper():
    store = SimpleNamespace(get=lambda guild_id, key: 7 if key == PANEL_MINUTES_KEY else None)

    assert panel_minutes(store, 1) == 7
    assert PANEL_MINUTES_KEY == "modmail_panel_minutes"


def test_the_four_sources_a_reply_can_come_from_are_named_once():
    assert SOURCES == ("card", "typed", "command", "web")


def a_ticket(**over):
    row = {
        "id": 4,
        "user_id": 900,
        "mode": "channel",
        "opened_at": "2026-09-05T10:00:00+00:00",
        "practice": 0,
    }
    row.update(over)
    return row


def test_the_card_carries_the_four_moves_and_only_practice_gets_the_other_two():
    plain = card_buttons(practice=False)
    practising = card_buttons(practice=True)

    assert [move.label for move in plain] == [
        "Reply",
        "Reply as Staff",
        "Private note",
        "Close…",
    ]
    assert [move.label for move in practising[4:]] == [
        "Speak as the member",
        "End the practice",
    ]
    assert set(plain) <= set(CARD_MOVES) and set(practising) <= set(CARD_MOVES)


@pytest.mark.parametrize("practice", [False, True])
def test_every_card_row_fits_inside_discords_five(practice):
    rows: dict[int, int] = {}
    for move in card_buttons(practice=practice):
        rows[move.row] = rows.get(move.row, 0) + 1

    assert max(rows.values()) <= CARD_ROW_LIMIT
    assert len(rows) <= CARD_ROW_LIMIT


def test_every_card_move_has_its_own_action_so_a_custom_id_can_never_be_ambiguous():
    actions = [move.action for move in CARD_MOVES]

    assert len(set(actions)) == len(actions)


def test_the_card_says_who_it_is_when_it_opened_and_how_much_has_been_said():
    lines = ticket_card_lines(a_ticket(), {IN: 3, OUT: 2, NOTE: 1}, label="Alice")

    assert lines[0] == "<@900> — Alice"
    assert lines[1] == "**opened** — 2026-09-05T10:00:00+00:00"
    assert lines[2] == "**mode** — channel"
    assert lines[3] == "**messages** — 3 from them · 2 sent · 1 note(s)"
    assert len(lines) == 4


def test_a_blocked_member_is_said_on_the_card_and_a_practice_ticket_says_it_is_fake():
    blocked = ticket_card_lines(a_ticket(), None, label="Alice", blocked=True)
    practice = ticket_card_lines(a_ticket(practice=1), None, label="Alice")

    assert "blocked" in blocked[-1]
    assert "practice" in practice[-1]
    assert is_practice(a_ticket(practice=1)) and not is_practice(a_ticket())


def test_the_card_embed_titles_a_practice_ticket_as_practice():
    assert ticket_card_embed(a_ticket()).title == "Ticket #4"
    assert ticket_card_embed(a_ticket(practice=1)).title == "Practice ticket #4"


def test_picked_values_reads_both_spellings_a_modal_group_answers_with():
    assert picked_values(SimpleNamespace(values=["a", "b"])) == ["a", "b"]
    assert picked_values(SimpleNamespace(value="a")) == ["a"]
    assert picked_values(SimpleNamespace(value=None)) == []
    assert picked_values(None) == []
