from discord import app_commands

from black_bloc.command_errors import COMMAND_FAILED, install, on_tree_error


class _Response:
    def __init__(self, done=False):
        self.done = done
        self.messages = []

    def is_done(self):
        return self.done

    async def send_message(self, content=None, ephemeral=False, **kwargs):
        self.messages.append({"content": content, "ephemeral": ephemeral})


class _Followup:
    def __init__(self):
        self.messages = []

    async def send(self, content=None, ephemeral=False, **kwargs):
        self.messages.append({"content": content, "ephemeral": ephemeral})


class _Interaction:
    def __init__(self, done=False):
        self.command = None
        self.response = _Response(done)
        self.followup = _Followup()


class _Tree:
    pass


class _Bot:
    def __init__(self):
        self.tree = _Tree()


async def test_an_unhandled_error_answers_the_caller_with_a_sentence(caplog):
    interaction = _Interaction()

    with caplog.at_level("ERROR"):
        await on_tree_error(interaction, RuntimeError("boom"))

    assert interaction.response.messages == [{"content": COMMAND_FAILED, "ephemeral": True}]
    assert "boom" in caplog.text


async def test_an_answered_interaction_gets_a_followup():
    interaction = _Interaction(done=True)

    await on_tree_error(interaction, RuntimeError("boom"))

    assert interaction.response.messages == []
    assert interaction.followup.messages[0]["content"] == COMMAND_FAILED


async def test_a_check_failure_is_left_to_the_check_that_already_answered():
    interaction = _Interaction()

    await on_tree_error(interaction, app_commands.CheckFailure("no"))

    assert interaction.response.messages == []
    assert interaction.followup.messages == []


async def test_a_broken_answer_never_raises_out_of_the_handler(caplog):
    interaction = _Interaction()

    async def explode(*args, **kwargs):
        raise RuntimeError("discord is down")

    interaction.response.send_message = explode

    with caplog.at_level("WARNING"):
        await on_tree_error(interaction, RuntimeError("boom"))

    assert "could not answer the caller" in caplog.text


def test_install_puts_the_handler_on_the_tree():
    bot = _Bot()
    install(bot)
    assert bot.tree.on_error is on_tree_error


def test_install_is_a_no_op_without_a_tree():
    install(object())
