from types import SimpleNamespace

import pytest

from black_bloc import channel_drafts
from black_bloc.channel_drafts import (
    DRAFT,
    NONE,
    REWRITTEN,
    USED,
    effective,
    get_draft,
    load_seed,
    no_note,
    reset_draft,
    review_counts,
    save_wording,
    seed_and_log,
    seed_drafts,
    use_draft,
)
from black_bloc.channel_notes import NOTE_CHARS, get_note, notes_for, set_note
from black_bloc.config import load_settings
from black_bloc.logkinds import VIA_WEBSITE
from black_bloc.settings_store import SettingsStore

GUILD = 7
ACTOR = 900
GENERAL = 1411816390414962700
SPEED = 1076003845232148580
WELCOME = 1285369365071527997
LOOSE = 55


def text(channel_id, name):
    return SimpleNamespace(id=channel_id, name=name)


class Guild:
    def __init__(self):
        self.id = GUILD
        self.text_channels = [
            text(GENERAL, "general-chat"),
            text(SPEED, "speed-and-pbs"),
            text(WELCOME, "welcome"),
            text(LOOSE, "made-after-the-catalog"),
        ]

    def get_channel(self, channel_id):
        return None


class Bot:
    def __init__(self, db, store):
        self.db = db
        self.store = store
        self.guild = Guild()
        self.guilds = [self.guild]

    def get_channel(self, channel_id):
        return None


@pytest.fixture
async def bot(db, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    store = SettingsStore(db, load_settings(_env_file=None, test_mode=True))
    await store.load()
    return Bot(db, store)


@pytest.fixture
def actor():
    return SimpleNamespace(id=ACTOR, display_name="Lead", mention=f"<@{ACTOR}>")


@pytest.fixture
async def seeded(bot):
    await seed_drafts(bot.db, bot.guild)
    return bot


async def kinds(db):
    cur = await db.conn.execute("SELECT kind FROM action_log ORDER BY id")
    return [row["kind"] for row in await cur.fetchall()]


def draft_of(channel_id):
    return load_seed()[str(channel_id)]["draft"]


def test_the_seed_is_the_catalog_ninety_four_rows_two_final_and_every_draft_fits():
    seed = load_seed()

    assert len(seed) == 94
    assert sorted(key for key, one in seed.items() if one["final"]) == [
        str(SPEED),
        str(GENERAL),
    ]
    assert all(one["name"].startswith("#") and one["draft"] for one in seed.values())
    assert max(len(one["draft"]) for one in seed.values()) <= NOTE_CHARS


def test_an_unreadable_seed_is_an_empty_seed(monkeypatch, tmp_path):
    monkeypatch.setattr(channel_drafts, "SEED_FILE", tmp_path / "gone.json")

    assert load_seed() == {}


async def test_the_seed_inserts_only_the_channels_this_guild_has(bot):
    made, noted = await seed_drafts(bot.db, bot.guild)

    rows = await channel_drafts.drafts_for(bot.db, GUILD)
    assert (made, noted) == (3, 2)
    assert set(rows) == {GENERAL, SPEED, WELCOME}
    assert rows[WELCOME]["status"] == DRAFT and rows[WELCOME]["decided_at"] is None
    assert rows[GENERAL]["status"] == USED


async def test_the_two_finals_become_notes_on_the_first_seed_only(bot):
    await seed_drafts(bot.db, bot.guild)

    notes = await notes_for(bot.db, GUILD)
    assert notes == {GENERAL: draft_of(GENERAL), SPEED: draft_of(SPEED)}

    await bot.db.conn.execute("DELETE FROM channel_notes WHERE channel_id = ?", (GENERAL,))
    await bot.db.conn.commit()
    assert await seed_drafts(bot.db, bot.guild) == (0, 0)
    assert GENERAL not in await notes_for(bot.db, GUILD)


async def test_a_note_staff_wrote_before_the_seed_is_kept(bot):
    await set_note(bot.db, GUILD, GENERAL, "Staff said this first.", by=ACTOR)

    assert await seed_drafts(bot.db, bot.guild) == (3, 1)
    assert (await get_note(bot.db, GUILD, GENERAL))["note"] == "Staff said this first."


async def test_the_seed_never_overwrites_a_decided_row(seeded, actor):
    await save_wording(seeded, seeded.guild, actor, WELCOME, "Where the rules live.")

    await seed_drafts(seeded.db, seeded.guild)

    row = await get_draft(seeded.db, GUILD, WELCOME)
    assert row["status"] == REWRITTEN and row["decided_by"] == ACTOR
    assert (await get_note(seeded.db, GUILD, WELCOME))["note"] == "Where the rules live."


async def test_a_seed_that_made_rows_logs_once_and_a_second_logs_nothing(bot):
    assert await seed_and_log(bot, bot.guild) == 3
    assert await seed_and_log(bot, bot.guild) == 0

    assert await kinds(bot.db) == ["chat.channel_drafts_seeded"]


async def test_use_writes_the_draft_as_the_note_and_logs_once(seeded, actor):
    outcome = await use_draft(seeded, seeded.guild, actor, WELCOME, via=VIA_WEBSITE)

    assert outcome.ok and "#welcome" in outcome.message and "now its note" in outcome.message
    assert (await get_note(seeded.db, GUILD, WELCOME))["note"] == draft_of(WELCOME)
    row = await get_draft(seeded.db, GUILD, WELCOME)
    assert (row["status"], row["decided_by"]) == (USED, ACTOR) and row["decided_at"]
    assert await kinds(seeded.db) == ["web.chat.channel_draft_used"]


async def test_saving_the_draft_word_for_word_counts_as_used(seeded, actor):
    outcome = await save_wording(seeded, seeded.guild, actor, WELCOME, f"  {draft_of(WELCOME)} ")

    assert outcome.ok and "now its note" in outcome.message
    assert (await get_draft(seeded.db, GUILD, WELCOME))["status"] == USED
    assert await kinds(seeded.db) == ["chat.channel_draft_used"]


async def test_saving_other_words_is_rewritten(seeded, actor):
    outcome = await save_wording(seeded, seeded.guild, actor, WELCOME, "Rules and roles.")

    assert outcome.ok and "is saved" in outcome.message
    assert (await get_draft(seeded.db, GUILD, WELCOME))["status"] == REWRITTEN
    assert await kinds(seeded.db) == ["chat.channel_draft_rewritten"]


async def test_a_blank_save_on_a_drafted_channel_is_no_note(seeded, actor):
    await use_draft(seeded, seeded.guild, actor, WELCOME)

    outcome = await save_wording(seeded, seeded.guild, actor, WELCOME, "   ")

    assert outcome.ok and "no note now" in outcome.message
    assert await get_note(seeded.db, GUILD, WELCOME) is None
    assert (await get_draft(seeded.db, GUILD, WELCOME))["status"] == NONE
    assert await kinds(seeded.db) == ["chat.channel_draft_used", "chat.channel_draft_none"]


async def test_no_note_twice_says_nothing_changed_the_second_time(seeded, actor):
    first = await no_note(seeded, seeded.guild, actor, WELCOME)
    second = await no_note(seeded, seeded.guild, actor, WELCOME)

    assert first.ok and "no note now" in first.message
    assert second.ok and "had no note" in second.message
    assert await kinds(seeded.db) == ["chat.channel_draft_none"]


async def test_reset_clears_the_note_and_the_decision(seeded, actor):
    await save_wording(seeded, seeded.guild, actor, WELCOME, "Rules and roles.")

    outcome = await reset_draft(seeded, seeded.guild, actor, WELCOME, via=VIA_WEBSITE)

    assert outcome.ok and "back to its draft" in outcome.message
    assert await get_note(seeded.db, GUILD, WELCOME) is None
    row = await get_draft(seeded.db, GUILD, WELCOME)
    assert (row["status"], row["decided_by"], row["decided_at"]) == (DRAFT, None, None)
    assert await kinds(seeded.db) == [
        "chat.channel_draft_rewritten",
        "web.chat.channel_draft_reset",
    ]


async def test_resetting_an_undecided_draft_writes_no_row(seeded, actor):
    outcome = await reset_draft(seeded, seeded.guild, actor, WELCOME)

    assert outcome.ok
    assert await kinds(seeded.db) == []


async def test_a_channel_without_a_draft_keeps_the_plain_note_path(seeded, actor):
    saved = await save_wording(seeded, seeded.guild, actor, LOOSE, "A new channel.")
    cleared = await no_note(seeded, seeded.guild, actor, LOOSE)
    used = await use_draft(seeded, seeded.guild, actor, LOOSE)
    reset = await reset_draft(seeded, seeded.guild, actor, LOOSE)

    assert saved.ok and cleared.ok
    for refused in (used, reset):
        assert (refused.ok, refused.status, refused.code) == (False, 404, "no_draft")
        assert "#made-after-the-catalog" in refused.message
    assert await kinds(seeded.db) == ["chat.channel_note_set", "chat.channel_note_cleared"]


async def test_a_channel_that_is_not_here_is_refused_by_every_move(seeded, actor):
    for move in (use_draft, no_note, reset_draft):
        outcome = await move(seeded, seeded.guild, actor, 999)
        assert (outcome.ok, outcome.status, outcome.code) == (False, 404, "no_such_channel")
    outcome = await save_wording(seeded, seeded.guild, actor, 999, "x")
    assert outcome.code == "no_such_channel"
    assert await kinds(seeded.db) == []


async def test_a_wording_over_the_cap_is_refused_and_nothing_moves(seeded, actor):
    outcome = await save_wording(seeded, seeded.guild, actor, WELCOME, "x" * 250)

    assert (outcome.ok, outcome.status, outcome.code) == (False, 422, "note_too_long")
    assert (await get_draft(seeded.db, GUILD, WELCOME))["status"] == DRAFT
    assert await kinds(seeded.db) == []


async def test_staff_wording_for_the_draft_moves_is_used(seeded, actor):
    await seeded.store.set(GUILD, "chat_channel_draft_used", "Done: #{channel}")

    outcome = await use_draft(seeded, seeded.guild, actor, WELCOME)

    assert outcome.message == "Done: #welcome"


@pytest.mark.parametrize(
    ("status", "note", "wanted"),
    [
        (DRAFT, None, DRAFT),
        (DRAFT, "the draft", USED),
        (DRAFT, "other words", REWRITTEN),
        (USED, None, NONE),
        (REWRITTEN, None, NONE),
        (NONE, None, NONE),
        (NONE, "other words", REWRITTEN),
    ],
)
def test_the_note_is_the_truth_and_the_status_says_why_it_is_absent(status, note, wanted):
    assert effective(status, "the draft", note) == wanted


def test_review_counts_skip_channels_that_were_never_drafted():
    rows = [
        {"draft": "a", "status": DRAFT},
        {"draft": "b", "status": USED},
        {"draft": "c", "status": NONE},
        {"draft": None, "status": None},
    ]

    assert review_counts(rows) == {"total": 3, "reviewed": 2, "drafts_left": 1}
