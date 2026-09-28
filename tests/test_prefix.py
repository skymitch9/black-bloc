from types import SimpleNamespace

from black_bloc.prefix import no_prefix_commands


def test_no_message_carries_a_prefix():
    message = SimpleNamespace(content="<@1> hi")
    assert no_prefix_commands(None, message) == []

