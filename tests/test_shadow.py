from types import SimpleNamespace

import discord

from black_bloc import posts, shadow

GUILD = 7
GUARD_CHANNEL = 111
SETTINGS_CHANNEL = 222
LOG_CHANNEL = 333
HOME = 444


class FakeStore:
    def __init__(self, **values):
        self.values = values
        self.hooks = {}

    def get(self, guild_id, key):
        assert guild_id == GUILD
        return self.values.get(key)

    def stored_values(self, key):
        found = self.values.get(key)
        return {GUILD: found} if found else {}

    def on_change(self, key, callback):
        self.hooks.setdefault(key, []).append(callback)


def bot_with(*, guard=None, settings_channel=None, log=LOG_CHANNEL, home=None):
    return SimpleNamespace(
        guard=SimpleNamespace(test_channel_id=guard) if guard is not None else None,
        settings=SimpleNamespace(test_channel_id=settings_channel),
        store=FakeStore(log_channel_id=log, shadow_channel_id=home),
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


class FakeMessage:
    def __init__(self, message_id):
        self.id = message_id


class FakeChannel:
    def __init__(self, channel_id, *holds, raises=None):
        self.id = channel_id
        self.holds = {int(one) for one in holds}
        self.raises = raises

    async def fetch_message(self, message_id):
        if self.raises is not None:
            raise self.raises
        if int(message_id) not in self.holds:
            raise discord.NotFound(SimpleNamespace(status=404, reason="gone"), "gone")
        return FakeMessage(int(message_id))


def cache(bot, *channels):
    known = {one.id: one for one in channels}
    bot.get_channel = lambda channel_id: known.get(int(channel_id))
    return SimpleNamespace(id=GUILD, get_channel=lambda channel_id: known.get(int(channel_id)))


class FakeGuard:
    def __init__(self, test_channel_id=GUARD_CHANNEL):
        self.test_channel_id = test_channel_id
        self.homes = {}

    def rehearse_in(self, guild_id, channel):
        if channel is None:
            self.homes.pop(int(guild_id), None)
            return
        self.homes[int(guild_id)] = int(channel)


def test_the_rehearsal_home_is_asked_first_and_blank_is_exactly_as_it_was():
    assert shadow.channel_id(bot_with(guard=GUARD_CHANNEL, home=HOME), GUILD) == HOME
    assert shadow.channel_id(bot_with(guard=GUARD_CHANNEL), GUILD) == GUARD_CHANNEL


def test_the_home_wins_over_the_log_channel_with_no_guard_at_all():
    assert shadow.channel_id(bot_with(home=HOME), GUILD) == HOME


def test_home_id_is_the_key_and_nothing_else():
    assert shadow.home_id(bot_with(guard=GUARD_CHANNEL), GUILD) is None
    assert shadow.home_id(bot_with(guard=GUARD_CHANNEL, home=HOME), GUILD) == HOME


def test_the_hunt_starts_at_the_home_because_the_key_may_have_moved():
    bot = bot_with(guard=GUARD_CHANNEL, settings_channel=SETTINGS_CHANNEL, home=HOME)

    assert shadow.channel_ids(bot, GUILD) == [HOME, GUARD_CHANNEL, SETTINGS_CHANNEL, LOG_CHANNEL]


async def test_a_copy_left_behind_in_the_old_home_is_still_found():
    bot = bot_with(guard=GUARD_CHANNEL, home=HOME)
    old = FakeChannel(GUARD_CHANNEL, 900)
    guild = cache(bot, FakeChannel(HOME), old, FakeChannel(LOG_CHANNEL))

    channel, message = await shadow.find_copy(bot, guild, 900)

    assert channel is old and message.id == 900


async def test_a_copy_nobody_has_is_no_channel_and_no_message():
    bot = bot_with(guard=GUARD_CHANNEL, home=HOME)
    guild = cache(bot, FakeChannel(HOME), FakeChannel(GUARD_CHANNEL), FakeChannel(LOG_CHANNEL))

    assert await shadow.find_copy(bot, guild, 900) == (None, None)
    assert await shadow.find_copy(bot, guild, None) == (None, None)


async def test_a_channel_discord_will_not_answer_about_never_stops_the_hunt():
    bot = bot_with(guard=GUARD_CHANNEL, home=HOME)
    sulking = FakeChannel(
        HOME, raises=discord.HTTPException(SimpleNamespace(status=500, reason="no"), "no")
    )
    guild = cache(bot, sulking, FakeChannel(GUARD_CHANNEL, 900))

    channel, message = await shadow.find_copy(bot, guild, 900)

    assert channel is not None and message.id == 900


def test_the_note_names_the_channel_the_real_one_is_aimed_at():
    bot = bot_with(guard=GUARD_CHANNEL, home=HOME)
    bot.store.values[shadow.NOTE_KEY] = shadow.NOTE_DEFAULT

    assert shadow.note_line(bot, GUILD, "<#5>") == "Rehearsal — this is where it would go: <#5>"


def test_a_blank_note_is_no_line_at_all():
    bot = bot_with(guard=GUARD_CHANNEL, home=HOME)
    bot.store.values[shadow.NOTE_KEY] = "   "

    assert shadow.note_line(bot, GUILD, "<#5>") == ""


def test_a_note_whose_braces_are_nonsense_is_used_as_written():
    bot = bot_with(guard=GUARD_CHANNEL, home=HOME)
    bot.store.values[shadow.NOTE_KEY] = "look at {oops}"

    assert shadow.note_line(bot, GUILD, "<#5>") == "look at {oops}"


async def test_the_guard_is_seeded_from_what_is_stored_and_then_follows_the_key():
    bot = bot_with(guard=GUARD_CHANNEL, home=HOME)
    bot.guard = FakeGuard()

    shadow.install(bot)
    assert bot.guard.homes == {GUILD: HOME}

    hook = bot.store.hooks[shadow.REHEARSAL_KEY][0]
    await hook(GUILD, shadow.REHEARSAL_KEY, 555, None)
    assert bot.guard.homes == {GUILD: 555}

    await hook(GUILD, shadow.REHEARSAL_KEY, None, None)
    assert bot.guard.homes == {}


def test_with_no_guard_installed_nothing_is_taught_and_no_hook_is_registered():
    bot = bot_with(home=HOME)

    shadow.install(bot)

    assert bot.store.hooks == {}
