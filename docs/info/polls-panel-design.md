# Polls — `/poll` is ONE command that opens a panel

> **Audience:** the builder and the reviewer. **Status:** TRACKED · ✅ **SHIPPED — live in v65** (`d13e1a4`, merged `--no-ff` `27452ac` 2026-09-03 after Fable review, 3644
> tests; deployed 14:14, `deploys.log` line 64; synced 43 app commands; not run against Discord by eye). Built on
> `worktree-agent-aa735ab092d13477d` (wave 1 of [`panels-program.md`](panels-program.md)) —
> commits `83640cf` (the panel + the extractions + the routes), `fd73cfa` (the cog tests moved
> onto the panel), `7826e94` (the panel's own tests) and the docs commit that follows them.
> This doc adds only what is specific to polls; the seventeen
> invariants **P1–P17** live in that file's §2 and are **not restated here** — a reviewer checks
> the build against §2 first, then this, then the `## Deviations` foot.
> **Last verified: 2026-09-03 (build)** — MEASURED on the branch: `ruff check .` clean;
> `pytest -q -n auto` **3526 tests, all green** (3442 at the base `d3da02c`, +84); the command tree
> loaded from every cog in `COGS` reports **44** top-level commands with `/poll` no longer a
> `Group` and no children; `black_bloc/polls.py` imports only `logging`, `datetime`, `typing`,
> `discord` and `.timezones` (no database, no gateway); `node site/mock/check.mjs` = 17 pages /
> 142 routes; `page-polls.js` and `labels.js` both parse as ES modules. §C's modal components
> were re-checked against the installed **discord.py 2.7.1**: `Label`, `RadioGroup` and
> `CheckboxGroup` all exist with the signatures §C assumes, `RadioGroup` exposes `.value` and
> `CheckboxGroup` `.values` (so `picked_values` reads both), and **the 5-component modal cap is
> enforced by the library** — a sixth `add_item` raises `ValueError: maximum number of children
> exceeded (5)`, measured, not taken from the docs.
> ⚠️ **NOT verified:** nothing has run against Discord — no boot with a token, no panel opened,
> no poll posted, no modal rendered by a real client. In particular the mixed-component modal
> payload, the `ChannelSelect`/`RoleSelect` rows on the preview, and whether a `RadioGroup`
> inside a `Label` returns its value on submit are all test-double evidence only. Whether
> `poll_who_can_create: everyone` was ever switched on live is still unknown. Sweep rows 80–86
> are the owner's path through all of it.

## A. Measured today — every subcommand, who may run it, what it calls

`poll` is a `Group` (`cogs/community/polls.py:1588`) with a nested `recur` `Group` (`:1589`).
**Seven + four = eleven subcommands.** `/poll` carries **no** `default_permissions`, so it is
member-visible (`tests/test_bot.py:71`, `MEMBER_COMMANDS`); `poll_mode` is **not** in
`command_visibility.py:16 HIDDEN_WHEN_OFF`, so turning polls off does not hide the command.

| Subcommand | Decorator | Gate today | Calls / inline logic |
|---|---|---|---|
| `logs` | `:1813` | `send_logs`' own `require_staff` | `send_logs(interaction, "poll", …)` — shared |
| `create` | `:1826` (body `:1846`) | `_ready` `:1802` + `poll_mode != off` + `_may_create` `:1808` (**member when `poll_who_can_create == everyone`**) | `poll_plan` `:264` → `store_poll` `:316` → `_post_now` `:1920` / `_send_for_review` `:1940` |
| `end` | `:1970` | `_ready`; **creator OR staff** (`:1978`) | `close_poll` `:1107` — shared |
| `cancel` | `:2004` | `require_staff` `:2007` | `cancel_poll` `:1238` — shared |
| `results` | `:2029` | `_ready` only — **any member** | `Polls.counts_for` `:2053` → `results_embed` (`polls.py:615`) |
| `list` | `:2066` | `_ready` only — **any member** | `polls_by_status` `:379`, capped at `LIST_LIMIT` = 25 (`:124`); **line-building inline** `:2074–2081` |
| `settings` | `:2293` (body `:2317`) | `require_staff` `:2336` | **all inline** `:2343–2376` (11 `store.set`, 2 `store.clear`, one `poll.settings` log) + `_settings_lines` `:2378` + `_health_lines` `:2403` |
| `recur create` | `:2086` (body `:2107`) | `require_staff` `:2124` | `cadence_trouble` → `poll_plan` → `store_poll(status=RECURRING)` → `set_recurrence` `:406` + log **inline** `:2182` |
| `recur list` | `:2202` | `_ready` only — **any member** | `recurrences` `:390`; lines **inline** `:2208–2215` |
| `recur pause` | `:2220` (body `:2225`) | `_wanted_recurrence` `:2278` → `require_staff` | **all inline** `:2231–2259` — `set_recur_next` `:417`, `next_occurrence`, two log kinds |
| `recur delete` | `:2261` | `_wanted_recurrence` | **all inline** `:2267–2276` — `set_recur_next(None)` + `set_status(CANCELLED)` + log |

**States** — `polls.py:85 STATUSES` = `draft · pending_review · open · closed · archived ·
denied · cancelled · recurring`; `OPEN_STATUSES` `:86` = draft/pending_review/open;
`TRANSITIONS` `:89`:

| From | To |
|---|---|
| `draft` | pending_review · open · cancelled |
| `pending_review` | open · denied · cancelled |
| `open` | closed · cancelled |
| `closed` / `cancelled` | archived |
| `denied` / `archived` | **nothing** (`TERMINAL_STATUSES` `:100`) |
| `recurring` | cancelled |

⚠️ **Nothing in the repo ever writes `draft`** — `store_poll:343` writes `pending_review` or
`open` only. The status exists unused.

**The review flow.** `poll_review_mode == on` (`settings_store.py:1239`, default `off`) makes
`store_poll` write `pending_review`; `send_review_card` `:1462` posts `card_for` `:1449` +
`review_view` `:787` into `card_channel` `:778` (= `staff_channel_id`, or the test channel
while guarded). Approve/Deny are `PollDecisionButton` `:1546`, a **persistent `DynamicItem`**
gated by `decision_context` `:1487` (guard → `require_staff` → db → row), calling
`apply_decision` `:1390`; Deny opens `PollDenyModal` `:1530`; both DM the creator.
⚠️ **`apply_decision` is reachable from NO subcommand today** — only that card.

**§7 — NOT the panel, untouched:** the poll message itself — native `discord.Poll`
(`native_poll:752`) or the panel post `panel_view:812` with `PollVoteButton:882` /
`PollOpenVoteButton:943` / `PollClearVoteButton:917`, all persistent `DynamicItem`s registered
in `cog_load:1594` — plus the review card above.

## B. The decision — one `/poll`, member panel AND staff panel

**`/poll` becomes a single `app_commands.command`; both `Group`s go.** `commands synced` stays
**44** (a group already held one top-level slot — requests deviation 7); the tree loses eleven
children.

⚠️ **`panels-program.md` §3's "Who: staff" row for Polls is WRONG as measured.** A member
panel genuinely exists: `results`, `list` and `recur list` have no staff gate at all, `end`
accepts the poll's creator, and `create` is a member move whenever
`poll_who_can_create == everyone`. So the panel splits on `store.is_staff` exactly as
`/request` does (`cogs/community/requests.py:454 build_panel`), and P9 governs what a member
is told rather than P9's "this is for staff" whole-panel sentence.

**Root panel** (`build_panel(bot, guild, actor)`), one ephemeral embed + view:

| Row | Member sees | Staff adds |
|---|---|---|
| 0 buttons | `Create` (only when `poll_mode` on **and** `_may_create`) · `Find #…` · `Refresh` | `Settings` · `Logs` |
| 1 | Select **"Pick a poll…"** — `polls_by_status(db, guild, OPEN_STATUSES)` `:379`, newest first, **25 cap**, `capped_placeholder` (`panels.py:55`) says "25 of N — the rest are on the site" | same |
| 2 | — | Select **"Repeating polls…"** — `recurrences` `:390`, 25 cap |
| 3 | `Open on the site` link — `f"{origin}/{FEATURE_PAGES['poll']}"` = `polls.html` (`logkinds.py:87`), only when an origin is set | same |

Embed: title "Polls", one intro line, then the open-poll summary lines `/poll list` writes
today (`:2074–2081`, extracted per §F), `NO_OPEN_POLLS` `:189` when empty, plus a staff counts
line. `POLLS_OFF` `:129` and `NOT_A_CREATOR` `:133` become **embed sentences with `Create` not
rendered** — never a dead button (P9), and they never refuse the whole command (requests
deviation 3: only the database being down does that).

⚠️ **No tab state machine** — two selects on one root render is fewer states than §3's
"Open polls / Recurring" tabs sketch, fits in 4 rows, and matches the shipped template.

**`Find #…`** (new, replaces the `poll_id` argument of `end`/`cancel`/`results`/`recur *`):
a one-field modal → the card for **any** poll id in this guild. It is what keeps a *closed or
archived* poll's results reachable — the pick select lists `OPEN_STATUSES` only.

## C. The button tables, as DATA

**The poll card** re-renders in place. Embed = `results_embed(...)` fed by `counts_for`
(`:2053`) — the same builder `/poll results` used, so **there is no separate `Results`
button**: picking a poll *is* the results. `Refresh` re-reads. Buttons come from a new
`CARD_BUTTONS: dict[str, tuple[MoveButton, ...]]` in `black_bloc/polls.py`, mirroring
`requests.py:392` and its `MoveButton` NamedTuple, filtered by the guards the shared functions
apply (P3):

| Status | Buttons rendered (+ `Back` always) | Shared function |
|---|---|---|
| `draft` | `Post it` · `Cancel` (staff) | `post_poll` `:1288` · `cancel_poll` `:1238` |
| `pending_review` | `Approve` (staff, success) · `Deny` (staff, danger, **modal**) · `Cancel` (staff) | `apply_decision` `:1390` (OPEN / DENIED) · `cancel_poll` |
| `open` | `End` (primary — rendered for the creator **or** staff, `:1978`) · `Cancel` (staff, danger) | `close_poll` `:1107` · `cancel_poll` |
| `closed` | none — final | — |
| `cancelled` | none — final | — |
| `denied` | `Post it anyway` (staff, success) — see §I-1, settled | `apply_decision` (OPEN) |
| `archived` | none — final | — |
| `recurring` | never reaches this card — see the recurrence card | — |

`draft`'s row is unreachable today; it is in the table so the parametrised test covers every
member of `STATUSES` and so §I-3 costs nothing later. Every move re-asks `guard_allows`
(`:739`) — the test-mode rule — and `still_staff` (`panels.py:28`) before every staff move (P8).

**The recurrence card** — embed from a new pure `recurrence_card(...)` (§F) showing question,
`describe_cadence` (`polls.py:482`), next occurrence or **paused**, channel, kind, options,
hours:

| Condition | Buttons (+ `Back`) |
|---|---|
| `recur_next_at` set | `Pause` · `Delete` (danger → Yes/Keep confirm, the shape at `cogs/community/requests.py:570`) |
| `recur_next_at` NULL | `Resume` · `Delete` (danger → confirm) |

**Modals.** Discord caps a modal at **5 components**. `/poll create` has twelve options today
(`:1827–1845`), so it splits:

| Step | Shape |
|---|---|
| 1 — `New poll` modal (5 Labels, the cap exactly) | Question (short, 300) · Options (paragraph, `A \| B \| C`) · Hours (short, blank = `poll_default_hours`) · **Kind** `RadioGroup` single/checkbox/yesno/rating/date · **Switches** `CheckboxGroup` "Nobody is told who voted" / "Hide the bars until it closes". Typed modal components are already used at `:971–1005`; `picked_values` `:1008` reads them |
| 2 — draft preview (a re-render, **no row written yet**) | Embed `review_card` (`polls.py:714`) of the plan `poll_plan` `:264` returned. Row 0 `Post it` (or `Date slots…` when kind = date) · `Start over` · `Cancel`. Row 1 ChannelSelect "Post it in…". Row 2 RoleSelect "Ping…". Row 3 `Thread: on/off` toggle. Defaults are what the slash command used when an option was omitted (`:1896–1905`) |
| 2a — `Date slots` modal, only for kind = date (4 fields) | start · slots · step · **step unit** `RadioGroup` hours/days — then `Post it` appears |
| 3 — `Post it` | `store_poll` `:316` then `_post_now` / `_send_for_review`, exactly as `poll_create` does. **One write, one log row** |

⚠️ **Nothing is stored before `Post it`** — `poll_plan` writes no row (`:264`), so a panel
that times out mid-create leaves nothing behind and `draft` gains no new user. See fork I-3.

`recur create` reuses step 1 and step 2, with step 2's row 0 carrying `Repeat…` → a
**cadence modal**: every (`RadioGroup` daily/weekly/monthly) · at (`HH:MM`) · day
(`mon`–`sun` or 1–28) · timezone. `RECUR_NOT_A_DATE` (`polls.py:252`) still refuses a date
poll, in words, before the cadence modal opens.

**Settings** (staff) — a re-render of the panel whose embed is `_settings_lines` `:2378` +
`_health_lines` `:2403`, five rows:

| Row | Controls |
|---|---|
| 0 | `Polls: on/off` · `Create: staff/everyone` · `Review: on/off` · `Threads: on/off` · `Drop votes: on/off` |
| 1 | ChannelSelect "Where dashboard polls go…" |
| 2 | RoleSelect "Ping role…" |
| 3 | Select "Date slot labels…" (plain / timestamp) |
| 4 | `Numbers…` (modal: default hours · reminder minutes · archive days · panel minutes) · `Clear ping role` · `Clear channel` · `Back` |

Every write goes through `store.set` / `store.clear` and **one** `poll.settings` log line per
submit, as `:2360–2376` does today.

**Logs** — `LogsButton` → `send_logs(interaction, "poll")` as a NEW ephemeral followup, the
same three lines as `cogs/community/requests.py:704–709`. ⚠️ The `count` / `important_only`
arguments (`:1821–1822`) are LOST, as they were for `/request`; the site's Logs page has both.

## D. Settings (P13 / checklist 33)

| Key | Type | Default | What it decides |
|---|---|---|---|
| `poll_panel_minutes` | `int` | **10** | how long the panel stays live. Help text must carry the KI-20 sentence verbatim in shape: the "gone quiet" footer can only be written while Discord's 15-minute interaction token is open, so **15 or more means the buttons stop with no footer**. Nothing is clamped |
| `poll_creator_may_end` | `bool` | **True** (owner, 2026-09-03 12:20, via birthdays F-B1: keep today's behaviour) | whether the `End` button renders for the poll's creator; staff always get it. §I-2 |

Registered the three places `request_panel_minutes` is — `settings_store.py:876` `KEY_TYPES`,
`:892` `KEY_HELP`, `:1305` `default()` — appended in the polls block so wave-1 merges stay
textual. The eleven existing `poll_*` keys (`:188–198` types, `:279–282` choices, `:534–559`
help, `:1235–1255` defaults) are unchanged. **Nothing else here is a decision:** the 25 cap and
the 5-component modal cap are Discord's, the button tables are the state machine.

## E. What goes away, and every line that names it

The two `Group`s (`:1588`, `:1589`) and all eleven subcommands. `/help` reads the tree
(`cogs/core.py:85 tree_commands`) so it follows with no edit.

| File:line | What it says now |
|---|---|
| `docs/access/sweeps.md:41` | row 6 — `/poll create` … `/poll end` |
| `docs/access/sweeps.md:43` | row 8 — `/poll create … anonymous:true` |
| `docs/access/sweeps.md:44` | row 9 — `/poll recur create` |
| `docs/access/sweeps.md:62` | row 27 — `/poll create` with `anonymous:true` |
| `docs/info/feature-list.md:53` | F15 row lists both command sets verbatim |
| `docs/info/phase10-design.md:24`, `:69`, `:111`, `:120`, `:121` | the phase doc — gets a dated "superseded by the panel" line, **not** a rewrite of history |
| `docs/info/code-notes.md:2813`, `:2814`, `:2888` | notes naming `/poll recur delete`, `kind:date`, `/poll` + `/poll recur` |
| `site/public/assets/page-polls.js:51`, `:66`, `:75` | site copy naming `/poll` commands |
| `tests/test_bot.py:21` | `LOGS_GROUPS` entry `"poll": "poll"` — **delete**; the loops at `:181` and `:227` follow |
| `tests/test_bot.py:204` | `assert len(top) == 44` — **unchanged** (requests deviation 7) |
| `tests/test_bot.py:71` | `MEMBER_COMMANDS` keeps `"poll"` — the panel stays member-visible (§B) |

✅ **`docs/access/OWNER_GUIDE.md` needs no edit** — re-measured at build time: 86 lines, and
the word "poll" still does not appear anywhere in it. ⚠️ **`docs/KNOWN_ISSUES.md` DID need one:**
KI-19 stands as written, but KI-20's symptom named `/request` specifically and its help-text
sentence named `request_panel_minutes` specifically. It was widened to "an ephemeral panel"
built on `panels.py`, naming both `/request` and `/poll` and both keys — one fact, one home,
rather than a second near-identical entry per feature wave.

## F. Extractions (P4)

⚠️ **`black_bloc/polls.py` has NO database and no gateway** (imports: logging, datetime,
typing, discord, timezones; `code-notes.md:2645` — "the rule book, with no gateway in it"). So
P4's "extract into the pure module" splits in two, and the build must not break that:

**Pure → `black_bloc/polls.py`:**

| New | Signature |
|---|---|
| `MoveButton` + `CARD_BUTTONS` + `card_buttons(status, *, staff, is_creator)` | mirrors `requests.py:392`/`:419`; the §C table as data |
| `poll_id_from(text) -> int \| None` | the `#`-stripping parse inlined at `:1960` and `:2283` |
| `summary_line(row, now)` / `recur_line(row)` | the list lines inlined at `:2074–2081` and `:2208–2215` |
| `recurrence_card(...) -> discord.Embed` | the recurrence card §C needs; no builder exists |

**DB/log → module level in `cogs/community/polls.py`**, beside `close_poll` / `cancel_poll` /
`apply_decision`, each `(said, fresh_row)` and each taking `via: str = VIA_DISCORD`:

| New | Replaces |
|---|---|
| `pause_recurrence(bot, guild, row, actor, *, via)` | inline `:2231–2241` |
| `resume_recurrence(bot, guild, row, actor, *, via)` | inline `:2242–2259` |
| `delete_recurrence(bot, guild, row, actor, *, via)` | inline `:2267–2276` |
| `save_recurrence(bot, guild, row, token, at, tz, actor, *, via)` | inline `:2181–2194` |
| `apply_poll_settings(bot, guild, actor, changes, clears) -> dict` | inline `:2343–2376` |

⚠️ **`black_bloc/api/tools/polls.py:436` already writes pause / resume / delete from the
dashboard** (`code-notes.md:2826`). Point those routes at the three functions above in the same
commit — that is checklist 17/34's whole point, and it is why they take `via`.

**Two deduplications the build should also do:** (1) `cogs/community/polls.py:1041 answer()`
is a byte-for-byte second copy of `panels.py:17 answer()` — delete it, import the library's;
(2) `panels.option_label(ident, status, text, limit)` — wave-0 **deviation 2** left
`requests.py:443 option_label` unextracted "for the first feature wave that actually needs a
second copy", and this is that wave. ⚠️ Events and birthdays are being designed in parallel;
if one lands the extraction first, **use theirs** rather than adding a third.

## G. Tests (P16 — mirror the package)

| File | What it must prove |
|---|---|
| `tests/cogs/community/test_polls.py` | `/poll` answers ephemerally with a panel; a member sees Create+Find+Refresh and no Settings/Logs/recurring select; staff see all of it; polls off / not-a-creator hide `Create` and say so in the embed; the pick select caps at 25 and its placeholder says so; the site link only with an origin; **parametrised over every member of `polls.py:85 STATUSES`** — the card renders exactly its §C row and no other; `End` renders for the creator and for staff and for nobody else; each button calls its shared function with `via` untouched (mock it); the create modal → preview → `Post it` writes exactly one row through `store_poll`; the date branch demands step 2a; Approve/Deny go through `apply_decision`; recurrence pause/resume/delete go through the new functions; a demoted staffer moves nothing (`still_staff`); guard refuses in test mode; `Logs` answers a new followup and still refuses a demoted staffer; timeout disables every item |
| `tests/test_polls.py` | `card_buttons` for every status, `poll_id_from`, `summary_line`, `recur_line`, `recurrence_card` |
| `tests/test_settings_store.py` | `poll_panel_minutes` round-trips and defaults to 10 |
| `tests/test_bot.py` | `LOGS_GROUPS` without `poll`; `len(top) == 44` still |
| `tests/test_panels.py` | `option_label`, if this wave is the one that extracts it |
| `tests/api/` | the three recurrence routes still pass through the extracted functions |

The existing shared-function tests (`close_poll`, `cancel_poll`, `apply_decision`,
`post_poll`, the loop, the vote buttons) **stay green untouched** — that is the proof the
refactor changed nothing.

## H. §J — prove before merge (P17), and the sweep rows

1. `python -m black_bloc` boots; read `commands synced` — expect **44**, unchanged.
2. The parametrised test proves every status renders its row and no other.
3. `ruff`; full `pytest`; `node site/mock/check.mjs`; `node --input-type=module --check <
   site/public/assets/labels.js`.
4. Confirm `black_bloc/polls.py` still imports no database module.

**`docs/access/sweeps.md` rows — take numbers from 80** (rows 66–72 belong to the two feature
builds in flight, events takes 73–79; owner's reservation, `docs/TODO.md`): 80 `/poll` opens a
panel · 81 create through the two-step modal and `Post it` · 82 a date poll through step 2a ·
83 pick an open poll → `End` → the result posts · 84 `Cancel` from the card · 85 review on →
Approve/Deny from the panel (not the card) · 86 a recurrence pause → resume → delete.
Rows 6, 8, 9 and 27 are rewritten in place, not added.

## I. The genuine forks — owner decisions, one at a time

1. ✅ **SETTLED by the owner's standing rule, 2026-09-03 (reviewer, not a new owner call):**
   `denied` gains `→ open`. `TRANSITIONS[DENIED] = (OPEN,)`; the `denied` card renders a staff
   `Post it anyway` (success) that calls `apply_decision(…, OPEN)` — its DM branch already
   treats everything but `DENIED` as an approval (`:1390`), so the creator is told it was
   approved after all. The parametrised test and every `can_transition` caller follow the
   table; `TERMINAL_STATUSES` loses `denied`. *"Never design a terminal state staff cannot
   leave"* (`CLAUDE.md`) is the whole reason.
2. **Does the panel keep letting a poll's creator end their own poll?** `/poll end` accepts
   creator-or-staff today (`:1978`). **Settled the same way as birthdays F-B1** — the owner
   answers ONE question for both: keep today's member permission as the default, or go
   staff-only as requests did (deviation 12). Either way it is a key, `poll_creator_may_end`
   (bool), registered beside `poll_panel_minutes` (§D). ✅ **DECIDED 2026-09-03 12:20: keep
   today's behaviour — default True.** If you can post it, you can close it; staff sit above.
3. ✅ **SETTLED (reviewer): nothing is written before `Post it`.** One write, one log row
   (checklist 34), no orphan rows, and `draft` stays unused. A timed-out create costs one
   modal's typing, which the 10-minute default and the "gone quiet" footer already bound.

## Deviations

Written by the build agent, 2026-09-03. Everything not listed here was built as this
document says.

1. **`card_buttons` takes a third keyword, `creator_may_end`.** §F's signature is
   `card_buttons(status, *, staff, is_creator)`. The `poll_creator_may_end` key (§D) has to be
   answered somewhere, and the alternative was for every caller to pass
   `is_creator=(theirs and the_key)` — a parameter whose name would then be a lie. The keyword
   defaults to `True`, so `card_buttons(status, staff=…, is_creator=…)` still reads exactly as
   the design wrote it.
2. **`MoveButton` gained a `staff_only` field rather than the table being split.** §C's table
   marks `End` as "rendered for the creator **or** staff" and everything else as staff. One
   boolean on the row keeps the table the single source of that fact; a second member-only
   table would have been the "two spellings of one move" P3 forbids.
3. **`summary_line(row, closes)` and `recur_line(row, following)` take the parsed datetime;
   they do not parse it.** §F writes `summary_line(row, now)`. ⚠️ **`black_bloc/polls.py`
   cannot import `golive.parse_ts`**: `golive` → `settings_store` → `polls` is an import cycle
   (`settings_store.py:35` imports `polls`), and `panels` → `settings_store` → `polls` is the
   same cycle, which is also why the pure module cannot use `capped_placeholder`. Passing the
   parsed value in from the cog is what keeps §H item 4 true — measured: `polls.py` imports
   `logging`, `datetime`, `typing`, `discord` and `.timezones`, and nothing else.
4. **The `Kind` radio offers `KNOWN_KINDS` (single / checkbox / yesno / rating / date), not
   `KINDS`.** §C's step-1 table names exactly those five, but the retired `/poll create` offered
   all eight, so `text` / `number` / `ranked` used to be typeable and were refused by name with
   `KIND_NOT_YET`. Those three are now unreachable from Discord (the web route still accepts
   them and still gets the refusal). The sentence is kept, not deleted — the v2 kinds are still
   on the roadmap and `surface_for` is still their gate.
5. **`Find #…` is its own `AnswersErrors` + `discord.ui.Modal` with one SHORT field, not the
   library's `NoteModal`.** §B calls it "a one-field modal"; `panels.NoteModal` is a paragraph
   box, and a paragraph box for `12` reads wrong. It follows P12's shape (the shared mixin, one
   labelled field) without pretending a poll number is a note. `poll_id_from` does the parsing,
   so `#12`, `12` and `  12  ` all work and `wibble` is refused in words.
6. **`apply_poll_settings` does NOT take `via`.** §F's table says each extracted function takes
   `via: str = VIA_DISCORD`; the other four do. This one is the exception because **no web route
   calls it** — the dashboard writes poll settings through the generic settings API, which logs
   `web.settings.set` itself. Adding a parameter no caller can pass, whose kind
   (`web.poll.settings`) nothing emits, would be dead weight. The other four routes WERE
   rewired: `api/tools/polls.py`'s pause / resume / delete now call the shared functions with
   `via=VIA_WEBSITE` and their own `note()` calls are deleted, which is checklist 34 and is
   pinned by the existing AST test in `tests/test_logkinds.py`.
7. **`RECUR_FUNCS` holds lambdas, not direct references**, so the shared function behind each
   recurrence button is late-bound and a test can prove the button goes through it rather than
   through a private path. `MOVE_FUNCS` was already this shape in `requests.py`.
8. **All five components of the create modal are wrapped in `discord.ui.Label`, including the
   three text fields.** §C's table implies `Label` only for the `RadioGroup` and the
   `CheckboxGroup`. Measured against the installed 2.7.1: a bare `TextInput` still works, but a
   modal mixing bare inputs with labels serialises to a payload carrying BOTH an action row and
   label components, and `TextInput(label=…)` raises a `DeprecationWarning` pointing at exactly
   this shape. Wrapping all five is one consistent modal and no warnings. ⚠️ It has NOT been
   rendered by a real Discord client — see the header.
9. **Strings that named a retired subcommand were rewritten, not just the docs.** `POLLS_OFF`,
   `NOT_A_CREATOR`, `NOT_AN_ID`, `NO_SUCH_POLL`, `NO_OPEN_POLLS`, `RECUR_NONE`,
   `RECUR_NOT_A_DATE`, `NOT_A_RECURRENCE`, three `KEY_HELP` entries (`poll_mode`,
   `poll_who_can_create`, `poll_channel_id`) and three lines of `site/public/assets/page-polls.js`
   told people to run `/poll settings mode:on`, `/poll list`, `/poll recur create` and so on.
   §E lists the docs; a refusal that names a command nobody can type is a worse bug than a stale
   doc, so they were rewritten in the same commit and their tests moved with them.
10. **A member who types a REPEATING poll's number into `Find #…` is refused in words rather
   than shown the recurrence card.** §B says `Find #…` opens "the card for **any** poll id in
   this guild"; §B's row 2 also makes the "Repeating polls…" select staff-only, so a member
   reaching a template by number would have been a way around that. `open_card` answers
   `store.staff_refusal(...)` for a `RECURRING` row and a member; every other status is open to
   anybody exactly as the design says, because the card IS the results and `/poll results` had
   no staff gate either.

### What §H asked for, and what it got

| # | Asked | Result |
|---|---|---|
| 1 | boot, read `commands synced` | ⚠️ **substituted.** No bot token in the build environment (same as wave 0 deviation 5). Instead every cog in `bot.COGS` was loaded into a real `BlackBlocBot` tree and its length read: **44**, unchanged, with `/poll` no longer an `app_commands.Group` and carrying no children. `tests/test_bot.py::test_the_command_tree_stays_inside_discords_limits` asserts the same number. |
| 2 | every status renders its row and no other | ✅ `tests/test_polls.py` parametrises `card_buttons` over `polls.STATUSES` for staff, for a bystander and for the author; `tests/cogs/community/test_polls.py::test_the_card_renders_exactly_the_buttons_the_table_says` does the same against the rendered view, and checks Discord's 5-per-row cap and the "nothing moves it now" footer. |
| 3 | ruff · full pytest · `check.mjs` · `labels.js` parse | ✅ all four. `ruff check .` clean; **3526 pass** (3442 collected at the base, of which 3441 passed — see the flake below); `check.mjs` 17 pages / 142 routes; `labels.js` AND `page-polls.js` parse as ES modules. ⚠️ One pre-existing flake, `tests/api/test_settings_api.py::test_writes_are_rate_limited_per_session`, fails under whole-suite `-n auto` — **measured on a throwaway worktree of the base commit `d3da02c` and it fails there too**, so it is not this build's. |
| 4 | `polls.py` still imports no database | ✅ measured by walking its AST: `logging`, `datetime`, `typing`, `discord`, `.timezones`. See deviation 3 for what that cost. |
| — | sweep rows | ✅ 80–86 appended to `docs/access/sweeps.md`, rows 6, 8, 9 and 27 rewritten in place, header count 72 → 79. Rows 73–79 left untouched for the events build. |
