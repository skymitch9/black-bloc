from __future__ import annotations

import asyncio
import logging
import re
import time
from datetime import timedelta
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands

from ...actionlog import log_action, send_logs
from ...automod import (
    ACTIONS,
    ARM,
    ARM_CONFIRM,
    ARM_CONFIRM_KEY,
    BACK,
    CHANNEL,
    DEFAULT_RULES,
    DISABLE,
    ENABLE,
    EXEMPT_BACK_MOVE,
    EXEMPTIONS,
    KEEP,
    LOG_ONLY,
    LOGS,
    NUMBERS,
    PANEL_MINUTES_KEY,
    PANEL_NUMBERS,
    PANEL_TIMEOUT_FOOTER,
    PANEL_TITLE,
    REFRESH,
    ROLE,
    RULE_HELP,
    RULE_ORDER,
    SETTINGS,
    SITE,
    THRESHOLD_MAX,
    TIMEOUT_MAX_SECONDS,
    WINDOW_MAX_SECONDS,
    AutomodMove,
    RuleError,
    Verdict,
    WindowState,
    arm_needs_confirm,
    card_buttons,
    channel_exempt,
    confirm_buttons,
    describe_rule,
    evaluate,
    exempt_options,
    exempt_reason,
    facts_from,
    mode_options,
    needs_confirm,
    normalise_rule,
    panel_minutes,
    root_buttons,
    rule_config,
    rule_field_labels,
    settings_buttons,
    typed,
)
from ...command_errors import AnswersErrors, SafeDynamicItem
from ...command_visibility import STAFF_ONLY
from ...logkinds import VIA_DISCORD, kind_via
from ...modcases import (
    ALREADY_APPLIED_BY_SOMEBODY,
    add_case,
    applied_by,
    case_embed,
    claim_case,
    clamp_timeout,
    dm_member,
    dm_text,
    edit_case_card,
    from_list_json,
    get_case,
    refusal_in_test_mode,
    row_value,
    send_modlog,
    set_case_log_message,
    set_case_outcome,
)
from ...panels import (
    DESCRIPTION_LIMIT,
    SELECT_OPTION_LIMIT,
    Outcome,
    Panel,
    answer,
    capped_placeholder,
    clamped,
    confirm,
    db_up,
    opened,
    retire,
    site_page_url,
    still_staff,
)
from ...settings_store import (
    DB_UNAVAILABLE,
    GUILD_ONLY,
    SettingError,
    coerce_value,
    require_staff,
    staff_roles_sentence,
)

log = logging.getLogger(__name__)

MESSAGE_TYPES = (discord.MessageType.default, discord.MessageType.reply)
APPLY_TEMPLATE = r"automod:apply:(?P<case_id>[0-9]+)"
STAFF_CACHE_SECONDS = 60

NO_STAFF_ROLES = (
    "Black Bloc cannot work out who counts as staff, so automod was left as it was. Nobody but "
    "server admins would be exempt from it, which means a moderator posting five pings would be "
    "timed out. Point `staff_channel_id` at a channel only staff can see with `/settings` ▸ "
    "staff_channel_id`, then check the panel lists the roles you expect and arm it again."
)
NO_STAFF_WARNING = (
    "⚠️ **No staff roles resolve.** Only people with Manage Server are exempt, so a moderator "
    "who trips a rule would be punished. Fix `staff_channel_id` before leaving automod on."
)
NO_SUCH_VERDICT = (
    "Black Bloc has no record of that automod verdict any more, so nothing was applied. It may "
    "have been cleared from the database; punish by hand if it is still a problem."
)
ALREADY_APPLIED = (
    "That verdict has already been applied, so nothing changed. Open case #{case_id} to see what "
    "happened."
)
MEMBER_GONE = "That member has left the server, so there is nothing to apply."
TIMEOUT_REFUSED = (
    "Discord refused the timeout, so nothing was done to them. Black Bloc needs the Moderate "
    "Members permission and its own role has to sit above theirs in Server Settings → Roles. Ask "
    "an admin to fix that, then time them out by hand."
)
UNKNOWN_RULE_CHOICE = (
    "**{given}** is not one of Black Bloc's automod rules, so nothing was changed. `/automod` "
    "lists them."
)
STAFF_IS_THE_TEST_CHANNEL = (
    "`staff_channel_id` is still the test channel, so everybody who can see it would count as "
    "staff and automod would punish nobody. Set a real staff channel first with `/settings` ▸ "
    "staff_channel_id`, then check the panel lists the roles you expect and arm it again."
)

MODE_SET = "Automod is now **{mode}**."
ALREADY = "<{mark}{ident}> was already {state}, so nothing changed."
CHANGED = "<{mark}{ident}> is {state}"
EXEMPT_NOW = "exempt from automod now."
WATCHED_AGAIN = "watched by automod again."
SETTINGS_NOTHING = "Nothing was given, so nothing changed."
SETTINGS_DONE = "The panel stays live {minutes} minute(s), and arming automod {what}."
ONE_MESSAGE_AT_A_TIME = (
    "**how it counts** — one message at a time; nothing carries over from the message before."
)
OVER_A_WINDOW = "**how it counts** — everything one member does in {seconds} seconds, added up."
ACTION_LABELS = {
    "delete": "delete what they posted",
    "warn": "warn them",
    "timeout": "time them out",
}
WHAT_IT_DOES = "What it does…"
NUMBER_LABEL = "A whole number"
SELECT_CAP = 25
PANEL_KEYS = (PANEL_MINUTES_KEY, ARM_CONFIRM_KEY)
EVERY_RULE_OFF = (
    "⚠️ **Every rule is off**, so automod reads what people post and can never act on it. Open "
    "**A rule…** below and turn one on."
)
EXEMPT_TITLE = "What automod never reads"
EXEMPT_INTRO = (
    "Staff are always exempt. These are the roles and channels automod skips on top of that."
)
HONEYPOT_LINE = (
    "**never read either** — {channels}, because they are the honeypot's own traps. They are not "
    "on the list below: the honeypot owns them."
)
NOTHING_EXEMPT = "Nothing extra is exempt yet."
PICK_A_RULE = "A rule…"
MODE_PLACEHOLDER = "What automod does…"
ADD_ROLE = "Stop watching a role…"
ADD_CHANNEL = "Stop watching a channel…"
REMOVE_PLACEHOLDER = "Watch it again…"
SETTINGS_TITLE = "How the automod panel behaves"
SITE_ONLY_LINES = (
    "**warn threshold** and **what a punished member is told** belong to moderation as a whole, "
    "not to automod, so they are changed on the Moderation page of the dashboard or with "
    "`/settings` ▸ **A setting group…** — not here, where a change would quietly alter `/warn` too."
)
ARM_QUESTION = (
    "Turning automod **on** starts deleting messages, warning people and timing them out for "
    "real, from the next message. Nothing you have read in shadow is applied retrospectively."
)
NUMBERS_TITLE = "Change the numbers"
WORDS_TITLE = "Words that are not allowed"
WORDS_LABEL = "One per line, or separated by commas"
WORDS_TOO_LONG = (
    "This word list is longer than a Discord box holds, so it can only be edited on the "
    "dashboard's Automod page. Nothing was changed."
)
PANEL_NUMBERS_TITLE = "Numbers"
PANEL_MINUTES_LABEL = "Minutes this panel stays live"
NOT_A_NUMBER = (
    "**{given}** is not a whole number, so nothing was changed. {label} takes a number of "
    "minutes — 1 or more."
)
ASKS_TWICE = "asks a second time first"
ONE_PRESS = "takes one press"

EXEMPT_KEYS: dict[str, tuple[str, str]] = {
    ROLE: ("automod_exempt_role_ids", "@&"),
    CHANNEL: ("automod_exempt_channel_ids", "#"),
}
STYLES = {
    "primary": discord.ButtonStyle.primary,
    "secondary": discord.ButtonStyle.secondary,
    "success": discord.ButtonStyle.success,
    "danger": discord.ButtonStyle.danger,
}
FIELD_LIMITS = {
    "window_s": len(str(WINDOW_MAX_SECONDS)),
    "threshold": len(str(THRESHOLD_MAX)),
    "timeout_s": len(str(TIMEOUT_MAX_SECONDS)),
}


def apply_custom_id(case_id: int) -> str:
    return f"automod:apply:{case_id}"


def _lock(bot: Any, attribute: str, key: int) -> asyncio.Lock:
    locks = getattr(bot, attribute, None)
    if locks is None:
        locks = {}
        setattr(bot, attribute, locks)
    lock = locks.get(int(key))
    if lock is None:
        lock = locks[int(key)] = asyncio.Lock()
    return lock


def user_lock(bot: Any, user_id: int) -> asyncio.Lock:
    """One lock per member, on the BOT — a button click never arrives with a cog."""
    return _lock(bot, "_automod_locks", user_id)


def case_lock(bot: Any, case_id: int) -> asyncio.Lock:
    """One lock per case: two staffers clicking Apply now race over the row, not over each other."""
    return _lock(bot, "_automod_case_locks", case_id)


def verdict_details(verdict: Verdict, case_id: Any) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "rule": verdict.rule,
        "why": verdict.sentence,
        "actions": list(verdict.actions),
    }


async def do_delete(bot: Any, message: Any) -> str | None:
    """None when the message is gone; 'test_mode' or the failure otherwise."""
    if getattr(bot, "guard", None) is not None:
        log.warning("automod: TEST MODE — refused to delete %s", getattr(message, "id", "?"))
        return "test_mode"
    try:
        await message.delete()
    except discord.HTTPException as exc:
        log.warning("automod: could not delete %s: %s", getattr(message, "id", "?"), exc)
        return f"{type(exc).__name__}: {exc}"
    return None


def contributing_messages(channel: Any, message: Any, message_ids: tuple[int, ...]) -> list[Any]:
    """Every message that put a token in the window, as something that can be deleted."""
    partial = getattr(channel, "get_partial_message", None)
    found: list[Any] = []
    for message_id in message_ids or ():
        if message is not None and message_id == getattr(message, "id", None):
            found.append(message)
        elif partial is not None:
            found.append(partial(int(message_id)))
    if not found and message is not None:
        found.append(message)
    return found


async def do_timeout(bot: Any, member: Any, seconds: int, reason: str) -> str | None:
    """None when the member was timed out; 'test_mode' or the failure otherwise."""
    if getattr(bot, "guard", None) is not None:
        log.warning("automod: TEST MODE — refused to time out %s", getattr(member, "id", "?"))
        return "test_mode"
    timeout = getattr(member, "timeout", None)
    if timeout is None:
        return "not_a_member"
    try:
        await timeout(timedelta(seconds=clamp_timeout(seconds)), reason=reason)
    except discord.HTTPException as exc:
        log.warning("automod: could not time out %s: %s", getattr(member, "id", "?"), exc)
        return f"{type(exc).__name__}: {exc}"
    return None


async def punish(
    bot: Any,
    guild: Any,
    member: Any,
    *,
    actions: tuple[str, ...],
    timeout_s: int,
    reason: str,
    case_id: Any,
    messages: list[Any] | None = None,
    actor: Any = None,
    via: str = VIA_DISCORD,
) -> tuple[list[str], list[str]]:
    """Carry out one verdict's actions; returns what was done and what was refused."""
    done: list[str] = []
    refused: list[str] = []
    details = {"case_id": case_id, "why": reason, "via": via}
    if "delete" in actions and messages:
        for one in messages:
            failure = await do_delete(bot, one)
            where = details | {"message_id": getattr(one, "id", None)}
            if failure is None:
                if "delete" not in done:
                    done.append("delete")
                await log_action(
                    bot, guild, kind_via("automod.deleted", via), actor=actor, target=member,
                    details=where
                )
            elif failure == "test_mode":
                if "test_mode" not in refused:
                    refused.append("test_mode")
                await log_action(
                    bot,
                    guild,
                    kind_via("automod.would_delete", via),
                    actor=actor,
                    target=member,
                    details=where | {"reason": "test_mode"},
                )
            else:
                if "delete" not in refused:
                    refused.append("delete")
                await log_action(
                    bot,
                    guild,
                    kind_via("automod.delete_failed", via),
                    actor=actor,
                    target=member,
                    details=where | {"reason": failure},
                )
    if "warn" in actions:
        done.append("warn")
        await log_action(
            bot,
            guild,
            kind_via("automod.warned", via),
            actor=actor,
            target=member,
            reason=reason,
            details=details,
        )
    if "timeout" in actions:
        failure = await do_timeout(bot, member, timeout_s, f"Automod: {reason}")
        if failure is None:
            done.append("timeout")
            await log_action(
                bot,
                guild,
                kind_via("automod.timed_out", via),
                actor=actor,
                target=member,
                reason=reason,
                details=details | {"duration_s": clamp_timeout(timeout_s)},
            )
        elif failure == "test_mode":
            refused.append("test_mode")
            await log_action(
                bot,
                guild,
                kind_via("automod.would_timeout", via),
                actor=actor,
                target=member,
                reason=reason,
                details=details | {"reason": "test_mode"},
            )
        else:
            refused.append("timeout")
            await log_action(
                bot,
                guild,
                kind_via("automod.timeout_failed", via),
                actor=actor,
                target=member,
                reason=reason,
                details=details | {"reason": failure},
            )
    if "warn" in actions:
        timed_out = "timeout" in done
        await dm_member(
            member,
            dm_text(
                bot.store.get(guild.id, "mod_dm_on_action"),
                guild.name,
                "automod_timeout" if timed_out else "automod",
                reason,
                duration_s=clamp_timeout(timeout_s) if timed_out else None,
            ),
        )
    return done, refused


async def save_rule(
    bot: Any,
    guild: Any,
    name: str,
    changes: dict[str, Any],
    actor: Any,
    *,
    via: str = VIA_DISCORD,
) -> dict[str, Any]:
    """One rule after the changes; RuleError carries the sentence when they are refused."""
    if name not in RULE_ORDER:
        raise RuleError(UNKNOWN_RULE_CHOICE.format(given=name))
    book = dict(bot.store.get(guild.id, "automod_rules"))
    book[name] = normalise_rule(name, dict(rule_config(book, name)) | dict(changes))
    await bot.store.set(guild.id, "automod_rules", book, by=getattr(actor, "id", actor))
    await log_action(
        bot,
        guild,
        kind_via("automod.rule", via),
        actor=actor,
        details={"rule": name, "via": via}
        | {key: book[name].get(key) for key in changes},
    )
    return book[name]


def message_to_delete(bot: Any, case: Any, actions: tuple[str, ...]) -> list[Any]:
    message_id = row_value(case, "message_id")
    channel_id = row_value(case, "channel_id")
    if "delete" not in actions or not message_id or not channel_id:
        return []
    channel = bot.get_channel(channel_id)
    return contributing_messages(channel, None, (int(message_id),))


async def rewrite_card(
    bot: Any, guild: Any, case: Any, done: list[str], refused: list[str], moderator: Any
) -> None:
    embed = case_embed(
        case_id=case["id"],
        kind="automod",
        user_id=case["user_id"],
        reason=case["reason"],
        duration_s=case["duration_s"],
        applied=True,
        mode=case["mode"],
        done=done,
        failed=refused,
    )
    applied_by(embed, getattr(moderator, "id", moderator))
    await edit_case_card(bot, guild, case, embed)


async def apply_case(
    bot: Any, guild: Any, case_id: int, actor: Any, *, via: str = VIA_DISCORD
) -> tuple[str, str]:
    """Apply one shadow verdict for real: (what happened, what to say)."""
    async with case_lock(bot, case_id):
        case = await get_case(bot.db, case_id)
        if case is None:
            return ("no_such_case", NO_SUCH_VERDICT)
        if case["applied"]:
            return ("already", ALREADY_APPLIED.format(case_id=case_id))
        member = guild.get_member(case["user_id"])
        if member is None:
            return ("member_gone", MEMBER_GONE)
        actions = tuple(from_list_json(row_value(case, "actions"))) or ("warn",)
        reason = str(case["reason"] or "automod")
        if getattr(bot, "guard", None) is not None:
            for action in actions:
                await log_action(
                    bot,
                    guild,
                    kind_via(f"automod.would_{action}", via),
                    actor=actor,
                    target=case["user_id"],
                    reason=reason,
                    details={"case_id": case_id, "reason": "test_mode", "via": via},
                )
            return ("test_mode", refusal_in_test_mode("time out"))
        if not await claim_case(bot.db, case_id):
            return ("raced", ALREADY_APPLIED_BY_SOMEBODY.format(case_id=case_id))
        done, refused = await punish(
            bot,
            guild,
            member,
            actions=actions,
            timeout_s=int(case["duration_s"] or 0),
            reason=reason,
            case_id=case_id,
            messages=message_to_delete(bot, case, actions),
            actor=actor,
            via=via,
        )
        await set_case_outcome(bot.db, case_id, done, refused)
        if not done:
            return ("refused", TIMEOUT_REFUSED)
        await rewrite_card(bot, guild, case, done, refused, actor)
        return ("applied", f"Applied case **#{case_id}** — {', '.join(done)}.")


class ApplyNowButton(
    SafeDynamicItem, discord.ui.DynamicItem[discord.ui.Button], template=APPLY_TEMPLATE
):
    def __init__(self, case_id: int) -> None:
        self.case_id = case_id
        super().__init__(
            discord.ui.Button(
                label="Apply now",
                style=discord.ButtonStyle.danger,
                custom_id=apply_custom_id(case_id),
            )
        )

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: Any, match: re.Match):
        return cls(int(match["case_id"]))

    async def on_click(self, interaction: discord.Interaction) -> None:
        bot = interaction.client
        if not await require_staff(interaction):
            return
        if not bot.db.is_connected:
            await interaction.response.send_message(DB_UNAVAILABLE, ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        _, said = await apply_case(bot, interaction.guild, self.case_id, interaction.user)
        await interaction.followup.send(
            said, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
        )


class AutoMod(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.state = WindowState()
        self._staff: dict[int, tuple[float, set[int]]] = {}

    async def cog_load(self) -> None:
        self.bot.add_dynamic_items(ApplyNowButton)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.guild is None or message.webhook_id is not None:
            return
        if getattr(message, "type", None) not in MESSAGE_TYPES:
            return
        me = getattr(self.bot, "user", None)
        if me is not None and message.author.id == me.id:
            return
        if not self.bot.db.is_connected:
            return
        store = self.bot.store
        guild = message.guild
        mode = store.get(guild.id, "automod_mode")
        if mode == "off":
            return
        if not self._may_read(message.channel):
            return
        if channel_exempt(
            message.channel,
            set(store.get(guild.id, "automod_exempt_channel_ids") or []),
            set(store.get(guild.id, "honeypot_channel_ids") or []),
        ):
            return
        if exempt_reason(
            message.author,
            self._staff_role_ids(guild),
            set(store.get(guild.id, "automod_exempt_role_ids") or []),
        ):
            return
        verdicts = evaluate(facts_from(message), self.state, store.get(guild.id, "automod_rules"))
        if not verdicts:
            return
        async with user_lock(self.bot, message.author.id):
            for verdict in verdicts:
                await self._answer_for(message, mode, verdict)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> None:
        if str(getattr(before, "content", "") or "") == str(getattr(after, "content", "") or ""):
            return
        await self.on_message(after)

    def _staff_role_ids(self, guild: Any) -> set[int]:
        """Resolving staff walks every role's permissions; a message event cannot afford that."""
        cached = self._staff.get(guild.id)
        now = time.monotonic()
        if cached is not None and now - cached[0] < STAFF_CACHE_SECONDS:
            return cached[1]
        ids = self.bot.store.staff_role_ids(guild)
        self._staff[guild.id] = (now, ids)
        return ids

    def _may_read(self, channel: Any) -> bool:
        """While the guard is on the engine only ever sees the test channel."""
        guard = getattr(self.bot, "guard", None)
        if guard is None:
            return True
        return guard.allows_channel(getattr(channel, "id", 0))

    async def _answer_for(self, message: discord.Message, mode: str, verdict: Verdict) -> None:
        guild = message.guild
        author = message.author
        if not verdict.actions:
            await log_action(
                self.bot,
                guild,
                "automod.observed",
                target=author,
                reason=verdict.sentence,
                details=verdict_details(verdict, None),
            )
            return
        timeout_s = verdict.timeout_s if "timeout" in verdict.actions else None
        case_id = await add_case(
            self.bot.db,
            guild.id,
            author.id,
            "automod",
            reason=verdict.sentence,
            duration_s=timeout_s,
            mode=mode,
            applied=False,
            actions=list(verdict.actions),
            message_id=message.id,
            channel_id=getattr(message.channel, "id", None),
        )
        details = verdict_details(verdict, case_id)
        done: list[str] = []
        refused: list[str] = []
        if mode == "on" and getattr(self.bot, "guard", None) is None:
            done, refused = await punish(
                self.bot,
                guild,
                author,
                actions=verdict.actions,
                timeout_s=verdict.timeout_s,
                reason=verdict.sentence,
                case_id=case_id,
                messages=contributing_messages(message.channel, message, verdict.message_ids),
            )
            await set_case_outcome(self.bot.db, case_id, done, refused)
        else:
            for action in verdict.actions:
                await log_action(
                    self.bot,
                    guild,
                    f"automod.would_{action}",
                    target=author,
                    reason=verdict.sentence,
                    details=details,
                )
        await self._post_case(guild, author, verdict, case_id, mode, done=done, refused=refused)

    async def _post_case(
        self,
        guild: Any,
        author: Any,
        verdict: Verdict,
        case_id: Any,
        mode: str,
        *,
        done: list[str],
        refused: list[str],
    ) -> None:
        embed = case_embed(
            case_id=case_id,
            kind="automod",
            user_id=author.id,
            reason=verdict.sentence,
            duration_s=verdict.timeout_s if "timeout" in verdict.actions else None,
            applied=bool(done),
            mode="test mode" if getattr(self.bot, "guard", None) is not None else mode,
            detail=f"{verdict.rule} — {', '.join(verdict.actions) or 'log only'}",
            done=done,
            failed=[item for item in refused if item != "test_mode"],
        )
        view = None
        if not done and case_id is not None:
            view = discord.ui.View(timeout=None)
            view.add_item(ApplyNowButton(case_id))
        message_id = await send_modlog(self.bot, guild, embed, view)
        await set_case_log_message(self.bot.db, case_id, message_id)

    @app_commands.command(
        name="automod", description="The rules that watch what people post"
    )
    @app_commands.default_permissions(STAFF_ONLY)
    async def automod(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await answer(interaction, GUILD_ONLY)
            return
        if not await require_staff(interaction):
            return
        if not await db_up(interaction):
            return
        embed, view = await build_root(self.bot, interaction.guild)
        await interaction.response.send_message(
            embed=embed,
            view=view,
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        view.message = await interaction.original_response()


# --- the moves, one function each, one write and one log row -------------------------------------


def arming_refusal(bot: Any, guild: Any) -> str | None:
    """The mode picker and `set_mode` read one answer, so offer and verdict cannot disagree."""
    store = bot.store
    if store.get(guild.id, "staff_channel_id") == bot.settings.test_channel_id:
        return STAFF_IS_THE_TEST_CHANNEL
    if not store.staff_roles(guild):
        return NO_STAFF_ROLES
    return None


async def set_mode(
    bot: Any, guild: Any, value: str, actor: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    """One verdict for both doors: an `Outcome`, so the website can tell a refusal from a save."""
    if value == "on":
        blocker = arming_refusal(bot, guild)
        if blocker is not None:
            return Outcome(False, blocker, "not_armable", 409)
    try:
        stored = coerce_value("automod_mode", value)
    except SettingError as exc:
        return Outcome(False, str(exc), "bad_value", 400)
    await bot.store.set(guild.id, "automod_mode", stored, by=getattr(actor, "id", actor))
    await log_action(
        bot,
        guild,
        kind_via("automod.mode", via),
        actor=actor,
        details={"mode": stored, "via": via},
    )
    return Outcome(True, MODE_SET.format(mode=stored), "set", 200, stored)


async def set_exempt(
    bot: Any,
    guild: Any,
    kind: str,
    entity_id: Any,
    actor: Any,
    *,
    add: bool,
    via: str = VIA_DISCORD,
) -> str:
    """One role or one channel per call; the kind picks the key and the mark it is written with."""
    key, mark = EXEMPT_KEYS[kind]
    ident = int(entity_id)
    ids = list(bot.store.get(guild.id, key) or [])
    if add and ident not in ids:
        ids.append(ident)
    elif not add and ident in ids:
        ids.remove(ident)
    else:
        return ALREADY.format(mark=mark, ident=ident, state="exempt" if add else "not exempt")
    await bot.store.set(guild.id, key, ids, by=getattr(actor, "id", actor))
    await log_action(
        bot,
        guild,
        kind_via("automod.exempt_add" if add else "automod.exempt_remove", via),
        actor=actor,
        details={key: ident, "via": via},
    )
    return CHANGED.format(mark=mark, ident=ident, state=EXEMPT_NOW if add else WATCHED_AGAIN)


async def save_settings(
    bot: Any, guild: Any, changes: Any, actor: Any, *, via: str = VIA_DISCORD
) -> str:
    """The two panel keys, written together so one press leaves one log row."""
    wanted = {key: value for key, value in (changes or {}).items() if key in PANEL_KEYS}
    if not wanted:
        return SETTINGS_NOTHING
    for key, value in wanted.items():
        try:
            coerce_value(key, value)
        except SettingError as exc:
            return str(exc)
    for key, value in wanted.items():
        await bot.store.set(guild.id, key, value, by=getattr(actor, "id", actor))
    await log_action(
        bot,
        guild,
        kind_via("automod.settings", via),
        actor=actor,
        details={"changed": wanted, "via": via},
    )
    return SETTINGS_DONE.format(
        minutes=panel_minutes(bot.store, guild.id),
        what=ASKS_TWICE if arm_needs_confirm(bot.store, guild.id) else ONE_PRESS,
    )


async def case_totals(db: Any, guild_id: int) -> dict[int, int]:
    cur = await db.conn.execute(
        "SELECT applied, COUNT(*) AS n FROM mod_cases WHERE guild_id = ? AND kind = 'automod' "
        "GROUP BY applied",
        (guild_id,),
    )
    return {int(row["applied"]): int(row["n"]) for row in await cur.fetchall()}


def status_lines(bot: Any, guild: Any, totals: dict[int, int]) -> list[str]:
    """The panel embed and what `/automod status` printed are ONE list, never two shapes."""
    store = bot.store
    mode = store.get(guild.id, "automod_mode")
    staff = store.staff_roles(guild)
    book = store.get(guild.id, "automod_rules")
    roles = store.get(guild.id, "automod_exempt_role_ids") or []
    channels = store.get(guild.id, "automod_exempt_channel_ids") or []
    modlog = store.get(guild.id, "modlog_channel_id")
    lines = [
        f"**mode** — {mode}",
        f"**staff (always exempt)** — {staff_roles_sentence(staff)}",
        f"**tells the member** — {store.get(guild.id, 'mod_dm_on_action')}",
        f"**warn threshold** — {store.get(guild.id, 'automod_warn_threshold')} (log only)",
        "**modlog** — " + (f"<#{modlog}>" if modlog else "not set"),
        "**exempt roles** — "
        + (", ".join(f"<@&{one}>" for one in roles) if roles else "staff only"),
        "**exempt channels** — "
        + (", ".join(f"<#{one}>" for one in channels) if channels else "none"),
        f"**seen** — {totals.get(1, 0)} acted on · {totals.get(0, 0)} logged only",
    ]
    blocker = arming_refusal(bot, guild)
    if blocker is not None:
        lines.append(blocker)
    if not any(rule_config(book, name)["enabled"] for name in RULE_ORDER):
        lines.append(EVERY_RULE_OFF)
    lines.append("")
    lines.extend(describe_rule(name, rule_config(book, name)) for name in RULE_ORDER)
    if not staff and mode == "on":
        lines.append(NO_STAFF_WARNING)
    return lines


def card_lines(name: str, cfg: dict[str, Any]) -> list[str]:
    lines = [describe_rule(name, cfg), "", f"**what it counts** — {RULE_HELP[name]}"]
    if cfg["window_s"]:
        lines.append(OVER_A_WINDOW.format(seconds=cfg["window_s"]))
    else:
        lines.append(ONE_MESSAGE_AT_A_TIME)
    if "words" in cfg:
        lines.append(f"**words** — {', '.join(cfg['words']) or 'none yet'}")
    return lines


def exempt_lines(bot: Any, guild: Any) -> list[str]:
    store = bot.store
    roles = store.get(guild.id, "automod_exempt_role_ids") or []
    channels = store.get(guild.id, "automod_exempt_channel_ids") or []
    honeypots = store.get(guild.id, "honeypot_channel_ids") or []
    lines = [
        EXEMPT_INTRO,
        "",
        "**exempt roles** — "
        + (", ".join(f"<@&{one}>" for one in roles) if roles else "staff only"),
        "**exempt channels** — "
        + (", ".join(f"<#{one}>" for one in channels) if channels else "none"),
    ]
    if honeypots:
        lines.append(HONEYPOT_LINE.format(channels=", ".join(f"<#{one}>" for one in honeypots)))
    if not roles and not channels:
        lines.append(NOTHING_EXEMPT)
    return lines


def settings_lines(bot: Any, guild: Any) -> list[str]:
    store = bot.store
    return [
        f"**this panel stays live** — {panel_minutes(store, guild.id)} minute(s)",
        "**arming automod** — " + (ASKS_TWICE if arm_needs_confirm(store, guild.id) else ONE_PRESS),
        "",
        f"**warn threshold** — {store.get(guild.id, 'automod_warn_threshold')} (log only)",
        f"**tells the member** — {store.get(guild.id, 'mod_dm_on_action')}",
        SITE_ONLY_LINES,
    ]


def exempt_names(guild: Any, roles: Any, channels: Any) -> dict[tuple[str, int], str]:
    found: dict[tuple[str, int], str] = {}
    for kind, ids, getter in (
        (ROLE, roles, getattr(guild, "get_role", None)),
        (CHANNEL, channels, getattr(guild, "get_channel", None)),
    ):
        for one in ids or ():
            entity = getter(int(one)) if getter is not None else None
            if entity is not None:
                found[(kind, int(one))] = str(getattr(entity, "name", one))
    return found


# --- the panel -----------------------------------------------------------------------------------


class AutomodPanel(Panel):
    def __init__(self, minutes: int) -> None:
        super().__init__(minutes, footer=PANEL_TIMEOUT_FOOTER)
        self.rule_name: str | None = None


def minutes_for(bot: Any, guild_id: int) -> int:
    return panel_minutes(bot.store, guild_id)


def add_root_buttons(view: Any, bot: Any) -> None:
    url = site_page_url(getattr(getattr(bot, "settings", None), "origin", ""), "automod")
    for move in root_buttons(has_site=url is not None):
        view.add_item(SiteButton(move, url) if move.action == SITE else MoveButton(move))


async def build_root(bot: Any, guild: Any) -> tuple[discord.Embed, AutomodPanel]:
    totals = await case_totals(bot.db, guild.id)
    embed = discord.Embed(title=PANEL_TITLE, description=clamped(status_lines(bot, guild, totals)))
    view = AutomodPanel(minutes_for(bot, guild.id))
    view.add_item(RulePick())
    view.add_item(
        ModePick(bot.store.get(guild.id, "automod_mode"), arming_refusal(bot, guild) is None)
    )
    add_root_buttons(view, bot)
    return (embed, view)


def build_card(bot: Any, guild: Any, name: str) -> tuple[discord.Embed, AutomodPanel]:
    cfg = rule_config(bot.store.get(guild.id, "automod_rules"), name)
    embed = discord.Embed(title=PANEL_TITLE, description=clamped(card_lines(name, cfg)))
    view = AutomodPanel(minutes_for(bot, guild.id))
    view.rule_name = name
    for move in card_buttons(cfg, has_words="words" in DEFAULT_RULES[name]):
        view.add_item(MoveButton(move))
    view.add_item(ActionsPick(cfg["actions"]))
    return (embed, view)


def build_exemptions(bot: Any, guild: Any) -> tuple[discord.Embed, AutomodPanel]:
    store = bot.store
    roles = store.get(guild.id, "automod_exempt_role_ids") or []
    channels = store.get(guild.id, "automod_exempt_channel_ids") or []
    embed = discord.Embed(title=EXEMPT_TITLE, description=clamped(exempt_lines(bot, guild)))
    view = AutomodPanel(minutes_for(bot, guild.id))
    view.add_item(ExemptRolePick())
    view.add_item(ExemptChannelPick())
    options = exempt_options(roles, channels, exempt_names(guild, roles, channels))
    if options:
        view.add_item(ExemptRemovePick(options))
    view.add_item(MoveButton(EXEMPT_BACK_MOVE))
    return (embed, view)


def build_settings(bot: Any, guild: Any) -> tuple[discord.Embed, AutomodPanel]:
    embed = discord.Embed(title=SETTINGS_TITLE, description=clamped(settings_lines(bot, guild)))
    view = AutomodPanel(minutes_for(bot, guild.id))
    for move in settings_buttons(asks_twice=arm_needs_confirm(bot.store, guild.id)):
        view.add_item(MoveButton(move))
    return (embed, view)


# --- rendering -----------------------------------------------------------------------------------


async def show(interaction: discord.Interaction, built: Any, previous: Any) -> None:
    embed, view = built
    retire(previous)
    view.message = await interaction.edit_original_response(
        embed=embed, view=view, allowed_mentions=discord.AllowedMentions.none()
    )


async def render_root(interaction: discord.Interaction, previous: Any = None) -> None:
    await show(interaction, await build_root(interaction.client, interaction.guild), previous)


async def render_card(interaction: discord.Interaction, name: str, previous: Any = None) -> None:
    await show(interaction, build_card(interaction.client, interaction.guild, name), previous)


async def render_exemptions(interaction: discord.Interaction, previous: Any = None) -> None:
    await show(interaction, build_exemptions(interaction.client, interaction.guild), previous)


async def render_settings(interaction: discord.Interaction, previous: Any = None) -> None:
    await show(interaction, build_settings(interaction.client, interaction.guild), previous)


async def back_to_root(interaction: discord.Interaction, previous: Any = None) -> None:
    if not await opened(interaction):
        return
    await render_root(interaction, previous)


async def open_card(interaction: discord.Interaction, name: str, previous: Any = None) -> None:
    if not await opened(interaction):
        return
    await render_card(interaction, name, previous)


async def open_exemptions(interaction: discord.Interaction, previous: Any = None) -> None:
    if not await opened(interaction):
        return
    await render_exemptions(interaction, previous)


async def open_settings(interaction: discord.Interaction, previous: Any = None) -> None:
    if not await opened(interaction):
        return
    await render_settings(interaction, previous)


async def open_confirm(interaction: discord.Interaction, previous: Any = None) -> None:
    """Arming replaces the root's controls rather than adding a row to them."""
    if not await opened(interaction):
        return
    bot, guild = interaction.client, interaction.guild
    totals = await case_totals(bot.db, guild.id)
    await confirm(
        interaction,
        AutomodPanel(minutes_for(bot, guild.id)),
        discord.Embed(title=PANEL_TITLE, description=clamped(status_lines(bot, guild, totals))),
        [
            MoveButton(move)
            for move in confirm_buttons(bot.store.get(guild.id, "automod_mode"))
        ],
        previous,
        question=ARM_QUESTION,
    )


async def run_rule(
    interaction: discord.Interaction, name: Any, changes: dict[str, Any], previous: Any = None
) -> None:
    """A refused value is answered and the card is NOT re-rendered, so it cannot read as a save."""
    if not await opened(interaction):
        return
    store = interaction.client.store
    try:
        await save_rule(interaction.client, interaction.guild, str(name), changes, interaction.user)
    except (RuleError, ValueError) as exc:
        await answer(interaction, str(exc))
        return
    await render_card(interaction, str(name), previous)
    cfg = rule_config(store.get(interaction.guild.id, "automod_rules"), str(name))
    await answer(interaction, describe_rule(str(name), cfg))


async def run_mode(
    interaction: discord.Interaction,
    value: str,
    previous: Any = None,
    *,
    confirmed: bool = False,
) -> None:
    bot = interaction.client
    guild = interaction.guild
    if not confirmed and needs_confirm(
        bot.store.get(guild.id, "automod_mode"), value, arm_needs_confirm(bot.store, guild.id)
    ):
        await open_confirm(interaction, previous)
        return
    if not await opened(interaction):
        return
    outcome = await set_mode(bot, guild, value, interaction.user)
    await render_root(interaction, previous)
    await answer(interaction, outcome.message)


async def run_exempt(
    interaction: discord.Interaction,
    kind: str,
    entity_id: Any,
    previous: Any = None,
    *,
    add: bool,
) -> None:
    if not await opened(interaction):
        return
    said = await set_exempt(
        interaction.client, interaction.guild, kind, entity_id, interaction.user, add=add
    )
    await render_exemptions(interaction, previous)
    await answer(interaction, said)


async def run_settings(
    interaction: discord.Interaction, changes: dict[str, Any], previous: Any = None
) -> None:
    if not await opened(interaction):
        return
    said = await save_settings(interaction.client, interaction.guild, changes, interaction.user)
    await render_settings(interaction, previous)
    await answer(interaction, said)


# --- the controls --------------------------------------------------------------------------------


class MoveButton(discord.ui.Button):
    def __init__(self, move: AutomodMove) -> None:
        super().__init__(label=move.label, style=STYLES[move.style], row=move.row)
        self.move = move

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        action = self.move.action
        if action == LOGS:
            await send_logs(interaction, "automod")
            return
        if action in (REFRESH, BACK, KEEP):
            await back_to_root(interaction, view)
            return
        if action == EXEMPTIONS:
            await open_exemptions(interaction, view)
            return
        if action == SETTINGS:
            await open_settings(interaction, view)
            return
        if action == ARM:
            await run_mode(interaction, "on", view, confirmed=True)
            return
        if action in (ENABLE, DISABLE):
            await run_rule(interaction, view.rule_name, {"enabled": action == ENABLE}, view)
            return
        if action == LOG_ONLY:
            await run_rule(interaction, view.rule_name, {"actions": []}, view)
            return
        if action == ARM_CONFIRM:
            asks = arm_needs_confirm(interaction.client.store, interaction.guild.id)
            await run_settings(interaction, {ARM_CONFIRM_KEY: not asks}, view)
            return
        await self.open_modal(interaction, view)

    async def open_modal(self, interaction: discord.Interaction, view: Any) -> None:
        if not await still_staff(interaction):
            return
        if not await db_up(interaction):
            return
        bot = interaction.client
        guild = interaction.guild
        if self.move.action == PANEL_NUMBERS:
            await interaction.response.send_modal(
                PanelNumbersModal(minutes_for(bot, guild.id), view)
            )
            return
        cfg = rule_config(bot.store.get(guild.id, "automod_rules"), view.rule_name)
        if self.move.action == NUMBERS:
            await interaction.response.send_modal(NumbersModal(view.rule_name, cfg, view))
            return
        given = "\n".join(cfg.get("words") or ())
        if len(given) > DESCRIPTION_LIMIT:
            await answer(interaction, WORDS_TOO_LONG)
            return
        await interaction.response.send_modal(WordsModal(view.rule_name, given, view))


class SiteButton(discord.ui.Button):
    def __init__(self, move: AutomodMove, url: str) -> None:
        super().__init__(label=move.label, style=discord.ButtonStyle.link, url=url, row=move.row)


class RulePick(discord.ui.Select):
    def __init__(self) -> None:
        super().__init__(
            placeholder=PICK_A_RULE,
            options=[
                discord.SelectOption(
                    label=f"{name} — {RULE_HELP[name]}"[:SELECT_OPTION_LIMIT], value=name
                )
                for name in RULE_ORDER
            ],
            min_values=1,
            max_values=1,
            row=0,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await open_card(interaction, self.values[0], self.view)


class ModePick(discord.ui.Select):
    def __init__(self, current: str, may_arm: bool) -> None:
        super().__init__(
            placeholder=MODE_PLACEHOLDER,
            options=[
                discord.SelectOption(label=label, value=value, default=now)
                for value, label, now in mode_options(current, may_arm)
            ],
            min_values=1,
            max_values=1,
            row=1,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await run_mode(interaction, self.values[0], self.view)


class ActionsPick(discord.ui.Select):
    """`Log only` is the same move by a second door: an empty submit is untested on clients."""

    def __init__(self, actions: Any) -> None:
        super().__init__(
            placeholder=WHAT_IT_DOES,
            options=[
                discord.SelectOption(
                    label=ACTION_LABELS[name], value=name, default=name in (actions or ())
                )
                for name in ACTIONS
            ],
            min_values=0,
            max_values=len(ACTIONS),
            row=1,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await run_rule(interaction, self.view.rule_name, {"actions": list(self.values)}, self.view)


class ExemptRolePick(discord.ui.RoleSelect):
    def __init__(self) -> None:
        super().__init__(placeholder=ADD_ROLE, min_values=1, max_values=1, row=0)

    async def callback(self, interaction: discord.Interaction) -> None:
        await run_exempt(interaction, ROLE, self.values[0].id, self.view, add=True)


class ExemptChannelPick(discord.ui.ChannelSelect):
    def __init__(self) -> None:
        super().__init__(placeholder=ADD_CHANNEL, min_values=1, max_values=1, row=1)

    async def callback(self, interaction: discord.Interaction) -> None:
        await run_exempt(interaction, CHANNEL, self.values[0].id, self.view, add=True)


class ExemptRemovePick(discord.ui.Select):
    """One control for both kinds, so add and remove never become two spellings of one move."""

    def __init__(self, options: list[tuple[str, int, str]]) -> None:
        shown = list(options)[:SELECT_CAP]
        super().__init__(
            placeholder=capped_placeholder(len(shown), len(options), pick=REMOVE_PLACEHOLDER),
            options=[
                discord.SelectOption(label=label, value=f"{kind}:{ident}")
                for kind, ident, label in shown
            ],
            min_values=1,
            max_values=1,
            row=2,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        kind, _, ident = str(self.values[0]).partition(":")
        await run_exempt(interaction, kind, int(ident), self.view, add=False)


# --- the modals ----------------------------------------------------------------------------------


class NumbersModal(AnswersErrors, discord.ui.Modal):
    window = discord.ui.TextInput(label=NUMBER_LABEL, max_length=FIELD_LIMITS["window_s"])
    threshold = discord.ui.TextInput(label=NUMBER_LABEL, max_length=FIELD_LIMITS["threshold"])
    timeout = discord.ui.TextInput(label=NUMBER_LABEL, max_length=FIELD_LIMITS["timeout_s"])

    def __init__(self, name: str, cfg: dict[str, Any], previous: Any = None) -> None:
        super().__init__(title=NUMBERS_TITLE[:45])
        self.rule_name = name
        self.previous = previous
        labels = rule_field_labels(name)
        for item, key in self.fields():
            item.label = labels[key]
            item.default = str(cfg[key])

    def fields(self) -> tuple[tuple[Any, str], ...]:
        return (
            (self.window, "window_s"),
            (self.threshold, "threshold"),
            (self.timeout, "timeout_s"),
        )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        """A modal has no Range, so every field is parsed before anything at all is written."""
        changes: dict[str, Any] = {}
        for item, key in self.fields():
            try:
                changes[key] = typed(key, str(item))
            except RuleError as exc:
                await answer(interaction, str(exc))
                return
        await run_rule(interaction, self.rule_name, changes, self.previous)


class WordsModal(AnswersErrors, discord.ui.Modal):
    words = discord.ui.TextInput(
        label=WORDS_LABEL,
        style=discord.TextStyle.paragraph,
        max_length=DESCRIPTION_LIMIT,
        required=False,
    )

    def __init__(self, name: str, given: str, previous: Any = None) -> None:
        super().__init__(title=WORDS_TITLE[:45])
        self.rule_name = name
        self.previous = previous
        self.words.default = given or None

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await run_rule(interaction, self.rule_name, {"words": str(self.words)}, self.previous)


class PanelNumbersModal(AnswersErrors, discord.ui.Modal):
    stays = discord.ui.TextInput(label=PANEL_MINUTES_LABEL, max_length=5)

    def __init__(self, minutes: Any, previous: Any = None) -> None:
        super().__init__(title=PANEL_NUMBERS_TITLE[:45])
        self.previous = previous
        self.stays.default = str(minutes)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        given = str(self.stays).strip()
        if not given.isdigit() or int(given) < 1:
            await answer(
                interaction,
                NOT_A_NUMBER.format(given=given[:40] or "nothing", label=PANEL_MINUTES_LABEL),
            )
            return
        await run_settings(interaction, {PANEL_MINUTES_KEY: int(given)}, self.previous)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AutoMod(bot))
