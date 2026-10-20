from __future__ import annotations

import csv
import io
import json
import re
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote

from . import marathon as mt
from .actionlog import log_action
from .cogs.content.marathon import links_of, not_ours_of, pairings_of, usernames_of
from .logkinds import VIA_DISCORD, kind_via
from .marathon_people import looks_like
from .marathon_sources import (
    GDQ,
    RUNNER,
    SOURCE_WORDS,
    ScheduleClient,
    ScheduleError,
    read_url,
    utc_iso,
)
from .panels import Outcome, refusal
from .runs_genres import (
    NO_RULE,
    Rule,
    family_terms,
    genre_family,
    parse_families,
    parse_qualifiers,
)
from .settings_store import (
    MARATHON_HOSTS_COUNT_AS_OURS_KEY,
    MARATHON_MATCH_HOSTS_KEY,
    RUNS_GENRE_FAMILIES,
    RUNS_GENRE_QUALIFIERS,
    RUNS_PARTS,
    RUNS_SOURCES,
)

TRACKED = "tracked"
IMPORTED = "imported"
HAND = "hand"
HOWS = (TRACKED, IMPORTED, HAND)
HOW_WORDS = {TRACKED: "tracked", IMPORTED: "imported", HAND: "by hand"}
EVENT_WORDS = {GDQ: "GDQ", "gdq_hotfix": "GDQ Hotfix"}
COUNTED_STATES = (mt.DONE, mt.LIVE)
EXCLUDED = "excluded"
FIELDS = ("date", "event", "game", "category", "runners", "note")
RUNS_PAGE = "runs.html"
MARATHONS_COG = "Marathons"
TEXT_LIMIT = 200
NOTE_LIMIT = 1000
TAG_LIMIT = 100
SERIES = "series"
GENRE = "genre"
TAGS = (SERIES, GENRE)
CSV_LIMIT = 2000
PREVIEW_LIMIT = 200
LOOKUP_GAMES = 5
LOOKUP_RUNS = 5
NAME_SPLIT = re.compile(r"\s*(?:;|,|&|/|\s\+\s)\s*")
CSV_COLUMNS = (
    "key",
    "date",
    "event",
    "event_source",
    "event_ref",
    "game",
    "series",
    "genre",
    "category",
    "runners",
    "runner_names",
    "runner_ids",
    "how",
    "note",
)
CSV_ALIASES = {
    "when": "date",
    "started_at": "date",
    "day": "date",
    "event name": "event",
    "event_name": "event",
    "marathon": "event",
    "runner": "runners",
    "runner(s)": "runners",
    "runners_text": "runners",
    "notes": "note",
}
DAY_FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%d %b %Y", "%b %d %Y", "%b %d, %Y")
MOMENT_FORMATS = ("%Y-%m-%d %H:%M", "%m/%d/%Y %H:%M", "%m/%d/%Y %I:%M %p")

NO_GAME = (
    "A run needs a game, so nothing was saved. Type the game's name in the Game box and save again."
)
BAD_DATE = (
    "**{given}** is not a date Black Bloc can read, so nothing was saved. Pick it in the date "
    "box, or write it as YYYY-MM-DD."
)
BAD_KEY = (
    "**{given}** is not a run on the BaF runs page, so nothing was changed. Refresh the page "
    "to see the runs as they are now."
)
NO_SUCH_RUN = (
    "That run is not in the BaF runs database any more, so nothing was changed. Refresh the "
    "page to see the runs as they are now."
)
NO_SUCH_EVENT = (
    "That marathon is not one Black Bloc follows any more, so nothing was saved. Pick another "
    "event, or choose Other… and type its name."
)
NOT_REMOVED = "That run is not removed, so there is nothing to restore."
HAND_GONE = (
    "A run added by hand is deleted when it is removed, so there is nothing to restore. Add it "
    "again with Add a run…."
)
ALREADY_REMOVED = "That run is already removed. Restore puts it back."
NO_CHANGE = "Nothing in that run changed, so nothing was saved."
NO_EDITS = "That run has no staff edits, so there was nothing to clear."
NOT_A_TRACKER = (
    "**{given}** is not a GDQ tracker event link, so nothing was read. Paste the link of the "
    "event from tracker.gamesdonequick.com, like https://tracker.gamesdonequick.com/tracker/"
    "event/50."
)
TRACKER_DOWN = "The GDQ tracker could not be read, so nothing was imported: {why}."
EMPTY_CSV = (
    "That CSV has no rows Black Bloc can read, so nothing was imported. The first line names "
    "the columns; game is the one every row needs."
)
NO_GAME_COLUMN = (
    "That CSV has no game column, so nothing was imported. The first line names the columns, "
    "and one of them must be game. Export CSV shows the full set."
)
TOO_MANY_ROWS = (
    "That CSV has more than {limit} rows, so nothing was imported. Split it into smaller files "
    "and import each."
)
ADDED = "**{game}** is in the BaF runs database."
EDITED = "**{game}** is saved."
CLEARED = "**{game}** is back to what the schedule says."
REMOVED = "**{game}** is off the BaF runs page."
DELETED = "**{game}** is deleted."
RESTORED = "**{game}** is back on the BaF runs page."
SERIES_SET = "**{game}** is in the series **{series}**."
SERIES_CLEARED = "**{game}** has no series now."
GENRE_SET = "**{game}** is in the genre **{genre}**."
GENRE_CLEARED = "**{game}** has no genre now."
TAG_WORDS = {SERIES: (SERIES_SET, SERIES_CLEARED), GENRE: (GENRE_SET, GENRE_CLEARED)}
DRY_SAID = (
    "{would} row(s) would be added, {skipped} skipped (already here), {need} need a runner "
    "match. Nothing was written."
)
IMPORT_SAID = "{added} row(s) added, {skipped} skipped (already here), {need} need a runner match."
EVENT_DRY_SAID = (
    "**{event}**: {would} BaF run(s) would be added, {skipped} skipped (already here), {need} "
    "runner name(s) match no member, {later} not run yet. Nothing was written."
)
EVENT_SAID = (
    "**{event}**: {added} BaF run(s) added, {skipped} skipped (already here), {need} runner "
    "name(s) match no member, {later} not run yet."
)


def game_key(text: Any) -> str:
    return " ".join(str(text or "").split()).lower()


def clean(text: Any, limit: int = TEXT_LIMIT) -> str:
    return " ".join(str(text or "").split())[:limit]


def event_word(source: Any) -> str:
    text = str(source or "")
    return EVENT_WORDS.get(text) or SOURCE_WORDS.get(text) or text


def parse_key(key: Any) -> tuple[str, int] | None:
    text = str(key or "").strip()
    if len(text) < 2 or text[0] not in "th" or not text[1:].isdigit():
        return None
    return (TRACKED if text[0] == "t" else HAND, int(text[1:]))


def parse_date(given: Any) -> tuple[bool, str | None]:
    text = " ".join(str(given or "").split())
    if not text:
        return (True, None)
    found = utc_iso(text.replace(" ", "T", 1) if re.match(r"^\d{4}-\d\d-\d\d \d", text) else text)
    if found is not None:
        return (True, found)
    for shape in MOMENT_FORMATS:
        try:
            return (True, datetime.strptime(text, shape).replace(tzinfo=UTC).isoformat())
        except ValueError:
            continue
    for shape in DAY_FORMATS:
        try:
            day = datetime.strptime(text, shape).date()
        except ValueError:
            continue
        return (True, datetime(day.year, day.month, day.day, tzinfo=UTC).isoformat())
    return (False, None)


def people_json(raw: Any) -> list[dict[str, Any]]:
    return mt.people_of({"people": raw})


def counted_people(people: list[dict[str, Any]], parts: Any) -> list[dict[str, Any]]:
    wanted = set(parts or ())
    mine = {int(one["user_id"]) for one in mt.ours(people)}
    return [
        one
        for one in people
        if one.get("user_id")
        and int(one["user_id"]) in mine
        and one.get("part") in wanted
        and one.get("counts") is not False
    ]


def display_of(guild: Any, user_id: Any, fallback: str) -> str:
    member = guild.get_member(int(user_id)) if user_id and guild is not None else None
    name = getattr(member, "display_name", None) or getattr(member, "name", None)
    return str(name or fallback or user_id or "")


def runner_entries(guild: Any, people: list[dict[str, Any]]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for one in people:
        source = clean(one.get("name"))
        user_id = one.get("user_id")
        shown = display_of(guild, user_id, source) if user_id else source
        found.append(
            {
                "name": source,
                "user_id": str(user_id) if user_id else None,
                "display": shown,
                "linked": bool(user_id),
            }
        )
    return found


def runners_line(entries: list[dict[str, Any]]) -> str:
    said: list[str] = []
    for one in entries:
        text = one["display"]
        if one["linked"] and one["name"] and one["name"].lower() != text.lower():
            text = f"{text} ({one['name']})"
        said.append(text)
    return ", ".join(said)


def row_people(row: Any, parts: Any) -> list[dict[str, Any]]:
    people = people_json(row["people"])
    if row["run_ref"]:
        return counted_people(people, parts) or hand_people(people, parts)
    return hand_people(people, parts)


def hand_people(people: list[dict[str, Any]], parts: Any) -> list[dict[str, Any]]:
    wanted = set(parts or ())
    kept = [one for one in people if one.get("part", RUNNER) in wanted]
    return kept or people


async def _fetch(db: Any, sql: str, args: tuple[Any, ...] = ()) -> list[Any]:
    cur = await db.conn.execute(sql, args)
    return list(await cur.fetchall())


TRACKED_SQL = """
SELECT r.id AS run_id, r.marathon_id, r.external_id, r.game, r.category, r.people, r.state,
       r.actual_started_at, r.scheduled_at, m.name AS marathon_name, m.source, m.source_ref,
       {live} AS live_row
FROM {runs} r JOIN {marathons} m ON m.id = r.marathon_id
WHERE m.guild_id = ? AND m.source IN ({marks}) AND r.state IN ({states})
"""


async def tracked_runs(db: Any, guild_id: int, sources: list[str]) -> list[Any]:
    if not sources:
        return []
    marks = ", ".join("?" for _ in sources)
    states = ", ".join("?" for _ in COUNTED_STATES)
    parts = [
        TRACKED_SQL.format(
            live=1, runs="marathon_runs", marathons="marathons", marks=marks, states=states
        ),
        TRACKED_SQL.format(
            live=0,
            runs="marathon_runs_archive",
            marathons="marathons_archive",
            marks=marks,
            states=states,
        ),
    ]
    args = (int(guild_id), *sources, *COUNTED_STATES)
    rows = await _fetch(db, " UNION ALL ".join(parts) + " ORDER BY live_row DESC", args * 2)
    seen: set[tuple[int, str]] = set()
    kept: list[Any] = []
    for row in rows:
        wanted = (int(row["marathon_id"]), str(row["external_id"]))
        if wanted in seen:
            continue
        seen.add(wanted)
        kept.append(row)
    return kept


async def edits_of(db: Any, guild_id: int) -> dict[tuple[int, str], dict[str, Any]]:
    found: dict[tuple[int, str], dict[str, Any]] = {}
    for row in await _fetch(db, "SELECT * FROM baf_run_edits WHERE guild_id = ?", (int(guild_id),)):
        slot = found.setdefault((int(row["marathon_id"]), str(row["external_id"])), {})
        if row["field"] == EXCLUDED:
            slot[EXCLUDED] = bool(row["excluded"])
        else:
            slot[row["field"]] = row["value"]
    return found


async def tags_of(db: Any, guild_id: int) -> dict[str, dict[str, str]]:
    rows = await _fetch(
        db, "SELECT game_key, series, genre FROM baf_series WHERE guild_id = ?", (int(guild_id),)
    )
    return {str(row["game_key"]): {tag: str(row[tag] or "") for tag in TAGS} for row in rows}


async def live_marathons(db: Any, guild_id: int) -> dict[tuple[str, str], int]:
    rows = await _fetch(
        db, "SELECT id, source, source_ref FROM marathons WHERE guild_id = ?", (int(guild_id),)
    )
    return {(str(row["source"]), str(row["source_ref"])): int(row["id"]) for row in rows}


def _tracked_row(
    guild: Any, run: Any, edits: dict[str, Any], parts: Any, tags: dict[str, dict[str, str]]
) -> dict[str, Any] | None:
    people = people_json(run["people"])
    counted = counted_people(people, parts)
    if not counted:
        return None
    source = {
        "date": run["actual_started_at"] or run["scheduled_at"],
        "event": run["marathon_name"],
        "game": run["game"],
        "category": run["category"] or "",
        "runners": json.dumps(counted),
        "note": "",
    }
    shown = dict(source)
    changed: list[str] = []
    for field in FIELDS:
        if field in edits and edits[field] is not None and edits[field] != source[field]:
            shown[field] = edits[field]
            changed.append(field)
    runners = runner_entries(guild, people_json(shown["runners"]))
    tracked = {field: source[field] for field in changed}
    if "runners" in tracked:
        tracked["runners"] = runners_line(runner_entries(guild, counted))
    return _shaped(
        key=f"t{int(run['run_id'])}",
        how=TRACKED,
        when=shown["date"],
        event=shown["event"],
        source=run["source"],
        ref=run["source_ref"],
        marathon_id=int(run["marathon_id"]) if run["live_row"] else None,
        game=shown["game"],
        category=shown["category"],
        runners=runners,
        note=shown["note"],
        tags=tags,
        removed=bool(edits.get(EXCLUDED)),
        edited=changed,
        tracked=tracked,
        state=run["state"],
    )


def _hand_row(
    guild: Any,
    row: Any,
    parts: Any,
    tags: dict[str, dict[str, str]],
    marathons: dict[tuple[str, str], int],
) -> dict[str, Any]:
    source, ref = row["event_source"], row["event_ref"]
    return _shaped(
        key=f"h{int(row['id'])}",
        how=row["how"] if row["how"] in (HAND, IMPORTED) else HAND,
        when=row["started_at"],
        event=row["event_name"],
        source=source,
        ref=ref,
        marathon_id=marathons.get((str(source), str(ref))) if source and ref else None,
        game=row["game"],
        category=row["category"],
        runners=runner_entries(guild, row_people(row, parts)),
        note=row["note"],
        tags=tags,
        removed=False,
        edited=[],
        tracked={},
        state=mt.DONE,
    )


def _shaped(**given: Any) -> dict[str, Any]:
    key_of_game = game_key(given["game"])
    tags = given["tags"].get(key_of_game, {})
    return {
        "key": given["key"],
        "how": given["how"],
        "how_word": HOW_WORDS[given["how"]],
        "date": given["when"],
        "event": given["event"] or "",
        "event_source": given["source"] or None,
        "event_word": event_word(given["source"]) if given["source"] else "",
        "event_ref": given["ref"] or None,
        "marathon_id": given["marathon_id"],
        "game": given["game"],
        "game_key": key_of_game,
        "series": tags.get(SERIES, ""),
        "genre": tags.get(GENRE, ""),
        "category": given["category"] or "",
        "runners": given["runners"],
        "runners_text": runners_line(given["runners"]),
        "note": given["note"] or "",
        "removed": given["removed"],
        "edited": given["edited"],
        "tracked": given["tracked"],
        "state": given["state"],
    }


def newest_first(row: dict[str, Any]) -> tuple[str, str]:
    return (str(row["date"] or ""), row["key"])


def genre_rule(bot: Any, guild_id: int) -> Rule:
    return (
        parse_qualifiers(bot.store.get(guild_id, RUNS_GENRE_QUALIFIERS)),
        parse_families(bot.store.get(guild_id, RUNS_GENRE_FAMILIES)),
    )


def families_shown(rule: Rule) -> list[dict[str, Any]]:
    return [{"family": name, "aliases": list(aliases)} for name, aliases in rule[1]]


def genre_text(row: dict[str, Any], rule: Rule) -> str:
    return family_terms(row["genre_family"], rule[1])


async def view(bot: Any, guild: Any) -> list[dict[str, Any]]:
    """Every BaF run in a counted source, newest first; removed rows carry `removed`."""
    db = bot.db
    sources = list(bot.store.get(guild.id, RUNS_SOURCES) or ())
    parts = list(bot.store.get(guild.id, RUNS_PARTS) or ())
    edits = await edits_of(db, guild.id)
    tags = await tags_of(db, guild.id)
    found: list[dict[str, Any]] = []
    for run in await tracked_runs(db, guild.id, sources):
        made = _tracked_row(
            guild,
            run,
            edits.get((int(run["marathon_id"]), str(run["external_id"])), {}),
            parts,
            tags,
        )
        if made is not None:
            found.append(made)
    marathons = await live_marathons(db, guild.id)
    for row in await _fetch(db, "SELECT * FROM baf_runs WHERE guild_id = ?", (int(guild.id),)):
        found.append(_hand_row(guild, row, parts, tags, marathons))
    rule = genre_rule(bot, guild.id)
    for made in found:
        made["genre_family"] = genre_family(made["genre"], *rule)
    found.sort(key=newest_first, reverse=True)
    return found


def year_of(row: dict[str, Any]) -> str:
    return str(row["date"] or "")[:4]


def text_of(row: dict[str, Any], rule: Rule = NO_RULE) -> str:
    return " ".join(
        [
            row["game"],
            row["category"],
            row["runners_text"],
            row["event"],
            row["series"],
            row["genre"],
            genre_text(row, rule),
        ]
    ).lower()


def filtered(
    rows: list[dict[str, Any]],
    *,
    game: Any = None,
    event: Any = None,
    series: Any = None,
    genre: Any = None,
    runner: Any = None,
    year: Any = None,
    how: Any = None,
    q: Any = None,
    removed: bool = False,
    rule: Rule = NO_RULE,
) -> list[dict[str, Any]]:
    kept: list[dict[str, Any]] = []
    family = genre_family(genre, *rule) if genre else ""
    for row in rows:
        if row["removed"] != removed:
            continue
        if game and game_key(game) not in row["game_key"]:
            continue
        if event and game_key(event) != game_key(row["event"]):
            continue
        if series and game_key(series) != game_key(row["series"]):
            continue
        if genre and family != row["genre_family"]:
            continue
        if runner and not any(
            str(runner) == one["user_id"] or game_key(runner) == game_key(one["display"])
            for one in row["runners"]
        ):
            continue
        if year and year_of(row) != str(year):
            continue
        if how and row["how"] != how:
            continue
        if q and game_key(q) not in text_of(row, rule):
            continue
        kept.append(row)
    return kept


def games(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        if not row["removed"]:
            grouped.setdefault(row["game_key"], []).append(row)
    found: list[dict[str, Any]] = []
    for key, runs in grouped.items():
        runs.sort(key=newest_first, reverse=True)
        last = runs[0]
        runners: list[str] = []
        categories: list[str] = []
        for run in runs:
            for one in run["runners"]:
                if one["display"] and one["display"] not in runners:
                    runners.append(one["display"])
            if run["category"] and run["category"] not in categories:
                categories.append(run["category"])
        found.append(
            {
                "game": last["game"],
                "game_key": key,
                "series": last["series"],
                "genre": last["genre"],
                "genre_family": last["genre_family"],
                "times": len(runs),
                "last_date": last["date"],
                "last_event": last["event"],
                "runners": runners,
                "categories": categories,
                "keys": [run["key"] for run in runs],
            }
        )
    found.sort(key=lambda one: (str(one["last_date"] or ""), one["game_key"]), reverse=True)
    return found


async def counted_events(db: Any, guild_id: int, sources: list[str]) -> list[dict[str, Any]]:
    if not sources:
        return []
    marks = ", ".join("?" for _ in sources)
    found: list[dict[str, Any]] = []
    for table, archived in (("marathons", False), ("marathons_archive", True)):
        for row in await _fetch(
            db,
            f"SELECT id, name, source, source_ref, starts_at FROM {table} "
            f"WHERE guild_id = ? AND source IN ({marks}) ORDER BY starts_at DESC",
            (int(guild_id), *sources),
        ):
            found.append(
                {
                    "marathon_id": int(row["id"]),
                    "name": row["name"],
                    "source": row["source"],
                    "word": event_word(row["source"]),
                    "starts_at": row["starts_at"],
                    "archived": archived,
                }
            )
    return found


async def marathon_by_id(db: Any, guild_id: int, marathon_id: Any) -> Any:
    try:
        wanted = int(marathon_id)
    except (TypeError, ValueError):
        return None
    for table in ("marathons", "marathons_archive"):
        rows = await _fetch(
            db,
            f"SELECT id, name, source, source_ref FROM {table} WHERE id = ? AND guild_id = ?",
            (wanted, int(guild_id)),
        )
        if rows:
            return rows[0]
    return None


async def tracked_run(db: Any, guild_id: int, run_id: int) -> Any:
    for runs, marathons in (
        ("marathon_runs", "marathons"),
        ("marathon_runs_archive", "marathons_archive"),
    ):
        rows = await _fetch(
            db,
            f"SELECT r.id, r.marathon_id, r.external_id, r.game FROM {runs} r "
            f"JOIN {marathons} m ON m.id = r.marathon_id WHERE r.id = ? AND m.guild_id = ?",
            (int(run_id), int(guild_id)),
        )
        if rows:
            return rows[0]
    return None


async def hand_run(db: Any, guild_id: int, row_id: int) -> Any:
    rows = await _fetch(
        db, "SELECT * FROM baf_runs WHERE id = ? AND guild_id = ?", (int(row_id), int(guild_id))
    )
    return rows[0] if rows else None


async def find(bot: Any, guild: Any, key: Any) -> dict[str, Any] | None:
    for row in await view(bot, guild):
        if row["key"] == key:
            return row
    return None


def actor_id(actor: Any) -> int | None:
    found = getattr(actor, "id", None)
    return int(found) if found is not None else None


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def members_named(guild: Any) -> dict[str, int]:
    found = dict(usernames_of(guild))
    for member in list(getattr(guild, "members", None) or ()):
        shown = game_key(getattr(member, "display_name", None))
        if shown and not getattr(member, "bot", False):
            found.setdefault(shown, int(member.id))
    return found


def people_from(guild: Any, payload: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for one in payload.get("runners") or ():
        given = one if isinstance(one, dict) else {"user_id": one}
        raw = str(given.get("user_id") or "").strip()
        user_id = int(raw) if raw.isdigit() else None
        name = clean(given.get("name")) or (display_of(guild, user_id, "") if user_id else "")
        if name or user_id:
            found.append(
                {"name": name or str(user_id), "login": None, "part": RUNNER, "user_id": user_id}
            )
    for name in NAME_SPLIT.split(str(payload.get("runner_names") or "")):
        if clean(name):
            found.append({"name": clean(name), "login": None, "part": RUNNER, "user_id": None})
    return found


async def _event_fields(bot: Any, guild: Any, payload: dict[str, Any]) -> Any:
    marathon_id = payload.get("marathon_id")
    if marathon_id not in (None, ""):
        marathon = await marathon_by_id(bot.db, guild.id, marathon_id)
        if marathon is None:
            return None
        return (marathon["name"], marathon["source"], marathon["source_ref"])
    return (
        clean(payload.get("event")),
        payload.get("event_source") or None,
        payload.get("event_ref") or None,
    )


async def _write_tag(bot: Any, guild_id: int, game: str, tag: str, value: Any, actor: Any) -> bool:
    text = clean(value, TAG_LIMIT)
    key = game_key(game)
    if tag not in TAGS or not key:
        return False
    await bot.db.conn.execute(
        f"INSERT INTO baf_series(guild_id, game_key, series, genre, by, at) "
        f"VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(guild_id, game_key) DO UPDATE SET "
        f"{tag} = excluded.{tag}, by = excluded.by, at = excluded.at",
        (
            int(guild_id),
            key,
            text if tag == SERIES else "",
            text if tag == GENRE else "",
            actor_id(actor),
            now_iso(),
        ),
    )
    await bot.db.conn.execute(
        "DELETE FROM baf_series WHERE guild_id = ? AND game_key = ? AND series = '' "
        "AND genre = ''",
        (int(guild_id), key),
    )
    return True


async def _write_given_tags(
    bot: Any, guild_id: int, game: str, payload: dict[str, Any], actor: Any, *, blank: bool
) -> dict[str, Any]:
    written: dict[str, Any] = {}
    for tag in TAGS:
        if tag not in payload or (not blank and payload.get(tag) in (None, "")):
            continue
        await _write_tag(bot, guild_id, game, tag, payload.get(tag), actor)
        written[tag] = payload.get(tag)
    return written


async def add(
    bot: Any, guild: Any, actor: Any, payload: dict[str, Any], *, via: str = VIA_DISCORD
) -> Outcome:
    game = clean(payload.get("game"))
    if not game:
        return refusal(NO_GAME, "no_game", 400)
    ok, started = parse_date(payload.get("date"))
    if not ok:
        return refusal(BAD_DATE.format(given=clean(payload.get("date"), 40)), "bad_date", 400)
    event = await _event_fields(bot, guild, payload)
    if event is None:
        return refusal(NO_SUCH_EVENT, "no_such_event", 404)
    people = people_from(guild, payload)
    cur = await bot.db.conn.execute(
        "INSERT INTO baf_runs(guild_id, how, event_name, event_source, event_ref, started_at, "
        "game, category, runners_text, people, note, added_by, added_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            int(guild.id),
            HAND,
            event[0] or "",
            event[1],
            event[2],
            started,
            game,
            clean(payload.get("category")),
            ", ".join(one["name"] for one in people),
            json.dumps(people),
            clean(payload.get("note"), NOTE_LIMIT),
            actor_id(actor),
            now_iso(),
        ),
    )
    key = f"h{int(cur.lastrowid)}"
    await _write_given_tags(bot, guild.id, game, payload, actor, blank=False)
    await bot.db.conn.commit()
    await log_action(
        bot,
        guild,
        kind_via("runs.added", via),
        actor=actor,
        details={
            "key": key,
            "game": game,
            "event": event[0],
            "date": started,
            "runners": [one["name"] for one in people],
            "via": via,
        },
    )
    return Outcome(True, ADDED.format(game=game), value=key)


def _wanted_fields(guild: Any, payload: dict[str, Any]) -> tuple[dict[str, str], str | None]:
    wanted: dict[str, str] = {}
    if "date" in payload:
        ok, started = parse_date(payload.get("date"))
        if not ok:
            return ({}, BAD_DATE.format(given=clean(payload.get("date"), 40)))
        wanted["date"] = started or ""
    if "game" in payload:
        game = clean(payload.get("game"))
        if not game:
            return ({}, NO_GAME)
        wanted["game"] = game
    if "category" in payload:
        wanted["category"] = clean(payload.get("category"))
    if "note" in payload:
        wanted["note"] = clean(payload.get("note"), NOTE_LIMIT)
    if "runners" in payload or "runner_names" in payload:
        wanted["runners"] = json.dumps(people_from(guild, payload))
    return (wanted, None)


async def edit(
    bot: Any,
    guild: Any,
    actor: Any,
    key: Any,
    payload: dict[str, Any],
    *,
    via: str = VIA_DISCORD,
) -> Outcome:
    parsed = parse_key(key)
    if parsed is None:
        return refusal(BAD_KEY.format(given=str(key)[:40]), "bad_key", 400)
    how, row_id = parsed
    if how == HAND:
        return await _edit_hand(bot, guild, actor, row_id, payload, via)
    return await _edit_tracked(bot, guild, actor, row_id, payload, via)


async def _edit_hand(
    bot: Any, guild: Any, actor: Any, row_id: int, payload: dict[str, Any], via: str
) -> Outcome:
    row = await hand_run(bot.db, guild.id, row_id)
    if row is None:
        return refusal(NO_SUCH_RUN, "no_such_run", 404)
    wanted, problem = _wanted_fields(guild, payload)
    if problem:
        return refusal(problem, "bad_value", 400)
    columns: dict[str, Any] = {}
    if "date" in wanted:
        columns["started_at"] = wanted["date"] or None
    for field in ("game", "category", "note"):
        if field in wanted:
            columns[field] = wanted[field]
    if "runners" in wanted:
        people = json.loads(wanted["runners"])
        columns["people"] = wanted["runners"]
        columns["runners_text"] = ", ".join(one["name"] for one in people)
    if "event" in payload or "marathon_id" in payload:
        event = await _event_fields(bot, guild, payload)
        if event is None:
            return refusal(NO_SUCH_EVENT, "no_such_event", 404)
        columns.update(event_name=event[0] or "", event_source=event[1], event_ref=event[2])
    changed = {name: value for name, value in columns.items() if row[name] != value}
    if not changed and not any(tag in payload for tag in TAGS):
        return refusal(NO_CHANGE, "no_change", 409)
    if changed:
        sets = ", ".join(f"{name} = ?" for name in changed)
        await bot.db.conn.execute(
            f"UPDATE baf_runs SET {sets}, edited_by = ?, edited_at = ? WHERE id = ?",
            (*changed.values(), actor_id(actor), now_iso(), int(row_id)),
        )
    game = columns.get("game", row["game"])
    written = await _write_given_tags(bot, guild.id, game, payload, actor, blank=True)
    await bot.db.conn.commit()
    await log_action(
        bot,
        guild,
        kind_via("runs.edited", via),
        actor=actor,
        details={
            "key": f"h{row_id}",
            "game": game,
            "before": {name: row[name] for name in changed},
            "after": changed,
            "series": written.get(SERIES),
            "genre": written.get(GENRE),
            "via": via,
        },
    )
    return Outcome(True, EDITED.format(game=game), value=f"h{row_id}")


async def _upsert_edit(
    db: Any, guild_id: int, run: Any, field: str, value: Any, actor: Any, excluded: bool = False
) -> None:
    await db.conn.execute(
        "INSERT INTO baf_run_edits(guild_id, marathon_id, external_id, field, value, excluded, "
        "by, at) VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(marathon_id, external_id, field) "
        "DO UPDATE SET value = excluded.value, excluded = excluded.excluded, by = excluded.by, "
        "at = excluded.at",
        (
            int(guild_id),
            int(run["marathon_id"]),
            str(run["external_id"]),
            field,
            value,
            1 if excluded else 0,
            actor_id(actor),
            now_iso(),
        ),
    )


async def _drop_edit(db: Any, run: Any, field: str | None) -> int:
    if field is None:
        cur = await db.conn.execute(
            "DELETE FROM baf_run_edits WHERE marathon_id = ? AND external_id = ? AND field != ?",
            (int(run["marathon_id"]), str(run["external_id"]), EXCLUDED),
        )
    else:
        cur = await db.conn.execute(
            "DELETE FROM baf_run_edits WHERE marathon_id = ? AND external_id = ? AND field = ?",
            (int(run["marathon_id"]), str(run["external_id"]), field),
        )
    return cur.rowcount


async def _edit_tracked(
    bot: Any, guild: Any, actor: Any, run_id: int, payload: dict[str, Any], via: str
) -> Outcome:
    run = await tracked_run(bot.db, guild.id, run_id)
    shown = await find(bot, guild, f"t{run_id}") if run is not None else None
    if run is None or shown is None:
        return refusal(NO_SUCH_RUN, "no_such_run", 404)
    if payload.get("clear"):
        gone = await _drop_edit(bot.db, run, None)
        if not gone:
            return refusal(NO_EDITS, "no_edits", 409)
        await bot.db.conn.commit()
        await log_action(
            bot,
            guild,
            kind_via("runs.edited", via),
            actor=actor,
            details={
                "key": f"t{run_id}",
                "game": run["game"],
                "cleared": shown["edited"],
                "via": via,
            },
        )
        return Outcome(True, CLEARED.format(game=run["game"]), value=f"t{run_id}")
    wanted, problem = _wanted_fields(guild, payload)
    if problem:
        return refusal(problem, "bad_value", 400)
    if "event" in payload:
        wanted["event"] = clean(payload.get("event"))
    source = await _source_values(bot, guild, run_id)
    before: dict[str, Any] = {}
    after: dict[str, Any] = {}
    current = await edits_of(bot.db, guild.id)
    held = current.get((int(run["marathon_id"]), str(run["external_id"])), {})
    for field, value in wanted.items():
        was = held.get(field)
        if value == source.get(field):
            if was is not None:
                await _drop_edit(bot.db, run, field)
                before[field], after[field] = was, None
            continue
        if value != was:
            await _upsert_edit(bot.db, guild.id, run, field, value, actor)
            before[field], after[field] = was, value
    game = wanted.get("game") or held.get("game") or run["game"]
    if not after and not any(tag in payload for tag in TAGS):
        return refusal(NO_CHANGE, "no_change", 409)
    written = await _write_given_tags(bot, guild.id, game, payload, actor, blank=True)
    await bot.db.conn.commit()
    await log_action(
        bot,
        guild,
        kind_via("runs.edited", via),
        actor=actor,
        details={
            "key": f"t{run_id}",
            "game": game,
            "before": before,
            "after": after,
            "series": written.get(SERIES),
            "genre": written.get(GENRE),
            "via": via,
        },
    )
    return Outcome(True, EDITED.format(game=game), value=f"t{run_id}")


async def _source_values(bot: Any, guild: Any, run_id: int) -> dict[str, Any]:
    sources = list(bot.store.get(guild.id, RUNS_SOURCES) or ())
    parts = list(bot.store.get(guild.id, RUNS_PARTS) or ())
    for run in await tracked_runs(bot.db, guild.id, sources):
        if int(run["run_id"]) != int(run_id):
            continue
        return {
            "date": run["actual_started_at"] or run["scheduled_at"] or "",
            "event": run["marathon_name"],
            "game": run["game"],
            "category": run["category"] or "",
            "runners": json.dumps(counted_people(people_json(run["people"]), parts)),
            "note": "",
        }
    return {}


async def remove(bot: Any, guild: Any, actor: Any, key: Any, *, via: str = VIA_DISCORD) -> Outcome:
    parsed = parse_key(key)
    if parsed is None:
        return refusal(BAD_KEY.format(given=str(key)[:40]), "bad_key", 400)
    how, row_id = parsed
    if how == HAND:
        row = await hand_run(bot.db, guild.id, row_id)
        if row is None:
            return refusal(NO_SUCH_RUN, "no_such_run", 404)
        await bot.db.conn.execute("DELETE FROM baf_runs WHERE id = ?", (int(row_id),))
        await bot.db.conn.commit()
        await log_action(
            bot,
            guild,
            kind_via("runs.removed", via),
            actor=actor,
            details={
                "key": f"h{row_id}",
                "game": row["game"],
                "deleted": True,
                "before": {name: row[name] for name in row.keys()},
                "via": via,
            },
        )
        return Outcome(True, DELETED.format(game=row["game"]), value=f"h{row_id}")
    run = await tracked_run(bot.db, guild.id, row_id)
    shown = await find(bot, guild, f"t{row_id}") if run is not None else None
    if run is None or shown is None:
        return refusal(NO_SUCH_RUN, "no_such_run", 404)
    if shown["removed"]:
        return refusal(ALREADY_REMOVED, "already_removed", 409)
    await _upsert_edit(bot.db, guild.id, run, EXCLUDED, None, actor, excluded=True)
    await bot.db.conn.commit()
    await log_action(
        bot,
        guild,
        kind_via("runs.removed", via),
        actor=actor,
        details={"key": f"t{row_id}", "game": shown["game"], "deleted": False, "via": via},
    )
    return Outcome(True, REMOVED.format(game=shown["game"]), value=f"t{row_id}")


async def restore(bot: Any, guild: Any, actor: Any, key: Any, *, via: str = VIA_DISCORD) -> Outcome:
    parsed = parse_key(key)
    if parsed is None:
        return refusal(BAD_KEY.format(given=str(key)[:40]), "bad_key", 400)
    how, row_id = parsed
    if how == HAND:
        return refusal(HAND_GONE, "not_restorable", 409)
    run = await tracked_run(bot.db, guild.id, row_id)
    if run is None:
        return refusal(NO_SUCH_RUN, "no_such_run", 404)
    if not await _drop_edit(bot.db, run, EXCLUDED):
        return refusal(NOT_REMOVED, "not_removed", 409)
    await bot.db.conn.commit()
    await log_action(
        bot,
        guild,
        kind_via("runs.restored", via),
        actor=actor,
        details={"key": f"t{row_id}", "game": run["game"], "via": via},
    )
    return Outcome(True, RESTORED.format(game=run["game"]), value=f"t{row_id}")


async def set_tag(
    bot: Any, guild: Any, actor: Any, key: Any, tag: str, value: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    wanted = game_key(key)
    if not wanted:
        return refusal(NO_GAME, "no_game", 400)
    shown = next((one for one in games(await view(bot, guild)) if one["game_key"] == wanted), None)
    game = shown["game"] if shown else wanted
    before = (await tags_of(bot.db, guild.id)).get(wanted, {}).get(tag, "")
    text = clean(value, TAG_LIMIT)
    if text == before:
        return refusal(NO_CHANGE, "no_change", 409)
    await _write_tag(bot, guild.id, game, tag, text, actor)
    await bot.db.conn.commit()
    await log_action(
        bot,
        guild,
        kind_via(f"runs.{tag}_set", via),
        actor=actor,
        details={"game_key": wanted, "game": game, "before": before, "after": text, "via": via},
    )
    said_set, said_cleared = TAG_WORDS[tag]
    said = said_set.format(game=game, **{tag: text}) if text else said_cleared.format(game=game)
    return Outcome(True, said, value=wanted)


async def set_series(
    bot: Any, guild: Any, actor: Any, key: Any, series: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    return await set_tag(bot, guild, actor, key, SERIES, series, via=via)


async def set_genre(
    bot: Any, guild: Any, actor: Any, key: Any, genre: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    return await set_tag(bot, guild, actor, key, GENRE, genre, via=via)


def natural_key(event: Any, game: Any, category: Any, when: Any) -> tuple[str, str, str, str]:
    return (game_key(event), game_key(game), game_key(category), str(when or "")[:10])


def _csv_rows(text: str) -> tuple[list[dict[str, str]], str | None]:
    body = str(text or "").lstrip("﻿")
    if not body.strip():
        return ([], EMPTY_CSV)
    reader = csv.DictReader(io.StringIO(body))
    names = [CSV_ALIASES.get(game_key(one), game_key(one)) for one in reader.fieldnames or ()]
    if "game" not in names:
        return ([], NO_GAME_COLUMN)
    found: list[dict[str, str]] = []
    for raw in reader:
        row: dict[str, str] = {}
        for given, value in raw.items():
            name = CSV_ALIASES.get(game_key(given), game_key(given))
            if name and name not in row:
                row[name] = "" if value is None else str(value)
        if any(value.strip() for value in row.values()):
            found.append(row)
        if len(found) > CSV_LIMIT:
            return ([], TOO_MANY_ROWS.format(limit=CSV_LIMIT))
    return (found, None if found else EMPTY_CSV)


def _csv_people(row: dict[str, str], guild: Any, matcher: Any) -> list[dict[str, Any]]:
    names = [clean(one) for one in str(row.get("runner_names") or "").split(";")]
    ids = [one.strip() for one in str(row.get("runner_ids") or "").split(";")]
    if not any(names):
        names = [clean(one) for one in NAME_SPLIT.split(str(row.get("runners") or ""))]
        ids = []
    people: list[dict[str, Any]] = []
    for at, name in enumerate(names):
        given = ids[at] if at < len(ids) else ""
        if not name and not given.isdigit():
            continue
        people.append(
            {
                "name": name or given,
                "login": None,
                "part": RUNNER,
                "user_id": int(given) if given.isdigit() else None,
            }
        )
    loose = [one for one in people if one["user_id"] is None]
    for person, matched in zip(loose, matcher(loose), strict=True):
        person["user_id"] = matched.get("user_id")
    return people


async def _matcher(bot: Any, guild: Any, pairs: dict[str, Any] | None = None) -> Any:
    links = await links_of(bot.db)
    everywhere = [
        row for row in await pairings_of(bot.db, guild.id) if mt._cell(row, "marathon_id") is None
    ]
    for name, user in (pairs or {}).items():
        if clean(name) and str(user or "").strip().isdigit():
            everywhere.append(
                {"runner_name": clean(name), "user_id": int(user), "marathon_id": None}
            )
    usernames = members_named(guild)
    excluded = await not_ours_of(bot, guild)
    match_hosts = bool(bot.store.get(guild.id, MARATHON_MATCH_HOSTS_KEY))
    hosts_count = bool(bot.store.get(guild.id, MARATHON_HOSTS_COUNT_AS_OURS_KEY))

    def match(people: Any) -> list[dict[str, Any]]:
        return mt.match_people(
            people,
            links,
            everywhere,
            match_hosts=match_hosts,
            usernames=usernames,
            hosts_count=hosts_count,
            not_ours=excluded,
        )

    match.usernames = usernames
    return match


async def _insert_imported(db: Any, guild_id: int, row: dict[str, Any], actor: Any) -> None:
    await db.conn.execute(
        "INSERT INTO baf_runs(guild_id, how, event_name, event_source, event_ref, run_ref, "
        "started_at, game, category, runners_text, people, note, added_by, added_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            int(guild_id),
            IMPORTED,
            row["event"],
            row["event_source"],
            row["event_ref"],
            row.get("run_ref"),
            row["date"],
            row["game"],
            row["category"],
            ", ".join(one["name"] for one in row["people"]),
            json.dumps(row["people"]),
            row.get("note") or "",
            actor_id(actor),
            now_iso(),
        ),
    )


def _preview(row: dict[str, Any], guild: Any) -> dict[str, Any]:
    return {
        "date": row["date"],
        "event": row["event"],
        "game": row["game"],
        "category": row["category"],
        "runners_text": runners_line(runner_entries(guild, row["people"])),
    }


async def import_csv(
    bot: Any,
    guild: Any,
    actor: Any,
    text: Any,
    *,
    dry_run: bool = True,
    via: str = VIA_DISCORD,
) -> Outcome:
    rows, problem = _csv_rows(str(text or ""))
    if problem:
        return refusal(problem, "bad_csv", 400)
    existing = await view(bot, guild)
    keys = {row["key"] for row in existing}
    seen = {
        natural_key(row["event"], row["game"], row["category"], row["date"]) for row in existing
    }
    known_tags = await tags_of(bot.db, guild.id)
    matcher = await _matcher(bot, guild)
    adds: list[dict[str, Any]] = []
    skipped = 0
    need = 0
    bad = 0
    for row in rows:
        game = clean(row.get("game"))
        ok, started = parse_date(row.get("date"))
        if not game or not ok:
            bad += 1
            continue
        if str(row.get("key") or "").strip() in keys:
            skipped += 1
            continue
        event = clean(row.get("event"))
        category = clean(row.get("category"))
        natural = natural_key(event, game, category, started)
        if natural in seen:
            skipped += 1
            continue
        seen.add(natural)
        people = _csv_people(row, guild, matcher)
        if any(one["user_id"] is None for one in people):
            need += 1
        adds.append(
            {
                "event": event,
                "event_source": clean(row.get("event_source")) or None,
                "event_ref": clean(row.get("event_ref")) or None,
                "date": started,
                "game": game,
                "category": category,
                "people": people,
                "note": clean(row.get("note"), NOTE_LIMIT),
                **{tag: clean(row.get(tag), TAG_LIMIT) for tag in TAGS},
            }
        )
    summary = {
        "dry_run": bool(dry_run),
        "would_add": len(adds),
        "added": 0,
        "skipped": skipped,
        "need_match": need,
        "unreadable": bad,
        "unmatched": [],
        "not_run_yet": 0,
        "event": None,
        "rows": [_preview(one, guild) for one in adds[:PREVIEW_LIMIT]],
    }
    if dry_run:
        said = DRY_SAID.format(would=len(adds), skipped=skipped, need=need)
        return Outcome(True, said, value=summary)
    for one in adds:
        await _insert_imported(bot.db, guild.id, one, actor)
        known = known_tags.setdefault(game_key(one["game"]), {})
        for tag in TAGS:
            if one[tag] and not known.get(tag):
                await _write_tag(bot, guild.id, one["game"], tag, one[tag], actor)
                known[tag] = one[tag]
    await bot.db.conn.commit()
    summary["added"] = len(adds)
    await log_action(
        bot,
        guild,
        kind_via("runs.imported", via),
        actor=actor,
        details={
            "from": "csv",
            "added": len(adds),
            "skipped": skipped,
            "need_match": need,
            "unreadable": bad,
            "via": via,
        },
    )
    return Outcome(
        True, IMPORT_SAID.format(added=len(adds), skipped=skipped, need=need), value=summary
    )


def tracker_ref(url: Any) -> str | None:
    found = read_url(url)
    if found is None or found[0] != GDQ:
        return None
    return found[1]


async def _already_here(db: Any, guild_id: int, refs: set[str]) -> set[str]:
    marks = ", ".join("?" for _ in refs)
    found: set[str] = set()
    for runs, marathons in (
        ("marathon_runs", "marathons"),
        ("marathon_runs_archive", "marathons_archive"),
    ):
        for row in await _fetch(
            db,
            f"SELECT r.external_id FROM {runs} r JOIN {marathons} m ON m.id = r.marathon_id "
            f"WHERE m.guild_id = ? AND m.source = ? AND m.source_ref IN ({marks})",
            (int(guild_id), GDQ, *refs),
        ):
            found.add(str(row["external_id"]))
    for row in await _fetch(
        db,
        f"SELECT run_ref FROM baf_runs WHERE guild_id = ? AND event_source = ? "
        f"AND event_ref IN ({marks}) AND run_ref IS NOT NULL",
        (int(guild_id), GDQ, *refs),
    ):
        found.add(str(row["run_ref"]))
    return found


def _client_of(bot: Any) -> tuple[Any, bool]:
    cog = bot.get_cog(MARATHONS_COG) if callable(getattr(bot, "get_cog", None)) else None
    found = getattr(cog, "client", None)
    return (found, False) if found is not None else (ScheduleClient(), True)


async def import_event(
    bot: Any,
    guild: Any,
    actor: Any,
    url: Any,
    *,
    dry_run: bool = True,
    pairs: dict[str, Any] | None = None,
    client: Any = None,
    now: datetime | None = None,
    via: str = VIA_DISCORD,
) -> Outcome:
    ref = tracker_ref(url)
    if ref is None:
        return refusal(NOT_A_TRACKER.format(given=clean(url, 120) or "(nothing)"), "not_gdq", 400)
    owned = False
    if client is None:
        client, owned = _client_of(bot)
    try:
        event_id, event_name = await client.resolve(GDQ, ref)
        runs = await client.runs(GDQ, event_id)
    except ScheduleError as exc:
        return refusal(TRACKER_DOWN.format(why=str(exc)), "tracker_unreadable", 502)
    finally:
        if owned:
            await client.close()
    moment = now or datetime.now(UTC)
    parts = set(bot.store.get(guild.id, RUNS_PARTS) or ())
    matcher = await _matcher(bot, guild, pairs)
    here = await _already_here(bot.db, guild.id, {str(event_id), str(ref)})
    adds: list[dict[str, Any]] = []
    unmatched: dict[str, dict[str, Any]] = {}
    skipped = 0
    later = 0
    for run in runs:
        people = matcher(run.people)
        for person in people:
            if (
                person.get("part") in parts
                and not person.get("user_id")
                and not person.get(mt.NOT_OURS)
            ):
                unmatched.setdefault(mt.runner_key(person["name"]), person)
        counted = counted_people(people, parts)
        if not counted:
            continue
        if run.starts_at is None or datetime.fromisoformat(run.starts_at) > moment:
            later += 1
            continue
        if str(run.external_id) in here:
            skipped += 1
            continue
        adds.append(
            {
                "event": event_name,
                "event_source": GDQ,
                "event_ref": str(event_id),
                "run_ref": str(run.external_id),
                "date": run.starts_at,
                "game": run.game,
                "category": run.category,
                "people": people,
            }
        )
    names = [
        {"name": person["name"], "suggest": _suggestion(person, matcher.usernames)}
        for person in sorted(unmatched.values(), key=lambda one: one["name"].lower())
    ]
    summary = {
        "dry_run": bool(dry_run),
        "would_add": len(adds),
        "added": 0,
        "skipped": skipped,
        "need_match": len(names),
        "unreadable": 0,
        "unmatched": names,
        "not_run_yet": later,
        "event": event_name,
        "event_ref": str(event_id),
        "runs_read": len(runs),
        "rows": [_preview(one, guild) for one in adds[:PREVIEW_LIMIT]],
    }
    words = {"event": event_name, "skipped": skipped, "need": len(names), "later": later}
    if dry_run:
        return Outcome(True, EVENT_DRY_SAID.format(would=len(adds), **words), value=summary)
    for one in adds:
        await _insert_imported(bot.db, guild.id, one, actor)
    await bot.db.conn.commit()
    summary["added"] = len(adds)
    await log_action(
        bot,
        guild,
        kind_via("runs.imported", via),
        actor=actor,
        details={
            "from": "gdq",
            "event": event_name,
            "event_ref": str(event_id),
            "added": len(adds),
            "skipped": skipped,
            "need_match": len(names),
            "not_run_yet": later,
            "pairs": sorted((pairs or {}).keys()),
            "via": via,
        },
    )
    return Outcome(True, EVENT_SAID.format(added=len(adds), **words), value=summary)


def _suggestion(person: dict[str, Any], usernames: dict[str, int]) -> dict[str, Any] | None:
    found = looks_like(person, usernames)
    if found is None:
        return None
    return {"username": found[0], "user_id": str(found[1])}


def export_csv(rows: list[dict[str, Any]]) -> str:
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(CSV_COLUMNS)
    for row in rows:
        if row["removed"]:
            continue
        writer.writerow(
            [
                row["key"],
                row["date"] or "",
                row["event"],
                row["event_source"] or "",
                row["event_ref"] or "",
                row["game"],
                row["series"],
                row["genre"],
                row["category"],
                row["runners_text"],
                "; ".join(one["name"] for one in row["runners"]),
                "; ".join(one["user_id"] or "" for one in row["runners"]),
                row["how"],
                row["note"],
            ]
        )
    return out.getvalue()


def text_of_game(game: dict[str, Any], rule: Rule = NO_RULE) -> str:
    return " ".join((game["genre"], genre_text(game, rule))).lower()


def page_url(origin: Any, query: Any = "") -> str | None:
    text = str(origin or "").strip()
    if not text:
        return None
    base = f"{text.rstrip('/')}/{RUNS_PAGE}"
    wanted = clean(query, 100)
    return f"{base}#q={quote(wanted)}" if wanted else base


async def lookup(
    bot: Any, guild: Any, actor: Any, query: Any, *, via: str = VIA_DISCORD
) -> list[dict[str, Any]]:
    wanted = game_key(query)
    every = await view(bot, guild)
    rule = genre_rule(bot, guild.id)
    found = [
        one
        for one in games(every)
        if wanted and (wanted in one["game_key"] or wanted in text_of_game(one, rule))
    ]
    rows = {row["key"]: row for row in every}
    answer: list[dict[str, Any]] = []
    for one in found[:LOOKUP_GAMES]:
        runs = [rows[key] for key in one["keys"] if key in rows]
        answer.append(one | {"runs": runs[:LOOKUP_RUNS], "more": max(0, len(runs) - LOOKUP_RUNS)})
    await log_action(
        bot,
        guild,
        kind_via("runs.lookup", via),
        actor=actor,
        details={"query": clean(query, 100), "games": len(found), "via": via},
    )
    return answer
