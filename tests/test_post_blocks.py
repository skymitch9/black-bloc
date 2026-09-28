import json
from types import SimpleNamespace

import discord
import pytest

from black_bloc import post_blocks, posts
from black_bloc.config import load_settings
from black_bloc.settings_store import SettingsStore

GUILD = 7
TEST_CHANNEL = 111
STAFF = SimpleNamespace(id=42, guild_permissions=SimpleNamespace(mention_everyone=False))


class FakeChannel:
    def __init__(self, channel_id, name):
        self.id = channel_id
        self.name = name


class FakeGuild:
    def __init__(self, bot):
        self.id = GUILD
        self.bot = bot

    def get_channel(self, channel_id):
        return self.bot.channels.get(int(channel_id))

    def get_role(self, role_id):
        return None

    def get_member(self, user_id):
        return None


class FakeBot:
    def __init__(self, db, store, settings):
        self.db = db
        self.store = store
        self.settings = settings
        self.guard = None
        self.channels = {TEST_CHANNEL: FakeChannel(TEST_CHANNEL, "blackbloc-logs")}
        self.guilds = [FakeGuild(self)]

    def get_channel(self, channel_id):
        return self.channels.get(int(channel_id))

    def get_cog(self, name):
        return None


@pytest.fixture
async def bot(db, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    settings = load_settings(_env_file=None, test_mode=True, test_channel_id=TEST_CHANNEL)
    store = SettingsStore(db, settings)
    await store.load()
    await store.set(GUILD, posts.MODE_KEY, "on")
    return FakeBot(db, store, settings)


@pytest.fixture
def guild(bot):
    return bot.guilds[0]


async def a_post(bot, *, slug="notice", title="A notice"):
    post_id = await posts.create_post(
        bot.db, GUILD, slug=slug, title=title, body="Hello.", channel_id=TEST_CHANNEL
    )
    return await posts.get_post_by_id(bot.db, post_id)


async def logged(db):
    cur = await db.conn.execute("SELECT kind, details FROM action_log ORDER BY id")
    return [(row["kind"], json.loads(row["details"] or "{}")) for row in await cur.fetchall()]


# --- the registry -----------------------------------------------------------------------------


def test_the_front_door_is_the_first_kind_and_goes_on_one_post_at_a_time():
    found = post_blocks.KINDS["frontdoor"]

    assert list(post_blocks.KINDS) == ["frontdoor"]
    assert found.exclusive and found.cache_column == "carries_door"
    assert found.parts is post_blocks.door_parts
    assert {"frontdoor_title", "frontdoor_text", "frontdoor_ticket_label", "rehearsal_note"} <= set(
        found.keys
    )
    assert post_blocks.kind_of(" FrontDoor ") is found and post_blocks.kind_of("jukebox") is None


async def test_the_display_name_is_a_key_and_blank_restores_the_shipped_one(bot):
    found = post_blocks.KINDS["frontdoor"]
    assert post_blocks.name_of(bot.store, GUILD, found) == "Front door"

    await bot.store.set(GUILD, found.name_key, "Need-something box")

    assert post_blocks.name_of(bot.store, GUILD, found) == "Need-something box"


# --- the rows ---------------------------------------------------------------------------------


async def test_the_column_follows_the_table_both_ways(bot):
    row = await a_post(bot)

    assert await post_blocks.attach(bot.db, row, "frontdoor", by=42)
    fresh = await posts.get_post_by_id(bot.db, int(row["id"]))
    assert posts.carries_door(fresh) and post_blocks.attached_by_cache(fresh) == ["frontdoor"]
    stored = (await post_blocks.blocks_of(bot.db, int(row["id"])))[0]
    assert stored["added_by"] == 42 and stored["exclusive"] == 1 and stored["position"] == 0

    assert await post_blocks.detach(bot.db, int(row["id"]), "frontdoor")
    fresh = await posts.get_post_by_id(bot.db, int(row["id"]))
    assert not posts.carries_door(fresh) and post_blocks.attached_by_cache(fresh) == []


async def test_the_old_switch_writes_the_block_row(bot):
    row = await a_post(bot)

    await posts.set_carries_door(bot.db, int(row["id"]), True)
    assert await post_blocks.kinds_on(bot.db, int(row["id"])) == ["frontdoor"]
    await posts.set_carries_door(bot.db, int(row["id"]), False)
    assert await post_blocks.kinds_on(bot.db, int(row["id"])) == []


async def test_a_second_holder_cannot_be_written_even_past_the_check(bot):
    first = await a_post(bot, slug="first")
    second = await a_post(bot, slug="second")
    assert await post_blocks.attach(bot.db, first, "frontdoor")

    assert not await post_blocks.attach(bot.db, second, "frontdoor")

    assert await post_blocks.kinds_on(bot.db, int(second["id"])) == []
    assert not posts.carries_door(await posts.get_post_by_id(bot.db, int(second["id"])))


async def test_deleting_a_post_takes_its_blocks_with_it(bot):
    row = await a_post(bot)
    await post_blocks.attach(bot.db, row, "frontdoor")

    await posts.delete_post(bot.db, int(row["id"]))

    assert await post_blocks.blocks_in(bot.db, GUILD) == []


# --- the moves --------------------------------------------------------------------------------


async def test_adding_a_block_is_one_saved_row_and_says_when_the_door_joins(bot, guild):
    row = await a_post(bot)

    outcome = await post_blocks.add_block(bot, guild, row, STAFF, "frontdoor")

    assert outcome.ok
    assert outcome.message == (
        post_blocks.BLOCK_ADDED_SAID.format(name="Front door", title="A notice")
        + posts.CARRYING_LATER_SAID
    )
    assert [kind for kind, _ in await logged(bot.db)] == ["post.saved"]
    details = (await logged(bot.db))[0][1]
    assert details["block_added"] == "frontdoor" and details["carries_door"] is True


async def test_an_exclusive_block_is_refused_on_a_second_post_naming_the_first(bot, guild):
    first = await a_post(bot, slug="first", title="Welcome and rules")
    second = await a_post(bot, slug="second", title="Hours")
    assert (await post_blocks.add_block(bot, guild, first, STAFF, "frontdoor")).ok

    outcome = await post_blocks.add_block(bot, guild, second, STAFF, "frontdoor")

    assert not outcome.ok and outcome.status == 409 and outcome.code == "block_held_elsewhere"
    assert outcome.message == post_blocks.BLOCK_HELD_ELSEWHERE.format(
        name="Front door", other="Welcome and rules", title="Hours"
    )
    assert await post_blocks.kinds_on(bot.db, int(second["id"])) == []


async def test_removing_a_block_that_is_not_there_is_refused_in_words(bot, guild):
    row = await a_post(bot)

    outcome = await post_blocks.remove_block(bot, guild, row, STAFF, "frontdoor")

    assert not outcome.ok and outcome.code == "block_not_on"
    assert "**A notice** has no **Front door** block" in outcome.message
    assert await logged(bot.db) == []


async def test_an_unknown_kind_is_refused_by_every_move(bot, guild):
    row = await a_post(bot)

    for move in (post_blocks.add_block, post_blocks.remove_block):
        outcome = await move(bot, guild, row, STAFF, "jukebox")
        assert not outcome.ok and outcome.code == "unknown_block" and outcome.status == 400
    assert (await post_blocks.redraw_kind(bot, guild, "jukebox")).code == "unknown_block"


async def test_an_order_must_name_each_block_once(bot, guild):
    row = await a_post(bot)
    await post_blocks.add_block(bot, guild, row, STAFF, "frontdoor")

    same = await post_blocks.order_blocks(bot, guild, row, STAFF, ["frontdoor"])
    twice = await post_blocks.order_blocks(bot, guild, row, STAFF, ["frontdoor", "frontdoor"])
    wrong = await post_blocks.order_blocks(bot, guild, row, STAFF, [])

    assert same.ok and same.message == post_blocks.ORDERED_SAID.format(title="A notice")
    assert not twice.ok and twice.code == "bad_order"
    assert not wrong.ok and wrong.code == "bad_order"


async def test_the_blocks_section_shape_says_where_each_kind_rides(bot, guild):
    shaped = await post_blocks.kinds_shape(bot, guild)
    assert shaped[0]["on"] == [] and shaped[0]["where"] == post_blocks.HELD_BY_NOBODY

    await post_blocks.add_block(bot, guild, await a_post(bot), STAFF, "frontdoor")

    shaped = await post_blocks.kinds_shape(bot, guild)
    assert shaped[0]["kind"] == "frontdoor" and shaped[0]["name"] == "Front door"
    assert shaped[0]["on"] == [{"slug": "notice", "title": "A notice"}]
    assert shaped[0]["where"] == "on A notice"


# --- the message ------------------------------------------------------------------------------


async def test_blocks_join_in_order_and_every_blocks_buttons_come_along():
    first, second = discord.Embed(title="one"), discord.Embed(title="two")
    view_a, view_b = discord.ui.View(timeout=None), discord.ui.View(timeout=None)
    view_a.add_item(discord.ui.Button(label="a", custom_id="a"))
    view_b.add_item(discord.ui.Button(label="b", custom_id="b"))

    made = posts.with_blocks(
        {"content": "hi", "embed": None}, [(first, view_a, "x"), (second, view_b, "y")]
    )

    assert made["content"] == "hi" and made["embeds"] == [first, second]
    assert [one.custom_id for one in made["view"].children] == ["a", "b"]
    assert (
        posts.with_blocks({"content": "hi", "embed": None}, [(first, view_a, "x")])["view"]
        is view_a
    )


async def test_the_payload_reads_the_kinds_it_is_given(bot, guild):
    await bot.store.set(GUILD, "frontdoor_mode", "off")
    row = await a_post(bot)

    alone, stamp = posts.message_payload(bot, guild, row, [])

    assert alone == posts.render_message(row) and stamp is None


# --- the seed ---------------------------------------------------------------------------------


async def test_the_shipped_welcome_post_arrives_carrying_the_front_door(bot, guild):
    await posts.seed_posts(bot, guild)
    row = await posts.get_post(bot.db, GUILD, "welcome")

    assert await post_blocks.kinds_on(bot.db, int(row["id"])) == ["frontdoor"]
    assert posts.carries_door(row)
    assert posts.seed_entries()[0]["blocks"] == ["frontdoor"]


async def test_the_seed_never_puts_a_removed_block_back(bot, guild):
    await posts.seed_posts(bot, guild)
    row = await posts.get_post(bot.db, GUILD, "welcome")
    await post_blocks.remove_block(bot, guild, row, STAFF, "frontdoor")

    await posts.seed_posts(bot, guild)

    assert await post_blocks.kinds_on(bot.db, int(row["id"])) == []


async def test_the_seed_leaves_an_exclusive_block_where_staff_already_put_it(bot, guild):
    mine = await a_post(bot)
    await post_blocks.add_block(bot, guild, mine, STAFF, "frontdoor")

    await posts.seed_posts(bot, guild)

    welcome = await posts.get_post(bot.db, GUILD, "welcome")
    assert await post_blocks.kinds_on(bot.db, int(welcome["id"])) == []
    assert await post_blocks.kinds_on(bot.db, int(mine["id"])) == ["frontdoor"]


# --- several blocks on one message (blocks-convert, 2026-09-28) ------------------------------


class FakeMessage:
    def __init__(self, message_id, content="", **kwargs):
        self.id = message_id
        self.content = content or ""
        self.embeds = list(kwargs.get("embeds") or [])
        self.view = kwargs.get("view")
        self.pinned = False
        self.edits = []

    async def edit(self, **kwargs):
        self.edits.append(kwargs)
        if "embeds" in kwargs:
            self.embeds = list(kwargs["embeds"])
        if "view" in kwargs:
            self.view = kwargs["view"]

    async def pin(self, reason=None):
        self.pinned = True


class FakeText(FakeChannel):
    def __init__(self, channel_id, name):
        super().__init__(channel_id, name)
        self.messages = []

    async def send(self, content=None, **kwargs):
        message = FakeMessage(9000 + len(self.messages), content, **kwargs)
        self.messages.append(message)
        return message

    async def fetch_message(self, message_id):
        found = next((one for one in self.messages if one.id == int(message_id)), None)
        if found is None:
            raise discord.NotFound(SimpleNamespace(status=404, reason="gone"), "gone")
        return found


WORDS = {"sign": "Sign in here", "note": "A note", "wall": "A wall"}


def drawn_kind(key, footprint=(1, 1, 5)):
    def parts(bot, guild, row):
        view = discord.ui.View(timeout=None)
        view.add_item(discord.ui.Button(label=WORDS[key], custom_id=f"{key}:press", row=0))
        return discord.Embed(title=WORDS[key]), view, f"{key}:{WORDS[key]}"

    return post_blocks.BlockKind(
        key=key,
        name_key=f"posts_block_{key}_name",
        name_default=key.title(),
        exclusive=False,
        cache_column="",
        keys=(),
        parts=parts,
        turned=post_blocks.blocks_turned,
        redraw=post_blocks.blocks_redraw,
        footprint=footprint,
    )


@pytest.fixture
def two_kinds(monkeypatch):
    monkeypatch.setitem(WORDS, "sign", "Sign in here")
    monkeypatch.setitem(WORDS, "note", "A note")
    monkeypatch.setitem(post_blocks.KINDS, "sign", drawn_kind("sign"))
    monkeypatch.setitem(post_blocks.KINDS, "note", drawn_kind("note"))
    monkeypatch.setattr(post_blocks, "name_of", lambda store, guild_id, found: found.name_default)
    return ("sign", "note")


ROOM = 444


@pytest.fixture
def room(bot):
    channel = FakeText(ROOM, "welcome-test")
    bot.channels[ROOM] = channel
    return channel


async def a_room_post(bot):
    post_id = await posts.create_post(
        bot.db, GUILD, slug="notice", title="A notice", body="Hello.", channel_id=ROOM
    )
    return await posts.get_post_by_id(bot.db, post_id)


async def carrying_both(bot):
    row = await a_room_post(bot)
    for kind in ("sign", "note"):
        assert await post_blocks.attach(bot.db, row, kind)
    return await posts.get_post_by_id(bot.db, int(row["id"]))


async def fresh_row(bot, row):
    return await posts.get_post_by_id(bot.db, int(row["id"]))


async def test_two_blocks_go_out_in_order_each_with_its_own_row_and_stamp(
    bot, guild, two_kinds, room
):
    row = await carrying_both(bot)

    outcome = await posts.publish_post(bot, guild, row, STAFF)

    assert outcome.ok, outcome.message
    sent = room.messages[0]
    assert sent.content == "Hello."
    assert [one.title for one in sent.embeds] == ["Sign in here", "A note"]
    assert [(one.custom_id, one.row) for one in sent.view.children] == [
        ("sign:press", 0),
        ("note:press", 1),
    ]
    assert await post_blocks.drawn_of(bot.db, int(row["id"])) == {
        "sign": "sign:Sign in here",
        "note": "note:A note",
    }


async def test_one_block_changing_rebuilds_the_whole_message_in_place(
    bot, guild, two_kinds, room
):
    row = await carrying_both(bot)
    await posts.publish_post(bot, guild, row, STAFF)
    message = room.messages[0]
    WORDS["note"] = "A new note"

    assert await post_blocks.redraw_post(bot, guild, await fresh_row(bot, row)) is True

    assert room.messages == [message]
    last = message.edits[-1]
    assert "content" not in last, "the post's own words stay exactly as posted"
    assert [one.title for one in last["embeds"]] == ["Sign in here", "A new note"]
    assert [one.custom_id for one in last["view"].children] == ["sign:press", "note:press"]
    assert (await post_blocks.drawn_of(bot.db, int(row["id"])))["note"] == "note:A new note"
    assert post_blocks.REDRAWN in [kind for kind, _ in await logged(bot.db)]

    assert await post_blocks.redraw_post(bot, guild, await fresh_row(bot, row)) is False
    assert len(message.edits) == 1, "nothing moved since, so nothing is edited"


async def test_an_embed_post_keeps_its_own_card_first_when_redrawn(bot, guild, two_kinds, room):
    row = await carrying_both(bot)
    await posts.set_post_fields(bot.db, int(row["id"]), style=posts.EMBED)
    await posts.publish_post(bot, guild, await fresh_row(bot, row), STAFF)
    message = room.messages[0]
    WORDS["sign"] = "Sign here"

    await post_blocks.redraw_post(bot, guild, await fresh_row(bot, row))

    assert [one.title for one in message.embeds] == ["A notice", "Sign here", "A note"]


async def test_reordering_blocks_redraws_a_message_already_up(bot, guild, two_kinds, room):
    row = await carrying_both(bot)
    await posts.publish_post(bot, guild, row, STAFF)
    message = room.messages[0]

    outcome = await post_blocks.order_blocks(
        bot, guild, await fresh_row(bot, row), STAFF, ["note", "sign"]
    )

    assert outcome.ok and outcome.message.endswith(post_blocks.ORDERED_NOW_SAID)
    assert [one.title for one in message.embeds] == ["A note", "Sign in here"]


async def test_removing_a_block_redraws_the_message_without_it(bot, guild, two_kinds, room):
    row = await carrying_both(bot)
    await posts.publish_post(bot, guild, row, STAFF)
    message = room.messages[0]

    outcome = await post_blocks.remove_block(bot, guild, await fresh_row(bot, row), STAFF, "note")

    assert outcome.ok and outcome.message.endswith(post_blocks.DRAWN_OFF_SAID)
    assert [one.title for one in message.embeds] == ["Sign in here"]
    assert [one.custom_id for one in message.view.children] == ["sign:press"]


async def test_adding_a_block_to_a_post_already_up_draws_it_at_once(bot, guild, two_kinds, room):
    row = await a_room_post(bot)
    await posts.publish_post(bot, guild, row, STAFF)
    message = room.messages[0]

    outcome = await post_blocks.add_block(bot, guild, await fresh_row(bot, row), STAFF, "sign")

    assert outcome.ok and outcome.message.endswith(post_blocks.DRAWN_NOW_SAID)
    assert [one.title for one in message.embeds] == ["Sign in here"]


async def test_adding_a_block_to_a_post_not_up_yet_says_nothing_more(bot, guild, two_kinds):
    row = await a_post(bot)

    outcome = await post_blocks.add_block(bot, guild, row, STAFF, "sign")

    assert outcome.ok and outcome.message == post_blocks.BLOCK_ADDED_SAID.format(
        name="Sign", title="A notice"
    )


async def test_a_block_past_discord_s_caps_is_refused_in_words(bot, guild, two_kinds, monkeypatch):
    monkeypatch.setitem(post_blocks.KINDS, "wall", drawn_kind("wall", footprint=(1, 4, 5)))
    row = await carrying_both(bot)

    outcome = await post_blocks.add_block(bot, guild, row, STAFF, "wall")

    assert not outcome.ok and outcome.code == "block_too_big"
    assert outcome.message == post_blocks.BLOCK_TOO_BIG.format(
        name="Wall", title="A notice", limit="at most 5 rows of buttons", need="6 rows"
    )
    assert await post_blocks.kinds_on(bot.db, int(row["id"])) == ["sign", "note"]


def test_the_caps_are_discord_s_own_and_an_embed_post_counts_its_card():
    assert post_blocks.too_big({"style": posts.PLAIN}, ["frontdoor"]) is None
    assert post_blocks.footprint_of({"style": posts.EMBED}, ["frontdoor"]) == {
        "embeds": 2,
        "rows": 1,
        "components": 3,
    }
    assert (post_blocks.MAX_EMBEDS, post_blocks.MAX_ROWS, post_blocks.MAX_COMPONENTS) == (
        10,
        5,
        25,
    )


async def test_taking_a_post_down_forgets_every_block_s_stamp(bot, guild, two_kinds, room):
    row = await carrying_both(bot)
    await posts.publish_post(bot, guild, row, STAFF)

    await posts.clear_posted(bot.db, int(row["id"]))

    assert await post_blocks.drawn_of(bot.db, int(row["id"])) == {"sign": None, "note": None}


async def test_the_sweep_redraws_a_carrier_the_door_does_not_ride(bot, guild, two_kinds, room):
    row = await carrying_both(bot)
    await posts.publish_post(bot, guild, row, STAFF)
    message = room.messages[0]

    assert await post_blocks.keep_drawn(bot, guild) == 0
    WORDS["sign"] = "Sign in, please"
    assert await post_blocks.keep_drawn(bot, guild) == 1

    assert message.embeds[0].title == "Sign in, please"
