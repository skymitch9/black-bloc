import discord
import pytest

from black_bloc import applications as forms
from black_bloc import rolegrants as grants
from black_bloc.cogs.community.applications import (
    DECIDE_TEMPLATE,
    MODE_SAID,
    NOT_AN_APPROVER,
    Applications,
    ApplyButton,
    ApplyModal,
    DecisionButton,
    DenyModal,
    apply_decision,
    approver_role_id,
    mode_of,
    open_form_modal,
    post_panel,
    review_channel,
    submit_application,
    withdraw_application,
)
from black_bloc.cogs.community.role_menus import RoleMenus
from black_bloc.config import load_settings
from black_bloc.settings_store import SettingsStore
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
    def __init__(self, bot, user, channel_id=TEST_CHANNEL):
        self.client = bot
        self.user = user
        self.guild = bot.guild
        self.guild_id = bot.guild.id
        self.channel = bot.guild.get_channel(channel_id)
        self.channel_id = channel_id
        self.response = FakeResponse()
        self.followup = FakeFollowup(self.response)

    @property
    def sent(self):
        return self.response.messages[-1]["content"] if self.response.messages else None

    @property
    def embed(self):
        return self.response.messages[-1].get("embed") if self.response.messages else None


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


async def action_kinds(db):
    cur = await db.conn.execute("SELECT kind FROM action_log ORDER BY id")
    return [row["kind"] for row in await cur.fetchall()]


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


# The slash commands.


async def test_the_mode_command_says_what_each_setting_actually_does(bot, db, lead):
    interaction = FakeInteraction(bot, lead)

    await Applications.applications_mode.callback(
        Applications(bot), interaction, _Choice("shadow")
    )

    assert bot.store.get(GUILD, forms.MODE_KEY) == "shadow"
    assert interaction.sent == MODE_SAID["shadow"]
    assert "application.mode" in await action_kinds(db)


async def test_creating_a_form_names_the_next_step_and_the_question_cap(bot, db, lead):
    interaction = FakeInteraction(bot, lead)

    await Applications.applications_create.callback(
        Applications(bot), interaction, "twitch-team", "Twitch Team", FakeRole(ROLE)
    )

    assert await forms.get_form(db, GUILD, "twitch-team") is not None
    assert "/applications question add twitch-team" in interaction.sent
    assert str(forms.QUESTIONS_MAX) in interaction.sent
    assert "application.form_created" in await action_kinds(db)


async def test_a_form_name_that_is_not_a_slug_is_refused_before_anything_is_written(
    bot, db, lead
):
    interaction = FakeInteraction(bot, lead)

    await Applications.applications_create.callback(
        Applications(bot), interaction, "Twitch Team!", "Twitch Team", FakeRole(ROLE)
    )

    assert "lower-case letters" in interaction.sent
    assert await forms.list_forms(db, GUILD) == []


async def test_a_form_with_people_waiting_on_it_refuses_to_be_deleted(bot, db, lead):
    form = await a_form(db)
    await pending_row(bot, db, form, FakeMember(bot.guild))
    interaction = FakeInteraction(bot, lead)

    await Applications.applications_delete.callback(
        Applications(bot), interaction, "twitch-team"
    )

    assert "still has 1 application(s) waiting" in interaction.sent
    assert await forms.get_form(db, GUILD, "twitch-team") is not None


async def test_the_panel_command_puts_the_apply_button_up_and_remembers_it(bot, db, lead):
    await a_form(db)
    interaction = FakeInteraction(bot, lead)

    await Applications.applications_panel.callback(
        Applications(bot), interaction, "twitch-team", None
    )

    form = await forms.get_form(db, GUILD, "twitch-team")
    assert form["panel_channel_id"] == TEST_CHANNEL and form["panel_message_id"]
    assert "application.panel_posted" in await action_kinds(db)
    assert f"<#{TEST_CHANNEL}>" in interaction.sent


async def test_the_panel_refuses_a_channel_test_mode_will_not_let_it_speak_in(bot, db, lead):
    bot.guard = FakeGuard(allowed=TEST_CHANNEL)
    await a_form(db)
    interaction = FakeInteraction(bot, lead)

    await Applications.applications_panel.callback(
        Applications(bot), interaction, "twitch-team", bot.guild.get_channel(LOG_CHANNEL)
    )

    assert interaction.sent == "test mode"
    assert (await forms.get_form(db, GUILD, "twitch-team"))["panel_message_id"] is None


async def test_status_lists_only_the_callers_own_applications(bot, db):
    form = await a_form(db)
    member = FakeMember(bot.guild)
    other = FakeMember(bot.guild, user_id=901, display_name="Bo")
    await pending_row(bot, db, form, member)
    await pending_row(bot, db, form, other)
    interaction = FakeInteraction(bot, member)

    await Applications.apply_status.callback(Applications(bot), interaction)

    assert interaction.sent.count("Twitch Team") == 1
    assert "waiting on staff" in interaction.sent


async def test_status_says_so_plainly_when_they_have_applied_for_nothing(bot, db):
    interaction = FakeInteraction(bot, FakeMember(bot.guild))

    await Applications.apply_status.callback(Applications(bot), interaction)

    assert "not applied for anything" in interaction.sent


async def test_show_renders_the_card_with_the_answers_on_it(bot, db, lead):
    form = await a_form(db)
    member = FakeMember(bot.guild)
    row = await pending_row(bot, db, form, member)
    interaction = FakeInteraction(bot, lead)

    await Applications.applications_show.callback(Applications(bot), interaction, row["id"])

    assert interaction.embed.title.endswith("Twitch Team")
    assert any(field.name == "Twitch handle" for field in interaction.embed.fields)


async def test_show_refuses_a_number_from_another_server_without_leaking_it(bot, db, lead):
    interaction = FakeInteraction(bot, lead)

    await Applications.applications_show.callback(Applications(bot), interaction, 999)

    assert "no application with that number" in interaction.sent


async def test_the_autocomplete_offers_open_forms_to_members_and_all_of_them_to_staff(
    bot, db, lead
):
    await a_form(db)
    closed = await a_form(db, name="mod-team")
    await forms.update_form(db, GUILD, closed["name"], open=False)
    cog = Applications(bot)
    interaction = FakeInteraction(bot, lead)

    member_side = await cog.form_choices(interaction, "")
    staff_side = await cog.any_form_choices(interaction, "team")

    assert [one.value for one in member_side] == ["twitch-team"]
    assert sorted(one.value for one in staff_side) == ["mod-team", "twitch-team"]


class _Choice:
    def __init__(self, value):
        self.value = value
        self.name = value
