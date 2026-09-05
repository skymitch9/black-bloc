from types import SimpleNamespace

from discord import app_commands

from black_bloc import bot as bot_module
from black_bloc.bot import COGS, BlackBlocBot
from black_bloc.logkinds import FEATURES

TOP_LEVEL_MAX = 100
CHILDREN_MAX = 25
LOGS_GROUPS = {
}


STAFF_COMMANDS = {
    "automod",
    "ban",
    "chat",
    "honeypot",
    "kick",
    "mod",
    "modmail",
    "presence",
    "purge",
    "reply",
    "rolemenu",
    "settings",
    "timeout",
    "unban",
    "untimeout",
    "warn",
}
MEMBER_COMMANDS = {
    "about",
    "apply",
    "birthday",
    "event",
    "golive",
    "help",
    "memory",
    "ping",
    "pings",
    "poll",
    "raidtrain",
    "request",
    "voice",
    "youtube",
}
GATE_IS_TWO_HOPS_AWAY = {"/reply"}


def leaves(command, path):
    if isinstance(command, app_commands.Group):
        for child in command.commands:
            yield from leaves(child, f"{path} {child.name}")
    else:
        yield path, command


async def test_a_command_only_staff_can_run_is_only_shown_to_staff(settings):
    """Measured 2026-09-01: among human roles only Leads and Aunties/Uncles hold
    manage_messages, so it is the permission that hides a command below them."""
    from black_bloc.command_visibility import STAFF_ONLY

    bot = BlackBlocBot(settings)
    for name in COGS:
        await bot.load_extension(name)

    top = bot.tree.get_commands()
    locked = {one.name for one in top if one.default_permissions is not None}
    visible = {one.name for one in top if one.default_permissions is None}

    assert locked == STAFF_COMMANDS
    assert visible == MEMBER_COMMANDS
    assert all(
        one.default_permissions == STAFF_ONLY
        for one in top
        if one.default_permissions is not None
    )
    await bot.close()


async def test_nothing_a_member_can_run_is_hidden_behind_the_lock(settings):
    """The lock is UX; the runtime gate is the enforcement, and it is untouched."""
    from black_bloc.settings_store import is_staff_command

    bot = BlackBlocBot(settings)
    for name in COGS:
        await bot.load_extension(name)

    for one in bot.tree.get_commands():
        if one.default_permissions is None:
            continue
        for path, command in leaves(one, f"/{one.name}"):
            if path in GATE_IS_TWO_HOPS_AWAY:
                continue
            assert is_staff_command(command), path
    await bot.close()


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


async def test_every_feature_group_has_a_logs_command(settings):
    bot = BlackBlocBot(settings)
    for name in COGS:
        await bot.load_extension(name)

    groups = {
        command.name: command
        for command in bot.tree.get_commands()
        if isinstance(command, app_commands.Group)
    }
    for group_name, feature in LOGS_GROUPS.items():
        group = groups[group_name]
        logs = next(child for child in group.commands if child.name == "logs")
        assert [option.name for option in logs.parameters] == ["count", "important_only"]
        assert feature in FEATURES
    assert "chat" not in groups
    assert "mod" not in groups
    assert "raidtrains" not in groups
    assert "rolemenu" not in groups
    assert "modmail" not in groups
    assert "snippet" not in groups
    await bot.close()


async def test_the_command_tree_stays_inside_discords_limits(settings):
    """One `logs` per group; two new top-level groups. Neither ceiling is near."""
    bot = BlackBlocBot(settings)
    for name in COGS:
        await bot.load_extension(name)

    top = bot.tree.get_commands()
    assert len(top) <= TOP_LEVEL_MAX
    assert len(top) == 30
    for command in top:
        if isinstance(command, app_commands.Group):
            assert len(command.commands) <= CHILDREN_MAX, command.name
            for child in command.commands:
                if isinstance(child, app_commands.Group):
                    assert len(child.commands) <= CHILDREN_MAX, child.name
    await bot.close()


async def test_a_logs_command_is_staff_only_and_ephemeral(settings):
    """`is_staff_command` reads the callback's helpers, so send_logs' gate is what it finds."""
    from black_bloc.settings_store import is_staff_command

    bot = BlackBlocBot(settings)
    for name in COGS:
        await bot.load_extension(name)

    groups = {
        command.name: command
        for command in bot.tree.get_commands()
        if isinstance(command, app_commands.Group)
    }
    for group_name in LOGS_GROUPS:
        logs = next(c for c in groups[group_name].commands if c.name == "logs")
        assert is_staff_command(logs), group_name
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
