from types import SimpleNamespace

from black_bloc import posts, shadow

GUILD = 7
GUARD_CHANNEL = 111
SETTINGS_CHANNEL = 222
LOG_CHANNEL = 333


class FakeStore:
    def __init__(self, **values):
        self.values = values

    def get(self, guild_id, key):
        assert guild_id == GUILD
        return self.values.get(key)


def bot_with(*, guard=None, settings_channel=None, log=LOG_CHANNEL):
    return SimpleNamespace(
        guard=SimpleNamespace(test_channel_id=guard) if guard is not None else None,
        settings=SimpleNamespace(test_channel_id=settings_channel),
        store=FakeStore(log_channel_id=log),
    )


def test_a_rehearsal_goes_to_the_guards_channel_while_the_guard_is_installed():
    bot = bot_with(guard=GUARD_CHANNEL)

    assert shadow.channel_id(bot, SimpleNamespace(id=GUILD)) == GUARD_CHANNEL


def test_with_no_guard_a_rehearsal_goes_to_the_log_channel():
    assert shadow.channel_id(bot_with(), SimpleNamespace(id=GUILD)) == LOG_CHANNEL


def test_a_guard_with_no_channel_falls_through_to_the_log_channel():
    assert shadow.channel_id(bot_with(guard=0), SimpleNamespace(id=GUILD)) == LOG_CHANNEL


def test_a_guild_id_is_taken_as_readily_as_a_guild():
    bot = bot_with()

    assert shadow.channel_id(bot, GUILD) == shadow.channel_id(bot, SimpleNamespace(id=GUILD))


def test_nothing_configured_anywhere_is_None_rather_than_a_guess():
    assert shadow.channel_id(bot_with(log=None), SimpleNamespace(id=GUILD)) is None


def test_the_hunt_covers_every_channel_a_copy_could_already_be_in():
    bot = bot_with(guard=GUARD_CHANNEL, settings_channel=SETTINGS_CHANNEL)

    assert shadow.channel_ids(bot, GUILD) == [GUARD_CHANNEL, SETTINGS_CHANNEL, LOG_CHANNEL]


def test_the_hunt_never_names_one_channel_twice():
    bot = bot_with(guard=LOG_CHANNEL, settings_channel=LOG_CHANNEL)

    assert shadow.channel_ids(bot, GUILD) == [LOG_CHANNEL]


def test_a_channel_id_that_is_not_a_number_is_no_channel_at_all():
    assert shadow.as_channel_id("nonsense") is None
    assert shadow.as_channel_id(None) is None
    assert shadow.as_channel_id("42") == 42


def test_posts_and_this_module_answer_the_same_question_the_same_way():
    """One fact, one home (checklist 15): `posts.shadow_channel_id` is still its own copy
    until the next build folds it, so this is the guard that stops the two drifting."""
    for guard, log in ((GUARD_CHANNEL, LOG_CHANNEL), (None, LOG_CHANNEL), (None, None)):
        bot = bot_with(guard=guard, log=log)
        guild = SimpleNamespace(id=GUILD)
        assert posts.shadow_channel_id(bot, guild) == shadow.channel_id(bot, guild)
        assert posts.shadow_channel_ids(bot, guild) == shadow.channel_ids(bot, guild)
