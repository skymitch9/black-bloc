import json
from types import SimpleNamespace

import discord
import pytest

from black_bloc.structure import counts
from black_bloc.structure_capture import NO_ROLES, CaptureError, capture, channel_row, role_row

GUILD = 7
LEADS = 11
MEMBER = 900


class Target(SimpleNamespace):
    __hash__ = object.__hash__


def role(role_id, name, permissions=0, position=0, **extra):
    return Target(
        id=role_id,
        name=name,
        color=discord.Colour(extra.pop("color", 0)),
        permissions=discord.Permissions(permissions),
        position=position,
        hoist=extra.pop("hoist", False),
        mentionable=extra.pop("mentionable", False),
        managed=extra.pop("managed", False),
        members=[SimpleNamespace(id=MEMBER, name="sam")],
    )


def channel(channel_id, name, kind=discord.ChannelType.text, **extra):
    return SimpleNamespace(
        id=channel_id,
        name=name,
        type=kind,
        category_id=extra.pop("category_id", None),
        position=extra.pop("position", 0),
        overwrites=extra.pop("overwrites", {}),
        members=[SimpleNamespace(id=MEMBER, name="sam")],
        last_message=SimpleNamespace(content="a secret said in chat"),
        **extra,
    )


def guild():
    return SimpleNamespace(
        id=GUILD,
        name="Black Bloc",
        verification_level=discord.VerificationLevel.medium,
        default_notifications=discord.NotificationLevel.only_mentions,
        system_channel=SimpleNamespace(id=41),
        rules_channel=None,
        members=[SimpleNamespace(id=MEMBER, name="sam", roles=[LEADS])],
        owner_id=MEMBER,
    )


def everything():
    everyone = role(GUILD, "@everyone", 1024)
    leads = role(LEADS, "Leads", 8, 2, color=0x4EEFFF, hoist=True)
    overwrites = {
        everyone: discord.PermissionOverwrite(view_channel=False),
        leads: discord.PermissionOverwrite(view_channel=True, manage_messages=True),
        Target(id=MEMBER): discord.PermissionOverwrite(send_messages=False),
    }
    channels = [
        channel(40, "Lobby", discord.ChannelType.category),
        channel(
            41,
            "general",
            category_id=40,
            position=1,
            topic="say hello",
            slowmode_delay=5,
            nsfw=False,
            overwrites=overwrites,
        ),
        channel(42, "Stage", discord.ChannelType.voice, bitrate=64000, user_limit=10),
        channel(
            43,
            "help",
            discord.ChannelType.forum,
            available_tags=[
                SimpleNamespace(id=70, name="solved", moderated=True, emoji="✅"),
            ],
        ),
    ]
    return guild(), [everyone, leads], channels


def test_a_capture_holds_the_server_its_roles_its_channels_and_its_overwrites():
    found = capture(*everything())

    assert found["guild"] == {
        "id": "7",
        "name": "Black Bloc",
        "verification_level": "medium",
        "default_notifications": "only_mentions",
        "system_channel_id": "41",
        "rules_channel_id": None,
    }
    assert found["roles"][1] == {
        "id": "11",
        "name": "Leads",
        "color": 0x4EEFFF,
        "permissions": 8,
        "position": 2,
        "hoist": True,
        "mentionable": False,
        "managed": False,
    }
    general = found["channels"][1]
    assert (general["name"], general["type"], general["parent_id"]) == ("general", "text", "40")
    assert (general["topic"], general["slowmode"], general["nsfw"]) == ("say hello", 5, False)
    assert found["channels"][2]["bitrate"] == 64000 and found["channels"][2]["user_limit"] == 10
    assert found["channels"][3]["tags"] == [
        {"id": "70", "name": "solved", "moderated": True, "emoji": "✅"}
    ]
    assert counts(found) == {"roles": 2, "categories": 1, "channels": 3, "overwrites": 3}


def test_an_overwrite_keeps_its_target_its_kind_and_both_permission_values():
    general = capture(*everything())["channels"][1]
    view = discord.Permissions(view_channel=True).value
    manage = discord.Permissions(view_channel=True, manage_messages=True).value
    send = discord.Permissions(send_messages=True).value

    assert general["overwrites"] == [
        {"target_id": "7", "target_type": "role", "allow": 0, "deny": view},
        {"target_id": "11", "target_type": "role", "allow": manage, "deny": 0},
        {"target_id": "900", "target_type": "member", "allow": 0, "deny": send},
    ]


def test_nothing_about_members_or_messages_is_ever_captured():
    said = json.dumps(capture(*everything()))

    assert "sam" not in said
    assert "a secret said in chat" not in said
    assert "owner" not in said and "members" not in said
    assert said.count("900") == 1


def test_a_capture_with_no_roles_is_refused_rather_than_stored():
    with pytest.raises(CaptureError) as refused:
        capture(guild(), [], [])

    assert str(refused.value) == NO_ROLES


def test_a_channel_that_lacks_a_field_reads_as_nothing_not_as_a_crash():
    bare = SimpleNamespace(id=50, name="bare", type="text")

    found = channel_row(bare, set())

    assert found["parent_id"] is None and found["topic"] is None
    assert found["tags"] == [] and found["overwrites"] == []


def test_a_role_row_reads_plain_numbers_as_well_as_discords_own_objects():
    plain = SimpleNamespace(id=12, name="Plain", color=255, permissions=1024, position=1)

    assert role_row(plain)["permissions"] == 1024 and role_row(plain)["color"] == 255
