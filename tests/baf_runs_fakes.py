import json

from black_bloc.config import load_settings
from black_bloc.marathon_sources import Person, Run
from black_bloc.settings_store import SettingsStore

GUILD = 7
RUNNER_ID = 111111111111111111
HOST_ID = 222222222222222222
OTHER_ID = 333333333333333333
AT = "2026-10-01T00:00:00+00:00"


class FakeMember:
    def __init__(self, user_id, name, display=None):
        self.id = user_id
        self.name = name
        self.display_name = display or name
        self.bot = False
        self.roles = []


class FakeGuild:
    def __init__(self):
        self.id = GUILD
        self.name = "Black Bloc"
        self.unavailable = False
        self.members = [
            FakeMember(RUNNER_ID, "kaizo_kat", "Kat"),
            FakeMember(HOST_ID, "hostess", "Hostess"),
            FakeMember(OTHER_ID, "pt", "PT"),
        ]
        self.roles = []

    def get_member(self, user_id):
        return next((one for one in self.members if one.id == int(user_id)), None)

    def get_role(self, role_id):
        return None


class FakeSettings:
    origin = "https://blackbloc.example"


class FakeBot:
    def __init__(self, db, store, guild):
        self.db = db
        self.store = store
        self.guild = guild
        self.guilds = [guild]
        self.settings = FakeSettings()
        self.guard = None

    def get_cog(self, name):
        return None


async def make_bot(db, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    settings = load_settings(_env_file=None, test_mode=False)
    store = SettingsStore(db, settings)
    await store.load()
    return FakeBot(db, store, FakeGuild())


def person(name, part="runner", user_id=None):
    return {"name": name, "login": None, "part": part, "user_id": user_id}


async def add_marathon(db, name, source="gdq", ref="50", *, archived=False, mid=None):
    table = "marathons_archive" if archived else "marathons"
    extra = ", archived_at, archived_why" if archived else ""
    marks = ", ?, ?" if archived else ""
    values = (AT, "over") if archived else ()
    cur = await db.conn.execute(
        f"INSERT INTO {table}(id, guild_id, name, schedule_url, source, source_ref, added_at"
        f"{extra}) VALUES (?, ?, ?, ?, ?, ?, ?{marks})",
        (mid, GUILD, name, f"https://x/{name}", source, ref, AT, *values),
    )
    await db.conn.commit()
    return cur.lastrowid


async def add_run(
    db,
    marathon_id,
    external_id,
    game,
    people,
    *,
    state="done",
    at="2026-10-02T18:00:00+00:00",
    category="Any%",
    archived=False,
    rid=None,
):
    table = "marathon_runs_archive" if archived else "marathon_runs"
    cur = await db.conn.execute(
        f"INSERT INTO {table}(id, marathon_id, external_id, game, category, people, state, "
        "scheduled_at, actual_started_at, first_seen_at, last_seen_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            rid,
            marathon_id,
            str(external_id),
            game,
            category,
            json.dumps(people),
            state,
            at,
            at,
            AT,
            AT,
        ),
    )
    await db.conn.commit()
    return cur.lastrowid


async def count(db, table):
    cur = await db.conn.execute(f"SELECT count(*) AS n FROM {table}")
    return (await cur.fetchone())["n"]


async def kinds(db):
    cur = await db.conn.execute("SELECT kind FROM action_log ORDER BY id")
    return [row["kind"] for row in await cur.fetchall()]


class FakeClient:
    def __init__(self, runs, event=("50", "SGDQ 2025")):
        self._runs = runs
        self.event = event
        self.closed = False
        self.reads = 0

    async def resolve(self, source, ref):
        return self.event

    async def runs(self, source, ref, **kwargs):
        self.reads += 1
        return list(self._runs)

    async def close(self):
        self.closed = True


def tracker_run(external_id, game, names, *, at="2025-07-01T18:00:00+00:00", host=None):
    people = tuple(Person(name, None, "runner") for name in names)
    if host:
        people += (Person(host, None, "host"),)
    return Run(
        external_id=str(external_id),
        order=None,
        game=game,
        display_name=game,
        category="Any%",
        starts_at=at,
        ends_at=None,
        run_seconds=None,
        people=people,
    )
