from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands, tasks

from ...actionlog import (
    LOGS_DEFAULT,
    LOGS_MAX,
    LOGS_MIN,
    log_action,
    send_logs,
)
from ...command_errors import NETWORK_ERRORS, AnswersErrors
from ...command_visibility import STAFF_ONLY
from ...events import DESCRIPTION_LIMIT, START_IN_THE_PAST, clamp, start_error
from ...golive import now_iso, parse_ts
from ...raidtrain import (
    CANCELLED,
    CAP_REACHED,
    DONE,
    LIVE,
    LOCKED,
    NEEDS_LINK,
    NOT_YOURS,
    OPEN,
    OPEN_STATUSES,
    SLOT_COUNT_MAX,
    SLOT_COUNT_MIN,
    SLOT_MINUTES_MAX,
    SLOT_MINUTES_MIN,
    SLOT_TAKEN,
    SLOT_UNKNOWN,
    STATUS_WORDS,
    TITLE_LIMIT,
    TRAIN_FULL,
    TRAIN_LOCKED,
    cancelled_text,
    caps_ok,
    due_checkins,
    due_reminders,
    live_post_text,
    may_move,
    missed_reminders,
    move_refusal,
    neighbours,
    next_open_position,
    positions_word,
    reminder_text,
    render_lineup,
    slot_at,
    slot_times,
    slots_held,
)
from ...settings_store import DB_UNAVAILABLE, GUILD_ONLY, RAIDTRAIN_MODES, require_staff
from ...timezones import START_EXAMPLE, get_timezone, parse_start, unix

log = logging.getLogger(__name__)

SWEEPS_BEFORE_DEGRADED = 3
CHOICE_LIMIT = 25
LIST_LIMIT = 20
MINE_LIMIT = 10
MODAL_ZONE_HINT = "{example} — read in {tz}"

FEATURE_OFF = (
    "Raid trains are **{mode}** on this server, so nothing was done. A Lead turns them on with "
    "`/raidtrains mode on`."
)
NOT_AN_ORGANIZER = (
    "Building a raid train's lineup is for {who}, so nothing was changed. Ask one of them to "
    "make the change, or to give you the organizer role."
)
NO_SUCH_TRAIN = (
    "Black Bloc has no raid train **{train}** here, so nothing was done. `/raidtrain list` shows "
    "the ones coming up."
)
NOTHING_UPCOMING = (
    "There is no raid train on the calendar right now. An organizer starts one with "
    "`/raidtrain create`."
)
NOTHING_HELD = "You do not hold a slot on any raid train. `/raidtrain list` shows what is running."
BAD_NUMBER = (
    "**{given}** is not a whole number, so no train was made. Slots are {min}–{max} minutes "
    "long, and a train runs {count_min}–{count_max} of them."
)
OUT_OF_RANGE = (
    "A raid train runs {count_min} to {count_max} slots of {min} to {max} minutes each, so "
    "nothing was made. Discord will not carry a longer lineup in one message."
)
CREATED = (
    "**{title}** is up with {count} slot(s) of {minutes} minutes, starting <t:{when}:F>. "
    "{where} People claim an hour with `/raidtrain claim`."
)
LINEUP_HERE = "The lineup is in <#{channel_id}>."
LINEUP_NOWHERE = (
    "There is nowhere to put the lineup yet — a Lead runs `/raidtrains setup channel:#somewhere`, "
    "and until then the train only shows on the dashboard."
)
CLAIMED = (
    "Slot **#{position}** on **{title}** is yours — <t:{when}:F> (<t:{when}:R>). You will get a "
    "DM before it starts saying who raids into you and who you raid next."
)
CLAIMED_SHADOW = " Raid trains are in **shadow** at the moment, so no DM is actually sent."
RELEASED = (
    "Slot **#{position}** on **{title}** is open again, so somebody else can take that hour."
)
ASSIGNED = "Slot **#{position}** on **{title}** now belongs to {who}."
UNASSIGNED = "Slot **#{position}** on **{title}** is open again."
NOBODY_THERE = "Slot **#{position}** is already empty, so there was nothing to take off it."
SWAPPED = "Slots **#{a}** and **#{b}** on **{title}** have changed places."
SAME_SLOT = "Those are the same slot, so nothing was changed."
LOCKED_NOW = "**{title}** is locked — its lineup cannot be changed until it is unlocked."
UNLOCKED_NOW = "**{title}** is open for sign-ups again."
CANCELLED_NOW = "**{title}** is cancelled, and the {count} person/people who held a slot were told."
MEMBER_NOT_LINKED = (
    "**{who}** has no Twitch channel linked, so the lineup cannot say who to raid. They run "
    "`/twitch link`, or a Lead turns `raidtrain_require_link` off."
)
MODE_SET = "Raid trains are now **{mode}**.{extra}"
NO_CHANNEL_YET = (
    " Nothing has anywhere to be posted yet: neither `raidtrain_channel_id` nor "
    "`events_announce_channel_id` is set. `/raidtrains setup channel:#somewhere` fixes that."
)
SETUP_NOTHING = (
    "Nothing was given, so nothing changed. Pass a channel, an organizer role, a ping role, or "
    "any mix — `/raidtrains setup channel:#raids organizer_role:@Organizers`."
)
SETUP_DONE = "Raid trains: {parts}."


def _row(row: Any, key: str, fallback: Any = None) -> Any:
    if row is None:
        return fallback
    try:
        return row[key]
    except (IndexError, KeyError, TypeError):
        return fallback


async def create_train(
    db: Any,
    guild_id: int,
    organizer_id: int,
    *,
    title: str,
    description: str,
    starts_at: datetime,
    slot_minutes: int,
    slot_count: int,
) -> int:
    """One train and every one of its slots, so a swap never has to rewrite a time."""
    at = now_iso()
    cur = await db.conn.execute(
        "INSERT INTO raid_trains(guild_id, organizer_id, title, description, starts_at, "
        "slot_minutes, slot_count, status, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            guild_id,
            organizer_id,
            title,
            description or None,
            starts_at.astimezone(UTC).isoformat(),
            int(slot_minutes),
            int(slot_count),
            OPEN,
            at,
            at,
        ),
    )
    train_id = int(cur.lastrowid)
    for index, (start, finish) in enumerate(slot_times(starts_at, slot_minutes, slot_count), 1):
        await db.conn.execute(
            "INSERT INTO raid_slots(train_id, position, starts_at, ends_at) VALUES (?, ?, ?, ?)",
            (
                train_id,
                index,
                start.astimezone(UTC).isoformat(),
                finish.astimezone(UTC).isoformat(),
            ),
        )
    await db.conn.commit()
    return train_id


async def get_train(db: Any, guild_id: int, train_id: Any) -> Any:
    cur = await db.conn.execute(
        "SELECT * FROM raid_trains WHERE id = ? AND guild_id = ?", (int(train_id), guild_id)
    )
    return await cur.fetchone()


async def list_trains(db: Any, guild_id: int, *, scope: str = "upcoming") -> list[Any]:
    sql = "SELECT * FROM raid_trains WHERE guild_id = ?"
    params: tuple[Any, ...] = (guild_id,)
    if scope == "upcoming":
        sql += " AND status IN ({})".format(",".join("?" * len(OPEN_STATUSES)))
        params += OPEN_STATUSES
    elif scope == "past":
        sql += " AND status IN (?, ?)"
        params += (DONE, CANCELLED)
    cur = await db.conn.execute(sql + " ORDER BY starts_at, id", params)
    return list(await cur.fetchall())


async def slots_for(db: Any, train_id: Any) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT * FROM raid_slots WHERE train_id = ? ORDER BY position", (int(train_id),)
    )
    return list(await cur.fetchall())


async def slots_of_member(db: Any, guild_id: int, user_id: int) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT s.*, t.title AS train_title, t.id AS train_id, t.status AS train_status "
        "FROM raid_slots s JOIN raid_trains t ON t.id = s.train_id "
        "WHERE t.guild_id = ? AND s.user_id = ? AND t.status != ? ORDER BY s.starts_at",
        (guild_id, user_id, CANCELLED),
    )
    return list(await cur.fetchall())


async def take_slot(db: Any, slot_id: int, user_id: int, login: Any, by: int | None) -> bool:
    """False when another click already had it — the WHERE clause is the race guard."""
    cur = await db.conn.execute(
        "UPDATE raid_slots SET user_id = ?, twitch_login = ?, claimed_at = ?, assigned_by = ? "
        "WHERE id = ? AND user_id IS NULL",
        (user_id, login or None, now_iso(), by, int(slot_id)),
    )
    await db.conn.commit()
    return bool(cur.rowcount)


async def empty_slot(db: Any, slot_id: int) -> bool:
    cur = await db.conn.execute(
        "UPDATE raid_slots SET user_id = NULL, twitch_login = NULL, claimed_at = NULL, "
        "assigned_by = NULL, reminded_at = NULL, checked_in_at = NULL, live_posted_at = NULL "
        "WHERE id = ? AND user_id IS NOT NULL",
        (int(slot_id),),
    )
    await db.conn.commit()
    return bool(cur.rowcount)


async def swap_holders(db: Any, first: Any, second: Any) -> None:
    """Only who is in the seat moves; the times belong to the position, not to the person."""
    carried = ("user_id", "twitch_login", "claimed_at", "assigned_by", "reminded_at")
    for target, source in ((first, second), (second, first)):
        await db.conn.execute(
            "UPDATE raid_slots SET "
            + ", ".join(f"{name} = ?" for name in carried)
            + " WHERE id = ?",
            tuple(_row(source, name) for name in carried) + (int(_row(target, "id")),),
        )
    await db.conn.commit()


async def set_status(db: Any, train_id: int, status: str, *, reason: Any = None) -> None:
    await db.conn.execute(
        "UPDATE raid_trains SET status = ?, cancel_reason = ?, updated_at = ? WHERE id = ?",
        (status, reason, now_iso(), int(train_id)),
    )
    await db.conn.commit()


async def set_lineup(
    db: Any,
    train_id: int,
    *,
    channel_id: int | None = None,
    message_id: int | None = None,
    thread_id: int | None = None,
    scheduled_event_id: int | None = None,
) -> None:
    await db.conn.execute(
        "UPDATE raid_trains SET channel_id = COALESCE(?, channel_id), "
        "lineup_message_id = COALESCE(?, lineup_message_id), "
        "thread_id = COALESCE(?, thread_id), "
        "scheduled_event_id = COALESCE(?, scheduled_event_id), updated_at = ? WHERE id = ?",
        (channel_id, message_id, thread_id, scheduled_event_id, now_iso(), int(train_id)),
    )
    await db.conn.commit()


async def stamp_slot(db: Any, slot_id: int, column: str) -> None:
    if column not in ("reminded_at", "checked_in_at", "live_posted_at"):
        raise ValueError(f"raid slots have no {column!r} to stamp")
    await db.conn.execute(
        f"UPDATE raid_slots SET {column} = ? WHERE id = ?", (now_iso(), int(slot_id))
    )
    await db.conn.commit()


async def twitch_login_of(db: Any, user_id: int) -> str | None:
    cur = await db.conn.execute(
        "SELECT twitch_login FROM golive_links WHERE user_id = ?", (int(user_id),)
    )
    row = await cur.fetchone()
    return str(row["twitch_login"]) if row else None


async def counts(db: Any, guild_id: int) -> dict[str, int]:
    async def scalar(sql: str, params: tuple[Any, ...]) -> int:
        cur = await db.conn.execute(sql, params)
        row = await cur.fetchone()
        return int(row["n"]) if row else 0

    marks = ",".join("?" * len(OPEN_STATUSES))
    return {
        "trains": await scalar(
            "SELECT COUNT(*) AS n FROM raid_trains WHERE guild_id = ?", (guild_id,)
        ),
        "upcoming": await scalar(
            f"SELECT COUNT(*) AS n FROM raid_trains WHERE guild_id = ? AND status IN ({marks})",
            (guild_id, *OPEN_STATUSES),
        ),
        "slots": await scalar(
            "SELECT COUNT(*) AS n FROM raid_slots s JOIN raid_trains t ON t.id = s.train_id "
            "WHERE t.guild_id = ?",
            (guild_id,),
        ),
        "claimed": await scalar(
            "SELECT COUNT(*) AS n FROM raid_slots s JOIN raid_trains t ON t.id = s.train_id "
            "WHERE t.guild_id = ? AND s.user_id IS NOT NULL",
            (guild_id,),
        ),
    }


async def dm(user: Any, text: str) -> bool:
    """Whether the person actually got told; DMs are the one place test mode leaves alone."""
    send = getattr(user, "send", None)
    if send is None:
        return False
    try:
        await send(text, allowed_mentions=discord.AllowedMentions.none())
    except Exception as exc:
        log.info("raidtrain: could not DM %s: %s", getattr(user, "id", "?"), exc)
        return False
    return True


class TrainModal(AnswersErrors, discord.ui.Modal, title="Start a raid train"):
    train_title = discord.ui.TextInput(label="Title", max_length=TITLE_LIMIT)
    description = discord.ui.TextInput(
        label="What is it?",
        style=discord.TextStyle.paragraph,
        max_length=DESCRIPTION_LIMIT,
        required=False,
    )
    start = discord.ui.TextInput(
        label="Start — YYYY-MM-DD HH:MM", placeholder=START_EXAMPLE, max_length=16
    )
    slot_minutes = discord.ui.TextInput(label="Minutes per slot", placeholder="60", max_length=4)
    slot_count = discord.ui.TextInput(label="How many slots", placeholder="8", max_length=3)

    def __init__(self, cog: RaidTrains, tz_name: str, minutes: int) -> None:
        super().__init__()
        self.cog = cog
        self.tz_name = tz_name
        self.slot_minutes.default = str(minutes)
        self.start.placeholder = MODAL_ZONE_HINT.format(example=START_EXAMPLE, tz=tz_name)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await self.cog.submit_train(
            interaction,
            tz_name=self.tz_name,
            title=clamp(self.train_title, TITLE_LIMIT),
            description=clamp(self.description, DESCRIPTION_LIMIT),
            start=str(self.start),
            slot_minutes=str(self.slot_minutes),
            slot_count=str(self.slot_count),
        )


class RaidTrains(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.last_sweep_ok_at: str | None = None
        self.last_sweep_error: str | None = None
        self.sweep_failures = 0
        self._locks: dict[int, asyncio.Lock] = {}

    raidtrain = app_commands.Group(
        name="raidtrain", description="Raid trains: sign up for an hour and pass the raid on"
    )
    raidtrains = app_commands.Group(
        name="raidtrains", description="Run raid trains", default_permissions=STAFF_ONLY
    )

    def loop_health(self, name: str) -> tuple[str | None, str | None]:
        if name != "sweep":
            return (None, None)
        return (self.last_sweep_ok_at, self.last_sweep_error)

    async def cog_load(self) -> None:
        if not self.bot.db.is_connected:
            return
        self.sweep.start()

    async def cog_unload(self) -> None:
        self.sweep.cancel()

    def _lock(self, train_id: int) -> asyncio.Lock:
        """One lock per train: two people claiming the same open slot are serialised here."""
        found = self._locks.get(int(train_id))
        if found is None:
            found = asyncio.Lock()
            self._locks[int(train_id)] = found
        return found

    # --- the sweep ----------------------------------------------------------------------------

    @tasks.loop(minutes=5)
    async def sweep(self) -> None:
        try:
            await self.sweep_once()
        except Exception as exc:
            self.last_sweep_error = f"{type(exc).__name__}: {exc}"
            self.sweep_failures += 1
            log.exception("raidtrain: the sweep failed")
            await self._sweep_degraded()
        self._retime()

    @sweep.before_loop
    async def _before_sweep(self) -> None:
        await self.bot.wait_until_ready()
        self._retime()

    @sweep.error
    async def _sweep_stopped(self, exc: BaseException) -> None:
        """discord.py stops a loop for the life of the process, so it is started again."""
        self.last_sweep_error = f"{type(exc).__name__}: {exc}"
        log.error("raidtrain: the sweep stopped; restarting it", exc_info=exc)
        self.sweep.restart()

    def _retime(self) -> None:
        wanted = self._minutes()
        if self.sweep.minutes != wanted:
            self.sweep.change_interval(minutes=wanted)

    def _minutes(self) -> int:
        guild = next(iter(getattr(self.bot, "guilds", ()) or ()), None)
        if guild is None:
            return 5
        return max(1, int(self.bot.store.get(guild.id, "raidtrain_poll_minutes")))

    async def _sweep_degraded(self) -> None:
        if self.sweep_failures != SWEEPS_BEFORE_DEGRADED:
            return
        for guild in list(getattr(self.bot, "guilds", ())):
            await log_action(
                self.bot,
                guild,
                "raidtrain.poll_degraded",
                details={"sweeps": self.sweep_failures, "reason": self.last_sweep_error},
            )

    async def sweep_once(self) -> None:
        if not self.bot.db.is_connected:
            return
        for guild in list(getattr(self.bot, "guilds", ())):
            if getattr(guild, "unavailable", False):
                continue
            if self._mode(guild.id) == "off":
                continue
            await self._sweep_guild(guild)
        self.last_sweep_ok_at = now_iso()
        self.last_sweep_error = None
        self.sweep_failures = 0

    async def _sweep_guild(self, guild: Any) -> None:
        now = datetime.now(UTC)
        for train in await list_trains(self.bot.db, guild.id, scope="upcoming"):
            async with self._lock(int(train["id"])):
                fresh = await get_train(self.bot.db, guild.id, train["id"])
                if fresh is None:
                    continue
                slots = await slots_for(self.bot.db, fresh["id"])
                moved = await self._run_clock(guild, fresh, slots, now)
                sent = await self._run_reminders(guild, fresh, slots, now)
                seen = await self._run_checkins(guild, fresh, slots, now)
                if moved or sent or seen:
                    await self._refresh_lineup(guild, fresh["id"])

    async def _run_clock(self, guild: Any, train: Any, slots: Any, now: datetime) -> bool:
        """Locks at the start, runs, and finishes — the poller owns all three."""
        from ...raidtrain import ends_at as train_ends_at

        starts = parse_ts(train["starts_at"])
        status = str(train["status"])
        if starts is None:
            return False
        details = {"train_id": train["id"], "title": train["title"], "slots": len(slots)}
        if status in (OPEN, LOCKED) and now >= starts:
            if status == OPEN:
                await set_status(self.bot.db, train["id"], LOCKED)
                await log_action(
                    self.bot,
                    guild,
                    "raidtrain.lock",
                    details=details | {"reason": "train_started"},
                )
            await set_status(self.bot.db, train["id"], LIVE)
            await log_action(self.bot, guild, "raidtrain.live", details=details)
            return True
        finish = train_ends_at(train, slots)
        if status == LIVE and finish is not None and now >= finish:
            await set_status(self.bot.db, train["id"], DONE)
            await log_action(self.bot, guild, "raidtrain.done", details=details)
            return True
        return False

    async def _run_reminders(self, guild: Any, train: Any, slots: Any, now: datetime) -> bool:
        lead = int(self.bot.store.get(guild.id, "raidtrain_reminder_minutes"))
        touched = False
        for slot in missed_reminders(now, slots):
            await stamp_slot(self.bot.db, slot["id"], "reminded_at")
            log.info(
                "raidtrain: slot %s on train %s started before its reminder was due",
                slot["position"],
                train["id"],
            )
            touched = True
        for slot in due_reminders(now, lead, slots):
            await stamp_slot(self.bot.db, slot["id"], "reminded_at")
            await self._remind(guild, train, slot, slots)
            touched = True
        return touched

    async def _remind(self, guild: Any, train: Any, slot: Any, slots: Any) -> None:
        """The stamp is already on the row, so a failure here loses one DM and never doubles it."""
        before, after = neighbours(slots, slot["position"])
        text = reminder_text(train, slot, before, after, self._jump(train))
        details = {
            "train_id": train["id"],
            "position": slot["position"],
            "user_id": slot["user_id"],
            "text": text,
        }
        mode = self._mode(guild.id)
        if mode != "on":
            await log_action(
                self.bot,
                guild,
                "raidtrain.would_remind",
                target=slot["user_id"],
                details=details | {"reason": f"mode_{mode}"},
            )
            return
        member = guild.get_member(slot["user_id"]) or self.bot.get_user(slot["user_id"])
        if await dm(member, text):
            await log_action(
                self.bot, guild, "raidtrain.remind", target=slot["user_id"], details=details
            )
            return
        await log_action(
            self.bot,
            guild,
            "raidtrain.dm_failed",
            target=slot["user_id"],
            details=details | {"reason": "dm_refused"},
        )

    async def _run_checkins(self, guild: Any, train: Any, slots: Any, now: datetime) -> bool:
        if not self.bot.store.get(guild.id, "raidtrain_live_posts"):
            return False
        if str(train["status"]) != LIVE:
            return False
        from .golive import open_sessions

        live = [int(row["user_id"]) for row in await open_sessions(self.bot.db, guild.id)]
        touched = False
        for slot in due_checkins(now, slots, live):
            await stamp_slot(self.bot.db, slot["id"], "checked_in_at")
            await log_action(
                self.bot,
                guild,
                "raidtrain.checkin",
                target=slot["user_id"],
                details={"train_id": train["id"], "position": slot["position"]},
            )
            await self._say_the_train_moved(guild, train, slot, slots)
            touched = True
        return touched

    async def _say_the_train_moved(self, guild: Any, train: Any, slot: Any, slots: Any) -> None:
        _before, after = neighbours(slots, slot["position"])
        text = live_post_text(train, slot, after)
        details = {"train_id": train["id"], "position": slot["position"], "text": text}
        mode = self._mode(guild.id)
        if mode != "on":
            await log_action(
                self.bot,
                guild,
                "raidtrain.would_post",
                details=details | {"reason": f"mode_{mode}"},
            )
            return
        where = train["thread_id"] or train["channel_id"] or self._channel_id(guild.id)
        message = await self._post(guild, where, text, details)
        if message is not None:
            await stamp_slot(self.bot.db, slot["id"], "live_posted_at")

    # --- posting ------------------------------------------------------------------------------

    def _channel_id(self, guild_id: int) -> int | None:
        """D7: blank means the events announcement channel, so one place is set up, not two."""
        store = self.bot.store
        return store.get(guild_id, "raidtrain_channel_id") or store.get(
            guild_id, "events_announce_channel_id"
        )

    def _mode(self, guild_id: int) -> str:
        return self.bot.store.get(guild_id, "raidtrain_mode")

    def _mentions(self, guild_id: int) -> discord.AllowedMentions:
        """Only the configured ping role; a display name on the lineup can never ping anybody."""
        role_id = self.bot.store.get(guild_id, "raidtrain_ping_role_id")
        return discord.AllowedMentions(
            everyone=False,
            users=False,
            roles=[discord.Object(role_id)] if role_id else False,
        )

    def _jump(self, train: Any) -> str | None:
        channel_id = _row(train, "channel_id")
        message_id = _row(train, "lineup_message_id")
        if not channel_id or not message_id:
            return None
        return f"https://discord.com/channels/{train['guild_id']}/{channel_id}/{message_id}"

    async def _post(
        self, guild: Any, channel_id: Any, text: str, details: dict[str, Any]
    ) -> Any:
        """The one guarded path anything of this feature takes to a channel."""
        if not channel_id:
            await log_action(
                self.bot,
                guild,
                "raidtrain.post_failed",
                details=details | {"reason": "no_channel_configured"},
            )
            return None
        guard = getattr(self.bot, "guard", None)
        if guard is not None and not guard.allows_channel(int(channel_id)):
            log.warning("raidtrain: TEST MODE — refused to post to channel %s", channel_id)
            await log_action(
                self.bot,
                guild,
                "raidtrain.post_skipped_test_mode",
                details=details | {"channel_id": int(channel_id)},
            )
            return None
        channel = self.bot.get_channel(int(channel_id)) or guild.get_channel(int(channel_id))
        if channel is None:
            await log_action(
                self.bot,
                guild,
                "raidtrain.post_failed",
                details=details | {"reason": "channel_not_visible"},
            )
            return None
        try:
            message = await channel.send(text, allowed_mentions=self._mentions(guild.id))
        except NETWORK_ERRORS as exc:
            log.warning("raidtrain: not posted — %s: %s", type(exc).__name__, exc)
            await log_action(
                self.bot,
                guild,
                "raidtrain.post_failed",
                details=details | {"reason": f"{type(exc).__name__}: {exc}"},
            )
            return None
        await log_action(
            self.bot, guild, "raidtrain.post", details=details | {"message_id": message.id}
        )
        return message

    async def publish_lineup(self, guild: Any, train_id: int) -> None:
        """The first post: the lineup, the thread under it, and Discord's own event if asked."""
        train = await get_train(self.bot.db, guild.id, train_id)
        if train is None:
            return
        slots = await slots_for(self.bot.db, train_id)
        text = render_lineup(
            train, slots, ping_role_id=self.bot.store.get(guild.id, "raidtrain_ping_role_id")
        )
        channel_id = self._channel_id(guild.id)
        details = {"train_id": train_id, "kind": "lineup"}
        if self._mode(guild.id) != "on":
            await log_action(
                self.bot,
                guild,
                "raidtrain.would_post",
                details=details | {"reason": f"mode_{self._mode(guild.id)}", "text": text},
            )
            return
        message = await self._post(guild, channel_id, text, details)
        if message is None:
            return
        await set_lineup(
            self.bot.db, train_id, channel_id=int(channel_id), message_id=int(message.id)
        )
        thread_id = await self._open_thread(guild, train, message)
        if thread_id is not None:
            await set_lineup(self.bot.db, train_id, thread_id=thread_id)
        await self._maybe_scheduled_event(guild, train_id)

    async def _open_thread(self, guild: Any, train: Any, message: Any) -> int | None:
        if not self.bot.store.get(guild.id, "raidtrain_thread"):
            return None
        maker = getattr(message, "create_thread", None)
        if maker is None:
            return None
        try:
            thread = await maker(name=clamp(train["title"], TITLE_LIMIT) or "Raid train")
        except NETWORK_ERRORS as exc:
            log.warning("raidtrain: no thread for train %s — %s", train["id"], exc)
            await log_action(
                self.bot,
                guild,
                "raidtrain.post_failed",
                details={
                    "train_id": train["id"],
                    "kind": "thread",
                    "reason": f"{type(exc).__name__}: {exc}",
                },
            )
            return None
        guard = getattr(self.bot, "guard", None)
        if guard is not None:
            guard.own_channel(thread)
        return int(thread.id)

    async def _maybe_scheduled_event(self, guild: Any, train_id: int) -> None:
        """D13: raid trains make their own, because Phase 4's helper writes to the events table."""
        if not self.bot.store.get(guild.id, "raidtrain_scheduled_event"):
            return
        train = await get_train(self.bot.db, guild.id, train_id)
        slots = await slots_for(self.bot.db, train_id)
        from ...raidtrain import ends_at as train_ends_at

        starts = parse_ts(train["starts_at"])
        finishes = train_ends_at(train, slots)
        details = {"train_id": train_id}
        if starts is None or finishes is None:
            await log_action(
                self.bot,
                guild,
                "raidtrain.create_scheduled_failed",
                details=details | {"reason": "unreadable_times"},
            )
            return
        if getattr(self.bot, "guard", None) is not None:
            log.warning("raidtrain: TEST MODE — no scheduled event made for train %s", train_id)
            await log_action(
                self.bot,
                guild,
                "raidtrain.would_create_scheduled",
                details=details | {"reason": "test_mode"},
            )
            return
        try:
            made = await guild.create_scheduled_event(
                name=clamp(train["title"], TITLE_LIMIT),
                description=clamp(train["description"], DESCRIPTION_LIMIT) or None,
                start_time=starts,
                end_time=finishes,
                entity_type=discord.EntityType.external,
                location=self._jump(train) or "Twitch",
                privacy_level=discord.PrivacyLevel.guild_only,
                reason=f"Black Bloc raid train {train_id}",
            )
        except NETWORK_ERRORS as exc:
            await log_action(
                self.bot,
                guild,
                "raidtrain.create_scheduled_failed",
                details=details | {"reason": f"{type(exc).__name__}: {exc}"},
            )
            return
        await set_lineup(self.bot.db, train_id, scheduled_event_id=int(made.id))

    async def _drop_scheduled_event(self, guild: Any, train: Any) -> None:
        scheduled_id = _row(train, "scheduled_event_id")
        if not scheduled_id or getattr(self.bot, "guard", None) is not None:
            return
        from ..community.events import find_scheduled_event

        try:
            found = await find_scheduled_event(guild, int(scheduled_id))
            if found is None:
                return
            if getattr(found, "status", None) is discord.EventStatus.active:
                await found.end(reason="Black Bloc raid train cancelled")
            else:
                await found.cancel(reason="Black Bloc raid train cancelled")
        except NETWORK_ERRORS as exc:
            await log_action(
                self.bot,
                guild,
                "raidtrain.cancel_scheduled_failed",
                details={"train_id": train["id"], "reason": f"{type(exc).__name__}: {exc}"},
            )

    async def _refresh_lineup(self, guild: Any, train_id: int) -> None:
        """The lineup post is edited in place, so one message is the whole record of a train."""
        train = await get_train(self.bot.db, guild.id, train_id)
        if train is None or not train["lineup_message_id"] or not train["channel_id"]:
            return
        slots = await slots_for(self.bot.db, train_id)
        text = render_lineup(
            train, slots, ping_role_id=self.bot.store.get(guild.id, "raidtrain_ping_role_id")
        )
        guard = getattr(self.bot, "guard", None)
        if guard is not None and not guard.allows_channel(int(train["channel_id"])):
            await log_action(
                self.bot,
                guild,
                "raidtrain.post_skipped_test_mode",
                details={"train_id": train_id, "kind": "lineup_edit"},
            )
            return
        channel = self.bot.get_channel(int(train["channel_id"])) or guild.get_channel(
            int(train["channel_id"])
        )
        if channel is None:
            return
        try:
            message = await channel.fetch_message(int(train["lineup_message_id"]))
            await message.edit(content=text, allowed_mentions=self._mentions(guild.id))
        except NETWORK_ERRORS as exc:
            log.warning("raidtrain: could not redraw the lineup for %s: %s", train_id, exc)
            await log_action(
                self.bot,
                guild,
                "raidtrain.post_failed",
                details={
                    "train_id": train_id,
                    "kind": "lineup_edit",
                    "reason": f"{type(exc).__name__}: {exc}",
                },
            )

    # --- gates --------------------------------------------------------------------------------

    async def _ready(self, interaction: discord.Interaction) -> bool:
        if interaction.guild is None:
            await interaction.response.send_message(GUILD_ONLY, ephemeral=True)
            return False
        if not self.bot.db.is_connected:
            await interaction.response.send_message(DB_UNAVAILABLE, ephemeral=True)
            return False
        mode = self._mode(interaction.guild.id)
        if mode == "off":
            await interaction.response.send_message(
                FEATURE_OFF.format(mode=mode), ephemeral=True
            )
            return False
        return True

    def _organizer_words(self, guild: Any) -> str:
        role_id = self.bot.store.get(guild.id, "raidtrain_organizer_role_id")
        return f"staff or <@&{role_id}>" if role_id else "staff"

    def is_organizer(self, member: Any) -> bool:
        guild = getattr(member, "guild", None)
        if guild is None:
            return False
        role_id = self.bot.store.get(guild.id, "raidtrain_organizer_role_id")
        if role_id and any(
            int(getattr(role, "id", 0)) == int(role_id) for role in getattr(member, "roles", ())
        ):
            return True
        return bool(self.bot.store.is_staff(member))

    async def _organizer(self, interaction: discord.Interaction) -> bool:
        if self.is_organizer(interaction.user):
            return True
        await interaction.response.send_message(
            NOT_AN_ORGANIZER.format(who=self._organizer_words(interaction.guild)),
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        return False

    async def _train_or_refusal(self, interaction: discord.Interaction, train: str) -> Any:
        row = None
        if str(train).strip().isdigit():
            row = await get_train(self.bot.db, interaction.guild.id, int(train))
        if row is None:
            await interaction.response.send_message(
                NO_SUCH_TRAIN.format(train=str(train)[:40]), ephemeral=True
            )
        return row

    # --- autocomplete -------------------------------------------------------------------------

    async def _train_choices(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        if interaction.guild is None or not self.bot.db.is_connected:
            return []
        typed = str(current or "").lower()
        found = []
        for row in await list_trains(self.bot.db, interaction.guild.id, scope="upcoming"):
            label = f"#{row['id']} {row['title']}"[:100]
            if typed and typed not in label.lower():
                continue
            found.append(app_commands.Choice(name=label, value=str(row["id"])))
        return found[:CHOICE_LIMIT]

    async def _slot_choices(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[int]]:
        if interaction.guild is None or not self.bot.db.is_connected:
            return []
        given = (interaction.namespace.train or "") if interaction.namespace else ""
        if not str(given).strip().isdigit():
            return []
        typed = str(current or "").lower()
        found = []
        for row in await slots_for(self.bot.db, int(given)):
            start = parse_ts(row["starts_at"])
            when = f"<t:{unix(start)}>" if start is None else start.strftime("%H:%M UTC")
            who = "open" if row["user_id"] is None else (row["twitch_login"] or "taken")
            label = f"#{row['position']} {when} — {who}"[:100]
            if typed and typed not in label.lower():
                continue
            found.append(app_commands.Choice(name=label, value=int(row["position"])))
        return found[:CHOICE_LIMIT]

    # --- member commands ----------------------------------------------------------------------

    @raidtrain.command(name="list", description="The raid trains coming up")
    async def list_command(self, interaction: discord.Interaction) -> None:
        if not await self._ready(interaction):
            return
        rows = await list_trains(self.bot.db, interaction.guild.id, scope="upcoming")
        if not rows:
            await interaction.response.send_message(NOTHING_UPCOMING, ephemeral=True)
            return
        lines = []
        for train in rows[:LIST_LIMIT]:
            slots = await slots_for(self.bot.db, train["id"])
            start = parse_ts(train["starts_at"])
            when = f"<t:{unix(start)}:F>" if start is not None else train["starts_at"]
            taken = len([one for one in slots if one["user_id"] is not None])
            lines.append(
                f"**#{train['id']} {train['title']}** — {when} · {taken}/{len(slots)} filled · "
                f"{STATUS_WORDS.get(str(train['status']), train['status'])} · "
                f"open: {positions_word(slots)}"
            )
        await interaction.response.send_message(
            "\n".join(lines), ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
        )

    @raidtrain.command(name="status", description="One train's whole lineup")
    @app_commands.describe(train="Which train")
    @app_commands.autocomplete(train=_train_choices)
    async def status_command(self, interaction: discord.Interaction, train: str) -> None:
        if not await self._ready(interaction):
            return
        row = await self._train_or_refusal(interaction, train)
        if row is None:
            return
        slots = await slots_for(self.bot.db, row["id"])
        await interaction.response.send_message(
            render_lineup(row, slots),
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @raidtrain.command(name="claim", description="Take an hour on a raid train")
    @app_commands.describe(train="Which train", slot="Which slot; the next open one by default")
    @app_commands.autocomplete(train=_train_choices, slot=_slot_choices)
    async def claim_command(
        self, interaction: discord.Interaction, train: str, slot: int | None = None
    ) -> None:
        if not await self._ready(interaction):
            return
        row = await self._train_or_refusal(interaction, train)
        if row is None:
            return
        login = await twitch_login_of(self.bot.db, interaction.user.id)
        if not login and self.bot.store.get(interaction.guild.id, "raidtrain_require_link"):
            await interaction.response.send_message(NEEDS_LINK, ephemeral=True)
            return
        async with self._lock(int(row["id"])):
            said = await self._claim(interaction, row, slot, login)
        await interaction.response.send_message(
            said, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
        )

    async def _claim(
        self, interaction: discord.Interaction, train: Any, position: Any, login: Any
    ) -> str:
        guild = interaction.guild
        if str(train["status"]) != OPEN:
            return TRAIN_LOCKED.format(title=train["title"])
        slots = await slots_for(self.bot.db, train["id"])
        ceiling = self.bot.store.get(guild.id, "raidtrain_max_slots_per_member")
        if not caps_ok(slots, interaction.user.id, ceiling):
            return CAP_REACHED.format(
                held=len(slots_held(slots, interaction.user.id)), title=train["title"]
            )
        if position is None:
            position = next_open_position(slots)
            if position is None:
                return TRAIN_FULL.format(title=train["title"])
        wanted = slot_at(slots, position)
        if wanted is None:
            return SLOT_UNKNOWN.format(position=position, last=len(slots))
        if not await take_slot(
            self.bot.db, wanted["id"], interaction.user.id, login, None
        ):
            return SLOT_TAKEN.format(position=position)
        await log_action(
            self.bot,
            guild,
            "raidtrain.claim",
            actor=interaction.user,
            target=interaction.user,
            details={
                "train_id": train["id"],
                "position": int(position),
                "twitch_login": login,
            },
        )
        await self._refresh_lineup(guild, train["id"])
        start = parse_ts(wanted["starts_at"])
        note = "" if self._mode(guild.id) == "on" else CLAIMED_SHADOW
        return (
            CLAIMED.format(
                position=position,
                title=train["title"],
                when=unix(start) if start is not None else 0,
            )
            + note
        )

    @raidtrain.command(name="release", description="Give an hour back")
    @app_commands.describe(train="Which train", slot="Which slot; yours by default")
    @app_commands.autocomplete(train=_train_choices, slot=_slot_choices)
    async def release_command(
        self, interaction: discord.Interaction, train: str, slot: int | None = None
    ) -> None:
        if not await self._ready(interaction):
            return
        row = await self._train_or_refusal(interaction, train)
        if row is None:
            return
        async with self._lock(int(row["id"])):
            said = await self._release(interaction, row, slot)
        await interaction.response.send_message(
            said, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
        )

    async def _release(self, interaction: discord.Interaction, train: Any, position: Any) -> str:
        if str(train["status"]) not in (OPEN,):
            return TRAIN_LOCKED.format(title=train["title"])
        slots = await slots_for(self.bot.db, train["id"])
        mine = slots_held(slots, interaction.user.id)
        wanted = slot_at(slots, position) if position is not None else (mine[0] if mine else None)
        if wanted is None or wanted["user_id"] != interaction.user.id:
            return NOT_YOURS.format(position=position if position is not None else "—")
        await empty_slot(self.bot.db, wanted["id"])
        await log_action(
            self.bot,
            interaction.guild,
            "raidtrain.release",
            actor=interaction.user,
            target=interaction.user,
            details={"train_id": train["id"], "position": wanted["position"]},
        )
        await self._refresh_lineup(interaction.guild, train["id"])
        return RELEASED.format(position=wanted["position"], title=train["title"])

    @raidtrain.command(name="mine", description="The raid-train slots you hold")
    async def mine_command(self, interaction: discord.Interaction) -> None:
        if not await self._ready(interaction):
            return
        rows = await slots_of_member(self.bot.db, interaction.guild.id, interaction.user.id)
        if not rows:
            await interaction.response.send_message(NOTHING_HELD, ephemeral=True)
            return
        lines = []
        for row in rows[:MINE_LIMIT]:
            start = parse_ts(row["starts_at"])
            when = (
                f"<t:{unix(start)}:F> (<t:{unix(start)}:R>)"
                if start is not None
                else row["starts_at"]
            )
            lines.append(
                f"**#{row['train_id']} {row['train_title']}** — slot #{row['position']}, {when}"
            )
        await interaction.response.send_message(
            "\n".join(lines), ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
        )

    # --- organizer commands -------------------------------------------------------------------

    @raidtrain.command(name="create", description="Start a raid train (organizers)")
    async def create_command(self, interaction: discord.Interaction) -> None:
        if not await self._ready(interaction):
            return
        if not await self._organizer(interaction):
            return
        tz_name = await get_timezone(self.bot.db, interaction.user.id)
        minutes = int(self.bot.store.get(interaction.guild.id, "raidtrain_slot_minutes"))
        await interaction.response.send_modal(TrainModal(self, tz_name, minutes))

    async def submit_train(
        self,
        interaction: discord.Interaction,
        *,
        tz_name: str,
        title: str,
        description: str,
        start: str,
        slot_minutes: str,
        slot_count: str,
    ) -> None:
        """Everything the modal typed, checked in words before a row is written."""
        starts = parse_start(start, tz_name)
        if starts is None:
            await interaction.response.send_message(
                start_error(start, tz_name, START_EXAMPLE), ephemeral=True
            )
            return
        if starts <= datetime.now(UTC):
            await interaction.response.send_message(
                START_IN_THE_PAST.format(given=clamp(start, 80), tz=tz_name), ephemeral=True
            )
            return
        numbers = self._numbers(slot_minutes, slot_count)
        if isinstance(numbers, str):
            await interaction.response.send_message(numbers, ephemeral=True)
            return
        minutes, count = numbers
        train_id = await create_train(
            self.bot.db,
            interaction.guild.id,
            interaction.user.id,
            title=title,
            description=description,
            starts_at=starts,
            slot_minutes=minutes,
            slot_count=count,
        )
        await log_action(
            self.bot,
            interaction.guild,
            "raidtrain.create",
            actor=interaction.user,
            details={
                "train_id": train_id,
                "title": title,
                "slot_minutes": minutes,
                "slot_count": count,
                "starts_at": starts.isoformat(),
            },
        )
        await self.publish_lineup(interaction.guild, train_id)
        channel_id = self._channel_id(interaction.guild.id)
        where = LINEUP_HERE.format(channel_id=channel_id) if channel_id else LINEUP_NOWHERE
        await interaction.response.send_message(
            CREATED.format(
                title=title, count=count, minutes=minutes, when=unix(starts), where=where
            ),
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )

    def _numbers(self, slot_minutes: Any, slot_count: Any) -> tuple[int, int] | str:
        try:
            minutes = int(str(slot_minutes).strip())
            count = int(str(slot_count).strip())
        except ValueError:
            return BAD_NUMBER.format(
                given=clamp(f"{slot_minutes} / {slot_count}", 60),
                min=SLOT_MINUTES_MIN,
                max=SLOT_MINUTES_MAX,
                count_min=SLOT_COUNT_MIN,
                count_max=SLOT_COUNT_MAX,
            )
        if not (SLOT_MINUTES_MIN <= minutes <= SLOT_MINUTES_MAX):
            return OUT_OF_RANGE.format(
                min=SLOT_MINUTES_MIN,
                max=SLOT_MINUTES_MAX,
                count_min=SLOT_COUNT_MIN,
                count_max=SLOT_COUNT_MAX,
            )
        if not (SLOT_COUNT_MIN <= count <= SLOT_COUNT_MAX):
            return OUT_OF_RANGE.format(
                min=SLOT_MINUTES_MIN,
                max=SLOT_MINUTES_MAX,
                count_min=SLOT_COUNT_MIN,
                count_max=SLOT_COUNT_MAX,
            )
        return (minutes, count)

    @raidtrain.command(name="assign", description="Put somebody in a slot (organizers)")
    @app_commands.describe(train="Which train", slot="Which slot", member="Who takes it")
    @app_commands.autocomplete(train=_train_choices, slot=_slot_choices)
    async def assign_command(
        self,
        interaction: discord.Interaction,
        train: str,
        slot: int,
        member: discord.Member,
    ) -> None:
        if not await self._ready(interaction):
            return
        if not await self._organizer(interaction):
            return
        row = await self._train_or_refusal(interaction, train)
        if row is None:
            return
        login = await twitch_login_of(self.bot.db, member.id)
        if not login and self.bot.store.get(interaction.guild.id, "raidtrain_require_link"):
            await interaction.response.send_message(
                MEMBER_NOT_LINKED.format(who=member.display_name),
                ephemeral=True,
                allowed_mentions=discord.AllowedMentions.none(),
            )
            return
        async with self._lock(int(row["id"])):
            said = await self._assign(interaction, row, slot, member, login)
        await interaction.response.send_message(
            said, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
        )

    async def _assign(
        self, interaction: discord.Interaction, train: Any, position: int, member: Any, login: Any
    ) -> str:
        slots = await slots_for(self.bot.db, train["id"])
        wanted = slot_at(slots, position)
        if wanted is None:
            return SLOT_UNKNOWN.format(position=position, last=len(slots))
        if wanted["user_id"] is not None:
            await empty_slot(self.bot.db, wanted["id"])
        await take_slot(self.bot.db, wanted["id"], member.id, login, interaction.user.id)
        await log_action(
            self.bot,
            interaction.guild,
            "raidtrain.assign",
            actor=interaction.user,
            target=member,
            details={"train_id": train["id"], "position": position, "twitch_login": login},
        )
        await self._refresh_lineup(interaction.guild, train["id"])
        return ASSIGNED.format(position=position, title=train["title"], who=member.display_name)

    @raidtrain.command(name="unassign", description="Empty a slot (organizers)")
    @app_commands.describe(train="Which train", slot="Which slot")
    @app_commands.autocomplete(train=_train_choices, slot=_slot_choices)
    async def unassign_command(
        self, interaction: discord.Interaction, train: str, slot: int
    ) -> None:
        if not await self._ready(interaction):
            return
        if not await self._organizer(interaction):
            return
        row = await self._train_or_refusal(interaction, train)
        if row is None:
            return
        async with self._lock(int(row["id"])):
            slots = await slots_for(self.bot.db, row["id"])
            wanted = slot_at(slots, slot)
            if wanted is None:
                said = SLOT_UNKNOWN.format(position=slot, last=len(slots))
            elif not await empty_slot(self.bot.db, wanted["id"]):
                said = NOBODY_THERE.format(position=slot)
            else:
                await log_action(
                    self.bot,
                    interaction.guild,
                    "raidtrain.unassign",
                    actor=interaction.user,
                    target=wanted["user_id"],
                    details={"train_id": row["id"], "position": slot},
                )
                await self._refresh_lineup(interaction.guild, row["id"])
                said = UNASSIGNED.format(position=slot, title=row["title"])
        await interaction.response.send_message(
            said, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
        )

    @raidtrain.command(name="swap", description="Change two slots round (organizers)")
    @app_commands.describe(train="Which train", first="One slot", second="The other")
    @app_commands.autocomplete(train=_train_choices)
    async def swap_command(
        self, interaction: discord.Interaction, train: str, first: int, second: int
    ) -> None:
        if not await self._ready(interaction):
            return
        if not await self._organizer(interaction):
            return
        row = await self._train_or_refusal(interaction, train)
        if row is None:
            return
        if int(first) == int(second):
            await interaction.response.send_message(SAME_SLOT, ephemeral=True)
            return
        async with self._lock(int(row["id"])):
            slots = await slots_for(self.bot.db, row["id"])
            one, other = slot_at(slots, first), slot_at(slots, second)
            if one is None or other is None:
                said = SLOT_UNKNOWN.format(
                    position=first if one is None else second, last=len(slots)
                )
            else:
                await swap_holders(self.bot.db, one, other)
                await log_action(
                    self.bot,
                    interaction.guild,
                    "raidtrain.swap",
                    actor=interaction.user,
                    details={"train_id": row["id"], "a": int(first), "b": int(second)},
                )
                await self._refresh_lineup(interaction.guild, row["id"])
                said = SWAPPED.format(a=first, b=second, title=row["title"])
        await interaction.response.send_message(
            said, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
        )

    @raidtrain.command(name="lock", description="Freeze a lineup (organizers)")
    @app_commands.describe(train="Which train")
    @app_commands.autocomplete(train=_train_choices)
    async def lock_command(self, interaction: discord.Interaction, train: str) -> None:
        await self._move(interaction, train, LOCKED)

    @raidtrain.command(name="unlock", description="Open a lineup for claims again (organizers)")
    @app_commands.describe(train="Which train")
    @app_commands.autocomplete(train=_train_choices)
    async def unlock_command(self, interaction: discord.Interaction, train: str) -> None:
        await self._move(interaction, train, OPEN)

    async def _move(self, interaction: discord.Interaction, train: str, to: str) -> None:
        if not await self._ready(interaction):
            return
        if not await self._organizer(interaction):
            return
        row = await self._train_or_refusal(interaction, train)
        if row is None:
            return
        if not may_move(row["status"], to):
            await interaction.response.send_message(
                move_refusal(row["status"], to), ephemeral=True
            )
            return
        await set_status(self.bot.db, row["id"], to)
        await log_action(
            self.bot,
            interaction.guild,
            "raidtrain.lock" if to == LOCKED else "raidtrain.unlock",
            actor=interaction.user,
            details={"train_id": row["id"], "title": row["title"]},
        )
        await self._refresh_lineup(interaction.guild, row["id"])
        said = LOCKED_NOW if to == LOCKED else UNLOCKED_NOW
        await interaction.response.send_message(
            said.format(title=row["title"]),
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @raidtrain.command(name="cancel", description="Call a raid train off (organizers)")
    @app_commands.describe(train="Which train", reason="What the people who signed up are told")
    @app_commands.autocomplete(train=_train_choices)
    async def cancel_command(
        self, interaction: discord.Interaction, train: str, reason: str
    ) -> None:
        if not await self._ready(interaction):
            return
        if not await self._organizer(interaction):
            return
        row = await self._train_or_refusal(interaction, train)
        if row is None:
            return
        if not may_move(row["status"], CANCELLED):
            await interaction.response.send_message(
                move_refusal(row["status"], CANCELLED), ephemeral=True
            )
            return
        await interaction.response.defer(ephemeral=True)
        told = await self.cancel_train(interaction.guild, row, reason, interaction.user)
        await interaction.followup.send(
            CANCELLED_NOW.format(title=row["title"], count=told),
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )

    async def cancel_train(self, guild: Any, train: Any, reason: str, actor: Any) -> int:
        """The state change first, then the DMs, then the cosmetics — the web calls it too."""
        said = clamp(reason, DESCRIPTION_LIMIT)
        await set_status(self.bot.db, train["id"], CANCELLED, reason=said or None)
        slots = await slots_for(self.bot.db, train["id"])
        holders = [int(one["user_id"]) for one in slots if one["user_id"] is not None]
        await log_action(
            self.bot,
            guild,
            "raidtrain.cancel",
            actor=actor,
            reason=said or None,
            details={"train_id": train["id"], "title": train["title"], "holders": len(holders)},
        )
        told = 0
        if self._mode(guild.id) == "on":
            text = cancelled_text(train, said)
            for user_id in dict.fromkeys(holders):
                member = guild.get_member(user_id) or self.bot.get_user(user_id)
                if await dm(member, text):
                    told += 1
                else:
                    await log_action(
                        self.bot,
                        guild,
                        "raidtrain.dm_failed",
                        target=user_id,
                        details={"train_id": train["id"], "reason": "cancel_dm_refused"},
                    )
        await self._drop_scheduled_event(guild, train)
        await self._refresh_lineup(guild, train["id"])
        return told

    # --- staff commands -----------------------------------------------------------------------

    @raidtrains.command(name="mode", description="Turn raid trains off, shadow or on")
    @app_commands.describe(mode="off, shadow (log only) or on (post and DM)")
    @app_commands.choices(
        mode=[app_commands.Choice(name=name, value=name) for name in RAIDTRAIN_MODES]
    )
    async def mode_command(
        self, interaction: discord.Interaction, mode: app_commands.Choice[str]
    ) -> None:
        if not await require_staff(interaction):
            return
        await self.bot.store.set(
            interaction.guild.id, "raidtrain_mode", mode.value, by=interaction.user.id
        )
        extra = "" if self._channel_id(interaction.guild.id) else NO_CHANNEL_YET
        await interaction.response.send_message(
            MODE_SET.format(mode=mode.value, extra=extra), ephemeral=True
        )
        await log_action(
            self.bot,
            interaction.guild,
            "raidtrain.mode",
            actor=interaction.user,
            details={"mode": mode.value},
        )

    @raidtrains.command(name="setup", description="Where lineups go, and who may run them")
    @app_commands.describe(
        channel="Where a lineup post lives; leave it out to keep using the events channel",
        organizer_role="Role that may build a lineup as well as staff",
        ping_role="Role mentioned in front of a lineup post",
    )
    async def setup_command(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel | None = None,
        organizer_role: discord.Role | None = None,
        ping_role: discord.Role | None = None,
    ) -> None:
        if not await require_staff(interaction):
            return
        if channel is None and organizer_role is None and ping_role is None:
            await interaction.response.send_message(SETUP_NOTHING, ephemeral=True)
            return
        store = self.bot.store
        parts = []
        for value, key, word in (
            (channel, "raidtrain_channel_id", "lineups go to {}"),
            (organizer_role, "raidtrain_organizer_role_id", "organizers are {}"),
            (ping_role, "raidtrain_ping_role_id", "{} is pinged"),
        ):
            if value is None:
                continue
            await store.set(interaction.guild.id, key, value.id, by=interaction.user.id)
            parts.append(word.format(value.mention))
        await interaction.response.send_message(
            SETUP_DONE.format(parts=", ".join(parts)),
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        await log_action(
            self.bot,
            interaction.guild,
            "raidtrain.setup",
            actor=interaction.user,
            details={
                "channel_id": getattr(channel, "id", None),
                "organizer_role_id": getattr(organizer_role, "id", None),
                "ping_role_id": getattr(ping_role, "id", None),
            },
        )

    @raidtrains.command(name="logs", description="The last few raid-train log lines")
    @app_commands.describe(
        count="How many lines, 1 to 50 (10 by default)",
        important_only="True to leave out the dry runs and the housekeeping",
    )
    async def logs_command(
        self,
        interaction: discord.Interaction,
        count: app_commands.Range[int, LOGS_MIN, LOGS_MAX] = LOGS_DEFAULT,
        important_only: bool = False,
    ) -> None:
        await send_logs(interaction, "raidtrain", count=count, important_only=important_only)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RaidTrains(bot))
