import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import discord
import pytest

from black_bloc import posts
from black_bloc.config import load_settings
from black_bloc.logkinds import VIA_WEBSITE
from black_bloc.settings_store import SettingsStore

GUILD = 7
TEST_CHANNEL = 111
LOG_CHANNEL = 333
WELCOME_CHANNEL = 222
GONE_CHANNEL = 444
STAFF = SimpleNamespace(id=42, guild_permissions=SimpleNamespace(mention_everyone=False))
LEAD = SimpleNamespace(id=43, guild_permissions=SimpleNamespace(mention_everyone=True))


class Refused(discord.HTTPException):
    def __init__(self, text="Missing Permissions"):
        super().__init__(SimpleNamespace(status=403, reason=text), text)


class FakeMessage:
    def __init__(self, channel, message_id, **kwargs):
        self.channel = channel
        self.id = message_id
        self.kwargs = dict(kwargs)
        self.pinned = False
        self.edits = []
        self.deleted = False
        self.edit_raises = None
        self.pin_raises = None

    async def edit(self, **kwargs):
        if self.edit_raises is not None:
            raise self.edit_raises
        self.edits.append(dict(kwargs))
        self.kwargs |= kwargs

    async def pin(self, reason=None):
        if self.pin_raises is not None:
            raise self.pin_raises
        self.pinned = True

    async def delete(self):
        self.deleted = True
        self.channel.messages.pop(self.id, None)


class FakeChannel:
    """Message ids never repeat across channels, the way a snowflake does not: a shadow copy
    is hunted BY ID through the channels it could be in, and a collision would find the
    wrong message."""

    def __init__(self, channel_id, name, first_id=9000):
        self.id = channel_id
        self.name = name
        self.sent = []
        self.messages = {}
        self.next_id = first_id
        self.send_raises = None
        self.fetch_raises = None

    async def send(self, **kwargs):
        if self.send_raises is not None:
            raise self.send_raises
        self.next_id += 1
        self.sent.append(dict(kwargs))
        message = FakeMessage(self, self.next_id, **kwargs)
        self.messages[message.id] = message
        return message

    async def fetch_message(self, message_id):
        if self.fetch_raises is not None:
            raise self.fetch_raises
        found = self.messages.get(int(message_id))
        if found is None:
            raise discord.NotFound(SimpleNamespace(status=404, reason="Not Found"), "gone")
        return found


class FakeRole:
    def __init__(self, role_id, name, mentionable=False):
        self.id = role_id
        self.name = name
        self.mentionable = mentionable


class FakeGuild:
    def __init__(self, bot, guild_id=GUILD):
        self.id = guild_id
        self.bot = bot
        self.unavailable = False
        self.roles = [FakeRole(900, "Aunties / Uncles"), FakeRole(901, "Live now", True)]

    def get_channel(self, channel_id):
        return self.bot.channels.get(int(channel_id))

    def get_role(self, role_id):
        return next((one for one in self.roles if one.id == int(role_id)), None)

    def get_member(self, user_id):
        return None


class FakeGuard:
    def __init__(self, allowed=TEST_CHANNEL, test_channel_id=TEST_CHANNEL):
        self.allowed = allowed
        self.test_channel_id = test_channel_id

    def allows_channel(self, channel_id):
        return int(channel_id or 0) == self.allowed

    def refusal_message(self):
        return "Black Bloc is in **test mode**."


class FakeBot:
    def __init__(self, db, store, settings):
        self.db = db
        self.store = store
        self.settings = settings
        self.guard = None
        self.channels = {
            TEST_CHANNEL: FakeChannel(TEST_CHANNEL, "blackbloc-logs"),
            WELCOME_CHANNEL: FakeChannel(WELCOME_CHANNEL, "welcome", first_id=8000),
            # The log channel is its own, so a `post.posted` EMBED never lands in the count
            # of what the post itself sent.
            LOG_CHANNEL: FakeChannel(LOG_CHANNEL, "bot-log", first_id=7000),
        }
        self.guilds = [FakeGuild(self)]

    def get_channel(self, channel_id):
        return self.channels.get(int(channel_id))

    def get_guild(self, guild_id):
        return self.guilds[0] if int(guild_id) == GUILD else None


@pytest.fixture
async def bot(db, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    settings = load_settings(_env_file=None, test_mode=True, test_channel_id=TEST_CHANNEL)
    store = SettingsStore(db, settings)
    await store.load()
    await store.set(GUILD, "log_channel_id", LOG_CHANNEL)
    await store.set(GUILD, posts.MODE_KEY, "on")
    return FakeBot(db, store, settings)


@pytest.fixture
def guild(bot):
    return bot.guilds[0]


async def logged(db):
    cur = await db.conn.execute("SELECT kind, actor_id, details FROM action_log ORDER BY id")
    return [dict(row) for row in await cur.fetchall()]


async def kinds(db):
    return [row["kind"] for row in await logged(db)]


async def details_of(db, kind):
    for row in await logged(db):
        if row["kind"] == kind:
            return json.loads(row["details"] or "{}")
    return None


async def a_post(bot, guild, *, slug="notice", body="Hello.", channel_id=TEST_CHANNEL, **fields):
    post_id = await posts.create_post(
        bot.db, guild.id, slug=slug, title="A notice", body=body, channel_id=channel_id, **fields
    )
    return await posts.get_post_by_id(bot.db, post_id)


# --- the seed ---------------------------------------------------------------------------------


def test_the_seed_is_carls_welcome_text_byte_for_byte():
    """§C6 is the archive's capture. A deploy that rewraps it would change what members read."""
    entries = posts.seed_entries()
    assert len(entries) == 1
    one = entries[0]
    assert one["slug"] == "welcome"
    assert one["title"] == "Welcome and rules"
    assert one["style"] == posts.PLAIN and one["pin"] is True
    assert one["channel_id"] == "1285369365071527997"
    body = one["body"]
    assert body.startswith("Welcome to** Black in a Flash**, a dedicated space for Black gamers!  ")
    assert "\n# Familiarize yourselves with the rules before you join the discord.\n" in body
    assert body.count("\n> ") == 3
    assert body.count("***") == 6
    assert body.endswith("you are welcome to ping the Aunties / Uncles role.")
    assert "\r" not in body
    assert len(body) == 1461
    assert len(body) <= posts.CAPS[posts.PLAIN]


async def test_seeding_resolves_the_channel_against_this_guild(bot, guild, monkeypatch):
    monkeypatch.setitem(
        bot.channels, 1285369365071527997, FakeChannel(1285369365071527997, "welcome")
    )

    made = await posts.seed_posts(bot, guild)

    assert made == 1
    row = await posts.get_post(bot.db, guild.id, "welcome")
    assert row["channel_id"] == 1285369365071527997
    assert row["body"] == posts.seed_entries()[0]["body"]
    assert row["message_id"] is None, "the seed never posts; posting is a person's press"
    assert posts.is_seeded(row)
    assert "post.seed_channel_unknown" not in await kinds(bot.db)


async def test_a_channel_this_guild_does_not_have_is_left_unset_and_written_down(bot, guild):
    made = await posts.seed_posts(bot, guild)

    assert made == 1
    row = await posts.get_post(bot.db, guild.id, "welcome")
    assert row["channel_id"] is None
    assert "post.seed_channel_unknown" in await kinds(bot.db)
    said = await details_of(bot.db, "post.seed_channel_unknown")
    assert said["channel_id"] == "1285369365071527997"


async def test_seeding_twice_makes_nothing_and_never_overwrites_a_staff_edit(bot, guild):
    await posts.seed_posts(bot, guild)
    row = await posts.get_post(bot.db, guild.id, "welcome")
    await posts.save_post(bot, guild, row, STAFF, body="Staff wrote this.")

    assert await posts.seed_posts(bot, guild) == 0
    fresh = await posts.get_post(bot.db, guild.id, "welcome")
    assert fresh["body"] == "Staff wrote this."


# --- the versions ------------------------------------------------------------------------------


async def versions(bot, row):
    return await posts.list_versions(bot.db, int(row["id"]))


async def test_a_save_that_changes_something_writes_a_version_and_one_that_does_not_writes_none(
    bot, guild
):
    row = await a_post(bot, guild)

    await posts.save_post(bot, guild, row, STAFF, body="First words.")
    row = await posts.get_post(bot.db, guild.id, "notice")
    await posts.save_post(bot, guild, row, STAFF, body="First words.")
    row = await posts.get_post(bot.db, guild.id, "notice")
    await posts.save_post(bot, guild, row, STAFF, body="Second words.")

    found = await versions(bot, row)
    assert [int(one["n"]) for one in found] == [2, 1]
    assert [one["body"] for one in found] == ["Second words.", "First words."]
    assert {one["because"] for one in found} == {posts.BECAUSE_SAVED}
    assert [one["saved_by"] for one in found] == [STAFF.id, STAFF.id]


async def test_the_saved_row_names_the_version_the_post_now_reads_as(bot, guild):
    row = await a_post(bot, guild)

    await posts.save_post(bot, guild, row, STAFF, body="First words.")
    row = await posts.get_post(bot.db, guild.id, "notice")
    await posts.save_post(bot, guild, row, STAFF, body="First words.")

    said = [
        json.loads(one["details"] or "{}")
        for one in await logged(bot.db)
        if one["kind"] == "post.saved"
    ]
    assert [one["version"] for one in said] == [1, 1], "a save that changed nothing keeps its n"


async def test_a_publish_writes_a_version_only_when_the_row_has_moved_since_the_last_one(
    bot, guild
):
    row = await a_post(bot, guild)
    await posts.save_post(bot, guild, row, STAFF, body="What goes out.")
    row = await posts.get_post(bot.db, guild.id, "notice")

    await posts.publish_post(bot, guild, row, STAFF)
    row = await posts.get_post(bot.db, guild.id, "notice")
    await posts.publish_post(bot, guild, row, STAFF)

    assert [int(one["n"]) for one in await versions(bot, row)] == [1]


async def test_a_row_edited_without_a_version_gets_one_when_it_is_posted(bot, guild):
    row = await a_post(bot, guild, body="Written before versions existed.")

    found = await posts.publish_post(bot, guild, row, STAFF)

    assert found.ok
    made = await versions(bot, row)
    assert [one["because"] for one in made] == [posts.BECAUSE_POSTED]
    assert made[0]["body"] == "Written before versions existed."
    said = await details_of(bot.db, "post.posted")
    assert said["version"] == 1


async def test_use_this_version_writes_a_version_of_its_own_so_nothing_is_lost(bot, guild):
    row = await a_post(bot, guild)
    await posts.save_post(bot, guild, row, STAFF, body="The first.")
    row = await posts.get_post(bot.db, guild.id, "notice")
    await posts.save_post(bot, guild, row, STAFF, body="The second.")
    row = await posts.get_post(bot.db, guild.id, "notice")

    found = await posts.restore_version(bot, guild, row, LEAD, 1)

    assert found.ok
    fresh = await posts.get_post(bot.db, guild.id, "notice")
    assert fresh["body"] == "The first."
    made = await versions(bot, fresh)
    assert [int(one["n"]) for one in made] == [3, 2, 1]
    assert made[0]["because"] == "restored:1" and made[0]["body"] == "The first."
    assert made[1]["body"] == "The second.", "what it said a moment ago is still here"
    said = await details_of(bot.db, "post.restored")
    assert said["from_version"] == 1 and said["new_version"] == 3


async def test_restoring_the_version_the_post_already_says_is_refused_in_words(bot, guild):
    row = await a_post(bot, guild)
    await posts.save_post(bot, guild, row, STAFF, body="The only one.")
    row = await posts.get_post(bot.db, guild.id, "notice")

    found = await posts.restore_version(bot, guild, row, STAFF, 1)

    assert not found.ok and found.code == "version_is_current"
    assert "Version 1 is already what the post says" in found.message
    assert "post.restored" not in await kinds(bot.db)


async def test_a_version_that_was_never_written_is_refused_in_words(bot, guild):
    row = await a_post(bot, guild)

    found = await posts.restore_version(bot, guild, row, STAFF, 9)

    assert not found.ok and found.code == "no_such_version"
    assert "There is no version 9 of **A notice**" in found.message


async def test_the_keep_limit_trims_the_oldest_and_never_the_last_one_standing(bot, guild):
    await bot.store.set(GUILD, posts.VERSIONS_KEEP_KEY, 2)
    row = await a_post(bot, guild)
    for word in ("one", "two", "three", "four"):
        await posts.save_post(bot, guild, row, STAFF, body=word)
        row = await posts.get_post(bot.db, guild.id, "notice")

    found = await versions(bot, row)
    assert [int(one["n"]) for one in found] == [4, 3]
    assert "post.versions_trimmed" in await kinds(bot.db)
    said = await details_of(bot.db, "post.versions_trimmed")
    assert said["versions"] == [1] and said["kept"] == 3

    await bot.store.set(GUILD, posts.VERSIONS_KEEP_KEY, 1)
    await posts.save_post(bot, guild, row, STAFF, body="five")
    left = await versions(bot, row)
    assert [int(one["n"]) for one in left] == [5]


async def test_zero_keeps_every_version(bot, guild):
    await bot.store.set(GUILD, posts.VERSIONS_KEEP_KEY, 0)
    row = await a_post(bot, guild)
    for word in ("one", "two", "three"):
        await posts.save_post(bot, guild, row, STAFF, body=word)
        row = await posts.get_post(bot.db, guild.id, "notice")

    assert [int(one["n"]) for one in await versions(bot, row)] == [3, 2, 1]


async def test_deleting_a_post_takes_its_versions_with_it(bot, guild):
    row = await a_post(bot, guild, seed_hash=None)
    await posts.save_post(bot, guild, row, STAFF, body="Something.")
    row = await posts.get_post(bot.db, guild.id, "notice")

    await posts.remove_post(bot, guild, row, STAFF)

    cur = await bot.db.conn.execute("SELECT COUNT(*) AS n FROM post_versions")
    assert (await cur.fetchone())["n"] == 0


def test_a_version_because_reads_as_words_a_person_understands():
    assert posts.because_words(posts.BECAUSE_SAVED) == "saved"
    assert posts.because_words(posts.BECAUSE_POSTED) == "posted"
    assert posts.because_words("restored:3") == "restored from 3"
    assert posts.because_words(posts.BECAUSE_BACKFILL) == "what it said before"


def test_a_versions_summary_is_one_line_however_the_message_is_written():
    row = {"body": "A line\n\n> and a quote\nand more"}
    assert posts.summary_of(row, 80) == "A line > and a quote and more"
    assert posts.summary_of(row, 10) == "A line > a…"


def test_when_words_are_what_a_select_option_can_carry():
    at = datetime(2026, 9, 20, 12, 0, tzinfo=UTC)
    assert posts.when_words((at - timedelta(days=2)).isoformat(), at=at) == "2 days ago"
    assert posts.when_words((at - timedelta(hours=1)).isoformat(), at=at) == "1 hour ago"
    assert posts.when_words((at - timedelta(seconds=5)).isoformat(), at=at) == "just now"
    assert posts.when_words("not a time") == "just now"


async def test_the_seed_hash_is_refreshed_without_touching_the_words(bot, guild):
    await posts.seed_posts(bot, guild)
    await bot.db.conn.execute("UPDATE posts SET seed_hash = 'old'")
    await bot.db.conn.commit()

    assert await posts.refresh_seeds(bot.db, guild.id) == 1
    row = await posts.get_post(bot.db, guild.id, "welcome")
    assert row["seed_hash"] == posts.seed_hash(posts.seed_entries()[0])
    assert row["body"] == posts.seed_entries()[0]["body"]
    assert await posts.refresh_seeds(bot.db, guild.id) == 0


# --- the caps ---------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "style,cap", [(posts.PLAIN, 2000), (posts.EMBED, 4096)]
)
async def test_over_the_cap_is_refused_in_words_that_name_the_count(bot, guild, style, cap):
    row = await a_post(bot, guild, style=style)

    found = await posts.save_post(bot, guild, row, STAFF, body="x" * (cap + 7))

    assert not found.ok and found.code == "body_too_long"
    assert str(cap + 7) in found.message
    assert str(cap) in found.message
    assert "7 characters out" in found.message
    assert "nothing was saved" in found.message
    fresh = await posts.get_post_by_id(bot.db, int(row["id"]))
    assert fresh["body"] == "Hello.", "a refused save changes nothing"


async def test_the_plain_refusal_offers_the_bigger_style_and_the_embed_one_does_not(bot, guild):
    plain = await a_post(bot, guild, slug="one", style=posts.PLAIN)
    embed = await a_post(bot, guild, slug="two", style=posts.EMBED)

    said_plain = (await posts.save_post(bot, guild, plain, STAFF, body="x" * 2001)).message
    said_embed = (await posts.save_post(bot, guild, embed, STAFF, body="x" * 4097)).message

    assert "set the style to an embed" in said_plain
    assert "set the style to an embed" not in said_embed


async def test_an_over_long_embed_title_is_refused_and_a_plain_one_is_not(bot, guild):
    row = await a_post(bot, guild, style=posts.EMBED)

    found = await posts.save_post(bot, guild, row, STAFF, title="t" * 300)

    assert not found.ok and found.code == "title_too_long"
    assert "256" in found.message
    assert "set the style back to a plain message" in found.message
    plain = await a_post(bot, guild, slug="plain", style=posts.PLAIN)
    same = await posts.save_post(bot, guild, plain, STAFF, title="t" * 300)
    assert not same.ok and same.code == "title_too_long"
    assert "set the style back" not in same.message, "a plain post has no bigger style to offer"
    assert (await posts.save_post(bot, guild, plain, STAFF, title="t" * 256)).ok


async def test_the_cap_is_checked_again_at_post_time(bot, guild):
    """The `/posts` modal holds 4000, which is over the plain cap, so save is not the only gate."""
    row = await a_post(bot, guild)
    await bot.db.conn.execute("UPDATE posts SET body = ? WHERE id = ?", ("x" * 2500, row["id"]))
    await bot.db.conn.commit()
    row = await posts.get_post_by_id(bot.db, int(row["id"]))

    found = await posts.publish_post(bot, guild, row, STAFF)

    assert not found.ok and found.code == "body_too_long"
    assert "2500" in found.message and "nothing was posted" in found.message
    assert bot.channels[TEST_CHANNEL].sent == []


async def test_an_unknown_channel_is_refused_in_words(bot, guild):
    row = await a_post(bot, guild)

    found = await posts.save_post(bot, guild, row, STAFF, channel_id=GONE_CHANNEL)

    assert not found.ok and found.code == "unknown_channel"
    assert str(GONE_CHANNEL) in found.message


# --- posting ----------------------------------------------------------------------------------


async def test_the_guard_turns_a_post_into_a_would_post_and_sends_nothing(bot, guild):
    bot.guard = FakeGuard()
    row = await a_post(bot, guild, channel_id=WELCOME_CHANNEL)

    found = await posts.publish_post(bot, guild, row, STAFF)

    assert not found.ok and found.code == "test_mode" and found.status == 409
    assert found.message == bot.guard.refusal_message()
    assert bot.channels[WELCOME_CHANNEL].sent == []
    assert await kinds(bot.db) == ["post.would_post"]
    said = await details_of(bot.db, "post.would_post")
    assert said["channel"] == "#welcome"
    fresh = await posts.get_post_by_id(bot.db, int(row["id"]))
    assert fresh["message_id"] is None


async def test_the_first_press_sends_once_and_the_second_edits_and_never_sends_again(bot, guild):
    bot.guard = FakeGuard()
    channel = bot.channels[TEST_CHANNEL]
    row = await a_post(bot, guild)

    first = await posts.publish_post(bot, guild, row, STAFF)
    assert first.ok and len(channel.sent) == 1
    assert "#blackbloc-logs" in first.message
    posted = await posts.get_post_by_id(bot.db, int(row["id"]))
    assert posted["message_id"] == 9001
    assert posts.changes_pending(posted) is False

    await posts.save_post(bot, guild, posted, STAFF, body="Changed.")
    changed = await posts.get_post_by_id(bot.db, int(row["id"]))
    assert posts.changes_pending(changed) is True

    second = await posts.publish_post(bot, guild, changed, STAFF)

    assert second.ok
    assert len(channel.sent) == 1, "a second press must never leave a second copy"
    message = channel.messages[9001]
    assert message.edits and message.edits[-1]["content"] == "Changed."
    assert await kinds(bot.db) == [
        "post.posted",
        "post.pinned",
        "post.saved",
        "post.updated",
    ]
    assert posts.changes_pending(await posts.get_post_by_id(bot.db, int(row["id"]))) is False


async def test_a_message_somebody_deleted_is_written_down_and_then_sent_again(bot, guild):
    bot.guard = FakeGuard()
    channel = bot.channels[TEST_CHANNEL]
    row = await a_post(bot, guild, pin=False)
    await posts.publish_post(bot, guild, row, STAFF)
    channel.messages.clear()
    row = await posts.get_post_by_id(bot.db, int(row["id"]))

    found = await posts.publish_post(bot, guild, row, STAFF)

    assert found.ok
    assert await kinds(bot.db) == ["post.posted", "post.message_gone", "post.posted"]
    assert len(channel.sent) == 2
    fresh = await posts.get_post_by_id(bot.db, int(row["id"]))
    assert fresh["message_id"] == 9002


async def test_a_pin_that_fails_never_takes_the_post_with_it(bot, guild):
    """Checklist 12: the row and its log line are written before the cosmetics are tried."""
    bot.guard = FakeGuard()
    channel = bot.channels[TEST_CHANNEL]

    async def send(**kwargs):
        channel.next_id += 1
        channel.sent.append(dict(kwargs))
        message = FakeMessage(channel, channel.next_id, **kwargs)
        message.pin_raises = Refused("Missing Permissions")
        channel.messages[message.id] = message
        return message

    channel.send = send
    row = await a_post(bot, guild)

    found = await posts.publish_post(bot, guild, row, STAFF)

    assert found.ok
    assert await kinds(bot.db) == ["post.posted", "post.pin_failed"]
    fresh = await posts.get_post_by_id(bot.db, int(row["id"]))
    assert fresh["message_id"] == 9001 and fresh["posted_hash"]


async def test_discord_refusing_the_send_leaves_the_row_untouched(bot, guild):
    bot.guard = FakeGuard()
    bot.channels[TEST_CHANNEL].send_raises = Refused("Missing Access")
    row = await a_post(bot, guild)

    found = await posts.publish_post(bot, guild, row, STAFF)

    assert not found.ok and found.code == "post_failed"
    assert "Missing Access" in found.message
    assert await kinds(bot.db) == ["post.post_failed"]
    fresh = await posts.get_post_by_id(bot.db, int(row["id"]))
    assert fresh["message_id"] is None


async def test_a_post_with_no_channel_and_a_post_with_no_words_each_refuse_in_words(bot, guild):
    empty = await a_post(bot, guild, slug="nowhere", channel_id=None)
    blank = await a_post(bot, guild, slug="blank", body="   ")

    no_channel = await posts.publish_post(bot, guild, empty, STAFF)
    nothing = await posts.publish_post(bot, guild, blank, STAFF)

    assert no_channel.code == "no_channel" and "**Channel**" in no_channel.message
    assert nothing.code == "nothing_to_post" and "Write the message" in nothing.message
    assert await kinds(bot.db) == []


# --- allowed mentions -------------------------------------------------------------------------


async def test_nothing_pings_unless_the_actor_may_ping_that_role(bot, guild):
    """Checklist 11: a staffer without Mention Everyone can only ping a mentionable role."""
    body = "Ping <@&900> and <@&901> and @everyone"

    quiet = posts.allowed_mentions_for(guild, body, STAFF)
    loud = posts.allowed_mentions_for(guild, body, LEAD)

    assert quiet.everyone is False and quiet.users is False
    assert [one.id for one in quiet.roles] == [901]
    assert [one.id for one in loud.roles] == [900, 901]
    assert loud.everyone is False


async def test_the_send_carries_the_allowed_mentions(bot, guild):
    bot.guard = FakeGuard()
    row = await a_post(bot, guild, body="Hello <@&900>")

    await posts.publish_post(bot, guild, row, STAFF)

    sent = bot.channels[TEST_CHANNEL].sent[0]
    assert sent["allowed_mentions"].roles == []
    assert sent["allowed_mentions"].everyone is False


# --- taking it down ---------------------------------------------------------------------------


async def test_taking_it_down_deletes_the_message_and_keeps_every_word(bot, guild):
    bot.guard = FakeGuard()
    row = await a_post(bot, guild)
    await posts.publish_post(bot, guild, row, STAFF)
    row = await posts.get_post_by_id(bot.db, int(row["id"]))

    found = await posts.take_down_post(bot, guild, row, STAFF)

    assert found.ok
    assert bot.channels[TEST_CHANNEL].messages == {}
    fresh = await posts.get_post_by_id(bot.db, int(row["id"]))
    assert fresh["message_id"] is None and fresh["posted_hash"] is None
    assert fresh["body"] == "Hello."
    assert "post.taken_down" in await kinds(bot.db)


async def test_the_guard_turns_a_take_down_into_a_would_take_down(bot, guild):
    row = await a_post(bot, guild, channel_id=WELCOME_CHANNEL)
    bot.guard = None
    await posts.publish_post(bot, guild, row, STAFF)
    bot.guard = FakeGuard()
    row = await posts.get_post_by_id(bot.db, int(row["id"]))

    found = await posts.take_down_post(bot, guild, row, STAFF)

    assert not found.ok and found.code == "test_mode"
    assert bot.channels[WELCOME_CHANNEL].messages
    assert "post.would_take_down" in await kinds(bot.db)


async def test_a_post_that_is_not_posted_has_nothing_to_take_down(bot, guild):
    row = await a_post(bot, guild)

    found = await posts.take_down_post(bot, guild, row, STAFF)

    assert not found.ok and found.code == "not_posted"
    assert "Press Post it first" in found.message


# --- making and deleting ----------------------------------------------------------------------


async def test_a_new_post_is_empty_and_never_posted(bot, guild):
    found = await posts.make_post(bot, guild, STAFF, title="When staff are around")

    assert found.ok
    row = await posts.get_post(bot.db, guild.id, "when-staff-are-around")
    assert row["body"] == "" and row["message_id"] is None and row["seed_hash"] is None
    assert row["style"] == posts.PLAIN and row["pin"] == 1
    assert await kinds(bot.db) == ["post.created"]


async def test_two_posts_cannot_share_a_slug_and_a_title_with_no_letters_is_refused(bot, guild):
    await posts.make_post(bot, guild, STAFF, title="Rules")

    taken = await posts.make_post(bot, guild, STAFF, title="Rules")
    empty = await posts.make_post(bot, guild, STAFF, title="!!!")
    blank = await posts.make_post(bot, guild, STAFF, title="   ")

    assert taken.code == "slug_taken" and "**rules**" in taken.message
    assert empty.code == "no_slug"
    assert blank.code == "no_title"


async def test_the_shipped_post_cannot_be_deleted_and_a_posted_one_is_taken_down_first(bot, guild):
    bot.guard = FakeGuard()
    await posts.seed_posts(bot, guild)
    seeded = await posts.get_post(bot.db, guild.id, "welcome")
    mine = await a_post(bot, guild, slug="mine")
    await posts.publish_post(bot, guild, mine, STAFF)
    mine = await posts.get_post_by_id(bot.db, int(mine["id"]))

    shipped = await posts.remove_post(bot, guild, seeded, STAFF)
    posted = await posts.remove_post(bot, guild, mine, STAFF)

    assert shipped.code == "seeded_post" and "Take it down" in shipped.message
    assert posted.code == "still_posted" and "Take it down" in posted.message
    assert await posts.count_posts(bot.db, guild.id) == 2


async def test_an_unposted_post_staff_wrote_here_is_deleted(bot, guild):
    row = await a_post(bot, guild)

    found = await posts.remove_post(bot, guild, row, STAFF)

    assert found.ok
    assert await posts.get_post(bot.db, guild.id, "notice") is None
    assert "post.deleted" in await kinds(bot.db)


# --- the reconcile sweep ----------------------------------------------------------------------


async def test_the_sweep_forgets_a_message_somebody_deleted_by_hand(bot, guild):
    bot.guard = FakeGuard()
    row = await a_post(bot, guild)
    await posts.publish_post(bot, guild, row, STAFF)
    bot.channels[TEST_CHANNEL].messages.clear()

    done = await posts.reconcile_posts(bot)

    assert done["gone"] == 1
    fresh = await posts.get_post_by_id(bot.db, int(row["id"]))
    assert fresh["message_id"] is None
    assert "post.message_gone" in await kinds(bot.db)


async def test_the_sweep_puts_a_pin_back_and_leaves_an_unpinned_post_alone(bot, guild):
    bot.guard = FakeGuard()
    pinned = await a_post(bot, guild, slug="pinned")
    loose = await a_post(bot, guild, slug="loose", pin=False)
    await posts.publish_post(bot, guild, pinned, STAFF)
    await posts.publish_post(bot, guild, loose, STAFF)
    bot.channels[TEST_CHANNEL].messages[9001].pinned = False

    done = await posts.reconcile_posts(bot)

    assert done["pinned"] == 1
    assert bot.channels[TEST_CHANNEL].messages[9001].pinned is True
    assert bot.channels[TEST_CHANNEL].messages[9002].pinned is False


async def test_the_sweep_skips_a_guild_discord_has_not_handed_over(bot, guild):
    """Checklist 32: an unavailable guild is not evidence that a message is gone."""
    bot.guard = FakeGuard()
    row = await a_post(bot, guild)
    await posts.publish_post(bot, guild, row, STAFF)
    bot.channels[TEST_CHANNEL].messages.clear()
    guild.unavailable = True

    done = await posts.reconcile_posts(bot)

    assert done == {"gone": 0, "pinned": 0}
    assert (await posts.get_post_by_id(bot.db, int(row["id"])))["message_id"] == 9001


async def test_the_sweep_does_nothing_at_all_without_a_database(bot):
    bot.db = SimpleNamespace(is_connected=False)

    assert await posts.reconcile_posts(bot) == {"gone": 0, "pinned": 0}


# --- the shapes both doors read ----------------------------------------------------------------


def test_render_message_is_one_function_and_always_clears_the_other_key():
    """An edit from an embed back to a plain message has to take the embed away with it."""
    plain = posts.render_message({"style": "plain", "title": "T", "body": "hello"})
    embed = posts.render_message({"style": "embed", "title": "T", "body": "hello"})

    assert plain == {"content": "hello", "embed": None}
    assert embed["content"] is None
    assert embed["embed"].title == "T" and embed["embed"].description == "hello"


def test_the_hash_moves_with_the_style_the_title_and_the_body():
    one = posts.body_hash("plain", "T", "b")
    assert one == posts.body_hash("plain", "T", "b")
    assert one != posts.body_hash("embed", "T", "b")
    assert one != posts.body_hash("plain", "U", "b")
    assert one != posts.body_hash("plain", "T", "c")


def test_the_label_on_the_button_is_the_move_it_makes():
    assert posts.move_label({"message_id": None}) == "Post it"
    assert posts.move_label({"message_id": 5}) == "Update the post"


def test_the_status_words_have_one_spelling():
    assert posts.status_words({"message_id": None, "pin": 1}) == ["not posted"]
    row = {"message_id": 5, "pin": 1, "style": "plain", "title": "T", "body": "b"}
    assert posts.status_words(row | {"posted_hash": posts.body_hash("plain", "T", "b")}) == [
        "posted",
        "pinned",
    ]
    assert posts.status_words(row | {"posted_hash": "stale"})[-1] == "changes not yet posted"


def test_a_slug_is_made_of_the_title():
    assert posts.slugify("Welcome and rules") == "welcome-and-rules"
    assert posts.slugify("It’s here!") == "its-here"
    assert posts.slugify("###") == ""


async def test_a_website_write_carries_via_and_the_web_head(bot, guild):
    row = await a_post(bot, guild)

    await posts.save_post(bot, guild, row, STAFF, body="From the site.", via=VIA_WEBSITE)

    rows = await logged(bot.db)
    assert [one["kind"] for one in rows] == ["web.post.saved"]
    assert json.loads(rows[0]["details"])["via"] == VIA_WEBSITE


# --- shadow (§C7, §C9) ------------------------------------------------------------------------


async def shadow_post(bot, guild, **fields):
    """A post aimed at #welcome, in shadow, which is the shape the cutover actually has."""
    await bot.store.set(GUILD, posts.MODE_KEY, posts.SHADOW)
    bot.guard = FakeGuard()
    return await a_post(bot, guild, channel_id=WELCOME_CHANNEL, **fields)


async def test_shadow_sends_to_the_shadow_channel_and_never_to_the_rows_own(bot, guild):
    """The owner's whole ask: the test work goes to #blackbloc-logs until we are ready."""
    row = await shadow_post(bot, guild)

    found = await posts.publish_post(bot, guild, row, STAFF)

    assert found.ok
    assert bot.channels[WELCOME_CHANNEL].sent == []
    assert len(bot.channels[TEST_CHANNEL].sent) == 1
    assert "#blackbloc-logs" in found.message and "shadow copy" in found.message
    fresh = await posts.get_post_by_id(bot.db, int(row["id"]))
    assert fresh["message_id"] is None
    assert fresh["shadow_message_id"] == 9001
    assert posts.posted_where(fresh) == posts.SHADOW
    assert posts.status_words(fresh)[0] == posts.STATUS_POSTED_SHADOW
    assert posts.changes_pending(fresh) is False
    assert await kinds(bot.db) == ["post.shadow_posted", "post.pinned"]


async def test_a_second_shadow_press_edits_the_copy_and_never_sends_again(bot, guild):
    row = await shadow_post(bot, guild)
    await posts.publish_post(bot, guild, row, STAFF)
    row = await posts.get_post_by_id(bot.db, int(row["id"]))
    await posts.save_post(bot, guild, row, STAFF, body="Changed.")
    changed = await posts.get_post_by_id(bot.db, int(row["id"]))
    assert posts.changes_pending(changed) is True

    found = await posts.publish_post(bot, guild, changed, STAFF)

    assert found.ok and "is updated in #blackbloc-logs" in found.message
    assert len(bot.channels[TEST_CHANNEL].sent) == 1, "shadow keeps ONE copy, edited in place"
    assert bot.channels[TEST_CHANNEL].messages[9001].edits[-1]["content"] == "Changed."
    fresh = await posts.get_post_by_id(bot.db, int(row["id"]))
    assert fresh["shadow_message_id"] == 9001 and posts.changes_pending(fresh) is False
    assert await kinds(bot.db) == [
        "post.shadow_posted",
        "post.pinned",
        "post.saved",
        "post.shadow_updated",
    ]


async def test_the_flip_to_on_posts_for_real_and_takes_the_shadow_copy_down(bot, guild):
    """The go-live. §C9: the next Post it reaches #welcome and the rehearsal is removed."""
    row = await shadow_post(bot, guild)
    await posts.publish_post(bot, guild, row, STAFF)
    await bot.store.set(GUILD, posts.MODE_KEY, posts.ON)
    bot.guard = None
    row = await posts.get_post_by_id(bot.db, int(row["id"]))

    found = await posts.publish_post(bot, guild, row, STAFF)

    assert found.ok and "#welcome" in found.message
    assert len(bot.channels[WELCOME_CHANNEL].sent) == 1
    assert bot.channels[TEST_CHANNEL].messages == {}, "the rehearsal is gone"
    fresh = await posts.get_post_by_id(bot.db, int(row["id"]))
    assert fresh["message_id"] and fresh["shadow_message_id"] is None
    assert posts.posted_where(fresh) == posts.CHANNEL
    assert "post.shadow_taken_down" in await kinds(bot.db)


async def test_a_shadow_copy_that_will_not_delete_never_takes_the_real_post_with_it(bot, guild):
    """Checklist 12: the real message is up and written down before the cosmetics are tried."""
    row = await shadow_post(bot, guild)
    await posts.publish_post(bot, guild, row, STAFF)
    await bot.store.set(GUILD, posts.MODE_KEY, posts.ON)
    bot.guard = None
    bot.channels[TEST_CHANNEL].messages[9001].delete = _refuses
    row = await posts.get_post_by_id(bot.db, int(row["id"]))

    found = await posts.publish_post(bot, guild, row, STAFF)

    assert found.ok
    fresh = await posts.get_post_by_id(bot.db, int(row["id"]))
    assert fresh["message_id"], "the real post stands"
    assert fresh["shadow_message_id"] == 9001, "the id is kept, so the next press tries again"
    said = await kinds(bot.db)
    assert "post.post_failed" in said and "post.shadow_taken_down" not in said


async def _refuses():
    raise Refused("Missing Permissions")


async def test_a_shadow_copy_somebody_deleted_is_written_down_and_sent_again(bot, guild):
    row = await shadow_post(bot, guild, pin=False)
    await posts.publish_post(bot, guild, row, STAFF)
    bot.channels[TEST_CHANNEL].messages.clear()
    row = await posts.get_post_by_id(bot.db, int(row["id"]))

    found = await posts.publish_post(bot, guild, row, STAFF)

    assert found.ok
    assert await kinds(bot.db) == [
        "post.shadow_posted",
        "post.shadow_message_gone",
        "post.shadow_posted",
    ]
    fresh = await posts.get_post_by_id(bot.db, int(row["id"]))
    assert fresh["shadow_message_id"] == 9002


async def test_posts_off_refuses_the_publish_in_words_and_sends_nothing(bot, guild):
    await bot.store.set(GUILD, posts.MODE_KEY, posts.OFF)
    bot.guard = FakeGuard()
    row = await a_post(bot, guild)

    found = await posts.publish_post(bot, guild, row, STAFF)

    assert not found.ok and found.code == "posts_off" and found.status == 409
    assert "Settings page" in found.message
    assert bot.channels[TEST_CHANNEL].sent == []
    assert await kinds(bot.db) == []


async def test_taking_it_down_removes_both_copies_and_clears_both_ids(bot, guild):
    row = await shadow_post(bot, guild)
    await posts.publish_post(bot, guild, row, STAFF)
    await bot.store.set(GUILD, posts.MODE_KEY, posts.ON)
    bot.guard = None
    row = await posts.get_post_by_id(bot.db, int(row["id"]))
    # Put a shadow copy back beside the real one, which is what a mode flip back and forth
    # leaves behind.
    await posts.publish_post(bot, guild, row, STAFF)
    await bot.store.set(GUILD, posts.MODE_KEY, posts.SHADOW)
    row = await posts.get_post_by_id(bot.db, int(row["id"]))
    await posts.publish_post(bot, guild, row, STAFF)
    row = await posts.get_post_by_id(bot.db, int(row["id"]))
    assert row["message_id"] and row["shadow_message_id"]

    found = await posts.take_down_post(bot, guild, row, STAFF)

    assert found.ok
    assert bot.channels[WELCOME_CHANNEL].messages == {}
    assert bot.channels[TEST_CHANNEL].messages == {}
    fresh = await posts.get_post_by_id(bot.db, int(row["id"]))
    assert fresh["message_id"] is None and fresh["shadow_message_id"] is None
    assert fresh["posted_hash"] is None and fresh["body"] == "Hello."
    assert posts.status_words(fresh) == [posts.STATUS_NOT_POSTED]


async def test_taking_down_a_shadow_only_post_clears_it(bot, guild):
    row = await shadow_post(bot, guild)
    await posts.publish_post(bot, guild, row, STAFF)
    row = await posts.get_post_by_id(bot.db, int(row["id"]))

    found = await posts.take_down_post(bot, guild, row, STAFF)

    assert found.ok
    assert bot.channels[TEST_CHANNEL].messages == {}
    fresh = await posts.get_post_by_id(bot.db, int(row["id"]))
    assert fresh["shadow_message_id"] is None and fresh["posted_hash"] is None
    said = await details_of(bot.db, "post.taken_down")
    assert said["shadow_message_id"] == 9001 and said["message_id"] is None


async def test_with_no_guard_the_shadow_copy_goes_to_the_log_channel(bot, guild):
    """Off the test bench there is no guard, so the shadow channel is log_channel_id."""
    await bot.store.set(GUILD, posts.MODE_KEY, posts.SHADOW)
    bot.guard = None
    bot.settings.test_channel_id = None
    row = await a_post(bot, guild, channel_id=WELCOME_CHANNEL)

    found = await posts.publish_post(bot, guild, row, STAFF)

    assert found.ok and "#bot-log" in found.message
    # The log channel also carries the action-log embed, so it is the POST that is counted.
    assert [one for one in bot.channels[LOG_CHANNEL].sent if one.get("content")] == [
        {
            "content": "Hello.",
            "embed": None,
            "allowed_mentions": bot.channels[LOG_CHANNEL].sent[0]["allowed_mentions"],
        }
    ]
    assert bot.channels[WELCOME_CHANNEL].sent == []


async def test_shadow_with_nowhere_to_put_the_copy_refuses_in_words(bot, guild):
    await bot.store.set(GUILD, posts.MODE_KEY, posts.SHADOW)
    await bot.store.clear(GUILD, "log_channel_id")
    bot.guard = None
    bot.settings.test_channel_id = None
    row = await a_post(bot, guild, channel_id=WELCOME_CHANNEL)

    found = await posts.publish_post(bot, guild, row, STAFF)

    assert not found.ok and found.code == "no_shadow_channel"
    assert "log_channel_id" in found.message
    assert await kinds(bot.db) == []


async def test_a_post_with_no_channel_of_its_own_can_still_be_rehearsed(bot, guild):
    """Shadow never touches the row's channel, so refusing for want of one would be a
    refusal about something shadow does not do."""
    await bot.store.set(GUILD, posts.MODE_KEY, posts.SHADOW)
    bot.guard = FakeGuard()
    row = await a_post(bot, guild, channel_id=None)

    found = await posts.publish_post(bot, guild, row, STAFF)

    assert found.ok and len(bot.channels[TEST_CHANNEL].sent) == 1
    assert posts.shadow_words(bot, guild, row) == posts.SHADOW_LINE_NOWHERE.format(
        shadow="#blackbloc-logs"
    )


async def test_the_shadow_line_names_the_shadow_channel_and_the_posts_own(bot, guild):
    bot.guard = FakeGuard()
    row = await a_post(bot, guild, channel_id=WELCOME_CHANNEL)

    assert posts.shadow_words(bot, guild, row) == (
        "shadow — this goes to #blackbloc-logs, not #welcome, until posts are on."
    )


async def test_a_post_already_aimed_at_the_shadow_channel_is_not_told_not_to_go_there(bot, guild):
    """§C9's OLD workaround was to point a post at #blackbloc-logs to see it, so this is a
    row staff really have; `not #blackbloc-logs` about #blackbloc-logs is nonsense."""
    bot.guard = FakeGuard()
    row = await a_post(bot, guild, channel_id=TEST_CHANNEL)

    assert posts.shadow_words(bot, guild, row) == (
        "shadow — this goes to #blackbloc-logs, which is where it was going anyway."
    )


async def test_the_sweep_forgets_a_shadow_copy_somebody_deleted_by_hand(bot, guild):
    row = await shadow_post(bot, guild, pin=False)
    await posts.publish_post(bot, guild, row, STAFF)
    bot.channels[TEST_CHANNEL].messages.clear()

    done = await posts.reconcile_posts(bot)

    assert done["gone"] == 1
    fresh = await posts.get_post_by_id(bot.db, int(row["id"]))
    assert fresh["shadow_message_id"] is None and fresh["posted_hash"] is None
    assert "post.shadow_message_gone" in await kinds(bot.db)


async def test_the_sweep_re_pins_a_shadow_copy_somebody_unpinned(bot, guild):
    row = await shadow_post(bot, guild)
    await posts.publish_post(bot, guild, row, STAFF)
    bot.channels[TEST_CHANNEL].messages[9001].pinned = False

    done = await posts.reconcile_posts(bot)

    assert done["pinned"] == 1
    assert bot.channels[TEST_CHANNEL].messages[9001].pinned is True


async def test_the_mode_key_answers_three_values_and_an_unknown_one_reads_as_shadow(bot, guild):
    assert posts.MODES == ("off", "shadow", "on")
    for value in posts.MODES:
        await bot.store.set(GUILD, posts.MODE_KEY, value)
        assert posts.mode_of(bot.store, GUILD) == value
    assert posts.posts_are_off(bot.store, GUILD) is False
    # The registry refuses a fourth value, so an unknown one can only arrive from a hand-edited
    # row — and it reads as the safe mode rather than as `on`.
    assert posts.mode_of(SimpleNamespace(get=lambda *a: "nonsense"), GUILD) == posts.SHADOW
    assert posts.mode_of(SimpleNamespace(get=lambda *a: None), GUILD) == posts.SHADOW


async def test_set_mode_answers_in_words_for_each_of_the_three(bot, guild):
    bot.guard = FakeGuard()

    off = await posts.set_mode(bot, guild, STAFF, "off")
    shadow = await posts.set_mode(bot, guild, STAFF, "shadow")
    on = await posts.set_mode(bot, guild, STAFF, "on")

    assert off == posts.MODE_OFF_SAID
    assert "#blackbloc-logs" in shadow and "nothing reaches members" in shadow
    assert on == posts.MODE_ON_SAID
    assert await kinds(bot.db) == ["post.mode", "post.mode", "post.mode"]
    assert bot.store.get(GUILD, posts.MODE_KEY) == "on"
