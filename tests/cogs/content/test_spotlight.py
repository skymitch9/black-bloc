import json
from datetime import UTC, datetime, timedelta

import pytest

from black_bloc import pings
from black_bloc import spotlight as words
from black_bloc.cogs.content.golive import GoLive
from black_bloc.cogs.content.spotlight import (
    AddChannelModal,
    AddWindowButton,
    DatesButton,
    DatesModal,
    RemoveWindowPick,
    Spotlight,
    WindowModal,
    add_channel,
    add_ping_window,
    add_window,
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
    read_dates,
    recent_sessions,
    remove_ping_window,
    render_spotlight,
    run_spotlight_move,
    set_announce,
    set_announced,
    set_dates,
    set_ping_mode,
    set_spotlight,
    spotlight_channel,
    start_session,
    unlink_youtube,
    update_channel,
    windows_for,
)
from black_bloc.config import load_settings
from black_bloc.golive import StreamInfo, now_iso
from black_bloc.settings_store import (
    CHANNEL_OPTOUT_POST_KEY,
    DEFAULT_TIMEZONE_KEY,
    SPOTLIGHT_BUMP_CLEANUP_KEY,
    SPOTLIGHT_END_MISSES_KEY,
    SPOTLIGHT_MODE_KEY,
    SPOTLIGHT_SCHEDULED_WORD_KEY,
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
        if self.channel.edit_raises is not None:
            raise self.channel.edit_raises
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
        self.edit_raises = None

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


async def test_a_spotlight_rehearses_in_go_lives_own_home_when_one_is_set(bot, cog):
    await bot.store.set(GUILD, SPOTLIGHT_MODE_KEY, "shadow")
    await bot.store.set(GUILD, "golive_shadow_channel_id", LOG_CHANNEL)
    await a_row(bot)
    helix_of(bot, twitch_stream())
    await cog.poll_once()

    assert bot.guild.shadow.messages == []
    assert len(bot.guild.channels[LOG_CHANNEL].messages) == 1
    details = await details_of(bot.db, "golive.would_spotlight_announce")
    assert details["shadow_home"] == str(LOG_CHANNEL)


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


async def a_live_session(bot, cog, **helix):
    row = await a_row(bot)
    made = helix_of(bot, twitch_stream(), **helix)
    await cog.poll_once()
    return row, made


async def test_bump_now_names_the_game_being_played_now_and_refreshes_the_session(bot, cog):
    row, helix = await a_live_session(bot, cog)
    helix.streams = [twitch_stream(game="Hollow Knight", title="AGDQ 2027 — HK any%")]

    outcome, _ = await bump_now(bot, bot.guild, FakeActor(), row["id"])

    assert outcome == "bumped"
    assert "Hollow Knight" in bot.guild.channel.messages[1].content
    session = await open_session(bot.db, row["id"])
    assert session["game"] == "Hollow Knight" and session["title"] == "AGDQ 2027 — HK any%"
    said = await details_of(bot.db, "golive.spotlight_bumped")
    assert said["game"] == "Hollow Knight" and said["refreshed"] is True


async def test_bump_now_falls_back_to_the_stored_game_when_helix_cannot_answer(bot, cog):
    row, _helix = await a_live_session(bot, cog)
    helix_of(bot, raises=TwitchError("twitch unreachable"))

    outcome, _ = await bump_now(bot, bot.guild, FakeActor(), row["id"])

    assert outcome == "bumped" and "Celeste" in bot.guild.channel.messages[1].content
    assert (await open_session(bot.db, row["id"]))["game"] == "Celeste"
    assert (await details_of(bot.db, "golive.spotlight_bumped"))["refreshed"] is False


async def test_bump_now_falls_back_to_the_stored_game_with_no_helix_at_all(bot, cog):
    row, _helix = await a_live_session(bot, cog)
    bot.cogs["GoLive"] = FakeGoLive(None)

    outcome, _ = await bump_now(bot, bot.guild, FakeActor(), row["id"])

    assert outcome == "bumped" and "Celeste" in bot.guild.channel.messages[1].content


async def test_a_bump_carries_the_go_live_card_with_the_games_art(bot, cog):
    row, helix = await a_live_session(bot, cog)
    helix.streams = [twitch_stream(game="Hollow Knight", game_id="2")]
    helix.games = [TwitchGame("2", "Hollow Knight", "hk-art")]

    await bump_now(bot, bot.guild, FakeActor(), row["id"])

    card = bot.guild.channel.messages[1].embed
    assert card is not None and card.image.url == "hk-art"
    assert "GamesDoneQuick" in card.author.name
    said = await details_of(bot.db, "golive.spotlight_bumped")
    assert said["embed"]["game"] == "Hollow Knight" and said["embed"]["image"] == "hk-art"


async def test_a_bump_posts_the_sentence_alone_while_the_card_is_off(bot, cog):
    row, _helix = await a_live_session(bot, cog)
    await bot.store.set(GUILD, "golive_embed", False)

    await bump_now(bot, bot.guild, FakeActor(), row["id"])

    assert bot.guild.channel.messages[1].embed is None
    assert "embed" not in await details_of(bot.db, "golive.spotlight_bumped")


async def test_the_poller_bump_uses_the_stream_it_just_saw_and_asks_helix_once(bot, cog):
    row, helix = await a_live_session(bot, cog)
    helix.streams = [twitch_stream(game="Hollow Knight")]
    session = await open_session(bot.db, row["id"])
    await bot.db.conn.execute(
        "UPDATE spotlight_sessions SET started_at = ? WHERE id = ?",
        ((datetime.now(UTC) - timedelta(hours=4, minutes=1)).isoformat(), session["id"]),
    )
    await bot.db.conn.commit()
    calls = len(helix.stream_calls)

    await cog.poll_once()

    assert len(helix.stream_calls) == calls + 1
    assert "Hollow Knight" in bot.guild.channel.messages[1].content
    assert (await open_session(bot.db, row["id"]))["game"] == "Hollow Knight"


# --- the pinned announcement follows the game (owner, 2026-09-22) ------------------------------


async def age_session(bot, session_id, hours):
    await bot.db.conn.execute(
        "UPDATE spotlight_sessions SET started_at = ? WHERE id = ?",
        ((datetime.now(UTC) - timedelta(hours=hours)).isoformat(), session_id),
    )
    await bot.db.conn.commit()


async def test_a_poll_with_a_new_game_re_words_the_pinned_announcement_at_once(bot, cog):
    row, helix = await a_live_session(bot, cog)
    announcement = bot.guild.channel.messages[0]
    assert announcement.pinned is True and "Celeste" in announcement.content
    helix.streams = [twitch_stream(game="Hollow Knight", title="HK any%", game_id="2")]
    helix.games = [TwitchGame("2", "Hollow Knight", "hk-art")]

    await cog.poll_once()

    assert len(bot.guild.channel.messages) == 1
    assert "Hollow Knight" in announcement.content and "Celeste" not in announcement.content
    assert announcement.embed.image.url == "hk-art"
    assert announcement.embed.fields[0].value == "Hollow Knight"
    assert announcement.pinned is True
    said = await details_of(bot.db, "golive.spotlight_announcement_refreshed")
    assert said["game"] == "Hollow Knight" and said["title"] == "HK any%"
    assert said["message_id"] == str(announcement.id)
    assert said["embed"]["image"] == "hk-art"
    assert (await open_session(bot.db, row["id"]))["game"] == "Hollow Knight"


async def test_a_poll_with_the_same_game_edits_nothing_and_logs_nothing(bot, cog):
    await a_live_session(bot, cog)
    announcement = bot.guild.channel.messages[0]

    await cog.poll_once()
    await cog.poll_once()

    assert announcement.edits == []
    assert "golive.spotlight_announcement_refreshed" not in await kinds(bot.db)


async def test_a_due_bump_with_a_new_game_re_words_the_post_and_sends_the_reminder(bot, cog):
    row, helix = await a_live_session(bot, cog)
    session = await open_session(bot.db, row["id"])
    await age_session(bot, session["id"], 4.1)
    helix.streams = [twitch_stream(game="Hollow Knight")]

    await cog.poll_once()

    announcement, reminder = bot.guild.channel.messages
    assert "Hollow Knight" in announcement.content and len(announcement.edits) == 1
    assert "Hollow Knight" in reminder.content
    assert (await details_of(bot.db, "golive.spotlight_bumped"))["refreshed"] is True
    assert (await kinds(bot.db)).count("golive.spotlight_announcement_refreshed") == 1


async def test_bump_now_with_a_new_game_also_re_words_the_announcement(bot, cog):
    row, helix = await a_live_session(bot, cog)
    helix.streams = [twitch_stream(game="Hollow Knight")]

    await bump_now(bot, bot.guild, FakeActor(), row["id"])

    assert "Hollow Knight" in bot.guild.channel.messages[0].content
    assert "Hollow Knight" in bot.guild.channel.messages[1].content
    assert "golive.spotlight_announcement_refreshed" in await kinds(bot.db)


async def test_with_the_card_off_the_re_worded_post_carries_no_new_embed(bot, cog):
    await bot.store.set(GUILD, "golive_embed", False)
    _row, helix = await a_live_session(bot, cog)
    announcement = bot.guild.channel.messages[0]
    helix.streams = [twitch_stream(game="Hollow Knight")]

    await cog.poll_once()

    assert "Hollow Knight" in announcement.content
    assert "embed" not in announcement.edits[0] and announcement.embed is None
    assert "embed" not in await details_of(bot.db, "golive.spotlight_announcement_refreshed")


async def test_a_refused_edit_is_logged_loud_and_the_reminder_still_goes_out(bot, cog):
    row, helix = await a_live_session(bot, cog)
    announcement = bot.guild.channel.messages[0]
    bot.guild.channel.edit_raises = RuntimeError("Missing Access")
    helix.streams = [twitch_stream(game="Hollow Knight")]

    outcome, _ = await bump_now(bot, bot.guild, FakeActor(), row["id"])

    assert outcome == "bumped" and len(bot.guild.channel.messages) == 2
    assert "Celeste" in announcement.content and announcement.pinned is True
    failed = await details_of(bot.db, "golive.spotlight_announcement_refresh_failed")
    assert failed["game"] == "Hollow Knight" and "Missing Access" in failed["reason"]
    assert "golive.spotlight_announcement_refreshed" not in await kinds(bot.db)


async def test_following_the_game_never_pins_or_unpins_anything(bot, cog):
    row, helix = await a_live_session(bot, cog)
    announcement = bot.guild.channel.messages[0]
    pins, before = list(announcement.pins), await kinds(bot.db)
    helix.streams = [twitch_stream(game="Hollow Knight")]
    await cog.poll_once()
    helix.streams = [twitch_stream(game="Hades")]
    await bump_now(bot, bot.guild, FakeActor(), row["id"])

    assert announcement.pins == pins and announcement.unpins == []
    assert announcement.pinned is True and len(announcement.edits) == 2
    after = (await kinds(bot.db))[len(before) :]
    assert not {"golive.spotlight_pinned", "golive.spotlight_unpinned"} & set(after)


async def test_a_spotlight_off_announcement_follows_the_game_too(bot, cog):
    row = await a_row(bot, spotlight=False)
    helix = helix_of(bot, twitch_stream())
    await cog.poll_once()
    announcement = bot.guild.channel.messages[0]
    assert announcement.pinned is False
    helix.streams = [twitch_stream(game="Hollow Knight")]

    await cog.poll_once()

    assert "Hollow Knight" in announcement.content and announcement.pinned is False
    assert announcement.pins == []
    assert (await open_session(bot.db, row["id"]))["game"] == "Hollow Knight"


async def test_a_shadow_announcement_keeps_its_rehearsal_line_when_re_worded(bot, cog):
    await bot.store.set(GUILD, SPOTLIGHT_MODE_KEY, "shadow")
    _row, helix = await a_live_session(bot, cog)
    announcement = bot.guild.shadow.messages[0]
    first_line = announcement.content.split("\n", 1)[0]
    helix.streams = [twitch_stream(game="Hollow Knight")]

    await cog.poll_once()

    assert "Hollow Knight" in announcement.content
    assert announcement.content.startswith(first_line + "\n")
    assert announcement.content.count(first_line) == 1


async def test_the_twitch_poller_leaves_a_youtube_sessions_announcement_alone(bot, cog):
    row = await a_row(bot)
    await cog.announce_info(
        bot.guild,
        row,
        StreamInfo(url="https://www.youtube.com/watch?v=abc", platform="YouTube", game="Celeste"),
        "GamesDoneQuick",
    )
    announcement = bot.guild.channel.messages[0]
    helix_of(bot, twitch_stream(game="Hollow Knight"))

    await cog.poll_once()

    assert announcement.edits == []
    assert "golive.spotlight_announcement_refreshed" not in await kinds(bot.db)


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
    said = await details_of(bot.db, "golive.channel_announced")
    assert said["spotlight"] is False and said["pin"] is False
    assert "golive.spotlight_announced" not in await kinds(bot.db)
    assert await open_session(bot.db, row["id"]) is not None


async def test_a_spotlight_off_announcement_is_logged_as_a_channel_announcement(bot, cog):
    """Owner, 2026-09-21: "why is gdq being spotlighted in the logs channel? its spot light
    isnt on" — the kind is the log embed's title, so the spotlight word there was a lie."""
    await a_row(bot, spotlight=False)
    helix_of(bot, twitch_stream())

    await cog.poll_once()

    said = await kinds(bot.db)
    assert "golive.channel_announced" in said
    assert not [kind for kind in said if "spotlight_announced" in kind]
    detail = await details_of(bot.db, "golive.channel_announced")
    assert detail["spotlight"] is False and detail["announce"] is True
    assert detail["platform"] == "Twitch"


async def test_a_spotlight_off_end_is_a_channel_end_and_never_a_spotlight_one(bot, cog):
    await bot.store.set(GUILD, SPOTLIGHT_END_MISSES_KEY, 1)
    await a_row(bot, spotlight=False)
    helix_of(bot, twitch_stream())
    await cog.poll_once()
    helix_of(bot)

    await cog.poll_once()

    said = await kinds(bot.db)
    assert "golive.channel_ended" in said and "golive.spotlight_ended" not in said
    ended = await details_of(bot.db, "golive.channel_ended")
    assert ended["reason"] == words.ENDED and ended["spotlight"] is False


async def test_the_spotlight_words_stay_while_the_spotlight_is_on(bot, cog):
    await bot.store.set(GUILD, SPOTLIGHT_END_MISSES_KEY, 1)
    await a_row(bot)
    helix_of(bot, twitch_stream())
    await cog.poll_once()
    helix_of(bot)

    await cog.poll_once()

    said = await kinds(bot.db)
    assert "golive.spotlight_announced" in said and "golive.spotlight_ended" in said
    assert not [kind for kind in said if "channel_announced" in kind]
    assert "golive.channel_ended" not in said


async def test_shadow_on_a_spotlight_off_channel_says_would_channel_announce(bot, cog):
    await bot.store.set(GUILD, SPOTLIGHT_MODE_KEY, "shadow")
    await a_row(bot, spotlight=False)
    helix_of(bot, twitch_stream())

    await cog.poll_once()

    said = await kinds(bot.db)
    assert "golive.would_channel_announce" in said
    assert "golive.would_spotlight_announce" not in said
    assert "golive.channel_announced" not in said


async def test_a_spotlight_taken_off_mid_stream_ends_under_the_kind_the_row_says_now(bot, cog):
    """The kind is read off the row at each moment, so a mid-stream toggle splits the pair."""
    await bot.store.set(GUILD, SPOTLIGHT_END_MISSES_KEY, 1)
    row = await a_row(bot)
    helix = helix_of(bot, twitch_stream())
    await cog.poll_once()
    await run_spotlight_move(bot, bot.guild, FakeActor(), row["id"], "spotlight_off")

    helix.streams = []
    await cog.poll_once()

    said = await kinds(bot.db)
    assert "golive.spotlight_announced" in said
    assert "golive.channel_ended" in said and "golive.spotlight_ended" not in said


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


async def a_live_row(bot, cog, **fields):
    """A channel with an announcement out there, pinned, and its reminder already due."""
    row = await a_row(bot, **fields)
    helix = helix_of(bot, twitch_stream())
    await cog.poll_once()
    session = await open_session(bot.db, row["id"])
    await bot.db.conn.execute(
        "UPDATE spotlight_sessions SET started_at = ? WHERE id = ?",
        ((datetime.now(UTC) - timedelta(hours=5)).isoformat(), session["id"]),
    )
    await bot.db.conn.commit()
    return row, helix, bot.guild.channel.messages[0]


async def test_opting_a_live_channel_out_ends_the_stream_that_is_out_there(bot, cog):
    """The defect: ESA was announced and pinned at boot, opted out, and nothing ended it
    because a 24/7 rerun channel never reads offline."""
    row, helix, announcement = await a_live_row(bot, cog)
    assert announcement.pinned is True

    said, picked = await run_spotlight_move(bot, bot.guild, FakeActor(), row["id"], "opt_out")

    assert picked is True and "is opted out" in said
    assert "edited to say the stream has ended" in said
    assert announcement.pinned is False and announcement.unpins == [words.UNPIN_REASON]
    assert "has ended" in announcement.content
    assert await open_session(bot.db, row["id"]) is None
    ended = await details_of(bot.db, "golive.spotlight_ended")
    assert ended["reason"] == words.OPTED_OUT_ENDED and ended["post"] == "end"
    assert (await details_of(bot.db, "golive.spotlight_unpinned"))["because"] == (
        words.OPTED_OUT_ENDED
    )

    await cog.poll_once()
    assert len(bot.guild.channel.messages) == 1, "a reminder went out after the opt-out"
    assert helix.streams, "the channel is still live; only the announcement ended"


async def test_the_optout_post_key_deletes_the_announcement_instead(bot, cog):
    await bot.store.set(GUILD, CHANNEL_OPTOUT_POST_KEY, "delete")
    row, _helix, announcement = await a_live_row(bot, cog)

    said, _ = await run_spotlight_move(bot, bot.guild, FakeActor(), row["id"], "opt_out")

    assert "has been deleted" in said
    assert announcement.deleted is True and bot.guild.channel.messages == []
    assert await open_session(bot.db, row["id"]) is None
    assert "golive.spotlight_post_deleted" in await kinds(bot.db)
    assert (await details_of(bot.db, "golive.spotlight_ended"))["post"] == "delete"


async def test_the_optout_post_key_leaves_the_words_exactly_as_posted(bot, cog):
    await bot.store.set(GUILD, CHANNEL_OPTOUT_POST_KEY, "leave")
    row, _helix, announcement = await a_live_row(bot, cog)
    posted = announcement.content

    said, _ = await run_spotlight_move(bot, bot.guild, FakeActor(), row["id"], "opt_out")

    assert "left exactly as it was posted" in said
    assert announcement.deleted is False and announcement.content == posted
    assert announcement.pinned is False
    assert await open_session(bot.db, row["id"]) is None
    assert (await details_of(bot.db, "golive.spotlight_ended"))["post"] == "leave"


async def test_opting_out_with_nothing_live_says_the_plain_sentence(bot, cog):
    row = await a_row(bot)

    said, _ = await run_spotlight_move(bot, bot.guild, FakeActor(), row["id"], "opt_out")

    assert "is opted out" in said
    assert "announcement that was out" not in said
    assert "golive.spotlight_ended" not in await kinds(bot.db)


async def test_opting_out_twice_settles_the_announcement_once(bot, cog):
    row, _helix, announcement = await a_live_row(bot, cog)
    await run_spotlight_move(bot, bot.guild, FakeActor(), row["id"], "opt_out")

    said, _ = await run_spotlight_move(bot, bot.guild, FakeActor(), row["id"], "opt_out")

    assert "announcement that was out" not in said
    assert (await kinds(bot.db)).count("golive.spotlight_ended") == 1
    assert announcement.unpins == [words.UNPIN_REASON]


async def test_taking_the_spotlight_off_a_live_channel_unpins_it_and_leaves_it_running(bot, cog):
    row, helix, announcement = await a_live_row(bot, cog)
    posted = announcement.content

    said, _ = await run_spotlight_move(
        bot, bot.guild, FakeActor(), row["id"], "spotlight_off"
    )

    assert "like anybody else" in said and "has been unpinned" in said
    assert announcement.pinned is False and announcement.content == posted
    assert await open_session(bot.db, row["id"]) is not None
    assert (await details_of(bot.db, "golive.spotlight_unpinned"))["because"] == (
        words.SPOTLIGHT_OFF_BECAUSE
    )

    await cog.poll_once()
    assert len(bot.guild.channel.messages) == 1, "a bump went out with the spotlight off"

    helix.streams = []
    await cog.poll_once()
    await cog.poll_once()
    assert await open_session(bot.db, row["id"]) is None
    assert "has ended" in announcement.content


async def a_plain_live_row(bot, cog, **fields):
    """GDQ on 2026-09-22: spotlight off, announced like a member's, so nothing pinned."""
    row = await a_row(bot, spotlight=False, **fields)
    helix_of(bot, twitch_stream())
    await cog.poll_once()
    announcement = bot.guild.channel.messages[0]
    assert announcement.pinned is False
    return row, announcement


async def test_turning_the_spotlight_on_mid_stream_pins_the_live_announcement(bot, cog):
    row, announcement = await a_plain_live_row(bot, cog)

    said, _ = await run_spotlight_move(bot, bot.guild, FakeActor(), row["id"], "spotlight_on")

    assert announcement.pinned is True and announcement.pins == [words.PIN_REASON]
    assert words.PINNED_NOW in said and "is spotlighted" in said
    assert (await details_of(bot.db, "golive.spotlight_pinned"))["because"] == (
        words.SPOTLIGHT_ON_BECAUSE
    )
    assert await open_session(bot.db, row["id"]) is not None


async def test_turning_the_spotlight_on_leaves_a_row_whose_pin_is_off_unpinned(bot, cog):
    row, announcement = await a_plain_live_row(bot, cog)
    await update_channel(bot.db, row["id"], pin=0)

    said, _ = await run_spotlight_move(bot, bot.guild, FakeActor(), row["id"], "spotlight_on")

    assert announcement.pinned is False and announcement.pins == []
    assert words.PINNED_NOW not in said
    assert "golive.spotlight_pinned" not in await kinds(bot.db)


async def test_turning_the_spotlight_on_over_an_already_pinned_post_changes_nothing(bot, cog):
    row, announcement = await a_plain_live_row(bot, cog)
    announcement.pinned = True

    said, _ = await run_spotlight_move(bot, bot.guild, FakeActor(), row["id"], "spotlight_on")

    assert announcement.pins == [] and announcement.pinned is True
    assert words.PINNED_NOW not in said
    assert "golive.spotlight_pinned" not in await kinds(bot.db)


async def test_turning_the_spotlight_on_after_the_stream_unpins_a_stale_pin(bot, cog):
    row, _helix, announcement = await a_live_row(bot, cog)
    await set_spotlight(bot, bot.guild, FakeActor(), row["id"], False)
    announcement.pinned = True
    session = await open_session(bot.db, row["id"])
    await end_session(bot.db, session["id"], now_iso())

    said, _ = await run_spotlight_move(bot, bot.guild, FakeActor(), row["id"], "spotlight_on")

    assert announcement.pinned is False
    assert words.UNPINNED_ENDED_NOW in said
    assert (await details_of(bot.db, "golive.spotlight_unpinned"))["because"] == (
        words.SPOTLIGHT_ON_BECAUSE
    )


async def test_turning_the_spotlight_on_with_nothing_out_there_settles_nothing(bot, cog):
    row = await a_row(bot, spotlight=False)

    fresh, settled = await set_spotlight(bot, bot.guild, FakeActor(), row["id"], True)

    assert settled is None and words.is_spotlit(fresh)
    assert words.spotlight_said(fresh, settled) == words.SPOTLIT_SAID.format(login=GDQ)
    assert "golive.spotlight_pinned" not in await kinds(bot.db)
    assert "golive.spotlight_unpinned" not in await kinds(bot.db)


async def test_a_pin_discord_refuses_on_the_flip_is_said_in_words_and_the_row_still_moves(
    bot, cog
):
    row, announcement = await a_plain_live_row(bot, cog)
    bot.guild.channel.pin_raises = RuntimeError("Forbidden")

    said, _ = await run_spotlight_move(bot, bot.guild, FakeActor(), row["id"], "spotlight_on")

    assert "could not be pinned" in said and "Manage Messages" in said
    assert words.is_spotlit(await channel_by_id(bot.db, row["id"]))
    assert announcement.pinned is False
    assert (await details_of(bot.db, "golive.spotlight_pin_failed"))["because"] == (
        words.SPOTLIGHT_ON_BECAUSE
    )


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


# --- the owner's date range (2026-09-22) ------------------------------------------------------


def ahead(days):
    return (datetime.now(UTC) + timedelta(days=days)).isoformat()


def behind(days):
    return (datetime.now(UTC) - timedelta(days=days)).isoformat()


async def test_a_scheduled_row_is_not_announced_before_its_start(bot, cog):
    row = await a_row(bot, starts_at=ahead(3))
    helix_of(bot, twitch_stream())
    await cog.poll_once()
    assert await open_session(bot.db, row["id"]) is None
    assert bot.guild.channels[CHANNEL].messages == []
    assert "golive.spotlight_announced" not in await kinds(bot.db)


async def test_the_same_row_is_announced_on_the_first_tick_after_its_start(bot, cog):
    row = await a_row(bot, starts_at=ahead(3))
    helix_of(bot, twitch_stream())
    await cog.poll_once()
    assert await open_session(bot.db, row["id"]) is None

    await update_channel(bot.db, row["id"], starts_at=behind(1))
    await cog.poll_once()
    assert await open_session(bot.db, row["id"]) is not None
    assert "golive.spotlight_announced" in await kinds(bot.db)


async def test_a_start_that_passes_leaves_one_routine_started_row(bot, cog):
    row = await a_row(bot, starts_at=ahead(3))
    helix_of(bot)
    await cog.poll_once()
    assert "golive.spotlight_started" not in await kinds(bot.db)

    await update_channel(bot.db, row["id"], starts_at=behind(1))
    await cog.poll_once()
    await cog.poll_once()
    assert (await kinds(bot.db)).count("golive.spotlight_started") == 1
    assert (await details_of(bot.db, "golive.spotlight_started"))["login"] == GDQ


async def test_a_boot_that_meets_an_already_started_row_says_nothing(bot, cog):
    await a_row(bot, starts_at=behind(1))
    helix_of(bot)
    await cog.poll_once()
    assert "golive.spotlight_started" not in await kinds(bot.db)


async def test_a_start_set_mid_stream_never_strands_the_announcement_that_is_out(bot, cog):
    row = await a_row(bot)
    helix_of(bot, twitch_stream())
    await cog.poll_once()
    assert await open_session(bot.db, row["id"]) is not None

    await update_channel(bot.db, row["id"], starts_at=ahead(5))
    await bot.store.set(GUILD, SPOTLIGHT_END_MISSES_KEY, 1)
    helix_of(bot)
    await cog.poll_once()
    assert (await open_session(bot.db, row["id"])) is None


async def test_the_added_row_carries_its_start_into_the_log(bot):
    outcome, row = await spotlight_channel(
        bot, bot.guild, FakeActor(), "esamarathon", starts_at=ahead(2), expires_at=ahead(9)
    )
    assert outcome == "added" and row["starts_at"] is not None
    said = await details_of(bot.db, "golive.spotlight_added")
    assert said["starts_at"] == row["starts_at"]


async def test_set_dates_stores_both_and_says_the_row_is_scheduled(bot, cog):
    row = await a_row(bot)
    outcome, fresh, said = await set_dates(
        bot, bot.guild, FakeActor(), row["id"], ahead(3), ahead(10)
    )
    assert outcome == "dated"
    assert fresh["starts_at"] is not None and fresh["expires_at"] is not None
    assert "before that start" in said


async def test_a_blank_start_and_a_blank_end_mean_now_and_for_ever(bot, cog):
    row = await a_row(bot, starts_at=ahead(3), expires_at=ahead(10))
    outcome, fresh, _ = await set_dates(bot, bot.guild, FakeActor(), row["id"], None, None)
    assert outcome == "dated"
    assert fresh["starts_at"] is None and fresh["expires_at"] is None
    assert words.is_scheduled(fresh) is False


async def test_an_end_before_the_start_is_refused_in_words_and_stores_nothing(bot, cog):
    row = await a_row(bot, starts_at=ahead(3), expires_at=ahead(10))
    outcome, _, said = await set_dates(
        bot, bot.guild, FakeActor(), row["id"], ahead(8), ahead(4)
    )
    assert outcome == words.END_BEFORE_START
    assert "ends before it starts" in said
    fresh = await channel_by_id(bot.db, row["id"])
    assert fresh["starts_at"] == row["starts_at"] and fresh["expires_at"] == row["expires_at"]


async def test_the_two_boxes_are_read_in_the_guilds_own_zone(bot):
    await bot.store.set(GUILD, DEFAULT_TIMEZONE_KEY, "America/Phoenix")
    start, end, refusal = await read_dates(
        bot, bot.guild, FakeActor(), "2026-09-30 19:00", "2026-10-01 19:00"
    )
    assert refusal is None
    assert start == "2026-10-01T02:00:00+00:00" and end == "2026-10-02T02:00:00+00:00"


async def test_a_date_nobody_can_read_is_a_sentence_not_a_stored_row(bot):
    start, end, refusal = await read_dates(bot, bot.guild, FakeActor(), "next tuesday", "")
    assert start is None and end is None
    assert refusal is not None and "next tuesday" in refusal


async def test_the_end_box_still_takes_a_number_of_days(bot):
    _, end, refusal = await read_dates(bot, bot.guild, FakeActor(), "", "7")
    assert refusal is None and end is not None


async def test_extending_a_scheduled_row_is_refused_when_it_would_land_before_the_start(bot, cog):
    _, row = await spotlight_channel(
        bot, bot.guild, FakeActor(), "esamarathon", starts_at=ahead(40), expires_at=ahead(60)
    )
    await update_channel(bot.db, row["id"], expires_at=ahead(1))
    said, kept = await run_spotlight_move(bot, bot.guild, FakeActor(), row["id"], "extend")
    assert "ends before it starts" in said and kept is True


async def test_letting_a_scheduled_row_expire_is_refused_rather_than_going_backwards(bot, cog):
    row = await a_row(bot, starts_at=ahead(40))
    said, _ = await run_spotlight_move(bot, bot.guild, FakeActor(), row["id"], "expire")
    assert "ends before it starts" in said
    assert (await channel_by_id(bot.db, row["id"]))["expires_at"] is None


# --- the panel, the button and the two modals -------------------------------------------------


async def test_every_row_offers_set_dates(bot, cog):
    row = await a_row(bot)
    interaction = FakeInteraction(bot, FakeActor(), bot.guild)
    await render_spotlight(interaction, row["id"])
    assert words.SPOTLIGHT_DATES_BUTTON in interaction.labels()


async def test_the_set_dates_button_opens_a_modal_filled_with_what_is_stored(bot, cog):
    await bot.store.set(GUILD, DEFAULT_TIMEZONE_KEY, "UTC")
    row = await a_row(
        bot, starts_at="2026-09-30T19:00:00+00:00", expires_at="2026-10-05T19:00:00+00:00"
    )
    interaction = FakeInteraction(bot, FakeActor(), bot.guild)
    await DatesButton(row["id"]).callback(interaction)
    modal = interaction.response.modals[-1]
    assert modal.starts.default == "2026-09-30 19:00"
    assert modal.ends.default == "2026-10-05 19:00"


async def test_the_dates_modal_round_trips_what_was_typed(bot, cog):
    await bot.store.set(GUILD, DEFAULT_TIMEZONE_KEY, "UTC")
    row = await a_row(bot)
    modal = DatesModal(row["id"], "Starts", "Ends", "", "")
    modal.starts._value = "2026-11-01 09:00"
    modal.ends._value = "2026-11-08 09:00"
    interaction = FakeInteraction(bot, FakeActor(), bot.guild)
    await modal.on_submit(interaction)
    fresh = await channel_by_id(bot.db, row["id"])
    assert fresh["starts_at"] == "2026-11-01T09:00:00+00:00"
    assert fresh["expires_at"] == "2026-11-08T09:00:00+00:00"
    assert GDQ in (interaction.sent or "")


async def test_the_dates_modal_refuses_a_backwards_range_and_changes_nothing(bot, cog):
    await bot.store.set(GUILD, DEFAULT_TIMEZONE_KEY, "UTC")
    row = await a_row(bot)
    modal = DatesModal(row["id"], "Starts", "Ends", "", "")
    modal.starts._value = "2026-11-08 09:00"
    modal.ends._value = "2026-11-01 09:00"
    interaction = FakeInteraction(bot, FakeActor(), bot.guild)
    await modal.on_submit(interaction)
    assert "ends before it starts" in (interaction.sent or "")
    fresh = await channel_by_id(bot.db, row["id"])
    assert fresh["starts_at"] is None and fresh["expires_at"] is None


async def test_the_add_modal_takes_a_start_and_an_end_instead_of_days(bot, cog):
    await bot.store.set(GUILD, DEFAULT_TIMEZONE_KEY, "UTC")
    modal = AddChannelModal(None, bot, bot.guild)
    modal.channel._value = "esamarathon"
    modal.spotlight._value = "yes"
    modal.youtube._value = ""
    modal.starts._value = "2026-11-01 09:00"
    modal.ends._value = "2026-11-08 09:00"
    interaction = FakeInteraction(bot, FakeActor(), bot.guild)
    await modal.on_submit(interaction)
    row = await channel_by_login(bot.db, GUILD, "esamarathon")
    assert row["starts_at"] == "2026-11-01T09:00:00+00:00"
    assert row["expires_at"] == "2026-11-08T09:00:00+00:00"


async def test_the_add_modal_refuses_a_backwards_range_and_adds_nothing(bot, cog):
    await bot.store.set(GUILD, DEFAULT_TIMEZONE_KEY, "UTC")
    modal = AddChannelModal(None, bot, bot.guild)
    modal.channel._value = "esamarathon"
    modal.spotlight._value = "yes"
    modal.youtube._value = ""
    modal.starts._value = "2026-11-08 09:00"
    modal.ends._value = "2026-11-01 09:00"
    interaction = FakeInteraction(bot, FakeActor(), bot.guild)
    await modal.on_submit(interaction)
    assert "ends before it starts" in (interaction.sent or "")
    assert await channel_by_login(bot.db, GUILD, "esamarathon") is None


async def test_the_add_modal_refuses_an_unreadable_date_by_name(bot, cog):
    modal = AddChannelModal(None, bot, bot.guild)
    modal.channel._value = "esamarathon"
    modal.spotlight._value = ""
    modal.youtube._value = ""
    modal.starts._value = "next tuesday"
    modal.ends._value = ""
    interaction = FakeInteraction(bot, FakeActor(), bot.guild)
    await modal.on_submit(interaction)
    assert "next tuesday" in (interaction.sent or "")
    assert await channel_by_login(bot.db, GUILD, "esamarathon") is None


async def test_the_panel_marks_a_scheduled_row_with_the_key_the_owner_can_change(bot, cog):
    await a_row(bot, starts_at=ahead(3))
    interaction = FakeInteraction(bot, FakeActor(), bot.guild)
    await render_spotlight(interaction)
    assert "scheduled" in interaction.words

    await bot.store.set(GUILD, SPOTLIGHT_SCHEDULED_WORD_KEY, "not yet")
    again = FakeInteraction(bot, FakeActor(), bot.guild)
    await render_spotlight(again)
    assert "not yet" in again.words


# --- ping windows: a spotlight split from its ping (owner, 2026-09-25) --------------------------


async def pinging_row(bot, mode="events"):
    await bot.store.set(GUILD, "pings_mode", "on")
    await bot.store.set(GUILD, "golive_ping_role_id", PING_ROLE)
    bot.guild.roles.append(FakeRole(PING_ROLE, "Events"))
    row = await a_row(bot)
    role_id = await a_fan_role(bot, row)
    await set_ping_mode(bot, bot.guild, FakeActor(), row["id"], mode)
    return await channel_by_id(bot.db, row["id"]), role_id


async def a_window(bot, row, start_hours, end_hours, **fields):
    now = datetime.now(UTC)
    return await add_window(
        bot.db,
        GUILD,
        row["id"],
        (now + timedelta(hours=start_hours)).isoformat(),
        (now + timedelta(hours=end_hours)).isoformat(),
        **fields,
    )


async def overdue_bump(bot, row, hours=9):
    session = await open_session(bot.db, row["id"])
    await bot.db.conn.execute(
        "UPDATE spotlight_sessions SET started_at = ?, last_bump_at = ? WHERE id = ?",
        (
            (datetime.now(UTC) - timedelta(hours=hours)).isoformat(),
            (datetime.now(UTC) - timedelta(hours=hours)).isoformat(),
            session["id"],
        ),
    )
    await bot.db.conn.commit()


async def test_an_events_row_announces_with_no_mention_outside_a_window(bot, cog):
    row, _ = await pinging_row(bot)
    await a_window(bot, row, 24, 48)
    helix_of(bot, twitch_stream())
    await cog.poll_once()
    posted = bot.guild.channel.messages[0]
    assert "<@&" not in posted.content
    assert posted.kwargs["allowed_mentions"].roles is False
    said = await details_of(bot.db, "golive.spotlight_announced")
    assert said["pinged"] is False and said["ping_mode"] == "events"
    assert said["fan_role_id"] is None
    assert (await open_session(bot.db, row["id"]))["pinging_last"] == 0


async def test_an_events_row_announces_with_both_roles_inside_a_window(bot, cog):
    row, role_id = await pinging_row(bot)
    await a_window(bot, row, -1, 5)
    helix_of(bot, twitch_stream())
    await cog.poll_once()
    posted = bot.guild.channel.messages[0]
    assert posted.content.startswith(f"<@&{PING_ROLE}> <@&{role_id}> ")
    assert [one.id for one in posted.kwargs["allowed_mentions"].roles] == [PING_ROLE, role_id]
    assert (await details_of(bot.db, "golive.spotlight_announced"))["pinged"] is True


async def test_never_mentions_nothing_even_inside_a_window_and_still_pins(bot, cog):
    row, _ = await pinging_row(bot, "never")
    await a_window(bot, row, -1, 5)
    helix_of(bot, twitch_stream())
    await cog.poll_once()
    posted = bot.guild.channel.messages[0]
    assert "<@&" not in posted.content
    assert posted.kwargs["allowed_mentions"].roles is False
    assert posted.pinned is True


async def test_always_is_the_default_and_pings_as_it_did(bot, cog):
    row, role_id = await pinging_row(bot, "always")
    assert row["ping_mode"] == "always"
    helix_of(bot, twitch_stream())
    await cog.poll_once()
    assert bot.guild.channel.messages[0].content.startswith(f"<@&{PING_ROLE}> <@&{role_id}> ")
    assert (await open_session(bot.db, row["id"]))["pinging_last"] == 1


async def test_a_new_row_takes_the_default_ping_mode(bot):
    await bot.store.set(GUILD, "spotlight_ping_mode_default", "events")
    row = await a_row(bot, "esamarathon")
    assert row["ping_mode"] == "events"
    assert (await details_of(bot.db, "golive.spotlight_added"))["ping_mode"] == "events"


async def test_a_bump_under_events_pings_only_in_a_window_and_only_with_the_key(bot, cog):
    row, role_id = await pinging_row(bot)
    window_id = await a_window(bot, row, -1, 5)
    helix_of(bot, twitch_stream())
    await cog.poll_once()
    await overdue_bump(bot, row)
    await cog.poll_once()
    quiet = bot.guild.channel.messages[1]
    assert "<@&" not in quiet.content
    assert (await details_of(bot.db, "golive.spotlight_bumped"))["pinged"] is False

    await bot.store.set(GUILD, "spotlight_bump_pings", True)
    await overdue_bump(bot, row)
    await cog.poll_once()
    loud = bot.guild.channel.messages[2]
    assert loud.content.startswith(f"<@&{PING_ROLE}> <@&{role_id}> ")
    said = await details_of(bot.db, "golive.spotlight_bumped")
    assert said["pinged"] is True and said["ping_mode"] == "events"

    await remove_ping_window(bot, bot.guild, FakeActor(), row["id"], window_id)
    await overdue_bump(bot, row)
    await cog.poll_once()
    closed = bot.guild.channel.messages[3]
    assert "<@&" not in closed.content
    assert closed.kwargs["allowed_mentions"].roles is False


async def test_a_window_opening_on_a_live_channel_posts_one_pinged_reminder(bot, cog):
    row, role_id = await pinging_row(bot)
    helix_of(bot, twitch_stream())
    await cog.poll_once()
    assert len(bot.guild.channel.messages) == 1

    window_id = await a_window(bot, row, -1, 5, note="AGDQ 2027")
    await cog.poll_once()
    assert len(bot.guild.channel.messages) == 2
    reminder = bot.guild.channel.messages[1]
    assert reminder.content.startswith(f"<@&{PING_ROLE}> <@&{role_id}> ")
    assert reminder.pinned is False
    said = await details_of(bot.db, "golive.spotlight_bumped")
    assert said["because"] == "window_opened" and said["window_id"] == window_id
    assert said["pinged"] is True
    session = await open_session(bot.db, row["id"])
    assert session["pinging_last"] == 1 and session["last_bump_at"] is not None

    await cog.poll_once()
    assert len(bot.guild.channel.messages) == 2


async def test_a_window_opening_on_a_live_channel_with_spotlight_off_posts_nothing(bot, cog):
    row, _ = await pinging_row(bot)
    await set_spotlight(bot, bot.guild, FakeActor(), row["id"], False)
    helix_of(bot, twitch_stream())
    await cog.poll_once()
    assert len(bot.guild.channel.messages) == 1

    await a_window(bot, row, -1, 5, note="AGDQ 2027")
    await cog.poll_once()
    assert len(bot.guild.channel.messages) == 1
    session = await open_session(bot.db, row["id"])
    assert session["pinging_last"] == 1


async def test_the_window_reminder_ignores_the_bump_pings_key_but_honours_its_own(bot, cog):
    await bot.store.set(GUILD, "spotlight_window_open_reminder", False)
    row, _ = await pinging_row(bot)
    helix_of(bot, twitch_stream())
    await cog.poll_once()
    await a_window(bot, row, -1, 5)
    await cog.poll_once()
    assert len(bot.guild.channel.messages) == 1
    assert (await open_session(bot.db, row["id"]))["pinging_last"] == 1


async def test_a_restart_mid_window_never_posts_the_reminder_again(bot, cog):
    row, _ = await pinging_row(bot)
    helix_of(bot, twitch_stream())
    await cog.poll_once()
    await a_window(bot, row, -1, 5)

    again = Spotlight(bot)
    bot.cogs["Spotlight"] = again
    await again.reconcile_open_sessions()
    assert (await open_session(bot.db, row["id"]))["pinging_last"] == 1
    await again.poll_once()
    assert len(bot.guild.channel.messages) == 1


async def test_a_session_from_before_the_migration_is_read_once_without_posting(bot, cog):
    row, _ = await pinging_row(bot)
    await a_window(bot, row, -1, 5)
    helix_of(bot, twitch_stream())
    await cog.poll_once()
    session = await open_session(bot.db, row["id"])
    await bot.db.conn.execute(
        "UPDATE spotlight_sessions SET pinging_last = NULL WHERE id = ?", (session["id"],)
    )
    await bot.db.conn.commit()
    await cog.poll_once()
    assert len(bot.guild.channel.messages) == 1
    assert (await open_session(bot.db, row["id"]))["pinging_last"] == 1


async def test_changing_the_mode_never_posts_by_itself(bot, cog):
    row, _ = await pinging_row(bot, "never")
    await a_window(bot, row, -1, 5)
    helix_of(bot, twitch_stream())
    await cog.poll_once()
    outcome, fresh, said = await set_ping_mode(bot, bot.guild, FakeActor(), row["id"], "events")
    assert outcome == "set" and fresh["ping_mode"] == "events"
    assert "open until" in said
    await cog.poll_once()
    assert len(bot.guild.channel.messages) == 1
    logged = await details_of(bot.db, "golive.spotlight_ping_mode_set")
    assert logged["from"] == "never" and logged["to"] == "events" and logged["via"] == "discord"


async def test_an_unknown_ping_mode_is_refused_in_words_and_changes_nothing(bot):
    row = await a_row(bot)
    outcome, _, said = await set_ping_mode(bot, bot.guild, FakeActor(), row["id"], "sometimes")
    assert outcome == "bad_mode" and "sometimes" in said and "`events`" in said
    assert (await channel_by_id(bot.db, row["id"]))["ping_mode"] == "always"


async def test_a_window_needs_both_ends_in_the_right_order(bot):
    await bot.store.set(GUILD, DEFAULT_TIMEZONE_KEY, "UTC")
    row = await a_row(bot)
    outcome, _, window, said = await add_ping_window(
        bot, bot.guild, FakeActor(), row["id"], "2027-01-12T15:00:00+00:00", None
    )
    assert outcome == "needs_both" and window is None and "start AND an end" in said
    outcome, _, _, said = await add_ping_window(
        bot,
        bot.guild,
        FakeActor(),
        row["id"],
        "2027-01-19T23:00:00+00:00",
        "2027-01-12T15:00:00+00:00",
    )
    assert outcome == "end_before_start" and "ends before it starts" in said
    assert await windows_for(bot.db, row["id"]) == []
    outcome, _, window, said = await add_ping_window(
        bot,
        bot.guild,
        FakeActor(),
        row["id"],
        "2027-01-12T15:00:00+00:00",
        "2027-01-19T23:00:00+00:00",
        "AGDQ 2027",
    )
    assert outcome == "added" and window["note"] == "AGDQ 2027" and window["source"] == "staff"
    assert "12 Jan 15:00 to 19 Jan 23:00 (AGDQ 2027)" in said
    assert "right now it pings always" in said
    assert (await details_of(bot.db, "golive.spotlight_window_added"))["window_id"] == window["id"]


async def test_a_marathon_window_is_refused_in_words_and_a_staff_one_goes(bot):
    row = await a_row(bot)
    marathon = await a_window(bot, row, 24, 48, source="marathon", source_id=9)
    staff = await a_window(bot, row, 72, 96)
    outcome, _, _, said = await remove_ping_window(bot, bot.guild, FakeActor(), row["id"], marathon)
    assert outcome == "not_staff"
    assert said == "That window comes from the marathon schedule — change it there."
    outcome, _, _, said = await remove_ping_window(bot, bot.guild, FakeActor(), row["id"], staff)
    assert outcome == "removed" and GDQ in said
    assert [one["id"] for one in await windows_for(bot.db, row["id"])] == [marathon]
    outcome, _, _, said = await remove_ping_window(bot, bot.guild, FakeActor(), row["id"], staff)
    assert outcome == "no_window" and "not there any more" in said
    assert "golive.spotlight_window_removed" in await kinds(bot.db)


async def test_an_ended_window_is_purged_once_older_than_the_keep(bot, cog):
    row = await a_row(bot)
    old = await a_window(bot, row, -24 * 45, -24 * 40)
    recent = await a_window(bot, row, -24 * 3, -24 * 2)
    await cog.poll_once()
    assert [one["id"] for one in await windows_for(bot.db, row["id"])] == [recent]
    purged = await details_of(bot.db, "golive.spotlight_window_purged")
    assert purged["window_id"] == old and purged["keep_days"] == 30


async def test_a_row_that_leaves_the_list_takes_its_windows_with_it(bot):
    row = await a_row(bot)
    await a_window(bot, row, 1, 2)
    await delete_channel(bot.db, row["id"])
    assert await windows_for(bot.db, row["id"]) == []


async def test_the_panel_draws_only_the_ping_moves_that_change_something(bot, cog):
    await bot.store.set(GUILD, DEFAULT_TIMEZONE_KEY, "UTC")
    row = await a_row(bot)
    embed, view = await build_spotlight(bot, bot.guild, row["id"])
    labels = [getattr(one, "label", None) for one in view.children]
    assert "Pings: always" not in labels
    assert {"Pings: never", "Pings: during events"} <= set(labels)
    assert words.ADD_WINDOW not in labels
    assert "Pings: always" in embed.description
    assert all(len([one for one in view.children if one.row == n]) <= 5 for n in range(5))

    said, keep = await run_spotlight_move(bot, bot.guild, FakeActor(), row["id"], "ping_events")
    assert keep is True and "no window set" in said
    await a_window(bot, row, 24, 48, note="AGDQ 2027")
    await a_window(bot, row, 72, 96, source="marathon", source_id=3)
    embed, view = await build_spotlight(bot, bot.guild, row["id"])
    labels = [getattr(one, "label", None) for one in view.children]
    assert {"Pings: always", "Pings: never", words.ADD_WINDOW} <= set(labels)
    assert "Pings: during events" not in labels
    assert "Pings: during events — next" in embed.description
    assert "AGDQ 2027" in embed.description and "from the marathon schedule" in embed.description
    pick = next(one for one in view.children if isinstance(one, RemoveWindowPick))
    assert len(pick.options) == 2
    assert pick.options[1].description == "from the marathon schedule"
    assert any(isinstance(one, AddWindowButton) for one in view.children)
    assert all(len([one for one in view.children if one.row == n]) <= 5 for n in range(5))


async def test_the_window_modal_reads_the_boxes_in_the_persons_zone(bot, cog):
    await bot.store.set(GUILD, DEFAULT_TIMEZONE_KEY, "UTC")
    row = await a_row(bot)
    modal = WindowModal(row["id"])
    modal.starts._value = "2027-01-12 15:00"
    modal.ends._value = "2027-01-19 23:00"
    modal.note._value = "AGDQ 2027"
    interaction = FakeInteraction(bot, FakeActor(), bot.guild)
    await modal.on_submit(interaction)
    [window] = await windows_for(bot.db, row["id"])
    assert window["starts_at"] == "2027-01-12T15:00:00+00:00"
    assert window["ends_at"] == "2027-01-19T23:00:00+00:00"
    assert "pings from 12 Jan 15:00" in (interaction.sent or "")


async def test_the_window_modal_refuses_an_unreadable_date_in_words(bot, cog):
    row = await a_row(bot)
    modal = WindowModal(row["id"])
    modal.starts._value = "next tuesday"
    modal.ends._value = "2027-01-19 23:00"
    modal.note._value = ""
    interaction = FakeInteraction(bot, FakeActor(), bot.guild)
    await modal.on_submit(interaction)
    assert "next tuesday" in (interaction.sent or "")
    assert await windows_for(bot.db, row["id"]) == []


async def test_the_remove_pick_takes_a_staff_window_off_and_refuses_a_marathon_one(bot, cog):
    row = await a_row(bot)
    await set_ping_mode(bot, bot.guild, FakeActor(), row["id"], "events")
    staff = await a_window(bot, row, 24, 48)
    marathon = await a_window(bot, row, 72, 96, source="marathon", source_id=3)
    windows = await windows_for(bot.db, row["id"])
    pick = RemoveWindowPick(row["id"], windows)
    pick._values = [str(marathon)]
    interaction = FakeInteraction(bot, FakeActor(), bot.guild)
    await pick.callback(interaction)
    assert "marathon schedule" in (interaction.sent or "")
    pick._values = [str(staff)]
    interaction = FakeInteraction(bot, FakeActor(), bot.guild)
    await pick.callback(interaction)
    assert [one["id"] for one in await windows_for(bot.db, row["id"])] == [marathon]
