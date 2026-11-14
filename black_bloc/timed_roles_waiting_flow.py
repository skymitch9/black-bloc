from __future__ import annotations

import logging
import re
from datetime import timedelta
from typing import Any

import discord

from . import rolegrants as grants
from . import timed_roles as timed
from . import timed_roles_by_hand as hand
from . import timed_roles_waiting as waits
from .actionlog import log_action
from .cogs.community import role_menus as rm
from .command_errors import NETWORK_ERRORS, AnswersErrors, SafeDynamicItem
from .logkinds import VIA_DISCORD, kind_via
from .panels import answer, capped_placeholder, db_up, still_staff
from .settings_store import (
    GUILD_ONLY,
    ROLEMENU_WAIT_MAX_DAYS_KEY,
    ROLEMENU_WAIT_PING_ROLE_KEY,
    ROLEMENU_WAIT_REMINDER_DAYS_KEY,
    ROLEMENU_WAIT_REMOVAL_DAYS_KEY,
    ROLEMENU_WAIT_REVERT_DAYS_KEY,
)

log = logging.getLogger(__name__)

REMOVE_REASON = "Black Bloc: nobody picked an event for a timed role"
REVERT_REASON = "Black Bloc: {actor} reverted a timed role's removal"
TAKE_OFF_REASON = "Black Bloc: {actor} took a waiting timed role off"
CONFIRM_SECONDS = 180


def word(bot: Any, guild_id: int, key: str, limit: int | None = None, **fields: Any) -> str:
    return rm.word(bot, guild_id, key, limit, **fields)


def offsets_of(bot: Any, guild_id: int) -> list[int]:
    return waits.live_offsets(
        bot.store.get(guild_id, ROLEMENU_WAIT_REMINDER_DAYS_KEY), removal_days(bot, guild_id)
    )


def removal_days(bot: Any, guild_id: int) -> int:
    return int(bot.store.get(guild_id, ROLEMENU_WAIT_REMOVAL_DAYS_KEY))


def revert_days(bot: Any, guild_id: int) -> int:
    return int(bot.store.get(guild_id, ROLEMENU_WAIT_REVERT_DAYS_KEY))


def stamp(at: Any) -> str:
    return grants.stamp(at, "D")


def roles_of(role_ids: Any) -> str:
    return rm.roles_named(role_ids)


def member_of(user_id: Any) -> str:
    return f"<@{int(user_id)}>"


def staff_of(user_id: Any) -> str:
    return f"<@{int(user_id)}>" if user_id else "Black Bloc"


def mentions(user_ids: Any) -> discord.AllowedMentions:
    wanted = [discord.Object(id=int(one)) for one in dict.fromkeys(user_ids or ()) if one]
    return discord.AllowedMentions(everyone=False, roles=False, users=wanted or False)


def date_refusal(bot: Any, guild_id: int, typed: Any) -> tuple[str | None, Any]:
    """(why not, the moment): unreadable, gone by, or further off than the ceiling key."""
    refusal, when = rm.typed_refusal(bot, guild_id, typed)
    if refusal:
        return refusal, None
    refusal = too_far(bot, guild_id, when)
    return (refusal, None) if refusal else (None, when)


def too_far(bot: Any, guild_id: int, when: Any) -> str | None:
    most = int(bot.store.get(guild_id, ROLEMENU_WAIT_MAX_DAYS_KEY))
    if when <= waits.now() + timedelta(days=most):
        return None
    return word(bot, guild_id, "rolemenu_wait_too_far_said", when=stamp(when), days=most)


def entry_line(bot: Any, guild: Any, entry: dict[str, Any], shown: Any = None) -> str:
    when = shown or stamp
    return word(
        bot,
        guild.id,
        "rolemenu_wait_line",
        member=member_of(entry["user_id"]),
        roles=roles_of(entry["role_ids"]),
        date=when(entry["until"]),
        removal=when(waits.iso(waits.removal_at(entry["until"], removal_days(bot, guild.id)))),
    )


async def waiting_entries(bot: Any, guild: Any, user_id: Any = None) -> list[dict[str, Any]]:
    return waits.entries(await waits.waiting(bot.db, guild.id, user_id))


async def entry_of(bot: Any, guild: Any, user_id: int) -> dict[str, Any] | None:
    found = await waiting_entries(bot, guild, user_id)
    return found[0] if found else None


# --- the by-hand post in its waiting state ------------------------------------------------------


def later_button(bot: Any, guild_id: int, prompt_id: int) -> Any:
    return ByHandLater(
        prompt_id,
        discord.ui.Button(
            custom_id=waits.later_id(prompt_id),
            label=word(bot, guild_id, "rolemenu_pick_later_button", rm.BUTTON_MAX),
            style=discord.ButtonStyle.secondary,
            row=1,
        ),
    )


def move_button(bot: Any, guild_id: int, user_id: int, move: str, row: int) -> Any:
    key = {
        waits.DATE: "rolemenu_wait_change_date_button",
        waits.OFF: "rolemenu_wait_take_off_button",
        waits.NEW: "rolemenu_new_event_button",
    }[move]
    style = discord.ButtonStyle.danger if move == waits.OFF else discord.ButtonStyle.secondary
    return WaitMove(
        user_id,
        move,
        discord.ui.Button(
            custom_id=waits.move_id(user_id, move),
            label=word(bot, guild_id, key, rm.BUTTON_MAX),
            style=style,
            row=row,
        ),
    )


def event_select(bot: Any, guild_id: int, user_id: int, events: Any) -> Any:
    shown = list(events or ())[: rm.OPTIONS_MAX]
    return WaitEventPick(
        user_id,
        discord.ui.Select(
            custom_id=waits.pick_id(user_id),
            placeholder=capped_placeholder(
                len(shown),
                len(list(events)),
                pick=word(bot, guild_id, "rolemenu_by_hand_pick"),
                capped=word(
                    bot, guild_id, "rolemenu_events_capped", shown="{shown}", total="{total}"
                ),
            )[: rm.SELECT_PLACEHOLDER_MAX],
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(
                    label=rm.event_name(one)[: rm.LABEL_MAX], value=str(int(one["id"]))
                )
                for one in shown
            ],
            row=0,
        ),
    )


def entry_view(bot: Any, guild_id: int, user_id: int, events: Any) -> discord.ui.View:
    """Pick an event · New event… · Change the date… · Take it off now, for one member."""
    view = discord.ui.View(timeout=None)
    if events:
        view.add_item(event_select(bot, guild_id, user_id, events))
    for move in (waits.NEW, waits.DATE, waits.OFF):
        view.add_item(move_button(bot, guild_id, user_id, move, row=1))
    return view


def waiting_post_text(bot: Any, guild_id: int, prompt: Any, rows: Any) -> str:
    open_rows = [row for row in rows if row["state"] == waits.WAITING]
    lead = open_rows[0] if open_rows else rows[0]
    return word(
        bot,
        guild_id,
        "rolemenu_wait_post_text",
        who=rm.by_hand_who(bot, guild_id, prompt["added_by"]),
        member=member_of(prompt["user_id"]),
        roles=roles_of([row["role_id"] for row in open_rows] or hand.role_ids_of(prompt)),
        date=stamp(lead["until"]),
        staff=staff_of(lead["set_by"]),
    )[: rm.NOTICE_LIMIT]


async def edit_post(bot: Any, prompt: Any, content: str, view: Any) -> None:
    """Cosmetic: the post says where it stands; a post Discord will not edit is logged only."""
    channel = bot.get_channel(prompt["channel_id"]) if prompt["channel_id"] else None
    if channel is None or not prompt["message_id"]:
        return
    try:
        message = channel.get_partial_message(int(prompt["message_id"]))
        await message.edit(
            content=content[: rm.NOTICE_LIMIT],
            view=view,
            allowed_mentions=discord.AllowedMentions.none(),
        )
    except (*NETWORK_ERRORS, LookupError, AttributeError) as exc:
        log.info("timed roles: could not edit by-hand post %s: %s", prompt["id"], exc)


async def show_waiting_post(bot: Any, guild: Any, prompt: Any) -> None:
    rows = await waits.of_prompt(bot.db, prompt["id"])
    if not any(row["state"] == waits.WAITING for row in rows):
        return
    events = await timed.open_events(bot.db, guild.id)
    view = rm.by_hand_view(bot, guild.id, prompt["id"], events, waiting=True)
    view.add_item(move_button(bot, guild.id, int(prompt["user_id"]), waits.DATE, row=2))
    view.add_item(move_button(bot, guild.id, int(prompt["user_id"]), waits.OFF, row=2))
    await edit_post(bot, prompt, waiting_post_text(bot, guild.id, prompt, rows), view)


async def settle_posts(
    bot: Any,
    guild: Any,
    prompt_ids: Any,
    text_key: str,
    actor: Any = None,
    menu: Any = None,
    **fields: Any,
) -> None:
    """Every post whose roles no longer wait is finished and says why, with nothing to press."""
    for prompt_id in dict.fromkeys(int(one) for one in prompt_ids or ()):
        prompt = await hand.get_prompt(bot.db, prompt_id)
        if prompt is None:
            continue
        menu_id = int(menu["id"]) if menu is not None else None
        if not await hand.finish(bot.db, prompt_id, menu_id=menu_id, by=rm.actor_id(actor)):
            if await hand.still_waiting(bot.db, prompt_id):
                await show_waiting_post(bot, guild, prompt)
            continue
        if menu is not None:
            await rm.close_by_hand_post(bot, guild, prompt, menu, actor)
            continue
        text = word(
            bot,
            guild.id,
            text_key,
            who=rm.by_hand_who(bot, guild.id, prompt["added_by"]),
            member=member_of(prompt["user_id"]),
            roles=roles_of(hand.role_ids_of(prompt)),
            staff=staff_of(rm.actor_id(actor)),
            **fields,
        )
        await edit_post(bot, prompt, text, None)


# --- the moves: put to waiting, change the date, take it off, attach -----------------------------


async def put_to_waiting(
    bot: Any, guild: Any, actor: Any, prompt: Any, until: Any, *, via: str = VIA_DISCORD
) -> tuple[bool, str]:
    """Pick later…: each role of the post the member still wears waits for an event."""
    if prompt["attached_at"]:
        return False, word(bot, guild.id, "rolemenu_by_hand_gone_said")
    if await hand.still_waiting(bot.db, prompt["id"]):
        return False, word(bot, guild.id, "rolemenu_wait_already_said")
    member = guild.get_member(int(prompt["user_id"]))
    role_ids = hand.role_ids_of(prompt)
    worn = [one for one in role_ids if member is not None and one in {r.id for r in member.roles}]
    if not worn:
        return False, word(
            bot,
            guild.id,
            "rolemenu_by_hand_not_worn_said",
            member=member_of(prompt["user_id"]),
            roles=roles_of(role_ids),
        )
    assigner = prompt["added_by"] or rm.actor_id(actor)
    async with rm.guild_lock(bot, guild.id):
        made = await waits.put(
            bot.db,
            guild.id,
            member.id,
            worn,
            prompt_id=int(prompt["id"]),
            assigner_id=assigner,
            until=until,
            by=rm.actor_id(actor),
            offsets=offsets_of(bot, guild.id),
        )
    if not made:
        return False, word(bot, guild.id, "rolemenu_wait_already_said")
    await log_action(
        bot,
        guild,
        kind_via("role_menu.wait_set", via),
        actor=actor,
        target=member,
        details={
            "prompt_id": int(prompt["id"]),
            "roles": worn,
            "until": waits.iso(until),
            "assigner": assigner,
            "wait_ids": made,
            "via": via,
        },
    )
    await show_waiting_post(bot, guild, prompt)
    return True, word(
        bot,
        guild.id,
        "rolemenu_wait_set_said",
        member=member_of(member.id),
        date=stamp(waits.iso(until)),
        roles=roles_of(worn),
        who=staff_of(assigner),
    )


async def change_date(
    bot: Any, guild: Any, actor: Any, user_id: int, until: Any, *, via: str = VIA_DISCORD
) -> tuple[bool, str]:
    rows = await waits.waiting(bot.db, guild.id, user_id)
    if not rows:
        return False, word(bot, guild.id, "rolemenu_wait_gone_said", member=member_of(user_id))
    moved = await waits.set_until(
        bot.db, [row["id"] for row in rows], until, offsets_of(bot, guild.id), rm.actor_id(actor)
    )
    await log_action(
        bot,
        guild,
        kind_via("role_menu.wait_date_changed", via),
        actor=actor,
        target=int(user_id),
        details={
            "user": int(user_id),
            "roles": [int(row["role_id"]) for row in rows],
            "was": rows[0]["until"],
            "until": waits.iso(until),
            "moved": moved,
            "via": via,
        },
    )
    for prompt_id in {int(row["prompt_id"]) for row in rows if row["prompt_id"] is not None}:
        prompt = await hand.get_prompt(bot.db, prompt_id)
        if prompt is not None and not prompt["attached_at"]:
            await show_waiting_post(bot, guild, prompt)
    return True, word(
        bot,
        guild.id,
        "rolemenu_wait_date_changed_said",
        member=member_of(user_id),
        date=stamp(waits.iso(until)),
    )


async def take_off_now(
    bot: Any, guild: Any, actor: Any, user_id: int, *, via: str = VIA_DISCORD
) -> tuple[bool, str]:
    """Take it off now: the wait ends; the role comes off unless an event or `/pings` holds it."""
    member = guild.get_member(int(user_id))
    async with rm.guild_lock(bot, guild.id):
        rows = await waits.waiting(bot.db, guild.id, user_id)
        if not rows:
            return False, word(bot, guild.id, "rolemenu_wait_gone_said", member=member_of(user_id))
        worn = {int(r.id) for r in member.roles} if member is not None else set()
        held = [
            int(row["role_id"])
            for row in rows
            if int(row["role_id"]) in worn
            and await rm.held_elsewhere(bot, guild.id, user_id, row["role_id"])
        ]
        taking = [int(row["role_id"]) for row in rows if int(row["role_id"]) in worn]
        taking = [one for one in taking if one not in held]
        reason = TAKE_OFF_REASON.format(actor=actor)
        if taking and not await rm.change_roles(bot, member, guild, set(), set(taking), reason):
            await log_action(
                bot,
                guild,
                kind_via("role_menu.wait_take_off_failed", via),
                actor=actor,
                target=member,
                details={"user": int(user_id), "roles": taking, "via": via},
            )
            return False, word(
                bot,
                guild.id,
                "rolemenu_wait_refused_said",
                roles=roles_of(taking),
                member=member_of(user_id),
            )
        ended = await waits.end(
            bot.db, [row["id"] for row in rows], waits.TAKEN_OFF, by=rm.actor_id(actor)
        )
        if taking:
            await timed.close_member_roles(bot.db, guild.id, user_id, taking, grants.ENDED_BY_STAFF)
    await log_action(
        bot,
        guild,
        kind_via("role_menu.wait_taken_off", via),
        actor=actor,
        target=member if member is not None else int(user_id),
        details={
            "user": int(user_id),
            "taken": taking,
            "stayed_on": held,
            "wait_ids": ended,
            "via": via,
        },
    )
    await settle_posts(
        bot,
        guild,
        [row["prompt_id"] for row in rows if row["prompt_id"] is not None],
        "rolemenu_wait_post_taken_off_text",
        actor,
    )
    said = [
        word(
            bot,
            guild.id,
            "rolemenu_wait_taken_off_said",
            roles=roles_of([row["role_id"] for row in rows]),
            member=member_of(user_id),
        )
    ]
    if held:
        said.append(
            word(
                bot,
                guild.id,
                "rolemenu_wait_stays_on_text",
                roles=roles_of(held),
                member=member_of(user_id),
            )
        )
    return True, " ".join(said)


def take_off_question(bot: Any, guild_id: int, entry: dict[str, Any]) -> str:
    return word(
        bot,
        guild_id,
        "rolemenu_wait_take_off_question",
        roles=roles_of(entry["role_ids"]),
        member=member_of(entry["user_id"]),
    )


async def attach_entry(
    bot: Any, guild: Any, actor: Any, user_id: int, menu: Any, *, via: str = VIA_DISCORD
) -> tuple[bool, str]:
    """The member's waiting roles go on the event; a wait ends only once that is written."""
    rows = await waits.waiting(bot.db, guild.id, user_id)
    if not rows:
        return False, word(bot, guild.id, "rolemenu_wait_gone_said", member=member_of(user_id))
    member = guild.get_member(int(user_id))
    worn = {int(r.id) for r in member.roles} if member is not None else set()
    attached: list[int] = []
    for row in rows:
        role_id = int(row["role_id"])
        if role_id not in worn:
            continue
        found = await rm.give_event_role(
            bot, guild, actor, menu, role_id, [member], source=grants.BY_HAND_ATTACHED, via=via
        )
        if int(member.id) in {*found["had"], *found["given"], *found["already"]}:
            attached += await waits.end(
                bot.db, [row["id"]], waits.ATTACHED, by=rm.actor_id(actor), menu_id=int(menu["id"])
            )
    if not attached:
        return False, word(
            bot,
            guild.id,
            "rolemenu_wait_not_attached_said",
            member=member_of(user_id),
            event=rm.event_name(menu),
        )
    await log_action(
        bot,
        guild,
        kind_via("role_menu.wait_attached", via),
        actor=actor,
        target=member,
        details={
            "user": int(user_id),
            "menu": menu["name"],
            "menu_id": int(menu["id"]),
            "roles": [int(row["role_id"]) for row in rows if int(row["id"]) in attached],
            "wait_ids": attached,
            "via": via,
        },
    )
    await settle_posts(
        bot,
        guild,
        [row["prompt_id"] for row in rows if row["prompt_id"] is not None],
        "rolemenu_by_hand_attached_text",
        actor,
        menu,
    )
    return True, word(
        bot,
        guild.id,
        "rolemenu_wait_attached_said",
        members=member_of(user_id),
        event=rm.event_name(menu),
    )


async def wait_came_off(bot: Any, guild: Any, member: Any, role_ids: Any) -> list[int]:
    """A role that came off by hand, or by any path but the waiting pass, ends only its own wait."""
    ended = await waits.end_pairs(bot.db, guild.id, member.id, role_ids, waits.CAME_OFF)
    if ended:
        await log_action(
            bot,
            guild,
            "role_menu.wait_cleared",
            target=member,
            details={"user": int(member.id), "state": waits.CAME_OFF, "wait_ids": ended},
        )
    return ended


async def wait_left(bot: Any, guild: Any, member: Any) -> list[int]:
    ended = await waits.end_member(bot.db, guild.id, member.id, waits.LEFT)
    if ended:
        await log_action(
            bot,
            guild,
            "role_menu.wait_cleared",
            target=int(member.id),
            details={"user": int(member.id), "state": waits.LEFT, "wait_ids": ended},
        )
    return ended


# --- the waiting pass: reminders, then the removal -----------------------------------------------


async def waiting_pass(bot: Any, guild: Any) -> dict[str, int]:
    """One guild's waits: records first, then the removals due, then one reminder per assigner."""
    counts = {"waiting": 0, "reminded": 0, "removed": 0, "wait_failures": 0}
    if getattr(guild, "unavailable", False):
        return counts
    members = await rm.members_of(guild)
    if members is None:
        await log_action(
            bot, guild, "role_menu.wait_pass_failed", details={"reason": "members_not_loaded"}
        )
        counts["wait_failures"] += 1
        return counts
    days = removal_days(bot, guild.id)
    offsets = offsets_of(bot, guild.id)
    rows = await waits.waiting(bot.db, guild.id)
    due: dict[int, list[Any]] = {}
    reminders: dict[int, list[Any]] = {}
    for row in rows:
        member = guild.get_member(int(row["user_id"]))
        if member is None:
            await wait_left(bot, guild, discord.Object(id=int(row["user_id"])))
            continue
        if int(row["role_id"]) not in {int(r.id) for r in member.roles}:
            await wait_came_off(bot, guild, member, [row["role_id"]])
            continue
        if waits.removal_due(row, days):
            due.setdefault(int(member.id), []).append(row)
            continue
        if waits.reminder_due(row, offsets) is not None:
            reminders.setdefault(int(row["assigner_id"] or 0), []).append(row)
    for user_id, found in due.items():
        done = await remove_member(bot, guild, guild.get_member(user_id), found)
        counts["removed"] += done["removed"]
        counts["wait_failures"] += done["failures"]
    for assigner_id, found in reminders.items():
        if await remind(bot, guild, assigner_id, found, offsets):
            counts["reminded"] += len({int(row["user_id"]) for row in found})
        else:
            counts["wait_failures"] += 1
    counts["waiting"] = await waits.people_waiting(bot.db, guild.id)
    return counts


async def remind(bot: Any, guild: Any, assigner_id: int, rows: Any, offsets: Any) -> bool:
    """One message to one assigner: every entry of theirs with a reminder due, and a picker."""
    target, where = rm.card_target(bot, rm.by_hand_channel(bot, guild))
    entries = waits.entries(rows)
    details = {
        "assigner": assigner_id or None,
        "users": [one["user_id"] for one in entries],
        "wait_ids": [int(row["id"]) for row in rows],
    }
    if target is None:
        await log_action(
            bot, guild, "role_menu.wait_remind_failed", details=details | {"reason": where}
        )
        return False
    who = staff_of(assigner_id) if assigner_id else word(bot, guild.id, "rolemenu_by_hand_someone")
    lines = [word(bot, guild.id, "rolemenu_wait_reminder_text", who=who)]
    lines += [entry_line(bot, guild, one) for one in entries]
    try:
        await target.send(
            "\n".join(lines)[: rm.NOTICE_LIMIT],
            view=reminder_view(bot, guild, assigner_id, entries),
            allowed_mentions=mentions([assigner_id]),
        )
    except Exception as exc:
        await log_action(
            bot,
            guild,
            "role_menu.wait_remind_failed",
            details=details | {"reason": f"{type(exc).__name__}: {exc}"[:300]},
        )
        return False
    stages = {int(row["id"]): waits.reminder_due(row, offsets) or row["stage"] for row in rows}
    await waits.mark_reminded(bot.db, list(stages), stages)
    await log_action(
        bot,
        guild,
        "role_menu.wait_reminded",
        details=details | {"channel_id": int(target.id), "where": where},
    )
    return True


def reminder_view(bot: Any, guild: Any, assigner_id: int, entries: Any) -> discord.ui.View:
    view = discord.ui.View(timeout=None)
    shown = list(entries)[: rm.OPTIONS_MAX]
    view.add_item(
        ReminderPick(
            assigner_id,
            discord.ui.Select(
                custom_id=waits.reminder_id(assigner_id),
                placeholder=capped_placeholder(
                    len(shown),
                    len(list(entries)),
                    pick=word(bot, guild.id, "rolemenu_wait_pick"),
                    capped=word(
                        bot, guild.id, "rolemenu_wait_capped", shown="{shown}", total="{total}"
                    ),
                )[: rm.SELECT_PLACEHOLDER_MAX],
                min_values=1,
                max_values=1,
                options=[
                    discord.SelectOption(
                        label=rm.who_is(guild, one["user_id"])[: rm.LABEL_MAX],
                        value=str(one["user_id"]),
                    )
                    for one in shown
                ],
            ),
        )
    )
    return view


async def remove_member(bot: Any, guild: Any, member: Any, rows: Any) -> dict[str, int]:
    """The removal day: the notice first, then the roles off (unless held), rows `removed`."""
    found = {"removed": 0, "failures": 0}
    details = {"user": int(member.id), "wait_ids": [int(row["id"]) for row in rows]}
    if getattr(bot, "guard", None) is not None:
        await log_action(
            bot,
            guild,
            "role_menu.wait_would_remove",
            target=member,
            details=details | {"roles": [int(row["role_id"]) for row in rows]},
        )
        return found
    target, where = rm.card_target(bot, rm.by_hand_channel(bot, guild))
    if target is None:
        await log_action(
            bot,
            guild,
            "role_menu.wait_notice_failed",
            target=member,
            details=details | {"reason": where},
        )
        found["failures"] += 1
        return found
    async with rm.guild_lock(bot, guild.id):
        fresh = {int(row["id"]) for row in await waits.waiting(bot.db, guild.id, member.id)}
        rows = [row for row in rows if int(row["id"]) in fresh]
        held, taking, stuck = [], [], []
        for row in rows:
            if await rm.held_elsewhere(bot, guild.id, member.id, row["role_id"]):
                held.append(row)
            elif rm.removable(guild, row["role_id"]):
                taking.append(row)
            else:
                stuck.append(row)
        message = None
        if held or taking:
            message = await post_removal(bot, guild, target, member, held + taking, held, stuck)
            if message is None:
                found["failures"] += 1
                return found
        refused = bool(taking) and not await rm.change_roles(
            bot, member, guild, set(), {int(row["role_id"]) for row in taking}, REMOVE_REASON
        )
        if refused:
            stuck, taking = stuck + taking, []
        gone = set(await waits.mark_removed(bot.db, [row["id"] for row in held + taking]))
        if taking:
            await timed.close_member_roles(
                bot.db, guild.id, member.id, [row["role_id"] for row in taking], grants.EXPIRED
            )
    ended = [row for row in held + taking if int(row["id"]) in gone]
    failures = await waits.failed_removal(bot.db, [row["id"] for row in stuck]) if stuck else {}
    if stuck:
        found["failures"] += 1
        await log_action(
            bot,
            guild,
            "role_menu.wait_remove_failed",
            target=member,
            details=details | {"roles": [int(row["role_id"]) for row in stuck]},
        )
    if message is not None:
        if ended:
            await waits.set_notice(bot.db, [row["id"] for row in ended], target.id, message.id)
        if refused or not ended:
            await redraw_removal(bot, guild, message, member, ended, held, stuck)
    elif any(failures.get(int(row["id"])) == 1 for row in stuck):
        await post_removal(bot, guild, target, member, [], [], stuck)
    if not ended:
        return found
    found["removed"] += len(ended)
    await log_action(
        bot,
        guild,
        "role_menu.wait_removed",
        target=member,
        details=details
        | {
            "taken": [int(row["role_id"]) for row in taking],
            "stayed_on": [int(row["role_id"]) for row in held],
            "removed_ids": [int(row["id"]) for row in ended],
        },
    )
    await settle_posts(
        bot,
        guild,
        [row["prompt_id"] for row in ended if row["prompt_id"] is not None],
        "rolemenu_wait_post_removed_text",
        date=stamp(waits.iso(waits.now())),
    )
    return found


async def redraw_removal(
    bot: Any, guild: Any, message: Any, member: Any, ended: Any, held: Any, stuck: Any
) -> None:
    """The notice says what really happened once Discord refused a removal it announced."""
    view = revert_view(bot, guild.id, int(ended[0]["id"])) if ended else None
    try:
        await message.edit(
            content=removal_text(bot, guild, member, ended, held, stuck)[: rm.NOTICE_LIMIT],
            view=view,
            allowed_mentions=discord.AllowedMentions.none(),
        )
    except (*NETWORK_ERRORS, LookupError, AttributeError) as exc:
        log.info("timed roles: could not redraw the removal notice for %s: %s", member.id, exc)


def removal_text(bot: Any, guild: Any, member: Any, ended: Any, held: Any, stuck: Any) -> str:
    lines = []
    if ended:
        lead = ended[0]
        lines.append(
            word(
                bot,
                guild.id,
                "rolemenu_wait_removed_text",
                member=member_of(member.id),
                roles=roles_of([row["role_id"] for row in ended]),
                date=stamp(lead["until"]),
                who=staff_of(lead["assigner_id"]),
            )
        )
    ending = {int(row["id"]) for row in ended}
    kept = [row for row in held if int(row["id"]) in ending]
    if kept:
        lines.append(
            word(
                bot,
                guild.id,
                "rolemenu_wait_stays_on_text",
                roles=roles_of([row["role_id"] for row in kept]),
                member=member_of(member.id),
            )
        )
    if stuck:
        lines.append(
            word(
                bot,
                guild.id,
                "rolemenu_wait_stuck_line",
                roles=roles_of([row["role_id"] for row in stuck]),
                member=member_of(member.id),
            )
        )
    return "\n".join(lines)


async def post_removal(
    bot: Any, guild: Any, target: Any, member: Any, ended: Any, held: Any, stuck: Any
) -> Any:
    role_id = bot.store.get(guild.id, ROLEMENU_WAIT_PING_ROLE_KEY)
    text = removal_text(bot, guild, member, ended, held, stuck)
    content = f"<@&{role_id}> {text}" if role_id else text
    view = revert_view(bot, guild.id, int(ended[0]["id"])) if ended else None
    try:
        return await target.send(
            content[: rm.NOTICE_LIMIT], view=view, allowed_mentions=rm.ping_mentions(role_id)
        )
    except Exception as exc:
        await log_action(
            bot,
            guild,
            "role_menu.wait_notice_failed",
            target=member,
            details={
                "user": int(member.id),
                "wait_ids": [int(row["id"]) for row in ended],
                "reason": f"{type(exc).__name__}: {exc}"[:300],
            },
        )
        return None


def revert_view(bot: Any, guild_id: int, wait_id: int) -> discord.ui.View:
    view = discord.ui.View(timeout=None)
    view.add_item(
        WaitRevert(
            wait_id,
            discord.ui.Button(
                custom_id=waits.revert_id(wait_id),
                label=word(bot, guild_id, "rolemenu_wait_revert_button", rm.BUTTON_MAX),
                style=discord.ButtonStyle.primary,
            ),
        )
    )
    return view


async def revert(
    bot: Any, guild: Any, actor: Any, wait_id: int, *, via: str = VIA_DISCORD
) -> tuple[bool, str]:
    """Revert, one press: the roles go back and wait again for the revert-days key, from now."""
    lead = await waits.get(bot.db, wait_id)
    if lead is None or int(lead["guild_id"]) != guild.id:
        return False, word(bot, guild.id, "rolemenu_wait_revert_done_said")
    rows = await waits.notice_rows(bot.db, lead)
    if not rows:
        return False, word(bot, guild.id, "rolemenu_wait_revert_done_said")
    user_id = int(lead["user_id"])
    role_ids = [int(row["role_id"]) for row in rows]
    member = guild.get_member(user_id)
    if member is None:
        return False, word(
            bot, guild.id, "rolemenu_wait_revert_left_said", member=member_of(user_id)
        )
    until = waits.now() + timedelta(days=revert_days(bot, guild.id))
    async with rm.guild_lock(bot, guild.id):
        worn = {int(r.id) for r in member.roles}
        adding = {one for one in role_ids if one not in worn}
        reason = REVERT_REASON.format(actor=actor)
        if adding and not await rm.change_roles(bot, member, guild, adding, set(), reason):
            await log_action(
                bot,
                guild,
                kind_via("role_menu.wait_revert_failed", via),
                actor=actor,
                target=member,
                details={"user": user_id, "roles": sorted(adding), "via": via},
            )
            return False, word(
                bot,
                guild.id,
                "rolemenu_wait_revert_refused_said",
                roles=roles_of(sorted(adding)),
                member=member_of(user_id),
            )
        moved = await waits.wait_again(
            bot.db, [row["id"] for row in rows], until, rm.actor_id(actor)
        )
    if not moved:
        return False, word(bot, guild.id, "rolemenu_wait_revert_done_said")
    back = [int(row["role_id"]) for row in rows if int(row["id"]) in moved]
    elsewhere = [int(row["role_id"]) for row in rows if int(row["id"]) not in moved]
    await log_action(
        bot,
        guild,
        kind_via("role_menu.wait_reverted", via),
        actor=actor,
        target=member,
        details={
            "user": user_id,
            "roles": back,
            "put_back": sorted(adding),
            "already_waiting": elsewhere,
            "until": waits.iso(until),
            "wait_ids": moved,
            "via": via,
        },
    )
    await edit_notice(bot, guild, lead, back, actor, until)
    said = [
        word(
            bot,
            guild.id,
            "rolemenu_wait_reverted_said",
            roles=roles_of(back),
            member=member_of(user_id),
            date=stamp(waits.iso(until)),
        )
    ]
    if elsewhere:
        said.append(
            word(
                bot,
                guild.id,
                "rolemenu_wait_revert_taken_said",
                member=member_of(user_id),
                roles=roles_of(elsewhere),
            )
        )
    return True, " ".join(said)


async def edit_notice(
    bot: Any, guild: Any, lead: Any, role_ids: Any, actor: Any, until: Any
) -> None:
    channel = bot.get_channel(lead["notice_channel_id"]) if lead["notice_channel_id"] else None
    if channel is None or not lead["notice_message_id"]:
        return
    text = word(
        bot,
        guild.id,
        "rolemenu_wait_reverted_text",
        member=member_of(lead["user_id"]),
        roles=roles_of(role_ids),
        staff=staff_of(rm.actor_id(actor)),
        date=stamp(waits.iso(until)),
    )
    try:
        message = channel.get_partial_message(int(lead["notice_message_id"]))
        await message.edit(
            content=text[: rm.NOTICE_LIMIT],
            view=None,
            allowed_mentions=discord.AllowedMentions.none(),
        )
    except (*NETWORK_ERRORS, LookupError, AttributeError) as exc:
        log.info("timed roles: could not edit removal notice %s: %s", lead["id"], exc)


# --- a new event while people wait: is it for any of these? -------------------------------------


async def ask_about_new_event(bot: Any, guild: Any, menu: Any) -> int | None:
    """One post in the by-hand channel naming who waits, pinging their assigners; never raises."""
    try:
        entries = await waiting_entries(bot, guild)
        if not entries or menu is None or rm.menu_value(menu, "ended_at"):
            return None
        target, where = rm.card_target(bot, rm.by_hand_channel(bot, guild))
        details = {
            "menu": menu["name"],
            "menu_id": int(menu["id"]),
            "users": [one["user_id"] for one in entries],
        }
        if target is None:
            await log_action(
                bot, guild, "role_menu.wait_event_ask_failed", details=details | {"reason": where}
            )
            return None
        assigners = [one["assigner_id"] for one in entries if one["assigner_id"]]
        message = await target.send(
            new_event_text(bot, guild, menu, entries),
            view=new_event_view(bot, guild, menu, entries),
            allowed_mentions=mentions(assigners),
        )
    except Exception as exc:
        log.warning("timed roles: could not ask about new event: %s", exc)
        try:
            await log_action(
                bot,
                guild,
                "role_menu.wait_event_ask_failed",
                details={
                    "menu_id": int(menu["id"]),
                    "reason": f"{type(exc).__name__}: {exc}"[:300],
                },
            )
        except Exception:
            log.exception("timed roles: could not log the failed new-event post")
        return None
    await log_action(
        bot,
        guild,
        "role_menu.wait_event_asked",
        details=details | {"channel_id": int(target.id), "where": where},
    )
    return int(message.id)


def new_event_text(bot: Any, guild: Any, menu: Any, entries: Any) -> str:
    who = " ".join(
        dict.fromkeys(staff_of(one["assigner_id"]) for one in entries if one["assigner_id"])
    )
    lines = [word(bot, guild.id, "rolemenu_wait_event_text", event=rm.event_name(menu), who=who)]
    lines += [entry_line(bot, guild, one) for one in entries]
    return "\n".join(lines)[: rm.NOTICE_LIMIT]


def new_event_view(bot: Any, guild: Any, menu: Any, entries: Any) -> discord.ui.View | None:
    shown = list(entries)[: rm.OPTIONS_MAX]
    if not shown:
        return None
    view = discord.ui.View(timeout=None)
    view.add_item(
        NewEventPick(
            int(menu["id"]),
            discord.ui.Select(
                custom_id=waits.event_id(menu["id"]),
                placeholder=capped_placeholder(
                    len(shown),
                    len(list(entries)),
                    pick=word(bot, guild.id, "rolemenu_wait_event_pick"),
                    capped=word(
                        bot, guild.id, "rolemenu_wait_capped", shown="{shown}", total="{total}"
                    ),
                )[: rm.SELECT_PLACEHOLDER_MAX],
                min_values=1,
                max_values=len(shown),
                options=[
                    discord.SelectOption(
                        label=rm.who_is(guild, one["user_id"])[: rm.LABEL_MAX],
                        value=str(one["user_id"]),
                    )
                    for one in shown
                ],
            ),
        )
    )
    return view


async def attach_many(
    bot: Any, guild: Any, actor: Any, user_ids: Any, menu: Any, *, via: str = VIA_DISCORD
) -> tuple[list[int], list[str]]:
    done: list[int] = []
    said: list[str] = []
    for user_id in dict.fromkeys(int(one) for one in user_ids or ()):
        ok, line = await attach_entry(bot, guild, actor, user_id, menu, via=via)
        if ok:
            done.append(user_id)
        else:
            said.append(line)
    return done, said


# --- the controls, restart-safe ------------------------------------------------------------------


async def staff_here(interaction: discord.Interaction) -> bool:
    if interaction.guild is None:
        await answer(interaction, GUILD_ONLY)
        return False
    return await still_staff(interaction) and await db_up(interaction)


async def open_entry_card(interaction: discord.Interaction, user_id: int) -> None:
    """The entry card: an event · New event… · Change the date… · Take it off now."""
    if not await staff_here(interaction):
        return
    bot, guild = interaction.client, interaction.guild
    entry = await entry_of(bot, guild, user_id)
    if entry is None:
        await answer(
            interaction, word(bot, guild.id, "rolemenu_wait_gone_said", member=member_of(user_id))
        )
        return
    events = await timed.open_events(bot.db, guild.id)
    lines = [entry_line(bot, guild, entry)]
    if not events:
        lines.append(word(bot, guild.id, "rolemenu_by_hand_no_events_text"))
    await interaction.response.send_message(
        "\n".join(lines)[: rm.NOTICE_LIMIT],
        view=entry_view(bot, guild.id, user_id, events),
        ephemeral=True,
        allowed_mentions=discord.AllowedMentions.none(),
    )


def picked(item: Any, interaction: discord.Interaction) -> list[str]:
    values = list(getattr(item, "values", None) or ())
    if not values:
        values = list((getattr(interaction, "data", None) or {}).get("values") or ())
    return values


async def open_event_or_gone(interaction: discord.Interaction, menu_id: Any) -> Any:
    bot, guild = interaction.client, interaction.guild
    menu = await rm.get_menu_by_id(bot.db, int(menu_id)) if str(menu_id).isdigit() else None
    if menu is None or int(menu["guild_id"]) != guild.id or rm.menu_value(menu, "ended_at"):
        await answer(interaction, word(bot, guild.id, "rolemenu_by_hand_gone_said"))
        return None
    return menu


class ByHandLater(
    SafeDynamicItem, discord.ui.DynamicItem[discord.ui.Button], template=waits.LATER_TEMPLATE
):
    """Pick later… on a by-hand post: a rough end date, then the role waits for an event."""

    def __init__(self, prompt_id: int, button: Any = None) -> None:
        self.prompt_id = int(prompt_id)
        super().__init__(
            button or discord.ui.Button(custom_id=waits.later_id(prompt_id), label="?")
        )

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: Any, match: re.Match):
        return cls(int(match["prompt_id"]), item)

    async def on_click(self, interaction: discord.Interaction) -> None:
        prompt = await rm.by_hand_target(interaction, self.prompt_id)
        if prompt is None:
            return
        await interaction.response.send_modal(
            WaitDateModal(
                interaction.client,
                interaction.guild.id,
                "rolemenu_pick_later_title",
                prompt_id=self.prompt_id,
            )
        )


class WaitDateModal(AnswersErrors, discord.ui.Modal):
    typed = discord.ui.TextInput(label="Date", max_length=rm.DATE_TYPED_MAX, required=True)

    def __init__(
        self, bot: Any, guild_id: int, title_key: str, *, prompt_id: Any = None, user_id: Any = None
    ) -> None:
        super().__init__(title=word(bot, guild_id, title_key, rm.MODAL_WORD_MAX))
        self.prompt_id = prompt_id
        self.user_id = user_id
        self.typed.label = word(bot, guild_id, "rolemenu_wait_date_label", rm.MODAL_WORD_MAX)
        self.typed.placeholder = word(
            bot, guild_id, "rolemenu_date_placeholder", rm.PLACEHOLDER_MAX
        )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not await staff_here(interaction):
            return
        bot, guild = interaction.client, interaction.guild
        refusal, when = date_refusal(bot, guild.id, str(self.typed))
        if refusal:
            await answer(interaction, refusal)
            return
        if self.prompt_id is not None:
            prompt = await rm.by_hand_target(interaction, int(self.prompt_id))
            if prompt is None:
                return
            await interaction.response.defer(ephemeral=True)
            _, said = await put_to_waiting(bot, guild, interaction.user, prompt, when)
        else:
            await interaction.response.defer(ephemeral=True)
            _, said = await change_date(bot, guild, interaction.user, int(self.user_id), when)
        await answer(interaction, said)


class WaitEventModal(AnswersErrors, discord.ui.Modal):
    name = discord.ui.TextInput(label="Name", max_length=rm.TITLE_MAX)
    typed = discord.ui.TextInput(label="Date", max_length=rm.DATE_TYPED_MAX)

    def __init__(self, bot: Any, guild_id: int, user_id: int) -> None:
        super().__init__(title=word(bot, guild_id, "rolemenu_new_event_title", rm.MODAL_WORD_MAX))
        self.user_id = int(user_id)
        self.name.label = word(bot, guild_id, "rolemenu_event_name_label", rm.MODAL_WORD_MAX)
        self.typed.label = word(bot, guild_id, "rolemenu_date_label", rm.MODAL_WORD_MAX)
        self.typed.placeholder = word(
            bot, guild_id, "rolemenu_date_placeholder", rm.PLACEHOLDER_MAX
        )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not await staff_here(interaction):
            return
        bot, guild = interaction.client, interaction.guild
        refusal, when = rm.typed_refusal(bot, guild.id, str(self.typed))
        if refusal:
            await answer(interaction, refusal)
            return
        if not await rm.guarded(interaction):
            return
        await interaction.response.defer(ephemeral=True)
        try:
            menu = await rm.make_event(
                bot, guild, interaction.user, str(self.name), ends_at=when, ask_waiting=False
            )
        except rm.MenuLimitError as exc:
            await answer(interaction, str(exc))
            return
        _, said = await attach_entry(bot, guild, interaction.user, self.user_id, menu)
        await answer(interaction, said)
        await ask_about_new_event(bot, guild, menu)


class TakeOffConfirm(AnswersErrors, discord.ui.View):
    def __init__(self, bot: Any, guild_id: int, user_id: int) -> None:
        super().__init__(timeout=CONFIRM_SECONDS)
        self.user_id = int(user_id)
        yes = discord.ui.Button(
            label=word(bot, guild_id, "rolemenu_wait_take_off_yes", rm.BUTTON_MAX),
            style=discord.ButtonStyle.danger,
        )
        keep = discord.ui.Button(
            label=word(bot, guild_id, "rolemenu_wait_keep_button", rm.BUTTON_MAX),
            style=discord.ButtonStyle.secondary,
        )
        yes.callback = self.take_it_off
        keep.callback = self.keep_it
        self.add_item(yes)
        self.add_item(keep)

    async def take_it_off(self, interaction: discord.Interaction) -> None:
        if not await staff_here(interaction) or not await rm.guarded(interaction):
            return
        await interaction.response.defer(ephemeral=True)
        _, said = await take_off_now(
            interaction.client, interaction.guild, interaction.user, self.user_id
        )
        self.stop()
        await answer(interaction, said)

    async def keep_it(self, interaction: discord.Interaction) -> None:
        self.stop()
        await interaction.response.defer(ephemeral=True)


class WaitMove(
    SafeDynamicItem, discord.ui.DynamicItem[discord.ui.Button], template=waits.MOVE_TEMPLATE
):
    """New event… · Change the date… · Take it off now, for one member waiting for an event."""

    def __init__(self, user_id: int, move: str, button: Any = None) -> None:
        self.user_id = int(user_id)
        self.move = move
        super().__init__(
            button or discord.ui.Button(custom_id=waits.move_id(user_id, move), label="?")
        )

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: Any, match: re.Match):
        return cls(int(match["user_id"]), match["move"], item)

    async def on_click(self, interaction: discord.Interaction) -> None:
        if not await staff_here(interaction):
            return
        bot, guild = interaction.client, interaction.guild
        entry = await entry_of(bot, guild, self.user_id)
        if entry is None:
            await answer(
                interaction,
                word(bot, guild.id, "rolemenu_wait_gone_said", member=member_of(self.user_id)),
            )
            return
        if self.move == waits.DATE:
            await interaction.response.send_modal(
                WaitDateModal(
                    bot, guild.id, "rolemenu_wait_change_date_title", user_id=self.user_id
                )
            )
            return
        if self.move == waits.NEW:
            await interaction.response.send_modal(WaitEventModal(bot, guild.id, self.user_id))
            return
        await interaction.response.send_message(
            take_off_question(bot, guild.id, entry),
            view=TakeOffConfirm(bot, guild.id, self.user_id),
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )


class WaitEventPick(
    SafeDynamicItem, discord.ui.DynamicItem[discord.ui.Select], template=waits.PICK_TEMPLATE
):
    """The entry card's event picker: the member's waiting roles are attached to it."""

    def __init__(self, user_id: int, select: Any = None) -> None:
        self.user_id = int(user_id)
        super().__init__(
            select
            or discord.ui.Select(
                custom_id=waits.pick_id(user_id),
                options=[discord.SelectOption(label="?", value="0")],
            )
        )

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: Any, match: re.Match):
        return cls(int(match["user_id"]), item)

    async def on_click(self, interaction: discord.Interaction) -> None:
        if not await staff_here(interaction) or not await rm.guarded(interaction):
            return
        values = picked(self.item, interaction)
        await interaction.response.defer(ephemeral=True)
        menu = await open_event_or_gone(interaction, values[0] if values else None)
        if menu is None:
            return
        _, said = await attach_entry(
            interaction.client, interaction.guild, interaction.user, self.user_id, menu
        )
        await answer(interaction, said)


class ReminderPick(
    SafeDynamicItem, discord.ui.DynamicItem[discord.ui.Select], template=waits.REMINDER_TEMPLATE
):
    """The reminder's picker: one entry's card, answered to the staff member alone."""

    def __init__(self, assigner_id: int, select: Any = None) -> None:
        self.assigner_id = int(assigner_id or 0)
        super().__init__(
            select
            or discord.ui.Select(
                custom_id=waits.reminder_id(assigner_id),
                options=[discord.SelectOption(label="?", value="0")],
            )
        )

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: Any, match: re.Match):
        return cls(int(match["assigner_id"]), item)

    async def on_click(self, interaction: discord.Interaction) -> None:
        values = picked(self.item, interaction)
        if not values or not str(values[0]).isdigit():
            await answer(
                interaction,
                word(interaction.client, interaction.guild.id, "rolemenu_by_hand_gone_said"),
            )
            return
        await open_entry_card(interaction, int(values[0]))


class NewEventPick(
    SafeDynamicItem, discord.ui.DynamicItem[discord.ui.Select], template=waits.EVENT_TEMPLATE
):
    """Is it for any of these?: the picked people are attached to the new event."""

    def __init__(self, menu_id: int, select: Any = None) -> None:
        self.menu_id = int(menu_id)
        super().__init__(
            select
            or discord.ui.Select(
                custom_id=waits.event_id(menu_id),
                options=[discord.SelectOption(label="?", value="0")],
            )
        )

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: Any, match: re.Match):
        return cls(int(match["menu_id"]), item)

    async def on_click(self, interaction: discord.Interaction) -> None:
        if not await staff_here(interaction) or not await rm.guarded(interaction):
            return
        values = [int(one) for one in picked(self.item, interaction) if str(one).isdigit()]
        await interaction.response.defer(ephemeral=True)
        menu = await open_event_or_gone(interaction, self.menu_id)
        if menu is None:
            return
        bot, guild = interaction.client, interaction.guild
        done, refused = await attach_many(bot, guild, interaction.user, values, menu)
        if done:
            await grow_event_post(interaction, menu, done)
            refused.insert(
                0,
                word(
                    bot,
                    guild.id,
                    "rolemenu_wait_attached_said",
                    members=", ".join(member_of(one) for one in done),
                    event=rm.event_name(menu),
                ),
            )
        await answer(interaction, " ".join(refused)[: rm.NOTICE_LIMIT])


async def grow_event_post(interaction: discord.Interaction, menu: Any, done: Any) -> None:
    """The post gains who was attached by whom; the picker keeps only who still waits."""
    bot, guild = interaction.client, interaction.guild
    message = getattr(interaction, "message", None)
    if message is None:
        return
    line = word(
        bot,
        guild.id,
        "rolemenu_wait_attached_line",
        staff=staff_of(rm.actor_id(interaction.user)),
        members=", ".join(member_of(one) for one in done),
        event=rm.event_name(menu),
    )
    content = f"{getattr(message, 'content', '') or ''}\n{line}".strip()
    entries = await waiting_entries(bot, guild)
    try:
        await message.edit(
            content=content[: rm.NOTICE_LIMIT],
            view=new_event_view(bot, guild, menu, entries),
            allowed_mentions=discord.AllowedMentions.none(),
        )
    except (*NETWORK_ERRORS, LookupError, AttributeError) as exc:
        log.info("timed roles: could not edit the new-event post of %s: %s", menu["id"], exc)


class WaitRevert(
    SafeDynamicItem, discord.ui.DynamicItem[discord.ui.Button], template=waits.REVERT_TEMPLATE
):
    """Revert on a removal notice: one press puts the roles back and the wait starts over."""

    def __init__(self, wait_id: int, button: Any = None) -> None:
        self.wait_id = int(wait_id)
        super().__init__(button or discord.ui.Button(custom_id=waits.revert_id(wait_id), label="?"))

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: Any, match: re.Match):
        return cls(int(match["wait_id"]), item)

    async def on_click(self, interaction: discord.Interaction) -> None:
        if not await staff_here(interaction) or not await rm.guarded(interaction):
            return
        await interaction.response.defer(ephemeral=True)
        _, said = await revert(
            interaction.client, interaction.guild, interaction.user, self.wait_id
        )
        await answer(interaction, said)


DYNAMIC_ITEMS = (ByHandLater, WaitMove, WaitEventPick, ReminderPick, NewEventPick, WaitRevert)

__all__ = [
    "DYNAMIC_ITEMS",
    "ByHandLater",
    "NewEventPick",
    "ReminderPick",
    "TakeOffConfirm",
    "WaitDateModal",
    "WaitEventModal",
    "WaitEventPick",
    "WaitMove",
    "WaitRevert",
    "ask_about_new_event",
    "attach_entry",
    "attach_many",
    "change_date",
    "date_refusal",
    "too_far",
    "entry_line",
    "entry_of",
    "open_entry_card",
    "put_to_waiting",
    "remove_member",
    "revert",
    "take_off_now",
    "take_off_question",
    "wait_came_off",
    "wait_left",
    "waiting_entries",
    "waiting_pass",
]
