from types import SimpleNamespace

from black_bloc.prefix import no_prefix_commands


def test_no_message_carries_a_prefix():
    message = SimpleNamespace(content="<@1> hi")
    assert no_prefix_commands(None, message) == []


def test_an_empty_prefix_list_matches_nothing_discord_py_would_look_for():
    """`get_context` returns early on `content.startswith(tuple(prefix))`, which is False."""
    assert "<@1> hi".startswith(tuple(no_prefix_commands(None, None))) is False
