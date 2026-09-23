import asyncio
from types import SimpleNamespace

import discord
import pytest
from discord.webhook.async_ import async_context

from black_bloc import orphaned
from black_bloc.bot import BlackBlocBot
from black_bloc.logkinds import PANEL_EXPIRED_CLICK, ROUTINE, feature_of, is_important
from black_bloc.settings_store import (
    CORE_KEYS,
    KEY_HELP,
    KEY_TYPES,
    PANEL_EXPIRED_TEXT,
    PANEL_EXPIRED_TEXT_KEY,
    namespace_of,
)

GUILD = 700
CHANNEL = 701
MESSAGE = 702
USER = 703
APP = 704
BUTTON = 2
EPHEMERAL = 64


class Adapter:
    """Discord's callback endpoint: records every response, and yields as a real POST does."""

    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def create_interaction_response(self, interaction_id, token, **kwargs):
        await asyncio.sleep(0)
        self.sent.append(kwargs["params"].payload)
        return {"interaction": {"id": str(interaction_id), "type": 3}}


def user() -> dict:
    return {"id": str(USER), "username": "member", "discriminator": "0", "avatar": None}


def message_payload(command: str | None) -> dict:
    found = {
        "id": str(MESSAGE),
        "channel_id": str(CHANNEL),
        "author": {**user(), "id": str(APP), "username": "Black Bloc", "bot": True},
        "content": "",
        "timestamp": "2026-09-22T12:00:00+00:00",
        "edited_timestamp": None,
        "tts": False,
        "mention_everyone": False,
        "mentions": [],
        "mention_roles": [],
        "attachments": [],
        "embeds": [],
        "pinned": False,
        "type": 0,
        "flags": EPHEMERAL,
        "components": [],
    }
    if command:
        found["interaction"] = {"id": "900", "type": 2, "name": command, "user": user()}
    return found


def payload(custom_id: str, *, command: str | None = "request", modal: bool = False) -> dict:
    data: dict = {"custom_id": custom_id}
    if modal:
        data["components"] = []
    else:
        data["component_type"] = BUTTON
    found = {
        "id": "800",
        "application_id": str(APP),
        "type": 5 if modal else 3,
        "token": "token",
        "version": 1,
        "guild_id": str(GUILD),
        "channel": {"id": str(CHANNEL), "type": 0, "name": "general", "position": 0},
        "member": {
            "user": user(),
            "roles": [],
            "joined_at": None,
            "deaf": False,
            "mute": False,
            "flags": 0,
        },
        "data": data,
        "attachment_size_limit": 8 * 1024 * 1024,
    }
    if not modal:
        found["message"] = message_payload(command)
    return found


class LiveView(discord.ui.View):
    """A live panel whose press stops the view BEFORE its first await — the race the mark beats."""

    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(label="Live", custom_id="live:known")
    async def live(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.stop()
        await interaction.response.send_message("the live panel answered", ephemeral=True)


@pytest.fixture
def logged(monkeypatch):
    rows: list[dict] = []

    async def fake(bot, guild, kind, **kwargs):
        rows.append({"guild": guild.id, "kind": kind, **kwargs})

    monkeypatch.setattr(orphaned, "log_action", fake)
    return rows


@pytest.fixture
async def live_bot(settings):
    bot = BlackBlocBot(settings)
    await bot._async_setup_hook()
    state = bot._connection
    state.user = discord.ClientUser(state=state, data={**user(), "id": str(APP), "bot": True})
    orphaned.install(bot)
    return bot


async def settle() -> None:
    for _ in range(25):
        await asyncio.sleep(0)


async def arrive(bot, body: dict) -> Adapter:
    """Feed one INTERACTION_CREATE through discord.py's own parser, exactly as the gateway does."""
    adapter = Adapter()
    token = async_context.set(adapter)
    try:
        bot._connection.parse_interaction_create(body)
        await settle()
    finally:
        async_context.reset(token)
    return adapter


async def test_a_click_a_live_view_owns_is_answered_by_the_view_alone(live_bot, logged):
    """The ordering proof: the view stops itself before its first await, so by the time any
    listener runs the store no longer knows the id — only the mark taken in `dispatch` does."""
    view = LiveView()
    live_bot._connection.store_view(view, MESSAGE)

    adapter = await arrive(live_bot, payload("live:known"))

    assert [one["data"]["content"] for one in adapter.sent] == ["the live panel answered"]
    assert logged == []
    probe = SimpleNamespace(
        type=discord.InteractionType.component,
        data={"custom_id": "live:known", "component_type": BUTTON},
        message=SimpleNamespace(id=MESSAGE),
    )
    assert orphaned.is_owned(orphaned.view_store(live_bot), probe) is False


async def test_a_click_nobody_owns_gets_the_sentence_ephemerally(live_bot, logged):
    adapter = await arrive(live_bot, payload("5f2a9c0d1e8b4a7f"))

    assert len(adapter.sent) == 1
    sent = adapter.sent[0]["data"]
    assert sent["flags"] & EPHEMERAL
    assert sent["content"] == PANEL_EXPIRED_TEXT.replace("{command}", "/request")
    assert sent["allowed_mentions"] == {"parse": []}
    assert logged == [
        {
            "guild": GUILD,
            "kind": PANEL_EXPIRED_CLICK,
            "actor": logged[0]["actor"],
            "details": {
                "feature": "request",
                "command": "/request",
                "surface": "component",
                "custom_id": "5f2a9c0d1e8b4a7f",
            },
        }
    ]
    assert logged[0]["actor"].id == USER


async def test_without_discords_record_of_the_command_it_says_run_the_command(live_bot, logged):
    adapter = await arrive(live_bot, payload("gone:1:2", command=None))

    assert adapter.sent[0]["data"]["content"] == PANEL_EXPIRED_TEXT.replace(
        "{command}", orphaned.THE_COMMAND
    )
    assert logged[0]["details"]["custom_id"] == "gone"
    assert logged[0]["details"]["feature"] == ""


async def test_a_modal_submitted_after_a_restart_is_answered_too(live_bot, logged):
    adapter = await arrive(live_bot, payload("modal-gone", modal=True))

    assert adapter.sent[0]["data"]["flags"] & EPHEMERAL
    assert logged[0]["details"]["surface"] == "modal"
    assert logged[0]["details"]["command"] == ""


async def test_a_live_modal_is_left_to_its_own_on_submit(live_bot, logged):
    class Live(discord.ui.Modal, title="Note"):
        async def on_submit(self, interaction: discord.Interaction) -> None:
            await interaction.response.send_message("the modal answered", ephemeral=True)

    modal = Live(custom_id="modal-live")
    live_bot._connection.store_view(modal)

    adapter = await arrive(live_bot, payload("modal-live", modal=True))

    assert [one["data"]["content"] for one in adapter.sent] == ["the modal answered"]
    assert logged == []


async def test_a_dynamic_item_template_counts_as_an_owner(live_bot, logged):
    class Door(discord.ui.DynamicItem[discord.ui.Button], template=r"door:(?P<n>\d+)"):
        def __init__(self, n: int) -> None:
            super().__init__(discord.ui.Button(label="Door", custom_id=f"door:{n}"))

        @classmethod
        async def from_custom_id(cls, interaction, item, match):
            return cls(int(match["n"]))

    live_bot.add_dynamic_items(Door)

    adapter = await arrive(live_bot, payload("door:7"))

    assert adapter.sent == []
    assert logged == []


async def test_a_persistent_view_added_without_a_message_counts_as_an_owner(live_bot, logged):
    live_bot.add_view(LiveView())

    adapter = await arrive(live_bot, payload("live:known"))

    assert [one["data"]["content"] for one in adapter.sent] == ["the live panel answered"]
    assert logged == []


async def test_a_finished_view_still_in_the_store_is_an_orphan(live_bot):
    view = LiveView()
    live_bot._connection.store_view(view, MESSAGE)
    item = orphaned.view_store(live_bot)._views[MESSAGE][(BUTTON, "live:known")]
    item.view._BaseView__stopped.set_result(True)
    probe = SimpleNamespace(
        type=discord.InteractionType.component,
        data={"custom_id": "live:known", "component_type": BUTTON},
        message=SimpleNamespace(id=MESSAGE),
    )

    assert orphaned.is_owned(orphaned.view_store(live_bot), probe) is False


def test_mark_ignores_slash_commands_and_never_raises():
    command = SimpleNamespace(type=discord.InteractionType.application_command, extras={})
    orphaned.mark(SimpleNamespace(), command)
    assert command.extras == {}

    broken = SimpleNamespace(type=discord.InteractionType.component, extras={}, data={})
    orphaned.mark(SimpleNamespace(), broken)
    assert broken.extras == {}


async def test_an_already_answered_interaction_is_never_answered_twice():
    sent: list[str] = []
    interaction = SimpleNamespace(
        extras={orphaned.ORPHANED: True},
        response=SimpleNamespace(
            is_done=lambda: True, send_message=lambda *a, **k: sent.append("x")
        ),
    )

    await orphaned.on_interaction(interaction)

    assert sent == []


def test_the_sentence_is_the_stored_words():
    store = SimpleNamespace(get=lambda guild_id, key: "Gone. Try {command}.")
    interaction = SimpleNamespace(client=SimpleNamespace(store=store), guild=SimpleNamespace(id=1))

    assert orphaned.sentence(interaction, "/poll") == "Gone. Try /poll."
    assert orphaned.sentence(interaction, "") == "Gone. Try the command."


def test_the_key_is_a_core_text_key_with_help():
    assert KEY_TYPES[PANEL_EXPIRED_TEXT_KEY] == "text"
    assert PANEL_EXPIRED_TEXT_KEY in CORE_KEYS
    assert namespace_of(PANEL_EXPIRED_TEXT_KEY) == "core"
    assert "{command}" in KEY_HELP[PANEL_EXPIRED_TEXT_KEY]
    assert "{command}" in PANEL_EXPIRED_TEXT


def test_the_row_is_routine_and_headed_core():
    assert PANEL_EXPIRED_CLICK in ROUTINE
    assert is_important(PANEL_EXPIRED_CLICK) is False
    assert feature_of(PANEL_EXPIRED_CLICK) == "core"


@pytest.mark.parametrize(
    ("command", "feature"),
    [
        ("/request", "request"),
        ("/event", "events"),
        ("/settings", "core"),
        ("/voice", ""),
        ("", ""),
    ],
)
def test_the_feature_comes_from_the_command_head(command, feature):
    assert orphaned.feature_of(command) == feature
