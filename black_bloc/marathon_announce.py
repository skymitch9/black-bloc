"""BaF announcements: the marathon's switches, each person's opt-out, each run's own answer
and who is written without an @."""

from __future__ import annotations

import json
from typing import Any, NamedTuple

from . import marathon as mt
from . import marathon_hosts as mh

SWITCH = mh.ANNOUNCE
HOSTS = mh.HOST_ANNOUNCE
OPTED = "announce_opt_out"
RUN_ANSWERS = "announce_people"
MENTIONS = "mention_people"
OPT_OUT = "optout"
OPT_IN = "optin"
OUT_WORDS = (OPT_OUT, "out", "remove", "off")
IN_WORDS = (OPT_IN, "in", "post", "on")
BAD_OPT = "Say out or in for a person's announcements, so nothing was changed."
BAD_OPT_CODE = "bad_opt"
NOT_BAF = "Nobody from BaF with that id is on **{marathon}**, so nothing was changed."
NOT_BAF_CODE = "not_baf"

IN = "in"
OUT = "out"
DEFAULT = "default"
ANSWERS = (IN, OUT)
RUN_WORDS = {
    IN: IN,
    "on": IN,
    "yes": IN,
    "announce": IN,
    OUT: OUT,
    "off": OUT,
    "no": OUT,
    DEFAULT: None,
    "follow": None,
    "clear": None,
    "": None,
}
BAD_RUN = (
    "Say in, out or default for whether a person is announced for a run, so nothing was changed."
)
BAD_RUN_CODE = "bad_announce"
NOT_ON_RUN = "Nobody from BaF with that id is on **{game}**, so nothing was changed."
NOT_ON_RUN_CODE = "not_on_run"
RUN_OVER = "**{game}** is over, so nothing was changed."
RUN_DROPPED = "**{game}** is off the schedule, so nothing was changed."
RUN_OVER_CODE = "run_over"

PLAIN = "plain"
MENTION = "mention"
MENTION_WORDS = {
    PLAIN: PLAIN,
    "name": PLAIN,
    "off": PLAIN,
    "no": PLAIN,
    MENTION: MENTION,
    "@": MENTION,
    "on": MENTION,
    "yes": MENTION,
}
BAD_MENTION = "Say plain or mention for how a person's name is written, so nothing was changed."
BAD_MENTION_CODE = "bad_mention"

RUNNER = "runner"
HOST = "host"

WHY_OFF = "marathon_off"
WHY_MARATHON = "opted_out"
WHY_RUN = "run"
WHY_DEFAULT = "default"
WHY_HOSTS_OFF = "hosts_off"
WHYS = (WHY_OFF, WHY_MARATHON, WHY_RUN, WHY_DEFAULT, WHY_HOSTS_OFF)

NAMED = "public_people"
GONE = "not_on_run"
BECAUSE = {
    WHY_MARATHON: "opted_out",
    WHY_HOSTS_OFF: "hosts_off",
    WHY_RUN: "run_answer",
    WHY_OFF: "marathon_off",
}

MOVES = (IN, OUT, DEFAULT, PLAIN, MENTION)
MOVE_TEMPLATE = (
    r"marathon:announce:(?P<marathon_id>[0-9]+):(?P<run_id>[0-9]+)"
    r":(?P<user_id>[0-9]+):(?P<to>in|out|default|plain|mention)"
)
MOVE_ID = "marathon:announce:{marathon_id}:{run_id}:{user_id}:{to}"
PICK_TEMPLATE = r"marathon:announce:(?P<marathon_id>[0-9]+):(?P<run_id>[0-9]+):pick(?P<page>[0-9]*)"
PICK_ID = "marathon:announce:{marathon_id}:{run_id}:pick{page}"
PICK = "pick"
PREFIX = "marathon:announce:"
BUTTON_PEOPLE = 4
OPTION_LIMIT = 25
PICK_PEOPLE = 12
PICK_ROWS = 4
LABEL_LIMIT = 80
OPTION_LABEL_LIMIT = 100
SHOWN_STATES = (mt.UPCOMING, mt.LIVE)


class Verdict(NamedTuple):
    yes: bool
    why: str


class Policy(NamedTuple):
    master: bool = True
    hosts_on: bool = False
    opted: frozenset[int] = frozenset()
    mentions: Any = None
    mention_default: bool = True

    def plain(self, user_id: Any) -> bool:
        answer = (self.mentions or {}).get(int(user_id))
        if answer is None:
            return not self.mention_default
        return answer == PLAIN


class Move(NamedTuple):
    custom_id: str
    label: str
    to: str
    user_id: int = 0


class Pick(NamedTuple):
    custom_id: str
    label: str
    options: tuple[tuple[str, str], ...]
    to: str = PICK
    row: int = 1


def announces(marathon: Any, default: Any) -> bool:
    return mh.switch_on(marathon, SWITCH, default)


def announces_hosts(marathon: Any, default: Any) -> bool:
    return mh.switch_on(marathon, HOSTS, default)


def decide(*, master: bool, opted_out: bool, answer: Any, role: str, hosts_on: bool) -> Verdict:
    """Whether one person is announced for one run: the marathon's switch is the master, then
    the person's marathon-wide opt-out (a run's own yes gets past it), then the run's own
    answer, then the default for their part."""
    if not master:
        return Verdict(False, WHY_OFF)
    if opted_out and answer != IN:
        return Verdict(False, WHY_MARATHON)
    if answer == IN:
        return Verdict(True, WHY_RUN)
    if answer == OUT:
        return Verdict(False, WHY_RUN)
    if role == HOST:
        return Verdict(bool(hosts_on), WHY_DEFAULT if hosts_on else WHY_HOSTS_OFF)
    return Verdict(True, WHY_DEFAULT)


def _ids(raw: Any) -> set[int]:
    try:
        found = json.loads(raw or "[]") if not isinstance(raw, list) else raw
    except (TypeError, ValueError):
        return set()
    kept: set[int] = set()
    for one in found if isinstance(found, list) else ():
        try:
            kept.add(int(one))
        except (TypeError, ValueError):
            continue
    return kept


def opted_out(marathon: Any) -> set[int]:
    return _ids(mt._cell(marathon, OPTED))


def _answers(raw: Any, allowed: tuple[str, ...]) -> dict[int, str]:
    try:
        found = json.loads(raw or "{}") if not isinstance(raw, dict) else raw
    except (TypeError, ValueError):
        return {}
    kept: dict[int, str] = {}
    for key, value in (found if isinstance(found, dict) else {}).items():
        try:
            user_id = int(key)
        except (TypeError, ValueError):
            continue
        if value in allowed:
            kept[user_id] = str(value)
    return kept


def run_answers(row: Any) -> dict[int, str]:
    return _answers(mt._cell(row, RUN_ANSWERS), ANSWERS)


def mentions(marathon: Any) -> dict[int, str]:
    return _answers(mt._cell(marathon, MENTIONS), (PLAIN, MENTION))


def dump_answers(found: dict[int, str]) -> str | None:
    if not found:
        return None
    return json.dumps({str(key): found[key] for key in sorted(found)})


def policy(
    marathon: Any, *, master_default: Any, hosts_default: Any, mention_default: Any
) -> Policy:
    return Policy(
        master=announces(marathon, master_default),
        hosts_on=announces_hosts(marathon, hosts_default),
        opted=frozenset(opted_out(marathon)),
        mentions=mentions(marathon),
        mention_default=bool(mention_default),
    )


def standing(found: Policy) -> Policy:
    """The policy a post that is already up is followed by: the master going off stops new
    posts, never one in flight."""
    return found._replace(master=True)


def dump(ids: Any) -> str:
    return json.dumps(sorted({int(one) for one in ids}))


def toggled(opted: set[int], user_ids: Any, out: bool) -> set[int]:
    wanted = {int(one) for one in user_ids}
    return (opted | wanted) if out else (opted - wanted)


def kept(people: Any, opted: Any) -> list[dict[str, Any]]:
    return [dict(one) for one in people or () if int(one["user_id"]) not in opted]


def role_of(person: Any) -> str:
    return HOST if person.get("part") == mt.HOST else RUNNER


def baf_on(row: Any) -> list[dict[str, Any]]:
    """Everyone from BaF a public post could name for this run: the people of ours on it, and
    its BaF hosts when a host does not make a run ours. Each carries their `role`."""
    found: dict[int, dict[str, Any]] = {}
    people = mt.people_of(row)
    for one in mt.ours(people):
        found[int(one["user_id"])] = dict(one) | {"role": role_of(one)}
    for one in people:
        if one.get("user_id") and one.get("part") == mt.HOST:
            found.setdefault(int(one["user_id"]), dict(one) | {"role": HOST})
    return list(found.values())


def verdict(found: Policy, row: Any, user_id: Any, role: str) -> Verdict:
    return decide(
        master=found.master,
        opted_out=int(user_id) in found.opted,
        answer=run_answers(row).get(int(user_id)),
        role=role,
        hosts_on=found.hosts_on,
    )


def runs_it(row: Any, user_id: Any) -> bool:
    return any(int(one["user_id"]) == int(user_id) and one["role"] == RUNNER for one in baf_on(row))


def host_verdict(found: Policy, row: Any, user_id: Any) -> Verdict:
    """A host weighed for one run of their block: the run's own answer is about their hosting
    only where they do not also run it."""
    return decide(
        master=found.master,
        opted_out=int(user_id) in found.opted,
        answer=None if runs_it(row, user_id) else run_answers(row).get(int(user_id)),
        role=HOST,
        hosts_on=found.hosts_on,
    )


def block_yes(block: Any, found: Policy, user_id: Any) -> bool:
    return any(host_verdict(found, row, user_id).yes for row in block.runs)


def run_people(row: Any, found: Policy) -> list[dict[str, Any]]:
    """The BaF people a run's public post names: everyone of ours the decision announces."""
    return [
        dict(one)
        for one in mt.ours(mt.people_of(row))
        if verdict(found, row, one["user_id"], role_of(one)).yes
    ]


def block_people(block: Any, found: Policy) -> list[dict[str, Any]]:
    """The hosts a host block's public posts name: each host announced for at least one run of
    the block. A host is weighed as a host on every run of it, whatever else they do there."""
    return [dict(one) for one in block.hosts if block_yes(block, found, one["user_id"])]


def as_named(people: Any) -> list[dict[str, Any]]:
    """Who a post names, as the post's own record keeps them."""
    return [
        {
            "user_id": int(one["user_id"]),
            "name": str(one.get("name") or one["user_id"]),
            "part": one.get("part"),
            "login": one.get("login"),
            "plain": bool(one.get("plain")),
        }
        for one in people or ()
    ]


def named_of(raw: Any) -> list[dict[str, Any]] | None:
    """The record of who a post names; None for a post from before names were recorded."""
    if raw is None or raw == "":
        return None
    try:
        found = json.loads(raw) if isinstance(raw, str) else raw
        return as_named(found) if isinstance(found, list) else None
    except (AttributeError, KeyError, TypeError, ValueError):
        return None


def dump_named(people: Any) -> str:
    return json.dumps(as_named(people))


def ids_of(people: Any) -> list[int] | None:
    return None if people is None else [int(one["user_id"]) for one in people]


def still_named(
    people: Any, recorded: Any, found: Policy, yes: Any, moved: Any = ()
) -> list[dict[str, Any]]:
    """Who a post already up names now. Someone it names stays unless they are left out by
    name; someone a move was aimed at is weighed by the real host switch; anyone it does not
    name joins only when the decision announces them. No record reads as naming everyone."""
    held = found._replace(master=True)
    carried = held._replace(hosts_on=True)
    was = None if recorded is None else {int(one) for one in recorded}
    aimed = {int(one) for one in moved or ()}
    kept = []
    for one in people or ():
        member = int(one["user_id"])
        if was is not None and member not in was:
            weighed = found
        else:
            weighed = held if member in aimed else carried
        if yes(one, weighed):
            kept.append(dict(one))
    return kept


def run_standing(row: Any, found: Policy, recorded: Any, moved: Any = ()) -> list[dict[str, Any]]:
    return still_named(
        mt.ours(mt.people_of(row)),
        recorded,
        found,
        lambda one, how: verdict(how, row, one["user_id"], role_of(one)).yes,
        moved,
    )


def block_standing(
    block: Any, found: Policy, recorded: Any, moved: Any = ()
) -> list[dict[str, Any]]:
    return still_named(
        block.hosts,
        recorded,
        found,
        lambda one, how: block_yes(block, how, one["user_id"]),
        moved,
    )


def _first(named: Any, moved: Any) -> list[dict[str, Any]]:
    aimed = {int(one) for one in moved or ()}
    return sorted(named or (), key=lambda one: int(one["user_id"]) not in aimed)


def run_because(row: Any, found: Policy, named: Any, moved: Any = ()) -> str:
    """Which decision left a run's post naming nobody: the person a move was aimed at first."""
    held = found._replace(master=True)
    on = {int(one["user_id"]): one for one in mt.ours(mt.people_of(row))}
    for one in _first(named, moved):
        here = on.get(int(one["user_id"]))
        if here is None:
            return GONE
        said = verdict(held, row, here["user_id"], role_of(here))
        if not said.yes:
            return BECAUSE[said.why]
    return BECAUSE[WHY_OFF] if not found.master else GONE


def block_because(block: Any, found: Policy, named: Any, moved: Any = ()) -> str:
    """Which decision left a block's post naming nobody."""
    held = found._replace(master=True)
    hosting = {int(one["user_id"]) for one in block.hosts}
    for one in _first(named, moved):
        member = int(one["user_id"])
        if member not in hosting:
            return GONE
        whys = {said.why for said in (host_verdict(held, row, member) for row in block.runs)}
        for why in (WHY_MARATHON, WHY_HOSTS_OFF, WHY_RUN):
            if why in whys:
                return BECAUSE[why]
    return BECAUSE[WHY_OFF] if not found.master else GONE


def all_out(user_ids: Any, opted: set[int]) -> bool:
    ids = [int(one) for one in user_ids]
    return bool(ids) and all(one in opted for one in ids)


def clean_opt(given: Any) -> bool | None:
    """True to opt out, False to opt back in, None when the word is not understood."""
    if isinstance(given, bool):
        return given
    word = str(given if given is not None else "").strip().lower()
    if word in OUT_WORDS:
        return True
    if word in IN_WORDS:
        return False
    return None


def clean_run(given: Any) -> tuple[bool, str | None]:
    """`(understood, answer)`: in, out, or None for the default."""
    if given is None:
        return (True, None)
    if isinstance(given, bool):
        return (True, IN if given else OUT)
    word = str(given).strip().lower()
    if word not in RUN_WORDS:
        return (False, None)
    return (True, RUN_WORDS[word])


def clean_mention(given: Any) -> str | None:
    if isinstance(given, bool):
        return MENTION if given else PLAIN
    return MENTION_WORDS.get(str(given if given is not None else "").strip().lower())


def answered(found: dict[int, str], user_id: Any, answer: str | None) -> dict[int, str]:
    now = dict(found)
    if answer is None:
        now.pop(int(user_id), None)
    else:
        now[int(user_id)] = answer
    return now


def mention_stored(wanted: str, default: bool) -> str | None:
    """What a person's choice is stored as: nothing while it is the server's own default."""
    return None if (wanted == MENTION) == bool(default) else wanted


def label(text: Any, limit: int = LABEL_LIMIT) -> str:
    return str(text or "").strip()[:limit] or "…"


def run_move(found: Policy, row: Any, person: dict[str, Any]) -> str:
    """The one move a person's answer for this run can take now: back to the default once it
    has an answer, else the opposite of what the defaults say."""
    if run_answers(row).get(int(person["user_id"])) is not None:
        return DEFAULT
    return OUT if verdict(standing(found), row, person["user_id"], person["role"]).yes else IN


def mention_move(found: Policy, person: dict[str, Any]) -> str:
    return MENTION if found.plain(person["user_id"]) else PLAIN


def shown(row: Any) -> bool:
    return mt._cell(row, "state") in SHOWN_STATES


def over(row: Any) -> str | None:
    """The refusal for a run that takes no answer any more, in words."""
    if shown(row):
        return None
    wanted = RUN_DROPPED if mt._cell(row, "state") == mt.DROPPED else RUN_OVER
    return wanted.format(game=mt._cell(row, "game") or "")


def moves(marathon_id: Any, row: Any, found: Policy, labels: dict[str, str]) -> tuple[Move, ...]:
    """Two buttons a person — their answer for this run and their @ — for a run still ahead."""
    if not shown(row):
        return ()
    made: list[Move] = []
    for one in baf_on(row):
        name = str(one.get("name") or one["user_id"])
        for to in (run_move(found, row, one), mention_move(found, one)):
            made.append(
                Move(
                    MOVE_ID.format(
                        marathon_id=int(marathon_id),
                        run_id=int(row["id"]),
                        user_id=int(one["user_id"]),
                        to=to,
                    ),
                    label(mt.render(labels[to], "{name}", name=name).text),
                    to,
                    int(one["user_id"]),
                )
            )
    return tuple(made)


def laid_out(marathon_id: Any, row: Any, made: tuple[Move, ...], placeholder: str) -> tuple:
    """Buttons while they fit under the run's own button; menus once they do not — twelve
    people a menu, a person's two moves never split, a menu a row."""
    people = list(dict.fromkeys(one.user_id for one in made))
    if len(people) <= BUTTON_PEOPLE:
        return made
    pages = [people[at : at + PICK_PEOPLE] for at in range(0, len(people), PICK_PEOPLE)]
    return tuple(
        Pick(
            PICK_ID.format(
                marathon_id=int(marathon_id), run_id=int(row["id"]), page=page + 1 if page else ""
            ),
            label(placeholder, OPTION_LABEL_LIMIT),
            tuple(
                (f"{one.user_id}:{one.to}", label(one.label, OPTION_LABEL_LIMIT))
                for one in made
                if one.user_id in here
            ),
            row=page + 1,
        )
        for page, here in enumerate(pages[:PICK_ROWS])
    )


def option_of(value: Any) -> tuple[int, str] | None:
    user_id, _, to = str(value or "").partition(":")
    if not user_id.isdigit() or to not in MOVES:
        return None
    return (int(user_id), to)


def state_lines(row: Any, found: Policy, words: dict[str, str], *, only: Any = None) -> list[str]:
    """Who is announced for this run and why, one line a person."""
    if not shown(row):
        return []
    lines = []
    for one in baf_on(row):
        if only is not None and int(one["user_id"]) != int(only):
            continue
        said = verdict(found, row, one["user_id"], one["role"])
        lines.append(
            mt.render(
                words["line"],
                "{name}: {state} — {why}{plain}",
                name=str(one.get("name") or one["user_id"]),
                state=words["yes" if said.yes else "no"],
                why=words[said.why],
                plain=words[PLAIN] if found.plain(one["user_id"]) else "",
            ).text
        )
    return lines


__all__ = [
    "ANSWERS",
    "BAD_MENTION",
    "BAD_OPT",
    "BAD_RUN",
    "DEFAULT",
    "HOST",
    "HOSTS",
    "IN",
    "MENTION",
    "MENTIONS",
    "MOVE_TEMPLATE",
    "Move",
    "NOT_BAF",
    "NOT_ON_RUN",
    "OPTED",
    "OPT_IN",
    "OPT_OUT",
    "OUT",
    "PICK_TEMPLATE",
    "PLAIN",
    "Pick",
    "Policy",
    "RUNNER",
    "RUN_ANSWERS",
    "RUN_OVER",
    "RUN_OVER_CODE",
    "NAMED",
    "as_named",
    "block_because",
    "block_standing",
    "block_yes",
    "dump_named",
    "host_verdict",
    "ids_of",
    "named_of",
    "over",
    "run_because",
    "run_standing",
    "runs_it",
    "still_named",
    "SWITCH",
    "Verdict",
    "all_out",
    "announces",
    "announces_hosts",
    "answered",
    "baf_on",
    "block_people",
    "clean_mention",
    "clean_opt",
    "clean_run",
    "decide",
    "dump",
    "dump_answers",
    "kept",
    "laid_out",
    "mention_move",
    "mention_stored",
    "mentions",
    "moves",
    "opted_out",
    "option_of",
    "policy",
    "role_of",
    "run_answers",
    "run_move",
    "run_people",
    "standing",
    "state_lines",
    "toggled",
    "verdict",
]
