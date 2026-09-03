import logging

import discord

from black_bloc import panels
from black_bloc.panels import NoteModal, Panel
from black_bloc.settings_store import DB_UNAVAILABLE

GUILD = 7
FOOTER = "This panel has gone quiet — run /request again"
REFUSAL = "That is staff only."


class _Response:
    def __init__(self, status):
        self.status = status
        self.reason = "refused"


def refused():
    return discord.HTTPException(_Response(403), "no")


class FakeResponse:
    def __init__(self, done=False):
        self.done = done
        self.sent = []

    def is_done(self):
        return self.done

    async def send_message(self, text, **kwargs):
        self.done = True
        self.sent.append((text, kwargs))


class FakeFollowup:
    def __init__(self):
        self.sent = []

    async def send(self, text, **kwargs):
        self.sent.append((text, kwargs))


class FakeStore:
    def __init__(self, staff=True, **values):
        self.staff = staff
        self.values = values

    def is_staff(self, who):
        return self.staff

    def staff_refusal(self, guild_id):
        return REFUSAL

    def get(self, guild_id, key):
        return self.values[key]


class FakeDb:
    def __init__(self, connected=True):
        self.is_connected = connected


class FakeBot:
    def __init__(self, staff=True, connected=True):
        self.store = FakeStore(staff=staff)
        self.db = FakeDb(connected)


class FakeGuild:
    def __init__(self, guild_id=GUILD):
        self.id = guild_id


class FakeInteraction:
    def __init__(self, bot=None, done=False):
        self.client = bot or FakeBot()
        self.guild = FakeGuild()
        self.user = object()
        self.response = FakeResponse(done)
        self.followup = FakeFollowup()
        self.edits = []

    async def edit_original_response(self, **kwargs):
        self.edits.append(kwargs)


class FakeToken:
    """Only what `on_timeout` reaches for — the interaction token's own original response."""

    def __init__(self, raises=None):
        self.edits = []
        self.raises = raises

    async def edit_original_response(self, **kwargs):
        if self.raises is not None:
            raise self.raises
        self.edits.append(kwargs)


class FakeMessage:
    def __init__(self, embed=None):
        self.embeds = [embed] if embed is not None else []
        self.view = None

    async def edit(self, **kwargs):
        if "embeds" in kwargs:
            self.embeds = list(kwargs["embeds"])
        if "view" in kwargs:
            self.view = kwargs["view"]


class DeafMessage(FakeMessage):
    async def edit(self, **kwargs):
        raise refused()


def a_panel(minutes=10, footer=FOOTER):
    return Panel(minutes, footer=footer)


def a_button(label="Go"):
    return discord.ui.Button(label=label)


# --- retire ---------------------------------------------------------------------------------


async def test_retire_marks_the_view_replaced_and_stops_it():
    view = a_panel()

    panels.retire(view)

    assert view.replaced is True
    assert view.is_finished()


async def test_retire_of_nothing_is_a_no_op():
    assert panels.retire(None) is None


# --- answer ---------------------------------------------------------------------------------


async def test_answer_sends_the_first_reply_through_the_response():
    interaction = FakeInteraction()

    await panels.answer(interaction, "in words")

    assert interaction.response.sent[0][0] == "in words"
    assert interaction.response.sent[0][1]["ephemeral"] is True
    assert interaction.response.sent[0][1]["allowed_mentions"].everyone is False
    assert interaction.followup.sent == []


async def test_answer_sends_a_followup_once_the_interaction_has_been_answered():
    interaction = FakeInteraction(done=True)

    await panels.answer(interaction, "in words")

    assert interaction.followup.sent[0][0] == "in words"
    assert interaction.followup.sent[0][1]["ephemeral"] is True
    assert interaction.response.sent == []


# --- still_staff ----------------------------------------------------------------------------


async def test_still_staff_lets_a_staffer_through_and_says_nothing():
    interaction = FakeInteraction(FakeBot(staff=True))

    assert await panels.still_staff(interaction) is True
    assert interaction.response.sent == []
    assert interaction.followup.sent == []


async def test_still_staff_refuses_a_demoted_staffer_in_words_through_answer():
    interaction = FakeInteraction(FakeBot(staff=False))

    assert await panels.still_staff(interaction) is False
    assert interaction.response.sent[0][0] == REFUSAL


async def test_a_demoted_staffer_who_already_deferred_is_refused_as_a_followup():
    interaction = FakeInteraction(FakeBot(staff=False), done=True)

    assert await panels.still_staff(interaction) is False
    assert interaction.followup.sent[0][0] == REFUSAL


# --- db_ready -------------------------------------------------------------------------------


async def test_db_ready_is_true_and_silent_when_the_database_is_connected():
    interaction = FakeInteraction(FakeBot(connected=True))

    assert await panels.db_ready(interaction) is True
    assert interaction.followup.sent == []


async def test_db_ready_answers_a_followup_in_words_when_the_database_is_down():
    interaction = FakeInteraction(FakeBot(connected=False))

    assert await panels.db_ready(interaction) is False
    assert interaction.followup.sent[0][0] == DB_UNAVAILABLE
    assert interaction.followup.sent[0][1]["ephemeral"] is True


# --- capped_placeholder ---------------------------------------------------------------------


def test_the_placeholder_says_how_many_are_left_off_only_when_some_are():
    assert panels.capped_placeholder(10, 10, pick="Pick one…") == "Pick one…"
    assert panels.capped_placeholder(25, 40, pick="Pick one…") == (
        "25 of 40 — the rest are on the site"
    )


def test_the_capped_wording_can_be_replaced_per_feature():
    assert (
        panels.capped_placeholder(5, 9, pick="Pick one…", capped="{shown}/{total}") == "5/9"
    )


# --- panel_minutes --------------------------------------------------------------------------


def test_panel_minutes_reads_the_key_it_is_given():
    store = FakeStore(request_panel_minutes=15, event_panel_minutes=30)

    assert panels.panel_minutes(store, GUILD, "request_panel_minutes") == 15
    assert panels.panel_minutes(store, GUILD, "event_panel_minutes") == 30


async def test_a_panel_never_takes_a_timeout_below_a_minute():
    assert a_panel(0).timeout == 60
    assert a_panel(3).timeout == 180


# --- interaction_check ----------------------------------------------------------------------


async def test_the_check_records_the_freshest_interaction_and_lets_the_click_through():
    view = a_panel()
    token = FakeToken()

    assert await view.interaction_check(token) is True
    assert view.last_interaction is token


# --- on_timeout -----------------------------------------------------------------------------


async def test_a_panel_with_no_message_yet_does_nothing_on_timeout():
    view = a_panel()
    view.add_item(a_button())

    await view.on_timeout()

    assert not any(item.disabled for item in view.children)


async def test_a_panel_that_was_replaced_does_nothing_on_timeout():
    view = a_panel()
    view.add_item(a_button())
    message = FakeMessage(discord.Embed(title="Panel"))
    view.message = message
    panels.retire(view)

    await view.on_timeout()

    assert message.embeds[0].footer.text is None
    assert not any(item.disabled for item in view.children)


async def test_the_timeout_footer_goes_through_the_freshest_interaction_token():
    view = a_panel()
    view.add_item(a_button())
    view.add_item(a_button("Again"))
    message = FakeMessage(discord.Embed(title="Panel"))
    view.message = message
    token = FakeToken()
    await view.interaction_check(token)

    await view.on_timeout()

    assert token.edits[0]["embeds"][0].footer.text == FOOTER
    assert all(item.disabled for item in token.edits[0]["view"].children)
    assert message.view is None
    assert message.embeds[0].footer.text is None


async def test_the_timeout_footer_falls_back_to_the_message_when_no_token_was_recorded():
    view = a_panel()
    view.add_item(a_button())
    message = FakeMessage(discord.Embed(title="Panel"))
    view.message = message

    await view.on_timeout()

    assert view.last_interaction is None
    assert message.embeds[0].footer.text == FOOTER
    assert message.view is view


async def test_the_timeout_footer_falls_back_to_the_message_when_the_token_has_expired():
    view = a_panel()
    view.add_item(a_button())
    message = FakeMessage(discord.Embed(title="Panel"))
    view.message = message
    await view.interaction_check(FakeToken(raises=refused()))

    await view.on_timeout()

    assert message.embeds[0].footer.text == FOOTER


async def test_a_timeout_discord_refuses_outright_is_logged_not_raised(caplog):
    view = a_panel()
    view.add_item(a_button())
    view.message = DeafMessage(discord.Embed(title="Panel"))
    await view.interaction_check(FakeToken(raises=refused()))

    with caplog.at_level(logging.INFO, logger="black_bloc.panels"):
        await view.on_timeout()

    assert all(item.disabled for item in view.children)
    said = [record for record in caplog.records if "timed-out panel" in record.message]
    assert len(said) == 2
    assert all(record.levelno == logging.INFO for record in said)


async def test_a_panel_with_no_embeds_still_disables_its_buttons_on_timeout():
    view = a_panel()
    view.add_item(a_button())
    message = FakeMessage()
    view.message = message

    await view.on_timeout()

    assert all(item.disabled for item in view.children)
    assert message.embeds == []


async def test_each_panel_carries_its_own_gone_quiet_sentence():
    view = a_panel(footer="This window has gone quiet — run /event again")
    view.add_item(a_button())
    message = FakeMessage(discord.Embed(title="Events"))
    view.message = message

    await view.on_timeout()

    assert message.embeds[0].footer.text == "This window has gone quiet — run /event again"


# --- the generic note modal -----------------------------------------------------------------


async def test_the_note_modal_hands_its_text_to_the_callback_it_was_given():
    seen = []

    async def took(interaction, text):
        seen.append((interaction, text))

    modal = NoteModal(
        title="Say why", label="Why? (sent to the asker)", max_length=40, on_submit=took
    )
    modal.note._value = "because"
    interaction = FakeInteraction()

    await modal.on_submit(interaction)

    assert seen == [(interaction, "because")]


async def test_the_note_modal_wears_the_title_label_and_limit_it_was_given():
    async def took(interaction, text):
        return None

    modal = NoteModal(title="Send this back", label="What's left?", max_length=300, on_submit=took)

    assert modal.title == "Send this back"
    assert modal.note.label == "What's left?"
    assert modal.note.max_length == 300
    assert modal.note.style == discord.TextStyle.paragraph


async def test_two_note_modals_do_not_share_one_field():
    async def took(interaction, text):
        return None

    one = NoteModal(title="One", label="First", max_length=10, on_submit=took)
    two = NoteModal(title="Two", label="Second", max_length=20, on_submit=took)

    assert one.note is not two.note
    assert one.note.label == "First" and two.note.label == "Second"
    assert one.note.max_length == 10 and two.note.max_length == 20


def test_an_option_label_names_the_id_the_state_and_as_much_text_as_fits():
    assert panels.option_label(12, "open", "Pizza or tacos?") == "#12 · open · Pizza or tacos?"
    assert panels.option_label(12, None, "Pizza or tacos?") == "#12 · Pizza or tacos?"
    assert panels.option_label(12, "", "Pizza or tacos?") == "#12 · Pizza or tacos?"


def test_an_option_label_never_goes_past_discords_hundred_characters():
    long = panels.option_label(12, "pending_review", "x" * 200)
    assert len(long) == panels.SELECT_OPTION_LIMIT
    assert long.startswith("#12 · pending_review · ")

    tight = panels.option_label(12, "open", "anything", limit=10)
    assert len(tight) == 10


def test_an_option_label_copes_with_a_row_that_has_no_text_at_all():
    assert panels.option_label("?", "open", None) == "#? · open · "
    assert panels.option_label(12, "open", "  padded  ") == "#12 · open · padded"


def test_the_library_says_what_it_offers_and_knows_nothing_about_requests():
    for name in (
        "Panel",
        "NoteModal",
        "answer",
        "still_staff",
        "retire",
        "db_ready",
        "option_label",
    ):
        assert name in panels.__all__
    for name in ("RequestView", "PANEL_TIMEOUT_FOOTER", "PICK_A_REQUEST"):
        assert not hasattr(panels, name)


async def test_a_note_modal_can_be_optional_so_dismissing_the_box_still_means_yes():
    """Events' Call-it-off note: submit is yes, an empty line is still a submit."""

    async def took(interaction, text):
        return None

    needed = NoteModal(title="Why not?", label="Why?", max_length=40, on_submit=took)
    spare = NoteModal(
        title="Why is it off?", label="Why?", max_length=40, on_submit=took, required=False
    )

    assert needed.note.required is True
    assert spare.note.required is False
