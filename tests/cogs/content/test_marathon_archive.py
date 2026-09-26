from datetime import timedelta

from black_bloc import marathon_archive as ma
from black_bloc.cogs.content.marathon import (
    build_card,
    build_panel,
    create_marathon,
    get_marathon,
    list_marathons,
    marathon_by_ref,
    marathon_for_event,
    pair_runner,
    remove_marathon,
    runs_of,
    update_marathon,
)
from black_bloc.cogs.content.marathon_archive import (
    archive_marathon,
    archive_one,
    archived_marathon,
    archived_pairings,
    archived_people_state,
    archived_runs,
    build_archive,
    count_archived,
    list_archived,
    marathon_by_id_any,
    restore_marathon,
)
from black_bloc.cogs.content.marathon_feeds import marathons_by_ref
from black_bloc.cogs.content.spotlight import add_window, channel_by_id, spotlight_channel
from tests.cogs.content.test_marathon import (  # noqa: F401
    NOW,
    URL,
    added,
    bot,
    cog,
)
from tests.cogs.content.test_spotlight import GUILD, FakeActor, details_of, kinds

LATER = NOW + timedelta(days=8)


async def count(bot, kind):  # noqa: F811
    return (await kinds(bot.db)).count(kind)


async def second(bot, cog):  # noqa: F811
    made = await create_marathon(
        bot, bot.guild, FakeActor(), name="SGDQ 2027", url=URL.replace("74", "75")
    )
    assert made.ok, made.message
    return made.value


async def test_the_tick_archives_one_ended_marathon_per_pass_after_the_grace(bot, cog):  # noqa: F811
    first = await added(bot, cog)
    other = await second(bot, cog)
    cog.clock = lambda: NOW + timedelta(days=2)
    await cog.tick_once()
    assert len(await list_marathons(bot.db, GUILD)) == 2

    cog.clock = lambda: LATER
    await cog.tick_once()
    assert len(await list_marathons(bot.db, GUILD)) == 1
    assert await count_archived(bot.db, GUILD) == 1
    await cog.tick_once()
    assert await list_marathons(bot.db, GUILD) == []
    moved = {row["id"] for row in await list_archived(bot.db, GUILD)}
    assert moved == {first["id"], other["id"]}
    assert await count(bot, "marathon.archived") == 2


async def test_the_grace_is_a_setting_and_zero_moves_it_the_same_day(bot, cog):  # noqa: F811
    await bot.store.set(GUILD, "marathon_archive_after_days", 0)
    await added(bot, cog)
    cog.clock = lambda: NOW + timedelta(hours=4)
    await cog.tick_once()
    assert await count_archived(bot.db, GUILD) == 1


async def test_a_marathon_with_no_dates_never_moves_by_itself(bot, cog):  # noqa: F811
    marathon = await added(bot, cog)
    await update_marathon(bot.db, marathon["id"], starts_at=None, ends_at=None)
    cog.clock = lambda: NOW + timedelta(days=400)
    assert await archive_one(cog, bot.guild, await list_marathons(bot.db, GUILD)) is False
    assert await count_archived(bot.db, GUILD) == 0


async def test_runs_and_people_travel_and_the_effects_are_dropped(bot, cog):  # noqa: F811
    marathon = await added(bot, cog)
    await pair_runner(bot, bot.guild, FakeActor(), marathon, "Somebody", 42)
    await pair_runner(bot, bot.guild, FakeActor(), marathon, "Elsewhere", 43, everywhere=True)
    _, row = await spotlight_channel(bot, bot.guild, FakeActor(), "skyruns", keep=True)
    await bot.db.conn.execute(
        "INSERT INTO marathon_spotlights(marathon_id, login, spotlight_id, added_at) "
        "VALUES (?, 'skyruns', ?, ?)",
        (marathon["id"], row["id"], NOW.isoformat()),
    )
    await add_window(
        bot.db,
        GUILD,
        row["id"],
        NOW.isoformat(),
        NOW.isoformat(),
        source="marathon",
        source_id=marathon["id"],
    )
    await bot.db.conn.commit()
    runs = len(await runs_of(bot.db, marathon["id"]))

    cog.clock = lambda: LATER
    await cog.tick_once()

    assert await get_marathon(bot.db, GUILD, marathon["id"]) is None
    assert await runs_of(bot.db, marathon["id"]) == []
    assert len(await archived_runs(bot.db, marathon["id"])) == runs == 5
    assert [one["runner_name"] for one in await archived_pairings(bot.db, marathon["id"])] == [
        "somebody"
    ]
    for sql in (
        "SELECT COUNT(*) FROM marathon_people WHERE marathon_id IS NOT NULL",
        "SELECT COUNT(*) FROM marathon_spotlights",
        "SELECT COUNT(*) FROM spotlight_ping_windows WHERE source = 'marathon'",
    ):
        cur = await bot.db.conn.execute(sql)
        assert (await cur.fetchone())[0] == 0, sql
    cur = await bot.db.conn.execute("SELECT COUNT(*) FROM marathon_people")
    assert (await cur.fetchone())[0] == 1
    kept = await archived_marathon(bot.db, GUILD, marathon["id"])
    assert (kept["archived_why"], kept["archived_by"]) == ("ended", None)
    assert kept["archived_at"] == LATER.isoformat()
    said = await details_of(bot.db, "marathon.archived")
    assert said["runs"] == 5 and said["baf"] == 4 and said["archived_why"] == "ended"
    assert said["ref"] == "74" and said["source"] == "gdq"


async def test_the_sweep_calls_off_no_event_but_staff_moves_do(bot, cog, monkeypatch):  # noqa: F811
    called = []

    async def cancel(bot, guild, actor, marathon, **kwargs):
        called.append(marathon["id"])

    monkeypatch.setattr("black_bloc.cogs.content.marathon_archive.cancel_linked_event", cancel)
    first = await added(bot, cog)
    cog.clock = lambda: LATER
    await cog.tick_once()
    assert await archived_marathon(bot.db, GUILD, first["id"]) is not None
    assert called == []
    other = await second(bot, cog)
    await archive_marathon(bot, bot.guild, FakeActor(), other)
    assert called == [other["id"]]


async def test_an_archived_marathon_holds_no_channel_spotlight(bot, cog):  # noqa: F811
    _, row = await spotlight_channel(
        bot, bot.guild, FakeActor(), "rpglimitbreak", keep=True, spotlight=False
    )
    marathon = await added(bot, cog, channel=row)
    assert (await channel_by_id(bot.db, row["id"]))["spotlit_by_marathon"] == marathon["id"]

    done = await archive_marathon(bot, bot.guild, FakeActor(), marathon)

    assert done.ok and "in the archive" in done.message
    fresh = await channel_by_id(bot.db, row["id"])
    assert (fresh["spotlight"], fresh["spotlit_by_marathon"], fresh["expires_at"]) == (
        0,
        None,
        None,
    )
    assert (await details_of(bot.db, "marathon.spotlight_lifted"))["because"] == ma.BECAUSE_ARCHIVED
    assert (await archived_marathon(bot.db, GUILD, marathon["id"]))["archived_why"] == "staff"


async def test_the_feed_dedupe_and_the_next_event_see_an_archived_ref(bot, cog):  # noqa: F811
    marathon = await added(bot, cog)
    await archive_marathon(bot, bot.guild, FakeActor(), marathon)

    known = await marathons_by_ref(bot.db, GUILD, "gdq")
    assert set(known) == {"74"} and known["74"]["archived"] == 1
    assert (await marathon_by_ref(bot.db, GUILD, "gdq", "74"))["id"] == marathon["id"]


async def test_a_removed_marathon_is_archived_and_left_to_the_feeds_ignore_list(bot, cog):  # noqa: F811
    marathon = await added(bot, cog)
    done = await remove_marathon(bot, bot.guild, FakeActor(), marathon)

    assert done.ok and "off the list and in the archive" in done.message
    kept = await archived_marathon(bot.db, GUILD, marathon["id"])
    assert kept["archived_why"] == "removed"
    assert await marathons_by_ref(bot.db, GUILD, "gdq") == {}
    assert (await details_of(bot.db, "marathon.removed"))["archived_why"] == "removed"
    assert await count(bot, "marathon.archived") == 0


async def test_restore_copies_it_back_paused_with_its_runs_and_people(bot, cog):  # noqa: F811
    marathon = await added(bot, cog)
    await pair_runner(bot, bot.guild, FakeActor(), marathon, "Somebody", 42)
    await archive_marathon(bot, bot.guild, FakeActor(), marathon)

    done = await restore_marathon(bot, bot.guild, FakeActor(), marathon["id"])

    assert done.ok and "back on the list, paused" in done.message
    fresh = await get_marathon(bot.db, GUILD, marathon["id"])
    assert fresh["active"] == 0 and fresh["name"] == "AGDQ 2027"
    assert len(await runs_of(bot.db, marathon["id"])) == 5
    cur = await bot.db.conn.execute(
        "SELECT runner_name FROM marathon_people WHERE marathon_id = ?", (marathon["id"],)
    )
    assert [row[0] for row in await cur.fetchall()] == ["somebody"]
    assert await archived_marathon(bot.db, GUILD, marathon["id"]) is None
    assert await archived_runs(bot.db, marathon["id"]) == []
    said = await details_of(bot.db, "marathon.restored")
    assert said["archived_why"] == "staff" and said["runs"] == 5


async def test_restore_refuses_in_words_when_nothing_is_archived_or_the_link_is_taken(bot, cog):  # noqa: F811
    missing = await restore_marathon(bot, bot.guild, FakeActor(), 999)
    assert not missing.ok and missing.status == 404 and "999" in missing.message

    marathon = await added(bot, cog)
    await archive_marathon(bot, bot.guild, FakeActor(), marathon)
    again = await added(bot, cog)
    taken = await restore_marathon(bot, bot.guild, FakeActor(), marathon["id"])
    assert not taken.ok and taken.status == 409
    assert "AGDQ 2027" in taken.message
    assert await archived_marathon(bot.db, GUILD, marathon["id"]) is not None
    assert (await get_marathon(bot.db, GUILD, again["id"]))["active"] == 1


async def test_an_event_keeps_its_marathon_line_after_the_move(bot, cog):  # noqa: F811
    marathon = await added(bot, cog)
    await update_marathon(bot.db, marathon["id"], event_id=321)
    await archive_marathon(bot, bot.guild, FakeActor(), marathon)

    assert (await marathon_for_event(bot.db, GUILD, 321))["id"] == marathon["id"]
    assert (await marathon_by_id_any(bot.db, GUILD, marathon["id"]))["name"] == "AGDQ 2027"


async def test_the_archived_people_card_reads_its_own_pairings(bot, cog):  # noqa: F811
    marathon = await added(bot, cog)
    await pair_runner(bot, bot.guild, FakeActor(), marathon, "Somebody", 42)
    await archive_marathon(bot, bot.guild, FakeActor(), marathon)

    state = await archived_people_state(
        bot, bot.guild, await archived_marathon(bot.db, GUILD, marathon["id"])
    )
    assert {one["name"] for one in state["baf"]} >= {"Somebody", "Sky"}


async def test_the_panel_offers_archive_it_on_a_card_and_the_archive_from_the_root(bot, cog):  # noqa: F811
    marathon = await added(bot, cog)
    _, card = await build_card(bot, bot.guild, marathon["id"])
    assert ma.ARCHIVE_MOVE.label in [getattr(one, "label", None) for one in card.children]
    _, root = await build_panel(bot, bot.guild, FakeActor())
    assert ma.ARCHIVE_LIST_MOVE.label in [getattr(one, "label", None) for one in root.children]

    embed, _ = await build_archive(bot, bot.guild)
    assert embed.title == "Archive · 0" and "7 day(s)" in embed.description
    await archive_marathon(bot, bot.guild, FakeActor(), marathon)
    embed, view = await build_archive(bot, bot.guild)
    assert embed.title == "Archive · 1" and "AGDQ 2027" in embed.description
    assert any(getattr(one, "placeholder", "") == ma.PICK_ARCHIVED for one in view.children)
