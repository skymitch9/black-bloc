from types import SimpleNamespace

import discord
import pytest

from black_bloc import rehearsal_copy

HOME = 333


class Guard:
    def __init__(self, allowed):
        self.allowed = allowed

    def allows_channel(self, channel_id):
        return int(channel_id) == self.allowed


class Message:
    def __init__(self, message_id):
        self.id = message_id
        self.edits = []

    async def edit(self, **kwargs):
        self.edits.append(kwargs)


class Channel:
    def __init__(self, channel_id, raises=None):
        self.id = channel_id
        self.sent = []
        self.raises = raises

    async def send(self, **kwargs):
        if self.raises is not None:
            raise self.raises
        self.sent.append(kwargs)
        return Message(900 + len(self.sent))


def bot_with(channels, guard=None):
    found = {channel.id: channel for channel in channels}
    return SimpleNamespace(get_channel=found.get, guard=guard)


def test_reach_finds_the_home_or_says_why_not():
    home = Channel(HOME)
    guild = SimpleNamespace(id=7, get_channel=lambda _id: None)

    assert rehearsal_copy.reach(bot_with([home]), guild, HOME) == (home, None)
    assert rehearsal_copy.reach(bot_with([]), guild, HOME) == (None, rehearsal_copy.CHANNEL_GONE)
    guarded = bot_with([home], guard=Guard(allowed=1))
    assert rehearsal_copy.reach(guarded, guild, HOME) == (None, rehearsal_copy.TEST_MODE)


async def test_deliver_sends_a_new_copy_or_edits_the_one_given():
    home = Channel(HOME)

    sent, edited = await rehearsal_copy.deliver(home, {"content": "one"})
    assert (sent.id, edited, home.sent) == (901, False, [{"content": "one"}])

    again, edited = await rehearsal_copy.deliver(home, {"content": "two"}, sent)
    assert (again, edited, sent.edits, len(home.sent)) == (sent, True, [{"content": "two"}], 1)


async def test_deliver_hands_discords_refusal_to_the_caller():
    response = SimpleNamespace(status=403, reason="Forbidden")
    home = Channel(HOME, raises=discord.Forbidden(response, "Missing Access"))

    with pytest.raises(discord.HTTPException):
        await rehearsal_copy.deliver(home, {"content": "one"})


def test_the_message_link_is_discords():
    url = rehearsal_copy.message_url(SimpleNamespace(id=7), Channel(HOME), Message(42))

    assert url == "https://discord.com/channels/7/333/42"
