from types import SimpleNamespace

import pytest

from black_bloc import chat_panel, knowledge, personas
from black_bloc.chat_llm import LLM_MODE_KEY
from black_bloc.chat_panel import (
    ANSWER_OFF,
    ANSWER_ON,
    LLM_OFF,
    LLM_ON,
    MODE_KEY,
    PANEL_MOVES,
    PanelState,
    knowledge_buttons,
    mood_options,
    mood_refusal,
    note_buttons,
    panel_buttons,
    panel_minutes,
    panel_state,
    personality_buttons,
    read_limits,
    settings_buttons,
    site_page_url,
    status_lines,
    toggle_move,
)
from black_bloc.config import load_settings
from black_bloc.logkinds import VIA_DISCORD, VIA_WEBSITE
from black_bloc.settings_store import SettingsStore

GUILD = 7
LOG_CHANNEL = 222
ACTOR = 900
ORIGIN = "https://blackbloc.example"


class FakeGuild:
    def __init__(self):
        self.id = GUILD

    def get_channel(self, channel_id):
        return None


class FakeBot:
    def __init__(self, db, store, guild):
        self.db = db
        self.store = store
        self.guild = guild
        self.guilds = [guild]

    def get_channel(self, channel_id):
        return None


@pytest.fixture
async def bot(db, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    settings = load_settings(_env_file=None, test_mode=True, origin=ORIGIN)
    store = SettingsStore(db, settings)
    await store.load()
    await store.set(GUILD, "log_channel_id", LOG_CHANNEL)
    return FakeBot(db, store, FakeGuild())


@pytest.fixture
def actor():
    return SimpleNamespace(id=ACTOR, display_name="Lead", mention=f"<@{ACTOR}>")


@pytest.fixture
async def pool(db):
    await personas.sync_tropes(db)
    return await personas.list_tropes(db)


async def kinds(db):
    cur = await db.conn.execute("SELECT kind, details FROM action_log ORDER BY id")
    return [(row["kind"], row["details"]) for row in await cur.fetchall()]


def actions(view):
    return [move.action for move in view]


# --- the tables as data ---------------------------------------------------------------------


def test_the_root_renders_its_row_and_nothing_else():
    on = panel_buttons(PanelState(chat_on=True, llm_on=True))
    off = panel_buttons(PanelState(chat_on=False, llm_on=False))

    assert actions(on) == [
        chat_panel.PERSONALITY,
        chat_panel.KNOWLEDGE,
        chat_panel.SETTINGS,
        chat_panel.CHANNELS,
        chat_panel.CHAT_TOGGLE,
        chat_panel.LLM_TOGGLE,
        chat_panel.LOGS,
        chat_panel.REFRESH,
    ]
    assert actions(off) == actions(on)


@pytest.mark.parametrize(
    ("chat_on", "llm_on", "wanted"),
    [
        (True, True, (ANSWER_OFF, LLM_OFF)),
        (True, False, (ANSWER_OFF, LLM_ON)),
        (False, True, (ANSWER_ON, LLM_OFF)),
        (False, False, (ANSWER_ON, LLM_ON)),
    ],
)
def test_a_mode_button_says_what_it_will_do_and_never_both_spellings(chat_on, llm_on, wanted):
    state = PanelState(chat_on=chat_on, llm_on=llm_on)

    labels = [move.label for move in panel_buttons(state)]

    assert toggle_move(state, MODE_KEY).label == wanted[0]
    assert toggle_move(state, LLM_MODE_KEY).label == wanted[1]
    assert wanted[0] in labels and wanted[1] in labels
    assert ANSWER_ON in labels or ANSWER_OFF in labels
    assert not (ANSWER_ON in labels and ANSWER_OFF in labels)
    assert not (LLM_ON in labels and LLM_OFF in labels)


def test_a_panel_nobody_may_use_renders_no_control_at_all():
    assert panel_buttons(PanelState(chat_on=True, llm_on=True), staff=False) == ()


def test_find_is_absent_until_there_is_something_to_find():
    assert chat_panel.FIND not in actions(knowledge_buttons(notes=0))
    assert chat_panel.WRITE in actions(knowledge_buttons(notes=0))
    assert chat_panel.FIND in actions(knowledge_buttons(notes=1))


def test_a_server_note_offers_neither_remove_nor_edit():
    staff = actions(note_buttons(knowledge.STAFF))
    server = actions(note_buttons(knowledge.SERVER))

    assert staff == [chat_panel.REMOVE, chat_panel.EDIT, chat_panel.BACK]
    assert server == [chat_panel.BACK]


def test_the_settings_and_personality_rows_are_what_they_say():
    assert actions(settings_buttons()) == [
        chat_panel.LIMITS,
        chat_panel.BACK,
        chat_panel.REFRESH,
    ]
    assert actions(personality_buttons()) == [
        chat_panel.VOICES,
        chat_panel.BACK,
        chat_panel.REFRESH,
    ]


def test_every_move_the_panel_can_render_is_in_the_one_table():
    known = {move.action for move in PANEL_MOVES}
    rendered = set()
    for state in (
        PanelState(chat_on=True, llm_on=True),
        PanelState(chat_on=False, llm_on=False),
    ):
        rendered |= {move.action for move in panel_buttons(state)}
    rendered |= {move.action for move in knowledge_buttons(notes=2)}
    rendered |= {move.action for move in note_buttons(knowledge.STAFF)}
    rendered |= {move.action for move in settings_buttons()}
    rendered |= {move.action for move in personality_buttons()}
    rendered |= {move.action for move in chat_panel.voices_buttons(2, 3)}
    rendered |= {move.action for move in chat_panel.member_buttons(True)}

    assert rendered == known
    assert all(0 <= move.row <= 4 for move in PANEL_MOVES)


# --- the status block -----------------------------------------------------------------------


def test_the_status_lines_say_the_models_are_off_and_where_the_answers_come_from(bot):
    lines = status_lines(bot.store, GUILD, tiers=("ready", "no key set"))

    assert "Answering @-mentions: **on**" in lines[0]
    assert chat_panel.STATUS_OFF_TAIL.strip() in lines[0]
    assert "the quick one: ready" in lines[1]
    assert not [one for one in lines if "This month so far" in one]


def test_the_spend_block_is_absent_and_says_who_may_read_it(bot):
    hidden = status_lines(bot.store, GUILD, tiers=("ready", "ready"), hidden=True)

    assert chat_panel.STATUS_ADMIN_ONLY in hidden
    assert not [one for one in hidden if "Answers today" in one]
    assert "/chat status" not in "\n".join(hidden)


def test_the_spend_block_says_the_month_is_closed_when_it_is(bot):
    spend = SimpleNamespace(
        today=3, today_of=0, person=1, person_of=5, spent=2_000_000, cap=20, ok=False
    )

    lines = status_lines(
        bot.store, GUILD, tiers=("ready", "ready"), spend=spend, notes="4 notes", trouble="boom"
    )

    assert "Answers today: **3** of no ceiling" in lines[2]
    assert "**$2.00** of $20" in lines[3]
    assert chat_panel.STATUS_CLOSED in lines
    assert "4 notes" in lines
    assert "The last daily read did not finish: boom." in lines


# --- the mood-pool guards (fork F-C4) -------------------------------------------------------


def test_the_mood_that_is_the_voice_is_never_offered_and_is_refused_if_asked(pool):
    off, on = mood_options(pool, "noir")

    assert "noir" not in [str(row["name"]) for row in off]
    assert on == ()
    held = mood_refusal(pool, next(r for r in pool if r["name"] == "noir"), False, "noir")
    assert held is not None and held.status == 409
    assert "cannot be switched off" in held.message
    assert chat_panel.guarded_moods(pool, "noir")[0]["name"] == "noir"


def test_the_last_mood_left_on_stays_on_while_the_voice_is_the_pool(pool):
    rows = [
        dict(row, enabled=1 if str(row["name"]) == "noir" else 0)
        for row in [dict(one) for one in pool]
    ]

    off, on = mood_options(rows, personas.POOL)

    assert off == ()
    assert len(on) == len(rows) - 1
    held = mood_refusal(rows, next(r for r in rows if r["name"] == "noir"), False, "pool")
    assert held is not None and held.status == 409
    assert "last voice left on" in held.message
    assert [str(row["name"]) for row in chat_panel.guarded_moods(rows, "pool")] == ["noir"]


def test_the_last_mood_may_go_off_when_the_voice_is_not_the_pool(pool):
    rows = [
        dict(row, enabled=1 if str(row["name"]) == "noir" else 0)
        for row in [dict(one) for one in pool]
    ]

    off, _on = mood_options(rows, personas.COOKOUT)

    assert [str(row["name"]) for row in off] == ["noir"]
    assert chat_panel.guarded_moods(rows, personas.COOKOUT) == ()


def test_turning_a_mood_on_is_never_guarded(pool):
    rows = [dict(one) for one in pool]
    rows[0]["enabled"] = 0

    assert mood_refusal(rows, rows[0], True, personas.POOL) is None


# --- one write, one log row -----------------------------------------------------------------


@pytest.mark.parametrize("via", [VIA_DISCORD, VIA_WEBSITE])
async def test_the_voice_writes_once_and_logs_once_under_the_right_head(bot, actor, pool, via):
    outcome = await chat_panel.set_voice(bot, bot.guild, actor, "noir", via=via)

    assert outcome.ok and "noir" in outcome.message
    assert bot.store.get(GUILD, personas.PERSONALITY_KEY) == "noir"
    written = await kinds(bot.db)
    assert [kind for kind, _ in written] == [
        "web.chat.personality_mode" if via == VIA_WEBSITE else "chat.personality_mode"
    ]
    assert f'"via": "{via}"' in written[0][1]


async def test_a_voice_nobody_has_is_refused_in_words_and_writes_nothing(bot, actor, pool):
    outcome = await chat_panel.set_voice(bot, bot.guild, actor, "swashbuckling")
    empty = await chat_panel.set_voice(bot, bot.guild, actor, "   ")

    assert outcome.status == 404 and "not one of the voices" in outcome.message
    assert empty.status == 400 and empty.message == chat_panel.MODE_NEEDS_A_NAME
    assert await kinds(bot.db) == []


async def test_a_voice_that_is_switched_off_cannot_be_the_one_in_use(bot, actor, pool, db):
    await personas.set_enabled(db, "noir", False)

    outcome = await chat_panel.set_voice(bot, bot.guild, actor, "noir")

    assert outcome.status == 409 and "switched off" in outcome.message
    assert await kinds(bot.db) == []


@pytest.mark.parametrize("via", [VIA_DISCORD, VIA_WEBSITE])
async def test_a_mood_moves_once_and_logs_once(bot, actor, pool, via):
    off = await chat_panel.set_mood(bot, bot.guild, actor, "noir", False, via=via)
    on = await chat_panel.set_mood(bot, bot.guild, actor, "noir", True, via=via)

    assert off.ok and on.ok
    head = "web.chat." if via == VIA_WEBSITE else "chat."
    assert [kind for kind, _ in await kinds(bot.db)] == [
        f"{head}trope_disabled",
        f"{head}trope_enabled",
    ]


async def test_the_discord_door_refuses_the_mood_the_website_refuses(bot, actor, pool):
    await bot.store.set(GUILD, personas.PERSONALITY_KEY, "noir")

    outcome = await chat_panel.set_mood(bot, bot.guild, actor, "noir", False)

    assert outcome.status == 409 and "cannot be switched off" in outcome.message
    assert await kinds(bot.db) == []
    assert (await personas.get_trope(bot.db, "noir"))["enabled"]


async def test_a_mood_nobody_has_is_refused_by_name(bot, actor, pool):
    outcome = await chat_panel.set_mood(bot, bot.guild, actor, "swashbuckling", False)

    assert outcome.status == 404 and "swashbuckling" in outcome.message


@pytest.mark.parametrize("via", [VIA_DISCORD, VIA_WEBSITE])
async def test_a_note_is_written_edited_and_removed_leaving_one_row_each(bot, actor, via):
    made = await chat_panel.add_note(
        bot, bot.guild, actor, "Cookout hours", "Doors at six.", "cookout", via=via
    )
    edited = await chat_panel.edit_note(
        bot, bot.guild, actor, made.value, {"body": "Doors at seven."}, via=via
    )
    gone = await chat_panel.remove_note(bot, bot.guild, actor, made.value, via=via)

    assert made.ok and edited.ok and gone.ok
    head = "web.chat." if via == VIA_WEBSITE else "chat."
    assert [kind for kind, _ in await kinds(bot.db)] == [
        f"{head}knowledge_added",
        f"{head}knowledge_edited",
        f"{head}knowledge_removed",
    ]
    assert await knowledge.get_section(bot.db, made.value) is None


async def test_a_note_that_is_refused_says_why_and_saves_nothing(bot, actor):
    empty = await chat_panel.add_note(bot, bot.guild, actor, "  ", "words")
    long_body = await chat_panel.add_note(bot, bot.guild, actor, "Rules", "x" * 4001)
    await chat_panel.add_note(bot, bot.guild, actor, "Rules", "Be kind.")
    again = await chat_panel.add_note(bot, bot.guild, actor, "Rules", "Be kinder.")

    assert empty.status == 400 and empty.message
    assert long_body.status == 400
    assert again.status == 409 and "already has a note" in again.message
    assert len(await knowledge.list_sections(bot.db, GUILD)) == 1


async def test_a_server_note_is_refused_by_both_the_edit_and_the_remove(bot, actor, db):
    section_id = await knowledge.add_section(
        db, GUILD, "Channels", "general", source=knowledge.SERVER
    )

    edited = await chat_panel.edit_note(bot, bot.guild, actor, section_id, {"body": "mine"})
    gone = await chat_panel.remove_note(bot, bot.guild, actor, section_id)

    assert edited.status == 409 and gone.status == 409
    assert knowledge.SERVER_ROW_IS_NOT_YOURS in edited.message
    assert await knowledge.get_section(db, section_id) is not None


async def test_a_note_from_another_server_is_not_reachable_by_its_number(bot, actor, db):
    elsewhere = await knowledge.add_section(db, 9999, "Theirs", "not ours")

    edited = await chat_panel.edit_note(bot, bot.guild, actor, elsewhere, {"body": "x"})
    gone = await chat_panel.remove_note(bot, bot.guild, actor, elsewhere)

    assert edited.status == 404 and gone.status == 404
    assert await knowledge.get_section(db, elsewhere) is not None


@pytest.mark.parametrize("via", [VIA_DISCORD, VIA_WEBSITE])
async def test_a_mode_flip_writes_one_row_that_says_which_door(bot, actor, via):
    outcome = await chat_panel.set_mode(bot, bot.guild, actor, MODE_KEY, "off", via=via)

    assert outcome.ok and bot.store.get(GUILD, MODE_KEY) == "off"
    written = await kinds(bot.db)
    assert [kind for kind, _ in written] == [
        "web.chat.mode" if via == VIA_WEBSITE else "chat.mode"
    ]
    assert '"key": "chat_mode"' in written[0][1]


async def test_a_mode_that_is_not_a_chat_mode_is_refused(bot, actor):
    key = await chat_panel.set_mode(bot, bot.guild, actor, "golive_mode", "on")
    value = await chat_panel.set_mode(bot, bot.guild, actor, MODE_KEY, "shadow")

    assert key.status == 400 and value.status == 400
    assert await kinds(bot.db) == []


# --- the five numbers (fork F-C1) -----------------------------------------------------------


def test_every_field_is_read_before_the_first_one_is_written():
    good = read_limits({key: "5" for key in chat_panel.SETTINGS_KEYS})
    bad = read_limits(
        {
            chat_panel.COOLDOWN_KEY: "5",
            chat_panel.DAILY_KEY: "not a number",
            chat_panel.CAP_KEY: "20",
        }
    )
    nothing = read_limits({})

    assert good.ok and good.value == {key: 5 for key in chat_panel.SETTINGS_KEYS}
    assert bad.status == 400 and chat_panel.DAILY_KEY in bad.message
    assert nothing.status == 400


def test_a_number_outside_its_range_names_the_field_and_the_range():
    outcome = read_limits({chat_panel.CAP_KEY: "999999"})

    assert outcome.status == 400
    assert chat_panel.CAP_KEY in outcome.message and "cannot be more than" in outcome.message


async def test_five_numbers_are_saved_together_and_logged_once(bot, actor):
    outcome = await chat_panel.save_settings(
        bot, bot.guild, actor, {key: 5 for key in chat_panel.SETTINGS_KEYS}
    )

    assert outcome.ok
    assert all(bot.store.get(GUILD, key) == 5 for key in chat_panel.SETTINGS_KEYS)
    assert [kind for kind, _ in await kinds(bot.db)] == ["chat.settings"]


async def test_one_bad_number_saves_none_of_them(bot, actor):
    outcome = await chat_panel.save_settings(
        bot, bot.guild, actor, {chat_panel.DAILY_KEY: 9, chat_panel.CAP_KEY: -1}
    )

    assert not outcome.ok and chat_panel.CAP_KEY in outcome.message
    assert bot.store.get(GUILD, chat_panel.DAILY_KEY) != 9
    assert await kinds(bot.db) == []


async def test_a_key_this_panel_does_not_own_is_never_written(bot, actor):
    outcome = await chat_panel.save_settings(bot, bot.guild, actor, {"chat_simple_model": "x"})

    assert outcome.message == chat_panel.SETTINGS_NOTHING
    assert await kinds(bot.db) == []


@pytest.mark.parametrize("via", [VIA_DISCORD, VIA_WEBSITE])
async def test_the_settings_row_says_which_door_saved_them(bot, actor, via):
    await chat_panel.save_settings(bot, bot.guild, actor, {chat_panel.DAILY_KEY: 9}, via=via)

    written = await kinds(bot.db)
    assert [kind for kind, _ in written] == [
        "web.chat.settings" if via == VIA_WEBSITE else "chat.settings"
    ]
    assert f'"via": "{via}"' in written[0][1]


# --- the library one-liners -----------------------------------------------------------------


async def test_the_panel_minutes_key_defaults_to_ten_and_is_read_through_the_library(bot):
    assert panel_minutes(bot.store, GUILD) == 10

    await bot.store.set(GUILD, chat_panel.PANEL_MINUTES_KEY, 4)

    assert panel_minutes(bot.store, GUILD) == 4


def test_the_state_is_read_from_the_registry_not_from_a_flag(bot):
    assert panel_state(bot.store, GUILD) == PanelState(chat_on=True, llm_on=False)


def test_no_origin_means_no_link_at_all():
    assert site_page_url(ORIGIN) == f"{ORIGIN}/chat.html"
    assert site_page_url("") is None


# --- channel notes: the one write both doors use --------------------------------------------


def text(channel_id, name):
    return SimpleNamespace(id=channel_id, name=name)


class NotedGuild(FakeGuild):
    def __init__(self):
        super().__init__()
        self.text_channels = [text(1076003845232148580, "speed-and-pbs"), text(55, "general-chat")]


@pytest.fixture
async def noted(bot):
    bot.guild = NotedGuild()
    return bot


async def test_a_channel_note_is_saved_logged_once_and_read_back(noted, actor, db):
    outcome = await chat_panel.save_channel_note(
        noted, noted.guild, actor, "1076003845232148580", "  Speedrunning records\nand PBs. "
    )

    assert outcome.ok and outcome.value == "Speedrunning records and PBs."
    assert "#speed-and-pbs" in outcome.message
    assert await chat_panel.channel_note(noted, noted.guild, 1076003845232148580) == (
        "Speedrunning records and PBs."
    )
    rows = await kinds(db)
    assert [kind for kind, _ in rows] == ["chat.channel_note_set"]
    assert '"via": "discord"' in rows[0][1]


async def test_the_website_door_heads_its_row_web(noted, actor, db):
    await chat_panel.save_channel_note(
        noted, noted.guild, actor, 55, "Anything goes.", via=VIA_WEBSITE
    )
    await chat_panel.clear_channel_note(noted, noted.guild, actor, 55, via=VIA_WEBSITE)

    assert [kind for kind, _ in await kinds(db)] == [
        "web.chat.channel_note_set",
        "web.chat.channel_note_cleared",
    ]


async def test_a_blank_note_clears_and_a_second_clear_says_there_was_nothing(noted, actor, db):
    await chat_panel.save_channel_note(noted, noted.guild, actor, 55, "Anything goes.")

    cleared = await chat_panel.save_channel_note(noted, noted.guild, actor, 55, "   ")
    again = await chat_panel.clear_channel_note(noted, noted.guild, actor, 55)

    assert cleared.ok and "gone" in cleared.message
    assert again.ok and "had no note" in again.message
    assert await chat_panel.channel_note(noted, noted.guild, 55) == ""
    assert [kind for kind, _ in await kinds(db)] == [
        "chat.channel_note_set",
        "chat.channel_note_cleared",
    ]


async def test_a_note_over_the_cap_is_refused_in_words_and_nothing_is_stored(noted, actor, db):
    outcome = await chat_panel.save_channel_note(noted, noted.guild, actor, 55, "x" * 250)

    assert not outcome.ok
    assert (outcome.status, outcome.code) == (422, "note_too_long")
    assert "250 characters" in outcome.message and "240" in outcome.message
    assert await chat_panel.channel_note(noted, noted.guild, 55) == ""
    assert await kinds(db) == []


async def test_a_channel_that_is_not_a_text_channel_here_is_refused(noted, actor, db):
    for wanted in (999, "not-a-number"):
        outcome = await chat_panel.save_channel_note(noted, noted.guild, actor, wanted, "x")
        assert (outcome.ok, outcome.status, outcome.code) == (False, 404, "no_such_channel")
    assert await kinds(db) == []


async def test_staff_wording_is_used_and_a_broken_template_falls_back(noted, actor):
    await noted.store.set(GUILD, "chat_channel_note_saved", "Got it: #{channel}")
    said = await chat_panel.save_channel_note(noted, noted.guild, actor, 55, "a")
    assert said.message == "Got it: #general-chat"

    noted.store._cache[(GUILD, "chat_channel_note_saved")] = "{nope}"
    said = await chat_panel.save_channel_note(noted, noted.guild, actor, 55, "b")
    assert said.message.startswith("The note for **#general-chat** is saved.")


def test_the_channel_notes_card_offers_back_and_refresh_only():
    assert [move.action for move in chat_panel.channel_notes_buttons()] == [
        chat_panel.BACK,
        chat_panel.REFRESH,
    ]


# --- who hears what (personality tones, 2026-09-23) ------------------------------------------


class PeopleGuild(FakeGuild):
    def __init__(self):
        super().__init__()
        self.members = {
            21: SimpleNamespace(id=21, display_name="Nia", bot=False),
            99: SimpleNamespace(id=99, display_name="A bot", bot=True),
        }

    def get_member(self, user_id):
        return self.members.get(int(user_id))


@pytest.fixture
async def people(bot, pool):
    bot.guild = PeopleGuild()
    return bot


async def test_a_pin_from_discord_is_one_row_one_log_and_a_keyed_sentence(people, actor, db):
    from black_bloc.chat_voice import voice_row

    found = await chat_panel.pin_voice(people, people.guild, actor, 21, "noir")

    assert found.ok and found.value == "noir"
    assert found.message.startswith("**Nia** hears **")
    assert (await voice_row(db, GUILD, 21))["pinned_by"] == ACTOR
    assert [kind for kind, _ in await kinds(db)] == ["chat.voice_pinned"]


async def test_the_website_door_writes_the_same_row_under_its_own_kind(people, actor, db):
    await chat_panel.pin_voice(people, people.guild, actor, 21, "warm", via=VIA_WEBSITE)
    await chat_panel.clear_voice(people, people.guild, actor, 21, via=VIA_WEBSITE)

    assert [kind for kind, _ in await kinds(db)] == [
        "web.chat.voice_pinned",
        "web.chat.voice_cleared",
    ]


async def test_a_bot_or_a_stranger_cannot_be_pinned(people, actor, db):
    for who in (99, 4242, "nobody"):
        found = await chat_panel.pin_voice(people, people.guild, actor, who, "noir")
        assert not found.ok and found.status == 404
        assert "not in this server" in found.message
    assert await kinds(db) == []


async def test_the_cookout_and_the_pool_are_not_tones_a_member_can_be_pinned_to(people, actor):
    for said in ("cookout", "pool", ""):
        found = await chat_panel.pin_voice(people, people.guild, actor, 21, said)
        assert not found.ok and found.status == 422


async def test_clearing_nothing_says_so_and_logs_nothing(people, actor, db):
    found = await chat_panel.clear_voice(people, people.guild, actor, 21)

    assert found.ok and "had no tone pinned" in found.message
    assert await kinds(db) == []


async def test_the_roster_is_one_shape_for_both_doors(people, actor):
    await chat_panel.pin_voice(people, people.guild, actor, 21, "noir")

    found = await chat_panel.voice_roster(people, people.guild)

    assert found["setting"] == "cookout" and "noir" in found["enabled"]
    assert found["voices"][0]["pinned"] == "noir" and found["voices"][0]["trope"] == "cookout"
    assert found["labels"]["noir"]


async def test_a_tone_edit_is_kept_by_the_sync_and_logged_once(people, actor, db):
    found = await chat_panel.edit_tone(people, people.guild, actor, "noir", "NOIR, ours.")

    assert found.ok and "reads the way you wrote it" in found.message
    await personas.sync_tropes(db)
    assert (await personas.get_trope(db, "noir"))["voice"] == "NOIR, ours."
    assert [kind for kind, _ in await kinds(db)] == ["chat.tone_edited"]


async def test_the_paging_buttons_render_only_where_there_is_somewhere_to_go():
    def acts(moves):
        return [move.action for move in moves]

    assert acts(chat_panel.voices_buttons(1, 1)) == [chat_panel.BACK, chat_panel.REFRESH]
    assert acts(chat_panel.voices_buttons(1, 2))[0] == chat_panel.NEXT
    assert acts(chat_panel.voices_buttons(2, 2))[0] == chat_panel.PREVIOUS
    assert chat_panel.CLEAR_PIN not in acts(chat_panel.member_buttons(False))
    assert chat_panel.page_count(26) == 2 and chat_panel.wanted_page(9, 2) == 2
