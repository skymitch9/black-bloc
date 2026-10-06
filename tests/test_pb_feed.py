# ruff: noqa: F401, F811
from datetime import timedelta
from types import SimpleNamespace

import discord
import pytest

from black_bloc import pb_feed, pb_store
from black_bloc.settings_panel import reachable_on_the_panel
from black_bloc.settings_store import (
    CORE_KEYS,
    KEY_CHOICES,
    KEY_HELP,
    KEY_MAX,
    KEY_MIN,
    KEY_TYPES,
    PB_FEED_DEFAULTS,
    PB_FEED_KEYS,
    PB_FEED_WORDS,
    SettingError,
    namespace_of,
)
from tests.test_pb_looks import ADA, BEA, CAL, GUILD, NOW, PBS, bot, guild
from tests.test_pb_looks import best as a_best

SPEEDRUN_LIMIT_PER_MINUTE = 100


def row(state, *, source="auto", login="zfg1", checked=None, looked=None, runner="s1"):
    return {
        "state": state,
        "source": source if state == pb_store.MATCHED else None,
        "twitch_login": login,
        "checked_at": checked.isoformat() if checked else None,
        "looked_at": looked.isoformat() if looked else None,
        "src_user_id": runner if state == pb_store.MATCHED else None,
        "opted_out_at": None,
    }


class Store:
    def __init__(self, **values):
        self.values = PB_FEED_DEFAULTS | values

    def get(self, guild_id, key):
        return self.values.get(key)


def test_the_feature_ships_in_shadow_with_no_channel_and_no_ping(bot):
    assert PB_FEED_DEFAULTS["pb_feed_mode"] == "shadow"
    assert KEY_CHOICES["pb_feed_mode"] == ("off", "shadow", "on")
    assert bot.store.get(GUILD, "pb_feed_channel_id") is None
    assert bot.store.get(GUILD, "pb_feed_ping_role_id") is None
    assert bot.store.get(GUILD, "pb_feed_shadow_channel_id") is None
    assert bot.store.get(GUILD, "pb_feed_auto_match") is True
    assert pb_feed.mode_of(bot.store, GUILD) == "shadow"
    for key, shipped in PB_FEED_DEFAULTS.items():
        assert bot.store.get(GUILD, key) == shipped


def test_every_key_is_under_core_typed_explained_and_reachable_from_settings():
    assert len(PB_FEED_KEYS) == len(set(PB_FEED_KEYS)) == 49
    for key in PB_FEED_KEYS:
        assert key in CORE_KEYS and namespace_of(key) == "core", key
        assert KEY_TYPES.get(key) and KEY_HELP.get(key), key
        assert reachable_on_the_panel(key), key
    assert KEY_TYPES["pb_feed_channel_id"] == KEY_TYPES["pb_feed_shadow_channel_id"] == "channel"
    assert KEY_TYPES["pb_feed_ping_role_id"] == "role"


def test_the_interval_floor_keeps_the_feed_far_inside_the_documented_limit():
    assert PB_FEED_DEFAULTS["pb_feed_interval_minutes"] == 60
    assert (KEY_MIN["pb_feed_interval_minutes"], KEY_MAX["pb_feed_interval_minutes"]) == (15, 1440)
    assert pb_feed.TICK_CAP * 20 <= SPEEDRUN_LIMIT_PER_MINUTE
    assert KEY_MAX["pb_feed_cycle_requests"] / KEY_MIN["pb_feed_interval_minutes"] < (
        SPEEDRUN_LIMIT_PER_MINUTE / 2
    )


async def test_a_template_refuses_a_field_it_does_not_have(bot):
    with pytest.raises(SettingError):
        await bot.store.set(GUILD, "pb_feed_post_text", "{member} did {nothing}")

    await bot.store.set(GUILD, "pb_feed_post_text", "{name} — {game} {category} {time}")
    assert pb_feed.said(
        bot.store, GUILD, "pb_feed_post_text", name="Ada", game="G", category="C", time="1:00"
    ) == "Ada — G C 1:00"


def test_every_shipped_sentence_fills_from_its_own_fields():
    store = Store()
    for key, (_, fields, _) in PB_FEED_WORDS.items():
        assert pb_feed.said(store, GUILD, key, **dict.fromkeys(fields, "x")), key


def test_an_unknown_mode_reads_as_off():
    assert pb_feed.mode_of(Store(pb_feed_mode="loud"), GUILD) == "off"


@pytest.mark.parametrize(
    ("seconds", "words"),
    [
        (2129, "35:29"),
        (616.9, "10:16.900"),
        (59.12, "0:59.120"),
        (3723, "1:02:03"),
        (3600.001, "1:00:00.001"),
        (0.999, "0:00.999"),
        (59.9996, "1:00"),
    ],
)
def test_a_time_reads_the_way_a_leaderboard_writes_it(seconds, words):
    assert pb_feed.time_words(seconds) == words


def test_backoff_doubles_from_five_minutes_and_stops_at_six_hours():
    assert [pb_feed.backoff_minutes(at) for at in range(1, 9)] == [
        5,
        10,
        20,
        40,
        80,
        160,
        320,
        360,
    ]
    assert pb_feed.backoff_minutes(500) == 360 and pb_feed.backoff_minutes(0) == 5


@pytest.mark.parametrize(
    ("people", "interval", "take"),
    [(0, 60, 0), (1, 60, 1), (60, 60, 1), (61, 60, 2), (120, 60, 2), (30, 15, 2), (5000, 15, 5)],
)
def test_a_tick_takes_its_share_of_the_interval_and_never_more_than_the_cap(
    people, interval, take
):
    assert pb_feed.per_tick(people, interval) == take


def test_a_post_escapes_markdown_in_names_speedrun_supplies(guild):
    fresh = a_best("r1", game="**Bold** Game", category="_Any%_", place=None)

    fields = pb_feed.post_fields(Store(), GUILD, guild.get_member(ADA), ADA, "zfg", fresh)

    assert fields["game"] == discord.utils.escape_markdown("**Bold** Game")
    assert fields["category"].startswith("\\_")
    assert (fields["member"], fields["name"], fields["runner"]) == (f"<@{ADA}>", "Ada", "zfg")
    assert (fields["place"], fields["place_line"]) == ("", "")


def test_a_member_who_left_is_still_named_by_a_mention():
    fields = pb_feed.post_fields(Store(), GUILD, None, CAL, "cal", a_best("r1"))

    assert (fields["member"], fields["name"]) == (f"<@{CAL}>", "cal")
    assert fields["place_line"] == " — #3 on the leaderboard"


def test_only_an_https_link_becomes_the_embeds_link_and_button():
    store = Store()
    risky = a_best("r1")
    object.__setattr__(risky, "weblink", "javascript:alert(1)")

    assert pb_feed.post_embed(store, GUILD, None, ADA, "zfg", risky).url is None
    assert pb_feed.link_view(store, GUILD, "javascript:alert(1)") is None
    assert pb_feed.link_view(store, GUILD, "https://www.speedrun.com/r").children[0].label == (
        "Watch the run"
    )


async def test_the_rehearsal_line_names_the_real_channel_or_says_there_is_none(bot, guild):
    assert "nowhere yet" in pb_feed.rehearsal_line(bot, guild)

    await bot.store.set(GUILD, "pb_feed_channel_id", PBS)

    assert f"<#{PBS}>" in pb_feed.rehearsal_line(bot, guild)


def test_a_refused_send_is_worded_with_the_fix_and_no_bare_status():
    response = SimpleNamespace(status=403, reason="Forbidden")
    said = pb_feed.send_reason(discord.Forbidden(response, "Missing Permissions"))

    assert "Send Messages" in said and "Missing Permissions" in said
    assert "RuntimeError" in pb_feed.send_reason(RuntimeError("boom"))


def test_who_wants_a_lookup():
    wants = lambda found, login, auto=True: pb_feed.wants_lookup(  # noqa: E731
        found, login, auto=auto, now=NOW, rematch_days=7
    )

    assert wants(None, "zfg1") is True
    assert wants(None, None) is False
    assert wants(None, "zfg1", auto=False) is False
    assert wants(row(pb_store.MATCHED), "zfg1") is False
    assert wants(row(pb_store.OPTED_OUT), "zfg1") is False
    assert wants(row(pb_store.BLOCKED), "zfg1") is False
    assert wants(row(pb_store.NONE, checked=NOW - timedelta(days=6)), "zfg1") is False
    assert wants(row(pb_store.NONE, checked=NOW - timedelta(days=7)), "zfg1") is True
    assert wants(row(pb_store.NONE, checked=NOW, login="old"), "zfg1") is True
    assert wants(row(pb_store.NONE), "zfg1") is True


def test_only_an_automatic_match_follows_the_link():
    assert pb_feed.link_moved(row(pb_store.MATCHED, login="old"), "new") is True
    assert pb_feed.link_moved(row(pb_store.MATCHED, login="old"), None) is True
    assert pb_feed.link_moved(row(pb_store.MATCHED, login="same"), "same") is False
    assert pb_feed.link_moved(row(pb_store.MATCHED, source="staff", login="old"), "new") is False
    assert pb_feed.link_moved(row(pb_store.OPTED_OUT, login="old"), "new") is False
    assert pb_feed.link_moved(None, "new") is False


def test_a_look_is_due_once_the_interval_has_passed():
    due = lambda found: pb_feed.look_due(found, now=NOW, interval_minutes=60)  # noqa: E731

    assert due(row(pb_store.MATCHED)) is True
    assert due(row(pb_store.MATCHED, looked=NOW - timedelta(minutes=59))) is False
    assert due(row(pb_store.MATCHED, looked=NOW - timedelta(minutes=60))) is True
    assert due(row(pb_store.OPTED_OUT, looked=None)) is False
    assert due(row(pb_store.BLOCKED)) is False


def test_the_work_list_is_lookups_first_then_the_longest_overdue_and_only_people_here():
    rows = {
        ADA: row(pb_store.MATCHED, looked=NOW - timedelta(hours=2)),
        BEA: row(pb_store.MATCHED, looked=NOW - timedelta(hours=5), login="bea"),
        CAL: row(pb_store.MATCHED, looked=None, login="cal"),
        1: row(pb_store.OPTED_OUT),
        2: row(pb_store.BLOCKED),
        3: row(pb_store.MATCHED, looked=NOW - timedelta(minutes=5), login="three"),
    }
    links = {ADA: "zfg1", BEA: "bea", CAL: "cal", 1: "one", 2: "two", 3: "three", 4: "four"}
    here = {ADA, BEA, 1, 2, 3, 4}

    work = pb_feed.work_list(rows, links, here, store=Store(), guild_id=GUILD, now=NOW)

    assert work == [(pb_feed.LOOKUP, 4), (pb_feed.LOOK, BEA), (pb_feed.LOOK, ADA)]
    assert pb_feed.population(rows, links, here) == 4


def test_with_auto_match_off_nobody_is_looked_up_but_matches_are_still_looked_at():
    rows = {ADA: row(pb_store.MATCHED, source="staff", login=None)}

    store = Store(pb_feed_auto_match=False)

    work = pb_feed.work_list(rows, {BEA: "bea"}, {ADA, BEA}, store=store, guild_id=GUILD, now=NOW)

    assert work == [(pb_feed.LOOK, ADA)]


def test_a_display_name_or_a_runner_name_cannot_smuggle_a_link_into_a_post(guild):
    member = SimpleNamespace(mention=f"<@{ADA}>", display_name="[free nitro](https://evil.example)")
    fresh = a_best("r1", game="Play at https://evil.example now", category="[x](http://a.b) *y*")

    fields = pb_feed.post_fields(Store(), GUILD, member, ADA, "[a](https://b.example) _z_", fresh)

    for key in ("name", "runner", "game", "category"):
        assert "](" not in fields[key].replace("\\](", ""), key
        assert "://" not in fields[key], key
        assert "\\[" in fields[key] or key == "game", key
    assert fields["name"] == "\\[free nitro\\](https:\u200b//evil.example)"
    assert fields["runner"].endswith("\\_z\\_")
    embed = pb_feed.post_embed(
        Store(pb_feed_post_text="{name} / {runner} / {game} / {category}"), GUILD, member, ADA,
        "[a](https://b.example)", fresh,
    )
    assert "://" not in embed.description and "[free nitro](" not in embed.description


def test_the_shipped_request_cap_covers_300_members_and_stays_far_under_the_limit():
    cap = PB_FEED_DEFAULTS["pb_feed_cycle_requests"]
    interval = PB_FEED_DEFAULTS["pb_feed_interval_minutes"]

    assert pb_feed.per_tick(300, interval) * interval >= 300
    assert cap >= 300 + 60
    assert cap / interval <= SPEEDRUN_LIMIT_PER_MINUTE / 10
    assert KEY_MAX["pb_feed_cycle_requests"] / KEY_MIN["pb_feed_interval_minutes"] < 50


def test_no_sentence_a_member_reads_promises_a_post_unless_the_mode_is_on():
    promise = "is posted once"
    told = [key for key in PB_FEED_WORDS if key.startswith(("pb_feed_you_", "pb_feed_dm_"))]
    told += ["pb_feed_opted_in_said", "pb_feed_opted_out_said", "pb_feed_posting_shadow"]
    told += ["pb_feed_posting_off"]

    for key in told:
        assert promise not in PB_FEED_DEFAULTS[key], key
        assert "will be posted" not in PB_FEED_DEFAULTS[key], key
    assert promise in PB_FEED_DEFAULTS["pb_feed_posting_on"]


def test_an_opted_out_member_staff_unblocked_is_never_looked_up():
    found = row(pb_store.NONE) | {"opted_out_at": NOW.isoformat()}

    assert pb_feed.wants_lookup(found, "zfg1", auto=True, now=NOW, rematch_days=7) is False
