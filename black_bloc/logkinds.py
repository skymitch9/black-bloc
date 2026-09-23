from __future__ import annotations

from typing import Any

CORE = "core"
WEB = "web"
SHADOW = ".would_"

VIA_DISCORD = "discord"
VIA_WEBSITE = "website"
VIA_OPERATOR = "operator"
VIA_BOOT = "boot"
VIA_FORUM = "forum"
VIA_WORDS: dict[str, str] = {
    VIA_DISCORD: "Discord",
    VIA_WEBSITE: "Website",
    VIA_OPERATOR: "Operator token",
    VIA_BOOT: "By the bot at boot",
    VIA_FORUM: "A forum post",
}

ERROR_HEAD = "error"
ERROR_COMMAND = f"{ERROR_HEAD}.command"
ERROR_PANEL = f"{ERROR_HEAD}.panel"
ERROR_MODAL = f"{ERROR_HEAD}.modal"
ERROR_BUTTON = f"{ERROR_HEAD}.button"
ERROR_KINDS: tuple[str, ...] = (ERROR_COMMAND, ERROR_PANEL, ERROR_MODAL, ERROR_BUTTON)

OFF = "off"
IMPORTANT_ONLY = "important"
ALL = "all"
LEVELS = (OFF, IMPORTANT_ONLY, ALL)
LEVEL_DEFAULT = IMPORTANT_ONLY

FEATURES = (
    CORE,
    "automod",
    "honeypot",
    "mod",
    "modmail",
    "golive",
    "youtube",
    "events",
    "birthday",
    "tempvoice",
    "rolemenu",
    "poll",
    "chat",
    "request",
    "pings",
    "raidtrain",
    "applications",
    "selftest",
    "guides",
    "posts",
    "minutes",
)

HEADS: dict[str, str] = {
    ERROR_HEAD: CORE,
    "settings": CORE,
    "commands": CORE,
    "presence": CORE,
    "automod": "automod",
    "honeypot": "honeypot",
    "mod": "mod",
    "case": "mod",
    "modmail": "modmail",
    "frontdoor": "modmail",
    "handoff": "request",
    "golive": "golive",
    "youtube": "youtube",
    "event": "events",
    "events": "events",
    "birthday": "birthday",
    "tempvoice": "tempvoice",
    "role": "rolemenu",
    "role_menu": "rolemenu",
    "rolemenu": "rolemenu",
    "poll": "poll",
    "chat": "chat",
    "request": "request",
    "requests": "request",
    "pings": "pings",
    "raidtrain": "raidtrain",
    "application": "applications",
    "applications": "applications",
    "selftest": "selftest",
    "guide": "guides",
    "guides": "guides",
    "post": "posts",
    "posts": "posts",
    "minutes": "minutes",
}

FEATURE_LABELS: dict[str, str] = {
    CORE: "Core",
    "automod": "Automod",
    "honeypot": "Honeypot",
    "mod": "Moderation",
    "modmail": "Modmail",
    "golive": "Go-live",
    "youtube": "YouTube",
    "events": "Events",
    "birthday": "Birthdays",
    "tempvoice": "Temp voice",
    "rolemenu": "Role menus",
    "poll": "Polls",
    "chat": "Chat",
    "request": "Requests",
    "pings": "Ping roles",
    "raidtrain": "Raid trains",
    "applications": "Applications",
    "selftest": "Test",
    "guides": "Guides",
    "posts": "Posts",
    "minutes": "Meeting minutes",
}

FEATURE_PAGES: dict[str, str] = {
    CORE: "settings.html",
    "automod": "automod.html",
    "honeypot": "honeypot.html",
    "mod": "moderation.html",
    "modmail": "modmail.html",
    "golive": "golive.html",
    "youtube": "golive.html",
    "events": "events.html",
    "birthday": "birthdays.html",
    "tempvoice": "tempvoice.html",
    "rolemenu": "rolemenus.html",
    "poll": "polls.html",
    "chat": "chat.html",
    "request": "requests.html",
    "pings": "golive.html",
    "raidtrain": "raidtrain.html",
    "applications": "rolemenus.html",
    "selftest": "health.html",
    "guides": "guides.html",
    "posts": "posts.html",
    "minutes": "minutes.html",
}

IMPORTANT_SUFFIXES = (
    "_failed",
    ".approved",
    ".denied",
    ".expired",
    ".warned",
    ".timed_out",
    ".timeout",
    ".kicked",
    ".kick",
    ".banned",
    ".ban",
    ".granted",
    ".ended",
    ".removed",
    ".purged",
    ".blocked",
    ".closed",
)

IMPORTANT: frozenset[str] = frozenset(
    {
        *ERROR_KINDS,
        "automod.deleted",
        "case.restored",
        "case.voided",
        "core.restart_requested",
        "event.cancelled",
        "event.missed",
        "event.announce_skipped_late",
        "event.where_channel_gone",
        "golive.costream_added",
        "golive.role_stuck",
        "handoff.event_to_request",
        "handoff.request_to_event",
        "handoff.request_to_ticket",
        "handoff.ticket_to_event",
        "handoff.ticket_to_request",
        "youtube.probe_unreadable",
        "mod.untimed_out",
        "mod.unbanned",
        "mod.warn_threshold",
        "frontdoor.duplicate_seen",
        "modmail.opened_by_staff",
        "modmail.panel_duplicate_seen",
        "modmail.unblocked",
        "pings.fan_role_created",
        "pings.fan_role_removed",
        "pings.forbidden",
        "pings.onboarding_took_over",
        "pings.role_pruned",
        "pings.streamer_hidden",
        "pings.streamer_pruned",
        "poll.cancelled",
        "poll.draft_discarded",
        "raidtrain.cancel",
        "raidtrain.event_made",
        "raidtrain.remind",
        "request.declined",
        "request.done",
        "request.hold",
        "request.review",
        "request.sent_back",
        "chat.memory_forgot",
        "chat.memory_optout",
        "chat.pool_retired",
        "role.extended",
        "post.posted",
        "post.updated",
        "post.shadow_posted",
        "post.shadow_updated",
        "post.taken_down",
        "post.restored",
    }
)

ROUTINE: frozenset[str] = frozenset(
    {
        "birthday.add_role",
        "handoff.asked",
        "handoff.refused",
        "birthday.announce",
        "birthday.clear",
        "birthday.member_missing",
        "birthday.mode",
        "birthday.optin",
        "birthday.optout",
        "birthday.remove",
        "birthday.remove_role",
        "birthday.set",
        "case.noted",
        "case.reason_edited",
        "chat.insult",
        "chat.intent_created",
        "chat.intent_deleted",
        "chat.intent_edited",
        "chat.knowledge_added",
        "chat.knowledge_edited",
        "chat.knowledge_ingested",
        "chat.knowledge_removed",
        "chat.line_added",
        "chat.line_deleted",
        "chat.line_edited",
        "chat.llm_capped",
        "chat.llm_error",
        "chat.llm_reply",
        "chat.mode",
        "chat.personality_mode",
        "chat.pool_synced",
        "chat.reply_reference_fixed",
        "chat.route",
        "chat.settings",
        "chat.trope_disabled",
        "chat.trope_enabled",
        "commands.visibility",
        "event.announce",
        "event.announce_channel_forgotten",
        "event.announce_room",
        "event.announcement_edited",
        "event.cancelled_room",
        "event.category_forgotten",
        "event.channel_deleted",
        "event.created",
        "event.denied_room",
        "event.done",
        "event.edited",
        "event.ended_room",
        "event.go_live",
        "event.go_live_room",
        "event.forum_forgotten",
        "event.forum_made",
        "event.post_archived",
        "event.post_skipped_test_mode",
        "event.room_forgotten",
        "event.room_moved",
        "event.settings",
        "frontdoor.below_post",
        "frontdoor.gone",
        "frontdoor.moved",
        "frontdoor.posted",
        "frontdoor.posted_shadow",
        "frontdoor.taken_down",
        "frontdoor.taken_down_shadow",
        "frontdoor.updated_shadow",
        "frontdoor.ticket_button_hidden",
        "golive.add_role",
        "golive.announce",
        "golive.autolink_refused",
        "golive.boot_swept",
        "golive.channel_announced",
        "golive.channel_ended",
        "golive.costream_dropped",
        "golive.end",
        "golive.end_wording_migrated",
        "golive.history_swept",
        "golive.link",
        "golive.mode",
        "golive.optin",
        "golive.optout",
        "golive.poll_degraded",
        "golive.post_deleted",
        "golive.remove_role",
        "golive.spotlight_added",
        "golive.spotlight_announced",
        "golive.spotlight_announcement_refreshed",
        "golive.spotlight_bumped",
        "golive.spotlight_ended",
        "golive.spotlight_expired",
        "golive.spotlight_pinned",
        "golive.spotlight_post_deleted",
        "golive.spotlight_reconciled",
        "golive.spotlight_removed",
        "golive.spotlight_started",
        "golive.spotlight_unpinned",
        "golive.spotlight_updated",
        "golive.test",
        "golive.unlink",
        "golive.unpinned",
        "youtube.link",
        "youtube.live_id_searched",
        "youtube.live_mode",
        "youtube.live_seen",
        "youtube.probe_walled",
        "youtube.unlink",
        "honeypot.exempt",
        "honeypot.exempt_set",
        "honeypot.hit_recorded",
        "honeypot.mode",
        "honeypot.settings",
        "honeypot.setup",
        "honeypot.trap_removed",
        "automod.exempt_add",
        "automod.exempt_remove",
        "automod.mode",
        "automod.observed",
        "automod.rule",
        "automod.settings",
        "modmail.blocked_dm",
        "modmail.category_forgotten",
        "modmail.forgotten",
        "modmail.forum_forgotten",
        "modmail.forum_made",
        "modmail.log_channel_forgotten",
        "modmail.member_left",
        "modmail.note",
        "modmail.open_refused",
        "modmail.opened",
        "modmail.panel_below_post",
        "modmail.panel_gone",
        "modmail.panel_moved",
        "modmail.panel_posted",
        "modmail.panel_posted_shadow",
        "modmail.panel_taken_down",
        "modmail.panel_taken_down_shadow",
        "modmail.panel_updated_shadow",
        "modmail.place_kept",
        "modmail.reply",
        "modmail.settings",
        "modmail.snippet_removed",
        "modmail.snippet_saved",
        "modmail.staff_channel_forgotten",
        "modmail.transcript",
        "pings.events_off",
        "pings.events_on",
        "pings.fan_role_missing",
        "pings.fan_role_renamed",
        "pings.follow",
        "pings.onboarding_synced",
        "pings.raidtrain_setup",
        "pings.settings",
        "pings.setup",
        "pings.streamer_restored",
        "pings.streamer_seen",
        "pings.unfollow",
        "poll.archived",
        "poll.channel_forgotten",
        "poll.closed",
        "poll.created",
        "poll.draft_expired",
        "poll.draft_saved",
        "poll.opened",
        "poll.opened_shadow",
        "poll.pinned",
        "poll.recur_created",
        "poll.recur_deleted",
        "poll.recur_paused",
        "poll.recur_resumed",
        "poll.recurred",
        "poll.reminded",
        "poll.settings",
        "poll.unpinned",
        "raidtrain.assign",
        "raidtrain.checkin",
        "raidtrain.claim",
        "raidtrain.create",
        "raidtrain.done",
        "raidtrain.event_cancelled",
        "raidtrain.live",
        "raidtrain.lock",
        "raidtrain.mode",
        "raidtrain.moved_pinged",
        "raidtrain.poll_degraded",
        "raidtrain.post",
        "raidtrain.post_skipped_test_mode",
        "raidtrain.release",
        "raidtrain.setup",
        "raidtrain.swap",
        "raidtrain.unassign",
        "raidtrain.unlock",
        "operator.read",
        "presence.bio_set",
        "request.check_asked",
        "request.comment",
        "request.filed",
        "request.forum_forgotten",
        "request.forum_made",
        "request.in_progress",
        "request.notify_skipped_test_mode",
        "request.resumed",
        "request.updated",
        "request.withdrawn",
        "chat.memory_distilled",
        "chat.memory_expired",
        "chat.memory_optin",
        "role.changed_by_hand",
        "role.reconciled",
        "role.requested",
        "role.withdrawn",
        "role_menu.assign",
        "role_menu.create",
        "role_menu.delete",
        "role_menu.edit",
        "role_menu.mode",
        "role_menu.option_added",
        "role_menu.option_removed",
        "role_menu.post",
        "role_menu.reposted",
        "role_menu.seeded",
        "role_menu.unassign",
        "role_menu.unposted",
        "role_menu.update",
        "settings.clear",
        "settings.set",
        "tempvoice.adopt",
        "tempvoice.ban",
        "tempvoice.bitrate",
        "tempvoice.claim",
        "tempvoice.create",
        "tempvoice.creator_removed",
        "tempvoice.delete",
        "tempvoice.hide",
        "tempvoice.kick",
        "tempvoice.limit",
        "tempvoice.lobby_hidden",
        "tempvoice.lobby_shown",
        "tempvoice.lock",
        "tempvoice.mode",
        "tempvoice.panel_elsewhere",
        "tempvoice.permit",
        "tempvoice.prefs_reset",
        "tempvoice.region",
        "tempvoice.rename",
        "tempvoice.repair",
        "tempvoice.setup",
        "tempvoice.show",
        "tempvoice.transfer",
        "tempvoice.turned_away",
        "tempvoice.unban",
        "tempvoice.unlock",
        "tempvoice.unpermit",
        "application.mode",
        "application.form_created",
        "application.form_updated",
        "application.form_deleted",
        "application.question_changed",
        "application.panel_posted",
        "application.post_skipped_test_mode",
        "application.submitted",
        "application.withdrawn",
        "application.removed",
        "selftest.started",
        "selftest.check",
        "selftest.finished",
        "selftest.purged",
        "guide.confirmed",
        "guide.created",
        "guide.deleted",
        "guide.edited",
        "guide.media_replaced",
        "guide.published",
        "guide.reset",
        "guide.seed_refreshed",
        "guide.seeded",
        "guide.shots_stale",
        "guide.unpublished",
        "post.created",
        "post.deleted",
        "post.message_gone",
        "post.mode",
        "post.pinned",
        "post.saved",
        "post.versions_trimmed",
        "post.shadow_message_gone",
        "post.shadow_taken_down",
        "post.seeded",
        "post.seed_channel_unknown",
        "minutes.started",
        "minutes.ended",
        "minutes.notes_written",
        "minutes.posted",
        "minutes.notes_edited",
        "minutes.deleted",
        "minutes.purged",
        "minutes.mode",
    }
)

CHAT_POOL_SYNCED = "chat.pool_synced"
CHAT_POOL_RETIRED = "chat.pool_retired"

SELFTEST = "selftest"
SELFTEST_STARTED = "selftest.started"
SELFTEST_CHECK = "selftest.check"
SELFTEST_FINISHED = "selftest.finished"
SELFTEST_PURGED = "selftest.purged"
SELFTEST_KINDS: tuple[str, ...] = (
    SELFTEST_STARTED,
    SELFTEST_CHECK,
    SELFTEST_FINISHED,
    SELFTEST_PURGED,
)


def bare(kind: str) -> str:
    """`web.role.granted` and `role.granted` are the same event, logged from two places."""
    text = str(kind or "")
    head, dot, rest = text.partition(".")
    return rest if head == WEB and rest else text


def kind_via(kind: str, via: str) -> str:
    """The one place the `web.` head is put on: `bare()` read backwards."""
    return f"{WEB}.{kind}" if via == VIA_WEBSITE else str(kind)


def feature_of(kind: str) -> str:
    head, _, _ = bare(kind).partition(".")
    return HEADS.get(head, CORE)


def heads_for(feature: str) -> tuple[str, ...]:
    return tuple(head for head, found in HEADS.items() if found == feature)


def like_patterns(feature: str) -> tuple[str, ...]:
    """The SQL `LIKE` forms of one feature's kinds, derived from `HEADS` so there is one home."""
    found: list[str] = []
    for head in heads_for(feature):
        found.append(f"{head}.%")
        found.append(f"{WEB}.{head}.%")
    return tuple(found)


FEATURES_WITHOUT_A_COMMAND: tuple[str, ...] = ("guides",)

HIDDEN_BY_DEFAULT: tuple[str, ...] = (SELFTEST,)


def hidden_by_default_patterns() -> tuple[str, ...]:
    """The features the Logs page leaves out until somebody asks for them by name."""
    return tuple(
        pattern for feature in HIDDEN_BY_DEFAULT for pattern in like_patterns(feature)
    )


def is_shadow(kind: str) -> bool:
    return SHADOW in bare(kind)


def is_important(kind: str) -> bool:
    text = bare(kind)
    if SHADOW in text or text in ROUTINE:
        return False
    if text in IMPORTANT:
        return True
    return any(text.endswith(suffix) for suffix in IMPORTANT_SUFFIXES)


def should_post(kind: str, level: str | None, *, carded: bool = False) -> bool:
    """An unknown level is `all` — today's behaviour — so nothing goes quiet by accident."""
    if level == OFF:
        return False
    if level == IMPORTANT_ONLY:
        return is_important(kind) and not carded
    return True


def via_of(kind: str, details: Any = None) -> str:
    """Where a change was made. What the writer recorded wins; the `web.` head decides the rest."""
    if isinstance(details, dict):
        found = str(details.get("via") or "").strip().lower()
        if found in VIA_WORDS:
            return found
    head, dot, rest = str(kind or "").partition(".")
    return VIA_WEBSITE if head == WEB and rest else VIA_DISCORD


def via_word(kind: str, details: Any = None) -> str:
    return VIA_WORDS[via_of(kind, details)]


def log_level_key(feature: str) -> str:
    return f"{feature}_log_level"


LOG_LEVEL_KEYS: tuple[str, ...] = tuple(log_level_key(feature) for feature in FEATURES)


__all__ = [
    "ALL",
    "CHAT_POOL_RETIRED",
    "CHAT_POOL_SYNCED",
    "CORE",
    "ERROR_BUTTON",
    "ERROR_COMMAND",
    "ERROR_HEAD",
    "ERROR_KINDS",
    "ERROR_MODAL",
    "ERROR_PANEL",
    "FEATURES",
    "FEATURES_WITHOUT_A_COMMAND",
    "FEATURE_LABELS",
    "FEATURE_PAGES",
    "HEADS",
    "HIDDEN_BY_DEFAULT",
    "IMPORTANT",
    "IMPORTANT_ONLY",
    "IMPORTANT_SUFFIXES",
    "LEVELS",
    "SHADOW",
    "LEVEL_DEFAULT",
    "LOG_LEVEL_KEYS",
    "OFF",
    "ROUTINE",
    "SELFTEST",
    "SELFTEST_CHECK",
    "SELFTEST_FINISHED",
    "SELFTEST_KINDS",
    "SELFTEST_PURGED",
    "SELFTEST_STARTED",
    "VIA_BOOT",
    "VIA_DISCORD",
    "VIA_FORUM",
    "VIA_OPERATOR",
    "VIA_WEBSITE",
    "VIA_WORDS",
    "bare",
    "feature_of",
    "heads_for",
    "hidden_by_default_patterns",
    "is_important",
    "is_shadow",
    "kind_via",
    "like_patterns",
    "log_level_key",
    "should_post",
    "via_of",
    "via_word",
]
