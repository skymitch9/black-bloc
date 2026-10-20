from __future__ import annotations

from black_bloc import optouts
from black_bloc.api.tools.optouts import SOURCES, roll_up
from black_bloc.cogs.content.marathon import update_marathon
from black_bloc.cogs.content.spotlight import add_channel, update_channel
from tests.api.conftest import WebRole
from tests.api.tools.test_marathons import add, cog  # noqa: F401

AT = "2026-10-18T22:00:00+00:00"
CREW, KEPT, POSTS, LIVE, CHATTY, CAKE, FAST, GONE, QUIET, HIDDEN = range(31, 41)
IGNORE_ROLE = 6200


async def seed(web, wf, client, sign_in):
    sign_in(client)
    db, guild = web.db, web.guild
    role = WebRole(6100, "Staff", position=3)
    ignored = WebRole(IGNORE_ROLE, "Lurker", position=1)
    guild.roles.extend([role, ignored])
    for user_id, name in ((CREW, "crew"), (KEPT, "kept"), (POSTS, "posty"), (QUIET, "quiet")):
        wf.member(guild, user_id, name=name)
    guild.get_member(CREW).roles.append(role)
    guild.get_member(KEPT).roles.append(role)
    guild.get_member(QUIET).roles.append(ignored)
    await web.store.set(wf.GUILD_ID, "marathon_optout_role_ids", [6100])
    await web.store.set(wf.GUILD_ID, "golive_ignore_role_id", IGNORE_ROLE)
    marathon_id = add(client).json()["id"]
    await update_marathon(db, marathon_id, announce_opt_out=f"[{POSTS}, {CREW}]")
    await db.conn.execute(
        "INSERT INTO marathon_baf_overrides(user_id, by, at, reason) VALUES (?, ?, ?, ?)",
        (KEPT, 7, AT, "runs with us every year"),
    )
    await db.conn.commit()
    for user_id, kind in (
        (LIVE, optouts.ANNOUNCE),
        (CHATTY, optouts.CHAT_MEMORY),
        (CAKE, optouts.BIRTHDAY),
        (FAST, optouts.PBS),
        (HIDDEN, optouts.STREAMER_LIST),
        (GONE, optouts.CHAT_MEMORY_IN),
    ):
        await optouts.set_out(db, wf.GUILD_ID, user_id, kind, at=AT)
    out = await add_channel(
        db, wf.GUILD_ID, "esamarathon", added_by=7, expires_at=None, pin=False,
        display_name="ESA",
    )
    await update_channel(db, out, marathons=0)
    await add_channel(db, wf.GUILD_ID, "takesthem", added_by=7, expires_at=None, pin=False)
    return marathon_id, out


def chips_of(found, user_id):
    row = next(one for one in found["people"] if one["user_id"] == str(user_id))
    return {one["source"]: one for one in row["chips"]}, row


async def test_every_source_lands_on_its_own_person_with_one_chip_each(
    client, sign_in, web, cog, wf  # noqa: F811
):
    marathon_id, esa = await seed(web, wf, client, sign_in)

    found = await roll_up(web, web.guild)

    assert found["sources"] == list(SOURCES)
    assert {one["user_id"] for one in found["people"]} == {
        str(one) for one in (CREW, POSTS, LIVE, CHATTY, CAKE, FAST, QUIET, HIDDEN)
    }
    crew, row = chips_of(found, CREW)
    assert list(crew) == ["marathon_role", "marathon_posts"] and row["here"] is True
    assert crew["marathon_role"]["said"] == "not BaF (Staff)"
    assert crew["marathon_role"]["rule"]["move"] == "set"
    posts, _ = chips_of(found, POSTS)
    assert posts["marathon_posts"]["said"] == "opted out of posts"
    assert posts["marathon_posts"]["marathons"] == [{"id": marathon_id, "name": "AGDQ 2027"}]
    quiet, _ = chips_of(found, QUIET)
    assert list(quiet) == ["golive_ignore_role"]
    assert quiet["golive_ignore_role"]["said"] == "ignored by role (Lurker)"
    for user_id, source in (
        (LIVE, "announce"),
        (CHATTY, "chat_memory"),
        (CAKE, "birthday"),
        (FAST, "pbs"),
        (HIDDEN, "streamer_list"),
    ):
        chips, row = chips_of(found, user_id)
        assert list(chips) == [source] and row["here"] is False and row["name"] == str(user_id)
    assert found["channels"] == [{"id": esa, "login": "esamarathon", "name": "ESA"}]


async def test_staff_overrides_are_their_own_counted_in_list_never_an_opt_out(
    client, sign_in, web, cog, wf  # noqa: F811
):
    await seed(web, wf, client, sign_in)

    found = await roll_up(web, web.guild)

    assert str(KEPT) not in {one["user_id"] for one in found["people"]}
    (kept,) = found["counted_in"]
    assert kept["user_id"] == str(KEPT) and kept["username"] == "kept"
    assert kept["said"] == "BaF (staff override)"
    assert kept["reason"] == "runs with us every year"
    assert kept["by"] == "7" and kept["at"] == AT
    assert kept["rule"]["move"] == "clear" and kept["rule"]["move_label"] == "Undo the override"


async def test_an_override_saved_before_reasons_reads_no_reason_given(
    client, sign_in, web, cog, wf  # noqa: F811
):
    await seed(web, wf, client, sign_in)
    await web.db.conn.execute("UPDATE marathon_baf_overrides SET reason = NULL")
    await web.db.conn.commit()

    (kept,) = (await roll_up(web, web.guild))["counted_in"]

    assert kept["reason"] == "no reason given"


async def test_the_roll_up_reads_only_the_one_table_and_not_the_old_stores(
    client, sign_in, web, cog, wf  # noqa: F811
):
    sign_in(client)
    rows = (
        ("INSERT INTO golive_optout(user_id, at) VALUES (?, ?)", (LIVE, AT)),
        (
            "INSERT INTO chat_memory_optout(user_id, guild_id, at) VALUES (?, ?, ?)",
            (CHATTY, wf.GUILD_ID, AT),
        ),
    )
    for sql, values in rows:
        await web.db.conn.execute(sql, values)
    await web.db.conn.commit()

    found = await roll_up(web, web.guild)

    assert found["people"] == [] and found["counted_in"] == []


async def test_a_consent_flip_no_longer_turns_an_opt_out_into_nothing(
    client, sign_in, web, cog, wf  # noqa: F811
):
    await seed(web, wf, client, sign_in)
    await web.store.set(wf.GUILD_ID, "chat_memory_consent", "optin")

    found = await roll_up(web, web.guild)

    assert list(chips_of(found, CHATTY)[0]) == ["chat_memory"]
    assert str(GONE) not in {one["user_id"] for one in found["people"]}


async def test_the_roll_up_writes_nothing(client, sign_in, web, cog, wf):  # noqa: F811
    await seed(web, wf, client, sign_in)
    cur = await web.db.conn.execute("SELECT COUNT(*) AS n FROM action_log")
    before = (await cur.fetchone())["n"]

    await roll_up(web, web.guild)

    cur = await web.db.conn.execute("SELECT COUNT(*) AS n FROM action_log")
    assert (await cur.fetchone())["n"] == before


