import discord

from black_bloc.spawned import STAFF_REACH_KEY, reach_roles, staff_reach


class FakeRole:
    def __init__(self, role_id):
        self.id = role_id
        self.name = f"role-{role_id}"


class FakeGuild:
    def __init__(self, guild_id=7):
        self.id = guild_id


class FakeStore:
    def __init__(self, on=True, roles=()):
        self.on = on
        self.roles = list(roles)

    def get(self, guild_id, key):
        assert key == STAFF_REACH_KEY
        return self.on

    def staff_roles(self, guild):
        return self.roles


class FakeBot:
    def __init__(self, store=None):
        if store is not None:
            self.store = store


def test_the_staff_roles_get_view_and_manage_on_a_text_channel():
    role = FakeRole(1)
    given = staff_reach({}, [role], voice=False)

    assert given[role].view_channel is True
    assert given[role].manage_channels is True
    assert given[role].connect is None


def test_a_voice_channel_also_gets_connect():
    role = FakeRole(1)
    given = staff_reach({}, [role], voice=True)

    assert given[role].connect is True


def test_the_allow_is_added_on_top_of_what_the_builder_already_said():
    role = FakeRole(1)
    everyone = FakeRole(0)
    overwrites = {
        everyone: discord.PermissionOverwrite(view_channel=False),
        role: discord.PermissionOverwrite(send_messages=True, view_channel=False),
    }

    given = staff_reach(overwrites, [role], voice=False)

    assert given[everyone].view_channel is False
    assert given[role].send_messages is True
    assert given[role].view_channel is True


def test_no_roles_and_none_entries_leave_the_overwrites_alone():
    everyone = FakeRole(0)
    overwrites = {everyone: discord.PermissionOverwrite(view_channel=False)}

    assert staff_reach(dict(overwrites), (), voice=True) == overwrites
    assert staff_reach(dict(overwrites), None, voice=True) == overwrites
    assert staff_reach(dict(overwrites), [None], voice=True) == overwrites


def test_the_key_decides_whether_there_are_any_roles_to_allow():
    role = FakeRole(1)
    guild = FakeGuild()

    assert reach_roles(FakeBot(FakeStore(on=True, roles=[role])), guild) == [role]
    assert reach_roles(FakeBot(FakeStore(on=False, roles=[role])), guild) == []


def test_roles_already_resolved_are_used_rather_than_looked_up_again():
    role = FakeRole(1)
    other = FakeRole(2)
    guild = FakeGuild()

    assert reach_roles(FakeBot(FakeStore(on=True, roles=[role])), guild, [other]) == [other]
    assert reach_roles(FakeBot(FakeStore(on=False, roles=[role])), guild, [other]) == []


def test_a_bot_with_no_store_and_a_missing_guild_ask_for_nothing():
    assert reach_roles(FakeBot(), FakeGuild()) == []
    assert reach_roles(FakeBot(FakeStore()), None) == []
