# Phase 15 — Ping roles (F14): the opt-in Events role + per-streamer fan roles

> ⚠️ **SUPERSEDED IN PART, 2026-09-03 — the slash surface below is gone.** `/golive` and
> `/twitch` and all eight of their subcommands (`logs`, `optout`, `optin`, `status`, `mode`,
> `test`, `link`, `unlink`) were replaced by ONE `/golive` command that opens an ephemeral
> panel; every subcommand is a button, a select or a modal on it. The behaviour this doc
> describes is unchanged — the announcer, the poller, the sessions, the settings and the log
> kinds are all exactly what it says. Only the way in moved:
> [`golive-panel-design.md`](golive-panel-design.md). This doc is NOT rewritten.

> **Audience:** the Opus builder first, reviewers second, the owner for the
> decisions table. **Status:** TRACKED — DESIGN, written 2026-09-02 by the Fable
> session from the owner's 2026-08-26 ask (F14 in `../TODO.md`) and the
> NEXT WAVE block ("the owner has already said go"). Secret NAMES only.
> Last verified: **2026-09-02** — every "what exists" claim below was read in
> the code today (`cogs/content/golive.py`, `golive.py:render`, `events.py:
> post_to_announce`, `cogs/community/role_menus.py`, `storage/db.py` schema 20,
> `settings_store.py`). ⚠️ NOT verified: anything against live Discord (no
> role has been created yet); the Discord select-menu cap (25 options) is the
> documented platform limit, not re-measured.

## The ask, verbatim

Owner, 2026-08-26: *"an opt-in **Events** role for go-live/event pings, and
**favourite-streamer roles** — per-streamer opt-in pings ('people that want to
see SuperNamu only … can get her pings'). Wire into F1/F5 announcements and
the role menus."*

## What already exists (do not rebuild)

| Piece | Where | Note |
|---|---|---|
| Global ping role per feed | `settings_store.py`: `golive_ping_role_id`, `events_ping_role_id` (`poll_ping_role_id` too) | `golive.py:render()` prefixes `<@&id> `; `cogs/content/golive.py:_mentions` builds the `AllowedMentions`; `events.py:mentions()`/`golive_text()` do the same for F5 |
| Role menus | `cogs/community/role_menus.py` — `/rolemenu create|add|remove|edit|post|unpost|assign|mode|seed-defaults`; tables `role_menus` (`mode` multiple/single/staff, `approval`, `expires_days`) + `role_menu_options` | Panels are a select; **Discord caps a select at 25 options** |
| Streamer identity | `golive_links (user_id, twitch_login, twitch_user_id)`; `/twitch link|unlink`; dashboard `linkCard` → `POST /api/golive/links` | The "who is a streamer" set = linked members (+ presence-detected ones, who are not linked) |
| Announcement path | `cogs/content/golive.py:_go_live_once` (one path for presence + Helix poll), `post_to_announce` for events | Opt-out, role filters and the cooldown all sit before the render |
| Feature-mode ladder | every feature has `<feature>_mode` off/shadow/on + `<feature>_log_level` | `info/cutover-plan.md` |

So F14 is **not** a new ping mechanism — it is (A) a one-shot setup that makes
the existing global role self-serve, and (B) a per-streamer role store wired
into the same render + mentions, with member-facing opt-in surfaces.

## Decisions (owner may flip any of these; each is a settings key)

| # | Question | Default chosen 2026-09-02 | Key |
|---|---|---|---|
| D1 | Who may create a streamer's fan role? | **`self`** — a linked streamer opts their own role in with `/pings fans on`; staff can always do it for anyone | `pings_fan_role_creation` = `self` / `staff` / `auto` (auto = created at `/twitch link` and at the dashboard link) |
| D2 | Fan-role name | **`{name} pings`** (display name at creation) | `pings_fan_role_template` |
| D3 | One Events role for both feeds, or two? | **One** — `/pingroles setup` creates "Events" and sets BOTH `golive_ping_role_id` and `events_ping_role_id`; the keys stay separate so the owner can split later on the Go-live / Events pages | `pings_events_role_name` = `Events` |
| D4 | What happens to a fan role on `/twitch unlink` or `/golive optout`? | **`keep`** the role, stop pinging (no announcement → no ping anyway) | `pings_fan_role_on_unlink` = `keep` / `delete` |
| D5 | Removing a fan role by staff: delete the Discord role too? | **yes** | `pings_fan_role_delete` bool |
| D6 | Feature mode | **`off`** at deploy (cutover ladder); the Fable session flips it `on` via the dashboard for the test sweep | `pings_mode` = `off` / `on` (no shadow — nothing here posts; role creation/assignment is the only member-affecting act and it is opt-in by the member) |
| D7 | Where members opt in | **all three**: `/pings follow` (autocomplete), the auto-maintained "Streamers" role-menu panels, and the Events role on a "Notifications" menu | — |

## A. The Events role (D3)

`/pingroles setup [role]` (staff group, hidden below manage_messages like the
other 24 staff groups):

1. If `role` is given, use it; else find a role named `pings_events_role_name`
   or create it (`mentionable=False`, no permissions, no colour, not hoisted).
2. Set `golive_ping_role_id` and `events_ping_role_id` to it (audit-logged via
   the store, Via: Discord).
3. Ensure a role menu named **`notifications`** (title "Notifications", mode
   `multiple`, no approval) exists and holds the role as an option (label
   "Events — go-live and event pings", emoji 🔔). Do NOT post the panel — the
   reply says "post it with `/rolemenu post notifications`" (in TEST_MODE that
   is refused outside the test channel; expected).
4. Reply in words with what was created / reused / already set.

Member side: pick it on the panel, or `/pings events on|off` (adds/removes the
role; refuses in words when `pings_mode` is off or the role is unset: "Staff
have not set up the Events role yet — ask an Auntie/Uncle to run
`/pingroles setup`").

Dashboard: Go-live page gains a **Pings** section (see E) with a "Set up the
Events role" button → `POST /api/pings/setup` (optional `role_id`).

## B. Fan roles per streamer

### Storage — schema **21**
```sql
CREATE TABLE IF NOT EXISTS golive_fan_roles (
    guild_id   INTEGER NOT NULL,
    user_id    INTEGER NOT NULL,      -- the streamer
    role_id    INTEGER NOT NULL,
    created_at TEXT    NOT NULL,
    created_by INTEGER,               -- who created it (streamer or staff), NULL = auto
    PRIMARY KEY (guild_id, user_id)
);
```
Additive only (`db.py` migration list + `SCHEMA_VERSION = 21` + the migration
test in `tests/storage/test_db.py`). A role deleted by hand in Discord: the
announcement path treats a missing role as "no fan role" and logs
`pings.fan_role_missing` once per session-start (not every announcement).

### Creation (D1) — one helper, three callers
`black_bloc/pings.py:ensure_fan_role(bot, guild, member, *, by, existing_role=None)`:
- refuses in words when `pings_mode` is off;
- reuses an existing row; else creates the Discord role from the template
  (`mentionable=False`, no perms; Discord places it at the bottom, below the
  bot's own role, so Manage Roles suffices), stores the row, logs
  `pings.fan_role_created`;
- then calls `sync_streamer_menus` (below).
Callers: `/pings fans on` (self — requires the caller to be linked OR to have
had a session announced; otherwise "link your Twitch first with
`/twitch link`"), `/pingroles streamer add <member> [role]` (staff, any mode),
`/twitch link` + `POST /api/golive/links` when `pings_fan_role_creation ==
auto`.
Removal: `/pings fans off` (self), `/pingroles streamer remove <member>`
(staff), `DELETE /api/pings/streamers/{member_id}`; D5 decides whether the
Discord role is deleted; the row always goes; `sync_streamer_menus` runs.

### Announcing — the only change to the go-live path
`golive.py:render(..., ping_role_id=..., fan_role_id=...)` prefixes both,
deduplicated, global first: `<@&events> <@&fan> REGULATORS! …`. `_mentions`
becomes `_mentions(guild_id, fan_role_id=None)` and lists both. `_go_live_once`
reads the fan role with one query after the cooldown check (so a suppressed
announcement never pings). The `details` dict logged gains `fan_role_id`. The
end-of-stream edit keeps its text and passes the same allowed-mentions (an edit
does not re-ping; the guard is there so a mention is never *added* by an edit).
**F5 event announcements are unchanged** — events are not per-streamer.

### Member opt-in surfaces (D7)
- `/pings follow <streamer>` / `/pings unfollow <streamer>` / `/pings list` —
  member-facing group (visible to everyone, like `/twitch`). Autocomplete lists
  fan roles by streamer display name. Adds/removes the role; refuses in words
  when the feature is off. `/pings list` shows what the caller follows + the
  Events role state.
- **Streamers panels**: role menus named `streamers`, `streamers-2`, … (title
  "Streamer pings", mode `multiple`), options = every fan role sorted by label,
  **25 per menu**. `pings.py:sync_streamer_menus(bot, guild)` rebuilds the
  option rows from `golive_fan_roles` after every create/remove and, when a
  menu's panel is posted (`message_id` set), refreshes it through the existing
  `rolemenu_panels` path (TEST_MODE refuses outside the test channel →
  `role_menu.would_post`, expected; KI-8 semantics apply unchanged). Empty
  trailing menus are deleted. Staff post them once with `/rolemenu post
  streamers`.
- Dashboard: the Pings section table (below).

### Guard rails
- Role changes go through `member.add_roles/remove_roles` with a reason
  "Black Bloc pings"; the guard (`guard.py`) does not gate role changes today
  (role menus already assign in TEST_MODE) — keep that, do not widen or
  narrow `guard.py`.
- Never `@` the streamer or members in any reply (`AllowedMentions.none()` on
  replies); the fan role is mentioned only inside the announcement.
- The Bots role must sit above the fan roles; new roles land at the bottom.
  If `add_roles` raises `Forbidden`, say so in words ("the bot's role is below
  this role — move it up in Server Settings ▸ Roles") and log `pings.forbidden`.

## C. Settings registry (every one on the Settings page + `/settings set-value`)

| Key | Type | Default | Help |
|---|---|---|---|
| `pings_mode` | mode (off/on) | `off` | the whole feature |
| `pings_log_level` | level | `important` | Discord log lines |
| `pings_events_role_name` | str | `Events` | name `/pingroles setup` creates |
| `pings_fan_role_creation` | choice self/staff/auto | `self` | D1 |
| `pings_fan_role_template` | str | `{name} pings` | D2; `{name}` only |
| `pings_fan_role_on_unlink` | choice keep/delete | `keep` | D4 |
| `pings_fan_role_delete` | bool | `true` | D5 |

Sync points (checklist item 33 + the exact-key-set tests): `settings_store.py`
KEY_TYPES / KEY_HELP / defaults, `site/public/assets/labels.js`,
`site/mock/server.mjs` key list, `tests/test_settings_store.py`, the Settings
page namespace list if it is enumerated anywhere in `site/`.

## D. Commands

| Group | Visibility | Commands |
|---|---|---|
| `/pingroles` (new, staff) | manage_messages default perms | `setup [role]`, `streamer add <member> [role]`, `streamer remove <member>`, `streamer list`, `logs` |
| `/pings` (new, member) | everyone | `follow <streamer>`, `unfollow <streamer>`, `list`, `events on\|off`, `fans on\|off` |

Both live in one cog `black_bloc/cogs/content/pings.py` (registered in
`bot.py:COGS`), helpers in `black_bloc/pings.py`. Command count goes 35 → 37
groups' worth — update the runbook boot line and `/help`. `/help` gets a
"Pings" entry.

## E. Dashboard + API (`api/tools/pings.py`, `page-golive.js` Pings section)

| Route | Does |
|---|---|
| `GET /api/pings/streamers` | rows: `member_id`, `member` (display name via the reference map), `role_id`, `role` (name), `followers` (role member count, `null` if the role is gone), `created_at`, `created_by` |
| `POST /api/pings/streamers` `{member_id, role_id?}` | staff create (D1 ignores mode for staff) |
| `DELETE /api/pings/streamers/{member_id}` | remove (D5) |
| `POST /api/pings/setup` `{role_id?}` | the Events role setup, same helper as the slash command |

Pings section on the Go-live page: the mode switch (`pings_mode`), the
existing `golive_ping_role_id` role field (already there as PING_KEY — do not
duplicate it; add the "Set up the Events role" button beside it), the streamer
table with a Remove button per row, a "Create for a streamer" card (member
picker + optional role), the `pings_*` settings namespace, and a Logs section
filtered to `pings.*`. Mock server + `contract.json` + `check.mjs` green.
Requests page rule stays: members see only Requests.

## F. Logs (`pings.*`, level `important` = acted on a member / failed)

`pings.setup`, `pings.events_on`, `pings.events_off`, `pings.fan_role_created`,
`pings.fan_role_removed`, `pings.follow`, `pings.unfollow`, `pings.forbidden`,
`pings.fan_role_missing`, `pings.would_*` when the feature is off (info level).
`golive.announce` details gain `fan_role_id`.

## G. Chat self-knowledge

`chat_data.py` / the FEATURES block: one line so "how do I get SuperNamu's
pings?" answers with `/pings follow` and the Streamer pings panel, and "how do
I get event pings?" with the Notifications panel / `/pings events on`.

## H. Tests (mirror the package)

`tests/test_pings.py`, `tests/cogs/content/test_pings.py`,
`tests/api/tools/test_pings.py`, `tests/storage/test_db.py` (schema 21),
`tests/test_golive.py` (render with both roles, dedup, none), `tests/cogs/
content/test_golive.py` (announce reads the fan role after the cooldown gate;
suppressed announcement never queries/pings), `tests/test_settings_store.py`
(exact key set), `tests/cogs/community/test_role_menus.py` if
`sync_streamer_menus` touches its helpers, `tests/test_bot.py` COGS count.
The 25-per-menu paging gets a test with 26 fan roles.

## I. Docs that land with the build

`code-notes.md` entries for every non-obvious line; `access/sweeps.md` rows
(setup, follow/unfollow, panel paging, announcement prefix, dashboard table);
`info/cutover-plan.md` ladder row for `pings_mode`; `info/feature-list.md` F14
row; `architecture.md` cog/table counts; runbook boot line (cog + command
counts); `TODO.md` F14 row → BUILT and the NEXT WAVE item 1 line moved whole to
`DONE.md` in the landing session (the Fable session does this, not the builder).
