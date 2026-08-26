"""Offline checks: the bot object builds and cogs load without a gateway connection."""

from black_bloc.bot import COGS, BlackBlocBot


async def test_bot_builds_and_cogs_load(settings):
    bot = BlackBlocBot(settings)
    assert bot.intents.members and bot.intents.message_content and bot.intents.presences
    for name in COGS:
        await bot.load_extension(name)
    names = {cmd.name for cmd in bot.tree.get_commands()}
    assert {"ping", "about"} <= names
    await bot.close()
