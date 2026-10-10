# ruff: noqa: F401, F811
from black_bloc import points_board_panel as settings_panel
from black_bloc import points_post
from black_bloc.panels import Outcome
from tests.cogs.moderation.test_modmail import GUILD, FakeInteraction
from tests.test_points_panel import item, labels, opened_by, press
from tests.test_points_tickets import SPEED, ada, bot, lead


async def settings_of(bot, lead):
    view = (await opened_by(bot, lead)).response.messages[0]["view"]
    return await press(bot, lead, view, "Settings…")


async def test_only_staff_get_the_settings_door(bot, ada, lead):
    member = (await opened_by(bot, ada)).response.messages[0]["view"]
    staff = (await opened_by(bot, lead)).response.messages[0]["view"]

    assert "Settings…" not in labels(member)
    assert "Settings…" in labels(staff)


async def test_the_door_shows_the_top_the_order_the_channel_and_the_pin(bot, lead):
    shown = await settings_of(bot, lead)

    assert shown.embed.title == "Leaderboard settings"
    assert shown.embed.description.splitlines() == [
        "**Top** 10",
        "**Order** Leaderboard",
        "**Channel** #speed-and-pbs",
        "**Pinned** not yet",
    ]
    top = next(one for one in shown.view.children if isinstance(one, settings_panel.TopPick))
    assert [one.label for one in top.options] == ["Top 5", "Top 10", "Top 15", "Top 20", "Top 25"]
    assert [one.default for one in top.options] == [False, True, False, False, False]
    channel = next(
        one for one in shown.view.children if isinstance(one, settings_panel.ChannelPick)
    )
    assert [one.id for one in channel.default_values] == [SPEED]
    assert labels(shown.view)[-2:] == ["Pin the leaderboard here", "Back"]
    assert shown.view.render_again is not None


async def test_picking_a_top_writes_the_key_once_and_redraws_the_door(bot, lead, db):
    shown = await settings_of(bot, lead)
    top = next(one for one in shown.view.children if isinstance(one, settings_panel.TopPick))
    top._values = ["5"]
    again = FakeInteraction(bot, lead)

    await top.callback(again)

    assert bot.store.get(GUILD, "points_top_n") == 5
    assert again.embed.description.splitlines()[0] == "**Top** 5"
    cur = await db.conn.execute("SELECT kind FROM action_log WHERE kind = 'settings.set'")
    assert len(await cur.fetchall()) == 1


async def test_pin_runs_the_shared_move_and_says_what_it_did(bot, lead, monkeypatch):
    asked = []

    async def pin_board(found_bot, guild, actor, *, replace=False, via="discord"):
        asked.append(replace)
        return Outcome(True, "The leaderboard is the sticky message in <#1> now.")

    monkeypatch.setattr(points_post, "pin_board", pin_board)
    shown = await settings_of(bot, lead)

    pressed = await press(bot, lead, shown.view, "Pin the leaderboard here")

    assert asked == [False]
    assert pressed.sent == "The leaderboard is the sticky message in <#1> now."


async def test_a_member_who_reaches_the_door_is_refused(bot, ada, lead):
    shown = await settings_of(bot, lead)

    refused = await press(bot, ada, shown.view, "Pin the leaderboard here")

    assert refused.edits == [] and refused.sent


def test_the_moves_offered_follow_the_sticky():
    none = {"channel_id": 5, "sticky": None, "other": None}
    other = {"channel_id": 5, "sticky": None, "other": {"text": "x"}}
    running = {
        "channel_id": 5,
        "sticky": {"channel_id": 5, "paused": 0, "trouble": None},
        "other": None,
    }
    paused = {
        "channel_id": 5,
        "sticky": {"channel_id": 9, "paused": 1, "trouble": None},
        "other": None,
    }

    assert [one[0] for one in settings_panel.moves_of(none)] == ["pin"]
    assert [one[0] for one in settings_panel.moves_of(other)] == ["replace"]
    assert [one[0] for one in settings_panel.moves_of(running)] == ["pause"]
    assert [one[0] for one in settings_panel.moves_of(paused)] == ["pin", "resume"]
