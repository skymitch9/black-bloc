# Phase 13 — Requests (F18): `/request` replaces the ideas doc

> ✅ **13a built in `5d637b4` (storage), `e7e0f9e` (settings), `cf23268` (cog),
> `27ec297` (API + member gate) and `415eb8c` (contract + mock)**, on branch
> `worktree-agent-ae90babf488323552` off `main` @ `40b7782`. The dashboard page is
> **13b**, built in parallel. Notes: `code-notes.md` § *requests (13a)*; routes:
> `phase8b-design.md` § *Requests (13a)*.
> ⚠️ **NOTHING has been run against live Discord** — no gateway session, no
> `/request`, no modal, no DM, no notice line.

> **Audience:** the Phase 13 build agents and the reviewer. **Status:** TEMPORARILY TRACKED (owner order
> 2026-08-27). Last verified: **2026-08-27** — owner answers taken 17:42–17:46; patterns from
> `code-notes.md` §§ events (review card), role menus 2 (requests + decisions), polls 10b (create form).
> NOT verified: nothing has run. **Build after the Sunday 2026-08-30 16:00 reset.**

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
| 3 | Review | on the site; **a mod-or-higher requester is auto-approved** (staff derivation = the dashboard's; `request_auto_approve_staff` on/off, default on) |
| 4 | Where it goes | the **pending features list** = the dashboard **Requests** page |
| 5 | Statuses | `pending` → `approved` → `planned` → `in_progress` → `done` \| `declined` (reason) ; `withdrawn` by the requester while pending |

## Design
- **Storage** (additive, `SCHEMA_VERSION` +1): `requests(id, guild_id, user_id, what, why, due_on NULL,
  status, priority INT NULL, assignee_id NULL, notes TEXT NULL, created_at, decided_by, decided_at,
  decline_reason NULL, done_at NULL, message_id NULL)`; `request_comments(id, request_id, author_id,
  text, at)` (staff notes / replies).
- **Bot:** `/request` opens a modal (What, Why, Due date as `YYYY-MM-DD` text, validated); on submit:
  store, ephemeral "Filed as #N — staff will see it on the site" (+ "approved straight away" for staff),
  `log_action("request.filed")`; when `request_notify_channel_id` is set, one line there (guarded).
  `/request list [mine|pending|all]` (ephemeral, paged), `/request withdraw <id>` (own, pending only),
  `/request set <id> status:<…>` (staff), `/request logs` (Phase 12 pattern). DM the requester on
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
