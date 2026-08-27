from types import SimpleNamespace

from black_bloc import bot as bot_module
from black_bloc.bot import COGS, BlackBlocBot


async def test_bot_builds_and_cogs_load(settings):
    bot = BlackBlocBot(settings)
    assert bot.intents.members and bot.intents.message_content and bot.intents.presences
    for name in COGS:
        await bot.load_extension(name)
    names = {cmd.name for cmd in bot.tree.get_commands()}
    assert {"ping", "about"} <= names
    await bot.close()


async def test_on_ready_reconciles_the_role_menu_panels(monkeypatch):
    """A restart mid-flip converges — the one thing `on_ready` does beyond logging."""
    seen = []

    async def fake_boot(bot):
        seen.append(bot)

    monkeypatch.setattr(bot_module, "panels_on_boot", fake_boot)
    stand_in = SimpleNamespace(user=SimpleNamespace(id=1), guilds=[])

    await BlackBlocBot.on_ready(stand_in)

    assert seen == [stand_in]
