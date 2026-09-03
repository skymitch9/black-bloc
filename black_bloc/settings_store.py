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
from .logkinds import FEATURE_LABELS, FEATURES, LEVEL_DEFAULT, LEVELS, log_level_key
from .personas import COOKOUT, PERSONALITY_CHOICES
from .polls import DATE_LABEL_FORMS as POLL_DATE_LABEL_FORMS
from .polls import MAX_HOURS as POLL_MAX_HOURS
from .polls import MIN_HOURS as POLL_MIN_HOURS
from .storage.db import Database

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

YOUTUBE_MODES = ("off", "shadow", "on")
YOUTUBE_TEMPLATE = "**{name}** just dropped a new video: **{title}** {url}"
YOUTUBE_POLL_MINUTES = 10
YOUTUBE_POLL_MIN_MINUTES = 5

ROLEMENU_MODES = ("off", "on")

PINGS_MODES = ("off", "on")
PINGS_EVENTS_ROLE_NAME = "Events"
PINGS_FAN_ROLE_TEMPLATE = "{name} pings"
PINGS_CREATORS = ("self", "staff", "auto")
PINGS_ON_UNLINK = ("keep", "delete")

MEMBER_ROLE_ID = 1073741054563602532
TEMPVOICE_NAME_TEMPLATE = "{user}'s bloc"
TEMPVOICE_CREATOR_NAME = "join to create a channel"
TEMPVOICE_MODES = ("off", "on")
HONEYPOT_MODES = ("off", "shadow", "on")
HONEYPOT_PURGE_MAX_DAYS = 7

EVENTS_MODES = ("off", "shadow", "on")
EVENTS_RETENTION_DAYS = 7
EVENTS_RETENTION_MIN_DAYS = 1
EVENTS_RETENTION_MAX_DAYS = 365
EVENTS_MAX_LATE_MINUTES = 15
EVENTS_LATE_CEILING_MINUTES = 24 * 60

POLL_MODES = ("off", "on")
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
MODMAIL_MODES = (CHANNEL_MODE, THREAD_MODE)
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
    "golive_live_role_id": "role",
    "golive_require_role_id": "role",
    "golive_ignore_role_id": "role",
    "golive_cooldown_minutes": "int",
    "golive_ping_role_id": "role",
    "golive_max_session_hours": "int",
    "golive_embed": "bool",
    "youtube_mode": "enum",
    "youtube_channel_id": "channel",
    "youtube_ping_role_id": "role",
    "youtube_ping_fan_roles": "bool",
    "youtube_announce_shorts": "bool",
    "youtube_template": "text",
    "youtube_poll_minutes": "int",
    "pings_mode": "enum",
    "pings_events_role_name": "text",
    "pings_fan_role_creation": "enum",
    "pings_fan_role_template": "text",
    "pings_fan_role_on_unlink": "enum",
    "pings_fan_role_delete": "bool",
    "tempvoice_mode": "enum",
    "tempvoice_creator_ids": "channels",
    "tempvoice_name_template": "text",
    "tempvoice_creator_name": "text",
    "tempvoice_allowed_role_id": "role",
    "honeypot_mode": "enum",
    "honeypot_channel_ids": "channels",
    "honeypot_purge_days": "int",
    "honeypot_exempt_role_ids": "roles",
    "events_mode": "enum",
    "events_category_id": "channel",
    "events_announce_channel_id": "channel",
    "events_ping_role_id": "role",
    "events_create_scheduled": "bool",
    "events_channel_retention_days": "int",
    "events_max_late_minutes": "int",
    "poll_mode": "enum",
    "poll_who_can_create": "enum",
    "poll_review_mode": "enum",
    "poll_default_hours": "int",
    "poll_channel_id": "channel",
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
}

KEY_CHOICES: dict[str, tuple[str, ...]] = {
    "golive_mode": GOLIVE_MODES,
    "golive_end_mode": GOLIVE_END_MODES,
    "youtube_mode": YOUTUBE_MODES,
    "pings_mode": PINGS_MODES,
    "pings_fan_role_creation": PINGS_CREATORS,
    "pings_fan_role_on_unlink": PINGS_ON_UNLINK,
    "tempvoice_mode": TEMPVOICE_MODES,
    "honeypot_mode": HONEYPOT_MODES,
    "events_mode": EVENTS_MODES,
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
    "events_max_late_minutes": EVENTS_LATE_CEILING_MINUTES,
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
}

KEY_MIN: dict[str, int] = {
    "events_channel_retention_days": EVENTS_RETENTION_MIN_DAYS,
    "chat_cooldown_seconds": CHAT_COOLDOWN_MIN_SECONDS,
    "poll_default_hours": POLL_MIN_HOURS,
    "poll_archive_days": POLL_ARCHIVE_MIN_DAYS,
    "youtube_poll_minutes": YOUTUBE_POLL_MIN_MINUTES,
    "raidtrain_slot_minutes": RAIDTRAIN_SLOT_MIN_MINUTES,
    "raidtrain_reminder_minutes": RAIDTRAIN_REMINDER_MIN_MINUTES,
    "raidtrain_poll_minutes": RAIDTRAIN_POLL_MIN_MINUTES,
}

KEY_MIN_REASON: dict[str, str] = {
    "events_channel_retention_days": (
        "Deleting a finished event's channel the moment it ends throws away the record before "
        "anybody has read it, so the shortest Black Bloc will keep one is {limit} day."
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
    "youtube_poll_minutes": (
        "YouTube's feed is cached for fifteen minutes at a time, so asking more often than every "
        "{limit} minutes fetches the same answer again and finds nothing new any sooner."
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
    "events_max_late_minutes": (
        "Announcing an event more than {limit} minutes after it started tells people to come to "
        "something that is already half over."
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
}

KEY_HELP: dict[str, str] = {
    "log_channel_id": "where Black Bloc posts what it did",
    "staff_channel_id": "the channel whose viewers count as staff",
    "role_menu_channel_id": "where /rolemenu post goes by default",
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
    "golive_live_role_id": "role given while someone is streaming",
    "golive_require_role_id": "only announce people who have this role",
    "golive_ignore_role_id": "never announce people who have this role",
    "golive_cooldown_minutes": "minutes before the same person is announced again",
    "golive_ping_role_id": "role mentioned in front of every go-live announcement",
    "golive_max_session_hours": "hours before a stream still marked live is closed anyway",
    "golive_embed": (
        "post the announcement as an embed with the game's art; off = the sentence only"
    ),
    "youtube_mode": "off, shadow (log only) or on (post an announcement for a new upload)",
    "youtube_channel_id": (
        "where a new-upload announcement is posted; leave it unset and the go-live channel is "
        "used instead"
    ),
    "youtube_ping_role_id": "role mentioned in front of every upload announcement",
    "youtube_ping_fan_roles": (
        "also mention the uploader's own fan role, the one their followers wear; off pings only "
        "youtube_ping_role_id"
    ),
    "youtube_announce_shorts": (
        "announce Shorts as well as full videos; off is the default because a channel can post "
        "several a day"
    ),
    "youtube_template": "what an upload announcement says; {name} {title} {url} {channel} {kind}",
    "youtube_poll_minutes": "minutes between checks of every linked channel's uploads feed",
    "pings_mode": (
        "off, or on (members can opt in to go-live and event pings, and a streamer can have a "
        "role of their own that only their followers wear)"
    ),
    "pings_events_role_name": (
        "what `/pingroles setup` calls the one opt-in role for go-live and event pings when it "
        "has to make it; an existing role of that name is reused rather than duplicated"
    ),
    "pings_fan_role_creation": (
        "who may start a streamer's own ping role: self (the streamer, with `/pings fans on`), "
        "staff (only an Auntie/Uncle, with `/pingroles streamer add`), or auto (one is made the "
        "moment a Twitch channel is linked). Staff can always do it for anybody, whichever this "
        "says"
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
    "tempvoice_mode": "off, or on (join-to-create makes a temporary voice channel)",
    "tempvoice_creator_ids": "the join-to-create channels; /tempvoice setup fills this in",
    "tempvoice_name_template": "what a spawned channel is called; {user} is the member",
    "tempvoice_creator_name": "what the join-to-create channel itself is called",
    "tempvoice_allowed_role_id": "only members with this role get a temporary channel",
    "honeypot_mode": "off, shadow (log only) or on (ban whoever posts in the trap)",
    "honeypot_channel_ids": "the trap channels; /honeypot setup fills this in",
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
    "events_channel_retention_days": (
        f"days a finished event's channel is kept before deletion, "
        f"{EVENTS_RETENTION_MIN_DAYS} to {EVENTS_RETENTION_MAX_DAYS}"
    ),
    "events_max_late_minutes": (
        "minutes an event may start late and still be announced; later than that it goes live "
        "quietly"
    ),
    "poll_mode": "off, or on (members and staff can start polls from the /poll panel)",
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
    "modmail_mode": "channel (one channel per ticket) or thread (private threads in one channel)",
    "modmail_category_id": "the category ticket channels are made in, in channel mode",
    "modmail_staff_channel_id": "the channel ticket threads are made in, in thread mode",
    "modmail_log_channel_id": "where a closed ticket's transcript is posted",
    "automod_mode": "off, shadow (log what it would do) or on (delete, warn and time out)",
    "automod_rules": "the automod rule book; /automod rule is what changes it",
    "automod_exempt_role_ids": "roles automod ignores; staff are always ignored too",
    "automod_exempt_channel_ids": "channels automod never reads",
    "automod_warn_threshold": "warnings before Black Bloc says so in the log, 0 to stop counting",
    "modlog_channel_id": "where mod cases are posted; defaults to log_channel_id",
    "mod_dm_on_action": "what a punished member is told: none, server_action, server_action_reason",
    "bot_bio": "the About Me on Black Bloc's own profile, dashboard link and all",
    "status_prefix": "what goes in front of the member count in Black Bloc's status",
    "rolemenu_mode": (
        "whether members can pick roles from the panels; off takes them down and hides the "
        "/rolemenu commands, on posts them again"
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
        "than pointing anywhere. Either way the invention is logged, so `/chat logs` and the "
        "Logs page count how often it happens"
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
        "on keeps `/chat status` (what the conversation models are spending) to server "
        "administrators; off lets any staff member read it. The dashboard's Spend section "
        "stays staff-visible either way"
    ),
    "chat_memory_mode": (
        "off, or on (Black Bloc keeps a few preferences about each person — what to call them, "
        "how they like to be answered — and reads them back next time). Off writes nothing and "
        "reads nothing; the profiles already stored stay until somebody clears them"
    ),
    "chat_memory_consent": (
        "optout means memory is on for everybody until they run `/chat memory off`; optin means "
        "nobody is remembered until they run `/chat memory on`"
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
        "staff read the notes themselves. The person can always read their own with "
        "`/chat memory show`"
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
        "on makes `/twitch link` a condition of claiming a slot, so the lineup carries the name "
        "the streamer before raids; off lets anybody claim and leaves the name off"
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
}

LOG_LEVEL_HELP = (
    "which {label} log lines reach the Discord log channel: off, important (anything that acted "
    "on a member, or failed) or all. Every line is kept on the dashboard{extra} either way"
)
LOG_LEVEL_COMMANDS: dict[str, str] = {
    "automod": "automod",
    "honeypot": "honeypot",
    "mod": "mod",
    "modmail": "modmail",
    "golive": "golive",
    "events": "event",
    "birthday": "birthday",
    "tempvoice": "voice",
    "rolemenu": "rolemenu",
    "poll": "poll",
    "chat": "chat",
    "request": "request",
    "pings": "pingroles",
    "applications": "applications",
}


def log_level_help(feature: str) -> str:
    command = LOG_LEVEL_COMMANDS.get(feature)
    return LOG_LEVEL_HELP.format(
        label=FEATURE_LABELS[feature].lower(),
        extra=f" and in `/{command} logs`" if command else "",
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
            "minutes the /applications show panel stays live before its buttons disable "
            "themselves; 10 by default. The 'this panel went quiet' footer can only be written "
            "while Discord's 15-minute interaction window is still open, so 15 or more means "
            "the buttons simply stop working with no footer to explain it"
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
        if not isinstance(value, str) or not value.strip():
            raise SettingError(f"{key!r} takes some text, not {value!r}.")
        return value
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

    def default(self, key: str) -> Any:
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
        if key == "golive_cooldown_minutes":
            return 60
        if key == "golive_max_session_hours":
            return 12
        if key == "golive_embed":
            return True
        if key == "youtube_mode":
            return "off"
        if key == "youtube_template":
            return YOUTUBE_TEMPLATE
        if key == "youtube_ping_fan_roles":
            return True
        if key == "youtube_announce_shorts":
            return False
        if key == "youtube_poll_minutes":
            return YOUTUBE_POLL_MINUTES
        if key == "pings_mode":
            return "off"
        if key == "pings_events_role_name":
            return PINGS_EVENTS_ROLE_NAME
        if key == "pings_fan_role_creation":
            return PINGS_CREATORS[0]
        if key == "pings_fan_role_template":
            return PINGS_FAN_ROLE_TEMPLATE
        if key == "pings_fan_role_on_unlink":
            return PINGS_ON_UNLINK[0]
        if key == "pings_fan_role_delete":
            return True
        if key == "tempvoice_mode":
            return "on"
        if key == "tempvoice_name_template":
            return TEMPVOICE_NAME_TEMPLATE
        if key == "tempvoice_creator_name":
            return TEMPVOICE_CREATOR_NAME
        if key == "tempvoice_allowed_role_id":
            return MEMBER_ROLE_ID
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
        if key == "events_channel_retention_days":
            return EVENTS_RETENTION_DAYS
        if key == "events_max_late_minutes":
            return EVENTS_MAX_LATE_MINUTES
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
