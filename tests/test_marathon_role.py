from types import SimpleNamespace

import discord
import pytest

from black_bloc import marathon_role as mr
from black_bloc.settings_store import (
    BUTTON_BLOCK_DEFAULTS,
    MARATHON_BLOCK_LABEL,
    MARATHON_BLOCK_TITLE,
)

GUILD = 7


class Store:
    def __init__(self, **values):
        self.values = values

    def get(self, guild_id, key):
        return self.values.get(key)


def a_role(role_id=55, name="Marathon", **perms):
    return SimpleNamespace(
        id=role_id,
        name=name,
        managed=False,
        is_default=lambda: False,
        permissions=discord.Permissions(**perms),
    )


def a_guild(*roles):
    found = {role.id: role for role in roles}
    return SimpleNamespace(id=GUILD, get_role=lambda role_id: found.get(int(role_id)))


def test_no_role_is_picked_by_default():
    assert BUTTON_BLOCK_DEFAULTS["marathon_role_id"] is None
    assert mr.usable_role(Store(), a_guild(a_role())) == (None, mr.UNSET)


def test_a_picked_plain_role_is_usable():
    role = a_role(send_messages=True, view_channel=True)

    assert mr.usable_role(Store(marathon_role_id="55"), a_guild(role)) == (role, "")


def test_a_role_gone_from_the_server_is_not_usable():
    assert mr.usable_role(Store(marathon_role_id=99), a_guild(a_role())) == (None, mr.GONE)


@pytest.mark.parametrize(
    "perm",
    ["administrator", "ban_members", "manage_roles", "mention_everyone", "moderate_members"],
)
def test_a_role_with_any_staff_permission_is_never_handed_out(perm):
    role = a_role(**{perm: True})
    assert mr.usable_role(Store(marathon_role_id=55), a_guild(role)) == (None, mr.UNSAFE)


def test_a_managed_role_and_everyone_are_never_handed_out():
    managed = a_role()
    managed.managed = True
    everyone = a_role()
    everyone.is_default = lambda: True

    assert mr.unsafe(managed) and mr.unsafe(everyone)


def test_the_block_is_drawn_even_with_no_role_so_the_press_can_say_why():
    assert mr.block_drawn(Store(), GUILD) is True


def test_the_block_says_its_shipped_words_and_a_toggle_label():
    look = mr.block_look(Store(), GUILD)

    assert look.title == BUTTON_BLOCK_DEFAULTS[MARATHON_BLOCK_TITLE]
    assert look.label == BUTTON_BLOCK_DEFAULTS[MARATHON_BLOCK_LABEL]
    assert look.label != look.title


def test_each_answer_names_the_role_and_staff_can_reword_it():
    role = a_role(name="Marathoners")

    assert "**Marathoners**" in mr.added_said(Store(), GUILD, role)
    assert "**Marathoners**" in mr.removed_said(Store(), GUILD, role)
    assert mr.added_said(Store(marathon_block_added_said="Got {role}"), GUILD, role) == (
        "Got Marathoners"
    )
    assert "not set up" in mr.unset_said(Store(), GUILD)


def test_the_custom_id_never_collides_with_the_marathon_cog_s_other_buttons():
    assert mr.BLOCK_HEAD == "marathonrole:toggle"
    assert not mr.BLOCK_HEAD.startswith("marathon:")
