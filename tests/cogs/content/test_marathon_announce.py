# ruff: noqa: F401, F811
from black_bloc import marathon_announce as ma
from black_bloc.cogs.content import marathon_announce as announce
from tests.cogs.content.test_marathon import SKY, bot, cog
from tests.cogs.content.test_marathon_host_highlights import ANARCHY, HIDDEN_HEROES, show
from tests.cogs.content.test_marathon_runner_posts import fresh
from tests.cogs.content.test_spotlight import GUILD, FakeActor, kinds


async def test_the_people_a_marathon_can_announce_are_its_baf_runners_and_hosts(bot, cog):
    marathon = await show(bot, cog, HIDDEN_HEROES)
    assert await announce.baf_people(bot, bot.guild, marathon) == {ANARCHY: "anarchy"}


async def test_the_writer_refuses_in_words_and_writes_once(bot, cog):
    marathon = await show(bot, cog, HIDDEN_HEROES)
    bad = await announce.set_opt_out(bot, bot.guild, FakeActor(), marathon, [ANARCHY], "maybe")
    assert not bad.ok and bad.status == 422 and bad.code == ma.BAD_OPT_CODE
    stranger = await announce.set_opt_out(bot, bot.guild, FakeActor(), marathon, [SKY], True)
    assert not stranger.ok and stranger.status == 404 and "Hidden Heroes" in stranger.message

    for _ in range(2):
        said = await announce.set_opt_out(bot, bot.guild, FakeActor(), marathon, [ANARCHY], "out")
        assert said.ok and "**anarchy** is opted out of **Hidden Heroes**" in said.message
    assert ma.opted_out(await fresh(bot, marathon)) == {ANARCHY}
    assert (await kinds(bot.db)).count("marathon.announce_opted_out") == 1

    said = await announce.set_opt_out(bot, bot.guild, FakeActor(), marathon, [ANARCHY], "in")
    assert said.ok and ma.opted_out(await fresh(bot, marathon)) == set()
    assert "marathon.announce_opted_in" in await kinds(bot.db)


async def test_the_switch_follows_the_default_key(bot, cog):
    marathon = await show(bot, cog, HIDDEN_HEROES)
    assert announce.announces(bot, GUILD, marathon)
    await bot.store.set(GUILD, "marathon_announcements_default", False)
    assert not announce.announces(bot, GUILD, marathon)
