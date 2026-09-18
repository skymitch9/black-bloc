import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import discord
import pytest
from discord import app_commands

from black_bloc.command_errors import (
    COMMAND_FAILED,
    AnswersErrors,
    SafeDynamicItem,
    install,
    message_of,
    on_tree_error,
    record,
    report,
    retry_view,
    step_of,
)
from black_bloc.config import load_settings
from black_bloc.logkinds import ERROR_COMMAND, ERROR_MODAL, ERROR_PANEL
from black_bloc.panels import Panel, panel_minutes
from black_bloc.settings_store import (
    ERROR_RETRY_EXPIRED_KEY,
    ERROR_RETRY_LABEL,
    ERROR_RETRY_LABEL_KEY,
    ERROR_RETRY_MINUTES_KEY,
    ERROR_SENTENCE,
    ERROR_SENTENCE_KEY,
    KEY_HELP,
    KEY_TYPES,
    SettingsStore,
    namespace_of,
)
from black_bloc.storage.db import Database

GUILD = 7
MEMBER = 900
TEST_CHANNEL = 111


class _Response:
    def __init__(self, done=False):
        self.done = done
        self.messages = []

    def is_done(self):
        return self.done

    async def send_message(self, content=None, ephemeral=False, **kwargs):
        self.done = True
        self.messages.append({"content": content, "ephemeral": ephemeral, **kwargs})

    async def defer(self, **kwargs):
        self.done = True


class _Followup:
    def __init__(self):
        self.messages = []

    async def send(self, content=None, ephemeral=False, **kwargs):
        self.messages.append({"content": content, "ephemeral": ephemeral, **kwargs})


class _Interaction:
    def __init__(self, done=False):
        self.command = None
        self.response = _Response(done)
        self.followup = _Followup()


class _Tree:
    pass


class _Bot:
    def __init__(self):
        self.tree = _Tree()


async def test_an_unhandled_error_answers_the_caller_with_a_sentence(caplog):
    interaction = _Interaction()

    with caplog.at_level("ERROR"):
        await on_tree_error(interaction, RuntimeError("boom"))

    assert interaction.response.messages == [{"content": COMMAND_FAILED, "ephemeral": True}]
    assert "boom" in caplog.text


async def test_an_answered_interaction_gets_a_followup():
    interaction = _Interaction(done=True)

    await on_tree_error(interaction, RuntimeError("boom"))

    assert interaction.response.messages == []
    assert interaction.followup.messages[0]["content"] == COMMAND_FAILED


async def test_a_check_failure_is_left_to_the_check_that_already_answered():
    interaction = _Interaction()

    await on_tree_error(interaction, app_commands.CheckFailure("no"))

    assert interaction.response.messages == []
    assert interaction.followup.messages == []


async def test_a_broken_answer_never_raises_out_of_the_handler(caplog):
    interaction = _Interaction()

    async def explode(*args, **kwargs):
        raise RuntimeError("discord is down")

    interaction.response.send_message = explode

    with caplog.at_level("WARNING"):
        await on_tree_error(interaction, RuntimeError("boom"))

    assert "could not answer the caller" in caplog.text


def test_install_puts_the_handler_on_the_tree():
    bot = _Bot()
    install(bot)
    assert bot.tree.on_error is on_tree_error


def test_install_is_a_no_op_without_a_tree():
    bot = SimpleNamespace()

    install(bot)

    assert not hasattr(bot, "tree")


class _Modal(AnswersErrors):
    pass


class _Button(SafeDynamicItem):
    def __init__(self, boom=None):
        self.boom = boom
        self.clicked = []

    async def on_click(self, interaction):
        if self.boom is not None:
            raise self.boom
        self.clicked.append(interaction)


async def test_a_view_or_modal_failure_answers_the_person_and_logs_the_traceback(caplog):
    interaction = _Interaction()

    with caplog.at_level("ERROR"):
        await _Modal().on_error(interaction, RuntimeError("boom"))

    assert interaction.response.messages == [{"content": COMMAND_FAILED, "ephemeral": True}]
    assert "boom" in caplog.text and "_Modal failed" in caplog.text


async def test_a_dynamic_item_catches_its_own_failure_because_no_view_will(caplog):
    interaction = _Interaction()
    button = _Button(boom=RuntimeError("boom"))

    with caplog.at_level("ERROR"):
        await button.callback(interaction)

    assert interaction.response.messages == [{"content": COMMAND_FAILED, "ephemeral": True}]
    assert "_Button failed" in caplog.text


async def test_a_dynamic_item_that_works_is_left_alone():
    interaction = _Interaction()
    button = _Button()

    await button.callback(interaction)

    assert button.clicked == [interaction]
    assert interaction.response.messages == []


async def test_an_unimplemented_dynamic_item_is_a_programmer_error_answered_politely():
    interaction = _Interaction()

    await SafeDynamicItem().callback(interaction)

    assert interaction.response.messages[0]["content"] == COMMAND_FAILED


# ── §A the row ───────────────────────────────────────────────────────────────
# Every command / panel / modal / button failure is an action-log row, so staff who are not
# the owner can read it on the site's Logs page (`docs/info/errors-design.md` §A).


class _Guild:
    def __init__(self, guild_id=GUILD):
        self.id = guild_id

    def get_channel(self, channel_id):
        return None


class _LoggingBot:
    def __init__(self, db, store):
        self.db = db
        self.store = store

    def get_channel(self, channel_id):
        return None


class _Live(_Interaction):
    """An interaction with the three things `record` reads: a client, a guild and a member."""

    def __init__(self, bot, done=False, command=None, data=None):
        super().__init__(done)
        self.client = bot
        self.guild = _Guild()
        self.user = SimpleNamespace(id=MEMBER)
        self.command = command
        self.data = data or {}
        self.deleted = False

    async def delete_original_response(self):
        self.deleted = True


@pytest.fixture
async def wired(tmp_path, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    settings = load_settings(_env_file=None, test_mode=True, test_channel_id=TEST_CHANNEL)
    db = Database(tmp_path / "errors.sqlite3")
    await db.connect()
    store = SettingsStore(db, settings)
    await store.load()
    try:
        yield _LoggingBot(db, store)
    finally:
        await db.close()


async def logged(bot):
    cur = await bot.db.conn.execute("SELECT kind, actor_id, details FROM action_log ORDER BY id")
    return [dict(row) for row in await cur.fetchall()]


class _AskModal(AnswersErrors, discord.ui.Modal, title="Ask for something"):
    what = discord.ui.TextInput(label="What are you asking for?")


def broken_inside_the_package():
    """A failure whose innermost frame is the package's, which is what `step` must name."""
    panel_minutes(None, GUILD, ERROR_RETRY_MINUTES_KEY)


async def test_a_modal_failure_is_one_row_naming_where_and_what_broke(wired):
    modal = _AskModal()
    modal.what._value = "my landlord's address"
    interaction = _Live(wired, data={"custom_id": "request:file"})

    try:
        broken_inside_the_package()
    except AttributeError as exc:
        await modal.on_error(interaction, exc)

    row = (await logged(wired))[0]
    details = json.loads(row["details"])

    assert row["kind"] == ERROR_MODAL
    assert row["actor_id"] == MEMBER
    assert details["where"] == "_AskModal"
    assert details["error"] == "AttributeError"
    assert details["step"].startswith("black_bloc/panels.py:")
    assert details["interaction"] == "request:file"


async def test_a_row_never_carries_a_single_word_the_member_typed(wired):
    modal = _AskModal()
    modal.what._value = "my landlord's address"
    interaction = _Live(wired, data={"custom_id": "request:file"})

    await modal.on_error(interaction, RuntimeError("the render blew up"))

    said = json.dumps((await logged(wired))[0])

    assert str(modal.what) == "my landlord's address"
    assert "landlord" not in said and "address" not in said
    assert "the render blew up" in said


async def test_a_command_failure_is_headed_by_the_command_and_a_panels_by_the_panel(wired):
    await on_tree_error(
        _Live(wired, command=SimpleNamespace(qualified_name="event")), RuntimeError("boom")
    )
    await Panel(10, footer="quiet").on_error(_Live(wired), RuntimeError("boom"))

    rows = await logged(wired)

    assert [row["kind"] for row in rows] == [ERROR_COMMAND, ERROR_PANEL]
    assert json.loads(rows[0]["details"])["interaction"] == "/event"


def test_a_long_message_is_cut_and_an_http_failure_is_reduced_to_discords_own_words():
    response = SimpleNamespace(status=400, reason="Bad Request")
    http = discord.HTTPException(response, {"code": 50035, "message": "Invalid Form Body"})

    assert len(message_of(RuntimeError("x" * 400))) == 200
    assert message_of(http) == "50035 Invalid Form Body"


def test_the_step_is_the_innermost_package_frame_not_the_line_that_caught_it():
    try:
        broken_inside_the_package()
    except AttributeError as exc:
        assert step_of(exc).startswith("black_bloc/panels.py:")
        assert step_of(exc).split(":")[-1].isdigit()


async def test_a_failure_in_a_dm_is_left_to_the_python_log_because_there_is_no_guild(wired):
    interaction = _Live(wired)
    interaction.guild = None

    await record(wired, interaction, RuntimeError("boom"), "Panel", surface=ERROR_PANEL)

    assert await logged(wired) == []


async def test_a_database_that_cannot_be_written_still_leaves_the_traceback(wired, caplog):
    async def explode(*args, **kwargs):
        raise RuntimeError("database is locked")

    kept = wired.db
    wired.db = SimpleNamespace(conn=SimpleNamespace(execute=explode), is_connected=False)
    interaction = _Live(wired)

    with caplog.at_level("INFO"):
        await report(interaction, RuntimeError("boom"), "Panel", surface=ERROR_PANEL)

    wired.db = kept

    assert "boom" in caplog.text
    assert "error.panel was not logged" in caplog.text
    assert interaction.response.messages[0]["content"] == COMMAND_FAILED


# ── §B Try again ─────────────────────────────────────────────────────────────


class _Draft(Panel):
    def __init__(self, again, fields):
        super().__init__(10, footer="quiet", again=again)
        self.fields = fields


def button_of(view):
    return next(item for item in view.children)


async def test_a_surface_that_can_rebuild_itself_answers_with_try_again(wired):
    seen = []

    async def again(interaction, previous):
        seen.append((interaction, previous.fields["title"]))

    panel = _Draft(again, {"title": "Cookout"})
    interaction = _Live(wired)

    await panel.on_error(interaction, RuntimeError("boom"))
    said = interaction.response.messages[0]

    assert said["content"] == ERROR_SENTENCE
    assert [item.label for item in said["view"].children] == [ERROR_RETRY_LABEL]

    await button_of(said["view"]).callback(_Live(wired))

    assert seen == [(interaction, "Cookout")]


async def test_try_again_re_renders_through_the_interaction_the_member_was_already_on(wired):
    seen = []

    async def again(interaction, previous):
        seen.append(interaction)

    panel = _Draft(again, {})
    origin = _Live(wired)
    await panel.on_error(origin, RuntimeError("boom"))
    press = _Live(wired)

    await button_of(origin.response.messages[0]["view"]).callback(press)

    assert seen == [origin] and press.deleted


async def test_a_modal_borrows_the_try_again_of_the_panel_that_opened_it(wired):
    seen = []

    async def again(interaction, previous):
        seen.append(previous.fields["title"])

    modal = _AskModal()
    modal.previous = _Draft(again, {"title": "Cookout"})
    interaction = _Live(wired)

    await modal.on_error(interaction, RuntimeError("boom"))
    await button_of(interaction.response.messages[0]["view"]).callback(_Live(wired))

    assert interaction.response.messages[0]["content"] == ERROR_SENTENCE
    assert seen == ["Cookout"]


async def test_a_surface_that_cannot_rebuild_itself_keeps_todays_plain_sentence(wired):
    interaction = _Live(wired)

    await Panel(10, footer="quiet").on_error(interaction, RuntimeError("boom"))

    said = interaction.response.messages[0]

    assert said["content"] == COMMAND_FAILED and "view" not in said


async def test_a_try_again_pressed_too_late_says_so_and_names_the_command_to_run(wired):
    seen = []

    async def again(interaction):
        seen.append(interaction)

    origin = _Live(wired, command=SimpleNamespace(qualified_name="event"))
    view = retry_view(origin, again)
    view.until = datetime.now(UTC) - timedelta(seconds=1)
    press = _Live(wired)

    await button_of(view).callback(press)

    assert seen == []
    assert "/event" in press.response.messages[0]["content"]
    assert "run out" in press.response.messages[0]["content"]


async def test_a_re_render_that_fails_again_says_the_same_thing_rather_than_raising(wired):
    async def again(interaction):
        raise RuntimeError("still broken")

    view = retry_view(_Live(wired), again)
    press = _Live(wired)

    await button_of(view).callback(press)

    assert "that command" in press.followup.messages[0]["content"]


async def test_the_words_and_the_window_are_settings_both_doors_reach(wired):
    for key in (
        ERROR_SENTENCE_KEY,
        ERROR_RETRY_LABEL_KEY,
        ERROR_RETRY_MINUTES_KEY,
        ERROR_RETRY_EXPIRED_KEY,
    ):
        assert key in KEY_TYPES and KEY_HELP.get(key)
        assert namespace_of(key) == "core"
    assert wired.store.get(GUILD, ERROR_RETRY_MINUTES_KEY) == 10

    await wired.store.set(GUILD, ERROR_RETRY_LABEL_KEY, "Pick up where I was")
    view = retry_view(_Live(wired), lambda one: None)

    assert button_of(view).label == "Pick up where I was"
