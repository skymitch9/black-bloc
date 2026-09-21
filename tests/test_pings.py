import json
from datetime import UTC, datetime, timedelta

import pytest

from black_bloc import pings
from black_bloc.cogs.community.role_menus import get_menu, get_options, list_menus
from black_bloc.config import load_settings
from black_bloc.settings_store import SettingsStore

GUILD = 7
LOG_CHANNEL = 222
STREAMER = 900
FAN = 901
STAFF = 5


class FakeRole:
    def __init__(self, role_id, name, assignable=True):
        self.id = role_id
        self.name = name
        self.members = []
        self.deleted = False
        self.guild = None
        self._assignable = assignable

    def is_assignable(self):
        return self._assignable

    async def delete(self, reason=None):
        """Discord takes a deleted role off the guild, so the fake has to as well."""
        self.deleted = True
        if self.guild is not None:
            self.guild.roles = [role for role in self.guild.roles if role is not self]


class FakeMember:
    def __init__(self, guild, user_id, display_name="Alice", roles=()):
        self.id = user_id
        self.guild = guild
        self.display_name = display_name
        self.name = display_name
        self.bot = False
        self.roles = list(roles)
        self.refuse = None
        guild.members[user_id] = self

    async def add_roles(self, *roles, reason=None):
        if self.refuse is not None:
            raise self.refuse
        self.roles += [role for role in roles if role not in self.roles]

    async def remove_roles(self, *roles, reason=None):
        if self.refuse is not None:
            raise self.refuse
        self.roles = [role for role in self.roles if role not in roles]


class FakeMessage:
    def __init__(self, message_id, channel, **kwargs):
        self.id = message_id
        self.channel = channel
        self.kwargs = kwargs
        self.edits = []

    async def edit(self, **kwargs):
        self.edits.append(kwargs)
        self.kwargs |= kwargs


class FakeChannel:
    def __init__(self, channel_id=LOG_CHANNEL):
        self.id = channel_id
        self.messages = []

    async def send(self, content=None, **kwargs):
        message = FakeMessage(9000 + len(self.messages), self, content=content, **kwargs)
        self.messages.append(message)
        return message

    async def fetch_message(self, message_id):
        found = next((m for m in self.messages if m.id == message_id), None)
        if found is None:
            raise LookupError(message_id)
        return found


class FakeGuild:
    def __init__(self):
        self.id = GUILD
        self.roles = []
        self.members = {}
        self.made = []
        self.refuse_create = None
        self.channel = FakeChannel()

    def get_role(self, role_id):
        return next((role for role in self.roles if role.id == int(role_id)), None)

    def get_member(self, user_id):
        return self.members.get(int(user_id))

    def get_channel(self, channel_id):
        return self.channel if channel_id == self.channel.id else None

    def add_role(self, role):
        role.guild = self
        self.roles.append(role)
        return role

    async def create_role(self, name=None, mentionable=False, reason=None):
        if self.refuse_create is not None:
            raise self.refuse_create
        role = FakeRole(1000 + len(self.roles), name)
        self.made.append((name, mentionable, reason))
        return self.add_role(role)


class FakeBot:
    def __init__(self, db, store, settings, guild):
        self.db = db
        self.store = store
        self.settings = settings
        self.guild = guild
        self.guilds = [guild]
        self.guard = None
        self.views = []

    def add_view(self, view, message_id=None):
        self.views.append((view, message_id))

    def get_channel(self, channel_id):
        return self.guild.get_channel(channel_id)

    def get_guild(self, guild_id):
        return self.guild if self.guild.id == guild_id else None


@pytest.fixture
async def bot(db, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    settings = load_settings(_env_file=None, test_mode=True, test_channel_id=LOG_CHANNEL)
    store = SettingsStore(db, settings)
    await store.load()
    await store.set(GUILD, "log_channel_id", LOG_CHANNEL)
    await store.set(GUILD, "pings_mode", "on")
    return FakeBot(db, store, settings, FakeGuild())


@pytest.fixture
def streamer(bot):
    return FakeMember(bot.guild, STREAMER, "SuperNamu")


async def kinds(db):
    cur = await db.conn.execute("SELECT kind FROM action_log ORDER BY id")
    return [row["kind"] for row in await cur.fetchall()]


async def details(db, kind):
    cur = await db.conn.execute(
        "SELECT details FROM action_log WHERE kind = ? ORDER BY id DESC LIMIT 1", (kind,)
    )
    row = await cur.fetchone()
    return json.loads(row["details"]) if row and row["details"] else None


def test_the_role_name_comes_from_the_template_and_a_broken_one_falls_back(caplog):
    assert pings.fan_role_name("{name} pings", "SuperNamu") == "SuperNamu pings"
    assert pings.fan_role_name("fans of {name}!", "Ada") == "fans of Ada!"
    with caplog.at_level("WARNING"):
        assert pings.fan_role_name("{nmae} pings", "Ada") == "Ada pings"
    assert "could not be rendered" in caplog.text


def test_a_role_name_is_clamped_to_what_discord_will_take():
    long = pings.fan_role_name("{name} pings", "x" * 400)
    assert len(long) == pings.ROLE_NAME_LIMIT


def test_a_typed_name_keeps_its_own_words_and_is_clamped():
    assert pings.typed_role_name("  Namu   crew ") == "Namu crew"
    assert pings.typed_role_name("   ") == ""
    assert pings.typed_role_name(None) == ""
    assert len(pings.typed_role_name("x" * 400)) == pings.ROLE_NAME_LIMIT


def test_a_template_that_renders_to_nothing_still_names_the_streamer():
    assert pings.fan_role_name("   ", "Ada") == "Ada pings"


def test_the_menus_page_at_twenty_five_because_that_is_all_a_select_shows():
    assert pings.pages_of([]) == []
    rows = list(range(26))
    pages = pings.pages_of(rows)
    assert [len(page) for page in pages] == [25, 1]
    assert pings.menu_name(0) == "streamers" and pings.menu_name(1) == "streamers-2"
    assert pings.menu_title(0) == "Streamer pings"
    assert pings.menu_title(1) == "Streamer pings (2)"


async def test_the_fan_role_store_is_one_row_per_streamer(db):
    await pings.set_fan_role(db, GUILD, STREAMER, 42, STAFF)
    await pings.set_fan_role(db, GUILD, STREAMER, 43, STAFF)
    rows = await pings.all_fan_roles(db, GUILD)
    assert [row["role_id"] for row in rows] == [43]
    assert (await pings.get_fan_role(db, GUILD, STREAMER))["created_by"] == STAFF
    assert await pings.owner_of(db, GUILD, 43) == STREAMER
    assert await pings.forget_fan_role(db, GUILD, STREAMER) is True
    assert await pings.forget_fan_role(db, GUILD, STREAMER) is False


async def test_a_role_is_made_stored_and_put_on_the_streamers_menu(bot, streamer):
    outcome = await pings.ensure_fan_role(bot, bot.guild, streamer, by=STREAMER)

    assert outcome.ok and outcome.created
    assert bot.guild.made == [("SuperNamu pings", False, pings.ROLE_REASON)]
    assert "streamers" in outcome.message
    menu = await get_menu(bot.db, GUILD, "streamers")
    assert [row["label"] for row in await get_options(bot.db, menu["id"])] == ["SuperNamu pings"]
    assert "pings.fan_role_created" in await kinds(bot.db)
    assert (await details(bot.db, "pings.fan_role_created"))["reused"] is False


async def test_a_second_ask_changes_nothing_and_says_so(bot, streamer):
    first = await pings.ensure_fan_role(bot, bot.guild, streamer, by=STREAMER)
    again = await pings.ensure_fan_role(bot, bot.guild, streamer, by=STREAMER)

    assert again.ok is False and again.role_id == first.role_id
    assert "already has a ping role" in again.message
    assert len(bot.guild.made) == 1


async def test_a_staff_given_role_is_used_instead_of_making_one(bot, streamer):
    role = bot.guild.add_role(FakeRole(4242, "Namu Squad"))

    outcome = await pings.ensure_fan_role(
        bot, bot.guild, streamer, by=STAFF, existing_role=role, staff=True
    )

    assert outcome.ok and outcome.created is False and outcome.role_id == 4242
    assert bot.guild.made == []
    assert (await details(bot.db, "pings.fan_role_created"))["reused"] is True


async def test_a_name_typed_on_the_site_is_what_the_role_is_called(bot, streamer):
    outcome = await pings.ensure_fan_role(
        bot, bot.guild, streamer, by=STAFF, name="  Namu   crew  ", staff=True
    )

    assert outcome.ok and outcome.created
    assert bot.guild.made == [("Namu crew", False, pings.ROLE_REASON)]
    assert bot.guild.get_role(outcome.role_id).name == "Namu crew"


async def test_a_name_another_role_already_has_is_refused_and_nothing_is_made(bot, streamer):
    bot.guild.add_role(FakeRole(4242, "Namu crew"))

    outcome = await pings.ensure_fan_role(
        bot, bot.guild, streamer, by=STAFF, name="namu CREW", staff=True
    )

    assert outcome.ok is False and outcome.code == pings.DUPLICATE_CODE
    assert "already exists in this server" in outcome.message and "namu CREW" in outcome.message
    assert bot.guild.made == []
    assert await pings.get_fan_role(bot.db, GUILD, STREAMER) is None


async def test_a_name_that_is_nothing_at_all_is_refused_in_words(bot, streamer):
    outcome = await pings.ensure_fan_role(
        bot, bot.guild, streamer, by=STAFF, name="   ", staff=True
    )

    assert outcome.ok is False and outcome.code == pings.BLANK_NAME_CODE
    assert "needs a name" in outcome.message
    assert bot.guild.made == []


async def test_a_typed_name_is_clamped_to_what_discord_will_take(bot, streamer):
    outcome = await pings.ensure_fan_role(
        bot, bot.guild, streamer, by=STAFF, name="x" * 400, staff=True
    )

    assert outcome.ok and len(bot.guild.get_role(outcome.role_id).name) == pings.ROLE_NAME_LIMIT


async def test_a_picked_role_wins_over_a_name_and_is_never_a_duplicate(bot, streamer):
    role = bot.guild.add_role(FakeRole(4242, "Namu Squad"))

    outcome = await pings.ensure_fan_role(
        bot, bot.guild, streamer, by=STAFF, existing_role=role, name="Namu Squad", staff=True
    )

    assert outcome.ok and outcome.role_id == 4242 and bot.guild.made == []


async def test_the_template_reuses_a_role_of_that_name_rather_than_making_a_second(bot, streamer):
    bot.guild.add_role(FakeRole(4242, "supernamu PINGS"))

    outcome = await pings.ensure_fan_role(bot, bot.guild, streamer, by=STREAMER)

    assert outcome.ok and outcome.created is False and outcome.role_id == 4242
    assert bot.guild.made == []
    assert (await details(bot.db, "pings.fan_role_created"))["reused"] is True
    assert "Used the role" in outcome.message


async def test_a_same_named_role_black_bloc_cannot_hand_out_is_not_reused(bot, streamer):
    bot.guild.add_role(FakeRole(4242, "SuperNamu pings", assignable=False))

    outcome = await pings.ensure_fan_role(bot, bot.guild, streamer, by=STREAMER)

    assert outcome.ok and outcome.created and outcome.role_id != 4242
    assert bot.guild.made == [("SuperNamu pings", False, pings.ROLE_REASON)]


async def test_a_role_black_bloc_cannot_hand_out_is_refused_in_words(bot, streamer):
    role = bot.guild.add_role(FakeRole(4242, "Admin", assignable=False))

    outcome = await pings.ensure_fan_role(
        bot, bot.guild, streamer, by=STAFF, existing_role=role, staff=True
    )

    assert outcome.ok is False
    assert "cannot hand out" in outcome.message and "Server Settings" in outcome.message
    assert await pings.get_fan_role(bot.db, GUILD, STREAMER) is None


async def test_the_feature_being_off_refuses_a_member_in_words_but_never_staff(bot, streamer):
    await bot.store.set(GUILD, "pings_mode", "off")

    refused = await pings.ensure_fan_role(bot, bot.guild, streamer, by=STREAMER)
    assert refused.ok is False and "turned off" in refused.message

    allowed = await pings.ensure_fan_role(bot, bot.guild, streamer, by=STAFF, staff=True)
    assert allowed.ok is True


async def test_discord_refusing_the_role_is_a_sentence_not_a_traceback(bot, streamer):
    bot.guild.refuse_create = RuntimeError("Missing Permissions")

    outcome = await pings.ensure_fan_role(bot, bot.guild, streamer, by=STREAMER)

    assert outcome.ok is False and "Manage Roles" in outcome.message
    assert await pings.all_fan_roles(bot.db, GUILD) == []


async def test_removing_deletes_the_discord_role_by_default(bot, streamer):
    made = await pings.ensure_fan_role(bot, bot.guild, streamer, by=STREAMER)
    role = bot.guild.get_role(made.role_id)

    outcome = await pings.remove_fan_role(bot, bot.guild, STREAMER, by=STAFF)

    assert outcome.ok and role.deleted is True
    assert "is gone from the server" in outcome.message
    assert await pings.all_fan_roles(bot.db, GUILD) == []
    assert await get_menu(bot.db, GUILD, "streamers") is None
    assert (await details(bot.db, "pings.fan_role_removed"))["deleted"] is True


async def test_pings_fan_role_delete_off_leaves_the_role_on_the_server(bot, streamer):
    await bot.store.set(GUILD, "pings_fan_role_delete", False)
    made = await pings.ensure_fan_role(bot, bot.guild, streamer, by=STREAMER)

    outcome = await pings.remove_fan_role(bot, bot.guild, STREAMER, by=STAFF)

    assert bot.guild.get_role(made.role_id).deleted is False
    assert "was left on the server" in outcome.message


async def test_removing_a_role_nobody_has_says_so(bot, streamer):
    outcome = await pings.remove_fan_role(bot, bot.guild, STREAMER, by=STAFF)
    assert outcome.ok is False and "no ping role" in outcome.message


async def test_a_role_deleted_by_hand_is_forgotten_without_a_failure(bot, streamer):
    made = await pings.ensure_fan_role(bot, bot.guild, streamer, by=STREAMER)
    bot.guild.roles = [role for role in bot.guild.roles if role.id != made.role_id]

    outcome = await pings.remove_fan_role(bot, bot.guild, STREAMER, by=STAFF)

    assert outcome.ok and "already been deleted by hand" in outcome.message


async def test_the_announcement_reads_the_role_and_names_a_missing_one_once(bot, streamer):
    made = await pings.ensure_fan_role(bot, bot.guild, streamer, by=STREAMER)

    assert await pings.announced_fan_role(bot, bot.guild, STREAMER) == made.role_id
    bot.guild.roles = [role for role in bot.guild.roles if role.id != made.role_id]
    assert await pings.announced_fan_role(bot, bot.guild, STREAMER) is None
    assert "pings.fan_role_missing" in await kinds(bot.db)

    before = len(await kinds(bot.db))
    assert await pings.announced_fan_role(bot, bot.guild, STREAMER, notice=False) is None
    assert len(await kinds(bot.db)) == before


async def test_nothing_is_read_while_the_feature_is_off(bot, streamer):
    await pings.ensure_fan_role(bot, bot.guild, streamer, by=STREAMER)
    await bot.store.set(GUILD, "pings_mode", "off")

    assert await pings.announced_fan_role(bot, bot.guild, STREAMER) is None


async def test_twenty_six_streamers_fill_two_menus_and_shrink_back_to_one(bot):
    for at in range(26):
        member = FakeMember(bot.guild, 2000 + at, f"streamer{at:02d}")
        await pings.ensure_fan_role(bot, bot.guild, member, by=member.id)

    first = await get_menu(bot.db, GUILD, "streamers")
    second = await get_menu(bot.db, GUILD, "streamers-2")
    assert len(await get_options(bot.db, first["id"])) == 25
    assert len(await get_options(bot.db, second["id"])) == 1

    for at in range(10):
        await pings.remove_fan_role(bot, bot.guild, 2000 + at, by=STAFF)

    assert await get_menu(bot.db, GUILD, "streamers-2") is None
    assert len(await get_options(bot.db, (await get_menu(bot.db, GUILD, "streamers"))["id"])) == 16


async def test_the_menu_is_sorted_by_the_role_name_people_read(bot):
    for at, name in enumerate(("Zoe", "ada", "Mo")):
        member = FakeMember(bot.guild, 3000 + at, name)
        await pings.ensure_fan_role(bot, bot.guild, member, by=member.id)

    menu = await get_menu(bot.db, GUILD, "streamers")
    labels = [row["label"] for row in await get_options(bot.db, menu["id"])]

    assert labels == ["ada pings", "Mo pings", "Zoe pings"]


async def test_a_role_that_vanished_is_left_off_the_menu(bot, streamer):
    made = await pings.ensure_fan_role(bot, bot.guild, streamer, by=STREAMER)
    other = FakeMember(bot.guild, 3100, "Bee")
    bot.guild.roles = [role for role in bot.guild.roles if role.id != made.role_id]

    await pings.ensure_fan_role(bot, bot.guild, other, by=other.id)

    menu = await get_menu(bot.db, GUILD, "streamers")
    assert [row["label"] for row in await get_options(bot.db, menu["id"])] == ["Bee pings"]


async def test_a_role_change_discord_refuses_is_a_sentence_and_a_log_line(bot, streamer):
    role = bot.guild.add_role(FakeRole(4242, "Namu Squad"))
    fan = FakeMember(bot.guild, FAN, "Fan")
    fan.refuse = RuntimeError("Missing Permissions")

    said = await pings.wear(bot, bot.guild, fan, role, add=True)

    assert said is not None and "Manage Roles" in said and "Server Settings" in said
    assert "pings.forbidden" in await kinds(bot.db)
    assert (await details(bot.db, "pings.forbidden"))["action"] == "add"


async def test_a_role_change_that_works_says_nothing_and_moves_the_role(bot):
    role = bot.guild.add_role(FakeRole(4242, "Namu Squad"))
    fan = FakeMember(bot.guild, FAN, "Fan")

    assert await pings.wear(bot, bot.guild, fan, role, add=True) is None
    assert [one.id for one in fan.roles] == [4242]
    assert await pings.wear(bot, bot.guild, fan, role, add=False) is None
    assert fan.roles == []


async def test_setup_makes_the_events_role_and_points_both_feeds_at_it(bot):
    outcome = await pings.setup_events_role(bot, bot.guild, by=STAFF)

    assert outcome.ok and outcome.created
    assert bot.guild.made == [("Events", False, pings.ROLE_REASON)]
    assert bot.store.get(GUILD, "golive_ping_role_id") == outcome.role_id
    assert bot.store.get(GUILD, "events_ping_role_id") == outcome.role_id
    assert "notifications" in outcome.message
    menu = await get_menu(bot.db, GUILD, "notifications")
    options = await get_options(bot.db, menu["id"])
    assert [row["label"] for row in options] == [pings.EVENTS_OPTION_LABEL]
    assert options[0]["emoji"] == pings.EVENTS_OPTION_EMOJI
    assert menu["message_id"] is None
    assert "pings.setup" in await kinds(bot.db)


async def test_setup_reuses_a_role_that_is_already_called_events(bot):
    bot.guild.add_role(FakeRole(88, "events"))

    outcome = await pings.setup_events_role(bot, bot.guild, by=STAFF)

    assert outcome.ok and outcome.created is False and outcome.role_id == 88
    assert bot.guild.made == []
    assert "already here" in outcome.message


async def test_setup_run_twice_changes_nothing_the_second_time(bot):
    first = await pings.setup_events_role(bot, bot.guild, by=STAFF)
    again = await pings.setup_events_role(bot, bot.guild, by=STAFF)

    assert again.role_id == first.role_id
    assert "nothing was changed" in again.message
    assert "already on the" in again.message
    menu = await get_menu(bot.db, GUILD, "notifications")
    assert len(await get_options(bot.db, menu["id"])) == 1


async def test_setup_says_the_feature_is_still_off_rather_than_leaving_it_a_mystery(bot):
    await bot.store.set(GUILD, "pings_mode", "off")

    outcome = await pings.setup_events_role(bot, bot.guild, by=STAFF)

    assert outcome.ok and "still off" in outcome.message


async def test_setup_takes_the_role_staff_chose(bot):
    chosen = bot.guild.add_role(FakeRole(77, "Announcements"))

    outcome = await pings.setup_events_role(bot, bot.guild, by=STAFF, role=chosen)

    assert outcome.role_id == 77 and bot.guild.made == []


async def test_setup_refuses_a_role_it_cannot_hand_out(bot):
    chosen = bot.guild.add_role(FakeRole(77, "Admin", assignable=False))

    outcome = await pings.setup_events_role(bot, bot.guild, by=STAFF, role=chosen)

    assert outcome.ok is False and "cannot hand out" in outcome.message
    assert bot.store.get(GUILD, "golive_ping_role_id") is None


async def test_the_events_role_id_falls_back_to_the_events_feed_key(bot):
    assert pings.events_role_id(bot, GUILD) is None
    await bot.store.set(GUILD, "events_ping_role_id", 55)
    assert pings.events_role_id(bot, GUILD) == 55
    await bot.store.set(GUILD, "golive_ping_role_id", 66)
    assert pings.events_role_id(bot, GUILD) == 66


async def test_unlinking_keeps_the_role_unless_the_setting_says_delete(bot, streamer):
    await pings.ensure_fan_role(bot, bot.guild, streamer, by=STREAMER)

    assert await pings.on_streamer_left(bot, bot.guild, STREAMER, by=STREAMER) is None
    assert await pings.get_fan_role(bot.db, GUILD, STREAMER) is not None

    await bot.store.set(GUILD, "pings_fan_role_on_unlink", "delete")
    outcome = await pings.on_streamer_left(bot, bot.guild, STREAMER, by=STREAMER)

    assert outcome is not None and outcome.ok
    assert await pings.get_fan_role(bot.db, GUILD, STREAMER) is None


async def test_a_link_only_makes_a_role_while_the_setting_says_auto(bot, streamer):
    assert await pings.maybe_auto_create(bot, bot.guild, streamer, by=STREAMER) is None

    await bot.store.set(GUILD, "pings_fan_role_creation", "auto")
    outcome = await pings.maybe_auto_create(bot, bot.guild, streamer, by=STREAMER)

    assert outcome is not None and outcome.ok
    assert await pings.maybe_auto_create(bot, bot.guild, streamer, by=STREAMER) is None


async def test_auto_creation_is_still_governed_by_the_mode(bot, streamer):
    await bot.store.set(GUILD, "pings_fan_role_creation", "auto")
    await bot.store.set(GUILD, "pings_mode", "off")

    assert await pings.maybe_auto_create(bot, bot.guild, streamer, by=STREAMER) is None


async def test_the_web_head_marks_a_line_the_dashboard_left(bot, streamer):
    await pings.ensure_fan_role(bot, bot.guild, streamer, by=STAFF, via="website", staff=True)

    assert "web.pings.fan_role_created" in await kinds(bot.db)
    assert (await details(bot.db, "web.pings.fan_role_created"))["via"] == "website"


async def test_a_posted_panel_is_refreshed_when_a_streamer_is_added(bot, streamer):
    from black_bloc.cogs.community.role_menus import post_panel

    await pings.ensure_fan_role(bot, bot.guild, streamer, by=STREAMER)
    menu = await get_menu(bot.db, GUILD, "streamers")
    posted = await post_panel(
        bot, menu, await get_options(bot.db, menu["id"]), bot.guild.channel
    )

    other = FakeMember(bot.guild, 3200, "Bee")
    await pings.ensure_fan_role(bot, bot.guild, other, by=other.id)

    assert posted.edits, "the panel already up was not re-rendered"
    picker = posted.edits[-1]["view"].children[0]
    assert sorted(option.label for option in picker.options) == ["Bee pings", "SuperNamu pings"]
    assert "role_menu.reposted" in await kinds(bot.db)


async def test_the_panel_refresh_is_refused_in_test_mode_and_says_so_in_the_log(bot, streamer):
    from black_bloc.cogs.community.role_menus import post_panel

    await pings.ensure_fan_role(bot, bot.guild, streamer, by=STREAMER)
    menu = await get_menu(bot.db, GUILD, "streamers")
    await post_panel(bot, menu, await get_options(bot.db, menu["id"]), bot.guild.channel)

    class Guard:
        test_channel_id = 1

        def allows_channel(self, channel):
            return False

    bot.guard = Guard()
    other = FakeMember(bot.guild, 3300, "Bee")
    await pings.ensure_fan_role(bot, bot.guild, other, by=other.id)

    assert "role_menu.would_repost" in await kinds(bot.db)
    menu = await get_menu(bot.db, GUILD, "streamers")
    assert [row["label"] for row in await get_options(bot.db, menu["id"])] == [
        "Bee pings",
        "SuperNamu pings",
    ]


async def test_the_streamers_menus_are_the_only_ones_the_sync_touches(bot, streamer):
    from black_bloc.cogs.community.role_menus import create_menu

    await create_menu(bot.db, GUILD, "pronouns", "Pronouns", None, "multiple")
    await pings.ensure_fan_role(bot, bot.guild, streamer, by=STREAMER)
    await pings.remove_fan_role(bot, bot.guild, STREAMER, by=STAFF)

    assert [menu["name"] for menu in await list_menus(bot.db, GUILD)] == ["pronouns"]


# --- the panel layer -------------------------------------------------------------------------


@pytest.fixture
def fan(bot):
    return FakeMember(bot.guild, FAN, "Fan")


def a_state(**changed):
    base = {
        "mode_on": True,
        "events": ((pings.BOTH_FEEDS, pings.NOT_WORN),),
        "own_role": False,
        "creation": "self",
        "streams": False,
        "followed": 0,
        "unfollowed": 0,
        "listed": pings.LISTED_NEVER,
    }
    return pings.PanelState(**(base | changed))


def moves(state, **kwargs):
    return [move.label for move in pings.panel_buttons(state, **kwargs)]


def test_the_mode_being_off_leaves_nothing_but_refresh():
    assert moves(a_state(mode_on=False, streams=True)) == ["Refresh"]


def test_a_role_already_held_can_be_dropped_with_the_mode_off():
    """Owner 2026-09-05 (a): ending a role is never gated; only starting one is."""
    assert moves(a_state(mode_on=False, own_role=True, streams=True)) == [
        "Take my ping role away",
        "Refresh",
    ]


def test_an_unset_or_gone_events_role_renders_no_toggle_at_all():
    for wear in (pings.UNSET, pings.GONE):
        assert moves(a_state(events=((pings.BOTH_FEEDS, wear),))) == ["Refresh"]


def test_the_one_events_toggle_says_what_pressing_it_does():
    assert moves(a_state()) == ["Turn event pings on", "Refresh"]
    assert moves(a_state(events=((pings.BOTH_FEEDS, pings.WORN),))) == [
        "Turn them off",
        "Refresh",
    ]


def test_split_feeds_get_two_labelled_toggles():
    """I2 (b): a split feed is the only case where one toggle would lie about what it does."""
    state = a_state(events=((pings.GOLIVE_FEED, pings.WORN), (pings.EVENTS_FEED, pings.NOT_WORN)))
    assert moves(state) == ["Turn go-live pings off", "Turn event pings on", "Refresh"]


def test_the_fan_button_is_the_one_the_state_allows():
    assert moves(a_state(streams=True)) == [
        "Turn event pings on",
        "Start my own ping role",
        "Refresh",
    ]
    assert "Start my own ping role" not in moves(a_state(streams=False))
    assert "Start my own ping role" not in moves(a_state(streams=True, creation="staff"))


def test_taking_your_own_role_away_renders_whoever_may_start_one():
    """I1 (a): the access-REDUCING move is never gated on who was allowed to start it."""
    for creation in ("self", "staff", "auto"):
        state = a_state(own_role=True, creation=creation)
        assert "Take my ping role away" in moves(state)
        assert "Start my own ping role" not in moves(state)


def test_the_staff_row_is_appended_and_only_for_staff():
    assert moves(a_state(), staff=True)[-6:] == [
        "Streamers…",
        "Set up the Events role",
        "Set up the raid-train role",
        "Onboarding…",
        "Settings",
        "Logs",
    ]
    assert "Logs" not in moves(a_state(), staff=False)


def test_the_raid_train_toggle_stands_beside_the_events_one():
    """C4: three toggles, and the raid-train one is its own role and its own key."""
    state = a_state(
        events=((pings.BOTH_FEEDS, pings.NOT_WORN), (pings.RAID_FEED, pings.NOT_WORN))
    )
    assert moves(state) == ["Turn event pings on", "Turn raid-train pings on", "Refresh"]

    worn = a_state(events=((pings.BOTH_FEEDS, pings.WORN), (pings.RAID_FEED, pings.WORN)))
    assert moves(worn) == ["Turn them off", "Turn raid-train pings off", "Refresh"]


def test_a_raid_train_role_nobody_set_up_renders_no_toggle():
    state = a_state(events=((pings.BOTH_FEEDS, pings.WORN), (pings.RAID_FEED, pings.UNSET)))
    assert moves(state) == ["Turn them off", "Refresh"]


def test_the_streamer_list_switch_says_which_way_it_goes():
    """C4: only somebody Black Bloc has SEEN streaming gets the switch at all."""
    assert "Take me off the streamer list" not in moves(a_state())
    assert "Put me back on the list" not in moves(a_state())
    assert "Take me off the streamer list" in moves(a_state(listed=pings.LISTED_ON))
    assert "Put me back on the list" in moves(a_state(listed=pings.LISTED_OFF))


def test_taking_yourself_off_the_list_works_with_the_mode_off_and_coming_back_does_not():
    """The access-REDUCING half never needs the switch; the access-INCREASING half does."""
    off = a_state(mode_on=False, listed=pings.LISTED_ON)
    assert moves(off) == ["Take me off the streamer list", "Refresh"]
    back = a_state(mode_on=False, listed=pings.LISTED_OFF)
    assert moves(back) == ["Refresh"]


def test_no_control_sits_outside_discords_five_rows_in_the_busiest_state():
    """The worst case is two split feeds, raid trains, an own role, the list switch, Refresh
    and the six staff moves — twelve buttons plus the site link over three rows."""
    busiest = a_state(
        events=(
            (pings.GOLIVE_FEED, pings.WORN),
            (pings.EVENTS_FEED, pings.NOT_WORN),
            (pings.RAID_FEED, pings.NOT_WORN),
        ),
        own_role=True,
        listed=pings.LISTED_ON,
    )
    found = pings.panel_buttons(busiest, staff=True)
    assert len(found) == 12
    for row in {move.row for move in found}:
        assert sum(1 for move in found if move.row == row) <= 5
    assert all(pings.MEMBER_ROW <= move.row <= 4 for move in found)
    assert pings.site_row(found) <= 4
    assert sum(1 for move in found if move.row == pings.site_row(found)) < 5


def test_the_card_offers_a_repair_only_when_the_discord_role_has_gone():
    assert [move.label for move in pings.card_buttons(role_gone=False)] == [
        "Remove their ping role",
        "Back",
    ]
    assert [move.label for move in pings.card_buttons(role_gone=True)] == [
        "Remove their ping role",
        "Make the role again",
        "Back",
    ]


def test_the_card_offers_staff_the_reverse_of_whatever_the_listing_says():
    """Staff final say: a member's own hide is one press for staff to undo."""
    listed = [
        move.label for move in pings.card_buttons(role_gone=False, listed=pings.LISTED_ON)
    ]
    hidden = [
        move.label for move in pings.card_buttons(role_gone=False, listed=pings.LISTED_OFF)
    ]
    assert "Hide them from the list" in listed and "Put them back on the list" not in listed
    assert "Put them back on the list" in hidden and "Hide them from the list" not in hidden


def test_the_onboarding_sub_panel_never_offers_a_sync_that_would_refuse():
    def labels(**kwargs):
        return [move.label for move in pings.onboarding_buttons(**kwargs)]

    assert labels(managed=True, community=True) == [
        "Sync now",
        "Stop managing onboarding",
        "Back",
    ]
    assert labels(managed=True, community=False) == ["Stop managing onboarding", "Back"]
    assert labels(managed=False, community=True) == ["Manage onboarding again", "Back"]


async def test_the_state_is_read_off_the_rows_and_the_settings(bot, streamer, fan):
    made = await pings.ensure_fan_role(bot, bot.guild, streamer, by=STREAMER)
    role = bot.guild.get_role(made.role_id)
    await fan.add_roles(role)
    rows = await pings.all_fan_roles(bot.db, GUILD)

    mine = pings.panel_state(bot, bot.guild, streamer, rows, streams=True)
    theirs = pings.panel_state(bot, bot.guild, fan, rows, streams=False)

    assert mine.own_role is True and mine.followed == 0 and mine.unfollowed == 1
    assert theirs.own_role is False and theirs.followed == 1 and theirs.unfollowed == 0
    assert mine.mode_on is True and mine.creation == "follow"
    assert mine.listed == pings.LISTED_NEVER


async def test_the_state_counts_who_is_followable_off_the_list_not_off_the_roles(
    bot, streamer, fan
):
    """C4: the select is over the LIST, so somebody with no role yet still counts as offered
    and the streamer never counts as following themselves."""
    await pings.saw_streaming(bot, bot.guild, streamer, "twitch", "supernamu")
    rows = await pings.all_fan_roles(bot.db, GUILD)
    streamers = await pings.all_streamers(bot.db, GUILD)

    theirs = pings.panel_state(
        bot, bot.guild, fan, rows, streams=False, streamers=streamers, mine=None
    )
    mine = pings.panel_state(
        bot,
        bot.guild,
        streamer,
        rows,
        streams=True,
        streamers=streamers,
        mine=pings.row_for(streamers, STREAMER),
    )

    assert theirs.unfollowed == 1 and theirs.followed == 0
    assert mine.unfollowed == 0 and mine.listed == pings.LISTED_ON


async def test_the_feeds_are_one_while_the_two_keys_agree_and_two_once_they_split(bot):
    assert pings.events_feeds(bot, GUILD) == ((pings.BOTH_FEEDS, None),)

    await pings.setup_events_role(bot, bot.guild, by=STAFF)
    shared = bot.store.get(GUILD, "golive_ping_role_id")
    assert pings.events_feeds(bot, GUILD) == ((pings.BOTH_FEEDS, shared),)

    await bot.store.set(GUILD, "events_ping_role_id", 4242)
    assert pings.events_feeds(bot, GUILD) == (
        (pings.GOLIVE_FEED, shared),
        (pings.EVENTS_FEED, 4242),
    )
    assert pings.feed_role_id(bot, GUILD, pings.EVENTS_FEED) == 4242
    assert pings.feed_role_id(bot, GUILD, pings.GOLIVE_FEED) == shared


async def test_following_leaves_exactly_one_log_row_with_the_right_kind(bot, streamer, fan):
    made = await pings.ensure_fan_role(bot, bot.guild, streamer, by=STREAMER)
    row = await pings.get_fan_role(bot.db, GUILD, STREAMER)
    before = len(await kinds(bot.db))

    said = await pings.follow_streamer(bot, bot.guild, fan, row, add=True)

    found = await kinds(bot.db)
    assert len(found) == before + 1 and found[-1] == "pings.follow"
    assert [one.id for one in fan.roles] == [made.role_id]
    assert "SuperNamu pings" in said

    stopped = await pings.follow_streamer(bot, bot.guild, fan, row, add=False)
    found = await kinds(bot.db)
    assert len(found) == before + 2 and found[-1] == "pings.unfollow"
    assert fan.roles == [] and "no longer get" in stopped


async def test_following_twice_writes_nothing_and_says_so(bot, streamer, fan):
    await pings.ensure_fan_role(bot, bot.guild, streamer, by=STREAMER)
    row = await pings.get_fan_role(bot.db, GUILD, STREAMER)
    await pings.follow_streamer(bot, bot.guild, fan, row, add=True)
    before = len(await kinds(bot.db))

    said = await pings.follow_streamer(bot, bot.guild, fan, row, add=True)

    assert "already follow" in said and len(await kinds(bot.db)) == before


async def test_following_a_role_discord_no_longer_has_refuses_in_words(bot, streamer, fan):
    made = await pings.ensure_fan_role(bot, bot.guild, streamer, by=STREAMER)
    row = await pings.get_fan_role(bot.db, GUILD, STREAMER)
    bot.guild.roles = [one for one in bot.guild.roles if one.id != made.role_id]
    before = len(await kinds(bot.db))

    said = await pings.follow_streamer(bot, bot.guild, fan, row, add=True)

    assert "Press **Refresh**" in said and len(await kinds(bot.db)) == before


async def test_the_events_pings_move_leaves_exactly_one_log_row(bot, fan):
    await pings.setup_events_role(bot, bot.guild, by=STAFF)
    before = len(await kinds(bot.db))

    said = await pings.set_event_pings(bot, bot.guild, fan, add=True)

    found = await kinds(bot.db)
    assert len(found) == before + 1 and found[-1] == "pings.events_on"
    assert "go-live and event pings" in said

    await pings.set_event_pings(bot, bot.guild, fan, add=False)
    found = await kinds(bot.db)
    assert len(found) == before + 2 and found[-1] == "pings.events_off"
    assert fan.roles == []


async def test_the_events_move_names_the_feed_it_moved(bot, fan):
    golive = bot.guild.add_role(FakeRole(71, "Go live"))
    bot.guild.add_role(FakeRole(72, "Events"))
    await bot.store.set(GUILD, "golive_ping_role_id", 71)
    await bot.store.set(GUILD, "events_ping_role_id", 72)

    said = await pings.set_event_pings(bot, bot.guild, fan, add=True, feed=pings.GOLIVE_FEED)

    assert "go-live pings" in said
    assert [one.id for one in fan.roles] == [golive.id]
    assert (await details(bot.db, "pings.events_on"))["feed"] == pings.GOLIVE_FEED


async def test_the_events_move_refuses_before_staff_have_made_the_role(bot, fan):
    before = len(await kinds(bot.db))

    said = await pings.set_event_pings(bot, bot.guild, fan, add=True)

    assert "Set up the Events role" in said and len(await kinds(bot.db)) == before


async def test_starting_your_own_role_asks_the_mode_the_setting_and_the_link(bot, streamer):
    await bot.store.set(GUILD, "pings_mode", "off")
    assert "turned off" in (
        await pings.start_own_fan_role(bot, bot.guild, streamer, streams=True)
    ).message

    await bot.store.set(GUILD, "pings_mode", "on")
    await bot.store.set(GUILD, "pings_fan_role_creation", "staff")
    assert "Only staff start" in (
        await pings.start_own_fan_role(bot, bot.guild, streamer, streams=True)
    ).message

    await bot.store.set(GUILD, "pings_fan_role_creation", "self")
    assert "does not know you stream" in (
        await pings.start_own_fan_role(bot, bot.guild, streamer, streams=False)
    ).message

    made = await pings.start_own_fan_role(bot, bot.guild, streamer, streams=True)
    assert made.ok and bot.guild.made == [("SuperNamu pings", False, pings.ROLE_REASON)]


async def test_stopping_your_own_role_says_so_when_there_is_none(bot, streamer):
    assert "nothing to take away" in (
        await pings.stop_own_fan_role(bot, bot.guild, streamer)
    ).message

    await pings.ensure_fan_role(bot, bot.guild, streamer, by=STREAMER)
    gone = await pings.stop_own_fan_role(bot, bot.guild, streamer)

    assert gone.ok and await pings.get_fan_role(bot.db, GUILD, STREAMER) is None


async def test_the_notification_lines_say_both_halves(bot, streamer, fan):
    feeds = pings.events_feeds(bot, GUILD)
    empty = pings.notification_lines(bot.guild, fan, [], feeds)
    assert "have not set up the Events role" in empty[0]
    assert "follow no streamers" in empty[1]

    await pings.setup_events_role(bot, bot.guild, by=STAFF)
    made = await pings.ensure_fan_role(bot, bot.guild, streamer, by=STREAMER)
    await fan.add_roles(bot.guild.get_role(made.role_id))
    rows = await pings.all_fan_roles(bot.db, GUILD)

    lines = pings.notification_lines(bot.guild, fan, rows, pings.events_feeds(bot, GUILD))

    assert "**off**" in lines[0]
    assert "SuperNamu pings" in lines[1]


async def test_a_gone_events_role_is_a_line_not_a_zero(bot, fan):
    await pings.setup_events_role(bot, bot.guild, by=STAFF)
    bot.guild.roles = []

    lines = pings.notification_lines(bot.guild, fan, [], pings.events_feeds(bot, GUILD))

    assert "not in this server any more" in lines[0]


async def test_the_streamer_lines_count_followers_and_never_say_zero_for_a_gone_role(
    bot, streamer, fan
):
    assert pings.streamer_lines(bot.guild, []) == [pings.STREAMER_LIST_EMPTY]

    await pings.saw_streaming(bot, bot.guild, streamer, "twitch", "supernamu")
    streamers = await pings.all_streamers(bot.db, GUILD)
    assert pings.NO_ROLE_WORD in pings.streamer_lines(bot.guild, streamers, [])[0]

    made = await pings.ensure_fan_role(bot, bot.guild, streamer, by=STREAMER)
    bot.guild.get_role(made.role_id).members.append(fan)
    rows = await pings.all_fan_roles(bot.db, GUILD)
    assert "1 follower(s)" in pings.streamer_lines(bot.guild, streamers, rows)[0]

    bot.guild.roles = []
    assert pings.FOLLOWERS_UNKNOWN in pings.streamer_lines(bot.guild, streamers, rows)[0]


async def test_a_hidden_streamer_is_marked_hidden_on_the_staff_list(bot, streamer):
    await pings.saw_streaming(bot, bot.guild, streamer, "twitch", "supernamu")
    await pings.hide_streamer(bot, bot.guild, STREAMER, by=STAFF)

    said = pings.streamer_lines(bot.guild, await pings.all_streamers(bot.db, GUILD), [])[0]

    assert pings.HIDDEN_WORD in said


async def test_the_counts_tell_the_list_apart_from_roles_discord_still_has(bot, streamer):
    await pings.saw_streaming(bot, bot.guild, streamer, "twitch", "supernamu")
    made = await pings.ensure_fan_role(bot, bot.guild, streamer, by=STREAMER)
    streamers = await pings.all_streamers(bot.db, GUILD)
    rows = await pings.all_fan_roles(bot.db, GUILD)
    assert pings.counts_of(streamers, rows, bot.guild) == {
        "streamers": 1,
        "listed": 1,
        "with_role": 1,
        "channels": 0,
    }

    bot.guild.roles = [one for one in bot.guild.roles if one.id != made.role_id]
    assert pings.counts_of(streamers, rows, bot.guild) == {
        "streamers": 1,
        "listed": 1,
        "with_role": 0,
        "channels": 0,
    }
    assert "**1** streamer(s) seen" in pings.counts_line(streamers, rows, bot.guild)


def test_the_template_preview_shows_what_a_broken_one_will_actually_produce():
    assert pings.template_preview("{name} pings", "Ada") == ("Ada pings", False)
    assert pings.template_preview("fans of {name}!", "Ada") == ("fans of Ada!", False)
    assert pings.template_preview("{game} pings", "Ada") == ("Ada pings", True)
    assert pings.template_preview("   ", "Ada") == ("Ada pings", True)


async def test_the_panel_minutes_and_the_site_page_come_from_one_home(bot):
    assert pings.panel_minutes(bot.store, GUILD) == 10
    await bot.store.set(GUILD, "pings_panel_minutes", 4)
    assert pings.panel_minutes(bot.store, GUILD) == 4
    assert pings.site_page_url("https://blackbloc.test/") == "https://blackbloc.test/golive.html"
    assert pings.site_page_url("") is None
    assert pings.site_page_url(None) is None


async def test_saving_settings_writes_every_key_and_leaves_one_log_row(bot, streamer):
    before = len(await kinds(bot.db))

    said = await pings.save_settings(
        bot, bot.guild, streamer, {"pings_mode": "off", "pings_panel_minutes": 12}
    )

    assert bot.store.get(GUILD, "pings_mode") == "off"
    assert bot.store.get(GUILD, "pings_panel_minutes") == 12
    found = await kinds(bot.db)
    assert len(found) == before + 1 and found[-1] == "pings.settings"
    assert "pings_mode" in said


async def test_saving_settings_refuses_a_value_the_registry_will_not_take(bot, streamer):
    before = len(await kinds(bot.db))

    said = await pings.save_settings(bot, bot.guild, streamer, {"pings_mode": "maybe"})

    assert bot.store.get(GUILD, "pings_mode") == "on"
    assert len(await kinds(bot.db)) == before
    assert "maybe" in said


async def test_saving_nothing_changes_nothing(bot, streamer):
    before = len(await kinds(bot.db))

    assert await pings.save_settings(bot, bot.guild, streamer, {}) == pings.SETTINGS_NOTHING
    assert await pings.save_settings(bot, bot.guild, streamer, {"log_channel_id": 1}) == (
        pings.SETTINGS_NOTHING
    )
    assert len(await kinds(bot.db)) == before


async def test_the_web_head_is_built_for_every_panel_move_too(bot, streamer, fan):
    await pings.setup_events_role(bot, bot.guild, by=STAFF)
    await pings.ensure_fan_role(bot, bot.guild, streamer, by=STREAMER)
    row = await pings.get_fan_role(bot.db, GUILD, STREAMER)

    await pings.follow_streamer(bot, bot.guild, fan, row, add=True, via="website")
    await pings.set_event_pings(bot, bot.guild, fan, add=True, via="website")

    found = await kinds(bot.db)
    assert "web.pings.follow" in found and "web.pings.events_on" in found
    assert (await details(bot.db, "web.pings.follow"))["via"] == "website"


# --- the streamer list (C1) ---------------------------------------------------------------------


async def test_a_first_go_live_lists_the_streamer_once_and_a_second_adds_no_row(bot, streamer):
    assert await pings.saw_streaming(bot, bot.guild, streamer, "twitch", "supernamu") is True
    first = await pings.get_streamer(bot.db, GUILD, STREAMER)

    assert await pings.saw_streaming(bot, bot.guild, streamer, "twitch", None) is False

    rows = await pings.all_streamers(bot.db, GUILD)
    assert len(rows) == 1 and rows[0]["live_count"] == 2
    assert rows[0]["first_live_at"] == first["first_live_at"]
    assert rows[0]["last_live_at"] >= first["last_live_at"]
    assert rows[0]["login"] == "supernamu" and rows[0]["listed"] == 1
    assert (await kinds(bot.db)).count("pings.streamer_seen") == 1


async def test_a_bot_never_lands_on_the_list(bot, streamer):
    streamer.bot = True
    assert await pings.saw_streaming(bot, bot.guild, streamer, "twitch", None) is False
    assert await pings.all_streamers(bot.db, GUILD) == []


async def test_a_streamer_a_person_hid_stays_hidden_across_a_go_live(bot, streamer):
    await pings.saw_streaming(bot, bot.guild, streamer, "twitch", None)
    await pings.hide_streamer(bot, bot.guild, STREAMER, by=STREAMER)

    await pings.saw_streaming(bot, bot.guild, streamer, "twitch", None)

    row = await pings.get_streamer(bot.db, GUILD, STREAMER)
    assert row["listed"] == 0 and row["hidden_by"] == STREAMER
    assert await pings.listed_streamers(bot.db, GUILD) == []


async def test_a_staleness_prune_is_undone_by_going_live_again(bot, streamer):
    """`hidden_by` empty is the difference: nobody decided, so nothing has to be undone by hand."""
    await pings.saw_streaming(bot, bot.guild, streamer, "twitch", None)
    await pings.set_listed(bot.db, GUILD, STREAMER, listed=False, by=None)

    await pings.saw_streaming(bot, bot.guild, streamer, "twitch", None)

    assert (await pings.get_streamer(bot.db, GUILD, STREAMER))["listed"] == 1


async def test_hiding_yourself_drops_an_unworn_role_and_keeps_a_worn_one(bot, streamer, fan):
    await pings.saw_streaming(bot, bot.guild, streamer, "twitch", None)
    made = await pings.ensure_fan_role(bot, bot.guild, streamer, by=STREAMER)
    role = bot.guild.get_role(made.role_id)

    outcome = await pings.hide_streamer(bot, bot.guild, STREAMER, by=STREAMER)

    assert outcome.ok and role.deleted is True
    assert await pings.get_fan_role(bot.db, GUILD, STREAMER) is None
    assert "pings.streamer_hidden" in await kinds(bot.db)

    await pings.restore_streamer(bot, bot.guild, STREAMER, by=STREAMER)
    again = await pings.ensure_fan_role(bot, bot.guild, streamer, by=STREAMER)
    kept = bot.guild.get_role(again.role_id)
    kept.members.append(fan)

    await pings.hide_streamer(bot, bot.guild, STREAMER, by=STAFF)

    assert kept.deleted is False
    assert await pings.get_fan_role(bot.db, GUILD, STREAMER) is not None


async def test_the_two_listing_moves_refuse_in_words_rather_than_writing_twice(bot, streamer):
    nothing = await pings.hide_streamer(bot, bot.guild, STREAMER, by=STREAMER)
    assert not nothing.ok and nothing.message == pings.NOT_ON_THE_LIST

    await pings.saw_streaming(bot, bot.guild, streamer, "twitch", None)
    assert (await pings.restore_streamer(bot, bot.guild, STREAMER, by=STAFF)).ok is False
    await pings.hide_streamer(bot, bot.guild, STREAMER, by=STREAMER)
    again = await pings.hide_streamer(bot, bot.guild, STREAMER, by=STREAMER)
    assert not again.ok and "already off" in again.message

    back = await pings.restore_streamer(bot, bot.guild, STREAMER, by=STAFF)
    assert back.ok and "pings.streamer_restored" in await kinds(bot.db)


# --- lazy roles and the prunes (C2) --------------------------------------------------------------


async def test_the_first_follow_makes_the_role_and_the_second_does_not(bot, streamer, fan):
    await pings.saw_streaming(bot, bot.guild, streamer, "twitch", None)
    other = FakeMember(bot.guild, 902, "Bo")

    said = await pings.follow_from_list(bot, bot.guild, fan, STREAMER)

    row = await pings.get_fan_role(bot.db, GUILD, STREAMER)
    assert row is not None and "SuperNamu pings" in said
    assert [one.id for one in fan.roles] == [int(row["role_id"])]
    made = (await kinds(bot.db)).count("pings.fan_role_created")

    await pings.follow_from_list(bot, bot.guild, other, STREAMER)

    assert (await kinds(bot.db)).count("pings.fan_role_created") == made
    assert [one.id for one in other.roles] == [int(row["role_id"])]


async def test_following_somebody_off_the_list_refuses_in_words_and_makes_nothing(
    bot, streamer, fan
):
    await pings.saw_streaming(bot, bot.guild, streamer, "twitch", None)
    await pings.hide_streamer(bot, bot.guild, STREAMER, by=STREAMER)

    said = await pings.follow_from_list(bot, bot.guild, fan, STREAMER)

    assert "streamer list any more" in said
    assert await pings.get_fan_role(bot.db, GUILD, STREAMER) is None


async def test_a_staff_only_server_refuses_the_first_follow_in_words(bot, streamer, fan):
    await bot.store.set(GUILD, pings.CREATION_KEY, "staff")
    await pings.saw_streaming(bot, bot.guild, streamer, "twitch", None)

    said = await pings.follow_from_list(bot, bot.guild, fan, STREAMER)

    assert "only staff start one" in said
    assert await pings.get_fan_role(bot.db, GUILD, STREAMER) is None
    assert fan.roles == []


async def test_following_with_the_mode_off_refuses_and_makes_nothing(bot, streamer, fan):
    await bot.store.set(GUILD, pings.MODE_KEY, "off")
    await pings.saw_streaming(bot, bot.guild, streamer, "twitch", None)

    assert await pings.follow_from_list(bot, bot.guild, fan, STREAMER) == pings.OFF
    assert await pings.get_fan_role(bot.db, GUILD, STREAMER) is None


async def test_the_empty_role_prune_deletes_only_a_role_nobody_wears(bot, streamer):
    made = await pings.ensure_fan_role(bot, bot.guild, streamer, by=STREAMER)
    role = bot.guild.get_role(made.role_id)
    now = datetime.now(UTC)

    assert await pings.prune_empty_roles(bot, bot.guild, now=now) == []
    row = await pings.get_fan_role(bot.db, GUILD, STREAMER)
    assert row["unworn_since"] is not None

    assert await pings.prune_empty_roles(bot, bot.guild, now=now) == []
    later = now + timedelta(days=31)
    assert await pings.prune_empty_roles(bot, bot.guild, now=later) == [STREAMER]
    assert role.deleted is True
    assert await pings.get_fan_role(bot.db, GUILD, STREAMER) is None
    assert "pings.role_pruned" in await kinds(bot.db)


async def test_a_worn_role_survives_the_prune_and_its_clock_is_cleared(bot, streamer, fan):
    made = await pings.ensure_fan_role(bot, bot.guild, streamer, by=STREAMER)
    role = bot.guild.get_role(made.role_id)
    now = datetime.now(UTC)
    await pings.prune_empty_roles(bot, bot.guild, now=now)

    role.members.append(fan)
    assert await pings.prune_empty_roles(bot, bot.guild, now=now + timedelta(days=99)) == []
    assert (await pings.get_fan_role(bot.db, GUILD, STREAMER))["unworn_since"] is None

    assert await pings.prune_empty_roles(bot, bot.guild, now=now + timedelta(days=999)) == []
    assert role.deleted is False


async def test_the_stale_prune_takes_a_quiet_streamer_off_the_list(bot, streamer):
    await pings.saw_streaming(bot, bot.guild, streamer, "twitch", None)
    now = datetime.now(UTC)

    assert await pings.prune_stale_streamers(bot, bot.guild, now=now) == []
    assert await pings.prune_stale_streamers(
        bot, bot.guild, now=now + timedelta(days=91)
    ) == [STREAMER]

    row = await pings.get_streamer(bot.db, GUILD, STREAMER)
    assert row["listed"] == 0 and row["hidden_by"] is None
    assert "pings.streamer_pruned" in await kinds(bot.db)


async def test_an_unreadable_timestamp_is_never_old_enough_to_prune(bot, streamer):
    await pings.saw_streaming(bot, bot.guild, streamer, "twitch", None)
    await bot.db.conn.execute(
        "UPDATE streamers SET last_live_at = 'whenever' WHERE guild_id = ?", (GUILD,)
    )
    await bot.db.conn.commit()

    assert await pings.prune_stale_streamers(bot, bot.guild, now=datetime.now(UTC)) == []


# --- the raid-train role (C3) --------------------------------------------------------------------


async def test_the_raid_train_role_is_made_once_and_reused_after_that(bot):
    made = await pings.setup_raidtrain_role(bot, bot.guild, by=STAFF)

    assert made.ok and made.created is True
    assert bot.store.get(GUILD, "raidtrain_ping_role_id") == made.role_id
    assert "pings.raidtrain_setup" in await kinds(bot.db)
    assert pings.feed_role_id(bot, GUILD, pings.RAID_FEED) == made.role_id

    again = await pings.setup_raidtrain_role(bot, bot.guild, by=STAFF)
    assert again.ok and again.created is False and "already pointed" in again.message


async def test_the_raid_train_role_takes_the_one_staff_picked(bot):
    picked = bot.guild.add_role(FakeRole(77, "Trains"))

    made = await pings.setup_raidtrain_role(bot, bot.guild, by=STAFF, role=picked)

    assert made.role_id == 77 and made.created is False
    assert bot.store.get(GUILD, "raidtrain_ping_role_id") == 77


async def test_a_raid_train_toggle_with_no_role_says_who_to_ask(bot, fan):
    said = await pings.set_event_pings(bot, bot.guild, fan, add=True, feed=pings.RAID_FEED)
    assert said == pings.NO_RAID_ROLE

    await pings.setup_raidtrain_role(bot, bot.guild, by=STAFF)
    on = await pings.set_event_pings(bot, bot.guild, fan, add=True, feed=pings.RAID_FEED)
    assert "raid-train pings" in on
    assert (await details(bot.db, "pings.events_on"))["feed"] == pings.RAID_FEED


# --- a ping role for a spotlight channel (info/spotlight-pings-design.md §A) ---------------


GDQ = 1


async def a_channel(db, spotlight_id=GDQ, login="gamesdonequick", name="GamesDoneQuick"):
    await db.conn.execute(
        "INSERT INTO spotlight_channels(id, guild_id, twitch_login, display_name, added_by, "
        "added_at, pin) VALUES (?, ?, ?, ?, ?, '2026-09-20T00:00:00+00:00', 1)",
        (spotlight_id, GUILD, login, name, STAFF),
    )
    await db.conn.commit()
    cur = await db.conn.execute(
        "SELECT * FROM spotlight_channels WHERE id = ?", (spotlight_id,)
    )
    return await cur.fetchone()


async def test_a_channels_ping_role_is_named_by_the_same_template_a_persons_is(bot):
    channel = await a_channel(bot.db)

    made = await pings.ensure_fan_role(bot, bot.guild, None, by=STAFF, spotlight=channel)

    assert made.ok and made.created
    role = bot.guild.get_role(made.role_id)
    assert role.name == "GamesDoneQuick pings"
    row = await pings.get_spotlight_fan_role(bot.db, GUILD, GDQ)
    assert row["user_id"] is None and pings.spotlight_of(row) == GDQ
    assert row["spotlight_login"] == "gamesdonequick"
    assert pings.is_spotlight(row) is True
    assert await details(bot.db, "pings.fan_role_created") == {
        "role_id": role.id,
        "role": "GamesDoneQuick pings",
        "reused": False,
        "via": "discord",
        "spotlight_id": GDQ,
        "spotlight": "gamesdonequick",
    }


async def test_a_channels_role_can_be_named_from_the_site_and_a_duplicate_is_refused(bot):
    channel = await a_channel(bot.db)
    bot.guild.add_role(FakeRole(4242, "GDQ crew"))

    refused = await pings.ensure_fan_role(
        bot, bot.guild, None, by=STAFF, name="gdq CREW", spotlight=channel
    )
    made = await pings.ensure_fan_role(
        bot, bot.guild, None, by=STAFF, name="GDQ friends", spotlight=channel
    )

    assert refused.ok is False and refused.code == pings.DUPLICATE_CODE
    assert made.ok and bot.guild.get_role(made.role_id).name == "GDQ friends"
    assert await pings.get_spotlight_fan_role(bot.db, GUILD, GDQ) is not None


async def test_a_channel_cannot_be_given_a_second_ping_role(bot):
    channel = await a_channel(bot.db)
    first = await pings.ensure_fan_role(bot, bot.guild, None, by=STAFF, spotlight=channel)

    again = await pings.ensure_fan_role(bot, bot.guild, None, by=STAFF, spotlight=channel)

    assert not again.ok
    assert "GamesDoneQuick" in again.message and str(first.role_id) in again.message
    assert len(await pings.spotlight_fan_roles(bot.db, GUILD)) == 1


async def test_a_channels_row_and_a_members_row_never_stand_in_for_each_other(bot, streamer):
    channel = await a_channel(bot.db)
    await pings.ensure_fan_role(bot, bot.guild, streamer, by=STAFF)
    await pings.ensure_fan_role(bot, bot.guild, None, by=STAFF, spotlight=channel)

    every = await pings.all_fan_roles(bot.db, GUILD)

    assert len(every) == 2
    assert pings.row_for(every, STREAMER) is not None
    assert pings.row_for(every, GDQ) is None, "a spotlight id is not a member id"
    assert pings.spotlight_row_for(every, GDQ) is not None
    assert [row["user_id"] for row in await pings.member_fan_roles(bot.db, GUILD)] == [STREAMER]
    assert pings.counts_of([], every, bot.guild)["channels"] == 1


async def test_taking_a_channels_ping_role_away_obeys_the_delete_setting(bot):
    channel = await a_channel(bot.db)
    made = await pings.ensure_fan_role(bot, bot.guild, None, by=STAFF, spotlight=channel)
    role = bot.guild.get_role(made.role_id)
    await bot.store.set(GUILD, pings.DELETE_KEY, True)

    gone = await pings.remove_fan_role(
        bot, bot.guild, by=STAFF, spotlight=channel, because="spotlight_expired"
    )

    assert gone.ok and role.deleted is True and bot.guild.get_role(made.role_id) is None
    assert await pings.get_spotlight_fan_role(bot.db, GUILD, GDQ) is None
    assert await details(bot.db, "pings.fan_role_removed") == {
        "role_id": made.role_id,
        "deleted": True,
        "via": "discord",
        "because": "spotlight_expired",
        "spotlight_id": GDQ,
        "spotlight": "gamesdonequick",
    }


async def test_a_kept_role_is_left_on_the_server_when_the_setting_says_keep(bot):
    channel = await a_channel(bot.db)
    made = await pings.ensure_fan_role(bot, bot.guild, None, by=STAFF, spotlight=channel)
    await bot.store.set(GUILD, pings.DELETE_KEY, False)

    gone = await pings.remove_fan_role(bot, bot.guild, by=STAFF, spotlight=channel)

    assert gone.ok and bot.guild.get_role(made.role_id).deleted is False
    assert "left on the server" in gone.message
    assert await pings.get_spotlight_fan_role(bot.db, GUILD, GDQ) is None


async def test_a_channel_with_no_role_refuses_the_removal_in_words(bot):
    channel = await a_channel(bot.db)

    gone = await pings.remove_fan_role(bot, bot.guild, by=STAFF, spotlight=channel)

    assert not gone.ok and "has no ping role" in gone.message
    assert await kinds(bot.db) == []


async def test_an_announcement_mentions_a_channels_role_and_says_so_when_it_is_gone(bot, caplog):
    channel = await a_channel(bot.db)
    made = await pings.ensure_fan_role(bot, bot.guild, None, by=STAFF, spotlight=channel)

    assert await pings.announced_spotlight_fan_role(bot, bot.guild, GDQ) == made.role_id

    bot.guild.roles = [one for one in bot.guild.roles if one.id != made.role_id]
    with caplog.at_level("WARNING"):
        assert await pings.announced_spotlight_fan_role(bot, bot.guild, GDQ) is None
    assert "not in this server any more" in caplog.text
    assert "pings.fan_role_missing" in await kinds(bot.db)
    assert (await details(bot.db, "pings.fan_role_missing"))["spotlight_id"] == GDQ


async def test_nothing_is_mentioned_for_a_channel_nobody_has_given_a_role(bot):
    await a_channel(bot.db)

    assert await pings.announced_spotlight_fan_role(bot, bot.guild, GDQ) is None
    assert await kinds(bot.db) == []


async def test_a_member_follows_a_channel_exactly_as_they_follow_a_person(bot, streamer):
    channel = await a_channel(bot.db)
    fan = FakeMember(bot.guild, FAN, "Fan")

    said = await pings.follow_spotlight(bot, bot.guild, fan, channel)

    row = await pings.get_spotlight_fan_role(bot.db, GUILD, GDQ)
    assert "GamesDoneQuick pings" in said
    assert pings.wears(fan, row["role_id"])
    assert (await details(bot.db, "pings.follow"))["streamer_id"] == "spotlight:1"
    assert pings.followable_channels(bot.guild, fan, [channel], [row]) == []
    assert pings.following(bot.guild, fan, [row])[0]["role_id"] == row["role_id"]


async def test_a_channel_with_no_role_yet_is_still_offered_to_follow(bot):
    channel = await a_channel(bot.db)
    fan = FakeMember(bot.guild, FAN, "Fan")

    offered = pings.followable_channels(bot.guild, fan, [channel], [])

    assert [row["twitch_login"] for row in offered] == ["gamesdonequick"]


async def test_only_staff_start_a_channels_role_when_the_setting_says_so(bot):
    channel = await a_channel(bot.db)
    fan = FakeMember(bot.guild, FAN, "Fan")
    await bot.store.set(GUILD, pings.CREATION_KEY, pings.STAFF)

    said = await pings.follow_spotlight(bot, bot.guild, fan, channel)

    assert "only staff start one" in said
    assert await pings.get_spotlight_fan_role(bot.db, GUILD, GDQ) is None


async def test_the_unworn_prune_never_reaches_a_channels_role(bot):
    """A channel's role goes when the channel does (§A), never on the 30-day sweep — the
    prune is keyed by member and a spotlight has none."""
    channel = await a_channel(bot.db)
    made = await pings.ensure_fan_role(bot, bot.guild, None, by=STAFF, spotlight=channel)
    await bot.store.set(GUILD, pings.EMPTY_ROLE_DAYS_KEY, 1)
    later = datetime.now(UTC) + timedelta(days=90)

    assert await pings.prune_empty_roles(bot, bot.guild, now=later) == []
    assert await pings.prune_empty_roles(bot, bot.guild, now=later) == []
    assert bot.guild.get_role(made.role_id) is not None
