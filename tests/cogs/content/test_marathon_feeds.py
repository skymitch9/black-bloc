import json
import pathlib
import re
from datetime import UTC, datetime, timedelta

import pytest

from black_bloc import marathon as mt
from black_bloc import marathon_feeds as mf
from black_bloc.cogs.content import marathon as cogmod
from black_bloc.cogs.content import marathon_feeds as feeds
from black_bloc.cogs.content.marathon import (
    Marathons,
    create_marathon,
    get_marathon,
    list_marathons,
    remove_marathon,
    runs_of,
)
from black_bloc.cogs.content.spotlight import forget_spotlight
from black_bloc.marathon_sources import Person, Run, ScheduleError
from tests.cogs.content.test_marathon import STAFF_ROOM, Member, bot  # noqa: F401
from tests.cogs.content.test_spotlight import (
    GUILD,
    SHADOW_CHANNEL,
    FakeActor,
    FakeChannel,
    FakeInteraction,
    details_of,
    kinds,
)

FIXTURES = pathlib.Path(__file__).parents[2] / "fixtures" / "marathon"
SEPT = datetime(2026, 9, 25, 18, 0, tzinfo=UTC)
GDQ_BASE = "https://tracker.gamesdonequick.com/tracker"
ESA_MEMBER = 4242


def fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class FeedClient:
    def __init__(self):
        self.tracker = {
            "gdq": fixture("gdq_events_list.json")["results"],
            "rpglb": fixture("rpglb_events_list.json")["results"],
        }
        self.horaro = {"esa": fixture("horaro_esa_schedules.json")["data"]}
        self.runs_by_ref = {}
        self.raises = None
        self.list_calls = []

    async def events(self, source="gdq"):
        self.list_calls.append(source)
        if self.raises is not None:
            raise self.raises
        return list(self.tracker.get(source, []))

    async def horaro_schedules(self, slug):
        self.list_calls.append(f"horaro:{slug}")
        if self.raises is not None:
            raise self.raises
        if slug not in self.horaro:
            raise ScheduleError(f"horaro.net has no event {slug}")
        return list(self.horaro[slug])

    async def resolve(self, source, ref):
        return (str(ref), f"{source} {ref}")

    async def runs(self, source, ref):
        return list(self.runs_by_ref.get((source, str(ref)), []))

    async def close(self):
        return None


@pytest.fixture
def cog(bot):  # noqa: F811
    made = Marathons(bot)
    made.client = FeedClient()
    made.clock = lambda: SEPT
    bot.cogs[cogmod.COG_NAME] = made
    return made


async def a_channel(bot, login, name=None):  # noqa: F811
    cur = await bot.db.conn.execute(
        "INSERT INTO spotlight_channels(guild_id, twitch_login, display_name, added_at) "
        "VALUES (?, ?, ?, ?)",
        (GUILD, login, name or login, SEPT.isoformat()),
    )
    await bot.db.conn.commit()
    return int(cur.lastrowid)


async def staff_room(bot):  # noqa: F811
    bot.guild.channels[STAFF_ROOM] = FakeChannel(STAFF_ROOM)
    await bot.store.set(GUILD, "staff_channel_id", STAFF_ROOM)


def notices(bot):  # noqa: F811
    return bot.guild.channels[STAFF_ROOM].messages


async def all_feeds(bot):  # noqa: F811
    return await feeds.list_feeds(bot.db, GUILD)


async def seeded(bot, cog):  # noqa: F811
    await staff_room(bot)
    gdq = await a_channel(bot, "gamesdonequick", "GamesDoneQuick")
    await a_channel(bot, "rpglimitbreak", "RPG Limit Break")
    await a_channel(bot, "esamarathon", "ESAMarathon")
    return gdq


async def checked_of(bot, name):  # noqa: F811
    cur = await bot.db.conn.execute(
        "SELECT details FROM action_log WHERE kind = 'marathon.feed_checked' ORDER BY id DESC"
    )
    for row in await cur.fetchall():
        found = json.loads(row["details"])
        if found["feed"] == name:
            return found
    return None


def later(cog, hours):
    cog.clock = lambda: SEPT + timedelta(hours=hours)


# --- the seed ---------------------------------------------------------------------------------


async def test_the_seed_makes_the_gdq_and_rpglb_feeds_once_and_never_esa(bot, cog):  # noqa: F811
    await seeded(bot, cog)
    await cog.tick_once()
    await cog.tick_once()
    rows = await all_feeds(bot)
    assert [(one["name"], one["source"], one["feed_ref"]) for one in rows] == [
        ("GDQ", "tracker", GDQ_BASE),
        ("RPG Limit Break", "tracker", "https://tracker.rpglimitbreak.com"),
    ]
    assert all(one["action"] == "add" for one in rows)
    assert (await kinds(bot.db)).count("marathon.feed_seeded") == 1


async def test_a_seeded_feed_staff_remove_is_not_seeded_again_on_the_next_boot(bot, cog):  # noqa: F811
    await seeded(bot, cog)
    await cog.tick_once()
    gdq = (await all_feeds(bot))[0]
    await feeds.remove_feed(bot, bot.guild, FakeActor(), gdq)
    again = Marathons(bot)
    again.client = FeedClient()
    again.clock = lambda: SEPT
    bot.cogs[cogmod.COG_NAME] = again
    await again.tick_once()
    assert [one["name"] for one in await all_feeds(bot)] == ["RPG Limit Break"]


async def test_the_seed_waits_for_a_channel_row_and_the_switch(bot, cog):  # noqa: F811
    await staff_room(bot)
    await bot.store.set(GUILD, "marathon_feeds", False)
    await a_channel(bot, "gamesdonequick")
    await cog.tick_once()
    assert await all_feeds(bot) == []
    await bot.store.set(GUILD, "marathon_feeds", True)
    cog.feeds_seeded.clear()
    await cog.tick_once()
    assert [one["name"] for one in await all_feeds(bot)] == ["GDQ"]


# --- add mode ---------------------------------------------------------------------------------


async def test_a_check_adds_every_new_event_on_the_feeds_channel_with_one_notice_each(
    bot,  # noqa: F811
    cog,
):
    gdq = await seeded(bot, cog)
    await cog.tick_once()
    made = {row["source_ref"]: row for row in await list_marathons(bot.db, GUILD)}
    assert sorted(made) == ["71", "72", "73", "74"]
    agdq = made["74"]
    assert agdq["name"] == "Awesome Games Done Quick 2027"
    assert agdq["schedule_url"] == "https://tracker.gamesdonequick.com/tracker/event/74"
    assert agdq["spotlight_id"] == gdq and agdq["added_by"] is None
    feed = (await all_feeds(bot))[0]
    assert {row["feed_id"] for row in made.values()} == {feed["id"]}
    assert len(notices(bot)) == 4
    words = [one.content for one in notices(bot)]
    assert any("GDQ has a new event: **Awesome Games Done Quick 2027**" in one for one in words)
    labels = [child.item.label for child in notices(bot)[0].kwargs["view"].children]
    assert labels == ["Pause it", "Remove it"]
    added = await details_of(bot.db, "marathon.feed_added")
    assert added["feed"] == "GDQ" and added["automatic"] is True
    assert (await details_of(bot.db, "marathon.added"))["feed_id"] == feed["id"]
    assert (await checked_of(bot, "GDQ"))["added"] == 4


async def test_the_make_event_wish_follows_the_setting(bot, cog):  # noqa: F811
    await seeded(bot, cog)
    await bot.store.set(GUILD, "marathon_event_mode_default", "marathon")
    await cog.tick_once()
    rows = await list_marathons(bot.db, GUILD)
    assert rows and all(one["event_mode"] == "marathon" and one["event_id"] is None for one in rows)


async def test_never_the_same_event_twice_even_six_hours_later(bot, cog):  # noqa: F811
    await seeded(bot, cog)
    await cog.tick_once()
    later(cog, 7)
    await cog.tick_once()
    assert len(await list_marathons(bot.db, GUILD)) == 4
    assert len(notices(bot)) == 4
    checked = await checked_of(bot, "GDQ")
    assert checked["new"] == 0 and checked["added"] == 0


async def test_a_feed_is_not_checked_again_before_its_gap(bot, cog):  # noqa: F811
    await seeded(bot, cog)
    await cog.tick_once()
    calls = len(cog.client.list_calls)
    later(cog, 5)
    await cog.tick_once()
    assert len(cog.client.list_calls) == calls


async def test_an_event_already_on_the_list_is_adopted_not_added(bot, cog):  # noqa: F811
    await seeded(bot, cog)
    await create_marathon(
        bot, bot.guild, FakeActor(), name="AGDQ", url="https://gamesdonequick.com/schedule/74"
    )
    await cog.tick_once()
    rows = await list_marathons(bot.db, GUILD)
    assert len(rows) == 4
    feed = (await all_feeds(bot))[0]
    assert next(one for one in rows if one["source_ref"] == "74")["feed_id"] == feed["id"]
    assert (await checked_of(bot, "GDQ"))["adopted"] == 1


async def test_a_removed_feed_marathon_is_ignored_and_forget_ignored_adds_it_again(
    bot,  # noqa: F811
    cog,
):
    await seeded(bot, cog)
    await cog.tick_once()
    agdq = next(one for one in await list_marathons(bot.db, GUILD) if one["source_ref"] == "74")
    await remove_marathon(bot, bot.guild, FakeActor(), agdq)
    feed = (await all_feeds(bot))[0]
    assert mf.ignored_of(feed) == ["74"]
    assert (await details_of(bot.db, "marathon.feed_ignored"))["event"] == "74"
    later(cog, 7)
    await cog.tick_once()
    assert "74" not in {one["source_ref"] for one in await list_marathons(bot.db, GUILD)}

    forgot = await feeds.forget_ignored(bot, bot.guild, FakeActor(), feed)
    assert forgot.ok and "forgot 1" in forgot.message
    again = await feeds.check_now(bot, bot.guild, FakeActor(), feed)
    assert again.ok and "1 added" in again.message
    assert "74" in {one["source_ref"] for one in await list_marathons(bot.db, GUILD)}
    nothing = await feeds.forget_ignored(bot, bot.guild, FakeActor(), feed)
    assert not nothing.ok and nothing.code == "nothing_ignored"


async def test_pause_it_and_remove_it_on_the_notice_are_the_marathons_own_moves(
    bot,  # noqa: F811
    cog,
):
    await seeded(bot, cog)
    await cog.tick_once()
    notice = notices(bot)[0]
    pause = notice.kwargs["view"].children[0].item
    match = re.fullmatch(feeds.FEED_TEMPLATE, pause.custom_id)
    button = await feeds.FeedButton.from_custom_id(None, None, match)
    marathon_id = int(match["ref"])

    bot.store.is_staff = lambda member: False
    stranger = FakeInteraction(bot, Member(42), bot.guild)
    stranger.message = notice
    await button.on_click(stranger)
    assert "staff only" in stranger.sent
    assert (await get_marathon(bot.db, GUILD, marathon_id))["active"] == 1

    bot.store.is_staff = lambda member: True
    lead = FakeInteraction(bot, FakeActor(), bot.guild)
    lead.message = notice
    await button.on_click(lead)
    assert (await get_marathon(bot.db, GUILD, marathon_id))["active"] == 0
    assert "Paused by" in notice.content and notice.edits[-1]["view"] is None

    remove = feeds.FeedButton(int(match["feed_id"]), str(marathon_id), "remove")
    other = FakeInteraction(bot, FakeActor(), bot.guild)
    other.message = notice
    await remove.on_click(other)
    assert await get_marathon(bot.db, GUILD, marathon_id) is None
    feed = (await all_feeds(bot))[0]
    assert str((await details_of(bot.db, "marathon.removed"))["marathon_id"]) == str(marathon_id)
    assert len(mf.ignored_of(feed)) == 1


# --- suggest mode -----------------------------------------------------------------------------


async def suggest_mode(bot, cog):  # noqa: F811
    await seeded(bot, cog)
    await bot.store.set(GUILD, "marathon_feed_action_default", "suggest")
    await cog.tick_once()
    return (await all_feeds(bot))[0]


async def test_suggest_mode_records_and_notices_and_adds_nothing(bot, cog):  # noqa: F811
    feed = await suggest_mode(bot, cog)
    assert await list_marathons(bot.db, GUILD) == []
    assert [one["ref"] for one in mf.open_suggestions(feed)] == ["71", "72", "73", "74"]
    assert all(one.get("notice_message_id") for one in mf.suggested_of(feed))
    labels = [child.item.label for child in notices(bot)[0].kwargs["view"].children]
    assert labels == ["Add it", "Not this one"]
    assert (await kinds(bot.db)).count("marathon.feed_suggested") == 4


async def test_add_it_makes_the_marathon_and_folds_the_notice(bot, cog):  # noqa: F811
    feed = await suggest_mode(bot, cog)
    took = await feeds.take_suggestion(bot, bot.guild, FakeActor(), feed, "74")
    assert took.ok
    marathon = took.value
    assert marathon["source_ref"] == "74" and marathon["feed_id"] == feed["id"]
    feed = await feeds.get_feed(bot.db, GUILD, feed["id"])
    assert "74" not in [one["ref"] for one in mf.suggested_of(feed)]
    folded = [one for one in notices(bot) if "Added by" in (one.content or "")]
    assert len(folded) == 1
    gone = await feeds.take_suggestion(bot, bot.guild, FakeActor(), feed, "74")
    assert not gone.ok and gone.code == "suggestion_gone"


async def test_a_dismissal_sticks_until_look_again_clears_it(bot, cog):  # noqa: F811
    feed = await suggest_mode(bot, cog)
    done = await feeds.dismiss_suggestion(bot, bot.guild, FakeActor(), feed, "73")
    assert done.ok
    later(cog, 7)
    await cog.tick_once()
    feed = await feeds.get_feed(bot.db, GUILD, feed["id"])
    assert [one["ref"] for one in mf.dismissed_of(feed)] == ["73"]
    assert "73" not in [one["ref"] for one in mf.open_suggestions(feed)]
    assert any(one.content.startswith("~~") for one in notices(bot))

    looked = await feeds.look_again(bot, bot.guild, FakeActor(), feed)
    assert looked.ok and "forgot 1" in looked.message
    feed = await feeds.get_feed(bot.db, GUILD, feed["id"])
    assert mf.dismissed_of(feed) == []
    assert "73" in [one["ref"] for one in mf.open_suggestions(feed)]


# --- failures, pause, shadow ------------------------------------------------------------------


async def test_a_failed_check_counts_and_the_third_is_important(bot, cog):  # noqa: F811
    await seeded(bot, cog)
    cog.client.raises = ScheduleError("the GDQ tracker answered 503")
    for hours in (0, 7, 14):
        later(cog, hours)
        await cog.tick_once()
    feed = (await all_feeds(bot))[0]
    assert feed["checks_failed"] == 3 and feed["last_ok"] == 0
    assert "answered 503" in feed["last_error"]
    assert (await kinds(bot.db)).count("marathon.feed_stale") == 2
    cog.client.raises = None
    later(cog, 21)
    await cog.tick_once()
    assert (await all_feeds(bot))[0]["checks_failed"] == 0


async def test_a_paused_feed_checks_nothing(bot, cog):  # noqa: F811
    await seeded(bot, cog)
    await bot.store.set(GUILD, "marathon_feeds", True)
    await cog.tick_once()
    feed = (await all_feeds(bot))[0]
    paused = await feeds.set_feed(bot, bot.guild, FakeActor(), feed, active=False)
    assert paused.ok and "paused" in paused.message
    calls = len(cog.client.list_calls)
    later(cog, 30)
    await cog.tick_once()
    assert cog.client.list_calls.count("gdq") == 1
    assert len(cog.client.list_calls) == calls + 1


async def test_shadow_adds_the_marathon_but_notices_the_shadow_home(bot, cog):  # noqa: F811
    await seeded(bot, cog)
    await bot.store.set(GUILD, "marathon_mode", "shadow")
    await cog.tick_once()
    assert len(await list_marathons(bot.db, GUILD)) == 4
    assert notices(bot) == []
    shadow = bot.guild.channels[SHADOW_CHANNEL].messages
    shadowed = [one for one in shadow if "new event" in one.content]
    assert len(shadowed) == 4 and f"<#{STAFF_ROOM}>" in shadowed[0].content
    found = await kinds(bot.db)
    assert "marathon.would_feed_add" in found and "marathon.feed_added" not in found


async def test_off_checks_nothing(bot, cog):  # noqa: F811
    await seeded(bot, cog)
    await bot.store.set(GUILD, "marathon_mode", "off")
    await cog.tick_once()
    assert await all_feeds(bot) == [] and cog.client.list_calls == []


# --- staff doors ------------------------------------------------------------------------------


async def test_add_a_feed_refuses_in_words_and_one_channel_has_one_feed(bot, cog):  # noqa: F811
    await staff_room(bot)
    esa = await a_channel(bot, "esamarathon", "ESAMarathon")
    nowhere = await feeds.create_feed(bot, bot.guild, FakeActor(), spotlight_id=999, pick="gdq")
    assert not nowhere.ok and nowhere.message == mf.NO_CHANNEL
    odd = await feeds.create_feed(bot, bot.guild, FakeActor(), spotlight_id=esa, pick="oengus")
    assert not odd.ok and odd.code == "unknown_source"
    blank = await feeds.create_feed(bot, bot.guild, FakeActor(), spotlight_id=esa, pick="horaro")
    assert not blank.ok and blank.code == "no_slug"
    silent = await feeds.create_feed(
        bot, bot.guild, FakeActor(), spotlight_id=esa, pick="horaro", slug="nope"
    )
    assert not silent.ok and silent.code == "slug_unreadable"
    assert "horaro.net has no event nope" in silent.message

    made = await feeds.create_feed(
        bot, bot.guild, FakeActor(), spotlight_id=esa, pick="horaro", slug="ESA", action="suggest"
    )
    assert made.ok, made.message
    assert made.value["feed_ref"] == "esa" and made.value["name"] == "ESAMarathon"
    assert "horaro.net/esa" in made.message
    twice = await feeds.create_feed(bot, bot.guild, FakeActor(), spotlight_id=esa, pick="gdq")
    assert not twice.ok and twice.code == "channel_has_feed"
    assert (await details_of(bot.db, "marathon.feed_created"))["source"] == "horaro"


async def test_removing_a_channel_removes_its_feed_and_keeps_its_marathons(bot, cog):  # noqa: F811
    gdq = await seeded(bot, cog)
    await cog.tick_once()
    feed = (await all_feeds(bot))[0]
    await forget_spotlight(bot, bot.guild, FakeActor(), gdq)
    assert feed["id"] not in {one["id"] for one in await all_feeds(bot)}
    rows = await list_marathons(bot.db, GUILD)
    assert len(rows) == 4 and all(one["feed_id"] is None for one in rows)
    gone = await details_of(bot.db, "marathon.feed_removed")
    assert gone["because"] == "channel_removed" and gone["marathons"] == 4


async def test_an_esa_schedule_matches_by_discord_username_and_pairing_never_by_link(
    bot,  # noqa: F811
    cog,
    monkeypatch,
):
    await staff_room(bot)
    esa = await a_channel(bot, "esamarathon", "ESAMarathon")

    class Someone:
        def __init__(self, user_id, name):
            self.id, self.name, self.bot = user_id, name, False

    monkeypatch.setattr(
        bot.guild, "members", [Someone(ESA_MEMBER, "spaceloz"), Someone(1, "hypnoshark")],
        raising=False,
    )
    ref = "esa/2026-summer2"
    cog.client.runs_by_ref[("horaro", ref)] = [
        Run("a", 1, "Doronko Wanko", "Doronko Wanko", "Any%", None, None, 60,
            (Person("spaceloz", None, "runner"),)),
        Run("b", 2, "Croc 2", "Croc 2", "Any%", None, None, 60,
            (Person("hypnoshark", "hypnoshark", "runner"),)),
        Run("c", 3, "Willow", "Willow", "Any%", None, None, 60,
            (Person("the_bagler", None, "runner"),)),
    ]
    made = await create_marathon(
        bot, bot.guild, FakeActor(), name="ESA", url=f"https://horaro.net/{ref}", spotlight_id=esa
    )
    assert made.ok, made.message
    rows = {one["game"]: one for one in await runs_of(bot.db, made.value["id"])}
    assert mt.member_ids(rows["Doronko Wanko"]) == [ESA_MEMBER]
    assert mt.member_ids(rows["Croc 2"]) == []
    await cogmod.pair_runner(bot, bot.guild, FakeActor(), made.value, "the_bagler", ESA_MEMBER)
    rows = {one["game"]: one for one in await runs_of(bot.db, made.value["id"])}
    assert mt.member_ids(rows["Willow"]) == [ESA_MEMBER]


# --- /event ▸ Marathons… ▸ Feeds… --------------------------------------------------------------


async def test_the_feeds_panel_lists_feeds_and_a_feed_card_draws_only_valid_moves(
    bot,  # noqa: F811
    cog,
):
    await seeded(bot, cog)
    await a_channel(bot, "speedstuff4charity", "Speed Stuff 4 Charity")
    await cog.tick_once()
    embed, view = await feeds.feeds_card(bot, bot.guild)
    assert "**GDQ** · GDQ tracker · GamesDoneQuick · adds" in embed.description
    labels = [getattr(one, "label", None) for one in view.children]
    assert "Add a feed…" in labels and "Back" in labels
    feed = (await all_feeds(bot))[0]
    embed, view = await feeds.feed_card(bot, bot.guild, feed["id"])
    labels = [one.label for one in view.children if isinstance(one, cogmod.MarathonMoveButton)]
    assert labels[:3] == ["Check now", "Pause", "Suggest instead of adding"]
    assert "Rename…" in labels and "Move to channel…" in labels
    assert "Look again" not in labels and "Forget ignored" not in labels
    assert "Awesome Games Done Quick 2027" in embed.description


async def test_the_marathon_root_offers_feeds_to_staff(bot, cog):  # noqa: F811
    embed, view = await cogmod.build_panel(bot, bot.guild, FakeActor())
    assert "Feeds…" in [getattr(one, "label", None) for one in view.children]
    lead = FakeInteraction(bot, FakeActor(), bot.guild)
    await feeds.feed_move(lead, view, mt.FEEDS)
    assert mf.FEEDS_TITLE == lead.edits[-1]["embed"].title


async def test_add_a_feed_in_the_panel_picks_a_channel_then_opens_the_modal(bot, cog):  # noqa: F811
    await staff_room(bot)
    await a_channel(bot, "esamarathon", "ESAMarathon")
    embed, view = await feeds.channel_card(bot, bot.guild)
    pick = next(one for one in view.children if isinstance(one, feeds.ChannelPick))
    pick._values = [pick.options[0].value]
    lead = FakeInteraction(bot, FakeActor(), bot.guild)
    await pick.callback(lead)
    modal = lead.response.modals[0]
    assert isinstance(modal, feeds.AddFeedModal) and modal.source.default == "horaro"
