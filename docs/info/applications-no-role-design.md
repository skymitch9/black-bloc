# Applications without a role — "let's have the bot store the info!"

**Audience:** the Opus build agent, then the reviewer. **Status:** TRACKED · BUILDABLE.
**Last verified:** 2026-09-03 against `46e3ba4` (v60 live) — every `path:line` below was read
in that tree. NOT verified: nothing has been built; no Discord or site surface was exercised.

Ask (Discord, 2026-09-03): a member asked whether the Twitch-team application could be done
*without a role*, or else a "stream team" role added as a reference point for who applied and
who belongs on the team page. Owner: **"let's have the bot store the info! that way we can
check the site and the official team page."**

Design record: the build follows this file. Any deviation goes in the **Deviations** foot.

---

## A. What is true today (measured)

| Fact | Where |
|---|---|
| A form MUST have a role | `application_forms.role_id INTEGER NOT NULL` — `black_bloc/storage/db.py:576` |
| `/applications create` requires `role: discord.Role` | `black_bloc/cogs/community/applications.py:877`; `/applications edit` (`:924`) cannot change or clear it |
| Site create refuses a blank role; PATCH refuses a blank role | `black_bloc/api/tools/applications.py:213–215`, `:260–261` (`wanted_role` `:137`) |
| Approving ALWAYS hands the role over | `_approve` `:415` → `_hand_over` `:461` (shadow → `application.would_grant`; refused → `application.grant_failed`; else grant row + `application.granted`) |
| Two strings tell staff to `/role grant` when Discord refuses | `black_bloc/applications.py:157` `ROLE_REFUSED_AFTER_DECISION`, `:194` `GRANT_FAILED_ON_CARD` |
| The card and the approval line name the role | `render_card` `:408` (`applied for <@&{role_id}>`), `decision_lines` `:445` (`APPROVED_SAID` `:180` "has **{role}** now", `EXPIRES_EXTRA` `:193`) |
| The applications ARE stored already — answers, status, who decided, when | `applications` table `db.py:604–618`; site rows `api/tools/applications.py:104` |
| `/applications list form:x status:approved` lists them (25 max) but the header line prints `<@&{role_id}>` | `cogs/community/applications.py:1263–1265` |
| Twitch logins exist per member, not per guild | `golive_links(user_id, twitch_login, twitch_user_id, linked_at)` — `cogs/content/golive.py:130`; read helper `raidtrain.py:299` `twitch_login_of(db, user_id)` |
| `update_form` DROPS `None` values, so nothing can be cleared through it today | `black_bloc/applications.py:558` |
| `application_questions.form_id` has an FK **with `ON DELETE CASCADE`** on `application_forms(id)`, and `connect()` turns `PRAGMA foreign_keys=ON` before the schema runs | `db.py:595`, `:694–698` |

So: **not possible today**, but everything the roster needs is already on disk except a
nullable role and a place to read it.

## B. Decision

1. **A form's role becomes optional.** A form with no role stores the application, DMs the
   decision, and hands nothing over. A form WITH a role behaves exactly as now.
2. **The roster is the set of approved applications on that form** — one fact, one home.
   No new table, no `team_members` copy. Members who left the server are shown, flagged, not
   hidden (the team page may still list them; staff decide).
3. **Staff can take somebody off a no-role roster** with a new terminal status `removed`
   (`APPROVED → REMOVED`), a one-line reason the person is DM'd, `retry_days` applying as it
   does after a denial. Without this a roster has no way off it, which the first team change
   would find. For a role form the role's own end (revoke / expiry) stays the way off; the
   `removed` move is offered only on no-role forms.
4. **The roster is read on the site** (Role menus page → Applications section, per form) with
   each member's Twitch login when one is linked, and a **Copy as text** button so the
   official team page can be updated from it. Discord keeps `/applications list form:… status:approved`,
   fixed to show the Twitch login and not print `<@&None>`. No new slash command.
5. **Schema 27 → 28** (the check feature owns 27 — `requests-check-design.md` §C2; if this
   lands first, take 27 and tell the other build): rebuild `application_forms` with
   `role_id INTEGER` nullable. Sentinel-zero was rejected: `<@&0>` leaks into every string
   that formats the role, and `holds_role(member, 0)` is a silent lie.

## C. Build spec

### C1. `black_bloc/storage/db.py`

- `SCHEMA_VERSION` → 28 (or 27, see B5).
- DDL at `:576`: `role_id INTEGER,` (drop `NOT NULL`). Nothing else in the table changes.
- New rebuild step, modelled on the `mod_cases` pair (`:723`, `:733`) **but run BEFORE
  `PRAGMA foreign_keys=ON`** (`:694`), because with FKs on, `DROP TABLE application_forms`
  performs an implicit `DELETE` that CASCADES into `application_questions` — every question
  on every form would vanish. Order inside `connect()`:
  1. `await self._loosen_application_form_roles()` — **new, placed between `row_factory` and
     the two PRAGMAs** (`:692–693`); it must see `foreign_keys` still OFF (the default).
  2. Body: `PRAGMA table_info(application_forms)`; return unless a row has `name == "role_id"
     and notnull`. Then `CREATE TABLE application_forms_loosened (…)` using the SAME column
     list as the schema (one fact one home: pull the DDL from a module constant
     `APPLICATION_FORMS_DDL` that `SCHEMA` also interpolates, so the two cannot drift),
     `INSERT INTO application_forms_loosened SELECT * FROM application_forms`,
     `DROP TABLE application_forms`, `ALTER TABLE application_forms_loosened RENAME TO
     application_forms`, `log.warning("database: rebuilding application_forms so a form may
     have no role")`.
  3. Do NOT use the mod_cases rename-then-restore shape here: renaming the live table would
     rewrite `application_questions`' FK to point at the renamed copy (SQLite ≥ 3.26 does this
     unless `legacy_alter_table` is on), and the fresh `application_forms` would then be
     unreferenced.
- Test (`tests/storage/test_db.py`): build a 26-shape db by hand with `NOT NULL`, two forms, three
  questions and one application; connect; assert `role_id` is nullable (`PRAGMA table_info`),
  all rows carried over, **all three questions still present**, FK pragma on afterwards,
  second connect is a no-op (no warning).

### C2. `black_bloc/applications.py` (module)

| Change | Detail |
|---|---|
| `REMOVED = "removed"`; `STATUSES += (REMOVED,)`; `SETTLED += (REMOVED,)`; `TRANSITIONS[APPROVED] = (REMOVED,)`; `TRANSITIONS[REMOVED] = ()` | `:34–41`. `may_move(APPROVED, REMOVED)` becomes true. Every place that enumerates `STATUSES` (slash choices `cogs/…/applications.py:1233`, site `wanted_statuses` `api/tools/applications.py:125`, `APPLICATION_TONE` in `page-rolemenus.js`, mock `contract.json`) picks it up or needs the new entry — the build lists each. |
| `role_of(form) -> int \| None` | `int(form_value(form, "role_id")) if form_value(form, "role_id") else None`. Every `form["role_id"]` read in the tree goes through it. |
| `create_form(..., role_id: int \| None, ...)` | `:481`; stores `int(role_id) if role_id else None`. |
| `NO_ROLE = 0` at the edit boundary | `update_form` `:553` keeps dropping `None` (that is how "leave it alone" is spelled). To CLEAR a role callers pass `role_id=NO_ROLE`; after the `wanted` filter add `if wanted.get("role_id") == NO_ROLE: wanted["role_id"] = None` — but the `kept` dict comprehension would then lose it again, so build the SQL from `kept` where a `None` value is an explicit `SET role_id = NULL`. Same trick fixes the standing inability to clear `review_channel_id`/`approver_role_id`/`owner_user_id`, but that is **out of scope** — do not widen it. |
| `render_card` `:408` | description: `f"<@{who}> applied for <@&{role}>"` when `role_of(form)` else `f"<@{who}> applied for **{title}**"`. |
| `decision_lines` `:433` | `granted: bool \| None = True` — `None` means "nothing to hand over". Approved + no role: `said = APPROVED_ON_RECORD.format(name=…, title=…)` (new string `"Approved — **{name}** is on the **{title}** list now."`), no `EXPIRES_EXTRA`, no `GRANT_FAILED_ON_CARD` (`:451` becomes `if granted is False`). Approved + role: unchanged. New branch `status == REMOVED`: card `REMOVED_SAID = "Taken off the list, and they have been told why."`, DM `DM_REMOVED = "**{title}** on **{guild}** — staff took you off the list. The reason given was: {reason}. You can apply again {stamp}."` (reuse `retry_at` + `deny_reason` column — the column name stays `deny_reason`; the row's `status` says which it was). |
| `remove_application(db, application_id, *, decided_by, reason) -> bool` | Mirrors `decide_application` for DENIED but requires `status = 'approved'` in the `WHERE`; sets `status`, `decided_by`, `decided_at`, `deny_reason`. Reason required (`REMOVE_NEEDS_A_REASON`, same voice as `DENY_NEEDS_A_REASON` `:153`). |
| `NO_FORMS_YET` `:164` | `/applications create <name> <title>` — role no longer in the sample. |
| `applications_for(...)` | unchanged; roster = `statuses=(APPROVED,)`. |

### C3. `black_bloc/cogs/community/applications.py` (cog)

| Change | Detail |
|---|---|
| `_approve` `:415` | `role = forms.role_of(form)`; `until = grants.expires_at(…) if role else None`; `details["role_id"] = role`; `granted = await _hand_over(…) if role else None`; `:451` → `if granted is False and is_live(...)`. |
| `_hand_over` `:461` | unchanged in body; only ever called with a role. |
| `remove(bot, guild, application_id, actor, reason, *, via)` | New sibling of `_deny`: `forms.remove_application` → `log_action(kind_via("application.removed", via), target=member, details={application_id, form, reason})` → `decision_lines` → `send_dm` → `edit_card`. Refuses when the form HAS a role (`REMOVE_IS_FOR_LISTS = "**{name}** hands over <@&{role}>; take the role off them with `/role revoke` and the record follows."`). |
| `/applications create` `:864` | `role: discord.Role \| None = None`, describe: `"The role an approved application hands over; leave it out to keep a list instead"`. Log details `role_id: role.id if role else None`. |
| `/applications edit` `:912` | add `role: discord.Role \| None = None` and `no_role: bool \| None = None` (describe `"True clears the role so the form keeps a list instead"`); `role_id = role.id if role else (forms.NO_ROLE if no_role else None)`. Refuse `role` + `no_role` together (`ROLE_OR_NO_ROLE`). |
| `/applications list` `:1263` | header line: `<@&{role}>` when `role_of(one)` else `"list"`; each approved row on a no-role form appends `· twitch.tv/{login}` when `golive_links` has one (`SELECT twitch_login FROM golive_links WHERE user_id = ?` via a small `forms.twitch_logins_for(db, user_ids) -> dict[int, str]` — one query, not one per row). |
| Discord path off the list | The pending card's Approve/Deny are unchanged and **no new slash command** is added (owner rule 2026-09-03, minimise slash). `/applications show <id>` (`:1283`, a bare ephemeral embed today) gains a `Panel` view from `black_bloc/panels.py` carrying ONE button, **Take off the list** (danger), rendered only when `status == approved and role_of(form) is None and may_decide(...)`; it opens a reason modal and calls `remove(...)`. When the button does not apply the embed is sent without a view, exactly as now. Site path is C5. |

### C4. Settings (`black_bloc/settings_store.py`) — checklist 33

One new key: `applications_roster_shows_left` (bool, default **true**, KEY_HELP: "Whether the
approved list still shows people who have left the server, marked as gone. False hides
them."). Register in `KEY_TYPES`/`KEY_HELP`, mock `server.mjs` settings table, `labels.js`.
Nothing else is a decided default: whether a form has a role is per-form and has both a slash
path (C3) and a dashboard editor (C5).

### C5. Site — `black_bloc/api/tools/applications.py` + `site/public/assets/page-rolemenus.js` + mock

| Change | Detail |
|---|---|
| `form_row` `:86–87` | `role_id`: `str(role) if role else None`; `role_name`: resolved only when a role is set, else `None`. `resolve_one(guild, None)` must not be called. |
| `POST /forms` `:213` | drop `payload.get("role_id") in (None, "")` from the refusal; `role = wanted_role(...) if payload.get("role_id") else None`; pass `role.id if role else None`. |
| `PATCH /forms/{id}` `:260` | `if "role_id" in payload: changes["role_id"] = wanted_role(...).id if payload["role_id"] else forms.NO_ROLE`. |
| `GET /roster?form=<id>` (new) | Approved rows for that form (404 in words when the form is unknown), each: `application_id, user_id, user_name, user_avatar, in_server (bool), twitch_login (nullable), decided_at, decided_by_name`. One `twitch_logins_for` query. Honour `applications_roster_shows_left`. |
| `POST /{application_id}/remove` (new) | body `{reason}`; `writer(request)`; calls cog `remove(...)` with `via=VIA_WEB`; refusal texts pass through as 400s in words. |
| `application_row` `:104` | unchanged (status now may be `removed`). |
| `formEditor` `:671` | role select gains a blank option labelled **"No role — keep a list"** (`roleSelect(…, { allowNone: true })` if the helper supports it, else prepend the option); `field('Role it hands over', …)` help: "Leave blank to keep a list instead of handing over a role." Hide `'Role lasts, days'` when the select is blank. `body.role_id = readSelect(role, false) \|\| null` on create, `\|\| ''` on PATCH so the API sees "clear". |
| `formsTable` `:872` | Role cell: `chipFor` when set, else `badge('list', null)`. |
| New `rosterFoldout(form)` in `applicationsSection` `:961` | Per form, after its Apply-button card: `foldout(\`Approved for ${form.name}\`, …, { count })` fetching `/api/applications/roster?form=<id>` lazily on open. Table: Member · Twitch (link `https://twitch.tv/<login>` or quiet "not linked") · Since (`ago(decided_at)`) · By · a **Take off the list** button (no-role forms only, reason modal via `ask({ input })` like Deny `:346`). Header bar: **Copy as text** → clipboard, one line per member `Name — twitch.tv/login` (or `Name — no Twitch linked`), gone members suffixed ` (left the server)`. Empty state: "Nobody is on this list yet." |
| `decidedApplications` `:851` | `APPLICATION_TONE.removed = 'warn'`. |
| Mock `site/mock/server.mjs` | `:4913` `role_name: form.role_id ? memberName(form.role_id) : null`; create/PATCH routes accept blank role; new roster + remove routes; one fixture form with no role (`twitch-team`) and three approved rows, one member absent from the members fixture, two with golive links. `contract.json`: forms row `role_id`/`role_name` nullable, new roster shape, `removed` status. |
| `site/scripts/check.mjs` | walk: open the roster foldout for `twitch-team`, assert three rows, click Take off the list on one with a reason, assert two rows + the Decided table shows `removed`. Route count 139 → 141 (roster + remove). |

### C6. Log kinds (`black_bloc/logkinds.py`, `tests/test_logkinds.py`)

- `application.removed` — routine (a staff decision the person is DM'd about; the DM is the loud part). Write it as a literal inside `kind_via(...)` so `_branches` (`tests/test_logkinds.py:272`) counts it and the `web.` head; add to whatever quiet/loud list the applications test asserts on (find it by `application.denied`).
- No new kind for "approved without a role" — `application.approved` with `granted: null` in details is the record; `application.granted`/`would_grant`/`grant_failed` simply do not fire.

### C7. Tests — mirrored files, one per source file touched

| File | Must cover |
|---|---|
| `tests/storage/test_db.py` | C1 rebuild: questions survive, rows carried, idempotent, FK on afterwards. |
| `tests/test_applications.py` | `role_of`; `create_form(role_id=None)`; `update_form(role_id=NO_ROLE)` clears, `role_id=None` leaves alone; `render_card` both descriptions; `decision_lines` approved/no-role (no expiry, no grant-failed text), approved/role unchanged, removed; `remove_application` refuses non-approved; `may_move(APPROVED, REMOVED)`; `twitch_logins_for` one query. |
| `tests/cogs/community/test_applications.py` | `_approve` on a no-role form: `_hand_over` NOT called, log details `granted: None`, `role_id: None`, DM sent, card edited, no `ROLE_REFUSED_AFTER_DECISION`; `_approve` on a role form unchanged (existing tests stay green); `remove` happy path + refuses role forms + reason required; `/applications create` without role; `/applications edit role:` / `no_role:` / both; `/applications list` header + twitch suffix; the show-panel button renders only in the right state. |
| `tests/api/tools/test_applications.py` | `form_row` with `None` role never calls `resolve_one`; POST/PATCH blank role; roster shape, `in_server`, `twitch_login`, hidden-left setting; remove route 400s in words. |
| `tests/test_settings_store.py` | the new key registered, bool-coerced, help text present. |
| `tests/test_logkinds.py` | `application.removed` known. |

### C8. Docs the build ships with

- `docs/access/sweeps.md`: rows **69–72** (66–68 belong to the check feature): 69 create a no-role form on the site and see the list badge; 70 apply + approve → DM says "on the list", no role given, `application.approved` shows `granted: null`; 71 roster foldout shows Twitch login + Copy as text pastes the lines; 72 Take off the list → DM with reason, Decided table says removed, `/applications list status:approved` no longer shows them.
- `docs/access/OWNER_GUIDE.md`: the applications paragraph — "a form can keep a list instead of handing over a role"; sweep count.
- `docs/info/code-notes.md`: "# Applications, no-role pass" — the FK-cascade reason for the rebuild order (C1) is the note that earns its keep; `NO_ROLE` vs `None` in `update_form`; `granted=None`.
- `docs/info/README.md` row for this file flips BUILDABLE → BUILT (commit); `TODO.md` item moves whole to `DONE.md` at landing (conductor).

## D. Owner-flippable calls (each has a default; none blocks the build)

| # | Call | Default | Where to flip |
|---|---|---|---|
| D1 | Roster shows members who left | shown, flagged | `applications_roster_shows_left` (C4) |
| D2 | "Take off the list" needs a reason | required, DM'd | same pattern as deny; a setting is not offered — a silent removal is the thing the member complained about in reverse |
| D3 | Twitch login source | `golive_links` only (member must have linked once) | if the team wants a manual login on the form, that is a per-application field — out of scope, see E |
| D4 | Copy-as-text line shape | `Name — twitch.tv/login` | `page-rolemenus.js` constant `ROSTER_LINE` |

## E. Out of scope (say no, do not build)

- Auto-posting the roster anywhere in Discord, or a temporary "stream team" role the bot
  takes back later (the member's second idea) — the owner picked the stored list.
- Editing a member's Twitch login from the roster; a roster entry note/position.
- Widening `update_form` so `None` clears other columns (C2 flags it; separate item).
- Exporting the roster to the "official team page" itself — that page is not ours; Copy as text
  is the bridge.

## F. Build brief essentials

- Branch `feat/applications-no-role` from `main` ≥ `46e3ba4`, own worktree, Opus. The
  `feat/requests-check` build may run beside it — different cogs, but **both bump
  `SCHEMA_VERSION`**: whichever merges second re-keys to the next number in the merge, never
  by editing the other branch. Never `git stash`, never `git add -A`, never touch the other
  worktree.
- Commit at boundaries: (1) db rebuild + its test; (2) module + cog + tests; (3) API + site +
  mock + check.mjs; (4) settings key + docs. Finish fewer things completely.
- Gate expectations: `pytest -q -n auto` ≥ 3371 + new; ruff clean; every `site/public/assets/*.js`
  parses as an ES module; `check.mjs` reports 141 routes.
- `TEST_MODE` stays on; the bot speaks only in `#mute-me-bot-test-spam` and DMs. Secret NAMES
  only. Near-zero comments — explanations go to `code-notes.md`. Refusals in words, never a
  bare status. Review against `docs/info/review-checklist.md` (33 items) before reporting.
- Report: what was verified by running it, what was not, and the review links (Role menus page
  → Applications section; `/applications show <id>` in the test channel).

## Deviations

_(the build appends here; empty means none)_
