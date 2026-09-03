# Birthdays — `/birthday` is ONE command that opens a panel

> **Audience:** the build agent and the reviewer. **Status:** TRACKED · **PLANNING** (wave 1).
> **Last verified: 2026-09-03** against `59ac96f` — every `path:line` below was read at that
> commit (the two birthdays modules, `panels.py`, `settings_store.py`, `api/tools/birthdays.py`,
> `tests/test_bot.py`, `docs/access/sweeps.md`).
> ⚠️ **NOT verified:** anything against live Discord (no boot, no token); no test was run and no
> code written — design only. The `code-notes.md` rows for the birthdays **cog** drift after
> `:300` (its `:308` says `loop_health`, which is at `:300`; its `:624` lock note is at `:673`) —
> the build re-keys that section, per the standing merge-order rule.
>
> **Inherits every invariant in [`panels-program.md`](panels-program.md) §2 (P1–P17) and the §4
> library — none restated here.** Template: [`requests-panel-design.md`](requests-panel-design.md),
> whose `## Deviations` foot lists the traps this avoids (1 defer-then-edit, 5 the 5-per-row cap,
> 7 `commands synced` does not drop, 9 `retire`, 10 the 15-minute footer, 11 `still_staff`).
> Feature behaviour — the sweep, the role, the daily import — is
> [`phase5-design.md`](phase5-design.md) and is untouched here.

## A. What is there today (measured at `59ac96f`)

`/birthday` is a `Group` (`cogs/community/birthdays.py:307`) with **eleven** subcommands plus a
nested `role` group (`:308`) holding one — **twelve** in all.

| Subcommand | Line | Who | What it calls · what is inline |
|---|---|---|---|
| `logs` | `:607` | staff | `send_logs(interaction, "birthday", count, important_only)`; `send_logs` carries its own `require_staff` (the requests template proved this, deviation 11) |
| `set` | `:620` | member | `_store_for(…, "self")`; month/day/year arrive as `app_commands.Range` options (`:629–631`) |
| `set-for` | `:637` | **staff** (`require_staff` `:652`) | `_store_for(…, "staff")` |
| — `_store_for` | `:658` | — | **inline:** `date_problem`/`year_problem` gate (`:668`), `clamp_month_day` (`:672`), per-user lock + `save_birthday` (`:673`), **the confirmation sentence built in place** (`:679–687`), `log_action("birthday.set")` (`:688`) |
| `remove` | `:697` | member | **inline:** lock → `get_birthday` → `NOT_STORED` → `_return_role` (`:706`) → `delete_birthday` → `log_action("birthday.remove")` |
| `optout` / `optin` | `:713` / `:717` | member | `_change_opt` (`:721`) — **inline:** `NOT_STORED`, the `ALREADY_OPTED` no-op, `set_opted_in`, `_return_role` on opt-out, `log_action` |
| `show [@user]` | `:747` | **member, for anybody** | `get_birthday` + `next_occurrence` + `age`; **the three lines are built inline** (`:772–778`) |
| `next` | `:783` | **member** | `rows_for_guild` filtered on `opted_in` (`:787`), `upcoming(…, limit=NEXT_LIMIT)`; **lines inline** (`:802–807`) |
| `list [month]` | `:814` | **staff** (`:825`) | `rows_for_guild`; **month grouping inline** (`:838–847`); `chunked` (`:190`) → first page answers, rest are ephemeral followups (`:848–855`) |
| `mode` | `:857` | **staff** | `store.set("birthday_mode")` + `log_action("birthday.mode")` (`:869–881`) |
| `role clear` | `:883` | **staff** | `store.clear("birthday_role_id")` + `log_action("settings.clear")` (`:889–903`) |
| `status` | `:905` | **staff** | `stored_counts` (`:172`); **twelve lines inline** (`:917–932`) |

**Member state that decides buttons** — three booleans, nothing else:

| Name | How it is derived |
|---|---|
| `has_date` | `await get_birthday(bot.db, actor.id) is not None` (`:98`) |
| `opted_out` | `has_date and not row["opted_in"]` |
| `is_staff` | `bot.store.is_staff(actor)` (`settings_store.py:1448`) |

**Shared with the website — do not move or rename** (measured): `api/tools/birthdays.py:17–25`
imports `delete_birthday`, `import_rows`, `members_of`, `report_lines`, `rows_for_guild`,
`save_birthday`, `set_opted_in` from the cog module; `api/tools/members.py:10` imports
`members_of`; `chat_data.py:9` imports `rows_for_guild`.

## B. The design — one `/birthday`, one panel

One ephemeral message: embed + `Panel` subclass (`panels.py:67`). Both panels come from
`build_panel(bot, guild, actor)`, split on `is_staff` exactly as `requests.py:454` does. Colour is
`discord.Colour(parse_color(store.get(guild.id, "birthday_color")))` (`birthdays.py:206`) so the
panel and the wish embed are one look.

**Embed, in order** — every block is a line, never a dead control (P9):

| Block | Shown to | Content |
|---|---|---|
| Intro | everyone | one sentence: what the panel is |
| Mode warning | everyone, when `birthday_mode` is `off`/`shadow` | "nothing is posted yet" in words — a member who sets a birthday deserves to know |
| **Your birthday** | everyone | the date **as stored** (`month_day_text`, `birthdays.py:373`), the year in brackets when stored, `Next: <t:D> (<t:R>), midnight in **<zone>**` — the same three lines `show` builds today (`:772–778`), extracted; plus the opted-out line when `opted_out` |
| — when `not has_date` | everyone | the `NOT_STORED` sentence, rewritten to name the **button**, not `/birthday set` |
| **Coming up** | everyone if `birthday_panel_next_for_members`, else staff | the `next` list, `NEXT_LIMIT = 5` (`:51`), opted-out rows already filtered by `:787`; when empty, `NOTHING_UPCOMING` (`:76`) |
| Counts | staff | `stored_counts` (`:172`) — stored · opted in · imported · set by the person |

**Controls.** Buttons render only when the move is valid (P3); a staff panel fills **all five of
Discord's rows**, so any later control needs a sub-panel, not a sixth row (template deviation 5).

| Row | Control | Shown to |
|---|---|---|
| 0 | `Set my birthday` / `Change my birthday` · `Remove` · `Opt out` **or** `Opt in` · `Refresh` | everyone, per §C |
| 1 | `UserSelect` "Look someone up…" | everyone when `birthday_panel_lookup`, else staff only |
| 2 | `Select` "List a month…" — `Every month` + the twelve `MONTH_NAMES` (`birthdays.py:37`), 13 options | staff |
| 3 | `Select` "Wishes are…" — the three `BIRTHDAY_MODES` (`settings_store.py:94`), the current one marked default | staff |
| 4 | `Status` · `Clear the birthday role` · `Logs` | staff |

**Screens** (each a re-render in place, `retire(previous)` first — P6): **panel**; **person card**
(from the UserSelect — their date / next / opted-out lines from the same extracted builder,
`Back`, and for staff `Set their birthday`, `source="staff"`, and `Forget their birthday`
(danger, confirm) — no slash command does that today but the website does
(`DELETE /api/birthdays/{user_id}`, `api/tools/birthdays.py`), so this is the Discord path to an
existing move, not an invented one (P4), and the owner's rule of 2026-09-03 — **staff always get
the final say and the permission** (`CLAUDE.md`) — requires it. It calls `forget_birthday` for the
target (`source="staff"`, log row `birthday.remove` naming the actor) and DMs the member one
sentence; **staff cannot opt somebody out** — that is the member's own choice and no surface does
it); **remove confirm** (`Yes, forget it` / `Keep it`, the shape of `open_withdraw_confirm`,
`requests.py:570`); **role clear confirm** (`Yes, clear it` / `Cancel`, answering the unchanged
`ROLE_CLEARED` / `ROLE_NOT_SET`, `:79`, `:83`).

## C. The button table, as data

`PANEL_BUTTONS: dict[tuple[bool, bool], tuple[PanelButton, ...]]` in `black_bloc/birthdays.py`,
keyed `(has_date, opted_out)`, read by `panel_buttons(has_date, opted_out)` — the shape of
`requests.py:385/392/419` (`MoveButton` / `CARD_BUTTONS` / `card_buttons`). Staff extras are a
separate constant, appended, never interleaved.

| `has_date` | `opted_out` | Row 0 renders |
|---|---|---|
| `False` | `False` | `Set my birthday` (primary, modal) · `Refresh` (secondary) |
| `True` | `False` | `Change my birthday` (primary, modal) · `Remove` (danger, confirm) · `Opt out` (secondary) · `Refresh` |
| `True` | `True` | `Change my birthday` · `Remove` · `Opt in` (success) · `Refresh` |

`(False, True)` is unreachable — `opted_out` is defined as `has_date and …`; the parametrised test
asserts it maps to the `(False, False)` row rather than raising.

**Modals.** One `DateModal`, one text input, used by both the self path and the set-for path:

| Field | Value |
|---|---|
| Title | `Your birthday` / `Set <display_name>'s birthday`, **clamped to Discord's 45-character modal-title cap** |
| Label | `Your birthday — MM-DD, or MM-DD-YYYY` |
| Placeholder | `09-15   or   09-15-1994` · `max_length=10` · required · prefilled with the stored date when there is one |

Validation, in order, reusing today's exact sentences:

| Step | Function | Sentence |
|---|---|---|
| 1 | `parse_birthday_input` (**new**, pure) | unreadable → the one new string, `DATE_UNREADABLE`: names the two shapes and gives `09-15` as the example |
| 2 | `date_problem(m, d)` (`birthdays.py:122`) | its three sentences **verbatim** ("There is no month **13**…", "**February** has no day **30**…") |
| 3 | `year_problem(year, today)` (`:140`) | its two sentences verbatim. ⚠️ The retired option used `Range[int, 1900, 2200]` (`:631`) while `year_problem` refuses anything after `today.year` — the modal keeps `year_problem`, so the effective rule is unchanged and the dead 1901-year gap in the Range disappears |
| 4 | `clamp_month_day` (`:110`) then the shared store path | the confirmation sentence, extracted from `:679–687` |

`parse_birthday_input(text)` accepts `-`, `/`, `.` and space as separators, two or three numeric
parts, and returns `(month, day, year|None)` or `None`. It never guesses: two parts means no year.

**Followup or re-render** (P5 — every click defers first, then `edit_original_response`; a select
that opens a modal must **not** defer, since a deferred interaction can no longer send one):

| Action | Then |
|---|---|
| Set / Change / Set-for (modal submit) | shared store path → **re-render** the panel (or the person card) + one-line followup |
| Remove, Opt out, Opt in, Role clear | shared path → **re-render** |
| `Refresh`, `Back`, `Look someone up…` | **re-render** |
| Mode select | shared path → **re-render** (the mode line and the warning both change) |
| `List a month…` | **followup(s)** — `chunked` pages as ephemeral messages, as `:848–855` does today; the panel stays |
| `Logs` | **followup** — `send_logs(interaction, "birthday")` (P11). ⚠️ The button loses the `count` and `important_only` options the subcommand had (`:608–617`) — the same loss `/request` accepted |

⚠️ **`capped_placeholder` (`panels.py:55`) is not used by this panel.** A `UserSelect` is not
option-capped by us, and the month select is 13 of a possible 25 — P10 has nothing to bite on
here. The reviewer should expect its absence, not a missing call.

## D. Settings (P13 · checklist 33)

Three keys, registered in the three places `request_panel_minutes` is — a **new
`KEY_TYPES.update({...})` / `KEY_HELP.update({...})` block of its own** beside `settings_store.py:872`
and `:881` so parallel wave-1 branches merge textually, and a `default()` branch beside the
birthday block at `:1255–1266`.

| Key | Type | Default | What it decides |
|---|---|---|---|
| `birthday_panel_minutes` | `int` | **10** | how long the panel stays live. Help text carries the same warning `request_panel_minutes` does (`settings_store.py:892–897`): the "gone quiet" footer can only be written inside Discord's 15-minute interaction window, so 15+ means the buttons stop with nothing to explain it (KI-20). Nothing is clamped |
| `birthday_panel_next_for_members` | `bool` | **True** | whether a member sees the "Coming up" list. **True is today's behaviour** — `/birthday next` (`:783`) has no `require_staff`. False makes it staff-only and the embed says so in words |
| `birthday_panel_lookup` | `bool` | **True** | whether a member may look up somebody else's stored birthday. **True is today's behaviour** — `/birthday show @user` (`:747`) has no `require_staff`. False hides the UserSelect from members; staff keep it. See fork **F-B1** |

Not decisions, so not keys: the button table, the five-row layout, `NEXT_LIMIT`, the 13 month
options. The six existing `birthday_*` keys (`:199–204`, `:563–568`) are untouched.

## E. What goes away

| Goes | Anchor |
|---|---|
| the `birthday` `Group` and the nested `birthday_role` group | `cogs/community/birthdays.py:307`, `:308` |
| all twelve subcommands | the §A table |
| `LOGS_GROUPS["birthday"]` | `tests/test_bot.py:14` — `/birthday` is no longer a `Group` with a `logs` child, so the loops at `:181` and `:227` would `KeyError` |
| `tests/test_bot.py::test_the_command_tree_stays_inside_discords_limits` (`:196`) | recount: **`commands synced` stays 44** (a Group already held one top-level slot — template deviation 7); the tree loses 12 children and one nested group |

**Unchanged, checked:** `MEMBER_COMMANDS` still contains `birthday` (`tests/test_bot.py:64`);
`LOG_LEVEL_COMMANDS["birthday"] = "birthday"` (`settings_store.py:787`) still names a real
command; `command_visibility` has no birthday entry (grep: none); `/help` follows the tree
(`cogs/core.py`), so it needs no edit (P15).

**Strings that name a retired command and must be rewritten in the same commit** — each currently
tells somebody to run something that will not exist:

| String | Line | Names |
|---|---|---|
| `NOT_STORED` | `:56` | `/birthday set` |
| `NOT_STORED_FOR` | `:61` | `/birthday set`, `/birthday set-for` |
| `OPTED_OUT` | `:65` | `/birthday optin`, `/birthday remove` |
| `NOBODY_YET` | `:71` | `/birthday set` |
| `report_lines` | `:276`, `:280` | `/birthday set`, `/birthday set-for` — ⚠️ also rendered by the **website** import report (`api/tools/birthdays.py:121`), so the replacement wording must read correctly on a web page as well |

`ROLE_CLEARED` / `ROLE_NOT_SET` (`:79`, `:83`) name `/settings set-role birthday_role_id`, which
still exists — leave them.

**Docs rewritten in the same commit** (P15): `docs/access/sweeps.md:133–138` (names six retired
subcommands **and the already-deleted `/birthday import`** — stale today); `phase5-design.md:99–106`
gets a dated "superseded by the panel" line, not a rewrite; `architecture.md:167`, `:177`;
`phase12-design.md:76`; `access/site.md:234` (says the route "runs the same import `/birthday
import` does" — stale since 2026-08-27); `code-notes.md:810`, `:862`, `:865`, `:866`, `:1697` plus
the drifted cog section. `feature-list.md` and `access/OWNER_GUIDE.md` name **no** birthday
subcommand (grep: zero hits) — the OWNER_GUIDE gaining a `/birthday` line is an addition worth
making, not a rewrite.

## F. Extractions (P4)

**Pure, into `black_bloc/birthdays.py`** — no Discord, tested in `tests/test_birthdays.py`:

| New | Signature | Taken from |
|---|---|---|
| `parse_birthday_input` | `(text: str) -> tuple[int, int, int \| None] \| None` | new; replaces the `Range` options at `:629–631` |
| `PANEL_BUTTONS`, `panel_buttons` | `(has_date: bool, opted_out: bool) -> tuple[PanelButton, ...]` | new; mirrors `requests.py:392/419` |
| `stored_sentence` | `(whose: str, month, day, year, zone: str, when: datetime) -> str` | inline at `:679–687` |
| `card_lines` | `(name: str, month, day, year, zone: str, when: datetime, years: int \| None, opted_in: bool, mine: bool) -> list[str]` | inline at `:772–778` |
| `upcoming_lines` | `(entries: list[dict], items: list[Upcoming]) -> list[str]` | inline at `:802–807` |
| `month_lines` | `(rows) -> list[str]` | inline at `:838–847` |
| `status_lines` | `(values: dict[str, Any]) -> list[str]` | inline at `:917–932`; the cog gathers the values, the function only words them |
| `chunked` | moved as-is | `cogs/community/birthdays.py:190` — nothing outside the cog imports it (grep), so the move is safe; update the mirrored test's import |

**Cog-module async, staying in `cogs/community/birthdays.py`** — they touch `bot.db`,
`log_action` and the role, so they live where `apply_decision` lives for requests
(`cogs/community/requests.py:280`), not in the pure module:

| New | Signature | Taken from |
|---|---|---|
| `store_birthday` | `(cog, guild, actor, member, month, day, year, source) -> str` | `_store_for` `:658` |
| `forget_birthday` | `(cog, guild, actor) -> str` | `remove` `:697–711` |
| `change_opt` | `(cog, guild, actor, *, opted_in: bool) -> str` | `_change_opt` `:721–745` |
| `set_mode` | `(bot, guild, actor, mode: str) -> str` | `mode` `:869–881` |
| `clear_role` | `(bot, guild, actor) -> str` | `role_clear` `:889–903` |

Each returns the sentence to show and does **one** write and **one** log row. The per-user lock
(`:588`) and `_return_role` (`:576`) move with them — `remove`/`optout` handing the role back
first was review finding 3 of Phase 5 (`code-notes.md`) and must not be lost.
⚠️ **`save_birthday`, `delete_birthday`, `set_opted_in`, `rows_for_guild`, `report_lines`,
`members_of`, `import_rows` keep their names and their module** — the website imports all seven by
name (§A).

## G. Tests (P16 — one file per source file)

| File | Adds |
|---|---|
| `tests/cogs/community/test_birthdays.py` | `/birthday` answers ephemerally with a panel; **parametrised over every `(has_date, opted_out, is_staff)` tuple → exactly the row's controls and no others**; the mode warning; "Coming up" present/absent per key; the lookup select present/absent per key and always for staff; the person card and its staff-only `Set their birthday`; each button calls its extracted function (mock it) and re-renders; the date modal's four validation steps answer the exact sentences; a staffer demoted mid-panel moves nothing (`still_staff`, three sites); the Logs button answers a new ephemeral message and still refuses a demoted staffer; `List a month…` sends chunked followups and leaves the panel; timeout disables every item; a re-render retires the view it replaced; DB-down and DM gates in words |
| `tests/test_birthdays.py` | `parse_birthday_input` (both shapes, all four separators, garbage, `2-30`, `2-29`, year `2200`); `panel_buttons` for all four tuples incl. the unreachable one; `stored_sentence` / `card_lines` / `upcoming_lines` / `month_lines` / `status_lines`; `chunked` after the move |
| `tests/test_settings_store.py` | the three new keys round-trip and default (10 / True / True) |
| `tests/test_bot.py` | `LOGS_GROUPS` loses `birthday`; the tree-limit test recounts |
| existing sweep/import/role tests | stay green untouched — the wish loop, the daily import and the role are not touched by this design |

## H. §J — prove before merge (P17), and the sweep

1. `python -m black_bloc` boots; `commands synced` reads **44**, unchanged (deviation 7).
2. The parametrised test proves every state renders exactly its row and nothing else.
3. `ruff`, full `pytest`, `node site/mock/check.mjs`, `node --input-type=module --check <
   site/public/assets/labels.js` (the site is untouched; both are cheap).

**Sweep rows to add to `docs/access/sweeps.md` — this feature takes 87–93** (66–72 are reserved by
the two feature builds in flight, events takes from 73, polls from 80; the file's last row today
is 65 at `:180`). The prose block at `:133–138` is replaced by these rows.

| # | What |
|---|---|
| 87 | `/birthday` as a member with nothing stored — intro, `Set my birthday`, `Refresh`, no staff controls |
| 88 | `Set my birthday` → `09-15` → the date, the zone and the next occurrence appear; reopen and try `13-40` and `09-15-2200` → the exact refusal sentences |
| 89 | `Opt out` → the panel shows opted out and `Opt in` only; `Opt in` → back |
| 90 | `Remove` → confirm → forgotten; `Keep it` → untouched |
| 91 | staff: `Look someone up…` → their card → `Set their birthday` → modal → their card re-renders |
| 92 | staff: `List a month…` → the month's list as a followup (and a long month arriving as more than one); `Wishes are…` → `shadow` → the mode line changes |
| 93 | staff: `Status`; `Clear the birthday role` → confirm; `Logs`; then leave the panel `birthday_panel_minutes` minutes and check the "gone quiet" footer |

## I. Forks — the owner decides, one at a time

✅ **F-B1 — DECIDED by the owner 2026-09-03 12:20 ("Follow your choice"): keep today's
behaviour — `birthday_panel_lookup` defaults True.** Reasoning kept for the record: the
"Coming up" list already shows the next five to everyone, and `Opt out` is the member's own
privacy control, so the lookup reveals nothing a member did not choose to store. The same answer
sets polls' `poll_creator_may_end` default True. Original question:
May a member look up somebody else's birthday? Today `/birthday show @user`
(`:747`) is open to every member, and this design keeps that (`birthday_panel_lookup` default
**True**). But the owner made the analogous call the other way on requests three hours after it
shipped (deviation 12: viewing became staff-only, default **off**). Default True keeps today's
behaviour; default False matches the requests decision. Either way the key exists and the site
switches it — only the default is in question.

Nothing else here is a genuine fork: every other choice is settled by §2, by the template, or by
what the commands already do.

## Deviations

_Written by the build agent when the build lands. Everything not listed here was built as
specified._
