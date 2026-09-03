# Phase 18 — Raid trains (member request #1)

> **Audience:** the Opus builder first, reviewers second, the owner for the
> decisions table. **Status:** TRACKED — DESIGN, written 2026-09-02 22:30 by
> the Fable session (NEXT WAVE item 6). Secret NAMES only.
> 🔨 **BUILT 2026-09-02** on branch `worktree-agent-a1c38e3df0f71fa7e` (off
> `820c393`) — not merged, not deployed, `raidtrain_mode` ships `off`. Read the
> `## Deviations` list at the foot before trusting the body of this doc.
> Last verified: **2026-09-02** — the "what exists" rows were read in the code
> today at `31b1689` (`storage/db.py` tables `events` / `golive_links` /
> `golive_sessions` / `user_timezones`, `cogs/community/events.py` surface,
> `cogs/content/golive.py:open_sessions`, `pings.py`). ⚠️ NOT verified: whether
> Phase 4's Scheduled-Event helper can be reused without editing `events.py`
> (§J — measure first). ⚠️ **Built IN PARALLEL with Phase 17** (owner,
> 2026-09-02 22:25: "Can we start doing some of this in parallel?") — see §K.

## The ask

Request #1 (Pawpette, staff, 2026-09-02 16:08): *"https://r3dlabs.com — raid
train site, want to see if the bot could do this instead since this site
requires twitch connection. We'd only need it for sign ups, slot availability,
and when the schedule is live it can DM someone 30 minutes before their slot
(if possible)!"* Owner: build (2026-09-02 20:10). The full r3dlabs inventory
and the ASKED/FIT/LATER/NO buckets are in
[`raid-train-capture.md`](raid-train-capture.md); this phase builds the
**ASKED + FIT** rows and nothing bucketed LATER/NO.

A raid train: a dated event split into consecutive slots (usually 1 h), one
streamer per slot; when a slot ends that streamer raids the next one, so the
audience travels down the lineup.

## What exists (reuse, do not rebuild)

| Piece | Where |
|---|---|
| Streamer identity without OAuth | `golive_links(user_id, twitch_login)` via `/twitch link` |
| Who is live right now | `cogs/content/golive.py:open_sessions(db, guild_id)` → `golive_sessions` rows with `ended_at IS NULL` |
| Per-user timezone for typed times, `<t:…>` rendering | `timezones.py`, `user_timezones`, `events.py:EventModal` (the `tz_name` pattern) |
| Poll-loop shape with `loop_health`, degraded-after-N, `before_loop` | `cogs/content/youtube.py` (the freshest copy), `golive.py:poller` |
| Guarded post + shadow `would_*` + TEST_MODE refusal | `cogs/content/youtube.py:_announce` / `events.py:post_to_announce` |
| DM path with refusal-in-words + `dm_failed` logging | `cogs/community/requests.py:dm / tell_requester` |
| Staff-group conventions, `/… logs`, `/… mode`, `/… setup` | every Phase ≥ 12 cog |
| Discord Scheduled Event creation | `events.py:_go_live` region — **§J decides whether it is reusable** |
| Page section + API + mock contract shape | `page-golive.js` YouTube section, `api/tools/youtube.py` |

## Decisions (defaults chosen 2026-09-02; each is a settings key — checklist 33)

| # | Question | Default | Key |
|---|---|---|---|
| D1 | Feature mode | **`off`** at deploy → shadow → on (cutover ladder) | `raidtrain_mode` off/shadow/on |
| D2 | Who organizes (create / assign / lock / cancel) | **staff** (the existing staff check) **or** holders of an organizer role when one is set | `raidtrain_organizer_role_id` role, blank |
| D3 | Slot length | **60 min**; per-train override at create | `raidtrain_slot_minutes` int ≥ 15 |
| D4 | Claiming needs `/twitch link` | **yes** — the lineup must carry the login the previous streamer raids; refusal names `/twitch link` | `raidtrain_require_link` bool `true` |
| D5 | Reminder lead time | **30 min** before the slot, by DM, once | `raidtrain_reminder_minutes` int ≥ 5 |
| D6 | Reminder poll cadence | **5 min** (floor 1) — the loop needs finer grain than the lead time | `raidtrain_poll_minutes` int |
| D7 | Where the lineup lives | a **lineup post** in `raidtrain_channel_id`, **edited in place** on every change; blank = the events announcement channel already in the registry | `raidtrain_channel_id` channel |
| D8 | Train chat | a **thread under the lineup post**, created with it (r3dlabs "event group chat") | `raidtrain_thread` bool `true` |
| D9 | Live check-in + "the train moves" post | when the slot holder has an open go-live session at/after `slot start − 15 min`: stamp `checked_in_at`, post "**{login}** is live — next up **{next}** at {t}" in the thread (or the lineup channel when D8 off) | `raidtrain_live_posts` bool `true` |
| D10 | Slots per member per train | **1** (0 = unlimited); organizer `assign` ignores the cap | `raidtrain_max_slots_per_member` int |
| D11 | Locking | organizer `lock`/`unlock` freezes member claims; **auto-lock at train start** (fixed, not a key) | — |
| D12 | Pings on the lineup post | **nobody**; a role when set | `raidtrain_ping_role_id` role, blank |
| D13 | Discord Scheduled Event for the train | **on** if §J finds the Phase 4 helper reusable without editing `events.py`; otherwise the key ships **`false`** and the report says so | `raidtrain_scheduled_event` bool |
| D14 | Logging | per-feature level like every cog | `raidtrain_log_level` level `important` |
| D15 | Time display | always Discord `<t:…:t>` / `<t:…:R>`; organizers type the start in their `/timezone` like `/event create` (no new tz machinery) | — |

## A. Storage — schema **24** (additive; 23 is Phase 17's — §K)

```sql
CREATE TABLE IF NOT EXISTS raid_trains (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id           INTEGER NOT NULL,
    organizer_id       INTEGER NOT NULL,
    title              TEXT    NOT NULL,
    description        TEXT,
    starts_at          TEXT    NOT NULL,           -- UTC ISO
    slot_minutes       INTEGER NOT NULL,
    slot_count         INTEGER NOT NULL,
    status             TEXT    NOT NULL DEFAULT 'open',   -- open | locked | live | done | cancelled
    channel_id         INTEGER,
    lineup_message_id  INTEGER,
    thread_id          INTEGER,
    scheduled_event_id INTEGER,
    created_at         TEXT    NOT NULL,
    updated_at         TEXT    NOT NULL
);
CREATE TABLE IF NOT EXISTS raid_slots (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    train_id       INTEGER NOT NULL,
    position       INTEGER NOT NULL,               -- 1-based, the raid order
    starts_at      TEXT    NOT NULL,
    ends_at        TEXT    NOT NULL,
    user_id        INTEGER,                        -- NULL = open
    twitch_login   TEXT,                           -- copied at claim time
    claimed_at     TEXT,
    assigned_by    INTEGER,                        -- organizer id when assigned, NULL when self-claimed
    locked         INTEGER NOT NULL DEFAULT 0,
    reminded_at    TEXT,
    checked_in_at  TEXT,
    live_posted_at TEXT,
    UNIQUE (train_id, position)
);
CREATE INDEX IF NOT EXISTS raid_slots_due ON raid_slots(starts_at, reminded_at);
```

Status moves: `open → locked` (organizer, or auto at start) `→ live` (poller at
`starts_at`) `→ done` (poller after the last slot ends); `cancelled` from
open/locked. One `TRANSITIONS` table, every path asks it (the Phase 17
requests pattern). Slots are created eagerly at `create` (`position` 1..N,
times derived), so `reorder` is a swap of two rows' `user_id`/`twitch_login`/
`claimed_at`/`assigned_by`, never a rewrite of times.

## B. `black_bloc/raidtrain.py` — pure helpers (testable without Discord)

- `slot_times(starts_at, slot_minutes, slot_count) -> list[(start, end)]`.
- `TRANSITIONS`, `may_move(status, to)`, `allowed_moves(status)` (words for refusals).
- `render_lineup(train, slots, *, ping_role_id) -> str`: title, `<t:start:F>`,
  one line per slot `#{pos} <t:…:t>–<t:…:t> — @user (twitch.tv/login)` or
  `— open`, "N/M filled", the lock/live state; `AllowedMentions` = the ping
  role only (members are written as `<@id>` inside `AllowedMentions.none()`
  for users — no member pings on edits).
- `reminder_text(slot, prev, next)`: the DM — your slot time, who raids INTO
  you (prev holder + login), who you raid NEXT (next holder + login), the
  lineup jump link.
- `due_reminders(now, lead_minutes, slots)`, `due_checkins(now, slots, open_sessions)`,
  `next_open_position(slots)`, `caps_ok(slots, user_id, max_per_member)`.
- `parse_start(text, tz_name)` — reuse `timezones.py` / the events modal parser;
  refuse in words on an unparseable or past time.

## C. `black_bloc/cogs/content/raidtrain.py` — the cog

- `tasks.loop(minutes=raidtrain_poll_minutes)` (re-read via `change_interval`),
  `loop_health`, `before_loop` waits ready. Each tick, per guild: promote
  `open/locked → live` at start (auto-lock first), `live → done` after the last
  slot; send due reminders (stamp `reminded_at` BEFORE sending — a crash loses
  one DM, never doubles it); D9 check-ins from `golive.open_sessions`; re-render
  the lineup post when anything changed.
- Mode: `off` → the loop idles and every command refuses in words ("raid trains
  are off — staff turn them on with `/raidtrains mode`"); `shadow` →
  `raidtrain.would_remind` / `raidtrain.would_post` with the text, nothing sent;
  `on` → DM + posts through the guard (`guard_allows`; a refused channel logs
  `raidtrain.post_skipped_test_mode`, never raises; DMs are allowed in TEST_MODE).
- Member group **`/raidtrain`** (visible to all): `list` (upcoming trains, N/M
  filled), `status <train>` (the lineup embed, ephemeral), `claim <train>
  [slot]` (default = next open; D4/D10 checks; refusals in words),
  `release <train>`, `mine` (my slots across trains with `<t:…:R>`).
  `train` and `slot` use autocomplete (title / "#3 21:00 open").
- Organizer subcommands on the same group, gated by D2 (`_organizer(interaction)`):
  `create` (modal: title, description, start, slot length, slot count — the
  events modal shape; posts the lineup, opens the thread, D13 event),
  `assign <train> <slot> <member>`, `unassign <train> <slot>`, `swap <train>
  <slot_a> <slot_b>`, `lock <train>` / `unlock <train>`, `cancel <train>
  <reason>` (edits the lineup post to say cancelled, DMs every holder).
- Staff group **`/raidtrains`** (manage_messages default perms): `mode`,
  `setup [channel] [organizer_role] [ping_role]`, `logs`.
- Registered in `bot.py:COGS` (**append at the end**), `/help` entry,
  `chat_data.py` FEATURES line ("how do I join the raid train? → `/raidtrain
  claim`").

## D. Settings registry (+ labels.js, mock key list, exact-key-set test)

| Key | Type | Default |
|---|---|---|
| `raidtrain_mode` | mode | `off` |
| `raidtrain_log_level` | level | `important` |
| `raidtrain_organizer_role_id` | role | blank |
| `raidtrain_channel_id` | channel | blank (= events announcement channel) |
| `raidtrain_ping_role_id` | role | blank |
| `raidtrain_slot_minutes` | int (≥15) | `60` |
| `raidtrain_reminder_minutes` | int (≥5) | `30` |
| `raidtrain_poll_minutes` | int (≥1) | `5` |
| `raidtrain_require_link` | bool | `true` |
| `raidtrain_thread` | bool | `true` |
| `raidtrain_live_posts` | bool | `true` |
| `raidtrain_max_slots_per_member` | int (≥0) | `1` |
| `raidtrain_scheduled_event` | bool | per §J |

No new config/env. No secrets.

## E. Dashboard + API

`api/tools/raidtrain.py`: `GET /api/raidtrains?scope=upcoming|past|all`,
`GET /api/raidtrains/{id}` (train + slots with member names/logins),
`POST /api/raidtrains` (organizer create — same fields as the modal, start as
ISO + tz), `POST /api/raidtrains/{id}/slots/{pos}` `{member_id|null}`
(assign / unassign), `POST /api/raidtrains/{id}/swap {a, b}`,
`POST /api/raidtrains/{id}/status {status, reason?}` (lock/unlock/cancel — asks
`TRANSITIONS`, refuses in words), `GET /api/raidtrains/status` (loop health,
mode, counts). **A Raid trains section on the Events page** (`events.html` +
`page-events.js` — the Schedule page owns "what is scheduled"; do NOT add a
page): mode switch, `raidtrain_*` settings namespace, upcoming trains table →
a train detail with the slot grid (claim/assign/unassign/swap for staff), Logs
filtered to `raidtrain.*`. `contract.json` + `server.mjs` fixtures + `check.mjs`
green; Health tab loop row in the parametrised `tests/api/test_status.py`.

## F. Logs (`raidtrain.*`)

`raidtrain.create`, `.claim`, `.release`, `.assign`, `.unassign`, `.swap`,
`.lock`, `.unlock`, `.live` (status move), `.done`, `.cancel`, `.remind`,
`.would_remind`, `.dm_failed`, `.checkin`, `.post` , `.would_post`,
`.post_skipped_test_mode`, `.post_failed`, `.poll_degraded`. Important =
anything sent to a member or failed; claims/releases routine.

## G. Tests (mirror)

`tests/test_raidtrain.py` (slot times, transitions, render, reminder text,
due_* selection incl. the "stamp before send" order, caps), `tests/cogs/
content/test_raidtrain.py` (claim needs link, cap, lock refuses, auto-lock at
start, shadow vs on, TEST_MODE refusal, reminder once, check-in from an open
session, cancel DMs holders), `tests/api/tools/test_raidtrain.py`,
`tests/storage/test_db.py` (schema 24), `tests/test_settings_store.py`,
`tests/test_bot.py` (COGS), `tests/api/test_status.py`.

## H. Docs landing with the build

`code-notes.md` (`# Phase 18` section), `access/sweeps.md` rows,
`cutover-plan.md` ladder row, `feature-list.md` new row **F19 raid trains**,
`architecture.md` counts, `info/README.md` row. Not `TODO.md`/`DONE.md`.

## I. Residuals to record in `KNOWN_ISSUES.md` at landing

- A member who unlinks Twitch after claiming keeps the slot with the copied
  login; the lineup may name a login that no longer streams. What would change
  it: 1 report.
- Check-in (D9) sees only what go-live sees — a holder whose presence is hidden
  and who is not Twitch-linked is never marked live. Accepted; same limit as F1.

## J. First task for the builder — measure, don't assume

Read `events.py:_go_live` and whatever it calls to create the Discord
Scheduled Event. **If** that helper is callable from a new cog without editing
`events.py` (a module-level function, or a method on the loaded `Events` cog
reachable via `bot.get_cog`), D13 ships `true` and the train creates one.
**If not**, do NOT edit `events.py` (it is not yours in a parallel build) —
D13 ships `false`, the key still exists, and the report + `## Deviations`
says exactly why. Record the finding in `code-notes.md`.

## K. Parallel-build rules (Phase 17 is building at the same time)

Branch off `main` at `31b1689` (Phase 16 is in; Phase 17 is NOT). Merge order
is **17 then 18**; the reviewer resolves the merge, so make it trivial:

- **Shared files are APPEND-ONLY at the foot:** `storage/db.py` (add the
  schema-24 block after the existing last migration; write it so it runs
  correctly whether or not 23's tables exist — it touches only its own two
  tables), `settings_store.py` registry (append the `raidtrain_*` block last),
  `logkinds.py`, `bot.py:COGS`, `labels.js`, `contract.json`, `server.mjs`
  fixtures, the exact-key-set test list, `chat_data.py` FEATURES, `/help`.
- `SCHEMA_VERSION` becomes **24** in your branch; the migration ladder must
  step 22→23 (an empty step in YOUR branch — Phase 17 fills it) →24, so the
  reviewer's merge only drops your empty 23 step.
- **Do not touch** anything Phase 17 owns: `chat*.py`, `chat_memory*`,
  `cogs/content/chat.py`, `requests.py`, `cogs/community/requests.py`,
  `api/tools/requests.py`, `page-chat.js`, `page-requests.js`, `chat.html`,
  `requests.html`, `phase17-design.md`, `requests-states-design.md`.
- `golive.py` / `events.py` / `pings.py` are READ-ONLY for you (import, call,
  never edit) — see §J.
- Commit at clean boundaries: schema+helpers → cog → API+page → docs.

## Deviations — what the build did differently, and why

Written by the Opus builder at landing, 2026-09-02, on branch
`worktree-agent-a1c38e3df0f71fa7e`. Every item below is a place the shipped code
does NOT match the spec above; the spec is left as written so the two can be
compared.

1. **§J / D13 — `raidtrain_scheduled_event` ships `false`, but the key is not a
   dead switch.** §J's condition ("callable from a new cog without editing
   `events.py`") is technically met — `create_scheduled_event` is module-level —
   and the design's answer is still `false`, because calling it would run
   `UPDATE events SET scheduled_event_id = ? WHERE id = ?` with a **raid train's**
   id and corrupt an unrelated `events` row. Rather than leave a key that does
   nothing when flipped, the cog got its own twenty-line
   `_maybe_scheduled_event` (raid-train log kinds, no writes outside
   `raid_trains`). `find_scheduled_event` — pure, no table — IS imported from
   `events.py` for the cancel path. `events.py` was NOT edited. Full reasoning in
   `code-notes.md` § *Phase 18 — What section J actually measured*.
2. **§A — two columns and two indexes differ.** `raid_trains` gained
   `cancel_reason TEXT` (the design's cancel flow needs somewhere to keep the
   reason the lineup post and the DMs both quote) and a
   `raid_trains_by_status(guild_id, status, starts_at)` index; `raid_slots`
   gained `raid_slots_by_member(user_id, starts_at)` for `/raidtrain mine`, and
   a `REFERENCES raid_trains(id) ON DELETE CASCADE`. ⚠️ **No unique index on
   `(train_id, user_id)`** — the per-member ceiling is a SETTING that may be 0
   (unlimited), and a schema cannot encode a value the owner may change. The
   race is guarded by an `asyncio.Lock` per train plus
   `UPDATE … WHERE id = ? AND user_id IS NULL` (checklist 6).
3. **§K — there is no numbered migration ladder to step through.**
   `storage/db.py` has no 22→23→24 steps: it is one idempotent `SCHEMA` script of
   `CREATE TABLE IF NOT EXISTS` plus an `ADDED_COLUMNS` list. So "an empty 23
   step" does not exist as a construct. What shipped is the append §K actually
   wanted: the two tables at the FOOT of `SCHEMA` and `SCHEMA_VERSION = 24`. The
   merge is a one-line resolution on `SCHEMA_VERSION`; nothing else conflicts.
   ⚠️ `tests/storage/test_db.py` had three hard-coded `"22"` assertions, which
   were changed to `str(SCHEMA_VERSION)` so the same trap does not fire on
   Phase 17's bump.
4. **§C — the `/help` line lives in `personas.py`, not `chat_data.py`.** The
   brief named `chat_data.py`; the member-command block a model reads is
   `personas.py:FEATURES`, and `chat_data.py` is a `chat*.py` file Phase 17 owns
   as read-only. `personas.py` was appended to instead.
   `tests/test_personas.py` asserts every member command appears there, so the
   omission would have failed the suite either way. `/help` itself needed no
   edit — `cogs/core.py` walks the command tree.
5. **§C — `reorder` is spelled `swap`.** §A describes a swap of two rows and the
   command list says `swap <train> <slot_a> <slot_b>`; the prose elsewhere says
   "reorders". Only `swap` exists.
6. **§B — `parse_start` is not re-declared in `raidtrain.py`.** The cog calls
   `timezones.parse_start` and `events.start_error` /
   `events.START_IN_THE_PAST` directly, so there is one home for the date
   sentences (checklist 15) rather than a second copy in a new module.
7. **§B — `due_reminders` grew a sibling, `missed_reminders`.** The design has
   one function; ageing a passed slot out (checklist 31) is a different ACTION
   from sending, so it is a different function. The cog stamps the missed ones
   without DMing.
8. **§C — `SLOT_COUNT_MAX = 24`, which the design did not name.** A lineup must
   fit in ONE message because it is edited in place; ~85 characters a line
   against Discord's 2000 gives 24. `create` refuses a bigger train in words and
   says why. r3dlabs allows 50.
9. **§E — the dashboard has no organizer "claim" control.** Claiming is a
   member action and the dashboard is staff-only, so the page carries assign /
   unassign / swap / lock / unlock / cancel / create, and `claim` is Discord-only.
10. **§F — three log kinds beyond the list**, all from the D13 creator that §J
    did not expect to exist: `raidtrain.would_create_scheduled`,
    `raidtrain.create_scheduled_failed`, `raidtrain.cancel_scheduled_failed`.
    The `would_`/`_failed` shapes mean `logkinds.py` classifies them without a
    new entry.
11. **Not verified.** Nothing in this phase has run against live Discord: no
    lineup posted, no thread opened, no reminder DM delivered, no scheduled event
    created, no member has claimed an hour. The Events page section WAS opened in
    a real browser against the mock (section, counts, settings namespace, logs
    section, create form — no console errors); the **train-detail slot grid was
    not** clicked through in the browser, because another agent took the shared
    Chrome tab mid-check — it is covered by `check.mjs` and the API tests only.
