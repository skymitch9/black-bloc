# Birthdays — `/birthday` is ONE command that opens a panel

> 🔴 **2026-09-20 (branch `events-group`, off `main` `5ea8d44`): the BIRTHDAY BOT IMPORT is gone,
> whole** — owner, *"in bvirthdays remove the import from birthday bot, its been kicked"*. This
> document's *"Five strings and `report_lines` name retired commands and are rewritten"* is
> history: ~~`report_lines`~~ is DELETED along with the rest of the importer, and `NOBODY_YET`
> no longer promises that *"the Birthday Bot list is brought over automatically once a day"*.
> Every other birthdays behaviour in this document is unchanged. Retirement banner and the full
> deletion list: [`phase5-design.md`](phase5-design.md).
>
> **Audience:** the build agent and the reviewer. **Status:** TRACKED · ✅ **LIVE** — built on
> `worktree-agent-a19bdce15408f8243` (2026-09-03; branched from `main` at `d3da02c`), Fable-reviewed
> with no defect found, merged `58974e1` 13:47, **live since v63** (`616adb3`, 2026-09-03 13:58;
> `deploys.log` line 62). Still live at **v108** (`73e2e44`, 2026-09-11 00:37).
> See the `## Deviations` foot for every departure.
>
> **Since then, four things this document predates:**
> 1. **v78** (`3429233`) — `HIDDEN_WHEN_OFF` grew to fourteen entries, so `birthday_mode:
>    ("birthday",)` EXISTS now (`command_visibility.py:20`). §E's *"`command_visibility` has no
>    birthday entry"* is history: `/birthday` DOES vanish while the mode is off, behind
>    `hide_commands_when_off`.
> 2. **v84** (`ce97de0`) — `LOG_LEVEL_COMMANDS` was corrected for all 17 features and
>    `log_level_help` now renders *"and in `/birthday` ▸ **Logs**"*, which closes deviation 9's
>    finding (and `/request`'s twin).
> 3. **v88** (`794d3aa`) — deviation 2's three confirms now go through the library:
>    `cogs/community/birthdays.py:592 open_confirm` wraps `panels.confirm` + `confirm_items`
>    (`:63–68`), not a local builder.
> 4. **v92** (`4b327cf`) — deviation 14's finding was repaired: `cogs/community/requests.py` passes
>    `allowed_mentions` on its re-renders (`:176`, `:257`, `:625`, `:653`, `:657`).
>
> **Last verified: 2026-09-11 08:41** — re-measured in this tree at `1d090e5`: all three §D keys are
> registered (`birthday_panel_minutes`, `birthday_panel_next_for_members`, `birthday_panel_lookup`)
> in a **202**-key registry; the labels §B/§C name still read the same strings — `SET_MINE` /
> `CHANGE_MINE` / `OPT_OUT` / `OPT_IN` (`birthdays.py:466–470`), `LOOKUP_PLACEHOLDER` /
> `MONTH_PLACEHOLDER` / `MODE_PLACEHOLDER` (`:58–61`), **Clear the birthday role** / **Set their
> birthday** / **Forget their birthday** (`cogs/community/birthdays.py:846`, `:871`, `:883`); the
> tree is **29** top-level commands with zero Groups (`tests/test_bot.py:11`), `LOGS_GROUPS` is gone
> as §E asked, and `"birthday"` is still in `MEMBER_COMMANDS` (`:44`). Sweep rows landed as
> **87–93** (`docs/access/sweeps.md` ▸ *Birthdays — `/birthday` is ONE panel (wave 1). Live in v63*);
> the file now runs to row **350**.
> ⚠️ **NOT checked in this pass:** anything in a Discord client or a browser; no boot, no pytest, no
> ruff, no `check.mjs`. The `path:line` keys in §A–§F are the `59ac96f` ones and have drifted —
> trust the anchor text, and `code-notes.md`'s `# Birthdays panel (wave 1)` section for current keys.
>
> **Before that, 2026-09-03** — `ruff check .` clean and **3500 tests pass** on the branch
> (3442 at `d3da02c`: +76 new, −19 command tests replaced by panel tests). `commands synced`
> was measured at **44, unchanged**, by
> `tests/test_bot.py::test_the_command_tree_stays_inside_discords_limits`, which loads every cog
> and counts the real tree. Every `path:line` in §A–§F was read at `59ac96f` and is history now;
> the live keys are in `code-notes.md`'s `# Birthdays panel (wave 1)` section.
> ⚠️ **NOT verified:** anything against live Discord — no boot (this build has no bot token), no
> panel opened by a person, no modal submitted, no DM sent, no timeout footer seen. The sweep,
> the daily import and the birthday role were not exercised beyond the existing tests.
> ✅ The `code-notes.md` rows for the birthdays **cog** drifted after `:300` (its `:308` said
> `loop_health`, which was at `:300`; its `:624` lock note was at `:673`) — **that whole section
> was re-keyed by anchor in this build**, 30 keys, per the standing merge-order rule.
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
command; `command_visibility` has no birthday entry (grep: none — ⚠️ **since v78 it does**,
`birthday_mode: ("birthday",)`, so the command hides while the mode is off); `/help` follows the tree
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

Written by the build agent, 2026-09-03, on `worktree-agent-a19bdce15408f8243`. Everything not listed here
was built as this document specifies.

1. **`forget_birthday` takes an optional `member`; §F's signature was `(cog, guild, actor)`.**
   §B requires the person card's **Forget their birthday** to call `forget_birthday` "for the
   target", which that signature cannot express. It is
   `forget_birthday(cog, guild, actor, member=None, *, source="self")`, defaulting to the
   actor, and `source` rides into the log row's details so a staff removal is distinguishable
   from a member's own. The log row also carries `target=` — the retired `/birthday remove`
   logged an actor and no target, which was fine when only you could remove your own.
2. **`Forget their birthday` asks first, like `Remove` does.** §B calls it "(danger, confirm)"
   and then lists only three screens, none of them a forget-confirm. There are **four**: panel,
   person card, remove-confirm, forget-confirm, role-clear-confirm — five counting the last.
   All three confirms share one builder (`open_confirm`), because they differ only in a
   sentence and two buttons. ✅ **Since v88** that builder is the library's:
   `open_confirm` (`cogs/community/birthdays.py:592`) wraps `panels.confirm` +
   `panels.confirm_items`, which replaced eight hand-rolled copies across the app.
3. **`Status` answers a NEW ephemeral message rather than re-rendering the panel.** The §C
   followup/re-render table does not list `Status` at all. It is a report, not a move, and the
   panel is more useful still on screen behind it — the same shape `Logs` and `List a month…`
   already have.
4. **`stored_line` was extracted, and §F does not list it.** The stored/opted-in/imported/self
   sentence is shown by BOTH the staff panel's counts block (§B) and `status_lines` (§F); one
   home rather than two literals is checklist 15. It is four lines of pure code with its own
   assertion inside the `status_lines` test.
5. **`card_lines` shows the stored YEAR only on your own block.** §B asks for "the year in
   brackets when stored" in **Your birthday**, and §F gives `card_lines` one signature for both
   that block and somebody else's card. `mine` decides: your own block gains ` (1987)`, their
   card renders exactly what `/birthday show` rendered before. `birthday_show_age` already
   governs whether an *age* is public and is untouched; the year is the raw fact behind it.
   `mine` also switches the opted-out sentence between "You are" and "They are".
6. **The panel strings live in `black_bloc/birthdays.py`, not the cog.** §B and §C name them
   without saying where. The precedent is `requests.py` (pure) holding `PANEL_TITLE`,
   `PANEL_INTRO`, `PANEL_TIMEOUT_FOOTER`, so the new panel strings went there;
   `NOT_STORED`/`OPTED_OUT`/`NOBODY_YET`/`REMOVED`/`ALREADY_OPTED` and the two role sentences
   stayed in the cog, where they already were, so the rewrite of the five command-naming
   strings is a one-line diff each rather than a move plus a rewrite.
7. **`black_bloc/birthdays.py` now imports `black_bloc/panels.py`** (for `panel_minutes`
   alone), which pulls `discord` into a module `code-notes.md` calls "the decisions, with no
   Discord in them". It is the same edge `black_bloc/requests.py:508` already has, it is not a
   cycle, and the module still handles no Discord object. Noted because the section heading now
   overstates its purity.
8. **`commands synced` is 44 and was NOT read off a boot.** §H item 1 asks for
   `python -m black_bloc`; this build has no bot token, so the number comes from
   `tests/test_bot.py::test_the_command_tree_stays_inside_discords_limits`, which builds the
   real bot, loads every cog and asserts `len(tree.get_commands()) == 44`. That is a
   measurement of the same object the boot would print, taken offline. The same substitution
   was accepted for wave 0 (its deviation 5). ⚠️ **Two sibling wave-1 builds are changing this
   number in parallel** — events retires `/timezone`, so 44 → 43 there; on THIS branch it is
   44, and the assertion will need re-measuring at the merge.
9. **`LOG_LEVEL_COMMANDS["birthday"]` was left alone, and it now renders a sentence naming a
   retired subcommand.** `settings_store.py:787` maps the feature to `/birthday`, and
   `log_level_help` renders "and in `/birthday logs`" into `birthday_log_level`'s help text.
   §E says the entry "still names a real command", which is true — but the help *sentence* now
   points at a Logs button. ⚠️ **`/request` has exactly the same defect since its own panel
   shipped**, so fixing one and not the other would be worse than fixing neither; it is
   recorded here as a finding for the conductor rather than repaired in a birthdays branch.
   ✅ **Fixed at v84** (`ce97de0`): `LOG_LEVEL_COMMANDS` was corrected for all 17 features and
   `log_level_help` now renders *"and in `/<command>` ▸ **Logs**"* — the sentence names the
   button, so both this and `/request` read correctly.
10. **§H item 3's `node site/mock/check.mjs` and the `labels.js` parse were NOT run.** No site
    file is touched by this build (grep: no `site/` change in the diff), and the design's own
    §E lists no site edit. The full `pytest -q -n auto` and `ruff check .` WERE run and are
    green.
11. **§H item 2 is proved, and so is more than it asks.** The parametrised test walks all three
    reachable `(has_date, opted_out)` states through the real command and asserts the row's
    labels **and nothing else**; the pure test adds the unreachable `(False, True)` and asserts
    it falls back rather than raising. `is_staff` is covered by separate tests rather than a
    third parametrise axis, because a staff panel differs by seven controls and asserting that
    as a parametrise case reads worse than as its own test.
12. **The `Refresh` button is on row 0 with the moves, as §B's table says — which means a
    member with nothing stored sees a two-button row.** Worth stating because it looks sparse
    beside the four-button rows; it is the table, not an omission.
13. **19 command tests were rewritten rather than kept.** They drove `cog.set_mine.callback`,
    `cog.show.callback` and nine other retired subcommands, so there was nothing to keep. Every
    behaviour they asserted has a panel-shaped replacement, and the two role-handback tests
    (Phase 5 review finding 3) now call `forget_birthday` / `change_opt` directly, which is
    what the buttons call. 3500 tests pass on the branch.
14. **Every re-render passes `allowed_mentions=none()`, which the shipped requests panel does
    NOT.** The panel embed interpolates `<@id>` (the coming-up list) and arbitrary display
    names, which is checklist item 11. Embeds do not raise notifications and the message is
    ephemeral, so this is belt-and-braces rather than a repaired defect — but the retired
    `/birthday next` passed it explicitly on its content, and dropping it silently would have
    been a regression in intent. A test pins it on the first send and on a re-render.
    ⚠️ **The same three edits in `cogs/community/requests.py` (`render_panel`, `open_card`,
    `finish_card`) pass no `allowed_mentions`** — recorded as a finding for the conductor, not
    repaired in a birthdays branch.
    ✅ **Repaired at v92** (`4b327cf`, *"`allowed_mentions` on 27 re-renders + 3 confirm cards"*):
    `cogs/community/requests.py` passes it at `:176`, `:257`, `:625`, `:653` and `:657`.

## Follow-up 2026-09-23 — post today's wishes by hand (branch `birthday-post-today`)

Owner, verbatim: *"can we add a birthday command to post the days birthdays? that way they can
be manually triggered"*. Not deployed. Measured the same day: a birthday set mid-day already
posts on the next five-minute tick by itself (Anarchy, set 12:29, posted 12:31), so the manual
trigger is for reposting after a deploy or restart swallowed one, posting again on purpose, or
posting NOW instead of waiting for the tick.

**The door.** `post_today(bot, guild, actor, *, again, via)` (`cogs/community/birthdays.py`) is
the one path both surfaces call. For every stored birthday it takes the member's lock, re-reads
the row, and — when the member is opted in and it is their birthday today in THEIR zone — runs
the same `_celebrate` the sweep runs. It answers a `PostedToday` (`black_bloc/birthdays.py`)
whose `said` is the sentence both surfaces show, and writes one `birthday.posted_now` row
(ROUTINE; `web.birthday.posted_now` from the site) with `{via, again, posted, skipped, missing,
failed, mode}`. The per-member `birthday.announce` / `would_announce` / `announce_failed` /
`member_missing` rows land exactly as the sweep's do.

**The two moves.**

| Move | What it does |
|---|---|
| **Post the ones not sent yet** (`again=False`) | the sweep, now: a birthday already stamped `last_announced_on` today is counted *skipped* and left alone |
| **Post them all again** (`again=True`) | everybody with a birthday today is wished, the already-wished included; the log row says `again: true` |

**Decisions.**

1. **No new slash command.** The owner said "command"; the standing rule (2026-09-03, minimise
   slash commands) puts it on the `/birthday` panel as a staff button, row 4 beside Status /
   Clear the birthday role / Logs, opening the panel's `open_confirm` card with the two moves and
   **Cancel**. The site puts it in the Birthdays page's page-head aside, which was empty
   (`ux-audit.md` finding 1); the button unfolds the question and the two moves inline.
2. **The button shows even when nobody has a birthday today** — staff must be able to check —
   and the answer then says so in words (`birthday_post_nobody`).
3. **`off` refuses in words** and says how to switch it (`birthday_post_off`); the site answers
   409 `birthdays_off` carrying that sentence. The `posted_now` row is still written with
   `mode: off`, so a refused press is visible in Logs.
4. ⚠️ **`shadow` posts a rehearsal copy by hand, but the sweep's shadow stays log-only.** The
   door passes `rehearse=True` to `_celebrate`, which in `shadow` posts the wish, with the
   `rehearsal_note` line above it naming the real channel, to the rehearsal home
   `shadow.channel_id` resolves (`shadow_channel_id`, else the guard's channel, else
   `log_channel_id`) and logs `birthday.would_announce` with `rehearsed: true`. The five-minute
   sweep was NOT changed: in `shadow` it still posts nothing anywhere —
   changing it would start a daily rehearsal post nobody asked for. Because the sweep's shadow
   stamps the row announced, **Post the ones not sent yet** in shadow usually reports them
   *skipped*; **Post them all again** is what rehearses them.
5. **Every word is a key** (11 `birthday_post_*` text keys, `settings_store.py`
   `BIRTHDAY_POST_WORDS`), each with help, a placeholder check (`{n}`, `{n}`+`{channel}`, or
   none) and a `labels.js` line. The `birthday` group went 10 → 21 keys, under Discord's 25-option
   select cap for one group on `/settings`. The confirm card's **Cancel** is the same unkeyed
   library word the role-clear confirm already uses — not a new string.
6. **The channel is named as `#name`** on both surfaces (`channel_words`), because the site
   would print a raw `<#id>`.

**Not verified.** Nothing here met live Discord or the live site: the panel path is proved by
fakes in `tests/cogs/community/test_birthdays.py`, the route by the TestClient, and the page
was clicked through in headless Chrome against the mock (open, **Post them all again**, the
off refusal) — never against the real API or a real guild. Whether Discord renders the
rehearsal note plus embed as intended in `#welcome-test` is unseen.
