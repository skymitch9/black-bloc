import json
from types import SimpleNamespace

import pytest

from black_bloc.chat_memory import (
    Note,
    Profile,
    fact_key,
    facts_of,
    overridden,
    profile_for,
    remembers,
    save_profile,
    set_override,
)
from black_bloc.cogs.content import chat_memory as cog_module
from black_bloc.cogs.content.chat_memory import (
    FORGET_ALL_MOVE,
    FORGET_WORDS_MOVE,
    PANEL_TIMEOUT_FOOTER,
    REFRESH_MOVE,
    START_MOVE,
    STOP_MOVE,
    ChatMemory,
    ForgetOnePick,
    ForgetWordsModal,
    build_panel,
    drop_by_words,
    moves_for,
    profile_words,
    render_panel,
)
from black_bloc.config import load_settings
from black_bloc.settings_store import DB_UNAVAILABLE, SettingsStore
from black_bloc.storage.db import Database

GUILD = 7
TEST_CHANNEL = 111
MEMBER = 900
AT = "2026-09-02T00:00:00+00:00"


class FakePerms:
    def __init__(self, manage_guild=False, view_channel=False):
        self.manage_guild = manage_guild
        self.view_channel = view_channel


class FakeMessage:
    def __init__(self, message_id, **kwargs):
        self.id = message_id
        self.kwargs = kwargs

    async def edit(self, **kwargs):
        self.kwargs |= kwargs

    @property
    def embeds(self):
        held = self.kwargs.get("embeds")
        if held is not None:
            return list(held)
        one = self.kwargs.get("embed")
        return [one] if one is not None else []


class FakeText:
    def __init__(self, channel_id):
        self.id = channel_id
        self.messages = []

    def permissions_for(self, role):
        return FakePerms()

    async def send(self, content=None, **kwargs):
        self.messages.append(content)
        return FakeMessage(len(self.messages), content=content, **kwargs)


class FakeGuild:
    def __init__(self):
        self.id = GUILD
        self.name = "Black in a Flash!"
        self.roles = []
        self.channels = {TEST_CHANNEL: FakeText(TEST_CHANNEL)}
        self.members = []

    def get_channel(self, channel_id):
        return self.channels.get(channel_id)

    def get_member(self, user_id):
        return None


class FakeMember:
    def __init__(self, guild, user_id=MEMBER):
        self.id = user_id
        self.guild = guild
        self.name = "Ada"
        self.display_name = "Ada"
        self.mention = f"<@{user_id}>"
        self.roles = []
        self.guild_permissions = FakePerms()


class FakeBot:
    def __init__(self, db, store, settings, guild):
        self.db = db
        self.store = store
        self.settings = settings
        self.guild = guild
        self.guilds = [guild]
        self.guard = None

    def get_guild(self, guild_id):
        return self.guild if int(guild_id) == self.guild.id else None

    def get_channel(self, channel_id):
        return self.guild.get_channel(channel_id)


class FakeResponse:
    def __init__(self):
        self.messages = []
        self.modals = []
        self.deferred = False

    def is_done(self):
        return self.deferred or bool(self.messages)

    async def send_message(self, content=None, ephemeral=False, **kwargs):
        self.messages.append({"content": content, "ephemeral": ephemeral, **kwargs})

    async def defer(self, ephemeral=False):
        self.deferred = True

    async def send_modal(self, modal):
        self.modals.append(modal)
        self.deferred = True


class FakeFollowup:
    def __init__(self, response):
        self.response = response

    async def send(self, content=None, ephemeral=False, **kwargs):
        self.response.messages.append({"content": content, "ephemeral": ephemeral, **kwargs})


class FakeInteraction:
    def __init__(self, bot, user, *, guild=True):
        self.client = bot
        self.user = user
        self.guild = bot.guild if guild else None
        self.guild_id = bot.guild.id if guild else None
        self.response = FakeResponse()
        self.followup = FakeFollowup(self.response)
        self.edits = []

    async def original_response(self):
        return FakeMessage(1)

    async def edit_original_response(self, **kwargs):
        self.edits.append(kwargs)
        return FakeMessage(9500, **kwargs)

    @property
    def rendered(self):
        if self.edits:
            return self.edits[-1]
        return self.response.messages[-1] if self.response.messages else {}

    @property
    def view(self):
        return self.rendered.get("view")

    @property
    def embed(self):
        return self.rendered.get("embed")

    @property
    def words(self):
        found = self.embed
        return "" if found is None else str(found.description or "")

    @property
    def sent(self):
        said = [
            one["content"] for one in self.response.messages if one.get("content") is not None
        ]
        return said[-1] if said else None

    @property
    def ephemeral(self):
        return all(one["ephemeral"] for one in self.response.messages)

    def labels(self):
        found = self.view
        return (
            []
            if found is None
            else [one.label for one in found.children if getattr(one, "label", None)]
        )

    def placeholders(self):
        found = self.view
        return (
            []
            if found is None
            else [
                one.placeholder
                for one in found.children
                if getattr(one, "placeholder", None) is not None
            ]
        )


@pytest.fixture
async def db(tmp_path):
    database = Database(tmp_path / "m.sqlite3")
    await database.connect()
    try:
        yield database
    finally:
        await database.close()


@pytest.fixture
async def bot(db, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    settings = load_settings(
        _env_file=None, test_mode=True, test_channel_id=TEST_CHANNEL, dev_guild_id=GUILD
    )
    store = SettingsStore(db, settings)
    await store.load()
    await store.set(GUILD, "chat_memory_mode", "on")
    return FakeBot(db, store, settings, FakeGuild())


@pytest.fixture
def cog(bot):
    return ChatMemory(bot)


@pytest.fixture
def member(bot):
    return FakeMember(bot.guild)


async def a_profile(db, *, notes=None, threads=None, call_me="Sky"):
    await save_profile(
        db,
        MEMBER,
        GUILD,
        Profile(
            call_me=call_me,
            notes=notes if notes is not None else (Note("likes short answers", "server", AT),),
            threads=(
                threads if threads is not None else (Note("was asking about it", "server", AT),)
            ),
            turns_seen=4,
            created_at=AT,
            updated_at=AT,
        ),
    )


async def many_facts(db, count=30):
    await save_profile(
        db,
        MEMBER,
        GUILD,
        Profile(
            call_me="Sky",
            notes=tuple(Note(f"prefers option {n}", "server", AT) for n in range(count)),
            threads=(),
            turns_seen=4,
            created_at=AT,
            updated_at=AT,
        ),
    )


async def action_kinds(db):
    cur = await db.conn.execute("SELECT kind FROM action_log ORDER BY id")
    return [row["kind"] for row in await cur.fetchall()]


async def action_rows(db):
    cur = await db.conn.execute("SELECT kind, details FROM action_log ORDER BY id")
    return [
        (row["kind"], json.loads(row["details"]) if row["details"] else {})
        for row in await cur.fetchall()
    ]


async def open_panel(bot, member):
    interaction = FakeInteraction(bot, member)
    await ChatMemory(bot).memory.callback(ChatMemory(bot), interaction)
    return interaction


def button(view, label):
    return next(one for one in view.children if getattr(one, "label", None) == label)


def picker(view):
    return next(one for one in view.children if isinstance(one, ForgetOnePick))


# The words a person reads back.


def test_the_lines_are_numbered_plain_and_marked_by_scope():
    lines = profile_words(
        Profile(
            call_me="Sky",
            notes=(Note("likes short answers", "server", AT), Note("prefers she/her", "dm", AT)),
            threads=(Note("was asking about the cookout", "server", AT),),
        )
    )
    said = "\n".join(lines)

    assert "Nobody else can read this" in said
    assert "**#1** It calls you **Sky**." in said
    assert "**#2** likes short answers" in said
    assert "**#3** prefers she/her" in said and "learned in a DM" in said
    assert "**#4** *still open:* was asking about the cookout" in said
    assert "/memory forget-this" not in said and "/memory show" not in said


def test_nothing_stored_reads_back_as_the_header_alone():
    assert profile_words(None) == profile_words(Profile())


# §C — the table is data, and every state renders exactly its row.


@pytest.mark.parametrize(
    "remembered,facts,expected",
    [
        (True, 0, ["Stop remembering me", "Refresh"]),
        (True, 1, ["Forget everything", "Stop remembering me", "Refresh"]),
        (True, 25, ["Forget everything", "Stop remembering me", "Refresh"]),
        (
            True,
            26,
            [
                "Forget everything",
                "Forget by words…",
                "Stop remembering me",
                "Refresh",
            ],
        ),
        (False, 0, ["Remember me again", "Refresh"]),
        (False, 1, ["Forget everything", "Remember me again", "Refresh"]),
    ],
)
def test_every_state_renders_exactly_its_row_of_the_button_table(remembered, facts, expected):
    assert [
        one.label for one in moves_for(remembered=remembered, facts=facts)
    ] == expected


def test_no_state_offers_both_spellings_of_one_move():
    for remembered in (True, False):
        for facts in (0, 1, 12, 26, 41):
            labels = [one.label for one in moves_for(remembered=remembered, facts=facts)]
            assert len(labels) == len(set(labels))
            assert not (STOP_MOVE.label in labels and START_MOVE.label in labels)
            assert (FORGET_ALL_MOVE.label in labels) is bool(facts)
            assert (FORGET_WORDS_MOVE.label in labels) is (facts > 25)
    assert REFRESH_MOVE.label == "Refresh"


async def test_memory_opens_one_ephemeral_panel_with_the_lines_and_the_controls(
    bot, member, db
):
    await a_profile(db)

    interaction = await open_panel(bot, member)

    assert interaction.ephemeral is True
    assert interaction.embed.title == "What Black Bloc remembers about you"
    assert "Nobody else can read this" in interaction.words
    assert "**#2** likes short answers" in interaction.words
    assert interaction.placeholders() == ["Forget one of these…"]
    assert interaction.labels() == [
        "Forget everything",
        "Stop remembering me",
        "Refresh",
    ]
    assert interaction.rendered["allowed_mentions"].everyone is False


async def test_every_send_and_every_edit_carries_allowed_mentions(bot, member, db):
    """A `call_me` is attacker-supplied text, so no render of it may ever ping (checklist 11)."""
    await a_profile(db, call_me="@everyone")
    opening = await open_panel(bot, member)
    clicking = FakeInteraction(bot, member)
    await button(opening.view, "Refresh").callback(clicking)
    asking = FakeInteraction(bot, member)
    await button(clicking.view, "Forget everything").callback(asking)

    for rendered in (opening.rendered, clicking.edits[-1], asking.edits[-1]):
        mentions = rendered["allowed_mentions"]
        assert mentions.everyone is False and mentions.roles is False
        assert mentions.users is False


async def test_nothing_stored_renders_no_picker_and_no_forget_everything(bot, member):
    interaction = await open_panel(bot, member)

    assert "not written anything down about you yet" in interaction.words
    assert interaction.placeholders() == []
    assert interaction.labels() == ["Stop remembering me", "Refresh"]


async def test_opted_out_with_facts_still_stored_keeps_the_forget_controls(bot, member, db):
    """A Lead flipping chat_memory_consent leaves people not-remembered with a profile."""
    await a_profile(db)
    await bot.store.set(GUILD, "chat_memory_consent", "optin")

    interaction = await open_panel(bot, member)

    assert await remembers(bot.db, MEMBER, GUILD, consent="optin") is False
    assert "not remembering you" in interaction.words
    assert interaction.placeholders() == ["Forget one of these…"]
    assert interaction.labels() == ["Forget everything", "Remember me again", "Refresh"]


async def test_the_mode_being_off_is_a_line_and_never_a_dead_command(bot, member, db):
    """Owner, 2026-09-03 16:12 (I-M1): open it. Turning memory off does not delete profiles,
    so the only door to what is already stored must stay open."""
    await bot.store.set(GUILD, "chat_memory_mode", "off")
    await a_profile(db)

    interaction = await open_panel(bot, member)

    assert "not remembering anybody here" in interaction.words
    assert "**#2** likes short answers" in interaction.words
    assert interaction.labels() == ["Forget everything", "Stop remembering me", "Refresh"]
    assert not any(getattr(one, "disabled", False) for one in interaction.view.children)


def test_memory_is_no_longer_hidden_when_the_mode_is_off():
    from black_bloc import command_visibility as cv

    assert "chat_memory_mode" not in cv.HIDDEN_WHEN_OFF
    assert all("memory" not in names for names in cv.HIDDEN_WHEN_OFF.values())


# The picker.


async def test_picking_a_line_drops_exactly_that_one_and_logs_a_count_not_the_words(
    bot, member, db
):
    await a_profile(
        db,
        notes=(Note("likes short answers", "server", AT), Note("hates emoji", "server", AT)),
    )
    opening = await open_panel(bot, member)
    pick = picker(opening.view)
    pick._values = ["note:1"]
    clicking = FakeInteraction(bot, member)

    await pick.callback(clicking)
    profile = await profile_for(db, MEMBER, GUILD)

    assert [one.text for one in profile.notes] == ["likes short answers"]
    assert clicking.sent == "Dropped **1** line(s). What is left is above."
    rows = await action_rows(db)
    assert [kind for kind, _ in rows] == ["chat.memory_forgot"]
    assert rows[0][1] == {"who_asked": "self", "lines": 1, "via": "discord"}
    assert "emoji" not in json.dumps(rows)


async def test_a_line_that_moved_between_render_and_click_is_never_the_one_dropped(
    bot, member, db
):
    await a_profile(
        db,
        notes=(Note("likes short answers", "server", AT), Note("hates emoji", "server", AT)),
    )
    opening = await open_panel(bot, member)
    pick = picker(opening.view)
    pick._values = ["note:1"]
    await a_profile(
        db,
        notes=(Note("likes short answers", "server", AT), Note("plays late", "server", AT)),
    )
    clicking = FakeInteraction(bot, member)

    await pick.callback(clicking)
    profile = await profile_for(db, MEMBER, GUILD)

    assert [one.text for one in profile.notes] == ["likes short answers", "plays late"]
    assert "not there any more" in clicking.sent
    assert await action_kinds(db) == []


async def test_a_line_dropped_out_from_under_the_click_re_renders_rather_than_guessing(
    bot, member, db
):
    await a_profile(db)
    opening = await open_panel(bot, member)
    pick = picker(opening.view)
    pick._values = ["thread:0"]
    await a_profile(db, threads=())
    clicking = FakeInteraction(bot, member)

    await pick.callback(clicking)

    assert "not there any more" in clicking.sent
    assert await action_kinds(db) == []


async def test_the_picker_caps_at_twenty_five_and_never_points_at_the_site(bot, member, db):
    await many_facts(db, count=30)

    interaction = await open_panel(bot, member)
    pick = picker(interaction.view)

    assert len(pick.options) == 25
    assert "the rest are on the site" not in pick.placeholder
    assert pick.placeholder == "25 of 31 — Forget by words… reaches the rest"
    assert "Forget by words…" in interaction.labels()


async def test_forget_by_words_is_absent_below_the_cap(bot, member, db):
    await a_profile(db)

    interaction = await open_panel(bot, member)

    assert "Forget by words…" not in interaction.labels()
    assert picker(interaction.view).placeholder == "Forget one of these…"


async def test_the_picker_labels_number_the_lines_the_way_the_embed_does(bot, member, db):
    await a_profile(db)

    interaction = await open_panel(bot, member)
    pick = picker(interaction.view)

    assert [one.label for one in pick.options] == [
        "#1 · what it calls you · Sky",
        "#2 · likes short answers",
        "#3 · still open · was asking about it",
    ]
    assert [one.value for one in pick.options] == ["name:0", "note:0", "thread:0"]


# The confirms.


async def test_forget_everything_asks_first_and_keep_it_changes_nothing(bot, member, db):
    await a_profile(db)
    opening = await open_panel(bot, member)
    asking = FakeInteraction(bot, member)

    await button(opening.view, "Forget everything").callback(asking)

    assert asking.labels() == ["Yes, forget it all", "Keep it"]
    assert any(field.name == "Are you sure?" for field in asking.embed.fields)

    keeping = FakeInteraction(bot, member)
    await button(asking.view, "Keep it").callback(keeping)

    assert await profile_for(db, MEMBER, GUILD) is not None
    assert await action_kinds(db) == []
    assert keeping.labels() == ["Forget everything", "Stop remembering me", "Refresh"]


async def test_forget_everything_confirmed_clears_it_once_and_leaves_one_row(bot, member, db):
    await a_profile(db)
    opening = await open_panel(bot, member)
    asking = FakeInteraction(bot, member)
    await button(opening.view, "Forget everything").callback(asking)
    confirming = FakeInteraction(bot, member)

    await button(asking.view, "Yes, forget it all").callback(confirming)

    assert await profile_for(db, MEMBER, GUILD) is None
    assert confirming.sent == "Cleared. Black Bloc remembers nothing about you here."
    rows = await action_rows(db)
    assert [kind for kind, _ in rows] == ["chat.memory_forgot"]
    assert rows[0][1] == {"who_asked": "self", "via": "discord"}
    assert confirming.labels() == ["Stop remembering me", "Refresh"]


async def test_stop_remembering_me_asks_first_then_opts_out_and_wipes(bot, member, db):
    await a_profile(db)
    opening = await open_panel(bot, member)
    asking = FakeInteraction(bot, member)
    await button(opening.view, "Stop remembering me").callback(asking)

    assert asking.labels() == ["Yes, stop", "Keep it"]

    confirming = FakeInteraction(bot, member)
    await button(asking.view, "Yes, stop").callback(confirming)

    assert await profile_for(db, MEMBER, GUILD) is None
    assert await remembers(db, MEMBER, GUILD, consent="optout") is False
    rows = await action_rows(db)
    assert [kind for kind, _ in rows] == ["chat.memory_optout"]
    assert rows[0][1] == {"via": "discord"}
    assert confirming.labels() == ["Remember me again", "Refresh"]


async def test_remember_me_again_needs_no_confirm_and_brings_the_writing_back(bot, member, db):
    await set_override(db, MEMBER, GUILD)
    opening = await open_panel(bot, member)

    clicking = FakeInteraction(bot, member)
    await button(opening.view, "Remember me again").callback(clicking)

    assert await remembers(db, MEMBER, GUILD, consent="optout") is True
    assert await overridden(db, MEMBER, GUILD) is False
    assert "never what you said" in clicking.sent
    rows = await action_rows(db)
    assert [kind for kind, _ in rows] == ["chat.memory_optin"]
    assert rows[0][1] == {"via": "discord"}
    assert clicking.labels() == ["Stop remembering me", "Refresh"]


async def test_an_optin_server_writes_the_row_rather_than_removing_one(bot, member, db):
    await bot.store.set(GUILD, "chat_memory_consent", "optin")
    opening = await open_panel(bot, member)
    clicking = FakeInteraction(bot, member)

    await button(opening.view, "Remember me again").callback(clicking)

    assert await overridden(db, MEMBER, GUILD) is True
    assert await remembers(db, MEMBER, GUILD, consent="optin") is True


# The one modal.


async def test_forget_by_words_opens_the_shared_modal_and_drops_every_match(bot, member, db):
    await many_facts(db, count=30)
    opening = await open_panel(bot, member)
    opening_modal = FakeInteraction(bot, member)

    await button(opening.view, "Forget by words…").callback(opening_modal)
    modal = opening_modal.response.modals[0]

    assert isinstance(modal, ForgetWordsModal)
    assert modal.note.max_length == 200 and modal.note.required is True

    typing = FakeInteraction(bot, member)
    await modal.words_given(typing, "option 29")
    profile = await profile_for(db, MEMBER, GUILD)

    assert len(profile.notes) == 29
    assert "Dropped **1**" in typing.sent
    rows = await action_rows(db)
    assert rows[0][1] == {"who_asked": "self", "lines": 1, "via": "discord"}
    assert "option 29" not in json.dumps(rows)


async def test_words_that_match_nothing_drop_nothing_and_point_at_the_picker(bot, member, db):
    await a_profile(db)

    said, fresh = await drop_by_words(
        bot, bot.guild, FakeMember(bot.guild), GUILD, await profile_for(db, MEMBER, GUILD),
        "nothing like this",
    )

    assert "Forget one of these…" in said
    assert len(fresh.notes) == 1
    assert await action_kinds(db) == []


async def test_empty_words_are_refused_in_words_and_write_nothing(bot, member, db):
    await a_profile(db)

    said, _ = await drop_by_words(
        bot, bot.guild, member, GUILD, await profile_for(db, MEMBER, GUILD), "   "
    )

    assert "Say a few words" in said
    assert await action_kinds(db) == []


# The panel's own machinery.


async def test_every_click_re_asks_whether_the_database_is_there(bot, member, db):
    await a_profile(db)
    opening = await open_panel(bot, member)
    bot.db = SimpleNamespace(is_connected=False, conn=db.conn)
    clicking = FakeInteraction(bot, member)

    await button(opening.view, "Refresh").callback(clicking)

    assert clicking.sent == DB_UNAVAILABLE
    assert clicking.edits == []


async def test_the_modal_button_refuses_in_words_rather_than_opening_a_dead_modal(
    bot, member, db
):
    await many_facts(db, count=30)
    opening = await open_panel(bot, member)
    bot.db = SimpleNamespace(is_connected=False, conn=db.conn)
    clicking = FakeInteraction(bot, member)

    await button(opening.view, "Forget by words…").callback(clicking)

    assert clicking.sent == DB_UNAVAILABLE
    assert clicking.response.modals == []


async def test_a_re_render_retires_the_view_it_replaced(bot, member, db):
    await a_profile(db)
    opening = await open_panel(bot, member)
    first = opening.view
    interaction = FakeInteraction(bot, member)

    await render_panel(interaction, first)

    assert first.replaced is True and first.is_finished() is True


async def test_the_panel_disables_every_item_and_says_so_on_timeout(bot, member, db):
    await a_profile(db)
    interaction = await open_panel(bot, member)
    view = interaction.view
    view.message = FakeMessage(1, embeds=[interaction.embed])

    await view.on_timeout()

    assert all(one.disabled for one in view.children)
    assert view.message.kwargs["embeds"][0].footer.text == PANEL_TIMEOUT_FOOTER
    assert PANEL_TIMEOUT_FOOTER == "This panel has gone quiet — run /memory again"


async def test_the_panel_stays_up_for_the_settings_key(bot, member, db):
    await bot.store.set(GUILD, "memory_panel_minutes", 4)

    _, view = await build_panel(bot, GUILD, member)

    assert view.timeout == 4 * 60


# The two refusals that are still whole-command noes.


async def test_a_dm_with_no_home_server_at_all_is_refused_in_words(bot, cog, member):
    bot.settings = SimpleNamespace(dev_guild_id=None)
    interaction = FakeInteraction(bot, member, guild=False)

    await cog.memory.callback(cog, interaction)

    assert "not in one it knows" in interaction.sent
    assert interaction.view is None


async def test_a_database_that_is_down_is_refused_in_words(bot, cog, member, db):
    bot.db = SimpleNamespace(is_connected=False, conn=db.conn)
    interaction = FakeInteraction(bot, member)

    await cog.memory.callback(cog, interaction)

    assert interaction.sent == DB_UNAVAILABLE
    assert interaction.view is None


async def test_a_dm_files_under_the_one_server_black_bloc_knows(bot, cog, member, db):
    await a_profile(db)
    interaction = FakeInteraction(bot, member, guild=False)

    await cog.memory.callback(cog, interaction)

    assert "likes short answers" in interaction.words


# Leaving the server (unchanged by the panel).


async def test_leaving_the_server_forgets_the_profile_at_once(bot, cog, member, db):
    await a_profile(db)

    await cog.on_member_remove(member)

    assert await profile_for(db, MEMBER, GUILD) is None
    assert "chat.memory_forgot" in await action_kinds(db)


async def test_a_leaver_with_nothing_written_down_logs_nothing(bot, cog, member, db):
    await cog.on_member_remove(member)

    assert await action_kinds(db) == []


# The move layer is what the panel calls, with `via` at its Discord default.


async def test_each_move_calls_its_shared_function_and_never_touches_via(
    bot, member, db, monkeypatch
):
    seen = {}

    def spy(name):
        async def taken(*args, **kwargs):
            seen[name] = kwargs
            return ("said", None)

        return taken

    for name in ("forget_profile", "stop_remembering", "start_remembering", "drop_by_words"):
        monkeypatch.setattr(cog_module, name, spy(name))

    await a_profile(db)
    for action, extra in (
        ("forget_all", None),
        ("stop", None),
        ("start", None),
        ("forget_words", "emoji"),
    ):
        await cog_module.run_move(FakeInteraction(bot, member), action, extra)

    assert set(seen) == {
        "forget_profile",
        "stop_remembering",
        "start_remembering",
        "drop_by_words",
    }
    assert all("via" not in kwargs for kwargs in seen.values())
    assert seen["forget_profile"]["home"] == GUILD


async def test_the_keys_a_pick_carries_are_the_ones_the_pure_module_makes(bot, member, db):
    await a_profile(db)
    profile = await profile_for(db, MEMBER, GUILD)
    facts = facts_of(profile)

    pick = ForgetOnePick(facts)

    assert set(pick.shown) == {fact_key(one) for one in facts}
