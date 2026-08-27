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

from ...actionlog import log_action
from ...automod import (
    AUTOMOD_MODES,
    PARITY_MAX_DAYS,
    RULE_HELP,
    RULE_ORDER,
    RuleError,
    Verdict,
    WindowState,
    channel_exempt,
    describe_rule,
    evaluate,
    exempt_reason,
    facts_from,
    normalise_rule,
    parity_report,
    parse_carl_entry,
    rule_config,
)
from ...command_errors import SafeDynamicItem
from ...golive import parse_ts
from ...modcases import (
    ALREADY_APPLIED_BY_SOMEBODY,
    add_case,
    applied_by,
    armed_verdicts_since,
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
    within_days,
)
from ...settings_store import DB_UNAVAILABLE, require_staff, staff_roles_sentence

log = logging.getLogger(__name__)

MESSAGE_TYPES = (discord.MessageType.default, discord.MessageType.reply)
APPLY_TEMPLATE = r"automod:apply:(?P<case_id>[0-9]+)"
RULE_FIELDS = ("enabled", "window_s", "threshold", "actions", "timeout_s", "words")
PARITY_HISTORY_LIMIT = 500
STAFF_CACHE_SECONDS = 60

NO_STAFF_ROLES = (
    "Black Bloc cannot work out who counts as staff, so automod was left as it was. Nobody but "
    "server admins would be exempt from it, which means a moderator posting five pings would be "
    "timed out. Point `staff_channel_id` at a channel only staff can see with `/settings set "
    "staff_channel_id`, check `/automod status` lists the roles you expect, then arm it again."
)
NO_STAFF_WARNING = (
    "⚠️ **No staff roles resolve.** Only people with Manage Server are exempt, so a moderator "
    "who trips a rule would be punished. Fix `staff_channel_id` before leaving automod on."
)
NO_SUCH_CASE = (
    "Black Bloc has no record of that automod verdict any more, so nothing was applied. It may "
    "have been cleared from the database; punish by hand if it is still a problem."
)
ALREADY_APPLIED = (
    "That verdict has already been applied, so nothing changed. `/case {case_id}` shows what "
    "happened."
)
TIMEOUT_REFUSED = (
    "Discord refused the timeout, so nothing was done to them. Black Bloc needs the Moderate "
    "Members permission and its own role has to sit above theirs in Server Settings → Roles. Ask "
    "an admin to fix that, then time them out by hand."
)
UNKNOWN_RULE_CHOICE = (
    "**{given}** is not one of Black Bloc's automod rules, so nothing was changed. `/automod "
    "status` lists them."
)
NO_CARL_LOG = (
    "Black Bloc cannot see Carl-bot's mod log, so there is nothing to compare against. Point "
    "`carl_modlog_channel_id` at the channel Carl posts cases in with `/settings set "
    "carl_modlog_channel_id`, and make sure Black Bloc can read its history."
)
CARL_LOG_FORBIDDEN = (
    "Discord refused to let Black Bloc read <#{channel_id}>, so parity could not be measured. It "
    "needs View Channel **and** Read Message History there. Ask an admin to give it both in that "
    "channel's permissions, then run this again."
)
CARL_LOG_FAILED = (
    "Discord would not hand over <#{channel_id}>'s history just now, so parity could not be "
    "measured. Try again in a minute, and tell a Lead if it keeps happening."
)
PARITY_HEADER = (
    "**Parity over the last {days} day(s)** — Black Bloc saw **{bloc}** verdict(s), Carl-bot "
    "logged **{carl}** case(s)."
)
PARITY_VERDICT = (
    "**{agree}** agree · **{carl_only}** Carl-only · **{bloc_only}** Bloc-only. Flip "
    "`automod_mode` to `on` and turn Carl's automod off once Carl-only and Bloc-only have both "
    "been zero for a week."
)
PARITY_TEST_MODE = (
    "Black Bloc is in test mode, so automod only ever saw the test channel — expect Carl-only to "
    "be the real cases and Bloc-only to be zero."
)
PARITY_SAME_CHANNEL = (
    "`carl_modlog_channel_id` and `modlog_channel_id` are the same channel, so parity would count "
    "Black Bloc's own cards as Carl-bot's cases and report nonsense. Point "
    "`carl_modlog_channel_id` at the channel **Carl** posts in with `/settings set "
    "carl_modlog_channel_id`, then run this again."
)
PARITY_TRUNCATED = (
    "⚠️ Only the first {limit} posts in that window were read, so the window is truncated — ask "
    "for fewer days to compare all of it."
)
STAFF_IS_THE_TEST_CHANNEL = (
    "`staff_channel_id` is still the test channel, so everybody who can see it would count as "
    "staff and automod would punish nobody. Set a real staff channel first with `/settings set "
    "staff_channel_id`, check `/automod status` lists the roles you expect, then arm it again."
)


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
) -> tuple[list[str], list[str]]:
    """Carry out one verdict's actions; returns what was done and what was refused."""
    done: list[str] = []
    refused: list[str] = []
    details = {"case_id": case_id, "why": reason}
    if "delete" in actions and messages:
        for one in messages:
            failure = await do_delete(bot, one)
            where = details | {"message_id": getattr(one, "id", None)}
            if failure is None:
                if "delete" not in done:
                    done.append("delete")
                await log_action(
                    bot, guild, "automod.deleted", actor=actor, target=member, details=where
                )
            elif failure == "test_mode":
                if "test_mode" not in refused:
                    refused.append("test_mode")
                await log_action(
                    bot,
                    guild,
                    "automod.would_delete",
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
                    "automod.delete_failed",
                    actor=actor,
                    target=member,
                    details=where | {"reason": failure},
                )
    if "warn" in actions:
        done.append("warn")
        await log_action(
            bot, guild, "automod.warned", actor=actor, target=member, reason=reason, details=details
        )
    if "timeout" in actions:
        failure = await do_timeout(bot, member, timeout_s, f"Automod: {reason}")
        if failure is None:
            done.append("timeout")
            await log_action(
                bot,
                guild,
                "automod.timed_out",
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
                "automod.would_timeout",
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
                "automod.timeout_failed",
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
        guild = interaction.guild
        async with case_lock(bot, self.case_id):
            case = await get_case(bot.db, self.case_id)
            if case is None:
                await interaction.response.send_message(NO_SUCH_CASE, ephemeral=True)
                return
            if case["applied"]:
                await interaction.response.send_message(
                    ALREADY_APPLIED.format(case_id=self.case_id), ephemeral=True
                )
                return
            member = guild.get_member(case["user_id"])
            if member is None:
                await interaction.response.send_message(
                    "That member has left the server, so there is nothing to apply.",
                    ephemeral=True,
                )
                return
            actions = tuple(from_list_json(row_value(case, "actions"))) or ("warn",)
            if getattr(bot, "guard", None) is not None:
                await self._would_have(bot, guild, case, actions, interaction)
                return
            await interaction.response.defer(ephemeral=True)
            if not await claim_case(bot.db, self.case_id):
                await interaction.followup.send(
                    ALREADY_APPLIED_BY_SOMEBODY.format(case_id=self.case_id), ephemeral=True
                )
                return
            done, refused = await punish(
                bot,
                guild,
                member,
                actions=actions,
                timeout_s=int(case["duration_s"] or 0),
                reason=str(case["reason"] or "automod"),
                case_id=self.case_id,
                messages=self._message_to_delete(bot, case, actions),
                actor=interaction.user,
            )
            await set_case_outcome(bot.db, self.case_id, done, refused)
            if not done:
                await interaction.followup.send(TIMEOUT_REFUSED, ephemeral=True)
                return
            await self._rewrite_card(bot, guild, case, done, refused, interaction.user)
            await interaction.followup.send(
                f"Applied case **#{self.case_id}** — {', '.join(done)}.",
                ephemeral=True,
                allowed_mentions=discord.AllowedMentions.none(),
            )

    def _message_to_delete(self, bot: Any, case: Any, actions: tuple[str, ...]) -> list[Any]:
        message_id = row_value(case, "message_id")
        channel_id = row_value(case, "channel_id")
        if "delete" not in actions or not message_id or not channel_id:
            return []
        channel = bot.get_channel(channel_id)
        return contributing_messages(channel, None, (int(message_id),))

    async def _would_have(
        self,
        bot: Any,
        guild: Any,
        case: Any,
        actions: tuple[str, ...],
        interaction: discord.Interaction,
    ) -> None:
        for action in actions:
            await log_action(
                bot,
                guild,
                f"automod.would_{action}",
                actor=interaction.user,
                target=case["user_id"],
                reason=str(case["reason"] or "automod"),
                details={"case_id": self.case_id, "reason": "test_mode"},
            )
        await interaction.response.send_message(refusal_in_test_mode("time out"), ephemeral=True)

    async def _rewrite_card(
        self, bot: Any, guild: Any, case: Any, done: list[str], refused: list[str], moderator: Any
    ) -> None:
        embed = case_embed(
            case_id=self.case_id,
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


class AutoMod(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.state = WindowState()
        self._staff: dict[int, tuple[float, set[int]]] = {}

    automod = app_commands.Group(
        name="automod", description="The rules that watch what people post"
    )
    rule = app_commands.Group(name="rule", description="One automod rule", parent=automod)
    exempt = app_commands.Group(
        name="exempt", description="Roles and channels automod ignores", parent=automod
    )

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

    async def _database_ready(self, interaction: discord.Interaction) -> bool:
        if self.bot.db.is_connected:
            return True
        log.warning("automod: refused a command — the database is not connected")
        await interaction.response.send_message(DB_UNAVAILABLE, ephemeral=True)
        return False

    @automod.command(name="status", description="Show what automod is set to and has seen")
    async def status(self, interaction: discord.Interaction) -> None:
        if not await require_staff(interaction):
            return
        if not await self._database_ready(interaction):
            return
        guild = interaction.guild
        store = self.bot.store
        mode = store.get(guild.id, "automod_mode")
        staff = store.staff_roles(guild)
        book = store.get(guild.id, "automod_rules")
        roles = store.get(guild.id, "automod_exempt_role_ids") or []
        channels = store.get(guild.id, "automod_exempt_channel_ids") or []
        cur = await self.bot.db.conn.execute(
            "SELECT applied, COUNT(*) AS n FROM mod_cases WHERE guild_id = ? AND kind = 'automod' "
            "GROUP BY applied",
            (guild.id,),
        )
        totals = {int(row["applied"]): int(row["n"]) for row in await cur.fetchall()}
        lines = [
            f"**mode** — {mode}",
            f"**staff (always exempt)** — {staff_roles_sentence(staff)}",
            f"**tells the member** — {store.get(guild.id, 'mod_dm_on_action')}",
            f"**warn threshold** — {store.get(guild.id, 'automod_warn_threshold')} (log only)",
            "**modlog** — "
            + (f"<#{store.get(guild.id, 'modlog_channel_id')}>"
               if store.get(guild.id, "modlog_channel_id") else "not set"),
            "**exempt roles** — "
            + (", ".join(f"<@&{r}>" for r in roles) if roles else "staff only"),
            "**exempt channels** — "
            + (", ".join(f"<#{c}>" for c in channels) if channels else "none"),
            f"**seen** — {totals.get(1, 0)} acted on · {totals.get(0, 0)} logged only",
            "",
            *[describe_rule(name, rule_config(book, name)) for name in RULE_ORDER],
        ]
        if not staff and mode == "on":
            lines.append(NO_STAFF_WARNING)
        await interaction.response.send_message(
            "\n".join(lines), ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
        )

    @automod.command(name="mode", description="Turn automod off, to shadow, or on")
    @app_commands.describe(mode="off, shadow (log what it would do) or on (punish)")
    @app_commands.choices(
        mode=[app_commands.Choice(name=name, value=name) for name in AUTOMOD_MODES]
    )
    async def mode(
        self, interaction: discord.Interaction, mode: app_commands.Choice[str]
    ) -> None:
        if not await require_staff(interaction):
            return
        if mode.value == "on":
            store = self.bot.store
            if store.get(interaction.guild.id, "staff_channel_id") == (
                self.bot.settings.test_channel_id
            ):
                await interaction.response.send_message(
                    STAFF_IS_THE_TEST_CHANNEL, ephemeral=True
                )
                return
            if not store.staff_roles(interaction.guild):
                await interaction.response.send_message(NO_STAFF_ROLES, ephemeral=True)
                return
        await self.bot.store.set(
            interaction.guild.id, "automod_mode", mode.value, by=interaction.user.id
        )
        await interaction.response.send_message(
            f"Automod is now **{mode.value}**.", ephemeral=True
        )
        await log_action(
            self.bot,
            interaction.guild,
            "automod.mode",
            actor=interaction.user,
            details={"mode": mode.value},
        )

    @rule.command(name="enable", description="Arm one automod rule")
    @app_commands.describe(name="Which rule")
    async def rule_enable(self, interaction: discord.Interaction, name: str) -> None:
        await self._set_field(interaction, name, "enabled", "true")

    @rule.command(name="disable", description="Stop one automod rule running")
    @app_commands.describe(name="Which rule")
    async def rule_disable(self, interaction: discord.Interaction, name: str) -> None:
        await self._set_field(interaction, name, "enabled", "false")

    @rule.command(name="set", description="Change one number on one automod rule")
    @app_commands.describe(
        name="Which rule", field="What to change", value="What to change it to"
    )
    @app_commands.choices(
        field=[app_commands.Choice(name=item, value=item) for item in RULE_FIELDS]
    )
    async def rule_set(
        self,
        interaction: discord.Interaction,
        name: str,
        field: app_commands.Choice[str],
        value: str,
    ) -> None:
        await self._set_field(interaction, name, field.value, value)

    @rule_enable.autocomplete("name")
    @rule_disable.autocomplete("name")
    @rule_set.autocomplete("name")
    async def rule_names(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        lowered = (current or "").lower()
        return [
            app_commands.Choice(name=f"{name} — {RULE_HELP[name]}"[:100], value=name)
            for name in RULE_ORDER
            if lowered in name
        ][:25]

    async def _set_field(
        self, interaction: discord.Interaction, name: str, field: str, raw: str
    ) -> None:
        if not await require_staff(interaction):
            return
        if name not in RULE_ORDER:
            await interaction.response.send_message(
                UNKNOWN_RULE_CHOICE.format(given=name), ephemeral=True
            )
            return
        guild = interaction.guild
        book = dict(self.bot.store.get(guild.id, "automod_rules"))
        current = dict(rule_config(book, name))
        try:
            current[field] = _typed(field, raw)
            book[name] = normalise_rule(name, current)
            await self.bot.store.set(guild.id, "automod_rules", book, by=interaction.user.id)
        except (RuleError, ValueError) as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return
        await interaction.response.send_message(
            describe_rule(name, book[name]),
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        await log_action(
            self.bot,
            guild,
            "automod.rule",
            actor=interaction.user,
            details={"rule": name, field: book[name].get(field)},
        )

    @exempt.command(name="add", description="Let a role or a channel go unwatched")
    async def exempt_add(
        self,
        interaction: discord.Interaction,
        role: discord.Role | None = None,
        channel: discord.abc.GuildChannel | None = None,
    ) -> None:
        await self._change_exempt(interaction, role, channel, add=True)

    @exempt.command(name="remove", description="Watch a role or a channel again")
    async def exempt_remove(
        self,
        interaction: discord.Interaction,
        role: discord.Role | None = None,
        channel: discord.abc.GuildChannel | None = None,
    ) -> None:
        await self._change_exempt(interaction, role, channel, add=False)

    async def _change_exempt(
        self, interaction: discord.Interaction, role: Any, channel: Any, *, add: bool
    ) -> None:
        if not await require_staff(interaction):
            return
        if role is None and channel is None:
            await interaction.response.send_message(
                "Name a role or a channel — that command needs one of them to do anything.",
                ephemeral=True,
            )
            return
        guild = interaction.guild
        said: list[str] = []
        for entity, key, mark in (
            (role, "automod_exempt_role_ids", "@&"),
            (channel, "automod_exempt_channel_ids", "#"),
        ):
            if entity is None:
                continue
            ids = list(self.bot.store.get(guild.id, key) or [])
            if add and entity.id not in ids:
                ids.append(entity.id)
            elif not add and entity.id in ids:
                ids.remove(entity.id)
            else:
                said.append(
                    f"<{mark}{entity.id}> was already "
                    + ("exempt" if add else "not exempt")
                    + ", so nothing changed."
                )
                continue
            await self.bot.store.set(guild.id, key, ids, by=interaction.user.id)
            said.append(
                f"<{mark}{entity.id}> is "
                + ("exempt from automod now." if add else "watched by automod again.")
            )
            await log_action(
                self.bot,
                guild,
                "automod.exempt_add" if add else "automod.exempt_remove",
                actor=interaction.user,
                details={key: entity.id},
            )
        await interaction.response.send_message(
            " ".join(said), ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
        )

    @automod.command(
        name="parity", description="Compare what automod saw with what Carl-bot logged"
    )
    @app_commands.describe(days="How many days back to compare")
    async def parity(self, interaction: discord.Interaction, days: int = 7) -> None:
        if not await require_staff(interaction):
            return
        if not await self._database_ready(interaction):
            return
        guild = interaction.guild
        store = self.bot.store
        channel_id = store.get(guild.id, "carl_modlog_channel_id")
        if channel_id and channel_id == store.get(guild.id, "modlog_channel_id"):
            await interaction.response.send_message(PARITY_SAME_CHANNEL, ephemeral=True)
            return
        channel = (
            (self.bot.get_channel(channel_id) or guild.get_channel(channel_id))
            if channel_id
            else None
        )
        if channel is None:
            await interaction.response.send_message(NO_CARL_LOG, ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        since = within_days(days, PARITY_MAX_DAYS)
        carl: list[tuple[int, Any]] = []
        read = 0
        try:
            async for post in channel.history(limit=PARITY_HISTORY_LIMIT, after=since):
                read += 1
                user_id, when = parse_carl_entry(post)
                if user_id is not None:
                    carl.append((user_id, when))
        except discord.Forbidden:
            log.warning("automod: parity could not read %s — forbidden", channel_id)
            await interaction.followup.send(
                CARL_LOG_FORBIDDEN.format(channel_id=channel_id),
                ephemeral=True,
                allowed_mentions=discord.AllowedMentions.none(),
            )
            return
        except discord.HTTPException as exc:
            log.warning("automod: parity could not read %s — %s", channel_id, exc)
            await interaction.followup.send(
                CARL_LOG_FAILED.format(channel_id=channel_id),
                ephemeral=True,
                allowed_mentions=discord.AllowedMentions.none(),
            )
            return
        rows = await armed_verdicts_since(self.bot.db, guild.id, since)
        bloc = [(user_id, parse_ts(at)) for user_id, at in rows]
        report = parity_report(bloc, carl)
        lines = [
            PARITY_HEADER.format(
                days=max(1, min(int(days or 1), PARITY_MAX_DAYS)), bloc=len(bloc), carl=len(carl)
            ),
            PARITY_VERDICT.format(**report),
        ]
        if read >= PARITY_HISTORY_LIMIT:
            lines.insert(1, PARITY_TRUNCATED.format(limit=PARITY_HISTORY_LIMIT))
        if getattr(self.bot, "guard", None) is not None:
            lines.append(PARITY_TEST_MODE)
        await interaction.followup.send(
            "\n".join(lines), ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
        )


def _typed(field: str, raw: str) -> Any:
    text = str(raw or "").strip()
    if field == "enabled":
        if text.lower() in ("true", "yes", "on"):
            return True
        if text.lower() in ("false", "no", "off"):
            return False
        raise RuleError(f"`enabled` takes true or false, not {raw!r}.")
    if field in ("window_s", "threshold", "timeout_s"):
        if not text.isdigit():
            raise RuleError(f"`{field}` takes a whole number, not {raw!r}.")
        return int(text)
    if field in ("actions", "words"):
        return text
    raise RuleError(f"`{field}` is not something an automod rule has.")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AutoMod(bot))
