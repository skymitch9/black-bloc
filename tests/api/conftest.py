from __future__ import annotations

import json
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

from black_bloc.api.server import SAME_ORIGIN, SAME_SITE_HEADER, create_app
from black_bloc.config import load_settings
from black_bloc.logkinds import VIA_DISCORD, VIA_WEBSITE
from black_bloc.settings_store import SettingsStore
from black_bloc.storage.db import Database
from tests.conftest import put, take

SECRET = "test-session-secret-long-enough-to-sign"
ORIGIN = "https://testserver"
SAME_SITE = {SAME_SITE_HEADER: SAME_ORIGIN}
GUILD_ID = 4242
STAFF_ROLE_ID = 11
PLAIN_ROLE_ID = 22
ADMIN_ROLE_ID = 33
TEST_CHANNEL_ID = 500
OTHER_CHANNEL_ID = 501
CATEGORY_ID = 490
VOICE_CHANNEL_ID = 502
BASELINE = "_test_baseline"


class Permissions:
    def __init__(self, *, manage_guild: bool = False, view_channel: bool = False) -> None:
        self.manage_guild = manage_guild
        self.view_channel = view_channel


class WebRole:
    def __init__(
        self,
        role_id: int,
        name: str,
        *,
        manage_guild: bool = False,
        position: int = 0,
        managed: bool = False,
        color: int = 0,
    ) -> None:
        self.id = role_id
        self.name = name
        self.position = position
        self.managed = managed
        self.color = color
        self.permissions = Permissions(manage_guild=manage_guild)
        self.members: list = []
        self.deleted = False

    def is_assignable(self) -> bool:
        return not self.managed

    async def delete(self, reason: str | None = None) -> None:
        self.deleted = True


class WebMember:
    def __init__(
        self, user_id: int, roles: list, *, name: str = "", manage_guild: bool = False
    ) -> None:
        self.id = user_id
        self.name = name or f"user{user_id}"
        self.display_name = self.name.title()
        self.roles = roles
        self.guild: Any = None
        self.guild_permissions = Permissions(manage_guild=manage_guild)
        self.display_avatar = SimpleNamespace(url=f"https://cdn.test/{user_id}.png")
        self.dms: list[str] = []
        self.timeouts: list[Any] = []
        self.edits: list[list[int]] = []
        self.edit_raises: Any = None

    async def send(self, content=None, **kwargs) -> None:
        self.dms.append(content)

    async def edit(self, roles=None, reason=None) -> None:
        if self.edit_raises is not None:
            raise self.edit_raises
        self.edits.append([role.id for role in roles])
        self.roles = list(roles)

    async def timeout(self, until, reason=None) -> None:
        self.timeouts.append((until, reason))

    async def add_roles(self, *roles, reason=None) -> None:
        self.roles += [role for role in roles if role not in self.roles]
        for role in roles:
            role.members.append(self)

    async def remove_roles(self, *roles, reason=None) -> None:
        self.roles = [role for role in self.roles if role not in roles]
        for role in roles:
            role.members = [one for one in role.members if one is not self]


class WebMessage:
    def __init__(self, message_id: int, channel: Any, **kwargs: Any) -> None:
        self.id = message_id
        self.channel = channel
        self.kwargs = kwargs
        self.content = kwargs.get("content")
        self.jump_url = f"https://discord.test/{message_id}"
        self.pinned = False

    async def edit(self, **kwargs: Any) -> None:
        self.kwargs |= kwargs

    async def pin(self, reason: str | None = None) -> None:
        self.pinned = True

    async def unpin(self, reason: str | None = None) -> None:
        self.pinned = False

    async def delete(self) -> None:
        self.channel.messages = [m for m in self.channel.messages if m.id != self.id]


class WebChannel:
    def __init__(
        self,
        channel_id: int,
        name: str,
        *,
        kind: str = "text",
        position: int = 0,
        category_id: int | None = None,
        viewers: set[int] | None = None,
    ) -> None:
        self.id = channel_id
        self.name = name
        self.type = SimpleNamespace(name=kind)
        self.position = position
        self.category_id = category_id
        self.category: Any = None
        self.viewers = viewers if viewers is not None else set()
        self.messages: list[WebMessage] = []
        self.mention = f"<#{channel_id}>"
        self.deleted = False
        self.user_limit = 0
        self.guild: Any = None
        self.voice_states: dict[int, Any] = {}
        self.overwrites: dict[Any, Any] = {}
        self.edit_raises: Any = None

    def permissions_for(self, role: Any) -> Permissions:
        return Permissions(view_channel=getattr(role, "id", None) in self.viewers)

    def overwrites_for(self, target: Any) -> Any:
        found = self.overwrites.get(target)
        if found is None:
            found = SimpleNamespace(connect=None, view_channel=None)
        return SimpleNamespace(**vars(found))

    async def set_permissions(self, target: Any, overwrite: Any = None, reason: str = "") -> None:
        if self.edit_raises is not None:
            raise self.edit_raises
        if overwrite is None:
            self.overwrites.pop(target, None)
        else:
            self.overwrites[target] = overwrite

    async def send(self, content=None, **kwargs: Any) -> WebMessage:
        message = WebMessage(9000 + len(self.messages), self, content=content, **kwargs)
        self.messages.append(message)
        return message

    async def delete(self, reason: str | None = None) -> None:
        self.deleted = True

    async def delete_messages(self, messages: Any) -> None:
        wanted = {getattr(one, "id", one) for one in messages}
        self.messages = [m for m in self.messages if m.id not in wanted]

    async def edit(self, **kwargs: Any) -> None:
        if self.edit_raises is not None:
            raise self.edit_raises
        self.edits = getattr(self, "edits", []) + [kwargs]
        for field in ("name", "user_limit"):
            if field in kwargs:
                setattr(self, field, kwargs[field])

    async def fetch_message(self, message_id: int) -> WebMessage:
        found = next((m for m in self.messages if m.id == message_id), None)
        if found is None:
            raise LookupError(message_id)
        return found


class MemberBook(dict):
    """A dict for the shared sign-in fixture, a list of members for the resolver."""

    def __iter__(self):
        return iter(self.values())


class WebGuild:
    def __init__(self) -> None:
        self.id = GUILD_ID
        self.name = "Black in a Flash!"
        self.owner_id = 999
        self.roles = [
            WebRole(STAFF_ROLE_ID, "Aunties / Uncles", position=5, color=0x4EEFFF),
            WebRole(PLAIN_ROLE_ID, "Member", position=2),
            WebRole(ADMIN_ROLE_ID, "Admin", manage_guild=True, position=9),
        ]
        category = WebChannel(CATEGORY_ID, "staff", kind="category", position=0)
        self.channels = [
            category,
            WebChannel(
                TEST_CHANNEL_ID,
                "blackbloc-logs",
                position=1,
                category_id=CATEGORY_ID,
                viewers={STAFF_ROLE_ID},
            ),
            WebChannel(OTHER_CHANNEL_ID, "general", position=2),
            WebChannel(VOICE_CHANNEL_ID, "voice", kind="voice", position=3),
        ]
        for channel in self.channels:
            channel.category = category if channel.category_id == CATEGORY_ID else None
            channel.guild = self
        self.members = MemberBook()
        self.bans: list[Any] = []
        self.kicks: list[Any] = []
        self.unbans: list[Any] = []
        self.created: list[Any] = []
        self.made_roles: list[Any] = []
        self.default_role = WebRole(GUILD_ID, "@everyone")

    async def create_role(self, name=None, mentionable=False, reason=None):
        role = WebRole(950 + len(self.made_roles), name, position=1)
        self.roles.append(role)
        self.made_roles.append(role)
        return role

    def add_member(self, member: WebMember) -> WebMember:
        member.guild = self
        self.members[member.id] = member
        return member

    def get_member(self, user_id: int):
        found = self.members.get(int(user_id))
        if found is not None and getattr(found, "guild", None) is None:
            found.guild = self
        return found

    def get_role(self, role_id: int):
        return next((r for r in self.roles if r.id == int(role_id)), None)

    def get_channel(self, channel_id: int):
        return next((c for c in self.channels if c.id == int(channel_id)), None)

    @property
    def text_channels(self):
        return [c for c in self.channels if c.type.name == "text"]

    @property
    def voice_channels(self):
        return [c for c in self.channels if c.type.name == "voice"]

    async def ban(self, user, reason=None, delete_message_seconds=0) -> None:
        self.bans.append((getattr(user, "id", user), reason, delete_message_seconds))

    async def kick(self, user, reason=None) -> None:
        self.kicks.append((getattr(user, "id", user), reason))

    async def unban(self, user, reason=None) -> None:
        self.unbans.append((getattr(user, "id", user), reason))

    async def create_text_channel(self, name, **kwargs):
        channel = WebChannel(700 + len(self.created), name, position=len(self.channels))
        channel.kwargs = kwargs
        channel.guild = self
        self.channels.append(channel)
        self.created.append(channel)
        return channel

    async def create_voice_channel(self, name, **kwargs):
        channel = WebChannel(
            750 + len(self.created), name, kind="voice", position=len(self.channels)
        )
        channel.kwargs = kwargs
        channel.guild = self
        self.channels.append(channel)
        self.created.append(channel)
        return channel

    async def create_forum(self, name, **kwargs):
        channel = WebChannel(
            780 + len(self.created), name, kind="forum", position=len(self.channels)
        )
        channel.kwargs = kwargs
        channel.available_tags = list(kwargs.get("available_tags") or ())
        channel.guild = self
        self.channels.append(channel)
        self.created.append(channel)
        return channel


class WebGuard:
    """The real guard's answers without patching an HTTP client."""

    def __init__(self, test_channel_id: int = TEST_CHANNEL_ID) -> None:
        self.test_channel_id = test_channel_id
        self.owned: set[int] = set()

    def own_channel(self, channel: Any) -> None:
        self.owned.add(int(getattr(channel, "id", channel)))

    def disown_channel(self, channel: Any) -> None:
        self.owned.discard(int(getattr(channel, "id", channel)))

    def owns_channel(self, channel: Any) -> bool:
        return int(getattr(channel, "id", channel)) in self.owned

    def allows_channel(self, channel: Any) -> bool:
        found = int(getattr(channel, "id", channel))
        return found == self.test_channel_id or found in self.owned

    def allows_place(self, channel: Any) -> bool:
        here = int(getattr(channel, "id", channel))
        return here == self.test_channel_id or getattr(channel, "category_id", None) == CATEGORY_ID

    def refusal_message(self) -> str:
        return (
            "Black Bloc is in **test mode** — commands only work in "
            f"<#{self.test_channel_id}> or by DM for now."
        )


class WebBot:
    def __init__(self, settings: Any, guild: Any, db: Any, store: Any) -> None:
        self.settings = settings
        self.guild = guild
        self.guilds = [guild] if guild is not None else []
        self.db = db
        self.store = store
        self.cogs: dict[str, Any] = {}
        self.guard: Any = None
        self.latency = 0.042
        self.started_at = datetime.now(UTC)
        self.views: list[Any] = []
        self.user = SimpleNamespace(id=1)

    def is_ready(self) -> bool:
        return True

    def get_guild(self, guild_id: int):
        if self.guild is not None and self.guild.id == guild_id:
            return self.guild
        return None

    def get_channel(self, channel_id: int):
        return self.guild.get_channel(channel_id) if self.guild is not None else None

    def get_user(self, user_id: int):
        return self.guild.get_member(user_id) if self.guild is not None else None

    def get_cog(self, name: str):
        return self.cogs.get(name)

    def add_view(self, view: Any, message_id: int | None = None) -> None:
        self.views.append((view, message_id))


def web_settings_now():
    with pytest.MonkeyPatch.context() as patch:
        for name in (
            "DISCORD_TOKEN",
            "DISCORD_CLIENT_ID",
            "DISCORD_CLIENT_SECRET",
            "SESSION_SECRET",
        ):
            patch.delenv(name, raising=False)
        return load_settings(
            _env_file=None,
            dev_guild_id=GUILD_ID,
            discord_client_id="client-id",
            discord_client_secret="client-secret",
            session_secret=SECRET,
            site_origin=ORIGIN,
            test_mode=False,
            test_channel_id=TEST_CHANNEL_ID,
        )


@pytest.fixture
def web_settings():
    return web_settings_now()


@pytest.fixture
async def fresh_web_db(tmp_path):
    database = Database(tmp_path / "web.sqlite3")
    await database.connect()
    try:
        yield database
    finally:
        await database.close()


@pytest.fixture
async def fresh_web(web_settings, guild, fresh_web_db):
    """A bot of its own, for the handful of entries that must not share a module's app."""
    store = SettingsStore(fresh_web_db, web_settings)
    await store.load()
    return WebBot(web_settings, guild, fresh_web_db, store)


@pytest.fixture
def fresh_client(fresh_web):
    return TestClient(create_app(fresh_web), base_url=ORIGIN, headers=SAME_SITE)


@pytest.fixture(scope="module")
def module_guild():
    return WebGuild()


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def module_web(module_guild, tmp_path_factory):
    settings = web_settings_now()
    database = Database(tmp_path_factory.mktemp("web") / "web.sqlite3")
    await database.connect()
    store = SettingsStore(database, settings)
    await store.load()
    bot = WebBot(settings, module_guild, database, store)
    bot.__dict__[BASELINE] = dict(bot.__dict__)
    try:
        yield bot
    finally:
        await database.close()


@pytest.fixture(scope="module")
def module_client(module_web):
    return TestClient(create_app(module_web), base_url=ORIGIN, headers=SAME_SITE)


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def module_blank(module_web):
    """What a freshly connected database holds, so a test is handed that instead of building it."""
    return await take(module_web.db)


def reset_bot(bot: Any, guild: Any) -> None:
    """The attributes a per-test bot was built with, back again. Everything a test hung on the
    shared one goes with them: a swapped `db`, an installed guard, a cog, and the four rate-limit
    buckets, which the api hangs off the bot by name. Settings are rebuilt rather than restored —
    tests write a token or an api key straight onto that object, so putting the same one back
    hands the next test the write."""
    base = bot.__dict__[BASELINE]
    bot.__dict__.clear()
    bot.__dict__.update(base)
    bot.__dict__[BASELINE] = base
    bot.guild = guild
    bot.guilds = [guild] if guild is not None else []
    bot.cogs = {}
    bot.views = []
    bot.settings = bot.store.settings = web_settings_now()


async def rewind(bot: Any, blank: Any, guild: Any) -> None:
    reset_bot(bot, guild)
    await put(bot.db, blank)
    await bot.store.load()


@pytest.fixture
def guild():
    """Overrides the shared fake so every api test has channels, roles and members."""
    return WebGuild()


@pytest.fixture
async def web(module_web, module_blank, guild):
    """The module's one app and database, rewound to what a per-test one would have handed over."""
    await rewind(module_web, module_blank, guild)
    return module_web


@pytest.fixture
def web_db(web):
    return web.db


@pytest.fixture
def client(module_client, web):
    """The header a browser sends from the dashboard's own page; without it every write is 403."""
    module_client.cookies.clear()
    return module_client


def member(guild: Any, user_id: int, *, name: str = "", staff: bool = False) -> WebMember:
    roles = [guild.get_role(STAFF_ROLE_ID if staff else PLAIN_ROLE_ID)]
    return guild.add_member(WebMember(user_id, roles, name=name))


async def kinds_in(db: Any) -> list[str]:
    cur = await db.conn.execute("SELECT kind FROM action_log ORDER BY id")
    return [row["kind"] for row in await cur.fetchall()]


async def web_rows_in(db: Any) -> list[tuple[str, dict]]:
    """The `web.*` lines with their details, so a test can count one row per dashboard write."""
    cur = await db.conn.execute(
        "SELECT kind, details FROM action_log WHERE kind LIKE 'web.%' ORDER BY id"
    )
    return [(row["kind"], json.loads(row["details"] or "{}")) for row in await cur.fetchall()]


async def one_web_row(db: Any, kind: str) -> dict:
    """Exactly one `web.*` row of this kind and no other — the double-post guard, per route."""
    rows = await web_rows_in(db)
    assert [found for found, _ in rows] == [kind], rows
    details = rows[0][1]
    assert details.get("via") == VIA_WEBSITE, details
    return details


@pytest.fixture(scope="session")
def wf():
    """The api fakes as a fixture, because a conftest is not importable by name."""
    return SimpleNamespace(
        Bot=WebBot,
        Channel=WebChannel,
        Guard=WebGuard,
        Guild=WebGuild,
        Member=WebMember,
        Role=WebRole,
        member=member,
        reset_bot=reset_bot,
        take=take,
        put=put,
        kinds_in=kinds_in,
        web_rows_in=web_rows_in,
        one_web_row=one_web_row,
        VIA_DISCORD=VIA_DISCORD,
        VIA_WEBSITE=VIA_WEBSITE,
        SECRET=SECRET,
        ORIGIN=ORIGIN,
        SAME_SITE=SAME_SITE,
        GUILD_ID=GUILD_ID,
        STAFF_ROLE_ID=STAFF_ROLE_ID,
        PLAIN_ROLE_ID=PLAIN_ROLE_ID,
        ADMIN_ROLE_ID=ADMIN_ROLE_ID,
        TEST_CHANNEL_ID=TEST_CHANNEL_ID,
        OTHER_CHANNEL_ID=OTHER_CHANNEL_ID,
        VOICE_CHANNEL_ID=VOICE_CHANNEL_ID,
        CATEGORY_ID=CATEGORY_ID,
    )
