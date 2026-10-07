# ruff: noqa: F401, F811
from datetime import timedelta
from types import SimpleNamespace

import discord
import pytest

from black_bloc import pb_panel, pb_store
from black_bloc.speedrun import UNREACHABLE, SpeedrunError
from tests.test_pb_looks import (
    ADA,
    BEA,
    GUILD,
    NOW,
    REHEARSAL,
    STAFFER,
    ZFG,
    best,
    bot,
    client,
    details_of,
    feed,
    guild,
    kinds,
    link,
    matched,
    seen,
)


class FakeResponse:
    def __init__(self):
        self.messages = []
        self.modals = []
        self.deferred = False

    def is_done(self):
        return self.deferred or bool(self.messages) or bool(self.modals)

    async def send_message(self, content=None, ephemeral=False, **kwargs):
        self.messages.append({"content": content, "ephemeral": ephemeral, **kwargs})

    async def send_modal(self, modal):
        self.modals.append(modal)

    async def defer(self, ephemeral=False):
        self.deferred = True


class FakeFollowup:
    def __init__(self, response):
        self.response = response

    async def send(self, content=None, ephemeral=False, **kwargs):
        self.response.messages.append({"content": content, "ephemeral": ephemeral, **kwargs})


class FakeInteraction:
    def __init__(self, bot, user_id=ADA):
        self.client = bot
        self.guild = bot.guild
        self.user = bot.guild.get_member(user_id)
        self.response = FakeResponse()
        self.followup = FakeFollowup(self.response)
        self.edits = []

    async def original_response(self):
        return SimpleNamespace(id=1, embeds=[])

    async def edit_original_response(self, **kwargs):
        self.edits.append(kwargs)
        return SimpleNamespace(id=2, embeds=[kwargs.get("embed")])

    @property
    def rendered(self):
        return self.edits[-1] if self.edits else self.response.messages[-1]

    @property
    def said(self):
        return [one["content"] for one in self.response.messages if one.get("content")]


def labels(view):
    return [getattr(item, "label", None) or type(item).__name__ for item in view.children]


def item(view, label):
    return next(one for one in view.children if getattr(one, "label", None) == label)


async def press(view, label, interaction):
    await item(view, label).callback(interaction)
    return interaction.rendered


def field(embed, name):
    return next(one.value for one in embed.fields if one.name == name)


async def test_a_member_sees_only_their_own_match_and_the_opt_out(bot, guild, feed):
    await matched(bot)
    interaction = FakeInteraction(bot)

    await pb_panel.open_panel(interaction)

    shown = interaction.response.messages[0]
    assert shown["ephemeral"] is True
    assert shown["allowed_mentions"].to_dict() == discord.AllowedMentions.none().to_dict()
    assert shown["embed"].title == "Personal bests"
    assert shown["embed"].description.startswith(
        "**speedrun.com** — [zfg](https://www.speedrun.com/users/zfg), found from twitch.tv/zfg1."
    )
    assert shown["embed"].fields == []
    assert labels(shown["view"]) == ["Do not post my personal bests"]


@pytest.mark.parametrize(
    ("prepare", "starts", "button"),
    [
        ("nothing", "You have not linked a Twitch channel", "Do not post my personal bests"),
        ("linked", "Black Bloc has not looked for your speedrun.com account yet", None),
        ("none", "No speedrun.com account lists twitch.tv/zfg1", None),
        ("staff", "**speedrun.com** — [zfg](https://www.speedrun.com/users/zfg), set by", None),
        ("opted_out", "You asked Black Bloc not to post", "Post my personal bests"),
        ("blocked", "Staff have turned personal best posts off for you", ""),
    ],
)
async def test_every_state_reads_as_one_sentence_with_only_the_valid_move(
    bot, guild, feed, prepare, starts, button
):
    if prepare != "nothing":
        await link(bot.db, ADA, "zfg1")
    if prepare == "none":
        await pb_store.write_state(
            bot.db, GUILD, ADA, pb_store.NONE, state_by="auto", twitch_login="zfg1"
        )
    if prepare == "staff":
        await matched(bot, source=pb_store.STAFF)
    if prepare in ("opted_out", "blocked"):
        await pb_store.write_state(bot.db, GUILD, ADA, prepare, state_by="staff")

    embed, view = await pb_panel.build_own(bot, guild, guild.get_member(ADA))

    assert embed.description.startswith(starts)
    wanted = [] if button == "" else [button or "Do not post my personal bests"]
    assert labels(view) == wanted


async def test_the_opt_out_button_opts_out_and_flips_to_the_way_back(bot, guild, feed):
    await matched(bot)
    interaction = FakeInteraction(bot)
    _, view = await pb_panel.build_own(bot, guild, interaction.user)

    shown = await press(view, "Do not post my personal bests", interaction)

    assert (await pb_store.match(bot.db, GUILD, ADA))["state"] == "opted_out"
    assert shown["embed"].description.startswith("Done — Black Bloc will not post")
    assert labels(shown["view"]) == ["Post my personal bests"]

    back = await press(shown["view"], "Post my personal bests", FakeInteraction(bot))
    assert (await pb_store.match(bot.db, GUILD, ADA))["state"] == "matched"
    assert labels(back["view"]) == ["Do not post my personal bests"]
    assert await kinds(bot.db) == ["pbfeed.opted_out", "pbfeed.opted_in"]


async def test_staff_see_the_feed_and_the_way_in_to_manage_it(bot, guild, feed):
    await matched(bot)
    await pb_store.write_state(bot.db, GUILD, BEA, pb_store.BLOCKED, state_by="staff")
    await pb_store.record_ok(bot.db, GUILD, found=0, now=NOW)

    embed, view = await pb_panel.build_own(bot, guild, guild.get_member(STAFFER))

    said = field(embed, pb_panel.FEED_FIELD)
    assert said.startswith("shadow · 1 matched · 0 with no match · 0 opted out · 1 blocked")
    assert "last look <t:" in said
    assert labels(view) == ["Do not post my personal bests", "Manage…", "Open on the site"]
    assert item(view, "Open on the site").url.endswith("/pbs.html")


async def test_the_feed_line_says_an_outage_in_words(bot, guild, feed):
    await pb_store.record_outage(
        bot.db, GUILD, str(SpeedrunError(UNREACHABLE, why="TimeoutError")), NOW, NOW
    )

    embed, _ = await pb_panel.build_manage(bot, guild)

    assert "could not look <t:" in field(embed, pb_panel.FEED_FIELD)
    assert "could not be reached" in field(embed, pb_panel.FEED_FIELD)


async def test_manage_is_refused_to_a_member_who_presses_a_stale_button(bot, guild, feed):
    interaction = FakeInteraction(bot, ADA)

    await pb_panel.ManageButton().callback(interaction)

    assert interaction.edits == [] and "staff only" in interaction.said[0]


async def test_staff_pick_a_member_and_get_only_the_moves_that_apply(bot, guild, feed):
    await matched(bot)
    staff = FakeInteraction(bot, STAFFER)
    _, own = await pb_panel.build_own(bot, guild, staff.user)

    manage = await press(own, "Manage…", staff)
    picker = manage["view"].children[0]
    assert isinstance(picker, discord.ui.UserSelect)
    picker._values = [guild.get_member(ADA)]
    await picker.callback(staff)
    card = staff.rendered

    assert card["embed"].description == f"<@{ADA}>"
    assert field(card["embed"], pb_panel.MEMBER_FIELD).startswith(
        "matched to [zfg](https://www.speedrun.com/users/zfg) (auto)"
    )
    assert labels(card["view"]) == ["Set by hand…", "Unmatch", "Look now", "Block", "Back"]


@pytest.mark.parametrize(
    ("state", "mode", "moves"),
    [
        (None, "shadow", ["set", "block"]),
        (pb_store.NONE, "shadow", ["set", "block"]),
        (pb_store.MATCHED, "shadow", ["set", "unmatch", "look", "block"]),
        (pb_store.MATCHED, "off", ["unmatch", "block"]),
        (None, "off", ["block"]),
        (pb_store.OPTED_OUT, "on", ["clear", "block"]),
        (pb_store.BLOCKED, "on", ["set", "unblock"]),
    ],
)
def test_the_staff_moves_for_each_state(state, mode, moves):
    row = None if state is None else {"state": state, "opted_out_at": None}

    assert pb_panel.staff_moves(row, mode) == moves
    hidden = {"state": pb_store.BLOCKED, "opted_out_at": NOW.isoformat()}
    assert pb_panel.staff_moves(hidden, "on") == ["unblock"]


async def test_block_then_unblock_from_the_card(bot, guild, feed):
    await matched(bot)
    staff = FakeInteraction(bot, STAFFER)
    _, card = await pb_panel.build_member(bot, guild, ADA)

    await item(card, "Block").callback(staff)
    modal = staff.response.modals[0]
    assert (await pb_store.match(bot.db, GUILD, ADA))["state"] == "matched"
    assert (modal.title, modal.reason.label, modal.reason.required) == (
        "Block",
        "Reason (the member is told)",
        False,
    )
    modal.reason._value = "posting fakes"
    submitted = FakeInteraction(bot, STAFFER)
    await modal.on_submit(submitted)
    blocked = submitted.rendered

    assert (await pb_store.match(bot.db, GUILD, ADA))["state"] == "blocked"
    assert (await details_of(bot.db, "pbfeed.blocked"))["reason"] == "posting fakes"
    assert blocked["embed"].description.startswith(f"<@{ADA}> is blocked")
    assert labels(blocked["view"]) == ["Set by hand…", "Unblock", "Back"]
    assert field(blocked["embed"], pb_panel.MEMBER_FIELD) == "blocked by staff"

    await press(blocked["view"], "Unblock", FakeInteraction(bot, STAFFER))
    assert (await pb_store.match(bot.db, GUILD, ADA))["state"] == "none"
    assert (await details_of(bot.db, "pbfeed.unblocked"))["actor_id"] == STAFFER


async def test_a_staff_button_pressed_by_a_member_changes_nothing(bot, guild, feed):
    await matched(bot)
    _, card = await pb_panel.build_member(bot, guild, ADA)
    member = FakeInteraction(bot, BEA)

    await item(card, "Block").callback(member)
    await item(card, "Set by hand…").callback(member)

    assert (await pb_store.match(bot.db, GUILD, ADA))["state"] == "matched"
    assert member.response.modals == [] and len(member.said) == 2
    assert await kinds(bot.db) == []


async def test_set_by_hand_opens_a_modal_and_the_name_becomes_the_match(bot, guild, feed, client):
    client.by_name["zfg"] = [ZFG]
    staff = FakeInteraction(bot, STAFFER)
    _, card = await pb_panel.build_member(bot, guild, ADA)

    await item(card, "Set by hand…").callback(staff)
    modal = staff.response.modals[0]
    modal.runner._value = "zfg"
    modal.reason._value = "they asked in chat"
    submitted = FakeInteraction(bot, STAFFER)
    await modal.on_submit(submitted)
    assert (await details_of(bot.db, "pbfeed.set_by_hand"))["reason"] == "they asked in chat"

    row = await pb_store.match(bot.db, GUILD, ADA)
    assert (row["state"], row["source"], row["src_name"]) == ("matched", "staff", "zfg")
    assert "is now matched to **zfg**" in submitted.rendered["embed"].description
    assert "(staff)" in field(submitted.rendered["embed"], pb_panel.MEMBER_FIELD)


async def test_a_refused_name_is_said_on_the_card_and_the_card_is_unchanged(
    bot, guild, feed, client
):
    staff = FakeInteraction(bot, STAFFER)

    await pb_panel.run_set(staff, ADA, "nobody")

    assert "no single account named exactly **nobody**" in staff.rendered["embed"].description
    assert field(staff.rendered["embed"], pb_panel.MEMBER_FIELD) == "not looked up yet"


async def test_look_now_from_the_card_rehearses_the_news(bot, guild, feed, client):
    await matched(bot)
    await seen(feed, client, [best("r1")])
    client.bests[ZFG.id] = [best("r9", seconds=1.5, verified_at=NOW + timedelta(minutes=1))]
    staff = FakeInteraction(bot, STAFFER)
    _, card = await pb_panel.build_member(bot, guild, ADA)

    shown = await press(card, "Look now", staff)

    assert "1 new personal best(s)" in shown["embed"].description
    assert len(guild.get_channel(REHEARSAL).sent) == 1
    lines = field(shown["embed"], pb_panel.MEMBER_FIELD)
    assert "last looked <t:" in lines and "last new personal best <t:" in lines


async def test_back_walks_from_a_member_to_the_picker_to_the_own_card(bot, guild, feed):
    staff = FakeInteraction(bot, STAFFER)
    _, card = await pb_panel.build_member(bot, guild, ADA)

    picker = await press(card, "Back", staff)
    own = await press(picker["view"], "Back", staff)

    assert isinstance(picker["view"].children[0], discord.ui.UserSelect)
    assert "Manage…" in labels(own["view"])


async def test_try_again_rebuilds_the_card_the_member_was_on(bot, guild, feed):
    staff = FakeInteraction(bot, STAFFER)
    _, card = await pb_panel.build_member(bot, guild, ADA)
    _, own = await pb_panel.build_own(bot, guild, staff.user)

    await card.render_again(staff)
    assert staff.rendered["embed"].description == f"<@{ADA}>"
    await own.render_again(staff)
    assert "Manage…" in labels(staff.rendered["view"])


async def test_the_panel_lives_for_the_minutes_the_key_says(bot, guild, feed):
    await bot.store.set(GUILD, "pb_feed_panel_minutes", 3)

    _, view = await pb_panel.build_own(bot, guild, guild.get_member(ADA))

    assert view.timeout == 180 and view.footer == "This panel has gone quiet — run /pb again"


async def test_the_command_says_so_when_the_database_is_down(bot, guild, feed, monkeypatch):
    monkeypatch.setattr(type(bot.db), "is_connected", property(lambda self: False))
    interaction = FakeInteraction(bot)

    await pb_panel.open_panel(interaction)

    assert "database" in interaction.said[0] and interaction.response.messages[0]["ephemeral"]


@pytest.mark.parametrize(
    ("mode", "says", "never"),
    [
        ("on", "A personal best is posted once speedrun.com has verified it.", "trying this out"),
        ("shadow", "Staff are still trying this out", "is posted once"),
        ("off", "switched off", "is posted once"),
    ],
)
@pytest.mark.parametrize("source", [pb_store.AUTO, pb_store.STAFF])
async def test_a_matched_member_is_never_promised_a_post_the_mode_forbids(
    bot, guild, feed, mode, says, never, source
):
    await bot.store.set(GUILD, "pb_feed_mode", mode)
    await matched(bot, source=source)

    embed, _ = await pb_panel.build_own(bot, guild, guild.get_member(ADA))

    assert says in embed.description and never not in embed.description
    assert embed.description.startswith("**speedrun.com** — [zfg](")


async def test_opting_back_in_while_rehearsing_promises_no_post(bot, guild, feed):
    await matched(bot)
    interaction = FakeInteraction(bot)
    _, view = await pb_panel.build_own(bot, guild, interaction.user)
    out = await press(view, "Do not post my personal bests", interaction)

    back = await press(out["view"], "Post my personal bests", FakeInteraction(bot))

    said = back["embed"].description
    assert said.startswith("Done — you are back in the personal best feed.")
    assert "will be posted" not in said and "is posted once" not in said
    assert "Staff are still trying this out" in said


@pytest.mark.parametrize("move", ["Unmatch", "Clear the opt-out"])
async def test_unmatch_and_clear_ask_for_a_reason_before_they_act(bot, guild, feed, move):
    await matched(bot)
    if move == "Clear the opt-out":
        await pb_store.write_state(
            bot.db, GUILD, ADA, pb_store.OPTED_OUT, state_by="member", keep_runner=True
        )
    staff = FakeInteraction(bot, STAFFER)
    _, card = await pb_panel.build_member(bot, guild, ADA)

    await item(card, move).callback(staff)
    modal = staff.response.modals[0]
    before = (await pb_store.match(bot.db, GUILD, ADA))["state"]
    modal.reason._value = "asked for it"
    await modal.on_submit(FakeInteraction(bot, STAFFER))

    kind = "pbfeed.unmatched" if move == "Unmatch" else "pbfeed.opt_out_cleared"
    assert before in ("matched", "opted_out") and modal.title == move
    assert (await details_of(bot.db, kind))["reason"] == "asked for it"
    assert (await pb_store.match(bot.db, GUILD, ADA))["state"] != before


def test_the_name_limit_has_one_home():
    from black_bloc import pb_moves

    assert pb_panel.NAME_LIMIT is pb_moves.NAME_LIMIT
    source = (pb_panel.__file__, pb_moves.__file__)
    counts = [open(path, encoding="utf-8").read().count("NAME_LIMIT = ") for path in source]
    assert counts == [0, 1]


async def stored_posts(bot, count):
    found = []
    for n in range(count):
        claimed = await pb_store.claim_post(
            bot.db, GUILD, ADA, best(f"r{n}", seconds=95.5 + n), "zfg", now=NOW
        )
        await pb_store.settle_post(bot.db, claimed, pb_store.REHEARSED, channel_id=REHEARSAL)
        found.append(claimed)
    return found


def again_pick(view):
    return next(
        (one for one in view.children if isinstance(one, discord.ui.Select)
         and not isinstance(one, discord.ui.UserSelect)),
        None,
    )


async def test_manage_offers_the_latest_posts_to_post_again(bot, guild, feed):
    await matched(bot)
    ids = await stored_posts(bot, pb_panel.AGAIN_CHOICES + 2)

    _, view = await pb_panel.build_manage(bot, guild)

    pick = again_pick(view)
    assert pick is not None and pick.placeholder == "Post one again…"
    assert [option.value for option in pick.options] == [
        str(one) for one in reversed(ids[-pb_panel.AGAIN_CHOICES:])
    ]
    newest = pick.options[0]
    assert newest.label.startswith("Ada — Ocarina of Time")
    assert "rehearsed" in newest.description


@pytest.mark.parametrize("why", ["off", "nothing posted"])
async def test_manage_draws_no_post_again_when_it_cannot_be_used(bot, guild, feed, why):
    await matched(bot)
    if why == "off":
        await stored_posts(bot, 1)
        await bot.store.set(GUILD, "pb_feed_mode", "off")

    _, view = await pb_panel.build_manage(bot, guild)

    assert again_pick(view) is None


async def test_picking_a_post_posts_it_again_and_says_where(bot, guild, feed):
    await matched(bot)
    [source] = await stored_posts(bot, 1)
    staff = FakeInteraction(bot, STAFFER)
    _, view = await pb_panel.build_manage(bot, guild)
    pick = again_pick(view)
    pick._values = [str(source)]

    await pick.callback(staff)

    card = staff.rendered
    assert card["embed"].description.startswith("Rehearsed <@900>")
    assert again_pick(card["view"]) is not None
    assert len(guild.get_channel(REHEARSAL).sent) == 1
    found = await details_of(bot.db, "pbfeed.would_post_again")
    assert (found["actor_id"], found["via"], found["again_of"]) == (STAFFER, "discord", source)


async def test_a_member_cannot_post_again_from_a_stale_panel(bot, guild, feed):
    await matched(bot)
    [source] = await stored_posts(bot, 1)
    _, view = await pb_panel.build_manage(bot, guild)
    pick = again_pick(view)
    pick._values = [str(source)]
    member = FakeInteraction(bot, ADA)

    await pick.callback(member)

    assert member.edits == [] and guild.get_channel(REHEARSAL).sent == []
