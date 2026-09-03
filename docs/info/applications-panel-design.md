# Applications — `/applications` is ONE command that opens a panel

> **Audience:** the build agent and the reviewer. **Status:** TRACKED · ✅ **SHIPPED — live in v66** (`853776c`, 15:00, `deploys.log` line 65; synced 42 app commands measured on the boot log). Built on
> `worktree-agent-abf063b9177e02f17`** (base `main` `27452ac`, after the birthdays/events/polls
> panels merged). Merged `--no-ff` `853776c` after Fable review 2026-09-03 (3697 tests).
> **Last verified: 2026-09-03** — the build measured `len(bot.tree.get_commands())` at **42**
> (43 at the base: exactly the one-slot drop §B predicts), **3697 tests pass** (3644 at the base),
> `ruff check .` clean, `node site/mock/check.mjs` **17 pages / 142 routes** (unchanged by this
> build — 142 is what `main` reads today, not the 141 §H guessed at `9891f71`), and both site
> assets parse under `node --input-type=module --check`.
> ⚠️ **NOT verified: anything against live Discord.** No boot (`python -m black_bloc` needs a
> token this environment does not have — `python -c "import …"` is the substitute, and it passes),
> no panel opened, no button pressed, and in particular **no empty-select submit** (§C's one
> unverified edge, the same one the events build flagged). Sweep rows 94–102 are the by-eye list.
> The §A/§C/§E `path:line` keys below were read at **`9891f71`** and have drifted by three merges
> plus this build; trust the anchor text. Every `path:line` below was read at that commit, in
> `black_bloc/applications.py`,
> `cogs/community/applications.py`, `api/tools/applications.py`, `panels.py`, `settings_store.py`,
> `command_visibility.py`, `logkinds.py`, `personas.py`, `tests/test_bot.py`,
> `tests/cogs/community/test_applications.py`, `docs/access/sweeps.md`, `docs/info/code-notes.md`.
> ⚠️ **NOT verified:** nothing was run — no boot, no pytest, no Discord, no site. Whether the client
> submits an EMPTY `RoleSelect`/`ChannelSelect`/`UserSelect` at `min_values=0` is the same unverified
> edge [`events-panel-design.md`](events-panel-design.md) flags; §C names the same fallback.
>
> **Inherits every invariant in [`panels-program.md`](panels-program.md) §2 (P1–P17) and its §4
> library — none restated here.** Template: [`requests-panel-design.md`](requests-panel-design.md),
> whose `## Deviations` foot is the trap list (1 defer-then-edit, 4 the member select's placeholder,
> 5 the 5-per-row cap, 7 `commands synced` does not always drop, 9 `retire`, 10 the 15-minute footer,
> 11 `still_staff` not `require_staff` after a defer). Feature behaviour is
> [`phase19-design.md`](phase19-design.md) and [`applications-no-role-design.md`](applications-no-role-design.md)
> (**merged**, schema 28) — this design builds ON the no-role pass and undoes none of it.

## A. Measured today — two groups, seventeen subcommands

`apply` is a `Group` (`cogs/community/applications.py:855`, **member-visible**, no
`default_permissions`); `applications` is a `Group` (`:858`, `default_permissions=STAFF_ONLY`) with a
nested `question` group (`:1143`). **3 + 14 = seventeen leaf subcommands over two top-level slots.**

| Subcommand | Line | Who | Calls · what is INLINE in the cog |
|---|---|---|---|
| `/apply start <form>` | `:916` | anyone; autocomplete `_apply_start_forms` `:924` over open forms | `_form` `:903` → `open_form_modal` `:669` → `ApplyModal` `:609` → `submit_application` `:326` |
| `/apply status` | `:928` | anyone, own rows only | `applications_for(user_id=…)` `:936`; ⚠️ **lines built inline** `:942–958` (`YOUR_APPLICATION` `:86`) |
| `/apply withdraw <form>` | `:960` | anyone, own row | `withdraw_application` `:379` — shared |
| `/applications mode` | `:977` | `require_staff` `:984` | ⚠️ **inline** `:986–996`: `store.set` + `log_action("application.mode")` + `MODE_SAID` |
| `/applications create` | `:998` | `require_staff` `:1015` | ⚠️ **inline** `:1017–1044`: `create_form` `:1018`, `NAME_TAKEN`, log, `FORM_CREATED` |
| `/applications edit` | `:1046` | `require_staff` `:1075` | ⚠️ **inline** `:1077–1108`: `ROLE_OR_NO_ROLE`, `role_id = … NO_ROLE if no_role`, `update_form`, log |
| `/applications delete` | `:1114` | `require_staff` | ⚠️ **inline** `:1122–1137`: `pending_count` guard (`FORM_HAS_PENDING`), `delete_form`, log |
| `/applications question add\|edit\|remove` | `:1149` `:1198` `:1255` | `require_staff` | ⚠️ **inline** `:1174–1196`, `:1225–1253`, `:1268–1282`: the module call + one `application.question_changed` log + the sentence |
| `/applications question list` | `:1284` | `require_staff` | `questions_for`; ⚠️ **lines inline** `:1296–1301` |
| `/applications panel` | `:1319` | `require_staff` | ⚠️ **inline** `:1332–1367`: guard check, `post_panel` `:314`, `application.post_failed` / `panel_posted`, `PANEL_POSTED` |
| `/applications list` | `:1373` | `require_staff` | `list_forms`, `applications_for(limit=25)`, `twitch_logins_for`; ⚠️ **all line building inline** `:1406–1435` |
| `/applications show <id>` | `:1441` | `require_staff` | `render_card` (`applications.py:427`) + `show_panel` `:838` → `ShowPanel` `:788` + `TakeOffButton` `:793` — **the first partial panel, already built** |
| `/applications approve` · `deny` | `:1466` `:1477` | `_decide` `:1490` → **`may_decide` `:165` — the approver ROLE, then staff** | `apply_decision` `:408` — shared |
| `/applications logs` | `:1514` | `send_logs` carries its own `require_staff` | `send_logs(interaction, "applications", count, important_only)` |

**Not subcommands and NOT moving** (P14): the per-form **Apply** post (`ApplyButton` `:704`,
`DynamicItem`, re-registered in `cog_load` `:864`) and the review card's **Approve/Deny**
(`DecisionButton` `:733` → `apply_decision`, `DenyModal` `:645`). Those belong to the room. The panel
is a SECOND door onto the same `apply_decision`.

**States** (`black_bloc/applications.py:37–45`) — `TRANSITIONS` is the whole machine:

| From | May become |
|---|---|
| `pending` | `approved` · `denied` · `withdrawn` |
| `approved` | `removed` (the no-role pass) |
| `denied` · `withdrawn` · `removed` | nothing today — see §C and §I |

⚠️ **`decide_application` `:836` hard-codes `may_move(PENDING, status)` and `WHERE status = 'pending'`**;
`remove_application` `:856` hard-codes `WHERE status = 'approved'`. Any new transition needs its own
writer, not a wider `decide_application` — §F names it.

**Three-way audience, measured:** member (`/apply*`), **approver** (`may_decide` `:165` — the form's
`approver_role_id`, else the setting, else staff), staff (`require_staff` everywhere else).
`can_decide` `:158` is the same question with no refusal sent, which is what renders a button.

## B. The decision — one `/applications`, member panel and staff panel

**`/applications` becomes a single `app_commands.command`; both `Group`s go and `/apply` disappears.**
`commands synced` drops by **one** relative to whatever it is when this lands (two top-level slots
become one). ⚠️ **State the delta, not the number** — events retires `/timezone` too, and polls and
birthdays collapse theirs; the build **re-measures** `commands synced` at boot and edits
`tests/test_bot.py:204` to what it reads (requests deviation 7 is why this is measured, not asserted).

⚠️ **The one command MUST be member-visible — it carries `no default_permissions`**, because the
member half (`/apply`) has none today. `"applications"` therefore moves from `STAFF_COMMANDS`
(`tests/test_bot.py:32`) to `MEMBER_COMMANDS`, and `"apply"` (`:63`) goes. The staff half is gated at
runtime as it always was (`require_staff` / `may_decide`), never by the UX lock.

**Root panel** — `build_panel(bot, guild, actor)`, one ephemeral embed + `Panel` subclass, split on
`store.is_staff(actor) or decides_anything(...)` (§F: an approver who is not staff still gets the
queue, and sees only forms they may decide).

| Row | Member sees | Staff / approver sees instead |
|---|---|---|
| 0 | Select **"Apply for…"** — open forms (`list_forms(open_only=True)`), ≤25, `capped_placeholder` (`panels.py:55`). Picking one opens `ApplyModal` **unchanged** | Select **"Pick an application…"** — the queue, `applications_for(statuses=(PENDING,))` on forms they may decide, pending-first order the query already gives (`applications.py:823`), 25 cap |
| 1 | Select **"Take one back…"** — the caller's own `pending` rows → Yes/Keep confirm → `withdraw_application` `:379` | Select **"A form…"** — every form, ≤25 |
| 2 | — | Select **"Take one back…"**, only when the staffer has one of their own |
| 3 | `Refresh` · `Open on the site` (link, `rolemenus.html` — `logkinds.py:104`, only with an origin) | `New form` · `Find #…` · `Settings` · `Logs` · `Refresh` — **five, Discord's per-row cap** |
| 4 | — | `Open on the site` (link) |

Embed **Applications**: intro; `APPLICATIONS_OFF` (`applications.py:110`) as a LINE when the mode is
off, with "Apply for…" simply not rendered (P9 — never a dead button, and it never refuses the whole
command: requests deviation 3); the caller's own applications — the `/apply status` lines `:942–958`
extracted — when `applications_panel_own_list` is on (default **True**, §D), `NOTHING_OF_YOURS`
(cog `:83`, reworded off `/apply start`) when empty; and for staff a counts line (forms · waiting ·
on a list).

**`Find #…`** (new, the polls precedent) — a one-field modal taking `#12` or `12` → the card for any
application id in this guild. It keeps a **settled** row reachable, since the queue select lists
`pending` only, and it replaces the `application_id` argument of `show` / `approve` / `deny`. Staff
apply through the form card's `Fill it in` (§C) rather than a second select, which is what frees row 2
and keeps both panels inside Discord's five rows.

## C. The cards, the sub-panels, the modals

Each is a **re-render in place**, `retire(previous)` first (P6), `defer()` then
`edit_original_response` (P5), `db_ready` on every click (requests deviation 6).

**The application card.** Embed = `render_card(form, row, member)` (`applications.py:427`) — the same
builder the channel card, the DM path and `/applications show` use; a card on the panel and a card in
the channel must never be two shapes. Buttons from a new `CARD_BUTTONS` in `black_bloc/applications.py`
(the shape of `requests.py:392`), keyed by status and filtered by the guards the shared functions
apply (P3):

| Status | Buttons rendered (+ `Back` always) | Shared function |
|---|---|---|
| `pending` | `Approve` (success) · `Deny` (danger, `NoteModal`) | `apply_decision` `:408` (APPROVED / DENIED) |
| `approved`, form keeps a LIST | `Take off the list` (danger, `NoteModal`) | `remove` `:560` — the existing `TakeOffButton` `:793` moves onto this card |
| `approved`, form hands a ROLE over | none — the embed says `/role revoke` is the way off, in the words `REMOVE_IS_FOR_LISTS` `:92` already uses | — |
| `denied` | `Approve after all` (success) — §I, settled | `reinstate` (§F) |
| `removed` | `Put them back on the list` (success) — §I, settled | `reinstate` (§F) |
| `withdrawn` | none — the member took it back and may apply again straight away (`last_decision` `applications.py:777` counts only approved/denied/removed, so no cooling-off applies). The embed says so | — |

Every move is rendered only when `can_decide(bot, guild.id, form, actor)` `:158`, and **every click
re-asks it** — see the `still_may_decide` trap in §F.

**The form card** (staff picked a form). Embed: name · title · open/closed · role chip **or** "keeps a
list" (`role_of` `applications.py:371` — never `<@&None>`) · review channel · approver role · owner +
next step · expires/retry days · question count · where the Apply button is · counts.

| Row | Buttons | Rendered when |
|---|---|---|
| 0 | `Edit…` (sub-panel) · `Questions…` (sub-panel) · `Close it` / `Open it` · `Post the Apply button` · `Back` | always (the third is `is_open` `:396`; the fourth needs a channel — a ChannelSelect appears on its own re-render) |
| 1 | `Roster` · `Fill it in` · `Delete` (danger, confirm) · `Open on the site` | `Roster` only when `role_of(form) is None`; `Fill it in` only when the mode is on, the form is open and the caller has no open application (the same order `open_form_modal` `:669` checks); `Delete` only when `pending_count` `:828` is 0, and the embed says why when it is not |

**Roster sub-panel** (no-role forms) — the Discord twin of the site's `rosterFoldout`: approved rows,
each with `twitch_logins_for` (`applications.py:786`) where linked, honouring
`applications_roster_shows_left`, and a select "Take somebody off…" → `NoteModal` → `remove`. One
query, never one per row.

**Edit sub-panel** — 5 rows exactly: 0 `Words…` (modal: title, description, next step, approved text)
· `Numbers…` (modal: expires days, retry days, clamped by `whole_days` `:266`) · `Back`; 1 `RoleSelect`
"Role it hands over…"; 2 `ChannelSelect` "Where its cards wait…"; 3 `RoleSelect` "Who decides it…";
4 `UserSelect` "Who is nudged next…". ⚠️ **An empty submit at `min_values=0` is CLEAR** — the role
select clearing is exactly `no_role:true` (`forms.NO_ROLE` `applications.py:35`), and `update_form`
`:600` already spells "leave it alone" as `None`. If the client will not submit an empty select
(unverified, see the header), the fallback is one `Forget…` button opening a select of which field to
clear; the write path is identical.

**Questions sub-panel** — select over `questions_for` (≤5, `QUESTIONS_MAX` `:51`) → `Edit` (modal:
label, style, required, placeholder) · `Remove` (confirm) · `Add…` (modal) · `Back`. ⚠️ **Reorder
stays site-only** — it has no slash twin today (`phase19-design.md:309`) and needs drag or a pair of
Up/Down per row; the sub-panel says so and links to the page. Nothing else is retired.

**Settings sub-panel** (staff) — embed is today's seven values as lines. Row 0 mode select
(`forms.MODES`), 1 `ChannelSelect` (`applications_channel_id`), 2 `RoleSelect` (approver), 3
`RoleSelect` (ping), 4 `DMs: on/off` · `Roster shows people who left: on/off` · `Numbers…` (retry days,
panel minutes) · `Open on the site` · `Back`. Every write goes through `store.set`/`clear`; the mode
write goes through the extracted `set_mode` so `application.mode` is logged **once** and the
`command_visibility` `on_change` hook still fires.

**`Logs`** — a button answering a NEW ephemeral followup (P11), `send_logs(interaction, "applications")`,
which carries its own `require_staff` (`actionlog.py`). ⚠️ The `count` / `important_only` options
(`:1516–1517`) are LOST, as they were for `/request`; the site's Logs page has both.

**Modals** — all `AnswersErrors` + `discord.ui.Modal`, one shape (P12). `ApplyModal` `:609` is
**unchanged** (built at open time from the stored questions). Deny / Take off / Put back use
`panels.NoteModal(title=…, label="One line they will be sent", max_length=forms.REASON_MAX)` —
`DenyModal` `:645` is deleted, its 400-clamp and its call unchanged. `New form` is one modal (name,
title, description) and lands on the new form's card, where role/channel/approver are selects.

## D. Settings (P13 · checklist 33)

| Key | Type | Default | Status |
|---|---|---|---|
| `applications_panel_minutes` | `int` | **10** | ✅ **EXISTS** (`settings_store.py:824` `KEY_TYPES`, `:862` `KEY_HELP`, `:1414` `default()`; no-role deviation 2). **Reuse it — do not add a second key.** Its help text names "the /applications show panel" (`:863`) and `labels.js:168` repeats it; both are rewritten to name the panel, the KI-20 warning kept verbatim |
| `applications_roster_shows_left` | `bool` | **True** | ✅ **EXISTS** (`:823`, `:858`, `:1412`). The roster sub-panel honours it exactly as `GET /roster` does (`api/tools/applications.py:379`) |
| `applications_panel_own_list` | `bool` | **True** | **NEW.** Whether a MEMBER sees their own applications written out. **True is today's behaviour** — `/apply status` `:928` has no staff gate — and the owner's standing answer of 2026-09-03 12:20 (birthdays F-B1, polls F2) is *keep today's permission*. False makes it staff-only, matching requests deviation 12. Registered in the applications block at `:815`/`:833`/`:1406` so wave-1 branches merge textually |

Nothing else here is a decision: the 25 cap and the 5-per-row cap are Discord's, the button tables are
`TRANSITIONS`, and the six existing `applications_*` keys are untouched.

## E. What goes away, and every line that names it

`/help` reads the tree (`cogs/core.py`), so it follows with no edit (P15).

| Thing | Where | Becomes |
|---|---|---|
| `apply` Group + 3 children | `:855`, `:916`, `:928`, `:960` | the "Apply for…" select, the own-list embed block, the "Take one back…" select |
| `applications` Group + 11 children + the `question` group's 4 | `:858`, `:1143`, and the §A table | buttons, selects, sub-panels |
| `DenyModal` | `:645` | `panels.NoteModal` |
| `LOGS_GROUPS["applications"]` | `tests/test_bot.py:27` | **deleted** — `/applications` is no longer a `Group` with a `logs` child, so the loops at `:181` and `:227` would `KeyError` |
| `STAFF_COMMANDS` `"applications"` | `tests/test_bot.py:32` | **moves to `MEMBER_COMMANDS`** (§B) |
| `MEMBER_COMMANDS` `"apply"` | `tests/test_bot.py:63` | **deleted** |
| `assert len(top) == 44` | `tests/test_bot.py:204` | **one lower than whatever the build measures at boot** — never a hard-coded absolute (§B) |
| `HIDDEN_WHEN_OFF["applications_mode"] = ("apply",)` | `command_visibility.py:19` | fork **I2** — `("applications",)` or dropped |

**Strings that name a retired subcommand and are rewritten in the SAME commit** — each currently tells
somebody to run something that will not exist: `black_bloc/applications.py:83` `:87` `:96` `:100`
`:104` `:108` `:116` `:123–124` `:135` `:139` `:167` `:177` `:182` `:186`;
`cogs/community/applications.py:40` (`PANEL_TIMEOUT_FOOTER` — "Run /applications show again") `:51`
`:62–63` `:71` `:80` `:84` `:90` `:102` (`MODE_SAID["off"]` says "`/apply` disappears" — see I2);
`black_bloc/personas.py:95–96` (⚠️ **the chat bot's own answer to "how do I join the Twitch Team"**);
`settings_store.py:863`; `site/public/assets/labels.js:168`; `site/public/assets/page-rolemenus.js:78`
`:85`.

**Docs rewritten in the same commit** (P15): `docs/access/sweeps.md` rows 53–57 (`:173–177`), rows
69–72 (`:194–197`) and the whole Twitch-Team walk-through block (`:199–229`, eleven slash lines) —
rewritten in place, not added to; `docs/access/OWNER_GUIDE.md:6–7` (header), `:62` (the sweeps count,
72 today) and `:63` (names `/applications show <id>`); `docs/info/feature-list.md:88`;
`docs/info/architecture.md:23–24` (⚠️ **already stale — says 41 top-level commands**; correct it to
what the build measures); `docs/info/phase19-design.md` gets a dated "superseded by the panel" line at
the top, **not** a rewrite (`:54`, `:56`, `:136`, `:147–148`, `:157`, `:282`, `:286`, `:290`, `:309`);
`docs/info/applications-no-role-design.md` §C3's last row (the `/applications show` panel) gets one
dated line saying the button moved onto the application card; `docs/info/panels-program.md:75` (the
Applications row → shipped); `docs/info/code-notes.md` re-keyed at the merge — the applications
sections at `:4884`, `:4910`, `:5103`, and specifically `:4922` (the `HIDDEN_WHEN_OFF` note),
`:4923` (`extras={"staff_only": True}`), `:5128` (`show_panel`), `:5129` (`/applications list`).

## F. Extractions (P4) — one function per move, called by BOTH doors

⚠️ **The DB/move layer lives in the COG** (`cogs/community/applications.py:228–606`), as it does for
events and not as it does for requests; `api/tools/applications.py:10` imports `apply_decision`,
`post_panel` and `remove` from it. **Do not move the layer** — this build adds to it in place.

⚠️ **The form-CRUD half is DUPLICATED today, and that is checklist 34's exact shape.** The cog logs
`application.form_created` / `form_updated` / `form_deleted` / `question_changed` / `panel_posted`
inline (§A), while the site writes the same event a second way through `note(bot, guild,
"web.application.form_created", …)` (`api/tools/applications.py:237`, `:281`, `:304`, `:321`, `:348`).
`kind_via(kind, VIA_WEBSITE)` (`logkinds.py:357`) produces **exactly** those strings, so pointing both
doors at one function is textually safe and deletes five `note()` calls — the same move requests
deviation 8 made.

**New, module level in `cogs/community/applications.py`** — each does ONE write and ONE log row, each
returns `(what to say, the fresh row)` and each takes `via: str = VIA_DISCORD`:

| Function | Replaces |
|---|---|
| `set_mode(bot, guild, actor, value, *, via)` | inline `:986–996` |
| `make_form(bot, guild, actor, name, title, role_id, …, *, via)` | inline `:1017–1044` (+ the API's `POST /forms`) |
| `save_form(bot, guild, actor, form, changes, *, via)` | inline `:1083–1108` (+ `PATCH /forms/{id}`) — the `NO_ROLE` clearing rule stays exactly as the no-role pass built it |
| `drop_form(bot, guild, actor, form, *, via)` | inline `:1122–1137` (+ `DELETE /forms/{id}`), `FORM_HAS_PENDING` included |
| `change_question(bot, guild, actor, form, what, …, *, via)` | the three inline blocks `:1174–1196`, `:1225–1253`, `:1268–1282` (+ `PUT /forms/{id}/questions`) |
| `put_panel_up(bot, guild, actor, form, target, *, via)` | inline `:1332–1367` (+ `POST /forms/{id}/panel`), guard check and `post_failed` included |
| `reinstate(bot, guild, application_id, actor, *, via)` | **new** — `denied`/`removed` → `approved` (§I). It calls a new `applications.restore_application(db, id, *, decided_by)` (`WHERE status IN ('denied','removed')`, `may_move` asked first) and then the SAME tail `_approve` `:437` uses, so a role form hands the role over and the DM is the approval DM (`decision_lines` `:462` already words `approved` for both role and list). **Extract that tail as `settle_approval(bot, guild, form, fresh, member, actor, until, via)`** rather than copying it |
| `still_may_decide(interaction, form) -> bool` | ⚠️ **the trap.** `may_decide` `:165` ends in `require_staff`, which calls `interaction.response.send_message` directly — after a `defer()` that is requests deviation 11 all over again. The panel's re-check must answer through `panels.answer` on every branch. `can_decide` `:158` stays the render-time question |
| `decides_anything(bot, guild, forms_, user) -> bool` | any(`can_decide`) — what splits the root panel (§B) |

**Pure, into `black_bloc/applications.py`:**

| New | Signature |
|---|---|
| `MoveButton` + `CARD_BUTTONS` + `card_buttons(status, *, has_role, may_decide)` | §C's table AS DATA, proved against `TRANSITIONS` by a parametrised test |
| `restore_application(db, application_id, *, decided_by)` | the third writer beside `decide_application` `:836` and `remove_application` `:856` |
| `application_id_from(text) -> int \| None` | the `#12` parse `Find #…` needs |
| `own_lines(rows, forms_by_id)` / `form_lines(forms_)` / `application_lines(rows, names, logins)` / `question_lines(rows)` / `counts_of(rows)` | the five inline line-builders (`:942–958`, `:1406–1435`, `:1296–1301`) |
| `panel_shows_own_list(store, guild_id)` | the one-liner over `panels.panel_minutes`'s shape, as `requests.py:477` |

**Two deduplications while here:** `cogs/community/role_menus.py:392 answer()` is a third
byte-for-byte copy of `panels.py:17 answer()` — the applications cog imports it from there (`:25`);
import the library's instead. And `panels.option_label` (wave-0 deviation 2) — ⚠️ events, polls and
birthdays may each be extracting it in parallel; **if one has landed it, use theirs**, never a fourth
copy.

## G. Tests (P16 — one file per source file, mirrored paths)

| File | What it gains |
|---|---|
| `tests/cogs/community/test_applications.py` (54 today) | `/applications` answers ephemerally with a panel; a member sees "Apply for…" + "Take one back…" and no queue/Settings/Logs; an APPROVER who is not staff sees the queue for their form only; staff see all of it; the mode being off hides "Apply for…" **and** the embed says so; the own-list block present/absent per key; **parametrised over every member of `STATUSES` — the card renders exactly its §C row and no other**, and the `approved` row differs on `role_of`; each button calls its shared function with `via` untouched (mock it); the queue select caps at 25 and its placeholder says so; `Find #…` finds a settled row; the form card's `Delete` is absent with a pending application and the embed says why; the questions sub-panel adds/edits/removes through the one function; an empty role select clears the role exactly as `no_role:true` did; `Logs` answers a NEW followup and still refuses a demoted staffer; a staffer demoted mid-card moves nothing (`still_may_decide`, every site); `db_ready` after a defer; timeout disables every item and a re-render `retire`s the view it replaced |
| `tests/test_applications.py` (29) | `card_buttons` for every status × role/list × may-decide; `restore_application` (only from `denied`/`removed`, refuses `pending`); `application_id_from`; the five line-builders; `panel_shows_own_list` |
| `tests/api/tools/test_applications.py` (23) | the five form routes still answer the same shapes and now log through `kind_via` — **one row per write, no `web.` duplicate** (assert the log count, not just the kind) |
| `tests/test_settings_store.py` | `applications_panel_own_list` round-trips, defaults True, has help text; the two existing keys unchanged |
| `tests/test_bot.py` | `LOGS_GROUPS` loses `applications`; `applications` moves to `MEMBER_COMMANDS`; `apply` goes; the tree-limit test recounts |
| `tests/test_logkinds.py` | no new kind — `reinstate` logs `application.approved` (its `web.` head via `kind_via`), so `_branches` still counts it |

The existing shared-function tests (`submit_application`, `apply_decision`, `_approve`, `_hand_over`,
`remove`, the persistent buttons, the no-role pass's fifteen) **stay green untouched** — that is the
proof the refactor changed nothing (wave-0 deviation 4).

## H. §J — prove before merge (P17), and the sweep rows

1. `python -m black_bloc` boots; **read `commands synced` and record both numbers** (before, after) —
   the drop must be exactly one for this feature (requests deviation 7; checklist 10 — a check that
   could not run is not a check that passed).
2. The parametrised card test: every status renders its row and no other (checklist 3, 12).
3. `python -c "import black_bloc.applications, black_bloc.cogs.community.applications,
   black_bloc.api.tools.applications, black_bloc.personas"` — the substitute for a boot in an
   environment with no token (wave-0 deviation 5).
4. `ruff`; full `pytest`; `node site/mock/check.mjs` (expect **17 pages / 141 routes**, unchanged —
   this design adds no route); `node --input-type=module --check < site/public/assets/labels.js`
   (⚠️ that file did not parse once before — `code-notes.md:5008`).
5. Checklist sweep before reporting — **8** (`AnswersErrors` on every modal and component), **11**
   (`allowed_mentions` everywhere), **12** (`edit_card` `:286` stays last), **15** and **17** (the
   three `answer` copies and the five duplicated form writes, §F), **22** (`whole_days` /
   `check_length` in the modals), **29** (the `min_values=0` submit checked against installed source,
   not guessed), **30**, **33** (§D), **34** — and 34 is the one this build can fail silently, so
   assert the log-row COUNT, not just the kind.

**Sweep rows — this feature takes 94 onward** (`docs/access/sweeps.md`'s last row today is **72**;
73–79 are reserved for events, 80–86 polls, 87–93 birthdays). Rows 53–57 and 69–72 are rewritten in
place, not added.

| # | Do this | Expect |
|---|---|---|
| 94 | `/applications` as a plain member | one ephemeral panel: intro, your own applications, **Apply for…**, Refresh, Open on the site — and no queue, no Settings, no Logs |
| 95 | Pick a form in **Apply for…** | the same modal `/apply start` opened, the same "Sent to staff" reply, the same DM, the same card in the test channel |
| 96 | **Take one back…** → Yes, then again → Keep it | the first withdraws (the card closes, the row reads withdrawn); the second changes nothing |
| 97 | `/applications` as staff | adds **Pick an application…** (25 cap, "25 of N" past that), **A form…**, New form, Find #…, Settings, Logs — Logs answers a NEW message and the panel stays |
| 98 | Pick a pending application → **Approve**; another → **Deny** with a reason | identical to pressing the buttons on the review card: the DM, the role (or the "on the list" wording), the card edited, ONE log row each |
| 99 | On a denied card press **Approve after all**; on a removed one **Put them back on the list** | the row goes back to approved, the person is DMed the approval, a role form hands the role over, and the log shows `application.approved` |
| 100 | **A form…** → the form card → `Questions…` add/edit/remove; `Edit…` → clear the role select | the questions change one at a time; clearing the role leaves the form keeping a list, exactly as `no_role:true` did — the card's Role line reads "keeps a list" |
| 101 | The form card → `Roster` → take somebody off with a reason; then `Close it`, `Open it`, `Post the Apply button` | the roster is one shorter and they are DMed; the form closes and reopens; the Apply button moves to the chosen channel |
| 102 | `Settings` → flip the mode, pick a channel, submit an EMPTY approver select; then leave the panel `applications_panel_minutes` minutes | the lines update, the empty select clears the key, and the panel goes quiet with the footer |

## I. The genuine forks — the owner decides, one at a time

Settled first, by the two standing rules, so they are NOT put to him:

- ✅ **`denied` and `removed` gain a staff exit** — *"never design a terminal state staff cannot
  leave"* (`CLAUDE.md`, owner 2026-09-03). `TRANSITIONS[DENIED] = (APPROVED,)`,
  `TRANSITIONS[REMOVED] = (APPROVED,)`; the cards render `Approve after all` / `Put them back on the
  list` through `reinstate` (§F), which DMs the person the approval and, on a role form, hands the
  role over. `withdrawn` stays terminal for staff **because the member owns it** and the way back is
  applying again, which no cooling-off blocks (`last_decision` `:777`).
- ✅ **A member keeps seeing their own applications** — *"if you can post it you can withdraw it"*, the
  owner's 2026-09-03 answer for polls and birthdays: today's permission is the default, as a key.
  `applications_panel_own_list` default **True** (§D).
- ✅ **Every removal and denial still carries a DM'd reason** — the no-role pass settled it (D2 there);
  the panel changes nothing but the door.

The three that are genuinely his:

- ✅ **I-A1 — DECIDED by the owner 2026-09-03 13:35: `/apply` ("it's gamer lingo").** The one
  command is `/apply`; the `applications` Group goes entirely. Everywhere this document says
  `/applications` for the COMMAND, read `/apply`; the feature, the log kinds, the settings keys and
  the site section keep the word "applications". Description: "Apply for something — staff manage
  the forms here too". `"apply"` stays in `MEMBER_COMMANDS`; `"applications"` leaves `STAFF_COMMANDS`.
  Original question: what is the command CALLED, `/applications` or `/apply`? One command has to carry both
  halves. `/applications` is what the feature, the logs, the settings keys and the site section are
  called, and it is what this document assumes; `/apply` is the word a member reaching for it would
  actually type, and it is the half that gets used a hundred times to the staff half's one.
  **Recommended: `/applications`**, with the description reading "Apply for something, or manage the
  forms" so the search box finds it either way. Whichever he picks, it is member-visible (§B).
- ✅ **I-A2 — DECIDED by the owner 2026-09-03 13:47: "Visible".** `/apply` stays in Discord when
  `applications_mode` is off: the `HIDDEN_WHEN_OFF["applications_mode"]` entry goes, the panel says
  the feature is off in words and renders no Apply control, staff keep their door. Sweeps row 53
  (the vanishing act) is rewritten to test the off-panel wording instead.
  Original question: does the command still DISAPPEAR when applications are off? Today
  `HIDDEN_WHEN_OFF["applications_mode"] = ("apply",)` (`command_visibility.py:19`) hides the member
  group within about five seconds and leaves `/applications` for staff (sweeps row 53 tests exactly
  that). With one command, hiding it hides staff's only Discord door to form management, and the mode
  can then only be turned back on from the site or `/settings set-value`.
  **Recommended: drop the entry** — the command stays, and with the mode off the panel says so in
  words and renders no Apply control (P9). The alternative is `("applications",)`, which keeps the
  vanishing act he asked for and costs staff the Discord door.
- ✅ **I-A3 — DECIDED by the owner 2026-09-03 14:12: "Build the question sub panel".** §C's
  Questions sub-panel is built as designed (select → Edit / Remove, plus Add); reorder stays site-only.
  Original question: does question EDITING stay in Discord at all? §C designs a Questions sub-panel (select →
  Edit / Remove, plus Add), so nothing is retired; but the site already owns a better editor with
  drag-reorder (`page-rolemenus.js`, `PUT /forms/{id}/questions`), and reorder will stay site-only
  either way. **Recommended: build the sub-panel** — a form with no questions cannot be applied for
  (`NO_QUESTIONS_YET`), so "make a form and put its questions on it" is a Discord-first job. The
  alternative is a `Questions…` button that answers one line and a link, which is smaller to build
  and leaves a staffer with a phone unable to finish a form.

## Deviations

Written by the build agent, 2026-09-03. Everything not listed here was built as this document
says, including all three decided forks (I-A1 `/apply`, I-A2 Visible, I-A3 build the Questions
sub-panel).

1. **`update_form` now clears FOUR id columns from the `NO_ROLE` sentinel, not one.** §C says an
   empty `RoleSelect` submit is CLEAR and points at `no_role:true`; but `update_form`
   (`black_bloc/applications.py`) drops every `None` as "leave it alone", so the sentinel was the
   only way to clear ANYTHING — and it was wired to `role_id` alone. The Edit sub-panel's other
   three pickers (review channel, approver role, form owner) would silently have done nothing when
   submitted empty, which is the "a control that looks like it worked and did not" defect. A new
   `CLEARABLE_IDS = ("role_id", "review_channel_id", "approver_role_id", "owner_user_id")` maps
   `0 → NULL` for each. Existing callers are untouched: the site never sends `0`, and the role
   half behaves exactly as the no-role pass built it.
2. **`settle_approval` computes `until` itself rather than taking it as an argument.** §F's
   signature is `settle_approval(bot, guild, form, fresh, member, actor, until, via)`. `until` is
   `grants.expires_at(forms.expires_days_of(form))` on a role form and `None` otherwise — a pure
   function of `form`, which is already a parameter. Passing it would let the two callers
   (`_approve`, `reinstate`) disagree about the expiry of the same approval; deriving it once
   inside cannot.
3. **`set_mode` takes `via` but no route calls it.** §F asks for it, and the kind is now
   `kind_via("application.mode", via)`. The site changes the mode through the Settings page, which
   logs its own `settings.set` row, so `web.application.mode` is a kind nothing emits today. It
   costs nothing and it means the fifth door, if one is ever built, cannot forget.
4. **The Settings sub-panel carries `applications_panel_own_list` as a toggle, and drops "DMs" and
   "Roster shows people who left" onto the same row.** §C's row 4 lists five things and Discord
   caps a row at five; adding the new key would have been a sixth. The row is now three toggles +
   **Numbers…** + **Back**, and the **Open on the site** link moved off it (the root panel and the
   form card both carry one). Checklist 33 is satisfied either way — the key is in the registry, so
   the Settings page and `/settings set-value` reach it — but a Lead should not have to leave
   Discord to flip a decision the panel itself is about.
5. **`Find #…` and the two confirm steps use `panels.NoteModal`, and `DenyModal` became a subclass
   of it.** §C only names `NoteModal` for Deny / Take off / Put back. `FindModal` is a one-field
   text modal with a different label and a 12-character cap — the same shape, so a second modal
   class would have been checklist item 17's exact defect. `DenyModal` (the CHANNEL card's, which
   §E said to delete) is kept as a name, because the persistent `DecisionButton` that P14 leaves
   alone constructs it — but its body is now three lines over the shared modal instead of a second
   `TextInput` declaration.
6. **The member's "Take one back…" select goes through a Yes/Keep confirm, and picks a FORM, not an
   application.** §B row 1 says "the caller's own `pending` rows → Yes/Keep confirm →
   `withdraw_application`". `withdraw_application(bot, guild, member, form)` takes a form, not an
   application id, and finds the open row itself — so the select's value is the form id and the
   shared function is called exactly as `/apply withdraw` called it. Same rows offered, same write.
7. **Staff are given no "Apply for…" picker at all**, as §B's table says, and reach a form through
   **A form…** → **Fill it in**. A non-staff APPROVER gets both (queue on row 0, Apply for… on row
   1) — §B's split is on `is_staff or decides_anything`, but form management is staff-only, so an
   approver who is not staff is a member with a queue rather than a staffer.
8. **The question Edit/Add modal spells `style` and `required` as text boxes** (`short`/`long`,
   `yes`/`no`), because §C asks for one modal carrying all four fields and a Discord modal holds
   only `TextInput`s. A blank box keeps what the question already had; `check_style` refuses a
   third word in its own sentence. The alternative — two toggle buttons on the question card — was
   not built.
9. **`PANEL_MINUTES_KEY`, `ROSTER_SHOWS_LEFT_KEY`, `PANEL_TIMEOUT_FOOTER` and the four `/apply
   status` strings moved from the cog into `black_bloc/applications.py`**, where every other
   feature keeps them (`requests.py`, `events.py`, `polls.py`, `birthdays.py` all do). The cog
   re-exports the two keys by name so no import outside it moved except
   `api/tools/applications.py`'s, which now reads `forms.ROSTER_SHOWS_LEFT_KEY`.
10. **`api/tools/applications.py`'s `checked()` helper was deleted, not kept.** Its three callers
    became `make_form` / `save_form` / `change_question`, each of which already returns the
    wording refusal rather than raising, so the wrapper had nothing left to wrap. The 400s and
    their sentences are unchanged — `tests/api/tools/test_applications.py` proves that, untouched.
11. **§H item 1 (a real boot, reading `commands synced`) was NOT run** — no token here. The number
    was measured the only other way it can be: `tests/test_bot.py::test_the_command_tree_stays_inside_discords_limits`
    counts `bot.tree.get_commands()` after loading every cog, which is what `command_sync.py`
    syncs. **43 before, 42 after**, and the drop is exactly the one slot §B predicts.
    `python -c "import black_bloc.applications, black_bloc.cogs.community.applications,
    black_bloc.api.tools.applications, black_bloc.personas"` passes (§H item 3).
12. **§H item 4's route count is 142, not 141.** `node site/mock/check.mjs` reports **17 pages /
    142 routes** on `main` at `27452ac` — the design's 141 was measured at `9891f71`, before
    polls. This build adds no route and `site/mock/contract.json` is untouched, so 142 is the
    unchanged number.
13. **The Roster sub-panel does not honour a 25-cap placeholder on its LIST, only on its select.**
    The embed writes every approved row it is allowed to show (clamped at 4000 characters, one
    query, as §C requires); the "Take somebody off…" select caps at 25 with the shared
    `capped_placeholder`. A roster past 25 is still fully readable, just not fully actionable from
    Discord — the site's roster is the other door and the placeholder says so.
15. **A `db_up(interaction)` gate was added for the reads that happen BEFORE a defer.**
    `db_ready` (the library's) answers a *followup*, so it only works once something has
    deferred — but a button that opens a MODAL cannot defer first, and several of them read the
    form (or its questions) to build the modal. With the database down those reads would have
    raised into `AnswersErrors`' generic fallback instead of saying `DB_UNAVAILABLE` in words
    (checklist 8). `run_move` was also reordered to defer → `db_ready` → read, which is P5's
    order anyway. One test pins it.
14. **`decidable()` was added beside `decides_anything()`.** §F names only the boolean; the staff
    split needs the LIST too, so an approver's queue can be filtered to the forms they may decide
    without asking `can_decide` twice per form. `decides_anything` is `bool(decidable(...))` in
    spirit and kept as its own name because §B reads better with it.
