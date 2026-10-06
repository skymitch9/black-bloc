import copy
import inspect
import string

import discord
import pytest

from black_bloc import structure_diff
from black_bloc.structure import (
    CHANNEL_FIELDS,
    GUILD_FIELDS,
    OVERWRITE_FIELDS,
    ROLE_FIELDS,
    TAG_FIELDS,
    digest,
)
from black_bloc.structure_diff import (
    AREAS,
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


def texts(old, new):
    return [one["text"] for one in changes(old, new)]


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


def test_the_wording_is_fixed_in_code_and_the_diff_takes_none_from_anywhere():
    assert list(inspect.signature(changes).parameters) == ["old", "new", "escape"]
    assert "store" not in inspect.getsource(structure_diff)


def test_every_sentence_fills_in_from_its_own_placeholders():
    for name, words in WORDS.items():
        fields = {field for _, field, _, _ in string.Formatter().parse(words) if field}
        filled = sentence(name, **{field: "x" for field in fields})
        assert filled and "{" not in filled, name
    assert sentence("target_member", id="900") == "member 900"


def test_the_kept_run_is_the_longest_one_still_in_order():
    assert kept_in_order(list("abcde"), list("abcde")) == set("abcde")
    assert kept_in_order(list("abcde"), list("eabcd")) == set("abcd")
    assert kept_in_order([], []) == set()
    assert moved(list("abcde"), list("eabcd")) == ["e"]
    assert moved(list("abcde"), list("xacbe")) in (["c"], ["b"])
    assert moved(list("abc"), list("xyz")) == []


def test_two_channels_with_one_name_are_told_apart_by_their_category():
    old = base()
    by_id(old["channels"], 51)["name"] = "general"

    def change(new):
        by_id(new["channels"], 51)["name"] = "general"
        by_id(new["channels"], 51)["topic"] = "staff only"
        by_id(new["channels"], 41)["overwrites"].append(overwrite(12, allow=SEND))

    assert texts(old, edited(change)) == [
        "Channel **general · Staff**'s topic changed from nothing to staff only.",
        "In **general · Lobby**, role **Mods** got its own permissions: "
        "now allowed Send Messages.",
    ]


def test_two_channels_with_one_name_in_one_place_fall_back_to_their_ids():
    old = base()
    by_id(old["channels"], 42)["name"] = "general"

    def change(new):
        by_id(new["channels"], 42)["name"] = "general"
        by_id(new["channels"], 42)["topic"] = "second"

    assert texts(old, edited(change)) == [
        "Channel **general · Lobby · 42**'s topic changed from nothing to second."
    ]


def test_a_name_that_is_unique_is_left_as_it_is():
    def change(new):
        by_id(new["channels"], 42)["topic"] = "only memes"

    assert texts(base(), edited(change)) == [
        "Channel **memes**'s topic changed from nothing to only memes."
    ]


def test_names_and_free_text_are_escaped_when_the_reader_is_discord():
    evil = "**x** [click](https://evil.example)"

    def change(new):
        new["roles"].append(role(14, evil, VIEW, 4))
        by_id(new["channels"], 42)["name"] = evil
        by_id(new["channels"], 43)["topic"] = evil
        new["guild"]["name"] = evil

    new = edited(change)
    said = [
        one["text"] for one in changes(base(), new, escape=discord.utils.escape_markdown)
    ]

    assert len(said) == 4
    for line in said:
        assert "\\*\\*x\\*\\* \\[click](https://evil.example)" in line, line
        assert " [click](" not in line and "**x**" not in line, line
    assert f"Role **{evil}** was added." in texts(base(), new)


def test_an_overwrite_whose_target_changed_kind_is_a_change_that_is_said():
    old = base()
    by_id(old["channels"], 41)["overwrites"].append(overwrite(12, allow=SEND))

    def change(new):
        by_id(new["channels"], 41)["overwrites"].append(overwrite(12, allow=SEND, kind="member"))

    assert texts(old, edited(change)) == [
        "In **general**, member 12 got its own permissions: now allowed Send Messages.",
        "In **general**, role **Mods**'s own permissions were removed.",
    ]


def with_a_tag(**tag):
    found = base()
    by_id(found["channels"], 43)["tags"] = [
        {"id": "70", "name": "solved", "moderated": False, "emoji": "✅"} | tag
    ]
    return found


def test_a_forum_tags_emoji_changing_is_said_with_both_values():
    assert texts(with_a_tag(), with_a_tag(emoji="🎉")) == [
        "Forum **links**'s tag **solved** changed its emoji from ✅ to 🎉."
    ]
    assert texts(with_a_tag(), with_a_tag(emoji=None)) == [
        "Forum **links**'s tag **solved** changed its emoji from ✅ to nothing."
    ]


def test_a_forum_tag_becoming_moderators_only_is_said_and_so_is_the_way_back():
    assert texts(with_a_tag(), with_a_tag(moderated=True)) == [
        "Forum **links**'s tag **solved** changed moderators-only from off to on."
    ]
    assert texts(with_a_tag(moderated=True), with_a_tag()) == [
        "Forum **links**'s tag **solved** changed moderators-only from on to off."
    ]


def test_a_tag_renamed_and_restyled_at_once_is_one_line_for_each():
    assert texts(with_a_tag(), with_a_tag(name="done", emoji="🎉", moderated=True)) == [
        "Forum **links**'s tag **done** changed its emoji from ✅ to 🎉.",
        "Forum **links**'s tag **done** changed moderators-only from off to on.",
        "Forum **links**'s tag **solved** was renamed **done**.",
    ]


def test_a_custom_emoji_is_escaped_when_the_reader_is_discord():
    found = changes(with_a_tag(), with_a_tag(emoji="<:a_b:1>"), escape=lambda text: f"[{text}]")

    assert [one["text"] for one in found] == [
        "Forum **[links]**'s tag **[solved]** changed its emoji from [✅] to [<:a_b:1>]."
    ]


def full():
    found = base()
    found["guild"]["rules_channel_id"] = "42"
    for one in found["roles"]:
        one.update(color=0, hoist=False, mentionable=False, managed=False)
    for one in found["channels"]:
        one.update(topic="t", slowmode=0, nsfw=False, bitrate=64000, user_limit=0)
    by_id(found["channels"], 41)["overwrites"] = [overwrite(11, allow=VIEW, deny=SEND)]
    by_id(found["channels"], 43)["tags"] = [
        {"id": "70", "name": "solved", "moderated": False, "emoji": "✅"}
    ]
    return found


OTHER_VALUE = {
    "id": "999",
    "name": "another",
    "verification_level": "high",
    "default_notifications": "all_messages",
    "system_channel_id": "42",
    "rules_channel_id": "43",
    "color": 255,
    "permissions": KICK,
    "position": 7,
    "hoist": True,
    "mentionable": True,
    "managed": True,
    "type": "voice",
    "parent_id": "50",
    "topic": "another topic",
    "slowmode": 5,
    "nsfw": True,
    "bitrate": 96000,
    "user_limit": 9,
    "moderated": True,
    "emoji": "🎉",
    "target_id": "12",
    "target_type": "member",
    "allow": KICK,
    "deny": MANAGE,
}
HOLDERS = {
    "guild": (GUILD_FIELDS, lambda found: found["guild"]),
    "role": (ROLE_FIELDS, lambda found: by_id(found["roles"], 12)),
    "channel": (CHANNEL_FIELDS, lambda found: by_id(found["channels"], 42)),
    "tag": (TAG_FIELDS, lambda found: by_id(found["channels"], 43)["tags"][0]),
    "overwrite": (OVERWRITE_FIELDS, lambda found: by_id(found["channels"], 41)["overwrites"][0]),
}
NEVER_COMPARED = {("guild", "id")}
EVERY_FIELD = [
    (part, field)
    for part, (fields, _) in HOLDERS.items()
    for field in fields
    if (part, field) not in NEVER_COMPARED
]


@pytest.mark.parametrize(("part", "field"), EVERY_FIELD)
def test_every_field_a_snapshot_holds_moves_the_digest_and_has_something_to_say(part, field):
    new = full()
    HOLDERS[part][1](new)[field] = OTHER_VALUE[field]

    assert digest(new) != digest(full()), (part, field)
    assert changes(full(), new), (part, field)


def test_the_field_table_covers_every_field_list_so_a_new_field_needs_a_sentence():
    named = {*GUILD_FIELDS, *ROLE_FIELDS, *CHANNEL_FIELDS, *TAG_FIELDS, *OVERWRITE_FIELDS}

    assert named == set(OTHER_VALUE)


def renumbered(found):
    for one in found["roles"]:
        one["position"] = one["position"] * 10 + 3
    for one in found["channels"]:
        one["position"] = one["position"] * 7 + 2
    return found


def test_positions_renumbered_with_the_order_kept_are_the_same_digest_and_say_nothing():
    assert digest(renumbered(full())) == digest(full())
    assert changes(full(), renumbered(full())) == []


def swapped(found, key, one, two):
    first, second = by_id(found[key], one), by_id(found[key], two)
    first["position"], second["position"] = second["position"], first["position"]
    return found


@pytest.mark.parametrize(("key", "one", "two"), [("roles", 11, 12), ("channels", 41, 42)])
def test_an_order_that_changed_moves_the_digest_and_is_said(key, one, two):
    new = swapped(full(), key, one, two)

    assert digest(new) != digest(full())
    assert changes(full(), new)
