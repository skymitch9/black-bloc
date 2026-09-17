from types import SimpleNamespace

import discord
import pytest

from black_bloc import posts
from black_bloc.cogs.community import posts as cog
from black_bloc.config import load_settings
from black_bloc.settings_store import SettingsStore

GUILD = 7
TEST_CHANNEL = 111
WELCOME_CHANNEL = 222
STAFF_ROLE = 900
STAFF_ID = 42


class FakeRole:
    def __init__(self, role_id, name="Aunties / Uncles"):
        self.id = role_id
        self.name = name
        self.mentionable = False


class FakeMessage:
    def __init__(self, channel, message_id, **kwargs):
        self.channel = channel
        self.id = message_id
        self.kwargs = dict(kwargs)
        self.pinned = False
        one = kwargs.get("embed")
        self.embeds = list(kwargs.get("embeds") or ([one] if one else []))

    async def edit(self, **kwargs):
        self.kwargs |= kwargs

    async def pin(self, reason=None):
        self.pinned = True

    async def delete(self):
        self.channel.messages.pop(self.id, None)


class FakeChannel:
    def __init__(self, channel_id, name):
        self.id = channel_id
        self.name = name
        self.messages = {}
        self.next_id = 9000

    async def send(self, **kwargs):
        self.next_id += 1
        message = FakeMessage(self, self.next_id, **kwargs)
        self.messages[message.id] = message
        return message

    async def fetch_message(self, message_id):
        found = self.messages.get(int(message_id))
        if found is None:
            raise discord.NotFound(SimpleNamespace(status=404, reason="Not Found"), "gone")
        return found


class FakeGuild:
    def __init__(self, bot):
        self.id = GUILD
        self.bot = bot
        self.unavailable = False

    def get_channel(self, channel_id):
        return self.bot.channels.get(int(channel_id))

    def get_role(self, role_id):
        return FakeRole(int(role_id))

    def get_member(self, user_id):
        return None


class FakeStaff:
    def __init__(self):
        self.id = STAFF_ID
        self.name = "Mod"
        self.display_name = "Mod"
        self.roles = [FakeRole(STAFF_ROLE)]
        self.guild_permissions = SimpleNamespace(mention_everyone=False)


class FakeBot:
    def __init__(self, db, store, settings):
        self.db = db
        self.store = store
        self.settings = settings
        self.guard = None
        self.channels = {
            TEST_CHANNEL: FakeChannel(TEST_CHANNEL, "blackbloc-logs"),
            WELCOME_CHANNEL: FakeChannel(WELCOME_CHANNEL, "welcome"),
        }
        self.guild = FakeGuild(self)
        self.guilds = [self.guild]

    def get_channel(self, channel_id):
        return self.channels.get(int(channel_id))

    def get_guild(self, guild_id):
        return self.guild if int(guild_id) == GUILD else None

    def get_cog(self, name):
        return None


class FakeResponse:
    def __init__(self):
        self.messages = []
        self.modals = []
        self.done = False

    def is_done(self):
        return self.done

    async def send_message(self, content=None, ephemeral=False, **kwargs):
        self.done = True
        self.messages.append({"content": content, "ephemeral": ephemeral, **kwargs})

    async def send_modal(self, modal):
        self.done = True
        self.modals.append(modal)

    async def defer(self, ephemeral=False, **kwargs):
        self.done = True


class FakeFollowup:
    def __init__(self, response):
        self.response = response

    async def send(self, content=None, ephemeral=False, **kwargs):
        self.response.messages.append({"content": content, "ephemeral": ephemeral, **kwargs})


class FakeInteraction:
    def __init__(self, bot, user):
        self.client = bot
        self.user = user
        self.guild = bot.guild
        self.guild_id = bot.guild.id
        self.channel_id = TEST_CHANNEL
        self.response = FakeResponse()
        self.followup = FakeFollowup(self.response)
        self.edits = []

    async def edit_original_response(self, **kwargs):
        self.edits.append(kwargs)
        return FakeMessage(None, 9500, **kwargs)

    async def original_response(self):
        return FakeMessage(None, 9500)

    @property
    def said(self):
        found = [one["content"] for one in self.response.messages if one.get("content")]
        return found[-1] if found else None

    @property
    def card(self):
        return self.edits[-1] if self.edits else None


@pytest.fixture
async def bot(db, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    settings = load_settings(
        _env_file=None, test_mode=True, test_channel_id=TEST_CHANNEL, site_origin="https://x.test"
    )
    store = SettingsStore(db, settings)
    await store.load()
    await store.set(GUILD, "staff_channel_id", TEST_CHANNEL)
    await store.set(GUILD, posts.MODE_KEY, "on")
    found = FakeBot(db, store, settings)
    store.is_staff = lambda member: getattr(member, "id", None) == STAFF_ID
    return found


@pytest.fixture
def staff():
    return FakeStaff()


async def kinds(db):
    cur = await db.conn.execute("SELECT kind FROM action_log ORDER BY id")
    return [row["kind"] for row in await cur.fetchall()]


async def a_post(bot, *, slug="notice", body="Hello.", channel_id=TEST_CHANNEL, **fields):
    post_id = await posts.create_post(
        bot.db, GUILD, slug=slug, title="A notice", body=body, channel_id=channel_id, **fields
    )
    return await posts.get_post_by_id(bot.db, post_id)


def labels(view):
    return [one.label for one in view.children if getattr(one, "label", None)]


def placeholders(view):
    return [one.placeholder for one in view.children if getattr(one, "placeholder", None)]


def picked(view):
    """Which value the mode select shows as chosen — the panel's own reading of the key."""
    mode = next(one for one in view.children if getattr(one, "placeholder", None) == cog.MODE_PICK)
    return next((one.value for one in mode.options if one.default), None)


# --- the panel --------------------------------------------------------------------------------


async def test_the_panel_writes_a_line_per_post_and_offers_the_way_in(bot, staff):
    await a_post(bot)
    await a_post(bot, slug="rules", body="", channel_id=None)

    embed, view = await cog.build_panel(bot, bot.guild, staff)

    said = embed.description
    assert "**A notice** · #blackbloc-logs · not posted" in said
    assert "no channel yet" in said
    assert labels(view) == ["New post…", "Logs", "Open on the site"]
    assert placeholders(view) == ["Posts are: off / shadow / on", "A post…"]


async def test_an_empty_panel_says_so_rather_than_showing_nothing(bot, staff):
    embed, view = await cog.build_panel(bot, bot.guild, staff)

    assert posts.PANEL_EMPTY in embed.description
    assert placeholders(view) == ["Posts are: off / shadow / on"]


async def test_the_panel_says_in_words_when_posts_are_off(bot, staff):
    await bot.store.set(GUILD, posts.MODE_KEY, "off")

    embed, view = await cog.build_panel(bot, bot.guild, staff)

    assert posts.POSTS_OFF in embed.description
    assert picked(view) == "off"


async def test_the_panel_says_where_shadow_puts_it_and_the_select_shows_the_third_value(
    bot, staff
):
    await a_post(bot)
    await bot.store.set(GUILD, posts.MODE_KEY, "shadow")

    embed, view = await cog.build_panel(bot, bot.guild, staff)

    assert "Posts are in shadow" in embed.description
    assert "#blackbloc-logs" in embed.description
    assert posts.POSTS_OFF not in embed.description
    mode = next(one for one in view.children if getattr(one, "placeholder", None) == cog.MODE_PICK)
    assert [one.value for one in mode.options] == ["off", "shadow", "on"]
    assert [one.label for one in mode.options] == [
        "Posts are: off",
        "Posts are: shadow",
        "Posts are: on",
    ]
    assert picked(view) == "shadow"


async def test_the_card_says_where_a_shadow_press_would_actually_go(bot, staff):
    row = await a_post(bot, slug="welcome-here", channel_id=WELCOME_CHANNEL)
    await bot.store.set(GUILD, posts.MODE_KEY, "shadow")

    embed, _ = cog.build_card(bot, bot.guild, row)

    assert (
        "shadow — this goes to #blackbloc-logs, not #welcome, until posts are on."
        in embed.description
    )


# --- the card ---------------------------------------------------------------------------------


async def test_the_card_offers_post_it_before_it_is_posted_and_update_after(bot, staff):
    row = await a_post(bot)

    _, before = cog.build_card(bot, bot.guild, row)
    await posts.set_posted(bot.db, int(row["id"]), 500, posts.hash_of(row))
    after_row = await posts.get_post_by_id(bot.db, int(row["id"]))
    _, after = cog.build_card(bot, bot.guild, after_row)

    assert "Post it" in labels(before) and "Update the post" not in labels(before)
    assert "Update the post" in labels(after) and "Post it" not in labels(after)
    assert "Take it down" not in labels(before), "there is nothing to take down yet"
    assert "Take it down" in labels(after)


async def test_the_pin_button_is_labelled_with_the_move_it_makes(bot, staff):
    pinned = await a_post(bot, slug="one", pin=True)
    loose = await a_post(bot, slug="two", pin=False)

    _, one = cog.build_card(bot, bot.guild, pinned)
    _, two = cog.build_card(bot, bot.guild, loose)

    assert "Do not pin it" in labels(one) and "Pin it" not in labels(one)
    assert "Pin it" in labels(two) and "Do not pin it" not in labels(two)


async def test_the_shipped_post_offers_put_it_back_and_a_written_one_offers_delete(bot, staff):
    await posts.seed_posts(bot, bot.guild)
    seeded = await posts.get_post(bot.db, GUILD, "welcome")
    mine = await a_post(bot)

    _, one = cog.build_card(bot, bot.guild, seeded)
    _, two = cog.build_card(bot, bot.guild, mine)

    assert "Put the original back" in labels(one) and "Delete this post" not in labels(one)
    assert "Delete this post" in labels(two) and "Put the original back" not in labels(two)


async def test_the_card_shows_the_first_of_the_words_and_never_the_whole_post(bot, staff):
    row = await a_post(bot, body="x" * 900)

    embed, _ = cog.build_card(bot, bot.guild, row)

    assert len(embed.description) < 900
    assert embed.description.endswith("…")


async def test_a_card_and_a_panel_are_both_built_with_the_two_select_rows(bot, staff):
    row = await a_post(bot)

    _, view = cog.build_card(bot, bot.guild, row)

    assert placeholders(view) == ["Channel…", "Style…"]
    assert len(view.children) <= 25


# --- the moves ---------------------------------------------------------------------------------


async def test_a_card_button_runs_the_shared_move_and_says_what_it_did(bot, staff):
    bot.guard = SimpleNamespace(
        allows_channel=lambda one: int(getattr(one, "id", one)) == TEST_CHANNEL,
        refusal_message=lambda: "test mode",
    )
    await a_post(bot)
    interaction = FakeInteraction(bot, staff)

    await cog.run_move(interaction, "notice", posts.publish_post)

    assert "is posted in #blackbloc-logs" in interaction.said
    assert bot.channels[TEST_CHANNEL].messages
    assert await kinds(bot.db) == ["post.posted", "post.pinned"]


async def test_every_move_refuses_in_words_while_posts_are_off(bot, staff):
    await a_post(bot)
    await bot.store.set(GUILD, posts.MODE_KEY, "off")
    interaction = FakeInteraction(bot, staff)

    await cog.run_move(interaction, "notice", posts.publish_post)

    assert interaction.said == posts.POSTS_OFF
    assert bot.channels[TEST_CHANNEL].messages == {}
    assert await kinds(bot.db) == []


async def test_the_pin_button_saves_through_the_one_shared_path(bot, staff):
    row = await a_post(bot, pin=True)
    interaction = FakeInteraction(bot, staff)

    await cog.run_move(interaction, "notice", posts.save_post, pin=False)

    fresh = await posts.get_post_by_id(bot.db, int(row["id"]))
    assert fresh["pin"] == 0
    assert await kinds(bot.db) == ["post.saved"]


async def test_the_mode_select_reaches_all_three_and_writes_one_row_each(bot, staff):
    said = await posts.set_mode(bot, bot.guild, staff, "shadow")

    assert bot.store.get(GUILD, posts.MODE_KEY) == "shadow"
    assert "#blackbloc-logs" in said
    assert await kinds(bot.db) == ["post.mode"]

    off = await posts.set_mode(bot, bot.guild, staff, "off")

    assert bot.store.get(GUILD, posts.MODE_KEY) == "off"
    assert "`/posts` disappears" in off
    assert await kinds(bot.db) == ["post.mode", "post.mode"]


async def test_the_edit_modal_arrives_prefilled_and_names_the_cap(bot, staff):
    row = await a_post(bot, body="Hello.", style=posts.EMBED)

    modal = cog.EditPostModal("notice", row)

    assert str(modal.heading.default) == "A notice"
    assert str(modal.body.default) == "Hello."
    assert "4096" in modal.body.label


async def test_the_modal_can_hold_more_than_a_plain_message_so_the_cap_is_checked_on_submit(
    bot, staff
):
    """Discord's paragraph box holds 4000; a plain post holds 2000, and the gap is the bug."""
    await a_post(bot)
    interaction = FakeInteraction(bot, staff)

    await cog.run_move(interaction, "notice", posts.save_post, body="x" * 3000)

    assert cog.BODY_BOX_MAX == 4000 > posts.CAPS[posts.PLAIN]
    assert "3000" in interaction.said and "2000" in interaction.said
    fresh = await posts.get_post(bot.db, GUILD, "notice")
    assert fresh["body"] == "Hello."


# --- the loop ----------------------------------------------------------------------------------


async def test_the_first_tick_seeds_the_guild_because_cog_load_has_none(bot):
    """`cog_load` runs before the gateway hands any guild over, so seeding waits for a tick."""
    found = cog.Posts(bot)

    await found._reconcile_loop()

    row = await posts.get_post(bot.db, GUILD, "welcome")
    assert row is not None and row["body"] == posts.seed_entries()[0]["body"]
    assert "post.seeded" in await kinds(bot.db)
    assert found.last_ok_at and found.last_error is None


async def test_a_later_tick_seeds_nothing_and_only_refreshes_the_shipped_hash(bot):
    found = cog.Posts(bot)
    await found._reconcile_loop()
    await bot.db.conn.execute("UPDATE posts SET seed_hash = 'old'")
    await bot.db.conn.commit()

    await found._reconcile_loop()

    assert await posts.count_posts(bot.db, GUILD) == 1
    row = await posts.get_post(bot.db, GUILD, "welcome")
    assert row["seed_hash"] == posts.seed_hash(posts.seed_entries()[0])
    assert (await kinds(bot.db)).count("post.seeded") == 1


async def test_the_loop_forgets_a_message_somebody_deleted_by_hand(bot, staff):
    bot.guard = SimpleNamespace(
        allows_channel=lambda one: int(getattr(one, "id", one)) == TEST_CHANNEL,
        refusal_message=lambda: "test mode",
    )
    row = await a_post(bot)
    await posts.publish_post(bot, bot.guild, row, staff)
    bot.channels[TEST_CHANNEL].messages.clear()
    found = cog.Posts(bot)

    await found._reconcile_loop()

    fresh = await posts.get_post_by_id(bot.db, int(row["id"]))
    assert fresh["message_id"] is None
    assert "post.message_gone" in await kinds(bot.db)


async def test_the_loop_says_which_of_its_own_names_it_answers_for(bot):
    found = cog.Posts(bot)
    found.last_ok_at = "then"
    found.last_error = None

    assert found.loop_health("_reconcile_loop") == ("then", None)
    assert found.loop_health("reconcile") == ("then", None)
    assert found.loop_health("something_else") == (None, None)


async def test_a_loop_that_raised_is_restarted_and_its_failure_is_on_the_record(bot):
    """Checklist 28: discord.py stops a loop for the life of the process otherwise."""
    found = cog.Posts(bot)
    restarted = []
    found._reconcile_loop.restart = lambda *a, **k: restarted.append(True)

    await found._reconcile_broke(RuntimeError("the gateway went away"))

    assert restarted == [True]
    assert "RuntimeError: the gateway went away" in found.last_error
    assert found.loop_health("reconcile")[1] == found.last_error


async def test_the_loop_does_nothing_at_all_without_a_database(bot):
    bot.db = SimpleNamespace(is_connected=False)
    found = cog.Posts(bot)

    await found._reconcile_loop()

    assert found.last_ok_at is None


# --- the command ------------------------------------------------------------------------------


async def test_the_command_is_staff_only_and_opens_the_panel(bot, staff):
    await a_post(bot)
    found = cog.Posts(bot)
    interaction = FakeInteraction(bot, staff)

    await found.posts_panel_command.callback(found, interaction)

    assert interaction.response.messages
    sent = interaction.response.messages[-1]
    assert sent["ephemeral"] is True
    assert sent["embed"].title == posts.PANEL_TITLE


async def test_a_member_who_is_not_staff_is_told_so_and_sees_no_panel(bot):
    await a_post(bot)
    found = cog.Posts(bot)
    interaction = FakeInteraction(bot, SimpleNamespace(id=99, roles=[]))

    await found.posts_panel_command.callback(found, interaction)

    assert interaction.said
    assert all("embed" not in one for one in interaction.response.messages)


async def test_the_command_says_so_when_the_database_is_not_there(bot, staff):
    bot.db = SimpleNamespace(is_connected=False)
    found = cog.Posts(bot)
    interaction = FakeInteraction(bot, staff)

    await found.posts_panel_command.callback(found, interaction)

    assert "database" in interaction.said.lower()
