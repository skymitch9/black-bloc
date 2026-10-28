import asyncio
import copy
import json
from datetime import timedelta

import pytest

from black_bloc import bluesky as rules
from black_bloc import bluesky_moves as moves
from black_bloc import bluesky_store as store
from black_bloc.logkinds import VIA_WEBSITE
from tests.bluesky_fakes import (
    GUILD,
    HOME,
    NEWEST_URI,
    NOW,
    REAL,
    ROLE,
    FakeFetch,
    make_bot,
    recorded,
    refused,
    with_feed,
)


@pytest.fixture
async def bot(db, monkeypatch):
    return await make_bot(db, monkeypatch)


async def kinds(db):
    cur = await db.conn.execute("SELECT kind FROM action_log ORDER BY id")
    return [row["kind"] for row in await cur.fetchall()]


async def details_of(db, kind):
    cur = await db.conn.execute(
        "SELECT details FROM action_log WHERE kind = ? ORDER BY id", (kind,)
    )
    return [json.loads(row["details"]) for row in await cur.fetchall()]


def home(bot):
    return bot.guild.get_channel(HOME)


def real(bot):
    return bot.guild.get_channel(REAL)


def fresh_entry(rkey, minutes_after=1, text="Fresh off the stream"):
    entry = copy.deepcopy(recorded()["feed"][0])
    stamp = (NOW + timedelta(minutes=minutes_after)).isoformat().replace("+00:00", "Z")
    entry["post"]["uri"] = entry["post"]["uri"].rsplit("/", 1)[0] + f"/{rkey}"
    entry["post"]["indexedAt"] = stamp
    entry["post"]["record"]["text"] = text
    entry["post"]["record"].pop("facets", None)
    return entry


async def test_the_first_read_in_test_mode_sends_only_the_recent_post_to_the_test_channel(bot):
    assert await moves.tick(bot, bot.guild, NOW) == "read"

    [copy_] = home(bot).sent
    assert copy_.content.splitlines()[0] == (
        f"Test copy · while bluesky_mode is on this goes to <#{REAL}>"
    )
    assert copy_.kwargs["allowed_mentions"].roles is False
    assert copy_.kwargs["embed"].url.endswith("/post/3myuptyegac23")
    assert real(bot).sent == []
    row = await store.get(bot.db, GUILD, NEWEST_URI)
    assert row["status"] == rules.WOULD_POST and row["message_id"] == copy_.id
    logged = await kinds(bot.db)
    assert logged.count("bluesky.would_post") == 1
    assert logged.count("bluesky.skipped_old") == 1 and logged.count("bluesky.skipped_kind") == 1
    [old] = await details_of(bot.db, "bluesky.skipped_old")
    assert old["count"] == len(old["uris"]) > 10


async def test_the_next_tick_waits_for_the_interval_and_then_finds_nothing_new(bot):
    await moves.tick(bot, bot.guild, NOW)

    assert await moves.tick(bot, bot.guild, NOW + timedelta(minutes=4)) is None
    assert await moves.tick(bot, bot.guild, NOW + timedelta(minutes=5)) == "read"
    assert len(home(bot).sent) == 1
    assert len(bot.bluesky_fetch.urls) == 2


async def test_on_posts_a_new_post_in_the_channel_with_the_ping_role_only(bot):
    await moves.tick(bot, bot.guild, NOW)
    await bot.store.set(GUILD, "bluesky_mode", "on")
    await bot.store.set(GUILD, "bluesky_ping_role_id", ROLE)
    bot.bluesky_fetch.payload["feed"].insert(0, fresh_entry("3mzzzzzzzzzz1"))

    await moves.tick(bot, bot.guild, NOW + timedelta(minutes=5))

    [post] = real(bot).sent
    assert post.content.splitlines() == [
        f"<@&{ROLE}>",
        "🦋 **Black in a Flash!** posted on Bluesky",
    ]
    assert post.kwargs["embed"].description == "Fresh off the stream"
    assert post.kwargs["embed"].footer.icon_url == (
        f"{bot.settings.site_origin.rstrip('/')}/assets/bluesky.png"
    )
    labels = [one.label for one in post.kwargs["view"].children]
    assert labels == ["Open on Bluesky", "@blackinaflash.bsky.social on Bluesky"]
    allowed = post.kwargs["allowed_mentions"]
    assert [role.id for role in allowed.roles] == [ROLE]
    assert allowed.everyone is False and allowed.users is False
    assert len(home(bot).sent) == 1
    assert (await details_of(bot.db, "bluesky.posted"))[0]["message_id"] == post.id


async def test_off_reads_nothing(bot):
    await bot.store.set(GUILD, "bluesky_mode", "off")

    assert await moves.tick(bot, bot.guild, NOW) is None
    assert bot.bluesky_fetch.urls == []


async def test_a_403_is_logged_once_per_streak_and_backs_off(bot):
    bot.bluesky_fetch.status = 403

    assert await moves.tick(bot, bot.guild, NOW) == "failed"
    assert await moves.tick(bot, bot.guild, NOW + timedelta(minutes=9)) is None
    assert await moves.tick(bot, bot.guild, NOW + timedelta(minutes=10)) == "failed"

    [said] = await details_of(bot.db, "bluesky.read_failed")
    assert said | {"via": None} == {
        "status": 403,
        "why": "Bluesky answered 403",
        "failures": 1,
        "via": None,
    }
    assert (await store.get_read(bot.db, GUILD))["failures"] == 2
    assert home(bot).sent == [] and await store.recent(bot.db, GUILD, 5) == []

    bot.bluesky_fetch.status = 200
    assert await moves.tick(bot, bot.guild, NOW + timedelta(minutes=30)) == "read"
    assert (await store.get_read(bot.db, GUILD))["failures"] == 0
    assert len(home(bot).sent) == 1


async def test_on_with_no_channel_reads_nothing_and_says_so_once(bot):
    await bot.store.set(GUILD, "bluesky_mode", "on")
    await bot.store.clear(GUILD, "bluesky_channel_id")

    assert await moves.tick(bot, bot.guild, NOW) == "nowhere"
    assert await moves.tick(bot, bot.guild, NOW + timedelta(minutes=5)) == "nowhere"

    [said] = await details_of(bot.db, "bluesky.post_failed")
    assert said["why"] == rules.NO_CHANNEL
    assert bot.bluesky_fetch.urls == []


async def test_a_refused_send_is_retried_once_then_left_failed(bot):
    home(bot).send_raises = refused()

    await moves.tick(bot, bot.guild, NOW)
    assert (await store.get(bot.db, GUILD, NEWEST_URI))["status"] == rules.RETRY
    await moves.tick(bot, bot.guild, NOW + timedelta(minutes=5))
    assert (await store.get(bot.db, GUILD, NEWEST_URI))["status"] == rules.FAILED
    home(bot).send_raises = None
    await moves.tick(bot, bot.guild, NOW + timedelta(minutes=10))

    assert home(bot).sent == []
    rows = await details_of(bot.db, "bluesky.post_failed")
    assert [one["row"] for one in rows] == [rules.RETRY, rules.FAILED]
    assert "403" in rows[0]["why"]


async def test_a_retry_that_works_is_posted(bot):
    home(bot).send_raises = refused(500)
    await moves.tick(bot, bot.guild, NOW)
    home(bot).send_raises = None

    await moves.tick(bot, bot.guild, NOW + timedelta(minutes=5))

    assert len(home(bot).sent) == 1
    assert (await store.get(bot.db, GUILD, NEWEST_URI))["status"] == rules.WOULD_POST


async def test_two_ticks_at_once_post_once(bot):
    await asyncio.gather(moves.tick(bot, bot.guild, NOW), moves.tick(bot, bot.guild, NOW))

    assert len(home(bot).sent) == 1


async def test_a_reply_is_mirrored_only_once_replies_are_on(bot):
    await bot.store.set(GUILD, "bluesky_replies", True)
    reply = fresh_entry("3mzzzzzzzzzz2", text="seriously though")
    reply["post"]["record"]["reply"] = {"root": {}, "parent": {}}
    bot.bluesky_fetch.payload["feed"].insert(0, reply)

    await moves.tick(bot, bot.guild, NOW)

    assert home(bot).sent[-1].kwargs["embed"].description == "seriously though"


async def test_post_the_latest_two_in_the_channel(bot):
    done = await moves.post_latest(bot, bot.guild, 5, 2, "channel", now=NOW)

    assert done.ok, done.message
    first, second = real(bot).sent
    assert first.kwargs["embed"].url.endswith("/post/3mydhiqbers2w")
    assert second.kwargs["embed"].url.endswith("/post/3myuptyegac23")
    assert first.kwargs["allowed_mentions"].roles is False
    assert first.kwargs["allowed_mentions"].users is False
    assert done.message == f"2 post(s) are up in <#{REAL}>."
    [logged] = await details_of(bot.db, "bluesky.posted_latest")
    assert logged | {"uris": None} == {
        "via": "discord",
        "count": 2,
        "where": "channel",
        "channel": REAL,
        "posted": 2,
        "skipped": 0,
        "failed": 0,
        "uris": None,
    }


async def test_what_post_the_latest_put_up_the_loop_never_repeats(bot):
    await moves.post_latest(bot, bot.guild, 5, 2, "channel", now=NOW)
    await bot.store.set(GUILD, "bluesky_mode", "on")

    await moves.tick(bot, bot.guild, NOW)

    assert len(real(bot).sent) == 2
    assert (await store.get(bot.db, GUILD, NEWEST_URI))["status"] == rules.POSTED


async def test_a_second_press_skips_what_is_already_up_and_says_so(bot):
    await moves.post_latest(bot, bot.guild, 5, 2, "channel", now=NOW)

    again = await moves.post_latest(bot, bot.guild, 5, 2, "channel", now=NOW)

    assert len(real(bot).sent) == 2
    assert again.message.endswith("2 were already up, so they were not posted again.")


async def test_post_the_latest_takes_a_test_copy_over_a_rehearsal_row(bot):
    await moves.tick(bot, bot.guild, NOW)

    done = await moves.post_latest(bot, bot.guild, 5, 1, "channel", now=NOW)

    assert done.ok and len(real(bot).sent) == 1
    assert (await store.get(bot.db, GUILD, NEWEST_URI))["status"] == rules.POSTED


async def test_to_the_test_channel_posts_again_and_touches_no_row(bot):
    await moves.post_latest(bot, bot.guild, 5, 1, "channel", now=NOW)

    done = await moves.post_latest(bot, bot.guild, 5, 1, "test", now=NOW)

    assert done.ok
    [copy_] = home(bot).sent
    assert copy_.content.startswith("Test copy ·")
    assert (await store.get(bot.db, GUILD, NEWEST_URI))["status"] == rules.POSTED
    assert "bluesky.rehearsed" in await kinds(bot.db)


async def test_post_to_test_is_one_post_in_the_test_channel(bot):
    done = await moves.rehearse(bot, bot.guild, 5, via=VIA_WEBSITE, now=NOW)

    assert done.ok and len(home(bot).sent) == 1 and real(bot).sent == []
    assert await store.recent(bot.db, GUILD, 5) == []
    [logged] = await details_of(bot.db, "web.bluesky.rehearsed")
    assert logged["count"] == 1 and logged["where"] == "test" and logged["via"] == "website"
    assert home(bot).sent[0].kwargs["view"] is not None


VIDEO_URI = "at://did:plc:4lijy65gdkw6gwwctvm6kxoc/app.bsky.feed.post/3myisto7wfc2y"
REPOST_RKEY = "3mykng2umee2q"


async def test_post_to_test_by_uri_sends_that_seen_post_whatever_its_status(bot):
    await moves.tick(bot, bot.guild, NOW)
    assert (await store.get(bot.db, GUILD, VIDEO_URI))["status"] == rules.SKIPPED_OLD

    done = await moves.rehearse(bot, bot.guild, 5, VIDEO_URI, via=VIA_WEBSITE, now=NOW)

    assert done.ok, done.message
    copy_ = home(bot).sent[-1]
    assert copy_.content.splitlines() == [
        f"Test copy · while bluesky_mode is on this goes to <#{REAL}>",
        "🦋 **Black in a Flash!** posted on Bluesky",
    ]
    assert copy_.kwargs["allowed_mentions"].roles is False
    assert copy_.kwargs["view"].children[0].url.endswith("/post/3myisto7wfc2y")
    assert real(bot).sent == []
    assert (await store.get(bot.db, GUILD, VIDEO_URI))["status"] == rules.SKIPPED_OLD
    [logged] = await details_of(bot.db, "web.bluesky.rehearsed")
    assert logged["uri"] == VIDEO_URI and logged["message_id"] == copy_.id


async def test_post_to_test_by_uri_keeps_a_reposts_line(bot):
    await moves.tick(bot, bot.guild, NOW)
    [uri] = [
        entry["post"]["uri"]
        for entry in recorded()["feed"]
        if entry["post"]["uri"].endswith(REPOST_RKEY)
    ]

    done = await moves.rehearse(bot, bot.guild, 5, uri, now=NOW)

    assert done.ok
    assert home(bot).sent[-1].content.splitlines()[1] == (
        "🔁 **Black in a Flash!** reposted **@gamesdonequick.com**"
    )


async def test_post_to_test_by_uri_refuses_a_post_never_seen(bot):
    done = await moves.rehearse(bot, bot.guild, 5, "at://nobody/app.bsky.feed.post/x", now=NOW)

    assert not done.ok and done.code == "not_seen" and done.status == 404
    assert "has not seen" in done.message and home(bot).sent == []


class RoutedFetch(FakeFetch):
    def __init__(self, posts):
        super().__init__({"feed": []})
        self.posts = posts

    async def __call__(self, url, headers, seconds):
        self.urls.append((url, headers))
        if "getPosts" in url:
            return 200, json.dumps({"posts": self.posts}).encode()
        return 200, json.dumps(self.payload).encode()


async def test_post_to_test_by_uri_asks_bluesky_for_a_post_gone_from_the_feed(bot):
    entry = copy.deepcopy(recorded()["feed"][0])
    item = rules.item_of(entry)
    await store.record(bot.db, GUILD, item, rules.POSTED, NOW)
    bot.bluesky_fetch = RoutedFetch([entry["post"]])

    done = await moves.rehearse(bot, bot.guild, 5, item.uri, now=NOW)

    assert done.ok, done.message
    assert "getPosts" in bot.bluesky_fetch.urls[-1][0]
    assert home(bot).sent[-1].kwargs["embed"].url == item.url


async def test_post_to_test_by_uri_says_so_when_bluesky_has_lost_the_post(bot):
    item = rules.item_of(recorded()["feed"][0])
    await store.record(bot.db, GUILD, item, rules.POSTED, NOW)
    bot.bluesky_fetch = RoutedFetch([])

    done = await moves.rehearse(bot, bot.guild, 5, item.uri, now=NOW)

    assert not done.ok and done.code == "gone" and home(bot).sent == []


async def test_post_to_test_by_uri_says_why_when_bluesky_cannot_be_read(bot):
    await moves.tick(bot, bot.guild, NOW)
    bot.bluesky_fetch.status = 403

    done = await moves.rehearse(bot, bot.guild, 5, NEWEST_URI, now=NOW)

    assert not done.ok and done.code == "read_failed" and done.status == 502
    assert "Bluesky answered 403" in done.message


@pytest.mark.parametrize(
    ("count", "where", "code"),
    [
        (0, "channel", "bad_count"),
        (11, "test", "bad_count"),
        ("x", "test", "bad_count"),
        (2, "elsewhere", "bad_where"),
    ],
)
async def test_a_bad_ask_is_refused_in_words(bot, count, where, code):
    done = await moves.post_latest(bot, bot.guild, 5, count, where, now=NOW)

    assert not done.ok and done.code == code and done.status == 400
    assert real(bot).sent == [] and home(bot).sent == []


async def test_the_channel_choice_needs_the_channel_but_not_the_mode(bot):
    await bot.store.set(GUILD, "bluesky_mode", "off")
    assert (await moves.post_latest(bot, bot.guild, 5, 1, "channel", now=NOW)).ok
    await bot.store.clear(GUILD, "bluesky_channel_id")

    done = await moves.post_latest(bot, bot.guild, 5, 1, "channel", now=NOW)

    assert not done.ok and done.message == rules.NO_CHANNEL


async def test_an_unreadable_feed_posts_nothing_and_says_why(bot):
    bot.bluesky_fetch.status = 403

    done = await moves.post_latest(bot, bot.guild, 5, 2, "channel", now=NOW)

    assert not done.ok and "Bluesky answered 403" in done.message
    assert real(bot).sent == []


async def test_nothing_eligible_is_refused(bot):
    bot.bluesky_fetch = with_feed([recorded()["feed"][4]])

    done = await moves.post_latest(bot, bot.guild, 5, 2, "channel", now=NOW)

    assert not done.ok and done.code == "nothing"


async def test_read_now_reads_whatever_the_clock_says_and_logs_from_the_site(bot):
    await moves.tick(bot, bot.guild, NOW)

    done = await moves.read_now(bot, bot.guild, 5, via=VIA_WEBSITE, now=NOW)

    assert done.ok
    assert done.message == "Read 30 post(s) from @blackinaflash.bsky.social: 0 new, 0 sent."
    assert "web.bluesky.read_now" in await kinds(bot.db)


async def test_read_now_while_off_is_refused(bot):
    await bot.store.set(GUILD, "bluesky_mode", "off")

    done = await moves.read_now(bot, bot.guild, 5, now=NOW)

    assert not done.ok and done.code == "bluesky_off"


async def test_status_reports_health_and_the_recent_rows(bot):
    bot.bluesky_fetch = FakeFetch()
    await moves.tick(bot, bot.guild, NOW)

    found = await moves.status(bot, bot.guild, NOW)

    assert found["mode"] == "shadow" and found["channel_id"] == str(REAL)
    assert found["test_home"] == str(HOME) and found["seed_count"] == 2
    assert found["last_ok_at"] == NOW.isoformat() and found["failures"] == 0
    assert found["next_read_at"] == (NOW + timedelta(minutes=5)).isoformat()
    top = found["recent"][0]
    assert top["status"] == rules.WOULD_POST and top["message_url"].endswith(
        str(home(bot).sent[0].id)
    )
    assert top["url"].startswith("https://bsky.app/profile/")
    assert all(len(row["text"]) <= 80 for row in found["recent"])
