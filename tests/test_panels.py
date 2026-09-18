import ast
import logging
import pathlib
from types import SimpleNamespace

import discord

from black_bloc import panels
from black_bloc.panels import NoteModal, Panel, picked_values
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
        self.deferred = False
        self.sent = []

    def is_done(self):
        return self.done

    async def send_message(self, text, **kwargs):
        self.done = True
        self.sent.append((text, kwargs))

    async def defer(self, **kwargs):
        self.done = True
        self.deferred = True


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
        self.rendered = object()

    async def edit_original_response(self, **kwargs):
        self.edits.append(kwargs)
        return self.rendered


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


# --- still_allowed --------------------------------------------------------------------------


async def test_still_allowed_says_nothing_when_the_gate_is_open():
    interaction = FakeInteraction(FakeBot(staff=False))

    assert await panels.still_allowed(interaction, True, "Organizers only.") is True
    assert interaction.response.sent == []
    assert interaction.followup.sent == []


async def test_still_allowed_refuses_with_the_callers_words_not_the_staff_refusal():
    interaction = FakeInteraction(FakeBot(staff=True))

    assert await panels.still_allowed(interaction, False, "Organizers only.") is False
    assert interaction.response.sent[0][0] == "Organizers only."


async def test_still_allowed_refuses_a_deferred_move_as_a_followup():
    interaction = FakeInteraction(FakeBot(staff=True), done=True)

    assert await panels.still_allowed(interaction, False, "Organizers only.") is False
    assert interaction.followup.sent[0][0] == "Organizers only."


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


# --- db_up ----------------------------------------------------------------------------------


async def test_db_up_is_true_and_silent_when_the_database_is_connected():
    interaction = FakeInteraction(FakeBot(connected=True))

    assert await panels.db_up(interaction) is True
    assert interaction.response.sent == [] and interaction.followup.sent == []


async def test_db_up_answers_through_the_response_because_nothing_has_deferred():
    """A button that opens a MODAL cannot defer first, so `db_ready`'s followup is no use."""
    interaction = FakeInteraction(FakeBot(connected=False))

    assert await panels.db_up(interaction) is False
    assert interaction.response.sent[0][0] == DB_UNAVAILABLE
    assert interaction.response.sent[0][1]["ephemeral"] is True


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
        "still_allowed",
        "still_staff",
        "retire",
        "db_ready",
        "db_up",
        "option_label",
        "picked_values",
        "confirm",
        "confirm_items",
        "opened",
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


# --- opened ---------------------------------------------------------------------------------


async def test_opened_re_asks_staff_then_defers_then_asks_the_database():
    interaction = FakeInteraction()

    assert await panels.opened(interaction) is True
    assert interaction.response.deferred is True
    assert interaction.response.sent == [] and interaction.followup.sent == []


async def test_opened_refuses_a_demoted_staffer_before_it_defers_anything():
    interaction = FakeInteraction(FakeBot(staff=False))

    assert await panels.opened(interaction) is False
    assert interaction.response.deferred is False
    assert interaction.response.sent[0][0] == REFUSAL


async def test_opened_says_the_database_is_down_as_a_followup_because_it_has_deferred():
    interaction = FakeInteraction(FakeBot(connected=False))

    assert await panels.opened(interaction) is False
    assert interaction.response.deferred is True
    assert interaction.followup.sent[0][0] == DB_UNAVAILABLE


async def test_opened_without_the_staff_gate_defers_for_a_member_panel():
    """`/memory`, `/raidtrain` and the member half of `/youtube` open for anybody."""
    interaction = FakeInteraction(FakeBot(staff=False))

    assert await panels.opened(interaction, staff=False) is True
    assert interaction.response.deferred is True
    assert interaction.response.sent == []


async def test_opened_twice_on_one_interaction_defers_once_and_never_raises():
    """The zone picker hands the same interaction on to open_draft, which opens it again (v130)."""
    interaction = FakeInteraction(FakeBot(staff=False))

    assert await panels.opened(interaction, staff=False) is True
    interaction.response.deferred = False
    assert await panels.opened(interaction, staff=False) is True
    assert interaction.response.deferred is False
    assert interaction.response.sent == []


# --- confirm --------------------------------------------------------------------------------


def a_confirm_embed():
    return discord.Embed(title="Birthdays", description="the card that raised the question")


async def test_confirm_adds_the_question_to_the_card_and_both_buttons_in_order():
    interaction = FakeInteraction()
    view = a_panel()

    await panels.confirm(
        interaction,
        view,
        a_confirm_embed(),
        [a_button("Yes, forget it"), a_button("Keep it")],
        question="Forget your birthday?",
    )

    embed = interaction.edits[0]["embed"]
    assert [(one.name, one.value) for one in embed.fields] == [
        ("Are you sure?", "Forget your birthday?")
    ]
    assert [one.label for one in view.children] == ["Yes, forget it", "Keep it"]
    assert interaction.edits[0]["view"] is view
    assert view.message is interaction.rendered


async def test_confirm_never_pings_out_of_a_question_somebody_typed():
    interaction = FakeInteraction()

    await panels.confirm(
        interaction, a_panel(), a_confirm_embed(), [], question="Delete @everyone?"
    )

    assert interaction.edits[0]["allowed_mentions"].everyone is False


async def test_confirm_leaves_the_card_alone_when_the_question_is_already_on_it():
    """Role menus titles the whole embed `Are you sure?`, so it hands no question here."""
    interaction = FakeInteraction()

    await panels.confirm(interaction, a_panel(), a_confirm_embed(), [])

    assert interaction.edits[0]["embed"].fields == []


async def test_confirm_lets_a_caller_name_the_question_field_itself():
    interaction = FakeInteraction()

    await panels.confirm(
        interaction, a_panel(), a_confirm_embed(), [], question="Arm it?", title="Last chance"
    )

    assert interaction.edits[0]["embed"].fields[0].name == "Last chance"


async def test_confirm_stops_the_view_it_replaces_so_its_timeout_cannot_win():
    interaction = FakeInteraction()
    old = a_panel()

    await panels.confirm(interaction, a_panel(), a_confirm_embed(), [], old)

    assert old.replaced is True and old.is_finished()


def test_confirm_items_puts_the_danger_move_first_and_the_way_back_second():
    async def nothing(interaction, view):
        return None

    yes, no = panels.confirm_items(
        yes="Yes, arm it", no="Keep it off", on_yes=nothing, on_no=nothing
    )

    assert (yes.label, yes.style, yes.row) == ("Yes, arm it", discord.ButtonStyle.danger, 0)
    assert (no.label, no.style, no.row) == ("Keep it off", discord.ButtonStyle.secondary, 0)


def test_confirm_items_can_wear_a_gentler_style_where_the_move_is_not_destructive():
    async def nothing(interaction, view):
        return None

    yes, _ = panels.confirm_items(
        yes="Yes, seed them",
        no="Leave them",
        on_yes=nothing,
        on_no=nothing,
        yes_style=discord.ButtonStyle.primary,
        row=1,
    )

    assert yes.style is discord.ButtonStyle.primary and yes.row == 1


async def test_a_confirm_button_hands_the_live_view_to_the_move_it_runs():
    """The card the click lands on is the `previous` the move retires, so it must be the view."""
    seen = []

    async def took(interaction, view):
        seen.append((interaction, view))

    interaction = FakeInteraction()
    view = a_panel()
    yes, no = panels.confirm_items(yes="Yes", no="Keep it", on_yes=took, on_no=took)
    view.add_item(yes)
    view.add_item(no)

    await yes.callback(interaction)

    assert seen == [(interaction, view)]


def test_picked_values_reads_both_spellings_a_modal_group_answers_with():
    """One home for the reader `polls.py` and `modmail.py` both had a copy of."""
    assert picked_values(SimpleNamespace(values=["a", "b"])) == ["a", "b"]
    assert picked_values(SimpleNamespace(value="a")) == ["a"]
    assert picked_values(SimpleNamespace(value=None)) == []
    assert picked_values(None) == []


PACKAGE = pathlib.Path(panels.__file__).resolve().parent
LIBRARY = "panels.py"


def _modules_holding(literal):
    """Every package module whose AST carries this exact string, however it is written."""
    found = set()
    for path in sorted(PACKAGE.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and node.value == literal:
                found.add(path.relative_to(PACKAGE).as_posix())
    return found


def test_keep_it_is_written_out_in_exactly_one_module():
    assert _modules_holding(panels.KEEP_IT) == {LIBRARY}


# The library helpers that take nothing feature-specific, so a second copy is always a copy.
# `panel_minutes`, `site_page_url` and `option_label` are deliberately NOT here: every feature
# binds its own key, page and row shape, and those thin wrappers are the binding.
UNCOPYABLE = (
    "confirm",
    "confirm_items",
    "db_ready",
    "db_up",
    "retire",
    "still_allowed",
    "still_staff",
)
DEFINITIONS = (ast.FunctionDef, ast.AsyncFunctionDef)


def _modules_defining(name):
    """Every package module with a top-level function of this name."""
    found = set()
    for path in sorted(PACKAGE.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, DEFINITIONS) and node.name == name:
                found.add(path.relative_to(PACKAGE).as_posix())
    return found


def test_no_cog_writes_its_own_copy_of_a_library_helper():
    """`golive.db_up` was byte-identical to `panels.db_up` until this test existed."""
    copies = {name: sorted(_modules_defining(name) - {LIBRARY}) for name in UNCOPYABLE}
    assert {name: found for name, found in copies.items() if found} == {}
