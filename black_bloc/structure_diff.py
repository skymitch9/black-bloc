"""What changed between two structure snapshots, in words. Pure: two dicts in, rows out."""

from __future__ import annotations

from bisect import bisect_left
from collections import Counter
from collections.abc import Callable
from typing import Any

import discord

from .structure import MEMBER, by_id, clean, in_order, top_down

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
SHOWN_AS = {
    "read_messages": "view_channel",
    "external_emojis": "use_external_emojis",
    "external_stickers": "use_external_stickers",
    "send_polls": "create_polls",
}

WORDS: dict[str, str] = {
    "server_changed": "The server's {what} changed from {old} to {new}.",
    "role_added": "Role **{role}** was added.",
    "role_removed": "Role **{role}** was removed.",
    "role_renamed": "Role **{old}** was renamed **{new}**.",
    "role_gained": "Role **{role}** gained: {permissions}.",
    "role_lost": "Role **{role}** lost: {permissions}.",
    "role_changed": "Role **{role}**'s {what} changed from {old} to {new}.",
    "role_moved": "Role **{role}** moved in the role list; it now sits under **{above}**.",
    "role_moved_top": "Role **{role}** moved to the top of the role list.",
    "channel_added": (
        "Channel **{channel}** ({type}) was added in {place} with {n} permission overwrite(s)."
    ),
    "channel_removed": "Channel **{channel}** ({type}) was removed from {place}.",
    "channel_renamed": "Channel **{old}** was renamed **{new}**.",
    "channel_changed": "Channel **{channel}**'s {what} changed from {old} to {new}.",
    "channel_recategorised": "Channel **{channel}** moved from {old} to {new}.",
    "channel_reordered": "Channel **{channel}** moved within {place}.",
    "tag_added": "Forum **{channel}** gained the tag **{tag}**.",
    "tag_removed": "Forum **{channel}** lost the tag **{tag}**.",
    "tag_renamed": "Forum **{channel}**'s tag **{old}** was renamed **{new}**.",
    "tag_emoji": "Forum **{channel}**'s tag **{tag}** changed its emoji from {old} to {new}.",
    "tag_moderated": (
        "Forum **{channel}**'s tag **{tag}** changed moderators-only from {old} to {new}."
    ),
    "overwrite_added": "In **{channel}**, {target} got its own permissions: {detail}.",
    "overwrite_removed": "In **{channel}**, {target}'s own permissions were removed.",
    "overwrite_changed": "In **{channel}**, {target}'s permissions changed: {detail}.",
    "allow_gained": "now allowed {permissions}",
    "allow_lost": "no longer allowed {permissions}",
    "deny_gained": "now denied {permissions}",
    "deny_lost": "no longer denied {permissions}",
    "target_role": "role **{name}**",
    "target_member": "member {id}",
    "top_level": "the top level",
    "nothing": "nothing",
    "yes": "on",
    "no": "off",
    "f_name": "name",
    "f_verification": "verification level",
    "f_notifications": "default notifications",
    "f_system_channel": "system messages channel",
    "f_rules_channel": "rules channel",
    "f_colour": "colour",
    "f_hoist": "shown separately",
    "f_mentionable": "anyone can mention",
    "f_managed": "managed by an integration",
    "f_type": "type",
    "f_topic": "topic",
    "f_slowmode": "slowmode in seconds",
    "f_nsfw": "age-restricted",
    "f_bitrate": "bitrate",
    "f_user_limit": "user limit",
}

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
TAG_WORDS = (("emoji", "tag_emoji"), ("moderated", "tag_moderated"))


def sentence(name: str, /, **fields: Any) -> str:
    return WORDS[name].format(**fields)


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


def shown(value: Any, text: Callable[[Any], str] = str) -> str:
    if value is None or value == "":
        return sentence("nothing")
    if value is True:
        return sentence("yes")
    if value is False:
        return sentence("no")
    return text(clipped(value))


def colour(value: Any) -> str:
    return f"#{int(value or 0):06x}"


def by_target(rows: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    """An overwrite is who it is on AND what kind of thing that is."""
    return {
        (str(row.get("target_type")), str(row["target_id"])): row
        for row in rows
        if row.get("target_id") is not None
    }


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


class Names:
    """Ids read back as names, the newer snapshot's first, made safe for whoever reads them."""

    def __init__(
        self,
        old: dict[str, Any],
        new: dict[str, Any],
        escape: Callable[[str], str] | None = None,
    ) -> None:
        self.escape = escape
        self.roles = {**self.of(old["roles"]), **self.of(new["roles"])}
        held = {**by_id(old["channels"]), **by_id(new["channels"])}
        plain = self.of(list(held.values()))
        named = Counter(plain.values())
        placed = Counter((plain[ident], one["parent_id"]) for ident, one in held.items())
        self.channels = {
            ident: self.label(ident, one, plain, named, placed) for ident, one in held.items()
        }

    @staticmethod
    def of(rows: list[dict[str, Any]]) -> dict[str, str]:
        return {str(row["id"]): str(row["name"] or row["id"]) for row in rows}

    def text(self, value: Any) -> str:
        return self.escape(str(value)) if self.escape is not None else str(value)

    def label(
        self, ident: str, one: dict[str, Any], plain: dict[str, str], named: Any, placed: Any
    ) -> str:
        """A name two channels share also says where it is, and its id when that is shared too."""
        name = plain[ident]
        if named[name] < 2:
            return self.text(name)
        parent = one["parent_id"]
        if parent is None:
            place = sentence("top_level")
        else:
            place = self.text(plain.get(str(parent), parent))
        parts = [self.text(name), place]
        if placed[(name, parent)] > 1:
            parts.append(ident)
        return " · ".join(parts)

    def role(self, ident: Any) -> str:
        return self.text(self.roles.get(str(ident), str(ident)))

    def channel(self, ident: Any) -> str:
        return self.channels.get(str(ident), self.text(ident))


def row(area: str, kind: str, text: str) -> dict[str, str]:
    return {"area": area, "kind": kind, "text": text}


def place_of(names: Names, parent_id: Any) -> str:
    if parent_id is None:
        return sentence("top_level")
    return f"**{names.channel(parent_id)}**"


def server_changes(old: dict, new: dict, names: Names) -> list[dict[str, str]]:
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
                    "server_changed",
                    what=sentence(label),
                    old=shown(was, names.text),
                    new=shown(now, names.text),
                ),
            )
        )
    return found


def role_changes(old: dict, new: dict, names: Names) -> list[dict[str, str]]:
    was, now = by_id(old["roles"]), by_id(new["roles"])
    found: list[dict[str, str]] = []
    for ident in now.keys() - was.keys():
        found.append(row(ROLES, ADDED, sentence("role_added", role=names.role(ident))))
    for ident in was.keys() - now.keys():
        found.append(row(ROLES, REMOVED, sentence("role_removed", role=names.role(ident))))
    for ident in was.keys() & now.keys():
        found.extend(one_role(was[ident], now[ident], names))
    order = top_down(now)
    for ident in moved(top_down(was), order):
        above = order.index(ident) - 1
        if above < 0:
            text = sentence("role_moved_top", role=names.role(ident))
        else:
            text = sentence("role_moved", role=names.role(ident), above=names.role(order[above]))
        found.append(row(ROLES, MOVED, text))
    return found


def one_role(was: dict, now: dict, names: Names) -> list[dict[str, str]]:
    found: list[dict[str, str]] = []
    name = names.role(now["id"])
    if was["name"] != now["name"]:
        old = names.text(was["name"])
        found.append(row(ROLES, CHANGED, sentence("role_renamed", old=old, new=name)))
    before, after = permission_names(was["permissions"]), permission_names(now["permissions"])
    if after - before:
        found.append(
            row(
                PERMISSIONS,
                ADDED,
                sentence("role_gained", role=name, permissions=listed(after - before)),
            )
        )
    if before - after:
        found.append(
            row(
                PERMISSIONS,
                REMOVED,
                sentence("role_lost", role=name, permissions=listed(before - after)),
            )
        )
    for field, label in ROLE_LABELS:
        if was.get(field) == now.get(field):
            continue
        paint = colour if field == "color" else (lambda value: shown(value))
        found.append(
            row(
                ROLES,
                CHANGED,
                sentence(
                    "role_changed",
                    role=name,
                    what=sentence(label),
                    old=paint(was.get(field)),
                    new=paint(now.get(field)),
                ),
            )
        )
    return found


def channel_changes(old: dict, new: dict, names: Names) -> list[dict[str, str]]:
    was, now = by_id(old["channels"]), by_id(new["channels"])
    found: list[dict[str, str]] = []
    for ident in now.keys() - was.keys():
        channel = now[ident]
        found.append(
            row(
                CHANNELS,
                ADDED,
                sentence(
                    "channel_added",
                    channel=names.channel(ident),
                    type=channel["type"],
                    place=place_of(names, channel["parent_id"]),
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
                    "channel_removed",
                    channel=names.channel(ident),
                    type=channel["type"],
                    place=place_of(names, channel["parent_id"]),
                ),
            )
        )
    both = was.keys() & now.keys()
    for ident in both:
        found.extend(one_channel(was[ident], now[ident], names))
    stayed = {ident for ident in both if was[ident]["parent_id"] == now[ident]["parent_id"]}
    before = in_order({ident: was[ident] for ident in stayed})
    for group, after in in_order({ident: now[ident] for ident in stayed}).items():
        for ident in moved(before.get(group, []), after):
            found.append(
                row(
                    CHANNELS,
                    MOVED,
                    sentence(
                        "channel_reordered",
                        channel=names.channel(ident),
                        place=place_of(names, group[0]),
                    ),
                )
            )
    return found


def one_channel(was: dict, now: dict, names: Names) -> list[dict[str, str]]:
    found: list[dict[str, str]] = []
    name = names.channel(now["id"])
    if was["name"] != now["name"]:
        old = names.text(was["name"])
        found.append(row(CHANNELS, CHANGED, sentence("channel_renamed", old=old, new=name)))
    if was["parent_id"] != now["parent_id"]:
        found.append(
            row(
                CHANNELS,
                MOVED,
                sentence(
                    "channel_recategorised",
                    channel=name,
                    old=place_of(names, was["parent_id"]),
                    new=place_of(names, now["parent_id"]),
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
                    "channel_changed",
                    channel=name,
                    what=sentence(label),
                    old=shown(was.get(field), names.text),
                    new=shown(now.get(field), names.text),
                ),
            )
        )
    found.extend(tag_changes(was, now, name, names))
    found.extend(overwrite_changes(was, now, name, names))
    return found


def tag_changes(was: dict, now: dict, name: str, names: Names) -> list[dict[str, str]]:
    before, after = by_id(was["tags"]), by_id(now["tags"])
    found: list[dict[str, str]] = []
    for ident in after.keys() - before.keys():
        found.append(
            row(
                CHANNELS,
                ADDED,
                sentence("tag_added", channel=name, tag=names.text(after[ident]["name"])),
            )
        )
    for ident in before.keys() - after.keys():
        found.append(
            row(
                CHANNELS,
                REMOVED,
                sentence("tag_removed", channel=name, tag=names.text(before[ident]["name"])),
            )
        )
    for ident in before.keys() & after.keys():
        found.extend(one_tag(before[ident], after[ident], name, names))
    return found


def one_tag(was: dict, now: dict, name: str, names: Names) -> list[dict[str, str]]:
    found: list[dict[str, str]] = []
    tag = names.text(now["name"])
    if was["name"] != now["name"]:
        old = names.text(was["name"])
        found.append(
            row(CHANNELS, CHANGED, sentence("tag_renamed", channel=name, old=old, new=tag))
        )
    for field, words in TAG_WORDS:
        if was.get(field) == now.get(field):
            continue
        found.append(
            row(
                CHANNELS,
                CHANGED,
                sentence(
                    words,
                    channel=name,
                    tag=tag,
                    old=shown(was.get(field), names.text),
                    new=shown(now.get(field), names.text),
                ),
            )
        )
    return found


def target_words(one: dict[str, Any], names: Names) -> str:
    if one["target_type"] == MEMBER:
        return sentence("target_member", id=one["target_id"])
    return sentence("target_role", name=names.role(one["target_id"]))


def detail(was: dict[str, Any] | None, now: dict[str, Any]) -> str:
    old_allow = permission_names(was["allow"]) if was else set()
    old_deny = permission_names(was["deny"]) if was else set()
    allow, deny = permission_names(now["allow"]), permission_names(now["deny"])
    parts = (
        ("allow_gained", allow - old_allow),
        ("allow_lost", old_allow - allow),
        ("deny_gained", deny - old_deny),
        ("deny_lost", old_deny - deny),
    )
    said = [sentence(key, permissions=listed(names)) for key, names in parts if names]
    return "; ".join(said) or sentence("nothing")


def overwrite_changes(was: dict, now: dict, name: str, names: Names) -> list[dict[str, str]]:
    before, after = by_target(was["overwrites"]), by_target(now["overwrites"])
    found: list[dict[str, str]] = []
    for ident in after.keys() - before.keys():
        found.append(
            row(
                PERMISSIONS,
                ADDED,
                sentence(
                    "overwrite_added",
                    channel=name,
                    target=target_words(after[ident], names),
                    detail=detail(None, after[ident]),
                ),
            )
        )
    for ident in before.keys() - after.keys():
        found.append(
            row(
                PERMISSIONS,
                REMOVED,
                sentence(
                    "overwrite_removed",
                    channel=name,
                    target=target_words(before[ident], names),
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
                    "overwrite_changed",
                    channel=name,
                    target=target_words(new, names),
                    detail=detail(old, new),
                ),
            )
        )
    return found


def changes(
    old: Any,
    new: Any,
    *,
    escape: Callable[[str], str] | None = None,
) -> list[dict[str, str]]:
    """Every difference between two snapshot bodies, grouped by area, steady in its order."""
    before, after = clean(old), clean(new)
    names = Names(before, after, escape)
    found = [
        *server_changes(before, after, names),
        *role_changes(before, after, names),
        *channel_changes(before, after, names),
    ]
    spot = {area: index for index, area in enumerate(AREAS)}
    return sorted(found, key=lambda one: (spot[one["area"]], one["text"]))


__all__ = [
    "ADDED",
    "AREAS",
    "CHANGED",
    "CHANNELS",
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
