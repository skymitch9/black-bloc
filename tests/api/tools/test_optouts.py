from __future__ import annotations

from black_bloc.api.tools.optouts import SOURCES, roll_up
from black_bloc.cogs.content.marathon import update_marathon
from black_bloc.cogs.content.spotlight import add_channel, update_channel
from tests.api.conftest import WebRole
from tests.api.tools.test_marathons import add, cog  # noqa: F401

AT = "2026-10-18T22:00:00+00:00"
CREW, KEPT, POSTS, LIVE, CHATTY, CAKE, FAST, GONE = 31, 32, 33, 34, 35, 36, 37, 38


async def seed(web, wf, client, sign_in):
    sign_in(client)
    db, guild = web.db, web.guild
    role = WebRole(6100, "Staff", position=3)
    guild.roles.append(role)
    for user_id, name in ((CREW, "crew"), (KEPT, "kept"), (POSTS, "posty")):
        wf.member(guild, user_id, name=name)
    guild.get_member(CREW).roles.append(role)
    guild.get_member(KEPT).roles.append(role)
    await web.store.set(wf.GUILD_ID, "marathon_optout_role_ids", [6100])
    marathon_id = add(client).json()["id"]
    await update_marathon(db, marathon_id, announce_opt_out=f"[{POSTS}, {CREW}]")
    rows = (
        ("INSERT INTO marathon_baf_overrides(user_id, by, at) VALUES (?, ?, ?)", (KEPT, 7, AT)),
        ("INSERT INTO golive_optout(user_id, at) VALUES (?, ?)", (LIVE, AT)),
        (
            "INSERT INTO chat_memory_optout(user_id, guild_id, at) VALUES (?, ?, ?)",
            (CHATTY, wf.GUILD_ID, AT),
        ),
        (
            "INSERT INTO birthdays(user_id, guild_id, month, day, opted_in, source, set_at) "
            "VALUES (?, ?, 1, 2, 0, 'self', ?)",
            (CAKE, wf.GUILD_ID, AT),
        ),
        (
            "INSERT INTO birthdays(user_id, guild_id, month, day, opted_in, source, set_at) "
            "VALUES (?, ?, 3, 4, 1, 'self', ?)",
            (POSTS, wf.GUILD_ID, AT),
        ),
        (
            "INSERT INTO pb_matches(guild_id, user_id, state, state_by, updated_at) "
            "VALUES (?, ?, 'opted_out', 'member', ?)",
            (wf.GUILD_ID, FAST, AT),
        ),
        (
            "INSERT INTO pb_matches(guild_id, user_id, state, state_by, updated_at) "
            "VALUES (?, ?, 'matched', 'staff', ?)",
            (wf.GUILD_ID, GONE, AT),
        ),
    )
    for sql, values in rows:
        await db.conn.execute(sql, values)
    await db.conn.commit()
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
        str(one) for one in (CREW, KEPT, POSTS, LIVE, CHATTY, CAKE, FAST)
    }
    crew, row = chips_of(found, CREW)
    assert list(crew) == ["marathon_role", "marathon_posts"] and row["here"] is True
    assert crew["marathon_role"]["said"] == "not BaF (Staff)"
    assert crew["marathon_role"]["rule"]["move"] == "set"
    kept, _ = chips_of(found, KEPT)
    assert list(kept) == ["marathon_override"]
    assert kept["marathon_override"]["said"] == "BaF (staff override)"
    assert kept["marathon_override"]["rule"]["move"] == "clear"
    posts, _ = chips_of(found, POSTS)
    assert posts["marathon_posts"]["said"] == "opted out of posts"
    assert posts["marathon_posts"]["marathons"] == [{"id": marathon_id, "name": "AGDQ 2027"}]
    for user_id, source in ((LIVE, "golive"), (CHATTY, "chat_memory"), (CAKE, "birthdays")):
        chips, row = chips_of(found, user_id)
        assert list(chips) == [source] and row["here"] is False and row["name"] == str(user_id)
    assert list(chips_of(found, FAST)[0]) == ["pbs"]
    assert found["channels"] == [{"id": esa, "login": "esamarathon", "name": "ESA"}]


async def test_chat_memory_rows_are_not_opt_outs_when_the_server_default_is_off(
    client, sign_in, web, cog, wf  # noqa: F811
):
    await seed(web, wf, client, sign_in)
    await web.store.set(wf.GUILD_ID, "chat_memory_consent", "optin")

    found = await roll_up(web, web.guild)

    assert str(CHATTY) not in {one["user_id"] for one in found["people"]}


async def test_the_roll_up_writes_nothing(client, sign_in, web, cog, wf):  # noqa: F811
    await seed(web, wf, client, sign_in)
    cur = await web.db.conn.execute("SELECT COUNT(*) AS n FROM action_log")
    before = (await cur.fetchone())["n"]

    await roll_up(web, web.guild)

    cur = await web.db.conn.execute("SELECT COUNT(*) AS n FROM action_log")
    assert (await cur.fetchone())["n"] == before
