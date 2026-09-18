from types import SimpleNamespace

from discord import app_commands

from black_bloc import bot as bot_module
from black_bloc.bot import COGS, BlackBlocBot
from black_bloc.logkinds import FEATURES

TOP_LEVEL_MAX = 100
CHILDREN_MAX = 25
TOP_LEVEL_NOW = 32
RETIRED_GROUPS = (
    "chat",
    "mod",
    "modmail",
    "presence",
    "raidtrains",
    "rolemenu",
    "settings",
    "snippet",
)


STAFF_COMMANDS = {
    "automod",
    "ban",
    "chat",
    "honeypot",
    "kick",
    "minutes",
    "mod",
    "posts",
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
    "ask",
    "birthday",
    "event",
    "golive",
    "help",
    "memory",
    "modmail",
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


async def test_every_features_logs_is_a_panel_button_and_no_group_is_left_to_hold_one(settings):
    """The guarantee this once made — every feature group carries a `logs` child — could not
    survive the panels program, which retired every group. It is re-expressed against what
    replaced it: no group is left at all, every feature in `FEATURES` has a panel whose Logs
    button calls `send_logs` with that feature's name, and nothing reaches `send_logs` from a
    slash command any more. The feature set is checked for EQUALITY, so a Logs button deleted
    by the next wave fails here, and so does a `send_logs("typo")` nobody can reach."""
    import ast
    import pathlib

    import black_bloc

    bot = BlackBlocBot(settings)
    for name in COGS:
        await bot.load_extension(name)
    groups = [
        command.name
        for command in bot.tree.get_commands()
        if isinstance(command, app_commands.Group)
    ]
    await bot.close()

    def strings(tree):
        found = {}
        for node in tree.body:
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant):
                for target in node.targets:
                    if isinstance(target, ast.Name) and isinstance(node.value.value, str):
                        found[target.id] = node.value.value
        return found

    def holders(tree):
        """Each node's nearest enclosing function, so a call's decorators can be read."""
        found = {}

        def walk(node, holder):
            for child in ast.iter_child_nodes(node):
                mine = child if isinstance(child, FUNCTIONS) else holder
                if holder is not None:
                    found[child] = holder
                walk(child, mine)

        walk(tree, None)
        return found

    FUNCTIONS = (ast.FunctionDef, ast.AsyncFunctionDef)
    root = pathlib.Path(black_bloc.__file__).resolve().parent
    shared = strings(ast.parse((root / "logkinds.py").read_text(encoding="utf-8")))
    logged = set()
    from_a_command = []
    labels = 0
    for path in root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        labels += text.count('"Logs"') + text.count("'Logs'")
        tree = ast.parse(text)
        known = {**shared, **strings(tree)}
        holder = holders(tree)
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and getattr(node.func, "id", "") == "send_logs"):
                continue
            feature = node.args[1] if len(node.args) > 1 else None
            if isinstance(feature, ast.Constant):
                logged.add(feature.value)
            elif isinstance(feature, ast.Name):
                logged.add(known.get(feature.id, feature.id))
            owner = holder.get(node)
            decorators = getattr(owner, "decorator_list", []) if owner is not None else []
            if any("app_commands" in ast.unparse(one) for one in decorators):
                from_a_command.append(f"{path.name}::{getattr(owner, 'name', '?')}")

    from black_bloc.logkinds import FEATURES_WITHOUT_A_COMMAND

    assert groups == []
    assert not [name for name in RETIRED_GROUPS if name in groups]
    # F-G1: guides are edited on the website only, so the one feature with no Discord door
    # has no panel and therefore no Logs button to find.
    assert logged == set(FEATURES) - set(FEATURES_WITHOUT_A_COMMAND)
    assert not from_a_command, (
        "Logs is a panel button now, not a subcommand — these reach send_logs from a slash "
        f"command callback: {sorted(from_a_command)}"
    )
    wanted = len(FEATURES) - len(FEATURES_WITHOUT_A_COMMAND)
    assert labels >= wanted, f"only {labels} controls are labelled Logs for {wanted} features"


async def test_the_command_tree_stays_inside_discords_limits(settings):
    """30 top-level slots and ZERO groups — the panels program's finish line, measured."""
    bot = BlackBlocBot(settings)
    for name in COGS:
        await bot.load_extension(name)

    top = bot.tree.get_commands()
    assert len(top) <= TOP_LEVEL_MAX
    assert len(top) == TOP_LEVEL_NOW
    assert [one.name for one in top if isinstance(one, app_commands.Group)] == []
    await bot.close()


async def test_every_log_level_names_a_command_that_still_exists(settings):
    """`LOG_LEVEL_COMMANDS` writes the help text a person reads on the Settings page and on
    `/settings` — "`/<command>` ▸ **Logs**". It went stale eight times over the panels program,
    each wave renaming a command under it, and nothing failed. This is what fails now."""
    from black_bloc.logkinds import FEATURES, FEATURES_WITHOUT_A_COMMAND
    from black_bloc.settings_store import LOG_LEVEL_COMMANDS, log_level_help

    bot = BlackBlocBot(settings)
    for name in COGS:
        await bot.load_extension(name)
    names = {one.name for one in bot.tree.get_commands()}
    await bot.close()

    assert set(LOG_LEVEL_COMMANDS) == set(FEATURES) - set(FEATURES_WITHOUT_A_COMMAND)
    gone = sorted(
        f"{feature} -> /{command}"
        for feature, command in LOG_LEVEL_COMMANDS.items()
        if command not in names
    )
    assert not gone, f"these log levels name a command that no longer exists: {gone}"
    for feature in FEATURES:
        said = log_level_help(feature)
        if feature in FEATURES_WITHOUT_A_COMMAND:
            assert "▸ **Logs**" not in said, feature
            continue
        assert f"`/{LOG_LEVEL_COMMANDS[feature]}` ▸ **Logs**" in said, feature
        assert "logs`" not in said, feature


async def test_a_features_logs_is_staff_only_wherever_the_panel_button_reaches_it(settings):
    """`send_logs` is the whole body every Logs button calls, and it gates itself."""
    from black_bloc.actionlog import send_logs
    from black_bloc.settings_store import called_names, require_staff

    assert require_staff.__name__ in called_names(send_logs)


async def test_on_ready_reconciles_the_role_menu_panels_and_runs_the_self_test(monkeypatch):
    """A restart mid-flip converges, and the deploy proves itself — the two things
    `on_ready` does beyond logging, in that order."""
    seen = []

    async def fake_panels(bot):
        seen.append(("panels", bot))

    async def fake_selftest(bot):
        seen.append(("selftest", bot))

    monkeypatch.setattr(bot_module, "panels_on_boot", fake_panels)
    monkeypatch.setattr(bot_module, "selftest_on_boot", fake_selftest)
    stand_in = SimpleNamespace(user=SimpleNamespace(id=1), guilds=[])

    await BlackBlocBot.on_ready(stand_in)

    assert seen == [("panels", stand_in), ("selftest", stand_in)]
