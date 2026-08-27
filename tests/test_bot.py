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


async def test_an_at_mention_is_never_read_as_a_prefix_command(settings, caplog):
    """`@Black Bloc hi` used to reach the log as CommandNotFound: Command "hi" is not found."""
    bot = BlackBlocBot(settings)
    bot._connection.user = SimpleNamespace(id=1)
    dispatched = []
    bot.dispatch = lambda name, *args, **kwargs: dispatched.append(name)
    message = SimpleNamespace(
        author=SimpleNamespace(id=2, bot=False),
        content="<@1> hi",
        _state=bot._connection,
    )

    caplog.clear()
    with caplog.at_level("WARNING"):
        await bot.process_commands(message)

    assert dispatched == []
    assert caplog.records == []
    await bot.close()


async def test_the_bot_has_no_prefix_commands_to_dispatch(settings):
    bot = BlackBlocBot(settings)
    for name in COGS:
        await bot.load_extension(name)
    assert bot.commands == set()
    assert await bot.get_prefix(SimpleNamespace(content="anything")) == []
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
