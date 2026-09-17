# Architecture

> **Audience:** Claude sessions and the owner. **Status:** TRACKED (owner, 2026-08-31 — was
> local-only until then).
> Last verified: **2026-09-16 09:10** — the fact table only, at the GUIDES landing (v111): schema **35**, keys **212** (from the v111 gate and the G1 report), features **19**, groups **24**, mock **18 pages / 160 routes**, tests **5703**, deploys **108**; new modules `black_bloc/guides.py`, `api/tools/guides.py`, `site/public/guides.html` + `assets/page-guides.js`, `scripts/release_json.py` — the Shape tree below was NOT redrawn for them. Before that, **2026-09-11 08:30** — docs-wide staleness pass on `main` at `1d090e5`. **Re-measured by import/command in a worktree of `main`:** cogs **19** (`len(bot.COGS)`), schema **34** (`db.SCHEMA_VERSION`), registry keys **202** (`len(settings_store.KEY_TYPES)`), features **18** (`settings_store.FEATURES == logkinds.FEATURES`), setting groups **23**, deploys **107** lines last `73e2e44` v108. **Read off disk:** `black_bloc/api/`, `black_bloc/api/tools/`, `black_bloc/cogs/**`, `site/public/*.html` (17). What that FIXED: the v92 fact table (keys 189 → **202**; schema "34 on `where-picker`, 33 on `main`" → **34 on `main`**; mock 149 → **150** routes; deploys 91/v92 → **107**/v108), the `storage/db.py` tree annotation (`SCHEMA_VERSION 22` → **34**), and three cogs + three `api/tools/` routers + three `api/` modules the Shape tree did not name. ⚠️ **NOT checked:** the prose below the tree (rules, library table, API section) still not re-traced to the code; the tree's per-file annotations beyond the ones named here; the mock line was taken from the v108 gate on `deploys.log`, not re-run; nothing here met Discord, and no browser rendered anything. Before that, **2026-09-11 00:38** (the follow-up 4 paragraph: ✅ LIVE v108 00:37, merge `73e2e44` — keys measured by the live `/api/settings` — **202**; tests and the mock line from the v108 gate — **5546** passed, *17 pages, 150 routes, 14 core settings, all keys present*; the link check itself probed live at the review; nothing here met Discord; nothing else re-measured) — earlier **2026-09-10 23:45** (the follow-ups 2+3 paragraph: keys measured by the live `/api/settings` — 199; tests and the mock line from the v107 gate — 5502 passed, 17 pages / 150 routes; nothing else re-measured) — earlier **2026-09-10 17:45** (the Where follow-up paragraph: keys and schema measured by import on the branch, tests and the mock line from the v106 gate — 5473 passed, 198 keys answered by the live `/api/settings`; nothing else re-measured) — earlier **2026-09-10 16:40** (the raid-train calendar-name paragraph: keys measured by import, tests and mock routes from the gate; nothing else re-measured) — earlier **2026-09-10 16:02** (the v100 paragraph: keys and schema measured by import, tests from the gate; nothing else re-measured) — earlier **2026-09-05**: every figure below re-MEASURED on the ENGINEERING SWEEP 3
> branch off `main` at `6af0ba0` (v92) by running the thing, not by reading a doc: the tree is
> built the way `tests/test_bot.py` builds it (load all `bot.py:COGS`, then `tree.get_commands()`),
> `SCHEMA_VERSION` is imported from `black_bloc/storage/db.py`, and the site figures come from
> `node site/mock/check.mjs` against `site/mock/server.mjs`.
>
> **2026-09-11 (Event rooms — the event's posts live in its own room and staff get a Delete button, branch `event-rooms` off `bd0b31d`; ⚠️ BUILT, NOT MERGED, NOT DEPLOYED, nothing has met Discord):**
> schema **unchanged at 34** — no migration and no backfill; registry keys **202 → 206** (`events_posts_where` enum room/announce/both default **room**, `events_room_delete_who` enum staff/approver default **staff**, `events_approver_role_id` role blank→staff, `events_room_notice` bool **true** — all events group by prefix); mock routes **150 → 151** (`POST /api/events/{event_id}/room/delete`). ⚠️ **No new module.** `make_review_channel` now calls `guard.own_channel`, which is the whole reason the posts move: the room joins the guard's owned set, so `card_channel` stops redirecting the review card to the test channel and the new `events.post_to_room` may speak there — `TEST_MODE` itself is untouched and still refuses every channel Black Bloc did not make. `events.post_event` fans the announce and go-live posts out over the two doors, and the room additionally gets the ended, cancelled and denied lines; only the announce channel's message id is stored (the room is deleted with the event). `events.delete_room` is the one canonical removal, reached from the persistent **Delete this room** button (`DECISION_TEMPLATE` grew a third action) and from the website route with `via=VIA_WEBSITE`; it cancels an open event FIRST so `on_guild_channel_delete` cannot settle it twice, and it cannot hold `event_lock` because `cancel_event` takes that same non-reentrant lock. Reconcile re-owns every room it can still see and `forget_room` clears a swept row's dead `review_channel_id` once (`event.room_forgotten`, TODO finding (h)). Five new log kinds by shape (`event.*_room`, `event.would_*_room`, `event.*_room_failed`) plus `event.room_forgotten`, `event.room_notice_failed`, `event.room_delete_failed`; tests **5546 → 5593**. Before that:
>
> **2026-09-11 (Where follow-up 4 — a shorthand becomes a link and the link is tried first, ✅ LIVE v108 00:37, merge `73e2e44` of `where-smart`):**
> schema **unchanged at 34** — no migration and no backfill; registry keys **199 → 202** (`events_where_link_aliases` text with a `where_alias_table` checker, `events_where_link_check` enum off/warn/refuse default **warn**, `events_where_link_check_seconds` int 1–3 default **2** — all events group by prefix); mock routes unchanged at **150**; ⚠️ **one new module, `black_bloc/linkcheck.py`** — the first outbound HTTP in the events path, `LINK_OK` / `LINK_MISSING` / `LINK_UNREACHABLE` from one GET with a browser UA, redirects followed and the body never read, with `fetch` injected the `groq.py` way so no test reaches the network. `events.where_link` also learns bare hosts (render-time, so rows stored before this build become links with no migration) and the new `events.where_typed` turns `ttv/skyaiva` / `yt @skyaiva` into the href at ENTRY, in `WhereModal.on_submit` and in the website's `checked_where`. `EventDraft.where_note` carries a warn-mode note on the draft's Where line only — never on the row, the card or the announcement; no new log kind (the check logs at `debug`); tests **5502 → 5546**. Before that:

> **2026-09-10 (Where follow-ups 2+3 — a typed link looks like a link, test rooms go in minutes, branch `where-links` off `8adbc75`, merged `ac43a20`, ✅ LIVE v107 23:41):**
> schema **unchanged at 34** — no migration; registry keys **198 → 199** (`events_test_retention_minutes`, int, events group by prefix, default 5, 1–1440; read only while `bot.guard is not None`); mock routes unchanged at **150**; no new module and no new log kind — `events.where_link` / `where_shown` / `where_line(linked=)` render a typed http(s) location as a masked link on the draft and the card, `cogs/community/events.add_open_link` adds a `ButtonStyle.link` **Open link** button to the review card only (the draft never gets it: Submit takes the row's fifth slot), `knowledge.event_where` and the scheduled event's description keep the bare url, and `events.swept_anchor` counts a DENIED / CANCELLED room from `decided_at` (then `ends_at`, then `created_at`); tests **5473 → 5502**. Before that:
> **2026-09-10 (the Where follow-up — a channel AND a link, branch `where-link` off `ebe0ead`, merged `6c10b9d`, ✅ LIVE v106 17:41):**
> schema **unchanged at 34** (measured: `SCHEMA_VERSION`) — no migration and no backfill, because `location`
> already existed and simply now carries the typed link for the two channel kinds as well as the place for
> `other`; registry keys **197 → 198** (measured: `len(KEY_TYPES)` — `events_where_link_in_description`, a bool
> filed in the `events` group by prefix, so **23** groups still); mock routes unchanged at **150** (checked:
> *17 pages, 150 routes, 14 core settings, all keys present*); no new module and no new log kind — the append
> is `events.described_with_where`, read once inside `create_scheduled_event`; tests **5453 → 5473**. Before
> that:
> **2026-09-10 (the "Where?" picker, merge `3205c0f`, v105 17:09):**
> schema **33 → 34** (measured: `SCHEMA_VERSION`) — `events` gains `where_kind TEXT` and
> `where_channel_id INTEGER`, both nullable, both `ALTER TABLE` entries in `ADDED_COLUMNS`, no backfill
> (a row with a `location` and no kind already reads as the `other` kind); registry keys **unchanged** —
> the design says there is nothing to decide, so no group count moved either; mock routes unchanged at
> **150**; no new module (the `Where` type and its readers live in `black_bloc/events.py`, the panel in
> `cogs/community/events.py`); one new log kind `event.where_channel_gone`; tests **5403 → 5453**. Before that:
> **2026-09-10 (the raid train's calendar name, branch `raidtrain-name`):** schema unchanged at **33**;
> registry keys **196 → 197** (measured: `len(KEY_TYPES)` — `raidtrain_scheduled_name_template`, filed in the
> `raidtrain` group by prefix, so **23** groups still); mock routes unchanged at **150**; no new module —
> `events.scheduled_name` grew a `fallback=` keyword so raid trains fall back to the plain title rather than
> to the events wording; tests **5395 → 5403**. Before that:
> **2026-09-10 (the "When?" picker `1f35f28`, v100):** schema unchanged at **33** (measured: `SCHEMA_VERSION`); registry
> keys **191 → 196** (measured: `len(KEY_TYPES)` — `default_timezone`, `timezone_choices`, `time_step_minutes`,
> `events_default_minutes`, `events_scheduled_name_template`, all filed in the `events` group by `NAMESPACE_OVERRIDE`,
> so **23** groups still); mock routes unchanged at **150**; new leaf module `black_bloc/when_picker.py` (the shared
> Day/Hour/Minute/Duration selects, `WhenDraft`, `ZonePanel`), used by `cogs/community/events.py` and
> `cogs/content/raidtrain.py`; `EventModal`, `TrainModal`, `Events.submit` gone; tests **5286 → 5395**. Before that:
> **2026-09-06 (loop guard `689eff5`, v97; operator bucket `deaae68`, v98; operator read bound `88e0242`, v99):**
> schema unchanged at **33**; registry keys unchanged at **191**; mock routes unchanged at **150**; new leaf module
> `black_bloc/loops.py` (`wait_ready`, called by all fourteen `before_loop`s); `auth.py:operator_session` reorders
> compare-then-bucket (v98) and then charges the shared 300/min read bucket on the operator identity (v99) — the
> read-bucket names and `_bucket` now live in `auth.py`, `writes.py` re-exports them; tests **5267 → 5277 → 5279 →
> 5286**; `tests/live/` green against v98 and v99 (58 passed / 1 skipped — the count lives in
> `../access/testing.md`, which owns it). Before that:
> **2026-09-06 (logs buttons `42d2e6e` + recurrence create from the website `c915ade`, v96):** schema unchanged at **33**; registry keys **189 → 191** (`logs_count`, `logs_important_only` — a new `logs` group, **23** groups); mock routes **149 → 150** (`POST /api/polls/recurrences`); new module `black_bloc/logs_panel.py`; tests **5226 → 5267**. Before that:
> **2026-09-06 (saved poll drafts, merged `8405bea`, v94):** schema **32 → 33** (`poll_drafts`)
> and registry keys **187 → 189** (`poll_drafts`, `poll_draft_days`), both re-measured by
> importing them. Nothing else in this table moved — no cog, no command, no feature, and the
> mock still reads 17 pages / 149 routes / 14 core settings.
>
> | What | v115 (`main`, 2026-09-16) | Where it is measured |
> |---|---|---|
> | Cogs | **20** (v113: `cogs/community/posts.py`) | `bot.py:COGS` |
> | Top-level slash commands | **30** — 15 staff-locked, 15 member-visible (`/modmail` became member-visible at v114) | `tree.get_commands()` |
> | `app_commands.Group`s | **0** | ⚠️ every group retired by the panel waves |
> | Schema version | **38** (v114, modmail doors: `modmail_tickets.source`, `opened_by`) | `storage/db.py:SCHEMA_VERSION` |
> | Registry keys | **220** (was 215 at v113) — **25 namespaces, the `/settings` select's cap** | `settings_store.KEY_TYPES` |
> | Setting groups | **25** — the `/settings` group select's cap; the next namespace needs a `Find…` path | `settings_store.namespace_of` over `KEY_TYPES` |
> | Features (log-level keys) | **20** (guides v111, posts v113) | `settings_store.FEATURES` == `logkinds.FEATURES` |
> | Mock contract | **19 pages / 171 routes / 14 core settings** (17/150 at v108; was 149 routes at v92) | `node site/mock/check.mjs` — figure read off the v108 gate line in `../deploys.log`, not re-run 2026-09-11 |
> | Tests | **5889** | the v115 deploy gate |
> | Deploys | **112**, last `64b69ce` (v115) at 2026-09-16 19:15 | `../deploys.log` |
>
> ⚠️ **The command count is the figure that has been wrong most often, and the reason is that
> it FELL.** The panel waves (owner rule, 2026-09-03: one command per feature opens a panel)
> retired every `app_commands.Group` and every sub-command with it, so a doc quoting a
> pre-panel figure reads as *more* commands than exist. The only trustworthy number is
> `tests/test_bot.py:TOP_LEVEL_NOW`, which the suite asserts on every run.
>
> **How the counts moved** — one row per reading, so a stale figure is visible as history
> rather than as a competing claim. Everything before v92 was measured on the branch named,
> not on `main`:
>
> | Reading | Cogs | Commands | Schema | Routes | Tests |
> |---|---|---|---|---|---|
> | Phase 16 branch | 16 | 39 | 22 | 116 | 2865 |
> | Phase 18 branch | 17 | 41 | 24 | 123 | — |
> | Phase 19 branch | 17 | 41 | 25 | 126 | — |
> | 17→18→19 on `main`, 2026-09-03 | 19 | 44 | 25 | 136 | 3238 |
> | Phase 15 (F14) branch, 2026-09-02 | 15 | 37 | 21 | 111 | 2714 |
> | v92 `6af0ba0`, 2026-09-05 | 19 | 29 | 32 | 149 | 5186 |
> | **v115 `64b69ce`, 2026-09-16** | **20** | **30** | **38** | **171** | **5889** |
> | **v114 `c279676`, 2026-09-16** | **20** | **30** | **38** | **170** | **5880** |
> | **v113 `4d60f68`, 2026-09-16** | **20** | **30** | **37** | **168** | **5833** |
> | **v111 `67aee7e`, 2026-09-16** | **19** | **29** | **35** | **160** | **5703** |
> | **v108 `73e2e44`, 2026-09-11** | **19** | **29** | **34** | **150** | **5546** |
>
> ⚠️ **NOT verified today:** the *prose* below the tree (the rules, the library table, the API
> section) was not re-traced to the code; the Shape tree's per-file annotations (last verified
> 2026-08-31); and nothing here was checked against the running bot or a browser. What is
> shipped but never exercised by a person is tracked per feature in
> [`../access/sweeps.md`](../access/sweeps.md) — that file is the one home for "shipped but
> never clicked", and this header must not grow a second copy.
>
> 📦 **The five stacked per-branch paragraphs this header used to carry, and the historical
> build-order narrative under them, are archived whole at
> [`../archive/architecture-header-2026-09-05.md`](../archive/architecture-header-2026-09-05.md)**
> with a retirement banner. They contradicted each other and the repo; the table above is what
> replaced them.

## Shape

```
black_bloc/
├── app.py            ← THE RUN BUTTON. Settings → logging → bot → run. Nothing else, ever.
├── errors.py         ← exit-code policy (2 config, 3 login/intents) + the asyncio run loop
├── bot.py            ← BlackBlocBot lifecycle ONLY: __init__, setup_hook, close, on_ready + COGS
├── intents.py        ← build_intents(): the three privileged intents
├── invite.py         ← INVITE_PERMISSIONS + invite_url(bot)
├── command_sync.py   ← sync_dev_guild(): dev-guild slash-command sync, 403 handling
├── command_errors.py ← the tree error handler: any unhandled slash-command failure answers with a sentence
├── guard.py          ← TestModeGuard: the TEST_MODE gate (send + edit HTTP layer, interaction_check)
├── config.py         ← Settings (pydantic-settings). THE ONLY reader of the environment / .env
├── settings_store.py ← per-guild settings on SQLite + the staff check. The ONLY way features read config
├── actionlog.py      ← log_action(): one DB row always, one embed to the log channel when it can
├── twitch.py         ← Helix client: app token, get_streams, get_users. HTTP is injectable, so tests are offline
├── golive.py         ← pure go-live logic: extract_stream, render, should_announce, role filters
├── timezones.py      ← per-member zone store, the autocomplete filter, HammerTime stamps
├── events.py         ← pure event logic: slugs, durations, the status machine, the one card
├── birthdays.py      ← pure birthday logic: local midnight, ages, the colour, the import matcher
├── modmail.py        ← pure modmail logic: the topic, the three embeds, the transcript, the byte-safe cut
├── automod.py        ← pure rule engine: the rule book, the windows, the verdict
├── modcases.py       ← the shared mod-case store: the row, the one card, the DM policy, the modlog post
├── presence.py       ← the bot's own face: the About Me (application description) and the
│                       "Cookout attendees: N" custom status. Pure formatters + two appliers
├── polls.py          ← F15: pure poll logic — kinds, date slots, the close/reminder clock, results
├── requests.py       ← F18: pure request logic — the status machine, auto-approval, the card
├── chat.py           ← F10: @-mention intent classification and the reply, one seam: reply_for()
├── chat_data.py      ← the data intents behind chat (live / next / birthdays / count / roles / tz)
├── pings.py          ← F14: the opt-in ping roles — the fan-role store, the Events-role set-up,
│                       the 25-per-menu Streamer pings panels, and the one role add/remove wrapper
├── rolegrants.py     ← F16/Phase 9: time-limited role grants and the expiry/reconcile logic
├── rolemenu_panels.py ← posting and un-posting role-menu panels when rolemenu_mode flips
├── command_visibility.py ← hides a feature's slash commands while the feature is off (re-syncs)
├── logkinds.py       ← ⚠️ THE ONE HOME for log-kind classification: important vs routine, and
│                       `via_of()` (Discord vs website) which stamps every action-log row
├── emoji.py          ← skin-tone application for the bot's own emoji (emoji_skin_tone)
├── prefix.py         ← no_prefix_commands: the bot answers no text prefix (slash only)
├── panels.py         ← ⚠️ THE PANEL LIBRARY every feature's one command opens (wave 0 of the
│                       panels program): Panel, retire, answer, still_staff, still_allowed,
│                       db_ready, capped_placeholder, panel_minutes, confirm, opened, KEEP_IT,
│                       NoteModal. A panel that re-implements one of these is the bug
├── logs_panel.py     ← the Logs button's list + its Show more / Important only knobs
├── settings_panel.py ← the pure half of /settings: the groups, the typed key cards, the editors
├── selftest.py       ← the self-test registry (config · panel · read · send) and run()/purge
├── selftest_panels.py ← the Discord half of the self-test: the panel and its cards
├── when_picker.py    ← the shared Day/Hour/Minute/How-long selects, WhenDraft, ZonePanel
├── linkcheck.py      ← ⚠️ the ONLY outbound HTTP in the events path: one bounded GET that tries
│                       a typed link before it is kept (LINK_OK / MISSING / UNREACHABLE)
├── loops.py          ← wait_ready, behind all fourteen before_loops so a failure reaches @loop.error
├── applications.py   ← Phase 19: pure application logic — the forms, the statuses, the roster
├── raidtrain.py      ← Phase 18: pure train logic — slots, claims, the lineup, the reminder clock
├── rolemenus.py      ← F16: pure role-menu logic, shared by the cog and the website
├── honeypot.py       ← F9: pure trap logic (built at the /honeypot panel; neither existed before)
├── tempvoice.py      ← F8: the temp-voice state machine and the owner control-post button table
├── chat_memory.py    ← Phase 17: the profile store and the opt-out list
├── chat_distil.py    ← Phase 17: the hourly distillation — never on the reply path
├── chat_check.py     ← the chat door: cooldown, mode, manners, the spend fuses
├── chat_panel.py     ← the pure half of /chat: Personality, Knowledge, Settings
├── chat_llm.py       ← the model ladder and the spend ledger (microdollars, month_start)
├── llm.py / groq.py  ← the two clients. HTTP injectable, so no test reaches the network
├── knowledge.py      ← GABI-style knowledge ingestion + lexical search behind chat
├── personas.py       ← the voice stack: roster, graph, drift constants, the shared clauses,
│                       fed by personality_pool.json (synced from catalog-platform)
├── directory.py      ← the channel directory the chat prompt gets: the visible-channel list,
│                       the hidden/archive categories, and the "name no channel at all" fallback
├── dbsnapshot.py     ← a consistent snapshot of the live database, for the nightly backup pull
├── personality_pool.json ← the SKELETON shared with GABI (see personality-pool-design.md)
├── data/             ← shipped package data (`pyproject.toml` → package-data)
│   └── birthday_import_2026-08-05.json  ← the 39-row Birthday Bot export, seed for the daily import loop
├── logging_setup.py
├── cogs/
│   ├── core.py       ← /ping, /about, /help, /settings — always loaded
│   ├── presence.py   ← the About Me on `on_ready`, the member-count status (10-min loop +
│   │                   a 5-second debounce on join/leave), /presence apply
│   ├── community/    ← one cog per community feature
│   │   ├── role_menus.py  ← F16: /rolemenu + persistent select panels + staff assign + approvals
│   │   ├── tempvoice.py   ← F8: join-to-create voice channels, the owner control post, and
│   │   │                    /voice — ONE command, one panel (both groups retired). The pure
│   │   │                    state machine and button table live in `black_bloc/tempvoice.py`
│   │   ├── events.py      ← F4/F5: /event — ONE command, one panel (the `timezone` group is
│   │   │                    retired); review channels, Approve/Deny, go-live. The shared DB
│   │   │                    and move layer lives in `black_bloc/events.py`, not here
│   │   ├── birthdays.py   ← F6: the five-minute sweep, the /birthday panel, the day role, the daily import
│   │   ├── polls.py       ← F15: /poll on native Discord polls + Black Bloc's own panel, /poll recur
│   │   ├── requests.py    ← F18: /request, the member intake, the pending-features board
│   │   └── applications.py ← Phase 19: /apply — ONE command, one panel (both groups retired);
│   │                        the forms, the queue, approve/deny/remove, the roster
│   ├── moderation/   ← one cog per moderation feature
│   │   ├── honeypot.py    ← F9: the trap channel, delete + ban, shadow first
│   │   ├── modmail.py     ← F11: inbound DM → ticket channel or private thread, the /modmail panel, the sticky ticket card, /reply, transcript
│   │   ├── automod.py     ← F7: the message listener, the Apply-now button, /automod
│   │   └── modcmds.py     ← F7: /warn /timeout /untimeout /kick /ban /unban /purge + the /mod panel
│   └── content/      ← one cog per content feature
│       ├── golive.py ← F1/F2: presence listener, Twitch poller, the /golive panel
│       ├── chat.py   ← F10: the @-mention listener, cooldown, modmail routing, /chat
│       ├── pings.py  ← F14: /pings — ONE command, one ephemeral panel (wave 2). Member half:
│       │                follow/stop-following selects, the Events toggle(s), the fan button.
│       │                Staff half: Streamers…, Set up the Events role, Settings, Logs
│       ├── chat_memory.py ← Phase 17: the hourly distillation sweep and /memory — ONE command,
│       │                    one member panel. The pure half is `chat_distil.py`
│       ├── raidtrain.py ← Phase 18: /raidtrain — ONE command, one panel (both slots retired);
│       │                  slots, claims, the lineup post, the 30-minute reminder DM
│       └── youtube.py ← F3: the uploads sweep and /youtube, ONE command that opens a panel for
│                        members and staff alike (2026-09-03; /uploads is retired). Reads the
│                        public Atom feed; YOUTUBE_API_KEY is optional (see KI-11)
├── storage/db.py     ← aiosqlite connection + schema bootstrap (SCHEMA_VERSION 34, measured 2026-09-11)
└── api/             ← the dashboard API, one router per surface (API_ENABLED)
    ├── server.py    ← create_app: /health (public), security headers, routers, then site/ at /
    ├── auth.py      ← Discord OAuth2 + the signed session cookie. The site's ONLY gate.
    │                  Also the operator read token and both rate buckets
    ├── sessions.py  ← the signed-cookie session store behind auth.py
    ├── costs.py     ← /api/costs: the chat spend ledger, hosting cost, secret presence (names only)
    ├── selftest_api.py ← /api/selftest — run, list, read one, purge one. The self-test's web door
    ├── status.py    ← /api/status + /api/actions — READ-ONLY, staff-gated
    ├── writes.py    ← THE SHARED WRITE SIDE: staff + one rate-limit bucket per bot, the guard's
    │                  409, the guild/database checks, and the `web.<area>.<verb>` audit line
    ├── names.py     ← the resolver every table uses. CACHE ONLY — no fetch_* call anywhere in it
    ├── ref.py       ← /api/ref/{channels,roles,members,names} — the pickers' data
    ├── settings_api.py ← /api/settings + /api/settings/audit. Owns NAMESPACE_OVERRIDE
    ├── assets.py    ← the cache-busting asset stamp (?v=…) and the no-store headers
    └── tools/       ← ONE ROUTER PER FEATURE TAB; each calls the cog's own plain helpers,
        │              never a second copy of the rule
        ├── mod.py        ← cases, the action bar, the rule book
        ├── modmail.py    ← tickets, replies, closes, snippets, blocks
        ├── events.py     ← the approval queue: approve / deny / cancel
        ├── golive.py     ← links, opt-outs, recent sessions
        ├── youtube.py    ← F3: upload links, the videos seen, and the sweep's own status
        ├── pings.py      ← F14: the streamer table, staff create/remove, the Events-role set-up
        ├── rolemenus.py  ← menus, options, post
        ├── birthdays.py  ← the list, set / remove, and the Birthday Bot import
        ├── honeypot.py   ← hits, Ban-now, setup
        ├── tempvoice.py  ← the live channel list, setup / repair
        ├── polls.py      ← the poll list, create, end / cancel, results
        ├── requests.py   ← the requests board + the member-only routes (the one non-staff gate)
        ├── chat.py       ← the editable intents and lines, the manners settings
        ├── chat_memory.py ← Phase 17: the stored preference profiles and the opt-out list
        ├── applications.py ← Phase 19: forms, questions, the queue, approve/deny/remove, the roster
        ├── raidtrain.py  ← Phase 18: trains, slots, claims, the lineup post
        ├── members.py    ← the Members tab: the roster, roles, grant chips
        └── roles.py      ← timed role grants: list, extend, end now
site/                 ← THE DASHBOARD (8a status page, 8b tabs). Static, no build step, COMMITTED
├── README.md         ← the developer-facing half (committed; `docs/access/site.md` is the runbook)
├── mock/             ← the contract's EXECUTABLE form. Node's own `http`, no dependency
│   ├── server.mjs    ← serves site/public AND /api/* on one origin, as the real deployment does.
│   │                   MOCK_TEST_MODE defaults ON, so refusals are what a developer meets first
│   ├── contract.json ← ⚠️ THE ONE HOME for every route's shape, derived from the pages'
│   │                   own property accesses. Read by BOTH halves of the contract check
│   └── check.mjs     ← fetches every page and every route from the mock and asserts contract.json
└── public/
    ├── index.html    ← Overview; <meta name="api-origin"> is EMPTY = "the origin I came from"
    ├── {moderation,automod,modmail,events,golive,rolemenus,birthdays,tempvoice,honeypot,
    │    polls,chat,requests,members,settings,audit,health}.html ← the other sixteen tabs
    │                   (17 pages total, measured 2026-08-31). Each is an empty shell:
    │                   #tabnav + #dash, filled by its page module. The nav is built from ONE
    │                   array in app.js, never seventeen hand-written copies
    │                   (17 `.html` files counted on disk 2026-09-11)
    └── assets/
        ├── api.js    ← the ONLY fetch. Outage vs refusal, the name cache, the ref caches
        ├── app.js    ← the shell: the tab list, the five permission states, start()/reload()
        ├── ui.js     ← the widgets. createElement + textContent only; nothing assigns innerHTML
        ├── page-*.js ← one module per tab, each exporting nothing and calling start()
        ├── labels.js ← ⚠️ the one home for every settings key's human sentence
        ├── logs.js   ← the shared Logs list every page embeds
        ├── shell.js / layout.js / theme.js / palette.js / icons.js / motion.js /
        │   permission-ux.js ← the restyle's shared chrome
        └── site.css  ← ours, beside a SNAPSHOT of the estate theme + fonts
                        (`estate-theme.css`, `status-shell.css`, `fonts/`)
tests/                ← everything runs OFFLINE; no test needs a token or the gateway
└── api/test_contract.py ← runs contract.json against the REAL routers with fakes, so the
                           mock and the bot cannot answer different shapes
```

⚠️ **The two halves of Phase 8b were built blind against
[`phase8b-design.md`](phase8b-design.md) and had never met.** The contract fixes
the JSON only for `/api/ref/*` and `/api/settings`; everywhere else the pages
guessed and the routers guessed, and they disagreed on nine routes. The fix is
`site/mock/contract.json` plus the two checkers that read it — the shape now has
one home, and a page and a router cannot drift apart without one of them going
red. `api.js`'s `listOf()` stays as deliberate slack on top of that.

⚠️ **Option A: one app, one origin, no Cloudflare Pages.** `server.py` mounts
`site/public` with `StaticFiles(html=True)` at `/` **after** the routers, so
`/health` and `/api/*` win and everything else is a file. There is no
`wrangler.toml`, no Pages project and **no CORS middleware** — a same-origin
`fetch` needs none. `SITE_ORIGIN` is the single hostname value (the OAuth
redirect base, where sign-in returns, and whether the cookies get `Secure`);
`SITE_ROOT` is the directory served. See
[`../access/site.md`](../access/site.md).

Two module-level facts worth knowing before adding a feature: config knobs go
through `settings_store.py` (a row in its registry, never a new `.env` field
per feature), and anything a feature does to a member or a channel goes
through `actionlog.py:log_action`. See [`phase1-design.md`](phase1-design.md)
and [`phase2-design.md`](phase2-design.md).

A feature that decides something keeps the decision in a **pure module** and
the Discord plumbing in the cog — `golive.py` next to `cogs/content/golive.py`
is the pattern; `events.py` next to `cogs/community/events.py` repeats it,
`birthdays.py` next to `cogs/community/birthdays.py` repeats it again, and so
does `modmail.py` next to `cogs/moderation/modmail.py`.
It is what lets the announcement wording, the debounce, the role filters, the
channel-name rules and the event status machine be tested with no gateway and
no network.

`tzdata` is a **runtime dependency**, not a convenience: Windows ships no
zone database, so without it `zoneinfo.available_timezones()` is empty and
every zone lookup and every event start fails — `timezones.py:31`'s
`available_timezones()` is what feeds the `My time zone` picker on the `/event` panel (the
`/timezone` command itself retired with the events panel in v64). Pinning it in
`pyproject.toml` makes the Windows developer machine and the Linux container
resolve the same zones from the same data.

The source carries near-zero comments (rule 0 below); the explanations live in
[`code-notes.md`](code-notes.md), keyed by `path:line`.

## The rules that shape it

0. **Near-zero comments in code (owner rule, 2026-08-26).** The source does
   not explain itself in comments; [`code-notes.md`](code-notes.md) does,
   keyed by `path:line`. A comment survives only where the code would
   *mislead* without it (a `type: ignore`, a deliberate no-op), one line.
   Docstrings: one line or none. When you find yourself writing a paragraph
   above a function, it goes in `code-notes.md` with a link to the line.
1. **The entrypoint is a run button (owner rule, 2026-08-26).** `app.py`
   wires settings → logging → bot and starts it; nothing else. `bot.py` is
   lifecycle only (intents, cog list, setup/close). Every behaviour — sync,
   invite URL, error mapping, guards — is its own module with helpers. A
   feature that "just needs a line in app.py" is in the wrong place.
2. **One cog per feature.** A cog is a class in its own module under
   `cogs/community/`, `cogs/moderation/` or `cogs/content/` with `async def setup(bot)`, registered
   by adding its dotted path to `bot.py:COGS`. Cogs talk to the DB through
   `bot.db`, to config through `bot.settings`. Cogs do not import each other;
   shared logic goes in a plain module the cogs both import.
3. **Slash commands first.** `app_commands` are the user surface. The text
   prefix exists for emergencies (works even when command sync is broken).
4. **One config owner.** `config.py` is the only place `os.environ`/`.env` is
   read. Add a field there with a default; document it in `.env.example`.
5. **Schema changes are migrations, not edits.** `storage/db.py:SCHEMA` is
   additive (`CREATE TABLE IF NOT EXISTS`, `CREATE … INDEX IF NOT EXISTS`).
   A **new column** on an existing table is a row in
   `storage/db.py:ADDED_COLUMNS`, applied by `Database.connect` as an
   `ALTER TABLE … ADD COLUMN` guarded by a `PRAGMA table_info` check — never
   a rewrite of a `CREATE TABLE` that has already run somewhere. Neither
   needs a version bump, because both are idempotent on any existing file;
   `SCHEMA_VERSION` moves when a change cannot be expressed that way, and the
   first such change introduces numbered migrations keyed on
   `schema_meta.schema_version`.
   ⚠️ **One exception exists and it is the only one: Phase 6's `mod_cases`
   rebuild** (`storage/db.py:296` and `:306`), which drops the table's two
   indexes, renames it aside, lets the schema script recreate it with a
   nullable `user_id`, copies the rows back and drops the husk. It is NOT a
   numbered migration because it does not need one: it is guarded by a
   `PRAGMA table_info` check that returns immediately when the constraint was
   never there, so it is idempotent on every file including a fresh one. Read
   it as the shape a bounded rewrite must take — guarded, bounded, and
   re-runnable — not as permission to edit a `CREATE TABLE` in place. A change
   that cannot be written this way is still the one that starts numbered
   migrations.
6. **Nothing in tests needs Discord.** Bot construction and cog loading work
   offline (`tests/test_bot.py` proves it). Anything that needs the gateway is
   a manual smoke test in `access/setup.md` §3, labelled as such.
7. **Tests mirror the package, one file per source file (owner rule,
   2026-08-26).** `black_bloc/<path>/<name>.py` ↔ `tests/<path>/test_<name>.py`
   — same folder shape, so a test is always one hop from its subject. No
   flat pile of test files. `conftest.py` stays at `tests/` root. pytest runs
   with `--import-mode=importlib` so same-named test files in different
   folders coexist without `__init__.py` files.
8. **Only bot code is committed (owner rule, 2026-08-26).** Research tooling
   (scans, scrapers, one-off inventories) and their tests never enter git;
   they live under `scripts/scan/` (gitignored).

## Why these libraries

| Choice | Over | Because |
|---|---|---|
| `discord.py` 2.x | hikari, nextcord, pycord | Largest ecosystem, first-party slash commands, cogs = natural feature unit; no estate Python bot to match |
| FastAPI (optional) | Flask | Same asyncio loop as the bot → routes read bot state directly, no thread/IPC. Flask would need both |
| SQLite via aiosqlite | Postgres | One process, one file, no service to run or pay for. Revisit at a second process or real write volume |
| pydantic-settings | hand-rolled `os.environ` | Typed, validated, `.env` for free, one owner |

## How the optional API runs

`bot.setup_hook` creates `start_api(bot)` as a background task on the same
loop; `uvicorn.Server.serve()` is awaited there. `bot.close()` cancels it.
Off by default and localhost-only in `.env`; **on and bound to `0.0.0.0` on
Fly**, where `[http_service]` exposes it. Since Phase 8a it is the config
site's back end: `api/auth.py` gates everything except `/health` behind a
Discord-OAuth session, and `api/status.py` serves the read-only status page.
Being in the bot's own process is what lets a route read live gateway state
and the same SQLite file with no IPC.

⚠️ **`auto_stop_machines`, `auto_start_machines` and `min_machines_running` in
`fly.toml` are load-bearing**, not tuning: the machine that answers HTTP is the
machine holding the outbound gateway websocket, and Fly's default
auto-stop-on-idle would kill it. An idle HTTP service is not an idle bot
([`hosting.md`](hosting.md)).

## Runtime model

One process, one persistent outbound websocket to the Discord gateway. That
single fact decides hosting — see [`hosting.md`](hosting.md).
