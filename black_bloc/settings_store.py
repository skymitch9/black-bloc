from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime
from inspect import isawaitable
from typing import Any

from .automod import (
    AUTOMOD_MODES,
    MOD_DM_STYLES,
    WARN_THRESHOLD_DEFAULT,
    RuleError,
    rules_summary,
    validate_rules,
)
from .chat_memory import (
    CONSENT_CHOICES,
    DM_SCOPES,
    MEMORY_MODES,
    NOTES_CEILING,
    NOTES_MAX,
    RETENTION_DAYS,
    RETENTION_MAX_DAYS,
    STAFF_VIEWS,
    THREADS_CEILING,
    THREADS_MAX,
)
from .config import Settings
from .emoji import SKIN_TONE_DEFAULT, SKIN_TONE_NAMES
from .groq import DEFAULT_MODEL as GROQ_DEFAULT_MODEL
from .logkinds import (
    CORE,
    FEATURE_LABELS,
    FEATURES,
    LEVEL_DEFAULT,
    LEVELS,
    OFF,
    log_level_key,
)
from .minutes_audio import CHUNK_SECONDS_DEFAULT as MINUTES_CHUNK_SECONDS_DEFAULT
from .minutes_audio import CHUNK_SECONDS_MAX as MINUTES_CHUNK_SECONDS_MAX
from .minutes_audio import CHUNK_SECONDS_MIN as MINUTES_CHUNK_SECONDS_MIN
from .personas import COOKOUT, PERSONALITY_CHOICES
from .polls import DATE_LABEL_FORMS as POLL_DATE_LABEL_FORMS
from .polls import MAX_HOURS as POLL_MAX_HOURS
from .polls import MIN_HOURS as POLL_MIN_HOURS
from .polls import MODES as POLL_MODES
from .polls import SHADOW_NOTE as POLL_SHADOW_NOTE
from .shadow import NOTE_DEFAULT as REHEARSAL_NOTE_DEFAULT
from .shadow import NOTE_KEY as REHEARSAL_NOTE
from .shadow import REHEARSAL_KEY as SHADOW_CHANNEL
from .storage.db import Database
from .timezones import DEFAULT_TZ, is_known, suggest

log = logging.getLogger(__name__)

LIVE_NOW_CHANNEL_ID = 1225457308230746202
GOLIVE_TEMPLATE = (
    "REGULATORS! Mount up! **{name}** is currently streaming **{game}**! "
    "Check it out: {url}"
)
GOLIVE_MODES = ("off", "shadow", "on")
GOLIVE_END_OFF = "off"
GOLIVE_END_EDIT = "edit"
GOLIVE_END_MODES = (GOLIVE_END_OFF, GOLIVE_END_EDIT)
GOLIVE_END_SUFFIX = " — stream ended"
GOLIVE_END_TEMPLATE = "**{name}** was streaming **{game}** — the stream has ended. {url}"
GOLIVE_END_AUTHOR = "{name} was live on {platform}"
GOLIVE_COSTREAM_OFF = "off"
GOLIVE_COSTREAM_ON = "on"
GOLIVE_COSTREAM_MODES = (GOLIVE_COSTREAM_OFF, GOLIVE_COSTREAM_ON)
GOLIVE_COSTREAM_MODE_KEY = "golive_costream_mode"
GOLIVE_COSTREAM_TEMPLATE_KEY = "golive_costream_template"
GOLIVE_COSTREAM_AUTHOR_KEY = "golive_costream_author"
GOLIVE_COSTREAM_TEMPLATE = (
    "**{name}** is streaming on **{platform}** and **{also_platform}**! "
    "Watch on {platform}: {url} · also live on {also_platform}: {also_url}"
)
GOLIVE_COSTREAM_AUTHOR = "{name} is live on {platform} and {also_platform}"
GOLIVE_COSTREAM_FIELDS = (
    "name",
    "game",
    "title",
    "url",
    "platform",
    "also_url",
    "also_platform",
)


ROLEMENU_MODES = ("off", "on")

PINGS_MODES = ("off", "on")
PINGS_EVENTS_ROLE_NAME = "Events"
PINGS_FAN_ROLE_TEMPLATE = "{name} pings"
PINGS_CREATORS = ("self", "staff", "auto", "follow")
PINGS_CREATION_DEFAULT = "follow"
PINGS_ON_UNLINK = ("keep", "delete")
PINGS_STREAMER_STALE_DAYS = 90
PINGS_STALE_MIN_DAYS = 7
PINGS_STALE_MAX_DAYS = 365
PINGS_EMPTY_ROLE_DAYS = 30
PINGS_EMPTY_ROLE_MIN_DAYS = 1
PINGS_EMPTY_ROLE_MAX_DAYS = 365
PINGS_ONBOARDING_TITLE = "What should ping you?"
PINGS_ONBOARDING_OPTION_CAP = 25
PINGS_OPTION_CAP_MIN = 1
PINGS_OPTION_CAP_MAX = 50

MEMBER_ROLE_ID = 1073741054563602532
TEMPVOICE_NAME_TEMPLATE = "{user}'s bloc"
TEMPVOICE_CREATOR_NAME = "join to create a channel"
TEMPVOICE_MODES = ("off", "shadow", "on")
TEMPVOICE_ROOM_OVERWRITES = ("lobby", "category")
HONEYPOT_MODES = ("off", "shadow", "on")
HONEYPOT_PURGE_MAX_DAYS = 7

EVENTS_MODES = ("off", "shadow", "on")
EVENTS_RETENTION_DAYS = 7
EVENTS_RETENTION_MIN_DAYS = 1
EVENTS_RETENTION_MAX_DAYS = 365
EVENTS_TEST_RETENTION_KEY = "events_test_retention_minutes"
EVENTS_TEST_RETENTION_MINUTES = 5
EVENTS_TEST_RETENTION_MIN_MINUTES = 1
EVENTS_TEST_RETENTION_MAX_MINUTES = 24 * 60
EVENTS_MAX_LATE_MINUTES = 15
EVENTS_LATE_CEILING_MINUTES = 24 * 60
EVENTS_DEFAULT_MINUTES = 120
EVENTS_DURATION_MIN_MINUTES = 5
EVENTS_DURATION_MAX_MINUTES = 7 * 24 * 60
EVENTS_SCHEDULED_NAME_KEY = "events_scheduled_name_template"
EVENTS_SCHEDULED_NAME_TEMPLATE = "{title} Feat. BaF"
NAME_PLACEHOLDER = "{title}"

EVENTS_POSTS_WHERE_KEY = "events_posts_where"
POSTS_ROOM = "room"
POSTS_ANNOUNCE = "announce"
POSTS_BOTH = "both"
EVENTS_POSTS_WHERES = (POSTS_ROOM, POSTS_ANNOUNCE, POSTS_BOTH)
EVENTS_POSTS_WHERE = POSTS_ROOM
EVENTS_ROOM_DELETE_KEY = "events_room_delete_who"
ROOM_DELETE_STAFF = "staff"
ROOM_DELETE_APPROVER = "approver"
EVENTS_ROOM_DELETE_WHOS = (ROOM_DELETE_STAFF, ROOM_DELETE_APPROVER)
EVENTS_ROOM_DELETE_WHO = ROOM_DELETE_STAFF
EVENTS_APPROVER_ROLE_KEY = "events_approver_role_id"
EVENTS_ROOM_NOTICE_KEY = "events_room_notice"
EVENTS_ROOM_NOTICE = True
EVENTS_REVIEW_MODE_KEY = "events_review_mode"
REVIEW_ROOM = "room"
REVIEW_FORUM = "forum"
EVENTS_REVIEW_MODES = (REVIEW_ROOM, REVIEW_FORUM)
EVENTS_REVIEW_MODE = REVIEW_ROOM
EVENTS_FORUM_CHANNEL_KEY = "events_forum_channel_id"
EVENTS_MOVED_LINE_KEY = "events_moved_line"
EVENTS_MOVED_LINE = (
    "This event now lives in its own post: {post}. This room is being removed."
)
POST_PLACEHOLDER = "{post}"
REQUEST_FILED_KEY = "request_filed_line"
REQUEST_FILED = (
    "Filed as **#{request_id}** — Request has been received. You will get a DM every time "
    "the status is updated."
)
REQUEST_ID_PLACEHOLDER = "{request_id}"

WHERE_ALIASES_KEY = "events_where_link_aliases"
WHERE_ALIAS_MAX = 32
HANDLE_PLACEHOLDER = "{handle}"
WHERE_ALIASES = (
    "ttv=https://twitch.tv/{handle}, twitch=https://twitch.tv/{handle}, "
    "yt=https://youtube.com/@{handle}, youtube=https://youtube.com/@{handle}, "
    "kick=https://kick.com/{handle}, tiktok=https://tiktok.com/@{handle}, "
    "ig=https://instagram.com/{handle}, instagram=https://instagram.com/{handle}, "
    "x=https://x.com/{handle}, twitter=https://x.com/{handle}, "
    "discord=https://discord.gg/{handle}"
)
WHERE_CHECK_KEY = "events_where_link_check"
WHERE_CHECK_OFF = "off"
WHERE_CHECK_WARN = "warn"
WHERE_CHECK_REFUSE = "refuse"
WHERE_CHECK_MODES = (WHERE_CHECK_OFF, WHERE_CHECK_WARN, WHERE_CHECK_REFUSE)
WHERE_CHECK_MODE = WHERE_CHECK_WARN
WHERE_CHECK_SECONDS_KEY = "events_where_link_check_seconds"
WHERE_CHECK_SECONDS = 2
WHERE_CHECK_MIN_SECONDS = 1
WHERE_CHECK_MAX_SECONDS = 3
WHERE_HINT_KEY = "events_where_hint"
WHERE_HINT = (
    "If you do not see your channel, start typing the channel name and it should appear."
)

DEFAULT_TIMEZONE_KEY = "default_timezone"
TIMEZONE_CHOICES_KEY = "timezone_choices"
TIME_STEP_KEY = "time_step_minutes"
TIME_STEP_MINUTES = 15
TIME_STEP_MIN_MINUTES = 5
TIME_STEP_MAX_MINUTES = 60
TIMEZONE_CHOICES_MAX = 24
TIMEZONE_CHOICES = (
    "America/Phoenix",
    "America/Los_Angeles",
    "America/Denver",
    "America/Chicago",
    "America/New_York",
    "America/Anchorage",
    "Pacific/Honolulu",
    "America/Toronto",
    "America/Vancouver",
    "America/Mexico_City",
    "America/Sao_Paulo",
    "Europe/London",
    "Europe/Paris",
    "Europe/Berlin",
    "Europe/Madrid",
    "Europe/Moscow",
    "Asia/Tokyo",
    "Asia/Seoul",
    "Asia/Shanghai",
    "Asia/Kolkata",
    "Asia/Dubai",
    "Australia/Sydney",
    "Australia/Perth",
    "Pacific/Auckland",
)

POLL_REVIEW_MODES = ("off", "on")
POLL_CREATORS = ("staff", "everyone")
POLL_DEFAULT_HOURS = 24
POLL_REMINDER_MINUTES = 60
POLL_REMINDER_MAX_MINUTES = 7 * 24 * 60
POLL_ARCHIVE_DAYS = 365
POLL_ARCHIVE_MIN_DAYS = 1
POLL_ARCHIVE_MAX_DAYS = 10 * 365

BIRTHDAY_CHANNEL_ID = 1411816390414962700
BIRTHDAY_TEMPLATE = "Happy Birthday **{name}**!"
BIRTHDAY_COLOR = "#4eefff"
BIRTHDAY_TZ = "America/Phoenix"
BIRTHDAY_MODES = ("off", "shadow", "on")
HEX_COLOR = re.compile(r"^#?([0-9a-fA-F]{6})$")

CHANNEL_MODE = "channel"
THREAD_MODE = "thread"
FORUM_MODE = "forum"
MODMAIL_MODES = (CHANNEL_MODE, THREAD_MODE, FORUM_MODE)
MODMAIL_CATEGORY_ID = 1442613057628012594
MODMAIL_LOG_CHANNEL_ID = 1442613059704066108

WARN_THRESHOLD_MAX = 100

REQUEST_MODES = ("off", "on")
REQUEST_FILERS = ("everyone", "staff")

CHAT_MODES = ("off", "on")
CHAT_COOLDOWN_SECONDS = 20
CHAT_COOLDOWN_MIN_SECONDS = 5
CHAT_COOLDOWN_MAX_SECONDS = 600
CHAT_PERSONALITY_DEFAULT = COOKOUT
CHAT_TURNS_MAX = 10_000
CHAT_MONTHLY_CAP_MAX = 1_000
CHAT_PERSON_HOURLY_TURNS = 20
CHAT_DAILY_TURNS = 200
CHAT_MONTHLY_CAP_USD = 20
CHAT_LLM_MODES = ("off", "on")
CHAT_ESCALATION_NAMES = 2
CHAT_ESCALATION_NAMES_MAX = 10

COST_HOSTING_USD = 0
COST_HOSTING_MAX_USD = 10_000

RAIDTRAIN_MODES = ("off", "shadow", "on")
RAIDTRAIN_SLOT_MINUTES = 60
RAIDTRAIN_SLOT_MIN_MINUTES = 15
RAIDTRAIN_SLOT_MAX_MINUTES = 12 * 60
RAIDTRAIN_REMINDER_MINUTES = 30
RAIDTRAIN_REMINDER_MIN_MINUTES = 5
RAIDTRAIN_REMINDER_MAX_MINUTES = 24 * 60
RAIDTRAIN_POLL_MINUTES = 5
RAIDTRAIN_POLL_MIN_MINUTES = 1
RAIDTRAIN_POLL_MAX_MINUTES = 60
RAIDTRAIN_MAX_SLOTS_PER_MEMBER = 1
RAIDTRAIN_SLOTS_PER_MEMBER_MAX = 24
RAIDTRAIN_SCHEDULED_NAME_KEY = "raidtrain_scheduled_name_template"
RAIDTRAIN_SCHEDULED_NAME_TEMPLATE = "{title}"

BOT_BIO_TEMPLATE = (
    "Black Bloc — moderation & content bot for Black in a Flash!. Staff dashboard: {site}"
)
STATUS_PREFIX = "Cookout attendees"

KEY_TYPES: dict[str, str] = {
    "log_channel_id": "channel",
    "staff_channel_id": "channel",
    "role_menu_channel_id": "channel",
    "golive_mode": "enum",
    "golive_channel_id": "channel",
    "golive_template": "text",
    "golive_end_mode": "enum",
    "golive_end_suffix": "text",
    "golive_end_template": "text",
    "golive_end_author": "text",
    "golive_end_keep_mention": "bool",
    GOLIVE_COSTREAM_MODE_KEY: "enum",
    GOLIVE_COSTREAM_TEMPLATE_KEY: "text",
    GOLIVE_COSTREAM_AUTHOR_KEY: "text",
    "golive_live_role_id": "role",
    "golive_require_role_id": "role",
    "golive_ignore_role_id": "role",
    "golive_cooldown_minutes": "int",
    "golive_ping_role_id": "role",
    "golive_max_session_hours": "int",
    "golive_embed": "bool",
    "golive_boot_sweep": "bool",
    "pings_mode": "enum",
    "pings_events_role_name": "text",
    "pings_fan_role_creation": "enum",
    "pings_fan_role_template": "text",
    "pings_fan_role_on_unlink": "enum",
    "pings_fan_role_delete": "bool",
    "pings_streamer_stale_days": "int",
    "pings_empty_role_days": "int",
    "pings_onboarding_managed": "bool",
    "pings_onboarding_prompt_title": "text",
    "pings_onboarding_option_cap": "int",
    "tempvoice_mode": "enum",
    "tempvoice_creator_ids": "channels",
    "tempvoice_name_template": "text",
    "tempvoice_creator_name": "text",
    "tempvoice_allowed_role_id": "role",
    "tempvoice_room_overwrites": "enum",
    "honeypot_mode": "enum",
    "honeypot_channel_ids": "channels",
    "honeypot_purge_days": "int",
    "honeypot_exempt_role_ids": "roles",
    "events_mode": "enum",
    "events_category_id": "channel",
    "events_announce_channel_id": "channel",
    "events_ping_role_id": "role",
    "events_create_scheduled": "bool",
    "events_where_link_in_description": "bool",
    WHERE_ALIASES_KEY: "text",
    WHERE_CHECK_KEY: "enum",
    WHERE_CHECK_SECONDS_KEY: "int",
    WHERE_HINT_KEY: "text",
    "events_channel_retention_days": "int",
    EVENTS_TEST_RETENTION_KEY: "int",
    "events_max_late_minutes": "int",
    "events_default_minutes": "int",
    EVENTS_SCHEDULED_NAME_KEY: "text",
    EVENTS_POSTS_WHERE_KEY: "enum",
    EVENTS_ROOM_DELETE_KEY: "enum",
    EVENTS_APPROVER_ROLE_KEY: "role",
    EVENTS_ROOM_NOTICE_KEY: "bool",
    EVENTS_REVIEW_MODE_KEY: "enum",
    EVENTS_FORUM_CHANNEL_KEY: "channel",
    EVENTS_MOVED_LINE_KEY: "text",
    REQUEST_FILED_KEY: "text",
    DEFAULT_TIMEZONE_KEY: "text",
    TIMEZONE_CHOICES_KEY: "text",
    TIME_STEP_KEY: "int",
    "poll_mode": "enum",
    "poll_who_can_create": "enum",
    "poll_review_mode": "enum",
    "poll_default_hours": "int",
    "poll_channel_id": "channel",
    "poll_pin": "bool",
    "poll_shadow_note": "text",
    "poll_ping_role_id": "role",
    "poll_reminder_minutes": "int",
    "poll_auto_thread": "bool",
    "poll_archive_days": "int",
    "poll_archive_drop_votes": "bool",
    "poll_date_labels": "enum",
    "birthday_mode": "enum",
    "birthday_channel_id": "channel",
    "birthday_template": "text",
    "birthday_color": "color",
    "birthday_role_id": "role",
    "birthday_show_age": "bool",
    "modmail_enabled": "bool",
    "modmail_mode": "enum",
    "modmail_category_id": "channel",
    "modmail_staff_channel_id": "channel",
    "modmail_log_channel_id": "channel",
    "automod_mode": "enum",
    "automod_rules": "json",
    "automod_exempt_role_ids": "roles",
    "automod_exempt_channel_ids": "channels",
    "automod_warn_threshold": "int",
    "modlog_channel_id": "channel",
    "mod_dm_on_action": "enum",
    "bot_bio": "text",
    "status_prefix": "text",
    "rolemenu_mode": "enum",
    "request_mode": "enum",
    "request_who_can_file": "enum",
    "request_notify_channel_id": "channel",
    "request_status_channel_id": "channel",
    "request_forum_channel_id": "channel",
    "request_dm_on_decision": "bool",
    "chat_mode": "enum",
    "chat_cooldown_seconds": "int",
    "chat_ignore_channels": "channels",
    "chat_ignore_categories": "channels",
    "chat_home_channel_id": "channel",
    "chat_visibility_role_id": "role",
    "chat_staff_can_ping_roles": "bool",
    "chat_escalation_names": "int",
    "chat_greeting_reaction": "bool",
    "chat_reply_in_threads": "bool",
    "chat_route_ping_staff": "bool",
    "chat_llm_mode": "enum",
    "chat_simple_model": "text",
    "chat_personality": "enum",
    "chat_person_hourly_turns": "int",
    "chat_daily_turns": "int",
    "chat_monthly_cap_usd": "int",
    "chat_status_admin_only": "bool",
    "chat_memory_mode": "enum",
    "chat_memory_consent": "enum",
    "chat_memory_retention_days": "int",
    "chat_memory_dm_scope": "enum",
    "chat_memory_staff_view": "enum",
    "chat_memory_notes_max": "int",
    "chat_memory_threads_max": "int",
    "chat_memory_model": "text",
    "rolemenu_approval_channel_id": "channel",
    "rolemenu_approver_role_id": "role",
    "emoji_skin_tone": "enum",
    "cost_hosting_usd": "int",
    "raidtrain_mode": "enum",
    "raidtrain_organizer_role_id": "role",
    "raidtrain_channel_id": "channel",
    "raidtrain_ping_role_id": "role",
    "raidtrain_slot_minutes": "int",
    "raidtrain_reminder_minutes": "int",
    "raidtrain_poll_minutes": "int",
    "raidtrain_require_link": "bool",
    "raidtrain_thread": "bool",
    "raidtrain_live_posts": "bool",
    "raidtrain_max_slots_per_member": "int",
    "raidtrain_scheduled_event": "bool",
    RAIDTRAIN_SCHEDULED_NAME_KEY: "text",
}

KEY_CHOICES: dict[str, tuple[str, ...]] = {
    "golive_mode": GOLIVE_MODES,
    "golive_end_mode": GOLIVE_END_MODES,
    GOLIVE_COSTREAM_MODE_KEY: GOLIVE_COSTREAM_MODES,
    "pings_mode": PINGS_MODES,
    "pings_fan_role_creation": PINGS_CREATORS,
    "pings_fan_role_on_unlink": PINGS_ON_UNLINK,
    "tempvoice_mode": TEMPVOICE_MODES,
    "tempvoice_room_overwrites": TEMPVOICE_ROOM_OVERWRITES,
    "honeypot_mode": HONEYPOT_MODES,
    "events_mode": EVENTS_MODES,
    EVENTS_POSTS_WHERE_KEY: EVENTS_POSTS_WHERES,
    EVENTS_ROOM_DELETE_KEY: EVENTS_ROOM_DELETE_WHOS,
    EVENTS_REVIEW_MODE_KEY: EVENTS_REVIEW_MODES,
    WHERE_CHECK_KEY: WHERE_CHECK_MODES,
    "poll_mode": POLL_MODES,
    "poll_review_mode": POLL_REVIEW_MODES,
    "poll_who_can_create": POLL_CREATORS,
    "poll_date_labels": POLL_DATE_LABEL_FORMS,
    "birthday_mode": BIRTHDAY_MODES,
    "modmail_mode": MODMAIL_MODES,
    "automod_mode": AUTOMOD_MODES,
    "mod_dm_on_action": MOD_DM_STYLES,
    "rolemenu_mode": ROLEMENU_MODES,
    "request_mode": REQUEST_MODES,
    "request_who_can_file": REQUEST_FILERS,
    "chat_mode": CHAT_MODES,
    "chat_llm_mode": CHAT_LLM_MODES,
    "chat_personality": PERSONALITY_CHOICES,
    "chat_memory_mode": MEMORY_MODES,
    "chat_memory_consent": CONSENT_CHOICES,
    "chat_memory_dm_scope": DM_SCOPES,
    "chat_memory_staff_view": STAFF_VIEWS,
    "emoji_skin_tone": SKIN_TONE_NAMES,
    "raidtrain_mode": RAIDTRAIN_MODES,
}

KEY_MAX: dict[str, int] = {
    "honeypot_purge_days": HONEYPOT_PURGE_MAX_DAYS,
    "events_channel_retention_days": EVENTS_RETENTION_MAX_DAYS,
    EVENTS_TEST_RETENTION_KEY: EVENTS_TEST_RETENTION_MAX_MINUTES,
    WHERE_CHECK_SECONDS_KEY: WHERE_CHECK_MAX_SECONDS,
    "events_max_late_minutes": EVENTS_LATE_CEILING_MINUTES,
    "events_default_minutes": EVENTS_DURATION_MAX_MINUTES,
    TIME_STEP_KEY: TIME_STEP_MAX_MINUTES,
    "automod_warn_threshold": WARN_THRESHOLD_MAX,
    "chat_cooldown_seconds": CHAT_COOLDOWN_MAX_SECONDS,
    "chat_escalation_names": CHAT_ESCALATION_NAMES_MAX,
    "chat_person_hourly_turns": CHAT_TURNS_MAX,
    "chat_daily_turns": CHAT_TURNS_MAX,
    "chat_monthly_cap_usd": CHAT_MONTHLY_CAP_MAX,
    "chat_memory_retention_days": RETENTION_MAX_DAYS,
    "chat_memory_notes_max": NOTES_CEILING,
    "chat_memory_threads_max": THREADS_CEILING,
    "poll_default_hours": POLL_MAX_HOURS,
    "poll_reminder_minutes": POLL_REMINDER_MAX_MINUTES,
    "poll_archive_days": POLL_ARCHIVE_MAX_DAYS,
    "cost_hosting_usd": COST_HOSTING_MAX_USD,
    "raidtrain_slot_minutes": RAIDTRAIN_SLOT_MAX_MINUTES,
    "raidtrain_reminder_minutes": RAIDTRAIN_REMINDER_MAX_MINUTES,
    "raidtrain_poll_minutes": RAIDTRAIN_POLL_MAX_MINUTES,
    "raidtrain_max_slots_per_member": RAIDTRAIN_SLOTS_PER_MEMBER_MAX,
    "pings_streamer_stale_days": PINGS_STALE_MAX_DAYS,
    "pings_empty_role_days": PINGS_EMPTY_ROLE_MAX_DAYS,
    "pings_onboarding_option_cap": PINGS_OPTION_CAP_MAX,
}

KEY_MIN: dict[str, int] = {
    "pings_streamer_stale_days": PINGS_STALE_MIN_DAYS,
    "pings_empty_role_days": PINGS_EMPTY_ROLE_MIN_DAYS,
    "pings_onboarding_option_cap": PINGS_OPTION_CAP_MIN,
    "events_channel_retention_days": EVENTS_RETENTION_MIN_DAYS,
    EVENTS_TEST_RETENTION_KEY: EVENTS_TEST_RETENTION_MIN_MINUTES,
    WHERE_CHECK_SECONDS_KEY: WHERE_CHECK_MIN_SECONDS,
    "events_default_minutes": EVENTS_DURATION_MIN_MINUTES,
    TIME_STEP_KEY: TIME_STEP_MIN_MINUTES,
    "chat_cooldown_seconds": CHAT_COOLDOWN_MIN_SECONDS,
    "poll_default_hours": POLL_MIN_HOURS,
    "poll_archive_days": POLL_ARCHIVE_MIN_DAYS,
    "raidtrain_slot_minutes": RAIDTRAIN_SLOT_MIN_MINUTES,
    "raidtrain_reminder_minutes": RAIDTRAIN_REMINDER_MIN_MINUTES,
    "raidtrain_poll_minutes": RAIDTRAIN_POLL_MIN_MINUTES,
}

KEY_MIN_REASON: dict[str, str] = {
    "events_default_minutes": (
        "An event shorter than {limit} minutes is over before anybody has read the announcement, "
        "and whoever proposes one can still pick a shorter length from How long."
    ),
    TIME_STEP_KEY: (
        "Minutes finer than every {limit} would need more than twelve options, which is more "
        "than one dropdown can hold and more than anybody wants to scroll."
    ),
    "events_channel_retention_days": (
        "Deleting a finished event's channel the moment it ends throws away the record before "
        "anybody has read it, so the shortest Black Bloc will keep one is {limit} day."
    ),
    EVENTS_TEST_RETENTION_KEY: (
        "The sweep that deletes a test event's room only runs every five minutes, so anything "
        "under {limit} minute is the same as {limit} minute and only reads as broken."
    ),
    WHERE_CHECK_SECONDS_KEY: (
        "A link check given less than {limit} second never gets an answer back, so every link "
        "typed would be called unreachable. Set `events_where_link_check` to off if you would "
        "rather no link was tried at all."
    ),
    "chat_cooldown_seconds": (
        "A gap shorter than {limit} seconds lets one person hold Black Bloc in a back-and-forth "
        "that fills the channel. Set `chat_mode` to off if you want it quiet altogether."
    ),
    "poll_default_hours": (
        "Discord counts a poll's length in whole hours and will not take less than {limit}, so "
        "a shorter one could never be posted."
    ),
    "poll_archive_days": (
        "Archiving a poll the day it closes hides the result before anybody has read it, so the "
        "shortest Black Bloc will wait is {limit} day."
    ),
    "raidtrain_slot_minutes": (
        "A raid train slot shorter than {limit} minutes is not long enough for anybody to start "
        "a stream, be raided into and hand the audience on again."
    ),
    "raidtrain_reminder_minutes": (
        "A warning less than {limit} minutes before a slot is not enough notice to get a stream "
        "up. Turn raid trains off altogether if you would rather Black Bloc said nothing."
    ),
    "raidtrain_poll_minutes": (
        "The sweep is what sends the reminders and spots who is live, and it cannot run more "
        "often than once every {limit} minute."
    ),
    "pings_streamer_stale_days": (
        "Somebody who streamed inside the last {limit} days is still somebody a member might "
        "want to follow, so that is the shortest Black Bloc will keep them on the list."
    ),
    "pings_empty_role_days": (
        "A ping role made and dropped inside {limit} day is almost always somebody changing "
        "their mind mid-press, so that is the shortest grace Black Bloc will give one."
    ),
    "pings_onboarding_option_cap": (
        "A prompt with no options on it is a prompt nobody can answer, so {limit} is the "
        "smallest cap there is. Turn `pings_onboarding_managed` off to have no prompt at all."
    ),
}

KEY_MAX_REASON: dict[str, str] = {
    "honeypot_purge_days": (
        "Discord itself refuses to delete more than {limit} days of a banned account's "
        "messages, and a bigger number would make every ban fail."
    ),
    "events_channel_retention_days": (
        "A finished event's channel kept for more than {limit} days is a channel nobody will "
        "ever tidy up."
    ),
    EVENTS_TEST_RETENTION_KEY: (
        "{limit} minutes is a whole day, and a test room kept longer than that is not a test "
        "room any more. `events_channel_retention_days` is the setting for rooms meant to last."
    ),
    WHERE_CHECK_SECONDS_KEY: (
        "Discord closes a box that has not been answered within three seconds, so waiting "
        "longer than {limit} seconds on a link would lose whatever was typed into it. Set "
        "`events_where_link_check` to off if you would rather no link was tried at all."
    ),
    "events_max_late_minutes": (
        "Announcing an event more than {limit} minutes after it started tells people to come to "
        "something that is already half over."
    ),
    "events_default_minutes": (
        "Black Bloc will not carry an event longer than {limit} minutes — a week — so a default "
        "above that would refuse every proposal that left How long alone."
    ),
    TIME_STEP_KEY: (
        "A step of {limit} minutes is one option, on the hour, which is as coarse as the Minute "
        "dropdown gets. Anything larger would leave it with nothing to offer."
    ),
    "automod_warn_threshold": (
        "A warning count above {limit} is a number nobody is reading any more. Set it to 0 to "
        "stop counting warnings at all."
    ),
    "chat_cooldown_seconds": (
        "A gap longer than {limit} seconds means most people never get an answer at all, which "
        "reads as a broken bot rather than a quiet one."
    ),
    "poll_default_hours": (
        "Discord closes every poll within 32 days, so {limit} hours is the longest one there is."
    ),
    "poll_reminder_minutes": (
        "A last call more than {limit} minutes before a poll closes is not a last call. Set it "
        "to 0 if you would rather Black Bloc said nothing."
    ),
    "poll_archive_days": (
        "A poll kept out of the archive for more than {limit} days is one nobody will ever "
        "tidy away. Nothing is deleted at the archive except the per-voter rows, and only when "
        "`poll_archive_drop_votes` says so."
    ),
    "chat_person_hourly_turns": (
        "More than {limit} conversational answers to one person in an hour is not a ceiling, it "
        "is a typo. Set it to 0 if you genuinely want no ceiling of its own — the dollar figure "
        "still applies."
    ),
    "chat_daily_turns": (
        "More than {limit} conversational answers in a day is not a ceiling, it is a typo. Set "
        "it to 0 if you genuinely want no ceiling of its own."
    ),
    "chat_monthly_cap_usd": (
        "Black Bloc refuses to be pointed at more than ${limit} a month by accident. If that is "
        "really what you want, a Lead should say so out loud first."
    ),
    "chat_escalation_names": (
        "Naming more than {limit} people is a list nobody reads, and the point is to hand "
        "somebody one or two names they can go to. Set it to 0 to name nobody at all."
    ),
    "cost_hosting_usd": (
        "A hosting bill over ${limit} a month is not this bot, it is a typo. Check the invoice "
        "and put in the monthly figure."
    ),
    "raidtrain_slot_minutes": (
        "A slot longer than {limit} minutes is half a day of one stream, which is not a raid "
        "train. Run two trains instead."
    ),
    "raidtrain_reminder_minutes": (
        "A reminder more than {limit} minutes before a slot arrives the day before and is "
        "forgotten by the time it matters."
    ),
    "raidtrain_poll_minutes": (
        "A sweep that runs less often than every {limit} minutes would miss its own reminder "
        "window, so the DMs would arrive late or not at all."
    ),
    "raidtrain_max_slots_per_member": (
        "No raid train Black Bloc will build has more than {limit} slots, so a ceiling above "
        "that is the same as no ceiling — set it to 0 for that."
    ),
    "pings_streamer_stale_days": (
        "Somebody who has not streamed in {limit} days is not somebody anybody is waiting on, "
        "and a list nobody can find a name in is worse than a shorter one."
    ),
    "pings_empty_role_days": (
        "A role nobody has worn for {limit} days is one of the 250 this server is allowed, held "
        "for nothing. The next follow makes a fresh one in a second."
    ),
    "pings_onboarding_option_cap": (
        "Discord publishes no ceiling for options on an onboarding prompt, so Black Bloc will "
        "not ask it for more than {limit} and have the whole write refused."
    ),
}

KEY_HELP: dict[str, str] = {
    "log_channel_id": "where Black Bloc posts what it did",
    "staff_channel_id": "the channel whose viewers count as staff",
    "role_menu_channel_id": "the channel /rolemenu offers first when a menu is posted",
    "golive_mode": "off, shadow (log only) or on (post go-live announcements)",
    "golive_channel_id": "where go-live announcements are posted",
    "golive_template": "the announcement wording; {name} {game} {title} {url} {platform}",
    "golive_end_mode": (
        "what happens to the announcement when the stream ends: off leaves it as posted, "
        "edit appends the ended wording and marks the card"
    ),
    "golive_end_suffix": (
        "what is added to an announcement once the stream has ended; only used when "
        "golive_end_mode is edit"
    ),
    "golive_end_template": (
        "the whole announcement once the stream is over; {name} {game} {title} {url} "
        "{platform} {duration}; blank keeps the live sentence and appends golive_end_suffix "
        "as before"
    ),
    "golive_end_author": (
        "the card's top line once the stream is over; {name} {platform} {duration}; blank "
        "keeps 'was live on'"
    ),
    "golive_end_keep_mention": (
        "on keeps the role mention at the front of the edited announcement; off drops it — "
        "nobody is pinged by an edit either way"
    ),
    GOLIVE_COSTREAM_MODE_KEY: (
        "on names both platforms in one announcement when somebody streaming on Twitch also "
        "goes live on YouTube (or the other way round) and edits the post that is already "
        "there; off holds the second platform back, as it did before"
    ),
    GOLIVE_COSTREAM_TEMPLATE_KEY: (
        "the announcement wording while two platforms are live; {name} {game} {title} {url} "
        "{platform} {also_url} {also_platform}. Twitch is always written first and is the only "
        "link Discord previews — {also_url} is always posted with its preview suppressed"
    ),
    GOLIVE_COSTREAM_AUTHOR_KEY: (
        "the card's top line while two platforms are live; {name} {game} {title} {url} "
        "{platform} {also_url} {also_platform}"
    ),
    "golive_live_role_id": "role given while someone is streaming",
    "golive_require_role_id": "only announce people who have this role",
    "golive_ignore_role_id": "never announce people who have this role",
    "golive_cooldown_minutes": "minutes before the same person is announced again",
    "golive_ping_role_id": "role mentioned in front of every go-live announcement",
    "golive_max_session_hours": "hours before a stream still marked live is closed anyway",
    "golive_embed": (
        "post the announcement as an embed with the game's art; off = the sentence only"
    ),
    "golive_boot_sweep": (
        "true walks every member's Discord presence at boot and announces anyone already "
        "streaming with no session; false trusts presence updates alone, as before v149"
    ),
    "pings_mode": (
        "off, or on (members can opt in to go-live and event pings, and a streamer can have a "
        "role of their own that only their followers wear)"
    ),
    "pings_events_role_name": (
        "what **Set up the Events role** on `/pings` calls the one opt-in role for go-live and "
        "event pings when it has to make it; an existing role of that name is reused rather than "
        "duplicated"
    ),
    "pings_fan_role_creation": (
        "when a streamer's ping role is made: follow (the first person to follow them on "
        "`/pings` makes it, which is the default so a role exists only where somebody wants "
        "it), self (the streamer, with **Start my own ping role** on `/pings`), staff (only an "
        "Auntie/Uncle, from `/pings` ▸ **Streamers…**), or auto (one is made the moment a Twitch "
        "channel is linked). Staff can always do it for anybody, whichever this says"
    ),
    "pings_fan_role_template": (
        "what a streamer's own ping role is called; {name} is their display name at the moment "
        "the role is made and is the only field there is"
    ),
    "pings_fan_role_on_unlink": (
        "what happens to a streamer's ping role when they unlink Twitch or opt out of "
        "announcements: keep leaves it alone (nothing is announced, so nobody is pinged), delete "
        "takes the role off the server"
    ),
    "pings_fan_role_delete": (
        "true to delete the Discord role itself when a streamer's ping role is removed; false "
        "forgets the role here and leaves it on the server for somebody to tidy by hand"
    ),
    "pings_streamer_stale_days": (
        "days without a go-live before somebody leaves the streamer list `/pings` ▸ **Follow a "
        "streamer…** offers; their ping role is kept while anybody still wears it, and one more "
        "go-live puts them back on"
    ),
    "pings_empty_role_days": (
        "days a streamer's ping role that nobody wears survives before Black Bloc deletes it, so "
        "the server's role count tracks who is actually followed; a role somebody wears is never "
        "deleted by this"
    ),
    "pings_onboarding_managed": (
        "true to let Black Bloc keep its two Discord onboarding prompts in step with the Events, "
        "raid-train and streamer roles; false leaves the prompts exactly as they are and Black "
        "Bloc never writes to onboarding again. Only does anything on a Community server"
    ),
    "pings_onboarding_prompt_title": (
        "what Black Bloc's first onboarding prompt is called; it is also how Black Bloc knows "
        "which prompts are its own, so changing it makes a fresh pair and leaves the old ones "
        "for somebody to delete by hand"
    ),
    "pings_onboarding_option_cap": (
        "how many streamers the **Which streamers?** onboarding prompt lists before it says how "
        "many more are on `/pings`. Discord publishes no number for this, so 25 is Black Bloc's "
        "own conservative cap — raise it and Discord refuses in words if it is too high"
    ),
    "tempvoice_mode": (
        "off, shadow (join-to-create works, but only staff can see the lobby — the rooms it "
        "spawns follow it), or on (the lobby is visible to whoever its category shows)"
    ),
    "tempvoice_creator_ids": "the join-to-create channels; Setup on /voice fills this in",
    "tempvoice_name_template": "what a spawned channel is called; {user} is the member",
    "tempvoice_creator_name": "what the join-to-create channel itself is called",
    "tempvoice_allowed_role_id": "only members with this role get a temporary channel",
    "tempvoice_room_overwrites": (
        "what a new room's permissions start from: lobby (the join-to-create channel's own — "
        "a staff-only lobby makes staff-only rooms) or category (the category's, as before)"
    ),
    "honeypot_mode": "off, shadow (log only) or on (ban whoever posts in the trap)",
    "honeypot_channel_ids": "the trap channels; Setup… on /honeypot fills this in",
    "honeypot_purge_days": (
        f"days of the banned account's messages to delete with it, 0 to "
        f"{HONEYPOT_PURGE_MAX_DAYS}"
    ),
    "honeypot_exempt_role_ids": "roles the trap ignores; staff are always ignored too",
    "events_mode": "off, shadow (no public announcement) or on (announce approved events)",
    "events_category_id": "the category review channels are made in; /event settings sets it",
    "events_announce_channel_id": "where an approved event is announced and pinged when it starts",
    "events_ping_role_id": "role mentioned when an event is announced and when it starts",
    "events_create_scheduled": "true to make a real Discord scheduled event when one is approved",
    "events_where_link_in_description": (
        "true to put the link or note typed beside a channel at the end of the Discord scheduled "
        "event's description, where a channel event has nowhere else to show it"
    ),
    WHERE_ALIASES_KEY: (
        f"the shorthands the Where box turns into links, `alias=https://host/{HANDLE_PLACEHOLDER}`"
        f" entries separated by commas, up to {WHERE_ALIAS_MAX} of them — so `ttv skyaiva` is "
        f"stored as `https://twitch.tv/skyaiva`. An entry Black Bloc cannot read is dropped, and "
        f"a bare host like `twitch.tv/skyaiva` is a link whatever this holds"
    ),
    WHERE_CHECK_KEY: (
        "whether a link typed into the Where box is opened once before it is kept: off (never "
        "tried), warn (kept either way, with a note on the draft when it does not answer) or "
        "refuse (the box says so in words and keeps the old place). Twitch answers for any "
        "channel name, so a misspelt Twitch name passes whatever this holds"
    ),
    WHERE_CHECK_SECONDS_KEY: (
        f"seconds the link check waits for an answer, {WHERE_CHECK_MIN_SECONDS} to "
        f"{WHERE_CHECK_MAX_SECONDS}; Discord closes a box that has not answered within three "
        f"seconds, so the panel has to render in what is left"
    ),
    WHERE_HINT_KEY: (
        "the sentence directly above the channel picker on the Where panel, and on the draft "
        "card's Where line while "
        "nothing is picked — Discord's picker only lists the first page of channels until "
        "somebody types, so this says so. Leave it empty and no such line is shown"
    ),
    "events_channel_retention_days": (
        f"days a finished event's channel is kept before deletion, "
        f"{EVENTS_RETENTION_MIN_DAYS} to {EVENTS_RETENTION_MAX_DAYS}. Staff can remove a room "
        f"sooner with **Delete this room** in the room itself"
    ),
    EVENTS_TEST_RETENTION_KEY: (
        f"minutes a finished or refused event's review room is kept while Black Bloc is in test "
        f"mode, {EVENTS_TEST_RETENTION_MIN_MINUTES} to {EVENTS_TEST_RETENTION_MAX_MINUTES}; the "
        f"real retention is `events_channel_retention_days`. The sweep runs every five minutes, "
        f"so a room goes between this many minutes and five minutes later. Staff can remove a "
        f"room sooner with **Delete this room** in the room itself"
    ),
    EVENTS_POSTS_WHERE_KEY: (
        "where an approved event's posts go: room (the event's own review room — the "
        "announcement, the go-live ping and the line saying it has ended), announce (only "
        "`events_announce_channel_id`, which is how it worked before rooms), or both"
    ),
    EVENTS_ROOM_DELETE_KEY: (
        "who may press **Delete this room**: staff, or approver — the role in "
        "`events_approver_role_id`. Staff can always press it whichever this holds"
    ),
    EVENTS_APPROVER_ROLE_KEY: (
        "the role **Delete this room** asks for when `events_room_delete_who` is approver; "
        "blank falls back to staff"
    ),
    EVENTS_ROOM_NOTICE_KEY: (
        "true to post the message carrying **Delete this room** in every review room Black "
        "Bloc makes; false posts nothing and the sweep still tidies the room away on its own"
    ),
    EVENTS_REVIEW_MODE_KEY: (
        "where a proposed event is reviewed: room makes a text channel per event under "
        "`events_category_id`; forum makes one post per event in `events_forum_channel_id` "
        "(**Make the forum** on `/event` first). Changing it only affects events proposed "
        "afterwards — the ones already open keep the room or post they have"
    ),
    EVENTS_FORUM_CHANNEL_KEY: (
        "the forum channel every event is posted in, in forum mode; **Make the forum** on "
        "`/event` ▸ **Settings** ▸ **Rooms…** makes one under the BlackMail category"
    ),
    EVENTS_MOVED_LINE_KEY: (
        f"the one line left in an event's old review room when staff press **Move to the "
        f"forum**; `{POST_PLACEHOLDER}` stands for the new post and is the only thing that may "
        "be filled in. The room is removed straight after, so this is the last thing said in it"
    ),
    REQUEST_FILED_KEY: (
        "what a member is told the moment their request is filed; "
        f"`{REQUEST_ID_PLACEHOLDER}` stands for the request's number and is the only thing "
        "that may be filled in"
    ),
    "events_max_late_minutes": (
        "minutes an event may start late and still be announced; later than that it goes live "
        "quietly"
    ),
    "events_default_minutes": (
        f"how long a proposed event runs when nobody changes How long, "
        f"{EVENTS_DURATION_MIN_MINUTES} to {EVENTS_DURATION_MAX_MINUTES} minutes; whoever "
        "proposes one picks their own length from the dropdown"
    ),
    EVENTS_SCHEDULED_NAME_KEY: (
        f"what an approved event is called on Discord's own calendar; `{NAME_PLACEHOLDER}` "
        f"stands for the event's title and is the only thing that may be filled in, so "
        f"`{EVENTS_SCHEDULED_NAME_TEMPLATE}` reads as `Cookout {EVENTS_SCHEDULED_NAME_TEMPLATE}`"
        " minus the placeholder. The review card, the announcement and the DM keep the plain "
        "title"
    ),
    DEFAULT_TIMEZONE_KEY: (
        "the `Region/City` zone times are read in for anybody who has never picked their own — "
        "the Time zone button on `/event` is how a member changes theirs"
    ),
    TIMEZONE_CHOICES_KEY: (
        f"the zones the Time zone dropdown offers, `Region/City` names separated by commas, up "
        f"to {TIMEZONE_CHOICES_MAX} of them; a name Black Bloc cannot resolve is dropped, and "
        "Other — type it… always sits at the bottom of the list for the rest"
    ),
    TIME_STEP_KEY: (
        f"how far apart the Minute dropdown's choices are on the /event and /raidtrain draft "
        f"panels, {TIME_STEP_MIN_MINUTES} to {TIME_STEP_MAX_MINUTES} minutes; 15 gives :00, "
        ":15, :30 and :45"
    ),
    "poll_mode": (
        "off, shadow (every poll is posted for real, but into the log channel with a line "
        "saying why, so staff can rehearse), or on (polls go where they are pointed)"
    ),
    "poll_who_can_create": "who may start a poll from the /poll panel: staff, or everyone",
    "poll_review_mode": (
        "off posts a poll straight away; on holds it for a staff Approve or Deny first"
    ),
    "poll_default_hours": (
        f"hours a poll stays open when nobody says otherwise, {POLL_MIN_HOURS} to "
        f"{POLL_MAX_HOURS} (32 days)"
    ),
    "poll_channel_id": (
        "where a poll made from the dashboard goes; the /poll panel offers the channel it was "
        "opened in and lets you pick another"
    ),
    "poll_ping_role_id": "role mentioned when a poll opens; blank pings nobody",
    "poll_reminder_minutes": (
        f"minutes before a poll closes that Black Bloc posts a last call, 0 to say nothing, up "
        f"to {POLL_REMINDER_MAX_MINUTES}"
    ),
    "poll_auto_thread": "true to open a discussion thread under every poll",
    "poll_pin": (
        "true pins a poll's message while it is open and unpins it when it closes"
    ),
    "poll_shadow_note": (
        "the line above a poll posted in shadow; {channel} is where it would have gone"
    ),
    "poll_archive_days": (
        f"days a closed poll stays on the list before it moves to the archive, "
        f"{POLL_ARCHIVE_MIN_DAYS} to {POLL_ARCHIVE_MAX_DAYS}"
    ),
    "poll_archive_drop_votes": (
        "true to forget who voted when a poll is archived; the totals are kept either way"
    ),
    "poll_date_labels": (
        "how a date poll writes its slots: plain (Sat 30 Aug · 7 pm, in the server's zone) or "
        "timestamp (each reader sees their own clock, if Discord renders one in an answer)"
    ),
    "birthday_mode": "off, shadow (log only) or on (post birthday wishes)",
    "birthday_channel_id": "where birthday wishes are posted",
    "birthday_template": "the birthday wording; {name} and {age}",
    "birthday_color": "the birthday embed's colour, as a hex code like #4eefff",
    "birthday_role_id": "role given for the day and taken back the next; none by default",
    "birthday_show_age": "true to put {age} in reach for people who stored a birth year",
    "modmail_enabled": "true when Black Bloc answers DMs; false leaves them to the old ModMail bot",
    "modmail_mode": (
        "channel (one channel per ticket), thread (private threads in the staff channel) or "
        "forum (one post per ticket in the forum channel — the list never grows past the "
        "forum's own archive)"
    ),
    "modmail_category_id": "the category ticket channels are made in, in channel mode",
    "modmail_staff_channel_id": "the channel ticket threads are made in, in thread mode",
    "modmail_log_channel_id": "where a closed ticket's transcript is posted",
    "automod_mode": "off, shadow (log what it would do) or on (delete, warn and time out)",
    "automod_rules": "the automod rule book; /automod then A rule… is what changes it",
    "automod_exempt_role_ids": "roles automod ignores; staff are always ignored too",
    "automod_exempt_channel_ids": "channels automod never reads",
    "automod_warn_threshold": "warnings before Black Bloc says so in the log, 0 to stop counting",
    "modlog_channel_id": "where mod cases are posted; defaults to log_channel_id",
    "mod_dm_on_action": "what a punished member is told: none, server_action, server_action_reason",
    "bot_bio": "the About Me on Black Bloc's own profile, dashboard link and all",
    "status_prefix": "what goes in front of the member count in Black Bloc's status",
    "rolemenu_mode": (
        "whether members can pick roles from the panels; off takes them down and hides the "
        "posted panels, on posts them again; /rolemenu itself stays either way"
    ),
    "request_mode": (
        "off, or on (members can ask for things with /request and staff decide on the site)"
    ),
    "request_who_can_file": "who may file a request: everyone, or staff only",
    "request_status_channel_id": (
        "where a line goes each time staff move a request — picked up, on hold, done, declined; "
        "blank uses request_notify_channel_id, so one channel carries both"
    ),
    "request_notify_channel_id": (
        "where one line goes when a request is filed; blank tells nobody and the site is the only "
        "place they show up"
    ),
    "request_forum_channel_id": (
        "a forum channel where every request is its own post; blank posts the card into "
        "request_notify_channel_id as before. /request ▸ Make the forum… makes one under the "
        "ticket category"
    ),
    "request_dm_on_decision": (
        "true to DM the person who asked every time staff move their request — picked up, on "
        "hold, done or declined"
    ),
    "chat_mode": "off, or on (Black Bloc answers when somebody @-mentions it)",
    "chat_cooldown_seconds": (
        f"seconds before the same person gets another @-mention reply, "
        f"{CHAT_COOLDOWN_MIN_SECONDS} to {CHAT_COOLDOWN_MAX_SECONDS}"
    ),
    "chat_ignore_channels": "channels Black Bloc never answers an @-mention in",
    "chat_ignore_categories": (
        "categories Black Bloc leaves out of everything it reads and tells people about — the "
        "channel names and topics it learns each day, and the channel list every conversational "
        "answer is written against. The modmail category and any category with `archive` in its "
        "name are left out already, and so is every channel @everyone cannot see"
    ),
    "chat_home_channel_id": (
        "where somebody is sent when a conversational answer points at a channel that does not "
        "exist. Blank is safe: the sentence is written again without the channel in it rather "
        "than pointing anywhere. Either way the invention is logged, so `/chat` ▸ **Logs** and "
        "the Logs page count how often it happens"
    ),
    "chat_visibility_role_id": (
        "the role whose view of the server IS the bot's map: channels this role can read are "
        "the ones the bot may learn about, list and point people at. This server hides "
        "everything from @everyone until the rules screen grants Member, so the default is the "
        "Member role — clearing it falls back to @everyone, which on this server means almost "
        "no channels at all"
    ),
    "chat_staff_can_ping_roles": (
        "on lets Black Bloc's conversational answers mention a role when the person who "
        "@-mentioned it is staff — an Auntie or Uncle and up. Nobody else can make it ping "
        "anything, and `@everyone` and `@here` never go through for anyone. Off means a "
        "conversational answer pings nobody at all, whoever asked"
    ),
    "chat_escalation_names": (
        "how many online staff Black Bloc names when somebody asks for a mod, 0 to name "
        "nobody and up to 10. They are named in plain words, never pinged — the person "
        "does that themselves. Nobody online says so instead"
    ),
    "chat_greeting_reaction": (
        "true to answer a bare hello with a wave reaction instead of a sentence; anything "
        "longer still gets a reply"
    ),
    "chat_reply_in_threads": "true to answer @-mentions inside threads as well as channels",
    "chat_route_ping_staff": (
        "true to drop one line in the staff channel when somebody asks the bot for a mod; only "
        "used while modmail_enabled is true"
    ),
    "chat_llm_mode": (
        "off, or on (an @-mention no built-in intent recognises is answered by a language model "
        "instead of the catch-all line). Off is the default and off is safe: with it off, or "
        "with no keys set, Black Bloc answers exactly as it does today"
    ),
    "chat_simple_model": (
        "which Groq model the quick tier asks; it is a setting because Groq retires model names "
        "faster than a deploy can follow"
    ),
    "chat_personality": (
        "the voice Black Bloc writes a conversational answer in: cookout is the house voice, "
        "pool lets a conversation pick one of the moods and drift a step at a time, or name one "
        "mood to keep it. Only used when chat_llm_mode is on"
    ),
    "chat_person_hourly_turns": (
        f"how many conversational answers one member may get in a rolling hour, up to "
        f"{CHAT_TURNS_MAX}; 0 means no ceiling of its own. Past it they still get Black Bloc's "
        f"own written lines"
    ),
    "chat_daily_turns": (
        f"how many conversational answers the whole server may get in a UTC day, up to "
        f"{CHAT_TURNS_MAX}; 0 means no ceiling of its own"
    ),
    "chat_monthly_cap_usd": (
        f"whole dollars a month Black Bloc may run the conversation models for, up to "
        f"{CHAT_MONTHLY_CAP_MAX}. At the figure it stops calling them until the 1st and answers "
        f"from its own written lines; 0 stops them altogether"
    ),
    "chat_status_admin_only": (
        "on keeps the spend block on `/chat` (what the conversation models are spending) to "
        "server administrators; the rest of the panel still opens for any staff member, and off "
        "lets them read the spend too. The dashboard's Spend section stays staff-visible either "
        "way"
    ),
    "chat_memory_mode": (
        "off, or on (Black Bloc keeps a few preferences about each person — what to call them, "
        "how they like to be answered — and reads them back next time). Off writes nothing and "
        "reads nothing; the profiles already stored stay until somebody clears them"
    ),
    "chat_memory_consent": (
        "optout means memory is on for everybody until they stop it themselves on the `/memory` "
        "panel; optin means nobody is remembered until they start it there"
    ),
    "chat_memory_retention_days": (
        f"days a profile nobody has added to is kept before it is deleted, up to "
        f"{RETENTION_MAX_DAYS}; 0 keeps them forever. Leaving the server clears one straight away"
    ),
    "chat_memory_dm_scope": (
        "separate keeps what Black Bloc learns in a DM out of public channels — a name or "
        "pronouns set by DM never reach the server; shared lets every note be used anywhere"
    ),
    "chat_memory_staff_view": (
        "counts shows staff only how many profiles there are and when each changed; full lets "
        "staff read the notes themselves. The person can always read their own with `/memory`"
    ),
    "chat_memory_notes_max": (
        f"how many preferences one profile holds, up to {NOTES_CEILING}; the oldest drops off "
        f"when a newer one arrives"
    ),
    "chat_memory_threads_max": (
        f"how many open topics (“was asking about the Thursday event”) one profile "
        f"holds, up to {THREADS_CEILING}"
    ),
    "chat_memory_model": (
        "which Groq model writes the profile up after a conversation ends; blank uses "
        "chat_simple_model, the same quick tier that answers"
    ),
    "rolemenu_approval_channel_id": (
        "where a role request waits for Approve or Deny; blank uses staff_channel_id"
    ),
    "rolemenu_approver_role_id": (
        "role mentioned when a role request arrives; blank pings nobody"
    ),
    "emoji_skin_tone": (
        f"the skin tone Black Bloc's hand and people emoji wear: "
        f"{', '.join(SKIN_TONE_NAMES)}"
    ),
    "cost_hosting_usd": (
        "what the always-on container costs a month in whole dollars — read it off your Fly "
        "invoice; 0 = not filled in yet, and the Costs card on the Health page says so rather "
        "than claiming hosting is free"
    ),
    "raidtrain_mode": (
        "off, shadow (log what would be sent and send nothing) or on (post the lineup and DM "
        "slot holders before their hour)"
    ),
    "raidtrain_organizer_role_id": (
        "role that may build and change a raid train's lineup as well as staff; blank leaves it "
        "to staff alone"
    ),
    "raidtrain_channel_id": (
        "where a train's lineup post lives; blank uses events_announce_channel_id"
    ),
    "raidtrain_ping_role_id": (
        "role mentioned in front of a lineup post; blank pings nobody, and members on the "
        "lineup are never pinged by an edit"
    ),
    "raidtrain_slot_minutes": (
        f"how long one slot is by default, {RAIDTRAIN_SLOT_MIN_MINUTES}-"
        f"{RAIDTRAIN_SLOT_MAX_MINUTES} minutes; each train may be created with its own length"
    ),
    "raidtrain_reminder_minutes": (
        "how long before their slot a holder is DMed, with who raids into them and who they "
        "raid next; the DM is sent once"
    ),
    "raidtrain_poll_minutes": (
        "minutes between sweeps that send those reminders, start and finish a train, and notice "
        "who is live"
    ),
    "raidtrain_require_link": (
        "on makes a linked Twitch channel (`/golive` → Link my Twitch channel) a condition of "
        "claiming a slot, so the lineup carries the name the streamer before raids; off lets "
        "anybody claim and leaves the name off"
    ),
    "raidtrain_thread": "on opens a thread under the lineup post for the people on the train",
    "raidtrain_live_posts": (
        "on says `X is live — next up Y` in that thread when a slot holder starts streaming "
        "inside their own hour, and marks the slot checked in"
    ),
    "raidtrain_max_slots_per_member": (
        "how many slots one member may claim on one train; 0 means as many as they like. An "
        "organizer assigning a slot is never held to it"
    ),
    "raidtrain_scheduled_event": (
        "on puts the train on Discord's own event calendar as well. Off by default: Phase 4's "
        "calendar helper writes to the events table, so raid trains keep their own"
    ),
    RAIDTRAIN_SCHEDULED_NAME_KEY: (
        f"what a raid train is called on Discord's own calendar when "
        f"`raidtrain_scheduled_event` is on; `{NAME_PLACEHOLDER}` stands for the train's title "
        f"and is the only thing that may be filled in. It ships as `{NAME_PLACEHOLDER}`, the "
        f"plain title — set it to `{EVENTS_SCHEDULED_NAME_TEMPLATE}` to match what `/event` "
        "events are called. The lineup post, the thread and the DMs keep the plain title"
    ),
}

LOG_LEVEL_HELP = (
    "which {label} log lines reach the Discord log channel: off, important (anything that acted "
    "on a member, or failed) or all. Every line is kept on the dashboard{extra} either way"
)
LOG_LEVEL_COMMANDS: dict[str, str] = {
    CORE: "settings",
    "automod": "automod",
    "honeypot": "honeypot",
    "mod": "mod",
    "modmail": "modmail",
    "golive": "golive",
    "youtube": "youtube",
    "events": "event",
    "birthday": "birthday",
    "tempvoice": "voice",
    "rolemenu": "rolemenu",
    "poll": "poll",
    "chat": "chat",
    "request": "request",
    "pings": "pings",
    "raidtrain": "raidtrain",
    "applications": "apply",
    "selftest": "settings",
    "posts": "posts",
    "minutes": "minutes",
}


def log_level_help(feature: str) -> str:
    """Every feature's Logs is a panel button now; no `/x logs` subcommand is left to name."""
    command = LOG_LEVEL_COMMANDS.get(feature)
    return LOG_LEVEL_HELP.format(
        label=FEATURE_LABELS[feature].lower(),
        extra=f" and in `/{command}` ▸ **Logs**" if command else "",
    )


KEY_TYPES.update({log_level_key(feature): "enum" for feature in FEATURES})
KEY_CHOICES.update({log_level_key(feature): LEVELS for feature in FEATURES})
KEY_HELP.update({log_level_key(feature): log_level_help(feature) for feature in FEATURES})

# Phase 19 — applications. Appended as its own block so the parallel branches merge cleanly.
APPLICATIONS_MODES = ("off", "shadow", "on")
APPLICATIONS_RETRY_DAYS = 30
APPLICATIONS_RETRY_MAX_DAYS = 3650

KEY_TYPES.update(
    {
        "applications_mode": "enum",
        "applications_channel_id": "channel",
        "applications_approver_role_id": "role",
        "applications_ping_role_id": "role",
        "applications_retry_days": "int",
        "applications_dm_on_decision": "bool",
        "applications_roster_shows_left": "bool",
        "applications_panel_minutes": "int",
        "applications_panel_own_list": "bool",
    }
)
KEY_CHOICES["applications_mode"] = APPLICATIONS_MODES
KEY_MAX["applications_retry_days"] = APPLICATIONS_RETRY_MAX_DAYS
KEY_MAX_REASON["applications_retry_days"] = (
    "A wait of more than {limit} days after a no is a permanent no with extra steps. Set it to "
    "0 if somebody may apply again the same day."
)
KEY_HELP.update(
    {
        "applications_mode": (
            "off, shadow (log only, nothing posted or DMed) or on (members can apply and staff "
            "decide on the card)"
        ),
        "applications_channel_id": (
            "where an application card waits for Approve or Deny when the form does not name a "
            "channel of its own; blank falls back to rolemenu_approval_channel_id, then to "
            "staff_channel_id"
        ),
        "applications_approver_role_id": (
            "who may approve or deny an application when the form does not name a role of its "
            "own; blank falls back to rolemenu_approver_role_id, then to staff"
        ),
        "applications_ping_role_id": (
            "role mentioned when a new application arrives; blank pings nobody"
        ),
        "applications_retry_days": (
            "days somebody waits after a decision before they may apply for the same form again; "
            "a form can set its own, and 0 lets them apply again straight away"
        ),
        "applications_dm_on_decision": (
            "true to DM the applicant when their application is approved or denied"
        ),
        "applications_roster_shows_left": (
            "whether the approved list still shows people who have left the server, marked as "
            "gone; false hides them"
        ),
        "applications_panel_minutes": (
            "minutes the /apply panel stays live before its buttons disable themselves; 10 by "
            "default. The 'this panel went quiet' footer can only be written while Discord's "
            "15-minute interaction window is still open, so 15 or more means the buttons simply "
            "stop working with no footer to explain it"
        ),
        "applications_panel_own_list": (
            "whether the /apply panel writes a member's own applications out for them; true by "
            "default, and false makes that list staff-only"
        ),
    }
)

# Requests, third pass — the two decisions the review state introduces. Appended as its own
# block so the parallel branches merge cleanly.
REQUEST_CARD_MOVES = (
    "filed",
    "in_progress",
    "review",
    "sent_back",
    "done",
    "hold",
    "declined",
    "check_asked",
)
REQUEST_CARD_DEFAULT = tuple(
    move for move in REQUEST_CARD_MOVES if move not in ("done", "check_asked")
)

KEY_TYPES.update(
    {
        "request_channel_moves": "enums",
        "request_review_by_other": "bool",
        "request_panel_minutes": "int",
        "request_panel_own_list": "bool",
        "request_check_fallback_channel": "bool",
        "request_check_on_ready": "bool",
        "request_post_buttons": "bool",
        "request_forum_adopts_posts": "bool",
    }
)
KEY_CHOICES["request_channel_moves"] = REQUEST_CARD_MOVES
KEY_HELP.update(
    {
        "request_channel_moves": (
            "which moves put a card in the request channel: filed, in_progress, review, "
            "sent_back, done, hold, declined, check_asked; every one but done and check_asked "
            "by default (the done card repeats what the site's log already says, and the "
            "check card is a DM to one person), and an empty list posts nothing at all"
        ),
        "request_review_by_other": (
            "true to make somebody other than the staffer who marked a request ready to check "
            "be the one who accepts it"
        ),
        "request_panel_minutes": (
            "minutes the /request panel stays live before its buttons disable themselves; 10 "
            "by default. The 'this panel has gone quiet' footer can only be written while "
            "Discord's 15-minute interaction window is still open, so 15 or more means the "
            "buttons simply stop working with no footer to explain it"
        ),
        "request_panel_own_list": (
            "true to show members their own requests on the /request panel; staff always see "
            "them, and members can still file and take one back"
        ),
        "request_check_fallback_channel": (
            "true to ping the person who asked in the request channel when Ask-them-to-check "
            "cannot DM them (closed DMs); false to tell staff nobody was reached and leave it "
            "there"
        ),
        "request_check_on_ready": (
            "true to ask the person who asked to try the work the moment a request is marked "
            "ready to check, without a staffer pressing Ask them to check"
        ),
        "request_post_buttons": (
            "true draws the staff move buttons on each request's forum post (and edits them as "
            "the request moves); false leaves the post a notice with the site link"
        ),
        "request_forum_adopts_posts": (
            "true turns a post somebody starts by hand in the requests forum into a request "
            "filed by them; false leaves such posts alone"
        ),
    }
)


# Send to... (v127) -- the staff hand-offs between requests, events and modmail tickets. Its own
# block so the parallel branches merge textually; both keys are filed under the `request`
# namespace through NAMESPACE_OVERRIDE, because `/settings` group select is at its cap of 25.
# Design: info/send-to-design.md.
HANDOFF_MODE = "handoff_mode"
HANDOFF_CONFIRM_HOURS = "handoff_confirm_hours"
HANDOFF_MODES = ("off", "on")
HANDOFF_CONFIRM_HOURS_DEFAULT = 24
HANDOFF_CONFIRM_HOURS_MIN = 1
HANDOFF_CONFIRM_HOURS_MAX = 168
KEY_TYPES.update({HANDOFF_MODE: "enum", HANDOFF_CONFIRM_HOURS: "int"})
KEY_CHOICES[HANDOFF_MODE] = HANDOFF_MODES
KEY_MIN[HANDOFF_CONFIRM_HOURS] = HANDOFF_CONFIRM_HOURS_MIN
KEY_MAX[HANDOFF_CONFIRM_HOURS] = HANDOFF_CONFIRM_HOURS_MAX
KEY_MIN_REASON[HANDOFF_CONFIRM_HOURS] = (
    "Less than {limit} hour is not long enough for somebody to read a DM and answer it, so the "
    "question would count as no before they ever saw it."
)
KEY_MAX_REASON[HANDOFF_CONFIRM_HOURS] = (
    "More than {limit} hours is a week, and a ticket nobody can file anything else from for a "
    "week is a ticket staff have lost the use of."
)
KEY_HELP.update(
    {
        HANDOFF_MODE: (
            "on draws the Send to... moves for staff -- a request becomes an event, an event "
            "becomes a request, a ticket becomes either with the member's say-so; off hides "
            "them and refuses a stale press in words"
        ),
        HANDOFF_CONFIRM_HOURS: (
            "how long a member has to answer a make-this-a-request/event DM before it counts "
            "as no; the ticket stays open either way"
        ),
    }
)

# Birthdays, the panel pass (wave 1). Appended as its own block so the parallel branches
# merge cleanly.
KEY_TYPES.update(
    {
        "birthday_panel_minutes": "int",
        "birthday_panel_next_for_members": "bool",
        "birthday_panel_lookup": "bool",
    }
)
KEY_HELP.update(
    {
        "birthday_panel_minutes": (
            "minutes the /birthday panel stays live before its buttons disable themselves; 10 "
            "by default. The 'this panel has gone quiet' footer can only be written while "
            "Discord's 15-minute interaction window is still open, so 15 or more means the "
            "buttons simply stop working with no footer to explain it"
        ),
        "birthday_panel_next_for_members": (
            "true to show every member the birthdays coming up on the /birthday panel; staff "
            "always see them. False makes the list staff-only and the panel says so in words"
        ),
        "birthday_panel_lookup": (
            "true to let any member look somebody else's stored birthday up on the /birthday "
            "panel; staff always can. Opting out is still the member's own privacy control"
        ),
    }
)


# Events panel (wave 1) — the two decisions `/event`'s panel makes, in their own block so the
# parallel wave-1 branches merge textually.
KEY_TYPES.update({"event_panel_minutes": "int", "event_panel_own_list": "bool"})
KEY_HELP.update(
    {
        "event_panel_minutes": (
            "minutes the /event panel stays live before its buttons disable themselves; 10 "
            "by default. The 'this panel has gone quiet' footer can only be written while "
            "Discord's 15-minute interaction window is still open, so 15 or more means the "
            "buttons simply stop working with no footer to explain it"
        ),
        "event_panel_own_list": (
            "true to show members the events they proposed on the /event panel; staff always "
            "see theirs, and members can still propose one and call one off either way"
        ),
    }
)


# Polls panel — wave 1. Its own block so the parallel wave-1 branches merge textually.
KEY_TYPES.update({"poll_panel_minutes": "int", "poll_creator_may_end": "bool"})
KEY_HELP.update(
    {
        "poll_panel_minutes": (
            "minutes the /poll panel stays live before its buttons disable themselves; 10 by "
            "default. The 'this panel has gone quiet' footer can only be written while "
            "Discord's 15-minute interaction window is still open, so 15 or more means the "
            "buttons simply stop working with no footer to explain it"
        ),
        "poll_creator_may_end": (
            "true to let whoever started a poll close it early from the /poll panel; staff can "
            "always close one either way"
        ),
    }
)


# Saved poll drafts. Its own block so a parallel branch merges textually.
POLL_DRAFT_DAYS = 14
POLL_DRAFT_MAX_DAYS = 365

KEY_TYPES.update({"poll_drafts": "bool", "poll_draft_days": "int"})
KEY_MAX["poll_draft_days"] = POLL_DRAFT_MAX_DAYS
KEY_MAX_REASON["poll_draft_days"] = (
    "A half-written poll nobody has come back to in {limit} days is not a draft any more. Set "
    "it to 0 if a saved draft should wait for ever."
)
KEY_HELP.update(
    {
        "poll_drafts": (
            "true to let somebody save a half-written poll from the /poll panel and come back to "
            "it; false hides Save for later and Resume draft, and the drafts already saved are "
            "kept, not deleted"
        ),
        "poll_draft_days": (
            f"days a saved poll draft is kept before Black Bloc drops it, up to "
            f"{POLL_DRAFT_MAX_DAYS}; 0 keeps it for ever"
        ),
    }
)


# Memory panel (wave 2) — the one decision `/memory`'s panel introduces, in its own block so the
# parallel wave-2 branches merge textually.
KEY_TYPES.update({"memory_panel_minutes": "int"})
KEY_HELP.update(
    {
        "memory_panel_minutes": (
            "minutes the /memory panel stays live before its buttons disable themselves; 10 by "
            "default. The 'this panel has gone quiet' footer can only be written while "
            "Discord's 15-minute interaction window is still open, so 15 or more means the "
            "buttons simply stop working with no footer to explain it"
        )
    }
)


# Go-live panel — wave 2. Its own block so the parallel wave-2 branches merge textually.
KEY_TYPES.update({"golive_panel_minutes": "int"})
KEY_HELP.update(
    {
        "golive_panel_minutes": (
            "minutes the /golive panel stays live before its buttons disable themselves; 10 by "
            "default. The 'this panel has gone quiet' footer can only be written while "
            "Discord's 15-minute interaction window is still open, so 15 or more means the "
            "buttons simply stop working with no footer to explain it"
        ),
    }
)


# YouTube panel (wave 2) — the two decisions `/youtube`'s panel introduces, in their own block so
# the parallel wave-2 branches merge textually.
KEY_TYPES.update({"youtube_panel_minutes": "int", "youtube_unlink_dms_them": "bool"})
KEY_HELP.update(
    {
        "youtube_panel_minutes": (
            "minutes the /youtube panel stays live before its buttons disable themselves; 10 by "
            "default. The 'this panel has gone quiet' footer can only be written while "
            "Discord's 15-minute interaction window is still open, so 15 or more means the "
            "buttons simply stop working with no footer to explain it"
        ),
        "youtube_unlink_dms_them": (
            "true to DM a member the reason when STAFF forget their YouTube channel for them; a "
            "member unlinking their own channel is never DMed"
        ),
    }
)


# YouTube live (v126) — a linked channel going live is announced through the go-live feature, in
# its own block so the parallel branches merge textually. Design: info/youtube-live-design.md §C.
YOUTUBE_LIVE_MODES = ("off", "shadow", "on")
YOUTUBE_LIVE_POLL_MINUTES = 5
YOUTUBE_LIVE_POLL_MIN_MINUTES = 2
YOUTUBE_LIVE_POLL_MAX_MINUTES = 60
YOUTUBE_LIVE_END_MISSES = 2
YOUTUBE_LIVE_END_MISSES_MIN = 1
YOUTUBE_LIVE_END_MISSES_MAX = 5
KEY_TYPES.update(
    {
        "youtube_live_mode": "enum",
        "youtube_live_poll_minutes": "int",
        "youtube_live_end_misses": "int",
    }
)
KEY_CHOICES["youtube_live_mode"] = YOUTUBE_LIVE_MODES
KEY_MIN["youtube_live_poll_minutes"] = YOUTUBE_LIVE_POLL_MIN_MINUTES
KEY_MAX["youtube_live_poll_minutes"] = YOUTUBE_LIVE_POLL_MAX_MINUTES
KEY_MIN["youtube_live_end_misses"] = YOUTUBE_LIVE_END_MISSES_MIN
KEY_MAX["youtube_live_end_misses"] = YOUTUBE_LIVE_END_MISSES_MAX
KEY_MIN_REASON["youtube_live_poll_minutes"] = (
    "Probing a channel more often than every {limit} minutes asks YouTube for the same page "
    "again and finds nobody live any sooner."
)
KEY_MAX_REASON["youtube_live_poll_minutes"] = (
    "A gap longer than {limit} minutes means a short stream can start and finish between two "
    "probes and never be announced at all."
)
KEY_MIN_REASON["youtube_live_end_misses"] = (
    "Ending a stream on {limit} quiet probe means one hiccup on YouTube's side rewrites the "
    "announcement while the stream is still running."
)
KEY_MAX_REASON["youtube_live_end_misses"] = (
    "Waiting for {limit} quiet probes leaves an announcement saying somebody is live long after "
    "they have stopped."
)
KEY_HELP.update(
    {
        "youtube_live_mode": (
            "off, shadow (log what would be announced), or on — a linked YouTube channel going "
            "live is announced through the go-live feature, exactly like a Twitch stream"
        ),
        "youtube_live_poll_minutes": (
            "how often linked YouTube channels are probed for a live stream"
        ),
        "youtube_live_end_misses": (
            "how many probes in a row must read offline before a stream is treated as ended"
        ),
    }
)


# Spotlight (v144) — Twitch channels with no Discord member behind them. Every key is
# NAMESPACE_OVERRIDE'd onto `golive` below, because a spotlight is a streamer without a member
# and the go-live page is where staff already look. Design: info/spotlight-design.md §D.
SPOTLIGHT_MODES = ("off", "shadow", "on")
SPOTLIGHT_MODE_KEY = "spotlight_mode"
SPOTLIGHT_POLL_MINUTES_KEY = "spotlight_poll_minutes"
SPOTLIGHT_END_MISSES_KEY = "spotlight_end_misses"
SPOTLIGHT_BUMP_HOURS_KEY = "spotlight_bump_hours"
SPOTLIGHT_BUMP_TEMPLATE_KEY = "spotlight_bump_template"
SPOTLIGHT_BUMP_CLEANUP_KEY = "spotlight_bump_cleanup"
SPOTLIGHT_PIN_KEY = "spotlight_pin"
SPOTLIGHT_DEFAULT_DAYS_KEY = "spotlight_default_days"
SPOTLIGHT_EVENT_SLACK_KEY = "spotlight_event_slack_hours"
SPOTLIGHT_POLL_MINUTES = 5
SPOTLIGHT_POLL_MIN_MINUTES = 2
SPOTLIGHT_POLL_MAX_MINUTES = 30
SPOTLIGHT_END_MISSES = 2
SPOTLIGHT_END_MISSES_MIN = 1
SPOTLIGHT_END_MISSES_MAX = 5
SPOTLIGHT_BUMP_HOURS = 4
SPOTLIGHT_BUMP_HOURS_MIN = 1
SPOTLIGHT_BUMP_HOURS_MAX = 48
SPOTLIGHT_DEFAULT_DAYS = 7
SPOTLIGHT_DEFAULT_DAYS_MIN = 1
SPOTLIGHT_DEFAULT_DAYS_MAX = 365
SPOTLIGHT_EVENT_SLACK_HOURS = 2
SPOTLIGHT_EVENT_SLACK_MIN = 0
SPOTLIGHT_EVENT_SLACK_MAX = 24
SPOTLIGHT_BUMP_TEMPLATE = (
    "**{name}** is still live — **{game}**, {duration} so far. {url}"
)
SPOTLIGHT_BUMP_FIELDS = ("name", "game", "title", "url", "duration")
KEY_TYPES.update(
    {
        SPOTLIGHT_MODE_KEY: "enum",
        SPOTLIGHT_POLL_MINUTES_KEY: "int",
        SPOTLIGHT_END_MISSES_KEY: "int",
        SPOTLIGHT_BUMP_HOURS_KEY: "int",
        SPOTLIGHT_BUMP_TEMPLATE_KEY: "text",
        SPOTLIGHT_BUMP_CLEANUP_KEY: "bool",
        SPOTLIGHT_PIN_KEY: "bool",
        SPOTLIGHT_DEFAULT_DAYS_KEY: "int",
        SPOTLIGHT_EVENT_SLACK_KEY: "int",
    }
)
KEY_CHOICES[SPOTLIGHT_MODE_KEY] = SPOTLIGHT_MODES
KEY_MIN[SPOTLIGHT_POLL_MINUTES_KEY] = SPOTLIGHT_POLL_MIN_MINUTES
KEY_MAX[SPOTLIGHT_POLL_MINUTES_KEY] = SPOTLIGHT_POLL_MAX_MINUTES
KEY_MIN[SPOTLIGHT_END_MISSES_KEY] = SPOTLIGHT_END_MISSES_MIN
KEY_MAX[SPOTLIGHT_END_MISSES_KEY] = SPOTLIGHT_END_MISSES_MAX
KEY_MIN[SPOTLIGHT_BUMP_HOURS_KEY] = SPOTLIGHT_BUMP_HOURS_MIN
KEY_MAX[SPOTLIGHT_BUMP_HOURS_KEY] = SPOTLIGHT_BUMP_HOURS_MAX
KEY_MIN[SPOTLIGHT_DEFAULT_DAYS_KEY] = SPOTLIGHT_DEFAULT_DAYS_MIN
KEY_MAX[SPOTLIGHT_DEFAULT_DAYS_KEY] = SPOTLIGHT_DEFAULT_DAYS_MAX
KEY_MIN[SPOTLIGHT_EVENT_SLACK_KEY] = SPOTLIGHT_EVENT_SLACK_MIN
KEY_MAX[SPOTLIGHT_EVENT_SLACK_KEY] = SPOTLIGHT_EVENT_SLACK_MAX
KEY_MIN_REASON[SPOTLIGHT_POLL_MINUTES_KEY] = (
    "Asking Twitch about the same handful of channels more often than every {limit} minutes "
    "spends the quota and finds a marathon no sooner."
)
KEY_MAX_REASON[SPOTLIGHT_POLL_MINUTES_KEY] = (
    "A gap longer than {limit} minutes means a spotlighted stream can be well under way before "
    "anybody is told it started."
)
KEY_MIN_REASON[SPOTLIGHT_END_MISSES_KEY] = (
    "Ending on {limit} quiet look means one hiccup at Twitch unpins a marathon that is still "
    "running."
)
KEY_MAX_REASON[SPOTLIGHT_END_MISSES_KEY] = (
    "Waiting for {limit} quiet looks leaves a pinned announcement saying a marathon is live "
    "long after it has finished."
)
KEY_MIN_REASON[SPOTLIGHT_BUMP_HOURS_KEY] = (
    "Bumping more often than every {limit} hour turns a reminder into the thing people mute."
)
KEY_MAX_REASON[SPOTLIGHT_BUMP_HOURS_KEY] = (
    "A gap longer than {limit} hours is longer than most marathons, so the reminder never "
    "arrives at all."
)
KEY_MIN_REASON[SPOTLIGHT_DEFAULT_DAYS_KEY] = (
    "A row that expires in under {limit} day is gone before the marathon it was added for."
)
KEY_MAX_REASON[SPOTLIGHT_DEFAULT_DAYS_KEY] = (
    "More than {limit} days is a year — use **keep forever** if that is what is meant, so the "
    "list says so out loud."
)
KEY_MAX_REASON[SPOTLIGHT_EVENT_SLACK_KEY] = (
    "More than {limit} hours past an event's end is a whole extra day of spotlight for an "
    "event that finished."
)
KEY_HELP.update(
    {
        SPOTLIGHT_MODE_KEY: (
            "off, shadow (post the rehearsal copy where shadow_channel_id points), or on — "
            "spotlighted Twitch channels are announced, bumped and pinned in the go-live "
            "channel even though nobody behind them is in this server"
        ),
        SPOTLIGHT_POLL_MINUTES_KEY: (
            "how often Twitch is asked whether the spotlighted channels are live; one batched "
            "call covers the whole list"
        ),
        SPOTLIGHT_END_MISSES_KEY: (
            "how many looks in a row must read offline before a spotlighted stream is treated "
            "as over"
        ),
        SPOTLIGHT_BUMP_HOURS_KEY: (
            "hours between reminders that a spotlighted stream is still going; a row can set "
            "its own instead. 4 by default, which is the owner's number for a GDQ marathon"
        ),
        SPOTLIGHT_BUMP_TEMPLATE_KEY: (
            "what a reminder says while a spotlighted stream runs on; {name} {game} {title} "
            "{url} {duration}. It is a new short message, never pinned and never a ping"
        ),
        SPOTLIGHT_BUMP_CLEANUP_KEY: (
            "true to delete a spotlighted stream's reminders when it ends, so the channel is "
            "left with the one announcement"
        ),
        SPOTLIGHT_PIN_KEY: (
            "true if a channel added to the spotlight list has its announcement pinned while "
            "it streams; each row can say otherwise"
        ),
        SPOTLIGHT_DEFAULT_DAYS_KEY: (
            "how long a newly spotlighted channel lasts before it is purged, unless it is kept "
            "for ever"
        ),
        SPOTLIGHT_EVENT_SLACK_KEY: (
            "hours past an approved event's end that its spotlight row survives, so a marathon "
            "that overruns is still announced"
        ),
    }
)


# Pings panel (wave 2) — the one decision `/pings`'s panel introduces, in its own block so the
# parallel wave-2 branches merge textually.
KEY_TYPES.update({"pings_panel_minutes": "int"})
KEY_HELP.update(
    {
        "pings_panel_minutes": (
            "minutes the /pings panel stays live before its buttons disable themselves; 10 by "
            "default. The 'this panel has gone quiet' footer can only be written while "
            "Discord's 15-minute interaction window is still open, so 15 or more means the "
            "buttons simply stop working with no footer to explain it"
        ),
    }
)


# Temp voice panel (wave 2) — the one decision `/voice`'s panel introduces, in its own block so
# the parallel wave-2 branches merge textually.
KEY_TYPES.update({"voice_panel_minutes": "int"})
KEY_HELP.update(
    {
        "voice_panel_minutes": (
            "minutes the /voice panel stays live before its buttons disable themselves; 10 by "
            "default. The 'this panel has gone quiet' footer can only be written while "
            "Discord's 15-minute interaction window is still open, so 15 or more means the "
            "buttons simply stop working with no footer to explain it"
        ),
    }
)


# Automod panel (wave 3) — the two decisions `/automod`'s panel introduces, in its own block so
# the parallel wave-3 branches merge textually.
KEY_TYPES.update({"automod_panel_minutes": "int", "automod_arm_needs_confirm": "bool"})
KEY_HELP.update(
    {
        "automod_panel_minutes": (
            "minutes the /automod panel stays live before its buttons disable themselves; 10 by "
            "default. The 'this panel has gone quiet' footer can only be written while "
            "Discord's 15-minute interaction window is still open, so 15 or more means the "
            "buttons simply stop working with no footer to explain it"
        ),
        "automod_arm_needs_confirm": (
            "true to ask a second time before automod is turned on from the panel, naming what "
            "will start happening; turning it off or back to shadow is always one press"
        ),
    }
)


# Chat panel (wave 3) — the one decision `/chat`'s panel introduces, in its own block so the
# parallel wave-3 branches merge textually. `CHAT_KEYS` is a prefix scan, so this is the only edit.
KEY_TYPES.update({"chat_panel_minutes": "int"})
KEY_HELP.update(
    {
        "chat_panel_minutes": (
            "minutes the /chat panel stays live before its buttons disable themselves; 10 by "
            "default. The 'this panel has gone quiet' footer can only be written while "
            "Discord's 15-minute interaction window is still open, so 15 or more means the "
            "buttons simply stop working with no footer to explain it"
        ),
    }
)


# Raid train panel (wave 3) — the one decision `/raidtrain`'s panel introduces, in its own block
# so the parallel wave-3 branches merge textually.
KEY_TYPES.update({"raidtrain_panel_minutes": "int"})
KEY_HELP.update(
    {
        "raidtrain_panel_minutes": (
            "minutes the /raidtrain panel stays live before its buttons disable themselves; 10 "
            "by default. The 'this panel has gone quiet' footer can only be written while "
            "Discord's 15-minute interaction window is still open, so 15 or more means the "
            "buttons simply stop working with no footer to explain it"
        ),
    }
)


# Role menus panel (wave 3) — the one decision `/rolemenu`'s panel introduces, in its own block
# so the parallel wave-3 branches merge textually.
KEY_TYPES.update({"rolemenu_panel_minutes": "int"})
KEY_HELP.update(
    {
        "rolemenu_panel_minutes": (
            "minutes the /rolemenu panel stays live before its buttons disable themselves; 10 by "
            "default. The 'this panel has gone quiet' footer can only be written while "
            "Discord's 15-minute interaction window is still open, so 15 or more means the "
            "buttons simply stop working with no footer to explain it"
        ),
    }
)


# Honeypot panel (wave 3) — the one decision `/honeypot`'s panel introduces, in its own block
# so the parallel wave-3 branches merge textually.
KEY_TYPES.update({"honeypot_panel_minutes": "int"})
KEY_HELP.update(
    {
        "honeypot_panel_minutes": (
            "minutes the /honeypot panel stays live before its buttons disable themselves; 10 by "
            "default. The 'this panel has gone quiet' footer can only be written while "
            "Discord's 15-minute interaction window is still open, so 15 or more means the "
            "buttons simply stop working with no footer to explain it"
        ),
    }
)


# Modmail panel (wave 4) — the two decisions `/modmail`'s panel introduces, in their own block
# so the parallel wave-4 branches merge textually.
MODMAIL_BUTTONS = "buttons"
MODMAIL_TYPING = "typing"
MODMAIL_BOTH = "both"
MODMAIL_REPLY_STYLES = (MODMAIL_BUTTONS, MODMAIL_TYPING, MODMAIL_BOTH)

KEY_TYPES.update({"modmail_panel_minutes": "int", "modmail_reply_style": "enum"})
KEY_CHOICES.update({"modmail_reply_style": MODMAIL_REPLY_STYLES})
KEY_HELP.update(
    {
        "modmail_panel_minutes": (
            "minutes the /modmail panel stays live before its buttons disable themselves; 10 by "
            "default. The 'this panel has gone quiet' footer can only be written while "
            "Discord's 15-minute interaction window is still open, so 15 or more means the "
            "buttons simply stop working with no footer to explain it"
        ),
        "modmail_reply_style": (
            "how staff answer a ticket. typing: a plain message in the ticket is relayed to the "
            "member, as it always has been. buttons: it is not — only the ticket card's Reply "
            "and /reply reach them, so a ticket channel can be talked in safely. both is the "
            "default and is today's behaviour with the card added"
        ),
    }
)

# Modmail doors — the member half of `/modmail` and the posted Open-a-ticket button, in their
# own block so the sibling wave-4 branches merge textually.
MODMAIL_MEMBER_COMMAND = "modmail_member_command"
MODMAIL_PANEL_CHANNEL = "modmail_panel_channel_id"
MODMAIL_PANEL_MESSAGE = "modmail_panel_message_id"
MODMAIL_PANEL_SHADOW_MESSAGE = "modmail_panel_shadow_message_id"
MODMAIL_PANEL_SHADOW_HASH = "modmail_panel_shadow_hash"
MODMAIL_PANEL_TITLE = "modmail_panel_title"
MODMAIL_PANEL_TEXT = "modmail_panel_text"
MODMAIL_OPEN_WITH_BUTTON = "modmail_open_with_button"
MODMAIL_PANEL_TITLE_DEFAULT = "Need a moderator?"
MODMAIL_PANEL_TEXT_DEFAULT = (
    "Press the button and tell us what is happening. Only staff see it."
)

KEY_TYPES.update(
    {
        MODMAIL_MEMBER_COMMAND: "bool",
        MODMAIL_PANEL_CHANNEL: "channel",
        MODMAIL_PANEL_MESSAGE: "text",
        MODMAIL_PANEL_SHADOW_MESSAGE: "text",
        MODMAIL_PANEL_SHADOW_HASH: "text",
        MODMAIL_PANEL_TITLE: "text",
        MODMAIL_PANEL_TEXT: "text",
        MODMAIL_OPEN_WITH_BUTTON: "bool",
    }
)
KEY_HELP.update(
    {
        MODMAIL_MEMBER_COMMAND: (
            "true when anybody running /modmail gets the Open a ticket panel; false leaves "
            "/modmail to staff, as it was before, and a member's only door is a DM"
        ),
        MODMAIL_PANEL_CHANNEL: (
            "where the Open a ticket message with its button is posted; blank means no button "
            "is up anywhere. Post it from /modmail ▸ Setup… ▸ Ticket button…"
        ),
        MODMAIL_PANEL_MESSAGE: (
            "the Open a ticket message Black Bloc posted, so it can be moved, taken down and "
            "put back after somebody deletes it. Written by the bot as TEXT, because a "
            "snowflake does not survive a JavaScript number; there is no reason to set it by "
            "hand"
        ),
        MODMAIL_PANEL_SHADOW_MESSAGE: (
            "the rehearsal copy of the Open a ticket message Black Bloc posted in the rehearsal "
            "home while test mode refuses the real channel, so it can be kept current, moved "
            "with shadow_channel_id and taken down. Written by the bot as TEXT; there is no "
            "reason to set it by hand"
        ),
        MODMAIL_PANEL_SHADOW_HASH: (
            "a fingerprint of the wording that rehearsal copy is showing, so a sweep edits it "
            "only when the heading or the line under it has actually changed. Written by the "
            "bot; there is no reason to set it by hand"
        ),
        MODMAIL_PANEL_TITLE: "the heading on the posted Open a ticket message",
        MODMAIL_PANEL_TEXT: "what the posted Open a ticket message says under its heading",
        MODMAIL_OPEN_WITH_BUTTON: (
            "true draws Open a ticket with… on the staff row of /modmail, so staff can start a "
            "ticket for somebody else; false hides that door and leaves every other way in "
            "untouched. The door is only hidden, never removed — turning this back on brings it "
            "straight back, and a press on a panel that was open when it went off is refused in "
            "words"
        ),
    }
)


# Blackmail forums — modmail's third mode and the post the ticket button sits under, in their
# own block so the sibling branches merge textually.
MODMAIL_CATEGORY_KEY = "modmail_category_id"
MODMAIL_FORUM_CHANNEL = "modmail_forum_channel_id"
MODMAIL_FORUM_TAGS = "modmail_forum_tags"
MODMAIL_PANEL_FOLLOWS_POST = "modmail_panel_follows_post"
MODMAIL_PANEL_FOLLOWS_POST_DEFAULT = "welcome"
MODMAIL_PANEL_FOLLOWS_NOTHING = "none"
REQUEST_FORUM_CHANNEL = "request_forum_channel_id"
MODMAIL_LOG_ON_OPEN = "modmail_log_on_open"

KEY_TYPES.update(
    {
        MODMAIL_FORUM_CHANNEL: "channel",
        MODMAIL_FORUM_TAGS: "bool",
        MODMAIL_LOG_ON_OPEN: "bool",
        MODMAIL_PANEL_FOLLOWS_POST: "text",
    }
)
KEY_HELP.update(
    {
        MODMAIL_FORUM_CHANNEL: (
            "the forum channel tickets are posted in, in forum mode; Setup on /modmail makes one "
            "under the ticket category"
        ),
        MODMAIL_FORUM_TAGS: (
            "true keeps the open / closed tags on each ticket post in forum mode; false leaves "
            "every post untagged and the forum's own tag list alone"
        ),
        MODMAIL_LOG_ON_OPEN: (
            "true posts a New-ticket card to the transcripts channel the moment a ticket opens "
            "(what the old ModMail bot's log did); false logs opens only in the action log"
        ),
        MODMAIL_PANEL_FOLLOWS_POST: (
            "the slug of the post the Open a ticket button sits under — welcome by default, so "
            "the button lands right after the rules and is put back there whenever that post is "
            "posted again. none never moves the button for that reason"
        ),
    }
)


# The front door — one posted message and `/ask`, routing to modmail, requests and events.
# Every key is NAMESPACE_OVERRIDE'd onto `modmail` so both doors sit in one group.
FRONTDOOR_MODE = "frontdoor_mode"
FRONTDOOR_CHANNEL = "frontdoor_channel_id"
FRONTDOOR_MESSAGE = "frontdoor_message_id"
FRONTDOOR_SHADOW_MESSAGE = "frontdoor_shadow_message_id"
FRONTDOOR_SHADOW_HASH = "frontdoor_shadow_hash"
FRONTDOOR_TITLE = "frontdoor_title"
FRONTDOOR_TEXT = "frontdoor_text"
FRONTDOOR_TICKET_LABEL = "frontdoor_ticket_label"
FRONTDOOR_REQUEST_LABEL = "frontdoor_request_label"
FRONTDOOR_EVENT_LABEL = "frontdoor_event_label"
FRONTDOOR_FOLLOWS_POST = "frontdoor_follows_post"
FRONTDOOR_REPLACES_TICKET_BUTTON = "frontdoor_replaces_ticket_button"
FRONTDOOR_PANEL_MINUTES = "frontdoor_panel_minutes"
FRONTDOOR_FOLLOWS_NOTHING = "none"
FRONTDOOR_MODES = ("off", "shadow", "on")
FRONTDOOR_MODE_DEFAULT = "on"
FRONTDOOR_TITLE_DEFAULT = "Need something?"
FRONTDOOR_TEXT_DEFAULT = (
    "Pick the one that fits and Black Bloc takes it from there. Staff only see what you write."
)
FRONTDOOR_TICKET_LABEL_DEFAULT = "Ask staff privately"
FRONTDOOR_REQUEST_LABEL_DEFAULT = "Request something"
FRONTDOOR_EVENT_LABEL_DEFAULT = "Propose an event"
FRONTDOOR_FOLLOWS_POST_DEFAULT = "welcome"

KEY_TYPES.update(
    {
        FRONTDOOR_MODE: "enum",
        FRONTDOOR_CHANNEL: "channel",
        FRONTDOOR_MESSAGE: "text",
        FRONTDOOR_SHADOW_MESSAGE: "text",
        FRONTDOOR_SHADOW_HASH: "text",
        FRONTDOOR_TITLE: "text",
        FRONTDOOR_TEXT: "text",
        FRONTDOOR_TICKET_LABEL: "text",
        FRONTDOOR_REQUEST_LABEL: "text",
        FRONTDOOR_EVENT_LABEL: "text",
        FRONTDOOR_FOLLOWS_POST: "text",
        FRONTDOOR_REPLACES_TICKET_BUTTON: "bool",
        FRONTDOOR_PANEL_MINUTES: "int",
    }
)
KEY_CHOICES.update({FRONTDOOR_MODE: FRONTDOOR_MODES})
KEY_HELP.update(
    {
        FRONTDOOR_MODE: (
            "off hides /ask and takes the door down; shadow posts the rehearsal copy into "
            "shadow_channel_id with the rehearsal note and nothing into the real channel; on "
            "posts it where it is pointed. /ask answers in both shadow and on, and the three "
            "flows behind it (modmail, requests, events) keep their own modes whatever this "
            "says. In shadow the Open a ticket button follows the door while "
            "frontdoor_replaces_ticket_button is true"
        ),
        FRONTDOOR_CHANNEL: (
            "where the front-door message is posted; blank posts nothing, and the /ask command "
            "still works. Post it from the Modmail page's Front door card"
        ),
        FRONTDOOR_MESSAGE: (
            "the front-door message Black Bloc posted, so it can be moved, taken down and put "
            "back after somebody deletes it. Written by the bot as TEXT, because a snowflake "
            "does not survive a JavaScript number; there is no reason to set it by hand"
        ),
        FRONTDOOR_SHADOW_MESSAGE: (
            "the rehearsal copy of the front door Black Bloc posted in the rehearsal home while "
            "test mode refuses the real channel, so it can be kept current, moved with "
            "shadow_channel_id and taken down. Written by the bot as TEXT; there is no reason "
            "to set it by hand"
        ),
        FRONTDOOR_SHADOW_HASH: (
            "a fingerprint of the wording the rehearsal copy is showing, so a sweep edits it "
            "only when the heading, the line or a button label has actually changed. Written "
            "by the bot; there is no reason to set it by hand"
        ),
        FRONTDOOR_TITLE: "the heading on the posted front-door message and on the /ask panel",
        FRONTDOOR_TEXT: "the line under that heading, on both",
        FRONTDOOR_TICKET_LABEL: (
            "what the button that opens a private modmail ticket is called, at most 80 "
            "characters, which is Discord's own cap; blank restores the shipped wording"
        ),
        FRONTDOOR_REQUEST_LABEL: (
            "what the button that files a request is called, at most 80 characters; blank "
            "restores the shipped wording"
        ),
        FRONTDOOR_EVENT_LABEL: (
            "what the button that starts an event proposal is called, at most 80 characters; "
            "blank restores the shipped wording"
        ),
        FRONTDOOR_FOLLOWS_POST: (
            "the slug of the post the front door sits directly under — welcome by default, so "
            "the door lands right after the rules and is put back there whenever that post is "
            "posted again. none never moves the door for that reason"
        ),
        FRONTDOOR_REPLACES_TICKET_BUTTON: (
            "true takes the posted Open-a-ticket message down while the front door is up in the "
            "same channel — one door per channel. modmail_panel_channel_id keeps its value, so "
            "moving the front door elsewhere or taking it down puts the ticket button back"
        ),
        FRONTDOOR_PANEL_MINUTES: (
            "minutes the /ask panel stays live before its buttons disable themselves; 10 by "
            "default. The 'this panel has gone quiet' footer can only be written while "
            "Discord's 15-minute interaction window is still open, so 15 or more means the "
            "buttons simply stop working with no footer to explain it"
        ),
    }
)


# Mod cases panel (wave 4) — the one decision `/mod`'s panel introduces, in its own block
# so the parallel wave-4 branches merge textually.
KEY_TYPES.update({"mod_panel_minutes": "int"})
KEY_HELP.update(
    {
        "mod_panel_minutes": (
            "minutes the /mod panel stays live before its buttons disable themselves; 10 by "
            "default. The 'this panel has gone quiet' footer can only be written while "
            "Discord's 15-minute interaction window is still open, so 15 or more means the "
            "buttons simply stop working with no footer to explain it"
        ),
    }
)


# Settings panel (wave 4) — the two decisions `/settings`'s own panel introduces, in their own
# block so the parallel wave-4 branches merge textually.
SETTINGS_PANEL_MINUTES = "settings_panel_minutes"
SETTINGS_CORE_KEYS_ADMIN_ONLY = "settings_core_keys_admin_only"
SETTINGS_CORE_KEYS_ADMIN_ONLY_DEFAULT = True

KEY_TYPES.update({SETTINGS_PANEL_MINUTES: "int", SETTINGS_CORE_KEYS_ADMIN_ONLY: "bool"})
KEY_HELP.update(
    {
        SETTINGS_PANEL_MINUTES: (
            "minutes the /settings panel stays live before its buttons disable themselves; 10 by "
            "default. The 'this panel has gone quiet' footer can only be written while "
            "Discord's 15-minute interaction window is still open, so 15 or more means the "
            "buttons simply stop working with no footer to explain it"
        ),
        SETTINGS_CORE_KEYS_ADMIN_ONLY: (
            "true keeps the four settings that decide who counts as staff and where Black Bloc "
            "talks — the staff channel, the log channel, the moderation log channel and the "
            "role-menu channel — to somebody with Manage Server; the rest of /settings still "
            "opens for any staff member, and false lets any staff member re-point them too. The "
            "dashboard's Settings page stays staff-visible either way"
        ),
    }
)


# Errors (`docs/info/errors-design.md` §B) — the words a failure says and how long Try again
# lives, in their own block so the parallel branches merge textually. All four sit under `core`.
ERROR_SENTENCE_KEY = "error_sentence"
ERROR_RETRY_LABEL_KEY = "error_retry_label"
ERROR_RETRY_MINUTES_KEY = "error_retry_minutes"
ERROR_RETRY_EXPIRED_KEY = "error_retry_expired"
ERROR_RETRY_MINUTES = 10
ERROR_RETRY_MIN_MINUTES = 1
ERROR_RETRY_MAX_MINUTES = 30
ERROR_SENTENCE = (
    "Black Bloc hit an error at that step; it has been logged for staff. Press **Try again** to "
    "pick up where you were — your answers are kept."
)
ERROR_RETRY_LABEL = "Try again"
ERROR_RETRY_EXPIRED = (
    "That Try again has run out — Black Bloc can only put somebody back where they were for a "
    "few minutes. Run {command} again to start it fresh, and tell a Lead if it keeps happening."
)

KEY_TYPES.update(
    {
        ERROR_SENTENCE_KEY: "text",
        ERROR_RETRY_LABEL_KEY: "text",
        ERROR_RETRY_MINUTES_KEY: "int",
        ERROR_RETRY_EXPIRED_KEY: "text",
    }
)
KEY_MIN[ERROR_RETRY_MINUTES_KEY] = ERROR_RETRY_MIN_MINUTES
KEY_MAX[ERROR_RETRY_MINUTES_KEY] = ERROR_RETRY_MAX_MINUTES
KEY_HELP.update(
    {
        ERROR_SENTENCE_KEY: (
            "what somebody is told when a panel, a modal or a button fails and Black Bloc can "
            "put them back where they were; it is said beside a Try again button that re-renders "
            "what they had open, answers kept. A failure with nothing to re-render says the "
            "plain 'hit an error running that command' sentence instead"
        ),
        ERROR_RETRY_LABEL_KEY: "what the Try again button on that sentence is called",
        ERROR_RETRY_MINUTES_KEY: (
            "minutes a Try again button keeps working before it says it has run out; 10 by "
            "default. Discord closes the interaction it re-renders through after 15 minutes, so "
            "anything above that is a button that answers 'run it again' rather than working"
        ),
        ERROR_RETRY_EXPIRED_KEY: (
            "what a Try again pressed too late says. `{command}` is filled in with the command "
            "the member was running when it is known, and with 'that command' when it is not"
        ),
    }
)


# Boot status (`docs/info/boot-status-design.md`) — red while it boots, green when it is ready.
BOOT_STATUS_MODE = "boot_status_mode"
BOOT_STATUS_TEXT_KEY = "boot_status_text"
SHUTDOWN_STATUS_TEXT_KEY = "shutdown_status_text"
BOOT_STATUS_MODES = ("off", "on")
BOOT_STATUS_MODE_DEFAULT = "on"
BOOT_STATUS_TEXT = "Restarting and booting — back in a moment"
SHUTDOWN_STATUS_TEXT = "Restarting — back in a moment"

KEY_TYPES.update(
    {
        BOOT_STATUS_MODE: "enum",
        BOOT_STATUS_TEXT_KEY: "text",
        SHUTDOWN_STATUS_TEXT_KEY: "text",
    }
)
KEY_CHOICES[BOOT_STATUS_MODE] = BOOT_STATUS_MODES
KEY_HELP.update(
    {
        BOOT_STATUS_MODE: (
            "on makes Black Bloc read Do Not Disturb with the restarting sentence from the "
            "moment Discord sees it until every cog is loaded and it is ready, and flip to it "
            "again on the way down; off is the older behaviour, where it simply appears"
        ),
        BOOT_STATUS_TEXT_KEY: (
            "the status Black Bloc carries while it is starting up, beside the red Do Not "
            "Disturb dot. It is replaced by the member count the moment it is ready"
        ),
        SHUTDOWN_STATUS_TEXT_KEY: (
            "the status Black Bloc carries on its way down, beside the red dot. Discord keeps "
            "a bot's status only while it is connected, so this shows for the last second and "
            "then it reads offline"
        ),
    }
)


# Operator read token — the token itself is the on/off switch; this is the one decision left.
KEY_TYPES.update({"operator_read_log": "bool"})
KEY_HELP.update(
    {
        "operator_read_log": (
            "true to write one Core log line for every read a Claude session makes with the "
            "operator token, saying which path it read; false reads the same data and leaves no "
            "row. The token itself is the on/off switch — unset it and there are no reads at all"
        )
    }
)


# The staff allow on every channel Black Bloc makes — one decision, one key.
SPAWNED_STAFF_REACH = "spawned_channels_staff_reach"
SPAWNED_STAFF_REACH_DEFAULT = True
KEY_TYPES.update({SPAWNED_STAFF_REACH: "bool"})
KEY_HELP.update(
    {
        SPAWNED_STAFF_REACH: (
            "true gives the staff roles view + manage on every channel Black Bloc makes (temp "
            "voice rooms and the lobby, event rooms, ticket channels), so a hidden room is still "
            "theirs to open or delete by hand; false leaves each builder's own permissions"
        )
    }
)


# Hiding a feature's slash command while its mode is off — the one decision that switch makes.
HIDE_COMMANDS_WHEN_OFF = "hide_commands_when_off"
HIDE_COMMANDS_WHEN_OFF_DEFAULT = True
KEY_TYPES.update({HIDE_COMMANDS_WHEN_OFF: "bool"})
KEY_HELP.update(
    {
        HIDE_COMMANDS_WHEN_OFF: (
            "true to take a feature's slash command out of this server's command list while "
            "that feature is turned off, so nobody is offered a command that cannot do "
            "anything; turning the feature back on brings the command back within about a "
            "minute. false leaves every command showing all the time and an off feature "
            "explains itself when it is opened. Only off hides a command — shadow does not"
        )
    }
)


# The Logs button's two knobs. Its own block so a parallel branch merges textually, and the
# bounds live here because `actionlog.py` reads them back out of the registry's one home.
LOGS_MIN = 1
LOGS_MAX = 50
LOGS_DEFAULT = 10
LOGS_COUNT = "logs_count"
LOGS_IMPORTANT_ONLY = "logs_important_only"

KEY_TYPES.update({LOGS_COUNT: "int", LOGS_IMPORTANT_ONLY: "bool"})
KEY_MIN[LOGS_COUNT] = LOGS_MIN
KEY_MAX[LOGS_COUNT] = LOGS_MAX
KEY_MIN_REASON[LOGS_COUNT] = (
    "A Logs button that opened on fewer than {limit} line would show nothing at all, which "
    "reads as a broken button rather than as an empty log."
)
KEY_MAX_REASON[LOGS_COUNT] = (
    "One embed holds about {limit} log lines before Discord cuts the rest off mid-sentence. "
    "The whole log, searchable, is on the dashboard's Logs page."
)
KEY_HELP.update(
    {
        LOGS_COUNT: (
            f"how many lines a Logs button shows to begin with, from {LOGS_MIN} to {LOGS_MAX}; "
            f"{LOGS_DEFAULT} by default. Show more adds the same number again, and stops being "
            f"offered once the log has run out or {LOGS_MAX} lines are shown"
        ),
        LOGS_IMPORTANT_ONLY: (
            "true to open every Logs button already filtered to the lines that matter — "
            "refusals, errors and staff moves — with Show everything beside the list to see the "
            "rest; false opens on everything, which is what it did before"
        ),
    }
)


# Self-test (wave 5) — the three decisions the self-test introduces, in their own block.
SELFTEST_ON_BOOT = "selftest_on_boot"
SELFTEST_CHANNEL_ID = "selftest_channel_id"
SELFTEST_PURGE_MINUTES = "selftest_purge_minutes"
SELFTEST_LOG_LEVEL = log_level_key("selftest")
SELFTEST_PURGE_MINUTES_DEFAULT = 1
SELFTEST_PURGE_MIN_MINUTES = 1
SELFTEST_PURGE_MAX_MINUTES = 24 * 60

KEY_TYPES.update(
    {
        SELFTEST_ON_BOOT: "bool",
        SELFTEST_CHANNEL_ID: "channel",
        SELFTEST_PURGE_MINUTES: "int",
    }
)
KEY_MIN.update({SELFTEST_PURGE_MINUTES: SELFTEST_PURGE_MIN_MINUTES})
KEY_MAX.update({SELFTEST_PURGE_MINUTES: SELFTEST_PURGE_MAX_MINUTES})
KEY_MIN_REASON.update(
    {
        SELFTEST_PURGE_MINUTES: (
            "A self-test's cards would be gone before anybody could look at them, so the "
            "shortest Black Bloc will keep them is {limit} minute."
        )
    }
)
KEY_MAX_REASON.update(
    {
        SELFTEST_PURGE_MINUTES: (
            "The self-test's cards are throwaway proof, not a record — anything past {limit} "
            "minutes is a day of test spam nobody asked for. The log lines are kept forever "
            "on the dashboard's Logs page under Test either way."
        )
    }
)
KEY_HELP.update(
    {
        SELFTEST_ON_BOOT: (
            "true to run the self-test at every boot, so a deploy proves itself in the hosting "
            "log without anybody opening Discord; false to run it only when staff ask with "
            "`/test`. The default is on while test mode is on and off otherwise, so a live "
            "server is not given a card per panel at every deploy. It posts a card per panel "
            "into the self-test channel and deletes them again a few minutes later"
        ),
        SELFTEST_CHANNEL_ID: (
            "where the self-test posts the cards it is proving; every one of them is deleted "
            "again once selftest_purge_minutes has passed. Unset means the test channel. While "
            "test mode is on, the guard refuses any other channel anyway"
        ),
        SELFTEST_PURGE_MINUTES: (
            "how long a self-test's messages stay in the self-test channel before Black Bloc "
            "deletes them; 1 by default. The log lines stay on the dashboard's Logs page under "
            "Test whatever this says"
        ),
    }
)


# The global personality pool (next-wave #4) — the two decisions the shared manifest introduces.
PERSONALITY_POOL_SYNC = "personality_pool_sync"
PERSONALITY_POOL_PEER_URL = "personality_pool_peer_url"
PERSONALITY_POOL_SYNC_DEFAULT = True
PERSONALITY_POOL_PEER_URL_DEFAULT = "https://discord.heygabi.ai/api/health"

KEY_TYPES.update(
    {PERSONALITY_POOL_SYNC: "bool", PERSONALITY_POOL_PEER_URL: "text"}
)
KEY_HELP.update(
    {
        PERSONALITY_POOL_SYNC: (
            "true to bring the mood pool up to the estate's shared personality manifest at every "
            "boot — new moods are added, a mood's wording, wings and order are refreshed, and a "
            "mood the manifest has dropped is retired and switched off. Whether a mood is ON is "
            "always staff's, and this never touches it. false adds missing moods only, which is "
            "what to use if a manifest change ever lands wrong"
        ),
        PERSONALITY_POOL_PEER_URL: (
            "the health address of the estate's other bot, read by the self-test so the two "
            "cannot drift apart unnoticed: it compares that bot's personality pool version with "
            "this one's and says which side is ahead. It cannot be left blank, and reaching it is "
            "never required for Black Bloc to work — a bot that will not answer is reported as "
            "unreachable, never as drifted"
        ),
    }
)


# Guides (G1) — the five decisions the guides pages introduce; the sixth is the log level,
# generated with every other feature's. Its own block so a parallel branch merges textually.
GUIDES_MODES = ("off", "on")
GUIDES_EDITORS = ("staff", "manage_guild")
GUIDES_MODE_DEFAULT = "on"
GUIDES_WHO_EDITS_DEFAULT = GUIDES_EDITORS[0]

KEY_TYPES.update(
    {
        "guides_mode": "enum",
        "guides_who_edits": "enum",
        "guides_help_links": "bool",
        "guides_show_facts": "bool",
        "guides_fault_files_request": "bool",
    }
)
KEY_CHOICES.update({"guides_mode": GUIDES_MODES, "guides_who_edits": GUIDES_EDITORS})
KEY_HELP.update(
    {
        "guides_mode": (
            "on to give members the Guides page and to put a guide link beside a command in "
            "/help; off hides both. Staff can still open a guide's web address while it is off, "
            "and the page says so. There is no slash command to hide either way"
        ),
        "guides_who_edits": (
            "who may change a guide's wording and screenshots: staff (anybody who can see the "
            "staff channel, the default) or manage_guild (a Lead only). It is read when Save is "
            "pressed rather than when the page is drawn, so taking the role away stops the next "
            "save"
        ),
        "guides_help_links": (
            "true to add a small guide link beside every /help line whose command has a "
            "published guide, and an All the guides button on the last page; false leaves /help "
            "exactly as it was"
        ),
        "guides_show_facts": (
            "true to show the Right now block on a guide — up to four live values read from the "
            "bot as the page opens, such as which mode a feature is in; false shows the steps "
            "only"
        ),
        "guides_fault_files_request": (
            "true to make Something's off at the foot of a guide file a request, so staff see it "
            "where they see everything else; false makes it a sentence telling the reader to "
            "tell a Lead"
        ),
    }
)


# Posts (§C7) — the two decisions the Posts page and `/posts` introduce; the third is the log
# level, generated with every other feature's. Its own block so a parallel branch merges
# textually.
POSTS_MODES = ("off", "shadow", "on")
POSTS_MODE_DEFAULT = "shadow"
POSTS_PANEL_MINUTES_DEFAULT = 10
POSTS_PANEL_MIN_MINUTES = 1
POSTS_PANEL_MAX_MINUTES = 1440

KEY_TYPES.update({"posts_mode": "enum", "posts_panel_minutes": "int"})
KEY_CHOICES.update({"posts_mode": POSTS_MODES})
KEY_MIN["posts_panel_minutes"] = POSTS_PANEL_MIN_MINUTES
KEY_MAX["posts_panel_minutes"] = POSTS_PANEL_MAX_MINUTES
KEY_MIN_REASON["posts_panel_minutes"] = (
    "A panel that goes quiet in less than {limit} minute is gone before anybody has read it."
)
KEY_MAX_REASON["posts_panel_minutes"] = (
    "{limit} minutes is a day, and a panel nobody has touched since yesterday is not one "
    "anybody is still looking at."
)
KEY_HELP.update(
    {
        "posts_mode": (
            "off, shadow (Post it sends the real message into the shadow channel — the test "
            "channel while test mode is on, otherwise the log channel — and keeps it edited "
            "there, whatever channel the post names) or on (Post it goes to the post's own "
            "channel, and the first real post removes the shadow copy). Shadow is the default, "
            "so nothing reaches members until a Lead turns posts on. Off hides `/posts` and "
            "refuses both doors in words; every word already written is kept in all three"
        ),
        "posts_panel_minutes": (
            "minutes the /posts panel stays live before its buttons disable themselves; 10 by "
            "default. The 'this panel has gone quiet' footer can only be written while "
            "Discord's 15-minute interaction window is still open, so 15 or more means the "
            "buttons simply stop working with no footer to explain it"
        ),
    }
)

# Posts — version history (owner, 2026-09-20). A version is written only by Save changes or
# Post it, so the two decisions the list makes are how many are kept and how long the one-line
# summary on each row runs.
POSTS_VERSIONS_KEEP_DEFAULT = 0
POSTS_VERSIONS_KEEP_MIN = 0
POSTS_VERSIONS_KEEP_MAX = 500
POSTS_VERSIONS_SUMMARY_CHARS_DEFAULT = 80
POSTS_VERSIONS_SUMMARY_CHARS_MIN = 20
POSTS_VERSIONS_SUMMARY_CHARS_MAX = 300

KEY_TYPES.update({"posts_versions_keep": "int", "posts_versions_summary_chars": "int"})
KEY_MIN["posts_versions_keep"] = POSTS_VERSIONS_KEEP_MIN
KEY_MAX["posts_versions_keep"] = POSTS_VERSIONS_KEEP_MAX
KEY_MIN["posts_versions_summary_chars"] = POSTS_VERSIONS_SUMMARY_CHARS_MIN
KEY_MAX["posts_versions_summary_chars"] = POSTS_VERSIONS_SUMMARY_CHARS_MAX
KEY_MIN_REASON["posts_versions_keep"] = (
    "{limit} is keep every version, and there is nothing below it — history is cheap, a lost "
    "version is not."
)
KEY_MAX_REASON["posts_versions_keep"] = (
    "Nobody scrolls past {limit} versions of one message, and the list has to be read by a "
    "person."
)
KEY_MIN_REASON["posts_versions_summary_chars"] = (
    "A summary under {limit} characters shows the first few words and tells nobody which "
    "version they are looking at."
)
KEY_MAX_REASON["posts_versions_summary_chars"] = (
    "The summary is one line beside two buttons, and past {limit} characters it wraps and the "
    "list stops being skimmable."
)
KEY_HELP.update(
    {
        "posts_versions_keep": (
            "how many saved versions of a post are kept; 0 (the default) keeps every one of "
            "them, and 1 to 500 trims the oldest after each save. History is cheap and a lost "
            "version is not, so raise it rather than lower it. The only remaining version is "
            "never trimmed, whatever the number says"
        ),
        "posts_versions_summary_chars": (
            "how many characters of a version's message are shown on its row in the Versions "
            "list, 20 to 300; 80 by default. It is one line beside View and Use this version — "
            "the whole message is in View"
        ),
    }
)

# Meeting minutes (prototype) — filed under `events` in NAMESPACE_OVERRIDE below, because the
# `/settings` group select is at its cap of 25 and a meeting is an event's cousin.
MINUTES_MODES = ("off", "on")
MINUTES_MODE_DEFAULT = "off"
MINUTES_START_TEXT_DEFAULT = (
    "\U0001f534 Black Bloc is taking notes in this meeting. Say **stop notes** or press Stop "
    "on /minutes to end it."
)
MINUTES_NOTES_TITLE_DEFAULT = "Meeting notes"
MINUTES_PROMPT_DEFAULT = (
    "You are writing the minutes of a voice meeting from an automatic transcript. The "
    "transcript is speaker-labelled and may contain mishearings — never invent anything it does "
    "not say, and say so plainly where it is unclear. Write, in plain words and in this order: "
    "a two-line summary; the decisions that were made; the action items, each with the name of "
    "the person who took it; the questions that were left open. Use short headings and bullets. "
    "Leave a section out entirely if the meeting held nothing for it."
)
MINUTES_MAX_HOURS_DEFAULT = 3
MINUTES_MAX_HOURS_MIN = 1
MINUTES_MAX_HOURS_MAX = 6
MINUTES_KEEP_DAYS_DEFAULT = 90
MINUTES_KEEP_DAYS_MIN = 1
MINUTES_KEEP_DAYS_MAX = 365
MINUTES_PANEL_MINUTES_DEFAULT = 10
MINUTES_PANEL_MIN_MINUTES = 1
MINUTES_PANEL_MAX_MINUTES = 1440

KEY_TYPES.update(
    {
        "minutes_mode": "enum",
        "minutes_channel_id": "channel",
        "minutes_opt_out_role_id": "role",
        "minutes_start_text": "text",
        "minutes_notes_title": "text",
        "minutes_prompt": "text",
        "minutes_chunk_seconds": "int",
        "minutes_max_hours": "int",
        "minutes_keep_days": "int",
        "minutes_panel_minutes": "int",
    }
)
KEY_CHOICES["minutes_mode"] = MINUTES_MODES
KEY_MIN.update(
    {
        "minutes_chunk_seconds": MINUTES_CHUNK_SECONDS_MIN,
        "minutes_max_hours": MINUTES_MAX_HOURS_MIN,
        "minutes_keep_days": MINUTES_KEEP_DAYS_MIN,
        "minutes_panel_minutes": MINUTES_PANEL_MIN_MINUTES,
    }
)
KEY_MAX.update(
    {
        "minutes_chunk_seconds": MINUTES_CHUNK_SECONDS_MAX,
        "minutes_max_hours": MINUTES_MAX_HOURS_MAX,
        "minutes_keep_days": MINUTES_KEEP_DAYS_MAX,
        "minutes_panel_minutes": MINUTES_PANEL_MAX_MINUTES,
    }
)
KEY_MIN_REASON.update(
    {
        "minutes_chunk_seconds": (
            "Below {limit} seconds the speech-to-text call is made so often that a meeting "
            "costs more in requests than it does in words, and a sentence cut in half "
            "transcribes worse than a whole one."
        ),
        "minutes_max_hours": "A meeting has to be allowed to run at least {limit} hour.",
        "minutes_keep_days": "A transcript deleted sooner than {limit} day is gone before "
        "anybody has read it.",
        "minutes_panel_minutes": (
            "A panel that goes quiet in less than {limit} minute is gone before anybody has "
            "read it."
        ),
    }
)
KEY_MAX_REASON.update(
    {
        "minutes_chunk_seconds": (
            "Over {limit} seconds a chunk gets big enough to be slow to send, and nothing "
            "reaches the transcript until the whole chunk is done."
        ),
        "minutes_max_hours": (
            "{limit} hours is longer than any meeting anybody means to hold, and the cut-off is "
            "what stops a bot left in an empty channel recording all night."
        ),
        "minutes_keep_days": "{limit} days is a year of somebody's words; the notes are kept "
        "either way.",
        "minutes_panel_minutes": (
            "{limit} minutes is a day, and a panel nobody has touched since yesterday is not "
            "one anybody is still looking at."
        ),
    }
)
KEY_HELP.update(
    {
        "minutes_mode": (
            "off or on. This is a PROTOTYPE and it ships off: while it is off `/minutes` is "
            "hidden and both doors refuse in words. On lets staff have Black Bloc join the "
            "voice channel they are in and take notes; it always announces itself first, and "
            "the audio is never stored"
        ),
        "minutes_channel_id": (
            "where a meeting's announcement and its notes go; blank means the voice channel's "
            "own text chat. While test mode is on, both land in the test channel or the "
            "rehearsal home instead, and the panel says where they went"
        ),
        "minutes_opt_out_role_id": (
            "a role that means do not record me: if anybody in the voice channel is wearing it, "
            "Start refuses and names them. Blank means nobody can opt out that way"
        ),
        "minutes_start_text": (
            "the message Black Bloc posts the moment it joins a meeting, before a word is "
            "recorded. It cannot be blank — a meeting that is recorded silently is the one "
            "thing this feature must never do"
        ),
        "minutes_notes_title": "the heading on the notes embed when a meeting is written up",
        "minutes_prompt": (
            "what Black Bloc asks the model for when it turns a transcript into notes. The "
            "transcript is sent after it, so write instructions rather than content"
        ),
        "minutes_chunk_seconds": (
            "how much of one person's speech is gathered before it is sent to be transcribed; "
            f"{MINUTES_CHUNK_SECONDS_DEFAULT} by default, {MINUTES_CHUNK_SECONDS_MIN}–"
            f"{MINUTES_CHUNK_SECONDS_MAX}. Nothing reaches the transcript until a chunk is "
            "finished, so this is also how far behind the live meeting the transcript runs"
        ),
        "minutes_max_hours": (
            "the longest a single meeting may be recorded before Black Bloc leaves and writes "
            f"the notes anyway; {MINUTES_MAX_HOURS_DEFAULT} by default. It is what stops a bot "
            "left in an empty channel recording all night"
        ),
        "minutes_keep_days": (
            "how long a meeting's TRANSCRIPT is kept before it is deleted; "
            f"{MINUTES_KEEP_DAYS_DEFAULT} days by default. The notes and the meeting itself are "
            "kept until somebody deletes them"
        ),
        "minutes_panel_minutes": (
            "minutes the /minutes panel stays live before its buttons disable themselves; 10 by "
            "default. The 'this panel has gone quiet' footer can only be written while Discord's "
            "15-minute interaction window is still open, so 15 or more means the buttons simply "
            "stop working with no footer to explain it"
        ),
    }
)

# The rehearsal home — one channel every shadow copy lands in, so staff review before the
# cutover. Core, beside `log_channel_id`: the `/settings` group select is at its cap of 25.
KEY_TYPES.update({SHADOW_CHANNEL: "channel", REHEARSAL_NOTE: "text"})
KEY_HELP.update(
    {
        SHADOW_CHANNEL: (
            "where every rehearsal goes while a feature is in shadow — the welcome post, the "
            "front door, the ticket button, polls; blank means the bot's own log channel. "
            "Setting it is the deliberate act that lets test mode speak in that one channel "
            "as well, so pick a channel only the people reviewing can see"
        ),
        REHEARSAL_NOTE: (
            "the line the front door and the ticket button carry at the top of their rehearsal "
            "copy; {channel} is replaced with the channel the real one is aimed at. Blank "
            "leaves the copy with no note at all"
        ),
    }
)


# The one grouping of the registry, read by the dashboard's Settings page and by /settings.
CORE_KEYS = (
    "log_channel_id",
    SHADOW_CHANNEL,
    REHEARSAL_NOTE,
    "staff_channel_id",
    "role_menu_channel_id",
    "bot_bio",
    "status_prefix",
    "operator_read_log",
    SPAWNED_STAFF_REACH,
    SETTINGS_PANEL_MINUTES,
    SETTINGS_CORE_KEYS_ADMIN_ONLY,
    SELFTEST_ON_BOOT,
    SELFTEST_CHANNEL_ID,
    SELFTEST_PURGE_MINUTES,
    SELFTEST_LOG_LEVEL,
    PERSONALITY_POOL_SYNC,
    PERSONALITY_POOL_PEER_URL,
    ERROR_SENTENCE_KEY,
    ERROR_RETRY_LABEL_KEY,
    ERROR_RETRY_MINUTES_KEY,
    ERROR_RETRY_EXPIRED_KEY,
    BOOT_STATUS_MODE,
    BOOT_STATUS_TEXT_KEY,
    SHUTDOWN_STATUS_TEXT_KEY,
)
NAMESPACE_OVERRIDE = {
    "modlog_channel_id": "automod",
    "mod_dm_on_action": "automod",
    "mod_log_level": "automod",
    "mod_panel_minutes": "automod",
    DEFAULT_TIMEZONE_KEY: "events",
    TIMEZONE_CHOICES_KEY: "events",
    TIME_STEP_KEY: "events",
    FRONTDOOR_MODE: "modmail",
    FRONTDOOR_CHANNEL: "modmail",
    FRONTDOOR_MESSAGE: "modmail",
    FRONTDOOR_SHADOW_MESSAGE: "modmail",
    FRONTDOOR_SHADOW_HASH: "modmail",
    FRONTDOOR_TITLE: "modmail",
    FRONTDOOR_TEXT: "modmail",
    FRONTDOOR_TICKET_LABEL: "modmail",
    FRONTDOOR_REQUEST_LABEL: "modmail",
    FRONTDOOR_EVENT_LABEL: "modmail",
    FRONTDOOR_FOLLOWS_POST: "modmail",
    FRONTDOOR_REPLACES_TICKET_BUTTON: "modmail",
    FRONTDOOR_PANEL_MINUTES: "modmail",
    HANDOFF_MODE: "request",
    HANDOFF_CONFIRM_HOURS: "request",
    "minutes_mode": "events",
    "minutes_channel_id": "events",
    "minutes_opt_out_role_id": "events",
    "minutes_start_text": "events",
    "minutes_notes_title": "events",
    "minutes_prompt": "events",
    "minutes_chunk_seconds": "events",
    "minutes_max_hours": "events",
    "minutes_keep_days": "events",
    "minutes_panel_minutes": "events",
    log_level_key("minutes"): "events",
    SPOTLIGHT_MODE_KEY: "golive",
    SPOTLIGHT_POLL_MINUTES_KEY: "golive",
    SPOTLIGHT_END_MISSES_KEY: "golive",
    SPOTLIGHT_BUMP_HOURS_KEY: "golive",
    SPOTLIGHT_BUMP_TEMPLATE_KEY: "golive",
    SPOTLIGHT_BUMP_CLEANUP_KEY: "golive",
    SPOTLIGHT_PIN_KEY: "golive",
    SPOTLIGHT_DEFAULT_DAYS_KEY: "golive",
    SPOTLIGHT_EVENT_SLACK_KEY: "golive",
}


def namespace_of(key: str) -> str:
    if key in NAMESPACE_OVERRIDE:
        return NAMESPACE_OVERRIDE[key]
    if key in CORE_KEYS:
        return CORE
    head, _, rest = key.partition("_")
    return head if rest else CORE


GUILD_ONLY = (
    "That command changes settings for a server, so it has to be run in the server itself "
    "rather than in a DM. Run it again from a channel Black Bloc can answer in."
)
DB_UNAVAILABLE = (
    "Black Bloc cannot reach its own database right now, so nothing was changed. It needs the "
    "bot to finish starting up — wait a moment and run the command again, and tell a Lead if it "
    "keeps happening."
)


class SettingError(ValueError):
    """A settings key is unknown, or its value is the wrong type."""


UNKNOWN_ZONE = (
    "**{given}** is not a time zone Black Bloc knows, so nothing was changed. Write the "
    "`Region/City` name Discord and your phone both use — `America/Phoenix`, `Europe/London`, "
    "`Asia/Tokyo`."
)
ZONE_DID_YOU_MEAN = " Did you mean {names}?"
NO_LINK_ALIAS = (
    "Not one of those is a shorthand Black Bloc can read, so nothing was changed. Each one is "
    "an alias, an `=`, and a link with `{{handle}}` where the name goes — "
    "`ttv=https://twitch.tv/{{handle}}, yt=https://youtube.com/@{{handle}}` — separated by "
    "commas, and the list holds at most {limit} of them."
)
NO_KNOWN_ZONE = (
    "Not one of those is a time zone Black Bloc knows, so nothing was changed. They are "
    "`Region/City` names separated by commas — `America/Phoenix, Europe/London, Asia/Tokyo` — "
    "and the dropdown holds at most {limit} of them."
)
NAME_TEMPLATE_NEEDS_TITLE = (
    "A calendar name has to say which event it is, so it must contain `{placeholder}` somewhere "
    "— `{example}` is one that works. Nothing was changed."
)
NAME_TEMPLATE_UNKNOWN = (
    "`{{{found}}}` is not something Black Bloc can fill in, so nothing was changed. The only "
    "thing a calendar name may stand in for is `{placeholder}`, the event's own title; write "
    "any other braces out as words."
)
FILED_LINE_UNKNOWN = (
    "`{{{found}}}` is not something Black Bloc can fill in, so nothing was changed. The only "
    "thing that line may stand in for is `{placeholder}`, the request's number; write any other "
    "braces out as words."
)
MOVED_LINE_UNKNOWN = (
    "`{{{found}}}` is not something Black Bloc can fill in, so nothing was changed. The only "
    "thing that line may stand in for is `{placeholder}`, the post the event moved into; write "
    "any other braces out as words."
)
COSTREAM_UNKNOWN = (
    "`{{{found}}}` is not something Black Bloc can fill in, so nothing was changed. A "
    "co-streaming announcement may stand in for {allowed}; write any other braces out as words."
)

BUMP_UNKNOWN = (
    "`{{{found}}}` is not something Black Bloc can fill in, so nothing was changed. A "
    "spotlight reminder may stand in for {allowed}; write any other braces out as words."
)

PLACEHOLDERS = re.compile(r"\{([^{}]*)\}")


def checked_zone(given: Any) -> str:
    """One `Region/City` name, refused in words with the closest matches when it is not one."""
    name = str(given or "").strip()
    if is_known(name):
        return name
    said = UNKNOWN_ZONE.format(given=name[:60] or "(nothing)")
    near = suggest(name, 5)
    if near:
        said += ZONE_DID_YOU_MEAN.format(names=", ".join(f"`{one}`" for one in near))
    raise SettingError(said)


def checked_zones(given: Any) -> str:
    """The dropdown's list: names this machine cannot resolve are dropped, and 24 are kept."""
    wanted: list[str] = []
    for part in str(given or "").split(","):
        name = part.strip()
        if is_known(name) and name not in wanted:
            wanted.append(name)
    if not wanted:
        raise SettingError(NO_KNOWN_ZONE.format(limit=TIMEZONE_CHOICES_MAX))
    return ", ".join(wanted[:TIMEZONE_CHOICES_MAX])


ALIAS_NAME = re.compile(r"^[a-z0-9]{1,16}$")


def where_alias_table(given: Any) -> dict[str, str]:
    """The one reader of the shorthand list; `events.where_typed` fills what it returns."""
    table: dict[str, str] = {}
    for part in str(given or "").split(","):
        alias, sign, rest = part.strip().partition("=")
        name, template = alias.strip().lower(), rest.strip()
        if not sign or name in table or ALIAS_NAME.match(name) is None:
            continue
        if not template.startswith("https://"):
            continue
        if [one.strip() for one in PLACEHOLDERS.findall(template)] != ["handle"]:
            continue
        table[name] = template
        if len(table) >= WHERE_ALIAS_MAX:
            break
    return table


def checked_aliases(given: Any) -> str:
    """The shorthand list: an entry Black Bloc cannot read is dropped, and 32 are kept."""
    table = where_alias_table(given)
    if not table:
        raise SettingError(NO_LINK_ALIAS.format(limit=WHERE_ALIAS_MAX))
    return ", ".join(f"{name}={template}" for name, template in table.items())


def checked_name_template(given: Any) -> str:
    """`{title}` and nothing else, so a staff-typed name can never fail to render."""
    text = str(given or "").strip()
    found = [one.strip() for one in PLACEHOLDERS.findall(text)]
    stray = next((one for one in found if one != "title"), None)
    if stray is not None:
        raise SettingError(
            NAME_TEMPLATE_UNKNOWN.format(found=stray[:40], placeholder=NAME_PLACEHOLDER)
        )
    if NAME_PLACEHOLDER not in text:
        raise SettingError(
            NAME_TEMPLATE_NEEDS_TITLE.format(
                placeholder=NAME_PLACEHOLDER, example=EVENTS_SCHEDULED_NAME_TEMPLATE
            )
        )
    return text


def checked_moved_line(given: Any) -> str:
    """`{post}` and nothing else, and it may be left out — a line with no link still reads."""
    text = str(given or "").strip()
    stray = next(
        (one.strip() for one in PLACEHOLDERS.findall(text) if one.strip() != "post"), None
    )
    if stray is not None:
        raise SettingError(
            MOVED_LINE_UNKNOWN.format(found=stray[:40], placeholder=POST_PLACEHOLDER)
        )
    return text


def checked_costream(given: Any) -> str:
    """The seven co-streaming placeholders and nothing else, so neither key can fail to fill."""
    text = str(given or "").strip()
    stray = next(
        (
            one.strip()
            for one in PLACEHOLDERS.findall(text)
            if one.strip() not in GOLIVE_COSTREAM_FIELDS
        ),
        None,
    )
    if stray is not None:
        raise SettingError(
            COSTREAM_UNKNOWN.format(
                found=stray[:40],
                allowed=", ".join(f"`{{{one}}}`" for one in GOLIVE_COSTREAM_FIELDS),
            )
        )
    return text


def checked_bump(given: Any) -> str:
    """The five bump placeholders and nothing else, so a reminder can never fail to fill."""
    text = str(given or "").strip()
    stray = next(
        (
            one.strip()
            for one in PLACEHOLDERS.findall(text)
            if one.strip() not in SPOTLIGHT_BUMP_FIELDS
        ),
        None,
    )
    if stray is not None:
        raise SettingError(
            BUMP_UNKNOWN.format(
                found=stray[:40],
                allowed=", ".join(f"`{{{one}}}`" for one in SPOTLIGHT_BUMP_FIELDS),
            )
        )
    return text


def checked_filed_line(given: Any) -> str:
    """`{request_id}` and nothing else, and it may be left out."""
    text = str(given or "").strip()
    stray = next(
        (one.strip() for one in PLACEHOLDERS.findall(text) if one.strip() != "request_id"), None
    )
    if stray is not None:
        raise SettingError(
            FILED_LINE_UNKNOWN.format(found=stray[:40], placeholder=REQUEST_ID_PLACEHOLDER)
        )
    return text


TEXT_CHECKS: dict[str, Any] = {
    DEFAULT_TIMEZONE_KEY: checked_zone,
    GOLIVE_COSTREAM_TEMPLATE_KEY: checked_costream,
    GOLIVE_COSTREAM_AUTHOR_KEY: checked_costream,
    TIMEZONE_CHOICES_KEY: checked_zones,
    WHERE_ALIASES_KEY: checked_aliases,
    EVENTS_SCHEDULED_NAME_KEY: checked_name_template,
    EVENTS_MOVED_LINE_KEY: checked_moved_line,
    REQUEST_FILED_KEY: checked_filed_line,
    RAIDTRAIN_SCHEDULED_NAME_KEY: checked_name_template,
    SPOTLIGHT_BUMP_TEMPLATE_KEY: checked_bump,
}

TEXT_MAY_BE_BLANK = (
    "golive_end_template",
    "golive_end_author",
    REHEARSAL_NOTE,
    WHERE_HINT_KEY,
)


def coerce_value(key: str, value: Any) -> Any:
    """Validate a value against the registry and return what gets stored."""
    kind = KEY_TYPES.get(key)
    if kind is None:
        known = ", ".join(sorted(KEY_TYPES))
        raise SettingError(f"{key!r} is not a Black Bloc setting. Known settings: {known}.")
    if kind == "channel":
        raw = getattr(value, "id", value)
        if isinstance(raw, bool) or not isinstance(raw, int):
            raise SettingError(f"{key!r} takes a channel, not {value!r}.")
        return raw
    if kind == "role":
        raw = getattr(value, "id", value)
        if isinstance(raw, bool) or not isinstance(raw, int):
            raise SettingError(f"{key!r} takes a role, not {value!r}.")
        return raw
    if kind in ("channels", "roles"):
        what = "channels" if kind == "channels" else "roles"
        if isinstance(value, str | bytes) or not isinstance(value, list | tuple | set):
            raise SettingError(f"{key!r} takes a list of {what}, not {value!r}.")
        ids: list[int] = []
        for item in value:
            raw = getattr(item, "id", item)
            if isinstance(raw, bool) or not isinstance(raw, int):
                raise SettingError(f"{key!r} takes a list of {what}, not {value!r}.")
            if raw not in ids:
                ids.append(raw)
        return ids
    if kind == "enum":
        allowed = KEY_CHOICES.get(key, ())
        if value not in allowed:
            raise SettingError(
                f"{key!r} takes one of {', '.join(allowed)}, not {value!r}."
            )
        return value
    if kind == "enums":
        allowed = KEY_CHOICES.get(key, ())
        if isinstance(value, str | bytes) or not isinstance(value, list | tuple | set):
            raise SettingError(
                f"{key!r} takes a list of {', '.join(allowed)}, not {value!r}."
            )
        picked: list[str] = []
        for item in value:
            if item not in allowed:
                raise SettingError(
                    f"{key!r} takes any of {', '.join(allowed)}, and {item!r} is not one of them."
                )
            if item not in picked:
                picked.append(item)
        return [one for one in allowed if one in picked]
    if kind == "int":
        if isinstance(value, bool) or not isinstance(value, int):
            raise SettingError(f"{key!r} takes a whole number, not {value!r}.")
        if value < 0:
            raise SettingError(f"{key!r} cannot be negative.")
        floor = KEY_MIN.get(key)
        if floor is not None and value < floor:
            why = KEY_MIN_REASON.get(key, "").format(limit=floor)
            raise SettingError(
                f"{key!r} cannot be less than {floor}, so nothing was changed. {why}".strip()
            )
        limit = KEY_MAX.get(key)
        if limit is not None and value > limit:
            why = KEY_MAX_REASON.get(key, "").format(limit=limit)
            raise SettingError(
                f"{key!r} cannot be more than {limit}, so nothing was changed. {why}".strip()
            )
        return value
    if kind == "bool":
        if not isinstance(value, bool):
            raise SettingError(f"{key!r} takes true or false, not {value!r}.")
        return value
    if kind == "text":
        if isinstance(value, str) and not value.strip() and key in TEXT_MAY_BE_BLANK:
            return ""
        if not isinstance(value, str) or not value.strip():
            raise SettingError(f"{key!r} takes some text, not {value!r}.")
        check = TEXT_CHECKS.get(key)
        return check(value) if check is not None else value
    if kind == "color":
        match = HEX_COLOR.match(str(value or "").strip()) if isinstance(value, str) else None
        if match is None:
            raise SettingError(
                f"{key!r} takes a hex colour like `#4eefff` — six digits 0-9 or a-f, with or "
                f"without the `#`, and nothing else. {value!r} is not one, so nothing was changed."
            )
        return f"#{match.group(1).lower()}"
    if kind == "json":
        try:
            return validate_rules(value)
        except RuleError as exc:
            raise SettingError(str(exc)) from exc
    raise SettingError(f"{key!r} has no validator for type {kind!r}.")


def parse_value(key: str, raw: str) -> Any:
    """Turn one typed-in string into the value `coerce_value` expects."""
    kind = KEY_TYPES.get(key)
    text = raw.strip()
    if kind in ("int", "channel", "role"):
        digits = text.lstrip("<#@&").rstrip(">")
        if not digits.isdigit():
            raise SettingError(f"{key!r} takes a whole number, not {raw!r}.")
        return int(digits)
    if kind in ("channels", "roles"):
        parts = [p.strip().lstrip("<#@&").rstrip(">") for p in text.split(",") if p.strip()]
        if not all(p.isdigit() for p in parts):
            raise SettingError(f"{key!r} takes ids separated by commas, not {raw!r}.")
        return [int(p) for p in parts]
    if kind == "enums":
        return [part.strip().lower() for part in text.split(",") if part.strip()]
    if kind == "bool":
        if text.lower() in ("true", "yes", "on"):
            return True
        if text.lower() in ("false", "no", "off"):
            return False
        raise SettingError(f"{key!r} takes true or false, not {raw!r}.")
    return text


def display_value(key: str, value: Any) -> str:
    kind = KEY_TYPES.get(key)
    if kind == "json":
        return rules_summary(value)
    if kind in ("channels", "roles"):
        mark = "#" if kind == "channels" else "@&"
        return ", ".join(f"<{mark}{v}>" for v in value) if value else "not set"
    if kind == "enums":
        return ", ".join(str(one) for one in value) if value else "none of them"
    if value is None or value == "":
        return "not set"
    if kind == "channel":
        return f"<#{value}>"
    if kind == "role":
        return f"<@&{value}>"
    return str(value)


def resolved_staff_roles(guild: Any, channel: Any, perms_for: Any = None) -> list[Any]:
    """Roles whose computed permissions see the staff channel; @everyone never counts."""
    if channel is None:
        return []
    resolve = perms_for or getattr(channel, "permissions_for", None)
    if resolve is None:
        log.warning("staff roles: %s cannot say what a role may see", getattr(channel, "id", "?"))
        return []
    found: list[Any] = []
    for role in getattr(guild, "roles", ()):
        is_default = getattr(role, "is_default", None)
        if is_default is not None and is_default():
            continue
        bot_managed = getattr(role, "is_bot_managed", None)
        if bot_managed is not None and bot_managed():
            continue
        try:
            perms = resolve(role)
        except Exception as exc:
            log.warning(
                "staff roles: could not work out what %s can see: %s",
                getattr(role, "id", role),
                exc,
            )
            continue
        if getattr(perms, "view_channel", False):
            found.append(role)
    return found


def staff_roles_sentence(roles: Any) -> str:
    names = [f"**{getattr(role, 'name', role)}**" for role in roles]
    if not names:
        return "no roles at all"
    return f"{len(names)} role(s) — " + ", ".join(names)


def member_is_staff(member: Any, staff_ids: set[int]) -> bool:
    perms = getattr(member, "guild_permissions", None)
    if perms is not None and getattr(perms, "manage_guild", False):
        return True
    return any(getattr(r, "id", None) in staff_ids for r in getattr(member, "roles", ()))


async def require_staff(interaction: Any) -> bool:
    """True if the caller may run a staff command; otherwise answer them and return False."""
    if interaction.guild is None:
        await interaction.response.send_message(GUILD_ONLY, ephemeral=True)
        return False
    store = interaction.client.store
    if not store.is_staff(interaction.user):
        await interaction.response.send_message(
            store.staff_refusal(interaction.guild.id), ephemeral=True
        )
        return False
    return True


def called_names(func: Any) -> tuple[str, ...]:
    code = getattr(func, "__code__", None)
    return tuple(getattr(code, "co_names", ()) or ())


def is_staff_command(command: Any) -> bool:
    """True when a command's own body, or a helper it calls, goes through `require_staff`."""
    extras = getattr(command, "extras", None) or {}
    if "staff_only" in extras:
        return bool(extras["staff_only"])
    gate = require_staff.__name__
    callback = getattr(command, "callback", None)
    names = called_names(callback)
    if gate in names:
        return True
    binding = getattr(command, "binding", None)
    scope = getattr(callback, "__globals__", None) or {}
    for name in names:
        helper = getattr(binding, name, None) if binding is not None else None
        if helper is None:
            helper = scope.get(name)
        if helper is not None and gate in called_names(helper):
            return True
    return False


class SettingsStore:
    def __init__(self, db: Database, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self._cache: dict[tuple[int, str], Any] = {}
        self._hooks: dict[str, list[Any]] = {}

    def on_change(self, key: str, callback: Any) -> None:
        """Call `callback(guild_id, key, value, by)` whenever this key is set or cleared."""
        if key not in KEY_TYPES:
            raise SettingError(f"{key!r} is not a Black Bloc setting.")
        self._hooks.setdefault(key, []).append(callback)

    async def _changed(self, guild_id: int, key: str, value: Any, by: int | None) -> None:
        for callback in self._hooks.get(key, ()):
            try:
                result = callback(guild_id, key, value, by)
                if isawaitable(result):
                    await result
            except Exception as exc:
                log.warning(
                    "settings hook for %s failed — %s: %s", key, type(exc).__name__, exc
                )

    def stored_values(self, key: str) -> dict[int, Any]:
        """Every guild that has this key stored, for a sweep that runs before any guild is up."""
        if key not in KEY_TYPES:
            raise SettingError(f"{key!r} is not a Black Bloc setting.")
        return {
            guild_id: value for (guild_id, name), value in self._cache.items() if name == key
        }

    def default(self, key: str) -> Any:
        if key == REHEARSAL_NOTE:
            return REHEARSAL_NOTE_DEFAULT
        if key == "staff_channel_id":
            return self.settings.test_channel_id
        if key == "log_channel_id":
            return self.settings.test_channel_id if self.settings.test_mode else None
        if key == "golive_channel_id":
            if self.settings.test_mode:
                return self.settings.test_channel_id
            return LIVE_NOW_CHANNEL_ID
        if key == "golive_mode":
            return "shadow"
        if key == "golive_template":
            return GOLIVE_TEMPLATE
        if key == "golive_end_mode":
            return GOLIVE_END_OFF
        if key == "golive_end_suffix":
            return GOLIVE_END_SUFFIX
        if key == "golive_end_template":
            return GOLIVE_END_TEMPLATE
        if key == "golive_end_author":
            return GOLIVE_END_AUTHOR
        if key == "golive_end_keep_mention":
            return False
        if key == GOLIVE_COSTREAM_MODE_KEY:
            return GOLIVE_COSTREAM_ON
        if key == GOLIVE_COSTREAM_TEMPLATE_KEY:
            return GOLIVE_COSTREAM_TEMPLATE
        if key == GOLIVE_COSTREAM_AUTHOR_KEY:
            return GOLIVE_COSTREAM_AUTHOR
        if key == SPOTLIGHT_MODE_KEY:
            return "shadow"
        if key == SPOTLIGHT_POLL_MINUTES_KEY:
            return SPOTLIGHT_POLL_MINUTES
        if key == SPOTLIGHT_END_MISSES_KEY:
            return SPOTLIGHT_END_MISSES
        if key == SPOTLIGHT_BUMP_HOURS_KEY:
            return SPOTLIGHT_BUMP_HOURS
        if key == SPOTLIGHT_BUMP_TEMPLATE_KEY:
            return SPOTLIGHT_BUMP_TEMPLATE
        if key == SPOTLIGHT_BUMP_CLEANUP_KEY:
            return True
        if key == SPOTLIGHT_PIN_KEY:
            return True
        if key == SPOTLIGHT_DEFAULT_DAYS_KEY:
            return SPOTLIGHT_DEFAULT_DAYS
        if key == SPOTLIGHT_EVENT_SLACK_KEY:
            return SPOTLIGHT_EVENT_SLACK_HOURS
        if key == "golive_cooldown_minutes":
            return 60
        if key == "golive_max_session_hours":
            return 12
        if key == "golive_embed":
            return True
        if key == "golive_boot_sweep":
            return True
        if key == "pings_mode":
            return "off"
        if key == "pings_events_role_name":
            return PINGS_EVENTS_ROLE_NAME
        if key == "pings_fan_role_creation":
            return PINGS_CREATION_DEFAULT
        if key == "pings_fan_role_template":
            return PINGS_FAN_ROLE_TEMPLATE
        if key == "pings_fan_role_on_unlink":
            return PINGS_ON_UNLINK[0]
        if key == "pings_fan_role_delete":
            return True
        if key == "pings_streamer_stale_days":
            return PINGS_STREAMER_STALE_DAYS
        if key == "pings_empty_role_days":
            return PINGS_EMPTY_ROLE_DAYS
        if key == "pings_onboarding_managed":
            return True
        if key == "pings_onboarding_prompt_title":
            return PINGS_ONBOARDING_TITLE
        if key == "pings_onboarding_option_cap":
            return PINGS_ONBOARDING_OPTION_CAP
        if key == "tempvoice_mode":
            return "on"
        if key == "tempvoice_name_template":
            return TEMPVOICE_NAME_TEMPLATE
        if key == "tempvoice_creator_name":
            return TEMPVOICE_CREATOR_NAME
        if key == "tempvoice_allowed_role_id":
            return MEMBER_ROLE_ID
        if key == "tempvoice_room_overwrites":
            return TEMPVOICE_ROOM_OVERWRITES[0]
        if key == "chat_visibility_role_id":
            return MEMBER_ROLE_ID
        if key == "honeypot_mode":
            return "shadow"
        if key == "honeypot_purge_days":
            return 1
        if key == "events_mode":
            return "on"
        if key == "events_announce_channel_id":
            if self.settings.test_mode:
                return self.settings.test_channel_id
            return LIVE_NOW_CHANNEL_ID
        if key == "events_create_scheduled":
            return True
        if key == "events_where_link_in_description":
            return True
        if key == WHERE_ALIASES_KEY:
            return WHERE_ALIASES
        if key == WHERE_CHECK_KEY:
            return WHERE_CHECK_MODE
        if key == WHERE_CHECK_SECONDS_KEY:
            return WHERE_CHECK_SECONDS
        if key == WHERE_HINT_KEY:
            return WHERE_HINT
        if key == "events_channel_retention_days":
            return EVENTS_RETENTION_DAYS
        if key == EVENTS_TEST_RETENTION_KEY:
            return EVENTS_TEST_RETENTION_MINUTES
        if key == "events_max_late_minutes":
            return EVENTS_MAX_LATE_MINUTES
        if key == "events_default_minutes":
            return EVENTS_DEFAULT_MINUTES
        if key == EVENTS_SCHEDULED_NAME_KEY:
            return EVENTS_SCHEDULED_NAME_TEMPLATE
        if key == EVENTS_POSTS_WHERE_KEY:
            return EVENTS_POSTS_WHERE
        if key == EVENTS_ROOM_DELETE_KEY:
            return EVENTS_ROOM_DELETE_WHO
        if key == EVENTS_ROOM_NOTICE_KEY:
            return EVENTS_ROOM_NOTICE
        if key == EVENTS_REVIEW_MODE_KEY:
            return EVENTS_REVIEW_MODE
        if key == EVENTS_MOVED_LINE_KEY:
            return EVENTS_MOVED_LINE
        if key == REQUEST_FILED_KEY:
            return REQUEST_FILED
        if key == DEFAULT_TIMEZONE_KEY:
            return DEFAULT_TZ
        if key == TIMEZONE_CHOICES_KEY:
            return ", ".join(TIMEZONE_CHOICES)
        if key == TIME_STEP_KEY:
            return TIME_STEP_MINUTES
        if key == "poll_mode":
            return "on"
        if key == "poll_who_can_create":
            return "staff"
        if key == "poll_review_mode":
            return "off"
        if key == "poll_default_hours":
            return POLL_DEFAULT_HOURS
        if key == "poll_channel_id":
            return self.settings.test_channel_id if self.settings.test_mode else None
        if key == "poll_reminder_minutes":
            return POLL_REMINDER_MINUTES
        if key == "poll_auto_thread":
            return False
        if key == "poll_pin":
            return True
        if key == "poll_shadow_note":
            return POLL_SHADOW_NOTE
        if key == "poll_archive_days":
            return POLL_ARCHIVE_DAYS
        if key == "poll_archive_drop_votes":
            return True
        if key == "poll_date_labels":
            return POLL_DATE_LABEL_FORMS[0]
        if key == "poll_panel_minutes":
            return 10
        if key == "poll_creator_may_end":
            return True
        if key == "poll_drafts":
            return True
        if key == "poll_draft_days":
            return POLL_DRAFT_DAYS
        if key == "golive_panel_minutes":
            return 10
        if key == "birthday_mode":
            return "shadow"
        if key == "birthday_channel_id":
            if self.settings.test_mode:
                return self.settings.test_channel_id
            return BIRTHDAY_CHANNEL_ID
        if key == "birthday_template":
            return BIRTHDAY_TEMPLATE
        if key == "birthday_color":
            return BIRTHDAY_COLOR
        if key == "birthday_show_age":
            return False
        if key == "birthday_panel_minutes":
            return 10
        if key == "birthday_panel_next_for_members":
            return True
        if key == "birthday_panel_lookup":
            return True
        if key == "event_panel_minutes":
            return 10
        if key == "event_panel_own_list":
            return False
        if key == "modmail_enabled":
            return False
        if key == "modmail_mode":
            return CHANNEL_MODE
        if key == "modmail_category_id":
            return None if self.settings.test_mode else MODMAIL_CATEGORY_ID
        if key == "modmail_log_channel_id":
            if self.settings.test_mode:
                return self.settings.test_channel_id
            return MODMAIL_LOG_CHANNEL_ID
        if key == "automod_mode":
            return "shadow"
        if key == "automod_rules":
            return validate_rules({})
        if key == "automod_warn_threshold":
            return WARN_THRESHOLD_DEFAULT
        if key == "modlog_channel_id":
            return self.default("log_channel_id")
        if key == "mod_dm_on_action":
            return "server_action_reason"
        if key == "bot_bio":
            return BOT_BIO_TEMPLATE.format(site=self.settings.origin)
        if key == "status_prefix":
            return STATUS_PREFIX
        if key == "operator_read_log":
            return True
        if key == SPAWNED_STAFF_REACH:
            return SPAWNED_STAFF_REACH_DEFAULT
        if key == "rolemenu_mode":
            return "off"
        if key == "request_mode":
            return "on"
        if key == "request_who_can_file":
            return "everyone"
        if key == "request_notify_channel_id":
            return self.settings.test_channel_id if self.settings.test_mode else None
        if key == "request_dm_on_decision":
            return True
        if key == "request_channel_moves":
            return list(REQUEST_CARD_DEFAULT)
        if key == "request_review_by_other":
            return False
        if key == "request_panel_minutes":
            return 10
        if key == "request_panel_own_list":
            return False
        if key == "request_check_fallback_channel":
            return True
        if key == "request_check_on_ready":
            return False
        if key == "request_post_buttons":
            return True
        if key == HANDOFF_MODE:
            return "on"
        if key == HANDOFF_CONFIRM_HOURS:
            return HANDOFF_CONFIRM_HOURS_DEFAULT
        if key == "request_forum_adopts_posts":
            return True
        if key == "chat_mode":
            return "on"
        if key == "chat_cooldown_seconds":
            return CHAT_COOLDOWN_SECONDS
        if key == "chat_greeting_reaction":
            return False
        if key == "chat_reply_in_threads":
            return True
        if key == "chat_route_ping_staff":
            return False
        if key == "chat_status_admin_only":
            return True
        if key == "chat_staff_can_ping_roles":
            return True
        if key == "chat_escalation_names":
            return CHAT_ESCALATION_NAMES
        if key == "chat_llm_mode":
            return "off"
        if key == "chat_simple_model":
            return GROQ_DEFAULT_MODEL
        if key == "chat_personality":
            return CHAT_PERSONALITY_DEFAULT
        if key == "chat_person_hourly_turns":
            return CHAT_PERSON_HOURLY_TURNS
        if key == "chat_daily_turns":
            return CHAT_DAILY_TURNS
        if key == "chat_monthly_cap_usd":
            return CHAT_MONTHLY_CAP_USD
        if key == "chat_memory_mode":
            return "off"
        if key == "chat_memory_consent":
            return CONSENT_CHOICES[0]
        if key == "chat_memory_retention_days":
            return RETENTION_DAYS
        if key == "chat_memory_dm_scope":
            return DM_SCOPES[0]
        if key == "chat_memory_staff_view":
            return STAFF_VIEWS[0]
        if key == "chat_memory_notes_max":
            return NOTES_MAX
        if key == "chat_memory_threads_max":
            return THREADS_MAX
        if key == "chat_memory_model":
            return ""
        if key == "emoji_skin_tone":
            return SKIN_TONE_DEFAULT
        if key == "cost_hosting_usd":
            return COST_HOSTING_USD
        if key == "raidtrain_mode":
            return "off"
        if key == "raidtrain_slot_minutes":
            return RAIDTRAIN_SLOT_MINUTES
        if key == "raidtrain_reminder_minutes":
            return RAIDTRAIN_REMINDER_MINUTES
        if key == "raidtrain_poll_minutes":
            return RAIDTRAIN_POLL_MINUTES
        if key == "raidtrain_require_link":
            return True
        if key == "raidtrain_thread":
            return True
        if key == "raidtrain_live_posts":
            return True
        if key == "raidtrain_max_slots_per_member":
            return RAIDTRAIN_MAX_SLOTS_PER_MEMBER
        if key == "raidtrain_scheduled_event":
            return False
        if key == RAIDTRAIN_SCHEDULED_NAME_KEY:
            return RAIDTRAIN_SCHEDULED_NAME_TEMPLATE
        if key == "applications_mode":
            return "off"
        if key == "applications_retry_days":
            return APPLICATIONS_RETRY_DAYS
        if key == "applications_dm_on_decision":
            return True
        if key == "applications_roster_shows_left":
            return True
        if key == "applications_panel_minutes":
            return 10
        if key == "applications_panel_own_list":
            return True
        if key == "memory_panel_minutes":
            return 10
        if key == "youtube_panel_minutes":
            return 10
        if key == "youtube_unlink_dms_them":
            return True
        if key == "youtube_live_mode":
            return "off"
        if key == "youtube_live_poll_minutes":
            return YOUTUBE_LIVE_POLL_MINUTES
        if key == "youtube_live_end_misses":
            return YOUTUBE_LIVE_END_MISSES
        if key == "pings_panel_minutes":
            return 10
        if key == "voice_panel_minutes":
            return 10
        if key == "automod_panel_minutes":
            return 10
        if key == "automod_arm_needs_confirm":
            return True
        if key == "chat_panel_minutes":
            return 10
        if key == "raidtrain_panel_minutes":
            return 10
        if key == "rolemenu_panel_minutes":
            return 10
        if key == "honeypot_panel_minutes":
            return 10
        if key == "modmail_panel_minutes":
            return 10
        if key == "modmail_reply_style":
            return MODMAIL_BOTH
        if key == MODMAIL_MEMBER_COMMAND:
            return True
        if key == MODMAIL_PANEL_TITLE:
            return MODMAIL_PANEL_TITLE_DEFAULT
        if key == MODMAIL_PANEL_TEXT:
            return MODMAIL_PANEL_TEXT_DEFAULT
        if key == MODMAIL_OPEN_WITH_BUTTON:
            return False
        if key == MODMAIL_FORUM_TAGS:
            return True
        if key == MODMAIL_LOG_ON_OPEN:
            return True
        if key == MODMAIL_PANEL_FOLLOWS_POST:
            return MODMAIL_PANEL_FOLLOWS_POST_DEFAULT
        if key == FRONTDOOR_MODE:
            return FRONTDOOR_MODE_DEFAULT
        if key == FRONTDOOR_TITLE:
            return FRONTDOOR_TITLE_DEFAULT
        if key == FRONTDOOR_TEXT:
            return FRONTDOOR_TEXT_DEFAULT
        if key == FRONTDOOR_TICKET_LABEL:
            return FRONTDOOR_TICKET_LABEL_DEFAULT
        if key == FRONTDOOR_REQUEST_LABEL:
            return FRONTDOOR_REQUEST_LABEL_DEFAULT
        if key == FRONTDOOR_EVENT_LABEL:
            return FRONTDOOR_EVENT_LABEL_DEFAULT
        if key == FRONTDOOR_FOLLOWS_POST:
            return FRONTDOOR_FOLLOWS_POST_DEFAULT
        if key == FRONTDOOR_REPLACES_TICKET_BUTTON:
            return True
        if key == FRONTDOOR_PANEL_MINUTES:
            return 10
        if key == "mod_panel_minutes":
            return 10
        if key == SETTINGS_PANEL_MINUTES:
            return 10
        if key == SETTINGS_CORE_KEYS_ADMIN_ONLY:
            return SETTINGS_CORE_KEYS_ADMIN_ONLY_DEFAULT
        if key == ERROR_SENTENCE_KEY:
            return ERROR_SENTENCE
        if key == ERROR_RETRY_LABEL_KEY:
            return ERROR_RETRY_LABEL
        if key == ERROR_RETRY_MINUTES_KEY:
            return ERROR_RETRY_MINUTES
        if key == ERROR_RETRY_EXPIRED_KEY:
            return ERROR_RETRY_EXPIRED
        if key == BOOT_STATUS_MODE:
            return BOOT_STATUS_MODE_DEFAULT
        if key == BOOT_STATUS_TEXT_KEY:
            return BOOT_STATUS_TEXT
        if key == SHUTDOWN_STATUS_TEXT_KEY:
            return SHUTDOWN_STATUS_TEXT
        if key == HIDE_COMMANDS_WHEN_OFF:
            return HIDE_COMMANDS_WHEN_OFF_DEFAULT
        if key == LOGS_COUNT:
            return LOGS_DEFAULT
        if key == LOGS_IMPORTANT_ONLY:
            return False
        if key == SELFTEST_ON_BOOT:
            return bool(getattr(self.settings, "test_mode", False))
        if key == SELFTEST_CHANNEL_ID:
            return self.settings.test_channel_id
        if key == SELFTEST_PURGE_MINUTES:
            return SELFTEST_PURGE_MINUTES_DEFAULT
        if key == SELFTEST_LOG_LEVEL:
            return OFF
        if key == PERSONALITY_POOL_SYNC:
            return PERSONALITY_POOL_SYNC_DEFAULT
        if key == PERSONALITY_POOL_PEER_URL:
            return PERSONALITY_POOL_PEER_URL_DEFAULT
        if key == "posts_mode":
            return POSTS_MODE_DEFAULT
        if key == "posts_panel_minutes":
            return POSTS_PANEL_MINUTES_DEFAULT
        if key == "posts_versions_keep":
            return POSTS_VERSIONS_KEEP_DEFAULT
        if key == "posts_versions_summary_chars":
            return POSTS_VERSIONS_SUMMARY_CHARS_DEFAULT
        if key == "guides_mode":
            return GUIDES_MODE_DEFAULT
        if key == "guides_who_edits":
            return GUIDES_WHO_EDITS_DEFAULT
        if key in ("guides_help_links", "guides_show_facts", "guides_fault_files_request"):
            return True
        if key == "minutes_mode":
            return MINUTES_MODE_DEFAULT
        if key == "minutes_start_text":
            return MINUTES_START_TEXT_DEFAULT
        if key == "minutes_notes_title":
            return MINUTES_NOTES_TITLE_DEFAULT
        if key == "minutes_prompt":
            return MINUTES_PROMPT_DEFAULT
        if key == "minutes_chunk_seconds":
            return MINUTES_CHUNK_SECONDS_DEFAULT
        if key == "minutes_max_hours":
            return MINUTES_MAX_HOURS_DEFAULT
        if key == "minutes_keep_days":
            return MINUTES_KEEP_DAYS_DEFAULT
        if key == "minutes_panel_minutes":
            return MINUTES_PANEL_MINUTES_DEFAULT
        if key.endswith("_log_level"):
            return LEVEL_DEFAULT
        if KEY_TYPES.get(key) in ("channels", "roles"):
            return []
        return None

    async def load(self) -> None:
        cur = await self.db.conn.execute("SELECT guild_id, key, value FROM settings")
        cache: dict[tuple[int, str], Any] = {}
        retired: set[str] = set()
        for row in await cur.fetchall():
            key = row["key"]
            if key not in KEY_TYPES:
                retired.add(key)
                continue
            try:
                cache[(row["guild_id"], key)] = json.loads(row["value"])
            except (TypeError, ValueError):
                retired.add(key)
        self._cache = cache
        log.info("settings loaded: %d row(s)", len(self._cache))
        if retired:
            log.warning("settings ignored: %s", ", ".join(sorted(retired)))

    def get(self, guild_id: int, key: str) -> Any:
        if key not in KEY_TYPES:
            raise SettingError(f"{key!r} is not a Black Bloc setting.")
        return self._cache.get((guild_id, key), self.default(key))

    def all(self, guild_id: int) -> dict[str, Any]:
        return {key: self.get(guild_id, key) for key in KEY_TYPES}

    def is_stored(self, guild_id: int, key: str) -> bool:
        """What `clear` would find, asked without deleting it."""
        if key not in KEY_TYPES:
            raise SettingError(f"{key!r} is not a Black Bloc setting.")
        return (guild_id, key) in self._cache

    async def set(self, guild_id: int, key: str, value: Any, *, by: int | None = None) -> Any:
        stored = coerce_value(key, value)
        await self.db.conn.execute(
            "INSERT OR REPLACE INTO settings(guild_id, key, value, updated_by, updated_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (guild_id, key, json.dumps(stored), by, datetime.now(UTC).isoformat()),
        )
        await self.db.conn.commit()
        self._cache[(guild_id, key)] = stored
        await self._changed(guild_id, key, stored, by)
        return stored

    async def clear(self, guild_id: int, key: str, *, by: int | None = None) -> bool:
        """Forget one stored setting so its default applies again."""
        if key not in KEY_TYPES:
            raise SettingError(f"{key!r} is not a Black Bloc setting.")
        cur = await self.db.conn.execute(
            "DELETE FROM settings WHERE guild_id = ? AND key = ?", (guild_id, key)
        )
        await self.db.conn.commit()
        self._cache.pop((guild_id, key), None)
        cleared = bool(cur.rowcount)
        if cleared:
            log.info("settings cleared: %s for guild %s by %s", key, guild_id, by)
            await self._changed(guild_id, key, self.default(key), by)
        return cleared

    def staff_roles(self, guild: Any) -> list[Any]:
        channel_id = self.get(guild.id, "staff_channel_id")
        channel = guild.get_channel(channel_id) if channel_id else None
        return resolved_staff_roles(guild, channel)

    def staff_role_ids(self, guild: Any) -> set[int]:
        return {role.id for role in self.staff_roles(guild)}

    def is_staff(self, member: Any) -> bool:
        guild = getattr(member, "guild", None)
        staff_ids = self.staff_role_ids(guild) if guild is not None else set()
        return member_is_staff(member, staff_ids)

    def staff_refusal(self, guild_id: int) -> str:
        channel_id = self.get(guild_id, "staff_channel_id")
        where = f"<#{channel_id}>" if channel_id else "the staff channel"
        return (
            "That command is for staff only, so nothing was changed. It needs either the "
            f"Manage Server permission or a role that can see {where}. Ask a server admin to "
            "give you one of those, or to run the command for you."
        )
