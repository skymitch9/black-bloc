import json
from types import SimpleNamespace

import discord
import pytest

from black_bloc import applications as forms
from black_bloc import rolegrants as grants
from black_bloc.cogs.community.applications import (
    DECIDE_TEMPLATE,
    MODE_SAID,
    NOT_AN_APPROVER,
    REMOVE_IS_FOR_LISTS,
    Applications,
    ApplyButton,
    ApplyModal,
    ApplyPick,
    CardMoveButton,
    DecisionButton,
    DenyModal,
    FormPick,
    LogsButton,
    QueuePick,
    WithdrawPick,
    apply_decision,
    approver_role_id,
    build_card,
    build_form_card,
    change_question,
    drop_form,
    make_form,
    mode_of,
    nudge_mentions,
    open_card,
    open_form_modal,
    post_panel,
    put_panel_up,
    reinstate,
    remove,
    render_panel,
    render_questions,
    render_roster,
    render_settings,
    review_channel,
    save_form,
    set_mode,
    still_may_decide,
    submit_application,
    withdraw_application,
)
from black_bloc.cogs.community.role_menus import RoleMenus
from black_bloc.config import load_settings
from black_bloc.settings_store import DB_UNAVAILABLE, SettingsStore
from black_bloc.storage.db import Database

GUILD = 7
TEST_CHANNEL = 111
LOG_CHANNEL = 222
STAFF_CHANNEL = 333
ROLE = 4242
MEMBER = 900
LEAD = 1
APPROVER_ROLE = 5150


class _Refused:
    status = 403
    reason = "Forbidden"


class FakePerms:
    def __init__(self, manage_guild=False):
        self.manage_guild = manage_guild


class FakeRole:
    def __init__(self, role_id):
        self.id = role_id
        self.name = f"role-{role_id}"


class FakeMessage:
    def __init__(self, message_id, channel, **kwargs):
        self.id = message_id
        self.channel = channel
        self.kwargs = kwargs

    async def edit(self, **kwargs):
        self.kwargs |= kwargs

    @property
    def embeds(self):
        held = self.kwargs.get("embeds")
        if held is not None:
            return list(held)
        one = self.kwargs.get("embed")
        return [one] if one is not None else []


class FakeChannel:
    def __init__(self, channel_id):
        self.id = channel_id
        self.messages = []
        self.send_raises = None

    async def send(self, content=None, **kwargs):
        if self.send_raises is not None:
            raise self.send_raises
        message = FakeMessage(self.id * 100 + len(self.messages), self, content=content, **kwargs)
        self.messages.append(message)
        return message

    def get_partial_message(self, message_id):
        found = next((m for m in self.messages if m.id == message_id), None)
        if found is None:
            raise LookupError(message_id)
        return found


class FakeGuild:
    def __init__(self):
        self.id = GUILD
        self.name = "Black in a Flash!"
        self.channels = {
            LOG_CHANNEL: FakeChannel(LOG_CHANNEL),
            TEST_CHANNEL: FakeChannel(TEST_CHANNEL),
            STAFF_CHANNEL: FakeChannel(STAFF_CHANNEL),
        }
        self.members = {}
        self.me = None

    def get_channel(self, channel_id):
        return self.channels.get(channel_id)

    def get_role(self, role_id):
        return FakeRole(role_id)

    def get_member(self, user_id):
        return self.members.get(user_id)


class FakeMember:
    def __init__(self, guild, user_id=MEMBER, display_name="Ada", roles=(), manage_guild=False):
        self.id = user_id
        self.guild = guild
        self.display_name = display_name
        self.mention = f"<@{user_id}>"
        self.roles = [FakeRole(r) for r in roles]
        self.guild_permissions = FakePerms(manage_guild=manage_guild)
        self.edits = []
        self.edit_raises = None
        self.dms = []
        guild.members[user_id] = self

    async def edit(self, roles=None, reason=None):
        if self.edit_raises is not None:
            raise self.edit_raises
        self.edits.append([r.id for r in roles])
        self.roles = list(roles)

    async def send(self, content=None, **kwargs):
        self.dms.append(content)


class FakeGuard:
    def __init__(self, allowed=TEST_CHANNEL):
        self.allowed = allowed
        self.test_channel_id = TEST_CHANNEL

    def allows_channel(self, channel_id):
        return channel_id == self.allowed

    def refusal_message(self):
        return "test mode"


class FakeBot:
    def __init__(self, db, store, guild):
        self.db = db
        self.store = store
        self.guild = guild
        self.guilds = [guild]
        self.guard = None
        self.views = []
        self.dynamic = []

    def get_channel(self, channel_id):
        return self.guild.get_channel(channel_id)

    def get_guild(self, guild_id):
        return self.guild if guild_id == self.guild.id else None

    def add_view(self, view, message_id=None):
        self.views.append((view, message_id))

    def add_dynamic_items(self, *items):
        self.dynamic.extend(items)


class FakeResponse:
    def __init__(self):
        self.messages = []
        self.modals = []
        self.deferred = False

    async def send_message(self, content=None, ephemeral=False, **kwargs):
        self.messages.append({"content": content, "ephemeral": ephemeral, **kwargs})

    async def defer(self, ephemeral=False):
        self.deferred = True

    async def send_modal(self, modal):
        self.modals.append(modal)
        self.deferred = True

    def is_done(self):
        return self.deferred or bool(self.messages)


class FakeFollowup:
    def __init__(self, response):
        self.response = response

    async def send(self, content=None, ephemeral=False, **kwargs):
        self.response.messages.append({"content": content, "ephemeral": ephemeral, **kwargs})


class FakeInteraction:
    def __init__(self, bot, user, channel_id=TEST_CHANNEL, guild=True):
        self.client = bot
        self.user = user
        self.guild = bot.guild if guild else None
        self.guild_id = bot.guild.id if guild else None
        self.channel = bot.guild.get_channel(channel_id)
        self.channel_id = channel_id
        self.response = FakeResponse()
        self.followup = FakeFollowup(self.response)
        self.edits = []

    async def original_response(self):
        return FakeMessage(1, self.channel)

    async def edit_original_response(self, **kwargs):
        self.edits.append(kwargs)
        return FakeMessage(9500, self.channel, **kwargs)

    @property
    def rendered(self):
        """What the panel last put on the screen — an edit if there was one, else the send."""
        if self.edits:
            return self.edits[-1]
        return self.response.messages[-1] if self.response.messages else {}

    @property
    def view(self):
        return self.rendered.get("view")

    @property
    def sent(self):
        said = [
            one["content"] for one in self.response.messages if one.get("content") is not None
        ]
        return said[-1] if said else None

    @property
    def embed(self):
        return self.rendered.get("embed")

    @property
    def words(self):
        found = self.embed
        return "" if found is None else str(found.description or "")

    def labels(self):
        found = self.view
        return [] if found is None else [
            getattr(one, "label", None) for one in found.children
        ]

    def placeholders(self):
        found = self.view
        return [] if found is None else [
            getattr(one, "placeholder", None) for one in found.children
        ]


@pytest.fixture
async def db(tmp_path):
    database = Database(tmp_path / "app.sqlite3")
    await database.connect()
    try:
        yield database
    finally:
        await database.close()


@pytest.fixture
async def bot(db, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    settings = load_settings(_env_file=None, test_mode=True, test_channel_id=TEST_CHANNEL)
    store = SettingsStore(db, settings)
    await store.load()
    await store.set(GUILD, "log_channel_id", LOG_CHANNEL)
    await store.set(GUILD, "staff_channel_id", STAFF_CHANNEL)
    await store.set(GUILD, forms.MODE_KEY, "on")
    return FakeBot(db, store, FakeGuild())


@pytest.fixture
def lead(bot):
    return FakeMember(bot.guild, user_id=LEAD, display_name="Lead", manage_guild=True)


async def a_form(db, name="twitch-team", questions=("Twitch handle",), **kwargs):
    form_id = await forms.create_form(db, GUILD, name, "Twitch Team", ROLE, LEAD, **kwargs)
    for label in questions:
        await forms.add_question(db, form_id, label)
    return await forms.get_form_by_id(db, form_id)


async def a_list_form(db, name="stream-team", questions=("Twitch handle",)):
    form_id = await forms.create_form(db, GUILD, name, "Stream Team", None, LEAD)
    for label in questions:
        await forms.add_question(db, form_id, label)
    return await forms.get_form_by_id(db, form_id)


async def action_kinds(db):
    cur = await db.conn.execute("SELECT kind FROM action_log ORDER BY id")
    return [row["kind"] for row in await cur.fetchall()]


async def action_details(db, kind):
    cur = await db.conn.execute(
        "SELECT details FROM action_log WHERE kind = ? ORDER BY id DESC LIMIT 1", (kind,)
    )
    row = await cur.fetchone()
    return json.loads(row["details"]) if row is not None and row["details"] else {}


async def apply_once(bot, db, form, member, answers=(("Twitch handle", "ada"),)):
    return await submit_application(bot, bot.guild, member, form["id"], answers)


async def pending_row(bot, db, form, member):
    await apply_once(bot, db, form, member)
    return await forms.open_application(db, form["id"], member.id)


# §J.1 — the role-add path, and the proof the reconciler leaves it alone.


async def test_a_role_this_cog_adds_is_never_reported_as_a_change_made_by_hand(bot, db, lead):
    """§J: the approve path goes through role_menus.change_roles, which remembers the edit
    before it is made, so Phase 9's on_member_update filters it out."""
    form = await a_form(db)
    member = FakeMember(bot.guild)
    row = await pending_row(bot, db, form, member)
    before = FakeMember(FakeGuild(), display_name="Ada")
    reconciler = RoleMenus(bot)

    said, fresh = await apply_decision(bot, bot.guild, row["id"], grants.APPROVED, lead)
    after = bot.guild.get_member(member.id)
    await reconciler.on_member_update(before, after)

    assert fresh["status"] == grants.APPROVED
    assert member.edits == [[ROLE]]
    assert "role.changed_by_hand" not in await action_kinds(db)
    assert grants.was_ours(bot, GUILD, member.id, ROLE, grants.ADDED) is False


async def test_a_role_added_outside_the_cog_is_still_reported_as_by_hand(bot, db):
    """The other half of the proof: without the ledger entry the same listener does report it."""
    member = FakeMember(bot.guild)
    before = FakeMember(FakeGuild(), display_name="Ada")
    member.roles = [FakeRole(ROLE)]

    await RoleMenus(bot).on_member_update(before, member)

    assert "role.changed_by_hand" in await action_kinds(db)


# §J.2 — the persistent buttons.


async def test_the_buttons_are_registered_by_template_so_a_restart_keeps_them(bot, db, lead):
    form = await a_form(db)
    await post_panel(bot, bot.guild, form, bot.guild.get_channel(TEST_CHANNEL))
    cog = Applications(bot)

    await cog.cog_load()

    assert ApplyButton in bot.dynamic and DecisionButton in bot.dynamic
    assert [message_id for _, message_id in bot.views][-1] == (
        await forms.get_form_by_id(db, form["id"])
    )["panel_message_id"]
    assert DECIDE_TEMPLATE == r"application:(?P<application_id>[0-9]+):(?P<action>approve|deny)"


async def test_a_button_custom_id_round_trips_through_its_template(bot, db):
    import re

    match = re.fullmatch(DECIDE_TEMPLATE, DecisionButton(9, "deny").item.custom_id)

    assert match["application_id"] == "9" and match["action"] == "deny"


# The modal is built from the rows staff stored.


async def test_the_modal_is_built_from_the_questions_staff_stored(bot, db):
    form = await a_form(
        db, questions=("Twitch handle", "How long streaming", "Why the Team")
    )
    await forms.edit_question(db, form["id"], 3, style=forms.LONG, required=False)
    member = FakeMember(bot.guild)
    interaction = FakeInteraction(bot, member)

    await open_form_modal(interaction, form)

    modal = interaction.response.modals[0]
    assert isinstance(modal, ApplyModal)
    assert [label for label, _ in modal.asked] == [
        "Twitch handle",
        "How long streaming",
        "Why the Team",
    ]
    assert modal.children[2].style is discord.TextStyle.paragraph
    assert modal.children[2].required is False
    assert modal.title == "Twitch Team"


async def test_a_form_with_no_questions_refuses_in_words_and_says_which_command(bot, db):
    form = await a_form(db, questions=())
    interaction = FakeInteraction(bot, FakeMember(bot.guild))

    await open_form_modal(interaction, form)

    assert "no questions on it yet" in interaction.sent
    assert "/applications question add" in interaction.sent
    assert interaction.response.modals == []


async def test_a_closed_form_says_so_rather_than_opening(bot, db):
    form = await a_form(db)
    await forms.update_form(db, GUILD, form["name"], open=False)
    form = await forms.get_form_by_id(db, form["id"])
    interaction = FakeInteraction(bot, FakeMember(bot.guild))

    await open_form_modal(interaction, form)

    assert "not taking applications" in interaction.sent
    assert interaction.response.modals == []


async def test_the_form_refuses_to_open_while_applications_are_off(bot, db):
    await bot.store.set(GUILD, forms.MODE_KEY, "off")
    form = await a_form(db)
    interaction = FakeInteraction(bot, FakeMember(bot.guild))

    await open_form_modal(interaction, form)

    assert "turned off" in interaction.sent
    assert "applications_mode on" in interaction.sent


async def test_somebody_already_waiting_is_not_offered_the_form_again(bot, db):
    form = await a_form(db)
    member = FakeMember(bot.guild)
    await pending_row(bot, db, form, member)
    interaction = FakeInteraction(bot, member)

    await open_form_modal(interaction, form)

    assert "already have an application waiting" in interaction.sent
    assert interaction.response.modals == []


# Submitting.


async def test_submitting_stores_the_answers_with_their_labels_and_cards_them(bot, db):
    form = await a_form(db, questions=("Twitch handle", "Why the Team"))
    member = FakeMember(bot.guild)

    said = await apply_once(
        bot, db, form, member, (("Twitch handle", "ada"), ("Why the Team", "the vibes"))
    )

    row = await forms.open_application(db, form["id"], member.id)
    assert forms.read_answers(row["answers"]) == [
        {"label": "Twitch handle", "answer": "ada"},
        {"label": "Why the Team", "answer": "the vibes"},
    ]
    assert "Sent to staff" in said
    assert row["card_channel_id"] == STAFF_CHANNEL or row["card_channel_id"] == TEST_CHANNEL
    assert "application.submitted" in await action_kinds(db)
    assert member.dms and "with staff now" in member.dms[0]


async def test_a_second_application_on_the_same_form_is_refused_in_words(bot, db):
    form = await a_form(db)
    member = FakeMember(bot.guild)
    await apply_once(bot, db, form, member)

    said = await apply_once(bot, db, form, member)

    assert "already have an application waiting" in said
    assert await forms.pending_count(db, form["id"]) == 1


async def test_somebody_still_cooling_off_is_told_when_they_may_apply_again(bot, db, lead):
    form = await a_form(db)
    await forms.update_form(db, GUILD, form["name"], retry_days=30)
    form = await forms.get_form_by_id(db, form["id"])
    member = FakeMember(bot.guild)
    row = await pending_row(bot, db, form, member)
    await apply_decision(bot, bot.guild, row["id"], grants.DENIED, lead, reason="not yet")

    said = await apply_once(bot, db, form, member)

    assert "you can apply again <t:" in said
    assert await forms.pending_count(db, form["id"]) == 0


async def test_the_form_s_own_wait_beats_the_server_wide_one(bot, db, lead):
    await bot.store.set(GUILD, forms.RETRY_DAYS_KEY, 0)
    form = await a_form(db)
    member = FakeMember(bot.guild)
    row = await pending_row(bot, db, form, member)
    await apply_decision(bot, bot.guild, row["id"], grants.DENIED, lead, reason="no")

    assert "Sent to staff" in await apply_once(bot, db, form, member)


# Approving.


async def test_approving_writes_the_ledger_then_the_role_then_the_grant_row(bot, db, lead):
    form = await a_form(db)
    await forms.update_form(db, GUILD, form["name"], expires_days=7)
    form = await forms.get_form_by_id(db, form["id"])
    member = FakeMember(bot.guild)
    row = await pending_row(bot, db, form, member)

    said, fresh = await apply_decision(bot, bot.guild, row["id"], grants.APPROVED, lead)

    assert member.edits == [[ROLE]]
    grant = await grants.open_grant(db, GUILD, member.id, ROLE)
    assert grant is not None and grant["source"] == grants.APPROVAL
    assert grant["expires_at"] is not None
    assert fresh["grant_id"] == grant["id"]
    assert "application.granted" in await action_kinds(db)
    assert "application.approved" in await action_kinds(db)
    assert "Ada" in said


async def test_an_approval_carries_the_owner_nudge_onto_the_card_and_the_dm(bot, db, lead):
    form = await a_form(db)
    await forms.update_form(
        db,
        GUILD,
        form["name"],
        owner_user_id=55,
        next_step="the Team owner sends your twitch.tv invite",
    )
    form = await forms.get_form_by_id(db, form["id"])
    member = FakeMember(bot.guild)
    row = await pending_row(bot, db, form, member)

    await apply_decision(bot, bot.guild, row["id"], grants.APPROVED, lead)

    card = bot.guild.get_channel(STAFF_CHANNEL).messages[0]
    assert "<@55> — next step:" in card.kwargs["content"]
    assert card.kwargs["view"] is None
    assert any("twitch.tv invite" in said for said in member.dms)
    # The named nudge is the ONE mention a decided card may actually ping.
    allowed = card.kwargs["allowed_mentions"]
    assert [one.id for one in allowed.users] == [55]
    assert allowed.roles is False and allowed.everyone is False


async def test_a_form_with_no_owner_pings_nobody_at_all(bot, db):
    form = await a_form(db)
    assert nudge_mentions(form).users is False


async def test_a_refused_role_leaves_the_application_approved_and_says_so(bot, db, lead):
    form = await a_form(db)
    member = FakeMember(bot.guild)
    member.edit_raises = discord.HTTPException(_Refused(), "no")
    row = await pending_row(bot, db, form, member)

    said, fresh = await apply_decision(bot, bot.guild, row["id"], grants.APPROVED, lead)

    assert fresh["status"] == grants.APPROVED and fresh["grant_id"] is None
    assert "application.grant_failed" in await action_kinds(db)
    assert "Discord refused to add" in said and "/role grant" in said
    card = bot.guild.get_channel(STAFF_CHANNEL).messages[0]
    assert "Discord refused to add the role" in card.kwargs["content"]


async def test_a_second_decider_is_told_somebody_got_there_first(bot, db, lead):
    form = await a_form(db)
    member = FakeMember(bot.guild)
    row = await pending_row(bot, db, form, member)
    await apply_decision(bot, bot.guild, row["id"], grants.APPROVED, lead)

    said, fresh = await apply_decision(
        bot, bot.guild, row["id"], grants.DENIED, lead, reason="too late"
    )

    assert fresh is None and "already **approved**" in said


async def test_an_applicant_who_has_left_is_named_and_the_row_stays_pending(bot, db, lead):
    form = await a_form(db)
    member = FakeMember(bot.guild)
    row = await pending_row(bot, db, form, member)
    bot.guild.members.pop(member.id)

    said, fresh = await apply_decision(bot, bot.guild, row["id"], grants.APPROVED, lead)

    assert fresh is None and "not in this server any more" in said
    assert (await forms.get_application(db, row["id"]))["status"] == grants.PENDING


# Denying and withdrawing.


async def test_denying_needs_a_reason_and_sends_it_to_the_applicant(bot, db, lead):
    form = await a_form(db)
    member = FakeMember(bot.guild)
    row = await pending_row(bot, db, form, member)

    blank, nothing = await apply_decision(
        bot, bot.guild, row["id"], grants.DENIED, lead, reason="   "
    )
    assert nothing is None and "needs one line" in blank
    assert (await forms.get_application(db, row["id"]))["status"] == grants.PENDING

    said, fresh = await apply_decision(
        bot, bot.guild, row["id"], grants.DENIED, lead, reason="not enough hours yet"
    )

    assert fresh["deny_reason"] == "not enough hours yet"
    assert "application.denied" in await action_kinds(db)
    assert any("not enough hours yet" in one for one in member.dms)
    assert said == forms.DENIED_SAID


async def test_the_applicant_may_take_their_own_application_back(bot, db):
    form = await a_form(db)
    member = FakeMember(bot.guild)
    await pending_row(bot, db, form, member)

    said = await withdraw_application(bot, bot.guild, member, form)

    assert "Taken back" in said
    assert await forms.pending_count(db, form["id"]) == 0
    assert "application.withdrawn" in await action_kinds(db)


async def test_nobody_else_can_withdraw_it_because_the_lookup_is_by_their_own_id(bot, db):
    form = await a_form(db)
    member = FakeMember(bot.guild)
    other = FakeMember(bot.guild, user_id=901, display_name="Bo")
    await pending_row(bot, db, form, member)

    said = await withdraw_application(bot, bot.guild, other, form)

    assert "nothing waiting" in said
    assert await forms.pending_count(db, form["id"]) == 1


# Modes and the guard.


async def test_shadow_posts_nothing_dms_nobody_and_hands_no_role_over(bot, db, lead):
    await bot.store.set(GUILD, forms.MODE_KEY, "shadow")
    form = await a_form(db)
    member = FakeMember(bot.guild)
    row = await pending_row(bot, db, form, member)

    await apply_decision(bot, bot.guild, row["id"], grants.APPROVED, lead)

    kinds = await action_kinds(db)
    assert "application.would_post" in kinds
    assert "application.would_dm" in kinds
    assert "application.would_grant" in kinds
    assert member.edits == [] and member.dms == []
    assert bot.guild.get_channel(TEST_CHANNEL).messages == []
    assert await grants.open_grant(db, GUILD, member.id, ROLE) is None
    assert mode_of(bot, GUILD) == "shadow"


async def test_a_card_bound_for_a_refused_channel_lands_in_the_test_channel_and_says_so(
    bot, db
):
    bot.guard = FakeGuard(allowed=TEST_CHANNEL)
    form = await a_form(db)
    member = FakeMember(bot.guild)

    said = await apply_once(bot, db, form, member)

    assert "Test mode is on" in said
    assert "application.post_skipped_test_mode" in await action_kinds(db)
    assert bot.guild.get_channel(TEST_CHANNEL).messages
    assert bot.guild.get_channel(STAFF_CHANNEL).messages == []


async def test_a_card_with_nowhere_to_go_says_the_application_is_still_saved(bot, db):
    await bot.store.set(GUILD, forms.CHANNEL_KEY, 999999)
    form = await a_form(db)
    member = FakeMember(bot.guild)

    said = await apply_once(bot, db, form, member)

    assert "could not put the card in front of staff" in said
    assert "application.post_failed" in await action_kinds(db)
    assert await forms.pending_count(db, form["id"]) == 1


async def test_a_decision_click_from_outside_the_test_channel_is_refused(bot, db, lead):
    bot.guard = FakeGuard(allowed=TEST_CHANNEL)
    form = await a_form(db)
    member = FakeMember(bot.guild)
    row = await pending_row(bot, db, form, member)
    interaction = FakeInteraction(bot, lead, channel_id=LOG_CHANNEL)

    await DecisionButton(row["id"], "approve").on_click(interaction)

    assert interaction.sent == "test mode"
    assert (await forms.get_application(db, row["id"]))["status"] == grants.PENDING


# Who may decide.


async def test_the_deny_click_opens_the_reason_modal_rather_than_deciding(bot, db, lead):
    form = await a_form(db)
    member = FakeMember(bot.guild)
    row = await pending_row(bot, db, form, member)
    interaction = FakeInteraction(bot, lead)

    await DecisionButton(row["id"], "deny").on_click(interaction)

    assert isinstance(interaction.response.modals[0], DenyModal)
    assert (await forms.get_application(db, row["id"]))["status"] == grants.PENDING


async def test_somebody_without_the_approver_role_is_told_which_role_it_needs(bot, db):
    form = await a_form(db, approver_role_id=APPROVER_ROLE)
    member = FakeMember(bot.guild)
    row = await pending_row(bot, db, form, member)
    passerby = FakeMember(bot.guild, user_id=902, display_name="Cass")
    interaction = FakeInteraction(bot, passerby)

    await DecisionButton(row["id"], "approve").on_click(interaction)

    assert interaction.sent == NOT_AN_APPROVER.format(
        role_id=APPROVER_ROLE, name="twitch-team"
    )
    assert (await forms.get_application(db, row["id"]))["status"] == grants.PENDING


async def test_holding_the_approver_role_is_enough_without_being_staff(bot, db):
    form = await a_form(db, approver_role_id=APPROVER_ROLE)
    member = FakeMember(bot.guild)
    row = await pending_row(bot, db, form, member)
    approver = FakeMember(bot.guild, user_id=903, display_name="Dee", roles=(APPROVER_ROLE,))
    interaction = FakeInteraction(bot, approver)

    await DecisionButton(row["id"], "approve").on_click(interaction)

    assert (await forms.get_application(db, row["id"]))["status"] == grants.APPROVED
    assert approver_role_id(bot, GUILD, form) == APPROVER_ROLE


async def test_the_review_channel_falls_back_through_the_settings_in_order(bot, db):
    form = await a_form(db)
    assert review_channel(bot, bot.guild, form).id == STAFF_CHANNEL

    await bot.store.set(GUILD, "rolemenu_approval_channel_id", LOG_CHANNEL)
    assert review_channel(bot, bot.guild, form).id == LOG_CHANNEL

    await bot.store.set(GUILD, forms.CHANNEL_KEY, TEST_CHANNEL)
    assert review_channel(bot, bot.guild, form).id == TEST_CHANNEL




# A form that keeps a list instead of handing a role over.


async def test_approving_on_a_list_form_hands_nothing_over_and_still_tells_them(bot, db, lead):
    form = await a_list_form(db)
    member = FakeMember(bot.guild)
    row = await pending_row(bot, db, form, member)

    said, fresh = await apply_decision(bot, bot.guild, row["id"], grants.APPROVED, lead)

    assert fresh["status"] == grants.APPROVED
    assert member.edits == [] and fresh["grant_id"] is None
    assert await grants.open_grant(db, GUILD, member.id, ROLE) is None
    kinds = await action_kinds(db)
    assert "application.approved" in kinds
    assert "application.granted" not in kinds and "application.grant_failed" not in kinds
    details = await action_details(db, "application.approved")
    assert details["granted"] is None and details["role_id"] is None
    assert any("on the Stream Team list" in one for one in member.dms) or member.dms
    assert "is on the **Stream Team** list now" in said
    assert "Discord refused" not in said
    card = bot.guild.get_channel(STAFF_CHANNEL).messages[0]
    assert "is on the **Stream Team** list now" in card.kwargs["content"]


async def test_a_shadow_run_on_a_list_form_never_reaches_the_would_grant_line(bot, db, lead):
    await bot.store.set(GUILD, forms.MODE_KEY, "shadow")
    form = await a_list_form(db)
    member = FakeMember(bot.guild)
    row = await pending_row(bot, db, form, member)

    await apply_decision(bot, bot.guild, row["id"], grants.APPROVED, lead)

    assert "application.would_grant" not in await action_kinds(db)


async def test_staff_can_take_somebody_off_a_list_and_they_are_told_why(bot, db, lead):
    form = await a_list_form(db)
    await forms.update_form(db, GUILD, form["name"], retry_days=30)
    form = await forms.get_form_by_id(db, form["id"])
    member = FakeMember(bot.guild)
    row = await pending_row(bot, db, form, member)
    await apply_decision(bot, bot.guild, row["id"], grants.APPROVED, lead)
    member.dms.clear()

    said, fresh = await remove(bot, bot.guild, row["id"], lead, "stopped streaming")

    assert said == forms.REMOVED_SAID
    assert fresh["status"] == forms.REMOVED and fresh["deny_reason"] == "stopped streaming"
    assert "application.removed" in await action_kinds(db)
    assert any("stopped streaming" in one for one in member.dms)
    card = bot.guild.get_channel(STAFF_CHANNEL).messages[0]
    assert card.kwargs["content"] == forms.REMOVED_SAID


async def test_taking_somebody_off_a_role_form_points_at_role_revoke_instead(bot, db, lead):
    form = await a_form(db)
    member = FakeMember(bot.guild)
    row = await pending_row(bot, db, form, member)
    await apply_decision(bot, bot.guild, row["id"], grants.APPROVED, lead)

    said, fresh = await remove(bot, bot.guild, row["id"], lead, "no longer needed")

    assert fresh is None
    assert said == REMOVE_IS_FOR_LISTS.format(name="twitch-team", role=ROLE)
    assert (await forms.get_application(db, row["id"]))["status"] == grants.APPROVED
    assert "application.removed" not in await action_kinds(db)


async def test_taking_somebody_off_needs_a_reason_and_an_approved_row(bot, db, lead):
    form = await a_list_form(db)
    member = FakeMember(bot.guild)
    row = await pending_row(bot, db, form, member)

    waiting, nothing = await remove(bot, bot.guild, row["id"], lead, "too soon")
    assert nothing is None and "not approved" in waiting

    await apply_decision(bot, bot.guild, row["id"], grants.APPROVED, lead)
    blank, still_nothing = await remove(bot, bot.guild, row["id"], lead, "   ")

    assert still_nothing is None and "needs one line" in blank
    assert (await forms.get_application(db, row["id"]))["status"] == grants.APPROVED



# The panel — `/apply` is one command, and both halves come out of one embed.


async def open_panel(bot, user):
    interaction = FakeInteraction(bot, user)
    await Applications.apply.callback(Applications(bot), interaction)
    return interaction


def picks(interaction, kind):
    view = interaction.view
    return [one for one in (view.children if view is not None else ()) if isinstance(one, kind)]


async def test_the_command_answers_ephemerally_with_one_panel(bot, db):
    await a_form(db)
    interaction = await open_panel(bot, FakeMember(bot.guild))

    said = interaction.response.messages[-1]
    assert said["ephemeral"] is True
    assert said["embed"].title == forms.PANEL_TITLE
    assert said["allowed_mentions"].roles is False
    assert forms.PANEL_INTRO in interaction.words


async def test_a_member_gets_apply_for_and_none_of_the_staff_controls(bot, db):
    await a_form(db)
    interaction = await open_panel(bot, FakeMember(bot.guild))

    assert picks(interaction, ApplyPick)
    assert not picks(interaction, QueuePick)
    assert not picks(interaction, FormPick)
    assert not picks(interaction, LogsButton)
    assert "Settings" not in interaction.labels()
    assert "New form" not in interaction.labels()


async def test_staff_get_the_queue_the_forms_and_the_five_buttons(bot, db, lead):
    form = await a_form(db)
    await pending_row(bot, db, form, FakeMember(bot.guild))

    interaction = await open_panel(bot, lead)

    assert picks(interaction, QueuePick) and picks(interaction, FormPick)
    assert picks(interaction, LogsButton)
    for label in ("New form", "Find #…", "Settings", "Logs", "Refresh"):
        assert label in interaction.labels()
    assert not picks(interaction, ApplyPick)


async def test_an_approver_who_is_not_staff_sees_only_the_queue_for_their_own_form(bot, db):
    theirs = await a_form(db, name="twitch-team", approver_role_id=APPROVER_ROLE)
    other = await a_form(db, name="mod-team")
    approver = FakeMember(bot.guild, user_id=903, display_name="Dee", roles=(APPROVER_ROLE,))
    mine = await pending_row(bot, db, theirs, FakeMember(bot.guild))
    await pending_row(bot, db, other, FakeMember(bot.guild, user_id=904, display_name="Eve"))

    interaction = await open_panel(bot, approver)

    queue = picks(interaction, QueuePick)[0]
    assert [one.value for one in queue.options] == [str(mine["id"])]
    assert not picks(interaction, FormPick)
    assert not picks(interaction, LogsButton)


async def test_the_mode_being_off_says_so_in_words_and_renders_no_apply_control(bot, db):
    """Owner, 2026-09-03 13:47 — "Visible": the command stays, the control does not."""
    await a_form(db)
    await bot.store.set(GUILD, forms.MODE_KEY, "off")

    interaction = await open_panel(bot, FakeMember(bot.guild))

    assert forms.APPLICATIONS_OFF in interaction.words
    assert not picks(interaction, ApplyPick)


async def test_a_member_sees_their_own_applications_or_not_by_the_key(bot, db):
    form = await a_form(db)
    member = FakeMember(bot.guild)
    await pending_row(bot, db, form, member)

    on = await open_panel(bot, member)
    assert "Twitch Team" in on.words
    assert forms.STATUS_WAITING.strip(", ") in on.words

    await bot.store.set(GUILD, forms.PANEL_OWN_LIST_KEY, False)
    off = await open_panel(bot, member)

    assert "Twitch Team" not in off.words


async def test_a_member_who_has_applied_for_nothing_is_told_so_plainly(bot, db):
    await a_form(db)

    interaction = await open_panel(bot, FakeMember(bot.guild))

    assert forms.NOTHING_OF_YOURS in interaction.words


async def test_the_queue_caps_at_twenty_five_and_the_placeholder_says_so(bot, db, lead):
    form = await a_form(db)
    for at in range(27):
        member = FakeMember(bot.guild, user_id=2000 + at, display_name=f"P{at}")
        await pending_row(bot, db, form, member)

    interaction = await open_panel(bot, lead)

    queue = picks(interaction, QueuePick)[0]
    assert len(queue.options) == 25
    assert "25 of 27" in queue.placeholder


async def test_a_staffer_with_something_of_their_own_waiting_can_take_it_back(bot, db, lead):
    form = await a_form(db)
    await pending_row(bot, db, form, lead)

    interaction = await open_panel(bot, lead)
    withdraw = picks(interaction, WithdrawPick)[0]
    picking = FakeInteraction(bot, lead)
    withdraw._values = [str(form["id"])]
    await withdraw.callback(picking)
    yes = next(one for one in picking.view.children if one.label.startswith("Yes"))
    confirming = FakeInteraction(bot, lead)
    await yes.callback(confirming)

    assert await forms.open_application(db, form["id"], lead.id) is None
    assert "application.withdrawn" in await action_kinds(db)


# The application card — the table is data, and every status renders its own row.


@pytest.mark.parametrize(
    "status,expected",
    [
        (grants.PENDING, ["Approve", "Deny"]),
        (grants.APPROVED, ["Take off the list"]),
        (grants.DENIED, ["Approve after all"]),
        (grants.WITHDRAWN, []),
        (forms.REMOVED, ["Put them back on the list"]),
    ],
)
def test_every_status_renders_exactly_its_row_of_the_button_table(status, expected):
    moves = forms.card_buttons(status, has_role=False, may_decide=True)
    assert [one.label for one in moves] == expected


def test_an_approved_role_form_offers_nothing_and_a_stranger_offers_nothing_either():
    assert forms.card_buttons(grants.APPROVED, has_role=True, may_decide=True) == ()
    assert forms.card_buttons(grants.PENDING, has_role=False, may_decide=False) == ()


async def test_the_card_says_where_an_approved_role_application_can_go_instead(bot, db, lead):
    form = await a_form(db)
    member = FakeMember(bot.guild)
    row = await pending_row(bot, db, form, member)
    await apply_decision(bot, bot.guild, row["id"], grants.APPROVED, lead)
    fresh = await forms.get_application(db, row["id"])

    embed, view = build_card(bot, bot.guild, form, fresh, lead)

    assert [one.label for one in view.children] == ["Back"]
    assert any("/role revoke" in field.value for field in embed.fields)


async def test_a_withdrawn_card_says_the_member_owns_it(bot, db):
    form = await a_form(db)
    member = FakeMember(bot.guild)
    row = await pending_row(bot, db, form, member)
    await withdraw_application(bot, bot.guild, member, form)
    fresh = await forms.get_application(db, row["id"])

    embed, view = build_card(bot, bot.guild, form, fresh, member)

    assert [one.label for one in view.children] == ["Back"]
    assert any(forms.WITHDRAWN_IS_THEIRS in field.value for field in embed.fields)


async def test_approving_from_the_card_is_the_same_write_the_channel_card_makes(bot, db, lead):
    form = await a_list_form(db)
    member = FakeMember(bot.guild)
    row = await pending_row(bot, db, form, member)
    button = CardMoveButton(row["id"], form["id"], forms.APPROVE)
    interaction = FakeInteraction(bot, lead)

    await button.callback(interaction)

    fresh = await forms.get_application(db, row["id"])
    assert fresh["status"] == grants.APPROVED
    kinds = await action_kinds(db)
    assert kinds.count("application.approved") == 1
    assert "web.application.approved" not in kinds


async def test_denying_from_the_card_goes_through_a_note_modal_that_carries_the_reason(
    bot, db, lead
):
    form = await a_form(db)
    member = FakeMember(bot.guild)
    row = await pending_row(bot, db, form, member)
    button = CardMoveButton(row["id"], form["id"], forms.DENY)
    opening = FakeInteraction(bot, lead)

    await button.callback(opening)
    modal = opening.response.modals[0]
    assert modal.note.max_length == forms.REASON_MAX
    submitting = FakeInteraction(bot, lead)
    await modal.sent(submitting, "not this time")

    fresh = await forms.get_application(db, row["id"])
    assert fresh["status"] == grants.DENIED and fresh["deny_reason"] == "not this time"
    assert (await action_kinds(db)).count("application.denied") == 1


async def test_a_staffer_demoted_while_the_card_is_open_moves_nothing(bot, db, lead):
    form = await a_list_form(db)
    member = FakeMember(bot.guild)
    row = await pending_row(bot, db, form, member)
    button = CardMoveButton(row["id"], form["id"], forms.APPROVE)
    stranger = FakeMember(bot.guild, user_id=905, display_name="Nobody")
    interaction = FakeInteraction(bot, stranger)

    await button.callback(interaction)

    assert (await forms.get_application(db, row["id"]))["status"] == grants.PENDING
    assert "staff only" in interaction.sent


async def test_still_may_decide_names_the_approver_role_instead_of_a_bare_refusal(bot, db):
    form = await a_form(db, approver_role_id=APPROVER_ROLE)
    stranger = FakeMember(bot.guild, user_id=906, display_name="Nobody")
    interaction = FakeInteraction(bot, stranger)

    assert await still_may_decide(interaction, form) is False
    assert NOT_AN_APPROVER.format(role_id=APPROVER_ROLE, name="twitch-team") == interaction.sent


# Staff's exit from a no — `denied` and `removed` go back to `approved`.


async def test_a_denied_application_can_be_approved_after_all(bot, db, lead):
    form = await a_form(db)
    member = FakeMember(bot.guild)
    row = await pending_row(bot, db, form, member)
    await apply_decision(bot, bot.guild, row["id"], grants.DENIED, lead, reason="no")
    member.dms.clear()

    said, fresh = await reinstate(bot, bot.guild, row["id"], lead)

    assert fresh["status"] == grants.APPROVED and fresh["deny_reason"] is None
    assert member.edits == [[ROLE]]
    assert (await action_kinds(db)).count("application.approved") == 1
    assert any("approved" in one for one in member.dms)
    assert f"#{row['id']}" in said


async def test_somebody_taken_off_a_list_can_be_put_back_on_it(bot, db, lead):
    form = await a_list_form(db)
    member = FakeMember(bot.guild)
    row = await pending_row(bot, db, form, member)
    await apply_decision(bot, bot.guild, row["id"], grants.APPROVED, lead)
    await remove(bot, bot.guild, row["id"], lead, "stopped streaming")

    said, fresh = await reinstate(bot, bot.guild, row["id"], lead)

    assert fresh["status"] == grants.APPROVED
    assert "on the **Stream Team** list" in said or f"#{row['id']}" in said


async def test_a_pending_or_withdrawn_application_is_not_something_to_put_back(bot, db, lead):
    form = await a_form(db)
    member = FakeMember(bot.guild)
    row = await pending_row(bot, db, form, member)

    waiting, nothing = await reinstate(bot, bot.guild, row["id"], lead)
    assert nothing is None and grants.PENDING in waiting

    await withdraw_application(bot, bot.guild, member, form)
    gone, still_nothing = await reinstate(bot, bot.guild, row["id"], lead)

    assert still_nothing is None and grants.WITHDRAWN in gone
    assert (await forms.get_application(db, row["id"]))["status"] == grants.WITHDRAWN


# Find #… reaches a settled row the queue select never lists.


async def test_find_opens_the_card_for_a_settled_application(bot, db, lead):
    form = await a_form(db)
    member = FakeMember(bot.guild)
    row = await pending_row(bot, db, form, member)
    await apply_decision(bot, bot.guild, row["id"], grants.DENIED, lead, reason="no")
    interaction = FakeInteraction(bot, lead)

    await open_card(interaction, row["id"])

    assert interaction.embed.title.endswith("Twitch Team")
    assert "Approve after all" in interaction.labels()


async def test_find_refuses_a_number_from_another_server_without_leaking_it(bot, db, lead):
    interaction = FakeInteraction(bot, lead)

    await open_card(interaction, 999)

    assert "no application with that number" in interaction.sent


def test_a_number_is_read_off_a_card_with_or_without_the_hash():
    assert forms.application_id_from("#12") == 12
    assert forms.application_id_from(" 12 ") == 12
    assert forms.application_id_from("twelve") is None


# The form card, its sub-panels, and the five writes that used to be inline.


async def test_the_mode_write_leaves_one_row_and_says_what_it_does(bot, db, lead):
    said, value = await set_mode(bot, bot.guild, lead, "shadow")

    assert bot.store.get(GUILD, forms.MODE_KEY) == "shadow" and value == "shadow"
    assert said == MODE_SAID["shadow"]
    assert (await action_kinds(db)).count("application.mode") == 1


async def test_making_a_form_names_the_next_step_and_the_question_cap(bot, db, lead):
    said, form = await make_form(bot, bot.guild, lead, "twitch-team", "Twitch Team", role_id=ROLE)

    assert form is not None and await forms.get_form(db, GUILD, "twitch-team") is not None
    assert "Questions…" in said and str(forms.QUESTIONS_MAX) in said
    assert (await action_kinds(db)).count("application.form_created") == 1


async def test_a_form_name_that_is_not_a_slug_is_refused_before_anything_is_written(bot, db, lead):
    said, form = await make_form(bot, bot.guild, lead, "Twitch Team!", "Twitch Team")

    assert form is None and "lower-case letters" in said
    assert await forms.list_forms(db, GUILD) == []


async def test_a_form_can_be_made_with_no_role_at_all(bot, db, lead):
    _, form = await make_form(bot, bot.guild, lead, "stream-team", "Stream Team")

    assert form is not None and forms.role_of(form) is None
    assert (await action_details(db, "application.form_created"))["role_id"] is None


async def test_a_form_with_people_waiting_on_it_refuses_to_be_deleted(bot, db, lead):
    form = await a_form(db)
    await pending_row(bot, db, form, FakeMember(bot.guild))

    said, gone = await drop_form(bot, bot.guild, lead, form)

    assert gone is None and "still has 1 application(s) waiting" in said
    assert await forms.get_form(db, GUILD, "twitch-team") is not None


async def test_the_form_card_hides_delete_while_somebody_is_waiting_and_says_why(bot, db, lead):
    form = await a_form(db)
    await pending_row(bot, db, form, FakeMember(bot.guild))

    embed, view = await build_form_card(bot, bot.guild, form, lead)

    assert "Delete" not in [getattr(one, "label", None) for one in view.children]
    assert "waiting on staff" in embed.description


async def test_the_form_card_offers_a_roster_only_where_the_form_keeps_a_list(bot, db, lead):
    role_form = await a_form(db)
    list_form = await a_list_form(db)

    _, with_role = await build_form_card(bot, bot.guild, role_form, lead)
    _, with_list = await build_form_card(bot, bot.guild, list_form, lead)

    assert "Roster" not in [getattr(one, "label", None) for one in with_role.children]
    assert "Roster" in [getattr(one, "label", None) for one in with_list.children]


async def test_clearing_the_role_select_leaves_the_form_keeping_a_list(bot, db, lead):
    form = await a_form(db)

    said, fresh = await save_form(bot, bot.guild, lead, form, {"role_id": forms.NO_ROLE})

    assert forms.role_of(fresh) is None and "Saved" in said
    assert (await action_kinds(db)).count("application.form_updated") == 1
    lines = forms.form_lines([fresh])
    assert lines == ["**twitch-team** — open, list"]


async def test_clearing_the_approver_select_clears_the_column_too(bot, db, lead):
    form = await a_form(db, approver_role_id=APPROVER_ROLE)

    _, fresh = await save_form(bot, bot.guild, lead, form, {"approver_role_id": forms.NO_ROLE})

    assert fresh["approver_role_id"] is None


async def test_the_form_card_names_the_role_a_role_form_hands_over(bot, db, lead):
    form = await a_form(db)

    embed, _ = await build_form_card(bot, bot.guild, form, lead)

    assert f"<@&{ROLE}>" in embed.description
    assert "<@&None>" not in embed.description


async def test_posting_the_apply_button_remembers_where_it_went(bot, db, lead):
    form = await a_form(db)

    said, message = await put_panel_up(
        bot, bot.guild, lead, form, bot.guild.get_channel(TEST_CHANNEL)
    )

    fresh = await forms.get_form(db, GUILD, "twitch-team")
    assert message is not None and fresh["panel_channel_id"] == TEST_CHANNEL
    assert (await action_kinds(db)).count("application.panel_posted") == 1
    assert f"<#{TEST_CHANNEL}>" in said


async def test_posting_refuses_a_channel_test_mode_will_not_let_it_speak_in(bot, db, lead):
    bot.guard = FakeGuard(allowed=TEST_CHANNEL)
    form = await a_form(db)

    said, message = await put_panel_up(
        bot, bot.guild, lead, form, bot.guild.get_channel(LOG_CHANNEL)
    )

    assert message is None and said == "test mode"
    assert (await forms.get_form(db, GUILD, "twitch-team"))["panel_message_id"] is None


async def test_questions_are_added_edited_and_removed_one_at_a_time(bot, db, lead):
    _, form = await make_form(bot, bot.guild, lead, "twitch-team", "Twitch Team")

    added, rows = await change_question(
        bot, bot.guild, lead, form, "added", label="Twitch handle"
    )
    assert "Added" in added and [one["label"] for one in rows] == ["Twitch handle"]

    edited, rows = await change_question(
        bot, bot.guild, lead, form, "edited", position=1, label="Your Twitch", style=forms.LONG
    )
    assert "Saved question 1" in edited
    assert rows[0]["label"] == "Your Twitch" and rows[0]["style"] == forms.LONG

    removed, rows = await change_question(bot, bot.guild, lead, form, "removed", position=1)
    assert "Removed question 1" in removed and rows == []
    assert (await action_kinds(db)).count("application.question_changed") == 3


async def test_a_slot_nobody_filled_is_refused_in_words(bot, db, lead):
    form = await a_form(db)

    said, rows = await change_question(bot, bot.guild, lead, form, "removed", position=4)

    assert rows is None and "nothing in slot 4" in said


async def test_the_questions_sub_panel_lists_them_and_points_reorder_at_the_site(bot, db, lead):
    form = await a_form(db, questions=("Twitch handle", "Why the Team"))
    interaction = FakeInteraction(bot, lead)

    await render_questions(interaction, form["id"])

    assert "**1.** Twitch handle" in interaction.words
    assert "Role menus page" in interaction.words
    assert "Add…" in interaction.labels()


async def test_the_roster_lists_the_approved_with_their_twitch_logins(bot, db, lead):
    form = await a_list_form(db)
    member = FakeMember(bot.guild)
    await db.conn.execute(
        "INSERT INTO golive_links(user_id, twitch_login, twitch_user_id, linked_at) "
        "VALUES (?, 'ada', '1', 'then')",
        (member.id,),
    )
    await db.conn.commit()
    row = await pending_row(bot, db, form, member)
    await apply_decision(bot, bot.guild, row["id"], grants.APPROVED, lead)
    interaction = FakeInteraction(bot, lead)

    await render_roster(interaction, form["id"])

    assert "twitch.tv/ada" in interaction.words
    assert "Take somebody off…" in interaction.placeholders()


async def test_the_settings_sub_panel_writes_every_value_it_shows(bot, db, lead):
    interaction = FakeInteraction(bot, lead)

    await render_settings(interaction)

    assert "**Mode:** on" in interaction.words
    assert "**Members see their own list:** on" in interaction.words
    assert "Mode…" in interaction.placeholders()


async def test_the_logs_button_answers_a_new_message_and_still_refuses_a_stranger(bot, db):
    stranger = FakeMember(bot.guild, user_id=907, display_name="Nobody")
    interaction = FakeInteraction(bot, stranger)

    await LogsButton().callback(interaction)

    assert "staff only" in interaction.sent


async def test_a_re_render_retires_the_view_it_replaced(bot, db, lead):
    await a_form(db)
    opening = await open_panel(bot, lead)
    first = opening.view
    interaction = FakeInteraction(bot, lead)

    await render_panel(interaction, first)

    assert first.replaced is True and first.is_finished() is True


async def test_the_panel_disables_every_item_and_says_so_on_timeout(bot, db, lead):
    await a_form(db)
    interaction = await open_panel(bot, lead)
    view = interaction.view
    view.message = FakeMessage(1, bot.guild.get_channel(TEST_CHANNEL), embeds=[interaction.embed])

    await view.on_timeout()

    assert all(one.disabled for one in view.children)
    assert view.message.kwargs["embeds"][0].footer.text == forms.PANEL_TIMEOUT_FOOTER


async def test_every_click_re_asks_whether_the_database_is_there(bot, db, lead):
    await a_form(db)
    interaction = await open_panel(bot, lead)
    view = interaction.view
    refresh = next(one for one in view.children if getattr(one, "label", "") == "Refresh")
    bot.db = SimpleNamespace(is_connected=False, conn=db.conn)
    clicking = FakeInteraction(bot, lead)

    await refresh.callback(clicking)

    assert clicking.sent == DB_UNAVAILABLE
