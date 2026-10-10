# ruff: noqa: F401, F811
import discord

from black_bloc import points_panel as panel
from black_bloc import points_store as store_
from black_bloc.cogs.moderation import modmail as modmail_cog
from black_bloc.points.model import APPROVED
from black_bloc.settings_store import POINTS_WORDS
from tests.cogs.moderation.test_modmail import GUILD, FakeInteraction, FakeUser
from tests.test_points_tickets import GIVEN, PROOF, ada, bot, lead, vera


def labels(view):
    return [getattr(one, "label", None) for one in view.children]


def item(view, label):
    return next(one for one in view.children if getattr(one, "label", None) == label)


async def opened_by(bot, who):
    interaction = FakeInteraction(bot, who)
    await panel.open_panel(interaction)
    return interaction


async def press(bot, who, view, label):
    interaction = FakeInteraction(bot, who)
    await item(view, label).callback(interaction)
    return interaction


async def approved_run(db, user_id, points=10, xp=5, game="Celeste"):
    run_id = await store_.add_run(
        db, GUILD, user_id, {"game": game, "seconds": 60.0, "proof_url": PROOF}
    )
    await store_.update_run(
        db,
        run_id,
        {
            "state": APPROVED,
            "decided_by": 1,
            "decided_at": store_.stamp(),
            "xp": xp,
            "speedpoints": points,
        },
        when_state="pending",
    )
    return run_id


async def test_a_member_opens_the_board_with_the_moves_that_fit_them(bot, ada):
    shown = await opened_by(bot, ada)

    message = shown.response.messages[0]
    assert message["ephemeral"] is True
    assert message["allowed_mentions"].to_dict() == discord.AllowedMentions.none().to_dict()
    embed = message["embed"]
    assert embed.title == "Leaderboard"
    assert embed.description == "No runs have been approved yet."
    assert [(one.name, one.value) for one in embed.fields] == [
        ("Bounties", "No bounties right now.")
    ]
    assert labels(message["view"]) == [
        "By XP",
        "Full board",
        "Next rank",
        "Submit a run",
        "speedrun.com…",
    ]
    assert message["view"].render_again is not None


async def test_the_board_lists_the_top_and_switches_to_xp(bot, ada, db):
    await approved_run(db, ada.id, points=20, xp=5)
    other = FakeUser(bot.guild, user_id=31, display_name="Bea")
    await approved_run(db, other.id, points=10, xp=100)
    view = (await opened_by(bot, ada)).response.messages[0]["view"]

    assert (await opened_by(bot, ada)).response.messages[0]["embed"].description == (
        "#1 Ada — 1 runs · 5 XP · 20 speedpoints\n#2 Bea — 1 runs · 100 XP · 10 speedpoints"
    )
    switched = await press(bot, ada, view, "By XP")

    assert switched.embed.title == "Leaderboard by XP"
    assert switched.embed.description.startswith("#1 Bea")
    assert labels(switched.view)[0] == "By speedpoints"


async def test_next_rank_says_how_far_the_next_place_up_is(bot, ada, db):
    await approved_run(db, ada.id, points=10)
    leader = FakeUser(bot.guild, user_id=31, display_name="Bea")
    await approved_run(db, leader.id, points=30)
    view = (await opened_by(bot, ada)).response.messages[0]["view"]

    shown = await press(bot, ada, view, "Next rank")

    assert shown.embed.description.startswith(
        "You are #2 with 10 speedpoints. 21 more passes Bea at #1 — about 3 approved run(s)."
    )


async def test_the_full_board_pages_twenty_five_at_a_time(bot, ada, db):
    for n in range(27):
        FakeUser(bot.guild, user_id=100 + n, display_name=f"Runner {n:02d}")
        await approved_run(db, 100 + n, points=1000 - n)
    view = (await opened_by(bot, ada)).response.messages[0]["view"]

    first = await press(bot, ada, view, "Full board")
    assert len(first.embed.description.splitlines()) == 25
    assert first.embed.footer.text == "Page 1 of 2"
    assert labels(first.view) == ["Next", "Back"]

    second = await press(bot, ada, first.view, "Next")
    assert second.embed.description.splitlines()[0].startswith("#26 Runner 25")
    assert labels(second.view) == ["Previous", "Back"]

    back = await press(bot, ada, second.view, "Back")
    assert back.embed.title == "Leaderboard"


async def test_submit_opens_five_fields_that_fit_discord_and_files_the_run(bot, ada, db):
    view = (await opened_by(bot, ada)).response.messages[0]["view"]

    pressed = await press(bot, ada, view, "Submit a run")
    modal = pressed.response.modals[-1]
    rows = [one for one in modal.children if isinstance(one, discord.ui.Label)]
    fields = [one.component for one in rows]
    assert [one.text for one in rows] == [
        "Game",
        "Category",
        "Time",
        "Proof link",
        "Note for staff",
    ]
    assert all(len(one.text) <= 45 for one in rows) and len(modal.title) <= 45
    assert all(len(one.placeholder or "") <= 100 for one in fields)
    for one, value in zip(fields, ("Celeste", "Any%", "30:00", PROOF, ""), strict=True):
        one._value = value
    answered = FakeInteraction(bot, ada)
    await modal.on_submit(answered)

    assert answered.embed.description.startswith("Your **Celeste** run (30:00) is in.")
    ticket = await modmail_cog.open_ticket_for(db, GUILD, ada.id)
    assert ticket["source"] == "points"
    assert ada.dms == []


def test_every_shipped_form_word_fits_discords_limits():
    for key in (
        "points_submit_title",
        "points_game_label",
        "points_category_label",
        "points_time_label",
        "points_proof_label",
        "points_note_label",
    ):
        assert len(POINTS_WORDS[key][0]) <= 45, key
    for key in ("points_time_hint", "points_proof_hint"):
        assert len(POINTS_WORDS[key][0]) <= 100, key


async def test_staff_see_pending_as_the_list_of_open_run_tickets(bot, ada, lead, db):
    from black_bloc import points_tickets

    await points_tickets.submit(bot, bot.guild, ada, GIVEN)
    ticket = await modmail_cog.open_ticket_for(db, GUILD, ada.id)
    view = (await opened_by(bot, lead)).response.messages[0]["view"]
    assert "Pending (1)" in labels(view)
    assert "Pending (1)" not in labels((await opened_by(bot, ada)).response.messages[0]["view"])

    shown = await press(bot, lead, view, "Pending (1)")

    assert shown.embed.title == "Runs waiting for a decision"
    assert f"<#{ticket['thread_id']}>" in shown.embed.description
    assert labels(shown.view) == ["Back"]


async def test_the_speedrun_com_panel_opens_behind_its_button_and_comes_back(bot, ada):
    view = (await opened_by(bot, ada)).response.messages[0]["view"]

    feed = await press(bot, ada, view, "speedrun.com…")

    assert feed.embed.title == "Personal bests"
    assert labels(feed.view)[-1] == "Back"
    back = await press(bot, ada, feed.view, "Back")
    assert back.embed.title == "Leaderboard"


async def test_the_feed_off_takes_speedrun_com_off_the_board(bot, ada):
    """Owner, 2026-10-10: no speedrun.com door until the feed is turned back on."""
    await bot.store.set(GUILD, "pb_feed_mode", "off")
    view = (await opened_by(bot, ada)).response.messages[0]["view"]
    assert "speedrun.com…" not in labels(view)
    assert "Submit a run" in labels(view)

    await bot.store.set(GUILD, "pb_feed_mode", "shadow")
    view = (await opened_by(bot, ada)).response.messages[0]["view"]
    assert "speedrun.com…" in labels(view)


async def test_off_takes_submit_away_and_the_board_still_reads(bot, ada):
    await bot.store.set(GUILD, "points_mode", "off")

    view = (await opened_by(bot, ada)).response.messages[0]["view"]

    assert "Submit a run" not in labels(view)
    assert "Full board" in labels(view)
