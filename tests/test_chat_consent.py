from types import SimpleNamespace

from black_bloc import chat_consent, optouts
from black_bloc.chat_memory import remembers, set_remembered
from black_bloc.config import load_settings
from black_bloc.settings_store import SettingsStore

GUILD = 7
CHOSE_OUT, CHOSE_IN, NOBODY, ANOTHER, ROBOT = 31, 32, 33, 34, 35


def a_guild():
    members = [
        SimpleNamespace(id=one, bot=False) for one in (CHOSE_OUT, CHOSE_IN, NOBODY, ANOTHER)
    ]
    members.append(SimpleNamespace(id=ROBOT, bot=True))
    return SimpleNamespace(id=GUILD, members=members)


async def a_bot(db):
    store = SettingsStore(db, load_settings(_env_file=None))
    await store.load()
    return SimpleNamespace(db=db, store=store)


async def chosen(db):
    await set_remembered(db, CHOSE_OUT, GUILD, consent="optout", wanted=False)
    await optouts.set_out(db, GUILD, CHOSE_IN, optouts.CHAT_MEMORY_IN, by=CHOSE_IN)


async def test_moving_to_opt_in_counts_everyone_remembered_today_who_never_asked(db):
    await chosen(db)

    assert await chat_consent.changing(db, a_guild(), "optin") == [NOBODY, ANOTHER]


async def test_the_question_names_the_count_and_nothing_changes_says_nothing(db):
    bot = await a_bot(db)
    await chosen(db)

    asked = await chat_consent.asked(bot, a_guild(), "optin")

    assert asked == "**2** members would stop being remembered. Press again to change it."
    assert await chat_consent.asked(bot, a_guild(), "optout") is None
    assert await chat_consent.asked(bot, a_guild(), "nonsense") is None


async def test_the_flip_to_opt_in_writes_rows_for_the_people_it_moved(db):
    bot = await a_bot(db)
    await chosen(db)
    await bot.store.set(GUILD, "chat_memory_consent", "optin")

    found = await chat_consent.flipped(bot, a_guild(), "optout", "optin", SimpleNamespace(id=9))

    assert found == {"from": "optout", "to": "optin", "count": 2}
    implicit = {
        int(row["user_id"]): row
        for row in await optouts.rows(db, GUILD, (optouts.CHAT_MEMORY,))
        if row["reason"] == optouts.IMPLICIT
    }
    assert set(implicit) == {NOBODY, ANOTHER} and implicit[NOBODY]["by"] == 9
    for user_id, wanted in ((CHOSE_OUT, False), (CHOSE_IN, True), (NOBODY, False)):
        assert await remembers(db, user_id, GUILD, consent="optin") is wanted, user_id


async def test_flipping_back_lifts_only_the_rows_the_flip_wrote(db):
    bot = await a_bot(db)
    await chosen(db)
    guild = a_guild()
    await chat_consent.flipped(bot, guild, "optout", "optin", 9)

    assert await chat_consent.changing(db, guild, "optout") == [NOBODY, ANOTHER]
    found = await chat_consent.flipped(bot, guild, "optin", "optout", 9)

    assert found["count"] == 2
    assert await optouts.out_of(db, GUILD, optouts.CHAT_MEMORY) == {CHOSE_OUT}
    for user_id, wanted in ((CHOSE_OUT, False), (CHOSE_IN, True), (NOBODY, True)):
        assert await remembers(db, user_id, GUILD, consent="optout") is wanted, user_id


async def test_a_flip_to_the_same_model_moves_nobody(db):
    bot = await a_bot(db)

    assert await chat_consent.flipped(bot, a_guild(), "optout", "optout", 9) is None
    assert await optouts.rows(db, GUILD) == []
