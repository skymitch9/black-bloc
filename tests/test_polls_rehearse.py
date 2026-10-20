import json
from types import SimpleNamespace

import discord
import pytest

from black_bloc import polls_rehearse as testing
from black_bloc.cogs.community.polls import poll_plan
from black_bloc.config import load_settings
from black_bloc.logkinds import VIA_WEBSITE
from black_bloc.settings_store import SettingsStore
from tests.test_sticky_posts import FakeGuard, FakeGuild, forbidden

GUILD = 7
HOME = 444
LOG = 222
STAFFER = 1


@pytest.fixture
async def bot(db, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    store = SettingsStore(db, load_settings(_env_file=None))
    await store.load()
    guild = FakeGuild()
    await store.set(GUILD, "shadow_channel_id", HOME)
    return SimpleNamespace(
        db=db, store=store, guard=None, guild=guild, get_channel=guild.get_channel
    )


def plan_of(bot, **asked):
    found, trouble = poll_plan(
        bot.store, GUILD, question=asked.pop("question", "Which night?"), **asked
    )
    assert found is not None, trouble
    return found


async def rows(db):
    cur = await db.conn.execute("SELECT kind, details FROM action_log ORDER BY id")
    return [(row["kind"], json.loads(row["details"])) for row in await cur.fetchall()]


async def test_a_native_poll_gets_one_real_looking_copy_and_nothing_is_written(bot, db):
    plan = plan_of(bot, kind="single", options="Friday | Saturday")

    outcome = await testing.rehearse(bot, bot.guild, STAFFER, plan, via=VIA_WEBSITE)

    assert outcome.ok and outcome.message == testing.TESTED.format(where=HOME)
    [copy] = bot.guild.get_channel(HOME).messages
    sent = copy.kwargs["poll"]
    assert isinstance(sent, discord.Poll) and [one.text for one in sent.answers] == [
        "Friday",
        "Saturday",
    ]
    assert copy.content == "<@1> started a poll."
    assert copy.kwargs["allowed_mentions"].to_dict() == discord.AllowedMentions.none().to_dict()
    [(kind, details)] = await rows(db)
    assert kind == "web.poll.rehearsed" and details["shadow_home"] == HOME
    cur = await db.conn.execute("SELECT COUNT(*) FROM polls")
    assert (await cur.fetchone())[0] == 0


async def test_a_panel_poll_copy_carries_the_card_and_no_buttons_a_vote_could_reach(bot):
    plan = plan_of(bot, kind="single", options="a | b", anonymous=True)
    assert plan["surface"] == "panel"

    outcome = await testing.rehearse(bot, bot.guild, STAFFER, plan)

    assert outcome.ok
    [copy] = bot.guild.get_channel(HOME).messages
    assert copy.kwargs["embed"].title == "Which night?" and "view" not in copy.kwargs


async def test_refusals_are_worded_and_send_nothing(bot):
    plan = plan_of(bot, kind="yesno")

    await bot.store.set(GUILD, "poll_mode", "off")
    off = await testing.rehearse(bot, bot.guild, STAFFER, plan)
    assert (off.code, off.message) == ("polls_off", testing.TEST_OFF)

    await bot.store.set(GUILD, "poll_mode", "on")
    bot.guard = FakeGuard(allowed=LOG)
    guarded = await testing.rehearse(bot, bot.guild, STAFFER, plan)
    assert guarded.code == "test_mode" and str(HOME) in guarded.message

    bot.guard = None
    bot.guild.get_channel(HOME).send_raises = forbidden()
    failed = await testing.rehearse(bot, bot.guild, STAFFER, plan)
    assert failed.code == "post_failed" and "403" in failed.message
    assert bot.guild.get_channel(HOME).messages == []


async def test_with_no_home_the_log_channel_is_where_the_copy_goes(bot):
    await bot.store.clear(GUILD, "shadow_channel_id")
    await bot.store.set(GUILD, "log_channel_id", LOG)

    outcome = await testing.rehearse(bot, bot.guild, STAFFER, plan_of(bot, kind="yesno"))

    assert outcome.ok and len(bot.guild.get_channel(LOG).messages) == 1
