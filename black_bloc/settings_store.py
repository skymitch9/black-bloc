from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime
from typing import Any

from .config import Settings
from .storage.db import Database

log = logging.getLogger(__name__)

GOLIVE_CHANNEL_ID = 1225457308230746202
GOLIVE_TEMPLATE = (
    "REGULATORS! Mount up! **{name}** is currently streaming **{game}**! "
    "Check it out: {url}"
)
GOLIVE_MODES = ("off", "shadow", "on")

MEMBER_ROLE_ID = 1073741054563602532
TEMPVOICE_NAME_TEMPLATE = "{user}'s bloc"
TEMPVOICE_MODES = ("off", "on")
HONEYPOT_MODES = ("off", "shadow", "on")
HONEYPOT_PURGE_MAX_DAYS = 7

BIRTHDAY_CHANNEL_ID = 1411816390414962700
BIRTHDAY_TEMPLATE = "Happy Birthday **{name}**!"
BIRTHDAY_COLOR = "#4eefff"
BIRTHDAY_TZ = "America/Phoenix"
BIRTHDAY_MODES = ("off", "shadow", "on")
HEX_COLOR = re.compile(r"^#?([0-9a-fA-F]{6})$")

KEY_TYPES: dict[str, str] = {
    "log_channel_id": "channel",
    "staff_channel_id": "channel",
    "role_menu_channel_id": "channel",
    "golive_mode": "enum",
    "golive_channel_id": "channel",
    "golive_template": "text",
    "golive_live_role_id": "role",
    "golive_require_role_id": "role",
    "golive_ignore_role_id": "role",
    "golive_cooldown_minutes": "int",
    "golive_ping_role_id": "role",
    "golive_max_session_hours": "int",
    "tempvoice_mode": "enum",
    "tempvoice_creator_ids": "channels",
    "tempvoice_name_template": "text",
    "tempvoice_allowed_role_id": "role",
    "honeypot_mode": "enum",
    "honeypot_channel_ids": "channels",
    "honeypot_purge_days": "int",
    "honeypot_exempt_role_ids": "roles",
    "birthday_mode": "enum",
    "birthday_channel_id": "channel",
    "birthday_template": "text",
    "birthday_color": "color",
    "birthday_role_id": "role",
    "birthday_show_age": "bool",
}

KEY_CHOICES: dict[str, tuple[str, ...]] = {
    "golive_mode": GOLIVE_MODES,
    "tempvoice_mode": TEMPVOICE_MODES,
    "honeypot_mode": HONEYPOT_MODES,
    "birthday_mode": BIRTHDAY_MODES,
}

KEY_MAX: dict[str, int] = {"honeypot_purge_days": HONEYPOT_PURGE_MAX_DAYS}

KEY_HELP: dict[str, str] = {
    "log_channel_id": "where Black Bloc posts what it did",
    "staff_channel_id": "the channel whose viewers count as staff",
    "role_menu_channel_id": "where /rolemenu post goes by default",
    "golive_mode": "off, shadow (log only) or on (post go-live announcements)",
    "golive_channel_id": "where go-live announcements are posted",
    "golive_template": "the announcement wording; {name} {game} {title} {url}",
    "golive_live_role_id": "role given while someone is streaming",
    "golive_require_role_id": "only announce people who have this role",
    "golive_ignore_role_id": "never announce people who have this role",
    "golive_cooldown_minutes": "minutes before the same person is announced again",
    "golive_ping_role_id": "role mentioned in front of every go-live announcement",
    "golive_max_session_hours": "hours before a stream still marked live is closed anyway",
    "tempvoice_mode": "off, or on (join-to-create makes a temporary voice channel)",
    "tempvoice_creator_ids": "the join-to-create channels; /tempvoice setup fills this in",
    "tempvoice_name_template": "what a spawned channel is called; {user} is the member",
    "tempvoice_allowed_role_id": "only members with this role get a temporary channel",
    "honeypot_mode": "off, shadow (log only) or on (ban whoever posts in the trap)",
    "honeypot_channel_ids": "the trap channels; /honeypot setup fills this in",
    "honeypot_purge_days": (
        f"days of the banned account's messages to delete with it, 0 to "
        f"{HONEYPOT_PURGE_MAX_DAYS}"
    ),
    "honeypot_exempt_role_ids": "roles the trap ignores; staff are always ignored too",
    "birthday_mode": "off, shadow (log only) or on (post birthday wishes)",
    "birthday_channel_id": "where birthday wishes are posted",
    "birthday_template": "the birthday wording; {name} and {age}",
    "birthday_color": "the birthday embed's colour, as a hex code like #4eefff",
    "birthday_role_id": "role given for the day and taken back the next; none by default",
    "birthday_show_age": "true to put {age} in reach for people who stored a birth year",
}


GUILD_ONLY = (
    "That command changes settings for a server, so it has to be run in the server itself "
    "rather than in a DM. Run it again from a channel Black Bloc can answer in."
)
DB_UNAVAILABLE = (
    "Black Bloc cannot reach its own database right now, so nothing was changed. It needs the "
    "bot to finish starting up — wait a moment and run the command again, and tell a Lead if it "
    "keeps happening."
)


class SettingError(ValueError):
    """A settings key is unknown, or its value is the wrong type."""


def coerce_value(key: str, value: Any) -> Any:
    """Validate a value against the registry and return what gets stored."""
    kind = KEY_TYPES.get(key)
    if kind is None:
        known = ", ".join(sorted(KEY_TYPES))
        raise SettingError(f"{key!r} is not a Black Bloc setting. Known settings: {known}.")
    if kind == "channel":
        raw = getattr(value, "id", value)
        if isinstance(raw, bool) or not isinstance(raw, int):
            raise SettingError(f"{key!r} takes a channel, not {value!r}.")
        return raw
    if kind == "role":
        raw = getattr(value, "id", value)
        if isinstance(raw, bool) or not isinstance(raw, int):
            raise SettingError(f"{key!r} takes a role, not {value!r}.")
        return raw
    if kind in ("channels", "roles"):
        what = "channels" if kind == "channels" else "roles"
        if isinstance(value, str | bytes) or not isinstance(value, list | tuple | set):
            raise SettingError(f"{key!r} takes a list of {what}, not {value!r}.")
        ids: list[int] = []
        for item in value:
            raw = getattr(item, "id", item)
            if isinstance(raw, bool) or not isinstance(raw, int):
                raise SettingError(f"{key!r} takes a list of {what}, not {value!r}.")
            if raw not in ids:
                ids.append(raw)
        return ids
    if kind == "enum":
        allowed = KEY_CHOICES.get(key, ())
        if value not in allowed:
            raise SettingError(
                f"{key!r} takes one of {', '.join(allowed)}, not {value!r}."
            )
        return value
    if kind == "int":
        if isinstance(value, bool) or not isinstance(value, int):
            raise SettingError(f"{key!r} takes a whole number, not {value!r}.")
        if value < 0:
            raise SettingError(f"{key!r} cannot be negative.")
        limit = KEY_MAX.get(key)
        if limit is not None and value > limit:
            raise SettingError(
                f"{key!r} cannot be more than {limit}, so nothing was changed. Discord itself "
                f"refuses to delete more than {limit} days of a banned account's messages, and a "
                f"bigger number would make every ban fail."
            )
        return value
    if kind == "bool":
        if not isinstance(value, bool):
            raise SettingError(f"{key!r} takes true or false, not {value!r}.")
        return value
    if kind == "text":
        if not isinstance(value, str) or not value.strip():
            raise SettingError(f"{key!r} takes some text, not {value!r}.")
        return value
    if kind == "color":
        match = HEX_COLOR.match(str(value or "").strip()) if isinstance(value, str) else None
        if match is None:
            raise SettingError(
                f"{key!r} takes a hex colour like `#4eefff` — six digits 0-9 or a-f, with or "
                f"without the `#`, and nothing else. {value!r} is not one, so nothing was changed."
            )
        return f"#{match.group(1).lower()}"
    raise SettingError(f"{key!r} has no validator for type {kind!r}.")


def parse_value(key: str, raw: str) -> Any:
    """Turn one typed-in string into the value `coerce_value` expects."""
    kind = KEY_TYPES.get(key)
    text = raw.strip()
    if kind in ("int", "channel", "role"):
        digits = text.lstrip("<#@&").rstrip(">")
        if not digits.isdigit():
            raise SettingError(f"{key!r} takes a whole number, not {raw!r}.")
        return int(digits)
    if kind in ("channels", "roles"):
        parts = [p.strip().lstrip("<#@&").rstrip(">") for p in text.split(",") if p.strip()]
        if not all(p.isdigit() for p in parts):
            raise SettingError(f"{key!r} takes ids separated by commas, not {raw!r}.")
        return [int(p) for p in parts]
    if kind == "bool":
        if text.lower() in ("true", "yes", "on"):
            return True
        if text.lower() in ("false", "no", "off"):
            return False
        raise SettingError(f"{key!r} takes true or false, not {raw!r}.")
    return text


def display_value(key: str, value: Any) -> str:
    kind = KEY_TYPES.get(key)
    if kind in ("channels", "roles"):
        mark = "#" if kind == "channels" else "@&"
        return ", ".join(f"<{mark}{v}>" for v in value) if value else "not set"
    if value is None or value == "":
        return "not set"
    if kind == "channel":
        return f"<#{value}>"
    if kind == "role":
        return f"<@&{value}>"
    return str(value)


def resolved_staff_roles(guild: Any, channel: Any, perms_for: Any = None) -> list[Any]:
    """Roles whose computed permissions see the staff channel; @everyone never counts."""
    if channel is None:
        return []
    resolve = perms_for or getattr(channel, "permissions_for", None)
    if resolve is None:
        log.warning("staff roles: %s cannot say what a role may see", getattr(channel, "id", "?"))
        return []
    found: list[Any] = []
    for role in getattr(guild, "roles", ()):
        is_default = getattr(role, "is_default", None)
        if is_default is not None and is_default():
            continue
        bot_managed = getattr(role, "is_bot_managed", None)
        if bot_managed is not None and bot_managed():
            continue
        try:
            perms = resolve(role)
        except Exception as exc:
            log.warning(
                "staff roles: could not work out what %s can see: %s",
                getattr(role, "id", role),
                exc,
            )
            continue
        if getattr(perms, "view_channel", False):
            found.append(role)
    return found


def staff_roles_sentence(roles: Any) -> str:
    names = [f"**{getattr(role, 'name', role)}**" for role in roles]
    if not names:
        return "no roles at all"
    return f"{len(names)} role(s) — " + ", ".join(names)


def member_is_staff(member: Any, staff_ids: set[int]) -> bool:
    perms = getattr(member, "guild_permissions", None)
    if perms is not None and getattr(perms, "manage_guild", False):
        return True
    return any(getattr(r, "id", None) in staff_ids for r in getattr(member, "roles", ()))


async def require_staff(interaction: Any) -> bool:
    """True if the caller may run a staff command; otherwise answer them and return False."""
    if interaction.guild is None:
        await interaction.response.send_message(GUILD_ONLY, ephemeral=True)
        return False
    store = interaction.client.store
    if not store.is_staff(interaction.user):
        await interaction.response.send_message(
            store.staff_refusal(interaction.guild.id), ephemeral=True
        )
        return False
    return True


class SettingsStore:
    def __init__(self, db: Database, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self._cache: dict[tuple[int, str], Any] = {}

    def default(self, key: str) -> Any:
        if key == "staff_channel_id":
            return self.settings.test_channel_id
        if key == "log_channel_id":
            return self.settings.test_channel_id if self.settings.test_mode else None
        if key == "golive_channel_id":
            if self.settings.test_mode:
                return self.settings.test_channel_id
            return GOLIVE_CHANNEL_ID
        if key == "golive_mode":
            return "shadow"
        if key == "golive_template":
            return GOLIVE_TEMPLATE
        if key == "golive_cooldown_minutes":
            return 60
        if key == "golive_max_session_hours":
            return 12
        if key == "tempvoice_mode":
            return "on"
        if key == "tempvoice_name_template":
            return TEMPVOICE_NAME_TEMPLATE
        if key == "tempvoice_allowed_role_id":
            return MEMBER_ROLE_ID
        if key == "honeypot_mode":
            return "shadow"
        if key == "honeypot_purge_days":
            return 1
        if key == "birthday_mode":
            return "shadow"
        if key == "birthday_channel_id":
            if self.settings.test_mode:
                return self.settings.test_channel_id
            return BIRTHDAY_CHANNEL_ID
        if key == "birthday_template":
            return BIRTHDAY_TEMPLATE
        if key == "birthday_color":
            return BIRTHDAY_COLOR
        if key == "birthday_show_age":
            return False
        if KEY_TYPES.get(key) in ("channels", "roles"):
            return []
        return None

    async def load(self) -> None:
        cur = await self.db.conn.execute("SELECT guild_id, key, value FROM settings")
        self._cache = {
            (row["guild_id"], row["key"]): json.loads(row["value"]) for row in await cur.fetchall()
        }
        log.info("settings loaded: %d row(s)", len(self._cache))

    def get(self, guild_id: int, key: str) -> Any:
        if key not in KEY_TYPES:
            raise SettingError(f"{key!r} is not a Black Bloc setting.")
        return self._cache.get((guild_id, key), self.default(key))

    def all(self, guild_id: int) -> dict[str, Any]:
        return {key: self.get(guild_id, key) for key in KEY_TYPES}

    async def set(self, guild_id: int, key: str, value: Any, *, by: int | None = None) -> Any:
        stored = coerce_value(key, value)
        await self.db.conn.execute(
            "INSERT OR REPLACE INTO settings(guild_id, key, value, updated_by, updated_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (guild_id, key, json.dumps(stored), by, datetime.now(UTC).isoformat()),
        )
        await self.db.conn.commit()
        self._cache[(guild_id, key)] = stored
        return stored

    async def clear(self, guild_id: int, key: str, *, by: int | None = None) -> bool:
        """Forget one stored setting so its default applies again."""
        if key not in KEY_TYPES:
            raise SettingError(f"{key!r} is not a Black Bloc setting.")
        cur = await self.db.conn.execute(
            "DELETE FROM settings WHERE guild_id = ? AND key = ?", (guild_id, key)
        )
        await self.db.conn.commit()
        self._cache.pop((guild_id, key), None)
        cleared = bool(cur.rowcount)
        if cleared:
            log.info("settings cleared: %s for guild %s by %s", key, guild_id, by)
        return cleared

    def staff_roles(self, guild: Any) -> list[Any]:
        channel_id = self.get(guild.id, "staff_channel_id")
        channel = guild.get_channel(channel_id) if channel_id else None
        return resolved_staff_roles(guild, channel)

    def staff_role_ids(self, guild: Any) -> set[int]:
        return {role.id for role in self.staff_roles(guild)}

    def is_staff(self, member: Any) -> bool:
        guild = getattr(member, "guild", None)
        staff_ids = self.staff_role_ids(guild) if guild is not None else set()
        return member_is_staff(member, staff_ids)

    def staff_refusal(self, guild_id: int) -> str:
        channel_id = self.get(guild_id, "staff_channel_id")
        where = f"<#{channel_id}>" if channel_id else "the staff channel"
        return (
            "That command is for staff only, so nothing was changed. It needs either the "
            f"Manage Server permission or a role that can see {where}. Ask a server admin to "
            "give you one of those, or to run the command for you."
        )
