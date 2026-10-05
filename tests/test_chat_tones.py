import json
import random
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from black_bloc import chat_panel, chat_tones, personas
from black_bloc.chat_voice import voice_row
from black_bloc.config import load_settings
from black_bloc.logkinds import VIA_WEBSITE
from black_bloc.settings_store import SettingsStore

GUILD = 7
ACTOR = 900
NOW = datetime(2026, 10, 5, 19, 0, tzinfo=UTC)


class PeopleGuild:
    def __init__(self):
        self.id = GUILD
        self.members = {
            21: SimpleNamespace(id=21, display_name="Nia", bot=False),
            99: SimpleNamespace(id=99, display_name="A bot", bot=True),
        }

    def get_channel(self, channel_id):
        return None

    def get_member(self, user_id):
        return self.members.get(int(user_id))


class FakeBot:
    def __init__(self, db, store, guild):
        self.db = db
        self.store = store
        self.guild = guild
        self.guilds = [guild]

    def get_channel(self, channel_id):
        return None


@pytest.fixture
async def people(db, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    store = SettingsStore(db, load_settings(_env_file=None, test_mode=True))
    await store.load()
    await personas.sync_tropes(db)
    return FakeBot(db, store, PeopleGuild())


@pytest.fixture
def actor():
    return SimpleNamespace(id=ACTOR, display_name="Lead", mention=f"<@{ACTOR}>")


async def kinds(db):
    cur = await db.conn.execute("SELECT kind, details FROM action_log ORDER BY id")
    return [(row["kind"], row["details"]) for row in await cur.fetchall()]


async def detailed(db):
    return [(kind, json.loads(details or "{}")) for kind, details in await kinds(db)]


async def test_a_starting_tone_from_discord_is_one_row_one_log_and_a_keyed_sentence(
    people, actor, db
):
    found = await chat_tones.start_voice(people, people.guild, actor, 21, "noir", now=NOW)

    kept = await voice_row(db, GUILD, 21)
    assert found.ok and found.value == "noir"
    assert found.message == "**Nia** starts from **noir** from their next answer on."
    assert (kept["tone"], kept["how"], kept["set_by"], kept["pinned"]) == (
        "noir", "set", ACTOR, None)
    assert kept["moved_at"] == NOW.isoformat()
    assert await detailed(db) == [
        ("chat.voice_set", {"member": "21", "from": None, "tone": "noir", "via": "discord"})]


async def test_a_reroll_is_seeded_never_the_same_tone_and_logged_from_either_door(
    people, actor, db
):
    await chat_tones.start_voice(people, people.guild, actor, 21, "noir", now=NOW)

    found = await chat_tones.reroll_voice(
        people, people.guild, actor, 21, via=VIA_WEBSITE, rng=random.Random(3), now=NOW)

    kept = await voice_row(db, GUILD, 21)
    assert found.ok and found.value != "noir" and kept["tone"] == found.value
    assert (kept["how"], kept["moved_from"], kept["settled"]) == ("rolled", "noir", 0)
    assert found.message.startswith("Rolled **") and "for **Nia**" in found.message
    assert [kind for kind, _ in await kinds(db)] == ["chat.voice_set", "web.chat.voice_rerolled"]


async def test_a_pinned_member_keeps_the_pin_whatever_is_rolled_or_set(people, actor, db):
    await chat_panel.pin_voice(people, people.guild, actor, 21, "noir")

    rolled = await chat_tones.reroll_voice(people, people.guild, actor, 21)
    started = await chat_tones.start_voice(people, people.guild, actor, 21, "warm")

    assert (rolled.ok, rolled.status, rolled.code) == (False, 409, "voice_is_pinned")
    assert started.message == (
        "**Nia** is pinned to **noir**, so nothing was changed. Clear the pin first.")
    assert (await voice_row(db, GUILD, 21))["tone"] is None
    assert [kind for kind, _ in await kinds(db)] == ["chat.voice_pinned"]


async def test_a_start_or_a_reroll_for_a_stranger_or_a_tone_that_is_off_is_refused(
    people, actor, db
):
    await personas.set_enabled(db, "noir", False)

    for who in (99, 4242):
        assert (await chat_tones.reroll_voice(people, people.guild, actor, who)).status == 404
        held = await chat_tones.start_voice(people, people.guild, actor, who, "warm")
        assert held.status == 404
    off = await chat_tones.start_voice(people, people.guild, actor, 21, "noir")
    blank = await chat_tones.start_voice(people, people.guild, actor, 21, "pool")

    assert off.status == blank.status == 422 and "switched off" in off.message
    assert await kinds(db) == []


async def test_a_reroll_with_no_tone_on_says_so(people, actor, db):
    await db.conn.execute("UPDATE personality_tropes SET enabled = 0")

    found = await chat_tones.reroll_voice(people, people.guild, actor, 21)

    assert (found.status, found.code) == (409, "no_tones_on")
    assert "No tone is switched on" in found.message


def a_role(people, *ids):
    people.guild.members.update(
        {uid: SimpleNamespace(id=uid, display_name=f"M{uid}", bot=False) for uid in ids}
    )
    role = SimpleNamespace(
        id=555,
        name="Aunties / Uncles",
        members=[*(people.guild.members[uid] for uid in ids), people.guild.members[99]],
    )
    people.guild.get_role = lambda role_id: role if int(role_id) == 555 else None
    return role


async def test_a_roll_for_a_role_skips_the_pinned_the_toned_and_the_bots(people, actor, db):
    a_role(people, 31, 32, 33)
    await chat_panel.pin_voice(people, people.guild, actor, 31, "noir")
    await chat_tones.start_voice(people, people.guild, actor, 32, "warm", now=NOW)

    found = await chat_tones.roll_role(
        people, people.guild, actor, 555, rng=random.Random(1), now=NOW)

    assert found.ok
    assert [one["user_id"] for one in found.value["rolled"]] == [33]
    assert [(one["user_id"], one["tone"]) for one in found.value["pinned"]] == [(31, "noir")]
    assert found.value["kept"] == 1
    assert found.message == (
        "Rolled a tone for **1** member(s) of **Aunties / Uncles**. Left alone: **1** pinned, "
        "**1** who already had a tone.")
    assert (await voice_row(db, GUILD, 32))["tone"] == "warm"
    assert (await voice_row(db, GUILD, 31))["tone"] is None
    assert await voice_row(db, GUILD, 99) is None
    rolled = await voice_row(db, GUILD, 33)
    assert (rolled["tone"], rolled["how"], rolled["set_by"]) == (
        found.value["rolled"][0]["tone"], "rolled", ACTOR)
    last = (await detailed(db))[-1]
    assert last[0] == "chat.voice_role_rolled"
    assert (last[1]["rolled"], last[1]["pinned"], last[1]["kept"], last[1]["everyone"]) == (
        1, 1, 1, False)
    assert chat_tones.role_lines(people.store, GUILD, found.value) == [
        f"<@33> — **{found.value['rolled'][0]['label']}**",
        "<@31> — pinned to **noir**, left alone",
    ]


async def test_a_roll_for_everyone_in_a_role_gives_the_toned_a_new_one(people, actor, db):
    a_role(people, 31, 32)
    await chat_panel.pin_voice(people, people.guild, actor, 31, "noir")
    await chat_tones.start_voice(people, people.guild, actor, 32, "warm", now=NOW)

    found = await chat_tones.roll_role(
        people, people.guild, actor, 555, everyone=True, via=VIA_WEBSITE,
        rng=random.Random(1), now=NOW)

    assert [one["user_id"] for one in found.value["rolled"]] == [32]
    assert found.value["rolled"][0]["tone"] != "warm" and found.value["kept"] == 0
    assert [one["user_id"] for one in found.value["pinned"]] == [31]
    assert (await kinds(db))[-1][0] == "web.chat.voice_role_rolled"


async def test_a_roll_for_a_role_that_is_gone_or_with_no_tone_on_is_refused(people, actor, db):
    a_role(people, 31)

    gone = await chat_tones.roll_role(people, people.guild, actor, 4242)
    odd = await chat_tones.roll_role(people, people.guild, actor, "nothing")
    await db.conn.execute("UPDATE personality_tropes SET enabled = 0")
    off = await chat_tones.roll_role(people, people.guild, actor, 555)

    assert (gone.status, odd.status, off.status) == (404, 404, 409)
    assert "not in this server" in gone.message and "No tone is switched on" in off.message
    assert await kinds(db) == []
