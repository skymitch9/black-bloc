from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

import aiosqlite

log = logging.getLogger(__name__)

SCHEMA_VERSION = 65

APPLICATION_FORMS_COLUMNS = """    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id          INTEGER NOT NULL,
    name              TEXT    NOT NULL,
    title             TEXT    NOT NULL,
    description       TEXT,
    role_id           INTEGER,
    review_channel_id INTEGER,
    approver_role_id  INTEGER,
    owner_user_id     INTEGER,
    next_step         TEXT,
    approved_text     TEXT,
    expires_days      INTEGER,
    retry_days        INTEGER,
    open              INTEGER NOT NULL DEFAULT 1,
    panel_channel_id  INTEGER,
    panel_message_id  INTEGER,
    created_by        INTEGER NOT NULL,
    created_at        TEXT    NOT NULL,
    updated_at        TEXT    NOT NULL,
    UNIQUE (guild_id, name)"""

APPLICATION_FORMS_LOOSENED = "application_forms_loosened"

SCHEMA = f"""
CREATE TABLE IF NOT EXISTS schema_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    guild_id   INTEGER NOT NULL,
    key        TEXT    NOT NULL,
    value      TEXT    NOT NULL,
    updated_by INTEGER,
    updated_at TEXT    NOT NULL,
    PRIMARY KEY (guild_id, key)
);

CREATE TABLE IF NOT EXISTS action_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id   INTEGER NOT NULL,
    at         TEXT    NOT NULL,
    kind       TEXT    NOT NULL,
    actor_id   INTEGER,
    target_id  INTEGER,
    reason     TEXT,
    details    TEXT
);

CREATE TABLE IF NOT EXISTS role_menus (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id    INTEGER NOT NULL,
    name        TEXT    NOT NULL,
    title       TEXT    NOT NULL,
    description TEXT,
    mode        TEXT    NOT NULL DEFAULT 'multiple',
    message_id  INTEGER,
    channel_id  INTEGER,
    approval     INTEGER NOT NULL DEFAULT 0,
    expires_days INTEGER,
    retry_days   INTEGER NOT NULL DEFAULT 7,
    UNIQUE (guild_id, name)
);

CREATE TABLE IF NOT EXISTS role_requests (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id     INTEGER NOT NULL,
    menu_id      INTEGER NOT NULL,
    user_id      INTEGER NOT NULL,
    role_id      INTEGER NOT NULL,
    requested_at TEXT    NOT NULL,
    status       TEXT    NOT NULL DEFAULT 'pending',
    decided_by   INTEGER,
    decided_at   TEXT,
    deny_reason  TEXT,
    message_id   INTEGER,
    channel_id   INTEGER
);

CREATE UNIQUE INDEX IF NOT EXISTS role_requests_one_open
    ON role_requests(menu_id, user_id, role_id) WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS role_requests_by_status
    ON role_requests(guild_id, status, id);

CREATE TABLE IF NOT EXISTS role_grants (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id       INTEGER NOT NULL,
    user_id        INTEGER NOT NULL,
    role_id        INTEGER NOT NULL,
    source         TEXT    NOT NULL,
    granted_by     INTEGER,
    granted_at     TEXT    NOT NULL,
    expires_at     TEXT,
    removed_at     TEXT,
    removed_reason TEXT
);

CREATE INDEX IF NOT EXISTS role_grants_due ON role_grants(expires_at, removed_at);
CREATE INDEX IF NOT EXISTS role_grants_by_member ON role_grants(guild_id, user_id, role_id);

CREATE TABLE IF NOT EXISTS role_menu_options (
    menu_id  INTEGER NOT NULL REFERENCES role_menus(id) ON DELETE CASCADE,
    role_id  INTEGER NOT NULL,
    label    TEXT    NOT NULL,
    emoji    TEXT,
    position INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (menu_id, role_id)
);

CREATE TABLE IF NOT EXISTS golive_links (
    user_id        INTEGER PRIMARY KEY,
    twitch_login   TEXT    NOT NULL,
    twitch_user_id TEXT,
    linked_at      TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS golive_optout (
    user_id INTEGER PRIMARY KEY,
    at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS golive_sessions (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id              INTEGER NOT NULL,
    user_id               INTEGER NOT NULL,
    source                TEXT    NOT NULL,
    url                   TEXT,
    game                  TEXT,
    title                 TEXT,
    platform              TEXT,
    started_at            TEXT    NOT NULL,
    ended_at              TEXT,
    announced_message_id  INTEGER,
    mode                  TEXT    NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS golive_open_session
    ON golive_sessions(guild_id, user_id) WHERE ended_at IS NULL;

CREATE TABLE IF NOT EXISTS golive_fan_roles (
    guild_id     INTEGER NOT NULL,
    user_id      INTEGER,
    role_id      INTEGER NOT NULL,
    created_at   TEXT    NOT NULL,
    created_by   INTEGER,
    unworn_since TEXT,
    spotlight_id INTEGER
);

CREATE UNIQUE INDEX IF NOT EXISTS golive_fan_roles_one_member
    ON golive_fan_roles(guild_id, user_id) WHERE user_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS golive_fan_roles_one_spotlight
    ON golive_fan_roles(guild_id, spotlight_id) WHERE spotlight_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS streamers (
    guild_id      INTEGER NOT NULL,
    user_id       INTEGER NOT NULL,
    first_live_at TEXT    NOT NULL,
    last_live_at  TEXT    NOT NULL,
    live_count    INTEGER NOT NULL DEFAULT 1,
    platform      TEXT,
    login         TEXT,
    listed        INTEGER NOT NULL DEFAULT 1,
    hidden_by     INTEGER,
    hidden_at     TEXT,
    PRIMARY KEY (guild_id, user_id)
);

CREATE INDEX IF NOT EXISTS streamers_by_last_live
    ON streamers(guild_id, listed, last_live_at);

CREATE TABLE IF NOT EXISTS youtube_links (
    user_id     INTEGER PRIMARY KEY,
    channel_id  TEXT    NOT NULL,
    handle      TEXT,
    title       TEXT,
    linked_at   TEXT    NOT NULL,
    etag        TEXT,
    seeded      INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS youtube_videos (
    video_id             TEXT PRIMARY KEY,
    user_id              INTEGER NOT NULL,
    channel_id           TEXT    NOT NULL,
    title                TEXT,
    published_at         TEXT    NOT NULL,
    seen_at              TEXT    NOT NULL,
    kind                 TEXT    NOT NULL DEFAULT 'video',
    announced_at         TEXT,
    announced_message_id INTEGER,
    mode                 TEXT
);

CREATE INDEX IF NOT EXISTS youtube_videos_user ON youtube_videos(user_id, published_at);

CREATE TABLE IF NOT EXISTS tempvoice_channels (
    channel_id       INTEGER PRIMARY KEY,
    guild_id         INTEGER NOT NULL,
    owner_id         INTEGER NOT NULL,
    creator_id       INTEGER NOT NULL,
    created_at       TEXT    NOT NULL,
    panel_message_id INTEGER,
    panel_channel_id INTEGER
);

CREATE TABLE IF NOT EXISTS tempvoice_prefs (
    user_id       INTEGER PRIMARY KEY,
    name          TEXT,
    user_limit    INTEGER,
    locked        INTEGER DEFAULT 0,
    hidden        INTEGER DEFAULT 0,
    bitrate       INTEGER,
    region        TEXT,
    permitted_ids TEXT,
    banned_ids    TEXT
);

CREATE TABLE IF NOT EXISTS honeypot_hits (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id   INTEGER NOT NULL,
    user_id    INTEGER NOT NULL,
    channel_id INTEGER NOT NULL,
    message_id INTEGER,
    content    TEXT,
    at         TEXT    NOT NULL,
    mode       TEXT    NOT NULL,
    action     TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS user_timezones (
    user_id INTEGER PRIMARY KEY,
    tz      TEXT NOT NULL,
    set_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id           INTEGER NOT NULL,
    requester_id       INTEGER NOT NULL,
    title              TEXT    NOT NULL,
    description        TEXT,
    location           TEXT,
    where_kind         TEXT,
    where_channel_id   INTEGER,
    starts_at          TEXT    NOT NULL,
    ends_at            TEXT,
    status             TEXT    NOT NULL DEFAULT 'pending',
    review_channel_id  INTEGER,
    review_message_id  INTEGER,
    scheduled_event_id INTEGER,
    announce_message_id INTEGER,
    decided_by         INTEGER,
    decided_at         TEXT,
    deny_reason        TEXT,
    created_at         TEXT    NOT NULL,
    moved_to           TEXT,
    review_kind        TEXT
);

CREATE INDEX IF NOT EXISTS events_by_status ON events(guild_id, status, starts_at);

CREATE TABLE IF NOT EXISTS birthdays (
    user_id           INTEGER PRIMARY KEY,
    guild_id          INTEGER NOT NULL,
    month             INTEGER NOT NULL,
    day               INTEGER NOT NULL,
    year              INTEGER,
    opted_in          INTEGER NOT NULL DEFAULT 1,
    source            TEXT    NOT NULL,
    set_at            TEXT    NOT NULL,
    last_announced_on TEXT,
    role_added        INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS modmail_tickets (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id       INTEGER NOT NULL,
    user_id        INTEGER NOT NULL,
    mode           TEXT    NOT NULL,
    channel_id     INTEGER NOT NULL,
    thread_id      INTEGER,
    status         TEXT    NOT NULL DEFAULT 'open',
    opened_at      TEXT    NOT NULL,
    closed_at      TEXT,
    closed_by      INTEGER,
    close_reason   TEXT,
    log_message_id INTEGER,
    card_message_id INTEGER,
    practice       INTEGER NOT NULL DEFAULT 0,
    source         TEXT    NOT NULL DEFAULT 'dm',
    opened_by      INTEGER,
    moved_to       TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS modmail_open_ticket
    ON modmail_tickets(guild_id, user_id) WHERE status = 'open';

CREATE TABLE IF NOT EXISTS modmail_messages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id   INTEGER NOT NULL REFERENCES modmail_tickets(id),
    at          TEXT    NOT NULL,
    author_id   INTEGER NOT NULL,
    direction   TEXT    NOT NULL,
    anonymous   INTEGER NOT NULL DEFAULT 0,
    content     TEXT,
    attachments TEXT
);

CREATE INDEX IF NOT EXISTS modmail_messages_by_ticket ON modmail_messages(ticket_id, id);

CREATE TABLE IF NOT EXISTS modmail_blocks (
    user_id INTEGER PRIMARY KEY,
    by      INTEGER,
    reason  TEXT,
    at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS modmail_snippets (
    name    TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    by      INTEGER,
    at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS mod_cases (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id       INTEGER NOT NULL,
    user_id        INTEGER,
    kind           TEXT    NOT NULL,
    moderator_id   INTEGER,
    reason         TEXT,
    duration_s     INTEGER,
    at             TEXT    NOT NULL,
    mode           TEXT    NOT NULL,
    applied        INTEGER NOT NULL,
    log_message_id INTEGER,
    note           TEXT,
    note_by        INTEGER,
    note_at        TEXT,
    voided_at      TEXT,
    voided_by      INTEGER,
    void_reason    TEXT
);

CREATE INDEX IF NOT EXISTS mod_cases_by_user ON mod_cases(guild_id, user_id, id);
CREATE INDEX IF NOT EXISTS mod_cases_by_kind ON mod_cases(guild_id, kind, at);

CREATE TABLE IF NOT EXISTS polls (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id          INTEGER NOT NULL,
    creator_id        INTEGER NOT NULL,
    question          TEXT    NOT NULL,
    kind              TEXT    NOT NULL DEFAULT 'single',
    surface           TEXT    NOT NULL DEFAULT 'native',
    multi             INTEGER NOT NULL DEFAULT 0,
    anonymous         INTEGER NOT NULL DEFAULT 0,
    results           TEXT    NOT NULL DEFAULT 'live',
    hours             INTEGER NOT NULL DEFAULT 24,
    auto_thread       INTEGER NOT NULL DEFAULT 0,
    channel_id        INTEGER,
    message_id        INTEGER,
    shadow_message_id INTEGER,
    thread_id         INTEGER,
    ping_role_id      INTEGER,
    status            TEXT    NOT NULL DEFAULT 'draft',
    opens_at          TEXT,
    closes_at         TEXT,
    reminded_at       TEXT,
    closed_at         TEXT,
    archived_at       TEXT,
    total_votes       INTEGER,
    recurrence        TEXT,
    recur_at          TEXT,
    recur_tz          TEXT,
    recur_next_at     TEXT,
    schedule_id       INTEGER,
    review_channel_id INTEGER,
    review_message_id INTEGER,
    decided_by        INTEGER,
    decided_at        TEXT,
    deny_reason       TEXT,
    vote_scheme       TEXT,
    created_at        TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS polls_by_status ON polls(guild_id, status, closes_at);

CREATE TABLE IF NOT EXISTS poll_options (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    poll_id     INTEGER NOT NULL,
    position    INTEGER NOT NULL,
    answer_id   INTEGER,
    label       TEXT    NOT NULL,
    emoji       TEXT,
    value       TEXT,
    final_votes INTEGER
);

CREATE UNIQUE INDEX IF NOT EXISTS poll_options_slot ON poll_options(poll_id, position);

CREATE TABLE IF NOT EXISTS poll_votes (
    poll_id   INTEGER NOT NULL,
    option_id INTEGER,
    user_id   INTEGER NOT NULL,
    answer    TEXT,
    at        TEXT    NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS poll_votes_one ON poll_votes(poll_id, option_id, user_id);

CREATE TABLE IF NOT EXISTS poll_results (
    poll_id         INTEGER PRIMARY KEY,
    closed_at       TEXT    NOT NULL,
    total_votes     INTEGER NOT NULL DEFAULT 0,
    winner_position INTEGER,
    counts          TEXT    NOT NULL,
    votes_dropped   INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS poll_drafts (
    guild_id INTEGER NOT NULL,
    user_id  INTEGER NOT NULL,
    payload  TEXT    NOT NULL,
    saved_at TEXT    NOT NULL,
    PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS chat_intents (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id   INTEGER NOT NULL,
    name       TEXT    NOT NULL,
    triggers   TEXT    NOT NULL DEFAULT '[]',
    kind       TEXT    NOT NULL DEFAULT 'canned'
               CHECK (kind IN ('canned', 'data', 'route')),
    enabled    INTEGER NOT NULL DEFAULT 1,
    sort       INTEGER NOT NULL DEFAULT 0,
    created_by INTEGER,
    updated_at TEXT    NOT NULL,
    UNIQUE (guild_id, name)
);

CREATE TABLE IF NOT EXISTS chat_lines (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    intent_id  INTEGER NOT NULL REFERENCES chat_intents(id) ON DELETE CASCADE,
    text       TEXT    NOT NULL,
    slot       TEXT    NOT NULL DEFAULT 'filled'
               CHECK (slot IN ('filled', 'empty', 'attendee')),
    enabled    INTEGER NOT NULL DEFAULT 1,
    created_by INTEGER,
    updated_at TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS chat_lines_by_intent ON chat_lines(intent_id, id);

CREATE TABLE IF NOT EXISTS knowledge_sections (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id   INTEGER NOT NULL,
    title      TEXT    NOT NULL,
    body       TEXT    NOT NULL,
    source     TEXT    NOT NULL DEFAULT 'staff'
               CHECK (source IN ('staff', 'server')),
    tag        TEXT,
    updated_at TEXT    NOT NULL,
    updated_by INTEGER
);

CREATE INDEX IF NOT EXISTS knowledge_sections_by_source
    ON knowledge_sections(guild_id, source, id);

CREATE UNIQUE INDEX IF NOT EXISTS knowledge_sections_one_title
    ON knowledge_sections(guild_id, source, title);

CREATE TABLE IF NOT EXISTS personality_tropes (
    name       TEXT    PRIMARY KEY,
    label      TEXT    NOT NULL,
    voice      TEXT    NOT NULL,
    neighbours TEXT    NOT NULL DEFAULT '[]',
    enabled    INTEGER NOT NULL DEFAULT 1,
    sort       INTEGER NOT NULL DEFAULT 0,
    source     TEXT    NOT NULL DEFAULT 'gabi',
    updated_at TEXT    NOT NULL,
    updated_by INTEGER,
    voice_edited_by INTEGER,
    voice_edited_at TEXT
);

CREATE TABLE IF NOT EXISTS chat_window (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id   INTEGER,
    channel_id INTEGER NOT NULL,
    user_id    INTEGER NOT NULL,
    at         TEXT    NOT NULL,
    speaker    TEXT    NOT NULL CHECK (speaker IN ('member', 'bot')),
    content    TEXT    NOT NULL,
    tier       TEXT
);

CREATE INDEX IF NOT EXISTS chat_window_by_place ON chat_window(channel_id, user_id, id);
CREATE INDEX IF NOT EXISTS chat_window_by_age ON chat_window(at);

CREATE TABLE IF NOT EXISTS chat_profiles (
    user_id    INTEGER NOT NULL,
    guild_id   INTEGER NOT NULL,
    call_me    TEXT,
    notes      TEXT    NOT NULL DEFAULT '[]',
    threads    TEXT    NOT NULL DEFAULT '[]',
    turns_seen INTEGER NOT NULL DEFAULT 0,
    created_at TEXT    NOT NULL,
    updated_at TEXT    NOT NULL,
    PRIMARY KEY (user_id, guild_id)
);

CREATE INDEX IF NOT EXISTS chat_profiles_by_age ON chat_profiles(updated_at);

CREATE TABLE IF NOT EXISTS chat_memory_optout (
    user_id  INTEGER NOT NULL,
    guild_id INTEGER NOT NULL,
    at       TEXT    NOT NULL,
    PRIMARY KEY (user_id, guild_id)
);

CREATE TABLE IF NOT EXISTS llm_ledger (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    at                 TEXT    NOT NULL,
    guild_id           INTEGER,
    user_id            INTEGER,
    turn               TEXT    NOT NULL,
    provider           TEXT    NOT NULL,
    model              TEXT    NOT NULL,
    tier               TEXT    NOT NULL,
    outcome            TEXT    NOT NULL DEFAULT 'ok'
                       CHECK (outcome IN ('ok', 'error')),
    input_tokens       INTEGER NOT NULL DEFAULT 0,
    output_tokens      INTEGER NOT NULL DEFAULT 0,
    cache_read_tokens  INTEGER NOT NULL DEFAULT 0,
    cache_write_tokens INTEGER NOT NULL DEFAULT 0,
    cost_microdollars  INTEGER NOT NULL DEFAULT 0,
    trope              TEXT
);

CREATE INDEX IF NOT EXISTS llm_ledger_by_at ON llm_ledger(at);
CREATE INDEX IF NOT EXISTS llm_ledger_by_person ON llm_ledger(user_id, at);

CREATE TABLE IF NOT EXISTS requests (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id       INTEGER NOT NULL,
    user_id        INTEGER NOT NULL,
    what           TEXT    NOT NULL,
    why            TEXT    NOT NULL,
    due_on         TEXT,
    status         TEXT    NOT NULL DEFAULT 'open',
    priority       INTEGER,
    held_from      TEXT,
    built          TEXT,
    how_to_test    TEXT,
    ready_by       INTEGER,
    sent_back_reason TEXT,
    check_asked_by INTEGER,
    check_asked_at TEXT,
    assignee_id    INTEGER,
    notes          TEXT,
    created_at     TEXT    NOT NULL,
    decided_by     INTEGER,
    decided_at     TEXT,
    decline_reason TEXT,
    done_at        TEXT,
    message_id     INTEGER,
    thread_id      INTEGER,
    source         TEXT    NOT NULL DEFAULT 'panel',
    moved_to       TEXT
);

CREATE INDEX IF NOT EXISTS requests_by_status ON requests(guild_id, status, id);

CREATE TABLE IF NOT EXISTS request_comments (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id INTEGER NOT NULL REFERENCES requests(id) ON DELETE CASCADE,
    author_id  INTEGER NOT NULL,
    text       TEXT    NOT NULL,
    at         TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS request_comments_by_request ON request_comments(request_id, id);

CREATE TABLE IF NOT EXISTS sessions (
    id         TEXT    PRIMARY KEY,
    user_id    INTEGER NOT NULL,
    created_at TEXT    NOT NULL,
    expires_at TEXT    NOT NULL,
    revoked_at TEXT
);

CREATE INDEX IF NOT EXISTS sessions_by_user ON sessions(user_id, created_at);

CREATE TABLE IF NOT EXISTS raid_trains (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id           INTEGER NOT NULL,
    organizer_id       INTEGER NOT NULL,
    title              TEXT    NOT NULL,
    description        TEXT,
    starts_at          TEXT    NOT NULL,
    slot_minutes       INTEGER NOT NULL,
    slot_count         INTEGER NOT NULL,
    status             TEXT    NOT NULL DEFAULT 'open',
    channel_id         INTEGER,
    lineup_message_id  INTEGER,
    thread_id          INTEGER,
    scheduled_event_id INTEGER,
    cancel_reason      TEXT,
    event_id           INTEGER,
    created_at         TEXT    NOT NULL,
    updated_at         TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS raid_trains_by_status ON raid_trains(guild_id, status, starts_at);

CREATE TABLE IF NOT EXISTS raid_slots (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    train_id       INTEGER NOT NULL REFERENCES raid_trains(id) ON DELETE CASCADE,
    position       INTEGER NOT NULL,
    starts_at      TEXT    NOT NULL,
    ends_at        TEXT    NOT NULL,
    user_id        INTEGER,
    twitch_login   TEXT,
    claimed_at     TEXT,
    assigned_by    INTEGER,
    locked         INTEGER NOT NULL DEFAULT 0,
    reminded_at    TEXT,
    checked_in_at  TEXT,
    live_posted_at TEXT,
    UNIQUE (train_id, position)
);

CREATE INDEX IF NOT EXISTS raid_slots_due ON raid_slots(starts_at, reminded_at);
CREATE INDEX IF NOT EXISTS raid_slots_by_member ON raid_slots(user_id, starts_at);
CREATE TABLE IF NOT EXISTS application_forms (
{APPLICATION_FORMS_COLUMNS}
);

CREATE TABLE IF NOT EXISTS application_questions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    form_id     INTEGER NOT NULL REFERENCES application_forms(id) ON DELETE CASCADE,
    position    INTEGER NOT NULL,
    label       TEXT    NOT NULL,
    style       TEXT    NOT NULL DEFAULT 'short',
    required    INTEGER NOT NULL DEFAULT 1,
    placeholder TEXT,
    UNIQUE (form_id, position)
);

CREATE TABLE IF NOT EXISTS applications (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id        INTEGER NOT NULL,
    form_id         INTEGER NOT NULL,
    user_id         INTEGER NOT NULL,
    answers         TEXT    NOT NULL,
    status          TEXT    NOT NULL DEFAULT 'pending',
    submitted_at    TEXT    NOT NULL,
    decided_by      INTEGER,
    decided_at      TEXT,
    deny_reason     TEXT,
    grant_id        INTEGER,
    card_channel_id INTEGER,
    card_message_id INTEGER
);

CREATE UNIQUE INDEX IF NOT EXISTS applications_one_open
    ON applications(form_id, user_id) WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS applications_by_status
    ON applications(guild_id, status, id);

CREATE TABLE IF NOT EXISTS selftest_runs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id    INTEGER NOT NULL,
    started_at  TEXT    NOT NULL,
    finished_at TEXT,
    ok          INTEGER NOT NULL DEFAULT 0,
    failed      INTEGER NOT NULL DEFAULT 0,
    posted      INTEGER NOT NULL DEFAULT 0,
    purged_at   TEXT,
    via         TEXT    NOT NULL,
    actor_id    INTEGER,
    keep_minutes INTEGER
);

CREATE INDEX IF NOT EXISTS selftest_runs_by_guild
    ON selftest_runs(guild_id, id);

CREATE TABLE IF NOT EXISTS selftest_messages (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id     INTEGER NOT NULL,
    guild_id   INTEGER NOT NULL,
    channel_id INTEGER NOT NULL,
    message_id INTEGER NOT NULL,
    posted_at  TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS selftest_messages_by_run
    ON selftest_messages(run_id, id);

CREATE INDEX IF NOT EXISTS action_log_by_kind
    ON action_log(guild_id, kind, id);

CREATE TABLE IF NOT EXISTS guides (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id   INTEGER NOT NULL,
    slug       TEXT    NOT NULL,
    title      TEXT    NOT NULL,
    goal       TEXT    NOT NULL,
    audience   TEXT    NOT NULL DEFAULT 'member'
               CHECK (audience IN ('member', 'staff')),
    feature    TEXT    NOT NULL,
    command    TEXT,
    sort       INTEGER NOT NULL DEFAULT 0,
    published  INTEGER NOT NULL DEFAULT 1,
    seed_hash  TEXT,
    updated_at TEXT    NOT NULL,
    updated_by INTEGER,
    UNIQUE (guild_id, slug)
);

CREATE UNIQUE INDEX IF NOT EXISTS guides_one_published_command
    ON guides(guild_id, command, audience) WHERE published = 1 AND command IS NOT NULL;
CREATE INDEX IF NOT EXISTS guides_by_guild ON guides(guild_id, sort, id);

CREATE TABLE IF NOT EXISTS guide_steps (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    guide_id    INTEGER NOT NULL REFERENCES guides(id) ON DELETE CASCADE,
    position    INTEGER NOT NULL,
    do_text     TEXT    NOT NULL,
    expect_text TEXT,
    media_id    INTEGER,
    seed_do     TEXT,
    seed_expect TEXT
);

CREATE INDEX IF NOT EXISTS guide_steps_by_guide ON guide_steps(guide_id, position, id);

CREATE TABLE IF NOT EXISTS guide_faults (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    guide_id INTEGER NOT NULL REFERENCES guides(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    symptom  TEXT    NOT NULL,
    answer   TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS guide_faults_by_guide ON guide_faults(guide_id, position, id);

CREATE TABLE IF NOT EXISTS guide_facts (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    guide_id INTEGER NOT NULL REFERENCES guides(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    kind     TEXT    NOT NULL CHECK (kind IN ('setting', 'probe')),
    ref      TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS guide_facts_by_guide ON guide_facts(guide_id, position, id);

CREATE TABLE IF NOT EXISTS guide_media (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id     INTEGER NOT NULL,
    guide_id     INTEGER NOT NULL REFERENCES guides(id) ON DELETE CASCADE,
    step_id      INTEGER,
    file         TEXT    NOT NULL,
    sha256       TEXT    NOT NULL,
    width        INTEGER,
    height       INTEGER,
    bytes        INTEGER NOT NULL DEFAULT 0,
    source       TEXT    NOT NULL DEFAULT 'capture'
                 CHECK (source IN ('capture', 'mock')),
    surface      TEXT    NOT NULL DEFAULT 'discord'
                 CHECK (surface IN ('discord', 'website')),
    shot_release TEXT,
    shot_by      INTEGER,
    shot_at      TEXT    NOT NULL,
    caption      TEXT,
    stale        INTEGER NOT NULL DEFAULT 0,
    stale_since  TEXT
);

CREATE INDEX IF NOT EXISTS guide_media_by_guide ON guide_media(guide_id, id);
CREATE INDEX IF NOT EXISTS guide_media_stale ON guide_media(guild_id, stale, id);

CREATE TABLE IF NOT EXISTS guide_releases (
    release          TEXT PRIMARY KEY,
    "commit"         TEXT,
    shipped_at       TEXT NOT NULL,
    changed_features TEXT NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS posts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id    INTEGER NOT NULL,
    slug        TEXT    NOT NULL,
    title       TEXT    NOT NULL,
    channel_id  INTEGER,
    body        TEXT    NOT NULL DEFAULT '',
    style       TEXT    NOT NULL DEFAULT 'plain'
                CHECK (style IN ('plain', 'embed')),
    pin         INTEGER NOT NULL DEFAULT 1,
    message_id  INTEGER,
    shadow_message_id INTEGER,
    posted_hash TEXT,
    posted_at   TEXT,
    posted_by   INTEGER,
    seed_hash   TEXT,
    updated_at  TEXT    NOT NULL,
    updated_by  INTEGER,
    UNIQUE (guild_id, slug)
);

CREATE INDEX IF NOT EXISTS posts_by_guild ON posts(guild_id, id);

CREATE TABLE IF NOT EXISTS post_versions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id   INTEGER NOT NULL,
    post_id    INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    n          INTEGER NOT NULL,
    title      TEXT    NOT NULL,
    body       TEXT    NOT NULL DEFAULT '',
    style      TEXT    NOT NULL DEFAULT 'plain'
               CHECK (style IN ('plain', 'embed')),
    channel_id INTEGER,
    pin        INTEGER NOT NULL DEFAULT 1,
    saved_at   TEXT    NOT NULL,
    saved_by   INTEGER,
    via        TEXT    NOT NULL DEFAULT 'discord',
    because    TEXT    NOT NULL DEFAULT 'saved',
    UNIQUE (post_id, n)
);

CREATE INDEX IF NOT EXISTS post_versions_by_post ON post_versions(post_id, n);

CREATE TABLE IF NOT EXISTS meetings (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id         INTEGER NOT NULL,
    channel_id       INTEGER NOT NULL,
    started_by       INTEGER NOT NULL,
    started_at       TEXT    NOT NULL,
    ended_at         TEXT,
    ended_reason     TEXT,
    notes            TEXT,
    notes_channel_id INTEGER,
    notes_message_id INTEGER,
    status           TEXT    NOT NULL DEFAULT 'recording'
                     CHECK (status IN ('recording', 'writing', 'done', 'failed'))
);

CREATE UNIQUE INDEX IF NOT EXISTS meetings_one_open
    ON meetings(guild_id) WHERE ended_at IS NULL;
CREATE INDEX IF NOT EXISTS meetings_by_guild ON meetings(guild_id, id);

CREATE TABLE IF NOT EXISTS meeting_lines (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    meeting_id INTEGER NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    speaker_id INTEGER NOT NULL,
    speaker    TEXT    NOT NULL,
    started_at TEXT    NOT NULL,
    text       TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS meeting_lines_by_meeting
    ON meeting_lines(meeting_id, started_at, id);

CREATE TABLE IF NOT EXISTS spotlight_channels (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id       INTEGER NOT NULL,
    twitch_login   TEXT    NOT NULL,
    twitch_user_id TEXT,
    display_name   TEXT,
    note           TEXT,
    added_by       INTEGER,
    added_at       TEXT    NOT NULL,
    starts_at      TEXT,
    expires_at     TEXT,
    bump_hours     INTEGER,
    pin            INTEGER NOT NULL DEFAULT 1,
    event_id       INTEGER,
    spotlight          INTEGER NOT NULL DEFAULT 1,
    announce           INTEGER NOT NULL DEFAULT 1,
    youtube_channel_id TEXT,
    youtube_handle     TEXT,
    ping_mode          TEXT    NOT NULL DEFAULT 'always',
    UNIQUE (guild_id, twitch_login)
);

CREATE TABLE IF NOT EXISTS spotlight_sessions (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id             INTEGER NOT NULL,
    spotlight_id         INTEGER NOT NULL,
    started_at           TEXT    NOT NULL,
    ended_at             TEXT,
    title                TEXT,
    game                 TEXT,
    url                  TEXT,
    mode                 TEXT    NOT NULL,
    announced_message_id INTEGER,
    last_bump_at         TEXT,
    bump_count           INTEGER NOT NULL DEFAULT 0,
    pinging_last         INTEGER
);

CREATE UNIQUE INDEX IF NOT EXISTS spotlight_open_session
    ON spotlight_sessions(spotlight_id) WHERE ended_at IS NULL;

CREATE INDEX IF NOT EXISTS spotlight_sessions_by_guild
    ON spotlight_sessions(guild_id, id);

CREATE TABLE IF NOT EXISTS spotlight_bumps (
    session_id INTEGER NOT NULL,
    message_id INTEGER NOT NULL,
    at         TEXT    NOT NULL,
    PRIMARY KEY (session_id, message_id)
);

CREATE TABLE IF NOT EXISTS spotlight_ping_windows (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id     INTEGER NOT NULL,
    spotlight_id INTEGER NOT NULL,
    starts_at    TEXT    NOT NULL,
    ends_at      TEXT    NOT NULL,
    note         TEXT,
    source       TEXT    NOT NULL DEFAULT 'staff',
    source_id    INTEGER,
    added_by     INTEGER,
    added_at     TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS spotlight_ping_windows_by_channel
    ON spotlight_ping_windows(spotlight_id, starts_at);

CREATE TABLE IF NOT EXISTS channel_notes (
    guild_id   INTEGER NOT NULL,
    channel_id INTEGER NOT NULL,
    note       TEXT    NOT NULL,
    set_by     INTEGER,
    set_at     TEXT    NOT NULL,
    PRIMARY KEY (guild_id, channel_id)
);

CREATE TABLE IF NOT EXISTS chat_voice (
    guild_id   INTEGER NOT NULL,
    user_id    INTEGER NOT NULL,
    trope      TEXT,
    turns      INTEGER NOT NULL DEFAULT 0,
    since      TEXT,
    pinned     TEXT,
    pinned_by  INTEGER,
    pinned_at  TEXT,
    PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS channel_drafts (
    guild_id   INTEGER NOT NULL,
    channel_id INTEGER NOT NULL,
    draft      TEXT    NOT NULL,
    status     TEXT    NOT NULL DEFAULT 'draft',
    decided_by INTEGER,
    decided_at TEXT,
    PRIMARY KEY (guild_id, channel_id)
);

CREATE TABLE IF NOT EXISTS channel_reach (
    guild_id   INTEGER NOT NULL,
    channel_id INTEGER NOT NULL,
    shown      INTEGER NOT NULL,
    set_by     INTEGER,
    set_at     TEXT    NOT NULL,
    PRIMARY KEY (guild_id, channel_id)
);

CREATE TABLE IF NOT EXISTS chat_review (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id            INTEGER NOT NULL,
    channel_id          INTEGER NOT NULL,
    user_id             INTEGER NOT NULL,
    asked               TEXT    NOT NULL,
    answered            TEXT    NOT NULL,
    tier                TEXT,
    trope               TEXT,
    intent              TEXT,
    reason              TEXT    NOT NULL,
    message_id          INTEGER,
    reply_id            INTEGER,
    at                  TEXT    NOT NULL,
    suggested_intent_id INTEGER,
    suggested_intent    TEXT,
    suggested_phrase    TEXT,
    suggested_kind      TEXT
                        CHECK (suggested_kind IN ('intent', 'phrase', 'knowledge', 'none')),
    suggested_line      TEXT,
    suggested_section   TEXT,
    suggested_why       TEXT,
    tagged_at           TEXT,
    status              TEXT    NOT NULL DEFAULT 'open'
                        CHECK (status IN ('open', 'approved', 'changed', 'dismissed')),
    decided_by          INTEGER,
    decided_at          TEXT
);

CREATE INDEX IF NOT EXISTS chat_review_by_status ON chat_review(guild_id, status, id);
CREATE UNIQUE INDEX IF NOT EXISTS chat_review_one_per_reply ON chat_review(reply_id);

CREATE TABLE IF NOT EXISTS marathons (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id         INTEGER NOT NULL,
    name             TEXT    NOT NULL,
    schedule_url     TEXT    NOT NULL,
    source           TEXT    NOT NULL,
    source_ref       TEXT    NOT NULL,
    spotlight_id     INTEGER,
    starts_at        TEXT,
    ends_at          TEXT,
    active           INTEGER NOT NULL DEFAULT 1,
    poll_minutes     INTEGER,
    board_channel_id INTEGER,
    board_message_id INTEGER,
    board_pinned     INTEGER NOT NULL DEFAULT 0,
    last_fetched_at  TEXT,
    last_fetch_ok    INTEGER,
    last_error       TEXT,
    fetch_failures   INTEGER NOT NULL DEFAULT 0,
    fetch_hash       TEXT,
    added_by         INTEGER,
    added_at         TEXT    NOT NULL,
    UNIQUE (guild_id, schedule_url)
);

CREATE TABLE IF NOT EXISTS marathon_runs (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    marathon_id           INTEGER NOT NULL,
    external_id           TEXT    NOT NULL,
    order_no              INTEGER,
    game                  TEXT    NOT NULL,
    display_name          TEXT,
    twitch_game           TEXT,
    category              TEXT,
    runners_text          TEXT,
    people                TEXT    NOT NULL DEFAULT '[]',
    scheduled_at          TEXT,
    ends_at               TEXT,
    run_seconds           INTEGER,
    previous_scheduled_at TEXT,
    moved_at              TEXT,
    state                 TEXT    NOT NULL DEFAULT 'upcoming',
    live_at               TEXT,
    live_because          TEXT,
    done_at               TEXT,
    shout_message_id      INTEGER,
    shout_channel_id      INTEGER,
    reminders_sent        TEXT    NOT NULL DEFAULT '[]',
    first_seen_at         TEXT    NOT NULL,
    last_seen_at          TEXT    NOT NULL,
    UNIQUE (marathon_id, external_id)
);

CREATE INDEX IF NOT EXISTS marathon_runs_by_time
    ON marathon_runs(marathon_id, scheduled_at);

CREATE TABLE IF NOT EXISTS marathon_people (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id    INTEGER NOT NULL,
    marathon_id INTEGER,
    runner_name TEXT    NOT NULL,
    user_id     INTEGER NOT NULL,
    added_by    INTEGER,
    added_at    TEXT    NOT NULL,
    UNIQUE (guild_id, marathon_id, runner_name)
);

CREATE UNIQUE INDEX IF NOT EXISTS marathon_people_everywhere
    ON marathon_people(guild_id, runner_name) WHERE marathon_id IS NULL;

CREATE TABLE IF NOT EXISTS marathon_feeds (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id        INTEGER NOT NULL,
    source          TEXT    NOT NULL,
    feed_ref        TEXT    NOT NULL,
    spotlight_id    INTEGER NOT NULL,
    name            TEXT    NOT NULL,
    action          TEXT    NOT NULL DEFAULT 'add',
    active          INTEGER NOT NULL DEFAULT 1,
    last_checked_at TEXT,
    last_ok         INTEGER,
    last_error      TEXT,
    checks_failed   INTEGER NOT NULL DEFAULT 0,
    suggested       TEXT    NOT NULL DEFAULT '[]',
    ignored         TEXT    NOT NULL DEFAULT '[]',
    added_by        INTEGER,
    added_at        TEXT    NOT NULL,
    UNIQUE (guild_id, source, feed_ref)
);

CREATE UNIQUE INDEX IF NOT EXISTS marathon_feeds_one_per_channel
    ON marathon_feeds(guild_id, spotlight_id);

CREATE TABLE IF NOT EXISTS marathon_feed_seeds (
    guild_id     INTEGER NOT NULL,
    twitch_login TEXT    NOT NULL,
    seeded_at    TEXT    NOT NULL,
    PRIMARY KEY (guild_id, twitch_login)
);

CREATE TABLE IF NOT EXISTS marathon_spotlights (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    marathon_id  INTEGER NOT NULL,
    login        TEXT    NOT NULL,
    spotlight_id INTEGER NOT NULL,
    run_id       INTEGER,
    added_by     INTEGER,
    added_at     TEXT    NOT NULL,
    UNIQUE (marathon_id, login)
);
"""

ADDED_COLUMNS: tuple[tuple[str, str, str], ...] = (
    ("role_menus", "approval", "INTEGER NOT NULL DEFAULT 0"),
    ("role_menus", "expires_days", "INTEGER"),
    ("role_menus", "retry_days", "INTEGER NOT NULL DEFAULT 7"),
    ("golive_sessions", "live_role_added", "INTEGER NOT NULL DEFAULT 0"),
    ("golive_sessions", "platform", "TEXT"),
    ("golive_sessions", "live_role_id", "INTEGER"),
    ("events", "card_channel_id", "INTEGER"),
    ("events", "where_kind", "TEXT"),
    ("events", "where_channel_id", "INTEGER"),
    ("birthdays", "role_added_id", "INTEGER"),
    ("modmail_messages", "delivered", "INTEGER NOT NULL DEFAULT 1"),
    ("modmail_tickets", "card_message_id", "INTEGER"),
    ("modmail_tickets", "practice", "INTEGER NOT NULL DEFAULT 0"),
    ("modmail_tickets", "source", "TEXT NOT NULL DEFAULT 'dm'"),
    ("modmail_tickets", "opened_by", "INTEGER"),
    ("mod_cases", "actions", "TEXT"),
    ("mod_cases", "done", "TEXT"),
    ("mod_cases", "failed", "TEXT"),
    ("mod_cases", "message_id", "INTEGER"),
    ("mod_cases", "channel_id", "INTEGER"),
    ("mod_cases", "note", "TEXT"),
    ("mod_cases", "note_by", "INTEGER"),
    ("mod_cases", "note_at", "TEXT"),
    ("mod_cases", "voided_at", "TEXT"),
    ("mod_cases", "voided_by", "INTEGER"),
    ("mod_cases", "void_reason", "TEXT"),
    ("tempvoice_channels", "panel_channel_id", "INTEGER"),
    ("tempvoice_prefs", "bitrate", "INTEGER"),
    ("tempvoice_prefs", "region", "TEXT"),
    ("tempvoice_prefs", "permitted_ids", "TEXT"),
    ("tempvoice_prefs", "banned_ids", "TEXT"),
    ("polls", "vote_scheme", "TEXT"),
    ("polls", "shadow_message_id", "INTEGER"),
    ("requests", "held_from", "TEXT"),
    ("requests", "built", "TEXT"),
    ("requests", "how_to_test", "TEXT"),
    ("requests", "ready_by", "INTEGER"),
    ("requests", "sent_back_reason", "TEXT"),
    ("requests", "check_asked_by", "INTEGER"),
    ("requests", "check_asked_at", "TEXT"),
    ("requests", "thread_id", "INTEGER"),
    ("requests", "source", "TEXT NOT NULL DEFAULT 'panel'"),
    ("posts", "shadow_message_id", "INTEGER"),
    ("golive_fan_roles", "unworn_since", "TEXT"),
    ("requests", "moved_to", "TEXT"),
    ("events", "moved_to", "TEXT"),
    ("modmail_tickets", "moved_to", "TEXT"),
    ("events", "review_kind", "TEXT"),
    ("golive_sessions", "also_source", "TEXT"),
    ("golive_sessions", "also_url", "TEXT"),
    ("golive_sessions", "also_platform", "TEXT"),
    ("golive_sessions", "also_started_at", "TEXT"),
    ("selftest_runs", "keep_minutes", "INTEGER"),
    ("golive_fan_roles", "spotlight_id", "INTEGER"),
    ("raid_trains", "event_id", "INTEGER"),
    ("spotlight_channels", "spotlight", "INTEGER NOT NULL DEFAULT 1"),
    ("spotlight_channels", "announce", "INTEGER NOT NULL DEFAULT 1"),
    ("spotlight_channels", "youtube_channel_id", "TEXT"),
    ("spotlight_channels", "youtube_handle", "TEXT"),
    ("spotlight_channels", "starts_at", "TEXT"),
    ("spotlight_channels", "ping_mode", "TEXT NOT NULL DEFAULT 'always'"),
    ("spotlight_sessions", "pinging_last", "INTEGER"),
    ("personality_tropes", "voice_edited_by", "INTEGER"),
    ("personality_tropes", "voice_edited_at", "TEXT"),
    ("llm_ledger", "trope", "TEXT"),
    ("marathons", "suggested_next", "TEXT"),
    ("marathons", "event_id", "INTEGER"),
    ("marathons", "event_wanted", "INTEGER NOT NULL DEFAULT 0"),
    ("marathons", "feed_id", "INTEGER"),
    ("marathons", "event_mode", "TEXT NOT NULL DEFAULT 'none'"),
    ("marathons", "held_by_channel", "INTEGER NOT NULL DEFAULT 0"),
    ("marathon_runs", "event_id", "INTEGER"),
    ("marathon_feeds", "event_mode", "TEXT"),
    ("marathon_feeds", "held_by_channel", "INTEGER NOT NULL DEFAULT 0"),
    ("spotlight_channels", "marathons", "INTEGER NOT NULL DEFAULT 1"),
)

CARRIED_EVENT_WISH = (
    "UPDATE marathons SET event_mode = 'marathon' "
    "WHERE event_id IS NOT NULL OR event_wanted = 1"
)
BACKFILLS: dict[tuple[str, str], str] = {("marathons", "event_mode"): CARRIED_EVENT_WISH}

RETIRED_REQUEST_STATUSES = ("pending", "approved", "planned")
OPEN_THE_RETIRED_STATUSES = (
    "UPDATE requests SET status = 'open' WHERE status IN "
    f"({', '.join('?' for _ in RETIRED_REQUEST_STATUSES)})"
)

BACKFILL_POST_VERSIONS = (
    "INSERT INTO post_versions(guild_id, post_id, n, title, body, style, channel_id, pin, "
    "saved_at, saved_by, via, because) "
    "SELECT guild_id, id, 1, title, body, style, channel_id, pin, "
    "COALESCE(updated_at, ?), updated_by, 'boot', 'backfill' FROM posts "
    "WHERE NOT EXISTS (SELECT 1 FROM post_versions WHERE post_versions.post_id = posts.id)"
)

MOD_CASES_CARRIED_OVER = (
    "id, guild_id, user_id, kind, moderator_id, reason, duration_s, at, mode, applied, "
    "log_message_id"
)
MOD_CASES_OLD = "mod_cases_before_null_user"

FAN_ROLES_OLD = "golive_fan_roles_before_spotlights"
FAN_ROLES_INDEXES = ("golive_fan_roles_one_member", "golive_fan_roles_one_spotlight")

CLOSE_DUPLICATE_OPEN_SESSIONS = """
UPDATE golive_sessions SET ended_at = ?
WHERE ended_at IS NULL AND id NOT IN (
    SELECT MAX(id) FROM golive_sessions WHERE ended_at IS NULL GROUP BY guild_id, user_id
)
"""


class Database:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._conn: aiosqlite.Connection | None = None

    @property
    def is_connected(self) -> bool:
        return self._conn is not None

    @property
    def conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("Database.connect() has not been called")
        return self._conn

    async def connect(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(self.path)
        self._conn.row_factory = aiosqlite.Row
        await self._loosen_application_form_roles()
        await self._conn.execute("PRAGMA journal_mode=WAL")
        await self._conn.execute("PRAGMA foreign_keys=ON")
        await self._close_duplicate_open_sessions()
        await self._set_aside_mod_cases_with_a_required_user()
        await self._set_aside_fan_roles_that_require_a_member()
        await self._conn.executescript(SCHEMA)
        await self._add_missing_columns()
        await self._restore_set_aside_mod_cases()
        await self._restore_set_aside_fan_roles()
        await self._open_the_retired_request_statuses()
        await self._backfill_post_versions()
        await self._conn.execute(
            "INSERT OR REPLACE INTO schema_meta(key, value) VALUES ('schema_version', ?)",
            (str(SCHEMA_VERSION),),
        )
        await self._conn.commit()

    async def _table_columns(self, table: str) -> set[str]:
        cur = await self.conn.execute(f"PRAGMA table_info({table})")
        return {str(row["name"]) for row in await cur.fetchall()}

    async def _close_duplicate_open_sessions(self) -> None:
        if not await self._table_columns("golive_sessions"):
            return
        cur = await self.conn.execute(
            CLOSE_DUPLICATE_OPEN_SESSIONS, (datetime.now(UTC).isoformat(),)
        )
        if cur.rowcount and cur.rowcount > 0:
            log.warning(
                "database: closed %d duplicate open go-live session(s) before indexing them",
                cur.rowcount,
            )

    async def _loosen_application_form_roles(self) -> None:
        """Schema 28: a form may keep a list instead of handing a role over."""
        cur = await self.conn.execute("PRAGMA table_info(application_forms)")
        rows = await cur.fetchall()
        if not any(row["name"] == "role_id" and row["notnull"] for row in rows):
            return
        await self.conn.execute(f"DROP TABLE IF EXISTS {APPLICATION_FORMS_LOOSENED}")
        await self.conn.execute(
            f"CREATE TABLE {APPLICATION_FORMS_LOOSENED} (\n{APPLICATION_FORMS_COLUMNS}\n)"
        )
        await self.conn.execute(
            f"INSERT INTO {APPLICATION_FORMS_LOOSENED} SELECT * FROM application_forms"
        )
        await self.conn.execute("DROP TABLE application_forms")
        await self.conn.execute(
            f"ALTER TABLE {APPLICATION_FORMS_LOOSENED} RENAME TO application_forms"
        )
        await self.conn.commit()
        log.warning("database: rebuilding application_forms so a form may have no role")

    async def _set_aside_mod_cases_with_a_required_user(self) -> None:
        cur = await self.conn.execute("PRAGMA table_info(mod_cases)")
        rows = await cur.fetchall()
        if not any(row["name"] == "user_id" and row["notnull"] for row in rows):
            return
        await self.conn.execute("DROP INDEX IF EXISTS mod_cases_by_user")
        await self.conn.execute("DROP INDEX IF EXISTS mod_cases_by_kind")
        await self.conn.execute(f"ALTER TABLE mod_cases RENAME TO {MOD_CASES_OLD}")
        log.warning("database: rebuilding mod_cases so a case may belong to a channel")

    async def _restore_set_aside_mod_cases(self) -> None:
        if not await self._table_columns(MOD_CASES_OLD):
            return
        await self.conn.execute(
            f"INSERT INTO mod_cases({MOD_CASES_CARRIED_OVER}) "
            f"SELECT {MOD_CASES_CARRIED_OVER} FROM {MOD_CASES_OLD}"
        )
        await self.conn.execute(f"DROP TABLE {MOD_CASES_OLD}")

    async def _set_aside_fan_roles_that_require_a_member(self) -> None:
        """Schema 50: a ping role may belong to a spotlight channel, which has no member."""
        cur = await self.conn.execute("PRAGMA table_info(golive_fan_roles)")
        rows = await cur.fetchall()
        if not any(row["name"] == "user_id" and row["notnull"] for row in rows):
            return
        for name in FAN_ROLES_INDEXES:
            await self.conn.execute(f"DROP INDEX IF EXISTS {name}")
        await self.conn.execute(f"ALTER TABLE golive_fan_roles RENAME TO {FAN_ROLES_OLD}")
        log.warning("database: rebuilding golive_fan_roles so a role may belong to a channel")

    async def _restore_set_aside_fan_roles(self) -> None:
        carried = await self._table_columns(FAN_ROLES_OLD)
        if not carried:
            return
        names = ", ".join(sorted(carried & await self._table_columns("golive_fan_roles")))
        await self.conn.execute(
            f"INSERT INTO golive_fan_roles({names}) SELECT {names} FROM {FAN_ROLES_OLD}"
        )
        await self.conn.execute(f"DROP TABLE {FAN_ROLES_OLD}")

    async def _open_the_retired_request_statuses(self) -> None:
        """Schema 23: pending, approved and planned all became `open`; nothing else moves."""
        cur = await self.conn.execute(
            OPEN_THE_RETIRED_STATUSES, RETIRED_REQUEST_STATUSES
        )
        if cur.rowcount and cur.rowcount > 0:
            log.warning("database: reopened %d request(s) into the new state machine", cur.rowcount)

    async def _backfill_post_versions(self) -> None:
        """Schema 49: every post that has no history gets version 1 from the row it is now."""
        cur = await self.conn.execute(
            BACKFILL_POST_VERSIONS, (datetime.now(UTC).isoformat(),)
        )
        if cur.rowcount and cur.rowcount > 0:
            log.info("database: gave %d post(s) a first saved version", cur.rowcount)

    async def _add_missing_columns(self) -> None:
        for table, column, declaration in ADDED_COLUMNS:
            present = await self._table_columns(table)
            if present and column not in present:
                await self.conn.execute(
                    f"ALTER TABLE {table} ADD COLUMN {column} {declaration}"
                )
                log.info("database: added %s.%s", table, column)
                backfill = BACKFILLS.get((table, column))
                if backfill is not None:
                    await self.conn.execute(backfill)

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None
