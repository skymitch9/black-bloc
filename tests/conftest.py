import asyncio
import os
import secrets
import sqlite3
import sys
import time
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any

import pytest
import pytest_asyncio

from black_bloc.api.auth import SESSION_COOKIE, SESSION_TTL_SECONDS, sign_session
from black_bloc.api.server import SAME_ORIGIN, SAME_SITE_HEADER
from black_bloc.bot import COGS
from black_bloc.config import Settings, load_settings
from black_bloc.settings_store import member_is_staff
from black_bloc.storage.db import Database

REVERSE = "BB_REVERSE"
SHELL_NAMES = {"DEV_GUILD_ID", "TEST_MODE", "TEST_CHANNEL_ID"}


def settings_names_in(environ) -> list[str]:
    """Every name Settings would read, plus the operator shell's own BLACK_BLOC_* names."""
    declared = {name.upper() for name in Settings.model_fields} | SHELL_NAMES
    return [n for n in environ if n.upper() in declared or n.upper().startswith("BLACK_BLOC_")]


@pytest.fixture(scope="session", autouse=True)
def the_shell_environment_never_reaches_a_test():
    """The suite answers the same with or without the operator's keys in the shell or a `.env`."""
    kept = {name: os.environ.pop(name) for name in settings_names_in(os.environ)}
    env_file = Settings.model_config.get("env_file")
    Settings.model_config["env_file"] = None
    try:
        yield
    finally:
        Settings.model_config["env_file"] = env_file
        os.environ.update(kept)


def pytest_collection_modifyitems(items):
    """`BB_REVERSE=1` runs everything backwards — the guard on the module-scoped fixtures."""
    if os.environ.get(REVERSE) == "1":
        items.reverse()


@pytest.fixture(scope="session")
def cog_modules_as_collected():
    return {name: sys.modules[name] for name in COGS if name in sys.modules}


@pytest.fixture(autouse=True)
def cog_modules_stay_the_ones_the_test_files_imported(cog_modules_as_collected):
    """`load_extension` builds a NEW module object and hangs it in `sys.modules`, so after any
    test that loads a cog, `monkeypatch.setattr("black_bloc.cogs.x.y", ...)` patches a module the
    test file's own imports no longer point at."""
    yield
    sys.modules.update(cog_modules_as_collected)


@pytest.fixture(autouse=True)
def no_test_ever_opens_a_link(monkeypatch):
    """`link_answers` falls back to a real GET, so the suite takes that fallback away."""

    async def refuse(url, *, seconds, headers):
        raise AssertionError(f"a test asked the network for {url}; inject `fetch` instead")

    monkeypatch.setattr("black_bloc.linkcheck.aiohttp_status", refuse)


@pytest.fixture
def settings(tmp_path):
    return load_settings(_env_file=None, database_path=tmp_path / "test.sqlite3")


async def schema_of(db: Any) -> dict[str, tuple[str, str | None]]:
    """Every table, index, view and trigger the database holds right now, in creation order."""
    cur = await db.conn.execute("SELECT type, name, sql FROM sqlite_master ORDER BY rowid")
    return {row["name"]: (row["type"], row["sql"]) for row in await cur.fetchall()}


async def take(db: Any) -> dict[str, Any]:
    """Every row of every table AND the schema holding them, so a database can be put back
    without rebuilding schema v32."""
    schema = await schema_of(db)
    rows: dict[str, list[tuple]] = {}
    for name, (kind, _sql) in schema.items():
        if kind != "table":
            continue
        cur = await db.conn.execute(f"SELECT * FROM {name}")
        rows[name] = [tuple(row) for row in await cur.fetchall()]
    return {"schema": schema, "rows": rows}


async def _put_schema_back(db: Any, wanted: dict, found: dict) -> None:
    for name, (kind, sql) in found.items():
        if name in wanted or sql is None or name.startswith("sqlite_"):
            continue
        await db.conn.execute(f"DROP {kind.upper()} IF EXISTS {name}")
    for name, (_kind, sql) in wanted.items():
        if name not in found and sql is not None and not name.startswith("sqlite_"):
            await db.conn.execute(sql)


async def put(db: Any, snapshot: dict[str, Any]) -> None:
    """The other half: emptied and refilled on the live connection, which a page copy cannot do.
    A test that dropped an index or made a table of its own has both put back first."""
    await db.conn.commit()
    await db.conn.execute("PRAGMA foreign_keys=OFF")
    found = await schema_of(db)
    rows = snapshot["rows"]
    for name in rows:
        if name in found:
            await db.conn.execute(f"DELETE FROM {name}")
    if set(found) != set(snapshot["schema"]):
        await _put_schema_back(db, snapshot["schema"], found)
    for name, kept in rows.items():
        if kept:
            marks = ", ".join("?" * len(kept[0]))
            await db.conn.executemany(f"INSERT INTO {name} VALUES ({marks})", kept)
    await db.conn.commit()
    await db.conn.execute("PRAGMA foreign_keys=ON")


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def module_db(tmp_path_factory):
    database = Database(tmp_path_factory.mktemp("db") / "test.sqlite3")
    await database.connect()
    try:
        yield database
    finally:
        if worker_is_alive(database):
            await database.close()


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def module_db_blank(module_db):
    """What a freshly connected database holds, so a test is handed that instead of building it."""
    return await take(module_db)


def worker_is_alive(database: Any) -> bool:
    if not database.is_connected:
        return True
    thread = getattr(database.conn, "_thread", None)
    return thread is None or thread.is_alive()


async def settle(database: Any) -> None:
    """Every task the test left running ends, then every query already queued is answered,
    all while this test's loop is still open."""
    here = asyncio.current_task()
    left = [task for task in asyncio.all_tasks() if task is not here and not task.done()]
    for task in left:
        task.cancel()
    await asyncio.gather(*left, return_exceptions=True)
    if database.is_connected and worker_is_alive(database):
        await (await database.conn.execute("SELECT 1")).close()


@pytest.fixture
async def db(module_db, module_db_blank):
    """The module's one schema-v32 database, rewound to what a per-test one would have handed over.
    Reconnected first when the test before it closed the database on purpose."""
    if not module_db.is_connected:
        await module_db.connect()
    if not worker_is_alive(module_db):
        pytest.fail("the module database's aiosqlite thread died: docs/info/ci-linux-hang.md")
    await put(module_db, module_db_blank)
    yield module_db
    await settle(module_db)


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
def api_settings():
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
