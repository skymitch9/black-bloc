# The Logs button's two knobs, as buttons — design

> **Audience:** the build agent and reviewers. **Status:** TRACKED. Last verified: **2026-09-06 11:05** —
> every `path:name` below was read in the tree at `c29b007` (v94 code). Owner decision **2026-09-06
> 11:00**, verbatim: *"3. B"* — answering "every panel's Logs button dropped the old `count` /
> `important_only` options: (a) a modal first, (b) `Show more` + `Important only` buttons ON the
> list, (c) leave it". So: the list shows first, and refines after.

## 1. What exists

- `black_bloc/actionlog.py:send_logs(interaction, feature, *, count=LOGS_DEFAULT,
  important_only=False, staff_only=True)` is **the one body** behind every feature's Logs button —
  18 call sites (`grep -rn "send_logs(" black_bloc`), every one passing only the feature name. It
  checks staff (`require_staff`), the database (`LOGS_DB_DOWN`), reads `recent_lines(db, guild_id,
  feature, limit, important_only)` and sends `logs_embed(feature, lines, important_only, origin)`
  ephemerally. `LOGS_MIN = 1`, `LOGS_MAX = 50`, `LOGS_DEFAULT = 10`.
- `recent_rows` already implements important-only (scans up to `SCAN_LIMIT` and keeps the
  `logkinds.IMPORTANT` kinds) — nothing new is needed in the query layer.
- `black_bloc/panels.py:Panel` is the ephemeral view base every panel inherits: minutes → timeout,
  `on_timeout` disables the buttons and writes a footer through the freshest interaction token.

## 2. Rules

1. **Still one body.** The 18 call sites do not change. `send_logs` grows a view; nothing else
   learns about counts or importance.
2. **Show first, refine after** — the buttons live UNDER the list, and each press edits the SAME
   ephemeral message (`interaction.response.edit_message(embed=…, view=…)`), never sends a second.
3. **Render only when valid:** `Show more` is not rendered (not merely disabled) once the shown
   count is at `LOGS_MAX` or the last read returned fewer rows than asked for (there is no more to
   show). The toggle's label is the move it would make: **`Important only`** while everything is
   shown, **`Show everything`** while filtered.
4. **Re-check on every press** (sweep row 290 precedent): staff and database are checked at press
   time, not trusted from render time; a lost right answers in words and changes nothing.
5. **Configurable both ways (checklist 33):** two keys in `settings_store.py`, with `KEY_HELP`
   sentences and labels in `site/public/assets/labels.js` (sweep 3's `NO_LABEL_YET` guard stays
   empty):
   - `logs_count` — int, default **10** (today's `LOGS_DEFAULT`), min `LOGS_MIN`, max `LOGS_MAX`:
     how many lines every Logs button starts with, and the step `Show more` adds.
   - `logs_important_only` — bool, default **False**: whether every Logs button starts filtered.
   `send_logs` reads both from `bot.store` for the guild, so a Lead who prefers a filtered 25-line
   view sets it once. Report the mock's core-settings count before and after (these may count as
   core; either answer is fine, say which).
6. **Timeout like a panel:** the view is a `Panel` subclass (`panels.Panel(minutes, footer=…)`)
   using the existing `core_panel_minutes`-style key if one fits the logs reply — read
   `panels.panel_minutes` callers and pick the key the Core panel uses; do NOT add a third key.
   On timeout the buttons disable and the embed footer says the panel went quiet, exactly as every
   other panel does.
7. **`allowed_mentions=none()` on every edit** (checklist 11); the embed already carries member
   mentions in log lines.

## 3. Where it lives

A new module `black_bloc/logs_panel.py` (every behaviour is its own module): `LogsPanel(Panel)`
holding `feature`, `count`, `important_only`, the two moves as module-level constants
(`MORE = "Show more"`, `ONLY_IMPORTANT = "Important only"`, `EVERYTHING = "Show everything"`), a
`refresh()` that re-reads lines and rebuilds the embed via `actionlog.logs_embed`, and
`buttons_for()` that returns only the valid ones. `actionlog.send_logs` builds it and passes it as
`view=`; `logs_embed` gains nothing but may take the shown count for its title if that reads well
(*"Poll logs — last 20 — important only"*).

## 4. Tests (mirror the package)

`tests/test_logs_panel.py` (new): `Show more` absent at the cap and when fewer rows came back;
label flips; a press re-reads with the new count/flag and edits in place; a non-staff press after
render answers in words and changes nothing; db-down press says `LOGS_DB_DOWN`.
`tests/test_actionlog.py`: `send_logs` starts from the two keys; the 18 call sites still pass only
the feature (a test that asserts the signature or a grep guard). `tests/test_settings_store.py`:
the two keys, defaults, bounds, help sentences; `labels.js` guard stays empty.

## 5. Prove before merge, and the sweep rows

`ruff` clean; full suite `-n auto` forward and `BB_REVERSE=1`; `node site/mock/check.mjs` ok (say
the core-settings count before/after; routes stay 149 unless a settings route enumerates keys);
`python -m black_bloc` NOT booted in a worktree — say so. Sweep rows lettered `LB-a…` in
`docs/access/sweeps.md`: `/poll` ▸ **Logs** shows 10 lines with `Show more` and `Important only`
under it; `Show more` → 20, then 30 … and the button goes away at 50 or when the log runs out;
`Important only` flips to `Show everything` and the list shrinks to refusals/errors/staff moves;
Dashboard → settings.html → `logs_count` 25 → the next Logs press starts at 25. Code notes:
`# Logs panel` at the foot of `code-notes.md`, keyed by name. Add a `## Deviations` section to
this file for anything that differed, and why.
