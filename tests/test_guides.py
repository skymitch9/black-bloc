import json
from types import SimpleNamespace

import pytest

from black_bloc import guides
from black_bloc.config import load_settings
from black_bloc.settings_store import SettingsStore

GUILD = 4242
OTHER_GUILD = 99


class Channel:
    def __init__(self, channel_id, name):
        self.id = channel_id
        self.name = name


class Guild:
    def __init__(self, guild_id=GUILD):
        self.id = guild_id
        self.name = "Black in a Flash!"
        self.channels = [Channel(500, "blackbloc-logs"), Channel(501, "general")]
        self.members = {}

    def get_channel(self, channel_id):
        return next((one for one in self.channels if one.id == int(channel_id)), None)

    def get_member(self, user_id):
        return self.members.get(int(user_id))

    def get_role(self, role_id):
        return None


class Bot:
    def __init__(self, db, store, settings, guilds):
        self.db = db
        self.store = store
        self.settings = settings
        self.guilds = list(guilds)

    def is_ready(self):
        return True


@pytest.fixture
def site(tmp_path, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    root = tmp_path / "public"
    (root / "assets").mkdir(parents=True)
    return root


@pytest.fixture
async def bot(db, site, tmp_path, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    settings = load_settings(
        _env_file=None,
        site_root=site,
        site_origin="https://blackbloc.test",
        database_path=tmp_path / "data" / "black_bloc.sqlite3",
        test_mode=True,
        test_channel_id=500,
    )
    store = SettingsStore(db, settings)
    await store.load()
    return Bot(db, store, settings, [Guild()])


def write_release(bot, release, features, commit="abc1234"):
    guides.release_path(bot).write_text(
        json.dumps({"release": release, "commit": commit, "changed_features": features}),
        encoding="utf-8",
    )


async def rows(db, sql, *args):
    cur = await db.conn.execute(sql, args)
    return list(await cur.fetchall())


# --- the seed ---------------------------------------------------------------------------------


def test_the_shipped_seed_is_eighteen_guides_with_a_slug_each():
    entries = guides.seed_entries()

    assert len(entries) == 27
    assert len({one["slug"] for one in entries}) == 27
    assert {one["audience"] for one in entries} == {"member", "staff"}


async def test_seeding_a_guild_writes_eighteen_guides_and_no_pictures(bot, db):
    made = await guides.seed_guides(db, GUILD)

    assert made == 27
    assert await guides.count_guides(db, GUILD) == 27
    assert len(await rows(db, "SELECT * FROM guide_media")) == 0
    steps = await rows(db, "SELECT * FROM guide_steps")
    assert steps and all(row["seed_do"] == row["do_text"] for row in steps)


async def test_seeding_twice_adds_nothing_and_keeps_a_staff_edit(bot, db):
    await guides.seed_guides(db, GUILD)
    guide = await guides.get_guide(db, GUILD, "golive-announce")
    step = (await guides.steps_of(db, guide["id"]))[0]
    await db.conn.execute(
        "UPDATE guide_steps SET do_text = ? WHERE id = ?", ("Press **Go**.", step["id"])
    )
    await db.conn.commit()

    assert await guides.seed_guides(db, GUILD) == 0
    again = (await guides.steps_of(db, guide["id"]))[0]
    assert again["do_text"] == "Press **Go**."


async def test_a_changed_seed_refreshes_only_what_put_the_original_back_reads(bot, db, monkeypatch):
    await guides.seed_guides(db, GUILD)
    guide = await guides.get_guide(db, GUILD, "golive-announce")
    step = (await guides.steps_of(db, guide["id"]))[0]
    await db.conn.execute(
        "UPDATE guide_steps SET do_text = ? WHERE id = ?", ("Press **Go**.", step["id"])
    )
    await db.conn.commit()
    entries = guides.seed_entries()
    for entry in entries:
        if entry["slug"] == "golive-announce":
            entry["steps"][0]["do"] = "Type **/golive** anywhere."
    monkeypatch.setattr(guides, "seed_entries", lambda: entries)

    assert await guides.refresh_seeds(db, GUILD) == 1
    fresh = (await guides.steps_of(db, guide["id"]))[0]
    assert fresh["do_text"] == "Press **Go**."
    assert fresh["seed_do"] == "Type **/golive** anywhere."
    assert await guides.refresh_seeds(db, GUILD) == 0


async def test_reset_puts_the_whole_guide_back_and_refuses_one_nobody_shipped(bot, db):
    await guides.seed_guides(db, GUILD)
    guide = await guides.get_guide(db, GUILD, "voice-room")
    await db.conn.execute("DELETE FROM guide_steps WHERE guide_id = ?", (guide["id"],))
    await db.conn.execute(
        "UPDATE guides SET title = 'Wrecked' WHERE id = ?", (guide["id"],)
    )
    await db.conn.commit()

    assert await guides.reset_to_seed(db, GUILD, guide) is True
    fresh = await guides.get_guide(db, GUILD, "voice-room")
    assert fresh["title"] == "Make your own voice room"
    assert len(await guides.steps_of(db, fresh["id"])) == 4

    mine = await guides.create_guide(
        db, GUILD, slug="mine", title="Mine", goal="A goal.", feature="core"
    )
    row = await guides.get_guide_by_id(db, mine)
    assert await guides.reset_to_seed(db, GUILD, row) is False
    assert guides.is_seeded(row) is False


# --- the linter -------------------------------------------------------------------------------


def test_the_linter_warns_about_the_openers_and_never_refuses():
    warnings = guides.lint_step("Simply press the thing")

    assert warnings
    assert any("Simply" in one for one in warnings)
    assert any("bold" in one for one in warnings)


def test_a_step_that_follows_the_rules_warns_about_nothing():
    assert guides.lint_step("Press **Link my Twitch channel**.", "The panel reads your name.") == []


def test_the_linter_names_each_rule_it_is_enforcing():
    assert guides.lint_step("Press **A** and then press **B**.")[0].startswith("This step asks")
    assert "bold" in guides.lint_step("Press the button.")[0]
    assert any("characters" in one for one in guides.lint_step("Press **A**. " + "x" * 200))
    assert any(
        "on the screen" in one
        for one in guides.lint_step("Press **A**.", "It should post the thing.")
    )
    assert any("easy" in one for one in guides.lint_step("Press **A**, it is easy."))
    assert any("always" in one for one in guides.lint_step("Press **A**; it always works."))


def test_lint_steps_keys_its_warnings_by_position():
    found = guides.lint_steps(
        [
            {"position": 1, "do_text": "Press **A**.", "expect_text": "The panel opens."},
            {"position": 2, "do_text": "Just press it."},
        ]
    )

    assert found[1] == []
    assert found[2]


# --- the live values --------------------------------------------------------------------------


async def test_a_setting_fact_renders_the_way_the_panel_renders_it(bot, db):
    await bot.store.set(GUILD, "golive_channel_id", 501)
    found = await guides.resolve_facts(
        bot,
        bot.guilds[0],
        [
            {"kind": "setting", "ref": "golive_mode"},
            {"kind": "setting", "ref": "golive_channel_id"},
        ],
    )

    assert [one["ref"] for one in found] == ["golive_mode", "golive_channel_id"]
    assert found[0]["value"] == "shadow" and found[0]["help"]
    assert found[1]["value"] == "#general"
    assert all(one["read_at"] for one in found)


async def test_the_four_core_keys_and_every_log_level_are_refused_in_words(bot):
    assert "Lead" in guides.refused_setting("staff_channel_id")
    assert "Discord log" in guides.refused_setting("golive_log_level")
    assert guides.refused_setting("not_a_key").startswith("**not_a_key**")
    assert guides.refused_setting("golive_mode") is None

    found = await guides.resolve_facts(
        bot, bot.guilds[0], [{"kind": "setting", "ref": "staff_channel_id"}]
    )
    assert found == []


async def test_every_probe_reads_without_a_query_of_its_own(bot, db):
    wanted = [
        "golive.linked_count",
        "golive.live_now",
        "events.open_count",
        "requests.open_count",
        "tempvoice.open_rooms",
        "polls.open_count",
        "birthdays.next",
        "raidtrain.next",
        "test_mode",
    ]

    assert sorted(guides.PROBES) == sorted(wanted)
    found = await guides.resolve_facts(
        bot, bot.guilds[0], [{"kind": "probe", "ref": name} for name in wanted]
    )
    assert [one["value"] for one in found] != []
    assert all(one["value"] and one["label"] for one in found)
    assert found[-1]["value"] == "on — #blackbloc-logs"


async def test_a_probe_that_throws_says_not_readable_rather_than_breaking_the_page(
    bot, monkeypatch
):
    async def boom(bot, guild):
        raise RuntimeError("no")

    monkeypatch.setitem(guides.PROBES, "test_mode", boom)
    found = await guides.resolve_facts(bot, bot.guilds[0], [{"kind": "probe", "ref": "test_mode"}])

    assert found[0]["value"] == "not readable"


def test_an_unknown_probe_is_refused_by_name_with_the_ones_there_are():
    said = guides.refused_probe("golive.nothing")

    assert "golive.nothing" in said and "test_mode" in said
    assert guides.refused_probe("test_mode") is None


# --- releases and staleness -------------------------------------------------------------------


def test_feature_paths_map_a_changed_file_to_the_feature_that_owns_it():
    assert guides.features_changed(["black_bloc/cogs/content/golive.py"]) == ["golive"]
    assert guides.features_changed(["site/public/assets/page-polls.js"]) == ["poll"]
    assert guides.features_changed(["README.md"]) == []
    assert set(guides.FEATURE_PATHS) <= set(guides.features())


def test_a_release_without_digits_still_orders_against_the_one_before_it():
    assert guides.release_before("v110", "v112") is True
    assert guides.release_before("v112", "v110") is False
    assert guides.release_before(None, "v112") is True


async def test_no_release_file_means_nothing_happens_at_all(bot, db):
    await guides.seed_guides(db, GUILD)

    assert await guides.reconcile_releases(bot) is None
    assert await rows(db, "SELECT * FROM guide_releases") == []


async def test_a_release_naming_golive_flips_the_go_live_shots_and_no_other(bot, db):
    await guides.seed_guides(db, GUILD)
    golive = await guides.get_guide(db, GUILD, "golive-announce")
    poll = await guides.get_guide(db, GUILD, "poll-vote-make")
    shot = await guides.save_media(bot, GUILD, golive["id"], b"\x89PNG\r\n\x1a\n" + b"\x00" * 40)
    other = await guides.save_media(bot, GUILD, poll["id"], b"\x89PNG\r\n\x1a\n" + b"\x00" * 40)
    fresh = await guides.save_media(
        bot, GUILD, golive["id"], b"\x89PNG\r\n\x1a\n" + b"\x00" * 40, shot_release="v112"
    )
    write_release(bot, "v112", ["golive"])

    found = await guides.reconcile_releases(bot)

    assert found["release"] == "v112" and found["features"] == ["golive"]
    assert found["counts"][GUILD] == 1 and found["count"] == 1
    stale = {int(row["id"]) for row in await guides.stale_media(db, GUILD)}
    assert stale == {shot}
    assert other not in stale and fresh not in stale


async def test_mark_all_stale_takes_every_picture_a_release_never_could(bot, db):
    """The cutover: a mode flip and a channel rename are not deploys, so nothing else reaches
    a shot whose own feature has not changed."""
    await guides.seed_guides(db, GUILD)
    golive = await guides.get_guide(db, GUILD, "golive-announce")
    poll = await guides.get_guide(db, GUILD, "poll-vote-make")
    shot = await guides.save_media(
        bot, GUILD, golive["id"], b"\x89PNG\r\n\x1a\n" + b"\x00" * 40, shot_release="v111"
    )
    other = await guides.save_media(
        bot, GUILD, poll["id"], b"\x89PNG\r\n\x1a\n" + b"\x00" * 40, shot_release="v111"
    )

    assert await guides.mark_all_stale(db, GUILD) == 2

    stale = {int(row["id"]) for row in await guides.stale_media(db, GUILD)}
    assert stale == {shot, other}
    assert all(row["stale_since"] for row in await guides.stale_media(db, GUILD))


async def test_mark_all_stale_counts_only_what_was_not_marked_already(bot, db):
    await guides.seed_guides(db, GUILD)
    golive = await guides.get_guide(db, GUILD, "golive-announce")
    first = await guides.save_media(bot, GUILD, golive["id"], b"\x89PNG\r\n\x1a\n" + b"\x00" * 40)
    await guides.mark_all_stale(db, GUILD)
    was = [row["stale_since"] for row in await guides.stale_media(db, GUILD)]
    second = await guides.save_media(bot, GUILD, golive["id"], b"\x89PNG\r\n\x1a\n" + b"\x00" * 40)

    assert await guides.mark_all_stale(db, GUILD) == 1
    assert await guides.mark_all_stale(db, GUILD) == 0

    rows = {int(row["id"]): row["stale_since"] for row in await guides.stale_media(db, GUILD)}
    assert sorted(rows) == sorted([first, second])
    assert rows[first] == was[0]


async def test_mark_all_stale_leaves_another_guilds_pictures_alone(bot, db):
    await guides.seed_guides(db, GUILD)
    await guides.seed_guides(db, OTHER_GUILD)
    mine = await guides.get_guide(db, GUILD, "golive-announce")
    theirs = await guides.get_guide(db, OTHER_GUILD, "golive-announce")
    await guides.save_media(bot, GUILD, mine["id"], b"\x89PNG\r\n\x1a\n" + b"\x00" * 40)
    await guides.save_media(bot, OTHER_GUILD, theirs["id"], b"\x89PNG\r\n\x1a\n" + b"\x00" * 40)

    assert await guides.mark_all_stale(db, GUILD) == 1
    assert len(await guides.stale_media(db, OTHER_GUILD)) == 0


async def test_the_same_release_is_read_once_and_leaves_one_row(bot, db):
    await guides.seed_guides(db, GUILD)
    write_release(bot, "v112", ["golive"])

    assert await guides.reconcile_releases(bot) is not None
    assert await guides.reconcile_releases(bot) is None
    found = await rows(db, "SELECT * FROM guide_releases")
    assert len(found) == 1
    assert found[0]["release"] == "v112" and found[0]["commit"] == "abc1234"
    assert json.loads(found[0]["changed_features"]) == ["golive"]


async def test_a_release_file_that_is_not_json_is_a_warning_and_not_a_crash(bot, db):
    guides.release_path(bot).write_text("{not json", encoding="utf-8")

    assert await guides.reconcile_releases(bot) is None


# --- what /help links to ----------------------------------------------------------------------


async def test_links_for_names_every_published_guide_by_its_command(bot, db):
    await guides.seed_guides(db, GUILD)

    found = await guides.links_for(bot, GUILD)

    member_commands = {
        one["command"]
        for one in guides.seed_entries()
        if one["audience"] == "member" and one["command"]
    }
    assert len(found) == len(member_commands) == 11
    assert found["/pings"] == "https://blackbloc.test/guides.html#pings-follow"
    assert found["/golive"] == "https://blackbloc.test/guides.html#golive-announce"
    assert "/settings" not in found, "a staff guide is not a link a member can follow"


async def test_an_unpublished_guide_is_not_linked_and_neither_is_one_with_no_command(bot, db):
    await guides.seed_guides(db, GUILD)
    await db.conn.execute(
        "UPDATE guides SET published = 0 WHERE guild_id = ? AND slug = 'golive-announce'", (GUILD,)
    )
    await db.conn.commit()

    found = await guides.links_for(bot, GUILD)

    assert "/golive" not in found


async def test_links_for_is_empty_while_guides_are_off(bot, db):
    await guides.seed_guides(db, GUILD)
    await bot.store.set(GUILD, "guides_mode", "off")

    assert await guides.links_for(bot, GUILD) == {}


async def test_one_command_may_only_have_one_published_guide(bot, db):
    import sqlite3

    await guides.seed_guides(db, GUILD)

    with pytest.raises(sqlite3.IntegrityError):
        await guides.create_guide(
            db,
            GUILD,
            slug="golive-second",
            title="Another",
            goal="A goal.",
            feature="golive",
            command="/golive",
            published=True,
        )


async def test_two_guilds_keep_their_own_guides(bot, db):
    await guides.seed_guides(db, GUILD)
    await guides.seed_guides(db, OTHER_GUILD)

    assert await guides.count_guides(db, GUILD) == 27
    assert await guides.count_guides(db, OTHER_GUILD) == 27
    assert (await guides.get_guide(db, OTHER_GUILD, "golive-announce"))["published"] == 1


# --- the rows ---------------------------------------------------------------------------------


async def test_put_steps_adds_removes_and_reorders_in_one_write(bot, db):
    guide_id = await guides.create_guide(
        db, GUILD, slug="mine", title="Mine", goal="A goal.", feature="core"
    )
    first = await guides.put_steps(
        db,
        guide_id,
        [{"do_text": "Press **A**."}, {"do_text": "Press **B**."}],
    )
    steps = await guides.steps_of(db, guide_id)
    swapped = await guides.put_steps(
        db,
        guide_id,
        [
            {"id": int(steps[1]["id"]), "do_text": "Press **B**."},
            {"id": int(steps[0]["id"]), "do_text": "Press **A** again."},
        ],
    )

    assert first == {"added": 2, "removed": 0, "changed": 0}
    assert swapped["added"] == 0 and swapped["removed"] == 0 and swapped["changed"] == 2
    assert [row["do_text"] for row in await guides.steps_of(db, guide_id)] == [
        "Press **B**.",
        "Press **A** again.",
    ]

    gone = await guides.put_steps(db, guide_id, [{"do_text": "Press **B**."}])
    assert gone["removed"] == 2 and gone["added"] == 1


async def test_a_diff_summary_says_what_moved(bot, db):
    said = guides.diff_summary(
        {"added": 1, "removed": 0, "changed": 2},
        {"added": 0, "removed": 0, "changed": 1},
        {"added": 0, "removed": 0, "changed": 0},
    )

    assert said == "steps +1 −0 ~2, faults +0 −0 ~1, facts +0 −0 ~0"


def test_a_title_becomes_a_slug_a_url_can_carry():
    assert guides.slugify("Get your stream announced in #live-now!") == (
        "get-your-stream-announced-in-live-now"
    )
    assert guides.slugify("  ") == ""
    assert guides.slugify("It’s a guide") == "its-a-guide"


# --- pictures ---------------------------------------------------------------------------------


def test_a_pictures_size_is_read_from_its_header_because_pillow_is_not_installed():
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 8 + (1600).to_bytes(4, "big") + (900).to_bytes(4, "big")

    assert guides.picture_size(png) == (1600, 900)
    assert guides.picture_size(b"not a picture at all") is None
    assert guides.media_kind("shot.PNG") == "image/png"
    assert guides.media_kind("shot.gif") is None


async def test_a_saved_picture_lands_beside_the_database_and_is_dropped_with_its_row(bot, db):
    guide_id = await guides.create_guide(
        db, GUILD, slug="mine", title="Mine", goal="A goal.", feature="core"
    )
    raw = b"\x89PNG\r\n\x1a\n" + b"\x00" * 8 + (10).to_bytes(4, "big") + (20).to_bytes(4, "big")
    media_id = await guides.save_media(bot, GUILD, guide_id, raw, caption="the card")

    row = await guides.get_media(db, GUILD, media_id)
    path = guides.media_path(bot, row["file"])
    assert path.read_bytes() == raw
    assert path.parent == guides.media_root(bot)
    assert (row["width"], row["height"], row["bytes"]) == (10, 20, len(raw))
    assert row["caption"] == "the card" and row["source"] == "capture"

    await guides.drop_media(bot, row)
    assert await guides.get_media(db, GUILD, media_id) is None
    assert not path.exists()


def test_the_seed_is_read_from_the_package_and_never_reworded():
    raw = guides.SEED_FILE.read_text(encoding="utf-8")

    assert json.loads(raw)["guides"][0]["slug"] == "front-door"
    assert guides.load_seed()["version"] >= 1
    assert guides.seed_hash({"a": 1}) != guides.seed_hash({"a": 2})


def test_the_module_reads_no_environment_of_its_own():
    assert not hasattr(guides, "os")
    assert isinstance(guides.FEATURE_PATHS, dict)
    assert isinstance(guides.PROBE_LABELS, dict)
    assert set(guides.PROBE_LABELS) == set(guides.PROBES)


def test_a_fake_guild_is_all_the_names_resolver_needs():
    assert guides.named_value(SimpleNamespace(get_member=lambda _: None), "nothing") == "nothing"


# --- G2: what the page and the deploy read ------------------------------------------------------


async def test_right_now_names_the_test_channel_and_counts_the_modes(bot):
    found = guides.right_now(bot, bot.guilds[0])

    assert found["test_mode"] is True
    assert found["test_channel"] == "blackbloc-logs"
    assert found["on"] + found["shadow"] + found["off"] > 10


async def test_right_now_says_off_without_naming_a_channel_nobody_is_in(bot):
    bot.settings.test_mode = False

    found = guides.right_now(bot, bot.guilds[0])

    assert found["test_mode"] is False and found["test_channel"] is None


async def test_a_feature_mode_is_read_from_the_registry_and_never_guessed(bot):
    await bot.store.set(GUILD, "golive_mode", "shadow", by=1)

    assert guides.feature_mode(bot.store, GUILD, "golive") == "shadow"
    assert guides.feature_mode(bot.store, GUILD, "guides") == "on"
    assert guides.feature_mode(bot.store, GUILD, "nothing_like_this") is None


async def test_whether_somethings_off_files_a_request_is_the_key_and_not_a_constant(bot):
    assert guides.fault_files_request(bot.store, GUILD) is True

    await bot.store.set(GUILD, "guides_fault_files_request", False, by=1)

    assert guides.fault_files_request(bot.store, GUILD) is False


def test_release_json_is_what_the_deploy_step_writes_and_the_boot_reads(bot):
    payload = guides.release_payload(
        ["black_bloc/golive.py", "site/public/assets/page-guides.js"], "v111", "abc1234"
    )

    assert payload == {
        "release": "v111",
        "commit": "abc1234",
        "changed_features": ["golive", "guides"],
    }

    guides.release_path(bot).write_text(json.dumps(payload), encoding="utf-8")
    assert guides.read_release(bot) == payload


def test_the_next_release_is_one_past_the_last_line_of_the_deploys_log():
    line = "2026-09-11T10:14:50-07:00  black-bloc  9c6201d  by=deploy.ps1  v110: EVENT ROOMS"

    assert guides.next_release(line) == "v111"
    assert guides.next_release("a line with v9 in it") == "v10"
    assert guides.next_release("nothing numbered here") is None
