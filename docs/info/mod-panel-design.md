# Mod cases — `/mod [member]` is ONE command that opens a panel (wave 4)

> **Audience:** the build agent and the reviewer, and the owner for §I. **Status:** TRACKED ·
> **PLANNING — unbuilt.**
> **Last verified: 2026-09-05** — every `path:line` below was READ against `main` at
> **`46fba16`**. ⚠️ **`main` moved to `0fcbac2` while this was being written** — the
> `hide_commands_when_off` build merged (`437b2d1`, then the merge commit). **Re-measured against
> `0fcbac2`: `command_visibility.py`, `settings_store.py` and `tests/test_bot.py:179` only** — see
> §B's red block, which is the one section that changed and is now stated against the NEW file.
> Every other `path:line` below is against `46fba16` and was NOT re-read; the merge touched
> `black_bloc/command_visibility.py`, `docs/access/sweeps.md`, `docs/info/code-notes.md`,
> `docs/info/feature-list.md`, `tests/test_command_visibility.py` and
> `tests/cogs/content/test_chat_memory.py`, so **§E's `sweeps.md` / `code-notes.md` /
> `feature-list.md` line numbers are the likeliest to have drifted — trust the anchor text.**
> Files read, in `black_bloc/cogs/moderation/modcmds.py` (**773 lines**),
> `black_bloc/modcases.py` (**454**), `black_bloc/panels.py` (**219**),
> `black_bloc/api/tools/mod.py` (**297**), `black_bloc/storage/db.py`,
> `black_bloc/logkinds.py` (**464**), `black_bloc/command_visibility.py` (**214**),
> `black_bloc/actionlog.py` (**317**), `black_bloc/settings_store.py` (**1762**),
> `black_bloc/command_errors.py`, `tests/test_bot.py`,
> `tests/cogs/moderation/test_modcmds.py` (**596**), `tests/test_modcases.py` (**229**),
> `tests/api/tools/test_mod.py` (**302**), `site/public/assets/page-moderation.js` (**397**),
> `site/public/moderation.html` (**102**), `site/mock/server.mjs`, `site/mock/contract.json`,
> `site/mock/check.mjs`, `docs/access/sweeps.md` (**588 lines, last row 182**),
> `docs/access/OWNER_GUIDE.md`, `docs/info/feature-list.md`, `docs/info/architecture.md`,
> `docs/info/panels-program.md`, `docs/info/phase6-design.md`, `docs/info/code-notes.md`.
>
> **Measured, not assumed:**
> `tests/test_bot.py:179` asserts **36** top-level commands. `SCHEMA_VERSION = 28`
> (`storage/db.py:11`). `CASES_PER_PAGE = 10` (`modcases.py:28`) — the page size `/cases` AND
> `GET /api/mod/cases` already share. `HEADS["case"] = "mod"` **already exists**
> (`logkinds.py:51`), so a `case.*` kind classifies as the Moderation feature with no edit there.
> `command_visibility.HIDDEN_WHEN_OFF` now holds **fourteen** entries (`:16–31` at `0fcbac2`) and
> **none of them is moderation**, because there is no `mod_mode` anywhere in `KEY_TYPES` — see
> §B's red block on `hide_commands_when_off`.
> `docs/access/OWNER_GUIDE.md` names `/case` or `/cases` **nowhere** (zero matches).
> The website **cannot edit, note, void or restore a case today** — measured, §A.
> ⚠️ **NOT verified: anything was run.** No boot, no `pytest`, no `ruff`, no `check.mjs`,
> nothing against live Discord or the live dashboard. No migration was executed. The `path:line`
> keys will drift as the two sibling wave-4 designs (`honeypot-panel-design.md`,
> `modmail-panel-design.md`) and the in-flight `hide_commands_when_off` build merge — **trust the
> anchor text, not the number.**
>
> **Inherits every invariant in [`panels-program.md`](panels-program.md) §2 (P1–P17) and its §4
> library — none restated here.** Closest precedents: [`role-menus-panel-design.md`](role-menus-panel-design.md)
> (list → card → moves, and its 14-item `## Deviations` foot) and
> [`automod-panel-design.md`](automod-panel-design.md) (a staff-only moderation panel that reuses an
> existing pure module and an existing test file). Feature behaviour is
> [`phase6-design.md`](phase6-design.md) (F7).
>
> ⚠️ **This build changes how staff READ and CORRECT the case record. It changes nothing about
> how a case is MADE.** `warn_member` (`modcmds.py:232`), `timeout_member` (`:262`),
> `untimeout_member` (`:303`), `kick_member` (`:326`), `ban_member` (`:347`), `unban_member`
> (`:389`), `record_case` (`:114`), `refuse_in_test_mode` (`:161`), `note_failure` (`:200`) and
> the `purge` body (`:622`) are **untouched**, and the seven bare commands that call them stay
> exactly as they are (§B). One deliberate exception, argued in §I fork **F-M2**: `warn_count`
> (`modcases.py:351`) may learn to skip a voided warn, which changes a number
> `automod_warn_threshold` reads.

## A. Measured today — one group with one child, and two top-level commands

| Command | Line | Gate | What it does · what is INLINE in the cog |
|---|---|---|---|
| `/mod logs [count] [important_only]` | `:422` (group at `:417`, `default_permissions=STAFF_ONLY` `:419`) | `send_logs` carries its own `require_staff` (`actionlog.py:296`) | one call to `send_logs(interaction, "mod", …)` `actionlog.py:287` |
| `/case <case_id>` | `:696` | `_ready` `:438` → `require_staff` + `db.is_connected` | `get_case` `modcases.py:270`, a guild check, then `case_embed` `modcases.py:154` — **all inline `:702–721`** |
| `/cases <member> [page]` | `:723` | `_ready` `:438` | `count_cases` `modcases.py:328`, `cases_for` `:303`, `case_line` `:421`, `pages_under_limit` `:432` — **all inline `:731–749`**, including the *"`/cases member:… page:N` for more"* tail `:748` |

**Three top-level slots for three doors onto one table.** `/mod` is a `Group` with exactly one
child; `/case` and `/cases` are bare `app_commands.command`s.

**The seven bare actions are NOT in scope and do not move** — `/warn` `:481`, `/timeout` `:495`,
`/untimeout` `:530`, `/kick` `:551`, `/ban` `:568`, `/unban` `:595`, `/purge` `:622`. Owner,
2026-09-04, proposal 3 of 6: *"typed mid-incident with autocompleted arguments; a panel would be
three clicks slower at the wrong moment."* This design touches them only through §E's string
rewrites and through making sure the case they write is the case the panel shows.

**Not a subcommand and NOT moving** (P14): `ApplyNowButton`
(`cogs/moderation/automod.py`, a `SafeDynamicItem` on the modlog case card). It belongs to the
room, not the caller, and `automod-panel-design.md` §I already settled it.

**The `mod_cases` row today** (`storage/db.py:306`, plus `ADDED_COLUMNS` `:632` rows `:642–646`):

| Column | Notes |
|---|---|
| `id`, `guild_id`, `kind`, `at` | `kind` ∈ `CASE_KINDS` `modcases.py:15` (⚠️ that tuple is **imported by nothing** — measured; a dead constant, checklist 15, reported not fixed) |
| `user_id` | ⚠️ **nullable.** An untargeted `/purge` files against the CHANNEL (`code-notes.md:1275`), and `cases_for` `:303` / `count_cases` `:328` can never return it because SQL `user_id = ?` does not match NULL |
| `moderator_id`, `reason`, `duration_s`, `mode`, `applied`, `log_message_id` | `reason` clamped to `REASON_LIMIT` 500 at write (`add_case` `:233`) |
| `actions`, `done`, `failed`, `message_id`, `channel_id` | added columns; JSON lists through `as_list_json` `:249` / `from_list_json` `:253` |

There is **no** void column, **no** note column and **no** edit path of any kind. A written case
is immutable today except through `claim_case` `:275` / `set_case_outcome` `:284` /
`set_case_log_message` `:294`, all of which are the automod Apply-now path.

**Settings keys this feature reads, all untouched:** `automod_warn_threshold`
(`settings_store.py:214`), `modlog_channel_id` (`:215`), `mod_dm_on_action` (`:216`, choices
`:286`), `mod_log_level` (generated `:808`; `LOG_LEVEL_COMMANDS["mod"] = "mod"` `:785`).

**Log kinds today:** `mod.warned`, `mod.timed_out`, `mod.untimed_out`, `mod.kicked`,
`mod.banned`, `mod.unbanned`, `mod.purged`, `mod.warn_threshold`, `mod.would_<action>`,
`mod.<action>_failed`. `mod.untimed_out` `logkinds.py:139`, `mod.unbanned` `:140` and
`mod.warn_threshold` `:141` are `IMPORTANT`; the rest fall through `IMPORTANT_SUFFIXES` `:112`.
Every action row already builds its kind with `kind_via` (`modcmds.py:240`, `:290`, `:317`,
`:338`, `:377`, `:404`, `:191`) — ⚠️ **except `mod.purged` `:680` and `mod.purge_failed` `:659`,
which are bare.** Reported, not fixed: `/purge` has no web door, so nothing double-posts yet.

**The site, measured** — `site/public/moderation.html` (102) + `page-moderation.js` (397):

| Surface | Where | What it owns |
|---|---|---|
| the cases table + pager + filter chips + search | `casesCard` `:193`, `toolbar` `:165`, `FILTERS` `:40` | `GET /api/mod/cases[?user_id=&page=]` `api/tools/mod.py:199` |
| the case drawer | `caseDetail` `:294`, `showCase` `:331` | `GET /api/mod/cases/{id}` `:225`; **Apply now** `page-moderation.js:299` → `POST …/apply` `:234` |
| Take an action | `actionBar` `:249` | the six `POST /api/mod/<kind>` routes `:250–272` → the same shared functions, `via=VIA_WEBSITE` |
| automod / honeypot mode pills, `mod_log_level`, Logs | `modeSwitches` `:83`, `load` `:382–392` | the generic settings API |

🔴 **The answer to "can the site edit or void a case today?" is NO.** `caseDetail` `:294` renders
six read-only lines and exactly one button, **Apply now**, and it renders that only when
`row.applied` is false (`:325`). There is no reason editor, no note field, no void control, and
no route behind any of them. **So this build does not point existing routes at new shared
functions the way automod and role menus did — it ADDS the website's half** (§F, and fork
**F-M3** if the owner would rather it came later).

⚠️ **Two measured site defects, reported not fixed.** (1) `FILTERS` `:45` offers a **Notes** chip
filtering `kind === 'note'`, and `'note'` is not in `CASE_KINDS` `modcases.py:15` and is written
by nothing — the chip has always matched zero rows. If §C's note lands it still matches zero,
because a note is a COLUMN on a case, not a kind. (2) `COLUMNS[0]`'s help text `:56` says *"The
same number the slash commands use"* — after this build the slash command is the panel.

**`commands synced` — the number MOVES, 36 → 34.** `tests/test_bot.py:179` measures **36**
today. The `mod` Group's one slot becomes the `/mod` command's one slot (no change); `/case` and
`/cases` are two slots that vanish. ⚠️ The build **re-measures and states both numbers** — three
other branches are in flight, so the assertion is edited to *what it reads*, and the delta must
be exactly **two**. If it is not, something else broke and the build stops.

### The four homes of one sentence

⚠️ Checklist 15, and it is this build's cheapest win: **`NO_SUCH_CASE` is defined FOUR times** —
`modcases.py:76` (**dead**, imported by nobody), `cogs/moderation/modcmds.py:94`,
`cogs/moderation/automod.py:126`, `api/tools/mod.py:71` — with three different wordings, two of
which name `/cases`. `NO_CASES` is defined twice (`modcases.py:80`, dead; `modcmds.py:98`).
**One home: `modcases.py`.** The dead copies are rewritten to the panel wording and the other
three import them. `automod.py:126`'s copy is the automod Apply-now refusal and keeps its own
meaning — it is rewritten in place, not merged.

## B. The decision — one `/mod [member]`, staff only

**`/mod` becomes a single `app_commands.command` taking one optional `member`; the `mod` Group
goes and `/case` and `/cases` go with it.** It keeps `default_permissions=STAFF_ONLY`
(`command_visibility.py:14`, `manage_messages`), so `"mod"` **stays** in
`tests/test_bot.py:19`'s `STAFF_COMMANDS` and `"case"` / `"cases"` leave it.

**No member/staff split** (the P2 split collapses to one branch). Every path into this feature is
`require_staff` today; a non-staffer gets `store.staff_refusal(guild_id)`
(`settings_store.py:1755`) as a sentence and no panel at all (P9).

> 🔴 **`hide_commands_when_off` cannot touch `/mod`, and this was re-measured after that build
> landed.** At `0fcbac2`, `HIDDEN_WHEN_OFF` (`command_visibility.py:16–31`) holds **fourteen**
> mode keys — `applications_mode`, `automod_mode`, `birthday_mode`, `chat_mode`, `events_mode`,
> `golive_mode`, `honeypot_mode`, `pings_mode`, `poll_mode`, `raidtrain_mode`, `request_mode`,
> `rolemenu_mode`, `tempvoice_mode`, `youtube_mode` — behind the master switch
> `HIDE_COMMANDS_WHEN_OFF` (`settings_store.py:1161`), with `NEVER_HIDDEN` now
> `("settings", "help", "about", "ping")` (`command_visibility.py:32`). **Moderation is not on
> that list and cannot be, because it has no mode key**: there is no `mod_mode` in `KEY_TYPES`,
> and `automod_mode` (`settings_store.py:210`) governs the automod LISTENER, not the mod
> commands — turning it off does not stop `/warn` writing a case. So **`/mod` is never hidden,
> whatever the switch says.** No entry is added; **`command_visibility.py` is not edited by this
> build at all**, and neither is `tests/test_command_visibility.py`. ⚠️ If a reviewer wants
> moderation to hide with the rest, that is a request for a `mod_mode` key — a new feature
> decision, not a line in a dict — and it is out of scope here.

**What the panel owns** — the three doors and nothing more:

| Today | On the panel |
|---|---|
| `/cases <member> [page]` | the ROOT: the list, paged with `‹ Newer` / `Older ›`, narrowed by a `UserSelect` or by `/mod @member` |
| `/case <case_id>` | the case card, opened from the list select — or from **Jump to case #…** when a moderator is holding a number off a log line |
| `/mod logs` | a **Logs** button answering a NEW ephemeral followup (P11) |
| — | **new moves on the card:** Edit reason…, Add a note…, Void this case…, Restore this case |

**What stays elsewhere, said out loud on the panel:** the seven bare actions (the root embed's
footer names them, because a moderator who opened `/mod` to punish somebody needs to be told
where that lives); `Apply now` on a shadow verdict (the modlog card and the site's drawer own
it); the cases table's search box and kind chips (the site — the panel has a select, not a
search); `mod_dm_on_action`, `modlog_channel_id`, `automod_warn_threshold` and `mod_log_level`
(the Settings page and `/settings set-value`, exactly as `automod-panel-design.md` §I fork F-A3
settled for the same two keys).

**The states.**

| # | Condition | Panel |
|---|---|---|
| M0 | not in a guild, or `db.is_connected` is False | **no panel.** `GUILD_ONLY` / `panels.db_up` (`panels.py:80`) answers `DB_UNAVAILABLE` (`settings_store.py:1164`) as a sentence — the same two checks `_ready` `:438` makes today |
| M1 | `/mod`, and the guild has no cases at all | the embed says so in one line (today's `NO_CASES` reworded for a whole server) over **Whose cases? · Jump to case #… · Refresh · Logs · Open on the site** — no list select, no page buttons |
| M2 | `/mod`, ≥1 case | the newest `CASES_PER_PAGE` as `case_line` lines, newest first, `page N of M` in the embed; **A case…** select; `Older ›` when a further page exists, `‹ Newer` when `page > 1` |
| M3 | `/mod @member` (or **Whose cases?**), that member has none | today's `NO_CASES.format(user_id=…)` `:98` verbatim, plus **Everyone's cases** so the filter is escapable |
| M4 | a member filter, ≥1 case for them | M2 plus **Everyone's cases**; the embed's first line is today's *"**N** case(s) for <@id> — page X of Y"* `:745` |
| M5 | the case card, not voided | `case_embed` + the moves in §C's first table |
| M6 | the case card, voided | the same embed carrying a **Voided** field (who, when, why), and §C's second table — **Restore this case** instead of **Void this case…** |
| M7 | **Jump to case #…** with an id that is missing or belongs to another guild | `NO_SUCH_CASE` as a sentence in a NEW followup; the panel stays exactly where it was |

P3 in one line: **no state renders a control whose shared function would refuse it.** `‹ Newer`
is absent on page 1 and `Older ›` on the last page; **Everyone's cases** renders only under a
filter; **A case…** only with rows to pick; **Void this case…** and **Restore this case** are
never both present; **Edit the note…** replaces **Add a note…** rather than sitting beside it.

⚠️ **A case whose `user_id` is NULL — an untargeted `/purge` — is on the root list and can never
be on a member's list**, because `cases_for` `modcases.py:303` filters `user_id = ?`
(`code-notes.md:1275`). That is today's behaviour and this build keeps it. It is also the reason
**Jump to case #…** matters: it is the only way to reach a channel case's card while a member
filter is on.

## C. The cards, the modals, and what each control is for

Each is a **re-render in place**: `retire(previous)` first (P6, `panels.py:62`), `defer()` then
`edit_original_response` (P5), `panels.db_ready` (`:70`) on every click after a defer, and
`panels.still_staff` (`:55`) before **every** move **including the reads** — this feature is
staff-only end to end, so the pings deviation 10 precedent applies: a demoted staffer paging the
list is the same defect one step earlier.

**The ROOT embed** = the lines `/cases` prints today, from the SAME function. `case_line`
(`modcases.py:421`) is reused unchanged for a live case and extended for a voided one (§F), and
the whole block goes through `panels.clamped` (`:108`, `DESCRIPTION_LIMIT` 4000) rather than
`pages_under_limit` `:432` — an embed description, not a chain of 1900-character messages.
`pages_under_limit` **stays in the module** (`cogs/core.py:13` imports it).

**The ROOT view.**

| Row | Control | Rendered when | Shared function · refusal in words |
|---|---|---|---|
| 0 | `Select` **"A case…"** over the page's ≤10 rows, label `panels.option_label(id, case_status(row), reason)` (`panels.py:96`, 100-char clamp) | ≥1 row on this page | — (opens the card) |
| 1 | `UserSelect` **"Whose cases?"**, `min_values=1`, `max_values=1` | always | — (re-renders M3/M4) |
| 2 | `‹ Newer` | `page > 1` | — |
| 2 | `Older ›` | a further page exists (`page * CASES_PER_PAGE < total`) | — |
| 2 | `Everyone's cases` | a member filter is on | — |
| 2 | `Jump to case #…` → `JumpModal` | always | `get_case` `modcases.py:270` + the guild check; a miss answers `NO_SUCH_CASE` in a NEW followup |
| 2 | `Refresh` | always | — |
| 3 | `Logs` → a NEW ephemeral followup (P11) | always | `send_logs(interaction, "mod")` — keeps its own `require_staff` (`actionlog.py:296`) |
| 3 | `Open on the site` (link) | `panels.site_page_url(origin, "mod")` (`panels.py:123`, `logkinds.py:96` → `moderation.html`) is not `None` | — |

⚠️ **Row 2 carries exactly five buttons in state M4 — Discord's per-row cap. Do not add a
sixth.** A select occupies a whole action row, so rows 0 and 1 hold one component each; that is
four rows of five, inside Discord's limit.

⚠️ **Page size is `CASES_PER_PAGE` = 10 (`modcases.py:28`), NOT 25.** Discord's select cap is 25
and 10 is under it, so `capped_placeholder` (`panels.py:88`) is **not** needed here — the pager
is what reaches row 11. Ten is not a new decision: it is the number `/cases` `:740` and
`GET /api/mod/cases` `api/tools/mod.py:209` already share, so "page 3" means the same thing on
the panel and on the dashboard. It stays a constant, not a settings key (§D).

⚠️ **The select label and the embed line are two different renderings on purpose.** Discord does
not render markdown in a select option label, so `case_line`'s backticks and bold would be shown
literally; `panels.option_label` builds `#12 · warn · the reason as far as it fits`, plain text,
clamped to `SELECT_OPTION_LIMIT` 100 (`panels.py:17`). A reason longer than the room left is cut
by the clamp, not by `LINE_REASON_LIMIT` `modcases.py:30` — that 120-character cut belongs to the
embed line and stays there.

**The case card embed** = `case_embed` (`modcases.py:154`), the one card the modlog post, `/case`
and every automod verdict already share (`code-notes.md:960`). It gains two keyword-only
parameters with defaults, so **every existing call site is byte-identical**: `note=` (rendered as
a *Note* field) and `voided=` (a *Voided* field naming who, when and why). A voided card's colour
drops to `COLOURS["purge"]` `modcases.py:46` — the grey already in the palette — so a voided case
reads as voided at a glance in the modlog too.

⚠️ **Voiding a case does NOT undo the punishment**, and the card says so in a sentence: a voided
ban is still a ban, a voided timeout is still running. `/untimeout` and `/unban` are the moves
that lift them and they are still typed commands. Nothing in this design may read as "void
undoes it".

**Live case (M5) — row 0, exactly five:**

| Control | Rendered when | Shared function | Log kind | Refusal in words |
|---|---|---|---|---|
| `Edit reason…` → `ReasonModal` (prefilled, `max_length` `REASON_LIMIT` 500) | always | `edit_case_reason` (§F) | `case.reason_edited` | a reason that is only whitespace: *"A case with no reason is a case nobody can read later, so nothing was changed. Say what it was for, even briefly."* |
| `Add a note…` / `Edit the note…` — **ONE button that says which** | always | `set_case_note` (§F) | `case.noted` | same emptiness refusal, worded for a note |
| `Void this case…` (danger) → `VoidModal` (reason **required**) | not voided | `void_case` (§F) | `case.voided` (IMPORTANT) | lost the race: *"Somebody voided this case a moment ago, so nothing was done twice."* |
| `Back` | always | — | — | — |
| `Refresh` | always | — | — | — |

**Voided case (M6) — row 0, four:** `Restore this case`, `Edit reason…`, `Add a note…` /
`Edit the note…`, `Back`, `Refresh` — five. `Restore this case` calls `restore_case` (§F), log
kind `case.restored` (IMPORTANT), and answers *"Somebody restored this case a moment ago"* when
it loses the race.

⚠️ **`Void…`'s reason modal IS the confirmation** — the raidtrain `Call it off…` shape. A
required free-text reason cannot be pressed by accident, and a second *Are you sure?* in front of
a modal is a speed bump on the one move a moderator makes when they have just realised they were
wrong. `Restore this case` is one press for the same reason and because it is the
access-REDUCING half of the pair (it takes an erasure back off the record).

**The modals** — all `AnswersErrors` + `discord.ui.Modal` (P12, checklist 30). ⚠️ **A modal has
no `app_commands.Range`**, so every bound that vanished with a parameter is rebuilt where the
value now enters (checklist 22):

| Modal | Fields | Bounds | Built from |
|---|---|---|---|
| `ReasonModal` | one paragraph, prefilled with the current reason | `max_length = REASON_LIMIT` 500 (`modcases.py:29`) — the same clamp `add_case` `:233` applies at write | `panels.NoteModal` (`panels.py:176`) — its label names what the note is for; this is exactly the shape it exists for |
| `NoteModal` (the card's) | one paragraph, prefilled when a note exists | `max_length = REASON_LIMIT` | `panels.NoteModal` |
| `VoidModal` | one paragraph, `required=True`, empty | `max_length = REASON_LIMIT` | `panels.NoteModal`; its label says **the member is told this** |
| `JumpModal` | one short line, the case number | digits only; a non-number answers *"**abc** is not a case number"* and **nothing is opened** | a bare `discord.ui.Modal` + `AnswersErrors` — one short `TextInput`, not a paragraph |

⚠️ **`panels.NoteModal` is used for three of the four and must not be re-implemented.** Its
constructor already takes `title`, `label`, `max_length`, `required` and `on_submit`
(`panels.py:181–194`); the only thing it cannot do is prefill, so **`default=` on the `TextInput`
is a one-line addition to `panels.NoteModal`** — reported to the conductor, per the wave-3
precedent, rather than edited on a branch three siblings share (§F).

**The void DM.** `void_case` DMs the member through the existing pair — `dm_text`
(`modcases.py:125`) and `dm_member` `:139` — so `mod_dm_on_action` (`settings_store.py:216`,
choices `:286`) is the ONE switch that decides whether they hear anything, exactly as it decides
for a warn or a ban. `DM_ACTIONS` `modcases.py:49` gains `"void"` (*"had a case against you
cancelled"*) and `"restore"`. A closed DM is never an error (`dm_member` `:148–151`). A case with
`user_id` NULL has nobody to tell, and the card says so.

⚠️ **TEST MODE: the DM is a DM, so it is allowed** (`black_bloc/guard.py` gates channel sends).
But `edit_case_card` (`modcases.py:390`) checks the guard at `:399–402` and **refuses to rewrite
the modlog card when the modlog is not the test channel**, logging a warning instead. So under
`TEST_MODE=true` on the live guild the case ROW is voided and the card in `#carlbot-logs` is not
rewritten. That is `edit_case_card`'s existing behaviour, not something this build introduces —
and the sweep rows say so rather than reading as a bug.

## D. Settings (P13 · checklist 33)

Registered **in its own appended block** at the foot of the registry, exactly where
`rolemenu_panel_minutes` sits (`settings_store.py:1134` for `KEY_TYPES`/`KEY_HELP`, `:1681` for
`default()`), so the parallel wave-4 branches merge textually.

| Key | Type | Default | Status |
|---|---|---|---|
| `mod_panel_minutes` | `int` | **10** | **NEW.** How long the panel stays live. Help text carries KI-20's warning in the same shape as the eleven shipped keys: 15 or more loses the "gone quiet" footer, because Discord's interaction token expires at 15 minutes |

Site rows, both appended in their own block:

| File | Line to copy | New row |
|---|---|---|
| `site/public/assets/labels.js` | `:56` (`rolemenu_panel_minutes`) | `mod_panel_minutes: 'How long the /mod panel stays live',` |
| `site/mock/server.mjs` | `:423` (the `automod_panel_minutes` row) | `['mod_panel_minutes', 'int', 10, 10, "minutes the /mod panel stays live … 15 or more means the buttons simply stop working with no footer to explain it", null, 1440],` |

**Existing keys this panel READS, all untouched:** `mod_dm_on_action`, `modlog_channel_id`,
`mod_log_level`, `automod_warn_threshold` (read only by `warn_member` `:247`, and only touched by
fork **F-M2**), `staff_channel_id` (through `store.staff_roles`).

**Nothing else here is a decision.** The 25-option select cap and the five-per-row cap are
Discord's; `REASON_LIMIT` 500 and `LINE_REASON_LIMIT` 120 are Phase 6's and already exist;
`CASES_PER_PAGE` 10 is the constant the website already shares (§C); and the four behaviours a
reader might mistake for decisions — staff re-checked before every move, a control not rendered
rather than rendered-and-refused, a voided case marked rather than deleted, and every stored
decision having a staff reversal — are **settled by the standing rules** (P8, P3/P9,
staff-final-say), not chosen here, so none becomes a key.

## E. What goes away, and every line that names it

`/help` reads the tree (`cogs/core.py`), so it follows with no edit (P15).

| Thing | Where | Becomes |
|---|---|---|
| `mod` Group | `modcmds.py:417–420` | one `@app_commands.command(name="mod")`, same `default_permissions=STAFF_ONLY` |
| `mod_logs` | `:422–433` | the **Logs** button (P11) |
| `case` | `:696–721` | the case card + **Jump to case #…** |
| `cases` | `:723–749` | the root list |
| `_say_in_chunks` | `:751–758` | **deleted** — an embed description replaces a chain of chunked messages. ⚠️ `pages_under_limit` `modcases.py:432` **stays** (`cogs/core.py:13` imports it) |
| `_ready` | `:438–445` | `panels.db_up` / `panels.db_ready` on the panel; ⚠️ **the seven bare commands keep calling `_ready` unchanged** |
| `_audit` `:760`, `_failed` `:763` | | ⚠️ **measured dead already** — no caller inside or outside the cog. Reported; delete them in this build's tidy commit or leave them, but say which |
| `NO_SUCH_CASE` `:94`, `NO_CASES` `:98` | | **moved to `modcases.py`** as the one home (§A); `modcases.py:76`/`:80`'s dead copies become the live ones and `automod.py:126` / `api/tools/mod.py:71` import rather than redefine |
| `tests/test_bot.py` `LOGS_GROUPS["mod"]` | `:14` | **deleted** — `/mod` is no longer a Group with a `logs` child, so the loops that walk it would `KeyError` |
| `tests/test_bot.py` `STAFF_COMMANDS` `"case"`, `"cases"` | `:23`, `:24` | **deleted**; `"mod"` `:28` stays |
| `tests/test_bot.py` `assert len(top) == 36` | `:179` | **two lower than whatever the build measures** — never a hard-coded absolute |
| `command_visibility.py` | — | ⚠️ **not edited.** Moderation has no mode key, so `/mod` is never hidden (§B) |

**Strings that name a retired command and are rewritten in the SAME commit** — each currently
tells somebody to run something that will not exist:

| File:line | Today | Becomes |
|---|---|---|
| `cogs/moderation/modcmds.py:84` | `NOT_AN_ID` — *"or read it out of `/case`"* | *"…or read it off the case in `/mod`"* |
| `:87–88` | `NOT_BANNED` — *"`/case` and `/cases` show what Black Bloc has done"* | *"`/mod` shows what Black Bloc has done"* |
| `:95` | `NO_SUCH_CASE` — *"`/cases` lists the cases it has for one member"* | *"`/mod` lists them"* (and moves to `modcases.py`) |
| `:748` | the *"`/cases member:… page:N` for more"* tail | **deleted with the command** — the pager replaces it |
| `modcases.py:63` | `ALREADY_APPLIED_BY_SOMEBODY` — *"`/case {case_id}` shows what happened"* | *"`/mod` ▸ **Jump to case #…** shows what happened"*. ⚠️ Read by the automod Apply-now path AND, through `api/tools/mod.py`, by the website — so it must read correctly on a web page too. Prefer *"open case #{case_id}"* over either command spelling |
| `modcases.py:78` | the dead `NO_SUCH_CASE`'s *"`/cases` lists…"* | the live wording above |
| `cogs/moderation/automod.py:131` | *"`/case {case_id}` shows what happened to them"* | same rewrite; also served to staff on the modlog card |
| `settings_store.py:785` | `LOG_LEVEL_COMMANDS["mod"] = "mod"` → `log_level_help` `:800` renders *"and in `/mod logs`"* | ⚠️ There is no `/mod logs` after this build. **REMOVE the row**, per `automod-panel-design.md` deviation 9 — with no row the help text says the lines are kept on the dashboard, which is true. ⚠️ **Also report, do not fix: eight of the remaining twelve rows already name a retired subcommand** (`pings` → `pingroles` `:795`, plus `tempvoice`, `events`, `poll`, `birthday`, `golive`, `request`, `applications`) — flagged by automod's deviation 9 and still open; it wants one pass of its own |
| `site/public/assets/page-moderation.js:56` | `COLUMNS[0]` help — *"The same number the slash commands use"* | *"The same number `/mod` uses."* |

**Docs rewritten in the same commit** (P15):

| Doc | What |
|---|---|
| `docs/access/sweeps.md:248–257` | the **Phase 6 appendix** block — rewritten **in place**, not added to. `:254` currently reads *"→ `/cases @second`, `/case 1`"*; both become panel steps |
| `docs/access/OWNER_GUIDE.md` | ⚠️ names `/case` / `/cases` **nowhere** (measured, zero matches), so this build ADDS one *"Look at what has been done to somebody"* row beside the `/automod` row `:87`, and moves the sweeps count in the header `:5` and the *"Test something"* row `:89` |
| `docs/info/feature-list.md:45` | the F7 row gains one clause: `/mod` is one command that opens a panel, and `/case` / `/cases` are retired |
| `docs/info/architecture.md:190` | the `modcmds.py` line lists `/case /cases` — rewritten to `/mod` plus the seven bare actions |
| `docs/info/phase6-design.md:39`, `:88–89` | name `/case <id>` and `/cases @user` — a dated **"superseded by the panel"** line at the top, NOT a rewrite. The phase doc is the record of what Phase 6 decided |
| `docs/info/phase12-design.md:85` | names `/mod logs` — same dated line |
| `docs/info/panels-program.md:87`, `:193` | the *Mod commands* row → built, with the measured before/after; **fork F1 is answered** (the seven bare actions stay) and the §6 bullet says so |
| `docs/info/README.md` | a row for this file beside the other panel designs (`:42–61`) |
| `docs/info/code-notes.md` | re-keyed at the merge. The anchors cluster at `modcases.py:960`, `:1272`, `:1275`, `:1298`, `cogs/moderation/modcmds.py:994`, and `:3436` / `:3439` / `:3545` in the Phase 12 section. ⚠️ **`:3436`'s note says `/mod` "holds `logs` and nothing else for now"** and `:3439` pins a 34-command tree from Phase 12 — both need rewriting, not just re-pointing. ⚠️ **A third note is already WRONG at HEAD, independent of this build:** the `modcmds.py` note keyed near `:431` says `/untimeout` and `/unban` are *not* gated by test mode, but `modcmds.py:538–542` and `:609–613` refuse both, and `tests/cogs/moderation/test_modcmds.py:368` proves it. Fix the text while the section is open |

## F. Extractions (P4) — one function per move, called by BOTH doors

⚠️ **The move layer stays in the COG.** `api/tools/mod.py:17–28` imports nine names from
`cogs.moderation.modcmds` by name; moving them would be a mechanical diff for no gain, and
keeping every existing import byte-identical is what makes the unchanged assertions in
`tests/api/tools/test_mod.py` (302 lines) the proof the refactor changed nothing (wave-0
deviation 4).

**Already shared, reuse unchanged:** `case_embed` `modcases.py:154` (two new keyword-only
parameters, §C), `case_line` `:421`, `get_case` `:270`, `cases_for` `:303`, `recent_cases` `:312`,
`count_cases` `:328`, `count_all_cases` `:320`, `edit_case_card` `:390`, `dm_text` `:125`,
`dm_member` `:139`, `send_logs` `actionlog.py:287`.

**New, module level in `black_bloc/cogs/moderation/modcmds.py`** — each does ONE write and ONE
log row, each takes `via: str = VIA_DISCORD` and builds its kind with `kind_via`
(`logkinds.py:367`; checklist 34). Each rewrites the modlog card through `edit_case_card`
`modcases.py:390` **after** the row is written and the row is logged, never before (checklist 12
— a card that cannot be rewritten must not abort the state change; `edit_case_card` already
returns `False` rather than raising):

| Function | Log kind | Notes |
|---|---|---|
| `edit_case_reason(bot, guild, case_id, reason, moderator, *, via=VIA_DISCORD)` | `case.reason_edited` (ROUTINE) | refuses an empty reason in words and writes nothing; `details` carry `case_id`, `via` and the OLD reason, so the log is the edit history the row no longer holds |
| `set_case_note(bot, guild, case_id, note, moderator, *, via=VIA_DISCORD)` | `case.noted` (ROUTINE) | one note per case, replaced not appended; `note_by` / `note_at` record who last wrote it |
| `void_case(bot, guild, case_id, reason, moderator, *, via=VIA_DISCORD)` | `case.voided` (**IMPORTANT**) | `mark_case_void` first (a conditional UPDATE, below); only the winner DMs, logs and rewrites the card |
| `restore_case(bot, guild, case_id, moderator, *, via=VIA_DISCORD)` | `case.restored` (**IMPORTANT**) | `clear_case_void` first, same shape |

⚠️ **`HEADS["case"] = "mod"` already exists** (`logkinds.py:51`), so all four kinds classify as
the Moderation feature and appear in `/mod`'s own Logs with **no edit to `HEADS`** — measured.
But each kind must be added explicitly to `IMPORTANT` (`:132`) or `ROUTINE` (`:160`) or the
classification test fails: `case.voided` and `case.restored` into `IMPORTANT`,
`case.reason_edited` and `case.noted` into `ROUTINE`. ⚠️ `like_patterns` `:381` derives
`case.%` and `web.case.%` from `HEADS`, so the website's rows are already picked up too.

**New, in the EXISTING `black_bloc/modcases.py`** — appended at the foot, the shape
`black_bloc/automod.py` landed with. ⚠️ Nothing already in the file is renamed or re-homed, so
`api/tools/mod.py:30–41`'s eleven imports, `api/tools/members.py:11`, `cogs/core.py:13` and
`cogs/moderation/automod.py:70` are all unchanged:

| New | What it is |
|---|---|
| `set_case_reason(db, case_id, reason)` · `write_case_note(db, case_id, note, by)` | plain UPDATEs, `datetime.now(UTC).isoformat()` for the stamp, `commit()` — the `set_case_outcome` `:284` shape |
| `mark_case_void(db, case_id, by, reason) -> bool` | ⚠️ **conditional UPDATE, `WHERE id = ? AND voided_at IS NULL`**, `True` for the one caller that won. Checklist 6: two staffers on two panels pressing Void at the same moment. This is `claim_case` `:275` read across a different column |
| `clear_case_void(db, case_id) -> bool` | the same, `WHERE voided_at IS NOT NULL` |
| `case_is_void(row) -> bool` · `case_status(row) -> str` | `case_status` is the select label's status word: `"voided"`, `"not done"` when `applied` is 0, else the kind |
| `CaseMove` + `CARD_MOVES` + `card_buttons(row)` + `root_buttons(*, has_rows, page, pages, filtered, has_site)` | §B/§C's tables **AS DATA**, proved by a parametrised test |
| `PANEL_MINUTES_KEY = "mod_panel_minutes"`, `panel_minutes(store, guild_id)` | one-liners over `panels.panel_minutes` (`panels.py:119`), exactly as the eleven shipped panels do |
| `PANEL_TITLE`, `PANEL_TIMEOUT_FOOTER`, `VOID_UNDOES_NOTHING`, the panel sentences | wave-0 deviation 1: the footer is a whole sentence, not a format string |
| `NO_SUCH_CASE`, `NO_CASES` | the live copies (§A, §E) |

⚠️ **`modcases.py` may import `panels` at MODULE level here, unlike `black_bloc/automod.py`.**
Measured: `settings_store.py:10–29` imports `automod` and `chat_memory` but **not** `modcases`,
and `panels.py:12` imports `settings_store` — so `modcases → panels → settings_store → automod`
is a chain, not a loop. That is exactly the cycle `automod-panel-design.md` deviation 4 tripped
on, and it does not exist here. **The §H import check is what proves it**; if it bites, fall back
to the function-local import that deviation landed with.

**What to ADD to `black_bloc/panels.py`: nothing on this branch.** One candidate is real and is
handed to the CONDUCTOR: **`NoteModal` cannot prefill** — `panels.py:179` declares
`note = discord.ui.TextInput(style=paragraph)` and `__init__` `:181` sets `label`, `max_length`
and `required` but never `default`. Three of this panel's four modals want a prefilled box, and
so did automod's `WordsModal` and role menus' `WordsModal`/`RulesModal`. It is a one-line
addition (`self.note.default = default`), but `panels.py` is the file every wave-4 branch
touches, and voice deviation 8 measured that a clean textual merge beats one-fact-one-home for a
handful of lines. **Build it locally as a subclass, name it in the deviations, and let the
conductor fold it in at the merge** — exactly how `clamped` and `still_allowed` landed.

**The website's half** (checklist 34, and fork **F-M3**). Four routes, all following the measured
shape of `POST /api/mod/cases/{case_id}/apply` `api/tools/mod.py:234` — `writer(request)`,
`require_guild`, `require_db`, `actor_for`, the shared function with `via=VIA_WEBSITE`, and
`Refused(status, code, sentence)` on a refusal (never a bare status — the standing rule):

| Route | Calls | Refusals |
|---|---|---|
| `POST /api/mod/cases/{id}/reason` `{reason}` | `edit_case_reason(…, via=VIA_WEBSITE)` | 404 `no_such_case`, 400 `bad_reason` |
| `POST /api/mod/cases/{id}/note` `{note}` | `set_case_note(…, via=VIA_WEBSITE)` | 404, 400 `bad_note` |
| `POST /api/mod/cases/{id}/void` `{reason}` | `void_case(…, via=VIA_WEBSITE)` | 404, 400 `bad_reason`, 409 `already_voided` |
| `POST /api/mod/cases/{id}/restore` | `restore_case(…, via=VIA_WEBSITE)` | 404, 409 `not_voided` |

⚠️ **Not one of them calls `note()`** — the shared function logs, the route passes `via`, and the
AST guard `tests/test_logkinds.py::test_a_route_never_notes_an_event_its_shared_path_already_logged`
is what proves it. `case_row` `api/tools/mod.py:103` gains `note`, `note_by`, `note_at`,
`voided_at`, `voided_by`, `void_reason`, and `caseDetail` `page-moderation.js:294` gains the four
controls beside **Apply now** (the two destructive ones through the existing `ask()` confirm,
`page-moderation.js:268`'s shape). ⚠️ **`node site/mock/check.mjs`'s route count MOVES by +4** —
state it before AND after rather than trusting the last measured figure (17 pages / 142 routes at
the automod landing); `site/mock/contract.json` and `site/mock/server.mjs` gain the four rows.

**Two things to reuse, never re-copy:** `panels.answer` (`:36`) — the cog has no copy today, keep
it that way; and `panels.site_page_url(origin, "mod")` (`:123`), never a private `SITE_PAGE`
constant (the youtube copy pings deviation 6 left behind is the counter-example).

## G. The migration (⚠️ the one thing no wave-3 panel had)

`mod_cases` gains **six nullable columns**. They go in **two places**, and both are required:

1. `storage/db.py:306`'s `CREATE TABLE mod_cases` block, so a **fresh** database has them;
2. `ADDED_COLUMNS` `:632` (append after the existing `mod_cases` rows `:642–646`), so an
   **existing** database gets them from `_add_missing_columns` `:779`.

| Column | Declaration |
|---|---|
| `note` | `TEXT` |
| `note_by` | `INTEGER` |
| `note_at` | `TEXT` |
| `voided_at` | `TEXT` |
| `voided_by` | `INTEGER` |
| `void_reason` | `TEXT` |

**`SCHEMA_VERSION` 28 → 29** (`storage/db.py:11`).

⚠️ **No table rebuild.** Every column is nullable with no `NOT NULL` and no default, so
`ALTER TABLE … ADD COLUMN` is enough — this is nothing like
`_set_aside_mod_cases_with_a_required_user` `:752`, which rebuilds because it is *removing* a
`NOT NULL`. Do not touch `MOD_CASES_CARRIED_OVER` `:668`.

⚠️ **No new index.** `mod_cases_by_user` `:320` and `mod_cases_by_kind` `:321` already serve every
query this panel makes; `voided_at` is read per row on a page of ten, never filtered on.

**Migrate-before-deploy applies, and here it means something specific:** the schema is applied by
`Database.connect()` `:697`, which runs `executescript(SCHEMA)` `:706` then
`_add_missing_columns()` `:707` **before the bot logs in** — so the ALTERs and the new code ship
in one image and run in the right order on the first boot. The direction that is safe is
old-database + new-code (the ALTERs run first); the direction to think about is a **rollback**:
old code on a new database is fine, because `SELECT *` (`get_case` `:271`, `cases_for` `:304`)
returns the extra columns and `row_value` `:263` tolerates whatever it finds. Say both in the
build report; do not claim the rollback was exercised unless it was.

## H. Tests (P16 — one file per source file, mirrored paths)

⚠️ **No new test file and no new module** — `black_bloc/modcases.py` and `tests/test_modcases.py`
both already exist. That is this build's single biggest saving against role menus (§K).

| File | What it gains, and what it keeps |
|---|---|
| `tests/cogs/moderation/test_modcmds.py` (596) | ⚠️ **The seven bare actions' tests stay UNCHANGED in assertion** — `:263`–`:483` (warn, the threshold, the DM setting, the test-mode refusals, timeout clamping, the failed-action kinds, kick/ban/unban, purge and its deferral, the untargeted purge). **That is the proof the punishment path did not move**, and it is the strongest evidence this build can produce. Rewritten: `:485` (`/case`), `:502` and `:521` (`/cases`), `:546–547` inside `test_every_command_is_staff_only`, `:568`/`:582`/`:591` (`/mod logs`). New: `/mod` answers ephemerally with a panel; **parametrised over M1–M7 — each renders exactly its §B row and no other**; `‹ Newer` absent on page 1 and `Older ›` on the last; `Everyone's cases` only under a filter; `Void this case…` and `Restore this case` never both; `Edit the note…` replaces `Add a note…`; an empty reason writes NOTHING and does not re-render; two Voids in a row leave ONE `case.voided` row and the loser is told; every move calls its shared function with `via` untouched (mock them); a staffer demoted mid-card moves nothing (`still_staff` at every site, **reads included**); `db_ready` after every defer; `Logs` answers a NEW followup and still refuses a demoted staffer; the timeout disables every item and a re-render `retire`s what it replaced |
| `tests/test_modcases.py` (229) | `card_buttons` / `root_buttons` for every flag combination; `case_status` for voided / not-done / plain; `case_line` struck through for a voided row and **byte-identical** for a live one; `case_embed` with and without `note=` / `voided=` (⚠️ **and unchanged for every existing call**); `mark_case_void` / `clear_case_void` returning `True` once and `False` the second time; `panel_minutes` |
| `tests/storage/test_db.py` | the six columns arrive on a database created **before** this build (the `ADDED_COLUMNS` shape the file already tests), `SCHEMA_VERSION` reads 29, and an existing row survives with `NULL` in all six |
| `tests/test_settings_store.py` | `mod_panel_minutes` round-trips, defaults 10, help mentions 15, is in `VALUE_KEYS`, refuses `-1` and the string `"15"` |
| `tests/test_bot.py` | `LOGS_GROUPS` loses `"mod"` (`:14`); `"case"` and `"cases"` leave `STAFF_COMMANDS` (`:23`, `:24`) and `"mod"` stays (`:28`); the tree-limit test **re-measures** and expects **two fewer** (`:179`) |
| `tests/test_logkinds.py` (736) | the four `case.*` kinds are classified; `feature_of("case.voided") == "mod"`; the four `web.case.*` heads sit in the SHARED map, not the routes' own set, or the AST walk fails; the three guards named in checklist 34 still pass |
| `tests/api/tools/test_mod.py` (302) | ⚠️ **every existing assertion stays green with no edit** — the proof the punish layer did not move. Four new route tests: each writes ONE `action_log` row carrying `via=website` (`tests/api/conftest.py:405 one_web_row`), each refuses in a sentence, and voiding twice is a 409 |
| `tests/test_automod.py` / `tests/cogs/moderation/test_automod.py` | ⚠️ **unchanged**, except the one `NO_SUCH_CASE` wording assertion if it pins the string. Under fork **F-M2 (a)** they also gain the case that a voided warn does not count toward `automod_warn_threshold` |

## I. §J — prove before merge (P17), and the sweep rows

1. `python -m black_bloc` boots; **read `commands synced` and record both numbers — the drop must
   be exactly two, 36 → 34.** ⚠️ If it is not, stop; something other than this build broke. With
   no token, measure it the only other way:
   `tests/test_bot.py::test_the_command_tree_stays_inside_discords_limits`, which counts the real
   tree after loading every cog.
2. The parametrised state test: every state renders its row and no other (checklist 3, 12).
3. `python -c "import black_bloc.modcases, black_bloc.cogs.moderation.modcmds,
   black_bloc.cogs.moderation.automod, black_bloc.api.tools.mod, black_bloc.panels,
   black_bloc.settings_store"` — the substitute for a boot (wave-0 deviation 5) **and the line
   that proves §F's module-level `panels` import is not a cycle.**
4. **The migration, exercised, not reasoned about:** create a database with the code at
   `46fba16`, write a case, then connect with the new code and assert the six columns exist and
   the old row survives. A migration that was not run is not a migration that passed
   (checklist 10).
5. `ruff`; full `pytest`; `node site/mock/check.mjs` (⚠️ **expect 17 pages and FOUR MORE
   routes** — state the before and after numbers, do not trust the 142 measured at the automod
   landing); `node --input-type=module --check < site/public/assets/labels.js`.
6. Checklist sweep before reporting — **1** and **2** (⚠️ *nothing in this build may change how a
   punishment is guarded or which kind a dry run gets*; the diff must show zero edits inside
   `warn_member` `:232`, `timeout_member` `:262`, `kick_member` `:326`, `ban_member` `:347`,
   `refuse_in_test_mode` `:161` and `note_failure` `:200`), **6** (`mark_case_void`'s conditional
   UPDATE), **8** and **30** (`AnswersErrors` on every modal, select and view), **10** (the
   migration was RUN), **11** (`allowed_mentions` on every interpolated send — reasons and
   display names are attacker-controlled and the list is full of `<@id>`), **12** (row, log, DM,
   then the card — `edit_case_card`'s failure must not abort the void), **15** and **17** (the
   four `NO_SUCH_CASE` copies, §A), **22** (`REASON_LIMIT` rebuilt as `max_length` where the
   `app_commands` parameter used to bound it), **33** (§D), **34** (four new routes, four new
   `kind_via` heads, zero `note()` calls).
7. ⚠️ **TEST MODE stands.** The bot speaks only in `#mute-me-bot-test-spam` (`TEST_CHANNEL_ID`),
   enforced by `black_bloc/guard.py`. Run every sweep row there. Two consequences worth stating
   rather than discovering: **the void DM is a DM and is allowed**; and `edit_case_card`
   `modcases.py:399–402` will NOT rewrite a modlog card that is outside the test channel, so on
   the live guild a voided case's card stays as it was until test mode is lifted (§C).

**Sweep rows — numbered at BUILD time, starting at the next free row.** `docs/access/sweeps.md`
holds **588 lines and its last row is 182** today, ⚠️ **but two sibling wave-4 designs are being
written in parallel and their builds may land first, so this document claims NO numbers.** Write
them as `D1`–`D9` (letters on purpose — a half-renumbered table cannot look finished) and let the
conductor number them at the merge, the way role menus' `M1`–`M10` became 173–182. The Phase 6
appendix block at `:248–257` is rewritten **in place**, not added to.

| # | Do this | Expect |
|---|---|---|
| D1 | `/mod` as a Lead in `#mute-me-bot-test-spam` | ONE ephemeral panel: the newest ten cases as the lines `/cases` used to print, newest first, *page 1 of N*, over **A case… · Whose cases? · Older › · Jump to case #… · Refresh · Logs · Open on the site**. Nothing anywhere says `/case` or `/cases` |
| D2 | `Older ›`, then `‹ Newer` | the page changes in place, the footer's page number agrees, and `‹ Newer` is simply **not there** on page 1 — not there and refusing |
| D3 | `Whose cases?` → a member with cases, then **Everyone's cases** | the list narrows and the first line reads *"**N** case(s) for @them"*; **Everyone's cases** appears only while the filter is on and takes it back off. A member with none says so and still offers the way out |
| D4 | `/mod @somebody-with-no-cases` | the same "no cases" sentence, straight from the command — no empty select, no dead page buttons |
| D5 | `A case…` → a warn | the card `/case` used to show — kind, member, moderator, when, reason — over **Edit reason… · Add a note… · Void this case… · Back · Refresh**, and a line saying voiding does not undo anything |
| D6 | `Edit reason…` → clear the box and submit; then type a real reason | the empty one is refused in one sentence and **nothing is saved** (re-open the card: the old reason is still there); the real one saves, leaves ONE `case.reason_edited` row, and the card in the modlog is rewritten to match |
| D7 | `Add a note…`, then re-open the card | the button now reads **Edit the note…** — never both — the note is a field on the card, and the log carries one `case.noted` |
| D8 | `Void this case…` → a reason → submit | the member is DM'd (or not, per `mod_dm_on_action`), the card shows **Voided** with who/when/why, the list line is struck through, the log carries ONE `case.voided`, and **the timeout or ban is still in force** — the card says so. Then press **Void this case…** from a second panel opened before the first: it says somebody just voided it and does nothing twice |
| D9 | On the voided case: `Restore this case`; then `Jump to case #…` → `99999`; then leave the panel `mod_panel_minutes` (10) minutes | the strike-through goes and the card is back to D5's five buttons — no state is terminal; the bad id answers *"Black Bloc has no case #99999"* in a NEW message with the panel untouched; then every control greys out and the footer reads *this panel has gone quiet — run /mod again* |

## J. The genuine forks — the owner decides, one at a time

**Settled first, by the standing rules, so they are NOT put to him:**

- ✅ **The seven bare actions stay bare.** The owner decided this on 2026-09-04 (proposal 3 of 6)
  and `panels-program.md` §6's fork **F1 is answered by it**, not re-asked here.
- ✅ **`/mod` stays `STAFF_ONLY`, and a member still cannot see their own cases.** Every door into
  this feature is `require_staff` today (`modcmds.py:439`, `:697`, `:724`). A case reason is
  staff text *about* a person, and `mod_dm_on_action` (`settings_store.py:216`) is the deliberate,
  server-configurable channel by which they learn what happened — including a `none` setting a
  server may have chosen on purpose. A "my cases" panel would route around that setting, so it is
  a new feature with its own decisions, not a door swap. Worth a later pass; not this build.
- ✅ **A voided case is marked, never deleted**, and **Restore** exists — the standing
  staff-final-say rule (*"never design a terminal state staff cannot leave"*).
- ✅ **Restoring DMs the member** when `mod_dm_on_action` is not `none`, because the same rule
  says a person affected by a staff decision is told, and they were told when it was voided.
- ✅ **`Void…`'s required reason modal IS its confirmation** (the raidtrain `Call it off…` shape);
  `Restore` is one press, being the access-REDUCING half.
- ✅ **`/mod` is never hidden** — moderation has no mode key (§B), measured.
- ✅ **The `ApplyNowButton` on modlog case cards is untouched** (P14, and
  `automod-panel-design.md` §I already settled it).

**Three questions are genuinely his:**

- **F-M1 — does the default list show voided cases?** They are marked, not deleted, so the
  question is only whether they are in the way.
  - **(a) Yes — struck through, in place, always. Recommended.** An audit that hides its own
    erasures is not an audit; the strike-through is what makes "somebody voided this" visible to
    the next moderator without their having to go looking. Cost: a heavily-voided member's page
    is mostly noise.
  - (b) Hidden behind a **Show voided** toggle on the root, off by default. Cleaner day to day,
    and it adds a sixth button to a row that already carries exactly five (§C) — so it would have
    to displace `Refresh`.

- **F-M2 — does voiding a warn stop it counting toward `automod_warn_threshold`?** `warn_count`
  (`modcases.py:351`) counts applied warns and automod warn verdicts; `warn_member`
  (`modcmds.py:246`) compares it to the threshold and says so in the reply and in
  `mod.warn_threshold`. ⚠️ **This is the one place a void changes a number something else reads**,
  which is why it is his and not settled in-doc.
  - **(a) Yes — `warn_count` gains `AND voided_at IS NULL`. Recommended.** A voided warn is a warn
    staff have said was wrong; counting it toward "this member is at three strikes" makes the
    void a lie. Cost: one clause inside a function the automod path reads, so it gets its own
    test asserting the count before and after a void, and it is named in the build's deviations
    whatever happens.
  - (b) No — the threshold counts rows, and voiding is a note on the record only. Nothing
    automod-adjacent moves at all, which is the safest possible build; but a moderator who voids
    two of three warns will still be told the member is at the threshold.

- **F-M3 — does the website get the same four moves in THIS build, or a later pass?** Measured
  (§A): the site can list, show, apply and punish, and can do none of the four. The
  "every decision is configurable BOTH ways" rule (checklist 33) points at (a).
  - **(a) Build the four routes and the four drawer controls now. Recommended.** Voiding is the
    most consequential move this design adds, and shipping it Discord-only makes the dashboard —
    the surface with the search box and the filters, i.e. the one somebody actually audits from —
    unable to correct what it can see. `check.mjs`'s route count moves +4 and
    `contract.json` / `server.mjs` gain four rows.
  - (b) Discord first, the website in its own pass. Takes roughly 60–90k off the estimate
    (§K) and leaves the site untouched but for `case_row`'s six new fields, which it needs
    anyway to render the strike-through. Cost: the both-ways rule is broken for one release, and
    "one release" is how `/role revoke` came to be promised in four docs for months.

## K. What NOT to build, and what this costs

**Not in this build:**

- **Anything inside the punishment path.** `warn_member` `:232`, `timeout_member` `:262`,
  `untimeout_member` `:303`, `kick_member` `:326`, `ban_member` `:347`, `unban_member` `:389`,
  `record_case` `:114`, `refuse_in_test_mode` `:161`, `note_failure` `:200`, `tell_member` `:217`,
  `audit_reason` `:109` and the `purge` body `:622`. Fork **F-M2**'s `warn_count` clause is the
  sole exception, and it changes a count, not an action.
- **A member card with Warn / Timeout / Kick / Ban buttons.** `panels-program.md:87` sketches it;
  the owner's 2026-09-04 decision retires the sketch. `Whose cases?` narrows a list and nothing
  more.
- **Deleting a case.** Void is the reversible move; a hard delete is a new capability, the first
  irreversible write in this feature, and it would break `warn_count`'s history and the modlog
  card's link. Not asked for.
- **Many notes per case.** One note, editable, with `note_by`/`note_at`. A note *thread* is a
  second table and a second surface.
- **Search, or the kind chips.** The site's toolbar `page-moderation.js:165` owns those; the
  panel has a select and a pager. ⚠️ Do NOT fix the dead **Notes** chip `:45` here — report it.
- **`count` / `important_only` on `Logs`** — lost exactly as they were for every other panel; the
  site's Logs page has both.
- **Touching `pages_under_limit`** `modcases.py:432` — `cogs/core.py:13` imports it.
- ⚠️ **REPORT, do not fix — five measured defects found while writing this.** (1) `mod.purged`
  `:680` and `mod.purge_failed` `:659` are **bare**, the last two mod kinds without `kind_via`;
  harmless today because `/purge` has no web door. (2) `CASE_KINDS` `modcases.py:15` is imported
  by nothing. (3) `_audit` `:760` and `_failed` `:763` have no caller. (4) The site's **Notes**
  filter chip `page-moderation.js:45` has always matched zero rows. (5) The `code-notes.md` note
  on `modcmds.py`'s test-mode predicate claims `/untimeout` and `/unban` are ungated; both are
  gated (`:538`, `:609`) and a test proves it (§E). (1) and (5) are `KNOWN_ISSUES.md` candidates.

**Cost.** Measured wave-3 builds against their own estimates: automod **370k** (est 300–360k),
chat **441k** (est 300–360k), raidtrain **473k** (est 380–450k), role menus **529k** (est
420–500k). ⚠️ **All four landed ABOVE their estimate** — treat a band as a floor, not a midpoint.

Sizing this one against them:

| Cheaper than wave 3 | Dearer than wave 3 |
|---|---|
| a **773-line cog** (automod 830, role menus 2164), of which the ~490 lines of punishment path are untouched — the surface actually rewritten is about 280 lines, the smallest of any panel so far | ⚠️ **a schema migration** — six columns, a version bump, and a run to prove it. No wave-3 panel had one |
| a **596-line test file** (automod 861, role menus 1558) whose first 220 lines must not move | ⚠️ **four NEW API routes plus the dashboard drawer** (fork F-M3 (a)) — every wave-3 panel could say "no route is added or removed"; this one cannot, and `check.mjs`'s count moves |
| **no new module and no new test file** — `black_bloc/modcases.py` and `tests/test_modcases.py` both exist. Automod's single biggest saving | ⚠️ **a pager** — no panel has built one; `‹ Newer` / `Older ›` and their P3 render conditions are new ground |
| **two surfaces** (root, case card) against automod's three and role menus' seven | **four new shared functions and four new log kinds**, each needing `kind_via`, a classification entry and a `via` round trip |
| **no mode**, no three-way crossing, no arming gate | four modals, three of them wanting a prefill `panels.NoteModal` cannot do (§F) |

**Estimate: 340–420k Opus tokens**, ~390k the likely landing — above automod (370k, no migration
and no route change) and below chat (441k). **Under fork F-M3 (b) — website deferred — 280–340k.**

**Prep before dispatch** (per the ≥150k rule): clean tree, a fresh usage read, and a brief that
tells the agent to **commit at clean boundaries, one layer at a time**, so a kill costs the last
layer rather than the build:

1. **the migration + the store layer** — `storage/db.py` (six columns, `SCHEMA_VERSION` 29),
   `modcases.py`'s new store functions, `case_line` / `case_embed` / `case_status`, the button
   tables, `tests/storage/test_db.py` + `tests/test_modcases.py`. Land this alone and prove it;
2. **the four shared functions + the four log kinds** in the cog, `logkinds.py`,
   `tests/test_logkinds.py` and the new cog tests — plus fork **F-M2**'s `warn_count` clause if it
   goes (a);
3. **the panel itself** and the retirement of `/case`, `/cases` and the `mod` Group,
   `tests/cogs/moderation/test_modcmds.py`, `tests/test_bot.py`, `settings_store.py`'s key;
4. **the website** (fork F-M3 (a)) — four routes, `case_row`, `page-moderation.js`,
   `contract.json`, `server.mjs`, `check.mjs`, `tests/api/tools/test_mod.py`;
5. **the string and doc sweep** (§E).

The brief carries `docs/info/review-checklist.md`, `docs/info/panels-program.md` and this file,
the standing rule that **`git stash` is never run in a shared tree**, and the reminder that a
**directory deploy ships the working tree** — this build touches `site/public/`, so it deploys
only from a committed-clean tree or a throwaway worktree.
