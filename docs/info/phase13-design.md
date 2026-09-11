# Phase 13 — Requests (F18): `/request` replaces the ideas doc

> ⚠️ **2026-09-03 (v61, `44170f4`, after four passes): slash paths superseded by the panel** —
> `/request` is now ONE command that opens an interactive panel and `list`, `withdraw`, `set`
> and `logs` are all controls on it; see [`requests-panel-design.md`](requests-panel-design.md).
>
> ⚠️ **The STATE MACHINE in decisions 3 and 5 was replaced by Phase 17** (merge `6d61994`,
> deployed `2026-09-03T00:31:37-07:00` as `7b1c592`). `pending`, `approved` and `planned` all
> folded into **`open`**; `hold` and `review` were added; `held_from` remembers where a held
> row came back to; and **`request_auto_approve_staff` was retired** — it is no longer in
> `KEY_TYPES`, because with no `pending` state there is nothing to auto-approve. Measured
> 2026-09-11, `black_bloc/requests.py:27`: `STATUSES = (open, in_progress, review, hold, done,
> declined, withdrawn)`. See [`requests-states-design.md`](requests-states-design.md).

> ✅ **13a built in `5d637b4` (storage), `e7e0f9e` (settings), `cf23268` (cog),
> `27ec297` (API + member gate) and `415eb8c` (contract + mock)**, on branch
> `worktree-agent-ae90babf488323552` off `main` @ `40b7782`. The dashboard page is
> **13b**, built in parallel. Notes: `code-notes.md` § *requests (13a)*; routes:
> `phase8b-design.md` § *Requests (13a)*.
> ⚠️ **NOTHING has been run against live Discord** — no gateway session, no
> `/request`, no modal, no DM, no notice line.

> **Audience:** the Phase 13 build agents and the reviewer. **Status:** TRACKED ·
> ✅ **LIVE since 2026-08-27** — 13a + 13b deployed together as `8036918`,
> `2026-08-27T20:15:35-07:00` (schema 16, 35 commands synced, `/health` ok), with the same
> night's integration fixes; `DONE.md` → "2026-08-27 — Phase 13: Requests (/request, member
> sign-in, the Requests page) + integration night fixes". ⚠️ Fly release numbers were not
> written into `deploys.log` until **v59** (2026-09-03), so this landing has a date and a
> commit but no `vNN`. Requests then took **six more passes** before it settled — see
> `DONE.md` 2026-09-03, third through sixth.
>
> Last verified: **2026-09-11 10:20** — re-checked against the tree at `1d090e5`:
> `black_bloc/requests.py`, `cogs/community/requests.py` and `site/public/requests.html` all
> exist; `request_mode`, `request_who_can_file`, `request_notify_channel_id`,
> `request_dm_on_decision` and `request_log_level` are in `KEY_TYPES` (the `request` namespace
> is **12** keys); `request_auto_approve_staff` is **NOT** — see the banner above. The "17
> pages / 89 routes" in the 13b note is now **17 pages / 150 routes**.
> ⚠️ **NOT verified:** still nothing against live Discord in this pass — no `/request`, no
> panel, no modal, no DM, no notice line, and no browser was opened.
> Before that, **2026-08-27** — owner answers taken 17:42–17:46; patterns from
> `code-notes.md` §§ events (review card), role menus 2 (requests + decisions), polls 10b (create form).

> ✅ **13b built in `a260e1b` (contract + mock) and `fec0f57` (the page)** on branch
> `worktree-agent-acd6d4a9712a56eb0` off `main` @ `40b7782`, and **merged in `641e53b`**
> on the integration branch `worktree-agent-acd3594b9dbefbec2` (off `main` @ `16c5781`).
> `docs/info/code-notes.md` §§ *requests — dashboard (13b)* and *integration night
> 2026-08-27* carry the keys, the measurements and what was NOT verified.
> Both things the reviewer was asked to reconcile with 13a are done: **a member mode**
> (the owner's "also let people put request on the dashboard too") now reads the real
> router's `/api/auth/me` — `staff: false, member: true, state: "not_staff"` — with
> `GET /api/requests/mine` and `POST /api/requests/{id}/withdraw` behind
> `member_dependency`, and a stranger still meets the gate; and the board stays
> **cards rather than a table**, which this document's §Dashboard already allows.
> The eight contract cases that failed by design now pass: `node site/mock/check.mjs`
> is clean at **17 pages / 89 routes** and `pytest -q` is **2158 passed**.

## The ask (owner, verbatim, 2026-08-27)
- "we should also make a /request command so we can stop using the google doc, also put it on the website"
- "its just the initial doc that I gave you, its an idea on paper, we should make our request form more
  robust for sure. no need for name just collect who ask, get the what, the why, and a due date if needed.
  review can be on the site but its its a mod or higher auto approve it. have it go to a pending features list"

## Decisions
| # | Decision | Owner's call |
|---|---|---|
| 1 | Fields | **What** (required, ≤ 1000), **Why** (required, ≤ 1000), **Due date** (optional; HammerTime `<t:…:D>` shown), requester recorded automatically (no name field) |
| 2 | Who may file | everyone (`request_who_can_file` everyone/staff, default everyone) |
| 3 | Review | on the site; **a mod-or-higher requester is auto-approved** (staff derivation = the dashboard's; `request_auto_approve_staff` on/off, default on) — ⚠️ **retired by Phase 17**: the key is gone from `KEY_TYPES` and there is no `pending` state to approve out of |
| 4 | Where it goes | the **pending features list** = the dashboard **Requests** page |
| 5 | Statuses | `pending` → `approved` → `planned` → `in_progress` → `done` \| `declined` (reason) ; `withdrawn` by the requester while pending — ⚠️ **replaced by Phase 17**: `open` → `in_progress` → `review` → `done`, plus `hold` (with `held_from`) and `declined`; `withdrawn` unchanged |

## Design
- **Storage** (additive, `SCHEMA_VERSION` +1): `requests(id, guild_id, user_id, what, why, due_on NULL,
  status, priority INT NULL, assignee_id NULL, notes TEXT NULL, created_at, decided_by, decided_at,
  decline_reason NULL, done_at NULL, message_id NULL)`; `request_comments(id, request_id, author_id,
  text, at)` (staff notes / replies).
- **Bot:** `/request` opens a modal (What, Why, Due date as `YYYY-MM-DD` text, validated); on submit:
  store, ephemeral "Filed as #N — staff will see it on the site" (+ "approved straight away" for staff),
  `log_action("request.filed")`; when `request_notify_channel_id` is set, one line there (guarded).
  `/request list [mine|pending|all]` (ephemeral, paged), `/request withdraw <id>` (own, pending only),
  `/request set <id> status:<…>` (staff), `/request logs` (Phase 12 pattern) *(removed: all four
  retired at **v61**, 2026-09-03 — `/request` opens the panel and each is a button, a select or
  a modal on it, `logs` included)*. DM the requester on
  approve / decline (reason) / done. Under TEST_MODE everything but DMs is refused outside the test channel.
- **API** (staff-gated except `POST /api/requests` which any signed-in member may call if
  `request_who_can_file = everyone` — the site's first non-staff write; gate it explicitly and rate-limit):
  `GET /api/requests` (status/assignee/search/paging), `POST /api/requests`, `GET /api/requests/{id}`,
  `POST /api/requests/{id}/{approve|decline|status}` (`{reason?, status?, assignee_id?, priority?}`),
  `POST /api/requests/{id}/comments`, `GET /api/requests/export.csv`. Action kinds `request.*`, `web.request.*`.
- **Dashboard:** `requests.html` (17th page, OVERVIEW group after Audit/Logs): **Pending** (decide),
  **Planned / In progress** (kanban-ish columns or one table with a status segment), **Done**,
  **Declined** (collapsed), **File a request** form (same fields as the modal), per-row: requester
  (avatar/initial), what/why, due `<t>`, priority, assignee (member picker), notes, comments thread,
  Approve / Decline (reason) / status segment / DM requester. Sidebar count = pending. Logs section
  (Phase 12) at the foot. Level fields, token-only CSS, pager scroll-to-top.
- **Seed:** the existing ideas from `docs/info/feature-list.md` "Future" rows are NOT auto-imported
  (they are the bot's own roadmap, not member requests); the owner can file them by hand if wanted.

## Slices
- **13a** (bot + storage + API, ~200k) · **13b** (dashboard, ~150k).

## Definition of done
Tests for every branch (mirror layout); `pytest -q` green; `ruff` clean; `check.mjs` clean; code-notes
keyed `path:line`; owner sweep: `/request` as a member (pending) and as staff (auto-approved), decide on
the site, DM arrives, status moves, list on the page.
