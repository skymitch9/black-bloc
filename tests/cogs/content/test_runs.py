import discord
import pytest

from black_bloc.cogs.content import runs as runs_cog
from black_bloc.command_visibility import STAFF_ONLY
from tests.baf_runs_fakes import FakeMember, make_bot


class FakeResponse:
    def __init__(self):
        self.done = False
        self.messages = []

    def is_done(self):
        return self.done

    async def send_message(self, content=None, **kwargs):
        self.done = True
        self.messages.append({"content": content, **kwargs})


class FakeInteraction:
    def __init__(self, client, user, guild=True):
        self.client = client
        self.user = user
        self.guild = client.guild if guild else None
        self.response = FakeResponse()

    async def original_response(self):
        return object()


@pytest.fixture
async def bot(db, monkeypatch):
    return await make_bot(db, monkeypatch)


def member(bot, user_id, *, staff):
    found = FakeMember(user_id, f"m{user_id}")
    found.guild = bot.guild
    found.guild_permissions = (
        discord.Permissions(manage_guild=True) if staff else discord.Permissions.none()
    )
    return found


async def test_runs_opens_one_ephemeral_panel_for_staff(bot):
    asked = FakeInteraction(bot, member(bot, 42, staff=True))

    await runs_cog.open_panel(asked)

    sent = asked.response.messages[0]
    assert sent["ephemeral"] is True and sent["embed"].title == "BaF runs"
    assert sent["allowed_mentions"].everyone is False
    assert [item.label for item in sent["view"].children][0] == "Search…"


async def test_runs_refuses_a_member_who_is_not_staff_and_a_dm(bot):
    stranger = FakeInteraction(bot, member(bot, 99, staff=False))
    direct = FakeInteraction(bot, member(bot, 42, staff=True), guild=False)

    await runs_cog.open_panel(stranger)
    await runs_cog.open_panel(direct)

    assert "staff only" in stranger.response.messages[0]["content"]
    assert "server" in direct.response.messages[0]["content"]


def test_runs_is_hidden_from_members_like_the_marathon_controls():
    command = runs_cog.Runs.runs

    assert command.name == "runs"
    assert command.default_permissions == STAFF_ONLY
