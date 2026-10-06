from __future__ import annotations

import re
from typing import Any

import discord

from ... import marathon as mt
from ... import marathon_announce as ma
from ... import marathon_hosts as mh
from ... import marathon_people as mp
from ... import spotlight as spot
from ...actionlog import log_action
from ...command_errors import AnswersErrors, SafeDynamicItem
from ...golive import now_iso, parse_ts
from ...logkinds import VIA_DISCORD, kind_via
from ...panels import Outcome, Panel, answer, clamped, opened, refusal, retire, still_staff
from ...settings_store import (
    DB_UNAVAILABLE,
    DEFAULT_TIMEZONE_KEY,
    MARATHON_DEFAULTS,
    MARATHON_PUBLIC_BUTTON_OPT_IN_KEY,
    MARATHON_PUBLIC_BUTTON_OPT_OUT_KEY,
    MARATHON_SPOTLIGHT_HOST_NOTE_KEY,
    MARATHON_SPOTLIGHT_LEAD_KEY,
    MARATHON_SPOTLIGHT_NOTE_KEY,
    MARATHON_SPOTLIGHT_SLACK_KEY,
)
from ...timezones import unix
from .marathon import (
    cog_of,
    get_marathon,
    links_of,
    minutes_for,
    now_for,
    pair_runner,
    pairing_by_id,
    pairings_of,
    runs_of,
    set_pairing_login,
    unpair_runner,
    usernames_of,
    words_for,
)
from .spotlight import channel_by_id, channels_for, forget_spotlight, spotlight_channel

PEOPLE_TEMPLATE = r"marathon:people:(?P<marathon_id>[0-9]+)"
NO_SUCH_PERSON_CODE = "no_such_person"
NO_LOGIN_CODE = "no_login"
BAD_LOGIN_CODE = "bad_login"
ALREADY_CODE = "already_on_golive"
RUNS_OVER_CODE = "runs_over"
NOT_SPOTLIT_CODE = "not_spotlit"
NO_SUCH_RUN_CODE = "no_such_run"
BAF_LIMIT = 15
PEOPLE_VIEW = "people"
SPOTLIGHT = "spotlight"
UNSPOTLIGHT = "unspotlight"
UNLINK = "unlink"
LINK_NEAR = "link_near"
TWITCH = "twitch"
OPT_OUT = "opt_out"
OPT_IN = "opt_in"
RUN_ANSWER = "run_answer"
MENTION = "mention"
BACK = "back"
LABELS = {
    SPOTLIGHT: ("Spotlight", discord.ButtonStyle.primary),
    UNSPOTLIGHT: ("Stop spotlighting", discord.ButtonStyle.secondary),
    UNLINK: ("Unlink", discord.ButtonStyle.secondary),
    LINK_NEAR: ("Link @{username}", discord.ButtonStyle.primary),
    TWITCH: ("Twitch name…", discord.ButtonStyle.secondary),
    OPT_OUT: ("{label}", discord.ButtonStyle.secondary),
    OPT_IN: ("{label}", discord.ButtonStyle.primary),
    RUN_ANSWER: ("{label}", discord.ButtonStyle.secondary),
    MENTION: ("{label}", discord.ButtonStyle.secondary),
    BACK: ("Back", discord.ButtonStyle.secondary),
}
PEOPLE_BUTTON = "People…"
TWITCH_TITLE = "Their Twitch channel"
TWITCH_LABEL = "Twitch name (blank = the schedule's)"
TWITCH_HINT = "junior_sm or twitch.tv/junior_sm"


# --- the table --------------------------------------------------------------------------------


async def remembered_of(db: Any, marathon_id: int) -> dict[str, Any]:
    cur = await db.conn.execute(
        "SELECT * FROM marathon_spotlights WHERE marathon_id = ?", (int(marathon_id),)
    )
    return {str(row["login"]).lower(): row for row in await cur.fetchall()}


async def remember(
    db: Any, marathon_id: int, login: str, spotlight_id: int, run_id: Any, added_by: Any
) -> None:
    await db.conn.execute(
        "INSERT OR REPLACE INTO marathon_spotlights(marathon_id, login, spotlight_id, run_id, "
        "added_by, added_at) VALUES (?, ?, ?, ?, ?, ?)",
        (
            int(marathon_id),
            login,
            int(spotlight_id),
            int(run_id) if run_id not in (None, "") else None,
            added_by,
            now_iso(),
        ),
    )
    await db.conn.commit()


async def forget(db: Any, marathon_id: int, login: str) -> None:
    await db.conn.execute(
        "DELETE FROM marathon_spotlights WHERE marathon_id = ? AND login = ?",
        (int(marathon_id), login),
    )
    await db.conn.commit()


# --- who is on the schedule --------------------------------------------------------------------


async def people_state(bot: Any, guild: Any, marathon: Any) -> dict[str, Any]:
    """Every person on the schedule with how they matched, their Go-live row and a near miss."""
    runs = await runs_of(bot.db, marathon["id"])
    entries = mp.group_people(runs)
    pairings = await pairings_of(bot.db, guild.id)
    links = await links_of(bot.db)
    usernames = usernames_of(guild)
    remembered = await remembered_of(bot.db, marathon["id"])
    channels = {
        str(row["twitch_login"]).lower(): row for row in await channels_for(bot.db, guild.id)
    }
    for entry in entries:
        how, pairing_id = mp.matched_by(entry, pairings, links, marathon_id=marathon["id"])
        login = str(entry.get("login") or "").lower()
        channel = channels.get(login) if login else None
        mine = remembered.get(login) if login else None
        spotlit = (
            mine is not None
            and channel is not None
            and int(channel["id"]) == int(mine["spotlight_id"])
        )
        near = mp.looks_like(entry, usernames)
        entry.update(
            matched_by=how,
            pairing_id=pairing_id,
            channel_id=channel["id"] if channel is not None else None,
            spotlight_id=channel["id"] if spotlit else None,
            spotlight_starts=channel["starts_at"] if spotlit else None,
            spotlight_until=channel["expires_at"] if spotlit else None,
            looks_like={"username": near[0], "user_id": near[1]} if near else None,
        )
    baf, others = mp.split_people(entries)
    return {"runs": runs, "entries": entries, "baf": baf, "others": others}


def zone_of(bot: Any, guild: Any) -> str:
    return str(bot.store.get(guild.id, DEFAULT_TIMEZONE_KEY) or "")


# --- Spotlight… and Stop spotlighting ----------------------------------------------------------


def spotlit_parts(entry: dict[str, Any], run_id: Any) -> list[Any]:
    if run_id in (None, ""):
        return list(entry.get("parts") or ())
    return [one["part"] for one in entry["runs"] if str(one["id"]) == str(run_id)]


async def spotlight_runner(
    bot: Any,
    guild: Any,
    actor: Any,
    marathon: Any,
    given: Any,
    *,
    run_id: Any = None,
    via: str = VIA_DISCORD,
) -> Outcome:
    """A channel-only spotlight row for one runner or host, through the path Go-live uses."""
    cog = cog_of(bot)
    async with cog.lock(marathon["id"]):
        state = await people_state(bot, guild, marathon)
        entry = mp.find_entry(state["entries"], given)
        if entry is None:
            said = mp.NO_SUCH_PERSON.format(given=str(given)[:40], marathon=marathon["name"])
            return refusal(said, NO_SUCH_PERSON_CODE, 404)
        name = entry["name"]
        if not entry.get("login"):
            return refusal(mp.NO_LOGIN.format(name=name), NO_LOGIN_CODE, 422)
        login = spot.clean_login(entry["login"])
        if login is None:
            return refusal(mp.BAD_LOGIN.format(login=entry["login"]), BAD_LOGIN_CODE, 422)
        if entry.get("channel_id"):
            return refusal(mp.ALREADY_ON_GOLIVE.format(login=login), ALREADY_CODE, 409)
        if run_id not in (None, "") and not any(
            str(one["id"]) == str(run_id) for one in entry["runs"]
        ):
            return refusal(mt.NO_SUCH_RUN.format(name=marathon["name"]), NO_SUCH_RUN_CODE, 404)
        starts, ends = mp.spotlight_span(
            entry["runs"],
            marathon,
            lead_hours=int(bot.store.get(guild.id, MARATHON_SPOTLIGHT_LEAD_KEY)),
            slack_hours=int(bot.store.get(guild.id, MARATHON_SPOTLIGHT_SLACK_KEY)),
            run_id=run_id or None,
        )
        now = now_for(bot)
        end_at = parse_ts(ends)
        if end_at is not None and end_at <= now:
            said = mp.RUNS_OVER.format(name=name, marathon=marathon["name"])
            return refusal(said, RUNS_OVER_CODE, 409)
        start_at = parse_ts(starts)
        hosting = mh.host_only(spotlit_parts(entry, run_id))
        note_key = MARATHON_SPOTLIGHT_HOST_NOTE_KEY if hosting else MARATHON_SPOTLIGHT_NOTE_KEY
        note = mt.render(
            bot.store.get(guild.id, note_key),
            str(MARATHON_DEFAULTS[note_key]),
            name=name,
            marathon=marathon["name"],
        ).text
        outcome, row = await spotlight_channel(
            bot,
            guild,
            actor,
            login,
            expires_at=ends if end_at is not None else False,
            starts_at=starts if start_at is not None and start_at > now else None,
            spotlight=True,
            announce=True,
            note=note[:200],
            via=via,
        )
        if outcome == "bad_login":
            return refusal(mp.BAD_LOGIN.format(login=login), BAD_LOGIN_CODE, 422)
        if outcome != "added" or row is None:
            return refusal(mp.ALREADY_ON_GOLIVE.format(login=login), ALREADY_CODE, 409)
        await remember(
            bot.db, marathon["id"], login, row["id"], run_id or None, getattr(actor, "id", actor)
        )
    await log_action(
        bot,
        guild,
        kind_via("marathon.runner_spotlit", via),
        actor=actor,
        target=entry.get("user_id"),
        details={
            "marathon_id": marathon["id"],
            "name": name,
            "login": login,
            "spotlight_id": row["id"],
            "run_id": int(run_id) if run_id not in (None, "") else None,
            "hosting": hosting,
            "starts_at": row["starts_at"],
            "expires_at": row["expires_at"],
            "via": via,
        },
    )
    said = mp.SPOTLIT.format(name=name, login=login, marathon=marathon["name"])
    return Outcome(True, said, value={"spotlight_id": row["id"], "login": login})


async def unspotlight_runner(
    bot: Any, guild: Any, actor: Any, marathon: Any, given: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    """Stop spotlighting removes the channel row exactly as the Go-live page does."""
    cog = cog_of(bot)
    async with cog.lock(marathon["id"]):
        state = await people_state(bot, guild, marathon)
        entry = mp.find_entry(state["entries"], given)
        remembered = await remembered_of(bot.db, marathon["id"])
        login = str((entry or {}).get("login") or given or "").strip().lower()
        sheet = str((entry or {}).get("sheet_login") or "").strip().lower()
        if login not in remembered and sheet in remembered:
            login = sheet
        mine = remembered.get(login)
        name = entry["name"] if entry is not None else login
        if mine is None:
            said = mp.NOT_SPOTLIT.format(name=name, marathon=marathon["name"])
            return refusal(said, NOT_SPOTLIT_CODE, 404)
        channel = await channel_by_id(bot.db, int(mine["spotlight_id"]))
        gone = channel is None or str(channel["twitch_login"]).lower() != login
        if not gone:
            await forget_spotlight(bot, guild, actor, int(mine["spotlight_id"]), via=via)
        await forget(bot.db, marathon["id"], login)
    await log_action(
        bot,
        guild,
        kind_via("marathon.runner_unspotlit", via),
        actor=actor,
        target=(entry or {}).get("user_id"),
        details={
            "marathon_id": marathon["id"],
            "name": name,
            "login": login,
            "spotlight_id": int(mine["spotlight_id"]),
            "row_was_gone": gone,
            "via": via,
        },
    )
    if gone:
        return Outcome(True, mp.UNSPOTLIT_GONE.format(login=login, marathon=marathon["name"]))
    return Outcome(True, mp.UNSPOTLIT.format(name=name, login=login))


# --- /event ▸ Marathons… ▸ People… -------------------------------------------------------------


class PeoplePanel(Panel):
    def __init__(self, minutes: int, marathon_id: Any, *, staff: bool) -> None:
        super().__init__(minutes, footer=mt.PANEL_TIMEOUT_FOOTER, again=reopen)
        self.where = PEOPLE_VIEW
        self.marathon_id = marathon_id
        self.staff = staff
        self.day: str | None = None
        self.run_id: Any = None
        self.person: str | None = None


def part_words(bot: Any, guild: Any, parts: list[Any]) -> str:
    return mh.part_tag(parts, words_for(bot, guild.id))


def run_chip(one: dict[str, Any]) -> str:
    if one["state"] == mt.LIVE:
        return mp.PEOPLE_RUN_LIVE.format(game=one["game"])
    if one["state"] == mt.DONE:
        return mp.PEOPLE_RUN_DONE.format(game=one["game"])
    at = parse_ts(one["scheduled_at"])
    return mp.PEOPLE_RUN.format(unix=unix(at) if at is not None else 0, game=one["game"])


def twitch_of(entry: dict[str, Any]) -> str:
    return f"twitch.tv/{entry['login']}" if entry.get("login") else mp.NO_TWITCH


def spotlight_words(entry: dict[str, Any]) -> str:
    if entry.get("spotlight_id"):
        until = parse_ts(entry.get("spotlight_until"))
        return mp.PEOPLE_SPOTLIT.format(unix=unix(until)) if until else mp.PEOPLE_SPOTLIT_OPEN
    return mp.PEOPLE_ON_GOLIVE if entry.get("channel_id") else ""


def baf_lines(bot: Any, guild: Any, baf: list[dict[str, Any]]) -> list[str]:
    """Who from BaF is on, and when — the whole answer a member gets."""
    if not baf:
        return [mp.PEOPLE_NOBODY]
    lines = []
    for entry in baf[:BAF_LIMIT]:
        line = mp.PEOPLE_LINE.format(
            who=f"<@{int(entry['user_id'])}>",
            twitch=twitch_of(entry),
            part=part_words(bot, guild, entry["parts"]),
            runs=", ".join(run_chip(one) for one in entry["runs"]),
        )
        extra = spotlight_words(entry)
        lines.append(f"{line} · {extra}" if extra else line)
    if len(baf) > BAF_LIMIT:
        lines.append(mp.PEOPLE_MORE.format(count=len(baf) - BAF_LIMIT, BAF=mp.BAF))
    return lines


def person_line(bot: Any, guild: Any, entry: Any, person: dict[str, Any]) -> str:
    who = f"<@{int(person['user_id'])}>" if person.get("user_id") else f"**{person.get('name')}**"
    how = mp.MATCHED_WORDS.get((entry or {}).get("matched_by") or "", "")
    near = (entry or {}).get("looks_like")
    if not person.get("user_id") and near:
        how = mp.SLOT_LOOKS_LIKE.format(username=near["username"])
    extra = spotlight_words(entry or {})
    parts = (entry or {}).get("parts") if person.get("user_id") else None
    line = mp.SLOT_PERSON.format(
        who=who,
        part=part_words(bot, guild, parts or [person.get("part")]),
        baf=mp.BAF_MARK if person.get("user_id") else "",
        twitch=twitch_of(person),
        how=how or "—",
    )
    return f"{line} · {extra}" if extra else line


async def build_people(
    bot: Any,
    guild: Any,
    actor: Any,
    marathon_id: Any,
    *,
    day: Any = None,
    run_id: Any = None,
    person: Any = None,
) -> tuple[Any, Any]:
    """Members read the BaF block and nothing more; staff pick a day, a slot, then a person."""
    marathon = await get_marathon(bot.db, guild.id, marathon_id)
    if marathon is None:
        return (None, None)
    staff = bool(bot.store.is_staff(actor))
    state = await people_state(bot, guild, marathon)
    view = PeoplePanel(minutes_for(bot, guild.id), marathon["id"], staff=staff)
    lines = [mp.PEOPLE_BAF, *baf_lines(bot, guild, state["baf"])]
    if not staff:
        view.add_item(PeopleMove(BACK))
        return (discord.Embed(title=marathon["name"], description=clamped(lines)), view)
    zone = zone_of(bot, guild)
    days = mp.days_of(state["runs"], zone, now_for(bot))
    run = next((one for one in state["runs"] if str(one["id"]) == str(run_id)), None)
    if run is not None:
        return slot_card(bot, guild, marathon, state, run, view, person, zone)
    wanted = next((one for one in days if one.key == day), None)
    view.day = wanted.key if wanted is not None else None
    lines += ["", mp.PEOPLE_SCHEDULE]
    if days:
        view.add_item(DayPick(days[: mp.SELECT_CAP], view.day))
    if wanted is not None:
        if len(wanted.runs) > mp.SELECT_CAP:
            lines.append(
                mp.SLOT_CAP_NOTE.format(cap=mp.SELECT_CAP, count=len(wanted.runs), day=wanted.label)
            )
        view.add_item(SlotPick(wanted.runs[: mp.SELECT_CAP], zone))
    view.add_item(PeopleMove(BACK))
    return (discord.Embed(title=marathon["name"], description=clamped(lines)), view)


def slot_card(
    bot: Any,
    guild: Any,
    marathon: Any,
    state: dict[str, Any],
    run: Any,
    view: PeoplePanel,
    person: Any,
    zone: str,
) -> tuple[Any, Any]:
    view.run_id = run["id"]
    view.day = mp.days_of([run], zone, now_for(bot))[0].key if run["scheduled_at"] else None
    people = mt.people_of(run)
    at = parse_ts(run["scheduled_at"])
    words = words_for(bot, guild.id)
    lines = [
        mp.SLOT_HEAD.format(
            game=run["game"],
            category=run["category"] or "",
            unix=unix(at) if at is not None else 0,
            state=words.get(mt.STATE_KEYS.get(str(run["state"]), ""), run["state"]),
        ),
        "",
    ]
    lines += [
        person_line(bot, guild, mp.entry_for(state["entries"], run["id"], one), one)
        for one in people
    ] or [mp.SLOT_NOBODY]
    if people:
        view.add_item(PersonPick(people, person))
    chosen = next((one for one in people if one.get("name") == person), None)
    if chosen is not None:
        view.person = chosen.get("name")
        entry = mp.entry_for(state["entries"], run["id"], chosen) or {}
        view.add_item(LinkPick())
        if entry.get("login") and not entry.get("channel_id"):
            view.add_item(PeopleMove(SPOTLIGHT))
        if entry.get("spotlight_id"):
            view.add_item(PeopleMove(UNSPOTLIGHT))
        if entry.get("matched_by") == mp.BY_PAIRING and entry.get("pairing_id"):
            view.add_item(PeopleMove(UNLINK))
            view.add_item(PeopleMove(TWITCH))
        opt_move = opt_move_for(bot, guild, marathon, chosen)
        if opt_move is not None:
            view.add_item(opt_move)
        for one in run_moves_for(bot, guild, marathon, run, chosen):
            view.add_item(one)
        lines += run_state_for(bot, guild, marathon, run, chosen)
        near = entry.get("looks_like")
        if near and not chosen.get("user_id"):
            view.add_item(PeopleMove(LINK_NEAR, username=near["username"]))
    view.add_item(PeopleMove(BACK))
    return (discord.Embed(title=marathon["name"], description=clamped(lines)), view)


def opt_move_for(bot: Any, guild: Any, marathon: Any, chosen: dict[str, Any]) -> Any:
    """Opt a BaF person out of this marathon's public posts, or back in — the runner post
    button's own words; never for someone who is not BaF."""
    from .marathon_public import words as public_words

    if not chosen.get("user_id"):
        return None
    if int(chosen["user_id"]) in ma.opted_out(marathon):
        label = public_words(bot, guild.id, MARATHON_PUBLIC_BUTTON_OPT_IN_KEY)
        return PeopleMove(OPT_IN, label=label, user_id=chosen["user_id"])
    label = public_words(bot, guild.id, MARATHON_PUBLIC_BUTTON_OPT_OUT_KEY)
    return PeopleMove(OPT_OUT, label=label, user_id=chosen["user_id"])


def announced_person(run: Any, chosen: dict[str, Any]) -> dict[str, Any] | None:
    if not chosen.get("user_id"):
        return None
    return next(
        (one for one in ma.baf_on(run) if int(one["user_id"]) == int(chosen["user_id"])), None
    )


def run_moves_for(bot: Any, guild: Any, marathon: Any, run: Any, chosen: dict[str, Any]) -> list:
    """This run's own answer for a BaF person and their @ — the run post's buttons, here."""
    from .marathon_announce import labels_of, policy_of

    person = announced_person(run, chosen)
    if person is None or not ma.shown(run):
        return []
    found = policy_of(bot, guild.id, marathon)
    labels = labels_of(bot, guild.id)
    name = str(person.get("name") or person["user_id"])
    made = []
    for action, to in (
        (RUN_ANSWER, ma.run_move(found, run, person)),
        (MENTION, ma.mention_move(found, person)),
    ):
        said = mt.render(labels[to], "{name}", name=name).text
        made.append(PeopleMove(action, label=said, user_id=person["user_id"], to=to, row=3))
    return made


def run_state_for(bot: Any, guild: Any, marathon: Any, run: Any, chosen: dict[str, Any]) -> list:
    from .marathon_announce import state_lines

    person = announced_person(run, chosen)
    if person is None:
        return []
    found = state_lines(bot, guild, marathon, run, only=person["user_id"])
    return ["", *found] if found else []


async def render(interaction: discord.Interaction, embed: Any, view: Any, previous: Any) -> None:
    retire(previous)
    view.message = await interaction.edit_original_response(
        embed=embed, view=view, allowed_mentions=discord.AllowedMentions.none()
    )


async def open_people(
    interaction: discord.Interaction,
    marathon_id: Any,
    previous: Any = None,
    *,
    day: Any = None,
    run_id: Any = None,
    person: Any = None,
) -> None:
    if not await opened(interaction, staff=False):
        return
    embed, view = await build_people(
        interaction.client,
        interaction.guild,
        interaction.user,
        marathon_id,
        day=day,
        run_id=run_id,
        person=person,
    )
    if view is None:
        from .marathon import open_root

        await open_root(interaction, previous)
        await answer(interaction, mt.NO_SUCH_MARATHON.format(given=str(marathon_id)[:40]))
        return
    await render(interaction, embed, view, previous)


async def reopen(interaction: discord.Interaction, previous: Any) -> None:
    await open_people(
        interaction,
        previous.marathon_id,
        previous,
        day=previous.day,
        run_id=previous.run_id,
        person=previous.person,
    )


async def people_move(interaction: discord.Interaction, view: Any, doing: Any) -> None:
    """A staff move from the slot view: re-read the marathon, do it, redraw the same slot."""
    if not await opened(interaction):
        return
    bot, guild = interaction.client, interaction.guild
    marathon = await get_marathon(bot.db, guild.id, view.marathon_id)
    if marathon is None:
        from .marathon import open_root

        await open_root(interaction, view)
        await answer(interaction, mt.NO_SUCH_MARATHON.format(given=str(view.marathon_id)[:40]))
        return
    outcome = await doing(bot, guild, interaction.user, marathon)
    await reopen(interaction, view)
    if outcome.message:
        await answer(interaction, outcome.message)


async def unlink_person(bot: Any, guild: Any, actor: Any, marathon: Any, name: Any) -> Outcome:
    state = await people_state(bot, guild, marathon)
    entry = mp.find_entry(state["entries"], name)
    pairing_id = (entry or {}).get("pairing_id")
    pairing = await pairing_by_id(bot.db, guild.id, pairing_id) if pairing_id else None
    if pairing is None:
        return refusal(mt.NO_SUCH_PAIRING, "no_such_pairing", 404)
    return await unpair_runner(bot, guild, actor, marathon, pairing)


async def person_pairing(bot: Any, guild: Any, view: Any, name: Any) -> Any:
    marathon = await get_marathon(bot.db, guild.id, view.marathon_id)
    if marathon is None:
        return None
    state = await people_state(bot, guild, marathon)
    pairing_id = (mp.find_entry(state["entries"], name) or {}).get("pairing_id")
    return await pairing_by_id(bot.db, guild.id, pairing_id) if pairing_id else None


async def fix_login(bot: Any, guild: Any, actor: Any, marathon: Any, name: Any, given: Any):
    state = await people_state(bot, guild, marathon)
    pairing_id = (mp.find_entry(state["entries"], name) or {}).get("pairing_id")
    pairing = await pairing_by_id(bot.db, guild.id, pairing_id) if pairing_id else None
    if pairing is None:
        return refusal(mt.NO_SUCH_PAIRING, "no_such_pairing", 404)
    return await set_pairing_login(bot, guild, actor, marathon, pairing, given)


class TwitchModal(AnswersErrors, discord.ui.Modal, title=TWITCH_TITLE):
    login = discord.ui.TextInput(
        label=TWITCH_LABEL, placeholder=TWITCH_HINT, required=False, max_length=100
    )

    def __init__(self, previous: Any = None, current: Any = None) -> None:
        super().__init__()
        self.previous = previous
        self.login.default = str(current) if current else None

    async def on_submit(self, interaction: discord.Interaction) -> None:
        view, given = self.previous, str(self.login)
        await people_move(
            interaction,
            view,
            lambda bot, guild, actor, row: fix_login(bot, guild, actor, row, view.person, given),
        )


def doing_for(action: str, name: Any, run_id: Any, member_id: Any, to: Any = None) -> Any:
    if action == RUN_ANSWER:
        from .marathon_announce import set_run_answer

        return lambda bot, guild, actor, row: set_run_answer(
            bot, guild, actor, row, run_id, member_id, to
        )
    if action == MENTION:
        from .marathon_announce import set_mention

        return lambda bot, guild, actor, row: set_mention(bot, guild, actor, row, member_id, to)
    if action in (OPT_OUT, OPT_IN):
        from .marathon_announce import set_opt_out

        return lambda bot, guild, actor, row: set_opt_out(
            bot, guild, actor, row, [member_id], action == OPT_OUT
        )
    if action == SPOTLIGHT:
        return lambda bot, guild, actor, row: spotlight_runner(
            bot, guild, actor, row, name, run_id=run_id
        )
    if action == UNSPOTLIGHT:
        return lambda bot, guild, actor, row: unspotlight_runner(bot, guild, actor, row, name)
    if action == UNLINK:
        return lambda bot, guild, actor, row: unlink_person(bot, guild, actor, row, name)
    return lambda bot, guild, actor, row: pair_runner(bot, guild, actor, row, name, member_id)


class PeopleMove(discord.ui.Button):
    def __init__(
        self,
        action: str,
        *,
        username: str = "",
        label: str = "",
        user_id: Any = None,
        to: Any = None,
        row: int = 2,
    ) -> None:
        words, style = LABELS[action]
        super().__init__(
            label=words.format(username=username, label=label)[:80] or "…",
            style=style,
            row=4 if action == BACK else row,
        )
        self.action = action
        self.username = username
        self.user_id = user_id
        self.to = to

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        name = view.person
        if self.action == BACK:
            if view.run_id is not None:
                await open_people(interaction, view.marathon_id, view, day=view.day)
            elif view.staff:
                from .marathon import open_card

                await open_card(interaction, view.marathon_id, view)
            else:
                from .marathon import open_root

                await open_root(interaction, view)
            return
        if self.action == TWITCH:
            if await still_staff(interaction):
                pairing = await person_pairing(interaction.client, interaction.guild, view, name)
                current = mt.pairing_login(pairing) if pairing is not None else None
                await interaction.response.send_modal(TwitchModal(view, current))
            return
        member_id = self.user_id or usernames_of(interaction.guild).get(self.username)
        await people_move(
            interaction, view, doing_for(self.action, name, view.run_id, member_id, self.to)
        )


class DayPick(discord.ui.Select):
    def __init__(self, days: list[mp.Day], chosen: Any) -> None:
        super().__init__(
            placeholder=mp.PICK_DAY,
            options=[
                discord.SelectOption(
                    label=mp.day_label(one)[:100], value=one.key, default=one.key == chosen
                )
                for one in days
            ],
            row=0,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await open_people(interaction, self.view.marathon_id, self.view, day=self.values[0])


class SlotPick(discord.ui.Select):
    def __init__(self, runs: list[Any], zone: str) -> None:
        super().__init__(
            placeholder=mp.PICK_SLOT,
            options=[
                discord.SelectOption(
                    label=mp.slot_label(run, zone)[:100],
                    value=str(run["id"]),
                    description=mp.slot_people(run)[:100] or None,
                )
                for run in runs
            ],
            row=1,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await still_staff(interaction):
            return
        await open_people(interaction, self.view.marathon_id, self.view, run_id=self.values[0])


class PersonPick(discord.ui.Select):
    def __init__(self, people: list[dict[str, Any]], chosen: Any) -> None:
        seen: set[str] = set()
        options = []
        for one in people:
            name = str(one.get("name") or "")[:100]
            if not name or name in seen:
                continue
            seen.add(name)
            options.append(
                discord.SelectOption(
                    label=name + (mp.BAF_MARK if one.get("user_id") else ""),
                    value=name,
                    description=str(one.get("part") or "")[:100] or None,
                    default=name == chosen,
                )
            )
        super().__init__(placeholder=mp.PICK_PERSON, options=options[: mp.SELECT_CAP], row=0)

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        await open_people(
            interaction, view.marathon_id, view, run_id=view.run_id, person=self.values[0]
        )


class LinkPick(discord.ui.UserSelect):
    def __init__(self) -> None:
        super().__init__(placeholder=mp.PICK_LINK, row=1)

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        name = view.person
        member_id = int(self.values[0].id)
        await people_move(
            interaction,
            view,
            lambda bot, guild, actor, row: pair_runner(bot, guild, actor, row, name, member_id),
        )


class PeopleButton(
    SafeDynamicItem, discord.ui.DynamicItem[discord.ui.Button], template=PEOPLE_TEMPLATE
):
    """The marathon notice's People…: the same view, private to whoever pressed it."""

    def __init__(self, marathon_id: int) -> None:
        self.marathon_id = int(marathon_id)
        super().__init__(
            discord.ui.Button(
                label=PEOPLE_BUTTON,
                style=discord.ButtonStyle.secondary,
                custom_id=f"marathon:people:{int(marathon_id)}",
            )
        )

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: Any, match: re.Match):
        return cls(int(match["marathon_id"]))

    async def on_click(self, interaction: discord.Interaction) -> None:
        bot = interaction.client
        if not bot.db.is_connected:
            await answer(interaction, DB_UNAVAILABLE)
            return
        embed, view = await build_people(bot, interaction.guild, interaction.user, self.marathon_id)
        if view is None:
            await answer(interaction, mt.NO_SUCH_MARATHON.format(given=str(self.marathon_id)))
            return
        await interaction.response.send_message(
            embed=embed,
            view=view,
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        view.message = await interaction.original_response()


def with_people(view: Any, marathon_id: Any, *, row: int | None = None) -> Any:
    """The notice's People… button beside whatever else the notice carries."""
    found = view if view is not None else discord.ui.View(timeout=None)
    button = PeopleButton(int(marathon_id))
    if row is not None:
        button.item.row = row
    found.add_item(button)
    return found


class MarathonPeoplePick(discord.ui.Select):
    """A member's way in: pick a marathon, read who from BaF is on it."""

    def __init__(self, rows: list[Any]) -> None:
        super().__init__(
            placeholder=mp.PICK_MARATHON_PEOPLE,
            options=[
                discord.SelectOption(label=str(row["name"])[:100], value=str(row["id"]))
                for row in rows[: mp.SELECT_CAP]
            ],
            row=0,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await open_people(interaction, self.values[0], self.view)
