# KI-24 loop guard, plus two small gates — design

> **Audience:** the build agent and reviewers. **Status:** TRACKED. Last verified: **2026-09-06 11:50** —
> every `path:name` below was read in the tree at `c71ed21` (v96 code). Owner decision **2026-09-06
> 11:48**, verbatim: *"Build it a"* — answering Q4 "KI-24: (a) build the guard, bundled with two small
> fixes, or (b) leave it WATCHING". Three items, one branch, one deploy.

## 1. What exists

- **KI-24** (`docs/KNOWN_ISSUES.md`): fourteen `tasks.loop`s across thirteen cogs (`grep -rln
  before_loop black_bloc --include=*.py`) each install `@loop.error` → record `last_error`, log,
  `loop.restart()` (the pattern: `cogs/community/polls.py:loop_failed` + `_polls_broke`). discord.py
  2.7.1 runs `before_loop` OUTSIDE the `try` that dispatches to `error` (`discord/ext/tasks/__init__.py`
  lines 210 / 217 / 278), so a `before_loop` that raises kills the task with no restart, no
  `last_error`, nothing on the Health tab. Every `_before_*` here is one line: `await
  self.bot.wait_until_ready()`.
- **`cogs/core.py:Core.cog_load`** starts `purge_loop` unconditionally; every other db-backed loop's
  `cog_load` first does `if not self.bot.db.is_connected: return` (`cogs/community/birthdays.py:cog_load`).
  The purge body already returns early on a missing db, so this is alignment, not a bug fix. ⚠️ Also
  read `Core._purge_failed`: it records and logs but does NOT `restart()` — say whether that is
  deliberate (the KI text claims every handler restarts; measure, and align or record why not).
- **`api/tools/polls.py:poll_create`** (one-off `POST /api/polls`) does not check `poll_mode`; the
  recurrence route beside it does: `if not polls_are_on(bot.store, guild.id): raise Refused(409,
  "polls_off", POLLS_OFF)`. Discord's `/poll` refuses with the same `POLLS_OFF`.

## 2. Rules

1. **One helper, fourteen callers.** A new leaf module `black_bloc/loops.py` with ONE coroutine —
   `wait_ready(bot, failed)` — that awaits `bot.wait_until_ready()` and, on any `Exception` (never
   `CancelledError`), hands the exception to `failed`, the cog's EXISTING `@loop.error` handler, so a
   `before_loop` failure takes exactly the path a body failure takes: `last_error` recorded, logged,
   restarted. Every `_before_*` becomes `await wait_ready(self.bot, self._x_broke)` (or whatever that
   cog's handler is called). No second copy of the try/except anywhere; an AST guard test asserts every
   `before_loop`-decorated method in `black_bloc/` calls `wait_ready`.
2. **Prove it with a REAL `tasks.Loop`, not a fake** (verification culture: exercise, don't reason).
   One test builds a minimal cog-shaped object with a real `@tasks.loop` whose bot's
   `wait_until_ready` raises once then succeeds, runs it under the event loop, and asserts: the handler
   recorded `last_error`, the loop restarted, and the body ran on the second attempt. If `restart()`
   from inside `before_loop` does not behave (the current task is the one being cancelled), say so in
   `## Deviations` and pick the alternative that the test proves: record + log, return, and let the
   body's own `is_connected` guard carry it. Whichever way, the Health tab must show an error beside a
   loop that failed this way — that is the whole point of the KI.
3. **`Core.cog_load`** guards on `self.bot.db.is_connected` before `purge_loop.start()`, like
   `birthdays`. Read the selftest test fixtures first (`tests/test_selftest_panels.py::live` and
   `tests/cogs/test_core.py`) — some load Core with a connected db on purpose and count on the loop.
4. **`poll_create`** gets the same three lines the recurrence route has (`409 polls_off`, `POLLS_OFF`).
   The page already shows a refusal sentence in the form's notice line; nothing new on the page.
5. **No new setting.** Nothing here is a decision a Lead would want to change (checklist 33 asks
   nothing). No new log kind — a loop failure is logged, not a log-table row (checklist 34).
6. **KI-24 moves out of `KNOWN_ISSUES.md`** in the same branch: replace its body with a two-line
   `CLOSED 2026-09-06 (branch loop-guard)` stub pointing at this doc, keep the number (numbers are
   never reused). The conductor writes the DONE entry — do not touch `TODO.md` / `DONE.md` /
   `deploys.log` / `architecture.md`.

## 3. Tests (mirror the package)

`tests/test_loops.py` (new): the real-Loop test above; `wait_ready` re-raises `CancelledError`
untouched; the AST guard over every `before_loop`. `tests/cogs/test_core.py`: no db → `purge_loop`
not started; db → started. `tests/api/tools/test_polls.py`: `poll_mode = off` → `POST /api/polls`
answers 409 in words and writes zero rows.

## 4. Prove before merge, and the sweep rows

`ruff` clean; full suite `-n auto` forward and `BB_REVERSE=1`; `node site/mock/check.mjs` ok (routes
stay 150 — say so); `python -m black_bloc` NOT booted in a worktree — say so. Sweep rows lettered
`LG-a…` in `docs/access/sweeps.md`: the Health tab on https://blackbloc.heygabi.ai/health.html (or
wherever loop health renders — read `api/tools/` and name the page) shows every loop running after
the deploy; `/poll` ▸ Settings ▸ polls **off** → the dashboard's Create-a-poll form refuses in a
sentence. Code notes: `# Loop guard` at the foot of `code-notes.md`, keyed by name. Add a
`## Deviations` section to this file for anything that differed, and why.
