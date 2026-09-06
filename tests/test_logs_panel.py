import discord
import pytest

from black_bloc import logs_panel
from black_bloc.actionlog import LOGS_DB_DOWN, NOTHING_IMPORTANT, NOTHING_YET, log_action, send_logs
from black_bloc.config import load_settings
from black_bloc.logs_panel import EVERYTHING, MORE, ONLY_IMPORTANT, LogsPanel, panel_for
from black_bloc.settings_store import (
    KEY_TYPES,
    LOGS_COUNT,
    LOGS_IMPORTANT_ONLY,
    LOGS_MAX,
    SETTINGS_PANEL_MINUTES,
)
from black_bloc.storage.db import Database

GUILD = 7
TEST_CH = 111
ORIGIN = "https://blackbloc.example"
REFUSAL = "That is staff only."


class FakeStore:
    def __init__(self, staff=True, **values):
        self.staff = staff
        self.values = {LOGS_COUNT: 10, LOGS_IMPORTANT_ONLY: False, SETTINGS_PANEL_MINUTES: 10}
        self.values.update(values)

    def is_staff(self, who):
        return self.staff

    def staff_refusal(self, guild_id):
        return REFUSAL

    def get(self, guild_id, key):
        return self.values[key]


class _Settings:
    origin = ORIGIN


class FakeBot:
    def __init__(self, db, store):
        self.db = db
        self.store = store
        self.settings = _Settings()

    def get_channel(self, channel_id):
        return None


class FakeGuild:
    id = GUILD


class FakeResponse:
    def __init__(self):
        self.done = False
        self.sent = []
        self.edits = []

    def is_done(self):
        return self.done

    async def send_message(self, content=None, **kwargs):
        self.done = True
        self.sent.append({"content": content, **kwargs})

    async def edit_message(self, **kwargs):
        self.done = True
        self.edits.append(kwargs)


class FakeFollowup:
    def __init__(self, response):
        self.response = response

    async def send(self, content=None, **kwargs):
        self.response.sent.append({"content": content, **kwargs})


class FakeMessage:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        embed = kwargs.get("embed")
        self.embeds = list(kwargs.get("embeds") or ([embed] if embed is not None else []))
        self.view = kwargs.get("view")

    async def edit(self, **kwargs):
        self.kwargs = kwargs
        if "embeds" in kwargs:
            self.embeds = list(kwargs["embeds"])


class FakeInteraction:
    def __init__(self, bot, guild=True):
        self.client = bot
        self.user = object()
        self.guild = FakeGuild() if guild else None
        self.response = FakeResponse()
        self.followup = FakeFollowup(self.response)
        self.message = None

    async def original_response(self):
        last = self.response.sent[-1]
        kept = {k: v for k, v in last.items() if k not in ("ephemeral", "content")}
        self.message = FakeMessage(**kept)
        return self.message

    async def edit_original_response(self, **kwargs):
        self.message = FakeMessage(**kwargs)
        return self.message


@pytest.fixture
async def wired(tmp_path, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    load_settings(_env_file=None, test_mode=True, test_channel_id=TEST_CH)
    db = Database(tmp_path / "logs.sqlite3")
    await db.connect()
    try:
        yield db
    finally:
        await db.close()


async def fill(db, store, how_many, kind="poll.created"):
    bot = FakeBot(db, store)
    for _ in range(how_many):
        await log_action(bot, FakeGuild(), kind, actor=1)


def labels(view):
    return [item.label for item in view.children]


async def a_panel(db, store, **kwargs):
    bot = FakeBot(db, store)
    view = panel_for(bot, GUILD, "poll", **kwargs)
    embed = await view.page(bot, GUILD)
    return view, embed


async def rows_of(db):
    cur = await db.conn.execute("SELECT * FROM action_log ORDER BY id")
    return await cur.fetchall()


# --- what is drawn --------------------------------------------------------------------------


async def test_show_more_is_drawn_when_a_full_page_came_back_below_the_cap(wired):
    store = FakeStore()
    await fill(wired, store, 12)

    view, _ = await a_panel(wired, store)

    assert labels(view) == [MORE, ONLY_IMPORTANT]
    assert view.count == 10 and view.ran_out is False


async def test_show_more_is_not_drawn_when_the_log_ran_out(wired):
    """Fewer rows than it asked for means there is no more to show, so the move is not offered."""
    store = FakeStore()
    await fill(wired, store, 3)

    view, _ = await a_panel(wired, store)

    assert labels(view) == [ONLY_IMPORTANT]
    assert view.ran_out is True


async def test_show_more_is_not_drawn_at_the_cap(wired):
    store = FakeStore(**{LOGS_COUNT: LOGS_MAX})
    await fill(wired, store, LOGS_MAX + 5)

    view, _ = await a_panel(wired, store)

    assert labels(view) == [ONLY_IMPORTANT]
    assert view.count == LOGS_MAX


async def test_the_toggle_wears_the_move_it_would_make(wired):
    store = FakeStore()
    await fill(wired, store, 2)

    showing_all, _ = await a_panel(wired, store)
    filtered, _ = await a_panel(wired, store, important_only=True)

    assert ONLY_IMPORTANT in labels(showing_all)
    assert EVERYTHING in labels(filtered)


async def test_an_empty_log_still_says_so_and_still_offers_the_toggle(wired):
    store = FakeStore()

    view, embed = await a_panel(wired, store)

    assert embed.description == NOTHING_YET
    assert labels(view) == [ONLY_IMPORTANT]


# --- pressing -------------------------------------------------------------------------------


async def test_show_more_reads_the_next_step_and_edits_the_same_message(wired):
    store = FakeStore()
    await fill(wired, store, 25)
    view, _ = await a_panel(wired, store)
    interaction = FakeInteraction(FakeBot(wired, store))

    await view.children[0].callback(interaction)

    assert view.count == 20
    assert interaction.response.sent == []
    edit = interaction.response.edits[-1]
    assert edit["view"] is view
    assert edit["allowed_mentions"].everyone is False
    assert len(edit["embed"].description.splitlines()) == 20
    assert labels(view) == [MORE, ONLY_IMPORTANT]


async def test_show_more_stops_at_the_cap_and_then_stops_being_offered(wired):
    store = FakeStore(**{LOGS_COUNT: 40})
    await fill(wired, store, LOGS_MAX + 10)
    view, _ = await a_panel(wired, store)

    await view.children[0].callback(FakeInteraction(FakeBot(wired, store)))

    assert view.count == LOGS_MAX
    assert labels(view) == [ONLY_IMPORTANT]


async def test_the_toggle_flips_the_filter_the_label_and_the_list(wired):
    store = FakeStore()
    await fill(wired, store, 2, kind="poll.created")
    await fill(wired, store, 1, kind="poll.cancelled")
    view, _ = await a_panel(wired, store)
    interaction = FakeInteraction(FakeBot(wired, store))

    await view.children[-1].callback(interaction)

    assert view.important_only is True
    assert labels(view) == [EVERYTHING]
    body = interaction.response.edits[-1]["embed"].description
    assert "poll.cancelled" in body and "poll.created" not in body


async def test_the_toggle_back_says_everything_again(wired):
    store = FakeStore(**{LOGS_IMPORTANT_ONLY: True})
    view, _ = await a_panel(wired, store)
    interaction = FakeInteraction(FakeBot(wired, store))

    await view.children[-1].callback(interaction)

    assert view.important_only is False
    assert labels(view) == [ONLY_IMPORTANT]


async def test_a_filtered_list_with_nothing_important_says_so(wired):
    store = FakeStore()
    await fill(wired, store, 2)
    view, _ = await a_panel(wired, store)
    interaction = FakeInteraction(FakeBot(wired, store))

    await view.children[-1].callback(interaction)

    assert view.important_only is True
    assert interaction.response.edits[-1]["embed"].description == NOTHING_IMPORTANT


async def test_pressing_a_logs_button_writes_no_log_row(wired):
    """Checklist 34 counts writes; a Logs button is a read and must leave nothing behind."""
    store = FakeStore()
    await fill(wired, store, 12)
    before = len(await rows_of(wired))
    view, _ = await a_panel(wired, store)

    await view.children[0].callback(FakeInteraction(FakeBot(wired, store)))
    await view.children[-1].callback(FakeInteraction(FakeBot(wired, store)))

    assert len(await rows_of(wired)) == before


# --- the two re-checks ----------------------------------------------------------------------


async def test_a_staffer_demoted_while_the_list_is_open_is_refused_and_nothing_changes(wired):
    store = FakeStore()
    await fill(wired, store, 25)
    view, _ = await a_panel(wired, store)
    store.staff = False
    interaction = FakeInteraction(FakeBot(wired, store))

    await view.children[0].callback(interaction)

    assert interaction.response.sent[0]["content"] == REFUSAL
    assert interaction.response.edits == []
    assert view.count == 10


async def test_a_press_after_the_database_goes_says_so_and_nothing_changes(wired):
    store = FakeStore()
    await fill(wired, store, 25)
    view, _ = await a_panel(wired, store)
    bot = FakeBot(wired, store)
    await wired.close()
    interaction = FakeInteraction(bot)

    await view.children[0].callback(interaction)

    assert interaction.response.sent[0]["content"] == LOGS_DB_DOWN
    assert interaction.response.edits == []
    assert view.count == 10


# --- send_logs ------------------------------------------------------------------------------


async def test_send_logs_opens_on_the_two_settings_keys(wired):
    store = FakeStore(**{LOGS_COUNT: 25, LOGS_IMPORTANT_ONLY: True})
    await fill(wired, store, 30, kind="poll.cancelled")
    interaction = FakeInteraction(FakeBot(wired, store))

    await send_logs(interaction, "poll")

    sent = interaction.response.sent[-1]
    view = sent["view"]
    assert sent["ephemeral"] is True
    assert sent["allowed_mentions"].everyone is False
    assert (view.count, view.important_only, view.step) == (25, True, 25)
    assert labels(view) == [MORE, EVERYTHING]
    assert view.message is interaction.message


async def test_send_logs_refuses_a_non_staffer_and_opens_no_panel(wired):
    interaction = FakeInteraction(FakeBot(wired, FakeStore(staff=False)))

    await send_logs(interaction, "poll")

    assert interaction.response.sent[0]["content"] == REFUSAL
    assert "view" not in interaction.response.sent[0]


async def test_send_logs_says_the_database_is_down_and_opens_no_panel(wired):
    store = FakeStore()
    bot = FakeBot(wired, store)
    await wired.close()
    interaction = FakeInteraction(bot)

    await send_logs(interaction, "poll")

    assert interaction.response.sent[0]["content"] == LOGS_DB_DOWN
    assert "view" not in interaction.response.sent[0]


async def test_an_important_only_start_says_so_in_the_title_and_the_empty_line(wired):
    store = FakeStore(**{LOGS_IMPORTANT_ONLY: True})
    interaction = FakeInteraction(FakeBot(wired, store))

    await send_logs(interaction, "poll")

    embed = interaction.response.sent[-1]["embed"]
    assert embed.title.endswith("important only")
    assert embed.description == NOTHING_IMPORTANT


# --- the panel's own shape ------------------------------------------------------------------


async def test_the_list_goes_quiet_like_every_other_panel(wired):
    store = FakeStore()
    await fill(wired, store, 2)
    interaction = FakeInteraction(FakeBot(wired, store))
    await send_logs(interaction, "poll")
    view = interaction.response.sent[-1]["view"]

    await view.on_timeout()

    assert all(item.disabled for item in view.children)
    assert view.message.embeds[0].footer.text == logs_panel.PANEL_TIMEOUT_FOOTER


async def test_the_panel_borrows_the_core_panels_minutes_key_and_adds_no_third_one(wired):
    """The design says do not add a third key; `/settings`'s own number is the one it uses."""
    store = FakeStore(**{SETTINGS_PANEL_MINUTES: 4})
    view, _ = await a_panel(wired, store)

    assert view.timeout == 4 * 60
    assert "logs_panel_minutes" not in KEY_TYPES


def test_the_panel_takes_a_minutes_number_like_every_other_panel():
    view = LogsPanel("poll", count=10, important_only=False, step=10, minutes=7)

    assert isinstance(view, discord.ui.View)
    assert view.timeout == 7 * 60
    assert view.footer == logs_panel.PANEL_TIMEOUT_FOOTER
