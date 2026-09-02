# Architecture

> **Audience:** Claude sessions and the owner. **Status:** TRACKED (owner,
> 2026-08-31 — was local-only until then).
> Last verified: **2026-09-02** — the fast-moving figures re-measured:
> `SCHEMA_VERSION` is **20** (17 sessions, 18 `polls.vote_scheme`, 19
> `golive_sessions.live_role_id`, 20 the chat tables), `check.mjs` reports
> **17 pages / 107 routes**, `pytest` runs **2610** tests (also green on
> ubuntu CI), `ruff check .` clean; `bot.py:COGS` still **14** cogs. New since
> the tree below was drawn: `chat_llm.py`, `llm.py`, `groq.py`, `knowledge.py`,
> `personas.py`, `directory.py`, `chat_check.py`, `dbsnapshot.py`,
> `api/costs.py`. ⚠️ NOT re-checked: the Shape tree's per-file annotations
> (verified 2026-08-31). Three cogs (polls, requests, chat) and eleven modules the tree did not
> list have been added, and the **Carl parity** entries removed — parity was
> deleted in `47634b8` and `grep -ri carl black_bloc site` is empty.
>
> ⚠️ **NOT verified today:** the *prose* below the tree (the rules, the library
> table, the API section) was read but not re-traced to the code; and nothing
> here was checked against the running bot or a browser.
>
> 🔴 **The "NOT verified" paragraph that used to end this header was itself
> stale and is replaced.** It claimed the site had never been opened in a
> browser and that `blackbloc.heygabi.ai` had "no DNS record and no certificate
> yet". Both are false: the owner signed in and saw the dashboard on 2026-08-26
> ~23:00, the site has been served from the Fly app on that hostname since, and
> `docs/deploys.log` records **37 deploys**, the last `8036918` at **2026-08-27
> 20:15**. What IS still unexercised by a person is tracked, per feature, in
> [`../access/sweeps.md`](../access/sweeps.md) — that file is the one home for
> "shipped but never clicked", and this header should not grow a second copy.
>
> *(Historical build-order narrative, left as written and NOT re-checked:)*
> matches the code after **presence**
> (`presence.py`, `cogs/presence.py`, the `bot_bio` and `status_prefix` registry keys;
> **1194 tests pass, ruff clean**), on top of the **Phase 8b merge
> and reconciliation** (the full dashboard: `api/{writes,names,ref,settings_api}.py`
> and `api/tools/*`, thirteen tabs under `site/public`, and `site/mock/` as the
> contract's executable form; **1105 tests pass, ruff clean**), on top of the
> **Phase 8a merge**
> (the config site: `api/auth.py`, `api/status.py`, the reworked `api/server.py`
> and the committed `site/` tree; **800 tests pass, ruff clean**), on top of the
> **Phase 6 merge**
> (moderation: `automod.py`, `modcases.py`, `cogs/moderation/automod.py`,
> `cogs/moderation/modcmds.py`), on top of the **Phase 7 merge**
> (modmail: `modmail.py`, `cogs/moderation/modmail.py`), on top of the Phase 5
> merge (birthdays: `birthdays.py`, `cogs/community/birthdays.py`, the shipped
> `data/` seed), the Phase 4 build (timezones, events logic, the
> events cog), the Phase 3 adversarial review fixes (temp voice, honeypot,
> staff derivation) and the Phase 2 go-live review fixes (Twitch client,
> go-live logic, go-live cog, `command_errors.py`). **Schema v8** — Phase 6's
> `mod_cases` table with two indexes and its five additive columns
> (`actions`, `done`, `failed`, `message_id`, `channel_id`), beside Phase 7's
> four `modmail_*` tables, two indexes and its additive
> `modmail_messages.delivered`, on top of Phase 5's `birthdays` plus
> `birthdays.role_added_id`,
> Phase 4's `user_timezones` and `events`, Phase 3's three tables, v3's one
> additive column and one partial unique index, all applied by idempotent
> steps inside `Database.connect`. ⚠️ **v7 was skipped and stays skipped:** it
> was Phase 6's own bump, and the Phase 6 merge kept **8** rather than
> renumbering, because every statement on both sides is additive and
> idempotent — the number is a label, and the merge order does not change the
> database it produces. ⚠️ **Phase 6 brought the project's first NON-additive
> step**, and it is bounded and idempotent: a `mod_cases` whose `user_id` is
> `NOT NULL` is set aside before the schema script runs, recreated nullable
> and copied back (`storage/db.py:296`), because a purge case belongs to a
> channel rather than a member. It needs no version branch — the PRAGMA check
> returns immediately on a table that never had the constraint. **Phase 8a added
> no schema at all** — the status page is a reader, so the version stayed **8**
> through 8a and 8b. ⚠️ **The temp-voice panel + `/voice` merge (2026-08-27) took
> it to 10**, and this time the numbers are used rather than skipped:
> `tempvoice_channels.panel_channel_id` is 9 (a click has to find its channel now
> that the panel can live somewhere else) and `tempvoice_prefs.bitrate` is 10.
> Both are additive through `ADDED_COLUMNS` and both are in `SCHEMA` as well, so a
> fresh database and a migrated one agree. 1134 tests pass; ruff clean.
> `cogs/community/role_menus.py` is now the worked example of the cog
> convention; `cogs/community/events.py` is the worked example of a feature
> whose side effects the guard cannot see at all, and
> `cogs/moderation/modmail.py` is the worked example of a feature whose whole
> SURFACE the guard would otherwise refuse — see `speak()` there, and
> `cogs/moderation/automod.py` is the worked example of a feature whose side
> effects (delete, timeout) the guard cannot see AND which therefore checks
> `bot.guard` by hand at every act site. NOT verified:
> any of it
> running against live Discord, no call has ever been made to the real Twitch
> API from this repo, no real Discord scheduled event has ever been created
> by it, and no DM has ever been relayed into a ticket — `modmail_enabled`
> defaults **false**, so the incumbent ModMail bot still holds the inbox. Nor
> has automod ever deleted a message, timed anybody out or read a Carl-bot
> modlog: `automod_mode` defaults **shadow**, and while `TEST_MODE` is on the
> engine only ever sees the test channel itself. Nor has the **site** ever been
> opened in a browser, nor has anybody completed a real Discord OAuth round-trip
> against this code: `blackbloc.heygabi.ai` has no DNS record and no certificate
> yet, and the cookies, CSP and static mount are asserted against an in-process
> ASGI client, which is not a browser (`../access/site.md`).

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
├── rolegrants.py     ← F16/Phase 9: time-limited role grants and the expiry/reconcile logic
├── rolemenu_panels.py ← posting and un-posting role-menu panels when rolemenu_mode flips
├── command_visibility.py ← hides a feature's slash commands while the feature is off (re-syncs)
├── logkinds.py       ← ⚠️ THE ONE HOME for log-kind classification: important vs routine, and
│                       `via_of()` (Discord vs website) which stamps every action-log row
├── emoji.py          ← skin-tone application for the bot's own emoji (emoji_skin_tone)
├── prefix.py         ← no_prefix_commands: the bot answers no text prefix (slash only)
├── data/             ← shipped package data (`pyproject.toml` → package-data)
│   └── birthday_import_2026-08-05.json  ← the 39-row Birthday Bot export, seed for /birthday import
├── logging_setup.py
├── cogs/
│   ├── core.py       ← /ping, /about, /help, /settings — always loaded
│   ├── presence.py   ← the About Me on `on_ready`, the member-count status (10-min loop +
│   │                   a 5-second debounce on join/leave), /presence apply
│   ├── community/    ← one cog per community feature
│   │   ├── role_menus.py  ← F16: /rolemenu + persistent select panels + staff assign + approvals
│   │   ├── tempvoice.py   ← F8: join-to-create voice channels, the owner control panel, /voice
│   │   ├── events.py      ← F4/F5: /event + /timezone, review channels, Approve/Deny, go-live
│   │   ├── birthdays.py   ← F6: the five-minute sweep, /birthday, the day role, the daily import
│   │   ├── polls.py       ← F15: /poll on native Discord polls + Black Bloc's own panel, /poll recur
│   │   └── requests.py    ← F18: /request, the member intake, the pending-features board
│   ├── moderation/   ← one cog per moderation feature
│   │   ├── honeypot.py    ← F9: the trap channel, delete + ban, shadow first
│   │   ├── modmail.py     ← F11: inbound DM → ticket channel or private thread, /reply, /close, transcript
│   │   ├── automod.py     ← F7: the message listener, the Apply-now button, /automod
│   │   └── modcmds.py     ← F7: /warn /timeout /untimeout /kick /ban /unban /purge /case /cases
│   └── content/      ← one cog per content feature
│       ├── golive.py ← F1/F2: presence listener, Twitch poller, /golive + /twitch
│       └── chat.py   ← F10: the @-mention listener, cooldown, modmail routing, /chat
├── storage/db.py     ← aiosqlite connection + schema bootstrap (SCHEMA_VERSION 19)
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
