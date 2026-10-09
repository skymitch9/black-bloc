from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime
from inspect import isawaitable
from typing import Any
from urllib.parse import urlsplit

from . import tone_keys
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
    DISTIL_MIN_TURNS,
    DISTIL_MIN_TURNS_CEILING,
    DM_SCOPES,
    MEMORY_MODES,
    MIN_TURNS_KEY,
    NOTES_CEILING,
    NOTES_MAX,
    RAPPORT_CEILING,
    RAPPORT_LINE,
    RAPPORT_LINE_CHARS,
    RAPPORT_LINE_FIELDS,
    RAPPORT_LINE_KEY,
    RAPPORT_MAX,
    RAPPORT_MAX_KEY,
    RETENTION_DAYS,
    RETENTION_MAX_DAYS,
    STAFF_VIEWS,
    SWEEP_HOURS,
    SWEEP_HOURS_KEY,
    SWEEP_HOURS_MAX,
    THREADS_CEILING,
    THREADS_MAX,
)
from .config import Settings
from .emoji import SKIN_TONE_DEFAULT, SKIN_TONE_NAMES
from .groq import DEFAULT_MODEL as GROQ_DEFAULT_MODEL
from .knowledge import GROUNDING_NOTE, GROUNDING_NOTE_KEY
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
from .personas import (
    BANTER_STYLE,
    BANTER_STYLE_KEY,
    COOKOUT,
    COOKOUT_VOICE,
    COOKOUT_VOICE_KEY,
    PERSONALITY_CHOICES,
    TONE_CLAUSE,
    TONE_CLAUSE_KEY,
)
from .points.model import PointsError
from .points.scoring import DEFAULT_PER_RUN as POINTS_PER_RUN_DEFAULT
from .points.xp import DEFAULT_HIGH as POINTS_XP_HIGH
from .points.xp import DEFAULT_LOW as POINTS_XP_LOW
from .points.xp import DEFAULT_TIERS_TEXT as POINTS_TIERS_TEXT
from .points.xp import MOST_XP as POINTS_MOST_XP
from .points.xp import parse_tiers as parse_point_tiers
from .points.xp import tiers_text as point_tiers_text
from .polls import DATE_LABEL_FORMS as POLL_DATE_LABEL_FORMS
from .polls import MAX_HOURS as POLL_MAX_HOURS
from .polls import MIN_HOURS as POLL_MIN_HOURS
from .polls import MODES as POLL_MODES
from .polls import SHADOW_NOTE as POLL_SHADOW_NOTE
from .shadow import NOTE_DEFAULT as REHEARSAL_NOTE_DEFAULT
from .shadow import NOTE_KEY as REHEARSAL_NOTE
from .shadow import REHEARSAL_KEY as SHADOW_CHANNEL
from .shadow import feature_key as shadow_feature_key
from .storage.db import Database
from .structure import FEATURE as STRUCTURE_FEATURE
from .structure import MODE_DEFAULT as STRUCTURE_MODE_DEFAULT
from .structure import MODES as STRUCTURE_MODES
from .structure import ROLE_KEY as STRUCTURE_ROLE_KEY
from .timezones import DEFAULT_TZ, is_known, suggest

log = logging.getLogger(__name__)

LIVE_NOW_CHANNEL_ID = 1225457308230746202
GOLIVE_TEMPLATE = (
    "REGULATORS! Mount up! **{name}** is currently streaming **{game}**! "
    "Check it out: {url}"
)
GOLIVE_MODES = ("off", "shadow", "on")
GOLIVE_LIVE_FIELD = "{live}"
GOLIVE_LIVE_AUTHOR_KEY = "golive_live_author"
GOLIVE_LIVE_AUTHOR = "{name} is now live on {platform}!"
GOLIVE_AUTHOR_FIELDS = ("name", "platform")
GOLIVE_END_TEMPLATE = "**{name}** was streaming **{game}** — the stream has ended. {url}"
GOLIVE_END_SUFFIX_RETIRED = "golive_end_suffix"
GOLIVE_END_MODE_RETIRED = "golive_end_mode"
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
RAIDTRAIN_EVENT_DEFAULT_KEY = "raidtrain_event_default"

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
    GOLIVE_LIVE_AUTHOR_KEY: "text",
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
    "chat_greeting_via_model": "enum",
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
    "chat_greeting_via_model": CHAT_LLM_MODES,
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
    "golive_mode": (
        "whether a stream is announced at all. off watches nobody; shadow watches and logs what "
        "it would have posted without posting it; on posts the announcement. Off by default, so "
        "nothing reaches the server until somebody turns it on"
    ),
    "golive_channel_id": (
        "the channel every go-live announcement is posted in. Blank — the default — means "
        "nothing is posted anywhere however golive_mode is set, so this is the one setting "
        "go-live cannot work without"
    ),
    "golive_template": (
        "the sentence a go-live announcement is made of. It takes {name} {game} {title} {url} "
        "{platform}, and {platform} fills itself in as Twitch or YouTube so one wording serves "
        "both platforms"
    ),
    GOLIVE_LIVE_AUTHOR_KEY: (
        "the small top line of the announcement card while the stream is still running. It "
        "takes {name} and {platform} only, because a stream that has not finished has no length "
        "yet; blank keeps 'is now live on'"
    ),
    "golive_end_template": (
        "the announcement once the stream is over, and the only place that wording lives. "
        "{live} is the sentence exactly as it was posted, so {live} — stream ended appends "
        "and a wording without {live} rewrites the whole post; the other fields are {name} "
        "{game} {title} {url} {platform} {duration}. Blank keeps the posted sentence and adds "
        "nothing; wording that cannot be rendered falls back to the default"
    ),
    "golive_end_author": (
        "the small top line of the announcement card once the stream is over. It takes {name} "
        "{platform} {duration}; blank keeps 'was live on'"
    ),
    "golive_end_keep_mention": (
        "whether the role mention stays at the front of the announcement after it is rewritten "
        "to say the stream ended. off — the default — drops it. Nobody is pinged by an edit "
        "either way, so this is only about how the finished post reads"
    ),
    GOLIVE_COSTREAM_MODE_KEY: (
        "what happens when somebody already live on one platform goes live on the other as "
        "well. on — the default — edits the announcement that is already out so ONE post names "
        "both platforms; off leaves the first post alone and the second platform is not "
        "announced at all"
    ),
    GOLIVE_COSTREAM_TEMPLATE_KEY: (
        "the sentence used while somebody is live on two platforms at once. It takes {name} "
        "{game} {title} {url} {platform} {also_url} {also_platform}. Twitch is always written "
        "first and is the only link Discord shows a preview for — the second link is always "
        "posted with its preview suppressed"
    ),
    GOLIVE_COSTREAM_AUTHOR_KEY: (
        "the small top line of the announcement card while two platforms are live. It takes "
        "{name} {game} {title} {url} {platform} {also_url} {also_platform}"
    ),
    "golive_live_role_id": (
        "a role Black Bloc puts on somebody while they are streaming and takes off again when "
        "the stream ends. Blank — the default — means no role is handed out at all"
    ),
    "golive_require_role_id": (
        "when this is set, only people wearing that role are ever announced. Blank — the "
        "default — announces anybody the bot sees streaming"
    ),
    "golive_ignore_role_id": (
        "anybody wearing this role is never announced, whatever else would have allowed it. "
        "Blank — the default — means nobody is held back this way"
    ),
    "golive_cooldown_minutes": (
        "how many minutes must pass before the same person is announced a second time, so a "
        "stream that drops and comes back does not get two posts. 60 by default"
    ),
    "golive_ping_role_id": (
        "the role mentioned in front of every go-live announcement, so the people who asked for "
        "streaming pings get one. Blank — the default — posts the announcement with no mention "
        "at all"
    ),
    "golive_max_session_hours": (
        "a safety net: a stream still marked live after this many hours is closed anyway, in "
        "case the bot never saw it end. 12 by default"
    ),
    "golive_embed": (
        "how the announcement is drawn. on — the default — posts an embed carrying the game's "
        "art and the stream's title; off posts the sentence on its own"
    ),
    "golive_boot_sweep": (
        "whether a restart looks for people who are ALREADY streaming. on — the default — walks "
        "every member's Discord status the moment the bot starts and announces anyone live with "
        "no session open, so a restart mid-stream does not lose the announcement; off waits for "
        "the next status change"
    ),
    "pings_mode": (
        "whether members can opt in to pings at all. off — the default — stops every opt-in and "
        "every ping, though nobody loses a role they already wear; on lets members take the "
        "shared Events role and follow individual streamers"
    ),
    "pings_events_role_name": (
        "what **Set up the Events role** on `/pings` calls the one shared opt-in role for "
        "go-live and event pings when it has to make it. *Events* by default; a role of that "
        "name that already exists is reused rather than duplicated"
    ),
    "pings_fan_role_creation": (
        "who can bring a streamer's own follower role into being. follow — the default — makes "
        "it the first time somebody follows them on `/pings`, so a role exists only where "
        "somebody wants one; self lets the streamer make their own with **Start my own ping "
        "role**; staff means only an Auntie or Uncle can, from `/pings` ▸ **Streamers…**; auto "
        "makes one the moment a Twitch channel is linked. Staff can always do it for anybody, "
        "whichever this says"
    ),
    "pings_fan_role_template": (
        "what a streamer's own follower role is called. {name} is their display name at the "
        "moment the role is made and is the only field there is; *{name} pings* by default"
    ),
    "pings_fan_role_on_unlink": (
        "what happens to a streamer's follower role when they unlink Twitch or opt out of "
        "announcements. keep — the default — leaves it alone, and since nothing is announced "
        "nobody is pinged by it; delete takes the role off the server"
    ),
    "pings_fan_role_delete": (
        "whether the Discord role itself goes when a streamer's follower role is removed here. "
        "on — the default — deletes it from the server; off forgets it here and leaves the role "
        "for somebody to tidy by hand"
    ),
    "pings_streamer_stale_days": (
        "how many days without a go-live before somebody drops off the streamer list `/pings` ▸ "
        "**Follow a streamer…** offers. 90 by default. Their role is kept while anybody still "
        "wears it, and one more go-live puts them back on the list"
    ),
    "pings_empty_role_days": (
        "how many days a streamer's follower role that NOBODY wears survives before Black Bloc "
        "deletes it, so the server's role count tracks who is actually followed. 30 by default; "
        "a role somebody wears is never deleted by this"
    ),
    "pings_onboarding_managed": (
        "whether Black Bloc keeps its two Discord onboarding prompts in step with the Events, "
        "raid-train and streamer roles. on — the default — rewrites them as those roles change; "
        "off leaves the prompts exactly as somebody left them and Black Bloc never writes to "
        "onboarding again. Only does anything on a Community server"
    ),
    "pings_onboarding_prompt_title": (
        "what Black Bloc's first onboarding prompt is called — *What should ping you?* by "
        "default. It is also how Black Bloc recognises which prompts are its own, so changing "
        "it makes a fresh pair and leaves the old ones for somebody to delete by hand"
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
        "posted panels, on posts them again; off also hides /rolemenu while hiding is on, and "
        "the timed roles stay under /mod ▸ Role grants…"
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
        "no channels at all. A channel this role cannot read still counts when a role members "
        "pick for themselves on a role menu can (Sports, Shows, RPGer …), and staff can tell "
        "the bot about any one channel, or keep it quiet, on the Channels page"
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
    "chat_greeting_via_model": (
        "on (a hello is answered by the quick model in the member's tone, with no server notes) "
        "or off (a hello gets one of the greeting's own written lines). Only used while "
        "chat_llm_mode is on; the cookout voice always uses the written lines, and a model that "
        "fails or is capped falls back to them"
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
    "marathon": "event",
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


# Birthdays, post today's wishes by hand (2026-09-23). Its own block so parallel branches merge
# textually; every word the door says is one of these keys. Design: info/birthdays-panel-design.md.
BIRTHDAY_POST_BUTTON_KEY = "birthday_post_button"
BIRTHDAY_POST_CONFIRM_KEY = "birthday_post_confirm"
BIRTHDAY_POST_UNSENT_KEY = "birthday_post_unsent_label"
BIRTHDAY_POST_AGAIN_KEY = "birthday_post_again_label"
BIRTHDAY_POST_NOBODY_KEY = "birthday_post_nobody"
BIRTHDAY_POST_OFF_KEY = "birthday_post_off"
BIRTHDAY_POST_POSTED_KEY = "birthday_post_posted"
BIRTHDAY_POST_REHEARSED_KEY = "birthday_post_rehearsed"
BIRTHDAY_POST_SKIPPED_KEY = "birthday_post_skipped"
BIRTHDAY_POST_MISSING_KEY = "birthday_post_missing"
BIRTHDAY_POST_FAILED_KEY = "birthday_post_failed"
BIRTHDAY_POST_COUNT_FIELDS = ("n",)
BIRTHDAY_POST_WHERE_FIELDS = ("n", "channel")
BIRTHDAY_POST_WORDS: dict[str, str] = {
    BIRTHDAY_POST_BUTTON_KEY: "Post today's wishes",
    BIRTHDAY_POST_CONFIRM_KEY: (
        "Post today's birthday wishes now? A birthday is today in the member's own time zone. "
        "**Post the ones not sent yet** does straight away what the five-minute sweep would. "
        "**Post them all again** also wishes anyone already wished today, so they get a second "
        "post."
    ),
    BIRTHDAY_POST_UNSENT_KEY: "Post the ones not sent yet",
    BIRTHDAY_POST_AGAIN_KEY: "Post them all again",
    BIRTHDAY_POST_NOBODY_KEY: (
        "Nobody who is opted in has a birthday today, so nothing was posted."
    ),
    BIRTHDAY_POST_OFF_KEY: (
        "Birthday wishes are **off**, so nothing was posted. Staff can switch them to "
        "**shadow** or **on** with **Wishes are…** on `/birthday`, or birthday_mode on the "
        "Birthdays page, and then post again."
    ),
    BIRTHDAY_POST_POSTED_KEY: "Posted {n} birthday wish(es) in {channel}.",
    BIRTHDAY_POST_REHEARSED_KEY: (
        "Birthday wishes are in **shadow**, so {n} wish(es) went to the rehearsal home, "
        "{channel}, and nothing to the real channel."
    ),
    BIRTHDAY_POST_SKIPPED_KEY: (
        "{n} already wished today were left alone — **Post them all again** posts those too."
    ),
    BIRTHDAY_POST_MISSING_KEY: (
        "{n} could not be found in the member list, so nothing was posted for them."
    ),
    BIRTHDAY_POST_FAILED_KEY: (
        "{n} could not be posted — **Logs** on `/birthday` or the Birthdays page says why."
    ),
}
KEY_TYPES.update({key: "text" for key in BIRTHDAY_POST_WORDS})
KEY_HELP.update(
    {
        BIRTHDAY_POST_BUTTON_KEY: (
            "what the staff button that posts today's birthday wishes by hand is called, on the "
            "/birthday panel and the Birthdays page"
        ),
        BIRTHDAY_POST_CONFIRM_KEY: (
            "the question staff are asked before today's wishes are posted by hand, above the "
            "two moves"
        ),
        BIRTHDAY_POST_UNSENT_KEY: (
            "what the move that posts only the wishes not sent yet today is called — the "
            "five-minute sweep, run now"
        ),
        BIRTHDAY_POST_AGAIN_KEY: (
            "what the move that posts every birthday today again, including anyone already "
            "wished, is called"
        ),
        BIRTHDAY_POST_NOBODY_KEY: (
            "what staff are told when they post today's wishes and nobody opted in has a "
            "birthday today"
        ),
        BIRTHDAY_POST_OFF_KEY: (
            "what staff are told when they post today's wishes while birthday_mode is off; "
            "nothing is posted when this is said"
        ),
        BIRTHDAY_POST_POSTED_KEY: (
            "the line that says how many wishes were posted by hand. It takes {n}, the count, "
            "and {channel}, the channel they went to"
        ),
        BIRTHDAY_POST_REHEARSED_KEY: (
            "the line that says how many wishes went to the rehearsal home because "
            "birthday_mode is shadow. It takes {n} and {channel}"
        ),
        BIRTHDAY_POST_SKIPPED_KEY: (
            "the line that says how many birthdays today were already wished and left alone. "
            "It takes {n}"
        ),
        BIRTHDAY_POST_MISSING_KEY: (
            "the line that says how many birthdays today belong to somebody Black Bloc cannot "
            "find in the member list. It takes {n}"
        ),
        BIRTHDAY_POST_FAILED_KEY: (
            "the line that says how many wishes Discord refused or had nowhere to go. It takes "
            "{n}; the log row for each says why"
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
            "whether a member is told why their YouTube channel was forgotten. on — the "
            "default — DMs them the reason when STAFF do it; somebody unlinking their own "
            "channel is never DMed"
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
            "whether a linked YouTube channel going live is announced. off probes nothing at "
            "all; shadow probes and logs what it would have posted; on announces it through the "
            "go-live feature exactly like a Twitch stream — so golive_mode and "
            "golive_channel_id still decide whether anybody sees it. Off by default"
        ),
        "youtube_live_poll_minutes": (
            "how many minutes between asking YouTube whether the linked channels are live. 5 by "
            "default; a shorter gap notices a stream sooner and spends more of the daily API "
            "quota when a YOUTUBE_API_KEY is set"
        ),
        "youtube_live_end_misses": (
            "how many probes in a row must read offline before a YouTube stream is treated as "
            "ended and its announcement rewritten. 2 by default, so one bad answer from YouTube "
            "does not end a stream that is still running"
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
SPOTLIGHT_BUMP_PINGS_KEY = "spotlight_bump_pings"
SPOTLIGHT_PIN_KEY = "spotlight_pin"
SPOTLIGHT_DEFAULT_DAYS_KEY = "spotlight_default_days"
SPOTLIGHT_EVENT_SLACK_KEY = "spotlight_event_slack_hours"
SPOTLIGHT_RANGE_KEY = "spotlight_range_template"
SPOTLIGHT_RANGE_KEPT_KEY = "spotlight_range_kept_template"
SPOTLIGHT_SCHEDULED_WORD_KEY = "spotlight_scheduled_word"
SPOTLIGHT_DATES_BUTTON_KEY = "spotlight_dates_button"
SPOTLIGHT_STARTS_LABEL_KEY = "spotlight_starts_label"
SPOTLIGHT_ENDS_LABEL_KEY = "spotlight_ends_label"
SPOTLIGHT_END_BEFORE_START_KEY = "spotlight_end_before_start"
SPOTLIGHT_BAD_DATE_KEY = "spotlight_bad_date"
SPOTLIGHT_PING_MODE_DEFAULT_KEY = "spotlight_ping_mode_default"
SPOTLIGHT_WINDOW_OPEN_REMINDER_KEY = "spotlight_window_open_reminder"
SPOTLIGHT_WINDOW_KEEP_DAYS_KEY = "spotlight_window_keep_days"
GOLIVE_EXPIRY_KEEPS_MARATHON_CHANNELS_KEY = "golive_expiry_keeps_marathon_channels"
SPOTLIGHT_PINGS_ALWAYS_WORDS_KEY = "spotlight_pings_always_words"
SPOTLIGHT_PINGS_NEVER_WORDS_KEY = "spotlight_pings_never_words"
SPOTLIGHT_PINGS_EVENTS_WORDS_KEY = "spotlight_pings_events_words"
SPOTLIGHT_WINDOW_OPEN_WORDS_KEY = "spotlight_window_open_words"
SPOTLIGHT_WINDOW_NEXT_WORDS_KEY = "spotlight_window_next_words"
SPOTLIGHT_WINDOW_NONE_WORDS_KEY = "spotlight_window_none_words"
PING_ALWAYS = "always"
PING_NEVER = "never"
PING_EVENTS = "events"
PING_MODES = (PING_ALWAYS, PING_NEVER, PING_EVENTS)
CHANNEL_SPOTLIGHT_DEFAULT_KEY = "golive_channel_spotlight_default"
CHANNEL_OPTOUT_POST_KEY = "golive_channel_optout_post"
CHANNEL_OPTOUT_END = "end"
CHANNEL_OPTOUT_DELETE = "delete"
CHANNEL_OPTOUT_LEAVE = "leave"
CHANNEL_OPTOUT_POSTS = (CHANNEL_OPTOUT_END, CHANNEL_OPTOUT_DELETE, CHANNEL_OPTOUT_LEAVE)
MEMBER_OPTOUT_POST_KEY = "golive_member_optout_post"
MEMBER_OPTOUT_END = CHANNEL_OPTOUT_END
MEMBER_OPTOUT_DELETE = CHANNEL_OPTOUT_DELETE
MEMBER_OPTOUT_LEAVE = CHANNEL_OPTOUT_LEAVE
MEMBER_OPTOUT_POSTS = CHANNEL_OPTOUT_POSTS
SPOTLIGHT_POLL_MINUTES = 5
SPOTLIGHT_POLL_MIN_MINUTES = 1
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
SPOTLIGHT_RANGE_FIELDS = ("start", "end")
SPOTLIGHT_GIVEN_FIELDS = ("given",)
SPOTLIGHT_RANGE = "from {start} to {end}"
SPOTLIGHT_RANGE_KEPT = "from {start} · kept"
SPOTLIGHT_SCHEDULED_WORD = "scheduled"
SPOTLIGHT_DATES_BUTTON = "Set dates…"
SPOTLIGHT_STARTS_LABEL = "Starts — blank means now"
SPOTLIGHT_ENDS_LABEL = "Ends — blank means for ever"
SPOTLIGHT_END_BEFORE_START = (
    "That range ends before it starts — {end} comes before {start} — so nothing was "
    "changed. Put the end after the start, or leave the end blank to keep the channel on "
    "the list for ever."
)
SPOTLIGHT_BAD_DATE = (
    "**{given}** is not a date Black Bloc can read, so nothing was changed. Write it as "
    "`YYYY-MM-DD` or `YYYY-MM-DD HH:MM` — for example `2026-09-30 19:00` — or leave the "
    "box blank."
)
SPOTLIGHT_WINDOW_KEEP_DAYS = 30
SPOTLIGHT_WINDOW_KEEP_DAYS_MIN = 1
SPOTLIGHT_WINDOW_KEEP_DAYS_MAX = 365
SPOTLIGHT_WINDOW_FIELDS = ("window",)
SPOTLIGHT_END_FIELDS = ("end",)
SPOTLIGHT_PINGS_ALWAYS_WORDS = "Pings: always"
SPOTLIGHT_PINGS_NEVER_WORDS = "Pings: never"
SPOTLIGHT_PINGS_EVENTS_WORDS = "Pings: during events — {window}"
SPOTLIGHT_WINDOW_OPEN_WORDS = "open until {end}"
SPOTLIGHT_WINDOW_NEXT_WORDS = "next {start} – {end}"
SPOTLIGHT_WINDOW_NONE_WORDS = "no window set"
KEY_TYPES.update(
    {
        SPOTLIGHT_MODE_KEY: "enum",
        SPOTLIGHT_POLL_MINUTES_KEY: "int",
        SPOTLIGHT_END_MISSES_KEY: "int",
        SPOTLIGHT_BUMP_HOURS_KEY: "int",
        SPOTLIGHT_BUMP_TEMPLATE_KEY: "text",
        SPOTLIGHT_BUMP_CLEANUP_KEY: "bool",
        SPOTLIGHT_BUMP_PINGS_KEY: "bool",
        SPOTLIGHT_PIN_KEY: "bool",
        SPOTLIGHT_DEFAULT_DAYS_KEY: "int",
        SPOTLIGHT_EVENT_SLACK_KEY: "int",
        SPOTLIGHT_RANGE_KEY: "text",
        SPOTLIGHT_RANGE_KEPT_KEY: "text",
        SPOTLIGHT_SCHEDULED_WORD_KEY: "text",
        SPOTLIGHT_DATES_BUTTON_KEY: "text",
        SPOTLIGHT_STARTS_LABEL_KEY: "text",
        SPOTLIGHT_ENDS_LABEL_KEY: "text",
        SPOTLIGHT_END_BEFORE_START_KEY: "text",
        SPOTLIGHT_BAD_DATE_KEY: "text",
        SPOTLIGHT_PING_MODE_DEFAULT_KEY: "enum",
        SPOTLIGHT_WINDOW_OPEN_REMINDER_KEY: "bool",
        SPOTLIGHT_WINDOW_KEEP_DAYS_KEY: "int",
        GOLIVE_EXPIRY_KEEPS_MARATHON_CHANNELS_KEY: "bool",
        SPOTLIGHT_PINGS_ALWAYS_WORDS_KEY: "text",
        SPOTLIGHT_PINGS_NEVER_WORDS_KEY: "text",
        SPOTLIGHT_PINGS_EVENTS_WORDS_KEY: "text",
        SPOTLIGHT_WINDOW_OPEN_WORDS_KEY: "text",
        SPOTLIGHT_WINDOW_NEXT_WORDS_KEY: "text",
        SPOTLIGHT_WINDOW_NONE_WORDS_KEY: "text",
        CHANNEL_SPOTLIGHT_DEFAULT_KEY: "bool",
        CHANNEL_OPTOUT_POST_KEY: "enum",
        MEMBER_OPTOUT_POST_KEY: "enum",
    }
)
KEY_CHOICES[SPOTLIGHT_MODE_KEY] = SPOTLIGHT_MODES
KEY_CHOICES[SPOTLIGHT_PING_MODE_DEFAULT_KEY] = PING_MODES
KEY_MIN[SPOTLIGHT_WINDOW_KEEP_DAYS_KEY] = SPOTLIGHT_WINDOW_KEEP_DAYS_MIN
KEY_MAX[SPOTLIGHT_WINDOW_KEEP_DAYS_KEY] = SPOTLIGHT_WINDOW_KEEP_DAYS_MAX
KEY_CHOICES[CHANNEL_OPTOUT_POST_KEY] = CHANNEL_OPTOUT_POSTS
KEY_CHOICES[MEMBER_OPTOUT_POST_KEY] = MEMBER_OPTOUT_POSTS
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
    "Twitch is asked at most once a minute: a gap shorter than {limit} minute spends the "
    "quota and finds a marathon no sooner."
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
            "whether Twitch channels with nobody here behind them are announced at all. off "
            "ignores them; shadow posts the rehearsal copy where shadow_channel_id points; on "
            "announces, pins and reminds in the go-live channel like any other stream"
        ),
        SPOTLIGHT_POLL_MINUTES_KEY: (
            "how many minutes between asking Twitch whether the spotlighted channels are live. "
            "One batched call covers the whole list, so a shorter gap costs little; 5 by default"
        ),
        SPOTLIGHT_END_MISSES_KEY: (
            "how many looks in a row must come back offline before a spotlighted stream is "
            "treated as over and its announcement rewritten. 2 by default, so one hiccup on "
            "Twitch's side does not end a stream that is still running"
        ),
        SPOTLIGHT_BUMP_HOURS_KEY: (
            "how many hours between reminders that a long spotlighted stream is still going. 4 "
            "by default, the owner's number for a GDQ marathon; any one channel's row can set "
            "its own instead"
        ),
        SPOTLIGHT_BUMP_TEMPLATE_KEY: (
            "what a reminder says while a spotlighted stream runs on. It takes {name} {game} "
            "{title} {url} {duration}. Each one is a new short message, never pinned, and never "
            "a ping unless spotlight_bump_pings says otherwise"
        ),
        SPOTLIGHT_BUMP_CLEANUP_KEY: (
            "whether a spotlighted stream's reminders are deleted when it ends. on — the "
            "default — leaves the channel with the one announcement; off leaves every reminder "
            "where it was posted"
        ),
        SPOTLIGHT_BUMP_PINGS_KEY: (
            "whether a reminder mentions the go-live role and the channel's own ping role, the "
            "way the first announcement did. off by default: a ping every few hours through a "
            "24-hour marathon is what makes people mute the channel"
        ),
        SPOTLIGHT_PIN_KEY: (
            "whether a channel newly added to the spotlight list has its announcement pinned "
            "while it streams. on by default; each channel's own row can say otherwise"
        ),
        SPOTLIGHT_DEFAULT_DAYS_KEY: (
            "how many days a newly spotlighted channel stays on the list before it is purged. 7 "
            "by default, and a row can be kept for ever instead"
        ),
        SPOTLIGHT_EVENT_SLACK_KEY: (
            "how many hours past an approved event's end its spotlight row survives, so a "
            "marathon that overruns is still announced. 2 by default; 0 drops the row the "
            "moment the event's end time passes"
        ),
        SPOTLIGHT_RANGE_KEY: (
            "how a spotlight's date range reads wherever it is shown — the panel line, the "
            "Go-live page's Announced cell and the row's drawer. It takes {start} and {end}, "
            "each a short day like 30 Sep; the row's own dates fill them"
        ),
        SPOTLIGHT_RANGE_KEPT_KEY: (
            "how a spotlight that has a start but no end reads. It takes {start} only, because "
            "a row with no end is kept for ever and there is no second date to name"
        ),
        SPOTLIGHT_SCHEDULED_WORD_KEY: (
            "the one word shown beside a spotlight whose start has not arrived yet. Such a row "
            "is on the list and watched, but nothing of its is announced, pinned or reminded "
            "until its start has passed"
        ),
        SPOTLIGHT_DATES_BUTTON_KEY: (
            "what the button that opens a spotlight's start and end boxes is called, on the "
            "/golive Channels panel and on the Go-live page's row drawer"
        ),
        SPOTLIGHT_STARTS_LABEL_KEY: (
            "what the start box is called on the Add a channel form and the Set dates form. "
            "Keep it short — Discord shows at most 45 characters on a modal label"
        ),
        SPOTLIGHT_ENDS_LABEL_KEY: (
            "what the end box is called on the Add a channel form and the Set dates form. Keep "
            "it short — Discord shows at most 45 characters on a modal label"
        ),
        SPOTLIGHT_END_BEFORE_START_KEY: (
            "what somebody is told when the end they gave a spotlight falls before its start. "
            "It takes {start} and {end}; nothing is stored when this is said"
        ),
        SPOTLIGHT_BAD_DATE_KEY: (
            "what somebody is told when a start or end box holds something that is not a date. "
            "It takes {given}, which is what they typed; nothing is stored when this is said"
        ),
        SPOTLIGHT_PING_MODE_DEFAULT_KEY: (
            "when a NEWLY added channel mentions its ping roles. always — the default — pings "
            "on every announcement; never announces, pins and reminds with no role mentioned; "
            "events pings only inside a ping window staff set on its row. Each channel's own "
            "row can say otherwise at any time"
        ),
        SPOTLIGHT_WINDOW_OPEN_REMINDER_KEY: (
            "whether a channel that is ALREADY live when one of its ping windows opens gets one "
            "reminder that pings, so a marathon starting on a channel running reruns is not "
            "missed. on by default; the window closing posts nothing"
        ),
        GOLIVE_EXPIRY_KEEPS_MARATHON_CHANNELS_KEY: (
            "whether a spotlight whose date passes KEEPS its channel row when the row carries a "
            "marathon — a marathon feed, a marathon on the list, or a spotlight a marathon turned "
            "on. on by default: the row turns its spotlight off and is kept for ever, with its "
            "ping role and its feed; off deletes it with its role and feed like any other row. A "
            "row with no marathon on it is deleted either way"
        ),
        SPOTLIGHT_WINDOW_KEEP_DAYS_KEY: (
            "how many days a ping window is kept after it ends, as history on the channel's "
            "row, before the sweep purges it. 30 by default"
        ),
        SPOTLIGHT_PINGS_ALWAYS_WORDS_KEY: (
            "how a channel that pings on every announcement says so, on its row and in the "
            "/golive Channels panel"
        ),
        SPOTLIGHT_PINGS_NEVER_WORDS_KEY: (
            "how a channel that never mentions a role says so, on its row and in the /golive "
            "Channels panel"
        ),
        SPOTLIGHT_PINGS_EVENTS_WORDS_KEY: (
            "how a channel that pings only during events says so. It takes {window}, which is "
            "one of the three window lines below"
        ),
        SPOTLIGHT_WINDOW_OPEN_WORDS_KEY: (
            "the {window} line while a ping window is open. It takes {end}, the moment it "
            "closes, like 19 Jan 23:00"
        ),
        SPOTLIGHT_WINDOW_NEXT_WORDS_KEY: (
            "the {window} line while the next ping window is still ahead. It takes {start} "
            "and {end}, each like 12 Jan 15:00"
        ),
        SPOTLIGHT_WINDOW_NONE_WORDS_KEY: (
            "the {window} line when a channel pings only during events and has no window "
            "ahead of it, so nothing it posts mentions a role"
        ),
        CHANNEL_SPOTLIGHT_DEFAULT_KEY: (
            "whether a channel added through **Add a streamer** with nobody here behind it is "
            "spotlighted from the start — its announcement pinned while it streams and a "
            "reminder every few hours. off by default: it is announced like any other stream, "
            "and its own row's **Spotlight on** adds the pin and the reminders whenever staff "
            "want them"
        ),
        CHANNEL_OPTOUT_POST_KEY: (
            "what becomes of an announcement already posted when a CHANNEL is opted out of "
            "announcements mid-stream. end — the default — unpins it and rewrites it to the "
            "ended wording, exactly as a real stream end does; delete removes the post "
            "outright; leave takes the pin off and leaves the words as they were posted. The "
            "session is closed either way, so no reminder follows and nothing waits on Twitch"
        ),
        MEMBER_OPTOUT_POST_KEY: (
            "what becomes of an announcement already posted when a MEMBER opts out of "
            "announcements mid-stream — the same three treatments the channel key has. end — "
            "the default — unpins it and rewrites it to the ended wording; delete removes the "
            "post outright; leave takes the pin off and leaves the words as they were posted. "
            "The session is closed either way, so their live role comes off and nothing waits "
            "on Twitch or on their presence"
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


# The raid-train page's one decision, in its own appended block.
KEY_TYPES.update({RAIDTRAIN_EVENT_DEFAULT_KEY: "bool"})
KEY_HELP.update(
    {
        RAIDTRAIN_EVENT_DEFAULT_KEY: (
            "whether **Also make an event** starts ticked when somebody begins a raid train, on "
            "the Raid trains page and on the /raidtrain draft panel alike; off by default. "
            "Ticking it sends the train through the same events review a proposal goes through, "
            "so a Lead still approves or denies it. This is only the starting position of a "
            "tick box — whoever starts the train can always set it the other way"
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
FRONTDOOR_SHOW_TICKET = "frontdoor_show_ticket"
FRONTDOOR_SHOW_REQUEST = "frontdoor_show_request"
FRONTDOOR_SHOW_EVENT = "frontdoor_show_event"
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
        FRONTDOOR_SHOW_TICKET: "bool",
        FRONTDOOR_SHOW_REQUEST: "bool",
        FRONTDOOR_SHOW_EVENT: "bool",
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
        FRONTDOOR_SHOW_TICKET: (
            "true shows the button that opens a private modmail ticket on the front door and on "
            "/ask; false leaves it off both. Every other way in (a DM, /modmail) still works"
        ),
        FRONTDOOR_SHOW_REQUEST: (
            "true shows the button that files a request on the front door and on /ask; false "
            "leaves it off both. /request still works"
        ),
        FRONTDOOR_SHOW_EVENT: (
            "true shows the button that starts an event proposal on the front door and on /ask; "
            "false leaves it off both. /event still works"
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


# A click on a panel no live view owns (`docs/info/panels-orphaned-click-design.md`) — own block.
PANEL_EXPIRED_TEXT_KEY = "panel_expired_text"
PANEL_EXPIRED_TEXT = (
    "This panel has gone quiet — it timed out, or Black Bloc restarted since it was opened, so "
    "its buttons no longer reach anything. Run {command} again for a fresh one."
)

KEY_TYPES[PANEL_EXPIRED_TEXT_KEY] = "text"
KEY_HELP[PANEL_EXPIRED_TEXT_KEY] = (
    "what somebody is told when they press a button, pick from a menu or submit a form on a "
    "panel Black Bloc no longer holds — it timed out, or the bot restarted (every deploy is a "
    "restart) while it was open. `{command}` is filled in with the slash command that opened "
    "the panel when Discord says which, and with 'the command' when it does not"
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

# Posts — the style a Google Doc import lands in (owner, 2026-09-28: "Make sure it post in a
# format style box like welcome does"). The choices are posts.STYLES; a test pins the two equal.
POSTS_IMPORT_STYLE = "posts_import_style"
POSTS_IMPORT_STYLES = ("plain", "embed")
POSTS_IMPORT_STYLE_DEFAULT = "embed"
KEY_TYPES.update({POSTS_IMPORT_STYLE: "enum"})
KEY_CHOICES.update({POSTS_IMPORT_STYLE: POSTS_IMPORT_STYLES})
KEY_HELP.update(
    {
        POSTS_IMPORT_STYLE: (
            "the style a post takes when its words come from a Google Doc — on a new post made "
            "with Import a Google Doc, and on an existing post's draft when Import replaces its "
            "message. embed (the default) is the box Welcome and rules is drawn in and holds "
            "4096 characters; plain is an ordinary message of up to 2000. Staff can still change "
            "the style of any post afterwards"
        ),
    }
)

# Posts — the title an import with no title of its own gets (owner, 2026-09-28: "leave it
# untitled if no title is on the google doc and no title header is used in the doc").
POSTS_UNTITLED_TITLE = "posts_untitled_title"
POSTS_UNTITLED_TITLE_DEFAULT = "Untitled"
KEY_TYPES.update({POSTS_UNTITLED_TITLE: "text"})
KEY_HELP.update(
    {
        POSTS_UNTITLED_TITLE: (
            "the title a post made with Import a Google Doc gets when the doc has no title of its "
            "own and no title line or heading; blank restores Untitled. A second one is numbered "
            "Untitled-1, then Untitled-2. It can become the embed's title members see"
        ),
    }
)

# Posts — blocks (owner, 2026-09-27: "lets do blocks"). A block is something a post's message
# carries under its own words; each kind's name is what staff see in the Add a block list.
POSTS_BLOCK_FRONTDOOR_NAME = "posts_block_frontdoor_name"
POSTS_BLOCK_FRONTDOOR_NAME_DEFAULT = "Front door"
KEY_TYPES.update({POSTS_BLOCK_FRONTDOOR_NAME: "text"})
KEY_HELP.update(
    {
        POSTS_BLOCK_FRONTDOOR_NAME: (
            "what the front-door block is called in the Posts page's Add a block list, its Blocks "
            "section and the /posts card; blank restores Front door. Members never see it"
        ),
    }
)

# Temp voice lobby block (blocks-convert, 2026-09-28) — a second surface over temp voice, drawn
# by the temp voice cog; every word it posts is one of these. Filed under tempvoice by prefix.
TEMPVOICE_BLOCK_TITLE = "tempvoice_block_title"
TEMPVOICE_BLOCK_TEXT = "tempvoice_block_text"
TEMPVOICE_BLOCK_LOBBY_LABEL = "tempvoice_block_lobby_label"
TEMPVOICE_BLOCK_CONTROLS_LABEL = "tempvoice_block_controls_label"
TEMPVOICE_BLOCK_SHOW_CONTROLS = "tempvoice_block_show_controls"
POSTS_BLOCK_TEMPVOICE_NAME = "posts_block_tempvoice_name"
POSTS_BLOCK_TEMPVOICE_NAME_DEFAULT = "Temp voice lobby"
TEMPVOICE_BLOCK_DEFAULTS: dict[str, Any] = {
    TEMPVOICE_BLOCK_TITLE: "A voice channel of your own",
    TEMPVOICE_BLOCK_TEXT: (
        "Join a lobby below and Black Bloc makes you a voice channel of your own and moves you "
        "in. Its controls are posted in that channel's chat, and it goes away once everyone has "
        "left. Type /voice any time for the same controls."
    ),
    TEMPVOICE_BLOCK_LOBBY_LABEL: "🔊 {lobby}",
    TEMPVOICE_BLOCK_CONTROLS_LABEL: "My voice channel",
    TEMPVOICE_BLOCK_SHOW_CONTROLS: True,
    POSTS_BLOCK_TEMPVOICE_NAME: POSTS_BLOCK_TEMPVOICE_NAME_DEFAULT,
}
KEY_TYPES.update(
    {
        TEMPVOICE_BLOCK_TITLE: "text",
        TEMPVOICE_BLOCK_TEXT: "text",
        TEMPVOICE_BLOCK_LOBBY_LABEL: "text",
        TEMPVOICE_BLOCK_CONTROLS_LABEL: "text",
        TEMPVOICE_BLOCK_SHOW_CONTROLS: "bool",
        POSTS_BLOCK_TEMPVOICE_NAME: "text",
    }
)
KEY_HELP.update(
    {
        TEMPVOICE_BLOCK_TITLE: (
            "the heading on the temp voice lobby block, when a post carries it; blank restores "
            "the shipped wording"
        ),
        TEMPVOICE_BLOCK_TEXT: (
            "the line under that heading, explaining join-to-create; blank restores the shipped "
            "wording"
        ),
        TEMPVOICE_BLOCK_LOBBY_LABEL: (
            "what each lobby's button on the block says, at most 80 characters; {lobby} is the "
            "lobby's name. The button opens that lobby in Discord. "
            "Blank restores the speaker and the name"
        ),
        TEMPVOICE_BLOCK_CONTROLS_LABEL: (
            "what the block's button that opens the /voice panel says, at most 80 characters; "
            "blank restores the shipped wording"
        ),
        TEMPVOICE_BLOCK_SHOW_CONTROLS: (
            "true puts the button that opens the /voice panel on the block, beside the lobby "
            "buttons; false leaves only the lobbies. /voice itself always works"
        ),
        POSTS_BLOCK_TEMPVOICE_NAME: (
            "what the temp voice lobby block is called in the Posts page's Add a block list, its "
            "Blocks section and the /posts card; blank restores Temp voice lobby. Members never "
            "see it"
        ),
    }
)

# Button blocks (blocks-buttons, 2026-09-28) — four one-button blocks, each drawn and answered by
# its own feature's code; every word they post is one of these. Filed under each feature by prefix.
MARATHON_ROLE_ID = "marathon_role_id"
MARATHON_BLOCK_TITLE = "marathon_block_title"
MARATHON_BLOCK_TEXT = "marathon_block_text"
MARATHON_BLOCK_LABEL = "marathon_block_label"
MARATHON_BLOCK_ADDED_SAID = "marathon_block_added_said"
MARATHON_BLOCK_REMOVED_SAID = "marathon_block_removed_said"
MARATHON_BLOCK_UNSET_SAID = "marathon_block_unset_said"
PINGS_BLOCK_TITLE = "pings_block_title"
PINGS_BLOCK_TEXT = "pings_block_text"
PINGS_BLOCK_LABEL = "pings_block_label"
BIRTHDAY_BLOCK_TITLE = "birthday_block_title"
BIRTHDAY_BLOCK_TEXT = "birthday_block_text"
BIRTHDAY_BLOCK_LABEL = "birthday_block_label"
BIRTHDAY_BLOCK_SAVED_SAID = "birthday_block_saved_said"
BIRTHDAY_BLOCK_REFUSED_SAID = "birthday_block_refused_said"
BIRTHDAY_BLOCK_OFF_SAID = "birthday_block_off_said"
EVENTS_BLOCK_TITLE = "events_block_title"
EVENTS_BLOCK_TEXT = "events_block_text"
EVENTS_BLOCK_LABEL = "events_block_label"
POSTS_BLOCK_MARATHONROLE_NAME = "posts_block_marathonrole_name"
POSTS_BLOCK_MARATHONROLE_NAME_DEFAULT = "Marathon role"
POSTS_BLOCK_PINGSFOLLOW_NAME = "posts_block_pingsfollow_name"
POSTS_BLOCK_PINGSFOLLOW_NAME_DEFAULT = "Ping me when they go live"
POSTS_BLOCK_BIRTHDAY_NAME = "posts_block_birthday_name"
POSTS_BLOCK_BIRTHDAY_NAME_DEFAULT = "Set your birthday"
POSTS_BLOCK_PROPOSEEVENT_NAME = "posts_block_proposeevent_name"
POSTS_BLOCK_PROPOSEEVENT_NAME_DEFAULT = "Propose an event"
BUTTON_BLOCK_DEFAULTS: dict[str, Any] = {
    MARATHON_ROLE_ID: None,
    MARATHON_BLOCK_TITLE: "The Marathon role",
    MARATHON_BLOCK_TEXT: (
        "Here for the marathons? Press the button to take the Marathon role, and press it again "
        "any time to hand it back."
    ),
    MARATHON_BLOCK_LABEL: "Get or drop the Marathon role",
    MARATHON_BLOCK_ADDED_SAID: (
        "You have the **{role}** role now. Press the button again any time to hand it back."
    ),
    MARATHON_BLOCK_REMOVED_SAID: (
        "The **{role}** role is off you now. Press the button again any time to take it back."
    ),
    MARATHON_BLOCK_UNSET_SAID: (
        "Staff have not set up the Marathon role yet, so nothing was changed. Try again later, "
        "or ask an Auntie/Uncle."
    ),
    PINGS_BLOCK_TITLE: "Get pinged when someone goes live",
    PINGS_BLOCK_TEXT: (
        "Pick the streamers and channels you want a ping for when they go live. Nothing pings "
        "you until you choose it, and you can stop any time. /pings opens the same choices."
    ),
    PINGS_BLOCK_LABEL: "Choose my pings",
    BIRTHDAY_BLOCK_TITLE: "Your birthday",
    BIRTHDAY_BLOCK_TEXT: (
        "Tell Black Bloc your birthday and the server can celebrate you on the day. Change or "
        "remove it any time; /birthday opens the same choices."
    ),
    BIRTHDAY_BLOCK_LABEL: "Set my birthday",
    BIRTHDAY_BLOCK_SAVED_SAID: "{said} Press the button again, or use /birthday, to change it.",
    BIRTHDAY_BLOCK_REFUSED_SAID: "{said} Nothing was saved; press the button to try again.",
    BIRTHDAY_BLOCK_OFF_SAID: (
        "Birthdays are turned off in this server right now, so nothing was saved. Ask an "
        "Auntie/Uncle if you think they should be on."
    ),
    EVENTS_BLOCK_TITLE: "Propose an event",
    EVENTS_BLOCK_TEXT: (
        "Got an idea for a movie night, a game session or a watch party? Propose it here and "
        "staff take it from there. /event opens the same form."
    ),
    EVENTS_BLOCK_LABEL: "Propose an event",
    POSTS_BLOCK_MARATHONROLE_NAME: POSTS_BLOCK_MARATHONROLE_NAME_DEFAULT,
    POSTS_BLOCK_PINGSFOLLOW_NAME: POSTS_BLOCK_PINGSFOLLOW_NAME_DEFAULT,
    POSTS_BLOCK_BIRTHDAY_NAME: POSTS_BLOCK_BIRTHDAY_NAME_DEFAULT,
    POSTS_BLOCK_PROPOSEEVENT_NAME: POSTS_BLOCK_PROPOSEEVENT_NAME_DEFAULT,
}
BLOCK_HEADING_HELP = (
    "the heading on the {what} block, when a post carries it; blank restores the shipped wording"
)
BLOCK_TEXT_HELP = (
    "the line under that heading on the {what} block; blank restores the shipped wording"
)
BLOCK_LABEL_HELP = (
    "what the {what} block's button says, at most 80 characters; the button {does}. Blank "
    "restores the shipped wording"
)
BLOCK_NAME_HELP = (
    "what the {what} block is called in the Posts page's Add a block list, its Blocks section "
    "and the /posts card; blank restores {name}. Members never see it"
)
KEY_TYPES.update(
    {
        MARATHON_ROLE_ID: "role",
        MARATHON_BLOCK_TITLE: "text",
        MARATHON_BLOCK_TEXT: "text",
        MARATHON_BLOCK_LABEL: "text",
        MARATHON_BLOCK_ADDED_SAID: "text",
        MARATHON_BLOCK_REMOVED_SAID: "text",
        MARATHON_BLOCK_UNSET_SAID: "text",
        PINGS_BLOCK_TITLE: "text",
        PINGS_BLOCK_TEXT: "text",
        PINGS_BLOCK_LABEL: "text",
        BIRTHDAY_BLOCK_TITLE: "text",
        BIRTHDAY_BLOCK_TEXT: "text",
        BIRTHDAY_BLOCK_LABEL: "text",
        BIRTHDAY_BLOCK_SAVED_SAID: "text",
        BIRTHDAY_BLOCK_REFUSED_SAID: "text",
        BIRTHDAY_BLOCK_OFF_SAID: "text",
        EVENTS_BLOCK_TITLE: "text",
        EVENTS_BLOCK_TEXT: "text",
        EVENTS_BLOCK_LABEL: "text",
        POSTS_BLOCK_MARATHONROLE_NAME: "text",
        POSTS_BLOCK_PINGSFOLLOW_NAME: "text",
        POSTS_BLOCK_BIRTHDAY_NAME: "text",
        POSTS_BLOCK_PROPOSEEVENT_NAME: "text",
    }
)
KEY_HELP.update(
    {
        MARATHON_ROLE_ID: (
            "the Marathon role: the one the Marathon role block hands to a member who presses "
            "its button and takes back on the next press. Blank until staff pick it, and the "
            "button then says staff have not set it up yet. A role with staff permissions is "
            "never handed out. Picking it pings nobody"
        ),
        MARATHON_BLOCK_TITLE: BLOCK_HEADING_HELP.format(what="Marathon role"),
        MARATHON_BLOCK_TEXT: BLOCK_TEXT_HELP.format(what="Marathon role"),
        MARATHON_BLOCK_LABEL: BLOCK_LABEL_HELP.format(
            what="Marathon role", does="gives the member the Marathon role, or takes it back"
        ),
        MARATHON_BLOCK_ADDED_SAID: (
            "what a member is told, privately, once the Marathon role block's button gave them "
            "the role; {role} is its name"
        ),
        MARATHON_BLOCK_REMOVED_SAID: (
            "what a member is told, privately, once the Marathon role block's button took the "
            "role back; {role} is its name"
        ),
        MARATHON_BLOCK_UNSET_SAID: (
            "what a member is told, privately, when they press the Marathon role block's button "
            "and no usable Marathon role is picked (marathon_role_id)"
        ),
        PINGS_BLOCK_TITLE: BLOCK_HEADING_HELP.format(what="ping me when they go live"),
        PINGS_BLOCK_TEXT: BLOCK_TEXT_HELP.format(what="ping me when they go live"),
        PINGS_BLOCK_LABEL: BLOCK_LABEL_HELP.format(
            what="ping me when they go live", does="opens the same /pings panel and its picker"
        ),
        BIRTHDAY_BLOCK_TITLE: BLOCK_HEADING_HELP.format(what="set your birthday"),
        BIRTHDAY_BLOCK_TEXT: BLOCK_TEXT_HELP.format(what="set your birthday"),
        BIRTHDAY_BLOCK_LABEL: BLOCK_LABEL_HELP.format(
            what="set your birthday",
            does="asks for the date straight away, in the same form /birthday's Set my birthday "
            "opens",
        ),
        BIRTHDAY_BLOCK_SAVED_SAID: (
            "what a member is told, privately, once the birthday block's form saved their date; "
            "{said} is the same sentence /birthday answers with"
        ),
        BIRTHDAY_BLOCK_REFUSED_SAID: (
            "what a member is told, privately, when the birthday block's form could not use the "
            "date they typed; {said} is the same refusal /birthday answers with"
        ),
        BIRTHDAY_BLOCK_OFF_SAID: (
            "what a member is told, privately, when they press the birthday block's button or "
            "send its form while birthdays are off (birthday_mode); nothing is saved"
        ),
        EVENTS_BLOCK_TITLE: BLOCK_HEADING_HELP.format(what="propose an event"),
        EVENTS_BLOCK_TEXT: BLOCK_TEXT_HELP.format(what="propose an event"),
        EVENTS_BLOCK_LABEL: BLOCK_LABEL_HELP.format(
            what="propose an event",
            does="opens the same private proposal card the front door opens",
        ),
        POSTS_BLOCK_MARATHONROLE_NAME: BLOCK_NAME_HELP.format(
            what="Marathon role", name=POSTS_BLOCK_MARATHONROLE_NAME_DEFAULT
        ),
        POSTS_BLOCK_PINGSFOLLOW_NAME: BLOCK_NAME_HELP.format(
            what="ping me when they go live", name=POSTS_BLOCK_PINGSFOLLOW_NAME_DEFAULT
        ),
        POSTS_BLOCK_BIRTHDAY_NAME: BLOCK_NAME_HELP.format(
            what="set your birthday", name=POSTS_BLOCK_BIRTHDAY_NAME_DEFAULT
        ),
        POSTS_BLOCK_PROPOSEEVENT_NAME: BLOCK_NAME_HELP.format(
            what="propose an event", name=POSTS_BLOCK_PROPOSEEVENT_NAME_DEFAULT
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
            "as well, so pick a channel only the people reviewing can see. A feature's own "
            "…_shadow_channel_id wins over this"
        ),
        REHEARSAL_NOTE: (
            "the line the front door and the ticket button carry at the top of their rehearsal "
            "copy; {channel} is replaced with the channel the real one is aimed at. Blank "
            "leaves the copy with no note at all"
        ),
    }
)


# A rehearsal home per feature: blank follows shadow_channel_id, set wins over it.
SHADOW_HOME_WORDS = {
    "frontdoor": "the front door's copy and the Open a ticket button it replaces",
    "posts": "posts such as the welcome post and the rules",
    "golive": "spotlight announcements",
    "marathon": "the marathon board, reminders, shoutouts and staff notices",
    "marathon_public": "a marathon's public highlights of BaF runners and its public reminders",
    "poll": "polls and their results",
    "birthday": "birthday wishes",
    "sticky": "sticky messages",
}
SHADOW_HOME_KEYS = {feature: shadow_feature_key(feature) for feature in SHADOW_HOME_WORDS}
KEY_TYPES.update({key: "channel" for key in SHADOW_HOME_KEYS.values()})
KEY_HELP.update(
    {
        SHADOW_HOME_KEYS[feature]: (
            f"where this feature's rehearsals land while it is in shadow ({words}); blank "
            "means shadow_channel_id. Set it to send only this feature's rehearsals somewhere "
            "else"
        )
        for feature, words in SHADOW_HOME_WORDS.items()
    }
)


# Auto-link: a presence go-live is the member saying which channel is theirs, out loud.
GOLIVE_AUTOLINK_PRESENCE_KEY = "golive_autolink_presence"
GOLIVE_AUTOLINK_PRESENCE_DEFAULT = True
KEY_TYPES.update({GOLIVE_AUTOLINK_PRESENCE_KEY: "bool"})
KEY_HELP.update(
    {
        GOLIVE_AUTOLINK_PRESENCE_KEY: (
            "whether being announced also remembers somebody's channel. on — the default — "
            "links a member to the Twitch or YouTube channel their Discord status names the "
            "first time they are announced from it, so nobody has to type it in; off leaves "
            "linking to the person or to staff"
        ),
    }
)


# A video address names a channel only if YouTube's own page is read, so this ships off.
GOLIVE_AUTOLINK_VIDEO_KEY = "golive_autolink_youtube_video"
GOLIVE_AUTOLINK_VIDEO_DEFAULT = False
KEY_TYPES.update({GOLIVE_AUTOLINK_VIDEO_KEY: "bool"})
KEY_HELP.update(
    {
        GOLIVE_AUTOLINK_VIDEO_KEY: (
            "whether a Discord status carrying a YouTube VIDEO address is read to find whose "
            "channel the video is on. Off by default, because it reads YouTube's page, which "
            "can change, and the video playing is not always the streamer's own; on links the "
            "person to the channel behind the video"
        ),
    }
)


# The "X pinned a message" notice under a pin Black Bloc made itself.
QUIET_BOT_PINS = "quiet_bot_pins"
QUIET_BOT_PINS_DEFAULT = True
KEY_TYPES.update({QUIET_BOT_PINS: "bool"})
KEY_HELP.update(
    {
        QUIET_BOT_PINS: (
            "whether Black Bloc deletes the 'pinned a message' notice Discord posts under a pin "
            "Black Bloc made itself (marathon boards, runner posts, spotlights, posts). on — the "
            "default — keeps channels tidy; off leaves the notice. A pin a person makes is never "
            "touched. It needs Manage Messages in the channel"
        ),
    }
)


# Sticky messages: one staff-set note per channel that is kept at the bottom.
STICKY_MODE = "sticky_mode"
STICKY_AFTER_MESSAGES = "sticky_after_messages"
STICKY_MIN_SECONDS = "sticky_min_seconds"
STICKY_SILENT = "sticky_silent"
STICKY_PANEL_MINUTES = "sticky_panel_minutes"
STICKY_MODES = ("off", "shadow", "on")
STICKY_MODE_DEFAULT = "shadow"
STICKY_AFTER_MESSAGES_DEFAULT = 5
STICKY_AFTER_MESSAGES_MIN = 1
STICKY_AFTER_MESSAGES_MAX = 100
STICKY_MIN_SECONDS_DEFAULT = 30
STICKY_MIN_SECONDS_MIN = 5
STICKY_MIN_SECONDS_MAX = 3600
STICKY_SILENT_DEFAULT = True
STICKY_PANEL_MINUTES_DEFAULT = 10
STICKY_DEFAULTS: dict[str, Any] = {
    STICKY_MODE: STICKY_MODE_DEFAULT,
    STICKY_AFTER_MESSAGES: STICKY_AFTER_MESSAGES_DEFAULT,
    STICKY_MIN_SECONDS: STICKY_MIN_SECONDS_DEFAULT,
    STICKY_SILENT: STICKY_SILENT_DEFAULT,
    STICKY_PANEL_MINUTES: STICKY_PANEL_MINUTES_DEFAULT,
}
KEY_TYPES.update(
    {
        STICKY_MODE: "enum",
        STICKY_AFTER_MESSAGES: "int",
        STICKY_MIN_SECONDS: "int",
        STICKY_SILENT: "bool",
        STICKY_PANEL_MINUTES: "int",
    }
)
KEY_CHOICES[STICKY_MODE] = STICKY_MODES
KEY_MIN[STICKY_AFTER_MESSAGES] = STICKY_AFTER_MESSAGES_MIN
KEY_MAX[STICKY_AFTER_MESSAGES] = STICKY_AFTER_MESSAGES_MAX
KEY_MIN[STICKY_MIN_SECONDS] = STICKY_MIN_SECONDS_MIN
KEY_MAX[STICKY_MIN_SECONDS] = STICKY_MIN_SECONDS_MAX
KEY_MIN[STICKY_PANEL_MINUTES] = 1
KEY_MIN_REASON[STICKY_AFTER_MESSAGES] = (
    "A sticky message has to wait for at least {limit} new message before it moves."
)
KEY_MAX_REASON[STICKY_AFTER_MESSAGES] = (
    "Past {limit} messages a sticky message is so far up the channel that nobody reads it."
)
KEY_MIN_REASON[STICKY_MIN_SECONDS] = (
    "Under {limit} seconds a busy channel would have Black Bloc deleting and posting faster "
    "than Discord allows."
)
KEY_MAX_REASON[STICKY_MIN_SECONDS] = (
    "{limit} seconds is an hour; longer than that and the sticky message is not at the bottom "
    "when people need it."
)
KEY_HELP.update(
    {
        STICKY_MODE: (
            "off, shadow or on. shadow — the default — posts nothing in the real channel: each "
            "copy goes to the rehearsal home with a line naming where it would have gone. on "
            "keeps each sticky message at the bottom of its own channel. off takes every copy "
            "down and keeps the words"
        ),
        STICKY_AFTER_MESSAGES: (
            "how many new messages from people it takes before a sticky message is posted "
            "again at the bottom; 5 by default, 1 to 100. Black Bloc's own messages and other "
            "bots' do not count"
        ),
        STICKY_MIN_SECONDS: (
            "the shortest gap, in seconds, between two copies of one sticky message; 30 by "
            "default, 5 to 3600. Both this and sticky_after_messages have to be met, so a busy "
            "channel never gets a copy per message"
        ),
        STICKY_SILENT: (
            "whether a sticky message is posted silently, so moving it to the bottom never "
            "lights up anybody's notifications. on by default"
        ),
        STICKY_PANEL_MINUTES: (
            "minutes the /sticky panel stays live before its buttons disable themselves; 10 by "
            "default. The 'this panel has gone quiet' footer can only be written while "
            "Discord's 15-minute interaction window is still open, so 15 or more means the "
            "buttons simply stop working with no footer to explain it"
        ),
    }
)
STICKY_KEYS = (*STICKY_DEFAULTS, SHADOW_HOME_KEYS["sticky"])


# Structure backup (docs/info/structure-backup-design.md) — its own block so parallel branches
# merge textually. Every key sits under `core`: `structure_` would be a 26th setting group.
STRUCTURE_BACKUP_MODE = "structure_backup_mode"
STRUCTURE_BACKUP_HOUR = "structure_backup_hour"
STRUCTURE_BACKUP_KEEP = "structure_backup_keep"
STRUCTURE_BACKUP_NOTIFY = "structure_backup_notify"
STRUCTURE_BACKUP_CHANNEL = "structure_backup_channel_id"
STRUCTURE_BACKUP_SHADOW_CHANNEL = shadow_feature_key(STRUCTURE_FEATURE)
STRUCTURE_BACKUP_ROLE = STRUCTURE_ROLE_KEY
STRUCTURE_BACKUP_NOTICE_LINES = "structure_backup_notice_lines"
STRUCTURE_BACKUP_PANEL_MINUTES = "structure_backup_panel_minutes"
STRUCTURE_BACKUP_NUMBERS: dict[str, tuple[int, int, int]] = {
    STRUCTURE_BACKUP_HOUR: (4, 0, 23),
    STRUCTURE_BACKUP_KEEP: (60, 1, 365),
    STRUCTURE_BACKUP_NOTICE_LINES: (15, 1, 40),
    STRUCTURE_BACKUP_PANEL_MINUTES: (10, 1, 14),
}
STRUCTURE_BACKUP_WORDS: dict[str, tuple[str, tuple[str, ...], str]] = {
    "structure_backup_notice_title": (
        "Server structure changed",
        (),
        "the heading of the notice staff get when a daily structure snapshot differs from the "
        "one before it",
    ),
    "structure_backup_notice_text": (
        "{n} change(s) since the snapshot of {when}.",
        ("n", "when"),
        "the first line of the structure-changed notice; {n} is how many changes and {when} "
        "is when the snapshot before it was taken",
    ),
    "structure_backup_notice_more": (
        "…and {n} more — the Structure page lists every one.",
        ("n",),
        "the last line of the structure-changed notice when it holds more changes than "
        "structure_backup_notice_lines lets it list; {n} is how many were left off",
    ),
    "structure_backup_notice_label": (
        "Notice",
        (),
        "what the /structure panel calls the line that says where the structure-changed "
        "notice goes",
    ),
    "structure_backup_notice_nowhere": (
        "Nowhere — {setting} is blank.",
        ("setting",),
        "what the /structure panel says when the structure-changed notice has no channel to "
        "go to; {setting} is the key that would give it one",
    ),
    "structure_backup_notice_off": (
        "Off — structure_backup_notify is false.",
        (),
        "what the /structure panel says about the notice while structure_backup_notify is "
        "false",
    ),
    "structure_backup_panel_title": (
        "Server structure",
        (),
        "the heading of the /structure panel",
    ),
    "structure_backup_panel_footer": (
        "This panel timed out — run /structure again for a fresh one.",
        (),
        "the footer the /structure panel gains when its buttons stop working",
    ),
    "structure_backup_mode_label": (
        "Mode",
        (),
        "what the /structure panel calls the line that says off, shadow or on",
    ),
    "structure_backup_latest_label": (
        "Latest snapshot",
        (),
        "what the /structure panel calls the newest stored snapshot",
    ),
    "structure_backup_latest_line": (
        "#{id} · {when} · {roles} roles · {categories} categories · {channels} channels · "
        "{overwrites} permission overwrites",
        ("id", "when", "roles", "categories", "channels", "overwrites"),
        "the line that describes one snapshot on the /structure panel: its number, when it "
        "was taken and what it counted",
    ),
    "structure_backup_none_yet": (
        "No snapshot has been taken yet.",
        (),
        "what the /structure panel says before the first snapshot exists",
    ),
    "structure_backup_look_label": (
        "Last look",
        (),
        "what the /structure panel calls the most recent time the structure was read",
    ),
    "structure_backup_look_saved": (
        "{when} — a new snapshot was stored.",
        ("when",),
        "the last-look line when the structure had changed and a snapshot was stored",
    ),
    "structure_backup_look_unchanged": (
        "{when} — nothing had changed.",
        ("when",),
        "the last-look line when the structure matched the latest snapshot and no copy was "
        "stored",
    ),
    "structure_backup_look_failed": (
        "{when} — it failed: {reason}",
        ("when", "reason"),
        "the last-look line when the structure could not be read; {reason} says why",
    ),
    "structure_backup_take_label": (
        "Take one now",
        (),
        "what the button that takes a structure snapshot straight away is called",
    ),
    "structure_backup_changes_label": (
        "What changed",
        (),
        "what the button that compares the latest snapshot with the server as it is now is "
        "called, and the heading of the list it answers with",
    ),
    "structure_backup_site_label": (
        "Open the Structure page",
        (),
        "what the link from the /structure panel to the Structure page is called",
    ),
    "structure_backup_saved_said": (
        "Snapshot #{id} saved.",
        ("id",),
        "what staff are told when Take one now stored a new snapshot",
    ),
    "structure_backup_unchanged_said": (
        "Nothing has changed since snapshot #{id}, so no second copy was stored.",
        ("id",),
        "what staff are told when Take one now found the structure unchanged",
    ),
    "structure_backup_failed_said": (
        "No snapshot was taken — {reason}",
        ("reason",),
        "what staff are told when a structure snapshot could not be taken; {reason} says why "
        "and what to do",
    ),
    "structure_backup_off_said": (
        "Structure backup is **off**, so nothing was captured. Set structure_backup_mode to "
        "shadow or on — in /settings or on the Settings page — and press it again.",
        (),
        "what staff are told when they ask for a snapshot while structure_backup_mode is off",
    ),
    "structure_backup_no_changes_said": (
        "Nothing has changed since the latest snapshot.",
        (),
        "what What changed answers when the server matches the latest snapshot",
    ),
}
STRUCTURE_BACKUP_DEFAULTS: dict[str, Any] = {
    STRUCTURE_BACKUP_MODE: STRUCTURE_MODE_DEFAULT,
    STRUCTURE_BACKUP_NOTIFY: True,
    **{key: default for key, (default, _, _) in STRUCTURE_BACKUP_NUMBERS.items()},
    **{key: default for key, (default, _, _) in STRUCTURE_BACKUP_WORDS.items()},
}
STRUCTURE_BACKUP_FIELDS: dict[str, tuple[str, ...]] = {
    key: fields for key, (_, fields, _) in STRUCTURE_BACKUP_WORDS.items()
}
STRUCTURE_LABEL = "label"
STRUCTURE_HINT = "hint"
STRUCTURE_HEADING = "heading"
STRUCTURE_LINE = "line"
STRUCTURE_ANSWER = "answer"
STRUCTURE_EMBED_CHARS = 6000
STRUCTURE_SLOTS: dict[str, tuple[int, str]] = {
    STRUCTURE_LABEL: (80, "a button's label"),
    STRUCTURE_HINT: (150, "a picker's hint"),
    STRUCTURE_HEADING: (256, "a heading"),
    STRUCTURE_LINE: (1024, "one block of a card"),
    STRUCTURE_ANSWER: (4096, "a card's main text"),
}
STRUCTURE_BACKUP_SLOT: dict[str, str] = {
    **{key: STRUCTURE_LINE for key in STRUCTURE_BACKUP_FIELDS},
    "structure_backup_take_label": STRUCTURE_LABEL,
    "structure_backup_changes_label": STRUCTURE_LABEL,
    "structure_backup_site_label": STRUCTURE_LABEL,
    "structure_backup_mode_label": STRUCTURE_HINT,
    "structure_backup_notice_title": STRUCTURE_HEADING,
    "structure_backup_notice_label": STRUCTURE_HEADING,
    "structure_backup_panel_title": STRUCTURE_HEADING,
    "structure_backup_panel_footer": STRUCTURE_HEADING,
    "structure_backup_latest_label": STRUCTURE_HEADING,
    "structure_backup_look_label": STRUCTURE_HEADING,
    "structure_backup_saved_said": STRUCTURE_ANSWER,
    "structure_backup_unchanged_said": STRUCTURE_ANSWER,
    "structure_backup_failed_said": STRUCTURE_ANSWER,
    "structure_backup_off_said": STRUCTURE_ANSWER,
}
STRUCTURE_BACKUP_LIMITS: dict[str, int] = {
    key: STRUCTURE_SLOTS[slot][0] for key, slot in STRUCTURE_BACKUP_SLOT.items()
}
STRUCTURE_TOO_LONG = (
    "That is {length} characters and {what} holds {limit} on Discord, so nothing was changed. "
    "Take {over} out and save it again."
)


def checked_structure_words(key: str) -> Any:
    """Known placeholders only, and no longer than the place Discord shows it in."""
    fields = STRUCTURE_BACKUP_FIELDS[key]
    limit, what = STRUCTURE_SLOTS[STRUCTURE_BACKUP_SLOT[key]]

    def check(given: Any) -> str:
        text = _checked_words(given, fields)
        if len(text) > limit:
            raise SettingError(
                STRUCTURE_TOO_LONG.format(
                    length=len(text), what=what, limit=limit, over=len(text) - limit
                )
            )
        return text

    return check


STRUCTURE_BACKUP_KEYS: tuple[str, ...] = (
    STRUCTURE_BACKUP_MODE,
    STRUCTURE_BACKUP_HOUR,
    STRUCTURE_BACKUP_KEEP,
    STRUCTURE_BACKUP_NOTIFY,
    STRUCTURE_BACKUP_CHANNEL,
    STRUCTURE_BACKUP_SHADOW_CHANNEL,
    STRUCTURE_BACKUP_ROLE,
    STRUCTURE_BACKUP_NOTICE_LINES,
    STRUCTURE_BACKUP_PANEL_MINUTES,
    *STRUCTURE_BACKUP_WORDS,
)
KEY_TYPES.update(
    {
        STRUCTURE_BACKUP_MODE: "enum",
        STRUCTURE_BACKUP_NOTIFY: "bool",
        STRUCTURE_BACKUP_CHANNEL: "channel",
        STRUCTURE_BACKUP_SHADOW_CHANNEL: "channel",
        STRUCTURE_BACKUP_ROLE: "role",
        **{key: "int" for key in STRUCTURE_BACKUP_NUMBERS},
        **{key: "text" for key in STRUCTURE_BACKUP_FIELDS},
    }
)
KEY_CHOICES[STRUCTURE_BACKUP_MODE] = STRUCTURE_MODES
KEY_MIN.update({key: low for key, (_, low, _) in STRUCTURE_BACKUP_NUMBERS.items() if low})
KEY_MAX.update({key: high for key, (_, _, high) in STRUCTURE_BACKUP_NUMBERS.items()})
KEY_HELP.update(
    {
        STRUCTURE_BACKUP_MODE: (
            "off, shadow or on. off takes no structure snapshot at all; shadow — the default — "
            "takes the daily snapshot silently and sends the structure-changed notice to "
            "structure_backup_shadow_channel_id; on sends that notice to "
            "structure_backup_channel_id. Either one blank means no notice is posted. A "
            "snapshot is a copy of roles, channels and permissions only: never messages, never "
            "members"
        ),
        STRUCTURE_BACKUP_HOUR: (
            "the hour of the day, 0 to 23 in default_timezone, at or after which the daily "
            "structure snapshot is taken; 4 by default. A bot that was down at that hour takes "
            "it when it comes back"
        ),
        STRUCTURE_BACKUP_KEEP: (
            "how many structure snapshots are kept; 60 by default. The oldest beyond that are "
            "deleted each time a new one is stored, except the one the next notice starts "
            "from. A day with no change stores nothing, so 60 is 60 distinct structures, not "
            "60 days"
        ),
        STRUCTURE_BACKUP_NOTIFY: (
            "true — the default — posts a notice when the daily look finds the structure "
            "changed since the last notice, snapshots taken by hand included; false takes the "
            "snapshot and says nothing"
        ),
        STRUCTURE_BACKUP_CHANNEL: (
            "the only place the structure-changed notice goes while structure_backup_mode is "
            "on. Blank means no notice is posted — it never falls back to the staff channel, "
            "because the notice names private channels. Only the server's leads can change this"
        ),
        STRUCTURE_BACKUP_SHADOW_CHANNEL: (
            "the only place the structure-changed notice goes while structure_backup_mode is "
            "shadow. Blank means no notice is posted — it never falls back to shadow_channel_id "
            "or the log channel, because the notice names private channels. Only the server's "
            "leads can change this"
        ),
        STRUCTURE_BACKUP_ROLE: (
            "the role whose holders may open /structure and the Structure page, beside the "
            "server owner and anyone with Discord's Administrator permission. Blank means the "
            "owner and administrators only. Only the server's leads can change this"
        ),
        STRUCTURE_BACKUP_NOTICE_LINES: (
            "how many changes the structure-changed notice and the /structure panel list "
            "before they say how many more there are; 15 by default"
        ),
        STRUCTURE_BACKUP_PANEL_MINUTES: (
            "minutes the /structure panel stays live before its buttons disable themselves; "
            "10 by default"
        ),
        **{key: said for key, (_, _, said) in STRUCTURE_BACKUP_WORDS.items()},
    }
)

# The personal best feed (docs/info/pb-feed-design.md) — its own block so parallel branches
# merge textually. Every key sits under `core`: `pb_` would be a 26th setting group.
PB_FEED_FEATURE = "pb_feed"
PB_FEED_MODES = ("off", "shadow", "on")
PB_FEED_MODE = "pb_feed_mode"
PB_FEED_CHANNEL = "pb_feed_channel_id"
PB_FEED_SHADOW_CHANNEL = shadow_feature_key(PB_FEED_FEATURE)
PB_FEED_PING_ROLE = "pb_feed_ping_role_id"
PB_FEED_AUTO_MATCH = "pb_feed_auto_match"
PB_FEED_INTERVAL = "pb_feed_interval_minutes"
PB_FEED_CYCLE_REQUESTS = "pb_feed_cycle_requests"
PB_FEED_REMATCH_DAYS = "pb_feed_rematch_days"
PB_FEED_MAX_AGE_DAYS = "pb_feed_max_age_days"
PB_FEED_MAX_POSTS = "pb_feed_max_posts"
PB_FEED_PANEL_MINUTES = "pb_feed_panel_minutes"
PB_FEED_NUMBERS: dict[str, tuple[int, int, int]] = {
    PB_FEED_INTERVAL: (60, 15, 1440),
    PB_FEED_CYCLE_REQUESTS: (400, 1, 600),
    PB_FEED_REMATCH_DAYS: (7, 1, 90),
    PB_FEED_MAX_AGE_DAYS: (7, 1, 60),
    PB_FEED_MAX_POSTS: (5, 1, 20),
    PB_FEED_PANEL_MINUTES: (10, 1, 14),
}
PB_FEED_POST_FIELDS = (
    "member",
    "name",
    "runner",
    "game",
    "category",
    "time",
    "place",
    "place_line",
    "link",
)
PB_FEED_WORDS: dict[str, tuple[str, tuple[str, ...], str]] = {
    "pb_feed_post_title": (
        "New personal best",
        PB_FEED_POST_FIELDS,
        "the heading of a personal best post",
    ),
    "pb_feed_post_text": (
        "**{name}** ran **{game}** — {category} in **{time}**{place_line}.",
        PB_FEED_POST_FIELDS,
        "the body of a personal best post. {name} is the member's server display name (their "
        "speedrun.com name once they have left), {runner} their speedrun.com name, {member} an "
        "@ of the member that Discord may show as a raw id inside a post like this one, so use "
        "{name} to name them; {category} carries the level and sub-category where the run has "
        "them, {place_line} is pb_feed_place_text or nothing when speedrun.com gave no place, "
        "{link} is the run",
    ),
    "pb_feed_post_author": (
        "{name}",
        ("name", "runner"),
        "the line above a personal best post, beside the member's avatar. {name} is their "
        "server display name (their speedrun.com name once they have left), {runner} their "
        "speedrun.com name",
    ),
    "pb_feed_place_text": (
        "— #{place} on the leaderboard",
        ("place",),
        "what {place_line} becomes in a personal best post when speedrun.com gives the run's "
        "place, after a space; {place} is the number",
    ),
    "pb_feed_link_label": (
        "Watch the run",
        (),
        "the label of the link button under a personal best post",
    ),
    "pb_feed_no_channel_words": (
        "nowhere yet — pb_feed_channel_id is blank",
        (),
        "what the rehearsal note names as the real channel while pb_feed_channel_id is blank",
    ),
    "pb_feed_panel_title": (
        "Personal bests",
        (),
        "the heading of the /pb panel",
    ),
    "pb_feed_panel_footer": (
        "This panel has gone quiet — run /pb again",
        (),
        "the footer the /pb panel gets when its buttons have timed out",
    ),
    "pb_feed_you_matched": (
        "**speedrun.com** — [{runner}]({link}), found from twitch.tv/{login}.",
        ("runner", "link", "login"),
        "what /pb tells a member Black Bloc matched from their Twitch link",
    ),
    "pb_feed_you_set": (
        "**speedrun.com** — [{runner}]({link}), set by staff.",
        ("runner", "link"),
        "what /pb tells a member whose speedrun.com account staff set by hand",
    ),
    "pb_feed_posting_on": (
        "A personal best is posted once speedrun.com has verified it.",
        (),
        "what /pb adds for a matched member while pb_feed_mode is on",
    ),
    "pb_feed_posting_shadow": (
        "Staff are still trying this out: a new personal best is not posted in the server's "
        "personal best channel yet, only copied to where staff rehearse.",
        (),
        "what /pb adds for a matched member while pb_feed_mode is shadow, in place of "
        "pb_feed_posting_on",
    ),
    "pb_feed_posting_off": (
        "The personal best feed is switched off, so nothing is looked at and nothing is posted.",
        (),
        "what /pb adds for a matched member while pb_feed_mode is off, in place of "
        "pb_feed_posting_on",
    ),
    "pb_feed_you_none": (
        "No speedrun.com account lists twitch.tv/{login} as its Twitch channel. Add your Twitch "
        "channel to your speedrun.com profile and Black Bloc finds it within {days} day(s), or "
        "ask staff to set it.",
        ("login", "days"),
        "what /pb tells a member whose Twitch login matched no speedrun.com account",
    ),
    "pb_feed_you_waiting": (
        "Black Bloc has not looked for your speedrun.com account yet. It looks for a few "
        "members a minute.",
        (),
        "what /pb tells a linked member Black Bloc has not looked up yet",
    ),
    "pb_feed_you_unlinked": (
        "You have not linked a Twitch channel, so Black Bloc cannot find your speedrun.com "
        "account. Link one with /golive, or ask staff to set it.",
        (),
        "what /pb tells a member with no Twitch link and no match",
    ),
    "pb_feed_you_opted_out": (
        "You asked Black Bloc not to post your personal bests, so it does not look.",
        (),
        "what /pb tells a member who opted out",
    ),
    "pb_feed_you_blocked": (
        "Staff have turned personal best posts off for you. Ask staff if that should change.",
        (),
        "what /pb tells a member staff have blocked from the personal best feed",
    ),
    "pb_feed_opt_out_label": (
        "Do not post my personal bests",
        (),
        "the button a member presses on /pb to opt out",
    ),
    "pb_feed_opt_in_label": (
        "Post my personal bests",
        (),
        "the button a member presses on /pb to opt back in",
    ),
    "pb_feed_opted_out_said": (
        "Done — Black Bloc will not post your personal bests and has stopped looking.",
        (),
        "what a member is told after opting out of the personal best feed",
    ),
    "pb_feed_opted_in_said": (
        "Done — you are back in the personal best feed. Runs verified before now are never "
        "posted.",
        (),
        "what a member is told after opting back in to the personal best feed",
    ),
    "pb_feed_set_said": (
        "{member} is now matched to **{runner}** on speedrun.com. Their existing personal "
        "bests are recorded at the next look and not posted.",
        ("member", "runner"),
        "what staff are told after setting a member's speedrun.com account by hand",
    ),
    "pb_feed_unmatched_said": (
        "{member} is no longer matched. Black Bloc may find a match from their Twitch link "
        "again; press Block to stop that.",
        ("member",),
        "what staff are told after unmatching a member from the personal best feed",
    ),
    "pb_feed_blocked_said": (
        "{member} is blocked: no match is looked for and nothing of theirs is posted until "
        "staff unblock them or set an account by hand.",
        ("member",),
        "what staff are told after blocking a member from the personal best feed",
    ),
    "pb_feed_unblocked_said": (
        "{member} is back in the personal best feed. Runs verified before now are not posted.",
        ("member",),
        "what staff are told after unblocking a member, or clearing their opt-out",
    ),
    "pb_feed_unblocked_opted_out_said": (
        "{member} is unblocked. They had asked not to have personal bests posted, and that "
        "still stands: only they, or staff pressing Clear the opt-out, can end it.",
        ("member",),
        "what staff are told after unblocking a member who had opted out before the block",
    ),
    "pb_feed_no_runner_said": (
        "speedrun.com has no single account named exactly **{given}**, so nothing was changed. "
        "Copy the name from the end of their speedrun.com profile address and try again.",
        ("given",),
        "what staff are told when the speedrun.com name they typed matches no account",
    ),
    "pb_feed_taken_said": (
        "**{runner}** on speedrun.com is already matched to {holder}, so nothing was changed. "
        "Unmatch them first if this is the right person.",
        ("runner", "holder"),
        "what staff are told when the speedrun.com account is already another member's",
    ),
    "pb_feed_not_now_said": (
        "{member} asked not to have personal bests posted, so nothing was changed. Clear the "
        "opt-out first if staff have decided otherwise.",
        ("member",),
        "what staff are told when they act on a member who opted out",
    ),
    "pb_feed_nothing_to_do_said": (
        "{member} has nothing to change there, so nothing was done.",
        ("member",),
        "what staff are told when a personal best move does not apply to that member",
    ),
    "pb_feed_looked_said": (
        "Looked at **{runner}** — {found} new personal best(s), {seen} on record.",
        ("runner", "found", "seen"),
        "what staff are told after Look now on a matched member",
    ),
    "pb_feed_failed_said": (
        "Nothing was changed — {reason}",
        ("reason",),
        "what staff are told when speedrun.com could not be read; {reason} says why and what "
        "to do",
    ),
    "pb_feed_off_said": (
        "The personal best feed is **off**, so Black Bloc did not ask speedrun.com anything. "
        "Set pb_feed_mode to shadow or on — in /settings or on the Settings page — and try "
        "again.",
        (),
        "what staff are told when they ask for a look, or set an account by hand, while "
        "pb_feed_mode is off",
    ),
    "pb_feed_post_again_label": (
        "Post again",
        (),
        "the button staff press on the Personal bests page to send a stored personal best post "
        "again",
    ),
    "pb_feed_post_again_pick": (
        "Post one again…",
        (),
        "the placeholder of the list of recent personal best posts staff pick from on /pb to send "
        "one again",
    ),
    "pb_feed_posted_again_said": (
        "Posted {member}’s **{game}** personal best again in {channel}.",
        ("member", "game", "channel"),
        "what staff are told after Post again while pb_feed_mode is on; {channel} is where it went",
    ),
    "pb_feed_rehearsed_again_said": (
        "Rehearsed {member}’s **{game}** personal best again in {channel}.",
        ("member", "game", "channel"),
        "what staff are told after Post again while pb_feed_mode is shadow; {channel} is the "
        "rehearsal home it went to",
    ),
    "pb_feed_again_failed_said": (
        "Nothing was posted — {reason}",
        ("reason",),
        "what staff are told when Post again could not send the post; {reason} says why and what "
        "to do",
    ),
    "pb_feed_again_off_said": (
        "The personal best feed is **off**, so nothing was posted. Set pb_feed_mode to shadow or "
        "on — in /settings or on the Settings page — and try again.",
        (),
        "what staff are told when they press Post again while pb_feed_mode is off",
    ),
    "pb_feed_no_post_said": (
        "There is no personal best post {post} on record, so nothing was posted.",
        ("post",),
        "what staff are told when Post again names a post Black Bloc has no record of",
    ),
    "pb_feed_again_not_in_feed_said": (
        "{member} is {state} in the feed, so only Post again posts for them.",
        ("member", "state"),
        "what Post again adds when the member is no longer matched, opted out or blocked; {state} "
        "says which",
    ),
    "pb_feed_dm_set": (
        "Staff in **{server}** matched you to **{runner}** on speedrun.com for the personal best "
        "feed. Their reason: {reason}\nRun /pb in the server to see it, or to opt out.",
        ("server", "runner", "reason"),
        "the DM a member gets when staff set their speedrun.com account by hand. {server} is "
        "the server's name, {runner} the account, {reason} what staff typed or "
        "pb_feed_dm_no_reason",
    ),
    "pb_feed_dm_unmatched": (
        "Staff in **{server}** removed your match to **{runner}** on speedrun.com from the "
        "personal best feed. Their reason: {reason}\nBlack Bloc may find your account again "
        "from your Twitch link; run /pb in the server to see where it stands, or to opt out.",
        ("server", "runner", "reason"),
        "the DM a member gets when staff unmatch them from the personal best feed",
    ),
    "pb_feed_dm_blocked": (
        "Staff in **{server}** turned the personal best feed off for you: Black Bloc no longer "
        "looks at your speedrun.com runs. Their reason: {reason}\nAsk staff if you think that "
        "should change.",
        ("server", "runner", "reason"),
        "the DM a member gets when staff block them from the personal best feed; {runner} is "
        "the account they were matched to, or nothing",
    ),
    "pb_feed_dm_opt_out_cleared": (
        "You had asked Black Bloc in **{server}** to leave your personal bests alone. Staff "
        "have put you back in the personal best feed. Their reason: {reason}\nRun /pb in the "
        "server to opt out again.",
        ("server", "reason"),
        "the DM a member gets when staff clear their opt-out",
    ),
    "pb_feed_dm_no_reason": (
        "none was given.",
        (),
        "what {reason} becomes in a personal best DM when staff typed no reason",
    ),
}
PB_FEED_DEFAULTS: dict[str, Any] = {
    PB_FEED_MODE: "shadow",
    PB_FEED_AUTO_MATCH: True,
    **{key: default for key, (default, _, _) in PB_FEED_NUMBERS.items()},
    **{key: default for key, (default, _, _) in PB_FEED_WORDS.items()},
}
PB_FEED_KEYS: tuple[str, ...] = (
    PB_FEED_MODE,
    PB_FEED_CHANNEL,
    PB_FEED_SHADOW_CHANNEL,
    PB_FEED_PING_ROLE,
    PB_FEED_AUTO_MATCH,
    *PB_FEED_NUMBERS,
    *PB_FEED_WORDS,
)
KEY_TYPES.update(
    {
        PB_FEED_MODE: "enum",
        PB_FEED_CHANNEL: "channel",
        PB_FEED_SHADOW_CHANNEL: "channel",
        PB_FEED_PING_ROLE: "role",
        PB_FEED_AUTO_MATCH: "bool",
        **{key: "int" for key in PB_FEED_NUMBERS},
        **{key: "text" for key in PB_FEED_WORDS},
    }
)
KEY_CHOICES[PB_FEED_MODE] = PB_FEED_MODES
KEY_MIN.update({key: low for key, (_, low, _) in PB_FEED_NUMBERS.items()})
KEY_MAX.update({key: high for key, (_, _, high) in PB_FEED_NUMBERS.items()})
KEY_MIN_REASON[PB_FEED_INTERVAL] = (
    "speedrun.com allows 100 requests a minute from one address; under {limit} minutes "
    "Black Bloc would be asking about the same members more often than a run gets verified."
)
KEY_HELP.update(
    {
        PB_FEED_MODE: (
            "off, shadow or on. off asks speedrun.com nothing; shadow — the default — looks, "
            "and sends each new personal best to the rehearsal home with a line naming where "
            "it would have gone; on posts it in pb_feed_channel_id. A personal best is posted "
            "only once speedrun.com has verified it, and a member's existing ones are never "
            "posted"
        ),
        PB_FEED_CHANNEL: (
            "where a new personal best is posted while pb_feed_mode is on. Blank posts "
            "nothing and says so in the log — Black Bloc never picks a channel itself"
        ),
        PB_FEED_SHADOW_CHANNEL: (
            "where a new personal best is rehearsed while pb_feed_mode is shadow; blank means "
            "shadow_channel_id"
        ),
        PB_FEED_PING_ROLE: (
            "a role mentioned above each personal best post; blank — the default — pings "
            "nobody. A rehearsal copy never pings"
        ),
        PB_FEED_AUTO_MATCH: (
            "true — the default — finds a member's speedrun.com account from the Twitch "
            "channel they linked with /golive, when exactly one account lists that channel; "
            "false leaves matching to staff. A member who opted out, or whom staff blocked, "
            "is never matched automatically either way"
        ),
        PB_FEED_INTERVAL: (
            "how many minutes pass between two looks at one member's personal bests; 60 by "
            "default, 15 to 1440. The members are spread across the interval, a few a minute"
        ),
        PB_FEED_CYCLE_REQUESTS: (
            "the most requests Black Bloc sends speedrun.com within one "
            "pb_feed_interval_minutes; 400 by default, which covers 300 members looked at "
            "once an hour with room for lookups. At the cap it stops until the interval has "
            "passed and says so once in the log; Look now and Set by hand stop there too"
        ),
        PB_FEED_REMATCH_DAYS: (
            "how many days pass before Black Bloc looks again for the speedrun.com account of "
            "a member it found none for; 7 by default"
        ),
        PB_FEED_MAX_AGE_DAYS: (
            "a run verified more than this many days ago is recorded and not posted; 7 by "
            "default. It is what stops old runs being posted after a long outage or when a "
            "leaderboard is reorganised"
        ),
        PB_FEED_MAX_POSTS: (
            "the most personal bests posted for one member from one look; 5 by default. The "
            "rest are recorded and never posted"
        ),
        PB_FEED_PANEL_MINUTES: (
            "minutes the /pb panel stays live before its buttons disable themselves; 10 by "
            "default"
        ),
        **{key: said for key, (_, _, said) in PB_FEED_WORDS.items()},
    }
)


# Tournament brackets (docs/info/brackets-design.md) — its own block so parallel branches merge
# textually. Every key sits under `core`: `brackets_` would be a 26th setting group.
BRACKETS_FEATURE = "brackets"
BRACKETS_MODES = ("off", "shadow", "on")
BRACKETS_FORMATS = ("single", "double", "round_robin", "swiss")
BRACKETS_LENGTHS = ("1", "3", "5", "7", "9", "11", "13", "15")
BRACKETS_MODE = "brackets_mode"
BRACKETS_CHANNEL = "brackets_channel_id"
BRACKETS_CHANNEL_ID = 1076005097617760296
BRACKETS_SHADOW_CHANNEL = shadow_feature_key(BRACKETS_FEATURE)
BRACKETS_TO_ROLE = "brackets_to_role_id"
BRACKETS_FORMAT_DEFAULT = "brackets_format_default"
BRACKETS_BEST_OF = "brackets_best_of"
BRACKETS_BEST_OF_LATE = "brackets_best_of_late"
BRACKETS_BEST_OF_FINALS = "brackets_best_of_finals"
BRACKETS_GRAND_FINAL_RESET = "brackets_grand_final_reset_default"
BRACKETS_THIRD_PLACE = "brackets_third_place_default"
BRACKETS_CONFIRM_MINUTES = "brackets_confirm_minutes"
BRACKETS_CHECK_IN_MINUTES = "brackets_check_in_minutes"
BRACKETS_BEST_OF_FROM_ROUND = "brackets_best_of_from_round"
BRACKETS_SWISS_ROUNDS = "brackets_swiss_rounds_default"
BRACKETS_ENTRANT_CAP = "brackets_entrant_cap_default"
BRACKETS_PANEL_MINUTES = "brackets_panel_minutes"
BRACKETS_POOLS_FORMATS = ("none", "round_robin", "swiss")
BRACKETS_POOLS_FORMAT = "brackets_pools_format_default"
BRACKETS_POOL_COUNT = "brackets_pool_count_default"
BRACKETS_ADVANCE_PER_POOL = "brackets_advance_per_pool_default"
BRACKETS_ADVANCE_LOSERS_FROM = "brackets_advance_losers_from_default"
BRACKETS_POOLS_SWISS_ROUNDS = "brackets_pools_swiss_rounds_default"
BRACKETS_POOLS_BEST_OF = "brackets_pools_best_of_default"
BRACKETS_NUMBERS: dict[str, tuple[int | None, int, int]] = {
    BRACKETS_CONFIRM_MINUTES: (12, 1, 1440),
    BRACKETS_CHECK_IN_MINUTES: (30, 5, 1440),
    BRACKETS_BEST_OF_FROM_ROUND: (None, 2, 1024),
    BRACKETS_SWISS_ROUNDS: (None, 1, 20),
    BRACKETS_ENTRANT_CAP: (None, 2, 1024),
    BRACKETS_PANEL_MINUTES: (10, 1, 14),
    BRACKETS_POOL_COUNT: (2, 1, 16),
    BRACKETS_ADVANCE_PER_POOL: (2, 1, 16),
    BRACKETS_ADVANCE_LOSERS_FROM: (None, 2, 16),
    BRACKETS_POOLS_SWISS_ROUNDS: (None, 1, 20),
}
BRACKETS_ENUMS: dict[str, tuple[str, tuple[str, ...]]] = {
    BRACKETS_MODE: ("shadow", BRACKETS_MODES),
    BRACKETS_FORMAT_DEFAULT: ("double", BRACKETS_FORMATS),
    BRACKETS_BEST_OF: ("3", BRACKETS_LENGTHS),
    BRACKETS_BEST_OF_LATE: ("5", BRACKETS_LENGTHS),
    BRACKETS_BEST_OF_FINALS: ("5", BRACKETS_LENGTHS),
    BRACKETS_POOLS_FORMAT: ("none", BRACKETS_POOLS_FORMATS),
    BRACKETS_POOLS_BEST_OF: ("3", BRACKETS_LENGTHS),
}
BRACKETS_BOOLS: dict[str, bool] = {
    BRACKETS_GRAND_FINAL_RESET: True,
    BRACKETS_THIRD_PLACE: False,
}
BRACKETS_NAMED = ("name",)
BRACKETS_SET = ("set",)
BRACKETS_ENTRANT = ("entrant", "name")
BRACKETS_WORDS: dict[str, tuple[str, tuple[str, ...], str]] = {
    "brackets_checked_in_said": (
        "{entrant} is checked in for **{name}**.",
        BRACKETS_ENTRANT,
        "what is said after an entrant checks in, or is checked in by a tournament organiser",
    ),
    "brackets_checked_out_said": (
        "{entrant} is no longer checked in for **{name}**.",
        BRACKETS_ENTRANT,
        "what a tournament organiser is told after taking back an entrant's check-in",
    ),
    "brackets_joined_said": (
        "You are in **{name}**.",
        BRACKETS_NAMED,
        "what a member is told after signing themselves up",
    ),
    "brackets_left_said": (
        "You have left **{name}**.",
        BRACKETS_NAMED,
        "what a member is told after taking themselves out before the start",
    ),
    "brackets_dropped_said": (
        "{entrant} has dropped out of **{name}**; their remaining sets are forfeited.",
        BRACKETS_ENTRANT,
        "what is said after an entrant drops out of a running tournament",
    ),
    "brackets_set_called_said": (
        "{set} is called: {a} v {b}.",
        ("set", "a", "b"),
        "what is said after a tournament organiser calls a set; {a} and {b} are its players",
    ),
    "brackets_set_reported_said": (
        "{set} reported {score_a}–{score_b}. It stands in {minutes} minute(s) unless {opponent} "
        "disputes it.",
        ("set", "score_a", "score_b", "minutes", "opponent"),
        "what a player is told after reporting a score; {opponent} is who confirms or disputes it",
    ),
    "brackets_set_final_said": (
        "{set} is final: {winner} wins {result}.",
        ("set", "winner", "result"),
        "what is said after a set is confirmed, decided by a tournament organiser, or forfeited; "
        "{result} is the score or brackets_forfeit_words",
    ),
    "brackets_forfeit_words": (
        "by forfeit",
        (),
        "what {result} becomes in brackets_set_final_said when a set was forfeited",
    ),
    "brackets_set_disputed_said": (
        "{set} is disputed; a tournament organiser decides it.",
        BRACKETS_SET,
        "what a player is told after disputing a reported score",
    ),
    "brackets_off_said": (
        "Tournament brackets are switched **off**, so nothing was done. Set brackets_mode to "
        "shadow or on — in /settings or on the Settings page — and try again.",
        (),
        "what anyone is told when they try a tournament move while brackets_mode is off",
    ),
    "brackets_not_organiser_said": (
        "Running a tournament is for staff and tournament organisers, so nothing was done. Ask "
        "staff for {role}.",
        ("role",),
        "what a member is told when they try a tournament organiser's move; {role} names the "
        "organiser role, or brackets_no_role_words when none is picked",
    ),
    "brackets_no_role_words": (
        "the tournament organiser role (staff have not picked one yet — it is "
        "brackets_to_role_id)",
        (),
        "what {role} becomes in brackets_not_organiser_said while brackets_to_role_id is blank",
    ),
    "brackets_no_tournament_said": (
        "There is no tournament {id} here, so nothing was done.",
        ("id",),
        "what is said when a move names a tournament Black Bloc has no record of",
    ),
    "brackets_wrong_state_said": (
        "**{name}** is {state}, so that cannot be done now.",
        ("name", "state"),
        "what is said when a move does not fit where the tournament is; {state} is one of the "
        "brackets_state_* words",
    ),
    "brackets_state_draft": ("a draft", (), "what {state} says for a tournament being set up"),
    "brackets_state_signups": (
        "open for sign-ups",
        (),
        "what {state} says for a tournament taking sign-ups",
    ),
    "brackets_state_check_in": (
        "in check-in",
        (),
        "what {state} says for a tournament whose check-in window is open",
    ),
    "brackets_state_seeding": (
        "being seeded",
        (),
        "what {state} says for a tournament whose sign-ups have closed and has not started",
    ),
    "brackets_state_running": ("running", (), "what {state} says for a tournament under way"),
    "brackets_state_complete": (
        "complete",
        (),
        "what {state} says for a tournament whose placements are final",
    ),
    "brackets_state_cancelled": ("cancelled", (), "what {state} says for a cancelled tournament"),
    "brackets_not_yours_said": (
        "Only {entrant} or a tournament organiser can do that, so nothing was done.",
        ("entrant",),
        "what a member is told when they check in, or drop, somebody else",
    ),
    "brackets_full_said": (
        "**{name}** is full at {cap} entrants, so you were not added.",
        ("name", "cap"),
        "what a member is told when sign-ups have reached the entrant cap",
    ),
    "brackets_already_in_said": (
        "{entrant} is already in **{name}**.",
        BRACKETS_ENTRANT,
        "what is said when someone signs up, or is added, twice",
    ),
    "brackets_removed_by_to_said": (
        "A tournament organiser took you out of **{name}**, so you cannot sign yourself back "
        "up. Ask them to put you back.",
        BRACKETS_NAMED,
        "what a member is told when they try to sign up again after an organiser removed them",
    ),
    "brackets_no_set_said": (
        "There is no set {set} in **{name}**, so nothing was done.",
        ("set", "name"),
        "what is said when a move names a set that is not in the bracket",
    ),
    "brackets_not_in_set_said": (
        "You are not playing in {set}, so nothing was done. Its two players and tournament "
        "organisers can report it.",
        BRACKETS_SET,
        "what a member is told when they report, confirm or dispute a set they are not in",
    ),
    "brackets_not_ready_said": (
        "{set} is waiting for a player, so it cannot be played yet.",
        BRACKETS_SET,
        "what is said about a set whose players are not both known yet",
    ),
    "brackets_not_playable_said": (
        "{set} is a bye, so nothing is played there.",
        BRACKETS_SET,
        "what is said about a set nobody plays because one side is empty",
    ),
    "brackets_already_complete_said": (
        "{set} is already final. A tournament organiser can correct it.",
        BRACKETS_SET,
        "what a player is told when they report a set that is already decided",
    ),
    "brackets_disputed_said": (
        "{set} is disputed, so a tournament organiser decides it.",
        BRACKETS_SET,
        "what a player is told when they report a set that is under dispute",
    ),
    "brackets_bad_score_said": (
        "That score does not finish a best of {best_of}: the winner has {wins} game(s) and the "
        "loser fewer.",
        ("best_of", "wins"),
        "what is said when a reported score does not fit the set's best-of",
    ),
    "brackets_reported_differently_said": (
        "{set} was reported {score_a}–{score_b}. Confirm that, or dispute it.",
        ("set", "score_a", "score_b"),
        "what a player is told when they report a different score from their opponent's",
    ),
    "brackets_not_reported_said": (
        "{set} has no reported score to confirm or dispute.",
        BRACKETS_SET,
        "what is said when a confirm or dispute names a set nobody has reported",
    ),
    "brackets_own_report_said": (
        "You reported {set}, so your opponent confirms or disputes it.",
        BRACKETS_SET,
        "what a player is told when they confirm or dispute their own report",
    ),
    "brackets_not_in_bracket_said": (
        "{entrant} is not playing in **{name}**, so nothing was done.",
        BRACKETS_ENTRANT,
        "what a tournament organiser is told when they DQ someone the bracket does not hold",
    ),
    "brackets_already_out_said": (
        "{entrant} is already out of **{name}**.",
        BRACKETS_ENTRANT,
        "what is said when an entrant is dropped or disqualified twice",
    ),
}
BRACKETS_PING_ROLE = "brackets_ping_role_id"
BRACKETS_CARD_WORDS: dict[str, tuple[str, tuple[str, ...], str]] = {
    "brackets_format_single_words": (
        "Single elimination",
        (),
        "what {format} says on a tournament card for single elimination",
    ),
    "brackets_format_double_words": (
        "Double elimination",
        (),
        "what {format} says on a tournament card for double elimination",
    ),
    "brackets_format_round_robin_words": (
        "Round robin",
        (),
        "what {format} says on a tournament card for round robin",
    ),
    "brackets_format_swiss_words": (
        "Swiss",
        (),
        "what {format} says on a tournament card for Swiss",
    ),
    "brackets_card_format_line": (
        "{format} · best of {best_of}",
        ("format", "best_of"),
        "the tournament card's format line; the option words follow it, separated by ·",
    ),
    "brackets_card_reset_words": (
        "grand-final reset",
        (),
        "the option word on a double elimination card whose grand final has a reset",
    ),
    "brackets_card_third_words": (
        "third-place set",
        (),
        "the option word on a single elimination card that plays for third place",
    ),
    "brackets_card_rounds_words": (
        "{rounds} rounds",
        ("rounds",),
        "the option word on a Swiss card that names its rounds",
    ),
    "brackets_card_late_words": (
        "best of {best_of} from top {top}",
        ("best_of", "top"),
        "the option word on an elimination card whose late sets are longer",
    ),
    "brackets_card_finals_words": (
        "finals best of {best_of}",
        ("best_of",),
        "the option word on an elimination card naming the last set's best-of",
    ),
    "brackets_card_state_line": (
        "**{state}**",
        ("state",),
        "the tournament card's state line; {state} is a brackets_state_* word",
    ),
    "brackets_card_entrants_line": (
        "{count} entrant(s)",
        ("count",),
        "the tournament card's entrant count when it has no cap",
    ),
    "brackets_card_entrants_cap_line": (
        "{count} of {cap} entrants",
        ("count", "cap"),
        "the tournament card's entrant count when it has a cap",
    ),
    "brackets_card_starts_line": (
        "Starts {when}",
        ("when",),
        "the tournament card's start time line",
    ),
    "brackets_card_check_in_line": (
        "Check-in closes {when}",
        ("when",),
        "the tournament card's line while check-in is open",
    ),
    "brackets_card_to_line": (
        "Organiser: {to}",
        ("to",),
        "the tournament card's line naming who runs it",
    ),
    "brackets_card_place_line": (
        "{place}. {name}",
        ("place", "name"),
        "one placing on a complete tournament's card",
    ),
    "brackets_card_link_label": (
        "Open the bracket",
        (),
        "the tournament card's button to the bracket on the site",
    ),
    "brackets_sign_up_label": ("Sign up", (), "the tournament card's sign-up button"),
    "brackets_leave_label": ("Leave", (), "the tournament card's button to leave before the start"),
    "brackets_check_in_label": ("Check in", (), "the tournament card's check-in button"),
    "brackets_not_entered_said": (
        "You are not signed up for **{name}**, so nothing was done.",
        BRACKETS_NAMED,
        "what a member is told when they press Leave or Check in on a tournament they are not in",
    ),
    "brackets_set_card_players": (
        "{a} v {b}",
        ("a", "b"),
        "the first line of a set's card; {a} and {b} mention the two players",
    ),
    "brackets_round_winners": ("Winners round {round}", ("round",), "a winners-side set's round"),
    "brackets_round_losers": ("Losers round {round}", ("round",), "a losers-side set's round"),
    "brackets_round_grand": ("Grand final", (), "the grand final set's round"),
    "brackets_round_reset": ("Grand final reset", (), "the grand final reset set's round"),
    "brackets_round_third": ("Third place", (), "the third-place set's round"),
    "brackets_round_plain": ("Round {round}", ("round",), "a round robin or Swiss set's round"),
    "brackets_set_card_title": ("{set} · {round}", ("set", "round"), "a set card's title"),
    "brackets_set_card_best_of": ("Best of {best_of}", ("best_of",), "a set card's best-of line"),
    "brackets_set_card_rematch": ("Rematch", (), "a set card's mark when the pair met before"),
    "brackets_set_card_ready": ("Ready to play", (), "a set card's line once both players are in"),
    "brackets_set_card_called": ("Called — play now", (), "a set card's line once it is called"),
    "brackets_set_card_reported": (
        "{reporter} reported {score} — waiting on {opponent}, stands {when}",
        ("reporter", "score", "opponent", "when"),
        "a set card's line while a report waits; {when} is when it stands on its own",
    ),
    "brackets_set_card_disputed": (
        "Disputed by {who} — an organiser decides",
        ("who",),
        "a set card's line while a report is disputed",
    ),
    "brackets_set_card_note": ("“{note}”", ("note",), "a disputed set card's note line"),
    "brackets_set_card_cleared": (
        "{set} was cleared",
        ("set",),
        "a set card's line once its result or players were taken back",
    ),
    "brackets_report_label": ("Report", (), "a set card's report button"),
    "brackets_confirm_label": ("Confirm", (), "a set card's confirm button"),
    "brackets_dispute_label": ("Dispute", (), "a set card's dispute button"),
    "brackets_report_title": (
        "Report {set} · best of {best_of}",
        ("set", "best_of"),
        "the report form's title; Discord cuts a form title at 45 characters",
    ),
    "brackets_score_label": (
        "{name} — games won",
        ("name",),
        "a report form's score box; Discord cuts a form label at 45 characters",
    ),
    "brackets_dispute_title": ("Dispute {set}", ("set",), "the dispute form's title"),
    "brackets_dispute_note_label": ("What is wrong", (), "the dispute form's note box"),
    "brackets_score_not_number_said": (
        "A score is a whole number of games, so nothing was reported.",
        (),
        "what is said when a report form's score is not a whole number",
    ),
    "brackets_panel_title": ("Tournaments", (), "the /bracket panel's title"),
    "brackets_panel_line": (
        "**{name}** · {state} · {count} entrant(s)",
        ("name", "state", "count"),
        "one tournament on the /bracket panel",
    ),
    "brackets_panel_empty": ("No tournaments right now.", (), "the /bracket panel with none"),
    "brackets_pick_placeholder": ("Pick a tournament…", (), "the /bracket tournament picker"),
    "brackets_pick_set_placeholder": ("Pick a set…", (), "the /bracket set picker"),
    "brackets_back_label": ("Back", (), "the /bracket panel's back button"),
    "brackets_your_sets_title": ("Your sets", (), "the heading over a member's own sets"),
    "brackets_drop_label": (
        "Drop out",
        (),
        "the /bracket button a player presses to leave a running tournament",
    ),
    "brackets_drop_confirm": (
        "Drop out of **{name}**? Your remaining sets are forfeited.",
        BRACKETS_NAMED,
        "the question before a player drops out of a running tournament",
    ),
    "brackets_panel_footer": (
        "This panel has gone quiet — run /bracket again.",
        (),
        "the footer a /bracket panel wears once its buttons stop",
    ),
    "brackets_dm_removed": (
        "A tournament organiser took you out of **{name}**.",
        BRACKETS_NAMED,
        "the DM a member gets when an organiser removes them before the start",
    ),
    "brackets_dm_dq": (
        "A tournament organiser disqualified you from **{name}**; your remaining sets are "
        "forfeited.",
        BRACKETS_NAMED,
        "the DM a player gets when an organiser disqualifies them",
    ),
    "brackets_dm_dropped": (
        "A tournament organiser dropped you from **{name}**; your remaining sets are forfeited.",
        BRACKETS_NAMED,
        "the DM a player gets when an organiser drops them from a running tournament",
    ),
    "brackets_dm_decided": (
        "A tournament organiser decided {set} in **{name}**: {result}",
        ("set", "name", "result"),
        "the DM both players get when an organiser decides or corrects their set",
    ),
    "brackets_dm_reset": (
        "A tournament organiser reset {set} in **{name}**.",
        ("set", "name"),
        "the DM both players get when an organiser resets their set",
    ),
    "brackets_dm_reason": (
        "Reason: {reason}",
        ("reason",),
        "the line under an organiser's DM when they gave a reason",
    ),
    "brackets_start_ping": (
        "{role} **{name}** has started.",
        ("role", "name"),
        "posted in a tournament's thread at the start when brackets_ping_role_id is picked",
    ),
    "brackets_moved_line": (
        "This tournament moved to {thread}.",
        ("thread",),
        "the line a rehearsal thread keeps once staff move its tournament into #knuck-up",
    ),
}
BRACKETS_WAITING = ("set", "opponent")
BRACKETS_PAGE_WORDS: dict[str, tuple[str, tuple[str, ...], str]] = {
    "brackets_waiting_play": (
        "Play {opponent} · {set}",
        BRACKETS_WAITING,
        "the bracket page's line for a player whose set is ready",
    ),
    "brackets_waiting_called": (
        "Called — play {opponent} now · {set}",
        BRACKETS_WAITING,
        "the bracket page's line for a player whose set an organiser called",
    ),
    "brackets_waiting_confirm": (
        "{opponent} reported {set} — confirm or dispute",
        BRACKETS_WAITING,
        "the bracket page's line for a player whose opponent reported a score",
    ),
    "brackets_waiting_opponent_confirms": (
        "Waiting on {opponent} to confirm {set}",
        BRACKETS_WAITING,
        "the bracket page's line for a player who reported and waits on the opponent",
    ),
    "brackets_waiting_to_decides": (
        "{set} is disputed — an organiser decides",
        BRACKETS_WAITING,
        "the bracket page's line for a player whose set is disputed",
    ),
    "brackets_waiting_waits": (
        "Next: {set}",
        BRACKETS_WAITING,
        "the bracket page's line for a player waiting on another set to finish",
    ),
    "brackets_waiting_next_round": (
        "Waiting for the next round",
        BRACKETS_WAITING,
        "the bracket page's line for a Swiss player waiting on the next round",
    ),
    "brackets_waiting_done": (
        "Finished",
        BRACKETS_WAITING,
        "the bracket page's line for a player with nothing left to play",
    ),
    "brackets_waiting_out": (
        "Out",
        BRACKETS_WAITING,
        "the bracket page's line for a player who dropped or was disqualified",
    ),
    "brackets_discord_label": (
        "In Discord",
        (),
        "the bracket page's link from a set to its card in the tournament thread",
    ),
}
BRACKETS_POOL_WORDS: dict[str, tuple[str, tuple[str, ...], str]] = {
    "brackets_state_pools": (
        "in pools",
        (),
        "what {state} says for a tournament playing its pools",
    ),
    "brackets_round_pool": (
        "Pool {pool} · round {round}",
        ("pool", "round"),
        "a pool set's round; {pool} is the pool's letter",
    ),
    "brackets_pool_title": ("Pool {pool}", ("pool",), "a pool's name; {pool} is its letter"),
    "brackets_card_pools_words": (
        "{count} pools of {format}, top {advance} through",
        ("count", "format", "advance"),
        "the tournament card's pools option; {format} is a brackets_format_* word",
    ),
    "brackets_card_losers_words": (
        "place {place} and below start in losers",
        ("place",),
        "the tournament card's option for pool finishers who enter the final's losers side",
    ),
    "brackets_card_pool_line": (
        "Pool {pool} · {top}",
        ("pool", "top"),
        "a pool's line on the tournament card while the pools play; {top} is its leaders",
    ),
    "brackets_waiting_final": (
        "Waiting for the final",
        BRACKETS_WAITING,
        "the bracket page's line for a player whose pool is done and the final is not built",
    ),
    "brackets_pool_tied": (
        "tied",
        (),
        "the bracket page's mark on a finished pool's row tied across the cut line",
    ),
    "brackets_pool_raise_label": (
        "Move up",
        (),
        "the bracket page's button that moves a tied player up a finished pool's order",
    ),
}
BRACKETS_WORDS.update(BRACKETS_CARD_WORDS)
BRACKETS_WORDS.update(BRACKETS_PAGE_WORDS)
BRACKETS_WORDS.update(BRACKETS_POOL_WORDS)
BRACKETS_DEFAULTS: dict[str, Any] = {
    BRACKETS_CHANNEL: BRACKETS_CHANNEL_ID,
    **{key: default for key, (default, _) in BRACKETS_ENUMS.items()},
    **BRACKETS_BOOLS,
    **{key: default for key, (default, _, _) in BRACKETS_NUMBERS.items() if default is not None},
    **{key: default for key, (default, _, _) in BRACKETS_WORDS.items()},
}
BRACKETS_KEYS: tuple[str, ...] = (
    BRACKETS_MODE,
    BRACKETS_CHANNEL,
    BRACKETS_SHADOW_CHANNEL,
    BRACKETS_TO_ROLE,
    BRACKETS_PING_ROLE,
    BRACKETS_FORMAT_DEFAULT,
    BRACKETS_BEST_OF,
    BRACKETS_BEST_OF_LATE,
    BRACKETS_BEST_OF_FINALS,
    BRACKETS_POOLS_FORMAT,
    BRACKETS_POOLS_BEST_OF,
    *BRACKETS_BOOLS,
    *BRACKETS_NUMBERS,
    *BRACKETS_WORDS,
)
KEY_TYPES.update(
    {
        BRACKETS_CHANNEL: "channel",
        BRACKETS_SHADOW_CHANNEL: "channel",
        BRACKETS_TO_ROLE: "role",
        BRACKETS_PING_ROLE: "role",
        **{key: "enum" for key in BRACKETS_ENUMS},
        **{key: "bool" for key in BRACKETS_BOOLS},
        **{key: "int" for key in BRACKETS_NUMBERS},
        **{key: "text" for key in BRACKETS_WORDS},
    }
)
KEY_CHOICES.update({key: choices for key, (_, choices) in BRACKETS_ENUMS.items()})
KEY_MIN.update({key: low for key, (_, low, _) in BRACKETS_NUMBERS.items()})
KEY_MAX.update({key: high for key, (_, _, high) in BRACKETS_NUMBERS.items()})
KEY_HELP.update(
    {
        BRACKETS_MODE: (
            "off, shadow or on. off refuses every tournament move; shadow — the default — runs "
            "tournaments with each one's thread made in the rehearsal home instead of "
            "brackets_channel_id; on makes the threads in brackets_channel_id"
        ),
        BRACKETS_CHANNEL: (
            "the text channel each tournament's thread is made under while brackets_mode is "
            "on; #knuck-up by default"
        ),
        BRACKETS_SHADOW_CHANNEL: (
            "where tournament threads are made while brackets_mode is shadow; blank means "
            "shadow_channel_id"
        ),
        BRACKETS_TO_ROLE: (
            "the Tournament Organiser role: its holders may create and run tournaments as staff "
            "can. Blank — the default — leaves tournaments to staff. Taking the role away takes "
            "the right away, even for a tournament that person created"
        ),
        BRACKETS_PING_ROLE: (
            "a role @-mentioned in a tournament's thread when it starts. Blank — the default — "
            "pings nobody; the set cards still mention their two players"
        ),
        BRACKETS_FORMAT_DEFAULT: (
            "the format a new tournament starts with: single, double — the default — "
            "round_robin or swiss. The organiser can change it until the tournament starts"
        ),
        BRACKETS_BEST_OF: (
            "the best-of every set plays unless a later rule says longer; 3 by default"
        ),
        BRACKETS_BEST_OF_LATE: (
            "the best-of a set plays once brackets_best_of_from_round entrants or fewer are "
            "left in an elimination bracket; 5 by default"
        ),
        BRACKETS_BEST_OF_FINALS: (
            "the best-of of the last set of an elimination bracket — the grand final and its "
            "reset, or a single elimination final; 5 by default"
        ),
        BRACKETS_GRAND_FINAL_RESET: (
            "true — the default — plays a second grand final set when the player from the "
            "losers side wins the first, so both have lost once; false lets the first grand "
            "final decide. A new double elimination tournament starts with this and its "
            "organiser can change it"
        ),
        BRACKETS_THIRD_PLACE: (
            "true plays a set between the two semi-final losers of a single elimination "
            "bracket for third place; false — the default — places both third"
        ),
        BRACKETS_CONFIRM_MINUTES: (
            "minutes a reported score waits for the opponent to confirm or dispute it before it "
            "stands on its own; 12 by default, as start.gg's verify timer"
        ),
        BRACKETS_CHECK_IN_MINUTES: (
            "how many minutes a new tournament's check-in window stays open; 30 by default. "
            "Whoever has not checked in when it closes is taken out and the bracket is made "
            "without them"
        ),
        BRACKETS_BEST_OF_FROM_ROUND: (
            "from how many entrants left an elimination set plays brackets_best_of_late — 8 "
            "means top 8. Blank — the default — never lengthens sets before the final"
        ),
        BRACKETS_SWISS_ROUNDS: (
            "how many rounds a new Swiss tournament plays. Blank — the default — plays enough "
            "rounds to separate the field: log2 of the entrants, rounded up"
        ),
        BRACKETS_ENTRANT_CAP: (
            "the most entrants a new tournament takes by sign-up. Blank — the default — takes "
            "any number; an organiser can still add people by hand past it"
        ),
        BRACKETS_PANEL_MINUTES: (
            "minutes a tournament panel stays live before its buttons disable themselves; 10 "
            "by default"
        ),
        BRACKETS_POOLS_FORMAT: (
            "whether a new tournament plays pools before its bracket: none — the default — "
            "round_robin or swiss. The organiser can change it until the tournament starts"
        ),
        BRACKETS_POOL_COUNT: "how many pools a new tournament with pools splits into; 2 by default",
        BRACKETS_ADVANCE_PER_POOL: (
            "how many from the top of each pool go through to the bracket; 2 by default"
        ),
        BRACKETS_ADVANCE_LOSERS_FROM: (
            "the pool place from which those going through start on the losers side of a double "
            "elimination bracket — 2 sends every pool's 2nd there. Blank — the default — puts "
            "everyone on the winners side"
        ),
        BRACKETS_POOLS_SWISS_ROUNDS: (
            "how many rounds Swiss pools play. Blank — the default — plays log2 of the pool, "
            "rounded up"
        ),
        BRACKETS_POOLS_BEST_OF: "the best-of every pool set plays; 3 by default",
        **{key: said for key, (_, _, said) in BRACKETS_WORDS.items()},
    }
)


# The BaF point system (docs/info/points-design.md) — its own block so parallel branches merge
# textually. Every key sits under `core`: `points_` would be a 26th setting group.
POINTS_FEATURE = "points"
POINTS_MODES = ("off", "shadow", "on")
POINTS_ORDERS = ("points", "xp")
POINTS_CLOCKS = ("approved", "submitted")
POINTS_MODE = "points_mode"
POINTS_CHANNEL = "points_channel_id"
POINTS_CHANNEL_ID = 1076003845232148580
POINTS_SHADOW_CHANNEL = shadow_feature_key(POINTS_FEATURE)
POINTS_PING_ROLE = "points_ping_role_id"
POINTS_VERIFIER_ROLE = "points_verifier_role_id"
POINTS_XP_TIERS = "points_xp_tiers"
POINTS_XP_MIN = "points_xp_min"
POINTS_XP_MAX = "points_xp_max"
POINTS_PER_RUN = "points_per_run"
POINTS_TOP_N = "points_top_n"
POINTS_BOARD_ORDER = "points_board_order"
POINTS_BOUNTY_CLOCK = "points_bounty_clock"
POINTS_NUMBERS: dict[str, tuple[int, int, int]] = {
    POINTS_XP_MIN: (POINTS_XP_LOW, 0, POINTS_MOST_XP),
    POINTS_XP_MAX: (POINTS_XP_HIGH, 1, POINTS_MOST_XP),
    POINTS_PER_RUN: (POINTS_PER_RUN_DEFAULT, 0, POINTS_MOST_XP),
    POINTS_TOP_N: (10, 1, 25),
}
POINTS_ENUMS: dict[str, tuple[str, tuple[str, ...]]] = {
    POINTS_MODE: ("shadow", POINTS_MODES),
    POINTS_BOARD_ORDER: ("points", POINTS_ORDERS),
    POINTS_BOUNTY_CLOCK: ("approved", POINTS_CLOCKS),
}
POINTS_RUN = ("game", "time")
POINTS_PLACE = ("name", "place", "was", "top", "points", "xp")
POINTS_WORDS: dict[str, tuple[str, tuple[str, ...], str]] = {
    "points_announce_title": (
        "Leaderboard update",
        (),
        "the heading of the post in points_channel_id when the top places change",
    ),
    "points_announce_entered": (
        "{name} is in the top {top} at #{place} with {points} speedpoints.",
        POINTS_PLACE,
        "the line that post carries for a member who entered the top places; {place} is where "
        "they are now, {top} is points_top_n",
    ),
    "points_announce_left": (
        "{name} dropped out of the top {top}.",
        POINTS_PLACE,
        "the line that post carries for a member who fell out of the top places; {was} is "
        "where they were",
    ),
    "points_announce_up": (
        "{name} moved up to #{place} (was #{was}).",
        POINTS_PLACE,
        "the line that post carries for a member in the top places who climbed",
    ),
    "points_announce_down": (
        "{name} moved down to #{place} (was #{was}).",
        POINTS_PLACE,
        "the line that post carries for a member in the top places who was passed",
    ),
    "points_board_title": (
        "Leaderboard",
        (),
        "the heading of the leaderboard ranked by speedpoints",
    ),
    "points_board_xp_title": (
        "Leaderboard by XP",
        (),
        "the heading of the leaderboard ranked by XP",
    ),
    "points_column_player": ("Player", (), "the leaderboard's player column"),
    "points_column_runs": ("Total runs", (), "the leaderboard's column of approved runs"),
    "points_column_xp": ("Total XP", (), "the leaderboard's XP column"),
    "points_column_points": ("Speedpoints", (), "the leaderboard's speedpoints column"),
    "points_board_line": (
        "#{place} {name} — {runs} runs · {xp} XP · {points} speedpoints",
        ("place", "name", "runs", "xp", "points"),
        "one row of the leaderboard where it is written as lines rather than a table",
    ),
    "points_board_empty": (
        "No runs have been approved yet.",
        (),
        "what the leaderboard says while nobody has an approved run",
    ),
    "points_next_rank_said": (
        "You are #{place} with {points} speedpoints. {gap} more passes {name} at #{above} — "
        "about {runs} approved run(s).",
        ("place", "points", "gap", "name", "above", "runs"),
        "what a member is told when they ask how far the next place is; {gap} is one more than "
        "the difference, so no tie-break decides it",
    ),
    "points_next_rank_first_said": (
        "You are #1 with {points} speedpoints. Nobody is ahead of you.",
        ("points",),
        "what the member in first place is told when they ask how far the next place is",
    ),
    "points_next_rank_unranked_said": (
        "You are not on the leaderboard yet. Your first approved run puts you on it.",
        (),
        "what a member with no approved run is told when they ask how far the next place is",
    ),
    "points_submitted_said": (
        "Your **{game}** run ({time}) is in. Staff check the proof before it counts.",
        POINTS_RUN,
        "what a member is told after submitting a run",
    ),
    "points_no_game_said": (
        "A run needs its game, at most {limit} characters, so nothing was sent.",
        ("limit",),
        "what a member is told when a submission has no game, or one too long",
    ),
    "points_too_long_said": (
        "The {field} can be at most {limit} characters, so nothing was sent.",
        ("field", "limit"),
        "what a member is told when the category or the note is too long",
    ),
    "points_no_time_said": (
        "A run needs its time — 1:23:45, 23:45, 45.2 or 1h 2m 3s — so nothing was sent.",
        (),
        "what a member is told when a submission has no time",
    ),
    "points_bad_time_said": (
        "**{given}** is not a time Black Bloc can read, so nothing was sent. Write it like "
        "1:23:45, 23:45, 45.2 or 1h 2m 3s.",
        ("given",),
        "what a member is told when the time they typed cannot be read",
    ),
    "points_no_proof_said": (
        "A run needs a link to its video or image — an image must show LiveSplit or the "
        "game's own timer — so nothing was sent.",
        (),
        "what a member is told when a submission has no proof link",
    ),
    "points_bad_proof_said": (
        "**{given}** is not a link, so nothing was sent. Paste the whole address, starting "
        "https://.",
        ("given",),
        "what a member is told when the proof they gave is not a web address",
    ),
    "points_off_said": (
        "The point system is switched **off**, so nothing was done. Staff can set points_mode "
        "to shadow or on — in /settings or on the Settings page.",
        (),
        "what anyone is told when they try a point system move while points_mode is off",
    ),
    "points_not_verifier_said": (
        "Approving runs is for staff and {role}, so nothing was done.",
        ("role",),
        "what a member is told when they try to approve or reject a run; {role} names the "
        "verifier role, or points_no_verifier_role_words when none is picked",
    ),
    "points_no_verifier_role_words": (
        "the run verifier role (staff have not picked one yet — it is points_verifier_role_id)",
        (),
        "what {role} becomes in points_not_verifier_said while points_verifier_role_id is blank",
    ),
    "points_not_staff_said": (
        "Only staff can do that, so nothing was done.",
        (),
        "what a member is told when they try a staff move on the leaderboard",
    ),
    "points_own_run_said": (
        "You submitted that run, so someone else approves it.",
        (),
        "what a verifier who is not staff is told when they try to decide their own run",
    ),
    "points_no_run_said": (
        "There is no run {id} here, so nothing was done.",
        ("id",),
        "what is said when a move names a run Black Bloc has no record of",
    ),
    "points_wrong_state_said": (
        "That run is {state}, so that cannot be done now.",
        ("state",),
        "what is said when a move does not fit where a run is; {state} is one of the "
        "points_state_* words",
    ),
    "points_state_pending": (
        "waiting for staff",
        (),
        "what {state} says for a run nobody has decided",
    ),
    "points_state_approved": ("approved", (), "what {state} says for a run that counts"),
    "points_state_rejected": ("not approved", (), "what {state} says for a rejected run"),
    "points_state_removed": (
        "taken off the leaderboard",
        (),
        "what {state} says for an approved run staff took back",
    ),
    "points_dm_rejected": (
        "Your **{game}** run ({time}) was not approved. {reason}",
        ("game", "time", "reason"),
        "the DM a member gets when their run is rejected; {reason} is points_dm_reason or "
        "points_dm_no_reason",
    ),
    "points_dm_removed": (
        "Your **{game}** run ({time}) was taken off the leaderboard. {reason}",
        ("game", "time", "reason"),
        "the DM a member gets when staff take back a run that had been approved",
    ),
    "points_dm_reason": ("Staff said: {reason}", ("reason",), "what {reason} becomes in those DMs"),
    "points_dm_no_reason": (
        "Staff gave no reason.",
        (),
        "what {reason} becomes in those DMs when staff left the reason blank",
    ),
    "points_bounty_line": (
        "**{name}** — {games}: {bonus}, {when}.",
        ("name", "games", "bonus", "when"),
        "one bounty as the leaderboard lists it",
    ),
    "points_bounty_multiplier_words": (
        "×{amount} speedpoints",
        ("amount",),
        "what {bonus} says for a bounty that multiplies a run's speedpoints",
    ),
    "points_bounty_extra_words": (
        "+{amount} speedpoints",
        ("amount",),
        "what {bonus} says for a bounty that adds speedpoints to a run",
    ),
    "points_bounty_until_words": (
        "until {ends}",
        ("ends", "starts"),
        "what {when} says for a bounty with its own dates",
    ),
    "points_bounty_event_words": (
        "during {event}",
        ("event",),
        "what {when} says for a bounty tied to an event",
    ),
    "points_bounty_none": (
        "No bounties right now.",
        (),
        "what the leaderboard says while no bounty is live",
    ),
}
POINTS_DEFAULTS: dict[str, Any] = {
    POINTS_CHANNEL: POINTS_CHANNEL_ID,
    POINTS_XP_TIERS: POINTS_TIERS_TEXT,
    **{key: default for key, (default, _) in POINTS_ENUMS.items()},
    **{key: default for key, (default, _, _) in POINTS_NUMBERS.items()},
    **{key: default for key, (default, _, _) in POINTS_WORDS.items()},
}
POINTS_KEYS: tuple[str, ...] = (
    POINTS_MODE,
    POINTS_CHANNEL,
    POINTS_SHADOW_CHANNEL,
    POINTS_PING_ROLE,
    POINTS_VERIFIER_ROLE,
    POINTS_XP_TIERS,
    *POINTS_NUMBERS,
    POINTS_BOARD_ORDER,
    POINTS_BOUNTY_CLOCK,
    *POINTS_WORDS,
)
KEY_TYPES.update(
    {
        POINTS_CHANNEL: "channel",
        POINTS_SHADOW_CHANNEL: "channel",
        POINTS_PING_ROLE: "role",
        POINTS_VERIFIER_ROLE: "role",
        POINTS_XP_TIERS: "text",
        **{key: "enum" for key in POINTS_ENUMS},
        **{key: "int" for key in POINTS_NUMBERS},
        **{key: "text" for key in POINTS_WORDS},
    }
)
KEY_CHOICES.update({key: choices for key, (_, choices) in POINTS_ENUMS.items()})
KEY_MIN.update({key: low for key, (_, low, _) in POINTS_NUMBERS.items()})
KEY_MAX.update({key: high for key, (_, _, high) in POINTS_NUMBERS.items()})
KEY_HELP.update(
    {
        POINTS_MODE: (
            "off, shadow or on. off refuses every point system move; shadow — the default — "
            "takes and approves runs and sends the top-places post to the rehearsal home; on "
            "posts it in points_channel_id"
        ),
        POINTS_CHANNEL: (
            "where the post goes when somebody enters, leaves or moves inside the top places "
            "while points_mode is on; #speed-and-pbs by default"
        ),
        POINTS_SHADOW_CHANNEL: (
            "where the top-places post is rehearsed while points_mode is shadow; blank means "
            "shadow_channel_id"
        ),
        POINTS_PING_ROLE: (
            "a role mentioned above the top-places post; blank — the default — pings nobody. "
            "A rehearsal copy never pings"
        ),
        POINTS_VERIFIER_ROLE: (
            "a role whose holders may approve and reject submitted runs as staff can. Blank — "
            "the default — leaves approving to staff. A verifier never decides their own run"
        ),
        POINTS_XP_TIERS: (
            "the XP a run earns by its length: each tier is the time it starts at and its XP, "
            "like 1:00=5, 10:00=25, 15:00=50, 30:00=100. A run gets the highest tier it "
            "reaches, never less than points_xp_min nor more than points_xp_max. A change "
            "counts for runs approved after it; Recompute applies it to every approved run"
        ),
        POINTS_XP_MIN: "the least XP an approved run earns, however short it is; 5 by default",
        POINTS_XP_MAX: "the most XP one approved run earns, however long it is; 100 by default",
        POINTS_PER_RUN: "the speedpoints every approved run earns before any bounty; 10 by default",
        POINTS_TOP_N: (
            "how many places at the top of the leaderboard are shown and announced when they "
            "change; 10 by default, at most 25"
        ),
        POINTS_BOARD_ORDER: (
            "what the leaderboard ranks by when it first opens: points — the default — for "
            "speedpoints, or xp. Anyone can switch it while they look"
        ),
        POINTS_BOUNTY_CLOCK: (
            "which moment decides whether a bounty was live for a run: approved — the default "
            "— uses when staff approved it, submitted uses when the member sent it in"
        ),
        **{key: said for key, (_, _, said) in POINTS_WORDS.items()},
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
    PANEL_EXPIRED_TEXT_KEY,
    QUIET_BOT_PINS,
    *STRUCTURE_BACKUP_KEYS,
    *PB_FEED_KEYS,
    *BRACKETS_KEYS,
    *POINTS_KEYS,
)
NAMESPACE_OVERRIDE = {
    "modlog_channel_id": "automod",
    "mod_dm_on_action": "automod",
    "mod_log_level": "automod",
    "mod_panel_minutes": "automod",
    DEFAULT_TIMEZONE_KEY: "events",
    TIMEZONE_CHOICES_KEY: "events",
    TIME_STEP_KEY: "events",
    "event_panel_minutes": "events",
    "event_panel_own_list": "events",
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
    FRONTDOOR_SHOW_TICKET: "modmail",
    FRONTDOOR_SHOW_REQUEST: "modmail",
    FRONTDOOR_SHOW_EVENT: "modmail",
    SHADOW_HOME_KEYS["frontdoor"]: "modmail",
    **{key: "posts" for key in STICKY_KEYS},
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
    SPOTLIGHT_BUMP_PINGS_KEY: "golive",
    SPOTLIGHT_PIN_KEY: "golive",
    SPOTLIGHT_DEFAULT_DAYS_KEY: "golive",
    SPOTLIGHT_EVENT_SLACK_KEY: "golive",
    SPOTLIGHT_RANGE_KEY: "golive",
    SPOTLIGHT_RANGE_KEPT_KEY: "golive",
    SPOTLIGHT_SCHEDULED_WORD_KEY: "golive",
    SPOTLIGHT_DATES_BUTTON_KEY: "golive",
    SPOTLIGHT_STARTS_LABEL_KEY: "golive",
    SPOTLIGHT_ENDS_LABEL_KEY: "golive",
    SPOTLIGHT_END_BEFORE_START_KEY: "golive",
    SPOTLIGHT_BAD_DATE_KEY: "golive",
    SPOTLIGHT_PING_MODE_DEFAULT_KEY: "golive",
    SPOTLIGHT_WINDOW_OPEN_REMINDER_KEY: "golive",
    SPOTLIGHT_WINDOW_KEEP_DAYS_KEY: "golive",
    GOLIVE_EXPIRY_KEEPS_MARATHON_CHANNELS_KEY: "golive",
    SPOTLIGHT_PINGS_ALWAYS_WORDS_KEY: "golive",
    SPOTLIGHT_PINGS_NEVER_WORDS_KEY: "golive",
    SPOTLIGHT_PINGS_EVENTS_WORDS_KEY: "golive",
    SPOTLIGHT_WINDOW_OPEN_WORDS_KEY: "golive",
    SPOTLIGHT_WINDOW_NEXT_WORDS_KEY: "golive",
    SPOTLIGHT_WINDOW_NONE_WORDS_KEY: "golive",
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
LIVE_AUTHOR_UNKNOWN = (
    "`{{{found}}}` is not something Black Bloc knows while a stream is still running, so "
    "nothing was changed. The card's top line may stand in for {allowed}; write any other "
    "braces out as words."
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


def _checked_words(given: Any, allowed: tuple[str, ...]) -> str:
    text = str(given or "").strip()
    stray = next(
        (one.strip() for one in PLACEHOLDERS.findall(text) if one.strip() not in allowed),
        None,
    )
    if stray is not None:
        raise SettingError(
            BUMP_UNKNOWN.format(
                found=stray[:40],
                allowed=", ".join(f"`{{{one}}}`" for one in allowed) or "nothing",
            )
        )
    return text


def checked_range(given: Any) -> str:
    """`{start}` and `{end}` only — a range line has no third date to name."""
    return _checked_words(given, SPOTLIGHT_RANGE_FIELDS)


def checked_given(given: Any) -> str:
    """`{given}` only — a refusal names what was typed and nothing else."""
    return _checked_words(given, SPOTLIGHT_GIVEN_FIELDS)


def checked_window(given: Any) -> str:
    """`{window}` only — the one line that says whether a window is open, next or none."""
    return _checked_words(given, SPOTLIGHT_WINDOW_FIELDS)


def checked_end(given: Any) -> str:
    """`{end}` only — an open window has no start left to name."""
    return _checked_words(given, SPOTLIGHT_END_FIELDS)


def checked_plain(given: Any) -> str:
    """A label or a state word stands in for nothing, so a brace in it would post raw."""
    return _checked_words(given, ())


def checked_count(given: Any) -> str:
    """`{n}` only — a count line names how many and nothing else."""
    return _checked_words(given, BIRTHDAY_POST_COUNT_FIELDS)


def checked_count_where(given: Any) -> str:
    """`{n}` and `{channel}` — how many, and where they went."""
    return _checked_words(given, BIRTHDAY_POST_WHERE_FIELDS)


def checked_live_author(given: Any) -> str:
    """`{name}` and `{platform}` only — a stream that has not ended has no `{duration}`."""
    text = str(given or "").strip()
    stray = next(
        (
            one.strip()
            for one in PLACEHOLDERS.findall(text)
            if one.strip() not in GOLIVE_AUTHOR_FIELDS
        ),
        None,
    )
    if stray is not None:
        raise SettingError(
            LIVE_AUTHOR_UNKNOWN.format(
                found=stray[:40],
                allowed=", ".join(f"`{{{one}}}`" for one in GOLIVE_AUTHOR_FIELDS),
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
    GOLIVE_LIVE_AUTHOR_KEY: checked_live_author,
    GOLIVE_COSTREAM_TEMPLATE_KEY: checked_costream,
    GOLIVE_COSTREAM_AUTHOR_KEY: checked_costream,
    TIMEZONE_CHOICES_KEY: checked_zones,
    WHERE_ALIASES_KEY: checked_aliases,
    EVENTS_SCHEDULED_NAME_KEY: checked_name_template,
    EVENTS_MOVED_LINE_KEY: checked_moved_line,
    REQUEST_FILED_KEY: checked_filed_line,
    RAIDTRAIN_SCHEDULED_NAME_KEY: checked_name_template,
    SPOTLIGHT_BUMP_TEMPLATE_KEY: checked_bump,
    SPOTLIGHT_RANGE_KEY: checked_range,
    SPOTLIGHT_RANGE_KEPT_KEY: checked_range,
    SPOTLIGHT_END_BEFORE_START_KEY: checked_range,
    SPOTLIGHT_BAD_DATE_KEY: checked_given,
    SPOTLIGHT_SCHEDULED_WORD_KEY: checked_plain,
    SPOTLIGHT_DATES_BUTTON_KEY: checked_plain,
    SPOTLIGHT_STARTS_LABEL_KEY: checked_plain,
    SPOTLIGHT_ENDS_LABEL_KEY: checked_plain,
    SPOTLIGHT_PINGS_ALWAYS_WORDS_KEY: checked_plain,
    SPOTLIGHT_PINGS_NEVER_WORDS_KEY: checked_plain,
    SPOTLIGHT_PINGS_EVENTS_WORDS_KEY: checked_window,
    SPOTLIGHT_WINDOW_OPEN_WORDS_KEY: checked_end,
    SPOTLIGHT_WINDOW_NEXT_WORDS_KEY: checked_range,
    SPOTLIGHT_WINDOW_NONE_WORDS_KEY: checked_plain,
    BIRTHDAY_POST_BUTTON_KEY: checked_plain,
    BIRTHDAY_POST_CONFIRM_KEY: checked_plain,
    BIRTHDAY_POST_UNSENT_KEY: checked_plain,
    BIRTHDAY_POST_AGAIN_KEY: checked_plain,
    BIRTHDAY_POST_NOBODY_KEY: checked_plain,
    BIRTHDAY_POST_OFF_KEY: checked_plain,
    BIRTHDAY_POST_POSTED_KEY: checked_count_where,
    BIRTHDAY_POST_REHEARSED_KEY: checked_count_where,
    BIRTHDAY_POST_SKIPPED_KEY: checked_count,
    BIRTHDAY_POST_MISSING_KEY: checked_count,
    BIRTHDAY_POST_FAILED_KEY: checked_count,
}

TEXT_MAY_BE_BLANK = (
    "golive_end_template",
    GOLIVE_LIVE_AUTHOR_KEY,
    "golive_end_author",
    REHEARSAL_NOTE,
    WHERE_HINT_KEY,
)

CHANNEL_NOTE_SAVED_KEY = "chat_channel_note_saved"
CHANNEL_NOTE_CLEARED_KEY = "chat_channel_note_cleared"
CHANNEL_NOTE_NOTHING_KEY = "chat_channel_note_nothing"
CHANNEL_NOTE_TOO_LONG_KEY = "chat_channel_note_too_long"
CHANNEL_NOTE_NO_CHANNEL_KEY = "chat_channel_note_no_channel"
CHANNEL_NOTES_BUTTON_KEY = "chat_channel_notes_button"
CHANNEL_NOTES_TITLE_KEY = "chat_channel_notes_title"
CHANNEL_NOTES_INTRO_KEY = "chat_channel_notes_intro"
CHANNEL_NOTES_PLACEHOLDER_KEY = "chat_channel_notes_placeholder"
CHANNEL_NOTE_MODAL_KEY = "chat_channel_note_modal"
CHANNEL_NOTE_LABEL_KEY = "chat_channel_note_label"
CHANNEL_DRAFT_USED_KEY = "chat_channel_draft_used"
CHANNEL_DRAFT_NONE_KEY = "chat_channel_draft_none"
CHANNEL_DRAFT_RESET_KEY = "chat_channel_draft_reset"
CHANNEL_DRAFT_MISSING_KEY = "chat_channel_draft_missing"
CHANNEL_REACH_SHOWN_KEY = "chat_channel_reach_shown"
CHANNEL_REACH_HIDDEN_KEY = "chat_channel_reach_hidden"
CHANNEL_REACH_CLEARED_KEY = "chat_channel_reach_cleared"
CHANNEL_REACH_NOTHING_KEY = "chat_channel_reach_nothing"
CHANNEL_REACH_IGNORED_KEY = "chat_channel_reach_ignored"
CHANNEL_NOTE_WORDS: dict[str, tuple[str, tuple[str, ...], str]] = {
    CHANNEL_DRAFT_USED_KEY: (
        "The drafted description for **#{channel}** is now its note. Black Bloc reads it in "
        "place of the channel's topic from its next answer on.",
        ("channel",),
        "what staff are told when they use a channel's drafted description as it is, on the "
        "Channels page. It takes {channel}, the channel's name",
    ),
    CHANNEL_DRAFT_NONE_KEY: (
        "**#{channel}** has no note now, and the draft is set aside. Black Bloc goes by the "
        "channel's own topic, or just its name when it has none.",
        ("channel",),
        "what staff are told when they decide a channel needs no note, on the Channels page. It "
        "takes {channel}",
    ),
    CHANNEL_DRAFT_RESET_KEY: (
        "**#{channel}** is back to its draft and waiting for review. Black Bloc reads no note "
        "for it until somebody uses or rewrites the draft.",
        ("channel",),
        "what staff are told when they put a channel back to its draft, on the Channels page. It "
        "takes {channel}",
    ),
    CHANNEL_DRAFT_MISSING_KEY: (
        "**#{channel}** has no drafted description to review, so nothing was done. Write a note "
        "for it instead.",
        ("channel",),
        "what staff are told when they use, set aside or reset a draft on a channel that was "
        "never drafted (made after the catalog). It takes {channel}",
    ),
    CHANNEL_REACH_SHOWN_KEY: (
        "Black Bloc is told about **#{channel}** now, because staff said so, whoever can read "
        "it. **Back to the rule** undoes that.",
        ("channel",),
        "what staff are told when they press Tell the bot anyway on a channel, on the Channels "
        "page. It takes {channel}, the channel's name",
    ),
    CHANNEL_REACH_HIDDEN_KEY: (
        "Black Bloc is not told about **#{channel}** now, because staff said so, even though "
        "members can read it. **Back to the rule** undoes that.",
        ("channel",),
        "what staff are told when they press Hide from the bot on a channel, on the Channels "
        "page. It takes {channel}",
    ),
    CHANNEL_REACH_CLEARED_KEY: (
        "**#{channel}** is back to the rule: Black Bloc is told about it while members can read "
        "it, through the Member role or a role they pick for themselves.",
        ("channel",),
        "what staff are told when they put a channel back to the rule, on the Channels page. It "
        "takes {channel}",
    ),
    CHANNEL_REACH_NOTHING_KEY: (
        "**#{channel}** already follows the rule, so nothing changed.",
        ("channel",),
        "what staff are told when they put back to the rule a channel staff never decided. It "
        "takes {channel}",
    ),
    CHANNEL_REACH_IGNORED_KEY: (
        "**#{channel}** sits in a category Black Bloc leaves out on purpose (one on "
        "`chat_ignore_categories`, or the ticket category), so nothing was changed. Take the "
        "category off that list on the Settings page first.",
        ("channel",),
        "what staff are told when they try to tell the bot about, or hide, a channel in an "
        "ignored category or the ticket category. It takes {channel}",
    ),
    CHANNEL_NOTE_SAVED_KEY: (
        "The note for **#{channel}** is saved. Black Bloc reads it in place of the channel's "
        "topic from its next answer on.",
        ("channel",),
        "what staff are told when a channel note is saved, on /chat and on the Chat page. It "
        "takes {channel}, the channel's name",
    ),
    CHANNEL_NOTE_CLEARED_KEY: (
        "The note for **#{channel}** is gone. Black Bloc goes back to the channel's own topic, "
        "or just its name when it has none.",
        ("channel",),
        "what staff are told when a channel note is cleared. It takes {channel}",
    ),
    CHANNEL_NOTE_NOTHING_KEY: (
        "**#{channel}** had no note, so nothing changed.",
        ("channel",),
        "what staff are told when they clear a channel note that was never written. It takes "
        "{channel}",
    ),
    CHANNEL_NOTE_TOO_LONG_KEY: (
        "That note is {length} characters and a channel note holds {limit}, so nothing was "
        "saved. Take {over} out and save it again.",
        ("length", "limit", "over"),
        "what staff are told when a channel note is longer than the list the model reads can "
        "hold. It takes {length}, {limit} and {over}; nothing is stored when this is said",
    ),
    CHANNEL_NOTE_NO_CHANNEL_KEY: (
        "**{channel}** is not a text channel in this server any more, so nothing was saved. "
        "Pick one from the list again.",
        ("channel",),
        "what staff are told when the channel a note was meant for has gone. It takes "
        "{channel}, the id or name that was given",
    ),
    CHANNEL_NOTES_BUTTON_KEY: (
        "Channel notes…",
        (),
        "the /chat panel button that opens the channel notes. Discord shows at most 80 "
        "characters on a button",
    ),
    CHANNEL_NOTES_TITLE_KEY: (
        "What each channel is for",
        (),
        "the heading of the channel notes card on /chat",
    ),
    CHANNEL_NOTES_INTRO_KEY: (
        "**{count}** channel(s) have a note.",
        ("count",),
        "the first lines of the channel notes card on /chat. It takes {count}, how many "
        "channels have a note",
    ),
    CHANNEL_NOTES_PLACEHOLDER_KEY: (
        "A channel to describe…",
        (),
        "the channel picker's placeholder on the channel notes card. Discord shows at most "
        "150 characters",
    ),
    CHANNEL_NOTE_MODAL_KEY: (
        "What #{channel} is for",
        ("channel",),
        "the title of the form a channel note is written in. It takes {channel}; Discord cuts "
        "a form title at 45 characters",
    ),
    CHANNEL_NOTE_LABEL_KEY: (
        "One sentence — blank clears the note",
        (),
        "the label over the note box on that form. Discord shows at most 45 characters on a "
        "form label",
    ),
}
KEY_TYPES.update({key: "text" for key in CHANNEL_NOTE_WORDS})
KEY_HELP.update({key: said for key, (_, _, said) in CHANNEL_NOTE_WORDS.items()})


def checked_fields(fields: tuple[str, ...]) -> Any:
    return lambda given: _checked_words(given, fields)


TEXT_CHECKS.update(
    {key: checked_fields(fields) for key, (_, fields, _) in CHANNEL_NOTE_WORDS.items()}
)
TEXT_CHECKS.update({key: checked_structure_words(key) for key in STRUCTURE_BACKUP_FIELDS})
TEXT_CHECKS.update(
    {key: checked_fields(fields) for key, (_, fields, _) in PB_FEED_WORDS.items()}
)
TEXT_CHECKS.update(
    {key: checked_fields(fields) for key, (_, fields, _) in BRACKETS_WORDS.items()}
)
TEXT_CHECKS.update(
    {key: checked_fields(fields) for key, (_, fields, _) in POINTS_WORDS.items()}
)
POINTS_BAD_TIERS = (
    "**{given}** is not a tier list Black Bloc can read, so nothing was changed. Write each "
    "tier as the time it starts at, an `=` and its XP, separated by commas — "
    "`1:00=5, 10:00=25, 15:00=50, 30:00=100` — at most {most} tiers."
)


def checked_point_tiers(given: Any) -> str:
    """The tiers in one spelling, earliest first."""
    try:
        return point_tiers_text(parse_point_tiers(given))
    except PointsError:
        raise SettingError(
            POINTS_BAD_TIERS.format(given=str(given or "").strip()[:60], most=10)
        ) from None


TEXT_CHECKS[POINTS_XP_TIERS] = checked_point_tiers

VOICE_SHEET_CHARS = 4000
TONE_CLAUSE_CHARS = 600
BANTER_STYLE_CHARS = 600
GROUNDING_NOTE_CHARS = 600
# Memory that works, and how we talk (2026-10-05) — its own block so parallel branches merge
# textually.
MEMORY_MIN_TURNS_KEY = MIN_TURNS_KEY
KEY_TYPES.update(
    {
        MEMORY_MIN_TURNS_KEY: "int",
        RAPPORT_MAX_KEY: "int",
        RAPPORT_LINE_KEY: "text",
        SWEEP_HOURS_KEY: "int",
    }
)
KEY_MAX.update(
    {
        MEMORY_MIN_TURNS_KEY: DISTIL_MIN_TURNS_CEILING,
        RAPPORT_MAX_KEY: RAPPORT_CEILING,
        SWEEP_HOURS_KEY: SWEEP_HOURS_MAX,
    }
)
KEY_MIN[MEMORY_MIN_TURNS_KEY] = 1
KEY_MIN[SWEEP_HOURS_KEY] = 1
KEY_MIN_REASON[SWEEP_HOURS_KEY] = (
    "A conversation is only written up once it is an hour old, so checking more often than "
    "every {limit} hour would find nothing new."
)
KEY_MIN_REASON[MEMORY_MIN_TURNS_KEY] = (
    "A conversation with no message from the person in it has nothing to remember, so the "
    "fewest Black Bloc will take is {limit}."
)
KEY_HELP.update(
    {
        MEMORY_MIN_TURNS_KEY: (
            f"how many messages a person must have sent Black Bloc in one conversation before "
            f"it is written up into their profile, up to {DISTIL_MIN_TURNS_CEILING}; 1 means a "
            f"single exchange can be remembered"
        ),
        RAPPORT_MAX_KEY: (
            f"how many lines about how a person and Black Bloc talk — the manner they like, a "
            f"running joke — Black Bloc uses from one profile, up to {RAPPORT_CEILING}; a newer "
            f"line on the same subject replaces the older one. Lowering it takes effect on the "
            f"very next answer: lines past the number stay stored and stay on the person's own "
            f"`/memory` panel but are not read, 0 reads none, and raising it brings them back"
        ),
        SWEEP_HOURS_KEY: (
            f"how often, in hours, Black Bloc writes finished conversations up into what it "
            f"remembers, from 1 to {SWEEP_HOURS_MAX}; 1 by default, and a change takes effect "
            f"without a restart. Each conversation written up counts as one of the server's "
            f"chat_daily_turns, so a shorter interval can spend more of them"
        ),
        RAPPORT_LINE_KEY: (
            "how one how-we-talk line reads on a person's own `/memory` panel; {number} is its "
            "place on the list and {text} is the line itself, and both must be there"
        ),
    }
)
RAPPORT_LINE_BROKEN = (
    "That line needs both {{number}} and {{text}} and no other placeholder, and it holds "
    "{limit} characters, so nothing was changed. The shipped one is `{shipped}`."
)


def checked_rapport_line(given: Any) -> str:
    text = str(given or "").strip()
    found = sorted({one.strip() for one in PLACEHOLDERS.findall(text)})
    if found != sorted(RAPPORT_LINE_FIELDS) or len(text) > RAPPORT_LINE_CHARS:
        raise SettingError(
            RAPPORT_LINE_BROKEN.format(limit=RAPPORT_LINE_CHARS, shipped=RAPPORT_LINE)
        )
    return text


TEXT_CHECKS[RAPPORT_LINE_KEY] = checked_rapport_line

PROMPT_TOO_LONG = (
    "That is {length} characters and {what} holds {limit}, so nothing was changed. Every "
    "character is read on every answer; take {over} out and save it again."
)
PROMPT_WORDS: dict[str, tuple[str, int, str, str]] = {
    COOKOUT_VOICE_KEY: (
        COOKOUT_VOICE,
        VOICE_SHEET_CHARS,
        "the cookout voice",
        "the cookout voice itself — the words Black Bloc reaches for, how it greets, teases and "
        "signs off, and what it never says. Every conversational answer is written in it, "
        "whatever tone is on top. It cannot be left blank",
    ),
    TONE_CLAUSE_KEY: (
        TONE_CLAUSE,
        TONE_CLAUSE_CHARS,
        "the tone sentence",
        "the sentence under every tone that tells the model a mood is a tone ON the cookout "
        "voice — keep its words and mannerisms, change only energy, pace and attitude. It "
        "cannot be left blank",
    ),
    BANTER_STYLE_KEY: (
        BANTER_STYLE,
        BANTER_STYLE_CHARS,
        "the small-talk hint",
        "the line every answer reads about greetings and small talk — how short to keep them and "
        "what never to pile on. Blank goes back to the default",
    ),
    GROUNDING_NOTE_KEY: (
        GROUNDING_NOTE,
        GROUNDING_NOTE_CHARS,
        "the notes header",
        "the sentence in front of the server notes a careful answer is handed — how to use them "
        "(silently, never quoted or listed back). Blank goes back to the default",
    ),
}
KEY_TYPES.update({key: "text" for key in PROMPT_WORDS})
KEY_HELP.update({key: said for key, (_, _, _, said) in PROMPT_WORDS.items()})


def checked_prompt(key: str) -> Any:
    _, limit, what, _ = PROMPT_WORDS[key]

    def check(given: Any) -> str:
        text = str(given or "").strip()
        if len(text) > limit:
            raise SettingError(
                PROMPT_TOO_LONG.format(
                    length=len(text), what=what, limit=limit, over=len(text) - limit
                )
            )
        return text

    return check


TEXT_CHECKS.update({key: checked_prompt(key) for key in PROMPT_WORDS})

VOICE_PINNED_KEY = "chat_voice_pinned"
VOICE_CLEARED_KEY = "chat_voice_cleared"
VOICE_NOTHING_KEY = "chat_voice_nothing"
VOICE_NO_MEMBER_KEY = "chat_voice_no_member"
VOICE_NO_TONE_KEY = "chat_voice_no_tone"
VOICE_TONE_OFF_KEY = "chat_voice_tone_off"
VOICE_BUTTON_KEY = "chat_voice_button"
VOICE_TITLE_KEY = "chat_voice_title"
VOICE_INTRO_KEY = "chat_voice_intro"
VOICE_EMPTY_KEY = "chat_voice_empty"
VOICE_OFF_NOTE_KEY = "chat_voice_off_note"
VOICE_LINE_PINNED_KEY = "chat_voice_line_pinned"
VOICE_LINE_ROLLED_KEY = "chat_voice_line_rolled"
VOICE_LINE_WAITING_KEY = "chat_voice_line_waiting"
VOICE_ACTIVE_KEY = "chat_voice_active"
VOICE_SET_KEY = "chat_voice_set_placeholder"
VOICE_TONE_PLACEHOLDER_KEY = "chat_voice_tone_placeholder"
VOICE_CLEAR_BUTTON_KEY = "chat_voice_clear_button"
VOICE_PREVIOUS_KEY = "chat_voice_previous_button"
VOICE_NEXT_KEY = "chat_voice_next_button"
VOICE_PAGE_KEY = "chat_voice_page"
VOICE_MEMBER_TITLE_KEY = "chat_voice_member_title"
TONE_EDITED_KEY = "chat_tone_edited"
TONE_RESET_KEY = "chat_tone_reset"
TONE_TOO_LONG_KEY = "chat_tone_too_long"
VOICE_WORDS: dict[str, tuple[str, tuple[str, ...], str]] = {
    VOICE_PINNED_KEY: (
        "**{member}** hears **{tone}** on top of the cookout voice from their next answer on, "
        "whatever the pool rolls. **Clear** hands them back to the server's setting.",
        ("member", "tone"),
        "what staff are told when a member's tone is pinned, on /chat and on the Chat page. It "
        "takes {member} and {tone}",
    ),
    VOICE_CLEARED_KEY: (
        "**{member}** is unpinned and back on their own tone from their next answer.",
        ("member",),
        "what staff are told when a member's pinned tone is cleared. It takes {member}",
    ),
    VOICE_NOTHING_KEY: (
        "**{member}** had no tone pinned, so nothing changed.",
        ("member",),
        "what staff are told when they clear a pin that was never set. It takes {member}",
    ),
    VOICE_NO_MEMBER_KEY: (
        "**{member}** is not in this server, so nothing was pinned. Pick somebody from the list "
        "again.",
        ("member",),
        "what staff are told when the member a tone was meant for is not in the server. It "
        "takes {member}, the id that was given",
    ),
    VOICE_NO_TONE_KEY: (
        "**{tone}** is not one of the tones Black Bloc knows, so nothing was pinned. The list "
        "beside it is all of them.",
        ("tone",),
        "what staff are told when a pin names a tone that does not exist. It takes {tone}",
    ),
    VOICE_TONE_OFF_KEY: (
        "**{tone}** is switched off in the pool, so it cannot be pinned. Turn it back on under "
        "Personality first, or pick another tone.",
        ("tone",),
        "what staff are told when a pin names a tone that is switched off. It takes {tone}",
    ),
    VOICE_BUTTON_KEY: (
        "Who hears what…",
        (),
        "the button on /chat ▸ Personality that opens the list of which tone each member hears. "
        "Discord shows at most 80 characters on a button",
    ),
    VOICE_TITLE_KEY: (
        "Who hears what",
        (),
        "the heading of the card on /chat that lists which tone each member hears",
    ),
    VOICE_INTRO_KEY: (
        "The server's setting is **{setting}**. **{count}** member(s) listed.",
        ("setting", "count"),
        "the first lines of that card. It takes {setting}, the chat_personality value, and "
        "{count}, how many members are listed",
    ),
    VOICE_EMPTY_KEY: (
        "Nobody has been answered by a conversation model yet, so nobody has a tone. Pick a "
        "member below to pin one.",
        (),
        "what that card says when nobody is listed yet",
    ),
    VOICE_OFF_NOTE_KEY: (
        "The setting is the cookout voice, so nobody hears a tone right now — pins included. "
        "Pick the pool or a mood under Personality and the pins come back into play.",
        (),
        "the line that card adds while chat_personality is cookout",
    ),
    VOICE_LINE_PINNED_KEY: (
        "{member} — **{tone}** · pinned by {by}",
        ("member", "tone", "by"),
        "one pinned member's line on that card. It takes {member}, {tone} and {by}, the staff "
        "member who pinned it",
    ),
    VOICE_LINE_ROLLED_KEY: (
        "{member} — **{tone}** · rolled · {turns} turn(s)",
        ("member", "tone", "turns"),
        "one unpinned member's line on that card. It takes {member}, {tone} and {turns}, the "
        "answers in their current window",
    ),
    VOICE_LINE_WAITING_KEY: (
        "{member} — pinned to **{tone}**, which is switched off, so the setting decides for now",
        ("member", "tone"),
        "the line for a member whose pinned tone is switched off. It takes {member} and {tone}",
    ),
    VOICE_ACTIVE_KEY: (
        "talking now",
        (),
        "the word added after a member's line while their conversation window is open",
    ),
    VOICE_SET_KEY: (
        "Set a member's tone…",
        (),
        "the member picker's placeholder on that card. Discord shows at most 150 characters",
    ),
    VOICE_TONE_PLACEHOLDER_KEY: (
        "Pin… (fix {member}'s tone)",
        ("member",),
        "the placeholder of the picker that pins a member's tone, once a member is picked. It "
        "takes {member}; Discord shows at most 150 characters",
    ),
    VOICE_CLEAR_BUTTON_KEY: (
        "Clear the pin",
        (),
        "the button that hands a pinned member back to the server's setting. Discord shows at "
        "most 80 characters on a button",
    ),
    VOICE_PREVIOUS_KEY: (
        "‹ Previous",
        (),
        "the button that shows the previous 25 members on that card",
    ),
    VOICE_NEXT_KEY: (
        "Next ›",
        (),
        "the button that shows the next 25 members on that card",
    ),
    VOICE_PAGE_KEY: (
        "Page {page} of {pages}",
        ("page", "pages"),
        "the page line on that card when there are more than 25 members. It takes {page} and "
        "{pages}",
    ),
    VOICE_MEMBER_TITLE_KEY: (
        "The tone for {member}",
        ("member",),
        "the heading of one member's card, where a tone is pinned or cleared. It takes {member}",
    ),
    TONE_EDITED_KEY: (
        "**{tone}** now reads the way you wrote it, from the next answer on. The boot sync keeps "
        "your wording.",
        ("tone",),
        "what staff are told when a tone's wording is saved on the Chat page. It takes {tone}",
    ),
    TONE_RESET_KEY: (
        "**{tone}** is back to the wording Black Bloc ships with.",
        ("tone",),
        "what staff are told when a tone's wording is put back. It takes {tone}",
    ),
    TONE_TOO_LONG_KEY: (
        "That tone is {length} characters and a tone holds {limit}, so nothing was saved. Take "
        "{over} out and save it again.",
        ("length", "limit", "over"),
        "what staff are told when a tone's wording is too long. It takes {length}, {limit} and "
        "{over}",
    ),
}
KEY_TYPES.update({key: "text" for key in VOICE_WORDS})
KEY_HELP.update({key: said for key, (_, _, said) in VOICE_WORDS.items()})
TEXT_CHECKS.update(
    {key: checked_fields(fields) for key, (_, fields, _) in VOICE_WORDS.items()}
)


def checked_order(given: Any) -> str:
    text = ", ".join(one.strip().lower() for one in str(given or "").split(",") if one.strip())
    unknown = tone_keys.unknown_tone(text)
    if unknown is not None:
        raise SettingError(
            tone_keys.ORDER_UNKNOWN.format(
                name=unknown[:40], known=", ".join(tone_keys.KNOWN_TONES)
            )
        )
    return text


KEY_TYPES.update({key: kind for key, (kind, _, _) in tone_keys.TONE_SETTINGS.items()})
KEY_HELP.update({key: said for key, (_, _, said) in tone_keys.TONE_SETTINGS.items()})
KEY_CHOICES[tone_keys.FEEDBACK_MODE_KEY] = tone_keys.FEEDBACK_MODES
KEY_MIN.update(
    {
        tone_keys.DRIFT_START_KEY: 0,
        tone_keys.DRIFT_HALVES_KEY: 0,
        tone_keys.DRIFT_FLOOR_KEY: 0,
    }
)
KEY_MAX.update(
    {
        tone_keys.DRIFT_START_KEY: tone_keys.PERCENT_MAX,
        tone_keys.DRIFT_HALVES_KEY: tone_keys.DRIFT_HALVES_MAX,
        tone_keys.DRIFT_FLOOR_KEY: tone_keys.PERCENT_MAX,
    }
)
TEXT_MAY_BE_BLANK = (*TEXT_MAY_BE_BLANK, *tone_keys.MAY_BE_BLANK)
TEXT_CHECKS.update({key: checked_order for key in tone_keys.ORDER_KEYS})
KEY_TYPES.update({key: "text" for key in tone_keys.TONE_WORDS})
KEY_HELP.update({key: said for key, (_, _, said) in tone_keys.TONE_WORDS.items()})
TEXT_CHECKS.update(
    {key: checked_fields(fields) for key, (_, fields, _) in tone_keys.TONE_WORDS.items()}
)


# Chat review loop (2026-09-23): answers that may have missed, tagged, reviewed by staff. Its own
# block so the parallel chat branches merge textually. Design: info/chat-review-loop-design.md.
REVIEW_MODE_KEY = "chat_review_mode"
REVIEW_MODES = ("off", "on")
REVIEW_REASK_KEY = "chat_review_reask_seconds"
REVIEW_REASK_SECONDS = 90
REVIEW_REASK_MAX_SECONDS = 3600
REVIEW_DOWNVOTE_KEY = "chat_review_downvote_emoji"
REVIEW_DOWNVOTE_EMOJI = "\U0001f44e"
REVIEW_NOT_IT_KEY = "chat_review_not_it_phrases"
REVIEW_NOT_IT_PHRASES = (
    "not what i meant, thats not what i meant, thats not it, not what i asked, "
    "you didnt answer, that doesnt answer, wrong answer, no i meant"
)
REVIEW_ACK_KEY = "chat_review_ack_phrases"
REVIEW_ACK_PHRASES = (
    "thanks, thank you, thx, ty, tysm, ok, okay, k, kk, cool, nice, got it, gotcha, perfect, "
    "great, awesome, bet, lol, lmao, haha, yes, yep, yeah, no worries, appreciate it, love it"
)
REVIEW_DIGEST_HOUR_KEY = "chat_review_digest_hour"
REVIEW_DIGEST_HOUR = 9
REVIEW_DIGEST_HOUR_MAX = 23
REVIEW_SETTINGS: dict[str, tuple[str, Any, str]] = {
    REVIEW_MODE_KEY: (
        "enum",
        "on",
        "on (a chat answer that may have missed lands in the Chat page's review queue, the cheap "
        "model suggests what Black Bloc should learn from it, and staff approve, change or "
        "dismiss it) or off (nothing new is queued, tagged or posted; items already waiting stay "
        "reviewable)",
    ),
    REVIEW_REASK_KEY: (
        "int",
        REVIEW_REASK_SECONDS,
        f"seconds after an answer in which the same person writing again in the same channel "
        f"counts as asking again, so the answer is queued for review; a thanks or an ok never "
        f"counts. 0 turns this reason off, up to {REVIEW_REASK_MAX_SECONDS}",
    ),
    REVIEW_DOWNVOTE_KEY: (
        "text",
        REVIEW_DOWNVOTE_EMOJI,
        "the reaction that queues one of Black Bloc's chat answers for review when anybody but "
        "the bot puts it on the answer; blank turns this reason off",
    ),
    REVIEW_NOT_IT_KEY: (
        "text",
        REVIEW_NOT_IT_PHRASES,
        "phrases, separated by commas, that mean the answer missed when somebody says one "
        "straight after it (not what i meant, thats not it); the answer is queued for review. "
        "Blank turns this reason off",
    ),
    REVIEW_ACK_KEY: (
        "text",
        REVIEW_ACK_PHRASES,
        "phrases, separated by commas, that are a thanks or an ok rather than asking again — a "
        "follow-up that is only one of these never queues the answer for review",
    ),
    REVIEW_DIGEST_HOUR_KEY: (
        "int",
        REVIEW_DIGEST_HOUR,
        f"the hour of the day, in default_timezone, when one line goes to the log channel "
        f"saying how many chat answers wait for review; nothing is posted when none wait. 0 to "
        f"{REVIEW_DIGEST_HOUR_MAX}",
    ),
}
KEY_TYPES.update({key: kind for key, (kind, _, _) in REVIEW_SETTINGS.items()})
KEY_HELP.update({key: said for key, (_, _, said) in REVIEW_SETTINGS.items()})
KEY_CHOICES[REVIEW_MODE_KEY] = REVIEW_MODES
KEY_MIN[REVIEW_REASK_KEY] = 0
KEY_MAX[REVIEW_REASK_KEY] = REVIEW_REASK_MAX_SECONDS
KEY_MIN[REVIEW_DIGEST_HOUR_KEY] = 0
KEY_MAX[REVIEW_DIGEST_HOUR_KEY] = REVIEW_DIGEST_HOUR_MAX
TEXT_MAY_BE_BLANK = (*TEXT_MAY_BE_BLANK, REVIEW_DOWNVOTE_KEY, REVIEW_NOT_IT_KEY, REVIEW_ACK_KEY)

REVIEW_DIGEST_KEY = "chat_review_digest"
REVIEW_ADDED_PHRASE_KEY = "chat_review_added_phrase"
REVIEW_MADE_INTENT_KEY = "chat_review_made_intent"
REVIEW_PLACEHOLDER_KEY = "chat_review_placeholder_line"
REVIEW_ADDED_LINE_KEY = "chat_review_added_line"
REVIEW_DISMISSED_KEY = "chat_review_dismissed"
REVIEW_REOPENED_KEY = "chat_review_reopened"
REVIEW_NO_SUCH_KEY = "chat_review_no_such"
REVIEW_DECIDED_KEY = "chat_review_decided"
REVIEW_NOT_DISMISSED_KEY = "chat_review_not_dismissed"
REVIEW_NOTHING_KEY = "chat_review_nothing_suggested"
REVIEW_NO_INTENT_KEY = "chat_review_no_intent"
REVIEW_NEEDS_PHRASE_KEY = "chat_review_needs_phrase"
REVIEW_NEEDS_LINE_KEY = "chat_review_needs_line"
REVIEW_BAD_KIND_KEY = "chat_review_bad_kind"
REVIEW_SECTION_KEY = "chat_review_section_default"
REVIEW_BUTTON_KEY = "chat_review_button"
REVIEW_TITLE_KEY = "chat_review_title"
REVIEW_INTRO_KEY = "chat_review_intro"
REVIEW_EMPTY_KEY = "chat_review_empty"
REVIEW_CAPPED_KEY = "chat_review_capped"
REVIEW_UNTAGGED_KEY = "chat_review_untagged"
REVIEW_LINE_KEY = "chat_review_line"
REVIEW_ITEM_TITLE_KEY = "chat_review_item_title"
REVIEW_ITEM_KEY = "chat_review_item"
REVIEW_PICK_KEY = "chat_review_pick_placeholder"
REVIEW_CHANGE_KEY = "chat_review_change_placeholder"
REVIEW_APPROVE_BUTTON_KEY = "chat_review_approve_button"
REVIEW_DISMISS_BUTTON_KEY = "chat_review_dismiss_button"
REVIEW_FACT_BUTTON_KEY = "chat_review_fact_button"
REVIEW_PHRASE_MODAL_KEY = "chat_review_phrase_modal"
REVIEW_PHRASE_LABEL_KEY = "chat_review_phrase_label"
REVIEW_FACT_MODAL_KEY = "chat_review_fact_modal"
REVIEW_FACT_LABEL_KEY = "chat_review_fact_label"
REVIEW_SECTION_LABEL_KEY = "chat_review_section_label"
REVIEW_PAGE_KEY = "chat_review_page"
REVIEW_REASON_UNGROUNDED_KEY = "chat_review_reason_ungrounded"
REVIEW_REASON_REASK_KEY = "chat_review_reason_reask"
REVIEW_REASON_DOWNVOTE_KEY = "chat_review_reason_downvote"
REVIEW_REASON_NOT_IT_KEY = "chat_review_reason_not_it"
REVIEW_SUGGEST_PHRASE_KEY = "chat_review_suggest_phrase"
REVIEW_SUGGEST_INTENT_KEY = "chat_review_suggest_intent"
REVIEW_SUGGEST_KNOWLEDGE_KEY = "chat_review_suggest_knowledge"
REVIEW_SUGGEST_NONE_KEY = "chat_review_suggest_none"
REVIEW_WORDS: dict[str, tuple[str, tuple[str, ...], str]] = {
    REVIEW_DIGEST_KEY: (
        "**{count}** chat answer(s) are waiting for review — approve, change or dismiss them on "
        "the Chat page: {link}",
        ("count", "link"),
        "the one line posted to the log channel once a day while chat answers wait for review. "
        "It takes {count}, how many wait, and {link}, the Chat page's review queue",
    ),
    REVIEW_ADDED_PHRASE_KEY: (
        "**{phrase}** now reaches **{intent}**. The next person who says it gets that intent's "
        "lines.",
        ("phrase", "intent"),
        "what staff are told when a review adds a phrase to an intent, on /chat and on the Chat "
        "page. It takes {phrase} and {intent}",
    ),
    REVIEW_MADE_INTENT_KEY: (
        "**{intent}** is in, with **{phrase}** as its first phrase. Its one line is a switched-"
        "off placeholder, so it stays quiet until somebody writes the real line on the Chat "
        "page's Intents section and switches it on.",
        ("intent", "phrase"),
        "what staff are told when a review makes a new intent. It takes {intent} and {phrase}",
    ),
    REVIEW_PLACEHOLDER_KEY: (
        "Write what Black Bloc should say here, then switch this line on.",
        (),
        "the placeholder line a review puts on an intent it makes; it is stored switched off, "
        "so nobody is ever answered with it",
    ),
    REVIEW_ADDED_LINE_KEY: (
        "That fact is in the **{section}** note now. Black Bloc quotes it the next time a "
        "question matches.",
        ("section",),
        "what staff are told when a review adds a fact to a knowledge note. It takes {section}, "
        "the note's heading",
    ),
    REVIEW_DISMISSED_KEY: (
        "Item **{id}** is dismissed and nothing was learned from it. **Reopen** on the Chat page "
        "puts it back in the queue.",
        ("id",),
        "what staff are told when a review item is dismissed. It takes {id}",
    ),
    REVIEW_REOPENED_KEY: (
        "Item **{id}** is back in the review queue.",
        ("id",),
        "what staff are told when a dismissed review item is reopened. It takes {id}",
    ),
    REVIEW_NO_SUCH_KEY: (
        "There is no review item **{id}** in this server any more, so nothing was done. Refresh "
        "the queue and pick again.",
        ("id",),
        "what staff are told when the review item they acted on has gone. It takes {id}",
    ),
    REVIEW_DECIDED_KEY: (
        "Item **{id}** was already {status}, so nothing was done — somebody else got there "
        "first. Refresh the queue.",
        ("id", "status"),
        "what staff are told when a review item was decided while they were looking at it. It "
        "takes {id} and {status}",
    ),
    REVIEW_NOT_DISMISSED_KEY: (
        "Only a dismissed item goes back in the queue. Item **{id}** was {status}, and what it "
        "taught Black Bloc stays on the Intents or Knowledge section, where it can be edited or "
        "removed.",
        ("id", "status"),
        "what staff are told when they reopen an item that was approved or changed. It takes "
        "{id} and {status}",
    ),
    REVIEW_NOTHING_KEY: (
        "Item **{id}** has nothing to approve — the cheap model found nothing that fits, or has "
        "not looked at it yet. Change it to a phrase or a fact yourself, or dismiss it.",
        ("id",),
        "what staff are told when they approve an item with no suggestion. It takes {id}",
    ),
    REVIEW_NO_INTENT_KEY: (
        "This server has no intent called **{intent}**, so nothing was saved. Pick one from the "
        "list.",
        ("intent",),
        "what staff are told when a review names an intent that does not exist. It takes "
        "{intent}",
    ),
    REVIEW_NEEDS_PHRASE_KEY: (
        "A phrase needs some words in it, so nothing was saved.",
        (),
        "what staff are told when a review's phrase is blank",
    ),
    REVIEW_NEEDS_LINE_KEY: (
        "A fact needs some words in it, so nothing was saved.",
        (),
        "what staff are told when a review's knowledge fact is blank",
    ),
    REVIEW_BAD_KIND_KEY: (
        "**{kind}** is not something a review can teach, so nothing was saved. It is a phrase "
        "for an intent, a new intent, or a knowledge fact.",
        ("kind",),
        "what staff are told when a review change names no known kind. It takes {kind}",
    ),
    REVIEW_SECTION_KEY: (
        "From review",
        (),
        "the heading of the knowledge note a reviewed fact goes into when the cheap model named "
        "no note of its own",
    ),
    REVIEW_BUTTON_KEY: (
        "Review queue…",
        (),
        "the /chat panel button that opens the review queue. Discord shows at most 80 "
        "characters on a button",
    ),
    REVIEW_TITLE_KEY: (
        "Answers to review",
        (),
        "the heading of the review queue card on /chat",
    ),
    REVIEW_INTRO_KEY: (
        "**{count}** answer(s) may have missed.",
        ("count",),
        "the first line of the review queue card on /chat. It takes {count}, how many wait",
    ),
    REVIEW_EMPTY_KEY: (
        "Nothing is waiting. An answer lands here when a real question found no note, somebody "
        "asks again straight away, says it was not what they meant, or gives it a thumbs down.",
        (),
        "what the review queue card says when nothing waits",
    ),
    REVIEW_CAPPED_KEY: (
        "This month's model money is spent, so new items wait untagged until the 1st. Change "
        "and Dismiss still work.",
        (),
        "the line the review queue adds while the monthly cap stops the cheap model tagging",
    ),
    REVIEW_UNTAGGED_KEY: (
        "not looked at yet",
        (),
        "the words in place of a suggestion on an item the cheap model has not tagged",
    ),
    REVIEW_LINE_KEY: (
        "`{id}` · {reason} · {when}\n> {asked}\nSuggested: {suggestion}",
        ("id", "reason", "when", "asked", "suggestion"),
        "one item's lines on the review queue card. It takes {id}, {reason}, {when}, {asked} — "
        "what the person said — and {suggestion}",
    ),
    REVIEW_ITEM_TITLE_KEY: (
        "Review item {id}",
        ("id",),
        "the heading of one review item's card on /chat. It takes {id}",
    ),
    REVIEW_ITEM_KEY: (
        "**Why it is here:** {reason} · {when}\n**They said:**\n> {asked}\n**Black Bloc "
        "answered:**\n> {answered}\n**Suggested:** {suggestion}\n{why}",
        ("reason", "when", "asked", "answered", "suggestion", "why"),
        "the body of one review item's card on /chat. It takes {reason}, {when}, {asked}, "
        "{answered}, {suggestion} and {why}, the cheap model's reason",
    ),
    REVIEW_PICK_KEY: (
        "An answer to review…",
        (),
        "the item picker's placeholder on the review queue card. Discord shows at most 150 "
        "characters",
    ),
    REVIEW_CHANGE_KEY: (
        "Change it: this should reach…",
        (),
        "the intent picker's placeholder on a review item's card; picking one asks for the "
        "phrase. Discord shows at most 150 characters",
    ),
    REVIEW_APPROVE_BUTTON_KEY: (
        "Approve",
        (),
        "the button that writes a review item's suggestion. Discord shows at most 80 characters",
    ),
    REVIEW_DISMISS_BUTTON_KEY: (
        "Dismiss",
        (),
        "the button that dismisses a review item. Discord shows at most 80 characters",
    ),
    REVIEW_FACT_BUTTON_KEY: (
        "Write a fact…",
        (),
        "the button that turns a review item into a knowledge fact instead. Discord shows at "
        "most 80 characters",
    ),
    REVIEW_PHRASE_MODAL_KEY: (
        "A phrase for {intent}",
        ("intent",),
        "the title of the form a review's phrase is written in. It takes {intent}; Discord cuts "
        "a form title at 45 characters",
    ),
    REVIEW_PHRASE_LABEL_KEY: (
        "The words somebody would say",
        (),
        "the label over the phrase box. Discord shows at most 45 characters on a form label",
    ),
    REVIEW_FACT_MODAL_KEY: (
        "A fact Black Bloc should know",
        (),
        "the title of the form a review's knowledge fact is written in. Discord cuts a form "
        "title at 45 characters",
    ),
    REVIEW_FACT_LABEL_KEY: (
        "One line, in plain words",
        (),
        "the label over the fact box. Discord shows at most 45 characters on a form label",
    ),
    REVIEW_SECTION_LABEL_KEY: (
        "The note it goes in",
        (),
        "the label over the note-heading box on the fact form. Discord shows at most 45 "
        "characters on a form label",
    ),
    REVIEW_PAGE_KEY: (
        "Page {page} of {pages}",
        ("page", "pages"),
        "the page line on the review queue card when more than five wait. It takes {page} and "
        "{pages}",
    ),
    REVIEW_REASON_UNGROUNDED_KEY: (
        "a real question found no note",
        (),
        "the reason shown on an item queued because the careful tier answered with nothing "
        "written down to ground it",
    ),
    REVIEW_REASON_REASK_KEY: (
        "they asked again straight away",
        (),
        "the reason shown on an item queued because the same person wrote again within "
        "chat_review_reask_seconds",
    ),
    REVIEW_REASON_DOWNVOTE_KEY: (
        "somebody gave it a thumbs down",
        (),
        "the reason shown on an item queued because of the chat_review_downvote_emoji reaction",
    ),
    REVIEW_REASON_NOT_IT_KEY: (
        "they said it was not what they meant",
        (),
        "the reason shown on an item queued because the follow-up said one of the "
        "chat_review_not_it_phrases",
    ),
    REVIEW_SUGGEST_PHRASE_KEY: (
        "add **{phrase}** to **{intent}**",
        ("phrase", "intent"),
        "how a suggested phrase reads on a review item. It takes {phrase} and {intent}",
    ),
    REVIEW_SUGGEST_INTENT_KEY: (
        "a new intent **{intent}** for **{phrase}**",
        ("intent", "phrase"),
        "how a suggested new intent reads on a review item. It takes {intent} and {phrase}",
    ),
    REVIEW_SUGGEST_KNOWLEDGE_KEY: (
        "a fact for **{section}**: {line}",
        ("section", "line"),
        "how a suggested knowledge fact reads on a review item. It takes {section} and {line}",
    ),
    REVIEW_SUGGEST_NONE_KEY: (
        "nothing to learn",
        (),
        "how a review item reads when the cheap model found nothing that fits",
    ),
}
KEY_TYPES.update({key: "text" for key in REVIEW_WORDS})
KEY_HELP.update({key: said for key, (_, _, said) in REVIEW_WORDS.items()})
TEXT_CHECKS.update(
    {key: checked_fields(fields) for key, (_, fields, _) in REVIEW_WORDS.items()}
)


MARATHON_MODES = ("off", "shadow", "on")
MARATHON_MODE_KEY = "marathon_mode"
MARATHON_CHANNEL_KEY = "marathon_channel_id"
MARATHON_POLL_MINUTES_KEY = "marathon_poll_minutes"
MARATHON_FAR_POLL_HOURS_KEY = "marathon_far_poll_hours"
MARATHON_LEAD_DAYS_KEY = "marathon_lead_days"
MARATHON_MOVE_MINUTES_KEY = "marathon_move_minutes"
MARATHON_TITLE_CONFIRMS_KEY = "marathon_title_confirms"
MARATHON_CATEGORY_CONFIRMS_KEY = "marathon_category_confirms"
MARATHON_RETRO_CATEGORY_KEY = "marathon_retro_category"
MARATHON_RETRO_CATEGORY = "Retro"
MARATHON_RETRO_LENGTH = 60
MARATHON_SETUP_MINUTES_KEY = "marathon_setup_minutes"
MARATHON_SETUP_MINUTES = 7
MARATHON_SETUP_MAX = 30
MARATHON_EARLY_START_KEY = "marathon_early_start_minutes"
MARATHON_EARLY_START_MINUTES = 10
MARATHON_LATE_GRACE_KEY = "marathon_late_grace_minutes"
MARATHON_MATCH_HOSTS_KEY = "marathon_match_hosts"
MARATHON_HOSTS_COUNT_AS_OURS_KEY = "marathon_hosts_count_as_ours"
MARATHON_REMINDER_MINUTES_KEY = "marathon_reminder_minutes"
MARATHON_PING_MINUTES_KEY = "marathon_ping_minutes"
MARATHON_REMINDER_PINGS_KEY = "marathon_reminder_pings"
MARATHON_LIVE_PINGS_KEY = "marathon_live_pings"
MARATHON_REMINDER_STALE_KEY = "marathon_reminder_stale_minutes"
MARATHON_REMINDER_ON_MOVE_KEY = "marathon_reminder_on_move"
MARATHON_REMINDER_ON_MOVES = ("edit", "repost")
MARATHON_REMINDER_EDIT_LIMIT_KEY = "marathon_reminder_edit_limit"
MARATHON_REMINDER_EDIT_LIMIT = 10
MARATHON_TRACKER_REFRESH_KEY = "marathon_tracker_refresh_seconds"
MARATHON_TRACKER_REFRESH = 30
MARATHON_PIN_BOARD_KEY = "marathon_pin_board"
MARATHON_RUNNER_POSTS_KEY = "marathon_runner_posts"
MARATHON_RUNNER_POSTS_PINNED_KEY = "marathon_runner_posts_pinned"
MARATHON_EDIT_DONE_KEY = "marathon_edit_done"
MARATHON_WINDOW_SLACK_KEY = "marathon_window_slack_hours"
MARATHON_SPOTLIGHT_LEAD_KEY = "marathon_spotlight_lead_hours"
MARATHON_SPOTLIGHT_SLACK_KEY = "marathon_spotlight_slack_hours"
MARATHON_SPOTLIGHT_NOTE_KEY = "marathon_spotlight_note_template"
MARATHON_SPOTLIGHT_FOLLOWS_KEY = "marathon_spotlight"
MARATHON_SPOTLIGHT_LEAD_MINUTES_KEY = "marathon_spotlight_lead_minutes"
MARATHON_SPOTLIGHT_TAIL_KEY = "marathon_spotlight_tail_minutes"
MARATHON_PING_ROLE_DEFAULT_KEY = "marathon_ping_role_default"
MARATHON_PING_ROLE_ON_SAID_KEY = "marathon_ping_role_on_said"
MARATHON_PING_ROLE_OFF_SAID_KEY = "marathon_ping_role_off_said"
MARATHON_PING_ROLE_SAME_KEY = "marathon_ping_role_same_said"
MARATHON_PING_ROLE_LINE_ON_KEY = "marathon_ping_role_line_on"
MARATHON_PING_ROLE_LINE_OFF_KEY = "marathon_ping_role_line_off"
MARATHON_ROLE_PINGS_KEY = "marathon_role_pings"
MARATHON_ROLE_PING_LINE_ON_KEY = "marathon_role_ping_line_on"
MARATHON_ROLE_PING_LINE_KEY_OFF_KEY = "marathon_role_ping_line_key_off"
MARATHON_ROLE_PING_LINE_ANNOUNCEMENTS_OFF_KEY = "marathon_role_ping_line_nobody_announced"
MARATHON_ROLE_PING_LINE_REHEARSAL_KEY = "marathon_role_ping_line_rehearsal"
MARATHON_ROLE_PING_LINE_UNSET_KEY = "marathon_role_ping_line_unset"
MARATHON_ROLE_PING_LINE_GONE_KEY = "marathon_role_ping_line_gone"
MARATHON_ROLE_PING_LINE_NOT_MENTIONABLE_KEY = "marathon_role_ping_line_not_mentionable"
MARATHON_ARCHIVE_AFTER_DAYS_KEY = "marathon_archive_after_days"
MARATHON_ARCHIVED_WORD_KEY = "marathon_archived_word"
MARATHON_ARCHIVE_QUESTION_KEY = "marathon_archive_question"
MARATHON_ARCHIVED_SAID_KEY = "marathon_archived_said"
MARATHON_RESTORE_QUESTION_KEY = "marathon_restore_question"
MARATHON_RESTORED_SAID_KEY = "marathon_restored_said"
MARATHON_RESTORE_TAKEN_KEY = "marathon_restore_taken"
MARATHON_NOT_ARCHIVED_KEY = "marathon_not_archived"
MARATHON_INBOX_CHANNEL_KEY = "marathon_inbox_channel_id"
MARATHON_INBOX_THREAD_NAME_KEY = "marathon_inbox_thread_name"
MARATHON_INBOX_OPENING_KEY = "marathon_inbox_opening"
MARATHON_THREAD_CHANNEL_KEY = "marathon_thread_channel_id"
MARATHON_THREAD_NAME_KEY = "marathon_thread_name_template"
MARATHON_THREAD_OPENING_KEY = "marathon_thread_opening_template"
MARATHON_TRACK_MAKES_THREAD_KEY = "marathon_track_makes_thread"
MARATHON_AUTO_TRACK_DEFAULT_KEY = "marathon_auto_track_default"
MARATHON_INBOX_LABEL_WHEN_KEY = "marathon_inbox_label_when"
MARATHON_INBOX_LABEL_SOURCE_KEY = "marathon_inbox_label_source"
MARATHON_INBOX_LABEL_CHANNEL_KEY = "marathon_inbox_label_channel"
MARATHON_INBOX_LABEL_SCHEDULE_KEY = "marathon_inbox_label_schedule"
MARATHON_INBOX_LABEL_EVENT_KEY = "marathon_inbox_label_event"
MARATHON_INBOX_LABEL_STATE_KEY = "marathon_inbox_label_state"
MARATHON_INBOX_STATE_FOUND_KEY = "marathon_inbox_state_found"
MARATHON_INBOX_STATE_TRACKED_KEY = "marathon_inbox_state_tracked"
MARATHON_INBOX_STATE_IGNORED_KEY = "marathon_inbox_state_ignored"
MARATHON_INBOX_BUTTON_TRACK_KEY = "marathon_inbox_button_track"
MARATHON_INBOX_BUTTON_IGNORE_KEY = "marathon_inbox_button_ignore"
MARATHON_INBOX_BUTTON_UNTRACK_KEY = "marathon_inbox_button_untrack"
MARATHON_INBOX_BUTTON_ANYWAY_KEY = "marathon_inbox_button_track_anyway"
MARATHON_INBOX_BUTTON_SITE_KEY = "marathon_inbox_button_open_site"
MARATHON_INBOX_BUTTON_THREAD_KEY = "marathon_inbox_button_open_thread"
MARATHON_INBOX_NO_DATES_KEY = "marathon_inbox_no_dates"
MARATHON_INBOX_NO_SCHEDULE_KEY = "marathon_inbox_schedule_none"
MARATHON_INBOX_SCHEDULE_KEY = "marathon_inbox_schedule_runs"
MARATHON_INBOX_NO_CHANNEL_KEY = "marathon_inbox_no_channel"
MARATHON_INBOX_OPTED_OUT_KEY = "marathon_inbox_channel_opted_out"
MARATHON_TRACK_REFUSED_KEY = "marathon_track_refused"
MARATHON_NOT_TRACKED_KEY = "marathon_not_tracked"
MARATHON_TRACKED_SAID_KEY = "marathon_tracked_said"
MARATHON_UNTRACKED_SAID_KEY = "marathon_untracked_said"
MARATHON_IGNORED_SAID_KEY = "marathon_ignored_said"
MARATHON_UNIGNORED_SAID_KEY = "marathon_unignored_said"
MARATHON_INBOX_AUTO_WHO_KEY = "marathon_inbox_auto_who"
MARATHON_LINK_CHANGED_SAID_KEY = "marathon_link_changed_said"
MARATHON_LINK_SAME_KEY = "marathon_link_same"
MARATHON_LINK_TAKEN_KEY = "marathon_link_taken"
MARATHON_LINK_UNREADABLE_KEY = "marathon_link_unreadable"
MARATHON_FEED_SEARCH_MOVE_KEY = "marathon_feed_search_move"
MARATHON_FEED_SEARCH_TITLE_KEY = "marathon_feed_search_title"
MARATHON_FEED_WORDS_LABEL_KEY = "marathon_feed_words_label"
MARATHON_FEED_OWNER_LABEL_KEY = "marathon_feed_owner_label"
MARATHON_FEED_SEARCH_LINE_KEY = "marathon_feed_search_line"
MARATHON_FEED_OWNER_LINE_KEY = "marathon_feed_owner_line"
MARATHON_FEED_WORDS_SAID_KEY = "marathon_feed_words_said"
MARATHON_FEED_WORDS_CLEARED_KEY = "marathon_feed_words_cleared"
MARATHON_FEED_OWNER_SAID_KEY = "marathon_feed_owner_said"
MARATHON_FEED_OWNER_CLEARED_KEY = "marathon_feed_owner_cleared"
MARATHON_FEED_SEARCH_REFUSED_KEY = "marathon_feed_search_refused"
MARATHON_FEED_WORDS_BAD_KEY = "marathon_feed_words_bad"
MARATHON_FEED_OWNER_BAD_KEY = "marathon_feed_owner_bad"
MARATHON_INBOX_POSTED_SAID_KEY = "marathon_inbox_posted_said"
MARATHON_INBOX_ALREADY_KEY = "marathon_inbox_already"
MARATHON_INBOX_POST_OFF_KEY = "marathon_inbox_post_off"
MARATHON_INBOX_POST_FAILED_KEY = "marathon_inbox_post_failed"
MARATHON_CONTROLS_EVENT_ON_KEY = "marathon_controls_event_on"
MARATHON_CONTROLS_EVENT_OFF_KEY = "marathon_controls_event_off"
MARATHON_CONTROLS_NO_CHANNEL_KEY = "marathon_controls_no_channel"
MARATHON_CONTROLS_KEPT_REFUSED_KEY = "marathon_controls_kept_refused"
MARATHON_CONTROLS_NO_END_KEY = "marathon_controls_no_end"
MARATHON_CONTROLS_STARTED_KEY = "marathon_controls_started_said"
MARATHON_CONTROLS_ALREADY_ON_KEY = "marathon_controls_already_on"
MARATHON_CONTROLS_WAITS_KEY = "marathon_controls_waits_said"
MARATHON_CONTROLS_CANCELLED_KEY = "marathon_controls_cancelled_said"
MARATHON_CONTROLS_CANNOT_WAIT_KEY = "marathon_controls_cannot_wait"
MARATHON_CONTROLS_PING_ON_KEY = "marathon_controls_ping_on"
MARATHON_CONTROLS_PING_OFF_KEY = "marathon_controls_ping_off"
MARATHON_HOST_EVENT_TITLE_KEY = "marathon_host_event_title_template"
MARATHON_HOST_EVENT_DESCRIPTION_KEY = "marathon_host_event_description_template"
MARATHON_HOST_EVENT_FIELDS = ("member", "marathon", "games", "runs")
MARATHON_HOST_HIGHLIGHTS_KEY = "marathon_host_highlights"
MARATHON_ANNOUNCEMENTS_DEFAULT_KEY = "marathon_announcements_default"
MARATHON_CONTROLS_ANNOUNCE_ON_KEY = "marathon_controls_announcements_on"
MARATHON_CONTROLS_ANNOUNCE_OFF_KEY = "marathon_controls_announcements_off"
MARATHON_ANNOUNCEMENTS_ON_SAID_KEY = "marathon_runner_announcements_on_said"
MARATHON_ANNOUNCEMENTS_OFF_SAID_KEY = "marathon_runner_announcements_off_said"
MARATHON_PUBLIC_BUTTON_OPT_OUT_KEY = "marathon_public_button_opt_out"
MARATHON_PUBLIC_BUTTON_OPT_IN_KEY = "marathon_public_button_opt_in"
MARATHON_ANNOUNCE_OPTED_OUT_SAID_KEY = "marathon_announce_opted_out_said"
MARATHON_ANNOUNCE_OPTED_IN_SAID_KEY = "marathon_announce_opted_in_said"
MARATHON_HOST_ANNOUNCEMENTS_DEFAULT_KEY = "marathon_host_announcements_default"
MARATHON_CONTROLS_HOST_ANNOUNCE_ON_KEY = "marathon_controls_host_announcements_on"
MARATHON_CONTROLS_HOST_ANNOUNCE_OFF_KEY = "marathon_controls_host_announcements_off"
MARATHON_HOST_ANNOUNCEMENTS_ON_SAID_KEY = "marathon_host_announcements_on_said"
MARATHON_HOST_ANNOUNCEMENTS_OFF_SAID_KEY = "marathon_host_announcements_off_said"
MARATHON_MENTION_PEOPLE_KEY = "marathon_mention_people"
MARATHON_ANNOUNCE_BUTTON_RUN_OUT_KEY = "marathon_announce_button_run_out"
MARATHON_ANNOUNCE_BUTTON_RUN_IN_KEY = "marathon_announce_button_run_in"
MARATHON_ANNOUNCE_BUTTON_RUN_DEFAULT_KEY = "marathon_announce_button_run_default"
MARATHON_ANNOUNCE_BUTTON_PLAIN_KEY = "marathon_announce_button_plain"
MARATHON_ANNOUNCE_BUTTON_MENTION_KEY = "marathon_announce_button_mention"
MARATHON_ANNOUNCE_PICK_KEY = "marathon_announce_pick"
MARATHON_PEOPLE_BUTTON_SPOTLIGHT_KEY = "marathon_people_button_spotlight"
MARATHON_PEOPLE_BUTTON_UNSPOTLIGHT_KEY = "marathon_people_button_unspotlight"
MARATHON_PEOPLE_BUTTON_UNLINK_KEY = "marathon_people_button_unlink"
MARATHON_PEOPLE_BUTTON_LINK_NEAR_KEY = "marathon_people_button_link_near"
MARATHON_PEOPLE_BUTTON_TWITCH_KEY = "marathon_people_button_twitch"
MARATHON_PEOPLE_BUTTON_BACK_KEY = "marathon_people_button_back"
MARATHON_ANNOUNCE_STATE_LINE_KEY = "marathon_announce_state_line"
MARATHON_ANNOUNCE_STATE_YES_KEY = "marathon_announce_state_yes"
MARATHON_ANNOUNCE_STATE_NO_KEY = "marathon_announce_state_no"
MARATHON_ANNOUNCE_WHY_DEFAULT_KEY = "marathon_announce_why_default"
MARATHON_ANNOUNCE_WHY_RUN_KEY = "marathon_announce_why_run"
MARATHON_ANNOUNCE_WHY_MARATHON_KEY = "marathon_announce_why_marathon"
MARATHON_ANNOUNCE_WHY_OFF_KEY = "marathon_announce_why_runners_off"
MARATHON_ANNOUNCE_WHY_HOSTS_OFF_KEY = "marathon_announce_why_hosts_off"
MARATHON_ANNOUNCE_STATE_PLAIN_KEY = "marathon_announce_state_plain"
MARATHON_ANNOUNCE_RUN_IN_SAID_KEY = "marathon_announce_run_in_said"
MARATHON_ANNOUNCE_RUN_OUT_SAID_KEY = "marathon_announce_run_out_said"
MARATHON_ANNOUNCE_RUN_DEFAULT_SAID_KEY = "marathon_announce_run_default_said"
MARATHON_MENTION_PLAIN_SAID_KEY = "marathon_mention_plain_said"
MARATHON_MENTION_ON_SAID_KEY = "marathon_mention_on_said"
MARATHON_SPOTLIGHT_HOST_NOTE_KEY = "marathon_spotlight_host_note_template"
MARATHON_REMINDER_CHANNEL_KEY = "marathon_reminder_channel_id"
MARATHON_PUBLIC_REMINDERS_KEY = "marathon_public_reminders"
MARATHON_THREAD_REMINDERS_KEY = "marathon_thread_reminders"
MARATHON_PUBLIC_REMINDER_TEMPLATE_KEY = "marathon_public_reminder_template"
MARATHON_PUBLIC_CHANNEL_KEY = "marathon_public_channel_id"
MARATHON_PUBLIC_TEMPLATE_KEY = "marathon_public_template"
MARATHON_NEAR_MISS_POSTS_KEY = "marathon_near_miss_posts"
MARATHON_NEAR_MISS_POST_KEY = "marathon_near_miss_post"
MARATHON_NEAR_MISS_HERE_KEY = "marathon_near_miss_link_here"
MARATHON_NEAR_MISS_EVERYWHERE_KEY = "marathon_near_miss_link_everywhere"
MARATHON_NEAR_MISS_NOT_KEY = "marathon_near_miss_not_them"
MARATHON_NEAR_MISS_LINKED_KEY = "marathon_near_miss_linked"
MARATHON_NEAR_MISS_LINKED_EVERYWHERE_KEY = "marathon_near_miss_linked_everywhere"
MARATHON_NEAR_MISS_DISMISSED_KEY = "marathon_near_miss_dismissed"
MARATHON_NEAR_MISS_DISMISSED_SAID_KEY = "marathon_near_miss_dismissed_said"
MARATHON_NEAR_MISS_GONE_KEY = "marathon_near_miss_gone"
MARATHON_NEAR_MISS_ANSWERED_KEY = "marathon_near_miss_answered"
MARATHON_NEAR_MISS_FIELDS = ("runner", "member", "username", "display_name", "marathon")
MARATHON_NEAR_MISS_DONE_FIELDS = (*MARATHON_NEAR_MISS_FIELDS, "staff")
MARATHON_PUBLIC_REMOVED_KEY = "marathon_public_removed"
MARATHON_PUBLIC_FIELDS = (
    "runner",
    "mention",
    "game",
    "category",
    "part",
    "when",
    "relative",
    "url",
    "marathon",
    "state",
)
MARATHON_PUBLIC_DONE_TEMPLATE_KEY = "marathon_public_done_template"
MARATHON_PUBLIC_DAY_TODAY_KEY = "marathon_public_day_today"
MARATHON_PUBLIC_DAY_EARLIER_KEY = "marathon_public_day_earlier"
MARATHON_PUBLIC_DONE_FIELDS = (*MARATHON_PUBLIC_FIELDS, "day")
MARATHON_THREAD_FIELDS = ("marathon", "channel", "when")
MARATHON_OPENING_FIELDS = ("marathon", "who", "url", "channel", "when")
MARATHON_CHANNEL_PING_MODE_DEFAULT_KEY = "marathon_channel_ping_mode_default"
MARATHON_CHANNEL_PING_HELP_KEY = "marathon_channel_ping_help"
MARATHON_BOARD_TEMPLATE_KEY = "marathon_board_template"
MARATHON_BOARD_LINE_KEY = "marathon_board_line_template"
MARATHON_BOARD_EMPTY_KEY = "marathon_board_empty_line"
MARATHON_RUNNER_POST_TEMPLATE_KEY = "marathon_runner_post_template"
MARATHON_RUNNER_POST_UNLISTED_KEY = "marathon_runner_post_unlisted"
MARATHON_REMINDER_TEMPLATE_KEY = "marathon_reminder_template"
MARATHON_REMINDER_DROPPED_TEMPLATE_KEY = "marathon_reminder_dropped_template"
MARATHON_LIVE_TEMPLATE_KEY = "marathon_live_template"
MARATHON_DONE_TEMPLATE_KEY = "marathon_done_template"
MARATHON_PART_RUNNER_KEY = "marathon_part_runner"
MARATHON_PART_HOST_KEY = "marathon_part_host"
MARATHON_PART_COMMENTATOR_KEY = "marathon_part_commentator"
MARATHON_PART_RUNNER_DONE_KEY = "marathon_part_runner_done"
MARATHON_PART_HOST_DONE_KEY = "marathon_part_host_done"
MARATHON_PART_COMMENTATOR_DONE_KEY = "marathon_part_commentator_done"
MARATHON_STATE_UPCOMING_KEY = "marathon_state_upcoming"
MARATHON_STATE_LIVE_KEY = "marathon_state_live"
MARATHON_STATE_DONE_KEY = "marathon_state_done"
MARATHON_STATE_DROPPED_KEY = "marathon_state_dropped"
MARATHON_UNKNOWN_SITE_KEY = "marathon_unknown_site"
MARATHON_ALREADY_ADDED_KEY = "marathon_already_added"
MARATHON_COULD_NOT_READ_KEY = "marathon_could_not_read"
MARATHON_NO_RUNS_YET_KEY = "marathon_no_runs_yet"
MARATHON_SUGGEST_NEXT_KEY = "marathon_suggest_next"
MARATHON_NEXT_TEMPLATE_KEY = "marathon_next_template"
MARATHON_NEXT_NONE_TEMPLATE_KEY = "marathon_next_none_template"
MARATHON_NEXT_ADDED_TEMPLATE_KEY = "marathon_next_added_template"
MARATHON_EVENT_MODE_DEFAULT_KEY = "marathon_event_mode_default"
MARATHON_EVENT_MODES = ("none", "marathon", "runs", "both")
MARATHON_RUN_EVENT_TITLE_KEY = "marathon_run_event_title_template"
MARATHON_RUN_EVENT_DESCRIPTION_KEY = "marathon_run_event_description_template"
MARATHON_RUN_EVENTS_REVIEWED_KEY = "marathon_run_events_reviewed"
MARATHON_RUN_EVENT_CANCEL_ON_LEAVE_KEY = "marathon_run_event_cancel_on_leave"
MARATHON_SHOUT_WHEN_RUN_HAS_EVENT_KEY = "marathon_shout_when_run_has_event"
MARATHON_NOTICE_HOME_KEY = "marathon_notice_home"
MARATHON_NOTICE_HOMES = ("events", "staff")
MARATHON_NOTICE_TITLE_KEY = "marathon_notice_title_template"
MARATHON_RUN_EVENT_FIELDS = ("member", "game", "category", "marathon")
MARATHON_EVENT_DESCRIPTION_KEY = "marathon_event_description_template"
MARATHON_FEEDS_KEY = "marathon_feeds"
MARATHON_FEED_HOURS_KEY = "marathon_feed_hours"
MARATHON_FEED_ACTION_KEY = "marathon_feed_action_default"
MARATHON_FEED_RECENT_KEY = "marathon_feed_recent_days"
MARATHON_LADYARCADERS_FLOOR_KEY = "marathon_ladyarcaders_floor"
MARATHON_HOTFIX_SHOWS_KEY = "marathon_hotfix_shows"
MARATHON_HOTFIX_SHOWS = "GDQueer"
MARATHON_HOTFIX_SHOWS_MAX = 20
MARATHON_HOTFIX_SHOW_LENGTH = 60
MARATHON_HOTFIX_TRACK_PEOPLE_KEY = "marathon_hotfix_track_people"
MARATHON_HOTFIX_VIEWER_URL_KEY = "marathon_hotfix_viewer_url"
MARATHON_HOTFIX_VIEWER_URL = "https://ogndrahcir.github.io/ScheduleViewer/"
MARATHON_HOTFIX_VIEWER_URL_LENGTH = 300
MARATHON_HOTFIX_VIEWER_INNER = (".internal", ".local", ".localhost", ".lan", ".home", ".corp")
MARATHON_HOTFIX_OVERLAY_DEFAULT_KEY = "marathon_hotfix_overlay_default"
MARATHON_CONTROLS_TRACKER_KEY = "marathon_controls_tracker"
MARATHON_CONTROLS_SPOTLIGHT_FOLLOW_ON_KEY = "marathon_controls_spotlight_follow_on"
MARATHON_CONTROLS_SPOTLIGHT_FOLLOW_OFF_KEY = "marathon_controls_spotlight_follow_off"
MARATHON_CONTROLS_SPOTLIGHT_UNTIL_LINE_KEY = "marathon_controls_spotlight_until_line"
MARATHON_CONTROLS_SPOTLIGHT_STARTS_LINE_KEY = "marathon_controls_spotlight_starts_line"
MARATHON_CONTROLS_SPOTLIGHT_KEPT_LINE_KEY = "marathon_controls_spotlight_kept_line"
MARATHON_CONTROLS_SPOTLIGHT_NONE_LINE_KEY = "marathon_controls_spotlight_none_line"
MARATHON_CONTROLS_SPOTLIGHT_RUNNING_LINE_KEY = "marathon_controls_spotlight_running_line"
MARATHON_CONTROLS_FOLLOW_OFF_RUNNING_KEY = "marathon_controls_follow_off_running_said"
MARATHON_HOST_EVENTS_GONE_KEY = "marathon_host_events_gone_said"
MARATHON_BAF_EVENT_STAFF_SET_KEY = "marathon_baf_event_staff_set_line"
MARATHON_CONTROLS_ARCHIVE_KEY = "marathon_controls_archive"
MARATHON_RUN_EVENT_UNLINK_KEY = "marathon_run_event_unlink"
MARATHON_BAF_EVENT_NAMES_KEY = "marathon_baf_event_names"
MARATHON_BAF_EVENT_MIN_RUNS_KEY = "marathon_baf_event_min_runs"
MARATHON_BAF_EVENT_ASK_PERCENT_KEY = "marathon_baf_event_ask_percent"
MARATHON_BAF_EVENT_PING_MINUTES_KEY = "marathon_baf_event_ping_minutes"
MARATHON_BAF_EVENT_ASK_ROLE_KEY = "marathon_baf_event_ask_role_id"
MARATHON_BAF_EVENT_ASK_TEXT_KEY = "marathon_baf_event_question"
MARATHON_BAF_EVENT_ASK_YES_KEY = "marathon_baf_event_ask_yes"
MARATHON_BAF_EVENT_ASK_NO_KEY = "marathon_baf_event_ask_no"
MARATHON_BAF_EVENT_ANSWERED_KEY = "marathon_baf_event_answered"
MARATHON_BAF_EVENT_WORD_YES_KEY = "marathon_baf_event_word_yes"
MARATHON_BAF_EVENT_WORD_NO_KEY = "marathon_baf_event_word_no"
MARATHON_BAF_EVENT_WORD_UNSURE_KEY = "marathon_baf_event_word_unsure"
MARATHON_BAF_EVENT_WORD_FOLLOW_KEY = "marathon_baf_event_word_follow"
MARATHON_BAF_EVENT_SET_SAID_KEY = "marathon_baf_event_set_said"
MARATHON_BAF_EVENT_SAME_SAID_KEY = "marathon_baf_event_same_said"
MARATHON_BAF_EVENT_LINE_KEY = "marathon_baf_event_answer_line"
MARATHON_BAF_EVENT_REASON_STAFF_KEY = "marathon_baf_event_reason_staff"
MARATHON_BAF_EVENT_REASON_NAME_KEY = "marathon_baf_event_reason_name"
MARATHON_BAF_EVENT_REASON_ALL_RUNS_KEY = "marathon_baf_event_reason_all_runs"
MARATHON_BAF_EVENT_REASON_SHARE_KEY = "marathon_baf_event_reason_share"
MARATHON_BAF_EVENT_REASON_FEW_RUNS_KEY = "marathon_baf_event_reason_few_runs"
MARATHON_BAF_EVENT_REASON_MIXED_KEY = "marathon_baf_event_reason_mixed"
MARATHON_BAF_EVENT_REASON_NO_RUNS_KEY = "marathon_baf_event_reason_no_runs"
MARATHON_BAF_EVENT_PING_WILL_KEY = "marathon_baf_event_ping_will"
MARATHON_BAF_EVENT_PING_DONE_KEY = "marathon_baf_event_ping_done"
MARATHON_BAF_EVENT_PING_NONE_KEY = "marathon_baf_event_ping_none"
MARATHON_BAF_EVENT_PING_FALLBACK_KEY = "marathon_baf_event_ping_fallback"
MARATHON_BAF_EVENT_REASON_LEADS_KEY = "marathon_baf_event_reason_answered"
MARATHON_BAF_EVENT_PING_UNCONFIRMED_KEY = "marathon_baf_event_ping_unconfirmed"
MARATHON_BAF_EVENT_PING_NO_RUN_KEY = "marathon_baf_event_ping_no_baf_run"
MARATHON_BAF_EVENT_PING_NOBODY_KEY = "marathon_baf_event_ping_nobody"
MARATHON_BAF_EVENT_ASK_PENDING_KEY = "marathon_baf_event_ask_pending"
MARATHON_BAF_EVENT_ASK_FAILED_KEY = "marathon_baf_event_ask_failed"
MARATHON_BAF_EVENT_ASK_NOWHERE_KEY = "marathon_baf_event_ask_nowhere"
MARATHON_BAF_EVENT_DAY_LINE_KEY = "marathon_baf_event_day_line"
MARATHON_BAF_EVENT_REASON_ACTED_KEY = "marathon_baf_event_reason_acted"
MARATHON_BAF_EVENT_CLEARED_KEY = "marathon_baf_event_cleared"
MARATHON_BAF_EVENT_CLEARED_SAID_KEY = "marathon_baf_event_cleared_said"
MARATHON_BAF_EVENT_NO_ANSWER_SAID_KEY = "marathon_baf_event_no_answer_said"
MARATHON_CONTROLS_BAF_SAID_YES_KEY = "marathon_controls_baf_said_yes"
MARATHON_CONTROLS_BAF_SAID_NO_KEY = "marathon_controls_baf_said_no"
MARATHON_CONTROLS_BAF_SAID_UNSURE_KEY = "marathon_controls_baf_said_unsure"
MARATHON_CONTROLS_BAF_STAFF_YES_KEY = "marathon_controls_baf_staff_yes"
MARATHON_CONTROLS_BAF_STAFF_NO_KEY = "marathon_controls_baf_staff_no"
MARATHON_CONTROLS_BAF_ANSWERED_YES_KEY = "marathon_controls_baf_answered_yes"
MARATHON_CONTROLS_BAF_ANSWERED_NO_KEY = "marathon_controls_baf_answered_no"
MARATHON_CONTROLS_BAF_NAMED_KEY = "marathon_controls_baf_named"
MARATHON_CONTROLS_BAF_RUNS_KEY = "marathon_controls_baf_runs"
MARATHON_BAF_EVENT_NAMES_MAX = 20
MARATHON_BAF_EVENT_NAME_LENGTH = 60
MARATHON_BAD_BAF_NAMES = (
    "**{given}** is not a list of show names. Give one to {most} names, up to {longest} "
    "characters each, separated by commas — for example `Black in a Flash`."
)
MARATHON_OVERLAY_ON_SAID_KEY = "marathon_overlay_on_said"
MARATHON_OVERLAY_OFF_SAID_KEY = "marathon_overlay_off_said"
MARATHON_HOTFIX_HOSTS_TEMPLATE_KEY = "marathon_hotfix_hosts_template"
MARATHON_HOTFIX_RUNS_TEMPLATE_KEY = "marathon_hotfix_runs_template"
MARATHON_HOTFIX_BECAUSE_FIELDS = ("people", "show")
MARATHON_FEED_ADDED_TEMPLATE_KEY = "marathon_feed_added_template"
MARATHON_FEED_SUGGEST_TEMPLATE_KEY = "marathon_feed_suggest_template"
MARATHON_FEED_ACTIONS = ("add", "suggest")
MARATHON_FEED_NOTICE_WHEN_KEY = "marathon_feed_notice_when"
MARATHON_FEED_NOTICE_WHENS = ("published", "added")
MARATHON_FEED_FIELDS = ("feed", "event", "when", "relative", "url", "channel")
MARATHON_EVENT_FIELDS = ("marathon", "channel")
MARATHON_NEXT_FIELDS = ("marathon", "next", "when", "relative", "url")
MARATHON_REMINDER_MINUTES = "120, 15"
MARATHON_MARKS_MAX = 6
MARATHON_MARK_MAX_MINUTES = 1440
MARATHON_BOARD_FIELDS = ("marathon", "count", "starts", "ends", "url")
MARATHON_LINE_FIELDS = ("member", "game", "category", "when", "relative", "part", "state")
MARATHON_RUNNER_POST_FIELDS = (
    "runner",
    "mention",
    "game",
    "category",
    "part",
    "when",
    "relative",
    "url",
    "marathon",
    "state",
)
MARATHON_REMINDER_FIELDS = (
    "member",
    "game",
    "category",
    "in",
    "when",
    "url",
    "marathon",
    "part",
)
MARATHON_REMINDER_DROPPED_FIELDS = (*MARATHON_REMINDER_FIELDS, "state")
MARATHON_LIVE_FIELDS = ("member", "game", "category", "url", "marathon", "part")
MARATHON_UNKNOWN_FIELD = (
    "`{{{found}}}` is not something Black Bloc can fill in, so nothing was changed. This "
    "marathon post may stand in for {allowed}; write any other braces out as words."
)
MARATHON_BAD_SHOWS = (
    "**{given}** names no Hotfix show, so nothing was changed. Write one to {most} show names "
    "as the Show column spells them, up to {longest} characters each, separated by commas — for "
    "example `GDQueer`. To stop the Hotfix feed, pause it instead."
)
MARATHON_BAD_VIEWER = (
    "**{given}** is not a page Black Bloc can read, so nothing was changed. Give one https link "
    "to a public site (no port, no sign-in, no address made of numbers), at most {longest} "
    "characters — or leave it blank to turn the Hotfix schedule viewer off."
)
MARATHON_BAD_RETRO = (
    "**{given}** is not a Twitch category name, so nothing was changed. Write the category a run "
    "with no category of its own is played under, up to {longest} characters — for example "
    "`Retro`."
)
MARATHON_BAD_MARKS = (
    "**{given}** is not a list Black Bloc can remind on, so nothing was changed. Write one to "
    "{most} whole numbers of minutes between 1 and {limit}, separated by commas — for example "
    "`120, 15`."
)
MARATHON_SETTINGS: dict[str, tuple[str, Any, str]] = {
    MARATHON_HOST_HIGHLIGHTS_KEY: (
        "bool",
        True,
        "whether each BaF host of a marathon is posted like a BaF runner, "
        "once per host block (the runs they host in a row, through runs with no host listed): "
        "the public reminder (marathon_public_reminder_template, with marathon_part_host) at "
        "every marathon_reminder_minutes mark before the block's first run in "
        "marathon_reminder_channel_id while marathon_public_reminders is on, and the public "
        "highlight (marathon_public_template) when the block goes live. Both follow the "
        "marathon's Host announcements switch and each host's opt-out. A host still never "
        "makes a run a BaF run. on by default",
    ),
    MARATHON_ANNOUNCEMENTS_DEFAULT_KEY: (
        "bool",
        True,
        "whether a marathon announces its BaF RUNNERS publicly — each run's reminders and "
        "highlight — when its own Runner announcements switch follows this setting. Hosts "
        "follow Host announcements; neither switch is over the other. A run's own answer for a "
        "runner beats this switch either way. on by default",
    ),
    MARATHON_HOST_ANNOUNCEMENTS_DEFAULT_KEY: (
        "bool",
        False,
        "whether a marathon announces its BaF HOSTS publicly — a host block's reminders and "
        "highlight — when its own Host announcements switch follows this setting. Runners "
        "follow Runner announcements; neither switch is over the other. A run's own answer for a "
        "host beats this switch either way. off by default",
    ),
    MARATHON_MENTION_PEOPLE_KEY: (
        "bool",
        True,
        "whether a public marathon post writes a BaF person as an @ (drawn, never notified). "
        "Off, every public post writes their name as the schedule has it, as plain text, "
        "instead; one person on one marathon can be set the other way from a run's post. on "
        "by default",
    ),
    MARATHON_MODE_KEY: (
        "enum",
        "shadow",
        "whether marathon schedules post at all. off reads nothing and posts nothing; shadow — "
        "the default — posts the board, the reminders and the shoutouts where "
        "shadow_channel_id points with the rehearsal note; on posts them in "
        "marathon_channel_id",
    ),
    MARATHON_CHANNEL_KEY: (
        "channel",
        None,
        "where the marathon board, the reminders and the shoutouts go. Blank uses the go-live "
        "channel",
    ),
    MARATHON_POLL_MINUTES_KEY: (
        "int",
        30,
        "minutes between reads of a marathon's schedule while it is near — from "
        "marathon_lead_days before it starts until a day after it ends. 30 by default; a "
        "marathon's own row can say otherwise",
    ),
    MARATHON_FAR_POLL_HOURS_KEY: (
        "int",
        24,
        "hours between reads of a schedule that is still weeks away. 24 by default",
    ),
    MARATHON_LEAD_DAYS_KEY: (
        "int",
        7,
        "how many days before a marathon starts its schedule counts as near and is read every "
        "marathon_poll_minutes. 7 by default",
    ),
    MARATHON_MOVE_MINUTES_KEY: (
        "int",
        5,
        "how many minutes a run's start must shift before it counts as moved — a moved run of "
        "ours is logged as important with the old and the new time. 5 by default",
    ),
    MARATHON_TITLE_CONFIRMS_KEY: (
        "bool",
        True,
        "whether the marathon channel's live title decides which run is on now. on by default; "
        "with this and marathon_category_confirms off the schedule's clock decides alone",
    ),
    MARATHON_CATEGORY_CONFIRMS_KEY: (
        "bool",
        True,
        "whether the marathon channel's Twitch category decides which run is on now, beside the "
        "title — both on one run is certain, and a direct category wins when they disagree. on "
        "by default",
    ),
    MARATHON_RETRO_CATEGORY_KEY: (
        "text",
        MARATHON_RETRO_CATEGORY,
        "the Twitch category a run with no category of its own is played under — the channel "
        "in this category stands for such a run. `Retro` by default; capitals do not matter",
    ),
    MARATHON_SETUP_MINUTES_KEY: (
        "int",
        MARATHON_SETUP_MINUTES,
        "minutes of setup between one run and the next, for a schedule that gives no start time "
        "per run (GDQ Hotfix) — each run is predicted at the start of the one before it, plus "
        "its estimate, plus this. 7 by default; 0 stacks the estimates with nothing between",
    ),
    MARATHON_EARLY_START_KEY: (
        "int",
        MARATHON_EARLY_START_MINUTES,
        "minutes before a show-day's first planned start that the stream's title or category may "
        "call a run live — a channel set up for the show earlier than that is waited out, and the "
        "day's times stay where the schedule put them. 10 by default; 0 believes the stream at "
        "once",
    ),
    MARATHON_LATE_GRACE_KEY: (
        "int",
        90,
        "minutes a run may sit past its scheduled start with no sign on the stream before the "
        "schedule alone calls it live — the run before it is probably running long. 90 by "
        "default",
    ),
    MARATHON_MATCH_HOSTS_KEY: (
        "bool",
        True,
        "whether a host or a commentator from BaF counts as BaF, not only a runner. "
        "on by default",
    ),
    MARATHON_HOSTS_COUNT_AS_OURS_KEY: (
        "bool",
        False,
        "whether a run a BaF host hosts counts as a BaF run — its runner post, reminders, "
        "shoutout and highlight — when nobody from BaF runs it. Off, a BaF host is shown, "
        "announced per host block and can be spotlit, but only a BaF runner makes a run ours. "
        "off by default",
    ),
    MARATHON_REMINDER_MINUTES_KEY: (
        "text",
        MARATHON_REMINDER_MINUTES,
        "minutes before a BaF run that a reminder is posted, separated by commas; "
        "`120, 15` by default. marathon_ping_minutes is always one of them",
    ),
    MARATHON_PING_MINUTES_KEY: (
        "int",
        15,
        "the one reminder that pings: this many minutes before a BaF run, the member's own "
        "ping role and the marathon channel's ping role are mentioned, and the public copy "
        "mentions the Marathon role (marathon_role_pings). 15 by default; 0 pings at the "
        "scheduled start",
    ),
    MARATHON_REMINDER_PINGS_KEY: (
        "bool",
        True,
        "whether the marathon_ping_minutes reminder mentions any role at all. on by default",
    ),
    MARATHON_LIVE_PINGS_KEY: (
        "bool",
        False,
        "whether the shoutout when a BaF run goes live pings too. off by default — the ping "
        "already went out marathon_ping_minutes before",
    ),
    MARATHON_REMINDER_STALE_KEY: (
        "int",
        30,
        "minutes past its moment after which a reminder is skipped and logged instead of posted "
        "late. 30 by default",
    ),
    MARATHON_REMINDER_ON_MOVE_KEY: (
        "enum",
        "edit",
        "what happens to a reminder already posted when its run (or its host block) moves: "
        "edit rewrites that post in place with the new time — any size of move, earlier or "
        "later, in the staff thread and the public channel alike — pings nobody, and never "
        "posts that mark a second time; a run taken off the schedule gets "
        "marathon_reminder_dropped_template. repost leaves the old post as it was and, when the "
        "run moves later by marathon_move_minutes or more, posts the reminder again at the new "
        "time (pinging again at marathon_ping_minutes). edit by default",
    ),
    MARATHON_REMINDER_EDIT_LIMIT_KEY: (
        "int",
        MARATHON_REMINDER_EDIT_LIMIT,
        "how many posted reminders one marathon may rewrite per minute while "
        "marathon_reminder_on_move is edit — when a whole day shifts, the soonest runs are "
        "corrected first and the rest follow a minute later. 10 by default",
    ),
    MARATHON_TRACKER_REFRESH_KEY: (
        "int",
        MARATHON_TRACKER_REFRESH,
        "seconds between one read and the next on a marathon's Marathon tracker page on the "
        "site, while the tab is open and showing — the page re-reads itself so a run going "
        "live, finishing or moving shows without a reload. 30 by default",
    ),
    MARATHON_PIN_BOARD_KEY: (
        "bool",
        True,
        "whether a marathon's board is pinned while the marathon is on; it comes down a day "
        "after the marathon ends. on by default",
    ),
    MARATHON_EDIT_DONE_KEY: (
        "bool",
        True,
        "whether a shoutout is rewritten in the past tense when the run is over. on by default",
    ),
    MARATHON_RUNNER_POSTS_KEY: (
        "bool",
        True,
        "whether each BaF run gets its own post in the marathon's thread, edited in place as its "
        "slot moves, goes live, ends or is dropped, and the board is only its head. off = the "
        "board lists every BaF run as before. on by default",
    ),
    MARATHON_RUNNER_POSTS_PINNED_KEY: (
        "bool",
        True,
        "whether each BaF run's own post is pinned; its pin comes off a day after the run is "
        "over or dropped, and with the board's. on by default",
    ),
    MARATHON_WINDOW_SLACK_KEY: (
        "int",
        2,
        "hours either side of a marathon that its channel's ping window stays open, when the "
        "channel pings during events only. 2 by default",
    ),
    MARATHON_SPOTLIGHT_LEAD_KEY: (
        "int",
        2,
        "hours before a runner's first run (or the one run it was spotlit from) that Spotlight… on "
        "a marathon's People card starts their channel's spotlight. 2 by default",
    ),
    MARATHON_SPOTLIGHT_SLACK_KEY: (
        "int",
        2,
        "hours after a runner's last run ends (or the one run it was spotlit from) that their "
        "channel's spotlight from a marathon's People card runs out. 2 by default",
    ),
    MARATHON_SUGGEST_NEXT_KEY: (
        "bool",
        True,
        "whether a GDQ marathon that is over looks up the next GDQ event on the tracker and "
        "suggests it to staff — a notice with Add it and Not this one, and a Next up card in the "
        "Marathons section of the Events page. on by default; nothing is ever added until staff "
        "press Add it",
    ),
    MARATHON_FEEDS_KEY: (
        "bool",
        True,
        "whether the marathon feeds check on their own — each feed reads the events list of one "
        "channel's marathons (the GDQ and RPG Limit Break trackers, a horaro.net event, horaro.net "
        "events found by name, Oengus, Fastest Furs' own list, Lady Arcaders' next event numbers) "
        "and adds or suggests every new event. on by default; off checks nothing, and Check now on "
        "a feed still works",
    ),
    MARATHON_FEED_HOURS_KEY: (
        "int",
        6,
        "hours between two checks of one marathon feed. 6 by default",
    ),
    MARATHON_FEED_ACTION_KEY: (
        "enum",
        "add",
        "what a new feed does with an event it finds, until staff change that feed: add puts "
        "it on the marathon list at once with its message in the marathon inbox thread (Track "
        "and Ignore); suggest posts a notice there with Add it and Not this one. add by default",
    ),
    MARATHON_FEED_NOTICE_WHEN_KEY: (
        "enum",
        "published",
        "when a marathon gets its message in the marathon inbox thread: published waits for the "
        "first read that finds runs on its schedule (a feed's find and a staff Add alike — Post it "
        "to the inbox now posts one early); added posts it the moment it is on the list. "
        "published by default",
    ),
    MARATHON_FEED_RECENT_KEY: (
        "int",
        1,
        "how many days after it started (a tracker event) or ended (a horaro.net schedule, an "
        "Oengus marathon, a Fastest Furs event or a Lady Arcaders event) an event still counts as "
        "new to a feed. 1 by default",
    ),
    MARATHON_LADYARCADERS_FLOOR_KEY: (
        "int",
        24,
        "the event number the Lady Arcaders feed probes upward from — it asks the next numbers "
        "above this or above the highest event it already knows, whichever is higher; staff raise "
        "it after a link is pasted. 24 by default",
    ),
    MARATHON_HOTFIX_SHOWS_KEY: (
        "text",
        MARATHON_HOTFIX_SHOWS,
        "the GDQ Hotfix shows the Hotfix feed turns into marathons, separated by commas and "
        "spelled as the sheet's Show column spells them (capitals do not matter); each run of "
        "days a show airs becomes one marathon. `GDQueer` by default",
    ),
    MARATHON_HOTFIX_TRACK_PEOPLE_KEY: (
        "bool",
        True,
        "whether the Hotfix feed also takes any show block a BaF person runs or hosts — paired "
        "for every schedule, matched by their Twitch link or their Discord name, the same rules "
        "the marathon's People card uses — even when its show is not in marathon_hotfix_shows. "
        "on by default",
    ),
    MARATHON_HOTFIX_VIEWER_URL_KEY: (
        "text",
        MARATHON_HOTFIX_VIEWER_URL,
        "the Hotfix schedule viewer page Black Bloc reads beside GDQ's own sheet — a second "
        "source, never a replacement. From it come the hosts' Twitch names and the links to "
        "each special event's own schedule (per-run start times, hosts and commentators). One "
        "https link; blank turns this source off and the GDQ sheet is read alone. "
        "`https://ogndrahcir.github.io/ScheduleViewer/` by default",
    ),
    MARATHON_HOTFIX_OVERLAY_DEFAULT_KEY: (
        "bool",
        True,
        "whether a Hotfix marathon takes its start times, hosts and commentators from the "
        "event's own schedule sheet when the viewer page links one that matches it — while "
        "the marathon's own Event schedule switch follows this setting. Off, such a marathon "
        "keeps GDQ's sheet times (the show's start plus the estimates) and its host column. "
        "on by default",
    ),
    MARATHON_EVENT_MODE_DEFAULT_KEY: (
        "enum",
        "none",
        "what a new marathon does about events, until staff change that marathon: none makes "
        "no event; marathon puts one event for the whole marathon into the events review, dated "
        "from the schedule; runs makes one event per BaF run, approved at once and re-dated as "
        "the schedule moves, and the events feature announces each one as it starts; both does "
        "the two. none by default — the Add form's Event select starts here, a feed's own mode "
        "wins for the marathons it adds, and each marathon's drawer changes its own",
    ),
    MARATHON_RUN_EVENTS_REVIEWED_KEY: (
        "bool",
        False,
        "whether an event made for a BaF run goes through the events review like any "
        "proposal. off by default — staff already chose the mode, so a run's event is approved "
        "at once and the events feature announces it when it starts",
    ),
    MARATHON_RUN_EVENT_CANCEL_ON_LEAVE_KEY: (
        "bool",
        True,
        "whether a marathon's events are called off when staff change its event mode away from "
        "them (reason mode_changed). on by default; off leaves them on the calendar as ordinary "
        "events the marathon no longer keeps in step",
    ),
    MARATHON_SHOUT_WHEN_RUN_HAS_EVENT_KEY: (
        "bool",
        False,
        "whether a BaF run that has its own event still gets the marathon shoutout when it "
        "goes live. off by default — the events feature announces that run as it starts, so the "
        "shoutout would say it twice. The reminders post either way",
    ),
    MARATHON_SPOTLIGHT_FOLLOWS_KEY: (
        "bool",
        True,
        "while a marathon on the list is running, its channel is spotlit and the spotlight "
        "expires at the marathon's end. on by default; a channel already kept for ever (like "
        "GamesDoneQuick) is never touched, a later expiry is never shortened, and each marathon's "
        "own Spotlight the channel while it runs switch turns it off for that marathon",
    ),
    MARATHON_SPOTLIGHT_LEAD_MINUTES_KEY: (
        "int",
        15,
        "minutes before a marathon's first run that marathon_spotlight turns its channel's "
        "spotlight on. 15 by default, like marathon_ping_minutes",
    ),
    MARATHON_SPOTLIGHT_TAIL_KEY: (
        "int",
        60,
        "minutes after a marathon's last run ends that the spotlight it follows stays on. 60 by "
        "default, so a schedule that runs over is still spotlit; 0 ends it with the last run. "
        "When the schedule is extended the end moves with it",
    ),
    MARATHON_PING_ROLE_DEFAULT_KEY: (
        "bool",
        False,
        "whether a NEW marathon pings roles — its run reminders and shoutouts mention the "
        "runner's and the channel's ping roles, and its channel gets a ping window. off by "
        "default; each marathon's own Ping the role switch changes it after, and marathons "
        "already on the list keep their own",
    ),
    MARATHON_PUBLIC_CHANNEL_KEY: (
        "channel",
        None,
        "where a BaF run's public highlight goes — the post members see, since a marathon's "
        "own thread is for staff. Blank uses the go-live channel. Changing it moves the next "
        "highlight; one already up stays where it is and keeps being updated",
    ),
    MARATHON_REMINDER_CHANNEL_KEY: (
        "channel",
        None,
        "where the public copy of a tracked marathon's reminders goes (the *is up in 15 "
        "minutes* posts members see; marathon_thread_reminders adds a copy in the marathon's "
        "own thread). Blank uses the "
        "go-live channel. Its own row: it never moves the go-live spotlight post or the public "
        "highlights",
    ),
    MARATHON_NEAR_MISS_POSTS_KEY: (
        "bool",
        True,
        "whether a tracked marathon's thread gets one post per runner whose Twitch login or "
        "schedule name is exactly a member's Discord username, with Link (this marathon), Link "
        "everywhere and Not them buttons for staff. Nobody is linked until staff press. on by "
        "default",
    ),
    MARATHON_ROLE_PINGS_KEY: (
        "bool",
        True,
        "whether the marathon_ping_minutes heads-up mentions the Marathon role (marathon_role_id) "
        "when the marathon's own ping switch is on. The mention goes in the public copy members "
        "see, once, never in the staff thread, and never on the live highlight or shoutout. on "
        "by default; off posts the heads-up without it",
    ),
    MARATHON_BAF_EVENT_NAMES_KEY: (
        "text",
        'Black in a Flash',
        "the show names that make a marathon a BaF event, separated by commas. A marathon whose "
        "name, or whose GDQ Hotfix show, starts with one of them on whole words is a BaF event "
        "whatever its runs say — capitals, spaces and punctuation do not matter, so Black in a "
        "Flash: Soul Train matches Black in a Flash, and Black in a Flashback does not. `Black "
        "in a Flash` by default; the marathon's own BaF event switch and an answer staff gave "
        "to the bot's question still win",
    ),
    MARATHON_BAF_EVENT_MIN_RUNS_KEY: (
        "int",
        2,
        "how many runs a marathon needs, over all of its days, before every run having a BaF "
        "runner makes it a BaF event. 2 by default — one run is not an event",
    ),
    MARATHON_BAF_EVENT_ASK_PERCENT_KEY: (
        "int",
        75,
        "the share of a marathon's runs with a BaF runner, in percent and over all of its days, "
        "from which the bot asks once in the marathon's thread whether it is a BaF event instead "
        "of deciding by itself. Under it the marathon is not one; at 100 percent it is. 75 by "
        "default; 100 never asks",
    ),
    MARATHON_BAF_EVENT_PING_MINUTES_KEY: (
        "int",
        120,
        "on each day of a BaF event the Marathon role is mentioned once, on the heads-up this "
        "many minutes before the day's first BaF run, and on no other heads-up that day. It "
        "should be one of marathon_reminder_minutes; when it is not, the largest mark at or "
        "under it carries the mention. 120 by default",
    ),
    MARATHON_BAF_EVENT_ASK_ROLE_KEY: (
        "role",
        None,
        "the role mentioned on the question the bot posts in a marathon's thread when it is not "
        "sure the show is a BaF event. Blank posts the question with no mention",
    ),
    MARATHON_PUBLIC_REMINDERS_KEY: (
        "bool",
        True,
        "whether every reminder of a tracked marathon also posts publicly, in "
        "marathon_reminder_channel_id — the switch over every marathon's runner and host "
        "announcements, for reminders. on by default; off keeps reminders in the staff thread "
        "only",
    ),
    MARATHON_THREAD_REMINDERS_KEY: (
        "bool",
        False,
        "whether a reminder that posted publicly also posts in the marathon's own thread. off "
        "by default: the thread gets a reminder only when no public copy went out",
    ),
    MARATHON_ARCHIVE_AFTER_DAYS_KEY: (
        "int",
        7,
        "days after a marathon's last run ends that it moves to the archive, with its runs and "
        "people — kept, browsable under Archive on the Events page, and Restore brings it back "
        "paused. 7 by default; 0 moves it the same day. A marathon with no dates never moves "
        "by itself",
    ),
    MARATHON_CHANNEL_PING_MODE_DEFAULT_KEY: (
        "enum",
        PING_EVENTS,
        "the pings a NEW channel row gets when it is a marathon channel (one a marathon feed is "
        "seeded for) that takes marathons: events — the default — mentions roles only inside a "
        "ping window, which its marathons set from their schedules; always and never as on the "
        "Go-live page. Every other new row follows spotlight_ping_mode_default, and no existing "
        "row is changed",
    ),
    MARATHON_NOTICE_HOME_KEY: (
        "enum",
        "events",
        "retired 2026-09 — the inbox thread is the notice home (marathon_inbox_channel_id). Kept "
        "so old rows still read; nothing reads it any more",
    ),
    MARATHON_INBOX_CHANNEL_KEY: (
        "channel",
        None,
        "where the marathon inbox thread is made — the one thread in which every marathon Black "
        "Bloc finds gets a message with Track and Ignore. Blank uses events_announce_channel_id. "
        "shadow makes it where marathon_shadow_channel_id or shadow_channel_id points",
    ),
    MARATHON_THREAD_CHANNEL_KEY: (
        "channel",
        None,
        "where a tracked marathon's own thread is made — its board, reminders and shoutouts post "
        "inside it. Blank uses the inbox's channel, beside the inbox thread",
    ),
    MARATHON_TRACK_MAKES_THREAD_KEY: (
        "bool",
        True,
        "whether Track makes the marathon its own thread. on by default; off tracks it without "
        "a thread and its posts go to marathon_channel_id as before. A marathon that already has "
        "a thread keeps it",
    ),
    MARATHON_AUTO_TRACK_DEFAULT_KEY: (
        "bool",
        False,
        "what a NEW marathon feed's auto-track switch starts at. off by default — Track is a "
        "staff press; a feed with auto-track on tracks each marathon it adds the moment its "
        "schedule is out. No existing feed is changed",
    ),
}
MARATHON_WORDS: dict[str, tuple[str, tuple[str, ...], str]] = {
    MARATHON_SPOTLIGHT_HOST_NOTE_KEY: (
        "{name} hosting {marathon}",
        ("name", "marathon"),
        "the note a host's channel row carries on the Go-live page when Spotlight… on a "
        "marathon's People card adds it for someone who only hosts there. It takes {name} "
        "{marathon}",
    ),
    MARATHON_HOST_EVENT_TITLE_KEY: (
        "{member} hosts {marathon}",
        MARATHON_HOST_EVENT_FIELDS,
        "what the event made for one BaF host block of a marathon is called (its hosts in "
        "{member}). It takes {member} "
        "{marathon} {games} {runs}",
    ),
    MARATHON_HOST_EVENT_DESCRIPTION_KEY: (
        "{member} hosts {runs} run(s) on {marathon}: {games}. Read from the schedule; times "
        "follow it.",
        MARATHON_HOST_EVENT_FIELDS,
        "the description of the event made for one BaF host block of a marathon. It takes "
        "{member} "
        "{marathon} {games} {runs}",
    ),
    MARATHON_BAF_EVENT_ASK_TEXT_KEY: (
        "Is **{marathon}** a BaF event? {baf} of its {runs} runs have a BaF runner.",
        ("marathon", "baf", "runs"),
        "the question posted once in a marathon's thread when the bot is not sure the marathon "
        "is a BaF event; its answer covers every day of the marathon. It takes {marathon} {baf} "
        "{runs}, counted over the whole marathon; the role in marathon_baf_event_ask_role_id is "
        "mentioned in front of it when the Marathon-role mention could go out",
    ),
    MARATHON_BAF_EVENT_ASK_YES_KEY: (
        "Yes, a BaF event",
        (),
        "the question's button that answers yes",
    ),
    MARATHON_BAF_EVENT_ASK_NO_KEY: (
        "No, not a BaF event",
        (),
        "the question's button that answers no",
    ),
    MARATHON_BAF_EVENT_ANSWERED_KEY: (
        "{who} answered: {answer}.",
        ("who", "answer", "marathon"),
        "the line added under the BaF event question once staff answer it with its buttons. It "
        "takes {who} {answer} {marathon}",
    ),
    MARATHON_BAF_EVENT_STAFF_SET_KEY: (
        "{who} set it on the BaF event switch: {answer}.",
        ("who", "answer", "marathon"),
        "the line that replaces the Yes/No buttons under a BaF event question nobody has "
        "answered once staff set the marathon's BaF event switch; following again brings the "
        "buttons back. It takes {who} {answer} {marathon}",
    ),
    MARATHON_BAF_EVENT_WORD_YES_KEY: (
        "a BaF event",
        (),
        "how a BaF event is named wherever its state is written",
    ),
    MARATHON_BAF_EVENT_WORD_NO_KEY: (
        "not a BaF event",
        (),
        "how a show that is not a BaF event is named wherever its state is written",
    ),
    MARATHON_BAF_EVENT_WORD_UNSURE_KEY: (
        "not decided",
        (),
        "how a show the bot is not sure about is named wherever its state is written",
    ),
    MARATHON_BAF_EVENT_WORD_FOLLOW_KEY: (
        "worked out from the schedule",
        (),
        "how a marathon whose BaF event switch follows the schedule is named in the answers staff "
        "get",
    ),
    MARATHON_BAF_EVENT_SET_SAID_KEY: (
        "**{marathon}** is {answer} now.",
        ("marathon", "answer"),
        "what staff are told once a marathon's BaF event switch changes. It takes {marathon} "
        "{answer}",
    ),
    MARATHON_BAF_EVENT_SAME_SAID_KEY: (
        "**{marathon}** is already {answer}, so nothing was changed.",
        ("marathon", "answer"),
        "what staff are told when a marathon's BaF event switch already says that. It takes "
        "{marathon} {answer}",
    ),
    MARATHON_BAF_EVENT_LINE_KEY: (
        "**{marathon}** is {answer} — {reason}.",
        ("marathon", "answer", "reason"),
        "the one line the thread controls and the marathon drawer carry for whether the "
        "marathon is a BaF event and why. It takes {marathon} {answer} {reason}",
    ),
    MARATHON_BAF_EVENT_REASON_STAFF_KEY: (
        "the BaF event switch says so",
        (),
        "the reason on the BaF event line when the marathon's BaF event switch decided it",
    ),
    MARATHON_BAF_EVENT_REASON_NAME_KEY: (
        "the show is named {name}",
        ("name",),
        "the reason on the BaF event line when the show's name is in marathon_baf_event_names. "
        "It takes {name}",
    ),
    MARATHON_BAF_EVENT_REASON_ALL_RUNS_KEY: (
        "all {runs} runs have a BaF runner",
        ("runs",),
        "the reason on the BaF event line when every run of the marathon has a BaF runner. It "
        "takes {runs}",
    ),
    MARATHON_BAF_EVENT_REASON_SHARE_KEY: (
        "{baf} of {runs} runs have a BaF runner, too few to be sure",
        ("baf", "runs"),
        "the reason on the BaF event line while the bot is not sure and nobody has answered. It "
        "takes {baf} {runs}, counted over the whole marathon",
    ),
    MARATHON_BAF_EVENT_REASON_FEW_RUNS_KEY: (
        "it has {runs} run(s), fewer than {min}",
        ("runs", "min"),
        "the reason on the BaF event line when every run has a BaF runner but the marathon has "
        "fewer runs than marathon_baf_event_min_runs. It takes {runs} {min}",
    ),
    MARATHON_BAF_EVENT_REASON_MIXED_KEY: (
        "{baf} of {runs} runs have a BaF runner",
        ("baf", "runs"),
        "the reason on the BaF event line when too few of the marathon's runs have a BaF "
        "runner. It takes {baf} {runs}",
    ),
    MARATHON_BAF_EVENT_REASON_NO_RUNS_KEY: (
        "no run is on the schedule",
        (),
        "the reason on the BaF event line when the marathon has no run on its schedule",
    ),
    MARATHON_BAF_EVENT_PING_WILL_KEY: (
        "{role} is mentioned once, on the heads-up {minutes} minutes before **{game}**.",
        ("role", "minutes", "game"),
        "what a BaF event day's line says while its one Marathon-role mention is still to come. "
        "It takes {role} {minutes} {game}",
    ),
    MARATHON_BAF_EVENT_PING_DONE_KEY: (
        "{role} was mentioned once, on the heads-up {minutes} minutes before **{game}**.",
        ("role", "minutes", "game"),
        "what a show-day's line says once its one Marathon-role mention went out. It takes "
        "{role} {minutes} {game}",
    ),
    MARATHON_BAF_EVENT_PING_NONE_KEY: (
        "Every heads-up of that day's BaF runs has gone, so {role} is not mentioned.",
        ("role",),
        "what a BaF event day's line says when every heads-up that could carry the Marathon "
        "role has been posted or its run has started. It takes {role}",
    ),
    MARATHON_BAF_EVENT_PING_FALLBACK_KEY: (
        "marathon_baf_event_ping_minutes is {wanted}, which is not one of "
        "marathon_reminder_minutes, so the {minutes}-minute heads-up carries it.",
        ("wanted", "minutes"),
        "what a BaF event day's line adds while marathon_baf_event_ping_minutes is not a reminder "
        "mark. It takes {wanted} {minutes}",
    ),
    MARATHON_BAF_EVENT_REASON_LEADS_KEY: (
        "staff answered the question in the thread ({baf} of {runs} runs have a BaF runner); "
        "the answer stands until the BaF event switch changes it",
        ("baf", "runs"),
        "the reason on the BaF event line when staff answered the bot's question. The answer "
        "stands whatever the schedule becomes afterwards. It takes {baf} {runs}, counted now",
    ),
    MARATHON_BAF_EVENT_PING_UNCONFIRMED_KEY: (
        "{role} may have been mentioned on the heads-up {minutes} minutes before **{game}**: "
        "the bot stopped before it could confirm it, so nothing else mentions {role} that day.",
        ("role", "minutes", "game"),
        "what a show-day's line says when the bot stopped between claiming the day's one "
        "Marathon-role mention and confirming it went out. It takes {role} {minutes} {game}",
    ),
    MARATHON_BAF_EVENT_PING_NO_RUN_KEY: (
        "No BaF run is on that day, so {role} is not mentioned.",
        ("role",),
        "what a BaF event day's line says when none of that day's runs has a BaF member to post "
        "a heads-up for. It takes {role}",
    ),
    MARATHON_BAF_EVENT_PING_NOBODY_KEY: (
        "Nobody on that day's BaF runs can be named publicly, so {role} is not mentioned.",
        ("role",),
        "what a BaF event day's line says when every BaF run still to come has only people "
        "who opted out of public posts. It takes {role}",
    ),
    MARATHON_BAF_EVENT_ASK_PENDING_KEY: (
        "Staff were asked in the thread and have not answered.",
        (),
        "what the BaF event line adds while the bot's question is up and unanswered",
    ),
    MARATHON_BAF_EVENT_ASK_FAILED_KEY: (
        "The question could not be posted in the thread, so answer with the BaF event switch.",
        (),
        "what the BaF event line adds when the bot's question could not be posted",
    ),
    MARATHON_BAF_EVENT_ASK_NOWHERE_KEY: (
        "There is no thread to ask in, so answer with the BaF event switch.",
        (),
        "what the BaF event line adds when the marathon has no thread the bot may post its "
        "question in",
    ),
    MARATHON_BAF_EVENT_REASON_ACTED_KEY: (
        "{baf} of {runs} runs have a BaF runner now; it was a BaF event when a day's one "
        "mention went out, so it stays one until staff answer",
        ("baf", "runs"),
        "the reason on the BaF event line when a schedule change left the bot unsure after it "
        "had already mentioned the Marathon role once for a day of the marathon as a BaF "
        "event. It takes {baf} {runs}, counted now",
    ),
    MARATHON_BAF_EVENT_CLEARED_KEY: (
        "{who} cleared the answer.",
        ("who", "marathon"),
        "the line under every BaF event question of a marathon once staff clear the answer. It "
        "takes {who} {marathon}",
    ),
    MARATHON_BAF_EVENT_CLEARED_SAID_KEY: (
        "The answer was cleared, so **{marathon}** is {answer} now.",
        ("marathon", "answer"),
        "what staff are told once the answer to a marathon's BaF event question is cleared. It "
        "takes {marathon} {answer}",
    ),
    MARATHON_BAF_EVENT_NO_ANSWER_SAID_KEY: (
        "**{marathon}** has no answer to clear, so nothing was changed.",
        ("marathon",),
        "what staff are told when they clear the answer to a marathon's BaF event question and "
        "none is stored. It takes {marathon}",
    ),
    MARATHON_CONTROLS_BAF_SAID_YES_KEY: (
        "BaF event: yes ({reason}) · say no",
        ("reason",),
        "the thread controls' BaF event button while the bot worked out the marathon is a "
        "BaF event; a press says no. It takes {reason}",
    ),
    MARATHON_CONTROLS_BAF_SAID_NO_KEY: (
        "BaF event: no ({reason}) · say yes",
        ("reason",),
        "the thread controls' BaF event button while the bot worked out the marathon is not "
        "a BaF event; a press says yes. It takes {reason}",
    ),
    MARATHON_CONTROLS_BAF_SAID_UNSURE_KEY: (
        "BaF event: not decided ({reason}) · say yes",
        ("reason",),
        "the thread controls' BaF event button while the bot is not sure and nobody has "
        "answered its question; a press says yes. It takes {reason}",
    ),
    MARATHON_CONTROLS_BAF_STAFF_YES_KEY: (
        "BaF event: yes (staff) · clear",
        (),
        "the thread controls' BaF event button while the marathon's BaF event switch says "
        "yes; a press lets the bot work it out again",
    ),
    MARATHON_CONTROLS_BAF_STAFF_NO_KEY: (
        "BaF event: no (staff) · clear",
        (),
        "the thread controls' BaF event button while the marathon's BaF event switch says "
        "no; a press lets the bot work it out again",
    ),
    MARATHON_CONTROLS_BAF_ANSWERED_YES_KEY: (
        "BaF event: yes (answered) · clear",
        (),
        "the thread controls' BaF event button while staff answered the bot's question yes; "
        "a press takes the answer back",
    ),
    MARATHON_CONTROLS_BAF_ANSWERED_NO_KEY: (
        "BaF event: no (answered) · clear",
        (),
        "the thread controls' BaF event button while staff answered the bot's question no; a "
        "press takes the answer back",
    ),
    MARATHON_CONTROLS_BAF_NAMED_KEY: (
        "named {name}",
        ("name",),
        "the reason inside the thread controls' BaF event button when the show's name is in "
        "marathon_baf_event_names. It takes {name}",
    ),
    MARATHON_CONTROLS_BAF_RUNS_KEY: (
        "{baf} of {runs} runs",
        ("baf", "runs"),
        "the reason inside the thread controls' BaF event button when the runs decide it. It "
        "takes {baf} {runs}, counted over the whole marathon",
    ),
    MARATHON_BAF_EVENT_DAY_LINE_KEY: (
        "{day}: {ping}",
        ("day", "ping"),
        "the line the thread controls and the marathon drawer carry for one show-day of a BaF "
        "event, under the event's own line: the day, then what its one Marathon-role mention "
        "did or will do. It takes {day} {ping}",
    ),
    MARATHON_CONTROLS_TRACKER_KEY: (
        "Marathon tracker ↗",
        (),
        "the link button on a tracked marathon's thread controls that opens its Marathon "
        "tracker page on the site — the runs in order with the times the bot is working from",
    ),
    MARATHON_CONTROLS_SPOTLIGHT_FOLLOW_ON_KEY: (
        "Spotlight follows the schedule: on · turn off",
        (),
        "the thread controls' spotlight switch while the marathon spotlights its channel "
        "from the lead before its first run to the tail after its last; a press cancels it "
        "before the show and stops it during",
    ),
    MARATHON_CONTROLS_SPOTLIGHT_FOLLOW_OFF_KEY: (
        "Spotlight follows the schedule: off · turn on",
        (),
        "the thread controls' spotlight switch while the marathon does not spotlight its "
        "channel on its own; a press turns it on, and on now when the show is near",
    ),
    MARATHON_CONTROLS_SPOTLIGHT_UNTIL_LINE_KEY: (
        "Spotlight: on now until {until}",
        ("until",),
        "the state line on the thread controls while the marathon's channel is spotlit. It "
        "takes {until}, read in each viewer's own clock",
    ),
    MARATHON_CONTROLS_SPOTLIGHT_STARTS_LINE_KEY: (
        "Spotlight: starts {starts}",
        ("starts",),
        "the state line on the thread controls while the channel's spotlight is set to start "
        "later. It takes {starts}, read in each viewer's own clock",
    ),
    MARATHON_CONTROLS_SPOTLIGHT_KEPT_LINE_KEY: (
        "Spotlight: kept on Go-live",
        (),
        "the state line on the thread controls while the channel's spotlight is kept for "
        "ever on Go-live; no spotlight button is drawn then",
    ),
    MARATHON_CONTROLS_SPOTLIGHT_RUNNING_LINE_KEY: (
        "Spotlight: on until {until} · not following the schedule · stop it on Go-live",
        ("until",),
        "the state line on the thread controls while a spotlight staff (or another marathon) "
        "set is up and this marathon does not follow the schedule. It takes {until}, read in "
        "each viewer's own clock",
    ),
    MARATHON_CONTROLS_SPOTLIGHT_NONE_LINE_KEY: (
        "Spotlight: no channel to spotlight",
        (),
        "the state line on the thread controls while the marathon has no channel; no "
        "spotlight button is drawn then",
    ),
    MARATHON_CONTROLS_ARCHIVE_KEY: (
        "Archive it",
        (),
        "the thread controls' button once the show is over: it moves the marathon to the "
        "archive, and Restore on the site puts it back",
    ),
    MARATHON_RUN_EVENT_UNLINK_KEY: (
        "Unlink the event",
        (),
        "the marathon drawer's button under a run's event link that unlinks that event from "
        "the run; it sits beside the person's own Unlink",
    ),
    MARATHON_OVERLAY_ON_SAID_KEY: (
        "**{marathon}** takes its start times, hosts and commentators from the event's own "
        "schedule sheet now, when the viewer links one that matches. The schedule is being "
        "read again.",
        ("marathon",),
        "what staff are told once a marathon's Event schedule switch is on. It takes "
        "{marathon}",
    ),
    MARATHON_OVERLAY_OFF_SAID_KEY: (
        "**{marathon}** keeps GDQ's sheet times and host column now — the event's own "
        "schedule sheet is not laid over it. The schedule is being read again.",
        ("marathon",),
        "what staff are told once a marathon's Event schedule switch is off. It takes "
        "{marathon}",
    ),
    MARATHON_CONTROLS_ANNOUNCE_ON_KEY: (
        "Runner announcements: on · turn off",
        (),
        "the thread controls' runner announcements button while the marathon's BaF runners are "
        "announced publicly",
    ),
    MARATHON_CONTROLS_ANNOUNCE_OFF_KEY: (
        "Runner announcements: off · turn on",
        (),
        "the thread controls' runner announcements button while the marathon's BaF runners are "
        "not announced publicly",
    ),
    MARATHON_ANNOUNCEMENTS_ON_SAID_KEY: (
        "**{marathon}** announces its BaF runners publicly now — reminders at every mark, and "
        "a highlight as each run goes live. A runner can still be left out of one run.",
        ("marathon",),
        "what staff are told once a marathon's Runner announcements switch is on. It takes "
        "{marathon}",
    ),
    MARATHON_ANNOUNCEMENTS_OFF_SAID_KEY: (
        "**{marathon}** no longer announces its BaF runners publicly. A runner can still be "
        "announced for one run from that run's post; posts already up follow their runs to the "
        "end.",
        ("marathon",),
        "what staff are told once a marathon's Runner announcements switch is off. It takes "
        "{marathon}",
    ),
    MARATHON_CONTROLS_HOST_ANNOUNCE_ON_KEY: (
        "Host announcements: on · turn off",
        (),
        "the thread controls' host announcements button while the marathon's BaF hosts are "
        "announced publicly",
    ),
    MARATHON_CONTROLS_HOST_ANNOUNCE_OFF_KEY: (
        "Host announcements: off · turn on",
        (),
        "the thread controls' host announcements button while the marathon's BaF hosts are not "
        "announced publicly",
    ),
    MARATHON_HOST_ANNOUNCEMENTS_ON_SAID_KEY: (
        "**{marathon}** announces its BaF hosts publicly now, once per stretch of runs they "
        "host. A host can still be left out of one run from that run's post.",
        ("marathon",),
        "what staff are told once a marathon's Host announcements switch is on. It takes "
        "{marathon}",
    ),
    MARATHON_HOST_ANNOUNCEMENTS_OFF_SAID_KEY: (
        "**{marathon}** no longer announces its BaF hosts publicly. A host can still be "
        "announced for one run from that run's post; a host highlight already up follows its "
        "runs to the end.",
        ("marathon",),
        "what staff are told once a marathon's Host announcements switch is off. It takes "
        "{marathon}",
    ),
    MARATHON_ANNOUNCE_BUTTON_RUN_OUT_KEY: (
        "Don't announce {name}",
        ("name",),
        "the button on a BaF run's post in the staff thread (and in the People slot view) for a "
        "person who would be announced for that run: it leaves them out of that run's public "
        "posts only. It takes {name}",
    ),
    MARATHON_ANNOUNCE_BUTTON_RUN_IN_KEY: (
        "Announce {name}",
        ("name",),
        "the same button for a person who would not be announced for that run (the switch for "
        "their part is off, or they are opted out of the whole marathon): it announces them for "
        "that run. It takes {name}",
    ),
    MARATHON_ANNOUNCE_BUTTON_RUN_DEFAULT_KEY: (
        "{name}: back to the default",
        ("name",),
        "the same button once the person has their own answer for that run: it clears it. It "
        "takes {name}",
    ),
    MARATHON_ANNOUNCE_BUTTON_PLAIN_KEY: (
        "No @ for {name}",
        ("name",),
        "the button beside it while the person is written as an @ in this marathon's public "
        "posts: their name is written as plain text instead. It takes {name}",
    ),
    MARATHON_ANNOUNCE_BUTTON_MENTION_KEY: (
        "@ {name} again",
        ("name",),
        "the same button while the person's name is written as plain text. It takes {name}",
    ),
    MARATHON_ANNOUNCE_PICK_KEY: (
        "Announcements for a person on this run…",
        (),
        "the menu a BaF run's post carries instead of buttons once more people are on the run "
        "than buttons fit; past twelve people it is one menu for every twelve",
    ),
    MARATHON_PEOPLE_BUTTON_SPOTLIGHT_KEY: (
        "Spotlight their channel…",
        (),
        "the People view's button that spotlights the person's own channel on Go-live while "
        "their runs are on",
    ),
    MARATHON_PEOPLE_BUTTON_UNSPOTLIGHT_KEY: (
        "Stop spotlighting their channel",
        (),
        "the People view's button that stops spotlighting the person's own channel for this "
        "marathon",
    ),
    MARATHON_PEOPLE_BUTTON_UNLINK_KEY: (
        "Unlink",
        (),
        "the People view's button that takes back a link staff made; it is there only while "
        "the person is linked",
    ),
    MARATHON_PEOPLE_BUTTON_LINK_NEAR_KEY: (
        "Link @{username}",
        ("username",),
        "the People view's button that links a schedule name to the member it nearly "
        "matched. It takes {username}",
    ),
    MARATHON_PEOPLE_BUTTON_TWITCH_KEY: (
        "Twitch name…",
        (),
        "the People view's button that fixes the Twitch name of a person linked by staff; it "
        "is there only while they are linked",
    ),
    MARATHON_PEOPLE_BUTTON_BACK_KEY: (
        "Back",
        (),
        "the People view's button back to the schedule, the card or the panel",
    ),
    MARATHON_ANNOUNCE_STATE_LINE_KEY: (
        "{name}: {state} — {why}{plain}",
        ("name", "state", "why", "plain"),
        "one line a BaF person under a run's post in the staff thread: whether they are "
        "announced for that run and why. It takes {name} {state} {why} {plain}",
    ),
    MARATHON_ANNOUNCE_STATE_YES_KEY: (
        "announced for this run",
        (),
        "{state} of that line while the person is announced for the run",
    ),
    MARATHON_ANNOUNCE_STATE_NO_KEY: (
        "not announced for this run",
        (),
        "{state} of that line while the person is not announced for the run",
    ),
    MARATHON_ANNOUNCE_WHY_DEFAULT_KEY: (
        "the default",
        (),
        "{why} of that line while nothing but the defaults decides",
    ),
    MARATHON_ANNOUNCE_WHY_RUN_KEY: (
        "set for this run",
        (),
        "{why} of that line while the run has its own answer for the person",
    ),
    MARATHON_ANNOUNCE_WHY_MARATHON_KEY: (
        "opted out of every run on this marathon",
        (),
        "{why} of that line while the person is opted out of the whole marathon",
    ),
    MARATHON_ANNOUNCE_WHY_OFF_KEY: (
        "runner announcements are off for this marathon",
        (),
        "{why} of that line for a runner while the marathon's Runner announcements switch is "
        "off",
    ),
    MARATHON_ANNOUNCE_WHY_HOSTS_OFF_KEY: (
        "host announcements are off for this marathon",
        (),
        "{why} of that line for a host while the marathon's Host announcements switch is off",
    ),
    MARATHON_ANNOUNCE_STATE_PLAIN_KEY: (
        " · written without an @",
        (),
        "{plain} of that line while the person's name is written as plain text",
    ),
    MARATHON_ANNOUNCE_RUN_IN_SAID_KEY: (
        "**{name}** is announced for **{game}** on **{marathon}** from the next reminder mark.",
        ("name", "game", "marathon"),
        "what staff are told once a person is announced for one run. It takes {name} {game} "
        "{marathon}",
    ),
    MARATHON_ANNOUNCE_RUN_OUT_SAID_KEY: (
        "**{name}** is not announced for **{game}** on **{marathon}**. Their other runs are "
        "unchanged.",
        ("name", "game", "marathon"),
        "what staff are told once a person is left out of one run's public posts. It takes "
        "{name} {game} {marathon}",
    ),
    MARATHON_ANNOUNCE_RUN_DEFAULT_SAID_KEY: (
        "**{name}** follows the defaults again for **{game}** on **{marathon}**.",
        ("name", "game", "marathon"),
        "what staff are told once a person's own answer for one run is cleared. It takes "
        "{name} {game} {marathon}",
    ),
    MARATHON_MENTION_PLAIN_SAID_KEY: (
        "**{name}** is written by name, with no @, in **{marathon}**'s public posts. Posts "
        "already up are rewritten in place.",
        ("name", "marathon"),
        "what staff are told once a person's name is written as plain text on a marathon. It "
        "takes {name} {marathon}",
    ),
    MARATHON_MENTION_ON_SAID_KEY: (
        "**{name}** is written as an @ again in **{marathon}**'s public posts. Posts already "
        "up are rewritten in place.",
        ("name", "marathon"),
        "what staff are told once a person is written as an @ again on a marathon. It takes "
        "{name} {marathon}",
    ),
    MARATHON_PUBLIC_BUTTON_OPT_OUT_KEY: (
        "Opt out of every run on this marathon",
        (),
        "the button on a BaF person in the People slot view that opts the person out of this "
        "marathon's public posts — every run of theirs on it. It posts nothing",
    ),
    MARATHON_PUBLIC_BUTTON_OPT_IN_KEY: (
        "Opt back in to this marathon",
        (),
        "the same button once the person is opted out of the whole marathon; they are "
        "announced again from the next reminder mark",
    ),
    MARATHON_ANNOUNCE_OPTED_OUT_SAID_KEY: (
        "**{name}** is opted out of **{marathon}**'s public posts: no reminders and no "
        "highlight. A highlight of theirs that was up is taken down.",
        ("name", "marathon"),
        "what staff are told once a person is opted out of a marathon's public posts. It takes "
        "{name} {marathon}",
    ),
    MARATHON_ANNOUNCE_OPTED_IN_SAID_KEY: (
        "**{name}** is back in **{marathon}**'s public posts from the next reminder mark.",
        ("name", "marathon"),
        "what staff are told once a person is opted back in to a marathon's public posts. It "
        "takes {name} {marathon}",
    ),
    MARATHON_ARCHIVED_WORD_KEY: (
        "Archived {when} — runs, people and posts are kept.",
        ("when",),
        "the line an archived marathon carries where its message is — the archived drawer on "
        "the Events page today, the marathon's inbox message once there is one. It takes {when}",
    ),
    MARATHON_ARCHIVE_QUESTION_KEY: (
        "Archive **{name}**? It stops being read and its ping window closes; its runs, people "
        "and posts are kept, and **Restore** brings it back paused.",
        ("name",),
        "what staff are asked before Archive it moves a marathon to the archive early. It takes "
        "{name}",
    ),
    MARATHON_ARCHIVED_SAID_KEY: (
        "**{name}** is in the archive — its runs, people and posts are kept. **Restore** brings "
        "it back, paused.",
        ("name",),
        "what staff are told once Archive it has moved a marathon to the archive. It takes {name}",
    ),
    MARATHON_RESTORE_QUESTION_KEY: (
        "Restore **{name}**? It comes back to the list paused — nothing is read or posted until "
        "someone presses **Resume**.",
        ("name",),
        "what staff are asked before Restore brings an archived marathon back. It takes {name}",
    ),
    MARATHON_RESTORED_SAID_KEY: (
        "**{name}** is back on the list, paused — **Resume** reads it again.",
        ("name",),
        "what staff are told once Restore has brought a marathon back. It takes {name}",
    ),
    MARATHON_RESTORE_TAKEN_KEY: (
        "**{name}** cannot come back while **{other}** is on the list with the same schedule "
        "link — remove that one first, so nothing was changed.",
        ("name", "other"),
        "the refusal when Restore would put a second marathon on the list with the same "
        "schedule link. It takes {name} {other}",
    ),
    MARATHON_NOT_ARCHIVED_KEY: (
        "There is no archived marathon **{given}** here, so nothing was restored.",
        ("given",),
        "the refusal when Restore names a marathon that is not in the archive. It takes {given}",
    ),
    MARATHON_INBOX_THREAD_NAME_KEY: (
        "Marathons — found and tracked",
        (),
        "what the marathon inbox thread is called when Black Bloc makes it",
    ),
    MARATHON_INBOX_OPENING_KEY: (
        "Every marathon Black Bloc finds gets a message here. **Track** gives it its own thread "
        "for its board, reminders and shoutouts; **Ignore** keeps it on the list and quiet.",
        (),
        "the first message in the marathon inbox thread, saying what the thread is for",
    ),
    MARATHON_THREAD_NAME_KEY: (
        "{marathon}",
        MARATHON_THREAD_FIELDS,
        "what a tracked marathon's own thread is called. It takes {marathon} {channel} {when}",
    ),
    MARATHON_THREAD_OPENING_KEY: (
        "{marathon} — tracked by {who}. The board, reminders and shoutouts for BaF runs post "
        "here. Schedule: {url}",
        MARATHON_OPENING_FIELDS,
        "the first message in a tracked marathon's own thread. It takes {marathon} {who} {url} "
        "{channel} {when}",
    ),
    MARATHON_INBOX_LABEL_WHEN_KEY: ("When", (), "the When label on a marathon's inbox message"),
    MARATHON_INBOX_LABEL_SOURCE_KEY: (
        "Source",
        (),
        "the Source label on a marathon's inbox message (the feed or the site it is read from)",
    ),
    MARATHON_INBOX_LABEL_CHANNEL_KEY: (
        "Channel",
        (),
        "the Channel label on a marathon's inbox message (the Twitch channel it airs on)",
    ),
    MARATHON_INBOX_LABEL_SCHEDULE_KEY: (
        "Schedule",
        (),
        "the Schedule label on a marathon's inbox message (its runs and BaF runs)",
    ),
    MARATHON_INBOX_LABEL_EVENT_KEY: (
        "Event",
        (),
        "the Event label on a marathon's inbox message (none, marathon, runs or both)",
    ),
    MARATHON_INBOX_LABEL_STATE_KEY: (
        "State",
        (),
        "the State label on a marathon's inbox message (found, tracked, ignored or archived)",
    ),
    MARATHON_INBOX_STATE_FOUND_KEY: (
        "Found {when} · not tracked",
        ("when",),
        "the State line of a marathon nobody has tracked or ignored yet. It takes {when}",
    ),
    MARATHON_INBOX_STATE_TRACKED_KEY: (
        "Tracked by {who} {when}",
        ("who", "when"),
        "the State line of a tracked marathon. {who} is the staff member, or the feed when it "
        "tracked itself. It takes {who} {when}",
    ),
    MARATHON_INBOX_STATE_IGNORED_KEY: (
        "Ignored by {who} {when}",
        ("who", "when"),
        "the State line of an ignored marathon — on the list, read, and posting nothing. It "
        "takes {who} {when}",
    ),
    MARATHON_INBOX_AUTO_WHO_KEY: (
        "the {feed} feed",
        ("feed",),
        "who a marathon was tracked by when its feed's auto-track tracked it — the {who} of the "
        "State line and of its thread's first message. It takes {feed}",
    ),
    MARATHON_INBOX_BUTTON_TRACK_KEY: (
        "Track",
        (),
        "the Track button on a marathon's inbox message",
    ),
    MARATHON_INBOX_BUTTON_IGNORE_KEY: (
        "Ignore",
        (),
        "the Ignore button on a marathon's inbox message",
    ),
    MARATHON_INBOX_BUTTON_UNTRACK_KEY: (
        "Untrack",
        (),
        "the Untrack button on a tracked marathon's inbox message",
    ),
    MARATHON_INBOX_BUTTON_ANYWAY_KEY: (
        "Track anyway",
        (),
        "the button on an ignored marathon's inbox message that tracks it after all",
    ),
    MARATHON_INBOX_BUTTON_SITE_KEY: (
        "Open on the site",
        (),
        "the link button on a marathon's inbox message that opens its drawer on the Events page",
    ),
    MARATHON_INBOX_BUTTON_THREAD_KEY: (
        "Open the thread",
        (),
        "the link button on a tracked marathon's inbox message that opens its own thread",
    ),
    MARATHON_INBOX_NO_DATES_KEY: (
        "dates not published yet",
        (),
        "the When line of a marathon whose schedule has no dates yet",
    ),
    MARATHON_INBOX_NO_SCHEDULE_KEY: (
        "not out yet",
        (),
        "the Schedule line of a marathon whose schedule has no runs yet",
    ),
    MARATHON_INBOX_SCHEDULE_KEY: (
        "{runs} runs · {baf} BaF",
        ("runs", "baf"),
        "the Schedule line of a marathon whose schedule is out. It takes {runs} {baf}",
    ),
    MARATHON_INBOX_NO_CHANNEL_KEY: (
        "no channel row",
        (),
        "the Channel line of a marathon that airs on no channel Black Bloc watches",
    ),
    MARATHON_INBOX_OPTED_OUT_KEY: (
        "opted out of marathons",
        (),
        "added to the Channel line when that channel row is opted out of marathons",
    ),
    MARATHON_TRACK_REFUSED_KEY: (
        "{marathon}'s channel is opted out of marathons — opt it back in on Go-live first, so "
        "nothing was tracked.",
        ("marathon",),
        "the refusal when Track is pressed on a marathon whose channel is opted out of "
        "marathons. It takes {marathon}",
    ),
    MARATHON_NOT_TRACKED_KEY: (
        "**{marathon}** is not tracked, so it posts nothing — press **Track** first.",
        ("marathon",),
        "the refusal when staff ask an untracked marathon to post (the board, a shoutout). It "
        "takes {marathon}",
    ),
    MARATHON_TRACKED_SAID_KEY: (
        "**{marathon}** is tracked — its board, reminders and shoutouts post in {where}.",
        ("marathon", "where"),
        "what staff are told once Track has tracked a marathon. It takes {marathon} {where}",
    ),
    MARATHON_UNTRACKED_SAID_KEY: (
        "**{marathon}** is not tracked any more — it posts nothing; its thread is kept, archived.",
        ("marathon",),
        "what staff are told once Untrack has stopped a marathon's posts. It takes {marathon}",
    ),
    MARATHON_IGNORED_SAID_KEY: (
        "**{marathon}** is ignored — it stays on the list and is read, and posts nothing. "
        "**Track anyway** changes that.",
        ("marathon",),
        "what staff are told once Ignore has quieted a marathon. It takes {marathon}",
    ),
    MARATHON_LINK_CHANGED_SAID_KEY: (
        "**{marathon}** reads its schedule from the new link now — its tracking, thread, event and "
        "switches are kept. {read}",
        ("marathon", "read"),
        "what staff are told once Change the schedule link… has moved a marathon to a new "
        "schedule. It takes {marathon} {read}",
    ),
    MARATHON_LINK_SAME_KEY: (
        "**{marathon}** already reads that link, so nothing was changed.",
        ("marathon",),
        "what staff are told when Change the schedule link… is given the link the marathon already "
        "reads. It takes {marathon}",
    ),
    MARATHON_LINK_TAKEN_KEY: (
        "**{other}** already follows that schedule, so **{marathon}**'s link was not changed.",
        ("marathon", "other"),
        "the refusal when Change the schedule link… is given a link another marathon on the list "
        "already follows. It takes {marathon} {other}",
    ),
    MARATHON_LINK_UNREADABLE_KEY: (
        "Black Bloc could not read that schedule, so **{marathon}**'s link was not changed: "
        "{reason}",
        ("marathon", "reason"),
        "the refusal when the new schedule link will not read. It takes {marathon} {reason}",
    ),
    MARATHON_FEED_SEARCH_MOVE_KEY: (
        "Search words…",
        (),
        "the button on a horaro.net events feed's card in /event ▸ Sources that "
        "opens its search words and owner",
    ),
    MARATHON_FEED_SEARCH_TITLE_KEY: (
        "What this feed searches horaro.net for",
        (),
        "the title of the Search words… window on a horaro.net events feed "
        "(Discord cuts it at 45 characters)",
    ),
    MARATHON_FEED_WORDS_LABEL_KEY: (
        "Search words — commas between them",
        (),
        "the Search words box in that window (Discord cuts it at 45 characters)",
    ),
    MARATHON_FEED_OWNER_LABEL_KEY: (
        "Owner — the horaro.net account, if any",
        (),
        "the Owner box in that window (Discord cuts it at 45 characters)",
    ),
    MARATHON_FEED_SEARCH_LINE_KEY: (
        "Searches horaro.net for **{words}**.",
        ("words",),
        "the line on a horaro.net events feed's card naming what it searches for. It takes {words}",
    ),
    MARATHON_FEED_OWNER_LINE_KEY: (
        "Also keeps every event the horaro.net account **{owner}** owns.",
        ("owner",),
        "the line on a horaro.net events feed's card when it has an owner. It takes {owner}",
    ),
    MARATHON_FEED_WORDS_SAID_KEY: (
        "**{feed}** searches horaro.net for **{words}** now.",
        ("feed", "words"),
        "what staff are told once a horaro.net events feed's search words change. "
        "It takes {feed} {words}",
    ),
    MARATHON_FEED_WORDS_CLEARED_KEY: (
        "**{feed}** searches horaro.net by its name again.",
        ("feed",),
        "what staff are told once a horaro.net events feed's search words are "
        "cleared. It takes {feed}",
    ),
    MARATHON_FEED_OWNER_SAID_KEY: (
        "**{feed}** also keeps every event the horaro.net account **{owner}** owns now.",
        ("feed", "owner"),
        "what staff are told once a horaro.net events feed's owner is set. It takes {feed} {owner}",
    ),
    MARATHON_FEED_OWNER_CLEARED_KEY: (
        "**{feed}** keeps only the events that name the channel's Twitch again.",
        ("feed",),
        "what staff are told once a horaro.net events feed's owner is cleared. It takes {feed}",
    ),
    MARATHON_FEED_SEARCH_REFUSED_KEY: (
        "Only a horaro.net events feed has search words and an owner, so "
        "**{feed}** was not changed.",
        ("feed",),
        "the refusal when search words or an owner are given to a feed of another "
        "kind. It takes {feed}",
    ),
    MARATHON_FEED_WORDS_BAD_KEY: (
        "A feed takes at most {most} search words of {longest} characters or "
        "fewer each, so **{feed}** was not changed.",
        ("feed", "most", "longest"),
        "the refusal when there are too many search words or one is too long. It "
        "takes {feed} {most} {longest}",
    ),
    MARATHON_FEED_OWNER_BAD_KEY: (
        "A horaro.net account name is {longest} characters or fewer, so "
        "**{feed}** was not changed.",
        ("feed", "longest"),
        "the refusal when the owner given is too long. It takes {feed} {longest}",
    ),
    MARATHON_INBOX_POSTED_SAID_KEY: (
        "**{marathon}**'s inbox message is up — its Schedule line says it is not out yet, and the "
        "same message is edited when the runs arrive.",
        ("marathon",),
        "what staff are told once Post it to the inbox now has posted a marathon's inbox message "
        "before its schedule is out. It takes {marathon}",
    ),
    MARATHON_INBOX_ALREADY_KEY: (
        "**{marathon}** already has its inbox message, so nothing was posted.",
        ("marathon",),
        "the refusal when Post it to the inbox now is pressed on a marathon whose inbox message is "
        "already up. It takes {marathon}",
    ),
    MARATHON_INBOX_POST_OFF_KEY: (
        "Marathon posts are off, so **{marathon}**'s inbox message was not posted — set "
        "marathon_mode to shadow or on first.",
        ("marathon",),
        "the refusal when Post it to the inbox now is pressed while marathon posts are off. It "
        "takes {marathon}",
    ),
    MARATHON_INBOX_POST_FAILED_KEY: (
        "**{marathon}**'s inbox message could not be posted just now — the Logs page says why "
        "(marathon.inbox_failed).",
        ("marathon",),
        "the refusal when Post it to the inbox now could not reach the inbox thread. It takes "
        "{marathon}",
    ),
    MARATHON_CONTROLS_EVENT_ON_KEY: (
        "Marathon event: on · turn off",
        (),
        "the thread controls' marathon-event button while the marathon makes its one event",
    ),
    MARATHON_CONTROLS_EVENT_OFF_KEY: (
        "Marathon event: off · turn on",
        (),
        "the thread controls' marathon-event button while the marathon makes no event of its own",
    ),
    MARATHON_CONTROLS_NO_CHANNEL_KEY: (
        "**{marathon}** has no channel yet, so there is no spotlight to start — pick the channel "
        "it airs on, on the site or in /event, first.",
        ("marathon",),
        "the line under the thread controls, and the answer, while a marathon has no channel. It "
        "takes {marathon}",
    ),
    MARATHON_CONTROLS_KEPT_REFUSED_KEY: (
        "twitch.tv/{channel} is spotlit and kept for ever, so it was not turned off here — "
        "change it on the Go-live page if that is really meant.",
        ("channel",),
        "the answer when the thread controls' spotlight button is pressed on a channel whose "
        "spotlight is kept for ever. It takes {channel}",
    ),
    MARATHON_CONTROLS_NO_END_KEY: (
        "**{marathon}** has no run times yet, or its last run is over, so there is no end to "
        "hold the spotlight until — nothing was changed. Turn it on from the Go-live page "
        "instead.",
        ("marathon",),
        "the refusal when Spotlight start is pressed on a marathon with no span still ahead. It "
        "takes {marathon}",
    ),
    MARATHON_CONTROLS_STARTED_KEY: (
        "twitch.tv/{channel} is spotlit for **{marathon}** until {until} — its last run plus "
        "{tail} minutes, and it moves if the schedule does.",
        ("channel", "marathon", "until", "tail"),
        "the answer once the thread controls started a marathon's spotlight. It takes {channel} "
        "{marathon} {until} {tail}",
    ),
    MARATHON_CONTROLS_ALREADY_ON_KEY: (
        "twitch.tv/{channel} is already spotlit, so nothing was changed.",
        ("channel",),
        "the answer when Spotlight start is pressed on a channel that is already spotlit. It "
        "takes {channel}",
    ),
    MARATHON_CONTROLS_WAITS_KEY: (
        "Spotlight is set to start {lead} minutes before the first run — {when} — and end "
        "{tail} minutes after the last.",
        ("lead", "when", "tail", "channel", "marathon"),
        "the answer when Spotlight start is pressed before the marathon is near: nothing is "
        "spotlit yet, the marathon's follow turns it on in time. It takes {lead} {when} {tail} "
        "{channel} {marathon}",
    ),
    MARATHON_HOST_EVENTS_GONE_KEY: (
        "BaF host events left this switch: they follow BaF run/host events in the marathon's "
        "drawer on the site. Nothing was changed.",
        (),
        "the answer when an old BaF host events button or field is used; host events follow the "
        "one BaF run/host events setting in the marathon's drawer",
    ),
    MARATHON_CONTROLS_FOLLOW_OFF_RUNNING_KEY: (
        "**{marathon}** no longer follows the schedule. twitch.tv/{channel} stays spotlit — "
        "stop it on Go-live.",
        ("marathon", "channel"),
        "the answer when the thread controls' Spotlight switch is turned off while a spotlight "
        "staff (or another marathon) set is running; it is left on. It takes {marathon} {channel}",
    ),
    MARATHON_CONTROLS_CANCELLED_KEY: (
        "**{marathon}** will not spotlight twitch.tv/{channel} after all — the start that was "
        "set is cancelled.",
        ("marathon", "channel"),
        "the answer when the thread controls' Spotlight cancel is pressed before the marathon "
        "has started its spotlight. It takes {marathon} {channel}",
    ),
    MARATHON_CONTROLS_CANNOT_WAIT_KEY: (
        "**{marathon}** is not near yet, and its spotlight cannot start itself — the marathon "
        "spotlight is off in Settings, or twitch.tv/{channel} is off for marathons. Nothing was "
        "changed; turn the spotlight on again within {lead} minutes of the first run, or set "
        "dates on the Go-live page.",
        ("marathon", "channel", "lead"),
        "the refusal when Spotlight start is pressed before the marathon is near while nothing "
        "would turn the spotlight on in time. It takes {marathon} {channel} {lead}",
    ),
    MARATHON_CONTROLS_PING_ON_KEY: (
        "Ping the marathon role: on · turn off",
        (),
        "the thread controls' ping button while the marathon's reminders, shoutouts and public "
        "posts mention the runner's and the channel's ping roles",
    ),
    MARATHON_CONTROLS_PING_OFF_KEY: (
        "Ping the marathon role: off · turn on",
        (),
        "the thread controls' ping button while the marathon mentions no role",
    ),
    MARATHON_PUBLIC_REMINDER_TEMPLATE_KEY: (
        "{member} {part} **{game}** ({category}) on **{marathon}** {in} — {when}. {url}",
        MARATHON_REMINDER_FIELDS,
        "the public copy of a reminder before a BaF run, posted in marathon_reminder_channel_id "
        "(the staff thread's copy is marathon_reminder_template). It takes {member} {game} "
        "{category} {in} {when} {url} {marathon} {part}",
    ),
    MARATHON_NEAR_MISS_POST_KEY: (
        "**{runner}** on the schedule looks like {member} ({display_name}) — link them?",
        MARATHON_NEAR_MISS_FIELDS,
        "the near-miss post in a tracked marathon's thread: a runner nobody linked whose name is "
        "a member's Discord username. It takes {runner} {member} {username} {display_name} "
        "{marathon}; {member} names the member without pinging",
    ),
    MARATHON_NEAR_MISS_HERE_KEY: (
        "Link (this marathon)",
        (),
        "the near-miss post's button that links the runner to the member on this marathon only",
    ),
    MARATHON_NEAR_MISS_EVERYWHERE_KEY: (
        "Link everywhere",
        (),
        "the near-miss post's button that links the runner to the member on every marathon",
    ),
    MARATHON_NEAR_MISS_NOT_KEY: (
        "Not them",
        (),
        "the near-miss post's button that says the runner is not that member",
    ),
    MARATHON_NEAR_MISS_LINKED_KEY: (
        "**{runner}** is {member} ({display_name}) on **{marathon}** — linked by {staff}.",
        MARATHON_NEAR_MISS_DONE_FIELDS,
        "what a near-miss post becomes after Link (this marathon). It takes {runner} {member} "
        "{username} {display_name} {marathon} {staff}",
    ),
    MARATHON_NEAR_MISS_LINKED_EVERYWHERE_KEY: (
        "**{runner}** is {member} ({display_name}) on every marathon — linked by {staff}.",
        MARATHON_NEAR_MISS_DONE_FIELDS,
        "what a near-miss post becomes after Link everywhere. It takes {runner} {member} "
        "{username} {display_name} {marathon} {staff}",
    ),
    MARATHON_NEAR_MISS_DISMISSED_KEY: (
        "**{runner}** is not {member} ({display_name}) — {staff} said so, and **{marathon}** "
        "will not ask again.",
        MARATHON_NEAR_MISS_DONE_FIELDS,
        "what a near-miss post becomes after Not them. It takes {runner} {member} {username} "
        "{display_name} {marathon} {staff}",
    ),
    MARATHON_NEAR_MISS_DISMISSED_SAID_KEY: (
        "Noted — **{runner}** stays unlinked on **{marathon}**. People… can still link them if "
        "that changes.",
        MARATHON_NEAR_MISS_FIELDS,
        "the answer staff see after Not them on a near-miss post. It takes {runner} {member} "
        "{username} {display_name} {marathon}",
    ),
    MARATHON_NEAR_MISS_GONE_KEY: (
        "That near-miss post is no longer on record, so nothing was changed. People… on the "
        "marathon can still link the runner.",
        (),
        "the refusal when a near-miss button is pressed on a post the bot has no record of",
    ),
    MARATHON_NEAR_MISS_ANSWERED_KEY: (
        "Staff already answered this near miss for **{runner}**, so nothing was changed.",
        MARATHON_NEAR_MISS_FIELDS,
        "the answer when a near-miss button is pressed after staff already answered it. It takes "
        "{runner} {member} {username} {display_name} {marathon}",
    ),
    MARATHON_PUBLIC_TEMPLATE_KEY: (
        "**{runner}** {part} **{game}** — {category} on **{marathon}** · {when} ({relative}) · "
        "{state} · {url}",
        MARATHON_PUBLIC_FIELDS,
        "a BaF run's public highlight, edited in place as its slot moves and it goes live; "
        "once it ends it becomes marathon_public_done_template. It takes {runner} {mention} "
        "{game} {category} {part} {when} {relative} {url} {marathon} {state}; {mention} names "
        "the member without pinging",
    ),
    MARATHON_PUBLIC_DONE_TEMPLATE_KEY: (
        "**{runner}** {part} **{game}** — {category} {day} on **{marathon}** · {url}",
        MARATHON_PUBLIC_DONE_FIELDS,
        "what a BaF run's public highlight is edited to once the run is over (a host's: once "
        "their block is): the past tense, with no role mention, and the edit notifies nobody. "
        "It takes the same words as marathon_public_template and {day}; {part} is the "
        "past-tense word (marathon_part_runner_done, marathon_part_host_done)",
    ),
    MARATHON_PUBLIC_DAY_TODAY_KEY: (
        "today",
        (),
        "{day} on a finished run's public highlight while it is still the day the run ended, "
        "by the server's time zone (default_timezone)",
    ),
    MARATHON_PUBLIC_DAY_EARLIER_KEY: (
        "on {date}",
        ("date",),
        "{day} on a finished run's public highlight once the day the run ended has passed, by "
        "the server's time zone. It takes {date}, the day the run ended, drawn by Discord in "
        "each reader's own language",
    ),
    MARATHON_PUBLIC_REMOVED_KEY: (
        "Staff took down the highlight for **{runner}** on **{marathon}**.",
        MARATHON_PUBLIC_FIELDS,
        "what a public highlight is edited to when everyone it names is opted out; it is not "
        "updated after unless they opt back in. It takes the same words as "
        "marathon_public_template",
    ),
    MARATHON_UNIGNORED_SAID_KEY: (
        "**{marathon}** is not ignored any more — it is found, not tracked, and posts nothing "
        "until someone presses **Track**.",
        ("marathon",),
        "what staff are told once an ignored marathon is put back to found. It takes {marathon}",
    ),
    MARATHON_BOARD_TEMPLATE_KEY: (
        "**{marathon}** — BaF on the schedule ({count}), {starts} to {ends}. {url}",
        MARATHON_BOARD_FIELDS,
        "the head of a marathon's board, the one message edited in place as the schedule moves. "
        "It takes {marathon} {count} {starts} {ends} {url}",
    ),
    MARATHON_BOARD_LINE_KEY: (
        "{when} ({relative}) · **{game}** — {category} · {member} {part} · {state}",
        MARATHON_LINE_FIELDS,
        "one line of the board per BaF run, used only while marathon_runner_posts is off "
        "(on, each run has its own post instead). It takes {member} {game} {category} {when} "
        "{relative} {part} {state}; {when} and {relative} show in each reader's own time zone",
    ),
    MARATHON_RUNNER_POST_TEMPLATE_KEY: (
        "**{runner}** ({mention}) {part} **{game}** — {category} · {when} ({relative}) · "
        "{state} · <{url}>",
        MARATHON_RUNNER_POST_FIELDS,
        "a BaF run's own post in the marathon's thread, pinned and edited in place; it names "
        "the member and never pings. It takes {runner} {mention} {game} {category} {part} "
        "{when} {relative} {url} {marathon} {state}",
    ),
    MARATHON_RUNNER_POST_UNLISTED_KEY: (
        "no longer counted as BaF",
        (),
        "{state} on a BaF run's own post once staff unlink its runner, so nobody from BaF is "
        "on it any more",
    ),
    MARATHON_BOARD_EMPTY_KEY: (
        "Nobody from BaF is on this schedule yet. Black Bloc keeps reading it.",
        (),
        "the board's only line while no BaF run has been found",
    ),
    MARATHON_PING_ROLE_ON_SAID_KEY: (
        "**{marathon}** pings again: its run reminders and shoutouts mention the runner's and "
        "the channel's ping roles, and its channel has a ping window while it runs.",
        ("marathon",),
        "what staff are told once a marathon's Ping the role switch is turned on. It takes "
        "{marathon}",
    ),
    MARATHON_PING_ROLE_OFF_SAID_KEY: (
        "**{marathon}** pings no role now: its reminders and shoutouts still post, with no "
        "mention, and its channel has no ping window for it.",
        ("marathon",),
        "what staff are told once a marathon's Ping the role switch is turned off. It takes "
        "{marathon}",
    ),
    MARATHON_PING_ROLE_SAME_KEY: (
        "**{marathon}** already has that, so nothing was changed.",
        ("marathon",),
        "what staff are told when the Ping the role switch is already where they asked. It "
        "takes {marathon}",
    ),
    MARATHON_PING_ROLE_LINE_ON_KEY: (
        "Pings the role",
        (),
        "the marathon card's line while its reminders and shoutouts mention roles",
    ),
    MARATHON_PING_ROLE_LINE_OFF_KEY: (
        "Pings no role",
        (),
        "the marathon card's line while its reminders and shoutouts mention no role",
    ),
    MARATHON_ROLE_PING_LINE_ON_KEY: (
        "The public heads-up {minutes} minutes before a BaF run mentions {role}.",
        ("role", "minutes"),
        "the line under a marathon's ping switch (thread controls and the marathon drawer) while "
        "the Marathon role will be mentioned. It takes {role} {minutes}; {role} names the role "
        "without pinging",
    ),
    MARATHON_ROLE_PING_LINE_KEY_OFF_KEY: (
        "The Marathon role is not mentioned: {key} is off.",
        ("key",),
        "the line under a marathon's ping switch while a setting keeps the Marathon role out of "
        "the heads-up. It takes {key}, the setting that is off",
    ),
    MARATHON_ROLE_PING_LINE_ANNOUNCEMENTS_OFF_KEY: (
        "The Marathon role is not mentioned: this marathon's runner and host announcements "
        "are both off, so no public heads-up posts.",
        (),
        "the line under a marathon's ping switch while its Runner and Host announcements are "
        "both off",
    ),
    MARATHON_ROLE_PING_LINE_REHEARSAL_KEY: (
        "The Marathon role is not mentioned while marathon posts rehearse: marathon_mode is "
        "not on, and a rehearsal copy never pings it.",
        (),
        "the line under a marathon's ping switch while marathon_mode is shadow or off",
    ),
    MARATHON_ROLE_PING_LINE_UNSET_KEY: (
        "The Marathon role is not mentioned: no role is picked in marathon_role_id.",
        (),
        "the line under a marathon's ping switch while no Marathon role is picked",
    ),
    MARATHON_ROLE_PING_LINE_GONE_KEY: (
        "The Marathon role is not mentioned: the role in marathon_role_id is no longer in this "
        "server.",
        (),
        "the line under a marathon's ping switch while the picked Marathon role has been deleted",
    ),
    MARATHON_ROLE_PING_LINE_NOT_MENTIONABLE_KEY: (
        "The Marathon role is not mentioned: {role} is not mentionable and Black Bloc may not "
        "mention every role, so a mention would notify nobody.",
        ("role",),
        "the line under a marathon's ping switch while Discord would not notify the Marathon "
        "role: it is not set mentionable and the bot lacks Mention Everyone. It takes {role}",
    ),
    MARATHON_CHANNEL_PING_HELP_KEY: (
        "During events pings while one of its marathons runs.",
        (),
        "the state line under the Pings choice on a marathon channel's Go-live drawer and the "
        "marathon drawer: when During events pings there",
    ),
    MARATHON_REMINDER_TEMPLATE_KEY: (
        "{member} {part} **{game}** ({category}) on **{marathon}** {in} — {when}. {url}",
        MARATHON_REMINDER_FIELDS,
        "a reminder before a BaF run. It takes {member} {game} {category} {in} {when} {url} "
        "{marathon} {part}",
    ),
    MARATHON_REMINDER_DROPPED_TEMPLATE_KEY: (
        "{member} {part} **{game}** ({category}) on **{marathon}** — {state}.",
        MARATHON_REMINDER_DROPPED_FIELDS,
        "what a posted reminder is rewritten to — the staff thread's copy and the public copy "
        "alike — when its run is taken off the schedule while marathon_reminder_on_move is edit. "
        "{state} is marathon_state_dropped. It takes {member} {game} {category} {in} {when} {url} "
        "{marathon} {part} {state}",
    ),
    MARATHON_LIVE_TEMPLATE_KEY: (
        "{member} {part} **{game}** ({category}) on **{marathon}** right now! {url}",
        MARATHON_LIVE_FIELDS,
        "the shoutout the moment a BaF run goes live. It takes {member} {game} {category} "
        "{url} {marathon} {part}",
    ),
    MARATHON_DONE_TEMPLATE_KEY: (
        "{member} {part} **{game}** ({category}) on **{marathon}** — that run is over. Thanks "
        "for cheering!",
        MARATHON_LIVE_FIELDS,
        "what a shoutout is rewritten to once the run is over. It takes the same words as "
        "marathon_live_template and never pings",
    ),
    MARATHON_PART_RUNNER_KEY: ("runs", (), "{part} for a runner"),
    MARATHON_PART_HOST_KEY: ("hosts", (), "{part} for a host"),
    MARATHON_PART_COMMENTATOR_KEY: ("is on commentary", (), "{part} for a commentator"),
    MARATHON_PART_RUNNER_DONE_KEY: (
        "ran",
        (),
        "{part} for a runner once the run is over, on its public highlight "
        "(marathon_public_done_template)",
    ),
    MARATHON_PART_HOST_DONE_KEY: (
        "hosted",
        (),
        "{part} for a host once their host block is over, on its public highlight "
        "(marathon_public_done_template)",
    ),
    MARATHON_PART_COMMENTATOR_DONE_KEY: (
        "was on commentary",
        (),
        "{part} for a commentator once the run is over, on its public highlight "
        "(marathon_public_done_template)",
    ),
    MARATHON_STATE_UPCOMING_KEY: (
        "coming up",
        (),
        "{state} on the board and a run's own post for a run not yet on",
    ),
    MARATHON_STATE_LIVE_KEY: (
        "on now",
        (),
        "{state} on the board and a run's own post for the run on now",
    ),
    MARATHON_STATE_DONE_KEY: (
        "done",
        (),
        "{state} on the board and a run's own post for a run that is over",
    ),
    MARATHON_STATE_DROPPED_KEY: (
        "off the schedule",
        (),
        "{state} on the board and a run's own post for a run the schedule no longer lists",
    ),
    MARATHON_UNKNOWN_SITE_KEY: (
        "I can read the GDQ and RPG Limit Break trackers, horaro.net schedules, Oengus "
        "marathons, Fastest Furs schedules, Lady Arcaders calendars and the GDQ Hotfix schedule "
        "— that link is none of them.",
        (),
        "what staff are told when a schedule link is from a site Black Bloc cannot read",
    ),
    MARATHON_ALREADY_ADDED_KEY: (
        "**{name}** already follows that schedule, so nothing was added.",
        ("name",),
        "what staff are told when a schedule link is already on the list. It takes {name}",
    ),
    MARATHON_COULD_NOT_READ_KEY: (
        "Black Bloc could not read that schedule, so nothing was added: {reason}",
        ("reason",),
        "what staff are told when a schedule link will not read. It takes {reason}",
    ),
    MARATHON_NO_RUNS_YET_KEY: (
        "**{marathon}** has no runs published yet — Black Bloc keeps checking and fills the "
        "list the moment the schedule goes up.",
        ("marathon",),
        "what the page and the panel say about a marathon whose schedule is not published yet. "
        "It takes {marathon}",
    ),
    MARATHON_NEXT_TEMPLATE_KEY: (
        "{marathon} is over — the next GDQ event is **{next}**, {when} ({relative}). Add it?",
        MARATHON_NEXT_FIELDS,
        "the staff notice when a GDQ marathon is over and the tracker lists another event ahead. "
        "It takes {marathon} {next} {when} {relative} {url}",
    ),
    MARATHON_NEXT_NONE_TEMPLATE_KEY: (
        "{marathon} is over and the GDQ tracker lists nothing ahead yet — Look again later.",
        ("marathon",),
        "what staff are told when a GDQ marathon is over and the tracker lists no event ahead. "
        "It takes {marathon}",
    ),
    MARATHON_NEXT_ADDED_TEMPLATE_KEY: (
        "Added **{next}** — it will be read from {url}.",
        MARATHON_NEXT_FIELDS,
        "what the staff notice is rewritten to once the next event is added. It takes "
        "{marathon} {next} {when} {relative} {url}",
    ),
    MARATHON_FEED_ADDED_TEMPLATE_KEY: (
        "{feed} has a new event: **{event}**, {when} — added. It will be read from its schedule.",
        MARATHON_FEED_FIELDS,
        "the line above a feed-found marathon's message in the marathon inbox thread, where "
        "Track and Ignore are. It takes {feed} {event} {when} {relative} {url} {channel}",
    ),
    MARATHON_FEED_SUGGEST_TEMPLATE_KEY: (
        "{feed} has a new event: **{event}**, {when} ({relative}). Add it?",
        MARATHON_FEED_FIELDS,
        "the staff notice when a feed in suggest mode finds a new event; it carries Add it and "
        "Not this one. It takes {feed} {event} {when} {relative} {url} {channel}",
    ),
    MARATHON_HOTFIX_HOSTS_TEMPLATE_KEY: (
        "Tracked because **{people}** hosts it.",
        MARATHON_HOTFIX_BECAUSE_FIELDS,
        "the line under a Hotfix feed's notice when it took a show that is not in "
        "marathon_hotfix_shows because a BaF person hosts it. It takes {people} {show}",
    ),
    MARATHON_HOTFIX_RUNS_TEMPLATE_KEY: (
        "Tracked because **{people}** runs in it.",
        MARATHON_HOTFIX_BECAUSE_FIELDS,
        "the line under a Hotfix feed's notice when it took a show that is not in "
        "marathon_hotfix_shows because a BaF person runs in it. It takes {people} {show}",
    ),
    MARATHON_RUN_EVENT_TITLE_KEY: (
        "{member} runs {game} at {marathon}",
        MARATHON_RUN_EVENT_FIELDS,
        "what an event made for one BaF run is called. {member} is every BaF member on "
        "the run, their names joined. It takes {member} {game} {category} {marathon}",
    ),
    MARATHON_RUN_EVENT_DESCRIPTION_KEY: (
        "{category} · {marathon} · read from the schedule; times follow it.",
        MARATHON_RUN_EVENT_FIELDS,
        "what an event made for one BaF run says about itself. It takes {member} {game} "
        "{category} {marathon}",
    ),
    MARATHON_NOTICE_TITLE_KEY: (
        "New marathon: {name}",
        ("name",),
        "retired 2026-09 — notices post in the marathon inbox thread, not as events-forum posts. "
        "Kept so old rows still read; nothing reads it any more. It takes {name}",
    ),
    MARATHON_SPOTLIGHT_NOTE_KEY: (
        "{name} at {marathon}",
        ("name", "marathon"),
        "the note a runner's channel row carries on the Go-live page when Spotlight… on a "
        "marathon's People card adds it. It takes {name} {marathon}",
    ),
    MARATHON_EVENT_DESCRIPTION_KEY: (
        "{marathon} — read from the GDQ schedule. BaF runs are boarded in {channel}.",
        MARATHON_EVENT_FIELDS,
        "what a marathon's event says about itself in the events review, the announcement and "
        "the Discord scheduled event. It takes {marathon} {channel}",
    ),
}
MARATHON_RANGES: dict[str, tuple[int, int]] = {
    MARATHON_POLL_MINUTES_KEY: (10, 120),
    MARATHON_FAR_POLL_HOURS_KEY: (1, 168),
    MARATHON_LEAD_DAYS_KEY: (1, 60),
    MARATHON_MOVE_MINUTES_KEY: (1, 120),
    MARATHON_SETUP_MINUTES_KEY: (0, MARATHON_SETUP_MAX),
    MARATHON_EARLY_START_KEY: (0, 240),
    MARATHON_LATE_GRACE_KEY: (0, 360),
    MARATHON_PING_MINUTES_KEY: (0, 240),
    MARATHON_REMINDER_STALE_KEY: (1, 240),
    MARATHON_REMINDER_EDIT_LIMIT_KEY: (1, 50),
    MARATHON_TRACKER_REFRESH_KEY: (10, 300),
    MARATHON_WINDOW_SLACK_KEY: (0, 24),
    MARATHON_SPOTLIGHT_LEAD_KEY: (0, 48),
    MARATHON_SPOTLIGHT_SLACK_KEY: (0, 48),
    MARATHON_SPOTLIGHT_LEAD_MINUTES_KEY: (0, 240),
    MARATHON_SPOTLIGHT_TAIL_KEY: (0, 720),
    MARATHON_FEED_HOURS_KEY: (1, 168),
    MARATHON_FEED_RECENT_KEY: (0, 30),
    MARATHON_ARCHIVE_AFTER_DAYS_KEY: (0, 365),
    MARATHON_LADYARCADERS_FLOOR_KEY: (1, 99999),
    MARATHON_BAF_EVENT_MIN_RUNS_KEY: (1, 50),
    MARATHON_BAF_EVENT_ASK_PERCENT_KEY: (1, 100),
    MARATHON_BAF_EVENT_PING_MINUTES_KEY: (1, 1440),
}


def marathon_marks(given: Any) -> tuple[int, ...] | None:
    """One to six whole minutes, 1–1440, in any order; anything else is None."""
    parts = [one.strip() for one in str(given or "").split(",")]
    if not parts or len(parts) > MARATHON_MARKS_MAX or not all(one.isdigit() for one in parts):
        return None
    found = tuple(int(one) for one in parts)
    if not all(1 <= one <= MARATHON_MARK_MAX_MINUTES for one in found):
        return None
    return found


def checked_marks(given: Any) -> str:
    text = str(given or "").strip()
    found = marathon_marks(text)
    if found is None:
        raise SettingError(
            MARATHON_BAD_MARKS.format(
                given=text[:40], most=MARATHON_MARKS_MAX, limit=MARATHON_MARK_MAX_MINUTES
            )
        )
    return ", ".join(str(one) for one in sorted(set(found), reverse=True))


def checked_retro(given: Any) -> str:
    """One Twitch category name, trimmed, never blank."""
    text = " ".join(str(given or "").split())
    if not text or len(text) > MARATHON_RETRO_LENGTH:
        raise SettingError(
            MARATHON_BAD_RETRO.format(given=text[:40] or "Nothing", longest=MARATHON_RETRO_LENGTH)
        )
    return text


def checked_shows(given: Any) -> str:
    """One to twenty show names, each once whatever its capitals, trimmed."""
    text = str(given or "").strip()
    found: list[str] = []
    for part in text.split(","):
        name = " ".join(part.split())
        if name and name.lower() not in {one.lower() for one in found}:
            found.append(name)
    if not found or len(found) > MARATHON_HOTFIX_SHOWS_MAX or any(
        len(one) > MARATHON_HOTFIX_SHOW_LENGTH for one in found
    ):
        raise SettingError(
            MARATHON_BAD_SHOWS.format(
                given=text[:40] or "Nothing",
                most=MARATHON_HOTFIX_SHOWS_MAX,
                longest=MARATHON_HOTFIX_SHOW_LENGTH,
            )
        )
    return ", ".join(found)


def checked_baf_names(given: Any) -> str:
    """One to twenty show names, each once whatever its capitals and spacing, trimmed."""
    text = str(given or "").strip()
    found: list[str] = []
    seen: set[str] = set()
    for part in text.split(","):
        name = " ".join(part.split())
        fold = "".join(one for one in name.lower() if one.isalnum())
        if fold and fold not in seen:
            seen.add(fold)
            found.append(name)
    if not found or len(found) > MARATHON_BAF_EVENT_NAMES_MAX or any(
        len(one) > MARATHON_BAF_EVENT_NAME_LENGTH for one in found
    ):
        raise SettingError(
            MARATHON_BAD_BAF_NAMES.format(
                given=text[:40] or "Nothing",
                most=MARATHON_BAF_EVENT_NAMES_MAX,
                longest=MARATHON_BAF_EVENT_NAME_LENGTH,
            )
        )
    return ", ".join(found)


def checked_viewer_url(given: Any) -> str:
    """One public https page, kept as typed; a blank turns the viewer off."""
    text = str(given or "").strip()
    if not text:
        return ""
    bad = SettingError(
        MARATHON_BAD_VIEWER.format(given=text[:60], longest=MARATHON_HOTFIX_VIEWER_URL_LENGTH)
    )
    if len(text) > MARATHON_HOTFIX_VIEWER_URL_LENGTH or any(ch.isspace() for ch in text):
        raise bad
    try:
        parts = urlsplit(text)
        port = parts.port
    except ValueError:
        raise bad from None
    host = (parts.hostname or "").lower()
    numbers = ":" in host or all(part.isdigit() for part in host.split("."))
    if parts.scheme.lower() != "https" or port is not None or parts.username is not None:
        raise bad
    if parts.password is not None or "." not in host or numbers:
        raise bad
    if host.endswith(MARATHON_HOTFIX_VIEWER_INNER):
        raise bad
    return text


def checked_marathon(fields: tuple[str, ...]) -> Any:
    def check(given: Any) -> str:
        text = str(given or "").strip()
        stray = next(
            (one.strip() for one in PLACEHOLDERS.findall(text) if one.strip() not in fields),
            None,
        )
        if stray is not None:
            raise SettingError(
                MARATHON_UNKNOWN_FIELD.format(
                    found=stray[:40],
                    allowed=", ".join(f"`{{{one}}}`" for one in fields) or "nothing",
                )
            )
        return text

    return check


KEY_TYPES.update({key: kind for key, (kind, _, _) in MARATHON_SETTINGS.items()})
KEY_HELP.update({key: said for key, (_, _, said) in MARATHON_SETTINGS.items()})
KEY_TYPES.update({key: "text" for key in MARATHON_WORDS})
KEY_HELP.update({key: said for key, (_, _, said) in MARATHON_WORDS.items()})
KEY_CHOICES[MARATHON_MODE_KEY] = MARATHON_MODES
KEY_CHOICES[MARATHON_FEED_ACTION_KEY] = MARATHON_FEED_ACTIONS
KEY_CHOICES[MARATHON_FEED_NOTICE_WHEN_KEY] = MARATHON_FEED_NOTICE_WHENS
KEY_CHOICES[MARATHON_REMINDER_ON_MOVE_KEY] = MARATHON_REMINDER_ON_MOVES
KEY_CHOICES[MARATHON_EVENT_MODE_DEFAULT_KEY] = MARATHON_EVENT_MODES
KEY_CHOICES[MARATHON_NOTICE_HOME_KEY] = MARATHON_NOTICE_HOMES
KEY_CHOICES[MARATHON_CHANNEL_PING_MODE_DEFAULT_KEY] = PING_MODES
KEY_MIN.update({key: floor for key, (floor, _) in MARATHON_RANGES.items()})
KEY_MAX.update({key: ceiling for key, (_, ceiling) in MARATHON_RANGES.items()})
TEXT_CHECKS[MARATHON_REMINDER_MINUTES_KEY] = checked_marks
TEXT_CHECKS[MARATHON_HOTFIX_SHOWS_KEY] = checked_shows
TEXT_CHECKS[MARATHON_BAF_EVENT_NAMES_KEY] = checked_baf_names
TEXT_CHECKS[MARATHON_HOTFIX_VIEWER_URL_KEY] = checked_viewer_url
TEXT_MAY_BE_BLANK = (*TEXT_MAY_BE_BLANK, MARATHON_HOTFIX_VIEWER_URL_KEY)
TEXT_CHECKS[MARATHON_RETRO_CATEGORY_KEY] = checked_retro
TEXT_CHECKS.update(
    {key: checked_marathon(fields) for key, (_, fields, _) in MARATHON_WORDS.items()}
)
MARATHON_DEFAULTS: dict[str, Any] = {
    **{key: default for key, (_, default, _) in MARATHON_SETTINGS.items()},
    **{key: default for key, (default, _, _) in MARATHON_WORDS.items()},
}


# Replays on a go-live channel: detected, posted plain or skipped, and staff can treat one as live.
GOLIVE_REPLAY_ACTION_KEY = "golive_replay_action"
GOLIVE_REPLAY_WORDS_KEY = "golive_replay_words"
GOLIVE_REPLAY_LIVE_WORDS_KEY = "golive_replay_live_words"
GOLIVE_REPLAY_TEMPLATE_KEY = "golive_replay_template"
GOLIVE_REPLAY_STATE_KEY = "golive_replay_state"
GOLIVE_REPLAY_REASON_TYPE_KEY = "golive_replay_reason_type"
GOLIVE_REPLAY_REASON_TITLE_KEY = "golive_replay_reason_title"
GOLIVE_REPLAY_TREAT_LIVE_KEY = "golive_replay_treat_live_label"
GOLIVE_REPLAY_TREATED_KEY = "golive_replay_treated_said"
GOLIVE_REPLAY_NOT_REPLAY_KEY = "golive_replay_not_replay_said"
GOLIVE_REPLAY_TAG_CERTAIN_KEY = "golive_replay_tag_certain"
GOLIVE_REPLAY_REASON_TAG_KEY = "golive_replay_reason_tag"
GOLIVE_REPLAY_MIDSTREAM_POLLS_KEY = "golive_replay_midstream_polls"
GOLIVE_REPLAY_MARATHON_RUNS_KEY = "golive_replay_marathon_runs"
GOLIVE_REPLAY_MIDSTREAM_POLLS_MAX = 10
GOLIVE_REPLAY_ACTIONS = ("plain", "skip", "live")
GOLIVE_REPLAY_SETTINGS: dict[str, tuple[str, Any, tuple[str, ...] | None, str]] = {
    GOLIVE_REPLAY_ACTION_KEY: (
        "enum",
        "plain",
        None,
        "what a channel on the Go-live list gets when its stream is a replay (Twitch marks it a "
        "rerun, or its title carries a golive_replay_words word outside a marathon on the "
        "channel). plain — the default — posts the golive_replay_template sentence with no pin, "
        "no role mention and no reminders; skip posts nothing and only logs it; live treats it "
        "as a live stream, the way it was before replays were looked for. Anything uncertain is "
        "treated as live",
    ),
    GOLIVE_REPLAY_WORDS_KEY: (
        "text",
        "replay, rerun, rebroadcast, re-broadcast, vod, encore",
        (),
        "the words that make a stream title read as a replay, separated by commas. Each is "
        "matched as a whole word in any case — [REPLAY], Replay:, (Rerun) all match, and a longer "
        "word that merely contains one does not. Blank leaves only Twitch's own rerun mark",
    ),
    GOLIVE_REPLAY_LIVE_WORDS_KEY: (
        "text",
        "live",
        (),
        "the words that overrule a replay word in the same title, separated by commas — a title "
        "that says both replay and live is treated as live, because a missed live stream is the "
        "worse mistake. Blank lets a replay word decide on its own",
    ),
    GOLIVE_REPLAY_TEMPLATE_KEY: (
        "text",
        "**{name}** is showing a replay — {title} {url}",
        ("name", "game", "title", "url", "platform"),
        "the sentence posted for a replay when golive_replay_action is plain — no pin, no role "
        "mention, no reminders. It takes {name} {game} {title} {url} {platform}",
    ),
    GOLIVE_REPLAY_STATE_KEY: (
        "text",
        "Replay detected ({reason})",
        ("reason",),
        "the line the Go-live page and the /golive Channels card show for a channel whose "
        "stream right now was read as a replay. {reason} is golive_replay_reason_type or "
        "golive_replay_reason_title",
    ),
    GOLIVE_REPLAY_REASON_TYPE_KEY: (
        "text",
        "Twitch marks the stream a rerun",
        (),
        "the reason in golive_replay_state when Twitch itself marked the stream a rerun",
    ),
    GOLIVE_REPLAY_REASON_TITLE_KEY: (
        "text",
        "the title says “{word}”",
        ("word",),
        "the reason in golive_replay_state when the title carried a golive_replay_words word; "
        "{word} is the word it matched",
    ),
    GOLIVE_REPLAY_TREAT_LIVE_KEY: (
        "text",
        "Treat as live",
        (),
        "the button beside a replay on the Go-live page and the /golive Channels card that "
        "announces this stream again with the full spotlight — pin, role mentions, reminders",
    ),
    GOLIVE_REPLAY_TREATED_KEY: (
        "text",
        "**{login}** is treated as live for this stream — announced again with the full spotlight.",
        ("login",),
        "what staff are told after Treat as live; {login} is the channel",
    ),
    GOLIVE_REPLAY_NOT_REPLAY_KEY: (
        "text",
        "**{login}** is not showing a replay right now, so there was nothing to change.",
        ("login",),
        "what staff are told when Treat as live finds no replay to treat — the stream ended, "
        "or it is already treated as live; {login} is the channel",
    ),
    GOLIVE_REPLAY_TAG_CERTAIN_KEY: (
        "bool",
        True,
        None,
        "whether a golive_replay_words word that OPENS the title — inside a leading bracket, "
        "[Replay] or (Rerun), or bare before a colon, a bar or a spaced dash — is certain, the "
        "way Twitch's own rerun mark is: no golive_replay_live_words word and no marathon "
        "overrules it. on by default; off reads it as any other title word",
    ),
    GOLIVE_REPLAY_REASON_TAG_KEY: (
        "text",
        "the title opens with “{word}”",
        ("word",),
        "the reason in golive_replay_state when the title opened with a golive_replay_words "
        "tag and golive_replay_tag_certain is on; {word} is the word it matched",
    ),
    GOLIVE_REPLAY_MIDSTREAM_POLLS_KEY: (
        "int",
        2,
        None,
        "how many checks in a row a stream already announced as live must read as a replay "
        "before it is treated as one from then on — and, after that, how many in a row it must "
        "read as live before it is announced again. 2 by default, 0 to 10; 0 never looks again "
        "after the stream starts, the way it was before",
    ),
    GOLIVE_REPLAY_MARATHON_RUNS_KEY: (
        "bool",
        True,
        None,
        "whether a marathon on the channel overrules a replay word in the title only while one "
        "of its runs is scheduled around now — each day's first run less the spotlight lead to "
        "its last run plus the tail — rather than for the marathon's whole span, overnight "
        "gaps included. on by default; a marathon with no timed runs keeps its whole span",
    ),
}
KEY_TYPES.update({key: kind for key, (kind, _, _, _) in GOLIVE_REPLAY_SETTINGS.items()})
KEY_HELP.update({key: said for key, (_, _, _, said) in GOLIVE_REPLAY_SETTINGS.items()})
KEY_CHOICES[GOLIVE_REPLAY_ACTION_KEY] = GOLIVE_REPLAY_ACTIONS
KEY_MIN[GOLIVE_REPLAY_MIDSTREAM_POLLS_KEY] = 0
KEY_MAX[GOLIVE_REPLAY_MIDSTREAM_POLLS_KEY] = GOLIVE_REPLAY_MIDSTREAM_POLLS_MAX
TEXT_CHECKS.update(
    {
        key: checked_fields(fields)
        for key, (kind, _, fields, _) in GOLIVE_REPLAY_SETTINGS.items()
        if kind == "text" and fields is not None
    }
)
TEXT_MAY_BE_BLANK = (*TEXT_MAY_BE_BLANK, GOLIVE_REPLAY_WORDS_KEY, GOLIVE_REPLAY_LIVE_WORDS_KEY)
GOLIVE_REPLAY_DEFAULTS: dict[str, Any] = {
    key: default for key, (_, default, _, _) in GOLIVE_REPLAY_SETTINGS.items()
}


# Blocks live (blocks-live, 2026-09-28) — who's live now, upcoming events and link buttons. Every
# word the three blocks post is one of these. Filed under posts, except the upcoming words
# (events, by prefix): the Go-live page's drawers are pinned by golive-join.test.mjs.
GOLIVE_BLOCK_TITLE = "golive_block_title"
GOLIVE_BLOCK_LINE = "golive_block_line"
GOLIVE_BLOCK_UNTITLED = "golive_block_untitled"
GOLIVE_BLOCK_EMPTY = "golive_block_empty"
GOLIVE_BLOCK_MAX = "golive_block_max"
GOLIVE_BLOCK_TITLE_CHARS = "golive_block_title_chars"
EVENTS_UPCOMING_TITLE = "events_upcoming_title"
EVENTS_UPCOMING_LINE = "events_upcoming_line"
EVENTS_UPCOMING_EMPTY = "events_upcoming_empty"
EVENTS_UPCOMING_MAX = "events_upcoming_max"
POSTS_BLOCK_LINKS_ROWS = "posts_block_links_rows"
POSTS_BLOCK_LINKS_TITLE = "posts_block_links_title"
POSTS_BLOCK_LINKS_TEXT = "posts_block_links_text"
POSTS_BLOCK_LINKS_CARD = "posts_block_links_card"
POSTS_BLOCK_LIVE_MINUTES = "posts_block_live_minutes"
POSTS_BLOCK_LIVENOW_NAME = "posts_block_livenow_name"
POSTS_BLOCK_LIVENOW_NAME_DEFAULT = "Who's live now"
POSTS_BLOCK_UPCOMING_NAME = "posts_block_upcoming_name"
POSTS_BLOCK_UPCOMING_NAME_DEFAULT = "Upcoming events"
POSTS_BLOCK_LINKS_NAME = "posts_block_links_name"
POSTS_BLOCK_LINKS_NAME_DEFAULT = "Link buttons"
LIVE_LINE_FIELDS = ("name", "title")
UPCOMING_LINE_FIELDS = ("title", "when", "relative")
LINKS_MAX = 10
LINK_LABEL_MAX = 80
LINK_URL_MAX = 512
LINKS_NOT_JSON = (
    "The link buttons must be a list like `[{{\"label\": \"Our site\", \"url\": "
    "\"https://example.org\"}}]`, and that is not one ({why}), so nothing was changed."
)
LINKS_TOO_MANY = (
    "That is {count} link buttons and a block carries at most {limit} (two rows of five), so "
    "nothing was changed. Take {over} out and save again."
)
LINKS_BAD_ROW = "Link button {n} must have exactly a `label` and a `url`, so nothing was changed."
LINKS_NO_LABEL = "Link button {n} has no label, so nothing was changed. Give it a few words."
LINKS_LONG_LABEL = (
    "Link button {n}'s label is {length} characters and Discord allows {limit}, so nothing was "
    "changed. Shorten it and save again."
)
LINKS_BAD_URL = (
    "Link button {n}'s address must start with `https://` and name a site, with no spaces, and "
    "`{url}` does not, so nothing was changed."
)
LINKS_LONG_URL = (
    "Link button {n}'s address is {length} characters and Discord allows {limit}, so nothing "
    "was changed."
)
LINK_HOST = re.compile(r"^https://[^\s/?#@]+\.[^\s/?#@]+(?:[/?#]\S*)?$", re.IGNORECASE)


def checked_links(given: Any) -> str:
    """The link buttons as one JSON list; a bad row is refused in words, never dropped."""
    rows = given
    if isinstance(given, str):
        if not given.strip():
            return ""
        try:
            rows = json.loads(given)
        except ValueError as exc:
            raise SettingError(LINKS_NOT_JSON.format(why=str(exc)[:80])) from exc
    if not isinstance(rows, list):
        raise SettingError(LINKS_NOT_JSON.format(why="it is not a list"))
    if len(rows) > LINKS_MAX:
        raise SettingError(
            LINKS_TOO_MANY.format(count=len(rows), limit=LINKS_MAX, over=len(rows) - LINKS_MAX)
        )
    kept: list[dict[str, str]] = []
    for n, row in enumerate(rows, start=1):
        if not isinstance(row, dict) or set(row) != {"label", "url"}:
            raise SettingError(LINKS_BAD_ROW.format(n=n))
        label = row["label"].strip() if isinstance(row["label"], str) else ""
        url = row["url"].strip() if isinstance(row["url"], str) else ""
        if not label:
            raise SettingError(LINKS_NO_LABEL.format(n=n))
        if len(label) > LINK_LABEL_MAX:
            raise SettingError(
                LINKS_LONG_LABEL.format(n=n, length=len(label), limit=LINK_LABEL_MAX)
            )
        if len(url) > LINK_URL_MAX:
            raise SettingError(LINKS_LONG_URL.format(n=n, length=len(url), limit=LINK_URL_MAX))
        if not LINK_HOST.match(url):
            raise SettingError(LINKS_BAD_URL.format(n=n, url=url[:80]))
        kept.append({"label": label, "url": url})
    return json.dumps(kept, ensure_ascii=False) if kept else ""


BLOCKS_LIVE_DEFAULTS: dict[str, Any] = {
    GOLIVE_BLOCK_TITLE: "Live now",
    GOLIVE_BLOCK_LINE: "**{name}** — {title}",
    GOLIVE_BLOCK_UNTITLED: "watch the stream",
    GOLIVE_BLOCK_EMPTY: "Nobody is live right now. This card updates itself when someone is.",
    GOLIVE_BLOCK_MAX: 10,
    GOLIVE_BLOCK_TITLE_CHARS: 60,
    EVENTS_UPCOMING_TITLE: "Coming up",
    EVENTS_UPCOMING_LINE: "**{title}** — {when} ({relative})",
    EVENTS_UPCOMING_EMPTY: "Nothing is on the calendar yet. This card updates itself.",
    EVENTS_UPCOMING_MAX: 5,
    POSTS_BLOCK_LINKS_ROWS: "",
    POSTS_BLOCK_LINKS_TITLE: "Links",
    POSTS_BLOCK_LINKS_TEXT: "Handy places, one press away.",
    POSTS_BLOCK_LINKS_CARD: True,
    POSTS_BLOCK_LIVE_MINUTES: 1,
    POSTS_BLOCK_LIVENOW_NAME: POSTS_BLOCK_LIVENOW_NAME_DEFAULT,
    POSTS_BLOCK_UPCOMING_NAME: POSTS_BLOCK_UPCOMING_NAME_DEFAULT,
    POSTS_BLOCK_LINKS_NAME: POSTS_BLOCK_LINKS_NAME_DEFAULT,
}
KEY_TYPES.update(
    {
        GOLIVE_BLOCK_TITLE: "text",
        GOLIVE_BLOCK_LINE: "text",
        GOLIVE_BLOCK_UNTITLED: "text",
        GOLIVE_BLOCK_EMPTY: "text",
        GOLIVE_BLOCK_MAX: "int",
        GOLIVE_BLOCK_TITLE_CHARS: "int",
        EVENTS_UPCOMING_TITLE: "text",
        EVENTS_UPCOMING_LINE: "text",
        EVENTS_UPCOMING_EMPTY: "text",
        EVENTS_UPCOMING_MAX: "int",
        POSTS_BLOCK_LINKS_ROWS: "text",
        POSTS_BLOCK_LINKS_TITLE: "text",
        POSTS_BLOCK_LINKS_TEXT: "text",
        POSTS_BLOCK_LINKS_CARD: "bool",
        POSTS_BLOCK_LIVE_MINUTES: "int",
        POSTS_BLOCK_LIVENOW_NAME: "text",
        POSTS_BLOCK_UPCOMING_NAME: "text",
        POSTS_BLOCK_LINKS_NAME: "text",
    }
)
KEY_HELP.update(
    {
        GOLIVE_BLOCK_TITLE: "the heading on the who's-live-now block, when a post carries it",
        GOLIVE_BLOCK_LINE: (
            "one line per stream on the who's-live-now block; {name} is who is live and {title} "
            "is the stream's title, linked to the stream"
        ),
        GOLIVE_BLOCK_UNTITLED: (
            "the linked words on the who's-live-now block for a stream with no title"
        ),
        GOLIVE_BLOCK_EMPTY: (
            "what the who's-live-now block says while nobody at all is live, in place of the list"
        ),
        GOLIVE_BLOCK_MAX: (
            "how many streams the who's-live-now block lists at most, 1 to 25; 10 by default"
        ),
        GOLIVE_BLOCK_TITLE_CHARS: (
            "how many characters of a stream's title the who's-live-now block shows, 10 to 200; "
            "a longer title is cut with an ellipsis"
        ),
        EVENTS_UPCOMING_TITLE: "the heading on the upcoming-events block, when a post carries it",
        EVENTS_UPCOMING_LINE: (
            "one line per event on the upcoming-events block; {title} is the event (linked to "
            "it in Discord once it has a scheduled event), {when} its start in each reader's "
            "own time and {relative} how long until then"
        ),
        EVENTS_UPCOMING_EMPTY: "what the upcoming-events block says while no event is coming up",
        EVENTS_UPCOMING_MAX: (
            "how many events the upcoming-events block lists at most, 1 to 20; 5 by default"
        ),
        POSTS_BLOCK_LINKS_ROWS: (
            "the link-buttons block's buttons, as a list of label and url pairs: at most 10, "
            "each label at most 80 characters and each url starting https://. The Posts page's "
            "Blocks section edits it row by row; blank means no buttons"
        ),
        POSTS_BLOCK_LINKS_TITLE: "the heading on the card above the link buttons",
        POSTS_BLOCK_LINKS_TEXT: "the line under that heading",
        POSTS_BLOCK_LINKS_CARD: (
            "true puts a card with the heading and line above the link buttons; false leaves "
            "the buttons alone under the post"
        ),
        POSTS_BLOCK_LIVE_MINUTES: (
            "how often, in minutes, the who's-live-now and upcoming-events blocks are checked, "
            "1 to 60; 1 by default. A message is edited only when what it lists has changed"
        ),
        POSTS_BLOCK_LIVENOW_NAME: (
            "what the who's-live-now block is called in the Posts page's Add a block list, its "
            "Blocks section and the /posts card. Members never see it"
        ),
        POSTS_BLOCK_UPCOMING_NAME: (
            "what the upcoming-events block is called in the Posts page's Add a block list, its "
            "Blocks section and the /posts card. Members never see it"
        ),
        POSTS_BLOCK_LINKS_NAME: (
            "what the link-buttons block is called in the Posts page's Add a block list, its "
            "Blocks section and the /posts card. Members never see it"
        ),
    }
)
KEY_MIN.update(
    {
        GOLIVE_BLOCK_MAX: 1,
        GOLIVE_BLOCK_TITLE_CHARS: 10,
        EVENTS_UPCOMING_MAX: 1,
        POSTS_BLOCK_LIVE_MINUTES: 1,
    }
)
KEY_MAX.update(
    {
        GOLIVE_BLOCK_MAX: 25,
        GOLIVE_BLOCK_TITLE_CHARS: 200,
        EVENTS_UPCOMING_MAX: 20,
        POSTS_BLOCK_LIVE_MINUTES: 60,
    }
)
TEXT_CHECKS.update(
    {
        GOLIVE_BLOCK_TITLE: checked_plain,
        GOLIVE_BLOCK_LINE: checked_fields(LIVE_LINE_FIELDS),
        GOLIVE_BLOCK_UNTITLED: checked_plain,
        GOLIVE_BLOCK_EMPTY: checked_plain,
        EVENTS_UPCOMING_TITLE: checked_plain,
        EVENTS_UPCOMING_LINE: checked_fields(UPCOMING_LINE_FIELDS),
        EVENTS_UPCOMING_EMPTY: checked_plain,
        POSTS_BLOCK_LINKS_ROWS: checked_links,
        POSTS_BLOCK_LINKS_TITLE: checked_plain,
        POSTS_BLOCK_LINKS_TEXT: checked_plain,
    }
)
TEXT_MAY_BE_BLANK = (*TEXT_MAY_BE_BLANK, POSTS_BLOCK_LINKS_ROWS)
NAMESPACE_OVERRIDE.update(
    {
        key: "posts"
        for key in (
            GOLIVE_BLOCK_TITLE,
            GOLIVE_BLOCK_LINE,
            GOLIVE_BLOCK_UNTITLED,
            GOLIVE_BLOCK_EMPTY,
            GOLIVE_BLOCK_MAX,
            GOLIVE_BLOCK_TITLE_CHARS,
        )
    }
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
        if key == "structure_backup_role_id":
            return getattr(self.settings, "structure_backup_role_id", None)
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
        if key == GOLIVE_LIVE_AUTHOR_KEY:
            return GOLIVE_LIVE_AUTHOR
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
        if key == SPOTLIGHT_BUMP_PINGS_KEY:
            return False
        if key == SPOTLIGHT_PIN_KEY:
            return True
        if key == SPOTLIGHT_DEFAULT_DAYS_KEY:
            return SPOTLIGHT_DEFAULT_DAYS
        if key == SPOTLIGHT_EVENT_SLACK_KEY:
            return SPOTLIGHT_EVENT_SLACK_HOURS
        if key == SPOTLIGHT_RANGE_KEY:
            return SPOTLIGHT_RANGE
        if key == SPOTLIGHT_RANGE_KEPT_KEY:
            return SPOTLIGHT_RANGE_KEPT
        if key == SPOTLIGHT_SCHEDULED_WORD_KEY:
            return SPOTLIGHT_SCHEDULED_WORD
        if key == SPOTLIGHT_DATES_BUTTON_KEY:
            return SPOTLIGHT_DATES_BUTTON
        if key == SPOTLIGHT_STARTS_LABEL_KEY:
            return SPOTLIGHT_STARTS_LABEL
        if key == SPOTLIGHT_ENDS_LABEL_KEY:
            return SPOTLIGHT_ENDS_LABEL
        if key == SPOTLIGHT_END_BEFORE_START_KEY:
            return SPOTLIGHT_END_BEFORE_START
        if key == SPOTLIGHT_BAD_DATE_KEY:
            return SPOTLIGHT_BAD_DATE
        if key == SPOTLIGHT_PING_MODE_DEFAULT_KEY:
            return PING_ALWAYS
        if key == SPOTLIGHT_WINDOW_OPEN_REMINDER_KEY:
            return True
        if key == GOLIVE_EXPIRY_KEEPS_MARATHON_CHANNELS_KEY:
            return True
        if key == SPOTLIGHT_WINDOW_KEEP_DAYS_KEY:
            return SPOTLIGHT_WINDOW_KEEP_DAYS
        if key == SPOTLIGHT_PINGS_ALWAYS_WORDS_KEY:
            return SPOTLIGHT_PINGS_ALWAYS_WORDS
        if key == SPOTLIGHT_PINGS_NEVER_WORDS_KEY:
            return SPOTLIGHT_PINGS_NEVER_WORDS
        if key == SPOTLIGHT_PINGS_EVENTS_WORDS_KEY:
            return SPOTLIGHT_PINGS_EVENTS_WORDS
        if key == SPOTLIGHT_WINDOW_OPEN_WORDS_KEY:
            return SPOTLIGHT_WINDOW_OPEN_WORDS
        if key == SPOTLIGHT_WINDOW_NEXT_WORDS_KEY:
            return SPOTLIGHT_WINDOW_NEXT_WORDS
        if key == SPOTLIGHT_WINDOW_NONE_WORDS_KEY:
            return SPOTLIGHT_WINDOW_NONE_WORDS
        if key == CHANNEL_SPOTLIGHT_DEFAULT_KEY:
            return False
        if key == CHANNEL_OPTOUT_POST_KEY:
            return CHANNEL_OPTOUT_END
        if key == MEMBER_OPTOUT_POST_KEY:
            return MEMBER_OPTOUT_END
        if key == "golive_cooldown_minutes":
            return 60
        if key == "golive_max_session_hours":
            return 12
        if key == "golive_embed":
            return True
        if key == "golive_boot_sweep":
            return True
        if key == GOLIVE_AUTOLINK_PRESENCE_KEY:
            return GOLIVE_AUTOLINK_PRESENCE_DEFAULT
        if key == GOLIVE_AUTOLINK_VIDEO_KEY:
            return GOLIVE_AUTOLINK_VIDEO_DEFAULT
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
        if key in BIRTHDAY_POST_WORDS:
            return BIRTHDAY_POST_WORDS[key]
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
        if key in CHANNEL_NOTE_WORDS:
            return CHANNEL_NOTE_WORDS[key][0]
        if key in PROMPT_WORDS:
            return PROMPT_WORDS[key][0]
        if key in VOICE_WORDS:
            return VOICE_WORDS[key][0]
        if key in tone_keys.TONE_SETTINGS:
            return tone_keys.TONE_SETTINGS[key][1]
        if key in tone_keys.TONE_WORDS:
            return tone_keys.TONE_WORDS[key][0]
        if key in MARATHON_DEFAULTS:
            return MARATHON_DEFAULTS[key]
        if key in GOLIVE_REPLAY_DEFAULTS:
            return GOLIVE_REPLAY_DEFAULTS[key]
        if key in TEMPVOICE_BLOCK_DEFAULTS:
            return TEMPVOICE_BLOCK_DEFAULTS[key]
        if key in BUTTON_BLOCK_DEFAULTS:
            return BUTTON_BLOCK_DEFAULTS[key]
        if key in BLOCKS_LIVE_DEFAULTS:
            return BLOCKS_LIVE_DEFAULTS[key]
        if key in REVIEW_SETTINGS:
            return REVIEW_SETTINGS[key][1]
        if key in REVIEW_WORDS:
            return REVIEW_WORDS[key][0]
        if key == "chat_mode":
            return "on"
        if key == "chat_cooldown_seconds":
            return CHAT_COOLDOWN_SECONDS
        if key == "chat_greeting_reaction":
            return False
        if key == "chat_greeting_via_model":
            return "on"
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
        if key == MEMORY_MIN_TURNS_KEY:
            return DISTIL_MIN_TURNS
        if key == RAPPORT_MAX_KEY:
            return RAPPORT_MAX
        if key == SWEEP_HOURS_KEY:
            return SWEEP_HOURS
        if key == RAPPORT_LINE_KEY:
            return RAPPORT_LINE
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
        if key == RAIDTRAIN_EVENT_DEFAULT_KEY:
            return False
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
        if key in (FRONTDOOR_SHOW_TICKET, FRONTDOOR_SHOW_REQUEST, FRONTDOOR_SHOW_EVENT):
            return True
        if key == POSTS_BLOCK_FRONTDOOR_NAME:
            return POSTS_BLOCK_FRONTDOOR_NAME_DEFAULT
        if key == "mod_panel_minutes":
            return 10
        if key == SETTINGS_PANEL_MINUTES:
            return 10
        if key == SETTINGS_CORE_KEYS_ADMIN_ONLY:
            return SETTINGS_CORE_KEYS_ADMIN_ONLY_DEFAULT
        if key == QUIET_BOT_PINS:
            return QUIET_BOT_PINS_DEFAULT
        if key in STICKY_DEFAULTS:
            return STICKY_DEFAULTS[key]
        if key == ERROR_SENTENCE_KEY:
            return ERROR_SENTENCE
        if key == ERROR_RETRY_LABEL_KEY:
            return ERROR_RETRY_LABEL
        if key == ERROR_RETRY_MINUTES_KEY:
            return ERROR_RETRY_MINUTES
        if key == ERROR_RETRY_EXPIRED_KEY:
            return ERROR_RETRY_EXPIRED
        if key == PANEL_EXPIRED_TEXT_KEY:
            return PANEL_EXPIRED_TEXT
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
        if key == POSTS_IMPORT_STYLE:
            return POSTS_IMPORT_STYLE_DEFAULT
        if key == POSTS_UNTITLED_TITLE:
            return POSTS_UNTITLED_TITLE_DEFAULT
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
        if key in STRUCTURE_BACKUP_DEFAULTS:
            return STRUCTURE_BACKUP_DEFAULTS[key]
        if key in PB_FEED_DEFAULTS:
            return PB_FEED_DEFAULTS[key]
        if key in BRACKETS_DEFAULTS:
            return BRACKETS_DEFAULTS[key]
        if key in POINTS_DEFAULTS:
            return POINTS_DEFAULTS[key]
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


async def _stored_row(store: SettingsStore, guild_id: int, key: str) -> Any:
    cur = await store.db.conn.execute(
        "SELECT value FROM settings WHERE guild_id = ? AND key = ?", (guild_id, key)
    )
    row = await cur.fetchone()
    if row is None:
        return None
    try:
        return json.loads(row["value"])
    except (TypeError, ValueError):
        return None


async def carry_end_wording(store: SettingsStore, guild_id: int) -> dict[str, Any] | None:
    """Schema 50: the two retired end keys fold into golive_end_template, once, at boot."""
    suffix = await _stored_row(store, guild_id, GOLIVE_END_SUFFIX_RETIRED)
    mode = await _stored_row(store, guild_id, GOLIVE_END_MODE_RETIRED)
    if suffix is None and mode is None:
        return None
    carried = False
    if isinstance(suffix, str) and not store.is_stored(guild_id, "golive_end_template"):
        await store.set(guild_id, "golive_end_template", GOLIVE_LIVE_FIELD + suffix)
        carried = True
    await store.db.conn.execute(
        "DELETE FROM settings WHERE guild_id = ? AND key IN (?, ?)",
        (guild_id, GOLIVE_END_SUFFIX_RETIRED, GOLIVE_END_MODE_RETIRED),
    )
    await store.db.conn.commit()
    return {"carried_suffix": carried, "dropped_mode": mode}
