from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import discord

from . import shadow as shadow_home
from .actionlog import log_action
from .llm import LLMError
from .logkinds import FEATURE_PAGES, VIA_DISCORD, kind_via
from .minutes_audio import CHUNK_SECONDS_DEFAULT as AUDIO_CHUNK_SECONDS_DEFAULT
from .minutes_audio import NO_EXTENSION, NO_OPUS, extension_available, opus_available
from .panels import Outcome, refusal
from .settings_store import (
    MINUTES_KEEP_DAYS_DEFAULT,
    MINUTES_MAX_HOURS_DEFAULT,
    MINUTES_MODES,
    MINUTES_NOTES_TITLE_DEFAULT,
    MINUTES_PANEL_MINUTES_DEFAULT,
    MINUTES_PROMPT_DEFAULT,
    MINUTES_START_TEXT_DEFAULT,
)

log = logging.getLogger(__name__)

FEATURE = "minutes"
PAGE = FEATURE_PAGES[FEATURE]

MODE_KEY = "minutes_mode"
CHANNEL_KEY = "minutes_channel_id"
OPT_OUT_KEY = "minutes_opt_out_role_id"
START_TEXT_KEY = "minutes_start_text"
PROMPT_KEY = "minutes_prompt"
NOTES_TITLE_KEY = "minutes_notes_title"
CHUNK_SECONDS_KEY = "minutes_chunk_seconds"
MAX_HOURS_KEY = "minutes_max_hours"
KEEP_DAYS_KEY = "minutes_keep_days"
PANEL_MINUTES_KEY = "minutes_panel_minutes"

OFF, ON = MINUTES_MODES
MODES = MINUTES_MODES

RECORDING = "recording"
WRITING = "writing"
DONE = "done"
FAILED = "failed"
STATUSES = (RECORDING, WRITING, DONE, FAILED)

BY_HAND = "by hand"
BY_EMPTY = "everyone left"
BY_WORDS = "somebody said stop notes"
BY_MAX_HOURS = "it ran past the longest a meeting may run"
BY_SHUTDOWN = "the bot was restarted"

STARTED = "minutes.started"
ENDED = "minutes.ended"
JOIN_FAILED = "minutes.join_failed"
TRANSCRIBE_FAILED = "minutes.transcribe_failed"
NOTES_WRITTEN = "minutes.notes_written"
NOTES_FAILED = "minutes.notes_failed"
POSTED = "minutes.posted"
POST_FAILED = "minutes.post_failed"
NOTES_EDITED = "minutes.notes_edited"
DELETED = "minutes.deleted"
PURGED = "minutes.purged"
MODE_SET = "minutes.mode"

STOP_PHRASE = "stop notes"

NOTES_MAX = 4000
TRANSCRIPT_CHARS_MAX = 60_000
LIST_LIMIT = 50

PANEL_TITLE = "Meeting minutes"
PANEL_INTRO = (
    "Black Bloc joins the voice channel you are in, listens, and writes the meeting up "
    "afterwards. Nothing is kept but the words — the audio is thrown away as it is read."
)
PANEL_EMPTY = "No meeting has been recorded here yet."
PANEL_TIMEOUT_FOOTER = "This panel has gone quiet — run /minutes again."
START_LABEL = "Start taking notes"
STOP_LABEL = "Stop"
WHERE_LABEL = "Where notes go…"
LOGS_LABEL = "Logs"
SITE_LABEL = "Open the Minutes page"
POST_AGAIN_LABEL = "Post again"
DELETE_LABEL = "Delete"

MINUTES_OFF = (
    "Meeting minutes are turned off for this server, so nothing was done. This is a prototype "
    "and it ships off on purpose — a Lead turns it on from the dashboard's Settings page under "
    "**events**, or with `/settings` ▸ **A setting group…** ▸ **events** ▸ **minutes_mode**."
)
NOT_IN_VOICE = (
    "You are not in a voice channel, so there is no meeting for Black Bloc to join. Join the "
    "meeting first, then press **Start taking notes** again."
)
ALREADY_RUNNING = (
    "Black Bloc is already taking notes in {where}, and it can only be in one meeting at a "
    "time. Press **Stop** there first, or move into that channel and stop it from `/minutes`."
)
OPT_OUT_PRESENT = (
    "{names} {is_are} in that channel wearing a role that says do not record me, so Black Bloc "
    "did not join and nothing was recorded. Ask them whether they are happy to be recorded — if "
    "they are, a Lead can take the role off, or clear **minutes_opt_out_role_id** on the "
    "Settings page."
)
NO_TRANSCRIBER = (
    "There is no speech-to-text key on this host, so Black Bloc cannot turn a meeting into "
    "words and did not join. The key is named `GROQ_API_KEY` and only the owner can set it — "
    "tell him, and nothing else here needs changing."
)
NO_NOTES_WRITER = (
    "There is no writing key on this host, so the transcript was kept but no notes were "
    "written. The key is named `ANTHROPIC_API_KEY` and only the owner can set it — tell him. "
    "The whole transcript is on the Minutes page in the meantime."
)
CANNOT_CONNECT = (
    "Black Bloc is not allowed to join **{where}**, so nothing was recorded. It needs the "
    "**Connect** permission on that channel — it never needs Speak. Ask a server admin to give "
    "it Connect there, then press **Start taking notes** again."
)
JOIN_BROKE = (
    "Black Bloc could not join **{where}**: {reason}. That is a fault between the bot and "
    "Discord rather than a problem with your access — try again, and tell a Lead if it keeps "
    "happening."
)
NO_MEETING_RUNNING = (
    "No meeting is being recorded right now, so there was nothing to stop. Press **Start "
    "taking notes** while you are in a voice channel to begin one."
)
NO_SUCH_MEETING = (
    "There is no meeting **#{meeting_id}** on this server, so nothing was done. It may have "
    "been deleted — open the Minutes page and pick one from the list."
)
STILL_RECORDING = (
    "Meeting **#{meeting_id}** is still being recorded, so there are no notes to work with "
    "yet. Press **Stop** on `/minutes` first."
)
NOTHING_HEARD = (
    "Nobody said anything Black Bloc could make out, so there is no transcript and no notes "
    "were written. The meeting is still on the Minutes page with nothing in it."
)
NOTES_BROKE = (
    "The transcript was kept but the notes could not be written: {reason}. Nothing is lost — "
    "open the meeting on the Minutes page and press **Write the notes again**, and tell a Lead "
    "if it keeps happening."
)
NO_WHERE_TO_POST = (
    "There is nowhere to put these notes: this meeting's channel has no text chat Black Bloc "
    "can write in, and **minutes_channel_id** is not set. A Lead sets it on the Settings page "
    "under **events**, then press **Post again**."
)
POST_BROKE = (
    "Discord would not take that post, so the notes are still only on the site: {reason}. Try "
    "**Post again**, and tell a Lead if it keeps happening."
)
NOTES_TOO_LONG = (
    "Notes hold {limit} characters and those are {count}, so nothing was saved. Take {over} "
    "character{s} out."
)
NOTES_ARE_BLANK = (
    "Notes cannot be empty, so nothing was saved. Write something, or press **Delete** if this "
    "meeting should not be kept at all."
)
TEST_MODE_LANDS = (
    "Black Bloc is in test mode, so what it would post in {wanted} goes to {landed} instead."
)
TEST_MODE_NOWHERE = (
    "Black Bloc is in test mode and there is nowhere it is allowed to speak, so the "
    "announcement and the notes are kept on the site only."
)
STARTED_SAID = (
    "Recording **{where}**. Say **stop notes** in the voice chat or press **Stop** here when "
    "the meeting is over — the notes are written then."
)
STOPPED_SAID = "Stopped recording {where}. Writing the notes now…"
NOTES_SAID = "Notes written for meeting **#{meeting_id}**."
POSTED_SAID = "Posted the notes for meeting **#{meeting_id}** in {where}."
EDITED_SAID = "Saved the notes for meeting **#{meeting_id}**."
DELETED_SAID = "Deleted meeting **#{meeting_id}** — the notes and the transcript went with it."
MODE_SAID = "Meeting minutes are now **{mode}**."
MODE_ON_NOTE = (
    " It is still a prototype: only staff can start one, and every meeting announces itself "
    "before a word is recorded."
)


def now_text() -> str:
    return datetime.now(UTC).isoformat()


def row_value(row: Any, key: str, fallback: Any = None) -> Any:
    try:
        found = row[key]
    except (KeyError, IndexError, TypeError):
        return fallback
    return fallback if found is None else found


def guild_id_of(guild: Any) -> int:
    return shadow_home.guild_id_of(guild)


def mode_of(store: Any, guild_id: int) -> str:
    return str(store.get(guild_id, MODE_KEY) or OFF)


def minutes_are_off(store: Any, guild_id: int) -> bool:
    return mode_of(store, guild_id) != ON


def panel_minutes(store: Any, guild_id: int) -> int:
    return int(store.get(guild_id, PANEL_MINUTES_KEY) or MINUTES_PANEL_MINUTES_DEFAULT)


def chunk_seconds(store: Any, guild_id: int) -> int:
    return int(store.get(guild_id, CHUNK_SECONDS_KEY) or AUDIO_CHUNK_SECONDS_DEFAULT)


def max_hours(store: Any, guild_id: int) -> int:
    return int(store.get(guild_id, MAX_HOURS_KEY) or MINUTES_MAX_HOURS_DEFAULT)


def keep_days(store: Any, guild_id: int) -> int:
    return int(store.get(guild_id, KEEP_DAYS_KEY) or MINUTES_KEEP_DAYS_DEFAULT)


def start_text(store: Any, guild_id: int) -> str:
    return str(store.get(guild_id, START_TEXT_KEY) or MINUTES_START_TEXT_DEFAULT)


def notes_title(store: Any, guild_id: int) -> str:
    return str(store.get(guild_id, NOTES_TITLE_KEY) or MINUTES_NOTES_TITLE_DEFAULT)


def notes_prompt(store: Any, guild_id: int) -> str:
    return str(store.get(guild_id, PROMPT_KEY) or MINUTES_PROMPT_DEFAULT)


def site_page_url(origin: Any) -> str | None:
    text = str(origin or "").strip()
    return f"{text.rstrip('/')}/{PAGE}" if text else None


def where_words(guild: Any, channel_id: Any) -> str:
    if not channel_id:
        return "nowhere yet"
    channel = guild.get_channel(int(channel_id)) if guild is not None else None
    return f"#{channel.name}" if channel is not None else f"<#{channel_id}>"


def opt_out_role_id(store: Any, guild_id: int) -> int | None:
    found = store.get(guild_id, OPT_OUT_KEY)
    return int(found) if found else None


def wearers_of(channel: Any, role_id: int | None) -> list[str]:
    """Who in the voice channel says do not record me; `voice_states`, never `members` (item 27)."""
    if not role_id or channel is None:
        return []
    guild = getattr(channel, "guild", None)
    found: list[str] = []
    for user_id in getattr(channel, "voice_states", {}) or {}:
        member = guild.get_member(int(user_id)) if guild is not None else None
        if member is None:
            continue
        if any(int(getattr(role, "id", 0)) == role_id for role in getattr(member, "roles", ())):
            found.append(str(getattr(member, "display_name", user_id)))
    return found


def names_sentence(names: list[str]) -> str:
    if len(names) == 1:
        return f"**{names[0]}**"
    kept = [f"**{one}**" for one in names]
    return ", ".join(kept[:-1]) + f" and {kept[-1]}"


def may_connect(channel: Any, me: Any) -> bool:
    permissions = getattr(channel, "permissions_for", None)
    if permissions is None or me is None:
        return True
    try:
        return bool(permissions(me).connect)
    except Exception as exc:
        log.warning("minutes: could not read permissions on a voice channel — %s", exc)
        return True


def landing(bot: Any, guild: Any, wanted: Any) -> tuple[int | None, str]:
    """Where a message actually goes, and the one sentence that says so when it moved."""
    guard = getattr(bot, "guard", None)
    if guard is None or wanted and guard.allows_channel(int(wanted)):
        return (int(wanted) if wanted else None, "")
    landed = shadow_home.channel_id(bot, guild)
    if landed is None:
        return (None, TEST_MODE_NOWHERE)
    if wanted and int(landed) == int(wanted):
        return (int(landed), "")
    return (
        int(landed),
        TEST_MODE_LANDS.format(
            wanted=where_words(guild, wanted) if wanted else "the meeting's own chat",
            landed=where_words(guild, landed),
        ),
    )


def wanted_channel_id(bot: Any, guild: Any, voice_channel: Any) -> int | None:
    """`minutes_channel_id` when set, else the voice channel's own text chat."""
    chosen = bot.store.get(guild_id_of(guild), CHANNEL_KEY)
    if chosen:
        return int(chosen)
    return int(getattr(voice_channel, "id", 0)) or None


async def open_meeting(db: Any, guild_id: int) -> Any:
    cur = await db.conn.execute(
        "SELECT * FROM meetings WHERE guild_id = ? AND ended_at IS NULL ORDER BY id DESC LIMIT 1",
        (int(guild_id),),
    )
    return await cur.fetchone()


async def get_meeting(db: Any, guild_id: int, meeting_id: Any) -> Any:
    try:
        wanted = int(meeting_id)
    except (TypeError, ValueError):
        return None
    cur = await db.conn.execute(
        "SELECT * FROM meetings WHERE guild_id = ? AND id = ?", (int(guild_id), wanted)
    )
    return await cur.fetchone()


async def list_meetings(db: Any, guild_id: int, limit: int = LIST_LIMIT) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT * FROM meetings WHERE guild_id = ? ORDER BY id DESC LIMIT ?",
        (int(guild_id), int(limit)),
    )
    return list(await cur.fetchall())


async def start_row(db: Any, guild_id: int, channel_id: int, started_by: int) -> Any:
    cur = await db.conn.execute(
        "INSERT INTO meetings(guild_id, channel_id, started_by, started_at, status) "
        "VALUES (?, ?, ?, ?, ?)",
        (int(guild_id), int(channel_id), int(started_by), now_text(), RECORDING),
    )
    await db.conn.commit()
    return await get_meeting(db, guild_id, cur.lastrowid)


async def add_line(
    db: Any, meeting_id: int, *, speaker_id: int, speaker: str, started_at: Any, text: str
) -> int | None:
    said = str(text or "").strip()
    if not said:
        return None
    stamp = started_at.isoformat() if hasattr(started_at, "isoformat") else str(started_at)
    cur = await db.conn.execute(
        "INSERT INTO meeting_lines(meeting_id, speaker_id, speaker, started_at, text) "
        "VALUES (?, ?, ?, ?, ?)",
        (int(meeting_id), int(speaker_id), str(speaker), stamp, said),
    )
    await db.conn.commit()
    return int(cur.lastrowid)


async def lines_of(db: Any, meeting_id: int) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT * FROM meeting_lines WHERE meeting_id = ? ORDER BY started_at, id",
        (int(meeting_id),),
    )
    return list(await cur.fetchall())


async def count_lines(db: Any, meeting_id: int) -> int:
    cur = await db.conn.execute(
        "SELECT COUNT(*) AS n FROM meeting_lines WHERE meeting_id = ?", (int(meeting_id),)
    )
    row = await cur.fetchone()
    return int(row["n"]) if row is not None else 0


def transcript_text(rows: list[Any]) -> str:
    """The ordered, speaker-labelled transcript — the one shape the notes and the file read."""
    return "\n".join(f"{row['speaker']}: {row['text']}" for row in rows)


def speakers_of(rows: list[Any]) -> list[str]:
    found: list[str] = []
    for row in rows:
        name = str(row["speaker"])
        if name not in found:
            found.append(name)
    return found


async def end_row(db: Any, meeting_id: int, reason: str) -> None:
    await db.conn.execute(
        "UPDATE meetings SET ended_at = ?, ended_reason = ?, status = ? "
        "WHERE id = ? AND ended_at IS NULL",
        (now_text(), str(reason), WRITING, int(meeting_id)),
    )
    await db.conn.commit()


async def save_notes_row(db: Any, meeting_id: int, notes: str, status: str) -> None:
    await db.conn.execute(
        "UPDATE meetings SET notes = ?, status = ? WHERE id = ?",
        (str(notes), str(status), int(meeting_id)),
    )
    await db.conn.commit()


async def save_posted(db: Any, meeting_id: int, channel_id: Any, message_id: Any) -> None:
    await db.conn.execute(
        "UPDATE meetings SET notes_channel_id = ?, notes_message_id = ? WHERE id = ?",
        (
            int(channel_id) if channel_id else None,
            int(message_id) if message_id else None,
            int(meeting_id),
        ),
    )
    await db.conn.commit()


async def delete_row(db: Any, guild_id: int, meeting_id: int) -> None:
    await db.conn.execute(
        "DELETE FROM meeting_lines WHERE meeting_id = ?", (int(meeting_id),)
    )
    await db.conn.execute(
        "DELETE FROM meetings WHERE guild_id = ? AND id = ?", (int(guild_id), int(meeting_id))
    )
    await db.conn.commit()


async def purge_old_lines(db: Any, guild_id: int, days: int, *, now: Any = None) -> int:
    """`minutes_keep_days`: the words go, the meeting and its notes stay."""
    cutoff = (now or datetime.now(UTC)) - timedelta(days=max(1, int(days)))
    cur = await db.conn.execute(
        "DELETE FROM meeting_lines WHERE meeting_id IN "
        "(SELECT id FROM meetings WHERE guild_id = ? AND started_at < ?)",
        (int(guild_id), cutoff.isoformat()),
    )
    await db.conn.commit()
    return int(cur.rowcount or 0)


def transcribe_configured(bot: Any) -> bool:
    return bool(getattr(bot.settings, "simple_tier_configured", False))


def notes_configured(bot: Any) -> bool:
    return bool(getattr(bot.settings, "important_tier_configured", False))


async def may_start(bot: Any, guild: Any, member: Any, voice_channel: Any) -> Outcome:
    """Every reason Start refuses, in the order a person meets them, each one in words."""
    guild_id = guild_id_of(guild)
    if minutes_are_off(bot.store, guild_id):
        return refusal(MINUTES_OFF, "minutes_off", 409)
    if voice_channel is None:
        return refusal(NOT_IN_VOICE, "not_in_voice", 409)
    if not extension_available():
        return refusal(NO_EXTENSION, "no_extension", 503)
    if not opus_available():
        return refusal(NO_OPUS, "no_opus", 503)
    if not transcribe_configured(bot):
        return refusal(NO_TRANSCRIBER, "no_transcriber", 503)
    running = await open_meeting(bot.db, guild_id)
    if running is not None:
        return refusal(
            ALREADY_RUNNING.format(where=where_words(guild, running["channel_id"])),
            "already_running",
            409,
        )
    wearing = wearers_of(voice_channel, opt_out_role_id(bot.store, guild_id))
    if wearing:
        return refusal(
            OPT_OUT_PRESENT.format(
                names=names_sentence(wearing), is_are="is" if len(wearing) == 1 else "are"
            ),
            "opt_out_present",
            409,
        )
    if not may_connect(voice_channel, getattr(guild, "me", None)):
        return refusal(
            CANNOT_CONNECT.format(where=getattr(voice_channel, "name", voice_channel)),
            "cannot_connect",
            403,
        )
    return Outcome(True, "", value=voice_channel)


def notes_text_ok(notes: Any) -> Outcome:
    text = str(notes or "").strip()
    if not text:
        return refusal(NOTES_ARE_BLANK, "notes_blank", 400)
    if len(text) > NOTES_MAX:
        over = len(text) - NOTES_MAX
        return refusal(
            NOTES_TOO_LONG.format(
                limit=NOTES_MAX, count=len(text), over=over, s="" if over == 1 else "s"
            ),
            "notes_too_long",
            400,
        )
    return Outcome(True, "", value=text)


def prompt_messages(store: Any, guild_id: int, transcript: str) -> tuple[list[str], list[dict]]:
    kept = transcript[-TRANSCRIPT_CHARS_MAX:]
    return ([notes_prompt(store, guild_id)], [{"role": "user", "content": kept}])


def notes_client(bot: Any) -> Any:
    made = getattr(bot, "minutes_notes_client", None)
    if made is not None:
        return made
    from .llm import HaikuClient

    made = HaikuClient(bot.settings.anthropic_api_key)
    bot.minutes_notes_client = made
    return made


async def write_notes(bot: Any, guild: Any, row: Any, *, via: str = VIA_DISCORD) -> Outcome:
    """Transcript → the bot's own LLM door → `meetings.notes`. Never raises into a caller."""
    guild_id = guild_id_of(guild)
    meeting_id = int(row["id"])
    rows = await lines_of(bot.db, meeting_id)
    if not rows:
        await save_notes_row(bot.db, meeting_id, "", DONE)
        return refusal(NOTHING_HEARD, "nothing_heard", 409)
    if not notes_configured(bot):
        await save_notes_row(bot.db, meeting_id, "", FAILED)
        await log_action(
            bot,
            guild,
            kind_via(NOTES_FAILED, via),
            details={"meeting": meeting_id, "reason": "no_key", "via": via},
        )
        return refusal(NO_NOTES_WRITER, "no_notes_writer", 503)
    system, messages = prompt_messages(bot.store, guild_id, transcript_text(rows))
    try:
        reply = await notes_client(bot).reply(system=system, messages=messages)
    except LLMError as exc:
        await save_notes_row(bot.db, meeting_id, "", FAILED)
        await log_action(
            bot,
            guild,
            kind_via(NOTES_FAILED, via),
            details={"meeting": meeting_id, "reason": exc.reason, "via": via},
        )
        return refusal(NOTES_BROKE.format(reason=str(exc)), "notes_broke", 502)
    said = str(reply.text or "").strip()[:NOTES_MAX]
    if not said:
        await save_notes_row(bot.db, meeting_id, "", FAILED)
        await log_action(
            bot,
            guild,
            kind_via(NOTES_FAILED, via),
            details={"meeting": meeting_id, "reason": "empty", "via": via},
        )
        return refusal(NOTES_BROKE.format(reason="it answered with no words in it"), "empty", 502)
    await save_notes_row(bot.db, meeting_id, said, DONE)
    await log_action(
        bot,
        guild,
        kind_via(NOTES_WRITTEN, via),
        details={
            "meeting": meeting_id,
            "lines": len(rows),
            "speakers": len(speakers_of(rows)),
            "via": via,
        },
    )
    return Outcome(True, NOTES_SAID.format(meeting_id=meeting_id), value=said)


def notes_embed(bot: Any, guild: Any, row: Any, rows: list[Any]) -> discord.Embed:
    embed = discord.Embed(
        title=notes_title(bot.store, guild_id_of(guild)),
        description=str(row_value(row, "notes", "")) or NOTHING_HEARD,
    )
    embed.add_field(name="Where", value=where_words(guild, row["channel_id"]), inline=True)
    started = str(row["started_at"])[:19].replace("T", " ")
    embed.add_field(name="Started", value=started, inline=True)
    speakers = speakers_of(rows)
    if speakers:
        embed.add_field(name="Heard", value=", ".join(speakers)[:1024], inline=False)
    return embed


def transcript_file(row: Any, rows: list[Any]) -> discord.File | None:
    import io

    text = transcript_text(rows)
    if not text:
        return None
    return discord.File(
        io.BytesIO(text.encode("utf-8")), filename=f"meeting-{int(row['id'])}-transcript.txt"
    )


async def post_notes(bot: Any, guild: Any, row: Any, *, via: str = VIA_DISCORD) -> Outcome:
    """The notes embed plus the transcript, into the one channel `landing` picked."""
    meeting_id = int(row["id"])
    wanted = row_value(row, "notes_channel_id") or bot.store.get(guild_id_of(guild), CHANNEL_KEY)
    wanted = wanted or row["channel_id"]
    where, note = landing(bot, guild, wanted)
    if where is None:
        return refusal(NO_WHERE_TO_POST if not note else note, "nowhere_to_post", 409)
    channel = shadow_home.channel_of(bot, guild, where)
    if channel is None:
        return refusal(NO_WHERE_TO_POST, "nowhere_to_post", 409)
    rows = await lines_of(bot.db, meeting_id)
    try:
        message = await channel.send(
            embed=notes_embed(bot, guild, row, rows),
            file=transcript_file(row, rows),
            allowed_mentions=discord.AllowedMentions.none(),
        )
    except Exception as exc:
        await log_action(
            bot,
            guild,
            kind_via(POST_FAILED, via),
            details={"meeting": meeting_id, "reason": f"{type(exc).__name__}: {exc}", "via": via},
        )
        return refusal(POST_BROKE.format(reason=f"{type(exc).__name__}"), "post_broke", 502)
    await save_posted(bot.db, meeting_id, where, getattr(message, "id", None))
    await log_action(
        bot,
        guild,
        kind_via(POSTED, via),
        details={"meeting": meeting_id, "channel": where, "via": via},
    )
    said = POSTED_SAID.format(meeting_id=meeting_id, where=where_words(guild, where))
    return Outcome(True, f"{said} {note}".strip(), value=where)


async def edit_notes(
    bot: Any, guild: Any, row: Any, actor: Any, notes: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    checked = notes_text_ok(notes)
    if not checked.ok:
        return checked
    meeting_id = int(row["id"])
    await save_notes_row(bot.db, meeting_id, checked.value, DONE)
    await log_action(
        bot,
        guild,
        kind_via(NOTES_EDITED, via),
        actor=actor,
        details={"meeting": meeting_id, "via": via},
    )
    return Outcome(True, EDITED_SAID.format(meeting_id=meeting_id))


async def delete_meeting(
    bot: Any, guild: Any, row: Any, actor: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    meeting_id = int(row["id"])
    await delete_row(bot.db, guild_id_of(guild), meeting_id)
    await log_action(
        bot,
        guild,
        kind_via(DELETED, via),
        actor=actor,
        details={"meeting": meeting_id, "via": via},
    )
    return Outcome(True, DELETED_SAID.format(meeting_id=meeting_id))


async def set_mode(bot: Any, guild: Any, actor: Any, wanted: str, *, via: str = VIA_DISCORD) -> str:
    mode = str(wanted) if wanted in MODES else OFF
    await bot.store.set(guild_id_of(guild), MODE_KEY, mode, by=getattr(actor, "id", None))
    await log_action(
        bot, guild, kind_via(MODE_SET, via), actor=actor, details={"mode": mode, "via": via}
    )
    said = MODE_SAID.format(mode=mode)
    return said + MODE_ON_NOTE if mode == ON else said


def status_words(row: Any) -> str:
    status = str(row_value(row, "status", RECORDING))
    if status == RECORDING:
        return "recording"
    if status == WRITING:
        return "writing the notes"
    if status == FAILED:
        return "the notes did not get written"
    return "done"


def details_json(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (TypeError, ValueError):
            return {}
    return value or {}


__all__ = [
    "ALREADY_RUNNING",
    "CANNOT_CONNECT",
    "CHANNEL_KEY",
    "CHUNK_SECONDS_KEY",
    "DELETED",
    "DONE",
    "ENDED",
    "FAILED",
    "JOIN_BROKE",
    "JOIN_FAILED",
    "KEEP_DAYS_KEY",
    "LIST_LIMIT",
    "MAX_HOURS_KEY",
    "MINUTES_OFF",
    "MODES",
    "MODE_KEY",
    "NOTES_ARE_BLANK",
    "NOTES_EDITED",
    "NOTES_FAILED",
    "NOTES_MAX",
    "NOTES_TITLE_KEY",
    "NOTES_WRITTEN",
    "NOT_IN_VOICE",
    "NOTHING_HEARD",
    "NO_MEETING_RUNNING",
    "NO_NOTES_WRITER",
    "NO_SUCH_MEETING",
    "NO_TRANSCRIBER",
    "NO_WHERE_TO_POST",
    "OFF",
    "ON",
    "OPT_OUT_KEY",
    "OPT_OUT_PRESENT",
    "PAGE",
    "PANEL_MINUTES_KEY",
    "POSTED",
    "POST_FAILED",
    "PROMPT_KEY",
    "PURGED",
    "RECORDING",
    "STARTED",
    "START_TEXT_KEY",
    "STATUSES",
    "STILL_RECORDING",
    "STOP_PHRASE",
    "TRANSCRIBE_FAILED",
    "WRITING",
    "add_line",
    "chunk_seconds",
    "count_lines",
    "delete_meeting",
    "delete_row",
    "edit_notes",
    "end_row",
    "get_meeting",
    "guild_id_of",
    "keep_days",
    "landing",
    "lines_of",
    "list_meetings",
    "max_hours",
    "may_connect",
    "may_start",
    "minutes_are_off",
    "mode_of",
    "names_sentence",
    "notes_configured",
    "notes_embed",
    "notes_prompt",
    "notes_text_ok",
    "notes_title",
    "open_meeting",
    "opt_out_role_id",
    "panel_minutes",
    "post_notes",
    "prompt_messages",
    "purge_old_lines",
    "row_value",
    "save_notes_row",
    "save_posted",
    "set_mode",
    "site_page_url",
    "speakers_of",
    "start_row",
    "start_text",
    "status_words",
    "transcribe_configured",
    "transcript_file",
    "transcript_text",
    "wanted_channel_id",
    "wearers_of",
    "where_words",
    "write_notes",
]
