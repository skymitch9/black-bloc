"""What changed between two structure snapshots, in words. Pure: two dicts in, rows out."""

from __future__ import annotations

from bisect import bisect_left
from collections.abc import Mapping
from typing import Any

import discord

from .structure import CATEGORY, MEMBER, clean

SERVER = "server"
ROLES = "roles"
CHANNELS = "channels"
PERMISSIONS = "permissions"
AREAS = (SERVER, ROLES, CHANNELS, PERMISSIONS)

ADDED = "added"
REMOVED = "removed"
CHANGED = "changed"
MOVED = "moved"

TEXT_LIMIT = 80
VOICE_TYPES = ("voice", "stage_voice")
SHOWN_AS = {
    "read_messages": "view_channel",
    "external_emojis": "use_external_emojis",
    "external_stickers": "use_external_stickers",
    "send_polls": "create_polls",
}

WORDS: dict[str, tuple[str, str]] = {
    "server_changed": (
        "The server's {what} changed from {old} to {new}.",
        "a server-level setting that changed",
    ),
    "role_added": ("Role **{role}** was added.", "a role that is new"),
    "role_removed": ("Role **{role}** was removed.", "a role that is gone"),
    "role_renamed": ("Role **{old}** was renamed **{new}**.", "a role with a new name"),
    "role_gained": (
        "Role **{role}** gained: {permissions}.",
        "the permissions a role was given",
    ),
    "role_lost": ("Role **{role}** lost: {permissions}.", "the permissions a role lost"),
    "role_changed": (
        "Role **{role}**'s {what} changed from {old} to {new}.",
        "a role's colour or switches changing",
    ),
    "role_moved": (
        "Role **{role}** moved in the role list; it now sits under **{above}**.",
        "a role that moved in the role list",
    ),
    "role_moved_top": (
        "Role **{role}** moved to the top of the role list.",
        "a role that moved to the top of the role list",
    ),
    "channel_added": (
        "Channel **{channel}** ({type}) was added in {place} with {n} permission overwrite(s).",
        "a channel or category that is new",
    ),
    "channel_removed": (
        "Channel **{channel}** ({type}) was removed from {place}.",
        "a channel or category that is gone",
    ),
    "channel_renamed": (
        "Channel **{old}** was renamed **{new}**.",
        "a channel with a new name",
    ),
    "channel_changed": (
        "Channel **{channel}**'s {what} changed from {old} to {new}.",
        "a channel's topic, slowmode or limits changing",
    ),
    "channel_recategorised": (
        "Channel **{channel}** moved from {old} to {new}.",
        "a channel that moved to another category",
    ),
    "channel_reordered": (
        "Channel **{channel}** moved within {place}.",
        "a channel that moved up or down inside its category",
    ),
    "tag_added": ("Forum **{channel}** gained the tag **{tag}**.", "a forum tag that is new"),
    "tag_removed": ("Forum **{channel}** lost the tag **{tag}**.", "a forum tag that is gone"),
    "tag_renamed": (
        "Forum **{channel}**'s tag **{old}** was renamed **{new}**.",
        "a forum tag with a new name",
    ),
    "overwrite_added": (
        "In **{channel}**, {target} got its own permissions: {detail}.",
        "a role or member given its own permissions in a channel",
    ),
    "overwrite_removed": (
        "In **{channel}**, {target}'s own permissions were removed.",
        "a role or member losing its own permissions in a channel",
    ),
    "overwrite_changed": (
        "In **{channel}**, {target}'s permissions changed: {detail}.",
        "a role's or member's own permissions in a channel changing",
    ),
    "allow_gained": ("now allowed {permissions}", "the permissions newly allowed in a channel"),
    "allow_lost": (
        "no longer allowed {permissions}",
        "the permissions no longer allowed in a channel",
    ),
    "deny_gained": ("now denied {permissions}", "the permissions newly denied in a channel"),
    "deny_lost": (
        "no longer denied {permissions}",
        "the permissions no longer denied in a channel",
    ),
    "target_role": ("role **{name}**", "how a role is named in a channel's permissions"),
    "target_member": ("member {id}", "how a member is named in a channel's permissions"),
    "top_level": ("the top level", "a channel that sits in no category"),
    "nothing": ("nothing", "a value that is not set"),
    "yes": ("on", "a switch that is on"),
    "no": ("off", "a switch that is off"),
    "f_name": ("name", "the label for the server's name"),
    "f_verification": ("verification level", "the label for the verification level"),
    "f_notifications": ("default notifications", "the label for default notifications"),
    "f_system_channel": ("system messages channel", "the label for the system channel"),
    "f_rules_channel": ("rules channel", "the label for the rules channel"),
    "f_colour": ("colour", "the label for a role's colour"),
    "f_hoist": ("shown separately", "the label for a role shown separately"),
    "f_mentionable": ("anyone can mention", "the label for a role anyone can mention"),
    "f_managed": ("managed by an integration", "the label for a managed role"),
    "f_type": ("type", "the label for a channel's type"),
    "f_topic": ("topic", "the label for a channel's topic"),
    "f_slowmode": ("slowmode in seconds", "the label for a channel's slowmode"),
    "f_nsfw": ("age-restricted", "the label for an age-restricted channel"),
    "f_bitrate": ("bitrate", "the label for a voice channel's bitrate"),
    "f_user_limit": ("user limit", "the label for a voice channel's user limit"),
}
DEFAULTS: dict[str, str] = {name: words for name, (words, _) in WORDS.items()}

SERVER_LABELS = (
    ("name", "f_name"),
    ("verification_level", "f_verification"),
    ("default_notifications", "f_notifications"),
    ("system_channel_id", "f_system_channel"),
    ("rules_channel_id", "f_rules_channel"),
)
SERVER_CHANNEL_FIELDS = ("system_channel_id", "rules_channel_id")
ROLE_LABELS = (
    ("color", "f_colour"),
    ("hoist", "f_hoist"),
    ("mentionable", "f_mentionable"),
    ("managed", "f_managed"),
)
CHANNEL_LABELS = (
    ("type", "f_type"),
    ("topic", "f_topic"),
    ("slowmode", "f_slowmode"),
    ("nsfw", "f_nsfw"),
    ("bitrate", "f_bitrate"),
    ("user_limit", "f_user_limit"),
)


def sentence(say: Mapping[str, str] | None, name: str, /, **fields: Any) -> str:
    """Staff wording first; a template that cannot be filled falls back to the shipped one."""
    wording = str((say or {}).get(name) or "").strip()
    if wording:
        try:
            return wording.format(**fields)
        except (IndexError, KeyError, ValueError):
            pass
    return DEFAULTS[name].format(**fields)


def permission_names(value: Any) -> set[str]:
    bits = int(value or 0)
    found = {SHOWN_AS.get(name, name) for name, on in discord.Permissions(bits) if on}
    known = discord.Permissions.all().value
    stray = bits & ~known
    spot = 0
    while stray:
        if stray & 1:
            found.add(f"bit_{spot}")
        stray >>= 1
        spot += 1
    return found


def listed(names: set[str]) -> str:
    return ", ".join(name.replace("_", " ").title() for name in sorted(names))


def clipped(value: Any) -> str:
    text = " ".join(str(value).split())
    return text if len(text) <= TEXT_LIMIT else text[: TEXT_LIMIT - 1] + "…"


def shown(say: Mapping[str, str] | None, value: Any) -> str:
    if value is None or value == "":
        return sentence(say, "nothing")
    if value is True:
        return sentence(say, "yes")
    if value is False:
        return sentence(say, "no")
    return clipped(value)


def colour(value: Any) -> str:
    return f"#{int(value or 0):06x}"


def by_id(rows: list[dict[str, Any]], field: str = "id") -> dict[str, dict[str, Any]]:
    return {str(row[field]): row for row in rows if row.get(field) is not None}


def kept_in_order(before: list[str], after: list[str]) -> set[str]:
    """The longest run of `after` still in `before`'s order; everything outside it moved."""
    spot = {ident: index for index, ident in enumerate(before)}
    ranks = [spot[ident] for ident in after]
    tails: list[int] = []
    tail_at: list[int] = []
    previous: list[int] = [-1] * len(ranks)
    for index, rank in enumerate(ranks):
        place = bisect_left(tails, rank)
        if place == len(tails):
            tails.append(rank)
            tail_at.append(index)
        else:
            tails[place] = rank
            tail_at[place] = index
        previous[index] = tail_at[place - 1] if place else -1
    kept: set[str] = set()
    index = tail_at[-1] if tail_at else -1
    while index >= 0:
        kept.add(after[index])
        index = previous[index]
    return kept


def moved(before: list[str], after: list[str]) -> list[str]:
    common = set(before) & set(after)
    old = [ident for ident in before if ident in common]
    new = [ident for ident in after if ident in common]
    kept = kept_in_order(old, new)
    return [ident for ident in new if ident not in kept]


def top_down(roles: dict[str, dict[str, Any]]) -> list[str]:
    return sorted(roles, key=lambda one: (-int(roles[one]["position"] or 0), one))


class Names:
    """Ids read back as names, the newer snapshot's first."""

    def __init__(self, old: dict[str, Any], new: dict[str, Any]) -> None:
        self.roles = {**self.of(old["roles"]), **self.of(new["roles"])}
        self.channels = {**self.of(old["channels"]), **self.of(new["channels"])}

    @staticmethod
    def of(rows: list[dict[str, Any]]) -> dict[str, str]:
        return {str(row["id"]): str(row["name"] or row["id"]) for row in rows}

    def role(self, ident: Any) -> str:
        return self.roles.get(str(ident), str(ident))

    def channel(self, ident: Any) -> str:
        return self.channels.get(str(ident), str(ident))


def row(area: str, kind: str, text: str) -> dict[str, str]:
    return {"area": area, "kind": kind, "text": text}


def place_of(say: Mapping[str, str] | None, names: Names, parent_id: Any) -> str:
    if parent_id is None:
        return sentence(say, "top_level")
    return f"**{names.channel(parent_id)}**"


def server_changes(old: dict, new: dict, names: Names, say: Any) -> list[dict[str, str]]:
    found: list[dict[str, str]] = []
    for field, label in SERVER_LABELS:
        was, now = old["guild"].get(field), new["guild"].get(field)
        if was == now:
            continue
        if field in SERVER_CHANNEL_FIELDS:
            was = names.channel(was) if was else None
            now = names.channel(now) if now else None
        found.append(
            row(
                SERVER,
                CHANGED,
                sentence(
                    say,
                    "server_changed",
                    what=sentence(say, label),
                    old=shown(say, was),
                    new=shown(say, now),
                ),
            )
        )
    return found


def role_changes(old: dict, new: dict, names: Names, say: Any) -> list[dict[str, str]]:
    was, now = by_id(old["roles"]), by_id(new["roles"])
    found: list[dict[str, str]] = []
    for ident in now.keys() - was.keys():
        found.append(row(ROLES, ADDED, sentence(say, "role_added", role=names.role(ident))))
    for ident in was.keys() - now.keys():
        found.append(row(ROLES, REMOVED, sentence(say, "role_removed", role=names.role(ident))))
    for ident in was.keys() & now.keys():
        found.extend(one_role(was[ident], now[ident], say))
    order = top_down(now)
    for ident in moved(top_down(was), order):
        above = order.index(ident) - 1
        if above < 0:
            text = sentence(say, "role_moved_top", role=names.role(ident))
        else:
            text = sentence(
                say, "role_moved", role=names.role(ident), above=names.role(order[above])
            )
        found.append(row(ROLES, MOVED, text))
    return found


def one_role(was: dict, now: dict, say: Any) -> list[dict[str, str]]:
    found: list[dict[str, str]] = []
    name = str(now["name"] or now["id"])
    if was["name"] != now["name"]:
        found.append(
            row(ROLES, CHANGED, sentence(say, "role_renamed", old=was["name"], new=name))
        )
    before, after = permission_names(was["permissions"]), permission_names(now["permissions"])
    if after - before:
        found.append(
            row(
                PERMISSIONS,
                ADDED,
                sentence(say, "role_gained", role=name, permissions=listed(after - before)),
            )
        )
    if before - after:
        found.append(
            row(
                PERMISSIONS,
                REMOVED,
                sentence(say, "role_lost", role=name, permissions=listed(before - after)),
            )
        )
    for field, label in ROLE_LABELS:
        if was.get(field) == now.get(field):
            continue
        paint = colour if field == "color" else (lambda value: shown(say, value))
        found.append(
            row(
                ROLES,
                CHANGED,
                sentence(
                    say,
                    "role_changed",
                    role=name,
                    what=sentence(say, label),
                    old=paint(was.get(field)),
                    new=paint(now.get(field)),
                ),
            )
        )
    return found


def bucket(channel: dict[str, Any]) -> str:
    if channel["type"] == CATEGORY:
        return CATEGORY
    return "voice" if channel["type"] in VOICE_TYPES else "text"


def in_order(channels: dict[str, dict[str, Any]]) -> dict[tuple[Any, str], list[str]]:
    groups: dict[tuple[Any, str], list[str]] = {}
    ranked = sorted(channels, key=lambda one: (int(channels[one]["position"] or 0), one))
    for ident in ranked:
        channel = channels[ident]
        groups.setdefault((channel["parent_id"], bucket(channel)), []).append(ident)
    return groups


def channel_changes(old: dict, new: dict, names: Names, say: Any) -> list[dict[str, str]]:
    was, now = by_id(old["channels"]), by_id(new["channels"])
    found: list[dict[str, str]] = []
    for ident in now.keys() - was.keys():
        channel = now[ident]
        found.append(
            row(
                CHANNELS,
                ADDED,
                sentence(
                    say,
                    "channel_added",
                    channel=names.channel(ident),
                    type=channel["type"],
                    place=place_of(say, names, channel["parent_id"]),
                    n=len(channel["overwrites"]),
                ),
            )
        )
    for ident in was.keys() - now.keys():
        channel = was[ident]
        found.append(
            row(
                CHANNELS,
                REMOVED,
                sentence(
                    say,
                    "channel_removed",
                    channel=names.channel(ident),
                    type=channel["type"],
                    place=place_of(say, names, channel["parent_id"]),
                ),
            )
        )
    both = was.keys() & now.keys()
    for ident in both:
        found.extend(one_channel(was[ident], now[ident], names, say))
    stayed = {ident for ident in both if was[ident]["parent_id"] == now[ident]["parent_id"]}
    before = in_order({ident: was[ident] for ident in stayed})
    for group, after in in_order({ident: now[ident] for ident in stayed}).items():
        for ident in moved(before.get(group, []), after):
            found.append(
                row(
                    CHANNELS,
                    MOVED,
                    sentence(
                        say,
                        "channel_reordered",
                        channel=names.channel(ident),
                        place=place_of(say, names, group[0]),
                    ),
                )
            )
    return found


def one_channel(was: dict, now: dict, names: Names, say: Any) -> list[dict[str, str]]:
    found: list[dict[str, str]] = []
    name = str(now["name"] or now["id"])
    if was["name"] != now["name"]:
        found.append(
            row(CHANNELS, CHANGED, sentence(say, "channel_renamed", old=was["name"], new=name))
        )
    if was["parent_id"] != now["parent_id"]:
        found.append(
            row(
                CHANNELS,
                MOVED,
                sentence(
                    say,
                    "channel_recategorised",
                    channel=name,
                    old=place_of(say, names, was["parent_id"]),
                    new=place_of(say, names, now["parent_id"]),
                ),
            )
        )
    for field, label in CHANNEL_LABELS:
        if was.get(field) == now.get(field):
            continue
        found.append(
            row(
                CHANNELS,
                CHANGED,
                sentence(
                    say,
                    "channel_changed",
                    channel=name,
                    what=sentence(say, label),
                    old=shown(say, was.get(field)),
                    new=shown(say, now.get(field)),
                ),
            )
        )
    found.extend(tag_changes(was, now, name, say))
    found.extend(overwrite_changes(was, now, name, names, say))
    return found


def tag_changes(was: dict, now: dict, name: str, say: Any) -> list[dict[str, str]]:
    before, after = by_id(was["tags"]), by_id(now["tags"])
    found: list[dict[str, str]] = []
    for ident in after.keys() - before.keys():
        found.append(
            row(
                CHANNELS,
                ADDED,
                sentence(say, "tag_added", channel=name, tag=after[ident]["name"]),
            )
        )
    for ident in before.keys() - after.keys():
        found.append(
            row(
                CHANNELS,
                REMOVED,
                sentence(say, "tag_removed", channel=name, tag=before[ident]["name"]),
            )
        )
    for ident in before.keys() & after.keys():
        if before[ident]["name"] != after[ident]["name"]:
            found.append(
                row(
                    CHANNELS,
                    CHANGED,
                    sentence(
                        say,
                        "tag_renamed",
                        channel=name,
                        old=before[ident]["name"],
                        new=after[ident]["name"],
                    ),
                )
            )
    return found


def target_words(one: dict[str, Any], names: Names, say: Any) -> str:
    if one["target_type"] == MEMBER:
        return sentence(say, "target_member", id=one["target_id"])
    return sentence(say, "target_role", name=names.role(one["target_id"]))


def detail(was: dict[str, Any] | None, now: dict[str, Any], say: Any) -> str:
    old_allow = permission_names(was["allow"]) if was else set()
    old_deny = permission_names(was["deny"]) if was else set()
    allow, deny = permission_names(now["allow"]), permission_names(now["deny"])
    parts = (
        ("allow_gained", allow - old_allow),
        ("allow_lost", old_allow - allow),
        ("deny_gained", deny - old_deny),
        ("deny_lost", old_deny - deny),
    )
    said = [sentence(say, key, permissions=listed(names)) for key, names in parts if names]
    return "; ".join(said) or sentence(say, "nothing")


def overwrite_changes(
    was: dict, now: dict, name: str, names: Names, say: Any
) -> list[dict[str, str]]:
    before, after = by_id(was["overwrites"], "target_id"), by_id(now["overwrites"], "target_id")
    found: list[dict[str, str]] = []
    for ident in after.keys() - before.keys():
        found.append(
            row(
                PERMISSIONS,
                ADDED,
                sentence(
                    say,
                    "overwrite_added",
                    channel=name,
                    target=target_words(after[ident], names, say),
                    detail=detail(None, after[ident], say),
                ),
            )
        )
    for ident in before.keys() - after.keys():
        found.append(
            row(
                PERMISSIONS,
                REMOVED,
                sentence(
                    say,
                    "overwrite_removed",
                    channel=name,
                    target=target_words(before[ident], names, say),
                ),
            )
        )
    for ident in before.keys() & after.keys():
        old, new = before[ident], after[ident]
        if (old["allow"], old["deny"]) == (new["allow"], new["deny"]):
            continue
        found.append(
            row(
                PERMISSIONS,
                CHANGED,
                sentence(
                    say,
                    "overwrite_changed",
                    channel=name,
                    target=target_words(new, names, say),
                    detail=detail(old, new, say),
                ),
            )
        )
    return found


def changes(old: Any, new: Any, say: Mapping[str, str] | None = None) -> list[dict[str, str]]:
    """Every difference between two snapshot bodies, grouped by area, steady in its order."""
    before, after = clean(old), clean(new)
    names = Names(before, after)
    found = [
        *server_changes(before, after, names, say),
        *role_changes(before, after, names, say),
        *channel_changes(before, after, names, say),
    ]
    spot = {area: index for index, area in enumerate(AREAS)}
    return sorted(found, key=lambda one: (spot[one["area"]], one["text"]))


__all__ = [
    "ADDED",
    "AREAS",
    "CHANGED",
    "CHANNELS",
    "DEFAULTS",
    "MOVED",
    "PERMISSIONS",
    "REMOVED",
    "ROLES",
    "SERVER",
    "WORDS",
    "changes",
    "kept_in_order",
    "moved",
    "permission_names",
    "sentence",
]
