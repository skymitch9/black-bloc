# Phase 12 — Logs: quiet Discord, loud website, `/… logs` everywhere

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


> **Audience:** the Phase 12 build agents and the reviewer. **Status:** TRACKED (2026-08-31; private repo).
> Last verified: **2026-08-27** — owner decisions taken 17:14–17:17; code facts from `black_bloc/actionlog.py`
> and the per-phase code-notes kind lists (every phase reported its `log_action` kinds). NOT verified:
> nothing has run. **Build after the Sunday 2026-08-30 16:00 weekly reset** unless the owner says otherwise.

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
| 3 | Per-feature control | `<feature>_log_level` ∈ `off` / `important` / `all`, default **important** (settings registry, one key per feature namespace: core, automod, honeypot, mod, modmail, golive, events, birthdays, tempvoice, rolemenu, poll, chat) |
| 4 | Website | a **Logs** section on every feature page + the Audit tab becomes the global **Logs** page |
| 5 | Slash | `/<feature> logs [count]` on every feature group, ephemeral, from the DB |

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

### 4. Slash
`/<feature> logs [count: 1–50, default 10] [important_only: bool]` added to every command group (`/golive`,
`/event`, `/birthday`, `/voice`, `/rolemenu`, `/role`, `/automod`, `/honeypot`, `/modmail`, `/poll`, `/chat`,
plus `/mod logs` for cases/warns) — ephemeral embed, newest first, `<t:…:R>` stamps, one line per action,
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
