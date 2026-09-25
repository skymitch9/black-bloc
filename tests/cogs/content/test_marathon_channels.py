from black_bloc import marathon_channels as mc
from black_bloc.cogs.content import marathon_feeds as feeds
from black_bloc.cogs.content.marathon import (
    Marathons,
    create_marathon,
    get_marathon,
    set_active,
    set_channel,
)
from black_bloc.cogs.content.marathon_channels import set_marathons
from black_bloc.cogs.content.spotlight import channel_by_id, run_spotlight_move
from tests.cogs.content.test_marathon import bot  # noqa: F401
from tests.cogs.content.test_marathon_feeds import (  # noqa: F401
    FeedClient,
    a_channel,
    all_feeds,
    cog,
    seeded,
    staff_room,
)
from tests.cogs.content.test_spotlight import GUILD, FakeActor, details_of, kinds

GDQ_URL = "https://gamesdonequick.com/schedule/74"


async def a_marathon(bot, spotlight_id, url=GDQ_URL):  # noqa: F811
    made = await create_marathon(
        bot, bot.guild, FakeActor(), name="AGDQ 2027", url=url, spotlight_id=spotlight_id
    )
    assert made.ok, made.message
    return made.value


async def rows_of(bot, kind):  # noqa: F811
    cur = await bot.db.conn.execute(
        "SELECT details FROM action_log WHERE kind = ? ORDER BY id", (kind,)
    )
    import json

    return [json.loads(row["details"]) for row in await cur.fetchall()]


async def test_the_boot_seed_opts_esa_out_once_and_a_staff_turn_back_on_sticks(bot, cog):  # noqa: F811
    await seeded(bot, cog)
    await feeds.tick_feeds(cog, bot.guild)
    esa = await feeds.channel_by_login_in(bot.db, GUILD, "esamarathon")
    gdq = await feeds.channel_by_login_in(bot.db, GUILD, "gamesdonequick")

    assert mc.takes_marathons(gdq) and not mc.takes_marathons(esa)
    set_row = await details_of(bot.db, "golive.channel_marathons_set")
    assert set_row["login"] == "esamarathon" and set_row["to"] is False
    assert set_row["via"] == "boot"

    await set_marathons(bot, bot.guild, FakeActor(), esa["id"], True)
    again = Marathons(bot)
    again.client = FeedClient()
    again.clock = cog.clock
    await feeds.tick_feeds(again, bot.guild)
    assert mc.takes_marathons(await channel_by_id(bot.db, esa["id"]))


async def test_adding_a_marathon_on_an_opted_out_channel_is_refused_in_words(bot, cog):  # noqa: F811
    esa = await a_channel(bot, "esamarathon", "ESAMarathon")
    await set_marathons(bot, bot.guild, FakeActor(), esa, False)

    made = await create_marathon(
        bot, bot.guild, FakeActor(), name="ESA", url=GDQ_URL, spotlight_id=esa
    )

    assert not made.ok and made.status == 409 and made.code == "channel_opted_out"
    assert made.message == mc.OPTED_OUT_REFUSAL.format(channel="ESAMarathon")


async def test_moving_a_marathon_onto_an_opted_out_channel_is_refused(bot, cog):  # noqa: F811
    gdq = await a_channel(bot, "gamesdonequick", "GamesDoneQuick")
    esa = await a_channel(bot, "esamarathon", "ESAMarathon")
    marathon = await a_marathon(bot, gdq)
    await set_marathons(bot, bot.guild, FakeActor(), esa, False)

    moved = await set_channel(bot, bot.guild, FakeActor(), marathon, esa)

    assert not moved.ok and moved.code == "channel_opted_out"
    assert (await get_marathon(bot.db, GUILD, marathon["id"]))["spotlight_id"] == gdq


async def test_opting_out_holds_the_feed_and_the_marathons_and_back_on_lets_only_those_go(
    bot, cog  # noqa: F811
):
    await staff_room(bot)
    gdq = await a_channel(bot, "gamesdonequick", "GamesDoneQuick")
    made = await feeds.create_feed(bot, bot.guild, FakeActor(), spotlight_id=gdq, pick="gdq")
    assert made.ok, made.message
    held = await a_marathon(bot, gdq, "https://gamesdonequick.com/schedule/80")
    staff_paused = await a_marathon(bot, gdq, "https://gamesdonequick.com/schedule/81")
    await set_active(bot, bot.guild, FakeActor(), staff_paused, False)

    _, said = await set_marathons(bot, bot.guild, FakeActor(), gdq, False)

    feed = (await all_feeds(bot))[0]
    assert not feed["active"] and feed["held_by_channel"] == 1
    fresh = await get_marathon(bot.db, GUILD, held["id"])
    assert not fresh["active"] and fresh["held_by_channel"] == 1
    assert (await get_marathon(bot.db, GUILD, staff_paused["id"]))["held_by_channel"] == 0
    cur = await bot.db.conn.execute("SELECT COUNT(*) FROM marathons WHERE held_by_channel = 1")
    assert f"{(await cur.fetchone())[0]} marathon(s)" in said
    paused = [one for one in await rows_of(bot, "marathon.paused") if one.get("because")]
    assert paused[-1]["because"] == "channel_opted_out" and paused[-1]["automatic"] is True
    assert (await details_of(bot.db, "marathon.feed_paused"))["because"] == "channel_opted_out"

    refused = await set_active(bot, bot.guild, FakeActor(), fresh, True)
    assert not refused.ok and refused.code == "held_by_channel"
    again = await feeds.set_feed(bot, bot.guild, FakeActor(), feed, active=True)
    assert not again.ok and again.code == "held_by_channel"

    await set_marathons(bot, bot.guild, FakeActor(), gdq, True)

    assert (await all_feeds(bot))[0]["active"] == 1
    assert (await get_marathon(bot.db, GUILD, held["id"]))["active"] == 1
    assert (await get_marathon(bot.db, GUILD, staff_paused["id"]))["active"] == 0
    resumed = await rows_of(bot, "marathon.resumed")
    assert resumed[-1]["because"] == "channel_opted_in"


async def test_a_feed_cannot_be_added_on_or_moved_to_an_opted_out_channel(bot, cog):  # noqa: F811
    await staff_room(bot)
    gdq = await a_channel(bot, "gamesdonequick", "GamesDoneQuick")
    esa = await a_channel(bot, "esamarathon", "ESAMarathon")
    await set_marathons(bot, bot.guild, FakeActor(), esa, False)

    refused = await feeds.create_feed(
        bot, bot.guild, FakeActor(), spotlight_id=esa, pick="horaro", slug="esa"
    )
    assert not refused.ok and refused.code == "channel_opted_out"
    assert [int(one["id"]) for one in await feeds.free_channels(bot, bot.guild)] == [gdq]

    made = await feeds.create_feed(bot, bot.guild, FakeActor(), spotlight_id=gdq, pick="gdq")
    moved = await feeds.set_feed(bot, bot.guild, FakeActor(), made.value, spotlight_id=esa)
    assert not moved.ok and moved.code == "channel_opted_out"


async def test_the_seed_makes_no_feed_for_a_channel_that_is_opted_out(bot, cog):  # noqa: F811
    await staff_room(bot)
    gdq = await a_channel(bot, "gamesdonequick", "GamesDoneQuick")
    await set_marathons(bot, bot.guild, FakeActor(), gdq, False)

    assert await feeds.seed_feeds(bot, bot.guild) == []
    assert await all_feeds(bot) == []


async def test_the_same_setting_twice_changes_nothing_and_logs_nothing(bot, cog):  # noqa: F811
    gdq = await a_channel(bot, "gamesdonequick", "GamesDoneQuick")
    _, said = await set_marathons(bot, bot.guild, FakeActor(), gdq, True)
    assert said == mc.MARATHONS_SAME.format(login="gamesdonequick", state="takes marathons")
    assert "golive.channel_marathons_set" not in await kinds(bot.db)


async def test_the_channels_panel_turns_marathons_off_and_on(bot, cog):  # noqa: F811
    gdq = await a_channel(bot, "gamesdonequick", "GamesDoneQuick")

    said, kept = await run_spotlight_move(bot, bot.guild, FakeActor(), gdq, "marathons_off")
    assert kept and "opted out of marathons" in said
    assert not mc.takes_marathons(await channel_by_id(bot.db, gdq))

    said, _ = await run_spotlight_move(bot, bot.guild, FakeActor(), gdq, "marathons_on")
    assert "takes marathons again" in said
    assert mc.takes_marathons(await channel_by_id(bot.db, gdq))
