import copy

import discord

from black_bloc.structure_diff import (
    AREAS,
    DEFAULTS,
    WORDS,
    changes,
    kept_in_order,
    moved,
    permission_names,
    sentence,
)

VIEW = discord.Permissions(view_channel=True).value
SEND = discord.Permissions(send_messages=True).value
KICK = discord.Permissions(kick_members=True).value
MANAGE = discord.Permissions(manage_channels=True).value


def role(role_id, name, permissions=0, position=0, **extra):
    return {"id": str(role_id), "name": name, "permissions": permissions, "position": position}


def channel(channel_id, name, kind="text", parent=None, position=0, **extra):
    return {
        "id": str(channel_id),
        "name": name,
        "type": kind,
        "parent_id": str(parent) if parent else None,
        "position": position,
        "overwrites": [],
        "tags": [],
        **extra,
    }


def overwrite(target, allow=0, deny=0, kind="role"):
    return {"target_id": str(target), "target_type": kind, "allow": allow, "deny": deny}


def base():
    return {
        "guild": {
            "id": "7",
            "name": "Black Bloc",
            "verification_level": "low",
            "default_notifications": "only_mentions",
            "system_channel_id": "41",
            "rules_channel_id": None,
        },
        "roles": [
            role(7, "@everyone", VIEW, 0),
            role(11, "Members", VIEW | SEND, 1),
            role(12, "Mods", VIEW | SEND | KICK, 2),
            role(13, "Leads", VIEW | SEND | KICK | MANAGE, 3),
        ],
        "channels": [
            channel(40, "Lobby", "category", position=0),
            channel(50, "Staff", "category", position=1),
            channel(41, "general", parent=40, position=0, topic="say hello"),
            channel(42, "memes", parent=40, position=1),
            channel(43, "links", parent=40, position=2),
            channel(51, "mod-chat", parent=50, position=0),
            channel(60, "Stage", "voice", parent=40, position=0, bitrate=64000),
        ],
    }


def texts(old, new, say=None):
    return [one["text"] for one in changes(old, new, say)]


def edited(change):
    new = copy.deepcopy(base())
    change(new)
    return new


def by_id(rows, ident):
    return next(row for row in rows if row["id"] == str(ident))


def test_two_copies_of_one_structure_have_no_changes():
    assert changes(base(), base()) == []


def test_a_role_added_and_a_role_removed_are_named():
    def change(new):
        new["roles"].append(role(14, "Streamers", VIEW, 4))
        new["roles"].remove(by_id(new["roles"], 11))

    assert texts(base(), edited(change)) == [
        "Role **Members** was removed.",
        "Role **Streamers** was added.",
    ]


def test_a_renamed_role_says_both_names():
    def change(new):
        by_id(new["roles"], 12)["name"] = "Moderators"

    assert texts(base(), edited(change)) == ["Role **Mods** was renamed **Moderators**."]


def test_permissions_gained_and_lost_are_named_not_numbered():
    def change(new):
        mods = by_id(new["roles"], 12)
        mods["permissions"] = VIEW | SEND | MANAGE

    found = changes(base(), edited(change))

    assert [one["text"] for one in found] == [
        "Role **Mods** gained: Manage Channels.",
        "Role **Mods** lost: Kick Members.",
    ]
    assert {one["area"] for one in found} == {"permissions"}
    assert [one["kind"] for one in found] == ["added", "removed"]


def test_a_permission_bit_newer_than_the_library_is_still_reported():
    assert permission_names(1 << 62) == {"bit_62"}

    def change(new):
        by_id(new["roles"], 12)["permissions"] |= 1 << 62

    assert texts(base(), edited(change)) == ["Role **Mods** gained: Bit 62."]


def test_a_roles_colour_and_switches_read_as_words():
    old = base()
    by_id(old["roles"], 12).update(color=0, hoist=False)

    def change(new):
        by_id(new["roles"], 12).update(color=0x4EEFFF, hoist=True)

    new = edited(change)
    by_id(new["roles"], 12).setdefault("mentionable", None)

    assert texts(old, new) == [
        "Role **Mods**'s colour changed from #000000 to #4eefff.",
        "Role **Mods**'s shown separately changed from off to on.",
    ]


def test_adding_one_role_does_not_call_every_role_above_it_moved():
    def change(new):
        for one in new["roles"]:
            if one["position"] >= 2:
                one["position"] += 1
        new["roles"].append(role(14, "Streamers", VIEW, 2))

    assert texts(base(), edited(change)) == ["Role **Streamers** was added."]


def test_one_moved_role_is_one_line_naming_what_it_now_sits_under():
    def change(new):
        by_id(new["roles"], 13)["position"] = 1
        by_id(new["roles"], 11)["position"] = 2
        by_id(new["roles"], 12)["position"] = 3

    assert texts(base(), edited(change)) == [
        "Role **Leads** moved in the role list; it now sits under **Members**."
    ]


def test_a_role_moved_to_the_top_says_so():
    def change(new):
        by_id(new["roles"], 11)["position"] = 9

    assert texts(base(), edited(change)) == ["Role **Members** moved to the top of the role list."]


def test_a_channel_added_and_a_channel_removed_name_their_category():
    def change(new):
        added = channel(44, "clips", parent=40, position=3)
        added["overwrites"] = [overwrite(12, allow=VIEW)]
        new["channels"].append(added)
        new["channels"].remove(by_id(new["channels"], 51))

    assert texts(base(), edited(change)) == [
        "Channel **clips** (text) was added in **Lobby** with 1 permission overwrite(s).",
        "Channel **mod-chat** (text) was removed from **Staff**.",
    ]


def test_a_channel_outside_any_category_is_at_the_top_level():
    def change(new):
        new["channels"].append(channel(70, "lobby-two", position=5))

    assert texts(base(), edited(change)) == [
        "Channel **lobby-two** (text) was added in the top level with 0 permission overwrite(s)."
    ]


def test_a_channel_moved_to_another_category_is_one_line_and_not_a_reorder():
    def change(new):
        by_id(new["channels"], 42).update(parent_id="50", position=1)
        by_id(new["channels"], 43)["position"] = 1

    assert texts(base(), edited(change)) == ["Channel **memes** moved from **Lobby** to **Staff**."]


def test_a_channel_moved_inside_its_category_is_one_line():
    def change(new):
        by_id(new["channels"], 43)["position"] = 0
        by_id(new["channels"], 41)["position"] = 1
        by_id(new["channels"], 42)["position"] = 2

    assert texts(base(), edited(change)) == ["Channel **links** moved within **Lobby**."]


def test_a_voice_channel_is_ordered_among_voice_channels_only():
    def change(new):
        by_id(new["channels"], 60)["position"] = 5

    assert texts(base(), edited(change)) == []


def test_a_channels_own_settings_are_named_with_both_values():
    def change(new):
        by_id(new["channels"], 41).update(topic=None, slowmode=10, nsfw=True)
        by_id(new["channels"], 41)["name"] = "lounge"
        by_id(new["channels"], 60)["bitrate"] = 96000

    old = base()
    by_id(old["channels"], 41).update(slowmode=0, nsfw=False)

    assert texts(old, edited(change)) == [
        "Channel **Stage**'s bitrate changed from 64000 to 96000.",
        "Channel **general** was renamed **lounge**.",
        "Channel **lounge**'s age-restricted changed from off to on.",
        "Channel **lounge**'s slowmode in seconds changed from 0 to 10.",
        "Channel **lounge**'s topic changed from say hello to nothing.",
    ]


def test_a_long_topic_is_cut_short():
    def change(new):
        by_id(new["channels"], 41)["topic"] = "x" * 400

    said = texts(base(), edited(change))[0]

    assert len(said) < 200 and said.endswith("….")


def test_forum_tags_added_removed_and_renamed():
    old = base()
    by_id(old["channels"], 43)["tags"] = [
        {"id": "70", "name": "solved"},
        {"id": "71", "name": "bug"},
    ]

    def change(new):
        by_id(new["channels"], 43)["tags"] = [
            {"id": "70", "name": "done"},
            {"id": "72", "name": "idea"},
        ]

    assert texts(old, edited(change)) == [
        "Forum **links** gained the tag **idea**.",
        "Forum **links** lost the tag **bug**.",
        "Forum **links**'s tag **solved** was renamed **done**.",
    ]


def test_an_overwrite_added_changed_and_removed_reads_in_permission_names():
    old = base()
    by_id(old["channels"], 51)["overwrites"] = [
        overwrite(7, deny=VIEW),
        overwrite(12, allow=VIEW),
        overwrite(11, allow=VIEW),
    ]

    def change(new):
        by_id(new["channels"], 51)["overwrites"] = [
            overwrite(7, deny=VIEW),
            overwrite(12, allow=VIEW | MANAGE, deny=SEND),
            overwrite(900, allow=VIEW, kind="member"),
        ]

    found = changes(old, edited(change))

    assert [one["text"] for one in found] == [
        "In **mod-chat**, member 900 got its own permissions: now allowed View Channel.",
        "In **mod-chat**, role **Members**'s own permissions were removed.",
        "In **mod-chat**, role **Mods**'s permissions changed: now allowed Manage Channels; "
        "now denied Send Messages.",
    ]
    assert {one["area"] for one in found} == {"permissions"}


def test_an_overwrite_for_a_role_that_is_gone_falls_back_to_its_id():
    def change(new):
        by_id(new["channels"], 51)["overwrites"] = [overwrite(999, allow=VIEW)]

    assert texts(base(), edited(change)) == [
        "In **mod-chat**, role **999** got its own permissions: now allowed View Channel."
    ]


def test_server_settings_resolve_a_channel_id_to_its_name():
    def change(new):
        new["guild"].update(
            name="Blacker Bloc", verification_level="high", system_channel_id="42"
        )

    assert texts(base(), edited(change)) == [
        "The server's name changed from Black Bloc to Blacker Bloc.",
        "The server's system messages channel changed from general to memes.",
        "The server's verification level changed from low to high.",
    ]


def test_changes_come_grouped_server_roles_channels_permissions():
    def change(new):
        new["guild"]["name"] = "Blacker Bloc"
        new["roles"].append(role(14, "Streamers", VIEW, 4))
        new["channels"].append(channel(44, "clips", parent=40, position=3))
        by_id(new["roles"], 12)["permissions"] |= MANAGE

    areas = [one["area"] for one in changes(base(), edited(change))]

    assert areas == ["server", "roles", "channels", "permissions"]
    assert tuple(dict.fromkeys(areas)) == AREAS


def test_staff_wording_is_used_and_a_broken_template_falls_back():
    def change(new):
        new["roles"].append(role(14, "Streamers", VIEW, 4))

    new = edited(change)

    assert texts(base(), new, {"role_added": "New role: {role}"}) == ["New role: Streamers"]
    assert texts(base(), new, {"role_added": "New role: {nope}"}) == [
        "Role **Streamers** was added."
    ]
    assert texts(base(), new, {"role_added": "   "}) == ["Role **Streamers** was added."]


def test_every_sentence_fills_in_from_its_own_placeholders():
    for name, (words, what) in WORDS.items():
        assert what and DEFAULTS[name] == words
    assert sentence(None, "target_member", id="900") == "member 900"


def test_the_kept_run_is_the_longest_one_still_in_order():
    assert kept_in_order(list("abcde"), list("abcde")) == set("abcde")
    assert kept_in_order(list("abcde"), list("eabcd")) == set("abcd")
    assert kept_in_order([], []) == set()
    assert moved(list("abcde"), list("eabcd")) == ["e"]
    assert moved(list("abcde"), list("xacbe")) in (["c"], ["b"])
    assert moved(list("abc"), list("xyz")) == []
