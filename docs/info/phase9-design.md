# Phase 9 — Role menus 2: approval, time limits, reconciliation

> **9a built 2026-08-27** in `341757a` (storage, schema 13), `940927c` (the cog:
> approval flow, `/rolemenu edit`, `/role grant`, `/role extend`, the hourly
> `_expiry` loop, `on_member_update` and the record sweep) and `7605730` (the
> API: `/api/rolemenus/requests`, `/api/roles/grants`). Bot, storage, API and
> tests only — **9b still owns every `site/` page**, including adding the new
> routes to `site/mock/contract.json`. 1441 tests pass, ruff clean,
> `check.mjs` clean; **nothing has run against Discord.** Details and the one
> deliberate deviation (how a pending option is withdrawn) are in
> `code-notes.md` § "role menus 2 — approval, expiry, reconciliation".

> **9b built 2026-08-27** on branch `worktree-agent-abbf5f12160a08357` off
> `main` @ `a46b7ff`, in `1905b4d` (the API this half needed: `menu_name` and
> `user_avatar` on a queue row, `channel_id` on `PUT /api/rolemenus/{name}`
> which MOVES a posted panel, `expires_at` per role on `/api/members`),
> `487da10` (the seven 9a routes in `contract.json` and the mock, with pending
> requests and timed grants in the seed), `b669207` (the shared widgets and the
> level-field grid), `b284031` (the Role menus page: Requests, Timed roles, the
> four new editor fields, the sidebar's waiting count) and `ded42aa` (the
> Members tab's `· N d` chips and its second link). 1584 tests pass, ruff
> clean, `check.mjs` reports 14 pages / 61 routes; **nothing has run against
> Discord.** ⚠️ **B5–B7 in `site-feature-audit.md` — un-post, seed, staff
> assign — were NOT built** and were not in the brief. Details, the deviations
> and the not-verified list are in `code-notes.md`
> § "role menus 2 — dashboard (9b)".

> **Audience:** the Phase 9 build agent and the reviewer. **Status:** TRACKED (2026-08-31; private repo).
> Last verified: **2026-08-27** — decisions taken with the owner one at a time (see `TODO.md`, the
> role-menu decisions entry); code facts read from `cogs/community/role_menus.py` at `8b8f792`.
> NOT verified: nothing here has run.

## The asks (owner, verbatim, 2026-08-27)

- "certain roles menus like runner-status we want to have be on approval basis, so you select a
  role and it pings a mod to approve it"
- "we also need a way for certain roles to be time limited. the same runner status roles. so we
  can set someone to have it for a week."
- "we also need a reconciliation step so if someone is manually given a role it reflects on our
  portal and the bot knows"

## Decisions (all four settled)

| # | Decision | Owner's call |
|---|---|---|
| 1 | Approval granularity | **per menu** (`role_menus.approval = 0/1`) |
| 2 | Who approves / where | **any staff role** approves; requests post in `rolemenu_approval_channel_id` (new setting, default = `staff_channel_id`), Approve / Deny buttons; optional ping `rolemenu_approver_role_id` (default none) |
| 3 | Pending experience | ephemeral "Sent to staff for approval — you'll get a DM when it's decided"; the option shows as **pending** for that member; picking it again **withdraws**; approve = role + DM; deny = DM with the reason |
| 4 | Denial cooldown | **7 days per menu** (`role_menus.retry_days`, default 7), the denial DM says when they can retry; staff can grant by hand any time |

Plus, from the asks: **time-limited grants** (per-menu default `expires_days`, staff override at approval or via a staff command), and **reconciliation** (log manual role changes; keep grants/requests honest; never remove a role the bot did not grant).

## What exists (read, not remembered)

- `role_menus` + `role_menu_options` tables; menus have `mode` in `("multiple", "single", "staff")`, a `channel_id`/`message_id` for the posted panel. There is **no picks table**: the Discord role is the record; `apply_diff()` (`role_menus.py:447`) adds/removes roles from a select's choice.
- `RoleMenuSelect` (`:459`) handles member picks; `StaffAssignSelect` (`:521`) is the staff-mode path; `panel_embed` (`:250`), `post_panel` (`:435`), `rolemenu_panels.py` reconciles panels with `rolemenu_mode`.
- The events cog is the model for review: `DECISION_TEMPLATE = r"event:(?P<event_id>[0-9]+):(?P<action>approve|deny)"` with `SafeDynamicItem` persistent buttons (`events.py:73`), `decide()` with `deny_reason`, member DMs (`:157–160`).
- Members tab (`api/tools/members.py`) already lists live roles from the gateway cache.

## Design

### Storage (additive; bump `SCHEMA_VERSION`)
- `role_menus`: `approval INTEGER NOT NULL DEFAULT 0`, `expires_days INTEGER NULL`, `retry_days INTEGER NOT NULL DEFAULT 7` (via `ADDED_COLUMNS`).
- `role_requests(id, guild_id, menu_id, user_id, role_id, requested_at, status IN ('pending','approved','denied','withdrawn','granted_by_hand'), decided_by, decided_at, deny_reason, message_id, channel_id)`; unique open request per (menu, user, role).
- `role_grants(id, guild_id, user_id, role_id, source IN ('menu','approval','staff','manual'), granted_by, granted_at, expires_at NULL, removed_at NULL, removed_reason NULL)`; index on `expires_at`.

### Approval flow
1. Member picks a role in an `approval=1` menu → `RoleMenuSelect` does NOT call `apply_diff`; it inserts a pending `role_requests` row (refusing with a sentence if one is open, or if a denial is inside `retry_days`: "Staff said no on {date}; you can ask again {stamp}"), replies ephemerally per decision 3, and posts the request card to the approval channel: who, which role, which menu, when, with **Approve** / **Deny** `SafeDynamicItem` buttons (`rolereq:(?P<id>[0-9]+):(?P<action>approve|deny)`), pinging `rolemenu_approver_role_id` if set. Deselecting the pending option withdraws (status `withdrawn`, card edited).
2. Approve (staff only — `require_staff` semantics on the interaction): `apply_diff` adds the role with reason "approved by {staff}", `role_grants` row `source='approval'` with `expires_at = now + menu.expires_days` (a modal on Approve lets staff override the days when the menu has `expires_days`), request → `approved`, card edited to show the decision, member DM'd. Deny: modal collects the reason, request → `denied`, DM with reason + retry stamp.
3. Test mode: cards and DMs go through the guard (DMs are allowed; the approval channel is refused unless it is the test channel — under TEST_MODE the card posts in the test channel and the log says so). Everything is `log_action`-ed: `role.requested`, `role.approved`, `role.denied`, `role.withdrawn`.

### Time limits
- Every grant the bot makes (menu pick, approval, staff assign, `/role grant`) writes a `role_grants` row; `expires_at` from the menu default or the staff override; `/role grant @member @role days:7 [reason]` (staff) grants outside any menu.
- Hourly loop `_expiry` (health-visible, `loop_health`): for `expires_at <= now` and `removed_at IS NULL`: remove the role (only if the member still has it), mark removed with reason `expired`, DM the member ("Your **{role}** on {guild} ran out today"), `log_action("role.expired")`. `/role extend @member @role days:N` and a dashboard Extend button push `expires_at`.

### Reconciliation
- `on_member_update` (roles diff): for every role added/removed **not** by the bot (compare against a short in-memory set of role changes the bot just made, or the audit log entry's user when `view_audit_log` is granted): `log_action("role.changed_by_hand", actor=<audit log user or None>, details={added, removed})`; if an added role has an open `role_requests` row → status `granted_by_hand`, card edited; if a removed role has an open `role_grants` row → `removed_at`, reason `by_hand`. A manual add of a timed-menu role writes a `role_grants` row with `source='manual'` and **no** expiry.
- Hourly sweep (same loop): diff live roles vs open `role_grants`/`role_requests` for menu-managed roles and correct the RECORDS (never the member). Log a summary only when something changed.

### Surfaces
- Menu editor (dashboard + `/rolemenu edit`): Approval on/off, Expires after (days, blank = never), Retry after (days).
- New dashboard section on Role menus: **Requests** (pending first: member, role, menu, age, Approve / Deny with reason) and **Timed roles** (member, role, expires, Extend / End now). API: `GET /api/rolemenus/requests`, `POST /api/rolemenus/requests/{id}/{approve|deny}`, `GET /api/roles/grants`, `POST /api/roles/grants` (staff grant), `POST /api/roles/grants/{id}/extend`, `DELETE /api/roles/grants/{id}`; contract + mock updated; refusals in words.
- Members tab: role chip gets "· expires in N d" when a grant has an expiry.
- Settings: `rolemenu_approval_channel_id` (channel), `rolemenu_approver_role_id` (role).

## Definition of done
Tests for every branch above (mirror layout); `pytest -q` green; `ruff` clean; `check.mjs` clean; code-notes section keyed `path:line`; nothing run against live Discord — the owner's sweep: make `runner-status` approval-gated with `expires_days=7`, pick it as a member, approve as staff, watch the DM, then `/role extend`.
