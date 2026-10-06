import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import discord
import pytest

from black_bloc import pb_store
from black_bloc.config import load_settings
from black_bloc.pb_looks import Feed, feed_of
from black_bloc.settings_store import SettingsStore
from black_bloc.speedrun import (
    NOT_FOUND,
    SERVER,
    THROTTLED,
    TOO_LARGE,
    UNREACHABLE,
    VERIFIED,
    PersonalBest,
    Runner,
    SpeedrunError,
)

GUILD = 7
LOGS = 501
REHEARSAL = 502
PBS = 503
ADA = 900
BEA = 901
CAL = 902
STAFFER = 950
LEADS = 11
PING = 77
NOW = datetime(2026, 10, 5, 18, 0, tzinfo=UTC)
ZFG = Runner("e8e5v680", "zfg", "https://www.speedrun.com/users/zfg", "zfg1")
OTHER = Runner("x1", "beaspeeds", "https://www.speedrun.com/users/beaspeeds", "bea_tv")


def best(
    run_id="r1",
    *,
    slot="g1|c1||",
    seconds=100.0,
    place=3,
    status=VERIFIED,
    verified_at=NOW,
    game="Ocarina of Time",
    category="Any%",
):
    return PersonalBest(
        run_id=run_id,
        slot=slot,
        game=game,
        category=category,
        seconds=seconds,
        place=place,
        weblink=f"https://www.speedrun.com/oot/runs/{run_id}",
        status=status,
        verified_at=verified_at,
    )


class _Response:
    def __init__(self, status):
        self.status = status
        self.reason = "refused"


class FakeClient:
    """speedrun.com as a dict: who a Twitch login or a name finds, and each runner's bests."""

    def __init__(self):
        self.requests = 0
        self.by_twitch = {}
        self.by_name = {}
        self.bests = {}
        self.raises = None
        self.asked = []
        self.closed = False

    def _ask(self, what):
        self.requests += 1
        self.asked.append(what)
        if self.raises is not None:
            raise self.raises

    async def users_by_twitch(self, login):
        self._ask(("twitch", login))
        return list(self.by_twitch.get(login, ()))

    async def users_by_name(self, name):
        self._ask(("name", name))
        return list(self.by_name.get(str(name).casefold(), ()))

    async def personal_bests(self, runner_id):
        self._ask(("bests", runner_id))
        found = self.bests.get(runner_id, [])
        if isinstance(found, Exception):
            raise found
        return list(found)

    async def close(self):
        self.closed = True


class FakeChannel:
    def __init__(self, channel_id, name):
        self.id = channel_id
        self.name = name
        self.sent = []
        self.send_raises = None

    async def send(self, content=None, **kwargs):
        if self.send_raises is not None:
            raise self.send_raises
        self.sent.append({"content": content, **kwargs})
        return SimpleNamespace(id=1000 + len(self.sent))


class FakeMember:
    def __init__(self, user_id, name, guild, *, staff=False):
        self.id = user_id
        self.display_name = name
        self.name = name.lower()
        self.mention = f"<@{user_id}>"
        self.guild = guild
        self.roles = [SimpleNamespace(id=LEADS)] if staff else []
        self.guild_permissions = SimpleNamespace(manage_guild=staff)


class FakeGuild:
    def __init__(self):
        self.id = GUILD
        self.name = "Black Bloc"
        self.unavailable = False
        self.channels = {
            one.id: one
            for one in (
                FakeChannel(LOGS, "logs"),
                FakeChannel(REHEARSAL, "rehearsal"),
                FakeChannel(PBS, "speed-and-pbs"),
            )
        }
        self.members = {
            ADA: FakeMember(ADA, "Ada", self),
            BEA: FakeMember(BEA, "Bea", self),
            STAFFER: FakeMember(STAFFER, "Sky", self, staff=True),
        }

    def get_channel(self, channel_id):
        return self.channels.get(channel_id)

    def get_member(self, user_id):
        return self.members.get(int(user_id))

    def get_role(self, role_id):
        return None


class FakeBot:
    def __init__(self, db, store, settings, guild):
        self.db = db
        self.store = store
        self.settings = settings
        self.guard = None
        self.guild = guild
        self.guilds = [guild]
        self.user = SimpleNamespace(id=42)

    def get_channel(self, channel_id):
        return self.guild.get_channel(channel_id)

    def get_guild(self, guild_id):
        return self.guild if guild_id == self.guild.id else None


@pytest.fixture
def guild():
    return FakeGuild()


@pytest.fixture
async def bot(db, guild, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    settings = load_settings(_env_file=None)
    store = SettingsStore(db, settings)
    await store.load()
    await store.set(GUILD, "log_channel_id", LOGS)
    await store.set(GUILD, "shadow_channel_id", REHEARSAL)
    return FakeBot(db, store, settings, guild)


@pytest.fixture
def client():
    return FakeClient()


@pytest.fixture
def feed(bot, client):
    found = Feed(bot, client)
    bot._pb_feed = found
    return found


async def link(db, user_id, login):
    await db.conn.execute(
        "INSERT OR REPLACE INTO golive_links(user_id, twitch_login, linked_at) VALUES (?, ?, ?)",
        (user_id, login, NOW.isoformat()),
    )
    await db.conn.commit()


async def matched(bot, user_id=ADA, runner=ZFG, *, source=pb_store.AUTO, login="zfg1"):
    if login:
        await link(bot.db, user_id, login)
    return await pb_store.write_match(
        bot.db, GUILD, user_id, runner, source=source, twitch_login=login, now=NOW
    )


async def seen(feed, client, bests, user_id=ADA, runner=ZFG, at=NOW):
    """The first sight: whatever the runner has is the baseline."""
    client.bests[runner.id] = list(bests)
    return await feed.look(feed.bot.guild, user_id, now=at)


async def kinds(db):
    cur = await db.conn.execute("SELECT kind FROM action_log ORDER BY id")
    return [row["kind"] for row in await cur.fetchall()]


async def details_of(db, kind):
    cur = await db.conn.execute(
        "SELECT details, actor_id, target_id FROM action_log WHERE kind = ? ORDER BY id DESC "
        "LIMIT 1",
        (kind,),
    )
    row = await cur.fetchone()
    return json.loads(row["details"] or "{}") | {
        "actor_id": row["actor_id"],
        "target_id": row["target_id"],
    }


def sent(guild):
    """What the feed posted; the log channel's own cards are the action log's, not the feed's."""
    return {
        channel.name: channel.sent
        for channel in guild.channels.values()
        if channel.sent and channel.id != LOGS
    }


async def test_the_first_sight_records_everything_and_posts_nothing(bot, guild, feed, client):
    await matched(bot)

    looked = await seen(feed, client, [best("r1"), best("r2", slot="g2|c1||")])

    assert (looked.found, looked.seen, looked.first) == (0, 2, True)
    assert sent(guild) == {}
    assert set(await pb_store.baseline(bot.db, GUILD, ADA)) == {"g1|c1||", "g2|c1||"}
    assert (await pb_store.match(bot.db, GUILD, ADA))["baseline_at"] == NOW.isoformat()
    assert await kinds(bot.db) == ["pbfeed.baseline"]
    assert (await details_of(bot.db, "pbfeed.baseline"))["runs"] == 2


async def test_a_faster_verified_run_after_the_baseline_is_rehearsed_once_in_shadow(
    bot, guild, feed, client
):
    await bot.store.set(GUILD, "pb_feed_channel_id", PBS)
    await matched(bot)
    await seen(feed, client, [best("r1", seconds=100.0)])
    later = NOW + timedelta(hours=2)
    client.bests[ZFG.id] = [best("r9", seconds=95.5, place=2, verified_at=later)]

    looked = await feed.look(guild, ADA, now=later)
    again = await feed.look(guild, ADA, now=later + timedelta(hours=1))

    assert (looked.found, again.found) == (1, 0)
    assert list(sent(guild)) == ["rehearsal"]
    copy = guild.get_channel(REHEARSAL).sent
    assert len(copy) == 1
    assert f"<#{PBS}>" in copy[0]["content"]
    embed = copy[0]["embed"]
    assert embed.title == "New personal best"
    assert embed.description == (
        f"<@{ADA}> ran **Ocarina of Time** — Any% in **1:35.500** — #2 on the leaderboard."
    )
    assert embed.url == "https://www.speedrun.com/oot/runs/r9"
    assert copy[0]["allowed_mentions"].to_dict() == discord.AllowedMentions.none().to_dict()
    found = await details_of(bot.db, "pbfeed.would_post")
    assert found["rehearsed"] is True and found["shadow_home"] == REHEARSAL
    assert found["aimed_at"] == PBS and found["target_id"] == ADA and found["run_id"] == "r9"
    posts = await pb_store.posts(bot.db, GUILD)
    assert [(row["run_id"], row["outcome"]) for row in posts] == [("r9", pb_store.REHEARSED)]
    assert (await pb_store.match(bot.db, GUILD, ADA))["last_pb_at"] == later.isoformat()


async def test_on_posts_in_the_channel_with_no_ping_by_default(bot, guild, feed, client):
    await bot.store.set(GUILD, "pb_feed_mode", "on")
    await bot.store.set(GUILD, "pb_feed_channel_id", PBS)
    await matched(bot)
    await seen(feed, client, [])
    later = NOW + timedelta(minutes=30)
    client.bests[ZFG.id] = [best("r1", place=None, verified_at=later)]

    await feed.look(guild, ADA, now=later)

    post = guild.get_channel(PBS).sent[0]
    assert list(sent(guild)) == ["speed-and-pbs"]
    assert post["content"] is None
    assert post["embed"].description == f"<@{ADA}> ran **Ocarina of Time** — Any% in **1:40**."
    assert post["allowed_mentions"].to_dict() == discord.AllowedMentions.none().to_dict()
    assert [item.url for item in post["view"].children] == [
        "https://www.speedrun.com/oot/runs/r1"
    ]
    assert "pbfeed.posted" in await kinds(bot.db)
    assert (await pb_store.posts(bot.db, GUILD))[0]["message_id"] == 1001


async def test_the_ping_role_is_the_only_mention_and_only_when_it_is_on(bot, guild, feed, client):
    await bot.store.set(GUILD, "pb_feed_mode", "on")
    await bot.store.set(GUILD, "pb_feed_channel_id", PBS)
    await bot.store.set(GUILD, "pb_feed_ping_role_id", PING)
    await matched(bot)
    await seen(feed, client, [])
    client.bests[ZFG.id] = [best("r1", verified_at=NOW + timedelta(minutes=5))]

    await feed.look(guild, ADA, now=NOW + timedelta(minutes=10))

    post = guild.get_channel(PBS).sent[0]
    allowed = post["allowed_mentions"]
    assert post["content"] == f"<@&{PING}>"
    assert [role.id for role in allowed.roles] == [PING]
    assert allowed.users is False and allowed.everyone is False


async def test_a_rehearsal_never_pings_even_with_a_ping_role_set(bot, guild, feed, client):
    await bot.store.set(GUILD, "pb_feed_ping_role_id", PING)
    await matched(bot)
    await seen(feed, client, [])
    client.bests[ZFG.id] = [best("r1", verified_at=NOW + timedelta(minutes=5))]

    await feed.look(guild, ADA, now=NOW + timedelta(minutes=10))

    copy = guild.get_channel(REHEARSAL).sent[0]
    assert f"<@&{PING}>" not in (copy["content"] or "")
    assert "nowhere yet" in copy["content"]
    assert copy["allowed_mentions"].to_dict() == discord.AllowedMentions.none().to_dict()


async def test_on_with_a_blank_channel_is_a_refusal_in_words_and_never_a_guess(
    bot, guild, feed, client
):
    await bot.store.set(GUILD, "pb_feed_mode", "on")
    await matched(bot)
    await seen(feed, client, [])
    later = NOW + timedelta(minutes=5)
    client.bests[ZFG.id] = [best("r1", verified_at=later)]

    looked = await feed.look(guild, ADA, now=later)
    await feed.look(guild, ADA, now=later + timedelta(hours=1))

    assert looked.found == 1 and sent(guild) == {}
    assert (await kinds(bot.db)).count("pbfeed.post_failed") == 1
    reason = (await details_of(bot.db, "pbfeed.post_failed"))["reason"]
    assert "pb_feed_channel_id is blank" in reason and "Personal bests page" in reason
    post = (await pb_store.posts(bot.db, GUILD))[0]
    assert (post["outcome"], post["reason"]) == (pb_store.FAILED, reason)


async def test_a_channel_discord_refuses_is_logged_once_and_not_retried(bot, guild, feed, client):
    await bot.store.set(GUILD, "pb_feed_mode", "on")
    await bot.store.set(GUILD, "pb_feed_channel_id", PBS)
    guild.get_channel(PBS).send_raises = discord.Forbidden(_Response(403), "Missing Access")
    await matched(bot)
    await seen(feed, client, [])
    later = NOW + timedelta(minutes=5)
    client.bests[ZFG.id] = [best("r1", verified_at=later)]

    await feed.look(guild, ADA, now=later)
    guild.get_channel(PBS).send_raises = None
    await feed.look(guild, ADA, now=later + timedelta(hours=1))

    assert sent(guild) == {}
    assert (await kinds(bot.db)).count("pbfeed.post_failed") == 1
    reason = (await details_of(bot.db, "pbfeed.post_failed"))["reason"]
    assert "Send Messages" in reason and "403" not in reason.split("(")[0]


async def test_shadow_with_no_home_at_all_is_a_dry_run_not_a_failure(bot, guild, feed, client):
    await bot.store.clear(GUILD, "shadow_channel_id")
    await bot.store.clear(GUILD, "log_channel_id")
    await matched(bot)
    await seen(feed, client, [])
    client.bests[ZFG.id] = [best("r1", verified_at=NOW + timedelta(minutes=5))]

    await feed.look(guild, ADA, now=NOW + timedelta(minutes=10))

    found = await details_of(bot.db, "pbfeed.would_post")
    assert found["rehearsed"] is False and "rehearsal home" in found["reason"]
    assert "pbfeed.post_failed" not in await kinds(bot.db)
    assert (await pb_store.posts(bot.db, GUILD))[0]["outcome"] == pb_store.DRY


async def test_the_features_own_rehearsal_home_wins(bot, guild, feed, client):
    await bot.store.set(GUILD, "pb_feed_shadow_channel_id", LOGS)
    await matched(bot)
    await seen(feed, client, [])
    client.bests[ZFG.id] = [best("r1", verified_at=NOW + timedelta(minutes=5))]

    await feed.look(guild, ADA, now=NOW + timedelta(minutes=10))

    copies = [one for one in guild.get_channel(LOGS).sent if one.get("view") is not None]
    assert len(copies) == 1 and sent(guild) == {}


async def test_test_mode_keeps_a_post_out_of_a_channel_the_guard_refuses(bot, guild, feed, client):
    await bot.store.set(GUILD, "pb_feed_mode", "on")
    await bot.store.set(GUILD, "pb_feed_channel_id", PBS)
    bot.guard = SimpleNamespace(allows_channel=lambda channel_id: False, test_channel_id=None)
    await matched(bot)
    await seen(feed, client, [])
    client.bests[ZFG.id] = [best("r1", verified_at=NOW + timedelta(minutes=5))]

    await feed.look(guild, ADA, now=NOW + timedelta(minutes=10))

    assert sent(guild) == {}
    assert (await details_of(bot.db, "pbfeed.would_post"))["reason"].startswith("test mode")


async def test_an_unverified_run_is_never_posted_and_never_recorded(bot, guild, feed, client):
    await matched(bot)
    await seen(feed, client, [])
    later = NOW + timedelta(minutes=5)
    client.bests[ZFG.id] = [best("r1", status="new", verified_at=None)]

    looked = await feed.look(guild, ADA, now=later)

    assert looked.found == 0 and sent(guild) == {}
    assert await pb_store.baseline(bot.db, GUILD, ADA) == {}

    client.bests[ZFG.id] = [best("r1", verified_at=later + timedelta(minutes=30))]
    verified = await feed.look(guild, ADA, now=later + timedelta(hours=1))

    assert verified.found == 1 and len(guild.get_channel(REHEARSAL).sent) == 1


async def test_an_empty_answer_and_an_outage_never_replay_old_runs(bot, guild, feed, client):
    await matched(bot)
    old = [best("r1"), best("r2", slot="g2|c1||")]
    await seen(feed, client, old)

    client.bests[ZFG.id] = []
    await feed.look(guild, ADA, now=NOW + timedelta(hours=1))
    client.bests[ZFG.id] = SpeedrunError(SERVER, status=503)
    with pytest.raises(SpeedrunError):
        await feed.look(guild, ADA, now=NOW + timedelta(hours=2))
    client.bests[ZFG.id] = old
    back = await feed.look(guild, ADA, now=NOW + timedelta(hours=3))

    assert back.found == 0 and sent(guild) == {}
    assert len(await pb_store.baseline(bot.db, GUILD, ADA)) == 2


async def test_a_restart_reads_the_same_baseline(bot, guild, feed, client):
    await matched(bot)
    await seen(feed, client, [best("r1")])

    reborn = Feed(bot, client)
    looked = await reborn.look(guild, ADA, now=NOW + timedelta(hours=1))

    assert looked.found == 0 and looked.first is False and sent(guild) == {}


async def test_a_rematch_is_a_first_sight_again(bot, guild, feed, client):
    await matched(bot)
    await seen(feed, client, [best("r1")])
    await matched(bot, runner=OTHER, source=pb_store.STAFF, login="zfg1")
    later = NOW + timedelta(hours=1)
    client.bests[OTHER.id] = [best("b1", verified_at=later), best("b2", slot="g2|c1||")]

    looked = await feed.look(guild, ADA, now=later)

    assert (looked.found, looked.first) == (0, True) and sent(guild) == {}
    assert {row["run_id"] for row in (await pb_store.baseline(bot.db, GUILD, ADA)).values()} == {
        "b1",
        "b2",
    }


async def test_one_run_is_claimed_once_however_many_looks_find_it(bot, guild, feed, client):
    await matched(bot)
    await seen(feed, client, [])
    later = NOW + timedelta(minutes=5)
    fresh = best("r1", verified_at=later)
    row = await pb_store.match(bot.db, GUILD, ADA)

    first = await feed.post(guild, row, fresh, later)
    second = await feed.post(guild, row, fresh, later)

    assert (first, second) == (pb_store.REHEARSED, pb_store.CLAIMED)
    assert len(guild.get_channel(REHEARSAL).sent) == 1


async def test_more_news_than_the_cap_is_held_and_never_posted_later(bot, guild, feed, client):
    await bot.store.set(GUILD, "pb_feed_max_posts", 2)
    await matched(bot)
    await seen(feed, client, [])
    later = NOW + timedelta(minutes=5)
    client.bests[ZFG.id] = [
        best(f"r{at}", slot=f"g{at}|c||", verified_at=later + timedelta(seconds=at))
        for at in range(5)
    ]

    looked = await feed.look(guild, ADA, now=later + timedelta(minutes=1))
    again = await feed.look(guild, ADA, now=later + timedelta(hours=1))

    assert (looked.found, again.found) == (2, 0)
    assert len(guild.get_channel(REHEARSAL).sent) == 2
    assert (await details_of(bot.db, "pbfeed.held_back"))["runs"] == 3
    outcomes = [row["outcome"] for row in await pb_store.posts(bot.db, GUILD)]
    assert sorted(outcomes) == [pb_store.HELD] * 3 + [pb_store.REHEARSED] * 2


async def test_a_template_that_cannot_be_filled_falls_back_to_the_shipped_words(
    bot, guild, feed, client, monkeypatch
):
    real = bot.store.get
    monkeypatch.setattr(
        bot.store,
        "get",
        lambda guild_id, key: (
            "{member} did {nothing}" if key == "pb_feed_post_text" else real(guild_id, key)
        ),
    )
    await matched(bot)
    await seen(feed, client, [])
    client.bests[ZFG.id] = [best("r1", verified_at=NOW + timedelta(minutes=5))]

    await feed.look(guild, ADA, now=NOW + timedelta(minutes=10))

    assert "ran **Ocarina of Time**" in guild.get_channel(REHEARSAL).sent[0]["embed"].description


async def test_a_lookup_matches_exactly_one_runner_and_logs_it(bot, guild, feed, client):
    await link(bot.db, ADA, "zfg1")
    client.by_twitch["zfg1"] = [ZFG]

    row = await feed.lookup(guild, ADA, "zfg1", now=NOW)

    assert (row["state"], row["source"], row["src_user_id"]) == (pb_store.MATCHED, "auto", ZFG.id)
    assert row["twitch_login"] == "zfg1" and row["baseline_at"] is None
    found = await details_of(bot.db, "pbfeed.matched")
    assert found["runner"] == "zfg" and found["target_id"] == ADA


@pytest.mark.parametrize(
    ("answer", "reason"),
    [([], "nobody"), ([ZFG, Runner("x2", "copycat", "", "zfg1")], "ambiguous")],
)
async def test_nobody_or_two_is_no_match(bot, guild, feed, client, answer, reason):
    client.by_twitch["zfg1"] = answer

    row = await feed.lookup(guild, ADA, "zfg1", now=NOW)

    assert (row["state"], row["reason"], row["src_user_id"]) == (pb_store.NONE, reason, None)
    assert "pbfeed.matched" not in await kinds(bot.db)


async def test_a_runner_whose_own_profile_names_another_login_is_not_a_match(
    bot, guild, feed, client
):
    client.by_twitch["zfg"] = [ZFG]

    row = await feed.lookup(guild, ADA, "zfg", now=NOW)

    assert row["state"] == pb_store.NONE


@pytest.mark.parametrize("state", [pb_store.OPTED_OUT, pb_store.BLOCKED])
async def test_an_opted_out_or_blocked_member_is_never_looked_up(bot, guild, feed, client, state):
    await pb_store.write_state(bot.db, GUILD, ADA, state, state_by=pb_store.STAFF)
    client.by_twitch["zfg1"] = [ZFG]

    row = await feed.lookup(guild, ADA, "zfg1", now=NOW)

    assert row["state"] == state and client.asked == []


async def test_two_members_cannot_hold_one_runner(bot, guild, feed, client):
    await matched(bot, ADA)
    client.by_twitch["zfg1"] = [ZFG]

    row = await feed.lookup(guild, BEA, "zfg1", now=NOW)

    assert (row["state"], row["reason"]) == (pb_store.NONE, "taken")
    assert (await details_of(bot.db, "pbfeed.match_refused"))["held_by"] == ADA


async def test_an_automatic_match_follows_a_changed_twitch_link(bot, guild, feed, client):
    await matched(bot)
    await seen(feed, client, [best("r1")])
    client.by_twitch["bea_tv"] = [OTHER]

    row = await feed.lookup(guild, ADA, "bea_tv", now=NOW)

    assert (row["src_user_id"], row["twitch_login"]) == (OTHER.id, "bea_tv")
    assert await pb_store.baseline(bot.db, GUILD, ADA) == {}
    assert (await details_of(bot.db, "pbfeed.unmatched"))["why"] == "link_moved"


async def test_a_match_staff_set_does_not_follow_the_link(bot, guild, feed, client):
    await matched(bot, source=pb_store.STAFF)

    row = await feed.lookup(guild, ADA, "bea_tv", now=NOW)

    assert row["src_user_id"] == ZFG.id and client.asked == []


async def test_a_runner_speedrun_no_longer_has_is_unmatched_and_said_once(
    bot, guild, feed, client
):
    await matched(bot)
    client.bests[ZFG.id] = SpeedrunError(NOT_FOUND, status=404)

    looked = await feed.look(guild, ADA, now=NOW)

    row = await pb_store.match(bot.db, GUILD, ADA)
    assert looked.gone and (row["state"], row["reason"]) == (pb_store.NONE, "runner_gone")
    assert await kinds(bot.db) == ["pbfeed.runner_gone"]


async def test_one_oversized_runner_is_their_own_trouble_not_an_outage(bot, guild, feed, client):
    await matched(bot)
    client.bests[ZFG.id] = SpeedrunError(TOO_LARGE)

    await feed.look(guild, ADA, now=NOW)
    await feed.look(guild, ADA, now=NOW + timedelta(hours=1))

    assert await kinds(bot.db) == ["pbfeed.look_failed"]
    assert "larger" in (await pb_store.match(bot.db, GUILD, ADA))["look_error"]
    assert await pb_store.looks(bot.db, GUILD) is None


async def test_a_tick_does_nothing_at_all_while_the_mode_is_off(bot, guild, feed, client):
    await bot.store.set(GUILD, "pb_feed_mode", "off")
    await link(bot.db, ADA, "zfg1")

    assert await feed.tick(guild, NOW) == 0
    assert client.asked == [] and await pb_store.matches(bot.db, GUILD) == []


async def test_a_tick_matches_a_linked_member_then_takes_the_baseline_then_looks_hourly(
    bot, guild, feed, client
):
    await link(bot.db, ADA, "zfg1")
    client.by_twitch["zfg1"] = [ZFG]
    client.bests[ZFG.id] = [best("r1")]

    await feed.tick(guild, NOW)
    await feed.tick(guild, NOW + timedelta(minutes=1))
    await feed.tick(guild, NOW + timedelta(minutes=2))
    await feed.tick(guild, NOW + timedelta(minutes=59))
    await feed.tick(guild, NOW + timedelta(minutes=62))

    assert client.asked == [("twitch", "zfg1"), ("bests", ZFG.id), ("bests", ZFG.id)]
    assert sent(guild) == {}


async def test_members_are_spread_across_the_interval_not_taken_in_one_burst(
    bot, guild, feed, client
):
    for at in range(120):
        user_id = 2000 + at
        guild.members[user_id] = FakeMember(user_id, f"m{at}", guild)
        runner = Runner(f"s{at}", f"runner{at}", "", f"login{at}")
        await matched(bot, user_id, runner, login=f"login{at}")

    took = [await feed.tick(guild, NOW + timedelta(minutes=at)) for at in range(60)]

    assert took == [2] * 60
    assert client.requests == 120


async def test_a_tick_never_takes_more_than_the_tick_cap(bot, guild, feed, client):
    await bot.store.set(GUILD, "pb_feed_interval_minutes", 15)
    for at in range(300):
        user_id = 2000 + at
        guild.members[user_id] = FakeMember(user_id, f"m{at}", guild)
        runner = Runner(f"s{at}", f"runner{at}", "", f"login{at}")
        await matched(bot, user_id, runner, login=f"login{at}")

    assert await feed.tick(guild, NOW) == 5


async def test_the_request_cap_stops_a_cycle_and_says_so_once(bot, guild, feed, client):
    await bot.store.set(GUILD, "pb_feed_cycle_requests", 3)
    await bot.store.set(GUILD, "pb_feed_interval_minutes", 15)
    for at in range(40):
        user_id = 2000 + at
        guild.members[user_id] = FakeMember(user_id, f"m{at}", guild)
        runner = Runner(f"s{at}", f"runner{at}", "", f"login{at}")
        await matched(bot, user_id, runner, login=f"login{at}")

    for at in range(5):
        await feed.tick(guild, NOW + timedelta(minutes=at))

    assert client.requests == 3
    assert (await kinds(bot.db)).count("pbfeed.cap_reached") == 1

    await feed.tick(guild, NOW + timedelta(minutes=16))
    assert client.requests > 3


@pytest.mark.parametrize(
    "error",
    [
        SpeedrunError(THROTTLED, status=420),
        SpeedrunError(SERVER, status=502),
        SpeedrunError(UNREACHABLE, why="TimeoutError"),
    ],
)
async def test_an_outage_is_logged_once_backs_off_and_recovery_is_said(
    bot, guild, feed, client, error
):
    await matched(bot)
    client.raises = error

    took = [await feed.tick(guild, NOW + timedelta(minutes=at)) for at in range(4)]

    assert took == [0, 0, 0, 0] and client.requests == 1
    assert await kinds(bot.db) == ["pbfeed.look_failed"]
    state = await pb_store.looks(bot.db, GUILD)
    assert state["failures"] == 1
    assert pb_store.parsed(state["backoff_until"]) == NOW + timedelta(minutes=5)
    assert str(error) == (await details_of(bot.db, "pbfeed.look_failed"))["reason"]

    await feed.tick(guild, NOW + timedelta(minutes=6))
    assert client.requests == 2 and await kinds(bot.db) == ["pbfeed.look_failed"]
    state = await pb_store.looks(bot.db, GUILD)
    assert pb_store.parsed(state["backoff_until"]) == NOW + timedelta(minutes=16)

    client.raises = None
    await feed.tick(guild, NOW + timedelta(minutes=17))
    assert await kinds(bot.db) == ["pbfeed.look_failed", "pbfeed.recovered", "pbfeed.baseline"]
    assert (await pb_store.looks(bot.db, GUILD))["failures"] == 0


async def test_a_restart_inside_an_outage_does_not_log_it_again(bot, guild, feed, client):
    await matched(bot)
    client.raises = SpeedrunError(SERVER, status=500)
    await feed.tick(guild, NOW)

    reborn = Feed(bot, client)
    await reborn.tick(guild, NOW + timedelta(minutes=1))
    await reborn.tick(guild, NOW + timedelta(minutes=6))

    assert await kinds(bot.db) == ["pbfeed.look_failed"]


async def test_a_bug_in_a_look_backs_off_instead_of_raising_out_of_the_tick(
    bot, guild, feed, client
):
    await matched(bot)
    client.raises = RuntimeError("boom")

    assert await feed.tick(guild, NOW) == 0
    assert "RuntimeError" in (await details_of(bot.db, "pbfeed.look_failed"))["reason"]


async def test_an_interval_of_looks_with_no_news_is_one_nothing_new_row(bot, guild, feed, client):
    await matched(bot)
    client.bests[ZFG.id] = [best("r1")]

    for at in (0, 61, 122):
        await feed.tick(guild, NOW + timedelta(minutes=at))

    found = await kinds(bot.db)
    assert found.count("pbfeed.nothing_new") == 2 and "pbfeed.would_post" not in found
    assert (await details_of(bot.db, "pbfeed.nothing_new"))["looks"] == 1


async def test_members_who_left_are_skipped_and_kept(bot, guild, feed, client):
    await matched(bot, CAL, Runner("s9", "cal", "", "cal_tv"), login="cal_tv")

    assert await feed.tick(guild, NOW) == 0
    assert client.asked == []
    assert (await pb_store.match(bot.db, GUILD, CAL))["state"] == pb_store.MATCHED


async def test_an_opt_out_in_the_middle_of_things_strands_nothing(bot, guild, feed, client):
    await matched(bot)
    await seen(feed, client, [best("r1")])
    await pb_store.write_state(
        bot.db, GUILD, ADA, pb_store.OPTED_OUT, state_by=pb_store.MEMBER, keep_runner=True
    )
    client.bests[ZFG.id] = [best("r9", seconds=1.0, verified_at=NOW + timedelta(hours=1))]

    took = await feed.tick(guild, NOW + timedelta(hours=2))
    looked = await feed.look(guild, ADA, now=NOW + timedelta(hours=2))

    assert took == 0 and looked.found == 0 and sent(guild) == {}


def test_one_feed_per_bot():
    bot = SimpleNamespace(settings=SimpleNamespace(origin="https://example.test"))

    assert feed_of(bot) is feed_of(bot)
    assert "https://example.test" in feed_of(bot).client.agent
