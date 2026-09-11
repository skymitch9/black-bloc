# The Logs button's two knobs, as buttons — design

> **Audience:** the build agent and reviewers. **Status:** TRACKED, ✅ **LIVE as v96** — branch
> `logs-buttons`, merge **`42d2e6e`**, deployed **2026-09-06 11:39** Phoenix (`../deploys.log`);
> landing entry in [`../DONE.md`](../DONE.md) (*"Logs buttons … and Create-a-recurring-poll from the
> website … shipping as v96"*). ⚠️ **Never met Discord** — no test can click a Discord button
> ([`../access/testing.md`](../access/testing.md)); the owner's by-eye rows are **305–309** in
> [`../access/sweeps.md`](../access/sweeps.md) (they were lettered `LB-a`–`LB-e` in this document;
> renumbered at the merge). Owner decision **2026-09-06
> 11:00**, verbatim: *"3. B"* — answering "every panel's Logs button dropped the old `count` /
> `important_only` options: (a) a modal first, (b) `Show more` + `Important only` buttons ON the
> list, (c) leave it". So: the list shows first, and refines after.
>
> **Last verified: 2026-09-11 08:29** (the header; the body is as at the build). Measured this pass
> against `main` at `f3ae743` (v108 live): `black_bloc/logs_panel.py` exists with `MORE` /
> `ONLY_IMPORTANT` / `EVERYTHING`, `LogsPanel(Panel)`, `buttons_for`, `refresh`, `panel_for`;
> `actionlog.py` has `lines_for`, `recent_lines`, `logs_embed`, `send_logs`; `send_logs` still has
> **18 call sites** (`grep -rn "send_logs(" black_bloc` → 19 lines, one of them the `def`);
> `settings_store.py` holds `LOGS_MIN = 1`, `LOGS_MAX = 50`, `LOGS_DEFAULT = 10`, `LOGS_COUNT =
> "logs_count"`, `LOGS_IMPORTANT_ONLY = "logs_important_only"` and `SETTINGS_PANEL_MINUTES =
> "settings_panel_minutes"` (which `logs_panel.py` imports). ⚠️ **NOT checked this pass:** anything in
> Discord or a browser — no button was pressed, no page was opened, the bot was not booted. Before
> that, **2026-09-06 11:05** — every `path:name` below was read in the tree at `c29b007` (v94 code).

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
the core-settings count before/after; routes stay 149 unless a settings route enumerates keys — the
mock is at **150** since v96, and the one added route came from the `recur-web` build merged the
same morning, not from this one; it is **150** still at v108);
`python -m black_bloc` NOT booted in a worktree — say so. Sweep rows lettered `LB-a…` in
`docs/access/sweeps.md` (**renumbered 305–309 at the merge**): `/poll` ▸ **Logs** shows 10 lines with `Show more` and `Important only`
under it; `Show more` → 20, then 30 … and the button goes away at 50 or when the log runs out;
`Important only` flips to `Show everything` and the list shrinks to refusals/errors/staff moves;
Dashboard → settings.html → `logs_count` 25 → the next Logs press starts at 25. Code notes:
`# Logs panel` at the foot of `code-notes.md`, keyed by name. Add a `## Deviations` section to
this file for anything that differed, and why.

## Deviations

Built on branch `logs-buttons`, off `main` at `b428236`, in a worktree at
`C:/lcw/bb-logs-buttons`. **Status: ✅ LIVE v96 — merged `42d2e6e`, deployed 2026-09-06 11:39.**
§2–§5 were built as written except for the following.

1. ⚠️ **`site/mock/contract.json` was edited, though the build was told to stay out of it.** Two
   lines: `settings.min.logs_count = 1` and `settings.max.logs_count = 50`. A bounded registry key
   cannot be added without them — `tests/api/test_contract.py` asserts the contract's `min`/`max`
   blocks EQUAL `KEY_MIN`/`KEY_MAX` (twice, once against the mock and once against the real
   router), and `site/mock/check.mjs` fails `has no logs_count row at all`. The alternative was to
   leave `logs_count` unbounded in the registry and keep clamping only inside the code, which §2.5
   rules out. The edit is in blocks a routes/pages change never touches.
2. **`LOGS_MIN` / `LOGS_MAX` / `LOGS_DEFAULT` moved from `actionlog.py` into `settings_store.py`**
   and are imported back. §2.5 wants the key bounded by them, and `settings_store` cannot import
   `actionlog`. Measured first: none of the three, nor `logs_embed`, had a reader outside
   `actionlog.py`.
3. **`actionlog.recent_lines` was split**, gaining `lines_for(rows, important_only)`. The panel
   must know how many ROWS came back to decide whether `Show more` is still true, and
   `recent_lines` answers a one-line placeholder for zero rows. Both callers now share one
   rendering; every existing caller of `recent_lines` is untouched.
4. **`logs_embed` was NOT given the shown count.** §3 said it "may take the shown count for its
   title if that reads well". It does not: the count is visible in the list itself, the title
   already says `— important only` when filtered, and a signature change would have been a second
   thing for the merge to reconcile for no gain.
5. **`send_logs` keeps its `count` / `important_only` keywords**, as `None` sentinels meaning
   *"ask the settings"*, rather than losing them. Nothing passes them (an AST guard in
   `tests/test_actionlog.py` pins all 18 sites at two positional arguments and no keywords), so
   deleting them was possible; keeping them costs one line each and leaves the override a caller
   might one day want.
6. **The `send_logs` tests are split across two files.** The two CONTRACT guards (the 18 call
   sites; the signature's `None` defaults) live in `tests/test_actionlog.py`, per the mirror rule.
   The four behavioural ones live in `tests/test_logs_panel.py` because what they assert is the
   panel, and they need its fakes. §4 put them all in `test_actionlog.py`.
7. **Three existing cog tests changed** — `test_polls.py::…answers_with_a_new_ephemeral_message`,
   `test_birthdays.py::…refuses_a_stranger`, `test_events.py::…keeps_its_own_staff_gate`. Each
   asserted the Logs button had not re-rendered its panel by reading a fake attribute
   (`interaction.rendered` / `.message` / `._edited`) that their harnesses also set inside
   `original_response()` — which `send_logs` now calls so a timed-out list can disable itself.
   The behaviour is unchanged; the assertions now read what the new message CARRIES.
8. **Two counting tests moved 22 → 23**
   (`tests/test_settings_panel.py:GROUP_COUNT`, `tests/test_settings_store.py::test_both_new_
   settings_keys_file_under_core_not_a_group_of_their_own`). The keys open a `logs` namespace,
   which is a new **Logs** section on the Settings page. They were NOT made core: `hide` and
   `emoji` are the precedent for a cross-cutting one-or-two-key group, and core membership would
   have moved `CORE_KEYS` in the contract and the mock as well. So the mock's core-settings count
   is **14 before and after**, per §2.5's "either answer is fine, say which".
9. **The timeout footer names a button, not a command** — *"This log has gone quiet — press Logs
   again"*. Every other panel's says *"run /x again"*; a Logs list is reached from eighteen panels
   and has no command of its own.
10. **`panel_for` reads `settings_store.SETTINGS_PANEL_MINUTES` directly**, not
    `settings_panel.PANEL_MINUTES_KEY` (they are the same string). The store is the home, and
    `settings_panel` imports half the app.

**Not verified:** anything against live Discord or the live dashboard. `python -m black_bloc` was
NOT booted — a worktree has no token — so no button has been pressed by a person, no ephemeral
edit has been made by a real client, and the new **Logs** section on `settings.html` has not been
opened in a browser. The sweep rows `LB-a`–`LB-e` — **numbered 305–309 at the merge** — are what
close that gap; as at 2026-09-11 nothing in `../access/sweeps.md`'s *Verified by the owner* table
records them as run.
