# ruff: noqa: F401, F811
import ast
import pathlib

from black_bloc.bot import COGS
from black_bloc.cogs.content import points as cog_module
from black_bloc.cogs.content.points import Points
from black_bloc.command_visibility import HIDDEN_WHEN_OFF
from black_bloc.points_tickets import RemoveButton
from tests.cogs.moderation.test_modmail import FakeInteraction
from tests.test_points_tickets import ada, bot

SOURCE = pathlib.Path(cog_module.__file__)


async def test_pb_opens_the_leaderboard_for_the_presser_alone(bot, ada):
    interaction = FakeInteraction(bot, ada)

    await Points.pb.callback(Points(bot), interaction)

    shown = interaction.response.messages[0]
    assert shown["ephemeral"] is True and shown["embed"].title == "Leaderboard"


async def test_pb_refuses_a_dm_in_words(bot, ada):
    interaction = FakeInteraction(bot, ada, guild=False)

    await Points.pb.callback(Points(bot), interaction)

    assert "server" in interaction.sent and interaction.response.messages[0]["ephemeral"]


async def test_the_cog_owns_the_remove_button_that_outlives_a_restart(bot):
    await Points(bot).cog_load()

    assert RemoveButton in bot.dynamic


def test_pb_hides_with_the_point_system_and_is_open_to_members():
    assert "black_bloc.cogs.content.points" in COGS
    assert HIDDEN_WHEN_OFF["points_mode"] == ("pb",)
    assert Points.pb.name == "pb" and Points.pb.default_permissions is None
    assert len(Points.pb.description) <= 100


def test_the_cog_is_thin_and_reads_no_environment():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    plain = [node for node in ast.walk(tree) if isinstance(node, ast.Import)]

    assert len(SOURCE.read_text(encoding="utf-8").splitlines()) < 60
    assert "os" not in {alias.name for node in plain for alias in node.names}


async def test_a_board_setting_redraws_the_leaderboard_post(bot, monkeypatch):
    asked = []

    async def redraw(found_bot, found_guild):
        asked.append(found_guild)
        return True

    monkeypatch.setattr(cog_module, "redraw", redraw)
    bot.get_guild = lambda guild_id: bot.guild
    await Points(bot).cog_load()

    await bot.store.set(bot.guild.id, "points_top_n", 5)
    await bot.store.set(bot.guild.id, "points_board_line", "{place}. {name}")
    await bot.store.set(bot.guild.id, "points_ping_role_id", 77)

    assert asked == [bot.guild, bot.guild]
