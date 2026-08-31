import secrets
import sqlite3
import time
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any

import pytest

from black_bloc.api.auth import SESSION_COOKIE, SESSION_TTL_SECONDS, sign_session
from black_bloc.api.server import SAME_ORIGIN, SAME_SITE_HEADER
from black_bloc.config import load_settings
from black_bloc.settings_store import member_is_staff


@pytest.fixture
def settings(tmp_path, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    return load_settings(_env_file=None, database_path=tmp_path / "test.sqlite3")


# At least SESSION_SECRET_MIN characters, or site_login_configured stays False
# and every sign-in route answers login_unavailable.
API_SECRET = "test-session-secret-long-enough-to-sign"
# https, because a __Host- cookie needs Secure and http.cookiejar refuses to
# return a Secure cookie over http — the tests would never carry a session.
API_ORIGIN = "https://testserver"
SAME_SITE = {SAME_SITE_HEADER: SAME_ORIGIN}
API_GUILD_ID = 4242
STAFF_ROLE_ID = 11
PLAIN_ROLE_ID = 22
ADMIN_ROLE_ID = 33


class FakePermissions:
    def __init__(self, *, manage_guild: bool = False) -> None:
        self.manage_guild = manage_guild


class FakeRole:
    def __init__(self, role_id: int, name: str, *, manage_guild: bool = False) -> None:
        self.id = role_id
        self.name = name
        self.permissions = FakePermissions(manage_guild=manage_guild)


class FakeMember:
    def __init__(self, user_id: int, roles: list, *, manage_guild: bool = False) -> None:
        self.id = user_id
        self.roles = roles
        self.guild_permissions = FakePermissions(manage_guild=manage_guild)


class FakeGuild:
    def __init__(self) -> None:
        self.id = API_GUILD_ID
        self.name = "Black in a Flash!"
        self.owner_id = 999
        self.roles = [
            FakeRole(STAFF_ROLE_ID, "Aunties / Uncles"),
            FakeRole(PLAIN_ROLE_ID, "Member"),
            FakeRole(ADMIN_ROLE_ID, "Admin", manage_guild=True),
        ]
        self.members: dict[int, FakeMember] = {}

    def get_member(self, user_id: int):
        return self.members.get(user_id)

    def get_role(self, role_id: int):
        return next((r for r in self.roles if r.id == role_id), None)


class FakeStore:
    """The staff question answered the one way settings_store answers it."""

    def __init__(self, staff_ids: set[int]) -> None:
        self.staff_ids = staff_ids
        self.values: dict[str, Any] = {}

    def staff_role_ids(self, guild: Any) -> set[int]:
        return set(self.staff_ids)

    def is_staff(self, member: Any) -> bool:
        return member_is_staff(member, self.staff_role_ids(getattr(member, "guild", None)))

    def get(self, guild_id: int, key: str) -> Any:
        return self.values.get(key)


class FakeDatabase:
    def __init__(self, conn: Any = None) -> None:
        self._conn = conn

    @property
    def is_connected(self) -> bool:
        return self._conn is not None

    @property
    def conn(self) -> Any:
        return self._conn


class FakeBot:
    def __init__(self, api_settings: Any, guild: Any) -> None:
        self.settings = api_settings
        self.store = FakeStore({STAFF_ROLE_ID})
        self.guild = guild
        self.guilds = [guild] if guild is not None else []
        self.cogs: dict[str, Any] = {}
        self.db = FakeDatabase()
        self.latency = 0.042
        self.started_at = datetime.now(UTC)

    def is_ready(self) -> bool:
        return True

    def get_guild(self, guild_id: int):
        if self.guild is not None and self.guild.id == guild_id:
            return self.guild
        return None


@pytest.fixture
def api_settings(monkeypatch):
    for name in ("DISCORD_TOKEN", "DISCORD_CLIENT_ID", "DISCORD_CLIENT_SECRET", "SESSION_SECRET"):
        monkeypatch.delenv(name, raising=False)
    return load_settings(
        _env_file=None,
        dev_guild_id=API_GUILD_ID,
        discord_client_id="client-id",
        discord_client_secret="client-secret",
        session_secret=API_SECRET,
        site_origin=API_ORIGIN,
    )


@pytest.fixture
def fakes():
    """The api fakes as a fixture, because a conftest is not importable by name."""
    return SimpleNamespace(
        Member=FakeMember,
        Role=FakeRole,
        Guild=FakeGuild,
        Bot=FakeBot,
        Database=FakeDatabase,
        SECRET=API_SECRET,
        ORIGIN=API_ORIGIN,
        SAME_SITE=SAME_SITE,
        GUILD_ID=API_GUILD_ID,
        STAFF_ROLE_ID=STAFF_ROLE_ID,
        PLAIN_ROLE_ID=PLAIN_ROLE_ID,
        ADMIN_ROLE_ID=ADMIN_ROLE_ID,
    )


@pytest.fixture
def guild():
    return FakeGuild()


@pytest.fixture
def bot(api_settings, guild):
    return FakeBot(api_settings, guild)


def record_session(client, sid: str, user_id: int, ttl: int) -> None:
    """The row the callback writes, from a sync fixture: plain sqlite3 on the same file."""
    db = getattr(getattr(getattr(client, "app", None), "state", None), "bot", None)
    db = getattr(db, "db", None)
    if db is None or not db.is_connected:
        return
    at = datetime.now(UTC)
    conn = sqlite3.connect(db.path)
    try:
        conn.execute(
            "INSERT OR REPLACE INTO sessions(id, user_id, created_at, expires_at) "
            "VALUES (?, ?, ?, ?)",
            (sid, int(user_id), at.isoformat(), (at + timedelta(seconds=ttl)).isoformat()),
        )
        conn.commit()
    finally:
        conn.close()


@pytest.fixture
def sign_in(guild):
    """Sign somebody in AND let the bot's guild cache see them — staff is re-read live."""

    def _sign_in(
        client,
        *,
        uid: int = 7,
        staff: bool = True,
        ttl: int = SESSION_TTL_SECONDS,
        cached: bool = True,
        sid: str | None = None,
    ):
        if cached:
            role = FakeRole(STAFF_ROLE_ID, "Aunties / Uncles") if staff else FakeRole(
                PLAIN_ROLE_ID, "Member"
            )
            guild.members.setdefault(uid, FakeMember(uid, [role]))
        session_id = sid or f"test-{uid}-{secrets.token_hex(4)}"
        record_session(client, session_id, uid, ttl)
        token = sign_session(
            API_SECRET,
            {
                "uid": str(uid),
                "name": "Mod",
                "avatar": None,
                "staff": staff,
                "sid": session_id,
                "exp": int(time.time()) + ttl,
            },
        )
        client.cookies.set(SESSION_COOKIE, token)
        return token

    return _sign_in
