from pathlib import Path

import discord
import pytest

from black_bloc import baf_runs as runs
from black_bloc import baf_runs_panel as panel
from black_bloc.settings_store import (
    RUNS_LOOKUP_COUNT,
    RUNS_LOOKUP_LINE,
    RUNS_LOOKUP_MORE,
    RUNS_LOOKUP_NO_DATE,
    RUNS_LOOKUP_NONE,
    RUNS_LOOKUP_SEEN,
    RUNS_LOOKUP_TAGS,
    RUNS_LOOKUP_TITLE,
)
from tests.baf_runs_fakes import (
    GUILD,
    RUNNER_ID,
    FakeMember,
    add_marathon,
    add_run,
    kinds,
    make_bot,
    person,
)


class FakeResponse:
    def __init__(self):
        self.done = False
        self.messages = []
        self.modals = []

    def is_done(self):
        return self.done

    async def defer(self, **kwargs):
        self.done = True

    async def send_message(self, content=None, **kwargs):
        self.done = True
        self.messages.append({"content": content, **kwargs})

    async def send_modal(self, modal):
        self.done = True
        self.modals.append(modal)


class FakeFollowup:
    def __init__(self, response):
        self.response = response

    async def send(self, content=None, **kwargs):
        self.response.messages.append({"content": content, **kwargs})


class FakeInteraction:
    def __init__(self, client, user):
        self.client = client
        self.user = user
        self.guild = client.guild
        self.response = FakeResponse()
        self.followup = FakeFollowup(self.response)
        self.edits = []

    async def edit_original_response(self, **kwargs):
        self.edits.append(kwargs)
        return object()


def buttons(view):
    return [(item.label, item.url) for item in view.children if isinstance(item, discord.ui.Button)]


@pytest.fixture
async def bot(db, monkeypatch):
    found = await make_bot(db, monkeypatch)
    gdq = await add_marathon(db, "SGDQ 2026")
    for at, game in ((1, "Shredder's Revenge"), (2, "Shredder's Revenge"), (3, "Celeste")):
        await add_run(
            db,
            gdq,
            at,
            game,
            [person("kaizo_kat", user_id=RUNNER_ID)],
            at=f"2026-10-0{at}T18:00:00+00:00",
        )
    return found


def staff_of(bot):
    member = FakeMember(42, "lead")
    member.guild = bot.guild
    member.guild_permissions = discord.Permissions(manage_guild=True)
    bot.guild.members.append(member)
    return member


async def test_the_panel_opens_on_the_counts_with_search_and_the_site(bot):
    embed, view = await panel.build_root(bot, bot.guild)

    assert embed.title == "BaF runs" and embed.description == "3 run(s) · 2 game(s)"
    assert buttons(view) == [
        ("Search…", None),
        ("Open on the site", "https://blackbloc.example/runs.html"),
    ]


async def test_search_answers_from_the_shared_view_with_the_word_keys(bot):
    await bot.store.set(GUILD, RUNS_LOOKUP_TITLE, "Game: {game}", by=1)
    await bot.store.set(GUILD, RUNS_LOOKUP_LINE, "{event} - {runners}", by=1)
    who = staff_of(bot)
    _, root = await panel.build_root(bot, bot.guild)
    pressed = FakeInteraction(bot, who)
    await root.children[0].callback(pressed)
    modal = pressed.response.modals[0]
    modal.typed._value = "  shredder  "

    submitted = FakeInteraction(bot, who)
    await modal.on_submit(submitted)

    shown = submitted.edits[0]
    embed = shown["embed"]
    assert [field.name for field in embed.fields] == ["Game: Shredder's Revenge"]
    lines = embed.fields[0].value.split("\n")
    assert lines[0].startswith("seen 2 time(s), last <t:") and lines[0].endswith("at SGDQ 2026")
    assert lines[1:] == ["SGDQ 2026 - Kat (kaizo_kat)"] * 2
    assert buttons(shown["view"]) == [
        ("Search again", None),
        ("Open on the site", "https://blackbloc.example/runs.html#q=shredder"),
    ]
    assert shown["allowed_mentions"].everyone is False
    assert (await kinds(bot.db)).count("runs.lookup") == 1


async def test_the_seen_line_is_the_runs_lookup_seen_key(bot):
    await bot.store.set(GUILD, RUNS_LOOKUP_SEEN, "{n}x, latest {event}", by=1)
    who = staff_of(bot)
    submitted = FakeInteraction(bot, who)
    modal = panel.SearchModal()
    modal.typed._value = "shredder"

    await modal.on_submit(submitted)

    assert submitted.edits[0]["embed"].fields[0].value.split("\n")[0] == "2x, latest SGDQ 2026"


async def test_no_match_says_the_none_words_with_what_was_typed(bot):
    who = staff_of(bot)
    submitted = FakeInteraction(bot, who)
    modal = panel.SearchModal()
    modal.typed._value = "zelda"

    await modal.on_submit(submitted)

    embed = submitted.edits[0]["embed"]
    assert embed.description == "Nothing in the BaF runs database matches **zelda**."
    assert embed.fields == []


async def test_a_member_who_is_not_staff_cannot_open_the_search(bot):
    stranger = FakeMember(99, "stranger")
    stranger.guild = bot.guild
    stranger.guild_permissions = discord.Permissions.none()
    _, root = await panel.build_root(bot, bot.guild)
    pressed = FakeInteraction(bot, stranger)

    await root.children[0].callback(pressed)

    assert pressed.response.modals == []
    assert "staff only" in pressed.response.messages[0]["content"]


def test_every_word_in_the_modal_fits_discords_limits():
    modal = panel.SearchModal()

    assert len(panel.MODAL_TITLE) <= 45 and len(panel.FIELD_LABEL) <= 45
    assert len(panel.FIELD_HINT) <= 100 and modal.typed.max_length == panel.QUERY_LIMIT


def test_a_long_answer_is_cut_inside_one_embed_field(bot):
    run = {"date": None, "event": "e" * 300, "category": "c", "runners_text": "r"}
    game = {
        "game": "g" * 300,
        "times": 9,
        "last_date": None,
        "last_event": "e",
        "more": 4,
        "runs": [run] * 5,
    }

    name, value = panel.game_field(bot, GUILD, game)

    assert len(name) <= 256 and len(value) <= 1024


async def test_a_game_with_a_series_or_genre_shows_them_on_the_tags_line_and_only_then(bot):
    who = staff_of(bot)
    modal = panel.SearchModal()
    modal.typed._value = "shredder"
    plain = FakeInteraction(bot, who)
    await modal.on_submit(plain)
    assert plain.edits[0]["embed"].fields[0].value.split("\n")[0].startswith("seen 2 time(s)")

    await runs.set_genre(bot, bot.guild, None, "Shredder's Revenge", "Beat 'em up")
    genre_only = FakeInteraction(bot, who)
    await modal.on_submit(genre_only)
    assert genre_only.edits[0]["embed"].fields[0].value.split("\n")[0] == "Beat 'em up"

    await runs.set_series(bot, bot.guild, None, "Shredder's Revenge", "TMNT")
    await bot.store.set(GUILD, RUNS_LOOKUP_TITLE, "{game} [{genre}]", by=1)
    await bot.store.set(GUILD, RUNS_LOOKUP_SEEN, "{n}x in {series}", by=1)
    both = FakeInteraction(bot, who)
    await modal.on_submit(both)
    field = both.edits[0]["embed"].fields[0]
    assert field.name == "Shredder's Revenge [Beat 'em up]"
    assert field.value.split("\n")[:2] == ["TMNT · Beat 'em up", "2x in TMNT"]

    await bot.store.set(GUILD, RUNS_LOOKUP_TAGS, "Series: {series} / Genre: {genre}", by=1)
    worded = FakeInteraction(bot, who)
    await modal.on_submit(worded)
    first = worded.edits[0]["embed"].fields[0].value.split("\n")[0]
    assert first == "Series: TMNT / Genre: Beat 'em up"


def test_no_panel_constant_carries_the_seen_words():
    text = Path(panel.__file__).read_text(encoding="utf-8")
    assert "time(s)" not in text and "seen {n}" not in text


async def test_the_count_more_and_no_date_words_are_settings_keys(bot):
    await bot.store.set(GUILD, RUNS_LOOKUP_COUNT, "{games} games, {runs} runs", by=1)
    await bot.store.set(GUILD, RUNS_LOOKUP_MORE, "+{more}", by=1)
    await bot.store.set(GUILD, RUNS_LOOKUP_NO_DATE, "undated", by=1)
    await bot.store.set(GUILD, RUNS_LOOKUP_LINE, "{date}", by=1)

    embed, _ = await panel.build_root(bot, bot.guild)
    run = {"date": None, "event": "e", "category": "c", "runners_text": "r"}
    game = {"game": "g", "times": 6, "last_date": None, "last_event": "e", "more": 1, "runs": [run]}
    _, value = panel.game_field(bot, GUILD, game)

    assert embed.description == "2 games, 3 runs"
    assert value.split("\n") == ["seen 6 time(s), last undated at e", "undated", "+1"]
    text = Path(panel.__file__).read_text(encoding="utf-8")
    assert "no date" not in text and "and {more} more" not in text and "game(s)" not in text


async def test_the_search_finds_a_game_by_its_genre_family(bot):
    await runs.set_genre(bot, bot.guild, None, "Celeste", "2D platformer")
    submitted = FakeInteraction(bot, staff_of(bot))
    modal = panel.SearchModal()
    modal.typed._value = "platformers"

    await modal.on_submit(submitted)

    assert [field.name for field in submitted.edits[0]["embed"].fields] == ["Celeste"]


async def test_the_search_takes_words_in_any_order_and_initials(bot):
    submitted = FakeInteraction(bot, staff_of(bot))
    modal = panel.SearchModal()
    modal.typed._value = "revenge shredders"

    await modal.on_submit(submitted)

    assert [field.name for field in submitted.edits[0]["embed"].fields] == ["Shredder's Revenge"]


async def test_nothing_found_offers_the_closest_names_through_the_none_key(bot):
    who = staff_of(bot)
    near = FakeInteraction(bot, who)
    modal = panel.SearchModal()
    modal.typed._value = "shredding reverb"
    await modal.on_submit(near)
    assert near.edits[0]["embed"].description == (
        "Nothing in the BaF runs database matches **shredding reverb**.\nShredder's Revenge"
    )

    await bot.store.set(GUILD, RUNS_LOOKUP_NONE, "No {query}. Closest: {suggestions}", by=1)
    worded = FakeInteraction(bot, who)
    await modal.on_submit(worded)
    assert worded.edits[0]["embed"].description == (
        "No shredding reverb. Closest: Shredder's Revenge"
    )


async def test_search_again_opens_the_form_with_the_query_already_typed(bot):
    who = staff_of(bot)
    submitted = FakeInteraction(bot, who)
    modal = panel.SearchModal()
    modal.typed._value = "celeste"
    await modal.on_submit(submitted)
    answer = submitted.edits[0]["view"]

    pressed = FakeInteraction(bot, who)
    await answer.children[0].callback(pressed)

    assert pressed.response.modals[0].typed.default == "celeste"
    assert panel.SearchModal().typed.default is None
