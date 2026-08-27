from datetime import UTC, datetime

from black_bloc.modmail import (
    ANONYMOUS_NAME,
    IN,
    NOTE,
    OUT,
    attachment_urls,
    closing_dm,
    count_directions,
    dump_attachments,
    header_embed,
    is_note,
    load_attachments,
    mentions,
    modes_sentence,
    note_body,
    parse_topic,
    relay_embed,
    staff_ping,
    thread_invite,
    thread_name,
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
        OUT, author_name="Mod Meg", author_id=STAFF, content="looking into it", anonymous=True
    )

    assert embed.author.name == ANONYMOUS_NAME
    assert embed.footer.text is None
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
