from types import SimpleNamespace

import pytest

from black_bloc.channel_reach import (
    back_to_rule,
    clear_override,
    openers_for,
    override_for,
    overrides_for,
    refresh,
    set_override,
    set_shown,
)
from black_bloc.cogs.community.role_menus import add_option, create_menu
from black_bloc.config import load_settings
from black_bloc.directory import Known, known_of, open_channels
from black_bloc.logkinds import VIA_WEBSITE
from black_bloc.settings_store import SettingsStore

GUILD = 7
ACTOR = 900
MEMBER = SimpleNamespace(id=444, name="Member")
SPORTS = SimpleNamespace(id=555, name="Sports")
RUNNER = SimpleNamespace(id=556, name="Runner")
EVERYONE = SimpleNamespace(id=GUILD, name="@everyone")
ROLES = {one.id: one for one in (MEMBER, SPORTS, RUNNER)}
BASEMENT = SimpleNamespace(id=77, name="The Basement")


def text(channel_id, name, *readers, cat=None):
    def permissions_for(role):
        return SimpleNamespace(view_channel=any(role is one for one in readers))

    return SimpleNamespace(
        id=channel_id,
        name=name,
        topic=None,
        category=cat,
        category_id=getattr(cat, "id", None),
        permissions_for=permissions_for,
    )


GENERAL = text(1, "general-chat", MEMBER)
SPORTS_BALL = text(2, "sports-ball", SPORTS)
RUN_PREP = text(3, "run-prep", RUNNER)
CELLAR = text(4, "cellar", SPORTS, cat=BASEMENT)


class Guild:
    id = GUILD
    default_role = EVERYONE
    text_channels = [GENERAL, SPORTS_BALL, RUN_PREP, CELLAR]

    def get_role(self, role_id):
        return ROLES.get(role_id)


class Bot:
    def __init__(self, db, store):
        self.db = db
        self.store = store
        self.guild = Guild()


@pytest.fixture
async def bot(db, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    store = SettingsStore(db, load_settings(_env_file=None, test_mode=True))
    await store.load()
    await store.set(GUILD, "chat_visibility_role_id", MEMBER.id)
    await store.set(GUILD, "chat_ignore_categories", [BASEMENT.id])
    return Bot(db, store)


@pytest.fixture
def actor():
    return SimpleNamespace(id=ACTOR, display_name="Lead", mention=f"<@{ACTOR}>")


async def kinds(db):
    cur = await db.conn.execute("SELECT kind FROM action_log ORDER BY id")
    return [row["kind"] for row in await cur.fetchall()]


async def menus(db):
    picked = await create_menu(db, GUILD, "interests", "Interests", None, "multiple")
    await add_option(db, picked, SPORTS.id, "Sports", None)
    handed = await create_menu(db, GUILD, "runner-status", "Runner status", None, "staff")
    await add_option(db, handed, RUNNER.id, "Runner", None)
    other = await create_menu(db, GUILD + 1, "elsewhere", "Elsewhere", None, "multiple")
    await add_option(db, other, 999, "Theirs", None)


async def test_an_override_is_stored_read_replaced_and_cleared(db):
    assert await override_for(db, GUILD, 1) is None
    await set_override(db, GUILD, 1, True, by=ACTOR)
    await set_override(db, GUILD, 2, False)
    assert await overrides_for(db, GUILD) == {1: True, 2: False}
    await set_override(db, GUILD, 1, False)
    assert await override_for(db, GUILD, 1) is False
    assert await clear_override(db, GUILD, 1) is True
    assert await clear_override(db, GUILD, 1) is False
    assert await overrides_for(db, GUILD + 1) == {}


async def test_the_self_assignable_roles_are_this_guilds_menu_roles_and_no_staff_menu(db):
    await menus(db)
    assert await openers_for(db, GUILD) == frozenset({SPORTS.id})


async def test_a_refresh_is_what_the_directory_reads_until_the_next_one(bot):
    await menus(bot.db)
    assert known_of(bot, bot.guild) == Known()
    known = await refresh(bot, bot.guild)
    assert known == Known(frozenset({SPORTS.id}), {})
    assert known_of(bot, bot.guild) == known
    assert [c.name for c in open_channels(bot, bot.guild)] == ["general-chat", "sports-ball"]


async def test_a_refresh_that_cannot_read_keeps_the_last_good_one(bot):
    await menus(bot.db)
    good = await refresh(bot, bot.guild)
    bot.db = SimpleNamespace(is_connected=True, conn=None)
    assert await refresh(bot, bot.guild) == good


async def test_staff_tell_the_bot_about_a_channel_and_put_it_back(bot, actor):
    said = await set_shown(bot, bot.guild, actor, RUN_PREP.id, True, via=VIA_WEBSITE)
    assert said.ok and "told about **#run-prep**" in said.message
    assert [c.name for c in open_channels(bot, bot.guild)] == ["general-chat", "run-prep"]
    again = await set_shown(bot, bot.guild, actor, RUN_PREP.id, True, via=VIA_WEBSITE)
    assert again.ok

    back = await back_to_rule(bot, bot.guild, actor, RUN_PREP.id, via=VIA_WEBSITE)
    assert "back to the rule" in back.message
    assert [c.name for c in open_channels(bot, bot.guild)] == ["general-chat"]
    nothing = await back_to_rule(bot, bot.guild, actor, RUN_PREP.id, via=VIA_WEBSITE)
    assert "already follows the rule" in nothing.message
    assert await kinds(bot.db) == [
        "web.chat.channel_reach_set",
        "web.chat.channel_reach_cleared",
    ]


async def test_staff_hide_a_channel_members_can_read(bot, actor):
    said = await set_shown(bot, bot.guild, actor, GENERAL.id, False)
    assert said.ok and "not told about **#general-chat**" in said.message
    assert open_channels(bot, bot.guild) == []
    assert await kinds(bot.db) == ["chat.channel_reach_set"]


async def test_the_basement_cannot_be_shown_by_staff_and_the_refusal_says_why(bot, actor):
    await menus(bot.db)
    refused = await set_shown(bot, bot.guild, actor, CELLAR.id, True, via=VIA_WEBSITE)
    assert not refused.ok and refused.status == 409 and refused.code == "ignored_category"
    assert "leaves out on purpose" in refused.message
    assert await override_for(bot.db, GUILD, CELLAR.id) is None
    assert (await back_to_rule(bot, bot.guild, actor, CELLAR.id)).status == 409
    known = await refresh(bot, bot.guild)
    assert "cellar" not in [c.name for c in open_channels(bot, bot.guild, known)]
    assert await kinds(bot.db) == []


async def test_a_channel_that_is_not_here_is_refused_in_words(bot, actor):
    refused = await set_shown(bot, bot.guild, actor, 12345, True)
    assert not refused.ok and refused.status == 404
    assert "not a text channel" in refused.message
