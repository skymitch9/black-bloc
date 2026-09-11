# Phase 19 — Applications (the Twitch Team form, member request #2)

> ⚠️ **Superseded on the DOOR, 2026-09-03 (v66, `853776c`): every `/apply *` and `/applications *` subcommand named below is retired** — BOTH groups and all seventeen leaves, which is why this was the program's second real `commands synced` drop (43 → 42). One member-visible `/apply` opens a panel and every subcommand is a button, a picker or a modal on it — [`applications-panel-design.md`](applications-panel-design.md). The forms, the questions, the states, the DMs, the logs, the settings and the site are all unchanged; only the way in is. Read this file for BEHAVIOUR, never for the command to type.
>
> ⚠️ **Superseded IN BEHAVIOUR too, 2026-09-03 (v62, `9891f71`, schema 28): an application form
> no longer has to grant a role.** A form with no role keeps a **list** instead — see
> [`applications-no-role-design.md`](applications-no-role-design.md) and the
> `applications_roster_shows_left` key. The role path below is still one of the two shapes,
> not the only one.

> **Audience:** the Opus builder first, reviewers second, the owner for the
> decisions table. **Status:** TRACKED · ✅ **LIVE since 2026-09-03** (shipped with
> `applications_mode` **off**) — built on branch tip `dcba425` (~575k Opus tokens),
> **merged `7b1c592`** and deployed with Phases 17 and 18 in one release,
> `2026-09-03T00:31:37-07:00` (schema 25 `application_forms`/`application_questions`/
> `applications`, 19 cogs incl. `community.applications`, 44 commands synced, `/apply` hidden);
> `DONE.md` → "2026-09-03 — Phases 17/18/19". ⚠️ Fly release numbers were not written into
> `deploys.log` until **v59** (2026-09-03), and this deploy predates the first numbered line,
> so it has a date and a merge sha but no `vNN`.
>
> ⚠️ **§D lists SEVEN keys; there are TEN today** — `applications_panel_minutes`,
> `applications_panel_own_list` (both with the panel, v66) and `applications_roster_shows_left`
> (with the no-role form, v62). ✅ **§I's two residuals ARE FILED** — **KI-17** ("Black Bloc
> cannot confirm the twitch.tv Team invite was ever sent") and **KI-18** ("Editing a question
> changes the form, never the answers already sent"), both `ACCEPTED`. ✅ **§J.1 was answered
> YES**: `change_roles` is module-level (`cogs/community/role_menus.py:704`) and remembers its
> own changes, so no `_add_role` deviation was needed.
>
> Last verified: **2026-09-11 11:08** — re-checked against the tree at `1d090e5`:
> `black_bloc/applications.py` and `cogs/community/applications.py` exist; **10**
> `applications_*` keys are in `KEY_TYPES`; `change_roles` is at `role_menus.py:704`;
> `applications` is one of the 18 `logkinds.FEATURES`.
> ⚠️ **NOT checked:** whether `applications_mode` is still off on the live guild, whether any
> form or application exists, and anything in Discord or a browser — nothing in this pass met
> either.
> Before that, **2026-09-02** — the "what exists" rows were read in the code
> that day at `820c393` (`storage/db.py` `role_requests`/`role_grants`/`role_menus`,
> `rolegrants.py` `add_grant`/`remember_change`/`decide_request`,
> `cogs/community/role_menus.py:_approve_request` and its `change_roles`
> call, the `rolemenu_*` registry keys).
> ⚠️ **Built IN PARALLEL with Phases 17 and 18** (owner, 2026-09-02 22:25) — §K.

## The ask

Request #2 (Pawpette, staff, 2026-09-02 16:48 Phoenix): *"Twitch Team
application form to be done via bot and approved by staff"* — why: *"makes it
easier"*. Owner: build next after raid trains (2026-09-02 20:14). The
twitch.tv Team invite has **no public API** — a Team owner clicks it on
twitch.tv — so the bot owns everything around that click: the form, the staff
review, the role, the DMs, and a named nudge to the person who sends the invite.

Design it as **applications** in general (a staff-defined form that, when
approved, grants a role), with the Team form as the first one the owner
creates. Nothing Team-specific is hard-coded.

## What exists (reuse, do not rebuild)

| Piece | Where |
|---|---|
| Time-limited role grants with a ledger the reconciler trusts | `rolegrants.py:add_grant(source=…)`, `remember_change` (⚠️ MUST be called before any role edit or Phase 9's reconcile loop reads it as a by-hand change — §J) |
| Staff approve/deny card with modal reason, "already decided" race guard | `role_menus.py:_approve_request / _deny_request / RequestButton / RequestDenyModal` — the PATTERN; your classes are your own (§K) |
| Modal shape, ≤5 fields, `AnswersErrors` | `events.py:EventModal`, `role_menus.py:RequestDenyModal` |
| Approval channel + approver role | registry `rolemenu_approval_channel_id`, `rolemenu_approver_role_id` (fallbacks for D3/D4) |
| DM with refusal-in-words + `dm_failed` logging | `cogs/community/requests.py:dm` |
| Guarded post + shadow `would_*` + TEST_MODE refusal | `cogs/content/youtube.py:_announce` |
| Persistent button views re-registered at boot | `role_menus.py` (the `re-registered on message` boot line) |
| Page section + API + mock contract shape | `page-rolemenus.js`, `api/tools/rolemenus.py` |

## Decisions (defaults chosen 2026-09-02; each is a settings key — checklist 33)

| # | Question | Default | Key |
|---|---|---|---|
| D1 | Feature mode | **`off`** → shadow → on | `applications_mode` |
| D2 | Who defines forms | **staff** (the existing staff check); forms live in the DB, never in code | — |
| D3 | Where the review card posts | per-form `review_channel_id`; blank = `applications_channel_id`; blank = `rolemenu_approval_channel_id` | `applications_channel_id` channel |
| D4 | Who may approve/deny | per-form `approver_role_id`; blank = `applications_approver_role_id`; blank = `rolemenu_approver_role_id`; blank = staff | `applications_approver_role_id` role |
| D5 | Questions per form | **≤ 5** (Discord modal cap — fixed), each `label`, `style` short/long, `required`, `placeholder`; staff edit them by slash AND on the dashboard | — |
| D6 | One open application per member per form | **yes** (partial unique index); a decided one can be re-filed after `retry_days` | per-form `retry_days`, default from `applications_retry_days` int `30` |
| D7 | On approve | grant the form's role via `add_grant(source="application:<form>")` (+`remember_change`, +Discord role add), optional expiry `expires_days` per form (blank = permanent), DM the applicant the form's `approved_text` | `applications_dm_on_decision` bool `true` |
| D8 | The human step after approve | per-form `owner_user_id` + `next_step` text: the approved card is edited to `@owner — next step: {next_step}` (the Team-invite click, named), the DM carries `next_step` too | — (per-form fields, editable both ways) |
| D9 | On deny | reason **required**, DM with the reason and when they may re-apply | — |
| D10 | Withdraw | the applicant may withdraw while pending | — |
| D11 | Entry points | `/apply start <form>` **and** a persistent **Apply** button panel per form (`/applications panel`) | — |
| D12 | Staff ping on a new application | none; a role when set | `applications_ping_role_id` role blank |
| D13 | Answers visibility | staff (card + dashboard); the applicant sees their own via `/apply status` | — |
| D14 | Logging | per-feature level | `applications_log_level` level `important` |

## A. Storage — schema **25** (additive; 23 = Phase 17, 24 = Phase 18 — §K)

```sql
CREATE TABLE IF NOT EXISTS application_forms (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id          INTEGER NOT NULL,
    name              TEXT    NOT NULL,            -- slug, autocomplete key
    title             TEXT    NOT NULL,
    description       TEXT,
    role_id           INTEGER NOT NULL,
    review_channel_id INTEGER,
    approver_role_id  INTEGER,
    owner_user_id     INTEGER,
    next_step         TEXT,
    approved_text     TEXT,
    expires_days      INTEGER,
    retry_days        INTEGER,
    open              INTEGER NOT NULL DEFAULT 1,  -- 0 = not accepting
    panel_channel_id  INTEGER,
    panel_message_id  INTEGER,
    created_by        INTEGER NOT NULL,
    created_at        TEXT    NOT NULL,
    updated_at        TEXT    NOT NULL,
    UNIQUE (guild_id, name)
);
CREATE TABLE IF NOT EXISTS application_questions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    form_id     INTEGER NOT NULL,
    position    INTEGER NOT NULL,                  -- 1..5
    label       TEXT    NOT NULL,                  -- ≤45 chars (Discord)
    style       TEXT    NOT NULL DEFAULT 'short',  -- short | long
    required    INTEGER NOT NULL DEFAULT 1,
    placeholder TEXT,
    UNIQUE (form_id, position)
);
CREATE TABLE IF NOT EXISTS applications (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id      INTEGER NOT NULL,
    form_id       INTEGER NOT NULL,
    user_id       INTEGER NOT NULL,
    answers       TEXT    NOT NULL,                -- JSON [{label, answer}] snapshot
    status        TEXT    NOT NULL DEFAULT 'pending', -- pending | approved | denied | withdrawn
    submitted_at  TEXT    NOT NULL,
    decided_by    INTEGER,
    decided_at    TEXT,
    deny_reason   TEXT,
    grant_id      INTEGER,
    card_channel_id INTEGER,
    card_message_id INTEGER
);
CREATE UNIQUE INDEX IF NOT EXISTS applications_one_open
    ON applications(form_id, user_id) WHERE status = 'pending';
```

Answers are a **snapshot** with labels — editing a question later never
rewrites history. `TRANSITIONS`: `pending → approved | denied | withdrawn`,
all final.

## B. `black_bloc/applications.py` — pure helpers

`TRANSITIONS`/`may_move`; `validate_question(label, style, required,
placeholder)` (Discord limits: label ≤45, placeholder ≤100, ≤5 per form);
`render_card(form, application, member, answers)` (embed: title, applicant,
one field per answer clamped to 1024, footer `#id · <t:submitted:R>`);
`decision_lines(form, application)` (the DM + card wording for
approved/denied/withdrawn incl. `next_step` and the re-apply date);
`still_cooling(last_decided, retry_days)` (reuse `rolegrants.still_cooling`);
`answers_json(fields)`. Autocomplete choices from `open` forms.

## C. `black_bloc/cogs/community/applications.py` — the cog

- Mode gate like every cog; `shadow` posts nothing and logs
  `application.would_post` / `.would_dm`; TEST_MODE refusal logged
  `application.post_skipped_test_mode`, DMs allowed.
- **Modal built per form at runtime** from `application_questions` (a
  `discord.ui.Modal` subclass with `add_item(TextInput(...))` per row; a form
  with zero questions refuses in words: "this form has no questions yet — staff
  add them with `/applications question add`").
- Submit: D6 checks (open application → "you already have one pending — `/apply
  status`"; cooling → "you can re-apply <t:…:R>"); insert; post the card with
  Approve / Deny buttons (persistent `custom_id` `application:<id>:approve|deny`,
  re-registered at boot like role menus); D12 ping; DM "received".
- Approve (D4 gate): `decide` with the race guard → `remember_change` →
  role add → `add_grant` → edit the card (decision + D8 owner nudge) → DM.
  A failed role add logs `application.grant_failed`, leaves the status
  `approved`, and the card says so in words (staff can add the role by hand).
- Deny: modal reason (required) → decide → card → DM with the reason + re-apply
  date. Withdraw: applicant only, while pending.
- Member group **`/apply`**: `start <form>`, `status`, `withdraw <form>`.
- Staff group **`/applications`** (manage_roles default perms): `mode`,
  `create <name> <title> <role> [channel] [approver_role]`, `edit <form>
  [title] [description] [open] [owner] [next_step] [approved_text]
  [expires_days] [retry_days]`, `question add <form> <label> [style]
  [required] [placeholder]`, `question edit <form> <position> …`, `question
  remove <form> <position>`, `question list <form>`, `panel <form>
  [channel]` (posts/refreshes the Apply button), `list [form] [status]`,
  `show <id>`, `approve <id>`, `deny <id> <reason>`, `logs`.
- Registered in `bot.py:COGS` (**append at the end**), `/help`, `chat_data.py`
  FEATURES line ("how do I join the Twitch Team? → `/apply start`").

## D. Settings registry (+ labels.js, mock key list, exact-key-set test)

| Key | Type | Default |
|---|---|---|
| `applications_mode` | mode | `off` |
| `applications_log_level` | level | `important` |
| `applications_channel_id` | channel | blank (→ `rolemenu_approval_channel_id`) |
| `applications_approver_role_id` | role | blank (→ `rolemenu_approver_role_id` → staff) |
| `applications_ping_role_id` | role | blank |
| `applications_retry_days` | int (≥0) | `30` |
| `applications_dm_on_decision` | bool | `true` |
| *(added v66)* `applications_panel_minutes` | int | `10` — the panel's gone-quiet clock |
| *(added v66)* `applications_panel_own_list` | bool | whether the panel carries its own list |
| *(added v62)* `applications_roster_shows_left` | bool | for a form with no role — see [`applications-no-role-design.md`](applications-no-role-design.md) |

No new config/env. No secrets. *(**10** `applications_*` keys in `KEY_TYPES` as of 2026-09-11.)*

## E. Dashboard + API

`api/tools/applications.py`: forms `GET/POST /api/applications/forms`,
`PATCH/DELETE /api/applications/forms/{id}` (delete refuses while it has
pending applications — in words), questions `PUT /api/applications/forms/{id}/questions`
(the whole ordered list, ≤5, validated), `POST …/forms/{id}/panel {channel_id}`,
applications `GET /api/applications?form=&status=`, `GET /api/applications/{id}`,
`POST /api/applications/{id}/decide {status: approved|denied, reason?}`
(asks `TRANSITIONS`, D4 gate on the session's roles), `GET /api/applications/status`.
**An Applications section on the Role menus page** (`rolemenus.html` +
`page-rolemenus.js` — the page that owns "how members get roles"; do NOT add a
page): mode switch, `applications_*` namespace, forms table → form editor
(fields + the ≤5 question rows with add/remove/reorder), pending applications
with answers + Approve/Deny (reason box), decided history, Logs filtered to
`application.*`. `contract.json` + `server.mjs` fixtures + `check.mjs` green.

## F. Logs (`application.*`)

`application.form_created`, `.form_updated`, `.form_deleted`,
`.question_changed`, `.panel_posted`, `.submitted`, `.approved`, `.denied`,
`.withdrawn`, `.granted`, `.grant_failed`, `.would_post`, `.would_dm`,
`.post_skipped_test_mode`, `.post_failed`, `.dm_failed`. Important = decisions,
grants, failures; submissions routine.

## G. Tests (mirror)

`tests/test_applications.py` (validation limits, transitions, render, cooling,
snapshot), `tests/cogs/community/test_applications.py` (modal built from rows,
zero-question refusal, one-open, cooling, approve → ledger before role add →
grant row, grant failure path, deny needs reason, withdraw only by applicant,
shadow vs on, TEST_MODE refusal, persistent view re-registration),
`tests/api/tools/test_applications.py`, `tests/storage/test_db.py` (schema 25),
`tests/test_settings_store.py`, `tests/test_bot.py` (COGS).

## H. Docs landing with the build

`code-notes.md` (`# Phase 19`), `access/sweeps.md` rows — including the
**owner's setup walk-through for the Twitch Team form** (create form →
role → five suggested questions: Twitch handle · how long streaming · schedule ·
what you stream · why the Team → `owner` = the Team owner → `next_step` =
"the Team owner sends your twitch.tv invite — accept it from your Twitch
notifications" → `panel`), `cutover-plan.md` ladder row, `feature-list.md` new
row **F20 applications**, `architecture.md` counts, `info/README.md` row.
Not `TODO.md`/`DONE.md`.

## I. Residuals to record in `KNOWN_ISSUES.md` at landing — ✅ BOTH FILED

*(Filed as **KI-17** and **KI-18**, both `ACCEPTED`.)*

- The twitch.tv Team invite is a human click; the bot cannot confirm it
  happened. What would change it: Twitch publishing a Teams API.
- Editing a question after submissions exist changes the modal, not history
  (snapshot by design). Accepted.

## J. First task for the builder — measure, don't assume — ✅ ANSWERED

*(1 = **yes**: `change_roles` is module-level at `cogs/community/role_menus.py:704` and calls
`rolegrants.remember_change` itself, so the applications cog imports it and no `_add_role`
deviation was needed. 2 = the persistent-view pattern was confirmed and used.)*

1. Confirm the role-add path a second cog can use WITHOUT editing
   `role_menus.py`: is `change_roles` (the thing `_approve_request` calls) a
   module-level function importable from wherever it lives? Does it call
   `rolegrants.remember_change` itself, or must you? Read the reconcile loop
   (`role_menus.py:_reconcile*` / `rolegrants.was_ours`) and PROVE with a
   test that a role added by your cog is NOT reported as a by-hand change.
   Record the finding in `code-notes.md`. If the only path requires editing
   `role_menus.py`, do NOT edit it — write your own `_add_role` that calls
   `remember_change` first and `member.add_roles`, and put it in `## Deviations`.
2. Confirm the persistent-view registration pattern (`bot.add_view` at boot
   with the `custom_id` regex) so Approve/Deny keep working after a restart.

## K. Parallel-build rules (Phases 17 and 18 are building at the same time)

Branch off `main` at `820c393` (Phase 16 is in; 17 and 18 are NOT). Merge
order is **17 → 18 → 19**; the reviewer resolves the merges, so make yours
trivial:

- **Shared files are APPEND-ONLY at the foot:** `storage/db.py` (empty 23 and
  24 steps in YOUR branch, your 25 block last, touching only your three
  tables; `SCHEMA_VERSION = 25`), `settings_store.py` (append the
  `applications_*` block last), `logkinds.py`, `bot.py:COGS`, `labels.js`,
  `contract.json`, `server.mjs` fixtures, the exact-key-set test list,
  `chat_data.py` FEATURES, `/help`.
- **Do not touch** anything Phase 17 owns (`chat*.py`, `chat_memory*`,
  `cogs/content/chat.py`, `requests.py`, `cogs/community/requests.py`,
  `api/tools/requests.py`, `page-chat.js`, `page-requests.js`, `chat.html`,
  `requests.html`) or Phase 18 owns (`raidtrain*`, `page-events.js`,
  `events.html`, `api/tools/raidtrain.py`).
- `role_menus.py`, `rolegrants.py`, `events.py`, `golive.py` are READ-ONLY
  (import, call, never edit) — §J.
- Commit at clean boundaries: schema+helpers → cog → API+page → docs.

## Deviations — what the build did differently, and why

Written by the Phase 19 builder at landing, 2026-09-02. Everything not listed here
was built as §A–§K describe it.

1. **`add_grant(source="application:<form>")` was not possible — the grant uses
   `source="approval"` instead.** `rolegrants.add_grant` validates `source` against a
   fixed `SOURCES` tuple and raises `ValueError` on anything else, and `rolegrants.py`
   is READ-ONLY for this build (§K). An approved application IS a staff approval, so
   `grants.APPROVAL` is the honest existing value; the form is recorded in the
   `application.granted` log details and the grant's row id is stored on
   `applications.grant_id`, so nothing about the provenance is lost. Adding a source is
   a migration to `SOURCES` and to every reader of it, which is the reviewer's call
   after the merge, not a parallel builder's.
2. **Shadow mode gained a third log kind, `application.would_grant`.** §F named only
   `.would_post` and `.would_dm`, but review-checklist item 1 requires every side effect
   the HTTP guard cannot see — a role add is one — to be checked explicitly and logged as
   `would_…` in shadow. Without it, approving in shadow would really hand the role over.
3. **The card's footer is `#<id> · <form name>`; the submitted time is a FIELD.**
   §B asked for a footer of `#id · <t:submitted:R>`. Discord does not render `<t:…>`
   timestamps inside an embed footer, so the relative stamp is an inline **Sent** field
   (the way `role_menus.request_card` does it) and the footer carries the id and the form.
4. **The `/apply` line went into `personas.py:FEATURES`, not `chat_data.py`.** The brief
   named `chat_data.py`; the block the conversational model actually reads is
   `black_bloc/personas.py:FEATURES`, and `tests/test_personas.py` fails by name when a
   member-facing command is missing from it. `chat_data.py` has no such list.
5. **`/applications approve` and `/applications deny` carry `extras={"staff_only": True}`.**
   Their gate is two hops away (`_decide` → `may_decide` → `require_staff`) and
   `settings_store.is_staff_command` walks one. The registry already supports the extra;
   using it states the fact on the command instead of hiding it in a test's exception list.
6. **`/applications delete` exists; §C did not list it.** `/applications create` with no
   way back would have left the owner unable to undo a typo from Discord, and the
   dashboard's DELETE was already in §E. It refuses in words while anybody is waiting.
7. **A member who already holds the form's role is recorded, not re-added.** Approving
   otherwise sends Discord a duplicate role in one `member.edit`. Found by the API tests,
   where the seeded applicant already wears the role the form hands out.
8. **Two settings constants live in `settings_store.py`, not `applications.py`.**
   `APPLICATIONS_MODES` and `APPLICATIONS_RETRY_DAYS` are declared there and imported by
   `applications.py`, because `applications.py` → `golive.py` → `settings_store.py` is a
   real import chain and the other direction would be a cycle. This is the same shape
   `golive.py` uses for `GOLIVE_TEMPLATE`.
9. **§J's fallback was not needed.** `role_menus.change_roles` is module-level and calls
   `rolegrants.remember_change` itself, so the approve path imports and calls it; no edit
   to `role_menus.py`. The proof is
   `tests/cogs/community/test_applications.py::test_a_role_this_cog_adds_is_never_reported_as_a_change_made_by_hand`,
   with its negative twin beside it.

### Not done

- **`/applications question reorder` has no slash twin.** Reordering is a dashboard
  control only (the editor's Up/Down, saved through `PUT …/questions`); from Discord the
  way to reorder is `question remove` + `question add`, which fills the freed slot. The
  slash path can edit, add and remove every question, so checklist 33 is met for the
  questions themselves — but if the owner wants ordering from Discord too, that is a
  small follow-up.
- **Nothing here has run against live Discord**, and no application has ever been
  submitted by a real person. Every claim above is test-suite evidence.
