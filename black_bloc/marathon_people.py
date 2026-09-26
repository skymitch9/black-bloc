from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Any, NamedTuple

from . import marathon as mt
from .golive import parse_ts
from .timezones import DEFAULT_TZ, zone

BAF = mt.BAF
BY_PAIRING = "pairing"
BY_LINK = "link"
BY_NAME = "username"
MATCHED_WORDS = {
    BY_PAIRING: "linked by staff",
    BY_LINK: "matched by their Twitch link",
    BY_NAME: "matched by their Discord name",
}
SPLIT = re.compile(r"[._\-\s]+")
SQUASH = re.compile(r"[^a-z0-9]+")
NEAR_FLOOR = 4
SELECT_CAP = 25

PEOPLE_BAF = f"**{BAF}**"
PEOPLE_NOBODY = f"Nobody from {BAF} is on this schedule yet."
PEOPLE_SCHEDULE = "**The schedule** — pick a day, then a slot, to link or spotlight someone."
PEOPLE_LINE = "{who} · {twitch} · {part} — {runs}"
PEOPLE_RUN = "<t:{unix}:f> {game}"
PEOPLE_RUN_LIVE = "**on now: {game}**"
PEOPLE_RUN_DONE = "~~{game}~~"
PEOPLE_SPOTLIT = "spotlit until <t:{unix}:d>"
PEOPLE_SPOTLIT_OPEN = "spotlit"
PEOPLE_ON_GOLIVE = "already on the Go-live page"
PEOPLE_MORE = "…and {count} more from {BAF}."
DAY_LABEL = "{day} · {slots} slot(s) · {baf} " + BAF
SLOT_LABEL = "{time} · {game}"
SLOT_HEAD = "**{game}** — {category} · <t:{unix}:f> · {state}"
SLOT_PERSON = "{who} ({part}){baf} · {twitch} · {how}"
SLOT_LOOKS_LIKE = "looks like **@{username}** — Link?"
SLOT_NOBODY = "Nobody is named on this slot."
SLOT_CAP_NOTE = "Showing the first {cap} of {count} slots on {day}."
PICK_MARATHON_PEOPLE = "Who from " + BAF + " is on… pick a marathon"
PICK_DAY = "Pick a day…"
PICK_SLOT = "…then a slot"
PICK_PERSON = "Pick a person in this slot…"
PICK_LINK = "Link to a member…"
NO_TWITCH = "no Twitch channel"
BAF_MARK = " ✦" + BAF

NO_LOGIN = (
    "**{name}** has no Twitch channel on this schedule, so there is nothing to spotlight. Add "
    "their channel on the Go-live page by hand if you know it."
)
ALREADY_ON_GOLIVE = (
    "**twitch.tv/{login}** is already on the Go-live page, so nothing was added — open it there "
    "to change its dates or spotlight."
)
NO_SUCH_PERSON = (
    "Nobody called **{given}** is on **{marathon}**'s schedule, so nothing was changed."
)
RUNS_OVER = "**{name}**'s runs on **{marathon}** are over, so there is nothing to spotlight."
NOT_SPOTLIT = "**{name}** is not spotlit from **{marathon}**, so nothing was changed."
BAD_LOGIN = "**{login}** is not a Twitch channel name, so nothing was spotlit."
SPOTLIT = (
    "**{name}** is spotlit on the Go-live page as **twitch.tv/{login}** for their runs on "
    "**{marathon}**."
)
UNSPOTLIT = "**{name}** is no longer spotlit — twitch.tv/{login} is off the Go-live page."
UNSPOTLIT_GONE = (
    "twitch.tv/{login} was already off the Go-live page, so **{marathon}** has forgotten it."
)


def person_key(person: Any) -> str:
    login = str(_get(person, "login") or "").strip().lower()
    return login or mt.runner_key(_get(person, "name"))


def is_person(person: Any, given: Any) -> bool:
    wanted = mt.runner_key(given)
    return bool(wanted) and wanted in {
        str(_get(person, "login") or "").strip().lower(),
        mt.runner_key(_get(person, "name")),
    }


def _get(row: Any, key: str) -> Any:
    return row.get(key) if isinstance(row, dict) else mt._cell(row, key)


def run_brief(run: Any, person: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": mt._cell(run, "id"),
        "game": mt._cell(run, "game"),
        "category": mt._cell(run, "category"),
        "scheduled_at": mt._cell(run, "scheduled_at"),
        "ends_at": mt._cell(run, "ends_at"),
        "state": mt._cell(run, "state"),
        "part": person.get("part"),
        "name": person.get("name"),
    }


def group_people(runs: Any) -> list[dict[str, Any]]:
    """Everyone on a schedule once: a member by their id across every name they run under,
    anyone else by their Twitch login, else their name; dropped runs are not counted."""
    found: dict[str, dict[str, Any]] = {}
    for run in sorted(
        (one for one in runs or () if mt._cell(one, "state") != mt.DROPPED), key=mt._when
    ):
        for person in mt.people_of(run):
            user_id = person.get("user_id")
            key = f"member:{int(user_id)}" if user_id else person_key(person)
            entry = found.setdefault(
                key,
                {
                    "key": person_key(person),
                    "name": str(person.get("name") or ""),
                    "login": person.get("login") or None,
                    "user_id": int(user_id) if user_id else None,
                    "parts": [],
                    "runs": [],
                },
            )
            if not entry["login"] and person.get("login"):
                entry["login"] = person["login"]
            if person.get("part") not in entry["parts"]:
                entry["parts"].append(person.get("part"))
            entry["runs"].append(run_brief(run, person))
    for entry in found.values():
        entry["parts"].sort(
            key=lambda part: mt.PART_ORDER.index(part) if part in mt.PART_ORDER else 9
        )
        entry.update(span_facts(entry["runs"]))
    return list(found.values())


def span_facts(runs: list[dict[str, Any]]) -> dict[str, Any]:
    starts = [at for at in (parse_ts(one["scheduled_at"]) for one in runs) if at is not None]
    ends = [
        at
        for at in (parse_ts(one["ends_at"]) or parse_ts(one["scheduled_at"]) for one in runs)
        if at is not None
    ]
    ahead = sorted(
        at
        for one in runs
        if one["state"] in (mt.UPCOMING, mt.LIVE)
        for at in [parse_ts(one["scheduled_at"])]
        if at is not None
    )
    return {
        "live": any(one["state"] == mt.LIVE for one in runs),
        "done": bool(runs) and all(one["state"] == mt.DONE for one in runs),
        "next_at": ahead[0].isoformat() if ahead else None,
        "first_at": min(starts).isoformat() if starts else None,
        "last_end": max(ends).isoformat() if ends else None,
    }


def baf_order(entry: dict[str, Any]) -> tuple[int, str, str]:
    """On now first, then the soonest next run, then people whose runs are all done."""
    if entry["live"]:
        return (0, entry["next_at"] or "", entry["name"].lower())
    if entry["next_at"]:
        return (1, entry["next_at"], entry["name"].lower())
    return (2, entry["last_end"] or "", entry["name"].lower())


def split_people(entries: list[dict[str, Any]]) -> tuple[list[dict], list[dict]]:
    baf = sorted((one for one in entries if one["user_id"]), key=baf_order)
    others = sorted((one for one in entries if not one["user_id"]), key=lambda one: one["key"])
    return (baf, others)


def matched_by(
    entry: dict[str, Any], pairings: Any, links: dict[str, int], *, marathon_id: Any
) -> tuple[str | None, Any]:
    """`(how, pairing_id)` for a member: the pairing that decided it, else their link, else name."""
    if not entry.get("user_id"):
        return (None, None)
    names = {mt.runner_key(one["name"]) for one in entry["runs"]}
    here = everywhere = None
    for row in pairings or ():
        if mt.runner_key(mt._cell(row, "runner_name")) not in names:
            continue
        owner = mt._cell(row, "marathon_id")
        if owner is None:
            everywhere = everywhere or row
        elif int(owner) == int(marathon_id):
            here = here or row
    chosen = here or everywhere
    if chosen is not None and int(mt._cell(chosen, "user_id")) == int(entry["user_id"]):
        return (BY_PAIRING, mt._cell(chosen, "id"))
    login = str(entry.get("login") or "").lower()
    if login and {k.lower(): v for k, v in (links or {}).items()}.get(login) == entry["user_id"]:
        return (BY_LINK, None)
    return (BY_NAME, None)


def squash(text: Any) -> str:
    return SQUASH.sub("", str(text or "").lower())


def one_edit(a: str, b: str) -> bool:
    if a == b or abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b, strict=True)) == 1
    short, long = (a, b) if len(a) < len(b) else (b, a)
    return any(long[:at] + long[at + 1 :] == short for at in range(len(long)))


def looks_like(entry: dict[str, Any], usernames: dict[str, int]) -> tuple[str, int] | None:
    """A Discord username a stranger is probably: the same letters, one edit away, or the head
    of an underscored name (`gz` / `gz_hero`). A suggestion only; staff press Link."""
    if entry.get("user_id"):
        return None
    words = [str(entry.get("name") or ""), str(entry.get("login") or "")]
    wanted = [one.strip().lower() for one in words if one.strip()]
    exact = {mt.runner_key(entry.get("name"))} if not entry.get("login") else set()
    for username in sorted(usernames or {}):
        if username in exact:
            continue
        flat = squash(username)
        head = SPLIT.split(username)[0]
        for given in wanted:
            flat_given = squash(given)
            if not flat_given:
                continue
            if (
                flat == flat_given
                or (len(flat_given) >= NEAR_FLOOR and one_edit(flat, flat_given))
                or (len(given) >= 2 and head == given and head != username)
            ):
                return (username, int(usernames[username]))
    return None


def spotlight_span(
    runs: list[dict[str, Any]],
    marathon: Any,
    *,
    lead_hours: int,
    slack_hours: int,
    run_id: Any = None,
) -> tuple[str | None, str | None]:
    """From a slot: that run's window. From the BaF block: the person's whole span. With no
    times at all: the marathon's own dates."""
    rows = [one for one in runs if run_id is None or str(one["id"]) == str(run_id)]
    facts = span_facts(rows)
    first = parse_ts(facts["first_at"])
    last = parse_ts(facts["last_end"])
    if first is None or last is None:
        return (mt._cell(marathon, "starts_at"), mt._cell(marathon, "ends_at"))
    return (
        (first - timedelta(hours=int(lead_hours))).isoformat(),
        (last + timedelta(hours=int(slack_hours))).isoformat(),
    )


class Day(NamedTuple):
    key: str
    label: str
    runs: list[Any]
    baf: int
    today: bool
    past: bool


def local(at: datetime, tz_name: Any) -> datetime:
    return at.astimezone(zone(tz_name) or zone(DEFAULT_TZ))


def day_word(at: datetime) -> str:
    return f"{at:%a} {at.day} {at:%b}"


def days_of(runs: Any, tz_name: Any, now: datetime) -> list[Day]:
    """Every slot by day in the guild's zone; a slot is one run, a race shares it."""
    today = local(now, tz_name).date()
    found: dict[str, list[Any]] = {}
    labels: dict[str, str] = {}
    dates: dict[str, Any] = {}
    for run in sorted(
        (one for one in runs or () if mt._cell(one, "state") != mt.DROPPED), key=mt._when
    ):
        at = parse_ts(mt._cell(run, "scheduled_at"))
        if at is None:
            continue
        there = local(at, tz_name)
        key = there.date().isoformat()
        found.setdefault(key, []).append(run)
        labels[key] = day_word(there)
        dates[key] = there.date()
    return [
        Day(
            key,
            labels[key],
            rows,
            len([one for one in rows if mt.is_ours(one)]),
            dates[key] == today,
            dates[key] < today,
        )
        for key, rows in found.items()
    ]


def day_label(day: Day) -> str:
    return DAY_LABEL.format(day=day.label, slots=len(day.runs), baf=day.baf)


def slot_label(run: Any, tz_name: Any) -> str:
    at = parse_ts(mt._cell(run, "scheduled_at"))
    time = f"{local(at, tz_name):%H:%M}" if at is not None else "—"
    return SLOT_LABEL.format(time=time, game=mt._cell(run, "game") or "")


def slot_people(run: Any) -> str:
    return ", ".join(
        str(one.get("name") or "") + (BAF_MARK if one.get("user_id") else "")
        for one in mt.people_of(run)
    )


def entry_for(entries: list[dict[str, Any]], run_id: Any, person: dict[str, Any]) -> Any:
    for entry in entries:
        for one in entry["runs"]:
            if (
                str(one["id"]) == str(run_id)
                and one["name"] == person.get("name")
                and one["part"] == person.get("part")
            ):
                return entry
    return None


def find_entry(entries: list[dict[str, Any]], given: Any) -> Any:
    wanted = mt.runner_key(given)
    for entry in entries:
        if wanted == str(entry.get("login") or "").lower() or wanted == entry["key"]:
            return entry
    for entry in entries:
        if any(is_person(one, given) for one in entry["runs"]):
            return entry
    return None
