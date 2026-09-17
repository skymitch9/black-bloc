from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .logkinds import FEATURE_PAGES
from .settings_panel import CORE_CHANNEL_KEYS
from .settings_store import KEY_HELP, KEY_TYPES, display_value

log = logging.getLogger(__name__)

SEED_FILE = Path(__file__).with_name("guides_seed.json")
RELEASE_FILE = ("assets", "release.json")
MEDIA_DIR = "guides"

PAGE = "guides.html"
MEMBER = "member"
STAFF = "staff"
AUDIENCES = (MEMBER, STAFF)
SETTING = "setting"
PROBE = "probe"
FACT_KINDS = (SETTING, PROBE)
CAPTURE = "capture"
MOCK = "mock"
SOURCES = (CAPTURE, MOCK)
DISCORD = "discord"
WEBSITE = "website"
SURFACES = (DISCORD, WEBSITE)

FACTS_MAX = 4
STEPS_MAX = 40
FAULTS_MAX = 20
TITLE_MAX = 120
GOAL_MAX = 300
DO_MAX = 400
EXPECT_MAX = 600
SYMPTOM_MAX = 120
ANSWER_MAX = 400
CAPTION_MAX = 200
SLUG_MAX = 60
REASON_MAX = 200

MEDIA_BYTES_MAX = 2 * 1024 * 1024
MEDIA_SIDE_MAX = 1600
MEDIA_TYPES = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "webp": "image/webp",
}
MEDIA_CACHE = "private, max-age=86400"

LINT_ONE_ACTION = (
    "This step asks for more than one thing. Split it so each step is one press."
)
LINT_NAME_THE_CONTROL = (
    "No control is named. Write the button, select or menu item in **bold**, spelled the way "
    "Discord spells it."
)
LINT_IMPERATIVE = (
    "This step opens with **{word}**. Start with the verb — Press, Type, Pick — and say it "
    "straight."
)
LINT_DO_LONG = "This step is {count} characters. Keep it under {limit}."
LINT_EXPECT_LONG = "This expect line is {count} characters. Keep it under {limit}."
LINT_EXPECT_OBSERVABLE = (
    "The expect line starts with **{word}**. Say what is on the screen — The panel…, A card…, "
    "Your name… — rather than what should happen."
)
LINT_EASE = "**{word}** tells nobody anything. Say what to press instead."
LINT_PROMISE = (
    "**{word}** is a promise rather than a fact. Say what happens, and when it does not."
)

EASE_WORDS = ("easy", "simple", "quick", "intuitive")
PROMISE_WORDS = ("always", "never fails", "instantly")
OPENERS = ("You can", "Simply", "Just", "Easily", "Please")
UNOBSERVABLE = ("It should", "It will", "This should", "There should", "You will")
BOLD = re.compile(r"\*\*(.+?)\*\*", re.DOTALL)
AND_THEN = re.compile(r"\s+(and\s+then|then)\s+")
SLUG_SHAPE = re.compile(r"[^a-z0-9-]+")
RELEASE_IN_LOG = re.compile(r"\bv(\d+)\b")
DEPLOY_MARKER = "by=deploy.ps1"

NO_SUCH_GUIDE = (
    "There is no guide called **{slug}**, so nothing was done. It may have been renamed — open "
    "the guides page and pick it from the list."
)
GUIDES_OFF = (
    "Guides are turned off for this server, so there is nothing to show. A Lead turns them back "
    "on from the dashboard's Settings page under **guides**."
)
NOT_YOURS_TO_EDIT = (
    "Editing a guide needs Manage Server on this server, and your account does not hold it, so "
    "nothing was saved. Ask a Lead to make the change, or to set **guides_who_edits** back to "
    "staff."
)
SEEDED_CANNOT_BE_DELETED = (
    "**{slug}** is one of the guides Black Bloc ships with, so it cannot be deleted — a deploy "
    "would only put it back. Press **Unpublish** instead: members and `/help` stop seeing it and "
    "every word you have written is kept."
)
SLUG_TAKEN = (
    "There is already a guide at **{slug}**, so nothing was made. Give this one a different "
    "title, or edit the one that is there."
)
SLUG_NEEDED = (
    "A guide needs a title Black Bloc can turn into a web address, and that one came out empty, "
    "so nothing was made. Use some letters or numbers in the title."
)
TITLE_NEEDED = (
    "A guide needs a title and a goal, so nothing was saved. Fill both in and save again."
)
STEP_NEEDS_TEXT = (
    "Step {position} has nothing in it, so nothing was saved. Write what to do, or remove the "
    "step with ×."
)
TOO_MANY_FACTS = (
    "A guide shows at most {limit} live values, and that one asked for {count}, so nothing was "
    "saved. Take one off and save again."
)
NO_SUCH_SETTING = (
    "**{ref}** is not one of Black Bloc's settings, so nothing was saved. Pick a setting from "
    "the list beside the box."
)
SETTING_IS_PRIVATE = (
    "**{ref}** is not a value a guide may show: it is one of the keys that decide who counts as "
    "staff, and the Settings panel keeps those for a Lead. Nothing was saved — pick another "
    "setting."
)
SETTING_IS_A_LOG_LEVEL = (
    "**{ref}** only decides how much of a feature is repeated into the Discord log, which is "
    "nothing a member can act on, so a guide will not show it. Nothing was saved."
)
NO_SUCH_PROBE = (
    "**{ref}** is not one of the live values Black Bloc can read, so nothing was saved. The ones "
    "it has are: {known}."
)
COMMAND_TAKEN = (
    "**{command}** already has a published guide (**{slug}**), and `/help` can only link to one, "
    "so this one was left unpublished. Unpublish that guide first, or leave this one's command "
    "blank."
)
MEDIA_TOO_BIG = (
    "That picture is {size} and Black Bloc keeps guide screenshots under {limit}. Nothing was "
    "uploaded — crop it, or save it again as a PNG at no more than {side} pixels on its longest "
    "side."
)
MEDIA_WRONG_TYPE = (
    "**{name}** is not a picture Black Bloc can serve. Nothing was uploaded — send a PNG, a JPEG "
    "or a WebP."
)
MEDIA_UNREADABLE = (
    "That upload did not arrive as a picture Black Bloc could read, so nothing was uploaded. It "
    "is a fault in the page rather than in the file — reload the guide and try again."
)
MEDIA_TOO_WIDE = (
    "That picture is {side} pixels on its longest side and Black Bloc keeps guide screenshots "
    "under {limit}. Nothing was uploaded — Black Bloc cannot resize it for you, so crop or "
    "export it smaller and send it again."
)
NO_SUCH_MEDIA = (
    "That picture is not one of this server's guide screenshots, so nothing was shown. It may "
    "have been replaced — reload the guide."
)

FEATURE_PATHS: dict[str, tuple[str, ...]] = {
    "core": (
        "black_bloc/cogs/core.py",
        "black_bloc/settings_panel.py",
        "site/public/settings.html",
    ),
    "automod": (
        "black_bloc/automod.py",
        "black_bloc/cogs/moderation/automod.py",
        "black_bloc/api/tools/mod.py",
        "site/public/automod.html",
        "site/public/assets/page-automod.js",
    ),
    "honeypot": (
        "black_bloc/honeypot.py",
        "black_bloc/cogs/moderation/honeypot.py",
        "black_bloc/api/tools/honeypot.py",
        "site/public/honeypot.html",
        "site/public/assets/page-honeypot.js",
    ),
    "mod": (
        "black_bloc/modcases.py",
        "black_bloc/cogs/moderation/mod.py",
        "black_bloc/api/tools/mod.py",
        "site/public/moderation.html",
        "site/public/assets/page-moderation.js",
    ),
    "modmail": (
        "black_bloc/modmail.py",
        "black_bloc/cogs/moderation/modmail.py",
        "black_bloc/api/tools/modmail.py",
        "site/public/modmail.html",
        "site/public/assets/page-modmail.js",
    ),
    "golive": (
        "black_bloc/golive.py",
        "black_bloc/cogs/content/golive.py",
        "black_bloc/api/tools/golive.py",
        "site/public/golive.html",
        "site/public/assets/page-golive.js",
    ),
    "youtube": (
        "black_bloc/youtube.py",
        "black_bloc/cogs/content/youtube.py",
        "black_bloc/api/tools/youtube.py",
    ),
    "events": (
        "black_bloc/events.py",
        "black_bloc/cogs/community/events.py",
        "black_bloc/api/tools/events.py",
        "site/public/events.html",
        "site/public/assets/page-events.js",
    ),
    "birthday": (
        "black_bloc/cogs/community/birthdays.py",
        "black_bloc/api/tools/birthdays.py",
        "site/public/birthdays.html",
        "site/public/assets/page-birthdays.js",
    ),
    "tempvoice": (
        "black_bloc/tempvoice.py",
        "black_bloc/cogs/community/tempvoice.py",
        "black_bloc/api/tools/tempvoice.py",
        "site/public/tempvoice.html",
        "site/public/assets/page-tempvoice.js",
    ),
    "rolemenu": (
        "black_bloc/rolemenus.py",
        "black_bloc/rolemenu_panels.py",
        "black_bloc/cogs/community/role_menus.py",
        "black_bloc/api/tools/rolemenus.py",
        "site/public/rolemenus.html",
        "site/public/assets/page-rolemenus.js",
    ),
    "poll": (
        "black_bloc/polls.py",
        "black_bloc/cogs/community/polls.py",
        "black_bloc/api/tools/polls.py",
        "site/public/polls.html",
        "site/public/assets/page-polls.js",
    ),
    "chat": (
        "black_bloc/chat.py",
        "black_bloc/chat_panel.py",
        "black_bloc/cogs/content/chat.py",
        "black_bloc/api/tools/chat.py",
        "site/public/chat.html",
        "site/public/assets/page-chat.js",
    ),
    "request": (
        "black_bloc/requests.py",
        "black_bloc/cogs/community/requests.py",
        "black_bloc/api/tools/requests.py",
        "site/public/requests.html",
        "site/public/assets/page-requests.js",
    ),
    "pings": (
        "black_bloc/pings.py",
        "black_bloc/cogs/content/pings.py",
        "black_bloc/api/tools/pings.py",
    ),
    "raidtrain": (
        "black_bloc/raidtrain.py",
        "black_bloc/cogs/content/raidtrain.py",
        "black_bloc/api/tools/raidtrain.py",
    ),
    "applications": (
        "black_bloc/applications.py",
        "black_bloc/cogs/community/applications.py",
        "black_bloc/api/tools/applications.py",
    ),
    "selftest": ("black_bloc/selftest.py", "black_bloc/selftest_panels.py"),
    "posts": (
        "black_bloc/posts.py",
        "black_bloc/posts_seed.json",
        "black_bloc/cogs/community/posts.py",
        "black_bloc/api/tools/posts.py",
        "site/public/posts.html",
        "site/public/assets/page-posts.js",
        "site/public/assets/discordmd.js",
    ),
    "guides": (
        "black_bloc/guides.py",
        "black_bloc/guides_seed.json",
        "black_bloc/api/tools/guides.py",
        "site/public/guides.html",
        "site/public/assets/page-guides.js",
    ),
}


def now() -> str:
    return datetime.now(UTC).isoformat()


def slugify(text: Any) -> str:
    """The URL and the `/help` link target, from the title a staffer typed."""
    lowered = str(text or "").strip().lower().replace("’", "").replace("'", "")
    return SLUG_SHAPE.sub("-", lowered).strip("-")[:SLUG_MAX].strip("-")


def clamp(value: Any, limit: int) -> str:
    return str(value or "").strip()[:limit]


def features() -> tuple[str, ...]:
    return tuple(FEATURE_PAGES)


def features_changed(paths: Any) -> list[str]:
    """Which features a list of changed file paths touches, so a deploy can write it down."""
    found: list[str] = []
    wanted = [str(one or "").replace("\\", "/").lstrip("./") for one in paths or ()]
    for feature, prefixes in FEATURE_PATHS.items():
        if any(path.startswith(prefix) for path in wanted for prefix in prefixes):
            found.append(feature)
    return sorted(found)


def release_order(release: Any) -> tuple[int, str]:
    """`v112` after `v110`; anything without digits falls back to its own text."""
    text = str(release or "")
    digits = re.findall(r"\d+", text)
    return (int(digits[0]) if digits else -1, text)


def release_before(older: Any, newer: Any) -> bool:
    if not str(older or ""):
        return True
    return release_order(older) < release_order(newer)


# --- the wording rules ------------------------------------------------------------------------


def lint_step(do_text: Any, expect_text: Any = None) -> list[str]:
    """§C2, warn-only: staff have the final say, so this never refuses a save."""
    said: list[str] = []
    do = str(do_text or "").strip()
    expect = str(expect_text or "").strip()
    bolds = BOLD.findall(do)
    if AND_THEN.search(do):
        said.append(LINT_ONE_ACTION)
    if not bolds:
        said.append(LINT_NAME_THE_CONTROL)
    for word in OPENERS:
        if do.lower().startswith(word.lower()):
            said.append(LINT_IMPERATIVE.format(word=word))
            break
    if len(do) > 140:
        said.append(LINT_DO_LONG.format(count=len(do), limit=140))
    if len(expect) > 200:
        said.append(LINT_EXPECT_LONG.format(count=len(expect), limit=200))
    for word in UNOBSERVABLE:
        if expect.lower().startswith(word.lower()):
            said.append(LINT_EXPECT_OBSERVABLE.format(word=word))
            break
    both = f"{do}\n{expect}".lower()
    for word in EASE_WORDS:
        if re.search(rf"\b{word}\b", both):
            said.append(LINT_EASE.format(word=word))
    for word in PROMISE_WORDS:
        if re.search(rf"\b{word}\b", both):
            said.append(LINT_PROMISE.format(word=word))
    return said


def lint_steps(steps: Any) -> dict[int, list[str]]:
    return {
        int(step["position"]): lint_step(step.get("do_text"), step.get("expect_text"))
        for step in steps or ()
    }


# --- the live values --------------------------------------------------------------------------


def refused_setting(ref: str) -> str | None:
    if ref not in KEY_TYPES:
        return NO_SUCH_SETTING.format(ref=ref)
    if ref in CORE_CHANNEL_KEYS:
        return SETTING_IS_PRIVATE.format(ref=ref)
    if ref.endswith("_log_level"):
        return SETTING_IS_A_LOG_LEVEL.format(ref=ref)
    return None


def named_value(guild: Any, shown: str) -> str:
    """`<#500>` and `<@&11>` become the names the guild cache already holds, never a fetch."""
    from .api.names import resolve_one

    def swap(match: re.Match[str]) -> str:
        found = resolve_one(guild, match.group(2))
        name = found["display_name"]
        if not name:
            return match.group(0)
        return name if match.group(1) == "#" else f"@{name}"

    return re.sub(r"<(#|@&)(\d+)>", swap, shown)


def setting_fact(bot: Any, guild: Any, ref: str) -> dict[str, Any]:
    value = bot.store.get(guild.id, ref)
    return {
        "kind": SETTING,
        "ref": ref,
        "label": ref,
        "value": named_value(guild, display_value(ref, value)),
        "help": KEY_HELP.get(ref, ""),
    }


async def probe_golive_linked(bot: Any, guild: Any) -> str:
    from .cogs.content.golive import counts

    return f"{(await counts(bot.db, guild.id))['links']} linked"


async def probe_golive_live(bot: Any, guild: Any) -> str:
    from .cogs.content.golive import counts

    return f"{(await counts(bot.db, guild.id))['open_sessions']} live now"


async def probe_events_open(bot: Any, guild: Any) -> str:
    from .api.status import open_counts

    found = await open_counts(bot, guild.id)
    return "not readable" if found is None else f"{found['open_events']} waiting"


async def probe_requests_open(bot: Any, guild: Any) -> str:
    from .requests import OPEN, count_requests

    return f"{await count_requests(bot.db, guild.id, statuses=(OPEN,))} open"


async def probe_tempvoice_rooms(bot: Any, guild: Any) -> str:
    from .api.status import open_counts

    found = await open_counts(bot, guild.id)
    return "not readable" if found is None else f"{found['temp_channels']} open"


async def probe_polls_open(bot: Any, guild: Any) -> str:
    from .cogs.community.polls import polls_by_status
    from .polls import OPEN_STATUSES

    return f"{len(await polls_by_status(bot.db, guild.id, OPEN_STATUSES))} open"


async def probe_birthdays_next(bot: Any, guild: Any) -> str:
    from .cogs.community.birthdays import next_lines

    lines = [line for line in await next_lines(bot, guild) if line.strip()]
    return lines[-1] if len(lines) > 1 else (lines[0] if lines else "none stored")


async def probe_raidtrain_next(bot: Any, guild: Any) -> str:
    from .cogs.content.raidtrain import counts

    found = await counts(bot.db, guild.id)
    return f"{found['upcoming']} upcoming, {found['claimed']} of {found['slots']} hours taken"


async def probe_test_mode(bot: Any, guild: Any) -> str:
    if not bot.settings.test_mode:
        return "off"
    channel = guild.get_channel(bot.settings.test_channel_id)
    where = getattr(channel, "name", None)
    return f"on — #{where}" if where else "on"


PROBES: dict[str, Any] = {
    "golive.linked_count": probe_golive_linked,
    "golive.live_now": probe_golive_live,
    "events.open_count": probe_events_open,
    "requests.open_count": probe_requests_open,
    "tempvoice.open_rooms": probe_tempvoice_rooms,
    "polls.open_count": probe_polls_open,
    "birthdays.next": probe_birthdays_next,
    "raidtrain.next": probe_raidtrain_next,
    "test_mode": probe_test_mode,
}

PROBE_LABELS: dict[str, str] = {
    "golive.linked_count": "Twitch channels linked",
    "golive.live_now": "Streaming right now",
    "events.open_count": "Events waiting on staff",
    "requests.open_count": "Requests still open",
    "tempvoice.open_rooms": "Voice rooms open",
    "polls.open_count": "Polls open",
    "birthdays.next": "The next birthday",
    "raidtrain.next": "Raid trains",
    "test_mode": "Test mode",
}


def refused_probe(ref: str) -> str | None:
    if ref in PROBES:
        return None
    return NO_SUCH_PROBE.format(ref=ref, known=", ".join(sorted(PROBES)))


def refused_fact(kind: str, ref: str) -> str | None:
    if kind == SETTING:
        return refused_setting(ref)
    return refused_probe(ref)


async def probe_fact(bot: Any, guild: Any, ref: str) -> dict[str, Any]:
    reader = PROBES.get(ref)
    label = PROBE_LABELS.get(ref, ref)
    if reader is None:
        return {"kind": PROBE, "ref": ref, "label": label, "value": "not readable", "help": ""}
    try:
        value = str(await reader(bot, guild))
    except Exception as exc:
        log.warning("guides: the %s probe failed — %s: %s", ref, type(exc).__name__, exc)
        value = "not readable"
    return {"kind": PROBE, "ref": ref, "label": label, "value": value, "help": ""}


async def resolve_facts(bot: Any, guild: Any, rows: Any) -> list[dict[str, Any]]:
    """Every fact a guide carries, read server-side; a refused key is dropped, never guessed."""
    found: list[dict[str, Any]] = []
    for row in rows or ():
        kind, ref = str(row["kind"]), str(row["ref"])
        if kind == SETTING:
            if refused_setting(ref) is not None:
                continue
            found.append(setting_fact(bot, guild, ref))
        else:
            found.append(await probe_fact(bot, guild, ref))
    at = now()
    for one in found:
        one["read_at"] = at
    return found


# --- the rows ---------------------------------------------------------------------------------


def _value(row: Any, key: str, fallback: Any = None) -> Any:
    try:
        return row[key]
    except (IndexError, KeyError, TypeError):
        return fallback


async def count_guides(db: Any, guild_id: int) -> int:
    cur = await db.conn.execute(
        "SELECT COUNT(*) AS n FROM guides WHERE guild_id = ?", (int(guild_id),)
    )
    row = await cur.fetchone()
    return int(row["n"]) if row else 0


async def list_guides(db: Any, guild_id: int) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT * FROM guides WHERE guild_id = ? ORDER BY sort, id", (int(guild_id),)
    )
    return list(await cur.fetchall())


async def get_guide(db: Any, guild_id: int, slug: str) -> Any:
    cur = await db.conn.execute(
        "SELECT * FROM guides WHERE guild_id = ? AND slug = ?", (int(guild_id), str(slug))
    )
    return await cur.fetchone()


async def get_guide_by_id(db: Any, guide_id: int) -> Any:
    cur = await db.conn.execute("SELECT * FROM guides WHERE id = ?", (int(guide_id),))
    return await cur.fetchone()


async def steps_of(db: Any, guide_id: int) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT * FROM guide_steps WHERE guide_id = ? ORDER BY position, id", (int(guide_id),)
    )
    return list(await cur.fetchall())


async def faults_of(db: Any, guide_id: int) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT * FROM guide_faults WHERE guide_id = ? ORDER BY position, id", (int(guide_id),)
    )
    return list(await cur.fetchall())


async def facts_of(db: Any, guide_id: int) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT * FROM guide_facts WHERE guide_id = ? ORDER BY position, id", (int(guide_id),)
    )
    return list(await cur.fetchall())


async def media_of(db: Any, guide_id: int) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT * FROM guide_media WHERE guide_id = ? ORDER BY id", (int(guide_id),)
    )
    return list(await cur.fetchall())


async def get_media(db: Any, guild_id: int, media_id: int) -> Any:
    cur = await db.conn.execute(
        "SELECT * FROM guide_media WHERE id = ? AND guild_id = ?",
        (int(media_id), int(guild_id)),
    )
    return await cur.fetchone()


async def stale_media(db: Any, guild_id: int) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT m.*, g.slug AS slug, g.title AS title, g.feature AS feature FROM guide_media m "
        "JOIN guides g ON g.id = m.guide_id WHERE m.guild_id = ? AND m.stale = 1 "
        "ORDER BY m.stale_since, m.id",
        (int(guild_id),),
    )
    return list(await cur.fetchall())


async def published_for(db: Any, guild_id: int, command: str, audience: str = MEMBER) -> Any:
    cur = await db.conn.execute(
        "SELECT * FROM guides WHERE guild_id = ? AND command = ? AND audience = ? "
        "AND published = 1",
        (int(guild_id), str(command), str(audience)),
    )
    return await cur.fetchone()


async def create_guide(
    db: Any,
    guild_id: int,
    *,
    slug: str,
    title: str,
    goal: str,
    audience: str = MEMBER,
    feature: str = "core",
    command: Any = None,
    sort: int = 0,
    published: bool = False,
    seed_hash: Any = None,
    by: int | None = None,
) -> int:
    cur = await db.conn.execute(
        "INSERT INTO guides(guild_id, slug, title, goal, audience, feature, command, sort, "
        "published, seed_hash, updated_at, updated_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            int(guild_id),
            str(slug),
            str(title),
            str(goal),
            audience if audience in AUDIENCES else MEMBER,
            str(feature),
            str(command) if command else None,
            int(sort),
            1 if published else 0,
            seed_hash,
            now(),
            by,
        ),
    )
    await db.conn.commit()
    return int(cur.lastrowid)


async def delete_guide(db: Any, guide_id: int) -> None:
    await db.conn.execute("DELETE FROM guides WHERE id = ?", (int(guide_id),))
    await db.conn.commit()


async def set_guide_fields(db: Any, guide_id: int, *, by: int | None = None, **fields: Any) -> None:
    columns = [name for name in fields if fields[name] is not ...]
    if not columns:
        return
    sets = ", ".join(f"{name} = ?" for name in columns)
    await db.conn.execute(
        f"UPDATE guides SET {sets}, updated_at = ?, updated_by = ? WHERE id = ?",
        (*[fields[name] for name in columns], now(), by, int(guide_id)),
    )
    await db.conn.commit()


async def put_steps(db: Any, guide_id: int, steps: list[dict[str, Any]]) -> dict[str, int]:
    """The whole list at once, the way `PUT /api/rolemenus/{name}` takes its options."""
    before = {int(row["id"]): row for row in await steps_of(db, guide_id)}
    kept: set[int] = set()
    added = changed = 0
    for position, step in enumerate(steps, start=1):
        step_id = step.get("id")
        found = before.get(int(step_id)) if step_id else None
        do_text, expect = step["do_text"], step.get("expect_text")
        media_id = step.get("media_id")
        if found is None:
            cur = await db.conn.execute(
                "INSERT INTO guide_steps(guide_id, position, do_text, expect_text, media_id, "
                "seed_do, seed_expect) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (int(guide_id), position, do_text, expect, media_id, None, None),
            )
            kept.add(int(cur.lastrowid))
            added += 1
            continue
        kept.add(int(found["id"]))
        same = (
            found["do_text"] == do_text
            and found["expect_text"] == expect
            and int(found["position"]) == position
            and _value(found, "media_id") == media_id
        )
        if same:
            continue
        await db.conn.execute(
            "UPDATE guide_steps SET position = ?, do_text = ?, expect_text = ?, media_id = ? "
            "WHERE id = ?",
            (position, do_text, expect, media_id, int(found["id"])),
        )
        changed += 1
    gone = [one for one in before if one not in kept]
    for step_id in gone:
        await db.conn.execute("DELETE FROM guide_steps WHERE id = ?", (step_id,))
        await db.conn.execute(
            "UPDATE guide_media SET step_id = NULL WHERE step_id = ?", (step_id,)
        )
    await db.conn.commit()
    return {"added": added, "removed": len(gone), "changed": changed}


async def put_faults(db: Any, guide_id: int, faults: list[dict[str, Any]]) -> dict[str, int]:
    before = await faults_of(db, guide_id)
    await db.conn.execute("DELETE FROM guide_faults WHERE guide_id = ?", (int(guide_id),))
    for position, fault in enumerate(faults, start=1):
        await db.conn.execute(
            "INSERT INTO guide_faults(guide_id, position, symptom, answer) VALUES (?, ?, ?, ?)",
            (int(guide_id), position, fault["symptom"], fault["answer"]),
        )
    await db.conn.commit()
    return _moved(len(before), len(faults), before, faults, ("symptom", "answer"))


async def put_facts(db: Any, guide_id: int, facts: list[dict[str, Any]]) -> dict[str, int]:
    before = await facts_of(db, guide_id)
    await db.conn.execute("DELETE FROM guide_facts WHERE guide_id = ?", (int(guide_id),))
    for position, fact in enumerate(facts, start=1):
        await db.conn.execute(
            "INSERT INTO guide_facts(guide_id, position, kind, ref) VALUES (?, ?, ?, ?)",
            (int(guide_id), position, fact["kind"], fact["ref"]),
        )
    await db.conn.commit()
    return _moved(len(before), len(facts), before, facts, ("kind", "ref"))


def _moved(
    was: int, is_now: int, before: Any, after: Any, fields: tuple[str, ...]
) -> dict[str, int]:
    same = 0
    for old, new in zip(before, after, strict=False):
        if all(old[name] == new[name] for name in fields):
            same += 1
    return {
        "added": max(0, is_now - was),
        "removed": max(0, was - is_now),
        "changed": min(was, is_now) - same,
    }


def diff_summary(steps: dict[str, int], faults: dict[str, int], facts: dict[str, int]) -> str:
    return (
        f"steps +{steps['added']} −{steps['removed']} ~{steps['changed']}, "
        f"faults +{faults['added']} −{faults['removed']} ~{faults['changed']}, "
        f"facts +{facts['added']} −{facts['removed']} ~{facts['changed']}"
    )


# --- the seed ---------------------------------------------------------------------------------


def load_seed() -> dict[str, Any]:
    try:
        return json.loads(SEED_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        log.warning("guides: the seed could not be read — %s: %s", type(exc).__name__, exc)
        return {"version": 0, "guides": []}


def seed_entries() -> list[dict[str, Any]]:
    return list(load_seed().get("guides") or ())


def seed_hash(entry: dict[str, Any]) -> str:
    body = json.dumps(entry, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


async def seed_one(db: Any, guild_id: int, entry: dict[str, Any]) -> int:
    guide_id = await create_guide(
        db,
        guild_id,
        slug=entry["slug"],
        title=entry["title"],
        goal=entry["goal"],
        audience=entry.get("audience", MEMBER),
        feature=entry.get("feature", "core"),
        command=entry.get("command"),
        sort=int(entry.get("sort", 0)),
        published=True,
        seed_hash=seed_hash(entry),
    )
    for position, step in enumerate(entry.get("steps") or (), start=1):
        await db.conn.execute(
            "INSERT INTO guide_steps(guide_id, position, do_text, expect_text, seed_do, "
            "seed_expect) VALUES (?, ?, ?, ?, ?, ?)",
            (guide_id, position, step["do"], step.get("expect"), step["do"], step.get("expect")),
        )
    for position, fault in enumerate(entry.get("faults") or (), start=1):
        await db.conn.execute(
            "INSERT INTO guide_faults(guide_id, position, symptom, answer) VALUES (?, ?, ?, ?)",
            (guide_id, position, fault["symptom"], fault["answer"]),
        )
    for position, fact in enumerate((entry.get("facts") or ())[:FACTS_MAX], start=1):
        await db.conn.execute(
            "INSERT INTO guide_facts(guide_id, position, kind, ref) VALUES (?, ?, ?, ?)",
            (guide_id, position, fact["kind"], fact["ref"]),
        )
    await db.conn.commit()
    return guide_id


async def seed_guides(db: Any, guild_id: int) -> int:
    """Once per guild, when there is no guide at all; a later deploy never comes back here."""
    made = 0
    for entry in seed_entries():
        if await get_guide(db, guild_id, entry["slug"]) is not None:
            continue
        await seed_one(db, guild_id, entry)
        made += 1
    return made


async def refresh_seeds(db: Any, guild_id: int) -> int:
    """What **Put the original back** restores, brought up to the shipped seed. Staff text is
    never touched."""
    changed = 0
    for entry in seed_entries():
        guide = await get_guide(db, guild_id, entry["slug"])
        if guide is None:
            continue
        fresh = seed_hash(entry)
        if _value(guide, "seed_hash") == fresh:
            continue
        steps = await steps_of(db, int(guide["id"]))
        seeds = entry.get("steps") or []
        for step, seed in zip(steps, seeds, strict=False):
            await db.conn.execute(
                "UPDATE guide_steps SET seed_do = ?, seed_expect = ? WHERE id = ?",
                (seed["do"], seed.get("expect"), int(step["id"])),
            )
        await db.conn.execute(
            "UPDATE guides SET seed_hash = ? WHERE id = ?", (fresh, int(guide["id"]))
        )
        changed += 1
    await db.conn.commit()
    return changed


def is_seeded(guide: Any) -> bool:
    return bool(_value(guide, "seed_hash"))


async def reset_to_seed(db: Any, guild_id: int, guide: Any) -> bool:
    """The whole guide back to the words it shipped with; only a seeded guide has any."""
    entry = next((one for one in seed_entries() if one["slug"] == guide["slug"]), None)
    if entry is None:
        return False
    guide_id = int(guide["id"])
    await db.conn.execute("DELETE FROM guide_steps WHERE guide_id = ?", (guide_id,))
    await db.conn.execute("DELETE FROM guide_faults WHERE guide_id = ?", (guide_id,))
    await db.conn.execute("DELETE FROM guide_facts WHERE guide_id = ?", (guide_id,))
    await db.conn.execute("UPDATE guide_media SET step_id = NULL WHERE guide_id = ?", (guide_id,))
    for position, step in enumerate(entry.get("steps") or (), start=1):
        await db.conn.execute(
            "INSERT INTO guide_steps(guide_id, position, do_text, expect_text, seed_do, "
            "seed_expect) VALUES (?, ?, ?, ?, ?, ?)",
            (guide_id, position, step["do"], step.get("expect"), step["do"], step.get("expect")),
        )
    for position, fault in enumerate(entry.get("faults") or (), start=1):
        await db.conn.execute(
            "INSERT INTO guide_faults(guide_id, position, symptom, answer) VALUES (?, ?, ?, ?)",
            (guide_id, position, fault["symptom"], fault["answer"]),
        )
    for position, fact in enumerate((entry.get("facts") or ())[:FACTS_MAX], start=1):
        await db.conn.execute(
            "INSERT INTO guide_facts(guide_id, position, kind, ref) VALUES (?, ?, ?, ?)",
            (guide_id, position, fact["kind"], fact["ref"]),
        )
    await db.conn.execute(
        "UPDATE guides SET title = ?, goal = ?, audience = ?, feature = ?, command = ?, "
        "sort = ?, seed_hash = ?, updated_at = ? WHERE id = ?",
        (
            entry["title"],
            entry["goal"],
            entry.get("audience", MEMBER),
            entry.get("feature", "core"),
            entry.get("command"),
            int(entry.get("sort", 0)),
            seed_hash(entry),
            now(),
            guide_id,
        ),
    )
    await db.conn.commit()
    return True


# --- releases and staleness -------------------------------------------------------------------


def next_release(line: Any) -> str | None:
    """`v110` in the last `deploys.log` line makes this deploy `v111`; no number, no guess."""
    text = str(line or "")
    _, marker, after = text.partition(DEPLOY_MARKER)
    found = RELEASE_IN_LOG.search(after if marker else text)
    return f"v{int(found.group(1)) + 1}" if found else None


def release_payload(paths: Any, release: Any, commit: Any) -> dict[str, Any]:
    """What `scripts/deploy.ps1` writes to `release.json` before it ships (§C4.2)."""
    return {
        "release": str(release or commit),
        "commit": str(commit),
        "changed_features": features_changed(paths),
    }


def release_path(bot: Any) -> Path:
    return Path(bot.settings.site_root).joinpath(*RELEASE_FILE)


def read_release(bot: Any) -> dict[str, Any] | None:
    """Absent is the normal case until the deploy writes one; absent means do nothing."""
    path = release_path(bot)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as exc:
        log.warning("guides: %s could not be read — %s: %s", path, type(exc).__name__, exc)
        return None
    if not isinstance(payload, dict) or not str(payload.get("release") or ""):
        return None
    return payload


async def known_release(db: Any, release: str) -> bool:
    cur = await db.conn.execute(
        "SELECT release FROM guide_releases WHERE release = ?", (str(release),)
    )
    return await cur.fetchone() is not None


async def record_release(db: Any, payload: dict[str, Any]) -> None:
    await db.conn.execute(
        'INSERT OR REPLACE INTO guide_releases(release, "commit", shipped_at, changed_features) '
        "VALUES (?, ?, ?, ?)",
        (
            str(payload["release"]),
            str(payload.get("commit") or "") or None,
            now(),
            json.dumps(sorted(str(one) for one in payload.get("changed_features") or ())),
        ),
    )
    await db.conn.commit()


async def mark_stale(db: Any, guild_id: int, release: str, wanted: list[str]) -> int:
    if not wanted:
        return 0
    marks = ", ".join("?" for _ in wanted)
    cur = await db.conn.execute(
        "SELECT m.id AS id, m.shot_release AS shot_release FROM guide_media m "
        "JOIN guides g ON g.id = m.guide_id "
        f"WHERE m.guild_id = ? AND m.stale = 0 AND g.feature IN ({marks})",
        (int(guild_id), *wanted),
    )
    rows = [row for row in await cur.fetchall() if release_before(row["shot_release"], release)]
    at = now()
    for row in rows:
        await db.conn.execute(
            "UPDATE guide_media SET stale = 1, stale_since = ? WHERE id = ?", (at, int(row["id"]))
        )
    await db.conn.commit()
    return len(rows)


async def mark_all_stale(db: Any, guild_id: int) -> int:
    """Every picture in the guild, whatever feature or release it belongs to."""
    cur = await db.conn.execute(
        "SELECT id FROM guide_media WHERE guild_id = ? AND stale = 0", (int(guild_id),)
    )
    rows = list(await cur.fetchall())
    at = now()
    for row in rows:
        await db.conn.execute(
            "UPDATE guide_media SET stale = 1, stale_since = ? WHERE id = ?", (at, int(row["id"]))
        )
    await db.conn.commit()
    return len(rows)


async def reconcile_releases(bot: Any) -> dict[str, Any] | None:
    """§C4.3 — one `guide.shots_stale` row per release, and nothing at all without the file."""
    db = getattr(bot, "db", None)
    if db is None or not getattr(db, "is_connected", False):
        return None
    payload = read_release(bot)
    if payload is None:
        return None
    release = str(payload["release"])
    if await known_release(db, release):
        return None
    wanted = sorted({str(one) for one in payload.get("changed_features") or ()})
    await record_release(db, payload)
    counts: dict[int, int] = {}
    for guild in list(getattr(bot, "guilds", ()) or ()):
        counts[int(guild.id)] = await mark_stale(db, guild.id, release, wanted)
    return {
        "release": release,
        "features": wanted,
        "counts": counts,
        "count": sum(counts.values()),
    }


# --- what `/help` links to --------------------------------------------------------------------


def guides_on(store: Any, guild_id: int) -> bool:
    return str(store.get(guild_id, "guides_mode")) == "on"


def help_links_on(store: Any, guild_id: int) -> bool:
    return bool(store.get(guild_id, "guides_help_links"))


def feature_mode(store: Any, guild_id: int, feature: str) -> str | None:
    """The mode pill a guide card wears. A feature with no `_mode` key has none."""
    key = f"{feature}_mode"
    if key not in KEY_TYPES:
        return None
    value = store.get(guild_id, key)
    return None if value is None else str(value)


def fault_files_request(store: Any, guild_id: int) -> bool:
    return bool(store.get(guild_id, "guides_fault_files_request"))


def right_now(bot: Any, guild: Any) -> dict[str, Any]:
    """The hub's fixed strip. `/api/status` is staff-only, so the hub reads it from here."""
    from .api.status import feature_modes

    on = shadow = off = 0
    for row in feature_modes(bot.store, guild.id):
        mode = str(row["mode"] or "")
        if mode == "shadow":
            shadow += 1
        elif mode == "off":
            off += 1
        else:
            on += 1
    testing = bool(getattr(bot.settings, "test_mode", False))
    channel = guild.get_channel(bot.settings.test_channel_id) if testing else None
    return {
        "test_mode": testing,
        "test_channel": getattr(channel, "name", None),
        "on": on,
        "shadow": shadow,
        "off": off,
    }


def guide_url(origin: str, slug: str) -> str:
    return f"{str(origin).rstrip('/')}/{PAGE}#{slug}"


def hub_url(origin: str) -> str:
    return f"{str(origin).rstrip('/')}/{PAGE}"


async def links_for(bot: Any, guild_id: int) -> dict[str, str]:
    """Command name → guide url, for the published guides only; empty when guides are off."""
    db = getattr(bot, "db", None)
    if db is None or not getattr(db, "is_connected", False):
        return {}
    store = getattr(bot, "store", None)
    if store is None or not guides_on(store, guild_id):
        return {}
    origin = getattr(getattr(bot, "settings", None), "origin", "")
    if not origin:
        return {}
    cur = await db.conn.execute(
        "SELECT command, slug FROM guides WHERE guild_id = ? AND published = 1 "
        "AND command IS NOT NULL AND audience = ? ORDER BY sort, id",
        (int(guild_id), MEMBER),
    )
    return {
        str(row["command"]): guide_url(origin, str(row["slug"]))
        for row in await cur.fetchall()
    }


# --- media on disk ----------------------------------------------------------------------------


def media_root(bot: Any) -> Path:
    return Path(bot.settings.database_path).parent / MEDIA_DIR


def media_path(bot: Any, file: str) -> Path:
    return media_root(bot) / str(file)


def media_kind(name: str) -> str | None:
    suffix = str(name or "").rsplit(".", 1)[-1].lower()
    return MEDIA_TYPES.get(suffix)


def png_size(raw: bytes) -> tuple[int, int] | None:
    if len(raw) < 24 or raw[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return (int.from_bytes(raw[16:20], "big"), int.from_bytes(raw[20:24], "big"))


def jpeg_size(raw: bytes) -> tuple[int, int] | None:
    if raw[:2] != b"\xff\xd8":
        return None
    at = 2
    while at + 9 < len(raw):
        if raw[at] != 0xFF:
            at += 1
            continue
        marker = raw[at + 1]
        if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
            at += 2
            continue
        length = int.from_bytes(raw[at + 2 : at + 4], "big")
        if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
            return (
                int.from_bytes(raw[at + 7 : at + 9], "big"),
                int.from_bytes(raw[at + 5 : at + 7], "big"),
            )
        at += 2 + length
    return None


def webp_size(raw: bytes) -> tuple[int, int] | None:
    if len(raw) < 30 or raw[:4] != b"RIFF" or raw[8:12] != b"WEBP":
        return None
    chunk = raw[12:16]
    if chunk == b"VP8X":
        return (
            int.from_bytes(raw[24:27], "little") + 1,
            int.from_bytes(raw[27:30], "little") + 1,
        )
    if chunk == b"VP8 ":
        return (
            int.from_bytes(raw[26:28], "little") & 0x3FFF,
            int.from_bytes(raw[28:30], "little") & 0x3FFF,
        )
    if chunk == b"VP8L":
        bits = int.from_bytes(raw[21:25], "little")
        return ((bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1)
    return None


def picture_size(raw: bytes) -> tuple[int, int] | None:
    """Pillow is not a dependency here, so the header is read rather than the image decoded."""
    return png_size(raw) or jpeg_size(raw) or webp_size(raw)


async def save_media(
    bot: Any,
    guild_id: int,
    guide_id: int,
    raw: bytes,
    *,
    step_id: Any = None,
    suffix: str = "png",
    source: str = CAPTURE,
    surface: str = DISCORD,
    caption: Any = None,
    shot_release: Any = None,
    shot_by: int | None = None,
) -> int:
    db = bot.db
    size = picture_size(raw)
    digest = hashlib.sha256(raw).hexdigest()
    cur = await db.conn.execute(
        "INSERT INTO guide_media(guild_id, guide_id, step_id, file, sha256, width, height, "
        "bytes, source, surface, shot_release, shot_by, shot_at, caption, stale) "
        "VALUES (?, ?, ?, '', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)",
        (
            int(guild_id),
            int(guide_id),
            int(step_id) if step_id else None,
            digest,
            size[0] if size else None,
            size[1] if size else None,
            len(raw),
            source if source in SOURCES else CAPTURE,
            surface if surface in SURFACES else DISCORD,
            str(shot_release) if shot_release else None,
            shot_by,
            now(),
            clamp(caption, CAPTION_MAX) or None,
        ),
    )
    media_id = int(cur.lastrowid)
    name = f"{media_id}.{suffix}"
    root = media_root(bot)
    root.mkdir(parents=True, exist_ok=True)
    (root / name).write_bytes(raw)
    await db.conn.execute("UPDATE guide_media SET file = ? WHERE id = ?", (name, media_id))
    await db.conn.commit()
    return media_id


async def drop_media(bot: Any, row: Any) -> None:
    await bot.db.conn.execute("DELETE FROM guide_media WHERE id = ?", (int(row["id"]),))
    await bot.db.conn.execute(
        "UPDATE guide_steps SET media_id = NULL WHERE media_id = ?", (int(row["id"]),)
    )
    await bot.db.conn.commit()
    try:
        media_path(bot, row["file"]).unlink(missing_ok=True)
    except OSError as exc:
        log.warning("guides: %s could not be removed — %s", row["file"], exc)


__all__ = [
    "AUDIENCES",
    "COMMAND_TAKEN",
    "FACTS_MAX",
    "FEATURE_PATHS",
    "GUIDES_OFF",
    "MEDIA_BYTES_MAX",
    "MEDIA_CACHE",
    "MEDIA_SIDE_MAX",
    "MEDIA_TOO_BIG",
    "MEDIA_TOO_WIDE",
    "MEDIA_TYPES",
    "MEDIA_UNREADABLE",
    "MEDIA_WRONG_TYPE",
    "MEMBER",
    "NOT_YOURS_TO_EDIT",
    "NO_SUCH_GUIDE",
    "NO_SUCH_MEDIA",
    "PAGE",
    "PROBES",
    "PROBE_LABELS",
    "REASON_MAX",
    "SEEDED_CANNOT_BE_DELETED",
    "SLUG_NEEDED",
    "SLUG_TAKEN",
    "STAFF",
    "STEP_NEEDS_TEXT",
    "TITLE_NEEDED",
    "TOO_MANY_FACTS",
    "count_guides",
    "create_guide",
    "delete_guide",
    "diff_summary",
    "drop_media",
    "facts_of",
    "fault_files_request",
    "faults_of",
    "features",
    "feature_mode",
    "features_changed",
    "get_guide",
    "get_guide_by_id",
    "get_media",
    "guide_url",
    "guides_on",
    "help_links_on",
    "hub_url",
    "is_seeded",
    "lint_step",
    "lint_steps",
    "links_for",
    "list_guides",
    "load_seed",
    "mark_all_stale",
    "media_kind",
    "media_of",
    "media_path",
    "media_root",
    "picture_size",
    "published_for",
    "put_facts",
    "put_faults",
    "put_steps",
    "next_release",
    "reconcile_releases",
    "refresh_seeds",
    "release_payload",
    "right_now",
    "refused_fact",
    "refused_probe",
    "refused_setting",
    "release_before",
    "reset_to_seed",
    "resolve_facts",
    "save_media",
    "seed_entries",
    "seed_guides",
    "seed_hash",
    "slugify",
    "stale_media",
    "steps_of",
]
