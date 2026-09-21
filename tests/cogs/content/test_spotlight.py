import json
from datetime import UTC, datetime, timedelta

import pytest

from black_bloc import pings
from black_bloc import spotlight as words
from black_bloc.cogs.content.golive import GoLive
from black_bloc.cogs.content.spotlight import (
    Spotlight,
    add_channel,
    build_spotlight,
    bump_now,
    bumps_of,
    channel_by_id,
    channel_by_login,
    channels_for,
    delete_channel,
    end_session,
    expire_for_event,
    forget_spotlight,
    link_youtube,
    mode_lines,
    open_session,
    open_sessions,
    recent_sessions,
    render_spotlight,
    run_spotlight_move,
    set_announce,
    set_announced,
    set_spotlight,
    spotlight_channel,
    start_session,
    unlink_youtube,
    update_channel,
)
from black_bloc.config import load_settings
from black_bloc.golive import StreamInfo, now_iso
from black_bloc.settings_store import (
    SPOTLIGHT_BUMP_CLEANUP_KEY,
    SPOTLIGHT_END_MISSES_KEY,
    SPOTLIGHT_MODE_KEY,
    SettingsStore,
)
from black_bloc.twitch import TwitchError, TwitchGame, TwitchStream

GUILD = 7
CHANNEL = 111
SHADOW_CHANNEL = 333
LOG_CHANNEL = 222
STAFF = 900
GDQ = "gamesdonequick"


class FakeMessage:
    def __init__(self, message_id, content, channel, **kwargs):
        self.id = message_id
        self.content = content
        self.channel = channel
        self.kwargs = kwargs
        self.edits = []
        self.pinned = False
        self.pins = []
        self.unpins = []
        self.deleted = False
        self.embeds = [kwargs["embed"]] if kwargs.get("embed") is not None else []

    async def edit(self, content=None, **kwargs):
        self.content = content
        self.edits.append(kwargs)
        if kwargs.get("embed") is not None:
            self.embeds = [kwargs["embed"]]

    async def pin(self, reason=None):
        if self.channel.pin_raises is not None:
            raise self.channel.pin_raises
        self.pinned = True
        self.pins.append(reason)

    async def unpin(self, reason=None):
        if self.channel.unpin_raises is not None:
            raise self.channel.unpin_raises
        self.pinned = False
        self.unpins.append(reason)

    async def delete(self):
        self.deleted = True
        self.channel.messages = [one for one in self.channel.messages if one is not self]

    @property
    def embed(self):
        return self.embeds[0] if self.embeds else None


class FakeChannel:
    def __init__(self, channel_id=CHANNEL):
        self.id = channel_id
        self.messages = []
        self.next_id = 1
        self.send_raises = None
        self.pin_raises = None
        self.unpin_raises = None

    async def send(self, content=None, **kwargs):
        if self.send_raises is not None:
            raise self.send_raises
        message = FakeMessage(self.next_id, content or "", self, **kwargs)
        self.next_id += 1
        self.messages.append(message)
        return message

    async def fetch_message(self, message_id):
        for message in self.messages:
            if message.id == message_id:
                return message
        raise LookupError(message_id)

    @property
    def texts(self):
        return [one.content for one in self.messages]


class FakeRole:
    def __init__(self, role_id, name):
        self.id = role_id
        self.name = name
        self.members = []
        self.deleted = False

    def is_assignable(self):
        return True

    async def delete(self, reason=None):
        self.deleted = True


class FakeGuild:
    def __init__(self):
        self.id = GUILD
        self.roles = []
        self.made = []
        self.channels = {
            CHANNEL: FakeChannel(CHANNEL),
            SHADOW_CHANNEL: FakeChannel(SHADOW_CHANNEL),
            LOG_CHANNEL: FakeChannel(LOG_CHANNEL),
        }

    @property
    def channel(self):
        return self.channels[CHANNEL]

    @property
    def shadow(self):
        return self.channels[SHADOW_CHANNEL]

    def get_channel(self, channel_id):
        return self.channels.get(channel_id)

    def get_member(self, user_id):
        return None

    def get_role(self, role_id):
        return next((one for one in self.roles if one.id == int(role_id)), None)

    async def create_role(self, name=None, mentionable=False, reason=None):
        role = FakeRole(7000 + len(self.roles), name)
        self.roles.append(role)
        self.made.append(name)
        return role


class FakeHelix:
    def __init__(self, streams=(), games=(), raises=None):
        self.streams = list(streams)
        self.games = list(games)
        self.raises = raises
        self.stream_calls = []

    async def get_streams(self, logins):
        self.stream_calls.append(list(logins))
        if self.raises is not None:
            raise self.raises
        wanted = {one.lower() for one in logins}
        return [one for one in self.streams if one.user_login in wanted]

    async def get_games(self, ids):
        return [one for one in self.games if one.id in {str(i) for i in ids}]

    async def close(self):
        return None


class FakeGoLive:
    def __init__(self, helix=None):
        self.helix = helix


class FakeYouTubeClient:
    def __init__(self, channel_id=None, title="", raises=None):
        self.channel_id = channel_id
        self.title = title
        self.raises = raises

    async def resolve(self, given):
        if self.raises is not None:
            raise self.raises
        return (self.channel_id, self.title)


class FakeYouTube:
    def __init__(self, channel_id=None, title="", raises=None):
        self.client = FakeYouTubeClient(channel_id, title, raises)


class FakeBot:
    def __init__(self, db, store, settings, guild):
        self.db = db
        self.store = store
        self.settings = settings
        self.guard = None
        self.guilds = [guild]
        self.guild = guild
        self.cogs = {}

    def get_channel(self, channel_id):
        return self.guild.get_channel(channel_id)

    def get_cog(self, name):
        return self.cogs.get(name)

    async def wait_until_ready(self):
        return None


class FakeActor:
    id = STAFF
    display_name = "A Lead"
    name = "lead"
    mention = f"<@{STAFF}>"
    bot = False


class FakeResponse:
    def __init__(self):
        self.messages = []
        self.modals = []
        self.deferred = False

    async def send_message(self, content=None, ephemeral=False, **kwargs):
        self.messages.append({"content": content, "kwargs": kwargs})

    async def defer(self, ephemeral=False):
        self.deferred = True

    async def send_modal(self, modal):
        self.modals.append(modal)
        self.deferred = True

    def is_done(self):
        return self.deferred or bool(self.messages)


class FakeFollowup:
    def __init__(self, response):
        self.response = response

    async def send(self, content=None, ephemeral=False, **kwargs):
        self.response.messages.append({"content": content, "kwargs": kwargs})


class FakePanelMessage:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class FakeInteraction:
    def __init__(self, bot, user, guild):
        self.client = bot
        self.user = user
        self.guild = guild
        self.guild_id = guild.id
        self.channel_id = CHANNEL
        self.response = FakeResponse()
        self.followup = FakeFollowup(self.response)
        self.edits = []

    @property
    def sent(self):
        said = [one["content"] for one in self.response.messages if one.get("content")]
        return said[-1] if said else None

    async def original_response(self):
        return FakePanelMessage()

    async def edit_original_response(self, **kwargs):
        self.edits.append(kwargs)
        return FakePanelMessage(**kwargs)

    @property
    def view(self):
        return self.edits[-1].get("view") if self.edits else None

    @property
    def words(self):
        found = self.edits[-1].get("embed") if self.edits else None
        return "" if found is None else str(found.description or "")

    def labels(self):
        found = self.view
        return [] if found is None else [getattr(one, "label", None) for one in found.children]


def twitch_stream(login=GDQ, game="Celeste", title="AGDQ 2027", game_id="1"):
    return TwitchStream(
        "10", login, "GamesDoneQuick", game, title, "2026-09-20T12:00:00Z", game_id, ""
    )


async def kinds(db):
    cur = await db.conn.execute("SELECT kind FROM action_log ORDER BY id")
    return [row["kind"] for row in await cur.fetchall()]


async def details_of(db, kind):
    cur = await db.conn.execute(
        "SELECT details FROM action_log WHERE kind = ? ORDER BY id DESC LIMIT 1", (kind,)
    )
    row = await cur.fetchone()
    return json.loads(row["details"]) if row and row["details"] else None


@pytest.fixture
async def bot(db, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    settings = load_settings(_env_file=None, test_mode=False)
    store = SettingsStore(db, settings)
    await store.load()
    await store.set(GUILD, "log_channel_id", LOG_CHANNEL)
    await store.set(GUILD, "golive_channel_id", CHANNEL)
    await store.set(GUILD, "shadow_channel_id", SHADOW_CHANNEL)
    await store.set(GUILD, SPOTLIGHT_MODE_KEY, "on")
    made = FakeBot(db, store, settings, FakeGuild())
    made.store.is_staff = lambda member: True
    return made


@pytest.fixture
def cog(bot):
    made = Spotlight(bot)
    bot.cogs["Spotlight"] = made
    bot.cogs["GoLive"] = FakeGoLive(FakeHelix())
    return made


def helix_of(bot, *streams, games=(), raises=None):
    made = FakeHelix(streams, games, raises)
    bot.cogs["GoLive"] = FakeGoLive(made)
    return made


async def a_row(bot, login=GDQ, **fields):
    fields.setdefault("spotlight", True)
    outcome, row = await spotlight_channel(
        bot, bot.guild, FakeActor(), login, keep=True, **fields
    )
    assert outcome == "added"
    return row


# --- the list ---------------------------------------------------------------------------------


async def test_a_kept_row_says_kept_and_carries_the_defaults(bot):
    row = await a_row(bot)
    assert row["twitch_login"] == GDQ and row["expires_at"] is None and row["pin"] == 1
    assert words.until_words(row) == "kept"
    assert (await details_of(bot.db, "golive.spotlight_added"))["login"] == GDQ


async def test_a_duplicate_add_refuses_in_words_and_offers_extend(bot):
    await a_row(bot)
    outcome, row = await spotlight_channel(bot, bot.guild, FakeActor(), "GamesDoneQuick")
    assert outcome == "already" and row is None
    assert len(await channels_for(bot.db, GUILD)) == 1


async def test_a_name_that_is_not_a_channel_is_refused_rather_than_stored(bot):
    outcome, row = await spotlight_channel(bot, bot.guild, FakeActor(), "games done quick")
    assert outcome == "bad_login" and row is None
    assert await channels_for(bot.db, GUILD) == []


async def test_a_row_with_no_keep_takes_the_default_days(bot):
    outcome, row = await spotlight_channel(
        bot, bot.guild, FakeActor(), "esamarathon", spotlight=True
    )
    assert outcome == "added" and row["expires_at"] is not None
    assert words.until_words(row).startswith("until ")


async def test_staff_can_always_remove_a_row_whatever_state_it_is_in(bot, cog):
    row = await a_row(bot)
    helix_of(bot, twitch_stream())
    await cog.poll_once()
    assert await open_session(bot.db, row["id"]) is not None
    assert await forget_spotlight(bot, bot.guild, FakeActor(), row["id"]) is not None
    assert await channels_for(bot.db, GUILD) == []
    assert await open_sessions(bot.db, GUILD) == []
    assert "golive.spotlight_removed" in await kinds(bot.db)


# --- offline to live --------------------------------------------------------------------------


async def test_going_live_announces_once_and_pins_it(bot, cog):
    row = await a_row(bot)
    helix_of(bot, twitch_stream(), games=[TwitchGame("1", "Celeste", "art")])
    await cog.poll_once()

    posted = bot.guild.channel.messages
    assert len(posted) == 1 and "GamesDoneQuick" in posted[0].content
    assert posted[0].pinned is True
    assert posted[0].pins == [words.PIN_REASON]
    session = await open_session(bot.db, row["id"])
    assert session["announced_message_id"] == posted[0].id and session["mode"] == "on"
    assert "golive.spotlight_announced" in await kinds(bot.db)
    assert "golive.spotlight_pinned" in await kinds(bot.db)

    await cog.poll_once()
    assert len(bot.guild.channel.messages) == 1


async def test_the_card_names_the_channel_not_someone(bot, cog):
    await a_row(bot)
    helix_of(bot, twitch_stream())
    await cog.poll_once()
    card = bot.guild.channel.messages[0].embed
    assert card is not None and "GamesDoneQuick" in card.author.name
    assert "Someone" not in card.author.name


async def test_the_spotlight_card_uses_the_guilds_own_live_top_line(bot, cog):
    await a_row(bot)
    await bot.store.set(bot.guild.id, "golive_live_author", "{name} is streaming on {platform}")
    helix_of(bot, twitch_stream())

    await cog.poll_once()

    assert bot.guild.channel.messages[0].embed.author.name == (
        "GamesDoneQuick is streaming on Twitch"
    )


async def test_a_row_with_pin_off_is_announced_and_left_unpinned(bot, cog):
    await a_row(bot, pin=False)
    helix_of(bot, twitch_stream())
    await cog.poll_once()
    posted = bot.guild.channel.messages
    assert len(posted) == 1 and posted[0].pinned is False
    assert "golive.spotlight_pinned" not in await kinds(bot.db)


async def test_shadow_posts_the_rehearsal_copy_and_says_would(bot, cog):
    await bot.store.set(GUILD, SPOTLIGHT_MODE_KEY, "shadow")
    await a_row(bot)
    helix_of(bot, twitch_stream())
    await cog.poll_once()

    assert bot.guild.channel.messages == []
    rehearsed = bot.guild.shadow.messages
    assert len(rehearsed) == 1 and f"<#{CHANNEL}>" in rehearsed[0].content
    assert "golive.would_spotlight_announce" in await kinds(bot.db)
    assert "golive.spotlight_announced" not in await kinds(bot.db)


async def test_mode_off_watches_nothing_at_all(bot, cog):
    await bot.store.set(GUILD, SPOTLIGHT_MODE_KEY, "off")
    await a_row(bot)
    helix = helix_of(bot, twitch_stream())
    await cog.poll_once()
    assert helix.stream_calls == [] and bot.guild.channel.messages == []


async def test_no_twitch_key_polls_nothing_and_the_panel_says_so(bot, cog):
    await a_row(bot)
    bot.cogs["GoLive"] = FakeGoLive(None)
    await cog.poll_once()
    assert bot.guild.channel.messages == []
    assert cog.last_poll_error == words.NO_KEY
    assert words.NO_KEY in " ".join(mode_lines(bot, bot.guild))


async def test_an_unreachable_twitch_leaves_everything_as_it_was(bot, cog):
    await a_row(bot)
    helix_of(bot, raises=TwitchError("twitch unreachable"))
    await cog.poll_once()
    assert bot.guild.channel.messages == []
    assert "unreachable" in (cog.last_poll_error or "")


async def test_one_batched_call_covers_the_whole_list(bot, cog):
    await a_row(bot)
    await a_row(bot, login="esamarathon")
    helix = helix_of(bot)
    await cog.poll_once()
    assert helix.stream_calls == [["esamarathon", GDQ]]


async def test_a_post_that_fails_leaves_no_session_behind_and_says_why(bot, cog):
    row = await a_row(bot)
    bot.guild.channel.send_raises = RuntimeError("boom")
    helix_of(bot, twitch_stream())
    await cog.poll_once()
    assert await open_session(bot.db, row["id"]) is None
    assert "golive.spotlight_post_failed" in await kinds(bot.db)
    assert "golive.spotlight_announced" not in await kinds(bot.db)


async def test_a_pin_that_fails_is_a_log_row_and_never_a_crash(bot, cog):
    row = await a_row(bot)
    bot.guild.channel.pin_raises = RuntimeError("Forbidden")
    helix_of(bot, twitch_stream())
    await cog.poll_once()
    assert len(bot.guild.channel.messages) == 1
    assert await open_session(bot.db, row["id"]) is not None
    assert "golive.spotlight_pin_failed" in await kinds(bot.db)


# --- the bump ---------------------------------------------------------------------------------


async def test_the_bump_fires_at_the_interval_and_never_on_the_first_look(bot, cog):
    row = await a_row(bot)
    helix_of(bot, twitch_stream())
    await cog.poll_once()
    assert len(bot.guild.channel.messages) == 1

    await cog.poll_once()
    assert len(bot.guild.channel.messages) == 1

    session = await open_session(bot.db, row["id"])
    await bot.db.conn.execute(
        "UPDATE spotlight_sessions SET started_at = ? WHERE id = ?",
        ((datetime.now(UTC) - timedelta(hours=4, minutes=1)).isoformat(), session["id"]),
    )
    await bot.db.conn.commit()
    await cog.poll_once()

    assert len(bot.guild.channel.messages) == 2
    bump = bot.guild.channel.messages[1]
    assert "is still live" in bump.content and bump.pinned is False
    fresh = await open_session(bot.db, row["id"])
    assert fresh["bump_count"] == 1 and fresh["last_bump_at"] is not None
    assert [one["message_id"] for one in await bumps_of(bot.db, session["id"])] == [bump.id]
    assert "golive.spotlight_bumped" in await kinds(bot.db)


async def test_the_second_bump_is_measured_from_the_first_not_from_the_start(bot, cog):
    row = await a_row(bot)
    helix_of(bot, twitch_stream())
    await cog.poll_once()
    session = await open_session(bot.db, row["id"])
    await bot.db.conn.execute(
        "UPDATE spotlight_sessions SET started_at = ?, last_bump_at = ?, bump_count = 1 "
        "WHERE id = ?",
        (
            (datetime.now(UTC) - timedelta(hours=9)).isoformat(),
            (datetime.now(UTC) - timedelta(hours=1)).isoformat(),
            session["id"],
        ),
    )
    await bot.db.conn.commit()
    await cog.poll_once()
    assert len(bot.guild.channel.messages) == 1


async def test_a_rows_own_bump_hours_beat_the_key(bot, cog):
    row = await a_row(bot, bump_hours=1)
    helix_of(bot, twitch_stream())
    await cog.poll_once()
    session = await open_session(bot.db, row["id"])
    await bot.db.conn.execute(
        "UPDATE spotlight_sessions SET started_at = ? WHERE id = ?",
        ((datetime.now(UTC) - timedelta(hours=2)).isoformat(), session["id"]),
    )
    await bot.db.conn.commit()
    await cog.poll_once()
    assert len(bot.guild.channel.messages) == 2


async def test_bump_now_refuses_in_words_when_nothing_is_live(bot, cog):
    row = await a_row(bot)
    outcome, found = await bump_now(bot, bot.guild, FakeActor(), row["id"])
    assert outcome == "not_live" and found["twitch_login"] == GDQ
    assert bot.guild.channel.messages == []


async def test_bump_now_posts_one_reminder_while_it_is_live(bot, cog):
    row = await a_row(bot)
    helix_of(bot, twitch_stream())
    await cog.poll_once()
    outcome, _ = await bump_now(bot, bot.guild, FakeActor(), row["id"])
    assert outcome == "bumped" and len(bot.guild.channel.messages) == 2


# --- the end ----------------------------------------------------------------------------------


async def test_the_end_unpins_rewrites_in_the_past_tense_and_takes_the_bumps_away(bot, cog):
    row = await a_row(bot)
    helix = helix_of(bot, twitch_stream())
    await cog.poll_once()
    session = await open_session(bot.db, row["id"])
    await bot.db.conn.execute(
        "UPDATE spotlight_sessions SET started_at = ? WHERE id = ?",
        ((datetime.now(UTC) - timedelta(hours=5)).isoformat(), session["id"]),
    )
    await bot.db.conn.commit()
    await cog.poll_once()
    assert len(bot.guild.channel.messages) == 2

    helix.streams = []
    await cog.poll_once()
    assert await open_session(bot.db, row["id"]) is not None

    await cog.poll_once()
    assert await open_session(bot.db, row["id"]) is None
    announcement = bot.guild.channel.messages[0]
    assert announcement.pinned is False and announcement.unpins == [words.UNPIN_REASON]
    assert "has ended" in announcement.content
    assert len(bot.guild.channel.messages) == 1
    assert await bumps_of(bot.db, session["id"]) == []
    assert "golive.spotlight_ended" in await kinds(bot.db)
    assert "golive.spotlight_unpinned" in await kinds(bot.db)


async def test_with_cleanup_off_the_reminders_stay_where_they_are(bot, cog):
    await bot.store.set(GUILD, SPOTLIGHT_BUMP_CLEANUP_KEY, False)
    row = await a_row(bot)
    helix = helix_of(bot, twitch_stream())
    await cog.poll_once()
    session = await open_session(bot.db, row["id"])
    await bot.db.conn.execute(
        "UPDATE spotlight_sessions SET started_at = ? WHERE id = ?",
        ((datetime.now(UTC) - timedelta(hours=5)).isoformat(), session["id"]),
    )
    await bot.db.conn.commit()
    await cog.poll_once()

    helix.streams = []
    await cog.poll_once()
    await cog.poll_once()
    assert len(bot.guild.channel.messages) == 2
    assert len(await bumps_of(bot.db, session["id"])) == 1


async def test_one_quiet_look_is_not_the_end(bot, cog):
    await bot.store.set(GUILD, SPOTLIGHT_END_MISSES_KEY, 3)
    row = await a_row(bot)
    helix = helix_of(bot, twitch_stream())
    await cog.poll_once()
    helix.streams = []
    await cog.poll_once()
    await cog.poll_once()
    assert await open_session(bot.db, row["id"]) is not None
    await cog.poll_once()
    assert await open_session(bot.db, row["id"]) is None


async def test_a_stream_that_comes_back_before_the_misses_run_out_never_ends(bot, cog):
    await bot.store.set(GUILD, SPOTLIGHT_END_MISSES_KEY, 3)
    row = await a_row(bot)
    helix = helix_of(bot, twitch_stream())
    await cog.poll_once()
    session_id = (await open_session(bot.db, row["id"]))["id"]
    helix.streams = []
    await cog.poll_once()
    helix.streams = [twitch_stream()]
    await cog.poll_once()
    helix.streams = []
    await cog.poll_once()
    await cog.poll_once()
    assert await open_session(bot.db, row["id"]) is not None
    assert (await open_session(bot.db, row["id"]))["id"] == session_id


async def test_an_unpin_that_fails_is_a_log_row_and_the_end_still_lands(bot, cog):
    row = await a_row(bot)
    helix = helix_of(bot, twitch_stream())
    await cog.poll_once()
    bot.guild.channel.unpin_raises = RuntimeError("Forbidden")
    helix.streams = []
    await cog.poll_once()
    await cog.poll_once()
    assert await open_session(bot.db, row["id"]) is None
    assert "golive.spotlight_unpin_failed" in await kinds(bot.db)


# --- expiry -----------------------------------------------------------------------------------


async def test_a_kept_row_is_never_purged(bot, cog):
    await a_row(bot)
    await cog.poll_once()
    assert len(await channels_for(bot.db, GUILD)) == 1


async def test_a_row_whose_date_has_passed_ends_its_session_first_then_goes(bot, cog):
    row = await a_row(bot)
    helix_of(bot, twitch_stream())
    await cog.poll_once()
    announcement = bot.guild.channel.messages[0]
    assert announcement.pinned is True

    await update_channel(
        bot.db, row["id"], expires_at=(datetime.now(UTC) - timedelta(hours=1)).isoformat()
    )
    await cog.poll_once()

    assert await channels_for(bot.db, GUILD) == []
    assert await open_sessions(bot.db, GUILD) == []
    assert announcement.pinned is False
    said = await kinds(bot.db)
    assert "golive.spotlight_ended" in said and "golive.spotlight_expired" in said


async def test_a_cancelled_event_takes_its_spotlight_with_it_at_once(bot, cog):
    outcome, row = await spotlight_channel(
        bot,
        bot.guild,
        FakeActor(),
        GDQ,
        expires_at=(datetime.now(UTC) + timedelta(days=5)).isoformat(),
        event_id=42,
    )
    assert outcome == "added"
    assert await expire_for_event(bot, bot.guild, 42) is not None
    assert await channels_for(bot.db, GUILD) == []
    assert (await details_of(bot.db, "golive.spotlight_expired"))["because"] == "event_cancelled"


# --- the boot reconcile (checklist 37) --------------------------------------------------------


async def test_two_reconciles_at_boot_close_a_gone_session_once(bot, cog):
    row = await a_row(bot)
    session_id = await start_session(
        bot.db, GUILD, row["id"], StreamInfo(url="u", game="g", title="t"), "on"
    )
    await set_announced(bot.db, session_id, 9999)

    await cog.cog_load()
    await cog.on_ready()

    assert await open_session(bot.db, row["id"]) is None
    assert (await kinds(bot.db)).count("golive.spotlight_reconciled") == 1
    cog.poller.cancel()


async def test_a_cog_load_with_no_guilds_yet_leaves_the_boot_to_on_ready(bot, cog):
    """`setup_hook` loads the cogs before IDENTIFY, so `bot.guilds` is empty at `cog_load`.

    A pass over nothing must not close the 60-second window, or the one pass that HAS guilds
    is the one `skip_if_recent` throws away. Mirrors the go-live cog's guard.
    """
    row = await a_row(bot)
    session_id = await start_session(
        bot.db, GUILD, row["id"], StreamInfo(url="u", game="g", title="t"), "on"
    )
    await set_announced(bot.db, session_id, 9999)
    guild = bot.guild
    bot.guilds = []

    await cog.cog_load()
    try:
        assert await open_session(bot.db, row["id"]) is not None
        bot.guilds = [guild]
        await cog.on_ready()
    finally:
        cog.poller.cancel()

    assert await open_session(bot.db, row["id"]) is None
    assert (await kinds(bot.db)).count("golive.spotlight_reconciled") == 1


async def test_a_session_whose_message_is_still_there_survives_the_boot(bot, cog):
    row = await a_row(bot)
    helix_of(bot, twitch_stream())
    await cog.poll_once()
    await cog.reconcile_open_sessions()
    assert await open_session(bot.db, row["id"]) is not None
    assert "golive.spotlight_reconciled" not in await kinds(bot.db)


# --- the /golive sub-panel --------------------------------------------------------------------


async def test_the_sub_panel_lists_the_channels_and_offers_add(bot, cog):
    await a_row(bot)
    interaction = FakeInteraction(bot, FakeActor(), bot.guild)
    await render_spotlight(interaction)
    assert GDQ in interaction.words and "kept" in interaction.words
    assert words.ADD_BUTTON in interaction.labels()


async def test_a_kept_row_offers_let_it_expire_and_a_dated_one_offers_keep(bot, cog):
    kept = await a_row(bot)
    interaction = FakeInteraction(bot, FakeActor(), bot.guild)
    await render_spotlight(interaction, kept["id"])
    assert "Let it expire" in interaction.labels()
    assert words.KEEP_FOREVER not in interaction.labels()

    _, dated = await spotlight_channel(
        bot, bot.guild, FakeActor(), "esamarathon", spotlight=True
    )
    second = FakeInteraction(bot, FakeActor(), bot.guild)
    await render_spotlight(second, dated["id"])
    assert words.KEEP_FOREVER in second.labels() and words.EXTEND_WEEK in second.labels()


async def test_bump_now_only_shows_while_the_channel_is_live(bot, cog):
    row = await a_row(bot)
    first = FakeInteraction(bot, FakeActor(), bot.guild)
    await render_spotlight(first, row["id"])
    assert words.BUMP_NOW not in first.labels()

    helix_of(bot, twitch_stream())
    await cog.poll_once()
    second = FakeInteraction(bot, FakeActor(), bot.guild)
    await render_spotlight(second, row["id"])
    assert words.BUMP_NOW in second.labels()


async def test_extending_a_row_from_the_panel_moves_its_date_and_says_so(bot, cog):
    _, row = await spotlight_channel(
        bot, bot.guild, FakeActor(), "esamarathon", days=2, spotlight=True
    )
    said, kept = await run_spotlight_move(bot, bot.guild, FakeActor(), row["id"], "extend")
    assert "esamarathon" in said and kept is True
    fresh = await channel_by_id(bot.db, row["id"])
    assert fresh["expires_at"] > row["expires_at"]
    assert "golive.spotlight_updated" in await kinds(bot.db)


async def test_keeping_a_row_for_ever_clears_its_date(bot, cog):
    _, row = await spotlight_channel(
        bot, bot.guild, FakeActor(), "esamarathon", days=2, spotlight=True
    )
    said, _ = await run_spotlight_move(bot, bot.guild, FakeActor(), row["id"], "keep")
    assert "kept for ever" in said
    assert (await channel_by_id(bot.db, row["id"]))["expires_at"] is None


async def test_a_move_on_a_row_that_has_gone_says_so_rather_than_crashing(bot, cog):
    said, kept = await run_spotlight_move(bot, bot.guild, FakeActor(), 4242, "remove")
    assert said == words.NO_SUCH_ROW and kept is False


# --- the storage round trip --------------------------------------------------------------------


async def test_the_channel_and_session_tables_round_trip(db):
    spotlight_id = await add_channel(
        db, GUILD, GDQ, added_by=STAFF, expires_at=None, pin=True
    )
    assert spotlight_id is not None
    assert await add_channel(db, GUILD, GDQ, added_by=STAFF, expires_at=None, pin=True) is None
    assert (await channel_by_login(db, GUILD, GDQ))["id"] == spotlight_id

    session_id = await start_session(
        db, GUILD, spotlight_id, StreamInfo(url="u", game="g", title="t"), "on"
    )
    assert await start_session(
        db, GUILD, spotlight_id, StreamInfo(url="u"), "on"
    ) is None
    await set_announced(db, session_id, 55)
    await end_session(db, session_id, now_iso())
    assert await open_session(db, spotlight_id) is None
    assert [one["id"] for one in await recent_sessions(db, GUILD)] == [session_id]
    assert await delete_channel(db, spotlight_id) is True
    assert await delete_channel(db, spotlight_id) is False


def test_the_cog_and_the_golive_cog_are_two_different_things():
    assert Spotlight.__name__ != GoLive.__name__


# --- the channel's own ping role (info/spotlight-pings-design.md §B) ---------------------------


PING_ROLE = 4242


async def a_fan_role(bot, row):
    made = await pings.ensure_fan_role(
        bot, bot.guild, None, by=STAFF, staff=True, spotlight=row
    )
    assert made.ok
    return made.role_id


async def test_the_announcement_pings_the_channels_role_beside_the_go_live_role(bot, cog):
    await bot.store.set(GUILD, "pings_mode", "on")
    await bot.store.set(GUILD, "golive_ping_role_id", PING_ROLE)
    bot.guild.roles.append(FakeRole(PING_ROLE, "Events"))
    row = await a_row(bot)
    role_id = await a_fan_role(bot, row)
    helix_of(bot, twitch_stream())

    await cog.poll_once()

    posted = bot.guild.channel.messages[0]
    assert posted.content.startswith(f"<@&{PING_ROLE}> <@&{role_id}> ")
    mentions = posted.kwargs["allowed_mentions"]
    assert [one.id for one in mentions.roles] == [PING_ROLE, role_id]
    assert (await details_of(bot.db, "golive.spotlight_announced"))["fan_role_id"] == role_id


async def test_an_announcement_for_a_channel_with_no_role_pings_only_the_go_live_role(bot, cog):
    await bot.store.set(GUILD, "pings_mode", "on")
    await bot.store.set(GUILD, "golive_ping_role_id", PING_ROLE)
    bot.guild.roles.append(FakeRole(PING_ROLE, "Events"))
    await a_row(bot)
    helix_of(bot, twitch_stream())

    await cog.poll_once()

    posted = bot.guild.channel.messages[0]
    assert posted.content.startswith(f"<@&{PING_ROLE}> ")
    assert (await details_of(bot.db, "golive.spotlight_announced"))["fan_role_id"] is None


async def test_a_bump_says_nothing_to_anybody_until_the_key_is_turned_on(bot, cog):
    await bot.store.set(GUILD, "pings_mode", "on")
    await bot.store.set(GUILD, "golive_ping_role_id", PING_ROLE)
    bot.guild.roles.append(FakeRole(PING_ROLE, "Events"))
    row = await a_row(bot)
    role_id = await a_fan_role(bot, row)
    helix_of(bot, twitch_stream())
    await cog.poll_once()
    session = await open_session(bot.db, row["id"])
    await bot.db.conn.execute(
        "UPDATE spotlight_sessions SET started_at = ? WHERE id = ?",
        ((datetime.now(UTC) - timedelta(hours=9)).isoformat(), session["id"]),
    )
    await bot.db.conn.commit()

    await cog.poll_once()

    quiet = bot.guild.channel.messages[1]
    assert not quiet.content.startswith("<@&")
    assert quiet.kwargs["allowed_mentions"].roles is False
    assert (await details_of(bot.db, "golive.spotlight_bumped"))["pinged"] is False

    await bot.store.set(GUILD, "spotlight_bump_pings", True)
    await bot.db.conn.execute(
        "UPDATE spotlight_sessions SET last_bump_at = ? WHERE id = ?",
        ((datetime.now(UTC) - timedelta(hours=9)).isoformat(), session["id"]),
    )
    await bot.db.conn.commit()
    await cog.poll_once()

    loud = bot.guild.channel.messages[2]
    assert loud.content.startswith(f"<@&{PING_ROLE}> <@&{role_id}> ")
    assert [one.id for one in loud.kwargs["allowed_mentions"].roles] == [PING_ROLE, role_id]
    said = await details_of(bot.db, "golive.spotlight_bumped")
    assert said["pinged"] is True and said["fan_role_id"] == role_id


async def test_an_expiring_channel_takes_its_ping_role_with_it(bot, cog):
    await bot.store.set(GUILD, "pings_mode", "on")
    await bot.store.set(GUILD, "pings_fan_role_delete", True)
    outcome, row = await spotlight_channel(
        bot, bot.guild, FakeActor(), GDQ, days=1, spotlight=True
    )
    assert outcome == "added"
    role_id = await a_fan_role(bot, row)
    await update_channel(
        bot.db, row["id"], expires_at=(datetime.now(UTC) - timedelta(days=1)).isoformat()
    )

    await cog.sweep_expiries(bot.guild)

    assert await channels_for(bot.db, GUILD) == []
    assert await pings.get_spotlight_fan_role(bot.db, GUILD, row["id"]) is None
    assert bot.guild.get_role(role_id).deleted is True
    said = await details_of(bot.db, "pings.fan_role_removed")
    assert said["because"] == words.FAN_ROLE_EXPIRED and said["spotlight_id"] == row["id"]


async def test_an_expiry_keeps_the_discord_role_when_the_setting_says_keep(bot, cog):
    await bot.store.set(GUILD, "pings_mode", "on")
    await bot.store.set(GUILD, "pings_fan_role_delete", False)
    outcome, row = await spotlight_channel(
        bot, bot.guild, FakeActor(), GDQ, days=1, spotlight=True
    )
    assert outcome == "added"
    role_id = await a_fan_role(bot, row)
    await update_channel(
        bot.db, row["id"], expires_at=(datetime.now(UTC) - timedelta(days=1)).isoformat()
    )

    await cog.sweep_expiries(bot.guild)

    assert bot.guild.get_role(role_id).deleted is False
    assert (await details_of(bot.db, "pings.fan_role_removed"))["deleted"] is False


async def test_removing_a_channel_takes_its_ping_role_too(bot, cog):
    await bot.store.set(GUILD, "pings_mode", "on")
    row = await a_row(bot)
    await a_fan_role(bot, row)

    await forget_spotlight(bot, bot.guild, FakeActor(), row["id"])

    assert await pings.get_spotlight_fan_role(bot.db, GUILD, row["id"]) is None
    said = await details_of(bot.db, "pings.fan_role_removed")
    assert said["because"] == words.FAN_ROLE_REMOVED


async def test_staff_give_and_take_a_channels_role_from_the_sub_panel(bot, cog):
    await bot.store.set(GUILD, "pings_mode", "on")
    row = await a_row(bot)

    said, picked = await run_spotlight_move(
        bot, bot.guild, FakeActor(), row["id"], "give_role"
    )

    assert picked is True and "gamesdonequick pings" in said
    held = await pings.get_spotlight_fan_role(bot.db, GUILD, row["id"])
    assert held is not None

    embed, view = await build_spotlight(bot, bot.guild, row["id"])
    assert words.TAKE_PING_ROLE in [getattr(one, "label", None) for one in view.children]
    assert f"<@&{held['role_id']}>" in str(embed.description)

    said, picked = await run_spotlight_move(
        bot, bot.guild, FakeActor(), row["id"], "take_role"
    )

    assert picked is True and "no longer has a ping role" in said
    assert await pings.get_spotlight_fan_role(bot.db, GUILD, row["id"]) is None
    _embed, view = await build_spotlight(bot, bot.guild, row["id"])
    assert words.GIVE_PING_ROLE in [getattr(one, "label", None) for one in view.children]


async def test_a_move_on_a_row_that_has_gone_says_so_rather_than_a_bare_status(bot, cog):
    said, picked = await run_spotlight_move(bot, bot.guild, FakeActor(), 9999, "give_role")

    assert said == words.NO_SUCH_ROW and picked is False


async def test_the_first_announcement_writes_twitchs_own_spelling_onto_the_row(bot, cog):
    """A row added by hand only knows the login, so its ping role would be called
    *gamesdonequick pings*; the announcement is where Twitch's `GamesDoneQuick` arrives."""
    row = await a_row(bot)
    assert words.display_for(row) == GDQ
    helix_of(bot, twitch_stream())

    await cog.poll_once()

    fresh = await channel_by_id(bot.db, row["id"])
    assert words.display_for(fresh) == "GamesDoneQuick"
    made = await pings.ensure_fan_role(
        bot, bot.guild, None, by=STAFF, staff=True, spotlight=fresh
    )
    assert bot.guild.get_role(made.role_id).name == "GamesDoneQuick pings"


# --- the channel record: spotlight and the opt-out are toggles on a row that persists ---------


async def test_a_channel_with_the_spotlight_off_is_announced_like_a_member_and_never_pinned(
    bot, cog
):
    row = await a_row(bot, spotlight=False)
    helix_of(bot, twitch_stream())

    await cog.poll_once()

    assert bot.guild.channel.texts, "nothing was announced at all"
    message = bot.guild.channel.messages[-1]
    assert message.pinned is False and message.pins == []
    said = await details_of(bot.db, "golive.spotlight_announced")
    assert said["spotlight"] is False and said["pin"] is False
    assert await open_session(bot.db, row["id"]) is not None


async def test_the_spotlight_off_announcement_is_the_same_wording_a_member_gets(bot, cog):
    await bot.store.set(GUILD, "golive_template", "{name} is live: {url}")
    row = await a_row(bot, spotlight=False)
    helix_of(bot, twitch_stream())

    await cog.poll_once()

    assert bot.guild.channel.texts[-1] == (
        "GamesDoneQuick is live: https://www.twitch.tv/gamesdonequick"
    )
    assert row is not None


async def test_a_channel_with_the_spotlight_off_is_never_bumped(bot, cog):
    row = await a_row(bot, spotlight=False, bump_hours=1)
    helix_of(bot, twitch_stream())
    await cog.poll_once()
    session = await open_session(bot.db, row["id"])
    await bot.db.conn.execute(
        "UPDATE spotlight_sessions SET started_at = ? WHERE id = ?",
        ((datetime.now(UTC) - timedelta(hours=9)).isoformat(), session["id"]),
    )
    await bot.db.conn.commit()

    await cog.poll_once()

    assert len(bot.guild.channel.messages) == 1
    assert "golive.spotlight_bumped" not in await kinds(bot.db)


async def test_the_end_still_rewrites_a_spotlight_off_announcement_in_the_past_tense(bot, cog):
    await bot.store.set(GUILD, SPOTLIGHT_END_MISSES_KEY, 1)
    row = await a_row(bot, spotlight=False)
    helix_of(bot, twitch_stream())
    await cog.poll_once()
    message = bot.guild.channel.messages[-1]
    helix_of(bot)

    await cog.poll_once()

    assert message.edits, "the announcement was never marked ended"
    assert await open_session(bot.db, row["id"]) is None
    assert message.unpins == []


async def test_the_toggle_keeps_the_row_its_role_and_its_sessions(bot, cog):
    await bot.store.set(GUILD, "pings_mode", "on")
    row = await a_row(bot)
    role_id = await a_fan_role(bot, row)
    helix_of(bot, twitch_stream())
    await cog.poll_once()
    session = await open_session(bot.db, row["id"])

    said, picked = await run_spotlight_move(
        bot, bot.guild, FakeActor(), row["id"], "spotlight_off"
    )

    assert picked is True and "like anybody else" in said
    fresh = await channel_by_id(bot.db, row["id"])
    assert fresh is not None and words.is_spotlit(fresh) is False
    held = await pings.get_spotlight_fan_role(bot.db, GUILD, row["id"])
    assert held is not None and int(held["role_id"]) == int(role_id)
    assert (await open_session(bot.db, row["id"]))["id"] == session["id"]

    back, _ = await run_spotlight_move(
        bot, bot.guild, FakeActor(), row["id"], "spotlight_on"
    )
    assert "is spotlighted" in back
    assert words.is_spotlit(await channel_by_id(bot.db, row["id"])) is True


async def test_a_channel_with_the_spotlight_off_is_never_purged(bot, cog):
    row = await a_row(bot, spotlight=False)
    await update_channel(
        bot.db, row["id"], expires_at=(datetime.now(UTC) - timedelta(days=30)).isoformat()
    )

    await cog.sweep_expiries(bot.guild)

    assert await channel_by_id(bot.db, row["id"]) is not None


async def test_an_opted_out_channel_is_listed_and_never_announced(bot, cog):
    row = await a_row(bot)
    said, picked = await run_spotlight_move(bot, bot.guild, FakeActor(), row["id"], "opt_out")
    assert picked is True and "is opted out" in said
    helix_of(bot, twitch_stream())

    await cog.poll_once()

    assert bot.guild.channel.texts == []
    assert await open_session(bot.db, row["id"]) is None
    assert await channel_by_id(bot.db, row["id"]) is not None
    assert "golive.spotlight_announced" not in await kinds(bot.db)


async def test_opting_a_channel_back_in_announces_the_next_time(bot, cog):
    row = await a_row(bot)
    await run_spotlight_move(bot, bot.guild, FakeActor(), row["id"], "opt_out")
    helix_of(bot, twitch_stream())
    await cog.poll_once()
    assert bot.guild.channel.texts == []

    said, _ = await run_spotlight_move(bot, bot.guild, FakeActor(), row["id"], "opt_in")

    assert "opted back in" in said
    await cog.poll_once()
    assert bot.guild.channel.texts, "opting back in did not start it announcing"


async def test_an_opted_out_channel_keeps_its_role_and_its_youtube_link(bot, cog):
    await bot.store.set(GUILD, "pings_mode", "on")
    row = await a_row(bot)
    role_id = await a_fan_role(bot, row)
    await update_channel(bot.db, row["id"], youtube_channel_id="UC" + "x" * 22)

    await run_spotlight_move(bot, bot.guild, FakeActor(), row["id"], "opt_out")

    fresh = await channel_by_id(bot.db, row["id"])
    assert words.youtube_of(fresh) == "UC" + "x" * 22
    held = await pings.get_spotlight_fan_role(bot.db, GUILD, row["id"])
    assert held is not None and int(held["role_id"]) == int(role_id)


async def test_the_panel_only_offers_the_spotlight_moves_while_the_spotlight_is_on(bot, cog):
    row = await a_row(bot, spotlight=False)

    _embed, view = await build_spotlight(bot, bot.guild, row["id"])
    labels = [getattr(one, "label", None) for one in view.children]
    assert words.SPOTLIGHT_ON in labels
    assert words.EXTEND_WEEK not in labels and words.KEEP_FOREVER not in labels
    assert "Let it expire" not in labels and words.BUMP_NOW not in labels
    assert words.OPT_OUT in labels and words.LINK_YOUTUBE in labels
    assert words.REMOVE in labels

    await set_spotlight(bot, bot.guild, FakeActor(), row["id"], True)
    _embed, on = await build_spotlight(bot, bot.guild, row["id"])
    now_labels = [getattr(one, "label", None) for one in on.children]
    assert words.SPOTLIGHT_OFF in now_labels and "Let it expire" in now_labels


async def test_an_opted_out_channel_is_never_offered_a_bump(bot, cog):
    row = await a_row(bot)
    helix_of(bot, twitch_stream())
    await cog.poll_once()
    await set_announce(bot, bot.guild, FakeActor(), row["id"], False)

    _embed, view = await build_spotlight(bot, bot.guild, row["id"])

    assert words.BUMP_NOW not in [getattr(one, "label", None) for one in view.children]


async def test_a_yes_or_no_that_is_neither_is_refused_rather_than_guessed(bot):
    assert words.wanted_spotlight("yes", False) is True
    assert words.wanted_spotlight("no", True) is False
    assert words.wanted_spotlight("", True) is True
    assert words.wanted_spotlight("maybe", True) is None


async def test_linking_a_youtube_channel_to_a_row_and_unlinking_it_again(bot, cog):
    row = await a_row(bot)
    bot.cogs["YouTube"] = FakeYouTube("UCI3DTtB-a3fJPjKtQ5kYHfA", "Games Done Quick")

    outcome, fresh, said = await link_youtube(
        bot, bot.guild, FakeActor(), row["id"], "@GamesDoneQuick"
    )

    assert outcome == "linked" and "Games Done Quick" in said
    assert words.youtube_of(fresh) == "UCI3DTtB-a3fJPjKtQ5kYHfA"
    assert fresh["youtube_handle"] == "@GamesDoneQuick"

    gone, after, unsaid = await unlink_youtube(bot, bot.guild, FakeActor(), row["id"])

    assert gone == "unlinked" and "only its Twitch side" in unsaid
    assert words.youtube_of(after) is None
    second, _, refused = await unlink_youtube(bot, bot.guild, FakeActor(), row["id"])
    assert second == "not_linked" and "nothing to unlink" in refused


async def test_a_youtube_channel_that_cannot_be_resolved_is_refused_in_words(bot, cog):
    row = await a_row(bot)
    bot.cogs["YouTube"] = FakeYouTube(raises=RuntimeError("no such channel"))

    outcome, _fresh, said = await link_youtube(
        bot, bot.guild, FakeActor(), row["id"], "@nope"
    )

    assert outcome == "bad_channel" and "no such channel" in said
    assert words.youtube_of(await channel_by_id(bot.db, row["id"])) is None


async def test_with_no_youtube_half_running_the_refusal_says_so(bot, cog):
    row = await a_row(bot)

    outcome, _fresh, said = await link_youtube(
        bot, bot.guild, FakeActor(), row["id"], "@GamesDoneQuick"
    )

    assert outcome == "no_cog" and "YouTube half is not running" in said


async def test_the_twitch_sweep_never_ends_a_session_the_youtube_side_opened(bot, cog):
    await bot.store.set(GUILD, SPOTLIGHT_END_MISSES_KEY, 1)
    row = await a_row(bot)
    await cog.announce_info(
        bot.guild,
        row,
        StreamInfo(url="https://www.youtube.com/watch?v=abc", platform="YouTube"),
        "GamesDoneQuick",
    )
    session = await open_session(bot.db, row["id"])
    assert session is not None
    helix_of(bot)

    await cog.poll_once()
    await cog.poll_once()

    assert await open_session(bot.db, row["id"]) is not None
