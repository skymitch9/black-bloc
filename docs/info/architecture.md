# Architecture

> **Audience:** Claude sessions and the owner. **Status:** TRACKED (owner, 2026-08-31 — was
> local-only until then).
> Last verified: **2026-09-10 16:40** (the raid-train calendar-name paragraph: keys measured by import, tests and mock routes from the gate; nothing else re-measured) — earlier **2026-09-10 16:02** (the v100 paragraph: keys and schema measured by import, tests from the gate; nothing else re-measured) — earlier **2026-09-05**: every figure below re-MEASURED on the ENGINEERING SWEEP 3
> branch off `main` at `6af0ba0` (v92) by running the thing, not by reading a doc: the tree is
> built the way `tests/test_bot.py` builds it (load all `bot.py:COGS`, then `tree.get_commands()`),
> `SCHEMA_VERSION` is imported from `black_bloc/storage/db.py`, and the site figures come from
> `node site/mock/check.mjs` against `site/mock/server.mjs`.
>
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
> | What | v92 | Where it is measured |
> |---|---|---|
> | Cogs | **19** | `bot.py:COGS` |
> | Top-level slash commands | **29** — 15 staff-locked, 14 member-visible | `tree.get_commands()` |
> | `app_commands.Group`s | **0** | ⚠️ every group retired by the panel waves |
> | Schema version | **34** (on `where-picker`; **33** on `main`) | `storage/db.py:SCHEMA_VERSION` |
> | Registry keys | **189** | `settings_store.KEY_TYPES` |
> | Features (log-level keys) | **18** | `settings_store.FEATURES` == `logkinds.FEATURES` |
> | Mock contract | **17 pages / 149 routes / 14 core settings** | `node site/mock/check.mjs` |
> | Deploys | **91**, last `4b327cf` (v92) at 2026-09-05 20:44 | `../deploys.log` |
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
> | **v92 `6af0ba0`, 2026-09-05** | **19** | **29** | **32** | **149** | **5186** |
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
│   │   └── requests.py    ← F18: /request, the member intake, the pending-features board
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
│       └── youtube.py ← F3: the uploads sweep and /youtube, ONE command that opens a panel for
│                        members and staff alike (2026-09-03; /uploads is retired). Reads the
│                        public Atom feed; YOUTUBE_API_KEY is optional (see KI-11)
├── storage/db.py     ← aiosqlite connection + schema bootstrap (SCHEMA_VERSION 22)
└── api/             ← the dashboard API, one router per surface (API_ENABLED)
    ├── server.py    ← create_app: /health (public), security headers, routers, then site/ at /
    ├── auth.py      ← Discord OAuth2 + the signed session cookie. The site's ONLY gate
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
    └── assets/
        ├── api.js    ← the ONLY fetch. Outage vs refusal, the name cache, the ref caches
        ├── app.js    ← the shell: the tab list, the five permission states, start()/reload()
        ├── ui.js     ← the widgets. createElement + textContent only; nothing assigns innerHTML
        ├── page-*.js ← one module per tab, each exporting nothing and calling start()
        └── site.css  ← ours, beside a SNAPSHOT of the estate theme + fonts
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
every `/timezone` lookup and every event start fails. Pinning it in
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
