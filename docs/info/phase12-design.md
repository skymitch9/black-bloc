# Phase 12 — Logs: quiet Discord, loud website, `/… logs` everywhere

> ⚠️ **SUPERSEDED IN PART, 2026-09-03 (v70, `0aeed72`) — the slash surface below is gone.** `/golive` and
> `/twitch` and all eight of their subcommands (`logs`, `optout`, `optin`, `status`, `mode`,
> `test`, `link`, `unlink`) were replaced by ONE `/golive` command that opens an ephemeral
> panel; every subcommand is a button, a select or a modal on it. The behaviour this doc
> describes is unchanged — the announcer, the poller, the sessions, the settings and the log
> kinds are all exactly what it says. Only the way in moved:
> [`golive-panel-design.md`](golive-panel-design.md). This doc is NOT rewritten.
>
> ⚠️ **EVERY `/<feature> logs` SUBCOMMAND IS GONE, 2026-09-03 → 2026-09-05.** §4 below lists
> eleven of them; the panels program retired the lot. There are **zero `app_commands.Group`s
> and zero subcommands** in the tree today (29 top-level commands), so every feature reaches
> its lines through a **Logs button** on its panel, calling the same
> `actionlog.send_logs(interaction, "<feature>")` the subcommand called. `black_bloc/logs_panel.py`
> is the shared implementation. See [`logs-buttons-design.md`](logs-buttons-design.md) and
> [`panels-program.md`](panels-program.md) invariant P11.
>
> ⚠️ **`/mod logs` is gone too, 2026-09-05 (v81, `a90f416`).** `/mod` became ONE command that opens a panel over
> the case record, and its **Logs** button calls the same `send_logs(interaction, "mod")` — the
> lines, the kinds and the gate are unchanged; only the way in moved
> ([`mod-panel-design.md`](mod-panel-design.md)). `LOG_LEVEL_COMMANDS["mod"]` was REMOVED rather
> than re-pointed, so `mod_log_level`'s help text now says the lines are kept on the dashboard,
> which is true. Same rule: this doc is NOT rewritten.

> ✅ **12a BUILT (2026-08-27)** on branch `agent-ac3b8dd35b6cc0c5d` off `main` @ `0090fd8`, in seven
> commits: `313fa48` (`logkinds.py` + the classification test), `e352f33` (the twelve
> `_log_level` keys), `d6f0541` (the gate in `log_action` + the shared renderer),
> `d4ac492` (`/<feature> logs` on every group), `da020f6` (the `/api/actions` filters +
> `export.csv`), `a6f422b` (12b's clarifications: `kinds` and per-row `summary`), `f0a897f` (every `.would_` kind routine by rule).
> `pytest -q` **2017 passed** (1941 before, +76). `ruff check .` clean. `site/mock/check.mjs`
> clean at **16 pages, 81 routes**. **12b (the dashboard) is separate** and is not in
> these commits. ⚠️ **Nothing has run against live Discord** — no line has been observed
> suppressed or posted. Read `docs/info/code-notes.md` § *logs (12a)* for the kind table
> and the decisions.


> **Audience:** the Phase 12 build agents and the reviewer. **Status:** TRACKED ·
> ✅ **LIVE since 2026-08-27** — both halves deployed together as `417ef23`,
> `2026-08-27T18:38:56-07:00` ("269 kinds classified (88 important), per-feature `_log_level`
> gates the Discord line, `/<feature> logs` on 12 groups, `/api/actions` filters + CSV, Logs
> sections on every page, Audit tab = Logs page"; 34 commands synced); `DONE.md` →
> "2026-08-27 — Phase 12: Logs — quiet Discord, loud website, /… logs everywhere". ⚠️ Fly
> release numbers were not written into `deploys.log` until **v59** (2026-09-03), so this
> landing has a date and a commit but no `vNN`.
>
> ⚠️ **The COUNT "twelve" in decision 3 and §"Slices" is now EIGHTEEN.** Measured 2026-09-11:
> `len(logkinds.FEATURES)` is **18** — `core, automod, honeypot, mod, modmail, golive,
> **youtube**, events, birthday, tempvoice, rolemenu, poll, chat, **request**, **pings**,
> **raidtrain**, **applications**, **selftest**` — and there are **18** `<feature>_log_level`
> keys in `KEY_TYPES`, one per feature. `logkinds.IMPORTANT` holds **28** kinds today.
> (The "269 kinds / 88 important" figure in the deploy line is a 2026-08-27 snapshot of the
> whole classified surface, a different count from `IMPORTANT`'s explicit list.)
>
> Last verified: **2026-09-11 10:12** — re-measured against the tree at `1d090e5`:
> `logkinds.FEATURES`, `logkinds.IMPORTANT`, `actionlog.send_logs` (`:299`) and
> `settings_store.LOG_LEVEL_COMMANDS` (`:974`) all exist; the 18 `_log_level` keys listed
> above are all in `KEY_TYPES`. ⚠️ **NOT verified:** still nothing against live Discord — no
> line has been watched being suppressed or posted, no Logs button pressed, no dashboard page
> opened in this pass.
> Before that, **2026-08-27** — owner decisions taken 17:14–17:17; code facts from `black_bloc/actionlog.py`
> and the per-phase code-notes kind lists (every phase reported its `log_action` kinds).

> **12b built** in `48927b2` (contract + mock) / `32c8d23` (logsSection + the twelve mounts) /
> `ec70c9b` (audit.html becomes the Logs page) / `6e2b6fc` (Overview important-only) / `047b21a`
> (the 390px fix), on branch `worktree-agent-a7158ae45cbdd06f1` off `main` @ `0090fd8`. Nothing under
> `black_bloc/` was touched. Details, deviations and what was NOT verified:
> `docs/info/code-notes.md` § `logs — dashboard (12b)`.

## The ask (owner, verbatim, 2026-08-27 17:14)
"i think we need to pipe a lot of the logs to the website and a logs command per function and keep the
discord spam to a minimum" — then (17:17) "a is fine, also any approvals need to make notifications still".

## Decisions
| # | Decision | Owner's call |
|---|---|---|
| 1 | What reaches the Discord log channel by default | **(a) important = acted on a member, or failed.** Shadow `would_*`, housekeeping, chat replies, poll creations, reminders, sweeps stay off Discord |
| 2 | Approval requests | **Always notify.** Role requests, poll reviews and event proposals post their card/ping to their approval channel regardless of any log level — they are notifications, not log lines |
| 3 | Per-feature control | `<feature>_log_level` ∈ `off` / `important` / `all`, default **important** (settings registry, one key per feature namespace: core, automod, honeypot, mod, modmail, golive, events, birthdays, tempvoice, rolemenu, poll, chat) — ***eighteen** today: `youtube`, `request`, `pings`, `raidtrain`, `applications` and `selftest` joined with phases 13–19 and the self-test wave, and the key is `birthday_log_level` (singular)* |
| 4 | Website | a **Logs** section on every feature page + the Audit tab becomes the global **Logs** page |
| 5 | Slash | `/<feature> logs [count]` on every feature group, ephemeral, from the DB — *(removed 2026-09-03…09-05: every one is now a **Logs button** on the feature's panel calling the same `send_logs`; see the banner at the top)* |

## What exists (read, not remembered)
`actionlog.log_action(bot, guild, kind, actor=…, target=…, details=…)` writes the `actions` row and posts a
line to `log_channel_id` (through the guard). Kinds are dotted `feature.event` strings
(`golive.announce`, `role.approved`, `poll.would_close`, `chat.insult`, `web.settings.set`, …); the
dashboard reads them via `GET /api/actions?kind=` (Audit page, Health's last-50, Overview's Last actions).

## Design

### 1. Importance is a property of the KIND, decided in one place
`black_bloc/logkinds.py`: `IMPORTANT: frozenset[str]` (the exact kinds that acted on a member or failed —
built from every phase's kind list; suffix rules as a backstop: `*_failed`, `.approved`, `.denied`,
`.expired`, `.warned`, `.timed_out`, `.kicked`, `.banned`, `.granted`, `.ended`), `feature_of(kind)`
(`golive.announce` → `golive`; `web.role.approved` → `rolemenu` via a small alias table), and
`should_post(kind, level)`. A test asserts every kind the codebase emits (grep at test time over
`black_bloc/**` for `log_action(` string literals) is classified — a new kind that is neither listed
nor matched by a suffix fails the test, so silence is never accidental.

### 2. `log_action` gains the gate
Same signature. After writing the row: `level = store.get(guild.id, f"{feature_of(kind)}_log_level")`;
post to Discord only if `should_post(kind, level)`. `all` = today's behaviour; `off` = DB only.
**Approval cards are not `log_action` calls** — they are their own sends in the events / role-menu /
poll cogs and are untouched (decision 2). A `notify` flag on `log_action` (default False) forces the
Discord line for the handful of kinds the owner wants regardless (none today; the hook exists).

### 3. Website
- `GET /api/actions` gains `feature=`, `q=` (substring over kind/actor/target/details), `since=`/`until=`,
  `important=1`, paging (it has `kind=` and a limit today) and `GET /api/actions/export.csv`.
- Shared `logsSection(feature)` in `ui.js`: kind chips (this feature's kinds), search, important-only
  toggle, pager (scroll-to-top helper), `—` for empty cells, actor/target links to Members; mounted at the
  foot of every feature page (golive, events, birthdays, tempvoice, rolemenus, moderation, automod,
  honeypot, modmail, polls, chat) and on Settings for `web.settings.*`.
- `audit.html` → **Logs**: all features, actor/target filters, date range, important-only, export.
  Health keeps its last-50 (different question: "is it alive").
- Each feature page's Settings section shows its `<feature>_log_level` segment.

### 4. Slash — ⚠️ REMOVED 2026-09-03 → 2026-09-05 (every one is a Logs BUTTON now)

*(Removed: all eleven `/<feature> logs` leaves retired with their groups as the panels program
landed. The button on each panel calls the same `actionlog.send_logs`, loses the two options,
and carries its own `require_staff`. `black_bloc/logs_panel.py` is the shared implementation;
see [`logs-buttons-design.md`](logs-buttons-design.md). Kept below as the record of what the
slash surface was.)*

`/<feature> logs [count: 1–50, default 10] [important_only: bool]` added to every command group (`/golive`,
`/event`, `/voice`, `/rolemenu`, `/role`, `/automod`, `/honeypot`, `/modmail`, `/poll`, `/chat`,
plus `/mod logs` for cases/warns; `/request` and `/birthday` moved theirs onto a **Logs button** when they
became panels — the button loses the two options and calls the same `send_logs`) — ephemeral embed, newest first, `<t:…:R>` stamps, one line per action,
a footer pointing at the dashboard page. Staff only where the feature is staff-only.

### 5. Test mode
Unchanged: the Discord line still goes through the guarded send; the DB row is always written.

## Slices
- **12a** (bot + API, ~250k): `logkinds.py` + classification test, the gate in `log_action`, the twelve
  `_log_level` keys, `/… logs` on every group, `GET /api/actions` filters + export, contract/mock entries.
- **12b** (dashboard, ~200k): `logsSection` on every page, the Logs page replacing Audit, settings segments.

## Definition of done
Every emitted kind classified; `pytest -q` green; `ruff` clean; `check.mjs` clean; code-notes keyed
`path:line`; owner sweep: flip `golive_log_level` to `all`, run `/golive test`, see the Discord line; flip
back to `important`, run it again, see only the dashboard row; `/golive logs`; a role request still posts
its card with `rolemenu_log_level = off`.
